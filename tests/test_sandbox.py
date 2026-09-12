"""sandbox/run.py 를 임시 저장소에서 **실제로 돌려** 붙든다.

붙드는 것 일곱: (1) HEAD 판에는 커밋 안 된 것이 없다, (2) 후보 판(--지금트리)도 git 워크트리다
(바탕과 같은 종류 -- 아니면 유령 회귀), (3) requirements.txt 의 없는 배포는 캐시에 한 번만 깐다,
(4) 판 안의 쓰기가 저장소에 안 닿고 워크트리도 안 남는다, (5) 시간을 넘기면 죽는다, (6) 비밀
변수가 기본으로 지워진다, (7) 산출물은 명시한 것만 나오고 탈출 경로는 돌기 전에 막힌다.

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

    print("\n== 후보 판(--지금트리)도 바탕과 같은 종류다: git 워크트리 ==")
    # 실측 2026-09-12(VM): 바탕은 워크트리, 후보는 파일만 베낀 사본이라 git 을 부르는 검사
    # (test_relay 의 rev-parse · test_seek_report 의 check-ignore)가 후보에서만 죽어 매번 "새로 깨짐" 이 났다.
    r = 격리.실행(["git", "rev-parse", "--short", "HEAD"], repo=repo, 초=30, 지금트리=True)
    ok(r["끝값"] == 0 and r["stdout"].strip(), f"**후보 판 안에서 git 이 돈다** ({r['끝값']} {r['stdout'].strip()!r})")
    (repo / "커밋된.txt").unlink()                       # 작업 트리에서 지운 것은 후보에도 없어야 한다
    r = 격리.실행(["cat", "커밋된.txt"], repo=repo, 초=30, 지금트리=True)
    ok(r["끝값"] != 0, "작업 트리에서 지운 파일은 후보 판에도 없다")
    (repo / "커밋된.txt").write_text("커밋된 내용\n", encoding="utf-8")
    트리들 = subprocess.run(["git", "-C", str(repo), "worktree", "list"],
                          capture_output=True, text=True).stdout.strip().splitlines()
    ok(len(트리들) == 1, f"후보 워크트리도 안 남았다 ({len(트리들)}개)")

    print("\n== requirements.txt 의 없는 배포는 캐시 자리에 한 번만 깐다 ==")
    # 실측 2026-09-12(VM): 두뇌가 fpdf 로 새 모듈 + requirements.txt 한 줄을 붙였는데 시뮬이
    # ModuleNotFoundError 로 빨갰다. 두뇌가 못 고치는 빨강은 판정의 거짓말이다. pip 은 가짜다(망 없이).
    깔기횟수 = []
    def 가짜pip(spec, 어디, 초):
        깔기횟수.append(spec)
        (Path(어디) / "fakedist_se.py").write_text("값 = 42\n", encoding="utf-8")
        return True, ""
    (repo / "requirements.txt").write_text("requests>=2.31.0\n# 주석\n-r 다른.txt\nfakedist_se>=1.0  # 없는 것\n",
                                            encoding="utf-8")
    캐시 = 임시 / "deps-cache"
    원래pip, 원래환경 = 격리.pip깔기, os.environ.get("SE_DEPS_CACHE")
    격리.pip깔기 = 가짜pip
    os.environ["SE_DEPS_CACHE"] = str(캐시)
    try:
        r = 격리.실행(["python3", "-c", "import fakedist_se; print(fakedist_se.값)"], repo=repo, 초=30, 지금트리=True)
        ok(r["끝값"] == 0 and "42" in r["stdout"], f"**없는 배포를 깔아 판에서 import 된다** ({r['끝값']} {r['stderr'][-120:]!r})")
        ok(깔기횟수 == ["fakedist_se>=1.0"], f"없는 것만 깐다 -- 깔린 것(requests)·주석·-r 줄은 안 깐다 ({깔기횟수})")
        ok("새로 깐 의존성 1개" in r["판"], f"판 이름에 깐 것이 적힌다 ({r['판']!r})")
        r = 격리.실행(["python3", "-c", "import fakedist_se"], repo=repo, 초=30, 지금트리=True)
        ok(len(깔기횟수) == 1 and r["끝값"] == 0 and "캐시에서 쓴" in r["판"], f"두 번째는 캐시를 쓰고 pip 을 안 부른다 ({len(깔기횟수)}번 {r['판']!r})")
        ok(not list(repo.glob("**/fakedist_se.py")) and not list(Path(sys.prefix).glob("lib/python*/site-packages/fakedist_se.py")),
           "저장소와 시스템 파이썬에는 안 깔린다")
        def 실패pip(spec, 어디, 초):
            return False, "no matching distribution"
        격리.pip깔기 = 실패pip
        (repo / "requirements.txt").write_text("fakedist_none>=1.0\n", encoding="utf-8")
        r = 격리.실행(["true"], repo=repo, 초=30, 지금트리=True)
        ok(r["돌았나"] and r["끝값"] == 0 and "못 깐 의존성 1개" in r["판"], f"pip 이 실패해도 명령은 돌고 판 이름에 적힌다 ({r['판']!r})")
        ok(not (격리._캐시자리("fakedist_none>=1.0") / ".ok").exists(), "실패한 자리는 캐시에 안 남는다")
    finally:
        격리.pip깔기 = 원래pip
        if 원래환경 is None:
            os.environ.pop("SE_DEPS_CACHE", None)
        else:
            os.environ["SE_DEPS_CACHE"] = 원래환경
        (repo / "requirements.txt").unlink()

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
