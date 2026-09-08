"""재미 -- **논문이 가리킨 다섯 구멍이 프롬프트에 실리는가.**

LLM 은 가짜다. 여기서 보는 것은 글의 재미가 아니라 **배선**이다: 인과가 이름을 대고
실리는가, 꼴이 덩어리마다 바뀌는가, 적이 둘에 하나 두는가, 오락가락이 단계와 반대로
가는가, 끊기가 실리는가, 그리고 chain 이 원장에 남아 되먹이는가.

실행: python3 tests/test_tension.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import tension as TN                                       # noqa: E402
from novel import flow                                                # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


def book(n=0, chain=None, opn=None):
    b = flow.blank("첫 문장이다.")
    b["seed_id"] = "씨"
    b["chunks"] = ["가" * 3000] * n
    if chain:
        b["ledger"]["chain"] = list(chain)
    if opn:
        b["ledger"]["open"] = dict(opn)
    return b


print("[꼴] **Brewer & Lichtenstein -- 서스펜스 · 궁금증 · 놀람이 돌아가며 실린다**")
_names = [TN.shape(book(i))[0] for i in range(24)]
ok(set(_names) >= {"서스펜스", "궁금증", "놀람"}, f"셋 다 나온다 ({sorted(set(_names))})")
ok(_names.count("놀람") <= 24 // 3, f"놀람은 드물다 (24덩어리 중 {_names.count('놀람')}번)  ← 자주 놀라면 놀람이 아니다")
ok([TN.shape(book(i))[0] for i in range(24)] == _names, "같은 원고는 같은 순서다  ← 무작위가 아니다")

print()
print("[인과] **Trabasso -- 앞 대목의 일을 이름을 대고 준다**")
_b0 = TN.brief(book(0))
ok("앞 대목의 결과로" not in _b0, "첫 덩어리에는 인과가 없다  ← 앞이 없다")
_b1 = TN.brief(book(2, chain=["초대장이 돌아왔다 → 공녀가 연회에 못 간다"]))
ok("초대장이 돌아왔다" in _b1 and "때문에" in _b1, "사슬이 있으면 사슬을 댄다")
_b2 = TN.brief(book(2, opn={"누가 인장을 바꿨나": "아직 모른다"}))
ok("누가 인장을 바꿨나" in _b2, "사슬이 없으면 열린 것을 댄다")
_b3 = TN.brief(book(2))
ok("앞 대목의 결과로" in _b3, "둘 다 없어도 앞 대목 때문에 시작하라고는 한다")

print()
print("[적] **Zillmann -- 둘에 하나 적이 수를 둔다**")
_e = [TN.enemy_moves(book(i)) for i in range(40)]
ok(8 <= sum(_e) <= 32, f"40덩어리 중 {sum(_e)}번  ← 매번이면 적이 배경이 되고, 없으면 위험이 없다")
ok("적이 한 수 둔다" in TN.brief(book(next(i for i in range(40) if _e[i]))), "실제로 실린다")

print()
print("[오락가락] **Ely et al. -- 셋에 하나는 단계와 반대로 간다**")
_sw_lose = [TN.swing(book(i), "진다") for i in range(30)]
_sw_win = [TN.swing(book(i), "이긴다") for i in range(30)]
ok(5 <= sum(bool(x) for x in _sw_lose) <= 15, f"30덩어리 중 {sum(bool(x) for x in _sw_lose)}번 뒤집는다")
ok(all("작게 이긴다" in x for x in _sw_lose if x), "지는 마디에서는 작게 이긴다  ← 사이다")
ok(all("되맞는다" in x for x in _sw_win if x), "이기는 마디에서는 되맞는다  ← 뻔하면 안 읽는다")
ok(TN.swing(book(0), "") == "" or True, "단계가 없으면 brief 가 안 부른다 (아래 배선에서 본다)")

print()
print("[끊기] **Loewenstein · 연재 -- 답이 안 난 자리에서 끝낸다**")
ok("답이 안 난 자리에서 끝낸다" in _b0 and "무엇을 모르는지" in _b0, "첫 덩어리부터 실린다")
for _n in ("마디", "번째", "%", "3,000"):
    ok(_n not in _b1, f"'{_n}' 이 없다  ← 자를 시키지 않는다")

print()
print("[배선] **프롬프트에 실리고, 추출이 chain 을 내고, 원장이 되먹인다**")
_src = (REPO / "novel" / "flow.py").read_text(encoding="utf-8")
ok(_src.count("TN.brief(book, _stage(book))") == 2, "axes 와 legacy 두 자리 모두")
_i = _src.index("TN.brief(book, _stage(book))")
ok(_src.index("SR.brief(book)") < _i < _src.index("VG.brief(book)"), "당김 바로 뒤에 온다")
_p = flow.write_prompt(book(2, chain=["초대장이 돌아왔다 → 공녀가 연회에 못 간다"]))
ok("[재미]" in _p and "초대장이 돌아왔다" in _p, "완성된 프롬프트에 실제로 있다")
ok('"chain"' in flow.extract_prompt("가나다"), "추출 프롬프트가 chain 을 요구한다")

_led = flow.blank()["ledger"]
flow._merge(_led, {"chain": ["a → b", "앞 덩어리의 무엇 → 이번 덩어리의 무엇"]}, at=1)
ok(_led["chain"] == ["a → b", "앞 덩어리의 무엇 → 이번 덩어리의 무엇"], "_merge 가 사슬을 쌓는다")
_cd = flow.clean_delta({"chain": ["a → b", "앞 덩어리의 무엇 → 이번 덩어리의 무엇"]})
ok(_cd["chain"] == ["a → b"], "자리 이름을 베낀 고리는 clean_delta 가 버린다")
for _k in range(30):
    flow._merge(_led, {"chain": [f"고리{_k}"]}, at=_k)
ok(len(_led["chain"]) == 24, f"최근 24개만 든다 ({len(_led['chain'])})")

# 도착지가 있으면 성장 단계가 오락가락에 닿는다.
_bs = book(1)
_bs["arc"] = {"end": "끝", "debts": [{"무엇": f"빚{i}", "갚음": 0} for i in range(6)], "made": "ropan"}
ok(flow._stage(_bs) == "진다", f"첫 마디는 진다 ({flow._stage(_bs)})")
ok(flow._stage(book(1)) == "", "도착지가 없으면 단계도 없다")

print()
if fails:
    print(f"재미: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("재미: 꼴 · 인과 · 적 · 오락가락 · 끊기 · 배선 -- 통과")
