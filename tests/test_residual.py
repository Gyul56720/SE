"""**빠진 축을 사람이 떠올리지 않게 한다.**

축은 늘 이렇게 늘었다: 사용자가 "대사도 특이하다" 고 하면 대사 축을, "편지" 라고
하면 삽입 칸을 붙였다. 목록을 먼저 적는 것으로도 모자랐다 -- 적을 때 떠오르지 않은
것은 목록에도 없었다(조판층이 통째로 빠져 있었다).

그래서 열거를 생성이 아니라 **검색**으로 바꾼다. 표본과 원고를 갈래별로 세어 차이가
큰 순으로 세우고, 이미 재는 축으로 설명되는 것을 걸러내면 남는 것이 후보다.

여기서 고정하는 계약:

  · **심어 둔 차이를 찾아낸다** -- 못 찾으면 이 자는 쓸모가 없다
  · **한쪽에만 있는 것에서 안 터진다** -- 분모가 0이 되던 자리다
  · **같은 것이 양쪽에 안 나온다** -- 위에서 잘라 뒤집으면 그렇게 된다
  · **이미 재는 축은 후보에서 뺀다** -- 그건 그 축을 맞추면 따라 맞는다

실행: python3 tests/test_residual.py
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_spec = importlib.util.spec_from_file_location(
    "residual", Path(__file__).resolve().parent.parent / "scripts" / "residual.py")
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

fails = []


def ok(cond, label):
    print(("  OK  " if cond else "  실패 ") + label)
    if not cond:
        fails.append(label)


# 표본에는 편지가 있고 원고에는 없다. 자는 이것을 스스로 찾아내야 한다.
SAMPLE = ("그는 마루에 앉아 있었다.\n영이에게\n잘 지내니. 나는 여기 있다.\n철수 올림\n"
          * 8)
DRAFT = ("그는 마루에 앉아 있었다.\n창밖으로 비가 내렸다. 그는 일어섰다.\n" * 8)

print("[심어 둔 차이를 찾는다]")
fa, fd = R.families(SAMPLE), R.families(DRAFT)
rows = R.logodds(fa["낱말"], fd["낱말"])
top = [k for z, k, _a, _b in rows if z > 1.0]
ok("올림" in top or "영이에게" in top or "지내니" in top,
   f"편지의 자국을 위로 올린다 ({top[:5]})")
ok(all(z >= n for z, n in zip([r[0] for r in rows], [r[0] for r in rows][1:])),
   "치우친 순으로 세운다")

print("\n[한쪽에만 있어도 안 터진다]")
from collections import Counter                                      # noqa: E402
ok(R.logodds(Counter({"가": 9}), Counter()) != [], "한쪽이 비어도 값을 낸다")
ok(R.logodds(Counter(), Counter()) == [], "둘 다 비면 빈 것을 낸다")
ok(R.logodds(Counter({"가": 1}), Counter({"나": 1})) == [],
   f"{R.MIN_N}번도 안 나온 것은 안 본다  ← 한두 번은 차이가 아니라 우연이다")

print("\n[같은 것이 양쪽에 안 나온다]")
out = []
_was = sys.stdout
try:
    import io
    sys.stdout = io.StringIO()
    R.main([str(Path(__file__).parent / "sample_job.txt"),
            str(Path(__file__).parent / "sample_outside.txt"), "--top", "5"])
    out = sys.stdout.getvalue()
finally:
    sys.stdout = _was
for block in out.split("[")[1:]:
    head = block.split("]")[0]
    a = block.split("표본에 짙다:")[-1].split("\n")[0]
    b = block.split("원고에 짙다:")[-1].split("\n")[0]
    same = {t.split("(")[0] for t in a.split(" · ")} & {t.split("(")[0] for t in b.split(" · ")}
    same.discard("이렇다 할 것이 없다")
    ok(not same, f"{head}: 양쪽에 겹치는 것이 없다 {sorted(same)[:3]}")

print("\n[이미 재는 축은 뺀다]")
ok(R.known("부호", ".") and R.known("어절 꼬리", "는"), "부호와 조사는 설명된 것으로 본다")
ok(not R.known("낱말", "편지"), "낱말은 설명되지 않는다  ← 여기가 후보가 나오는 자리다")

print()
if fails:
    print(f"잔차: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("잔차: 찾기 · 안 터짐 · 안 겹침 · 거르기 -- 통과")
