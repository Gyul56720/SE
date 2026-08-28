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

Discord 이벤트 루프에서 동기 파일 I/O를 쓰지만, JSON 파일 하나 읽고 원자적으로 쓰는 정도라
사용자 응답 시간에 체감될 정도로 느리지 않다 -- 응답을 먼저 만든 뒤에 이 기록을 남기므로
사용자가 기다리는 구간에는 들어가지 않는다.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent / "Public_agent" / "quota_state.json"
DEFAULT_DAILY_LIMIT = 500
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
    """실제 429를 맞았다는 걸 확정 기록한다 -- 카운트 추정이 틀렸더라도 이걸로 확실히
    한도에 도달한 걸로 처리해서, 오늘 안에는 다시 이 조합을 먼저 시도하지 않게 한다."""
    with _LOCK:
        data = _load()
        rec = _entry(data, label)
        rec["count"] = max(rec["count"], limit)
        _save(data)


def remaining(label: str, limit: int = DEFAULT_DAILY_LIMIT) -> int:
    """오늘 남았을 것으로 추정되는 호출 수. 기록이 없으면(=오늘 한 번도 안 씀) limit 그대로."""
    with _LOCK:
        data = _load()
        rec = data.get(label)
        if not rec or rec.get("date") != _today():
            return limit
        return max(0, limit - rec["count"])


def rank_candidates(candidates: "list[tuple[str, object]]", limit: int = DEFAULT_DAILY_LIMIT
                     ) -> "list[tuple[str, object]]":
    """남은 추정 쿼터가 많은 순으로 후보를 재정렬한다. 소진 예상(잔량 0)인 후보는 맨
    뒤로 밀리되, 다 소진 상태여도(추정이 틀렸을 수 있으니) 완전히 제거하지는 않는다 --
    최후의 수단으로라도 시도는 되게 남겨둔다."""
    return sorted(candidates, key=lambda c: remaining(c[0], limit), reverse=True)
