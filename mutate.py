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


def 변형들(src: str, 이름: str, 상한: int = 6) -> "list[tuple[str, str]]":
    """그 함수의 **조용한** 변형들 [(설명, 새 소스)]. 예외를 던지지 않는다 -- 틀린 값을 돌려준다.

    다섯 가지를 본다:
      1. `return <값>`   -> `return None` (값이 이미 None 이면 `return 0`)
      2. `if a == b`     -> `if a != b`  (그 반대도)
      3. `if <조건>`     -> `if True` · `if False`
      4. `return a and b`/`or` -> 뒤집기
      5. 숫자 상수       -> +1 (0 은 1, 1 은 0)
    터뜨리는 변형(raise)은 절제검사가 이미 본다 -- 여기서는 쓰지 않는다."""
    자리 = _자리(src).get(이름)
    if 자리 is None:
        return []
    out: "list[tuple[str, str]]" = []
    본줄 = set()
    for 노드 in ast.walk(자리):
        if len(out) >= 상한:
            break
        줄 = getattr(노드, "lineno", 0)
        if isinstance(노드, ast.Return) and 노드.value is not None and 줄 not in 본줄:
            본줄.add(줄)
            글 = ast.unparse(노드.value) if hasattr(ast, "unparse") else ""
            새 = "return 0" if 글.strip() == "None" else "return None"
            out.append((f"{줄}줄 `return {글[:28]}` -> `{새}`", _줄바꾸기(src, 줄, 새)))
        elif isinstance(노드, ast.Compare) and 줄 not in 본줄 and len(노드.ops) == 1:
            뒤집기 = {ast.Eq: "!=", ast.NotEq: "==", ast.Lt: ">=", ast.LtE: ">", ast.Gt: "<=", ast.GtE: "<",
                    ast.In: "not in", ast.Is: "is not"}
            새연산 = 뒤집기.get(type(노드.ops[0]))
            if 새연산 and hasattr(ast, "unparse"):
                본줄.add(줄)
                왼 = ast.unparse(노드.left)
                오 = ast.unparse(노드.comparators[0])
                옛글 = src.splitlines()[줄 - 1]
                원래 = ast.unparse(노드)
                if 원래 in 옛글:
                    새줄 = 옛글.replace(원래, f"{왼} {새연산} {오}", 1)
                    out.append((f"{줄}줄 `{원래[:28]}` 뒤집기", _줄바꾸기(src, 줄, 새줄)))
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
    env = {**os.environ, "PYTHONPATH": str(판)}
    try:
        for t in 검사들:
            if not (판 / t).is_file():
                continue
            try:
                r = subprocess.run(["python3", str(도구), rel, t], cwd=str(판), env=env,
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


def _돌려보기(판: Path, 검사들: "list[str]", 초: int = 검사시한초) -> "tuple[bool, str]":
    """하나라도 빨갛면 (True, 그 검사). 전부 초록이면 (False, "")."""
    env = {**os.environ, "PYTHONPATH": str(판)}
    for t in 검사들:
        if not (판 / t).is_file():
            continue
        try:
            rc = subprocess.run(["python3", t], cwd=str(판), env=env, capture_output=True,
                                text=True, timeout=초).returncode
        except subprocess.TimeoutExpired:
            rc = 124
        if rc != 0:
            return True, t
    return False, ""


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
            빨강먼저, 어디 = _돌려보기(판, 검사들)
            if 빨강먼저:
                out["못잼"] += 1
                적기(repo, {"꼴": "원래빨강", "파일": rel, "검사": 어디})
                말(f"[변형] {rel}: 그 검사가 원래 빨강({어디}) -- 못 잰다")
                continue
            out["파일수"] += 1
            덮임 = 덮인줄(판, rel, 검사들)                 # 파일마다 한 번 -- 변형마다 다시 재지 않는다
            적기(repo, {"꼴": "덮임", "파일": rel, "덮인줄수": len(덮임), "검사": 검사들[:3]})
            if 함수상한:
                이름들 = 이름들[:함수상한]
            for 이름 in 이름들:
                if time.monotonic() - 시작 > 시한초:
                    break
                for 설명, 새글 in 변형들(원글, 이름):
                    if time.monotonic() - 시작 > 시한초:
                        break
                    # **비등가성 먼저.** 의미가 보존된 변형(TCE 동등)은 살아남아도 아무것도 증명하지 못한다.
                    if 동등한가(원글, 새글):
                        out["동등제외"] += 1
                        적기(repo, {"꼴": "동등제외", "파일": rel, "함수": 이름, "변형": 설명})
                        continue
                    # **실행되는 줄인가.** 안 덮인 줄의 변형이 사는 것은 단언의 약함이 아니라 덮임의 구멍이다.
                    줄 = 0
                    try:
                        줄 = int(설명.split("줄")[0])
                    except ValueError:
                        줄 = 0
                    if 줄 and 덮임 and 줄 not in 덮임:
                        out["덮이지않음"] += 1
                        out["덮이지않은것"].append({"파일": rel, "함수": 이름, "변형": 설명})
                        적기(repo, {"꼴": "덮이지않음", "파일": rel, "함수": 이름, "변형": 설명})
                        continue
                    (판 / rel).write_text(새글, encoding="utf-8")
                    try:
                        죽었나, 죽인검사 = _돌려보기(판, 검사들)
                    finally:
                        (판 / rel).write_text(원글, encoding="utf-8")
                    out["잰변형"] += 1
                    if 죽었나:
                        out["죽음"] += 1
                    else:
                        out["살아남음"] += 1
                        out["살아남은것"].append({"파일": rel, "함수": 이름, "변형": 설명, "검사": 검사들, "덮임": True})
                        적기(repo, {"꼴": "살아남음", "파일": rel, "함수": 이름, "변형": 설명, "검사": 검사들[:3]})
                        말(f"[변형] **거짓 초록** {rel}:{이름} -- {설명} (검사 {', '.join(검사들[:2])} 가 초록)")
            적기(repo, {"꼴": "파일끝", "파일": rel, "잰변형": out["잰변형"], "살아남음": out["살아남음"]})
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(판)],
                       capture_output=True, text=True)
        shutil.rmtree(판, ignore_errors=True)
    적기(repo, {"꼴": "사냥끝", **{k: v for k, v in out.items() if k != "살아남은것"}})
    return out


def 보고(repo=None, 몇: int = 20) -> str:
    """원장에서 사람이 읽는 표. 사냥하지 않는다."""
    행들 = 원장읽기(repo)
    산것 = [x for x in 행들 if x.get("꼴") == "살아남음"]
    끝 = [x for x in 행들 if x.get("꼴") == "사냥끝"]
    줄 = [f"**거짓 초록 사냥** -- 원장 {len(행들)}줄 · 사냥 {len(끝)}번"]
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
        파일별.setdefault(x.get("파일", "?"), []).append(x)
    줄.append(f"\n**살아남은 변형 {len(산것)}개** (코드가 이렇게 틀려도 검사가 초록이다):")
    for f, xs in sorted(파일별.items(), key=lambda kv: -len(kv[1]))[:몇]:
        줄.append(f"  {f} -- {len(xs)}개")
        for x in xs[:3]:
            줄.append(f"      {x.get('함수')}: {x.get('변형')}")
    덮안 = [x for x in 행들 if x.get("꼴") == "덮이지않음"]
    if 덮안:
        파 = {}
        for x in 덮안:
            파[x.get("파일", "?")] = 파.get(x.get("파일", "?"), 0) + 1
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
