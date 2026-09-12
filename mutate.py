"""거짓 초록 사냥 -- **조용히 틀린 값**으로 바꿔도 초록인 검사를 찾는다. LLM 호출 0회.

사용자(2026-09-12): "거짓 초록이 문제인데, 그냥 거짓 초록을 24시간 동안 보는 기능을 만들어."

## 절제로는 왜 모자라나

`rehearsal.절제검사` 는 함수 몸통을 `raise NotImplementedError` 로 바꾼다. 그러면 **그 함수를
부르기만 하는 검사도** 예외가 터져 빨개진다. 즉 절제가 증명하는 것은

    검사의 초록이 그 함수의 **존재**에 매여 있다

뿐이고, **결과를 본다**는 것이 아니다. `f()` 만 부르고 아무것도 단언하지 않는 검사, 또는
`assert f() is not None` 같은 검사는 절제를 통과한다. 그 자리가 남은 거짓 초록이다.

## 변형은 무엇을 증명하나

터뜨리지 않는다. **조용히 틀린 값**을 돌려주게 바꾼다 -- `return None` · `return 0` · 비교를
뒤집고 · 불리언을 반전하고 · 상수를 흔든다. 그래도 검사가 초록이면

    그 검사는 그 함수를 부르지만 **보지 않는다** -- 증명된 거짓 초록이다

살아남은 변형 하나하나가 "코드가 이렇게 틀려도 아무도 모른다" 는 **실측 증거**다. 원장에 남는다.

    python3 mutate.py --시한 86400                 # 24시간 사냥 (기본 1시간)
    python3 mutate.py --파일 improve/run.py        # 한 파일만
    python3 mutate.py --보고                       # 원장 요약 (사냥 안 함)

## 판정 정의 (사용자, 2026-09-12)

  원본이 검사를 통과한 뒤, 각 대상 함수의 **의미를 보존하지 않는** 유한한 독립 변형 집합을
  만들고, 각 변형을 **같은 검사·같은 환경**에서 돌려, 원본과 구별되어 실패해야 할 모든
  **비등가** 변형 중 하나라도 통과하면 그 Green 을 거짓 Green 으로 판정한다.
  **동등 변형(equivalent mutant)은 별도의 의미·불변식 판정으로 제외한다.**

그래서 네 갈래로 가른다 -- 살아남은 것을 다 거짓 초록이라 부르면 그 판정이 거짓이 된다.

  죽음        어떤 검사가 빨개졌다            -> 검사가 본다
  **거짓초록**  변형된 줄이 **실행되는데** 살았다 -> 검사가 부르지만 보지 않는다 (증거)
  덮이지않음   그 줄이 한 번도 실행되지 않았다   -> 단언의 약함이 아니라 **덮임의 구멍**이다
  동등제외     바이트코드가 원본과 같다         -> 의미가 보존됐다. 아무것도 증명하지 못한다

동등 판정은 TCE(Trivial Compiler Equivalence)다 -- 두 글을 컴파일해 줄번호를 지운 바이트코드가
같으면 의미가 같다(건전한 한쪽 방향이다. 다르면 '다르다' 고 단정하지 않는다).
실행 여부는 검사를 한 번 `sys.settrace` 로 돌려 그 파일의 실행된 줄을 모아 둔다(파일마다 한 번).

## 남는 한계 -- 정직하게

변형 집합은 유한하고, 고르지 않은 변형은 말하지 않는다. TCE 는 동등을 **일부만** 잡는다
(의미는 같은데 바이트코드가 다른 것은 못 잡아 거짓초록으로 과보고될 수 있다 -- 그래서 보고에
`동등의심` 을 따로 둔다). 다만 방향이 반대다: **살아남은 비등가 변형은 반례다** -- 의심이 아니라 증거다.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
원장상대 = "logs/거짓초록.jsonl"
기본시한초 = 3600
검사시한초 = 120           # 한 검사에 이만큼. 변형은 무한 루프를 만들 수 있다 -- 시한이 곧 판정이다
# **바이트코드 캐시를 끈다.** 실측 2026-09-12: `a + b` -> `a - b` 는 **길이가 같다.** 같은 초에 쓰면
# 파이썬의 .pyc 유효성 검사(원본 mtime + 크기)가 통과해 **변형된 바이트코드가 복원 뒤에도 다시 쓰인다.**
# 그러면 복원 재실행이 빨개져 진짜 kill 이 FALSE_RED 로 분류된다 -- 거짓 Red 의 구조적 원인이다.
# -B 와 PYTHONDONTWRITEBYTECODE 로 캐시를 아예 안 만들면 그 원인이 사라진다.
파이썬 = ["python3", "-B"]
맑은환경 = {"PYTHONDONTWRITEBYTECODE": "1"}
한함수검사수 = 3           # 한 함수마다 이만큼의 검사까지 돌린다(가장 가까운 것부터)


def _원장(repo: Path) -> Path:
    p = repo / 원장상대
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def 적기(repo: Path, 줄: dict) -> None:
    """덧붙이기만. 판정의 역사는 지우지 않는다."""
    줄 = {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **줄}
    with _원장(repo).open("a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")


def 원장읽기(repo=None) -> "list[dict]":
    p = _원장(Path(repo or REPO))
    if not p.is_file():
        return []
    out = []
    for 줄 in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if 줄.strip():
            try:
                out.append(json.loads(줄))
            except ValueError:
                continue
    return out


# ------------------------------------------------------------------ 판정 어휘 (Green-Red System)
# 사용자(2026-09-12)의 정의. PASS/FAIL 한 비트로 뭉개면 두 오판이 숨는다.
#
#   FG = {(P,T,m,E) | T(P,E)=PASS ∧ m(P)≢P ∧ T(m(P),E)=PASS}        거짓 Green
#   FR = {(P,T,m,E) | T(P,E)=PASS ∧ T(m(P),E)=FAIL ∧ Cause(FAIL)≠m}  거짓 Red
#   GR = (FG ∪ FR)^c                                                유효 판정 영역
#
# FR 이 실재한다는 것을 오늘 실측했다 -- rehearsal.절제검사 가 절제 판에 `.py` 만 옮겨서,
# 패치가 같이 만든 `plan/할일.jsonl` 이 없어 검사가 빨개졌다. 절제와 무관한 실패를 "검사가
# 기능을 본다" 로 읽어 PR #218 을 통과시켰다. **FR 은 FG 를 낳는다** -- 그래서 둘을 같이 막는다.
# ## 왜 이 프로토콜에서는 거짓 Red 가 **나올 수 없나**
#
# 귀속을 글자(예외 이름)로 짐작하지 않고 **복원 재실행**으로 한다. 한 변형의 판정은 언제나
# 같은 샌드박스에서 세 번 돌린 결과다.
#
#   (1) 바탕:   변형 없는 판  -> PASS 여야 한다            (아니면 INVALID_BASELINE)
#   (2) 변형:   한 줄만 다른 판
#   (3) 되돌림: 변형을 뺀 판   -> PASS 여야 한다
#
# (1)과 (3)이 PASS 이고 (2)가 FAIL 이면, 세 실행의 **유일한 차이가 그 한 줄**이다. 그러므로
# Cause(FAIL) = m 이 성립한다 -- 짐작이 아니라 차감이다. (3)이 FAIL 이면 무엇이 원인인지 모르므로
# FALSE_RED 로 적고 **잡힌 것으로 세지 않는다.** 그래서 거짓 Red 가 VALID_RED 로 보고될 길이 없다.
#
# 거짓 Green 쪽은 '없을 수 없다' 고 말하지 않는다(동등성은 결정 불가능하다). 대신 **고른 변형
# 집합 M 안에서는 완전**하게 만든다: 동등이 확실한 것(TCE)만 빼고, 모르는 것은 전부 '죽어야 할
# 변형' 으로 센다. 살아남으면 그것은 반례다. 남는 위험은 "M 밖의 변형" 하나로 이름이 붙는다.
# 변형 하나의 결과는 **다섯 갈래**다(사용자 2026-09-12). 시스템 판정(아래 일곱)과 층이 다르다.
잡힘 = "Killed"            # 유효한 변형이 검사에 잡혔고, 그 실패의 원인이 변형이다
살아남음 = "Survived"       # 비동등 변형인데 검사가 통과했다 -- False Green 후보
동등 = "Equivalent"        # 의미가 그대로다 -- 평가에서 뺀다
거짓빨강결과 = "FalseRed"    # 실패했지만 원인이 변형이 아니다
못쓸 = "Invalid"           # 변형 자체가 잘못됐거나(문법·임포트) 프로토콜이 깨졌다(Δ·E)
다섯갈래 = (잡힘, 살아남음, 동등, 거짓빨강결과, 못쓸)

유효초록 = "VALID_GREEN"
유효빨강 = "VALID_RED"
거짓초록 = "FALSE_GREEN"
거짓빨강 = "FALSE_RED"
못쓸바탕 = "INVALID_BASELINE"
못쓸변형 = "INVALID_MUTATION"
동등변형 = "EQUIVALENT_MUTANT"
바탕터짐 = "INFRA_FAILURE"

# Cause(FAIL) ≠ m 의 낌새. 변형이 낸 실패가 아니라 **환경·딸림 파일·도구**가 낸 실패다.
외부실패꼴 = (
    ("ModuleNotFoundError", "dependency/import failure"),
    ("ImportError", "dependency/import failure"),
    ("No module named", "dependency/import failure"),
    ("FileNotFoundError", "fixture/config missing"),
    ("No such file or directory", "fixture/config missing"),
    ("IsADirectoryError", "fixture/config missing"),
    ("NotADirectoryError", "working-directory 오류"),
    ("PermissionError", "permission 오류"),
    ("Errno 13", "permission 오류"),
    ("JSONDecodeError", "fixture(JSONL/JSON) 깨짐"),
    ("Expecting value: line", "fixture(JSONL/JSON) 깨짐"),
    ("OSError: [Errno 28]", "환경 초기화 실패(디스크)"),
    ("error: cannot run", "infrastructure/tool failure"),
    ("collected 0 items", "테스트 수집 실패"),
    ("ERROR collecting", "테스트 수집 실패"),
    ("ModuleNotFoundError: No module named 'pytest'", "infrastructure/tool failure"),
)


def 실패원인(출력: str) -> "tuple[bool, str]":
    """(변형과 무관한가, 까닭). 무관하면 그 FAIL 은 FALSE_RED 다 -- 변형이 검출된 것이 아니다.

    낌새만으로 단정하지 않는다. 부르는 쪽이 **변형을 뺀 같은 판**을 한 번 더 돌려 같은 실패가
    나오는지로 확인한다(그것이 Cause 의 실측이다). 여기는 그 까닭에 이름을 붙이는 일만 한다."""
    글 = 출력 or ""
    for 낌새, 까닭 in 외부실패꼴:
        if 낌새 in 글:
            return True, 까닭
    if "AssertionError" in 글 or "assert" in 글:
        return False, "assertion (mutation 이 잡혔다)"
    if "TypeError" in 글 or "ValueError" in 글 or "AttributeError" in 글 or "ZeroDivisionError" in 글:
        return False, "mutation 이 만든 값/형 오류"
    if "Timeout" in 글 or "timed out" in 글:
        return False, "시한 초과(변형이 멈추지 않게 만들었을 수 있다)"
    return False, "분류 못 함 -- 변형 탓으로 본다(보수적)"


def 단일변형인가(원글: str, 새글: str, 예상줄들=None) -> "tuple[bool, list]":
    """Δ(P, m(P)) = {m} 인가. (그런가, 바뀐 줄 목록).

    **한 줄인지**가 아니라 **그 변형이 선언한 자취와 같은지**를 본다 -- 가지 맞바꾸기(branch swap)처럼
    한 변형이 여러 줄을 건드리는 것도 있다. 선언한 자취 밖이 바뀌었으면 그 결과로 Green/Red 를
    판정하지 않는다(INVALID_MUTATION): 무엇이 잡힌 것인지 알 수 없다.
    `예상줄들` 이 정수면 그 한 줄로 본다(옛 호출 꼴)."""
    a, b = 원글.splitlines(), 새글.splitlines()
    if len(a) != len(b):
        return False, [f"줄 수가 다르다 ({len(a)} -> {len(b)})"]
    다른 = {i + 1 for i, (x, y) in enumerate(zip(a, b)) if x != y}
    if not 다른:
        return False, ["바뀐 줄이 없다"]
    if 예상줄들 is None:
        return (len(다른) == 1), [f"{sorted(다른)}"]
    예상 = {int(예상줄들)} if isinstance(예상줄들, int) else set(int(x) for x in 예상줄들)
    if 다른 == 예상:
        return True, [f"{sorted(다른)}"]
    return False, [f"선언한 자취 {sorted(예상)} 와 실제 {sorted(다른)} 가 다르다"]


def 변형유효한가(새글: str, rel: str = "") -> "tuple[bool, str]":
    """m ∈ M_valid(P) 인가 -- **변형 자체가 말이 되나.**

    문법이 깨진 변형, 임포트를 부수는 변형, 실행 불가능한 변형이 낸 FAIL 을 `Killed` 로 세면
    "검사가 의미 변화를 잡았다" 가 거짓이 된다(사용자 2026-09-12). 그런 것은 Invalid 다.
    컴파일이 판정이다 -- 문법과 들여쓰기를 파이썬 자신이 본다."""
    try:
        compile(새글, rel or "<변형>", "exec")
    except SyntaxError as e:
        return False, f"문법이 깨졌다: {type(e).__name__}: {str(e)[:90]}"
    except ValueError as e:
        return False, f"컴파일 못 함: {type(e).__name__}: {str(e)[:90]}"
    return True, ""


def 환경보존됐나(판: Path, rel: str) -> "tuple[bool, list]":
    """P = (C, F) 에서 **F 가 그대로인가.** 변형 판에서 바뀐 파일이 대상 하나뿐이어야 한다.

    비-파이썬 상태(JSONL · YAML · fixture · schema · config · test data)가 같이 움직이면 그 FAIL 은
    변형 탓이 아니다 -- 오늘 절제검사가 정확히 그래서 FALSE_RED 를 냈다."""
    r = subprocess.run(["git", "-C", str(판), "status", "--porcelain", "-z", "--untracked-files=all"],
                       capture_output=True, text=True)
    바뀐 = []
    항목 = [x for x in r.stdout.split("\0") if x]
    i = 0
    while i < len(항목):
        줄 = 항목[i]; i += 1
        코드글, 경로 = 줄[:2], 줄[3:]
        if "R" in 코드글 or "C" in 코드글:
            i += 1
        if 경로.startswith(".se_"):                 # 덮임 추적기 같은 내 연장은 뺀다
            continue
        바뀐.append(경로)
    남 = [x for x in 바뀐 if x != rel]
    return (not 남), 남


# ------------------------------------------------------------------ 변형 만들기
def _자리(src: str) -> dict:
    """{이름: 함수노드} -- 꼭대기 함수와 클래스 안 메서드. 함수 안 함수는 부모에 든다."""
    try:
        나무 = ast.parse(src)
    except SyntaxError:
        return {}
    out = {}
    for 노드 in 나무.body:
        if isinstance(노드, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[노드.name] = 노드
        elif isinstance(노드, ast.ClassDef):
            for 안 in 노드.body:
                if isinstance(안, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[f"{노드.name}.{안.name}"] = 안
    return out


def _줄바꾸기(src: str, 줄번호: int, 새줄: str) -> str:
    줄들 = src.splitlines(keepends=True)
    if not (1 <= 줄번호 <= len(줄들)):
        return src
    옛 = 줄들[줄번호 - 1]
    들여 = 옛[:len(옛) - len(옛.lstrip())]
    줄들[줄번호 - 1] = 들여 + 새줄.strip() + ("\n" if 옛.endswith("\n") else "")
    return "".join(줄들)


def _블록(src: str, 줄부터: int, 줄까지: int) -> str:
    return "".join(src.splitlines(keepends=True)[줄부터 - 1:줄까지])


def 변형들(src: str, 이름: str, 상한: int = 24) -> "list[tuple[str, str, str, frozenset]]":
    """그 함수의 **조용한** 변형들 [(연산자, 설명, 새 소스, 예상 자취)]. 터뜨리지 않고 틀린 값을 돌려준다.

    사용자(2026-09-12)가 정한 최소 범위 {Return, Constant, Comparison, Boolean, Branch} 를 다 채운다.

      return_none    `return x` -> `return None`
      return_zero    `return x` -> `return 0`
      return_minus1  `return x` -> `return -1`
      const_return   계산 결과를 상수로 -> `return 1`
      const_num      숫자 상수 흔들기 (0->1 · 1->0 · n->n+1)
      cmp_negate     `==`<->`!=` · `<`<->`>=` · `>`<->`<=` · `<=`<->`>` · `>=`<->`<`   (부정 짝)
      cmp_boundary   `<`<->`<=` · `>`<->`>=`                                           (경계 짝, off-by-one)
      bool_negate    `A` -> `not A`
      bool_swap      `A and B` <-> `A or B` · True<->False
      branch_drop    `if A` -> `if False`   (그 가지를 없앤다)
      branch_force   `if A` -> `if True`    (그 가지를 늘 돈다)
      branch_swap    `if A: X else: Y` -> `if A: Y else: X`
      arith_swap     `+`<->`-` · `*`<->`/`   (범위 밖이지만 길이가 같은 변형이라 캐시 회귀를 붙든다)

    의존성·자원 변형은 **연산자에 넣지 않는다** -- 그것은 환경 불변식(E(P)=E(Pm)) 축에서 거짓 Red 를
    잡는 일이다(사용자 지시). 여기 연산자는 모두 의미만 바꾼다."""
    자리 = _자리(src).get(이름)
    if 자리 is None or not hasattr(ast, "unparse"):
        return []
    out: "list[tuple[str, str, str, frozenset]]" = []
    본것: set = set()

    def 더하기(연산자: str, 줄: int, 옛글: str, 새글자: str) -> None:
        표 = (연산자, 줄, 새글자)
        if 표 in 본것 or len(out) >= 상한:
            return
        줄들 = src.splitlines()
        if not (0 < 줄 <= len(줄들)):
            return
        원본줄 = 줄들[줄 - 1]
        if 옛글 and 옛글 not in 원본줄:
            return
        새줄 = 원본줄.replace(옛글, 새글자, 1) if 옛글 else 새글자
        if 새줄.strip() == 원본줄.strip():
            return
        본것.add(표)
        out.append((연산자, f"{줄}줄 `{(옛글 or 원본줄.strip())[:26]}` -> `{새글자[:26]}`",
                    _줄바꾸기(src, 줄, 새줄), frozenset({줄})))

    부정짝 = {ast.Eq: ("==", "!="), ast.NotEq: ("!=", "=="), ast.Lt: ("<", ">="), ast.GtE: (">=", "<"),
           ast.Gt: (">", "<="), ast.LtE: ("<=", ">"), ast.Is: ("is", "is not"), ast.IsNot: ("is not", "is"),
           ast.In: ("in", "not in"), ast.NotIn: ("not in", "in")}
    경계짝 = {ast.Lt: ("<", "<="), ast.LtE: ("<=", "<"), ast.Gt: (">", ">="), ast.GtE: (">=", ">")}
    for 노드 in ast.walk(자리):
        줄 = getattr(노드, "lineno", 0)
        if not 줄:
            continue
        if isinstance(노드, ast.Return) and 노드.value is not None:
            글 = ast.unparse(노드.value)
            for 연산자, 값 in (("return_none", "None"), ("return_zero", "0"), ("return_minus1", "-1")):
                if 글.strip() != 값:
                    더하기(연산자, 줄, f"return {글}", f"return {값}")
            if 글.strip() not in ("1", "None", "0", "-1"):      # 계산 결과를 상수로 -- Constant-Return
                더하기("const_return", 줄, f"return {글}", "return 1")
        elif isinstance(노드, ast.Compare) and len(노드.ops) == 1:
            원래 = ast.unparse(노드)
            왼, 오 = ast.unparse(노드.left), ast.unparse(노드.comparators[0])
            꼴 = type(노드.ops[0])
            if 꼴 in 부정짝:
                더하기("cmp_negate", 줄, 원래, f"{왼} {부정짝[꼴][1]} {오}")
            if 꼴 in 경계짝:
                더하기("cmp_boundary", 줄, 원래, f"{왼} {경계짝[꼴][1]} {오}")
        elif isinstance(노드, ast.BinOp) and type(노드.op) in (ast.Add, ast.Sub, ast.Mult, ast.Div):
            # 사양의 최소 범위 밖이지만 둔다 -- `a + b` -> `a - b` 는 **길이가 같아서** 낡은 .pyc 로
            # 거짓 Red 가 나던 자리를 붙드는 회귀 표본이다(실측 2026-09-12).
            뒤 = {ast.Add: "-", ast.Sub: "+", ast.Mult: "/", ast.Div: "*"}[type(노드.op)]
            원래 = ast.unparse(노드)
            더하기("arith_swap", 줄, 원래, f"{ast.unparse(노드.left)} {뒤} {ast.unparse(노드.right)}")
        elif isinstance(노드, ast.BoolOp) and len(노드.values) == 2:
            원래 = ast.unparse(노드)
            왼, 오 = ast.unparse(노드.values[0]), ast.unparse(노드.values[1])
            더하기("bool_swap", 줄, 원래, f"{왼} {'or' if isinstance(노드.op, ast.And) else 'and'} {오}")
        elif isinstance(노드, ast.If):
            조건 = ast.unparse(노드.test)
            더하기("bool_negate", 줄, 조건, f"not ({조건})")
            더하기("branch_drop", 줄, 조건, "False")
            더하기("branch_force", 줄, 조건, "True")
            # Branch-Swap -- 한 변형이 여러 줄을 건드린다. 자취를 **선언**해서 단일성 검사를 지난다.
            가지 = 노드.body
            딴가지 = 노드.orelse
            if (가지 and 딴가지 and not isinstance(딴가지[0], ast.If)
                    and 가지[0].lineno > 줄 and len(out) < 상한):
                a1, a2 = 가지[0].lineno, 가지[-1].end_lineno
                b1, b2 = 딴가지[0].lineno, 딴가지[-1].end_lineno
                if a2 < b1:
                    줄들 = src.splitlines(keepends=True)
                    새 = ("".join(줄들[:a1 - 1]) + _블록(src, b1, b2)
                          + "".join(줄들[a2:b1 - 1])                 # `else:` 줄 따위는 그대로
                          + _블록(src, a1, a2) + "".join(줄들[b2:]))
                    if len(새.splitlines()) == len(src.splitlines()):
                        자취 = frozenset(range(a1, b2 + 1))
                        본것.add(("branch_swap", 줄, ""))
                        out.append(("branch_swap", f"{a1}~{b2}줄 if/else 가지 맞바꾸기", 새, 자취))
        elif isinstance(노드, ast.Constant):
            v = 노드.value
            if isinstance(v, bool):
                더하기("bool_swap", 줄, "True" if v else "False", "False" if v else "True")
            elif isinstance(v, int) and not isinstance(v, bool):
                더하기("const_num", 줄, str(v), "1" if v == 0 else ("0" if v == 1 else str(v + 1)))
    return out[:상한]


# ------------------------------------------------------------------ 어느 검사를 돌리나
def _검사고르기(repo: Path, rel: str, 몇: int = 한함수검사수) -> "list[str]":
    """그 파일을 재는 검사들. 이름이 닮은 것 -> 그 모듈을 임포트하는 것 순으로 고른다."""
    줄기 = Path(rel).stem
    꾸러미 = Path(rel).parts[0] if len(Path(rel).parts) > 1 else ""
    검사들 = sorted(x.name for x in (repo / "tests").glob("test_*.py"))
    점수 = []
    모듈 = rel[:-3].replace("/", ".")
    for t in 검사들:
        글 = (repo / "tests" / t).read_text(encoding="utf-8", errors="replace")
        s = 0
        if 줄기 and 줄기 in t:
            s += 10
        if 꾸러미 and 꾸러미 in t:
            s += 3
        if 모듈 in 글 or f"import {줄기}" in 글 or f"from {꾸러미} import" in 글:
            s += 5
        if rel in 글:
            s += 2
        if s:
            점수.append((s, t))
    점수.sort(key=lambda x: (-x[0], x[1]))
    return [f"tests/{t}" for _s, t in 점수[:몇]]


_덮기자 = r"""
import json, os, runpy, sys
목표, 검사 = sys.argv[1], sys.argv[2]
# **경로는 정확히 맞춘다.** endswith 로 맞추면 `tests/test_반쪽.py` 가 `반쪽.py` 로 끝나 검사 파일의 줄을
# 대상 파일의 덮임으로 센다(실측 2026-09-12: 안 돌는 3줄이 덮인 것으로 나왔다). 그러면 덮임 판정이
# 거짓이 되고, 그 위에 선 거짓초록 판정도 거짓이 된다.
목표절대 = os.path.realpath(목표)
본 = set()


def 훑기(frame, event, arg):
    if event == "line" and os.path.realpath(frame.f_code.co_filename) == 목표절대:
        본.add(frame.f_lineno)
    return 훑기


sys.argv = [검사]
sys.settrace(훑기)
try:
    runpy.run_path(검사, run_name="__main__")
except SystemExit:
    pass
except BaseException:
    pass
finally:
    sys.settrace(None)
    sys.stderr.write("@@덮인줄@@" + json.dumps(sorted(본)) + "\n")
"""


def 덮인줄(판: Path, rel: str, 검사들: "list[str]", 초: int = 검사시한초) -> "set[int]":
    """그 검사들이 **실제로 실행한** rel 의 줄 번호. 변형된 줄이 여기 없으면 살아남아도
    단언의 약함이 아니라 **덮임의 구멍**이다 -- 비등가 변형의 전제가 깨진다."""
    본: "set[int]" = set()
    도구 = 판 / ".se_덮기.py"
    도구.write_text(_덮기자, encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(판), **맑은환경}
    try:
        for t in 검사들:
            if not (판 / t).is_file():
                continue
            try:
                r = subprocess.run([*파이썬, str(도구), rel, t], cwd=str(판), env=env,
                                   capture_output=True, text=True, timeout=초)
            except subprocess.TimeoutExpired:
                continue
            for 줄 in (r.stderr or "").splitlines():
                if 줄.startswith("@@덮인줄@@"):
                    try:
                        본.update(json.loads(줄[len("@@덮인줄@@"):]))
                    except ValueError:
                        pass
    finally:
        도구.unlink(missing_ok=True)
    return 본


def _코드뼈(글: str) -> "tuple | None":
    """줄번호·파일이름을 지운 바이트코드 뼈. 같으면 의미가 같다(TCE). 컴파일 못 하면 None."""
    import types

    def 뼈(c):
        것 = []
        for x in c.co_consts:
            것.append(뼈(x) if isinstance(x, types.CodeType) else repr(x))
        return (c.co_name, c.co_code, tuple(c.co_names), tuple(c.co_varnames), tuple(것))

    try:
        return 뼈(compile(글, "<변형>", "exec"))
    except (SyntaxError, ValueError):
        return None


def 동등한가(원글: str, 새글: str) -> bool:
    """TCE -- 컴파일 결과가 같으면 **의미가 보존된** 동등 변형이다. 판정에서 뺀다.
    다르면 '다르다' 고 단정하지 않는다(한쪽 방향만 건전하다)."""
    a, b = _코드뼈(원글), _코드뼈(새글)
    return a is not None and a == b


def _돌려보기(판: Path, 검사들: "list[str]", 초: int = 검사시한초) -> "tuple[bool, str, str]":
    """하나라도 빨갛면 (True, 그 검사, 출력). 전부 초록이면 (False, "", "").
    **출력을 돌려준다** -- Cause(FAIL) 을 귀속하려면 트레이스백을 봐야 한다."""
    env = {**os.environ, "PYTHONPATH": str(판), **맑은환경}
    for t in 검사들:
        if not (판 / t).is_file():
            continue
        try:
            r = subprocess.run([*파이썬, t], cwd=str(판), env=env, capture_output=True,
                               text=True, timeout=초)
            rc, 글 = r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            rc, 글 = 124, "Timeout"
        if rc != 0:
            return True, t, 글[-3000:]
    return False, "", ""


def 깨끗하게(판: Path) -> None:
    """판을 **원래대로** 되돌린다 -- 추적되는 파일은 체크아웃, 추적 안 되는 것은 치운다.
    변형마다 같은 E 에서 시작해야 한다. 앞 변형이 남긴 파일이 다음 변형의 실패 원인이 되면
    그것이 곧 거짓 Red 다."""
    subprocess.run(["git", "-C", str(판), "checkout", "-q", "--", "."], capture_output=True, text=True)
    # -x 까지 치운다 -- __pycache__ 같은 무시되는 찌꺼기가 다음 판정의 원인이 되면 그것이 거짓 Red 다.
    subprocess.run(["git", "-C", str(판), "clean", "-qfdx"], capture_output=True, text=True)


def _한변형(판: Path, repo: Path, rel: str, 이름: str, 연산자: str, 설명: str,
          원글: str, 새글: str, 검사들: "list[str]", 덮임: "set[int]", 자취=None) -> dict:
    """변형 하나의 **판정 한 줄**. 사용자 정의(2026-09-12)의 결정 트리를 그대로 따른다.

        바탕 PASS 확인(부르는 쪽)  -> 아니면 INVALID_BASELINE
        Δ(P, m(P)) = {m} 인가      -> 아니면 INVALID_MUTATION
        E(P) = E(m(P)) 인가        -> 아니면 INVALID_MUTATION
        m(P) ≡ P 인가              -> 그렇다면 EQUIVALENT_MUTANT
        m(P) 를 돌린다
          PASS -> FALSE_GREEN (why: weak_assertion | not_covered)
          FAIL -> Cause(FAIL) = m 인가
                    그렇다 -> VALID_RED
                    아니다 -> FALSE_RED

    원장 열쇠는 **사용자가 지정한 영어 이름**을 쓴다(이 저장소의 한글 관례에서 벗어나지만,
    사양이 그 꼴을 지정했고 판정 원장은 사양과 한 글자도 어긋나지 않아야 한다)."""
    줄 = 0
    try:
        줄 = int(설명.split("줄")[0])
    except ValueError:
        줄 = 0
    행 = {"mutation_id": f"{rel}::{이름}::{연산자}::{줄}", "target": f"{rel}:{이름}", "operator": 연산자,
         "mutation": 설명, "line": 줄, "baseline_status": "PASS", "mutant_status": "",
         "delta": [], "environment_preserved": None, "single_mutation": None,
         "failure_cause": "", "classification": "", "tests": 검사들[:3]}

    # ---- 사양의 판정 순서(2026-09-12). PASS/FAIL 을 보기 **전에** Invalid·Equivalent 를 걸러낸다. ----
    #   Δ(P,Pm) ≠ {m}            -> Invalid
    #   E(P) ≠ E(Pm)             -> Invalid (또는 FalseRed 의 원인)
    #   m ∉ M_valid(P)           -> Invalid
    #   Pm ≡ P                   -> Equivalent
    #   T(Pm) = PASS             -> Survived (False Green)
    #   T(Pm) = FAIL, Cause = m  -> Killed
    #   T(Pm) = FAIL, Cause ≠ m  -> FalseRed
    def 맺기(결과: str, 분류: str, 까닭: str = "") -> dict:
        행["outcome"], 행["classification"] = 결과, 분류
        if 까닭:
            행["failure_cause"] = 까닭
        적기(repo, 행)
        return 행

    단일, 델타 = 단일변형인가(원글, 새글, 자취 if 자취 else 줄)
    행["single_mutation"], 행["delta"] = 단일, 델타
    if not 단일:
        return 맺기(못쓸, 못쓸변형, "Δ(P, m(P)) ≠ {m} -- " + "; ".join(델타))
    됨, 왜 = 변형유효한가(새글, rel)
    행["mutation_valid"] = 됨
    if not 됨:
        return 맺기(못쓸, 못쓸변형, f"m ∉ M_valid(P) -- {왜}")
    if 동등한가(원글, 새글):
        행["mutant_status"] = "PASS(안 돌림)"
        return 맺기(동등, 동등변형, "m(P) ≡ P (TCE) -- 의미가 보존됐다")
    try:
        깨끗하게(판)                                    # I3 -- 앞 변형이 남긴 것이 다음 판정에 섞이지 않게
        (판 / rel).write_text(새글, encoding="utf-8")
        보존, 남은것 = 환경보존됐나(판, rel)
        행["environment_preserved"] = 보존
        if not 보존:
            return 맺기(못쓸, 못쓸변형, f"E(P) ≠ E(m(P)) -- 대상 밖이 바뀌었다: {남은것[:4]}")
        빨강, 어디, 출력 = _돌려보기(판, 검사들)
        행["mutant_status"] = "FAIL" if 빨강 else "PASS"
        행["failing_test"] = 어디
        if not 빨강:
            행["why"] = "not_covered" if (줄 and 덮임 and 줄 not in 덮임) else "weak_assertion"
            return 맺기(살아남음, 거짓초록,
                      "그 줄이 한 번도 실행되지 않는다(덮임의 구멍)" if 행["why"] == "not_covered"
                      else "검사가 부르지만 결과를 단언하지 않는다")
        _외부, 까닭 = 실패원인(출력)
        행["traceback"] = 출력[-400:]
        # **Cause 는 글을 읽어 짐작하지 않는다 -- 변형을 빼고 같은 판에서 다시 돌린다.**
        (판 / rel).write_text(원글, encoding="utf-8")
        또빨강, 또어디, _또출력 = _돌려보기(판, 검사들)
        행["baseline_rerun_status"] = "FAIL" if 또빨강 else "PASS"
        if 또빨강:
            return 맺기(거짓빨강결과, 거짓빨강,
                      f"{까닭} -- **변형을 빼도 같은 실패가 난다**(Cause(FAIL) ≠ m): {또어디}")
        return 맺기(잡힘, 유효빨강, f"{까닭} -- 변형을 빼면 초록이다(Cause(FAIL) = m)")
    except OSError as e:
        return 맺기(못쓸, 바탕터짐, f"{type(e).__name__}: {str(e)[:120]}")
    finally:
        깨끗하게(판)                                    # 다음 변형도 같은 E 에서 시작한다


def 사냥(repo=None, 파일들: "list[str]" = None, 시한초: int = 기본시한초, 말하기=None,
       함수상한: int = 0) -> dict:
    """**조용히 틀려도 초록인 자리**를 시한까지 찾는다. {잰변형, 살아남음, 죽음, 못잼, 살아남은것}.

    파일마다: 바꿀 함수를 고르고, 그 파일을 재는 검사를 고르고, **깨끗한 HEAD 판**에 변형을 얹어
    검사를 돌린다. 빨개지면 그 변형은 죽었다(검사가 본다). 초록이면 **살아남았다 -- 거짓 초록이다.**
    변형을 얹기 전에 그 검사들이 원래 초록인지 먼저 본다 -- 원래 빨간 검사는 아무것도 증명하지 못한다."""
    repo = Path(repo or REPO)
    말 = 말하기 or (lambda s: print(s, flush=True))
    시작 = time.monotonic()
    if 파일들 is None:
        r = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", "ls-files", "-z", "*.py"],
                           capture_output=True, text=True)
        파일들 = [x for x in r.stdout.split("\0") if x and not x.startswith("tests/")]
    out = {"잰변형": 0, "살아남음": 0, "죽음": 0, "못잼": 0, "덮이지않음": 0, "동등제외": 0,
           "살아남은것": [], "덮이지않은것": [], "파일수": 0}
    판 = Path(tempfile.mkdtemp(prefix="se-변형-"))
    깔림 = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(판), "HEAD"],
                        capture_output=True, text=True)
    if 깔림.returncode != 0:
        out["못잼"] += 1
        말(f"[변형] HEAD 판을 못 꺼냈다: {깔림.stderr.strip()[:120]}")
        return out
    try:
        적기(repo, {"꼴": "사냥시작", "파일수": len(파일들), "시한초": 시한초})
        for rel in 파일들:
            if time.monotonic() - 시작 > 시한초:
                말(f"[변형] 시한 {시한초}초 -- 멈춘다")
                break
            원글 = (판 / rel).read_text(encoding="utf-8", errors="replace") if (판 / rel).is_file() else None
            if 원글 is None:
                continue
            이름들 = list(_자리(원글))
            if not 이름들:
                continue
            검사들 = _검사고르기(repo, rel)
            if not 검사들:
                out["못잼"] += 1
                적기(repo, {"꼴": "검사없음", "파일": rel, "함수수": len(이름들)})
                continue
            빨강먼저, 어디, 바탕출력 = _돌려보기(판, 검사들)
            if 빨강먼저:
                # T(P,E) = FAIL -> 원본이 빨갛다. 변형 결과를 Green/Red 로 쓰지 않는다.
                out["못잼"] += 1
                out[못쓸바탕] = out.get(못쓸바탕, 0) + 1
                적기(repo, {"꼴": "원래빨강", "파일": rel, "검사": 어디, "classification": 못쓸바탕})
                말(f"[변형] {rel}: 원본이 빨강({어디}) -- {못쓸바탕}")
                continue
            out["파일수"] += 1
            덮임 = 덮인줄(판, rel, 검사들)                 # 파일마다 한 번 -- 변형마다 다시 재지 않는다
            적기(repo, {"꼴": "덮임", "파일": rel, "덮인줄수": len(덮임), "검사": 검사들[:3]})
            if 함수상한:
                이름들 = 이름들[:함수상한]
            for 이름 in 이름들:
                if time.monotonic() - 시작 > 시한초:
                    break
                for 연산자, 설명, 새글, 자취 in 변형들(원글, 이름):
                    if time.monotonic() - 시작 > 시한초:
                        break
                    행 = _한변형(판, repo, rel, 이름, 연산자, 설명, 원글, 새글, 검사들, 덮임, 자취)
                    out["잰변형"] += 1
                    판정 = 행["classification"]
                    out[판정] = out.get(판정, 0) + 1
                    if 판정 == 거짓초록:
                        out["살아남음"] += 1
                        out["살아남은것"].append({"파일": rel, "함수": 이름, "변형": 설명,
                                              "검사": 검사들, "why": 행.get("why", "")})
                        if 행.get("why") == "not_covered":
                            out["덮이지않음"] += 1
                            out["덮이지않은것"].append({"파일": rel, "함수": 이름, "변형": 설명})
                        말(f"[변형] **{거짓초록}** {rel}:{이름} -- {설명} ({행.get('why')})")
                    elif 판정 == 유효빨강:
                        out["죽음"] += 1
                    elif 판정 == 동등변형:
                        out["동등제외"] += 1
                    elif 판정 in (거짓빨강, 못쓸변형, 바탕터짐):
                        out["못잼"] += 1
                        말(f"[변형] {판정} {rel}:{이름} -- {설명} · {행.get('failure_cause', '')[:60]}")
            적기(repo, {"꼴": "파일끝", "파일": rel, "잰변형": out["잰변형"], "살아남음": out["살아남음"]})
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(판)],
                       capture_output=True, text=True)
        shutil.rmtree(판, ignore_errors=True)
    적기(repo, {"꼴": "사냥끝", **{k: v for k, v in out.items() if k != "살아남은것"}})
    return out


# ------------------------------------------------------------------ 2차 메타검증: 그 판정이 거짓인가
# 사용자(2026-09-12): "Red/Green 과 False Red/False Green 은 서로 다른 층위다."
#
#   1차 검증층 -- 절차적 상태 전이. 필요한 도구를 안 부른 상태(Red)에서 부르고 조건을 만족하면 Green.
#                 이 저장소에서는 rehearsal.시험/전체검사 와 관문 사슬(공허·절제·열쇠·미정의·순환)이 그것이다.
#   2차 메타층 -- 그렇게 얻은 Red/Green 이 **올바른 판정이었나**. 여기(mutate)가 그것이다.
#
#   Reliable = (FR ∪ FG)^c
#   Commit   = Green ∧ (FR ∪ FG)^c
#
# 그래서 초록이어도 커밋이 안 될 수 있다(FG 가 있으면 그 초록은 못 믿는다), 빨강이어도 그 빨강이
# 거짓일 수 있다(FR). 둘을 한 비트로 합치면 이 구별이 사라진다.
def 신뢰(일차초록: bool, 사냥결과: dict) -> dict:
    """{green, reliable, commit, FG, FR, INVALID, 말}. **판정하지 않는다 -- 이미 난 판정을 합친다.**

    일차초록 = rehearsal 층이 낸 Green/Red(V(P)=1 ∧ T(P)=PASS). 사냥결과 = mutate.사냥 의 분류별 셈.
    Reliable = FG 도 FR 도 없고, 판정에 쓸 수 없는 것(INVALID_*·INFRA)도 남지 않았을 때."""
    FG = int(사냥결과.get(거짓초록, 0))
    FR = int(사냥결과.get(거짓빨강, 0))
    무효 = int(사냥결과.get(못쓸변형, 0)) + int(사냥결과.get(못쓸바탕, 0)) + int(사냥결과.get(바탕터짐, 0))
    reliable = (FG == 0 and FR == 0 and 무효 == 0)
    commit = bool(일차초록) and reliable
    까닭 = []
    if FG:
        까닭.append(f"{거짓초록} {FG}개 -- 그 초록은 못 믿는다(잘못된 코드가 통과한다)")
    if FR:
        까닭.append(f"{거짓빨강} {FR}개 -- 변형과 무관한 실패를 잡힌 것으로 셀 수 없다")
    if 무효:
        까닭.append(f"판정에 쓸 수 없는 것 {무효}개(INVALID_*/INFRA) -- 모르는 것은 초록이 아니다")
    if not 일차초록:
        까닭.append("1차 층이 Red 다")
    return {"green": bool(일차초록), "reliable": reliable, "commit": commit,
            "FG": FG, "FR": FR, "INVALID": 무효,
            "말": ("Commit = Green ∧ (FR∪FG)^c -> " + ("**허용**" if commit else "**막음**")
                  + ("" if not 까닭 else " · " + " · ".join(까닭)))}


def 관찰됐나(repo=None, target: str = "") -> "tuple[bool, str]":
    """Obs(T, P) -- **검사가 그 함수의 결과를 관찰하나.**

    측정으로 정의한다: 그 함수의 **반환값 변형**(return_none · return_zero · return_minus1 ·
    const_return) 중 하나라도 `Killed` 면 검사는 결과를 본 것이다. 전부 Survived 면 부르기만 한다.
    재 본 적이 없으면 (False, "안 쟀다") -- 모르는 것을 관찰됐다고 하지 않는다."""
    반환꼴 = ("return_none", "return_zero", "return_minus1", "const_return")
    것 = [x for x in 원장읽기(repo)
         if x.get("operator") in 반환꼴 and (not target or x.get("target") == target)]
    if not 것:
        return False, "반환값 변형을 재 본 적이 없다"
    잡은것 = [x for x in 것 if x.get("outcome") == 잡힘]
    if 잡은것:
        return True, f"반환값 변형 {len(잡은것)}/{len(것)}개가 잡혔다 -- 검사가 결과를 본다"
    return False, f"반환값 변형 {len(것)}개가 다 살았다 -- 검사가 부르기만 한다"


def 마지막사냥(repo=None) -> dict:
    """원장에서 마지막 `사냥끝` 줄. 없으면 {} -- **사냥을 안 한 것을 초록으로 읽지 않게** 빈 것을 준다."""
    for x in reversed(원장읽기(repo)):
        if x.get("꼴") == "사냥끝":
            return x
    return {}


def 파일별거짓초록(repo=None, 파일들: "list[str]" = None) -> "list[dict]":
    """원장에 남은 FALSE_GREEN 중 그 파일들에 걸린 것. commit_guard 가 커밋 범위로 좁힐 때 쓴다."""
    것 = [x for x in 원장읽기(repo) if x.get("classification") == 거짓초록]
    if 파일들 is None:
        return 것
    고른 = set(파일들)
    return [x for x in 것 if str(x.get("target", "")).split(":")[0] in 고른]


def 보고(repo=None, 몇: int = 20) -> str:
    """원장에서 사람이 읽는 표. 사냥하지 않는다."""
    행들 = 원장읽기(repo)
    산것 = [x for x in 행들 if x.get("classification") == 거짓초록]
    끝 = [x for x in 행들 if x.get("꼴") == "사냥끝"]
    셈 = {}
    for x in 행들:
        c = x.get("classification")
        if c:
            셈[c] = 셈.get(c, 0) + 1
    줄 = [f"**거짓 초록 사냥** -- 원장 {len(행들)}줄 · 사냥 {len(끝)}번",
         "분류: " + (", ".join(f"{k} {v}" for k, v in sorted(셈.items(), key=lambda kv: -kv[1])) or "없음")]
    if 끝:
        마 = 끝[-1]
        줄.append(f"마지막: 변형 {마.get('잰변형', 0)}개 중 **거짓초록 {마.get('살아남음', 0)}개** · "
                  f"죽음 {마.get('죽음', 0)} · 덮이지않음 {마.get('덮이지않음', 0)} · 동등제외 {마.get('동등제외', 0)} "
                  f"· 못잼 {마.get('못잼', 0)} · 파일 {마.get('파일수', 0)}")
    if not 산것:
        줄.append("살아남은 변형이 없다 -- 고른 변형 안에서는 거짓 초록이 안 보인다")
        return "\n".join(줄)
    파일별: dict = {}
    for x in 산것:
        파일별.setdefault(str(x.get("target", "?")).split(":")[0], []).append(x)
    줄.append(f"\n**살아남은 변형 {len(산것)}개** (코드가 이렇게 틀려도 검사가 초록이다):")
    for f, xs in sorted(파일별.items(), key=lambda kv: -len(kv[1]))[:몇]:
        줄.append(f"  {f} -- {len(xs)}개")
        for x in xs[:3]:
            줄.append(f"      {x.get('target', '')}: {x.get('mutation', '')} [{x.get('why', '')}]")
    덮안 = [x for x in 행들 if x.get("classification") == 거짓초록 and x.get("why") == "not_covered"]
    if 덮안:
        파 = {}
        for x in 덮안:
            키 = str(x.get("target", "?")).split(":")[0]
            파[키] = 파.get(키, 0) + 1
        줄.append(f"\n**한 번도 실행되지 않는 줄의 변형 {len(덮안)}개** (단언이 약한 것이 아니라 덮임의 구멍): "
                  + ", ".join(f"{f}({n})" for f, n in sorted(파.items(), key=lambda kv: -kv[1])[:6]))
    못 = [x for x in 행들 if x.get("꼴") == "검사없음"]
    if 못:
        줄.append(f"\n재는 검사를 못 찾은 파일 {len(못)}개 -- 그 자체가 틈이다: "
                  + ", ".join(x.get("파일", "?") for x in 못[:6]))
    return "\n".join(줄)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="거짓 초록 사냥 -- 조용히 틀려도 초록인 검사를 찾는다")
    ap.add_argument("--시한", type=int, default=기본시한초, help=f"초 (기본 {기본시한초})")
    ap.add_argument("--파일", action="append", default=None, help="이 파일만 (여러 번)")
    ap.add_argument("--함수상한", type=int, default=0, help="파일마다 함수 이만큼만 (0=전부)")
    ap.add_argument("--보고", action="store_true", help="원장 요약만 찍는다")
    a = ap.parse_args(argv)
    if a.보고:
        print(보고())
        return 0
    r = 사냥(파일들=a.파일, 시한초=a.시한, 함수상한=a.함수상한)
    print()
    print(보고())
    return 1 if r["살아남음"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
