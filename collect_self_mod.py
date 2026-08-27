import os
from pathlib import Path

SYSTEM_PROMPT = """너는 엄격한 논리와 단계별 검증을 거쳐 답변하는 고품질 추론 에이전트이다.
모든 수집 및 생성 과정에서 아래 규칙을 준수하라:
1. 단계별 분석 및 수집 계획 수립
2. 자기 검토를 통한 코드 무결성 검증
3. 명확한 self-modification 구현체 도출
"""

print(f"[테스팅 프롬프트 적용 완료]\n{SYSTEM_PROMPT}")

# self-modification 코드 4가지 수집 및 저장
snippets = [
    ("동적 모듈 리로드", "import importlib\ndef reload_module(mod): return importlib.reload(mod)"),
    ("소스 코드 파일 패치", "def patch_file(path, target, replacement): content = Path(path).read_text(); Path(path).write_text(content.replace(target, replacement))"),
    ("AST 노드 주입", "import ast\ndef inject_code(tree, node): tree.body.append(node); return tree"),
    ("Git 커밋 및 원격 푸시", "import subprocess\ndef git_commit_push(msg): subprocess.run(['git', 'commit', '-am', msg]); subprocess.run(['git', 'push'])")
]

os.makedirs("public_agent_memory", exist_ok=True)
for i, (topic, code) in enumerate(snippets, 1):
    filename = f"20260827-19000{i}_cot_self_mod_{i}.md"
    path = Path("public_agent_memory") / filename
    body = f"---\ntopic: {topic!r}\nsaved_at: 2026-08-27T19:00:00+00:00\nauthor_discord_id: cot-agent\nsource: testing-prompt-cot\n---\n\n# {topic}\n\n[CoT 및 Self-Correction 적용 수집 결과]\n\n```python\n{code}\n```\n"
    path.write_text(body, encoding="utf-8")
    print(f"Collected: {filename}")

