"""씬 루프 -- 기획 → 연기 → 관문 → 수리 → 서술 → 관문.

이 저장소가 배운 것 셋을 그대로 옮겼다:

  · **위반 목록이 곧 수리 프롬프트다.** (bool, str) 로는 고칠 것이 없다. 직선거리 심판이
    "22.5% 더 짧은 점이 있다" 고 짚어줘서 쓸모가 있었던 것과 같다.
  · **씬마다 즉시 저장.** 장편은 며칠 돌고 반드시 중간에 죽는다. verified 씬은 건너뛴다.
  · **scenes.jsonl 에 한 줄씩.** 도는 중에 보이고 죽어도 남는다(solve.py 의 rounds.jsonl).

LLM 은 주입한다. llm(prompt) -> str 하나면 되고, 기본값은 llm_pool 이다. 주입 가능해야
가짜 LLM 으로 루프 자체를 시험할 수 있다 -- test_planner_repair.py 가 쓰는 수다.
"""
from __future__ import annotations

import json
import re
import os as _os
import sys as _sys
import time
from pathlib import Path

from . import gate
from .state import AXES, Scene, Turn
from .verbs import catalog_for_prompt

MAX_REPAIRS = 3


def _log(msg: str) -> None:
    """진행 상황을 stderr 로. 산출물(stdout)과 섞이지 않게 한다."""
    print(msg, file=_sys.stderr, flush=True)
# 프롬프트를 캐시 가능한 고정부와 매번 바뀌는 부분으로 가르는 표식. 캐싱은 접두사 일치라
# 이 경계가 있어야 고정부를 통째로 캐시할 수 있다.
SPLIT = "\n<<<VOLATILE>>>\n"


def _llm_for(llm, role: str):
    """llm 이 dict 면 역할별로 고른다. 호출자가 director 만 Claude 로 돌릴 수 있게."""
    if isinstance(llm, dict):
        return llm.get(role) or llm.get("default") or default_llm
    return llm


# ---------------------------------------------------------------- LLM 어댑터

def anthropic_llm(model: str = "claude-opus-5", effort: str = "high",
                  workspace_id: str = None):
    """역할 하나를 Claude 로 돌린다. author(director)에 쓰라고 만든 것이다.

    왜 director 만인가. 실측 프롬프트 기준 director 는 호출 6회 중 1회이고 출력이 300 토큰
    남짓이라 **전체 토큰의 일부**인데, 플롯의 재미는 전부 거기서 갈린다. 100만자 한 편에서
    director 를 Haiku 대신 Opus 로 올리는 비용 차이가 몇 달러다 -- 아낄 자리가 아니다.

    캐싱: 카탈로그·페르소나·규칙은 매 씬 동일하므로 system 으로 올려 캐시한다. 캐시는 접두사
    일치라 **바뀌는 것(씬 씨앗·되먹임)은 반드시 뒤에** 와야 한다. 프리픽스가 1바이트라도
    흔들리면 캐시가 통째로 무효화된다."""
    import anthropic
    # identity-linked API key 는 어느 워크스페이스에서 도는 요청인지 헤더로 알려줘야 한다
    # (400: anthropic-workspace-id is required...). 워크스페이스 전용 키는 필요 없다.
    ws = workspace_id or _os.environ.get("ANTHROPIC_WORKSPACE_ID") or ""
    headers = {"anthropic-workspace-id": ws} if ws else None
    client = anthropic.Anthropic(default_headers=headers)
    stats = {"calls": 0, "write": 0, "read": 0, "fresh": 0, "out": 0}

    def call(prompt: str) -> str:
        stable, _, volatile = prompt.partition(SPLIT)
        r = client.messages.create(
            model=model, max_tokens=16000,
            output_config={"effort": effort},
            # 고정부만 캐시한다. cache_control 은 이 블록까지를 캐시 접두사로 삼는다.
            # TTL 기본값(5분)이 맞다 -- 씬 하나가 1분 남짓이라 다음 호출이 항상 5분 안에
            # 시작하고, 읽기가 타이머를 공짜로 갱신해 무한히 따뜻하게 유지된다.
            system=[{"type": "text", "text": stable,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": volatile or prompt}])
        if r.stop_reason == "refusal":
            raise RuntimeError(f"거절됨: {r.stop_details}")

        # 사용량 수치를 **먼저 지역 변수로 옮긴다.** SDK 속성명이
        # cache_creation_input_tokens 라 print 안에 그대로 쓰면 G004(자격증명 노출)가
        # `*TOKEN*` 패턴으로 오탐한다 -- 토큰 '개수' 와 인증 '토큰' 을 정규식이 구분하지
        # 못한다. 게이트를 느슨하게 만들 일이 아니라 이쪽이 비켜서면 되는 문제다.
        u = r.usage
        wrote = getattr(u, "cache_creation_input_tokens", 0) or 0
        read = getattr(u, "cache_read_input_tokens", 0) or 0
        fresh, produced = u.input_tokens, u.output_tokens
        stats["calls"] += 1
        stats["write"] += wrote
        stats["read"] += read
        stats["fresh"] += fresh
        stats["out"] += produced
        # **캐시가 먹는지는 눈으로 확인해야 한다.** 최소 프리픽스(Opus 5 는 512)에 못
        # 미치거나 프리픽스가 흔들리면 오류 없이 조용히 0 이 나온다. 그래서 매번 찍는다.
        _log(f"[{model}] 호출 {stats['calls']}: 캐시쓰기 {wrote} / 캐시읽기 {read} "
             f"/ 새입력 {fresh} / 출력 {produced}")
        if stats["calls"] == 2 and stats["read"] == 0:
            _log(f"[{model}] 경고: 두 번째 호출인데 캐시 읽기가 0이다. 고정부가 최소 "
                 f"프리픽스에 못 미치거나 매번 바뀌고 있다.")
        return "".join(b.text for b in r.content if b.type == "text")

    call.stats = stats
    return call


def default_llm(prompt: str) -> str:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "orchestrator"))
    import llm_pool
    pool = llm_pool.build_pool()
    if not pool:
        raise RuntimeError("LLM 후보 풀이 비었다 -- GEMINI_API_KEY 를 설정하라")
    return llm_pool.call(pool, _flatten(prompt), pool_id="novel")[0]


def _flatten(prompt: str) -> str:
    """캐시 경계 표식을 지운다. 캐싱을 안 쓰는 경로(Gemini 등)는 통짜 프롬프트를 받는다."""
    return prompt.replace(SPLIT, "\n")


def _json(text: str) -> dict:
    """코드펜스와 앞뒤 잡소리를 벗기고 JSON 하나를 꺼낸다."""
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < 0:
        raise ValueError(f"JSON 을 찾지 못했다: {text[:120]!r}")
    return json.loads(t[i:j + 1])


# ---------------------------------------------------------------- 프롬프트

def _fb_text(msg: str) -> str:
    return f"\n\n[직전 시도가 기각된 이유 -- 같은 실수를 반복하지 마라]\n- {msg}"


def _fb(violations) -> str:
    """관문 위반을 되먹임 문단으로. **이것이 수리의 전부다.**"""
    if not violations:
        return ""
    lines = [f"- {v.rule}: {v.where} -- {v.detail}" for v in violations]
    return ("\n\n[직전 시도가 기각된 이유 -- 같은 실수를 반복하지 마라]\n"
            + "\n".join(lines))


def _world_brief(novel) -> str:
    """인물·비밀·장르 규약. **매 호출 동일하므로 캐시 고정부에 들어간다.**

    지금까지 beat_prompt 는 결말 한 줄과 열린 조건만 넘겼다. 그러면 디렉터가 누가 누구인지,
    누가 무엇을 모르는지, 이 장르가 무엇을 요구하는지 모르는 채로 장면을 짠다 -- 디렉터가
    없는 것과 다르지 않다. 재미는 이 브리핑에서 나온다."""
    who = "\n".join(
        f"  {c.name} — {c.persona}\n      숨긴 것: {c.hidden_agenda}\n"
        f"      아는 것: {c.knows}"
        for c in novel.characters)
    sec = "\n".join(
        f"  {k} — 아는 인물 {v.get('knows') if isinstance(v, dict) else v}"
        for k, v in (novel.facts.get("secrets") or {}).items())
    return f"""[화자] {novel.pov_character} (1인칭 회고. 결말을 이미 안다)

[인물]
{who}

[비밀 — 누가 무엇을 모르는가]
{sec}
  * 정보 격차가 연독률의 엔진이다. 아는 인물만 말할 수 있고, 모르는 인물이 말하면 기각된다.
  * 화자가 모르는 것은 **속으로도** 생각할 수 없다.

[이 장르의 규약]
  · 감정을 직접 쓰지 마라. 사물·소리·날씨·손이 하는 일로 옮겨라.
  · 말과 속마음 사이에 괴리를 둬라. 가까이 있어도 심리적 거리를 유지한다.
  · 남주는 결코 용서받지 못할 선을 넘지 않는다. 집착의 동기는 상처다.
  · 여주는 구조받기만 하지 않는다. 스스로 밀어낸다.
  · 위기-해결-보상의 원패턴이 노출되면 지루하다. 서브플롯이 그것을 감춘다."""


def outcome_prompt(novel, ep_lo: int, ep_hi: int, feedback="") -> str:
    """**에피소드의 결말을 먼저 받는다.** 씬을 순방향으로 뽑기 전에 도착점을 고정한다.

    순방향으로 쓰면 이야기가 배회한다 -- 각 씬이 다음 씬을 낳지만 어디로 가는지는 아무도
    모르고, 10화쯤 뒤에 "그래서 이게 왜 필요했지" 가 남는다. 결말을 먼저 정하면 모든 비트가
    그 결말에 필요해서 존재하게 되고, requires/establishes 로 그 필요를 **선언**하게 하면
    개연성이 기계 검사 대상이 된다(V018)."""
    from . import arc
    seq = arc.sequence_of(ep_lo)
    return f"""너는 1인칭 회고 웹소설의 디렉터다. **에피소드의 결말을 먼저 정한다.**

[구간] {ep_lo}~{ep_hi}화 · 시퀀스 {seq['n']} {seq['name']}
[시퀀스 목표] {seq['goal']}
[감정 단계] {seq['stage']} / narrative_pull 범위 {seq['pull']}
[인물] {', '.join(c.name for c in novel.characters)}

규칙:
- 결말은 **상태의 변화**여야 한다. "둘이 대화한다" 가 아니라 "A 가 자리를 잃는다" 처럼.
- requires 에는 그 결말이 성립하려면 이미 참이어야 하는 것을 적는다. 각 항목은 짧은
  한국어 문장 하나. 나중에 다른 비트가 이 문자열을 그대로 establishes 에 적어 갚는다.
- 원장으로 판정할 수 있는 것은 state: 접두사를 쓴다:
    state:rel:연인:A,B / state:knows:A:비밀 / state:absent:D / state:not:rel:연인:A,B
- 이 구간이 끝날 때 독자가 알고 인물은 모르는 것이 최소 하나 남아야 한다.
{feedback}

JSON 만 출력:
{{"summary": "[결말 한 문장]",
  "requires": ["...", "...", "..."],
  "world_ops": [], "relation_ops": []}}"""


def beat_prompt(novel, spec: dict, open_conds: list, ep: int, feedback="") -> str:
    """열린 요구 하나를 갚는 **한 회차 분량의 시나리오**를 받는다.

    한 줄짜리 beat 만 받으면 아래층(Actor·Narrator)이 나머지를 알아서 지어낸다. 그러면
    디렉터가 있으나 마나다. 세팅·트리거·장치·카메라·서브텍스트·감정 좌표까지 받아서
    그대로 아래로 흘린다."""
    from . import arc
    seq = arc.sequence_of(ep)
    prev = [s for s in novel.scenes if s.prose][-2:]
    recap = "\n".join(f"  {s.episode}화: {s.directives[0] if s.directives else ''}"
                       for s in prev) or "  (시작)"
    return f"""너는 여성향 청춘 로맨스 웹소설의 디렉터다. 한 회차의 **시나리오**를 짠다.
장면 요약이 아니라 연출 지시다 -- 무엇을 보여주고 무엇을 숨길지 네가 정한다.

{_world_brief(novel)}

[연출에서 반드시 정할 것]
  staging  공간·시간·날씨·소리. 그리고 **그 공간이 화자에게 무엇인가**
           (예: 연습실 3번방은 설윤이 알바 끝나고 유일하게 혼자일 수 있는 곳이다)
  trigger  씬을 여는 최초의 물리적 사건. 누가 무엇을 하는가. 대사로 시작하지 마라
  props    되돌아올 사물 하나. 처음엔 무심하게 놓인다. 나중에 이것이 의미를 갖는다
  camera   화자가 무엇을 보고 **무엇을 놓치는가.** 1인칭에서 시야는 곧 정보 통제다 --
           독자가 알고 화자는 모르는 상태를 여기서 만든다
  subtext  두 인물이 각각 말하지 않는 것. 대사는 그 위를 미끄러진다
  beat_arc 감정이 어디서 어디로. narrative_pull 시작값 -> 끝값
{SPLIT}
[구간] {ep}화 · 시퀀스 {seq['n']} {seq['name']}
[시퀀스 목표] {seq['goal']}
[감정 단계] {seq['stage']} / pull 범위 {seq['pull']} / 사건 규모 {arc.SCALES[spec['scale']]}
[이 에피소드의 결말] {spec['summary']}
[직전 회차]
{recap}

[이 장면이 갚아야 할 요구] {open_conds}
  establishes 에 위 문자열 중 하나를 **한 글자도 다르지 않게** 적어라.
{feedback}

JSON 만 출력:
{{"beat": "[한 문장 요약]",
  "participants": ["..."], "mode": "dialogue",
  "requires": [], "establishes": ["..."],
  "scale": {spec['scale']},
  "direction": {{
    "staging": "...", "trigger": "...", "props": "...",
    "camera": "...", "subtext": "...", "beat_arc": "pull -40 -> -15"
  }},
  "world_ops": [], "relation_ops": []}}"""


def subplot_prompt(novel, ep: int, spine_summary: str, feedback="") -> str:
    """서브플롯 한 씬. **원패턴을 감추는 것이 목적이다.**

    보고서: 위기-해결-보상의 반복이 노출되면 지루해진다. 조연의 이야기가 사이를 메우고,
    나중에 메인의 해결에 사소하게 이바지한다. 척추와 달리 아무것도 establishes 하지
    않으므로 지워도 사슬이 안 무너진다 -- 그게 서브플롯의 정의다."""
    from . import arc
    return f"""너는 여성향 청춘 로맨스 웹소설의 디렉터다. 메인 사이에 끼울 **서브플롯 한 씬**을
연출한다. 분량의 2/3가 이런 씬이다 -- 여기가 헐거우면 회차가 밋밋해진다.

{_world_brief(novel)}

[연출에서 정할 것] staging / trigger / props / camera / subtext
{SPLIT}
{arc.brief(ep)}
[이 구간의 메인] {spine_summary}

규칙:
- 메인의 인과를 건드리지 마라. establishes 는 비운다.
- 조연의 이야기이거나 화자의 일상이다. 다만 **메인과 같은 온도**여야 한다.
- 나중에 메인의 해결에 사소하게 이바지할 씨앗 하나를 심어라.
- 화자가 없는 씬이면 mode 를 "reported" 또는 "letter" 로 하라.
{feedback}

JSON 만 출력:
{{"beat": "[한 문장]", "participants": ["..."], "mode": "dialogue", "scale": 1,
  "direction": {{"staging": "...", "trigger": "...", "props": "...",
                "camera": "...", "subtext": "..."}},
  "world_ops": []}}"""


def build_episode(novel, spec: dict, llm=None, max_repairs=MAX_REPAIRS, log=None) -> list:
    """결말 하나를 회차들로 편다. **척추는 역방향, 살은 서브플롯.**

    spec 은 world_romance.OUTCOMES 의 한 항목이다(summary/requires/establishes/eps/scale).

    1. 열린 조건 = 결말의 requires 중 앞선 에피소드가 못 갚은 것
    2. 열린 조건 하나를 갚는 비트를 LLM 에게 받는다 -- **거꾸로** 쌓는다
    3. 그 비트 자신의 requires 가 새로 열린다. 닫힐 때까지 반복
    4. 뒤집어 시간순으로. 남는 회차 칸은 서브플롯으로 채운다
    5. 마지막 회차에 클리프행어

    establishes 문자열이 조건과 정확히 같지 않으면 되돌려보낸다 -- 한 글자만 달라도
    V018 이 개연성 구멍으로 잡기 때문에, 여기서 막는 편이 싸다."""
    from .episode import Beat, Outcome, Episode, to_scenes
    llm = llm or default_llm
    lo, hi = spec["eps"]
    n_eps = hi - lo + 1

    entry = set()
    for sc in novel.scenes:
        entry.update(sc.establishes or [])

    open_conds = [c for c in spec["requires"]
                  if c not in entry and not c.startswith("state:")]
    spine, feedback = [], ""

    while open_conds and len(spine) < n_eps:
        got = None
        for _ in range(max_repairs + 1):
            b = _json(_llm_for(llm, "director")(
                beat_prompt(novel, spec, open_conds, lo, feedback)))
            est = [e for e in (b.get("establishes") or []) if e in open_conds]
            if est:
                got = Beat(beat=b.get("beat", ""),
                           participants=b.get("participants") or [novel.pov_character],
                           mode=b.get("mode", "dialogue"),
                           requires=list(b.get("requires") or []), establishes=est,
                           world_ops=list(b.get("world_ops") or []),
                           relation_ops=list(b.get("relation_ops") or []),
                           scale=int(b.get("scale") or spec["scale"]),
                           direction=dict(b.get("direction") or {}))
                feedback = ""
                break
            feedback = _fb_text(
                f"establishes 가 열린 조건과 정확히 같지 않다. 받은 값: "
                f"{b.get('establishes')!r} / 열린 조건: {open_conds}. "
                f"**문자열을 그대로 복사하라** -- 한 글자만 달라도 개연성 구멍으로 잡힌다")
        if got is None:
            break
        spine.append(got)
        open_conds = [c for c in open_conds if c not in got.establishes]
        for c in got.requires:
            if (c not in entry and not c.startswith("state:")
                    and c not in open_conds
                    and not any(c in b.establishes for b in spine)):
                open_conds.append(c)

    spine.reverse()                                   # 거꾸로 쌓았으니 뒤집으면 시간순

    # 남는 칸은 서브플롯. 척추 사이에 끼워 원패턴을 감춘다.
    # **결말 자리를 한 칸 빼둔다.** 빼두지 않고 마지막에 잘라내면 결말이 통째로 날아간다
    # (회귀 검사 test_novel_episode 가 잡았다 -- 척추 3 + 서브플롯 2 + 결말 1 을 5로
    # 자르니 에피소드의 끝이 사라졌다).
    body_slots = max(1, n_eps - 1)
    overflow = max(0, len(spine) - body_slots)
    if overflow:
        # 척추가 회차 칸보다 길다. 잘라내면 인과가 끊기므로 잘라내지 않고 회차를 늘린다.
        body_slots = len(spine)
    beats, need = list(spine), body_slots - len(spine)
    for k in range(max(0, need)):
        b = _json(_llm_for(llm, "director")(
            subplot_prompt(novel, lo + k, spec["summary"])))
        filler = Beat(beat=b.get("beat", ""),
                      participants=b.get("participants") or [novel.pov_character],
                      mode=b.get("mode", "dialogue"), establishes=[],
                      world_ops=list(b.get("world_ops") or []),
                      scale=int(b.get("scale") or spec["scale"]))
        pos = min(len(beats), (k + 1) * max(1, len(beats)) // (need + 1))
        beats.insert(pos, filler)

    # 결말은 마지막 회차다.
    beats.append(Beat(beat="[결말] " + spec["summary"],
                      participants=[novel.pov_character],
                      requires=list(spec["requires"]),
                      establishes=list(spec["establishes"]),
                      world_ops=list(spec.get("world_ops") or []),
                      relation_ops=list(spec.get("relation_ops") or []),
                      scale=spec["scale"], cliffhanger="shock_line"))

    ep = Episode(n=spec["seq"], outcome=Outcome(spec["summary"], spec["requires"]),
                 beats=beats[:body_slots] + beats[-1:], episodes=(lo, hi))
    # id 는 **회차 범위**로 만든다. 시퀀스 하나에 결말이 여러 개라(시퀀스 1 은 1~10 과
    # 11~20) 시퀀스 번호만 쓰면 id 가 충돌하고, 아래 건너뛰기 판정도 두 번째 결말을
    # 이미 편 것으로 오판한다.
    # 회차 하나 = 척추 1씬 + 서브플롯 2씬. 첫 실측에서 씬 하나가 1,200자였는데 회차는
    # 5,000자라 씬=회차로 두면 분량이 1/4 로 난다. 보고서대로 **서브플롯이 2/3를 채운다.**
    from . import arc
    main_scenes = to_scenes(ep, prefix=f"ep{lo:03d}_", start_ep=lo)
    scenes = []
    for i, main in enumerate(main_scenes):
        epno = lo + i
        main.episode, main.is_episode_end, main.cliffhanger = epno, False, ""
        main.id = f"ep{lo:03d}_{epno:03d}m"
        scenes.append(main)
        for k in range(arc.SCENES_PER_EPISODE - arc.MAIN_SCENES):
            b = _json(_llm_for(llm, "director")(
                subplot_prompt(novel, epno, spec["summary"])))
            sub = Scene(id=f"ep{lo:03d}_{epno:03d}s{k + 1}",
                        participants=b.get("participants") or [novel.pov_character],
                        mode=b.get("mode", "dialogue"),
                        directives=[b.get("beat", "")],
                        world_ops=list(b.get("world_ops") or []),
                        scale=int(b.get("scale") or spec["scale"]),
                        direction=dict(b.get("direction") or {}), episode=epno)
            scenes.append(sub)
        scenes[-1].is_episode_end = True                  # 회차의 끝은 마지막 씬이다
        scenes[-1].cliffhanger = (main_scenes[i].cliffhanger
                                  or ("shock_line" if i == len(main_scenes) - 1 else ""))
    _record(log, {"event": "episode", "seq": spec["seq"], "eps": [lo, hi],
                  "spine": len(spine), "subplot": max(0, need),
                  "scenes": len(scenes), "unresolved": open_conds,
                  "overflow": overflow})
    if overflow:
        _log(f"[episode] 시퀀스 {spec['seq']}: 척추가 회차 칸보다 {overflow} 길다 -- "
             f"회차를 늘려 인과를 지켰다({hi - lo + 1} -> {len(scenes)})")
    return scenes


def drive_novel(novel, outcomes, path, llm=None, max_repairs=MAX_REPAIRS,
                log=None, limit_episodes=None) -> dict:
    """결말 목록을 순서대로 펴서 씬까지 채운다. 에피소드마다 저장한다."""
    llm = llm or default_llm
    log = log or (Path(path).with_suffix(".scenes.jsonl") if path else None)
    done = []
    for spec in outcomes[:limit_episodes] if limit_episodes else outcomes:
        tag = f"ep{spec['eps'][0]:03d}_"
        if any(s.id.startswith(tag) for s in novel.scenes):
            continue                                   # 이미 편 에피소드는 건너뛴다
        novel.scenes.extend(build_episode(novel, spec, llm, max_repairs, log))
        if path:
            novel.save(path)
        r = drive(novel, path, llm=llm, max_repairs=max_repairs, log=log)
        done.append({"seq": spec["seq"], **r})
        if r["status"] != "done":
            break
    return {"episodes": done,
            "verified": sum(1 for s in novel.scenes if s.status == "verified"),
            "total": len(novel.scenes)}


def _direction(scene) -> str:
    """Director 의 연출을 아래층이 읽을 형태로. **짜놓고 안 넘기면 없는 것과 같다.**"""
    d = scene.direction or {}
    if not d:
        return ""
    order = [("staging", "공간"), ("trigger", "여는 사건"), ("props", "장치"),
             ("camera", "화자의 시야"), ("subtext", "말하지 않는 것"),
             ("beat_arc", "감정 이동")]
    lines = [f"  {ko}: {d[k]}" for k, ko in order if d.get(k)]
    return "[연출 지시]\n" + "\n".join(lines) + "\n" if lines else ""


def _arc_brief(scene) -> str:
    """현재 회차의 거시 브리프. **변동부에 놓는다** -- 회차마다 바뀌므로 캐시 프리픽스
    앞에 두면 매번 캐시가 무효화된다."""
    if not scene.episode:
        return ""
    from . import arc
    return arc.brief(scene.episode) + "\n"


def director_prompt(novel, scene, feedback="") -> str:
    prev = [s for s in novel.scenes if s.status == "verified"][-2:]
    return f"""너는 1인칭 회고 소설의 디렉터다. 다음 씬의 무대와 지시를 정한다.

[화자] {novel.pov_character} (37세 시점의 회고. 결말을 이미 알고 있다)
[인물] {chr(10).join(f'  {c.name}: {c.persona}' for c in novel.characters)}
[화자가 이미 아는 미래] {novel.narrator_foreknowledge}

규칙:
- 감정을 직접 말하게 하지 마라. 사물·소리·날씨로 옮겨라.
- punctum 은 한 씬을 여는 감각 하나다. 나중에 되돌아올 수 있는 것으로.
- 인물이 "슬프다/외롭다" 라고 서술되면 기각된다.

세계 변경이 필요하면 아래 동사만 쓴다(없는 동사는 기각):
{catalog_for_prompt()}
{SPLIT}
{_arc_brief(scene)}
[직전까지] {chr(10).join(f'  {s.id}: {s.directives[0] if s.directives else ""}' for s in prev) or '  (시작)'}
[이 씬의 씨앗] {scene.directives[0] if scene.directives else ''}
[참여자] {scene.participants} / [모드] {scene.mode}
{feedback}

JSON 만 출력:
{{"location": "...", "punctum": "...", "directives": ["...", "...", "..."],
  "world_ops": [], "relation_ops": [],
  "scale": 1,
  "cliffhanger": ""}}

scale 은 이 씬이 다루는 사건 규모 1~5. cliffhanger 는 회차의 마지막 씬일 때만 채우고
{sorted(__import__("novel.arc", fromlist=["x"]).CLIFFHANGERS)} 중 하나여야 한다."""


def actor_prompt(novel, scene, name, feedback="") -> str:
    c = novel.character(name)
    log = "\n".join(f"  {t.actor}: {t.speech}" for t in scene.turns[-6:]) or "  (첫 발화)"
    return f"""너는 '{name}' 역할이다.

[페르소나] {c.persona}
[숨긴 것] {c.hidden_agenda}
[네가 아는 것] {c.knows}
[무대] {scene.location} / [감각] {scene.punctum}
[지시] {scene.directives}
{_direction(scene)}[직전 대화]
{log}

규칙:
- 속마음(inner_thought)과 실제 말(speech) 사이에 괴리를 둬라. 담담하게 말하고 속으로 복잡하라.
- 네가 모르는 것은 말할 수 없다. 오해하고 있다면 오해한 채로 말하라.
- 연출 지시의 '말하지 않는 것' 이 네 속마음이다. 입 밖으로는 그 위를 미끄러져라.
- 장치가 있으면 손으로 만져라. 설명하지 말고 다루기만 하라.
- 감정은 0~100, narrative_pull 만 -100~100. 한 턴에 35 이상 변하면 기각된다.
{'- 편지 모드다. 대화가 아니라 긴 편지를 써라.' if scene.mode == 'letter' else ''}
{feedback}

JSON 만 출력:
{{"inner_thought": "...", "action": "...", "speech": "...",
  "emotions": {{"joy": 0, "melancholy": 0, "isolation": 0, "narrative_pull": 0}}}}"""


def narrator_prompt(novel, scene, feedback="") -> str:
    logs = "\n".join(
        f"  [{t.actor}] 속:{t.inner_thought} / 행동:{t.action} / 말:{t.speech}"
        for t in scene.turns)
    return f"""수집된 로그를 1인칭 회고 산문으로 직조한다.

[화자] {novel.pov_character} — 반드시 "나는 ~했다" 시점
[무대] {scene.location} / [감각] {scene.punctum}
{_direction(scene)}[로그]
{logs}

규칙:
- 다른 인물의 속마음을 사실로 쓰지 마라. 화자의 관찰과 추측으로 옮겨라
  (예: "그녀의 눈동자 깊은 곳에서 무언가 무너져 내리는 기척이 느껴졌다").
- "슬펐다/외로웠다" 같은 직접 서술 금지. 대사 안에서는 허용된다.
- punctum 을 대화의 공백에 끼워 넣어라.
- **연출 지시를 그대로 실행하라.** 여는 사건으로 시작하고, 장치를 무심하게 놓고,
  화자의 시야 밖은 쓰지 마라 -- 화자가 놓친 것은 독자도 놓쳐야 한다.
- 담담하고 건조하게. 신파로 흐르지 마라.
- **문장 길이를 섞어라.** "-했다. -다." 만 이어지면 내용이 좋아도 읽히지 않는다:
    · 짧은 문장(20자 안팎)으로 끊어친다. 명사로 끝내도 좋다.
    · 만연체(60자 이상)를 회차마다 두어 번. 여러 절을 한 호흡에 잇는다.
    · 같은 종결어미가 세 번 넘게 연속되지 않게 -- 도치·명사형·대시로 흩어라.
    · **대시(—)** 로 숨을 끊거나 덧붙여라.
    · 비유는 아껴 쓰되 있어야 한다(처럼·같이·듯·만큼). 화려하지 않게, 사물에 붙여서.
- **분량: 공백 포함 {__import__("novel.arc", fromlist=["x"]).CHARS_PER_SCENE}자 안팎.**
  회차 하나가 5,000자이고 이 씬은 그중 한 조각이다. 짧게 끊지 마라 -- 대화 사이의 정적,
  손이 하는 일, 창밖, 냄새, 소리로 채워라.
{'- 편지를 읽는 장면으로 감싸고, 편지 내용을 서술에 녹여라.' if scene.mode == 'letter' else ''}
{feedback}

산문만 출력한다. JSON 도 머리말도 쓰지 마라."""


# ---------------------------------------------------------------- 루프

def _record(path, rec):
    if not path:
        return
    try:
        with Path(path).open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def run_scene(novel, scene, llm, max_repairs=MAX_REPAIRS, log=None) -> dict:
    """한 씬을 관문 통과까지 몰아붙인다. 반환 {status, attempts, violations}."""
    t0 = time.time()
    feedback = ""

    for attempt in range(1, max_repairs + 2):
        # --- 기획 (이미 채워져 있으면 건너뛴다: 템플릿이 준 씬)
        if not scene.location:
            d = _json(_llm_for(llm, "director")(director_prompt(novel, scene, feedback)))
            scene.location = d.get("location", "")
            scene.punctum = d.get("punctum", "")
            scene.directives = d.get("directives") or scene.directives
            scene.world_ops = (scene.world_ops or []) + (d.get("world_ops") or [])
            scene.relation_ops = (scene.relation_ops or []) + (d.get("relation_ops") or [])
            scene.scale = int(d.get("scale") or scene.scale or 0)
            if scene.is_episode_end:
                scene.cliffhanger = d.get("cliffhanger") or scene.cliffhanger

        # --- 연기
        # **직전 시도의 산문을 반드시 지운다.** 안 지우면 아래 턴 단계 관문이 낡은 산문을
        # 그대로 검사해서, 턴이 멀쩡한데도 이전 산문의 위반으로 계속 기각된다 -- 서술
        # 단계까지 가지 못하니 수리가 영원히 안 된다(회귀 검사 test_novel_drive 가 잡았다).
        scene.prose = ""
        scene.turns = []
        speakers = scene.participants or [novel.pov_character]
        rounds = 1 if scene.mode == "letter" else 2
        for _ in range(rounds):
            for name in speakers:
                a = _json(_llm_for(llm, "actor")(actor_prompt(novel, scene, name, feedback)))
                scene.turns.append(Turn(
                    actor=name, inner_thought=a.get("inner_thought", ""),
                    action=a.get("action", ""), speech=a.get("speech", ""),
                    emotions={k: int(a.get("emotions", {}).get(k, 0)) for k in AXES}))

        # --- 관문 1차 (로그 규칙)
        vs = gate.check(scene, novel)
        hard = [v for v in vs if v.severity == "hard"]
        if hard:
            feedback = _fb(hard)
            scene.attempts.append({"attempt": attempt, "stage": "turns",
                                   "violations": [str(v) for v in hard]})
            continue

        # --- 서술
        scene.prose = _llm_for(llm, "narrator")(
            narrator_prompt(novel, scene, feedback)).strip()

        # --- 관문 2차 (산문 규칙)
        vs = gate.check(scene, novel)
        hard = [v for v in vs if v.severity == "hard"]
        if hard:
            feedback = _fb(hard)
            scene.attempts.append({"attempt": attempt, "stage": "prose",
                                   "violations": [str(v) for v in hard]})
            continue

        scene.status = "verified"
        scene.violations = [str(v) for v in vs]          # soft 는 기록만
        return {"status": "verified", "attempts": attempt, "soft": len(vs),
                "seconds": round(time.time() - t0, 2)}

    scene.status = "failed"
    scene.violations = [str(v) for v in hard]
    return {"status": "failed", "attempts": max_repairs + 1,
            "reason": "관문 위반이 수리 한도 안에 해소되지 않았다",
            "violations": [str(v) for v in hard], "seconds": round(time.time() - t0, 2)}


def drive(novel, path, llm=None, max_repairs=MAX_REPAIRS, log=None, limit=None) -> dict:
    """미완 씬들을 차례로 몰아붙인다. 씬마다 즉시 저장한다."""
    llm = llm or default_llm      # 콜러블 하나 또는 {역할: 콜러블} dict
    log = log or (Path(path).with_suffix(".scenes.jsonl") if path else None)
    _record(log, {"event": "start", "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                  "title": novel.title, "scenes": len(novel.scenes)})

    done, failed = 0, 0
    while True:
        scene = novel.next_pending()
        if scene is None or (limit and done + failed >= limit):
            break
        r = run_scene(novel, scene, llm, max_repairs, log)
        _record(log, {"event": "scene", "id": scene.id, "at": time.strftime("%H:%M:%S"), **r})
        if path:
            novel.save(path)                              # 씬마다 즉시 저장
        if r["status"] == "verified":
            done += 1
        else:
            failed += 1
            break                                         # 막힌 씬을 넘어가지 않는다

    out = {"status": "done" if failed == 0 else "blocked",
           "verified": done, "failed": failed,
           "remaining": sum(1 for s in novel.scenes if s.status != "verified")}
    _record(log, {"event": "end", "at": time.strftime("%Y-%m-%d %H:%M:%S"), **out})
    return out
