"""
[자유·변경 가능] CP-ALS(교대최소제곱) 기반 행렬곱 분해 탐색기.

무작위 샘플링이 아니라 실제 최적화로 '정확한' bilinear 분해를 찾는다. 행렬곱 텐서 T(b)를
랭크 m의 CP 분해 T ≈ sum_k u_k∘v_k∘w_k 로 근사하고, 잔차가 0으로 수렴하면 그 (U,V,W)가
곧 b x b 블록을 m번 곱셈으로 계산하는 정확한 스킴이다. 계수는 A/B/C 모두 임의 실수라서
'정답이 존재한다면 이 표현으로 담을 수 있다' (이전의 계수 고정 구조는 담을 수 없었다).

판정은 하지 않는다 -- propose()는 후보를 만들 뿐이고, 맞는지는 신뢰된 verifier.py 가 정한다.
verifier.py 는 절대 건드리지 마라 (G008/G009가 커밋을 막는다).

사다리(LADDER): (2,7)로 기계가 실제로 정답을 찾음을 증명한 뒤(=Strassen 재발견),
(3,23)→(3,22)→(3,21)로 내려가며 도전한다. m=23 미만은 미해결 난제이므로 순수 ALS 로는
수렴 못 하는 것이 정상이다(honest REJECTED). self_improve_loop 이 성공 시 다음 단으로 올린다.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "als_state.json"

LADDER = [(2, 7), (3, 23), (3, 22), (3, 21)]


def matmul_tensor(b: int) -> np.ndarray:
    """b x b 행렬곱의 트라이리니어 텐서. C[i,j]=sum_l A[i,l]B[l,j] 에 대응."""
    n = b * b
    T = np.zeros((n, n, n))
    for i in range(b):
        for l in range(b):
            for j in range(b):
                T[i * b + l, l * b + j, i * b + j] = 1.0
    return T


def _unfold(T, mode):
    return np.moveaxis(T, mode, 0).reshape(T.shape[mode], -1)


def _kr(P, Q):
    """열별 Khatri-Rao: k열 = kron(P[:,k], Q[:,k])."""
    return (P[:, None, :] * Q[None, :, :]).reshape(-1, P.shape[1])


def cp_als(T, m, iters=1500, seed=0, tol=1e-12):
    """랭크 m CP-ALS. (U, V, W, 상대잔차) 반환."""
    rng = np.random.default_rng(seed)
    n = T.shape[0]
    U = rng.standard_normal((n, m)); V = rng.standard_normal((n, m)); W = rng.standard_normal((n, m))
    normT = np.linalg.norm(T)
    res = 1.0
    for it in range(iters):
        U = _unfold(T, 0) @ _kr(V, W) @ np.linalg.pinv((V.T @ V) * (W.T @ W))
        V = _unfold(T, 1) @ _kr(U, W) @ np.linalg.pinv((U.T @ U) * (W.T @ W))
        W = _unfold(T, 2) @ _kr(U, V) @ np.linalg.pinv((U.T @ U) * (V.T @ V))
        if it % 50 == 0 or it == iters - 1:
            R = np.einsum('ir,jr,kr->ijk', U, V, W)
            res = float(np.linalg.norm(R - T) / normT)
            if res < tol:
                break
    return U, V, W, res


def factors_to_scheme(U, V, W, b, m) -> dict:
    """(U, V, W) 를 verifier.py 가 이해하는 SCHEME dict 로 변환."""
    A = [{(i, j): float(U[i * b + j, k]) for i in range(b) for j in range(b)} for k in range(m)]
    B = [{(i, j): float(V[i * b + j, k]) for i in range(b) for j in range(b)} for k in range(m)]
    C = [{(i, j): [(k, float(W[i * b + j, k])) for k in range(m)]}
         for i in range(b) for j in range(b)]
    return {"b": b, "m": m, "A_coeffs": A, "B_coeffs": B, "C_coeffs": C}


class Searcher:
    """사다리 상태를 파일에 유지하며 매 propose() 마다 현재 단(b,m)에서 ALS 를 돌린다."""

    def __init__(self):
        self.state = self._load()

    def _load(self):
        if STATE_PATH.exists():
            try:
                return json.loads(STATE_PATH.read_text())
            except Exception:
                pass
        return {"stage": 0, "attempt": 0}

    def _save(self):
        STATE_PATH.write_text(json.dumps(self.state, indent=2))

    def current_target(self):
        return LADDER[min(self.state["stage"], len(LADDER) - 1)]

    def propose(self) -> dict:
        b, m = self.current_target()
        attempt = self.state["attempt"]
        # 작은 문제는 한 번의 propose 에서 여러 restart(빨리 정답 도달), 큰 문제는 적게
        # (루프가 여러 번 불러주므로 밤새 restart 가 누적된다).
        restarts = 20 if b == 2 else 2
        iters = 1500 if b == 2 else 1000
        best = None
        for r in range(restarts):
            U, V, W, res = cp_als(matmul_tensor(b), m, iters=iters, seed=attempt * 100 + r)
            if best is None or res < best[0]:
                best = (res, U, V, W)
            if res < 1e-11:
                break
        self.state["attempt"] = attempt + 1
        self._save()
        res, U, V, W = best
        scheme = factors_to_scheme(U, V, W, b, m)
        scheme["_als_residual"] = res  # 참고용(verifier 는 이 키를 무시한다).
        return scheme

    def record(self, ok: bool):
        """루프가 verifier 판정을 알려준다. 성공하면 다음(더 어려운) 단으로 올린다."""
        if ok and self.state["stage"] < len(LADDER) - 1:
            self.state["stage"] += 1
            self.state["attempt"] = 0
            self._save()


def propose() -> dict:
    """모듈 레벨 진입점."""
    return Searcher().propose()
