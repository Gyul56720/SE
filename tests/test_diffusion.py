"""확산 -- **이야기는 뒤로 갈수록 짙어져야 한다.**

실측 2026-09-04 평: "이야기가 갈 수록 농도가 얕아져. 이전에 나왔던 소품들이 계속
점층되야해. 대사도 스토리의 일부야."

원인은 구조에 있었다. 다음 덩어리에게 넘어가는 것은 꼬리 900자뿐이라 세 덩어리 앞의
소품이 창 밖으로 빠졌고, 원장은 프롬프트에서 **금지 목록**으로만 쓰였다. 세계가 자산이
아니라 제약이었으니 모델은 매번 새 방에서 새로 시작했다.

실행: python3 tests/test_diffusion.py
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


BEFORE = {"people": {"요우": {}}, "places": {"양조장": "x"},
          "objects": {"지포 라이터": "은색"}, "facts": {"오로라": "z"}, "time": []}
AFTER = {"people": {"요우": {}, "한나": {}},
         "places": {"양조장": "x", "등대": "a"},
         "objects": {"지포 라이터": "은색", "무전기": "b"},
         "facts": {"오로라": "z", "1978년 화재": "c"}, "time": []}

THIN = "설명만 이어지는 글이다. 아무 일도 일어나지 않는다.\n" * 6
THICK = "\n".join([
    "요우는 지포 라이터를 등대 난간에 올려놓았다.",
    '"그거 아버지 거였죠?"',
    '"몰라."',
    '"그게 말이죠, 1978년 화재 때 등대지기가 무전기를 하나 주웠다는데, 그 사람이 우리 '
    '외삼촌이고, 그때부터 이 동네 사람들은 라이터를 안 켜요. 미신이죠 뭐."',
])

print("[자] **넓히기와 깊게 하기를 함께 센다**")
print("      ← 새것만 있으면 산만해지고, 되돌아온 것만 있으면 제자리를 돈다.")
m = F.measure(THICK, BEFORE, AFTER)
ok(m["new"] == 4, f"세계에 새로 놓인 것을 센다 ({m['new']})")
ok(m["back"] >= 2, f"앞에서 나온 소품을 다시 만진 것을 센다 ({m['back']})")
ok(F.check(THICK, BEFORE, AFTER) == [], "넓히고 깊게 한 덩어리는 통과한다")

thin = F.check(THIN, BEFORE, BEFORE)
ok(len(thin) >= 3, f"설명만 있는 덩어리는 걸린다 ({len(thin)}건)")
ok(F.score(THIN, BEFORE, BEFORE) > F.score(THICK, BEFORE, AFTER), "점수로 농도를 가른다")

print()
print("[대사] **긴 것과 짧은 것이 둘 다 있어야 한다**")
short, long = F.talk(THICK)
ok(short >= 2, f"끊고 받아치는 짧은 대사 ({short})")
ok(long >= 1, f"길게 떠드는 대사 -- 소품의 유래가 여기서 나온다 ({long})")
ok(any("긴 대사" in c for c in thin), "긴 대사가 없으면 그것을 짚는다")
ok(any("설명으로 넘기지 마라" in c for c in thin), "설명으로 때우지 말라고 말한다")

print()
print("[연료] **원장은 금지 목록이 아니라 재료다**")
cold = F.cold(BEFORE, "요우는 양조장에 있었다.")
ok("지포 라이터" in cold and "등대" not in cold,
   "최근 글에 없는 것만 '식은 소품' 이다  ← 확산의 연료가 여기 있다")
ok("양조장" not in cold, "방금 쓴 것은 연료로 올리지 않는다")

print()
print("[프롬프트] 식은 소품을 이름으로 짚어 다시 올려주는가")
bk = flow.blank(flow.FIRST)
bk["chunks"] = ["요우는 양조장에 갔다."]
bk["ledger"]["objects"] = {"지포 라이터": "은색"}
bk["ledger"]["places"] = {"등대": "북쪽"}
p = flow.write_prompt(bk)
ok("[확산]" in p, "확산 항목이 실린다")
ok("지포 라이터" in p.split("[확산]")[1].split("[전환]")[0],
   "식은 소품을 이름으로 부른다  ← 꼬리 1,200자 밖으로 빠진 것이 여기서 돌아온다")
ok("한 단계 키운다" in p, "똑같이 쓰지 말고 키우라고 한다")
ok("연료다" in p, "원장을 금지 목록이 아니라 연료라고 부른다")
ok("외현에서 내현으로" in p, "전환을 매 덩어리에 요구한다")
ok("이상한 대화를 해라" in p, "용건만 오가는 대사를 막는다")
ok(f"{F.LIMITS['new']}개 이상" in p and f"{F.TALK_LONG}자" in p,
   "코드가 재는 숫자와 프롬프트의 숫자가 같다")

print()
print("[개입] **확산도 원고를 죽이지 않는다** -- '게이트 크게 걸지마'")
src = Path(flow.__file__).read_text(encoding="utf-8")
ok("제일 짙은 것을 채택한다" in src, "끝내 못 고치면 제일 짙은 후보를 쓴다")
ok("줄이지 말고 늘려라" in src, "되먹임이 몸을 사리게 하지 않는다")
ok("같은 밀도로 그대로 가라" in src,
   "모순으로 기각됐을 때도 밀도를 지키라고 한다  ← 기각당한 모델은 얕게 쓴다")
ok(flow.MAX_REWRITE >= 3, "재는 자가 늘었으니 다시 쓰는 예산도 늘렸다")
ok(flow.TAIL >= 1200, "꼬리를 늘려 점층이 매번 새로 시작하지 않게 한다")

print()
if fails:
    print(f"확산: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("확산: 넓힘·회수 · 대사 분포 · 식은 소품 · 프롬프트 일치 · 소프트 개입 -- 통과")
