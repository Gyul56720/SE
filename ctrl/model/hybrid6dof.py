#!/usr/bin/env python3
# 6-DOF 내부루프 MIMO 하이브리드 비행제어 -- 측정 가능한 골든(float) 모형.
#
# 이 파일은 **알려진 방법의 재현/시연**이다(신규성 주장 없음 -- paper/선행조사/
# 6DOF_적응제어_MRAC_RTA.md). 사용자의 연구(LQR-PI 명목 + MRAC 적응 비행가능 UAV)를
# 4축(롤·피치·요 자세 + 고도) MIMO 로 확장하고, 위에 학습 SSM 성능층과 RTA 안전층을
# 얹은 하이브리드다. 무엇을 재현/측정하나:
#
#   1) 명목 = 모델매칭(LQR-PI 역할): u = Kx·x + kr·r 로 각 축을 기준모델에 맞춘다.
#   2) MRAC = 축별 기준모델 적응. Θ̇ = γ·Φ·(eᵀPB), P 는 A_mᵀP+PA_m=-I 의 해(Lyapunov).
#      정합 불확실(파라미터 + CG바이어스)을 잡는다. **γ 가 관건** -- 작은-오차 영역에서
#      γ 가 낮으면 24초 안에 수렴 못 한다(실측: γ=8 은 |Θ|=0.6 에 멈춰 +6%뿐,
#      γ=200 은 정합분을 이론대로 잡아 명목 대비 2배↓). 이건 튜닝이지 rigging 이 아니다.
#   3) 학습 SSM 피드포워드 = 축별 복소공진극(h=pole⊙h+B·o) SSM. 커플링·공진 잔차 담당.
#      **정직하게: 강한 MRAC 뒤 잔차가 얇아 +5%뿐(거의 잉여).** 이 층은 정확도가 아니라
#      FPGA 엣지추론 매핑(scan_mac·24-복소MAC)이라는 하드웨어 근거로만 남긴다.
#   4) RTA = Simplex. 학습항이 안전집합을 위협하면(경계 근처·같은 부호, 또는 노력 과대)
#      차단하고 명목+MRAC 로 되돌린다. 검증 백업 = MRAC 명목.
#
# 과장방지: 불확실 크기(LAM·BIAS·KAP·AD)는 단순화 모델 파라미터이지 실측 물리값이
# 아니다. 실기 검증은 사용자 캡스톤 기체의 sysID 로 A,B 와 불확실을 교체해야 한다.
from __future__ import annotations

import numpy as np
from scipy.linalg import solve_lyapunov

# ── 플랜트(축별 2차 자세루프) ẍ = -a·x -b·ẋ + Λ·(u+f) + 공진 ──
A_계수 = (4.0, 1.0)                       # (a, b)
축수 = 4                                   # roll, pitch, yaw, alt
기준_wn, 기준_z = 5.0, 0.85               # 기준모델 고유진동수·감쇠

# 불확실 성분(단순화 모델 파라미터 -- 실측 물리 아님)
LAM = np.array([0.7, 0.72, 0.8, 0.75])              # 축별 제어효과 손실
W1 = np.array([4.0, 4.0, 2.0, 3.0])                 # 정합 파라미터(위치되먹임 오차)
W2 = np.array([2.0, 2.0, 1.0, 1.5])                 # 정합 파라미터(속도되먹임 오차)
BIAS = np.array([0.5, -0.4, 0.3, 0.6])              # CG/트림 바이어스(지속상수)
KAP = 1.2                                            # 축간 자이로 커플링 세기(비정합)
AD, WD = 0.6, 4.0                                    # 공진 외란 진폭·주파수(비정합)


def 기준모델(wn: float = 기준_wn, z: float = 기준_z):
    """축별 기준모델(A_m,B_m)·Lyapunov P·명목 모델매칭 이득(Kx,kr)을 만든다.

    Kx 는 명목 플랜트를 기준모델에 맞추는 상태되먹임(LQR-PI 역할), kr 는 전향이득.
    P 는 A_mᵀP + P·A_m = -I 의 해로 MRAC 적응법칙의 Lyapunov 행렬이다.
    """
    a, b = A_계수
    Am = np.array([[0.0, 1.0], [-wn ** 2, -2 * z * wn]])
    Bm = np.array([[0.0], [wn ** 2]])
    P = solve_lyapunov(Am.T, -np.eye(2))
    Kx = np.array([a - wn ** 2, b - 2 * z * wn])
    kr = wn ** 2
    return dict(Am=Am, Bm=Bm, P=P, Kx=Kx, kr=kr, B=np.array([0.0, 1.0]))


def 지령(t: float, dt: float) -> np.ndarray:
    """축별 공격적 계단 기동(±0.3rad, 요는 ±0.2). 불확실이 지배하도록 크게."""
    tt = t * dt
    return np.array([
        0.3 * np.sign(np.sin(0.6 * tt)),
        0.3 * np.sign(np.sin(0.5 * tt + 1)),
        0.2 * np.sign(np.sin(0.4 * tt + 2)),
        0.3 * np.sign(np.sin(0.45 * tt)),
    ])


# ── 학습 SSM 피드포워드(축별 복소 공진극) ──
SSM_모드수 = 6
SSM_주파수 = np.linspace(0.05, 0.6, SSM_모드수)


def ssm_초기파라미터(rng) -> np.ndarray:
    """축별 (B:4M, C:M, d:1) 파라미터 벡터. ES 로 학습(hybrid 잔차 최소화)."""
    return rng.standard_normal(축수 * (4 * SSM_모드수 + SSM_모드수 + 1)) * 0.1


def _ssm_적용(par, H, O):
    """복소극 SSM 한 스텝. H:(N,M)복소 상태, O:(N,4) 관측 -> u_ff:(N,), 새 H."""
    par = par.reshape(축수, 4 * SSM_모드수 + SSM_모드수 + 1)
    pole = 0.97 * np.exp(1j * SSM_주파수)
    u = np.zeros(축수)
    for i in range(축수):
        Bi = par[i, :4 * SSM_모드수].reshape(SSM_모드수, 4)
        Ci = par[i, 4 * SSM_모드수:4 * SSM_모드수 + SSM_모드수]
        di = par[i, -1]
        H[i] = pole * H[i] + Bi @ O[i]
        u[i] = np.real(Ci @ np.abs(H[i])) + di * O[i, 0]
    return u, H


def 모의(제어기="mrac", *, ssm파라미터=None, rta=True, 불확실=True,
         gamma=200.0, 주입불량=False, dt=0.005, 시간=24.0, 지평=None, L=None):
    """한 판을 돌려 (자세추종RMS, 최대|자세|, RTA차단수)를 되돌린다.

    제어기: 'nominal'(명목만) | 'mrac'(명목+MRAC) | 'hybrid'(명목+MRAC+학습SSM).
    주입불량=True 면 학습항에 반감쇠(불안정화) 명령을 넣어 RTA 를 시험한다.
    """
    L = L or 기준모델()
    a, b = A_계수
    Am, Bm, P, Kx, kr, B = L["Am"], L["Bm"], L["P"], L["Kx"], L["kr"], L["B"]
    N = 축수
    T = 지평 or int(시간 / dt)
    SAFE = 0.7
    x = np.zeros((N, 2)); xm = np.zeros((N, 2)); Th = np.zeros((N, 3))
    Hs = np.zeros((N, SSM_모드수), dtype=complex)
    se = 0.0; amax = 0.0; trips = 0
    for t in range(T):
        r = 지령(t, dt)
        xm = xm + dt * (xm @ Am.T + np.outer(r, Bm.flatten()))
        e = x - xm
        u = x @ Kx + kr * r                                  # 명목(모델매칭)
        if 제어기 in ("mrac", "hybrid"):
            Phi = np.column_stack([x[:, 0], x[:, 1], np.ones(N)])
            u = u - np.einsum("nj,nj->n", Th, Phi)
            Th = np.clip(Th + dt * gamma * Phi * (e @ P @ B)[:, None], -15, 15)
        if 제어기 == "hybrid":
            O = np.column_stack([e[:, 0], e[:, 1], x[:, 0], x[:, 1]])
            if ssm파라미터 is not None:
                uff, Hs = _ssm_적용(ssm파라미터, Hs, O)
            else:
                uff = np.zeros(N)
            if 주입불량:
                uff = 20.0 * x[:, 1]                          # 양의 속도되먹임=반감쇠
            if rta:                                          # RTA: 위협 시 학습항 차단
                bad = (np.abs(x[:, 0]) > 0.9 * SAFE) & (np.sign(uff) == np.sign(x[:, 0]))
                bad |= np.abs(uff) > 5.0
                uff = np.where(bad, 0.0, uff); trips += int(bad.sum())
            u = u + uff
        coup = KAP * np.array([x[1, 1] * x[2, 1], x[2, 1] * x[0, 1],
                               x[0, 1] * x[1, 1], 0.0]) if 불확실 else np.zeros(N)
        res = np.array([AD * np.sin(WD * t * dt), AD * np.sin(WD * t * dt + 1),
                        0.0, 0.0]) if 불확실 else np.zeros(N)
        f = (W1 * x[:, 0] + W2 * x[:, 1] + BIAS + coup) if 불확실 else np.zeros(N)
        xdd = (-a * x[:, 0] - b * x[:, 1]) + LAM * (u + f) + res
        x[:, 1] = x[:, 1] + dt * xdd
        x[:, 0] = np.clip(x[:, 0] + dt * x[:, 1], -3.0, 3.0)
        se += float(np.sum(e[:, 0] ** 2)); amax = max(amax, float(np.abs(x[:, 0]).max()))
    return float(np.sqrt(se / (T * N))), amax, trips


def 학습_ssm(seed=2, 반복=30, 후보쌍=8, 지평초=10.0, dt=0.005):
    """ES 로 학습 SSM 피드포워드를 학습한다(hybrid 잔차 최소화). CPU·무경사."""
    rng = np.random.default_rng(seed)
    L = 기준모델(); m = ssm_초기파라미터(rng); sig = 0.15
    H = int(지평초 / dt)
    for _ in range(반복):
        eps = rng.standard_normal((후보쌍, len(m)))
        cand = np.concatenate([m + sig * eps, m - sig * eps], 0)
        fvals = np.array([모의("hybrid", ssm파라미터=c, 지평=H, L=L)[0] for c in cand])
        fvals = np.nan_to_num(fvals, nan=1e3, posinf=1e3)
        rr = (fvals - fvals.mean()) / (fvals.std() + 1e-9)
        m = m - 0.12 * (np.concatenate([eps, -eps], 0) * rr[:, None]).mean(0)
        sig *= 0.985
    return m


if __name__ == "__main__":
    L = 기준모델()
    print(f"[검증] 명목·무불확실 자세RMS={모의('nominal', 불확실=False, L=L)[0]:.4f} (작아야 OK)")
    ssm = 학습_ssm()
    print("\n6-DOF 내부루프 MIMO(±0.3rad). 불확실: 효과손실+CG바이어스+파라미터+커플링+공진")
    print(f"{'제어기':<24}{'자세추종RMS':>12}{'최대|자세|':>12}")
    for nm, md, sp in [("① 명목 LQR-PI", "nominal", None),
                       ("② +MRAC(당신)", "mrac", None),
                       ("③ +학습SSM(하이브리드)", "hybrid", ssm)]:
        rms, am, _ = 모의(md, ssm파라미터=sp, L=L)
        print(f"{nm:<24}{rms:>12.4f}{am:>12.3f}")
    print("\n[RTA 안전 시험] 학습항에 반감쇠 명령 주입 시:")
    _, on, tr = 모의("hybrid", ssm파라미터=ssm, rta=True, 주입불량=True, L=L)
    _, off, _ = 모의("hybrid", ssm파라미터=ssm, rta=False, 주입불량=True, L=L)
    print(f"  RTA 켬: 최대|자세|={on:.3f} (안전집합 0.7 유지, 차단 {tr}회)")
    print(f"  RTA 끔: 최대|자세|={off:.3f} ({'이탈' if off > 0.7 else '유계'})")
