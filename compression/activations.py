"""레이어에 실제로 들어오는 활성치를 모은다 -- 심판이 왜곡을 재는 방향을 정한다.

왜 필요한가. 지금 심판은 `X ~ N(0, I)` 로 `‖W·X − W'·X‖ / ‖W·X‖` 를 잰다. X 가 등방이면
이 값은 `‖ΔW‖_F / ‖W‖_F` 로 떨어진다(실측 비율 0.96) -- 즉 "함수 오차"라고 이름 붙인 축이
사실은 가중치 오차이고, 축이 둘인 척하지만 정보는 하나다.

그런데 우리가 실제로 풀려는 문제는 이것이 아니다:

    푼 문제   : W 를 압축해 **W 를 MSE 작게** 복원하라
    진짜 문제 : W 를 압축해 **실제로 들어오는 x 에 대해 W·x 를** 보존하라

한 번도 들어오지 않는 x 방향은 아예 안 지켜도 된다. 활성치 공분산이 등방이면 두 문제가
같아지지만, 실제 LLM 활성치는 강하게 비등방이다 -- 소수 채널이 나머지보다 수십 배 크다
(LLM.int8() 이 보고한 outlier 채널). 그 구조를 심판에 넣지 않으면, 심판은 "모든 입력
방향이 똑같이 중요하다"는 틀린 가정 위에서 채점한다.

측정으로 확인한 것: outlier 채널 8/256 을 30배로 두면 int8 의 오차가 0.0256 -> 0.0316 으로
23% 늘고, 활성치를 아는 코덱(AWQ 식 채널 스케일링)은 같은 8비트에서 오차를 1.96배 줄인다.
등방 X 앞에서는 그 1.96배가 **정확히 0 으로 보인다** -- 스케일 지수가 항등원이 되기 때문이다.

무엇을 저장하는가. 공분산을 모델링하지 않고 **실제 활성치 벡터 표본을 그대로** 둔다.
(n_in, N_PROBE) float32 한 장이면 심판이 그대로 곱해 쓸 수 있고, 공분산 추정/제곱근 같은
중간 단계가 없어 "무엇을 가정했는가"가 파일 하나로 드러난다.

두 갈래로 만든다:
  capture()   -- VM 에서. transformers 로 모델을 돌리며 각 Linear 의 **입력**을 후킹한다.
                 이 컨테이너에는 torch 도 없고 huggingface 로 나가지도 못한다.
  synthesize()-- 여기서. 배관 시험용. 실제 활성치가 아니고 그 사실이 manifest 에 남는다.

주의: 텐서마다 들어오는 활성치가 다르다. q/k/v/gate/up 의 입력은 RMSNorm 출력이지만
down_proj 의 입력은 `SiLU(gate) ⊙ up` 이라 두 사영의 곱이고 꼬리가 훨씬 두껍다. o_proj 의
입력은 softmax 가중평균이라 분산이 작다. 그래서 텐서 이름마다 따로 저장한다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import weights  # noqa: E402

N_PROBE = 256            # 활성치 표본 벡터 수. n_in 차원 공간을 어느 정도 덮어야 한다
ACT_SUFFIX = ".act.npy"
ACT_MANIFEST = "activations.json"
STATS_FILE = "activation_stats.npz"

# 배관 시험용 합성 활성치의 outlier 구조. 실제로 관측되는 모양을 흉내 낸다 --
# 소수 채널만 크고, 그 채널이 어디인지는 텐서마다 다르다.
SYN_HOT_FRACTION = 1 / 32
SYN_HOT_SCALE = 30.0


def _slug(name: str) -> str:
    return name.replace("/", "_") + ACT_SUFFIX


def manifest(cache_dir: Path = None) -> dict | None:
    cache_dir = Path(cache_dir or weights.CACHE_DIR)
    p = cache_dir / ACT_MANIFEST
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def export_stats(cache_dir: Path = None, out: Path = None) -> Path:
    """활성치 표본에서 **채널별 RMS 만** 뽑아 한 파일로 낸다.

    이것이 VM 의존을 끊는 조각이다. 전체 표본은 텐서당 (n_in x 256) float32 = 896 폭에서
    918KB 라 스무 개면 20MB 다. 채널별 RMS 는 텐서당 n_in 개 실수 = 3.5KB, 전부 합쳐
    100KB 아래다 -- 저장소에 넣을 수 있다.

    무엇을 잃는가: 채널 간 상관이 빠진다. 다만 변환 부호화 이득 0.5·log2(AM/GM) 도,
    AWQ 식 채널 스케일링도 대각(채널별 크기)만 본다. 그 목적에는 손실이 없고, 심판의
    함수 오차에는 근사다. 그래서 출처를 'activation_stats' 로 따로 표시한다 -- 전체
    표본으로 잰 것과 섞이지 않게.
    """
    cache_dir = Path(cache_dir or weights.CACHE_DIR)
    man = manifest(cache_dir)
    if man is None:
        raise RuntimeError("활성치가 없다. capture 나 synthetic 을 먼저 돌려라.")
    out = Path(out or cache_dir / STATS_FILE)
    data = {}
    for t in man["tensors"]:
        X = np.load(cache_dir / _slug(t["name"]))
        data[t["name"]] = np.sqrt((X.astype(np.float64) ** 2).mean(1)).astype(np.float32)
    data["__meta__"] = np.array(json.dumps(
        {"source": man["source"], "synthetic": man["synthetic"],
         "n_probe": man.get("n_probe", N_PROBE)}, ensure_ascii=False))
    np.savez_compressed(out, **data)
    return out


def _stats(cache_dir: Path):
    p = Path(cache_dir) / STATS_FILE
    if not p.is_file():
        return None
    return np.load(p, allow_pickle=False)


def stats_meta(cache_dir: Path = None) -> dict | None:
    z = _stats(Path(cache_dir or weights.CACHE_DIR))
    if z is None:
        return None
    return json.loads(str(z["__meta__"]))


def load_probes(name: str, n_in: int, cache_dir: Path = None):
    """텐서 하나의 활성치 표본과 그 출처.

    세 단계로 물러난다:
      1. 전체 표본 `.act.npy` 가 있으면 그것 ("activations")
      2. 없고 채널별 RMS 만 있으면 그것으로 만들어 쓴다 ("activation_stats")
      3. 둘 다 없으면 None -- 심판이 등방 가우시안으로 물러난다

    2단계는 채널 간 상관을 버린 근사다. 그래도 등방보다 낫다 -- 활성치의 값어치는
    "어느 채널이 큰가"에서 나오고 그건 대각에 다 들어 있다.
    """
    cache_dir = Path(cache_dir or weights.CACHE_DIR)
    p = cache_dir / _slug(name)
    if p.is_file():
        X = np.load(p)
        if X.ndim != 2 or X.shape[0] != n_in:
            raise ValueError(f"활성치 모양이 가중치와 안 맞는다: {name} {X.shape}, n_in={n_in}")
        return np.ascontiguousarray(X, dtype=np.float32), "activations"

    z = _stats(cache_dir)
    if z is not None and name in z:
        rms = z[name].astype(np.float32)
        if rms.size != n_in:
            raise ValueError(f"활성치 통계 길이가 안 맞는다: {name} {rms.size} != {n_in}")
        h = int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(20260902 + h)     # 이름으로 고정 -- 점수가 흔들리면 안 된다
        X = rng.standard_normal((n_in, N_PROBE)).astype(np.float32) * rms[:, None]
        return X, "activation_stats"

    return None, None


def synthesize(cache_dir: Path = None, seed: int = 20260902, n_probe: int = N_PROBE) -> dict:
    """배관 시험용 합성 활성치. **실제 활성치가 아니다.**

    캐시에 있는 각 가중치의 입력 차원에 맞춰 (n_in, n_probe) 를 만든다. 채널 일부만 크게
    두어 비등방을 넣는다 -- 등방으로 만들면 이 파일이 있으나 없으나 점수가 같아져서
    배관 시험이 아무것도 시험하지 않는다."""
    cache_dir = Path(cache_dir or weights.CACHE_DIR)
    man = weights.manifest(cache_dir)
    saved = []
    for t in man["tensors"]:
        n_in = int(t["shape"][1])
        # 텐서 이름으로 시드를 갈라 outlier 위치가 텐서마다 다르게 한다
        rng = np.random.default_rng(seed + (hash(t["name"]) & 0xFFFF))
        s = np.ones(n_in, dtype=np.float32)
        k = max(1, int(round(n_in * SYN_HOT_FRACTION)))
        s[rng.choice(n_in, k, replace=False)] = SYN_HOT_SCALE
        X = (rng.standard_normal((n_in, n_probe)).astype(np.float32) * s[:, None])
        np.save(cache_dir / _slug(t["name"]), X)
        saved.append({"name": t["name"], "shape": [n_in, n_probe]})
    out = {"source": "synthetic", "synthetic": True, "n_probe": n_probe,
           "hot_fraction": SYN_HOT_FRACTION, "hot_scale": SYN_HOT_SCALE, "tensors": saved}
    (cache_dir / ACT_MANIFEST).write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    return out


def capture(repo: str = weights.DEFAULT_REPO, cache_dir: Path = None,
            n_probe: int = N_PROBE, texts: "list[str]" = None,
            max_tokens: int = 4096) -> dict:
    """**VM 전용.** 모델을 실제로 돌리며 각 Linear 의 입력을 후킹해 표본을 모은다.

    이 컨테이너에서는 못 돈다(torch 없음, huggingface 차단). 네트워크와 torch 가 있는
    곳에서 `python3 compression/activations.py capture` 로 한 번 돌린다."""
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as e:
        raise RuntimeError(
            "capture 는 torch 와 transformers 가 필요하다. 이 컨테이너에는 없다 -- "
            f"VM 에서 돌려라. ({e})") from e

    cache_dir = Path(cache_dir or weights.CACHE_DIR)
    man = weights.manifest(cache_dir)
    if man.get("synthetic"):
        raise RuntimeError("가중치가 합성이다. weights.py fetch 를 먼저 돌려라 -- "
                           "합성 가중치에 실제 활성치를 붙이면 둘이 무관해진다")

    # 어떤 모듈의 입력이 필요한가. 저장된 텐서 이름에서 모듈 경로를 되돌린다.
    # model.layers.3.mlp.down_proj.weight   -> model.layers.3.mlp.down_proj
    # model.embed_tokens.rows512.weight     -> lm_head (묶인 임베딩의 입력은 마지막 은닉상태)
    want = {}
    for t in man["tensors"]:
        n = t["name"]
        if ".rows" in n:
            want.setdefault("lm_head", []).append(n)
        else:
            want.setdefault(n[:-len(".weight")], []).append(n)

    tok = AutoTokenizer.from_pretrained(repo)
    model = AutoModelForCausalLM.from_pretrained(repo, torch_dtype=torch.float32)
    model.eval()

    texts = texts or _DEFAULT_TEXTS
    seen: dict = {}

    def hook(mod_name):
        def fn(_mod, args):
            x = args[0]
            if x is None:
                return
            flat = x.reshape(-1, x.shape[-1]).detach().float()
            buf = seen.setdefault(mod_name, [])
            if sum(b.shape[0] for b in buf) < max_tokens:
                buf.append(flat.cpu())
        return fn

    handles = []
    named = dict(model.named_modules())
    for mod_name in want:
        if mod_name not in named:
            print(f"  ⚠ 모듈을 못 찾았다: {mod_name}")
            continue
        handles.append(named[mod_name].register_forward_pre_hook(hook(mod_name)))

    with torch.no_grad():
        for text in texts:
            ids = tok(text, return_tensors="pt", truncation=True, max_length=512)
            model(**ids)
    for h in handles:
        h.remove()

    rng = np.random.default_rng(20260902)
    saved = []
    for mod_name, tensor_names in want.items():
        if mod_name not in seen:
            continue
        allx = np.concatenate([b.numpy() for b in seen[mod_name]], axis=0)   # (tokens, n_in)
        idx = rng.choice(allx.shape[0], min(n_probe, allx.shape[0]), replace=False)
        X = np.ascontiguousarray(allx[idx].T, dtype=np.float32)              # (n_in, n_probe)
        for tname in tensor_names:
            np.save(cache_dir / _slug(tname), X)
            saved.append({"name": tname, "shape": list(X.shape), "module": mod_name,
                          "tokens_seen": int(allx.shape[0])})
            print(f"  {tname} <- {mod_name} {X.shape} (토큰 {allx.shape[0]}개에서 표본)")

    out = {"source": repo, "synthetic": False, "n_probe": n_probe,
           "n_texts": len(texts), "tensors": saved}
    (cache_dir / ACT_MANIFEST).write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    return out


_DEFAULT_TEXTS = [
    "The quick brown fox jumps over the lazy dog. " * 8,
    "In information theory, the rate-distortion function gives the minimum number of bits "
    "per symbol required to reconstruct a source within a given distortion. " * 4,
    "def quicksort(a):\n    if len(a) <= 1:\n        return a\n    p = a[len(a)//2]\n"
    "    return quicksort([x for x in a if x < p]) + [x for x in a if x == p] + "
    "quicksort([x for x in a if x > p])\n" * 4,
    "양자화는 연속적인 값을 유한한 개수의 대표값으로 바꾸는 과정이다. "
    "신경망 가중치를 8비트 정수로 바꾸면 메모리가 절반이 된다. " * 4,
    "1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584. " * 6,
]


def main() -> int:
    ap = argparse.ArgumentParser(description="심판이 쓸 활성치 표본")
    ap.add_argument("action", choices=["capture", "synthetic", "stats", "list"])
    ap.add_argument("--repo", default=weights.DEFAULT_REPO)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--n-probe", type=int, default=N_PROBE)
    a = ap.parse_args()
    cache = Path(a.cache) if a.cache else weights.CACHE_DIR

    if a.action == "stats":
        out = export_stats(cache)
        z = np.load(out, allow_pickle=False)
        n = len([k for k in z.files if k != "__meta__"])
        print(f"채널별 RMS 를 뽑았다 -> {out} ({out.stat().st_size/1024:.0f}KB, 텐서 {n}개)")
        print(f"메타: {stats_meta(cache)}")
        print("이 파일 하나면 다른 곳에서도 실제 활성치 방향으로 채점할 수 있다.")
        return 0

    if a.action == "capture":
        m = capture(a.repo, cache, a.n_probe)
        export_stats(cache)
        print(f"채널별 RMS 도 함께 뽑았다 -> {cache / STATS_FILE}")
    elif a.action == "synthetic":
        m = synthesize(cache, n_probe=a.n_probe)
        print("합성 활성치를 만들었다 -- 실제 활성치가 아니다. 배관 시험용.")
    else:
        m = manifest(cache)
        if m is None:
            print("활성치가 없다. 심판은 등방 가우시안으로 물러난다.")
            return 1

    for t in m["tensors"]:
        print(f"  {t['name']:52} {tuple(t['shape'])}")
    print(f"source={m['source']} synthetic={m['synthetic']} 텐서 {len(m['tensors'])}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
