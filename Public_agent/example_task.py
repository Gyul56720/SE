"""
Loop.py의 AutoRegressivePatcher를 실제로 돌려보는 예시 하나.

3가지를 한 세트로 묶었다:
1. SKELETON_CODE  -- 미완성/버그가 있는 원본 코드 (RuleConfig 원칙 2: 이 원형은
   유지되어야 한다. diff_generator는 이 구조를 갈아엎지 않고 빈 로직만 채워야 한다).
2. OBJECTIVE      -- "무엇을 구현해야 하는가"를 구체적 함수 시그니처가 아니라
   추상화된 목표(입출력 조건)로만 서술한다 -- 구현 디테일은 diff_generator가 정한다.
3. verify(code)   -- 완성된 코드가 목표를 만족하는지 나중에 독립적으로 재검증하는
   함수. evaluator(내부 루프가 반복마다 쓰는 성공 판정)와 별개로 존재해서,
   루프가 끝난 뒤 최종 산출물을 한 번 더 확인할 수 있다 -- 루프 evaluator를
   신뢰하지 않고 이중 검증하는 셈이다.

diff_generator 자체(실제로 diff 텍스트를 만드는 부분, 예: LLM 호출)는 이 파일에
없다 -- Loop.py와 마찬가지로 여기서도 외부 API를 부르지 않는다. 대신
run_demo()에 규칙 기반 예시 생성기를 하나 끼워 넣어서 전체 파이프라인이
end-to-end로 동작하는 걸 보여준다.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from Loop import AutoRegressivePatcher, make_unified_diff


# 1. 스켈레톤 -- clamp(x, lo, hi)의 뼈대만 있고 본문이 비어 있다 (항상 None을 반환).
SKELETON_CODE = '''\
def clamp(x, lo, hi):
    """x를 [lo, hi] 범위로 자른다."""
    pass
'''

# 2. 추상화된 목표 -- 함수를 어떻게 짜라고 하지 않고, 만족해야 할 입출력 조건만 준다.
OBJECTIVE = (
    "clamp(x, lo, hi)는 x가 lo보다 작으면 lo를, hi보다 크면 hi를, 그 사이면 x를 "
    "그대로 반환해야 한다. lo > hi인 입력은 고려하지 않는다."
)

# 3. 검증 코드 -- 루프가 끝난 뒤에도 독립적으로 다시 돌려볼 수 있는 재검증 함수.
_VERIFY_CASES = [
    ((5, 0, 10), 5),
    ((-3, 0, 10), 0),
    ((15, 0, 10), 10),
    ((0, 0, 10), 0),
    ((10, 0, 10), 10),
    ((2.5, -1.0, 1.0), 1.0),
]


def verify(code: str) -> "tuple[bool, str]":
    """완성된 clamp 구현을 별도 프로세스에서 실제로 호출해보고 기대값과 비교한다.
    Loop 내부 evaluator와 완전히 독립된 코드 경로라서, 루프의 성공 판정 자체가
    틀렸을 가능성까지 걸러낸다."""
    harness = code + "\n\n" + "\n".join(
        f"assert clamp{args!r} == {expected!r}, "
        f"f'clamp{args!r} == {{clamp{args!r}}}, expected {expected!r}'"
        for args, expected in _VERIFY_CASES
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(harness)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [sys.executable, tmp_path], capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return True, "모든 검증 케이스 통과"
        return False, (result.stderr or result.stdout)[-2000:]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _rule_based_diff_generator(current_code: str, feedback: str) -> str:
    """LLM 없이 규칙으로만 diff를 만드는 예시 생성기 -- OBJECTIVE를 그대로 구현한
    코드로 한 번에 고친다. 실제 사용에서는 이 함수 자리에 LLM 호출을 넣고,
    current_code + OBJECTIVE + feedback을 프롬프트로 줘서 unified diff를 받으면 된다."""
    fixed = '''\
def clamp(x, lo, hi):
    """x를 [lo, hi] 범위로 자른다."""
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x
'''
    return make_unified_diff(current_code, fixed, "example_task_target.py")


def run_demo() -> None:
    patcher = AutoRegressivePatcher(
        initial_code=SKELETON_CODE,
        objective=OBJECTIVE,
        diff_generator=_rule_based_diff_generator,
        max_iters=5,
    )
    final_code, iterations = patcher.run_self_correction_loop()

    print(f"--- {iterations}회 반복 후 결과 ---")
    print(final_code)

    ok, msg = verify(final_code)
    print(f"--- 독립 재검증: {'통과' if ok else '실패'} ---")
    print(msg)


if __name__ == "__main__":
    run_demo()
