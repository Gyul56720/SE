"""shellmemo -- **같은 나무에 같은 명령은 두 번 돌리지 않는다** 를 임시 저장소에서 실제로 붙든다.

실측 2026-09-12: 조사 c5cc1ef8 이 열한 바퀴 중 열 바퀴를 같은 명령으로 돌았다. 코드가 되풀이를 세기만
하고 막지 않았다. 나무가 안 바뀌면 답도 안 바뀐다 -- 그것을 모델이 기억하게 두지 않고 코드가 막는다.

붙드는 것 여섯: (1) 같은 나무 · 같은 명령은 두 번째에 막힌다(그때 답을 돌려준다), (2) 파일이 바뀌면 지문이
바뀌어 다시 돈다, (3) 다른 명령은 막지 않는다, (4) 안 켠 작성자에겐 아무 일도 없다, (5) 끄면 막음·돌린것이
돌아온다, (6) run_shell 이 실제로 이 모듈에 묻고 적는다(글로 확인 -- bot_tools 는 langchain 이 있어야 임포트된다).

실행: python3 tests/test_shellmemo.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import shellmemo as M  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


d = Path(tempfile.mkdtemp(prefix="shellmemo-"))
g = lambda *a: subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True)  # noqa: E731
g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
(d / "a.txt").write_text("a\n", encoding="utf-8"); g("add", "-A"); g("commit", "-qm", "init")


def 돌리기(작성자, 명령):
    """run_shell 이 하는 것을 그대로: 묻고 -> 없으면 돌리고 적는다."""
    지문 = M.나무지문(d)
    전 = M.이미돌렸나(작성자, 명령, 지문)
    if 전 is not None:
        return M.막힘말(명령, 지문, 전)
    p = subprocess.run(["bash", "-lc", 명령], cwd=str(d), capture_output=True, text=True)
    M.적기(작성자, 명령, 지문, p.returncode, p.stdout)
    return f"[exit={p.returncode}]\n{p.stdout}"


print("== 같은 나무 · 같은 명령은 두 번째에 막힌다 ==")
M.켜기("t1")
첫 = 돌리기("t1", "cat a.txt")
둘 = 돌리기("t1", "cat a.txt")
ok(첫.startswith("[exit=0]") and 둘.startswith("[중복 -- 돌리지 않았다]") and "끝값 0" in 둘 and "a" in 둘,
   f"**두 번째는 돌리지 않고 그때 답을 돌려준다** ({둘.splitlines()[0][:60]})")
ok(M.보기("t1") == {"막음": ["cat a.txt"], "돌린것": [("cat a.txt", 0)]}, f"막은 것과 돌린 것이 따로 센다 ({M.보기('t1')})")

print("\n== 파일이 바뀌면 다른 나무다 -- 다시 돈다 ==")
(d / "a.txt").write_text("b\n", encoding="utf-8")
셋 = 돌리기("t1", "cat a.txt")
ok(셋.startswith("[exit=0]") and "b" in 셋, "**나무가 바뀌면 같은 명령도 돈다** -- 고친 뒤 다시 재는 것을 막지 않는다")
ok(돌리기("t1", "cat a.txt").startswith("[중복"), "그 뒤 또 같은 것은 막힌다")

print("\n== 다른 명령은 막지 않는다 · 안 켠 작성자는 무관 ==")
ok(돌리기("t1", "ls").startswith("[exit=0]"), "다른 명령은 돈다")
ok(돌리기("아무도", "cat a.txt").startswith("[exit=0]") and 돌리기("아무도", "cat a.txt").startswith("[exit=0]"),
   "안 켠 작성자(봇의 보통 대화)에겐 아무 일도 없다")
ok(M.보기("아무도") is None, "안 켠 작성자의 기록은 없다")

print("\n== 끄면 기록이 돌아온다 ==")
끝 = M.끄기("t1")
ok(끝 and len(끝["막음"]) == 2 and len(끝["돌린것"]) == 3 and not M.켜졌나("t1"), f"막음 {len(끝['막음'])} · 돌린것 {len(끝['돌린것'])}")
ok(M.끄기("t1") is None, "두 번 꺼도 조용하다")

print("\n== 배선: run_shell 이 묻고 적는다 · 조사가 켜고 끈다 ==")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_런셸 = _도구.split("def run_shell", 1)[-1].split("\n@tool", 1)[0]
ok("shellmemo.이미돌렸나(" in _런셸 and "shellmemo.적기(" in _런셸 and "shellmemo.막힘말(" in _런셸,
   "run_shell 이 돌리기 전에 묻고, 돌린 뒤 적고, 막힐 때 그 말을 돌려준다")
ok(_런셸.index("shellmemo.이미돌렸나(") < _런셸.index("subprocess.Popen("), "묻는 것이 Popen 보다 앞이다 -- 돌리고 나서 막으면 늦다")
_조사 = (뿌리 / "investigate" / "run.py").read_text(encoding="utf-8")
ok("shellmemo.켜기(thread_id)" in _조사 and "shellmemo.끄기(thread_id)" in _조사, "조사가 thread_id 로 켜고 끈다")
ok('"막음": 막음수' in _조사, "바퀴마다 막은 수가 원장에 남는다")

import shutil
shutil.rmtree(d, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("shellmemo: 같은 나무 같은 명령 차단 · 나무 바뀌면 재실행 · 끄기 · 배선 -- 통과")
