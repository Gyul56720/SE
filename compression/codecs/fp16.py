"""
상한 기준선: fp16 그대로. 16 bits/weight, 오차는 거의 0.

압축력은 int8 보다 나쁘고 복원력은 좋다. 파레토 곡선의 반대쪽 끝을 보여주려고 둔다 --
"오차만 낮추면 이긴다"가 아니라는 것을 숫자로 확인하는 용도다.
"""
from __future__ import annotations

import struct

import numpy as np

MAGIC = b"F16\x00"


def encode(W: np.ndarray) -> bytes:
    W = np.asarray(W, dtype=np.float32)
    rows, cols = W.shape
    return MAGIC + struct.pack("<II", rows, cols) + W.astype(np.float16).tobytes()


def decode(blob: bytes) -> np.ndarray:
    assert blob[:4] == MAGIC, "fp16 blob 이 아니다"
    rows, cols = struct.unpack("<II", blob[4:12])
    a = np.frombuffer(blob, dtype=np.float16, count=rows * cols, offset=12)
    return a.reshape(rows, cols).astype(np.float32)
