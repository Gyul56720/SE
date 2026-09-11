"""audit -- 변경을 **실제로 돌려 보는** 감사. 겉을 훑지 않는다.

이 저장소에서 버그를 잡아 온 것은 눈이 아니라 실행이다: seek.sh 는 `bash -n` 과
grep 을 다 통과하고도 한 줄도 안 돌았고(한글 변수명), sandbox 의 첫 검사는 한글
파일명이 복사에서 통째로 빠지는 것을 잡았다(git quotepath). 그래서 감사는 이렇다:

  바뀐 파일을 찾고 -> 그 파일을 붙드는 검사를 찾아 -> **격리 판에서 끝까지 돌린다**

  미커밋 감사(기본): 지금 트리 사본에서 돈다 -- 커밋하기 **전에** 버그를 잡는 자리다.
  커밋 감사(--커밋): HEAD 워크트리에서 돈다 -- 방금 커밋이 성한지 뒤늦게 본다.

검사를 찾는 법(코드가, 결정적으로): (1) 이름 -- foo/bar.py 면 tests/test_bar*.py 와
tests/test_foo*.py, (2) 임포트 -- 그 모듈을 import 하는 검사 파일. 바뀐 것이 검사
파일 자신이면 그 파일이 곧 검사다.

**검사 없는 변경은 없는 대로 크게 말한다.** 그 자리가 버그가 새는 자리다. 다만 기본
끝값은 그것으로 빨간불을 내지 않는다 -- 늘 우는 경보는 아무도 안 듣는다. `--엄격`
이면 안 덮인 .py 변경도 끝값 1 이다.

쓰기:
    python3 audit/run.py                # 미커밋 변경 감사
    python3 audit/run.py --커밋          # 마지막 커밋(HEAD~1..HEAD) 감사
    python3 audit/run.py --엄격
끝값: 0 돌린 검사 다 통과 · 1 실패 있음(--엄격이면 안 덮임도) · 3 감사 자체를 못 했다
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from sandbox import run as 격리  # noqa: E402


def _git(repo: Path, args: "list[str]") -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True)


def 변경파일(repo: Path, 커밋: bool) -> "list[str] | None":
    """바뀐 파일의 상대경로. -z 로 받는다(한글 경로 인용 문제, sandbox 가 실측으로
    배운 그 자리). None 이면 git 조회 자체가 실패한 것이다."""
    if 커밋:
        base = _git(repo, ["rev-parse", "--verify", "-q", "HEAD~1"])
        기준 = ["HEAD~1", "HEAD"] if base.returncode == 0 else \
            ["4b825dc642cb6eb9a060e54bf8d69288fbee4904", "HEAD"]  # git 의 빈 트리
        r = _git(repo, ["diff", "--name-only", "-z", *기준])
        if r.returncode != 0:
            return None
        return [x for x in r.stdout.split("\0") if x]
    diff = _git(repo, ["diff", "--name-only", "-z", "HEAD"])
    새것 = _git(repo, ["ls-files", "-z", "--others", "--exclude-standard"])
    if diff.returncode != 0 or 새것.returncode != 0:
        return None
    out = [x for x in diff.stdout.split("\0") if x]
    out += [x for x in 새것.stdout.split("\0") if x and x not in out]
    return out


def _모듈이름(rel: str) -> "list[str]":
    """foo/bar.py -> [bar, foo] · dispatch.py -> [dispatch]. 검사 이름과 임포트를 이
    이름들로 찾는다."""
    p = Path(rel)
    names = [p.stem]
    if p.parent != Path("."):
        names.append(p.parts[0])
    return [n for n in names if n and n != "__init__"]


def 검사찾기(repo: Path, 바뀐py: "list[str]") -> "tuple[dict, list]":
    """{바뀐 파일: 걸린 검사들}, 안 덮인 파일들. 이름과 임포트 둘 다 본다."""
    검사들 = sorted((repo / "tests").glob("test_*.py")) if (repo / "tests").is_dir() else []
    본문 = {t: t.read_text(encoding="utf-8", errors="replace") for t in 검사들}
    걸림: dict = {}
    안덮임: list = []
    for rel in 바뀐py:
        if rel.startswith("tests/") and Path(rel).name.startswith("test_"):
            걸림[rel] = {rel}                      # 바뀐 검사는 자신이 곧 검사다
            continue
        찾은 = set()
        for 이름 in _모듈이름(rel):
            for t in 검사들:
                if t.stem.startswith(f"test_{이름}"):
                    찾은.add(str(t.relative_to(repo)))
            임포트 = re.compile(
                rf"^\s*(import\s+{re.escape(이름)}\b|from\s+{re.escape(이름)}\b)", re.M)
            for t, text in 본문.items():
                if 임포트.search(text):
                    찾은.add(str(t.relative_to(repo)))
        if 찾은:
            걸림[rel] = 찾은
        else:
            안덮임.append(rel)
    return 걸림, 안덮임


def 감사(repo=None, 커밋: bool = False, 초: int = 180) -> dict:
    """{결과: [(검사, 끝값, 꼬리)], 안덮임: [...], 안봄: [...], 변경: [...]}.
    변경이 None 이면 git 을 못 봤다 -- 모르는 것은 안 된 것으로 다뤄라."""
    repo = Path(repo or REPO)
    변경 = 변경파일(repo, 커밋)
    if 변경 is None:
        return {"결과": None, "안덮임": [], "안봄": [], "변경": None}
    바뀐py = [c for c in 변경 if c.endswith(".py")]
    안봄 = [c for c in 변경 if not c.endswith(".py")]
    걸림, 안덮임 = 검사찾기(repo, 바뀐py)
    돌릴 = sorted({t for ts in 걸림.values() for t in ts})
    결과 = []
    for t in 돌릴:
        r = 격리.실행(["python3", t], repo=repo, 초=초, 메모리MB=4096, 지금트리=not 커밋)
        꼬리 = ((r["stdout"] or "") + (r["stderr"] or "")).strip().splitlines()[-6:]
        if not r["돌았나"]:
            결과.append((t, 3, [r["메모"]]))
        else:
            결과.append((t, r["끝값"], 꼬리))
    return {"결과": 결과, "안덮임": 안덮임, "안봄": 안봄, "변경": 변경}


def 보고(r: dict) -> str:
    if r["변경"] is None:
        return "git 을 못 봤다 -- 감사 못 함 (모르는 것은 안 된 것으로 다뤄라)"
    if not r["변경"]:
        return "변경이 없다 -- 감사할 것이 없다"
    lines = []
    for t, rc, 꼬리 in r["결과"] or []:
        if rc == 0:
            lines.append(f"  OK   {t}")
        else:
            lines.append(f"  실패 {t} (끝값 {rc})")
            lines += [f"         {x}" for x in 꼬리]
    if r["안덮임"]:
        lines.append(f"  **검사 없는 .py 변경 {len(r['안덮임'])}개 -- 버그가 샌다면 여기다:**")
        lines += [f"       {c}" for c in r["안덮임"]]
    if r["안봄"]:
        lines.append(f"  (안 봄: .py 아닌 변경 {len(r['안봄'])}개)")
    return "\n".join(lines) or "돌릴 검사도, 안 덮인 .py 도 없다"


def main() -> int:
    ap = argparse.ArgumentParser(description="변경을 실제로 돌려 보는 감사")
    ap.add_argument("--커밋", action="store_true", help="미커밋 대신 HEAD~1..HEAD 를 본다")
    ap.add_argument("--엄격", action="store_true", help="검사 없는 .py 변경도 빨간불")
    ap.add_argument("--초", type=int, default=180, help="검사 하나의 시간 상한")
    args = ap.parse_args()
    r = 감사(커밋=args.커밋, 초=args.초)
    print(보고(r))
    if r["변경"] is None:
        return 3
    실패 = any(rc != 0 for _, rc, _ in r["결과"] or [])
    if 실패 or (args.엄격 and r["안덮임"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
