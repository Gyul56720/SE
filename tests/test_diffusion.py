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
         # '양조장' → '양조장 뒤편 창고' -- 이름이 자란 것이 점층의 자국이다
         "places": {"양조장": "x", "등대": "a", "양조장 뒤편 창고": "b"},
         "objects": {"지포 라이터": "은색", "무전기": "b"},
         "facts": {"오로라": "z", "1978년 화재": "c"}, "time": []}

THIN = "설명만 이어지는 글이다. 아무 일도 일어나지 않는다.\n" * 6
THICK = "\n".join([
    # 앞엣것 하나는 **수단**이 되어야 한다 -- 언급은 회수가 아니다.
    "요우는 지포 라이터로 젖은 심지를 몇 번 지지다가 등대 난간에 올려놓았다.",
    '"그거 아버지 거였죠?"',
    '"몰라."',
    '"그게 말이죠, 화재 때 등대지기가 무전기를 하나 주웠다는데, 그 사람이 우리 '
    '외삼촌이고, 그때부터 이 동네 사람들은 라이터를 안 켜요. 미신이죠 뭐."',
    '"미신이라뇨. 나는 그날 밤에 거기 있었고, 등이 꺼지는 것도 봤고, 그 뒤로 사흘 동안 '
    '배가 한 척도 안 들어온 것도 봤습니다. 그게 미신입니까."',
    '"그래서요."',
    '"그래서라뇨."',
    '"아니 그러니까 내 말은, 그날 밤에 뭘 봤냐고 묻는 거잖아요."',
    '"봤죠."',
    '"뭘요."',
    # 아주 긴 대사 하나. 한 사람이 자기 얘기에 빠져 있는 대목이 없으면 자에 걸린다.
    '"그게 말입니다, 등이 꺼지고 나서 한 삼십 분쯤 아무것도 안 보였는데, 그때 물소리가 '
    '평소랑 달랐어요. 아니 물소리가 아니라 물이 없는 소리였나. 아무튼 나는 그 소리를 '
    '지금도 가끔 듣습니다. 우리 형이 죽던 해 겨울에도 그 소리가 났었고요."',
])

print("[자] **넓히기와 깊게 하기를 함께 센다**")
print("      ← 새것만 있으면 산만해지고, 되돌아온 것만 있으면 제자리를 돈다.")
m = F.measure(THICK, BEFORE, AFTER)
ok(m["new"] == 5, f"세계에 새로 놓인 것을 센다 ({m['new']})")
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
ok("분량은 줄이지 마라" in src, "되먹임이 몸을 사리게 하지 않는다")
ok("**이것 하나만** 고쳐라" in src,
   "한 번에 한 건만 시킨다  ← 네 건을 한꺼번에 주자 짧은 '-다' 가 64% -> 67% 로 올라갔다")
ok("같은 밀도로 그대로 가라" in src,
   "모순으로 기각됐을 때도 밀도를 지키라고 한다  ← 기각당한 모델은 얕게 쓴다")
ok(flow.MAX_REWRITE >= 3, "재는 자가 늘었으니 다시 쓰는 예산도 늘렸다")
ok(flow.TAIL >= 1200, "꼬리를 늘려 점층이 매번 새로 시작하지 않게 한다")

ok(len(F.grown(BEFORE, AFTER)) >= 1,
   "앞엣것에서 자라난 이름을 센다  ← 웅포 → 웅포 소금 공장")
ok(F.measure(THICK, BEFORE, AFTER)["rally"] >= 4,
   "주고받는 턴을 센다  ← 대사가 흩어져 있으면 대화가 아니라 인용이다")

print()
print("[역행] **회수는 가까운 과거를 향해야 한다**")
print("      ← 실측: 새로 쓴 글이 첫 문장으로 되돌아갔다. 첫 장면의 물건은 한번 원장에")
print("        오르면 영원히 '최근 글에 없는 것' 이라, 매번 '다시 만질 것' 으로 올라갔다.")
aged = flow.blank()["ledger"]
flow._merge(aged, {"places": {"함부르크 공항": "비가 온다"},
                   "objects": {"보잉 747": "큰 것"}}, at=0)
flow._merge(aged, {"objects": {"지포 라이터": "은색"}}, at=9)
ok("_age" in aged and aged["_age"]["함부르크 공항"] == 0, "언제 놓였는지 적어 둔다")
ok("함부르크 공항" in F.cold(aged, "", 0), "갓 놓인 것은 연료다")
old_fuel = F.cold(aged, "", 10)
ok("함부르크 공항" not in old_fuel,
   f"오래된 것은 연료에서 빠진다  ← 마흔 덩어리 전 공항으로 가는 것은 점층이 아니라 역행이다")
ok("지포 라이터" in old_fuel, "가까운 과거는 그대로 연료다  ← 세 덩어리 전 라이터는 점층이다")
ok(F.cold({"objects": {"오래된 것": "x"}}, "", 99) == ["오래된 것"],
   "나이를 모르는 옛 원고는 나이를 안 따진다  ← 잴 수 없는 것을 있는 척하지 않는다")

_go = flow.blank(); _go["chunks"] = ["…문을 닫았다."]
_p = flow.write_prompt(_go)
ok("이 마지막 문장 다음 순간부터 써라" in _p, "가장 최근 문장이 출발점이라고 말한다")
ok("시간은 앞으로만 간다" in _p, "앞 장면으로 돌아가지 말라고 한다")
ok("다시 쓸 수 있는 재료**이지 다시 갈 장소가 아니다" in _p,
   "원장을 재료와 장소로 갈라 말한다  ← 회수를 '거기로 가라' 로 읽으면 역행한다")
ok("시간은 앞으로만 간다" not in flow.write_prompt(flow.blank()),
   "첫 덩어리에는 안 붙는다  ← 돌아갈 앞이 없다")

print()
print("[호명] **사람은 부르라고 있는 이름이다**")
print("      ← 상한 2회는 소품을 겨냥한 것이었는데 인물과 무대에도 걸렸다. 1,400자 안에서")
print("        주인공을 두 번만 부르는 것은 한국어로 불가능하다. 실측 2026-09-05:")
print("        '도영 5회 · 웅포 4회' 로 기각되어 매 덩어리가 재시도를 다 썼고,")
print("        호출과 토큰이 네 배가 되어 429 를 불렀다.")
_led = {"people": {"도영": {}, "재현": {}}, "places": {"웅포": "x"},
        "objects": {"무전기": "x"}}
_names = F.props(_led)
_normal = ("도영이 웃었다. " * 5) + ("웅포 얘기였다. " * 4) + ("무전기가 울렸다. " * 4) + "가" * 1200
ok(F.overused(_normal, _names, _led) == [],
   "보통 밀도의 1,400자는 통과한다  ← 이게 안 되면 원고가 안 나온다")
ok(F.overused(("도영이 웃었다. " * 12) + "가" * 1200, _names, _led),
   "그래도 과하면 잡는다")
ok(F.PEOPLE_ECHO > F.ECHO_MAX and F.PLACE_ECHO > F.ECHO_MAX,
   "사람·장소는 소품보다 상한이 높다")
_short = "도영. 도영. 도영. 도영. 도영. 도영. 도영."
_long = _short + "가" * 3000
ok(len(F.overused(_long, _names, _led)) <= len(F.overused(_short, _names, _led)),
   "긴 덩어리는 상한이 늘어난다  ← 3,000자에 2회는 억지다")

print()
if fails:
    print(f"확산: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("확산: 넓힘·회수 · 대사 분포 · 식은 소품 · 프롬프트 일치 · 소프트 개입 -- 통과")
