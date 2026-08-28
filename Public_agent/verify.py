"""
Loop.py의 self-correction 루프가 만든 후보를 diff_generator와는 "다른" 판단 주체로
재검토하는 절차. diff_generator(Gemini)가 스스로 "내 결과물이 objective를 달성했다"고
판단하게 두면 자기 확신 편향으로 실패해도 성공이라고 우길 위험이 크다 -- 그래서 생성자와
분리된 별도 호출(claude -p, 여기 세션과 같은 Claude Code CLI)로 한 번 더 검토시킨다.

fail-closed 원칙: claude CLI 호출 자체가 실패하면(토큰 소진, 명령 없음, 타임아웃 등)
"검증됐다"고 조용히 넘어가지 않고 무조건 미승인(approved=False) + 이유를 반환한다.
discord_bot_server.py 상단 주석에 있듯 Claude Code 토큰이 소진된 적이 있었다(2026-08-27) --
그 상태에서는 이 검증 절차 자체가 항상 미승인을 반환하게 되는데, 이건 "확인 안 된 걸 통과시키는
것"보다는 안전한 방향이라 의도적으로 그렇게 뒀다.
"""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent

VERIFY_PROMPT_TEMPLATE = """\
너는 아래 self-correction 루프가 만든 코드 변경을 검토하는 독립적인 검증자다.
이 변경을 만든 모델이 스스로 "성공"이라고 판단한 것과 별개로, 너는 회의적으로 재검토해야 한다.

# 목표(objective)
{objective}

# 적용된 diff
{diff}

# 자동 평가 결과 (서브프로세스 실행 로그)
{eval_feedback}

# 지시
1. diff가 실제로 objective를 달성하는지 확인하라.
2. diff가 목표와 무관한 부분을 건드리거나, 위험한 부작용(파일 삭제, 무한루프, 자격증명 노출 등)이
   없는지 확인하라.
3. 자동 평가 결과가 "성공"이라고 나왔어도 액면 그대로 믿지 말고 diff 내용 자체로 판단하라.

# 출력 형식 (반드시 첫 줄에 정확히 이 형식으로)
APPROVE
또는
REJECT: <구체적인 이유>
"""


def verify_candidate(objective: str, diff: str, eval_feedback: str, timeout: int = 120) -> "tuple[bool, str]":
    """diff_generator와 분리된 claude -p 호출로 후보를 재검토한다.
    반환: (승인 여부, 판단 근거 또는 실패 사유). claude 호출 자체가 안 되면 항상 (False, ...)."""
    prompt = VERIFY_PROMPT_TEMPLATE.format(objective=objective, diff=diff, eval_feedback=eval_feedback)
    session_id = f"verify-{uuid.uuid4().hex[:12]}"
    try:
        result = subprocess.run(
            ["claude", "-p", "--session-id", session_id, "--permission-mode", "bypassPermissions", prompt],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return False, "검증 실패(사람 확인 필요): claude CLI를 찾을 수 없다."
    except subprocess.TimeoutExpired:
        return False, f"검증 실패(사람 확인 필요): claude -p가 {timeout}초 안에 응답하지 않았다."

    output = (result.stdout or "").strip()
    if result.returncode != 0 or not output:
        err = (result.stderr or "").strip()
        return False, f"검증 실패(사람 확인 필요): claude -p 호출 오류 (토큰 소진 등 가능). {err[-500:]}"

    first_line = output.splitlines()[0].strip()
    if first_line.startswith("APPROVE"):
        return True, output
    if first_line.startswith("REJECT"):
        return False, output
    # 형식을 안 지켰으면 애매한 걸 통과시키지 않는다.
    return False, f"검증 실패(형식 위반, 사람 확인 필요): {output[:500]}"
