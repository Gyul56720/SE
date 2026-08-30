"""
행렬곱 텐서의 정확 CP 분해를 찾는 개선된 탐색기.

[개선 전략: 외삽 ALS(Extrapolated ALS) 및 적응형 가속]

1. 외삽 ALS (Extrapolated ALS):
   ALS는 'swamp(늪)' 구간에서 수렴 속도가 극도로 느려지며, b=3, m=22 같은 난제에서 
   잔차 0.01 부근의 국소 최적점에 갇히는 경향이 있다. 이전의 단순 ALS 대신, 
   이전 단계와 현재 단계의 차이를 이용해 진행 방향으로 더 큰 걸음을 내딛는 
   외삽법(Line Search와 유사)을 도입하여 늪을 빠르게 탈출한다.

2. 가속도 제어:
   외삽 계수(alpha)를 고정하지 않고, 잔차가 줄어들면 가속(alpha 증가)하고 
   잔차가 늘어나면 감속(alpha=1 리셋 및 롤백)하는 적응형 로직을 통해 
   비볼록 공간에서도 안정적인 하강을 보장한다.

3. 대칭성 및 리프팅 유지:
   이미 검증된 열 균형화(Balance)와 반올림-리프팅(Lifting)은 유지하되, 
   리프팅 시도 시점에 도달하기 전까지의 ALS 효율을 극대화하여 
   '정확해 분지'에 도달할 확률을 높였다.
"""

import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "als_state.json"
PARAMS_PATH = HERE / "params.json"
LADDER = [(2, 7), (3, 23), (3, 22), (3, 21)]

DISCRETE_GRID = np.array([-1.0, -0.5, 0.0, 0.5, 1.0])

TOL = 1e-13
POLISH_ENTER = 1e-3
POLISH_ITERS = 15000
LIFT_ENTER = 3e-2
LIFT_ROUNDS = 8
DAMP0 = 1e-3
ANNEAL_FRAC = 0.5


def load_params():
    defaults = {"iters": 2000, "noise_scale": 0.1, "use_perturbation": False}
    try:
        if PARAMS_PATH.exists():
            with open(PARAMS_PATH, "r") as f:
                defaults.update(json.load(f))
    except Exception:
        pass
    return defaults


def matmul_tensor(b: int) -> np.ndarray:
    n = b * b
    T = np.zeros((n, n, n), dtype=np.float64)
    for i in range(b):
        for l in range(b):
            for j in range(b):
                T[i * b + l, l * b + j, i * b + j] = 1.0
    return T


def _residual(T, U, V, W, normT):
    R = np.einsum("ir,jr,kr->ijk", U, V, W)
    return float(np.linalg.norm(R - T) / normT)


def _balance(U, V, W):
    nu = np.linalg.norm(U, axis=0)
    nv = np.linalg.norm(V, axis=0)
    nw = np.linalg.norm(W, axis=0)
    prod = nu * nv * nw
    live = prod > 1e-300
    s = np.ones_like(prod)
    s[live] = np.cbrt(prod[live])

    def rescale(A, norms):
        out = A.copy()
        out[:, live] = A[:, live] / (norms[live] + 1e-308) * s[live]
        return out

    return rescale(U, nu), rescale(V, nv), rescale(W, nw)


def _als_sweep(T, U, V, W, iters, damp0=DAMP0, anneal_frac=ANNEAL_FRAC,
               frozen=None, tol=TOL, normT=None, rng=None, noise_scale=0.0,
               use_perturbation=False):
    if normT is None:
        normT = np.linalg.norm(T)
    
    anneal_end = max(1, int(iters * anneal_frac))
    res = _residual(T, U, V, W, normT)
    best = (U.copy(), V.copy(), W.copy(), res)

    # 외삽(Extrapolation)을 위한 이전 상태 저장
    U_prev, V_prev, W_prev = U.copy(), V.copy(), W.copy()
    alpha = 1.0  # 가속 계수
    
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        for it in range(iters):
            if it < anneal_end:
                lam = damp0 * (1.0 - it / anneal_end) ** 2
            else:
                lam = 0.0

            # 인자 보관 (실패 시 복구용)
            U_old, V_old, W_old = U.copy(), V.copy(), W.copy()

            for mode in range(3):
                if mode == 0:
                    G = (V.T @ V) * (W.T @ W)
                    RHS = np.einsum("ijk,jr,kr->ir", T, V, W)
                elif mode == 1:
                    G = (U.T @ U) * (W.T @ W)
                    RHS = np.einsum("ijk,ir,kr->jr", T, U, W)
                else:
                    G = (U.T @ U) * (V.T @ V)
                    RHS = np.einsum("ijk,ir,jr->kr", T, U, V)

                A = G + lam * np.eye(G.shape[0])
                try:
                    X = np.linalg.solve(A, RHS.T).T
                except np.linalg.LinAlgError:
                    X = np.linalg.lstsq(A.T, RHS.T, rcond=None)[0].T

                if mode == 0:
                    U = X
                elif mode == 1:
                    V = X
                else:
                    W = X

                if frozen is not None:
                    for arr, (mask, val) in zip((U, V, W), frozen):
                        if mask is not None and mask.any():
                            arr[mask] = val[mask]

            # 외삽 가속: U_next = U_curr + alpha * (U_curr - U_prev)
            if it > 0:
                U_extrap = U + (alpha - 1.0) * (U - U_prev)
                V_extrap = V + (alpha - 1.0) * (V - V_prev)
                W_extrap = W + (alpha - 1.0) * (W - W_prev)
                
                # 외삽 후 잔차 확인
                res_new = _residual(T, U_extrap, V_extrap, W_extrap, normT)
                if res_new < res:
                    # 가속 성공
                    U, V, W, res = U_extrap, V_extrap, W_extrap, res_new
                    alpha = min(alpha * 1.05, 1.5) # 가속도 점증
                else:
                    # 가속 실패: 리셋 및 단순 ALS 결과 수용
                    res = _residual(T, U, V, W, normT)
                    alpha = 1.0
            else:
                res = _residual(T, U, V, W, normT)

            U_prev, V_prev, W_prev = U_old, V_old, W_old

            if res < best[3]:
                best = (U.copy(), V.copy(), W.copy(), res)
            
            if res < tol:
                break
                
            if it % 500 == 0 and use_perturbation and rng is not None:
                # 가끔씩 흔들어주어 고착 방지
                scale = noise_scale * (res + 1e-8)
                U += rng.normal(0, scale, U.shape)

    return best


def cp_als(T, m, iters=2000, seed=0, init_U=None, init_V=None, init_W=None,
           noise_scale=0.0, use_perturbation=False, polish=True):
    rng = np.random.default_rng(seed)
    n = T.shape[0]
    
    # 지능적 초기화: Matmul 텐서의 경우 약간의 정규분포가 유리함
    U = rng.normal(0, 1, (n, m)) if init_U is None else np.array(init_U, dtype=np.float64)
    V = rng.normal(0, 1, (n, m)) if init_V is None else np.array(init_V, dtype=np.float64)
    W = rng.normal(0, 1, (n, m)) if init_W is None else np.array(init_W, dtype=np.float64)

    normT = np.linalg.norm(T)
    U, V, W, res = _als_sweep(T, U, V, W, iters, rng=rng, normT=normT,
                              noise_scale=noise_scale, use_perturbation=use_perturbation)

    if polish and TOL <= res < POLISH_ENTER:
        U, V, W, res = _als_sweep(T, U, V, W, POLISH_ITERS, damp0=0.0, normT=normT)
    return U, V, W, res


def _lift(T, U, V, W, res, normT, iters):
    best = (U.copy(), V.copy(), W.copy(), res)

    for r in range(LIFT_ROUNDS):
        U0, V0, W0, res0 = best
        Ub, Vb, Wb = _balance(U0, V0, W0)
        # 라운드가 진행될수록 더 공격적으로 격자에 붙임
        thresh = 0.015 * (r + 1)

        frozen = []
        any_frozen = False
        for A in (Ub, Vb, Wb):
            d = np.abs(A[..., None] - DISCRETE_GRID[None, None, :])
            idx = np.argmin(d, axis=-1)
            nearest = DISCRETE_GRID[idx]
            mask = np.min(d, axis=-1) <= thresh
            frozen.append((mask, nearest))
            any_frozen = any_frozen or bool(mask.any())
        
        if not any_frozen:
            continue

        Uc, Vc, Wc = Ub.copy(), Vb.copy(), Wb.copy()
        for arr, (mask, val) in zip((Uc, Vc, Wc), frozen):
            arr[mask] = val[mask]

        # 고정된 상태에서 남은 자유도 수렴
        Uc, Vc, Wc, resc = _als_sweep(T, Uc, Vc, Wc, iters, damp0=1e-7,
                                      frozen=frozen, normT=normT)
        if math.isfinite(resc) and resc < best[3]:
            best = (Uc, Vc, Wc, resc)
            if resc < TOL:
                break
    return best


def factors_to_scheme(U: np.ndarray, V: np.ndarray, W: np.ndarray, b: int, m: int) -> dict:
    A = [{(i, j): float(U[i * b + j, k]) for i in range(b) for j in range(b)} for k in range(m)]
    B = [{(i, j): float(V[i * b + j, k]) for i in range(b) for j in range(b)} for k in range(m)]
    C = [
        {(i, j): [(k, float(W[i * b + j, k])) for k in range(m)]}
        for i in range(b)
        for j in range(b)
    ]
    return {"b": b, "m": m, "A_coeffs": A, "B_coeffs": B, "C_coeffs": C}


class Searcher:
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
        params = load_params()
        budget = int(params.get("iters", 2000))
        noise = float(params.get("noise_scale", 0.1))
        perturb = bool(params.get("use_perturbation", False))

        T = matmul_tensor(b)
        normT = np.linalg.norm(T)

        # 다중 재시작으로 다양한 초기점 탐색
        per_restart = max(500, budget // 3)
        restarts = max(1, budget // per_restart)

        base_seed = int(self.state["attempt"]) * 1337
        best = None
        
        for r in range(restarts):
            # 1. ALS 탐색
            U, V, W, res = cp_als(T, m, iters=per_restart, seed=base_seed + r,
                                  noise_scale=noise, use_perturbation=perturb)
            
            # 2. 리프팅 (충분히 가까워진 경우만)
            if res < LIFT_ENTER:
                U, V, W, res = _lift(T, U, V, W, res, normT, per_restart)
            
            if best is None or res < best[3]:
                best = (U, V, W, res)
            
            if best[3] < TOL:
                break

        U, V, W, res = best
        scheme = factors_to_scheme(U, V, W, b, m)
        scheme["_als_residual"] = res
        self.state["attempt"] += 1
        self._save()
        return scheme

    def record(self, ok: bool):
        if ok and self.state["stage"] < len(LADDER) - 1:
            self.state["stage"] += 1
            self.state["attempt"] = 0
            self._save()


def propose() -> dict:
    return Searcher().propose()