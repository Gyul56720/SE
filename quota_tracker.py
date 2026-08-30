"""
(API 키, 모델) 조합별로 오늘 몇 번 호출했는지 로컬에 세어서, 실제 429를 맞기 전에
"이 조합은 오늘 다 썼을 것"이라고 미리 추정하는 트래커.

왜 필요한가: 429가 실제로 나기까지 langchain 내부 재시도/backoff 때문에 매번 30~50초가
걸린다(실측 확인됨, 2026-08-28). 소진된 조합인 걸 이미 알면서도 매 메시지마다 그 조합을
먼저 찔러보고 기다리는 건 낭비다. 여기서는 두 가지로 미리 안다:

1. 카운트 기반 추정: 무료 티어 한도(기본 500/일)에 다가가는 걸 로컬 카운터로 추적해서,
   한도 근처면 실제로 429가 나기 전에 먼저 건너뛴다. Google이 정확한 잔여량을 API로
   안 주기 때문에 완벽하진 않다(추정치일 뿐) -- 그래서 실제 429를 맞으면 그 즉시 카운터를
   한도까지 강제로 채워서 확정 소진 처리한다(2번).
2. 실측 소진: 429를 실제로 맞으면 그 조합을 "오늘 UTC 자정까지 소진"으로 확정 기록한다.
   (quotaId가 GenerateRequestsPerDayPerProjectPerModel-FreeTier로 일일 쿼터라서 리셋
   시점을 UTC 자정으로 잡는다.)

여기에 더해 429에는 성격이 다른 둘이 섞여 있다는 점을 다룬다. 일일 한도(RPD)는 자정까지
안 풀리지만 분당 한도(RPM, GenerateRequestsPerMinutePerProjectPerModel)는 1분이면 풀린다.
RPM까지 일일 소진으로 처리하면 ReAct 루프처럼 짧은 시간에 여러 번 호출하다 걸렸을 뿐인
멀쩡한 최상위 조합이 하루 종일 봉인된다. 그래서 RPM은 60초짜리 쿨다운(_rpm_cooldown)으로
따로 처리하고, 일일 소진 기록은 그대로 유지한다 -- 둘 중 하나만 남기면 반대쪽 낭비가 생긴다
(RPM만 남기면 진짜 소진된 키를 1분마다 다시 두드리며 매번 수십 초 backoff를 문다).

Discord 이벤트 루프에서 동기 파일 I/O를 쓰지만, JSON 파일 하나 읽고 원자적으로 쓰는 정도라
사용자 응답 시간에 체감될 정도로 느리지 않다 -- 응답을 먼저 만든 뒤에 이 기록을 남기므로
사용자가 기다리는 구간에는 들어가지 않는다.

[_LOCK 재진입 주의] threading.Lock은 재진입이 안 된다. _LOCK을 잡은 함수가 같은 락을 잡는
다른 공개 함수(is_rpm_cooling 등)를 부르면 그 자리에서 영구 교착한다(실측 확인됨,
2026-08-30 -- get_pinned가 락을 쥔 채 is_rpm_cooling을 불러 프로세스가 멈췄다). 락 안에서는
반드시 _cooling_until 같은 '락 없는 내부 헬퍼'를 쓸 것.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent / "Public_agent" / "quota_state.json"
DEFAULT_DAILY_LIMIT = 500
# 분당 한도(RPM) 429를 맞았을 때 그 조합을 쉬게 하는 시간. Gemini 무료 티어의 RPM 창이
# 1분이므로 60초면 충분하다.
RPM_COOLDOWN_SECONDS = 60
_LOCK = threading.Lock()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)  # 원자적 교체


def _entry(data: dict, label: str) -> dict:
    """label의 오늘자 기록을 반환한다. 날짜가 바뀌었으면(=쿼터 리셋) 0으로 초기화."""
    rec = data.get(label)
    if not rec or rec.get("date") != _today():
        rec = {"date": _today(), "count": 0}
        data[label] = rec
    return rec


def record_success(label: str) -> None:
    """호출이 실제로 성공했음을 기록해서 카운터를 올린다."""
    with _LOCK:
        data = _load()
        rec = _entry(data, label)
        rec["count"] += 1
        _save(data)


def record_exhausted(label: str, limit: int = DEFAULT_DAILY_LIMIT) -> None:
    """일일 한도(RPD) 429를 맞았다는 걸 확정 기록한다 -- 카운트 추정이 틀렸더라도 이걸로
    확실히 한도에 도달한 걸로 처리해서, 오늘 안에는 다시 이 조합을 먼저 시도하지 않게 한다.

    분당 한도(RPM)는 여기가 아니라 record_rpm_cooldown 이 처리한다. 둘을 합쳐 놓으면
    자정까지 못 쓸 키를 1분마다 다시 두드리거나(합쳐서 쿨다운으로 처리한 경우), 1분이면
    풀릴 키를 하루 종일 봉인하게(합쳐서 소진으로 처리한 경우) 된다."""
    with _LOCK:
        data = _load()
        rec = _entry(data, label)
        rec["count"] = max(rec["count"], limit)
        _save(data)


def record_rpm_cooldown(label: str, seconds: int = RPM_COOLDOWN_SECONDS) -> None:
    """분당 한도 429를 맞았을 때 호출. 이 조합을 seconds 동안만 쉬게 한다."""
    with _LOCK:
        data = _load()
        cooling = data.setdefault("_rpm_cooldown", {})
        cooling[label] = time.time() + seconds
        _save(data)


def _cooling_until(data: dict, label: str) -> float:
    """_LOCK을 이미 잡은 쪽에서 쓰는 내부 헬퍼 (모듈 독스트링의 재진입 주의 참고)."""
    try:
        return float(data.get("_rpm_cooldown", {}).get(label, 0.0))
    except (TypeError, ValueError):
        return 0.0


def is_rpm_cooling(label: str) -> bool:
    """지금 이 조합이 RPM 쿨다운 중인가."""
    with _LOCK:
        return _cooling_until(_load(), label) > time.time()


def rpm_cooldown_remaining(label: str) -> float:
    """쿨다운이 풀리기까지 남은 초. 쿨다운 중이 아니면 0.0."""
    with _LOCK:
        return max(0.0, _cooling_until(_load(), label) - time.time())


def remaining(label: str, limit: int = DEFAULT_DAILY_LIMIT) -> int:
    """오늘 남았을 것으로 추정되는 호출 수. 기록이 없으면(=오늘 한 번도 안 씀) limit 그대로.
    RPM 쿨다운 중이면 0을 돌려줘서 후보 정렬에서 뒤로 밀리게 한다 -- 쿨다운이 끝나면
    저절로 원래 잔량으로 돌아온다(별도 해제 작업이 필요 없다)."""
    with _LOCK:
        data = _load()
        if _cooling_until(data, label) > time.time():
            return 0
        rec = data.get(label)
        if not rec or rec.get("date") != _today():
            return limit
        return max(0, limit - rec["count"])


# 429(쿼터 소진)는 매일 자정에 리셋되니까 "오늘자" 기록(위)이면 충분하다. 근데 404(모델
# 단종/무료 티어에 아예 없음)나 403(유료 전용, billing 필요)은 다르다 -- 이런 건 하루가
# 지나도 안 풀린다. 그런데 이걸 오늘자 기록과 똑같이 취급했더니, 자정이 지나면(또는
# quota_state.json을 지우면) 이미 죽은 걸 알고 있던 모델을 처음부터 또 다 두드려보는
# 낭비가 있었다(실측 확인됨, 2026-08-28 -- gemini-2.5-pro/gemini-2.5-flash/gemini-pro-latest
# 같은 단종 모델을 매 요청마다 다시 시도). 그래서 영구 소진은 날짜 리셋이 없는 별도
# 목록("_dead")에 한 번 기록하면 끝까지 건너뛴다 -- "다음 질문이 오기 전에 이미 준비된
# 상태"를 만드는 핵심이 이 부분이다.
def mark_dead(label: str, reason: str = "") -> None:
    with _LOCK:
        data = _load()
        dead = data.setdefault("_dead", {})
        dead[label] = reason
        _save(data)


def is_dead(label: str) -> bool:
    with _LOCK:
        data = _load()
        return label in data.get("_dead", {})


# "다음 질문이 오기 전에 이미 준비해두기"의 핵심 -- 매 요청마다 순위를 계산해서 1등을
# 고르는 대신, 직전에 실제로 성공했던 조합을 그대로 다음 요청에서도 제일 먼저 쓴다.
# pool_id(예: "public-agent", "admin-agent")별로 하나씩 기억한다.
def set_pinned(pool_id: str, label: str) -> None:
    with _LOCK:
        data = _load()
        pins = data.setdefault("_pinned", {})
        pins[pool_id] = label
        _save(data)


def get_pinned(pool_id: str) -> "str | None":
    """pin된 조합. 단, 그게 지금 RPM 쿨다운 중이면 None을 돌려준다 -- pin은 후보 정렬을
    통째로 건너뛰고 맨 앞에 꽂는 장치라, 쿨다운 중인 조합이 pin돼 있으면 remaining()이
    0을 돌려줘도 소용없이 매번 먼저 시도돼서 쿨다운이 무력화되기 때문이다."""
    with _LOCK:
        data = _load()
        pinned = data.get("_pinned", {}).get(pool_id)
        if pinned and _cooling_until(data, pinned) > time.time():
            return None
        return pinned
