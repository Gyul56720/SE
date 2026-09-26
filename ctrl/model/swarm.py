#!/usr/bin/env python3
# 편대(스웜) 제어의 집단 동역학 -- 측정 가능한 골든(float) 모형.
#
# 이 파일은 **알려진 제어이론의 재현/시연**이다(신규성 주장 없음 -- paper/선행조사/
# 무인체계_편대제어_MPC.md). 무엇을 재현하나:
#   1) 편대의 집단모드 = 그라운디드 라플라시안 고유값 -> 폐루프 2차 극 (Olfati-Saber,
#      Fax&Murray 2004). 약감쇠 복소쌍 σ±jω = "편대가 출렁이는" 모드.
#   2) 다운워시 커플링. 후류는 **아래로만** 흐르면 결합행렬이 삼각=멱영이라 고리가 없어
#      절대 발산 못 한다. 근접장 재순환을 α(양방향성)로 켜야 **음강성 단조 발산**이 생김.
#      임계 α* 는 폐루프 A 의 고유값이 우반평면으로 넘는 지점(선형화로 판정).
#   3) 분산 고정모드(Wang&Davison 1973): 커플링이 만든 불안정은 각 드론이 자기상태만
#      보는 분산 제어로는 못 잡는다. 이웃 정보라야 잡는다.
#
# 과장방지: α 는 단순화 모델의 파라미터이지 실측 물리값이 아니다. α*≈0.225 는
# "이 모형 안에서" 의 임계이고, 실제 드론이 그 양방향성에 도달한다는 주장이 아니다.
import numpy as np


def 그라운디드_라플라시안(N: int) -> np.ndarray:
    """경로그래프 0-1-...-(N-1) 라플라시안 + 리더(0) 앵커. 전 편대가 공간에 고정됨."""
    L = np.zeros((N, N))
    for i in range(N - 1):
        L[i, i] += 1; L[i + 1, i + 1] += 1
        L[i, i + 1] -= 1; L[i + 1, i] -= 1
    K = L.copy(); K[0, 0] += 1.0
    return K


def 집단모드(K: np.ndarray, kp: float, kd: float):
    """라플라시안 고유값 λ_k 마다 2차식 s²+kd·λ·s+kp·λ=0 의 극.
    반환: [(λ, σ, ω, ζ, 복소여부)] -- ω>0(복소) 면 진동 모드."""
    lam = np.linalg.eigvalsh(K)
    out = []
    for lk in lam:
        a = kd * lk / 2.0
        disc = kp * lk - a * a
        if disc > 1e-12:
            w = np.sqrt(disc); zeta = a / np.sqrt(kp * lk)
            out.append((float(lk), float(-a), float(w), float(zeta), True))
        else:
            out.append((float(lk), float(-a), 0.0, 1.0, False))
    return out


def 가장_약감쇠_모드(K, kp, kd):
    """편대가 가장 잘 흔들리는(감쇠비 최소) 진동 모드."""
    osc = [m for m in 집단모드(K, kp, kd) if m[4]]
    if not osc:
        return None
    return min(osc, key=lambda m: m[3])   # ζ 최소


# ── 다운워시 커플링 ────────────────────────────────────────────────
def 후류가중(N: int, gap: float = 0.6, Kw: float = 0.9, sz: float = 1.0) -> np.ndarray:
    """수직 컬럼(정렬)에서 위 드론 j 가 아래 드론 i 에 주는 후류가중(아래방향)."""
    z = np.arange(N) * gap
    Wd = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            if z[j] > z[i]:
                Wd[i, j] = Kw / (1 + ((z[j] - z[i]) / sz) ** 2)
    return Wd


def 결합행렬(Wd: np.ndarray, alpha: float) -> np.ndarray:
    """C = W_down + α·W_downᵀ. α=0 순수 아래방향(고리 없음), α=1 완전 양방향."""
    return Wd + alpha * Wd.T


def 폐루프_고유값(C: np.ndarray, kp: float, kd: float) -> np.ndarray:
    """분산 PD + 후류결합의 선형 폐루프 A=[[0,I],[-kp(I-C),-kd(I-C)]] 고유값."""
    N = C.shape[0]
    M = np.eye(N) - C
    A = np.zeros((2 * N, 2 * N))
    A[:N, N:] = np.eye(N)
    A[N:, :N] = -kp * M
    A[N:, N:] = -kd * M
    return np.linalg.eigvals(A)


def 안정한가(C, kp, kd, tol=1e-6) -> bool:
    return 폐루프_고유값(C, kp, kd).real.max() < tol


def 불안정_임계_alpha(Wd, kp, kd, lo=0.0, hi=1.0, iters=50) -> float:
    """이분법으로 α* 를 찾는다 -- 이 위로 컬럼 평형이 불안정(음강성 발산)."""
    if not 안정한가(결합행렬(Wd, lo), kp, kd):
        return lo
    if 안정한가(결합행렬(Wd, hi), kp, kd):
        return hi   # 이 hi 까지도 안정
    for _ in range(iters):
        m = (lo + hi) / 2
        if 안정한가(결합행렬(Wd, m), kp, kd):
            lo = m
        else:
            hi = m
    return hi


# ── 외란 링잉: 임펄스가 예측된 집단모드로 울리는지 독립 대조 ──────────
def 임펄스_링잉_주파수(N=8, kp=4.0, kd=2.0, dt=0.01, T=6000, 타격드론=None):
    """중앙 드론에 임펄스를 주고 편대 링잉 주파수를 측정(영점교차). 예측 ω 와 대조용."""
    K = 그라운디드_라플라시안(N)
    hit = N // 2 if 타격드론 is None else 타격드론
    e = np.zeros(N); v = np.zeros(N)
    hist = np.zeros((T, N))
    for t in range(T):
        w = np.zeros(N)
        if t == int(1.0 / dt):
            w[hit] = 200.0
        v = v + dt * (-kp * (K @ e) - kd * (K @ v) + w)
        e = e + dt * v
        hist[t] = e
    sig = hist[int(1.0 / dt):, hit]; sig = sig - sig.mean()
    zc = np.where(np.diff(np.sign(sig)))[0]
    if len(zc) < 4:
        return None
    per = np.diff(zc[:8]) * dt * 2
    return float(2 * np.pi / per.mean())


if __name__ == "__main__":
    N = 6; kp, kd = 4.0, 3.0
    K = 그라운디드_라플라시안(N)
    m = 가장_약감쇠_모드(K, kp, kd)
    print(f"편대 {N}대: 가장 약감쇠 집단모드 ω={m[2]:.3f} ζ={m[3]:.3f} (복소={m[4]})")
    Wd = 후류가중(N)
    a = 불안정_임계_alpha(Wd, kp, kd)
    print(f"다운워시 불안정 임계 α*≈{a:.3f}  "
          f"(α=0 안정={안정한가(결합행렬(Wd,0),kp,kd)}, α=0.4 안정={안정한가(결합행렬(Wd,0.4),kp,kd)})")
    w = 임펄스_링잉_주파수()
    K8 = 그라운디드_라플라시안(8); m8 = 가장_약감쇠_모드(K8, 4.0, 2.0)
    print(f"임펄스 링잉 ω_meas={w:.3f} vs 예측 {m8[2]:.3f}")
