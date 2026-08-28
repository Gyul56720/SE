"""G006 후보 -- 모듈 최상위에서 이름을 정의 전에 참조하지 않는가."""
from __future__ import annotations
import ast

RULE_ID = "G006"
TITLE = "데코레이터가 정의되지 않은 이름을 참조하지 않는가"
ORIGIN = "1a82685"
EVIDENCE = "public_agent_memory/20260828-201605_고친_코드는_push_전에_임포트부터_시켜봐라.md"


def check(ctx) -> "list[str]":
    """@client.event 처럼 데코레이터가 참조하는 최상위 이름이 그 줄보다 먼저 대입돼
    있는지 본다. 1a82685는 client 대입(114행)보다 @client.event(62행)가 앞서 있어
    임포트 시점에 NameError로 죽었다."""
    violations = []
    for path in ctx.python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        assigned: dict[str, int] = {}
        for stmt in tree.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                for a in stmt.names:
                    assigned.setdefault((a.asname or a.name).split(".")[0], stmt.lineno)
            elif isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        assigned.setdefault(t.id, stmt.lineno)
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for dec in stmt.decorator_list:
                    base = dec
                    while isinstance(base, (ast.Attribute, ast.Call)):
                        base = base.value if isinstance(base, ast.Attribute) else base.func
                    if isinstance(base, ast.Name) and base.id in {"property", "staticmethod", "classmethod"}:
                        continue
                    if isinstance(base, ast.Name) and assigned.get(base.id, 10**9) > dec.lineno:
                        violations.append(
                            f"{ctx.rel(path)}:{dec.lineno} 데코레이터가 '{base.id}'를 참조하는데 "
                            f"그 이름은 아직 정의되지 않았다 -- 임포트 시 NameError"
                        )
                assigned.setdefault(stmt.name, stmt.lineno)
    return violations
