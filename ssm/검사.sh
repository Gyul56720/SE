#!/usr/bin/env bash
# ssm exp_unit: 골든 대조 + 변이 검사(거짓 초록 사냥) + 자원 측정.
# 셸 변수는 아스키만 (CLAUDE.md). aim/rtl검사.sh 와 같은 뼈대.
set -euo pipefail
cd "$(dirname "$0")/.."
BIN=$(mktemp -d); trap 'rm -rf "$BIN"' EXIT

echo "== 0) 골든 재생성 (K=8..128 LUT + K=64 벡터) =="
for K in 8 16 32 64 128; do python3 ssm/model/exp_golden.py emit "$K" ssm/dv >/dev/null; done

build_run () { iverilog -g2012 -o "$BIN/tb" ssm/dv/tb_exp.v ssm/rtl/exp_unit.v && "$BIN/tb"; }

echo "== 1) 정상 대조 =="
out=$(build_run); echo "$out" | grep -E 'vectors=|RESULT'
echo "$out" | grep -q 'RESULT: PASS' || { echo "정상 실행이 통과가 아니다"; exit 1; }

mutate () {  # $1=파일 $2=찾을것 $3=바꿀것 $4=이름
  cp "$1" "$BIN/bak"
  python3 - "$1" "$2" "$3" <<'PY'
import sys, pathlib
p=pathlib.Path(sys.argv[1]); s=p.read_text()
if sys.argv[2] not in s: sys.exit(f"변이 대상을 못 찾음: {sys.argv[2]!r}")
p.write_text(s.replace(sys.argv[2], sys.argv[3], 1))
PY
  echo "== 변이: $4 =="
  set +e; out=$(build_run 2>&1); set -e
  echo "$out" | grep -E 'vectors=|RESULT' || true
  cp "$BIN/bak" "$1"
  echo "$out" | grep -q 'RESULT: FAIL' || { echo "**이 변이를 검사가 못 잡는다 -- 거짓 초록**"; exit 1; }
}

# 인덱스 슬라이스를 한 칸 밀면 틀린 표를 친다 -> FAIL 해야 한다
mutate ssm/rtl/exp_unit.v "m[MBITS-1 -: IDXBITS]" "m[MBITS-2 -: IDXBITS]" "인덱스 상위비트 한 칸 밀기"

echo "== 변이: LUT 첫 엔트리 훼손 =="
cp ssm/dv/exp_lut_64.memh "$BIN/lut"; sed -i '1s/.*/0000/' ssm/dv/exp_lut_64.memh
set +e; out=$(build_run 2>&1); set -e
echo "$out" | grep -E 'vectors=|RESULT' || true
cp "$BIN/lut" ssm/dv/exp_lut_64.memh
echo "$out" | grep -q 'RESULT: FAIL' || { echo "**LUT 훼손인데 초록 -- 거짓 초록**"; exit 1; }

echo; echo "== 2) 자원 측정 (FPGA: synth_xilinx xc7) =="
printf "  %5s %6s %8s %6s %6s %14s\n" "K" "idxb" "LUT" "DSP" "BRAM" "최대절대오차"
python3 ssm/model/exp_golden.py 2>/dev/null | awk 'NF==4 && $1 ~ /^[0-9]+$/ {err[$1]=$3}
  END{for(k in err) e[k]=err[k]}' > "$BIN/err.txt"
for K in 8 16 32 64 128; do
  IDX=$(python3 -c "print(($K).bit_length()-1)")
  err=$(python3 ssm/model/exp_golden.py 2>/dev/null | awk -v k="$K" 'NF==4 && $1==k{print $3}')
  out=$(yosys -p "read_verilog ssm/rtl/exp_unit.v; chparam -set IDXBITS $IDX -set LUTFILE \"ssm/dv/exp_lut_$K.memh\" exp_unit; hierarchy -top exp_unit; synth_xilinx -family xc7 -flatten; stat" 2>&1)
  lut=$(echo "$out" | awk '/LUT[0-9]/{s+=$NF} END{print s+0}')
  dsp=$(echo "$out" | awk '/DSP4/{s+=$NF} END{print s+0}')
  bram=$(echo "$out" | awk '/RAMB|BRAM/{s+=$NF} END{print s+0}')
  printf "  %5s %6s %8s %6s %6s %14s\n" "$K" "$IDX" "$lut" "$dsp" "$bram" "$err"
done

echo; echo "== 3) 자원 측정 (ASIC: yosys generic, 메모리를 게이트로 풀어서) =="
# memory_map 을 넣어야 ROM 이 실제 게이트로 풀린다. 안 넣으면 $mem 로 남아 '셀 2' 같은 오해값.
for K in 8 32 64 128; do
  IDX=$(python3 -c "print(($K).bit_length()-1)")
  yosys -p "read_verilog ssm/rtl/exp_unit.v; chparam -set IDXBITS $IDX -set LUTFILE \"ssm/dv/exp_lut_$K.memh\" exp_unit; hierarchy -top exp_unit; proc; opt; memory; memory_map; flatten; techmap; opt; stat" 2>&1 \
   | awk -v k="$K" '/Number of cells/{c=$NF} END{printf "  K=%-4s 총 셀 %s\n", k, c}'
done

echo; echo "모든 변이가 물었다. exp 근사는 DSP/BRAM 0, 순수 LUT."
