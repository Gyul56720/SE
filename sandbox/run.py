"""sandbox -- 실험은 깨끗한 판에서 돌린다. 저장소는 실험대가 아니다.

왜 있나: run_shell 은 진짜 저장소 안에서 돈다. 그래서 "라노벨 상황극" 요청 하나가
`scripts/drift.sh` 를 20줄 촌극으로 덮었다(실측 2026-09-10, 커밋 4cd4473). 실험이
저장소를 만지면 실수가 그대로 배포판이 된다.

수법은 새것이 아니다 -- `scripts/precheck.sh` 가 이미 하는 것(HEAD 를 임시 워크트리로)을
모듈로 뺐다. 세 겹이다.

  판   -- HEAD 워크트리(기본) 또는 `--지금트리`(HEAD 워크트리 + 미커밋 변경). **둘 다 git
          워크트리다** -- 바탕과 후보가 다른 종류면 git 을 부르는 검사가 후보에서만 죽어
          유령 회귀가 난다(실측 2026-09-12). 안에서 무엇을 쓰고 지우든 저장소에 닿지 않는다.
          requirements.txt 에 있는데 없는 배포는 캐시 자리에 한 번 깔아 PYTHONPATH 로 준다(저장소에는 안 깐다).
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
    """지금 작업 트리의 사본 -- **HEAD 워크트리 위에 미커밋 변경을 덮는다.**

    실측 2026-09-12(VM): `!개선` 의 레포 전체 시뮬이 매번 "새로 깨짐 6개" 로 빨갰다. 패치와 상관
    없는 검사들(test_relay · test_seek_report · test_jaso_sift …)이었다. 바탕은 HEAD **워크트리**
    (git 저장소)에서 재고, 후보는 파일만 베낀 **사본**(git 이 아니다)에서 쟀다 -- git 을 부르는
    검사(`git rev-parse` · `check-ignore`)가 후보에서만 죽어 유령 회귀가 됐다. 판정이 거짓말이면
    두뇌는 무엇을 고쳐도 못 끝낸다. 그래서 후보도 워크트리로 깐다: 둘이 같은 종류다.

    .gitignore 에 걸린 것(.env · venv 등)은 여전히 안 딸려 간다 -- git status 가 안 세니까."""
    r = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(tmp), "HEAD"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return f"워크트리를 못 꺼냈다: {r.stderr.strip()[:300]}", False
    # -z: 비ASCII(한글) 경로 인용을 없앤다. --untracked-files=all: 디렉터리째가 아니라 파일마다.
    st = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "-z", "--untracked-files=all"],
                        capture_output=True, text=True)
    if st.returncode != 0:
        return f"변경 목록을 못 얻었다: {st.stderr.strip()[:300]}", False
    항목 = [x for x in st.stdout.split("\0") if x]
    i, 덮음, 지움 = 0, 0, 0
    while i < len(항목):
        줄 = 항목[i]; i += 1
        코드, 경로 = 줄[:2], 줄[3:]
        if "R" in 코드 or "C" in 코드:          # 이름 바꿈: 다음 항목이 원래 경로
            i += 1
        src, dst = repo / 경로, tmp / 경로
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst); 덮음 += 1
        elif dst.exists():
            dst.unlink(); 지움 += 1
    sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    return f"HEAD {sha} 워크트리 + 미커밋 {덮음}개 덮음" + (f" · {지움}개 지움" if 지움 else ""), True


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


def _치우기(repo: Path, tmp: Path, 워크트리등록: bool = True) -> None:
    """두 판 다 워크트리라 늘 지운다. `worktree add` 가 됐는데 그 뒤(status)가 실패한 경우도
    등록은 남아 있다 -- 그래서 성공 여부를 안 묻고 지운다(워크트리가 아니면 git 이 조용히 거절)."""
    if 워크트리등록:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                        str(tmp)], capture_output=True, text=True)
        subprocess.run(["git", "-C", str(repo), "worktree", "prune"],
                       capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 새 의존성: 캐시 자리에 한 번 깐다
# 실측 2026-09-12(VM): `!개선` 이 fpdf 로 PDF 를 만드는 새 모듈과 requirements.txt 한 줄을 붙였는데
# 시뮬이 `ModuleNotFoundError: fpdf` 로 빨갰다. 기능은 다 됐는데 판정이 "안 깔린 라이브러리" 를
# 두뇌 탓으로 돌렸다 -- 두뇌는 requirements.txt 밖에 못 만지니 무엇을 고쳐도 못 끝난다.
# 그래서 실행기가 판의 requirements.txt 를 읽어 **없는 것만** 캐시 자리에 깐다(~/.cache/se-sandbox-deps,
# SE_DEPS_CACHE 로 바꾼다). 저장소와 시스템 파이썬에는 안 깐다. 시험에서는 pip 을 가짜로 바꿔 끼운다(망 없이 돈다).
pip깔기 = None
_의존성_초 = 240


def _요구이름(줄: str) -> "str | None":
    """requirements.txt 한 줄에서 배포 이름만. 옵션 줄(-r · -e · --…)과 주석은 None."""
    import re
    줄 = 줄.split("#", 1)[0].strip()
    if not 줄 or 줄.startswith("-"):
        return None
    m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", 줄)
    return m.group(1) if m else None


def _깔렸나(이름: str) -> bool:
    from importlib import metadata
    후보 = {이름, 이름.replace("_", "-"), 이름.replace("-", "_"), 이름.lower()}
    for n in 후보:
        try:
            metadata.distribution(n)
            return True
        except metadata.PackageNotFoundError:
            continue
    return False


def _pip기본(spec: str, 어디: Path, 초: int) -> "tuple[bool, str]":
    r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                        "--no-input", "--target", str(어디), spec],
                       capture_output=True, text=True, timeout=초)
    return r.returncode == 0, (r.stderr or r.stdout or "").strip()[-300:]


def _캐시뿌리() -> Path:
    return Path(os.environ.get("SE_DEPS_CACHE") or (Path.home() / ".cache" / "se-sandbox-deps"))


def _캐시자리(spec: str) -> Path:
    import hashlib
    import re
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", spec)[:40]
    return _캐시뿌리() / f"{slug}-{hashlib.sha256(spec.encode()).hexdigest()[:8]}"


def 새의존성깔기(tmp: Path, env: dict, 초: int = _의존성_초) -> str:
    """판의 requirements.txt 에 있는데 이 파이썬에 없는 배포를 **캐시(배포 하나에 자리 하나)** 에 깔고
    그 자리들을 PYTHONPATH 맨 앞에 둔다. 같은 줄은 한 번만 깐다 -- 리허설은 검사마다 판을 새로 까는데
    (검사상한 10), 매번 pip 을 돌리면 그것만으로 몇 분이다. 저장소와 시스템 파이썬에는 안 깐다.
    돌려주는 것은 메모 한 줄(아무것도 안 했으면 빈 글)."""
    req = tmp / "requirements.txt"
    if not req.is_file():
        return ""
    없는: list[str] = []
    for 줄 in req.read_text(encoding="utf-8", errors="replace").splitlines():
        이름 = _요구이름(줄)
        if 이름 and not _깔렸나(이름):
            없는.append(줄.split("#", 1)[0].strip())
    if not 없는:
        return ""
    새로, 재사용, 실패 = [], [], []
    자리들: list[str] = []
    for spec in 없는:
        어디 = _캐시자리(spec)
        if (어디 / ".ok").is_file():
            재사용.append(spec); 자리들.append(str(어디))
            continue
        shutil.rmtree(어디, ignore_errors=True)           # 반쯤 깔린 자리는 믿지 않는다
        어디.mkdir(parents=True, exist_ok=True)
        try:
            ok, 말 = (pip깔기 or _pip기본)(spec, 어디, 초)
        except (subprocess.TimeoutExpired, OSError) as e:      # noqa: PERF203
            ok, 말 = False, f"{type(e).__name__}: {e}"
        if ok:
            (어디 / ".ok").write_text(spec + "\n", encoding="utf-8")
            새로.append(spec); 자리들.append(str(어디))
        else:
            shutil.rmtree(어디, ignore_errors=True)
            실패.append(f"{spec} ({말[-120:]})")
    if 자리들:
        env["PYTHONPATH"] = os.pathsep.join(자리들) + os.pathsep + env.get("PYTHONPATH", "")
    조각 = []
    if 새로:
        조각.append(f"새로 깐 의존성 {len(새로)}개: {', '.join(새로)}")
    if 재사용:
        조각.append(f"캐시에서 쓴 의존성 {len(재사용)}개")
    if 실패:
        조각.append(f"못 깐 의존성 {len(실패)}개: {'; '.join(실패)}")
    return " · ".join(조각)


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
        워크트리등록 = True                      # 두 판 다 워크트리다(_치우기 참고)
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
        의존메모 = "" if 망차단 else 새의존성깔기(tmp, env)     # 망을 끊었으면 깔 수 없다 -- 그대로 돈다
        if 의존메모:
            판 += " · " + 의존메모
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
