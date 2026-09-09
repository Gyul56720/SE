r"""**여러 줄로 된 명령은 중간이 빠진다.**

실측 2026-09-09, 네 번: 원장 커밋 · sweep 두 번 · 표 옮기기. 빠진 줄이 sweep 이면
답이 0개인 원장으로 보고서가 나오고, 그 보고서의 0%를 연산자의 성적으로 읽게 된다
(실제로 한 번 그렇게 읽을 뻔했다 -- 대조군이 "이 자는 계보를 안 본다" 고 단정했다).

그래서 줄을 하나로 줄인다. `scripts/seek.sh` 가 순서를 들고 있다.

여기서 재는 것은 그 파일이 **순서를 실제로 지키는가** 다. 특히 두 가지:

    훑기가 실패하면 보고서를 안 만든다   -- 빈 원장 보고서가 커밋되면 안 된다
    밀 때 rebase 도 --force 도 안 쓴다   -- 이 브랜치는 봇이 같이 쓴다

LLM·네트워크 없이 돈다. 실행: python3 tests/test_seek_돌리기.py
"""
from __future__ import annotations

import os
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


글 = (뿌리 / "scripts" / "seek.sh").read_text(encoding="utf-8")

print("== 문법이 선다 ==")
_r = subprocess.run(["bash", "-n", str(뿌리 / "scripts" / "seek.sh")],
                    capture_output=True, text=True)
ok(_r.returncode == 0, f"bash -n 통과 ({_r.stderr.strip()})")

print("\n== 네 걸음이 다 있다 ==")
for 걸음 in ("seek/sweep.py", "seek/report.py", "git add seek/report.md", "git push"):
    ok(걸음 in 글, f"{걸음} 이 있다")
ok(글.index("seek/sweep.py") < 글.index("seek/report.py") < 글.index("git push"),
   "**순서가 훑기 -> 보고서 -> 밀기다** -- 이 순서가 이 파일의 존재 이유다")

print("\n== 훑기가 실패하면 거기서 멈춘다 ==")
# 빈 원장으로 만든 보고서가 커밋되면, 그 0%를 연산자의 성적으로 읽게 된다
_토막 = 글[글.index("python3 seek/sweep.py"):글.index("=== [2/4]")]
ok("exit 1" in _토막, "훑기 뒤에 exit 1 이 있다")
ok("보고서를 안 만든다" in _토막, "왜 멈추는지 적는다")

print("\n== rebase 도 --force 도 안 쓴다 ==")
# 실측 2026-09-08~09: 이 브랜치는 봇이 같이 쓴다. rebase 하면 fast-forward 가 영영 안 된다
# **말하는 줄과 하는 줄을 가른다.** 이 파일은 주석에도 echo 에도 "--force 는 쓰지
# 마라" 고 적어 두었는데, 그대로 grep 하면 그 경고문이 걸린다 -- 만지는 것과
# 설명하는 것은 다르다(G016·G019 가 같은 자리에서 같은 것을 겪었다).
# 그래서 **git 을 실제로 부르는 줄만** 본다.
_부르는줄 = [ln for ln in 글.split("\n")
            if "git " in ln and not ln.lstrip().startswith("#")
            and not ln.lstrip().startswith("echo")]
ok(_부르는줄, f"git 을 부르는 줄이 있다 ({len(_부르는줄)}줄)")
for 금지 in ("rebase", "--force", "push -f"):
    걸린 = [ln.strip() for ln in _부르는줄 if 금지 in ln]
    ok(not 걸린, f"`{금지}` 를 **실제로 안 쓴다** ({걸린})")
ok("--force 는 쓰지 마라" in 글, "쓰지 말라고 적어는 놨다 -- 다음 사람이 읽는다")
ok("git merge" in 글 and 'origin/$BR' in 글,
   "**지금 브랜치의 origin 을 merge 한다** -- origin/main 이 아니다")
ok("origin/main" not in 글, "origin/main 을 아무 브랜치에나 안 건다")
ok("merge --abort" in 글, "충돌하면 되돌리고 사람에게 넘긴다")

print("\n== 밀기를 되풀이한다 ==")
ok("sleep" in 글 and "2 ** 번" in 글, "실패하면 2·4·8·16초로 물러나며 다시 민다")

print("\n== 백그라운드로 띄우는 법을 적어 놨다 ==")
ok("setsid nohup" in 글 and "disown" in 글, "setsid nohup ... disown 이 적혀 있다")
ok("pgrep -af" in 글, "**pgrep -af 로 확인하라고 적는다** -- ps -p $! 는 거짓 음성을 낸다")
ok("ps -p $!" in 글, "왜 그것이 아닌지도 적는다")

print("\n== 훑기 -> 보고서가 실제로 이어진다 ==")
# 씨앗만 있는 새 원장에서 짧게 돌려 본다. 밀기까지 가면 안 되므로 --초 를 아주 짧게
_tmp = Path(tempfile.mkdtemp())
_env = dict(os.environ, SEEK_LEDGER=str(_tmp / "led.json"))
_r2 = subprocess.run([sys.executable, str(뿌리 / "seek" / "sweep.py"),
                      "--초", "20", "--tries", "400000"],
                     capture_output=True, text=True, env=_env, cwd=str(뿌리), timeout=600)
ok(_r2.returncode == 0, f"훑기가 돈다 (종료 {_r2.returncode})")
_r3 = subprocess.run([sys.executable, str(뿌리 / "seek" / "report.py")],
                     capture_output=True, text=True, env=_env, cwd=str(뿌리))
ok("답이 있는 것 5개" in _r3.stdout,
   f"**훑고 나면 답이 찬다** -- 그러면 보고서에 경고가 안 붙는다\n"
   f"        {_r3.stdout.splitlines()[2] if len(_r3.stdout.splitlines()) > 2 else ''}")
ok("안 풀렸다" not in _r3.stdout.split("## 감사")[0],
   "다 푼 원장에는 '안 풀렸다' 가 없다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("seek 돌리기: 순서 · 실패시 멈춤 · merge · 되풀이 · 이어짐 -- 통과")
