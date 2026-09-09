"""**nv2 -- 앞 판이 죽은 이유를 구조로 막았는가.**

여기서 보는 것은 재미가 아니라 배선과 관문이다. 앞 판(`novel/`)이 죽은 병은 하나였다:
**적어 두고 안 부친 규칙.** 다섯 번 났고 다섯 번 다 원고는 멀쩡히 나왔다.

실행: python3 tests/test_nv2.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from nv2 import bank, card, ledger as LG, probe, prompt as P, repair, rules, ruler, write  # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


CARD = {"원함": "명부에 제 이름을 올리는 것", "막는것": "문지기가 이름을 지운다",
        "장면": ["문 앞에서 쫓겨남", "뒷길에서 거래", "명부 앞의 대질"],
        "쾌감": "얕보던 자가 무릎을 꿇는다", "전투": "문지기와 한 합",
        "설정": "명부: 이름이 없으면 못 든다", "바뀜": "이름이 명부에 남는다",
        "끝": "명부가 덮이고 손등이 찍힌다", "심음": "낡은 인장", "거둠": ""}


def book(n=1, hero=""):
    b = {"씨앗": "씨", "회차": n, "회차분량": 5000, "원장": LG.blank()}
    if hero:
        LG.add(b["원장"], "사람", {"이름": hero, "주인공": True})
    return b


print("[은행] **문법만 적는다 -- 값은 한 글자도**")
_lit = [(c, n) for c in bank.CATS for n, r, _t in bank.CATS[c]
        if any(v in n + r for v in ("거지", "왕궁", "흑마왕", "강아지", "중세",
                                    "은빛", "금빛", "잿빛", "함부루크", "웅포"))]
ok(not _lit, f"사용자가 든 예도 값도 안 박혀 있다 ({_lit[:2]})")
ok(bank.total() >= 100, f"항목이 넉넉하다 ({bank.total()}개)")
ok(all(bank.cond(c) or c == "여는꼴" for c in bank.CATS), "칸마다 조건이 있다(여는꼴만 예외)")
_c = sum(len(bank.cond(c)) for c in bank.CATS)
ok(_c < bank.total() / 4, f"조건은 전체의 사분의 일 미만 ({_c}/{bank.total()})  ← 다 조건이면 조건이 아니다")
ok(bank.draw("전개", "씨", 1, 3) != bank.draw("전개", "씨", 2, 3), "회차마다 다른 본보기가 나온다")
ok(bank.draw("전개", "씨", 1, 3) == bank.draw("전개", "씨", 1, 3), "같은 원고 같은 회차는 같다")
ok(not set(bank.cond("전투")) & set(bank.eg("전투")), "조건과 본보기가 안 겹친다")

print("\n[자] **밴드는 잰 것에서만 나온다**")
# 앞 판이 여기서 죽었다 -- 표본이 다른 갈래였다. sent_len 가운뎃값 22.58 인데 실제
# 웹소설 1화는 47.6 이었고, 폭이 넓어 둘 다 '정상' 이라 아무도 늘리라고 안 했다.
ok(ruler.band("sent_len") and ruler.band("sent_len")[0] > 30,
   f"실제 1화에서 나온 밴드 ({ruler.band('sent_len')})")
ok(ruler.band("없는축") is None, "표본이 없는 축은 밴드가 없다  ← 짐작한 수는 못 들어온다")
ok(ruler.band("sent_var") is None, "sent_var 도 표본이 없어 밴드가 없다")
_real = [s for s in ruler.samples() if s.get("이름")]
ok(_real, f"표본이 파일에 있다 ({len(_real)}편)")

print("\n[자] **이름 대용이 부사를 안 잡는다**")
# 첫 판은 '속에서 · 낮게 · 위로 · 몸을' 을 이름으로 잡았다. 잘못 답하는 자는 없느니만 못하다.
_t = ('"레이언이 왔다."\n레이언은 검을 들었다. 레이언의 손이 떨렸다.\n'
      "카일이 웃었다. 카일을 보았다. 카일의 눈.\n"
      "그 속에서 낮게 울렸다. 그 속에서 위로 갔다. 그 속에서 몸을 돌렸다.\n")
_n = set(ruler._names(_t))
ok({"레이언", "카일"} <= _n, f"사람 이름은 잡는다 ({sorted(_n)})")
ok(not (_n & {"속에서", "낮게", "위로", "몸을"}), f"부사·조사 덩이는 안 잡는다 ({sorted(_n)})")

print("\n[관문] **잰다 · 부친다 · 고친다 셋을 갖춰야 규칙이다**")
ok(rules.gate() == [], f"등록된 규칙이 넷을 다 갖췄다 ({rules.gate()})")
ok(all(r.고친다 or r.되먹임만 for r in rules.RULES),
   "고치는 손이 없으면 '되먹임만' 이라고 밝혔다  ← 잡고 흘려보내는 자리를 안 둔다")
ok(all(ruler.band(r.축) for r in rules.live()), "사는 규칙은 전부 밴드가 있다")
ok(rules.MAX <= 3, f"한 회차에 부치는 것은 셋까지 ({rules.MAX})  ← 한꺼번에 시키면 안 지켜진다")
_bad = "그는 걸었다. " * 80
ok(len(rules.says(_bad)) <= rules.MAX, f"어긋난 축이 많아도 셋까지 ({len(rules.says(_bad))}개)")
ok(rules.says("") == [], "잴 것이 없으면 아무 말도 안 한다")

print("\n[수리] **잡았으면 고친다 -- 무손실인 것만**")
_dup = "긴 문장이 여기 하나 있고 그것이 두 번 적혀 있다.\n" * 2 + "다른 줄이 하나.\n"
_k, _cut = repair.dedup(_dup)
ok(_cut > 0 and repair.selfish(_k)[0] == 0, f"복사한 줄을 지운다 ({_cut}자)")
_many = "\n".join(f"이것은 서로 다른 {i}번째 문장이고 길이가 충분히 길다." for i in range(20))
ok(repair.dedup(_many + "\n" + _many.splitlines()[3])[1] == 0,
   "문턱 아래면 한 글자도 안 지운다  ← 후렴까지 지우면 그것이 과잉이다")
ok(repair.dedup('"난 안 가."\n그가 말했다.\n"난 안 가."\n' + _dup)[0].count("난 안 가") == 2,
   "짧은 대사는 두 번 다 남는다")
ok(repair.stage("눈을 뜬 화자가 걸었다. 화자의 걸음.") == [("화자", 2)], "무대 낱말을 센다")
ok(repair.rename("화자가 걸었다.", "레이언")[0] == "레이언가 걸었다.", "이름을 알면 바꾼다")
ok(repair.rename("화자가 걸었다.", "")[1] == 0, "이름을 모르면 안 건드린다  ← 되먹임으로 넘긴다")
for _w in ("주인공", "쾌감", "장면", "설정"):
    ok(_w not in repair.STAGE, f"  '{_w}' 는 무대 낱말이 아니다  ← 원고에 나올 수 있다")
_cp = repair.copied("문 앞에서 쫓겨난 그가 뒷길로 돌아 거래를 한다.", ["뒷길에서 거래"])
ok(isinstance(_cp, list), "각본을 옮긴 자국을 찾는다(되먹임으로만)")

print("\n[프롬프트] **예산과 자리**")
_p, _d, _spent = P.build(book(3), CARD, prev="앞 회차.\n")
ok(_spent <= P.BUDGET, f"지시가 예산 안이다 ({_spent:,} <= {P.BUDGET:,}자)")
ok(len(_p) < 4000, f"통째로도 앞 판(8,455자)의 절반 아래 ({len(_p):,}자)")
ok(len(re.findall(r"\*\*", _p)) // 2 < 30,
   f"굵은 글씨가 앞 판(88군데)보다 훨씬 적다 ({len(re.findall(r'[*][*]', _p)) // 2}군데)")
_blocks = probe._blocks(_p)
ok(_blocks and _blocks[1] == "반드시", f"[반드시] 가 맨 앞 (차례: {_blocks[:3]})")
ok(_p.index("[반드시]") < len(_p) * 0.2 if "[반드시]" in _p else True,
   "고치라는 말이 앞머리에 있다  ← 앞 판은 97% 지점이었다")
_big = dict(CARD, 원함="ㄱ" * 1200)
_p2, _d2, _s2 = P.build(book(3), _big, prev="앞.\n")
ok(_d2, f"예산에 막히면 떨어뜨린다 ({_d2})")
ok("예산" in _p2 and "안 실은 본보기" in _p2, "무엇을 떨어뜨렸는지 프롬프트에 적는다  ← 조용히 안 싣지 않는다")
_p3, _, _ = P.build(book(3, hero="레이언"), CARD)
ok("«레이언»" in _p3, "주인공 이름이 실린다")
ok("이름을 **이 회차에서 정하고**" in P.build(book(3), CARD)[0], "이름이 없으면 정하라고 한다")
ok("메모다" in _p3, "각본은 메모지 문장이 아니라고 말한다")
_p4, _, _ = P.build(book(0), CARD)
ok("첫회차" in probe._blocks(_p4) or "[첫회차]" in _p4, "첫 회차에는 첫 회차 문법이 실린다")
ok("첫회차" not in _p3, "둘째부터는 안 실린다")
ok("[전투]" in _p3 and "[전투]" not in P.build(book(3), dict(CARD, 전투=""))[0],
   "싸움이 없는 회차에는 전투·부상을 안 싣는다")

print("\n[카드] **설명문을 값으로 받지 않는다**")
ok(card.parse(json.dumps(CARD, ensure_ascii=False))["원함"] == CARD["원함"], "제대로 된 카드는 받는다")
for _bad_card in (dict(CARD, 원함=card._TMPL["원함"]),
                  dict(CARD, 장면=[card._TMPL["장면"]]),
                  dict(CARD, 장면=[])):
    try:
        card.parse(json.dumps(_bad_card, ensure_ascii=False))
        ok(False, "설명문/빈 뼈대를 받아들였다")
    except ValueError:
        ok(True, "뼈대가 설명문이거나 비면 버린다")
ok(card.make(book(), {}, lambda p: "산문이다", tries=1).get("_실패"), "못 세우면 그렇다고 남긴다")
_asked = card.ask(book(), {"끝": "되찾는다"})
ok("JSON 만 낸다" in _asked and "산문을 쓰지 마라" in _asked, "디렉터에게 산문을 안 시킨다")

print("\n[회차 쓰기] **회차가 생성 단위다**")
_bad_text = ("눈을 뜬 화자가 걸었다. 화자의 걸음.\n" * 2
             + "긴 문장을 여기 하나 두고 그것을 두 번 적어서 되풀이를 만든다.\n" * 2)
_r = write.once(book(1, hero="레이언"), CARD, lambda p: _bad_text, prev="앞 회차.\n")
ok(_r["상태"] == "ok", "한 번 불러 한 회차를 받는다")
ok("화자" not in _r["글"], "무대 낱말을 고쳐서 넣는다")
ok(any("지웠다" in d for d in _r["수리"]), f"되풀이를 지운다 ({_r['수리']})")
ok(isinstance(_r["어긋남"], list), "재서 어긋난 축을 남긴다")
ok(_r["지시"] <= P.BUDGET, "예산을 지킨다")
_r2 = write.once(book(1), CARD, lambda p: "눈을 뜬 화자가 걸었다.", prev="")
ok(any("무대 뒤" in o for o in _r2["넘길말"]),
   "이름을 모르면 다음 회차로 넘긴다  ← 잡고 흘려보내지 않는다")

print("\n[점검] **무엇이 켜졌는지 늘 찍는다**")
_rep = probe.report()
for _sec in ("[프롬프트]", "[규칙]", "[표본]", "[은행]", "[원장]"):
    ok(_sec in _rep, f"  {_sec}")
ok("표본이 없다 -- 규칙이 아니다" in _rep or "산다" in _rep, "규칙의 생사를 말한다")
ok("아직 없다" in _rep, "주인공 이름이 없으면 그렇다고 말한다")

print()
if fails:
    print(f"nv2: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("nv2: 은행 · 자 · 관문 · 수리 · 프롬프트 · 카드 · 회차 · 점검 -- 통과")
