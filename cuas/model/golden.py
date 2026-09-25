# -*- coding: utf-8 -*-
"""합성 드론 도플러 -> STFT 스펙트로그램의 **황금값**. RTL 이 이걸 못 이긴다.

날개 마이크로 도플러 모형: 회전 날개는 조종기 캐리어 둘레에 측대역을 만든다.
단순 모형 -- 본체 도플러(느림) + 날개 성분(sinc 꼴 HERM 측대역)을 합성한다.
정확한 물리는 나중에. 지금은 **배선과 자원**을 재는 것이 목적이라 재현 가능한 합성이면 된다.
"""
from __future__ import annotations
import numpy as np
from . import param as P


def 합성IQ(길이: int, 종류: str = "드론", 씨앗: int = 1) -> np.ndarray:
    rng = np.random.default_rng(씨앗)
    t = np.arange(길이) / P.fs
    본체 = 30.0                                    # 본체 도플러 Hz (느린 이동)
    x = np.exp(2j*np.pi*본체*t)
    if 종류 == "드론":
        # 날개 4장, 회전 200 rev/s -> 깜빡임 성분 + 측대역
        frot = 200.0
        for k in range(1, 9):
            amp = 1.0/k
            x += amp*np.exp(2j*np.pi*(본체 + k*frot)*t)
            x += amp*np.exp(2j*np.pi*(본체 - k*frot)*t)
    elif 종류 == "새":
        # 날갯짓 ~10 Hz, 측대역이 좁고 성김
        for k in range(1, 3):
            x += (0.5/k)*np.exp(2j*np.pi*(본체 + k*10.0)*t)
    # 잡음
    x += (rng.standard_normal(길이) + 1j*rng.standard_normal(길이)) * 0.3
    return x.astype(np.complex64)


def 고정소수(x: np.ndarray, 비트: int = 16) -> np.ndarray:
    """RTL 과 같은 Q 형식으로 양자화. 최대 진폭을 재서 스케일한다."""
    s = np.max(np.abs(np.concatenate([x.real, x.imag]))) or 1.0
    q = np.round(x/s * (2**(비트-1)-1))
    return np.clip(q, -(2**(비트-1)), 2**(비트-1)-1).astype(np.int32)


def stft프레임(iq: np.ndarray) -> np.ndarray:
    """한 창의 Hann-STFT 크기제곱. RTL 대조용 황금."""
    win = np.hanning(P.N).astype(np.float64)
    seg = iq[:P.N] * win
    X = np.fft.fft(seg, P.N)
    return (np.abs(X)**2)


if __name__ == "__main__":
    for 종류 in ("드론", "새", "잡음"):
        iq = 합성IQ(P.N*4, 종류 if 종류 != "잡음" else "새", 씨앗=1)
        if 종류 == "잡음":
            iq = (np.random.default_rng(9).standard_normal(P.N*4) +
                  1j*np.random.default_rng(8).standard_normal(P.N*4)).astype(np.complex64)*0.3
        s = stft프레임(iq)
        peak = np.argmax(s[:P.N//2])
        print(f"{종류:5} 스펙트럼 피크 빈={peak:3} ({peak*P.fs/P.N:6.0f} Hz) · 에너지={s.sum():.1e}")
