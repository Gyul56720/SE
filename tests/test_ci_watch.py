"""ci_watch(main CI 결론을 봇이 읽는다)를 가짜 HTTP 로 붙든다.

실측 2026-09-11: main gates.yml 60회 연속 초록 0 -- 아무도 안 읽었다.

붙드는 것: (1) 초록/빨강을 conclusion 으로 가른다, (2) 빨강이면 실패 job 로그에서 `실패 test_*.py`
를 뽑는다, (3) 조회 실패는 못잼(초록도 빨강도 아님), (4) 바뀌었나 -- 같은 상태는 두 번 알리지 않고
상태·sha·실패 목록 중 하나라도 바뀌면 알린다, (5) CLI 끝값 0/1/3, (6) 배선 -- 봇이 주기적으로 읽고
관리 채널에 알린다.

망 없이 돈다. 실행: python3 tests/test_ci_watch.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import ci_watch as CW  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def 가짜(결론="failure", 로그="  실패 test_rhythm.py\n  OK test_x.py\n  실패 test_echo.py\n"):
    """결론을 하나 주면 실행 하나, 목록을 주면 **새것부터** 그만큼의 완료 실행을 흉내 낸다."""
    결론들 = [결론] if isinstance(결론, str) else list(결론)

    def f(url, h):
        if "/runs?" in url:
            return 200, json.dumps({"workflow_runs": [
                {"conclusion": c, "head_sha": f"abcdef{i}123456", "html_url": "https://x/run/9",
                 "run_number": 100 - i, "updated_at": "2026-01-01T00:00:00Z", "id": 900 + i,
                 "display_title": "제목"} for i, c in enumerate(결론들)]})
        if url.endswith("/jobs"):
            return 200, json.dumps({"jobs": [{"id": 1, "conclusion": "failure"}, {"id": 2, "conclusion": "success"}]})
        return 200, 로그
    return f


임시 = Path(tempfile.mkdtemp(prefix="test-ci-"))
try:
    CW.요청 = 가짜("success")
    r = CW.보기(임시)
    ok(r["상태"] == "초록" and r["sha"] == "abcdef0" and r["실패"] == [], f"success -> 초록 ({r['말']})")

    CW.요청 = 가짜("failure")
    r = CW.보기(임시)
    ok(r["상태"] == "빨강" and r["실패"] == ["test_rhythm.py", "test_echo.py"], f"**failure -> 빨강 + 실패 검사 이름** ({r['실패']})")
    ok("run/9" in r["말"] and "test_rhythm.py" in r["말"], "말에 url 과 검사 이름")

    CW.요청 = lambda url, h: (403, "forbidden")
    r = CW.보기(임시)
    ok(r["상태"] == "못잼" and "초록이 아니다" in r["말"], "조회 실패는 못잼 -- 초록도 빨강도 아니다")

    print("\n== 바뀌었나: 같은 상태는 두 번 알리지 않는다 ==")
    CW.요청 = 가짜("failure")
    r = CW.보기(임시)
    ok(CW.바뀌었나(r, 임시) and not CW.바뀌었나(r, 임시), "처음은 True, 같은 상태 두 번째는 False")
    CW.요청 = 가짜("failure", 로그="  실패 test_rhythm.py\n")
    r2 = CW.보기(임시)
    ok(CW.바뀌었나(r2, 임시), "실패 목록이 줄면(하나 고쳐지면) 다시 알린다")
    CW.요청 = 가짜("success")
    ok(CW.바뀌었나(CW.보기(임시), 임시), "초록으로 바뀌면 알린다")
    ok((임시 / CW.상태상대).is_file(), "상태 파일이 logs/ 에 남는다")

    print("\n== CLI 끝값 ==")
    import subprocess
    p = subprocess.run([sys.executable, "-c",
                        "import sys; sys.path.insert(0, '.'); import ci_watch as C; "
                        "C.요청 = lambda u, h: (500, 'x'); raise SystemExit(C.main())"],
                       cwd=str(뿌리), capture_output=True, text=True, timeout=30)
    ok(p.returncode == 3 and "못 읽" in p.stdout, f"조회 실패 CLI 끝값 3 ({p.returncode})")
finally:
    CW.요청 = None
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 배선 ==")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("async def _ci지켜보기" in _서버 and "asyncio.create_task(_ci지켜보기())" in _서버, "**봇이 켜지면 CI 를 주기적으로 읽는다**")
ok("ci_watch.바뀌었나" in _서버 and "ADMIN_CHANNEL_ID" in _서버.split("async def _ci지켜보기")[1].split("async def")[0],
   "상태가 바뀔 때만 관리 채널에 알린다")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"ci_watch.py"' in _wf, "ci_watch 가 배포 경로에")

print("\n== 취소는 실패가 아니다 (cancel-in-progress) ==")
# 실측 2026-09-12 18:21: 봇이 켜지며 `[ci_watch] 빨강 c8f96c3 실패 []` 를 찍었다. main 의 마지막 완료 실행이
# conclusion=cancelled 였고 취소된 실행에는 실패 job 이 없으니 이름 없는 '빨강' 이 됐다. 그러면 commit_guard 가
# **거짓 빨강으로 자가 커밋을 전부 막는다** -- 재지 않은 것을 빨강이라 하는 것은 초록이라 하는 것과 같은 잘못이다.
CW.요청 = 가짜(["cancelled"] * 3)
r = CW.보기()
ok(r["상태"] == "못잼" and "취소" in r["말"] and r["실패"] == [],
   f"**완료 실행이 다 취소면 못잼** -- 빨강으로 치지 않는다 ({r['상태']})")
CW.요청 = 가짜(["cancelled", "cancelled", "success"])
r = CW.보기()
ok(r["상태"] == "초록" and "2개는 취소돼 안 쟀다" in r["말"],
   f"취소를 건너뛰고 **판정이 있는 실행**을 찾는다 -- 초록 ({r['말'][:60]})")
CW.요청 = 가짜(["cancelled", "failure"])
r = CW.보기()
ok(r["상태"] == "빨강" and r["실패"] == ["test_rhythm.py", "test_echo.py"],
   f"취소 뒤의 실패는 그대로 빨강이고 검사 이름도 준다 ({r['실패']})")
CW.요청 = 가짜("timed_out")
r = CW.보기()
ok(r["상태"] == "빨강", "시한 초과는 빨강이다(실제로 돌다 못 끝냈다)")
CW.요청 = 가짜("skipped")
r = CW.보기()
ok(r["상태"] == "못잼", "건너뛴 실행도 못잼이다")
_통 = __import__("commit_guard")
_원CI = _통.CI기
try:
    _통.CI기 = lambda repo=None: {"상태": "못잼", "실패": [], "말": "취소뿐"}
    통과, 보 = _통.검사(뿌리, 게이트=False, 감사=False, ci=True)
    ok(통과 and "(경고)" in 보, f"**못잼은 커밋을 막지 않는다(경고만)** -- 6시간 무인 실행이 거짓 빨강에 멈추지 않는다 ({통과})")
    _통.CI기 = lambda repo=None: {"상태": "빨강", "실패": ["test_x.py"], "말": "빨강"}
    통과2, 보2 = _통.검사(뿌리, 게이트=False, 감사=False, ci=True)
    ok(not 통과2 and "[CI 차단]" in 보2, "진짜 빨강은 그대로 막는다")
finally:
    _통.CI기 = _원CI

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("ci_watch: 초록/빨강/못잼 · 실패 검사 이름 · 바뀔 때만 · CLI · 배선 -- 통과")
