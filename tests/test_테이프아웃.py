# -*- coding: utf-8 -*-
"""**테이프아웃 계획이 제 상태를 지어내지 않는가 -- 증거를 망가뜨려서 잰다.**

계획표는 언제나 좋아 보인다. 항목마다 「있다」 라고 적어 두면 되기 때문이다.
그래서 `house/tapeout.py` 는 상태를 적지 않고 **찾아본다** -- 능력(그 코드가
있나)과 붙듦(그것을 막는 관문·문턱이 있나)을 따로.

**그 '찾아본다' 가 진짜인지를 여기서 잰다.** 글자로 "찾아보는 코드가 있나" 를
보면 안 된다 -- 이 저장소는 그 자리에서 두 번 거짓 초록을 냈다(CLAUDE.md
"둘 다 글자를 봐서다"). 여기서는 **찾는 함수를 실제로 망가뜨려** 상태가 따라
움직이는지 본다. 안 움직이면 그 표는 지어낸 것이다.

그리고 **「없다」 가 표에서 안 빠지는지**를 센다. 구멍을 지우면 계획이 초록으로
보이고, 그것이 이 저장소가 가장 경계하는 꼴이다.

실행: python3 tests/test_테이프아웃.py
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


from house import flow as FLOW          # noqa: E402
from house import people as PEOPLE      # noqa: E402
from house import report as RPT         # noqa: E402
from house import tapeout as TO         # noqa: E402

print("\n[1] 계획 자체가 성한가 -- 가리키는 이름이 다 있나")
흠 = TO.검사()
ok(not 흠, f"단계·주인·마일스톤 조건이 다 실재한다 ({len(흠)}개 흠)")
for x in 흠:
    print("       " + x)

print("\n[2] 적어 놓고 없는 것 -- #62 law/bench.py 가 이 자리다")
거 = TO.거짓증거()
ok(not 거, f"「능력」 으로 적은 코드가 다 실재한다 ({len(거)}개)")
for x in 거:
    print(f"       [{x['주인']}] {x['항목']}: {x['말']}")
끊 = TO.흐름이가리키는파일()
ok(not 끊, f"house/flow.py 가 없는 파일을 안 가리킨다 ({len(끊)}개)")
for x in 끊:
    print(f"       {x['단계']} -> {x['길']}")

print("\n[3] 상태를 **찾아보고** 정하는가 -- 찾는 함수를 망가뜨려 본다")
# 이것이 이 파일의 심장이다. 상태가 손으로 적혀 있으면 아래 셋이 다 안 변한다.
원래 = (TO._파일있나, TO._이름있나, TO._관문있나, TO._문턱있나, TO._게이트있나)
전 = TO.셈()
try:
    TO._파일있나 = lambda _p: False
    TO._이름있나 = lambda _p, _n: False
    후능 = TO.셈()
finally:
    TO._파일있나, TO._이름있나 = 원래[0], 원래[1]
ok(후능[TO.있다] == 0 and 후능[TO.시연뿐] == 0 and 후능[TO.없다] == 후능["전체"],
   f"능력 증거를 다 없애면 모든 항목이 「없다」 가 된다 "
   f"(있다 {전[TO.있다]}→{후능[TO.있다]} · 없다 {전[TO.없다]}→{후능[TO.없다]})")

try:
    TO._관문있나 = lambda _n: False
    TO._문턱있나 = lambda _k: False
    TO._게이트있나 = lambda _g: False
    후붙 = TO.셈()
finally:
    TO._관문있나, TO._문턱있나, TO._게이트있나 = 원래[2], 원래[3], 원래[4]
ok(후붙[TO.있다] == 0 and 후붙[TO.시연뿐] == 전[TO.있다] + 전[TO.시연뿐],
   f"붙듦 증거를 다 없애면 「있다」 가 전부 「시연뿐」 으로 내려온다 "
   f"(있다 {전[TO.있다]}→{후붙[TO.있다]} · 시연뿐 {전[TO.시연뿐]}→{후붙[TO.시연뿐]})")
ok(TO.셈() == 전, "망가뜨린 것을 되돌려 놓았다 -- 뒤 검사가 그 위에서 돈다")

print("\n[4] 증거확인() 이 아무거나 초록으로 안 낸다")
가짜 = ["파일:house/없는파일.py", "함수:house/tapeout.py::없는함수",
      "함수:house/없는파일.py::상태", "관문:99", "문턱:없는열쇠", "게이트:G999",
      "아무말", "함수:house/tapeout.py"]
ok(all(not TO.증거확인(x)["있나"] for x in 가짜),
   f"없는 파일·함수·관문·문턱·게이트와 꼴이 틀린 글 {len(가짜)}가지를 다 빨갛게 낸다")
진짜 = ["파일:house/tapeout.py", "함수:house/tapeout.py::상태", "관문:7",
      "문턱:변이점수", "게이트:G024"]
ok(all(TO.증거확인(x)["있나"] for x in 진짜),
   f"실재하는 증거 {len(진짜)}가지는 초록으로 낸다 — 늘 빨간 장치도 쓸모가 없다")

print("\n[5] 아는 구멍이 표에 **남아** 있나 -- 지우면 계획이 초록으로 보인다")
이름별 = {x["이름"]: x for x in TO.표()}
# **메워진 것은 이 목록에서 뺀다.** 「코드 커버리지」 는 관문 4c 가 생겨
# 「있다」 로 올라갔다(tests/test_코드커버리지관문.py 가 그 자리를 붙든다).
# 메워졌는데 구멍이라고 적어 두면 이 검사가 거짓 빨강을 낸다.
구멍 = ["RDC (리셋 도메인 건넘)", "LEC (RTL ↔ 넷리스트 등가)", "ECO (위반 고치기)",
      "어서션 (SVA) · 형식 검증",
      "게이트 레벨 시뮬 (SDF 역주석)", "DRC (설계 규칙)",
      "LVS (레이아웃 ↔ 넷리스트)", "IP-XACT 패키징 · 통합 문서",
      "PDK · 레이어 맵 · 실제 공정 라이브러리"]
for n in 구멍:
    x = 이름별.get(n)
    ok(x is not None and x["상태"] == TO.없다 and x["막나"],
       f"{n} — 「없다」 로 남아 있고 테이프아웃을 막는다")
막이름 = {x["이름"] for x in TO.막는것()}
ok(all(n in 막이름 for n in 구멍), "열 구멍이 전부 막는것() 에 든다")

print("\n[6] 「없다」 인 항목은 증거를 안 달고, 증거를 단 항목은 「없다」 가 아니다")
어긋 = [x["이름"] for x in TO.표() if x["상태"] == TO.없다 and x["능력"]]
ok(not 어긋, f"없다고 적은 항목에 능력 증거가 붙어 있지 않다 ({어긋})")

print("\n[7] 마일스톤이 앞 칸을 건너뛰지 않는다")
w = TO.어디까지()
t = TO.마일스톤표()
첫막힘 = next((i for i, m in enumerate(t) if m["막는것"]), None)
ok(len(w["지난것"]) == (첫막힘 if 첫막힘 is not None else len(t)),
   f"막힌 칸 앞까지만 지났다고 말한다 (지난 칸 {len(w['지난것'])}개)")
ok(w["막힌곳"] == t[첫막힘]["이름"] if 첫막힘 is not None else w["막힌곳"] is None,
   f"막힌 곳을 바로 집는다: {w['막힌곳']}")
ok(all(m["표시"] != "선다" for m in t if any(c["상태"] != TO.있다 for c in m["조건"])),
   "안 선 항목이 있는 칸을 「선다」 라고 적지 않는다 (M8 규격 칸이 그 자리다)")

print("\n[8] 못 읽은 규격을 근거로 막지 않는다")
밀 = [x for x in TO.표() if "MIL-STD" in x["이름"]]
ok(len(밀) == 2, f"MIL-STD 줄이 둘 있다 ({len(밀)})")
ok(all(not x["막나"] for x in 밀),
   "MIL-STD 줄은 막는 칸으로 안 센다 — 본문을 못 읽었기 때문이다")
ok(all("[사용자가져옴:안읽음]" in x["메모"] for x in 밀),
   "두 줄 다 어디까지 읽었는지를 메모에 그대로 달고 있다")

print("\n[9] 에이전트에 묶였나 -- 다섯 보고서가 제 몫을 싣는다")
주인들 = {x["주인"] for x in TO.항목들}
ok(주인들 <= set(PEOPLE.BY_KEY) and len(주인들) == 5,
   f"다섯 사람 모두에게 항목이 붙어 있다 ({sorted(주인들)})")
for 키 in sorted(PEOPLE.BY_KEY):
    R = RPT.보고서(PEOPLE.BY_KEY[키], "t", "x", "y")
    TO.절(R, 키)
    몫 = TO.표(주인=키)
    없는것 = [x for x in 몫 if x["상태"] == TO.없다]
    ok(R.표수 == 1, f"{키}: 보고서에 테이프아웃 표가 한 장 실린다")
    ok(R.그림수 == 1, f"{키}: 제 몫을 칠한 상태 지도가 한 장 실린다")
    # **줄 수를 센다.** "「없다」 가 표에 있나" 를 글자로 보면 설명글의 「없다」 에
    # 걸려 초록이 난다. 그리고 `getattr(R, "없는칸", [])` 처럼 **없을 수도 있는
    # 자리**에서 세면 언제나 0 이 나와 빈말로 통과한다 -- 이 저장소가 두 번 당한
    # 꼴이다. 표는 `R.조각` 의 HTML 로 들어가므로 거기서 `<tr>` 을 센다.
    표HTML = [x for x in R.조각 if "<tr>" in x]
    ok(len(표HTML) == 1, f"{키}: 조각에서 표 HTML 을 딱 하나 집었다 ({len(표HTML)})")
    실린줄 = 표HTML[0].count("<tr>") - 1 if 표HTML else -1      # 머리줄 한 줄을 뺀다
    ok(len(몫) >= 3 and 실린줄 == len(몫),
       f"{키}: 제 몫 {len(몫)}항목(없다 {len(없는것)}개)이 한 줄도 안 빠지고 실린다 "
       f"— 표에 실린 줄 {실린줄}")
    # 「없다」 가 **표 칸 안에** 찍혔나 -- 설명글에 든 같은 글자에 안 걸리게
    # `<table` 뒤만 센다. 캡션은 표보다 **앞에** 붙으므로(report.표: `cap + t`)
    # 앞을 잘라 내는 것으로는 안 걸러진다 -- 첫 판이 그래서 빈 글을 셌다.
    본문 = 표HTML[0][표HTML[0].index("<table"):] if 표HTML else ""
    찍힘 = 본문.count(">" + TO.없다 + "</td>")
    ok(찍힘 == len(없는것),
       f"{키}: 「없다」 가 표 칸에 {len(없는것)}번 그대로 찍힌다 (찍힌 수 {찍힘})")

print("\n[10] 다섯 에이전트가 실제로 이 칸을 부르는가")
# 글자로 본다. 여기서만은 그것이 맞다 -- 보고서를 통째로 돌리려면 합성이 돌아야 한다.
from tests._소스보기 import 산주장                                    # noqa: E402
짝 = {"house/rtl/agent.py": "rtl", "house/dv/agent.py": "dv",
     "house/syn/agent.py": "syn", "house/dft/agent.py": "dft",
     "house/pd/agent.py": "pd"}
for 길, 키 in 짝.items():
    src = 산주장((뿌리 / 길).read_text(encoding="utf-8"))
    ok(f'TO.절(R, "{키}")' in src and "from house import tapeout as TO" in src,
       f"{길} 가 제 열쇠 {키!r} 로 TO.절() 을 부른다")

print("\n[11] 제안서에도 계획 칸이 실린다 -- 마일스톤 표를 실제로 그려 본다")
from house import arch as ARCH                                        # noqa: E402
_R = RPT.보고서(PEOPLE.ETHAN, "t", "x", "y")
ARCH.테이프아웃절(_R)
_표 = [x for x in _R.조각 if "<tr>" in x]
ok(len(_표) == 1, f"제안서 칸이 표를 한 장 그린다 ({len(_표)})")
ok(_R.그림수 == 1, f"제안서 칸이 상태 지도를 한 장 그린다 ({_R.그림수})")
ok(_표 and _표[0].count("<tr>") - 1 == len(TO.마일스톤표()),
   f"마일스톤 {len(TO.마일스톤표())}칸이 한 줄도 안 빠지고 실린다"
   + (f" — 실린 줄 {_표[0].count('<tr>') - 1}" if _표 else ""))
_arch = 산주장((뿌리 / "house" / "arch.py").read_text(encoding="utf-8"))
ok("    테이프아웃절(R)" in _arch,
   "house/arch.py 의 보고서() 가 그 칸을 실제로 부른다")

print("\n[12] 단계 이름을 두 군데 적지 않는다")
흐름이름 = {x[0] for x in (FLOW.단계들 + FLOW.따로)}
ok(all(x["단계"] in 흐름이름 for x in TO.항목들),
   "모든 항목의 단계가 house/flow.py 에서 온다 — 여기서 새 단계를 만들지 않는다")

print("\n" + "=" * 62)
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for x in FAIL:
        print("  · " + x)
    raise SystemExit(1)
print("전부 통과")
