"""
BitNet b1.58 방식 3진 양자화 + 5진법 패킹. ~1.6 bits/weight.

npu/quantize_data.py 가 하던 것을 코덱 계약에 맞춰 다시 쓴 것이다. 원본은 gamma 를 상수
0.65 로 박아놨는데, 여기서는 채널별 평균 절대값으로 정한다(b1.58 논문의 방식).

압축력은 int8 을 크게 이기고 복원력은 크게 진다. 이 두 축을 동시에 이기는 것이 목표다 --
이 코덱은 "한쪽만 이기는 것은 쉽다"는 사실을 숫자로 남기는 기준선이다.

blob = magic | rows | cols | scales(float32 x rows) | 5개씩 묶은 3진 바이트
"""
from __future__ import annotations

import struct

import numpy as np

MAGIC = b"T3\x01\x00"
PACK = 5                                          # 3^5 = 243 <= 255, 바이트 하나에 5개
_POW = (3 ** np.arange(PACK)).astype(np.int32)


def encode(W: np.ndarray) -> bytes:
    W = np.asarray(W, dtype=np.float32)
    rows, cols = W.shape
    scale = np.abs(W).mean(axis=1)
    scale[scale == 0] = 1.0
    t = np.clip(np.rint(W / scale[:, None]), -1, 1).astype(np.int8)

    flat = (t.reshape(-1) + 1).astype(np.int32)   # -1,0,1 -> 0,1,2
    pad = (-flat.size) % PACK
    if pad:
        flat = np.concatenate([flat, np.ones(pad, dtype=np.int32)])   # 0(=값 0)으로 채운다
    packed = (flat.reshape(-1, PACK) * _POW).sum(axis=1).astype(np.uint8)
    return (MAGIC + struct.pack("<II", rows, cols)
            + scale.astype(np.float32).tobytes() + packed.tobytes())


def decode(blob: bytes) -> np.ndarray:
    assert blob[:4] == MAGIC, "ternary blob 이 아니다"
    rows, cols = struct.unpack("<II", blob[4:12])
    off = 12
    scale = np.frombuffer(blob, dtype=np.float32, count=rows, offset=off)
    off += rows * 4
    packed = np.frombuffer(blob, dtype=np.uint8, offset=off).astype(np.int32)
    digits = ((packed[:, None] // _POW) % 3).reshape(-1)[:rows * cols]
    t = (digits.astype(np.float32) - 1.0).reshape(rows, cols)
    return (t * scale[:, None]).astype(np.float32)
