"""말맛 장부 -- 쓴 것은 세어 두고 안 쓴 쪽으로 민다.

하한을 더 두지 않는다. 하한을 두면 하한을 정확히 맞춘다는 것을 두 번 겪었다
(짧은 '-다' 62%, 긴 대사 여덟 할). 이건 금지가 아니라 **복원력**이다 -- 한쪽으로
기울면 반대쪽으로 미는 힘이고, 기울지 않았으면 아무 일도 하지 않는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import flow, rhythm, shock as SH, wording as W             # noqa: E402

_bad = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        _bad.append(label)


print("[말맛] **기울면 되민다** -- 하한을 하나 더 두는 것이 아니다")
ok(W.brief([], "씨", 0).count("말끝") == 0,
   "원고가 없으면 말끝을 안 민다  ← 밀 방향이 없다")

_da = ["배가 들어왔다. " * 40]
ok("-다" in W.hogs(_da), f"'-다' 만 쓰면 그것을 짚는다 ({W.hogs(_da)})")
ok("-다" not in W.thin(_da), "많이 쓴 것을 '써 보라' 고 밀지는 않는다")
ok(len(W.thin(_da)) == W.PUSH_END,
   f"적게 쓴 것 {W.PUSH_END}개를 민다  ← 한꺼번에 다 시키면 안 지켜진다")

_mixed = ["배가 들어왔다. 온다. 오겠다. 올까. 오는군. 올 것이다. 오지. 옴. 와라. " * 3]
ok(not W.hogs(_mixed), f"고르게 썼으면 아무 말도 안 한다 ({W.hogs(_mixed)})")

print()
print("[비유·꼴] **세지 않고 뽑는다** -- 은유를 정규식으로 어떻게 찾겠는가")
_f = [tuple(W.figures("씨", n)) for n in range(20)]
ok(all(len(x) == W.PUSH_FIG for x in _f), "매번 정해진 개수를 뽑는다")
ok(all(len(set(x)) == len(x) for x in _f), "한 덩어리 안에서 겹치지 않는다")
ok(len(set(_f)) > 8, f"덩어리마다 다르다 ({len(set(_f))}가지)")
ok(W.figures("씨", 3) == W.figures("씨", 3), "같은 씨앗·번호면 같다  ← 이어 쓰기에 재현된다")
ok("번역체" in W.FORMS, "영어로 쓴 다음 옮긴 듯한 꼴도 재료다")
ok(len(set(tuple(W.forms("씨", n)) for n in range(20))) > 5, "꼴도 덩어리마다 다르다")

print()
print("[리얼리즘] **자세하되 있을 법하게** -- 다채로움이 허구가 되면 안 된다")
_b = W.brief(["배가 들어왔다. " * 40], "씨", 2)
ok("현실의 테두리 안" in _b, "현실 밖으로 나가지 말라고 한다")
ok("재서 말하면 진짜가 된다" in _b, "자세함이 그럴듯함을 만든다고 말한다")
ok("사람이 저질러서" in _b, "마법으로 풀지 못하게 한다")

print()
print("[문장] **몰리면 되민다** -- 몫이 맞아도 몰려 있으면 읽을 땐 두 덩어리다")
_short = "\n".join(["짧다."] * 9)
_long = "\n".join(["이것은 쉼표로 이어 붙여서 마흔다섯 자를 넘기게 만든 긴 문장인데, 정말로 그렇다."] * 7)
ok([c for c in rhythm.check(_short) if "짧은 문장이 내리" in c],
   "짧은 것이 몰리면 긴 문장으로 끊으라고 한다")
ok([c for c in rhythm.check(_long) if "긴 문장이 내리" in c],
   "긴 것이 몰리면 짧은 문장으로 끊으라고 한다")

print()
print("[흔들기] **목표치는 한 벌을 나눠 쓴다** -- 두 벌로 두면 한쪽만 고치게 된다")
_v = [rhythm.wave("씨", n, 0.1, 0.4) for n in range(80)]
ok(0.1 <= min(_v) and max(_v) <= 0.4, f"구간 안이다 ({min(_v):.2f}~{max(_v):.2f})")
_mid = 0.25
_run = _best = 1
_prev = None
for _x in _v:
    _hi = _x > _mid
    _run = _run + 1 if _hi == _prev else 1
    _prev = _hi
    _best = max(_best, _run)
ok(_best <= 3, f"한쪽으로 안 쏠린다 (최대 {_best}번 연속)")
ok(abs(sum(_v) / len(_v) - _mid) < 0.05, f"평균은 가운데다 ({sum(_v) / len(_v):.2f})")

src = Path(flow.__file__).read_text(encoding="utf-8")
ok("_wording(book)" in src, "프롬프트에 실린다")
ok("리듬은 몫이 아니라 배치다" in src, "몰지 말라고 프롬프트에도 적혀 있다")

print()
print("[군집] **인물이 느는 것이 사건이 느는 것이다**")
from novel import shock as SH                                         # noqa: E402
_sc = SH.brief(SH.draw("씨", 1))
ok("이 일로 사람들이 갈라진다" in _sc, "사건 뒤에 사람들이 갈라진다고 말한다")
ok("새 사람이 하나씩 딸려 온다" in _sc, "갈라진 자리마다 사람이 는다")
ok("군집처럼" in _sc, "붙고 갈라지고 사라지고 죽는다")
ok("죽은 사람은 되살아나지 않는다" in _sc, "죽음만은 되돌릴 수 없다  ← 원장의 무모순성과 같은 말")
ok("한 덩어리에 전부 하지는 마라" in _sc, "한 번에 다 시키지는 않는다")
_ways = {SH.scatter("씨", i) for i in range(12)}
ok(len(_ways) > 6, f"흩어지는 방향이 덩어리마다 다르다 ({len(_ways)}가지)")
ok(all(len(set(w)) == len(w) for w in _ways), "한 사건 안에서 겹치지 않는다")

print()
print("[세계] **다양한 설정을 섞되 있을 법하게** -- 제도 · 매체 · 제한")
_b2 = W.brief(["배가 들어왔다. " * 40], "씨", 3)
ok("이번 대목의 제도" in _b2, "제도를 하나 준다  ← 사람을 움직이는 것은 마음이 아니라 절차다")
ok("이번 대목의 매체" in _b2, "편지·영화·드라마·책 같은 장치를 준다")
ok("이번 대목의 제한" in _b2, "제한을 준다")
ok("우연이 문제를 풀지 못하게 하는 것이 이 자리다" in _b2,
   "제한이 편의주의를 막는 장치라고 말한다")
_w = {W.brief([], "씨", n).count("제도") for n in range(6)}
_p = {tuple(SH._batch(W.SYSTEMS, "씨|이번 대목의 제도", n, "이번 대목의 제도", 1))
      for n in range(12)}
ok(len(_p) > 5, f"제도가 덩어리마다 다르다 ({len(_p)}가지)")
ok("편입 시험" in " ".join(W.SYSTEMS), "편입 시험도 재료다")
ok(any("편지" in x for x in W.MEDIA), "편지도 재료다")

print()
print("[감정] **초고의 감정은 단속하지 않는다** -- 잡을 것은 내용이 아니라 방향과 꼴이다")
_hot = ["그는 슬펐다. 그는 불안했다. 그는 외로웠다."] * 4
ok("감정" not in W.brief(_hot, "씨", 4),
   "감정 얘기를 프롬프트에 안 싣는다  ← 초고에는 있어도 좋다")
ok(W.feel_rate("그는 슬펐다. 그는 앉았다.") == 0.5, "재 두기는 한다")
ok(W.feel_rate('"나는 슬퍼."') == 0.0,
   "대사는 안 센다  ← 사람은 자기 기분을 말한다. 그건 대사가 할 일이다")

print()
print("[대사 몫] **대사가 원고의 절반이다** -- 0.10 은 바닥이었지 목표가 아니었다")
_talky = "\n".join(['"이건 대사다. 길게 말한다, 정말로 길게 말이다."'] * 9
                    + ["서술이다."] * 6)
_share = rhythm.measure(_talky)["talk"]
ok(not [c for c in rhythm.check(_talky, talk=_share) if "대사가 전체 줄의" in c],
   f"나온 만큼을 목표로 주면 통과한다 ({_share:.0%})")
ok([c for c in rhythm.check(_talky, talk=0.9) if "대사가 전체 줄의" in c],
   "목표가 아홉 할이면 모자라다고 한다")
ok([c for c in rhythm.check(_talky, talk=0.2) if "희곡이지 소설이 아니다" in c],
   "서술이 있어야 할 대목에서 대사만 이어지면 그것도 잡는다")
ok(0.35 <= (rhythm.TALK_LO + rhythm.TALK_HI) / 2 <= 0.65,
   f"절반 언저리를 조준한다 ({rhythm.TALK_LO}~{rhythm.TALK_HI})")
src2 = Path(flow.__file__).read_text(encoding="utf-8")
ok("_dialogue(book)" in src2, "프롬프트가 자와 같은 숫자를 본다")
ok("내력도 사정도 숫자도 대사 안에 녹는다" in src2, "정보를 대사에 녹이라고 한다")

print()
print("[외현] **밖을 보여라** -- 안으로만 파고들면 무슨 일이 어디서 나는지 안 보인다")
_b3 = W.brief(["x" * 50], "씨", 2)
ok("밖을 보여라(외현)" in _b3, "밖을 시키는 자리가 있다")
ok(_b3.index("밖을 보여라") < _b3.index("이번 대목의 제도"),
   "외현이 앞에 선다  ← 뒤에 묻으면 안 지켜진다")
ok("이름과 번호를 대라" in _b3, "'낡은 건물' 이 아니라 몇 층에 뭐라고 적힌 건물인지")
ok("자릿수와 붙는 말이 그럴듯해야" in _b3,
   "지어내되 있을 법한 꼴로  ← 예시를 박지 않고 '어떤 종류의 이름인지' 를 시킨다")
_kinds = " ".join(W.OUTSIDE.values())
for _k in ("업종", "도로명", "발행처", "노선 번호", "명찰", "조항"):
    ok(_k in _kinds, f"어떤 이름표를 대야 하는지 말해 준다: {_k}")
ok("누구 것인지 물어라" in _b3, "저 상호는 누구 이름인지 묻게 한다  ← 그 물음이 다음 사람을 부른다")
ok("이 사람이 보는 것이다" in _b3,
   "**보는 사람이 있다** -- 화자의 설명이 아니라 주인공의 눈이다")
ok("안 닿은 것은 없는 것이나 같다" in _b3, "눈길이 안 간 것은 안 적힌다")
ok("본 것에는 그 사람의 짐작이 묻는다" in _b3, "본 것에 그 사람이 묻어난다")
ok("이번 대목의 보는 방식" in _b3, "어떻게 보는지도 덩어리마다 다르다")
_g = {SH._batch(W.GAZE, "씨|gaze", i, "gaze", 1)[0] for i in range(14)}
ok(len(_g) > 5, f"보는 방식이 여러 가지다 ({len(_g)}가지)")
for _k in ("놓친다", "다시 확인한다", "글자부터 읽는다"):
    ok(_k in W.GAZE, f"사람이 실제로 하는 짓이 들어 있다: {_k}")
_outs = {W._out_share("씨", i) for i in range(20)}
ok(len(_outs) > 10, f"안팎의 몫이 덩어리마다 다르다 ({len(_outs)}가지)")
ok(0.25 <= min(_outs) and max(_outs) <= 0.75, "구간 안이다  ← 한쪽만 남기지는 않는다")

print()
print("[이음말] **예시를 박으면 원고가 그것으로 도배된다**")
_bk = flow.blank(flow.FIRST)
_c = {flow._climb(dict(_bk, chunks=["x"] * i)) for i in range(12)}
ok(len(_c) > 8, f"이음말이 덩어리마다 다르다 ({len(_c)}가지)")
_p = flow.write_prompt(dict(_bk, chunks=["x" * 200]))
ok("이것만 쓰라는 것이 아니다" in _p, "목록에 없는 것으로 받아도 된다고 한다")
ok("호칭과 말높임은 관계가 정한다" in _p,
   "처음 만난 사람에게 '너' 라고 안 한다  ← 무례해서가 아니라 한국어가 그렇게 안 굴러간다")
# **선 채로 서 있는 지시를 뺐다.** "같은 장면을 또 쓰지 마라" 를 프롬프트에 박아 두면
# 겹치지 않은 덩어리까지 매번 그 말을 듣는다. 겹쳤을 때만, 얼마나 겹쳤는지와 함께 말한다.
ok("같은 장면을 또 쓰지 마라" not in _p, "되풀이 금지를 프롬프트에 박아 두지 않는다")
from novel import echo as _E                                          # noqa: E402
_a = "항구에서 도영을 만나 소금 공장 얘기를 했다. 그는 웃었고 나는 담배를 물었다." * 3
_b = "소금 공장 얘기를 하러 항구에서 도영을 다시 만났다. 나는 담배를 물었고 그는 웃었다." * 3
_c = "시청 민원실에서 번호표를 뽑고 두 시간을 기다렸다. 반려 사유는 적혀 있지 않았다." * 3
ok(_E.samey(_b, _a) > _E.SAMEY_MAX,
   f"낱말만 바꾼 되풀이를 잡는다 ({_E.samey(_b, _a):.0%})  ← 글자로 견주면 남남으로 나온다")
ok(_E.samey(_c, _a) < 0.2, f"다른 장면은 안 잡는다 ({_E.samey(_c, _a):.0%})")
ok([x for x in _E.check(_b, _a) if "겹친다" in x], "겹쳤을 때만 말한다")
ok(not [x for x in _E.check(_c, _a) if "겹친다" in x], "안 겹치면 아무 말도 안 한다")

print()
print("[낯선 개념] **어디서 온 것이든 끌어온다** -- 소설은 무엇이든 삼킨다")
_b4 = W.brief(["x" * 60], "씨", 4)
ok("끌어올 개념" in _b4, "남의 분야에서 끌어오게 한다")
ok("바깥 말에서 끌어올 것" in _b4, "남의 말에서도 끌어오게 한다")
ok("설정이 아니라 성격이 된다" in _b4,
   "설명하지 말고 쓰게 한다  ← 인물이 자기 삶에 갖다 붙이는 순간 성격이 된다")
ok("어색한 채로 두는 것이 요점이다" in _b4, "한국어답게 다듬지 말라고 한다")
_o = {tuple(SH._batch(W.ODD, "씨|odd", i, "odd", W.PUSH_ODD)) for i in range(16)}
ok(len(_o) > 8, f"덩어리마다 다른 분야를 뒤진다 ({len(_o)}가지)")
ok(all(len(set(x)) == len(x) for x in _o), "한 덩어리 안에서 겹치지 않는다")
_fg = {SH._batch(W.FOREIGN, "씨|foreign", i, "foreign", 1)[0] for i in range(16)}
ok(len(_fg) > 5, f"바깥 말도 덩어리마다 다르다 ({len(_fg)}가지)")
ok(len(W.ODD) >= 12 and len(W.FOREIGN) >= 10, "뒤질 데가 넉넉하다")

print()
print("[차림표] **목록 전체를 보여 주고 이번 것만 짚는다**")
print("      ← 뽑힌 둘만 보여 주면 모델이 아는 것이 둘뿐이 된다. 점층 이음말을 넷만")
print("        보여 줬다가 원고가 그 넷으로 도배된 일이 있었다.")
_b5 = W.brief(["x" * 60], "씨", 4)
for _name, _pool in (("비유", W.FIGURES), ("꼴", W.FORMS), ("제도", W.SYSTEMS),
                     ("매체", W.MEDIA), ("제한", W.LIMITS_LIFE), ("외현", W.OUTSIDE),
                     ("개념", W.ODD), ("바깥 말", W.FOREIGN)):
    _miss = [k for k in _pool if k not in _b5]
    ok(not _miss, f"{_name}: {len(_pool)}개가 전부 실린다 (빠진 것 {_miss[:2]})")
ok(_b5.count("목록 밖도 자유다") >= 6, "목록 밖도 자유라고 매번 말해 준다")
ok("그 밖에 쓸 수 있는 것" in _b5, "안 뽑힌 것은 이름만 보여 준다  ← 설명까지 다 붙이면 프롬프트가 터진다")
ok(len(_b5) < 4000, f"그래도 {len(_b5)}자에 담긴다  ← 이름은 짧고 설명은 뽑힌 것에만")

print()
if _bad:
    print(f"말맛: {len(_bad)}개 실패 -- {_bad}")
    raise SystemExit(1)
print("말맛: 되밀기 · 비유 · 꼴 · 리얼리즘 · 몰림 -- 통과")
