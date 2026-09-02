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
  6. 원본 그대로 -- 오차 0 이지만 32 bits/weight. 실격은 아니고 **져야** 한다
     (비트를 코덱의 주장이 아니라 실제 blob 길이로 재는지 확인)
  7. int8_clip   -- 정직하게 두 축을 이기므로 **통과**여야 한다 (심판이 아무것도 통과시키지
     못하면 그것도 고장이다)
그리고 search.py 가 orchestrator 런에 주입하는 노드 심판이 같은 판정을 내는지도 확인한다.

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
    """정직하게 두 축을 이기는 코덱은 통과해야 한다 -- 전부 막는 심판도 고장이다."""
    res = judge.evaluate(CODECS / "int8_clip.py")
    check(res["beats_int8"], f"정직한 개선안을 통과시키지 못한다: {res['reason']}")
    base = res["baseline_int8"]
    check(res["mean"]["bits_per_weight"] < base["bits_per_weight"], "압축력 비교가 틀렸다")
    check(res["mean"]["func_err"] < base["func_err"], "복원력 비교가 틀렸다")


def test_one_axis_win_is_not_enough() -> None:
    """압축력만 이기는 코덱(3진)은 통과하면 안 된다."""
    res = judge.evaluate(CODECS / "ternary_b158.py")
    check(not res["beats_int8"],
          f"한 축만 이긴 코덱을 통과시켰다: {res['reason']}")
    check(res["mean"]["bits_per_weight"] < res["baseline_int8"]["bits_per_weight"],
          "3진 코덱이 압축력에서 이기고 있어야 한다(전제 확인)")


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

        ok, msg = nv.check({"codec_code": (CODECS / "int8_clip.py").read_text(encoding="utf-8")}, {})
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


def main() -> int:
    for fn in (test_cheats_are_disqualified, test_bits_are_measured_not_claimed,
               test_honest_improvement_passes, test_one_axis_win_is_not_enough,
               test_injected_node_verifier, test_holdout_is_disjoint_from_design):
        fn()
    if FAILURES:
        print("실패:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("압축 심판: 부정행위 5종 실격, 대조군 2종 판정, 셋 분리 -- 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
