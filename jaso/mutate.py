"""**관문이 진짜 잡는가** -- 성한 자소서에 결함 하나를 일부러 심고 잡히는지 본다.

    python3 jaso/mutate.py 자소서.md --표 내원장.json
    python3 jaso/mutate.py 자소서.md --표 내원장.json --놓침    # 놓친 것을 문장까지

`law/mutate.py` 를 그대로 옮겼다. 그 파일이 적어 둔 것:

    위반 0 은 좋은 소식처럼 보이지만 **그것만으로는 아무것도 증명하지 못한다.**
    관문이 잘 만들어져서 0 일 수도 있고, 아무것도 못 잡는 관문이라서 0 일 수도 있다.

    RED   -- 고장난 입력에서 반드시 위반을 보고해야 한다.
    GREEN -- 멀쩡한 입력에서 반드시 통과해야 한다.

자소서에서 이것이 특히 급하다. 법이론서는 틀려도 문서가 하나 나쁠 뿐이지만, 자소서는
**그 사람이 면접에서 그 말을 다시 해야 한다.** 관문이 못 잡은 부풀림은 사용자가 그것을
사실로 믿고 말하는 자리까지 간다.

## 심는 자리를 고른다

관문이 판정할 자격이 있는 자리에만 심는다. 원장이 `주도` 인 항목에 승격어를 심어 놓고
"J004 가 못 잡았다" 고 하는 것은 관문을 모함하는 것이다 -- 사실 그대로이므로 잡으면 안
된다. 그래서 돌연변이마다 심을 자리를 먼저 찾고, **심은 수와 잡은 수를 같이 적는다.**
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import gate as GT                                           # noqa: E402
from jaso import ledger as LG                                         # noqa: E402
from jaso import swap as SW                                           # noqa: E402
from jaso import wording as WD                                        # noqa: E402


def m_수치(문단: str, h: LG.항목, L: LG.원장):
    """J002 -- 잰 값을 **원장에 없는 수**로 바꾼다. F1(수치 창작)을 흉내 낸다.

    아무 수나 더하면 안 된다. 더한 값이 원장의 다른 값과 겹치면 그것은 환각이 아니게
    되고, 그러면 관문이 안 잡는 것이 맞다 -- `law/mutate.py` 의 `m_citation` 이 조문
    번호에서 같은 함정에 빠졌던 자리다.
    """
    맨수 = {v for x in L.항목들 for v in LG.값수(x)}
    쌍 = {p for x in L.항목들 for p in LG.값앵커(x)}
    for 수, 단위, _ in WD.성과수들(문단):
        for 더 in (7, 13, 29, 71, 143):
            새 = str(int(float(수) + 더)) if float(수) == int(float(수)) \
                else f"{float(수) + 더:.1f}"
            if 새 in 맨수 or f"{새}|{LG._단위(단위)}" in 쌍:
                continue
            m = re.search(re.escape(수) + r"\s*" + re.escape(단위), 문단)
            return 문단[:m.start()] + 새 + 단위 + 문단[m.end():] if m else None
    return None


def m_역할(문단: str, h: LG.항목, L=None):
    """J004 -- 원장이 `참여`·`보조`·`관찰` 인 항목에 승격어를 심는다."""
    if h.역할 == "주도" or WD.승격(문단):
        return None
    for 낱말, 대신 in (("참여하며", "주도하며"), ("참여한", "주도한"),
                      ("맡았", "총괄했"), ("했습니다", "제가 주도했습니다"),
                      ("들였습니다", "혼자 들였습니다")):
        if 낱말 in 문단:
            return 문단.replace(낱말, 대신, 1)
    return None


def m_기간(문단: str, h: LG.항목, L=None):
    """J003 -- 기간을 원장보다 길게 적는다. 없으면 새로 적어 넣는다."""
    if not h.개월:
        return None
    m = re.search(r"(\d+)\s*개월", 문단)
    if m and int(m.group(1)) == h.개월:
        return 문단[:m.start()] + f"{h.개월 + 6}개월" + 문단[m.end():]
    if not m and "." in 문단:
        k = 문단.index(".")
        return 문단[:k] + f"({h.개월 + 6}개월)" + 문단[k:]
    return None


def m_연도(문단: str, h: LG.항목, L: LG.원장):
    """J001 -- 원장에 없는 해를 적어 넣는다."""
    해들 = {y for x in L.항목들 for y in x.연도들}
    바깥 = next((str(y) for y in range(2010, 2035) if str(y) not in 해들), None)
    if not 바깥 or "." not in 문단:
        return None
    k = 문단.index(".")
    return 문단[:k] + f" ({바깥}년)" + 문단[k:]


def m_치환(문단: str, h: LG.항목, L: LG.원장):
    """P001 -- **앵커만 지운다.** 글은 그대로 두고 고유한 것을 일반어로 바꾼다.

    이것이 일반 LLM 이 재료 없이 내놓는 글의 꼴이다 -- 문장은 멀쩡하고 고유한 것만
    없다. 새로 지어 쓰지 않고 지우기만 하는 이유는, 지어 쓰면 무엇 때문에 걸렸는지가
    흐려지기 때문이다.
    """
    새 = 문단
    for a in sorted(LG.말앵커(h), key=len, reverse=True):
        새 = 새.replace(a, "해당 조직")
    for 수, 단위, _ in WD.수단위쌍(새):
        새 = 새.replace(f"{수}{단위}", "상당 수준").replace(
            f"{수} {단위}", "상당 수준")
    새 = re.sub(r"\d[\d,]*(?:\.\d+)?", "", 새)
    return 새 if not SW.앵커들(새, L) and 새 != 문단 else None


def m_상투(문단: str, h=None, L=None):
    """P003 -- 상투구를 심는다."""
    return (문단.rstrip() + " 귀사의 인재상에 부합하는 인재로서 최선을 다하겠습니다."
            if not WD.상투(문단) else None)


돌연변이들 = (
    ("J002 수치창작", m_수치, "J002"),
    ("J004 역할승격", m_역할, "J004"),
    ("J003 기간부풀림", m_기간, "J003"),
    ("J001 없는해", m_연도, "J001"),
    ("P001 치환가능", m_치환, "P001"),
    ("P003 상투구", m_상투, "P003"),
)


def _바꿔쓴것(글: str, 옛: str, 새: str) -> str:
    return 글.replace(옛, 새, 1)


def _다른자리(옛: str, 새: str) -> tuple:
    """무엇을 무엇으로 바꿨나. 앞뒤로 같은 데를 깎아 내면 남는 것이 바뀐 자리다."""
    i = 0
    while i < min(len(옛), len(새)) and 옛[i] == 새[i]:
        i += 1
    j = 0
    while j < min(len(옛), len(새)) - i and 옛[-1 - j] == 새[-1 - j]:
        j += 1
    return (옛[i:len(옛) - j] or "?", 새[i:len(새) - j] or "?")


def 돌리기(글: str, L: LG.원장, 놓침도: bool = False) -> dict:
    """문단마다 돌연변이를 심고 관문이 그 규칙으로 잡는지 센다."""
    tally = {이름: {"심음": 0, "잡음": 0, "놓친것": []} for 이름, _, _ in 돌연변이들}
    자 = GT.읽기(글)
    성한것, _, _ = GT.검사(자, L)
    이미 = {v.규칙 for v in 성한것 if v.등급 == "hard"}

    for a in 자.답변들:
        for p in a.문단들:
            h = SW.가리키는것(p, L)
            if h is None:
                continue
            for 이름, 만들기, 규칙 in 돌연변이들:
                if 규칙 in 이미:                 # 원래 걸려 있던 규칙은 판정에 못 쓴다
                    continue
                새 = 만들기(p, h, L)
                if not 새 or 새 == p:
                    continue
                tally[이름]["심음"] += 1
                vs, _, _ = GT.검사(GT.읽기(_바꿔쓴것(글, p, 새)), L)
                if any(v.규칙 == 규칙 for v in vs):
                    tally[이름]["잡음"] += 1
                elif 놓침도:
                    tally[이름]["놓친것"].append((_다른자리(p, 새), 새))
    return tally


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="관문이 진짜 잡는지 -- 결함 하나를 일부러 심어 본다")
    ap.add_argument("자소서")
    ap.add_argument("--표", dest="표", default="jaso/보기.json")
    ap.add_argument("--놓침", action="store_true", help="놓친 것을 문장까지 보여준다")
    a = ap.parse_args(argv)

    p = Path(a.자소서)
    if not p.exists():
        print(f"그런 파일이 없다: {p}", file=sys.stderr)
        return 2
    L = LG.읽기(a.표)
    if not L:
        print("원장이 비었다 -- **심어도 잡을 자가 없다.** 원장을 먼저 채워라",
              file=sys.stderr)
        return 2

    tally = 돌리기(p.read_text(encoding="utf-8"), L, a.놓침)
    print(f"{'돌연변이':<16}{'심음':>6}{'잡음':>6}{'놓침':>6}")
    심 = 잡 = 0
    for 이름, _, _ in 돌연변이들:
        t = tally[이름]
        심 += t["심음"]
        잡 += t["잡음"]
        print(f"{이름:<16}{t['심음']:>6}{t['잡음']:>6}{t['심음'] - t['잡음']:>6}")
    print(f"{'합계':<16}{심:>6}{잡:>6}{심 - 잡:>6}")

    눈먼것 = [n for n, _, _ in 돌연변이들
             if tally[n]["심음"] and not tally[n]["잡음"]]
    없던자리 = [n for n, _, _ in 돌연변이들 if not tally[n]["심음"]]
    if 눈먼것:
        print(f"\n**하나도 못 잡은 것: {', '.join(눈먼것)}** -- 그 관문은 지금 눈이 없다")
    if 없던자리:
        print(f"심을 자리가 없던 것: {', '.join(없던자리)} "
              f"(이 자소서에 해당 자리가 없다 -- 관문 잘못이 아니다)")
    if a.놓침:
        for 이름, _, _ in 돌연변이들:
            for (옛, 새), 문단 in tally[이름]["놓친것"][:3]:
                print(f"\n[놓침 {이름}] 심은 것: {옛!r} -> {새!r}")
                print("    " + re.sub(r"\s+", " ", 문단)[:150])
    return 1 if 눈먼것 else 0


if __name__ == "__main__":
    raise SystemExit(main())
