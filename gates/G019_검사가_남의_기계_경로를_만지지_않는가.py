r"""
G019 -- 검사가 **그 기계에만 있는 절대경로**를 만지지 않는가.

**실측 2026-09-09:** 게이트 워크플로가 오래 빨간불이었는데 게이트 13개는 다 통과했다.
빨간 것은 검사 한 벌이었다.

    tests/test_law_hwp.py:77
    _기출 = ... if Path("/root/.claude/uploads").is_dir() else []
    PermissionError: [Errno 13] Permission denied: '/root/.claude/uploads'

에이전트 컨테이너에서는 그 경로가 **아예 없어서** `is_dir()` 이 False 를 돌려주고
초록이었다. CI 러너에서는 `/root` 가 **있는데 못 읽어서** 터졌다.

`pathlib` 이 삼키는 errno 는 `(2, 20, 9, 40)` 뿐이다 -- ENOENT · ENOTDIR · EBADF ·
ELOOP. **EACCES(13)는 안 삼킨다.** 그래서 "없으면 건너뛴다" 로 짠 것이 "못 읽으면
터진다" 가 된다.

## 무엇을 위반으로 보는가

`tests/` 의 파이썬 파일에 `/root/` · `/home/` · `/Users/` · `/mnt/` · `/media/` 로
시작하는 문자열이 있는 것. 사람마다 기계마다 다른 자리다.

## 무엇을 건너뛰나

  · `/tmp` `/dev` `/usr` `/bin` `/proc` `/etc` -- 어디에나 있고 읽을 수 있다
  · **주석과 독스트링** -- 거기 적힌 경로는 만지는 것이 아니라 설명하는 것이다
    (G016 이 같은 이유로 같은 가리개를 쓴다. 이 게이트가 제 검사 파일의 사고 기록을
    잡아서 알았다)
  · `# G019: 기계 경로` 를 그 줄이나 바로 위 주석에 달면 넘어간다.
    일부러 만져야 하는 자리가 있다면 **눈에 보이게** 고르게 한다

## 고치는 법

경로를 만지는 것 자체를 `try/except OSError` 로 감싸고, 건너뛸 때 **건너뛴다고
말한다.** 조용히 건너뛰면 그것도 가짜 green 이다.
"""
from __future__ import annotations

import ast
import io
import re
import tokenize

RULE_ID = "G019"
TITLE = "검사가 남의 기계 경로를 만지지 않는가"
ORIGIN = "게이트 워크플로 2026-09-09"
OPT_OUT = "G019: 기계 경로"

_BAD = re.compile(r"""['"](/(?:root|home|Users|mnt|media)/[^'"]*)['"]""")


def _masked(src: str) -> str:
    """주석과 독스트링을 지운 소스. G016 과 같은 가리개다."""
    out = list(src)
    lines = src.split("\n")
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln) + 1)

    def blank(a_ln, a_col, b_ln, b_col):
        a, b = starts[a_ln - 1] + a_col, starts[b_ln - 1] + b_col
        for i in range(max(0, a), min(len(out), b)):
            if out[i] != "\n":
                out[i] = " "

    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                blank(tok.start[0], tok.start[1], tok.end[0], tok.end[1])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return "".join(out)
    for node in ast.walk(tree):
        body = getattr(node, "body", None) if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) else None
        if not body:
            continue
        first = body[0]
        if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            blank(first.value.lineno, first.value.col_offset,
                  first.value.end_lineno, first.value.end_col_offset)
    return "".join(out)


def check(ctx) -> "list[str]":
    tests = ctx.repo / "tests"
    if not tests.is_dir():
        return []
    bad: list[str] = []
    for f in sorted(tests.glob("test_*.py")):
        try:
            raw = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lines = raw.split("\n")
        code = _masked(raw).split("\n")
        for i, line in enumerate(code):
            m = _BAD.search(line)
            if not m:
                continue
            around = "\n".join(lines[max(0, i - 3):i + 1])
            if OPT_OUT in around:
                continue
            bad.append(
                f"{ctx.rel(f)}:{i + 1} -- `{m.group(1)}` 은 그 기계에만 있는 자리다. "
                "여기서는 없어서 건너뛰고 CI 에서는 못 읽어서 터진다 "
                "(`is_dir()` 은 EACCES 를 안 삼킨다). "
                f"`try/except OSError` 로 감싸고 건너뛴다고 말해라 "
                f"(일부러면 `# {OPT_OUT}`)")
    return bad
