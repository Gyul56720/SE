"""인물끼리 말이 얼마나 다른가 -- **시켜 놓고 안 재던 것을 잰다.**

`flow` 는 인물 카드에 말투를 적어 두고 그대로 말하게 시킨다. 그런데 지켜졌는지 재는
자가 없었다(사용자 평 2026-09-07: "대사가 너무 별로였다"). 방법은 문헌에서 왔다 --
문자 3-gram 분포의 부트스트랩 거리, 언어 독립적이고 한 작품 안에서만 계산한다
(EVIDENCE.md 10절).

여기서 고정하는 계약:

  · **1.0 이 기준점이다** -- 한 사람을 둘로 가른 것과 같으면 구별이 안 되는 것이다
  · **표본 크기가 답을 만들면 안 된다** -- 한쪽 대사가 두 배라고 말투가 달라지지 않는다
  · **귀속은 보수적으로** -- 애매하면 버린다. 섞이면 수가 거짓이 된다
  · **못 재면 없다고 한다** -- 0 으로 채우면 "말투가 같다" 와 "알 수 없다" 가 같아진다

실행: python3 tests/test_voicegap.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import voicegap as V                                       # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


FORMAL_HEAD = ["삼가 아뢰옵건대", "황공하오나", "여쭈옵건대", "감히 아뢰옵기를",
               "송구하오나", "엎드려 청하옵건대", "고하옵건대", "삼가 여쭈옵나니"]
FORMAL_TAIL = ["아니 되옵니다", "그러하옵니다", "모르겠사옵니다", "받자옵니다",
               "통촉하여 주시옵소서", "헤아려 주시옵소서", "아뢰옵나이다", "없사옵니다"]
BLUNT_HEAD = ["됐고", "아니 진짜", "그만해", "몰라", "알았다고", "야", "그래서 뭐", "어이없네"]
BLUNT_TAIL = ["어쩌라고", "지겹지도 않냐", "말이 되냐", "그냥 해", "됐어", "관심 없어",
              "나도 몰라", "하지 마"]
MID = ["가문의 일은", "그 사람 얘기는", "어제 그 자리에서", "형님께서 하신 말씀은",
       "지난번 약조는", "이번 연회 건은", "저쪽 사정은", "그 서찰 말인데"]


def lines(head, tail, seed, n=24):
    r = random.Random(seed)
    return [f"{r.choice(head)} {r.choice(MID)} {r.choice(tail)}" for _ in range(n)]


def weave(a, b):
    """윤설은 같은 줄 꼬리로, 카시아는 뒤 지문으로 귀속된다 -- 두 경로를 다 쓴다."""
    out = []
    for x, y in zip(a, b):
        out += [f'"{x}." 하고 윤설이 말했다.', f'"{y}."', "카시아가 잔을 내려놓았다."]
    return "\n".join(out)


WHO = ["윤설", "카시아"]

print("[귀속] **애매하면 버린다** -- 섞이면 수가 거짓이 된다")
_d = V.by_speaker('"가."  하고 윤설이 말했다.', WHO)
ok(_d.get("윤설") == ["가."], "같은 줄 꼬리에서 잡는다")
_d = V.by_speaker('카시아가 문을 열었다.\n"가."', WHO)
ok(_d.get("카시아") == ["가."], "바로 앞 지문에서 잡는다")
_d = V.by_speaker('"가."\n카시아가 문을 열었다.', WHO)
ok(_d.get("카시아") == ["가."], "바로 뒤 지문에서 잡는다")
_d = V.by_speaker('"가." 하고 윤설이 카시아에게 말했다.', WHO)
ok(not _d, "이름이 둘이면 버린다  ← 누가 한 말인지 모른다")
_d = V.by_speaker('"가." 하고 그가 말했다.', WHO)
ok(not _d, "이름이 없으면 버린다")
_d = V.by_speaker('"가." 하고 수윤설이 말했다.', WHO)
ok(not _d, "이름이 다른 낱말에 박혀 있으면 안 잡는다  ← 수윤설은 윤설이 아니다")
_d = V.by_speaker('"가."\n"나."\n윤설이 웃었다.', WHO)
ok(len(_d.get("윤설", [])) <= 1,
   "대사 줄은 지문이 아니다  ← 앞이 대사면 거기서 이름을 찾지 않는다")

print()
print("[자] **1.0 이 기준점이다** -- 한 사람을 둘로 가른 것과 같으면 구별이 안 된다")
_diff = V.measure(weave(lines(FORMAL_HEAD, FORMAL_TAIL, 1),
                        lines(BLUNT_HEAD, BLUNT_TAIL, 2)), WHO)
_same = V.measure(weave(lines(BLUNT_HEAD, BLUNT_TAIL, 3),
                        lines(BLUNT_HEAD, BLUNT_TAIL, 4)), WHO)
_same2 = V.measure(weave(lines(FORMAL_HEAD, FORMAL_TAIL, 5),
                         lines(FORMAL_HEAD, FORMAL_TAIL, 6)), WHO)
ok(_diff["voice_gap"] > 2.0, f"격식 대 반말이면 크게 벌어진다 ({_diff['voice_gap']})")
for _m, _lab in ((_same, "둘 다 반말"), (_same2, "둘 다 격식")):
    ok(0.6 < _m["voice_gap"] < 1.5,
       f"{_lab}이면 1.0 언저리다 ({_m['voice_gap']})  ← 문장은 다 다른데 말투가 같다")
ok(_diff["voice_gap"] > _same["voice_gap"] * 1.8,
   f"다른 말투가 같은 말투보다 뚜렷하게 크다 ({_diff['voice_gap']} 대 {_same['voice_gap']})")

print()
print("[편향] **표본 크기가 답을 만들면 안 된다**")
print("      ← 처음엔 안 거리를 반쪽끼리, 사이 거리를 통째로 쟀다. 3-gram 은 표본이")
print("        작을수록 멀어지므로 안 거리만 부풀었고, 같은 말투가 0.4 로 나왔다.")
_lop = V.measure(weave(lines(BLUNT_HEAD, BLUNT_TAIL, 7, 24),
                       lines(BLUNT_HEAD, BLUNT_TAIL, 8, 24)[:8] * 3), WHO)
ok(0.6 < _lop["voice_gap"] < 1.5,
   f"한쪽이 같은 말을 되풀이해도 말투가 같으면 1.0 언저리다 ({_lop['voice_gap']})")
_big = V.measure(weave(lines(FORMAL_HEAD, FORMAL_TAIL, 1, 48),
                       lines(BLUNT_HEAD, BLUNT_TAIL, 2, 48)), WHO)
ok(_big["voice_gap"] > 2.0,
   f"표본을 두 배로 해도 결론이 안 뒤집힌다 ({_diff['voice_gap']} → {_big['voice_gap']})")

print()
print("[없으면 없다고 한다] **0 으로 채우면 '같다' 와 '모른다' 가 같아진다**")
ok(V.measure("아무 지문만 있다. 대사가 없다.", WHO)["voice_gap"] is None,
   "대사가 없으면 None 이다")
_one = V.measure("\n".join(f'"{x}." 하고 윤설이 말했다.'
                           for x in lines(BLUNT_HEAD, BLUNT_TAIL, 9)), WHO)
ok(_one["voice_gap"] is None and _one["speakers"] == 1,
   "인물이 하나뿐이면 None 이다  ← 견줄 상대가 없다")
_thin = V.measure('"네." 하고 윤설이 말했다.\n"응."\n카시아가 웃었다.', WHO)
ok(_thin["voice_gap"] is None and _thin["skipped"],
   f"대사가 모자란 인물은 빼고 그 사실을 남긴다 ({_thin['skipped']})")

print()
print("[재현] **같은 원고면 같은 수** -- 안 그러면 되먹임을 믿을 수 없다")
_t = weave(lines(FORMAL_HEAD, FORMAL_TAIL, 1), lines(BLUNT_HEAD, BLUNT_TAIL, 2))
ok(V.measure(_t, WHO)["voice_gap"] == V.measure(_t, WHO)["voice_gap"],
   "두 번 재면 같은 수가 나온다")
ok(V.measure(_t, WHO)["pairs"] == V.measure(_t, WHO)["pairs"], "쌍별 값도 같다")

print()
print("[원문 격리] **결과에 원문이 안 실린다** (DATA.md)")
_r = repr(V.measure(_t, WHO))
ok("아뢰옵건대" not in _r and "어쩌라고" not in _r,
   "대사 원문이 결과에 안 들어간다  ← 새면 원고가 그것으로 도배된다")
ok(set(_diff["pairs"][0]) == {"a", "b", "between", "within", "gap"},
   "쌍에는 이름과 수만 있다")

print()
print("[되먹임] **기각하지 않는다** -- 겹치는 둘을 짚고 넘어간다")
print("      ← C층 지표에 기각 권한을 안 주는 것은 관문 열셋을 없애며 산 교훈이고,")
print("        4만 편에서 구조 준수와 인기가 무관했다는 결과가 그 근거다.")
_ledger = {"people": {"윤설": {}, "카시아": {}}}
_txt = weave(lines(BLUNT_HEAD, BLUNT_TAIL, 3), lines(BLUNT_HEAD, BLUNT_TAIL, 4))
_half = len(_txt) // 2
_book_same = {"chunks": [_txt[:_half], _txt[_half:]], "ledger": _ledger}
_b = V.brief(_book_same)
ok("[말투]" in _b, "구별이 안 되면 되먹인다")
ok("윤설" in _b and "카시아" in _b, "겹치는 둘의 이름을 짚는다")
ok("말끝" in _b and "호칭" in _b, "어디를 갈라야 하는지 말한다")
ok("어쩌라고" not in _b and "가문의 일은" not in _b,
   "대사 원문은 안 싣는다  ← 새면 원고가 그것으로 도배된다")

_txt2 = weave(lines(FORMAL_HEAD, FORMAL_TAIL, 1), lines(BLUNT_HEAD, BLUNT_TAIL, 2))
_h2 = len(_txt2) // 2
ok(V.brief({"chunks": [_txt2[:_h2], _txt2[_h2:]], "ledger": _ledger}) == "",
   "말투가 다르면 아무 말도 안 한다  ← 다 잘하고 있는데 잔소리하면 그것도 잡음이다")
ok(V.brief({"chunks": [], "ledger": _ledger}) == "", "첫 덩어리에는 안 나온다")
ok(V.brief({"chunks": [_txt], "ledger": {"people": {}}}) == "",
   "원장이 비었으면 안 나온다  ← 귀속할 이름이 없다")

print()
print("[배선] **프롬프트에 실린다**")
from novel import flow                                                # noqa: E402
_p = flow.write_prompt(dict(_book_same, genre="", first="첫 문장", seed_id="씨",
                            fixed={}, since=0))
ok("[말투]" in _p, "구별이 안 되면 프롬프트에 실린다")
_p2 = flow.write_prompt(dict(flow.blank(flow.FIRST), chunks=["x" * 300]))
ok("[말투]" not in _p2, "잴 것이 없으면 안 실린다  ← 지금까지의 프롬프트 그대로다")

print()
if fails:
    print(f"말투: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("말투: 귀속 · 기준점 1.0 · 표본 편향 · 없으면 None · 재현 · 원문 격리 -- 통과")
