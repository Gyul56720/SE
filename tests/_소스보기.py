# -*- coding: utf-8 -*-
"""**산 주장만 남긴 소스.** docstring 과 주석을 지우고 나머지는 글자 그대로 둔다.

## 왜 있나

이 저장소는 고칠 때 **무엇이 틀렸었는지를 docstring 에 인용해 남긴다.** 그래서
"그 문장을 지웠나" 를 글자로 검사하면 사후 기록에 걸려 거짓 빨간불이 난다.

## 그런데 첫 판이 거짓 **초록**을 냈다

실측 2026-09-23. 첫 판은 이렇게 썼다.

    "\\n".join(tok.string for tok in tokenize... if tok.type != COMMENT)

토큰마다 줄을 바꿔 붙였으므로 `x.get("fail") or x.get("timeout")` 처럼
**여러 토큰에 걸친 글**은 원문에 있어도 안 맞는다. 그런데 이 도우미를 쓰는
검사는 대부분 "**없어야 한다**" 이다 -- 뭉갠 소스에서는 무엇이든 없다.

    소스를 뭉개는 도우미 + 없음을 보는 검사 = **언제나 통과**

`tests/test_스윕이름.py` 의 "지웠다" 여섯 줄이 그래서 통과하고 있었다.
검사하지 않은 초록불이 검사한 빨간불보다 나쁘다.

지금은 **줄과 칸을 그대로 두고** docstring 줄과 주석 자리만 지운다.
"""
from __future__ import annotations

import ast
import io
import tokenize


def 산주장(글: str) -> str:
    """docstring 과 주석만 지운 소스. 줄 수도 간격도 원문 그대로다."""
    줄 = 글.splitlines()
    for n in ast.walk(ast.parse(글)):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)) and ast.get_docstring(n, clean=False):
            d = n.body[0]
            for i in range(d.lineno - 1, d.end_lineno):
                줄[i] = ""
    남 = "\n".join(줄)
    칸 = 남.splitlines()
    for tok in tokenize.generate_tokens(io.StringIO(남).readline):
        if tok.type != tokenize.COMMENT:
            continue
        r, c = tok.start[0] - 1, tok.start[1]
        칸[r] = 칸[r][:c] + " " * (len(tok.string)) + 칸[r][c + len(tok.string):]
    return "\n".join(칸)


def 자기검사() -> None:
    """**이 도우미가 원문을 안 뭉개는지 스스로 확인한다.**"""
    본 = ('def f():\n'
         '    """설명 -- 옛 문장: 지운 주장.\n\n    두 줄짜리.\n    """\n'
         '    x = a.get("fail") or a.get("timeout")   # 옛 문장: 지운 주장\n'
         '    y = "지운 주장"\n')
    난 = 산주장(본)
    assert 'a.get("fail") or a.get("timeout")' in 난, "여러 토막 글이 살아 있어야 한다"
    assert 난.count("지운 주장") == 1, f"docstring·주석은 지운다 (남은 수 {난.count('지운 주장')})"
    assert 'y = "지운 주장"' in 난, "문자열 상수는 지우지 않는다 -- 그게 검사 대상이다"
    assert len(난.splitlines()) == len(본.splitlines()), "줄 수가 그대로여야 한다"
