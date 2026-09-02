"""무엇이 이론적 하한이고 무엇이 가정인지 분리해서 잰다.

이 파일은 코덱을 만들지 않는다. **어디까지 갈 수 있는지**와, 그 답이 어떤 가정에 매달려
있는지를 숫자로 보여준다. 같은 스크립트를 VM 에서 실제 가중치·실제 활성치로 다시 돌리면
가정이 실제로 얼마짜리였는지가 드러난다.

세 개의 서로 다른 '한계'를 구별한다 -- 앞서 한 번 혼동했던 지점이다:

  (A) 가우시안 R(D) = -log2(e)
      주어진 분산에서 엔트로피를 최대화하는 분포의 값. 어떤 분포든 이보다 작거나 같다.
      **하한이 아니라 상한이다.**

  (B) 섀넌 하한 SLB = h(X) - 0.5·log2(2πeD)
      i.i.d. 가정 하의 진짜 하한. 실측 h(X) 를 쓴다.

  (C) 활성치를 아는 하한 = SLB - 변환부호화이득
      가중 MSE 에서 최적 비트 배분의 이득은 0.5·log2(AM(σ²)/GM(σ²)) 이다.
      σ_j² 는 입력 채널 j 의 활성치 분산. 등방이면 AM=GM 이라 이득이 0 이 된다 --
      즉 등방 가정은 이 이득을 **정의상 0 으로 만든다**.

(C) 조차 하한이 아니다. 남은 가정:
  - i.i.d.: 실측으로 깨진다(이웃 문맥에서 편향 보정 후 약 0.065 bits).
  - `W` 를 복원해야 한다: 압축 모델이 지켜야 하는 건 W 가 아니라 함수다. 레이어를 통째로
    재파라미터화해도 출력만 같으면 된다(BitNet 학습이 그것이다). 그러면 "W 복원"의
    율-왜곡 하한은 아무것도 말해주지 않는다.

그리고 이 스크립트가 드러내는 설계 충돌 하나: **회전과 활성치 비트배분은 서로를 깎는다.**
아다마르 회전은 가중치를 균질하게 만들어 양자화를 쉽게 하지만, 같은 이유로 활성치도
등방으로 만들어 "이 채널은 안 중요하다"를 표현할 수 없게 한다. 두 이득을 다 가지려면
부분 이동(AWQ/SmoothQuant 의 α)처럼 중간 어딘가를 골라야 한다.
"""
from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import activations  # noqa: E402
import judge  # noqa: E402
import weights  # noqa: E402


def _codec():
    """챔피언 코덱과 **같은** 회전·그룹 크기를 쓴다. 두 곳에 따로 두면 곧 갈라진다."""
    global _CODEC
    if _CODEC is None:
        spec = importlib.util.spec_from_file_location(
            "_hr", HERE / "codecs" / "hadamard_int.py")
        _CODEC = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_CODEC)
    return _CODEC


_CODEC = None


def _rotation(n: int):
    return _codec()._rotation(n)


def _group(n: int) -> int:
    return _codec()._divisor(n, _codec().MAX_GROUP)


def coding_gain(v: np.ndarray) -> float:
    """0.5·log2(AM/GM). 최적 비트배분이 균등배분보다 아끼는 비트 수."""
    v = np.asarray(v, dtype=np.float64)
    v = np.maximum(v, v.max() * 1e-12) if v.max() > 0 else np.ones_like(v)
    return 0.5 * math.log2(float(v.mean()) / float(np.exp(np.log(v).mean())))


def differential_entropy(x: np.ndarray, bins: int = 4096) -> float:
    """히스토그램 추정. 분산 1 로 표준화한 표본에 대해 bits 단위."""
    x = np.asarray(x, dtype=np.float64).ravel()
    x = x / (x.std() or 1.0)
    lo, hi = np.percentile(x, [0.001, 99.999])
    d = (hi - lo) / bins
    cnt, _ = np.histogram(x, bins=bins, range=(lo, hi))
    p = cnt / cnt.sum()
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum() + math.log2(d))


def report(split: str = "holdout", cache_dir=None) -> dict:
    T = weights.load(split, cache_dir)
    tot = sum(W.size for _, W in T)
    act_man = activations.manifest(cache_dir)

    # 목표 왜곡: int8 기준선의 가중치 상대오차
    e8 = 0.0
    for _, W in T:
        sc = np.abs(W).max(1, keepdims=True) / 127.0
        sc[sc == 0] = 1
        R = (np.round(W / sc).clip(-127, 127) * sc).astype(np.float32)
        e8 += float(np.linalg.norm(W - R) / np.linalg.norm(W)) * W.size
    e8 /= tot

    # 회전 후 가중치의 미분 엔트로피 (블록 스케일은 따로 세므로 블록별 표준화)
    vals = []
    ov_sum = 0.0
    for _, W in T:
        g = _group(W.shape[1])
        H = _rotation(W.shape[1])
        R = (W @ H).reshape(W.shape[0], -1, g)
        vals.append((R / np.maximum(R.std(2, keepdims=True), 1e-12)).ravel())
        ov_sum += (16.0 / g) * W.size
    h_x = differential_entropy(np.concatenate(vals))
    h_g = 0.5 * math.log2(2 * math.pi * math.e)

    r_gauss = -math.log2(e8)
    slb = h_x - 0.5 * math.log2(2 * math.pi * math.e * e8 ** 2)

    # 활성치 이득 -- 회전 전후 둘 다. 둘의 차이가 설계 충돌의 크기다.
    gb = ga = 0.0
    if act_man is not None:
        for name, W in T:
            X, _ = activations.load_probes(name, W.shape[1], cache_dir)
            if X is None:
                continue
            H = _rotation(W.shape[1])
            gb += coding_gain((X ** 2).mean(1)) * W.size
            ga += coding_gain(((H.T @ X) ** 2).mean(1)) * W.size
        gb /= tot
        ga /= tot

    scale_ov = ov_sum / tot          # fp16 블록 스케일의 실제 가중 평균 비용
    return {"split": split, "e8": e8, "h_x": h_x, "h_gauss": h_g,
            "r_gauss": r_gauss, "slb": slb, "scale_overhead": scale_ov,
            "gain_unrotated": gb, "gain_rotated": ga,
            "activations": None if act_man is None else act_man["source"],
            "act_synthetic": None if act_man is None else act_man["synthetic"],
            "weights_synthetic": weights.manifest(cache_dir)["synthetic"]}


def main() -> int:
    ap = argparse.ArgumentParser(description="압축의 이론적 한계와 그 한계가 선 가정")
    ap.add_argument("--split", default="holdout", choices=["holdout", "design", "all"])
    ap.add_argument("--cache", default=None)
    a = ap.parse_args()
    r = report(a.split, Path(a.cache) if a.cache else None)

    if r["weights_synthetic"]:
        print("⚠ 합성 가중치다. 실제 코덱 성능도, 실제 하한도 아니다.")
    if r["act_synthetic"]:
        print("⚠ 합성 활성치다. 아래 '활성치 이득'은 내가 넣은 outlier 구조를 되잰 값이다.")
    print()
    print(f"목표 왜곡  e = int8 의 가중치 상대오차 = {r['e8']:.5f}")
    print(f"회전 후 분포  h(X) = {r['h_x']:.4f} bits  (같은 분산 가우시안 {r['h_gauss']:.4f})")
    print()
    ov = r["scale_overhead"]
    print(f"{'':44}{'bits/weight':>13}{'압축':>8}")
    rows = [
        ("(A) 가우시안 R(D) = -log2(e)  ← 하한 아님, 상한", r["r_gauss"] + ov),
        ("(B) 섀넌 하한 SLB  ← i.i.d. 가정 하의 하한", r["slb"] + ov),
    ]
    if r["activations"] is not None:
        rows.append(("(C) 활성치를 아는 하한 (회전 없이)",
                     r["slb"] - r["gain_unrotated"] + ov))
        rows.append(("(C') 활성치를 아는 하한 (회전 후 남는 이득만)",
                     r["slb"] - r["gain_rotated"] + ov))
    for label, v in rows:
        print(f"{label:44}{v:>13.3f}{16 / v:>7.2f}x")

    if r["activations"] is not None:
        print()
        print(f"변환 부호화 이득  회전 전 {r['gain_unrotated']:.3f} bits  ->  "
              f"회전 후 {r['gain_rotated']:.3f} bits")
        lost = r["gain_unrotated"] - r["gain_rotated"]
        if r["gain_unrotated"] > 0:
            print(f"  회전이 활성치 이득의 {lost / r['gain_unrotated']:.0%} 를 파괴한다 "
                  f"({lost:.3f} bits). 회전과 활성치 비트배분은 서로를 깎는다 --")
            print(f"  둘 다 가지려면 부분 이동(AWQ/SmoothQuant 의 α) 같은 중간점이 필요하다.")
    print()
    print("어느 것도 '진짜 하한'이 아니다. 남은 가정: i.i.d.(실측으로 깨짐, 약 0.065 bits),")
    print("그리고 'W 를 복원해야 한다'(함수만 같으면 되므로 하한 자체가 정의되지 않는다).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
