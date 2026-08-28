"""
G002 -- 로컬 모듈 사이에 top-level 임포트 순환을 만들지 마라.

사고: b32aa78 (2026-08-28). agent_memory.py와 public_agent_files.py가 bot_tools에서
_current_author를 top-level로 임포트했다. 그런데 bot_tools는 그 두 모듈을 자기보다 위에서
임포트하고 _current_author는 그 아래에 정의돼 있었다:

    ImportError: cannot import name '_current_author' from partially initialized
    module 'bot_tools' (most likely due to a circular import)

순환이 있어도 "이름이 이미 정의된 뒤"라면 우연히 통과할 수 있다 -- 즉 순환 자체가
시한폭탄이다. 그래서 실패를 기다리지 않고 순환의 존재 자체를 막는다.

정적 검사(AST)로 잡는 이유: 동적 임포트 검사는 langchain/discord 같은 서드파티가 설치된
환경에서만 돌아간다. 순환은 서드파티 없이도 확정적으로 판정할 수 있으므로 정적으로 본다.
서드파티가 있는 환경에서는 G006이 실제 임포트까지 돌린다.
"""
from __future__ import annotations

import ast

RULE_ID = "G002"
TITLE = "로컬 모듈 간 top-level 임포트 순환 금지"
ORIGIN = "b32aa78"
EVIDENCE = "public_agent_memory/20260828-201605_고친_코드는_push_전에_임포트부터_시켜봐라.md"


def _toplevel_local_imports(tree: ast.Module, local_names: "set[str]") -> "set[str]":
    """모듈 최상위(함수/클래스 안이 아닌)에서 임포트하는 로컬 모듈 이름들.
    함수 안의 지연 임포트는 순환을 만들지 않으므로 세지 않는다."""
    found: set[str] = set()
    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                root = alias.name.split(".")[0]
                if root in local_names:
                    found.add(root)
        elif isinstance(stmt, ast.ImportFrom) and stmt.level == 0 and stmt.module:
            root = stmt.module.split(".")[0]
            if root in local_names:
                found.add(root)
    return found


def check(ctx) -> "list[str]":
    files = {p.stem: p for p in ctx.python_files() if p.parent == ctx.repo}
    graph: dict[str, set[str]] = {}
    for name, path in files.items():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        graph[name] = _toplevel_local_imports(tree, set(files))

    violations: list[str] = []
    seen_cycles: set[frozenset] = set()

    def walk(node: str, stack: "list[str]") -> None:
        for nxt in sorted(graph.get(node, ())):
            if nxt in stack:
                cycle = stack[stack.index(nxt):] + [nxt]
                key = frozenset(cycle)
                if key not in seen_cycles:
                    seen_cycles.add(key)
                    violations.append(
                        "top-level 임포트 순환: " + " -> ".join(f"{m}.py" for m in cycle)
                        + " (한쪽을 함수 안 지연 임포트로 바꾸거나, 공유 대상을 "
                          "agent_context.py처럼 의존성 없는 모듈로 분리하라)"
                    )
            elif len(stack) < 12:
                walk(nxt, stack + [nxt])

    for name in sorted(graph):
        walk(name, [name])
    return violations
