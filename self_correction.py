"""
Discord 채팅 한 번으로 트리거되는 자동 diff 자가 수정 루프.

Public_agent/Loop.py의 AutoRegressivePatcher를 실제 Gemini 모델(diff_generator)에
연결한다. 사용자가 다시 채팅을 치지 않아도, 이 모듈의 run() 호출 하나 안에서
(LLM 호출 -> diff 적용 -> 서브프로세스 실행/검증 -> 실패 시 피드백을 다시 LLM에
줌) 을 성공하거나 max_iters에 도달할 때까지 반복한다.

보안 경고 (사용자가 위험을 인지하고 명시적으로 public 채널 연결을 요청함,
2026-08-27): 화이트리스트 없는 채널에서 익명 사용자가 지시한 코드를 서버에서
실제로 실행시킬 수 있게 된다. run_shell을 없앤 것과 본질적으로 같은 위험이라,
아래 제약을 코드로 강제한다.

- max_iters/총 시간/입력 길이 모두 사용자가 뭘 요청하든 하드 상한을 넘지 못한다.
- 후보 코드는 이 프로세스 안에서 exec()하지 않고 별도 python3 서브프로세스에서
  돌린다 (Loop.py의 default_subprocess_evaluator와 같은 원칙).
- 서브프로세스는 CPU 시간/메모리(RLIMIT)를 제한해서, 무한루프나 메모리 폭탄을
  돌려도 타임아웃/OOM으로 죽는다 -- 네트워크 접근이나 파일시스템 접근 자체를
  막는 진짜 샌드박스(컨테이너, seccomp 등)는 아니다. 이 서버의 나머지 부분과
  같은 OS 사용자 권한으로 돈다는 걸 감안하고 써야 한다.
"""

from __future__ import annotations

import re
import resource
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from Public_agent.Loop import AutoRegressivePatcher

MAX_ITERS_CAP = 10
MAX_CODE_CHARS = 8000
MAX_TEST_CHARS = 4000
MAX_TOTAL_SECONDS = 120
PER_RUN_TIMEOUT = 8
CPU_SECONDS_LIMIT = 5
MEMORY_BYTES_LIMIT = 256 * 1024 * 1024  # 256MB

_DIFF_FENCE_RE = re.compile(r"```(?:diff|patch)?\n(.*?)```", re.DOTALL)


def _extract_diff(text: str) -> str:
    """모델 응답에서 코드펜스가 있으면 안쪽만, 없으면 전체를 diff로 취급한다."""
    match = _DIFF_FENCE_RE.search(text)
    return (match.group(1) if match else text).strip()


def _limit_resources() -> None:
    """서브프로세스 preexec_fn -- CPU 시간과 가상메모리를 제한한다 (Linux 전용)."""
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS_LIMIT, CPU_SECONDS_LIMIT))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES_LIMIT, MEMORY_BYTES_LIMIT))


def _make_test_evaluator(test_code: str) -> Callable[[str], "tuple[bool, str]"]:
    def _evaluate(candidate_code: str) -> "tuple[bool, str]":
        harness = candidate_code + "\n\n" + test_code
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(harness)
            tmp_path = f.name
        try:
            result = subprocess.run(
                ["python3", tmp_path],
                capture_output=True,
                text=True,
                timeout=PER_RUN_TIMEOUT,
                preexec_fn=_limit_resources,
            )
            if result.returncode == 0:
                return True, ""
            return False, (result.stderr or result.stdout)[-1500:]
        except subprocess.TimeoutExpired:
            return False, f"실행 시간 초과({PER_RUN_TIMEOUT}초) -- 무한루프이거나 너무 느리다."
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    return _evaluate


def _make_llm_diff_generator(llm, objective: str, prior_lessons: str) -> Callable[[str, str], str]:
    prompt_template = (
        "너는 파이썬 코드를 unified diff(git diff -u) 형식으로만 고치는 도구다. "
        "설명 없이 diff 텍스트만 출력하라. 코드펜스(```diff ... ```)로 감싸도 된다.\n\n"
        "[목표]\n{objective}\n\n"
        "[과거 유사 시도에서 얻은 교훈 -- 참고만 하고 맹신하지 마라]\n{prior_lessons}\n\n"
        "[현재 코드]\n```python\n{code}\n```\n\n"
        "[직전 시도 피드백]\n{feedback}\n\n"
        "이 코드를 목표를 만족하도록 고치는 unified diff만 출력하라. "
        "형식은 '--- a/code' / '+++ b/code' / '@@ -시작,길이 +시작,길이 @@' 헤더를 포함해야 한다."
    )

    def _generate(code: str, feedback: str) -> str:
        prompt = prompt_template.format(
            objective=objective, prior_lessons=prior_lessons or "(없음)", code=code, feedback=feedback,
        )
        response = llm.invoke(prompt)
        text = response.content if isinstance(response.content, str) else str(response.content)
        return _extract_diff(text)

    return _generate


def summarize_history(objective: str, iterations: int, success: bool, history: list) -> str:
    """history(IterationRecord 리스트)를 memory 노트에 남길 수 있는 짧은 교훈으로 압축한다.
    실패한 시도의 피드백 첫 줄만 남겨서, 다음에 비슷한 objective가 들어왔을 때
    diff_generator 프롬프트에 '전에 이런 이유로 몇 번 실패했다'를 끼워넣을 수 있게 한다."""
    lines = [f"목표: {objective}", f"결과: {'성공' if success else '실패'} ({iterations}회 반복)"]
    for record in history:
        if record.success:
            continue
        first_line = (record.feedback or "").splitlines()[0] if record.feedback else ""
        lines.append(f"- iter {record.iteration} 실패: {first_line[:200]}")
    return "\n".join(lines)[:3800]


def run(
    llm,
    objective: str,
    skeleton_code: str,
    test_code: str,
    max_iters: int = MAX_ITERS_CAP,
    prior_lessons: str = "",
) -> "tuple[str, int, bool, list]":
    """objective를 만족할 때까지(또는 상한까지) diff 자가 수정을 자동 반복한다.
    prior_lessons는 과거 비슷한 objective에서 겪은 실패 요약(search_memory 결과 등)을
    diff_generator 프롬프트에 참고 자료로 끼워넣는다 -- 모델 가중치가 바뀌는 학습은
    아니지만, 이전 시행착오를 프롬프트로 재사용해서 같은 실수를 반복하지 않게 한다.

    반환: (최종 코드, 반복 횟수, 성공 여부, IterationRecord 리스트)
    """
    skeleton_code = (skeleton_code or "")[:MAX_CODE_CHARS]
    test_code = (test_code or "")[:MAX_TEST_CHARS]
    max_iters = max(1, min(int(max_iters), MAX_ITERS_CAP))

    patcher = AutoRegressivePatcher(
        initial_code=skeleton_code,
        objective=objective,
        diff_generator=_make_llm_diff_generator(llm, objective, prior_lessons),
        evaluator=_make_test_evaluator(test_code),
        max_iters=max_iters,
        max_seconds=MAX_TOTAL_SECONDS,
    )
    final_code, iterations = patcher.run_self_correction_loop()
    success = bool(patcher.history) and patcher.history[-1].success
    return final_code, iterations, success, patcher.history
