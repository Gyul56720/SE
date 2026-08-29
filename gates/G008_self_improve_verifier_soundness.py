"""
G008 -- 검증 함수가 "아무것도 검산하지 않고도 성공을 반환"할 수 있는 구조인가 (vacuous verify).

방지 대상은 특정 파일이나 특정 값이 아니라 오류의 '종류'다: 검증(verify/validate/check)
함수가 건너뛸 수 있는 루프를 돌면서, 루프가 전부 건너뛰어져 검산을 0회 하고도 성공을
반환할 수 있는 구조. 이러면 그 검증을 신뢰하는 상위 로직(예: 자가 수정 루프의 채택/롤백
판단)이 조용히 무력화된다. 검증은 언제나 fail-closed여야 한다 -- 검산한 게 없으면 통과가
아니라 실패여야 한다.

계기가 된 사고(2026-08-29): mathmetics/matrix_exponent/skeleton.py 의 verify_scheme 가
`for size in sizes: if size % b != 0: continue ... return True` 형태였고, 기본 sizes가
b로 나눠지지 않는 경우 루프가 전부 건너뛰어져 검산 0회로 통과했다. 하지만 이 게이트는 그
파일/그 b 값에 묶이지 않는다 -- 아래 '위험한 구조'는 어느 검증 함수에서든 잡는다.

무엇을 잡는가 (AST 구조 검사, 파일 무관):
  이름이 verify/validate/check 계열인 함수가 동시에 다음을 만족하면 위반:
    (1) 본문에 `continue` 로 반복을 건너뛸 수 있는 루프가 있다.
    (2) 그 루프 '뒤'(같은 블록 레벨)에서 참(True / (True, ...))을 반환한다
        -- 즉 루프를 다 건너뛰어도 성공 반환에 도달한다.
    (3) "검산을 한 번이라도 했는가"를 확인하는 가드가 없다
        -- 0과의 비교(== 0, > 0, < 1 ...)도, `if not <이름>:` 형태의 빈-검사 가드도 없다.
  고치는 법은 도메인과 무관하게 항상 같다: 실제 검산 횟수를 세고, 0이면 성공이 아니라
  실패를 반환하는 가드를 추가한다.

무엇을 안 잡는가: 가드가 있는 함수, 루프가 없는 함수, 성공 반환이 루프 '안'에만 있어
건너뛰면 자연히 falsy(None)로 떨어지는 함수. 파싱 불가한 파일은 다른 게이트(문법/임포트)의
몫이라 여기서는 건너뛴다.
"""
from __future__ import annotations

import ast

RULE_ID = "G008"
TITLE = "검증 함수가 검산 0회로 통과할 수 있는 구조가 아닌가 (vacuous verify 방지)"
ORIGIN = "2026-08-29 matrix_exponent vacuous-verify 안전장치 우회"
EVIDENCE = ""

# 검증기로 볼 함수 이름 신호 (소문자 부분일치).
_VERIFIER_NAME_HINTS = ("verify", "validate", "check", "is_valid", "assert_")


def _looks_like_verifier(name: str) -> bool:
    low = name.lower()
    return any(h in low for h in _VERIFIER_NAME_HINTS)


def _contains_continue(node: ast.AST) -> bool:
    """node 서브트리 안에, 더 안쪽의 다른 루프에 속하지 않는 continue 가 있는가.
    (안쪽 중첩 루프의 continue 는 그 루프 소관이므로 제외)"""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.Continue):
            return True
        if isinstance(child, (ast.For, ast.While, ast.AsyncFor)):
            continue  # 중첩 루프 내부는 그 루프가 책임진다.
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        if _contains_continue(child):
            return True
    return False


def _is_truthy_return(node: ast.AST) -> bool:
    """`return True` 또는 `return True, ...` / `return (True, ...)` 인가."""
    if not isinstance(node, ast.Return) or node.value is None:
        return False
    val = node.value
    if isinstance(val, ast.Tuple) and val.elts:
        val = val.elts[0]
    return isinstance(val, ast.Constant) and val.value is True


def _loop_body_node_ids(func: ast.AST) -> set:
    """함수 안 모든 루프의 '본문'(body)에 속한 노드 id 집합.
    루프 안의 스킵 조건(`if size % b != 0: continue`)에 든 상수 0을, 루프 '뒤'에 있는
    진짜 '검산했나' 가드와 구분하기 위해 쓴다 -- 유효한 가드는 루프 밖에 있어야 한다.
    (for-else 의 orelse 는 루프 완주 후 실행되므로 가드 위치로 인정 = 제외하지 않는다.)"""
    ids: set = set()
    for node in ast.walk(func):
        if isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
            for stmt in node.body:
                for sub in ast.walk(stmt):
                    ids.add(id(sub))
    return ids


def _has_zero_or_empty_guard(func: ast.AST) -> bool:
    """검산 횟수를 확인하는 가드가 '루프 밖'에 있는가.
    - 상수 0 과의 비교 (tested == 0, count > 0, n < 1 등)
    - len(...) 이 들어간 비교
    - `if not <이름>:` (빈 컬렉션/0 검사)
    루프 본문 안의 비교는 스킵 조건일 뿐 가드가 아니므로 제외한다."""
    inside_loop = _loop_body_node_ids(func)
    for node in ast.walk(func):
        if id(node) in inside_loop:
            continue
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            for op in operands:
                if isinstance(op, ast.Constant) and op.value == 0:
                    return True
                if isinstance(op, ast.Call) and isinstance(op.func, ast.Name) and op.func.id == "len":
                    return True
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            if isinstance(node.operand, ast.Name):
                return True
    return False


def _vacuous_success_after_loop(func) -> bool:
    """함수 본문 최상위에서, '건너뛸 수 있는 루프' 뒤에 참 반환이 오는가.
    (재귀적으로 if/try/with 블록 안까지 같은 규칙으로 살핀다.)"""

    def scan(body) -> bool:
        seen_skippable_loop = False
        for stmt in body:
            if isinstance(stmt, (ast.For, ast.While, ast.AsyncFor)) and _contains_continue(stmt):
                seen_skippable_loop = True
                continue
            if seen_skippable_loop and _is_truthy_return(stmt):
                return True
            # 중첩 블록도 같은 규칙으로 (루프 뒤 성공 반환이 if/with 안에 있을 수 있다).
            for inner in _child_blocks(stmt):
                if scan(inner):
                    return True
        return False

    return scan(func.body)


def _child_blocks(stmt):
    for attr in ("body", "orelse", "finalbody"):
        block = getattr(stmt, attr, None)
        if isinstance(block, list) and block:
            yield block


def check(ctx) -> "list[str]":
    violations: list[str] = []
    for path in ctx.tracked_files():
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue  # 문법/인코딩 문제는 다른 게이트 소관.
        rel = ctx.rel(path)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not _looks_like_verifier(node.name):
                continue
            if not _vacuous_success_after_loop(node):
                continue
            if _has_zero_or_empty_guard(node):
                continue
            violations.append(
                f"{rel}:{node.lineno} 검증 함수 '{node.name}()' 는 건너뛸 수 있는 루프를 "
                f"전부 건너뛰면 검산을 0회 하고도 성공(True)을 반환할 수 있다 (vacuous verify). "
                f"검산 횟수를 세고 0이면 실패를 반환하는 가드를 넣어라 -- 검산한 게 없으면 통과가 "
                f"아니라 실패여야 한다."
            )
    return violations
