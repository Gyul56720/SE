"""Verified Improvement Loop(Phase 2)을 붙든다. 생성·검증·평가를 **주입**해 루프의 논리만 잰다.

사용자(2026-09-12):

    P_t -> Generate(P'_1..P'_n) -> V(P'_i) -> J(P_t, P'_i) -> Select -> P_{t+1}
    채택:  argmax ΔJ   단,  V(P')=PASS  ∧  ΔJ > ε

붙드는 것:
  1. V 를 못 지난 후보는 **J 가 가장 높아도** 안 고른다
  2. ΔJ ≤ ε 이면 채택하지 않는다 (아무것도 나아지지 않은 채 커밋이 쌓이는 것을 막는다)
  3. ε 를 올리면 작은 개선은 안 받는다
  4. 동점이면 먼저 온 것 (흔들지 않는다)
  5. 원장에 사양의 칸이 다 남는다: P_t · P' · V · J · ΔJ · hypothesis · cost · result
  6. 버린 후보도 **왜 버렸는지**와 함께 남는다 (그것이 π 의 재료다)
  7. 여러바퀴는 채택한 것을 새 P_t 로 삼고, 채택이 없으면 멈춘다(멈춤은 실패가 아니라 측정이다)

실행: python3 tests/test_improveloop.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import improveloop as L  # noqa: E402

FAIL: list = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


판 = Path(tempfile.mkdtemp(prefix="test-loop-"))
try:
    점수: dict = {}

    def 판만들기(이름: str) -> Path:
        p = Path(tempfile.mkdtemp(prefix=f"후보-{이름}-"))
        점수[str(p)] = 0.0
        return p

    def J자(P, X=None, Θ=None, R=None):
        return {"Y": 점수.get(str(P), 0.0), "칸": {"관찰파일수": int(점수.get(str(P), 0.0))}}

    def 후보들만들기(값들: dict) -> list:
        out = []
        for 이름, 값 in 값들.items():
            p = 판만들기(이름)
            점수[str(p)] = 값
            out.append({"이름": 이름, "판": p, "가설": f"{이름} 가설"})
        return out

    점수[str(판)] = 0.0

    print("== 1~2. V 를 못 지난 후보는 J 가 최고여도 안 고르고, ΔJ > ε 만 채택한다 ==")
    후 = 후보들만들기({"가": 1.0, "나": 9.0, "다": 5.0})
    r = L.한바퀴(판, 생성자=lambda P: 후, V자=lambda x: (x["이름"] != "나", "V 빨강(나)"),
              J자=J자, 원장저장소=판)
    ok(r["고른것"]["이름"] == "다", f"**V 를 못 지난 '나'(J 9.0)를 안 고르고 '다'(5.0)를 골랐다** ({r['고른것']['이름']})")
    ok([x["이름"] for x in r["막힌것"]] == ["나"], "막힌 후보를 따로 적는다")
    ok(abs(r["ΔJ"] - 5.0) < 1e-9, f"ΔJ = {r['ΔJ']}")

    print("\n== 3. ΔJ 가 ε 를 안 넘으면 채택하지 않는다 ==")
    후2 = 후보들만들기({"라": 0.0, "마": -2.0})
    r2 = L.한바퀴(판, 생성자=lambda P: 후2, V자=lambda x: (True, ""), J자=J자, 원장저장소=판)
    ok(r2["고른것"] is None and "ΔJ > ε" in r2["왜"],
       f"**V 는 지났지만 나아지지 않았으면 안 받는다** ({r2['왜'][:60]})")
    후3 = 후보들만들기({"바": 0.5})
    r3 = L.한바퀴(판, 생성자=lambda P: 후3, V자=lambda x: (True, ""), J자=J자, ε=1.0, 원장저장소=판)
    ok(r3["고른것"] is None, "ε=1.0 이면 +0.5 개선은 안 받는다")
    r4 = L.한바퀴(판, 생성자=lambda P: 후3, V자=lambda x: (True, ""), J자=J자, ε=0.0, 원장저장소=판)
    ok(r4["고른것"] is not None and r4["고른것"]["이름"] == "바", "ε=0.0 이면 +0.5 개선을 받는다")

    print("\n== 4. 동점이면 먼저 온 것 ==")
    후5 = 후보들만들기({"사": 3.0, "아": 3.0})
    r5 = L.한바퀴(판, 생성자=lambda P: 후5, V자=lambda x: (True, ""), J자=J자, 원장저장소=판)
    ok(r5["고른것"]["이름"] == "사" and "동점" in r5["왜"], f"먼저 온 '사' ({r5['고른것']['이름']})")

    print("\n== 5~6. 원장에 사양의 칸이 다 남는다 (버린 것도) ==")
    행들 = L.원장읽기(판)
    후보행 = [x for x in 행들 if x.get("꼴") == "후보"]
    ok(후보행, f"후보 줄이 남는다 ({len(후보행)}개)")
    칸들 = ("P_t", "P'", "V", "J", "ΔJ", "hypothesis", "cost", "result")
    빠진 = [k for k in 칸들 if not any(k in x for x in 후보행)]
    ok(not 빠진, f"사양의 칸이 다 있다 (빠진 것: {빠진})")
    버린 = [x for x in 후보행 if str(x.get("result", "")).startswith("버림")]
    ok(버린 and 버린[0].get("V") is False and "V 빨강" in str(버린[0].get("V말")),
       "**버린 후보가 왜 버려졌는지와 함께 남는다** -- π 의 재료다")
    ok(any(x.get("result") == "채택" and x.get("hypothesis") for x in 행들), "채택 줄에 가설이 남는다")
    ok(any(x.get("꼴") == "바퀴시작" and x.get("Θ") is not None for x in 행들),
       "바퀴 시작에 Θ(평가 기준)가 남는다 -- 다른 기준으로 잰 J 와 섞이지 않게")
    보 = L.보고(판)
    ok("개선 루프" in 보 and "채택" in 보 and "쌓인 ΔJ" in 보, f"보고가 원장을 읽는다 ({보[:50]!r})")

    print("\n== 7. 여러바퀴: 채택한 것을 새 P_t 로 삼고, 채택이 없으면 멈춘다 ==")
    차례 = [{"자": 5.0}, {"차": 3.0}, {"카": 0.0}]     # 셋째 바퀴에서 더 나아질 후보가 없다
    몇 = {"n": 0}

    def 생성차례(P):
        i = 몇["n"]
        몇["n"] += 1
        if i >= len(차례):
            return []
        값들 = dict(차례[i])
        바탕 = 점수.get(str(P), 0.0)
        for k in list(값들):
            값들[k] = 바탕 + 값들[k]                  # 직전 P_t 보다 이만큼
        return 후보들만들기(값들)

    rr = L.여러바퀴(판, 생성자=생성차례, 적용자=lambda 고른, P: 고른["후보"]["판"],
                V자=lambda x: (True, ""), J자=J자, 바퀴수=5, 원장저장소=판)
    ok(len(rr["바퀴들"]) == 3 and rr["나아간바퀴"] == 2,
       f"두 바퀴 나아가고 셋째에 멈췄다 (바퀴 {len(rr['바퀴들'])} · 나아간 {rr['나아간바퀴']})")
    ok("ΔJ > ε" in rr["멈춘까닭"] or "채택" in rr["멈춘까닭"], f"멈춘 까닭을 말한다 ({rr['멈춘까닭'][:50]})")
    ok(점수.get(str(rr["P"]), 0.0) == 8.0, f"P_t 가 0 -> 5 -> 8 로 움직였다 (지금 {점수.get(str(rr['P']))})")
    ok(any(x.get("꼴") == "루프끝" for x in L.원장읽기(판)), "루프 끝이 원장에 남는다")

    print("\n== 후보가 없으면 ==")
    r6 = L.한바퀴(판, 생성자=lambda P: [], V자=lambda x: (True, ""), J자=J자, 원장저장소=판)
    ok(r6["고른것"] is None and "V 를 지난 후보가 없다" in r6["왜"], "후보 0개면 채택 없음")
finally:
    shutil.rmtree(판, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("improveloop: V 우선 · ΔJ>ε · ε 문턱 · 동점 · 원장 칸 · 버린 까닭 · 여러바퀴 · 멈춤 -- 통과")
