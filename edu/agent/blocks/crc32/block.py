# -*- coding: utf-8 -*-
"""CRC-32 한 바이트 갱신.  골든모델은 파이썬 표준 zlib.crc32 다.

zlib 을 쓰는 이유는 **독립성** 때문이다.  골든모델을 DUT 와 같은 사람이 같은
이해로 쓰면 둘이 같이 틀린다.  zlib 은 수십 년 동안 다른 이유로 검증된 구현이라
그 위험이 없다.
"""
import os, random, zlib

여기 = os.path.dirname(os.path.abspath(__file__))
이름 = "crc32_8"
톱 = "tb"

# 합성·lint 는 **DUT 만** 본다.  테스트벤치를 같이 넣으면 $fopen 때문에
# yosys 가 실패하고 verilator 가 경고를 쏟는다 -- 그것은 블록의 품질이 아니다.
합성톱 = "crc32_8"


def 소스들():
    """[0] 이 DUT 다 -- 수리와 변이는 이 파일만 건드린다."""
    return [os.path.join(여기, "dut.v"), os.path.join(여기, "tb.v")]


def _한바이트(crc, b):
    """zlib.crc32 는 '최종 XOR 이 적용된' 값을 받고 돌려준다.
    DUT 는 내부 레지스터 값을 다루므로 양쪽 끝에서 보정한다."""
    return zlib.crc32(bytes([b]), crc ^ 0xFFFFFFFF) ^ 0xFFFFFFFF


def 자극(시행, 씨앗):
    r = random.Random(씨앗)
    경계 = [(0x00000000, 0x00), (0xFFFFFFFF, 0x00), (0xFFFFFFFF, 0xFF),
            (0x00000000, 0xFF), (0x00000001, 0x01), (0x80000000, 0x80)]
    쌍 = 경계 + [(r.getrandbits(32), r.getrandbits(8))
                 for _ in range(max(0, 시행 - len(경계)))]
    입력 = [f"{c:08x} {b:02x}" for c, b in 쌍]
    골든 = [_한바이트(c, b) for c, b in 쌍]
    return 입력, 골든


# 처리량 한계를 선언하지 않는 이유를 **적는다**.  관문이 "못 쟀다" 로 내는 것과
# "해당 없다" 는 다르다 -- 모르는 것은 안 된 것으로 다루되, 아는 것은 적는다.
성능해당없음 = ("조합 블록이다 -- 한 바이트 갱신이 조합이다. 위와 같다."
              )
