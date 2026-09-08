"""스키마 통로 배선 검사. **LLM 도 네트워크도 안 쓴다.**

무엇을 재는가:
  · 통로에 **판정이 한 방울도 안 흐르는가** -- 이 파일의 요점이다
  · 실을 것이 없으면 **한 글자도 안 싣는가**
  · 형제를 거르지 않는가 (자르는 것은 고르는 것이 아니다)
  · 되풀이를 재되 **기각하지 않는가**
  · 스위치로 통로를 닫을 수 있는가 (켜고 끄고 견주려면 필요하다)
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mathdrift import measure as ME
from mathdrift import space as SP
from mathdrift import spread as SPR
from mathdrift import terrain as TR

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def grab(fn, *a, **kw):
    """화면을 받아 온다. **`ok` 를 이 안에서 부르지 않는다** -- 그러면 그 줄이 통째로
    삼켜져서 실패해도 안 보인다(이 파일에서 한 번 그랬다)."""
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        rc = fn(*a, **kw)
    return rc, b.getvalue()


def led_of(*rows):
    led = SP.blank()
    SP.add(led, {"식": r"\sum_r \lambda_r U V W = \delta", "점": r"(U,V,W,\lambda)",
                 "정의역": r"F = \mathbb{R}", "치수": 91}, parent="-", op="씨앗", dist=0)
    for op, rec in rows:
        SP.add(led, rec, parent="S1", op=op)
    return led


def rec(expr, dom=r"F = \mathbb{R}", dim=91):
    return {"식": expr, "점": r"(U,V,W,\lambda)", "정의역": dom, "치수": dim}


print("== 판정은 한 방울도 안 흐른다 ==")
_led = led_of(("이산화", rec(r"\sum_r \lambda_r U V W \equiv \delta", r"F = \mathbb{F}_2")))
# 원장에 심판이 남긴 것을 **잔뜩** 박아 둔다. 통로가 그것을 흘리면 여기서 걸린다.
_s2 = SP.get(_led, "S2")
_s2["재현"] = {"판정": "재현", "시금석": "strassen b=2 m=7", "하드코딩": False,
              "왜": "쓸모없는말"}
_s2["잰것"] = {"확산": True, "몫": 0.933, "물려받음": 14, "자식몫": 0.5}
_s2["등급"] = "검증가능"
_b = TR.brief(_led, "S1")
for _w in ("재현", "판정", "확산", "0.933", "검증가능", "시금석", "하드코딩", "strassen"):
    ok(_w not in _b, f"'{_w}' 가 프롬프트에 안 실린다")
ok("점수" not in _b and "통과" not in _b and "좋" not in _b,
   "**잘했다/못했다 는 말이 없다** -- 겨눌 수 있는 수를 주면 그리로 균질해진다")
ok(all(f in TR.VERDICT_FIELDS for f in ("재현", "잰것", "판정")),
   "안 읽을 칸이 코드에 목록으로 적혀 있다")

print("\n== 실을 것이 없으면 한 글자도 안 싣는다 ==")
_seed = SP.blank()
SP.add(_seed, rec(r"\sum_r \lambda_r U V W = \delta"), parent="-", op="씨앗", dist=0)
ok(TR.brief(_seed, "S1") == "",
   "씨앗뿐이면 빈 줄이다  ← 늘 실으면 그것이 상수가 되어 묻힌다")
ok(TR.brief(_led, "S2") == "" or "이 부모에서" not in TR.brief(_led, "S2"),
   "자식이 없는 부모 자리에는 형제 줄이 없다")

print("\n== 형제를 거르지 않는다 ==")
_many = led_of(*[(o, rec(f"E_{i}")) for i, o in enumerate(
    ["이산화", "매장", "쌍대", "경계화", "완비화", "국소화", "망각", "범주화"])])
_sibs = TR.siblings(_many, "S1")
ok(len(_sibs) == 8, f"형제는 다 세어 돌려준다 ({len(_sibs)}개)  ← 고르지 않는다")
_b2 = TR.brief(_many, "S1")
ok(f"{8 - TR.SIBS}개 더" in _b2,
   f"프롬프트에 {TR.SIBS}개만 싣되 **몇 개를 못 실었는지 말한다**  ← 조용히 자르지 않는다")
ok(all(o in _b2 for o, _ in _sibs[:TR.SIBS]), "실은 것에는 연산자 이름이 붙는다")

print("\n== 지형은 세는 것뿐이다 ==")
_mix = led_of(("이산화", rec("E1", r"F = \mathbb{Z}")),
              ("표수 이동", rec("E2", r"F = \mathbb{F}_2")),
              ("경계화", rec("E3", r"F = \mathbb{R}", 95)))
_c = TR.census(_mix)
ok(_c["정의역"] == {3: 2, 2: 1, 1: 1, 0: 0}, f"정의역을 등급별로 센다 ({_c['정의역']})")
ok(_c["치수"] == (91, 95), f"치수의 폭을 적는다 ({_c['치수']})")
_b3 = TR.brief(_mix, "S1")
ok("R/C 2" in _b3 and "F_q 1" in _b3, "그 수가 프롬프트에 그대로 간다")
ok("좁혀라" not in _b3 and "늘려라" not in _b3 and "해라" not in _b3,
   "**무엇을 하라고 시키지 않는다** -- 지형만 말한다")

print("\n== 되풀이를 재되 기각하지 않는다 ==")
_dup = led_of(("이산화", rec("A + B = C")), ("매장", rec("A + B = C")),
              ("쌍대", rec(r"\lim A + B = C \quad \epsilon")))
_st = TR.stale(_dup)
ok(_st["똑같음"] == 1, f"토큰이 완전히 같은 것을 센다 ({_st['똑같음']}개)")
ok(_st["몫"] > 0, f"몫으로도 적는다 ({_st['몫']})")
ok(len(_dup["spaces"]) == 4, "**되풀이해도 원장에 그대로 있다** -- 기각이 아니다")
ok(TR.stale(led_of(("이산화", rec("A = B"))))["똑같음"] == 0, "안 겹치면 0")
ok(TR.stale(SP.blank())["잰공간"] == 0, "빈 원장에서도 안 터진다")

print("\n== 형제끼리 얼마나 겹치나 (통로가 베끼게 만드는지 재는 자) ==")
_same = led_of(("이산화", rec("A + B = C")), ("매장", rec("A + B = C")))
_diff = led_of(("이산화", rec("A + B = C")), ("매장", rec(r"\int \rho \, dx \le \eta")))
ok(TR.spread_of(_same, "S1") == 1.0, "똑같은 형제 둘은 1.0")
ok(TR.spread_of(_diff, "S1") == 0.0, "겹치는 기호가 없으면 0.0")
ok(TR.spread_of(_same, "S1") > TR.spread_of(_diff, "S1"), "둘을 가른다")
ok(TR.spread_of(led_of(("이산화", rec("A = B"))), "S1") is None,
   "형제가 하나면 None  ← 견줄 것이 없다")

print("\n== 스위치 ==")
_on = TR.ON
try:
    TR.ON = False
    ok(TR.brief(_many, "S1") == "",
       "MATHDRIFT_SCHEMA=0 이면 한 글자도 안 나간다  ← 켜고 끄고 견주려면 있어야 한다")
finally:
    TR.ON = _on
ok(TR.brief(_many, "S1") != "", "되돌리면 다시 실린다")

print("\n== 프롬프트에 실제로 붙는가 ==")
_picks = [("쌍대", "화살표를 뒤집는다", 1)]
_p_on = SPR.prompt(SP.get(_many, "S1"), _picks, TR.brief(_many, "S1"))
_p_off = SPR.prompt(SP.get(_many, "S1"), _picks, "")
ok("지금까지의 지형" in _p_on, "지형이 프롬프트 안에 들어간다")
ok("지금까지의 지형" not in _p_off, "빈 지형이면 그 자리가 아예 없다")
ok(len(_p_on) > len(_p_off), "실린 만큼만 길어진다")
ok("오로지 수학적 기호만" in _p_on, "원래 규칙은 그대로다")
ok("심판" not in _p_on and "관문" not in _p_on,
   "**심판 얘기는 여전히 없다** -- 통로를 열었다고 관문이 생긴 것이 아니다")

print("\n== 보고 ==")
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    _rc = TR.show(_dup)
_out = _buf.getvalue()
ok(_rc == 0 and "되풀이" in _out, "되풀이를 보고에 적는다")
ok("기각하지 않는다" in _out, "기각이 아니라고 화면에도 적어 둔다")
# `ok` 를 redirect 안에서 부르면 그 줄이 통째로 삼켜진다 -- 실패해도 화면에 안 뜬다.
# 판정만 안에서 받고 말은 밖에서 한다.
with contextlib.redirect_stdout(io.StringIO()):
    _rc404 = TR.show(_dup, "S999")
ok(_rc404 == 1, "없는 부모는 1 로 끝난다")

print("\n== 깊이별로 부모를 얼마나 베끼나 ==")
# 실측 2026-09-08, VM 51개 런: 부모몫이 깊이 1 에 0.270 · 2 에 0.770 · 3 에 0.887 로
# **올랐다.** 그리고 깊이 3 에서 S8 의 자식 넷(국소화·상대화·이산화·쌍대)이 부모 식과
# 앞 36자가 글자 그대로 같았다 -- 연산자가 이름만 걸린 것이다.
_E = r"Tr(\sum_{r=1}^{m} \lambda_r (U_r \otimes V_r \otimes W_r)) = n^2"
_dep = SP.blank()
SP.add(_dep, {"식": _E, "정의역": r"F = \mathbb{R}"}, parent="-", op="씨앗", dist=0)
_p0 = SP.get(_dep, "S1")
for _op in ("국소화", "상대화", "이산화"):
    _c = SP.add(_dep, {"식": _E + f"  ({_op})", "정의역": r"F = \mathbb{R}"},
                parent="S1", op=_op)
    _c["잰것"] = ME.measure(_c, _p0)
_far = SP.add(_dep, {"식": r"\omega = \inf \{ \tau : R_n(M) \le n^{\tau} \} 아주 다른 식",
                     "정의역": r"F = \mathbb{R}"}, parent="S1", op="점근화")
_far["잰것"] = ME.measure(_far, _p0)
_rows = TR.by_depth(_dep)
ok(len(_rows) == 1 and _rows[0]["깊이"] == 1, "깊이별로 묶는다")
ok(_rows[0]["수"] == 4, f"그 깊이의 공간을 다 센다 ({_rows[0]['수']}개)")
ok(_rows[0]["그대로"] == 3,
   f"**앞머리가 글자 그대로 같은 것을 센다** ({_rows[0]['그대로']}개)  ← 낱말과 달리 못 우긴다")
ok(_rows[0]["부모몫"] is not None and _rows[0]["부모몫"] > 0.5,
   f"부모몫도 평균 낸다 ({_rows[0]['부모몫']})")
# 짧은 식은 안 센다 -- 둘 다 36자가 있어야 "앞 36자가 같다" 가 뜻이 있다
_short = SP.blank()
SP.add(_short, {"식": "A = B", "정의역": r"F = \mathbb{R}"}, parent="-", op="씨앗", dist=0)
SP.add(_short, {"식": "A = B", "정의역": r"F = \mathbb{R}"}, parent="S1", op="매장")
ok(TR.by_depth(_short)[0]["그대로"] == 0,
   "짧은 식은 안 센다  ← 자른 길이가 다르면 비교가 뜻이 없다")
ok(TR.by_depth(SP.blank()) == [], "빈 원장은 빈 목록")
_rc_d, _out_d = grab(TR.show, _dep)
ok("앞머리 그대로" in _out_d and "깊이" in _out_d, "보고에 깊이별 표가 나온다")
ok("연산자가 이름만 걸린 것이다" in _out_d,
   "**오르면 무슨 뜻인지 화면에 적어 둔다** -- 판정은 아니다")

print("\n== 24시간을 견디는 저장 ==")
import tempfile
_big = SP.blank()
SP.add(_big, rec("E0"), parent="-", op="씨앗", dist=0)
_d = Path(tempfile.mkdtemp())
_f = _d / "l.json"
_ob, _oe = SP.BIG, SP.EVERY
try:
    SP.BIG, SP.EVERY = 5, 4
    _wrote, _small = [], []
    for _i in range(12):
        SP.add(_big, rec(f"E{_i + 1}"), parent="S1", op="매장")
        _small.append(len(_big["spaces"]) < SP.BIG)     # 이 걸음에서 원장이 작았나
        _wrote.append(SP.save_step(_big, _f, i=_i, last=(_i == 11)))
    ok(any(_small) and all(w for w, sm in zip(_wrote, _small) if sm),
       f"원장이 {SP.BIG} 밑일 동안은 걸음마다 쓴다")
    _late = [w for w, sm in zip(_wrote[:-1], _small) if not sm]
    ok(_late and not all(_late),
       "커지면 걸음마다 안 쓴다  ← O(n^2) 이라 24시간을 못 끝낸다")
    ok(_wrote[-1], "**마지막 걸음은 크기와 상관없이 쓴다**")
    ok(len(SP.load(_f)["spaces"]) == 13, "다 쓰고 나면 원장이 온전하다")
finally:
    SP.BIG, SP.EVERY = _ob, _oe
ok(not list(_d.glob("*.tmp")),
   "임시 파일을 안 남긴다  ← .tmp 에 쓰고 갈아 끼우므로 쓰다 죽어도 반쪽이 안 된다")
_before = _f.read_text(encoding="utf-8")
SP.save(_big, _f)
ok(_f.read_text(encoding="utf-8") == _before, "`save` 는 크기와 상관없이 늘 쓴다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    raise SystemExit(1)
print("전부 통과")
