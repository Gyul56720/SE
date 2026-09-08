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
        "답": "반만", "갈고리종류": "피", "갈고리": "로일의 팔이 문틀에 끼여 잘려 나간다"}


print("[다섯 칸] **전개 · 연출 · 대사 · 인물 · 빌드업**")
for _c, _min in (("전개", 25), ("큰줄기", 10), ("로맨스", 30), ("싸움", 15), ("시스템", 15),
                 ("설정", 8), ("연출", 10), ("대사", 12), ("인물", 12), ("외모", 8), ("관능", 8),
                 ("반응", 6), ("빌드업", 14)):
    ok(len(SP.CATS[_c]) >= _min, f"{_c} {len(SP.CATS[_c])}개")
ok(SP.total() >= 180, f"전부 {SP.total()}개  ← 사용자: 최대한 많이")
_bad = [(c, n, r) for c, items in SP.CATS.items() for n, r, _ in items
        if any(v in n + r for v in ("은빛", "잿빛", "금빛 왕자"))]
ok(not _bad, f"설정 값이 문법에 박혀 있지 않다 ({_bad[:2]})  ← 이명은 [색]+[직함] 꼴만")
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
ok("· 싸움이 있으면:" in _w and "· 몸과 살갗:" in _w and "· 주변의 반응:" in _w,
   "싸움 · 외모/관능 · 반응 칸이 있다  ← 전투 자세히 · 생생하게 · 반응 격하게")
_cp = BT.card_prompt(book())
ok("[로맨스 · 싸움 · 체계 본보기" in _cp and "[설정 본보기" in _cp, "각본에 로맨스 · 싸움 · 체계 · 설정이 실린다")

print()
print("[같은 장면 반복] **마지막 비트를 썼으면 분량이 안 찼어도 다음 회차다**")
print("      ← 실측: 갈고리를 쓴 뒤 같은 카드가 남아 다음 덩어리가 같은 장면을 다시 썼다.")
_br = book(100)
_dr = Director([BASE, dict(BASE, 질문="다음 회차의 질문")])
BT.ensure(_br, _dr)
_br["chunks"].append("가" * (BT.EP * 4 // 5))          # 회차의 5분의 4 -- 마지막 비트 차례
ok(BT.beat_at(_br) == 3, f"마지막 비트 차례다 ({BT.beat_at(_br)})")
BT.brief(_br)                                           # 집필 프롬프트를 만들었다 = 마지막 비트를 맡겼다
_br["chunks"].append("나" * 500)                        # 그 덩어리를 썼다. 분량은 아직 EP 미만
ok(sum(len(c) for c in _br["chunks"]) < BT.EP * 2, "분량으로는 아직 같은 회차다")
BT.ensure(_br, _dr)
ok(_br["card"]["질문"] == "다음 회차의 질문" and _br["card"]["ep"] == 1,
   f"그래도 다음 회차 카드가 선다 (회차 {_br['card']['ep'] + 1})  ← 같은 장면을 두 번 안 쓴다")
BT.ensure(_br, _dr)
ok(_br["card"]["ep"] == 1 and BT.ep_no(_br) == 1, "새 카드는 다음 덩어리에서 그대로 유지된다")
ok(any(n in _w for n in SP.names("연출")) and any(n in _w for n in SP.names("대사")), "본보기가 실제로 실린다")
_bk["chunks"].append("라" * 1000)
ok(BT.brief(_bk) != _w, "덩어리마다 다른 본보기가 돈다")

print()
if fails:
    print(f"novel_space: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("novel_space: 다섯 칸 · 각본 프롬프트 · 심고 거둔다 · 집필 프롬프트 -- 통과")
