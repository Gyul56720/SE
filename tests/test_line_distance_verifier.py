"""두 직선 최단거리 문제의 외부 심판 검사.

**이 파일은 오케스트레이터가 보지 않는다.** repair_node 가 노드에 보여주는 것은 문제
기술서와 verify.py 뿐이다. 여기서 쓰는 무식한 수치 최소화는 심판이 초록 사례를 실제로
통과시키는지 확인하려는 것이지, 풀이를 저장소에 남기려는 것이 아니다.

무엇을 지키는가:
  1. 명백히 틀린 답을 거부한다
  2. **맞는 답을 받아들인다** -- 전부 거부하는 심판도 고장이다
  3. 퇴화한 경우(평행/일치)에도 최소점이면 받아들인다. 유일해를 강요하지 않는다
  4. 일차 조건만 겨우 맞춘 가짜를 섭동 검사가 잡는다

수치 최소화만 쓴다. 정규방정식도 외적 공식도 여기에 없다 -- 심판이 특정 풀이법에
묶이지 않는다는 것을 이 파일 자체가 보인다.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROB = REPO / "orchestrator" / "problems" / "line_distance"
sys.path.insert(0, str(PROB))

import verify  # noqa: E402

CASES = json.loads((PROB / "cases.json").read_text(encoding="utf-8"))
FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


def _f(case, t, s) -> float:
    return verify._norm(verify._residual(case, t, s))


def _numeric_min(case, iters: int = 400) -> tuple:
    """좌표하강 + 축소. 해석적 풀이를 쓰지 않고 최소점 하나를 찾는다.

    심판의 초록 사례를 만들기 위한 것일 뿐이다. 정확도가 아주 높을 필요는 없고,
    심판의 허용치를 넘길 만큼만 정확하면 된다."""
    t = s = 0.0
    step = 64.0
    for _ in range(iters):
        improved = False
        for _ in range(60):
            best = _f(case, t, s)
            for dt, ds in ((step, 0), (-step, 0), (0, step), (0, -step)):
                v = _f(case, t + dt, s + ds)
                if v < best - 1e-15:
                    t, s, best, improved = t + dt, s + ds, v, True
            if not improved:
                break
            improved = False
        step *= 0.5
        if step < 1e-13:
            break
    return t, s, _f(case, t, s)


def _answer(pairs) -> dict:
    return {"cases": [{"id": c["id"], "t": t, "s": s, "distance": d}
                      for c, (t, s, d) in zip(CASES, pairs)]}


def test_rejects_obvious_garbage() -> None:
    """형식 위반 / 빠진 case / 전부 0 -- 전부 거부해야 한다."""
    for label, out in (("dict 아님", [1, 2]),
                       ("cases 없음", {"nope": 1}),
                       ("빈 리스트", {"cases": []}),
                       ("전부 0", _answer([(0.0, 0.0, 0.0)] * len(CASES)))):
        ok, why = verify.check(out, {})
        check(not ok, f"{label} 을 통과시켰다")


def test_accepts_true_minimum() -> None:
    """맞는 답을 받아들이는가. **전부 거부하는 심판도 고장이다.**"""
    pairs = [_numeric_min(c) for c in CASES]
    ok, why = verify.check(_answer(pairs), {})
    check(ok, f"수치 최소점을 통과시키지 못한다: {why}")
    if ok:
        print(f"    [통과] {why[:100]}")


def test_accepts_any_minimizer_when_degenerate() -> None:
    """평행/일치 직선은 최소점이 무한히 많다. 어느 것을 내도 받아야 한다.

    유일해를 강요하면 오케스트레이터가 맞는 답을 내고도 떨어진다 -- 심판이 문제를
    실제보다 좁게 정의하는 형태의 고장이다."""
    pairs = [_numeric_min(c) for c in CASES]
    shifted = []
    for c, (t, s, d) in zip(CASES, pairs):
        if c["id"] in ("parallel", "identical"):
            # 방향을 따라 같이 미끄러뜨린다. 잔차가 그대로면 여전히 최소점이다.
            n1 = verify._dot(c["v1"], c["v1"])
            n12 = verify._dot(c["v1"], c["v2"])
            delta = 3.0
            tt, ss = t + delta, s + delta * n12 / n1 if n12 else s
            if abs(_f(c, tt, ss) - d) < 1e-9:
                t, s = tt, ss
        shifted.append((t, s, _f(c, t, s)))
    ok, why = verify.check(_answer(shifted), {})
    check(ok, f"퇴화한 경우의 다른 최소점을 거부한다: {why}")


def test_catches_near_miss() -> None:
    """최소점에서 살짝 벗어난 답을 잡는가. 허용치가 헐거우면 심판이 헛돈다."""
    pairs = [_numeric_min(c) for c in CASES]
    for eps, must_fail in ((1e-12, False), (1e-2, True), (1.0, True)):
        off = []
        for c, (t, s, _) in zip(CASES, pairs):
            tt = t + eps
            off.append((tt, s, _f(c, tt, s)))
        ok, why = verify.check(_answer(off), {})
        if must_fail:
            check(not ok, f"최소점에서 {eps} 벗어난 답을 통과시켰다")
        else:
            check(ok, f"수치 오차 수준({eps})의 답을 거부한다: {why}")


def test_verifier_does_not_contain_the_answer() -> None:
    """심판 파일이 풀이법을 담고 있지 않은가.

    담고 있으면 오케스트레이터가 verify.py 를 읽고 베낀다 -- repair_node 는 노드에
    verifier 를 읽기 전용으로 보여주기 때문이다. 그러면 이 시험이 무의미해진다."""
    import re
    src = (PROB / "verify.py").read_text(encoding="utf-8")
    # 단어 경계로 본다. resolve( 가 solve( 로 잡히는 거짓 양성을 피한다.
    banned = [r"\blstsq\b", r"\bpinv\b", r"\bsolve\(", r"\bcross\(",
              r"\bdet\(", r"\binv\(", r"normal\s+equation"]
    hits = [b for b in banned if re.search(b, src)]
    check(not hits, f"심판이 풀이법을 담고 있다: {hits}")
    check("grad" in src.lower() or "직교" in src,
          "심판이 무엇을 확인하는지 설명이 없다")


def main() -> int:
    for fn in (test_rejects_obvious_garbage, test_accepts_true_minimum,
               test_accepts_any_minimizer_when_degenerate, test_catches_near_miss,
               test_verifier_does_not_contain_the_answer):
        fn()
    if FAILURES:
        print("실패:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("직선거리 심판: 쓰레기 거부, 최소점 통과, 퇴화 허용, 근접오답 검출, 풀이 미포함 -- 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
