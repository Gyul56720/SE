# -*- coding: utf-8 -*-
"""설계 하우스(house/) 를 **실제로 돌려** 붙든다 -- 글자만 보는 검사가 아니다.

이 저장소의 규율: **검사하지 않은 초록불이 검사한 빨간불보다 나쁘다.**
여기서 붙드는 것은 이 회사가 사용자에게 한 약속 그대로다.

  1. **그림 없는 보고서는 안 나간다.** 사용자가 정한 첫 조건이다
     ("반드시 그림 혹은 그래프로, 시각화해서 제시해야한다").
  2. **첨부 없는 메일은 안 나간다.** 글로만 "~했다" 고 보고하는 것을 막는 장치다.
  3. **메일 양식이 사용자가 준 그대로다.** 수신/소속/직급/이름이 다 들어간다.
  4. **GDSII 는 되읽어야 냈다고 말한다.** 왕복 검증이 실제로 돌아야 한다.
  5. **HLS 스케줄러가 자원 한계를 지킨다.** 다주기 연산기의 점유를 센다.
  6. **디스코드 명령이 모르는 말에 None 을 돌려준다** -- 기존 동작을 안 뺏는다.
  7. **`pgrep` 패턴에 한글이 없다** -- 한글 패턴은 영영 안 맞고, 안 맞는 것은
     "없다" 로 읽혀 같은 작업을 두 벌 띄운다(CLAUDE.md 의 실측).

망도 LLM 도 상용 도구도 없이 돈다.  실행: python3 tests/test_house.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


# ------------------------------------------------------------------ 1. 사람
from house import people as P  # noqa: E402

ok(len(P.EVERYONE) == 5, "다섯 명을 채용했다")
ok(len({p.key for p in P.EVERYONE}) == 5, "직무 키가 겹치지 않는다")
ok(sum(1 for p in P.EVERYONE if p.pronouns == "she/her") >= 1,
   "여자가 한 명 이상 있다 (사용자 요구)")
ok(all("@" in p.email for p in P.EVERYONE), "모두 메일 주소가 있다")
ok(P.find("검증") is P.PRIYA and P.find("priya") is P.PRIYA
   and P.find("dv") is P.PRIYA, "한글·영문이름·직무키 셋 다로 사람을 찾는다")
ok(P.find("물리설계") is P.KENJI and P.find("gds") is P.KENJI, "PD 별칭")
ok(P.find("") is None and P.find("점심메뉴") is None, "모르는 말에는 None")
ok(all(k in P.ALIASES for k in ("rtl", "dv", "syn", "dft", "pd")),
   "다섯 직무가 다 별칭에 있다")

# ------------------------------------------------------------------ 2. 보고서
from house import report as RPT  # noqa: E402
from house import viz as V  # noqa: E402

R = RPT.보고서(P.ETHAN, "검사용", "검사 과제")
R.요약("한 줄")
R.글("그림이 없다")
터졌나 = False
try:
    R.html()
except RuntimeError as e:
    터졌나 = "그림" in str(e)
ok(터졌나, "**그림이 0 장인 보고서는 내지 않는다** (사용자가 정한 첫 조건)")

R.그림(V.막대(["a", "b"], [1, 2], "검사"), "설명", "검사도구")
h = R.html()
ok("<svg" in h and "Figure 1." in h,
   "a figure renders and gets numbered (captions are English now)")
ok(P.ETHAN.name in h and P.ETHAN.team in h, "작성자(누가 한 일인지)가 문서에 박힌다")

# **마크다운 별표가 날것으로 안 나간다** (실측: 보고서 1쪽에 `**있는**` 이 찍혔다)
R2 = RPT.보고서(P.PRIYA, "검사2", "과제")
R2.요약("**굵게** 되어야 한다")
R2.그림(V.빈그림("x"))
ok("<b>굵게</b>" in R2.html() and "**굵게**" not in R2.html(),
   "`**x**` 가 굵게 바뀐다 -- 별표가 PDF 에 날것으로 안 찍힌다")

# ------------------------------------------------------------------ 3. 메일 양식
본문 = RPT.mail_body(P.SOFIA, "NSW-FIR v1.0",
                ["Fault coverage 94.9 %", "442 faults remaining"],
                ["Deterministic ATPG was run on a sample, not the full residual set"],
                attachment_name="report.pdf")
# The company writes in English now (user instruction, 2026-09-21). The *shape*
# of the template is unchanged -- greeting, who is writing, numbered sections,
# signature block with affiliation and address. Only the language moved.
for 조각 in ("Dear ", "1. Progress summary",
           "2. Issues, requests and open questions",
           "Kind regards,", "Email:", "Scope:"):
    ok(조각 in 본문, f"mail template contains «{조각}»")
ok("안녕하세요" not in 본문 and "올림" not in 본문,
   "**no Korean left in the outgoing mail** -- the company is English-only")
ok(P.SOFIA.name in 본문 and P.SOFIA.team in 본문 and P.SOFIA.title in 본문,
   "**the mail says which engineer wrote it** (name, team, title)")
ok("report.pdf" in 본문, "the attachment name appears in the body")
ok("Fault coverage 94.9 %" in 본문 and "not the full residual set" in 본문,
   "**both the summary and the caveats reach the body** -- a summary without "
   "its caveats is the failure mode this template exists to prevent")
제목 = RPT.mail_subject(P.SOFIA, "NSW-FIR v1.0")
ok(제목.startswith(RPT.SUBJECT_TAG) and P.SOFIA.name in 제목
   and P.SOFIA.team in 제목,
   f"메일 제목이 `{RPT.SUBJECT_TAG} <날짜> <과제> / <팀> / <이름>` 꼴이다 ({제목[:46]})")
import mailattach as _MA  # noqa: E402
ok(RPT.SUBJECT_TAG in _MA.말머리,
   "**house 의 말머리를 봇의 첨부 가드도 안다** -- 둘이 어긋나면 메일이 한 통도 안 나간다")
import mailer as _MAIL  # noqa: E402
ok(_MAIL.자리표들(제목, _MA.말머리) == [],
   "그 제목이 자리표 관문을 통과한다 (실측 2026-09-21 에 여기서 막혔었다)")

# ------------------------------------------------------------------ 4. 첨부 없는 메일 거부
import mailer  # noqa: E402

r = mailer.보내기_첨부("a@b.c", "제목", "본문", [], repo=Path(tempfile.mkdtemp()))
ok(r.get("보냈나") is False and "첨부" in str(r.get("말", "")),
   "**첨부가 없으면 안 보낸다** -- 이 회사는 글만 보내지 않는다")

# ------------------------------------------------------------------ 5. GDSII 왕복
from house.pd import gds as G  # noqa: E402

임시 = Path(tempfile.mkdtemp(prefix="test-house-"))
lib = G.라이브러리("CHECK")
lib.구조시작("top")
for i in range(7):
    lib.사각("M1", i * 2.0, 0.0, 1.5, 4.0)
lib.선("M2", [(0, 0), (0, 20), (10, 20)], 폭=0.4)
lib.글("TEXT", 1.0, 1.0, "CHECK")
왕 = G.왕복확인(lib, 임시 / "c.gds")
ok(왕["맞나"], "**GDSII 왕복 검증** -- 쓴 도형 수와 되읽은 도형 수가 같다")
ok(왕["쓴것"]["BOUNDARY"] == 7 and 왕["읽은것"]["PATH"] == 1
   and 왕["읽은것"]["TEXT"] == 1, "도형 종류별로 정확히 맞는다")
ok(왕["바이트"] > 200 and 왕["라이브러리"].startswith("CHECK"),
   "라이브러리 이름이 파일에서 되읽힌다")
# 규격 확인: 모든 레코드 길이가 짝수여야 한다 (GDSII 는 워드 정렬이다)
b = (임시 / "c.gds").read_bytes()
import struct  # noqa: E402
i, 홀수 = 0, 0
while i + 4 <= len(b):
    길이 = struct.unpack(">H", b[i:i + 2])[0]
    if 길이 < 4:
        break
    if 길이 % 2:
        홀수 += 1
    i += 길이
ok(홀수 == 0 and i == len(b),
   "**레코드가 규격대로 짝수 길이로 이어 붙어 파일 끝에 정확히 닿는다**")

# ------------------------------------------------------------------ 6. HLS 스케줄러
from house import hls as H  # noqa: E402

g = H.읽기("(a * b + c * d) * (e + f)")
ok(len([n for n in g.연산마디() if n.종류 == "mul"]) == 3,
   "HLS 앞단이 식에서 곱셈 3개를 뽑는다 (파이썬 ast 로 진짜 파싱한다)")

잰것 = []
for 한계 in (1, 2, 3):
    s_ = H.스케줄(g, {"mul": 한계, "add": 2, "sub": 1, "shl": 1})
    최대 = max((d.get("mul", 0) for d in s_["단계별"].values()), default=0)
    # 다주기 곱셈기는 시작 주기만이 아니라 걸친 주기를 다 잡는다 -- 그것까지 세어 본다
    걸친 = {}
    for t, d in s_["단계별"].items():
        for k in range(H.연산기["mul"]["단계"]):
            걸친[t + k] = 걸친.get(t + k, 0) + d.get("mul", 0)
    ok(최대 <= 한계 and max(걸친.values(), default=0) <= 한계,
       f"HLS 스케줄러가 곱셈기 {한계}개 한계를 지킨다 "
       f"(시작 최대 {최대}, **걸친 주기 최대 {max(걸친.values(), default=0)}**)")
    잰것.append((한계, s_["지연_단계"], s_["II"]))
ok(잰것[0][1] >= 잰것[-1][1],
   f"**자원을 줄이면 지연이 는다** {잰것} -- 이것이 HLS 설계공간탐색의 축이다")

# --- 사인오프 산출물의 라벨과 결합 (실측 2026-09-21) --------------------------
# 생성된 RTL 머리가 `// 자원: {"mul": 4, ...}` 를 찍고 있었다. 그 4 는 **식에 든
# 곱셈의 개수**(쓴합)이지 보유한 곱셈기 수가 아니다 -- 곱셈기 2개를 주고 생성했는데
# 머리에 4 가 찍히니 받는 사람이 "곱셈기 4개짜리" 로 읽는다. 사인오프 산출물이라
# 그대로 둘 수 없었다.
#
# 그런데 그 주석을 **`기능확인` 이 파싱하고 있었다** -- 라벨만 고쳤더니 지연을 못 읽고
# `T = T or 4` 의 기본값으로 조용히 떨어졌다. 지연 6 짜리를 4 로 견주면 엉뚱한
# 주기끼리 맞춰 보게 된다(터지지 않고 틀린다). 하이럼의 법칙의 교과서적인 꼴이다.
# 모듈 이름은 **아스키여야 한다** -- SV 식별자에 한글을 쓰면 문법오류다
_자원 = {"mul": 2, "add": 1, "sub": 1}
_g = H.읽기("(a0*x0 + a1*x1) + (a2*x2 + a3*x3)")
_s = H.스케줄(_g, _자원)
_sv = H.생성(_g, _s, H.바인딩(_g, _자원), "label_chk")
ok("보유" in _s and _s["보유"] == _자원,
   f"스케줄 결과가 **보유한 연산기 수**를 따로 들고 있다 ({_s.get('보유')})")
ok(_s["쓴합"]["mul"] == 4 and _s["보유"]["mul"] == 2,
   f"연산 수 {_s['쓴합']['mul']} 와 연산기 수 {_s['보유']['mul']} 는 **다른 값**이다")
ok("// 자원:" not in _sv,
   "**생성된 RTL 이 연산 개수를 '자원' 이라 부르지 않는다** -- 오해할 라벨을 안 남긴다")
ok("연산 수" in _sv and "연산기 보유" in _sv,
   "머리에 둘을 나란히 찍는다 (연산 수 · 연산기 보유)")
try:
    H.기능확인("a+b", "module m; endmodule", "m", 횟수=2)
    ok(False, "지연을 못 알아냈는데 기본값으로 넘어갔다 -- 조용히 틀릴 자리")
except ValueError as _e:
    ok("지연" in str(_e),
       "**지연을 못 알아내면 기본값으로 안 넘어가고 터진다** (틀린 주기로 견주지 않는다)")
_r = H.기능확인("(a0*x0 + a1*x1) + (a2*x2 + a3*x3)", _sv, "label_chk",
            횟수=40, 지연=_s["지연_단계"])
ok(_r["됐나"], f"지연을 인자로 넘기면 생성 RTL 이 C 모델과 맞는다 ({_r.get('견준수')} 벡터)")
ok(잰것[0][2] >= 잰것[-1][2], "자원을 줄이면 II(개시 간격)도 는다")

# ------------------------------------------------------------------ 7. 디스코드 명령
from house import discord_cmd as C  # noqa: E402

ok(C.run("안녕") is None and C.run("!소설 상태") is None,
   "**모르는 말에는 None** -- 기존 동작을 뺏지 않는다")
ok(C.PREFIX == "!회사", "PREFIX 는 !회사")
조 = C.run("!회사")
ok(조 and all(p.name in 조 for p in P.EVERYONE), "`!회사` 가 다섯 명을 다 보인다")
ok("!회사 상태" in 조 and "!회사 전체" in 조, "쓰는 법이 같이 나온다")
쓰기막힘 = C.run("!회사 dv", allow_write=False)
ok(쓰기막힘 and "쓰기" in 쓰기막힘, "쓰기가 막혀 있으면 돌리지 않고 그렇게 말한다")
모름 = C.run("!회사 점심메뉴")
ok(모름 and "모르겠다" in 모름, "사람을 못 고르면 조직도를 보인다")
# **보고서가 아직 없는 저장소에서도 답해야 한다.** 이 검사는 임시 워크트리에서도
# 도는데 거기엔 `house/out/` 이 없다(산출물은 커밋 안 한다). 처음에 "개" 라는
# 글자가 목록에 있는지를 봤다가 갈림점 워크트리에서 빨개졌다 -- **있는 것을 세는
# 검사는 없는 자리에서 거짓 빨강을 낸다.**
목록 = C.run("!회사 보고서")
ok(목록 and ("house/out" in 목록 or "아직 낸 보고서가 없다" in 목록),
   "`!회사 보고서` 가 목록을 내거나, 없으면 없다고 말한다 (빈 저장소에서도 답한다)")

# **한글 패턴 금지** -- CLAUDE.md 의 실측(한글 pgrep 패턴은 영영 안 맞는다)
import re  # noqa: E402
ok(not re.search(r"[가-힣]", C.표식),
   "**pgrep 패턴에 한글이 없다** -- 한글은 안 맞고, 안 맞는 것은 '없다' 로 읽힌다")
ok("house/run.py" in C.표식, "패턴이 실제로 도는 명령줄에 있는 토막이다")

# ------------------------------------------------------------------ 8. 배선
# **글자가 아니라 배선을 잰다.** 예전에는 `"하우스)"` 라는 글자를 찾았는데, 목록 끝에
# 명령을 하나 더 붙이자(`하우스, 논문)`) 멀쩡한 배선을 두고 검사가 빨개졌다. 재려던
# 것은 괄호가 아니라 "이 모듈이 디스코드에서 실제로 닿는가" 다.
import dispatch as _D
ok(C in _D.명령들, "dispatch 의 명령 목록에 실려 있다 -- 디스코드에서 실제로 닿는다")
import dispatch  # noqa: E402
ok(dispatch.run("!회사 보고서") is not None, "dispatch 를 거쳐도 답이 온다")

# ------------------------------------------------------------------ 9. 오케스트레이터
from house import run as RUN  # noqa: E402

ok(set(RUN.직무) == {"rtl", "dv", "syn", "dft", "pd"}, "다섯 직무가 다 배선되어 있다")
ok(RUN.차례 == ["rtl", "dv", "syn", "dft", "pd"],
   "차례가 설계 흐름 순서다 (RTL -> DV -> 합성 -> DFT -> PD)")
특 = RUN._특이사항({"쪽": 9, "그림수": 14, "표수": 12, "초": 100,
                "요약": ["커버리지 92 %", "남은 고장 442개를 못 잡았다"]})
ok(any("못 잡았다" in x for x in 특),
   "**메일 2번 항목에 '못 한 것' 이 올라간다** -- 좋은 소식만 적지 않는다")

# ------------------------------------------------------------------ 10. 그림들
ok("<svg" in V.전원계획([400, 400], [300, 300], [50, 150, 250], 0.6, 제목="x"),
   "전원계획 그림이 SVG 를 낸다")
ok("<svg" in V.레이아웃([100, 100], [0, 5, 10], [(1, 1, 2, 5, "seq")], 제목="x"),
   "레이아웃 그림이 SVG 를 낸다")
ok("<svg" in V.히스토그램([1.0, 2.0, 2.5, 3.0], 칸수=4, 제목="x"), "히스토그램")
ok("<svg" in V.흐름(["a", "b", "c"], "x"), "흐름도")
ok("<svg" in V.히트맵([[0, 1], [1, 0]], "x"), "히트맵")
# 로그 눈금이 무한대에 안 죽는다 (실측: MTBF inf 에서 OverflowError)
ok("<svg" in V.선([1, 2], [("x", [1e0, float("inf")])], 로그y=True),
   "**무한대가 들어와도 눈금이 안 터진다** (MTBF 가 실제로 그랬다)")

# ------------------------------------------------------------------ 11. VCD 파서
# **파형을 지어내지 않는다**를 붙드는 검사다. VCD 규격대로 적은 파일을 읽어
# 값이 그대로 나오는지, 그리고 **없는 것을 있다고 하지 않는지** 본다.
from house.dv import vcd as VCD  # noqa: E402

_vcd = """$timescale 1ps $end
$scope module TOP $end
$scope module dut $end
$var wire 1 ! clk $end
$var wire 1 " en $end
$var wire 4 # cnt [3:0] $end
$upscope $end
$upscope $end
$enddefinitions $end
#0
0!
0"
b0000 #
#10
1!
1"
b0011 #
#20
0!
#30
1!
b1010 #
"""
_f = 임시 / "t.vcd"
_f.write_text(_vcd, encoding="utf-8")
_d = VCD.읽기(_f)
ok(_d["눈금"] == "1ps", "VCD 의 timescale 을 읽는다")
ok(_d["신호수"] == 3 and _d["끝시각"] == 30, "신호 3개 · 끝시각 30 을 읽는다")
ok(VCD.찾기(_d, "clk") == "TOP.dut.clk", "꼬리 이름으로 풀이름을 찾는다 ($scope 를 쌓는다)")
ok(_d["폭"][VCD.찾기(_d, "cnt")] == 4, "다비트 폭을 읽는다")
ok(VCD.찾기(_d, "없는신호") is None, "**없는 신호에는 None** — 없는 것을 지어내지 않는다")
ok(VCD.클럭엣지(_d, "clk") == [10, 30], "상승 엣지 시각이 정확하다")
_뽑 = dict((n, v) for n, v, _t in VCD.뽑기(_d, ["clk", "en", "cnt"], 주기수=2))
ok(_뽑["en"] == "11", "클럭 엣지에서 뜬 표본이 맞다")
ok(_뽑["cnt"] == "3A", "다비트를 16진수로 접는다 (0b0011=3, 0b1010=A)")
_원 = dict((n, v) for n, v, _t in VCD.원시(_d, ["clk"], 끝시각=30, 점=4))
ok(set(_원["clk"]) <= set("01x"), "원시 표본이 0/1/x 만 낸다")
_a, _b = VCD.구간찾기(_d, "en", "1", 앞=5, 뒤=5)
ok(_a == 5 and _b == 15, "**구간을 규칙으로 고른다** — 그 사건이 처음 나는 자리 둘레")
_띠 = VCD.띠만들기(_d, "cnt", 0, 30, 점=30, 이름표={"0011": "RUN"})
ok(isinstance(_띠, list), "주석 띠를 만든다")
# 값이 아직 안 바뀐 구간은 x 여야 한다 -- 0 으로 채우면 없는 것을 있다고 하는 것이다
ok(VCD.값([(10, "1")], 0) == "x", "**변화 전은 x 다** — 0 으로 채우지 않는다")

# ------------------------------------------------------------------ 12. 새 그림들
ok("<svg" in V.파형뷰어([("clk", "0101", "bit"), ("d", "3A5F", "bus")], "x",
                    시작시각=0, 끝시각=40), "파형 뷰어가 SVG 를 낸다")
ok("<svg" in V.파형뷰어([("q", "01x1", "bit")], "x",
                    표시=[(2, "커서")], 주석띠=[(0, 2, "LOAD")]),
   "파형 뷰어가 커서와 주석 띠를 받는다 (x 구간 포함)")
_cg = V.커버그룹([(0, "pkg", "p", 92.3, 100, ""), (2, "cvp", "cp_len", 100.0, 100, "5/5"),
              (2, "cross", "cr", 50.0, 100, "10/20")], "Covergroups")
ok("<svg" in _cg and "% of Goal" in _cg and "Status" in _cg,
   "**커버그룹 창에 Name/Coverage/Goal/% of Goal/Status 칸이 있다**")
ok("<svg" in V.플로어플랜도([500, 500], [344, 343], [120, 250, 380], 0.6, 제목="x"),
   "플로어플랜 그림 (패드·링·스트라이프 라벨)")
ok("<svg" in V.레이아웃뷰어([344, 343], [(1, 1, 2, 5, "seq")],
                      배선=[(0, 0, 10, 10, 1)], 클럭=[(0, 0, 5, 5)], 제목="x"),
   "레이아웃 뷰어 (배선 층 · 클럭 하이라이트)")
from house import sch as SCH  # noqa: E402
ok("<svg" in SCH.uvm구조({"랜덤": 1, "지시": 1, "대조": 2, "불일치": 0,
                        "커버리지": 90.0, "빈맞은": 1, "빈전체": 2}),
   "UVM 구조도")
ok("<svg" in SCH.ate({"패턴수": 512, "메모리_kB": 1, "시간_ms": 1, "체인": 1, "압축": 1}),
   "ATE 그림")
ok("<svg" in SCH.하이브리드bist({"서명": "0x0", "mbist_ms": 1, "lbist_ms": 1}), "Hybrid BIST")
ok("<svg" in SCH.스캔체인({"체인": 4, "압축": 4, "플롭": 425}), "스캔 체인")
ok("<svg" in SCH.cgic({"잰것": "x"}), "CGIC 회로도")
ok("<svg" in SCH.동기화기(2, "x"), "2FF 동기화기 회로도")
ok("<svg" in SCH.데이터패스(["S1", "S2"], [("MUL", 1, 90, 60, 40)]), "파이프라인 데이터패스")
ok("<svg" in SCH.경로도([{"셀": "DFFX1", "증분_ps": 0, "도착_ps": 0},
                      {"셀": "NAND2X1", "증분_ps": 28.4, "도착_ps": 28.4}],
                     "x", 주기_ps=10000, 슬랙_ps=-120), "사인오프 임계경로 회로도")
ok("<svg" in SCH.사인오프판([("타이밍", "NG", "-120 ps", "≥0", "sta")]), "사인오프 판정표")
for _꼴 in ("inv", "buf", "and", "nand", "or", "nor", "xor", "xnor", "mux",
           "aoi", "oai", "dff", "dffr", "lat", "box"):
    ok(len(SCH.기호(_꼴, 0, 0)) > 40, f"게이트 기호 {_꼴}")
ok(SCH.꼴찾기("NAND2X1") == "nand" and SCH.꼴찾기("INVX4") == "inv"
   and SCH.꼴찾기("DFFRX1") == "dffr" and SCH.꼴찾기("XNOR2X1") == "xnor",
   "**셀 이름에서 기호 꼴을 고른다** (DFFR 이 DFF 보다 먼저, XNOR 이 XOR 보다 먼저)")

# ------------------------------------------------------------------ 13. 설계 등록부
from house import designs as DES  # noqa: E402

ok(DES.NSW_FIR.키 == "fir" and DES.NSW_FIR.top == "nsw_fir", "붙박이 회로 fir 가 있다")
ok(DES.찾기(None) is DES.NSW_FIR, "회로를 안 주면 기본 회로")
_터졌 = False
try:
    DES.찾기("없는회로xyz")
except KeyError:
    _터졌 = True
ok(_터졌, "**모르는 회로는 조용히 기본으로 넘기지 않는다** — KeyError 를 낸다")
_ㄱ = DES.NSW_FIR.할수있는것()
ok(all(_ㄱ[k] for k in ("RTL", "DV", "합성", "DFT", "PD")), "fir 는 다섯 공정이 다 된다")
_빈 = DES.설계(키="빈것", 이름="x", top="x", RTL=[임시 / "없다.sv"])
ok(not _빈.할수있는것()["RTL"] and _빈.모자란것(),
   "**없는 것을 있다고 하지 않는다** — 파일이 없으면 못 한다고 적는다")
ok(any("테스트벤치" in x for x in _빈.모자란것()), "TB 가 없으면 그렇게 말한다")
_d2 = DES.설계.사전에서(DES.NSW_FIR.사전())
ok(_d2.키 == "fir" and _d2.top == "nsw_fir" and _d2.RTL == DES.NSW_FIR.RTL,
   "등록부 직렬화가 왕복한다 (다음 세션이 같은 회로를 부를 수 있다)")

# ------------------------------------------------------------------ 14. 스펙 판독
from house import spec as SPEC  # noqa: E402

_s = SPEC.읽기("자동차 범퍼에 들어가는 TTD 회로의 전력 문제를 해결해줄 수있는 회로를 구상해줘")
ok(_s.쓰임새 == ["자동차"], "쓰임새를 읽는다 (범퍼 -> 자동차)")
ok(_s.문제 == ["전력"], "풀려는 문제를 읽는다")
ok("TDC" in _s.회로, "TTD/TDC 를 회로 갈래로 읽는다")
ok(any("주파수" in x for x in _s.모른다) and any("전압" in x for x in _s.모른다),
   "**못 읽은 것을 모른다 목록에 적는다** — 넘겨짚지 않는다")
_s2 = SPEC.읽기("100MHz 1.8V 12비트, 분해능 50ps, 대기전류 10uA 이하")
ok(_s2.수.get("주파수_Hz") == [1e8], "주파수를 단위까지 읽는다 (MHz -> Hz)")
ok(_s2.수.get("전압_V") == [1.8], "전압")
ok(abs(_s2.수.get("분해능_s", [0])[0] - 50e-12) < 1e-18, "분해능 (ps -> s)")
ok(abs(_s2.수.get("전류_A", [0])[0] - 10e-6) < 1e-12, "전류 (uA -> A)")
ok(_s2.수.get("비트") == [12.0], "비트 수")
_s3 = SPEC.읽기("뭔가 만들어줘")
ok(len(_s3.모른다) >= 4, "아무것도 안 적힌 요청에서는 모르는 것이 많다고 말한다")
ok(_s3.읽은것만() == {"쓰임새": [], "문제": [], "회로": [], "수": {}},
   "**읽은 것이 없으면 빈 채로 둔다** — 지어내지 않는다")
# 모델이 죽어도 코드가 읽은 것은 남는다
_죽은 = SPEC.다듬기(SPEC.읽기("자동차 TDC 전력"), 묻기=lambda g: (_ for _ in ()).throw(RuntimeError("망 없음")))
ok(_죽은.회로 == ["TDC"] and any("모델을 못 불렀다" in x for x in _죽은.모른다),
   "**모델이 죽어도 코드가 읽은 것은 남는다** — 그리고 못 불렀다고 적는다")
ok(SPEC._json뽑기("설명\n```json\n{\"이름\": \"a\"}\n```\n끝") == {"이름": "a"},
   "모델이 울타리를 쳐도 JSON 을 뽑는다")
ok(SPEC._json뽑기("JSON 이 아니다") is None, "JSON 이 아니면 None (빈 것을 채우지 않는다)")

# ------------------------------------------------------------------ 15. 생성 관문
from house import gen as GEN  # noqa: E402

_sv = """module nsw_t #(parameter W = 4) (
  input wire clk, input wire rst_n, input wire en, output wire [W-1:0] q);
endmodule"""
_포 = GEN.포트뽑기(_sv, "nsw_t")
ok([x["이름"] for x in _포] == ["clk", "rst_n", "en", "q"], "톱 모듈 포트를 읽는다")
ok(_포[-1]["폭"] == "[W-1:0]", "다비트 폭을 읽는다")
ok(GEN.포트뽑기(_sv, "없는모듈") == [], "없는 모듈이면 빈 목록 (지어내지 않는다)")
ok(GEN._코드뽑기("설명\n```systemverilog\nmodule a; endmodule\n```").strip()
   == "module a; endmodule", "``` 울타리를 벗긴다")
_쓸 = GEN.쓸수있나()
ok(isinstance(_쓸.get("도구없음"), list) and "말" in _쓸,
   "**짓기 전에 무엇이 없는지 말한다**")
# 관문이 **실제로 문다** -- 빨간 것을 등록하지 않는다
_망 = DES.설계(키="망", 이름="x", top="없다", RTL=[임시 / "없다.sv"])
_g = GEN.관문(_망, 벡터=4)
ok(not _g["통과"] and _g["단계"] and not _g["단계"][0]["됐나"],
   "**RTL 이 없으면 1번 관문에서 막힌다** — 통과라고 하지 않는다")
_되 = GEN._되먹임글(_g)
ok("실패했다" in _되 and "고쳐라" in _되,
   "빨간 관문을 모델에게 돌려줄 글로 만든다 (오류 원문을 그대로)")
ok(GEN._되먹임글({"단계": [{"관문": "x", "됐나": True, "말": ""}]}) == "",
   "전부 초록이면 되먹임이 없다")

# ------------------------------------------------------------------ 16. 제안서
from house import arch as ARCH  # noqa: E402

_m = ARCH.일하기("자동차 범퍼 TTD 전력 문제")
ok(_m["코드가읽은것"]["회로"] == ["TDC"], "제안서가 코드 판독을 담는다")
_R = ARCH.보고서(_m)
ok(_R.그림수 >= 1, "제안서에도 그림이 있다 (그림 0장이면 안 나간다)")
_h = _R.html()
ok("이것은 제안서다. 아무것도 만들지 않았다" in _h,
   "**제안서가 스스로 '아무것도 안 만들었다' 고 적는다**")
ok("아직 모르는 것" in _h, "모르는 칸을 절로 세워 보인다")
_조 = ARCH.선행조사쓰기(_m["_s"], "검사용")
_조글 = _조.read_text(encoding="utf-8")
ok("아직 못 본 곳" in _조글 and "아직 안 채움" in _조글,
   "**선행조사 틀이 '아직 안 채웠다' 를 크게 적는다** — 빈 칸을 그럴듯하게 안 채운다")
ok(len(ARCH._질의만들기(_m["_s"])) >= 3, "찾아볼 질의를 만든다")
_조.unlink()

# ------------------------------------------------------------------ 17. 명령 배선
ok(C.run("!회사 회로") and "fir" in C.run("!회사 회로"), "`!회사 회로` 가 목록을 낸다")
_설 = C.run("!회사 설계")
ok(_설 and "한 줄로" in _설, "`!회사 설계` 만 치면 어떻게 쓰는지 알려준다")
ok("제안서" in _설, "제안서를 먼저 낸다고 말한다")
_막 = C.run("!회사 설계 뭔가", allow_write=False)
ok(_막 and "쓰기" in _막, "쓰기가 막히면 설계도 안 한다")

# ------------------------------------------------------------------ 18. VM 에서 깨진 자리
#
# **실측 2026-09-21, VM 로그.** 다섯 에이전트가 줄줄이 죽었다:
#
#   Ethan   ValueError: min() iterable argument is empty
#   Marcus  KeyError: '코너'
#   Priya · Sofia · Kenji   ModuleNotFoundError: No module named 'weasyprint'
#
# 뿌리는 하나였다 -- `house/lib/nsw10.lib` 을 **.gitignore 에 넣어 놓고** 그것이
# 없을 때 만들지 않았다. 새로 받은 저장소(= VM)에는 그 파일이 없고, yosys 가
# `Can't open liberty file` 로 죽고, 그 위의 집계가 빈 목록에서 터졌다.
#
# **생성물을 커밋 안 하는 것은 옳다. 만들지 않은 것이 틀렸다.**
# 이 검사는 precheck 의 임시 워크트리(= HEAD 만 꺼낸 새 저장소)에서 돌므로,
# 바로 그 상황을 재현한다.
from house import synth as SYN  # noqa: E402

ok(not (뿌리 / "house" / "lib" / "nsw10.lib").exists()
   or True, "(참고) 이 저장소에 nsw10.lib 이 있든 없든 아래가 통과해야 한다")
_lib = SYN.라이브러리확인()
ok(_lib["있었나"] or _lib["만들었나"],
   "**표준셀 라이브러리가 없으면 스스로 만든다** — 커밋 안 된 생성물에 기대도 안 깨진다")
ok(SYN.LIB.exists(), f"만든 뒤에는 실제로 파일이 있다: {SYN.LIB.name}")
ok((뿌리 / "lab" / "lib" / "se10.lib").exists(),
   "**원본(lab/lib/se10.lib)은 커밋되어 있다** — 없으면 만들 수가 없다")

# 합성이 실제로 돈다 (라이브러리 자동 생성 뒤)
import shutil as _sh  # noqa: E402
if _sh.which("yosys"):
    _r = SYN.합성({"TAPS": 4, "STAGES": 2})
    ok(_r.get("됐나"), f"라이브러리 자동 생성 뒤 합성이 돈다 (셀 {_r.get('셀수')}개)")
else:
    ok(True, "(yosys 가 없다 — 합성 검사는 건너뛴다. CI 가 본다)")

# weasyprint 를 requirements 가 싣고 있나 -- **사람에게 설치를 시키지 않는다**
_req = (뿌리 / "requirements.txt").read_text(encoding="utf-8")
ok("weasyprint" in _req,
   "**weasyprint 가 requirements.txt 에 있다** — 배포가 깐다, 사람을 시키지 않는다")
ok(RPT.PDF된다().get("된다") is not None, "PDF 가 되는지 미리 물을 수 있다")
_pd = RPT.PDF된다()
ok("고치는법" in _pd or _pd["된다"], "안 되면 고치는 법을 같이 말한다")

# 집계가 빈 목록에서 안 죽는다 (Ethan 이 죽은 그 줄)
_빈스윕 = [{"파라": {"TAPS": 4}, "실패": "liberty 없음"}]
_면적들 = [x.get("면적") for x in _빈스윕 if isinstance(x.get("면적"), (int, float))]
ok(_면적들 == [], "스윕이 다 실패하면 면적 목록이 빈다 (이때 min() 을 부르면 죽는다)")
_rtl = (뿌리 / "house" / "rtl" / "agent.py").read_text(encoding="utf-8")
ok("면적들 = [" in _rtl and "if 면적들:" in _rtl,
   "**Ethan 의 보고서가 빈 목록을 막는다** — 실패는 죽을 일이 아니라 적을 일이다")
_syn = (뿌리 / "house" / "syn" / "agent.py").read_text(encoding="utf-8")
ok('"코너" not in m' in _syn,
   "**Marcus 의 보고서가 '코너' 없는 경우를 받는다** — 합성 실패도 보고서로 낸다")
_rep = (뿌리 / "house" / "report.py").read_text(encoding="utf-8")
ok("htm.write_text" in _rep and _rep.index("htm.write_text") < _rep.index("from weasyprint"),
   "**HTML 을 PDF 보다 먼저 쓴다** — PDF 단계가 죽어도 내용은 남는다")

# ------------------------------------------------------------------ 9. 메일이 자동으로 나가나
# 사용자(2026-09-21): "이메일로 보고서 자동으로 보내야지. 그렇게 만들어."
# 그 전에는 `메일` 이라고 **말해야만** 나갔고, `!회사 설계` 는 아예 메일 길이 없었다.
# 백그라운드로 도는 일의 결과가 디스크에만 남는 것은 낸 것이 아니다.
import relay as _R  # noqa: E402

_R.배경들.clear()
_뜬것 = {}


def _가짜Popen(명, **kw):
    _뜬것["명"] = 명

    class _P:
        pid = 4242
    return _P()


_진짜Popen, _진짜도나 = C.subprocess.Popen, C._도나
C.subprocess.Popen = _가짜Popen
C._도나 = lambda: ["4242 python3 house/run.py --설계 x"]
try:
    r = C._띄우기(["--설계", "무엇"], "arch")
    ok(r["떴나"], "띄운 것을 pgrep 으로 확인한 뒤에만 '떴다' 고 한다")
    ok(len(_R.배경들) == 1,
       "**끝나면 알리도록 배경 감시에 등록한다** -- 전에는 하우스만 이 줄이 빠져 있었다")
    _e = _R.배경들[0]
    ok(_e["찾을말"].isascii(),
       f"**찾을말이 아스키다** ({_e['찾을말']}) -- pgrep 은 이 로캘에서 한글에 영영 안 맞고, "
       "안 맞는 것은 '끝났다' 로 읽혀 빈 로그를 보고하게 된다")
    ok(_e["시작바이트"] == 0, "로그가 실행마다 새 파일이라 처음부터 읽는다")
finally:
    C.subprocess.Popen, C._도나 = _진짜Popen, _진짜도나
    _R.배경들.clear()

# 메일은 **기본으로 켜진다**. 끄려면 말해야 한다 -- 예전과 반대다.
_인자 = {}
_진짜띄우기 = C._띄우기
C._띄우기 = lambda 인자, 이름: (_인자.update(인자=인자, 이름=이름),
                          {"떴나": True, "로그": Path("/tmp/x.log"), "프로세스": ["p"]})[1]
try:
    C.run("!회사 전체", allow_write=True)
    ok("--메일" in _인자["인자"],
       f"**`메일` 이라고 말하지 않아도 메일이 나간다** ({_인자['인자']})")
    C.run("!회사 전체 메일없이", allow_write=True)
    ok("--메일" not in _인자["인자"], "`메일없이` 로 끌 수 있다 -- 장치에는 끄는 길이 있어야 한다")
    C.run("!회사 설계 8탭 FIR 가속기 0.9V 500MHz 자동차용", allow_write=True)
    ok(_인자["인자"][0] == "--설계" and "--메일" in _인자["인자"],
       f"**제안서도 메일로 나간다** ({_인자['인자'][:1]}…) -- 전에는 그 길이 아예 없었다")
finally:
    C._띄우기 = _진짜띄우기

# 못 보낼 것을 **미리** 말한다. 여섯 분 돌고 나서 "주소를 모른다" 로 끝나면
# 그 여섯 분이 버려지고, 사람은 오지 않을 메일을 기다린다.
_m = C.메일된다()
ok(set(_m) == {"된다", "빠진", "말"}, "메일 준비 상태를 묻는 길이 있다")
ok(_m["된다"] is (not _m["빠진"]), "빠진 것이 있으면 '안 된다'")
if not _m["된다"]:
    ok(all(("!열쇠 " + k) in _m["말"] for k in _m["빠진"]),
       f"**무엇을 주면 되는지까지 말한다** ({_m['말'][:60]})")
    ok("⚠" in C._메일줄(True) and "그대로 돌고" in C._메일줄(True),
       "못 보내도 일은 돌린다고 적는다 -- 메일이 없다고 설계를 멈추지 않는다")
else:
    ok("📧" in C._메일줄(True), "보낼 수 있으면 보낸다고 적는다")
ok("메일없이" in C._메일줄(False), "끈 상태도 그렇게 적는다")



# ------------------------------------------------------------------ 10. 리스트가 메일을 막는다
# 실측 2026-09-22: 제안서는 멀쩡히 나왔는데(5쪽 · 블록 7 · 포트 22) **메일이 한 통도
# 안 나갔다.** 까닭은 요약 한 줄이 이랬다:
#
#     코드가 글에서 읽은 것 — 쓰임새 없음 · 문제 ['속도', '면적', '정밀도'] ·
#     회로 ['AXI', 'FIFO']
#
# 파이썬 리스트를 f-string 에 그대로 박은 것이고, `mailer.자리표들` 이 그 대괄호를
# **"안 채운 자리표"** 로 읽었다. 같은 관문에 막힌 것이 두 번째다(처음은 제목의 `[보고]`).
from house import arch as _ARCH  # noqa: E402
from house import spec as _SP  # noqa: E402

ok(_ARCH._묶음(["속도", "면적", "정밀도"]) == "속도 · 면적 · 정밀도",
   "**목록을 사람이 읽는 글로 푼다** -- `['속도', '면적']` 이 아니라 `속도 · 면적`")
ok(_ARCH._묶음([]) == "없음" and _ARCH._묶음(None) == "없음", "비면 '없음'")
ok(_ARCH._묶음("이미 글") == "이미 글", "글은 그대로 둔다")

_깨진줄 = f"문제 {['속도', '면적']} · 회로 {['AXI']}"
ok(mailer.자리표들(_깨진줄) != [],
   "**깨진 꼴이 실제로 관문에 걸린다** -- 이 검사가 그 사고를 재현한다")
_고친줄 = f"문제 {_ARCH._묶음(['속도', '면적'])} · 회로 {_ARCH._묶음(['AXI'])}"
ok(mailer.자리표들(_고친줄) == [], "고친 꼴은 안 걸린다")

# **메일 본문 전체**를 관문에 통과시켜 본다. 어느 줄이 깨져도 여기서 잡힌다.
# **비슷한 것을 재지 말고 그것을 재라.**
#
# 실측 2026-09-22: 위 검사는 손으로 쓴 줄(`_고친줄`)을 쟀고 **통과했다.** 그런데 메일은
# 또 막혔다 -- 진짜 요약 줄에는 `[모델]` 이라는 출처 표시가 붙어 있었고 그것이 자리표로
# 읽혔기 때문이다. 같은 관문에 막힌 **세 번째**이고, 그 중 하나는 **내가 앞의 것을
# 고치면서 넣은 것**이다.
#
# 그래서 줄을 만드는 자리를 함수(`arch.판독줄`)로 빼고, 검사가 **그것을 부른다.**
_진짜스펙 = _SP.스펙(쓰임새=["계측/시험장비"], 문제=["속도", "면적"],
                 회로=["AXI", "FIFO"], 수={"주파수_Hz": [5e8]},
                 출처={"쓰임새": "모델 제안", "문제": "글에서 읽음"})
_진짜줄 = _ARCH.판독줄(_진짜스펙)
ok("모델 제안" in _진짜줄, "모델이 채운 칸에 출처가 붙는다")
ok(mailer.자리표들(_진짜줄) == [],
   f"**제안서가 실제로 찍는 그 줄이 관문을 통과한다** ({_진짜줄[:60]})")
ok("[" not in _진짜줄,
   "**출처 표시에 대괄호를 안 쓴다** -- mailer 는 `[...]` 를 전부 빈칸으로 보고, "
   "그것이 옳다(봐주면 진짜 빈칸을 놓친다)")

_본문 = RPT.mail_body(P.ETHAN, "MERA-1 v1.0",
                    [_진짜줄, "<b>아직 모르는 것 5개</b> — 정하기 전에는 RTL 을 안 짓는다"],
                    ["This is a proposal, not a design."],
                    attachment_name="20260922_제안서.pdf")
ok(mailer.자리표들(_본문, _MA.말머리) == [],
   "**조립된 메일 본문이 자리표 관문을 통과한다** -- 손으로 쓴 줄이 아니라 진짜 줄로")


# **판독이 0칸이면 돌리지 않는다.** 실측 2026-09-21: 요청 31자("MERA-1 v1.0 Event
# Recorder Core")로 3.3초를 돌려 **빈 제안서**가 나왔다 -- 쓰임새·문제·회로 전부
# 못 읽음, 검증 시나리오 다섯 칸이 전부 "모름", 제안 블록은 "외부 아날로그" 하나.
# 보고서가 "13개가 비어 있다" 고 정직하게 적었지만 정직함이 비용을 없애지는 않는다.
_빈 = C.run("!회사 설계 MERA-1 v1.0 Event Recorder Core", allow_write=True)
ok("돌리지 않았습니다" in _빈,
   "**아무것도 못 읽은 요청은 안 돌린다** -- 모델을 부르기 전에 막는 것이 싸다")
ok("31자" in _빈, "받은 글이 몇 자였는지 그대로 보여준다")
ok("100 MHz" in _빈 and "1.8 V" in _빈,
   "**그냥 돌리면 무엇이 기본값으로 채워지는지 말한다** -- 그 수가 틀리면 아래가 다 틀린다")
ok("Shift+Enter" in _빈, "여러 줄을 한 번에 보내는 법까지 적는다 (디스코드는 Enter 로 보낸다)")

_찬 = C.run("!회사 설계 계측장비용 FIR 가속기. 목표 500 MHz 0.8V, 속도가 문제다",
          allow_write=False)
ok("돌리지 않았습니다" not in (_찬 or ""),
   "읽히는 요청은 이 관문에 안 걸린다 -- 관문이 멀쩡한 요청을 막으면 안 된다")


# run.py 쪽: 제안서 메일이 **첨부와 함께** 나가는 길인가 (글만 보내지 않는다)
import inspect  # noqa: E402
from house import run as _RUN  # noqa: E402
_src = inspect.getsource(_RUN.설계하기)
ok("메일보내기" in _src, "제안서도 같은 메일 길을 쓴다 (첨부 없는 발송을 거부하는 그 길)")
ok("_제안서특이사항" in _src,
   "**아직 모르는 칸이 메일 2번 항목에 올라간다** -- 첨부를 안 열어도 할 일이 보인다")
_특 = _RUN._제안서특이사항({"쪽": 3, "그림수": 2, "모른다": ["동작 주파수"], "선행조사": "p.md"})
ok(any("Needs your decision" in x for x in _특), "사람이 정해야 하는 칸을 그렇게 적는다")
ok(any("not a design" in x for x in _특),
   "**제안서는 설계가 아니라고 못 박는다** -- 받는 사람이 다 된 줄 알면 안 된다")

# ------------------------------------------------------------------ 11. 낱말표가 문이 아니다
# 사용자(2026-09-22): "파이썬 조건문으로 쓰지 말고, LLM 이 한번 개입해주면 안되?
# 너무 hard 한데 format 이" · **"나는 너의 도움 없이 돌아가는 discord bot 을 만들고 싶어."**
#
# 실측: 요청이 "계측·시험장비용" 이라고 **글자 그대로** 적었는데 판독이 `쓰임새 없음`
# 을 냈다 -- 낱말표에 그 말이 없어서다. 그러면 IP 가 바뀔 때마다 사람이 표를 고쳐
# 줘야 하고, 그것은 봇이 혼자 도는 것이 아니다.
import json as _json  # noqa: E402

_s = _SP.읽기("계측·시험장비용 이벤트 레코더를 설계한다")
ok(not _s.쓰임새,
   "**낱말표는 제가 아는 것만 읽는다** -- '계측·시험장비용' 이 글에 있는데도 못 읽는다")

def _가짜모델(글):
    ok("판독" in 글, "프롬프트가 모델에게 **판독 칸을 채우라고** 말한다")
    return _json.dumps({"판독": {"쓰임새": ["계측/시험장비"], "문제": ["속도"],
                               "회로": ["FIFO"], "수": {"주파수_Hz": [5e8]}},
                        "이름": "nsw_er", "한줄": "이벤트 레코더"})

_s2 = _SP.다듬기(_SP.읽기("계측·시험장비용 이벤트 레코더를 설계한다"), 묻기=_가짜모델)
ok(_s2.쓰임새 == ["계측/시험장비"],
   "**모델이 빈 칸을 읽는다** -- 표에 없는 말도 이제 들어온다")
ok(_s2.출처.get("쓰임새") == "모델 제안",
   "**어디서 온 값인지 칸마다 적는다** -- 안 적으면 읽는 사람이 전부 글에 있던 줄 안다")
ok(_s2.수.get("주파수_Hz") == [5e8], "수도 받아 넣는다 (숫자로 바꿔서)")

# **규칙이 읽은 것을 모델이 뒤집지 못한다.** 규칙은 공짜이고 같은 답을 두 번 준다.
_규칙이읽음 = _SP.읽기("속도가 문제인 FIR 필터, 500 MHz")
ok(_규칙이읽음.문제 == ["속도"], "규칙이 '속도' 를 읽었다")
_뒤집기 = lambda 글: _json.dumps({"판독": {"문제": ["전력"], "쓰임새": [], "회로": [], "수": {}}})
_s3 = _SP.다듬기(_규칙이읽음, 묻기=_뒤집기)
ok(_s3.문제 == ["속도"],
   "**모델이 규칙의 판독을 못 뒤집는다** -- 빈 칸만 채운다")
ok(_s3.출처.get("문제") == "글에서 읽음", "출처도 그대로 '글에서 읽음'")

# 관문: 모델이 있으면 못 읽어도 안 막는다 (막으면 사람을 부르게 된다)
import house.gen as _G  # noqa: E402
_진짜쓸수, _진짜띄 = _G.쓸수있나, C._띄우기
try:
    # **발사대를 막는다.** 안 막으면 첫 호출이 진짜로 하우스를 띄우고, 두 번째
    # 호출은 관문이 아니라 "이미 돌고 있다" 로 가서 검사가 엉뚱한 것을 잰다
    # (실측 2026-09-22: 이 자리에서 두 줄이 빨갰다).
    C._띄우기 = lambda 인자, 이름: {"떴나": True, "로그": Path("/tmp/x.log"),
                                "프로세스": ["p"]}
    _G.쓸수있나 = lambda: {"모델키": 2, "도구없음": [], "됨": True}
    _답 = C.run("!회사 설계 zzz", allow_write=True)
    ok("돌리지 않았습니다" not in (_답 or ""),
       "**모델이 있으면 규칙이 못 읽어도 돌린다** -- 모델이 판독을 대신한다")
    _G.쓸수있나 = lambda: {"모델키": 0, "도구없음": [], "됨": False}
    _답2 = C.run("!회사 설계 zzz", allow_write=True)
    ok("돌리지 않았습니다" in (_답2 or ""),
       "모델도 없고 규칙도 못 읽으면 그때는 막는다 -- 정말로 아무도 못 읽는다")
    ok("모델 키가 있으면" in _답2, "왜 막혔는지 까닭을 적는다")
finally:
    _G.쓸수있나, C._띄우기 = _진짜쓸수, _진짜띄

# ---------------------------------------------------------------- 자연어가 회사에 닿는가
# **실측 2026-09-22.** 사용자가 실시간 FIR 필터 IP 를 물었고, 에이전트가
# `iverilog ... && vvp` · `yosys -s ...` 를 적으며 "PASS · 셀 2,474개" 로 답했다.
# **그 명령은 한 줄도 안 돌았다.** 사용자: "왜 회사로 답변안하지?"
# 그리고 `!회사 <자연어>` 를 쳤더니 "누구를 말하는지 모르겠다" 가 왔다.
# 사용자: "!회사 자연어로 되게 만들어. 스펙서 하나 제대로 못하면 뭐하자는거야?"
print()
print("[자연어] `설계` 라고 안 써도 회사가 받는가")
ok(C.요청으로읽히나("500MHz 8탭 FIR 필터 만들어줘"),
   "**짓자는 말 + 읽힌 칸이 있으면 요청으로 읽는다** (회로 FIR · 주파수 5e8)")
ok(not C.요청으로읽히나("자언어로 되게 만들어 스펙서 하나 제대로 못하면 뭐하자는거야? 이게 회사야?"),
   "**불만은 요청이 아니다** -- '만들어' 가 들어 있어도 읽힌 칸이 0이면 안 돌린다")
ok(not C.요청으로읽히나("오늘 날씨 어때"), "짓자는 말이 없으면 애초에 아니다")

# **발사대와 `_도나()` 를 둘 다 막는다.** 안 막으면 검사가 진짜 하우스를 띄우고
# (실측 2026-09-22: `house/run.py --메일` 이 실제로 돌았다), 그 뒤의 검사는 관문이
# 아니라 "이미 돌고 있다" 를 재게 된다.
_진짜띄2, _진짜쓸2, _진짜도나2 = C._띄우기, _G.쓸수있나, C._도나
try:
    C._도나 = lambda: []
    _띄운것 = {}
    C._띄우기 = lambda 인자, 이름: (_띄운것.update(인자=인자),
                                {"떴나": True, "로그": Path("/tmp/x.log"), "프로세스": ["p"]})[1]
    _G.쓸수있나 = lambda: {"모델키": 2, "도구없음": [], "됨": True}

    _답 = C.run("!회사 500MHz 8탭 FIR 필터 만들어줘", allow_write=True)
    ok("누구를 말하는지" not in (_답 or ""),
       "**`설계` 를 빼고 쳐도 안 혼난다** -- 이름이 아니면 요청으로 읽는다")
    ok("제안서를 짓고 있습니다" in (_답 or ""), f"실제로 띄운다 ({(_답 or '')[:40]!r})")
    ok(_띄운것.get("인자", [None])[0] == "--설계",
       f"`house/run.py --설계` 로 넘어간다 ({_띄운것.get('인자')})")

    _불만 = C.run("!회사 자언어로 되게 만들어 스펙서 하나 제대로 못하면 뭐하자는거야?",
                allow_write=True)
    ok("누구를 말하는지" in (_불만 or ""), "요청으로 안 읽히면 예전처럼 되묻는다")
    ok("만들 것을 그냥 적어도 됩니다" in (_불만 or ""),
       "**그때 자연어로도 된다는 것을 알려 준다** -- 명령을 외우게 하지 않는다")

    # 회사로 넘기기 -- 에이전트가 재지 않고 수를 지어냈을 때의 길
    _r = C.설계로넘기기("실시간 FIR 필터 IP 를 만들어줘, 셀 수와 f_max 를 알려줘")
    ok(_r["돌았나"], f"**지어낸 답 대신 회사를 띄운다** ({_r['까닭']!r})")
    _글 = C.넘김글("실시간 FIR 필터 IP", _r)
    ok("버리고" in _글 and "회사" in _글,
       "**지어낸 답을 버렸다고 적는다** -- 조용히 바꿔치지 않는다")
    ok("셸 원장에 그 줄이 없습니다" in _글,
       "왜 버렸는지 근거를 적는다 (명령까지 지어냈다)")
finally:
    C._띄우기, _G.쓸수있나, C._도나 = _진짜띄2, _진짜쓸2, _진짜도나2

# 못 넘겼을 때는 버리지 않는다 -- 답이 통째로 사라지는 것이 더 나쁘다
_r2 = C.설계로넘기기("FIR 필터 만들어줘", allow_write=False)
ok(not _r2["돌았나"] and "쓰기" in _r2["까닭"], f"쓰기가 막히면 안 돈다 ({_r2['까닭']})")
_글2 = C.넘김글("FIR", _r2)
ok("못 넘겼습니다" in _글2, "**못 넘겼으면 못 넘겼다고 적는다**")
ok("!회사 설계" in _글2, "사람이 직접 돌릴 명령을 같이 준다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("house: 다섯 명 · 그림 없는 보고서 거부 · 첨부 없는 메일 거부 · 메일 양식 · "
      "GDSII 왕복 · HLS 자원한계 · 명령 배선 -- 통과")
