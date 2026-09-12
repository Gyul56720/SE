"""sandbox/run.py 를 임시 저장소에서 **실제로 돌려** 붙든다.

붙드는 것 다섯: (1) HEAD 판에는 커밋 안 된 것이 없다, (2) 판 안의 쓰기가 저장소에
안 닿고 워크트리도 안 남는다, (3) 시간을 넘기면 죽는다, (4) 비밀 변수가 기본으로
지워진다, (5) 산출물은 명시한 것만 나오고 탈출 경로는 돌기 전에 막힌다.

`bash -n` 급 겉훑기가 아니라 끝까지 돌린다 -- `tests/test_seek_돌리기.py` 와 같은
까닭이다(검사하지 않은 초록불이 검사한 빨간불보다 나쁘다). LLM·네트워크 없이 돈다.

실행: python3 tests/test_sandbox.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from sandbox import run as 격리  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def 저장소_짓기(어디: Path) -> Path:
    repo = 어디 / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    (repo / "커밋된.txt").write_text("커밋된 내용\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "첫 커밋"], check=True)
    (repo / "안담긴.txt").write_text("커밋 안 된 내용\n", encoding="utf-8")
    return repo


임시 = Path(tempfile.mkdtemp(prefix="test-sandbox-"))
repo = 저장소_짓기(임시)
받을곳 = 임시 / "밖"

try:
    print("== HEAD 판에는 커밋 안 된 것이 없다 ==")
    r = 격리.실행(["cat", "커밋된.txt"], repo=repo, 초=30)
    ok(r["끝값"] == 0 and "커밋된 내용" in r["stdout"], f"커밋된 파일은 보인다 ({r['끝값']})")
    r = 격리.실행(["cat", "안담긴.txt"], repo=repo, 초=30)
    ok(r["끝값"] != 0, "**커밋 안 된 파일은 안 보인다** -- precheck 와 같은 성질")
    r = 격리.실행(["cat", "안담긴.txt"], repo=repo, 초=30, 지금트리=True)
    ok(r["끝값"] == 0 and "커밋 안 된 내용" in r["stdout"],
       "--지금트리 면 커밋 안 된 것도 보인다")

    print("\n== 판 안의 쓰기가 저장소에 안 닿는다 ==")
    r = 격리.실행(["bash", "-c", "echo 오염 > 새파일.txt && rm 커밋된.txt"],
                repo=repo, 초=30)
    ok(r["끝값"] == 0, f"판 안에서 쓰고 지우는 것 자체는 된다 ({r['끝값']})")
    ok(not (repo / "새파일.txt").exists(), "**판에서 만든 파일이 저장소에 없다**")
    ok((repo / "커밋된.txt").exists(), "**판에서 지운 파일이 저장소에 남아 있다**")
    트리들 = subprocess.run(["git", "-C", str(repo), "worktree", "list"],
                          capture_output=True, text=True).stdout.strip().splitlines()
    ok(len(트리들) == 1, f"워크트리가 안 남았다 ({len(트리들)}개)")

    print("\n== 시간을 넘기면 죽는다 ==")
    r = 격리.실행(["sleep", "10"], repo=repo, 초=1)
    ok(r["끝값"] != 0 and "죽였다" in r["메모"], f"1초 제한에 sleep 10 이 죽었다 ({r['메모']})")

    print("\n== 비밀 변수가 기본으로 지워진다 ==")
    os.environ["SANDBOX_TEST_API_KEY"] = "secret-value-12345"
    try:
        명령 = ["bash", "-c", "printenv SANDBOX_TEST_API_KEY || echo 없음"]
        r = 격리.실행(명령, repo=repo, 초=30)
        ok("없음" in r["stdout"] and "secret-value" not in r["stdout"],
           "기본: *_API_KEY 가 자식 환경에 없다")
        r = 격리.실행(명령, repo=repo, 초=30, 키포함=True)
        ok("secret-value-12345" in r["stdout"], "--키포함 을 명시해야 남는다")
    finally:
        del os.environ["SANDBOX_TEST_API_KEY"]

    print("\n== 산출물은 명시한 것만, 탈출은 돌기 전에 막힌다 ==")
    r = 격리.실행(["bash", "-c", "mkdir -p out && echo 답 > out/r.txt"],
                repo=repo, 초=30, 가져와=["out/r.txt", "out/없는.txt"], 밖으로=받을곳)
    담긴 = [p for p in r["산출물"] if not p.startswith("(")]
    ok(len(담긴) == 1 and Path(담긴[0]).read_text(encoding="utf-8").strip() == "답",
       f"명시한 산출물이 밖으로 나왔다 ({r['산출물']})")
    ok(any(p.startswith("(없다)") for p in r["산출물"]),
       "없는 것은 없다고 말한다 -- 조용히 빠지지 않는다")
    for 탈출 in ("../밖.txt", "/etc/passwd", "a/../../밖.txt", "~/밖.txt"):
        try:
            격리.실행(["true"], repo=repo, 초=30, 가져와=[탈출], 밖으로=받을곳)
            ok(False, f"{탈출!r} 가 막히지 않았다")
        except ValueError:
            ok(True, f"{탈출!r} 는 ValueError 로 막힌다 (돌기 전에)")

    print("\n== 망차단은 못 끊으면 안 돌린다 ==")
    원래 = 격리.망차단_가능
    격리.망차단_가능 = lambda: False
    try:
        r = 격리.실행(["echo", "돌면안된다"], repo=repo, 초=30, 망차단=True)
        ok(not r["돌았나"] and r["끝값"] == 3 and "돌면안된다" not in r["stdout"],
           "**끊은 척하고 돌리지 않는다** -- 돌았나=False, 끝값 3")
    finally:
        격리.망차단_가능 = 원래
    if 격리.망차단_가능():
        r = 격리.실행(["true"], repo=repo, 초=30, 망차단=True)
        ok(r["끝값"] == 0, f"이 환경은 unshare 가 돼서 망차단으로도 돈다 ({r['끝값']})")
    else:
        print("  (이 환경은 unshare 가 안 된다 -- 위의 fail-closed 갈래가 실제 갈래다)")
finally:
    shutil.rmtree(임시, ignore_errors=True)

print()
# 실측 2026-09-12(VM): 모델이 지은 tests/test_x.py 가 `from utils.x import …` 로 죽어 레포 전체 시뮬이
# 빨갰다. 실행기가 판의 뿌리를 PYTHONPATH 에 놓아 주면 그 함정이 없다 -- 세 실행기 모두.
_sb = (Path(__file__).resolve().parent.parent / "sandbox" / "run.py").read_text(encoding="utf-8")
_ts = (Path(__file__).resolve().parent.parent / "scripts" / "tests.sh").read_text(encoding="utf-8")
_pc = (Path(__file__).resolve().parent.parent / "scripts" / "precheck.sh").read_text(encoding="utf-8")
ok('env["PYTHONPATH"] = str(tmp)' in _sb, "sandbox 가 판의 뿌리를 PYTHONPATH 에 둔다")
ok('export PYTHONPATH="$PWD' in _ts and 'export PYTHONPATH="$PWD' in _pc, "tests.sh · precheck.sh 도 뿌리를 둔다")

if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("sandbox: HEAD 격리 · 쓰기 차단 · 시간 고삐 · 비밀 제거 · 산출물 경계 -- 통과")
