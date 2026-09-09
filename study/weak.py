"""**취약점을 세어서 말한다.** "너는 확률에 약해" 는 세 문제로도 할 수 있는 말이다.

    이 태그에서 n 번 중 k 번 틀렸다
    이 사람 전체 오답률은 p0 이다
    p0 짜리 동전을 n 번 던져 k 번 이상 나올 확률이 얼마인가   <- 이것이 p

`brief/infer.py` 가 시장에 쓰던 자를 사람에게 대는 것이다. 자가 같아야 하는 이유는
**같은 실수를 안 하려고**다 -- 거기서 배운 셋이 여기서도 그대로 온다.

    1. **못 잴 수 있음을 먼저 본다.** 못 잰 것을 '평범' 이라 하면 거짓말이다.
       태그가 셋인데 각 태그에 세 문제면, 다 틀려도 우연과 못 가른다.
       그때 나오는 답은 '약하지 않다' 가 아니라 **'못잼'** 이다.
    2. **여럿을 견주면 문턱을 조인다**(Holm). 태그 열 개를 훑으면 그중 하나는
       그냥 나빠 보인다. 안 조이면 매번 없는 약점을 찾아 준다.
    3. **도달 가능한 최소 p 를 같이 낸다.** 그것이 문턱보다 크면 무슨 결과가
       나와도 약점이라 말할 수 없다 -- 표본이 짧아서지 잘해서가 아니다.

## 왜 이항 꼬리인가

`brief` 의 `기저()` 는 "오늘 일어난 일이 과거에 얼마나 잦았나" 를 물었다. 여기 물음은
다르다 -- **"이 태그가 전체보다 나쁜가"** 다. 그래서 한쪽 이항 꼬리를 그대로 쓴다.
정확히 센다(근사 안 한다). 문제 수가 수백이면 근사해도 되지만, 오답노트는 대개
수십이고 거기서는 근사가 어긋난다.

## 도달 가능한 최소 p

이 태그를 **다 틀려도** 나올 수 있는 가장 작은 p 는 `p0**n` 이다. `brief/최소p` 와
같은 자리다 -- 짧은 원장에서 무슨 값이 나와도 못 가르는 것을 먼저 말한다.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brief import infer as IF                                  # noqa: E402
from study import note as NT                                   # noqa: E402

ALPHA = IF.ALPHA          # 문턱은 **저장소 하나로 쓴다**. 여기만 다르면 자가 둘이 된다

# 이보다 적으면 아예 안 센다. **4 로 두었다가 내렸다** -- 3/3 을 다 틀린 태그가
# 도달 가능한 최소 p 0.048 로 이미 갈릴 수 있는데도 `못잼` 으로 나왔다(실측). 문턱을
# 두 군데(MIN_N 과 최소p)에 두면 엄한 쪽이 조용히 이기고, 그러면 **가릴 수 있는 것을
# 못 가린다고 말한다.** 가르는 일은 `도달가능최소p` 하나가 한다 -- 그것이 정확한 자다.
# 여기 3 은 자가 아니라 밑바닥이다: 전체 오답률(p0)도 추정값이라 한두 개로는 그 자가
# 흔들린다.
MIN_N = 3


@dataclass
class 약점:
    태그: str
    n: int = 0
    틀린: int = 0
    오답률: float = 0.0
    기저: float = 0.0         # 이 사람 전체 오답률
    p: float | None = None
    p보정: float | None = None
    최소p: float = 1.0
    쓴기저: float = 0.0       # **판정에 실제로 쓴 자.** 화면이 이것과 다른 자를 쓰면 어긋난다
    판정: str = "못잼"        # 약함 / 평범 / 못잼
    문제들: list = field(default_factory=list)   # 틀린 문제 id -- **근거다**

    def __str__(self) -> str:
        p = "-" if self.p보정 is None else f"{self.p보정:.3f}"
        return (f"[{self.판정}] {self.태그}: {self.틀린}/{self.n} 틀림 "
                f"({self.오답률:.0%} vs 전체 {self.기저:.0%}) · 보정 p={p} · "
                f"도달가능 최소 p={self.최소p:.3f}")


def 이항꼬리(k: int, n: int, p: float) -> float:
    """`P(X >= k)`, X ~ B(n, p). **정확히 센다** -- 오답노트는 표본이 작다."""
    if n <= 0:
        return 1.0
    p = min(max(p, 0.0), 1.0)
    if p <= 0.0:
        return 1.0 if k <= 0 else 0.0
    if p >= 1.0:
        return 1.0 if k <= n else 0.0
    k = max(0, k)
    if k > n:
        return 0.0
    return min(1.0, sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
                        for i in range(k, n + 1)))


def 도달가능최소p(n: int, p0: float) -> float:
    """이 태그를 **다 틀려도** 나올 수 있는 가장 작은 p. `brief/최소p` 와 같은 자리."""
    if n <= 0:
        return 1.0
    return 이항꼬리(n, n, p0)


def 사유별(n: NT.공책, 갈래: str = "") -> dict:
    """**사유 -> (몇 번, 어느 문제).** 취약점의 알맹이는 여기다.

    사용자 지시(2026-09-09): "취약점은 (특정 과목)에 취약하다 이런 게 아니라 훨씬 더
    구체적이어야 한다." 태그로 세면 `확률에 약함` 까지가 끝이다. **틀린 까닭**으로
    세야 `조건부확률에서 분모를 전체로 잡는다` 가 나온다.

    `갈래` 를 주면 그것만("오답" 또는 "모름"). 둘은 고칠 데가 서로 다르므로 대개 갈라
    본다 -- 오답은 아는데 어긋난 것이고 모름은 아예 없는 것이다.

    문제 하나는 한 번만 센다(마지막 시도). 같은 문제를 다섯 번 틀렸다고 그 사유가
    다섯 배 무거운 것이 아니다.
    """
    본문제 = {}
    for a in n.시도:
        if a.맞았나 is False:
            본문제[a.문제id] = a
    out: dict = {}
    for qid, a in 본문제.items():
        if not a.사유 or (갈래 and a.갈래 != 갈래):
            continue
        칸 = out.setdefault(a.사유, [0, []])
        칸[0] += 1
        칸[1].append(qid)
    return out


def 사유취약점(n: NT.공책, 갈래: str = "", alpha: float = ALPHA) -> list:
    """**되풀이되는 까닭**을 찾는다. 한 번은 실수고 다섯 번은 버릇이다.

    ## 여기 자는 태그 때와 다르다

    태그는 "이 태그에서 남들보다(= 자기 평균보다) 많이 틀리나" 였다. 사유는 애초에
    틀린 것에만 붙으므로 그 물음이 안 된다. 대신 묻는 것:

        틀린 것이 W 개이고 사유가 S 가지다. 고르게 흩어졌다면 한 사유에 W/S 번쯤이다.
        이 사유가 k 번 나왔다. **고르게 흩어진 것 치고 너무 잦은가?**

    귀무가설은 `Binomial(W, 1/S)` 이고 한쪽 꼬리를 정확히 센다. S 를 데이터에서
    얻으므로 **이 자는 '고르게 흩어졌다면' 이라는 가정 위에 있다** -- 그 가정을
    화면에도 적는다(`plan.취약점보고`).

    도달 가능한 최소 p 는 `(1/S)**W` 다. 사유가 하나뿐이면(S=1) 무엇을 해도 p=1 이라
    **못잼** 이다 -- 맞는 답이다. 까닭이 한 가지뿐인데 그것을 '약점' 이라 부르면
    아무 말도 안 한 것이다.
    """
    표 = 사유별(n, 갈래)
    W = sum(v[0] for v in 표.values())
    S = len(표)
    if not 표:
        return []
    p1 = 1.0 / S if S else 1.0
    것들, ps = [], []
    for 사, (k, ids) in sorted(표.items()):
        p = 이항꼬리(k, W, p1) if (W >= MIN_N and S >= 2) else None
        것들.append(약점(태그=사, n=W, 틀린=k, 기저=p1,
                       오답률=(k / W if W else 0.0), 문제들=ids,
                       p=p, 최소p=도달가능최소p(W, p1), 쓴기저=p1))
        ps.append(p)
    잰자리 = [i for i, x in enumerate(ps) if x is not None]
    보정목록 = IF.holm([ps[i] for i in 잰자리])
    보정 = [None] * len(ps)
    for 자리, pb in zip(잰자리, 보정목록):
        보정[자리] = pb
    m = len(잰자리) or 1
    for w, pb in zip(것들, 보정):
        w.p보정 = pb
        if pb is None:
            w.판정 = "못잼"
        elif min(1.0, m * w.최소p) >= alpha:
            w.판정 = "못잼"
        else:
            w.판정 = "약함" if pb < alpha else "평범"
    것들.sort(key=lambda w: ({"약함": 0, "평범": 1, "못잼": 2}[w.판정],
                            -w.틀린,
                            w.p보정 if w.p보정 is not None else 1.0))
    return 것들


def 태그별(n: NT.공책) -> dict:
    """태그 -> (푼 수, 틀린 수, 틀린 문제 id). **안 정해진 시도는 안 센다.**

    각 문제의 **마지막 시도**만 센다 -- 같은 문제를 열 번 틀리면 그 태그가 열 배
    나빠 보이는데, 그것은 문제가 열 개인 것과 다르다.
    """
    out: dict = {}
    본문제 = {}
    for a in n.시도:
        if a.맞았나 is None:
            continue
        본문제[a.문제id] = a
    for qid, a in 본문제.items():
        q = n.문제.get(qid)
        if not q:
            continue
        for t in (q.태그 or ["(태그없음)"]):
            칸 = out.setdefault(t, [0, 0, []])
            칸[0] += 1
            if a.맞았나 is False:
                칸[1] += 1
                칸[2].append(qid)
    return out


def 전체기저(n: NT.공책) -> tuple:
    """(푼 수, 틀린 수, 오답률). **문제 하나를 한 번만 센다.**"""
    본문제 = {}
    for a in n.시도:
        if a.맞았나 is not None:
            본문제[a.문제id] = a
    전 = len(본문제)
    틀 = sum(1 for a in 본문제.values() if a.맞았나 is False)
    return 전, 틀, (틀 / 전 if 전 else 0.0)


def 취약점(n: NT.공책, alpha: float = ALPHA) -> list:
    """태그마다 판정. **Holm 으로 조이고, 못 잴 수 있음을 먼저 본다.**"""
    전, _, p0 = 전체기저(n)
    표 = 태그별(n)
    if not 표 or 전 < MIN_N:
        return [약점(태그=t, n=v[0], 틀린=v[1], 기저=p0,
                    오답률=(v[1] / v[0] if v[0] else 0.0),
                    문제들=v[2], 판정="못잼", 최소p=1.0)
                for t, v in sorted(표.items())]

    것들, ps = [], []
    for t, (개, 틀, ids) in sorted(표.items()):
        # **라플라스로 살짝 민다.** p0 가 0 이면 한 번만 틀려도 p=0 이 되어 무엇이든
        # 약점이 되고, p0 가 1 이면 아무것도 약점이 안 된다. 둘 다 자가 아니다.
        기 = min(max((전 * p0 + 1) / (전 + 2), 1e-6), 1 - 1e-6)
        p = 이항꼬리(틀, 개, 기) if 개 >= MIN_N else None
        것들.append(약점(태그=t, n=개, 틀린=틀, 기저=p0,
                       오답률=(틀 / 개 if 개 else 0.0), 문제들=ids,
                       p=p, 최소p=도달가능최소p(개, 기), 쓴기저=기))
        ps.append(p)

    # **Holm 에는 실제로 잰 것만 넣는다.** 처음에 None 까지 통째로 넘겼더니
    # `holm` 이 `m = len(ps)` 로 세어, 잰 것이 하나뿐인데도 문턱을 넷으로 조였다
    # (실측: p=0.140 이 0.560 으로 부풀어 약점이 사라졌다). 안 잰 태그는 견준
    # 것이 아니므로 셈에 들어가면 안 된다.
    잰자리 = [i for i, x in enumerate(ps) if x is not None]
    보정목록 = IF.holm([ps[i] for i in 잰자리])
    보정 = [None] * len(ps)
    for 자리, pb in zip(잰자리, 보정목록):
        보정[자리] = pb
    m = len(잰자리) or 1
    for w, pb in zip(것들, 보정):
        w.p보정 = pb
        if w.n < MIN_N or pb is None:
            w.판정 = "못잼"
        elif min(1.0, m * w.최소p) >= alpha:
            # 다 틀려도 못 가르는 자리. **'평범' 이라 하면 거짓말이다**
            w.판정 = "못잼"
        else:
            w.판정 = "약함" if pb < alpha else "평범"
    # 약한 것 먼저, 그 다음 p 작은 순
    것들.sort(key=lambda w: ({"약함": 0, "평범": 1, "못잼": 2}[w.판정],
                            w.p보정 if w.p보정 is not None else 1.0))
    return 것들


def 몇개더(w: 약점, p0: float = 0.0, alpha: float = ALPHA, m: int = 1,
          상한: int = 200) -> int:
    """**이 태그를 가르려면 몇 문제가 더 있어야 하나.** 0 이면 이미 가릴 수 있다.

    '못잼' 만 말하고 끝내면 학생은 무엇을 해야 할지 모른다. 그 판정에 늘 붙어야 하는
    말이 이것이다 -- `brief` 가 안 하던 것이고, 여기서는 학생이 다음에 무엇을 할지가
    답의 절반이라 넣는다.
    """
    # **판정이 쓴 자를 그대로 쓴다.** 처음에 여기만 날 p0(0.333)를 쓰고 판정은
    # 라플라스로 민 것(0.364)을 써서, 같은 태그에 "이미 갈릴 수 있다" 와 `못잼` 이
    # 나란히 찍혔다(실측). 화면이 스스로와 어긋나면 읽는 쪽은 어느 쪽도 못 믿는다.
    기 = min(max(w.쓴기저 or p0, 1e-6), 1 - 1e-6)
    for n2 in range(max(w.n, 1), 상한 + 1):
        # **MIN_N 도 같이 본다.** 이것을 빼먹어서 n=3 인 태그에 "이미 갈릴 수 있다"
        # 고 말해 놓고 판정은 `못잼` 을 냈다(실측). 화면이 스스로와 어긋나면 읽는
        # 쪽은 어느 쪽을 믿을지 모른다.
        if n2 >= MIN_N and min(1.0, m * 도달가능최소p(n2, 기)) < alpha:
            return max(0, n2 - w.n)
    return -1                                        # 상한까지 봐도 못 가른다
