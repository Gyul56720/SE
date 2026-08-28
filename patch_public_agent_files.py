with open("public_agent_files.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# _current_author 임포트
with open("public_agent_files.py", "w", encoding="utf-8") as f:
    for line in lines:
        if 'from pathlib import Path' in line:
            f.write(line)
            f.write('from bot_tools import _current_author\n')
        elif 'def write_output(filename: str, content: str, author_id: str = "unknown") -> str:' in line:
            f.write(line)
            f.write('    if _current_author.get() == "249746307877437450":\n')
            f.write('        return "실패: 게스트는 파일을 쓸 수 없습니다."\n')
        else:
            f.write(line)
