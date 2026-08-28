import sys

# 게스트 ID
GUEST_ID = "249746307877437450"

with open("bot_tools.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# 1. run_shell 수정: GUEST_ID가 호출 시도시 차단
# 메타데이터 파악을 위해 _current_author를 가져와 체크한다.
with open("bot_tools.py", "w", encoding="utf-8") as f:
    for line in lines:
        if 'def run_shell(command: str) -> str:' in line:
            f.write(line)
            f.write('    if _current_author.get() == "249746307877437450":\n')
            f.write('        return "실패: 게스트는 run_shell을 사용할 수 없습니다."\n')
        else:
            f.write(line)
