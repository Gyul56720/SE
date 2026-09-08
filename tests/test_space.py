"""novel_space -- **게임 · 라노벨 · 애니의 문법이 실리고, 심은 것을 거두는가.**

세 불만이 세 층이었다: 상황이 안 떠오른다(연출) · 난입이 없다(전개 · 인물) · 빌드업이
없다(개연성). 여기서 보는 것은 배선이다 -- 다섯 칸이 있고, 회차마다 돌아가고, 각본
프롬프트와 집필 프롬프트에 실리고, 심은 것이 원장에 남아 다음 카드가 거둔다.

실행: python3 tests/test_space.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from novel import space as SP                                         # noqa: E402
from novel import beat as BT                                          # noqa: E402
from novel import flow                                                # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


def book(chars=100):
    b = flow.blank("첫 문장이다.")
    b["seed_id"] = "씨"
    b["chunks"] = ["가" * chars]
    b["arc"] = {"end": "끝", "start": "시작", "debts": [{"무엇": f"빚{i}", "갚음": 0} for i in range(5)], "made": "ropan"}
    b["_target"] = 50_000
    return b


class Director:
    def __init__(self, queue):
        self.queue, self.prompts = list(queue), []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        if "회차**의 각본" in prompt:
            return json.dumps(self.queue.pop(0), ensure_ascii=False)
        return "{}"


BASE = {"질문": "공녀가 초대장을 받아낸다", "방해": "백작 부인이 명부에서 이름을 지운다",
        "비트": [{"무엇": "a", "꼴": "장면"}, {"무엇": "b", "꼴": "요약"}, {"무엇": "c", "꼴": "장면"}],
        "답": "반만", "쾌감": "집사가 명부를 공녀 앞에 펼쳐 놓고 물러선다", "쾌감자리": 2,
        "갈고리종류": "피", "갈고리": "로일의 팔이 문틀에 끼여 잘려 나간다"}


print("[다섯 칸] **전개 · 연출 · 대사 · 인물 · 빌드업**")
for _c, _min in (("전개", 15), ("연출", 6), ("대사", 8), ("인물", 6), ("빌드업", 5)):
    ok(len(SP.CATS[_c]) >= _min, f"{_c} {len(SP.CATS[_c])}개")
ok("난입" in SP.names("전개") and "지는 싸움" in SP.names("전개"), "난입과 負けイベント 가 있다  ← 은빛 기사")
ok("이명" in SP.names("인물"), "二つ名 이 있다")
ok("화면" in SP.names("연출") and "등장 5단계" in SP.names("연출"), "레이아웃과 등장 연출이 있다  ← 상황이 떠오르게")
ok("먼저 심는다" in SP.names("빌드업"), "前フリ 규칙이 있다  ← 뜬금없음 방지")
_d0, _d1 = SP.draw("전개", "씨", 0, 4), SP.draw("전개", "씨", 1, 4)
ok(len(_d0) == 4 and _d0 != _d1 and SP.draw("전개", "씨", 0, 4) == _d0, "회차마다 돌고, 같은 원고는 같다")

print()
print("[각본 프롬프트] **전개 · 인물 본보기와 빌드업 규칙이 실린다**")
_p = BT.card_prompt(book())
ok("[전개 본보기" in _p and any(n in _p for n in SP.names("전개")), "전개 본보기가 실린다")
ok("[인물 본보기" in _p, "인물 본보기가 실린다")
ok("처음 나온 이름은 판을 뒤집을 수 없다" in _p, "빌드업 규칙이 전부 실린다")
ok('"심음"' in _p and '"거둠"' in _p, "심음 · 거둠을 요구한다")
ok("아직 없다 -- 이번 회차에 하나 심어라" in _p, "심어 둔 것이 없으면 심으라고 한다")

print()
print("[심고 거둔다] **원장에 남고, 다음 카드가 그 낱말로 거둔다**")
_b = book()
_d = Director([dict(BASE, 심음="회랑에 은빛 갑주의 기사가 다녀갔다는 소문", 거둠=""),
               dict(BASE, 심음="", 거둠="은빛 갑주의 기사"),
               dict(BASE, 심음="", 거둠="검은 백작의 인장")])
BT.ensure(_b, _d)
ok(len(BT.plants(_b)) == 1 and "은빛 갑주" in BT.plants(_b)[0]["무엇"], "심은 것이 원장에 남는다")
ok("**심는다:**" in BT.brief(_b) and "지나가듯" in BT.brief(_b), "집필 프롬프트가 지나가듯 심으라고 한다")
_b["chunks"].append("나" * BT.EP)
BT.ensure(_b, _d)
ok("은빛 갑주의 기사가 다녀갔다는 소문" in _d.prompts[-1], "다음 각본에 심어 둔 것이 보인다")
ok(len(BT.plants(_b)) == 0 and _b["plants"][0]["거둠"] == 1, "그 낱말로 거두면 원장에서 닫힌다")
ok("**거둔다:**" in BT.brief(_b) and "기척 → 실루엣" in BT.brief(_b), "거둘 때 등장 5단계를 시킨다")
_b["chunks"].append("다" * BT.EP)
BT.ensure(_b, _d)
ok(_b["card"]["거둠"] == "검은 백작의 인장" and not any(p.get("거둠") == 2 for p in _b["plants"]),
   "심은 적 없는 것을 거둔다고 하면 원장은 안 닫히고 로그에 남는다  ← 뜬금없음의 기록")
ok("아직 안 거둔 것" not in BT.show(_b) and "심음:" in BT.show(_b), "show 가 심음 · 거둠을 보여 준다")

print()
print("[집필 프롬프트] **연출 · 대사 본보기가 덩어리마다 실린다**")
_bk = book(); BT.ensure(_bk, Director([BASE]))
_w = BT.brief(_bk)
ok("· 연출:" in _w and "· 대사:" in _w, "연출과 대사 칸이 있다")
ok(any(n in _w for n in SP.names("연출")) and any(n in _w for n in SP.names("대사")), "본보기가 실제로 실린다")
_bk["chunks"].append("라" * 1000)
ok(BT.brief(_bk) != _w, "덩어리마다 다른 본보기가 돈다")

print()
print("[도파민] **전투 · 세계 · 쾌감 · 줄기 -- 두 번째 요구**")
print("      ← 사용자(2026-09-08 저녁): 액션씬 전투씬 스킬 직함 세계관 설정 더 자세히. 복수극도")
print("        좋고 거지가 왕궁 들어가서 권력 탈취하는 것도 좋고(예시야 하드코딩하지마).")
print("        중간에 주인공을 구해주는 잘생긴 히로인도 없고 도파민 요소가 없어.")
for _c, _min in (("전투", 12), ("세계", 10), ("쾌감", 12), ("줄기", 14)):
    ok(len(SP.CATS[_c]) >= _min, f"{_c} {len(SP.CATS[_c])}개")
ok(len(SP.CATS["전개"]) >= 28 and len(SP.CATS["인물"]) >= 13, "전개 · 인물도 늘었다")
ok("구원자" in SP.names("인물") and "구원 난입" in SP.names("전개") and "구원" in SP.names("쾌감"),
   "구해 주는 사람이 인물 · 전개 · 쾌감에 있다  ← 히로인")
ok("구원자도 심는다" in SP.names("빌드업"), "구원도 심어 둔 사람만 한다  ← 우연이 문제를 풀지 않는다")
ok("복수" in SP.names("줄기") and "밑바닥에서 왕좌로" in SP.names("줄기"),
   "복수와 왕좌는 줄기 목록의 둘이다  ← 하드코딩이 아니라 본보기")
ok(len({tuple(x[0] for x in SP.draw("줄기", str(i), 0, 4)) for i in range(30)}) >= 20,
   "씨앗마다 다른 줄기 넷이 보인다")
ok(all("숫자" in r or "이름" in r for n, r, _ in SP.CATS["세계"] if n == "등급은 이름이다"),
   "등급은 이름이지 숫자가 아니다  ← 상태창은 style.py 가 뺐다")
ok(any("조건" in n for n, _, _ in SP.CATS["전투"]), "기술에는 값이 아니라 조건이 있다  ← 사이다에서 대가는 고구마")
ok("작은 승리" in SP.names("쾌감"), "지는 회차에도 작은 것 하나  ← Ely 의 분산")

print("  [각본 프롬프트] 전투 · 세계 · 쾌감 본보기와 규칙이 실린다")
_pd = BT.card_prompt(book())
for _blk in ("[전투 본보기", "[세계 본보기", "[쾌감 본보기", "[설정집]"):
    ok(_blk in _pd, f"{_blk} 가 있다")
ok('"쾌감"' in _pd and '"쾌감자리"' in _pd and '"전투"' in _pd and '"설정"' in _pd, "쾌감 · 전투 · 설정을 요구한다")
ok("회차마다 쾌감이 하나 있다" in _pd and "지는 단계에서도" in _pd, "지는 회차에도 쾌감 하나를 요구한다")
ok("상태창 · 수치 · 게이지를 열지 마라" in _pd, "숫자 창을 막는다")
ok("쓰기 한 회차 앞에 세워라" in _pd, "설정은 쓰기 전에 세운다  ← 빌드업")
ok("이번 회차에 하나 세워라" in _pd, "설정집이 비면 세우라고 한다")

print("  [쾌감의 꼴] 갈고리와 같은 계약 -- 벌어진 문장. 빈 것은 되묻고, 두 번 틀리면 카드는 살린다")
ok(BT.joy_ok("얕보던 단장이 화자 앞에 무릎을 꿇는다") == "", "무릎은 통과")
ok("비었다" in BT.joy_ok(""), "빈 쾌감은 안 된다")
ok("질문" in BT.joy_ok("그가 무릎을 꿇을까?"), "질문은 안 된다")
ok("쾌감" in BT.joy_ok("\"이겼다.\"") and "갈고리" not in BT.joy_ok("\"이겼다.\""), "사유에 쾌감이라고 적힌다")
_bj = book()
_dj = Director([dict(BASE, 쾌감="", 전투="", 설정=""), dict(BASE, 쾌감="")])
BT.ensure(_bj, _dj)
ok(len(_dj.prompts) == 2 and "쾌감이 틀렸다" in _dj.prompts[-1], "빈 쾌감은 한 번 되묻는다")
ok(BT.has(_bj) and _bj["card"]["쾌감"] == "", "두 번 다 비면 카드는 살리고 쾌감만 비운다")
ok("**쾌감**" not in BT.brief(_bj), "쾌감이 없으면 집필 프롬프트도 조용하다")
_bq = book()
_dq = Director([dict(BASE, 갈고리="정말 잘렸을까?", 쾌감="그가 무릎을 꿇을까?"), BASE])
BT.ensure(_bq, _dq)
ok("갈고리가 틀렸다" in _dq.prompts[-1] and "쾌감이 틀렸다" in _dq.prompts[-1],
   "둘 다 틀리면 한 되묻기에 둘 다 싣는다  ← 호출은 한 번만 는다")
ok(_bq["card"]["쾌감"] == BASE["쾌감"], "고쳐 오면 받는다")

print("  [설정집] 카드가 세운 설정이 원장에 남고, 다음 카드와 화자가 그 이름을 본다")
_bc = book()
_dc = Director([dict(BASE, 설정={"이름": "회색 서임", "규칙": "기사단장만 내리고 증인 셋이 있어야 선다"},
                     전투="공녀의 호위가 단장의 부관과 붙는다 -- 격은 부관이 위, 촛대로 결착, 왼손에 상처가 남는다"),
               dict(BASE, 설정="회색 서임 -- 다시 세운다"),
               dict(BASE, 설정="붉은 패 -- 탑의 셋째 층 출입증. 피로 값을 치른다")])
BT.ensure(_bc, _dc)
ok(len(BT.codex(_bc)) == 1 and BT.codex(_bc)[0]["이름"] == "회색 서임", "설정이 설정집에 남는다")
_wc = BT.brief(_bc)
ok("**이 회차의 설정**: 회색 서임" in _wc and "상태창 · 수치를 열지 마라" in _wc, "집필 프롬프트가 이번 설정을 이름으로 시킨다")
ok("**싸움**" in _wc and "촛대로 결착" in _wc and any(n in _wc for n in SP.names("전투")),
   "싸움이 있으면 전투 문법이 실린다")
ok("**쾌감** (비트 2에서" in _wc and "곁의 사람들이다" in _wc, "쾌감이 비트 번호와 함께 실린다")
_bc["chunks"].append("마" * BT.EP)
BT.ensure(_bc, _dc)
ok(len(BT.codex(_bc)) == 1 and _bc["card"]["설정"] is None, "같은 이름을 다시 세우면 설정집의 것이 이긴다  ← 값이 둘이면 모순")
ok("회색 서임: 기사단장만" in _dc.prompts[-1], "다음 각본 프롬프트에 설정집이 보인다")
_bc["chunks"].append("바" * BT.EP)
BT.ensure(_bc, _dc)
ok([c["이름"] for c in BT.codex(_bc)] == ["회색 서임", "붉은 패"], "한 줄 꼴(이름 -- 규칙)도 받는다")
ok("설정집 (이 이름 그대로 쓴다" in BT.brief(_bc) and "회색 서임" in BT.brief(_bc), "화자에게 설정집이 실린다")
ok("설정집 2개" in BT.show(_bc) and "붉은 패" in BT.show_codex(_bc), "show · show_codex 가 보여 준다")
ok("**싸움**" not in BT.brief(_bc), "싸움이 없는 회차에는 전투 문법을 안 싣는다")
_bw = book(); BT.ensure(_bw, Director([dict(BASE, 쾌감자리=1)]))
_bw["chunks"].append("가" * (BT.EP * 4 // 5))
ok("앞 비트에서 이미 벌어졌다" in BT.brief(_bw), "쾌감 비트를 지났으면 되풀이하지 말라고 한다")
_bs = book(); BT.ensure(_bs, Director([dict(BASE, 쾌감자리="아홉")]))
ok(_bs["card"]["쾌감자리"] == 2, "쾌감자리가 엉뚱하면 지는 단계는 가운데 비트")
for _n in ("%", "번째", "회차 "):
    ok(_n not in _wc, f"'{_n}' 이 집필 프롬프트에 없다  ← 자를 시키지 않는다")

print()
print("[액션] **전투와 갈라 둔다 -- 싸우는 덩어리에는 통째로 싣는다**")
print("      ← 사용자: 액션씬 전투씬 더 자세히. 애니·만화와 소설 작법이 같은 것을 말한다:")
print("        화려함보다 알아보기 쉬움이 먼저다.")
ok(len(SP.CATS["액션"]) >= 5, f"액션 {len(SP.CATS['액션'])}개")
for _n in ("다섯 박", "한 문장에 동작 하나", "알아보기가 먼저", "약동감", "1인칭은 속도를 못 낸다"):
    ok(_n in SP.names("액션"), f"액션: {_n}")
ok("안 보여 주는 것" in SP.names("연출"), "연출에 카메라워크가 있다  ← 다 보여 주면 아무것도 안 보인다")
ok("움직임의 버릇" in SP.names("인물"), "인물에 움직임의 버릇이 있다")
_bf = book(); BT.ensure(_bf, Director([dict(BASE, 전투="호위가 부관과 붙는다 -- 격은 부관이 위")]))
_wf = BT.brief(_bf)
ok("액션은 이렇게 쓴다" in _wf, "싸움이 있으면 액션 규율이 실린다")
ok(all(n in _wf for n in SP.names("액션")), "돌려 뽑지 않고 **전부** 싣는다  ← 뽑으면 정작 싸우는 회차에 안 걸린다")
_bn = book(); BT.ensure(_bn, Director([dict(BASE, 전투="")]))
ok("액션은 이렇게 쓴다" not in BT.brief(_bn), "싸움이 없으면 안 싣는다")

print()
print("[전환] **판이 흔들리는가 -- 회차마다 하나는 바뀐다**")
print("      ← 사용자: 스토리 진행이 너무 느리다. 4만 자 내외의 전개가 없다. 한 씬의")
print("        반복이다. 판이 계속 흔들리며 뒤통수를 쳐야 한다.")
ok(len(SP.CATS["전환"]) >= 10, f"전환 {len(SP.CATS['전환'])}개")
for _n in ("예상은 배신, 기대는 배신 않기", "한 회차에 하나는 바뀐다", "기승전결", "서파급",
           "뒤집기", "세 회차마다 산", "더 센 것 말고 더 싫은 것", "한 회차 한 사건"):
    ok(_n in SP.names("전환"), f"전환: {_n}")
_pp = BT.card_prompt(book())
ok("[전환 본보기" in _pp, "각본에 전환 본보기가 실린다")
ok('"바뀜"' in _pp and "장소 | 처지 | 관계 | 앎" in _pp, "바뀜을 넷 중 하나로 요구한다")
ok("앞 회차와 다른 축을 바꿔라" in _pp, "같은 축을 두 번 바꾸지 못하게 한다")
ok("예상은 배신하고 기대는 배신하지 마라" in _pp, "뒤통수의 규율이 실린다")
ok("한 회차에 큰 사건 하나" in _pp, "한 회차 한 사건")
_bm = book()
_dm = Director([dict(BASE, 바뀜={"축": "처지", "무엇": "공녀가 명부에서 이름이 지워진다"}),
                dict(BASE, 바뀜="관계 -- 집사가 편을 바꾼다")])
BT.ensure(_bm, _dm)
ok(_bm["card"]["바뀜"] == {"축": "처지", "무엇": "공녀가 명부에서 이름이 지워진다"}, "바뀜이 카드에 붙는다")
ok("달라져 있는 것** (처지)" in BT.brief(_bm), "집필 프롬프트에 실린다")
_bm["chunks"].append("나" * BT.EP)
BT.ensure(_bm, _dm)
ok("**처지** 축이 바뀌었다" in _dm.prompts[-1], "다음 각본이 앞 회차의 축을 본다")
ok(_bm["card"]["바뀜"]["축"] == "관계", "한 줄 꼴(축 -- 무엇)도 받는다")
ok("바뀜(처지)" in BT.show(_bm) or "바뀜(관계)" in BT.show(_bm), "show 가 보여 준다")

print()
print("[수위] **켠 원고에만. 어른만 · 원하는지가 보인다는 조건이라 늘 실린다**")
ok(len(SP.CATS["수위"]) >= 10, f"수위 {len(SP.CATS['수위'])}개")
ok(SP.names("수위")[0] == "어른만" and SP.names("수위")[1] == "원하는지가 보인다",
   "머리 둘이 조건이다  ← 본보기가 아니라 조건이라 뽑기에서 안 빠진다")
ok(SP.HEAD["수위"] == 2, "머리 둘은 뽑기에서 뺀다  ← 안 빼면 같은 줄이 두 번 실린다")
_bh = book(); _bh["heat"] = 0.6
BT.ensure(_bh, Director([BASE]))
_wh = BT.brief(_bh)
ok("**수위 (성인)**" in _wh, "켜면 실린다")
ok("전부 어른이다" in _wh and "학생 · 미성년" in _wh, "어른만이 늘 실린다")
ok("원하는지가 보인다" in _wh, "동의가 늘 실린다")
_bh0 = book(); BT.ensure(_bh0, Director([BASE]))
ok("**수위 (성인)**" not in BT.brief(_bh0), "안 켜면 한 줄도 안 실린다  ← 기본은 꺼짐")
ok(flow.blank("x")["heat"] == 0.0, "원고의 기본 수위는 0 이다")
ok("--heat" in (REPO / "novel" / "flow.py").read_text(encoding="utf-8"), "인자로 켠다")

print()
if fails:
    print(f"novel_space: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("novel_space: 열한 칸 · 각본 · 심고 거둔다 · 집필 · 도파민 · 액션 · 전환 · 수위 -- 통과")
