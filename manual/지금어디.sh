#!/usr/bin/env bash
# 지금어디.sh -- 지금 어디까지 왔는지 **기계가** 답한다.
#
#     bash manual/지금어디.sh
#
# 매뉴얼을 처음 열었거나, 며칠 쉬었다가 돌아왔거나, 다음에 뭘 할지
# 모르겠을 때 이것부터 돌린다.  기억에 기대지 않는다.
#
# 변수 이름이 전부 아스키인 이유: bash 는 한글 식별자를 못 받는다.
# `단계=1` 은 대입이 아니라 **명령어**로 파싱되어 "No such file or
# directory" 가 난다.  이 저장소가 실제로 한 번 물린 자리다.
set -u
cd "$(dirname "$0")/.." || exit 1
ROOT=$(pwd)

G='\033[32m'; R='\033[31m'; Y='\033[33m'; N='\033[0m'
okc=0; ngc=0

say()  { printf '%b\n' "$*"; }
head2() { say ""; say "── $* ────────────────────────────────"; }

# chk <설명> <명령...>   : 명령이 0 이면 통과
chk() {
  local what="$1"; shift
  if "$@" >/dev/null 2>&1; then
    say "  ${G}[o]${N} $what"; okc=$((okc+1)); return 0
  else
    say "  ${R}[ ]${N} $what"; ngc=$((ngc+1)); return 1
  fi
}

have() { command -v "$1" >/dev/null 2>&1; }

say "╔══════════════════════════════════════════════╗"
say "║  1인 디자인 하우스 -- 지금 어디까지 왔나     ║"
say "╚══════════════════════════════════════════════╝"
say "저장소: $ROOT"

head2 "0단계  연장이 있는가 (manual/00_설치.md)"
chk "verilator (lint + 빠른 시뮬)"      have verilator
chk "iverilog  (시뮬)"                  have iverilog
chk "yosys     (합성)"                  have yosys
chk "nextpnr-ice40 (배치배선 + Fmax)"   have nextpnr-ice40
chk "g++       (C++ 모델)"              have g++
chk "python3"                           have python3
if have /opt/bambu/bin/bambu || have bambu; then
  say "  ${G}[o]${N} bambu (HLS) -- 선택"
else
  say "  ${Y}[-]${N} bambu (HLS) -- 없어도 된다. 08단계까지는 안 쓴다"
fi

head2 "1단계  만들 것을 골랐는가 (manual/02_제품고르기.md)"
chk "work/제품.md 가 있다"  test -f "$ROOT/work/제품.md"

head2 "2단계  스펙을 썼는가 (manual/03_스펙쓰기.md)"
chk "work/스펙.md 가 있다"  test -f "$ROOT/work/스펙.md"
if [ -f "$ROOT/work/스펙.md" ]; then
  if grep -q "TODO" "$ROOT/work/스펙.md"; then
    say "  ${Y}[!]${N} 스펙에 TODO 가 남아 있다 -- $(grep -c TODO "$ROOT/work/스펙.md") 개"
  else
    say "  ${G}[o]${N} 스펙에 TODO 가 없다"
  fi
fi

head2 "3단계  C++ 골든모델이 도는가 (manual/04_C++모델.md)"
if [ -f "$ROOT/work/model/golden.cpp" ]; then
  if g++ -O2 -I"$ROOT/work/model" -o /tmp/_gm "$ROOT/work/model/golden.cpp" 2>/dev/null; then
    say "  ${G}[o]${N} work/model/golden.cpp 가 컴파일된다"; okc=$((okc+1))
  else
    say "  ${R}[ ]${N} work/model/golden.cpp 가 **컴파일 안 된다**"; ngc=$((ngc+1))
  fi
else
  say "  ${R}[ ]${N} work/model/golden.cpp 가 없다"; ngc=$((ngc+1))
fi

head2 "4단계  RTL 이 lint 를 지나는가 (manual/05_RTL.md)"
DUT=$(ls "$ROOT"/work/rtl/*.v 2>/dev/null | grep -v '_tb\.v$' | head -1)
if [ -n "${DUT:-}" ] && have verilator; then
  TOP=$(basename "$DUT" .v)
  if verilator --lint-only -Wall --top-module "$TOP" "$DUT" >/dev/null 2>&1; then
    say "  ${G}[o]${N} $TOP -- 경고 0"; okc=$((okc+1))
  else
    WN=$(verilator --lint-only -Wall --top-module "$TOP" "$DUT" 2>&1 | grep -cE '^%(Error|Warning)')
    say "  ${R}[ ]${N} $TOP -- 경고/오류 $WN 개.  manual/05_RTL.md 의 표를 볼 것"; ngc=$((ngc+1))
  fi
else
  say "  ${R}[ ]${N} work/rtl/ 에 DUT 가 없다"; ngc=$((ngc+1))
fi

head2 "5단계  검증이 도는가 (manual/06_검증.md)"
chk "work/rtl 에 테스트벤치가 있다"  bash -c "ls $ROOT/work/rtl/*_tb.v >/dev/null 2>&1"
if [ -f "$ROOT/work/검증결과.txt" ]; then
  LAST=$(grep -oE "틀림 [0-9]+" "$ROOT/work/검증결과.txt" | tail -1)
  say "  기록된 마지막 결과: ${LAST:-없음}"
  if [ "${LAST:-}" = "틀림 0" ]; then okc=$((okc+1)); else ngc=$((ngc+1)); fi
else
  say "  ${R}[ ]${N} work/검증결과.txt 가 없다 -- 아직 안 돌렸다"; ngc=$((ngc+1))
fi

head2 "6단계  합성 수가 있는가 (manual/07_합성과타이밍.md)"
chk "work/합성결과.txt 가 있다"  test -f "$ROOT/work/합성결과.txt"

head2 "7단계  납품 문서가 채워졌는가 (manual/08_납품문서.md)"
for f in DATASHEET.md INTEGRATION.md KNOWN_ISSUES.md; do
  if [ -f "$ROOT/work/$f" ]; then
    # `grep -c` 는 못 찾으면 **0 을 찍고 종료코드 1** 을 낸다.
    # 그래서 `|| echo 0` 을 붙이면 "0\n0" 이 되어 `[ "$T" -eq 0 ]` 가
    # "integer expression expected" 로 깨진다 -- 실측으로 물린 자리다.
    T=$(grep -c "TODO" "$ROOT/work/$f" 2>/dev/null)
    [ -z "$T" ] && T=0
    if [ "$T" -eq 0 ]; then
      say "  ${G}[o]${N} work/$f  (TODO 0)"; okc=$((okc+1))
    else
      say "  ${Y}[!]${N} work/$f  TODO $T 개 남음"; ngc=$((ngc+1))
    fi
  else
    say "  ${R}[ ]${N} work/$f 가 없다"; ngc=$((ngc+1))
  fi
done

say ""
say "═══════════════════════════════════════════════"
say "  통과 $okc 개 / 남은 것 $ngc 개"
say ""
if [ "$ngc" -eq 0 ]; then
  say "  ${G}팔 수 있는 모양이다.${N}  manual/09_값매기기와영업.md 로."
else
  say "  ${Y}다음에 할 일${N}: 위에서 ${R}[ ]${N} 가 붙은 **맨 위 한 줄**."
  say "  그 줄 옆 괄호 안 문서를 연다.  여러 개를 동시에 하지 않는다."
fi
say "═══════════════════════════════════════════════"
