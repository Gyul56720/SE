"""audit(변경 감사)를 임시 저장소에서 **red-green 으로** 붙든다.

붙드는 것: (1) 미커밋으로 깨뜨린 변경을 감사가 **실패로** 잡는다(RED) -- 지금 트리
사본에서 돌기 때문이다, (2) 고치면 통과한다(GREEN), (3) 이름이 안 닮아도 임포트로
검사를 찾는다, (4) 검사 없는 .py 변경은 크게 말한다, (5) 커밋 감사는 HEAD 를 본다
-- 미커밋 수정이 커밋 감사 결과에 새어 들면 안 된다.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_audit.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from audit import run as 감사기  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def sh(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


임시 = Path(tempfile.mkdtemp(prefix="test-audit-"))
repo = 임시 / "repo"
(repo / "tests").mkdir(parents=True)
subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
sh(repo, "config", "user.email", "t@t")
sh(repo, "config", "user.name", "t")

(repo / "셈.py").write_text("def 더하기(a, b):\n    return a + b\n", encoding="utf-8")
(repo / "tests" / "test_셈.py").write_text(
    "import sys\nfrom pathlib import Path\n"
    "sys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n"
    "import 셈\n"
    "assert 셈.더하기(2, 2) == 4, 셈.더하기(2, 2)\n"
    "print('셈 통과')\n", encoding="utf-8")
# 이름이 안 닮은 모듈 + 임포트로만 이어진 검사
(repo / "돈.py").write_text("이율 = 0.05\n", encoding="utf-8")
(repo / "tests" / "test_기능.py").write_text(
    "import sys\nfrom pathlib import Path\n"
    "sys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n"
    "import 돈\n"
    "assert 돈.이율 == 0.05\nprint('기능 통과')\n", encoding="utf-8")
# 임포트할 수 없는 파일(봇처럼)을 원문으로 읽는 검사 -- 이름이 따옴표 안에 적혀 있다
(repo / "봇.py").write_text("import 없는꾸러미\nX = 1\n", encoding="utf-8")
(repo / "tests" / "test_원문.py").write_text(
    "from pathlib import Path\n"
    "글 = (Path(__file__).resolve().parent.parent / '봇.py').read_text(encoding='utf-8')\n"
    "assert 'X = 1' in 글, '배선이 끊겼다'\nprint('원문 통과')\n", encoding="utf-8")
sh(repo, "add", "-A")
sh(repo, "commit", "-q", "-m", "첫 커밋")

try:
    print("== RED: 미커밋으로 깨뜨리면 감사가 잡는다 ==")
    (repo / "셈.py").write_text("def 더하기(a, b):\n    return a - b\n", encoding="utf-8")
    r = 감사기.감사(repo=repo, 초=60)
    돌린 = {t: rc for t, rc, _ in r["결과"]}
    ok("tests/test_셈.py" in 돌린, f"이름으로 검사를 찾았다 ({sorted(돌린)})")
    ok(돌린.get("tests/test_셈.py") not in (0, None),
       f"**깨진 변경이 실패로 잡힌다** (끝값 {돌린.get('tests/test_셈.py')})")

    print("\n== 커밋 감사는 HEAD 를 본다 -- 미커밋 수정이 안 샌다 ==")
    r2 = 감사기.감사(repo=repo, 커밋=True, 초=60)
    돌린2 = {t: rc for t, rc, _ in (r2["결과"] or [])}
    ok(all(rc == 0 for rc in 돌린2.values()),
       f"HEAD 는 성하므로 커밋 감사는 초록이다 ({돌린2})")

    print("\n== GREEN: 고치면 통과한다 ==")
    # 원상복구가 아니라 '다르지만 옳은' 수정이어야 한다 -- HEAD 와 같아지면 변경이
    # 없으니 감사할 것도 없다(그것은 아래 '변경 없음' 갈래가 따로 붙든다).
    (repo / "셈.py").write_text("def 더하기(a, b):\n    return b + a\n", encoding="utf-8")
    r = 감사기.감사(repo=repo, 초=60)
    돌린 = {t: rc for t, rc, _ in r["결과"]}
    ok(돌린.get("tests/test_셈.py") == 0, f"고친 뒤에는 통과 ({돌린})")
    sh(repo, "checkout", "--", "셈.py")

    print("\n== 임포트로도 검사를 찾는다 ==")
    (repo / "돈.py").write_text("이율 = 0.07\n", encoding="utf-8")
    r = 감사기.감사(repo=repo, 초=60)
    돌린 = {t: rc for t, rc, _ in r["결과"]}
    ok("tests/test_기능.py" in 돌린,
       f"이름이 안 닮아도 import 돈 으로 찾았다 ({sorted(돌린)})")
    ok(돌린.get("tests/test_기능.py") not in (0, None), "그리고 깨진 것을 잡았다")
    (repo / "돈.py").write_text("이율 = 0.05\n", encoding="utf-8")

    print("\n== 원문을 읽는 검사도 검사로 센다 ==")
    (repo / "봇.py").write_text("import 없는꾸러미\nX = 2\n", encoding="utf-8")
    r = 감사기.감사(repo=repo, 초=60)
    돌린 = {t: rc for t, rc, _ in r["결과"]}
    ok("tests/test_원문.py" in 돌린,
       f"임포트 못 하는 파일도 이름을 따옴표로 적은 검사에 걸린다 ({sorted(돌린)})")
    ok("봇.py" not in r["안덮임"], "그래서 '검사 없음' 으로 안 찍힌다")
    ok(돌린.get("tests/test_원문.py") not in (0, None), "그리고 깨진 것(X=1 -> 2)을 잡았다")
    (repo / "봇.py").write_text("import 없는꾸러미\nX = 1\n", encoding="utf-8")

    print("\n== 검사 없는 변경은 크게 말한다 ==")
    (repo / "고아.py").write_text("x = 1\n", encoding="utf-8")
    r = 감사기.감사(repo=repo, 초=60)
    ok("고아.py" in r["안덮임"], f"안 덮인 .py 가 보고된다 ({r['안덮임']})")
    보고 = 감사기.보고(r)
    ok("검사 없는" in 보고, "보고문에도 크게 적힌다")

    print("\n== 변경이 없으면 없다고 한다 ==")
    (repo / "고아.py").unlink()
    (repo / "셈.py").write_text("def 더하기(a, b):\n    return a + b\n", encoding="utf-8")
    r = 감사기.감사(repo=repo, 초=60)
    ok(not r["변경"], f"변경 없음이 그대로 보고된다 ({r['변경']})")
finally:
    shutil.rmtree(임시, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("audit: RED 잡기 · GREEN 통과 · 임포트 추적 · 검사 없음 경고 · HEAD 분리 -- 통과")
