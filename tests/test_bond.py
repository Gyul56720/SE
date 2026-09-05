"""관계와 몸 -- **인물 사이에 아무것도 없으면 사람들이 한 방에 서 있기만 한다.**

카드로 갈리고 몸으로도 갈렸는데 둘 사이에는 이름이 없었다. 그래서 대사만 오가고
아무 일도 안 일어났다. 관계에 이름이 붙는 순간 할 일이 정해진다 -- 연인이면 자고 안고
다투고, 친구면 욕하고 화해하고, 어색한 사이면 친해지려다 더 어색해진다.

실행: python3 tests/test_bond.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import bond, flow, style, trait                             # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


print("[관계] **이름을 붙이면 할 일이 정해진다**")
ok(len(bond.KIND) >= 20, f"관계가 충분히 갈린다 ({len(bond.KIND)}가지)")
ok(all(len(does) > 10 for _, does in bond.KIND),
   "관계마다 **하는 일**이 붙어 있다  ← 이름만 있으면 말로만 관계가 된다")
kinds = {k for k, _ in bond.KIND}
for want in ("연인", "오랜 친구", "어색한 사이", "한쪽만 마음이 있는 사이"):
    ok(want in kinds, f"관계: {want}")
dup = sum(bond.draw("s", i)["kind"] == bond.draw("s", i + 1)["kind"] for i in range(200))
ok(dup == 0, f"연달아 같은 관계가 아니다 ({dup}건)")

bb = bond.brief(bond.draw("a", 0))
ok("말로만 관계를 말하지 마라" in bb,
   "'우리는 친구였다' 가 아니라 친구가 하는 짓을 하게 한다")
ok("관계가 문제를 풀지 않는다" in bb,
   "사랑이 사건을 해결하면 편의주의다  ← 앞서 정한 금지를 그대로 지킨다")
ok("되돌려 주지 마라" in bb,
   "틀어진 것은 틀어진 채로 간다  ← '실패한 것은 실패한 채로' 와 같은 규칙이다")
ok("급발진이 나온다" in bb, "관계가 움직이는 자리가 사람이 제일 이상해지는 자리다")

print()
print("[몸] **종류가 많아야 사람이 안 겹친다**")
ok(len(trait.OUTER) >= 55, f"몸의 사실 ({len(trait.OUTER)}가지 × 쓰는 법 {len(trait.OUTER_USE)})")
ok(len({trait.draw("s", i)["outer"] for i in range(60)}) > 25,
   "예순 번 뽑으면 스물다섯 가지 넘게 나온다")

print()
print("[섞임] **매번 다 붙이면 인물이 관계표가 된다**")
b = flow.blank()
rel = sum("[관계]" in flow.write_prompt(dict(b, chunks=["x"] * i)) for i in range(1, 101))
bod = sum("[설정]" in flow.write_prompt(dict(b, chunks=["x"] * i)) for i in range(1, 101))
ok(25 < rel < 55, f"관계는 절반 아래 ({rel}/100)")
ok(20 < bod < 55, f"몸도 절반 아래 ({bod}/100)")
ok("관계" in flow.CARD and "몸" in flow.CARD, "카드에 관계·몸 칸이 있다")
ok("관계 칸" in flow.extract_prompt("x") and "몸 칸" in flow.extract_prompt("x"),
   "추출기가 둘 다 적는다  ← 한 번 맺어진 관계는 저절로 풀리지 않는다")

print()
print("[결] **사건은 크게, 분위기는 가볍게**")
n = " ".join(style.narrator().split())
ok("큰일을 미루지 마라" in n,
   "큰일을 뒤로 아끼지 않는다  ← 문학은 첫 장에서 사람을 죽이기도 한다")
ok("다만 무게를 얹지 마라" in n, "그런데 무게는 얹지 않는다  ← 우리는 밝은 싸구려 픽션이다")
ok("사건은 크게,\n    분위기는 가볍게" in style.narrator()
   or "사건은 크게, 분위기는 가볍게" in n, "둘을 한 문장으로 못박는다")

print()
print("[스윙] **재즈처럼 -- 박자를 어긋나게**")
ok("[스윙]" in style.narrator(), "스윙 항목이 화자에 있다")
ok("한 박 빠르게 끝내라" in n, "독자가 더 갈 줄 알 때 멈춘다  ← 그 빈자리가 스윙이다")
ok("되받아치기" in n, "대사는 되받아치기다  ← 답이 질문에 맞을 필요가 없다")
ok("박자표" in n, "같은 길이가 세 번 이어지면 리듬이 아니라 박자표다")

print()
print("[설정] **설정은 원고가 아니라 코드가 정한다**")
print("      ← 계수를 원고에 저장해 두면 이어 쓸 때 그것을 쓴다. 그러면 코드를 고쳐도")
print("        옛 원고는 옛 설정으로 계속 돈다 -- 밤새 고친 것이 하나도 안 걸린다.")
import json as _json, sys as _sys, tempfile as _tf                    # noqa: E402
_d = Path(_tf.mkdtemp()) / "old.json"
_old = flow.blank()
_old["chunks"] = ["옛 본문"]
_old["drift"], _old["matter"] = 0.5, 0.9
_old.pop("trait", None)
_old.pop("bond", None)
_d.write_text(_json.dumps(_old, ensure_ascii=False), encoding="utf-8")
flow.BACKOFF = (0,)
_argv = _sys.argv
_sys.argv = ["flow.py", "--resume", str(_d), "--chars", "1"]
try:
    flow.main()
finally:
    _sys.argv = _argv
_new = _json.loads(_d.read_text(encoding="utf-8"))
ok(_new["drift"] == flow.DRIFT and _new["matter"] == flow.MATTER,
   f"옛 계수가 지금 기본값으로 맞춰진다 ({_old['drift']}→{_new['drift']}, "
   f"{_old['matter']}→{_new['matter']})")
ok(_new["trait"] == flow.TRAIT and _new["bond"] == flow.BOND,
   "원고에 없던 새 축도 채워진다  ← 나중에 생긴 축이 옛 원고에서 빠지면 안 된다")
ok(_new["chunks"] == ["옛 본문"], "원고는 그대로다  ← 설정만 갈아 끼운다")

print()
if fails:
    print(f"관계·몸: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("관계·몸: 관계 목록 · 하는 일 · 몸 종류 · 섞임 · 결 · 스윙 -- 통과")
