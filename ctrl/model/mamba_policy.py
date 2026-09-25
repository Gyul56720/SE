#!/usr/bin/env python3
# 신경망 Mamba 제어 정책 -- PI 를 모방학습한다. **순수 numpy(수동 BPTT).**
#
# 왜 numpy 인가: torch 는 무겁고(~800MB) 봇 배포에 부담이다. 그리고 FPGA 쪽은 어차피
# 내가 통제하는 numpy 레퍼런스가 필요하다(ssm/ 골든과 같은 철학). 모델이 작아 손 역전파로 충분.
#
# 이것이 "AI 정책"인 근거(PI 와 다른 점):
#   - 가중치가 **학습**된다(손으로 정한 Kp/Ki 아님).
#   - 게이트 비선형 SiLU 가 들어간다(선형 PI 아님).
#   - 상태 재귀 h=a⊙h+b⊙x 의 a,b 도 학습(대각 SSM = linear-recurrent unit).
# 그런데 재귀 구조는 PI(=scan)와 같아서 **같은 scan_mac 하드웨어**에 올라간다.
#
# 구조(한 Mamba 블록, 대각 SSM):
#   x_t = W_in·o_t                      (M 채널)
#   h_t = a⊙h_{t-1} + b⊙x_t             (a=sigmoid(a_raw)∈(0,1): 학습된 감쇠)
#   y_t = C⊙h_t
#   g_t = SiLU(W_g·o_t + bg)            (비선형 게이트 -- 이것이 '신경망'이게 함)
#   a_pred = W_out·(y_t⊙g_t) + D·o_t    (D: 직접 비례 경로)
import sys, pathlib
import numpy as np

RNG = np.random.default_rng(7)
M = 8          # 상태/모델 채널
DT = 0.05

def silu(u): return u / (1.0 + np.exp(-u))
def dsilu(u):
    s = 1.0/(1.0+np.exp(-u)); return s*(1+u*(1-s))
def sig(u): return 1.0/(1.0+np.exp(-u))

# ---------- 교사: 3축 PI (velocity 지령) ----------
def pi_rollout(target, dist, dstart, T, Kp=4.5, Ki=2.0, p0=None):
    p = np.zeros(3) if p0 is None else np.array(p0,float)
    integ = np.zeros(3)
    O, A = [], []
    for k in range(T):
        e = target - p
        integ = integ + e*DT
        a = Kp*e + Ki*integ                 # PI 속도 지령(교사 행동)
        O.append(e.copy()); A.append(a.copy())
        d = dist if k*DT >= dstart else np.zeros(3)
        p = p + (a - d)*DT
    return np.array(O), np.array(A)

def gen_data(B=48, T=160):
    O, A = [], []
    for _ in range(B):
        tgt = RNG.uniform(-3, 3, 3)
        dist = RNG.uniform(-0.4, 0.4, 3) * (RNG.random(3) < 0.6)
        dstart = RNG.uniform(2, 5)
        o, a = pi_rollout(tgt, dist, dstart, T)
        O.append(o); A.append(a)
    return np.array(O), np.array(A)   # (B,T,3)

# ---------- 파라미터 ----------
def init():
    return {"W_in": RNG.normal(0,0.5,(M,3)), "a_raw": RNG.normal(1.5,0.3,M),  # a≈0.82 시작
            "b": RNG.normal(0,0.3,M), "C": RNG.normal(0,0.5,M),
            "W_g": RNG.normal(0,0.5,(M,3)), "bg": np.zeros(M),
            "W_out": RNG.normal(0,0.3,(3,M)), "D": np.eye(3)*3.0}

# ---------- 순전파 (BPTT용 캐시 저장) ----------
def forward(P, O):
    B,T,_ = O.shape
    a = sig(P["a_raw"])
    X = O @ P["W_in"].T                      # (B,T,M)
    U = O @ P["W_g"].T + P["bg"]             # 게이트 pre
    G = silu(U)
    H = np.zeros((B,T,M)); h = np.zeros((B,M))
    for t in range(T):
        h = a*h + P["b"]*X[:,t,:]
        H[:,t,:] = h
    Y = P["C"]*H                             # (B,T,M)
    Z = Y*G
    Apred = Z @ P["W_out"].T + O @ P["D"].T  # (B,T,3)
    return Apred, {"O":O,"X":X,"U":U,"G":G,"H":H,"Y":Y,"Z":Z,"a":a}

def backward(P, cache, dApred):
    O,X,U,G,H,Y,Z,a = (cache[k] for k in ("O","X","U","G","H","Y","Z","a"))
    B,T,_ = O.shape
    g = {k: np.zeros_like(v) for k,v in P.items()}
    g["W_out"] += np.einsum("btk,btm->km", dApred, Z)
    g["D"]     += np.einsum("btk,btj->kj", dApred, O)
    dZ = dApred @ P["W_out"]                  # (B,T,M)
    dY = dZ*G; dG = dZ*Y
    g["C"] += np.sum(dY*H, axis=(0,1))
    dH = dY*P["C"]                            # from readout
    dU = dG*dsilu(U)
    g["W_g"] += np.einsum("btm,btj->mj", dU, O)
    g["bg"]  += np.sum(dU, axis=(0,1))
    # BPTT
    dh_next = np.zeros((B,M))
    for t in range(T-1,-1,-1):
        dh = dH[:,t,:] + dh_next
        h_prev = H[:,t-1,:] if t>0 else np.zeros((B,M))
        g["a_raw"] += np.sum(dh*h_prev, axis=0) * (a*(1-a))
        g["b"]     += np.sum(dh*X[:,t,:], axis=0)
        dx = dh*P["b"]
        g["W_in"]  += np.einsum("bm,bj->mj", dx, O[:,t,:])
        dh_next = dh*a
    return g

def train(iters=400, lr=0.02):
    P = init(); O,A = gen_data()
    m={k:np.zeros_like(v) for k,v in P.items()}; v={k:np.zeros_like(v) for k,v in P.items()}
    b1,b2,eps=0.9,0.999,1e-8
    Bsz = O.shape[0]*O.shape[1]*3
    for it in range(1,iters+1):
        Apred,cache = forward(P,O)
        diff = Apred - A
        loss = np.mean(diff**2)
        dApred = 2*diff/Bsz
        g = backward(P,cache,dApred)
        for k in P:
            m[k]=b1*m[k]+(1-b1)*g[k]; v[k]=b2*v[k]+(1-b2)*g[k]**2
            mh=m[k]/(1-b1**it); vh=v[k]/(1-b2**it)
            P[k]-=lr*mh/(np.sqrt(vh)+eps)
        if it%80==0 or it==1:
            print(f"  iter {it:4d}  모방손실(MSE) {loss:.5f}")
    return P, loss

# ---------- 폐루프 평가: 신경망 정책이 드론을 나는가 ----------
def closed_loop(P, target, dist=(0,0,0), dstart=5.0, T=200):
    a = sig(P["a_raw"]); h=np.zeros(M); p=np.zeros(3); traj=[]
    target=np.array(target,float); dist=np.array(dist,float)
    for k in range(T):
        o = target - p
        x = P["W_in"]@o
        h = a*h + P["b"]*x
        y = P["C"]*h
        gt = silu(P["W_g"]@o + P["bg"])
        act = P["W_out"]@(y*gt) + P["D"]@o     # 신경망 정책의 행동
        d = dist if k*DT>=dstart else np.zeros(3)
        p = p + (act - d)*DT
        traj.append(p.copy())
    return np.array(traj), float(np.linalg.norm(target-p))

if __name__ == "__main__":
    print("== 신경망 Mamba 정책 -- PI 모방학습 (numpy) ==")
    P, loss = train()
    # 평가: 학습에 안 쓴 목표들로 폐루프
    errs=[]
    for tgt in [(2,-1,3),(-2.5,1.5,-1),(1,1,1),(3,0,-2)]:
        _,e = closed_loop(P, tgt, dist=(0.3,0,-0.2))
        errs.append(e); print(f"  목표 {tgt}: 폐루프 최종오차 {e:.3f}")
    m = float(np.mean(errs))
    print(f"  평균 최종오차 {m:.3f}")
    if "--저장" in sys.argv:
        np.savez(pathlib.Path(__file__).with_name("mamba_policy.npz"), **P)
        print(f"  가중치 저장: mamba_policy.npz (M={M}, 학습됨)")
    ok = loss < 0.05 and m < 0.3
    print(f"  판정: {'모방 성공·폐루프 수렴' if ok else '**아직 학습 부족**'}")
    sys.exit(0 if ok else 1)
