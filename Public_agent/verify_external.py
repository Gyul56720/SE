"""
외부(다른 모델/에이전트)가 만든 run_length_encode/decode 구현을 채점만 하는
독립 스크립트. example_task_advanced.py의 SKELETON_CODE/OBJECTIVE로 낸 문제에
대해 다른 모델이 내놓은 답을 검증할 때 쓴다.

이 파일은 정답을 만들지 않는다 -- verify()를 그대로 재사용해서 통과/실패만
판정한다 (검증자 역할과 풀이자 역할을 코드 수준에서 분리해두기 위함).

사용법:
    python3 verify_external.py <코드파일.py>
    또는
    python3 verify_external.py --stdin   (표준입력으로 코드를 받음)

<코드파일.py>에는 run_length_encode, run_length_decode 두 함수(필요하면 import도)만
있으면 된다. Public_agent/를 통해 write_public_answer로 저장된 파일 경로를 그대로
넘겨도 된다.
"""

from __future__ import annotations

import sys
from pathlib import Path

from example_task_advanced import OBJECTIVE, SKELETON_CODE, _VERIFY_STRINGS, verify


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--stdin":
        code = sys.stdin.read()
        label = "(stdin)"
    elif len(sys.argv) == 2:
        path = Path(sys.argv[1])
        if not path.is_file():
            print(f"파일을 찾을 수 없다: {path}", file=sys.stderr)
            return 2
        code = path.read_text(encoding="utf-8")
        label = str(path)
    else:
        print(__doc__)
        return 2

    print(f"=== 채점 대상: {label} ===")
    print(f"OBJECTIVE: {OBJECTIVE}")
    print(f"검증 케이스 수: {len(_VERIFY_STRINGS)} (멀티 digit 반복횟수 포함)")
    print()

    ok, msg = verify(code)
    print(f"결과: {'PASS' if ok else 'FAIL'}")
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
