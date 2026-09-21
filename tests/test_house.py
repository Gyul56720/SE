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

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("house: 다섯 명 · 그림 없는 보고서 거부 · 첨부 없는 메일 거부 · 메일 양식 · "
      "GDSII 왕복 · HLS 자원한계 · 명령 배선 -- 통과")
