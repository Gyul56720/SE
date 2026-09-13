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
# ------------------------------------------------------------------ π0 -- 공정한 정책(똑똑한 정책이 아니다)
# 사용자(2026-09-12): "첫 π 는 '똑똑한 π' 가 아니라 '공정한 π' 여야 한다. 그래야 나중에 π 가 바뀌었을 때
# ASTRA 가 실제로 더 똑똑해졌다고 주장할 수 있다."
#
#   π0 : P(m) = 1/|M0| · P(f) = 1/|F| · P(t) = 1/|T_usable| · seed = s0
#
# 내 순회는 **전수(exhaustive)** 다 -- 모든 파일·함수·연산자를 돈다. 그것은 균등 추출보다 강하지만
# (분산 0) **시한에 잘리면 순서가 곧 편향**이 된다: git 순서로 앞쪽 파일만 재고 끝난다.
# 그래서 씨앗으로 섞는다. 전수로 끝나면 결과가 같고, 시한에 잘리면 **치우치지 않은 표본**이 된다.
# 씨앗을 고정하는 까닭은 π0 -> π1 비교에서 차이가 씨앗 탓이 아니게 하기 위함이다.
기본씨앗 = 0
# ------------------------------------------------------------------ 잴 값이 없는 곳
# **실측 2026-09-13 (D_0):** 19파일 중 4개가 `orchestrator/runs/` 의 **실행 산출물**이었다
# (커밋된 출력물 110개 · 1,276줄). 전부 Killed 0 · FG 40 -- 아무도 검사하지 않으니 당연하다.
# 그것을 세면 두 가지를 잃는다: 시한(16.8초×40)과 **점수의 뜻**(0.327 이 산출물을 빼면 0.341 이다).
#
#   잴 값이 있는 것 = 누군가 쓰는 코드.  산출물은 고쳐야 할 코드가 아니다.
안잴곳 = ("orchestrator/runs/",)


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
    # **자취 밖이 바뀌었나**를 본다 -- 같은지가 아니라 **드는지**(Δ ⊆ 자취). 자취 안의 어떤 줄이
    # 안 바뀌는 것은 흠이 아니다: 가지 맞바꾸기는 `else:` 줄과 두 가지의 똑같은 줄은 그대로 두므로
    # 같음을 요구하면 멀쩡한 변형이 INVALID_MUTATION 으로 버려진다(실측 2026-09-13: D_0 에서 5건).
    # 한 줄 변형은 |자취|=1 이라 드는 것 = 같은 것이어서 더 느슨해지지 않는다.
    if 다른 <= 예상:
        return True, [f"{sorted(다른)}"]
    return False, [f"선언한 자취 {sorted(예상)} 밖이 바뀌었다: {sorted(다른 - 예상)}"]


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


def 덮인줄(판: Path, rel: str, 검사들: "list[str]", 초: int = None) -> "set[int]":
    """그 검사들이 **실제로 실행한** rel 의 줄 번호. 변형된 줄이 여기 없으면 살아남아도
    단언의 약함이 아니라 **덮임의 구멍**이다 -- 비등가 변형의 전제가 깨진다."""
    초 = 초 or 검사시한초
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


def 동등장치살았나() -> "tuple[bool, str]":
    r"""**TCE 가 한 번이라도 불을 켜나.** (켜나, 말).

    실측 2026-09-13 (D_0): 1111번 재고 `동등 0` 이었다. 그 0 은 두 가지 뜻일 수 있다 --
    등가 변형이 정말 없었거나, **장치가 안 도는 것.** 이 저장소는 그 병을 이미 앓았다
    (`ledgerstat` 의 여섯 칸이 늘 0 이었다). 그래서 0 을 적을 때마다 장치를 같이 잰다.

    탐침: 두 가지가 **똑같은** if/else 를 맞바꾼다 -> 바이트코드가 같아야 한다.
    이것이 거짓이면 `동등 0` 은 아무것도 말하지 않는다."""
    원 = "def f(a):\n    if a:\n        return 1\n    else:\n        return 1\n"
    것 = [새글 for op, _설, 새글, _자취 in 변형들(원, "f") if op == "branch_swap"]
    if not 것:
        return False, "탐침이 가지 맞바꾸기를 못 만들었다 -- 장치를 잴 수 없다"
    if not 동등한가(원, 것[0]):
        return False, "**똑같은 두 가지를 맞바꿨는데 동등이라 안 한다 -- 장치가 죽었다**"
    # 한 방향만 건전하다: 다른 것을 같다고 하면 안 된다(진짜 Killed 를 동등으로 빼면 점수가 거짓으로 오른다)
    다름 = "def f(a):\n    if a:\n        return 1\n    else:\n        return 2\n"
    if 동등한가(원, 다름):
        return False, "**다른 것을 동등이라 한다 -- 진짜 잡힘을 동등으로 빼 버린다**"
    return True, "탐침 통과 -- 같은 것은 같다 하고 다른 것은 같다 하지 않는다"


def _돌려보기(판: Path, 검사들: "list[str]", 초: int = None) -> "tuple[bool, str, str]":
    """하나라도 빨갛면 (True, 그 검사, 출력). 전부 초록이면 (False, "", "").
    **출력을 돌려준다** -- Cause(FAIL) 을 귀속하려면 트레이스백을 봐야 한다.

    시한은 **부를 때** 모듈 전역에서 읽는다 -- 기본값으로 박아 두면 정의될 때 한 번 묶여서
    `M.검사시한초 = 2` 가 아무 효과가 없다(검사가 그것을 못 흉내 낸다)."""
    초 = 초 or 검사시한초
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
    들어온때 = time.monotonic()
    행 = {"mutation_id": f"{rel}::{이름}::{연산자}::{줄}", "target": f"{rel}:{이름}", "operator": 연산자,
         "mutation": 설명, "line": 줄, "baseline_status": "PASS", "mutant_status": "",
         "delta": [], "environment_preserved": None, "single_mutation": None,
         "failure_cause": "", "classification": "", "tests": 검사들[:3], "cost": None}

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
        # **cost 를 적는다** -- 사용자(2026-09-12)의 보상식 R(m) = αFG + βFR + γΔJ - λCost(m) 의 마지막 항이다.
        # 24시간 데이터는 한 번만 모이므로, 그때 안 적으면 그 항을 영영 못 쓴다.
        행["cost"] = {"초": round(time.monotonic() - 들어온때, 2)}
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
            # RG1 이 무너졌다. 까닭은 둘 중 하나다 -- 바탕이 불안정하거나(앞 실행이 상태를 남겼다),
            # 환경이 변형과 무관하게 깨졌다. 어느 쪽이든 **잡힌 것으로 세지 않는다.**
            행["why"] = "baseline_unstable" if 또어디 == 어디 else "env_changed"
            return 맺기(거짓빨강결과, 거짓빨강,
                      f"{까닭} -- **변형을 빼도 같은 실패가 난다**(Cause(FAIL) ≠ m · {행['why']}): {또어디}")
        return 맺기(잡힘, 유효빨강, f"{까닭} -- 변형을 빼면 초록이다(Cause(FAIL) = m)")
    except OSError as e:
        return 맺기(못쓸, 바탕터짐, f"{type(e).__name__}: {str(e)[:120]}")
    finally:
        깨끗하게(판)                                    # 다음 변형도 같은 E 에서 시작한다


# ------------------------------------------------------------------ 바탕이 도중에 무너졌나
# **실측 2026-09-13 (D_0):** `brief/report.py` 에서 FALSE_RED 가 **107 번 잇따랐다.** 까닭을 끝까지
# 따라가니 `tests/test_brief.py` 가 받은날을 `2026-09-09` 로 박아 두었고 신선도가 3일이어서,
# **사냥이 도는 동안 날이 바뀌며 그 검사가 혼자 빨개졌다.** RG0 는 파일마다 **한 번만** 재므로
# 그 뒤로는 변형마다 "변형을 빼도 빨갛다" 를 107 번 되풀이했다 -- 판정은 옳았지만(잡힘으로 안 셌다)
# 시한을 그만큼 버렸다.
#
#   RG0 의 유효 기간은 영원하지 않다. 거짓 빨강이 잇따르면 **바탕을 다시 잰다.**
잇단거짓빨강상한 = 3


def 접을까(판: Path, repo: Path, rel: str, 검사들: "list[str]", out: dict, 말) -> bool:
    """거짓 빨강이 잇따랐다 -- RG0 를 **다시** 재고, 빨갛면 그 파일은 더 재지 않는다.

    참을 돌려주면 부르는 쪽이 그 파일을 접는다. 이미 적힌 FALSE_RED 줄은 그대로 둔다 --
    그것들도 사실이었다(변형 탓이 아니었다). 다만 그 뒤를 더 재지 않는다."""
    깨끗하게(판)                                  # 판에 변형이 남아 있지 않게
    또빨강, 또어디, _ = _돌려보기(판, 검사들)
    if not 또빨강:
        return False                              # 바탕은 멀쩡하다 -- 거짓 빨강이 우연히 몰렸다
    out["못잼"] += 1
    out[못쓸바탕] = out.get(못쓸바탕, 0) + 1
    적기(repo, {"꼴": "바탕무너짐", "파일": rel, "검사": 또어디, "classification": 못쓸바탕,
             "failure_cause": f"거짓 빨강 {잇단거짓빨강상한}번 뒤 RG0 를 다시 재니 빨강 -- "
                              "사냥 도중에 바탕이 무너졌다(RG0 의 유효 기간이 끝났다)"})
    말(f"[변형] {rel}: 도중에 바탕이 무너졌다({또어디}) -- 이 파일은 접는다")
    return True


def 사냥(repo=None, 파일들: "list[str]" = None, 시한초: int = 기본시한초, 말하기=None,
       함수상한: int = 0, 뺄검사: "list[str]" = None, 씨앗: int = 기본씨앗) -> dict:
    """**조용히 틀려도 초록인 자리**를 시한까지 찾는다. {잰변형, 살아남음, 죽음, 못잼, 살아남은것}.

    파일마다: 바꿀 함수를 고르고, 그 파일을 재는 검사를 고르고, **깨끗한 HEAD 판**에 변형을 얹어
    검사를 돌린다. 빨개지면 그 변형은 죽었다(검사가 본다). 초록이면 **살아남았다 -- 거짓 초록이다.**
    변형을 얹기 전에 그 검사들이 원래 초록인지 먼저 본다(RG0) -- 원래 빨간 검사는 아무것도 증명하지 못한다.

    `뺄검사` 는 **거짓빨강사냥이 먼저 걸러낸 못 믿을 검사**다(상태오염·환경의존). 그것을 바탕으로 쓰면
    RG0 가 무너져 그 파일을 통째로 못 재게 되므로, 미리 뺀다 -- 사용자(2026-09-12)가 말한
    `Baseline RG -> Mutation Validity -> FR Attribution -> FG/Equivalent` 순서의 실제 효과가 이것이다."""
    repo = Path(repo or REPO)
    말 = 말하기 or (lambda s: print(s, flush=True))
    시작 = time.monotonic()
    import random
    주사위 = random.Random(씨앗)
    if 파일들 is None:
        r = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", "ls-files", "-z", "*.py"],
                           capture_output=True, text=True)
        파일들 = sorted(x for x in r.stdout.split("\0")
                     if x and not x.startswith("tests/") and not x.startswith(안잴곳))
        주사위.shuffle(파일들)                      # π0 -- 시한에 잘려도 표본이 치우치지 않게
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
        적기(repo, {"꼴": "사냥시작", "파일수": len(파일들), "시한초": 시한초,
                  "정책": {"이름": "pi0", "연산자": "uniform(전수)", "파일": "uniform(전수, 섞음)",
                         "seed": 씨앗, "뺀검사수": len(뺄검사 or ())}})
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
            검사들 = [x for x in _검사고르기(repo, rel) if x not in set(뺄검사 or ())]
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
            주사위.shuffle(이름들)                  # 함수 순서도 씨앗으로 -- 같은 까닭
            if 함수상한:
                이름들 = 이름들[:함수상한]
            잇단거짓빨강, 접었다 = 0, False
            for 이름 in 이름들:
                if 접었다 or time.monotonic() - 시작 > 시한초:
                    break
                변형목록 = 변형들(원글, 이름)
                주사위.shuffle(변형목록)            # 연산자도 균등하게 -- 상한·시한에 앞쪽만 쓰이지 않게
                for 연산자, 설명, 새글, 자취 in 변형목록:
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
                    잇단거짓빨강 = 잇단거짓빨강 + 1 if 판정 == 거짓빨강 else 0
                    if 잇단거짓빨강 >= 잇단거짓빨강상한 and 접을까(판, repo, rel, 검사들, out, 말):
                        접었다 = True
                        break
            적기(repo, {"꼴": "파일끝", "파일": rel, "잰변형": out["잰변형"], "살아남음": out["살아남음"]})
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(판)],
                       capture_output=True, text=True)
        shutil.rmtree(판, ignore_errors=True)
    적기(repo, {"꼴": "사냥끝", **{k: v for k, v in out.items() if k != "살아남은것"}})
    return out


# ------------------------------------------------------------------ 병렬 사냥: 판정을 바꾸지 않는 범위에서만
# 사용자(2026-09-13): "시간이 문제면 비동기로 하면 안 되나? 병렬로 한 번에 뿌려서."
#
# 맞다 -- 16.8초/변형의 대부분은 **검사 서브프로세스를 기다리는 시간**이다. 그런데 병렬화는
# **판정을 바꿀 수 있다.** 그래서 바꾸지 않는 범위만 병렬로 돈다.
#
#   파일 단위로 나눈다       -- 일꾼마다 **자기 판(worktree)** 을 갖는다. 서로의 되돌림을 안 본다
#   한 판 안은 순차다        -- `깨끗하게` 와 복원 귀속(RG0 -> 변형 -> RG1)은 **독점된 판**을 요구한다
#   원장은 일꾼마다 따로 쓴다 -- 덧붙이기가 섞여 한 줄이 찢기지 않게. 끝에 합친다
#   HOME·TMPDIR 도 갈라 준다 -- 검사가 판 밖(캐시·고정 경로)에 쓰면 그것이 서로를 오염시킨다
#
# **그래도 가정으로 두지 않는다.** `tests/test_mutate.py` 가 같은 표본을 순차로 한 번,
# 병렬로 한 번 재서 **변형마다의 판정이 똑같은지** 본다. 다르면 병렬이 측정을 바꾼 것이다.
#
# 시한초과는 늘어날 수 있다(코어를 나눠 쓰니 느려진다). 그것은 빨강이 아니라 못잼으로 적히고,
# 요약의 `시한초과` 와 `견줄수있나` 가 그만큼 표본이 줄었다고 말해 준다 -- 숨지 않는다.
def _일꾼수(바람: int = 0) -> int:
    """쓸 일꾼 수. 0 이면 스스로 고른다.

    **실측 2026-09-13: `코어수 - 1` 은 2코어 기계에서 1이 된다 -- 즉 병렬이 아니다.**
    VM 의 `nproc` 가 2 인데 `--일꾼 0` 을 주면 조용히 순차로 돌았다. 기본값이 제 구실을
    못 하는 쪽으로 무너지면 **쓰는 사람은 빠른 줄 알고 기다린다.** 그래서 2코어 이하에서는
    2를 준다 -- 봇은 대개 디스코드를 기다리며 놀고 있고, 검사 하나는 짧다.
    (2코어에서 2일꾼의 실제 배수는 그 기계에서 재 봐야 안다. 4코어·3일꾼은 2.99배였다.)"""
    if 바람 and 바람 > 0:
        return int(바람)
    n = os.cpu_count() or 1
    return 2 if n <= 2 else n - 1


def _쟬파일들(repo: Path, 파일들=None, 씨앗: int = 기본씨앗) -> "list[str]":
    """π0 의 순서를 **부모에서 한 번** 만든다. 일꾼에게 나눠 줘도 같은 순서에서 나온 것이어야 한다."""
    if 파일들 is not None:
        return list(파일들)
    import random
    r = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", "ls-files", "-z", "*.py"],
                       capture_output=True, text=True)
    것 = sorted(x for x in r.stdout.split("\0")
              if x and not x.startswith("tests/") and not x.startswith(안잴곳))
    random.Random(씨앗).shuffle(것)
    return 것


def 병렬사냥(repo=None, 시한초: int = 기본시한초, 일꾼: int = 0, 파일들=None, 말하기=None,
        함수상한: int = 0, 뺄검사: "list[str]" = None, 씨앗: int = 기본씨앗) -> dict:
    """파일을 일꾼들에게 나눠 동시에 잰다. 일꾼이 1이면 그냥 `사냥` 이다(다른 길이 아니다).

    돌려주는 것은 `사냥` 과 같은 꼴 -- 합친 원장에서 다시 센 것이다."""
    repo = Path(repo or REPO)
    말 = 말하기 or (lambda s: print(s, flush=True))
    n = _일꾼수(일꾼)
    차례 = _쟬파일들(repo, 파일들, 씨앗)
    if n <= 1 or len(차례) <= 1:
        말(f"[변형] **순차로 돈다** (일꾼 {n} · 파일 {len(차례)}개) -- 병렬이 아니다")
        return 사냥(repo, 차례, 시한초, 말하기, 함수상한, 뺄검사, 씨앗)
    n = min(n, len(차례))
    몫 = [차례[i::n] for i in range(n)]              # 돌려 나눈다 -- π0 의 순서를 고르게 쪼갠다
    적기(repo, {"꼴": "병렬시작", "일꾼": n, "파일수": len(차례), "시한초": 시한초,
              "정책": {"이름": "pi0", "seed": 씨앗, "일꾼": n, "나눔": "round-robin"}})
    말(f"[변형] 병렬 {n}일꾼 · 파일 {len(차례)}개 ({'·'.join(str(len(x)) for x in 몫)})")
    샤드 = [f"logs/거짓초록-일꾼{i}.jsonl" for i in range(n)]
    for s in 샤드:
        (repo / s).parent.mkdir(parents=True, exist_ok=True)
        (repo / s).unlink(missing_ok=True)
    집 = Path(tempfile.mkdtemp(prefix="se-일꾼집-"))
    일들 = []
    try:
        for i, (몫하나, s) in enumerate(zip(몫, 샤드)):
            argv = [sys.executable, str(Path(__file__).resolve()), "--저장소", str(repo),
                    "--원장이름", s, "--시한", str(시한초), "--씨앗", str(씨앗)]
            if 함수상한:
                argv += ["--함수상한", str(함수상한)]
            for f in 몫하나:
                argv += ["--파일", f]
            for x in (뺄검사 or ()):
                argv += ["--뺄검사", x]
            칸 = 집 / f"일꾼{i}"
            (칸 / "tmp").mkdir(parents=True, exist_ok=True)
            env = {**os.environ, "HOME": str(칸), "TMPDIR": str(칸 / "tmp"), **맑은환경}
            일들.append(subprocess.Popen(argv, env=env, cwd=str(repo),
                                      stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True))
        for i, 일 in enumerate(일들):
            try:
                _, 에러 = 일.communicate(timeout=시한초 + 600)
            except subprocess.TimeoutExpired:
                일.kill()
                _, 에러 = 일.communicate()
                에러 = (에러 or "") + " -- 일꾼이 시한을 넘겨 죽였다"
            if 에러 and 일.returncode not in (0, 1):
                말(f"[변형] 일꾼 {i} 끝값 {일.returncode}: {에러.strip()[:200]}")
                적기(repo, {"꼴": "일꾼터짐", "일꾼": i, "끝값": 일.returncode,
                          "failure_cause": (에러 or "").strip()[-300:]})
    finally:
        shutil.rmtree(집, ignore_errors=True)
    # ---- 샤드를 합친다. 덧붙이기만 -- 한 줄도 버리지 않는다.
    모은: "list[dict]" = []
    for s in 샤드:
        p = repo / s
        if not p.is_file():
            continue
        줄들 = [x for x in p.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
        with _원장(repo).open("a", encoding="utf-8") as f:
            for 줄 in 줄들:
                f.write(줄 + "\n")
                try:
                    모은.append(json.loads(줄))
                except ValueError:
                    pass
        p.unlink(missing_ok=True)
    out = {"잰변형": 0, "살아남음": 0, "죽음": 0, "못잼": 0, "덮이지않음": 0, "동등제외": 0,
           "살아남은것": [], "덮이지않은것": [], "파일수": 0, "일꾼": n}
    for x in 모은:
        결 = x.get("outcome")
        if not 결:
            if x.get("꼴") == "덮임":
                out["파일수"] += 1
            continue
        out["잰변형"] += 1
        분 = x.get("classification")
        out[분] = out.get(분, 0) + 1
        if 분 == 거짓초록:
            out["살아남음"] += 1
            out["살아남은것"].append({"파일": str(x.get("target", "")).split(":")[0],
                                  "함수": str(x.get("target", "")).split(":")[-1],
                                  "변형": x.get("mutation"), "검사": x.get("tests"),
                                  "why": x.get("why", "")})
            if x.get("why") == "not_covered":
                out["덮이지않음"] += 1
        elif 분 == 유효빨강:
            out["죽음"] += 1
        elif 분 == 동등변형:
            out["동등제외"] += 1
        else:
            out["못잼"] += 1
    적기(repo, {"꼴": "사냥끝", **{k: v for k, v in out.items()
                               if k not in ("살아남은것", "덮이지않은것")}})
    return out


# ------------------------------------------------------------------ 거짓 빨강 사냥: 빨강이 거짓인가
# 사용자(2026-09-12): "왜 거짓 빨강은 조사 안 해?"  맞는 지적이었다 -- 거짓 초록에는 저장소를 훑는
# 사냥이 있는데, 거짓 빨강은 변형 하나 단위로 **막기만** 하고 찾아다니지 않았다.
#
# 빨강이 거짓인 꼴을 셋으로 가른다. 전부 실행으로 가린다(예외 이름으로 짐작하지 않는다).
#
#   상태오염   깨끗한 판에서 한 번은 초록인데 **두 번째에 빨강**    -> 제 상태를 지우거나 덧쓴다
#   환경의존   깨끗한 판에서는 빨강인데 **작업 트리에서는 초록**   -> 추적 안 되는 파일·캐시에 매여 있다
#   원래빨강   둘 다 빨강                                        -> 거짓이 아니다. 진짜 빨강(고쳐야 한다)
#
# 표본이 이미 눈앞에 있었다: CI 의 `test_law_hwp`(권한 -- 환경의존) · 이 컨테이너의
# `test_compression_judge`(활성화 캐시 없음 -- 환경의존) · Case D 표본(두 번 돌리면 빨강 -- 상태오염).
# 순서 의존(혼자면 초록인데 묶어 돌리면 빨강)은 **안 잰다** -- 전체 묶음을 여러 벌 돌려야 해서 비싸다.
멀쩡 = "Clean"
상태오염 = "StatePollution"
환경의존 = "EnvDependent"
원래빨강 = "TrueRed"
# **실측 2026-09-13 (D_0):** FR 사냥이 `진짜빨강 5` 를 보고했는데, 같은 판에서 다시 재 보니 넷은
# 초록이고(이 컨테이너) 하나(`tests/test_precheck.py`)는 **시한을 넘긴 것**이었다. 시한을 넘긴 것은
# 빨간 것이 아니라 **재지 못한 것**이다. 그것을 "고쳐야 할 빨강" 으로 적으면 이 저장소가 오늘 배운
# 바로 그 잘못이 된다 -- **재지 않은 것을 빨강이라 하지 마라.**
시한초과 = "Timeout"
시한넘김표 = "Timeout"


def 거짓빨강사냥(repo=None, 검사들: "list[str]" = None, 시한초: int = 기본시한초,
            말하기=None, 작업트리도: bool = True, 씨앗: int = 기본씨앗) -> dict:
    """**빨강이 거짓인 검사를 찾는다.** {잰것, 상태오염, 환경의존, 원래빨강, 멀쩡, 못잼, 찾은것}.

    깨끗한 HEAD 판에서 검사마다 **두 번** 돌린다(같은 판, 사이에 되돌림 없이). 그리고 빨강이면
    작업 트리에서도 한 번 돌려 견준다. 판정은 전부 끝값이다.

    이 사냥이 왜 필요한가: 거짓 빨강은 **거짓 초록을 낳는다.** 오늘 실측 -- 절제검사가 데이터 파일을
    안 옮겨 빨개진 것을 "검사가 기능을 본다" 로 읽어 PR #218 을 통과시켰다. 그리고 `ci_watch` 가
    취소를 빨강으로 세어 **모든 자가 커밋을 막았다.** 막힌 것은 아무것도 못 고친다."""
    repo = Path(repo or REPO)
    말 = 말하기 or (lambda s: print(s, flush=True))
    시작 = time.monotonic()
    if 검사들 is None:
        import random
        검사들 = sorted(f"tests/{x.name}" for x in (repo / "tests").glob("test_*.py"))
        random.Random(씨앗).shuffle(검사들)          # π0 -- 시한에 잘려도 치우치지 않게
    out = {"잰것": 0, 멀쩡: 0, 상태오염: 0, 환경의존: 0, 원래빨강: 0, 시한초과: 0,
           "못잼": 0, "찾은것": []}
    판 = Path(tempfile.mkdtemp(prefix="se-FR-"))
    r = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(판), "HEAD"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        out["못잼"] += 1
        말(f"[거짓빨강] HEAD 판을 못 꺼냈다: {r.stderr.strip()[:120]}")
        return out
    적기(repo, {"꼴": "FR사냥시작", "검사수": len(검사들), "시한초": 시한초,
              "정책": {"이름": "pi0", "검사": "uniform(전수, 섞음)", "seed": 씨앗}})
    try:
        for t in 검사들:
            if time.monotonic() - 시작 > 시한초:
                out["못잼"] += len(검사들) - out["잰것"]
                말(f"[거짓빨강] 시한 {시한초}초 -- 멈춘다 (못 잰 것 {len(검사들) - out['잰것']}개)")
                break
            if not (판 / t).is_file():
                continue
            검사때 = time.monotonic()
            깨끗하게(판)
            첫빨강, _어디1, 첫글 = _돌려보기(판, [t])
            둘빨강, _어디2, 둘글 = _돌려보기(판, [t])          # 되돌리지 않는다 -- 제 상태가 남았나 본다
            out["잰것"] += 1
            if 첫빨강 and 첫글.strip() == 시한넘김표:
                out["못잼"] += 1
                out[시한초과] = out.get(시한초과, 0) + 1
                적기(repo, {"꼴": "거짓빨강", "검사": t, "test": t, "classification": 시한초과,
                          "cost": {"초": round(time.monotonic() - 검사때, 2)},
                          "baseline_pass": None, "repeat_fail": None, "worktree_pass": None,
                          "cause": f"{검사시한초}초 안에 안 끝났다",
                          "failure_cause": f"{검사시한초}초 안에 안 끝났다 -- **빨강이 아니라 못 잰 것이다**"})
                말(f"[거짓빨강] {시한초과} {t} -- {검사시한초}초를 넘겼다. 빨강이라 하지 않는다(못잼)")
                continue
            if not 첫빨강 and not 둘빨강:
                out[멀쩡] += 1
                # **멀쩡도 적는다** -- 이것이 없으면 한 번 FR 로 찍힌 검사가 고쳐져도 영영 제외된다.
                # 복구도 측정으로 한다(U_t = (U_{t-1} \ Clean_t) ∪ FR_t).
                적기(repo, {"꼴": "거짓빨강", "검사": t, "test": t, "classification": 멀쩡,
                          "cost": {"초": round(time.monotonic() - 검사때, 2)},
                          "baseline_pass": True, "repeat_fail": False, "worktree_pass": None,
                          "cause": "", "failure_cause": ""})
                continue
            if not 첫빨강 and 둘빨강:
                _외부, 까닭 = 실패원인(둘글)
                out[상태오염] += 1
                것 = {"검사": t, "분류": 상태오염, "까닭": 까닭, "꼬리": 둘글[-300:]}
                out["찾은것"].append(것)
                적기(repo, {"꼴": "거짓빨강", "검사": t, "test": t, "classification": 상태오염,
                          "cost": {"초": round(time.monotonic() - 검사때, 2)},
                          "baseline_pass": True, "repeat_fail": True, "worktree_pass": None,
                          "cause": 까닭, "failure_cause": 까닭, "traceback": 둘글[-400:]})
                말(f"[거짓빨강] **{상태오염}** {t} -- 두 번째에 빨강 ({까닭})")
                continue
            작업빨강 = None
            if 작업트리도:
                작업빨강, _어디3, _작업글 = _돌려보기(repo, [t])
            _외부, 까닭 = 실패원인(첫글)
            if 작업빨강 is False:
                out[환경의존] += 1
                것 = {"검사": t, "분류": 환경의존, "까닭": 까닭, "꼬리": 첫글[-300:]}
                out["찾은것"].append(것)
                적기(repo, {"꼴": "거짓빨강", "검사": t, "test": t, "classification": 환경의존,
                          "cost": {"초": round(time.monotonic() - 검사때, 2)},
                          "baseline_pass": False, "repeat_fail": True, "worktree_pass": True,
                          "cause": 까닭, "failure_cause": 까닭, "traceback": 첫글[-400:]})
                말(f"[거짓빨강] **{환경의존}** {t} -- 깨끗한 판에서만 빨강 ({까닭})")
            else:
                out[원래빨강] += 1
                적기(repo, {"꼴": "거짓빨강", "검사": t, "test": t, "classification": 원래빨강,
                          "cost": {"초": round(time.monotonic() - 검사때, 2)},
                          "baseline_pass": False, "repeat_fail": bool(둘빨강),
                          "worktree_pass": (False if 작업빨강 else None),
                          "cause": 까닭, "failure_cause": 까닭, "traceback": 첫글[-400:]})
                말(f"[거짓빨강] {원래빨강} {t} -- 둘 다 빨강이다. 거짓이 아니다 ({까닭})")
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(판)],
                       capture_output=True, text=True)
        shutil.rmtree(판, ignore_errors=True)
    적기(repo, {"꼴": "FR사냥끝", **{k: v for k, v in out.items() if k != "찾은것"}})
    return out


def 못믿을검사들(repo=None) -> "list[str]":
    r"""**FR 이력이 있는 검사.** ReliableTest = RG0 ∧ ¬FR이력 -- RG0 통과는 신뢰성이 아니다.

    사용자(2026-09-12): "RG0 PASS 와 검사 신뢰성을 혼동하지 마라." 상태오염 검사는 **첫 실행이
    초록이므로 RG0 를 지난다.** 그래도 바탕으로 쓸 수 없다 -- 그 초록이 두 번째에 무너진다. 그래서
    신뢰성은 원장의 FR 이력으로 판단한다(이 함수), RG0 로 판단하지 않는다.

    **마지막 관측이 이긴다.** 누적이지만 단조(monotone)는 아니다:

        U_t = (U_{t-1} \ Clean_t) ∪ FR_t

    순수 누적이면 고친 검사가 **영영** 제외되고, 그 파일을 다시는 못 잰다. 나중 사냥이 그 검사를
    `멀쩡` 으로 관측하면 빠져나온다 -- 복구도 측정으로 한다. 진짜빨강은 여기 안 넣는다(거짓이 아니다).
    RG0 가 알아서 막는다."""
    마지막: dict = {}
    for x in 원장읽기(repo):
        if x.get("꼴") == "거짓빨강":
            이름 = str(x.get("test") or x.get("검사") or "")
            if 이름:
                마지막[이름] = x.get("classification")
    # 시한초과도 넣는다 -- **바탕으로 쓸 수 없다**(RG0 가 시한을 넘기면 그 파일을 통째로 못 잰다).
    # 진짜빨강은 안 넣는다(거짓이 아니다). RG0 가 알아서 막는다.
    return sorted(k for k, v in 마지막.items() if v in (상태오염, 환경의존, 시한초과))


def FR보고(repo=None) -> str:
    행들 = [x for x in 원장읽기(repo) if x.get("꼴") in ("거짓빨강", "FR사냥끝")]
    끝 = [x for x in 행들 if x.get("꼴") == "FR사냥끝"]
    것 = [x for x in 행들 if x.get("꼴") == "거짓빨강"]
    줄 = [f"**거짓 빨강 사냥** -- 원장 {len(것)}줄 · 사냥 {len(끝)}번"]
    if 끝:
        마 = 끝[-1]
        줄.append(f"마지막: 검사 {마.get('잰것', 0)}개 · 멀쩡 {마.get(멀쩡, 0)} · "
                  f"**상태오염 {마.get(상태오염, 0)}** · **환경의존 {마.get(환경의존, 0)}** · "
                  f"진짜빨강 {마.get(원래빨강, 0)} · 시한초과 {마.get(시한초과, 0)} · "
                  f"못잼 {마.get('못잼', 0)}")
    거짓 = [x for x in 것 if x.get("classification") in (상태오염, 환경의존)]
    if 거짓:
        줄.append(f"\n**거짓 빨강 {len(거짓)}개** (그 빨강은 검사 대상의 잘못이 아니다):")
        for x in 거짓[-12:]:
            줄.append(f"  [{x.get('classification')}] {x.get('검사')} -- {str(x.get('failure_cause'))[:60]}")
    진짜 = [x for x in 것 if x.get("classification") == 원래빨강]
    if 진짜:
        줄.append(f"\n진짜 빨강 {len(진짜)}개 (고쳐야 한다): "
                  + ", ".join(str(x.get("검사")) for x in 진짜[-8:]))
    늦 = [x for x in 것 if x.get("classification") == 시한초과]
    if 늦:
        줄.append(f"\n시한초과 {len(늦)}개 (**빨강이 아니다 -- 못 쟀다**): "
                  + ", ".join(str(x.get("검사")) for x in 늦[-8:]))
    if not 것:
        줄.append("아직 안 돌렸다 -- `python3 mutate.py --거짓빨강` 또는 `!거짓빨강`")
    return "\n".join(줄)


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


# ------------------------------------------------------------------ 추적되는 요약 (D_0 를 남긴다)
# **실측 2026-09-13:** 6시간 사냥이 끝났는데 **나는 그 숫자를 볼 수 없었다.** 원장은
# `logs/거짓초록.jsonl` 이고 `logs/` 는 .gitignore 에 들어 있다 -- VM 에만 있고 저장소에는 없다.
# 그래서 사용자가 Discord 출력을 손으로 붙여 줘야 D_0 가 여기 닿았고, `judge.py` 는 이 컨테이너에서
# 늘 `관찰파일수 0` 을 본다(원장이 없으니 관찰이 없다고 읽는다).
#
#   원장은 크고 사사롭다 -> 안 추적한다.  **요약은 작고 비교 가능하다 -> 추적한다.**
#
# D_t 가 git 에 남으면 D_0 -> D_1 의 차이(ΔJ)를 사람 손을 안 거치고 잴 수 있다. 그것이 π 갱신의 재료다.
요약경로 = "falsegreen/요약.jsonl"


def 요약(repo=None) -> dict:
    r"""원장 전체를 **작은 한 줄**로 줄인다.

    **점수만 남기면 안 된다**(사용자 2026-09-13). `Killed/(Killed+FG)` 는 *가른 것들 중* 잡은 비율이라,
    **분모 자체가 줄어도 오른다.**

        D_0: Killed 90 · FG 10 -> 0.90   (잰변형 100)
        D_1: Killed 95 · FG  5 -> 0.95   (잰변형 100)  -> 검사가 좋아졌다
        D_1: Killed 95 · FG  5 -> 0.95   (잰변형  20)  -> **아무것도 증명하지 않는다**

    둘은 점수가 같다. 가른 수가 다르다. 그래서 **표본이 같이 남아야** ΔJ 를 말할 수 있다 --
    잰변형 · 못잼 · 동등 · 거짓빨강 · 못쓸 · 시한초과 · 안덮임 · 약한단언 · 파일수 · 함수수 ·
    검사수 · 시한초 · 씨앗 · 정책. 그리고 견줄 수 있는지는 `견줄수있나` 가 따로 판정한다.
    """
    repo = Path(repo or REPO)
    행들 = 원장읽기(repo)
    분류: dict = {}
    연산자: dict = {}
    파일: dict = {}
    칸들: dict = {}                                   # (파일|연산자) -- 짝지어 견주는 단위
    함수들, 쟨파일들 = set(), set()
    왜 = {"not_covered": 0, "weak_assertion": 0, "baseline_unstable": 0, "env_changed": 0}
    for x in 행들:
        c = x.get("classification")
        if c:
            분류[c] = 분류.get(c, 0) + 1
        m, 결 = x.get("operator"), x.get("outcome")
        # **변형 줄에는 "파일" 칸이 없다** -- `target` 이 "파일:함수" 꼴이다(실측: 이것을 안 풀어서
        # 요약의 파일별 셈이 늘 비어 있었다 -- 죽은 측정이었다).
        rel = x.get("파일") or x.get("file") or (str(x.get("target") or "").split(":")[0] or None)
        함수 = (str(x.get("target") or "").split(":", 1) + [""])[1] or x.get("함수")
        if x.get("why") in 왜:
            왜[x["why"]] += 1
        if m:
            칸 = 연산자.setdefault(m, {"잰것": 0, 잡힘: 0, 살아남음: 0, 동등: 0, 거짓빨강결과: 0,
                                    못쓸: 0, "초": 0.0})
            칸["잰것"] += 1
            if 결 in 칸:
                칸[결] += 1
            칸["초"] = round(칸["초"] + float(((x.get("cost") or {}).get("초") or 0)), 2)
            if rel:
                쟨파일들.add(rel)
                키 = f"{rel}|{m}"
                셀 = 칸들.setdefault(키, {"잰것": 0, 잡힘: 0, 살아남음: 0})
                셀["잰것"] += 1
                if 결 in 셀:
                    셀[결] += 1
            if 함수:
                함수들.add(f"{rel}:{함수}")
        if rel and 결 in (잡힘, 살아남음):
            파일.setdefault(rel, {잡힘: 0, 살아남음: 0})[결] += 1
    잡 = sum(v[잡힘] for v in 연산자.values())
    산 = sum(v[살아남음] for v in 연산자.values())
    동 = sum(v[동등] for v in 연산자.values())
    가빨 = sum(v[거짓빨강결과] for v in 연산자.values())
    무효 = sum(v[못쓸] for v in 연산자.values())
    끝 = 마지막사냥(repo)
    시작줄 = next((x for x in reversed(행들) if x.get("꼴") == "사냥시작"), {})
    병렬줄 = next((x for x in reversed(행들) if x.get("꼴") == "병렬시작"), {})
    FR끝 = next((x for x in reversed(행들) if x.get("꼴") == "FR사냥끝"), {})
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True)
    return {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "판": (r.stdout or "").strip(),
            "줄수": len(행들),
            "사냥끝": bool(끝),
            # ---- 표본: **점수보다 먼저 읽을 것들.** 이것이 없으면 점수는 견줄 수 없다.
            "잰변형": 잡 + 산 + 동 + 가빨 + 무효,
            "Killed": 잡, "FG": 산, "동등": 동, "거짓빨강": 가빨, "못쓸": 무효,
            "시한초과": 분류.get(시한초과, 0),
            "못쓸바탕": 분류.get(못쓸바탕, 0),
            # **잰변형 = Killed + FG + 못잼** 이 성립해야 분모에서 빠진 수를 숨기지 않는다.
            # 바탕 쪽에서 못 잰 것(시한초과·못쓸바탕)은 변형 셈이 아니므로 따로 둔다.
            "못잼": 동 + 가빨 + 무효,
            "바탕못잼": 분류.get(시한초과, 0) + 분류.get(못쓸바탕, 0),
            "안덮임": 왜["not_covered"], "약한단언": 왜["weak_assertion"],
            "파일수": len(쟨파일들), "함수수": len(함수들),
            "검사수": FR끝.get("잰것", 0),
            "시한초": 시작줄.get("시한초"), "씨앗": (시작줄.get("정책") or {}).get("seed"),
            # **일꾼 수도 표본의 조건이다** -- 코어를 나눠 쓰면 느려져 시한초과가 늘 수 있다.
            "일꾼": 병렬줄.get("일꾼", 1),
            "정책": 병렬줄.get("정책") or 시작줄.get("정책") or {},
            # ---- 점수: 가를 수 있었던 것만 분모로 쓴다. **홀로 읽으면 안 된다.**
            "점수": round(잡 / (잡 + 산), 4) if (잡 + 산) else None,
            "분류": 분류, "연산자": 연산자,
            "파일": dict(sorted(파일.items(), key=lambda kv: -kv[1][살아남음])[:40]),
            "칸": 칸들,
            # **`동등 0` 을 혼자 믿지 않는다** -- 장치가 죽어서 0 인지 같이 적는다.
            "동등장치": 동등장치살았나()[0],
            "못믿을검사": sorted(못믿을검사들(repo))}


def 요약적기(repo=None) -> dict:
    """요약을 **추적되는 경로**에 덧붙인다. 덧붙이기만 -- D_0 를 지우고 D_1 을 쓰지 않는다."""
    repo = Path(repo or REPO)
    줄 = 요약(repo)
    p = repo / 요약경로
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")
    return 줄


def 요약들(repo=None) -> "list[dict]":
    p = Path(repo or REPO) / 요약경로
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


# ------------------------------------------------------------------ 견줄 수 있나 (ΔJ 의 전제)
# 사용자(2026-09-13): "FG 숫자가 줄었다고 해서 검사가 좋아졌다고 단정할 수 없다. D_0 가 100개를
# 재고 D_1 이 20개를 쟀다면 점수 0.90 -> 0.95 는 아무것도 증명하지 않는다."
#
# 맞다. 그래서 **ΔJ 를 내기 전에 견줄 수 있는지를 먼저 판정한다.** 그리고 견줄 수 있을 때도
# 전체 점수를 빼지 않는다 -- **두 판이 똑같이 잰 칸에서만** 빼고, 그 칸 수를 같이 적는다.
#
#   칸 = (파일, 연산자).  공통칸 = 두 판이 다 잰 칸.
#   Δ점수 = 점수(b | 공통칸) - 점수(a | 공통칸)
#
# 이것이 표본 크기에 휘둘리지 않는 유일한 꼴이다. 공통칸이 없으면 **모른다고 답한다**(None).
견줄최소비 = 0.5                 # 공통칸에서 잰 수가 한쪽이 다른 쪽의 절반도 안 되면 견주지 않는다


def _칸점수(요약줄: dict, 칸키들) -> "tuple[int, int, float | None]":
    """그 칸들에서의 (Killed, FG, 점수)."""
    칸 = 요약줄.get("칸") or {}
    잡 = sum((칸.get(k) or {}).get(잡힘, 0) for k in 칸키들)
    산 = sum((칸.get(k) or {}).get(살아남음, 0) for k in 칸키들)
    return 잡, 산, (round(잡 / (잡 + 산), 4) if (잡 + 산) else None)


def 견줄수있나(앞: dict, 뒤: dict) -> "tuple[bool, list]":
    """두 요약을 견줄 수 있나. (그런가, 안 되는 까닭들).

    **모르는 것은 안 된 것으로 다룬다** -- 여기서 봐주면 점수가 표본 축소를 개선으로 읽는다."""
    왜 = []
    if not (앞 and 뒤):
        return False, ["요약이 둘 다 있어야 한다"]
    if not (앞.get("사냥끝") and 뒤.get("사냥끝")):
        왜.append("한쪽이 사냥을 끝내지 않았다 -- 시한에 잘린 표본은 치우쳐 있다")
    if 앞.get("씨앗") is not None and 뒤.get("씨앗") is not None and 앞["씨앗"] != 뒤["씨앗"]:
        왜.append(f"씨앗이 다르다 ({앞['씨앗']} vs {뒤['씨앗']}) -- 표본 자체가 다른 추출이다")
    앞칸, 뒤칸 = set(앞.get("칸") or {}), set(뒤.get("칸") or {})
    공통 = sorted(앞칸 & 뒤칸)
    if not 공통:
        왜.append("두 판이 같이 잰 칸이 하나도 없다")
        return False, 왜
    # **표본이 얼마나 줄었나** -- 한쪽이 100칸을 재고 다른 쪽이 10칸을 쟀으면, 그 10칸의 점수가
    # 올랐다는 것이 "검사가 좋아졌다" 는 뜻이 아니다. 그것은 **덜 쟀다**는 뜻일 수도 있다.
    덮임 = len(공통) / max(len(앞칸), len(뒤칸))
    if 덮임 < 견줄최소비:
        왜.append(f"공통칸이 너무 적다 ({len(공통)}칸 / 앞 {len(앞칸)} · 뒤 {len(뒤칸)} = {덮임:.0%}) -- "
                 f"{견줄최소비:.0%} 아래면 점수 차가 표본 차일 수 있다")
    a잡, a산, _ = _칸점수(앞, 공통)
    b잡, b산, _ = _칸점수(뒤, 공통)
    큰, 작 = max(a잡 + a산, b잡 + b산), min(a잡 + a산, b잡 + b산)
    if 큰 and 작 / 큰 < 견줄최소비:
        왜.append(f"공통칸 안에서도 잰 수가 너무 다르다 ({a잡 + a산} vs {b잡 + b산})")
    return (not 왜), 왜


def 점수차(앞: dict, 뒤: dict) -> dict:
    """**공통칸에서만** 점수를 뺀다. 견줄 수 없으면 Δ 를 내지 않는다(None).

    돌려주는 것: {견줄수있나, 까닭, 공통칸수, 앞점수, 뒤점수, Δ, 앞잰것, 뒤잰것}"""
    됨, 왜 = 견줄수있나(앞, 뒤)
    공통 = sorted(set((앞 or {}).get("칸") or {}) & set((뒤 or {}).get("칸") or {}))
    a잡, a산, a점 = _칸점수(앞 or {}, 공통)
    b잡, b산, b점 = _칸점수(뒤 or {}, 공통)
    return {"견줄수있나": 됨, "까닭": 왜, "공통칸수": len(공통),
            "앞점수": a점, "뒤점수": b점,
            "앞잰것": a잡 + a산, "뒤잰것": b잡 + b산,
            "Δ": (round(b점 - a점, 4) if (됨 and a점 is not None and b점 is not None) else None)}


def 요약보고(repo=None) -> str:
    """D_0 -> D_1 -> ... 를 한눈에. **점수가 오르고 있나**를 사람이 읽는 자리."""
    것 = 요약들(repo)
    if not 것:
        return f"{요약경로} 가 비어 있다 -- `python3 mutate.py --요약적기` 로 한 줄 남겨라"
    줄 = [f"{'때':17} {'판':9} {'잰변형':>6} {'Killed':>6} {'FG':>4} {'못잼':>4} "
         f"{'안덮임':>5} {'파일':>4} {'점수':>6} {'끝':>2}"]
    for x in 것[-12:]:
        점 = x.get("점수")
        줄.append(f"{str(x.get('때'))[:16]:17} {str(x.get('판')):9} {x.get('잰변형', 0):>6} "
                  f"{x.get('Killed', 0):>6} {x.get('FG', 0):>4} {x.get('못잼', 0):>4} "
                  f"{x.get('안덮임', 0):>5} {x.get('파일수', 0):>4} "
                  f"{(f'{점:.3f}' if 점 is not None else '--'):>6} {'o' if x.get('사냥끝') else 'x':>2}")
    # **점수만 빼지 않는다.** 분모가 줄어도 점수는 오른다 -- 공통칸에서만 빼고, 견줄 수 없으면 안 뺀다.
    if len(것) >= 2:
        d = 점수차(것[-2], 것[-1])
        if d["Δ"] is None:
            줄.append(f"\n**Δ 를 내지 않는다** (공통칸 {d['공통칸수']}개 · "
                      f"{d['앞잰것']} vs {d['뒤잰것']}개 쟀다): " + "; ".join(d["까닭"] or ["모르겠다"]))
            줄.append("모르는 것은 안 된 것으로 다룬다 -- 표본이 줄어든 것을 개선으로 읽지 않는다.")
        else:
            줄.append(f"\n**Δ점수 {d['Δ']:+.4f}** -- 공통칸 {d['공통칸수']}개에서만 쟀다 "
                      f"({d['앞점수']} -> {d['뒤점수']} · {d['앞잰것']} vs {d['뒤잰것']}개). "
                      "전체 점수를 뺀 것이 아니다.")
    마 = 것[-1]
    줄.append(f"\n마지막 표본: 잰변형 {마.get('잰변형', 0)} = Killed {마.get('Killed', 0)} + "
              f"FG {마.get('FG', 0)} + 못잼 {마.get('못잼', 0)}"
              f"(동등 {마.get('동등', 0)} · 거짓빨강 {마.get('거짓빨강', 0)} · 못쓸 {마.get('못쓸', 0)})"
              f" · 바탕못잼 {마.get('바탕못잼', 0)}"
              f"(시한초과 {마.get('시한초과', 0)} · 못쓸바탕 {마.get('못쓸바탕', 0)})")
    if 마.get("동등", 0) == 0:
        살, 말 = 동등장치살았나()
        줄.append(f"  동등 0 -- 장치 탐침 {'통과' if 살 else '**실패**'}: {말}")
        줄.append("  **TCE 는 바이트코드가 같을 때만 잡는다.** `a+0 -> a-0` 같은 등가는 안 잡혀 FG 로 "
                  "센다 -- 그래서 **FG 는 상한이고 점수는 하한이다.**")
    줄.append(f"  FG 가운데 안덮임 {마.get('안덮임', 0)} · 약한단언 {마.get('약한단언', 0)} "
              f"-- 안덮임은 단언이 약한 것이 아니라 **그 줄이 아예 안 돈다**는 뜻이다")
    줄.append(f"  파일 {마.get('파일수', 0)} · 함수 {마.get('함수수', 0)} · 검사 {마.get('검사수', 0)} · "
              f"시한 {마.get('시한초')}초 · 씨앗 {마.get('씨앗')} · 일꾼 {마.get('일꾼', 1)}")
    return "\n".join(줄)


def 파일별거짓초록(repo=None, 파일들: "list[str]" = None) -> "list[dict]":
    """원장에 남은 FALSE_GREEN 중 그 파일들에 걸린 것. commit_guard 가 커밋 범위로 좁힐 때 쓴다."""
    것 = [x for x in 원장읽기(repo) if x.get("classification") == 거짓초록]
    if 파일들 is None:
        return 것
    고른 = set(파일들)
    return [x for x in 것 if str(x.get("target", "")).split(":")[0] in 고른]


def 둘다사냥(repo=None, 시한초: int = 기본시한초, 파일들: "list[str]" = None,
         말하기=None, FR몫: float = 0.25, 씨앗: int = 기본씨앗, 일꾼: int = 1) -> dict:
    """**거짓 빨강을 먼저, 거짓 초록을 그다음.** {FR, FG, 말}

    순서가 중요하다 -- 환경 때문에 빨간 검사는 FG 사냥의 **바탕을 무효로 만든다**(T(P)=PASS 가 깨지면
    변형 결과로 아무것도 판정할 수 없다: INVALID_BASELINE). 그러므로 어느 검사를 바탕으로 쓸 수 없는지
    먼저 알아야 초록 사냥이 뜻을 가진다. 시한을 FR몫(기본 1/4)만큼 앞에 주고 나머지를 FG 에 준다."""
    repo = Path(repo or REPO)
    말 = 말하기 or (lambda s: print(s, flush=True))
    FR시한 = max(60, int(시한초 * FR몫))
    말(f"[사냥] 1/2 거짓 빨강 -- 시한 {FR시한}초")
    fr = 거짓빨강사냥(repo, 시한초=FR시한, 말하기=말하기, 씨앗=씨앗)
    # **이번 것과 원장의 누적을 합친다** -- U_t = (U_{t-1} \ Clean_t) ∪ FR_t.
    # 이번 호출 것만 쓰면 구멍이 난다: FR 에 시한의 일부만 주므로 **다 못 훑으면 못 닿은 검사가
    # 조용히 신뢰받는다**(검사 186개 · FR 시한 1/4). 누적이면 지난 사냥이 찍어 둔 것이 계속 빠진다.
    이번것 = [x["검사"] for x in fr["찾은것"] if x["분류"] in (상태오염, 환경의존)]
    못믿을검사 = sorted(set(이번것) | set(못믿을검사들(repo)))
    if 못믿을검사:
        말(f"[사냥] 바탕으로 쓸 수 없는 검사 {len(못믿을검사)}개"
          f"(이번에 찾은 것 {len(이번것)}개 + 원장 누적): {', '.join(못믿을검사[:4])}")
    FG시한 = max(60, 시한초 - FR시한)
    말(f"[사냥] 2/2 거짓 초록 -- 시한 {FG시한}초"
      + (f" · 바탕에서 뺀 검사 {len(못믿을검사)}개" if 못믿을검사 else ""))
    # 일꾼 2 이상이면 파일을 나눠 동시에 잰다. **FR 은 순차로 둔다** -- 검사를 두 번 돌려
    # 상태오염을 보는 판정이라, 같이 돌리면 서로가 그 '두 번째' 가 된다.
    fg = (병렬사냥(repo, 시한초=FG시한, 일꾼=일꾼, 파일들=파일들, 말하기=말하기,
                뺄검사=못믿을검사, 씨앗=씨앗) if (일꾼 or 0) > 1
          else 사냥(repo, 파일들=파일들, 시한초=FG시한, 말하기=말하기, 뺄검사=못믿을검사, 씨앗=씨앗))
    적기(repo, {"꼴": "둘다끝", "FR": {k: v for k, v in fr.items() if k != "찾은것"},
              "FG": {k: v for k, v in fg.items() if k not in ("살아남은것", "덮이지않은것")},
              "못믿을검사": 못믿을검사[:12]})
    return {"FR": fr, "FG": fg, "못믿을검사": 못믿을검사, "이번에찾은것": 이번것,
            "말": (f"거짓빨강 {fr[상태오염] + fr[환경의존]}개(상태오염 {fr[상태오염]} · 환경의존 {fr[환경의존]}) · "
                  f"거짓초록 {fg.get(거짓초록, 0)}개 · 잡힘 {fg.get(유효빨강, 0)} · "
                  f"동등 {fg.get(동등변형, 0)} · 못쓸 {fg.get(못쓸변형, 0)}")}


def 연산자표(repo=None) -> str:
    """**연산자마다 무엇을 얼마에 찾았나.** π 의 보상식 R(m) = αFG + βFR + γΔJ - λCost 의 재료를
    그대로 읽게 한다(여기서 보상을 계산하지는 않는다 -- 그것은 π 의 몫이다)."""
    셈: dict = {}
    for x in 원장읽기(repo):
        m = x.get("operator")
        if not m:
            continue
        c = 셈.setdefault(m, {"잰것": 0, 잡힘: 0, 살아남음: 0, 동등: 0, 거짓빨강결과: 0, 못쓸: 0, "초": 0.0})
        c["잰것"] += 1
        결 = x.get("outcome")
        if 결 in c:
            c[결] += 1
        c["초"] += float(((x.get("cost") or {}).get("초") or 0))
    if not 셈:
        return "연산자 기록이 없다 -- `!거짓초록` 을 한 번 돌려라"
    줄 = [f"{'연산자':14} {'잰것':>5} {'FG':>4} {'Killed':>7} {'동등':>5} {'FR':>4} {'못쓸':>5} {'초/개':>7}"]
    for m, c in sorted(셈.items(), key=lambda kv: -kv[1][살아남음]):
        줄.append(f"{m:14} {c['잰것']:>5} {c[살아남음]:>4} {c[잡힘]:>7} {c[동등]:>5} "
                  f"{c[거짓빨강결과]:>4} {c[못쓸]:>5} {(c['초'] / max(1, c['잰것'])):>7.1f}")
    return "\n".join(줄)


def 둘다보고(repo=None) -> str:
    return FR보고(repo) + "\n\n" + 보고(repo) + "\n\n**연산자별** (π 의 재료)\n" + 연산자표(repo)


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
    ap.add_argument("--거짓빨강", action="store_true", help="빨강이 거짓인 검사를 찾는다(변형 안 함)")
    ap.add_argument("--FR보고", action="store_true", help="거짓 빨강 원장 요약")
    ap.add_argument("--둘다", action="store_true", help="거짓 빨강 -> 거짓 초록 (한 번에)")
    ap.add_argument("--씨앗", type=int, default=기본씨앗, help=f"π0 의 고정 씨앗 (기본 {기본씨앗})")
    ap.add_argument("--요약적기", action="store_true",
                    help=f"원장을 한 줄로 줄여 {요약경로}(추적됨) 에 덧붙인다")
    ap.add_argument("--요약보고", action="store_true", help="D_0 -> D_1 -> ... 점수 추이")
    ap.add_argument("--일꾼", type=int, default=1,
                    help="파일을 나눠 동시에 잰다 (0=코어수-1, 1=순차). 판정은 바뀌지 않아야 한다")
    ap.add_argument("--저장소", default=None, help="이 저장소를 잰다 (일꾼이 쓴다)")
    ap.add_argument("--원장이름", default=None, help="원장 경로를 갈아끼운다 (일꾼이 쓴다)")
    ap.add_argument("--뺄검사", action="append", default=None, help="바탕에서 뺄 검사 (일꾼이 쓴다)")
    a = ap.parse_args(argv)
    global 원장상대, REPO
    if a.원장이름:
        원장상대 = a.원장이름                      # 일꾼마다 제 원장에 쓴다 -- 덧붙이기가 섞여 찢기지 않게
    if a.저장소:
        REPO = Path(a.저장소)
    if a.요약보고:
        print(요약보고())
        return 0
    if a.요약적기:
        줄 = 요약적기()
        print(f"{요약경로} 에 남겼다 -- 잰변형 {줄['잰변형']} · Killed {줄['Killed']} · FG {줄['FG']} "
              f"· 점수 {줄['점수']}")
        return 0
    if a.FR보고:
        print(FR보고())
        return 0
    if a.둘다:
        r = 둘다사냥(시한초=a.시한, 파일들=a.파일, 씨앗=a.씨앗, 일꾼=a.일꾼)
        요약적기()                                  # D_t 를 추적되는 자리에 남긴다
        print()
        print(둘다보고())
        return 1 if (r["FR"][상태오염] or r["FR"][환경의존] or r["FG"].get(거짓초록, 0)) else 0
    if a.거짓빨강:
        r = 거짓빨강사냥(시한초=a.시한, 검사들=a.파일, 씨앗=a.씨앗)
        print()
        print(FR보고())
        return 1 if (r[상태오염] or r[환경의존]) else 0
    if a.보고:
        print(보고())
        return 0
    r = (병렬사냥(시한초=a.시한, 일꾼=a.일꾼, 파일들=a.파일, 함수상한=a.함수상한,
                뺄검사=a.뺄검사, 씨앗=a.씨앗) if (a.일꾼 or 0) != 1
         else 사냥(파일들=a.파일, 시한초=a.시한, 함수상한=a.함수상한, 뺄검사=a.뺄검사, 씨앗=a.씨앗))
    if not a.원장이름:                              # 일꾼은 요약을 안 적는다 -- 부모가 합친 뒤에 적는다
        요약적기()
    print()
    print(보고())
    return 1 if r["살아남음"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
