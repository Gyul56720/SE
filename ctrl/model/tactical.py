#!/usr/bin/env python3
# 전술비행 3층 스택 -- 계획 → MPC 중심궤적 → 편대 수행. 측정 가능한 골든(float).
#
# 재현/시연이다(신규성 없음 -- paper/선행조사/무인체계_편대제어_MPC.md):
#   상위 계획: 직선이 위협원을 뚫으면 우회 웨이포인트 삽입.
#   중위 MPC : 조밀 선형 MPC(이중적분기, 가속도 한계)로 매끄럽고 가능한 중심궤적.
#   하위 수행: N대 편대가 바람 외란 속에서 (중심+회전오프셋)을 추종하며 대형 유지.
#
# 정직한 핵심 측정: 편대는 점이 아니라 폭이 있다. 계획이 '중심'만 피하면 바깥 드론이
# 위협을 뚫는다. 필요 안전마진 = 위협반경 + 편대 반폭 + 하위 실행오차(바람+유지오차).
# 세 층이 얽혀 있어 상위 계획을 하위 실행 오차예산 없이 설계하면 실패한다.
import numpy as np


def 직선이_위협을_뚫나(p, q, c, r) -> bool:
    p, q, c = map(np.asarray, (p, q, c))
    d = q - p
    t = np.clip(np.dot(c - p, d) / np.dot(d, d), 0, 1)
    return float(np.linalg.norm(p + t * d - c)) < r


def 계획(start, goal, threat_c, Rplan):
    """상위: 직선이 (반경 Rplan) 위협을 뚫으면 위로 우회 웨이포인트를 삽입."""
    start = np.asarray(start, float); goal = np.asarray(goal, float)
    threat_c = np.asarray(threat_c, float)
    if 직선이_위협을_뚫나(start, goal, threat_c, Rplan):
        detour = threat_c + np.array([0.0, Rplan + 0.6])
        return np.array([start, detour, goal])
    return np.array([start, goal])


def _mpc행렬(H, dt):
    Sp = np.zeros((H, H))
    for k in range(1, H + 1):
        for i in range(k):
            Sp[k - 1, i] = dt * dt * (k - i - 0.5)
    Minv = np.linalg.inv(Sp.T @ Sp + 0.05 * np.eye(H))
    return Sp, Minv


def _경로점(wps):
    seg = np.diff(wps, axis=0); sl = np.linalg.norm(seg, axis=1)
    cum = np.concatenate([[0], np.cumsum(sl)]); Ltot = cum[-1]
    def pt(s):
        s = np.clip(s, 0, Ltot)
        k = int(np.clip(np.searchsorted(cum, s) - 1, 0, len(seg) - 1))
        return wps[k] + seg[k] * ((s - cum[k]) / sl[k])
    return pt, Ltot


def mpc_중심궤적(wps, goal, dt=0.1, v_des=1.4, a_max=3.0, H=25, Tmax=500):
    """중위: 웨이포인트를 매끄럽게 추종하는 동역학 가능 중심궤적(바람 없는 '계획')."""
    goal = np.asarray(goal, float)
    Sp, Minv = _mpc행렬(H, dt)
    pt, Ltot = _경로점(wps)
    p = wps[0].astype(float).copy(); v = np.zeros(2); s0 = 0.0
    C = [p.copy()]
    ks = np.arange(1, H + 1)
    for _ in range(Tmax):
        acc = np.zeros(2)
        for ax in range(2):
            r = np.array([pt(s0 + kk * dt * v_des)[ax] for kk in ks])
            a = Minv @ (Sp.T @ (r - (p[ax] + ks * dt * v[ax])))
            acc[ax] = a[0]
        n = np.linalg.norm(acc)
        if n > a_max:
            acc = acc / n * a_max
        v = v + dt * acc; p = p + dt * v; s0 = min(s0 + v_des * dt, Ltot)
        C.append(p.copy())
        if np.linalg.norm(p - goal) < 0.3:
            break
    return np.array(C)


def 편대오프셋_V(n_side=2, along=0.7, cross=0.7):
    """V자 편대 본체프레임 오프셋 [along, cross]. 리더 1 + 좌우 각 n_side."""
    off = [[0.0, 0.0]]
    for k in range(1, n_side + 1):
        off.append([-along * k, cross * k])
        off.append([-along * k, -cross * k])
    return np.array(off)


def 편대수행(center, offsets, wind=(0.5, -0.4), dt=0.1, a_max=3.0):
    """하위: N대가 바람 속에서 (중심+진행방향 회전 오프셋)을 추종하며 대형 유지.
    반환: (궤적(T,N,2), 편대유지오차 평균, 각 드론 궤적)."""
    center = np.asarray(center, float); wind = np.asarray(wind, float)
    T = len(center); N = len(offsets)
    head = np.zeros(T)
    for t in range(1, T):
        d = center[t] - center[t - 1]
        head[t] = np.arctan2(d[1], d[0]) if np.linalg.norm(d) > 1e-6 else head[t - 1]
    if T > 1:
        head[0] = head[1]
    P = np.array([center[0] + offsets[i] for i in range(N)], float)
    V = np.zeros((N, 2)); traj = np.zeros((T, N, 2)); ferr = []
    for t in range(T):
        th = head[t]
        Rm = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        tgt = center[t] + offsets @ Rm.T
        vref = (center[t] - center[t - 1]) / dt if t > 0 else np.zeros(2)
        a = 4.0 * (tgt - P) - 3.0 * (V - vref)
        e = P - tgt                                # 이웃 응집(경로그래프)
        a[1:] += 0.8 * (e[:-1] - e[1:])
        a[:-1] += 0.8 * (e[1:] - e[:-1])
        nn = np.linalg.norm(a, axis=1, keepdims=True)
        a = np.where(nn > a_max, a / nn * a_max, a)
        V = V + dt * (a + wind); P = P + dt * V; traj[t] = P
        ferr.append(float(np.linalg.norm(P - tgt, axis=1).mean()))
    fe = float(np.mean(ferr[len(ferr) // 2:]))     # 정착 후 평균 유지오차
    return traj, fe


def 최악_위협여유(traj, threat_c, R) -> float:
    """모든 드론·모든 시점 중 위협 중심까지 최소거리 − R (음수=관통)."""
    threat_c = np.asarray(threat_c, float)
    N = traj.shape[1]
    return float(min(np.linalg.norm(traj[:, i] - threat_c, axis=1).min() for i in range(N)) - R)


def 스택_데모(start=(0, 0), goal=(12, 0), threat_c=(6, 0), R=2.0,
             offsets=None, wind=(0.5, -0.4)):
    """세 계획마진(중심만 / +편대폭 / +편대폭+실행마진)에서 최악 위협여유를 잰다."""
    if offsets is None:
        offsets = 편대오프셋_V()
    half_w = float(np.abs(offsets[:, 1]).max())
    cases = [("중심만", R), ("편대폭", R + half_w), ("편대폭+실행마진", R + half_w + 0.8)]
    out = []
    for 이름, Rplan in cases:
        wps = 계획(start, goal, threat_c, Rplan)
        C = mpc_중심궤적(wps, goal)
        traj, fe = 편대수행(C, offsets, wind=wind)
        clr = 최악_위협여유(traj, threat_c, R)
        out.append((이름, Rplan, fe, clr))
    return out


if __name__ == "__main__":
    # 단일기: 계획 없이 직진 vs 계획+MPC
    wps = 계획((0, 0), (10, 0), (5, 0), 2.0)
    print(f"웨이포인트(우회 삽입={len(wps)==3}): {wps.tolist()}")
    for 이름, Rplan, fe, clr in 스택_데모():
        print(f"  {이름:14} Rplan={Rplan:.2f} 편대유지오차={fe:.3f} 최악여유={clr:+.3f} "
              f"{'관통✗' if clr < 0 else '전원회피✓'}")
