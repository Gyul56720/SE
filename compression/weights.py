"""
실제 오픈소스 모델 가중치를 가져와 캐시한다 -- 압축 코덱 탐색의 채점 데이터.

왜 실제 가중치인가: 합성 가우시안으로 코덱을 채점하면 "가우시안을 잘 압축하는 코덱"이
나온다. 실제 LLM 가중치는 가우시안이 아니다 -- 채널마다 스케일이 다르고, 소수의 outlier 가
분포 꼬리를 길게 끌고, 레이어마다 성질이 다르다. int8 per-channel 이 표준이 된 이유가 바로
그 구조다. 합성 데이터로 int8 을 이기는 것은 아무 의미가 없다.

왜 부분 다운로드인가: safetensors 는 헤더에 각 텐서의 바이트 범위가 적혀 있다. HTTP Range
요청으로 필요한 행렬 몇 개만 긁어오면 7B 모델에서도 수십 MB 면 끝난다. 모델 전체를 받을
이유가 없다.

설계셋/평가셋 분리: 코덱을 설계할 때 본 행렬로 채점하면 그 행렬에 과적합한 코덱이 이긴다
(상수 테이블을 코드에 박아넣는 식). 텐서 이름 해시로 갈라서, 평가셋은 설계 과정이 보지
못한 행렬만 쓴다.

오프라인: 이 저장소의 개발 컨테이너는 huggingface.co 로 나가지 못한다(egress 정책).
그래서 받는 것과 채점하는 것을 분리했다 -- fetch 는 네트워크가 되는 곳(VM)에서 한 번 돌고,
verifier 는 캐시 디렉토리만 본다. 캐시가 없으면 조용히 합성으로 넘어가지 않고 실패한다.
--synthetic 을 명시했을 때만 합성 데이터를 만들고, 그 사실은 채점 결과에 source 로 남는다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CACHE_DIR = Path(os.environ.get("SE_WEIGHT_CACHE", HERE / "cache"))

# 기본 모델. 작지만 진짜 LLM 가중치다(bf16, 24레이어, hidden 896).
DEFAULT_REPO = "Qwen/Qwen2.5-0.5B"
DEFAULT_FILE = "model.safetensors"
HF_URL = "https://huggingface.co/{repo}/resolve/main/{file}"

# 가져올 행렬 종류. 성질이 다른 것들을 섞는다 -- attention 사영, MLP, 임베딩은
# 분포가 서로 다르고, 한 종류만으로 채점하면 그 종류에만 좋은 코덱이 이긴다.
WANT_PATTERNS = ["self_attn.q_proj.weight", "self_attn.o_proj.weight",
                 "mlp.gate_proj.weight", "mlp.down_proj.weight"]
MAX_TENSORS = 12
MAX_ELEMS = 4_000_000        # 텐서 하나 상한(행렬이 너무 크면 채점이 느려진다)

_ST_DTYPES = {"F32": np.float32, "F16": np.float16, "BF16": None, "F64": np.float64}


def _fetch(url: str, start: int, end: int) -> bytes:
    """HTTP Range 로 [start, end] 바이트를 가져온다."""
    import requests
    r = requests.get(url, headers={"Range": f"bytes={start}-{end}"}, timeout=120)
    r.raise_for_status()
    return r.content


def _to_f32(raw: bytes, dtype: str, shape: list) -> np.ndarray:
    """safetensors 원시 바이트 -> float32. bf16 은 numpy 에 없어서 상위 16비트로 복원한다."""
    if dtype == "BF16":
        u16 = np.frombuffer(raw, dtype=np.uint16).astype(np.uint32)
        return (u16 << 16).view(np.float32).reshape(shape).astype(np.float32)
    np_dtype = _ST_DTYPES.get(dtype)
    if np_dtype is None:
        raise ValueError(f"지원하지 않는 dtype: {dtype}")
    return np.frombuffer(raw, dtype=np_dtype).reshape(shape).astype(np.float32)


def fetch(repo: str = DEFAULT_REPO, filename: str = DEFAULT_FILE,
          cache_dir: Path = None, limit: int = MAX_TENSORS) -> dict:
    """safetensors 헤더를 읽고 원하는 행렬만 Range 로 받아 .npy 로 캐시한다."""
    cache_dir = Path(cache_dir or CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    url = HF_URL.format(repo=repo, file=filename)

    head = _fetch(url, 0, 7)
    (header_len,) = struct.unpack("<Q", head)
    header = json.loads(_fetch(url, 8, 8 + header_len - 1).decode("utf-8"))
    data_start = 8 + header_len

    picked, saved = [], []
    for name, meta in header.items():
        if name == "__metadata__":
            continue
        if not any(p in name for p in WANT_PATTERNS):
            continue
        shape = meta["shape"]
        if len(shape) != 2 or int(np.prod(shape)) > MAX_ELEMS:
            continue
        picked.append((name, meta))
    picked.sort(key=lambda kv: kv[0])
    picked = picked[:limit]
    if not picked:
        raise RuntimeError("헤더에서 조건에 맞는 2차원 행렬을 찾지 못했다.")

    for name, meta in picked:
        s, e = meta["data_offsets"]
        raw = _fetch(url, data_start + s, data_start + e - 1)
        arr = _to_f32(raw, meta["dtype"], meta["shape"])
        out = cache_dir / (name.replace("/", "_") + ".npy")
        np.save(out, arr)
        saved.append({"name": name, "shape": list(arr.shape), "file": out.name})
        print(f"  {name} {tuple(arr.shape)} -> {out.name} ({arr.nbytes/1e6:.1f}MB)")

    manifest = {"source": f"{repo}/{filename}", "synthetic": False, "tensors": saved}
    (cache_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
    return manifest


def make_synthetic(cache_dir: Path = None, count: int = 8, seed: int = 0) -> dict:
    """네트워크가 없는 곳에서 배관을 시험하기 위한 가짜 가중치.

    실제 가중치가 아니다. 이걸로 낸 점수는 코덱의 성능이 아니라 파이프라인이 도는지의
    확인일 뿐이다. manifest 에 synthetic=True 로 남고 verifier 가 결과에 그대로 싣는다."""
    cache_dir = Path(cache_dir or CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    saved = []
    for i in range(count):
        rows, cols = 256, 256
        # 채널별 스케일 차이 + **행마다** outlier. 처음에는 전체에서 무작위로 몇 개만
        # 키웠는데, 그러면 행별 max/std 가 3 정도에 그쳐 채널 단위 양자화에 아무 영향이
        # 없었다(실측). 실제 LLM 가중치는 채널 안에 소수의 큰 값이 있고, 그것이 per-channel
        # max-abs 스케일의 해상도를 잡아먹는 것이 알려진 현상이다. 그 성질을 흉내 낸다.
        scale = rng.lognormal(mean=0.0, sigma=0.6, size=(rows, 1)).astype(np.float32)
        W = (rng.standard_normal((rows, cols)).astype(np.float32) * scale) * 0.02
        for r in range(rows):
            k = int(rng.integers(1, 3))
            cols_idx = rng.integers(0, cols, size=k)
            W[r, cols_idx] *= rng.uniform(8.0, 20.0, size=k).astype(np.float32)
        name = f"synthetic.layer{i}.weight"
        out = cache_dir / (name + ".npy")
        np.save(out, W)
        saved.append({"name": name, "shape": list(W.shape), "file": out.name})
    manifest = {"source": "synthetic", "synthetic": True, "tensors": saved}
    (cache_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
    return manifest


def _split(name: str) -> str:
    """텐서 이름 해시로 설계셋/평가셋을 가른다. 이름만 보고 결정되므로 재현된다."""
    h = int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:8], 16)
    return "holdout" if h % 3 == 0 else "design"


def load(split: str = "holdout", cache_dir: Path = None) -> "list[tuple[str, np.ndarray]]":
    """캐시에서 (이름, 행렬) 목록을 읽는다. split 은 'design' | 'holdout' | 'all'."""
    cache_dir = Path(cache_dir or CACHE_DIR)
    man_path = cache_dir / "manifest.json"
    if not man_path.is_file():
        raise FileNotFoundError(
            f"가중치 캐시가 없다: {cache_dir}\n"
            f"네트워크가 되는 곳에서 `python3 compression/weights.py fetch` 를 먼저 돌려라.\n"
            f"(배관 시험만 할 거면 `python3 compression/weights.py synthetic` -- "
            f"실제 가중치가 아니고 결과에 synthetic 으로 표시된다)")
    manifest = json.loads(man_path.read_text(encoding="utf-8"))
    out = []
    for t in manifest["tensors"]:
        if split != "all" and _split(t["name"]) != split:
            continue
        out.append((t["name"], np.load(cache_dir / t["file"])))
    if not out:
        raise RuntimeError(f"'{split}' 셋이 비었다. 텐서를 더 받아라.")
    return out


def manifest(cache_dir: Path = None) -> dict:
    cache_dir = Path(cache_dir or CACHE_DIR)
    return json.loads((cache_dir / "manifest.json").read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="압축 코덱 채점용 실제 가중치 캐시")
    ap.add_argument("action", choices=["fetch", "synthetic", "list"])
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--file", default=DEFAULT_FILE)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--limit", type=int, default=MAX_TENSORS)
    args = ap.parse_args()
    cache = Path(args.cache) if args.cache else CACHE_DIR

    if args.action == "fetch":
        print(f"{args.repo}/{args.file} 에서 행렬을 받는다 -> {cache}")
        m = fetch(args.repo, args.file, cache, args.limit)
    elif args.action == "synthetic":
        m = make_synthetic(cache)
        print("합성 가중치를 만들었다 -- 실제 가중치가 아니다. 배관 시험용.")
    else:
        m = manifest(cache)

    for t in m["tensors"]:
        print(f"  [{_split(t['name']):7}] {t['name']} {tuple(t['shape'])}")
    print(f"source={m['source']} synthetic={m['synthetic']} 총 {len(m['tensors'])}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
