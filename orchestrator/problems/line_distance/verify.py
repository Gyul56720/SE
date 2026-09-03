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
PERTURB = 64             # 무작위 섭동 개수 (격자 방향 밖을 훑는다)

# 기하급수 직선탐색. **일차 조건만으로는 부족하다** -- 두 직선이 거의 평행하면 헤시안이
# 거의 특이해서, 진짜 최소점에서 한참 떨어진 곳에서도 기울기가 미세하다.
#
# 실측으로 걸린 사례(near_par): 진짜 최소거리는 0 인데(두 직선이 실제로 만난다),
# 최소점에서 444 떨어진 점의 <v2,d> 가 4.4e-10 이라 GRAD_TOL 을 가볍게 통과했다.
# 더 심하게는 거리 5.0 인 점(최소점에서 5e6 떨어진 곳)도 통과했다.
#
# 무작위 섭동으로도 못 잡는다. 최소점이 좁은 골짜기를 따라 멀리 있으면 무작위 방향이
# 그 골짜기에 떨어질 확률이 사실상 0 이다.
#
# 그래서 **방향을 정해 놓고 배율을 기하급수로 훑는다.** 이것은 푸는 방법을 알려주지
# 않는다 -- 어느 방향으로 얼마나 가야 하는지는 여전히 후보가 알아내야 한다.
PROBE_DIRS = ((1.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, -1.0))
PROBE_MAGS = tuple(10.0 ** k for k in range(-9, 13))
# 개선 임계. 부동소수 잡음보다 확실히 커야 한다 -- 1e-9 로 잡았더니 12번째 자리 차이로
# 걸려서, 기각은 맞는데 이유가 잡음이었다. 그러면 맞는 답도 잡음으로 기각할 수 있다.
# 그리고 **첫 히트에서 멈추지 않고 전체를 훑어 최선을 보고한다** -- 얼마나 빗나갔는지가
# 보여야 실패 사유가 쓸모 있다.
IMPROVE = 1e-6           # 이 **비율**만큼 작아지는 점이 있으면 최소점이 아니다
# 상대 임계만으로는 **진짜 최소가 0 일 때 무너진다** -- 8.9e-16 에서 0 으로 가는 것을
# "100% 개선"으로 읽어 맞는 답을 기각한다. near_par 처럼 두 직선이 실제로 만나는 경우가
# 그렇다. 그래서 문제 규모에 묶은 절대 하한을 함께 둔다.
ABS_REL = 1e-9           # 절대 하한 = ABS_REL x (문제의 좌표 규모)
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

        # ③ 기하급수 직선탐색 + ④ 무작위 섭동. 전체를 훑어 **최선**을 찾는다.
        best, best_at = actual, None
        step = max(1.0, abs(t), abs(s))
        probes = [(t + sg * dt * m, s + sg * ds * m)
                  for dt, ds in PROBE_DIRS for m in PROBE_MAGS for sg in (1.0, -1.0)]
        probes += [(t + rng.uniform(-h, h) * step, s + rng.uniform(-h, h) * step)
                   for _ in range(PERTURB) for h in (1e-6, 1e-3, 1e-1, 1.0)]
        for tt, ss in probes:
            if not (math.isfinite(tt) and math.isfinite(ss)):
                continue
            v = _norm(_residual(case, tt, ss))
            if v < best:
                best, best_at = v, (tt, ss)
        geo = max([abs(x) for v in (case["p1"], case["p2"], case["v1"], case["v2"])
                   for x in v] + [1.0])
        margin = max(IMPROVE * actual, ABS_REL * geo)
        if best < actual - margin:
            return False, (
                f"case {cid}: 최소점이 아니다 -- (t,s)=({best_at[0]:.9g},{best_at[1]:.9g}) "
                f"에서 거리가 {best:.9g} 다 (보고값 {actual:.9g}, "
                f"{1 - best / actual:.1%} 더 짧다)")
        notes.append(f"{cid}:{actual:.6g}")

    return True, "모든 case 가 최소점이다 (거리 " + ", ".join(notes) + ")"
