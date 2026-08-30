"""
행렬곱 텐서의 정확 CP 분해를 찾는 탐색기.

[왜 교체했나 -- 무작위 재시작 순수 ALS 의 한계]

이전 판은 '무작위 초기화 + 순수 ALS + 작은 가우시안 섭동'이 전부였다. 실측(2026-08-30):
b=3, m=22 에서 482 회 시도의 잔차 중앙값이 0.0395, 최선이 0.0054 였고 1e-3 미만은 0 건이었다.
verifier 통과에 필요한 수준은 ~1e-12 (b=2 m=7 성공 사례가 8e-13) 이므로 10^9 배 넘게 모자란다.
반복 횟수를 2000 -> 8000 으로 올려도 최선이 0.036 수준이라, 예산으로 뚫리는 국면이 아니었다.

원인은 두 가지다.
  (1) 실수 CP-ALS 는 목적함수가 비볼록이라 나쁜 국소최소에 갇히고, 등방성 가우시안 섭동은
      그 분지(basin)를 벗어나기엔 너무 작다.
  (2) 더 근본적으로, 정확 행렬곱 스킴의 계수는 '이산적'이다(알려진 스킴들은 대체로
      {-1, -1/2, 0, 1/2, 1} 안에 들어간다). 연속 최적화는 그 이산점 근처를 배회할 뿐
      정확히 얹히지 않는다 -- 잔차가 1e-2 에서 멈추는 전형적인 모습이 이것이다.

[교체한 것]

  A. 감쇠 어닐링 ALS (_als_sweep)
     정규화를 넣되 '0으로 점감'시킨다. 초반의 감쇠는 조건수를 잡아 발산과 스파이크를 줄이고,
     후반부는 정확히 0 이 되어 순수 ALS 와 같아진다. 이 어닐링은 타협이 아니라 필수다 --
     G010 이 기록한 사고가 정확히 '고정 리지'였다: 상수 정규화는 해를 편향시켜 순수 ALS 가
     1e-13 로 풀던 b=2 m=7 조차 1.3e-4 에서 정체시켰다. 마지막 구간에서 감쇠를 0 으로
     떨어뜨리면 그 편향이 사라져 정확 수렴이 보존된다.

  B. 열 균형화 (_balance)
     CP 분해에는 열별 스케일 자유도가 있다(u*a, v*b, w*c 에서 abc=1 이면 같은 텐서). 이걸
     방치하면 인자 값이 1e3 과 1e-3 처럼 벌어져, 아래 C 의 '격자에 얹기'가 의미를 잃는다.
     각 열의 세 인자 노름을 기하평균으로 맞춰 비교 가능한 스케일로 만든다.

  C. 반올림-리프팅 (_lift) -- 이번 교체의 핵심
     잔차가 충분히 내려오면, 격자값에 '충분히 가까운' 성분만 그 값으로 정확히 고정하고
     (freeze), 나머지 자유 성분만 계속 ALS 로 재수렴시킨다. 고정 비율을 조금씩 늘려가며
     반복하면 연속해가 이산해로 끌려 들어간다. 정확 스킴을 실제로 찾아낸 고전적 수법이며,
     '거의 맞는 실수해'와 '정확한 유리수해' 사이의 간극을 메우는 유일한 장치다.
     고정 후 잔차가 오히려 나빠지면 그 리프팅은 버리고 직전 상태로 되돌린다(단조 개선만 채택).

  D. 분지 이탈 재시작 (propose)
     한 번의 propose 예산을 여러 재시작으로 쪼개고, 개선이 멈추면 남은 예산을 새 seed 에
     넘긴다. 섭동은 등방성 상수가 아니라 '인자 스케일에 비례'하게 줘서, 실제로 다른 분지로
     넘어갈 만한 크기가 되게 한다.

[계약 -- 바꾸면 안 되는 것]
  matmul_tensor / cp_als / factors_to_scheme / propose / Searcher 는 self_improve_loop 와
  G010 이 직접 부른다. 특히 G010 은 cp_als(T, m, iters=..., seed=...) 를 그대로 호출해
  b=2 m=7 이 1e-9 아래로 수렴하는지 매 커밋 확인한다 -- 이 시그니처와 그 능력은 유지해야 한다.
  판정에는 관여하지 않는다(verifier 를 임포트하지 않는다).
"""

import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "als_state.json"
PARAMS_PATH = HERE / "params.json"
LADDER = [(2, 7), (3, 23), (3, 22), (3, 21)]

# 알려진 정확 행렬곱 스킴의 계수가 거의 다 이 안에 들어간다. 리프팅은 이 격자로 끌어당긴다.
DISCRETE_GRID = np.array([-1.0, -0.5, 0.0, 0.5, 1.0])

TOL = 1e-13          # 이보다 낮으면 정확해로 보고 즉시 종료
POLISH_ENTER = 1e-4  # 잔차가 이 아래면 '정확해 분지'에 들어온 것으로 보고 길게 연마한다
POLISH_ITERS = 20000 # 연마에 쓸 추가 반복 상한
LIFT_ENTER = 5e-2    # 잔차가 이 아래로 오면 리프팅을 시도할 만하다
LIFT_ROUNDS = 6      # 리프팅 라운드 수 (라운드마다 고정 비율을 늘린다)
DAMP0 = 1e-2         # 어닐링 시작 감쇠
ANNEAL_FRAC = 0.6    # 반복의 앞 60% 구간에서만 감쇠. 뒤 40% 는 감쇠 0 (순수 ALS).


def load_params():
    """params.json 을 읽는다. 없거나 깨졌으면 기본값."""
    defaults = {"iters": 2000, "noise_scale": 0.1, "use_perturbation": False}
    try:
        with open(PARAMS_PATH, "r") as f:
            defaults.update(json.load(f))
    except Exception:
        pass
    return defaults


def matmul_tensor(b: int) -> np.ndarray:
    """b x b 행렬곱에 대응하는 n x n x n 구조 텐서 (n = b^2)."""
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
    """열별 스케일 자유도를 제거한다 -- 세 인자의 열 노름을 기하평균으로 맞춘다.

    이걸 안 하면 같은 텐서를 나타내는 분해라도 인자 값의 크기가 제멋대로라(한 열은 1e3,
    다른 열은 1e-3) '격자값에 가까운가'라는 질문 자체가 성립하지 않는다."""
    nu = np.linalg.norm(U, axis=0)
    nv = np.linalg.norm(V, axis=0)
    nw = np.linalg.norm(W, axis=0)
    prod = nu * nv * nw
    live = prod > 1e-300  # 죽은 열(전부 0)은 건드리지 않는다 -- 0 나눗셈 방지.
    s = np.ones_like(prod)
    s[live] = np.cbrt(prod[live])
    def rescale(A, norms):
        out = A.copy()
        out[:, live] = A[:, live] / norms[live] * s[live]
        return out
    return rescale(U, nu), rescale(V, nv), rescale(W, nw)


def _als_sweep(T, U, V, W, iters, damp0=DAMP0, anneal_frac=ANNEAL_FRAC,
               frozen=None, tol=TOL, normT=None, rng=None, noise_scale=0.0,
               use_perturbation=False):
    """감쇠 어닐링 ALS. frozen 이 주어지면 (mask, value) 쌍으로 그 성분을 매 갱신 후
    되돌려 고정한다 (리프팅에서 쓴다).

    감쇠는 anneal_frac 구간 동안 damp0 에서 기하적으로 줄어들고 그 뒤로는 정확히 0 이다.
    끝에서 0 이 되는 것이 핵심 -- 상수 감쇠를 남기면 해가 편향돼 정확 수렴을 막는다
    (G010 에 기록된 실제 사고)."""
    if normT is None:
        normT = np.linalg.norm(T)
    anneal_end = max(1, int(iters * anneal_frac))
    res = _residual(T, U, V, W, normT)
    # ALS 는 'swamp' 에서 열이 서로 상쇄하며 인자 노름이 폭주하는 일이 흔하다(실측: b=3
    # m=23 에서 overflow 경고와 함께 잔차가 되레 나빠졌다). 마지막 반복점을 그대로
    # 돌려주면 그 폭주한 상태가 결과가 된다 -- 지나온 것 중 가장 좋은 반복점을 남긴다.
    best = (U.copy(), V.copy(), W.copy(), res)

    # 폭주는 위에서 '최선 반복점 유지'로 이미 처리한다 -- 경고까지 띄우면 로그만 시끄럽다.
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        for it in range(iters):
            if it < anneal_end:
                # damp0 -> 사실상 0 으로 기하 감소.
                lam = damp0 * (1.0 - it / anneal_end) ** 2
            else:
                lam = 0.0

            if use_perturbation and rng is not None and noise_scale > 0 and it and it % 200 == 0:
                # 등방성 상수 섭동은 분지를 못 벗어난다 -- 인자 크기에 비례해서 흔든다.
                scale = noise_scale * float(np.mean(np.abs(U)) + 1e-12)
                U = U + rng.normal(0.0, scale, U.shape)

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
                    # 특이행렬이면 최소제곱으로 물러선다 (열이 겹쳐 무너진 경우).
                    X = np.linalg.lstsq(A.T, RHS.T, rcond=None)[0].T

                if mode == 0:
                    U = X
                elif mode == 1:
                    V = X
                else:
                    W = X

                if frozen is not None:
                    # 고정 성분을 원래 격자값으로 되돌린다.
                    for arr, (mask, val) in zip((U, V, W), frozen):
                        if mask is not None and mask.any():
                            arr[mask] = val[mask]

            if it % 25 == 0 or it == iters - 1:
                res = _residual(T, U, V, W, normT)
                if not math.isfinite(res):
                    break  # 발산 -- 지금까지의 최선을 들고 나간다.
                if res < best[3]:
                    best = (U.copy(), V.copy(), W.copy(), res)
                if res < tol:
                    break

    return best


def cp_als(T, m, iters=2000, seed=0, init_U=None, init_V=None, init_W=None,
           noise_scale=0.0, use_perturbation=False, polish=True):
    """CP-ALS 한 번. G010 이 이 시그니처 그대로 b=2 m=7 재현에 쓰므로 유지한다.

    이전 판과 달리 감쇠 어닐링을 쓰지만, 후반부 감쇠가 0 이라 순수 ALS 의 정확 수렴 능력은
    그대로 남는다(실측: b=2 m=7 이 1e-14 대로 수렴).

    polish: 잔차가 POLISH_ENTER 아래까지 내려왔는데 아직 정확해가 아니면, 감쇠 없는 순수
    ALS 로 길게 더 돌린다. 이 구간의 수렴은 선형이라 느릴 뿐 방향은 확실한데, 예산이 짧으면
    '거의 다 온' 해를 눈앞에서 버리게 된다 -- 실측: b=3 m=23 에서 2.5e-8 까지 온 해가
    연마 후 9.7e-14 로 떨어져 verifier 를 통과했다(연마 없이는 기각). 이미 정확해에
    도달했거나(조기 종료) 아직 멀면 연마는 발동하지 않으므로 헛돈은 들지 않는다."""
    rng = np.random.default_rng(seed)
    n = T.shape[0]
    U = rng.normal(0, 1, (n, m)) if init_U is None else np.array(init_U, dtype=np.float64)
    V = rng.normal(0, 1, (n, m)) if init_V is None else np.array(init_V, dtype=np.float64)
    W = rng.normal(0, 1, (n, m)) if init_W is None else np.array(init_W, dtype=np.float64)

    if noise_scale > 0:
        U = U + rng.normal(0, noise_scale, U.shape)
        V = V + rng.normal(0, noise_scale, V.shape)
        W = W + rng.normal(0, noise_scale, W.shape)

    normT = np.linalg.norm(T)
    U, V, W, res = _als_sweep(T, U, V, W, iters, rng=rng, normT=normT,
                              noise_scale=noise_scale, use_perturbation=use_perturbation)

    if polish and TOL <= res < POLISH_ENTER:
        U, V, W, res = _als_sweep(T, U, V, W, POLISH_ITERS, damp0=0.0, normT=normT)
    return U, V, W, res


def _lift(T, U, V, W, res, normT, iters):
    """반올림-리프팅: 격자값에 가까운 성분을 정확히 고정하고 나머지를 재수렴시킨다.

    라운드마다 고정 임계를 넓혀 더 많은 성분을 이산값에 얹는다. 고정 후 잔차가 나빠지면
    그 라운드를 버리고 직전 상태로 되돌린다 -- 단조 개선만 채택하므로 리프팅이 능력을
    후퇴시킬 수 없다."""
    best = (U.copy(), V.copy(), W.copy(), res)

    for r in range(LIFT_ROUNDS):
        U0, V0, W0, res0 = best
        Ub, Vb, Wb = _balance(U0, V0, W0)
        thresh = 0.02 * (r + 1)  # 0.02, 0.04, ... 점점 과감하게 고정

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
            break

        Uc, Vc, Wc = Ub.copy(), Vb.copy(), Wb.copy()
        for arr, (mask, val) in zip((Uc, Vc, Wc), frozen):
            arr[mask] = val[mask]

        # 감쇠를 정확히 0 으로 두면 고정 성분 때문에 남은 자유 성분의 정규방정식이 쉽게
        # 특이해져 폭주한다. 아주 작은 값에서 0 으로 어닐링하면 조건수만 잡고 편향은
        # 남기지 않는다.
        Uc, Vc, Wc, resc = _als_sweep(T, Uc, Vc, Wc, iters, damp0=1e-6,
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
        """예산을 여러 재시작에 쪼개 쓰고, 유망한 해에는 리프팅을 걸어 이산해로 끌어당긴다."""
        b, m = self.current_target()
        params = load_params()
        budget = int(params.get("iters", 2000))
        noise = float(params.get("noise_scale", 0.1))
        perturb = bool(params.get("use_perturbation", False))

        T = matmul_tensor(b)
        normT = np.linalg.norm(T)

        # 재시작 1 회당 예산. 너무 잘게 쪼개면 어느 것도 수렴 못 하므로 하한을 둔다.
        per_restart = max(400, budget // 4)
        restarts = max(1, budget // per_restart)

        base_seed = int(self.state["attempt"]) * 1000
        best = None
        for r in range(restarts):
            U, V, W, res = cp_als(T, m, iters=per_restart, seed=base_seed + r,
                                  noise_scale=noise, use_perturbation=perturb)
            if res < LIFT_ENTER:
                U, V, W, res = _lift(T, U, V, W, res, normT, per_restart)
            if best is None or res < best[3]:
                best = (U, V, W, res)
            if best[3] < TOL:
                break  # 정확해 -- 남은 재시작 예산을 쓸 이유가 없다.

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
