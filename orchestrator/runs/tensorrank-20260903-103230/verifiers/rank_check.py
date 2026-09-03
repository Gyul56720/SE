"""텐서 랭크 분해의 외부 심판. LLM 도 numpy 도 쓰지 않는다. 전부 유리수 정확 연산이다.

**이 파일은 답을 담지 않는다.** 분해를 찾는 방법도 적혀 있지 않다. 넘어온 세 인자행렬
(u, v, w) 이 표적 텐서를 **정확히** 되살리는지, 그리고 항의 개수가 예산 안인지만 본다.

원리. 표적 텐서 T 와 후보 분해가 주어지면 확인은 곱셈 M * nnz(u) * nnz(v) * nnz(w) 번이다
-- <3,3,3>, M=23 이면 수만 번. 반면 그 분해를 **찾는** 것은 열린 문제다. 문헌이 아는 것은
랭크가 19 이상 23 이하라는 것뿐이다. 이 격차가 이 심판이 성립하는 이유다: 심판은 답을
모르면서 답을 확인한다.

왜 정확 연산인가 -- **경계랭크(border rank) 때문이다.** 실수 위에서 랭크 R 텐서를 랭크
R' < R 인 텐서열의 극한으로 만들 수 있다. w_state 가 그 예다: 랭크는 3 인데 계수를
1/eps 로 발산시키면 2 항으로 오차를 0 에 임의로 가깝게 만든다. 그래서 "잔차가 1e-12 라
통과"라는 심판은 랭크가 아니라 경계랭크를 재게 되고, 그것은 **다른 양**이다. 부동소수
허용치를 두는 순간 이 시험은 뜻을 잃는다.

그래서 두 겹으로 막는다:
  ① 성분은 유리수로 받고 재구성을 Fraction 으로 정확히 맞춘다 (허용치 0)
  ② 성분을 격자에 가둔다 (|x| <= COEF_MAX, 분모 <= DEN_MAX) -- 발산하는 계수 자체를 막는다

보조로 전개행렬(unfolding)의 정확 랭크를 재서 하한 증명서를 만든다. 이것이 SVD 기반
차원축소가 여기서 통하지 않는 이유이기도 하다: 행렬곱 텐서는 세 전개가 모두 꽉 찬
랭크라 HOSVD 로 줄일 코어가 없다. 심판이 그 값을 재서 보고한다.

기각 사유에는 case 별로 항 개수 / 틀린 칸 수 / 최대 오차 / 계수 규모를 전부 적는다.
수리 루프가 무엇을 고쳐야 하는지 알아야 하기 때문이다.
"""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "target.json"

# 격자. 경계랭크로 새어나가는 길을 계수 크기에서 끊는다. 문헌에 알려진 구성들은 성분이
# 전부 절댓값 2 이하의 정수라, 이 격자는 필요한 것보다 네 배 넉넉하다.
COEF_MAX = Fraction(8)
DEN_MAX = 12


def _frac(x, where: str) -> Fraction:
    """정수 / 'p/q' 문자열 / 부동소수를 유리수로. 부동소수는 이진 표현 그대로 읽는다.

    0.1 같은 값은 이진으로 정확하지 않아 분모가 2^55 급이 되고, 그러면 DEN_MAX 에서
    걸린다. 그것이 의도다 -- 격자에 못 앉은 답은 격자에 못 앉은 것이다."""
    if isinstance(x, bool):
        raise ValueError(f"{where}: 불리언은 성분이 될 수 없다")
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x)
    if isinstance(x, str):
        try:
            return Fraction(x)
        except (ValueError, ZeroDivisionError):
            raise ValueError(f"{where}: 유리수로 못 읽는다: {x!r}")
    if isinstance(x, float):
        if x != x or x in (float("inf"), float("-inf")):
            raise ValueError(f"{where}: 유한한 수가 아니다: {x!r}")
        return Fraction(x)
    raise ValueError(f"{where}: 수가 아니다: {type(x).__name__}")


def _vec(raw, n: int, where: str) -> list:
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f"{where}: 리스트가 아니다")
    if len(raw) != n:
        raise ValueError(f"{where}: 길이가 {len(raw)} 다 -- {n} 이어야 한다")
    return [_frac(x, f"{where}[{i}]") for i, x in enumerate(raw)]


def _factors(row, case) -> tuple:
    """(u, v, w) 를 M x dim 유리수 행렬 세 개로 읽는다."""
    d0, d1, d2 = case["shape"]
    out = []
    lengths = []
    for key, dim in (("u", d0), ("v", d1), ("w", d2)):
        mat = row.get(key)
        if not isinstance(mat, (list, tuple)) or not mat:
            raise ValueError(f"'{key}' 가 비어 있거나 리스트가 아니다")
        out.append([_vec(r, dim, f"{key}[{i}]") for i, r in enumerate(mat)])
        lengths.append(len(mat))
    if len(set(lengths)) != 1:
        raise ValueError(f"u, v, w 의 항 개수가 다르다: {lengths}")
    return out[0], out[1], out[2]


def _lattice(u, v, w) -> tuple:
    """격자 위반을 찾고, 계수 규모도 같이 돌려준다."""
    worst = Fraction(0)
    den = 1
    for mat in (u, v, w):
        for r in mat:
            for x in r:
                a = abs(x)
                if a > worst:
                    worst = a
                den = max(den, x.denominator)
    bad = []
    if worst > COEF_MAX:
        bad.append(f"|성분| 최대 {float(worst):.6g} > {int(COEF_MAX)}")
    if den > DEN_MAX:
        bad.append(f"분모 최대 {den} > {DEN_MAX}")
    return bad, worst, den


def _reconstruct(u, v, w) -> dict:
    """sum_r u_r (x) v_r (x) w_r 을 성긴 dict 로. 0 이 된 칸은 버린다."""
    acc: dict = {}
    for ur, vr, wr in zip(u, v, w):
        nzu = [(i, x) for i, x in enumerate(ur) if x]
        nzv = [(j, x) for j, x in enumerate(vr) if x]
        nzw = [(k, x) for k, x in enumerate(wr) if x]
        for i, a in nzu:
            for j, b in nzv:
                ab = a * b
                for k, c in nzw:
                    key = (i, j, k)
                    val = acc.get(key, 0) + ab * c
                    if val:
                        acc[key] = val
                    else:
                        acc.pop(key, None)
    return acc


def _target(case) -> dict:
    return {(int(i), int(j), int(k)): Fraction(val)
            for i, j, k, val in case["entries"]}


def _rank_exact(rows) -> int:
    """성긴 유리수 행들의 정확 랭크. 부동소수를 쓰지 않으므로 문턱값 문제가 없다."""
    pivots = []                      # [(축열, 정규화된 행)]
    rank = 0
    for raw in rows:
        r = {c: Fraction(v) for c, v in raw.items() if v}
        for col, prow in pivots:
            f = r.get(col)
            if f:
                for c2, v2 in prow.items():
                    nv = r.get(c2, 0) - f * v2
                    if nv:
                        r[c2] = nv
                    else:
                        r.pop(c2, None)
        if r:
            col = min(r)
            piv = r[col]
            pivots.append((col, {c: v / piv for c, v in r.items()}))
            rank += 1
    return rank


def _unfold_ranks(case) -> list:
    """세 전개행렬의 정확 랭크 = 다중선형 랭크. max 가 텐서 랭크의 하한이다.

    SVD/HOSVD 로 차원을 줄이려는 시도가 여기서 걸린다. 행렬곱 텐서는 세 값이 모두
    꽉 차 있어 줄일 코어가 없다 -- 줄였다는 주장은 곧 이 하한 아래의 M 주장이 된다."""
    T = _target(case)
    shape = case["shape"]
    out = []
    for mode in range(3):
        rows = [dict() for _ in range(shape[mode])]
        for (i, j, k), val in T.items():
            idx = (i, j, k)
            rest = tuple(x for m, x in enumerate(idx) if m != mode)
            rows[idx[mode]][rest] = val
        out.append(_rank_exact(rows))
    return out


def score_case(case, row) -> dict:
    """case 하나를 채점한다. 통과 여부와 진단을 함께 돌려준다."""
    d = {"id": case["id"], "ok": False, "reason": None, "rank": None,
         "budget": case["budget"]}
    try:
        u, v, w = _factors(row, case)
    except ValueError as e:
        d["reason"] = f"형식: {e}"
        return d

    M = len(u)
    d["rank"] = M
    claimed = row.get("rank")
    if claimed is not None and int(claimed) != M:
        d["reason"] = f"보고한 rank {claimed} 와 실제 항 개수 {M} 가 다르다"
        return d

    bad, worst, den = _lattice(u, v, w)
    d["coef_max"] = float(worst)
    d["den_max"] = den
    if bad:
        # 경계랭크로 새어나가는 전형적 신호. 잔차가 작아도 이것이면 분해가 아니다.
        d["reason"] = ("격자 이탈 -- " + ", ".join(bad) +
                       ". 계수를 키워 오차를 줄이는 것은 경계랭크이지 분해가 아니다")
        return d

    lb = max(_unfold_ranks(case))
    d["flattening_lb"] = lb
    if M < lb:
        d["reason"] = (f"M={M} 은 전개행렬 랭크 하한 {lb} 보다 작다 -- 어떤 분해도 "
                       f"불가능하다 (심판이 직접 증명한 하한)")
        return d

    T = _target(case)
    got = _reconstruct(u, v, w)
    wrong, maxerr = 0, Fraction(0)
    for key in set(T) | set(got):
        diff = got.get(key, 0) - T.get(key, 0)
        if diff:
            wrong += 1
            maxerr = max(maxerr, abs(diff))
    d["wrong_cells"] = wrong
    d["max_err"] = float(maxerr)
    # 상쇄 질량. 항의 크기 합이 텐서 자체보다 훨씬 크면 큰 항들이 서로 지우고 있다는
    # 뜻이고, 그것이 국소최소/경계랭크에 앉은 해의 모습이다.
    mass = sum(max((abs(x) for x in ur), default=Fraction(0)) *
               max((abs(x) for x in vr), default=Fraction(0)) *
               max((abs(x) for x in wr), default=Fraction(0))
               for ur, vr, wr in zip(u, v, w))
    d["mass_ratio"] = float(mass) / max(1, len(T))
    if wrong:
        hint = ""
        if d["mass_ratio"] > 4.0:
            hint = (f" 항 크기 합이 텐서의 {d['mass_ratio']:.1f} 배다 -- 큰 항들이 서로 "
                    f"지우고 있다. 국소최소이거나 경계랭크로 새는 중이다")
        d["reason"] = (f"정확히 재구성하지 못한다: {wrong} 칸이 틀렸다 "
                       f"(최대 오차 {d['max_err']:.6g}).{hint}")
        return d

    if M > case["budget"]:
        d["reason"] = (f"정확한 분해지만 M={M} 이 예산 {case['budget']} 을 넘는다 "
                       f"-- 구간 밖이다")
        return d

    d["ok"] = True
    known = case.get("known", {})
    lo, hi = known.get("lower"), known.get("upper")
    if lo is None:
        d["reason"] = f"정확 · M={M} (기지 랭크 {known.get('rank', '?')})"
        return d

    # **예산 통과와 구간 진입은 다른 말이다.** 예산은 이번 런에 걸어둔 목표라 --budget 으로
    # 느슨하게 풀 수 있고, 구간은 문헌이 아는 사실이라 안 움직인다. 처음 쓴 코드는 M >= lo
    # 이기만 하면 "구간 안"이라 적었고, 그래서 예산 27 로 푼 런에서 M=27 을 두고 "구간
    # [19,23] 안"이라고 **거짓을 보고했다**. 심판이 통과 여부를 맞게 내도 보고가 틀리면
    # 그 위에 쌓는 판단이 전부 틀어진다.
    d["interval"] = "below" if M < lo else ("inside" if M <= hi else "above")
    if d["interval"] == "below":
        d["alert"] = (f"M={M} 이 문헌 하한 {lo} 아래다. 문헌이 틀렸을 확률보다 심판에 "
                      f"구멍이 있을 확률이 훨씬 크다 -- 먼저 심판을 의심하라")
        d["reason"] = f"정확 · M={M} · 구간 [{lo},{hi}] **아래**"
    elif d["interval"] == "inside":
        d["reason"] = f"정확 · M={M} · 구간 [{lo},{hi}] 안"
    else:
        d["reason"] = (f"정확 · M={M} · 구간 [{lo},{hi}] **위** -- 예산은 넘겼지만 "
                       f"문헌 상한 {hi} 는 아직 못 내렸다")
    return d


def check(output, inputs):
    """output = {"cases": [{"id", "rank", "u", "v", "w"}, ...]}"""
    if not isinstance(output, dict):
        return False, f"출력이 dict 가 아니다: {type(output).__name__}"
    got = output.get("cases")
    if not isinstance(got, list):
        return False, "출력에 'cases' 리스트가 없다"

    spec = json.loads(TARGET.read_text(encoding="utf-8"))
    cases = spec["cases"]
    by_id = {}
    for r in got:
        if not isinstance(r, dict) or "id" not in r:
            return False, f"각 항목은 id 를 가진 dict 여야 한다: {str(r)[:80]}"
        by_id[str(r["id"])] = r
    missing = [c["id"] for c in cases if str(c["id"]) not in by_id]
    if missing:
        return False, f"빠진 case: {missing}"

    # **전부 채점하고 모아서 보고한다.** 첫 실패에서 멈추면 수리 루프가 한 번에 하나씩만
    # 알게 되어 라운드를 낭비한다.
    rows = [score_case(c, by_id[str(c["id"])]) for c in cases]
    bad = [r for r in rows if not r["ok"]]
    parts = []
    for r in rows:
        mark = "OK" if r["ok"] else "X "
        parts.append(f"[{mark}] {r['id']}(M={r['rank']}/{r['budget']}): {r['reason']}")
        if r.get("alert"):
            parts.append(f"     !! {r['alert']}")
    return (not bad), " | ".join(parts)
