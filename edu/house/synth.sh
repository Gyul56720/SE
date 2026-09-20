#!/usr/bin/env bash
# synth.sh -- 무료 도구만으로 RTL 을 재는 한 줄.
#
# 변수 이름이 전부 아스키인 이유 -- 이 저장소가 이미 한 번 물린 자리다
# ------------------------------------------------------------------
# bash 는 식별자로 `[A-Za-z_][A-Za-z0-9_]*` 만 받는다.  `파일=x` 는 대입이
# **아니라 명령어**로 파싱되고 "No such file or directory" 가 난다.
# 이 저장소의 파이썬은 한글 이름을 쓰지만 **셸만 다르다**.
# 실측 2026-09-19: 이 파일의 첫 판이 정확히 그렇게 한 줄도 안 돌았다
# (`파일=...: No such file or directory`, 그리고 `${톱}` 은 bad substitution).
# CLAUDE.md 에 그 규칙이 이미 적혀 있었는데도 그랬다 -- **규칙을 적는 것과
# 지키는 것은 다르고, 그래서 검사가 필요하다** (tests/test_synth_sh.py).
#
#     bash edu/house/synth.sh <SRC.v> <TOP모듈> [--pnr]
#
# 네 도구를 순서대로 돌린다.  전부 무료이고 이 컨테이너에 깔려 있다.
#
#   1. verilator --lint-only -Wall   문법·폭·미사용 신호.  **가장 싸고 가장 많이 잡는다**
#   2. yosys                         합성.  기술독립 셀 수 (`stat`)
#   3. yosys -p synth_ice40          iCE40 로 매핑.  진짜 LUT·FF·DSP 수
#   4. nextpnr-ice40                 배치·배선.  **진짜 Fmax** (--pnr 일 때만, 느리다)
#
# 왜 이 순서인가
# --------------
# 뒤로 갈수록 느리고 뒤로 갈수록 진짜다.  lint 는 초, 합성은 초~분, P&R 은 분~시간.
# **싼 것부터 돌려서 싼 데서 죽는 것을 비싼 데까지 안 끌고 간다.**
#
# 왜 셀 수를 믿고 '예상 면적' 을 안 믿나
# ---------------------------------------
# HLS 도구가 스스로 내는 "Total estimated area" 는 그 도구의 내부 모델이다.
# 실측 2026-09-19: Bambu 가 FIR naive 를 299, narrow 를 677 로 냈는데
# **yosys 로 실제로 매핑하면 순서가 달라진다.**  도구의 자기 평가를 결과로
# 옮겨 적으면 안 된다 -- 재려던 것(실제 하드웨어 비용)이 아니다.
set -u

SRC=${1:?사용법: synth.sh <SRC.v> <TOP모듈> [--pnr]}
TOP=${2:?TOP 모듈 이름이 필요하다}
PNR=${3:-}
# 로그를 파일로 받는다 -- 파이프로 받으면 SIGPIPE 로 종료코드를 잃는다.
OUT=${SYNTH_OUT:-/tmp/synth_$$}
mkdir -p "$OUT"
LOG="$OUT/$TOP"
JSON="$OUT/$TOP.ice40.json"

say() { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

say "== 1. verilator lint =="
if have verilator; then
  # -Wall 은 업계가 실제로 켜는 수준이다.  UNUSEDSIGNAL 까지 잡는다.
  # `--timing` 없이 lint 만 -- 시뮬레이션을 안 하므로 빠르다.
  #
  # `| head` 를 쓰지 않는다.  실측: head 가 파이프를 닫으면 verilator 가
  # SIGPIPE 로 죽고 **rc=141 이 나온다** -- lint 가 통과했는지 실패했는지
  # 알 수 없게 된다.  파일로 받고 나서 자른다.
  verilator --lint-only -Wall --top-module "$TOP" "$SRC" > "$LOG.lint" 2>&1
  LRC=$?
  grep -cE "^%(Error|Warning)" "$LOG.lint" | sed 's/^/   경고+오류 /'
  grep -oE "^%(Error|Warning)-[A-Z]+" "$LOG.lint" | sort | uniq -c | sort -rn | head -12
  say "   lint rc=$LRC"
else
  say "   verilator 없음 -- 건너뜀"
fi

say ""
say "== 2. yosys 기술독립 합성 =="
if have yosys; then
  # `-q` 를 쓰지 않는다.  실측: `-q` 가 `stat` 출력까지 삼켜서
  # 셀 수를 못 읽었다.  조용하게 만들려다 재려던 것을 잃는다.
  yosys -p "read_verilog -sv $SRC; hierarchy -check -top $TOP; proc; opt; fsm; opt; memory; opt; techmap; opt; stat" \
        > "$LOG.generic" 2>&1
  # stat 은 모듈마다 한 덩이를 낸다.  **마지막 덩이**가 톱이다.
  # (앞 덩이는 하위 모듈이라 그것을 읽으면 엉뚱한 수를 보고한다.)
  awk '/^[0-9.]* Printing statistics/{found=1} /=== '"$TOP"' ===/{grab=1; buf=""} grab{buf=buf $0 "\n"} END{printf "%s", buf}' "$LOG.generic" \
    | grep -E "Number of (cells|wires)|^ +\\$?[a-z_]+ +[0-9]+" | head -25
  say "   yosys rc=$(grep -c '^ERROR' "$LOG.generic")개 오류"
else
  say "   yosys 없음 -- 건너뜀"
fi

say ""
say "== 3. yosys iCE40 매핑 (진짜 LUT 수) =="
if have yosys; then
  yosys -p "read_verilog -sv $SRC; synth_ice40 -top $TOP -json ${JSON}; stat" > "$LOG.ice40" 2>&1
  # "Generating RTLIL representation for module \SB_LUT4" 같은 줄이
  # 셀 이름을 품고 있어서 그냥 grep 하면 그것까지 센다 -- 실측으로 그랬다.
  # `stat` 덩이 안에서만 본다.
  awk '/=== '"$TOP"' ===/{grab=1} grab' "$LOG.ice40" \
    | grep -E "Number of cells|SB_LUT4|SB_CARRY|SB_DFF|SB_MAC16|SB_RAM" | head -15
else
  say "   yosys 없음 -- 건너뜀"
fi

if [ "$PNR" = "--pnr" ]; then
  say ""
  say "== 4. nextpnr-ice40 배치·배선 (진짜 Fmax) =="
  if have nextpnr-ice40 && [ -s "$JSON" ]; then
    # hx8k/ct256 을 쓴다.  up5k/sg48 은 I/O 가 39개뿐이라 이 IP 의 포트
    # (8비트 x 4 입력 + 8비트 출력 + 제어)를 못 담는다 -- 실측으로 그랬다:
    #   ERROR: Unable to find a placement location for cell 'x3[1]$sb_io'
    # **핀이 모자라 P&R 이 죽는 것은 IP 의 품질이 아니다.**  판을 키운다.
    nextpnr-ice40 --hx8k --package ct256 --json "$JSON" \
                  --pcf-allow-unconstrained --placer heap --freq "${PNR_FREQ:-300}" --seed "${PNR_SEED:-1}" > "$LOG.pnr" 2>&1
    grep -E "Max frequency|ICESTORM_LC:|ICESTORM_DSP:|SB_IO:" "$LOG.pnr" | tail -8
    say "   pnr rc=$?"
  else
    say "   nextpnr-ice40 이 없거나 3단계가 JSON 을 못 냈다 -- 건너뜀"
  fi
fi

say ""
say "로그: $LOG.{lint,generic,ice40,pnr}"
