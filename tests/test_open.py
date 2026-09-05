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

from novel import diffusion as F, flow                                # noqa: E402

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
if fails:
    print(f"미결: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("미결: 원장 · 열고 닫기 · 프롬프트 · 자 · 추출 -- 통과")
