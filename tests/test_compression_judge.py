"""
압축 코덱 심판(compression/judge.py)의 red-green 검사.

무엇을 지키려는가: **심판이 채점을 실제로 하는가.** orchestrator/MANUAL.md 가 실측으로
보인 것처럼, 헛도는 심판은 모든 것을 통과시키면서도 겉으로는 멀쩡해 보인다. 이 심판은
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
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "compression"))

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

    초록 사례가 int8_clip 에서 hadamard_int 로 바뀌었다. int8_clip 은 fp16 스케일로 비트를
    아끼지만 오차가 int8 보다 근소하게 크다 -- 예전 합성 데이터에서 이겨 보였던 것은 5번째
    자리의 잡음이었고, 종류와 크기가 다양한 지금 데이터에서는 두 split 모두에서 오차 축에
    진다. 회전 코덱은 같은 비트에서 오차를 실제로 줄이므로 마진이 잡음이 아니다."""
    res = judge.evaluate(CODECS / "hadamard_int.py")
    check(res["beats_int8"], f"정직한 개선안을 통과시키지 못한다: {res['reason']}")
    base = res["baseline_int8"]
    check(res["mean"]["bits_per_weight"] < base["bits_per_weight"], "압축력 비교가 틀렸다")
    check(res["mean"]["func_err"] < base["func_err"], "복원력 비교가 틀렸다")


def test_one_axis_win_is_not_enough() -> None:
    """한 축만 이기는 코덱은 어느 방향이든 통과하면 안 된다.

    양쪽 방향을 다 본다. 압축력만 이기는 쪽(3진, int8_clip)과 복원력만 이기는 쪽(fp16).
    한 방향만 시험하면 부등호를 뒤집은 심판을 못 잡는다."""
    for name in ("ternary_b158.py", "int8_clip.py"):
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

        ok, msg = nv.check({"codec_code": (CODECS / "hadamard_int.py").read_text(encoding="utf-8")}, {})
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


def main() -> int:
    for fn in (test_cheats_are_disqualified, test_bits_are_measured_not_claimed,
               test_honest_improvement_passes, test_one_axis_win_is_not_enough,
               test_injected_node_verifier, test_holdout_is_disjoint_from_design,
               test_split_is_stratified_by_kind, test_compression_denominator_is_source_dtype,
               test_mean_is_parameter_weighted):
        fn()
    if FAILURES:
        print("실패:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("압축 심판: 부정행위 5종 실격, 대조군 4종 판정, 셋 층화 분리, "
          "bf16 분모, 파라미터 가중 평균 -- 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
