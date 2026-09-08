"""단조량 배선 검사. **LLM 도 네트워크도 안 쓴다.**

무엇을 재는가:
  · 정의역 등급이 **기호**에서 나오는가 (한국어를 보면 0 이다 -- 낱말로 재지 않는다)
  · 제약수가 `a <= b` 를 한 번 세는가 (처음에 0 이었다)
  · `검산m` 이 **왕복이 통과했을 때만** 값을 갖는가 -- 넷 중 이것만 정리다
  · 방향 선언과 어긋난 걸음을 짚되 **기각하지 않는가** (게이트가 아니다)
  · 방향을 모르는 연산자가 아무 것도 주장하지 않는가 (매장 · 쌍대 · 점근화)
  · 사슬 전체에서 단조/오르내림/그대로/모름이 갈리는가
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mathdrift import mono as MO
from mathdrift import space as SP

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def grab(fn, *a, **kw):
    b = io.StringIO()
    with contextlib.redirect_stdout(b):
        rc = fn(*a, **kw)
    return rc, b.getvalue()


print("== 정의역 등급은 기호에서 나온다 ==")
ok(MO.domain_grade(r"F = \mathbb{R}") == 3, r"\mathbb{R} 은 연속 (3)")
ok(MO.domain_grade(r"F = \mathbb{Z}") == 2, r"\mathbb{Z} 는 이산무한 (2)")
ok(MO.domain_grade(r"F = F_2") == 1, "F_2 는 유한 (1)")
ok(MO.domain_grade(r"\mathbb{F}_q, \ \mathrm{char} = p") == 1,
   r"\mathbb{F}_q 도 유한 -- 유한을 먼저 본다")
# **이것이 이 자의 계약이다.** 낱말로 재면 두 번 뒤집혔던 그 자리로 돌아간다.
ok(MO.domain_grade("연속이다. 매개변수 594개") == 0,
   "**한국어로 '연속' 이라고 써도 0 이다** -- 기호가 아니면 모른다고 한다")
ok(MO.domain_grade("") == 0, "빈 칸도 0")
ok(MO.domain_grade(r"\mathbb{Z}/p\mathbb{Z}") == 1,
   r"\mathbb{Z}/p 는 이산이 아니라 유한이다 -- 순서가 뒤집히면 안 된다")

print("\n== 제약수 ==")
ok(MO.constraints("a = b") == 1, "= 하나")
ok(MO.constraints("a <= b") == 1,
   "**`a <= b` 는 1 이다** -- 처음에 `<` 와 `=` 를 둘 다 건너뛰어 0 이었다")
ok(MO.constraints(r"a \le b") == 1, r"\le 도 1")
ok(MO.constraints("a != b") == 1, "!= 도 1 (두 번 안 센다)")
ok(MO.constraints(r"\forall i, \ a = b, \ c \le d") == 3, r"\forall + = + \le = 3")
ok(MO.constraints(r"m \in \mathbb{N}") == 0,
   r"**`\in` 은 안 센다** -- 자료형을 말하는 자리라 세면 문법을 세게 된다")
ok(MO.constraints("") == 0, "빈 식은 0")

print("\n== 넷 중 하나만 정리다 ==")
_pass = {"재현": {"판정": "재현", "시금석": "strassen b=2 m=7"}}
_fail = {"재현": {"판정": "틀림", "시금석": "strassen b=2 m=7"}}
ok(MO.quants(_pass)["검산m"] == 7, "왕복이 통과하면 검산m 이 선다 (7)")
ok(MO.quants(_fail)["검산m"] is None, "**틀림이면 값이 없다** -- 통과했을 때만이다")
ok(MO.quants({})["검산m"] is None, "왕복을 안 돌렸으면 값이 없다")
# 상수를 정리인 척 돌려주던 자리 -- `got.get("m") or 7` 이면 시금석이 b=3 으로 바뀌어도
# 7 이 그대로 남는다. 원장이 적어 둔 시금석에서 읽는다.
ok(MO.quants({"재현": {"판정": "재현", "시금석": "strassen b=3 m=23"}})["검산m"] == 23,
   "**시금석이 바뀌면 검산m 도 바뀐다** -- 7 을 박아 두지 않는다")
ok(MO.quants({"재현": {"판정": "재현"}})["검산m"] is None,
   "시금석이 안 적혀 있으면 모른다고 한다 (7 로 채우지 않는다)")
_q = MO.quants({"치수": 91, "정의역": r"F = \mathbb{R}", "식": "a = b"})
ok(_q["치수"] == 91 and _q["정의역등급"] == 3 and _q["제약수"] == 1,
   f"나머지 셋은 적어 낸 것을 센다 ({_q['치수']} · {_q['정의역등급']} · {_q['제약수']})")
ok(MO.quants({"치수": "아흔하나"})["치수"] is None, "수가 아니면 치수도 모른다")


def led_of(*rows):
    """(id 는 자동) 씨앗 하나 + 이어 붙인 걸음들."""
    led = SP.blank()
    SP.add(led, {"식": r"\sum_r \lambda_r U V W = \delta", "점": r"(U,V,W,\lambda)",
                 "정의역": r"F = \mathbb{R}", "치수": 91}, parent="-", op="씨앗", dist=0)
    prev = "S1"
    for op, rec in rows:
        prev = SP.add(led, rec, parent=prev, op=op)["id"]
    return led, prev


print("\n== 선언대로 갔나 ==")
_led, _end = led_of(("이산화", {"식": r"\sum_r \lambda_r U V W = \delta",
                               "정의역": r"F = \mathbb{Z}", "치수": 91}),
                    ("표수 이동", {"식": r"\sum_r \lambda_r U V W = \delta",
                                  "정의역": r"F = F_2", "치수": 91}))
_rows = MO.chain(_led, _end)
ok(len(_rows) == 2, f"사슬이 두 걸음으로 펴진다 ({len(_rows)}걸음)")
ok([r["연산자"] for r in _rows] == ["이산화", "표수 이동"],
   "걸음마다 **자식의** 연산자가 붙는다")
ok(_rows[0]["칸"]["정의역등급"]["전"] == 3 and _rows[0]["칸"]["정의역등급"]["후"] == 2,
   "이산화가 연속(3)에서 이산무한(2)으로 내렸다")
ok(_rows[0]["칸"]["정의역등급"]["움직임"] == -1, "움직임이 -1 로 적힌다")
ok(not any(r["칸"][k]["어긋남"] for r in _rows for k in r["칸"]),
   "선언대로 갔으면 어긋남이 없다")
ok(MO.monotone(_rows, "정의역등급") == "단조↓",
   "**사슬 전체가 한 방향이면 단조↓** -- 이것이 있어야 궤적이다")
ok(MO.monotone(_rows, "치수") == "그대로", "안 움직인 양은 '그대로'")
ok(MO.monotone(_rows, "검산m") == "모름", "왕복을 안 돌린 양은 '모름' -- 그대로와 다르다")

print("\n== 정의역은 이제 연산자가 정한다 (선언이 아니라 문법) ==")
# 모델이 세 걸음 내내 `F = \mathbb{R}` 이라고 써도 사슬의 등급은 연산자 열을 따라간다.
# 선언이면 어길 수 있지만 문법이면 어길 수가 없다 -- `space.add` 가 부모 없는 공간을
# 아예 못 받는 것과 같은 수다.
_g, _gend = led_of(("이산화", {"식": "a = b", "정의역": r"F = \mathbb{R}", "치수": 91}))
_g2 = SP.add(_g, {"식": "a = b", "정의역": r"F = \mathbb{R}", "치수": 91},
             parent=_gend, op="표수 이동")
ok([SP.get(_g, i)["정의역등급"] for i in SP.lineage(_g, _g2["id"])] == [3, 2, 1],
   "모델이 내내 R 이라고 써도 등급은 3 -> 2 -> 1 로 간다  ← 연산자 열이 궤적을 정한다")
ok(SP.get(_g, _gend)["정의역_적힘"] == 3,
   "**글자에서 읽은 등급은 안 지운다** -- `정의역_적힘` 에 따로 남는다")
ok(SP.get(_g, _gend)["정의역_연산자가정함"] is True, "연산자가 정했다고 표가 붙는다")
_r_fix = MO.chain(_g, _g2["id"])
ok(all(r["칸"]["정의역등급"]["선언"] is None for r in _r_fix),
   "**연산자가 정한 칸에는 선언이 없다** -- 견줄 일이 아니라 문법이다")
ok(not any(r["칸"]["정의역등급"]["어긋남"] for r in _r_fix),
   "그래서 어긋남이 설 수가 없다")
ok(MO.monotone(_r_fix, "정의역등급") == "단조↓", "사슬이 단조↓ 로 간다")
# 정하지 않는 연산자는 예전 그대로다 -- 억지로 채우지 않았다
_free = led_of(("매장", {"식": "a = b", "정의역": r"F = \mathbb{F}_2", "치수": 91}))[0]
ok(SP.get(_free, "S2")["정의역등급"] == 1 and not SP.get(_free, "S2")["정의역_연산자가정함"],
   "매장은 정의역을 안 정한다 -- 글자에서 읽는다")

print("\n== 어긋난 걸음을 짚는다 (기각하지 않는다) ==")
# 정의역은 이제 문법이라 어긋날 수가 없다. 아직 **선언**인 칸으로 잰다.
_led2, _end2 = led_of(("탈범주화", {"식": "a = b", "정의역": r"F = \mathbb{R}", "치수": 91}))
_r2 = MO.chain(_led2, _end2)[0]
ok(_r2["칸"]["치수"]["움직임"] == 0 and not _r2["칸"]["치수"]["어긋남"],
   "안 움직인 것은 어긋남이 아니다 -- 연산자가 그 양을 안 건드린 것이다")
_led3, _end3 = led_of(("탈범주화", {"식": "a = b", "정의역": r"F = \mathbb{R}", "치수": 200}))
_r3 = MO.chain(_led3, _end3)
ok(_r3[0]["칸"]["치수"]["움직임"] == 1 and _r3[0]["칸"]["치수"]["선언"] == "↓",
   "탈범주화라고 해 놓고 치수가 91 에서 200 으로 늘었다")
ok(_r3[0]["칸"]["치수"]["어긋남"], "**반대로 간 걸음에 어긋남이 선다**")
ok(len(_led3["spaces"]) == 2 and SP.get(_led3, _end3) is not None,
   "**그래도 원장에 그대로 있다** -- 단조량은 게이트가 아니다")
_rc, _out = grab(MO.show, _led3, _end3)
ok(_rc == 0, "어긋난 사슬을 보여 줘도 0 으로 끝난다 (실패가 아니다)")
ok("어긋난 걸음" in _out and "!" in _out, "어긋난 자리를 찍어 준다")
ok("부기이지 정리가 아니다" in _out,
   "**부기라고 적혀 있다** -- 선언대로 갔다는 것이 그 양이 단조라는 증명은 아니다")
ok("점근 스펙트럼" in grab(MO.report, _led3)[1],
   "진짜로 하려면 무엇이 있어야 하는지도 적어 둔다 (Strassen)")

print("\n== 한 걸음에서 둘이 동시에 어긋난다 ==")
_led4, _end4 = led_of(("대칭성 강제", {"식": r"m \in \mathbb{N}",
                                      "정의역": r"F = \mathbb{R}", "치수": 200}))
_r4 = MO.chain(_led4, _end4)[0]
ok(_r4["칸"]["제약수"]["선언"] == "↑" and _r4["칸"]["치수"]["선언"] == "↓",
   "대칭성 강제는 두 양에 방향을 선언한다")
ok(_r4["칸"]["치수"]["어긋남"], "치수가 91 -> 200 으로 늘어서 어긋났다")
ok(_r4["칸"]["제약수"]["움직임"] is None,
   r"자식 식에 관계 기호가 없어(`\in` 은 안 센다) 제약수는 모른다 -- 어긋남도 아니다")
ok(not _r4["칸"]["제약수"]["어긋남"], "**모르는 것으로는 어긋났다고 하지 않는다**")

print("\n== 방향을 모르는 연산자는 아무 것도 주장하지 않는다 ==")
for _op in ("매장", "쌍대", "점근화"):
    _l, _e = led_of((_op, {"식": "a = b < c", "정의역": r"F = F_2", "치수": 4}))
    _rr = MO.chain(_l, _e)[0]
    ok(_op not in MO.DIR and not any(_rr["칸"][k]["어긋남"] for k in _rr["칸"]),
       f"{_op} 은 선언이 없다 -- 무엇이 어디로 가도 어긋남이 안 선다")
    ok(all(_rr["칸"][k]["선언"] is None for k in _rr["칸"]), f"{_op} 의 선언 칸이 다 비어 있다")
ok(all(o not in MO.DIR for o in ("매장", "내부화", "쌍대", "점근화", "불변량 이동")),
   "**모르는 다섯은 비워 둔다** -- 억지로 채우면 자가 뒤집힌다")

print("\n== 오르내림 ==")
_led5, _end5 = led_of(("이산화", {"식": "a = b", "정의역": r"F = \mathbb{Z}", "치수": 91}),
                      ("완비화", {"식": "a = b", "정의역": r"F = \mathbb{R}", "치수": 91}))
_r5 = MO.chain(_led5, _end5)
ok(MO.monotone(_r5, "정의역등급") == "오르내림",
   "내렸다 올라간 사슬은 단조가 아니다 (3 -> 2 -> 3)")
ok(not any(r["칸"]["정의역등급"]["어긋남"] for r in _r5),
   "둘 다 제 선언대로 갔다 -- 사슬이 단조가 아닌 것과 걸음이 어긋난 것은 다른 말이다")

print("\n== 끝점과 보고 ==")
_led6 = SP.blank()
SP.add(_led6, {"식": "a = b", "정의역": r"F = \mathbb{R}", "치수": 91},
       parent="-", op="씨앗", dist=0)
_a = SP.add(_led6, {"식": "a = b", "정의역": r"F = \mathbb{Z}", "치수": 91},
            parent="S1", op="이산화")
_b2 = SP.add(_led6, {"식": "a = b", "정의역": r"F = F_2", "치수": 91},
             parent=_a["id"], op="표수 이동")
_c2 = SP.add(_led6, {"식": "a = b", "정의역": r"F = \mathbb{C}", "치수": 92},
             parent="S1", op="경계화")
ok(sorted(MO.leaves(_led6)) == sorted([_b2["id"], _c2["id"]]),
   f"자식 없는 것만 끝점이다 ({MO.leaves(_led6)})")
ok("S1" not in MO.leaves(_led6), "씨앗은 자식이 있으니 끝점이 아니다")
_rc6, _out6 = grab(MO.report, _led6)
ok(_rc6 == 0 and "사슬 2개" in _out6, f"끝점 수만큼 사슬을 센다")
ok("단조↓" in _out6, "사슬마다 궤적을 적는다")
ok("한 방향으로만 간 사슬:" in _out6, "한 방향으로 간 사슬이 몇인지 모아 준다")
ok(grab(MO.show, _led6, "S1")[1].strip().endswith("사슬이 없다"),
   "씨앗은 사슬이 없다고 말한다")
# `A and B or C` 는 C 만 참이어도 초록이다 -- 이 저장소에서 두 번 걸린 모양이라 안 쓴다.
_rc7, _out7 = grab(MO.report, SP.blank())
ok(_rc7 == 0 and "씨앗뿐이다" in _out7, "빈 원장에서도 안 터진다")

print("\n== 자르개를 자국과 나눠 쓴다 ==")
from mathdrift import act as ACT
ok(MO.ACT.tokens is ACT.tokens,
   "**단조량과 자국이 같은 자르개를 본다** -- 두 벌이면 세는 것이 갈린다")
from mathdrift import spread as SPR
ok(SPR.tokens is ACT.tokens, "발산 쪽도 같은 것을 쓴다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    raise SystemExit(1)
print("전부 통과")
