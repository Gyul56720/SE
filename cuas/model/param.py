# -*- coding: utf-8 -*-
"""CUAS 마이크로 도플러 -- 설계 파라미터를 **물리에서** 낸다. 추측하지 않는다."""
import math

c = 3e8
fc = 10e9                       # X-band
lam = c / fc
날개반경 = 0.12                  # m, 소형 드론 프로펠러
최대rpm = 15000

def 최대_마이크로도플러() -> float:
    w = 최대rpm / 60 * 2 * math.pi
    vtip = w * 날개반경
    return 2 * vtip / lam        # Hz

fs = 40_000                     # 표본율 (2*fd 의 1.6배 여유)
N = 256                         # STFT 창
HOP = 64
관측_ms = 20

def 요약() -> dict:
    fd = 최대_마이크로도플러()
    return {"fc_GHz": fc/1e9, "lambda_mm": lam*1000, "f_micro_max_kHz": fd/1000,
            "fs_kHz": fs/1000, "N": N, "HOP": HOP,
            "창길이_ms": N/fs*1000, "분해능_Hz": fs/N,
            "관측당_홉": int((관측_ms*1e-3*fs - N)/HOP)+1}

if __name__ == "__main__":
    for k, v in 요약().items():
        print(f"  {k:18} {v}")
