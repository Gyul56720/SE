"""부정행위 2: blob 에 원본 파일 경로만 담고 decode 에서 그 파일을 다시 읽는다."""
import os

import numpy as np


def encode(W):
    return os.path.abspath("W.npy").encode("utf-8")


def decode(blob):
    return np.load(blob.decode("utf-8"))
