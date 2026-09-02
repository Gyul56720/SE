"""
압축 코덱의 독립 심판. 코덱을 만든 쪽이 아니라 여기가 점수를 정한다.

이것이 이 저장소가 말하는 "밖에서 주입한 심판"이다(orchestrator/MANUAL.md 축 A). 플래너나
자가개선 루프가 코덱을 아무리 그럴듯하게 써도, 통과 여부는 이 파일이 정한다. 이 파일은
코덱을 블랙박스로만 다룬다 -- encode 로 바이트를 받고, decode 로 행렬을 돌려받고, 그 둘만
가지고 잰다. 코덱 안이 무슨 알고리즘인지 보지 않는다.

프로그램 최적화의 언어로 쓰면: 레이어 하나가 프로그램 P(x) = W @ x 이고, 압축된 가중치는
최적화된 프로그램 P'(x) = W' @ x 다. 채점은 P(x) ≈ P'(x) 를 실측 입력으로 확인하는 것이고,
거기에 메모리(bits/weight)와 시간(encode/decode 초)을 함께 잰다.

  원본 W ──> encode(별도 프로세스) ──> blob ──> decode(별도 프로세스) ──> W'
     │                                  │                                 │
     │                             실제 바이트 수                          │
     └──────────── 같은 X 로 W@X 와 W'@X 를 비교 ──────────────────────────┘

두 축을 **동시에** 이겨야 한다:
  - 압축력: bits/weight 가 int8 기준선보다 작다
  - 복원력: 함수 오차가 int8 기준선보다 작다
한쪽만 이기는 것은 쉽다. ternary_b158 은 압축력을 4.7배 이기고 복원력에서 31배 진다.
fp16 은 복원력을 124배 이기고 압축력에서 2배 진다. 둘 다 이기는 것이 목표다.

집계에서 두 가지를 지킨다:
  - 압축배율의 분모는 **원본이 배포되는 비트폭**(bf16 = 16)이지 fp32(32) 가 아니다.
  - 텐서별 산술 평균이 아니라 **파라미터 수 가중 평균**이다.
둘 다 예전에 틀려 있었다. 분모가 32 라 배율이 전부 2배 부풀었고(int8 이 3.9배로 표시됐다),
산술 평균이라 0.8M 짜리 q_proj 와 4.4M 짜리 gate_proj 가 같은 표를 가졌다.

부정행위 차단(무엇을 막고 무엇을 못 막는지 분명히 적는다):
  막는다 - 전역 변수로 원본 넘기기(프로세스 분리), 원본 파일 재읽기(decode 전에 지운다),
           비트 수 속이기(코덱의 주장이 아니라 실제 blob 길이로 잰다), 설계한 행렬로
           채점하기(holdout 셋), 실행마다 다른 결과 내기(결정성 검사),
           임시 디렉토리에 원본 몰래 쓰기(파일 스냅샷 비교).
  못 막는다 - 코덱이 /tmp 밖 절대경로에 원본을 숨기는 것. 진짜 격리는 컨테이너/네임스페이스가
           필요하다. 여기서 막는 것은 "무심코 새는" 경로와 "그럴듯하게 속이는" 경로다.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import weights  # noqa: E402

WORKER = HERE / "_worker.py"
BASELINE = HERE / "codecs" / "int8.py"

N_PROBE = 32              # P(x)=P'(x) 를 확인할 입력 벡터 수
PROBE_SEED = 20260902     # 고정 -- 점수가 실행마다 흔들리면 래칫을 걸 수 없다
NODE_TIMEOUT = float(os.environ.get("CODEC_TIMEOUT", "120"))


class CodecFailure(RuntimeError):
    """코덱이 계약을 못 지켰다. 점수가 아니라 실격 사유다."""


def _snapshot(paths) -> dict:
    """파일 목록 스냅샷 (경로 -> (크기, mtime)). 부정행위 흔적 비교용."""
    seen = {}
    for root in paths:
        root = Path(root)
        if not root.exists():
            continue
        for p in root.rglob("*"):
            try:
                if p.is_file():
                    st = p.stat()
                    seen[str(p)] = (st.st_size, st.st_mtime)
            except OSError:
                continue
    return seen


def _run(args: list, env: dict, cwd: Path, timeout: float) -> float:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run([sys.executable, str(WORKER), *args], cwd=str(cwd), env=env,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise CodecFailure(f"{args[0]} 가 {timeout:g}초 예산을 넘겼다")
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
        raise CodecFailure(f"{args[0]} 가 실패했다 (exit={proc.returncode}): " + " / ".join(tail))
    return time.perf_counter() - t0


def _child_env(tmp: Path) -> dict:
    env = dict(os.environ)
    env["TMPDIR"] = str(tmp)
    env["HOME"] = str(tmp)
    env["PYTHONDONTWRITEBYTECODE"] = "1"     # __pycache__ 가 스냅샷을 어지럽히지 않게
    return env


def functional_error(W: np.ndarray, R: np.ndarray, n_probe: int = N_PROBE,
                     seed: int = PROBE_SEED) -> float:
    """P(x)=W@x 와 P'(x)=W'@x 의 상대 오차. 가중치 자체의 오차보다 이것이 본질이다 --
    쓰이는 곳이 행렬곱이므로, 가중치가 조금 틀려도 출력이 보존되면 좋은 코덱이다."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((W.shape[1], n_probe)).astype(np.float32)
    Y, Y2 = W @ X, R @ X
    denom = float(np.linalg.norm(Y))
    if denom == 0:
        return 0.0
    return float(np.linalg.norm(Y - Y2) / denom)


def score_tensor(codec: Path, name: str, W: np.ndarray, timeout: float = NODE_TIMEOUT,
                 src_bits: float = None) -> dict:
    """행렬 하나에 대해 코덱을 격리 실행하고 잰다.

    src_bits 는 압축률의 분모 -- 원본이 몇 비트로 배포되는가다. 생략하면 캐시의
    manifest 에서 읽는다. 실제 모델은 bf16(16) 이지 fp32(32) 가 아니다."""
    codec = Path(codec).resolve()
    tmp_root = Path(tempfile.mkdtemp(prefix="codec_judge_"))
    try:
        enc_dir, dec_dir = tmp_root / "enc", tmp_root / "dec"
        enc_dir.mkdir(); dec_dir.mkdir()
        w_path, blob_path = enc_dir / "W.npy", enc_dir / "blob.bin"
        np.save(w_path, W)

        # 감시 범위: 우리가 만든 임시 트리(자식의 TMPDIR/HOME 이 여기다)와 코덱 파일이
        # 놓인 디렉토리. 시스템 /tmp 전체는 넣지 않는다 -- 다른 프로세스가 쓰는 파일까지
        # 잡아 거짓 실격이 난다. 그 대신 자식의 TMPDIR 을 이 트리 안으로 돌려놨으므로
        # tempfile 을 쓰는 코덱은 여기로 들어온다.
        watched = [tmp_root, codec.parent]
        before = _snapshot(watched)
        enc_s = _run(["encode", "--codec", str(codec), "--in", str(w_path),
                      "--out", str(blob_path)], _child_env(enc_dir), enc_dir, timeout)
        after = _snapshot(watched)

        if not blob_path.is_file():
            raise CodecFailure("encode 가 blob 을 만들지 않았다")
        blob = blob_path.read_bytes()
        if not blob:
            raise CodecFailure("encode 가 빈 blob 을 냈다")

        # 결정성: 같은 입력에 같은 blob. 점수가 흔들리면 래칫(개선만 채택)이 성립하지 않는다.
        blob2_path = enc_dir / "blob2.bin"
        _run(["encode", "--codec", str(codec), "--in", str(w_path), "--out", str(blob2_path)],
             _child_env(enc_dir), enc_dir, timeout)
        if blob2_path.read_bytes() != blob:
            raise CodecFailure("encode 가 결정론적이지 않다 -- 같은 입력에 다른 blob 을 낸다")

        # 부정행위 흔적: blob 말고 새로 생긴 파일이 있는가.
        allowed = {str(blob_path), str(blob2_path), str(w_path)}
        stashed = [p for p in set(after) - set(before) if p not in allowed]
        if stashed:
            raise CodecFailure(
                "encode 가 blob 밖에 파일을 남겼다(원본 은닉 의심): " + ", ".join(stashed[:3]))

        # 원본을 지운다. 이제 decode 는 blob 말고 볼 것이 없다.
        shutil.copy2(blob_path, dec_dir / "blob.bin")
        shutil.rmtree(enc_dir, ignore_errors=True)

        rec_path = dec_dir / "R.npy"
        dec_s = _run(["decode", "--codec", str(codec), "--in", str(dec_dir / "blob.bin"),
                      "--out", str(rec_path)], _child_env(dec_dir), dec_dir, timeout)
        R = np.load(rec_path)
        if R.shape != W.shape:
            raise CodecFailure(f"decode 가 모양을 잃었다: {R.shape} != {W.shape} "
                               f"-- shape 도 blob 에 담아야 한다")
        if not np.isfinite(R).all():
            raise CodecFailure("decode 결과에 NaN/Inf 가 있다")

        bits = 8.0 * len(blob) / W.size
        sb = float(src_bits if src_bits is not None else weights.source_bits())
        return {
            "name": name, "shape": list(W.shape), "n_weights": int(W.size),
            "bits_per_weight": bits,
            "compression_x": sb / bits,
            "func_err": functional_error(W, R),
            "weight_err": float(np.linalg.norm(W - R) / (np.linalg.norm(W) or 1.0)),
            "encode_s": enc_s, "decode_s": dec_s,
        }
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def score_codec(codec: Path, split: str = "holdout", cache_dir=None,
                timeout: float = NODE_TIMEOUT) -> dict:
    """코덱을 평가셋 전체로 채점한다.

    집계는 텐서별 산술 평균이 아니라 **파라미터 수 가중 평균**이다. 산술 평균을 쓰면
    작은 텐서와 큰 텐서가 같은 표를 갖는다 -- Qwen2.5-0.5B 한 레이어에서 MLP 가
    87.7%, q+o 가 10.8%, GQA 라 k+v 는 1.5% 인데, 텐서별 평균은 이 셋을 동급으로 센다.
    그러면 작은 텐서에만 좋은 코덱이 이긴다.

    bits/weight 의 가중 평균은 정의상 (전체 blob 비트) / (전체 파라미터 수) 와 같다 --
    즉 "이 코덱으로 모델을 담으면 몇 비트인가"라는 원래 묻고 싶던 값이 된다.

    시간(encode_s/decode_s)만 평균이 아니라 합이다. 평균 내면 텐서를 늘릴수록 작아 보인다.
    """
    tensors = weights.load(split, cache_dir)
    sb = float(weights.source_bits(cache_dir))
    rows = [score_tensor(codec, name, W, timeout, sb) for name, W in tensors]
    total = sum(r["n_weights"] for r in rows)

    def wmean(key: str) -> float:
        return sum(r[key] * r["n_weights"] for r in rows) / total

    mean = {"bits_per_weight": wmean("bits_per_weight"),
            "func_err": wmean("func_err"),
            "weight_err": wmean("weight_err"),
            "encode_s": sum(r["encode_s"] for r in rows),
            "decode_s": sum(r["decode_s"] for r in rows),
            "n_weights": total}
    mean["compression_x"] = sb / mean["bits_per_weight"]
    return {"codec": str(codec), "split": split, "source_bits": sb,
            "tensors": rows, "mean": mean}


def evaluate(codec: Path, split: str = "holdout", cache_dir=None,
             timeout: float = NODE_TIMEOUT) -> dict:
    """코덱을 채점하고 int8 기준선과 비교해 승패까지 판정한다."""
    man = weights.manifest(cache_dir)
    result = score_codec(codec, split, cache_dir, timeout)
    base = score_codec(BASELINE, split, cache_dir, timeout)

    m, b = result["mean"], base["mean"]
    smaller_bits = m["bits_per_weight"] < b["bits_per_weight"]
    smaller_err = m["func_err"] < b["func_err"]
    if smaller_bits and smaller_err:
        verdict, why = True, (
            f"int8 을 두 축에서 이겼다: {m['bits_per_weight']:.3f} < {b['bits_per_weight']:.3f} "
            f"bits/weight, 오차 {m['func_err']:.5f} < {b['func_err']:.5f}")
    elif smaller_bits:
        verdict, why = False, (
            f"압축력만 이겼다(복원력이 진다): 오차 {m['func_err']:.5f} >= {b['func_err']:.5f}")
    elif smaller_err:
        verdict, why = False, (
            f"복원력만 이겼다(압축력이 진다): {m['bits_per_weight']:.3f} >= "
            f"{b['bits_per_weight']:.3f} bits/weight")
    else:
        verdict, why = False, "두 축 모두 int8 보다 나쁘다"

    return {
        "codec": str(codec),
        "source": man["source"], "synthetic": man["synthetic"], "split": split,
        "source_bits": result["source_bits"],
        "n_tensors": len(result["tensors"]),
        "mean": m, "baseline_int8": b, "tensors": result["tensors"],
        "beats_int8": verdict, "reason": why,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="압축 코덱 독립 심판 (int8 기준선과 비교)")
    ap.add_argument("--codec", required=True, help="encode/decode 를 정의한 파이썬 파일")
    ap.add_argument("--split", default="holdout", choices=["holdout", "design", "all"])
    ap.add_argument("--cache", default=None)
    ap.add_argument("--timeout", type=float, default=NODE_TIMEOUT)
    ap.add_argument("--json", action="store_true", help="결과를 JSON 으로만 출력")
    a = ap.parse_args()

    try:
        res = evaluate(Path(a.codec), a.split, a.cache, a.timeout)
    except CodecFailure as e:
        out = {"codec": a.codec, "beats_int8": False, "reason": f"실격: {e}"}
        print(json.dumps(out, ensure_ascii=False, indent=2) if a.json else f"실격 -- {e}")
        return 1

    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["beats_int8"] else 1

    m, b = res["mean"], res["baseline_int8"]
    warn = "  ⚠ 합성 데이터 -- 실제 가중치가 아니다" if res["synthetic"] else ""
    print(f"코덱 {res['codec']}")
    sb = res.get("source_bits", 16)
    print(f"데이터 {res['source']} / {res['split']} 셋 {res['n_tensors']}개, "
          f"파라미터 {m['n_weights']:,}개{warn}")
    print(f"압축배율 분모 = 원본 {sb:g} bits/weight (bf16 배포 기준)")
    print(f"{'':14}{'bits/weight':>13}{'압축배율':>10}{'함수오차':>12}{'가중치오차':>12}")
    print(f"{'이 코덱':14}{m['bits_per_weight']:13.3f}{m['compression_x']:9.2f}x"
          f"{m['func_err']:12.5f}{m['weight_err']:12.5f}")
    print(f"{'int8 기준선':14}{b['bits_per_weight']:13.3f}{b['compression_x']:9.2f}x"
          f"{b['func_err']:12.5f}{b['weight_err']:12.5f}")
    print(f"encode {m['encode_s']*1000:.0f}ms / decode {m['decode_s']*1000:.0f}ms "
          f"(셋 전체 합계)")
    print(("통과: " if res["beats_int8"] else "미달: ") + res["reason"])
    return 0 if res["beats_int8"] else 1


if __name__ == "__main__":
    sys.exit(main())
