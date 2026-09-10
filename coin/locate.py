"""**주소를 찾는다.** 손으로 적지 않고, 아무거나 받지도 않는다.

    python3 coin/locate.py --나라 US            # 죽은 것만 다시 찾는다
    python3 coin/locate.py --나라 US --전부      # 되는 것도 다시 찾아 본다
    python3 coin/locate.py --보기               # 찾아 둔 주소

## 왜

손으로 적은 주소 104개 중 열여덟이 404 였고, 고쳐서 다시 재니 또 몇이 죽었다.
**주소는 썩는다.** 그 쪽이 개편하면 또 죽고, 죽은 줄 알려면 사람이 탐침을 봐야 한다.
이 되돌이는 주소를 손으로 적는 한 안 끝난다.

## 그런데 아무 주소나 받을 수는 없다

검색이 물어온 것을 그대로 쓰면 **아무 데서 온 글이 사건 원장에 들어가고**, 그러면
D0 를 정하는 시각을 아무도 검사 안 한 곳이 정하게 된다. 그래서 세 자물쇠를 건다.

    1. 집 필터   `sec.gov` 가 아니면 SEC 출처가 아니다. 도메인은 **선언**이다
    2. 두드려 본다  그 주소가 실제로 **글과 날짜**를 내야 한다. 안 내면 안 쓴다
    3. 적어 둔다  고른 주소가 `corpus/주소.json` 에 남는다 -- 되짚을 수 있다

즉 **집은 선언이고 경로는 발견**이다. 도메인은 경로와 달리 잘 안 바뀌므로 손으로
적을 값어치가 있고, 경로는 자주 바뀌므로 손으로 적을 값어치가 없다.

## 무엇으로 찾나

`source.찾을말()` 이 이미 적힌 것(집 · 층 · 설명)에서 짓는다. 백 곳에 검색어를 또
손으로 적지 않는다 -- 그것도 썩는다.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin import source as SRC                                        # noqa: E402

길 = Path(__file__).resolve().parent / "corpus/주소.json"

try:
    from dig import search as DIGS
except Exception:                                                     # noqa: BLE001
    DIGS = None


def 찾아둔것() -> dict:
    return json.loads(길.read_text(encoding="utf-8")).get("주소", {}) if 길.exists() else {}


def 적기(이름: str, url: str, 왜: str = "", 건수: int = 0) -> Path:
    본 = 찾아둔것()
    본[이름] = {"url": url, "건수": 건수, "왜": 왜,
                "때": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    길.parent.mkdir(parents=True, exist_ok=True)
    길.write_text(json.dumps({"주소": 본}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 길


def 지금주소(s) -> str:
    """찾아 둔 것이 있으면 그것, 없으면 선언된 것."""
    본 = 찾아둔것().get(s.이름)
    return (본 or {}).get("url") or s.url


def 재보기(s, url: str) -> int:
    """그 주소가 **실제로 글을 내는가.** 안 내면 0. 이것이 둘째 자물쇠다."""
    from coin import news as NW
    try:
        raw, 최종 = NW._캐기(url, timeout=15.0, 곁문수=2)
    except Exception:                                                 # noqa: BLE001
        return 0
    글 = (NW._rss(raw, s) if s.꼴 in ("rss", "") else []) or NW._html(raw, s, 최종)
    return len(글)


def 후보(s, 몇: int = 25) -> list:
    """검색에서 **그 집의 주소만** 거둔다. 이것이 첫째 자물쇠다."""
    if DIGS is None:
        return []
    집 = SRC.집이름(s)
    뿌리 = DIGS._집(집) if callable(getattr(DIGS, "_집", None)) else 집
    try:
        _, _, 거둔것 = DIGS.찾기(SRC.찾을말(s), 몇=몇)
    except Exception:                                                 # noqa: BLE001
        return []
    out, 본 = [], set()
    for x in 거둔것:
        u = x.get("url") if isinstance(x, dict) else str(x)
        if not u or u in 본:
            continue
        그집 = SRC.집뽑기(u)
        같나 = (DIGS._집(그집) == 뿌리) if callable(getattr(DIGS, "_집", None)) else (그집 == 집)
        if not 같나:
            continue                       # **다른 집이면 이 출처가 아니다**
        본.add(u)
        out.append(u)
    return out


def 찾기(s, 몇: int = 25) -> dict:
    """(1) 지금 주소가 되면 그대로 (2) 안 되면 그 집에서 찾아 두드려 본다."""
    지금 = 지금주소(s)
    n = 재보기(s, 지금)
    if n:
        return {"이름": s.이름, "url": 지금, "건수": n, "바뀜": False, "왜": ""}
    for u in 후보(s, 몇):
        if u == 지금:
            continue
        n2 = 재보기(s, u)
        if n2:
            적기(s.이름, u, "찾아서 바꿨다", n2)
            return {"이름": s.이름, "url": u, "건수": n2, "바뀜": True, "왜": "찾아서 바꿨다"}
    return {"이름": s.이름, "url": 지금, "건수": 0, "바뀜": False,
            "왜": "그 집에서 글을 내는 주소를 못 찾았다"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--나라", default=None)
    ap.add_argument("--전부", action="store_true", help="되는 것도 다시 찾아 본다")
    ap.add_argument("--몇", type=int, default=25)
    ap.add_argument("--보기", action="store_true")
    a = ap.parse_args(argv)

    if a.보기:
        본 = 찾아둔것()
        if not 본:
            print("찾아 둔 것이 없다 -- python3 coin/locate.py --나라 US", file=sys.stderr)
            return 3
        for k, v in sorted(본.items()):
            print(f"  {k:<16} {v['건수']:>4}건  {v['url'][:70]}")
        print(f"\n{len(본)}곳")
        return 0

    if DIGS is None:
        print("dig/search 가 없다", file=sys.stderr)
        return 3

    쪽들 = SRC.쓸수있는것(나라=a.나라)
    if not a.전부:
        본 = SRC.탐침본것()
        쪽들 = [s for s in 쪽들 if 본.get(s.이름, {}).get("산것", 0) == 0]
        if not 쪽들:
            print("탐침 기록이 없거나 죽은 것이 없다. --전부 로 다 찾아볼 수 있다")
            return 0
    print(f"{len(쪽들)}곳을 찾는다 (집이 안 맞는 주소는 버린다)\n", flush=True)
    바뀐것, 산것 = 0, 0
    for i, s in enumerate(쪽들, 1):
        r = 찾기(s, a.몇)
        산것 += 1 if r["건수"] else 0
        바뀐것 += 1 if r["바뀜"] else 0
        표 = "바꿈" if r["바뀜"] else ("OK  " if r["건수"] else "못함")
        print(f"  [{i:>3}/{len(쪽들)}] {표} {s.이름:<16} {r['건수']:>4}건  "
              f"{r['url'][:60]}  {r['왜']}", flush=True)
    print(f"\n{산것}/{len(쪽들)} 이 글을 낸다 · **주소를 바꾼 것 {바뀐것}곳** -> {길}")
    print("바꾼 주소는 news.py 가 다음부터 쓴다. 집이 다르면 애초에 후보가 안 된다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
