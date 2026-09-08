"""`scripts/precheck.sh` 가 **반쯤 죽은 채 초록불을 내지 않는가.**

CI 를 안 기다리기로 했으므로 이 스크립트가 CI 자리에 선다. 그런데 이 스크립트는
`scripts/tests.sh` 의 종료 코드를 그대로 물려주므로, **스크립트 자신이 중간에
깨져도 초록불이 나온다.** 실측: 변수 이름을 한글(`남`)로 써서 bash 가 그 줄을
명령으로 읽었는데(`남: command not found`) 종료 코드는 0 이었다.

**잘못 답하는 장치는 없느니만 못하다** -- 통과했다는 이유로 더 마음 놓고 민다.

    python3 tests/test_precheck.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SH = ROOT / "scripts" / "precheck.sh"

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


print("[있나] CI 자리에 서는 스크립트다")
ok(SH.is_file(), f"{SH.relative_to(ROOT)} 가 있다")
_글 = SH.read_text(encoding="utf-8") if SH.is_file() else ""

print()
print("[문법] **반쯤 죽은 채 도는 스크립트가 가장 나쁘다**")
_문법 = subprocess.run(["bash", "-n", str(SH)], capture_output=True, text=True)
ok(_문법.returncode == 0, f"bash -n 을 통과한다 (얻은 값 {_문법.stderr.strip()[:80]!r})")

# 한글 변수 이름은 bash 가 못 받는다. 파일 전체에서 그 꼴을 막는다.
import re                                                             # noqa: E402
_한글변수 = re.compile(r"^\s*[가-힣][가-힣A-Za-z0-9_]*\s*=", re.M)
ok(not _한글변수.findall(_글),
   f"한글 변수 이름을 쓰지 않는다 (얻은 값 {_한글변수.findall(_글)})")

print()
print("[깨끗한 판] **작업 디렉터리를 보면 안 된다**")
# 이 스크립트가 있는 이유가 그것이다 -- `git add` 를 빠뜨린 파일을 잡는 것.
# 작업 디렉터리에서 돌면 그 파일이 보이므로 아무것도 못 잡는다.
ok("worktree add" in _글 and "HEAD" in _글,
   "HEAD 를 임시 워크트리로 꺼내 거기서 돈다")
ok("worktree remove" in _글, "끝나면 임시 워크트리를 치운다")
ok("scripts/tests.sh" in _글, "--전부 를 주면 CI 가 돌리던 것을 그대로 돌린다")

# **되돌이 방지.** 이 검사가 precheck 를 돌리고 precheck 가 이 검사를 돌린다.
# 막는 것이 없으면 워크트리를 파며 끝없이 내려간다 -- 실측으로 프로세스 넷이
# /tmp/tmp.*/ 에서 돌고 있었고, 겉으로는 그냥 **안 끝나는 검사**로만 보였다.
ok("PRECHECK_RUNNING" in _글, "되돌이 방지 빗장이 있다")

print()
print("[돌려 보기] 실제로 돌고 판정을 낸다")
_돌 = subprocess.run(["bash", str(SH)], capture_output=True, text=True, cwd=str(ROOT),
                    timeout=180)
_출 = _돌.stdout + _돌.stderr
ok("깨끗한 판에서 검사" in _출, "어느 판을 검사하는지 찍는다")
ok("command not found" not in _출 and "bad substitution" not in _출,
   f"스크립트 자신이 깨진 자국을 안 남긴다 (얻은 값 "
   f"{[l for l in _출.splitlines() if 'command not found' in l or 'bad substitution' in l][:2]})")
ok("검사" in _출, "검사 결과를 그대로 물려준다")

# 빗장이 서 있으면 아무것도 안 하고 빠진다 -- 그래야 안쪽에서 안 내려간다.
import os                                                             # noqa: E402
_안 = subprocess.run(["bash", str(SH)], capture_output=True, text=True, cwd=str(ROOT),
                    env={**os.environ, "PRECHECK_RUNNING": "1"}, timeout=60)
ok(_안.returncode == 0 and "되돌이" in _안.stdout,
   f"빗장이 서 있으면 바로 빠진다 (얻은 값 {_안.stdout.strip()[:40]!r})")

print()
if fails:
    print(f"밀기 전 검사: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("밀기 전 검사: 문법 · 한글 변수 · 깨끗한 판 · 뒤처리 · 실제 실행 -- 통과")
