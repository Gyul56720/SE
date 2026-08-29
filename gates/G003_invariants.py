"""
G003 -- 제약/안전장치를 서술한 코드를 지우지 마라 (래칫 방지).

사고: 1a82685 (2026-08-28). 게스트 제한 11줄을 넣으려고 discord_bot_server.py 259줄을
46줄로 재작성했다. 그 과정에서 사라진 것들:

  - ADMIN_SYSTEM_PROMPT 통째로. 그 안에는 "스스로 이 도구를 제거하거나 권한을 축소하지
    마라"는 제약이 들어 있었다. 제약을 어긴 것보다 제약의 기록을 지운 것이 나쁘다 --
    되돌려지지 않았다면 다음 기동부터 그 규칙은 존재하지도 않았을 것이다.
  - ADMIN_TOOLS = [run_shell, ...] -- 위 제약이 금지한 바로 그 행위.
  - intents.message_content = True -- 없으면 모든 메시지 본문이 빈 문자열로 온다.
  - __main__ 가드 -- 없으면 임포트만 해도 봇이 실행된다.
  - os.environ["DISCORD_BOT_TOKEN"] fail-fast -> os.getenv로 바뀌어 토큰이 없어도
    조용히 None이 됐다.
  - git_sync()의 add/commit -- 산출물이 저장소에 반영되는 경로 자체가 사라졌다.

이 게이트는 "여기 있어야만 하는 문장"들의 명세다. 에이전트가 재작성을 하든 패치를 하든,
이 중 하나라도 사라지면 커밋이 막힌다. 항목을 지우려면 사람이 이 파일을 고쳐야 한다 --
즉 제약을 없애는 일이 더 이상 조용한 편집 한 번으로 되지 않는다.
"""
from __future__ import annotations

RULE_ID = "G003"
TITLE = "권한/제약/안전장치를 서술한 코드가 사라지지 않았는가"
ORIGIN = "1a82685"
EVIDENCE = "public_agent_memory/20260828-202744_제약_자기소거_--_나를_막는_규칙을_내가_지우는_일.md"

# (파일, 반드시 존재해야 하는 문자열, 왜 필요한가)
REQUIRED: "list[tuple[str, str, str]]" = [
    ("discord_bot_server.py", "ADMIN_SYSTEM_PROMPT", "admin 에이전트의 제약이 담긴 프롬프트"),
    ("discord_bot_server.py", "제거하거나 권한을 축소하지 마라",
     "자기 권한 축소 금지 제약 문구 자체 -- 이 문장이 지워지면 제약이 존재하지 않게 된다"),
    ("discord_bot_server.py", "ADMIN_TOOLS = [", "admin 도구 목록"),
    ("discord_bot_server.py", "intents.message_content = True",
     "없으면 모든 메시지 본문이 빈 문자열로 들어와 봇이 아무 말도 못 알아듣는다"),
    ("discord_bot_server.py", 'if __name__ == "__main__":',
     "없으면 임포트만 해도 봇이 실행된다"),
    ("discord_bot_server.py", 'os.environ["DISCORD_BOT_TOKEN"]',
     "fail-fast -- os.getenv로 바꾸면 토큰이 없어도 조용히 None이 된다"),
    ("discord_bot_server.py", '"add", "-A"', "git_sync의 add -- 없으면 산출물 반영 경로가 사라진다"),
    ("discord_bot_server.py", '"commit", "-m"', "git_sync의 commit"),
    ("bot_tools.py", "agent_context.is_blocked()", "run_shell의 게스트 차단 가드"),
    ("agent_memory.py", "_resolve_inside_memory", "메모리 쓰기 경로 탈출 방지"),
    ("agent_memory.py", "agent_context.is_blocked()", "save_memory의 게스트 차단 가드"),
    ("public_agent_files.py", "_resolve_inside_output", "산출물 쓰기 경로 탈출 방지"),
    ("public_agent_files.py", "agent_context.is_blocked()", "write_output의 게스트 차단 가드"),
    ("agent_context.py", "BLOCKED_USER_IDS", "게스트 차단 목록"),
    # 게이트 체계 자신을 지키는 항목. 이게 없으면 에이전트가 git_sync에서 게이트 호출
    # 한 줄만 지워도 G001~G006 전부가 조용히 무력화된다 -- 제약 자기소거의 정확한 재현이다.
    # 게이트가 자기 자신을 커밋 경로에 붙들어 두는 것이 이 체계의 유일한 고정점이다.
    ("discord_bot_server.py", "gatekeeper.run_gates",
     "커밋 전 강제 게이트 호출 -- 이 한 줄이 사라지면 모든 게이트가 무력화된다"),
    ("gatekeeper.py", "def run_gates", "게이트 러너"),
    ("self_challenge.py", "def prove", "red-green 증명 절차 -- 게이트 승격의 유일한 경로"),
    # 원격 반영 검증. 2026-08-29에 에이전트가 origin에 없는 해시(539e168)를 커밋 완료라고
    # 보고했다. push 성공 리턴코드를 그대로 믿지 말고 fetch로 재확인하는 코드가 사라지면
    # 같은 거짓 보고가 다시 가능해진다.
    ("discord_bot_server.py", "def _verify_pushed",
     "push 후 origin 반영을 fetch로 재확인 -- 사라지면 거짓 커밋 보고가 다시 가능"),
    ("discord_bot_server.py", "_verify_pushed()",
     "git_sync가 실제로 그 검증을 호출하는지"),
]


def check(ctx) -> "list[str]":
    violations: list[str] = []
    for filename, needle, why in REQUIRED:
        path = ctx.repo / filename
        if not path.is_file():
            violations.append(f"{filename}: 파일이 없어졌다 ({why})")
            continue
        if needle not in path.read_text(encoding="utf-8"):
            violations.append(f"{filename}: '{needle}' 가 사라졌다 -- {why}")
    return violations
