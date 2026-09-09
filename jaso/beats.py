"""**박자와 차례.** 종류를 내가 안 정한다 -- 잰 것에서 무리로 나온다.

    python3 jaso/beats.py --곳 jaso/corpus/잰형식      # 어떤 박자가 나왔나
    python3 jaso/beats.py --차례                       # 무엇 다음에 무엇이 오나
    python3 jaso/beats.py --문법후보                   # forms.py 에 붙일 초안

## 문법은 문장이 아니라 **차례**다

`novel/beat.py` 가 회차를 비트 차례로 쓰는 자리와 같다. 자소서 한 편도 문단마다 하는
일이 다르다 -- 장면을 세우는 자리 · 한 일을 적는 자리 · 수로 결과를 대는 자리 ·
깨달은 것을 적는 자리. **문법은 그 차례다.**

## 박자 종류를 하드코딩하지 않는다

`novel/arc.py` 의 `STAGES` 는 손으로 적은 목록이다. 소설에서는 그래도 됐다 -- 3막
8시퀀스가 밖에 있는 이론이므로. **자소서에는 그런 것이 없다.** 내가 '상황·행동·결과'
같은 목록을 적으면 그 순간 그것이 사양서가 되고, 캐 온 자료는 내 목록을 확인해 주는
데밖에 못 쓰인다.

그래서 **문단을 재고 무리를 짓는다.** 무리가 박자다.

    문단 -> 아홉 축으로 잰다 -> 무리짓기 -> 무리 하나가 박자 하나
                                              이름은 **중심에서 저절로 나온다**

이름도 안 적는다. `수·과거` 같은 이름은 그 무리의 중심이 어느 축에서 두드러지는지에서
나온 것이지 내가 붙인 뜻이 아니다.

## 축은 특징이지 박자가 아니다

아홉 축은 **말의 꼴**을 잰다(수가 있나 · 과거형인가 · 전환어가 있나). 그것이 어떤
박자인지는 안 정한다 -- 정하는 것은 무리다. `wording.py` 가 낱말을 세는 것과 같은
자리이고, `mine.py` 의 형식 축과 같은 규율이다.

## 흔들리면 문법이 아니다

무리짓기는 시작점에 따라 답이 달라진다. 돌릴 때마다 다른 박자가 나오면 그것은 문법이
아니라 잡음이다. 그래서 **시작점을 데이터에서 정한다**(제일 멀리 떨어진 점부터) --
같은 자료면 같은 답이 나온다. `tests/test_jaso_beats.py` 가 그것을 붙든다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import swap as SW                                          # noqa: E402
from jaso import wording as WD                                       # noqa: E402

# **축은 말의 꼴이다 -- 박자가 아니다.** 무엇이 박자인지는 무리가 정한다.
축 = ("수", "고유", "과거", "앞말", "되새김", "전환", "말소리", "길이", "나")

_수 = re.compile(r"\d[\d,]*(?:\.\d+)?")
_고유 = re.compile(r"[A-Z][A-Za-z0-9+#.]{1,}|[가-힣]{2,6}(?:테크|전자|은행|공사|공단|"
                   r"대학교|연구소|병원|화학|제철|카드|증권|물산|중공업|바이오|팀|과|부)")
_과거 = re.compile(r"(했|였|었|았)(습니다|다|고|으며|는데|지만|으나)")
_앞말 = re.compile(r"(하겠|싶습니다|계획|앞으로|입사\s*후|나아가|기여하)")
_되새김 = re.compile(r"(배웠|깨달|느꼈|알게\s*되|돌아보|생각합니다|기준이\s*되)")
_전환 = re.compile(r"(그런데|하지만|그러나|처음에는|알고\s*보니|돌이켜|막상)")
_말소리 = re.compile(r"[\"'‘“][^\"'’”]{4,}[\"'’”]|라고\s*(말|물|답)")
_나 = re.compile(r"(저는|제가|저를|제\s)")


def 재기(문단: str) -> tuple:
    """문단 하나 -> 아홉 수. **글은 안 들고 나온다.**"""
    t = 문단 or ""
    n = max(1, len(t))
    ss = max(1, len(WD.문장들(t)))
    return (round(len(_수.findall(t)) * 100 / n, 3),
            round(len(set(_고유.findall(t))) * 100 / n, 3),
            round(len(_과거.findall(t)) / ss, 3),
            round(len(_앞말.findall(t)) / ss, 3),
            round(len(_되새김.findall(t)) / ss, 3),
            round(len(_전환.findall(t)) / ss, 3),
            round(len(_말소리.findall(t)) / ss, 3),
            round(min(3.0, n / 200), 3),
            round(len(_나.findall(t)) / ss, 3))


def 글재기(글: str) -> list:
    """한 편 -> 문단마다 아홉 수. 이것이 `mine.py` 에 담기는 것이다."""
    return [재기(p) for p in SW.문단들(글 or "")]


# ---------------------------------------------------------------- 무리짓기

def _거리(a, b) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def _펴기(벡터들: list) -> list:
    """축마다 0~1 로 편다. **안 펴면 `길이` 축 하나가 무리를 통째로 정한다.**"""
    if not 벡터들:
        return []
    폭 = []
    for i in range(len(축)):
        값 = [v[i] for v in 벡터들]
        아래, 위 = min(값), max(값)
        폭.append((아래, (위 - 아래) or 1.0))
    return [tuple((v[i] - 폭[i][0]) / 폭[i][1] for i in range(len(축)))
            for v in 벡터들]


def 무리짓기(벡터들: list, k: int, 바퀴: int = 30) -> tuple:
    """**시작점을 데이터에서 정한다** -- 같은 자료면 같은 답이 나온다.

    무작위 시작이면 돌릴 때마다 다른 박자가 나오고, 그러면 그것은 문법이 아니라
    잡음이다. 제일 멀리 떨어진 점부터 집는다(farthest-point).
    """
    X = _펴기(벡터들)
    if not X or k < 1:
        return [], []
    k = min(k, len(X))
    # **첫 점도 자리로 안 고른다.** `X[0]` 을 쓰면 편 차례만 바꿔도 다른 박자가
    # 나온다(실측: 같은 자료를 뒤집었더니 무리가 갈렸다). 평균에서 제일 먼 점부터
    # 집고, 같은 거리면 값 순으로 -- 자료가 같으면 답이 같아진다.
    평균 = tuple(sum(v[i] for v in X) / len(X) for i in range(len(축)))
    중심 = [min(X, key=lambda x: (-_거리(x, 평균), x))]
    while len(중심) < k:
        먼것 = min(X, key=lambda x: (-min(_거리(x, c) for c in 중심), x))
        if any(_거리(먼것, c) == 0 for c in 중심):
            break
        중심.append(먼것)
    배정 = [0] * len(X)
    for _ in range(바퀴):
        새배정 = [min(range(len(중심)), key=lambda j: _거리(x, 중심[j])) for x in X]
        if 새배정 == 배정:
            break
        배정 = 새배정
        for j in range(len(중심)):
            것 = [X[i] for i, a in enumerate(배정) if a == j]
            if 것:
                중심[j] = tuple(sum(c) / len(것) for c in zip(*것))
    return 중심, 배정


def 흩어짐(벡터들: list, 중심, 배정) -> float:
    X = _펴기(벡터들)
    return (sum(_거리(X[i], 중심[a]) for i, a in enumerate(배정)) / len(X)
            if X else 0.0)


def k고르기(벡터들: list, 최대: int = 7) -> int:
    """**k 도 안 정한다.** 흩어짐이 더는 안 줄어드는 자리에서 멈춘다(팔꿈치)."""
    if len(벡터들) < 4:
        return max(1, min(2, len(벡터들)))
    앞, 고른것 = None, 2
    for k in range(2, min(최대, len(벡터들)) + 1):
        중심, 배정 = 무리짓기(벡터들, k)
        s = 흩어짐(벡터들, 중심, 배정)
        if 앞 is not None and s > 앞 * 0.75:      # 줄어드는 폭이 4분의 1 미만
            break
        앞, 고른것 = s, k
    return 고른것


def 이름(중심, 모든중심) -> str:
    """**중심에서 저절로 나오는 이름.** 내가 붙인 뜻이 아니다.

    다른 무리 평균보다 두드러지는 축 둘을 이어 붙인다. 두드러지는 것이 없으면 `평이`.
    """
    if not 모든중심:
        return "?"
    평균 = [sum(c[i] for c in 모든중심) / len(모든중심) for i in range(len(축))]
    튄것 = sorted(range(len(축)), key=lambda i: -(중심[i] - 평균[i]))
    골라 = [축[i] for i in 튄것[:2] if 중심[i] - 평균[i] > 0.15]
    return "·".join(골라) or "평이"


# ---------------------------------------------------------------- 차례

@dataclass
class 박자표:
    이름들: list = field(default_factory=list)
    중심들: list = field(default_factory=list)
    차례들: list = field(default_factory=list)     # 편마다 박자 번호 열
    표본: int = 0

    def 전이(self) -> dict:
        """무엇 다음에 무엇이 오나. `{(앞, 뒤): 몇 번}`."""
        out = {}
        for 열 in self.차례들:
            for a, b in zip(열, 열[1:]):
                out[(a, b)] = out.get((a, b), 0) + 1
        return out

    def 흔한차례(self, 길이: int = 3, 몇: int = 5) -> list:
        본것 = {}
        for 열 in self.차례들:
            for i in range(len(열) - 길이 + 1):
                조각 = tuple(열[i:i + 길이])
                본것[조각] = 본것.get(조각, 0) + 1
        return sorted(본것.items(), key=lambda kv: (-kv[1], kv[0]))[:몇]

    def 자리(self, 박자: int) -> float:
        """이 박자가 글의 어디쯤에 오나. 0 이면 앞, 1 이면 뒤."""
        자리들 = [i / max(1, len(열) - 1)
                for 열 in self.차례들 for i, b in enumerate(열) if b == 박자]
        return round(sum(자리들) / len(자리들), 2) if 자리들 else 0.0


def 세우기(편별벡터: list, k: int = 0) -> 박자표:
    """편마다의 문단 벡터 -> 박자표. **k 도 데이터가 정한다.**"""
    모두 = [v for 편 in 편별벡터 for v in 편]
    if not 모두:
        return 박자표()
    k = k or k고르기(모두)
    중심, 배정 = 무리짓기(모두, k)
    이름들 = [이름(c, 중심) for c in 중심]
    차례들, i = [], 0
    for 편 in 편별벡터:
        차례들.append(배정[i:i + len(편)])
        i += len(편)
    return 박자표(이름들, 중심, 차례들, len(편별벡터))


def 문법말(표: 박자표) -> list:
    """박자표 -> 프롬프트에 넣을 지시. **차례를 말로 옮긴다.**"""
    if not 표.차례들:
        return []
    흔한 = 표.흔한차례(3, 1)
    줄 = []
    if 흔한:
        조각 = " -> ".join(표.이름들[b] for b in 흔한[0][0])
        줄.append(f"문단을 이 차례로 놓습니다: **{조각}**.")
    앞것 = min(range(len(표.이름들)), key=표.자리) if 표.이름들 else None
    뒷것 = max(range(len(표.이름들)), key=표.자리) if 표.이름들 else None
    이름풀이 = {"수": "잰 값을 대는", "고유": "이름과 자리를 대는",
              "과거": "지난 일을 적는", "앞말": "앞으로 할 일을 적는",
              "되새김": "무엇을 알게 됐는지 적는", "전환": "생각이 바뀐 자리를 적는",
              "말소리": "그때 오간 말을 적는", "길이": "길게 풀어 쓰는",
              "나": "내가 한 일을 적는"}

    def 풀이(이름: str) -> str:
        return " · ".join(이름풀이.get(x, x) for x in 이름.split("·")) or 이름
    if 앞것 is not None:
        줄.append(f"첫 문단은 **{풀이(표.이름들[앞것])}** 자리로 엽니다.")
    if 뒷것 is not None and 뒷것 != 앞것:
        줄.append(f"마지막 문단은 **{풀이(표.이름들[뒷것])}** 자리로 닫습니다.")
    긴것 = max(len(x) for x in 표.차례들)
    줄.append(f"문단은 {긴것}개를 넘지 않습니다.")
    return 줄


# ---------------------------------------------------------------- CLI

def _읽기(곳: str) -> list:
    from jaso import mine as MN
    편별 = []
    for x in MN.읽기(곳):
        if x.문단벡터:
            편별.append([tuple(v) for v in x.문단벡터])
    return 편별


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="박자와 차례 (종류는 데이터가 정한다)")
    ap.add_argument("--곳", default="")
    ap.add_argument("--k", type=int, default=0, help="0 이면 데이터가 정한다")
    ap.add_argument("--차례", action="store_true")
    ap.add_argument("--문법후보", action="store_true")
    a = ap.parse_args(argv)

    from jaso import mine as MN
    편별 = _읽기(a.곳 or str(MN.잰것DIR))
    if not 편별:
        print("문단 벡터가 있는 표본이 없다.\n"
              "  python3 jaso/mine.py --질의 \"...\" 로 먼저 받아라 (**VM 에서**)",
              file=sys.stderr)
        return 3
    표 = 세우기(편별, a.k)
    print(f"표본 {표.표본}편 · 문단 {sum(len(x) for x in 표.차례들)}개 · "
          f"박자 {len(표.이름들)}개 (k 는 데이터가 정했다)\n")
    for i, 이 in enumerate(표.이름들):
        몇 = sum(1 for 열 in 표.차례들 for b in 열 if b == i)
        print(f"  [{i}] {이:<12} 문단 {몇:>3}개 · 자리 {표.자리(i):.2f}")
    if a.차례 or a.문법후보:
        print("\n흔한 차례 (3박자):")
        for 조각, 몇 in 표.흔한차례(3, 5):
            print(f"  {몇:>3}번  " + " -> ".join(표.이름들[b] for b in 조각))
    if a.문법후보:
        말 = 문법말(표)
        몸 = "\n".join(f'         "{x}",' for x in 말)
        print(f"\n# jaso/forms.py 의 `문법들` 에 붙일 초안 -- **가설이지 결론이 아니다**\n")
        print(f'    "캔차례": 문법(\n        "캔차례", "합격 자소서 {표.표본}편에서 '
              f'나온 박자 차례 (가설)",\n        [\n{몸}\n'
              '         "위 경험에서만 나올 수 있는 것을 문단마다 하나는 둡니다.",\n'
              '        ]),')
        print("\n붙인 뒤 반드시 재라:  python3 jaso/bench.py --표 원장.json "
              "--문항 \"...\" --문법 캔차례 --문법 기본 --맨")
    if 표.표본 < 20:
        print(f"\n**표본이 {표.표본}편뿐이다** -- 무리가 흔들릴 만큼 적다. "
              "차례를 결론처럼 읽지 마라")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
