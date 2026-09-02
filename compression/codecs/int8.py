"""
기준선(baseline): 채널별 대칭 int8 양자화. **이것을 이겨야 한다.**

행 하나(출력 채널)마다 scale = max|w|/127 을 따로 둔다. LLM 가중치는 채널마다 크기가
수십 배씩 다르므로 행렬 전체에 스케일 하나를 쓰면 작은 채널이 뭉개진다 -- per-channel 이
표준이 된 이유다.

blob = magic | rows | cols | scales(float32 x rows) | int8 데이터
bits/weight = 8 + 32/cols  (cols=896 이면 8.036)
"""
from __future__ import annotations

import struct

import numpy as np

MAGIC = b"I8\x01\x00"


def encode(W: np.ndarray) -> bytes:
    W = np.asarray(W, dtype=np.float32)
    rows, cols = W.shape
    scale = np.abs(W).max(axis=1) / 127.0
    scale[scale == 0] = 1.0                      # 전부 0인 채널: 0으로 나누지 않는다
    q = np.clip(np.rint(W / scale[:, None]), -127, 127).astype(np.int8)
    return (MAGIC + struct.pack("<II", rows, cols)
            + scale.astype(np.float32).tobytes() + q.tobytes())


def decode(blob: bytes) -> np.ndarray:
    assert blob[:4] == MAGIC, "int8 blob 이 아니다"
    rows, cols = struct.unpack("<II", blob[4:12])
    off = 12
    scale = np.frombuffer(blob, dtype=np.float32, count=rows, offset=off)
    off += rows * 4
    q = np.frombuffer(blob, dtype=np.int8, count=rows * cols, offset=off).reshape(rows, cols)
    return (q.astype(np.float32) * scale[:, None]).astype(np.float32)
