#!/usr/bin/env python3
# 이산화 감쇠게이트 exp 근사의 골든 모델.
#
# 재는 것: Abar = exp(z), z = delta*A <= 0 (Mamba 는 A<0 안정, delta>0).
# 그래서 Abar in (0,1] -- 감쇠게이트. 입력은 크기 m = -z in [0, M] 로 다룬다(무부호).
#
# 이 파일이 하는 일:
#  1) 직접-LUT 근사의 K(엔트리수) 별 최대/평균 절대오차를 낸다 (정확도 축).
#  2) RTL 이 읽을 LUT 내용(.memh)과 대조 벡터(.txt)를 K 하나에 대해 낸다.
#
# 규율: 사소한 설명 배제 -- exp 가 전부 1.0 로 퇴화하지 않는지 z 범위를 실제로 흔든다.
#       독립 대조 -- RTL 은 이 numpy exp 를 비트로 대조한다(dv/).
import numpy as np, sys, pathlib

M_MAX = 8.0          # m = -z 의 최대. z in [-8,0]. exp(-8)=3.35e-4 이면 감쇠 충분.
MBITS = 16           # m 포맷 Q3.13 무부호: raw/8192, 범위 [0,8)
MFRAC = 13
ABITS = 16           # Abar 포맷 Q0.16 무부호: raw/65536, 범위 [0,1). 1.0 은 0xFFFF 로 포화.
AFRAC = 16

def m_to_raw(m):  return int(round(m * (1 << MFRAC))) & ((1 << MBITS) - 1)
def raw_to_m(r):  return r / (1 << MFRAC)
def abar_to_raw(a):
    r = int(round(a * (1 << AFRAC)))
    return min(r, (1 << ABITS) - 1)   # 1.0 포화
def raw_to_abar(r): return r / (1 << AFRAC)

def lut(K):
    """K 엔트리 직접 LUT. 인덱스 = m 의 상위 log2(K) 비트. 값 = 구간 중심의 exp(-m_center)."""
    assert (K & (K-1)) == 0, "K 는 2의 거듭제곱"
    idxbits = K.bit_length() - 1
    step = M_MAX / K                       # 구간 폭
    tab = []
    for i in range(K):
        m_center = (i + 0.5) * step        # 구간 중심
        tab.append(abar_to_raw(np.exp(-m_center)))
    return tab, idxbits, step

def approx(m, K):
    tab, idxbits, step = lut(K)
    # RTL 과 똑같이: m_raw 의 상위 idxbits 비트로 인덱스
    m_raw = m_to_raw(m)
    idx = m_raw >> (MBITS - idxbits)
    idx = min(idx, K-1)
    return raw_to_abar(tab[idx])

def sweep():
    ms = np.linspace(0, M_MAX*0.999, 4000)
    ref = np.exp(-ms)
    print(f"# 직접-LUT exp 근사 정확도 (m in [0,{M_MAX}], Q3.13->Q0.16)")
    print(f"{'K':>5} {'idxbits':>7} {'최대절대오차':>12} {'평균절대오차':>12}")
    rows=[]
    for K in [8,16,32,64,128]:
        ap = np.array([approx(m,K) for m in ms])
        emax = float(np.max(np.abs(ap-ref))); emean=float(np.mean(np.abs(ap-ref)))
        rows.append((K,emax,emean))
        print(f"{K:>5} {K.bit_length()-1:>7} {emax:>12.3e} {emean:>12.3e}")
    # 퇴화 점검: 근사가 상수가 아니어야 한다
    ap64 = np.array([approx(m,64) for m in ms])
    assert ap64.max()-ap64.min() > 0.5, "근사가 퇴화(거의 상수) -- 사소한 설명"
    # 구간중심 LUT 는 m=0 에서 exp(-step/2) 로 편향된다(K=64 면 0.94). 1.0 은 아니다 -- 정직.
    assert approx(0.0,64) > 0.9, "m=0 에서 게이트가 1 근처가 아니다(장기기억 못 함)"
    assert approx(M_MAX*0.99,64) < 0.05, "큰 m 에서 안 죽는다"
    print("# 퇴화 점검 통과: 근사가 1근처(0.94)->0 으로 실제로 변한다 (m=0 편향은 구간중심 LUT 특성)")
    return rows

def emit(K, outdir):
    outdir = pathlib.Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    tab, idxbits, step = lut(K)
    (outdir/f"exp_lut_{K}.memh").write_text("\n".join(f"{v:04x}" for v in tab)+"\n")
    # 대조 벡터: 여러 m 에 대해 (m_raw, 기대 Abar_raw). RTL 인덱싱과 동일 규칙.
    lines=[]
    for m in np.linspace(0, M_MAX*0.999, 200):
        m_raw = m_to_raw(m)
        idx = min(m_raw >> (MBITS-idxbits), K-1)
        lines.append(f"{m_raw:04x} {tab[idx]:04x}")
    (outdir/f"exp_vec_{K}.txt").write_text("\n".join(lines)+"\n")
    print(f"# emit: exp_lut_{K}.memh ({K} 엔트리), exp_vec_{K}.txt (200 벡터), idxbits={idxbits}")

if __name__ == "__main__":
    sweep()
    if len(sys.argv)>1 and sys.argv[1]=="emit":
        K = int(sys.argv[2]) if len(sys.argv)>2 else 64
        emit(K, sys.argv[3] if len(sys.argv)>3 else "ssm/dv")
