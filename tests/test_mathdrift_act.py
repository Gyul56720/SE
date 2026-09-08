r"""연산자의 자국을 **기호로** 찾는가 -- LLM 도 네트워크도 안 쓴다.

이 자가 있는 이유. 낱말 겹침 자는 두 번 뒤집혔다(실측 2026-09-07):

    1차(85개)  부모 이름 "멀티리니어 랭크 스펙트럼" + 연산자 어휘가 최고점
    2차(50개)  식으로 바꿨는데 장식이 식 쪽으로 따라왔다 -- 0.933 이 최고점이고
               ε-근사(경계 랭크) · 그로텐디크가 0 으로 깔렸다

원인은 하나였다: **연산자가 무슨 일을 했는지를 한국어로 물었다.** 기호로 물으면 그 문제가
사라진다 -- 경계화면 `\lim`, 국소화면 `S^{-1}`, 쌍대면 `\inf` -> `\sup`.

무엇을 고정하나:
  · 더한 쪽과 뺀 쪽을 **둘 다** 본다 (쌍대는 \sup 을 더하면서 \inf 를 뺀다)
  · 식이 글자 그대로면 자국이 없다고 말한다
  · 자국을 안 정한 연산자(망각)는 **미정**이지 없음이 아니다
  · **한국어를 아무리 써도 자국이 안 생긴다** -- 이 자가 낱말로 돌아가지 않는다는 증거
  · 아무것도 거르지 않는다 (원장을 안 바꾼다)
"""
from __future__ import annotations

import io
import contextlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mathdrift import act as ACT
from mathdrift import measure as ME
from mathdrift import space as SP
from mathdrift import spread as SPR

fails = []


def ok(cond, what):
    print(("    OK   " if cond else "    실패 ") + what)
    if not cond:
        fails.append(what)


print("[자국] **기호로 묻는다** -- diff 의 더한 쪽과 뺀 쪽을 둘 다 본다")
_m = ACT.marks([r"\sup"], [r"\inf"], "쌍대")
ok(_m["판정"] == "있음", "쌍대: \\inf -> \\sup 은 자국이다")
ok("+\\sup" in _m["자국"] and "-\\inf" in _m["자국"],
   f"더한 것과 뺀 것을 둘 다 짚는다 ({_m['자국']})")
ok(ACT.marks(["S", "^", "{", "-", "1", "}"], [], "국소화")["판정"] == "있음",
   "국소화: S^{-1} 은 자국이다")
ok(ACT.marks([r"\widehat", r"\varprojlim"], [], "완비화")["판정"] == "있음",
   "완비화: \\widehat · \\varprojlim 은 자국이다")
ok(ACT.marks([r"\epsilon", r"\lim"], [], "경계화")["판정"] == "있음",
   "경계화: \\epsilon · \\lim 은 자국이다")

print()
print("[없음과 미정은 다르다]")
ok(ACT.marks([], [], "완비화")["판정"] == "없음", "식이 글자 그대로면 자국이 없다")
ok("글자 그대로" in ACT.marks([], [], "완비화")["왜"], "왜 없는지 말한다")
ok(ACT.marks(["x", "+", "1"], [], "경계화")["판정"] == "없음",
   "바뀌었지만 그 연산자의 자국이 아니면 없음")
_u = ACT.marks([r"\mathcal", "C"], [], "망각")
ok(_u["판정"] == "미정", "**망각은 미정이다** -- 구조가 없어지는 것이라 자국을 안 정했다")
ok("망각" not in ACT.SIGNS, "자국 목록에 망각이 없다 (억지로 채우면 자가 또 뒤집힌다)")
ok(ACT.marks([r"\sup"], [], "없는연산자")["판정"] == "미정", "모르는 연산자는 미정")

print()
print("[낱말로 돌아가지 않는다] **이 자가 뒤집혔던 그 자리다**")
# 한국어를 아무리 써도 자국이 안 생겨야 한다. 토큰이 한글이면 SIGNS 의 어떤 조각과도
# 안 맞기 때문이다 -- 1·2차에서 자를 뒤집은 것이 정확히 이 낱말들이었다.
_ko = ACT.marks(["순환", "대칭", "불변", "행렬곱", "지수", "식"], [], "대칭성 강제")
ok(_ko["판정"] == "없음",
   f"'순환 대칭 불변' 이라고 한국어로 써도 자국이 아니다 ({_ko['자국']})")
_ko2 = ACT.marks(["경계", "랭크", "근사"], [], "경계화")
ok(_ko2["판정"] == "없음", "'경계 랭크 근사' 라고 써도 자국이 아니다")
ok(ACT.marks([r"\epsilon"], [], "경계화")["판정"] == "있음",
   "같은 뜻을 기호로 쓰면(\\epsilon) 자국이다  ← 낱말이 아니라 토큰을 본다")

print()
print("[원장 훑기] 호출 0회, 아무것도 안 거른다")
_led = SP.load(SP.SEED)
_E = r"\lim_{N \to \infty} \inf \left\{ m \in \mathbb{N} \mid R(n) \le m \right\}"
_pa = SP.add(_led, {"식": _E, "점": "(U,V,W,lam)", "정의역": "F = R"}, parent="S1", op="점근화")
_pa["잰것"] = ME.measure(_pa, SP.get(_led, "S1"))
for _expr, _op in ((_E.replace(r"\inf \left", r"\sup \left"), "쌍대"),
                   ("S^{-1} " + _E, "국소화"),
                   (_E, "이산화"),
                   (_E, "망각")):
    _r = SP.add(_led, {"식": _expr, "점": "(U,V,W,lam)", "정의역": "F = R"},
                parent=_pa["id"], op=_op)
    _r["잰것"] = ME.measure(_r, _pa)

_before = [dict(x) for x in _led["spaces"]]
_b = io.StringIO()
with contextlib.redirect_stdout(_b):
    _rc = SPR.act(_led)
_out = _b.getvalue()
ok(_rc == 0 and "자국 있음" in _out, "원장 전체를 훑는다")
ok("S3" in _out and "쌍대" in _out, "공간마다 한 줄")
ok("연산자별" in _out, "연산자별로 센다 -- 연산자가 일을 하고 있는가")
ok("판정이 아니라 눈금이다" in _out, "**판정이 아니라고 적혀 있다**")
ok(_led["spaces"] == _before, "훑기가 원장을 한 글자도 안 바꾼다")

with tempfile.TemporaryDirectory() as _d:
    _f = Path(_d) / "seed_only.json"
    ok(SPR.act(SP.load(_f)) == 0, "씨앗뿐이면 견줄 것이 없다고 말하고 끝난다")

print()
print("[diff 에도 실린다]")
_b2 = io.StringIO()
with contextlib.redirect_stdout(_b2):
    SPR.diff(_led, "S3")
ok("자국 있음: +\\sup -\\inf" in _b2.getvalue(),
   "diff 가 바뀐 토큰과 자국을 함께 보여 준다")

print()
print("[세기] 미정은 분모에서 뺀다")
_t = ACT.tally([("쌍대", {"판정": "있음"}), ("쌍대", {"판정": "없음"}),
                ("망각", {"판정": "미정"})])
ok("1/2" in _t, f"판정한 것만 분모에 넣는다 ({_t.strip()!r})")
ok("미정" in _t, "미정만 있는 연산자는 미정으로 적는다")

print()
if fails:
    print(f"mathdrift 자국: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("mathdrift 자국: 기호 · 없음/미정 · 낱말 안 봄 · 원장 훑기 · diff · 세기 -- 통과")
