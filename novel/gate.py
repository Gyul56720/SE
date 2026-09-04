"""기계적 관문 -- LLM 을 쓰지 않는다. 위반 목록을 돌려준다.

원 설계의 Critic 은 LLM 이 LLM 출력을 주관적으로 평가하고 롤백을 결정했다. mathgen/README
가 그것을 하지 말라고 적어둔 바로 그 구조다(DeepMind, LLMs Cannot Self-Correct Reasoning
Yet -- 내재적 자기교정은 개선이 없거나 성능을 떨어뜨린다).

여기서 하는 일은 **판정을 둘로 가르는 것**이다:

    기계 관문 (이 파일)  -- 결정적으로 판정되는 것만. 하드 위반은 기각 권한을 갖는다.
    LLM 비평가          -- "하루키다운가" 같은 취향. **자문만 한다. 기각 권한이 없다.**

반환은 (bool, str) 이 아니라 **위반 목록**이다. gates/__init__.py 의 규약을 그대로 떼왔다.
이유: 소설에서 "실패했다" 는 수리 신호가 못 된다. 어느 규칙이 어디서 왜 깨졌는지가 있어야
Director 와 Actor 에게 되먹일 것이 생긴다. 직선거리 심판이 "22.5% 더 짧은 점이 있다" 고
짚어줘서 쓸모가 있었던 것과 같다.

severity:
    hard -- 확실한 위반. 씬을 기각한다.
    soft -- 의심스럽다. 기록하고 수리 프롬프트에 실지만 기각하지는 않는다.

관문은 **모순만** 본다 (2026-09-04 축소). 세계가 자기모순인가 -- 모르는 것을 말하는가,
관계·설정이 어긋나는가, 없는 것을 요구하는가, 화자가 보지 못한 것을 서술하는가, 시계가
되감기는가. 이것들은 취향이 아니라 사실이라 기계가 판정할 자격이 있다.

취향에 속하는 검사는 전부 뺐다 -- 시점 위반(V004), 감정 급변/폭(V002·V003),
직접 감정 서술(V005),
푼크툼(V006), 시퀀스 궤도·꺾임·규모(V013~V015), 정보 격차(V016), 클리프행어(V017),
회차 분량(V019), 문장 리듬(V020), 능동성(V022), 회차가 여는가(V025). 이유는 두 가지다:
(1) 그것들은 "무엇이 좋은 소설인가" 에 대한 이 파일의 의견이었지 모순이 아니다.
(2) 실측에서 되돌려보내기 1·2위(V003 25회, V009 16회)가 산문 수리로 고칠 수 없는
    선언 문제였고, 집필 시간의 100% 가 수리에 갔다. 관문이 작가가 되면 그 자리를
    통과하려고 원고가 균질해진다. 재미는 씨앗과 디렉터 시나리오가 만든다.
남은 규율(분량·리듬·푼크툼 등)은 프롬프트와 조립 단계의 강제로 남아 있다 -- 기각 권한만
없앤 것이다.

soft 를 따로 둔 이유가 있다. **과잉 기각하는 심판은 맞는 답도 버린다** -- 직선거리에서
상대 임계만 쓰다가 진짜 최소가 0 일 때 정답을 기각한 것이 그 사례다. 한국어 패턴 검사는
정밀도가 100% 가 아니므로, 애매한 것은 기각이 아니라 보고로 내린다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


_SENT = re.compile(r"[^.!?…\n]+[.!?…]?")
_QUOTED = re.compile(r"[\"“”][^\"“”]*[\"“”]|'[^']*'|「[^」]*」")


@dataclass
class Violation:
    rule: str
    severity: str        # "hard" | "soft"
    where: str
    detail: str

    def __str__(self):
        return f"[{self.rule}/{self.severity}] {self.where}: {self.detail}"


def _strip_quotes(text: str) -> str:
    """대사를 지운다. 서술만 남겨서 검사한다."""
    return _QUOTED.sub(" ", text)


def _sentences(text: str) -> list:
    return [s.strip() for s in _SENT.findall(text) if s.strip()]


# ---------------------------------------------------------------- 개별 검사

def check_turn_format(scene, novel) -> list:
    """V001 -- Actor 턴의 형식. 파싱이 깨진 것을 문학적 판단에 넘기지 않는다."""
    out = []
    from .state import AXES, BIPOLAR
    for i, t in enumerate(scene.turns):
        w = f"턴 {i}({t.actor})"
        if t.actor not in [c.name for c in novel.characters]:
            out.append(Violation("V001", "hard", w, f"등장인물 목록에 없는 화자: {t.actor!r}"))
        if not (t.speech or t.action or t.inner_thought):
            out.append(Violation("V001", "hard", w, "speech/action/inner_thought 가 모두 비었다"))
        for a in AXES:
            if a not in t.emotions:
                out.append(Violation("V001", "hard", w, f"감정 축 '{a}' 누락"))
                continue
            v = t.emotions[a]
            lo = -100 if a in BIPOLAR else 0
            if not isinstance(v, int) or not (lo <= v <= 100):
                out.append(Violation("V001", "hard", w,
                                     f"'{a}'={v!r} 가 범위 [{lo},100] 밖이거나 정수가 아니다"))
    return out


def check_pov_presence(scene, novel) -> list:
    """V007 -- 화자가 없는 씬. 1인칭 회고는 이것을 직접 서술할 수 없다.

    원 설계에 이 구멍이 있었다. Actor 들이 자율 상호작용하면 화자가 없는 씬이 필연적으로
    생기는데, 그것을 1인칭으로 쓸 방법이 없다. 해답은 문서가 이미 갖고 있었다 -- 편지 모드다.
    원작이 나오코의 요양원을 편지와 레이코의 입을 통해 전달하는 것과 같다."""
    if novel.pov_character in scene.participants:
        return []
    if scene.mode in ("letter", "reported"):
        return []
    return [Violation("V007", "hard", f"씬 {scene.id}",
                      f"화자 '{novel.pov_character}' 가 참여하지 않는데 mode 가 "
                      f"'{scene.mode}' 다. letter 또는 reported 로 세탁하라")]


def _secret_spec(v):
    """secrets 값의 두 형태를 하나로. ["B","D"] 또는 {"knows":[...], "aliases":[...]}"""
    if isinstance(v, dict):
        return list(v.get("knows") or []), list(v.get("aliases") or [])
    return list(v or []), []


def check_knowledge(scene, novel) -> list:
    """V008 -- 지식 누출. 인물이 자기가 모르는 것을 말하거나 **생각한다.**

    처음엔 speech 와 action 만 봤다. 첫 실측 런에서 그 구멍이 그대로 드러났다 -- A 가 모르는
    '교환학생 지원서' 를 inner_thought 에서 언급했고, Narrator 가 그것을 산문으로 옮겨
    "지원서 얘기라도 꺼낼 참일 것이다" 가 나왔는데 관문은 통과시켰다.

    **inner_thought 는 서술의 재료다. 거기서 새면 산문에서 샌다.** 산문 자체도 화자의 것이므로
    화자가 모르는 것이 서술되면 같은 누출이다. 그래서 셋 다 본다.

    별칭도 같은 런에서 필요해졌다. 비밀이 '교환학생 지원서' 인데 텍스트에는 '지원서' 로만 나오면
    정확 일치로는 안 걸린다. 별칭은 작가가 명시적으로 등록하는 것이라 hard 로 둔다 -- 등록했다는
    것 자체가 그 말이 이 비밀을 가리킨다는 선언이다."""
    out = []
    for term, spec in (novel.facts.get("secrets", {}) or {}).items():
        _, aliases = _secret_spec(spec)
        knowers = _knowers(novel, term, scene.id)
        needles = [n for n in [term] + aliases if n]

        for i, t in enumerate(scene.turns):
            if t.actor in knowers:
                continue
            for field, txt in (("speech", t.speech), ("action", t.action),
                               ("inner_thought", t.inner_thought)):
                hit = next((n for n in needles if n in (txt or "")), None)
                if hit:
                    verb = "생각했" if field == "inner_thought" else "말했"
                    tail = ("속마음은 서술의 재료라 여기서 새면 산문에서 샌다. "
                            if field == "inner_thought" else "")
                    out.append(Violation(
                        "V008", "hard", f"턴 {i}({t.actor}) {field}",
                        f"'{hit}' 를 {verb}지만 이 인물은 '{term}' 를 모른다 "
                        f"(아는 인물: {sorted(knowers)}). {tail}"
                        f"알아야 한다면 먼저 reveal 이 있어야 한다"))

        # 산문은 화자의 것이다. 화자가 모르는 것이 서술되면 같은 누출이다.
        if scene.prose and novel.pov_character not in knowers:
            hit = next((n for n in needles if n in scene.prose), None)
            if hit:
                out.append(Violation(
                    "V008", "hard", f"씬 {scene.id} 서술부",
                    f"산문이 '{hit}' 를 언급하지만 화자 {novel.pov_character} 는 "
                    f"'{term}' 를 모른다 (아는 인물: {sorted(knowers)})"))
    return out


def check_relations(scene, novel) -> list:
    """V009 -- 관계 모순.

    두 층으로 본다.
      1. **원장 자체의 무모순** -- 배타성, 시작 없는 종료, 중복 시작. 결정적이라 hard 다.
         도출 자체는 state.Novel.derive_relations 가 하고 여기서는 위반으로 옮기기만 한다.
      2. **산문이 원장과 어긋나는가** -- 한국어 패턴이라 정밀도가 100% 가 아니므로 soft 다.

    1층이 핵심이다. 관계 변화를 구조화된 op 로 선언하게 만들면, "어느 순간 C 가 A 와
    사귄다" 는 산문을 읽지 않고도 잡힌다."""
    idx = novel.scene_index(scene.id)
    if idx < 0:
        return []
    # 도출은 state 가 한다 -- 관계 타임라인 구현이 둘이면 그 둘이 어긋날 수 있다.
    rels, problems = novel.derive_relations(idx)
    out = [Violation("V009", sev, f"씬 {sid}", msg) for sev, sid, msg in problems]

    # --- 2층: 산문이 원장과 다른 짝을 연인으로 말하는가
    if scene.prose:
        from .state import EXCLUSIVE_KINDS
        text = _strip_quotes(scene.prose)
        active = {r.key(): r for r in rels
                  if r.kind in EXCLUSIVE_KINDS and not r.until}
        names = [c.name for c in novel.characters]
        for i, x in enumerate(names):
            for y in names[i + 1:]:
                near = re.search(
                    rf"{re.escape(x)}[^.!?\n]{{0,40}}{re.escape(y)}[^.!?\n]{{0,40}}"
                    rf"(사귀|연인|애인|여자친구|남자친구)", text) or re.search(
                    rf"{re.escape(y)}[^.!?\n]{{0,40}}{re.escape(x)}[^.!?\n]{{0,40}}"
                    rf"(사귀|연인|애인|여자친구|남자친구)", text)
                if not near:
                    continue
                if not any(set(k[1]) == {x, y} for k in active):
                    p1 = novel.partner(x, upto_scene=scene.id)
                    out.append(Violation(
                        "V009", "soft", f"씬 {scene.id} 서술부",
                        f"산문이 {x}·{y} 를 연인으로 말하는데 원장에 그 관계가 없다"
                        + (f" ({x} 의 현재 상대는 {p1})" if p1 else "")))
    return out


def check_facts(scene, novel) -> list:
    """V010 -- 설정 모순. 같은 키가 다른 값으로 재선언되는 것을 잡는다.

    설정은 바뀔 수 있다(전학, 이직). 그래서 **변경 자체**를 막지 않고, 같은 씬 안에서
    한 키가 두 값을 갖는 것과 원장에 없는 값이 산문에 나오는 것을 본다."""
    out = []
    idx = novel.scene_index(scene.id)
    if idx < 0:
        return out

    seen = {}
    for op in scene.fact_ops or []:
        k, v = op.get("key"), op.get("value")
        if k in seen and seen[k] != v:
            out.append(Violation("V010", "hard", f"씬 {scene.id}",
                                 f"'{k}' 가 한 씬 안에서 {seen[k]!r} 와 {v!r} 두 값을 갖는다"))
        seen[k] = v

    # 이전까지 확립된 값과 다른 값을 **이별 없이** 덮어쓰면 보고한다(변경은 허용하되 눈에 띄게).
    established = {}
    for i in range(idx):
        for op in novel.scenes[i].fact_ops or []:
            established[op.get("key")] = (op.get("value"), novel.scenes[i].id)
    for k, v in seen.items():
        if k in established and established[k][0] != v:
            out.append(Violation("V010", "soft", f"씬 {scene.id}",
                                 f"'{k}' 가 {established[k][1]} 의 {established[k][0]!r} 에서 "
                                 f"{v!r} 로 바뀐다. 의도한 변화라면 그 계기가 서술에 있어야 한다"))
    return out


def _knowers(novel, term: str, upto_scene: str) -> set:
    """해당 시점에 term 의 **진실**을 아는 인물 집합."""
    raw = (novel.facts.get("secrets", {}) or {}).get(term, [])
    out = set(raw.get("knows", []) if isinstance(raw, dict) else raw)
    for c in novel.characters:
        if term in (c.knows or []):
            out.add(c.name)
    idx = novel.scene_index(upto_scene)
    gates, _ = novel.derive_gates(idx)
    # **기억을 갖고 넘어온 사람은 지워진 구간의 것도 안다.** 그 비대칭이 이 장치의 요점이다
    # -- 그가 아는 것을 아무도 모르는 상태가 곧 정보 격차이고, 그것을 지식 누출로 잡으면
    # 되감기 서사가 통째로 성립하지 않는다.
    live, carried = novel.timeline(idx)
    for who, span in carried.items():
        for j in span:
            if j > idx:
                continue
            for op in (novel.scenes[j].world_ops or []):
                if not isinstance(op, dict) or op.get("term") != term:
                    continue
                if op.get("event") in ("reveal", "overhear", "secret_pact"):
                    out.add(who)
    for g in gates:
        if novel.scene_index(g.from_scene) > idx:
            continue
        if g.kind in ("knowledge_grant", "knowledge_grant_covert") \
                and g.params.get("term") == term:
            out.update(g.params.get("to") or ([g.params["who"]]
                                              if g.params.get("who") else []))
        if g.kind == "knowledge_revoke" and g.params.get("term") == term:
            out.discard(g.params.get("who"))
    return out


def check_belief(scene, novel) -> list:
    """V011 -- 믿음과 사실의 분리. **이 관문의 절반은 막는 것이 아니라 허용하는 것이다.**

    misbelieve 가 없으면 인물의 오해가 전부 환각으로 잡힌다. 세계가 모순된 것과 인물이
    틀린 것은 완전히 다른데 텍스트만 보면 똑같이 생겼다. 그래서 여기서 보는 것은
    '인물이 틀린 말을 했는가' 가 아니라 **'그 틀림이 선언된 것인가'** 다.

    잡는 것 셋:
      · 오해하는 인물이 진실을 입에 올린다 -- 그는 그것을 모른다
      · 정정(reveal)된 뒤에도 같은 오해를 계속한다 -- 오해에도 수명이 있다
      · 누명 구조에서 진실을 모르는 인물이 진범을 지목한다
    """
    out = []
    idx = novel.scene_index(scene.id)
    if idx < 0:
        return out
    gates, _ = novel.derive_gates(idx)
    truths = novel.facts.get("truths", {})

    active_belief = {}          # (인물, term) -> {"believes":..., "since": 씬}
    for g in gates:
        if g.kind != "belief" or novel.scene_index(g.from_scene) > idx:
            continue
        pr = g.params
        if "who" in pr:                                   # misbelieve
            active_belief[(pr["who"], pr.get("term"))] = {
                "believes": pr.get("believes", ""), "since": g.from_scene}
        elif "truth_who" in pr:                           # blame_transfer
            term = pr.get("term")
            for c in novel.characters:
                if c.name not in _knowers(novel, term, scene.id):
                    active_belief[(c.name, term)] = {
                        "believes": f"{pr.get('blamed_who')} 가 했다",
                        "since": g.from_scene, "hides": pr.get("truth_who")}

    for i, t in enumerate(scene.turns):
        text = f"{t.speech} {t.action}"
        for (who, term), b in active_belief.items():
            if who != t.actor or not term:
                continue
            # 1) 진실을 입에 올린다
            truth = truths.get(term)
            if truth and truth in text:
                out.append(Violation("V011", "hard", f"턴 {i}({t.actor})",
                                     f"'{term}' 의 진실({truth!r})을 말했지만 이 인물은 "
                                     f"{b['since']} 부터 다르게 믿고 있다. 오해를 풀려면 "
                                     f"먼저 reveal 이 있어야 한다"))
            # 2) 누명: 진실을 모르는 인물이 진범을 지목한다
            hides = b.get("hides")
            if hides and hides in text and term in text:
                out.append(Violation("V011", "hard", f"턴 {i}({t.actor})",
                                     f"'{term}' 에 대해 {hides} 를 지목했지만 이 인물은 "
                                     f"진실을 모른다"))
            # 3) 정정된 뒤에도 계속되는 오해
            if who in _knowers(novel, term, scene.id) and b["believes"] \
                    and b["believes"] in text:
                out.append(Violation("V011", "hard", f"턴 {i}({t.actor})",
                                     f"이미 '{term}' 의 진실을 알게 된 뒤인데 예전 오해"
                                     f"({b['believes']!r})를 그대로 말한다. 오해에도 수명이 "
                                     f"있다 -- 계속하려면 그럴 이유가 서술에 있어야 한다"))
    return out


def check_public_fiction(scene, novel) -> list:
    """V012 -- 공개된 허구. fabricate / assume_identity / expose 의 구조를 본다.

    개츠비의 옥스퍼드가 이 구조다. 세계의 진실과 공개된 이야기가 갈라진 채 유지되고,
    그 간극이 서사의 엔진이 된다. 기계가 볼 수 있는 것은 **간극이 선언대로 유지되는가** 다.

    구조 검사(hard)는 결정적이고, 텍스트 검사(soft)는 한국어 패턴이라 보고만 한다."""
    out = []
    idx = novel.scene_index(scene.id)
    if idx < 0:
        return out
    gates, _ = novel.derive_gates(idx)

    fictions, exposed = {}, {}
    for g in gates:
        if novel.scene_index(g.from_scene) > idx:
            continue
        if g.kind == "public_fiction":
            pr = g.params
            story = pr.get("story") or pr.get("as_whom")
            if not story:
                continue
            if story in fictions:
                out.append(Violation("V012", "hard", f"씬 {g.from_scene}",
                                     f"'{story}' 를 두 번 지어냈다. 이미 "
                                     f"{fictions[story]['since']} 에 있다"))
                continue
            teller = pr.get("who")
            believers = list(pr.get("believed_by") or [])
            if teller and teller in believers:
                out.append(Violation("V012", "hard", f"씬 {g.from_scene}",
                                     f"{teller} 가 자기가 지어낸 이야기의 believed_by 에 "
                                     f"들어 있다. 지어낸 사람은 그것을 믿지 않는다"))
            fictions[story] = {"teller": teller, "believers": believers,
                               "since": g.from_scene}
        elif g.kind == "public_fiction_break":
            story = g.params.get("story")
            if story not in fictions:
                out.append(Violation("V012", "hard", f"씬 {g.from_scene}",
                                     f"지어낸 적 없는 이야기를 폭로했다: {story!r}"))
                continue
            exposed[story] = g.from_scene

    # 텍스트: 아직 폭로되지 않았는데 믿는 사람이 이야기를 부정한다
    if scene.prose or scene.turns:
        blob = _strip_quotes(scene.prose) + " " + " ".join(
            f"{t.speech} {t.action}" for t in scene.turns)
        for story, f in fictions.items():
            if story in exposed:
                continue
            if story in blob and re.search(r"(거짓|지어낸|사실이 아니|꾸며낸)", blob):
                out.append(Violation("V012", "soft", f"씬 {scene.id}",
                                     f"'{story}' 가 아직 폭로되지 않았는데 거짓이라는 "
                                     f"말이 나온다. 폭로라면 expose 로 선언하라"))
    return out


def check_causality(scene, novel) -> list:
    """V018 -- 개연성 사슬. **플롯 구멍을 그래프 도달 가능성으로 잡는다.**

    보고서: 에피소드는 결과를 먼저 정하고 인과를 역방향으로 조립한다. 그 조립이 실제로
    성립하는지는 비트마다 requires/establishes 를 선언하게 하면 기계가 판정한다:

        구멍 = 어떤 씬의 requires 가 앞선 어떤 establishes 로도, 원장으로도 충족되지 않는 것

    사람이 읽고 "어색하다" 고 느끼는 것을 "48화의 요구 'A가 열쇠를 갖고 있다' 가 아무 데서도
    성립되지 않는다" 로 짚는다. 200화에서 이것 없이 순방향으로 쓰면 뒤로 갈수록 앞을 기억하지
    못해 구멍이 쌓인다.

    맨 문자열은 오타가 곧 구멍이 된다. 그게 맞다 -- 조용히 통과하는 것보다 시끄럽게 틀리는
    편이 낫다. 다만 비슷한 것이 있으면 오타로 짚어 soft 로 낮춘다."""
    import difflib
    from .episode import eval_state
    out = []
    idx = novel.scene_index(scene.id)
    if idx < 0 or not scene.requires:
        return out

    have = set()
    for i in range(idx):
        have.update(novel.scenes[i].establishes or [])

    for cond in scene.requires:
        if cond.startswith("state:"):
            try:
                if eval_state(cond, novel, scene.id):
                    continue
                out.append(Violation("V018", "hard", f"씬 {scene.id}",
                                     f"요구 {cond!r} 를 원장이 만족하지 않는다"))
            except ValueError as e:
                out.append(Violation("V018", "hard", f"씬 {scene.id}", str(e)))
            continue
        if cond in have:
            continue
        near = difflib.get_close_matches(cond, have, n=1, cutoff=0.75)
        if near:
            out.append(Violation("V018", "soft", f"씬 {scene.id}",
                                 f"요구 {cond!r} 가 충족되지 않았지만 비슷한 것이 있다: "
                                 f"{near[0]!r} -- 오타이면 맞춰라"))
        else:
            out.append(Violation("V018", "hard", f"씬 {scene.id}",
                                 f"요구 {cond!r} 를 성립시키는 씬이 앞에 없다. "
                                 f"**개연성 구멍이다** -- 이것을 세우는 씬을 먼저 놓거나 "
                                 f"이 요구를 지워라"))
    return out


def check_pressure(scene, novel) -> list:
    """V023 -- 시계가 조여드는가.

    같은 마감을 공유하는 씬들 사이에서 남은 시간은 줄어들어야 한다. 늘어나면 압박이 아니라
    상황일 뿐이다. 마감 문장이 바뀌면 새 시계이므로 늘어나도 된다 -- 그것까지 벌하면
    구간이 넘어갈 때마다 걸린다(과잉 기각하는 심판은 맞는 답도 버린다).

    **soft 다.** deadline_hours 는 산문이 아니라 선언이라, 여기서 hard 로 잡으면 수리
    루프가 산문만 다시 쓰며 영원히 못 고친다. 진짜 강제는 조립 시점
    (drive._check_pressure)에서 되먹임으로 한다. 이 관문은 그것이 새는지 보는 눈이다."""
    if not scene.deadline_hours or not scene.deadline:
        return []
    idx = novel.scene_index(scene.id)
    earlier = [s for s in novel.scenes[:idx]
               if s.deadline == scene.deadline and s.deadline_hours]
    if not earlier:
        return []
    least = min(s.deadline_hours for s in earlier)
    if scene.deadline_hours >= least:
        return [Violation("V023", "soft", f"씬 {scene.id}",
                          f"남은 시간이 {scene.deadline_hours} 인데 앞 씬에서 이미 "
                          f"{least} 였다. 시계가 되감겼다 -- 같은 마감 안에서는 줄어야 한다")]
    return []


CHECKS = (check_turn_format, check_pov_presence,
          check_knowledge, check_relations, check_facts,
          check_belief, check_public_fiction,
          check_causality, check_pressure)


def check(scene, novel) -> list:
    """전체 관문. 위반 목록을 돌려준다. 빈 목록이면 통과."""
    out = []
    for fn in CHECKS:
        out.extend(fn(scene, novel))
    return out


def verdict(violations) -> tuple:
    """(통과 여부, 요약). hard 가 하나라도 있으면 기각한다."""
    hard = [v for v in violations if v.severity == "hard"]
    soft = [v for v in violations if v.severity == "soft"]
    if hard:
        return False, f"하드 위반 {len(hard)}건 (참고 soft {len(soft)}건):\n" + \
                      "\n".join(f"  {v}" for v in hard + soft)
    if soft:
        return True, f"통과 -- 다만 soft {len(soft)}건:\n" + \
                     "\n".join(f"  {v}" for v in soft)
    return True, "통과 -- 위반 없음"
