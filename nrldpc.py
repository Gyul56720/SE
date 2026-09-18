"""**5G NR LDPC 복호기의 부동소수 골든.** 계층 정규화 min-sum.

`spec/IP_5G_LDPC복호기.md` 의 골든 단계. 고정소수 골든(`nrldpcfix.py`)과 RTL 이
이것을 기준으로 선다.

## 이 판에서 거짓 초록이 나는 자리 다섯 -- 처음부터 막고 짓는다

    1. 수렴 안 했는데 마지막 반복의 판정만 보기
       -> `복호()` 가 `수렴` 과 `쓴반복` 을 **반드시** 같이 낸다
    2. 영부호어(all-zero)로만 BLER 을 재기
       -> 대칭성이 깨지는 버그를 통째로 숨긴다. `tests/` 가 **무작위 부호어와 같은지**를 본다
    3. 패리티검사를 안 보고 반복을 다 쓰기
       -> 조기종료가 실제로 무는지 안 보면 "반복 20회" 가 아무 뜻이 없다
    4. 오류 0 을 BLER 0 이라 부르기
       -> `측정()` 이 오류 0 이면 **상한만** 말한다
    5. 정규화 계수 α 를 BLER 로 고르고 **같은 블록에서** BLER 을 재기
       -> 고르는 블록과 재는 블록을 가른다

## 범위 -- v1 이 하지 않는 것

  · 율 정합(rate matching, 38.212 5.4.2) · 부호블록 분할 -- **다른 블록이다**
  · v1 은 모부호(mother code)에 대고 돈다. 첫 두 기저열(2Z 비트)은 표준대로 펑처
"""
from __future__ import annotations

import csv
import math
import pathlib

import numpy as np

뿌리 = pathlib.Path(__file__).resolve().parent
표자리 = 뿌리 / "codes"

# 38.212 Table 5.3.2-1. 51 개 -- 8+8+7+6+6+6+5+5
리프팅집합 = (
    (2, 4, 8, 16, 32, 64, 128, 256),
    (3, 6, 12, 24, 48, 96, 192, 384),
    (5, 10, 20, 40, 80, 160, 320),
    (7, 14, 28, 56, 112, 224),
    (9, 18, 36, 72, 144, 288),
    (11, 22, 44, 88, 176, 352),
    (13, 26, 52, 104, 208),
    (15, 30, 60, 120, 240),
)
Kb = {"BG1": 22, "BG2": 10}
펑처기저열 = 2          # 첫 2Z 정보비트는 전송하지 않는다 (38.212)


def 집합색인(Z: int) -> int:
    for i, s in enumerate(리프팅집합):
        if Z in s:
            return i
    raise ValueError(f"표준에 없는 리프팅 크기: {Z}")


def 기저행렬(bg: str = "BG1", 파일=None) -> "dict[tuple[int,int], tuple[int,...]]":
    """`{(행, 열): (집합0..7 의 이동량)}`. 행 번호는 빈칸이면 위에서 이어받는다."""
    p = pathlib.Path(파일) if 파일 else 표자리 / f"nr_{bg.lower()}.csv"
    표: "dict[tuple[int,int], tuple[int,...]]" = {}
    현재행 = None
    for 줄 in csv.reader(open(p, encoding="utf-8"), delimiter=";"):
        f = [x.strip() for x in 줄]
        if len(f) < 3 or not f[2].lstrip("-").isdigit():
            continue
        if f[0]:
            현재행 = int(f[0])
        if 현재행 is None or not f[1]:
            continue
        표[(현재행, int(f[1]))] = tuple(int(x) for x in f[2:10])
    return 표


class 부호:
    """(기저행렬, 리프팅 Z) 한 벌. 층마다 (열, 이동량) 목록을 들고 있다."""

    def __init__(self, bg: str = "BG1", Z: int = 32):
        self.bg, self.Z = bg, int(Z)
        self.iLS = 집합색인(self.Z)
        표 = 기저행렬(bg)
        self.행수 = max(r for r, _ in 표) + 1
        self.열수 = max(c for _, c in 표) + 1
        self.층: "list[tuple[np.ndarray, np.ndarray]]" = []
        for m in range(self.행수):
            항 = sorted((c, 표[(m, c)][self.iLS] % self.Z) for (r, c) in 표 if r == m)
            self.층.append((np.array([c for c, _ in 항]), np.array([s for _, s in 항])))
        self.Kb = Kb[bg]
        self.K = self.Kb * self.Z                       # 정보 비트
        self.N = (self.열수 - 펑처기저열) * self.Z      # 전송되는 비트

    @property
    def 부호율(self) -> float:
        return self.K / self.N

    def 신드롬0(self, c: np.ndarray) -> bool:
        """`c` 는 (열수, Z) 이진 배열. 모든 검사식이 0 인가."""
        for js, ss in self.층:
            acc = np.zeros(self.Z, dtype=np.int8)
            for j, s in zip(js, ss):
                acc ^= np.roll(c[j], -int(s))
            if acc.any():
                return False
        return True


def 복호(부: 부호, llr: np.ndarray, 최대반복: int = 20, 알파: float = 0.75,
       조기종료: bool = True) -> dict:
    """**계층 정규화 min-sum.** 층 m 은 층 m-1 이 갱신한 L 을 받아 쓴다.

    낸 것에 `수렴` 과 `쓴반복` 이 **반드시** 들어간다 -- 수렴 안 한 판정을
    조용히 쓰는 것이 이 판의 제일 조용한 거짓 초록이다.
    """
    Z = 부.Z
    L = llr.astype(np.float64).copy()                   # (열수, Z)
    R = [np.zeros((len(js), Z)) for js, _ in 부.층]
    for it in range(1, int(최대반복) + 1):
        for m, (js, ss) in enumerate(부.층):
            Q = np.stack([np.roll(L[j], -int(s)) for j, s in zip(js, ss)])
            Q -= R[m]
            a = np.abs(Q)
            순 = np.argsort(a, axis=0)
            최소1 = np.take_along_axis(a, 순[0:1], axis=0)
            최소2 = np.take_along_axis(a, 순[1:2], axis=0) if len(js) > 1 else 최소1
            부호곱 = np.prod(np.where(Q >= 0, 1.0, -1.0), axis=0)
            크기 = np.where(np.arange(len(js))[:, None] == 순[0:1], 최소2, 최소1)
            새R = 알파 * (부호곱[None, :] * np.where(Q >= 0, 1.0, -1.0)) * 크기
            R[m] = 새R
            갱신 = Q + 새R
            for i, (j, s) in enumerate(zip(js, ss)):
                L[j] = np.roll(갱신[i], int(s))
        c = (L < 0).astype(np.int8)
        if 조기종료 and 부.신드롬0(c):
            return {"비트": c, "수렴": True, "쓴반복": it}
    return {"비트": (L < 0).astype(np.int8), "수렴": 부.신드롬0((L < 0).astype(np.int8)),
            "쓴반복": int(최대반복)}


def 채널llr(전송비트: np.ndarray, snr_dB: float, rng, 부: 부호) -> np.ndarray:
    """BPSK + AWGN. `전송비트` 는 (열수, Z) 이고 앞 `펑처기저열` 은 안 보낸다(LLR 0)."""
    sigma = 10 ** (-float(snr_dB) / 20)
    x = 1.0 - 2.0 * 전송비트.astype(np.float64)          # 0->+1, 1->-1
    y = x + sigma * rng.standard_normal(x.shape)
    llr = 2.0 * y / (sigma ** 2)
    llr[:펑처기저열] = 0.0                               # 펑처된 자리는 정보가 없다
    return llr


def 측정(부: 부호, snr_dB: float, 블록수: int = 200, 씨: int = 0,
       최대반복: int = 20, 알파: float = 0.75, 부호어=None) -> dict:
    """BLER/BER. **오류가 0 이면 BLER 을 0 이라 부르지 않고 상한만 말한다.**"""
    rng = np.random.default_rng(씨)
    블록오류 = 비트오류 = 비트수 = 0
    반복합 = 미수렴 = 0
    for b in range(int(블록수)):
        c = (np.zeros((부.열수, 부.Z), dtype=np.int8) if 부호어 is None
             else 부호어(rng))
        llr = 채널llr(c, snr_dB, rng, 부)
        r = 복호(부, llr, 최대반복, 알파)
        반복합 += r["쓴반복"]
        미수렴 += int(not r["수렴"])
        틀린 = int((r["비트"][:부.Kb] != c[:부.Kb]).sum())
        비트오류 += 틀린
        비트수 += 부.K
        블록오류 += int(틀린 > 0)
    상한 = 블록오류 == 0
    return {
        "snr_dB": float(snr_dB), "블록수": int(블록수),
        "블록오류": 블록오류, "비트오류": 비트오류,
        "BLER": 블록오류 / 블록수, "BER": 비트오류 / max(비트수, 1),
        "평균반복": 반복합 / 블록수, "미수렴": 미수렴,
        "상한만": 상한,
        "말": (f"오류 0 -- BLER < {3.0/블록수:.2e} (95% 상한) 라고만 말할 수 있다"
              if 상한 else f"BLER = {블록오류}/{블록수}"),
    }


# ---------------------------------------------------------------- 부호화
# **영부호어만으로 BLER 을 재면 대칭성이 깨지는 버그가 통째로 숨는다.**
# 여기는 그것을 잡기 위한 자리다 -- 빠른 길(영부호어)이 옳은지 재 보는 데 쓴다.
# 5G 의 전용 부호화 절차를 쓰지 않고 **일반 GF(2) 풀이**로 둔다: 전용 절차가
# 기저행렬 구조를 가정하므로, 그 가정이 틀리면 부호화기와 복호기가 **같이** 틀려
# 서로를 못 잡는다. 일반 풀이는 신드롬만 보므로 독립적이다.

_H칸 = {}


def 이진H(부: 부호) -> np.ndarray:
    """`(행수*Z, 열수*Z)` 이진 행렬. 신드롬 정의와 같은 자리에 1 을 둔다."""
    키 = (부.bg, 부.Z)
    if 키 in _H칸:
        return _H칸[키]
    Z = 부.Z
    H = np.zeros((부.행수 * Z, 부.열수 * Z), dtype=np.uint8)
    for m, (js, ss) in enumerate(부.층):
        for j, s in zip(js, ss):
            for z in range(Z):
                H[m * Z + z, int(j) * Z + (z + int(s)) % Z] = 1
    _H칸[키] = H
    return H


def _gf2역(A: np.ndarray) -> "np.ndarray | None":
    n = A.shape[0]
    M = np.concatenate([A.copy() % 2, np.eye(n, dtype=np.uint8)], axis=1)
    행 = 0
    for 열 in range(n):
        칸 = np.nonzero(M[행:, 열])[0]
        if len(칸) == 0:
            return None
        p = 행 + 칸[0]
        if p != 행:
            M[[행, p]] = M[[p, 행]]
        치환 = np.nonzero(M[:, 열])[0]
        치환 = 치환[치환 != 행]
        M[치환] ^= M[행]
        행 += 1
    return M[:, n:]


_역칸 = {}


def 부호화(부: 부호, 정보: np.ndarray) -> np.ndarray:
    """`정보` (Kb, Z) -> 부호어 (열수, Z). 패리티를 GF(2) 로 푼다."""
    Z, 키 = 부.Z, (부.bg, 부.Z)
    H = 이진H(부)
    분기 = 부.Kb * Z
    if 키 not in _역칸:
        inv = _gf2역(H[:, 분기:])
        if inv is None:
            raise RuntimeError(f"{키}: 패리티 부분이 역행렬이 없다")
        _역칸[키] = inv
    s = 정보.astype(np.uint8).reshape(-1) % 2
    b = (H[:, :분기] @ s) % 2
    p = (_역칸[키] @ b) % 2
    c = np.concatenate([s, p]).astype(np.int8).reshape(부.열수, Z)
    return c


def 무작위부호어(부: 부호):
    """`측정(..., 부호어=...)` 에 넣는 공장."""
    def 만들기(rng):
        return 부호화(부, rng.integers(0, 2, size=(부.Kb, 부.Z)))
    return 만들기
