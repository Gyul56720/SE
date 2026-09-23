# -*- coding: utf-8 -*-
"""**게이트 레벨 시뮬(관문 6b) 이 서는가 -- 그리고 다른 것을 다르다고 하는가.**

테이프아웃 지도 M3:

    게이트 레벨 시뮬 (SDF 역주석)   없다   칸 자체가 없다

## 왜 없었나 -- 셀 모델이 없었다

합성 넷리스트는 `INVX1` · `DFFRX1` 같은 셀을 부르는데, 이 저장소에는
Liberty(타이밍·면적)만 있고 **Verilog 모델이 없었다.** 그래서 넷리스트를
돌릴 방법이 아예 없었다. `house/lib/cells.v` 가 그 자리를 메운다.

## 모델을 지어내면 이 관문이 거짓말을 한다

셀 모델과 Liberty 의 `function` 이 갈라지면, 게이트 결과가 RTL 과 달라도
**합성 탓인지 모델 탓인지 못 가린다.** 그래서 이 검사는 `cells.v` 의 식과
`lab/lib/se10.lib` 의 `function` 을 **맞춰 본다** -- 눈으로가 아니라 파싱해서.

실행: python3 tests/test_게이트시뮬.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


from house import designs as DES       # noqa: E402
from house import gen as GEN           # noqa: E402
from house import tapeout as TO        # noqa: E402

문턱 = GEN.기본문턱

print("\n[1] 문턱과 견줄 칸이 있나")
for 열쇠 in ("게이트시뮬씨앗", "게이트시뮬벡터", "게이트비교칸"):
    ok(열쇠 in 문턱, f"gen.기본문턱 에 {열쇠!r} 가 있다")
ok("fail" in 문턱["게이트비교칸"] and "cov_pct" in 문턱["게이트비교칸"],
   f"틀린 값(fail)과 지나간 길(cov_pct)을 둘 다 견준다 ({len(문턱['게이트비교칸'])}칸)")
ok(len(문턱["게이트시뮬씨앗"]) >= 2,
   f"씨앗을 여럿 돌린다 ({len(문턱['게이트시뮬씨앗'])}개)")

print("\n[2] **견주기가 다른 것을 다르다고 하는가**")
칸 = ("pass", "fail", "cov_pct")
ok(GEN.견주기({"pass": 10, "fail": 0, "cov_pct": 50.0},
            {"pass": 10, "fail": 0, "cov_pct": 50.0}, 칸) == [],
   "같으면 빈 목록이다")
d = GEN.견주기({"pass": 9, "fail": 1, "cov_pct": 50.0},
            {"pass": 10, "fail": 0, "cov_pct": 50.0}, 칸)
ok(len(d) == 2 and {x["칸"] for x in d} == {"pass", "fail"},
   f"다른 칸만 정확히 집는다 ({[x['칸'] for x in d]})")
ok(d[0]["게이트"] != d[0]["RTL"], "어느 쪽이 무엇이었는지 같이 적는다")
# **죽은 시뮬을 초록으로 읽지 않는다** -- 이 자리가 가장 미끄럽다
죽 = GEN.견주기(None, {"pass": 10, "fail": 0, "cov_pct": 50.0}, 칸)
ok(len(죽) == len(칸) and all(x["게이트"] is None for x in 죽),
   f"게이트 JSON 이 없으면 모든 칸이 다른 것으로 난다 ({len(죽)}칸)")
ok(all("JSON" in x["왜"] for x in 죽), "왜 그런지 칸마다 적는다")

print("\n[3] **관문이 무는가**")
성한것 = {"씨앗별": [{"씨": 1, "rc": 0, "게이트JSON있나": True, "게이트fail": 0,
                 "다른칸": []},
                {"씨": 2, "rc": 0, "게이트JSON있나": True, "게이트fail": 0,
                 "다른칸": []}],
        "다른수": 0, "칸": list(칸), "벡터": 200, "셀수": 4313, "초": 9.4}


def 판정(**고침):
    return GEN.게이트시뮬판정({**성한것, **고침}, 문턱)


r = 판정()
ok(len(r) == 1 and r[0][1], "전부 같으면 초록이다")
ok(r[0][0].startswith("6b."), f"이름표가 6b 로 시작한다 ({r[0][0][:12]})")
ok(not 판정(다른수=1, 씨앗별=[{**성한것["씨앗별"][0],
    "다른칸": [{"칸": "fail", "게이트": 3, "RTL": 0, "왜": ""}]}])[0][1],
   "칸 하나라도 다르면 빨갛다")
ok(not 판정(씨앗별=[{**성한것["씨앗별"][0], "rc": 134}])[0][1],
   "게이트 시뮬이 비정상 종료하면 빨갛다 (다른 칸이 0이어도)")
ok(not 판정(씨앗별=[{**성한것["씨앗별"][0], "게이트JSON있나": False}])[0][1],
   "게이트가 JSON 을 안 내면 빨갛다")
ok(not 판정(씨앗별=[{**성한것["씨앗별"][0], "게이트fail": 2}])[0][1],
   "게이트 쪽 fail 이 0 이 아니면 빨갛다")
ok(not GEN.게이트시뮬판정({"오류": "셀 모델이 없다"}, 문턱)[0][1],
   "못 지으면 빨갛다 — 못 쟀는데 통과시키지 않는다")

print("\n[4] 관문 글이 한계를 적는가")
말 = 판정()[0][2]
ok("SDF 역주석이 아니" in 말 and "타이밍이 없다" in 말,
   "지연 0 이고 SDF 가 아니라고 말한다")
ok("cells.v" in 말 and "Liberty" in 말,
   "셀 모델이 어디서 왔는지와, 갈라지면 거짓말이 된다는 것을 적는다")
ok("7" in 말, "타이밍은 어느 관문이 보는지 가리킨다")

print("\n[5] **셀 모델이 Liberty 와 같은가** -- 지어낸 것이 아닌지 맞춰 본다")
셀글 = (뿌리 / "house" / "lib" / "cells.v").read_text(encoding="utf-8")
lib글 = (뿌리 / "lab" / "lib" / "se10.lib").read_text(encoding="utf-8", errors="replace")
# Liberty 에서 (셀이름 -> 출력 function) 을 뽑는다
리브 = {}
for m in re.finditer(r'cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)\s*\{', lib글):
    이름, i, 깊이 = m.group(1), m.end(), 1
    while i < len(lib글) and 깊이:
        깊이 += (lib글[i] == "{") - (lib글[i] == "}")
        i += 1
    f = re.search(r'pin\s*\(\s*Y\s*\)\s*\{\s*direction\s*:\s*output;\s*'
                  r'function\s*:\s*"([^"]*)"', lib글[m.end():i])
    if f:
        리브[이름] = f.group(1)
ok(len(리브) >= 12, f"Liberty 에서 조합 셀 {len(리브)}개의 function 을 읽었다")


def _판판(식: str) -> str:
    """괄호·공백을 털어 견줄 수 있는 꼴로."""
    return re.sub(r"[\s()]", "", 식).replace("~", "!")


어긋 = []
for 이름, f in 리브.items():
    m = re.search(rf"^module\s+{이름}\s*\(.*?assign\s+Y\s*=\s*([^;]+);",
                  셀글, re.M | re.S)
    if not m:
        어긋.append(f"{이름}: cells.v 에 모델이 없다")
        continue
    if _판판(m.group(1)) != _판판(f):
        어긋.append(f"{이름}: cells.v={m.group(1).strip()!r} vs lib={f!r}")
ok(not 어긋, f"조합 셀 {len(리브)}개의 식이 Liberty 와 **글자 그대로 같다** ({어긋})")
for x in 어긋[:4]:
    print("       " + x)
# 플롭·래치는 식이 아니라 꼴로 본다
ok(re.search(r"module\s+DFFRX1\b.*?negedge\s+RN.*?Q\s*<=\s*1'b0", 셀글, re.S) is not None,
   "DFFRX1 이 Liberty 의 clear:\"!RN\" 대로 비동기 클리어를 한다")
ok(re.search(r"module\s+LATX1\b.*?if\s*\(G\)\s*Q\s*=\s*D", 셀글, re.S) is not None,
   "LATX1 이 enable:\"G\" 대로 G 가 높을 때 투명하다")
# **이 맞춤 검사가 진짜인지 본다** -- 일부러 어긋난 식을 넣어 걸리는지
ok(_판판("(A&!S)|(B&S)") != _판판("(A&S)|(B&!S)"),
   "맞추는 자리가 MUX 방향을 뒤집은 식을 다른 것으로 본다 — 늘 통과가 아니다")

print("\n[6] **진짜로 지어 돌린다** -- 넷리스트가 RTL 과 같은 답을 내나")
import time                                                   # noqa: E402
t0 = time.time()
try:
    from house import synth as SYN                            # noqa: E402
    합 = SYN.합성(DES.파라기본(DES.NSW_FIR) or None, 설계=DES.NSW_FIR,
               top=DES.NSW_FIR.top)
    ok(합.get("됐나"), "합성이 됐다")
    GL = GEN.게이트시뮬(DES.NSW_FIR, {**문턱, "게이트시뮬씨앗": (1,),
                                "게이트시뮬벡터": 120}, 합)
    ok(not GL.get("오류"), f"게이트시뮬()이 돌았다 ({str(GL.get('오류', ''))[:200]})")
    if not GL.get("오류"):
        ok(set(성한것) <= set(GL),
           f"손으로 만든 값과 칸이 같다 (빠진 칸 {sorted(set(성한것) - set(GL))})")
        ok(GL["다른수"] == 0,
           f"넷리스트와 RTL 이 견준 칸 전부에서 같다 (다른 칸 {GL['다른수']}개)")
        ok(all(x["rc"] == 0 and x["게이트JSON있나"] for x in GL["씨앗별"]),
           "게이트 시뮬이 정상 종료하고 결과를 냈다")
        ok(GEN.게이트시뮬판정(GL, 문턱)[0][1], "잰 값으로 관문이 초록이다")
        print(f"       (셀 {GL['셀수']:,}개 · {GL['초']} s)")
except Exception as e:                                        # noqa: BLE001
    ok(False, f"진짜로 못 돌렸다: {type(e).__name__}: {e}")

print("\n[7] 테이프아웃 표 -- 못 하는 것은 못 한다고 남았나")
이름별 = {x["이름"]: x for x in TO.표(주인="dv")}
x = 이름별.get("게이트 레벨 시뮬 (기능 · 지연 0)")
ok(x is not None and x["상태"] == TO.있다, "「게이트 레벨 시뮬(기능)」 이 「있다」 다")
sdf = 이름별.get("SDF 역주석 (게이트 타이밍 시뮬)")
ok(sdf is not None and sdf["상태"] == TO.없다 and sdf["막나"],
   "「SDF 역주석」 은 **없는 채로 남고 여전히 막는다** — 지연 0 을 타이밍 시뮬로 "
   "세지 않는다")
ok("Verilog 테스트벤치" in (sdf or {}).get("메모", ""),
   "SDF 로 가려면 무엇이 더 있어야 하는지 적어 둔다")
ok(TO._관문있나("6b") and "6b" in GEN.관문번호들(), "관문 6b 가 있다")
ok(not TO.검사() and not TO.거짓증거() and not TO.안걸린붙듦(),
   f"계획에 흠이 없다 ({TO.검사()})")

print("\n" + "=" * 62)
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for x in FAIL:
        print("  · " + x)
    raise SystemExit(1)
print("전부 통과")
