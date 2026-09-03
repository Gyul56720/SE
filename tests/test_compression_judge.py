"""
압축 코덱 심판(compression/judge.py)의 red-green 검사.

무엇을 지키려는가: **심판이 채점을 실제로 하는가.** orchestrator/MANUAL.md 가 실측으로
보인 것처럼, 전부 통과시키는 심판은 모든 것을 통과시키면서도 겉으로는 멀쩡해 보인다. 이 심판은
자가개선 루프가 코덱을 밤새 고쳐 나갈 때 유일한 채택 기준이 되므로, 부정행위를 실제로
거부하는지 카나리로 확인해 둔다.

카나리(전부 실격이어야 한다):
  1. 전역 은닉    -- 원본을 모듈 전역에 두고 4바이트 blob 을 낸다
  2. 원본 재읽기  -- blob 에 원본 경로만 담는다
  3. 임시파일 은닉 -- 원본을 임시 디렉토리에 쓰고 경로만 담는다
  4. 비결정성    -- 실행마다 다른 blob (점수가 흔들리면 래칫이 무너진다)
  5. 모양 소실    -- decode 가 1차원을 돌려준다(비트는 아껴진다)
대조군:
  6. 원본 그대로  -- 오차 0 이지만 32 bits/weight. 실격은 아니고 **져야** 한다
     (비트를 코덱의 주장이 아니라 실제 blob 길이로 재는지 확인)
  7. hadamard_int -- 정직하게 두 축을 이기므로 **통과**여야 한다 (심판이 아무것도 통과시키지
     못하면 그것도 고장이다)
  8. ternary/int8_clip -- 압축력만 이긴다. fp16 -- 복원력만 이긴다. 셋 다 **기각**이어야 한다
그리고 search.py 가 orchestrator 런에 주입하는 노드 심판이 같은 판정을 내는지도 확인한다.

집계 규약도 함께 지킨다:
  - 압축률의 분모는 원본 배포 비트폭(bf16 = 16)이지 fp32(32) 가 아니다
  - 텐서별 산술 평균이 아니라 파라미터 수 가중 평균이다
  - design/holdout 이 텐서 **종류**별로 층화돼 있다

LLM 도 네트워크도 쓰지 않는다. 가중치 캐시가 없으면 합성으로 만들어 배관만 시험한다.
"""
from __future__ import annotations

import importlib.util
import sys

import numpy as np
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "compression"))

import activations  # noqa: E402
import bounds  # noqa: E402
import rans  # noqa: E402
import judge  # noqa: E402
import weights  # noqa: E402

CHEATS = REPO / "tests" / "fixtures" / "cheat_codecs"
CODECS = REPO / "compression" / "codecs"
FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def _one_tensor():
    """채점에 쓸 행렬 하나. 캐시가 없으면 합성으로 만든다(배관 시험용)."""
    try:
        return weights.load("holdout")[0]
    except (FileNotFoundError, RuntimeError):
        weights.make_synthetic()
        return weights.load("holdout")[0]


def test_cheats_are_disqualified() -> None:
    name, W = _one_tensor()
    cases = [
        ("global_stash.py", "전역 은닉"),
        ("reread_original.py", "원본 재읽기"),
        ("tempfile_stash.py", "임시파일 은닉"),
        ("nondeterministic.py", "비결정성"),
        ("shape_loss.py", "모양 소실"),
    ]
    for filename, what in cases:
        try:
            res = judge.score_tensor(CHEATS / filename, name, W)
        except judge.CodecFailure:
            continue                                   # 정상 -- 실격시켰다
        FAILURES.append(
            f"{what}({filename}) 를 막지 못했다: {res['bits_per_weight']:.3f} bits/weight, "
            f"오차 {res['func_err']:.6f} 로 점수가 나왔다 -- 심판이 채점하지 않는다")


def test_bits_are_measured_not_claimed() -> None:
    """원본을 그대로 담은 코덱은 오차 0 이지만 32 bits/weight 라 져야 한다."""
    name, W = _one_tensor()
    res = judge.score_tensor(CHEATS / "raw_float32.py", name, W)
    check(res["func_err"] < 1e-6, f"원본 그대로인데 오차가 있다: {res['func_err']}")
    check(res["bits_per_weight"] > 31.9,
          f"실제 blob 길이가 아니라 다른 값으로 비트를 세고 있다: {res['bits_per_weight']}")


def test_honest_improvement_passes() -> None:
    """정직하게 두 축을 이기는 코덱은 통과해야 한다 -- 전부 막는 심판도 고장이다.

    통과 사례가 int8_clip 에서 hadamard_int 로 바뀌었다. int8_clip 은 fp16 스케일로 비트를
    아끼지만 오차가 int8 보다 근소하게 크다 -- 예전 합성 데이터에서 이겨 보였던 것은 5번째
    자리의 잡음이었고, 종류와 크기가 다양한 지금 데이터에서는 두 split 모두에서 오차 축에
    진다. 회전 코덱은 같은 비트에서 오차를 실제로 줄이므로 마진이 잡음이 아니다."""
    res = judge.evaluate(CODECS / "hadamard_rans.py")
    check(res["beats_int8"], f"정직한 개선안을 통과시키지 못한다: {res['reason']}")
    base = res["baseline_int8"]
    check(res["mean"]["bits_per_weight"] < base["bits_per_weight"], "압축력 비교가 틀렸다")
    check(res["mean"]["func_err"] < base["func_err"], "복원력 비교가 틀렸다")


def test_one_axis_win_is_not_enough() -> None:
    """한 축만 이기는 코덱은 어느 방향이든 통과하면 안 된다.

    양쪽 방향을 다 본다. 압축력만 이기는 쪽(3진)과 복원력만 이기는 쪽(fp16). 한 방향만
    시험하면 부등호를 뒤집은 심판을 못 잡는다.

    int8_clip 은 여기 넣지 않는다. 비트는 확실히 이기지만(8.070 < 8.138) 오차가 int8 과
    5번째 자리까지 동점이라, 왜곡을 등방으로 재느냐 활성치로 재느냐에 따라 판정이 뒤집힌다
    (등방에서는 기각, 활성치에서는 통과). 마진이 잡음인 코덱을 red 사례로 박아두면 지표를
    손볼 때마다 테스트가 깨진다. 대신 그 사실 자체를 README 에 적어 둔다."""
    for name in ("ternary_b158.py",):
        res = judge.evaluate(CODECS / name)
        check(not res["beats_int8"], f"{name}: 한 축만 이긴 코덱을 통과시켰다: {res['reason']}")
        check(res["mean"]["bits_per_weight"] < res["baseline_int8"]["bits_per_weight"],
              f"{name}: 압축력에서 이기고 있어야 한다(전제 확인)")
        check(res["mean"]["func_err"] >= res["baseline_int8"]["func_err"],
              f"{name}: 복원력에서 지고 있어야 한다(전제 확인)")

    res = judge.evaluate(CODECS / "fp16.py")
    check(not res["beats_int8"], f"복원력만 이긴 코덱을 통과시켰다: {res['reason']}")
    check(res["mean"]["func_err"] < res["baseline_int8"]["func_err"],
          "fp16 이 복원력에서 이기고 있어야 한다(전제 확인)")
    check(res["mean"]["bits_per_weight"] >= res["baseline_int8"]["bits_per_weight"],
          "fp16 이 압축력에서 지고 있어야 한다(전제 확인)")


def test_injected_node_verifier() -> None:
    """search.py 가 orchestrator 런에 심는 심판이 실제로 판정하는가.

    이것이 축 A(밖에서 주입한 심판)의 실물이다. LLM 이 쓴 채점표를 버리고 judge 를 부르는
    파일을 런 디렉토리에 깔아 plan.json 의 verifier 를 갈아끼운다. 그 파일이 제대로
    판정하지 못하면 루프 전체가 헛돈다."""
    import shutil
    import tempfile

    sys.path.insert(0, str(REPO / "compression"))
    import search

    run = Path(tempfile.mkdtemp(prefix="node_verifier_test_"))
    try:
        design = judge.score_codec(search.ensure_champion(), "design")["mean"]
        rel = search._plant_verifier(run, design["bits_per_weight"], design["func_err"])
        check(rel.endswith("#check"), f"주입 경로가 이상하다: {rel}")

        spec = importlib.util.spec_from_file_location("_nv", run / "verifiers" / "codec_check.py")
        nv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(nv)

        ok, msg = nv.check({"codec_code": (CODECS / "hadamard_rans.py").read_text(encoding="utf-8")}, {})
        check(ok, f"챔피언을 이긴 코덱을 통과시키지 못한다: {msg}")

        ok, msg = nv.check({"codec_code": (CODECS / "ternary_b158.py").read_text(encoding="utf-8")}, {})
        check(not ok, "한 축만 이긴 코덱을 통과시켰다")

        ok, msg = nv.check({"answer": 42}, {})
        check(not ok, "codec_code 가 없는 출력을 통과시켰다")

        ok, msg = nv.check({"codec_code": (CHEATS / "global_stash.py").read_text(encoding="utf-8")}, {})
        check(not ok, "부정행위 코덱을 통과시켰다")
    finally:
        shutil.rmtree(run, ignore_errors=True)


def test_holdout_is_disjoint_from_design() -> None:
    """설계셋과 평가셋이 겹치면 과적합한 코덱이 이긴다."""
    design = {n for n, _ in weights.load("design")}
    holdout = {n for n, _ in weights.load("holdout")}
    check(bool(design) and bool(holdout), "설계셋/평가셋 중 하나가 비었다")
    check(not (design & holdout), f"설계셋과 평가셋이 겹친다: {design & holdout}")


def test_split_is_stratified_by_kind() -> None:
    """텐서 **종류**가 한쪽 split 에 통째로 몰리면 안 된다.

    down_proj 가 전부 design 에 들어가면 down_proj 에 과적합한 코덱을 holdout 이 못 잡는다
    -- 본 적 없는 종류를 못 봤으니까. 회전 코덱이 들어오면 이 구멍이 더 커진다: 회전 행렬은
    차원마다 다르고 차원은 종류를 따라가므로, 종류가 한쪽에 몰리면 그 차원의 회전이 아예
    검증되지 않는다."""
    kinds = {}
    for split in ("design", "holdout"):
        for name, _ in weights.load(split):
            kinds.setdefault(weights._kind(name), set()).add(split)
    check(len(kinds) > 1, f"종류가 하나뿐이라 층화를 시험할 수 없다: {list(kinds)}")
    for kind, where in sorted(kinds.items()):
        # 종류에 텐서가 2개 이상이면 양쪽에 다 나타나야 한다
        n = sum(1 for sp in ("design", "holdout")
                for nm, _ in weights.load(sp) if weights._kind(nm) == kind)
        if n >= 2:
            check(where == {"design", "holdout"},
                  f"종류 '{kind}'({n}개)가 {where} 한쪽에만 있다 -- 층화가 안 됐다")


def test_compression_denominator_is_source_dtype() -> None:
    """압축배율의 분모는 원본 배포 비트폭이다. bf16 모델을 fp32 로 재면 배율이 2배 부푼다.

    예전 코드는 32.0/bits 로 박혀 있어서 int8 이 3.9배로 표시됐다. 실제 모델은 bf16 으로
    배포되므로 1.97배가 맞다. fp16 코덱이 "2배 압축"으로 보이던 것이 같은 착시였다 --
    bf16 원본을 fp16 으로 바꾸는 것은 압축이 아니다."""
    sb = weights.source_bits()
    check(sb == 16, f"합성/실제 가중치의 원본 비트폭이 16 이어야 한다: {sb}")

    res = judge.score_codec(CODECS / "int8.py", "holdout")
    m = res["mean"]
    check(abs(m["compression_x"] - sb / m["bits_per_weight"]) < 1e-9,
          f"압축배율이 분모 {sb} 와 맞지 않는다: {m['compression_x']}")
    check(1.9 < m["compression_x"] < 2.05,
          f"int8 의 압축배율은 bf16 대비 약 1.97 이어야 한다: {m['compression_x']:.3f}")

    fp = judge.score_codec(CODECS / "fp16.py", "holdout")["mean"]
    check(abs(fp["compression_x"] - 1.0) < 0.05,
          f"fp16 은 bf16 원본 대비 압축이 아니다(1.0x): {fp['compression_x']:.3f}")


def test_mean_is_parameter_weighted() -> None:
    """집계는 텐서별 산술 평균이 아니라 파라미터 수 가중 평균이다.

    산술 평균은 작은 텐서와 큰 텐서에 같은 표를 준다. Qwen2.5-0.5B 한 레이어에서 MLP 가
    87.7%, q+o 가 10.8%, GQA 라 k+v 는 1.5% 인데 그것들을 동급으로 세면 작은 텐서에만
    좋은 코덱이 이긴다. 가중 평균의 bits/weight 는 정의상 (전체 blob 비트)/(전체 파라미터)
    와 같아서, "이 코덱으로 모델을 담으면 몇 비트인가"라는 원래 묻고 싶던 값이 된다."""
    res = judge.score_codec(CODECS / "int8.py", "holdout")
    rows, m = res["tensors"], res["mean"]
    check(len({r["n_weights"] for r in rows}) > 1,
          "텐서 크기가 전부 같아 가중 평균과 산술 평균을 구별할 수 없다")

    total = sum(r["n_weights"] for r in rows)
    check(m["n_weights"] == total, "파라미터 총수가 맞지 않는다")

    want = sum(r["bits_per_weight"] * r["n_weights"] for r in rows) / total
    check(abs(m["bits_per_weight"] - want) < 1e-9,
          f"bits/weight 가 가중 평균이 아니다: {m['bits_per_weight']} != {want}")

    # 전체 blob 비트 / 전체 파라미터 와 같아야 한다
    blob_bits = sum(r["bits_per_weight"] * r["n_weights"] for r in rows)
    check(abs(m["bits_per_weight"] - blob_bits / total) < 1e-9,
          "bits/weight 가 (전체 blob 비트)/(전체 파라미터) 와 다르다")

    plain = sum(r["bits_per_weight"] for r in rows) / len(rows)
    check(abs(plain - m["bits_per_weight"]) > 1e-9,
          "가중 평균이 산술 평균과 같다 -- 가중이 실제로 걸리지 않았다")

    werr = sum(r["func_err"] * r["n_weights"] for r in rows) / total
    check(abs(m["func_err"] - werr) < 1e-9, "함수오차도 가중 평균이어야 한다")


def test_metric_rewards_activation_awareness() -> None:
    """활성치를 아는 코덱이 모르는 코덱을 **이길 수 있는 지표인가.**

    처음에는 "같은 코덱의 점수가 X 를 바꾸면 변하는가"를 시험했는데, 그건 틀린 성질이었다.
    실제 Qwen 가중치처럼 열마다 균일한 행렬에서는 ΔW 도 균일해서
    ‖ΔW·X‖ 와 ‖W·X‖ 가 같이 커지고 **비율이 거의 안 변한다**(실측 0.9%). 앞서 23% 가
    변했던 것은 내 합성 가중치에 행 내 outlier 가 과하게 들어 있었기 때문이다.

    활성치의 값어치는 점수가 흔들리는 데 있지 않고 **비트를 재배분할 수 있다**는 데 있다.
    그래서 시험할 것은 이것이다: 같은 비트에서 활성치를 아는 코덱(AWQ 식 채널 스케일링)이
    모르는 코덱을 이기는가, 그리고 **등방 지표는 그 이득을 못 보는가**.

    실측: 비등방 지표에서 1.81배 개선, 등방 지표에서는 0.83배 -- 등방 심판이라면 더 좋은
    코덱을 기각한다. 이 검사가 깨지면 심판이 활성치 인지 코덱을 보상하지 못한다는 뜻이고,
    그러면 자가개선 루프가 그 방향을 영영 못 찾는다."""
    name, W = _one_tensor()
    n_in = W.shape[1]
    Xa, _ = activations.load_probes(name, n_in)
    check(Xa is not None, "활성치가 없다 -- activations.py 를 먼저 돌려라")
    if Xa is None:
        return
    Xi = judge.isotropic_probes(n_in)

    def q(M):
        sc = np.abs(M).max(1, keepdims=True) / 127.0
        sc[sc == 0] = 1
        return (np.round(M / sc).clip(-127, 127) * sc).astype(np.float32)

    def rel(R, X):
        Y = W @ X
        return float(np.linalg.norm(Y - R @ X) / np.linalg.norm(Y))

    plain = q(W)
    s = np.maximum(np.sqrt((Xa ** 2).mean(1)) ** 0.25, 1e-12)
    aware = (q(W * s) / s).astype(np.float32)      # 같은 8비트. 스케일은 활성치에서 유도

    gain_a = rel(plain, Xa) / rel(aware, Xa)
    gain_i = rel(plain, Xi) / rel(aware, Xi)
    check(gain_a > 1.3,
          f"활성치 지표가 활성치 인지 코덱을 보상하지 않는다: {gain_a:.2f}배")
    check(gain_i < 1.05,
          f"등방 지표가 이 이득을 본다면 활성치 파일이 등방이다: {gain_i:.2f}배")


def test_metric_is_not_silently_mixed() -> None:
    """일부 텐서에만 활성치가 있으면 합계가 두 지표의 잡탕이 된다. 조용히 넘어가면 안 된다."""
    import shutil
    import tempfile
    src = Path(weights.CACHE_DIR)
    tmp = Path(tempfile.mkdtemp(prefix="mixed_probe_"))
    try:
        shutil.copytree(src, tmp / "cache")
        cache = tmp / "cache"
        victims = sorted(cache.glob("*" + activations.ACT_SUFFIX))
        check(len(victims) > 1, "활성치 파일이 없어 섞임을 시험할 수 없다")
        victims[0].unlink()                      # 한 텐서만 활성치를 없앤다
        try:
            judge.score_codec(CODECS / "int8.py", "all", cache)
            check(False, "지표가 섞였는데 그냥 점수를 냈다")
        except RuntimeError as e:
            check("섞인다" in str(e), f"섞임을 알리는 오류가 아니다: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_coding_gain_is_zero_for_isotropic() -> None:
    """변환 부호화 이득 0.5·log2(AM/GM) 이 등방에서 0 이고 비등방에서 양수인가.

    이 한 줄이 '등방 가정은 활성치 이득을 정의상 0 으로 만든다'는 주장의 실물이다.
    하한을 얼마나 내릴 수 있는지가 전부 이 값에 달려 있다."""
    check(abs(bounds.coding_gain(np.ones(256))) < 1e-9, "등방인데 이득이 0 이 아니다")

    v = np.ones(256)
    v[:8] = 30.0 ** 2
    g = bounds.coding_gain(v)
    check(g > 1.0, f"명백한 outlier 구조인데 이득이 작다: {g:.3f} bits")

    # 단조성: outlier 가 셀수록 이득이 커진다
    prev = -1.0
    for mag in (2.0, 10.0, 30.0, 100.0):
        w = np.ones(256)
        w[:8] = mag ** 2
        cur = bounds.coding_gain(w)
        check(cur > prev, f"배율 {mag} 에서 이득이 안 늘었다")
        prev = cur


def test_rans_roundtrip_and_determinism() -> None:
    """엔트로피 부호기가 **정확히** 복원하고 매번 같은 바이트를 내는가.

    부호기가 한 심볼이라도 흘리면 코덱이 조용히 틀린 가중치를 낸다 -- 심판은 그것을
    "오차가 큰 코덱"으로 볼 뿐 버그로 보지 않는다. 그리고 심판이 결정성을 검사하므로
    같은 입력에 같은 blob 이 아니면 실격이다.

    실제 텐서 모양을 그대로 시험한다. 레인 수를 심볼 수에서 유도하는데(레인마다 최종 상태
    4바이트가 blob 에 실린다) 작은 텐서에서 그 고정 비용이 이득을 삼킬 수 있어서다."""
    rng = np.random.default_rng(0)
    shapes = [(32, 224), (224, 224), (128, 896), (896, 896)]
    for rows, cols in shapes:
        n = rows * cols
        # 회전 후 코드의 모양: 가운데가 두꺼운 가우시안형
        sym = np.clip(np.round(rng.standard_normal(n) * 32) + 128, 0, 255).astype(np.int64)
        freq = rans.build_table(sym, 256)
        check(int(freq.sum()) == rans.M, f"{rows}x{cols}: 빈도 합이 M 이 아니다")
        check((freq[np.bincount(sym, minlength=256) > 0] > 0).all(),
              f"{rows}x{cols}: 쓰인 심볼에 빈도 0 이 있다 -- 부호화 불가")
        blob = rans.encode(sym, freq)
        check(np.array_equal(rans.decode(blob, n, freq), sym),
              f"{rows}x{cols}: 왕복이 깨진다")
        check(rans.encode(sym, freq) == blob, f"{rows}x{cols}: 결정론적이지 않다")

        p_ = np.bincount(sym, minlength=256) / n
        p_ = p_[p_ > 0]
        H = float(-(p_ * np.log2(p_)).sum())
        over = 8 * len(blob) / n - H
        check(over < 0.05, f"{rows}x{cols}: 엔트로피 초과가 크다 {over:.3f} bits")

    # 극단: 심볼 하나만, 그리고 아주 희소
    for sym in (np.zeros(50000, dtype=np.int64),
                rng.choice([7, 200], 50000, p=[0.97, 0.03]).astype(np.int64)):
        f = rans.build_table(sym, 256)
        check(np.array_equal(rans.decode(rans.encode(sym, f), sym.size, f), sym),
              "극단 분포에서 왕복이 깨진다")


def test_entropy_coding_only_moves_bits() -> None:
    """엔트로피 부호화는 **오차를 건드리면 안 된다.**

    hadamard_rans 는 hadamard_int 와 같은 코드를 더 짧게 담을 뿐이라 복원 결과가 비트
    단위로 같아야 한다. 오차가 달라지면 부호화 과정이 값을 바꾸고 있다는 뜻이다."""
    a = judge.score_codec(CODECS / "hadamard_int.py", "holdout")["mean"]
    b = judge.score_codec(CODECS / "hadamard_rans.py", "holdout")["mean"]
    check(abs(a["func_err"] - b["func_err"]) < 1e-9,
          f"엔트로피 부호화가 오차를 바꿨다: {a['func_err']:.8f} vs {b['func_err']:.8f}")
    check(b["bits_per_weight"] < a["bits_per_weight"] - 0.3,
          f"엔트로피 부호화가 비트를 충분히 못 줄였다: "
          f"{a['bits_per_weight']:.3f} -> {b['bits_per_weight']:.3f}")


def test_stats_fallback_keeps_direction() -> None:
    """전체 표본 없이 **채널별 RMS 만** 있어도 실제 방향으로 잴 수 있는가.

    이것이 VM 의존을 끊는 조각이다. 전체 표본은 텐서당 918KB 라 스무 개면 20MB 지만,
    채널별 RMS 는 전부 합쳐 24KB 라 저장소에 넣을 수 있다. 그러면 활성치를 뽑은 기계가
    없는 곳(이 컨테이너, CI)에서도 등방으로 물러나지 않는다.

    지키는 것 셋: 통계 경로가 실제로 쓰이는가, 출처가 'activations' 와 **구별되게**
    표시되는가(채널 간 상관을 버린 근사라 섞이면 안 된다), 그리고 등방보다 나은가."""
    import shutil
    import tempfile
    src = Path(weights.CACHE_DIR)
    tmp = Path(tempfile.mkdtemp(prefix="stats_only_"))
    try:
        cache = tmp / "cache"
        shutil.copytree(src, cache)
        activations.export_stats(cache)
        for f in cache.glob("*" + activations.ACT_SUFFIX):
            f.unlink()                                # 전체 표본을 없앤다
        (cache / activations.ACT_MANIFEST).unlink()

        name, W = weights.load("holdout", cache)[0]
        X, source = activations.load_probes(name, W.shape[1], cache)
        check(source == "activation_stats", f"통계 경로가 안 쓰인다: {source}")
        check(X is not None and X.shape[0] == W.shape[1], "통계에서 만든 표본 모양이 틀렸다")

        # 같은 이름이면 같은 표본이어야 한다 -- 점수가 실행마다 흔들리면 래칫이 무너진다
        X2, _ = activations.load_probes(name, W.shape[1], cache)
        check(np.array_equal(X, X2), "통계에서 만든 표본이 실행마다 다르다")

        # 등방이 아니어야 한다 (그러면 통계를 쓴 의미가 없다)
        rms = np.sqrt((X ** 2).mean(1))
        spread = float(rms.max() / max(rms.min(), 1e-12))
        check(spread > 2.0, f"통계에서 만든 표본이 사실상 등방이다: 채널 크기비 {spread:.1f}")

        res = judge.score_codec(CODECS / "int8.py", "holdout", cache)
        check(res["probe_source"] == "activation_stats",
              f"심판이 통계 출처를 표시하지 않는다: {res['probe_source']}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    for fn in (test_cheats_are_disqualified, test_bits_are_measured_not_claimed,
               test_honest_improvement_passes, test_one_axis_win_is_not_enough,
               test_injected_node_verifier, test_holdout_is_disjoint_from_design,
               test_split_is_stratified_by_kind, test_compression_denominator_is_source_dtype,
               test_mean_is_parameter_weighted, test_metric_rewards_activation_awareness,
               test_metric_is_not_silently_mixed, test_coding_gain_is_zero_for_isotropic,
               test_rans_roundtrip_and_determinism,
               test_entropy_coding_only_moves_bits,
               test_stats_fallback_keeps_direction):
        fn()
    if FAILURES:
        print("실패:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("압축 심판: 부정행위 5종 실격, 대조군 4종 판정, 셋 층화 분리, bf16 분모, "
          "파라미터 가중 평균, 활성치 방향, rANS 왕복 -- 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
