"""sandbox -- 실험은 깨끗한 판에서 돌린다. 저장소는 실험대가 아니다.

왜 있나: run_shell 은 진짜 저장소 안에서 돈다. 그래서 "라노벨 상황극" 요청 하나가
`scripts/drift.sh` 를 20줄 촌극으로 덮었다(실측 2026-09-10, 커밋 4cd4473). 실험이
저장소를 만지면 실수가 그대로 배포판이 된다.

수법은 새것이 아니다 -- `scripts/precheck.sh` 가 이미 하는 것(HEAD 를 임시 워크트리로)을
모듈로 뺐다. 세 겹이다.

  판   -- HEAD 워크트리(기본) 또는 `--지금트리`(작업 트리 사본). 어느 쪽이든 안에서
          무엇을 쓰고 지우든 저장소에 닿지 않는다.
  고삐 -- 벽시계 시간(기본 180초, 넘으면 프로세스 그룹째 죽인다) · CPU(RLIMIT_CPU) ·
          메모리(RLIMIT_AS).
  환경 -- 비밀 변수는 기본으로 지운다(secret_filter.secret_names). `--키포함` 을
          명시해야 남는다. `--망차단` 은 unshare 가 되는 곳에서만 -- **못 끊는 환경이면
          끊은 척하고 돌리지 않는다**(돌았나=False). 검사하지 않은 초록불이 검사한
          빨간불보다 나쁘다.

산출물은 `--가져와 <상대경로>` 로만 밖으로 나온다. `sandbox/out/<런>/` 에 담기고,
경로는 워크트리 안으로만 해석된다(G014 와 같은 규율 -- 돌기 **전에** 검사해서, 다 돌고
나서야 못 가져온다고 하는 낭비를 없앤다).

쓰기:
    python3 sandbox/run.py -- <명령...>                  # HEAD 판에서
    python3 sandbox/run.py --지금트리 -- <명령...>        # 작업 트리 사본에서
    python3 sandbox/run.py --가져와 out/r.txt -- <명령...>
    python3 sandbox/run.py --시간 60 --메모리 1024 --망차단 -- <명령...>

끝값: 0 명령이 통과 · 1 명령이 실패(시간 초과 포함) · 3 판 자체를 못 깔았다.
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import secret_filter  # noqa: E402  (표준 라이브러리만 쓰는 모듈이다)

OUT_DIR = Path(__file__).resolve().parent / "out"
# 산출물 한 개 상한. 실험 산출물로 저장소/디스크가 부풀지 않게 한다.
산출물_상한 = 5 * 1024 * 1024


def _경로검사(rel: str) -> str:
    """가져올 경로는 워크트리 안 상대경로만. 밖을 가리키면 ValueError."""
    rel = (rel or "").strip()
    if not rel or rel.startswith(("/", "~")):
        raise ValueError(f"절대경로는 못 가져온다: {rel!r}")
    if any(part == ".." for part in Path(rel).parts):
        raise ValueError(f"워크트리 밖의 경로는 가져올 수 없다: {rel!r}")
    return rel


def _워크트리안(worktree: Path, rel: str) -> Path:
    """실제 워크트리 기준으로 한 번 더 확인한다 -- 심볼릭 링크로 밖으로 풀리는 것을 잡는다."""
    p = (worktree / _경로검사(rel)).resolve()
    wt = worktree.resolve()
    if p != wt and wt not in p.parents:
        raise ValueError(f"워크트리 밖으로 풀리는 경로다: {rel!r}")
    return p


def 망차단_가능() -> bool:
    """unshare 로 네트워크 네임스페이스를 뗄 수 있는 환경인가. 컨테이너에 따라 안 된다."""
    try:
        r = subprocess.run(["unshare", "-r", "-n", "true"],
                           capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def _환경(키포함: bool) -> dict:
    """자식 환경. 기본은 비밀 변수를 지운 사본 -- 실험 코드는 키가 필요 없고, 필요하면
    그렇다고 말하게(--키포함) 한다. public 채널만 지우는 child_env 와 달리 여기는
    채널과 무관하게 지운다: 격리 판의 기본값은 '없음' 이다."""
    env = dict(os.environ)
    if not 키포함:
        for name in secret_filter.secret_names():
            env.pop(name, None)
    return env


def _고삐(초: int, 메모리MB: int):
    """자식 프로세스에 거는 제한. setsid 로 그룹을 만들어 시간 초과 시 통째로 죽인다."""
    def 묶기():
        os.setsid()
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (초, 초 + 5))
        except (ValueError, OSError):
            pass
        if 메모리MB:
            b = int(메모리MB) * 1024 * 1024
            try:
                resource.setrlimit(resource.RLIMIT_AS, (b, b))
            except (ValueError, OSError):
                pass
    return 묶기


def _깨끗한판(repo: Path, tmp: Path) -> "tuple[str, bool]":
    """HEAD 를 임시 워크트리로 꺼낸다. 커밋 안 된 것은 여기 없다 -- 그것이 요점이다
    (precheck 가 다섯 번 앓은 병에서 배운 것: 남이 받아 가는 것은 커밋된 나무뿐이다)."""
    r = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach",
                        str(tmp), "HEAD"], capture_output=True, text=True)
    if r.returncode != 0:
        return f"워크트리를 못 꺼냈다: {r.stderr.strip()[:300]}", False
    sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    return f"HEAD {sha}", True


def _지금판(repo: Path, tmp: Path) -> "tuple[str, bool]":
    """지금 작업 트리의 사본. 커밋 안 한 변경을 실험할 때 쓴다. .gitignore 에 걸린 것
    (.env · venv 등)은 복사하지 않는다 -- 비밀 파일이 판으로 딸려 가는 길을 막는다."""
    # -z 가 없으면 git 이 비ASCII 경로를 "\354..." 로 인용해서(core.quotepath 기본값)
    # 한글 파일명이 통째로 복사에서 빠진다(실측: 이 모듈의 첫 검사가 잡았다). 이 저장소는
    # 파일 이름부터 한글이다 -- NUL 구분으로 받아 인용을 아예 없앤다.
    r = subprocess.run(["git", "-C", str(repo), "ls-files", "-z", "--cached", "--others",
                        "--exclude-standard"], capture_output=True, text=True)
    if r.returncode != 0:
        return f"파일 목록을 못 얻었다: {r.stderr.strip()[:300]}", False
    for line in r.stdout.split("\0"):
        if not line:
            continue
        src = repo / line
        if not src.is_file():
            continue  # 지웠는데 아직 인덱스에 남은 것
        dst = tmp / line
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return "지금 트리 사본", True


def _꺼내기(tmp: Path, 가져와: "list[str]", 밖으로) -> "list[str]":
    if not 가져와:
        return []
    런 = time.strftime("%Y%m%d-%H%M%S") + "-" + os.urandom(3).hex()
    받을곳 = Path(밖으로 or OUT_DIR) / 런
    담긴: list[str] = []
    for rel in 가져와:
        src = _워크트리안(tmp, rel)
        if not src.is_file():
            담긴.append(f"(없다) {rel}")
            continue
        if src.stat().st_size > 산출물_상한:
            담긴.append(f"(너무 크다, {src.stat().st_size:,}바이트) {rel}")
            continue
        dst = 받을곳 / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        담긴.append(str(dst))
    return 담긴


def _치우기(repo: Path, tmp: Path, 워크트리등록: bool) -> None:
    if 워크트리등록:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                        str(tmp)], capture_output=True, text=True)
        subprocess.run(["git", "-C", str(repo), "worktree", "prune"],
                       capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)


def 실행(argv: "list[str]", *, 지금트리: bool = False, 초: int = 180,
        메모리MB: int = 2048, 망차단: bool = False, 키포함: bool = False,
        가져와: "list[str] | tuple" = (), repo=None, 밖으로=None) -> dict:
    """argv 를 격리 판에서 돌리고 결과를 dict 로 돌려준다.

    돌려주는 것: 끝값 · stdout · stderr · 산출물(밖으로 담긴 경로들) · 판 · 메모 ·
    돌았나(False 면 판 자체를 못 깔아 명령이 한 줄도 안 돈 것 -- 끝값과 갈라 읽어라).
    """
    가져와 = [_경로검사(r) for r in 가져와]  # 돌기 전에 -- 다 돌고 나서 거절하면 낭비다
    if 망차단:
        if not 망차단_가능():
            return {"끝값": 3, "stdout": "", "stderr": "", "산출물": [], "판": "",
                    "돌았나": False,
                    "메모": "망을 못 끊는 환경이다 -- 끊은 척하고 돌리지 않는다 (unshare -r -n 불가)"}
        argv = ["unshare", "-r", "-n", "--"] + list(argv)
    repo = Path(repo or REPO)
    tmp = Path(tempfile.mkdtemp(prefix="sandbox-"))
    워크트리등록 = False
    try:
        판, ok = _지금판(repo, tmp) if 지금트리 else _깨끗한판(repo, tmp)
        워크트리등록 = ok and not 지금트리
        if not ok:
            return {"끝값": 3, "stdout": "", "stderr": 판, "산출물": [], "판": "",
                    "돌았나": False,
                    "메모": "판을 못 깔았다 -- 모르는 것은 안 된 것으로 다룬다"}
        시작 = time.monotonic()
        # **판의 뿌리를 PYTHONPATH 에 둔다.** 실측 2026-09-12(VM): `!개선` 이 지은 tests/test_x.py 가
        # `from utils.x import …` 를 하다 ModuleNotFoundError 로 레포 전체 시뮬을 빨갛게 했다. 저장소
        # 검사들은 제 손으로 뿌리를 sys.path 에 넣지만 모델이 지은 검사는 안 그럴 수 있다 -- 기능이
        # 다 됐는데 그 한 줄로 빨강이면 판정이 거짓말이다. 실행기가 뿌리를 놓아 주면 함정이 사라진다.
        env = _환경(키포함)
        env["PYTHONPATH"] = str(tmp) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        proc = subprocess.Popen(
            list(argv), cwd=str(tmp), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors="replace", preexec_fn=_고삐(초, 메모리MB))
        try:
            stdout, stderr = proc.communicate(timeout=초)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            stdout, stderr = proc.communicate()
            return {"끝값": 124, "stdout": stdout or "", "stderr": stderr or "",
                    "산출물": [], "판": 판, "돌았나": True,
                    "메모": f"{초}초 안에 안 끝나 프로세스 그룹째 죽였다"}
        return {"끝값": proc.returncode, "stdout": stdout or "", "stderr": stderr or "",
                "산출물": _꺼내기(tmp, 가져와, 밖으로), "판": 판, "돌았나": True,
                "메모": "", "걸린초": round(time.monotonic() - 시작, 1)}
    finally:
        _치우기(repo, tmp, 워크트리등록)


def main() -> int:
    ap = argparse.ArgumentParser(description="격리 판에서 명령을 돌린다")
    ap.add_argument("--지금트리", action="store_true", help="HEAD 대신 작업 트리 사본")
    ap.add_argument("--시간", type=int, default=180)
    ap.add_argument("--메모리", type=int, default=2048, help="MB. 0 이면 제한 없음")
    ap.add_argument("--망차단", action="store_true")
    ap.add_argument("--키포함", action="store_true", help="비밀 환경변수를 지우지 않는다")
    ap.add_argument("--가져와", action="append", default=[], metavar="상대경로")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("argv", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    argv = args.argv[1:] if args.argv and args.argv[0] == "--" else args.argv
    if not argv:
        print("돌릴 명령이 없다:  python3 sandbox/run.py -- <명령...>")
        return 3
    try:
        r = 실행(argv, 지금트리=args.지금트리, 초=args.시간, 메모리MB=args.메모리,
                망차단=args.망차단, 키포함=args.키포함, 가져와=args.가져와)
    except ValueError as e:
        print(f"못 돌린다: {e}")
        return 3
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"[판: {r['판'] or '-'}] 끝값 {r['끝값']}"
              + (f" -- {r['메모']}" if r["메모"] else ""))
        if r["stdout"]:
            print(r["stdout"], end="" if r["stdout"].endswith("\n") else "\n")
        if r["stderr"]:
            print("--- stderr ---")
            print(r["stderr"], end="" if r["stderr"].endswith("\n") else "\n")
        for p in r["산출물"]:
            print(f"산출물: {p}")
    if not r["돌았나"]:
        return 3
    return 0 if r["끝값"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
