"""문제 생성기 심판(mathgen/judge.py)의 red-green 검사.

무엇을 지키려는가: **심판이 채점을 실제로 하는가.** 압축 심판에서 배운 것 그대로다 --
헛도는 심판은 모든 것을 통과시키면서 겉으로는 멀쩡해 보이고, 그 위에 올린 자가개선 루프는
아무 방향으로나 굴러간다.

카나리(전부 실격이어야 한다):
  1. 답 흘리기    문제문에 정답을 적어둔다
  2. 틀린 답      어렵기만 하고 검증을 안 했다
  3. 비결정성    같은 seed 에 다른 문제 (점수가 흔들리면 래칫이 무너진다)
  4. 퇴화        ∫7 dx 처럼 문제가 아닌 것
  5. 전역 은닉    전역 변수로 검증기에 신호를 보내려 한다
대조군:
  6. baseline_poly   정당하지만 sympy 가 즉시 푼다 -> **비자명성에서 떨어져야** 한다
  7. backward_hard   세 축을 모두 넘으므로 **통과해야** 한다
     (심판이 아무것도 통과시키지 못하면 그것도 고장이다)

그리고 세 축이 서로를 대체하지 못하는지도 본다 -- 축 하나를 빼면 어떤 카나리가 살아나는지.

LLM 도 네트워크도 쓰지 않는다. sympy 만 쓴다.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "mathgen"))

import judge  # noqa: E402

CHEATS = REPO / "tests" / "fixtures" / "cheat_generators"
SEEDS = REPO / "mathgen" / "seeds"
FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def _rejected(path: Path, seeds=(0, 1)) -> tuple:
    """실격이거나 판정 미달이면 (True, 사유). 통과해버리면 (False, 사유)."""
    try:
        res = judge.evaluate(path, seeds=seeds)
        return (not res["passed"]), res["reason"]
    except judge.GeneratorFailure as e:
        return True, f"실격: {e}"


def test_cheats_are_rejected() -> None:
    """부정행위 생성기 5종이 전부 막히는가."""
    cases = {
        "leak_answer.py": "답 흘리기",
        "wrong_answer.py": "틀린 답",
        "nondeterministic.py": "비결정성",
        "degenerate.py": "퇴화",
        "global_stash.py": "전역 은닉",
    }
    for name, label in cases.items():
        ok, why = _rejected(CHEATS / name)
        check(ok, f"{label}({name}) 를 통과시켰다")
        if ok:
            print(f"    [막힘] {label:10} -- {why[:78]}")


def test_machine_solvable_is_rejected() -> None:
    """정당하지만 sympy 가 즉시 푸는 생성기는 통과하면 안 된다.

    이것이 '어려운 문제'의 최소 조건이다. 답이 맞기만 하면 되는 심판은 교과서 연습문제를
    무한히 찍어내고 끝난다."""
    ok, why = _rejected(SEEDS / "baseline_poly.py", seeds=(0, 1, 2))
    check(ok, f"sympy 가 바로 푸는 생성기를 통과시켰다: {why}")
    check("비자명성" in why, f"기각 사유가 비자명성이어야 한다: {why}")


def test_hard_generator_passes() -> None:
    """세 축을 넘는 생성기는 통과해야 한다 -- 전부 막는 심판도 고장이다."""
    res = judge.evaluate(SEEDS / "backward_hard.py", seeds=(0, 1, 2, 3))
    check(res["passed"], f"정당한 어려운 생성기를 통과시키지 못한다: {res['reason']}")
    m = res["mean"]
    check(m["sound"] == 1.0, "정당성이 100% 여야 한다(전제 확인)")
    check(m["machine_solved"] == 0.0, "sympy 가 못 풀어야 한다(전제 확인)")


def test_verification_is_asymmetric() -> None:
    """검증이 푸는 것보다 싼가 -- 이 심판이 성립하는 전제다.

    답을 미분해 확인하는 것은 즉시 끝나지만, 같은 식을 적분해 되찾는 것은 sympy 가
    시간 안에 못 한다. 그 격차가 없으면 '심판이 후보보다 싸다'가 무너지고, 채점이
    푸는 것만큼 비싸지면 탐색 루프 자체가 성립하지 않는다."""
    res = judge.score_generator(SEEDS / "backward_hard.py", seeds=(0, 1))
    for r in res["instances"]:
        check(r["sound"] == 1.0, f"seed {r['seed']}: 미분 검증이 통과해야 한다")
        check(r["machine_solved"] == 0.0,
              f"seed {r['seed']}: 적분은 실패해야 한다 -- 비대칭이 없으면 심판이 무의미하다")


def test_compressibility_separates_structure_from_tedium() -> None:
    """압축성 축이 '구조가 숨은 것'과 '계산만 긴 것'을 실제로 가르는가.

    절대 길이(단계 수 <= K)로 재면 이미 구조를 아는 문제만 통과한다. 비율로 재면
    지저분해도 되고 압축되지 않는 지저분함만 막힌다 -- 그 구별이 실제로 일어나는지 본다.

    backward_hard 의 두 족은 압축비가 갈린다(실측): 근호 나눗셈 약 0.44,
    이중 지수 약 1.77. 같은 심판이 둘을 다르게 읽는다는 것이 축이 살아 있다는 뜻이다."""
    res = judge.score_generator(SEEDS / "backward_hard.py", seeds=(0, 1, 2, 3))
    ratios = [r["compress_ratio"] for r in res["instances"]]
    lo, hi = min(ratios), max(ratios)
    check(hi / max(lo, 1e-9) > 2.0,
          f"압축비가 족을 구별하지 못한다: {[round(r, 3) for r in ratios]}")
    check(lo < 1.0 < hi,
          f"1.0(풀이=문제 분량) 을 사이에 두고 갈려야 한다: {lo:.3f} ~ {hi:.3f}")


def test_ratchet_needs_a_baseline() -> None:
    """압축성은 절대값이 아니라 기준선 대비로 걸린다.

    압축에서 배운 것과 같다 -- bits/weight 절대값이 의미 없었듯, 풀이 단계 수 절대값도
    의미가 없다. 기준선을 주면 그보다 나쁜 것이 걸려야 한다."""
    hard = SEEDS / "backward_hard.py"
    res = judge.evaluate(hard, baseline=hard, seeds=(0, 1))
    check(not res["passed"], "자기 자신을 기준선으로 주면 압축성에서 걸려야 한다(동률)")
    check("압축성" in res["reason"], f"기각 사유가 압축성이어야 한다: {res['reason']}")


def main() -> int:
    for fn in (test_cheats_are_rejected, test_machine_solvable_is_rejected,
               test_hard_generator_passes, test_verification_is_asymmetric,
               test_compressibility_separates_structure_from_tedium,
               test_ratchet_needs_a_baseline):
        fn()
    if FAILURES:
        print("실패:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("문제 생성 심판: 부정행위 5종 실격, 기계풀이 기각, 어려운 생성기 통과, "
          "검증 비대칭, 압축성 분리, 래칫 -- 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
