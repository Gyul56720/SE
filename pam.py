"""**PAM4 원단** -- 4레벨·그레이·3문턱, 그리고 심볼오류와 비트오류를 **따로** 센다.

## 왜 NRZ 로는 부족한가

112G/224G 는 **PAM4** 다. 그리고 이 저장소가 쓰는 손상 -- `압축하기`(tanh) -- 은
NRZ 와 PAM4 에 **전혀 다르게** 작용한다.

    NRZ    판정은 부호 하나다. tanh 는 단조증가라 **부호를 안 바꾼다.**
           압축은 잡음 여유를 깎을 뿐 판정 자체를 뒤집지 않는다.
    PAM4   판정은 세 문턱이다. tanh 는 **바깥 레벨을 안쪽으로 끌어당긴다** --
           ±3/3 이 ±1/3 쪽으로 눌리면서 **바깥 눈이 먼저 닫힌다.**

그러니 "메모리 없는 역변환이 값어치가 있나" 라는 질문은 PAM4 에서 물어야 뜻이 있다.
NRZ 에서 그것을 물으면 손상이 원래 판정에 무해한 자리에서 물은 것이다.

## 정규화 -- 바깥 레벨을 ±1 로 둔다

    레벨 = (-3, -1, +1, +3)/3

NRZ 의 ±1 과 **꼭대기 진폭이 같다.** 그러면 최소거리가 2 에서 2/3 으로 줄고

    페널티 = 20·log10(3) = 9.54 dB

가 그대로 나온다. 같은 채널·같은 잡음에서 두 변조를 견줄 때 이 정규화라야
"PAM4 가 9.54 dB 손해" 라는 교과서 값과 맞물린다(`검증()` 이 그것을 잰다).

## 그레이 -- 이웃 레벨은 한 비트만 다르다

    레벨색인  0     1     2     3
    레벨    -1  -1/3  +1/3    +1
    비트    00    01    11    10

잡음이 만드는 오류는 거의 다 **이웃 레벨로 가는 것**이므로, 그레이면 심볼오류
하나가 비트오류 하나다. 그래서 대략 `BER ~ SER/2`(심볼당 2비트) 이고, 이것이
성립하는지 자체가 검사 거리다 -- **성립하지 않으면 오류가 이웃이 아니라는 뜻**이고
그것은 대개 바닥이나 오류 번짐이 있다는 신호다.

## 심볼오류를 **따로** 세는 까닭 -- RS FEC 가 심볼로 센다

KP4 는 `RS(544,514)` 이고 GF(2^10) 위에서 돈다. 정정 능력은 **심볼 15개**다.
그러니 규격 판정에 필요한 것은 비트오류율이 아니라 **코드워드당 심볼오류 분포**다
(`fec.py`). 비트오류가 몇 개인지가 아니라 **몇 심볼에 뭉쳐 있는지**가 판정을
가른다 -- DFE 오류 번짐은 비트오류 수는 그대로 두면서 그것을 한 심볼에 뭉치므로
FEC 에 **유리하게** 작용하기도 한다. 그 방향까지 재려면 심볼을 세야 한다.
"""
from __future__ import annotations

import numpy as np

# 그레이: 레벨색인 -> 비트쌍(MSB, LSB). 이웃 색인끼리 한 비트만 다르다.
_그레이 = np.array([[0, 0], [0, 1], [1, 1], [1, 0]], dtype=np.int8)
_그레이역 = {(0, 0): 0, (0, 1): 1, (1, 1): 2, (1, 0): 3}


def 레벨들(M: int = 4) -> np.ndarray:
    """`M`-PAM 의 정규화 레벨. 바깥을 ±1 로 둔다."""
    M = int(M)
    if M == 2:
        return np.array([-1.0, 1.0])
    k = np.arange(M)
    v = 2.0 * k - (M - 1)                       # -3,-1,1,3
    return v / float(M - 1)


def 최소거리(M: int = 4) -> float:
    """이웃 레벨 사이 거리. NRZ 는 2, PAM4 는 2/3."""
    L = 레벨들(M)
    return float(L[1] - L[0])


def 페널티dB(M: int = 4) -> float:
    """같은 꼭대기 진폭에서 NRZ 대비 잃는 dB. PAM4 는 9.54 dB."""
    return float(20.0 * np.log10(최소거리(2) / 최소거리(M)))


def 비트수(M: int = 4) -> int:
    return int(np.log2(int(M)))


def 심볼만들기(rng, 심볼수: int, M: int = 4):
    """무작위 비트 -> 그레이 -> 레벨. `(레벨열, 비트열, 색인열)` 을 돌려준다.

    비트열은 심볼당 `log2(M)` 개가 **차례로** 늘어선 1차원이다 -- FEC 가 그 순서로
    심볼을 자르므로 순서를 바꾸면 안 된다.
    """
    M = int(M)
    심볼수 = int(심볼수)
    if M == 2:
        비트 = rng.integers(0, 2, 심볼수).astype(np.int8)
        색인 = 비트.astype(np.int64)
        return (비트 * 2 - 1).astype(float), 비트, 색인
    색인 = rng.integers(0, M, 심볼수).astype(np.int64)
    비트 = _그레이[색인].reshape(-1).astype(np.int8)
    return 레벨들(M)[색인], 비트, 색인


def 색인으로(레벨열: np.ndarray, M: int = 4) -> np.ndarray:
    """레벨값 -> 가장 가까운 레벨색인."""
    L = 레벨들(M)
    return np.argmin(np.abs(np.asarray(레벨열, dtype=float)[:, None] - L[None, :]), axis=1)


def 비트로(색인열: np.ndarray, M: int = 4) -> np.ndarray:
    """레벨색인 -> 그레이 비트열(1차원, 심볼당 log2(M) 개)."""
    색인열 = np.asarray(색인열, dtype=np.int64)
    if int(M) == 2:
        return 색인열.astype(np.int8)
    return _그레이[색인열].reshape(-1).astype(np.int8)


def 슬라이스(x: np.ndarray, M: int = 4) -> np.ndarray:
    """**문턱 판정.** 가장 가까운 레벨로 보낸다. NRZ 면 부호와 똑같다."""
    L = 레벨들(M)
    x = np.asarray(x, dtype=float)
    if int(M) == 2:
        return np.where(x >= 0, 1.0, -1.0)
    # 문턱은 이웃 레벨의 한가운데다. searchsorted 가 한 줄로 한다.
    문턱 = (L[:-1] + L[1:]) / 2.0
    return L[np.searchsorted(문턱, x)]


def 오류세기(판정레벨: np.ndarray, 정답레벨: np.ndarray, M: int = 4) -> dict:
    """심볼오류와 비트오류를 **따로** 센다. 그리고 비트오류 **자리**를 남긴다.

    자리를 남기는 까닭은 `fec.py` 가 그것을 10비트 심볼로 잘라 코드워드당 분포를
    내기 때문이다. 개수만 남기면 **뭉쳐 있는지 흩어져 있는지**를 잃는다.
    """
    M = int(M)
    ㅍ = 색인으로(판정레벨, M)
    ㅈ = 색인으로(정답레벨, M)
    심볼오류 = ㅍ != ㅈ
    ㅍb, ㅈb = 비트로(ㅍ, M), 비트로(ㅈ, M)
    비트오류 = ㅍb != ㅈb
    # 이웃으로 간 오류만 세면 그레이가 먹었는지 알 수 있다
    이웃 = int(np.sum(np.abs(ㅍ - ㅈ) == 1))
    난것 = int(심볼오류.sum())
    return {"심볼수": int(len(ㅈ)), "심볼오류": 난것,
            "SER": (난것 / len(ㅈ)) if len(ㅈ) else float("nan"),
            "비트수": int(len(ㅈb)), "비트오류": int(비트오류.sum()),
            "BER": (float(비트오류.sum()) / len(ㅈb)) if len(ㅈb) else float("nan"),
            "이웃오류": 이웃,
            "이웃비율": (이웃 / 난것) if 난것 else float("nan"),
            "비트오류자리": np.flatnonzero(비트오류).astype(np.int64),
            "심볼오류자리": np.flatnonzero(심볼오류).astype(np.int64), "M": M}


def 검증() -> dict:
    """**이 원단이 스스로 맞나** -- 교과서 값 셋으로 친다.

    (가) 페널티가 9.54 dB 인가            (나) 그레이가 이웃 한 비트인가
    (다) 잡음만 있을 때 SER 이 닫힌 꼴과 맞나
    """
    from math import erfc, sqrt
    난 = {}
    난["페널티dB"] = 페널티dB(4)
    이웃한비트 = all(int(np.sum(_그레이[i] != _그레이[i + 1])) == 1 for i in range(3))
    난["그레이_이웃한비트"] = bool(이웃한비트)
    # 잡음만: SER = 2(1-1/M)·Q(d/2sigma)
    rng = np.random.default_rng(7)
    # **오류가 열 개쯤 나는 자리에서 재면 안 된다** -- 처음에 sigma=0.08 로 쟀더니
    # 400,000 심볼에 오류가 9개였고, 그 9개로 "닫힌 꼴의 0.97배" 라고 말할 뻔했다.
    # 오류 700개쯤 나는 자리를 고른다(상대오차 ~4%).
    M, sigma, N = 4, 0.11, 400000
    레벨, _, _ = 심볼만들기(rng, N, M)
    받은 = 레벨 + rng.normal(0, sigma, N)
    r = 오류세기(슬라이스(받은, M), 레벨, M)
    d = 최소거리(M)
    예측 = 2.0 * (1.0 - 1.0 / M) * 0.5 * erfc((d / 2.0) / (sigma * sqrt(2.0)))
    난["SER실측"] = r["SER"]
    난["SER예측"] = float(예측)
    난["SER비"] = r["SER"] / 예측 if 예측 else float("nan")
    난["오류수"] = r["심볼오류"]
    난["이웃비율"] = r["이웃비율"]
    난["BER_over_SER"] = r["BER"] / r["SER"] if r["SER"] else float("nan")
    return 난
