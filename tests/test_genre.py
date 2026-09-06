"""갈래 꾸러미 -- **갈아 끼운다.** 그리고 사건이 이야기를 끈다.

틀(리듬·확산·모순·급발진·말맛)은 갈래와 상관없이 그대로 돌아야 한다. 갈래가 바꾸는
것은 무엇을 놓느냐와 어느 쪽으로 기울이느냐 둘뿐이다 -- 그것이 여기서 고정하는 계약이다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import flow, genre, shock as SH, wording as W              # noqa: E402

_bad = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        _bad.append(label)


print("[갈래] **갈아 끼운다** -- 이번엔 로맨스, 다음엔 다른 것")
ok(genre.get("") == {}, "갈래를 안 주면 아무것도 안 씌운다  ← 지금까지의 틀 그대로")
_died = False
try:
    genre.get("없는갈래")
except ValueError:
    _died = True
ok(_died, "모르는 갈래는 사실대로 실패한다  ← 조용히 물러서면 밤새 다른 것을 쓴다")
ok("romance" in genre.names(), f"로맨스가 있다 ({genre.names()})")

_g = genre.brief("romance", "씨", 3)
ok("[로맨스]" in _g, "머리표가 붙는다")
ok("이번 대목의 관계" in _g and "이번 대목에 일어날 수 있는 일" in _g,
   "관계와 사건을 하나씩 뽑아 준다")
ok("말로 진전되지 않는다" in _g,
   "관계는 말이 아니라 일로 움직인다고 못박는다  ← 지금은 대사로만 이야기가 간다")
ok(genre.brief("", "씨", 3) == "", "갈래가 없으면 빈 줄이다")
_rel = {tuple(SH._batch(genre.PACKS["romance"]["관계"], "씨|rel", i, "rel", 2))
        for i in range(10)}
ok(len(_rel) > 5, f"관계도 덩어리마다 다르다 ({len(_rel)}가지)")
_eve = {SH._batch(genre.PACKS["romance"]["사건"], "씨|eve", i, "eve", 1)[0]
        for i in range(10)}
ok(len(_eve) > 4, f"사건도 덩어리마다 다르다 ({len(_eve)}가지)")

print()
print("[저울] **소프트하게 올린다** -- 숫자를 박는 것이 아니라 구간을 옮긴다")
_base = [W._out_share("씨", n) for n in range(24)]
_rom = [W._out_share("씨", n, genre.tune("romance", "밖", None)) for n in range(24)]
ok(sum(_rom) / 24 > sum(_base) / 24 + 0.1,
   f"로맨스는 밖이 더 많다 (평균 {sum(_rom)/24:.0%} 대 {sum(_base)/24:.0%})")
ok(len(set(_rom)) > 15, f"그래도 매 덩어리 다르다 ({len(set(_rom))}가지)  ← 고정값이 아니다")
ok(min(_rom) < max(_rom) - 0.2, f"폭이 살아 있다 ({min(_rom):.0%}~{max(_rom):.0%})")
ok(genre.tune("", "밖", (0.25, 0.75)) == (0.25, 0.75), "갈래가 없으면 원래 구간이다")

print()
print("[사슬] **사건이 이야기를 끈다** -- 결과가 다음 원인이 된다")
print("      ← 덩어리를 잇는 것이 꼬리 1,200자뿐이라, 모델은 앞 문장에 이어 붙이는")
print("        것만 했다. 앞 덩어리가 세계에 무엇을 바꿔 놨는지는 아무도 안 알려 줬다.")
_bk = flow.blank(flow.FIRST)
ok(flow.turned(_bk) == "", "첫 덩어리에는 바뀐 것이 없다")
_bk["chunks"] = ["x" * 200]
_bk["ledger"]["people"] = {"도영": {"_age": 0, "나이": "42"}}
_bk["ledger"]["places"] = {"웅포": {"_age": 0}}
_bk["_last_shock"] = "낯선 사람 / 문을 부수고 들어온다 / 동네"
_t = flow.turned(_bk)
ok("도영(인물)" in _t and "웅포(장소)" in _t, "지난 덩어리가 새로 놓은 것을 짚는다")
ok("직전에 벌어진 일" in _t, "직전 사건도 짚는다")
ok("그 결과에서 연다" in _t, "이번 덩어리를 그 결과에서 열게 한다")
ok("말로 정리하지 말고 그 결과를 겪게 해라" in _t,
   "말로 정리하지 못하게 한다  ← 대사로 때우면 사건이 아니라 요약이다")
ok("한 칸은 바꿔 놓고" in _t, "이 덩어리도 세계를 바꾸고 끝내게 한다")

_old = flow.blank(flow.FIRST)
_old["chunks"] = ["x" * 200]
_old["ledger"]["people"] = {"도영": {"_age": -9, "나이": "42"}}
ok(flow.turned(_old) == "", "오래된 것은 안 짚는다  ← 매번 같은 이름을 대면 그것도 배경이다")

print()
print("[격리] **갈래는 틀을 안 건드린다**")
_p0 = flow.write_prompt(flow.blank(flow.FIRST))
_bk2 = flow.blank(flow.FIRST)
_bk2["genre"] = "romance"
_p1 = flow.write_prompt(_bk2)
for _sec in ("[문장]", "[리듬]", "[점층]", "[대사가 이야기다]", "[말맛]", "[확산]"):
    ok((_sec in _p0) == (_sec in _p1), f"{_sec} 는 갈래와 무관하다")
ok("[로맨스]" not in _p0, "갈래를 안 주면 로맨스가 안 실린다")
ok("[로맨스]" in _p1, "갈래를 주면 실린다")

print()
print("[직장물] **좋은 글을 튕기던 자를 고쳤다**")
print("      ← 표본(취준 직장물)을 우리 자로 재니 여덟 군데서 걸렸다. 대사 19%,")
print("        주고받기 5턴, 긴 대사 1개. 그런데 이 글은 서술이 이야기를 끈다 --")
print("        '대사가 절반' 은 자가 아니라 **갈래 가정**이었다.")
_s = (Path(__file__).resolve().parent / "sample_job.txt")
if _s.exists():
    _t = _s.read_text(encoding="utf-8")
    from novel import diffusion as F, rhythm as R                     # noqa: E402
    _base = F.check(_t, {}, {}, want=0.5)
    _tuned = F.check(_t, {}, {}, want=0.15,
                     tune={"자": genre.tune("job", "자", {})})
    ok(len(_tuned) < len(_base),
       f"직장물 저울로 재면 지적이 준다 ({len(_base)}건 → {len(_tuned)}건)")
    ok(not [c for c in R.check(_t, want=0.35, talk=0.2)],
       f"리듬은 이제 통과한다 ({R.check(_t, want=0.35, talk=0.2)})")
    _m = R.measure(_t)
    ok(R.numclimb(_t) >= 4,
       f"숫자로 하는 점층을 센다 ({R.numclimb(_t)}개)  ← 이음말만 세면 2개로 낙제였다")
    ok(_m["climb"] >= _m["n"] // R.LIMITS["climb"],
       f"점층 {_m['climb']}개 (필요 {_m['n'] // R.LIMITS['climb']}개)")

ok("job" in genre.names(), "직장물 꾸러미가 있다")
_j = genre.brief("job", "씨", 2)
ok("[직장물]" in _j, "머리표가 붙는다")
ok("이야기를 끄는 것은 대사가 아니라 서술이다" in _j, "무엇이 이야기를 끄는지 말한다")
ok("절차" in _j, "세계를 움직이는 것이 절차라고 말한다")
ok("이번 대목의 화법" in _j, "갈래 고유의 말버릇을 준다")
for _k in ("화자가 끼어든다", "자문자답", "화면을 그대로 옮긴다", "숫자로 점층한다"):
    ok(_k in genre.PACKS["job"]["화법"], f"표본에서 뽑아낸 화법: {_k}")
ok("이번 대목의 화법" not in genre.brief("romance", "씨", 2),
   "화법이 없는 갈래에는 안 실린다  ← 갈래마다 가진 것이 다르다")

_dlg = genre.tune("job", "대사", None)
ok(_dlg and _dlg[1] < 0.5, f"직장물은 대사 몫이 낮다 ({_dlg})")
ok(genre.tune("job", "자", {}).get("rally", 9) <= 3,
   "주고받기 요구도 낮다  ← 혼잣말이 대부분인 갈래다")
ok(genre.tune("romance", "자", {}) == {}, "로맨스는 자를 안 건드린다")

print()
print("[가짓수] **목록이 아니라 곱으로 뽑는다** -- 열두 개짜리 목록은 백 덩어리면 바닥난다")
print("      ← 그것이 과접합이다. 축을 갈라 곱하면 목록을 안 늘리고도 만 가지가 되고,")
print("        축이 갈래의 것이라 갈래 밖으로 새지도 않는다.")
for _g in ("job", "romance"):
    ok(genre.size(_g) > 5000, f"{_g}: 사건 {genre.size(_g):,}가지")
    _es = [tuple(genre.event(_g, "씨앗", i).values()) for i in range(200)]
    ok(len(set(_es)) > 180, f"{_g}: 200 덩어리에 {len(set(_es))}가지가 나온다")
    ok(not [1 for a, b in zip(_es, _es[1:]) if a == b],
       f"{_g}: 이웃한 덩어리가 같은 사건을 안 받는다")
    ok(not [1 for a, b in zip(_es, _es[1:])
            if sum(x == y for x, y in zip(a, b)) >= 3],
       f"{_g}: 축 셋 이상이 이웃과 겹치지 않는다  ← 축마다 따로 흔들린다")
    ok(genre.event(_g, "씨앗", 7) == genre.event(_g, "씨앗", 7),
       f"{_g}: 같은 씨앗·번호면 같다  ← 이어 쓰기에 재현된다")

_jb = genre.brief("job", "씨", 5)
ok("이번 대목의 뒤틀림" in _jb, "뒤틀림이 실린다")
ok("대사로 알리지 말고 **일로**" in _jb,
   "사건을 일로 벌이게 한다  ← 대사로 알리면 그건 요약이지 사건이 아니다")
ok("이미 있는 것에 붙여라" in _jb,
   "이미 있는 것에 붙인다  ← 매번 새 회사를 만들면 이야기가 안 이어진다")
ok("축은 출발점이지 각본이 아니다" in _jb, "비틀어도 된다고 말해 준다")
ok(genre.event("", "씨", 1) == {}, "갈래가 없으면 뒤틀림도 없다")

print()
print("[예시] **꾸러미에 구체적인 예를 박지 않는다**")
print("      ← 실측: 화법 설명에 '179번 · 87회 · 42회 · 14회처럼' 이라고 적었더니")
print("        원고가 그 수를 그대로 베껴 썼다('벽에 42회, 87회, 14회를 적는 남자').")
print("        '정확히 말하자면' 과 똑같은 사고를 새 꾸러미에서 또 냈다.")
import re as _re                                                      # noqa: E402
for _gname, _pack in genre.PACKS.items():
    _texts = []
    for _key in ("머리", "관계", "사건", "화법"):
        _v = _pack.get(_key)
        if isinstance(_v, dict):
            _texts += [f"{k} {v}" for k, v in _v.items()]
        elif _v:
            _texts.append(_v)
    _nums = [t for t in _texts if _re.search(r"\d{2,}", t)]
    ok(not _nums, f"{_gname}: 두 자리 이상 수가 안 박혀 있다 ({_nums[:1]})")
    _quoted = [t for t in _texts if "'" in t and "처럼" in t]
    ok(not _quoted, f"{_gname}: 따옴표 친 예문이 없다 ({_quoted[:1]})")

print()
print("[청춘] **판돈은 작고 무게는 크다**")
ok("youth" in genre.names(), "청춘물 꾸러미가 있다")
_y = genre.brief("youth", "씨", 4)
ok("[청춘물]" in _y, "머리표가 붙는다")
ok("시간이 정해져 있다" in _y, "끝이 정해진 기간이 압력이 된다고 말한다")
ok("자기가 어떤 사람인지 아직 모른다" in _y,
   "인물이 백지에서 시작한다  ← 겪는 중에 자기도 몰랐던 쪽으로 튄다")
_yd = genre.tune("youth", "대사", None)
ok(_yd and _yd[0] > genre.tune("job", "대사", (0, 0))[0],
   f"직장물보다 말이 많다 (청춘 {_yd} 대 직장 {genre.tune('job', '대사', None)})")
ok(_yd[1] <= 0.6, "그래도 위를 열어 두지 않는다  ← 대사로만 굴러가면 사건이 요약이 된다")
ok(genre.tune("youth", "자", {}).get("rally", 0) >= 3,
   "주고받기는 길게 간다  ← 이 나이대는 실제로 오래 떠든다")
ok(genre.size("youth") > 5000, f"사건이 곱으로 뽑힌다 ({genre.size('youth'):,}가지)")
_ye = {tuple(genre.event("youth", "씨", i).values()) for i in range(20)}
ok(len(_ye) >= 18, f"덩어리마다 다른 뒤틀림이 나온다 ({len(_ye)}/20)")
ok(genre.tune("youth", "초현실", 1) == 0, "현실 바운더리 안이다")

print()
print("[여는 좌표] **첫 문장을 고정하면 그 문장의 세계가 원고를 끌고 간다**")
print("      ← 지명 하나가 백 덩어리를 따라다녔다. 그렇다고 매번 같은 문장으로 열면")
print("        매번 같은 데서 시작한다. 그래서 문장 대신 좌표를 뽑는다.")
_o1, _o2 = genre.opening("youth", "가"), genre.opening("youth", "나")
ok(_o1.startswith("[좌표]"), "좌표 표식으로 시작한다")
ok("무대" in _o1 and "관계" in _o1, "무대와 관계를 뽑아 준다")
ok(_o1 != _o2, "씨앗이 다르면 다른 자리에서 연다")
ok(len({genre.opening("youth", str(i)) for i in range(20)}) >= 15,
   "스무 번 돌리면 열다섯 자리 넘게 나온다")
ok(genre.opening("", "가") == "", "갈래가 없으면 좌표도 없다")
_ob = flow.blank(genre.opening("youth", "가")); _ob["genre"] = "youth"
_op = flow.write_prompt(_ob)
ok("첫 문장은 네가 지어라" in _op,
   "좌표로 열면 문장을 주지 않는다  ← 사람이 지은 문장은 말씨까지 심는다")
ok("[첫 문장 — 이것으로 시작하라]" not in _op, "머리표가 바뀐다")
ok("좌표를 문장으로 옮겨 적지 마라" in _op, "좌표를 그대로 받아쓰지 못하게 한다")
ok("[첫 문장 — 이것으로 시작하라]" in flow.write_prompt(flow.blank(flow.FIRST)),
   "문장을 주면 예전 머리표 그대로다  ← 주는 길도 남는다")

print()
print("[끄기] **갈래가 초현실을 끌 수 있다**")
print("      ← 직장물로 돌렸는데 죽은 사람이 걸어 다니고 시간을 거스르는 서류가")
print("        나오는 미스터리가 됐다. '말한 것이 실제가 된다' 장치 하나가 이야기를")
print("        통째로 다른 데로 끌고 간다.")
_lit = sum(bool(SH.impulse("씨", i)["literal"]) for i in range(40))
_off = sum(bool(SH.impulse("씨", i, literal=False)["literal"]) for i in range(40))
ok(_lit > 0, f"기본은 가끔 켜진다 ({_lit}/40)  ← 표류에서는 이게 맛이다")
ok(_off == 0, f"끄면 안 나온다 ({_off}/40)")
ok(genre.tune("job", "초현실", 1) == 0, "직장물은 꺼져 있다")
ok(genre.tune("romance", "초현실", 1) == 1, "로맨스는 그대로다")
ok(genre.tune("job", "의심", 1.0) < 1.0, "직장물은 사실을 흔드는 것도 줄인다")
_src = (Path(__file__).resolve().parent.parent / "novel" / "flow.py").read_text(encoding="utf-8")
ok('GENRE.tune(book.get("genre", ""), "초현실", 1)' in _src, "flow 가 그 저울을 본다")

print()
if _bad:
    print(f"갈래: {len(_bad)}개 실패 -- {_bad}")
    raise SystemExit(1)
print("갈래: 갈아끼우기 · 저울 · 사슬 · 격리 -- 통과")

print()
print("[변수] **고정 파라미터는 안 바뀌고, 서사 변수는 바뀐다**")
print("      ← 도중에 시점이나 세계 법칙이 흔들리면 설정이 충돌한다. 원장이")
print("        무모순성을 지키는 것과 같은 이유다.")
_bk4 = flow.blank(flow.FIRST)
ok(set(_bk4["fixed"]) == {"시점", "전제", "톤", "법칙"}, "고정 넷을 들고 있다")
_fb = flow.fixed_brief(_bk4)
ok("원고 내내 안 바뀐다" in _fb, "안 바뀐다고 못박는다")
ok("만약 ~한다면" in _fb, "핵심 전제를 묻는다")
ok("보여서" in _fb, "선언하지 말고 보여서 정하라고 한다")
_bk4["fixed"]["시점"] = "1인칭 주인공"
ok("**1인칭 주인공**" in flow.fixed_brief(_bk4), "정해진 것은 그대로 실린다")

ok("표면 목표" in flow.CARD and "내면 결핍" in flow.CARD,
   "인물 카드에 Want 와 Need 가 있다")
_ex = flow.extract_prompt("아무 산문")
ok("의식적으로 쫓는 것" in _ex and "본인이 모르는 채로 모자란 것" in _ex,
   "추출기가 둘을 갈라 뽑는다")
ok("둘은 어긋나 있어야 한다" in _ex, "어긋나야 옮겨 갈 데가 생긴다")
ok("bonds" in _bk4["ledger"], "원장에 관계 지수 칸이 있다")
ok("적대가 조력으로" in _ex, "관계가 바뀌는 것이 이야기라고 말한다")

print()
print("[세기] **갈등은 쌓이고, 쌓이면 조인다**")
for _owed, _since, _word in ((1, 500, "느슨"), (6, 2000, "조여"), (11, 3800, "팽팽")):
    _bk4["ledger"]["open"] = {f"o{i}": 1 for i in range(_owed)}
    _bk4["since"] = _since
    _bk4["chunks"] = ["x"]
    _tb = flow.tension_brief(_bk4)
    ok(_word in _tb, f"미결 {_owed} · {_since}자 → {_tb[:34]}")
ok(flow.tension_brief(flow.blank(flow.FIRST)) == "", "첫 덩어리에는 세기를 안 말한다")

_p9 = flow.write_prompt(dict(flow.blank(flow.FIRST), chunks=["x" * 300]))
ok("속에 있는 것은 밖으로 나와야 한다" in _p9,
   "내현이 외현으로 발현되게 한다  ← 속만 적으면 일기다")
ok("[고정]" in _p9 and "[세기]" in _p9, "둘 다 프롬프트에 실린다")
