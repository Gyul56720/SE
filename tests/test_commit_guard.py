"""commit_guard(봇 커밋 전의 문 셋: 게이트 · 바뀐 파일의 검사 · main CI)를 가짜 문으로 붙든다.

실측 2026-09-11: 게이트만 보고 커밋했더니 main 이 하루 넘게 빨강인 채 자가 커밋 35번.

붙드는 것: (1) 셋 다 초록이면 통과, (2) 검사 빨강이면 막고 검사 이름·꼬리를 준다, (3) 검사를
못 돌렸으면(결과 None) **막는다**(fail-closed), (4) CI 빨강이면 막고 실패 검사를 준다, (5) CI 못잼은
경고만(근거 없이 막지 않는다), (6) 게이트 위반이면 막고 고친 것은 보고에 남는다, (7) 문이 예외로
죽어도 닫힌 문이다, (8) 배선 -- git_sync 가 run_gates 직접 대신 commit_guard.검사 를 부른다.

LLM·망·디스코드 없이 돈다. 실행: python3 tests/test_commit_guard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import commit_guard as G  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


초록게이트 = lambda repo: (True, [], "")                                       # noqa: E731
초록감사 = lambda repo: {"결과": [("tests/test_a.py", 0, ["a: 통과"])], "안덮임": [], "안봄": [], "변경": ["a.py"]}  # noqa: E731
초록CI = lambda repo: {"상태": "초록", "sha": "abc", "url": "", "번호": 1, "실패": [], "말": "main CI 초록 (#1 abc)"}  # noqa: E731

try:
    G.게이트기, G.감사기, G.CI기 = 초록게이트, 초록감사, 초록CI
    ok_, 보 = G.검사(뿌리)
    ok(ok_ and "검사 통과 1개" in 보 and "초록" in 보, f"셋 다 초록 -> 통과 ({보.splitlines()[0][:40]})")

    print("\n== 검사 빨강 -> 막힘 ==")
    G.감사기 = lambda repo: {"결과": [("tests/test_a.py", 0, []), ("tests/test_b.py", 1, ["b: 2개 실패 -- [...]"])],
                         "안덮임": ["c.py"], "안봄": [], "변경": ["a.py", "b.py", "c.py"]}
    ok_, 보 = G.검사(뿌리)
    ok(not ok_ and "[검사 차단]" in 보 and "test_b.py" in 보 and "2개 실패" in 보, "**빨간 검사가 있으면 커밋하지 않는다** + 이름·꼬리")
    ok("검사 없는 .py 변경" in 보 and "c.py" in 보, "검사 없는 변경도 보고에")

    print("\n== 검사를 못 돌렸으면 막는다 (fail-closed) ==")
    G.감사기 = lambda repo: {"결과": None, "안덮임": [], "안봄": [], "변경": None}
    ok_, 보 = G.검사(뿌리)
    ok(not ok_ and "검사하지 않은 초록불" in 보, "**못 돌린 검사는 초록이 아니다 -- 막는다**")

    print("\n== CI 빨강 -> 막힘 · 못잼 -> 경고만 ==")
    G.감사기 = 초록감사
    G.CI기 = lambda repo: {"상태": "빨강", "sha": "def", "url": "https://x", "번호": 2,
                        "실패": ["test_rhythm.py"], "말": "**main CI 빨강** (#2 def failure) https://x\n  실패 검사: test_rhythm.py"}
    ok_, 보 = G.검사(뿌리)
    ok(not ok_ and "[CI 차단]" in 보 and "test_rhythm.py" in 보 and "빨강 위에" in 보, "**main 빨강이면 자가 수정을 쌓지 않는다** + 실패 검사 이름")
    G.CI기 = lambda repo: {"상태": "못잼", "sha": "", "url": "", "번호": 0, "실패": [], "말": "못 읽었다"}
    ok_, 보 = G.검사(뿌리)
    ok(ok_ and "(경고)" in 보, "CI 못잼은 경고만 -- 근거 없이 막지 않는다")

    print("\n== 게이트 위반 -> 막힘, 고친 것은 남는다 ==")
    G.CI기 = 초록CI
    G.게이트기 = lambda repo: (False, ["G017 고침: x.py (1개 리터럴)"], "G013 -- y.py 가 paths 에 없다")
    ok_, 보 = G.검사(뿌리)
    ok(not ok_ and "[게이트 차단]" in 보 and "고침 G017" in 보 and "G013" in 보, "게이트 위반은 막고, 자동으로 고친 것은 보고에")

    print("\n== 문이 예외로 죽어도 닫힌 문 ==")
    def 죽는(repo):
        raise RuntimeError("붕")
    G.게이트기 = 죽는
    ok_, 보 = G.검사(뿌리)
    ok(not ok_ and "게이트를 못 돌렸다" in 보, "게이트가 죽으면 막는다")
    G.게이트기, G.감사기 = 초록게이트, 죽는
    ok_, 보 = G.검사(뿌리)
    ok(not ok_ and "[검사 차단]" in 보, "검사가 죽으면 막는다")
    G.감사기, G.CI기 = 초록감사, 죽는
    ok_, 보 = G.검사(뿌리)
    ok(ok_ and "(경고)" in 보, "CI 조회가 죽으면 경고만(못잼)")
finally:
    G.게이트기 = G.감사기 = G.CI기 = None

print("\n== 배선 ==")
import subprocess  # noqa: E402
p = subprocess.run(["python3", "commit_guard.py", "--배선"], cwd=str(뿌리), capture_output=True, text=True, timeout=60)
ok(p.returncode == 0 and "임포트 됨" in p.stdout, "--배선 이 돈다(읽기 점검)")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
sync = _서버.split("def _git_sync_locked")[1].split("\ndef ")[0]
ok("commit_guard.검사(Path(REPO_DIR))" in sync and "gatekeeper.run_gates" not in sync,
   "**git_sync 가 게이트만 보지 않고 문지기(게이트·검사·CI)를 지난다**")
ok("[검사 차단]" in _서버 and "빨강 위에 자가 수정을 쌓지 않는다" in _서버, "프롬프트가 막혔을 때 그 검사부터 고치라고 시킨다")
_src = (뿌리 / "commit_guard.py").read_text(encoding="utf-8")
ok("run_gates(repo, 고치기=True)" in _src and "A.감사(repo, 커밋=False" in _src and "ci_watch.보기(repo)" in _src,
   "진짜 문 셋: gatekeeper 고치기 · audit 바뀐 파일 검사 · ci_watch")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"commit_guard.py"' in _wf, "commit_guard 가 배포 경로에")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("commit_guard: 통과 · 검사 빨강 · fail-closed · CI 빨강/못잼 · 게이트 · 죽어도 닫힘 · 배선 -- 통과")
