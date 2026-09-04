"""소설 오케스트레이션의 공유 상태 -- 파일 영속, 재개 가능.

**Pydantic 대신 dataclass 를 쓴다.** plan_schema.py 와 같은 이유다: 이 저장소가 반복
실증한 것은 "인메모리 상태는 프로세스 재시작에 소실된다" 이고, 장편 소설은 수십~수백 씬이라
며칠 도는 작업이며 반드시 중간에 죽는다. 그래서 씬 하나가 끝날 때마다 JSON 으로 떨군다.
새 의존성도 늘리지 않는다(requirements.txt 에 pydantic 이 없다).

원본 설계와 바꾼 것:
  · 감정 축에 **narrative_pull 을 추가**했다. 원 문서 §2 가 이 소설의 진짜 상태 공간을
    "나오코(죽음의 인력) ↔ 미도리(삶의 추동)" 로 정확히 짚어놓고 §4 스키마에는 안 넣었다.
    joy/melancholy/isolation 세 축은 그 축을 표현하지 못한다.
  · Character 에 emotion_envelope 를 넣었다. **미도리가 지워지는 것을 막기 위한 것**이다
    (관문은 이 값을 더 이상 판정하지 않는다 -- 프롬프트의 인물 규율로만 쓴다).
  · Scene 에 pov_present / mode 를 넣었다. 1인칭 회고는 화자가 없는 씬을 서술할 수 없다.
  · narrator_foreknowledge -- 회고 프레임을 분위기가 아니라 상태로 만든다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

# 감정 축. narrative_pull 은 -100(죽음의 인력/나오코) .. +100(삶의 추동/미도리).
# 나머지 셋은 0..100.
AXES = ("joy", "melancholy", "isolation", "narrative_pull")
BIPOLAR = ("narrative_pull",)

# 검사기가 실제로 구현된 게이트 종류. 표에는 있는데 여기 없으면 "선언은 되지만 강제되지
# 않는다" 는 뜻이고, derive_gates 가 그것을 soft 문제로 보고한다.
IMPLEMENTED_GATES = ("timeline_branch",
                     "absence", "absence_physical", "lift_absence", "not_before",
                     "knowledge_grant", "knowledge_grant_covert", "stale_fact",
                     "relation_start", "relation_end", "suspend_absence",
                     "belief", "public_fiction", "public_fiction_break")
# 어겨도 세계가 자기모순이 되지는 않는 것들. 최소한만 걸러야 재미가 산다.
SOFT_GATES = ("stale_fact", "punctum_refresh", "motif_track", "object_track",
              "retro_reinterpret", "convergence", "age_advance", "stage_move")

# 한 인물이 동시에 하나만 가질 수 있는 관계. "A 와 B 가 사귀는데 어느 순간 C 가 A 와
# 사귄다" 는 오류가 바로 이 배타성 위반이다 -- 관계를 상태로 들고 있지 않으면 못 잡는다.
EXCLUSIVE_KINDS = ("연인", "약혼", "배우자")
# 방향이 있는 관계. members[0] 가 주체다. 짝사랑은 배타적이지 않다.
DIRECTED_KINDS = ("짝사랑",)


@dataclass
class Character:
    name: str
    persona: str
    hidden_agenda: str = ""
    emotions: dict = field(default_factory=lambda: {a: 0 for a in AXES})
    # 이 인물이 아는 비밀 용어들. 발화에 모르는 것이 나오면 지식 누출이다.
    knows: list = field(default_factory=list)
    # 씬 안에서 이 축이 적어도 한 번은 이 값에 도달해야 한다.
    # 미도리: {"joy": 40} -- 관문이 밝음만 벌해서 인물이 균일한 우울로 수렴하는 것을 막는다.
    emotion_envelope: dict = field(default_factory=dict)


@dataclass
class Relation:
    """관계 하나의 유효 구간. 소설의 관계는 사실이 아니라 **구간을 가진 주장**이다.

    since/until 은 씬 id 다. until 이 비면 진행 중이다. 이 구간 표현이 있어야
    "3화에서 헤어졌으니 5화에서 C 와 사귀는 것은 모순이 아니다" 를 판정할 수 있다."""
    kind: str
    members: list
    since: str
    until: str = ""
    note: str = ""

    def key(self) -> tuple:
        return (self.kind, tuple(self.members) if self.kind in DIRECTED_KINDS
                else tuple(sorted(self.members)))


@dataclass
class DynamicGate:
    """세계관 사건에서 태어난 규칙. **코드가 아니라 데이터다.**

    임의의 파이썬 함수로 만들면 JSON 에 저장되지 않고, 저장되지 않으면 재개 때 사라지며,
    사라지면 며칠짜리 런의 후반부가 무방비가 된다. 이 저장소가 인메모리 상태로 이미 값을
    치른 자리다. 그래서 선언적 명세로 두고 gate.py 의 해석기가 실행한다 -- 저장되고,
    사람이 읽을 수 있고, 감사된다.

    from_scene 이후의 씬에만 적용된다. 사건이 일어나기 전 세계에는 이 규칙이 없었다."""
    rule: str                       # "D001"
    kind: str                       # absence | not_before | stale_fact | knowledge_grant
    params: dict
    from_scene: str
    origin: str = ""                # 이 규칙을 낳은 사건
    severity: str = "hard"


@dataclass
class Fact:
    """확립된 설정 하나. key 는 'A.전공' 처럼 인물.속성 꼴을 권장한다."""
    key: str
    value: str
    since: str


@dataclass
class Turn:
    actor: str
    inner_thought: str = ""
    action: str = ""
    speech: str = ""
    emotions: dict = field(default_factory=dict)


@dataclass
class Scene:
    id: str
    location: str = ""
    punctum: str = ""
    directives: list = field(default_factory=list)
    participants: list = field(default_factory=list)
    # "dialogue" | "letter" | "reported"
    mode: str = "dialogue"
    turns: list = field(default_factory=list)
    # 이 씬에서 일어나는 관계·설정 변화. **Director 가 구조화된 데이터로 선언해야 한다.**
    # 산문 안에서만 바뀌면 기계가 검증할 방법이 없다 -- 모델이 상태를 커밋하게 만드는 것이
    # 관계 모순을 잡는 유일한 길이다.
    #   {"op": "start"|"end", "kind": "연인", "members": ["A","B"]}
    relation_ops: list = field(default_factory=list)
    #   {"key": "A.전공", "value": "건축학"}
    fact_ops: list = field(default_factory=list)
    # 세계관 자체를 바꾸는 사건. 여기서 **동적 게이트가 자동 생성된다.**
    #   {"event": "death", "who": "D"} / {"event": "meeting", "pair": ["A","C"]}
    world_ops: list = field(default_factory=list)
    # 회상 씬. 죽거나 떠난 인물도 등장할 수 있다.
    flashback: bool = False
    # 씬의 종류(style.SCENE_KINDS). 분량 배분은 지시로는 지켜지지 않으므로 -- 실측:
    # 서브플롯에 "겹치지 마라" 를 넣어도 절반쯤만 지켜졌다 -- 코드가 종류를 배정하고
    # 그 종류의 규율만 프롬프트에 싣는다. 모델은 한 종류만 잘 쓰면 된다.
    #   routine 50~60% · encounter 20~25% · delivery 15~20% · resolution 5% 미만
    kind: str = ""
    # --- 거시 서사 (arc.py) ---
    episode: int = 0                 # 몇 화인가. 0 이면 거시 검사를 건너뛴다
    scale: int = 0                   # 이 씬이 다루는 사건 규모 1~5 (arc.SCALES)
    cliffhanger: str = ""            # 회차 끝이면 5대 공식 중 하나 (arc.CLIFFHANGERS)
    is_episode_end: bool = False     # 이 씬이 회차의 마지막인가
    # --- 시간선 좌표 --------------------------------------------------------
    # **모순을 없애는 방법은 좌표를 하나 더 주는 것이다.**
    #
    # misbelieve 가 그랬다. "설윤은 X 를 믿는데 사실은 Y" 는 진실과 믿음을 분리하기 전에는
    # 모순이었다. 축을 갈랐더니 둘 다 참이 됐다.
    #
    # 시간 되감기도 같다. "설윤이 X 를 안다" 와 "설윤이 X 를 모른다" 가 모순인 것은 어느
    # 시간선인지가 없기 때문이다. branch 를 주면 둘 다 참이다 -- 원장은 그 씬이 속한
    # 시간선의 조상만 본다.
    #
    # branch 0 이 원래 시간선이다. rewind 가 일어나면 그 뒤 씬들이 branch 1 로 간다.
    # 되감은 사람은 기억을 갖고 넘어온다(carry) -- 그것이 이 장치의 존재 이유다.
    branch: int = 0
    # --- 압박과 능동 (2026-09-04 피드백: "주인공이 수동적이고 시간 압박이 없다") ---
    # 역방향 조립은 **무엇이 참이 되는가**(establishes)만 물었다. 누가 그것을 했는지 묻지
    # 않았으므로 조건이 저절로 성립하고 화자는 구경했다. 그것이 수동성의 기계적 원인이다.
    #
    #   driver          이 씬의 사건을 일으킨 사람. 화자면 그 회차는 화자가 움직인 회차다
    #   cost            driver 가 치른 대가. 공짜로 얻으면 긴장이 없다
    #   deadline        무엇을 언제까지 (사람이 읽는 문장)
    #   deadline_hours  그 시점까지 남은 시간. **기계가 읽는 숫자** -- 압박이 실제로
    #                   조여드는지는 텍스트로는 판정할 수 없다
    #   stake           못 지키면 잃는 것
    driver: str = ""
    cost: str = ""
    deadline: str = ""
    deadline_hours: float = 0.0
    stake: str = ""
    # --- 인과 배선 (episode.py 의 역방향 조립이 채운다) ---
    # requires: 이 씬이 성립하려면 이미 참이어야 하는 것
    # establishes: 이 씬이 참으로 만드는 것
    # 개연성 구멍 = 어떤 requires 가 앞의 어떤 establishes 로도 충족되지 않는 것.
    # 플롯 구멍이 그래프 도달 가능성 문제로 환원된다.
    requires: list = field(default_factory=list)
    establishes: list = field(default_factory=list)
    # --- 연출 지시 (Director 가 채우고 Actor·Narrator 가 읽는다) ---
    # 한 줄짜리 beat 만 넘기면 아래층이 알아서 지어내고, 그러면 디렉터가 없는 것과 같다.
    #   staging  공간·시간·날씨·소리. 그 공간이 이 인물에게 무엇인가
    #   trigger  씬을 여는 최초의 물리적 사건. 누가 무엇을 하는가
    #   props    되돌아올 사물. 처음엔 무심하게 놓인다
    #   camera   화자가 무엇을 보고 **무엇을 놓치는가**. 1인칭에서 시야는 곧 정보 통제다
    #   subtext  두 인물이 각각 말하지 않는 것
    #   beat_arc 이 씬에서 감정이 어디서 어디로 (pull 시작 -> 끝)
    direction: dict = field(default_factory=dict)
    prose: str = ""
    status: str = "pending"          # pending | gated | verified | failed
    violations: list = field(default_factory=list)
    attempts: list = field(default_factory=list)


@dataclass
class Novel:
    title: str
    pov_character: str
    characters: list
    scenes: list = field(default_factory=list)
    # 화자가 이미 알고 있는 미래. Narrator 가 가끔 흘려 회고의 아이러니를 만든다.
    narrator_foreknowledge: list = field(default_factory=list)
    # 문장의 색. 씨앗이 정하고 화자 프롬프트가 실행한다 -- 세계마다 문체가 달라야
    # 200화를 넘겨도 같은 목소리로 수렴하지 않는다.
    voice: str = ""
    # 확립된 사실 원장. 모순 검사의 기준이 된다.
    facts: dict = field(default_factory=dict)
    # 관계 원장의 **캐시**. 진실은 씬의 relation_ops 이고 derive_relations() 가 도출한다.
    # 저장해 두는 것은 사람이 JSON 을 열어봤을 때 읽히게 하려는 것뿐이다.
    relations: list = field(default_factory=list)
    # 설정 원장. gate.V010 이 검증한다.
    fact_log: list = field(default_factory=list)
    # 동적 게이트의 **캐시**. 진실은 씬의 world_ops 이고 derive_gates() 가 도출한다.
    dynamic_gates: list = field(default_factory=list)
    # 공리 개정 예산. 무제한이면 제약이 없는 것과 같다.
    revision_budget: int = 2

    # ---- 영속 ----
    @staticmethod
    def load(path) -> "Novel":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return Novel(
            title=raw["title"], pov_character=raw["pov_character"],
            characters=[Character(**c) for c in raw["characters"]],
            scenes=[Scene(**{**s, "turns": [Turn(**t) for t in s.get("turns", [])]})
                    for s in raw.get("scenes", [])],
            narrator_foreknowledge=raw.get("narrator_foreknowledge", []),
            voice=raw.get("voice", ""),
            facts=raw.get("facts", {}),
            relations=[Relation(**r) for r in raw.get("relations", [])],
            fact_log=[Fact(**f) for f in raw.get("fact_log", [])],
            dynamic_gates=[DynamicGate(**g) for g in raw.get("dynamic_gates", [])],
            revision_budget=raw.get("revision_budget", 2))

    def timeline(self, upto_idx: int = None) -> tuple:
        """어느 씬이 **지금 시간선에 남아 있는가**, 그리고 누가 기억을 갖고 넘어왔는가.

        반환 (살아 있는 씬 인덱스 집합, 기억을 나른 사람 -> 지워진 씬 인덱스 집합).

        **이것이 시간 되감기의 모순을 없애는 자리다.** misbelieve 가 진실과 믿음을 갈라
        "설윤은 X 를 믿는데 사실은 Y" 를 모순이 아니게 만든 것과 같은 수법이다. 여기서는
        시간선을 좌표로 준다 -- 지워진 씬에서 일어난 일은 이 시간선에 없으므로, "그 관계가
        시작됐다" 와 "그런 적 없다" 가 동시에 참일 수 있다.

        carry 가 심장이다. 되감은 사람만 지워진 구간의 기억을 갖고 넘어오고, 그 비대칭이
        정보 격차를 통째로 만든다 -- 그가 아는 것을 아무도 모르는 상태가 곧 서스펜스다.
        """
        end = len(self.scenes) - 1 if upto_idx is None else upto_idx
        erased: set = set()
        carried: dict = {}
        for i in range(max(0, end + 1)):
            for op in (self.scenes[i].world_ops or []):
                if not isinstance(op, dict) or op.get("event") != "rewind":
                    continue
                back = self.scene_index(str(op.get("back_to") or ""))
                if back < 0:
                    back = i                      # 대상을 못 찾으면 이 씬만 지운다
                span = set(range(back, i + 1))
                erased |= span
                for who in (op.get("carry") or []):
                    carried.setdefault(who, set()).update(span)
        live = {i for i in range(max(0, end + 1)) if i not in erased}
        return live, carried

    def derive_gates(self, upto_idx: int = None) -> tuple:
        """씬의 world_ops 에서 동적 게이트를 생성한다. 반환 (게이트 목록, 문제 목록).

        **디스패치는 verbs.VERBS 레지스트리에서 한다.** 처음엔 여기에 if/elif 로 사건 이름을
        박아뒀는데, 카탈로그를 52개로 늘리자 die 가 게이트를 하나도 안 낳고 조용히 통과했다
        -- 검증이 있는 척만 하는 상태였다. 표를 늘릴 때 여기가 따라오지 않으면 그 구멍은
        보이지 않으므로, 출처를 하나로 묶고 **미구현은 시끄럽게** 만든다.

        **모델은 동사를 선언할 뿐 규칙을 쓰지 않는다.** 어떤 게이트가 붙는지는 표가 정한다."""
        from . import verbs as V
        end = len(self.scenes) - 1 if upto_idx is None else upto_idx
        gates, problems, n, spent = [], [], 0, 0
        # 되감기로 지워진 씬의 사건은 **이 시간선에 없다.** 그것을 게이트로 만들면
        # 일어나지 않은 일이 이후 씬을 계속 기각한다 -- 되감기가 서사 장치가 아니라
        # 오류 발생기가 된다.
        live, _ = self.timeline(end)

        for idx in range(max(0, end + 1)):
            if idx not in live:
                continue
            sc = self.scenes[idx]
            for op in sc.world_ops or []:
                bad = V.validate_op(op)          # 객체가 아니면 위반으로 보고하고 넘어간다
                if bad:
                    problems.append(("hard", sc.id, "; ".join(bad)))
                    continue
                verb = op["event"]
                spec = V.VERBS[verb]

                # 인물 인자는 실재해야 한다. 표를 믿되 값은 확인한다.
                names = {c.name for c in self.characters}
                for key in ("who", "target", "truth_who", "blamed_who", "center", "to",
                            "from_whom", "against", "toward", "as_whom"):
                    val = op.get(key)
                    if isinstance(val, str) and key in spec["params"] and val not in names:
                        problems.append(("hard", sc.id,
                                         f"'{verb}' 의 {key}={val!r} 가 등장인물에 없다"))
                for key in ("pair", "members", "witnesses", "who", "believed_by", "to"):
                    val = op.get(key)
                    if isinstance(val, list) and key in spec["params"]:
                        miss = [x for x in val if x not in names]
                        if miss:
                            problems.append(("hard", sc.id,
                                             f"'{verb}' 의 {key} 에 없는 인물: {miss}"))

                if spec["budget"]:
                    spent += 1

                n += 1
                gates.append(DynamicGate(
                    rule=f"D{n:03d}", kind=spec["gate"],
                    params={k: v for k, v in op.items() if k != "event"},
                    from_scene=sc.id, origin=f"{sc.id}: {verb}",
                    severity="soft" if spec["gate"] in SOFT_GATES else "hard"))

                if spec["gate"] not in IMPLEMENTED_GATES:
                    # 미구현을 침묵시키지 않는다. 표에만 있고 검사기가 없는 규칙은
                    # 있는 척하는 규칙이라 그 자체가 위험하다.
                    problems.append(("soft", sc.id,
                                     f"'{verb}' 의 게이트 '{spec['gate']}' 는 아직 "
                                     f"검사기가 없다 -- 선언은 기록되지만 강제되지 않는다"))

        if spent > self.revision_budget:
            problems.append(("hard", self.scenes[min(end, len(self.scenes) - 1)].id,
                             f"공리 개정 예산 초과: {spent}회 사용, 한도 "
                             f"{self.revision_budget}회. 무제한 개정은 제약이 없는 것과 "
                             f"같아서 환각과 반전을 구분할 수 없게 만든다"))
        return gates, problems

    def granted_knowledge(self, upto_scene: str) -> dict:
        """공개 사건으로 확장된 지식. {용어: [아는 인물...]} 을 덮어쓰기가 아니라 합집합으로."""
        idx = self.scene_index(upto_scene)
        gates, _ = self.derive_gates(idx)
        out = {}
        for g in gates:
            if g.kind == "knowledge_grant" and self.scene_index(g.from_scene) <= idx:
                out.setdefault(g.params["term"], []).extend(g.params.get("to", []))
        return out

    def sync_gates(self):
        self.dynamic_gates, _ = self.derive_gates()
        return self.dynamic_gates

    def sync_relations(self):
        """캐시를 도출값으로 갱신한다. save() 전에 부른다."""
        self.relations, _ = self.derive_relations()
        return self.relations

    def save(self, path):
        self.sync_relations()
        self.sync_gates()
        Path(path).write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2),
                              encoding="utf-8")

    def character(self, name: str) -> Character:
        for c in self.characters:
            if c.name == name:
                return c
        raise KeyError(name)

    def scene(self, sid: str) -> Scene:
        for s in self.scenes:
            if s.id == sid:
                return s
        raise KeyError(sid)

    def next_pending(self):
        """아직 verified 가 아닌 첫 씬. 소설은 선형이라 DAG 가 아니라 시퀀스다."""
        for s in self.scenes:
            if s.status != "verified":
                return s
        return None

    def others(self, name: str) -> list:
        return [c.name for c in self.characters if c.name != name]

    def scene_index(self, sid: str) -> int:
        for i, s in enumerate(self.scenes):
            if s.id == sid:
                return i
        return -1

    def derive_relations(self, upto_idx: int = None) -> tuple:
        """씬의 relation_ops 를 순서대로 적용해 관계 타임라인을 만든다.

        **단일 출처는 씬의 relation_ops 다.** self.relations 를 따로 들고 있으면 둘이
        어긋나는 순간 어느 쪽이 진실인지 알 수 없게 된다 -- 모순을 잡으려고 만든 원장이
        모순의 출처가 되는 꼴이다. 그래서 저장은 캐시일 뿐이고 판단은 항상 여기서 한다.

        반환 (관계 목록, 문제 목록). 문제는 (등급, 씬 id, 설명) 튜플이라 gate 에 의존하지
        않는다 -- 상태 계층이 심판 계층을 임포트하면 순환이 된다."""
        end = len(self.scenes) - 1 if upto_idx is None else upto_idx
        rels, problems = [], []
        names = {c.name for c in self.characters}

        # 관계 동사가 world_ops 로 선언될 수도 있다(start_romance / marry / end_romance
        # / divorce / bind). 두 출처가 서로를 모르면 원장이 반쪽이 된다 -- 관계 타임라인의
        # 출처를 하나로 모았던 것과 같은 병이라 여기서 합쳐서 읽는다.
        WORLD_TO_REL = {"start_romance": ("start", "연인"), "end_romance": ("end", "연인"),
                        "marry": ("start", "배우자"), "divorce": ("end", "배우자"),
                        "unrequited": ("start", "짝사랑")}

        def rel_ops_of(sc):
            # **객체가 아닌 항목은 여기서 걸러낸다.** LLM 이 ops 를 문자열 목록으로 낼 때가
            # 있는데, 그러면 아래 w.get 이 'str' object has no attribute 'get' 로 터진다.
            # 이 함수는 save() 안에서 불리므로 여기서 죽으면 **원고 저장이 통째로 실패한다**
            # -- 2026-09-03 밤샘 런이 그렇게 결말 블록을 잃었다. 잘못된 항목은 관계를
            # 만들지 못할 뿐이고, 그것이 위반이라는 사실은 derive_gates 가 따로 보고한다.
            out = [o for o in (sc.relation_ops or []) if isinstance(o, dict)]
            for w in sc.world_ops or []:
                if not isinstance(w, dict):
                    continue
                m = WORLD_TO_REL.get(w.get("event"))
                if not m:
                    continue
                members = list(w.get("pair") or ([w.get("who"), w.get("toward")]
                                                 if w.get("who") else []))
                if len(members) == 2 and all(members):
                    out.append({"op": m[0], "kind": w.get("kind") or m[1],
                                "members": members})
            return out

        live, _ = self.timeline(end)
        for idx in range(max(0, end + 1)):
            if idx not in live:
                continue                      # 지워진 씬의 관계 변화는 없던 일이다
            sc = self.scenes[idx]
            for op in rel_ops_of(sc):
                kind, members = op.get("kind", ""), list(op.get("members", []))
                bad = [m for m in members if m not in names]
                if bad:
                    problems.append(("hard", sc.id, f"등장인물에 없는 인물의 관계: {bad}"))
                    continue
                if len(members) != 2 or members[0] == members[1]:
                    problems.append(("hard", sc.id,
                                     f"관계 구성원이 두 사람이 아니다: {members}"))
                    continue
                key = (kind, tuple(members) if kind in DIRECTED_KINDS
                       else tuple(sorted(members)))

                if op.get("op") == "start":
                    if any(r.key() == key and not r.until for r in rels):
                        problems.append(("hard", sc.id,
                                         f"이미 진행 중인 관계를 다시 시작했다: "
                                         f"{kind} {members}"))
                        continue
                    # 배타성. "A 와 B 가 사귀는데 어느 순간 C 가 A 와 사귄다" 를 잡는 자리.
                    if kind in EXCLUSIVE_KINDS:
                        for m in members:
                            cur = next((r for r in rels if r.kind == kind
                                        and not r.until and m in r.members), None)
                            if cur:
                                other = next(x for x in cur.members if x != m)
                                problems.append((
                                    "hard", sc.id,
                                    f"{m} 은(는) {cur.since} 부터 {other} 와(과) "
                                    f"'{kind}' 인데 끝내지 않고 {members} 로 새 '{kind}' 를 "
                                    f"시작했다. 먼저 end 로 닫고 그 이별 장면을 남겨라"))
                    rels.append(Relation(kind=kind, members=members, since=sc.id))

                elif op.get("op") == "end":
                    cur = next((r for r in rels if r.key() == key and not r.until), None)
                    if cur is None:
                        problems.append(("hard", sc.id,
                                         f"시작한 적 없는 관계를 끝냈다: {kind} {members}"))
                        continue
                    cur.until = sc.id
                else:
                    problems.append(("hard", sc.id,
                                     f"알 수 없는 op: {op.get('op')!r} (start/end 만 허용)"))
        return rels, problems

    def active_relations(self, upto_scene: str = None) -> list:
        """해당 씬 시점에 살아 있는 관계들."""
        idx = None if upto_scene is None else self.scene_index(upto_scene)
        rels, _ = self.derive_relations(idx)
        return [r for r in rels if not r.until]

    def partner(self, name: str, kind: str = "연인", upto_scene: str = None):
        for r in self.active_relations(upto_scene):
            if r.kind == kind and name in r.members:
                return next(m for m in r.members if m != name)
        return None
