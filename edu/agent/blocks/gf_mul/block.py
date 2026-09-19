# -*- coding: utf-8 -*-
"""GF(2^10) 곱셈기 블록: 골든모델은 저장소의 gf.py 다."""
import os, sys, random
sys.path.insert(0, "/home/user/SE")
from gf import 필드

여기 = os.path.dirname(os.path.abspath(__file__))
이름 = "gf_mul"
톱 = "tb"
_f = 필드(10, 0x409, 확인됨=False, 이름="GF(1024) 0x409")


# 합성·lint 는 **DUT 만** 본다.  테스트벤치를 같이 넣으면 $fopen 때문에
# yosys 가 실패하고 verilator 가 경고를 쏟는다 -- 그것은 블록의 품질이 아니다.
합성톱 = "gf_mul"


def 소스들():
    """[0] 이 DUT 다 -- 수리와 변이는 이 파일만 건드린다."""
    return [os.path.join(여기, "dut.v"), os.path.join(여기, "tb.v")]


def 자극(시행, 씨앗):
    """무작위 + **경계값**.  경계값을 섞는 이유는 무작위가 0 과 1 을 거의 안 내서다."""
    r = random.Random(씨앗)
    경계 = [(0, 0), (1, 1), (0, 1023), (1023, 1023), (512, 2), (1, 1023)]
    쌍 = 경계 + [(r.randrange(1024), r.randrange(1024))
                 for _ in range(max(0, 시행 - len(경계)))]
    입력 = [f"{a:03x} {b:03x}" for a, b in 쌍]
    골든 = [_f.곱하기(a, b) for a, b in 쌍]
    return 입력, 골든


# 처리량 한계를 선언하지 않는 이유를 **적는다**.  관문이 "못 쟀다" 로 내는 것과
# "해당 없다" 는 다르다 -- 모르는 것은 안 된 것으로 다루되, 아는 것은 적는다.
성능해당없음 = ("조합 블록이다 -- 한 사이클에 곱한다. 사이클 예산은 이 블록을 쓰는"
              )
