r"""**π 와 개선결정** -- 자기 발전이 검증을 지날 때만 일어나는가.

    python3 tests/test_policy.py

붙드는 것: π 가 실제로 연산자 선택에 닿나 · 후보가 결정적인가 · 한 연산자도 버리지 않나 ·
**ACCEPT 는 V 와 ΔJ 가 둘 다 설 때만인가** · 기본이 REJECT 인가 · 거절된 π 를 쓰지 않나.
"""
from __future__ import annotations

import json
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import mutate as M                                                 # noqa: E402
import policy as P                                                 # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


print("== π 의 정의역이 `변형들` 과 어긋나지 않는다 ==")
_풍부 = """def 고르기(x, y):
    if x > 100 and y:
        return x * 2
    else:
        a = 1
        return a
"""
난것 = {op for op, _s, _n, _t in M.변형들(_풍부, "고르기")}
ok(난것 <= set(M.연산자목록()),
   f"`변형들` 이 내는 연산자가 다 목록에 있다 (빠진 것 {sorted(난것 - set(M.연산자목록()))})")
ok(set(P.기본정책()["무게"]) == set(M.연산자목록()), "π0 의 무게가 연산자 전부를 덮는다")
ok(all(v == 1.0 for v in P.기본정책()["무게"].values()),
   "**π0 은 전부 1.0 이다** -- 똑똑한 π 가 아니라 공정한 π 가 먼저다")

print("\n== π 가 연산자 선택에 실제로 닿는다 ==")
목록 = [(m, "", "", frozenset()) for m in M.연산자목록()]
ok(len(M.변형뽑기(목록, None, random.Random(0))) == len(목록), "무게가 없으면 그냥 섞는다(개수 보존)")
ok({x[0] for x in M.변형뽑기(목록, {"const_num": 9.0}, random.Random(0))} == set(M.연산자목록()),
   "**한 연산자도 버리지 않는다** -- 버리면 그것이 재는 의미 변화를 영영 못 본다")
ok({x[0] for x in M.변형뽑기(목록, {m: 0.0 for m in M.연산자목록()}, random.Random(0))} == set(M.연산자목록()),
   "무게가 0 이어도 목록에는 남는다(바닥으로 올린다)")
앞 = {"무게": 0, "균등": 0}
for s in range(200):
    센 = M.변형뽑기(목록, {"cmp_boundary": 4.0, "const_return": 0.25}, random.Random(s))
    평 = M.변형뽑기(목록, None, random.Random(s))
    앞["무게"] += [x[0] for x in 센].index("cmp_boundary")
    앞["균등"] += [x[0] for x in 평].index("cmp_boundary")
ok(앞["무게"] / 200 < 앞["균등"] / 200,
   f"**무게를 준 연산자가 앞으로 온다** (평균 자리 {앞['무게']/200:.1f} < 균등 {앞['균등']/200:.1f}) "
   f"-- 시한에 잘리는 순회에서는 순서가 곧 P(m) 이다")
뒤 = sum([x[0] for x in M.변형뽑기(목록, {"cmp_boundary": 4.0, "const_return": 0.25},
                              random.Random(s))].index("const_return") for s in range(200)) / 200
균뒤 = sum([x[0] for x in M.변형뽑기(목록, None, random.Random(s))].index("const_return")
         for s in range(200)) / 200
ok(뒤 > 균뒤, f"무게를 깎은 연산자는 뒤로 간다 (평균 자리 {뒤:.1f} > 균등 {균뒤:.1f})")

print("\n== 후보는 결정적이고, 바닥·천장을 지킨다 ==")
바탕요약 = {"사냥끝": True, "씨앗": 0, "동등장치": True,
        "정책": {"이름": "pi0"},
        "연산자": {"const_num": {"잰것": 100, M.잡힘: 10, M.살아남음: 90, "초": 500.0},
                "const_return": {"잰것": 100, M.잡힘: 90, M.살아남음: 10, "초": 2000.0}},
        "칸": {f"a{i}.py|const_num": {"잰것": 10, M.잡힘: 5, M.살아남음: 5} for i in range(10)}}
후1 = P.후보만들기(바탕요약)
후2 = P.후보만들기(바탕요약)
ok(후1 == 후2, "**같은 D 를 주면 같은 π' 가 나온다** -- 무작위가 아니다")
ok(all(P.무게바닥 <= w <= P.무게천장 for w in 후1["무게"].values()),
   f"무게가 바닥·천장 안에 있다 ({sorted(후1['무게'].values())[:3]} ~ {sorted(후1['무게'].values())[-2:]})")
ok(후1["무게"]["const_num"] > 후1["무게"]["const_return"],
   f"**자주 찾고 싼 연산자가 무게를 더 받는다** (const_num {후1['무게']['const_num']} > "
   f"const_return {후1['무게']['const_return']})")
ok(set(후1["무게"]) >= {"const_num", "const_return"}, "본 연산자가 다 들어 있다")
ok(후1["이름"] == "pi1", f"π0 의 다음은 π1 이다 ({후1['이름']}) -- 자릿수를 세면 pi2 가 된다(실측으로 틀렸다)")
ok(P._번호("pi0") == 0 and P._번호("pi12") == 12 and P._번호("없음") == 0, "이름에서 번호를 읽는다")
ok(P.후보만들기(바탕요약, {"이름": "pi7", "무게": {}})["이름"] == "pi8", "π7 다음은 π8 이다")
빈후 = P.후보만들기({"연산자": {}})
ok("바꿀 근거가 없어" in 빈후["왜"], f"자료가 없으면 **그대로 둔다** ({빈후['왜'][:40]})")

print("\n== J(π) 는 칸으로 센다 -- 한 약점을 거듭 찾는 것은 하나를 찾은 것이다 ==")
한칸 = {"칸": {"a.py|const_num": {"잰것": 100, M.잡힘: 0, M.살아남음: 100}},
      "연산자": {"const_num": {"초": 3600.0}}}
열칸 = {"칸": {f"a{i}.py|const_num": {"잰것": 10, M.잡힘: 0, M.살아남음: 10} for i in range(10)},
      "연산자": {"const_num": {"초": 3600.0}}}
ok(P.J정책(한칸)["발견칸"] == 1 and P.J정책(열칸)["발견칸"] == 10,
   f"FG 100개가 한 칸이면 1 이고 열 칸이면 10 이다 ({P.J정책(한칸)['발견칸']} · {P.J정책(열칸)['발견칸']})")
ok(P.J정책(열칸)["Y"] == 10.0, f"Y = 시간당 발견칸 ({P.J정책(열칸)['Y']})")
ok(P.J정책({"칸": {"a|b": {M.살아남음: 1}}})["Y"] is None,
   "**시간을 모르면 Y 는 None 이다** -- 0 으로 채우지 않는다")

print("\n== 개선결정: ACCEPT 는 V 와 ΔJ 가 둘 다 설 때만 ==")


def 요약(초, 칸수=10, k=5, f=5, 끝=True, 씨앗=0, 장치=True):
    return {"사냥끝": 끝, "씨앗": 씨앗, "동등장치": 장치,
            "연산자": {"const_num": {"잰것": 10 * 칸수, M.잡힘: k * 칸수, M.살아남음: f * 칸수,
                                 "초": float(초)}},
            "칸": {f"a{i}.py|const_num": {"잰것": k + f, M.잡힘: k, M.살아남음: f}
                  for i in range(칸수)}}


바 = 요약(1000)
후 = 요약(500)                                    # 같은 것을 절반 시간에 찾았다
r = P.개선결정(바, 후, P.기본정책())
ok(r["결정"] == "ACCEPT" and r["ΔJ"] and r["ΔJ"] > 0,
   f"**같은 표본을 절반 시간에 찾으면 ACCEPT** (ΔJ {r['ΔJ']})")
ok(r["V"] is True and any("V 섰다" in x for x in r["까닭"]), f"V 가 섰다고 적는다 ({r['까닭'][:1]})")
r2 = P.개선결정(바, 요약(2000), P.기본정책())
ok(r2["결정"] == "REJECT" and any("문턱" in x for x in r2["까닭"]),
   f"더 느리면 REJECT ({r2['까닭'][:1]})")
r3 = P.개선결정(바, 요약(500, 끝=False), P.기본정책())
ok(r3["결정"] == "REJECT" and any("사냥을 끝내지" in x for x in r3["까닭"]),
   "시한에 잘린 표본으로는 ACCEPT 하지 않는다 -- 치우쳐 있다")
r4 = P.개선결정(바, 요약(500, 장치=False), P.기본정책())
ok(r4["결정"] == "REJECT" and any("동등 장치" in x for x in r4["까닭"]),
   "**동등 장치가 죽었으면 REJECT** -- `동등 0` 이 뜻을 못 갖는다")
r5 = P.개선결정(바, 요약(500, 씨앗=99), P.기본정책())
ok(r5["결정"] == "REJECT" and any("씨앗" in x for x in r5["까닭"]),
   "씨앗이 다르면 차이가 π 탓인지 모른다 -- REJECT")
r6 = P.개선결정(바, 요약(500, k=9, f=1), P.기본정책())
ok(r6["결정"] == "REJECT" and any("편향" in x for x in r6["까닭"]),
   f"**공통칸 점수가 어긋나면 REJECT** -- 더 빨리 찾은 것이 아니라 다른 것을 쟀다 ({r6['까닭'][:1]})")
r7 = P.개선결정(바, 요약(500, 칸수=2), P.기본정책())
ok(r7["결정"] == "REJECT", "공통칸이 적으면 편향을 못 보므로 REJECT")
ok(P.개선결정(None, 후)["결정"] == "REJECT", "요약이 없으면 REJECT -- **기본이 거절이다**")
ok(P.개선결정(바, {"사냥끝": True, "씨앗": 0, "칸": {}})["결정"] == "REJECT", "빈 후보도 REJECT")

print("\n== 거절된 π 는 쓰지 않는다 (원장은 덧붙이기만) ==")
집 = Path(tempfile.mkdtemp(prefix="test-pi-"))
ok(P.지금정책(집)["이름"] == "pi0", "원장이 없으면 π0 이다")
P.정책적기(집, 정책={"이름": "pi거절", "무게": {"const_num": 4.0}}, 결정="REJECT", 까닭=["더 느렸다"])
ok(P.지금정책(집)["이름"] == "pi0", "**REJECT 된 π 는 안 쓴다** -- 거절도 적지만 적용하지 않는다")
P.정책적기(집, 정책={"이름": "pi1", "무게": {"const_num": 2.0}}, 결정="ACCEPT", 까닭=["더 빨랐다"])
ok(P.지금정책(집)["이름"] == "pi1", "ACCEPT 된 π 를 쓴다")
ok(len(P.정책들(집)) == 2, "두 줄 다 남는다 -- 무엇을 해 보고 안 됐는지가 다음 후보의 재료다")
ok("pi1" in P.보고(집) and "REJECT" in P.보고(집), "보고가 지금 π 와 이력을 같이 찍는다")
ok("비어 있다" in P.보고(Path(tempfile.mkdtemp(prefix="빈pi-"))),
   "원장이 없으면 없다고 말한다")

print("\n== 배선 ==")
ok("policy.py" in (ROOT / ".github/workflows/deploy-oracle.yml").read_text(encoding="utf-8"),
   "배포가 policy.py 를 서버에 올린다")
ok("policy" in (ROOT / "mutate.py").read_text(encoding="utf-8"),
   "사냥이 π 를 읽는다")
ok(M._정책(집, {"이름": "주어진것"})["이름"] == "주어진것", "π 를 주면 그것을 쓴다")
ok(M._정책(집)["이름"] == "pi1", "안 주면 받아들여진 마지막 π 를 읽는다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("policy: π 의 정의역 · 선택에 닿음 · 결정적 후보 · J(π) 는 칸 · "
      "ACCEPT 는 V∧ΔJ · 기본 REJECT · 거절된 π 안 씀 -- 통과")
