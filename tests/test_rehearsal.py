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

print("\n== 공허 검사: 초록이 뜻이 있나 -- 코드가 바뀌었으면 그 변경 없이 빨간 검사가 하나는 있어야 한다 ==")
# 사용자(2026-09-12): "구조가 좋으면 모델의 성능을 이길 수 있다." investigate.목표검사유효한가 가 #194 의 속임수를
# 잡은 것을 **모든 패치**로 넓힌 것이다. #194(함수만 정의) · #201(글자 검사) · 구글 문 셋(검사 없음)이 전부 걸린다.
_공 = Path(tempfile.mkdtemp(prefix="공허-"))
try:
    git(_공, "init", "-q"); git(_공, "config", "user.email", "t@t"); git(_공, "config", "user.name", "t")
    (_공 / "tests").mkdir(); (_공 / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8")
    git(_공, "add", "-A"); git(_공, "commit", "-qm", "init")

    def 판으로(**files):
        w = Path(tempfile.mkdtemp(prefix="판-"))
        git(_공, "worktree", "add", "-q", "--detach", str(w), "HEAD")
        for rel, 본 in files.items():
            (w / rel).parent.mkdir(parents=True, exist_ok=True); (w / rel).write_text(본, encoding="utf-8")
        return w

    def 재기(**files):
        w = 판으로(**files)
        try:
            return R.공허검사(_공, w)
        finally:
            git(_공, "worktree", "remove", "--force", str(w))

    r = 재기(**{"tests/test_a.py": "import sys\nsys.exit(0)\n"})
    ok(not r["공허"] and "행동 변화 없음" in r["말"], "검사만 더한 패치는 볼 것 없다")
    r = 재기(**{"mod.py": 'def f():\n    """설명"""\n    return 2\n'})
    ok(not r["공허"] and "행동 변화 없음" in r["말"], "독스트링·주석만 바뀐 것은 행동 변화가 아니다")
    r = 재기(**{"mod.py": "def f():\n    return 1\n"})
    ok(r["공허"] and "재는 검사가 없다" in r["말"] and r["코드들"] == ["mod.py"], "**코드만 바뀌고 검사가 없으면 공허** -- 구글 문 셋의 자리")
    r = 재기(**{"mod.py": "def f():\n    return 1\n", "tests/test_b.py": "assert True\n"})
    ok(r["공허"] and "코드 변경 없이도" in r["말"], "**검사가 코드 변경 없이도 초록이면 공허** -- #194 · #201 의 자리")
    r = 재기(**{"new.py": "X = 1\n", "tests/test_c.py": "import new\nassert new.X == 1\n"})
    ok(not r["공허"] and r["빨간검사"] == ["tests/test_c.py (끝값 1)"], "새 모듈을 임포트하는 검사는 기능 없는 판에서 빨강 -- 증언한다")
    r = 재기(**{"mod.py": "def f():\n    return 1\n", "tests/test_d.py": "import mod\nassert mod.f() == 1\n"})
    ok(not r["공허"] and "증언한다" in r["말"], "값을 단언하는 검사는 증언한다")
    ok(git(_공, "worktree", "list").stdout.strip().count("\n") == 0, "HEAD 판 워크트리가 안 남는다")
finally:
    shutil.rmtree(_공, ignore_errors=True)

print("\n== 절제 검사: 기능을 하나씩 빼면 검사가 무너지나 -- 빼면 빨강 · 넣으면 초록 ==")
# 사용자(2026-09-12): "기능의 존재를 주장하지 말고, 그 기능을 제거했을 때 검사가 무너지고 다시 넣었을 때 복구되는지."
# 공허검사는 패치 전체를 빼고 보므로 함수 셋 중 하나만 걸려도 통과한다. 여기서는 함수마다 몸통을 빼고 패치의 검사를 돌린다.
_절 = Path(tempfile.mkdtemp(prefix="절제-"))
try:
    git(_절, "init", "-q"); git(_절, "config", "user.email", "t@t"); git(_절, "config", "user.name", "t")
    (_절 / "tests").mkdir()
    (_절 / "mod.py").write_text("def f():\n    return 2\n\n\nclass C:\n    def m(self):\n        return 0\n", encoding="utf-8")
    (_절 / "old.py").write_text("X = 1\n", encoding="utf-8")
    git(_절, "add", "-A"); git(_절, "commit", "-qm", "init")

    def 절판(지울=(), **files):
        w = Path(tempfile.mkdtemp(prefix="판-"))
        git(_절, "worktree", "add", "-q", "--detach", str(w), "HEAD")
        for rel, 본 in files.items():
            (w / rel).parent.mkdir(parents=True, exist_ok=True); (w / rel).write_text(본, encoding="utf-8")
        for rel in 지울:
            (w / rel).unlink()
        return w

    def 절재기(지울=(), 상한=None, **files):
        w = 절판(지울, **files)
        try:
            return R.절제검사(_절, w, 상한=상한)
        finally:
            git(_절, "worktree", "remove", "--force", str(w))

    F1 = "def f():\n    return 1\n"
    T_F = "import mod\nassert mod.f() == 1\n"
    r = 절재기(**{"mod.py": F1})
    ok(r["성립"] and "검사가 없다" in r["말"] and not r["잰것"], "검사 없는 패치는 여기 몫이 아니다(공허검사가 막는다)")
    r = 절재기(**{"tests/test_a.py": "assert True\n"})
    ok(r["성립"] and "뺄 수 있는 단위가 없다" in r["말"], "검사만 바뀐 패치는 뺄 단위가 없다")
    r = 절재기(**{"mod.py": F1, "tests/test_a.py": T_F})
    ok(r["성립"] and r["잰것"] == [{"이름": "mod.py:f", "무너짐": True, "어디": "tests/test_a.py"}] and "다 무너졌다" in r["말"],
       "**f 를 빼면 f 의 검사가 빨갛다** -- 성립")
    r = 절재기(**{"mod.py": F1 + "\n\ndef g():\n    return 9\n", "tests/test_a.py": T_F})
    ok(not r["성립"] and r["안잡힌것"] == ["mod.py:g"] and "절제해도 검사가 안 무너진다" in r["말"] and "mod.py:g" in r["말"],
       f"**검사에 안 걸리는 함수 g 를 같이 넣으면 잡힌다** -- 공허검사는 놓치는 자리 ({r['안잡힌것']})")
    ok([x["이름"] for x in r["잰것"]] == ["mod.py:f", "mod.py:g"], "바뀐 함수마다 하나씩 잰다")
    r = 절재기(**{"mod.py": F1 + "def h(): return 3\n", "tests/test_a.py": T_F})
    ok(not r["성립"] and r["안잡힌것"] == ["mod.py:h"] and not r["못잼"], "한 줄짜리 `def h(): return 3` 도 몸통을 빼서 잰다")
    r = 절재기(**{"mod.py": F1 + "\n\nclass C:\n    def m(self):\n        return 5\n", "tests/test_a.py": T_F + "assert mod.C().m() == 5\n"})
    ok(r["성립"] and [x["이름"] for x in r["잰것"]] == ["mod.py:f", "mod.py:C.m"], "클래스 안 메서드는 `C.m` 으로 따로 잰다")
    r = 절재기(**{"mod.py": 'def f():\n    return 1\n\n\nclass C:\n    def m(self):\n        """설명"""\n        return 0  # 주석\n',
                 "tests/test_a.py": T_F})
    ok(r["성립"] and [x["이름"] for x in r["잰것"]] == ["mod.py:f"], "독스트링·주석만 바뀐 함수는 단위가 아니다")
    r = 절재기(**{"new.py": "def a():\n    return 1\n\n\ndef b():\n    return 2\n", "tests/test_n.py": "import new\nassert new.a() == 1\n"})
    ok(not r["성립"] and r["안잡힌것"] == ["new.py:b"], "새 파일도 함수마다 잰다 -- 파일을 임포트만 하는 검사로는 못 넘어간다")
    r = 절재기(**{"new.py": "X = 1\n", "tests/test_n.py": "import new\nassert new.X == 1\n"})
    ok(r["성립"] and r["잰것"] == [{"이름": "new.py(파일 전체)", "무너짐": True, "어디": "tests/test_n.py"}], "함수 없는 새 파일은 통째로 뺀다")
    r = 절재기(지울=("old.py",), **{"mod.py": F1 + "\n\ndef g():\n    return 9\n",
                                   "tests/test_a.py": T_F + "import importlib.util\nassert importlib.util.find_spec('old') is None\n"})
    ok(not r["성립"] and r["안잡힌것"] == ["mod.py:g"], "패치가 지운 파일은 절제 판에서도 없다 -- 지움 때문에 빨개지는 것을 '잡혔다' 로 안 친다")
    r = 절재기(상한=1, **{"mod.py": F1 + "\n\ndef g():\n    return 9\n", "tests/test_a.py": T_F})
    ok(r["성립"] and len(r["잰것"]) == 1 and "1개는 안 쟀다" in r["말"], "상한을 넘는 단위는 안 재고 그렇게 말한다")
    ok(git(_절, "worktree", "list").stdout.strip().count("\n") == 0, "절제 워크트리가 안 남는다")

    print("\n  -- 기준 커밋: 조사 모드처럼 두뇌가 바퀴마다 커밋해 HEAD 가 움직여도 시작 커밋 대비 전부가 한 패치다 --")
    w = 절판(**{"mod.py": F1 + "\n\ndef g():\n    return 9\n", "tests/test_a.py": T_F})
    try:
        시작 = git(w, "rev-parse", "HEAD").stdout.strip()
        git(w, "add", "-A"); git(w, "commit", "-qm", "바퀴 1")            # f·g·검사를 커밋했다 -- HEAD 대비는 빈 판
        (w / "mod.py").write_text(F1 + "\n\ndef g():\n    return 9\n\n\ndef k():\n    return 0\n", encoding="utf-8")
        r = R.절제검사(_절, w)
        ok(r["성립"] and "검사가 없다" in r["말"], "기준 HEAD 로는 커밋된 검사가 안 보인다(패치에 검사가 없다고 본다)")
        r = R.절제검사(_절, w, 기준=시작)
        ok(not r["성립"] and r["안잡힌것"] == ["mod.py:g", "mod.py:k"] and [x["이름"] for x in r["잰것"]] == ["mod.py:f", "mod.py:g", "mod.py:k"],
           f"**기준=시작 커밋이면 커밋된 것 + 작업 디렉터리 것이 다 한 패치다** -- f 잡힘, g·k 안 잡힘 ({r['안잡힌것']})")
        (w / "old.py").unlink(); git(w, "add", "-A"); git(w, "commit", "-qm", "바퀴 2")
        r = R.절제검사(_절, w, 기준=시작)
        ok(not r["성립"] and r["안잡힌것"] == ["mod.py:g", "mod.py:k"], "커밋으로 지운 파일도 기준 대비 지움으로 잡혀 절제 판에서 빠진다")
    finally:
        git(_절, "worktree", "remove", "--force", str(w))
    ok(git(_절, "worktree", "list").stdout.strip().count("\n") == 0, "기준 커밋 절제 뒤에도 워크트리가 안 남는다")
finally:
    shutil.rmtree(_절, ignore_errors=True)

print("\n== 열쇠 대조: 원장에 없는 열쇠를 읽고 있나 (LLM 0회 · subprocess 0회) ==")
# 실측 2026-09-12: 봇이 지은 scripts/ledgerstat.py 가 repair/ledger.jsonl 에 없는 열쇠 다섯(귀속·맞춘수·
# 틀린수·막음·명령수)을 읽어 여덟 칸 중 여섯이 **구조적으로 항상 0** 이었다. 검사는 그 열쇠를 다 넣은 가짜 행을
# 지어 합을 단언했으니 초록이었다 -- 공허·절제가 보는 "검사가 코드를 부르나" 로는 안 잡히는 축이다.
_열 = Path(tempfile.mkdtemp(prefix="열쇠-"))
try:
    git(_열, "init", "-q"); git(_열, "config", "user.email", "t@t"); git(_열, "config", "user.name", "t")
    (_열 / "ldg").mkdir(); (_열 / "tests").mkdir()
    (_열 / "ldg" / "ledger.jsonl").write_text(
        '{"꼴": "조사", "때": "t1", "바퀴": 1, "해결": true}\n'
        '{"꼴": "조사", "때": "t2", "바퀴": 2}\n'
        '{"꼴": "끝", "때": "t3"}\n', encoding="utf-8")
    (_열 / "ldg" / "빈.jsonl").write_text("", encoding="utf-8")
    (_열 / "ldg" / "목록.json").write_text('[{"id": "a", "점수": 1}, {"id": "b"}]', encoding="utf-8")
    git(_열, "add", "-A"); git(_열, "commit", "-qm", "init")

    def 열판(**files):
        w = Path(tempfile.mkdtemp(prefix="판-"))
        git(_열, "worktree", "add", "-q", "--detach", str(w), "HEAD")
        for rel, 본 in files.items():
            (w / rel).parent.mkdir(parents=True, exist_ok=True); (w / rel).write_text(본, encoding="utf-8")
        return w

    def 열재기(**files):
        w = 열판(**files)
        try:
            return R.열쇠대조(_열, w)
        finally:
            git(_열, "worktree", "remove", "--force", str(w))

    한조각 = ('import json\n'
            'def 세기():\n'
            '    n = 0\n'
            '    for 줄 in open("ldg/ledger.jsonl"):\n'
            '        r = json.loads(줄)\n'
            '        n += r.get("%s", 0)\n'
            '    return n\n')
    r1 = 열재기(**{"a.py": 한조각 % "바퀴"})
    ok(r1["성립"] and "다 원장에 있다" in r1["말"] and r1["본것"] == ["a.py:세기 <- ldg/ledger.jsonl(3줄)"],
       f"있는 열쇠만 읽으면 성립 ({r1['말'][:40]})")
    r2 = 열재기(**{"a.py": 한조각 % "맞춘수"})
    ok(not r2["성립"] and [x["열쇠"] for x in r2["죽은읽기"]] == ["맞춘수"] and "꼴(3)" in r2["말"],
       f"**한 줄에도 없는 열쇠는 죽은 읽기** -- 실제로 있는 열쇠를 세어 같이 알려 준다 ({[x['열쇠'] for x in r2['죽은읽기']]})")
    r3 = 열재기(**{"a.py": 한조각 % "해결"})
    ok(r3["성립"], "일부 행에만 있는 열쇠(해결: 3줄 중 1줄)는 죽은 읽기가 아니다")
    r4 = 열재기(**{"a.py": 'import json\n'
                          'from pathlib import Path\n'
                          'def 세기(경로):\n'
                          '    for 줄 in open(경로):\n'
                          '        r = json.loads(줄)\n'
                          '        print(r.get("막음", 0), r["꼴"])\n'
                          'def main():\n'
                          '    p = Path("ldg/ledger.jsonl")\n'
                          '    세기(p)\n'})
    ok(not r4["성립"] and [x["열쇠"] for x in r4["죽은읽기"]] == ["막음"],
       f"**경로가 부른 쪽에 있어도 한 홉 따라간다** -- ledgerstat 의 꼴 (main 의 Path -> 세기) ({r4['죽은읽기']})")
    r5 = 열재기(**{"a.py": 'import json\n'
                          'def 원장():\n'
                          '    for 줄 in open("ldg/ledger.jsonl"):\n'
                          '        d = json.loads(줄)\n'
                          '        print(d.get("바퀴"))\n'
                          'def 딴것(d):\n'
                          '    return d["증거"] + d["고칠거리"]\n'})
    ok(r5["성립"], "**다른 함수의 같은 이름(d)을 원장 행으로 오인하지 않는다** -- diagnose.py 에서 난 거짓 양성")
    r6 = 열재기(**{"a.py": 'import json\n'
                          'import os\n'
                          'def 훑기(뿌리):\n'
                          '    for 이름 in os.listdir(뿌리):\n'
                          '        t = json.loads(open(이름).read())\n'
                          '        print(t.get("id"), t["물음"])\n'
                          'def 원장():\n'
                          '    for 줄 in open("ldg/ledger.jsonl"):\n'
                          '        r = json.loads(줄)\n'
                          '        print(r["꼴"])\n'})
    ok(r6["성립"], "**부른 쪽이 계산된 경로를 넘기면 짝을 모르므로 재지 않는다** -- eval/tasks.py 에서 난 거짓 양성")
    r7 = 열재기(**{"a.py": 'import json\n'
                          'def 세기(cfg):\n'
                          '    for 줄 in open("ldg/ledger.jsonl"):\n'
                          '        r = json.loads(줄)\n'
                          '        print(r["꼴"], cfg.get("model"), cfg["키없음"])\n'})
    ok(r7["성립"], "같은 조각의 설정 dict(cfg)는 원장 열쇠로 안 센다 -- json.loads 로 만든 이름만 본다")
    r8 = 열재기(**{"a.py": 한조각.replace("ldg/ledger.jsonl", "ldg/빈.jsonl") % "바퀴"})
    ok(r8["성립"] and r8["못잼"] == ["a.py:세기 -> ldg/빈.jsonl (행이 없다)"], "행이 없는 원장은 못 잰다고 적는다(막지 않는다)")
    r9 = 열재기(**{"a.py": 'import json\n'
                          'def 세기():\n'
                          '    담 = json.load(open("ldg/목록.json"))\n'
                          '    for r in 담:\n'
                          '        print(r.get("점수"), r.get("없는것"))\n'})
    ok(not r9["성립"] and [x["열쇠"] for x in r9["죽은읽기"]] == ["없는것"],
       f".json 목록 꼴 -- json.load 를 돌면 알맹이가 행이다 ({[x['열쇠'] for x in r9['죽은읽기']]})")
    r9b = 열재기(**{"a.py": 'import json\n'
                           'def 세기():\n'
                           '    행들 = [json.loads(x) for x in open("ldg/ledger.jsonl") if x.strip()]\n'
                           '    for r in 행들:\n'
                           '        print(r.get("없는것"))\n'})
    ok(not r9b["성립"] and [x["열쇠"] for x in r9b["죽은읽기"]] == ["없는것"],
       f"내포 표현식으로 만든 행 목록도 센다 ({[x['열쇠'] for x in r9b['죽은읽기']]})")
    r10 = 열재기(**{"tests/test_a.py": 한조각 % "맞춘수"})
    ok(r10["성립"] and "볼 것 없다" in r10["말"], "검사 파일은 제 표본을 지어 쓰므로 안 본다")
    r11 = 열재기(**{"a.py": 'def 아무것(x):\n    return x + 1\n'})
    ok(r11["성립"] and "볼 것 없다" in r11["말"], "원장을 읽는 코드가 없으면 볼 것 없다")
finally:
    shutil.rmtree(_열, ignore_errors=True)

print("\n== 미정의 이름: 함수 안에서 없는 이름을 부르나 (symtable -- 파이썬 자신의 스코프 해석) ==")
# 실측 2026-09-12: discord_bot_server._git_sync_locked 가 `report.summary()` 를 불렀는데 그 이름이 없었다.
# **밀기가 성공한 경로에서만** 터지므로 사용자는 커밋·푸시가 다 된 뒤 "[git 동기화 실패] NameError" 를 보았다.
# 같은 결이 저장소에 다섯 군데 있었다(coin/news._주소 · gemini_limits._hdr·_die · test 의 ast). 전부 이것이 찾았다.
_이 = Path(tempfile.mkdtemp(prefix="이름-"))
try:
    git(_이, "init", "-q"); git(_이, "config", "user.email", "t@t"); git(_이, "config", "user.name", "t")
    (_이 / "tests").mkdir(); (_이 / "mod.py").write_text("X = 1\n", encoding="utf-8")
    git(_이, "add", "-A"); git(_이, "commit", "-qm", "init")

    def 이재기(**files):
        w = Path(tempfile.mkdtemp(prefix="판-"))
        git(_이, "worktree", "add", "-q", "--detach", str(w), "HEAD")
        for rel, 본 in files.items():
            (w / rel).parent.mkdir(parents=True, exist_ok=True); (w / rel).write_text(본, encoding="utf-8")
        try:
            return R.미정의이름(_이, w)
        finally:
            git(_이, "worktree", "remove", "--force", str(w))

    r1 = 이재기(**{"a.py": "def 밀기():\n    보고 = 1\n    return f'{report}{보고}'\n"})
    ok(not r1["성립"] and [(x["조각"], x["이름"]) for x in r1["찾은것"]] == [("밀기", "report")] and "NameError" in r1["말"],
       f"**없는 이름을 부르면 잡는다** -- git_sync 의 자리 ({r1['찾은것']})")
    r2 = 이재기(**{"a.py": "def 쓰기():\n    return 뒤에정의(1)\n\n\ndef 뒤에정의(x):\n    return x\n"})
    ok(r2["성립"], "뒤에 정의된 모듈 이름은 미정의가 아니다(파이썬은 부를 때 푼다)")
    r3 = 이재기(**{"a.py": "def 겉():\n    속값 = 1\n    def 안():\n        return 속값\n    return 안()\n"})
    ok(r3["성립"], "감싼 함수의 이름을 읽는 클로저는 미정의가 아니다")
    r4 = 이재기(**{"a.py": "def f(xs):\n    return [y * 2 for y in xs]\n"})
    ok(r4["성립"], "내포 표현식의 변수는 미정의가 아니다")
    r5 = 이재기(**{"a.py": "class C:\n    def m(self):\n        return super().m()\n"})
    ok(r5["성립"], "super() 가 암묵으로 쓰는 __class__ 는 미정의가 아니다(거짓 양성 하나를 봐준다)")
    r6 = 이재기(**{"a.py": "def f(p):\n    import os\n    return os.path.join(p, 'x')\n"})
    ok(r6["성립"], "함수 안 임포트도 정의다")
    r7 = 이재기(**{"a.py": "총 = 0\n\n\ndef 더하기():\n    global 총\n    총 += 1\n    return 총\n"})
    ok(r7["성립"], "global 로 선언한 모듈 이름은 미정의가 아니다")
    r8 = 이재기(**{"a.py": "from os import *\n\n\ndef f():\n    return getcwd()\n"})
    ok(r8["성립"] and r8["못잼"] == ["a.py (import * 가 있어 무엇이 들어왔는지 모른다)"], "`import *` 가 있으면 재지 않는다고 적는다")
    r9 = 이재기(**{"tests/test_a.py": "def 재기():\n    나무 = ast.parse('x')\n    return 나무\n"})
    ok(not r9["성립"] and r9["찾은것"][0]["이름"] == "ast", "**검사 파일도 본다** -- 거기 NameError 면 검사가 아예 안 돈다")
    r10 = 이재기(**{"a.py": "def f(xs):\n    return sorted(len(x) for x in xs)\n"})
    ok(r10["성립"] and r10["본것"] == ["a.py"], "빌트인은 미정의가 아니다")
finally:
    shutil.rmtree(_이, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("rehearsal: 문법 · 뜻 · 초록 · 안 건드림 · 못잼 · 승인 전제 · 배선 · 공허 검사 · 절제 검사 · 열쇠 대조 · 미정의 이름 -- 통과")
