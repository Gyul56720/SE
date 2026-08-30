cd ${SE_DIR:-/home/ubuntu/SE} || exit 1
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
