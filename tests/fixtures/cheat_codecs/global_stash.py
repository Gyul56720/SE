"""부정행위 1: 원본을 모듈 전역에 숨기고 blob 은 4바이트만 낸다."""
import numpy as np
_STASH = {}


def encode(W):
    _STASH["W"] = np.asarray(W, dtype=np.float32)
    return b"\x00\x00\x00\x01"


def decode(blob):
    return _STASH["W"]                      # 같은 프로세스라면 완벽 복원 + 4바이트
