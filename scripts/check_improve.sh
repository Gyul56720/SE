cd ${SE_DIR:-/home/ubuntu/SE} || exit 1
echo "===== 0. 서버가 들고 있는 코드 (배포가 반영됐는가) ====="
echo "HEAD: $(git rev-parse --short HEAD)  $(git log -1 --format=%s | cut -c1-60)"
for feat in "checks" "best_seen_by_target" "_log_line_count"; do
  if grep -q "$feat" mathmetics/matrix_exponent/improve_agent.py \
                     mathmetics/matrix_exponent/self_improve_loop.py 2>/dev/null; then
    echo "  [O] $feat"
  else
    echo "  [X] $feat  <- 이 기능이 없는 옛 코드다 (배포 미반영)"
  fi
done
if grep -q "_LEADING_STATUS" bot_tools.py 2>/dev/null; then
  echo "  [O] 에러분류 수정판(_LEADING_STATUS)"
else
  echo "  [X] 에러분류 수정판  <- 옛 substring 매칭 사용 중"
fi

echo
echo "===== 1. 서비스/프로세스 ====="
systemctl is-active se-matrix-search 2>/dev/null || echo "(systemctl 확인 불가)"
ps -eo pid,etime,args | grep "[s]elf_improve_loop" || echo "!! 루프 프로세스 없음"

echo
echo "===== 2. 대장 (improve_agent 가 돌았는가) ====="
python3 - <<'PY'
import json, time, pathlib
p = pathlib.Path("mathmetics/matrix_exponent/improve_ledger.json")
if not p.exists():
    print("대장 파일 없음 -> improve_agent 가 아직 한 번도 실행되지 않았다")
    raise SystemExit
d = json.loads(p.read_text())
print(f"version : {d.get('version')}")
print(f"checks  : {d.get('checks', 0)}   <- 정체 판정을 시도한 총 횟수 (0 이면 개선 주기 미도달)")
a = d.get("attempts", [])
print(f"attempts: {len(a)}   <- 정체로 판정돼 제안까지 간 횟수")
llm = [x for x in a if x.get("backend") == "llm_proposer"]
print(f"  이 중 llm_proposer: {len(llm)}건")
for x in a[-5:]:
    ts = x.get("ts")
    when = time.strftime("%m-%d %H:%M:%S", time.localtime(ts)) if ts else "-"
    print(f"   {when}  {x.get('backend','-'):<15} {x.get('result','-'):<16} bench={x.get('bench_residual')}")
lc = d.get("last_check")
if lc:
    when = time.strftime("%m-%d %H:%M:%S", time.localtime(lc["ts"]))
    print(f"last_check: {when}  stagnant={lc.get('stagnant')}  사유={lc.get('reason')}")
    if "observed" in lc:
        print(f"            observed={lc['observed']:.6f}  threshold={lc.get('threshold')}")
PY

echo
echo "===== 3. 최근 improve 호출 로그 ====="
journalctl -u se-matrix-search -n 400 --no-pager 2>/dev/null \
  | grep -o '{"improve".*}' | tail -5 || echo "(저널 접근 불가 -- sudo 필요할 수 있음)"

echo
echo "===== 4. 능력 래칫 (이미 되던 것이 안 되게 됐는가) ====="
# 원래 커밋 게이트 G010 이었다. b=2 에서 seed 12 x 2000 iter 를 실제로 돌리는 검사라
# 커밋 경로에 두면 git_sync 가 GIT_MUTEX 를 쥔 채 오래 머문다 -- 그래서 여기(점검 시점)로
# 옮겼다. 통과 0 / 후퇴 1. numpy 가 없거나 프레임워크가 없으면 조용히 통과한다.
python3 "${SE_DIR:-/home/ubuntu/SE}/scripts/capability_ratchet.py" || echo "  ^^ 후퇴 감지: searcher 변경을 되돌리거나 고쳐라"
