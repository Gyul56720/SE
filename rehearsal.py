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


def _판변경(판: Path) -> "tuple[list[str], list[str], list[str]]":
    """판에서 HEAD 대비 바뀐 파일. (검사파일, 코드파일, 지운파일) -- 모두 저장소 상대경로, .py 만."""
    r = subprocess.run(["git", "-C", str(판), "status", "--porcelain", "-z", "--untracked-files=all"],
                       capture_output=True, text=True)
    검사, 코드, 지움 = [], [], []
    항목 = [x for x in r.stdout.split("\0") if x]
    i = 0
    while i < len(항목):
        줄 = 항목[i]; i += 1
        코드글, rel = 줄[:2], 줄[3:]
        if "R" in 코드글 or "C" in 코드글:
            i += 1
        if not rel.endswith(".py"):
            continue
        if "D" in 코드글:
            지움.append(rel)
        elif rel.startswith("tests/") and Path(rel).name.startswith("test_"):
            검사.append(rel)
        else:
            코드.append(rel)
    return 검사, 코드, 지움


def _HEAD글(판: Path, rel: str) -> "str | None":
    r = subprocess.run(["git", "-C", str(판), "show", f"HEAD:{rel}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


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
