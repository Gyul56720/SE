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
from . import style
from .state import AXES, Scene, Turn
from .verbs import catalog_for_prompt

MAX_REPAIRS = 3
# 야간 러너가 에피소드마다 세운다. build_episode 가 이 시각을 넘기면 척추/서브플롯 생성을
# 멈추고 지금까지 만든 것으로 마무리한다 -- 한 편이 밤을 다 먹는 것을 막는다.
EPISODE_DEADLINE = None


def _log(msg: str) -> None:
    """진행 상황을 stderr 로. 산출물(stdout)과 섞이지 않게 한다."""
    print(msg, file=_sys.stderr, flush=True)
# 프롬프트를 캐시 가능한 고정부와 매번 바뀌는 부분으로 가르는 표식. 캐싱은 접두사 일치라
# 이 경계가 있어야 고정부를 통째로 캐시할 수 있다.
SPLIT = "\n<<<VOLATILE>>>\n"


def _llm_for(llm, role: str):
    """llm 이 dict 면 역할별로 고른다. 호출자가 director 만 Claude 로 돌릴 수 있게.

    extractor 는 기본이 Gemini 다. 판단하지 않고 옮기기만 하므로 값싼 모델로 충분하고,
    비싼 모델을 여기 쓰면 호출의 절반이 추출에 들어간다."""
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


def claude_code_llm(timeout: float = 300.0):
    """Claude Code CLI(`claude -p`)로 한 역할을 돌린다. **Console 크레딧이 아니라 구독으로
    청구된다** -- Max 구독이 있으면 API 크레딧 없이 director 를 Claude 로 쓸 수 있다.

    Public_agent/verify.py 가 이미 같은 수를 쓴다(생성자와 분리된 판단 주체로 claude -p 를
    부른다). 여기서는 판단이 아니라 연출을 시킬 뿐 호출 형태는 같다.

    fail-closed: 호출이 실패하면(토큰 소진·CLI 없음·타임아웃) 조용히 넘어가지 않고 예외를
    올린다. drive 의 수리 루프가 그것을 위반으로 받아 재시도하거나 사실대로 실패한다 --
    verify.py 가 "확인 안 된 것을 통과시키는 것보다 낫다" 고 적어둔 원칙과 같다.

    API 경로와 다른 점:
      · 프롬프트 캐싱을 제어할 수 없다. SPLIT 경계는 지우고 통짜로 보낸다
      · 호출당 오버헤드가 크다(프로세스 기동). 씬 루프 전체를 이걸로 돌리지 말고
        director 처럼 호출이 드문 역할에만 붙여라
      · 동시 실행은 구독의 제한을 따른다"""
    import subprocess
    import tempfile
    import uuid

    # **저장소 밖에서 돌린다.** cwd 가 저장소면 CLAUDE.md 와 프로젝트 지시가 전부 실려
    # 디렉터가 소설이 아니라 이 저장소 얘기를 하게 된다. 연출만 시킬 것이므로 빈 디렉토리에서.
    workdir = tempfile.mkdtemp(prefix="novel-director-")

    # **API 키를 물려주지 않는다.** 이 어댑터의 존재 이유가 "구독으로 청구한다" 인데,
    # 부모 셸에 ANTHROPIC_API_KEY 가 export 돼 있으면 CLI 가 로그인 프로필 대신 그 키로
    # 인증한다(문서화된 대표적 함정: 키가 있으면 프로필은 아예 조회되지 않는다).
    # 그러면 크레딧을 피하려고 만든 경로가 도로 크레딧으로 나가고, 그 키가 워크스페이스
    # 헤더를 요구하면 같은 400 을 낸다 -- 실측으로 그렇게 났다.
    # 빈 문자열도 자리를 차지하므로 **지운다.**
    child_env = {k: v for k, v in _os.environ.items()
                 if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}

    def call(prompt: str) -> str:
        # session-id 는 정식 UUID 여야 한다 (Public_agent/verify.py 는 접두사를 붙여 쓰는데
        # 최신 CLI 는 그것을 거부한다: "Invalid session ID").
        sid = str(uuid.uuid4())
        try:
            r = subprocess.run(
                # 권한 모드를 주지 않는다. 디렉터는 텍스트만 내놓으므로 도구가 필요 없고,
                # bypassPermissions 는 root 로 돌면 CLI 가 거부한다.
                ["claude", "-p", "--session-id", sid, _flatten(prompt)],
                cwd=workdir, stdin=subprocess.DEVNULL, env=child_env,
                capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError:
            raise RuntimeError("claude CLI 를 찾지 못했다 -- Claude Code 가 설치돼 있는가")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"claude -p 가 {timeout:g}초 안에 응답하지 않았다")
        if r.returncode != 0:
            # stderr 가 비는 경우가 있다(CLI 가 stdout 으로 내거나 조용히 죽거나).
            # 그때 "실패" 한 줄만 던지면 사람이 원인을 못 찾는다 -- 있는 것을 전부 보여준다.
            detail = (r.stderr or "").strip() or (r.stdout or "").strip() or "(출력 없음)"
            raise RuntimeError(
                f"claude -p 가 exit {r.returncode} 로 끝났다: {detail[-500:]}\n"
                f"  직접 확인:  claude -p '안녕' < /dev/null; echo \"exit=$?\"\n"
                f"  로그인 상태: claude 를 대화형으로 한 번 띄워 인증을 확인하라\n"
                f"  (이 어댑터는 ANTHROPIC_API_KEY 를 자식에게 넘기지 않는다 -- "
                f"넘기면 구독이 아니라 그 키로 청구된다)\n"
                f"  한도 소진이면 API 키 경로(anthropic_llm)나 Gemini 로 우회하라")
        out = (r.stdout or "").strip()
        if not out:
            raise RuntimeError("claude -p 가 빈 응답을 냈다")
        return out
    return call


_POOL = None            # (키 x 모델) 후보. **한 번만 만든다**


def default_llm(prompt: str) -> str:
    """orchestrator/llm_pool 로 나간다 -- 쿼터 소진·모델 장애를 견디는 그 풀이다.

    풀을 캐시하는 이유. build_pool 은 키마다 **실사용 모델 목록을 조회**한다(API 호출).
    예전에는 프롬프트마다 그것을 다시 했다 -- 한 회차가 100호출 남짓이니 100번을 더 물은
    셈이고, 3화면 300번이다. 후보 목록은 런 중에 바뀌지 않는다. 쿼터 소진·영구 제외·성공
    pin 같은 **상태는 quota_tracker 가 파일로 들고 있으므로** 풀을 재사용해도 그대로
    반영된다 -- 캐시해서 잃는 것이 없다."""
    _ensure_pool()
    mod, pool = _POOL
    return mod.call(pool, _flatten(prompt), pool_id="novel")[0]


def _ensure_pool() -> None:
    """후보 풀을 한 번만 세운다. build_pool 은 키마다 모델 목록을 조회하므로(API 호출)
    프롬프트마다 다시 하면 한 회차에 100번을 더 묻는다."""
    global _POOL
    if _POOL is None:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "orchestrator"))
        import llm_pool
        _POOL = (llm_pool, llm_pool.build_pool())
        if not _POOL[1]:
            _POOL = None
            raise RuntimeError("LLM 후보 풀이 비었다 -- GEMINI_API_KEY 를 설정하라")
        _log(f"[풀] 후보 {len(_POOL[1])}개: "
             f"{', '.join(l for l, _ in _POOL[1][:4])}...")


def _extractor(llm):
    """추출에 쓸 콜러블. **주입한 것은 주입한 대로 쓴다** -- 기본 풀로 돌 때만 gemma 로
    돌린다. 안 그러면 가짜 LLM 을 넣은 테스트가 진짜 API 로 새어 나간다."""
    if isinstance(llm, dict):
        return _llm_for(llm, "extractor")
    return extractor_llm if llm is default_llm else llm


def extractor_llm(prompt: str) -> str:
    """추출 전용 -- **gemma 를 먼저 쓴다.**

    추출은 판단하지 않고 옮기기만 한다(원고에서 인물·장소·사물을 JSON 으로). 문장력이
    필요 없는 자리인데 호출 수는 화자와 맞먹는다. 그런데 지금까지 이것도 flash 로 나갔다.

    분당 한도는 모델별로 따로 걸린다. gemma 는 계열이 달라 자기 통을 따로 갖는데,
    _model_rank 가 품질 순으로 맨 뒤에 두는 바람에 다른 것이 전부 429 일 때만 닿았다
    (실측: 사용량 1~2건). **비어 있는 통을 놀리면서 찬 통 앞에 줄을 서 있던 것이다.**
    추출을 그쪽으로 돌리면 flash 의 분당 한도가 통째로 산문에 남는다. 산문 품질은
    건드리지 않는다 -- 화자는 그대로 flash 다.

    gemma 가 없거나 전부 막히면 평소 풀로 물러난다(call 이 알아서 다음 후보로 간다)."""
    _ensure_pool()
    mod, pool = _POOL
    return mod.call(pool, _flatten(prompt), pool_id="novel", prefer=r"gemma")[0]


def _flatten(prompt: str) -> str:
    """캐시 경계 표식을 지운다. 캐싱을 안 쓰는 경로(Gemini 등)는 통짜 프롬프트를 받는다."""
    return prompt.replace(SPLIT, "\n")


def _json(text: str) -> dict:
    """코드펜스와 앞뒤 잡소리를 벗기고 JSON **객체** 하나를 꺼낸다.

    dict 인지 확인한다. 확인하지 않으면 문자열이나 배열이 그대로 위로 올라가서, 훨씬
    뒤의 `b.get(...)` 에서 'str' object has no attribute 'get' 로 터진다 -- 원인에서
    멀리 떨어진 곳에서 죽으면 로그만 보고는 무엇이 잘못됐는지 알 수 없다."""
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < 0:
        raise ValueError(f"JSON 을 찾지 못했다: {text[:120]!r}")
    got = json.loads(t[i:j + 1])
    if not isinstance(got, dict):
        raise ValueError(f"JSON 객체가 아니라 {type(got).__name__} 이다: {t[i:j + 1][:120]!r}")
    return got


def _ops(raw, label: str = "") -> list:
    """LLM 이 준 ops 목록에서 **객체만** 남긴다.

    world_ops/relation_ops 는 기계가 읽는 선언이라 {"event": ...} 형태여야 하는데,
    모델이 종종 문자열 목록으로 낸다(["설윤이 자리를 잃었다"]). 그대로 담으면 씬에
    저장되고, 한참 뒤 novel.save() 안의 derive_gates 에서 터진다 -- 원인에서 멀리
    떨어진 곳에서 죽으면 로그만 보고는 무엇이 잘못됐는지 알 수 없다. 경계에서 거른다.

    버린 것은 반드시 로그에 남긴다. 조용히 버리면 세계관 변화가 사라진 줄도 모른다."""
    kept = [o for o in (raw or []) if isinstance(o, dict)]
    dropped = len(raw or []) - len(kept)
    if dropped:
        _log(f"[ops] {label}: 객체가 아닌 항목 {dropped}개를 버렸다 -- "
             f"{[str(o)[:40] for o in (raw or []) if not isinstance(o, dict)]}")
    return kept


def clock_of(spec: dict, novel) -> float:
    """지금 남은 시간. 같은 마감을 쓰는 씬들의 최솟값에서 이어받는다 -- 시계는 되감기지
    않는다. 아직 아무것도 없으면 결말이 준 시계에서 시작한다."""
    made = [sc.deadline_hours for sc in novel.scenes
            if sc.deadline_hours and sc.deadline == spec.get("deadline")]
    return min(made) if made else float(spec.get("deadline_hours") or 72)


def _check_pressure(b: dict, novel, clock: float) -> list:
    """압박과 능동이 선언됐는가. 위반 사유 목록(빈 목록이면 통과).

    **최소한만 본다.** 과잉 기각하는 심판은 맞는 답도 버린다 -- 여기서 막히면 그 비트를
    다시 받느라 호출이 두 배가 되므로, 정말 없으면 안 되는 것만 되돌려보낸다:

      · driver 가 등장인물도 "사건" 도 아니면      -- 누가 움직였는지 모르는 장면이다
      · driver 가 화자인데 cost 가 비었으면        -- 화자가 공짜로 이겼다
      · deadline_hours 가 숫자가 아니거나 안 줄면  -- 시계가 조여들지 않는다

    화자가 아닌 사람이 움직인 장면은 통과시킨다. 매 장면 화자가 움직이면 그것대로
    지치고, 당하는 장면도 서사에 필요하다 -- 연속으로 당하기만 하는 것이 병이지
    한 장면 당하는 것은 병이 아니다. 이제 관문은 이것을 보지 않는다 -- 조립 단계의
    이 강제만 남았다."""
    names = {c.name for c in novel.characters}
    out = []
    b["deadline_hours_raw"] = b.get("deadline_hours")
    driver = str(b.get("driver") or "").strip()
    if not driver or (driver not in names and driver != "사건"):
        out.append(f"'움직이는 사람' 이 비었거나 등장인물이 아니다({driver!r}). "
                   f"{sorted(names)} 중 하나이거나 '사건' 이어야 한다")
    elif driver == novel.pov_character and not str(b.get("cost") or "").strip():
        out.append(f"{driver} 가 스스로 움직였는데 '치른 대가' 가 비었다. "
                   f"무엇을 잃었는지 적어라 -- 공짜로 얻으면 긴장이 죽는다")
    # 시계는 **산수지 창작이 아니다.** 틀렸다고 비트를 통째로 되돌려보내면 300초짜리
    # 디렉터 호출 하나를 산수 하나 때문에 버리는 것이고, 네 번 틀리면 그 척추 비트가
    # 아예 사라져 인과가 끊긴다. 여기서는 **고쳐서 쓴다** -- 모델이 못 고치는 것만
    # 되돌려보내는 것이 이 함수의 원칙이다(driver 와 cost 는 의미라서 모델만 고칠 수 있다).
    try:
        hours = float(b.get("deadline_hours"))
    except (TypeError, ValueError):
        hours = None
    if hours is None or hours >= clock:
        b["deadline_hours"] = fixed = max(0.5, round(clock - 1, 1))
        _log(f"[압박] 남은 시간을 보정했다: {b.get('deadline_hours_raw', hours)!r} "
             f"-> {fixed} (장면 시작 {clock})")
    return out


SUBPLOT_SIMILAR = 0.55        # 이보다 닮으면 같은 소재로 본다


def _too_similar(beat: str, done: list) -> str:
    """이미 쓴 서브플롯과 너무 닮았는가. 닮은 것 하나를 돌려준다(아니면 빈 문자열).

    프롬프트로 "겹치지 마라" 고만 하면 절반쯤 지켜진다. 기계가 재서 되돌려보내야 한다 --
    이 저장소가 관문을 두는 이유와 같다. difflib 는 형태소를 모르지만, "핫팩을 많이 사는
    남자" 와 "핫팩을 많이 사는 상급생" 처럼 **같은 문장을 조금 고친 것**은 확실히 잡는다.
    실측에서 나온 반복이 정확히 그 모양이었다.

    임계는 0.55 다. 낮추면 정당하게 이어지는 서브플롯(같은 조연의 연속된 이야기)까지
    걸리고, 그건 과잉 기각이다."""
    import difflib
    a = re.sub(r"\s+", "", beat or "")
    if len(a) < 6:
        return ""
    for prev in done or []:
        b = re.sub(r"\s+", "", prev or "")
        if difflib.SequenceMatcher(None, a, b).ratio() >= SUBPLOT_SIMILAR:
            return prev
    return ""


def _people(raw, novel, label: str = "") -> list:
    """참가자 목록에서 **등장인물만** 남긴다.

    world_ops 가 문자열로 왔던 것과 같은 종류의 실패다. 디렉터가 "낯선 남자", "취객",
    "스물세 개의 핫팩을 사는 남자" 같은 것을 등장인물 자리에 적으면 그대로 씬에 저장되고,
    한참 뒤 배우 프롬프트를 만들 때 novel.character(name) 이 KeyError 로 터진다 --
    **회차 전체가 거기서 죽는다**(실측 2026-09-04: drive() 가 이걸로 예외를 내고 1~10화가
    산문 0자로 끝났다).

    씬에 이름 없는 인물이 필요하면 그건 배우가 아니라 배경이다. 산문 안에서 묘사하면
    되고, 대사를 주려면 등장인물로 등록해야 한다. 여기서 거르고 로그에 남긴다.

    전부 걸러지면 화자를 넣는다 -- 참가자가 없는 씬은 배우 단계가 아무것도 못 한다."""
    names = {c.name for c in novel.characters}
    kept, dropped = [], []
    for x in (raw or []):
        nm = str(x).strip()
        if nm in names:
            if nm not in kept:
                kept.append(nm)          # 중복은 조용히 지운다. 잘못이 아니다
        elif nm:
            dropped.append(nm)           # 이쪽만 보고한다 -- 디렉터가 만든 유령이다
    if dropped:
        _log(f"[인물] {label}: 등장인물이 아닌 이름을 뺐다 -- {dropped[:4]}")
    if not kept:
        kept = [novel.pov_character]
        _log(f"[인물] {label}: 남은 참가자가 없어 화자({novel.pov_character})를 넣는다")
    return kept


def _rel_ops(raw, novel, label: str = "") -> tuple:
    """relation_ops 에서 **쓸 수 있는 선언만** 남긴다.

    관계 선언은 members 가 서로 다른 두 등장인물이어야 한다. 아니면 V009 가 hard 로 잡는데,
    수리 루프는 산문만 다시 쓰므로 **문장을 백 번 고쳐도 그 배열은 안 바뀐다** -- 그 씬은
    시도 횟수를 다 쓰고 결정론적으로 실패하고, 그 뒤 씬들까지 세운다(2026-09-04 시험 런:
    "관계 구성원이 두 사람이 아니다: []" 로 4번 시도 111초, verified 0).

    고칠 수 없는 선언은 경계에서 버린다. 잃는 것은 관계 선언 하나이고, 사는 것은 그 회차다.

    반환은 (쓸 수 있는 관계 선언, world_ops 로 옮길 것) 이다."""
    from . import verbs as V
    names = {c.name for c in novel.characters}
    kept, moved = [], []
    for o in _ops(raw, label):
        m = list(o.get("members") or [])
        if len(m) == 2 and m[0] != m[1] and all(x in names for x in m):
            kept.append(o)
            continue
        # **자리를 잘못 찾은 선언은 버리지 않고 옮긴다.** 모델이 world 동사를
        # relation_ops 에 넣는 일이 잦다(실측: {"op": "meet", "pair": [...]}).
        # 선언 자체는 진짜인데 버킷만 틀린 것이라, 버리면 세계 변화가 사라진다.
        verb = o.get("event") or o.get("op")
        if verb in V.VERBS:
            moved.append({**o, "event": verb})
            _log(f"[ops] {label}: '{verb}' 은 world 동사다 -- world_ops 로 옮긴다")
        else:
            _log(f"[ops] {label}: 쓸 수 없는 관계 선언을 버렸다 -- members={m} op={verb!r}")
    return kept, moved


def call_json(llm, prompt: str, tries: int = 3, label: str = "") -> dict:
    """LLM 에게 JSON 을 받아 파싱한다. **깨지면 에러 문구를 붙여 다시 묻는다.**

    2026-09-03 밤샘 런이 여기서 통째로 날아갔다. 추출기가 낸 JSON 하나가 깨졌는데
    (값 안의 큰따옴표를 안 escape 한 전형적인 실패) 재시도가 없어서 예외가 build_episode
    를 뚫고 올라갔고, 그 블록 15화가 통째로 버려졌다. 일곱 시간에 0자였다.

    모델은 **자기가 낸 JSON 의 파싱 오류를 알려주면 대체로 고친다.** 그러니 한 번의
    파싱 실패로 열다섯 화를 버릴 이유가 없다. 실패 문구를 그대로 되먹여 다시 묻는다.

    끝내 못 받으면 ValueError 를 올린다 -- 호출자가 그 비트 하나만 접을지, 전부를
    포기할지 정한다. 여기서 조용히 {} 를 돌려주면 빈 씬이 조립돼 더 나쁘다."""
    last = ""
    for attempt in range(tries):
        raw = llm(prompt if not last else prompt + _fb_text(
            f"직전 출력이 JSON 으로 파싱되지 않았다: {last}. "
            f"**JSON 만** 출력하고, 값 안의 큰따옴표는 홑따옴표로 바꾸거나 escape 하라. "
            f"줄바꿈은 값 안에 넣지 마라."))
        try:
            return _json(raw)
        except (ValueError, json.JSONDecodeError) as e:
            last = f"{type(e).__name__}: {str(e)[:150]}"
            _log(f"[json] {label or 'LLM'} 파싱 실패 {attempt + 1}/{tries} -- {last}")
    raise ValueError(f"{label or 'LLM'}: {tries}번 시도했지만 JSON 을 못 받았다 ({last})")


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


def _depth_brief(novel) -> str:
    """이 소설이 시험하는 것 한 줄. **명제도 사상가 이름도 싣지 않는다** -- 프롬프트에
    '칸트' 나 '정언명령' 이 들어가면 모델은 그 말을 텍스트에 쓴다. 시험(test)과 겉모습
    (cover)만 준다. 사상은 선택으로 드러나야 하고, 선택은 장면이 만든다."""
    d = getattr(novel, "depth", None) or {}
    if not d.get("test"):
        return ""
    return (f"[이 이야기가 시험하는 것] {d['test']}\n"
            f"[겉으로 보여야 하는 것] {d.get('cover', '가볍고 재미있게')}\n"
            f"  ※ 이것을 대사로 옮기지 마라. 인물이 설명하면 소설이 강의가 된다.\n"
            f"    선택과 그 대가로만 드러내라. 답은 주지 않는다.\n")


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
    w = getattr(novel, "world", None) or {}
    bible = ""
    if w:
        bible = f"""
[세계 — {w.get('name', '')}]
  법칙      {w.get('order', '')}
  등급      {w.get('ranks', '')}
  종족      {w.get('races', '')}
  세력      {w.get('nations', '')}
  의식주    {w.get('living', '')}
  시민의식  {w.get('ethic', '')}
  위협      {w.get('threat', '')}
  잔혹      {w.get('cruelty', '')}
  관계      {w.get('bond', '')}
  * 이 설정 안에서만 써라. **새 종족·새 제도·새 등급을 지어내지 마라** -- 씬마다 다른
    세계가 되면 그것은 관문이 못 잡는 종류의 붕괴다.
  * 설정을 설명하지 마라. 인물들에게는 다 아는 일이다. 배급 줄에 서고, 부적값을 치르고,
    등급을 확인하는 **행동**으로만 보이게 하라.
  * 시민의식이 이 세계의 핵심이다. 잔혹한 것을 사람들이 **당연하게** 여기는 자리를 보여줘라.
"""
    return f"""[화자] {novel.pov_character} (1인칭 회고. 결말을 이미 안다)
{bible}
[인물]
{who}

[비밀 — 누가 무엇을 모르는가]
{sec}
  * 정보 격차가 연독률의 엔진이다. 아는 인물만 말할 수 있고, 모르는 인물이 말하면 기각된다.
  * 화자가 모르는 것은 **속으로도** 생각할 수 없다.

[이 장르의 규약]
  · 감정을 직접 쓰지 마라. 사물·소리·날씨·손이 하는 일로 옮겨라.
  · 말과 속마음 사이에 괴리를 둬라. 가까이 있어도 심리적 거리를 유지한다.
  · 주인공이 대가를 치르게 하지 마라. 걸린 것은 잃을 위험이지 이미 낸 값이 아니다.
  · 위기-해결-보상의 원패턴이 노출되면 지루하다. 서브플롯이 그것을 감춘다.
  · **잔혹은 설명하지 않는다.** 그 자리에 있던 사람이 아무 말 없이 하던 일을 계속하는 것,
    그것이 이 세계의 잔혹이다.

[관계 — 이 세계에서 연애는 제도다]
  · 위 [세계]의 **관계** 항목이 이 소설의 연애 규칙이다. 짝을 맺는 것이 사적인 감정이기
    전에 **제도이자 생존 조건**이라는 점이 이 장르의 긴장을 만든다.
  · 끌림을 대사로 고백하지 마라. 제도 안에서 무엇을 감수하는가로 보여라 -- 배급표를
    넘겨주고, 순번을 양보하고, 기록을 고치고, 자기 등급을 낮게 신고한다.
  · 집착의 동기는 상처다. 그리고 **결코 용서받지 못할 선은 넘지 않는다.**
  · 상대역은 구조받기만 하지 않는다. 스스로 밀어내고, 스스로 값을 치른다.
  · 짝을 잃거나 떼이는 것이 이 세계에서 가장 아픈 형태의 폭력이다. 그 자리를 아껴 써라."""


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
    """한 회차 분량의 **시나리오**를 받는다. 입력은 XML, 출력은 Markdown.

    형식 세금(Format Tax): 출력 형식을 JSON/XML 로 강제하면 모델이 문장을 지으면서 동시에
    문법 유효성을 지켜야 해서 주의력이 갈리고, 개방형 창작에서 품질이 떨어진다. 그래서
    **창작은 Markdown 자유 형식으로 받는다.**

    그런데 관문(V009 관계·V018 개연성)은 구조화된 데이터를 먹고 산다. 산문만
    받으면 검증이 통째로 무너진다. 그래서 두 단계로 가른다:

        디렉터(Opus)  XML 입력 -> Markdown 시나리오   창작. 형식 세금 면제
        추출기(Gemini) Markdown -> JSON              데이터 추출. JSON 이 유리한 태스크

    보고서 자신이 근거다 -- "JSON 의 정확도 우위는 **데이터 추출 태스크에 한정**된 이야기다."
    창작에는 Markdown, 추출에는 JSON 을 쓰면 둘 다 자기 자리에서 쓰인다.

    입력의 XML 태그는 맥락 구역을 갈라 환각과 맥락 이탈을 막는 쪽이라 유지한다."""
    from . import arc
    seq = arc.sequence_of(ep)
    # 지금 남은 시간. 이미 만든 척추 비트가 있으면 그 최솟값에서 이어받는다 -- 시계는
    # 되감기지 않는다. 없으면 결말의 시계에서 시작한다.
    clock = clock_of(spec, novel)
    prev = [s for s in novel.scenes if s.prose][-2:]
    recap = "\n".join(f"- {s.episode}화: {s.directives[0] if s.directives else ''}"
                       for s in prev) or "- (시작)"
    return f"""<System_Persona>
당신은 대한민국 최고 수준의 웹소설 서사 디자이너다. 장기/에피소드/화별 3단 플롯에 능통하고,
연독률 방어를 위해 도파민 메커니즘과 정보 격차, 5대 클리프행어 공식을 자유자재로 쓴다.
</System_Persona>

<Narrative_Doctrine>
- 메인(로맨스) 33% · 서브(일상·가족) 67%. 서브플롯이 위기-해결-보상의 원패턴을 은폐한다.
- 감정은 추상어로 쓰지 않는다. "슬프다" 가 아니라 "목이 메어 말이 나오지 않았다" 로.
- 작은 사건에서 시작해 스케일을 키운다. 처음부터 크면 50화 전에 동력을 잃는다.
- 남주는 윤리적 선을 넘지 않되 강한 동기를 갖는다. 여주는 구조받기만 하지 않는다.
- 독자와 인물의 정보 격차가 연독률의 엔진이다.
- **화자는 구경하지 않는다.** 조건은 저절로 성립하지 않는다 -- 누군가 무언가를 해서
  성립한다. 화자가 스스로 움직여 판을 바꾸는 장면을 회차마다 최소 하나 만들어라.
  화자가 당하기만 하는 회차가 이어지면 독자는 떠난다.
- **공짜로 얻지 않는다.** 화자가 무언가를 얻으면 반드시 무언가를 잃는다. 빚, 자존심,
  관계, 시간, 손. 대가 없는 승리는 긴장을 죽인다.
- **시계는 조여든다.** 모든 장면은 마감까지 남은 시간 위에서 벌어진다. 시간이 줄지
  않으면 압박이 없고, 압박이 없으면 사건이 아니라 상황일 뿐이다.
- 클리프행어 5공식: 위기 직전 / 충격 대사 후 / 예상 밖 인물 등장 / 위험 신호 직전 /
  들키면 안 되는 순간에 들키기. 매회 남발하면 양치기 소년이 된다.
</Narrative_Doctrine>

<World>
{_world_brief(novel)}
{_depth_brief(novel)}
</World>
{SPLIT}
<Position>
{ep}화 / 200화 · 시퀀스 {seq['n']} {seq['name']}
시퀀스 목표: {seq['goal']}
감정 단계: {seq['stage']} · narrative_pull 범위 {seq['pull']}
사건 규모: {arc.SCALES[spec['scale']]}
</Position>

<Episode_Outcome>
{spec['summary']}
</Episode_Outcome>

<Clock>
마감: {spec.get('deadline') or '(이 구간에는 명시된 마감이 없다 -- 하나 만들어라)'}
못 지키면: {spec.get('stake') or '(잃을 것을 정하라)'}
지금 남은 시간: {clock}시간
이 장면이 끝날 때 남은 시간은 **{clock}보다 작아야 한다.**
</Clock>

<Recent>
{recap}
</Recent>

<Task_Objective>
아래 조건 중 **하나**를 성립시키는 한 회차 분량의 장면을 설계하라.
{open_conds}
</Task_Objective>
{feedback}

<Output_Format_Instruction>
**JSON 도 XML 도 쓰지 마라.** 추론과 창의성을 최대로 쓰기 위해 Markdown 산문만 쓴다.
아래 제목을 그대로 두고 각 항목을 채워라.

## 장면
(한 문장 요약)

## 성립시키는 조건
(위 조건 목록에서 **한 글자도 다르지 않게** 하나를 그대로 옮겨 적는다)

## 선행 조건
(이 장면이 성립하려면 그 전에 참이어야 하는 것. 없으면 "없음")

## 등장인물
(이름을 쉼표로. 화자가 없으면 그 이유를 한 줄 덧붙인다)

## 공간
(시간·장소·날씨·소리. **그리고 그 공간이 화자에게 무엇인가**)

## 여는 사건
(장면을 여는 최초의 물리적 사건. 누가 무엇을 하는가. 대사로 시작하지 않는다)

## 장치
(되돌아올 사물 하나. 처음엔 무심하게 놓인다)

## 화자의 시야
(화자가 무엇을 보고 **무엇을 놓치는가**. 독자는 알고 화자는 모르는 것을 여기서 만든다)

## 말하지 않는 것
(두 인물이 각각 삼키는 말. 대사는 그 위를 미끄러진다)

## 감정 이동
(narrative_pull 시작값에서 끝값으로. 숫자로)

## 움직이는 사람
(이 장면의 사건을 **일으킨** 사람의 이름 하나. 화자가 스스로 움직였으면 화자의 이름을,
당했으면 상대의 이름을, 아무도 아니면 "사건")

## 치른 대가
(움직인 사람이 그 대가로 잃은 것. 구체적으로. 없으면 "없음" -- 다만 화자가 움직였는데
잃은 것이 없으면 그 장면은 아직 덜 설계된 것이다)

## 남은 시간
(이 장면이 끝난 시점에서 마감까지 **몇 시간** 남았는지. 숫자만. 예: 9)
</Output_Format_Instruction>"""


def _est_rule(open_conds: list) -> str:
    """추출기에게 establishes 를 어떻게 채울지 말해준다.

    서브플롯은 인과에 얹히지 않으므로 열린 조건이 없다. 그때도 목록 지시를 그대로
    보내면 "[] 중에서 하나를 고르라"는 자기모순이 되고, 모델은 빈 목록 대신 그럴듯한
    문자열을 지어낸다 -- 그 한 줄이 서브플롯을 척추로 둔갑시켜 V018 을 흔든다."""
    if not open_conds:
        return ('establishes 는 **빈 목록 []** 으로 둔다. 이 장면은 인과 사슬에 얹히지 않는다 '
                '-- 무엇이든 지어 넣으면 개연성 사슬이 오염된다.')
    return (f'establishes 는 다음 목록 중 시나리오의 "성립시키는 조건" 과 일치하는 것 하나다:\n'
            f'{open_conds}\n'
            f'목록에 없는 문자열을 만들어 넣지 마라. 시나리오가 목록과 다르면 가장 가까운 것을 고른다.')


def extract_prompt(scenario: str, open_conds: list, scale: int) -> str:
    """Markdown 시나리오에서 구조화된 데이터를 뽑는다. **여기서는 JSON 이 맞다.**

    창작이 아니라 데이터 추출이고, 추출은 JSON 이 유리한 태스크다. 이 호출은 값싼 모델로
    보내도 된다 -- 판단하지 않고 옮기기만 하기 때문이다."""
    return f"""아래 시나리오에서 구조화된 값만 뽑아라. **내용을 지어내지 마라.**
시나리오에 없으면 빈 값으로 둔다.

--- 시나리오 ---
{scenario}
--- 끝 ---

{_est_rule(open_conds)}

JSON 만 출력:
{{"beat": "...", "participants": ["..."], "mode": "dialogue",
  "requires": [], "establishes": ["..."], "scale": {scale},
  "driver": "움직이는 사람에 적힌 이름", "cost": "치른 대가",
  "deadline_hours": 남은시간숫자,
  "direction": {{"staging": "...", "trigger": "...", "props": "...",
                "camera": "...", "subtext": "...", "beat_arc": "..."}}}}

deadline_hours 는 **숫자**다. "9시간" 이 아니라 9 로 쓴다."""


def subplot_prompt(novel, ep: int, spine_summary: str, feedback="", done=None) -> str:
    """서브플롯 한 씬. **원패턴을 감추는 것이 목적이다.**

    보고서: 위기-해결-보상의 반복이 노출되면 지루해진다. 조연의 이야기가 사이를 메우고,
    나중에 메인의 해결에 사소하게 이바지한다. 척추와 달리 아무것도 establishes 하지
    않으므로 지워도 사슬이 안 무너진다 -- 그게 서브플롯의 정의다.

    **done 이 이 함수의 핵심이다.** 예전에는 이미 쓴 서브플롯을 알려주지 않았다. 그래서
    프롬프트가 회차마다 거의 같았고(세계 브리프 동일 · 같은 시퀀스면 arc.brief 도 거의
    동일 · spine_summary 는 블록 내내 동일), 같은 입력을 여섯 번 받은 모델이 같은 답을
    냈다. 실측(2026-09-04 탐침): 1·2·3화 서브플롯이 전부 "핫팩을 많이 사는 남자 ->
    연습실에서 손이 얼어붙는 사람" 이었다. 모델 탓이 아니라 알려줄 자리가 없었던 것이다.

    조연도 회차마다 돌린다. 공간을 나눠주지 않으면 모델은 가장 먼저 떠오르는 소재로
    계속 돌아온다."""
    from . import arc
    others = [c.name for c in novel.characters if c.name != novel.pov_character]
    focus = others[(ep - 1) % len(others)] if others else ""
    seen = "\n".join(f"- {b}" for b in (done or [])[-8:])
    return f"""너는 여성향 청춘 로맨스 웹소설의 디렉터다. 메인 사이에 끼울 **서브플롯 한 씬**을
연출한다. 분량의 2/3가 이런 씬이다 -- 여기가 헐거우면 회차가 밋밋해진다.

{_world_brief(novel)}
{_depth_brief(novel)}

[연출에서 정할 것] staging / trigger / props / camera / subtext
{SPLIT}
{arc.brief(ep)}
[이 구간의 메인] {spine_summary}

[이번 씬의 초점 인물] {focus}
  이 인물을 중심에 두어라. 화자와의 관계나 이 인물 자신의 사정에서 출발한다.

[이미 쓴 서브플롯 -- **겹치지 마라**]
{seen or "- (아직 없다)"}
  같은 소재·같은 장소·같은 구도를 반복하지 마라. 위 목록과 다른 축을 잡아라:
  다른 공간(강의실·기숙사·지하철·병원·집), 다른 시간대, 다른 인물, 다른 종류의 마찰.

규칙:
- 메인의 인과를 건드리지 마라. 이 장면은 아무것도 성립시키지 않는다.
- 조연의 이야기이거나 화자의 일상이다. 다만 **메인과 같은 온도**여야 한다.
- 나중에 메인의 해결에 사소하게 이바지할 씨앗 하나를 심어라.
- 화자가 없는 씬이면 그 사실을 "화자의 시야" 에 적어라.
{feedback}

<Output_Format_Instruction>
**JSON 도 XML 도 쓰지 마라.** 척추와 같은 이유다 -- 형식을 지키느라 주의력이 갈리면
2/3를 채우는 이 씬들이 먼저 밋밋해진다. 아래 제목을 그대로 두고 Markdown 으로 쓴다.

## 장면
(한 문장 요약)

## 등장인물
(이름을 쉼표로)

## 공간
(시간·장소·소리. 그리고 그 공간이 화자에게 무엇인가)

## 여는 사건
(장면을 여는 최초의 물리적 사건. 대사로 시작하지 않는다)

## 장치
(되돌아올 사물 하나. 메인의 해결에 사소하게 이바지할 씨앗이면 더 좋다)

## 화자의 시야
(화자가 무엇을 보고 무엇을 놓치는가. 화자가 아예 없으면 그렇게 적는다)

## 말하지 않는 것
(인물들이 각각 삼키는 말)
</Output_Format_Instruction>"""


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

    # **steps 가 척추의 씨앗이다.** requires 는 앞 블록이 이미 갚았으므로 여기서는 거의
    # 항상 비고, 그것만 쓰면 척추가 결말 하나로 끝난다(실측: 2블록부터 척추 1/서브플롯 29).
    #
    # **steps 를 뒤집어 넣는다.** steps 는 사람이 시간순으로 쓴다("쓰기로 한다" 다음에
    # "거절한다"). 그런데 이 루프는 거꾸로 쌓은 뒤 마지막에 spine.reverse() 로 뒤집는다.
    # 시간순 그대로 넣으면 두 번 뒤집혀 인과가 거꾸로 선다 -- 탐침이 실측으로 잡았다:
    # "공명이 거절한다" 가 "설윤이 이의서를 쓴다" 보다 앞에 왔다.
    open_conds = [c for c in (list(reversed(spec.get("steps") or []))
                              + list(spec["requires"]))
                  if c not in entry and not c.startswith("state:")]
    spine, feedback = [], ""

    def _out_of_time() -> bool:
        return EPISODE_DEADLINE is not None and time.time() > EPISODE_DEADLINE

    while open_conds and len(spine) < n_eps and not _out_of_time():
        got = None
        for _ in range(max_repairs + 1):
            # 1단계: 창작 -- Markdown 자유 형식(형식 세금 면제)
            # **한 번에 하나만 요구한다.** 목록을 통째로 주면 모델이 아무거나 골라
            # 갚으므로 거꾸로 쌓는 순서가 무너진다. 다음에 갚을 것 하나만 준다.
            target = open_conds[:1]
            scenario = _llm_for(llm, "director")(
                beat_prompt(novel, spec, target, lo, feedback))
            # 2단계: 추출 -- JSON(데이터 추출은 JSON 이 유리하다). 값싼 모델로 보낸다.
            # **파싱 실패는 여기서 흡수한다.** 위로 던지면 이 결말 블록 열다섯 화가
            # 통째로 버려진다(2026-09-03 밤샘 런이 그렇게 0자로 끝났다).
            try:
                b = call_json(_llm_for(llm, "extractor"),
                              extract_prompt(scenario, target, spec["scale"]),
                              label=f"추출 {lo}~{hi}화")
            except ValueError as e:
                feedback = _fb_text(f"추출기가 이 시나리오에서 JSON 을 못 뽑았다({e}). "
                                    f"항목 제목을 그대로 두고 더 짧고 단순하게 다시 써라. "
                                    f"각 항목은 한두 문장이면 된다.")
                continue
            b.setdefault("direction", {})["scenario"] = scenario
            bad = _check_pressure(b, novel, clock_of(spec, novel))
            if bad:
                # **조용히 기각하지 않는다.** 되먹임만 붙이고 넘어가면 밖에서는 아무 일도
                # 안 일어난 것처럼 보인다 -- 비싼 디렉터 호출이 네 번씩 버려지는데
                # 로그에는 한 줄도 안 남는다. 오늘 아침 밤을 날린 것도 같은 종류의
                # 침묵이었다.
                _log(f"[압박] {lo}~{hi}화 비트 기각: {'; '.join(bad)[:160]}")
                # **여기서 잡아야 한다.** driver/cost/deadline_hours 는 산문이 아니라
                # 선언이라, 씬 관문에서 hard 로 잡으면 수리 루프가 산문만 다시 써서
                # 영원히 못 고친다(V009 가 정확히 그렇게 회차를 세웠다). 조립 단계에서
                # 되돌려보내는 것이 유일하게 고칠 수 있는 자리다.
                feedback = _fb_text("; ".join(bad))
                continue
            est = [e for e in (b.get("establishes") or []) if e in target]
            if est:
                rel_ok, rel_moved = _rel_ops(b.get("relation_ops"), novel,
                                             f"척추 {lo}~{hi}화")
                got = Beat(driver=str(b.get("driver") or ""),
                           cost=str(b.get("cost") or ""),
                           deadline=spec.get("deadline", ""),
                           deadline_hours=float(b.get("deadline_hours") or 0),
                           stake=spec.get("stake", ""),
                           beat=b.get("beat", ""),
                           participants=_people(b.get("participants"), novel,
                                                f"척추 {lo}~{hi}화"),
                           mode=b.get("mode", "dialogue"),
                           requires=list(b.get("requires") or []), establishes=est,
                           world_ops=_ops(b.get("world_ops"),
                                          f"척추 {lo}~{hi}화") + rel_moved,
                           relation_ops=rel_ok,
                           scale=int(b.get("scale") or spec["scale"]),
                           direction=dict(b.get("direction") or {}))
                feedback = ""
                break
            feedback = _fb_text(
                f"establishes 가 열린 조건과 정확히 같지 않다. 받은 값: "
                f"{b.get('establishes')!r} / 지금 갚아야 할 것: {target}. "
                f"**문자열을 그대로 복사하라** -- 한 글자만 달라도 개연성 구멍으로 잡힌다")
        if got is None:
            _log(f"[조립] {lo}~{hi}화 척추 {len(spine)}개에서 멈춘다 -- "
                 f"'{open_conds[0] if open_conds else ''}' 를 갚을 비트를 못 받았다")
            break
        spine.append(got)
        # 조립은 20~40분이 걸리는데 예전에는 시작과 끝에만 줄이 남았다. 그 사이가
        # 통째로 침묵이라 "도는 중" 과 "멈춤" 이 구별되지 않았다. 비트마다 남긴다.
        _log(f"[조립] {lo}~{hi}화 척추 {len(spine)}개째: {got.beat[:44]} "
             f"(움직인 사람 {got.driver or '?'} · 남은 시간 {got.deadline_hours} · "
             f"열린 조건 {len(open_conds) - 1}개)")
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
    # 이 블록에서 이미 쓴 서브플롯 요약. 프롬프트에 실어 겹침을 막고, 기계로도 잰다.
    made: list = []
    for k in range(max(0, need)):
        if _out_of_time():
            _log(f"[episode] 시퀀스 {spec['seq']}: 시간 상한에 걸려 서브플롯 {k}개에서 멈춘다")
            break
        # 씬 단위 서브플롯과 **같은 2단계**를 탄다. 한쪽만 JSON 을 직접 받으면 같은
        # 프롬프트가 두 계약을 갖게 되고, 그 불일치는 조용히 direction 을 비운다.
        b, sub_md, fb = None, "", ""
        for _try in range(3):
            sub_md = _llm_for(llm, "director")(
                subplot_prompt(novel, lo + k, spec["summary"], fb, done=made))
            try:
                b = call_json(_llm_for(llm, "extractor"),
                              extract_prompt(sub_md, [], spec["scale"]),
                              label=f"서브플롯 추출 {lo + k}화")
            except ValueError as e:
                _log(f"[episode] 서브플롯 {lo + k}화 추출 실패 -- 이 칸만 접는다 ({e})")
                b = None
                break
            same = _too_similar(b.get("beat", ""), made)
            if not same:
                break
            _log(f"[중복] 서브플롯 {lo + k}화: '{b.get('beat','')[:34]}' 가 "
                 f"'{same[:34]}' 와 겹친다 -- 다시 받는다")
            fb = _fb_text(f"이미 쓴 '{same}' 와 너무 비슷하다. **다른 인물·다른 공간·"
                          f"다른 종류의 마찰**로 완전히 새 소재를 잡아라")
            b = None
        if b is None:
            continue
        made.append(b.get("beat", ""))
        b.setdefault("direction", {})["scenario"] = sub_md
        filler = Beat(beat=b.get("beat", ""),
                      participants=_people(b.get("participants"), novel,
                                           f"서브플롯 {lo + k}화"),
                      mode=b.get("mode", "dialogue"), establishes=[],
                      world_ops=_ops(b.get("world_ops"), f"서브플롯 {lo + k}화"),
                      scale=int(b.get("scale") or spec["scale"]),
                      direction=dict(b.get("direction") or {}))
        pos = min(len(beats), (k + 1) * max(1, len(beats)) // (need + 1))
        beats.insert(pos, filler)
        _log(f"[조립] {lo}~{hi}화 서브플롯 {k + 1}/{need}: {filler.beat[:44]}")

    # 결말은 마지막 회차다.
    # 결말도 누군가 일으킨다. 비워두면 화자가 구경만 한 회차가 된다
    # -- 결말 회차가 수동으로 판정되면 그 판정 자체가 쓸모없어진다.
    beats.append(Beat(driver=spec.get("driver") or novel.pov_character,
                      cost=spec.get("cost", ""),
                      deadline=spec.get("deadline", ""),
                      stake=spec.get("stake", ""),
                      beat="[결말] " + spec["summary"],
                      participants=[novel.pov_character],
                      requires=list(spec["requires"]),
                      establishes=list(spec["establishes"]),
                      world_ops=list(spec.get("world_ops") or []),
                      relation_ops=list(spec.get("relation_ops") or []),
                      scale=spec["scale"], cliffhanger="shock_line"))

    # **시계는 마지막에 산수로 정한다.** 모델이 낸 숫자는 거꾸로 쌓는 동안 받은 것이라
    # 뒤집고 나면 늘었다 줄었다 한다(탐침 실측: [12.0, 12.5, 0.0]). 디렉터에게 남은
    # 시간을 물은 것은 **그 장면을 시간 압박 위에서 쓰게 하려는 것**이지 그 숫자를 쓰려는
    # 것이 아니었다. 시간순이 확정된 지금 결말의 시계에서 0 까지 고르게 나눈다.
    chain = beats[:body_slots] + beats[-1:]
    total = float(spec.get("deadline_hours") or 72)
    for i, b in enumerate(chain):
        b.deadline = spec.get("deadline", "")
        b.stake = spec.get("stake", "")
        b.deadline_hours = round(total * (len(chain) - 1 - i) / max(1, len(chain) - 1), 1)

    ep = Episode(n=spec["seq"], outcome=Outcome(spec["summary"], spec["requires"]),
                 beats=chain, episodes=(lo, hi))
    # id 는 **회차 범위**로 만든다. 시퀀스 하나에 결말이 여러 개라(시퀀스 1 은 1~10 과
    # 11~20) 시퀀스 번호만 쓰면 id 가 충돌하고, 아래 건너뛰기 판정도 두 번째 결말을
    # 이미 편 것으로 오판한다.
    # 회차 하나 = 척추 1씬 + 서브플롯 2씬. 첫 실측에서 씬 하나가 1,200자였는데 회차는
    # 5,000자라 씬=회차로 두면 분량이 1/4 로 난다. 보고서대로 **서브플롯이 2/3를 채운다.**
    from . import arc
    main_scenes = to_scenes(ep, prefix=f"ep{lo:03d}_", start_ep=lo)
    # 씬 종류 배분(style). **지금까지 쓴 것을 이어서 센다** -- 블록마다 0 에서 시작하면
    # 매 블록의 첫 씬이 같은 종류가 되고, 200화 전체의 비율은 목표에서 멀어진다.
    kinds = style.tally(novel.scenes)

    def _assign(sc, pool) -> None:
        sc.kind = style.pick_kind(pool, kinds)
        kinds[sc.kind] = kinds.get(sc.kind, 0) + 1

    scenes = []
    for i, main in enumerate(main_scenes):
        epno = lo + i
        main.episode, main.is_episode_end, main.cliffhanger = epno, False, ""
        main.id = f"ep{lo:03d}_{epno:03d}m"
        # 척추의 종류는 페르소나가 정한 풀에서 고른다. **블록의 결말 씬만 예외**로
        # 페르소나가 지정한 종류를 쓴다 -- 사이다에서는 가장 큰 성취이고 하드보일드에서는
        # 증발하는 해결이다. 그 자리는 배분이 아니라 형식이 정한다.
        _assign(main, style.spine_pool())
        if i == len(main_scenes) - 1:
            main.kind = style.finale_kind()
            kinds[main.kind] = kinds.get(main.kind, 0) + 1
        scenes.append(main)
        for k in range(arc.SCENES_PER_EPISODE - arc.MAIN_SCENES):
            if _out_of_time():
                break
            b, sub_md, fb = None, "", ""
            for _try in range(3):
                sub_md = _llm_for(llm, "director")(
                    subplot_prompt(novel, epno, spec["summary"], fb, done=made))
                try:
                    b = call_json(_llm_for(llm, "extractor"),
                                  extract_prompt(sub_md, [], spec["scale"]),
                                  label=f"서브플롯 추출 {epno}화")
                except ValueError as e:
                    _log(f"[episode] {epno}화 서브플롯 씬 추출 실패 -- 건너뛴다 ({e})")
                    b = None
                    break
                same = _too_similar(b.get("beat", ""), made)
                if not same:
                    break
                _log(f"[중복] {epno}화 서브플롯 씬: '{b.get('beat','')[:34]}' 가 "
                     f"'{same[:34]}' 와 겹친다 -- 다시 받는다")
                fb = _fb_text(f"이미 쓴 '{same}' 와 너무 비슷하다. **다른 인물·다른 공간·"
                              f"다른 종류의 마찰**로 완전히 새 소재를 잡아라")
                b = None
            if b is None:
                continue
            made.append(b.get("beat", ""))
            b.setdefault("direction", {})["scenario"] = sub_md
            sub = Scene(id=f"ep{lo:03d}_{epno:03d}s{k + 1}",
                        participants=_people(b.get("participants"), novel,
                                             f"서브플롯 {epno}화"),
                        mode=b.get("mode", "dialogue"),
                        directives=[b.get("beat", "")],
                        world_ops=_ops(b.get("world_ops"), f"서브플롯 {epno}화"),
                        scale=int(b.get("scale") or spec["scale"]),
                        direction=dict(b.get("direction") or {}), episode=epno)
            _assign(sub, style.subplot_pool())      # 서브플롯은 페르소나가 정한 풀에서
            scenes.append(sub)
            _log(f"[조립] {epno}화 씬 {len(scenes)}개째 (서브플롯)")
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
    # LLM 이 direction 을 문자열로 낼 때가 있다. isinstance 로 막지 않으면 아래 d.get 이
    # 'str' object has no attribute 'get' 로 터지는데, 그 자리는 원인(추출)에서 한참
    # 떨어진 서술 단계라 로그만 보고는 무엇이 잘못됐는지 알 수 없다.
    d = scene.direction if isinstance(scene.direction, dict) else {}
    if not d:
        return ""
    # 디렉터가 쓴 Markdown 시나리오가 있으면 **그것을 그대로 넘긴다.** 요약해서 넘기면
    # 연출의 결이 그 요약에서 사라진다 -- 디렉터를 좋은 모델로 쓰는 의미가 없어진다.
    if d.get("scenario"):
        return "[디렉터 시나리오]\n" + d["scenario"].strip() + "\n\n"
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

{style.director()}

{_depth_brief(novel)}{style.brief(scene.kind)}{style.episode_brief(scene.episode)}규칙:
- 감정을 직접 말하게 하지 마라. 사물·소리·날씨로 옮겨라.
- punctum 은 한 씬을 여는 감각 하나다. 나중에 되돌아올 수 있는 것으로.

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

{style.actor()}

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


# 분량은 취향이 아니라 규격이다. 관문에서 V019 를 뺀 것은 "몇 자여야 좋은가" 가 의견이라서가
# 아니라 **씬 관문이 잡을 자리가 아니어서**였다 -- 회차가 다 찬 뒤에 hard 를 내면 수리 루프는
# 이미 지나간 씬을 다시 쓰지 못한다. 그래서 여기, 씬을 쓰는 자리로 옮긴다.
#
# 실측(사용자 보고): 회차가 5,000자 목표인데 3,000자로 나왔다. 원인은 지시의 형태다 --
# "5,000자 안팎" 은 모델이 지킬 수 있는 형태가 아니고, 실제로 지켜지지도 않았다. 코드가
# 세고 모자란 만큼을 숫자로 돌려주는 것이 유일하게 작동하는 방법이다.
PROSE_MIN_RATIO = 0.95        # 목표의 이만큼은 채워야 한다
PROSE_EXTEND_TRIES = 4        # 이어쓰기 시도 상한. 넘으면 있는 만큼으로 간다


def extend_prompt(novel, scene, short_by: int) -> str:
    """모자란 만큼을 **이어서** 쓰게 한다. 다시 쓰라고 하면 또 짧게 나온다.

    다시 쓰기(rewrite)를 시켜보면 모델은 같은 길이로 수렴한다 -- 이미 완결된 글을 받고
    "더 길게" 를 들으면 같은 내용을 다르게 배열할 뿐이다. 이어쓰기는 끝 지점이 주어지므로
    새로 쓸 것이 생긴다. 그리고 무엇으로 채울지도 말해준다 -- 사건을 더 넣으라고 하면
    플롯이 부풀고, 그건 조립이 정한 인과를 씬이 멋대로 늘리는 것이다."""
    tail = scene.prose[-600:]
    return f"""아래는 네가 방금 쓴 장면의 끝부분이다. **이어서 계속 써라.**

{style.narrator()}

{style.brief(scene.kind)}[무대] {scene.location} / [감각] {scene.punctum}
[지금까지 쓴 것의 끝]
...{tail}

규칙:
- **{short_by}자 이상 더 써라.** 지금 분량이 목표에 그만큼 모자란다.
- **새 사건을 만들지 마라.** 인과는 이미 정해져 있다. 여기서 늘릴 것은 사건이 아니다:
  · 손이 하는 일을 순서대로 (물을 올리고, 레코드를 고르고, 셔츠를 다린다)
  · 끝없는 내적 독백 -- 결론에 닿지 않아도 된다
  · 메인과 무관한 딴 이야기 (옛 연인, 어젯밤의 꿈, 라디오에서 나오던 곡)
  · 공간의 집요한 묘사 (소리·냄새·빛·먼지)
- 위 끝부분과 자연스럽게 이어져야 한다. 요약하거나 되짚지 마라.
- 문체는 그대로다. 건조한 단문, 느낌표 없음, 감정 직접 서술 없음.

이어질 산문만 출력한다. 머리말도 표식도 쓰지 마라."""


def fill_prose(novel, scene, llm, target: int, log=None) -> int:
    """목표 분량까지 이어쓴다. 반환은 최종 길이. **코드가 센다.**"""
    for _ in range(PROSE_EXTEND_TRIES):
        have = len(scene.prose)
        short_by = target - have
        if have >= target * PROSE_MIN_RATIO:
            return have
        more = _llm_for(llm, "narrator")(
            extend_prompt(novel, scene, short_by)).strip()
        if more.lstrip().startswith(("{", "[")):
            # 산문 자리에 JSON 이 왔다. 붙이면 원고에 중괄호가 박힌다 -- 조용히 섞이면
            # 다음 사람이 읽을 때까지 아무도 모른다.
            _log(f"[분량] 씬 {scene.id}: 이어쓰기가 JSON 으로 왔다 -- 버린다")
            break
        if len(more) < 40:
            # 빈 응답이나 "알겠습니다" 한 줄. 더 두드려도 같은 것이 온다.
            _log(f"[분량] 씬 {scene.id}: 이어쓰기가 {len(more)}자로 돌아왔다 -- 멈춘다")
            break
        scene.prose = scene.prose + "\n\n" + more
        _log(f"[분량] 씬 {scene.id}: {have} -> {len(scene.prose)}자 "
             f"(목표 {target})")
    return len(scene.prose)


def narrator_prompt(novel, scene, feedback="") -> str:
    logs = "\n".join(
        f"  [{t.actor}] 속:{t.inner_thought} / 행동:{t.action} / 말:{t.speech}"
        for t in scene.turns)
    return f"""수집된 로그를 1인칭 회고 산문으로 직조한다.

[화자] {novel.pov_character} — 반드시 "나는 ~했다" 시점
{f"[문장의 색] {novel.voice}" if getattr(novel, "voice", "") else ""}
[무대] {scene.location} / [감각] {scene.punctum}

{style.narrator()}

{_depth_brief(novel)}{style.brief(scene.kind)}{style.episode_brief(scene.episode)}{_direction(scene)}[로그]
{logs}

규칙:
- 다른 인물의 속마음을 사실로 쓰지 마라. 화자가 본 것과 들은 것으로만 옮겨라.
- **연출 지시를 그대로 실행하라.** 여는 사건으로 시작하고, 장치를 무심하게 놓고,
  화자의 시야 밖은 쓰지 마라 -- 화자가 놓친 것은 독자도 놓쳐야 한다.
- **분량: 공백 포함 {__import__("novel.arc", fromlist=["x"]).CHARS_PER_SCENE}자 안팎.**
  회차 하나가 5,000자이고 이 씬은 그중 한 조각이다. **분량은 사건으로 채우지 마라.**
  손이 하는 일, 끝없는 내적 독백, 창밖, 냄새, 소리, 그리고 실없는 딴 이야기로 채운다.
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
    # **산문만 틀렸으면 턴은 다시 만들지 않는다.**
    #
    # 예전에는 시도마다 디렉터·배우·화자를 전부 다시 돌렸다. 산문 규칙(V004 시점 ·
    # V007 화자 부재) 하나가 걸려도 배우 턴 넷을 새로 받았다 -- 턴은 통과했는데도.
    # 실측(2026-09-04 탐침): 씬 하나가 24호출(6호출 x 4시도), 2.3분. 호출 자체는 5.8초라
    # 빠른데 횟수가 문제였다.
    #
    # 단계별로 다시 만든다: 턴 단계에서 막히면 턴부터, 산문 단계에서 막히면 산문만.
    # 그러면 6 + 1 + 1 + 1 = 9호출이 된다.
    #
    # 다만 산문만 두 번 연속 막히면 턴도 다시 만든다 -- 산문이 계속 같은 벽에 부딪히는
    # 것은 턴이 그 벽을 만들고 있다는 뜻일 때가 있다(감정 값이 그렇다).
    redo_turns, prose_only_run = True, 0

    for attempt in range(1, max_repairs + 2):
        # --- 기획 (이미 채워져 있으면 건너뛴다: 템플릿이 준 씬)
        if not scene.location:
            d = _json(_llm_for(llm, "director")(director_prompt(novel, scene, feedback)))
            scene.location = d.get("location", "")
            scene.punctum = d.get("punctum", "")
            scene.directives = d.get("directives") or scene.directives
            # **여기가 새고 있었다.** 경계 검사(_ops/_rel_ops)는 조립 단계에만 걸려
            # 있었고, 씬 기획 단계에서 배우·화자가 낸 ops 는 아무 검사 없이 붙었다.
            # 그래서 'meet(설윤, 재현)' 같은 문자열과 world 동사가 relation_ops 에 그대로
            # 들어갔고, V009 가 "구성원이 두 사람이 아니다: []" 로 매 시도마다 hard 를
            # 냈다 -- 산문이 아니라 선언의 문제라 네 번 다시 써도 안 고쳐졌다(탐침 실측:
            # V009 16회 = 4씬 x 4시도).
            rel_ok, rel_moved = _rel_ops(d.get("relation_ops"), novel, f"씬 {scene.id}")
            scene.world_ops = ((scene.world_ops or [])
                               + _ops(d.get("world_ops"), f"씬 {scene.id}") + rel_moved)
            scene.relation_ops = (scene.relation_ops or []) + rel_ok
            scene.scale = int(d.get("scale") or scene.scale or 0)
            if scene.is_episode_end:
                scene.cliffhanger = d.get("cliffhanger") or scene.cliffhanger

        # --- 연기
        # **직전 시도의 산문을 반드시 지운다.** 안 지우면 아래 턴 단계 관문이 낡은 산문을
        # 그대로 검사해서, 턴이 멀쩡한데도 이전 산문의 위반으로 계속 기각된다 -- 서술
        # 단계까지 가지 못하니 수리가 영원히 안 된다(회귀 검사 test_novel_drive 가 잡았다).
        scene.prose = ""
        # **이미 저장된 씬에도 등장인물 아닌 이름이 있을 수 있다.** 경계(_people)는 앞으로
        # 들어올 것만 막는다. 여기서 한 번 더 거르지 않으면 actor_prompt 안의
        # novel.character(name) 이 KeyError 로 터지고 **회차 전체가 죽는다** -- 실측으로
        # 1~10화가 그렇게 산문 0자로 끝났다. 걸러도 잃는 것은 배경 인물의 대사뿐이고,
        # 그건 화자의 산문이 묘사하면 된다.
        if redo_turns or not scene.turns:
            scene.turns = []
            speakers = _people(scene.participants, novel, f"씬 {scene.id}")
            rounds = 1 if scene.mode == "letter" else 2
            for _ in range(rounds):
                for name in speakers:
                    a = _json(_llm_for(llm, "actor")(
                        actor_prompt(novel, scene, name, feedback)))
                    scene.turns.append(Turn(
                        actor=name, inner_thought=a.get("inner_thought", ""),
                        action=a.get("action", ""), speech=a.get("speech", ""),
                        emotions={k: int(a.get("emotions", {}).get(k, 0)) for k in AXES}))
        else:
            _log(f"[씬 {scene.id}] 산문만 다시 쓴다 (턴 {len(scene.turns)}개 재사용)")

        # --- 관문 1차 (로그 규칙)
        vs = gate.check(scene, novel)
        hard = [v for v in vs if v.severity == "hard"]
        if hard:
            feedback = _fb(hard)
            scene.attempts.append({"attempt": attempt, "stage": "turns",
                                   "violations": [str(v) for v in hard]})
            redo_turns, prose_only_run = True, 0
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
            # 턴은 1차를 통과했으므로 그대로 두고 산문만 다시 쓴다. 다만 두 번 연속
            # 같은 벽이면 턴이 그 벽을 만들고 있을 수 있으니 턴부터 다시 만든다.
            prose_only_run += 1
            redo_turns = prose_only_run >= 2
            if redo_turns:
                prose_only_run = 0
            continue

        # --- 분량 (코드가 세고 모자란 만큼을 숫자로 돌려준다)
        # **관문을 통과한 뒤에 채운다.** 기각될 산문에 이어쓰기를 붙이면 그 호출이 통째로
        # 버려진다 -- 씬 하나가 24호출이던 시절과 같은 낭비다.
        from . import arc as _arc
        fill_prose(novel, scene, llm, _arc.CHARS_PER_SCENE, log)

        scene.status = "verified"
        scene.violations = [str(v) for v in vs]          # soft 는 기록만
        return {"status": "verified", "attempts": attempt, "soft": len(vs),
                "seconds": round(time.time() - t0, 2)}

    scene.status = "failed"
    scene.violations = [str(v) for v in hard]
    return {"status": "failed", "attempts": max_repairs + 1,
            "reason": "관문 위반이 수리 한도 안에 해소되지 않았다",
            "violations": [str(v) for v in hard], "seconds": round(time.time() - t0, 2)}


# ---------------------------------------------------------------- 자유 집필
#
# README 의 "안 됨 / 다음" 에 적어둔 것이다: 배우 JSON 을 거치지 않고 화자가 회차를 통째로
# 쓴 뒤 추출하는 경로.
#
# 왜 필요한가. 씬 단위 집필은 화자에게 "이 씬을 1,666자로 쓰라" 고 시킨다. 그건 분량
# 할당량이고, 할당량은 곧 **희석 지시**다 -- 채우라고 하면 채운다. 회차를 통째로 주면
# 화자가 어디를 늘리고 어디를 자를지 스스로 정한다. 점층과 전환(문장론 3·4번)도 씬 경계에
# 잘리지 않는다.
#
# 그리고 싸다. 씬 3개 x (배우 4 + 화자 1 + 분량보충) ≈ 18호출이 **화자 1 + 보충 1~2**로
# 준다. 배우 턴을 잃지만, 턴은 산문의 재료였지 산문이 아니다.
#
# 잃는 것: 턴 기반 관문(V001 형식·V008 의 턴 부분·V011 믿음)이 검사할 대상이 없어진다.
# 산문 기반 관문(V007 화자 부재·V008 산문 누출·V018 개연성·V009/V010 선언)은 그대로 돈다.
# 그 교환을 알고 쓰는 모드다 -- 그래서 기본값이 아니다.

FREE_MARK = "### 씬 "


def episode_prompt(novel, scenes, target: int, feedback="") -> str:
    """회차 하나를 통째로 쓰는 프롬프트. 씬마다 표식을 달아 돌려받는다."""
    from . import arc
    ep = scenes[0].episode
    # 디렉터가 고른 절단 공식이 있으면 그것을 그대로 준다. 없으면 다섯을 다 보여주고
    # 고르게 한다 -- 지정하지 않으면 모델은 대개 해소로 닫는다.
    picked = next((sc.cliffhanger for sc in scenes if sc.cliffhanger), "")
    if picked and picked in arc.CLIFFHANGERS:
        cliff = f"- 이 회차의 절단 공식: **{arc.CLIFFHANGERS[picked]}**\n"
    else:
        cliff = ("- 절단 공식 다섯 중 하나를 골라 써라:\n"
                 + "".join(f"    · {v}\n" for v in arc.CLIFFHANGERS.values()))
    blocks = []
    for i, sc in enumerate(scenes, 1):
        blocks.append(
            f"{FREE_MARK}{i}\n"
            f"[무대] {sc.location}\n[감각] {sc.punctum}\n"
            f"[이 씬의 종류] {style.kinds().get(sc.kind, {}).get('label', sc.kind)}\n"
            f"[참여자] {sc.participants} / [모드] {sc.mode}\n"
            f"{_direction(sc)}")
    return f"""{ep}화 전체를 쓴다. **씬 세 개를 한 호흡으로 이어서 쓴다.**

[화자] {novel.pov_character} — 반드시 "나는 ~했다" 시점
{f"[문장의 색] {novel.voice}" if getattr(novel, "voice", "") else ""}

{style.narrator()}

{_depth_brief(novel)}{style.episode_brief(ep)}[이 회차의 씬들]
{chr(10).join(blocks)}

규칙:
- **{FREE_MARK}1 · {FREE_MARK}2 · {FREE_MARK}3 표식을 그대로 찍고** 그 아래에 각 씬을 써라.
  표식 말고는 머리말도 번호도 붙이지 마라.
- 씬 사이를 끊지 마라. 앞 씬의 마지막 문장이 다음 씬의 첫 문장으로 이어지게 하라.
- **회차 전체가 공백 포함 {target}자 안팎**이다. 씬마다 균등할 필요는 없다 -- 길게 쓸 곳과
  짧게 끊을 곳을 네가 정해라. 그것이 이 방식의 요점이다.
- 다른 인물의 속마음을 사실로 쓰지 마라. 화자가 본 것과 들은 것으로만 옮겨라.
- 연출 지시를 그대로 실행하라. 화자의 시야 밖은 쓰지 마라.
- **마지막 씬의 끝이 이 회차의 절단면이다.** 해소하지 마라. 위 [엔딩] 규율대로,
  가장 궁금해지는 순간에 짧은 한 줄로 끊어라. 마지막 문장 뒤에 설명을 붙이지 마라.
{cliff}{feedback}

산문만 출력한다. JSON 도 설명도 쓰지 마라."""


def split_episode(text: str, n: int) -> list:
    """표식으로 회차 산문을 씬별로 가른다. 표식이 없거나 모자라면 길이로 나눈다.

    모델이 표식을 빠뜨리는 일은 반드시 생긴다. 그때 통째로 버리면 회차 하나가 날아가므로,
    **길이로라도 나눠서 살린다** -- 경계가 조금 어긋나는 것이 원고가 없는 것보다 낫다."""
    parts = []
    if FREE_MARK in text:
        chunks = text.split(FREE_MARK)
        for ch in chunks[1:]:
            body = ch.split("\n", 1)[1] if "\n" in ch else ""
            if body.strip():
                parts.append(body.strip())
    if len(parts) == n:
        return parts
    _log(f"[자유] 표식이 {len(parts)}개다(필요 {n}개) -- 길이로 나눈다")
    flat = text.replace(FREE_MARK, "").strip()
    size = max(1, len(flat) // n)
    return [flat[i * size:(i + 1) * size if i < n - 1 else None] for i in range(n)]


def write_episode(novel, scenes, llm, log=None) -> dict:
    """회차 하나를 통째로 쓰고 씬에 나눠 담는다. 반환 {status, chars, violations}."""
    from . import arc
    target = arc.CHARS_PER_EPISODE
    t0 = time.time()
    text = _llm_for(llm, "narrator")(episode_prompt(novel, scenes, target)).strip()
    for sc, body in zip(scenes, split_episode(text, len(scenes))):
        sc.prose = body

    # 분량은 코드가 센다. 모자라면 **마지막 씬에 이어 쓴다** -- 회차의 끝을 늘리는 것이
    # 중간을 부풀리는 것보다 낫다(중간을 늘리면 이미 이어놓은 흐름이 끊긴다).
    have = sum(len(sc.prose or "") for sc in scenes)
    if have < target * PROSE_MIN_RATIO:
        fill_prose(novel, scenes[-1], llm,
                   len(scenes[-1].prose or "") + (target - have), log)
        have = sum(len(sc.prose or "") for sc in scenes)

    vs = []
    for sc in scenes:
        vs.extend(gate.check(sc, novel))
    hard = [v for v in vs if v.severity == "hard"]
    for sc in scenes:
        sc.status = "failed" if hard else "verified"
        sc.violations = [str(v) for v in vs]
    _log(f"[자유] {scenes[0].episode}화 {have:,}자 · "
         f"{'기각' if hard else '통과'} · {time.time() - t0:.0f}초")
    return {"status": "failed" if hard else "verified", "chars": have,
            "violations": [str(v) for v in hard]}


def drive_free(novel, path, llm, log, upto_episode: int, skip_blocked: int,
               rounds: int) -> dict:
    """자유 집필: **회차 단위로** 민다. 씬 단위 루프와 같은 계약을 돌려준다."""
    _record(log, {"event": "start", "mode": "free",
                  "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                  "title": novel.title, "scenes": len(novel.scenes)})
    done, failed = 0, 0
    eps = sorted({sc.episode for sc in novel.scenes
                  if sc.episode and not (upto_episode and sc.episode > upto_episode)})
    for rnd in range(1, max(1, rounds) + 1):
        todo = [e for e in eps
                if any(sc.status != "verified" for sc in novel.scenes if sc.episode == e)]
        if not todo:
            break
        if rnd > 1:
            _log(f"[자유] {rnd}바퀴째 -- 미완 {len(todo)}화를 다시 쓴다")
        gained = 0
        for e in todo:
            if EPISODE_DEADLINE is not None and time.time() > EPISODE_DEADLINE:
                _log("[자유] 시간 상한 -- 여기서 멈춘다")
                break
            scenes = [sc for sc in novel.scenes if sc.episode == e]
            r = write_episode(novel, scenes, llm, log)
            _record(log, {"event": "episode", "ep": e,
                          "at": time.strftime("%H:%M:%S"), **r})
            if path:
                novel.save(path)
            if r["status"] == "verified":
                done += 1
                gained += 1
            else:
                failed += 1
                if failed > skip_blocked:
                    break
        if gained == 0:
            break
    blocked = [{"id": sc.id, "episode": sc.episode,
                "why": (sc.violations or [""])[0][:120]}
               for sc in novel.scenes if sc.status == "failed"
               and not (upto_episode and sc.episode > upto_episode)]
    out = {"status": "done" if failed == 0 else ("partial" if done else "blocked"),
           "verified": done, "failed": failed, "blocked": blocked,
           "remaining": sum(1 for sc in novel.scenes if sc.status != "verified"
                            and not (upto_episode and sc.episode > upto_episode))}
    _record(log, {"event": "end", "at": time.strftime("%Y-%m-%d %H:%M:%S"), **out})
    return out


def drive(novel, path, llm=None, max_repairs=MAX_REPAIRS, log=None, limit=None,
          skip_blocked: int = 0, upto_episode: int = 0, rounds: int = 1,
          freewrite: bool = False) -> dict:
    """미완 씬들을 차례로 몰아붙인다. 씬마다 즉시 저장한다.

    skip_blocked -- 막힌 씬을 몇 개까지 넘어갈 것인가. 기본 0 은 예전 그대로 **첫 실패에서
    멈춘다**: 대화형으로 돌릴 때는 막힌 씬을 넘기면 구멍 난 원고가 조용히 쌓이므로 거기서
    멈추고 사람이 보는 편이 낫다.

    무인 야간 런은 반대다. 씬 하나가 관문에 막혔다고 그 뒤 29씬을 손도 못 대면 **열다섯
    화가 통째로 선다** -- 2026-09-04 시험 런이 정확히 그랬다(111초 만에 blocked,
    verified 0). 자는 동안 사람이 풀어줄 수 없으므로, 막힌 것은 failed 로 남겨 기록하고
    다음 씬으로 간다. 구멍은 아침에 read.py 로 보이고 그 회차만 다시 돌리면 된다.

    넘어간 씬은 status="failed" 와 violations 를 그대로 갖고 있어 무엇이 막혔는지 잃지
    않는다.

    upto_episode -- 여기까지의 회차만 채운다(0 이면 전부). 한 회차만 돌려보고 산문이 실제로
    나오는지 확인하는 데 쓴다. 씬 수(limit)가 아니라 **회차**로 자르는 이유: 회차의 끝
    씬에서만 도는 관문(V018 개연성의 회차 단위 판정)이 있어서, 씬 수로
    자르면 회차가 중간에 끊겨 그 관문들이 판정할 대상 자체를 못 갖는다.

    rounds -- 막힌 씬을 **몇 바퀴까지 다시 도는가**. 기본 1 은 예전 그대로 한 바퀴다.

    왜 필요한가(2026-09-04 실측): 12씬 중 9씬이 통과하고 3씬이 막힌 채 런이 끝났다.
    `attempted` 가 한 호출 안에서 같은 씬을 다시 잡지 않게 막는데(그게 없으면 무한
    루프다), 그러면 막힌 씬은 **그 런 안에서 두 번 다시 기회를 얻지 못한다.** 남은 예산이
    다섯 시간이어도 끝난다. 그런데 여기서 실패는 결정론적이지 않다 -- 디렉터·배우·화자를
    새로 뽑으면 다음 바퀴에 통과하는 일이 흔하다(같은 프롬프트에 같은 답이 오는 것은
    되먹임이 없을 때 이야기이고, 실패 사유는 되먹임으로 실린다).

    그래서 한 바퀴가 끝나면 막힌 씬만 pending 으로 되돌리고 다시 돈다. attempts 이력은
    지우지 않는다 -- 무엇이 몇 번 막았는지가 아침에 읽을 유일한 단서다."""
    llm = llm or default_llm      # 콜러블 하나 또는 {역할: 콜러블} dict
    log = log or (Path(path).with_suffix(".scenes.jsonl") if path else None)
    if freewrite:
        return drive_free(novel, path, llm, log, upto_episode, skip_blocked, rounds)
    _record(log, {"event": "start", "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                  "title": novel.title, "scenes": len(novel.scenes)})

    done, failed = 0, 0
    # **이번 호출에서 이미 시도한 씬.** next_pending() 은 "verified 가 아닌 첫 씬" 을
    # 돌려주므로, 막힌 씬을 넘어가려 해도 다음 회차에 같은 씬을 또 집어온다 -- 넘어가는
    # 것이 아니라 무한 루프가 된다(내 회귀 검사가 실측으로 잡았다: 같은 씬을 999번 넘게
    # "넘어간다" 고 찍었다). 밤에 걸었으면 씬 하나로 일곱 시간을 태웠다.
    attempted: set = set()

    def _pass() -> int:
        """막히지 않은 씬을 끝까지 민다. 반환은 이번 바퀴에 막힌 개수."""
        nonlocal done
        stuck_here = 0
        while True:
            scene = next((sc for sc in novel.scenes
                          if sc.status != "verified" and sc.id not in attempted
                          and not (upto_episode and sc.episode > upto_episode)), None)
            if scene is None or (limit and done + stuck_here >= limit):
                return stuck_here
            attempted.add(scene.id)
            r = run_scene(novel, scene, llm, max_repairs, log)
            _record(log, {"event": "scene", "id": scene.id,
                          "at": time.strftime("%H:%M:%S"), **r})
            if path:
                novel.save(path)                          # 씬마다 즉시 저장
            if r["status"] == "verified":
                done += 1
                continue
            stuck_here += 1
            if stuck_here > skip_blocked:
                return stuck_here        # 한도를 넘으면 멈춘다 (기본값 0 = 첫 실패에서)
            _log(f"[drive] {scene.id} 막힘 -- 넘어간다 ({stuck_here}/{skip_blocked}) "
                 f"{(r.get('violations') or [''])[0][:80]}")

    failed = _pass()
    for rnd in range(2, max(1, rounds) + 1):
        stuck = [sc for sc in novel.scenes if sc.status == "failed"
                 and not (upto_episode and sc.episode > upto_episode)]
        if not stuck:
            break
        if EPISODE_DEADLINE is not None and time.time() > EPISODE_DEADLINE:
            _log(f"[drive] 시간 상한이라 {rnd}바퀴째는 돌지 않는다 (막힌 씬 {len(stuck)}개)")
            break
        _log(f"[drive] {rnd}바퀴째 -- 막힌 씬 {len(stuck)}개를 다시 돈다: "
             f"{', '.join(sc.id for sc in stuck[:6])}")
        for sc in stuck:
            sc.status = "pending"        # attempts 이력은 남긴다 -- 아침의 유일한 단서다
        attempted = set()
        failed = _pass()

    # **무엇이 막았는지 함께 돌려준다.** 예전에는 "blocked" 세 글자만 올라와서, 아침에
    # 원고를 열기 전에는 어느 씬이 왜 막혔는지 알 수 없었다.
    blocked = [{"id": sc.id, "episode": sc.episode,
                "why": (sc.violations or [""])[0][:120]}
               for sc in novel.scenes
               if sc.status == "failed"
               and not (upto_episode and sc.episode > upto_episode)]
    out = {"status": "done" if failed == 0 else ("partial" if done else "blocked"),
           "verified": done, "failed": failed, "blocked": blocked,
           "remaining": sum(1 for s in novel.scenes
                            if s.status != "verified"
                            and not (upto_episode and s.episode > upto_episode))}
    _record(log, {"event": "end", "at": time.strftime("%Y-%m-%d %H:%M:%S"), **out})
    return out
