"""
int8 개선안: 스케일을 max|w| 가 아니라 **오차 최소화**로 고르고, 스케일 자체를 fp16 으로 저장.

두 축을 각각 건드린다.
  복원력: per-channel max-abs 스케일은 outlier 하나가 그 채널 전체의 해상도를 잡아먹는다.
          LLM 가중치는 outlier 가 실제로 있다. 후보 클리핑 비율을 훑어 재구성 MSE 가 가장
          작은 지점을 고른다 -- outlier 는 잘리지만 나머지 전부가 촘촘해진다.
  압축력: 스케일은 채널당 하나뿐이라 fp32 로 둘 이유가 없다. fp16 이면 채널당 2바이트가
          줄고, 스케일은 어차피 양자화 격자보다 훨씬 정밀하다.

blob = magic | rows | cols | scales(float16 x rows) | int8 데이터
bits/weight = 8 + 16/cols
"""
from __future__ import annotations

import struct

import numpy as np

MAGIC = b"I8C\x01"
# 훑어볼 클리핑 비율. 1.0 이 기존 max-abs 이므로 최악이어도 기존과 같아진다.
_RATIOS = np.array([1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.42, 0.35, 0.3, 0.25], dtype=np.float32)


def _best_scales(W: np.ndarray) -> np.ndarray:
    """채널마다 재구성 MSE 를 최소화하는 스케일을 고른다."""
    amax = np.abs(W).max(axis=1)
    amax[amax == 0] = 1.0
    rows = W.shape[0]
    best = amax / 127.0
    best_err = np.full(rows, np.inf, dtype=np.float32)
    for r in _RATIOS:
        scale = (amax * r) / 127.0
        q = np.clip(np.rint(W / scale[:, None]), -127, 127)
        err = ((q * scale[:, None] - W) ** 2).mean(axis=1)
        take = err < best_err
        best_err = np.where(take, err, best_err)
        best = np.where(take, scale, best)
    return best.astype(np.float32)


def encode(W: np.ndarray) -> bytes:
    W = np.asarray(W, dtype=np.float32)
    rows, cols = W.shape
    scale = _best_scales(W)
    # fp16 으로 저장할 값이므로, 양자화도 그 fp16 값으로 해야 decode 와 어긋나지 않는다.
    scale16 = scale.astype(np.float16)
    eff = scale16.astype(np.float32)
    eff[eff == 0] = np.float32(np.finfo(np.float16).tiny)
    q = np.clip(np.rint(W / eff[:, None]), -127, 127).astype(np.int8)
    return (MAGIC + struct.pack("<II", rows, cols) + scale16.tobytes() + q.tobytes())


def decode(blob: bytes) -> np.ndarray:
    assert blob[:4] == MAGIC, "int8_clip blob 이 아니다"
    rows, cols = struct.unpack("<II", blob[4:12])
    off = 12
    scale = np.frombuffer(blob, dtype=np.float16, count=rows, offset=off).astype(np.float32)
    off += rows * 2
    q = np.frombuffer(blob, dtype=np.int8, count=rows * cols, offset=off).reshape(rows, cols)
    return (q.astype(np.float32) * scale[:, None]).astype(np.float32)
