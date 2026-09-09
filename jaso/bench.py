"""**무엇이 나은가를 잰다.** 감으로 정한 것을 재서 정하는 자리.

    python3 jaso/bench.py --표 원장.json --문항 "<원문>" --벌 3 --되풀이 2
    python3 jaso/bench.py --표 원장.json --문항 "<원문>" --문법 기본 --문법 두괄
    python3 jaso/bench.py --표 원장.json --문항 "<원문>" --맨 --문법 기본   # 대조군

## 이것은 **합격률이 아니다**

먼저 이것부터 적는다. 이 파일이 내는 수를 합격률로 읽으면 그 순간 이 파이프라인이
제일 싫어하는 것 -- **판정 안 받은 답에 판정받은 옷을 입히는 것** -- 이 된다.

합격률을 재려면 `(자소서, 합격여부)` 짝이 있어야 한다. 세 가지가 막는다.

| | |
|---|---|
| **선택 편향** | 인터넷의 '합격 자소서' 는 합격자만 올린다. 불합격 쪽이 통째로 빠진 표본에서 "합격 자소서의 특징" 을 아무리 세도, 불합격 자소서도 같은 특징을 갖는지 알 수가 없다 |
| **교란** | 합격은 자소서가 정하지 않는다. 학점·전공·경력·자격·면접·TO·경쟁률이 대부분이다. "인턴을 쓴 자소서가 합격률이 높다" 의 원인은 형식이 아니라 **인턴** 이다 |
| **딥러닝이 가린다** | 편향된 라벨에 큰 모델을 붙이면 편향이 사라지는 것이 아니라 **더 자신 있게 재현된다.** 그리고 왜 그렇게 골랐는지 물어볼 수도 없어진다 |

`brain/README.md` R004 의 갈래로는 **전망**이다 -- 관할 밖. 관할 밖이라고 답을 못 하는
것이 아니라, **판정 없이 답한다고 말하고 답하는 것**이다.

## 그러면 무엇을 재나 -- 관문

바깥에 심판이 하나 있다: `jaso/gate.py`. LLM 이 아니고, 생성자가 그 존재를 모르며,
`mutate.py` 로 RED/GREEN 을 이미 확인했다.

    이 문법으로 쓰면  지어낸 수가 덜 나오는가 · 역할을 덜 부풀리는가 ·
                      문항에 더 닿는가 · 그 사람만 쓸 수 있는 글이 더 나오는가

`mathgen` 이 sympy 로 채점하고 `compression` 이 심판으로 채점한 자리와 같다 --
**무엇이 더 나은가를 LLM 이 정하지 않는다.**

## 대조군을 같이 돌린다

`--맨` 은 원장도 문항 분해도 없이 문항만 던진 것이다. 일반 LLM 에 "이 문항으로 자소서
써 줘" 한 것과 같다. **이것이 없으면 우리 수가 좋은지 알 수 없다** -- 이 저장소가
`seek/` 에서 대조군 `P3` 를 둔 것과 같은 이유다.
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import echo as EC                                          # noqa: E402
from jaso import forms as FM                                         # noqa: E402
from jaso import item as IT                                          # noqa: E402
from jaso import ledger as LG                                        # noqa: E402
from jaso import refine as RF                                        # noqa: E402
from jaso import write as WR                                         # noqa: E402


@dataclass
class 성적:
    이름: str
    잰것들: list = field(default_factory=list)
    죽은것: int = 0
    겹침들: list = field(default_factory=list)     # 예시를 얼마나 베꼈나

    @property
    def 겹침(self) -> float:
        return st.fmean(self.겹침들) if self.겹침들 else 0.0

    @property
    def 벌(self) -> int:
        return len(self.잰것들)

    def _평(self, 뽑기) -> float:
        return st.fmean([뽑기(x) for x in self.잰것들]) if self.잰것들 else 0.0

    @property
    def hard(self) -> float:
        return self._평(lambda x: x.hard)

    @property
    def soft(self) -> float:
        return self._평(lambda x: x.soft)

    @property
    def 앵커(self) -> float:
        return self._평(lambda x: x.앵커)

    @property
    def 채움(self) -> float:
        return self._평(lambda x: x.채움)

    @property
    def 성한비율(self) -> float:
        """**hard 0 인 벌의 비율.** 이 파일이 내는 제일 중요한 수다."""
        return (sum(1 for x in 잰 if x.hard == 0) / len(잰)
                if (잰 := self.잰것들) else 0.0)

    @property
    def 점수(self) -> tuple:
        return (round(self.hard, 3), round(self.soft, 3),
                -round(self.앵커, 3), -round(self.채움, 3))


def 예시프롬프트(q: IT.문항, 항목, 생각, 예시들: list, 회사="", 직무="") -> str:
    """**"그렇게 만들어줘".** 긁어온 글을 프롬프트에 넣고 이렇게 쓰라고 한다.

    자연스러운 방법이고 대개 잘 된다. 여기 있는 이유는 **재기 위해서**다 -- 이겼는지
    졌는지, 그리고 **얼마나 베꼈는지**(`echo.py`). 예시는 프롬프트에만 들어가고
    어디에도 저장되지 않는다(`mine.py` M001 은 담는 쪽 규칙이다).
    """
    바탕 = WR.프롬프트(q, 항목, 생각, 회사, 직무)
    벌 = "\n\n".join(f"### 보기 {i}\n{x[:1500]}" for i, x in enumerate(예시들, 1))
    return (바탕 + f"""

## 이런 글들입니다

{벌}

위 보기들처럼 써 주십시오. 다만 **보기의 내용은 제 것이 아닙니다** -- 문장을 가져오지
말고, 위에 적힌 제 재료로만 쓰십시오.""")


def 맨프롬프트(q: IT.문항, 회사: str = "", 직무: str = "") -> str:
    """**대조군.** 원장도 요구 분해도 없이 문항만. 일반 LLM 에 시킨 것과 같다."""
    어디 = (f"{회사} " if 회사 else "") + (f"{직무} 직무 " if 직무 else "")
    칸 = f"{q.상한}자 이내로 " if q.상한 else ""
    return (f"{어디}지원자로서 아래 자기소개서 문항에 {칸}답해 주세요.\n\n"
            f"{q.원문}\n\n본문만 출력하세요.")


def 재기(q: IT.문항, L: LG.원장, 문법들: list, 벌: int = 3, 되풀이: int = 1,
        회사="", 직무="", 맨: bool = False, 묻기=None, 예시들=()) -> list:
    """문법마다 (벌 x 되풀이) 를 돌려 관문으로 채점한다. **LLM 이 채점하지 않는다.**

    `예시들` 을 주면 "그렇게 만들어줘" 후보가 하나 더 돌고, **모든 후보의 겹침**을
    그 예시에 대고 잰다 -- 예시를 안 준 후보가 우연히 비슷해질 수도 있으므로.
    """
    항목, 생각 = WR.고르기(q, L)
    돌릴것 = [(이름, None) for 이름 in 문법들]
    if 예시들:
        돌릴것.append(("보기(그렇게)",
                     예시프롬프트(q, 항목, 생각, list(예시들), 회사, 직무)))
    if 맨:
        돌릴것.append(("맨(대조군)", 맨프롬프트(q, 회사, 직무)))
    부르기 = 묻기 or WR._풀에게

    out = []
    for 이름, 고정프 in 돌릴것:
        s = 성적(이름)
        프 = (고정프 if 고정프 is not None
             else WR.프롬프트(q, 항목, 생각, 회사, 직무, 이름))
        for _ in range(max(1, 벌) * max(1, 되풀이)):
            try:
                글 = WR.벗기기(부르기(프))
            except Exception:
                s.죽은것 += 1
                continue
            if not 글.strip():
                s.죽은것 += 1
                continue
            잰, _ = RF.재기(q, 글, L, 회사, 직무)
            s.잰것들.append(잰)
            if 예시들:
                s.겹침들.append(EC.재기(글, list(예시들))["겹침"])
        out.append(s)
    return out


def 순위(성적들: list) -> list:
    """**점수순.** 같으면 이름순 -- 흔들리면 견줄 수가 없다."""
    return sorted([s for s in 성적들 if s.벌], key=lambda s: (s.점수, s.이름))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="어느 문법이 관문을 더 잘 지나는가 (합격률이 아니다)")
    ap.add_argument("--표", dest="표", required=True)
    ap.add_argument("--문항", dest="문항", action="append", default=[], required=True)
    ap.add_argument("--문법", dest="문법들", action="append", default=[])
    ap.add_argument("--회사", default="")
    ap.add_argument("--직무", default="")
    ap.add_argument("--벌", dest="벌", type=int, default=3)
    ap.add_argument("--되풀이", dest="되풀이", type=int, default=1,
                    help="같은 문법을 몇 번 더 돌릴까 (모델 출력이 흔들린다)")
    ap.add_argument("--맨", action="store_true", help="대조군(문항만 던지기)도 같이")
    ap.add_argument("--예시", nargs="*", default=[],
                    help="예시 자소서 파일들 -- '그렇게 만들어줘' 후보가 같이 돈다")
    ap.add_argument("--예시글", action="append", default=[], help="예시를 바로")
    a = ap.parse_args(argv)

    L = LG.읽기(a.표)
    if not L:
        print("원장이 비었다 -- 잴 것이 없다", file=sys.stderr)
        return 3
    if LG.hard(LG.검사(L)):
        for v in LG.hard(LG.검사(L)):
            print(f"  {v}", file=sys.stderr)
        return 1
    문법들 = a.문법들 or list(FM.문법들)
    예시들 = [Path(p).read_text(encoding="utf-8") for p in a.예시
             if Path(p).is_file()] + list(a.예시글)

    모은것 = {}
    for i, 글 in enumerate(a.문항, 1):
        q = IT.쪼개기(글, str(i))
        for s in 재기(q, L, 문법들, a.벌, a.되풀이, a.회사, a.직무, a.맨,
                     예시들=예시들):
            모인 = 모은것.setdefault(s.이름, 성적(s.이름))
            모인.잰것들 += s.잰것들
            모인.죽은것 += s.죽은것
            모인.겹침들 += s.겹침들

    표 = 순위(list(모은것.values()))
    if not 표:
        print("\n**한 벌도 못 받았다.** GEMINI_API_KEY 가 있는 데서 돌려라",
              file=sys.stderr)
        return 3

    print(f"\n문항 {len(a.문항)}개 · 문법마다 {a.벌 * a.되풀이}벌\n")
    겹칸 = "  겹침" if 예시들 else ""
    print(f"{'문법':<14}{'성한비율':>9}{'hard':>7}{'soft':>7}{'앵커':>7}"
          f"{'칸':>7}{'죽음':>6}{겹칸:>7}")
    for s in 표:
        줄 = (f"{s.이름:<14}{s.성한비율:>8.0%}{s.hard:>7.2f}{s.soft:>7.2f}"
             f"{s.앵커:>7.1f}{s.채움:>6.0%}{s.죽은것:>6}")
        print(줄 + (f"{s.겹침:>6.0%}" if 예시들 else ""))
    이긴것 = 표[0]
    print(f"\n제일 나은 것: **{이긴것.이름}** "
          f"(hard 0 인 벌 {이긴것.성한비율:.0%})")
    if len(표) > 1 and 표[0].점수 == 표[1].점수:
        print("  다만 **1위와 2위가 같은 점수다** -- 더 돌려야 갈린다(`--되풀이`)")
    if 예시들:
        벤것 = [s for s in 표 if s.겹침 > 0.05]
        if 벤것:
            print(f"\n  **예시를 베낀 것: "
                  + " · ".join(f"{s.이름} {s.겹침:.0%}" for s in 벤것) + "**")
            print("  겹침은 관문이 아니다 -- 관문은 **당신의 원장**과 대조하지 예시와")
            print("  대조하지 않는다. 그런데 표절 검사는 예시 쪽을 본다. 이 수는 "
                  "사람이 봐야 한다.")
        else:
            print("\n  예시를 베낀 자리는 없다 (낱말 다섯 이어짐 기준). "
                  "**뜻을 바꿔 쓴 것은 이 자가 못 잡는다**")
    if min(s.벌 for s in 표) < 5:
        print(f"  그리고 **표본이 작다**(문법마다 {min(s.벌 for s in 표)}벌) -- "
              "모델 출력이 흔들리므로 이 순위는 다음 번에 바뀔 수 있다")

    print("\n" + "=" * 62)
    print("**이 수는 합격률이 아니다.** 관문(J·P·D)을 얼마나 지나는가일 뿐이다.")
    print("  합격은 학점·전공·경력·면접·TO 가 대부분을 정하고, 그 라벨이 여기 없다.")
    print("  '합격 자소서' 모음은 합격자만 올리므로 불합격 쪽이 통째로 빠진 표본이다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
