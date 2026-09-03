"""두 직선 최단거리 문제의 외부 심판 검사.

**이 파일은 오케스트레이터가 보지 않는다.** repair_node 가 노드에 보여주는 것은 문제
기술서와 verify.py 뿐이다. 여기서 쓰는 무식한 수치 최소화는 심판이 통과 사례를 실제로
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


def _numeric_min(case, iters: int = 200) -> tuple:
    """좌표하강 + 대각 방향 + 큰 초기 보폭. 해석적 풀이를 쓰지 않고 최소점 하나를 찾는다.

    처음에는 보폭 64 에서 시작해 반씩 줄였는데, 그것으로는 **near_par 에서 최소점을 못
    찾았다** -- 진짜 최소점이 t=s=-5e6 에 있어 64 에서 반씩 줄여서는 도달하지 못한다.
    거리 5.0 을 최소라고 내놨고, 그때 심판이 그것을 통과시켰다.
    **검증기와 그 검증이 같은 맹점을 공유한 것**이고, 그래서 둘 다 고쳤다.

    좁은 골짜기(거의 평행한 두 직선)에서는 축 방향만으로 못 내려간다. 대각 방향을 넣는다.

    그리고 **호길이로 매개화한다** (u = t*|v1|, w = s*|v2|). t, s 를 그대로 훑으면 보폭
    하나가 뜻하는 실제 이동 거리가 case 마다 1e8 배씩 달라진다 -- scale_gap 은 |v1|=2^27,
    |v2|=2^-27 이라 t 의 보폭 1e-12 가 공간에서는 1.3e-4 이고, 그 오차로는 심판의 일차
    조건(1e-6)을 못 넘는다. 호길이로 재면 보폭이 곧 이동 거리라 case 규모와 무관해진다."""
    DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1))
    n1 = verify._norm(case["v1"]) or 1.0
    n2 = verify._norm(case["v2"]) or 1.0
    g = lambda u, w: _f(case, u / n1, w / n2)      # noqa: E731  호길이 좌표에서 본 목적함수
    u = w = 0.0
    step = 1e8                                    # 멀리 있는 최소점에 닿을 만큼 크게 시작
    for _ in range(iters):
        for _ in range(200):
            best = g(u, w)
            moved = False
            for du, dw in DIRS:
                v = g(u + du * step, w + dw * step)
                if v < best - 1e-15:
                    u, w, best, moved = u + du * step, w + dw * step, v, True
            if not moved:
                break
        step *= 0.5
        if step < 1e-12:
            break
    t, s = u / n1, w / n2
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
    """최소점에서 살짝 벗어난 답을 잡는가. 허용치가 헐거우면 심판이 헛돈다.

    벗어나는 양도 **호길이로 준다**. t 를 그대로 eps 만큼 밀면 실제 이동 거리가 |v1| 배로
    달라져서, scale_gap(|v1|=2^27) 에서는 eps=1e-12 가 공간에서 1.3e-4 가 된다 -- 잡음이
    아니라 명백한 오답이다. 그것을 "잡음 수준"이라 부르면 검사가 뜻을 잃는다."""
    pairs = [_numeric_min(c) for c in CASES]
    for eps, must_fail in ((1e-12, False), (1e-2, True), (1.0, True)):
        off = []
        for c, (t, s, _) in zip(CASES, pairs):
            tt = t + eps / (verify._norm(c["v1"]) or 1.0)
            off.append((tt, s, _f(c, tt, s)))
        ok, why = verify.check(_answer(off), {})
        if must_fail:
            check(not ok, f"최소점에서 {eps} 벗어난 답을 통과시켰다")
        else:
            check(ok, f"수치 오차 수준({eps})의 답을 거부한다: {why}")


def test_catches_ill_conditioned_near_miss() -> None:
    """조건수가 나쁜 경우에 일차 조건이 전부 통과시키는 것을 잡는가.

    **실측으로 걸린 실패다.** near_par 의 두 직선은 z=0 평면에서 평행하지 않으므로 실제로
    만난다 -- 진짜 최소거리는 0 이다. 그런데 오케스트레이터는 최소점에서 444 떨어진
    (t,s)=(-4999555.5, -4999555.5), 거리 4.44e-4 를 냈고, **옛 심판이 그것을 통과시켰다.**

    이유: 거의 평행이라 헤시안이 거의 특이해서, 최소점이 아닌 곳에서도 <v2,d> 가
    4.4e-10 이다. 일차 조건 허용치 1e-6 이 이 조건수에서는 터무니없이 헐겁다. 무작위
    섭동도 못 잡는다 -- 최소점이 좁은 골짜기를 따라 멀리 있으면 무작위 방향이 그 골짜기에
    떨어질 확률이 사실상 0 이다.

    기하급수 직선탐색이 그것을 잡는다. 이 검사가 깨지면 심판이 다시 헛돈다."""
    np_case = next(c for c in CASES if c["id"] == "near_par")
    others = {c["id"]: _numeric_min(c)[:2] for c in CASES if c["id"] != "near_par"}

    def judge_with(t, s):
        rows = []
        for c in CASES:
            tt, ss = (t, s) if c["id"] == "near_par" else others[c["id"]]
            rows.append({"id": c["id"], "t": tt, "s": ss, "distance": _f(c, tt, ss)})
        return verify.check({"cases": rows}, {})

    # 오케스트레이터가 실제로 낸 답 -- 기각되어야 한다
    ok, why = judge_with(-4999555.536601, -4999555.536601)
    check(not ok, "조건수가 나쁜 경우의 근접오답을 통과시킨다 (옛 심판의 실패)")
    check("near_par" in why, f"기각 사유가 near_par 이어야 한다: {why[:80]}")

    # 훨씬 멀리 빗나간 답도 기각되어야 한다 (옛 심판은 이것도 통과시켰다)
    ok, _ = judge_with(-0.001, -0.001)
    check(not ok, "거리 5.0 인 답을 통과시킨다 (진짜 최소는 0)")

    # 진짜 최소점은 통과해야 한다
    ok, why = judge_with(-5.0e6, -5.0e6)
    check(ok, f"진짜 최소점을 거부한다 -- 임계가 너무 빡빡하다: {why[:100]}")
    check(abs(_f(np_case, -5.0e6, -5.0e6)) < 1e-9, "near_par 의 진짜 최소거리는 0 이다")


def test_catches_rank_truncation() -> None:
    """척도 차이로 특이값이 잘려나간 답을 잡는가 (scale_gap).

    **near_par 를 더 심하게 만드는 길은 막혀 있다.** v2=[1,1e-9,0] 로 조건수를 2e9 로
    올려봤지만 lstsq 의 오차가 정확히 t 의 1 ulp 였다 -- 최소점 |t|=5e9 에서 ulp 가
    9.5e-7 이라, 그보다 잘 하라는 요구는 방법의 문제가 아니라 배정도 표현의 바닥이다.
    그런 기각은 어떤 풀이도 못 넘고, 못 넘는 시험은 신호를 주지 못한다.

    그래서 조건수를 **척도 불균형**으로 만든다. |v1|=2^27, |v2|=2^-27 이면 sigma =
    (1.34e8, 7.45e-9), k(A) = 1.8e16 이다. numpy 의 rcond=None 기본값은
    max(M,N)*eps = 6.7e-16 이라 잘라내는 문턱이 sigma_max*6.7e-16 = 8.9e-8 이고,
    sigma_min = 7.45e-9 가 그 아래로 떨어져 **랭크가 1 로 잘린다**. 그러면 lstsq 는
    두 번째 열을 없는 셈 치고 최소노름해 s=0 을 내놓는다 -- 거리 8.602, 진짜 최소는 5.

    이 실패는 고칠 수 있다는 점이 near_par 와 다르다. 열을 정규화하고 풀면(전처리)
    s=-939524096 이 정확히 나오고 거리도 정확히 5 다. 그래서 이 case 는 방법을 묻는다."""
    sg = next(c for c in CASES if c["id"] == "scale_gap")
    others = {c["id"]: _numeric_min(c)[:2] for c in CASES if c["id"] != "scale_gap"}

    def judge_with(t, s):
        rows = [{"id": c["id"],
                 "t": (t if c["id"] == "scale_gap" else others[c["id"]][0]),
                 "s": (s if c["id"] == "scale_gap" else others[c["id"]][1])}
                for c in CASES]
        for r in rows:
            r["distance"] = _f(next(c for c in CASES if c["id"] == r["id"]),
                               r["t"], r["s"])
        return verify.check({"cases": rows}, {})

    # numpy.linalg.lstsq(A, y, rcond=None) 이 실제로 내놓는 답 (실측값을 박아둔다 --
    # 이 검사에 numpy 를 끌어들이지 않는다). 랭크가 잘려 s=0 이 된다.
    ok, why = judge_with(3.0 / 2 ** 27, 0.0)
    check(not ok, "특이값이 잘려 s=0 이 된 답을 통과시킨다 (거리 8.602, 진짜 최소 5)")
    check("scale_gap" in why, f"기각 사유가 scale_gap 이어야 한다: {why[:80]}")

    # 열을 정규화하고 풀면 나오는 정확한 답. 통과해야 한다.
    ok, why = judge_with(3.0 / 2 ** 27, -7.0 * 2 ** 27)
    check(ok, f"전처리한 정확한 답을 거부한다: {why[:120]}")
    check(abs(_f(sg, 3.0 / 2 ** 27, -7.0 * 2 ** 27) - 5.0) < 1e-12,
          "scale_gap 의 진짜 최소거리는 정확히 5 다")


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
               test_catches_ill_conditioned_near_miss,
               test_catches_rank_truncation,
               test_verifier_does_not_contain_the_answer):
        fn()
    if FAILURES:
        print("실패:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("직선거리 심판: 쓰레기 거부, 최소점 통과, 퇴화 허용, 근접오답 검출, "
          "조건수 나쁜 경우 검출, 랭크 절단 검출, 풀이 미포함 -- 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
