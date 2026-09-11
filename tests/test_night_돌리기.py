"""scripts/night.sh 를 임시 저장소에서 **끝까지 돌려** 붙든다.

seek.sh 의 교훈 그대로다: `bash -n` 과 grep 은 한 줄도 안 도는 파일을 통과시켰다.
그래서 bare 원격 + 작업 클론을 지어 실제로 돌리고, **원격에 색인 커밋이 실제로
올라갔는지**까지 본다. 게이트가 빨간불이면 커밋하지 않는 것도 실행으로 확인한다
(임시 저장소의 gatekeeper.py 를 갈아 끼워서 -- night.sh 는 저장소 루트의 것을 부른다).

이 세션의 clone 은 shallow 라 그대로 복제하면 밀기가 막힌다 -- 새로 짓는다.
LLM·네트워크 없이 돈다. 실행: python3 tests/test_night_돌리기.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def sh(cwd, *args, 명령="git"):
    return subprocess.run([명령, *args], cwd=str(cwd), capture_output=True, text=True)


글 = (뿌리 / "scripts" / "night.sh").read_text(encoding="utf-8")

print("== 문법과 규칙 (실행 전 최소 확인) ==")
_r = subprocess.run(["bash", "-n", str(뿌리 / "scripts" / "night.sh")],
                    capture_output=True, text=True)
ok(_r.returncode == 0, f"bash -n 통과 ({_r.stderr.strip()})")
_부르는줄 = [ln for ln in 글.split("\n")
            if "git " in ln and not ln.lstrip().startswith("#")
            and not ln.lstrip().startswith("echo")]
for 금지 in ("rebase", "--force", "push -f"):
    걸린 = [ln.strip() for ln in _부르는줄 if 금지 in ln]
    ok(not 걸린, f"`{금지}` 를 실제로 안 쓴다 ({걸린})")
ok("git merge" in 글 and 'origin/"$BR"' in 글, "지금 브랜치의 origin 을 merge 한다")
ok("origin/main" not in 글, "origin/main 을 아무 브랜치에나 안 건다")

임시 = Path(tempfile.mkdtemp(prefix="test-night-"))
try:
    bare = 임시 / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    work = 임시 / "work"
    subprocess.run(["git", "clone", "-q", str(bare), str(work)], check=True)
    sh(work, "config", "user.email", "t@t")
    sh(work, "config", "user.name", "t")

    # night.sh 가 기대는 것만 옮겨 심는다: graph 모듈(표준 라이브러리만) + 스크립트.
    (work / "graph").mkdir()
    for f in ("__init__.py", "store.py", "ask.py", "night.py",
              "verify.py", "link.py", "digest.py"):
        shutil.copy2(뿌리 / "graph" / f, work / "graph" / f)
    (work / "scripts").mkdir()
    shutil.copy2(뿌리 / "scripts" / "night.sh", work / "scripts" / "night.sh")
    # 게이트 대역: 초록불. 진짜 gatekeeper 는 이 헐벗은 저장소에서 당연히 빨갛다 --
    # 여기서 붙드는 것은 게이트의 내용이 아니라 night.sh 가 게이트 말을 듣는가다.
    (work / "gatekeeper.py").write_text(
        "print('게이트 대역: 통과')\nraise SystemExit(0)\n", encoding="utf-8")
    (work / "public_agent_memory").mkdir()
    (work / "public_agent_memory" / "20260901-010101_촉매_기록.md").write_text(
        "---\ntopic: '촉매'\n---\n\n백금 촉매 수율 82%.\n", encoding="utf-8")
    sh(work, "add", "-A")
    sh(work, "commit", "-q", "-m", "첫 커밋")
    sh(work, "push", "-q", "-u", "origin", "main")

    print("\n== 한 바퀴: 간추리고 -> 게이트 -> 커밋 -> 민다 ==")
    r = sh(work, "scripts/night.sh", 명령="bash")
    ok(r.returncode == 0, f"끝값 0 ({r.stdout.strip().splitlines()[-1:]} {r.stderr[:120]})")
    보인 = sh(work, "show", "origin/main:graph/ledger.jsonl")
    ok(보인.returncode == 0 and "촉매" in 보인.stdout,
       "**원격에 색인 커밋이 실제로 올라갔다**")
    간선 = sh(work, "show", "origin/main:graph/edges.jsonl")
    ok(간선.returncode == 0 and "재계산" in 간선.stdout, "다섯 꼴 간선도 같이 올라갔다")
    요지 = sh(work, "show", "origin/main:graph/digest.md")
    ok(요지.returncode == 0 and "손으로 고치지 마라" in 요지.stdout,
       "요지문(읽힐 텍스트)도 같이 올라갔다")

    print("\n== 새것이 없으면 커밋하지 않는다 ==")
    전 = sh(work, "rev-parse", "origin/main").stdout.strip()
    r = sh(work, "scripts/night.sh", 명령="bash")
    후 = sh(work, "rev-parse", "origin/main").stdout.strip()
    ok(r.returncode == 0 and "없다" in r.stdout, "'새로 적힌 것이 없다' 로 끝난다")
    ok(전 == 후, "원격이 안 움직였다")

    print("\n== 게이트가 빨간불이면 커밋하지 않는다 ==")
    (work / "gatekeeper.py").write_text(
        "print('게이트 대역: 차단')\nraise SystemExit(1)\n", encoding="utf-8")
    (work / "public_agent_memory" / "20260902-010101_새_기록.md").write_text(
        "---\ntopic: '새것'\n---\n\n새 실측.\n", encoding="utf-8")
    전 = sh(work, "rev-parse", "HEAD").stdout.strip()
    r = sh(work, "scripts/night.sh", 명령="bash")
    후 = sh(work, "rev-parse", "HEAD").stdout.strip()
    ok(r.returncode != 0 and "빨간불" in r.stdout, "빨간불을 말하고 멈춘다")
    ok(전 == 후, "**커밋이 안 됐다** -- 게이트 말을 듣는다")
finally:
    shutil.rmtree(임시, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("night.sh: 간추림->게이트->커밋->밀기 · 빈손 무커밋 · 빨간불 무커밋 -- 통과")
