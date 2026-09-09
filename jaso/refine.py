"""**루프.** 관문이 짚은 자리를 원장의 사실로 되먹여 다시 쓴다. 나빠지면 버린다.

    python3 jaso/refine.py --표 원장.json --문항 "<원문>" --바퀴 4 --벌 3
    python3 jaso/refine.py --표 원장.json --문항 "<원문>" --궤적   # 무엇이 줄었나

```
문항 ─> 프롬프트(도출) ─> n벌 ─(관문)─> 점수 ─> 최선을 든다
             ↑                              │
             └── 위반이 **가리키는 원장 사실** ┘        나빠진 바퀴는 버린다
```

## 프롬프트를 모델이 짓지 않는다 -- 계산한다

    프롬프트 = 문항 요구  ×  원장 사실  ×  남은 위반이 가리키는 사실

모델이 프롬프트를 짓고 같은 계열 모델이 답하고 그것을 루프 돌리면 **바깥이 없는 닫힌
고리**다. 이 저장소가 두 번 덴 자리다(`mathdrift/spread.py` -- 발산 프롬프트에 심판을
실었더니 발산이 사양서가 됐다). 바깥은 둘뿐이다: **원장(사실)** 과 **관문(코드)**.

## 위반 이름을 모델에게 주지 않는다 -- 사실만 준다

    안 준다   "J002 위반이다. 원장에 있는 수만 써라"
    준다      "이 문장의 수는 제 기록에 없습니다. 제 기록은 클릭률 2.1% -> 2.6%
               (2주 A/B, n=48,000)입니다. 그 값으로 다시 쓰거나 수 없이 쓰십시오"

앞엣것을 주면 모델은 **원장의 수를 아무 데나 끼워 넣어 관문을 통과시킨다.** 그 문장은
통과했는데 틀린 문장이다 -- 관문이 사양서가 되는 순간이고, `law/write.py` 가 처음부터
피한 자리다. `tests/test_jaso_refine.py` 가 프롬프트에 관문 이름이 안 실리는 것을 고정한다.

## 단조 -- **정제됐다는 말을 검사받게 한다**

`mathdrift/mono.py` 가 "사슬이 어디로 가는가" 를 세는 자리와 같다. 그냥 돌리면 그것은
정제가 아니라 그냥 도는 것이다. 그래서 바퀴마다 점수를 재고 **최선을 늘 들고 간다.**

    점수 = (hard 수, soft 수, -앵커 수, -글자 채움)   사전식. 작을수록 좋다

나빠진 바퀴는 **버린다**(그 벌을 안 쓴다). `--궤적` 이 바퀴마다 무엇이 줄었는지 낸다.

## 루프가 못 고치는 것이 있다 -- 그때는 사람에게 돌아간다

같은 위반이 두 바퀴를 살아남으면 대개 **재료가 없는 것**이다. 원장에 없는 것을 모델이
채울 수는 없다(채우면 그것이 지어낸 것이다). 그래서 그런 위반이 남으면 **더 돌리지 않고**
`jaso/ask.py` 로 무엇을 물어야 하는지 낸다. 호출을 아끼는 것이 아니라, **거기서부터는
루프가 할 수 있는 일이 아니기 때문이다.**
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import ask as AS                                           # noqa: E402
from jaso import gate as GT                                          # noqa: E402
from jaso import item as IT                                          # noqa: E402
from jaso import ledger as LG                                        # noqa: E402
from jaso import swap as SW                                          # noqa: E402
from jaso import wording as WD                                       # noqa: E402
from jaso import write as WR                                         # noqa: E402

# 재료가 없어서 못 고치는 갈래. 두 바퀴를 살아남으면 사람에게 돌아간다.
재료부족 = {"J002", "J006", "P001", "P005", "D003"}


@dataclass
class 잰것:
    hard: int = 0
    soft: int = 0
    앵커: int = 0
    채움: float = 0.0        # 글자 수를 얼마나 채웠나 (0~1)

    @property
    def 점수(self) -> tuple:
        """**작을수록 좋다.** 사전식이라 hard 하나가 soft 열보다 무겁다."""
        return (self.hard, self.soft, -self.앵커, -round(self.채움, 2))

    def __str__(self) -> str:
        return (f"hard {self.hard} · soft {self.soft} · 앵커 {self.앵커}종 · "
                f"칸 {self.채움:.0%}")


@dataclass
class 바퀴:
    번호: int
    글: str = ""
    잰: 잰것 = field(default_factory=잰것)
    위반: list = field(default_factory=list)
    나아졌나: bool = False
    준말: list = field(default_factory=list)     # 이 바퀴에 무엇을 되먹였나


def 재기(q: IT.문항, 글: str, L: LG.원장, 회사="", 직무="") -> tuple:
    h, s, vs = WR.재기(q, 글, L, 회사, 직무)
    앵커 = SW.재기(글, L)["앵커수"]
    n = WD.글자수(글, q.공백포함)
    채움 = min(1.0, n / q.상한) if q.상한 else (1.0 if n else 0.0)
    return 잰것(h, s, 앵커, 채움), vs


# ---------------------------------------------------------------- 위반 -> 사실

def 위반을말로(v, L: LG.원장, q: IT.문항, 글: str) -> str:
    """**관문 이름을 빼고 사실만 남긴다.** 못 옮기는 것은 빈 문자열이다.

    여기가 이 파일의 심장이다. 위반을 그대로 주면 관문이 사양서가 되고, 아무 말도 안
    주면 루프가 안 돈다. 그 사이에 **'내 기록은 이렇다' 는 문장**이 있다.
    """
    말 = v.말
    if v.규칙 == "J002":
        쓸수있는것 = [f"{m.무엇} {m.전}{m.단위} -> {m.후}{m.단위} ({m.어떻게})"
                    for x in L.항목들 for m in x.잰것 if m.쓸수있나]
        if "잰 방법이 안 적혀" in 말:
            return ("적어 주신 수 중에 제가 어떻게 쟀는지 기록해 두지 않은 것이 "
                    "있습니다. 그 수는 빼고, 무엇이 달라졌는지 말로만 써 주십시오.")
        return ("이 답변에 제 기록에 없는 수가 있습니다. 제가 실제로 잰 것은 이것뿐입니다: "
                + (" · ".join(쓸수있는것) or "(없습니다)")
                + ". 이 값으로 다시 쓰거나, 수를 빼고 써 주십시오.")
    if v.규칙 == "J004":
        역할들 = " · ".join(f"[{x.이름 or x.id}] 은 {x.역할}" for x in L.항목들)
        return (f"제가 맡은 것을 제 기록보다 크게 적었습니다. 기록은 이렇습니다: {역할들}. "
                "그대로 써 주십시오 -- 크게 적으면 면접에서 되물었을 때 제가 답할 수 "
                "없습니다.")
    if v.규칙 == "J003":
        기간 = " · ".join(f"[{x.이름 or x.id}] {' ~ '.join(x.언제)} ({x.개월}개월)"
                        for x in L.항목들 if x.개월)
        return f"기간이 제 기록과 다릅니다. 기록은 이렇습니다: {기간}."
    if v.규칙 == "J001":
        해 = ", ".join(sorted({y for x in L.항목들 for y in x.연도들}))
        return (f"제 기록에 없는 해나 도구가 적혔습니다. 제가 일한 해는 {해} 뿐이고, "
                "쓴 것은 위 재료에 적힌 것뿐입니다.")
    if v.규칙 == "J005":
        n = WD.글자수(글, q.공백포함)
        if q.상한 and n > q.상한:
            return (f"지금 {n}자인데 {q.상한}자 안에 들어가야 합니다. "
                    f"{n - q.상한}자를 줄여 주십시오 -- 사실을 빼지 말고 "
                    "설명하는 말을 줄이십시오.")
        if q.하한 and n < q.하한:
            return f"지금 {n}자인데 {q.하한}자는 되어야 합니다. 더 적어 주십시오."
        return (f"지금 {n}자로 {q.상한}자 칸의 {n / q.상한:.0%}만 썼습니다. "
                "위 재료에서 아직 안 쓴 것을 더 넣어 주십시오.")
    if v.규칙 in ("P001", "D003"):
        앵커 = sorted({a for x in L.항목들 for a in LG.말앵커(x)}, key=len,
                     reverse=True)[:8]
        return ("이 글은 회사 이름만 바꾸면 어디에나 들어갑니다. **문단마다** 위 "
                "재료에서만 나올 수 있는 것을 하나씩 넣어 주십시오 -- 예를 들어 "
                + ", ".join(앵커) + " 같은 것입니다.")
    if v.규칙 == "P002":
        return ("저를 설명하는 형용사(성실 · 열정 · 책임감 같은 말)를 빼고, 그 자리에 "
                "제가 실제로 한 일을 넣어 주십시오.")
    if v.규칙 == "P003":
        return (f"어디서나 보는 말이 있습니다: {말.split(':', 1)[-1].strip()}. "
                "빼고 제 일로 바꿔 주십시오.")
    if v.규칙 == "P004":
        return ("'~되었습니다' 처럼 누가 했는지 안 보이는 문장이 많습니다. "
                "제가 한 일은 제가 주어가 되게 써 주십시오.")
    if v.규칙 == "P006":
        return "한 경험을 여러 곳에 되풀이했습니다. 다른 재료를 써 주십시오."
    if v.규칙 == "J007":
        return "무엇이 달라졌는지가 없습니다. 위 재료의 '잰 것' 을 결과로 써 주십시오."
    if v.규칙 == "J006":
        return ("문항이 물은 것 중 답이 없는 자리가 있습니다: "
                + 말.split("--")[0].strip() + ".")
    if v.규칙 == "D001":
        return ("문장 길이가 다 비슷합니다. 짧게 끊는 문장과 길게 이어가는 문장을 "
                "섞어 주십시오.")
    if v.규칙 == "D002":
        return ("'또한' · '이를 통해' 같은 이음말이 많습니다. 빼고 문장을 바로 "
                "이어 주십시오.")
    if v.규칙 == "D004":
        return "문단이 다 같은 크기입니다. 중요한 데를 길게, 나머지를 짧게 하십시오."
    if v.규칙 == "D005":
        return ("첫 문장이 문항을 되풀이합니다. 읽는 사람은 문항을 압니다 -- 그 자리에 "
                "첫 장면을 넣어 주십시오.")
    return ""


def 고칠말(위반들, L, q, 글, 몇: int = 5) -> list:
    """되먹일 말들. **hard 를 먼저, 같은 규칙은 한 번만.**"""
    본것, out = set(), []
    for v in sorted(위반들, key=lambda x: (x.등급 != "hard", x.규칙)):
        if v.규칙 in 본것:
            continue
        말 = 위반을말로(v, L, q, 글)
        if 말:
            본것.add(v.규칙)
            out.append(말)
        if len(out) >= 몇:
            break
    return out


def 고침프롬프트(q, 항목, 생각, 글, 말들, 회사="", 직무="",
             문법: str = "기본") -> str:
    """**바탕은 첫 프롬프트 그대로다.** 재료를 안 빼고 고칠 말만 덧붙인다.

    재료를 빼고 "이것만 고쳐라" 라고 하면 모델이 나머지를 기억으로 다시 채운다 --
    그 순간 원장 밖이 들어온다.
    """
    바탕 = WR.프롬프트(q, 항목, 생각, 회사, 직무, 문법)
    붙임 = "\n".join(f"- {m}" for m in 말들)
    return (바탕 + f"""

## 제가 먼저 써 본 것

{글}

## 고쳐 주셨으면 하는 것

{붙임}

위 재료 밖의 것을 새로 넣지는 마십시오. 고칠 데만 고치고 나머지는 그대로 두십시오.
본문만 다시 출력하십시오.""")


# ---------------------------------------------------------------- 루프

def 돌리기(q: IT.문항, L: LG.원장, 바퀴수: int = 4, 벌: int = 3, 회사="", 직무="",
         쓴것=frozenset(), 묻기=None, 문법: str = "기본") -> dict:
    """관문이 짚은 자리를 사실로 되먹이며 돈다. **나빠지면 버린다.**"""
    항목, 생각 = WR.고르기(q, L, 쓴것)
    첫 = WR.쓰기(q, L, 벌, 회사, 직무, 쓴것, 묻기, 문법)
    if not 첫["글있나"]:
        return {"문항": q, "바퀴들": [], "최선": None, "글있나": False,
                "왜": 첫["왜"], "남은것": [], "물을것": []}

    최선글 = 첫["뽑힘"]["글"]
    최선잰, 최선위반 = 재기(q, 최선글, L, 회사, 직무)
    궤적 = [바퀴(0, 최선글, 최선잰, 최선위반, True)]
    살아남은것 = {}

    정체 = 0
    for n in range(1, max(0, 바퀴수) + 1):
        if not 최선위반:
            break
        # **안 움직이면 멈춘다.** 그냥 도는 것은 정제가 아니고, 바퀴마다 호출이 나간다.
        # `mathdrift/mono.py` 가 "사슬이 어디로 가는가" 를 세는 자리와 같은 규율이다.
        if 정체 >= 2:
            break
        # **재료가 없어 못 고치는 것만 남았으면 멈춘다.** 더 돌려도 지어내기만 한다.
        #
        # `hard` 만 본다. soft 까지 걸면 상투구 하나가 남았다고 계속 도는데, 그것은
        # 고칠 수 있는 것이라 멈출 이유가 아니다. 반대로 hard 가 전부 재료 문제면
        # **모델이 할 수 있는 일이 없다** -- 없는 것을 채우면 그것이 지어낸 것이다.
        for v in 최선위반:
            살아남은것[(v.규칙, v.어디)] = 살아남은것.get((v.규칙, v.어디), 0) + 1
        굳은것 = [v for v in 최선위반 if v.등급 == "hard"
                 and v.규칙 in 재료부족 and 살아남은것.get((v.규칙, v.어디), 0) >= 2]
        if 굳은것 and len(굳은것) == len([v for v in 최선위반 if v.등급 == "hard"]):
            break

        말들 = 고칠말(최선위반, L, q, 최선글)
        if not 말들:
            break
        프 = 고침프롬프트(q, 항목, 생각, 최선글, 말들, 회사, 직무, 문법)
        후보 = []
        for _ in range(max(1, 벌)):
            try:
                새글 = WR.벗기기((묻기 or WR._풀에게)(프))
            except Exception:
                continue
            if 새글.strip():
                후보.append((새글, *재기(q, 새글, L, 회사, 직무)))
        if not 후보:
            궤적.append(바퀴(n, "", 최선잰, 최선위반, False, 말들))
            break
        새글, 새잰, 새위반 = min(후보, key=lambda x: x[1].점수)
        나아짐 = 새잰.점수 < 최선잰.점수
        궤적.append(바퀴(n, 새글, 새잰, 새위반, 나아짐, 말들))
        정체 = 0 if 나아짐 else 정체 + 1
        if 나아짐:                       # **나빠진 바퀴는 버린다** -- 최선을 들고 간다
            최선글, 최선잰, 최선위반 = 새글, 새잰, 새위반

    물을것 = []
    if 최선위반:
        물을것 = [x for x in AS.물을것([q], L, 4)]
    return {"문항": q, "바퀴들": 궤적, "최선": {"글": 최선글, "잰": 최선잰,
                                          "위반": 최선위반, "항목": [h.id for h in 항목]},
            "글있나": True, "왜": "", "남은것": 최선위반, "물을것": 물을것}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="관문이 짚은 자리를 사실로 되먹여 다시 쓴다")
    ap.add_argument("--표", dest="표", required=True)
    ap.add_argument("--문항", dest="문항", action="append", default=[], required=True)
    ap.add_argument("--회사", default="")
    ap.add_argument("--직무", default="")
    ap.add_argument("--바퀴", dest="바퀴", type=int, default=4)
    ap.add_argument("--벌", dest="벌", type=int, default=3)
    ap.add_argument("--문법", dest="문법", default="기본",
                    help="bench 가 고른 것을 쓴다")
    ap.add_argument("--궤적", action="store_true", help="바퀴마다 무엇이 줄었나")
    ap.add_argument("--낼곳", default="")
    a = ap.parse_args(argv)

    L = LG.읽기(a.표)
    if not L:
        print("원장이 비었다 -- 쓸 재료가 없다", file=sys.stderr)
        return 3
    if LG.hard(LG.검사(L)):
        for v in LG.hard(LG.검사(L)):
            print(f"  {v}", file=sys.stderr)
        return 1

    조각, 쓴것, 남은게있나 = [], set(), False
    for i, 글 in enumerate(a.문항, 1):
        q = IT.쪼개기(글, str(i))
        r = 돌리기(q, L, a.바퀴, a.벌, a.회사, a.직무, 쓴것, 문법=a.문법)
        if not r["글있나"]:
            print(f"\n**문항 {i} 에서 한 벌도 글을 못 받았다: {r['왜']}**\n"
                  "  (GEMINI_API_KEY 가 있는 데서 돌려라 -- 빈 파일은 안 쓴다)",
                  file=sys.stderr)
            return 3
        쓴것 |= set(r["최선"]["항목"])
        조각.append(f"## {q.번호}. {q.원문}\n\n{r['최선']['글']}\n")
        print(f"\n[문항 {i}] {len(r['바퀴들'])}바퀴")
        for b in r["바퀴들"]:
            표 = "나아짐" if b.나아졌나 else ("버림 " if b.번호 else "첫벌 ")
            print(f"   {b.번호}바퀴 {표}  {b.잰}")
            if a.궤적 and b.준말:
                for m in b.준말:
                    print(f"        되먹임: {m[:76]}")
        print(f"   최선: {r['최선']['잰']}")
        if r["남은것"]:
            남은게있나 = True
            print(f"   **남은 위반 {len(r['남은것'])}건** -- 루프가 못 고쳤다:")
            for v in r["남은것"]:
                print(f"     {v}")
            if r["물을것"]:
                print("   여기서부터는 재료 문제다. 사람에게 물을 것:")
                for x in r["물을것"][:3]:
                    print(f"     · {x.말[:80]}")

    글 = (f"---\n회사: \"{a.회사}\"\n직무: \"{a.직무}\"\n---\n\n" + "\n".join(조각))
    if a.낼곳:
        Path(a.낼곳).write_text(글, encoding="utf-8")
        print(f"\n[씀] {a.낼곳}")
    else:
        print("\n" + 글)
    return 1 if 남은게있나 else 0


if __name__ == "__main__":
    raise SystemExit(main())
