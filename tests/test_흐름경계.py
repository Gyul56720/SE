# -*- coding: utf-8 -*-
"""**우리가 어디까지 하는지 문서와 코드가 같은 말을 하는가.**

사용자(2026-09-22): "GDSII 까지 직접 수행하는 것이 IP 개발자의 일이라는 의미도
아닙니다. … IP Spec → Architecture → C/C++ HLS 또는 RTL → Verification →
Synthesis/PPA 검토 → 고객 SoC 에 전달 까지가 IP 개발자의 중심 업무이고, 실제 SoC
통합 이후의 physical implementation 은 별도 조직/파트너가 담당할 수 있습니다."

맞는 교정이고 **우리 집에 그대로 걸렸다.** `people.py` 의 Kenji 가 제 일을
"passes the sign-off checks and emits GDSII" 라고 적고, 산출물에 "GDSII file" 을
올려 두었다. 우리는 GDSII 를 **실제로 쓴다** -- 그것은 참말이다. 그러나 **IP
하우스의 인도물이 아니다.** 둘을 같은 칸에 놓으면 받는 사람이 우리가 칩을 내
준다고 읽는다.

실행: python3 tests/test_흐름경계.py
"""
from __future__ import annotations

import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


from house import flow as F           # noqa: E402
from house import people as P         # noqa: E402

# ---------------------------------------------------------------- 흐름이 그물이다
끊 = F.이어지나()
ok(not 끊, f"**모든 단계가 있는 앞 단계를 가리킨다** ({끊})")
# **줄이 아니라 그물이다.** 첫 판은 목록 순서를 흐름으로 보고 "앞 칸의 출력이 뒤 칸의
# 입력에 나오나" 를 봤다 -- 안 이어지는 자리 4개가 나왔는데 **셋이 거짓**이었다.
# Verification 과 Lint/CDC 는 나란히 RTL 을 받는다.
_표 = {x["단계"]: x for x in F.표()}
ok(_표["Verification"]["앞"] == ["RTL / HLS"] and _표["Lint / CDC / RDC"]["앞"] == ["RTL / HLS"],
   "**검증과 Lint/CDC 는 나란히 RTL 을 받는다** — 줄로 보면 없는 끊김이 생긴다")
ok(_표["DRC / LVS"]["앞"] == _표["STA / IR / EM"]["앞"],
   "**STA/IR/EM 과 DRC/LVS 도 나란하다**")
ok(len([x for x in F.단계들 if not x[1]]) == 1, "시작 칸은 하나다")

# ---------------------------------------------------------------- 단계마다 입출력
for x in F.표():
    ok(bool(x["출력"]), f"{x['단계']}: 출력이 적혀 있다")
ok(all(x["입력"] for x in F.표() if x["앞"]),
   "**앞 단계가 있는 칸은 입력이 비지 않는다**")

# ---------------------------------------------------------------- 경계
b = F.경계()
ok("Specification" in b["인도물"] and "RTL / HLS" in b["인도물"]
   and "Verification" in b["인도물"],
   f"**인도물은 스펙·RTL·검증**이다 ({b['인도물']})")
ok("PPA / STA" in b["검토"] and "Synthesis" in b["검토"],
   f"**합성·PPA 는 참고치**다 ({b['검토']})")
ok("GDSII / Tape-out" in b["시연"],
   "**GDSII 는 시연이다** — 실제로 쓰지만 IP 하우스의 인도물이 아니다")
ok("GDSII / Tape-out" not in b["인도물"],
   "**GDSII 를 인도물로 세지 않는다** — 그것이 이 파일의 전부다")
ok(set(b["인도물"]) & set(b["시연"]) == set(),
   "인도물과 시연이 겹치지 않는다")
for 칸 in ("LEC (논리 등가)", "ECO", "고객 SoC 에 전달"):
    ok(칸 in b["없음"], f"**안 하는 칸을 안 한다고 적는다**: {칸}")

# ---------------------------------------------------------------- 사람 설명과 맞나
_k = P.BY_KEY["pd"]
ok("demonstration" in _k.role.lower() or "시연" in _k.role,
   "**PD 담당의 설명이 '시연' 이라고 말한다** — 전에는 "
   "'passes the sign-off checks and emits GDSII' 였다")
ok(any("NOT an IP deliverable" in a or "not an ip deliverable" in a.lower()
       for a in _k.artifacts),
   "**산출물 목록의 GDSII 옆에 '인도물이 아니다' 가 붙어 있다**")

# ---------------------------------------------------------------- 제안서가 이 표를 낸다
_소스 = (뿌리 / "house" / "arch.py").read_text(encoding="utf-8")
ok("from house import flow as FLOW" in _소스 and "_경계절(R)" in _소스,
   "**제안서가 이 경계 표를 낸다** — 코드에만 있고 문서에 없으면 읽는 사람은 모른다")

# ---------------------------------------------------------------- 안 하는 주장
_문서 = (뿌리 / "house" / "flow.py").read_text(encoding="utf-8")
ok("절반 이상이 Physical Design" in _문서 and "안 한다" in _문서,
   "**비중 주장을 안 한다고 적어 둔다** — 조직과 과제에 따라 크게 다르다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("흐름경계: 그물 · 입출력 · 인도물/검토/시연/없음 · 사람 설명 · 제안서 -- 통과")
