# -*- coding: utf-8 -*-
"""RS 신드롬 누산 한 걸음.  골든모델은 저장소의 gf.py 다.

자극이 **알파의 거듭제곱만** 두 번째 인자로 쓴다.  무작위 값을 넣으면 곱셈기
검사가 되지 그 걸음의 검사가 안 되고, 실제 하드웨어는 그 자리에 알파 거듭제곱만
받는다 -- 안 일어나는 입력으로 시간을 쓰지 않는다.
"""
import os, sys, random
sys.path.insert(0, "/home/user/SE")
from gf import 필드

여기 = os.path.dirname(os.path.abspath(__file__))
이름 = "rs_syn_step"
톱 = "tb"

# 합성·lint 는 **DUT 만** 본다.  테스트벤치를 같이 넣으면 $fopen 때문에
# yosys 가 실패하고 verilator 가 경고를 쏟는다 -- 그것은 블록의 품질이 아니다.
합성톱 = "rs_syn_step"
_f = 필드(10, 0x409, 확인됨=False)


def 소스들():
    """[0] 이 DUT 다 -- 수리와 변이는 이 파일만 건드린다."""
    return [os.path.join(여기, "dut.v"), os.path.join(여기, "tb.v")]


def 자극(시행, 씨앗):
    rnd = random.Random(씨앗)
    경계 = [(0, 1, 0), (0, 1, 1023), (1023, 1, 0), (1, _f.알파(1), 0)]
    셋 = list(경계)
    for _ in range(max(0, 시행 - len(경계))):
        j = rnd.randrange(30)                    # 2t = 30 신드롬
        셋.append((rnd.randrange(1024), _f.알파(j), rnd.randrange(1024)))
    입력 = [f"{s:03x} {a:03x} {r:03x}" for s, a, r in 셋]
    골든 = [_f.더하기(_f.곱하기(s, a), r) for s, a, r in 셋]
    return 입력, 골든


# 처리량 한계를 선언하지 않는 이유를 **적는다**.  관문이 "못 쟀다" 로 내는 것과
# "해당 없다" 는 다르다 -- 모르는 것은 안 된 것으로 다루되, 아는 것은 적는다.
성능해당없음 = ("조합 블록이다 -- 한 걸음이 조합이다. 위와 같다."
              )
