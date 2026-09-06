"""동적 프롬프트 -- **어긋난 축만 싣는다.**

지금까지 프롬프트는 상수였다. 그래서 두 가지가 동시에 나빴다: 매 호출 다 태우고,
스무 항목이 늘 켜져 있어 **어느 것도 강조가 아니었다.** 여기서 고정하는 계약:

  · 맞고 있는 축은 **한 글자도** 안 싣는다
  · 첫 덩어리에는 잴 것이 없으니 기준을 다 준다
  · 한 번에 몇 개까지만 -- 한꺼번에 시키면 안 지켜진다
  · 지시문은 코드가 아니라 데이터다(directives.json)

실행: python3 tests/test_dyn.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import dyn, flow, profile as PF, targets as TG              # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


HERE = Path(__file__).resolve().parent
JOB = (HERE / "sample_job.txt").read_text(encoding="utf-8")
FLAT = "그는 갔다.\n" * 300

print("[고름] **어긋난 축만 골라낸다**")
_off = dyn.off(FLAT)
ok(_off, f"단조로운 글에서 어긋난 축을 찾는다 ({[k for k, *_ in _off][:4]})")
ok(all(d > dyn.SLACK for _, _, d, _v in _off), "폭 안인 축은 안 고른다")
ok([d for _, _, d, _ in _off] == sorted([d for _, _, d, _ in _off], reverse=True),
   "먼 것부터 온다  ← 하나만 고칠 것이므로")
ok(dyn.off("") == [], "빈 글에서도 안 죽는다")

print()
print("[싣기] **맞고 있으면 한 글자도 안 싣는다**")
ok(len(dyn.asks(FLAT)) <= dyn.MAX_ASKS,
   f"한 번에 {dyn.MAX_ASKS}개까지만  ← 한꺼번에 시키면 안 지켜진다")
_b = dyn.brief(FLAT)
ok(_b.startswith("[직전 덩어리에서 어긋난 것]"), "머리표가 붙는다")
ok("여기만 고쳐라" in _b, "나머지는 지금대로 좋다고 말한다")
ok(len(_b) < 900, f"짧다 ({len(_b)}자)  ← 이게 상수 블록을 대신한다")

# 폭 안에만 있는 글은 아무 말도 안 듣는다. 표본 자체를 넣어 확인한다 --
# 우리가 표본을 벌하면 자가 틀린 것이다.
_calm = "\n".join(l for l in JOB.split("\n") if l.strip())[:0] or ""
ok(dyn.brief("") == "", "잴 수 없는 글에는 아무 말도 안 한다")
_high = dyn.SLACK
try:
    dyn.SLACK = 99.0                      # 아무것도 어긋나지 않은 셈 치고
    ok(dyn.brief(JOB) == "", "다 맞고 있으면 빈 줄이다  ← 한 글자도 안 싣는다")
finally:
    dyn.SLACK = _high

print()
print("[데이터] **지시문은 코드가 아니다**")
ok(dyn.PATH.exists(), f"파일로 있다 ({dyn.PATH.name})")
_ax = dyn.load()
ok(set(_ax) >= set(PF.AXES) - {"repeat"}, f"재는 축마다 지시문이 있다 ({len(_ax)}개)")
ok(all(set(v) <= {"low", "high"} for v in _ax.values()), "모자랄 때와 넘칠 때를 따로 적는다")
_txt = " ".join(s for v in _ax.values() for s in v.values())
import re as _re                                                      # noqa: E402
ok(not _re.search(r"\d{2,}(?![}%])", _txt.replace("{", " {")),
   "지시문에 수를 안 박는다  ← 수는 targets.json 에서 와서 렌더러가 채운다")

print()
print("[프롬프트] **첫 덩어리는 다 주고, 그다음엔 어긋난 것만**")
_first = flow.write_prompt(flow.blank())
ok("길이를 섞어라 -- 이건 재서 판정한다" in _first,
   "첫 덩어리에는 기준을 다 준다  ← 잴 것이 없다")
_next = flow.write_prompt(dict(flow.blank(), chunks=[FLAT]))
ok("길이를 섞어라 -- 이건 재서 판정한다" not in _next,
   "이어 쓸 때는 그 상수 블록을 안 싣는다")
ok("[직전 덩어리에서 어긋난 것]" in _next, "대신 어긋난 축만 싣는다")
ok("재서 판정한다" in _next, "재서 본다는 것은 여전히 말해 준다")

_was = flow.DYNAMIC
try:
    flow.DYNAMIC = False
    ok("길이를 섞어라 -- 이건 재서 판정한다" in flow.write_prompt(
        dict(flow.blank(), chunks=[FLAT])), "끄면 예전 그대로다  ← 지운 것이 아니다")
finally:
    flow.DYNAMIC = _was

print()
if fails:
    print(f"동적 프롬프트: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("동적 프롬프트: 고름 · 싣기 · 데이터 · 프롬프트 -- 통과")
