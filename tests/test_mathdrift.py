"""mathdrift 배선 검사. **LLM 도 네트워크도 안 쓴다** -- 가짜 모델로 한 바퀴 돈다.

무엇을 재는가:
  · 계보가 끊긴 공간을 원장이 거절하는가 (인과성이 구성으로 보장되는가)
  · 되사상이 빈 공간을 **기각하지 않고** 등급만 내리는가 (발산은 안 죽인다)
  · 확산 두 계수가 세 경우를 가르는가 -- 확산 / 남의 공간 / 제자리
  · 발산 한 바퀴가 실제로 돌고 계보가 사슬로 남는가
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mathdrift import measure as ME
from mathdrift import ops as OPS
from mathdrift import space as SP
from mathdrift import spread as SPR

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def seed_led():
    led = SP.blank()
    SP.add(led, {"점": "랭크 1 텐서의 합",
                 "식": "U V W 세 행렬과 계수", "해독": "항등. Brent 항등식으로 검산",
                 "정의역": "연속. 매개변수 594개", "왜": "씨앗"},
           parent="-", op="씨앗", dist=0)
    return led


print("== 인과성은 구성으로 보장된다 ==")
led = seed_led()
try:
    SP.add(led, {"식": ""}, parent="S99", op="망각")
    ok(False, "원장에 없는 부모를 거절한다")
except ValueError:
    ok(True, "원장에 없는 부모를 거절한다")
ok(SP.get(led, "S1") is not None, "씨앗은 부모 '-' 로 올라간다")

print("\n== 원장은 pull 로 안 날아간다 ==")
# 실측 2026-09-07: 원장이 추적되고 있어서 VM 이 낳은 공간 15개가 git pull 한 번에
# 씨앗만 든 커밋본으로 되돌아갔다. compression/ledger.json 과 novel/*.json 이 같은
# 이유로 이미 .gitignore 에 있는데 그 규약을 안 따랐던 것이다.
_gi = (Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8")
ok("mathdrift/ledger.json" in _gi, "원장은 .gitignore 에 있다 (런타임 상태다)")
ok(SP.SEED.exists(), "씨앗은 파일로 저장소에 있다 (코드다)")
with tempfile.TemporaryDirectory() as d:
    _f = Path(d) / "없던원장.json"
    _boot = SP.load(_f)
    ok(len(_boot["spaces"]) == 1 and _boot["spaces"][0]["id"] == "S1",
       "원장이 없으면 씨앗에서 새로 세운다  ← 빈 원장으로는 발산이 못 시작한다")
    ok(_boot["spaces"][0].get("해독") and _boot["spaces"][0].get("부호화"),
       "씨앗이 해독기와 부호화기를 들고 있다 -- 시금석점은 거기서 만든다")
    _r = SP.add(_boot, {"해독": "돌아간다"}, parent="S1", op="망각")
    SP.save(_boot, _f)
    ok(len(SP.load(_f)["spaces"]) == 2, "원장이 생긴 뒤에는 씨앗이 그것을 안 덮는다")

print("\n== 발산은 죽이지 않는다 ==")
r = SP.add(led, {"점": "무엇인가"}, parent="S1", op="망각")
ok(r["등급"] == "미검증",
   "**코드 칸이 없는 것을 벌하지 않는다** -- 등급은 벌이 아니라 표다")
_v = SP.add(led, {"해독": "def decode(p): pass",
                  "부호화": "def encode(U,V,W,l): pass"}, parent="S1", op="쌍대")
ok(_v["등급"] == "검증가능", "해독기와 부호화기가 있으면 '검증가능' 으로 표시한다")
ok(SP.get(led, r["id"]) is not None, "그래도 원장에는 남는다 (다음 세대의 부모가 된다)")
r2 = SP.add(led, {}, parent="S1", op="쌍대")
ok(SP.get(led, r2["id"]) is not None, "칸이 전부 비어도 받는다")

print("\n== 확산 두 계수 ==")
p = {"점": "랭크 1 텐서의 합", "식": "U V W 세 행렬",
     "해독": "항등 Brent 항등식", "정의역": "연속 매개변수 594", "왜": ""}
child = {"점": "랭크 1 텐서 합의 극한",
         "식": "U V W 세 행렬과 매개변수 epsilon", "해독": "epsilon 극한에서 Brent 항등식",
         "정의역": "연속 매개변수 594 에 epsilon 하나", "왜": ""}
other = {"점": "기압", "식": "헥토파스칼", "해독": "", "정의역": "연속", "왜": ""}
ok(ME.measure(child, p)["확산"], "부모를 품고 넓힌 것은 확산")
ok(not ME.measure(other, p)["확산"], "아무 관계 없는 공간은 확산이 아니다")
ok(not ME.measure(dict(p), p)["확산"], "부모를 그대로 베낀 것은 확산이 아니다")
ok(ME.measure(p, None)["씨앗"], "씨앗은 잴 것이 없다")

print("\n== 몫의 분모는 부모다 ==")
# 자식 어휘로 나누면 **새 낱말을 많이 쓴 자식이 벌을 받는다** -- 그리고 그것이 우리가
# 원하는 것이다. 분모를 부모로 바꾼 이유가 그것이다. (이 자는 판정에 안 쓴다. 두 번
# 뒤집혔고, 지금은 눈금으로만 남아 있다.)
_par = {"식": "sum_r lam_r U[(i,k),r] V[(k,j),r] W[(i,j),r] = d(k,k) d(j,j) d(i,i)",
        "점": "(U,V,W,lam) in F^{4x7}", "정의역": "F = R"}
_rich = {"식": "lim_{e->0} sum_r lam_r(e) U(e)[(i,k),r] V(e)[(k,j),r] W(e)[(i,j),r] "
               "= d(k,k) d(j,j) d(i,i) + O(e)",
         "점": "(U(e),V(e),W(e),lam(e)) in F(e)^{4x7}", "정의역": "F = R(e)"}
_lean = {"식": "sum_r lam_r U V W = d", "점": "(U,V,W,lam)", "정의역": "F = R"}
_rm, _lm = ME.measure(_rich, _par), ME.measure(_lean, _par)
# **분모를 직접 못 박는다.** 전에는 `A or B` 였는데 뒤 절(물려받음 절대 수)이 분모와
# 무관해서, 분모를 자식으로 되돌려도 초록이었다 -- 이 블록 제목이 말하는 계약이 정작
# 검사되지 않았다(2026-09-08 가짜 green 사냥).
# (몫은 소수 셋째 자리에서 반올림되므로 같은 방식으로 견준다)
_plen, _clen = len(ME._toks(_par)), len(ME._toks(_rich))
ok(_plen and _rm["몫"] == round(_rm["물려받음"] / _plen, 3),
   f"몫의 분모는 **부모** 어휘 수다 ({_rm['물려받음']}/{_plen} = {_rm['몫']})")
ok(_clen and _rm["자식몫"] == round(_rm["물려받음"] / _clen, 3),
   f"자식몫의 분모는 자식이다 ({_rm['물려받음']}/{_clen} = {_rm['자식몫']}) -- 둘이 다른 자다")
ok(_plen != _clen, "이 고정물에서 두 분모가 실제로 다르다 -- 같으면 위 둘이 못 가른다")
ok(_rm["몫"] >= _lm["몫"],
   f"**기호를 많이 더한 쪽이 안 깎인다** (부모몫 {_rm['몫']} vs {_lm['몫']})")
ok(_rm["자식몫"] < _lm["자식몫"],
   f"옛 자로는 거꾸로였다 (자식몫 {_rm['자식몫']} vs {_lm['자식몫']})")
ok(ME.measure(_par, None)["씨앗"], "씨앗은 잴 것이 없다")
ok("치수차" in _rm and "정의역바뀜" in _rm, "수로도 적어 둔다 (판정에는 안 쓴다)")

print("\n== 다시 재기 (호출 0회) ==")
led = seed_led()
for _op, _nm in (("완비화", "자리스키 닫힘"), ("매장", "비가환 군대수")):
    _r = SP.add(led, dict(_rich, 이름=_nm), parent="S1", op=_op)
    _r["잰것"] = ME.measure(_r, SP.get(led, "S1"))
_before = [x["잰것"]["확산"] for x in led["spaces"][1:]]
with tempfile.TemporaryDirectory() as d:
    _f = Path(d) / "l.json"
    SP.save(led, _f)
    import io, contextlib
    _buf = io.StringIO()
    with contextlib.redirect_stdout(_buf):
        SPR.remeasure(SP.load(_f), _f)
    ok("부모몫 분포" in _buf.getvalue(), "바닥값을 실측으로 정하라고 분포를 찍는다")
    _back = SP.load(_f)
    ok(all(x.get("계보", {}).get("부모") for x in _back["spaces"][1:]),
       "다시 재도 계보는 그대로다")
    ok([x["잰것"]["확산"] for x in _back["spaces"][1:]] == _before,
       "자를 안 바꿨으면 판정도 그대로")
    # 바닥을 올리면 판정이 바뀐다 -- 호출 없이
    _old = ME.KEEP_SHARE
    ME.KEEP_SHARE = 0.99
    with contextlib.redirect_stdout(io.StringIO()):
        SPR.remeasure(SP.load(_f), _f)
    ME.KEEP_SHARE = _old
    ok(not any(x["잰것"]["확산"] for x in SP.load(_f)["spaces"][1:]),
       "바닥을 올리면 호출 없이 판정이 다시 매겨진다")

print("\n== 이름 칸이 없다 ==")
# 두 번 다 이름에서 장식이 시작됐다 -- 1차(85개) "멀티리니어 랭크 스펙트럼"+연산자 어휘,
# 2차(50개) "행렬곱 지수 식"+수식어. 자식이 부모 이름을 못 보면 덧붙일 것도 없다.
ok("이름" not in SP.FIELDS, "칸 목록에 이름이 없다")
_p2 = {"식": "sum_r lam_r U V W = d", "점": "(U,V,W,lam)", "정의역": "F = R"}
_pr = SPR.prompt(_p2, [("쌍대", "화살표를 뒤집는다", 1)])
ok("이름" not in _pr.split("연산자 :")[0], "부모를 보여 줄 때 이름을 안 싣는다")
ok("오로지 수학적 기호만" in _pr, "**식 칸은 기호만 받는다**")
ok("전달되지 않는다" in _pr, "`왜` 는 사람이 읽는 칸이고 다음 세대에 안 넘어간다")

print("\n== 카드 ==")
led = seed_led()
_c = SP.add(led, dict(_rich), parent="S1", op="경계화")
_c["잰것"] = ME.measure(_c, SP.get(led, "S1"))
import io as _io, contextlib as _ctx
_b = _io.StringIO()
with _ctx.redirect_stdout(_b):
    _rc = SPR.card(led, _c["id"])
_out = _b.getvalue()
# `A and B or A` 는 A 다 -- 2026-09-08 가짜 green 사냥에서 내가 넣은 것이 걸렸다.
ok(_rc == 0 and "lim_{e->0}" in _out, "카드가 자식의 식을 펼친다")
ok("--- 부모" in _out and "lam_r" in _out,
   "부모의 식도 같이 보여 준다 -- 견주려고 있는 것이다")
ok("계보:" in _out and "S1" in _out, "계보 사슬도 적는다")
with _ctx.redirect_stdout(_io.StringIO()):
    ok(SPR.card(led, "S999") == 1, "없는 공간은 1 로 끝난다")

print("\n== LaTeX 이 JSON 을 깨는 것 ==")
# 실측 2026-09-07: 식을 기호로 받기 시작하자 다섯 묶음 중 하나를 통째로 잃었다(20%).
# `\lambda` 는 JSON 파서에게 "잘못된 이스케이프" 다. 모델에게 역슬래시를 두 번 쓰라고
# 시키지 않는다 -- 그건 프롬프트를 사양서로 만드는 길이고 이미 한 번 데었다. 읽는 쪽에서 고친다.
_tex = ('```json\n[{"연산자":"\uc30d\ub300","\uc2dd":"\\lim_{N \\to \\infty} \\sup \\left\\{ m \\right\\}"},'
        ' {"연산자":"\ub9e4\uc7a5","\uc2dd":"\\sum_r \\lambda_r \\rho(U_r) \\frac{1}{n} \\beta \\nabla \\theta"}]\n```')
_got = SPR.objects(_tex)
ok(len(_got) == 2, f"LaTeX 묶음을 건진다 ({len(_got)}개)")
ok(_got and "\\to" in _got[0]["식"] and "\\sup" in _got[0]["식"],
   r"**`\to` 가 탭이 되지 않는다** -- \t \b \f \n \r 은 LaTeX 명령의 머리이기도 하다")
ok(_got and all(c in _got[1]["식"] for c in (r"\rho", r"\frac", r"\beta", r"\nabla", r"\theta")),
   r"\rho \frac \beta \nabla \theta 가 다 살아 있다")
ok(SPR.objects('[{"a":"x\\ty","b":"\\u0041"}]') == [{"a": "x\ty", "b": "A"}],
   "제대로 이스케이프된 JSON 은 안 건드린다  ← 평범한 파싱이 먼저 간다")

print("\n== 연산자가 식에 무엇을 했나 ==")
_led = seed_led()
_e = r"\lim_{N \to \infty} \inf \left\{ m \in \mathbb{N} \mid R(n) \le m \right\}"
_pa = SP.add(_led, {"식": _e, "점": "(U,V,W,lam)", "정의역": "F = R"}, parent="S1", op="완비화")
_ch = SP.add(_led, {"식": _e.replace(r"\inf \left", r"\sup \left"), "점": "(U,V,W,lam)",
                    "정의역": "F = R"}, parent=_pa["id"], op="쌍대")
_same = SP.add(_led, {"식": _e, "점": "(U,V,W,lam)", "정의역": "F = R"},
               parent=_pa["id"], op="이산화")
import io as _io3, contextlib as _ctx3


def _dtext(sid):
    _b = _io3.StringIO()
    with _ctx3.redirect_stdout(_b):
        SPR.diff(_led, sid)
    return _b.getvalue()


_d1 = _dtext(_ch["id"])
ok(r"- \inf" in _d1 and r"+ \sup" in _d1, r"바뀐 토큰만 짚는다 (\inf -> \sup)")
import re as _re3
_m3 = _re3.search(r"그대로 둔 토큰 (\d+)/(\d+)", _d1)
ok(_m3 and int(_m3.group(1)) == int(_m3.group(2)) - 1,
   f"그대로 둔 것을 센다 -- 한 토큰만 바뀌었다 ({_m3.group(0) if _m3 else '없음'})")
ok("판정이 아니다" in _d1, "**판정이 아니라고 적혀 있다**")
ok("바뀐 것이 없다" in _dtext(_same["id"]),
   "식이 글자 그대로면 연산자가 아무 일도 안 한 것이라고 말한다")
ok("씨앗이다" in _dtext("S1"), "씨앗은 견줄 부모가 없다")
ok(SPR.tokens(r"\hat{H}_*(U \otimes V)")[:3] == [r"\hat", "{", "H"],
   "낱말이 아니라 LaTeX 토큰으로 가른다")

print("\n== 연산자 ==")
ok(all(d >= 1 for _, _, d in OPS.OPS), "거리는 1 이상")
ok(OPS.JUMP and OPS.NEAR, "급발진과 한 걸음이 둘 다 있다")
ok(OPS.draw("x", 3) == OPS.draw("x", 3), "뽑기는 씨앗에 묶여 재현된다")
seen = {OPS.draw("x", i)[0] for i in range(200)}
ok(len(seen) >= 8, f"뽑기가 한쪽으로 안 쏠린다 (본 연산자 {len(seen)}개)")

print("\n== 가짜 모델로 한 바퀴 ==")
CALLS = []


def fake(p):
    CALLS.append(p)
    n = len(CALLS)
    return ("```json\n" + json.dumps({
        "식": f"S{n}: sum_r lam_r U V W = d", "점": "(U,V,W,lam)",
        "식": "U V W 세 행렬과 새 매개변수", "해독": "Brent 항등식으로 되돌린다",
        "정의역": "연속", "왜": "그럴듯하다"}, ensure_ascii=False) + "\n```")


led = seed_led()
made = [SPR.one(led, fake, seed="t", n=i, log=lambda *a: None) for i in range(6)]
ok(all(m is not None for m in made), "여섯 걸음이 전부 원장에 올랐다")
ok(all(m["계보"]["부모"] for m in made if m), "모든 공간이 부모를 갖는다")
ok(len(CALLS) == 6, "호출은 걸음당 한 번")
ok("연산자" in CALLS[0] and "부모 식을 부정하지 마라" in CALLS[0],
   "프롬프트에 연산자와 인과 규칙이 실린다")
ok("decode(p)" in CALLS[0] and "선택 칸" in CALLS[0],
   "코드 칸은 **선택**이다 -- 없다고 벌점 없다")
ok("검사한다" not in CALLS[0] and "하드코딩" not in CALLS[0],
   "**심판 얘기가 프롬프트에 없다** -- 보여 주면 원고가 관문에 맞춰 균질해진다")
last = made[-1]["id"]
ok(SP.lineage(led, last)[0] == "S1", "계보가 씨앗까지 사슬로 이어진다")

print("\n== 깨진 응답 ==")
ok(SPR.one(led, lambda p: "미안, JSON 은 못 준다", seed="t", n=0,
           log=lambda *a: None) is None, "JSON 이 아니면 건너뛴다")


def boom(p):
    raise RuntimeError("쿼터")


ok(SPR.one(led, boom, seed="t", n=0, log=lambda *a: None) is None, "호출이 터지면 건너뛴다")

print("\n== 묶어 부르기 ==")
CALLS2 = []


def fake_batch(p):
    CALLS2.append(p)
    ops = [ln.split(":")[0].strip(" ·") for ln in p.splitlines() if ln.startswith("  · ")]
    body = [{"연산자": o, "식": f"{o}: sum_r lam_r U V W = d(k) d(j) d(i)",
             "점": "(U,V,W,lam) in F^{4x7}", "정의역": "F = R",
             "해독": "def decode(p): pass", "왜": "그럴듯하다"} for o in ops]
    return "```json\n" + json.dumps(body, ensure_ascii=False) + "\n```"


led = seed_led()
got = SPR.step(led, fake_batch, seed="t", n=0, k=5, log=lambda *a: None)
ok(len(got) == 5, f"호출 한 번에 다섯 개 ({len(got)}개)")
ok(len(CALLS2) == 1, "호출은 한 번뿐")
ok(len({g["계보"]["연산자"] for g in got}) == 5, "연산자가 다섯 다 다르다")
ok(all(g["계보"]["부모"] == "S1" for g in got), "다섯 다 같은 부모에서 나왔다")
ok(all(g["계보"]["연산자"] in g["식"] for g in got), "연산자 이름으로 짝이 맞았다")

print("\n== 묶음이 깨져도 건진다 ==")
half = ('앞말 [{"연산자":"쌍대","이름":"A","해독":"돌아간다"}, {깨짐, '
        '{"연산자":"망각","이름":"B","해독":"돌아간다"}]')
ok(len(SPR.objects(half)) == 2, f"중괄호 덩어리를 낱낱이 건진다 ({len(SPR.objects(half))}개)")
led = seed_led()
got = SPR.step(led, lambda p: half, seed="t", n=0, k=5, log=lambda *a: None)
ok(len(got) == 2, "다섯 중 둘만 와도 둘은 원장에 오른다")
ok(all(g["계보"]["부모"] == "S1" for g in got), "건진 것도 계보가 온전하다")

print("\n== 순서가 어긋나도 부모-연산자가 안 뒤틀린다 ==")
led = seed_led()
picks = SPR._pick_ops(led, "t", 0, 3)
mixed = json.dumps([{"연산자": picks[2][0], "해독": "돌아간다"},
                    {"연산자": picks[0][0], "해독": "돌아간다"}],
                   ensure_ascii=False)
got = SPR.step(led, lambda p: mixed, seed="t", n=0, k=3, log=lambda *a: None)
ok([g["계보"]["연산자"] for g in got] == [picks[2][0], picks[0][0]],
   "적어 온 연산자대로 붙는다 (순서로 밀어 넣지 않는다)")

print("\n== 연산자 뽑기 ==")
led = seed_led()
pk = SPR._pick_ops(led, "t", 0, 8)
ok(len(pk) == 8 and len({x[0] for x in pk}) == 8, "한 묶음 안에서 연산자가 안 겹친다")
ok(len(SPR._pick_ops(led, "t", 0, 99)) == len(OPS.OPS), "목록보다 많이 달라면 있는 만큼만")

print("\n== 저장/복원 ==")
with tempfile.TemporaryDirectory() as d:
    f = Path(d) / "l.json"
    SP.save(led, f)
    back = SP.load(f)
    ok(len(back["spaces"]) == len(led["spaces"]), "원장이 그대로 돌아온다")
    # **없는 파일은 빈 원장이 아니라 씨앗이다.** 원장을 추적에서 빼면서 계약이 바뀌었다 --
    # 빈 원장으로는 발산이 못 시작하므로, 없으면 씨앗에서 세운다.
    ok([x["id"] for x in SP.load(Path(d) / "없다.json")["spaces"]] == ["S1"],
       "없는 파일은 씨앗에서 세운다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    raise SystemExit(1)
print("전부 통과")
