"""rehearsal -- **고치기 전에 격리 판에서 돌려 본다.** 실제 트리에 닿기 전의 리허설.

사용자(2026-09-11): "너는 코드를 바꾸기 전에 바뀔 코드가 배선된 시스템을 시뮬레이션해 보고
문제가 없으면 바꾸잖아. 우리는 샌드박스 공간도 있는데 왜 이걸 안 하지?"

맞는 지적이다. 이 저장소에는 이미 둘이 있었는데 **이어져 있지 않았다**:
  · `sandbox.실행` -- 격리 판에서 명령을 돌린다
  · `plan` -- 그림자 워크트리에서 고치고 diff 를 보인다
그런데 `!계획 보기` 는 diff 를 **보여 주기만** 했고, 그 diff 를 **돌려 보지는 않았다.**
그래서 `!계획 승인` 은 '돌려 보지 않은 코드' 를 실제 트리에 붙였다. 여기서 잇는다.

리허설이 하는 것(전부 **판 안에서**, 실제 트리는 안 건드린다):
  1. 문법   -- 바뀐 .py 를 py_compile. **임포트 못 해도 잡힌다**(실측: on_ready 들여쓰기
              사고를 이것이 잡는다). 제3자 꾸러미가 없어도 도는 검사다
  2. 게이트 -- 그 판에서 gatekeeper 를 돌린다(G012 가 진짜 임포트까지 본다)
  3. 검사   -- 바뀐 파일이 거는 검사만 그 판에서 돌린다(audit.검사찾기 -- 두 벌 금지)

판정은 코드가 한다(끝값). 못 돌린 것은 **못잼**으로 따로 세고, 통과로 치지 않는다.

    python3 rehearsal.py                 # 계획판이 켜져 있으면 그 그림자를, 아니면 지금 작업 트리 사본을
    python3 rehearsal.py --판 <경로>
    끝값 0 통과 · 1 빨강 · 3 판을 못 깜
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent


def _바뀐것(판: Path) -> "list[str]":
    """그 판에서 바뀐(또는 새로 생긴) .py 들. 계획판은 add -N 을 이미 해 둔다."""
    r = subprocess.run(["git", "-C", str(판), "status", "--porcelain"],
                       capture_output=True, text=True, timeout=60)
    out = []
    for line in (r.stdout or "").splitlines():
        rel = line[3:].strip()
        if " -> " in rel:
            rel = rel.split(" -> ")[-1]
        if rel.endswith(".py"):
            out.append(rel)
    return sorted(set(out))


def _돌리기(argv: "list[str]", 판: Path, 초: int) -> dict:
    from sandbox import run as SB
    return SB.실행(argv, repo=판, 지금트리=True, 초=초, 메모리MB=4096)


def 시험(repo=None, 판=None, 초: int = 180, 검사상한: int = 10,
        전부: bool = False, 전부초: int = 1800) -> dict:
    """격리 판에서 문법·게이트·검사를 돌린다. 실제 트리는 안 건드린다.

    전부=True 면 **레포 전체**(scripts/tests.sh, 171개)를 판에서 돌리고 HEAD 바탕과 견주어 **회귀**를
    찾는다 -- 사용자(2026-09-11): "코드 하나 바뀌면 전체가 영향을 받을 수도 있잖아. 레포 전체를
    시뮬레이션해." 바뀐 파일이 거는 검사만 보면 **멀리서 깨진 것**을 못 본다."""
    repo = Path(repo or REPO)
    if 판 is None:
        try:
            from plan import store as P
            판 = P.현재판(repo)
        except Exception:                                  # noqa: BLE001
            판 = None
    판 = Path(판) if 판 else repo
    그림자인가 = 판 != repo
    결과 = {"판": str(판), "그림자": 그림자인가, "바뀐것": [], "걸음": [], "통과": True,
           "못잼": [], "걸린초": 0.0}
    시작 = time.monotonic()

    # **판이 없거나 git 판이 아니면 초록이라고 하지 않는다**(실측: 없는 경로에 '바뀐 것 없음 -> 통과' 를 냈다).
    if not 판.is_dir():
        결과.update(통과=False, 못잼=[f"판이 없다: {판}"], 걸린초=round(time.monotonic() - 시작, 1))
        return 결과
    확인 = subprocess.run(["git", "-C", str(판), "rev-parse", "--is-inside-work-tree"],
                        capture_output=True, text=True, timeout=30)
    if 확인.returncode != 0:
        결과.update(통과=False, 못잼=[f"git 판이 아니다: {판}"], 걸린초=round(time.monotonic() - 시작, 1))
        return 결과

    바뀐 = _바뀐것(판)
    결과["바뀐것"] = 바뀐
    if not 바뀐:
        결과["걸음"].append(("바뀐 .py 없음", 0, "리허설할 코드 변경이 없다"))
        결과["걸린초"] = round(time.monotonic() - 시작, 1)
        return 결과

    # 1. 문법 -- 임포트가 안 되는 환경에서도 도는 검사(들여쓰기·문법 사고를 여기서 잡는다)
    잴것 = [f for f in 바뀐 if (판 / f).is_file()]
    r = _돌리기(["python3", "-m", "py_compile", *잴것], 판, 초=60)
    if not r["돌았나"]:
        결과["못잼"].append(f"문법: {r.get('메모', '판을 못 깜')}")
        결과["통과"] = False
    else:
        꼬리 = ((r["stdout"] or "") + (r["stderr"] or "")).strip().splitlines()[-4:]
        결과["걸음"].append(("문법(py_compile)", r["끝값"], "\n".join(꼬리) or f"{len(잴것)}개 깨끗"))
        if r["끝값"] != 0:
            결과["통과"] = False

    # 2. 게이트 -- 그 판에서. G012 가 진짜 임포트까지 본다
    r = _돌리기(["python3", "gatekeeper.py"], 판, 초=초)
    if not r["돌았나"]:
        결과["못잼"].append(f"게이트: {r.get('메모', '판을 못 깜')}")
        결과["통과"] = False
    else:
        꼬리 = ((r["stdout"] or "") + (r["stderr"] or "")).strip().splitlines()[-6:]
        결과["걸음"].append(("게이트", r["끝값"], "\n".join(꼬리)))
        if r["끝값"] != 0:
            결과["통과"] = False

    # 3. 바뀐 파일이 거는 검사만 -- 그 판에서
    try:
        from audit import run as A
        걸림, 안덮임 = A.검사찾기(판, 바뀐)
        검사들 = sorted({t for ts in 걸림.values() for t in ts})[:검사상한]
    except Exception as e:                                 # noqa: BLE001
        검사들, 안덮임 = [], []
        결과["못잼"].append(f"검사 고르기: {type(e).__name__}")
        결과["통과"] = False
    결과["안덮임"] = 안덮임
    for t in 검사들:
        r = _돌리기(["python3", t], 판, 초=초)
        if not r["돌았나"]:
            결과["못잼"].append(f"{t}: {r.get('메모', '판을 못 깜')}")
            결과["통과"] = False
            continue
        꼬리 = ((r["stdout"] or "") + (r["stderr"] or "")).strip().splitlines()[-4:]
        결과["걸음"].append((t, r["끝값"], "\n".join(꼬리)))
        if r["끝값"] != 0:
            결과["통과"] = False

    # 4. 레포 전체 -- 멀리서 깨진 것을 찾는다(회귀)
    if 전부:
        바 = 바탕(repo, 초=전부초)
        뒤 = 전체검사(판, 초=전부초)
        if not (바["돌았나"] and 뒤["돌았나"]):
            결과["못잼"].append("레포 전체: " + (바.get("메모") or 뒤.get("메모") or "판을 못 깜"))
            결과["통과"] = False
        else:
            회 = 회귀(바, 뒤)
            결과["회귀"] = 회
            결과["전체"] = {"바탕실패": len(바["실패"]), "뒤실패": len(뒤["실패"]),
                         "센것": len(뒤["통과"]) + len(뒤["실패"]), "바탕캐시": bool(바.get("캐시"))}
            꼬 = (f"바탕 빨강 {len(바['실패'])} -> 뒤 빨강 {len(뒤['실패'])}"
                 + (f" · **새로 깨짐** {회['새로깨짐']}" if 회["새로깨짐"] else " · 새로 깨진 것 없음")
                 + (f" · 고쳐짐 {회['고쳐짐']}" if 회["고쳐짐"] else ""))
            결과["걸음"].append(("레포 전체(회귀)", 1 if 회["새로깨짐"] else 0, 꼬))
            if 회["새로깨짐"]:
                결과["통과"] = False

    결과["걸린초"] = round(time.monotonic() - 시작, 1)
    return 결과


# ---------------------------------------------------------------- 레포 전체 시뮬레이션 (회귀 찾기)
바탕상대 = "logs/rehearsal_baseline.json"


def _검사줄뽑기(본: str) -> dict:
    """scripts/tests.sh 의 출력을 가른다. {"통과":[...], "실패":[...], "건너뜀":[...]}"""
    r = {"통과": [], "실패": [], "건너뜀": []}
    for line in (본 or "").splitlines():
        m = re.match(r"\s*(OK|실패|건너뜀)\s+(\S+\.py)", line)
        if m:
            r["통과" if m.group(1) == "OK" else m.group(1)].append(m.group(2))
    return {k: sorted(set(v)) for k, v in r.items()}


# ---------------------------------------------------------------- 공허 검사: 초록이 뜻이 있나
# 사용자(2026-09-12): "구조가 좋으면 모델의 성능을 이길 수 있다." 이 저장소가 가진 최고의 장치가
# investigate.목표검사유효한가 다 -- 기능 없는 판에서 검사가 빨간지 본다(PR #194 의 속임수를 잡았다).
# 그런데 목표 모드·성공 시점·한 파일에만 돌았다. 여기서 **모든 패치**로 넓힌다.
#
#   규칙: 코드가 바뀌었으면, 그 변경이 없을 때 빨갛고 있을 때 초록인 검사가 하나는 있어야 한다.
#
# 오늘 이것이 없어서 지나간 것들: #194(함수만 정의한 검사), #201(글자가 있는지 보는 검사), 구글 문
# 세 줄(검사 없음). 셋 다 시뮬이 초록이었다 -- 검사하지 않은 초록불.
def _본문AST(src: str) -> str:
    """독스트링을 뺀 AST 덤프. 주석은 AST 에 없고 독스트링은 여기서 뺀다 -- 둘만 바뀐 것은 행동 변화가 아니다."""
    import ast
    try:
        나무 = ast.parse(src)
    except SyntaxError:
        return "!syntax:" + src
    for 노드 in ast.walk(나무):
        본 = getattr(노드, "body", None)
        if (isinstance(본, list) and 본 and isinstance(본[0], ast.Expr)
                and isinstance(getattr(본[0], "value", None), ast.Constant)
                and isinstance(본[0].value.value, str)):
            del 본[0]
    return ast.dump(나무)


def _판변경(판: Path, 기준: str = "HEAD") -> "tuple[list[str], list[str], list[str]]":
    """판에서 **기준 커밋** 대비 바뀐 파일. (검사파일, 코드파일, 지운파일) -- 모두 저장소 상대경로, .py 만.

    기준이 HEAD 면 `git status` 그대로(작업 디렉터리의 변경). 기준이 다른 커밋이면 -- 조사 모드처럼 두뇌가
    바퀴마다 커밋해 HEAD 가 움직인 자리 -- `git diff 기준`(그 커밋 대 작업 디렉터리)에 추적 안 된 파일을 더한다."""
    검사, 코드, 지움 = [], [], []
    본것: set = set()

    def 넣기(rel: str, 지웠나: bool) -> None:
        if rel in 본것 or not rel.endswith(".py"):
            return
        본것.add(rel)
        if 지웠나:
            지움.append(rel)
        elif rel.startswith("tests/") and Path(rel).name.startswith("test_"):
            검사.append(rel)
        else:
            코드.append(rel)

    if 기준 != "HEAD":
        r = subprocess.run(["git", "-C", str(판), "diff", "--name-status", "-z", 기준],
                           capture_output=True, text=True)
        항목 = [x for x in r.stdout.split("\0") if x]
        i = 0
        while i < len(항목):
            상태 = 항목[i]; i += 1
            if i >= len(항목):
                break
            rel = 항목[i]; i += 1
            if 상태[:1] in "RC" and i < len(항목):      # R/C 는 옛 이름 · 새 이름 둘
                rel = 항목[i]; i += 1
            넣기(rel, 상태[:1] == "D")
    r = subprocess.run(["git", "-C", str(판), "status", "--porcelain", "-z", "--untracked-files=all"],
                       capture_output=True, text=True)
    항목 = [x for x in r.stdout.split("\0") if x]
    i = 0
    while i < len(항목):
        줄 = 항목[i]; i += 1
        코드글, rel = 줄[:2], 줄[3:]
        if "R" in 코드글 or "C" in 코드글:
            i += 1
        if 기준 != "HEAD" and 코드글 != "??":          # 기준이 따로 있으면 status 는 추적 안 된 파일만 보탠다
            continue
        넣기(rel, "D" in 코드글)
    return 검사, 코드, 지움


def _HEAD글(판: Path, rel: str, 기준: str = "HEAD") -> "str | None":
    r = subprocess.run(["git", "-C", str(판), "show", f"{기준}:{rel}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def _함수자리(src: str) -> dict:
    """뺄 수 있는 함수 자리. {이름: {시작, 끝, 열, 들여, 지문}} -- 위에서부터. 클래스 안은 `클래스.이름`.

    시작·끝 = 몸통의 첫 줄·마지막 줄(1부터). 열 = 몸통이 서명과 **같은 줄**에 있으면(`def f(): return 1`,
    여러 줄 서명의 끝 줄에 붙은 것도) 그 줄에서 몸통이 시작하는 열, 아니면 None. 들여 = 몸통이 들여쓰일 칸.
    지문 = 독스트링을 뺀 AST 덤프 -- 주석·독스트링만 바뀐 함수는 지문이 같아 절제 단위가 안 된다.
    함수 안의 함수는 따로 안 센다(부모와 같이 빠진다)."""
    import ast, copy
    try:
        나무 = ast.parse(src)
    except SyntaxError:
        return {}
    줄들 = src.splitlines()
    out: dict = {}

    def 담기(노드, 앞=""):
        if not 노드.body:
            return
        첫 = 노드.body[0]
        같은줄 = bool(줄들[첫.lineno - 1][:첫.col_offset].strip())     # 서명 끝과 몸통이 한 줄
        복 = copy.deepcopy(노드)
        if (isinstance(복.body[0], ast.Expr) and isinstance(getattr(복.body[0], "value", None), ast.Constant)
                and isinstance(복.body[0].value.value, str)):
            del 복.body[0]
        out[f"{앞}{노드.name}"] = {"시작": 첫.lineno, "끝": 노드.end_lineno,
                                  "열": 첫.col_offset if 같은줄 else None,
                                  "들여": 노드.col_offset + 4 if 같은줄 else 첫.col_offset,
                                  "지문": ast.dump(복)}

    for 노드 in 나무.body:
        if isinstance(노드, (ast.FunctionDef, ast.AsyncFunctionDef)):
            담기(노드)
        elif isinstance(노드, ast.ClassDef):
            for 안 in 노드.body:
                if isinstance(안, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    담기(안, f"{노드.name}.")
    return out


def _절제한글(src: str, 이름: str) -> "str | None":
    """그 함수의 **몸통만** `raise NotImplementedError` 로 바꾼 글. 못 찾으면 None.
    서명·데코레이터·기본값은 그대로 둔다 -- 임포트와 호출 자리는 살아 있고 **동작만 사라진다**."""
    자리 = _함수자리(src).get(이름)
    if not 자리:
        return None
    줄들 = src.splitlines(keepends=True)
    시작, 끝 = 자리["시작"], 자리["끝"]
    빼기 = " " * 자리["들여"] + 'raise NotImplementedError("절제")\n'
    if 자리["열"] is not None:                       # `def f(): return 1` -- 서명만 남기고 줄을 끊는다
        머리 = 줄들[시작 - 1][:자리["열"]].rstrip() + "\n"
        return "".join(줄들[:시작 - 1]) + 머리 + 빼기 + "".join(줄들[끝:])
    return "".join(줄들[:시작 - 1]) + 빼기 + "".join(줄들[끝:])


절제상한 = 8          # 기능 하나마다 검사를 다 돌린다 -- 비싸다. 많으면 앞 것만


def _절제단위(판: Path, 코드: "list[str]", 기준: str = "HEAD") -> "list[tuple[str, str | None]]":
    """뺄 단위 목록 [(파일, 함수이름|None)]. None 은 파일 전체(함수가 하나도 없는 새 파일).
    바뀐 파일의 함수 중 **지문이 HEAD 와 다른 것**만 -- 새 함수, 몸통·서명이 바뀐 함수. 새 파일은 함수마다."""
    단위: list = []
    for rel in 코드:
        if not (판 / rel).is_file():
            continue
        후 = (판 / rel).read_text(encoding="utf-8", errors="replace")
        전 = _HEAD글(판, rel, 기준)
        전자리 = _함수자리(전) if 전 is not None else {}
        후자리 = _함수자리(후)
        if 전 is None and not 후자리:
            단위.append((rel, None))                   # 상수뿐인 새 파일 -- 통째로 빼 본다
            continue
        for 이름, 자리 in 후자리.items():
            if 이름 not in 전자리 or 전자리[이름]["지문"] != 자리["지문"]:
                단위.append((rel, 이름))
    return 단위


def 절제검사(repo=None, 판=None, 초: int = 300, 상한: int = None, 기준: str = "HEAD") -> dict:
    """**기능을 빼면 검사가 무너지나.** {성립, 말, 잰것:[{이름, 무너짐, 어디}], 안잡힌것, 못잼}.

    사용자(2026-09-12): "기능의 존재를 주장하지 말고, 그 기능을 제거했을 때 검사가 무너지고 다시 넣었을
    때 복구되는지를 볼 수 있도록 해라."

    공허검사(아래)는 **패치 전체**를 빼고 본다 -- 그 한 덩어리가 검사에 걸리는지만 안다. 그래서 함수 셋을
    더했는데 그중 하나만 검사에 걸려도 통째로는 초록이다. 나머지 둘은 지워도 아무도 모른다.
    여기서는 **하나씩** 뺀다: 바뀐 함수마다 몸통을 NotImplementedError 로 바꾸고(서명은 그대로 두므로
    임포트는 살아 있다) 패치의 검사를 돌린다. 빨개져야 한다. 초록이면 그 함수는 아무 검사도 안 본다.

    '다시 넣으면 복구' 의 반쪽은 이미 있다 -- 절제 안 한 판이 초록이라는 사실(`시험`)이 그것이다.
    그래서 한 쌍이 완성된다: **빼면 빨강(여기) · 넣으면 초록(리허설)**.

    재는 검사는 **패치의 검사 파일**뿐이다(공허검사와 같은 기준) -- 이 저장소는 행동 변경마다 그 변경을 재는
    검사를 패치에 담게 하므로, 저장소의 다른 검사가 우연히 잡아 주는 것은 안 친다.
    비싸므로 `절제상한` 개까지만 재고, 다 합쳐 `초*3` 을 넘기면 남은 것은 못잼으로 적는다.
    `기준` 은 '기능 없는 판' 의 커밋 -- 보통 HEAD, 조사 모드에서는 조사 시작 커밋(두뇌가 바퀴마다 커밋해도
    시작 커밋 대비 바뀐 것 전부가 한 패치다).
    """
    import os, shutil, tempfile, time
    repo = Path(repo or REPO)
    판 = Path(판) if 판 else repo
    상한 = 절제상한 if 상한 is None else 상한
    검사, 코드, 지움 = _판변경(판, 기준)
    out = {"성립": True, "말": "", "잰것": [], "안잡힌것": [], "못잼": []}
    if not 검사:
        out["말"] = "패치에 검사가 없다 -- 공허검사가 먼저 막는다"
        return out
    단위 = _절제단위(판, 코드, 기준)
    if not 단위:
        out["말"] = "뺄 수 있는 단위가 없다(검사만 바뀌었거나, 함수 밖 상수·주석만 바뀌었다)"
        return out
    넘침 = max(0, len(단위) - 상한)
    단위 = 단위[:상한]
    시작때 = time.monotonic()
    for i, (rel, 이름) in enumerate(단위):
        이름말 = f"{rel}:{이름}" if 이름 else f"{rel}(파일 전체)"
        if time.monotonic() - 시작때 > 초 * 3:
            out["못잼"].extend(f"{r}:{n or '파일'} -- 시간 상한" for r, n in 단위[i:])
            break
        tmp = Path(tempfile.mkdtemp(prefix="se-절제-"))
        try:
            r = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(tmp), 기준],
                               capture_output=True, text=True)
            if r.returncode != 0:
                out["못잼"].append(f"{이름말} -- 판을 못 꺼냈다")
                continue
            for x in 검사 + 코드:                      # 후보를 그대로 옮기고 지운 것은 지운다
                src = 판 / x
                if src.is_file():
                    (tmp / x).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(src, tmp / x)
            for x in 지움:
                (tmp / x).unlink(missing_ok=True)
            if 이름 is None:
                (tmp / rel).unlink(missing_ok=True)
            else:
                새글 = _절제한글((tmp / rel).read_text(encoding="utf-8", errors="replace"), 이름)
                if 새글 is None:
                    out["못잼"].append(f"{이름말} -- 그 자리를 못 찾았다")
                    continue
                (tmp / rel).write_text(새글, encoding="utf-8")
            env = {**os.environ, "PYTHONPATH": str(tmp)}
            무너짐, 어디 = False, ""
            for t in 검사:
                if not (tmp / t).is_file():
                    continue
                try:
                    rc = subprocess.run(["python3", t], cwd=str(tmp), env=env, capture_output=True,
                                        text=True, timeout=초).returncode
                except subprocess.TimeoutExpired:
                    rc = 124
                if rc != 0:
                    무너짐, 어디 = True, t
                    break
            out["잰것"].append({"이름": 이름말, "무너짐": 무너짐, "어디": 어디})
            if not 무너짐:
                out["안잡힌것"].append(이름말)
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(tmp)],
                           capture_output=True, text=True)
            shutil.rmtree(tmp, ignore_errors=True)
    if out["안잡힌것"]:
        out["성립"] = False
        out["말"] = (f"**절제해도 검사가 안 무너진다**: {', '.join(out['안잡힌것'][:4])}. 그 기능을 빼도 패치의 검사"
                     f"({', '.join(검사[:3])})가 초록이다 -- 그 기능은 아무 검사도 안 본다. 그것을 실제로 부르고 "
                     f"결과를 단언하는 검사를 더해라(기능의 존재를 글로 주장하는 것이 아니라).")
    else:
        out["말"] = (f"절제 {len(out['잰것'])}개 다 무너졌다(빼면 빨강 · 넣으면 초록) -- 검사가 기능마다 걸린다"
                     + (f" · 상한으로 {넘침}개는 안 쟀다" if 넘침 else "")
                     + (f" · 못 잰 것 {len(out['못잼'])}개" if out["못잼"] else ""))
    return out


# ------------------------------------------------------------------ 순환검사: 제 부산물을 보고 초록이 되나
# 실측 2026-09-12(VM, PR #214 "[조사 f867ea29] scripts/ledgerstat.py 열쇠 집계 기능 수정"): 조사가 '해결' 로
# 스스로 머지했는데 **고쳤다는 파일이 머지에 없었다.** 코드 변경은 목표 검사 한 파일뿐이고, 그 검사가 이렇게
# 바뀌어 있었다 -- `for entry in 원장: if '귀속' in entry: return`(통과). 그런데 `귀속` 은 조사 루프가
# 바퀴마다 repair/ledger.jsonl 에 적는 필드다. 같은 PR 이 그 원장에 6줄을 더했다.
# **검사가 자기 실행의 부산물을 보고 초록이 됐다.** 공허도 절제도 이것을 못 본다(검사는 정말 무언가를 읽고
# 단언한다). 목표검사유효한가 도 통과시킨다 -- 시작 판에는 그 줄이 아직 없어 빨강, 지금은 있어 초록이니
# '검사 구실을 한다' 로 보인다. 데이터가 그 사이 **제 손으로** 바뀐 것을 아무도 안 봤다.
#
# 그래서 목록을 박지 않고 이렇게 잰다: **패치가 고친 데이터 파일(이미 있던 것)을 패치의 검사가 읽으면 순환.**
# 패치가 새로 더한 표본 파일은 기준 커밋에 없으므로 걸리지 않는다 -- 그것은 정당한 붙임이다.
순환볼꼴 = (".jsonl", ".json", ".log", ".csv", ".txt")
읽는부름 = ("read_text", "read_bytes", "readlines", "read", "open", "load", "loads")


def _판변경모두(판: Path, 기준: str = "HEAD") -> "list[str]":
    """판에서 기준 대비 바뀐 **모든** 경로(.py 만이 아니다). 지운 것도 든다."""
    out, 본것 = [], set()

    def 넣기(rel: str) -> None:
        if rel and rel not in 본것:
            본것.add(rel); out.append(rel)

    if 기준 != "HEAD":
        r = subprocess.run(["git", "-C", str(판), "diff", "--name-only", "-z", 기준],
                           capture_output=True, text=True)
        for x in r.stdout.split("\0"):
            넣기(x)
    r = subprocess.run(["git", "-C", str(판), "status", "--porcelain", "-z", "--untracked-files=all"],
                       capture_output=True, text=True)
    항목 = [x for x in r.stdout.split("\0") if x]
    i = 0
    while i < len(항목):
        줄 = 항목[i]; i += 1
        코드글, rel = 줄[:2], 줄[3:]
        if "R" in 코드글 or "C" in 코드글:
            i += 1
        if 기준 != "HEAD" and 코드글 != "??":
            continue
        넣기(rel)
    return out


def _읽는파일들(노드들, 판: Path) -> "dict[str, int]":
    """그 조각이 **실제로 읽는** 파일 -> 줄번호. 문자열로 '언급' 만 한 것은 안 센다.

    센다: open("a.jsonl") · Path("a.jsonl").read_text() · p = "a.jsonl" 뒤 open(p) (한 홉).
    안 센다: 딕트 값·보고 문구·명령 문자열 안의 경로 -- 실측: 지금 검사들은 원장 경로를 그렇게만 들고 있다."""
    import ast
    쓸것: dict = {}
    이름표 = _이름에든자료(판, 노드들)

    def 글자(노드):
        if isinstance(노드, ast.Constant) and isinstance(노드.value, str):
            return 노드.value.strip()
        if isinstance(노드, ast.Name):
            return 이름표.get(노드.id)
        if isinstance(노드, ast.Call) and 노드.args:        # Path("a") · str(x)
            return 글자(노드.args[0])
        return None

    for 노드 in 노드들:
        if not isinstance(노드, ast.Call):
            continue
        이름 = (노드.func.attr if isinstance(노드.func, ast.Attribute)
                else 노드.func.id if isinstance(노드.func, ast.Name) else "")
        if 이름 not in 읽는부름:
            continue
        몫 = list(노드.args)
        if isinstance(노드.func, ast.Attribute):           # Path(...).read_text() 의 그 Path(...)
            몫.append(노드.func.value)
        for a in 몫:
            g = 글자(a)
            if g and (판 / g).is_file() and g not in 쓸것:
                쓸것[g] = 노드.lineno
    return 쓸것


def 순환검사(repo=None, 판=None, 기준: str = "HEAD") -> dict:
    """**검사가 제 실행의 부산물을 보고 초록이 되나.** {성립, 말, 찾은것:[{검사, 읽은것, 줄}], 본것}.

    패치가 고친 데이터 파일(.jsonl/.json/.log/.csv/.txt) 중 **기준 커밋에 이미 있던 것**을, 패치의 검사가
    실제로 읽으면 순환이다 -- 그 초록은 기능이 아니라 같은 실행이 덧붙인 줄을 증언한다.
    패치가 새로 더한 표본 파일은 기준에 없으니 걸리지 않는다. LLM 0회 · subprocess 는 git 조회뿐."""
    repo = Path(repo or REPO)
    판 = Path(판) if 판 else repo
    out = {"성립": True, "말": "", "찾은것": [], "본것": []}
    바뀐것 = _판변경모두(판, 기준)
    의심 = []
    for rel in 바뀐것:
        if not rel.endswith(순환볼꼴):
            continue
        있었나 = subprocess.run(["git", "-C", str(판), "cat-file", "-e", f"{기준}:{rel}"],
                              capture_output=True, text=True).returncode == 0
        if 있었나:
            의심.append(rel)
    if not 의심:
        out["말"] = "패치가 고친 기존 데이터 파일이 없다 -- 볼 것 없다"
        return out
    검사, _코드, _지움 = _판변경(판, 기준)
    for t in 검사:
        낱 = 판 / t
        if not 낱.is_file():
            continue
        out["본것"].append(t)
        나무, 조각들 = _조각들(낱.read_text(encoding="utf-8", errors="replace"))
        for 조각, 노드들, _함수 in 조각들:
            for 경로, 줄 in _읽는파일들(노드들, 판).items():
                if 경로 in 의심 and not any(x["읽은것"] == 경로 and x["검사"] == t for x in out["찾은것"]):
                    out["찾은것"].append({"검사": t, "읽은것": 경로, "줄": 줄})
    if out["찾은것"]:
        보임 = ", ".join(f"{x['검사']}:{x['줄']} -> {x['읽은것']}" for x in out["찾은것"][:4])
        out["성립"] = False
        out["말"] = (f"**검사가 제 실행이 고친 원장을 읽는다**: {보임}. 같은 패치가 그 파일을 바꿨으니 그 초록은 "
                     f"기능이 아니라 **이 실행이 덧붙인 줄**을 증언한다(실측 2026-09-12 PR #214: 조사가 "
                     f"repair/ledger.jsonl 에 적은 `귀속` 을 제 검사가 보고 '해결' 이 됐다). 검사는 원장이 아니라 "
                     f"**고친 코드**를 불러 결과를 단언해라 -- 원장이 필요하면 검사가 지은 임시 파일을 써라.")
    else:
        out["말"] = f"검사가 제 실행이 고친 원장을 읽지 않는다 (고친 데이터 {len(의심)}개)"
    return out


# ------------------------------------------------------------------ 미정의이름: 없는 이름을 부르나
# 실측 2026-09-12: `discord_bot_server._git_sync_locked` 가 `report.summary()` 를 불렀는데 그 이름이 없었다
# (게이트 보고 변수 이름이 `보고` 로 바뀐 뒤에 남은 줄). **밀기가 성공한 경로에서만** 터지므로 커밋·푸시가 다
# 된 뒤에 사용자가 "[git 동기화 실패] NameError" 를 보았다. py_compile 도 임포트도 이것을 못 잡는다 --
# 파이썬은 함수 몸통의 이름을 **부를 때** 푼다. 같은 결이 저장소에 다섯 군데 있었다(coin/news._주소 ·
# scripts/gemini_limits._hdr·_die · tests/test_스크립트로_돈다 의 ast). 전부 이 검사가 찾았다.
_빌트인이름 = None
미정의봐주기 = ("__class__",)     # super() 가 암묵으로 쓴다 -- 미정의가 아니다


def _미정의한파일(src: str, 이름표: str = "<판>") -> "list[tuple[str, int, str]]":
    """(조각 이름, 줄, 이름) -- 함수 안에서 **어디에도 정의되지 않은** 이름.

    symtable 을 쓴다 -- 파이썬 자신의 스코프 해석이므로 내포 표현식·클로저·global/nonlocal·함수 안 임포트를
    다 제대로 본다. AST 로 손수 세면 그것들이 전부 거짓 양성이 된다."""
    import builtins, symtable
    global _빌트인이름
    if _빌트인이름 is None:
        _빌트인이름 = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__package__",
                                         "__spec__", "__loader__", "__builtins__", "__debug__"}
    if "import *" in src:
        return []                                  # 무엇이 들어왔는지 알 수 없다 -- 재지 않는다
    try:
        top = symtable.symtable(src, 이름표, "exec")
    except (SyntaxError, ValueError):
        return []
    모듈이름 = {x.get_name() for x in top.get_symbols()}
    out = []

    def 돌기(tbl, 감싼: set):
        여기 = {x.get_name() for x in tbl.get_symbols()
                if x.is_assigned() or x.is_parameter() or x.is_imported()}
        if tbl.get_type() == "function":
            for x in tbl.get_symbols():
                n = x.get_name()
                if (not x.is_referenced() or x.is_assigned() or x.is_parameter() or x.is_imported()
                        or n in 미정의봐주기 or n in _빌트인이름 or n in 모듈이름 or n in 감싼):
                    continue
                out.append((tbl.get_name(), tbl.get_lineno(), n))
        for 아 in tbl.get_children():
            돌기(아, 감싼 | 여기)

    for 아 in top.get_children():
        돌기(아, set())
    return out


def 미정의이름(repo=None, 판=None, 기준: str = "HEAD") -> dict:
    """**없는 이름을 부르나.** {성립, 말, 찾은것:[{파일, 조각, 줄, 이름}], 본것, 못잼}.

    패치가 만지는 .py 전부(검사 파일도 -- 거기 NameError 면 검사가 아예 안 돈다)를 본다.
    LLM 호출 0회 · subprocess 0회. 저장소 전체에 돌려 거짓 양성이 `__class__` 하나뿐임을 확인했다."""
    repo = Path(repo or REPO)
    판 = Path(판) if 판 else repo
    검사, 코드, 지움 = _판변경(판, 기준)
    out = {"성립": True, "말": "", "찾은것": [], "본것": [], "못잼": []}
    for rel in 검사 + 코드:
        낱 = 판 / rel
        if not 낱.is_file():
            continue
        src = 낱.read_text(encoding="utf-8", errors="replace")
        if "import *" in src:
            out["못잼"].append(f"{rel} (import * 가 있어 무엇이 들어왔는지 모른다)")
            continue
        out["본것"].append(rel)
        for 조각, 줄, 이름 in _미정의한파일(src, rel):
            out["찾은것"].append({"파일": rel, "조각": 조각, "줄": 줄, "이름": 이름})
    if out["찾은것"]:
        보임 = ", ".join(f"{x['파일']}:{x['줄']} {x['조각']}() -> `{x['이름']}`" for x in out["찾은것"][:5])
        out["성립"] = False
        out["말"] = (f"**없는 이름을 부른다**: {보임}. 그 이름은 그 파일 어디에도 없다(정의도 임포트도 아니다) -- "
                     f"그 줄이 돌면 NameError 다. py_compile 과 임포트는 이것을 못 잡는다(파이썬은 함수 몸통의 "
                     f"이름을 **부를 때** 푼다). 이름을 바로잡거나 그 함수에서 임포트해라.")
    elif out["본것"]:
        out["말"] = f"파일 {len(out['본것'])}개에 없는 이름을 부르는 자리가 없다"
    else:
        out["말"] = "볼 .py 가 없다"
    return out


# ------------------------------------------------------------------ 열쇠대조: 없는 열쇠를 읽고 있나
# 실측 2026-09-12: 봇이 `scripts/ledgerstat.py` 를 지어 "검증 완료 · OK" 라고 답했다. 검사는 정말 초록이었고
# 도구도 실제로 돌았다. 그런데 표의 여덟 칸 중 여섯이 **구조적으로 항상 0** 이었다 -- `repair/ledger.jsonl`
# 에 없는 열쇠(귀속·맞춘수·틀린수·막음·명령수)를 읽고 있었다. 검사는 그 열쇠들을 다 넣은 **가짜 행 한 줄**을
# 지어서 합을 단언했으니 초록이었다. 공허검사·절제검사는 "검사가 코드를 부르나" 를 보므로 여기를 못 본다 --
# 빠진 축은 **검사의 입력이 실제 입력과 같은 모양인가** 다. 작은 모델은 원장의 스키마를 모르고, 모르는 것을
# 안다고 할 수도 없다. 그래서 코드가 잰다: 읽는 열쇠 vs 그 파일에 실제로 있는 열쇠.
자료꼴 = (".jsonl", ".json")
_자료꼴정규식 = None


def _속노드들(노드):
    """그 조각의 노드들 -- **안에 든 다른 함수·람다는 뺀다.** 조각 하나가 한 이름 공간이다.

    실측 2026-09-12: 모듈 전체에서 이름을 모았더니 `diagnose.py` 의 240줄 `d = json.loads(line)`(원장 행)과
    312줄 `d["증거"]`(진단 결과 dict, 다른 함수)를 같은 것으로 보아 거짓 양성이 났다. `eval/tasks.py` 도
    과제 json 의 `t` 를 다른 함수가 읽는 원장과 맞췄다. **거짓 양성을 내는 검사는 없느니만 못하다.**"""
    import ast
    남 = list(ast.iter_child_nodes(노드))
    while 남:
        x = 남.pop()
        yield x
        if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        남.extend(ast.iter_child_nodes(x))


def _조각들(src: str) -> "tuple[object, list]":
    """(나무, [(조각 이름, 노드들, 함수노드|None)]). 모듈 몸통 하나 + 함수마다 하나."""
    import ast
    try:
        나무 = ast.parse(src)
    except SyntaxError:
        return None, []
    out = [("(모듈)", list(_속노드들(나무)), None)]
    for 노드 in ast.walk(나무):
        if isinstance(노드, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((노드.name, list(_속노드들(노드)), 노드))
    return 나무, out


def _이름에든자료(판: Path, 노드들) -> "dict[str, str]":
    """`x = "a/b.jsonl"` · `x = Path("a/b.jsonl")` 로 묶인 이름 -> 그 파일."""
    import ast
    out: dict = {}
    for 노드 in 노드들:
        if not isinstance(노드, ast.Assign) or len(노드.targets) != 1 or not isinstance(노드.targets[0], ast.Name):
            continue
        값 = 노드.value
        if isinstance(값, ast.Call) and 값.args:
            값 = 값.args[0]
        if isinstance(값, ast.Constant) and isinstance(값.value, str):
            for f in _자료파일들(판, [값]):
                out[노드.targets[0].id] = f
    return out


def _부른자료(판: Path, 나무, 함수: str) -> "list[str]":
    """모듈 안에서 그 함수를 부르는 자리가 넘기는 자료 파일. 경로가 `main()` 에 있고 읽기가 다른 함수에
    있는 꼴(실측: scripts/ledgerstat.py) 을 한 홉 따라간다 -- 리터럴과 그 조각에서 리터럴로 묶인 이름까지만.
    부르는 자리가 계산된 경로를 넘기면(디렉터리를 훑는 꼴) 아무것도 안 돌려준다 -- 짝을 모르면 재지 않는다."""
    import ast
    out, 본것 = [], set()
    for 조각, 노드들, _ in _조각들_노드(나무):
        이름표 = None
        for 노드 in 노드들:
            if not (isinstance(노드, ast.Call) and isinstance(노드.func, ast.Name) and 노드.func.id == 함수):
                continue
            if 이름표 is None:
                이름표 = _이름에든자료(판, 노드들)
            for 인자 in list(노드.args) + [k.value for k in 노드.keywords]:
                if isinstance(인자, ast.Call) and 인자.args:
                    인자 = 인자.args[0]
                찾음 = None
                if isinstance(인자, ast.Constant) and isinstance(인자.value, str):
                    찾음 = (_자료파일들(판, [인자]) or [None])[0]
                elif isinstance(인자, ast.Name):
                    찾음 = 이름표.get(인자.id)
                if 찾음 and 찾음 not in 본것:
                    본것.add(찾음); out.append(찾음)
    return out


def _조각들_노드(나무) -> "list[tuple[str, list, object]]":
    """이미 파싱된 나무에서 조각들만 -- _조각들 과 같은 꼴."""
    import ast
    out = [("(모듈)", list(_속노드들(나무)), None)]
    for 노드 in ast.walk(나무):
        if isinstance(노드, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((노드.name, list(_속노드들(노드)), 노드))
    return out


def _자료파일들(판: Path, 노드들) -> "list[str]":
    """그 조각이 **문자열로** 가리키는, 저장소에 실제로 있는 자료 파일들(.jsonl/.json)."""
    import ast, re
    global _자료꼴정규식
    if _자료꼴정규식 is None:
        _자료꼴정규식 = re.compile(r"^[\w./가-힣_-]+\.(?:jsonl|json)$")
    out, 본것 = [], set()
    for 노드 in 노드들:
        if isinstance(노드, ast.Constant) and isinstance(노드.value, str):
            글 = 노드.value.strip()
            if 글 in 본것 or not _자료꼴정규식.match(글):
                continue
            본것.add(글)
            if (판 / 글).is_file():
                out.append(글)
    return out


def _행이름들(노드들) -> "set[str]":
    """`json.loads(...)` 로 만든 **행**을 담는 이름들. 세 꼴만 본다 --
    `r = json.loads(x)` · `행들 = [json.loads(x) for x in f]` 뒤의 `for r in 행들` · `for r in [json.loads(x) …]`.
    이렇게 좁히면 같은 조각의 설정 dict(`cfg.get("model")`)를 원장 열쇠로 잘못 세지 않는다."""
    import ast

    def json읽기냐(노드) -> bool:
        return (isinstance(노드, ast.Call) and isinstance(노드.func, ast.Attribute)
                and 노드.func.attr in ("loads", "load")
                and isinstance(노드.func.value, ast.Name) and 노드.func.value.id == "json")

    def 속에json(노드) -> bool:
        return isinstance(노드, (ast.ListComp, ast.GeneratorExp, ast.SetComp)) and json읽기냐(노드.elt)

    행, 행목록 = set(), set()
    # **한 바퀴로는 모자란다** -- 노드 순서가 소스 순서가 아니라(가지치기 스택) `for r in 담` 을 `담 = json.load(…)`
    # 보다 먼저 볼 수 있다. 더 붙을 것이 없을 때까지 돈다.
    for _ in range(5):
        전크기 = (len(행), len(행목록))
        for 노드 in 노드들:
            if isinstance(노드, (ast.Assign, ast.AnnAssign)):
                값 = 노드.value
                대상 = 노드.targets if isinstance(노드, ast.Assign) else [노드.target]
                for t in 대상:
                    if not isinstance(t, ast.Name):
                        continue
                    if json읽기냐(값):
                        행.add(t.id)
                    elif 속에json(값):
                        행목록.add(t.id)
            elif isinstance(노드, (ast.For, ast.AsyncFor)) and isinstance(노드.target, ast.Name):
                잇 = 노드.iter
                # 행 목록을 돌면 그 알맹이가 행이다. `담 = json.load(f)` 처럼 행인지 목록인지 모를 것도 돌면 행으로 본다
                # (dict 를 돌면 열쇠 문자열이 나오는데, 문자열에는 .get 이 없어 아무 열쇠도 안 모인다 -- 해롭지 않다).
                if json읽기냐(잇) or 속에json(잇) or (isinstance(잇, ast.Name) and (잇.id in 행목록 or 잇.id in 행)):
                    행.add(노드.target.id)
        if (len(행), len(행목록)) == 전크기:
            break
    return 행


def _읽는열쇠(노드들) -> "dict[str, int]":
    """행에서 읽는 리터럴 열쇠 -> 첫 줄번호. `r.get("k")` · `r["k"]` · `"k" in r`."""
    import ast
    행 = _행이름들(노드들)
    if not 행:
        return {}
    out: dict = {}

    def 적기(k, 줄):
        if isinstance(k, str) and k and k not in out:
            out[k] = 줄

    for 노드 in 노드들:
        if (isinstance(노드, ast.Call) and isinstance(노드.func, ast.Attribute) and 노드.func.attr == "get"
                and isinstance(노드.func.value, ast.Name) and 노드.func.value.id in 행 and 노드.args
                and isinstance(노드.args[0], ast.Constant)):
            적기(노드.args[0].value, 노드.lineno)
        elif (isinstance(노드, ast.Subscript) and isinstance(노드.value, ast.Name) and 노드.value.id in 행
                and isinstance(노드.slice, ast.Constant)):
            적기(노드.slice.value, 노드.lineno)
        elif (isinstance(노드, ast.Compare) and isinstance(노드.left, ast.Constant)
                and any(isinstance(o, (ast.In, ast.NotIn)) for o in 노드.ops)
                and any(isinstance(c, ast.Name) and c.id in 행 for c in 노드.comparators)):
            적기(노드.left.value, 노드.lineno)
    return out


def _파일열쇠(경로: Path, 줄수: int = 3000) -> "tuple[dict, int]":
    """그 파일 행들의 top-level 열쇠 -> 몇 줄에 있나, 그리고 읽은 행 수."""
    import collections, json
    셈: collections.Counter = collections.Counter()
    행수 = 0
    try:
        if 경로.suffix == ".json":
            담 = json.loads(경로.read_text(encoding="utf-8", errors="replace"))
            행들 = 담 if isinstance(담, list) else [담]
        else:
            행들 = []
            with 경로.open(encoding="utf-8", errors="replace") as f:
                for 줄 in f:
                    if not 줄.strip():
                        continue
                    try:
                        행들.append(json.loads(줄))
                    except ValueError:
                        continue
                    if len(행들) >= 줄수:
                        break
    except (OSError, ValueError):
        return {}, 0
    for r in 행들[:줄수]:
        if isinstance(r, dict):
            행수 += 1
            셈.update(r.keys())
    return dict(셈), 행수


def 열쇠대조(repo=None, 판=None, 기준: str = "HEAD", 줄수: int = 3000) -> dict:
    """**없는 열쇠를 읽고 있나.** {성립, 말, 죽은읽기:[{파일, 조각, 열쇠, 줄, 원장}], 본것, 있는열쇠, 못잼}.

    패치의 코드 파일마다, **조각(함수)마다**: `json.loads` 로 만든 행에서 읽는 리터럴 열쇠를 모으고, 같은 조각이
    문자열로 가리키는 실제 자료 파일(.jsonl/.json)의 행들이 가진 열쇠와 맞춘다. **한 줄에도 없는 열쇠**는 죽은
    읽기다 -- `.get()` 은 조용히 None 을 주므로 터지지도 않고, 합은 0 이 되어 "아무 일도 없었다" 처럼 보인다.

    공허검사·절제검사가 "검사가 코드를 부르나" 를 보는 데 비해 여기는 **코드가 실제 데이터를 보나** 를 본다.
    조각 단위로 좁히는 까닭은 _속노드들 의 독스트링에 있다(거짓 양성 둘을 실측했다).
    LLM 호출 0회 · subprocess 0회 (AST 와 파일 읽기뿐). 검사 파일은 제 표본을 지어 쓰므로 안 본다."""
    repo = Path(repo or REPO)
    판 = Path(판) if 판 else repo
    검사, 코드, 지움 = _판변경(판, 기준)
    out = {"성립": True, "말": "", "죽은읽기": [], "본것": [], "있는열쇠": [], "못잼": []}
    for rel in 코드:
        낱 = 판 / rel
        if not 낱.is_file():
            continue
        나무, 조각들 = _조각들(낱.read_text(encoding="utf-8", errors="replace"))
        for 조각, 노드들, 함수 in 조각들:
            열쇠들 = _읽는열쇠(노드들)
            if not 열쇠들:
                continue
            자료들 = _자료파일들(판, 노드들)
            if not 자료들 and 함수 is not None:
                자료들 = _부른자료(판, 나무, 조각)          # 경로는 부른 쪽에 있다 -- 한 홉 따라간다
            if not 자료들:
                continue
            있는것: dict = {}
            쓴것, 행수 = [], 0
            for 자료 in 자료들:
                셈, n = _파일열쇠(판 / 자료, 줄수)
                if n == 0:
                    out["못잼"].append(f"{rel}:{조각} -> {자료} (행이 없다)")
                    continue
                쓴것.append(f"{자료}({n}줄)")
                행수 += n
                for k, 몇 in 셈.items():
                    있는것[k] = 있는것.get(k, 0) + 몇
            if 행수 == 0:
                continue
            out["본것"].append(f"{rel}:{조각} <- {', '.join(쓴것)}")
            죽 = [(k, 줄) for k, 줄 in 열쇠들.items() if k not in 있는것]
            if 죽:
                out["죽은읽기"].extend({"파일": rel, "조각": 조각, "열쇠": k, "줄": 줄, "원장": ", ".join(쓴것)}
                                   for k, 줄 in 죽)
                흔한 = sorted(있는것.items(), key=lambda x: -x[1])[:8]
                out["있는열쇠"] = [f"{k}({몇})" for k, 몇 in 흔한]
    if out["죽은읽기"]:
        보임 = ", ".join(f"{x['파일']}:{x['줄']} `{x['열쇠']}`" for x in out["죽은읽기"][:5])
        out["성립"] = False
        out["말"] = (f"**없는 열쇠를 읽는다**: {보임}. 그 열쇠는 {out['죽은읽기'][0]['원장']} 의 어느 행에도 없다 -- "
                     f".get() 은 조용히 None 을 주므로 터지지 않고 합이 0 이 되어 '아무 일도 없었다' 처럼 보인다. "
                     f"실제로 있는 열쇠: {', '.join(out['있는열쇠'])}. 그것으로 다시 써라(검사 표본도 지어낸 행이 "
                     f"아니라 실제 원장의 앞 몇 줄로).")
    elif out["본것"]:
        out["말"] = f"읽는 열쇠가 다 원장에 있다 -- {', '.join(out['본것'][:3])}"
    else:
        out["말"] = "원장을 읽는 코드가 패치에 없다 -- 볼 것 없다"
    return out


def 공허검사(repo=None, 판=None, 초: int = 300) -> dict:
    """패치의 초록이 **뜻이 있나**. {공허: bool, 말, 검사들, 코드들, 빨간검사}.

    공허 = 코드가 바뀌었는데 (a) 그것을 재는 검사가 하나도 안 바뀌었거나, (b) 바뀐 검사가 코드 변경
    없이도(HEAD 위에 검사만 얹어도) 전부 초록이다. 어느 쪽이든 그 초록은 이 변경을 증언하지 않는다.
    주석·독스트링만 바뀐 파일은 행동 변화로 안 친다."""
    repo = Path(repo or REPO)
    판 = Path(판) if 판 else repo
    검사, 코드, 지움 = _판변경(판)
    out = {"공허": False, "말": "", "검사들": 검사, "코드들": 코드, "빨간검사": []}
    행동 = []
    for rel in 코드 + 지움:
        전 = _HEAD글(판, rel)
        후 = (판 / rel).read_text(encoding="utf-8", errors="replace") if (판 / rel).is_file() else None
        if 전 is None or 후 is None or _본문AST(전) != _본문AST(후):
            행동.append(rel)
    if not 행동:
        out["말"] = "코드 행동 변화 없음(검사만, 또는 주석·독스트링만) -- 볼 것 없다"
        return out
    out["코드들"] = 행동
    if not 검사:
        out.update(공허=True, 말=(f"**공허** -- 코드가 바뀌었는데({', '.join(행동[:4])}) 그 변경을 재는 검사가 없다. "
                                "tests/test_<이름>.py 를 더해라: 이 변경이 없으면 빨갛고 있으면 초록인 검사"))
        return out
    import shutil, tempfile, os
    tmp = Path(tempfile.mkdtemp(prefix="se-공허-"))
    try:
        r = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(tmp), "HEAD"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            out["말"] = f"HEAD 판을 못 꺼내 못 쟀다: {r.stderr.strip()[:120]}"
            return out
        for rel in 검사:
            src = 판 / rel
            if src.is_file():
                (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, tmp / rel)
        env = {**os.environ, "PYTHONPATH": str(tmp)}
        for rel in 검사:
            if not (tmp / rel).is_file():
                continue
            try:
                p = subprocess.run(["python3", rel], cwd=str(tmp), env=env, capture_output=True, text=True, timeout=초)
                rc = p.returncode
            except subprocess.TimeoutExpired:
                rc = 124
            if rc != 0:
                out["빨간검사"].append(f"{rel} (끝값 {rc})")
        if out["빨간검사"]:
            out["말"] = f"기능 없는 판에서 빨강({', '.join(out['빨간검사'])}) · 지금 초록 -- 검사가 이 변경을 증언한다"
        else:
            out.update(공허=True, 말=(f"**공허** -- 검사({', '.join(검사[:3])})가 코드 변경 없이도(HEAD 위에 검사만 얹어도) "
                                    f"초록이다. 함수만 정의하고 안 부르거나, 글자가 있는지만 보거나, 바뀐 코드를 안 부르는 "
                                    f"검사다. 바뀐 코드({', '.join(행동[:3])})를 실제로 부르고 결과를 단언하게 다시 써라"))
        return out
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(tmp)], capture_output=True, text=True)
        shutil.rmtree(tmp, ignore_errors=True)


def 전체검사(판, 초: int = 1800, 지금트리: bool = True) -> dict:
    """그 판의 **검사 전부**를 격리 판에서 돌린다(scripts/tests.sh -- 목록이 한 군데에만 있다)."""
    from sandbox import run as SB
    r = SB.실행(["bash", "scripts/tests.sh"], repo=Path(판), 지금트리=지금트리, 초=초, 메모리MB=4096)
    if not r["돌았나"]:
        return {"돌았나": False, "통과": [], "실패": [], "건너뜀": [], "메모": r.get("메모", "판을 못 깜")}
    out = _검사줄뽑기((r["stdout"] or "") + (r["stderr"] or ""))
    out.update(돌았나=True, 끝값=int(r["끝값"]), 메모="")
    return out


def _헤드(repo: Path) -> str:
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30)
    return (r.stdout or "").strip()[:12]


def 바탕(repo=None, 초: int = 1800, 다시: bool = False) -> dict:
    """**고치기 전의 레포 전체 상태.** HEAD 별로 캐시한다 -- 같은 HEAD 에서 여러 번 개선해도 한 번만 돈다.

    깨끗한 HEAD 판(지금트리=False)에서 잰다: 작업 트리의 미커밋 변경이 섞이면 '원래 빨강' 과
    '내가 깨뜨림' 이 갈리지 않는다."""
    repo = Path(repo or REPO)
    sha = _헤드(repo)
    p = repo / 바탕상대
    if not 다시 and p.is_file():
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            if j.get("sha") == sha and j.get("돌았나"):
                j["캐시"] = True
                return j
        except (ValueError, OSError):
            pass
    r = 전체검사(repo, 초=초, 지금트리=False)
    r.update(sha=sha, 캐시=False)
    if r["돌았나"]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    return r


def 회귀(바탕결과: dict, 뒤결과: dict) -> dict:
    """{"새로깨짐","고쳐짐","그대로빨강"}. **새로깨짐이 있으면 개선이 아니다** -- 멀리서 깨뜨린 것이다."""
    전, 후 = set(바탕결과.get("실패", [])), set(뒤결과.get("실패", []))
    return {"새로깨짐": sorted(후 - 전), "고쳐짐": sorted(전 - 후), "그대로빨강": sorted(전 & 후)}


def 보고(r: dict) -> str:
    머리 = ("리허설(격리 판에서 미리 돌려 봤다) -- "
           + ("**그림자 계획판**" if r["그림자"] else "지금 작업 트리 사본")
           + f" · {r['걸린초']}초")
    줄 = [머리]
    if r["바뀐것"]:
        줄.append("  바뀐 코드: " + ", ".join(r["바뀐것"][:8]))
    for 이름, 끝값, 꼬리 in r["걸음"]:
        표 = "✓" if 끝값 == 0 else "✗"
        줄.append(f"  {표} {이름} (끝값 {끝값})")
        for x in (꼬리 or "").splitlines()[-3:]:
            if x.strip():
                줄.append(f"      {x[:160]}")
    for x in r["못잼"]:
        줄.append(f"  ? 못잼 {x[:140]} -- **못 돌린 것은 통과가 아니다**")
    if r.get("안덮임"):
        줄.append("  검사 없는 변경(버그가 샌다면 여기): " + ", ".join(r["안덮임"][:5]))
    줄.append("  판정: " + ("**초록 -- 실제 트리에 붙여도 된다**" if r["통과"]
                         else "**빨강 -- 붙이지 마라.** 위를 고치고 다시 시험하라"))
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="고치기 전에 격리 판에서 돌려 본다")
    ap.add_argument("--판", default="", help="리허설할 워크트리(비우면 계획판, 그것도 없으면 작업 트리)")
    ap.add_argument("--초", type=int, default=180)
    ap.add_argument("--전부", action="store_true", help="레포 전체를 돌려 회귀를 찾는다(느리다)")
    ap.add_argument("--바탕다시", action="store_true", help="HEAD 바탕을 다시 잰다")
    ap.add_argument("--저장소", default="")
    a = ap.parse_args()
    if a.바탕다시:
        바 = 바탕(Path(a.저장소) if a.저장소 else None, 다시=True)
        print(f"바탕: {바.get('sha')} · 빨강 {len(바.get('실패', []))}개 {바.get('실패', [])[:8]}")
        return 0
    r = 시험(Path(a.저장소) if a.저장소 else None, 판=(a.판 or None), 초=a.초, 전부=a.전부)
    print(보고(r))
    if r["못잼"] and not r["걸음"]:
        return 3
    return 0 if r["통과"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
