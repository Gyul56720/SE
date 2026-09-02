"""부정행위 5: blob 에 모양을 안 담아 decode 가 다른 모양을 낸다(비트는 아껴진다)."""
import numpy as np


def encode(W):
    return np.asarray(W, dtype=np.float16).tobytes()


def decode(blob):
    return np.frombuffer(blob, dtype=np.float16).astype(np.float32)   # 1차원
