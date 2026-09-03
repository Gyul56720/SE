"""텐서 랭크 심판의 red-green 검사.

무엇을 지키려는가. 이 문제의 답은 **아무도 모른다** -- <3,3,3> 행렬곱 텐서의 랭크는
19 이상 23 이하까지만 알려져 있다. 그러니 심판이 헛돌아도 비교할 정답이 없고, 헛도는
심판 위에 올린 탐색은 어디로든 굴러간다. 그래서 **답을 아는 case 로 심판을 먼저 잰다.**

카나리(전부 거부되어야 한다):
  1. 잘못된 재구성        한 성분만 어긋난 Strassen
  2. 경계랭크 발산 (격자)  1/eps 계수로 2 항에 다가가는 W 상태 -- 계수에서 걸린다
  3. 경계랭크 발산 (정확)  eps=1/8 이라 격자는 통과하지만 정확히는 틀리다
  4. 전개랭크 하한 위반    <3,3,3> 에 M=8 주장 -- 심판이 스스로 증명한 하한 아래다
  5. rank 값 거짓말        보고한 rank 와 실제 항 개수가 다르다
대조군(통과해야 한다 -- 전부 거부하는 심판도 고장이다):
  6. W 상태 3 항          정확한 랭크 3 분해
  7. Strassen 7 항        mm222 예산 정확히 충족
  8. 자명한 27 항         <3,3,3> 을 정확히 재구성한다 (예산은 못 넘지만 정확성은 참)

그리고 검증 비대칭 -- 확인이 찾기보다 압도적으로 싼가 -- 을 실제로 잰다.

numpy 도 LLM 도 쓰지 않는다. 전부 Fraction 정확 연산이다.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROB = REPO / "orchestrator" / "problems" / "tensor_rank"
sys.path.insert(0, str(PROB))

import verify  # noqa: E402

SPEC = json.loads((PROB / "target.json").read_text(encoding="utf-8"))
CASE = {c["id"]: c for c in SPEC["cases"]}
FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        FAILURES.append(msg)


# --- 알려진 분해들. 심판을 재는 자尺이지 심판 안에 있는 것이 아니다 -----------------

def w_rank3() -> dict:
    """T = e0(x)e0(x)e1 + e0(x)e1(x)e0 + e1(x)e0(x)e0. 항 세 개면 정확하다."""
    return {"rank": 3,
            "u": [[1, 0], [1, 0], [0, 1]],
            "v": [[1, 0], [0, 1], [1, 0]],
            "w": [[0, 1], [1, 0], [1, 0]]}


def w_border2(eps: Fraction) -> dict:
    """경계랭크 2 로 새는 시도.

        (1/eps)(e0+eps*e1)^(x)3 - (1/eps) e0(x)e0(x)e0  =  T + O(eps)

    eps 를 줄이면 오차가 0 으로 가지만 계수가 1/eps 로 발산한다. **어떤 유한한 eps
    에서도 정확한 2 항 분해가 아니다.** 수치 최적화가 잔차만 보고 멈추는 지점이 여기다."""
    # 실제 제출이 JSON 으로 오는 것과 같게 문자열로 적는다 ("8", "1/8").
    inv, e = str(1 / eps), str(eps)
    return {"rank": 2,
            "u": [[inv, 1], ["-" + inv, 0]],
            "v": [[1, e], [1, 0]],
            "w": [[1, e], [1, 0]]}


def strassen7() -> dict:
    """Strassen. 색인은 alpha=(i,j) 행우선이므로 0=(1,1) 1=(1,2) 2=(2,1) 3=(2,2).

    m1=(a11+a22)(b11+b22)  m2=(a21+a22)b11      m3=a11(b12-b22)   m4=a22(b21-b11)
    m5=(a11+a12)b22        m6=(a21-a11)(b11+b12) m7=(a12-a22)(b21+b22)
    c11=m1+m4-m5+m7  c12=m3+m5  c21=m2+m4  c22=m1-m2+m3+m6"""
    u = [[1, 0, 0, 1], [0, 0, 1, 1], [1, 0, 0, 0], [0, 0, 0, 1],
         [1, 1, 0, 0], [-1, 0, 1, 0], [0, 1, 0, -1]]
    v = [[1, 0, 0, 1], [1, 0, 0, 0], [0, 1, 0, -1], [-1, 0, 1, 0],
         [0, 0, 0, 1], [1, 1, 0, 0], [0, 0, 1, 1]]
    w = [[1, 0, 0, 1], [0, 0, 1, -1], [0, 1, 0, 1], [1, 0, 1, 0],
         [-1, 1, 0, 0], [0, 0, 0, 1], [1, 0, 0, 0]]
    return {"rank": 7, "u": u, "v": v, "w": w}


def trivial(n: int, m: int, p: int) -> dict:
    """교과서 알고리즘. 곱셈 n*m*p 번, 각 항이 표준기저 하나씩이다."""
    u, v, w = [], [], []
    for i in range(n):
        for j in range(m):
            for k in range(p):
                a = [0] * (n * m); a[i * m + j] = 1
                b = [0] * (m * p); b[j * p + k] = 1
                c = [0] * (n * p); c[i * p + k] = 1
                u.append(a); v.append(b); w.append(c)
    return {"rank": len(u), "u": u, "v": v, "w": w}


# --- 검사 ---------------------------------------------------------------------

def test_accepts_known_good() -> None:
    """답을 아는 case 를 통과시키는가. 전부 거부하는 심판도 고장이다."""
    for cid, sub in (("w_state", w_rank3()), ("mm222", strassen7())):
        r = verify.score_case(CASE[cid], sub)
        check(r["ok"], f"{cid}: 알려진 정확한 분해를 거부한다 -- {r['reason']}")
        if r["ok"]:
            print(f"    [통과] {cid:8} {r['reason']}")


def test_trivial_is_exact_but_over_budget() -> None:
    """자명한 27 항은 **정확하지만** 예산 23 을 넘는다. 두 축이 분리되어 있는가."""
    r = verify.score_case(CASE["mm333"], trivial(3, 3, 3))
    check(not r["ok"], "27 항을 예산 23 안이라고 통과시켰다")
    check(r.get("wrong_cells") == 0, f"27 항은 정확해야 한다: {r.get('wrong_cells')} 칸 틀림")
    check("예산" in (r["reason"] or ""), f"기각 사유가 예산이어야 한다: {r['reason']}")
    print(f"    [분리] mm333 자명해 M=27: 재구성 정확, 예산에서 기각")


def test_rejects_wrong_reconstruction() -> None:
    """성분 하나만 어긋나도 잡는가. 허용치가 0 이므로 잡아야 한다."""
    bad = strassen7()
    bad["u"] = [list(r) for r in bad["u"]]
    bad["u"][0][0] = 2                      # m1 의 a11 계수만 1 -> 2
    r = verify.score_case(CASE["mm222"], bad)
    check(not r["ok"], "한 성분이 어긋난 Strassen 을 통과시켰다")
    check(r.get("wrong_cells", 0) > 0, f"틀린 칸 수를 세지 못한다: {r}")


def test_rejects_border_rank_by_lattice() -> None:
    """계수를 크게 발산시킨 경계랭크 시도가 격자에서 걸리는가 (eps=1/100 -> 1/eps=100)."""
    r = verify.score_case(CASE["w_state"], w_border2(Fraction(1, 100)))
    check(not r["ok"], "1/eps=100 인 경계랭크 시도를 통과시켰다")
    check("격자" in (r["reason"] or ""), f"기각 사유가 격자여야 한다: {r['reason']}")


def test_rejects_border_rank_by_exactness() -> None:
    """격자를 통과하는 크기(eps=1/8, 1/eps=8)여도 **정확히는 틀리다**.

    이것이 부동소수 허용치를 두면 안 되는 이유다. eps 를 줄이면 잔차는 얼마든지 작아지고,
    잔차에 문턱을 두는 심판은 랭크가 아니라 경계랭크를 재게 된다 -- 다른 양이다."""
    sub = w_border2(Fraction(1, 8))
    r = verify.score_case(CASE["w_state"], sub)
    check(not r["ok"], "eps=1/8 경계랭크 시도를 통과시켰다")
    check(r.get("wrong_cells", 0) > 0, f"틀린 칸이 있어야 한다: {r}")
    check(r.get("mass_ratio", 0) > 4.0,
          f"상쇄 질량이 커야 한다 (국소최소 신호): {r.get('mass_ratio')}")
    check("경계랭크" in (r["reason"] or "") or "국소최소" in (r["reason"] or ""),
          f"기각 사유에 국소최소/경계랭크 진단이 있어야 한다: {r['reason']}")
    print(f"    [진단] w_state eps=1/8: 틀린 칸 {r['wrong_cells']}, "
          f"상쇄 질량 {r['mass_ratio']:.1f}배")


def test_rejects_below_flattening_bound() -> None:
    """전개행렬 랭크 하한(=9) 아래의 주장을 심판이 스스로 증명해 거부하는가.

    SVD/HOSVD 로 차원을 줄였다는 주장이 여기서 걸린다. 행렬곱 텐서는 세 전개가 모두
    꽉 찬 랭크라 줄일 코어가 없다."""
    check(verify._unfold_ranks(CASE["mm333"]) == [9, 9, 9],
          "mm333 의 다중선형 랭크는 (9,9,9) 여야 한다 -- HOSVD 로 줄일 코어가 없다")
    sub = {"rank": 8, "u": [[0] * 9] * 8, "v": [[0] * 9] * 8, "w": [[0] * 9] * 8}
    r = verify.score_case(CASE["mm333"], sub)
    check(not r["ok"], "M=8 주장을 통과시켰다")
    check("하한" in (r["reason"] or ""), f"기각 사유가 하한이어야 한다: {r['reason']}")


def test_rejects_rank_lie() -> None:
    """보고한 rank 와 실제 항 개수가 다르면 잡는가."""
    sub = strassen7()
    sub["rank"] = 5
    r = verify.score_case(CASE["mm222"], sub)
    check(not r["ok"], "rank 를 5 라고 거짓말한 답을 통과시켰다")


def test_check_reports_every_case() -> None:
    """모아서 보고하는가. 첫 실패에서 멈추면 수리 루프가 한 라운드에 하나씩만 배운다."""
    out = {"cases": [dict(id="w_state", **w_rank3()),
                     dict(id="mm222", **strassen7()),
                     dict(id="mm333", **trivial(3, 3, 3))]}
    ok, why = verify.check(out, {})
    check(not ok, "mm333 이 27 항인데 전체를 통과시켰다")
    for cid in ("w_state", "mm222", "mm333"):
        check(cid in why, f"보고에 {cid} 가 빠졌다")
    check("[OK]" in why and "[X ]" in why, f"통과/실패가 같이 보여야 한다: {why[:120]}")
    print(f"    [보고] {why[:150]}")


def test_check_can_pass() -> None:
    """예산을 27 로 풀면 **통과가 실제로 가능한가.** 통과 불가능한 심판은 신호가 없다."""
    spec = json.loads(json.dumps(SPEC))
    for c in spec["cases"]:
        if c["id"] == "mm333":
            c["budget"] = 27
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "target.json"
        p.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        old, verify.TARGET = verify.TARGET, p
        try:
            out = {"cases": [dict(id="w_state", **w_rank3()),
                             dict(id="mm222", **strassen7()),
                             dict(id="mm333", **trivial(3, 3, 3))]}
            ok, why = verify.check(out, {})
        finally:
            verify.TARGET = old
    check(ok, f"예산 27 에서도 통과시키지 못한다: {why}")


def test_verification_is_cheap() -> None:
    """확인이 찾기보다 싼가 -- 이 심판이 성립하는 전제다.

    27 항 <3,3,3> 을 정확 유리수로 검사하는 데 걸리는 시간을 잰다. 반대로 랭크가
    19 인지 23 인지는 50 년째 열려 있다. 그 격차가 이 문제를 오케스트레이션 대상으로
    만든다 -- 심판은 답을 모르면서 답을 확인한다."""
    sub = trivial(3, 3, 3)
    t0 = time.perf_counter()
    for _ in range(5):
        verify.score_case(CASE["mm333"], sub)
    dt = (time.perf_counter() - t0) / 5
    check(dt < 1.0, f"27 항 검사에 {dt:.3f}s 걸린다 -- 심판이 너무 비싸다")
    print(f"    [비대칭] <3,3,3> 27항 정확 검증 {dt * 1000:.1f}ms "
          f"/ 랭크 결정은 미해결 (19 <= R <= 23)")


def test_verifier_has_no_method() -> None:
    """심판이 분해를 찾는 방법이나 알려진 분해표를 담고 있지 않은가.

    repair_node 는 노드에 verifier 를 읽기 전용으로 보여준다. 심판이 답을 담고 있으면
    오케스트레이터가 그것을 베끼고 이 시험 전체가 무의미해진다."""
    import re
    src = (PROB / "verify.py").read_text(encoding="utf-8")
    banned = [r"\bals\b", r"\bcp_als\b", r"\bparafac\b", r"\bkhatri\b",
              r"\bstrassen\b", r"\bladerman\b", r"\bsmirnov\b", r"\balphatensor\b",
              r"\bhosvd\b\s*\(", r"\bsvd\("]
    hits = [b for b in banned if re.search(b, src, re.IGNORECASE)]
    check(not hits, f"심판이 풀이/알려진 분해를 담고 있다: {hits}")
    # 인자행렬 표가 박혀 있으면 항 개수만큼의 긴 수 리스트가 남는다
    longlists = re.findall(r"\[(?:\s*-?\d+\s*,){8,}", src)
    check(not longlists, f"심판에 인자행렬 표가 박혀 있다: {len(longlists)}개")


def main() -> int:
    for fn in (test_accepts_known_good, test_trivial_is_exact_but_over_budget,
               test_rejects_wrong_reconstruction, test_rejects_border_rank_by_lattice,
               test_rejects_border_rank_by_exactness, test_rejects_below_flattening_bound,
               test_rejects_rank_lie, test_check_reports_every_case,
               test_check_can_pass, test_verification_is_cheap,
               test_verifier_has_no_method):
        fn()
    if FAILURES:
        print("실패:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("텐서 랭크 심판: 기지해 통과, 정확성/예산 분리, 경계랭크 2중 차단, "
          "전개랭크 하한, 전수 보고, 검증 비대칭, 풀이 미포함 -- 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
