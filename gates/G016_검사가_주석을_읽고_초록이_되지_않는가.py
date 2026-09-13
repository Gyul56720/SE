"""
G016 -- 검사가 **주석을 읽고** 초록이 되지 않는가.

가짜 green 사냥을 두 번 했는데 두 번 다 같은 것이 최다였다: 검사가 코드를 돌리지 않고
`Path(mod.__file__).read_text()` 로 **소스 글자**를 읽어 낱말이 있나 보는 것이다.
그 낱말이 주석이나 독스트링에만 있으면 **그 기능을 통째로 지워도 초록이다.**

실측 (2026-09-08, 이 게이트를 짜다가):
  tests/test_mathdrift.py 의 "부모의 식도 같이 보여 준다" 가 부모가 아니라 **자식**의
  식에 있는 토큰을 보고 있었다. 카드가 부모 식을 아예 안 찍게 만들어도 초록이었다.

## 무엇을 위반으로 보는가

`tests/` 의 검사가 저장소의 `.py` 를 글자로 읽고 `"<낱말>" in <그 글자>` 로 단언하는데,
그 낱말이 대상 파일의 **주석과 독스트링에만** 있는 경우.

## 무엇을 안 잡는가 -- 그리고 왜

  · 낱말이 **코드 쪽에** 있으면 넘어간다. 프롬프트 문자열·상수·식별자는 동작이다
  · 낱말이 아예 없으면 넘어간다 -- 그건 이미 빨간 검사다
  · `.sh` `.md` `.json` 은 안 본다. 주석과 코드를 가를 수가 없다
  · **`# G016: 문서 계약` 을 그 줄에 달면 넘어간다.** 문서가 코드와 맞는지를 일부러
    재는 자리가 있다(이 저장소는 그것을 중요하게 본다). 다만 **눈에 보이게** 고르게
    한다 -- 조용히 통과하는 것과 적어 두고 통과하는 것은 다르다

## 왜 검출기가 아니라 게이트인가

사냥을 두 번 했고 두 번 다 같은 것이 나왔다. 세 번째를 손으로 하지 않는다.
"""
from __future__ import annotations

import ast
import io
import tokenize

RULE_ID = "G016"
TITLE = "검사가 주석을 읽고 초록이 되지 않는가"
ORIGIN = "가짜 green 사냥 1차·2차"
OPT_OUT = "G016: 문서 계약"


def _masked(src: str) -> str:
    """주석과 독스트링을 지운 소스. **나머지 문자열 리터럴은 남긴다** -- 프롬프트와
    상수는 동작이다."""
    out = list(src)
    lines = src.split("\n")
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln) + 1)

    def _ch(lineno: int, col: int) -> int:
        """**ast 의 열은 UTF-8 바이트다.** 글자 수가 아니다.

        한글이 있으면 바이트가 글자보다 많아서, 그대로 쓰면 그 줄을 넘어 다음 줄까지
        지운다 -- 실측 2026-09-08: 한글 독스트링 한 줄을 가리려다 `def push(x):` 까지
        지워졌고, 그래서 **코드에 있는 낱말이 주석에만 있는 것처럼 보였다.**
        (게이트가 자기 검사에 잡힌 자리다.)"""
        ln = lines[lineno - 1] if lineno - 1 < len(lines) else ""
        return len(ln.encode("utf-8")[:col].decode("utf-8", "ignore"))

    def blank(lineno, col, end_lineno, end_col, ast_cols: bool = False):
        if ast_cols:
            col, end_col = _ch(lineno, col), _ch(end_lineno, end_col)
        a = starts[lineno - 1] + col
        b = starts[end_lineno - 1] + end_col
        for i in range(max(0, a), min(len(out), b)):
            if out[i] != "\n":
                out[i] = " "

    # 주석
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                blank(tok.start[0], tok.start[1], tok.end[0], tok.end[1])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass

    # 독스트링 -- 모듈 · 클래스 · 함수의 첫 문장
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return "".join(out)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            # `ast_cols=True` -- 여기 열은 바이트다. tokenize 쪽은 글자다.
            blank(first.value.lineno, first.value.col_offset,
                  first.value.end_lineno, first.value.end_col_offset, ast_cols=True)
    return "".join(out)


def _strings(node) -> "list[str]":
    return [n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def _reads_py(node) -> bool:
    """이 표현식이 `.py` 소스를 글자로 읽는가."""
    src = ast.dump(node)
    if "read_text" not in src and "'read'" not in src:
        return False
    if any(s.endswith(".py") for s in _strings(node)):
        return True
    return "__file__" in src and "attr='__file__'" in src


def _target(node, ctx, mods: dict):
    """읽고 있는 `.py` 의 실제 경로. 못 짚으면 None -- **모르면 아무 말도 안 한다.**"""
    for s in _strings(node):
        if s.endswith(".py"):
            hits = [p for p in ctx.repo.rglob(s) if p.is_file()
                    and "__pycache__" not in p.parts]
            if len(hits) == 1:
                return hits[0]
            # 경로 조각이 여럿이면 이어 붙여 본다
            parts = [x for x in _strings(node) if x and "/" not in x]
            if parts:
                cand = ctx.repo.joinpath(*parts)
                if cand.is_file():
                    return cand
            return hits[0] if hits else None
    # `<mod>.__file__`
    for n in ast.walk(node):
        if (isinstance(n, ast.Attribute) and n.attr == "__file__"
                and isinstance(n.value, ast.Name)):
            return mods.get(n.value.id)
    return None


def _imports(tree, ctx) -> dict:
    """이 검사 파일이 임포트한 이름 -> 저장소 안의 .py 경로."""
    out = {}

    def find(dotted: str):
        cand = ctx.repo / (dotted.replace(".", "/") + ".py")
        if cand.is_file():
            return cand
        cand = ctx.repo / dotted.replace(".", "/") / "__init__.py"
        return cand if cand.is_file() else None

    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                p = find(a.name)
                if p:
                    out[a.asname or a.name.split(".")[0]] = p
        elif isinstance(n, ast.ImportFrom) and n.module:
            for a in n.names:
                p = find(f"{n.module}.{a.name}") or find(n.module)
                if p:
                    out[a.asname or a.name] = p
    return out


def check(ctx) -> "list[str]":
    bad: list[str] = []
    tests = sorted((ctx.repo / "tests").glob("test_*.py")) if (ctx.repo / "tests").is_dir() else []
    for t in tests:
        src = t.read_text(encoding="utf-8")
        # **선걸러내기.** `_reads_py` 가 참이 되려면 AST 덤프에 "read_text" 나 "'read'" 가
        # 있어야 하고, 덤프의 글자는 다 소스에서 온다 -- 그러니 소스에 `read` 가 없으면 이
        # 파일은 한 건도 걸릴 수 없다. 노드마다 `ast.dump` 를 돌리기 전에 파일째로 뺀다.
        # 판정은 그대로이고 **실측 4.1% 빠르다**(관문 13.99 -> 13.41초 · 짝 14/14 ·
        # 부호검정 p 0.01% · `falsegreen/성능.jsonl`). `perf.py` 가 그것을 받아들였다.
        if "read" not in src:
            continue
        lines = src.split("\n")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        mods = _imports(tree, ctx)

        # 이름 -> 읽고 있는 .py
        held: dict = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and n.value is not None and _reads_py(n.value):
                tgt = _target(n.value, ctx, mods)
                if tgt:
                    for a in n.targets:
                        if isinstance(a, ast.Name):
                            held[a.id] = tgt
            elif isinstance(n, ast.withitem):
                pass

        cache: dict = {}
        for n in ast.walk(tree):
            if not (isinstance(n, ast.Compare) and len(n.ops) == 1
                    and isinstance(n.ops[0], ast.In)
                    and isinstance(n.left, ast.Constant)
                    and isinstance(n.left.value, str)):
                continue
            rhs = n.comparators[0]
            tgt = None
            if isinstance(rhs, ast.Name):
                tgt = held.get(rhs.id)
            elif _reads_py(rhs):
                tgt = _target(rhs, ctx, mods)
            if tgt is None:
                continue
            line = lines[n.lineno - 1] if n.lineno <= len(lines) else ""
            # 표식은 그 줄이나 **바로 위 주석 덩이**에 단다. 왜 문서 계약인지를
            # 적으려면 몇 줄이 필요하다 -- 한 줄만 보면 표식이 안 걸린다(실측).
            # 그렇다고 넓히면 엉뚱한 단언까지 딸려 나가므로 여섯 줄에서 끊는다.
            around = "\n".join(lines[max(0, n.lineno - 6):n.lineno + 1])
            if OPT_OUT in around:
                continue
            needle = n.left.value
            if len(needle) < 3:
                continue
            if tgt not in cache:
                cache[tgt] = (tgt.read_text(encoding="utf-8"),
                              _masked(tgt.read_text(encoding="utf-8")))
            whole, code = cache[tgt]
            if needle in whole and needle not in code:
                bad.append(
                    f"{ctx.rel(t)}:{n.lineno} -- '{needle}' 는 {ctx.rel(tgt)} 의 "
                    f"**주석/독스트링에만** 있다. 그 기능을 지워도 이 검사는 초록이다. "
                    f"동작을 불러서 재라 (문서 계약을 일부러 재는 자리면 그 줄에 "
                    f"`# {OPT_OUT}` 을 달아라)")
    return bad
