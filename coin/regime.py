"""**장세와 거래량 이상 -- 문턱을 안 박는다. 전부 자기 역사의 백분위다.**

    python3 coin/regime.py --자산 BTC
    python3 coin/regime.py --폭 BTC,ETH,SOL        여러 종목의 폭(breadth)

## 왜 백분위인가 -- "약세장 = -20%" 를 박으면 그것이 편향이다

문턱을 박는 순간 그 수가 어디서 왔는지 아무도 못 말한다. -20% 는 주식에서 온 관습이고
비트코인의 하루 변동이 주식의 한 달인 시장에서는 뜻이 다르다. 그래서 여기서 재는 것은
전부 **그 계열 자기 역사 안에서의 자리**다.

    추세   최근 N일 수익률이 **자기 역사의 몇 %** 자리인가
    변동   최근 N일 실현변동성이 몇 % 자리인가
    낙폭   고점 대비 낙폭이 몇 % 자리인가
    폭     종목 중 몇 개가 오르고 있나 (그리고 그 값이 자기 역사의 몇 % 자리인가)

"장이 안 좋다" 는 **추세 백분위가 아래 다섯 칸 중 첫 칸**일 때다. 다섯 칸은
`scenario.py` 가 칸을 가르는 법과 같다 -- 널 분포의 오분위. 새 상수가 아니다.

## 거래량 이상을 '고래' 라고 부르지 않는다

지갑을 못 본다. 온체인 자료가 없으면 큰 지갑이 움직였는지 알 길이 없고, **거래량을
고래라고 부르는 순간 그것은 측정이 아니라 과장이다.** 여기서 재는 것은 하나다 --
**거래량이 자기 역사에서 어느 자리이고, 그날 값이 어느 쪽으로 움직였나.**

    거래량 상위 2% 인데 값이 내렸다     <- 이렇게 적는다
    고래가 던졌다                       <- 이렇게 안 적는다

뉴스에 `고래이동` 꼬리표가 같이 걸렸으면 그 사실은 따로 적는다. 둘을 합쳐 하나의
결론으로 만들지 않는다 -- 합치는 순간 무게를 내가 정하게 되고, 그 무게가 편향이다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from statistics import pstdev

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

칸수기본 = 5


def _백분위(값: float, 모음: list) -> float:
    쓸것 = [v for v in 모음 if v is not None]
    if not 쓸것 or 값 is None:
        return float("nan")
    return sum(1 for v in 쓸것 if v <= 값) / len(쓸것)


def 추세(계열, 창: int = 60) -> dict:
    """최근 `창`일 수익률과 그 값이 자기 역사에서 어느 자리인가."""
    if len(계열) < 창 * 3:
        return {"값": float("nan"), "백분위": float("nan"), "n": 0, "창": 창}
    모음 = [계열.수익(d, 창) for d in 계열.살수있는날들(창)]
    지금 = 계열.수익(계열.날들[-1 - 창], 창)
    return {"값": 지금, "백분위": _백분위(지금, 모음), "n": len(모음), "창": 창}


def 변동(계열, 창: int = 30) -> dict:
    날 = 계열.날들
    if len(날) < 창 * 4:
        return {"값": float("nan"), "백분위": float("nan"), "창": 창}

    def 재기(i):
        토막 = [계열.수익(날[j], 1) for j in range(i - 창, i)]
        토막 = [v for v in 토막 if v is not None]
        return pstdev(토막) if len(토막) > 2 else None

    모음 = [재기(i) for i in range(창 + 1, len(날) - 1, 2)]
    지금 = 재기(len(날) - 1)
    return {"값": 지금, "백분위": _백분위(지금, 모음), "창": 창}


def 낙폭(계열, 창: int = 365) -> dict:
    날 = 계열.날들
    if len(날) < 창:
        창 = max(30, len(날) // 2)

    def 재기(i):
        고 = max(계열.종가[d] for d in 날[max(0, i - 창):i + 1])
        return 계열.종가[날[i]] / 고 - 1.0 if 고 else None

    모음 = [재기(i) for i in range(창, len(날), 2)]
    지금 = 재기(len(날) - 1)
    return {"값": 지금, "백분위": _백분위(지금, 모음), "창": 창}


def 거래량이상(원장: dict, 창: int = 365) -> dict:
    """**거래량이 자기 역사의 어느 자리인가. 고래라고 부르지 않는다.**"""
    봉 = 원장.get("봉") or []
    if len(봉) < 30:
        return {"백분위": float("nan"), "n": len(봉)}
    쓸것 = 봉[-창:] if len(봉) > 창 else 봉
    양 = [r[5] for r in 쓸것 if r[5]]
    if not 양:
        return {"백분위": float("nan"), "n": 0}
    지금 = 봉[-1][5]
    앞 = 봉[-2][4] if len(봉) > 1 else None
    움직임 = (봉[-1][4] / 앞 - 1.0) if 앞 else float("nan")
    return {"백분위": _백분위(지금, 양), "값": 지금, "그날움직임": 움직임,
            "n": len(양), "창": 창, "날": 봉[-1][0]}


def 장세(계열, 원장: dict = None, 칸수: int = 칸수기본) -> dict:
    t, v, d = 추세(계열), 변동(계열), 낙폭(계열)
    아래칸 = 1.0 / 칸수
    나쁨 = (t["백분위"] == t["백분위"]) and t["백분위"] < 아래칸
    좋음 = (t["백분위"] == t["백분위"]) and t["백분위"] > 1 - 아래칸
    return {"자산": 계열.자산, "추세": t, "변동": v, "낙폭": d,
            "거래량": 거래량이상(원장 or {}), "칸수": 칸수, "아래칸": 아래칸,
            "나쁨": 나쁨, "좋음": 좋음,
            "말": ("아래 " if 나쁨 else "위 " if 좋음 else "가운데 ")
                  + f"{칸수}칸 중 {'첫' if 나쁨 else '끝' if 좋음 else '중간'} 칸"}


def 폭(계열들: dict, 창: int = 60) -> dict:
    """**여럿이 같이 오르고 있나.** 한 종목만 보면 장세를 못 본다."""
    오름, 잰것 = 0, 0
    for c in 계열들.values():
        if len(c) < 창 + 2:
            continue
        r = c.수익(c.날들[-1 - 창], 창)
        if r is None:
            continue
        잰것 += 1
        오름 += 1 if r > 0 else 0
    return {"오름": 오름, "잰것": 잰것,
            "비율": (오름 / 잰것) if 잰것 else float("nan")}


def 장세별(계열, 날들: list, 수익들: list, 창: int = 60) -> dict:
    """**같은 사건을 장세 좋을 때와 나쁠 때로 갈라 잰다.**

    갈리는 자리를 안 보면 "규제 뉴스 뒤 -7.8%p" 가 사실은 "약세장에서만 -15%p, 강세장에선
    0" 일 수 있다. 가르는 선은 **그 계열 자기 추세 백분위의 중앙값**이다 -- 상수가 아니다.
    """
    from coin import null as NU
    모음 = [계열.수익(d, 창) for d in 계열.살수있는날들(창)]
    낮, 높 = [], []
    for d, v in zip(날들 or [], 수익들 or []):
        i = 계열.차례.get(d)
        if i is None or v is None or i < 창:
            continue
        앞 = 계열.수익(계열.날들[i - 창], 창)
        (낮 if _백분위(앞, 모음) < 0.5 else 높).append(v)
    부호 = lambda xs: 0 if not xs else (1 if NU.중앙(xs) > 0 else -1)          # noqa: E731
    return {"약세n": len(낮), "약세중앙": NU.중앙(낮) if 낮 else float("nan"),
            "강세n": len(높), "강세중앙": NU.중앙(높) if 높 else float("nan"),
            "갈림": bool(낮 and 높 and 부호(낮) != 부호(높))}


def 적기(g: dict) -> str:
    t, v, d, q = g["추세"], g["변동"], g["낙폭"], g["거래량"]
    줄 = [f"  {g['자산']} 장세: **{g['말']}**"]
    if t["백분위"] == t["백분위"]:
        줄.append(f"    추세 {t['창']}일 {t['값']*100:+.1f}% -> 자기 역사의 "
                  f"{t['백분위']*100:.0f}% 자리")
    if v["백분위"] == v["백분위"]:
        줄.append(f"    변동 {v['창']}일 -> {v['백분위']*100:.0f}% 자리")
    if d["백분위"] == d["백분위"]:
        줄.append(f"    낙폭 고점 대비 {d['값']*100:.1f}% -> {d['백분위']*100:.0f}% 자리")
    if q.get("백분위") == q.get("백분위"):
        움 = q.get("그날움직임", float("nan"))
        줄.append(f"    거래량 {q['날']} -> 자기 역사의 {q['백분위']*100:.0f}% 자리"
                  + (f", 그날 값은 {움*100:+.1f}%" if 움 == 움 else "")
                  + "  (**지갑을 본 것이 아니다 -- 거래량이다**)")
    return "\n".join(줄)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--자산", default="BTC")
    ap.add_argument("--폭", default="")
    a = ap.parse_args(argv)
    from coin import price as PR
    if a.폭:
        계열들 = {}
        for x in a.폭.split(","):
            원 = PR.불러오기(x.strip())
            if 원:
                계열들[x.strip()] = PR.계열(원)
        b = 폭(계열들)
        print(f"폭: {b['오름']}/{b['잰것']} 종목이 오르고 있다 ({b['비율']*100:.0f}%)")
        return 0 if b["잰것"] else 3
    원 = PR.불러오기(a.자산)
    if not 원:
        print(f"가격 원장이 없다: {a.자산}", file=sys.stderr)
        return 3
    print(적기(장세(PR.계열(원), 원)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
