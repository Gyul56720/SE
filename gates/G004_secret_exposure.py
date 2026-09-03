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

# _ECHO_SECRET(비밀값을 출력하는 코드)을 어디에 적용하는가. **셸/설정 파일에만** 본다.
#
# 이 검사는 이름에 TOKEN/SECRET/... 이 든 단어가 출력 구문에 보간되면 위반으로 잡는다.
# 이름만 보고는 "자격증명"과 "그냥 그 단어가 든 이름"을 못 가른다. 그런데 파이썬 쪽에서는
# token 이 LLM 단위를 뜻하는 표준 단어다 -- 실제로 걸린 것이 셋이었고 셋 다 자격증명이
# 아니었다: cache_creation_input_tokens(캐시 통계), approx_tokens(크기 추정),
# DISCORD_BOT_TOKEN(값이 아니라 라벨 문자열). 참 양성은 한 건도 없었다.
#
# 반면 이 게이트를 낳은 사고(1ea4304)는 run_bot_loop.sh 였다. 셸에는 토큰을 뜻하지 않는
# TOKEN 이란 이름을 쓸 일이 없고, `echo "$TOKEN"` 이 곧 유출 경로다.
#
# 실측으로 확인하고 좁혔다(2026-09-03):
#   _ECHO_SECRET 을 통째로 빼면      -> 1ea4304 에서 G004 가 발동하지 않는다 (RED 실패)
#   셸/설정 파일에만 적용하면        -> 1ea4304 RED 성립 · 현재 트리 GREEN · 오탐 0
# 즉 마찰만 사라지고 사고를 잡는 능력은 그대로다.
#
# 잃는 것: .py 가 자격증명을 print 하는 경우를 이 게이트는 더 이상 보지 않는다. 그 경로는
# secret_filter.py(stdout 필터), G011(셸 도구 반환값 마스킹), 그리고 알림 경로에 대해서는
# tests/test_overnight.py 의 "토큰이 로그에 새지 않는가" 회귀 검사가 덮는다.
# _LIVE_SECRET(자격증명 문자열이 커밋되는 것)은 범위를 줄이지 않았다 -- .env 가 커밋되는
# 것을 막는 쪽은 그대로 모든 파일을 본다.
_ECHO_SUFFIXES = {".sh", ".yml", ".yaml", ".service"}


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

        echo_hits = _ECHO_SECRET.finditer(text) if path.suffix in _ECHO_SUFFIXES else ()
        for m in echo_hits:
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
