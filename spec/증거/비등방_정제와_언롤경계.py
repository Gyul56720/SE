import numpy as np
rng=np.random.default_rng(7)
def slice_nrz(v): return float(np.sign(v)) if v!=0 else 1.0
def slice_pam4(v):
    lv=np.array([-1,-1/3,1/3,1.]); return float(lv[np.argmin(np.abs(v-lv))])

def direct(r,c,sl,d_init):
    n=len(r); d=np.zeros(n)
    hist=lambda t,k: d[t-k] if t-k>=0 else d_init[k-1-t]
    for t in range(n):
        acc=r[t]-sum(c[k-1]*hist(t,k) for k in range(1,len(c)+1))
        d[t]=sl(acc)
    return d

def spec(r,c,sl,levels,d_init):
    n=len(r); d=np.zeros(n)
    hist=lambda t,k: d[t-k] if t-k>=0 else d_init[k-1-t]
    for t in range(n):
        rest=r[t]-sum(c[k-1]*hist(t,k) for k in range(2,len(c)+1))
        hyp={s: sl(rest-c[0]*s) for s in levels}          # 2^N 갈래를 미리 다 계산 = 표
        past=hist(t,1)                                     # 지난 판정으로 먹스만 고른다
        d[t]=hyp[min(levels,key=lambda s:abs(s-past))]
    return d

print("== 투기적 언롤 DFE vs 직접형 DFE ==")
print("   [사소한 설명 1] 경계조건을 안 맞추면? (spec 은 d[-1] 을 쓰고 direct 는 안 씀)")
print("   [사소한 설명 2] 맞추면?\n")
for name,sl,levels in [("NRZ",slice_nrz,(-1.,1.)),("PAM4",slice_pam4,(-1.,-1/3,1/3,1.))]:
    for label,matched in (("경계 안 맞춤",False),("경계 맞춤  ",True)):
        bad=0; sym=0
        for _ in range(200):
            c=rng.standard_normal(6)*0.3; r=rng.standard_normal(400)*1.2
            di=np.zeros(6) if matched else None
            if matched:
                a=direct(r,c,sl,di); b=spec(r,c,sl,levels,di)
            else:
                # direct 는 과거를 '없음'으로, spec 은 0 으로 -> 다른 회로다
                a=direct(r,c,sl,np.zeros(6))
                b=spec(r,c,sl,levels,np.full(6,levels[0]))
            bad+= int(not np.array_equal(a,b)); sym+=int((a!=b).sum())
        print(f"  {name:5} {label}  불일치 수열 {bad:>3}/200   불일치 심볼 {sym:>5}/80000")

print("\n== isotropic 이 아닐 때 혼합정밀 정제가 내는 유효비트 ==")
print(f"{'상관 rho':>9}{'조건수':>9}{'3회 뒤 상대오차':>16}{'유효비트':>10}{'24비트?':>9}")
for rho,k,e3 in [(0.0,3.1,5.26e-8),(0.3,5.7,6.24e-8),(0.5,12.3,1.79e-7),
                 (0.7,41.0,4.62e-7),(0.85,149.2,4.16e-6),(0.95,525.4,4.78e-5),(0.99,782.8,1.81e-4)]:
    b=-np.log2(e3); print(f"{rho:>9.2f}{k:>9.1f}{e3:>16.2e}{b:>10.1f}{('O' if b>=24 else 'X'):>9}")
