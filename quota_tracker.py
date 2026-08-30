"""
(API 키, 모델) 조합별로 오늘 몇 번 호출했는지 로컬에 세어서, 실제 429를 맞기 전에
"이 조합은 오늘 다 썼을 것"이라고 미리 추정하는 트래커.

RPM(분당 제한) 쿨다운 추가:
429 에러가 일일 쿼터(RPD) 소진이 아닌 분당 쿼터(RPM) 초과인 경우, 자정까지 죽이는 대신
60초 동안만 일시적으로 차단하여 1분 후 최우선 모델로 자동 복귀하게 한다.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent / "Public_agent" / "quota_state.json"
DEFAULT_DAILY_LIMIT = 500
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
    """429 분당 제한(RPM) 초과 발생 시 60초간 쿨다운 처리한다."""
    with _LOCK:
        data = _load()
        cooldowns = data.setdefault("_rpm_cooldown", {})
        cooldowns[label] = time.time() + RPM_COOLDOWN_SECONDS
        _save(data)


def is_rpm_cooling(label: str) -> bool:
    """해당 조합이 현재 60초 쿨다운 중인지 확인한다."""
    with _LOCK:
        data = _load()
        cooldowns = data.get("_rpm_cooldown", {})
        until = cooldowns.get(label, 0)
        return time.time() < until


def remaining(label: str, limit: int = DEFAULT_DAILY_LIMIT) -> int:
    """오늘 남았을 것으로 추정되는 호출 수. 쿨다운 중이면 0으로 반환하여 후보에서 임시 제외."""
    if is_rpm_cooling(label):
        return 0
    with _LOCK:
        data = _load()
        rec = data.get(label)
        if not rec or rec.get("date") != _today():
            return limit
        return max(0, limit - rec["count"])


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


def set_pinned(pool_id: str, label: str) -> None:
    with _LOCK:
        data = _load()
        pins = data.setdefault("_pinned", {})
        pins[pool_id] = label
        _save(data)


def get_pinned(pool_id: str) -> "str | None":
    with _LOCK:
        data = _load()
        pinned = data.get("_pinned", {}).get(pool_id)
        if pinned and is_rpm_cooling(pinned):
            return None  # 쿨다운 중인 경우 핀 해제하여 다음 후보 시도
        return pinned
