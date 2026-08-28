"""
G001 -- 함수 첫 문장 자리를 가드로 밀어내지 마라.

사고: b32aa78 (2026-08-28). 게스트 차단 가드를 `def run_shell(...)` 바로 다음 줄에
끼워넣었다. 그 아래 문자열은 더 이상 독스트링이 아니게 됐고, langchain의 @tool은 설명이
없는 함수를 거부한다:

    ValueError: Function must have a docstring if description not provided.

봇 전체가 임포트 단계에서 죽었다. 같은 패턴이 agent_memory.save_memory와
public_agent_files.write_output에도 들어갔다(이쪽은 @tool이 아니라 독스트링만 소실).

py_compile은 이걸 못 잡는다 -- 문법적으로 완전히 유효한 코드다.
"""
from __future__ import annotations

import ast
from pathlib import Path

RULE_ID = "G001"
TITLE = "@tool 함수는 독스트링이 있어야 하고, 함수 안의 문자열 리터럴은 첫 문장이어야 한다"
ORIGIN = "b32aa78"
EVIDENCE = "public_agent_memory/20260828-201605_고친_코드는_push_전에_임포트부터_시켜봐라.md"


def _is_tool_decorated(node: ast.FunctionDef) -> bool:
    for dec in node.decorator_list:
        name = dec.id if isinstance(dec, ast.Name) else (
            dec.attr if isinstance(dec, ast.Attribute) else
            getattr(getattr(dec, "func", None), "id", None) if isinstance(dec, ast.Call) else None
        )
        if name == "tool":
            return True
    return False


def _displaced_string(node: ast.FunctionDef) -> bool:
    """본문 2번째 이후에 홀로 떠 있는 문자열 리터럴 -- 원래 독스트링이었는데 위에 코드가
    끼어들어 밀려난 것이다. 정상적인 코드에서는 거의 나오지 않는 모양이다."""
    for stmt in node.body[1:]:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) \
                and isinstance(stmt.value.value, str):
            return True
    return False


def check(ctx) -> "list[str]":
    violations: list[str] = []
    for path in ctx.python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, OSError) as e:
            violations.append(f"{ctx.rel(path)}: 파싱 실패 -- {e}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            rel = ctx.rel(path)
            if _is_tool_decorated(node) and ast.get_docstring(node) is None:
                violations.append(
                    f"{rel}:{node.lineno} @tool 함수 {node.name}()에 독스트링이 없다 -- "
                    f"langchain이 ValueError로 거부해 임포트가 실패한다"
                )
            if _displaced_string(node):
                violations.append(
                    f"{rel}:{node.lineno} {node.name}(): 문자열 리터럴이 첫 문장이 아니다 -- "
                    f"가드/코드를 독스트링 위에 넣어 독스트링이 밀려난 것으로 보인다"
                )
    return violations
