#!/usr/bin/env bash
#
# **정해진 시간 동안 계속 판다.**
#
#     bash scripts/dig_loop.sh '<물음>' [분] [낼파일]
#     bash scripts/dig_loop.sh '중화역 맛집' 10
#
# `dig/run.py --찾기` 한 번과 무엇이 다른가 -- 한 번은 문을 두드리고 위쪽 몇을 파고
# 끝난다. 여기는 **캔 주소를 원장에 쌓아 두고 안 판 것부터 이어 판다.** 그리고
# 라운드마다 더 깊이 판다(--따라 를 키운다). 시간이 다하면 멈춘다.
#
#     라운드 0   문 22개를 두드려 주소를 캔다 (--찾기 --json)
#     라운드 n   안 판 주소를 batch 개씩, --따라 를 키워 가며
#     주소가 다하면  --찾기 를 다시 돌려 더 캔다 (다른 문이 다른 것을 준다)
#
# ## 한글 변수명을 쓰지 않는다
#
# bash 식별자는 `[A-Za-z_][A-Za-z0-9_]*` 뿐이다. `초=25` 는 **대입이 아니라
# 명령어**로 파싱되고 `set -u` 아래에서 `$초` 는 unbound 라 첫 줄에서 죽는다.
# 실측 2026-09-09: `scripts/seek.sh` 가 그것 때문에 **한 줄도 안 돌았다.**
# `bash -n` 은 이것을 안 잡는다 -- 문법으로는 그냥 명령어 하나라서 멀쩡하다.
# 그래서 `tests/test_dig_loop.py` 가 이 파일을 **실제로 돌린다.**

set -uo pipefail
# **`set -e` 를 안 쓴다.** 한 라운드가 403 으로 끝값 3 을 내는 것은 이 도구에서
# **정상**이다(dig 는 거절이 없다 -- 못 받은 것도 까닭과 함께 낸다). 거기서 루프가
# 죽으면 남은 시간을 통째로 버린다.

Q="${1:-}"
MINS="${2:-10}"
OUT="${3:-}"
# 갈아 끼울 수 있게 둔다 -- 검사가 이 자리에 가짜를 물려 **진짜로 돌려 본다.**
DIG="${DIG_CMD:-python3 dig/run.py}"
# 라운드마다 몇 주소씩 팔지, --따라 를 얼마에서 시작해 얼마씩 키울지.
BATCH="${DIG_LOOP_BATCH:-4}"
FOLLOW="${DIG_LOOP_FOLLOW:-8}"
FOLLOW_STEP="${DIG_LOOP_FOLLOW_STEP:-6}"
# **몇 홉까지.** 1 이면 목록에서 글로 한 걸음이 끝이라 제목만 쌓인다.
DEPTH="${DIG_LOOP_DEPTH:-2}"

if [ -z "$Q" ]; then
  echo "물음을 줘라."
  echo "  bash scripts/dig_loop.sh '중화역 맛집' 10"
  echo "  bash scripts/dig_loop.sh '3x3 텐서 랭크 하한' 30 logs/tensor.txt"
  exit 3
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 3
mkdir -p logs

STAMP="$(date +%Y%m%d-%H%M%S)"
[ -z "$OUT" ] && OUT="logs/dig-$STAMP.txt"
SEEDS="$(mktemp)"
SEEN="$(mktemp)"
TMPJSON="$(mktemp)"
trap 'rm -f "$SEEDS" "$SEEN" "$TMPJSON"' EXIT

# 검사가 3초짜리로 돌려 볼 수 있게. 사람은 분으로 준다.
SECS="${DIG_LOOP_SECONDS:-$((MINS * 60))}"
DEADLINE=$((SECONDS + SECS))

# **--찾 말은 물음에서 뽑는다.** 여기서 지어내면 그것이 하드코딩이다.
FIND="$(printf '%s' "$Q" | tr -s ' ' ',')"

echo "# dig 루프 -- '$Q'" | tee "$OUT"
echo "#   ${SECS}초 · 라운드마다 ${BATCH}주소 · --따라 ${FOLLOW}부터 +${FOLLOW_STEP} · --깊이 ${DEPTH}" | tee -a "$OUT"
echo "#   $OUT" | tee -a "$OUT"

# ── 주소를 캔다. 안 판 것만 SEEDS 에 쌓는다 ────────────────────────
harvest() {
  local left=$1
  [ "$left" -le 3 ] && return 0
  timeout "$left" $DIG --찾기 "$Q" --json > "$TMPJSON" 2>/dev/null
  python3 - "$TMPJSON" <<'PY' >> "$SEEDS"
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:                                              # noqa: BLE001
    raise SystemExit(0)                                        # 못 받아도 루프는 산다
for x in (d.get("찾은주소") or []):
    u = (x or {}).get("주소") or ""
    if u:
        print(u)
PY
}

harvest $((DEADLINE - SECONDS))
FOUND=$(sort -u "$SEEDS" | wc -l | tr -d ' ')
echo "# 캔 주소 $FOUND 개" | tee -a "$OUT"

ROUND=0
while [ "$SECONDS" -lt "$DEADLINE" ]; do
  LEFT=$((DEADLINE - SECONDS))
  [ "$LEFT" -le 3 ] && break

  # 안 판 것만. `comm` 은 양쪽이 정렬돼 있어야 한다.
  NEXT="$(comm -23 <(sort -u "$SEEDS") <(sort -u "$SEEN") | head -n "$BATCH")"

  if [ -z "$NEXT" ]; then
    # 판 것이 다했다. 다시 두드려 본다 -- **다른 문이 다른 것을 준다.**
    harvest "$LEFT"
    NEXT="$(comm -23 <(sort -u "$SEEDS") <(sort -u "$SEEN") | head -n "$BATCH")"
    if [ -z "$NEXT" ]; then
      echo "# 더 팔 주소가 없다 (라운드 $ROUND 에서 멈춤)" | tee -a "$OUT"
      break
    fi
  fi

  ROUND=$((ROUND + 1))
  LEFT=$((DEADLINE - SECONDS))
  [ "$LEFT" -le 3 ] && break
  echo "" >> "$OUT"
  echo "═══ 라운드 $ROUND · --따라 $FOLLOW · $(echo "$NEXT" | wc -l | tr -d ' ')주소 · ${LEFT}초 남음 ═══" >> "$OUT"

  # shellcheck disable=SC2086
  timeout "$LEFT" $DIG --url $NEXT --따라 "$FOLLOW" --깊이 "$DEPTH" \
    --찾 "$FIND" >> "$OUT" 2>&1
  printf '%s\n' "$NEXT" >> "$SEEN"
  FOLLOW=$((FOLLOW + FOLLOW_STEP))
done

# ── 무엇을 얼마나 캤나. **안 세면 돌았는지도 모른다** ──────────────
# **`|| echo 0` 을 쓰지 않는다.** `grep -c` 는 안 맞으면 "0" 을 **찍고** 끝값 1 을
# 낸다 -- 그러면 `||` 가 0 을 하나 더 찍어 값이 "0\n0" 이 되고, 요약에 떠도는 0 이
# 한 줄 생긴다(실측: 진짜로 한 번 돌려 보고 나서야 보였다). `set -e` 를 안 썼으므로
# 끝값 1 은 그냥 지나간다.
BYTES=$(wc -c < "$OUT" | tr -d ' ')
PAGES=$(grep -c '^## 글 ' "$OUT" 2>/dev/null)
# 캔값 줄 꼴: `  가격    (2) 9,000원 · 15,000원`
VALUES=$(grep -cE '^  [^ ]+ +\([0-9]+\)' "$OUT" 2>/dev/null)
DUG=$(sort -u "$SEEN" | grep -c . 2>/dev/null)
SEEDN=$(sort -u "$SEEDS" | grep -c . 2>/dev/null)
echo ""
echo "── 끝 ─────────────────────────────────────────"
echo "  라운드   $ROUND"
echo "  판 주소  $DUG / 캔 것 $SEEDN"
echo "  받은 쪽  $PAGES"
echo "  캔값 줄  $VALUES"
echo "  글자     $BYTES"
echo "  파일     $OUT"
[ "$BYTES" -gt 0 ] || exit 3
