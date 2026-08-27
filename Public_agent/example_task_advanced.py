"""
example_task.py보다 한 단계 위 예시 -- 단일 함수/단일 hunk/1회 반복으로 끝나는
사례가 아니라, (1) 함수 두 개짜리 스켈레톤, (2) 여러 번의 diff에 걸쳐서만
드러나는 버그(멀티 digit run-length), (3) 이전 반복의 실패 피드백을 실제로
읽고 다른 diff를 내놓는 생성기를 갖춘 run-length 인코딩/디코딩 예제다.

_rule_based_diff_generator가 attempt 횟수에 따라 다른 목표 코드를 내놓는 걸로
"피드백을 보고 다음 시도를 바꾼다"를 흉내낸다 -- 실제 LLM을 그 자리에 넣으면
현재 코드+OBJECTIVE+feedback을 프롬프트로 주고 unified diff를 받는 것과 같은
자리다. 이 파일도 Loop.py/example_task.py와 마찬가지로 외부 API를 부르지 않는다.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from Loop import AutoRegressivePatcher, make_unified_diff


# 1. 스켈레톤 -- 함수 두 개, 둘 다 본문이 없다.
SKELETON_CODE = '''\
def run_length_encode(s):
    """문자열을 'a3b2' 같은 (문자+반복횟수) 시퀀스 문자열로 압축한다."""
    pass


def run_length_decode(s):
    """run_length_encode가 만든 문자열을 원래 문자열로 복원한다."""
    pass
'''

# 2. 추상화된 목표 -- 구현 방식이 아니라 라운드트립 조건 + 포맷 조건만 준다.
OBJECTIVE = (
    "모든 문자열 s에 대해 run_length_decode(run_length_encode(s)) == s여야 한다. "
    "인코딩 포맷은 각 반복 구간을 '문자 + 10진수 반복횟수'로 이어붙인 것이다. "
    "반복횟수는 10 이상(두 자리 이상)일 수 있다는 걸 잊지 마라."
)

# --- 이 아래는 diff_generator가 시도마다 내놓는 후보들이다 (LLM 대신 규칙 기반 예시) ---

# 시도 1: encode는 맞지만, decode가 반복횟수를 한 자리 숫자로만 읽는다
# (실무에서 자주 나오는 버그 -- "일단 짧은 예시로 테스트해서 통과한 줄 알았던" 케이스).
_ATTEMPT_1 = '''\
def run_length_encode(s):
    """문자열을 'a3b2' 같은 (문자+반복횟수) 시퀀스 문자열로 압축한다."""
    if not s:
        return ""
    parts = []
    prev, count = s[0], 1
    for ch in s[1:]:
        if ch == prev:
            count += 1
        else:
            parts.append(prev + str(count))
            prev, count = ch, 1
    parts.append(prev + str(count))
    return "".join(parts)


def run_length_decode(s):
    """run_length_encode가 만든 문자열을 원래 문자열로 복원한다."""
    result = []
    i = 0
    while i < len(s):
        ch = s[i]
        count = int(s[i + 1])  # 버그: 반복횟수가 두 자리 이상이면 잘못 읽는다
        result.append(ch * count)
        i += 2
    return "".join(result)
'''

# 시도 2: 피드백(멀티 digit에서 실패)을 반영해 정규식으로 숫자 전체를 읽는다.
_ATTEMPT_2 = '''\
import re


def run_length_encode(s):
    """문자열을 'a3b2' 같은 (문자+반복횟수) 시퀀스 문자열로 압축한다."""
    if not s:
        return ""
    parts = []
    prev, count = s[0], 1
    for ch in s[1:]:
        if ch == prev:
            count += 1
        else:
            parts.append(prev + str(count))
            prev, count = ch, 1
    parts.append(prev + str(count))
    return "".join(parts)


def run_length_decode(s):
    """run_length_encode가 만든 문자열을 원래 문자열로 복원한다."""
    result = []
    for ch, num in re.findall(r"([A-Za-z])(\\d+)", s):
        result.append(ch * int(num))
    return "".join(result)
'''


def _rule_based_diff_generator():
    """attempt 횟수에 따라 다른 목표 코드를 내놓는 클로저.

    실제 시도(_ATTEMPT_1)는 짧은 문자열에서는 통과하지만 두 자리 이상 반복횟수에서
    깨진다 -- verify()/evaluator가 그걸 잡아내서 실행 오류 피드백을 주면, 다음
    호출에서 _ATTEMPT_2로 넘어간다. LLM을 쓴다면 이 분기 대신 feedback 텍스트를
    프롬프트에 그대로 넣어 모델이 스스로 원인을 보고 고치게 하면 된다."""
    state = {"n": 0}

    def _generate(current_code: str, feedback: str) -> str:
        state["n"] += 1
        target = _ATTEMPT_1 if state["n"] == 1 else _ATTEMPT_2
        return make_unified_diff(current_code, target, "run_length.py")

    return _generate


# 3. 검증 코드 -- 루프가 끝난 뒤 독립적으로 재검증. 두 자리 이상 반복횟수 케이스를
#    반드시 포함시켜서, "짧은 예시만 통과하고 실제로는 안 되는" 상태를 걸러낸다.
_VERIFY_STRINGS = [
    "",
    "a",
    "aabbccddee",
    "a" * 12 + "b" * 3 + "c",          # 두 자리 반복횟수(12)가 섞여 있음
    "x" * 100,                         # 세 자리 반복횟수(100)
    "abcabcabc",
]


def verify(code: str) -> "tuple[bool, str]":
    # repr()로 넣은 문자열이 따옴표를 포함할 수 있어서 f-string 안에 그대로 또
    # 끼워넣으면 깨진다 -- assert 메시지는 문자열 리터럴을 중첩하지 않고 만든다.
    checks = "\n".join(
        f"r = run_length_decode(run_length_encode({s!r}))\n"
        f"assert r == {s!r}, 'mismatch for ' + repr({s!r}) + ': got ' + repr(r)"
        for s in _VERIFY_STRINGS
    )
    harness = code + "\n\n" + checks
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(harness)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [sys.executable, tmp_path], capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return True, f"{len(_VERIFY_STRINGS)}개 케이스(멀티 digit 포함) 전부 통과"
        return False, (result.stderr or result.stdout)[-2000:]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def run_demo() -> None:
    patcher = AutoRegressivePatcher(
        initial_code=SKELETON_CODE,
        objective=OBJECTIVE,
        diff_generator=_rule_based_diff_generator(),
        evaluator=lambda code: verify(code),  # 루프 내부 평가 == 최종 검증(예시 단순화용)
        max_iters=5,
    )
    final_code, iterations = patcher.run_self_correction_loop()

    print(f"--- {iterations}회 반복 후 결과 ---")
    for record in patcher.history:
        status = "성공" if record.success else "실패"
        first_line = (record.feedback or "").splitlines()[0] if record.feedback else ""
        print(f"  iter {record.iteration}: {status} ({first_line[:80]})")
    print()
    print(final_code)

    ok, msg = verify(final_code)
    print(f"--- 독립 재검증: {'통과' if ok else '실패'} ---")
    print(msg)


if __name__ == "__main__":
    run_demo()
