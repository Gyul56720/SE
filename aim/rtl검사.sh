#!/usr/bin/env bash
# aim/rtl 을 **AIMer 레퍼런스가 낸 벡터**로 대조하고, 변이로 그 검사가 무는지 본다.
# 셸 변수 이름은 아스키만 쓴다 (CLAUDE.md).
set -euo pipefail
cd "$(dirname "$0")/.."
RTL="aim/rtl/gf128_mul.v aim/rtl/gf128_sqr.v aim/rtl/mer7.v"
BIN=$(mktemp -d); trap 'rm -rf "$BIN"' EXIT

build_run () { iverilog -g2012 -I aim/rtl -o "$BIN/tb" aim/dv/tb_gf128.v $RTL && "$BIN/tb"; }

echo "== 정상 =="
out=$(build_run); echo "$out" | grep -E 'vectors=|RESULT'
echo "$out" | grep -q 'RESULT: PASS' || { echo "정상 실행이 통과가 아니다"; exit 1; }

# 변이 -- 검사가 실제로 무는지 본다. **주석이 아니라 코드 줄**을 노린다
# (실측: 처음에 sed 가 주석의 '<< 7)' 을 맞춰서 아무것도 안 바뀐 채 통과했다).
mutate () {  # $1=파일 $2=찾을것 $3=바꿀것 $4=이름
  cp "$1" "$BIN/bak"
  python3 - "$1" "$2" "$3" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
if sys.argv[2] not in s: sys.exit(f"변이 대상을 못 찾았다: {sys.argv[2]!r}")
p.write_text(s.replace(sys.argv[2], sys.argv[3], 1))
PY
  echo "== 변이: $4 =="
  set +e; out=$(build_run 2>&1); set -e
  echo "$out" | grep -E 'vectors=|RESULT' || true
  cp "$BIN/bak" "$1"
  echo "$out" | grep -q 'RESULT: FAIL' || { echo "**이 변이를 검사가 못 잡는다 -- 거짓 초록**"; exit 1; }
}

mutate aim/rtl/gf128.vh "{7'd0, hi} << 7"        "{7'd0, hi} << 6"        "축약 다항식 x^7 -> x^6"
mutate aim/rtl/gf128.vh "& {255{b[i]}}) << i)"   "& {255{b[i]}}) << (i+1))" "clmul 자리이동 i -> i+1"
mutate aim/rtl/gf128.vh "s[2*i] = a[i];"         "s[2*i+1] = a[i];"        "제곱 비트벌리기 한 칸 밀기"

echo "== 변이: 벡터 파일 비우기 =="
cp aim/dv/vectors.txt "$BIN/vec"; : > aim/dv/vectors.txt
set +e; out=$(build_run 2>&1); set -e
echo "$out" | grep -E 'vectors=|RESULT' || true
cp "$BIN/vec" aim/dv/vectors.txt
echo "$out" | grep -q 'RESULT: FAIL' || { echo "**벡터가 0개인데 초록이다 -- 검사하지 않은 초록불**"; exit 1; }

echo; echo "== 면적 (yosys) =="
for top in gf128_sqr gf128_mul mer7; do
  printf "  %-11s " "$top"
  yosys -p "read_verilog -sv -I aim/rtl $RTL; hierarchy -top $top; proc; opt; flatten; techmap; opt; stat" 2>&1 \
   | awk '/Number of cells/{c=$NF} /\$_AND_/{a=$NF} /\$_XOR_/{x=$NF} /\$_MUX_/{m=$NF} END{printf "셀 %-7s AND %-7s XOR %-7s MUX %s\n", c, (a?a:0), (x?x:0), (m?m:0)}'
done
echo; echo "모든 변이가 물었다. 검사가 실제로 검사한다."
