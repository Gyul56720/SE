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


def _transpose(d: dict) -> list:
    """칸 지향 -> 줄 지향. `{"time":[a,b], "tmax":[1,2]}` -> 두 줄.

    **실측 2026-09-09:** 이것이 없어서 Open-Meteo 가 `한 줄도 안 왔다` 로 떨어졌다.
    공개 API 의 절반쯤이 이 꼴로 준다 -- 줄 지향만 읽으면 그 절반을 통째로 못 쓴다.

    길이가 다른 칸이 섞여 있으면 **안 한다.** 짧은 쪽에 맞춰 자르면 남는 줄이 조용히
    사라지고, 긴 쪽에 맞춰 채우면 없는 값이 생긴다 -- 둘 다 원장을 거짓말로 만든다.
    """
    # **칸은 스칼라의 목록이다.** dict 나 list 가 든 목록은 칸이 아니라 **줄 목록**이다.
    #
    # 실측 2026-09-09 (이 검사가 잡았다): `{"data": {"items": [{...},{...}]}}` 에서
    # `items` 를 칸으로 보고 전치했더니, 줄 세 개가 각각 `{"items": {...}}` 하나짜리로
    # 나왔다 -- 칸이 통째로 사라지고 `살펴보기` 가 수인 칸을 하나도 못 찾았다.
    # 걸러 내면 그 dict 에는 칸이 없는 것이 되고, 아래 `find_rows` 가 목록으로
    # 내려가 제대로 읽는다.
    lists = {k: v for k, v in d.items()
             if isinstance(v, list) and not any(isinstance(x, (dict, list)) for x in v)}
    if not lists:
        return []
    n = len(next(iter(lists.values())))
    if n == 0 or any(len(v) != n for v in lists.values()):
        return []
    return [{k: v[i] for k, v in lists.items()} for i in range(n)]


def find_rows(data, _깊이: int = 0) -> tuple:
    """아무 JSON 에서나 **줄이 있을 만한 자리**를 찾는다. (줄, 어디서 찾았나).

    출처를 미리 등록해 두는 것 자체가 하드코딩이다 -- 내가 예상한 API 만 되기 때문이다.
    티켓값이든 무엇이든 요청 시점에 붙이려면, 받은 것에서 줄을 **스스로 찾아야** 한다.

    찾는 것은 셋뿐이고 셋 다 꼴로만 판정한다 -- 뜻을 짐작하지 않는다:

        dict 의 목록          그대로 줄이다
        길이가 같은 list 의 dict   칸 지향이다 -> 전치
        그 밖의 dict          값마다 내려가 보고 **제일 많은 줄**을 집는다

    못 찾으면 빈 목록이다. 억지로 하나를 만들어 내지 않는다.
    """
    if _깊이 > 6:
        return [], ""
    if isinstance(data, list):
        rows = [r for r in data if isinstance(r, dict)]
        return (rows, "") if rows else ([], "")
    if not isinstance(data, dict):
        return [], ""
    flat = _transpose(data)
    if flat:
        return flat, ""
    best, where = [], ""
    for k, v in data.items():
        rows, sub = find_rows(v, _깊이 + 1)
        if len(rows) > len(best):
            best, where = rows, (f"{k}.{sub}" if sub else k)
    return best, where


def parse(src, text: str) -> list:
    """받은 몸통 -> 줄 목록. **꼴이 다르면 빈 목록이다.**

    `경로` 가 적혀 있으면 그리로만 간다(적어 준 사람을 믿는다). 비어 있으면
    `find_rows` 가 찾는다 -- 그래야 처음 보는 출처를 요청 시점에 붙일 수 있다.
    """
    if src.꼴 == "json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
        if src.경로:
            for step in src.경로.split("."):
                if isinstance(data, dict):
                    data = data.get(step)
                else:
                    return []
            rows, _ = find_rows(data)
            return rows
        rows, _ = find_rows(data)
        return rows
    try:
        return [dict(r) for r in csv.DictReader(io.StringIO(text))]
    except csv.Error:
        return []


def 살펴보기(rows: list) -> dict:
    """도착한 것에서 **칸이 무엇인지 스스로 읽는다.** 저장은 안 한다.

    이것이 '요청 시점에 붙이기' 의 열쇠다. 스키마를 미리 알아야 쓸 수 있으면 미리
    등록해 둔 출처만 되는데, 그러면 표를 손으로 늘리는 것과 같아진다.

    돌려주는 것: 모든 칸 · 수인 칸 · 줄을 가리킬 수 있는 칸(값이 안 겹치는 것).
    **판정이 아니라 눈금이다** -- 무엇을 쓸지는 부르는 쪽이 정한다.
    """
    if not rows:
        return {"칸": [], "수칸": [], "key후보": [], "줄수": 0}
    cols, seen = [], set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                cols.append(k)
    수칸 = [c for c in cols
            if sum(1 for r in rows if _num(r.get(c)) is not None) >= len(rows) * 0.8]
    # 줄을 가리킬 칸: 값이 다 있고 안 겹치는 것. 수는 뒤로 민다 -- id 로 쓰면
    # `1` 같은 이름이 되어 되짚을 때 사람이 못 알아본다.
    key후보 = [c for c in cols
               if len({str(r.get(c)) for r in rows}) == len(rows)
               and all(str(r.get(c) or "").strip() for r in rows)]
    key후보.sort(key=lambda c: (c in 수칸, cols.index(c)))
    return {"칸": cols, "수칸": 수칸, "key후보": key후보, "줄수": len(rows)}


def inspect(src, rows: list) -> dict:
    """저장해도 되는가. **판정과 이유를 같이 돌려준다.**"""
    if not rows:
        return {"통과": False, "왜": ["한 줄도 안 왔다"], "good": [], "받은것": 0, "버린것": 0}
    왜, good = [], []
    # **적혀 있으면 강제하고, 안 적혀 있으면 도착한 것에서 읽는다.**
    #
    # 등록된 출처는 칸을 적어 두므로 스키마가 바뀌면 걸린다(그것이 B002 를 받치는
    # 자리다). 처음 보는 출처는 적어 둘 것이 없다 -- 그때까지 못 쓰게 하면 결국
    # 내가 미리 등록해 둔 것만 되고, 그게 하드코딩이다.
    본 = 살펴보기(rows)
    칸 = tuple(src.칸) or tuple(본["칸"])
    수칸 = tuple(src.수칸) or tuple(본["수칸"])
    key = src.key or (본["key후보"][0] if 본["key후보"] else "")

    missing = [c for c in 칸 if c not in rows[0]]
    if missing:
        왜.append(f"칸이 빠졌다: {', '.join(missing)} -- 스키마가 바뀐 모습이다")
        return {"통과": False, "왜": 왜, "good": [], "받은것": len(rows),
                "버린것": len(rows), "샘플": rows[:2], "본것": 본}
    if not 수칸:
        왜.append("수인 칸이 하나도 없다 -- 셀 것이 없으면 보고서가 아니라 그냥 옮겨 적기다")
    for i, r in enumerate(rows, 1):
        nums = {c: _num(r.get(c)) for c in 수칸}
        if any(v is None for v in nums.values()):
            continue
        # key 를 못 정했으면 **자리 번호로 가리킨다.** 없는 이름을 지어내지 않고,
        # 그래도 B002 가 되짚을 자리는 있어야 한다.
        rid = str(r.get(key) or "").strip() if key else f"행{i}"
        if not rid:
            continue
        good.append({"id": rid, **{c: str(r.get(c) or "").strip() for c in 칸
                                   if c not in 수칸}, **nums})
    # 같은 id 가 둘이면 되짚기가 갈린다 -- B002 가 어느 줄을 가리키는지 모르게 된다.
    if len({g["id"] for g in good}) != len(good):
        왜.append(f"id({key or '자리번호'})가 겹친다 -- 되짚을 수 없는 원장이다")
        return {"통과": False, "왜": 왜, "good": [], "받은것": len(rows),
                "버린것": len(rows), "샘플": rows[:2], "본것": 본}
    share = len(good) / len(rows)
    if share < OK_SHARE:
        왜.append(f"쓸 수 있는 줄이 {len(good)}/{len(rows)} 뿐이다 "
                  f"-- 줄 문제가 아니라 스키마 문제로 본다")
    return {"통과": bool(good) and share >= OK_SHARE and bool(수칸), "왜": 왜,
            "good": good, "받은것": len(rows), "버린것": len(rows) - len(good),
            "샘플": rows[:2], "본것": 본, "쓴것": {"칸": 칸, "수칸": 수칸, "key": key}}


def get(url: str, timeout: float = 30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:   # noqa: S310
        return r.read().decode("utf-8", errors="replace")


def fetch(src, **params) -> tuple:
    """(원장, 오류). **오류가 있으면 원장은 비어 있다** -- 반쯤 채우지 않는다."""
    ok, why = src.쓸수있나()
    if not ok:
        return Ledger(출처=src.이름, 왜=[why]), why
    # 즉석 출처의 url 은 이미 완성돼 있고, 질의 안에 `{` 가 들어 있을 수도 있다
    # (JSON 을 실어 보내는 API). format 이 거기서 터지면 받아 보지도 못하고 죽으므로,
    # 채울 자리가 없으면 그대로 쓴다.
    try:
        url = src.url.format(**params) if "{" in src.url else src.url
    except (KeyError, IndexError, ValueError):
        url = src.url
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
