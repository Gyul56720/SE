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
ok("한 방에 끝내지 마라" in p,
   "사건은 터지고 나서가 더 길다  ← 뒷자락에서 다음 이야기가 나온다")
ok("대사로 받아라" in p, "위트는 대사에서 나온다  ← 서술로 정리하면 시시해진다")

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
ok(brief.startswith("[급발진]"),
   "제 이름을 단 항목으로 선다  ← 글머리표로 두면 대사 규칙의 하위 항목처럼 읽힌다")
ok("주인공이 저지른다" in brief and "본인은 그게 급발진인 줄 모른다" in brief,
   "급발진은 사건이 아니라 사람이다  ← 뽑기로 굴리는 돌발이 아니라 기본값이다")

print()
print("[주체] **저지르는 것은 주인공만이 아니다**")
print("      ← 주인공 전용이면 세계가 주인공만 살아 있고 나머지는 반응만 하는 배경이 된다.")
from collections import Counter as _C                                 # noqa: E402
who = _C(SH.impulse("s", i)["who"] for i in range(600))
ok(len(who) == 3, f"주체가 셋으로 갈린다 ({dict(who)})")
ok(who["주인공"] > max(v for k, v in who.items() if k != "주인공"),
   "그래도 주인공이 제일 잦다  ← 이 사람의 기본값이라는 점은 변하지 않는다")
ok(sum(v for k, v in who.items() if k != "주인공") > 200,
   "남이 저지르는 몫이 충분하다")
other = SH.impulse_brief(SH.impulse("s", next(
    i for i in range(20) if SH.impulse("s", i)["who"] != "주인공")))
ok("이번엔" in other and "이 저지른다" in other, "남이 저지르는 판이 따로 있다")
ok("주인공은 당하는 쪽이고" in other,
   "그때 주인공은 반응한다  ← 자기가 저지른 일은 몰라도 남이 저지른 일에는 반응한다")
ok("본인은 그게 급발진인 줄 모른다" in brief,
   "본인만 모른다  ← 그 간극이 이 인물의 전부다")
ok("그 뒤의 태연함**이 그 사람이다" in brief, "유유자적이 정체다")
ok("장례식에서도" in brief,
   "분위기를 가리지 않는다  ← 웃기려고 넣는 것이 아니라 그런 사람이라서다")
ok("같은 몸짓" in " ".join(style.narrator().split()),
   "지어낸 말이 급발진의 일부로 들어왔다  ← 변명하는 꼴이 딱 급발진 이후 유유자적이다")
ok("편의주의다" in brief,
   "급발진도 문제를 풀지 않는다  ← 앞서 정한 편의주의 금지를 그대로 지킨다")
ok("설명하지 마라" in brief, "왜 그랬는지 정리해 주지 않는다  ← 설명하면 재미가 죽는다")
ok("그 사람 카드에" in brief, "인물 카드에 맞게 비튼다  ← 같은 짓도 사람마다 다르다")
ok("저지른 일이 다음 일을 부른다" in brief,
   "저지른 일이 다음 일을 부른다  ← 저지르고 아무 일도 안 일어나면 그건 장식이다")

bk3 = flow.blank()
bk3["chunks"] = ["앞 덩어리."]
bk3["drift"] = 1.0          # 여기서 보는 것은 **내용**이다. 빈도는 아래에서 따로 본다.
p3 = flow.write_prompt(bk3)
ok("[급발진]" in p3, "확산 덩어리에 급발진이 실린다  ← 확산을 대신하지 않고 그 안에 든다")
bk3["_shock"] = SH.draw("x", 0)
ok("[급발진]" not in flow.write_prompt(bk3),
   "사건 덩어리에는 안 실린다  ← 큰 것과 작은 것을 한꺼번에 시키지 않는다")

print()
print("[잡소리] **개그는 칸이 아니라 자리다**")
print("      ← 매 덩어리마다 다 하려 들면 그게 버릇이 되고, 버릇이 되면 안 웃긴다.")
flat3 = " ".join(p3.split())
ok("[잡소리]" in p3, "쓸데없는 말을 한 자리에 모았다")
ok("적어도 하나는 넣어라" in flat3 and "둘은 반드시, 셋까지" in flat3,
   "둘은 반드시, 셋까지  ← '헛소리가 너무 적다' 는 실측 뒤에 올렸다")
ok("없는 낱말을 만들고 변명을 단다" not in flat3,
   "지어낸 낱말은 [잡소리] 가 아니라 급발진 쪽에 있다  ← 그건 개그의 한 수가 아니라"
   " 이 인물의 몸짓이다")
ok("멍청한 소리를 아주 진지하게 한다" in flat3, "멍청하면서 진지한 수도 목록에 있다")
_sn = " ".join(style.narrator().split())
ok("매번 하지는 마라" in _sn, "화자에게도 매번 하지 말라고 한다  ← 두 자리가 어긋나면 안 된다")
# [주인공] 자체를 지웠다 -- 급발진 뽑기가 매 덩어리 인물을 주므로 화자 쪽에 또 적으면
# 두 자리가 어긋난다. 이제 인물 규정은 한 곳에만 있다.
ok("[주인공]" not in _sn,
   "화자 페르소나에 인물 규정이 없다  ← 뽑기가 주는 것을 또 적으면 어긋난다")
ok(len(SH.impulse("씨앗", 1)["swerve"]) >= 2,
   "인물은 **여러 축을 겹쳐서** 온다  ← 예를 박아 두면 매번 그리로 쏠린다")
_im = SH.impulse_brief(SH.impulse("씨앗", 1))
ok(_im.count("      - ") >= 2,
   "성질을 여럿 겹쳐 준다  ← 하나만 뽑으면 그 하나가 인물 전체를 설명해 버린다")
ok("그 어긋남이 입체다" in _im, "안 어울리는 것을 겹치라고 한다")
_hows = {len(SH.draw("씨앗", i)["hows"]) for i in range(5)}
ok(_hows == {SH.EVENT_K}, f"사건도 묶음으로 뽑는다 ({_hows})")
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
_on = flow.blank(); _on["chunks"] = ["앞."]; _on["drift"] = 1.0; _on["matter"] = 1.0
ok("[소재]" in flow.write_prompt(_on), "켜면 확산 덩어리에 실린다")
_on["_shock"] = SH.draw("x", 0)
ok("[소재]" not in flow.write_prompt(_on), "켜도 사건 덩어리에는 안 실린다")
_off = flow.blank(); _off["chunks"] = ["앞."]
ok("[소재]" not in flow.write_prompt(_off), "기본값에서는 안 실린다  ← 껐다")
# 소재는 이제 **곁들이 한 자리**를 다른 축들과 나눠 쓴다. 제 비율은 후보가 되는
# 문턱이고, 실제로 실리는 것은 그중 하나뿐이다.
_half = flow.blank(); _half["matter"] = 0.4; _half["drift"] = 1.0
hits = sum("[소재]" in flow.write_prompt(dict(_half, chunks=["x"] * i))
           for i in range(1, 201))
ok(0 < hits < 130, f"비율은 후보가 되는 문턱이다 (0.4 → 실제 {hits}/200)")
_off2 = flow.blank(); _off2["matter"] = 0.0
ok(not any("[소재]" in flow.write_prompt(dict(_off2, chunks=["x"] * i))
           for i in range(1, 51)), "0 이면 후보에도 안 든다")

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
ok("그 동작이 실제로 일어나야 한다" in SH.impulse_brief(SH.impulse("a", 0)),
   "몸으로 하는 짓은 대사로 때우지 말라고 한다  ← 동작이 실제로 일어나야 한다")

print()
print("[계수] **부조리의 세기를 하나로 조인다**")
print("      ← 축을 넷이나 겹쳐 놓으니 뒤로 갈수록 쌓였다. 계수로 셋을 함께 줄인다.")
# 0.8 → 0.5 로 내렸다가 1.0 으로 되돌렸다. 밀도를 올린 것은 계수가 아니라 소재 축이었다 --
# 급발진을 반으로 줄이니 밀도는 그대로인 채 인물만 밋밋해졌다.
ok(flow.DRIFT == 1.0, f"기본 계수 1.0 -- 급발진은 매 덩어리 ({flow.DRIFT})")
ok(flow.MATTER == 0.0, f"소재 축은 꺼져 있다 ({flow.MATTER})  ← 밀도를 올린 것이 이것이다")
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
        if "[급발진]" in flow.write_prompt(bk):
            hit += 1
    return hit


full, less, half = _fires(1.0), _fires(0.8), _fires(0.5)
ok(full == 200, f"계수 1.0 이면 매 덩어리 ({full}/200)")
ok(140 < less < 195, f"계수 0.8 이면 다섯에 넷쯤 ({less}/200)")
ok(70 < half < 130, f"계수 0.5 면 절반쯤 -- 지금의 기본값 ({half}/200)")
ok(half < less < full, "기준을 올리면 잦아진다  ← 흔들려도 기준은 지켜진다")

bk4 = flow.blank(); bk4["drift"] = 0.5; bk4["chunks"] = ["x"] * 3
off = flow.write_prompt(bk4)
if "[급발진]" not in off:
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
print("[연쇄] **저지르고 끝나면 장식이다 -- 판이 바뀌어야 이야기가 굴러간다**")
print("      ← 셋에 하나쯤 판이 바뀐다. 매번 바뀌면 이야기가 정신없어진다.")
lands = [SH.impulse("s", i)["land"] for i in range(300)]
ok(0 < sum(bool(x) for x in lands) < 200, f"셋에 하나쯤 옮긴다 ({sum(bool(x) for x in lands)}/300)")
ok(len({x for x in lands if x}) > 10, "가는 곳이 다양하다")
lb = SH.impulse_brief(SH.impulse("s", lands.index(next(x for x in lands if x))))
ok("사슬의 모양" in lb and "한 칸만\n      나아가면 된다" in lb.replace("**",""),
   "사슬을 한 칸씩 나아가게 한다  ← 한 덩어리에 다 하라는 것이 아니다")
ok("이름과 사정을 하나 줘라" in lb, "거기서 만난 사람이 다음 칸을 부른다")
ok("경찰서로 끌려간다" not in lb and "소세지" not in lb and "철학" not in lb,
   "구체적인 예시를 박아 두지 않는다  ← 예시를 하드코딩하면 내용이 다 그쪽으로 쏠린다")

print()
print("[욕망] **급발진은 욕망이 새어 나온 것이다**")
print("      ← 무엇을 원하는지가 정해지면 왜 하필 지금 저지르는지가 따라 나온다.")
ok(len(SH.URGE) >= 15, f"욕망이 충분히 갈린다 ({len(SH.URGE)}개)")
ok("urge" in SH.impulse("a", 0), "급발진에 욕망이 붙어 나온다")
ub = SH.impulse_brief(SH.impulse("a", 0))
ok("욕망이 먼저다" in ub, "욕망을 먼저 말한다")
ok("채워지거나 어긋난다" in ub,
   "그 자리에서 결판난다  ← 채워지면 카타르시스고 어긋나면 다음 급발진을 부른다")
ok("합창단" in ub, "반응이 사람마다 갈린다  ← 다 같이 놀라면 그건 사람이 아니다")

lits = [SH.impulse("s", i)["literal"] for i in range(400)]
ok(0 < sum(bool(x) for x in lits) < 160,
   f"말이 실제가 되는 것은 넷에 하나쯤 ({sum(bool(x) for x in lits)}/400)")
lb2 = SH.impulse_brief(SH.impulse("s", next(i for i in range(40) if SH.impulse("s", i)["literal"])))
ok("놀라면 판타지가 되고, 안 놀라면 아이러니가 된다" in lb2.replace("\n      ", " "),
   "아무도 크게 안 놀란다  ← 놀라는 순간 아이러니가 판타지로 떨어진다")

print()
print("[값] **프롬프트를 캐시 경계로 가른다**")
print("      ← 매 덩어리·매 재시도마다 통짜로 보내면 같은 문장을 수백 번 다시 산다.")
from novel import drive as _D                                         # noqa: E402
_pp = flow.write_prompt(dict(flow.blank(), chunks=["앞."] * 3))
_st, _sep, _vo = _pp.partition(_D.SPLIT)
ok(_sep, "경계가 있다")
ok(_pp.count(_D.SPLIT) == 1, "경계는 하나뿐이다")
ok(len(_st) > len(_vo), f"고정부가 더 크다 (고정 {len(_st):,} · 휘발 {len(_vo):,})")
ok(all(k in _st for k in ("건조한 번역투", "규칙:", "리얼리즘")),
   "매번 같은 것은 앞에  ← 문체·규칙은 원고 내내 안 변한다")
ok(all(k in _vo for k in ("[세계", "끝부분", "급발진")),
   "덩어리마다 바뀌는 것은 뒤에  ← 세계·꼬리·뽑기")

print()
print("[설정] **외현과 내현 -- 겉과 속을 한 벌로 붙인다**")
print("      ← 몸은 이 장치의 한 사례일 뿐이다. 인물을 남과 다르게 만드는 조건이라면")
print("        무엇이든 같은 자리에 들어간다. 겉만 있으면 인상이고, 속만 있으면 설명이다.")
from novel import trait                                               # noqa: E402
ok(len(trait.OUTER) >= 50, f"외현이 충분하다 ({len(trait.OUTER)}개)")
ok(len(trait.INNER) >= 30, f"내현도 충분하다 ({len(trait.INNER)}개)")
_t = trait.draw("a", 0)
ok(all(k in _t for k in ("outer", "inner")),
   "둘을 한 벌로 준다  ← 겉만 있으면 인상이고 속만 있으면 설명이다")
dupb = sum(trait.draw("s", i)["outer"] == trait.draw("s", i + 1)["outer"]
           for i in range(200))
ok(dupb == 0, f"연달아 같은 몸이 아니다 ({dupb}건)  ← 두 인물이 한 사람처럼 읽힌다")
bb = trait.brief(trait.draw("a", 0))
ok("불행으로 쓰지 마라" in bb,
   "조건을 불행으로 쓰지 않는다  ← 사연이 아니라 조건이다")
ok("이름을 붙이는 순간 진단서가 되고" in bb,
   "내현은 이름을 안 붙인다  ← 진단서는 인물이 아니다")
ok("겉은 보이고, 속은 새어 나온다" in bb, "둘의 규율이 다르다")
ok("출발점이다" in bb, "이것도 출발점이다  ← 표류가 먼저다")
ok("동정할 자리를 만들지 마라" in bb, "동정할 자리를 만들지 않는다")
ok("끝까지 그 사람의 것이다" in bb, "한 번 정해진 것은 안 바뀐다")
hits = sum("[설정]" in flow.write_prompt(dict(flow.blank(), chunks=["x"] * i))
           for i in range(1, 101))
# 설정도 곁들이 한 자리를 나눠 쓴다 -- 제 비율(0.35)은 후보가 되는 문턱이다.
ok(0 < hits < 40, f"곁들이로 돈다 ({hits}/100)  ← 매번 넣으면 인물 소개서가 된다")
ok("몸" in flow.CARD and "속" in flow.CARD, "카드에 몸 칸과 속 칸이 둘 다 있다")
ok("속 칸" in flow.extract_prompt("x") and "감정 이름이나 진단명은 쓰지 마라"
   in flow.extract_prompt("x"),
   "추출기가 속을 **행동으로** 적는다  ← 감정 이름을 적으면 그게 진단서다")

print()
print("[낯섦] **낯섦은 재료가 아니라 전개에서 나온다**")
print("      ← 한때 '시간이 한 시간 비어 있다', '문이 하나 더 생겨 있다' 를 넣었다가 뺐다.")
print("        설명 안 되는 것으로 사건을 만들면 그게 편의주의고, 그건 첫 번째 금지다.")
for w in ("옆자리에서 들려오는 남의 이야기", "잘못 온 우편물", "검사 결과", "해고 통보"):
    ok(w in SH.WHO, f"개입자는 있을 법한 것: {w}")
for h in ("옆자리 대화를 엿듣는다. 그 내용이 남 일이 아니다", "들킨다",
          "돈이 모자란 것이 그 자리에서 드러난다"):
    ok(h in SH.HOW, f"방식도 있을 법한 것: {h}")
for gone in ("시간이 한 시간 비어 있다", "문이 하나 더 생겨 있다", "글자가 안 읽힌다"):
    ok(gone not in SH.HOW, f"초자연은 뺐다: {gone}")
for gone in ("냄새", "빛", "숫자 하나"):
    ok(gone not in SH.WHO, f"초자연은 뺐다: {gone}")
ok("낯섦은 재료가 아니라 전개에서 나온다" in SH.brief(SH.draw("a", 0)),
   "평범한 재료가 예상 밖 순서로 이어질 때 낯설어진다고 말한다")
ok(any("말이 실제가 된다" in SH.impulse_brief(SH.impulse("s", i)) for i in range(20)),
   "마술적인 것은 [아이러니] 장치가 따로 맡는다  ← 사건과 자리를 나눠 둔다")

print()
print("[집중] **곁들이는 한 덩어리에 하나만**")
print("      ← 각자 비율로 켜지게 두었더니 절반 넘는 덩어리에 둘 이상이 겹쳤고")
print("        (100덩어리 중 2개 34회 · 3개 17회 · 5개 3회) 프롬프트가 18,000자를 넘었다.")
print("        그러면 계수가 1.0 이라 매번 켜져 있어도 급발진이 아홉 목소리 중 하나가 된다.")
_bk = flow.blank()
for _i, (_b, _k) in enumerate([("places", "웅포"), ("objects", "소금 공장"),
                               ("people", "도영"), ("facts", "실종"),
                               ("objects", "무전기"), ("people", "재현"),
                               ("places", "파출소")]):
    flow._merge(_bk["ledger"], {_b: {_k: {"직업": "x"} if _b == "people" else "x"}}, at=_i)
flow._merge(_bk["ledger"], {"rules": {"겨울 출항": "x"}, "open": {"왜 실종되나": "x"},
                            "macguffin": {"소금 공장": "x"}}, at=1)
_SIDES = ("[관계]", "[설정]", "[의심]", "[연결]", "[예외]", "[시점]", "[소재]")
_counts = []
_imp = 0
for _i in range(1, 61):
    _p = flow.write_prompt(dict(_bk, chunks=["x"] * _i))
    _counts.append(sum(_o in _p for _o in _SIDES))
    _imp += "[급발진]" in _p
ok(max(_counts) <= 1, f"둘 이상 겹치지 않는다 (최대 {max(_counts)}개)")
ok(sum(_counts) > 30, f"그래도 자주 곁들인다 ({sum(_counts)}/60)")
ok(_imp == 60, f"급발진은 매 덩어리 실린다 ({_imp}/60)  ← 이건 곁들이가 아니라 본체다")
_one = flow.write_prompt(dict(_bk, chunks=["x"] * 3))
ok(_one.index("[급발진]") < _one.index("[열린 것]"),
   "급발진이 앞자리에 선다  ← 뒤에 묻히면 안 지켜진다")

print()
if fails:
    print(f"충격: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("충격: 조합 · 연속 회피 · 때 · 확산 교대 · 셈 -- 통과")
