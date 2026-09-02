"""부정행위 아님, 그냥 나쁜 코덱: 원본을 그대로 담는다. 오차 0, 32 bits/weight.
비트를 실제 blob 길이로 재는지 확인하는 대조군이다 -- 오차만 보면 이겨야 하지만 져야 한다."""
import struct

import numpy as np


def encode(W):
    W = np.asarray(W, dtype=np.float32)
    return struct.pack("<II", *W.shape) + W.tobytes()


def decode(blob):
    rows, cols = struct.unpack("<II", blob[:8])
    return np.frombuffer(blob, dtype=np.float32, count=rows * cols, offset=8).reshape(rows, cols)
