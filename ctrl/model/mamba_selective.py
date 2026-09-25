#!/usr/bin/env python3
# Selective 신경망 Mamba 제어 정책 -- **입력의존 파라미터(진짜 Mamba S6).**
#
# mamba_policy.py 는 a,b 가 고정이었다(선형 SSM). Mamba 의 핵심은 **selective**:
# Δ,B,C 를 입력의 함수로 만들어 내용에 따라 상태를 다르게 쌓는다. 그러면 이산화
#     Abar_t = exp(Δ_t·A),   Bbar_t = Δ_t·B_t
# 의 **exp 가 다시 등장**한다 -- 그래서 우리 exp_unit(LUT) 하드웨어에 역할이 생긴다.
# 하드웨어 전체가 꿰인다: 입력투영(DSP) -> exp 이산화(exp_unit,LUT) -> 스캔(scan_mac,DSP).
#
# 구조(대각 SSM, 채널당 상태 1, 전부 입력의존):
#   x_t=W_in·o,  Δ_t=softplus(W_Δ·o+bΔ),  B_t=W_B·o,  C_t=W_C·o
#   A = -softplus(A_raw) < 0  (학습, 고정)      -> Abar_t=exp(Δ_t·A)∈(0,1)
#   h_t = Abar_t⊙h_{t-1} + (Δ_t⊙B_t)⊙x_t
#   y_t = C_t⊙h_t ,  g_t=SiLU(W_g·o+bg) ,  a_pred=W_out·(y⊙g)+D·o
# 순수 numpy + 수동 BPTT(입력의존·exp 통과).
import sys, pathlib
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
import ctrl.model.mamba_policy as base   # 데이터 생성·silu 재사용

RNG = np.random.default_rng(11)
M = 8
def softplus(u): return np.log1p(np.exp(-np.abs(u))) + np.maximum(u,0)
def dsoftplus(u): return 1.0/(1.0+np.exp(-u))   # = sigmoid
silu, dsilu = base.silu, base.dsilu

def init():
    return {"W_in":RNG.normal(0,0.5,(M,3)), "W_D":RNG.normal(0,0.3,(M,3)), "bD":np.zeros(M),
            "W_B":RNG.normal(0,0.4,(M,3)), "W_C":RNG.normal(0,0.5,(M,3)),
            # A 를 0 근처~적당히로 다양하게: 일부 채널은 적분기(Ā≈1), 일부는 빠른 감쇠.
            # A=-softplus(A_raw); A_raw≈-2.5 -> A≈-0.08 -> Ā≈0.9(느린 감쇠=적분기)
            "A_raw":RNG.uniform(-3.5,-0.5,M),
            "W_g":RNG.normal(0,0.5,(M,3)), "bg":np.zeros(M),
            "W_out":RNG.normal(0,0.3,(3,M)), "D":np.eye(3)*3.0}

def forward(P, O):
    B,T,_ = O.shape
    A = -softplus(P["A_raw"])                       # (M,)  <0
    X  = O @ P["W_in"].T
    pD = O @ P["W_D"].T + P["bD"]; Dt = softplus(pD)  # (B,T,M) >0
    Bt = O @ P["W_B"].T
    Ct = O @ P["W_C"].T
    U  = O @ P["W_g"].T + P["bg"]; G = silu(U)
    Abar = np.exp(Dt * A)                            # (B,T,M) ∈(0,1)
    Bbar = Dt * Bt
    H = np.zeros((B,T,M)); h=np.zeros((B,M))
    for t in range(T):
        h = Abar[:,t,:]*h + Bbar[:,t,:]*X[:,t,:]
        H[:,t,:] = h
    Y = Ct*H; Z = Y*G
    Apred = Z @ P["W_out"].T + O @ P["D"].T
    return Apred, dict(O=O,A=A,X=X,pD=pD,Dt=Dt,Bt=Bt,Ct=Ct,U=U,G=G,Abar=Abar,Bbar=Bbar,H=H,Y=Y,Z=Z)

def backward(P, c, dApred):
    O,A,X,pD,Dt,Bt,Ct,U,G,Abar,Bbar,H,Y,Z = (c[k] for k in
        ("O","A","X","pD","Dt","Bt","Ct","U","G","Abar","Bbar","H","Y","Z"))
    B,T,_ = O.shape
    g = {k:np.zeros_like(v) for k,v in P.items()}
    g["W_out"] += np.einsum("btk,btm->km", dApred, Z)
    g["D"]     += np.einsum("btk,btj->kj", dApred, O)
    dZ = dApred @ P["W_out"]
    dY = dZ*G; dG = dZ*Y
    dU = dG*dsilu(U); g["W_g"] += np.einsum("btm,btj->mj", dU, O); g["bg"] += dU.sum((0,1))
    dCt = dY*H                                       # y=Ct*h
    dH  = dY*Ct
    # BPTT
    dAbar = np.zeros((B,T,M)); dBbar=np.zeros((B,T,M)); dX=np.zeros((B,T,M))
    dh_next = np.zeros((B,M))
    for t in range(T-1,-1,-1):
        dh = dH[:,t,:] + dh_next
        h_prev = H[:,t-1,:] if t>0 else np.zeros((B,M))
        dAbar[:,t,:] = dh*h_prev
        dBbar[:,t,:] = dh*X[:,t,:]
        dX[:,t,:]    = dh*Bbar[:,t,:]
        dh_next = dh*Abar[:,t,:]
    # Abar=exp(Dt*A): dDt += dAbar*Abar*A ; dA += sum dAbar*Abar*Dt
    dDt  = dAbar*Abar*A
    dA   = np.sum(dAbar*Abar*Dt, axis=(0,1))
    # Bbar=Dt*Bt
    dDt += dBbar*Bt
    dBt  = dBbar*Dt
    # Dt=softplus(pD)
    dpD  = dDt*dsoftplus(pD)
    g["W_D"] += np.einsum("btm,btj->mj", dpD, O); g["bD"] += dpD.sum((0,1))
    g["W_B"] += np.einsum("btm,btj->mj", dBt, O)
    g["W_C"] += np.einsum("btm,btj->mj", dCt, O)
    g["W_in"]+= np.einsum("btm,btj->mj", dX,  O)
    # A=-softplus(A_raw): dA_raw = dA * -dsoftplus(A_raw)
    g["A_raw"] += dA * (-dsoftplus(P["A_raw"]))
    return g

def train(iters=500, lr=0.02, seed=11):
    global RNG; RNG=np.random.default_rng(seed)
    P=init(); O,A = base.gen_data()
    m={k:np.zeros_like(v) for k,v in P.items()}; v={k:np.zeros_like(v) for k,v in P.items()}
    b1,b2,eps=0.9,0.999,1e-8; sz=O.shape[0]*O.shape[1]*3
    loss=1.0
    for it in range(1,iters+1):
        Ap,c = forward(P,O); diff=Ap-A; loss=float(np.mean(diff**2))
        g = backward(P,c,2*diff/sz)
        for k in P:
            m[k]=b1*m[k]+(1-b1)*g[k]; v[k]=b2*v[k]+(1-b2)*g[k]**2
            P[k]-=lr*(m[k]/(1-b1**it))/(np.sqrt(v[k]/(1-b2**it))+eps)
        if it%100==0 or it==1: print(f"  iter {it:4d}  모방손실(MSE) {loss:.5f}")
    return P, loss

def closed_loop(P, target, dist=(0,0,0), dstart=5.0, T=200):
    A=-softplus(P["A_raw"]); h=np.zeros(M); p=np.zeros(3); traj=[]
    target=np.array(target,float); dist=np.array(dist,float)
    for k in range(T):
        o=target-p
        x=P["W_in"]@o; Dt=softplus(P["W_D"]@o+P["bD"]); Bt=P["W_B"]@o; Ct=P["W_C"]@o
        Abar=np.exp(Dt*A); Bbar=Dt*Bt
        h=Abar*h + Bbar*x
        y=Ct*h; gt=silu(P["W_g"]@o+P["bg"])
        act=P["W_out"]@(y*gt)+P["D"]@o
        d=dist if k*base.DT>=dstart else np.zeros(3)
        p=p+(act-d)*base.DT; traj.append(p.copy())
    return np.array(traj), float(np.linalg.norm(target-p))

if __name__=="__main__":
    print("== Selective 신경망 Mamba 정책 -- PI 모방학습 (입력의존 Δ,B,C + exp 이산화) ==")
    P,loss=train()
    errs=[]
    for tgt in [(2,-1,3),(-2.5,1.5,-1),(1,1,1),(3,0,-2)]:
        _,e=closed_loop(P,tgt,dist=(0.3,0,-0.2)); errs.append(e); print(f"  목표 {tgt}: 폐루프 최종오차 {e:.3f}")
    mm=float(np.mean(errs)); print(f"  평균 최종오차 {mm:.3f}")
    if "--저장" in sys.argv:
        np.savez(pathlib.Path(__file__).with_name("mamba_selective.npz"), **P)
        print("  가중치 저장: mamba_selective.npz")
    ok=loss<0.05 and mm<0.3
    print(f"  판정: {'selective 모방 성공·폐루프 수렴' if ok else '**아직 학습 부족**'}")
    sys.exit(0 if ok else 1)
