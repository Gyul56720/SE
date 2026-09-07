"""갚는가 -- **던져 놓고 안 닫은 것이 얼마나 묵었나.**

절단은 효과가 있지만, 다음 화가 중심 질문을 합리적인 시간 안에 풀지 않으면 몰입이
떨어진다(EVIDENCE.md 5절). `flow` 는 이미 "열린 것이 아홉 개 넘으면 하나 닫아라" 를
시키는데 그것은 **개수**만 본다 -- 곁가지 아홉을 여닫으며 핵심 하나를 마흔 덩어리째
묵혀도 통과한다.

여기서 고정하는 계약:

  · **나이를 센다** -- 오래 열려 있는 것이 이 이야기가 갚지 않은 것이다
  · **분류하지 않는다** -- 핵심/곁을 판정하지 않는다. 판정은 기계에게 안 맡긴다
  · **모르면 모른다고 한다** -- 이어 쓰기 전부터 열린 것의 나이는 하한이지 참값이 아니다
  · **기각하지 않는다** -- 이름을 짚을 뿐이다

실행: python3 tests/test_payoff.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import payoff as P                                         # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


def run(script, start=None):
    """script[n] = (열 것들, 닫을 것들). 덩어리를 n 개 돌린 책을 돌려준다."""
    book = {"chunks": [], "ledger": {"open": dict(start or {})}}
    for n, (add, drop) in enumerate(script):
        before = dict(book["ledger"]["open"])
        for k in add:
            book["ledger"]["open"][k] = "?"
        for k in drop:
            book["ledger"]["open"].pop(k, None)
        P.record(book, before, book["ledger"]["open"], n)
        book["chunks"].append("x" * 3200)
    return book


print("[장부] **무엇을 열고 무엇을 닫았나**")
_b = run([(["가"], []), ([], []), (["나"], []), ([], []), ([], ["가"])])
_log = _b["payoff"]
ok(len(_log) == 5, f"덩어리마다 한 줄 ({len(_log)}줄)")
ok(_log[0]["opened"] == 1 and _log[0]["closed"] == 0, "연 것을 센다")
ok(_log[4]["closed"] == 1, "닫은 것을 센다")
ok(_log[4]["lives"] == [4], f"닫힌 것이 몇 덩어리 살았는지 적는다 ({_log[4]['lives']})")
ok(P.measure(_b)["ratio"] == 0.5, f"회수율 = 닫은 것/연 것 ({P.measure(_b)['ratio']})")
ok("가" not in (_b["ledger"]["_open_age"]), "닫히면 나이표에서 지운다")
ok(_b["ledger"]["_open_age"].get("나") == 2, "안 닫힌 것은 언제 열렸는지 남는다")

print()
print("[나이] **개수가 아니라 나이다** -- 곁가지를 여닫으며 핵심을 묵힐 수 있다")
_script = [(["핵심"], [])] + [([f"곁{n}"], [f"곁{n-1}"] if n else []) for n in range(1, 15)]
_b = run(_script)
_m = P.measure(_b)
ok(_m["open_now"] == 2, f"지금 열린 것은 둘뿐이다 ({_m['open_now']})  ← 개수로는 아무 문제 없다")
ok(_m["ratio"] is not None and _m["ratio"] > 0.8,
   f"회수율도 좋다 ({_m['ratio']})  ← 여기까지는 다 통과한다")
ok(_m["stale"] == ["핵심"], f"그런데 묵은 것이 잡힌다 ({_m['stale']})")
ok(_m["oldest"][0][1] == "핵심", "제일 오래된 것을 앞에 둔다")

print()
print("[되먹임] **이름을 짚는다. 기각은 안 한다**")
_br = P.brief(_b)
ok("[갚을 것]" in _br, "묵은 것이 있으면 실린다")
ok("핵심" in _br, "묵은 것의 이름을 짚는다")
ok("덩어리째 열려 있다" in _br, "얼마나 묵었는지 말한다")
ok("김빠지는 답도 답" in _br, "시원할 필요 없다고 말한다  ← 안 그러면 안 갚고 미룬다")
ok(P.brief(run([(["가"], []), ([], [])])) == "",
   "안 묵었으면 아무 말도 안 한다  ← 잘하고 있는데 잔소리하면 그것도 잡음이다")
ok(P.brief({"chunks": [], "ledger": {}}) == "", "첫 덩어리에는 안 나온다")

print()
print("[빚] **여는 것보다 닫는 것이 느리면 말한다**")
_debt = run([([f"q{n}"], []) for n in range(14)])
_bd = P.brief(_debt)
ok("빚이 쌓이는 중" in _bd, "열기만 하면 짚는다")
ok("빚이 쌓이는 중" not in P.brief(_b), "잘 갚고 있으면 그 말은 안 한다")

print()
print("[모르면 모른다] **이어 쓰기 전부터 열린 것은 나이를 모른다**")
print("      ← 원장에 그 기록이 없었다. 지금부터 세되 하한이라고 표시한다.")
_old = run([([], []) for _ in range(14)], start={"옛날부터": "?"})
_mo = P.measure(_old)
ok(_mo["unknown_age"] == 0, "첫 기록에서 나이를 채운다")
ok(_mo["oldest"][0][0] == 14,
   f"그 나이는 **지금부터** 센 것이다 ({_mo['oldest'][0][0]}덩어리)"
   "  ← 실제로는 더 오래됐을 수 있다. 하한이지 참값이 아니다")
_fresh = P.measure({"chunks": ["x"] * 20, "ledger": {"open": {"가": "?"}}})
ok(_fresh["unknown_age"] == 1 and not _fresh["oldest"],
   "장부가 없는 옛 원고는 나이를 모른다고 한다  ← 0 으로 채우지 않는다")
ok(_fresh["ratio"] is None, "장부가 비면 회수율도 None 이다")

print()
print("[배선] **프롬프트에 실린다**")
from novel import flow                                                # noqa: E402
_p = flow.write_prompt(dict(flow.blank(flow.FIRST), chunks=_b["chunks"],
                            ledger=dict(flow.blank(flow.FIRST)["ledger"],
                                        **{k: _b["ledger"][k] for k in ("open", "_open_age")}),
                            payoff=_b["payoff"]))
ok("[갚을 것]" in _p, "묵은 것이 있으면 프롬프트에 실린다")
_p2 = flow.write_prompt(dict(flow.blank(flow.FIRST), chunks=["x" * 300]))
ok("[갚을 것]" not in _p2, "잴 것이 없으면 안 실린다  ← 지금까지의 프롬프트 그대로다")

print()
if fails:
    print(f"갚기: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("갚기: 장부 · 나이 · 되먹임 · 빚 · 모르면 모른다 · 배선 -- 통과")
