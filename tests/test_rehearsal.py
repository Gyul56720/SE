"""rehearsal(고치기 전에 격리 판에서 돌려 본다)를 **진짜 sandbox 로** 붙든다.

사용자(2026-09-11): "샌드박스 공간도 있는데 왜 미리 수정해 보고 시뮬레이션해서 문제 없는지
확인하지 않지?" -- 맞다. `sandbox.실행` 과 `plan` 은 있었는데 **이어져 있지 않았다**. 여기서 잇는다.

붙드는 것(전부 임시 저장소 + 진짜 격리 판에서): (1) 문법이 깨지면 py_compile 이 잡는다
(임포트가 안 되는 환경에서도 -- 실측: on_ready 들여쓰기 사고가 이 꼴이었다), (2) 문법은 맞지만
**뜻이 틀리면** 그 파일이 거는 검사가 잡는다, (3) 옳은 변경은 초록, (4) **실제 트리는 안 바뀐다**,
(5) 바뀐 .py 가 없으면 그렇다고 말한다, (6) 못 돌린 것은 통과로 치지 않는다, (7) 배선.

실행: python3 tests/test_rehearsal.py   (망·LLM 없이 돈다)
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

import rehearsal as R  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=False)


os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})
판 = Path(tempfile.mkdtemp(prefix="test-rh-"))
try:
    git(판, "init", "-q")
    (판 / "gatekeeper.py").write_text("import sys\nprint('[게이트 통과] 흉내')\nsys.exit(0)\n", encoding="utf-8")
    (판 / "tests").mkdir()
    (판 / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (판 / "tests" / "test_mod.py").write_text(
        'import sys; sys.path.insert(0, ".")\nimport mod\nassert mod.f() == 1, "f 는 1"\nprint("test_mod 통과")\n',
        encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "init")
    원본 = (판 / "mod.py").read_text(encoding="utf-8")

    print("== 바뀐 .py 가 없으면 ==")
    r = R.시험(판, 판=판, 초=60)
    ok(r["통과"] and not r["바뀐것"] and "없음" in R.보고(r), "리허설할 변경이 없다고 말한다")

    print("\n== 문법이 깨지면 py_compile 이 잡는다 (임포트 없이도) ==")
    (판 / "mod.py").write_text("def f():\n    return 1\n  틀린들여쓰기\n", encoding="utf-8")
    r = R.시험(판, 판=판, 초=60)
    걸음 = {이름: 끝값 for 이름, 끝값, _ in r["걸음"]}
    ok(not r["통과"] and 걸음.get("문법(py_compile)") == 1, f"**문법 빨강** ({걸음})")
    ok("IndentationError" in R.보고(r), "무엇이 깨졌는지 말한다")

    print("\n== 문법은 맞지만 뜻이 틀리면 검사가 잡는다 ==")
    (판 / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8")
    r = R.시험(판, 판=판, 초=60)
    걸음 = {이름: 끝값 for 이름, 끝값, _ in r["걸음"]}
    ok(not r["통과"] and 걸음.get("문법(py_compile)") == 0 and 걸음.get("tests/test_mod.py") == 1,
       f"**문법 초록 · 검사 빨강** ({걸음})")
    ok("f 는 1" in R.보고(r), "검사의 말을 그대로 보여 준다")

    print("\n== 옳은 변경은 초록 ==")
    (판 / "mod.py").write_text("def f():\n    # 뜻은 그대로\n    return 1\n", encoding="utf-8")
    r = R.시험(판, 판=판, 초=60)
    ok(r["통과"] and all(끝값 == 0 for _, 끝값, _ in r["걸음"]) and "초록" in R.보고(r), "셋 다 초록")
    ok("게이트" in {이름 for 이름, _, _ in r["걸음"]}, "게이트도 그 판에서 돈다")

    print("\n== 실제 트리는 안 바뀐다 ==")
    앞 = (판 / "mod.py").read_text(encoding="utf-8")
    R.시험(판, 판=판, 초=60)
    ok((판 / "mod.py").read_text(encoding="utf-8") == 앞, "리허설이 판의 파일을 안 건드린다(사본에서 돈다)")
    ok(원본 != 앞, "(참고) 이 검사는 실제로 코드를 바꿔 가며 쟀다")

    print("\n== 레포 전체 시뮬: **멀리서 깨진 것**을 잡는다 (좁은 시험은 못 본다) ==")
    # mod 를 other 가 쓰고, test_other 는 other 만 임포트한다 -> 바뀐 파일(mod.py)이 거는 검사는
    # test_mod 뿐이라 좁은 시험은 test_other 가 깨진 것을 못 본다. 전체 시뮬은 본다.
    (판 / "other.py").write_text("import mod\n\n\ndef g():\n    return mod.f() + 10\n", encoding="utf-8")
    (판 / "tests" / "test_other.py").write_text(
        'import sys; sys.path.insert(0, ".")\nimport other\nassert other.g() == 11, "g 는 11"\nprint("test_other 통과")\n',
        encoding="utf-8")
    (판 / "scripts").mkdir(exist_ok=True)
    (판 / "scripts" / "tests.sh").write_text(
        '#!/usr/bin/env bash\nset -u\ncd "$(dirname "$0")/.."\nfail=0\n'
        'for f in tests/test_*.py; do\n  b="$(basename "$f")"\n  if out="$(python3 "$f" 2>&1)"; then\n'
        '    printf "  OK   %-34s\\n" "$b"\n  else\n    fail=$((fail+1)); printf "  실패 %-34s\\n" "$b"\n  fi\ndone\n'
        'echo; [ $fail -gt 0 ] && { echo "테스트 중 $fail개 실패"; exit 1; }; echo "전부 통과"\n', encoding="utf-8")
    (판 / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    git(판, "add", "-A"); git(판, "commit", "-qm", "other")

    바 = R.바탕(판, 초=300, 다시=True)
    ok(바["돌았나"] and 바["실패"] == [] and set(바["통과"]) == {"test_mod.py", "test_other.py"},
       f"바탕: HEAD 는 전부 초록 ({바.get('통과')}, 빨강 {바.get('실패')})")
    ok(R.바탕(판, 초=300)["캐시"] is True, "같은 HEAD 면 바탕을 다시 안 잰다(캐시)")

    (판 / "mod.py").write_text("def f():\n    return 1\n\n\ndef 쓸모없음():\n    return 0\n", encoding="utf-8")
    r = R.시험(판, 판=판, 초=60, 전부=True, 전부초=300)
    ok(r["통과"] and r["회귀"]["새로깨짐"] == [], "곁다리만 더한 변경은 전체 초록")

    (판 / "mod.py").write_text("def f():\n    return 1\n\n\ndef g():\n    return 999\n", encoding="utf-8")
    (판 / "other.py").write_text("import mod\n\n\ndef g():\n    return mod.g()\n", encoding="utf-8")
    좁 = R.시험(판, 판=판, 초=60)                       # 좁은 시험: mod.py·other.py 가 거는 검사만
    전 = R.시험(판, 판=판, 초=60, 전부=True, 전부초=300)
    ok(not 전["통과"] and 전["회귀"]["새로깨짐"] == ["test_other.py"],
       f"**전체 시뮬이 멀리서 깨진 test_other 를 잡는다** ({전['회귀']['새로깨짐']})")
    ok("새로 깨짐" in R.보고(전), "보고가 무엇이 새로 깨졌는지 말한다")
    ok(전["전체"]["센것"] == 2 and 전["전체"]["바탕캐시"], "전체 몇 개를 셌는지·바탕은 캐시였는지 남긴다")

    print("\n== 못 돌린 것은 통과가 아니다 ==")
    r = R.시험(판, 판=판 / "없는곳", 초=10)
    ok(not r["통과"] or r["못잼"], "판이 없으면 초록이라고 하지 않는다")
finally:
    shutil.rmtree(판, ignore_errors=True)

print("\n== 배선 ==")
_st = (뿌리 / "plan" / "store.py").read_text(encoding="utf-8")
ok("def 시험하기" in _st and "import rehearsal" in _st, "!계획 시험 이 리허설을 부른다")
ok("아직 안 돌려 봤다" in _st and "리허설이 빨강" in _st and "또 바뀌었다" in _st,
   "**승인은 리허설 초록 + 같은 diff 일 때만**")
_cmd = (뿌리 / "plan" / "discord_cmd.py").read_text(encoding="utf-8")
ok('머리 == "시험"' in _cmd, "`!계획 시험` 하위 명령")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("!계획 시험" in _서버, "프롬프트가 `!계획 시험` 을 이름을 대고 시킨다")
import dispatch  # noqa: E402
ok(dispatch.고르기("계획 시험해봐")[0] == "!계획 시험" or dispatch.고르기("바꾸기 전에 돌려 봐")[0] == "!계획 시험",
   f"자연어가 시험으로 간다 ({dispatch.고르기('바꾸기 전에 돌려 봐')[0]})")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"rehearsal.py"' in _wf, "rehearsal 이 배포 경로에")
_st2 = (뿌리 / "plan" / "store.py").read_text(encoding="utf-8")
ok("전부: bool = False" in _st2 and "전부=전부" in _st2, "plan.시험하기 가 전부 모드를 넘긴다")
_cmd2 = (뿌리 / "plan" / "discord_cmd.py").read_text(encoding="utf-8")
ok('("전부", "전체", "레포")' in _cmd2, "`!계획 시험 전부` 가 레포 전체를 돌린다")
ok("rehearsal_baseline" in (뿌리 / "rehearsal.py").read_text(encoding="utf-8"), "바탕은 HEAD 별로 캐시된다")
p = subprocess.run(["python3", "rehearsal.py", "--판", str(뿌리 / "없는판"), "--초", "5"],
                   cwd=str(뿌리), capture_output=True, text=True, timeout=60)
ok(p.returncode in (0, 1, 3), f"CLI 가 돈다 (끝값 {p.returncode})")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("rehearsal: 문법 · 뜻 · 초록 · 안 건드림 · 못잼 · 승인 전제 · 배선 -- 통과")
