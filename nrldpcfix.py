"""**5G NR LDPC 복호기의 고정소수점 골든.** RTL 이 이것과 비트까지 같아야 한다.

`nrldpc.py`(부동소수) 가 위, 이것이 아래, RTL 이 그 아래다.

## DFE 에서 얻은 규칙이 여기서 **뒤집힌다** -- 그대로 옮기면 틀린다

`specdfe.py` 에서 이렇게 적었다: *누산기는 감싸기(wrap)로 두라, 포화를 쓰지 마라.*
거기서는 **직접형과 투기형 두 구조가 비트까지 같아야** 했고, 감싸기는 mod 2^W 환이라
합산 순서에 무관하지만 포화는 결합법칙을 안 지켜 둘을 갈랐다.

**여기는 구조가 하나다.** 맞대야 할 다른 형태가 없다. 대신 값 자체가 뜻을 갖는다 --
LLR 이다. 감싸면 **큰 확신이 반대 부호의 큰 확신으로 뒤집힌다.** 복호기가 죽는다.
그러므로 여기서는 **반드시 포화한다.**

    DFE      두 구조의 비트일치가 목표  ->  감싸기 (순서 무관)
    LDPC     BLER 이 목표              ->  포화   (부호 뒤집힘 금지)

`tests/test_nrldpcfix.py` 가 **감싸기로 두면 실제로 망가지는지**까지 잰다.
안 망가지면 이 규칙은 빈 규칙이다.

## 손잡이

    W       LLR 워드폭 (부호 포함)      4 | 5 | 6 | 8
    스케일   부동 LLR -> 정수 눈금       클리핑과 해상도의 맞바꿈. **재서 고른다**
    알파     정규화 계수 (분자/2^분모)   3/4 · 7/8 · 1/2 -- 전부 시프트-덧셈
"""
from __future__ import annotations

import numpy as np

import nrldpc as F


def 포화(v: np.ndarray, W: int) -> np.ndarray:
    lo, hi = -(1 << (W - 1)) + 1, (1 << (W - 1)) - 1   # 대칭 범위 (-2^(W-1) 은 안 쓴다)
    return np.clip(v, lo, hi)


def 감싸기(v: np.ndarray, W: int) -> np.ndarray:
    m = 1 << W
    v = np.mod(v, m)
    return np.where(v >= (m >> 1), v - m, v)


def 양자화(llr: np.ndarray, W: int, 스케일: float) -> np.ndarray:
    return 포화(np.round(llr * float(스케일)).astype(np.int64), W)


def 정규화(v: np.ndarray, 분자: int, 분모비트: int) -> np.ndarray:
    """`alpha = 분자 / 2^분모비트`. 하드웨어는 시프트-덧셈으로 한다 -- 0 쪽으로 버린다."""
    s = np.sign(v)
    return s * ((np.abs(v) * int(분자)) >> int(분모비트))


def 복호(부: F.부호, llr정수: np.ndarray, W: int = 6, 최대반복: int = 20,
       분자: int = 3, 분모비트: int = 2, 조기종료: bool = True,
       넘침="포화") -> dict:
    """계층 정규화 min-sum, 정수만. `넘침` 은 '포화' 또는 '감싸기'."""
    한계 = 포화 if 넘침 == "포화" else 감싸기
    Z = 부.Z
    L = 한계(llr정수.astype(np.int64).copy(), W)
    R = [np.zeros((len(js), Z), dtype=np.int64) for js, _ in 부.층]
    for it in range(1, int(최대반복) + 1):
        for m, (js, ss) in enumerate(부.층):
            Q = np.stack([np.roll(L[j], -int(s)) for j, s in zip(js, ss)])
            Q = 한계(Q - R[m], W)
            a = np.abs(Q)
            순 = np.argsort(a, axis=0)
            최소1 = np.take_along_axis(a, 순[0:1], axis=0)
            최소2 = np.take_along_axis(a, 순[1:2], axis=0) if len(js) > 1 else 최소1
            부호 = np.where(Q >= 0, 1, -1)
            부호곱 = np.prod(부호, axis=0)
            크기 = np.where(np.arange(len(js))[:, None] == 순[0:1], 최소2, 최소1)
            새R = 한계(정규화(부호곱[None, :] * 부호 * 크기, 분자, 분모비트), W)
            R[m] = 새R
            갱신 = 한계(Q + 새R, W)
            for i, (j, s) in enumerate(zip(js, ss)):
                L[j] = np.roll(갱신[i], int(s))
        c = (L < 0).astype(np.int8)
        if 조기종료 and 부.신드롬0(c):
            return {"비트": c, "수렴": True, "쓴반복": it}
    c = (L < 0).astype(np.int8)
    return {"비트": c, "수렴": 부.신드롬0(c), "쓴반복": int(최대반복)}


def 측정(부: F.부호, snr_dB: float, W: int = 6, 스케일: float = 1.0,
       블록수: int = 200, 씨: int = 0, 최대반복: int = 20,
       분자: int = 3, 분모비트: int = 2, 넘침="포화", 부호어=None) -> dict:
    """`nrldpc.측정` 과 같은 계약. **오류 0 이면 상한만 말한다.**"""
    rng = np.random.default_rng(씨)
    블록오류 = 비트오류 = 비트수 = 반복합 = 미수렴 = 0
    포화친횟수 = 0
    for _ in range(int(블록수)):
        c = (np.zeros((부.열수, 부.Z), dtype=np.int8) if 부호어 is None
             else 부호어(rng))
        llr = F.채널llr(c, snr_dB, rng, 부)
        q = 양자화(llr, W, 스케일)
        포화친횟수 += int((np.abs(q) == (1 << (W - 1)) - 1).sum())
        r = 복호(부, q, W, 최대반복, 분자, 분모비트, 넘침=넘침)
        반복합 += r["쓴반복"]
        미수렴 += int(not r["수렴"])
        틀린 = int((r["비트"][:부.Kb] != c[:부.Kb]).sum())
        비트오류 += 틀린
        비트수 += 부.K
        블록오류 += int(틀린 > 0)
    상한 = 블록오류 == 0
    총입력 = 블록수 * (부.열수 - F.펑처기저열) * 부.Z
    return {
        "snr_dB": float(snr_dB), "W": int(W), "스케일": float(스케일),
        "블록수": int(블록수), "블록오류": 블록오류, "비트오류": 비트오류,
        "BLER": 블록오류 / 블록수, "BER": 비트오류 / max(비트수, 1),
        "평균반복": 반복합 / 블록수, "미수렴": 미수렴,
        "입력포화율": 포화친횟수 / max(총입력, 1),
        "넘침": 넘침, "상한만": 상한,
        "말": (f"오류 0 -- BLER < {3.0/블록수:.2e} (95% 상한)" if 상한
              else f"BLER = {블록오류}/{블록수}"),
    }
