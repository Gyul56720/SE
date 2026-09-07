"""연재 오케스트레이션 -- **도착지를 주되 줄거리는 안 준다.**

LLM 은 가짜다. 여기서 보는 것은 글의 질이 아니라 **배선**이다: 도착지가 세워지는가,
분량으로 마디가 넘어가는가(호출 없이), 당김이 프롬프트에 실리는가, 그리고
**자를 시키지 않는가**(마디 번호 · 남은 개수 · 분량이 프롬프트에 안 실린다).

실행: python3 tests/test_serial.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import serial as SR                                        # noqa: E402
from novel import flow                                                # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


def book(chars=0, arc=None):
    b = flow.blank("첫 문장이다.")
    if chars:
        b["chunks"] = ["가" * chars]
    if arc:
        b["arc"] = arc
    return b


ARC = {"end": "그 계약이 더는 두 사람을 묶지 못한다",
       "debts": [{"무엇": "공녀가 계약의 진짜 조항을 알게 된다", "갚음": 0},
                 {"무엇": "대공이 그것을 감춘 이유가 드러난다", "갚음": 0},
                 {"무엇": "공녀가 그 조항을 깰 수단을 얻는다", "갚음": 0}],
       "made": "ropan"}


class Fake:
    """디렉터 자리에서 도착지를 돌려준다. **부른 횟수를 센다.**"""

    def __init__(self, payload=None):
        self.calls = 0
        self.payload = payload if payload is not None else {
            "끝": "그 계약이 더는 두 사람을 묶지 못한다",
            "빚": ["공녀가 진짜 조항을 알게 된다", "대공이 감춘 이유가 드러난다",
                  "공녀가 그것을 깰 수단을 얻는다", "둘이 같은 편에 선다"]}

    def __call__(self, prompt):
        self.calls += 1
        return json.dumps(self.payload, ensure_ascii=False)


print("[세우기] **호출 한 번. 그리고 이미 있으면 안 덮는다**")
_b, _f = book(), Fake()
SR.plan(_b, _f, "ropan")
ok(_f.calls == 1, f"도착지는 호출 한 번이다 ({_f.calls}회)")
ok(SR.planned(_b), "원고에 붙는다")
ok(len(_b["arc"]["debts"]) == 4, f"빚이 실린다 ({len(_b['arc']['debts'])}개)")

SR.plan(_b, _f, "ropan")
ok(_f.calls == 1, f"두 번째 부름은 안 나간다 ({_f.calls}회)  ← 이어 쓸 때마다 다시 세우면 안 된다")

# **넘치면 자르되 모자라면 안 채운다.** 채우려면 지어내야 한다.
_b2, _f2 = book(), Fake({"끝": "끝난다", "빚": [f"빚{i}" for i in range(9)]})
SR.plan(_b2, _f2, "ropan")
ok(len(_b2["arc"]["debts"]) == SR.DEBTS[1],
   f"넘치면 자른다 ({len(_b2['arc']['debts'])}개)")

# 못 받으면 사실대로 죽는다 -- 빈 도착지를 붙이면 당김이 조용히 사라진다.
_died = False
try:
    SR.plan(book(), Fake({"끝": "", "빚": []}), "ropan")
except ValueError:
    _died = True
ok(_died, "도착지를 못 받으면 사실대로 죽는다  ← 빈 것을 붙이면 조용히 없는 것이 된다")


print()
print("[마디] **분량으로 넘어간다 -- 호출이 안 든다**")
for _chars, _want in ((0, 0), (9_999, 0), (10_000, 1), (25_000, 2)):
    ok(SR.where(book(_chars, ARC)) == _want,
       f"{_chars:,}자면 마디 {SR.where(book(_chars, ARC)) + 1}")

ok(SR.current(book(0, ARC))["무엇"].startswith("공녀가 계약"), "첫 마디는 첫 빚")
ok(SR.current(book(15_000, ARC))["무엇"].startswith("대공이"), "다음 마디는 다음 빚")

# **마지막에 머문다.** 빚이 끝났다고 당김을 놓으면 그 뒤로는 다시 도착지 없는 글이 된다.
ok(SR.done(book(40_000, ARC)), "빚을 다 지나면 done")
ok(SR.current(book(40_000, ARC)) is not None, "그래도 당김을 놓지 않는다")


print()
print("[당김] **프롬프트에 한 줄로 실린다**")
ok(SR.brief(book()) == "", "도착지가 없으면 아무 말도 안 한다  ← 없는 것을 지어내지 않는다")

_t = SR.brief(book(3_000, ARC))
ok("공녀가 계약의 진짜 조항" in _t, "이번 마디의 빚이 실린다")
ok("한 걸음 가까워지면 된다" in _t, "이루라고 하지 않는다  ← 각본이 아니라 당김이다")
ok("옮겨 적지 마라" in _t, "원고에 그대로 옮기지 말라고 한다")

_e = SR.brief(book(40_000, ARC))
ok("끝을 향해 간다" in _e and ARC["end"] in _e, "다 지나면 끝을 가리킨다")

# **자를 시키지 않는다.** 마디 번호 · 남은 개수 · 분량이 실리면 진도표를 맞추러 간다.
for _n in ("마디", "빚 1", "10,000", "3,000자", "번째", "%"):
    ok(_n not in _t, f"'{_n}' 이 프롬프트에 없다  ← 자를 시키지 않고 일을 시킨다")


print()
print("[배선] **두 프롬프트 경로 모두에 실린다**")
_src = (REPO / "novel" / "flow.py").read_text(encoding="utf-8")
ok(_src.count("SR.brief(book)") == 2,
   f"axes 와 legacy 두 자리 모두 ({_src.count('SR.brief(book)')}자리)  "
   f"← 한쪽만 넣으면 DRIFT_PROMPT 를 바꾼 런에서 당김이 사라진다")

# 당김은 **맨 앞**이어야 한다. 나머지 자는 전부 뒤를 보고 이것만 앞을 본다 --
# 뒤에 두면 지시 상한에 밀려 사라진다.
_i = _src.index("SR.brief(book)")
ok(_i < _src.index("VG.brief(book)") and _i < _src.index("TU.brief(book)"),
   "당김이 다른 자들보다 앞에 온다")

# 실제로 프롬프트 글에 들어가는지 -- 자리만 맞고 안 실리면 소용없다.
_bk = book(3_000, ARC)
_p = flow.write_prompt(_bk)
ok("공녀가 계약의 진짜 조항" in _p, "완성된 프롬프트에 실제로 있다")
ok("[어디로]" in _p, "머리표가 붙는다")

_p0 = flow.write_prompt(book(3_000))
ok("[어디로]" not in _p0, "도착지가 없으면 프롬프트도 조용하다")


print()
print("[각본 금지] **world_romance 의 15화 대본을 쓰지 않는다**")
print("      ← 그것은 특정 음대 로맨스의 각본이지 갈래의 결말 목록이 아니다.")
print("        여기서 쓰면 모든 원고가 그 이야기가 된다.")
_ssrc = (REPO / "novel" / "serial.py").read_text(encoding="utf-8")
ok("OUTCOMES" not in _ssrc.split('"""', 2)[-1],
   "코드가 OUTCOMES 를 안 부른다  ← 문서에서 왜 안 쓰는지만 말한다")

_pp = SR.plan_prompt("ropan")
ok("줄거리는 정하지 않는다" in _pp, "줄거리를 정하지 말라고 한다")
ok("상태로 적어라" in _pp, "사건이 아니라 상태로 받는다")
ok("인물 이름을 정하지 마라" in _pp,
   "이름을 여기서 안 정한다  ← 아직 아무도 없고, 이름은 이름결이 정한다")


print()
print("[띄우기] **drift.sh 가 도착지를 자동으로 세운다**")
print("      ← 사람이 따로 쳐야 하는 단계로 두면 아무도 안 친다. 이 저장소가 여섯 번")
print("        겪은 '코드가 실행에 도달하지 못하는' 자리를 일부러 하나 더 만드는 셈이다.")

_sh = (REPO / "scripts" / "drift.sh").read_text(encoding="utf-8")
ok("serial.py\" plan" in _sh, "start 가 plan 을 부른다")
ok("serial.py\" show" in _sh, "arc 로 볼 수 있다")
ok("|| echo" in _sh.split("serial.py\" plan")[1][:300],
   "실패해도 런은 계속 간다  ← 도착지가 없으면 예전 DRIFT 그대로다")
ok("--genre" in _sh.split("serial.py\" plan")[1][:200],
   "갈래를 넘긴다  ← 안 넘기면 갈래 없는 결말이 온다")


print()
if fails:
    print(f"연재: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("연재: 세우기 · 마디 · 당김 · 배선 · 각본 금지 · 띄우기 -- 통과")
