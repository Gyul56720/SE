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

ok(len(P.모두) == 5, "다섯 명을 채용했다")
ok(len({p.키 for p in P.모두}) == 5, "직무 키가 겹치지 않는다")
ok(sum(1 for p in P.모두 if p.대명사 == "she/her") >= 1,
   "여자가 한 명 이상 있다 (사용자 요구)")
ok(all("@" in p.메일 for p in P.모두), "모두 메일 주소가 있다")
ok(P.찾기("검증") is P.PRIYA and P.찾기("priya") is P.PRIYA
   and P.찾기("dv") is P.PRIYA, "한글·영문이름·직무키 셋 다로 사람을 찾는다")
ok(P.찾기("물리설계") is P.KENJI and P.찾기("gds") is P.KENJI, "PD 별칭")
ok(P.찾기("") is None and P.찾기("점심메뉴") is None, "모르는 말에는 None")
ok(all(k in P.별칭 for k in ("rtl", "dv", "syn", "dft", "pd")),
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
ok("<svg" in h and "그림 1." in h, "그림을 넣으면 HTML 이 나오고 번호가 붙는다")
ok(P.ETHAN.이름 in h and P.ETHAN.팀 in h, "작성자(누가 한 일인지)가 문서에 박힌다")

# **마크다운 별표가 날것으로 안 나간다** (실측: 보고서 1쪽에 `**있는**` 이 찍혔다)
R2 = RPT.보고서(P.PRIYA, "검사2", "과제")
R2.요약("**굵게** 되어야 한다")
R2.그림(V.빈그림("x"))
ok("<b>굵게</b>" in R2.html() and "**굵게**" not in R2.html(),
   "`**x**` 가 굵게 바뀐다 -- 별표가 PDF 에 날것으로 안 찍힌다")

# ------------------------------------------------------------------ 3. 메일 양식
본문 = RPT.메일본문(P.SOFIA, "NSW-FIR v1.0", ["커버리지 94.9 %", "남은 고장 442개"],
                ["결정적 ATPG 를 표본으로만 쳤습니다"], 첨부이름="보고서.pdf")
for 조각 in ("안녕하세요", "1. 주요 진행 상황 (요약)", "2. 특이사항 및 요청/문의 사항",
           "소속:", "이메일:", "올림"):
    ok(조각 in 본문, f"메일 양식에 «{조각}» 이 있다 (사용자가 준 양식)")
ok(P.SOFIA.이름 in 본문 and P.SOFIA.팀 in 본문 and P.SOFIA.직급 in 본문,
   "**어떤 직원인지 명시한다** (이름·팀·직급)")
ok("보고서.pdf" in 본문, "첨부 이름이 본문에 적힌다")
ok("커버리지 94.9 %" in 본문 and "표본으로만" in 본문,
   "요약과 특이사항이 둘 다 본문에 들어간다")
제목 = RPT.메일제목(P.SOFIA, "NSW-FIR v1.0")
ok(제목.startswith("[보고]") and P.SOFIA.이름 in 제목 and P.SOFIA.팀 in 제목,
   "메일 제목이 `[보고] ... _팀 이름` 꼴이다")

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
ok(잰것[0][2] >= 잰것[-1][2], "자원을 줄이면 II(개시 간격)도 는다")

# ------------------------------------------------------------------ 7. 디스코드 명령
from house import discord_cmd as C  # noqa: E402

ok(C.run("안녕") is None and C.run("!소설 상태") is None,
   "**모르는 말에는 None** -- 기존 동작을 뺏지 않는다")
ok(C.PREFIX == "!회사", "PREFIX 는 !회사")
조 = C.run("!회사")
ok(조 and all(p.이름 in 조 for p in P.모두), "`!회사` 가 다섯 명을 다 보인다")
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
_d = (뿌리 / "dispatch.py").read_text(encoding="utf-8")
ok("from house import discord_cmd as 하우스" in _d and "하우스)" in _d,
   "dispatch.py 의 명령 목록에 실려 있다 -- 디스코드에서 실제로 닿는다")
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

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("house: 다섯 명 · 그림 없는 보고서 거부 · 첨부 없는 메일 거부 · 메일 양식 · "
      "GDSII 왕복 · HLS 자원한계 · 명령 배선 -- 통과")
