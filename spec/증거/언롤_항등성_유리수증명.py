from fractions import Fraction as F
import numpy as np
rng=np.random.default_rng(7)

# ---------- 가설 A: 남은 불일치는 '부동소수점 합산 순서' 때문이다 ----------
# 검사 1: 불일치가 난 자리의 슬라이서 입력 크기를 본다 (문턱에 붙어 있나?)
def slice_nrz(v): return 1.0 if v>=0 else -1.0
def run_float(c,r,d_init):
    n=len(r); a=np.zeros(n); b=np.zeros(n); gaps=[]
    ha=lambda t,k: a[t-k] if t-k>=0 else d_init[k-1-t]
    hb=lambda t,k: b[t-k] if t-k>=0 else d_init[k-1-t]
    for t in range(n):
        acc=r[t]
        for k in range(1,7): acc-=c[k-1]*ha(t,k)          # 직접형 순서
        a[t]=slice_nrz(acc)
        rest=r[t]
        for k in range(2,7): rest-=c[k-1]*hb(t,k)         # 투기형 순서: 뒤탭 먼저
        past=hb(t,1)
        acc2=rest-c[0]*past
        b[t]=slice_nrz(acc2)
        if a[t]!=b[t]: gaps.append((abs(acc),abs(acc-acc2)))
    return a,b,gaps

allg=[]
for _ in range(200):
    c=rng.standard_normal(6)*0.3; r=rng.standard_normal(400)*1.2
    a,b,g=run_float(c,r,np.zeros(6)); allg+=g
if allg:
    ac=np.array([x[0] for x in allg]); df=np.array([x[1] for x in allg])
    print(f"불일치 심볼 {len(allg)}개")
    print(f"  그 자리 |슬라이서 입력| 최대 = {ac.max():.3e}   중앙값 = {np.median(ac):.3e}")
    print(f"  두 순서의 차이   최대 = {df.max():.3e}")
    print(f"  -> 전부 배정밀도 엡실론({np.finfo(float).eps:.1e}) 언저리인가? {ac.max() < 1e-12}")

# ---------- 검사 2: 유리수(무한정밀)로 다시 돌린다 ----------
def slice_F(v): return F(1) if v>=0 else F(-1)
def both_exact(c,r):
    n=len(r); a=[F(0)]*n; b=[F(0)]*n
    ha=lambda t,k: a[t-k] if t-k>=0 else F(0)
    hb=lambda t,k: b[t-k] if t-k>=0 else F(0)
    for t in range(n):
        acc=r[t]
        for k in range(1,7): acc-=c[k-1]*ha(t,k)
        a[t]=slice_F(acc)
        rest=r[t]
        for k in range(2,7): rest-=c[k-1]*hb(t,k)
        b[t]=slice_F(rest-c[0]*hb(t,1))
    return a,b
bad=0
for _ in range(60):
    c=[F(x).limit_denominator(10**6) for x in rng.standard_normal(6)*0.3]
    r=[F(x).limit_denominator(10**6) for x in rng.standard_normal(120)*1.2]
    a,b=both_exact(c,r); bad+= int(a!=b)
print(f"\n무한정밀(유리수) 60회 x 120심볼:  불일치 수열 {bad}/60")
