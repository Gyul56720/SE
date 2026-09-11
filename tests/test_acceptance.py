"""eval/acceptance.py(에이전트 인수 검사)를 끝까지 돌려 끝값으로 붙든다 -- precheck 가 매번 문다.

실행: python3 tests/test_acceptance.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
p = subprocess.run(["python3", "eval/acceptance.py"], cwd=str(뿌리), capture_output=True, text=True, timeout=900)
print(p.stdout[-3000:])
if p.returncode != 0:
    print(p.stderr[-1500:])
    print("인수 검사 실패 -- 위 표의 ✗ 를 보라")
    raise SystemExit(1)
print("acceptance: 인수 검사 전부 통과")
