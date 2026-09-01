"""
행렬 곱셈 텐서 분해 도메인 -- 오라클이 수학적으로 정의되는, 이 구조에 가장 잘 맞는 난제.

문제: n×n 행렬 두 개의 곱을 몇 번의 '스칼라 곱셈'으로 계산할 수 있는가. 표준 알고리즘은
n^3 번(2×2면 8번). Strassen(1969)은 2×2를 7번에 해냈다. 이것이 곧 행렬곱 텐서의 rank 다.
더 낮은 rank 를 '창조'하는 것이 이 도메인의 목표이고, AlphaTensor(2022)가 유명하게 도전한
바로 그 문제다.

왜 이 구조에 완벽하게 맞는가 -- 오라클이 세 조건을 다 만족한다:
  1. 자동    : 분해 (U, V, W, lambdas)가 주어지면 재계산 한 번으로 맞는지 판정한다.
  2. 위조불가 : 정확 유리수 산술로 검증한다. float 근사가 아니라 Fraction 이라 '거의 맞음'으로
               속일 수 없다. 저장소의 mathmetics/matrix_exponent/verifier.py 가 이미 이걸 한다.
  3. 탐색어려움 : 검증은 O(n^3 × rank) 로 즉시지만, 낮은 rank 분해를 '찾는' 것은 열린 난제다.
               검증 쉬움 + 탐색 어려움 = 이 저장소의 orchestrator 가 겨냥한 바로 그 형태.

데이터가 없다 -- 그리고 그게 핵심이다:
  세포 추적은 라벨 데이터(ground_truth.csv)가 심판이었다. 여기서는 심판이 데이터가 아니라
  '수학적 정의'다. n×n 행렬곱 텐서는 n 만 주면 유일하게 결정된다. 그래서 이 도메인은 외부
  데이터 없이 돈다 -- 대회 데이터를 못 구해도, 인터넷이 없어도 심판이 성립한다.

점수(높을수록 좋다):
  검증에 실패하면 0. (틀린 분해는 아무 가치가 없다 -- 부분 점수 없음. 위조 방지의 핵심.)
  검증에 성공하면: 1 + (baseline_rank - rank) / baseline_rank.
    - 표준 rank(n^3)를 재현하면 정확히 1.0.
    - rank 를 하나 줄일 때마다 오른다. 2×2에서 8→7(Strassen)이면 1.125.
    - 이 단조성이 루프에 방향을 준다: '맞으면서 더 적은 곱셈'이 항상 더 높은 점수.

계약: solve(data_dir, out_csv) 는 세포 추적과 같은 서명을 쓰되, data_dir 안의 config.json
에서 n(행렬 크기)을 읽고, out_csv 에 분해를 쓴다. 데이터 파일은 안 읽는다.

분해 CSV 형식(제출):
    kind,r,i,j,val
    U,0,0,0,1        # U[i=0][r=0] = 1  (i 는 좌행렬을 편 인덱스 0..n^2-1)
    V,0,0,0,1
    W,0,0,0,1
    lambda,0,-1,-1,1 # lambdas[r=0] = 1
  r 은 항 인덱스(0..rank-1), val 은 유리수(정수/소수/'a/b' 분수 모두 허용).
"""
from __future__ import annotations

import csv
from fractions import Fraction


def matmul_tensor(n: int):
    """n×n 행렬곱 텐서 T[a][b][c]. a=좌행렬(i,k), b=우행렬(k,j), c=결과(i,j) 를 편 인덱스.
    표준 정의: C[i,j] = sum_k A[i,k] B[k,j]. 텐서 성분은 그 계수(0 또는 1)."""
    N = n * n
    T = {}
    for i in range(n):
        for j in range(n):
            for k in range(n):
                a = i * n + k          # A[i,k]
                b = k * n + j          # B[k,j]
                c = i * n + j          # C[i,j]
                T[(a, b, c)] = T.get((a, b, c), 0) + 1
    return N, T


def _frac(s) -> Fraction:
    s = str(s).strip()
    return Fraction(s) if s else Fraction(0)


def parse_decomposition(rows, N: int):
    """CSV 행 -> (U, V, W, lambdas). U[i][r] 형태의 dict-of-dict 로 모은 뒤 밀집화.
    rank 는 등장한 r 의 최댓값+1. 빠진 성분은 0."""
    U, V, W, lam = {}, {}, {}, {}
    max_r = -1
    for row in rows:
        kind = str(row["kind"]).strip()
        r = int(row["r"])
        val = _frac(row["val"])
        max_r = max(max_r, r)
        if kind == "lambda":
            lam[r] = val
        else:
            i = int(row["i"])
            tgt = {"U": U, "V": V, "W": W}.get(kind)
            if tgt is None:
                raise ValueError(f"알 수 없는 kind: {kind!r}")
            tgt.setdefault(r, {})[i] = val
    rank = max_r + 1
    if rank <= 0:
        raise ValueError("분해에 항이 하나도 없다")

    def dense(d, length):
        return [[d.get(r, {}).get(i, Fraction(0)) for r in range(rank)] for i in range(length)]

    Um = dense(U, N)
    Vm = dense(V, N)
    Wm = dense(W, N)
    lams = [lam.get(r, Fraction(1)) for r in range(rank)]     # lambda 생략 시 1
    return Um, Vm, Wm, lams, rank


def verify_exact(U, V, W, lambdas, N, T) -> tuple:
    """정확 유리수 산술로 T[a][b][c] == sum_r lambda_r U[a][r] V[b][r] W[c][r] 를 전부 확인.
    (맞는가, 첫 불일치 설명). float 없음 -- '거의 맞음'으로 통과할 수 없다."""
    rank = len(lambdas)
    for a in range(N):
        Ua = U[a]
        for b in range(N):
            Vb = V[b]
            for c in range(N):
                Wc = W[c]
                val = Fraction(0)
                for r in range(rank):
                    if Ua[r] and Vb[r] and Wc[r]:
                        val += lambdas[r] * Ua[r] * Vb[r] * Wc[r]
                if val != T.get((a, b, c), 0):
                    return False, f"성분 ({a},{b},{c}): 기대 {T.get((a,b,c),0)}, 얻음 {val}"
    return True, ""


def score_decomposition(rows, n: int) -> dict:
    """제출 분해를 채점한다. 틀리면 0(부분점수 없음), 맞으면 rank 가 낮을수록 높다."""
    N, T = matmul_tensor(n)
    baseline_rank = n ** 3                # 표준 알고리즘의 곱셈 수
    try:
        U, V, W, lambdas, rank = parse_decomposition(rows, N)
    except Exception as e:                # noqa: BLE001
        return {"score": 0.0, "valid": False, "rank": None, "error": f"파싱 실패: {e}"}
    ok, msg = verify_exact(U, V, W, lambdas, N, T)
    if not ok:
        return {"score": 0.0, "valid": False, "rank": rank, "error": f"검증 실패: {msg}"}
    return {"score": 1.0 + (baseline_rank - rank) / baseline_rank, "valid": True,
            "rank": rank, "baseline_rank": baseline_rank, "n": n,
            "beats_standard": rank < baseline_rank}


def read_decomposition_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
