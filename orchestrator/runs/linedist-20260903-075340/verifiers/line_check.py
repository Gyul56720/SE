"""두 직선 사이 최단거리 문제의 외부 심판. LLM 을 쓰지 않는다.

**이 파일은 답을 담지 않는다.** 푸는 방법도 적혀 있지 않다. 오직 넘어온 (t, s) 가
최소점인지 확인만 한다 -- 그리고 그 확인이 푸는 것보다 압도적으로 싸다.

원리. 목적함수

    f(t, s) = || (p1 + t*v1) - (p2 + s*v2) ||^2

는 (t, s) 에 대한 볼록 이차형식이다. 볼록함수에서는

    grad f = 0   <=>   전역 최소

이고, d = (p1 + t*v1) - (p2 + s*v2) 라 두면

    df/dt = 2 * <v1, d>,    df/ds = -2 * <v2, d>

이다. 그래서 심판이 하는 일은 **내적 두 개를 재는 것**뿐이다. 어떻게 그 점을 찾는지는
전혀 관여하지 않는다 -- 정규방정식을 풀든, 외적을 쓰든, 수치 최적화를 하든 상관없다.

퇴화한 경우(v1 // v2)도 같은 조건이 그대로 성립한다. 그때는 최소점이 무한히 많고,
잔차가 span{v1, v2} 에 직교한다는 조건은 여전히 <v1,d> = <v2,d> = 0 이다. 그래서
심판은 **어느 최소점을 내든 받아들인다** -- 유일해를 강요하지 않는다.

보조 검사로 무작위 섭동을 준다. 일차 조건만 보면 수치 오차로 통과할 수 있는 답을
거른다. 이것도 답을 알려주지 않는다 -- 주변보다 낮은지만 본다.
"""
import json
import math
import random
from pathlib import Path

GRAD_TOL = 1e-6          # 내적 잔차 허용치 (스케일로 정규화한 뒤)
DIST_TOL = 1e-9          # 보고한 거리와 실제 ||d|| 의 차이
PERTURB = 64             # 무작위 섭동 개수
CASES = Path(__file__).resolve().parent / "cases.json"


def _sub(a, b):
    return [x - y for x, y in zip(a, b)]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _norm(a):
    return math.sqrt(_dot(a, a))


def _residual(case, t, s):
    """d = (p1 + t*v1) - (p2 + s*v2)"""
    p1, v1, p2, v2 = case["p1"], case["v1"], case["p2"], case["v2"]
    r1 = [p + t * v for p, v in zip(p1, v1)]
    r2 = [p + s * v for p, v in zip(p2, v2)]
    return _sub(r1, r2)


def check(output, inputs):
    """output 에 각 case 의 t, s, distance 가 들어 있어야 한다."""
    if not isinstance(output, dict):
        return False, f"출력이 dict 가 아니다: {type(output).__name__}"
    got = output.get("cases")
    if not isinstance(got, list):
        return False, "출력에 'cases' 리스트가 없다"

    cases = json.loads(CASES.read_text(encoding="utf-8"))
    by_id = {}
    for row in got:
        if not isinstance(row, dict) or "id" not in row:
            return False, f"각 항목은 id 를 가진 dict 여야 한다: {row!r}"
        by_id[str(row["id"])] = row
    missing = [c["id"] for c in cases if str(c["id"]) not in by_id]
    if missing:
        return False, f"빠진 case: {missing}"

    rng = random.Random(20260902)
    notes = []
    for case in cases:
        cid = str(case["id"])
        row = by_id[cid]
        for key in ("t", "s", "distance"):
            if key not in row:
                return False, f"case {cid}: '{key}' 가 없다"
            try:
                float(row[key])
            except (TypeError, ValueError):
                return False, f"case {cid}: '{key}' 가 수가 아니다: {row[key]!r}"

        t, s, dist = float(row["t"]), float(row["s"]), float(row["distance"])
        if not all(map(math.isfinite, (t, s, dist))):
            return False, f"case {cid}: 유한한 수가 아니다 (t={t}, s={s}, d={dist})"

        d = _residual(case, t, s)
        actual = _norm(d)

        # ① 보고한 거리가 실제 ||d|| 와 같은가
        if abs(actual - dist) > DIST_TOL * max(1.0, actual):
            return False, (f"case {cid}: 보고한 거리 {dist:.12g} 가 실제 "
                           f"||r1-r2|| = {actual:.12g} 와 다르다")

        # ② 일차 조건. 방향벡터 크기로 정규화해 스케일 의존을 없앤다.
        v1, v2 = case["v1"], case["v2"]
        n1, n2 = _norm(v1), _norm(v2)
        scale = max(actual, 1.0)
        g1 = abs(_dot(v1, d)) / (n1 * scale)
        g2 = abs(_dot(v2, d)) / (n2 * scale)
        if g1 > GRAD_TOL or g2 > GRAD_TOL:
            return False, (f"case {cid}: 최소점이 아니다 -- 잔차가 방향벡터와 직교하지 "
                           f"않는다 (<v1,d>={g1:.3e}, <v2,d>={g2:.3e}, 허용 {GRAD_TOL:.0e})")

        # ③ 무작위 섭동. 주변에 더 낮은 점이 있으면 일차 조건이 수치적으로 속은 것이다.
        step = max(1.0, abs(t), abs(s))
        for _ in range(PERTURB):
            for h in (1e-3, 1e-1, 1.0):
                tt = t + rng.uniform(-h, h) * step
                ss = s + rng.uniform(-h, h) * step
                if _norm(_residual(case, tt, ss)) < actual * (1 - 1e-9) - 1e-12:
                    return False, (f"case {cid}: 더 작은 값이 있다 -- "
                                   f"(t,s)=({tt:.6g},{ss:.6g}) 에서 더 짧다")
        notes.append(f"{cid}:{actual:.6g}")

    return True, "모든 case 가 최소점이다 (거리 " + ", ".join(notes) + ")"
