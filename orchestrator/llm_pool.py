"""
쿼터에 견디는 LLM 호출기 -- orchestration의 모든 LLM 호출(플래너 등)이 공유한다.

문제 (실측, VM 로그): Gemini 무료 티어 쿼터는 (프로젝트, 모델) 단위 일일 한도라, 고정 모델
하나로 호출하면 곧 429 RESOURCE_EXHAUSTED 로 죽는다. 게다가 모델은 단종/개명(404, 400
"only supports Interactions API")되고 과부하(503)도 난다. 단일 ChatGoogleGenerativeAI
호출(improve_agent 초기판이 그랬다)은 이 순간 하나만 막혀도 전체가 멈춘다.

해결: 모든 LLM 호출을 (키 x 모델) 후보 풀로 돌린다. 이 저장소가 Discord 에이전트용으로 이미
쓰는 quota_tracker 를 그대로 재사용한다 --
  - 429(일일 한도): record_exhausted 로 오늘자 소진 표시 후 다음 후보.
  - 429(분당 한도, "PerMinute"): record_rpm_cooldown 으로 60초만 밀어둔다. 이것을 일일
    소진으로 적으면 1분이면 풀릴 후보를 자정까지 봉인한다.
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
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # quota_tracker 임포트용
import quota_tracker  # noqa: E402

FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]
ALLOW_PATH = Path(__file__).resolve().parent / "models_allow.json"
MODEL_CACHE = Path(__file__).resolve().parent / ".model_cache.json"

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
# 후보를 더 빨리 넘기는 것으로는 안 풀리는 실패가 있다(실측): 수요 급증 때 Gemini 는 키와
# 모델을 가리지 않고 503 UNAVAILABLE 을 던진다. 후보 12개가 몇 초 만에 전부 타고 끝났고,
# 남은 26개를 더 시도했어도 같은 벽이었다. 이때 필요한 것은 **다음 후보가 아니라 시간**이다.
#
# 그래서 스윕(풀 한 바퀴)을 단위로 재시도한다. 한 바퀴가 전부 실패했는데 그중 일시장애가
# 하나라도 있으면 기다렸다가 다시 돈다. 전부 쿼터 소진(429)이면 기다려도 안 풀리므로 즉시
# 포기한다 -- 일일 한도는 시간이 아니라 날짜로 풀린다.
SWEEPS = int(os.environ.get("GEMINI_SWEEPS", "4"))
BACKOFF_BASE = float(os.environ.get("GEMINI_BACKOFF", "20"))
BACKOFF_MAX = float(os.environ.get("GEMINI_BACKOFF_MAX", "120"))
# 전체 벽시계 상한. 이것이 없으면 최악의 경우 스윕 x 후보 x TIMEOUT 으로 수십 분을 말없이
# 매달린다 -- CLI 에서는 "답이 안 나온다"로만 보인다.
DEADLINE = float(os.environ.get("GEMINI_DEADLINE", "900"))


def _is_quota(e) -> bool:
    t = str(e)
    return "RESOURCE_EXHAUSTED" in t or "429" in t


def _is_permanent(e) -> bool:
    t = str(e)
    return any(m in t for m in ("PERMISSION_DENIED", "403", "FAILED_PRECONDITION",
                                "NOT_FOUND", "404", "billing", "not supported", "not found"))


def _is_rpm(e) -> bool:
    """429 중에서 **1분이면 풀리는 분당 한도**인가. bot_tools.is_rpm_quota_error 와 같은 규칙이다
    (규칙이 바뀌면 둘을 함께 갱신한다 -- llm_pool 은 langchain 없이도 임포트돼야 해서 복제한다).

    Gemini 는 분당 한도와 일일 한도를 둘 다 429 로 준다. 분당 한도의 metric 이름은
    GenerateRequestsPerMinutePerProjectPerModel 이라 "PerMinute" 가 들어간다.

    **가르지 않으면 1분이면 풀릴 후보를 자정까지 봉인한다.** 실측(2026-09-03): 오케스트레이터는
    후보 12~38개를 몇 초 안에 몰아 때리므로 분당 한도에 걸리기 딱 좋다. 그렇게 걸린 429 를
    전부 record_exhausted 로 확정 기록해서, 장부에 count=15000(=일일 한도) 이 박힌 후보가
    8개 생겼다. 사용자는 그날 LLM 을 부른 적이 없다고 했고 그 말이 맞았다 -- 하루치를 쓴 게
    아니라 1분치를 쓴 것을 우리가 하루치로 적은 것이다. quota_tracker 의 주석이 정확히 이
    함정을 경고하고 있었고 bot_tools 는 이미 가르고 있었는데, orchestrator 쪽만 안 갈랐다."""
    t = str(e)
    return _is_quota(e) and ("PerMinute" in t or "per minute" in t.lower())


def _is_transient(e) -> bool:
    """기다리면 풀릴 수 있는 실패인가. 503/504/500/499 계열.

    _is_permanent 보다 **나중에** 물어야 한다. 404/403 은 기다려도 안 풀린다."""
    t = str(e)
    return any(m in t for m in ("UNAVAILABLE", "503", "DEADLINE_EXCEEDED", "504",
                                "INTERNAL", "500", "CANCELLED", "499",
                                "overloaded", "high demand"))


def _model_rank(model: str):
    n = model.lower()
    fam = 3 if "gemma" in n else 2 if "flash-lite" in n else 1 if "flash" in n else 0 if "pro" in n else 4
    return (fam, 1 if "preview" in n else 0)


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


def _norm(name: str) -> str:
    """표시이름과 id 를 같은 자리에 놓고 비교하기 위한 정규화. 영숫자만 남긴다.

    'Gemini 3.5 Flash' -> 'gemini35flash',  'gemini-3.5-flash' -> 'gemini35flash'
    **접두사 비교를 하지 않는다.** 'gemini35flash' 는 'gemini35flashlite' 의 접두사라,
    접두사로 맞추면 Flash 를 고르려다 Flash Lite 를 집는다."""
    return "".join(c for c in name.lower() if c.isalnum())


def _allow_list() -> list:
    """쓰기로 정한 모델의 표시이름. 파일이 없으면 빈 목록(=제한 없음)."""
    if not ALLOW_PATH.is_file():
        return []
    try:
        return list(json.loads(ALLOW_PATH.read_text(encoding="utf-8")).get("allow") or [])
    except Exception:
        return []


def list_models_http(key: str, timeout: float = 30.0) -> list:
    """ListModels 를 표준 라이브러리로 때린다. [(id, displayName)] 를 돌려준다.

    langchain 을 거치지 않는다 -- 후보 목록을 얻는 일까지 그 스택에 얹으면, 목록 조회가
    실패했을 때 그것이 키 문제인지 모델 문제인지 라이브러리 문제인지 알 수 없다."""
    import urllib.request
    url = (f"https://generativelanguage.googleapis.com/v1beta/models"
           f"?key={key}&pageSize=200")
    with urllib.request.urlopen(url, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    out = []
    for m in data.get("models", []):
        if "generateContent" in (m.get("supportedGenerationMethods") or []):
            out.append((m["name"].split("/", 1)[-1], m.get("displayName") or ""))
    return out


def _cache_rw(kid: str, value=None):
    try:
        data = json.loads(MODEL_CACHE.read_text(encoding="utf-8")) if MODEL_CACHE.is_file() else {}
    except Exception:
        data = {}
    if value is None:
        return data.get(kid) or []
    data[kid] = value
    try:
        MODEL_CACHE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass
    return value


def resolve_models(key: str, allow=None, lister=None) -> list:
    """허용 목록(표시이름)을 **실제 API id** 로 바꾼다. 목록 순서가 곧 우선순위다.

    왜 대조하는가. id 를 손으로 적으면 유령 모델을 때리게 된다 -- 'Gemini 3.6 Flash' 가
    'gemini-3.6-flash' 일 것이라는 짐작은 짐작일 뿐이고, 틀리면 404 가 나는데 그 404 가
    다시 '구글이 이상하다'로 읽힌다. ListModels 가 id 와 displayName 을 같이 주므로
    대조하면 짐작이 필요 없다.

    왜 목록을 줄이는가. ListModels 는 40개 넘게 준다. 전부 후보로 삼으면 계획 호출 한
    번에 수십 개를 몇 초 안에 몰아 때려 **분당 한도를 스스로 긁는다.** TTS/임베딩처럼
    generateContent 가 안 되는 것도 섞인다.

    조회에 실패하면 지난번에 풀린 id 를 캐시에서 쓴다. 503 이 나는 동안에도 후보가
    유지돼야 한다 -- 목록을 못 얻었다고 풀이 비면 그것이 또 다른 고장이다."""
    allow = _allow_list() if allow is None else allow
    kid = _key_id(key)
    try:
        pairs = (lister or list_models_http)(key)
    except Exception:
        cached = _cache_rw(kid)
        return cached or FALLBACK_MODELS
    if not allow:
        ids = [i for i, _ in pairs]
        return _cache_rw(kid, ids) if ids else FALLBACK_MODELS

    by_norm = {}
    for mid, disp in pairs:
        by_norm.setdefault(_norm(disp), mid)
        by_norm.setdefault(_norm(mid), mid)
    ids, missing = [], []
    for want in allow:                       # 사람이 적은 순서 = 우선순위
        hit = by_norm.get(_norm(want))
        if hit and hit not in ids:
            ids.append(hit)
        elif not hit:
            missing.append(want)
    if missing:
        print(f"[llm_pool] 허용 목록에 있지만 이 키에 없는 모델: {missing}",
              file=sys.stderr, flush=True)
    return _cache_rw(kid, ids) if ids else (_cache_rw(kid) or FALLBACK_MODELS)


def _default_models(key: str):
    return resolve_models(key) or FALLBACK_MODELS


def _dotenv_candidates():
    """.env 를 찾을 자리. 저장소 루트가 먼저다 -- 어디서 실행하든 같은 키를 쓰게 한다.

    함수로 빼둔 이유는 시험 때문이다. 상수로 박아두면 "저장소 루트에 .env 가 없는
    기계에서만 통과하는 시험"이 되고, 실제로 그랬다 -- 컨테이너에서는 초록인데 VM
    에서는 빨강이었다. VM 에는 진짜 .env 가 있어서 임시 .env 가 읽히지도 않았다."""
    return [Path(__file__).resolve().parent.parent / ".env", Path.cwd() / ".env"]


def _load_dotenv() -> None:
    """저장소 루트의 .env 를 환경에 올린다. **이미 있는 환경변수는 덮지 않는다.**

    왜 필요한가(실측): 키는 .env 에 있고, Discord 봇은 systemd 유닛의
    `EnvironmentFile=/home/ubuntu/SE/.env` 로 그것을 받는다. 그런데 SSH 셸에서
    `python3 ...` 로 직접 돌리면 .env 가 안 실려서 후보 풀이 비고,
    "RuntimeError: 빈 후보 풀" 만 보인다 -- 키가 없는 것처럼 보이지만 실은 있다.

    서비스로 돌 때와 손으로 돌 때가 달라지는 것이 함정의 정체이므로, 여기서 한 번
    맞춰준다. override 하지 않으므로 systemd 로 이미 들어온 값이 우선이다.

    후보를 하나 찾고 멈추지 않고 전부 훑는다. 어차피 덮지 않으므로 앞자리가 이기고,
    앞 파일에 없는 변수만 뒤에서 채워진다."""
    for cand in _dotenv_candidates():
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


def build_pool(keys=None, models=None, llm_factory=_default_factory, model_lister=_default_models):
    """(label, llm) 후보 목록. keys 기본 = 환경변수 두 키. models 기본 = 키별 실사용 모델 조회."""
    if keys is None:
        if not os.environ.get("GEMINI_API_KEY"):
            _load_dotenv()
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


def _ranked(pool, pool_id: str):
    """후보를 쿼터 잔량 / 모델 등급 순으로 세운다. 스윕마다 다시 매긴다 -- 직전 스윕에서
    죽은(404/403) 후보가 자동으로 빠지고, 소진된(429) 후보가 뒤로 밀린다."""
    live = [c for c in pool if not quota_tracker.is_dead(c[0])] or pool

    def sort_key(c):
        label = c[0]
        model = label.split(":", 1)[1] if ":" in label else label
        rem = quota_tracker.remaining(label)
        return (rem <= 0, _model_rank(model), -rem)

    ranked = sorted(live, key=sort_key)
    pinned = quota_tracker.get_pinned(pool_id)
    if pinned:
        ranked = [c for c in ranked if c[0] == pinned] + [c for c in ranked if c[0] != pinned]
    return ranked


def call(pool, prompt: str, pool_id: str = "orchestrator", max_candidates: int = None,
         verbose: bool = True, sweeps: int = None, sleep=time.sleep,
         clock=time.monotonic) -> tuple[str, str]:
    """후보를 쿼터/장애 견디며 순회. (응답텍스트, 성공한 label) 반환. 전부 실패면 예외.

    두 겹으로 버틴다.

      후보 순회  한 스윕 안에서 (키 x 모델) 후보를 순서대로 시도한다. 429 는 소진 기록,
                 404/403 은 영구 제외, 나머지는 그냥 다음 후보. max_candidates 로 시도
                 수를 제한한다 -- 상한이 없으면 죽은 키로 돌릴 때 수십 개 x 타임아웃만큼
                 말없이 매달린다.
      스윕 재시도 **한 바퀴가 통째로 실패했을 때가 진짜 문제다.** 실측(2026-09-03):
                 수요 급증에 Gemini 가 키와 모델을 가리지 않고 503 을 던져 후보 12개가 몇
                 초 만에 전부 탔다. 이때 필요한 것은 다음 후보가 아니라 시간이다. 그래서
                 실패 중 일시장애가 하나라도 있으면 지수 백오프로 기다렸다가 다시 돈다.
                 전부 쿼터 소진이면 즉시 포기한다 -- 일일 한도는 날짜로 풀린다.

    **스윕마다 시간 예산을 나눠 준다.** 이것이 없으면 스윕 재시도가 무력해진다(실측,
    2026-09-03 두 번째 런): 504 DEADLINE_EXCEEDED 는 후보 하나가 TIMEOUT(60s)을 통째로
    먹으므로, 12후보 스윕 하나가 720s 를 삼켰다. 전체 상한 900s 는 스윕 2 중간에 끊겼고
    스윕 3, 4 는 돌지도 못했다. 후보를 더 태우는 데 시간을 다 쓴 것이다.

    과부하 구간에서 값이 있는 것은 다음 후보가 아니라 기다림이므로, 한 스윕이
    DEADLINE/스윕수 를 넘기면 남은 후보를 포기하고 백오프로 넘어간다. 그래야 상한
    900s 가 "4번 시도를 15분에 걸쳐 펼친다"가 된다.

    sleep 과 clock 을 주입할 수 있다(시험에서 실제로 기다리지 않기 위해)."""
    limit = MAX_CANDIDATES if max_candidates is None else max_candidates
    n_sweeps = max(1, SWEEPS if sweeps is None else sweeps)
    per_sweep = DEADLINE / n_sweeps       # 스윕 하나가 먹을 수 있는 시간
    t0 = clock()
    last_error, total_tried, ranked, out_of_time = None, 0, _ranked(pool, pool_id), False

    for sweep in range(1, n_sweeps + 1):
        if sweep > 1:
            ranked = _ranked(pool, pool_id)
        skipped = max(0, len(ranked) - limit)
        tried = transient = 0
        sweep_t0 = clock()
        for label, llm in ranked[:limit]:
            if clock() - t0 > DEADLINE:
                out_of_time = True
                if verbose:
                    print(f"[llm_pool] 전체 상한 {DEADLINE:.0f}s 를 넘겨 중단한다",
                          file=sys.stderr, flush=True)
                break
            # 스윕 시간 예산. 504 처럼 후보 하나가 TIMEOUT 을 통째로 먹는 실패에서는
            # 후보를 더 태우는 것보다 기다리는 편이 낫다.
            if tried and clock() - sweep_t0 > per_sweep:
                if verbose:
                    print(f"[llm_pool] 스윕 {sweep} 시간 예산 {per_sweep:.0f}s 를 넘겼다 "
                          f"-- 남은 후보 대신 백오프로 넘어간다", file=sys.stderr, flush=True)
                break
            tried += 1
            total_tried += 1
            try:
                text = _extract_text(llm.invoke(prompt))
                quota_tracker.record_success(label)
                quota_tracker.set_pinned(pool_id, label)
                return text, label
            except Exception as e:
                if _is_rpm(e):
                    quota_tracker.record_rpm_cooldown(label)
                elif _is_quota(e):
                    quota_tracker.record_exhausted(label)
                elif _is_permanent(e):
                    quota_tracker.mark_dead(label, str(e)[:200])
                elif _is_transient(e):
                    transient += 1
                if verbose:
                    print(f"[llm_pool] {label} 실패(스윕 {sweep}, {tried}/"
                          f"{min(limit, len(ranked))}): {str(e)[:120]}",
                          file=sys.stderr, flush=True)
                last_error = e
        if out_of_time or not tried or not transient:
            break                       # 빈 풀이거나, 기다려도 안 풀리는 실패만 남았다
        if sweep >= n_sweeps:
            break
        wait = min(BACKOFF_MAX, BACKOFF_BASE * 2 ** (sweep - 1))
        if clock() - t0 + wait > DEADLINE:
            break
        if verbose:
            print(f"[llm_pool] 스윕 {sweep}/{n_sweeps}: 후보 {tried}개가 모두 실패했고 "
                  f"그중 {transient}개가 일시장애다. 후보를 더 넘겨도 같은 벽이므로 "
                  f"{wait:.0f}s 기다렸다가 다시 돈다", file=sys.stderr, flush=True)
        sleep(wait)

    if last_error:
        raise RuntimeError(
            f"후보 {total_tried}회 시도가 모두 실패했다"
            f"{f' (상한 {limit} 때문에 {skipped}개는 시도 안 함)' if skipped else ''}"
            f"{f', 스윕 {n_sweeps}회' if n_sweeps > 1 else ''}. "
            f"마지막 오류: {type(last_error).__name__}: {last_error}\n"
            f"  일시장애(503/504)가 계속되면 업스트림 과부하다 -- 코드로 못 푼다. "
            f"{'전체 상한 %.0fs 를 다 썼다. GEMINI_DEADLINE 을 늘리거나 ' % DEADLINE if out_of_time else ''}"
            f"GEMINI_SWEEPS / GEMINI_BACKOFF 를 늘리거나 나중에 다시 돌려라.") from last_error
    raise RuntimeError(
        "빈 후보 풀 -- GEMINI_API_KEY 를 찾지 못했다.\n"
        "  환경변수에도 없고 저장소 루트 .env 에도 없다.\n"
        "  systemd 서비스는 EnvironmentFile 로 .env 를 받지만 SSH 셸은 그렇지 않다.\n"
        "  확인:  grep -c GEMINI_API_KEY ~/SE/.env\n"
        "  즉시:  set -a; source ~/SE/.env; set +a")
