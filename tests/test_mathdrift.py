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
    SP.add(led, {"이름": "텐서 랭크", "점": "랭크 1 텐서의 합",
                 "표기": "U V W 세 행렬과 계수", "되사상": "항등. Brent 항등식으로 검산",
                 "크기": "연속. 매개변수 594개", "왜": "씨앗"},
           parent="-", op="씨앗", dist=0)
    return led


print("== 인과성은 구성으로 보장된다 ==")
led = seed_led()
try:
    SP.add(led, {"이름": "남의 공간"}, parent="S99", op="망각")
    ok(False, "원장에 없는 부모를 거절한다")
except ValueError:
    ok(True, "원장에 없는 부모를 거절한다")
ok(SP.get(led, "S1") is not None, "씨앗은 부모 '-' 로 올라간다")

print("\n== 발산은 죽이지 않는다 ==")
r = SP.add(led, {"이름": "되사상 없는 공간", "점": "무엇인가"}, parent="S1", op="망각")
ok(r["등급"] == "검증불가", "되사상이 비면 기각이 아니라 등급만 '검증불가'")
ok(SP.get(led, r["id"]) is not None, "그래도 원장에는 남는다 (다음 세대의 부모가 된다)")
r2 = SP.add(led, {}, parent="S1", op="쌍대")
ok(SP.get(led, r2["id"]) is not None, "칸이 전부 비어도 받는다")

print("\n== 확산 두 계수 ==")
p = {"이름": "텐서 랭크", "점": "랭크 1 텐서의 합", "표기": "U V W 세 행렬",
     "되사상": "항등 Brent 항등식", "크기": "연속 매개변수 594", "왜": ""}
child = {"이름": "경계 랭크", "점": "랭크 1 텐서 합의 극한",
         "표기": "U V W 세 행렬과 매개변수 epsilon", "되사상": "epsilon 극한에서 Brent 항등식",
         "크기": "연속 매개변수 594 에 epsilon 하나", "왜": ""}
other = {"이름": "날씨", "점": "기압", "표기": "헥토파스칼", "되사상": "", "크기": "연속", "왜": ""}
ok(ME.measure(child, p)["확산"], "부모를 품고 넓힌 것은 확산")
ok(not ME.measure(other, p)["확산"], "아무 관계 없는 공간은 확산이 아니다")
ok(not ME.measure(dict(p), p)["확산"], "부모를 그대로 베낀 것은 확산이 아니다")
ok(ME.measure(p, None)["씨앗"], "씨앗은 잴 것이 없다")

print("\n== 몫의 분모는 부모다 ==")
_par = {"이름": "텐서 랭크", "점": "행렬곱 텐서를 랭크 1 텐서 m 개의 합으로 쓴 분해",
        "표기": "세 행렬 U V W 와 계수 lambda", "되사상": "항등 Brent 항등식으로 검산",
        "크기": "연속 실수 매개변수 594 개", "왜": ""}
_rich = {"이름": "자리스키 닫힘",
         "점": "랭크 1 텐서 합의 극한이 이루는 대수다양체의 닫힘 위의 점",
         "표기": "U V W 에 매개변수 하나를 더한 곡선",
         "되사상": "극한에서 Brent 항등식을 만족", "크기": "연속 차원이 더 크다", "왜": ""}
_lean = {"이름": "랭크 스펙트럼", "점": "분해 하나", "표기": "U V W",
         "되사상": "항등", "크기": "연속", "왜": ""}
_rm, _lm = ME.measure(_rich, _par), ME.measure(_lean, _par)
ok(_rm["확산"] and _lm["확산"], "말수가 많든 적든 부모를 품었으면 확산")
ok(_rm["몫"] >= _lm["몫"],
   f"**새 낱말을 많이 쓴 자식이 벌받지 않는다** (부모몫 {_rm['몫']} >= {_lm['몫']})")
ok(_rm["자식몫"] < _lm["자식몫"],
   f"옛 자로는 거꾸로였다 (자식몫 {_rm['자식몫']} < {_lm['자식몫']})  ← 이것이 고친 이유")
ok(not ME.measure(other, _par)["확산"], "무관한 공간은 새 자로도 확산이 아니다")

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
        "이름": f"공간 {n}", "점": "랭크 1 텐서의 합에 조건 하나",
        "표기": "U V W 세 행렬과 새 매개변수", "되사상": "Brent 항등식으로 되돌린다",
        "크기": "연속", "왜": "그럴듯하다"}, ensure_ascii=False) + "\n```")


led = seed_led()
made = [SPR.one(led, fake, seed="t", n=i, log=lambda *a: None) for i in range(6)]
ok(all(m is not None for m in made), "여섯 걸음이 전부 원장에 올랐다")
ok(all(m["계보"]["부모"] for m in made if m), "모든 공간이 부모를 갖는다")
ok(len(CALLS) == 6, "호출은 걸음당 한 번")
ok("연산자" in CALLS[0] and "부모를 지우지 마라" in CALLS[0], "프롬프트에 연산자와 인과 규칙이 실린다")
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
    body = [{"연산자": o, "이름": f"{o} 공간", "점": "랭크 1 텐서의 합에 조건 하나",
             "표기": "U V W 세 행렬과 새 매개변수", "되사상": "Brent 항등식으로 되돌린다",
             "크기": "연속", "왜": "그럴듯하다"} for o in ops]
    return "```json\n" + json.dumps(body, ensure_ascii=False) + "\n```"


led = seed_led()
got = SPR.step(led, fake_batch, seed="t", n=0, k=5, log=lambda *a: None)
ok(len(got) == 5, f"호출 한 번에 다섯 개 ({len(got)}개)")
ok(len(CALLS2) == 1, "호출은 한 번뿐")
ok(len({g["계보"]["연산자"] for g in got}) == 5, "연산자가 다섯 다 다르다")
ok(all(g["계보"]["부모"] == "S1" for g in got), "다섯 다 같은 부모에서 나왔다")
ok(all(g["계보"]["연산자"] in g["이름"] for g in got), "연산자 이름으로 짝이 맞았다")

print("\n== 묶음이 깨져도 건진다 ==")
half = ('앞말 [{"연산자":"쌍대","이름":"A","되사상":"돌아간다"}, {깨짐, '
        '{"연산자":"망각","이름":"B","되사상":"돌아간다"}]')
ok(len(SPR.objects(half)) == 2, f"중괄호 덩어리를 낱낱이 건진다 ({len(SPR.objects(half))}개)")
led = seed_led()
got = SPR.step(led, lambda p: half, seed="t", n=0, k=5, log=lambda *a: None)
ok(len(got) == 2, "다섯 중 둘만 와도 둘은 원장에 오른다")
ok(all(g["계보"]["부모"] == "S1" for g in got), "건진 것도 계보가 온전하다")

print("\n== 순서가 어긋나도 부모-연산자가 안 뒤틀린다 ==")
led = seed_led()
picks = SPR._pick_ops(led, "t", 0, 3)
mixed = json.dumps([{"연산자": picks[2][0], "이름": "뒤엣것 먼저", "되사상": "돌아간다"},
                    {"연산자": picks[0][0], "이름": "앞엣것 나중", "되사상": "돌아간다"}],
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
    ok(SP.load(Path(d) / "없다.json")["spaces"] == [], "없는 파일은 빈 원장")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    raise SystemExit(1)
print("전부 통과")
