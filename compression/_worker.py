"""
코덱을 격리해서 돌리는 자식 프로세스. judge.py 가 encode/decode 를 각각 따로 띄운다.

왜 프로세스를 나누는가: 같은 프로세스에서 encode 와 decode 를 부르면 코덱이 모듈 전역
변수에 원본 행렬을 숨겨두고 decode 에서 꺼내 쓸 수 있다. 그러면 blob 이 1비트여도 완벽히
복원된다 -- 채점이 통째로 무의미해진다. 프로세스를 나누고, decode 를 띄우기 전에 원본
.npy 를 지우면 그 경로가 막힌다.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys

import numpy as np


def _load(path: str):
    spec = importlib.util.spec_from_file_location("_codec_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["encode", "decode"])
    ap.add_argument("--codec", required=True)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    a = ap.parse_args()

    codec = _load(a.codec)
    if a.mode == "encode":
        W = np.load(a.inp)
        blob = codec.encode(W)
        if not isinstance(blob, (bytes, bytearray)):
            print(f"encode 가 bytes 를 반환하지 않았다: {type(blob).__name__}", file=sys.stderr)
            return 2
        with open(a.out, "wb") as f:
            f.write(bytes(blob))
    else:
        with open(a.inp, "rb") as f:
            blob = f.read()
        R = codec.decode(blob)
        R = np.asarray(R, dtype=np.float32)
        np.save(a.out, R)
    return 0


if __name__ == "__main__":
    sys.exit(main())
