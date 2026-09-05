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
import concurrent.futures as cf
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # quota_tracker 임포트용
import quota_tracker  # noqa: E402

FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]

# **pro 계열은 후보에서 뺀다.** 무료 티어에서 pro 의 분당 한도는 flash 계열의 몇 분의 일이라,
# 후보에 끼워 두면 거의 매번 429 만 받아 오면서 그 키의 벌점만 올린다 -- 답을 주지도 않고
# 다음 시도를 늦추기만 하는 후보다(실측 로그: pro-latest / 3.1-pro-preview 가 매 바퀴 429).
# 산문 품질은 화자 프롬프트가 정하지 모델 등급이 정하지 않는다. 되살리려면
# GEMINI_ALLOW_PRO=1 을 준다.
SKIP_MODEL = re.compile(os.environ.get("GEMINI_SKIP_MODEL", r"pro"), re.I)
ALLOW_PRO = os.environ.get("GEMINI_ALLOW_PRO", "") not in ("", "0", "false")

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

# **같은 후보를 연달아 때리지 않는다.** 이것이 "잔여량은 남았는데 429" 의 진짜 원인이었다.
#
# 무료 티어 RPM 은 (프로젝트, 모델) 당 분당 몇 회다. 그런데 이 파이프라인은 씬 하나에
# 디렉터·추출기·배우 넷·화자를 몇 초 안에 연달아 부른다. 성공한 후보를 pin 해서 매번 그것을
# 먼저 두드리면 **그 하나가 몇 초 만에 자기 RPM 을 다 쓴다.** pin 은 일일 소진을 피하려고
# 만든 것인데 RPM 에는 정반대로 작동했다.
#
# 그래서 최근에 쓴 후보는 뒤로 민다. 키 2개 x 모델 N 개를 **번갈아** 쓰면 유효 RPM 이 그만큼
# 곱해진다 -- 후보가 여덟이고 간격이 6초면 초당 하나씩 쏴도 아무도 자기 한도에 닿지 않는다.
# **한 번에 여러 후보에게 동시에 던진다.** 먼저 답하는 것을 쓴다.
#
# 구글 문서 기준으로 RPM 은 **모델별**로 따로 걸린다(무료: 2.5 Pro 5 · Flash 10 ·
# Flash-Lite 15). 그러니 서로 다른 모델은 각자의 통을 쓰고, 동시에 던져도 서로의 한도를
# 깎지 않는다. 직렬로 하나씩 두드리며 사이사이 기다리면 그 통들을 놀리는 것이다
# (실측 2026-09-05: 후보 12개 × 간격 8초 × 3바퀴 = 최악 7.3분).
FANOUT = int(os.environ.get("GEMINI_FANOUT", "3"))
MIN_GAP = float(os.environ.get("GEMINI_MIN_GAP", "8"))   # 같은 통을 다시 쓰기까지(초)
# 429 를 맞은 키는 이만큼 더 쉰다. 한도가 키에 걸리므로 형제 모델도 같이 쉬어야 한다.
KEY_PENALTY = float(os.environ.get("GEMINI_KEY_PENALTY", "30"))

# 이 프로세스가 각 후보를 마지막으로 부른 시각. 파일에 안 남긴다 -- RPM 은 60초짜리라
# 프로세스 수명보다 짧고, 파일 잠금 비용을 매 호출마다 물 이유가 없다.
_LAST_USED: dict = {}
# **키 단위로도 잰다.** 분당 한도는 키(프로젝트)에 걸리지 모델마다 따로 걸리지 않는다.
# 그런데 후보는 `키:모델` 이라, 한 키에 모델이 넷이면 넷이 각자 "6초 지났으니 괜찮다" 고
# 판단해 같은 키를 잇달아 두드린다 -- 그러면 간격을 지킨 셈인데도 429 가 온다
# (실측 2026-09-05: 서로 다른 키가 연달아 RPM 으로 떨어졌다).
_LAST_KEY: dict = {}
# 후보별 응답 시간(성공했을 때). **이름으로 짐작하지 말고 재서 쓴다.**
#
# 실측 2026-09-05(탐침): 같은 "flash" 인데 gemini-flash-lite-latest 는 1.0초,
# gemini-3.5-flash 는 12.7초였다. 열세 배다. 이름 기반 등급(_model_rank)은 세대가
# 바뀔 때마다 낡는데, 걸린 시간은 안 낡는다.
_LAT: dict = {}
LAT_MEMORY = 0.7          # 새 측정을 이만큼 반영한다(나머지는 옛값)


def _lat(label: str) -> float:
    """이 후보의 응답 시간 추정.

    **안 재본 것은 0으로 둔다 -- 낙관한다.** 중간값으로 두면 한 번 이긴 후보가 계속
    앞에 서고 나머지는 영원히 안 재본 채로 남는다(실측: 0.4초짜리가 계속 뽑히는 동안
    0.05초짜리는 한 번도 안 불렸다). 모르는 것을 먼저 재보는 편이 낫다 -- 어차피 묶음으로
    던지니 느린 후보가 섞여도 손해가 없고, 몇 번이면 전부 재진다.
    """
    return _LAT.get(label, 0.0)


def _retry_delay(e) -> float:
    """429 응답에 실린 retryDelay(초). 구글이 직접 알려 주는 값이라 추측보다 낫다."""
    m = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", str(e))
    return float(m.group(1)) if m else 0.0


def _key_of(label: str) -> str:
    """`키:모델` 에서 키만. 한도가 걸리는 단위다."""
    return label.split(":", 1)[0] if ":" in label else label


def _since_key(label: str) -> float:
    """이 **키**를 마지막으로 쓴 뒤 흐른 시간."""
    t = _LAST_KEY.get(_key_of(label))
    return 1e9 if t is None else time.time() - t


def _since_used(label: str) -> float:
    """마지막으로 쓴 지 몇 초 지났나. 한 번도 안 썼으면 아주 큰 값."""
    t = _LAST_USED.get(label)
    return 1e9 if t is None else time.time() - t


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
            if not ALLOW_PRO and SKIP_MODEL.search(m):
                continue
            pool.append((f"key-{kid}:{m}", llm_factory(m, key)))
    if not pool and keys:          # 전부 걸러졌으면 거르지 않는다 -- 빈 풀보다는 낫다
        for key in keys:
            kid = _key_id(key)
            for m in (models or model_lister(key)):
                pool.append((f"key-{kid}:{m}", llm_factory(m, key)))
    return pool


def _extract_text(resp) -> str:
    content = getattr(resp, "content", resp)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return str(content)


def _note_failure(label: str, e, verbose: bool) -> str:
    """실패 하나를 갈래대로 기록하고 갈래 이름을 돌려준다."""
    if _is_rpm(e):
        quota_tracker.record_rpm_cooldown(label)
        # **구글이 알려 준 만큼 쉰다.** 429 응답에 retryDelay 가 실려 오면 그것이 추측보다
        # 정확하다. 없으면 KEY_PENALTY 로 물러난다. 한도는 키에 걸리므로 형제 모델도 같이.
        back = _retry_delay(e) or KEY_PENALTY
        _LAST_KEY[_key_of(label)] = time.time() + back - MIN_GAP
        kind = "RPM/60초"
    elif _is_quota(e):
        quota_tracker.record_exhausted(label)
        kind = "일일소진"
    elif _is_permanent(e):
        quota_tracker.mark_dead(label, str(e)[:200])
        kind = "영구배제"
    else:
        kind = "일시장애"
    if verbose:
        print(f"[llm_pool] {label} 실패 [{kind}]: {str(e)[:120]}",
              file=sys.stderr, flush=True)
    return kind


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
        # **방금 쓴 후보는 뒤로.** 이것이 첫 번째 정렬 키다 -- 모델 등급보다 앞선다.
        # 좋은 모델이라도 3초 전에 썼으면 지금 두드려봐야 429 만 받는다.
        # 키 간격이 먼저다 -- 모델을 바꿔 봐야 같은 키면 같은 한도를 쓴다.
        # 그 다음은 **재본 응답 시간**이다. 이름 등급은 재본 적 없는 후보의 기본값으로만
        # 쓴다 -- 한 번이라도 재봤으면 그 숫자가 이름보다 정확하다.
        return (_since_key(label) < MIN_GAP, _since_used(label) < MIN_GAP,
                rem <= 0, round(_lat(label), 1), _model_rank(model), -rem)

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
        # pin 은 **간격을 지킬 때만** 앞으로 당긴다. 방금 쓴 것을 또 앞에 두면 그 하나가
        # 자기 RPM 을 다 쓰고, 나머지 후보는 놀면서 런이 죽는다.
        pinned = quota_tracker.get_pinned(pool_id)
        if pinned and _since_used(pinned) >= MIN_GAP:
            ranked = ([c for c in ranked if c[0] == pinned]
                      + [c for c in ranked if c[0] != pinned])
        skipped = max(0, len(ranked) - limit)

        # 후보 전부가 방금 쓴 것들이면 두드려봐야 429 다. 가장 오래된 것이 간격을 채울
        # 만큼만 기다린다 -- 몇 초다. 이 몇 초가 바퀴 하나를 통째로 살린다.
        if ranked:
            oldest = max(min(_since_used(c[0]), _since_key(c[0]))
                         for c in ranked[:limit])
            if oldest < MIN_GAP:
                nap = MIN_GAP - oldest
                if verbose:
                    print(f"[llm_pool] 후보가 전부 {oldest:.1f}초 전에 쓰였다 -- "
                          f"{nap:.1f}초 쉰다 (RPM 회피)", file=sys.stderr, flush=True)
                time.sleep(nap)

        only_transient = True          # 이 바퀴가 전부 "기다리면 풀리는" 실패였는가
        queue = list(ranked[:limit])
        # **처음엔 하나만 던진다.** 동시 발사는 같은 프롬프트를 복제해서 던지고 제일 빨리
        # 온 것만 쓴다 -- 첫 후보가 어차피 성공할 상황에서는 쿼터를 배로 태우고 나머지는
        # 버리는 것이다. 속도를 사려고 쿼터를 파는 셈인데, 쿼터가 병목이면 정확히 거꾸로
        # 작동한다(실측: 키 둘의 모든 모델이 동시에 429). 그래서 폭은 1 에서 시작해
        # **실패할 때만** 넓힌다. 잘 도는 런은 호출 한 번, 막힌 런만 여러 발이다.
        width = 1

        # **묶음으로 동시에 던진다.** RPM 은 모델별로 따로 걸리므로 서로 다른 통에 던지는
        # 것은 서로의 한도를 안 깎는다. 직렬로 하나씩 두드리며 사이사이 기다리면 그 통들을
        # 놀리는 것이고, 그것이 후보 12개에 7분이 걸리던 이유였다.
        while queue:
            queue.sort(key=sort_key)
            # **한 묶음에 같은 키를 두 번 넣지 않는다.** 한도는 모델이 아니라 키
            # (프로젝트)에 걸린다. 예전에는 키:모델 단위로만 걸러서, 동시에 던진 셋이
            # 전부 같은 키인 일이 흔했다 -- 같은 통을 세 번 때리니 셋이 같이 429 를 받고,
            # 같이 벌점을 물고, 37 초를 자고, 다시 같은 짓을 했다(실측: 그렇게 10분).
            # 키로 거르면 묶음 하나가 서로 다른 프로젝트 셋을 쓴다.
            batch, seen_keys, held = [], set(), []
            while queue and len(batch) < max(1, min(width, FANOUT)):
                cand = queue.pop(0)
                k = _key_of(cand[0])
                if k in seen_keys:
                    held.append(cand)            # 이번 묶음엔 안 쓴다, 버리지도 않는다
                    continue
                seen_keys.add(k)
                batch.append(cand)
            queue = held + queue
            if not batch:
                break

            # 이 묶음에서 제일 빨리 준비되는 만큼만 **한 번** 쉰다. 후보마다 쉬지 않는다.
            # 제일 빨리 준비되는 만큼만 쉬고, 그때까지도 아직 안 풀린 것은 이번 묶음에서
            # 뺀다. 안 그러면 벌점 먹은 키가 묶음에 얹혀 그대로 또 429 를 받는다.
            nap = min(max(0.0, MIN_GAP - _since_key(lb)) for lb, _ in batch)
            if nap > 0:
                if verbose:
                    print(f"[llm_pool] {nap:.1f}초 쉬고 {len(batch)}개를 동시에 던진다",
                          file=sys.stderr, flush=True)
                time.sleep(nap)
                ready = [c for c in batch if _since_key(c[0]) >= MIN_GAP]
                if ready and len(ready) < len(batch):
                    queue = [c for c in batch if c not in ready] + queue
                    batch = ready

            now = time.time()
            for lb, _ in batch:
                _LAST_USED[lb] = now
                _LAST_KEY[_key_of(lb)] = now
            tried += len(batch)

            # **with 을 안 쓴다.** 블록을 나갈 때 shutdown(wait=True) 가 걸려서, 먼저 답한
            # 것을 쓰고도 제일 느린 후보를 끝까지 기다리게 된다(실측: 0.1초에 받아 놓고
            # 1.2초를 버렸다). 남은 것은 버리고 간다 -- 어차피 안 쓸 답이다.
            pool_x = cf.ThreadPoolExecutor(max_workers=len(batch))
            futs = {pool_x.submit(lambda l=llm: _extract_text(l.invoke(prompt))): lb
                    for lb, llm in batch}
            won = None
            try:
                for fut in cf.as_completed(futs):
                    label = futs[fut]
                    try:
                        text = fut.result()
                    except Exception as e:
                        last_error = e
                        kind = _note_failure(label, e, verbose)
                        if kind in ("일일소진", "영구배제"):
                            only_transient = False
                        continue
                    quota_tracker.record_success(label)
                    quota_tracker.set_pinned(pool_id, label)
                    took = time.time() - now
                    _LAT[label] = (LAT_MEMORY * took
                                   + (1 - LAT_MEMORY) * _LAT.get(label, took))
                    won = (text, label)
                    break
            finally:
                pool_x.shutdown(wait=False, cancel_futures=True)
            if won:
                return won
            width = min(max(1, FANOUT), width + 1)   # 막혔다 -- 다음 묶음은 넓게

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
