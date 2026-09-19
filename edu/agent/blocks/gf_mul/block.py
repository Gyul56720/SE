# -*- coding: utf-8 -*-
"""GF(2^10) 곱셈기 블록: 골든모델은 저장소의 gf.py 다."""
import os, sys, random
sys.path.insert(0, "/home/user/SE")
from gf import 필드

여기 = os.path.dirname(os.path.abspath(__file__))
이름 = "gf_mul"
톱 = "tb"
_f = 필드(10, 0x409, 확인됨=False, 이름="GF(1024) 0x409")


def 소스들():
    return [os.path.join(여기, "dut.v")]


def 자극(시행, 씨앗):
    """무작위 + **경계값**.  경계값을 섞는 이유는 무작위가 0 과 1 을 거의 안 내서다."""
    r = random.Random(씨앗)
    경계 = [(0, 0), (1, 1), (0, 1023), (1023, 1023), (512, 2), (1, 1023)]
    쌍 = 경계 + [(r.randrange(1024), r.randrange(1024))
                 for _ in range(max(0, 시행 - len(경계)))]
    입력 = [f"{a:03x} {b:03x}" for a, b in 쌍]
    골든 = [_f.곱하기(a, b) for a, b in 쌍]
    return 입력, 골든
