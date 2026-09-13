#!/usr/bin/env python3
r"""**먼 검사 사각지대를 없앤다** -- 전체 검사를 주기로 돌려 *늦게 발견되는 빨강*을 잰다.

## 왜 있나

`scripts/precheck.sh` 의 기본은 **빠른 길**이다(law 검사). 전체 검사는 6분이 넘어서, 답을 주기 전에
그것을 기다리면 CI 를 기다리던 것과 똑같아진다 -- 없애려던 바로 그 기다림이다. 그래서 먼 검사는
"CI 가 뒤늦게 알려 주게" 두었다. 그런데 **CI 를 안 본다**(사용자 지시 2026-09-08). 둘을 합치면
구멍이 된다: 먼 검사가 깨져도 아무도 안 본다. 실측 2026-09-09 의 `test_law_hwp` 가 그 구멍이었다 --
게이트가 며칠 빨간 채로 있었다.

## 무엇을 하나

**판정하지 않는다. 재고 적는다.** 이것은 답을 막는 관문이 아니다(그러면 기다림이 돌아온다).
주기로 깨끗한 HEAD 판에서 검사를 전부 돌리고, 빨간 것마다 **언제부터 빨간지**를 적는다.

    늦음(t) = 그 검사가 처음 빨갛게 보인 판부터 지금 판까지의 커밋 수

늦음이 크다는 것은 "그 사이의 모든 초록 보고가 그 검사를 안 보고 있었다" 는 뜻이다.

## 어디에 적나

`falsegreen/먼검사.jsonl` -- **추적된다.** `logs/` 는 .gitignore 에 있어서 VM 에만 남고
저장소에는 안 남는다(실측 2026-09-13: 6시간 사냥의 숫자를 손으로 붙여 받아야 했다).

    python3 farcheck.py                # 한 바퀴 돌고 적는다
    python3 farcheck.py --보고         # 지금까지의 사건
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
기록경로 = "falsegreen/먼검사.jsonl"
검사시한초 = 600
기본시한초 = 3600
맑은환경 = {"PYTHONDONTWRITEBYTECODE": "1"}
파이썬 = ["python3", "-B"]


def _git(repo: Path, *a) -> str:
    r = subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)
    return (r.stdout or "").strip()


def 검사목록(repo=None) -> "list[str]":
    repo = Path(repo or REPO)
    return sorted(f"tests/{x.name}" for x in (repo / "tests").glob("test_*.py"))


def 한바퀴(repo=None, 시한초: int = 기본시한초, 말하기=None, 검사들=None) -> dict:
    """깨끗한 HEAD 판에서 검사를 전부 돌린다. {판, 잰것, 빨강, 시한초과, 못잼}.

    **작업 디렉터리를 안 본다** -- 남이 받아 가는 것은 커밋된 나무뿐이다(`git add` 를 빠뜨린 파일이
    여기서는 없다). precheck 과 같은 까닭이다."""
    repo = Path(repo or REPO)
    말 = 말하기 or (lambda s: print(s, flush=True))
    검사들 = 검사들 if 검사들 is not None else 검사목록(repo)
    판 = Path(tempfile.mkdtemp(prefix="se-먼검사-"))
    r = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(판), "HEAD"],
                       capture_output=True, text=True)
    out = {"판": _git(repo, "rev-parse", "--short", "HEAD"), "잰것": 0,
           "빨강": [], "시한초과": [], "못잼": 0, "까닭": {}}
    if r.returncode != 0:
        out["못잼"] = len(검사들)
        말(f"[먼검사] HEAD 판을 못 꺼냈다: {r.stderr.strip()[:120]}")
        return out
    시작 = time.monotonic()
    env = {**os.environ, "PYTHONPATH": str(판), **맑은환경}
    try:
        for t in 검사들:
            if time.monotonic() - 시작 > 시한초:
                out["못잼"] += len(검사들) - out["잰것"]
                말(f"[먼검사] 시한 {시한초}초 -- 멈춘다 (못 잰 것 {out['못잼']}개)")
                break
            if not (판 / t).is_file():
                continue
            out["잰것"] += 1
            try:
                p = subprocess.run([*파이썬, t], cwd=str(판), env=env, capture_output=True,
                                   text=True, timeout=검사시한초)
                rc, 글 = p.returncode, (p.stdout or "") + (p.stderr or "")
            except subprocess.TimeoutExpired:
                # **시한을 넘긴 것은 빨강이 아니다 -- 못 잰 것이다.** 빨강으로 적으면 안 재고
                # 빨강이라 하는 꼴이 된다(mutate 의 시한초과와 같은 자리).
                out["시한초과"].append(t)
                out["못잼"] += 1
                말(f"[먼검사] 시한초과 {t} ({검사시한초}초) -- 빨강이라 하지 않는다")
                continue
            if rc != 0:
                out["빨강"].append(t)
                out["까닭"][t] = 글.strip().splitlines()[-1][:160] if 글.strip() else f"rc={rc}"
                말(f"[먼검사] 빨강 {t} -- {out['까닭'][t][:80]}")
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(판)],
                       capture_output=True, text=True)
        shutil.rmtree(판, ignore_errors=True)
    return out


def 기록들(repo=None) -> "list[dict]":
    p = Path(repo or REPO) / 기록경로
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


def 처음본판(repo=None) -> dict:
    """검사마다 **언제부터 빨간지**. 초록으로 관측되면 지운다 -- 복구도 측정으로 한다."""
    마지막: dict = {}
    for x in 기록들(repo):
        for t in x.get("빨강") or ():
            마지막.setdefault(t, x.get("판"))
        for t in (x.get("잰것목록") or ()):
            if t not in (x.get("빨강") or ()) and t in 마지막:
                del 마지막[t]
    return 마지막


def _커밋수(repo: Path, 이전: str, 지금: str) -> "int | None":
    if not 이전 or not 지금:
        return None
    r = subprocess.run(["git", "-C", str(repo), "rev-list", "--count", f"{이전}..{지금}"],
                       capture_output=True, text=True)
    try:
        return int((r.stdout or "").strip())
    except ValueError:
        return None                                 # **모르면 모른다고 한다.** 0 으로 안 채운다


def 사건기록(repo=None, 결과: dict = None, 검사들=None) -> dict:
    """한 바퀴의 결과를 **추적되는 경로**에 덧붙인다. 늦음을 여기서 센다."""
    repo = Path(repo or REPO)
    결과 = 결과 if 결과 is not None else 한바퀴(repo)
    이전 = 처음본판(repo)
    지금 = 결과.get("판") or ""
    늦음 = {}
    for t in 결과.get("빨강") or ():
        시작판 = 이전.get(t) or 지금
        늦음[t] = {"처음본판": 시작판, "커밋수": _커밋수(repo, 시작판, 지금)}
    줄 = {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "판": 지금, "잰것": 결과.get("잰것", 0),
          "잰것목록": 검사들 if 검사들 is not None else 검사목록(repo),
          "빨강": 결과.get("빨강") or [], "시한초과": 결과.get("시한초과") or [],
          "못잼": 결과.get("못잼", 0), "까닭": 결과.get("까닭") or {},
          "새빨강": sorted(set(결과.get("빨강") or ()) - set(이전)),
          "고쳐진것": sorted(set(이전) - set(결과.get("빨강") or ())),
          "늦음": 늦음}
    p = repo / 기록경로
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")
    return 줄


def 보고(repo=None) -> str:
    것 = 기록들(repo)
    if not 것:
        return f"{기록경로} 가 비어 있다 -- `python3 farcheck.py` 를 한 번 돌려라"
    마 = 것[-1]
    줄 = [f"**먼 검사** -- 기록 {len(것)}번 · 마지막 {str(마.get('때'))[:19]} (판 {마.get('판')})",
         f"검사 {마.get('잰것', 0)}개 · 빨강 {len(마.get('빨강') or ())} · "
         f"시한초과 {len(마.get('시한초과') or ())} · 못잼 {마.get('못잼', 0)}"]
    for t in (마.get("빨강") or ())[:20]:
        늦 = (마.get("늦음") or {}).get(t) or {}
        n = 늦.get("커밋수")
        줄.append(f"  {t} -- 커밋 {n if n is not None else '?'}개 전부터(판 {늦.get('처음본판')}) · "
                  f"{str((마.get('까닭') or {}).get(t, ''))[:70]}")
    if 마.get("새빨강"):
        줄.append("**새로 빨개진 것**: " + ", ".join(마["새빨강"]))
    if 마.get("고쳐진것"):
        줄.append("고쳐진 것: " + ", ".join(마["고쳐진것"]))
    늦은것 = [(t, (마.get("늦음") or {}).get(t, {}).get("커밋수") or 0) for t in (마.get("빨강") or ())]
    if 늦은것:
        t, n = max(늦은것, key=lambda kv: kv[1])
        줄.append(f"\n가장 오래 안 들킨 것: {t} -- 커밋 {n}개. "
                  "그 사이의 모든 초록 보고가 이 검사를 안 보고 있었다.")
    return "\n".join(줄)


def 밀기(repo=None, 말하기=None) -> "tuple[bool, str]":
    r"""기록을 **커밋하고 민다.** 안 하면 배포가 지운다.

    배포(`deploy-oracle.yml`)가 `git reset --hard origin/main` 을 한다. 그것은 추적 안 되는 파일은
    남기지만 **추적되는 파일의 커밋 안 된 변경은 지운다.** 기록을 추적되는 경로에 두기로 한 이상,
    커밋하지 않으면 다음 배포에 사라진다 -- `logs/` 에 두었을 때와 똑같이 아무것도 안 남는다.

    rebase 도 --force 도 쓰지 않는다. origin 이 앞서면 `gitsync.reconcile` 이 merge 한다."""
    repo = Path(repo or REPO)
    말 = 말하기 or (lambda s: print(s, flush=True))

    def git(a):
        return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)

    br = git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    if not br or br == "HEAD":
        return False, "지금 어느 브랜치도 아니다 -- 밀지 않는다"
    git(["add", "--", 기록경로])
    if not git(["diff", "--cached", "--quiet", "--", 기록경로]).returncode:
        return False, "적을 것이 없다"
    c = git(["commit", "-m", "먼 검사 기록 -- 전체 검사를 주기로 돌린 결과", "--", 기록경로])
    if c.returncode != 0:
        return False, f"커밋 못 함: {c.stderr.strip()[:120]}"
    밀림 = git(["push", "-u", "origin", br])
    if 밀림.returncode == 0:
        return True, f"{br} 에 밀었다"
    import gitsync
    됨, 왜 = gitsync.reconcile(git)                  # merge 다. rebase 도 --force 도 아니다
    말(f"[먼검사] 밀기 실패 -- {왜}")
    if not 됨:
        return False, 왜
    다시 = git(["push", "-u", "origin", br])
    return (다시.returncode == 0), (f"{왜} 뒤 다시 밀었다" if 다시.returncode == 0
                                 else f"{왜} 뒤에도 못 밀었다: {다시.stderr.strip()[:120]}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="먼 검사 사각지대 -- 전체 검사를 주기로 돌려 늦음을 잰다")
    ap.add_argument("--시한", type=int, default=기본시한초, help=f"초 (기본 {기본시한초})")
    ap.add_argument("--보고", action="store_true", help="기록만 찍는다")
    ap.add_argument("--검사", action="append", default=None, help="이 검사만 (여러 번)")
    ap.add_argument("--주기", type=int, default=0, help="이 초마다 되풀이한다 (0=한 번만)")
    ap.add_argument("--횟수", type=int, default=0, help="--주기 와 함께: 이만큼만 (0=끝없이)")
    ap.add_argument("--밀기", action="store_true", help="기록을 커밋하고 민다 (배포가 지우지 않게)")
    a = ap.parse_args(argv)
    if a.보고:
        print(보고())
        return 0
    바퀴 = 0
    while True:
        바퀴 += 1
        r = 한바퀴(시한초=a.시한, 검사들=a.검사)
        사건기록(결과=r, 검사들=a.검사)
        print()
        print(보고())
        if a.밀기:
            됨, 왜 = 밀기()
            print(f"[밀기] {'됨' if 됨 else '안 됨'} -- {왜}")
        if not a.주기 or (a.횟수 and 바퀴 >= a.횟수):
            break
        time.sleep(a.주기)
    # **끝값 0 이다 -- 막는 관문이 아니다.** 여기서 막으면 기다림이 돌아온다.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
