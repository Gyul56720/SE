"""**받아서 원장에 넣는다. 받은 것을 그대로 믿지 않는다.**

`law/fetch.py` 와 `lol/fetch.py` 가 각자 하던 일을 한 벌로 모았다. 다른 것은 무엇을
검사할지가 **코드가 아니라 `Source` 에 적혀 있다**는 것뿐이다.

    빈 응답        -> 안 받는다
    칸이 빠졌다    -> 안 받는다 (스키마가 바뀐 모습이다)
    수칸이 수가 아니다 -> 그 줄만 버린다. 대부분이 그러면 통째로 안 받는다
    통과           -> **머리글 한 줄**(받은날·출처·질의)과 함께 저장한다

머리글이 요점이다. **언제 것인지 모르는 원장은 못 쓴다** -- 낡은 값으로 낸 보고서는
틀린 보고서인데, 화면에서는 맞는 것과 똑같이 생겼다.
"""
from __future__ import annotations

import csv
import io
import json
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER_DIR = HERE / "ledger"
UA = "SE-brief/1.0 (https://github.com/gyul56720/se)"

# 이만큼은 성해야 저장한다. 이보다 나쁘면 줄 문제가 아니라 스키마 문제다.
OK_SHARE = 0.8


@dataclass
class Ledger:
    출처: str = ""
    받은날: str = ""
    질의: str = ""
    줄: list = field(default_factory=list)       # [{id, 칸...}]
    버린것: int = 0
    왜: list = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.줄)

    def 찾기(self, rid: str) -> dict | None:
        for r in self.줄:
            if r.get("id") == rid:
                return r
        return None

    def 나이(self) -> int | None:
        """받은 날로부터 며칠. 못 읽으면 None -- **모르는 것은 모른다고 한다.**"""
        try:
            d = datetime.strptime(self.받은날, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
        return (date.today() - d).days


def _num(v):
    """수로 읽는다. 못 읽으면 None -- 0 으로 채우지 않는다.

    0 으로 채우면 그 줄이 '거래가 없었다' 로 읽히고, 평균과 등락률이 조용히 기운다.
    `law/wording.py` 가 견줄 것이 없으면 판정 안 하는 것과 같다."""
    if v is None:
        return None
    t = str(v).strip().replace(",", "").replace("%", "")
    if t in ("", "N/A", "-", "null", "None"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def parse(src, text: str) -> list:
    """받은 몸통 -> 줄 목록. **꼴이 다르면 빈 목록이다.**"""
    if src.꼴 == "json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
        for step in (src.경로.split(".") if src.경로 else []):
            if isinstance(data, dict):
                data = data.get(step)
            else:
                return []
        rows = data if isinstance(data, list) else []
        return [r for r in rows if isinstance(r, dict)]
    try:
        return [dict(r) for r in csv.DictReader(io.StringIO(text))]
    except csv.Error:
        return []


def inspect(src, rows: list) -> dict:
    """저장해도 되는가. **판정과 이유를 같이 돌려준다.**"""
    if not rows:
        return {"통과": False, "왜": ["한 줄도 안 왔다"], "good": [], "받은것": 0, "버린것": 0}
    왜, good = [], []
    missing = [c for c in src.칸 if c not in rows[0]]
    if missing:
        왜.append(f"칸이 빠졌다: {', '.join(missing)} -- 스키마가 바뀐 모습이다")
        return {"통과": False, "왜": 왜, "good": [], "받은것": len(rows),
                "버린것": len(rows), "샘플": rows[:2]}
    for r in rows:
        nums = {c: _num(r.get(c)) for c in src.수칸}
        if any(v is None for v in nums.values()):
            continue
        rid = str(r.get(src.key) or "").strip()
        if not rid:
            continue
        good.append({"id": rid, **{c: str(r.get(c) or "").strip() for c in src.칸
                                   if c not in src.수칸}, **nums})
    share = len(good) / len(rows)
    if share < OK_SHARE:
        왜.append(f"쓸 수 있는 줄이 {len(good)}/{len(rows)} 뿐이다 "
                  f"-- 줄 문제가 아니라 스키마 문제로 본다")
    return {"통과": bool(good) and share >= OK_SHARE, "왜": 왜, "good": good,
            "받은것": len(rows), "버린것": len(rows) - len(good), "샘플": rows[:2]}


def get(url: str, timeout: float = 30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:   # noqa: S310
        return r.read().decode("utf-8", errors="replace")


def fetch(src, **params) -> tuple:
    """(원장, 오류). **오류가 있으면 원장은 비어 있다** -- 반쯤 채우지 않는다."""
    ok, why = src.쓸수있나()
    if not ok:
        return Ledger(출처=src.이름, 왜=[why]), why
    url = src.url.format(**params)
    try:
        body = get(url)
    except Exception as e:                                    # noqa: BLE001
        return Ledger(출처=src.이름, 왜=[f"{type(e).__name__}: {str(e)[:120]}"]), \
            f"못 받았다: {type(e).__name__}: {str(e)[:120]}"
    v = inspect(src, parse(src, body))
    if not v["통과"]:
        return Ledger(출처=src.이름, 왜=v["왜"]), "; ".join(v["왜"]) or "검사 실패"
    return Ledger(출처=src.이름, 받은날=date.today().isoformat(), 질의=url,
                  줄=v["good"], 버린것=v["버린것"]), ""


def save(led: Ledger, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(led), ensure_ascii=False, indent=1),
                    encoding="utf-8")
    return path


def load(path: Path) -> Ledger | None:
    """**머리글(받은날·출처)이 없으면 안 읽는다.**"""
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(d, dict) or not d.get("출처") or not d.get("받은날"):
        return None
    return Ledger(출처=d["출처"], 받은날=d["받은날"], 질의=d.get("질의", ""),
                  줄=[r for r in d.get("줄", []) if isinstance(r, dict) and r.get("id")],
                  버린것=int(d.get("버린것") or 0), 왜=list(d.get("왜") or ()))
