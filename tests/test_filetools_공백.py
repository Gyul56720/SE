"""정확 편집이 **공백만 다른 유일한 자리**는 스스로 맞추는지 붙든다.

실측 2026-09-12(VM): `!개선` 이 제2의 뇌 근거까지 들고 패치를 냈는데 `ValueError: old 가 파일에
없다` 로 끝났다. 모델은 앞 200줄을 보고 old 를 짓고, 들여쓰기 한 칸이면 정확히-한-번 규칙에
걸린다. 그 실패의 대부분은 뜻이 아니라 공백이다.

붙드는 것: (1) 글자 그대로 있으면 예전처럼, (2) 들여쓰기·줄 끝 공백·속 공백만 다르고 자리가
하나면 **파일의 실제 글에 맞춰 바꾼다**(그렇다고 말한다), (3) 공백만 다른 자리가 둘이면 예전처럼
거절한다(안전 규칙은 그대로), (4) 뜻이 다르면 거절한다, (5) old 에 빈 줄이 없어도 파일의 빈 줄은
건너뛴다, (6) 바뀐 결과가 옳다(new 가 그 자리에 들어간다).

실행: python3 tests/test_filetools_공백.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import filetools  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


d = Path(tempfile.mkdtemp(prefix="test-ft-"))
try:
    (d / "src").mkdir()
    f = d / "src" / "a.py"
    f.write_text("def f(a, b):\n    x = a + b   \n\n    return x\n\n\ndef g():\n    return 1\n", encoding="utf-8")

    print("== 글자 그대로 있으면 예전처럼 ==")
    말 = filetools.편집("src/a.py", "    return 1\n", "    return 2\n", repo=d)
    ok("공백" not in 말 and "return 2" in f.read_text(encoding="utf-8"), f"그대로 바꾼다 ({말})")

    print("\n== 들여쓰기·줄 끝 공백만 다르고 자리가 하나면 맞춘다 ==")
    말 = filetools.편집("src/a.py", "  x = a+b\n  return x\n", "    x = a * b\n    return x\n", repo=d)
    본 = f.read_text(encoding="utf-8")
    ok("공백만 달라" in 말, f"**그렇다고 말한다** ({말})")
    ok("    x = a * b\n    return x\n" in 본 and "a + b" not in 본, "new 가 그 자리에 들어갔다")
    ok("def g():\n    return 2\n" in 본, "다른 곳은 안 건드렸다")

    print("\n== 뜻이 다르면 거절 ==")
    try:
        filetools.편집("src/a.py", "    return 99\n", "x", repo=d); ok(False, "없는 글은 거절해야 한다")
    except ValueError as e:
        ok("old 가 파일에 없다" in str(e), f"없는 글은 예전처럼 거절 ({str(e)[:40]})")

    print("\n== 공백만 다른 자리가 둘이면 거절 (안전 규칙 그대로) ==")
    f.write_text("def f():\n    return 1\n\n\ndef g():\n  return 1\n", encoding="utf-8")
    try:
        filetools.편집("src/a.py", "return 1", "return 2", repo=d); ok(False, "둘이면 거절해야 한다")
    except ValueError as e:
        ok("여러 번" in str(e) or "번 나온다" in str(e), f"둘이면 거절 ({str(e)[:50]})")
    ok(f.read_text(encoding="utf-8").count("return 1") == 2, "거절했으면 파일은 그대로다")
finally:
    shutil.rmtree(d, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("filetools 공백: 그대로 · 공백만 다르면 맞춤 · 뜻 다르면 거절 · 둘이면 거절 -- 통과")
