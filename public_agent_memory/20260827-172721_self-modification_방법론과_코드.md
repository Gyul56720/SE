---
topic: 'self-modification 방법론과 코드'
saved_at: 2026-08-27T17:27:21.973952+00:00
author_discord_id: 732577811172163605
source: discord-public-channel-agent
---

# self-modification 방법론과 코드

self-modification(자기 수정)을 위한 방법론:
1. 에이전트가 실행 중인 환경(파일 시스템, git 저장소 등)에 대한 전체 셸 접근 권한(run_shell 등)을 확보한다.
2. 소스 코드 파일(파이썬 스크립트 등)을 직접 읽고 분석하는 도구를 제공한다.
3. 코드를 수정하는 패치 생성 및 적용 로직(파일 쓰기/덮어쓰기)을 구현한다.
4. 수정 후 자동 테스트(pytest 등)나 git diff를 통해 변경 사항을 검증하고, 문제가 없으면 git commit 및 push를 수행하여 반영한다.

실제 코드 예시 (agent_modifier.py 개념 예시):
```python
from pathlib import Path
import subprocess

def modify_code(file_path: str, new_content: str, commit_message: str) -> str:
    path = Path(file_path).resolve()
    path.write_text(new_content, encoding="utf-8")
    subprocess.run(["git", "add", str(path)], check=True)
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    subprocess.run(["git", "push"], check=True)
    return f"Successfully modified and pushed {file_path}"
```
