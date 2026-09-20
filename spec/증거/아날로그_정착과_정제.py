import numpy as np
rng = np.random.default_rng(1)

def settle(A,b,eps=1e-6):
    lam=np.linalg.eigvalsh(A); dt=0.1/lam.max()
    x=np.zeros(len(b)); xs=np.linalg.solve(A,b); n0=np.linalg.norm(xs); t=0.
    for _ in range(20_000_000):
        x=x+dt*(b-A@x); t+=dt
        if np.linalg.norm(x-xs)/n0<eps: return t,lam.min(),lam.max()
    return np.nan,lam.min(),lam.max()

print("== 사소한 설명 죽이기: 정착시간은 조건수에 걸리나, lam_min 에 걸리나 ==")
print("   (A) lam_min 을 1 로 고정하고 lam_max 만 키운다")
n=16; Q,_=np.linalg.qr(rng.standard_normal((n,n)))
for k in (1,10,100,1000):
    A=Q@np.diag(np.logspace(0,np.log10(k),n))@Q.T; b=rng.standard_normal(n)
    t,lo,hi=settle(A,b); print(f"     k={k:>5}  lam_min={lo:6.3f} lam_max={hi:9.2f}  t={t:8.2f}")
print("   (B) lam_max 를 1 로 고정한다  <- 하드웨어가 실제로 하는 정규화 (컨덕턴스 상한이 있다)")
for k in (1,10,100,1000):
    A=Q@np.diag(np.logspace(-np.log10(k),0,n))@Q.T; b=rng.standard_normal(n)
    t,lo,hi=settle(A,b); print(f"     k={k:>5}  lam_min={lo:9.5f} lam_max={hi:6.3f}  t={t:8.2f}   t/k={t/k:7.3f}")

print("\n== 3회 정제로 24비트를 내려면 아날로그가 몇 비트여야 하나 ==")
H=(rng.standard_normal((64,8))+1j*rng.standard_normal((64,8)))/np.sqrt(2)
G=H.conj().T@H+0.1*np.eye(8)
A=np.block([[G.real,-G.imag],[G.imag,G.real]]); N=len(A); b=rng.standard_normal(N)
xs=np.linalg.solve(A,b); Ainv=np.linalg.inv(A)
print(f"{'eta':>9}{'비트':>7}{'x0':>11}{'1회':>11}{'2회':>11}{'3회':>11}")
for eta in (5e-2,2e-2,1.6e-2,1e-2):
    acc=[]
    for trial in range(20):
        E=rng.standard_normal((N,N)); E/=np.linalg.norm(E,2)
        Ai=Ainv@(np.eye(N)+eta*E); x=Ai@b; row=[np.linalg.norm(x-xs)/np.linalg.norm(xs)]
        for _ in range(3):
            x=x+Ai@(b-A@x); row.append(np.linalg.norm(x-xs)/np.linalg.norm(xs))
        acc.append(row)
    m=np.median(np.array(acc),axis=0)
    print(f"{eta:>9.1e}{-np.log2(eta):>7.1f}"+"".join(f"{v:>11.2e}" for v in m))
print("\n24비트 = 상대오차 5.96e-08.  위 표의 '3회' 칸이 그보다 작아야 한다.")
