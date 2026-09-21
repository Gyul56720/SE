# -*- coding: utf-8 -*-
"""house/people -- 다섯 명의 엔지니어.

한 사람이 아니라 **직무**다. 이름을 붙이는 까닭은 보고서에 서명할 주체가 있어야
하고(사내 메일 양식이 그것을 요구한다), 다섯 보고서가 서로 다른 책임에서 나왔다는
것이 한눈에 보여야 하기 때문이다.

각 사람은 `직무`(무엇을 책임지나) · `도구`(실제로 부르는 것) · `산출물`(무엇을
남기나) 를 가진다. **도구 칸에 적힌 것은 실제로 이 저장소에서 돌아가는 것뿐이다** --
상용 도구(VCS · Verdi · DC · ICC2 · Tessent · PrimeTime) 는 이 기계에 없다. 없는
것을 쓴 것처럼 적지 않는다. 대신 같은 일을 하는 대안을 저장소 안에 짓고, 보고서에
"무엇으로 쟀는지" 를 매번 적는다.
"""
from __future__ import annotations

회사 = "Nowon Silicon Works"
회사약칭 = "NSW"
도메인 = "nowonsilicon.dev"          # 메일 서명용 표기. 실제 발신은 SMTP_USER 계정이다.


class 사람:
    def __init__(self, 키, 이름, 직급, 팀, 직무, 도구, 산출물, 한줄, 대명사="they/them"):
        self.키 = 키
        self.이름 = 이름
        self.직급 = 직급
        self.팀 = 팀
        self.직무 = 직무
        self.도구 = 도구
        self.산출물 = 산출물
        self.한줄 = 한줄
        self.대명사 = 대명사

    @property
    def 메일(self) -> str:
        first = self.이름.split()[0].lower()
        last = self.이름.split()[-1].lower()
        return f"{first}.{last}@{도메인}"

    @property
    def 서명(self) -> str:
        return f"{회사} / {self.팀} / {self.직급}"

    def __repr__(self):
        return f"<사람 {self.키} {self.이름}>"


# --------------------------------------------------------------------------
# 다섯 명. 직무는 사용자가 정한 다섯 가지 그대로다 -- RTL(+HLS) · DV · PI(합성) ·
# DFT · PD. 여자 둘(Priya · Sofia)을 포함한다.
# --------------------------------------------------------------------------

ETHAN = 사람(
    "rtl", "Ethan Ross", "Staff Engineer", "Front-End Design",
    직무="HLS 및 RTL 설계 -- C++ 동작 기술에서 스케줄링·바인딩으로 RTL 을 뽑고(HLS), "
       "SystemVerilog 로 FSM 제어 흐름 · 파이프라인 · 파라미터 재사용 · 클럭/리셋 구조 · "
       "클럭 게이팅 전력 최적화 · CDC 를 설계한다.",
    도구=["house/hls (자체 HLS: DFG → 스케줄 → 바인딩 → SV 생성)",
        "verilator 5.020 --lint-only -Wall (RTL lint)",
        "iverilog / vvp (elaborate · 기능 확인)",
        "house/rtl/cdc.py (CDC 정적 점검 -- 도메인 전파 · 동기화기 인식)"],
    산출물=["SystemVerilog RTL", "FSM 상태표/상태도", "파이프라인 예약표",
         "CDC 경계 목록", "클럭 게이팅 전/후 토글 비교"],
    한줄="스펙을 돌아가는 논리로 바꾸고, 그 논리가 왜 그 모양인지 수로 설명한다.",
    대명사="he/him")

PRIYA = 사람(
    "dv", "Priya Raghavan", "Verification Lead", "Design Verification",
    직무="UVM 꼴 검증 환경을 세우고 제약 랜덤으로 수천~수만 거래를 던져 스코어보드로 "
       "판정한다. 기능/코드 커버리지를 닫고, 자해 검사(mutation)로 '검사기가 정말 "
       "무는지' 를 증명한다. 검증이 끝났다는 말은 커버리지 수와 변이 결과로만 한다.",
    도구=["verilator 5.020 (--cc, C++ 하네스) -- 초당 수십만 주기",
        "house/dv/uvm_like.py (agent/driver/monitor/scoreboard/coverage 구조)",
        "house/dv/mutate.py (RTL 변이 주입 -- 검사기가 무는지 증명)",
        "iverilog/vvp (교차 확인용 두 번째 시뮬레이터)"],
    산출물=["커버리지 닫기 곡선", "크로스 커버리지 히트맵", "변이 생존표",
         "거래별 불일치 로그", "회귀 통계(시드·주기·에러)"],
    한줄="코드를 다 짰다는 것은 아무것도 증명하지 않는다. 수만 번 던져 본 것만 증명한다.",
    대명사="she/her")

MARCUS = 사람(
    "syn", "Marcus Webb", "Principal Engineer", "Synthesis & Physical Implementation (PI)",
    직무="RTL 을 넷리스트로 바꾸고 SDC 제약을 물려 PVT 코너 전체에서 STA 를 돌린다. "
       "전압·온도·공정이 바뀌어도 타이밍이 서는지, UPF 전원 도메인이 실제로 꺼지고 "
       "켜지는지를 수로 확인한다.",
    도구=["yosys (합성 -- 실제 도구)",
        "house/syn/sdc.py (SDC 파서: create_clock · set_input_delay · false/multicycle)",
        "house/syn/sta_pvt.py (lab/se/sta 를 PVT 코너로 확장 · OCV 디레이트)",
        "house/syn/upf.py (UPF-lite: 전원 도메인 · 아이솔레이션 · 리테션 점검)"],
    산출물=["코너별 슬랙 표/그래프", "임계경로 단계별 지연 분해", "전력 분해(동적/누설)",
         "온도 반전 곡선", "UPF 도메인 상태표"],
    한줄="한 코너에서 도는 것은 도는 것이 아니다. 216개 코너에서 도는 것이 도는 것이다.",
    대명사="he/him")

SOFIA = 사람(
    "dft", "Sofia Almeida", "Senior Engineer", "Design for Test",
    직무="스캔 체인을 넣어 내부를 들여다보게 만들고, ATPG 로 패턴을 만들고, BIST 로 "
       "칩이 스스로를 시험하게 한다. 수백만 개를 찍어낼 때 나쁜 다이가 몇 개나 "
       "새어 나가는지(DPPM)를 셈해 커버리지 목표를 정한다.",
    도구=["house/dft/scan.py (스캔 삽입 · 체인 순서 · 시프트 길이)",
        "house/dft/atpg.py (무작위 + 결정적 ATPG · 병렬 패턴 고장 시뮬)",
        "house/dft/bist.py (MBIST March C- · LBIST LFSR/MISR 서명)",
        "house/dft/yield_.py (Williams-Brown DL · 몬테카를로 대조)"],
    산출물=["고장 커버리지 곡선", "패턴 수 대 시험시간/값", "체인 길이 대 압축비",
         "MBIST March 알고리즘 표", "DPPM 대 커버리지 곡선"],
    한줄="시험은 좋은 다이를 증명하지 않는다. 나쁜 다이가 몇 개 새는지를 한계 지을 뿐이다.",
    대명사="she/her")

KENJI = 사람(
    "pd", "Kenji Tanaka", "Staff Engineer", "Physical Design",
    직무="플로어플랜으로 블록과 전원 격자를 놓고, 배치·배선으로 잇고, CTS 로 클럭을 "
       "고르게 퍼뜨리고, 사인오프 검사를 통과시킨 뒤 GDSII 를 낸다.",
    도구=["house/pd (lab/se 의 floorplan·place·cts·route·signoff 를 확장)",
        "house/pd/gds.py (GDSII stream 바이너리 직접 기록 -- 실제 규격)",
        "house/pd/drc.py (간격·최소폭·밀도 규칙 검사)",
        "klayout 없음 -> GDS 를 자체 파서로 되읽어 왕복 검증"],
    산출물=["플로어플랜/배치 도면", "혼잡도 히트맵", "클럭 트리 도면과 스큐 분포",
         "IR 강하 지도", "GDSII 파일과 층별 도형 수"],
    한줄="앞의 넷이 옳아도 여기서 지면 칩은 없다. 기하는 흥정하지 않는다.",
    대명사="he/him")

모두 = [ETHAN, PRIYA, MARCUS, SOFIA, KENJI]
키로 = {p.키: p for p in 모두}
이름으로 = {p.이름.lower(): p for p in 모두}

# 별칭 -- 디스코드에서 사람이 치는 말. "!회사 검증" · "!회사 priya" 둘 다 받는다.
별칭 = {
    "rtl": "rtl", "설계": "rtl", "hls": "rtl", "frontend": "rtl", "ethan": "rtl", "ross": "rtl",
    "dv": "dv", "검증": "dv", "verification": "dv", "uvm": "dv", "priya": "dv", "raghavan": "dv",
    "syn": "syn", "합성": "syn", "pi": "syn", "sta": "syn", "synthesis": "syn",
    "marcus": "syn", "webb": "syn",
    "dft": "dft", "테스트": "dft", "scan": "dft", "atpg": "dft", "sofia": "dft", "almeida": "dft",
    "pd": "pd", "물리설계": "pd", "레이아웃": "pd", "layout": "pd", "gds": "pd",
    "kenji": "pd", "tanaka": "pd",
}


def 찾기(말: str):
    """사람이 친 말에서 담당자를 고른다.  못 고르면 None."""
    t = (말 or "").strip().lower()
    if not t:
        return None
    if t in 별칭:
        return 키로[별칭[t]]
    for k, v in 별칭.items():
        if k in t:
            return 키로[v]
    return None


def 조직도글() -> str:
    """디스코드에 그대로 붙일 수 있는 한 화면짜리 조직도."""
    줄 = [f"**{회사}** ({회사약칭}) -- 1인 디자인 하우스, 엔지니어 5명", ""]
    for p in 모두:
        줄.append(f"· **{p.이름}** -- {p.팀} / {p.직급}  (`!회사 {p.키}`)")
        줄.append(f"   {p.한줄}")
    return "\n".join(줄)
