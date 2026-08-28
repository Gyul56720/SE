"""
G004 -- 비밀값을 표준출력/로그/커밋으로 내보내지 마라.

사고: run_bot_loop.sh (2026-08-28). 토큰이 비어 있으면 저장소 전체를 grep해서 토큰처럼
생긴 문자열을 찾아 `echo "토큰을 발견했습니다: $TOKEN"` 으로 출력했다. .env는 grep 제외
대상이 아니었고, 이 스크립트의 stdout은 bot_execution.log로 리다이렉트됐으며, 그 로그는
git에 커밋되어 origin으로 push됐다. 즉 Discord 봇 토큰이 원격 저장소에 평문으로 나가는
경로가 열려 있었다.

이 게이트는 두 가지를 본다.
  1. 커밋될 파일에 실제 자격증명처럼 보이는 문자열이 들어있는가 (.env.example의 자리표시자,
     문서에 적힌 형식 설명은 제외).
  2. 비밀값을 담은 변수를 echo/print/log로 내보내는 코드 패턴이 있는가.
"""
from __future__ import annotations

import ast
import io
import re
import tokenize

RULE_ID = "G004"
TITLE = "자격증명이 커밋되거나 로그로 출력되지 않는가"
ORIGIN = "run_bot_loop.sh (2026-08-28)"
EVIDENCE = ""

# 비밀값을 담았을 이름 + 그걸 그대로 뱉는 출력 구문.
_ECHO_SECRET = re.compile(
    r"""(?:echo|print|printf|logger?\.\w+)\s*\(?[^\n]{0,80}?
        \$?\{?\b(?:\w*(?:TOKEN|SECRET|PASSWORD|APIKEY|API_KEY|CREDENTIAL)\w*)\b""",
    re.IGNORECASE | re.VERBOSE,
)
# 저장소를 훑어 자격증명을 찾아내는 패턴 (grep -r + 토큰 정규식).
_HARVEST = re.compile(r"grep\s+-[a-zA-Z]*r[a-zA-Z]*\b[^\n|]*\|[^\n]*(?:TOKEN|SECRET|KEY)", re.IGNORECASE)

# 실제 자격증명 형태. 자리표시자(your_..._here, <...>, xxx, 빈 값)는 제외한다.
_LIVE_SECRET = re.compile(
    r"""^\s*(?:export\s+)?(\w*(?:TOKEN|SECRET|PASSWORD|API_KEY)\w*)\s*[=:]\s*['"]?([A-Za-z0-9_\-\.]{16,})['"]?\s*$""",
    re.IGNORECASE | re.MULTILINE,
)
_PLACEHOLDER = re.compile(r"your_|_here|example|placeholder|xxx+|\.\.\.|changeme|<.*>", re.IGNORECASE)

_SKIP_DIRS = {".git", "node_modules", "venv", "__pycache__"}


def _code_only(text: str, suffix: str) -> str:
    """주석과 독스트링을 빈 줄로 지운 사본. 줄 번호는 보존한다.

    이게 없으면 이 파일 자신의 독스트링("... echo \"토큰을 발견했습니다: $TOKEN\" ...")과
    run_bot_loop.sh에 남긴 사고 경위 주석이 위반으로 잡힌다 -- 사고를 기록한 문장이 사고로
    오인되면 재발 방지 기록을 지우는 압력이 생긴다. 문자열 리터럴 자체는 지우지 않는다
    (print(f"token={TOKEN}") 같은 실제 노출이 문자열 안에 있기 때문)."""
    lines = text.splitlines()
    blanked = set()
    if suffix == ".py":
        try:
            for tok in tokenize.generate_tokens(io.StringIO(text).readline):
                if tok.type == tokenize.COMMENT:
                    blanked.add(tok.start[0])
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                body = getattr(node, "body", None)
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    doc = body[0]
                    blanked.update(range(doc.lineno, (doc.end_lineno or doc.lineno) + 1))
        except (SyntaxError, tokenize.TokenError, IndentationError):
            pass
    else:
        for i, line in enumerate(lines, 1):
            if line.lstrip().startswith("#"):
                blanked.add(i)
    return "\n".join("" if i in blanked else line for i, line in enumerate(lines, 1))
_SCAN_SUFFIXES = {".py", ".sh", ".yml", ".yaml", ".json", ".env", ".service", ".toml", ".cfg"}


def check(ctx) -> "list[str]":
    violations: list[str] = []
    for path in ctx.tracked_files():
        if path.suffix not in _SCAN_SUFFIXES:
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = ctx.rel(path)
        text = _code_only(text, path.suffix)

        if _HARVEST.search(text):
            violations.append(f"{rel}: 저장소를 grep해 자격증명을 수집하는 패턴 -- .env가 딸려 나온다")

        for m in _ECHO_SECRET.finditer(text):
            line_no = text[:m.start()].count("\n") + 1
            line = text.splitlines()[line_no - 1].strip()
            # 이름만 언급하는 안내 문구는 값을 노출하지 않는다.
            if "$" in line or "%s" in line or "{" in line or "+ " in line:
                violations.append(f"{rel}:{line_no}: 비밀값을 출력한다 -- {line[:100]}")

        for m in _LIVE_SECRET.finditer(text):
            name, value = m.group(1), m.group(2)
            if _PLACEHOLDER.search(value) or len(set(value)) < 8:
                continue
            line_no = text[:m.start()].count("\n") + 1
            violations.append(f"{rel}:{line_no}: 실제 자격증명으로 보이는 값이 커밋된다 ({name})")
    return violations
