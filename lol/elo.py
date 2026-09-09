"""**승률은 판단이 아니라 계산이다.** LLM 호출 0회.

`law/issue.py` 가 쟁점을 뽑지 않고 도출하는 것과 같은 자리다. 모델에게 "누가 이길
것 같냐" 고 묻지 않는다 -- 원장에 적힌 경기를 시간순으로 걸으며 레이팅을 갱신하고,
그 레이팅으로 다음 경기를 계산한다.

    E_A = 1 / (1 + 10^((R_B - R_A) / 400))

## 예측이 갱신보다 **먼저**다

이 파일에서 틀리기 제일 쉬운 자리다. 경기를 걸으며 레이팅을 갱신할 때, **그 경기로
갱신한 뒤에** 그 경기를 예측하면 답을 보고 찍는 것이다(look-ahead). 그러면 백테스트
점수가 아름답게 나오고 실전에서 무너진다 -- 이 저장소가 부르는 이름으로는
**검사하지 않은 초록불**이다. `walk()` 는 예측을 먼저 적고 나서 갱신한다.

## 진영 이점은 **선언하지 않고 잰다**

블루/레드 승률 차이를 "보통 52% 쯤" 이라고 적어 두면 그 숫자는 패치마다 낡는다.
`side_bias()` 가 원장에서 직접 센다. 잰 값이 없으면(경기가 너무 적으면) **0 이다** --
모르는 것을 그럴듯한 값으로 채우지 않는다.
"""
from __future__ import annotations

import math

BASE = 1500.0
K = 24.0          # 한 경기가 레이팅을 얼마나 움직이나. LCK 정규시즌 한 시즌이 45경기쯤
MIN_FOR_BIAS = 50  # 진영 이점을 재려면 최소 이만큼은 있어야 한다


def expect(ra: float, rb: float) -> float:
    """A 가 이길 확률. 400점 차이 = 10배."""
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


def to_elo(p: float) -> float:
    """확률 p 를 만드는 레이팅 차이. `expect` 의 역함수다.

    진영 이점을 '승률' 로 재서 '레이팅 점수' 로 바꿔 넣을 때 쓴다 -- 두 자리에서
    서로 다른 단위를 쓰면 어긋난다."""
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -400.0 * math.log10(1.0 / p - 1.0)


def side_bias(games) -> float:
    """블루 진영 이점을 **레이팅 점수로** 돌려준다. 잴 것이 모자라면 0.0.

    선언이 아니라 측정이다. 원장이 바뀌면 이 값도 바뀐다."""
    n = len(games)
    if n < MIN_FOR_BIAS:
        return 0.0
    wins = sum(1 for g in games if g.blue_won)
    return to_elo(wins / n)


def walk(games, k: float = K, base: float = BASE, bias: float | None = None) -> tuple:
    """경기를 시간순으로 걸으며 **예측을 먼저 적고** 레이팅을 갱신한다.

    돌려주는 것은 (레이팅, 걸음, 진영이점). 걸음 하나가 곧 백테스트 한 줄이다 --
    `score.py` 가 이것만 있으면 채점할 수 있다. 채점기가 자기 예측을 다시 만들면
    두 벌이 갈라지므로, **예측은 여기 한 자리에서만 만든다.**
    """
    bias = side_bias(games) if bias is None else bias
    r, played = {}, {}
    rows = []
    for g in games:
        ra = r.get(g.blue, base)
        rb = r.get(g.red, base)
        p = expect(ra + bias, rb)                     # ← 갱신 전. 이 순서가 요점이다
        y = 1.0 if g.blue_won else 0.0
        rows.append({
            "date": g.date, "blue": g.blue, "red": g.red,
            "p_blue": p, "blue_won": g.blue_won,
            # 이 경기 **전에** 두 팀이 각각 몇 경기 했나. 백테스트에서 초반
            # 몸풀기 구간을 빼는 데 쓴다 -- 전부 1500 에서 시작하므로 첫 경기들의
            # 예측은 사실상 동전던지기이고, 그것까지 점수에 넣으면 자를 흐린다.
            "n_blue": played.get(g.blue, 0), "n_red": played.get(g.red, 0),
        })
        r[g.blue] = ra + k * (y - p)
        r[g.red] = rb + k * ((1 - y) - (1 - p))
        played[g.blue] = played.get(g.blue, 0) + 1
        played[g.red] = played.get(g.red, 0) + 1
    return r, rows, bias


def series(p: float, best_of: int) -> float:
    """한 세트 승률 p 일 때 **다전제**를 이길 확률.

    Bo{n} 은 (n+1)/2 판을 먼저 이기는 것이다. 세트가 서로 **독립**이라고 보고 센다 --
    실제로는 밴픽이 이어지고 기세가 있으니 독립이 아니다. 그 한계를 여기 적어 두고,
    `predict.py` 가 화면에도 적는다. 모르는 것을 아는 척하지 않는 자리다.
    """
    if best_of <= 1:
        return p
    need = best_of // 2 + 1
    total = 0.0
    for lose in range(need):                       # 상대가 lose 판 이기는 동안
        games = need + lose
        c = math.comb(games - 1, lose)             # 마지막 판은 반드시 우리가 이긴다
        total += c * (p ** need) * ((1 - p) ** lose)
    return total
