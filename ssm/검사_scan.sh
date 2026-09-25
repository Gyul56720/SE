#!/usr/bin/env bash
# scan_mac(병렬)·scan_seq(순차): 같은 골든으로 비트 대조 + 변이 검사 + 자원 측정.
set -euo pipefail
cd "$(dirname "$0")/.."
BIN=$(mktemp -d); trap 'rm -rf "$BIN"' EXIT

echo "== 0) 골든 재생성 (N=16, 64 스텝) =="
python3 ssm/model/scan_golden.py 16 64 ssm/dv >/dev/null

run_par () { iverilog -g2012 -o "$BIN/p" ssm/dv/tb_scan.v     ssm/rtl/scan_mac.v && "$BIN/p"; }
run_seq () { iverilog -g2012 -o "$BIN/s" ssm/dv/tb_scan_seq.v ssm/rtl/scan_seq.v && "$BIN/s"; }

echo "== 1) 병렬(scan_mac) 정상 =="
o=$(run_par); echo "$o"|grep -E 'steps=|RESULT'; echo "$o"|grep -q 'RESULT: PASS' || { echo 병렬실패; exit 1; }
echo "== 2) 순차(scan_seq) 정상 =="
o=$(run_seq); echo "$o"|grep -E 'steps=|RESULT'; echo "$o"|grep -q 'RESULT: PASS' || { echo 순차실패; exit 1; }

mutate () {  # $1 파일 $2 찾기 $3 바꾸기 $4 이름 $5 실행함수
  cp "$1" "$BIN/bak"
  python3 - "$1" "$2" "$3" <<'PY'
import sys,pathlib
p=pathlib.Path(sys.argv[1]); s=p.read_text()
if sys.argv[2] not in s: sys.exit(f"변이 대상 못 찾음: {sys.argv[2]!r}")
p.write_text(s.replace(sys.argv[2],sys.argv[3],1))
PY
  echo "== 변이: $4 =="
  set +e; o=$($5 2>&1); set -e
  echo "$o"|grep -E 'steps=|RESULT' || true
  cp "$BIN/bak" "$1"
  echo "$o"|grep -q 'RESULT: FAIL' || { echo "**이 변이를 못 잡음 -- 거짓 초록**"; exit 1; }
}

# 상태갱신 시프트량을 흔들면 스케일이 틀린다 -> FAIL
mutate ssm/rtl/scan_mac.v "(p1 >>> 16)" "(p1 >>> 15)" "병렬: Abar*h 시프트 16->15" run_par
mutate ssm/rtl/scan_mac.v "(p2 >>> 18)" "(p2 >>> 17)" "병렬: Bbar*x 시프트 18->17" run_par
mutate ssm/rtl/scan_seq.v "acc <= acc + mp;" "acc <= acc + (mp>>>1);" "순차: 출력 누산 왜곡" run_seq

echo; echo "== 3) 자원 (synth_xilinx xc7) -- Pareto 두 끝 =="
printf "  %-8s %5s %8s %8s %10s\n" "구조" "N" "DSP48" "LUT" "cyc/step"
for N in 4 16 64; do
  for mod in scan_mac scan_seq; do
    out=$(yosys -p "read_verilog ssm/rtl/$mod.v; chparam -set N $N $mod; hierarchy -top $mod; synth_xilinx -family xc7 -flatten; stat" 2>&1)
    dsp=$(echo "$out"|awk '/DSP4/{s+=$NF}END{print s+0}')
    lut=$(echo "$out"|awk '/LUT[0-9]/{s+=$NF}END{print s+0}')
    if [ "$mod" = scan_mac ]; then cyc=1; else cyc=$((3*N+2)); fi
    printf "  %-8s %5s %8s %8s %10s\n" "$mod" "$N" "$dsp" "$lut" "$cyc"
  done
done
echo; echo "모든 변이가 물었다. 병렬=DSP 6N/1cyc, 순차=DSP 2상수/~3N cyc(단 LUT는 mux로 커짐)."
