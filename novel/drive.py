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
    한 장면 당하는 것은 병이 아니다. 그 연속은 관문(V022)이 회차 단위로 본다."""
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


def _rel_ops(raw, novel, label: str = "") -> list:
    """relation_ops 에서 **쓸 수 있는 선언만** 남긴다.

    관계 선언은 members 가 서로 다른 두 등장인물이어야 한다. 아니면 V009 가 hard 로 잡는데,
    수리 루프는 산문만 다시 쓰므로 **문장을 백 번 고쳐도 그 배열은 안 바뀐다** -- 그 씬은
    시도 횟수를 다 쓰고 결정론적으로 실패하고, 그 뒤 씬들까지 세운다(2026-09-04 시험 런:
    "관계 구성원이 두 사람이 아니다: []" 로 4번 시도 111초, verified 0).

    고칠 수 없는 선언은 경계에서 버린다. 잃는 것은 관계 선언 하나이고, 사는 것은 그 회차다."""
    names = {c.name for c in novel.characters}
    kept = []
    for o in _ops(raw, label):
        m = list(o.get("members") or [])
        if len(m) == 2 and m[0] != m[1] and all(x in names for x in m):
            kept.append(o)
        else:
            _log(f"[ops] {label}: 쓸 수 없는 관계 선언을 버렸다 -- members={m}")
    return kept


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
    """한 회차 분량의 **시나리오**를 받는다. 입력은 XML, 출력은 Markdown.

    형식 세금(Format Tax): 출력 형식을 JSON/XML 로 강제하면 모델이 문장을 지으면서 동시에
    문법 유효성을 지켜야 해서 주의력이 갈리고, 개방형 창작에서 품질이 떨어진다. 그래서
    **창작은 Markdown 자유 형식으로 받는다.**

    그런데 관문(V009 관계·V018 개연성·V013 진도)은 구조화된 데이터를 먹고 산다. 산문만
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

    open_conds = [c for c in spec["requires"]
                  if c not in entry and not c.startswith("state:")]
    spine, feedback = [], ""

    def _out_of_time() -> bool:
        return EPISODE_DEADLINE is not None and time.time() > EPISODE_DEADLINE

    while open_conds and len(spine) < n_eps and not _out_of_time():
        got = None
        for _ in range(max_repairs + 1):
            # 1단계: 창작 -- Markdown 자유 형식(형식 세금 면제)
            scenario = _llm_for(llm, "director")(
                beat_prompt(novel, spec, open_conds, lo, feedback))
            # 2단계: 추출 -- JSON(데이터 추출은 JSON 이 유리하다). 값싼 모델로 보낸다.
            # **파싱 실패는 여기서 흡수한다.** 위로 던지면 이 결말 블록 열다섯 화가
            # 통째로 버려진다(2026-09-03 밤샘 런이 그렇게 0자로 끝났다).
            try:
                b = call_json(_llm_for(llm, "extractor"),
                              extract_prompt(scenario, open_conds, spec["scale"]),
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
            est = [e for e in (b.get("establishes") or []) if e in open_conds]
            if est:
                got = Beat(driver=str(b.get("driver") or ""),
                           cost=str(b.get("cost") or ""),
                           deadline=spec.get("deadline", ""),
                           deadline_hours=float(b.get("deadline_hours") or 0),
                           stake=spec.get("stake", ""),
                           beat=b.get("beat", ""),
                           participants=b.get("participants") or [novel.pov_character],
                           mode=b.get("mode", "dialogue"),
                           requires=list(b.get("requires") or []), establishes=est,
                           world_ops=_ops(b.get("world_ops"), f"척추 {lo}~{hi}화"),
                           relation_ops=_rel_ops(b.get("relation_ops"), novel, f"척추 {lo}~{hi}화"),
                           scale=int(b.get("scale") or spec["scale"]),
                           direction=dict(b.get("direction") or {}))
                feedback = ""
                break
            feedback = _fb_text(
                f"establishes 가 열린 조건과 정확히 같지 않다. 받은 값: "
                f"{b.get('establishes')!r} / 열린 조건: {open_conds}. "
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
    for k in range(max(0, need)):
        if _out_of_time():
            _log(f"[episode] 시퀀스 {spec['seq']}: 시간 상한에 걸려 서브플롯 {k}개에서 멈춘다")
            break
        # 씬 단위 서브플롯과 **같은 2단계**를 탄다. 한쪽만 JSON 을 직접 받으면 같은
        # 프롬프트가 두 계약을 갖게 되고, 그 불일치는 조용히 direction 을 비운다.
        sub_md = _llm_for(llm, "director")(
            subplot_prompt(novel, lo + k, spec["summary"]))
        try:
            b = call_json(_llm_for(llm, "extractor"),
                          extract_prompt(sub_md, [], spec["scale"]),
                          label=f"서브플롯 추출 {lo + k}화")
        except ValueError as e:
            _log(f"[episode] 서브플롯 {lo + k}화 추출 실패 -- 이 칸만 접는다 ({e})")
            continue
        b.setdefault("direction", {})["scenario"] = sub_md
        filler = Beat(beat=b.get("beat", ""),
                      participants=b.get("participants") or [novel.pov_character],
                      mode=b.get("mode", "dialogue"), establishes=[],
                      world_ops=_ops(b.get("world_ops"), f"서브플롯 {lo + k}화"),
                      scale=int(b.get("scale") or spec["scale"]),
                      direction=dict(b.get("direction") or {}))
        pos = min(len(beats), (k + 1) * max(1, len(beats)) // (need + 1))
        beats.insert(pos, filler)
        _log(f"[조립] {lo}~{hi}화 서브플롯 {k + 1}/{need}: {filler.beat[:44]}")

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
            if _out_of_time():
                break
            sub_md = _llm_for(llm, "director")(
                subplot_prompt(novel, epno, spec["summary"]))
            try:
                b = call_json(_llm_for(llm, "extractor"),
                              extract_prompt(sub_md, [], spec["scale"]),
                              label=f"서브플롯 추출 {epno}화")
            except ValueError as e:
                _log(f"[episode] {epno}화 서브플롯 씬 추출 실패 -- 건너뛴다 ({e})")
                continue
            b.setdefault("direction", {})["scenario"] = sub_md
            sub = Scene(id=f"ep{lo:03d}_{epno:03d}s{k + 1}",
                        participants=b.get("participants") or [novel.pov_character],
                        mode=b.get("mode", "dialogue"),
                        directives=[b.get("beat", "")],
                        world_ops=_ops(b.get("world_ops"), f"서브플롯 {epno}화"),
                        scale=int(b.get("scale") or spec["scale"]),
                        direction=dict(b.get("direction") or {}), episode=epno)
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


def drive(novel, path, llm=None, max_repairs=MAX_REPAIRS, log=None, limit=None,
          skip_blocked: int = 0, upto_episode: int = 0) -> dict:
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
    씬에서만 도는 관문(V016 클리프행어·V017 회차 마무리·V019 분량)이 있어서, 씬 수로
    자르면 회차가 중간에 끊겨 그 관문들이 판정할 대상 자체를 못 갖는다."""
    llm = llm or default_llm      # 콜러블 하나 또는 {역할: 콜러블} dict
    log = log or (Path(path).with_suffix(".scenes.jsonl") if path else None)
    _record(log, {"event": "start", "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                  "title": novel.title, "scenes": len(novel.scenes)})

    done, failed = 0, 0
    # **이번 호출에서 이미 시도한 씬.** next_pending() 은 "verified 가 아닌 첫 씬" 을
    # 돌려주므로, 막힌 씬을 넘어가려 해도 다음 회차에 같은 씬을 또 집어온다 -- 넘어가는
    # 것이 아니라 무한 루프가 된다(내 회귀 검사가 실측으로 잡았다: 같은 씬을 999번 넘게
    # "넘어간다" 고 찍었다). 밤에 걸었으면 씬 하나로 일곱 시간을 태웠다.
    attempted: set = set()
    while True:
        scene = next((sc for sc in novel.scenes
                      if sc.status != "verified" and sc.id not in attempted
                      and not (upto_episode and sc.episode > upto_episode)), None)
        if scene is None or (limit and done + failed >= limit):
            break
        attempted.add(scene.id)
        r = run_scene(novel, scene, llm, max_repairs, log)
        _record(log, {"event": "scene", "id": scene.id, "at": time.strftime("%H:%M:%S"), **r})
        if path:
            novel.save(path)                              # 씬마다 즉시 저장
        if r["status"] == "verified":
            done += 1
        else:
            failed += 1
            if failed > skip_blocked:
                break                    # 한도를 넘으면 멈춘다 (기본값 0 = 첫 실패에서)
            _log(f"[drive] {scene.id} 막힘 -- 넘어간다 ({failed}/{skip_blocked}) "
                 f"{(r.get('violations') or [''])[0][:80]}")

    out = {"status": "done" if failed == 0 else ("partial" if done else "blocked"),
           "verified": done, "failed": failed,
           "remaining": sum(1 for s in novel.scenes
                            if s.status != "verified"
                            and not (upto_episode and s.episode > upto_episode))}
    _record(log, {"event": "end", "at": time.strftime("%Y-%m-%d %H:%M:%S"), **out})
    return out
