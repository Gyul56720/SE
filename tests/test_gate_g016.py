"""G016 -- **주석을 읽고 초록이 되는 검사**를 잡는가. 임시 저장소로 잰다.

이 게이트가 무엇을 잡고 무엇을 안 잡는지가 요점이다. 다 잡으면 쓸 수가 없다 --
소스를 읽는 단언이 전부 가짜인 것은 아니고(프롬프트 문자열·상수는 동작이다),
과잉 기각은 이 저장소가 반복해서 겪은 실패다.

실행: python3 tests/test_gate_g016.py
"""
from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import gatekeeper                                                     # noqa: E402

G016 = importlib.import_module("gates.G016_검사가_주석을_읽고_초록이_되지_않는가")

FAIL = []


def ok(cond, what):
    print(("    OK   " if cond else "    실패 ") + what)
    if not cond:
        FAIL.append(what)


def run(module_src: str, test_src: str) -> list:
    """임시 저장소를 세우고 게이트를 돌린다. **진짜 파일에 진짜 게이트를 돌린다** --
    가짜로 대신하면 이 검사가 재는 것이 게이트가 아니라 가짜가 된다."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "pkg").mkdir()
        (root / "pkg" / "mod.py").write_text(module_src, encoding="utf-8")
        (root / "tests").mkdir()
        (root / "tests" / "test_x.py").write_text(test_src, encoding="utf-8")
        return G016.check(gatekeeper.GateContext(root))


MOD = '''"""이 모듈은 **되밀기**를 한다."""


def push(x):
    # 여기서 되감기 를 한다 -- 이 낱말은 주석에만 있다
    LABEL = "실제로 도는 낱말"
    return x + 1
'''

HEAD = ("from pathlib import Path\n"
        "src = (Path(__file__).resolve().parent.parent / 'pkg' / 'mod.py')"
        ".read_text(encoding='utf-8')\n")


print("[주석] **주석에만 있는 낱말은 아무것도 재지 않는다**")
v = run(MOD, HEAD + 'assert "되감기" in src\n')
ok(len(v) == 1, f"주석 낱말을 잡는다 ({len(v)}건)")
ok(v and "되감기" in v[0] and "pkg/mod.py" in v[0], "어느 낱말이 어느 파일의 주석인지 짚는다")
ok(v and "동작을 불러서 재라" in v[0], "무엇을 하라고 말해 준다")

print("\n[독스트링] **독스트링도 주석과 같다**")
v = run(MOD, HEAD + 'assert "되밀기" in src\n')
ok(len(v) == 1, f"모듈 독스트링의 낱말도 잡는다 ({len(v)}건)")

print("\n[코드] **코드 쪽 낱말은 안 잡는다** -- 문자열 상수와 식별자는 동작이다")
v = run(MOD, HEAD + 'assert "실제로 도는 낱말" in src\n')
ok(v == [], f"코드 안의 문자열은 넘어간다 ({len(v)}건)")
v = run(MOD, HEAD + 'assert "def push" in src\n')
ok(v == [], "식별자도 넘어간다")

print("\n[없는 낱말] **이미 빨간 검사는 남의 일이다**")
v = run(MOD, HEAD + 'assert "어디에도 없는 낱말" in src\n')
ok(v == [], "파일에 아예 없는 낱말은 안 잡는다  ← 그건 이미 실패하는 검사다")

print("\n[표식] **문서 계약은 눈에 보이게 고르면 넘어간다**")
v = run(MOD, HEAD + '# G016: 문서 계약\nassert "되감기" in src\n')
ok(v == [], "같은 줄 위 표식이면 넘어간다")
v = run(MOD, HEAD + ("# G016: 문서 계약 -- 왜 그런지\n# 두 줄\n# 세 줄\n"
                     'assert "되감기" in src\n'))
ok(v == [], "주석 덩이로 적어도 걸린다  ← 까닭을 적으려면 몇 줄이 필요하다")
v = run(MOD, HEAD + ("# G016: 문서 계약\n" + "# 채움\n" * 8 + 'assert "되감기" in src\n'))
ok(len(v) == 1, "너무 멀면 안 걸린다  ← 넓히면 엉뚱한 단언까지 딸려 나간다")

print("\n[변수를 안 거쳐도] 읽는 자리에서 바로 비교하는 꼴")
v = run(MOD, "from pathlib import Path\n"
        'assert "되감기" in (Path(__file__).resolve().parent.parent / "pkg" / "mod.py")'
        ".read_text(encoding='utf-8')\n")
ok(len(v) == 1, f"변수에 담지 않아도 잡는다 ({len(v)}건)")

print("\n[안 보는 것]")
v = run(MOD, HEAD + 'assert "되" in src\n')
ok(v == [], "세 글자 미만은 안 본다  ← 우연히 맞을 것이 너무 많다")
with tempfile.TemporaryDirectory() as _d:
    _r = Path(_d)
    (_r / "tests").mkdir()
    (_r / "tests" / "test_y.py").write_text("assert 'x' in 'xy'\n", encoding="utf-8")
    ok(G016.check(gatekeeper.GateContext(_r)) == [], "소스를 안 읽는 검사는 안 본다")
ok(G016.check(gatekeeper.GateContext(Path(tempfile.gettempdir()) / "없는곳")) == [],
   "tests/ 가 없어도 안 터진다")

print("\n[깨진 파일에도 안 터진다]")
v = run(MOD, HEAD + 'assert "되감기" in src\ndef (\n')
ok(v == [], "검사 파일이 문법 오류면 조용히 넘어간다  ← 게이트가 죽으면 다 못 본다")
v = run("def (\n", HEAD + 'assert "되감기" in src\n')
ok(isinstance(v, list), "대상 파일이 깨져도 목록을 돌려준다")

print("\n[이름표]")
ok(G016.RULE_ID == "G016" and G016.TITLE, "게이트가 자기 이름을 갖는다")
# `A or B` 로 쓰면 뒤 절만 참이어도 초록이다 -- 이 파일이 잡으려는 바로 그 꼴이다.
# 표식 문구가 **어긋나지 않는지**를 잰다: 위반 문구가 상수 그대로를 안내해야 하고,
# 그 상수로 실제로 넘어가야 한다.
_v = run(MOD, HEAD + 'assert "되감기" in src\n')
ok(_v and G016.OPT_OUT in _v[0], "위반 문구가 표식 상수를 그대로 안내한다")
ok(run(MOD, HEAD + f"# {G016.OPT_OUT}\n" + 'assert "되감기" in src\n') == [],
   "안내한 그 상수로 실제로 넘어간다  ← 안내와 동작이 어긋나면 아무도 못 빠져나간다")

print()
if FAIL:
    print(f"G016: {len(FAIL)}개 실패 -- {FAIL}")
    raise SystemExit(1)
print("G016: 주석 · 독스트링 · 코드 · 표식 · 깨진 파일 -- 통과")
