"""`scripts/pr_merged.sh` 가 **머지된 것을 안 됐다고 답하지 않는가.**

이 장치의 유일한 위험이 잘못된 답이다. 특히 **거짓 양성**(안 된 것을 됐다고)은 장치가
있으나 마나가 아니라 **없느니만 못하다** -- 통과했다는 이유로 더 마음 놓고 명령을 준다.

첫 판이 실제로 거짓 음성을 냈다: 깃허브가 `"merged": true` 처럼 공백을 넣어 보내는데
`"merged":true` 로만 찾았다. 그래서 머지된 PR #66 을 "안 됐다" 고 답했다.

검사를 `.sh` 로 썼다가 `.py` 로 옮겼다 -- `scripts/tests.sh` 가 `tests/test_*.py` 만
돌리므로 `.sh` 검사는 **CI 에서 안 돈다.** 그 스크립트가 머리말에 적어 둔 그 함정이다.

    python3 tests/test_pr_merged.py
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "pr_merged.sh"
fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


def 돌린다(응답: str) -> int:
    """가짜 curl 을 앞세워 스크립트를 돌린다. 네트워크를 안 탄다."""
    d = Path(tempfile.mkdtemp())
    fake = d / "curl"
    fake.write_text("#!/usr/bin/env bash\ncat <<'JSON'\n" + 응답 + "\nJSON\n",
                    encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = dict(os.environ, PATH=f"{d}:{os.environ.get('PATH', '')}")
    return subprocess.run(["bash", str(SCRIPT), "1"], env=env,
                          capture_output=True).returncode


print("[머지 확인] **모르는 것을 됐다고 하지 않는다**")
ok(SCRIPT.is_file(), f"{SCRIPT.relative_to(ROOT)} 가 있다")
ok(돌린다('{"merged": true, "state": "closed"}') == 0,
   "공백이 든 `\"merged\": true` 를 머지됨으로 읽는다 -- **첫 판이 여기서 틀렸다**")
ok(돌린다('{"merged":true,"state":"closed"}') == 0, "공백 없는 꼴도 읽는다")
ok(돌린다('{"merged": false, "state": "open"}') == 1,
   "안 머지된 것은 1 -- 명령을 주지 마라")
ok(돌린다("") == 2, "조회 실패는 2 -- 모르는 것을 됐다고 하지 않는다")
ok(돌린다("<html>403 Forbidden</html>") == 2,
   "JSON 이 아니어도 됐다고 하지 않는다 -- 망 정책에 막히면 이 꼴이 온다")
ok(돌린다('{"title": "merged: true 라 적힌 제목", "merged": false, "state": "open"}') == 1,
   "제목에 든 글자에 속지 않는다 -- 칸 이름으로만 본다")

print()
print("[규칙] CLAUDE.md 에 순서가 적혀 있는가 -- 장치만 있고 규칙이 없으면 안 쓰인다")
_c = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
ok("머지하지 않은 PR 의 명령을 주지 마라" in _c, "규칙이 CLAUDE.md 에 있다")
ok("pr_merged.sh" in _c, "규칙이 이 장치를 가리킨다")
ok("#57" in _c and "#67" in _c,
   "언제 몇 번 그랬는지 실측이 적혀 있다 -- 근거 없는 금지는 지켜지지 않는다")

print()
if fails:
    print(f"머지 확인: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("머지 확인: 공백 · 실패 · 비JSON · 제목 미끼 · 규칙 -- 통과")
