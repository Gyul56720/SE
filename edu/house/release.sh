#!/usr/bin/env bash
# 판매 가능 관문 -- 한 번에 다 돌리고, **못 잰 것은 초록이라고 안 한다**.
#
#   bash edu/house/release.sh [블록이름 ...]
#
# 종료 코드 0 통과 / 1 실패 / 2 못 쟀다.
#
# 이 스크립트는 **깨끗한 판**에서 돈다(scripts/precheck.sh 와 같은 이유):
# 작업 디렉터리에는 있는데 커밋에 안 담긴 파일이 있으면 여기서는 초록이고
# 고객에게는 "그런 파일 없다" 가 된다. 이 저장소가 다섯 번 앓은 병이다.
#
# **셸 변수명에 한글을 쓰지 않는다** -- bash 는 식별자로 [A-Za-z_][A-Za-z0-9_]*
# 만 받는다(CLAUDE.md). 한글 변수는 대입이 아니라 명령어로 파싱된다.
set -u

ROOT=$(git rev-parse --show-toplevel) || exit 2
CLEAN=""
WORK="${SE_RELEASE_DIR:-}"
if [ -z "$WORK" ]; then
  WORK=$(mktemp -d) || exit 2
  if git -C "$ROOT" worktree add --detach "$WORK" HEAD >/dev/null 2>&1; then
    CLEAN="$WORK"
    trap 'git -C "$ROOT" worktree remove --force "$WORK" >/dev/null 2>&1; rm -rf "$WORK"' EXIT
  else
    echo "깨끗한 판을 못 꺼냈다 -- 모르는 것은 안 된 것으로 다룬다" >&2
    exit 2
  fi
fi

AGENT="$WORK/edu/agent"
HOUSE="$WORK/edu/house"
BLOCKS="$*"
if [ -z "$BLOCKS" ]; then
  BLOCKS=$(ls "$AGENT/blocks" 2>/dev/null | tr '\n' ' ')
fi

pass=0; fail=0; unknown=0
line() { printf '  %-10s %-26s %s\n' "$1" "$2" "$3"; }
ok()   { pass=$((pass+1));    line "통과"   "$1" "$2"; }
bad()  { fail=$((fail+1));    line "실패"   "$1" "$2"; }
huh()  { unknown=$((unknown+1)); line "못쟀다" "$1" "$2"; }

echo "판매 가능 관문 -- $(git -C "$ROOT" rev-parse --short HEAD)"
echo

for B in $BLOCKS; do
  [ -f "$AGENT/blocks/$B/block.py" ] || continue
  echo "== $B =="
  OUT=$(cd "$AGENT" && SE_LEDGER_ROOT="$WORK/.relledger" timeout 900 python3 - "$B" <<'PY' 2>&1
import sys, os, json, importlib.util
sys.path.insert(0, os.getcwd())
import harness, mutscore
name = sys.argv[1]
spec = importlib.util.spec_from_file_location("b", f"blocks/{name}/block.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
res = {}
ok, why = harness.자해검사(m, 시행=80)
res["자해검사"] = [bool(ok), why]
bad = 0; mind = 10**9; perf = None
시행 = getattr(m, "관문시행", 600)
for s_ in range(20):
    r = harness.잰다(m, 시행=시행, 씨앗=1000 + s_)
    if r.오류:
        res["실행오류"] = r.오류; break
    bad += r.틀림; mind = min(mind, r.서로다른출력)
    if r.성능실패: perf = r.성능실패
res["틀림"] = bad
res["최소서로다른출력"] = mind
res["성능"] = perf
res["성능한계선언"] = hasattr(m, "성능한계")
res["성능해당없음"] = getattr(m, "성능해당없음", None)
sc = mutscore.점수(m, 시행=300, 씨앗들=(1,), 최대변이=60, 시간제한=10)
res["변이"] = {"수": sc["변이수"], "잡힘": sc["잡힘"], "점수": sc["점수"],
               "탈출": len(sc["탈출"])}
print(json.dumps(res, ensure_ascii=False))
PY
)
  J=$(printf '%s' "$OUT" | tail -1)
  if ! printf '%s' "$J" | python3 -c "import sys,json;json.load(sys.stdin)" 2>/dev/null; then
    huh "에이전트" "돌리지 못했다: $(printf '%s' "$OUT" | tail -2 | head -1)"
  else
    eval "$(printf '%s' "$J" | python3 -c "
import sys, json
d = json.load(sys.stdin)
v = d['변이']
print('SELF=%d' % int(bool(d['자해검사'][0])))
print('BADC=%d' % d.get('틀림', -1))
print('DIST=%d' % d.get('최소서로다른출력', 0))
print('PERF=%d' % (1 if d.get('성능') else 0))
print('PDEC=%d' % (1 if d.get('성능한계선언') else 0))
print('PNA=%s' % (d.get('성능해당없음') or ''))
print('MSCORE=%.1f' % (v['점수'] * 100))
print('MESC=%d' % v['탈출'])
print('MNUM=%d' % v['수'])
")"
    [ "$SELF" = "1" ] && ok "자해검사" "비교가 문다" || bad "자해검사" "비교가 안 문다 -- 아래 결과는 뜻이 없다"
    [ "$BADC" = "0" ] && ok "회귀" "씨앗 20개, 불일치 0" || bad "회귀" "불일치 $BADC"
    [ "$DIST" -ge 20 ] 2>/dev/null && ok "자극" "서로 다른 출력 $DIST" || bad "자극" "서로 다른 출력 $DIST -- 자극이 얕다"
    if [ "$PDEC" = "1" ]; then
      [ "$PERF" = "0" ] && ok "처리량" "선언된 한계 안" || bad "처리량" "한계를 넘었다"
    elif [ -n "$PNA" ]; then
      ok "처리량" "해당 없음: $PNA"
    else
      huh "처리량" "성능한계() 도 성능해당없음 도 없다 -- 어느 쪽인지 적어라"
    fi
    if [ "$MESC" != "0" ]; then
      bad "변이점수" "$MSCORE% -- **판정 안 된 탈출 $MESC 개**. 등가인지 구멍인지 적어라"
    elif awk "BEGIN{exit !($MSCORE >= 90)}"; then
      ok "변이점수" "$MSCORE% ($MNUM 개), 판정 안 된 탈출 없음"
    else
      bad "변이점수" "$MSCORE% -- 90% 아래, 탈출 $MESC"
    fi
  fi

  # DUT 파일들 = 소스들() 에서 tb.v 를 뺀 것.  여러 모듈이면 다 같이 본다 --
  # 하나만 lint 하면 인스턴스된 모듈을 못 찾아 실패한다.
  SRC=$(cd "$AGENT" && python3 -c "
import importlib.util, os
sp = importlib.util.spec_from_file_location('b', 'blocks/$B/block.py')
m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
print(' '.join(p for p in m.소스들() if os.path.basename(p) != 'tb.v'))
" 2>/dev/null)
  TOP=$(cd "$AGENT" && python3 -c "
import importlib.util, sys
sp = importlib.util.spec_from_file_location('b', 'blocks/$B/block.py')
m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
print(getattr(m, '합성톱', '') or '')
" 2>/dev/null)
  if [ -n "$SRC" ] && [ -n "$TOP" ]; then
    if command -v verilator >/dev/null 2>&1; then
      if verilator --lint-only -Wall --top-module "$TOP" $SRC >/tmp/lint.$$ 2>&1; then
        ok "lint" "경고 없음"
      else
        bad "lint" "$(wc -l </tmp/lint.$$) 줄 -- verilator --lint-only -Wall"
      fi
      rm -f /tmp/lint.$$
    else
      huh "lint" "verilator 가 없다"
    fi
    if command -v yosys >/dev/null 2>&1; then
      YS=""; for f in $SRC; do YS="$YS read_verilog -sv $f;"; done
      if yosys -q -p "$YS hierarchy -top $TOP; proc; opt; techmap; opt; stat" \
           >/tmp/ys.$$ 2>&1; then
        CELLS=$(grep -oP 'Number of cells:\s+\K[0-9]+' /tmp/ys.$$ | tail -1)
        ok "합성" "$TOP: 셀 ${CELLS:-?}개"
      else
        bad "합성" "yosys 실패"
      fi
      rm -f /tmp/ys.$$
    else
      huh "합성" "yosys 가 없다"
    fi
  else
    huh "lint/합성" "dut.v 또는 합성톱 이 없다 (생성된 블록일 수 있다)"
  fi
  echo
done

echo "== 집 전체 =="
if (cd "$HOUSE" && python3 regmap.py --전부 "$WORK/.relgen" >/dev/null 2>&1) \
   && iverilog -g2012 -o /dev/null "$WORK/.relgen"/*_regs.v >/dev/null 2>&1; then
  ok "레지스터맵" "RTL·헤더·문서·IP-XACT 생성, RTL 컴파일됨"
else
  bad "레지스터맵" "생성 또는 컴파일 실패"
fi

for D in DATASHEET.md INTEGRATION.md KNOWN_ISSUES.md; do
  if [ -s "$HOUSE/$D" ]; then ok "문서" "$D"; else bad "문서" "$D 가 없거나 비었다"; fi
done

echo
echo "통과 $pass · 실패 $fail · 못쟀다 $unknown"
if [ "$fail" -gt 0 ]; then
  echo "=> 팔 수 없다. 실패한 줄을 고쳐라."
  exit 1
fi
if [ "$unknown" -gt 0 ]; then
  echo "=> 못 잰 것이 $unknown 개 있다. **모르는 것은 안 된 것으로 다룬다** -- 초록이라고 하지 마라."
  exit 2
fi
echo "=> 전부 통과."
exit 0
