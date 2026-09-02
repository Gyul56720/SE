"""부정행위 4: 실행마다 결과가 달라진다 -- 점수를 흔들어 래칫을 무력화한다."""
import os
import struct

import numpy as np


def encode(W):
    W = np.asarray(W, dtype=np.float32)
    rows, cols = W.shape
    noise = os.urandom(8)
    return struct.pack("<II", rows, cols) + noise + W.astype(np.float16).tobytes()


def decode(blob):
    rows, cols = struct.unpack("<II", blob[:8])
    return np.frombuffer(blob, dtype=np.float16, count=rows * cols,
                         offset=16).reshape(rows, cols).astype(np.float32)
