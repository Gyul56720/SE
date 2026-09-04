"""
쿼터에 견디는 LLM 호출기 -- orchestration의 모든 LLM 호출(플래너 등)이 공유한다.

문제 (실측, VM 로그): Gemini 무료 티어 쿼터는 (프로젝트, 모델) 단위 일일 한도라, 고정 모델
하나로 호출하면 곧 429 RESOURCE_EXHAUSTED 로 죽는다. 게다가 모델은 단종/개명(404, 400
"only supports Interactions API")되고 과부하(503)도 난다. 단일 ChatGoogleGenerativeAI
호출(improve_agent 초기판이 그랬다)은 이 순간 하나만 막혀도 전체가 멈춘다.

해결: 모든 LLM 호출을 (키 x 모델) 후보 풀로 돌린다. 이 저장소가 Discord 에이전트용으로 이미
쓰는 quota_tracker 를 그대로 재사용한다 --
  - 429(쿼터 소진): record_exhausted 로 오늘자 소진 표시 후 다음 후보.
  - 404/403(단종/유료전용): mark_dead 로 영구 제외(자정에도 안 풀림).
  - 503/500(일시 장애): 다음 후보(영구 제외 안 함).
  - 성공: record_success + 그 후보를 pin -> 다음 호출도 그걸 먼저.
이로써 "Gemini API 자동 변경"이 자동으로, 매 orchestration 호출마다 처리된다.

의존: quota_tracker(경량, 이 저장소) 만 필수. 실제 Gemini 클라이언트/모델 목록 조회는 지연
임포트하고, llm_factory 를 주입할 수 있어(테스트에서 목 주입) 폴백 로직만 따로 검증 가능하다.
에러 분류기는 bot_tools 와 같은 규칙(문자열 매칭)을 여기서도 갖는다 -- orchestrator 가
langchain 없이도 임포트되도록 자체 정의한다(규칙이 바뀌면 bot_tools 와 함께 갱신).
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # quota_tracker 임포트용
import quota_tracker  # noqa: E402

FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]

# 후보 하나에 얼마나 버틸 것인가. bot_tools 가 실측으로 얻은 값과 같은 규칙을 여기서도 갖는다
# (langchain 없이도 임포트되게 값만 복제한다 -- 규칙이 바뀌면 bot_tools 와 함께 갱신).
# langchain 기본값(max_retries=6, timeout 없음)을 그대로 쓰면 실패하는 후보 하나가 지수 backoff
# 로 30~50초를 먹고, timeout 이 없어 응답이 안 오는 요청은 영원히 매달린다. 후보 풀 자체가
# 재시도 전략이므로 한 후보 안에서 오래 버틸 이유가 없다.
MAX_RETRIES = int(os.environ.get("GEMINI_MAX_RETRIES", "2"))
TIMEOUT = float(os.environ.get("GEMINI_TIMEOUT", "60"))
# 풀은 (키 x 실사용 모델) 이라 모델 목록 조회 결과에 따라 수십~백 개가 될 수 있다. 전부 순회하면
# 최악의 경우 시간 단위로 매달리므로, 시도 후보 수에 상한을 둔다(최악 대기 = 상한 x TIMEOUT).
MAX_CANDIDATES = int(os.environ.get("GEMINI_MAX_CANDIDATES", "12"))

# **RPM 은 기다리면 풀린다.** 후보를 전부 두드렸는데 실패 사유가 전부 분당 한도(429/RPM)나
# 일시 장애(503)뿐이면, 그것은 "이 키로는 못 한다" 가 아니라 "지금은 못 한다" 다. 예전에는
# 거기서 예외를 던졌고, 야간 런은 그 한 번으로 블록을 통째로 잃었다(실측: 1~3화와 4~5화가
# 2분 간격으로 같은 이유로 죽었다). 쿨다운이 풀릴 때까지 기다렸다 다시 돈다.
RPM_ROUNDS = int(os.environ.get("GEMINI_RPM_ROUNDS", "3"))       # 총 시도 바퀴 수
RPM_MAX_WAIT = float(os.environ.get("GEMINI_RPM_MAX_WAIT", "75"))  # 한 바퀴 최대 대기(초)


def _is_quota(e) -> bool:
    t = str(e)
    return "RESOURCE_EXHAUSTED" in t or "429" in t


def _is_rpm(e) -> bool:
    """429 중에서도 **1분이면 풀리는** 분당 한도인가.

    bot_tools.is_rpm_quota_error 와 같은 판정을 여기로 가져왔다. 봇 경로는 이미 구분하고
    있었는데 이 풀은 아니어서, 모든 429 를 자정까지 소진으로 확정하고 있었다.
    quota_tracker 가 그러지 말라고 적어둔 바로 그 실수다:

        "둘을 합쳐 놓으면 ... 1분이면 풀릴 키를 하루 종일 봉인하게 된다"

    야간 런에서 이게 치명적이다. 후보가 넷뿐인데 몇 초 안에 여러 번 호출하다 RPM 에 걸리면
    멀쩡한 조합이 차례로 봉인되고, 몇 분 만에 풀이 비어 남은 밤이 통째로 날아간다.

    판별 실패면 False -- 일일 소진을 분당으로 잘못 보면 1분마다 죽은 조합을 다시 두드린다.
    모르는 것은 보수적으로 일일 소진 취급하는 쪽이 안전하다(bot_tools 와 같은 판단)."""
    t = str(e)
    return _is_quota(e) and ("PerMinute" in t or "per minute" in t.lower())


def _is_permanent(e) -> bool:
    t = str(e)
    return any(m in t for m in ("PERMISSION_DENIED", "403", "FAILED_PRECONDITION",
                                "NOT_FOUND", "404", "billing", "not supported", "not found"))


def _model_rank(model: str):
    """후보 순서. **분당 한도(RPM)에 강한 것부터 간다.**

    예전에는 pro 를 맨 앞에 뒀다(fam 0). 품질 순서였는데, 무료 티어에서 그 순서는 정확히
    거꾸로다 -- pro 와 preview 계열은 RPM 이 가장 빡빡해서 몇 호출 만에 429 를 낸다.
    2026-09-04 VM 실측 로그가 그것이다: 12개 후보를 순서대로 두드렸는데 pro-latest,
    3.1-pro-preview, 3.1-pro-preview-customtools, omni-* 가 전부 429 [RPM/60초] 였고,
    **상한 12개를 그것들로 다 써버려 flash 계열에 닿지도 못한 채** 블록이 통째로 예외로
    끝났다. 429 를 맞은 pro 는 품질이 0 이다. 안 도는 모델은 좋은 모델이 아니다.

    그래서 flash-lite -> flash -> pro -> gemma 순으로 뒤집는다. 그리고 preview 는 어느
    계열이든 뒤로 민다(쿼터가 실험적이고 예고 없이 바뀐다). 품질이 중요한 자리(디렉터)는
    이제 Claude 가 맡으므로, 이 풀은 **양이 많은 배우·화자·추출기**를 감당하는 것이
    본업이다 -- 거기서는 도는 것이 곧 품질이다."""
    n = model.lower()
    if "gemma" in n:
        fam = 3
    elif "flash-lite" in n:
        fam = 0
    elif "flash" in n:
        fam = 1
    elif "pro" in n:
        fam = 2
    else:
        fam = 4
    # preview/experimental 은 같은 계열 안에서 맨 뒤로. customtools 같은 변종도 여기 걸린다.
    exp = 1 if any(w in n for w in ("preview", "exp", "customtools")) else 0
    return (fam, exp)


def _key_id(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:8]


def _default_factory(model: str, key: str):
    """max_retries/timeout 을 모르는 langchain 버전에서도 뜨도록 TypeError 면 물러선다."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    try:
        return ChatGoogleGenerativeAI(model=model, google_api_key=key,
                                      max_retries=MAX_RETRIES, timeout=TIMEOUT)
    except TypeError:
        return ChatGoogleGenerativeAI(model=model, google_api_key=key)


def _default_models(key: str):
    try:
        from bot_tools import list_available_models
        return list_available_models(key) or FALLBACK_MODELS
    except Exception:
        return FALLBACK_MODELS


def _load_dotenv_once() -> None:
    """저장소 루트의 .env 를 환경에 올린다. **이미 있는 환경변수는 덮지 않는다.**

    왜 필요한가(실측): 키는 .env 에 있고, Discord 봇은 systemd 유닛의
    `EnvironmentFile=/home/ubuntu/SE/.env` 로 그것을 받는다. 그런데 SSH 셸에서
    `python3 ...` 로 직접 돌리면 .env 가 안 실려서 후보 풀이 비고,
    "RuntimeError: 빈 후보 풀" 만 보인다 -- 키가 없는 것처럼 보이지만 실은 있다.

    서비스로 돌 때와 손으로 돌 때가 달라지는 것이 함정의 정체이므로, 여기서 한 번
    맞춰준다. override 하지 않으므로 systemd 로 이미 들어온 값이 우선이다."""
    for cand in (Path(__file__).resolve().parent.parent / ".env", Path.cwd() / ".env"):
        if not cand.is_file():
            continue
        try:
            from dotenv import load_dotenv
            load_dotenv(cand, override=False)
        except ImportError:
            # python-dotenv 가 없어도 돌아야 한다. 이 경로가 조용히 물러나면
            # "키가 없는 것처럼 보이지만 실은 있다"는 함정이 그대로 남는다.
            for line in cand.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("'\"")
                if k and k not in os.environ:          # 기존 환경변수를 덮지 않는다
                    os.environ[k] = v
        return


def build_pool(keys=None, models=None, llm_factory=_default_factory, model_lister=_default_models):
    """(label, llm) 후보 목록. keys 기본 = 환경변수 두 키. models 기본 = 키별 실사용 모델 조회."""
    if keys is None:
        if not os.environ.get("GEMINI_API_KEY"):
            _load_dotenv_once()
        keys = [k for k in (os.environ.get("GEMINI_API_KEY"),
                            os.environ.get("GEMINI_API_KEY_FALLBACK")) if k]
    pool = []
    for key in keys:
        if not key:
            continue
        kid = _key_id(key)
        kmodels = models or model_lister(key)
        for m in kmodels:
            pool.append((f"key-{kid}:{m}", llm_factory(m, key)))
    return pool


def _extract_text(resp) -> str:
    content = getattr(resp, "content", resp)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return str(content)


def call(pool, prompt: str, pool_id: str = "orchestrator", max_candidates: int = None,
         verbose: bool = True) -> tuple[str, str]:
    """후보를 쿼터/장애 견디며 순회. (응답텍스트, 성공한 label) 반환. 전부 실패면 예외.

    max_candidates 로 시도 수를 제한한다(기본 MAX_CANDIDATES). 상한이 없으면 죽은 키로 돌릴 때
    수십 개 후보 x 타임아웃만큼 말없이 매달린다 -- CLI 에서는 "답이 안 나온다"로만 보인다.
    verbose 면 실패한 후보를 stderr 에 한 줄씩 남긴다(어디서 막혔는지 보이게)."""
    live = [c for c in pool if not quota_tracker.is_dead(c[0])] or pool

    def sort_key(c):
        label = c[0]
        model = label.split(":", 1)[1] if ":" in label else label
        rem = quota_tracker.remaining(label)
        return (rem <= 0, _model_rank(model), -rem)

    limit = MAX_CANDIDATES if max_candidates is None else max_candidates
    last_error, tried, skipped = None, 0, 0

    # **바퀴를 돈다.** 한 바퀴가 전부 RPM/일시장애로 끝났으면 그것은 "이 키로는 못 한다" 가
    # 아니라 "지금은 못 한다" 다. 쿨다운이 풀릴 만큼 기다렸다 다시 돈다.
    for rnd in range(1, max(1, RPM_ROUNDS) + 1):
        # **잔량이 없는 후보는 아예 빼고 시도한다.** 예전에는 sort_key 로 뒤에 밀어두기만
        # 해서 여전히 순회 대상이었다 -- 소진된 조합 하나마다 왕복 한 번과 429 대기를 물고,
        # 상한(MAX_CANDIDATES)까지 그것으로 채우면 **멀쩡한 후보에 닿지도 못한다**.
        #
        # remaining() 은 일일 소진과 RPM 쿨다운을 모두 0 으로 돌려주므로 이 한 줄이 둘 다
        # 건너뛴다. 바퀴를 다시 돌 때는 쿨다운이 풀려 잔량이 돌아와 있다.
        #
        # 전부 0 이면 그때는 거르지 않는다 -- 추정이 틀렸을 수 있고(카운터는 휴리스틱이다),
        # 아무것도 시도하지 않고 실패하는 것보다 한 번 두드려보는 편이 낫다.
        fresh = [c for c in live if quota_tracker.remaining(c[0]) > 0]
        if verbose and len(fresh) < len(live):
            print(f"[llm_pool] 잔량 없는 후보 {len(live) - len(fresh)}개를 건너뛴다 "
                  f"(남은 후보 {len(fresh)}개)", file=sys.stderr, flush=True)
        ranked = sorted(fresh or live, key=sort_key)
        pinned = quota_tracker.get_pinned(pool_id)
        if pinned:
            ranked = ([c for c in ranked if c[0] == pinned]
                      + [c for c in ranked if c[0] != pinned])
        skipped = max(0, len(ranked) - limit)

        only_transient = True          # 이 바퀴가 전부 "기다리면 풀리는" 실패였는가
        for label, llm in ranked[:limit]:
            tried += 1
            try:
                text = _extract_text(llm.invoke(prompt))
                quota_tracker.record_success(label)
                quota_tracker.set_pinned(pool_id, label)
                return text, label
            except Exception as e:
                # **어느 갈래로 판정했는지 로그에 남긴다.** 예전에는 str(e)[:120] 만 찍었는데,
                # RPM 과 일일 소진을 가르는 quotaId 는 그 뒤에 나온다 -- 분류는 제대로
                # 하면서도 사람이 로그로 확인할 방법이 없었다.
                if _is_rpm(e):
                    quota_tracker.record_rpm_cooldown(label)
                    kind = "RPM/60초"
                elif _is_quota(e):
                    quota_tracker.record_exhausted(label)
                    kind = "일일소진"
                    only_transient = False
                elif _is_permanent(e):
                    quota_tracker.mark_dead(label, str(e)[:200])
                    kind = "영구배제"
                    only_transient = False
                else:
                    kind = "일시장애"      # 503 등은 기록 없이 다음 후보로
                if verbose:
                    print(f"[llm_pool] {label} 실패({tried}/{min(limit, len(ranked))}"
                          f"{f' · {rnd}바퀴' if rnd > 1 else ''}) "
                          f"[{kind}]: {str(e)[:100]}", file=sys.stderr, flush=True)
                last_error = e

        if rnd >= max(1, RPM_ROUNDS) or not only_transient:
            break
        # 가장 빨리 풀리는 쿨다운까지만 기다린다. 하나라도 살아나면 다음 바퀴가 성공한다.
        waits = [quota_tracker.rpm_cooldown_remaining(c[0]) for c in live]
        waits = [w for w in waits if w > 0]
        wait = min(min(waits) + 2, RPM_MAX_WAIT) if waits else 10.0
        if verbose:
            print(f"[llm_pool] 한 바퀴가 전부 RPM/일시장애다 -- {wait:.0f}초 기다렸다 "
                  f"다시 돈다 ({rnd}/{RPM_ROUNDS}바퀴)", file=sys.stderr, flush=True)
        time.sleep(wait)

    if last_error:
        raise RuntimeError(
            f"후보 {tried}개를 모두 실패했다"
            f"{f' (상한 {limit} 때문에 {skipped}개는 시도 안 함)' if skipped else ''}. "
            f"마지막 오류: {type(last_error).__name__}: {last_error}") from last_error
    raise RuntimeError(
        "빈 후보 풀 -- GEMINI_API_KEY 를 찾지 못했다.\n"
        "  환경변수에도 없고 저장소 루트 .env 에도 없다.\n"
        "  systemd 서비스는 EnvironmentFile 로 .env 를 받지만 SSH 셸은 그렇지 않다.\n"
        "  확인:  grep -c GEMINI_API_KEY ~/SE/.env\n"
        "  즉시:  set -a; source ~/SE/.env; set +a")
