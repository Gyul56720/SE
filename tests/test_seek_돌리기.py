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
ok("sleep" in 글 and "2 ** TRY" in 글, "실패하면 2·4·8·16초로 물러나며 다시 민다")

print("\n== 백그라운드로 띄우는 법을 적어 놨다 ==")
ok("setsid nohup" in 글 and "disown" in 글, "setsid nohup ... disown 이 적혀 있다")
ok("pgrep -af" in 글, "**pgrep -af 로 확인하라고 적는다** -- ps -p $! 는 거짓 음성을 낸다")
ok("ps -p $!" in 글, "왜 그것이 아닌지도 적는다")

print("\n== 셸 변수 이름이 ASCII 다 ==")
# **실측 2026-09-09: 이 파일 전체가 안 돌았다.** bash 는 식별자로
# [A-Za-z_][A-Za-z0-9_]* 만 받는다. `초=25` 는 대입이 아니라 **명령어**로 파싱되고,
# `set -u` 아래에서 `$초` 는 unbound 라 첫 줄에서 죽는다.
#
# `bash -n` 은 이것을 안 잡는다 -- 문법으로는 그냥 "명령어 하나" 라서 멀쩡하다.
# 그래서 아래 '진짜로 돌려 본다' 가 있다. 텍스트만 보던 것이 이 병의 원인이다.
import re                                                     # noqa: E402
_대입 = re.findall(r"^\s*([^\s=]+)=", 글, re.M)
_한글 = [v for v in _대입 if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v)]
ok(not _한글, f"**대입되는 이름이 다 ASCII 다** ({_한글})  <- 한글이면 안 돈다")
ok("변수 이름을 한글로 쓰지 마라" in 글, "왜인지 파일에 적어 놨다 -- 다음 사람이 또 쓴다")

print("\n== 진짜로 돌려 본다 ==")
# **여기가 이 검사의 요점이다.** 앞의 것들은 다 텍스트를 봤고, 텍스트는 이 파일이
# 한 줄도 안 도는 동안에도 다 통과했다. 돌려 봐야 안다.
# **저장소를 새로 짓는다.** 이 세션의 clone 은 shallow 라 그대로 복제하면
# `shallow update not allowed` 로 밀기가 막힌다 -- 그러면 [4/4] 를 못 재본다.
_일터 = Path(tempfile.mkdtemp())
_먼곳 = _일터 / "remote.git"
subprocess.run(["git", "init", "-q", "--bare", str(_먼곳)], check=True)
_여기 = _일터 / "work"
_여기.mkdir()
for _칸 in ("seek", "scripts", "orchestrator"):
    shutil.copytree(뿌리 / _칸, _여기 / _칸,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
(_여기 / "seek" / "ledger.json").unlink(missing_ok=True)      # 씨앗부터 시작한다
subprocess.run(["git", "init", "-q", "-b", "main", str(_여기)], check=True)
for _k, _v in (("user.email", "t@t"), ("user.name", "t")):
    subprocess.run(["git", "-C", str(_여기), "config", _k, _v], check=True)
subprocess.run(["git", "-C", str(_여기), "add", "-A"], check=True)
subprocess.run(["git", "-C", str(_여기), "commit", "-q", "-m", "밑동"], check=True)
subprocess.run(["git", "-C", str(_여기), "remote", "add", "origin", str(_먼곳)], check=True)
subprocess.run(["git", "-C", str(_여기), "push", "-q", "-u", "origin", "main"], check=True)

_r4 = subprocess.run(["bash", "scripts/seek.sh", "25", "400000"],
                     capture_output=True, text=True, cwd=str(_여기), timeout=900)
_말 = _r4.stdout + _r4.stderr
ok(_r4.returncode == 0, f"끝까지 돈다 (종료 {_r4.returncode})\n{_말[-500:]}")
for _단 in ("[1/4]", "[2/4]", "[3/4]", "[4/4]"):
    ok(_단 in _말, f"{_단} 를 지난다")
ok("unbound variable" not in _말 and "No such file or directory" not in _말,
   f"**대입이 명령어로 새지 않는다**\n{_말[:300]}")
ok("끝났다" in _말, f"끝났다고 말한다\n{_말[-300:]}")

print("\n== 돌고 나면 정말 커밋되어 있다 ==")
_로그 = subprocess.run(["git", "-C", str(_여기), "log", "--oneline", "-1", "origin/main"],
                      capture_output=True, text=True).stdout.strip()
ok("seek 결과 -- 푼 것" in _로그, f"**원격에 커밋이 올라가 있다** ({_로그})")
ok("/5" in _로그 or "/" in _로그.split("푼 것")[-1],
   f"몇 개를 풀었는지 적힌다 ({_로그})")
ok("?" not in _로그.split("푼 것")[-1],
   f"셈이 실패하지 않았다 ({_로그})  <- '?' 면 파이썬 토막이 터진 것이다")
_보 = subprocess.run(["git", "-C", str(_여기), "show", "origin/main:seek/report.md"],
                     capture_output=True, text=True).stdout
ok("답이 있는 것 5개" in _보, f"**올라간 보고서에 답이 차 있다**\n{_보[:160]}")
ok("안 풀렸다" not in _보.split("## 감사")[0], "덜 푼 경고가 안 붙어 있다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("seek 돌리기: 순서 · 실패시 멈춤 · merge · 되풀이 · 이어짐 -- 통과")
