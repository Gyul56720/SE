#!/usr/bin/env python3
# selective-scan 상태갱신 + 출력의 고정소수 골든. RTL 과 비트로 맞춘다.
#
# 한 타임스텝, 채널 하나, 상태차원 N:
#   h[n] = Abar[n]*h_prev[n] + Bbar[n]*x        # N MAC
#   y    = sum_n C[n]*h[n]                        # N MAC + 리덕션
#
# 고정소수 (RTL 과 동일):
#   x,Bbar,C : Q1.15 부호 16b   (val = raw/2^15)
#   Abar     : Q0.16 무부호 16b (val = raw/2^16, [0,1))  -- RTL 에서 17b 부호확장(양수)
#   h,y      : Q4.12 부호 16b   (val = raw/2^12, [-8,8)) -- 포화
#
# 곱/시프트는 Verilog `>>>`(부호 산술시프트)와 같게: Python 은 부호 int 의 `>>` 가 floor 라
# 그대로 맞는다. Abar 는 무부호라 부호혼합 버그를 피하려 RTL 이 17b 부호확장을 쓴다.
import numpy as np, sys, pathlib

N_DEFAULT = 16
def s16(v):  # 16b 부호 포화
    return max(-32768, min(32767, v))
def tc(raw, bits=16):  # 무부호 raw -> 부호 int
    return raw - (1<<bits) if raw >= (1<<(bits-1)) else raw
def u16(raw): return raw & 0xFFFF

def step(x, Abar, Bbar, C, hprev):
    """전부 부호 int(Abar 는 양수). h,y 를 Q4.12 raw(부호)로 돌려준다."""
    N = len(Abar)
    h = []
    for n in range(N):
        p1 = (Abar[n] * hprev[n]) >> 16     # Q0.16 * Q4.12 = Q4.28 -> Q4.12
        p2 = (Bbar[n] * x)        >> 18     # Q1.15 * Q1.15 = Q2.30 -> Q4.12
        h.append(s16(p1 + p2))
    acc = 0
    for n in range(N):
        acc += C[n] * h[n]                  # Q1.15 * Q4.12 = Q5.27
    y = s16(acc >> 15)                      # -> Q4.12, 포화
    return h, y

def rnd_signed(rng, bits=16):
    return int(rng.integers(-(1<<(bits-1)), (1<<(bits-1))))

def gen_vectors(N, T, seed, outdir):
    """T 타임스텝의 스트림. 매 스텝 x,Abar,Bbar,C 를 주고 h,y 를 기대값으로."""
    rng = np.random.default_rng(seed)
    outdir = pathlib.Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    # 초기 상태 0
    hprev = [0]*N
    lines_in, lines_out = [], []
    # Abar 는 [0,1) 무부호. 감쇠게이트라 대개 0.5~0.99 근처를 주어 상태가 실제로 누적되게.
    Abar = [int(rng.integers(int(0.3*65536), 65535)) for _ in range(N)]  # 스텝간 고정(A 는 정적)
    maxabs_h = 0
    for t in range(T):
        x = rnd_signed(rng)
        Bbar = [rnd_signed(rng) for _ in range(N)]
        C    = [rnd_signed(rng) for _ in range(N)]
        h, y = step(x, Abar, Bbar, C, hprev)
        maxabs_h = max(maxabs_h, max(abs(v) for v in h))
        # 입력 한 줄: x, N*Abar, N*Bbar, N*C  (모두 4자리 hex 무부호 표기)
        row_in = [u16(x)] + [u16(a) for a in Abar] + [u16(b) for b in Bbar] + [u16(c) for c in C]
        lines_in.append(" ".join(f"{v:04x}" for v in row_in))
        row_out = [u16(v) for v in h] + [u16(y)]
        lines_out.append(" ".join(f"{v:04x}" for v in row_out))
        hprev = h
    (outdir/f"scan_in_N{N}.txt").write_text("\n".join(lines_in)+"\n")
    (outdir/f"scan_out_N{N}.txt").write_text("\n".join(lines_out)+"\n")
    # 퇴화 점검: 상태가 실제로 0 이 아니게 누적됐나
    assert maxabs_h > 100, f"상태가 안 누적됨(maxabs_h={maxabs_h}) -- 사소한 설명"
    print(f"# gen: N={N} T={T} -> scan_in_N{N}.txt, scan_out_N{N}.txt  (maxabs_h_raw={maxabs_h}, ~{maxabs_h/4096:.2f} in Q4.12)")

if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv)>1 else N_DEFAULT
    T = int(sys.argv[2]) if len(sys.argv)>2 else 64
    gen_vectors(N, T, seed=1234, outdir=sys.argv[3] if len(sys.argv)>3 else "ssm/dv")
