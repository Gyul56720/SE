import sys

with open("discord_bot_server.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "async with GIT_LOCK:" in line and "sync_note =" in lines[lines.index(line)+1]:
        continue # 이미 수정된 경우 건너뜀
        
    if "async with GIT_LOCK:" in line:
        new_lines.append("        # 게스트 보안 정책: 김희섭(249746307877437450) Git 제한\n")
        new_lines.append("        if str(message.author.id) == \"249746307877437450\":\n")
        new_lines.append("            sync_note = \"[보안 제한] 게스트 사용자의 Git 접근이 제한되었습니다.\"\n")
        new_lines.append("        else:\n")
        new_lines.append("            async with GIT_LOCK:\n")
        new_lines.append("                sync_note = await loop.run_in_executor(None, git_sync)\n")
    elif "sync_note = await loop.run_in_executor(None, git_sync)" in line and "async with GIT_LOCK:" not in lines[lines.index(line)-1]:
        continue # 기존의 단순 줄 삭제
    else:
        new_lines.append(line)

with open("discord_bot_server.py", "w") as f:
    f.writelines(new_lines)
