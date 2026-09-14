"""`scripts/vm_dep.sh` -- **실제로 돌려서** 본다.

`bash -n` 은 이런 스크립트에서 아무것도 안 잡는다(실측 2026-09-09: `scripts/seek.sh` 가
한 줄도 안 돌았는데 `bash -n` 과 grep 검사는 전부 통과했다). 그래서 여기서는 진짜 git
저장소를 지어 스크립트를 끝까지 돌리고, **세 종료 코드가 실제로 나오는지** 본다.

무엇을 붙드나: 0=깔렸다 · 1=안 깔렸다 · 2=모르겠다. 특히 **2 가 0 으로 새지 않는 것**이
이 장치의 값이다 -- 모르는 것을 깔렸다고 답하면 사람에게 설치를 안 시키는 대신
'왜 안 되지' 를 남긴다. 모르는 것은 안 된 것으로 다룬다.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
스크립트 = 뿌리 / "scripts" / "vm_dep.sh"
FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


def 돌리기(판: Path, 꾸러미: str, sha: str):
    환 = dict(os.environ, SE_DEPLOY_SHA=sha)
    r = subprocess.run(["bash", str(스크립트), 꾸러미], cwd=판, env=환,
                       capture_output=True, text=True, timeout=60)
    return r.returncode, (r.stdout + r.stderr)


print("== 진짜 저장소를 지어 끝까지 돌린다 ==")
# 이 세션의 clone 은 shallow 라 그대로 복제하면 막힌다 -- 새로 짓는다(CLAUDE.md).
바깥 = Path(tempfile.mkdtemp(prefix="vmdep-"))
try:
    판 = 바깥 / "repo"
    판.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=판, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=판, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=판, check=True)
    (판 / "requirements.txt").write_text(
        "# scipy 를 왜 핀했는지 여기 길게 적혀 있다 -- 이 주석 줄은 세면 안 된다\n"
        "# torch 도 이 주석 안에 이름이 나온다\n"
        "scipy>=1.14.0\n"
        "antlr4-python3-runtime==4.11\n"
        "matplotlib>=3.7\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=판, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "요구"], cwd=판, check=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=판,
                         capture_output=True, text=True, check=True).stdout.strip()

    코드, 글 = 돌리기(판, "scipy", sha)
    ok(코드 == 0, f"requirements 에 있으면 0 (깔렸다) -- {코드} · {글.strip()[:60]}")
    코드, 글 = 돌리기(판, "matplotlib", sha)
    ok(코드 == 0, f"핀이 `>=` 여도 0 -- {코드}")
    코드, 글 = 돌리기(판, "antlr4_python3_runtime", sha)
    ok(코드 == 0, "**밑줄과 붙임표를 섞어 써도 맞는다** -- pip 이 둘을 섞어 쓴다")

    코드, 글 = 돌리기(판, "torch", sha)
    ok(코드 == 1, f"없으면 1 (안 깔렸다) -- {코드}")
    ok("사람에게 시키지 말고" in 글,
       "**1 일 때도 사람을 시키지 않는다** -- requirements 에 넣어 머지하라고 말한다")

    # **주석에 든 이름을 세면 안 된다.** requirements.txt 에는 왜 핀했는지가 주석으로
    # 길게 적혀 있고 거기에 꾸러미 이름이 그대로 나온다. 세면 안 깔린 것을 깔렸다고
    # 답하게 되고, 그것이 이 장치가 막으려던 바로 그 잘못이다.
    ok(코드 == 1, "주석 줄의 `torch` 를 깔린 것으로 읽지 않는다")

    코드, 글 = 돌리기(판, "scipy", "0" * 40)
    ok(코드 == 2, f"못 꺼내면 2 (모르겠다) -- **0 으로 새지 않는다** ({코드})")
    ok("모르겠다" in 글, "2 일 때 모르겠다고 말한다")

    코드, 글 = 돌리기(판, "", sha)
    ok(코드 == 2, f"꾸러미 이름이 없으면 2 -- {코드}")
finally:
    import shutil
    shutil.rmtree(바깥, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("vm_dep: 0/1/2 가 실제로 난다 · 주석을 안 센다 · 이름 꼴을 섞어 받는다 -- 통과")
