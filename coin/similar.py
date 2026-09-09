"""**지금과 가장 닮은 과거를 찾는다.** 이 파이프라인의 새 중심.

    python3 coin/similar.py --자산 BTC              지금과 닮은 날 다섯
    python3 coin/similar.py --자산 BTC --날 2021-05-19   그날과 닮은 날
    python3 coin/similar.py --자산 BTC --창 1,3,7   창을 바꿔도 같은 날이 나오나

## 무엇을 하나

    상황  ->  숫자 벡터  ->  과거의 모든 날과 견줌  ->  제일 닮은 몇 날
                                                        -> 그날 뒤에 무엇이 있었나

"~를 바탕으로 미루어 보면 ~할 것 같다" 의 **앞부분이 여기서 나온다.** 뒷부분은
그 닮은 날들 뒤에 실제로 있었던 일이고, 그것은 가격 원장이 안다.

## 벡터를 어떻게 세우나 -- 세 덩이

    뉴스   (유형 x 나라) 별 건수. 최근 `창일` 안의 것만        <- 성긴 셈
    가격   추세 · 변동 · 낙폭. **자기 역사의 백분위**          <- [0,1]
    흐름   자금조달률 · 미결제 · 공포탐욕. 백분위              <- [0,1]

**섞어서 하나로 만들지 않는다.** 셋의 닮음을 따로 내고 그다음에 합친다. 안 그러면
어느 덩이가 그 답을 끌고 왔는지 아무도 못 말한다 -- 뉴스가 닮아서 뽑힌 날과 시장이
닮아서 뽑힌 날은 **전혀 다른 뜻**이다. 화면에 셋이 다 나온다.

합치는 가중치는 눈에 보이는 인자다(`--무게 뉴스,가격,흐름`). 숨기면 그 수가 순위를
전부 정하면서 아무도 그것을 모른다.

## 날짜 보정 -- 이것이 조용히 틀리는 자리다

기사 시각은 UTC 로 저장한다. 그런데 **어느 날의 뉴스인가**는 시간대가 정한다.

    2021-05-21 08:00 UTC = 한국 17:00  -> 같은 날
    2021-05-21 20:00 UTC = 한국 05:00 **다음 날**

한국 기준으로 보면 하루가 밀리는 기사가 하루의 3분의 1 이다. 그래서 `시간대` 를
인자로 두고(기본 +9, 한국) **잰 값에 같이 적는다** -- 바꿔 재면 다른 답이 나오는
손잡이는 안 적으면 재현이 안 된다.

## 며칠을 '지금' 으로 보나

`창일` 이다(기본 3). 정답이 없으므로 **바꿔 보고 답이 흔들리는지 본다** --
`--창 1,3,7` 이 세 창으로 각각 뽑아 준다. 창을 바꿨는데 닮은 날이 통째로 바뀌면
그 닮음은 창이 만든 것이지 상황이 만든 것이 아니다.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin.price import _때                                            # noqa: E402

지평기본 = (1, 3, 7, 14, 30)


def 날짜(iso: str, 시간대=None) -> str:
    """UTC 시각 -> 그 시간대에서의 날짜. **셈은 `coin/clock.py` 한 군데에 있다.**"""
    from coin import clock as CK
    return CK.날짜(iso, 시간대)


def 뉴스벡터(사건들: list, 끝날: str, 창일: int = 3, 시간대: int = 9,
            자산: str = "") -> dict:
    """(유형|나라) -> 건수. 끝날에서 뒤로 `창일` 안의 것만."""
    from datetime import datetime, timezone
    끝 = datetime.strptime(끝날, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    첫 = 끝 - timedelta(days=창일 - 1)
    v = {}
    for e in 사건들:
        if 자산 and e.get("자산") != 자산:
            continue
        d = 날짜(e.get("최초") or "", 시간대)
        if not d or not (첫.strftime("%Y-%m-%d") <= d <= 끝날):
            continue
        for 나라 in (e.get("나라들") or ["XX"]):
            k = f"{e.get('유형')}|{나라}"
            v[k] = v.get(k, 0) + 1
    return v


def 시장벡터(계열, 끝날: str, 원봉: list = None, 눈금: str = "1d") -> dict:
    """가격 쪽 백분위. **그 날까지의 자료로만** 잰다 -- 미리보기를 막는다.

    셋(추세·변동·낙폭)에 **차트 지표**(`chart.py`)를 더한다. 전부 백분위라 그냥
    붙여도 자가 안 어긋난다. 차트를 예측기로 안 쓰고 **상황 서술자로** 쓰는 자리다.
    """
    from coin import chart as CH
    from coin import price as PR
    from coin import regime as RG
    봉 = [[d, 0, 0, 0, 계열.종가[d], 0] for d in 계열.날들 if d <= 끝날]
    if len(봉) < 200:
        return {}
    잘린 = PR.계열({"자산": 계열.자산, "봉": 봉})
    t, v, dd = RG.추세(잘린), RG.변동(잘린), RG.낙폭(잘린)
    out = {}
    for 이름, x in (("추세", t), ("변동", v), ("낙폭", dd)):
        p = x.get("백분위")
        if isinstance(p, float) and p == p:
            out[이름] = p
    # 고저·거래량이 있는 원봉이 있으면 차트 지표까지. 없으면 종가만으로 되는 것만
    쓸봉 = [r for r in (원봉 or 봉) if r[0] <= 끝날]
    out.update(CH.재기(쓸봉, 눈금))
    return out


def 흐름벡터(흐름원장: dict, 끝날: str) -> dict:
    """흐름 쪽 백분위. 그 날까지의 값으로만."""
    from coin.regime import _백분위
    계 = (흐름원장 or {}).get("계열") or {}
    out = {}
    for 이름, 값들 in 계.items():
        날 = sorted(d for d in 값들 if d <= 끝날)
        if len(날) < 20:
            continue
        out[이름] = _백분위(값들[날[-1]], [값들[d] for d in 날])
    return out


def 벡터(계열, 사건들: list, 흐름원장: dict, 끝날: str, 창일: int = 3,
        시간대=None, 자산: str = "", 원봉: list = None) -> dict:
    return {"날": 끝날, "창일": 창일, "시간대": 시간대,
            "뉴스": 뉴스벡터(사건들, 끝날, 창일, 시간대, 자산),
            "시장": 시장벡터(계열, 끝날, 원봉),
            "흐름": 흐름벡터(흐름원장, 끝날)}


# ------------------------------------------------------------------ 닮음
def _코사인(a: dict, b: dict) -> float:
    """성긴 셈 벡터끼리. 둘 다 비면 **0 이지 1 이 아니다** -- 아무 일도 없던 날끼리
    '완벽히 닮았다' 고 하면 뉴스가 없는 날이 죄다 서로 최고점이 된다."""
    if not a or not b:
        return 0.0
    안 = sum(a.get(k, 0) * b.get(k, 0) for k in set(a) | set(b))
    na = math.sqrt(sum(x * x for x in a.values()))
    nb = math.sqrt(sum(x * x for x in b.values()))
    return (안 / (na * nb)) if na and nb else 0.0


def _가까움(a: dict, b: dict) -> float:
    """백분위끼리. 1 - 평균 절대차. 겹치는 칸이 없으면 못 잰다(nan)."""
    칸 = set(a) & set(b)
    if not 칸:
        return float("nan")
    return 1.0 - sum(abs(a[k] - b[k]) for k in 칸) / len(칸)


def 닮음(v1: dict, v2: dict, 무게=(0.5, 0.3, 0.2)) -> dict:
    """**셋을 따로 내고 그다음에 합친다.** 어느 덩이가 끌고 왔는지 보이게."""
    뉴 = _코사인(v1.get("뉴스") or {}, v2.get("뉴스") or {})
    시 = _가까움(v1.get("시장") or {}, v2.get("시장") or {})
    흐 = _가까움(v1.get("흐름") or {}, v2.get("흐름") or {})
    쌍 = [(뉴, 무게[0]), (시, 무게[1]), (흐, 무게[2])]
    쓸것 = [(x, w) for x, w in 쌍 if x == x]
    합 = sum(x * w for x, w in 쓸것) / sum(w for _, w in 쓸것) if 쓸것 else float("nan")
    return {"뉴스": 뉴, "시장": 시, "흐름": 흐, "합": 합}


def 찾기(계열, 사건들: list, 흐름원장: dict, 오늘: str = "", 창일: int = 3,
        시간대: int = 9, 자산: str = "", 몇: int = 5, 걸음: int = 1,
        무게=(0.5, 0.3, 0.2), 떨어뜨림: int = 30) -> dict:
    """지금과 닮은 과거 날들. **가까운 날은 뺀다**(`떨어뜨림`) -- 어제와 오늘이
    닮은 것은 당연하고, 그것을 답이라고 내놓으면 아무 말도 안 한 것이다."""
    오늘 = 오늘 or (계열.날들[-1] if len(계열) else "")
    if not 오늘:
        return {"왜": "가격 원장이 비었다", "닮은날": []}
    지금 = 벡터(계열, 사건들, 흐름원장, 오늘, 창일, 시간대, 자산)
    from datetime import datetime, timezone
    기준 = datetime.strptime(오늘, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    본 = []
    for d in 계열.날들[::걸음]:
        if d >= 오늘:
            continue
        t = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if (기준 - t).days < 떨어뜨림:
            continue
        v = 벡터(계열, 사건들, 흐름원장, d, 창일, 시간대, 자산)
        s = 닮음(지금, v, 무게)
        if s["합"] != s["합"]:
            continue
        본.append({"날": d, "닮음": s,
                   "뒤": {h: 계열.수익(d, h) for h in 지평기본},
                   "뉴스수": sum((v.get("뉴스") or {}).values())})
    본.sort(key=lambda x: -x["닮음"]["합"])
    return {"오늘": 오늘, "지금": 지금, "닮은날": 본[:몇], "본것": len(본),
            "무게": list(무게), "창일": 창일, "시간대": 시간대, "왜": ""}


def 줄(x: dict) -> str:
    s, 뒤 = x["닮음"], x["뒤"]
    수 = " · ".join(f"D+{h} {v*100:+.1f}%" for h, v in 뒤.items() if v is not None)
    return (f"  {x['날']}  닮음 {s['합']:.3f} "
            f"(뉴스 {s['뉴스']:.2f} · 시장 {s['시장']:.2f} · 흐름 {s['흐름']:.2f}) "
            f"· 뉴스 {x['뉴스수']}건\n      그 뒤: {수 or '못 셌다'}")


def 적기(r: dict) -> str:
    if r.get("왜"):
        return f"  {r['왜']}"
    지 = r["지금"]
    줄들 = [f"오늘 {r['오늘']} (창 {r['창일']}일 · 시간대 UTC{r['시간대']:+d} · "
            f"무게 뉴스{r['무게'][0]}/시장{r['무게'][1]}/흐름{r['무게'][2]})",
            f"  지금 상황: 뉴스 {sum((지.get('뉴스') or {}).values())}건 "
            + " · ".join(f"{k} {v*100:.0f}%자리" for k, v in (지.get("시장") or {}).items()),
            f"  견준 날 {r['본것']}일 중 닮은 것:"]
    for x in r["닮은날"]:
        줄들.append(줄(x))
    if r["닮은날"]:
        뒤들 = [x["뒤"].get(7) for x in r["닮은날"] if x["뒤"].get(7) is not None]
        if 뒤들:
            오름 = sum(1 for v in 뒤들 if v > 0)
            줄들.append(f"\n  **닮은 {len(뒤들)}날 중 {오름}날이 D+7 에 올랐다** "
                        f"(중앙 {sorted(뒤들)[len(뒤들)//2]*100:+.1f}%)")
            줄들.append("  이것은 표본 다섯이다 -- 셈이지 예언이 아니다")
    return "\n".join(줄들)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--자산", default="BTC")
    ap.add_argument("--날", default="")
    ap.add_argument("--창", default="3", help="며칠을 '지금' 으로 보나. 3 또는 1,3,7")
    ap.add_argument("--시간대", type=int, default=9, help="날짜를 어느 시간대로 (기본 한국 +9)")
    ap.add_argument("--몇", type=int, default=5)
    ap.add_argument("--걸음", type=int, default=1)
    ap.add_argument("--무게", default="0.5,0.3,0.2")
    a = ap.parse_args(argv)

    from coin import flow as FL
    from coin import price as PR
    원 = PR.불러오기(a.자산)
    if not 원:
        print(f"가격 원장이 없다: {a.자산} -- python3 coin/price.py --받기 {a.자산}",
              file=sys.stderr)
        return 3
    c = PR.계열(원)
    사건p = Path(__file__).resolve().parent / "corpus/events.json"
    사건 = json.loads(사건p.read_text(encoding="utf-8")).get("사건", []) if 사건p.exists() else []
    흐름 = FL.불러오기()
    무게 = tuple(float(x) for x in a.무게.split(","))
    창들 = [int(x) for x in a.창.split(",") if x.strip()]
    for i, 창 in enumerate(창들):
        if i:
            print()
        r = 찾기(c, 사건, 흐름, a.날, 창, a.시간대, a.자산, a.몇, a.걸음, 무게)
        print(적기(r))
    if len(창들) > 1:
        print("\n  **창을 바꿔도 같은 날이 나오나.** 통째로 바뀌면 그 닮음은 창이 만든 것이지")
        print("  상황이 만든 것이 아니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
