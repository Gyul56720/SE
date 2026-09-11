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
    def 요청(url, headers):
        if "/workflows/gates.yml/runs" in url:
            return 200, json.dumps({"workflow_runs": [{"conclusion": 결론, "head_sha": "abcdef0123", "html_url": "https://x/run/9",
                                                         "run_number": 9, "updated_at": "t", "id": 77, "display_title": "m"}]})
        if url.endswith("/runs/77/jobs"):
            return 200, json.dumps({"jobs": [{"id": 5, "conclusion": "failure"}, {"id": 6, "conclusion": "success"}]})
        if url.endswith("/jobs/5/logs"):
            return 200, 로그
        return 404, "{}"
    return 요청


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

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("ci_watch: 초록/빨강/못잼 · 실패 검사 이름 · 바뀔 때만 · CLI · 배선 -- 통과")
