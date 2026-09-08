"""뼈대 -- **남의 작품의 차례를 따라가되 문장은 우리 것으로.**

사용자가 방향으로 삼는 작품이 있다. 그 이야기의 차례를 따라가되 꼴은 웹소설로 쓴다.
여기서 고정하는 계약:

  · 뼈대에는 **문장이 안 들어간다** -- 상태 변화 한 줄과 갈래뿐이다
  · 뽑는 것은 토막당 호출 한 번. 그것으로 끝이다
  · 뼈대가 있으면 그 차례가 프롬프트에 실리고, 없으면 갈래만 뽑아 준다
  · 원고가 뼈대보다 길어져도 안 죽는다

실행: python3 tests/test_spine.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import compose, flow, plot, spine                          # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


D = Path(tempfile.mkdtemp())
SP = D / "spine.json"
SP.write_text(json.dumps({"beats": [
    {"n": 1, "갈래": "위치", "무엇": "한 사람이 오래 있던 데를 떠난다", "누구": "본인"},
    {"n": 2, "갈래": "앎", "무엇": "몰랐던 사실 하나가 드러난다", "누구": "둘 사이"},
]}, ensure_ascii=False), encoding="utf-8")

print("[묻기] **요약을 시키지 않는다** -- 달라진 것 하나만")
_q = spine.ask("가" * 100)
ok("무엇이 달라졌는지" in _q, "상태 변화를 묻는다")
ok("줄거리를 요약하지 마라" in _q, "요약은 막는다  ← 요약을 받으면 그것을 베낀다")
ok("원문 문장을 옮겨 적지 마라" in _q, "문장을 못 가져오게 한다")
ok(all(k in _q for k in list(plot.CHANGE)[:3]), "갈래는 TAXONOMY 의 상태 변화다")
ok(len(_q) < 1200, f"짧게 묻는다 ({len(_q)}자)  ← 토막마다 한 번씩 부른다")

print()
print("[따라가기] **차례가 프롬프트에 실린다**")
ok(spine.at(0, SP)["n"] == 1, "덩어리 0 은 첫 비트")
ok(spine.at(1, SP)["n"] == 2, "덩어리 1 은 둘째 비트")
ok(spine.at(99, SP)["n"] == 2, "원고가 더 길어도 안 죽는다  ← 마지막 비트를 쥔다")
_b = spine.brief(0, SP)
ok("무엇이 달라지나" in _b and "위치" in _b, "무엇이 달라질지 말해 준다")
ok("무엇으로 그렇게 되는지는 네가 정한다" in _b, "내용은 우리가 정한다")
ok("본보기가 아니다" in _b, "차례일 뿐 본보기가 아니라고 못박는다")

print()
print("[없을 때] **뼈대가 없으면 갈래만 뽑아 준다**")
ok(spine.brief(0, D / "없다.json") == "", "없으면 빈 줄")
_p = flow.write_prompt(flow.blank())
ok(any(t in _p for t in ("[이 대목의 짜임]", "[이 대목에서 일어날 일]")),
   "그래도 한 걸음은 준다  ← 의미층이나 plot 이 대신한다")

print()
print("[안 담는 것] **문장은 안 들어간다**")
_raw = SP.read_text(encoding="utf-8")
ok('"문장"' not in _raw and "chunks" not in _raw, "뼈대에 원문이 없다")
# 여기 있던 `"저장소에 안 올린다" in spine.py` 를 뺐다 -- 그 문장은 **주석**에 있어서
# 무시 규칙을 지워도 초록이었다(G016). 진짜 계약은 바로 아래 줄이 잰다.
_gi = (Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8")
ok("novel/spine.json" in _gi, "실제로 무시 목록에 있다  ← 남의 작품에서 나온 것이다")

print()
print("[견주기] **얼마나 따라갔나** -- 호출 없이")
_bk = D / "b.json"
_bk.write_text(json.dumps({"chunks": ["가"] * 1}, ensure_ascii=False), encoding="utf-8")
_c = spine.cover(SP, _bk)
ok(_c["비트"] == 2 and _c["덩어리"] == 1, "비트 수와 덩어리 수를 센다")
ok(0 < _c["따라간 몫"] <= 1, f"몫이 나온다 ({_c['따라간 몫']:.0%})")

print()
if fails:
    print(f"뼈대: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("뼈대: 묻기 · 따라가기 · 없을 때 · 안 담는 것 · 견주기 -- 통과")
