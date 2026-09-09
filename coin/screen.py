"""**훑기 -- 지금 어느 종목이 어떤 자리인가.** 점수를 합치지 않는다.

    python3 coin/screen.py --지평 7
    python3 coin/screen.py --지평 7 --전부        기저율과 못 가른 것까지

## 왜 종합 점수를 안 만드나 -- 그것이 편향이 들어오는 자리다

"초과 x0.5 + 승률 x0.3 + 거래량 x0.2" 같은 것을 만들면 그 0.5·0.3·0.2 가 어디서
왔는지 아무도 못 말한다. 그리고 그 무게가 순위를 **전부** 정한다. 즉 종합 점수는
측정처럼 보이는 자리에 **내 취향을 숨기는 일**이다.

그래서 여기서는 하나만 가지고 줄을 세운다 -- **초과(관측 - 기저율)**. 나머지(승률 ·
표본 · 장세 · 거래량 · 흐름)는 **줄 세우기에 안 쓰고 옆에 그대로 적는다.** 무엇을
더 볼지는 읽는 사람이 정한다.

## 두 칸으로 가른다

    가른 것    다중비교 보정(BH)을 넘은 것. **기저율과 다르다고 말할 수 있다**
    못 가른 것  쟀는데 기저율과 안 갈린다. **없는 것이 아니라 못 가른 것이다**

둘째 칸을 안 보여 주면 "걸린 것만 보여 주는" 화면이 되고, 그것이 이 파이프라인이
`null.보정` 으로 막으려던 바로 그 편향이다. `--전부` 가 아니어도 **몇 개가 못 갈렸는지
수는 늘 적는다.**

## 장이 안 좋으면 맨 위에 적는다

`regime.장세()` 가 아래 칸이면 그것을 머리에 올린다. 오를 만한 것을 고르는 화면이
약세장에서 그대로 나가면, 읽는 사람은 그 목록을 **권유로 읽는다.** 이 파이프라인은
권유를 안 한다(`gate.py` C012) -- 그러면 장세도 같이 말해야 앞뒤가 맞는다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coin import ledger as LG                                         # noqa: E402
from coin import regime as RG                                         # noqa: E402


def 훑기(원장: dict, 계열들: dict, 지평: int = 7, 지금유형=None,
        흐름: dict = None) -> dict:
    """자산마다 지금 걸린 유형의 잰 값을 모은다. **줄 세우는 자는 초과 하나다.**"""
    가른것, 못가른것 = [], []
    for r in LG.쓸만한것(원장):
        if r["지평"] != 지평:
            continue
        if 지금유형 and r["유형"] not in 지금유형:
            continue
        c = 계열들.get(r["자산"])
        칸 = {
            "자산": r["자산"], "유형": r["유형"], "지평": 지평,
            "초과": r["초과"], "관측": r["관측중앙"], "기저율": r["널중앙"],
            "n": r["n"], "유효n": r["유효n"], "승률": r["승률"],
            "p": r["p양측"], "살아남음": r.get("살아남음", False),
            "나라수": r.get("나라수", 0), "부호일관": r.get("부호일관", True),
            "장세": (RG.장세(c) if c else None),
        }
        (가른것 if 칸["살아남음"] else 못가른것).append(칸)
    가른것.sort(key=lambda x: -x["초과"])
    못가른것.sort(key=lambda x: -x["초과"])
    나쁜장 = [x["자산"] for x in 가른것 + 못가른것
              if x["장세"] and x["장세"]["나쁨"]]
    return {"지평": 지평, "가른것": 가른것, "못가른것": 못가른것,
            "나쁜장": sorted(set(나쁜장)), "흐름": 흐름 or {},
            "시험수": (LG.쓸만한것(원장)[0].get("시험수", 0)
                     if LG.쓸만한것(원장) else 0)}


def 줄(x: dict) -> str:
    장 = x["장세"]
    장말 = ""
    if 장 and 장["추세"]["백분위"] == 장["추세"]["백분위"]:
        장말 = f" · 장세 {장['추세']['백분위']*100:.0f}%자리{'(아래칸)' if 장['나쁨'] else ''}"
    일 = "" if x["부호일관"] else " · **해마다 부호가 갈린다**"
    return (f"    {x['자산']:<6} {x['유형']:<14} 초과 {x['초과']*100:+6.2f}%p "
            f"(관측 {x['관측']*100:+.2f}% - 기저율 {x['기저율']*100:+.2f}%) "
            f"n={x['n']}(유효{x['유효n']}) 승률 {x['승률']*100:.0f}% "
            f"p={x['p']:.3f} 나라{x['나라수']}{장말}{일}")


def 적기(s: dict, 전부: bool = False) -> str:
    줄들 = []
    if s["나쁜장"]:
        줄들.append(f"  **장세가 아래 칸인 종목: {', '.join(s['나쁜장'])}** -- "
                    "아래 목록은 '오를 것' 이 아니라 '과거에 이런 뉴스 뒤 이랬다' 이다")
    if s["흐름"]:
        극단 = [f"{k} {v['백분위']*100:.0f}%자리" for k, v in s["흐름"].items()
                if v.get("백분위") == v.get("백분위")
                and (v["백분위"] > 0.8 or v["백분위"] < 0.2)]
        if 극단:
            줄들.append("  흐름에서 극단인 것: " + " · ".join(극단)
                        + "  (**지갑·포지션이지 예언이 아니다**)")
    줄들.append(f"  기저율과 갈린 것 {len(s['가른것'])}개 "
                f"(D+{s['지평']} · 이번 실행에서 {s['시험수']}번 쟀고 BH 보정)")
    for x in s["가른것"]:
        줄들.append(줄(x))
    if not s["가른것"]:
        줄들.append("    **없다.** 잰 것 중 기저율과 갈리는 것이 하나도 없다")
    줄들.append(f"  쟀지만 기저율과 못 가른 것 {len(s['못가른것'])}개"
                + ("" if 전부 else " (--전부 로 본다)"))
    if 전부:
        for x in s["못가른것"]:
            줄들.append(줄(x))
    return "\n".join(줄들)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--지평", type=int, default=7)
    ap.add_argument("--전부", action="store_true")
    ap.add_argument("--원장", default="")
    a = ap.parse_args(argv)
    from coin import flow as FL
    from coin import price as PR
    원장 = LG.불러오기(a.원장 or None)
    if not LG.쓸만한것(원장):
        print("쓸만한 잰것이 없다 -- python3 coin/run.py --채우기", file=sys.stderr)
        return 3
    계열들 = {}
    for x in sorted({r["자산"] for r in LG.쓸만한것(원장)}):
        원 = PR.불러오기(x)
        if 원:
            계열들[x] = PR.계열(원)
    print(적기(훑기(원장, 계열들, a.지평, None, FL.상태()), a.전부))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
