"""미결 -- **증명이 흘러가는 느낌은 갚아야 할 것이 쌓여 있어서 생긴다.**

원장은 확정된 사실만 적고 있었다. 인물·장소·사물·사건, 전부 닫힌 것. 그래서 매 덩어리가
자기 안에서 완결되고, 결과적으로 표류가 아니라 나열이 됐다.

수학에서 증명이 나아가는 것은 결론이 정해져서가 아니라 **아직 보이지 못한 것**이 남아
있어서다. 소설도 같다 -- 묻고 답 안 한 것, 한 약속, 진 빚, 기다리는 사람.

닫으라고 시키지는 않는다. 시키는 순간 그것이 각본이 되고, 각본은 이 모드가 버린 것이다.

실행: python3 tests/test_open.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import diffusion as F, flow, style                         # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


print("[원장] **닫힌 사실 옆에 미결 칸을 낸다**")
L = flow.blank()["ledger"]
ok("open" in L, "원장에 열린 것 칸이 있다")
ok(not flow._merge(L, {"open": {"요우가 기다리는 사람": "누구인지 안 나왔다",
                                "자물쇠가 둘인 이유": "안 나왔다"}}, at=0),
   "여는 것은 기각하지 않는다  ← 미결은 모순이 아니다")
ok(len(L["open"]) == 2, "둘이 열렸다")

flow._merge(L, {"closed": ["자물쇠"]}, at=1)
ok("자물쇠가 둘인 이유" not in L["open"], "닫히면 목록에서 빠진다  ← 이름이 겹치면 같은 것으로 본다")
ok("요우가 기다리는 사람" in L["open"], "안 닫은 것은 남는다")

flow._merge(L, {"open": {"새 미결": "x"}, "closed": ["새 미결"]}, at=2)
ok("새 미결" not in L["open"],
   "같은 덩어리에서 열고 닫으면 안 남는다  ← 그 자리에서 답한 것은 미결이 아니다")

print()
print("[프롬프트] **닫으라고 시키지 않는다. 손대라고만 한다**")
bk = flow.blank()
bk["chunks"] = ["앞."]
p0 = flow.write_prompt(bk)
ok("[열린 것]" not in p0, "열린 것이 없으면 블록도 없다")

flow._merge(bk["ledger"], {"open": {"빌린 돈": "안 갚았다"}}, at=0)
p = flow.write_prompt(bk)
ok("[열린 것]" in p, "있으면 블록이 실린다")
ok(p.count("[열린 것]") == 1, "한 번만 실린다  ← 브리핑과 블록에 두 번 실으면 프롬프트만 무거워진다")
ok("닫으라는 것이 아니다" in p, "닫으라고 시키지 않는다  ← 시키면 그게 각본이다")
ok("하나를 건드려라" in p, "손을 대라고 한다")
ok("더 벌려도 되고" in p, "벌리는 것도 건드리는 것이다")
ok("열린 것 하나를 건드린다" in p, "맨 끝 필수 목록에도 오른다")

for i in range(12):
    flow._merge(bk["ledger"], {"open": {f"미결{i}": "x"}}, at=1)
ok("하나쯤 닫아라" in flow.write_prompt(bk),
   "너무 많이 열리면 그때만 닫으라고 한다  ← 벌리기만 하면 산만해진다")

print()
print("[자] **열기와 닫기를 함께 센다**")
before = {"open": {f"미결{i}": "x" for i in range(11)}}
same = {"open": dict(before["open"])}
closed = {"open": {k: v for k, v in before["open"].items() if k != "미결0"}}
ok(F.opened(before, closed) == (0, 1), "연 것과 닫은 것을 센다")
ok(any("하나는 닫아라" in c for c in F.check("본문", before, same)),
   "쌓였는데 안 닫으면 짚는다")
ok(not any("하나는 닫아라" in c for c in F.check("본문", before, closed)),
   "하나라도 닫으면 넘어간다")
few = {"open": {"하나": "x"}}
ok(not any("하나는 닫아라" in c for c in F.check("본문", few, few)),
   "적게 열려 있으면 안 따진다  ← 미결이 쌓여 있어도 되는 이야기가 있다")
ok(F.score("본문", before, same) > F.score("본문", before, closed),
   "점수로 가른다  ← 다만 소프트다. 원고를 죽이지 않는다")

print()
print("[추출·보기] 사람이 볼 수 있는가")
e = flow.extract_prompt("x")
ok('"open"' in e and '"closed"' in e, "추출기가 열림과 닫힘을 둘 다 뽑는다")
ok("던져지고 아직 안 닫힌 것" in e, "무엇이 미결인지 말해 준다")
ok("글이 답을 준 것은 여기 적지 마라" in e, "답한 것은 미결이 아니다")
sh = (Path(flow.__file__).parent.parent / "scripts" / "drift.sh").read_text(encoding="utf-8")
ok("drift.sh open" in sh, "drift.sh open 이 문서에 있다")
ok("열린 것 {len(" in sh, "status 에도 개수가 뜬다")

print()
print("[연결] **따로 있던 둘을 잇는다 -- 세계는 넓어지기만 하는 것이 아니라 접힌다**")
print("      ← 오일러가 한 것은 지수를 정교하게 만든 것이 아니라, 따로 자라던 셋이")
print("        실은 한 식이라는 것을 보인 것이다.")
from novel import bridge                                              # noqa: E402
BL = flow.blank()["ledger"]
for _i, (_b, _k) in enumerate([("places", "웅포"), ("objects", "지포 라이터"),
                               ("people", "우체부"), ("places", "소금 공장"),
                               ("facts", "형의 사고"), ("objects", "무전기"),
                               ("people", "한나")]):
    flow._merge(BL, {_b: {_k: {"직업": "x"} if _b == "people" else "x"}}, at=_i)
_d = bridge.draw(BL, "s", 0)
ok(_d["a"] and _d["b"] and _d["a"] != _d["b"], f"둘을 고른다 ({_d['a']} + {_d['b']})")
_dup = sum(bridge.draw(BL, "s", i)["a"] == bridge.draw(BL, "s", i + 1)["a"]
           for i in range(100))
ok(_dup == 0, f"한쪽에 같은 것이 계속 서지 않는다 ({_dup}건)")
_bb = bridge.brief(_d)
ok("앞에 쓴 것을 뒤집지 마라" in _bb,
   "이으면서 뒤집지 않는다  ← 보존적 확장. 뒤집으면 다리가 아니라 다른 이야기다")
ok("이것으로 문제를 풀지 마라" in _bb,
   "다리가 문제를 풀지 않는다  ← '알고 보니 열쇠를 갖고 있었다' 는 편의주의다")
ok("이미 읽은 것을 다시 읽게 된다" in _bb, "새 정보가 아니라 앞의 재독이 목적이다")
_thin = flow.blank()
_thin["chunks"] = ["x"]
ok("[연결]" not in flow.write_prompt(_thin),
   "원장이 얇으면 안 잇는다  ← 셋으로 다리를 놓으면 그냥 우연이다")
_thick = flow.blank()
_thick["ledger"] = BL
_hits = sum("[연결]" in flow.write_prompt(dict(_thick, chunks=["x"] * i))
            for i in range(1, 101))
ok(15 < _hits < 45, f"셋에 하나쯤만 잇는다 ({_hits}/100)  ← 다 연결되면 음모론이 된다")

print()
print("[예외] **통칙을 깨는 것과 사실을 뒤집는 것은 다른 물건이다**")
_r = flow.blank()
flow._merge(_r["ledger"], {"rules": {"겨울 출항": "겨울엔 배를 안 띄운다"}}, at=0)
_ep = ""
for _i in range(1, 12):
    _r["chunks"] = ["x"] * _i
    _p = flow.write_prompt(_r)
    if "[예외]" in _p:
        _ep = _p[_p.index("[예외]"):]
        break
ok(_ep, "통칙이 있으면 언젠가 예외가 걸린다")
ok("규칙은 지워지지 않는다" in _ep, "규칙은 남는다  ← 예외가 규칙을 정교하게 만든다")
ok("이건 모순이 아니다" in _ep,
   "예외는 모순이 아니다  ← 나이나 생사가 바뀌는 것은 여전히 기각이다")
ok("[예외]" not in flow.write_prompt(flow.blank()), "통칙이 없으면 안 실린다")

print()
print("[압축] **통칙 하나가 낱낱의 사실을 갈음한다 -- 정리는 공리를 지우지 않는다**")
_c = flow.blank()["ledger"]
for _i, _k in enumerate(["안 띄운 날1", "안 띄운 날2", "안 띄운 날3"]):
    flow._merge(_c, {"facts": {_k: "그날도 안 띄웠다"}}, at=_i)
_was = len(flow.brief(_c, now=3))
flow._merge(_c, {"rules": {"겨울 출항": "겨울엔 배를 안 띄운다"},
                 "folded": ["안 띄운 날1", "안 띄운 날2", "안 띄운 날3"]}, at=3)
_now = flow.brief(_c, now=3)
ok(len(_now) < _was, f"브리핑이 실제로 줄어든다 ({_was}자 → {len(_now)}자)")
ok("[통칙]" in _now, "통칙이 대신 실린다")
ok(len(_c["facts"]) == 3, "원장에는 그대로 남는다  ← 눈앞에서 치우는 것이지 지우는 것이 아니다")
ok("folded" in flow.extract_prompt("x") and "rules" in flow.extract_prompt("x"),
   "추출기가 통칙과 갈음을 뽑는다")

print()
print("[보조정리] **언급은 회수가 아니다. 쓰여야 회수다**")
_names = ["지포 라이터", "웅포", "무전기"]
ok(F.tooled("지포 라이터가 거기 있었다. 웅포는 조용했다.", _names) == [],
   "다시 부르기만 한 것은 안 센다")
ok(set(F.tooled("그는 지포 라이터로 실을 지졌다. 무전기를 들고 나갔다.", _names))
   == {"지포 라이터", "무전기"}, "수단이 된 것을 센다")
_bf = {"objects": {n: "x" for n in _names}, "facts": {"형의 사고": "x"}}
_msg = F.check("지포 라이터가 있었다. 웅포도 무전기도 그대로였다. 형의 사고도.",
               _bf, _bf)
ok(any("쓰지는 않았다" in c for c in _msg), "만지기만 하고 안 썼으면 짚는다")

print()
print("[죽음] **죽음은 모순이 아니라 사건이다**")
print("      ← 살아 있던 사람이 죽는 것은 이야기가 나아간 것이고,")
print("        죽은 사람이 걸어 들어오는 것만 세계가 무너진 것이다. 시간은 한 방향이다.")
_L = flow.blank()["ledger"]
_L["people"]["재현"] = {"나이": "42", "직업": "형사", "말투": "짧다",
                       "생사": "살아 있다", "_seen": 5}
ok(not flow._merge(_L, {"people": {"재현": {"생사": "죽었다"}}}, at=3),
   "주요 인물이 죽는 것은 통과한다  ← 이걸 막으면 주인공을 못 죽인다")
ok(_L["people"]["재현"]["생사"] == "죽었다", "원장이 죽음을 받아 적는다")
ok(flow._merge(_L, {"people": {"재현": {"생사": "살아 있다"}}}, at=4),
   "죽은 사람이 살아나는 것은 기각한다  ← 그것만은 되돌릴 수 없다")
_n = " ".join(style.narrator().split())
ok("주인공 같던 사람도 죽는다" in _n, "화자가 그것을 안다")
ok("복선은 뒤에서 보이는 것이지 앞에서 놓는 것이 아니다" in _n, "죽음에 예고를 안 단다")
ok("한 사람을 위해 돌아가는 세계는 세계가 아니라 무대다" in _n,
   "남은 사람이 이어받는다  ← 그때 세계가 진짜라는 것이 증명된다")

print()
print("[맥거핀] **미결과 반대다 -- 손대지 말라고 올려 주는 것**")
_m = flow.blank()
_m["chunks"] = ["x"]
ok("[맥거핀]" not in flow.write_prompt(_m), "없으면 안 실린다")
flow._merge(_m["ledger"], {"macguffin": {"소금 공장": "정체는 아무도 모른다"}}, at=0)
_mp = flow.write_prompt(_m)
ok("[맥거핀]" in _mp, "있으면 실린다")
ok("정체를 밝히지 마라" in _mp, "밝히지 말라고 한다  ← 밝혀지는 순간 동력이 꺼진다")
ok("사람마다" in _mp and "다르게 알고 있다" in _mp, "사람마다 다르게 안다")
ok("닫지 마라" in _mp, "열린 것에서 닫지 않는다  ← 미결과 반대로 취급한다")
ok("macguffin" in flow.extract_prompt("x") and "맥거핀이 둘이면" in flow.extract_prompt("x"),
   "추출기가 뽑되 하나만 둔다  ← 둘이면 둘 다 안 궁금해진다")

print()
print("[의심] **뒤집지 말고 흔들어라 -- 사실이 아니라 지반을 건드린다**")
print("      ← 평행선 공리를 부정해도 무모순인 세계가 있다는 것이 밝혀지면서 기하학은")
print("        하나가 아니게 됐다. 공리를 틀렸다고 한 것이 아니라 꼭 그래야 하는 것은")
print("        아니라고 한 것이다. 소설에서 그대로 하면 게이트와 부딪히므로 자리를 가른다.")
from novel import doubt                                               # noqa: E402
_DL = flow.blank()["ledger"]
for _i, (_b, _k) in enumerate([("places", "웅포"), ("objects", "소금 공장"),
                               ("people", "도영"), ("facts", "실종 사건")]):
    flow._merge(_DL, {_b: {_k: {"직업": "x"} if _b == "people" else "x"}}, at=_i)
_db = doubt.brief(doubt.draw(_DL, "s", 0))
ok("뒤집지 말고 흔들어라" in _db, "뒤집는 것과 흔드는 것을 가른다")
ok("사실은 그대로 둔다" in _db,
   "원장은 안 바뀐다  ← 사실을 뒤집는 것은 여전히 유일한 금지다")
ok("의심은 답이 아니라 상태다" in _db,
   "답을 주지 않는다  ← 답이 나오면 그건 의심이 아니라 반전이고, 반전은 한 번 쓰면 끝난다")
ok(all(("바꾼다" not in w and "틀렸다" not in w) for w in doubt.WAY),
   "흔드는 방식이 전부 지반 쪽이다  ← 사실을 건드리는 항목이 없다")
_thin2 = flow.blank()
_thin2["chunks"] = ["x"]
ok("[의심]" not in flow.write_prompt(_thin2), "흔들 것이 없으면 안 실린다")

print()
print("[시점] **누가 주인공인가는 사실이 아니라 믿음이다**")
_pb = doubt.pov_brief(doubt.POV[0])
ok("선언하지 마라" in _pb,
   "'사실 이 이야기의 주인공은' 을 안 쓴다  ← 분량과 시선이 옮겨가면 저절로 안다")
ok("원장은 한 글자도 안 바뀐다" in _pb, "시점을 흔들어도 게이트에 안 걸린다")
ok(any("자처하는 사람" in w for w in doubt.POV), "자기를 주인공으로 자처하는 사람이 목록에 있다")
ok("앞사람은 계속 거기 있고" in _pb, "옮겨도 버리지 않는다")
_pv = flow.blank()
_pv["chunks"] = ["x"]
ok("[시점]" not in flow.write_prompt(_pv), "초반에는 안 흔든다  ← 믿음이 서기 전에는 흔들 것이 없다")

print()
print("[정밀] **없는 것일수록 자세해야 진짜가 된다**")
_sn2 = " ".join(style.narrator().split())
ok("[정밀]" in style.narrator(), "정밀 항목이 있다")
for _w in ("이름", "수", "절차"):
    ok(f"**{_w}** --" in _sn2, f"셋 중 하나: {_w}")
ok("어중간한 수가 세다" in _sn2, "어림수보다 어중간한 수  ← 열일곱 개")
ok("라벨을 붙이는 것이 아니다" in _sn2,
   "라벨 쌓기와 가른다  ← 앞서 '1982년형 볼보' 가 아홉 번 나왔던 실측과 부딪히면 안 된다")
ok("그 흐릿함이 오히려 진짜처럼" in _sn2, "확실하지 않다고 써도 된다")

print()
if fails:
    print(f"미결: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("미결: 원장 · 열고 닫기 · 프롬프트 · 자 · 추출 -- 통과")
