"""**베꼈나.** 생성물과 예시가 얼마나 겹치는지 잰다. 호출 0회.

    python3 jaso/echo.py --글 자소서.md --예시 예시1.txt 예시2.txt
    python3 jaso/echo.py --글 자소서.md --예시글 "<붙여넣은 예시>"

## 왜 있나 -- "그렇게 만들어줘" 를 재기 위해

긁어온 자소서 몇 편을 프롬프트에 넣고 "이렇게 만들어줘" 라고 하는 것은 자연스럽고,
대개 잘 된다. **문제는 그것이 얼마나 베꼈는지 아무도 안 잰다는 것이다.**

모델은 맥락에 있는 문장을 되쓴다. 그것이 in-context 학습이 되는 이유이기도 하다.
그래서 예시를 넣으면 **형식만 오는 것이 아니라 표현도 온다.** 조금이면 참고이고
많으면 표절인데, 그 선이 어디인지 **재지 않으면 모른다.**

여기가 그 자를 만드는 자리다. `--예시` 로 재면 수가 나오고, 수가 나오면 고를 수 있다.

## 무엇을 재나

    겹침    예시와 **다섯 낱말 이어짐**을 공유하는 비율 (0~1)
    최장    가장 긴 공통 토막의 글자 수
    어디    그 토막들 (사람이 눈으로 보라고)

다섯 낱말로 잡는 것은 표절 검사가 흔히 쓰는 눈금이다. **뜻은 안 본다** -- 뜻을 바꿔
쓴 것은 여기서 안 잡히고, 그것까지 잡으려면 다른 자가 필요하다. 못 잡는 것을 못
잡는다고 적는 것이 이 파일이 하는 일의 절반이다.

## 이 수를 관문에 안 건다

`gate.py` 는 **사용자의 원장**과 대조한다. 여기는 **긁어온 예시**와 대조한다 -- 예시는
그때그때 다르고, 저장하지도 않는다(`mine.py` M001). 판정 기준이 런마다 달라지는 것은
관문이 될 수 없다. 그래서 `bench.py` 가 축으로 쓰고, 관문에는 안 올린다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_토막 = re.compile(r"[0-9A-Za-z가-힣]+")
N = 5                       # 다섯 낱말 이어짐


def 낱말들(글: str) -> list:
    return _토막.findall(글 or "")


def _엔그램(낱말: list, n: int = N) -> set:
    return {tuple(낱말[i:i + n]) for i in range(len(낱말) - n + 1)}


def _최장공통(a: str, b: str) -> str:
    """가장 긴 공통 토막. **글이 길면 잘라서 본다** -- O(len(a)*len(b)) 다."""
    a, b = a[:6000], b[:6000]
    if not a or not b:
        return ""
    앞 = [0] * (len(b) + 1)
    끝, 길이 = 0, 0
    for i in range(1, len(a) + 1):
        새 = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                새[j] = 앞[j - 1] + 1
                if 새[j] > 길이:
                    길이, 끝 = 새[j], i
        앞 = 새
    return a[끝 - 길이:끝]


def 재기(글: str, 예시들: list) -> dict:
    """`{겹침, 최장, 어디}`. 예시가 없으면 0 이다 -- **못 잰 것이지 깨끗한 것이 아니다.**"""
    낱 = 낱말들(글)
    내것 = _엔그램(낱)
    if not 내것 or not 예시들:
        return {"겹침": 0.0, "최장": 0, "어디": [], "잴수있나": bool(내것 and 예시들)}
    남의것 = set()
    for x in 예시들:
        남의것 |= _엔그램(낱말들(x))
    겹친것 = 내것 & 남의것
    최장 = max((_최장공통(글, x) for x in 예시들), key=len, default="")
    어디 = sorted({" ".join(g) for g in 겹친것}, key=len, reverse=True)[:5]
    return {"겹침": round(len(겹친것) / len(내것), 3), "최장": len(최장),
            "어디": ([최장] if len(최장) >= 12 else []) + 어디, "잴수있나": True}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="생성물이 예시를 얼마나 베꼈나 (호출 0회)")
    ap.add_argument("--글", required=True)
    ap.add_argument("--예시", nargs="*", default=[], help="예시 파일들")
    ap.add_argument("--예시글", action="append", default=[], help="예시를 바로")
    a = ap.parse_args(argv)

    글 = Path(a.글).read_text(encoding="utf-8") if Path(a.글).is_file() else a.글
    예시들 = [Path(p).read_text(encoding="utf-8") for p in a.예시
             if Path(p).is_file()] + list(a.예시글)
    r = 재기(글, 예시들)
    if not r["잴수있나"]:
        print("**잴 것이 없다** -- 예시를 안 주면 0 이 나오는데, 그것은 깨끗한 것이 "
              "아니라 못 잰 것이다", file=sys.stderr)
        return 3
    print(f"예시 {len(예시들)}편 · 겹침 {r['겹침']:.1%} · 최장 공통 토막 {r['최장']}자")
    for x in r["어디"]:
        print(f"  · {x[:70]}")
    if r["겹침"] > 0.05 or r["최장"] >= 20:
        print("\n**베낀 자리가 있다.** 예시를 프롬프트에 넣으면 형식만 오는 것이 "
              "아니라 표현도 온다")
    print("\n뜻을 바꿔 쓴 것은 여기서 안 잡힌다 -- 낱말 다섯 이어짐으로만 본다")
    return 1 if (r["겹침"] > 0.05 or r["최장"] >= 20) else 0


if __name__ == "__main__":
    raise SystemExit(main())
