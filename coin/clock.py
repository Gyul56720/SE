"""**시간대를 한 군데서 정한다.** 코드가 보정하지 프롬프트가 보정하지 않는다.

    python3 coin/clock.py --보기
    COIN_TZ=-5 python3 coin/clock.py --보기      뉴욕 기준으로

## 두 가지가 있고 섞으면 안 된다

    절대 시각   "언제 일어났나". 시간대와 무관하다. **비교는 늘 여기서 한다**
    날 이름     "며칠의 일인가". **시간대가 정한다**

뉴스가 05-21 20:00 UTC 에 났다면 그것은 한국에서 **05-22** 의 일이고 뉴욕에서는
05-21 의 일이다. 같은 사건인데 날 이름이 다르다. 하루의 3분의 1이 이렇게 갈린다.

## 시세도 마찬가지다 -- 그리고 여기가 더 어렵다

거래소 일봉은 **UTC 자정으로 잘려 있다.** `2021-05-21` 봉은
[05-21 00:00 UTC, 05-22 00:00 UTC) 이다. 한국 기준 하루는
[05-20 15:00 UTC, 05-21 15:00 UTC) 이라 **겹치지 않는다.**

일봉을 아무리 만져도 한국 하루가 안 나온다. 그래서 시간대를 걸면
`price.받기` 가 **시간봉을 받아 그 시간대의 하루로 다시 묶는다.**

    UTC 하루로 재면    "D+7" 이 한국 사람이 생각하는 이레와 아홉 시간 어긋난다
    다시 묶으면        어긋나지 않는다. 대신 받는 양이 24배다

받는 양이 커서 기본은 UTC(0)로 둔다. `COIN_TZ` 를 걸면 그때 다시 묶는다.
**그 값이 원장에 적힌다** -- 바꿔 재면 다른 수가 나오므로.

## 어디가 UTC 로 남아야 하나

    진입일 규칙   뉴스 시각과 봉 마감 시각을 견주는 것이라 **절대 시각끼리**다.
                  시간대를 넣으면 양쪽에 같은 값을 더하는 셈이라 답이 안 바뀐다
    널 · 수익률   봉 위에서 세므로 봉이 어떤 하루인지만 맞으면 된다

즉 **시간대는 '하루를 어디서 자르나' 에만 든다.** 그 한 자리를 여기서 정한다.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

기본 = 0.0


def 시간대(값=None) -> float:
    """시간(hour) 단위 오프셋. 안 주면 `COIN_TZ`, 그것도 없으면 UTC.

    한국 +9 · 뉴욕 -5(겨울)/-4(여름) · UTC 0. **여름시간을 안 따라간다** --
    따라가면 같은 원장 안에서 하루의 길이가 달라져 D+n 이 어긋난다.
    """
    if 값 is not None:
        return float(값)
    v = os.environ.get("COIN_TZ", "").strip()
    try:
        return float(v) if v else 기본
    except ValueError:
        return 기본


def 옮김(t: datetime, tz=None) -> datetime:
    return t + timedelta(hours=시간대(tz))


def 날짜(iso: str, tz=None) -> str:
    """절대 시각 -> **그 시간대에서의 날 이름.**"""
    from coin.price import _때
    t = _때(iso)
    return 옮김(t, tz).strftime("%Y-%m-%d") if t else ""


def 하루경계(날: str, tz=None) -> tuple:
    """그 시간대의 하루가 **절대 시각으로** 언제부터 언제까지인가."""
    h = 시간대(tz)
    첫 = (datetime.strptime(날, "%Y-%m-%d").replace(tzinfo=timezone.utc)
          - timedelta(hours=h))
    return 첫, 첫 + timedelta(days=1)


def 묶기(시간봉: list, tz=None) -> list:
    """시간봉 -> 그 시간대의 일봉. `[[ms, o, h, l, c, v], ...]` 를 받는다.

    **이것이 시세 시간보정의 전부다.** UTC 일봉을 만질 게 아니라 시간봉을 다시 묶는다.
    """
    h = 시간대(tz)
    통 = {}
    for k in 시간봉:
        t = datetime.fromtimestamp(float(k[0]) / 1000, timezone.utc) + timedelta(hours=h)
        날 = t.strftime("%Y-%m-%d")
        o, hi, lo, c, v = (float(k[1]), float(k[2]), float(k[3]),
                           float(k[4]), float(k[5]))
        r = 통.get(날)
        if r is None:
            통[날] = [날, o, hi, lo, c, v]
        else:
            r[2] = max(r[2], hi)
            r[3] = min(r[3], lo)
            r[4] = c                      # 마지막 시간봉의 종가가 그 하루의 종가
            r[5] += v
    return [통[d] for d in sorted(통)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--보기", action="store_true")
    ap.add_argument("--시각", default="")
    a = ap.parse_args(argv)
    h = 시간대()
    이름 = {9: "한국", -5: "뉴욕(겨울)", -4: "뉴욕(여름)", 0: "UTC", 8: "중국·홍콩"}
    print(f"  지금 시간대: UTC{h:+g}  ({이름.get(int(h), '?')})")
    print(f"  COIN_TZ 로 바꾼다. 예: COIN_TZ=9 (한국) · COIN_TZ=-5 (뉴욕)")
    보기 = a.시각 or "2021-05-21T20:00:00+00:00"
    print(f"\n  {보기}")
    for x, 나 in ((0, "UTC"), (9, "한국"), (-5, "뉴욕")):
        print(f"    {나:<5} {날짜(보기, x)}")
    print("\n  **하루의 3분의 1이 이렇게 갈린다.** 그래서 원장에 시간대를 같이 적는다")
    첫, 끝 = 하루경계("2021-05-21", 9)
    print(f"\n  한국 2021-05-21 = [{첫.strftime('%m-%d %H:%M')} ~ "
          f"{끝.strftime('%m-%d %H:%M')}] UTC")
    print("  거래소 일봉은 UTC 자정으로 잘려 있어 이 창과 안 겹친다")
    print("  -> 시간대를 걸면 price.받기 가 **시간봉을 받아 다시 묶는다**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
