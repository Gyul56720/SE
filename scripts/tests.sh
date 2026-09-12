#!/usr/bin/env bash
# **테스트 목록은 한 군데에만 있다.**
#
# 전에는 CI 워크플로에 파일 이름을 손으로 나열했다. 그래서 새 테스트를 만들면 목록에
# 넣는 것을 잊었고, 로컬에서는 도는데 CI 에서는 안 도는(또는 그 반대인) 일이 생겼다.
# 실측 2026-09-06: targets.json 이 무시 규칙에 걸려 저장소에 없었는데 로컬은 초록이었다 --
# 로컬과 CI 가 같은 것을 돌지 않으면 그 차이가 조용히 쌓인다.
#
# 이제 CI 도 이 스크립트를 부른다. 여기서 도는 것이 곧 거기서 도는 것이다.
#
#   scripts/tests.sh            tests/test_*.py 전부
#   scripts/tests.sh -k rhythm  이름에 rhythm 이 든 것만
set -u
cd "$(dirname "$0")/.."
# 뿌리를 PYTHONPATH 에 둔다 -- 모델이 지은 검사가 뿌리 모듈을 임포트해도 산다 (sandbox/run.py 와 같은 까닭)
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

# 따로 다루는 것들 -- 앞선 단계에서 환경변수나 준비 데이터를 주고 돌린다.
SKIP="test_gates_on_incidents.py test_g004_scope.py test_compression_judge.py"

# **설정을 제대로 한 사람만 보는 실패**가 이 저장소에서 네 번 났다(키 세 개 · 루트 .env ·
# 봇 토큰 · 웹훅). 검사가 환경을 안 치우고 들어가면 CI 와 개발 컨테이너에서는 통과하고
# 실제로 돌리는 사람만 깨진 것을 본다 -- 그런 검사는 검사가 아니라 함정이다.
# 그래서 여기서 한 번 더 흉내 내 본다: 설정이 다 있는 기계처럼 돌려도 초록이어야 한다.
if [ -n "${SE_TEST_AS_CONFIGURED:-}" ]; then
  export GEMINI_API_KEY="${GEMINI_API_KEY:-test-key}"
  export GEMINI_API_KEY_FALLBACK="${GEMINI_API_KEY_FALLBACK:-test-2}"
  export DISCORD_BOT_TOKEN="${DISCORD_BOT_TOKEN:-test-token}"
  export DISCORD_CHANNEL_ID="${DISCORD_CHANNEL_ID:-1}"
  # 다섯 번째로 겪은 것: 키가 있으면 오케스트레이터가 일부러 터뜨린 노드를 LLM 으로
  # 고쳐서 런이 성공해 버렸다. 흉내에도 진짜처럼 보이는 키를 넣는다.
  echo "  (설정이 다 있는 기계처럼 돌린다)"
fi

want=""
[ "${1:-}" = "-k" ] && want="${2:-}"

fail=0
ran=0
for f in tests/test_*.py; do
  base="$(basename "$f")"
  case " $SKIP " in *" $base "*) continue ;; esac
  [ -n "$want" ] && case "$base" in *"$want"*) ;; *) continue ;; esac
  ran=$((ran + 1))
  out="$(python3 "$f" 2>&1)"
  code=$?
  # **의존성이 없어서 죽은 것은 실패가 아니라 건너뜀이다** -- 다만 CI 에서는 실패다.
  # 거기서는 requirements.txt 를 깔고 임포트까지 확인하므로, 그래도 없다면 진짜 문제다.
  # (검사하지 않은 초록불은 검사한 빨간불보다 나쁘다 -- 이 저장소가 이미 배운 것이다.)
  if [ $code -ne 0 ] && printf '%s' "$out" | grep -q "ModuleNotFoundError"; then
    miss="$(printf '%s' "$out" | grep -o "No module named '[^']*'" | head -1)"
    if [ -n "${SE_REQUIRE_DEPS:-}" ]; then
      fail=$((fail + 1))
      printf '  실패 %-34s %s  <- CI 에서는 깔려 있어야 한다\n' "$base" "$miss"
    else
      printf '  건너뜀 %-32s %s\n' "$base" "$miss"
    fi
    continue
  fi
  if [ $code -eq 0 ]; then
    printf '  OK   %-34s %s\n' "$base" "$(printf '%s' "$out" | tail -1)"
  else
    fail=$((fail + 1))
    printf '  실패 %-34s\n' "$base"
    printf '%s\n' "$out" | tail -25 | sed 's/^/       /'
  fi
done

echo
if [ "$fail" -gt 0 ]; then
  echo "테스트 $ran개 중 $fail개 실패"
  exit 1
fi
echo "테스트 $ran개 전부 통과"
