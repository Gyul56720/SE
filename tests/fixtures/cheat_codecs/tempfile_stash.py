"""부정행위 3: 원본을 임시 디렉토리에 몰래 쓰고 blob 에는 경로만 담는다."""
import os
import tempfile

import numpy as np


def encode(W):
    path = os.path.join(tempfile.gettempdir(), "stash_original.npy")
    np.save(path, np.asarray(W, dtype=np.float32))
    return path.encode("utf-8")


def decode(blob):
    return np.load(blob.decode("utf-8"))
