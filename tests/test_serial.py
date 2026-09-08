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
print("[성장] **주인공은 지다가 이긴다 -- 마디가 어디냐로 정한다**")
print("      ← 사용자 평(2026-09-08): 주인공이 성장하지 않는다. 역경을 만나고 힘들어가다")
print("        성장해야 한다.")
_ga = dict(ARC, start="공녀는 제 이름으로 초대장 한 장 못 보낸다",
           debts=[{"무엇": f"빚{i}", "갚음": 0} for i in range(6)])
_g0, _g1, _g2 = book(0, _ga), book(25_000, _ga), book(55_000, _ga)
ok(SR.stage(_g0)[0] == "진다" and SR.stage(_g1)[0] == "버틴다" and SR.stage(_g2)[0] == "이긴다",
   f"앞 · 중간 · 뒤 = {SR.stage(_g0)[0]} · {SR.stage(_g1)[0]} · {SR.stage(_g2)[0]}")
ok(SR.stage(book(0)) is None, "도착지가 없으면 단계도 없다")
_gb = SR.brief(_g0)
ok("**진다.**" in _gb and "초대장 한 장" in _gb, "첫 마디는 지라고 하고 처음의 주인공을 싣는다")
ok("초대장 한 장" not in SR.brief(_g2) and "못 하던 것을 한다" in SR.brief(_g2),
   "뒤 마디는 처음을 되풀이하지 않고 이기라고 한다")
_pp2 = SR.plan_prompt("ropan")
ok('"시작"' in _pp2 and "역경" in _pp2, "디렉터에게 시작 상태와 역경을 요구한다")
_b3, _f3 = book(), Fake({"끝": "끝난다", "시작": "아무것도 못 한다", "빚": ["a", "b", "c", "d"]})
SR.plan(_b3, _f3, "ropan")
ok(_b3["arc"].get("start") == "아무것도 못 한다", "시작이 원고에 붙는다")
ok("시작:" in SR.show(_b3), "show 에 시작이 보인다")

print()
print("[끝] **목표를 알면 마디가 거기에 맞고, 마지막 덩어리는 닫으라고 한다**")
print("      ← 빚 다섯 x 1만 자 = 5만 자인데 목표가 5만 자면 끝을 향하는 마디가 없다.")
_bt = book(0, ARC); _bt["_target"] = 20_000
ok(SR.span(_bt) == 5_000, f"빚 셋 · 목표 2만 자면 한 마디 5,000자 ({SR.span(_bt):,})")
ok(SR.span(book(0, ARC)) == SR.SPAN, "목표를 모르면 SPAN 그대로")
_bt["chunks"] = ["가" * 15_000]
ok(SR.done(_bt) and not SR.closing(_bt), "빚을 다 지나면 끝을 향하되 아직 안 닫는다")
_bt["chunks"] = ["가" * 17_000]
ok(SR.closing(_bt), "목표까지 덩어리 하나 남짓이면 닫는다")
_bf = SR.brief(_bt)
ok("여기서 이야기를 닫는다" in _bf and ARC["end"] in _bf and "마지막 문장으로 끝내라" in _bf,
   "마지막 대목의 당김은 닫으라고 한다")
ok("[어디로]" in flow.write_prompt(_bt), "그것이 프롬프트에 실린다")

# flow.run 이 목표를 원고에 남긴다 -- 안 남기면 위 전부가 검사에서만 참이다.
_fsrc = (REPO / "novel" / "flow.py").read_text(encoding="utf-8")
ok('book["_target"] = int(target)' in _fsrc, "run() 이 _target 을 원고에 적는다")
ok("SR.plan(book" in _fsrc, "flow.main 이 도착지를 스스로 세운다  ← 딴 프로세스가 파일에 쓰면 다음 저장이 덮는다")
_ssrc2 = (REPO / "novel" / "serial.py").read_text(encoding="utf-8")
ok("if planned(book):" in _ssrc2.split("def main", 1)[1],
   "serial.py plan 은 이미 있으면 파일을 안 쓴다  ← 돌고 있는 런의 덩어리를 지운다")


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
print("[줄기] **소설 전체의 꼴을 본보기로 보여 주고, 고른 것을 원고에 남긴다**")
print("      ← 사용자(2026-09-08): 복수극도 좋고 거지가 왕궁 들어가서 권력 탈취하는 것도 좋고 --")
print("        예시야, 하드코딩하지 마. 이런 문법들을 더 모으라고.")
from novel import space as SP                                         # noqa: E402
_pk = SR.plan_prompt("ropan", "씨앗")
ok("[줄기 본보기" in _pk and '"줄기"' in _pk, "줄기 본보기를 싣고 줄기를 요구한다")
ok(sum(1 for n in SP.names("줄기") if f"    {n}:" in _pk) == 4, "넷을 보여 준다")
ok(SR.plan_prompt("ropan", "가") != SR.plan_prompt("ropan", "나"), "씨앗이 다르면 다른 넷이다")
ok("목록 밖을 지어도 된다" in _pk, "목록 밖도 된다  ← 닫힌 목록이 아니다")
ok("되찾고 · 편을 늘리고 · 누군가 그것을 인정하는 자리" in _pk, "끝은 사이다다  ← 값을 치르고 물러나는 끝이 아니다")
ok("되갚는 것 · 오르는 것 · 곁에 서는 사람" in _pk, "뒤 절반의 빚에 도파민의 재료가 하나씩 든다")
_bk, _fk = book(), Fake({"줄기": "복수 + 가면", "끝": "끝난다", "시작": "못 한다", "빚": ["a", "b", "c", "d"]})
_bk["seed_id"] = "씨앗"
SR.plan(_bk, _fk, "ropan")
ok(_bk["arc"].get("shape") == "복수 + 가면", "줄기가 원고에 붙는다")
ok("줄기: 복수 + 가면" in SR.show(_bk), "show 에 줄기가 보인다")
ok(SR.plan_prompt("ropan").count("[줄기 본보기") == 1, "씨앗 없이 불러도 산다  ← 옛 부름")

print()
if fails:
    print(f"연재: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("연재: 세우기 · 마디 · 당김 · 배선 · 각본 금지 · 띄우기 · 줄기 -- 통과")
