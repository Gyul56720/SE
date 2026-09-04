"""충격 -- **점층을 끊고 제3자가 들이닥친다.**

확산만 돌리면 이야기는 한 방향으로 계속 짙어진다. 짙어지는 건 좋은데 짙어지기만 하면
프롬프트가 원장으로 차고(기술적 한계), 인물들이 같은 방에서 같은 이야기를 점점 자세히
하게 된다(서사적 정체). 사용자 평: "충격적인 사건이 많지 않아. 프롬포트가 터질 것
같거나, 일정 한도를 넘어가면, 점층을 하지 말고 충격적인 사건을 넣어."

**사건은 한 덩어리만 대신한다. 그 다음부터는 다시 점층이다.**

실행: python3 tests/test_shock.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import flow, shock as SH, style                            # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


print("[뽑기] **목록 하나를 돌려 쓰면 세 번째부터 예측된다** -- 축을 갈라 조합한다")
combos = len(SH.WHO) * len(SH.HOW) * len(SH.MARK) * len(SH.SCALE) * len(SH.TONE)
ok(combos > 1_000_000, f"조합이 백만 가지를 넘는다 ({combos:,})")
ok(SH.draw("a", 0) == SH.draw("a", 0), "같은 씨앗·같은 번호는 같은 사건  ← 이어 쓰기 재현")
ok(SH.draw("a", 0) != SH.draw("b", 0), "씨앗이 다르면 다른 사건")

print()
print("[뽑기] **연달아 같은 톤이면 신선함이 죽는다**")
print("      ← 처음엔 축 다섯을 한 난수원에서 연달아 뽑았더니 0~3번 온도가 넷 다 같았다.")
for axis in ("who", "how", "mark", "scale", "tone"):
    dup = sum(SH.draw("s", i)[axis] == SH.draw("s", i + 1)[axis] for i in range(200))
    ok(dup == 0, f"{axis}: 연속으로 같은 값이 나오지 않는다 ({dup}건)")
spread = Counter(SH.draw("s", i)["tone"] for i in range(400))
ok(len(spread) == len(SH.TONE), f"온도가 한쪽으로 쏠리지 않는다 ({len(spread)}/{len(SH.TONE)}종)")

print()
print("[때] **분량이 찼거나, 프롬프트가 부풀었거나**")
ok(SH.due(SH.EVERY, 0), "약 2,000자를 쓰면 터진다")
ok(not SH.due(SH.EVERY - 1, 0), "그 전에는 안 터진다")
ok(SH.due(0, SH.PRESSURE), "원장이 부풀면 자릿수를 안 채웠어도 터진다  ← 터지기 전에 환기")

print()
print("[개입] **사건은 확산을 한 덩어리만 대신한다**")
src = Path(flow.__file__).read_text(encoding="utf-8")
ok("다음 덩어리부터는 **다시 점층이다.**" in src, "사건 뒤에는 다시 점층이라고 못박는다")
ok("사건 덩어리는 확산으로 재지 않는다" in src,
   "사건 덩어리는 확산 자로 재지 않는다  ← 넓히라고 시키지 않았으니 그것으로 벌하지 않는다")
ok("리듬만 본다" in src, "리듬은 사건이든 아니든 지킨다  ← 대사와 길이는 늘 지켜야 한다")

bk = flow.blank("첫 문장.")
bk["chunks"] = ["x" * 2500]
bk["since"] = 2500
bk["_shock"] = SH.draw("첫 문장.", 0)
p = flow.write_prompt(bk)
ok("[사건]" in p, "사건 차례에는 사건 지시가 실린다")
ok("[확산]" not in p, "그 덩어리에는 확산 지시가 빠진다  ← 둘을 한꺼번에 시키지 않는다")
ok("문제를 풀어주지 않는다" in p,
   "사건이 문제를 풀지 않는다  ← 딱 맞춰 나타나 구해주는 것은 편의주의다")
ok("환기해라" in p, "사건 뒤에 공간이 바뀌어 있게 한다")

bk["_shock"] = None
ok("[확산]" in flow.write_prompt(bk), "사건이 아닌 덩어리에는 확산이 돌아온다")

print()
print("[셈] **사건이 터지면 분량을 0부터 다시 센다**")
b2 = flow.blank("첫 문장.")
b2["chunks"] = ["앞 덩어리"]
b2["since"] = 2500
b2["_shock"] = SH.draw("x", 0)
flow._after(b2, "사건 본문")
ok(b2["shocks"] == 1 and b2["since"] == 0, "사건 뒤 계수가 오르고 분량이 초기화된다")
flow._after(b2, "그 다음 덩어리")
ok(b2["shocks"] == 1 and b2["since"] == len("그 다음 덩어리"),
   "그 다음 덩어리는 다시 쌓기 시작한다")
ok(flow.blank()["shocks"] == 0 and "since" in flow.blank(),
   "새 원고는 사건 0에서 시작한다")

print()
print("[급발진] **인물이 스스로 저지르는 것** -- 사건과 다른 물건이다")
print("      ← 사건은 밖에서 들이닥쳐 점층을 끊는다. 급발진은 흐름 안에서 한 번 튄다.")
combo = len(SH.ACT) * len(SH.REACT) * len(SH.CALM)
ok(combo > 5000, f"저지름 × 반응 × 유유자적 조합 ({combo:,}가지)")
ok(SH.impulse("a", 0) == SH.impulse("a", 0), "같은 씨앗·번호는 같은 급발진  ← 이어 쓰기 재현")
dup = sum(SH.impulse("s", i)["act"] == SH.impulse("s", i + 1)["act"] for i in range(200))
ok(dup == 0, f"연달아 같은 짓을 하지 않는다 ({dup}건)")
ok("calm" in SH.impulse("a", 0), "저지른 뒤의 태연함까지 뽑는다")
dupc = sum(SH.impulse("s", i)["calm"] == SH.impulse("s", i + 1)["calm"] for i in range(200))
ok(dupc == 0, f"태연함도 연달아 같지 않다 ({dupc}건)")

brief = SH.impulse_brief(SH.impulse("a", 0))
ok("주인공의 성격이다" in brief,
   "급발진은 사건이 아니라 사람이다  ← 뽑기로 굴리는 돌발이 아니라 기본값이다")
ok("본인은 그게 급발진인 줄 모른다" in brief,
   "본인만 모른다  ← 그 간극이 이 인물의 전부다")
ok("저지름보다 그 뒤의 태연함이 이 인물이다" in brief, "유유자적이 정체다")
ok("장례식에서도" in brief,
   "분위기를 가리지 않는다  ← 웃기려고 넣는 것이 아니라 그런 사람이라서다")
ok("없는 말을 태연히" in brief,
   "지어낸 말이 급발진의 일부로 들어왔다  ← 변명하는 꼴이 딱 급발진 이후 유유자적이다")
ok("문제를 풀지 않는다" in brief,
   "급발진도 문제를 풀지 않는다  ← 앞서 정한 편의주의 금지를 그대로 지킨다")
ok("설명하지 마라" in brief, "왜 그랬는지 정리해 주지 않는다  ← 설명하면 재미가 죽는다")
ok("그 사람 카드에" in brief, "인물 카드에 맞게 비튼다  ← 같은 짓도 사람마다 다르다")
ok("하던 이야기를 이어 간다" in brief, "반응이 끝나면 확산으로 돌아간다")

bk3 = flow.blank()
bk3["chunks"] = ["앞 덩어리."]
bk3["drift"] = 1.0          # 여기서 보는 것은 **내용**이다. 빈도는 아래에서 따로 본다.
p3 = flow.write_prompt(bk3)
ok("급발진 하나" in p3, "확산 덩어리에 급발진이 실린다  ← 확산을 대신하지 않고 그 안에 든다")
bk3["_shock"] = SH.draw("x", 0)
ok("급발진 하나" not in flow.write_prompt(bk3),
   "사건 덩어리에는 안 실린다  ← 큰 것과 작은 것을 한꺼번에 시키지 않는다")

print()
print("[잡소리] **개그는 칸이 아니라 자리다**")
print("      ← 매 덩어리마다 다 하려 들면 그게 버릇이 되고, 버릇이 되면 안 웃긴다.")
flat3 = " ".join(p3.split())
ok("[잡소리]" in p3, "쓸데없는 말을 한 자리에 모았다")
ok("하나쯤**만 골라라. 안 골라도 된다" in flat3, "하나쯤, 안 해도 된다")
ok("없는 낱말을 만들고 변명을 단다" not in flat3,
   "지어낸 낱말은 [잡소리] 가 아니라 급발진 쪽에 있다  ← 그건 개그의 한 수가 아니라"
   " 이 인물의 몸짓이다")
ok("멍청한 소리를 아주 진지하게 한다" in flat3, "멍청하면서 진지한 수도 목록에 있다")
_sn = " ".join(style.narrator().split())
ok("매번 하지는 마라" in _sn, "화자에게도 매번 하지 말라고 한다  ← 두 자리가 어긋나면 안 된다")
ok("급발진이 이 사람의 기본값이다" in _sn, "화자가 주인공 성격으로 안다")
ok("같은 몸짓" in _sn, "지어낸 말과 급발진을 한 벌로 묶는다")

print()
print("[소재] **무엇이 나오는가도 뽑아서 준다**")
print("      ← 확산·리듬은 '어떻게' 다. '무엇' 을 안 주면 모델은 늘 술집·부두·낡은 차를 낸다.")
from novel import matter                                              # noqa: E402
mcombo = len(matter.GENRE) * len(matter.MEDIUM) * len(matter.HEAT)
ok(mcombo > 10000, f"갈래 × 매체 × 온도 ({mcombo:,}가지)")
for axis in ("genre", "medium", "heat"):
    d = sum(matter.draw("s", i)[axis] == matter.draw("s", i + 1)[axis] for i in range(200))
    ok(d == 0, f"{axis}: 연달아 같은 재료가 아니다 ({d}건)")
mb = matter.brief(matter.draw("a", 0))
ok("섞되 갈아타지 마라" in mb,
   "소재가 장르를 바꾸지 않는다  ← 던전이 나온다고 던전물이 되지 않는다")
ok("본문에 실물로" in mb, "편지는 통째로, 노래는 가사 두 줄로  ← '읽었다' 로 넘기지 않는다")
ok("문제를 풀지 않는다" in mb, "지도가 나왔다고 길을 찾게 되지 않는다")
ok("[소재]" in p3, "확산 덩어리에 실린다")
ok("[소재]" not in flow.write_prompt(bk3), "사건 덩어리에는 안 실린다")

print()
print("[사건] **셋에 하나쯤은 주인공이 불러온다**")
print("      ← 급발진이 기본값인데 사건이 늘 밖에서만 오면 두 축이 따로 논다.")
mine = [SH.draw("s", i)["mine"] for i in range(120)]
ok(0 < sum(mine) < len(mine), f"밖에서 오는 것과 섞인다 ({sum(mine)}/120)")
own = SH.brief(SH.draw("s", mine.index(True)))
ok("주인공이 불러온다" in own, "급발진이 사건으로 번진다")
ok("본인은 왜 이렇게 됐는지 모른다" in own, "그러고도 본인은 모른다")
ok("제3자가 개입한다" in SH.brief(SH.draw("s", mine.index(False))), "나머지는 밖에서 온다")
ok(any("시비를 건다" in a for a in SH.ACT), "길 가는 사람에게 시비도 목록에 있다")
ok(any("추파" in a for a in SH.ACT), "추파도 목록에 있다")

print()
print("[병맛] **언어적인 것과 행위적인 것이 둘 다 있어야 한다**")
print("      ← 미스터 빈이 웃긴 건 대사 때문이 아니다. 처음엔 언어 쪽만 있었다.")
BODY = ("지하철 바닥에 눕는다", "에스컬레이터를 거꾸로", "회전문을 한 바퀴 더",
        "우산을 안 펴고", "문을 잡아 준다. 아무도 안 온다",
        "지도를 거꾸로 들고", "남의 우산 속으로")
for b in BODY:
    ok(any(b in a for a in SH.ACT), f"몸으로 하는 것: {b}")
ok(len(SH.ACT) > 55, f"행동이 충분히 많다 ({len(SH.ACT)}개)")
ok("몸으로 하는 것이 반씩이다" in SH.impulse_brief(SH.impulse("a", 0)),
   "몸으로 하는 짓은 대사로 때우지 말라고 한다  ← 동작이 실제로 일어나야 한다")

print()
print("[계수] **부조리의 세기를 하나로 조인다**")
print("      ← 축을 넷이나 겹쳐 놓으니 뒤로 갈수록 쌓였다. 계수로 셋을 함께 줄인다.")
# 0.8 → 0.5. 초반이 좋았던 이유는 쌓인 것이 없어서다 -- 그 밀도를 끝까지 가려면
# 매 덩어리에 얹는 양을 줄여야 한다.
ok(flow.DRIFT == 0.5, f"기본 계수 0.5 ({flow.DRIFT})")
ok(flow.blank()["drift"] == flow.DRIFT, "새 원고에 계수가 저장된다  ← 이어 써도 같게")


print()
print("[흔들림] **계수를 고정하면 매 덩어리가 똑같이 반쯤 시끄럽다**")
print("      ← 균일한 0.5 는 균일한 1.0 만큼이나 단조롭다. 덩어리마다 다시 뽑는다.")
for base in (0.5, 0.8, 0.3):
    lv = [matter.level_at("s", i, base) for i in range(3000)]
    avg = sum(lv) / len(lv)
    ok(abs(avg - base) < 0.02, f"기준 {base}: 평균이 기준과 같다 ({avg:.3f})")
    # 폭은 [2b-1, 2b] 를 0~1 로 자른 것이라 기준이 0.5 에서 멀어질수록 좁아진다
    # (0.5 → 1.0 · 0.8 과 0.3 → 0.4). 그래도 절반 이상 흔들려야 구간이 생긴다.
    width = max(lv) - min(lv)
    ok(width >= 0.39, f"기준 {base}: 폭이 벌어진다 ({min(lv):.2f}~{max(lv):.2f})")
lo5 = [matter.level_at("s", i, 0.5) for i in range(3000)]
ok(min(lo5) < 0.1 and max(lo5) > 0.9,
   "기준 0.5 는 아주 조용한 덩어리와 아주 요란한 덩어리를 둘 다 낸다")
lo8 = [matter.level_at("s", i, 0.8) for i in range(3000)]
ok(min(lo8) >= 0.55,
   "기준을 높이면 아주 조용해지지는 않는다  ← 0~1 로 자른 구간이라 그렇다")
ok(matter.level_at("s", 7, 0.5) == matter.level_at("s", 7, 0.5),
   "같은 자리는 같은 세기  ← 이어 쓰기에도 재현된다")
ok(len({round(matter.level_at("s", i, 0.5), 2) for i in range(20)}) > 12,
   "이웃한 덩어리끼리 세기가 다르다")
ok("이번 세기" in Path(flow.__file__).read_text(encoding="utf-8"),
   "로그에 이번 덩어리의 세기가 찍힌다  ← 왜 조용한지 밖에서 보여야 한다")


def _fires(level, n=200):
    bk = flow.blank()
    bk["drift"] = level
    hit = 0
    for i in range(1, n + 1):
        bk["chunks"] = ["x"] * i
        if "급발진 하나" in flow.write_prompt(bk):
            hit += 1
    return hit


full, less, half = _fires(1.0), _fires(0.8), _fires(0.5)
ok(full == 200, f"계수 1.0 이면 매 덩어리 ({full}/200)")
ok(140 < less < 195, f"계수 0.8 이면 다섯에 넷쯤 ({less}/200)")
ok(70 < half < 130, f"계수 0.5 면 절반쯤 -- 지금의 기본값 ({half}/200)")
ok(half < less < full, "기준을 올리면 잦아진다  ← 흔들려도 기준은 지켜진다")

bk4 = flow.blank(); bk4["drift"] = 0.5; bk4["chunks"] = ["x"] * 3
off = flow.write_prompt(bk4)
if "급발진 하나" not in off:
    ok("사람이 바뀌는 것은 아니다" in off,
       "꺼진 덩어리에서도 성격은 그대로다  ← 저지르지 않을 뿐이다")

ok(SH.due(2000, 0, 1.0) and not SH.due(2000, 0, 0.8),
   "계수가 낮으면 사건 간격이 벌어진다 (0.8 이면 2,500자)")
ok(SH.due(0, SH.PRESSURE, 0.5),
   "원장이 부푼 것은 계수와 무관하다  ← 취향이 아니라 프롬프트가 무거워지는 한계다")

lv_on = sum(bool(matter.draw("s", i, 0.8)["genre"]) for i in range(200))
ok(150 < lv_on < 190, f"갈래도 같은 비율로 빠진다 ({lv_on}/200)")
ok("장르를 섞지 마라" in matter.brief({"genre": "", "medium": "편지", "heat": "웃기게"}),
   "갈래가 빠진 덩어리는 그냥 일상이다  ← 매체와 온도는 그대로 들어간다")

print()
if fails:
    print(f"충격: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("충격: 조합 · 연속 회피 · 때 · 확산 교대 · 셈 -- 통과")
