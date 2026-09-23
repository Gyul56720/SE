# -*- coding: utf-8 -*-
"""house/sch -- **회로도를 그린다.** 넷리스트의 실제 셀을 게이트 기호로.

사용자: "회로도 또한 시각화해서 제시해야한다."

레이아웃 그림(`viz.레이아웃`)은 셀이 **어디 있나**를 보이지 사람이 **무엇인지**
읽게 해 주지 않는다 -- 빨간 네모 3,500개는 회로도가 아니다. 여기서는 셀 종류를
IEEE 게이트 기호로 바꿔 그린다. NAND 는 D 꼴에 동그라미, INV 는 삼각형에 동그라미,
MUX 는 사다리꼴, 플롭은 클럭 쐐기가 붙은 네모다.

**무엇을 그리나.** 4,308 셀을 다 그릴 수는 없다(그리면 아무도 못 읽는다). 그래서
**사인오프가 실제로 판정한 것** -- 임계경로 -- 를 그린다. 경로 위의 셀을 차례로
놓고, STA 가 그 셀에서 잰 지연을 기호 밑에 적는다. 그러면 그림 한 장이 "왜 이
주기에서 떨어졌나" 를 그 자리에서 답한다.

기호는 `lab/lib/se10.lib` 의 14셀 + LATX1 을 전부 덮는다:
    INVX1 INVX4 BUFX2 NAND2X1 NOR2X1 AND2X1 OR2X1 XOR2X1 XNOR2X1
    MUX2X1 AOI21X1 OAI21X1 DFFX1 DFFRX1 LATX1
"""
from __future__ import annotations

import re

from house.viz import (svg, _글, _선, _네모, _화살, 먹, 흐림, 빨강, 파랑, 초록, 주황,
                       빈그림)

# 셀 이름 -> 기호 꼴.  뒤의 구동세기(X1/X4)는 떼고 본다.
_꼴 = [
    (r"^INV", "inv"), (r"^BUF", "buf"),
    (r"^NAND", "nand"), (r"^NOR", "nor"),
    (r"^AND", "and"), (r"^OR", "or"),
    (r"^XNOR", "xnor"), (r"^XOR", "xor"),
    (r"^MUX", "mux"),
    (r"^AOI", "aoi"), (r"^OAI", "oai"),
    (r"^DFFR", "dffr"), (r"^DFF", "dff"), (r"^LAT", "lat"),
]

핀이름 = {
    "inv": (["A"], "Y"), "buf": (["A"], "Y"),
    "nand": (["A", "B"], "Y"), "nor": (["A", "B"], "Y"),
    "and": (["A", "B"], "Y"), "or": (["A", "B"], "Y"),
    "xor": (["A", "B"], "Y"), "xnor": (["A", "B"], "Y"),
    "mux": (["A", "B", "S"], "Y"),
    "aoi": (["A1", "A2", "B"], "Y"), "oai": (["A1", "A2", "B"], "Y"),
    "dff": (["D", "CK"], "Q"), "dffr": (["D", "CK", "RN"], "Q"),
    "lat": (["D", "G"], "Q"),
}

식 = {
    "inv": "!A", "buf": "A", "nand": "!(A&B)", "nor": "!(A|B)",
    "and": "A&B", "or": "A|B", "xor": "A^B", "xnor": "!(A^B)",
    "mux": "(A&!S)|(B&S)", "aoi": "!((A1&A2)|B)", "oai": "!((A1|A2)&B)",
    "dff": "Q <= D @posedge", "dffr": "Q <= D @posedge, RN", "lat": "Q = D when G",
}


def 꼴찾기(셀종류: str) -> str:
    t = (셀종류 or "").upper().lstrip("\\")
    for 패턴, 이름 in _꼴:
        if re.match(패턴, t):
            return 이름
    return "box"


# ------------------------------------------------------------------ 기호 하나

def 기호(꼴, x, y, w=36, h=30, 채움="#ffffff", 선색=None, 굵기=1.5) -> str:
    """게이트 기호 하나를 (x, y) 왼쪽 위 기준으로 그린다.  출력은 오른쪽 가운데."""
    선색 = 선색 or 먹
    m = []
    cy = y + h / 2
    동 = 3.0                                   # 부정 동그라미 반지름

    def 원(cx, ccy, r=동):
        return (f'<circle cx="{cx:.1f}" cy="{ccy:.1f}" r="{r:.1f}" '
                f'fill="#fff" stroke="{선색}" stroke-width="{굵기}"/>')

    def D꼴(x0, w0, 부정):
        """AND 계열 -- 왼쪽 직선, 오른쪽 반원."""
        r = h / 2
        d = (f"M{x0:.1f},{y:.1f} L{x0+w0-r:.1f},{y:.1f} "
             f"A{r:.1f},{r:.1f} 0 0 1 {x0+w0-r:.1f},{y+h:.1f} "
             f"L{x0:.1f},{y+h:.1f} Z")
        s = (f'<path d="{d}" fill="{채움}" stroke="{선색}" stroke-width="{굵기}"/>')
        if 부정:
            s += 원(x0 + w0 + 동, cy)
        return s

    def 방패(x0, w0, 부정, 두겹=False):
        """OR 계열 -- 오목한 왼쪽, 뾰족한 오른쪽."""
        d = (f"M{x0:.1f},{y:.1f} Q{x0+w0*0.55:.1f},{y:.1f} {x0+w0:.1f},{cy:.1f} "
             f"Q{x0+w0*0.55:.1f},{y+h:.1f} {x0:.1f},{y+h:.1f} "
             f"Q{x0+w0*0.28:.1f},{cy:.1f} {x0:.1f},{y:.1f} Z")
        s = f'<path d="{d}" fill="{채움}" stroke="{선색}" stroke-width="{굵기}"/>'
        if 두겹:                                # XOR 의 바깥 활
            s = (f'<path d="M{x0-5:.1f},{y:.1f} Q{x0+w0*0.28-5:.1f},{cy:.1f} '
                 f'{x0-5:.1f},{y+h:.1f}" fill="none" stroke="{선색}" '
                 f'stroke-width="{굵기}"/>') + s
        if 부정:
            s += 원(x0 + w0 + 동, cy)
        return s

    if 꼴 == "inv" or 꼴 == "buf":
        d = (f"M{x:.1f},{y:.1f} L{x+w-6:.1f},{cy:.1f} L{x:.1f},{y+h:.1f} Z")
        m.append(f'<path d="{d}" fill="{채움}" stroke="{선색}" stroke-width="{굵기}"/>')
        if 꼴 == "inv":
            m.append(원(x + w - 6 + 동, cy))
    elif 꼴 in ("and", "nand"):
        m.append(D꼴(x, w - 6, 꼴 == "nand"))
    elif 꼴 in ("or", "nor"):
        m.append(방패(x, w - 6, 꼴 == "nor"))
    elif 꼴 in ("xor", "xnor"):
        m.append(방패(x, w - 6, 꼴 == "xnor", 두겹=True))
    elif 꼴 == "mux":
        d = (f"M{x:.1f},{y:.1f} L{x+w:.1f},{y+7:.1f} "
             f"L{x+w:.1f},{y+h-7:.1f} L{x:.1f},{y+h:.1f} Z")
        m.append(f'<path d="{d}" fill="{채움}" stroke="{선색}" stroke-width="{굵기}"/>')
        m.append(_글(x + w / 2, cy + 3, "M", 8.5, 흐림, "middle"))
    elif 꼴 in ("aoi", "oai"):
        # 두 단짜리: 앞단(AND 또는 OR) + 뒷단 NOR/NAND
        앞 = D꼴 if 꼴 == "aoi" else 방패
        m.append(앞(x, w * 0.46, False))
        뒤 = 방패 if 꼴 == "aoi" else D꼴
        m.append(_선(x + w * 0.46, cy - h * 0.22, x + w * 0.54, cy - h * 0.22, 선색, 굵기))
        m.append(뒤(x + w * 0.54, w * 0.40, True))
    elif 꼴 in ("dff", "dffr", "lat"):
        m.append(_네모(x, y - 4, w, h + 8, 채움, 선색, 굵기, 2))
        m.append(_글(x + w / 2, y + 8, "D" if 꼴 != "lat" else "G", 8, 흐림, "middle"))
        # 클럭 쐐기
        m.append(f'<path d="M{x:.1f},{y+h-2:.1f} L{x+7:.1f},{y+h+2:.1f} '
                 f'L{x:.1f},{y+h+6:.1f}" fill="none" stroke="{선색}" '
                 f'stroke-width="{굵기}"/>')
        m.append(_글(x + w / 2, y + h, "FF" if 꼴 != "lat" else "L", 8.5, 흐림, "middle"))
    else:
        m.append(_네모(x, y, w, h, 채움, 선색, 굵기, 2))
    return "".join(m)


def 출력점(꼴, x, y, w=36, h=30):
    if 꼴 in ("dff", "dffr", "lat", "box", "mux"):
        return (x + w, y + h / 2)
    if 꼴 in ("inv", "nand", "nor", "xnor"):
        return (x + w - 6 + 6, y + h / 2)
    return (x + w, y + h / 2)


# ------------------------------------------------------------------ 경로 회로도

def 경로도(단계들, 제목="", 폭=640, 주기_ps=None, 슬랙_ps=None,
         setup_ps=None, 클럭_ps=None, 한줄=7) -> str:
    """임계경로를 **게이트 기호의 사슬**로 그린다.

    단계들 = [{"셀": "NAND2X1", "인스턴스": "$auto$...", "핀": "Y",
              "증분_ps": 28.4, "도착_ps": 412.0, "이음": "A->Y"}]
    첫 단계는 보통 발사 플롭(DFFX1), 마지막은 포착 플롭의 D 다.
    """
    if not 단계들:
        return 빈그림("임계경로를 못 뽑았다")
    n = len(단계들)
    줄수 = (n + 한줄 - 1) // 한줄
    칸 = (폭 - 40) / 한줄
    기호폭, 기호높이 = min(40.0, 칸 * 0.46), 30.0
    줄높이 = 96
    y0 = 34 if 제목 else 12
    머리 = 30 if (주기_ps or 슬랙_ps) else 0
    높이 = y0 + 머리 + 줄수 * 줄높이 + 26
    m = []

    if 머리:
        글 = []
        if 주기_ps is not None:
            글.append(f"주기 {주기_ps:,.0f} ps")
        if 클럭_ps is not None:
            글.append(f"클럭 도착 {클럭_ps:,.0f} ps")
        if setup_ps is not None:
            글.append(f"셋업 {setup_ps:,.0f} ps")
        if 슬랙_ps is not None:
            글.append(f"슬랙 {슬랙_ps:+,.0f} ps")
        색 = 빨강 if (슬랙_ps is not None and 슬랙_ps < 0) else 초록
        m.append(_네모(12, y0, 폭 - 24, 22, "#fafbfc", 흐림, 1.0, 3))
        m.append(_글(20, y0 + 15, "  ·  ".join(글), 9.5, 먹))
        m.append(_네모(폭 - 92, y0 + 4, 76, 14,
                      "#fdecea" if 색 == 빨강 else "#e9f6ef", 색, 1.0, 3))
        m.append(_글(폭 - 54, y0 + 14.5,
                    "위반" if 색 == 빨강 else "통과", 9, 색, "middle", 굵게=True))

    최대증분 = max((s.get("증분_ps") or 0) for s in 단계들) or 1.0
    앞끝 = None
    for i, s in enumerate(단계들):
        줄 = i // 한줄
        자리 = i % 한줄
        x = 20 + 자리 * 칸
        y = y0 + 머리 + 24 + 줄 * 줄높이
        꼴 = 꼴찾기(s.get("셀", ""))
        증 = s.get("증분_ps") or 0.0
        # 지연이 큰 셀일수록 진하게 -- 그림이 곧 어디가 느린가다
        진하기 = min(1.0, 증 / 최대증분)
        채움 = f"rgb({255-int(60*진하기)},{255-int(95*진하기)},{255-int(105*진하기)})"
        m.append(기호(꼴, x, y, 기호폭, 기호높이, 채움,
                    선색=(빨강 if 진하기 > 0.72 else 먹)))
        # 입력 다리
        입, _출 = 핀이름.get(꼴, (["A"], "Y"))
        for k, pn in enumerate(입):
            fy = y + 기호높이 * (k + 1) / (len(입) + 1)
            if 꼴 in ("dff", "dffr", "lat"):
                fy = y + (8 if k == 0 else 기호높이 - 2)
            m.append(_선(x - 9, fy, x, fy, 흐림, 0.9))
            if len(입) > 1:
                m.append(_글(x - 11, fy + 3, pn, 6.8, 흐림, "end"))
        ox, oy = 출력점(꼴, x, y, 기호폭, 기호높이)
        m.append(_선(ox, oy, x + 칸 - 9 if 자리 < 한줄 - 1 and i < n - 1 else ox + 10,
                     oy, 흐림, 0.9))
        # 글: 셀 이름 · 증분 · 누적
        m.append(_글(x + 기호폭 / 2, y - 7, s.get("셀", "?"), 7.8, 먹, "middle", 굵게=True))
        m.append(_글(x + 기호폭 / 2, y + 기호높이 + 18,
                    f"+{증:,.1f} ps", 8.2,
                    빨강 if 진하기 > 0.72 else 흐림, "middle", 굵게=진하기 > 0.72))
        도 = s.get("도착_ps")
        if 도 is not None:
            m.append(_글(x + 기호폭 / 2, y + 기호높이 + 29,
                        f"Σ {도:,.0f}", 7.6, 파랑, "middle"))
        이음 = s.get("이음")
        if 이음:
            m.append(_글(x + 기호폭 / 2, y + 기호높이 + 39, str(이음)[:12], 6.8,
                        흐림, "middle"))
        # 줄이 바뀌면 되돌이 화살
        if 자리 == 한줄 - 1 and i < n - 1:
            m.append(_선(ox + 10, oy, 폭 - 12, oy, 흐림, 0.9))
            m.append(_선(폭 - 12, oy, 폭 - 12, oy + 42, 흐림, 0.9))
            m.append(_선(폭 - 12, oy + 42, 12, oy + 42, 흐림, 0.9))
            m.append(_화살(12, oy + 42, 12, oy + 줄높이 - 30, 흐림, 0.9))
        앞끝 = (ox, oy)
    if 앞끝:
        m.append(_글(앞끝[0] + 14, 앞끝[1] + 4, "→ 포착 FF/D", 7.6, 흐림))
    if 제목:
        m.append(_글(폭 / 2, 18, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(m), 제목)


# ------------------------------------------------------------------ 사인오프 판

def 사인오프판(항목들, 제목="사인오프 판정", 폭=560, 칸=30) -> str:
    """항목들 = [(이름, 판정 'OK'|'NG'|'-', 잰값, 기준, 무엇으로)].

    **회로도 옆에 이 판이 같이 있어야 한다.** 그림만 있으면 '그렸다' 이고,
    판정만 있으면 '무엇을 판정했는지' 가 없다.
    """
    if not 항목들:
        return 빈그림("사인오프 항목이 없다")
    y0 = 32 if 제목 else 10
    높이 = y0 + len(항목들) * 칸 + 14
    이름폭, 판폭, 값폭 = 150, 46, 132
    m = [_네모(10, y0 - 4, 폭 - 20, len(항목들) * 칸 + 8, "#ffffff", 흐림, 1.0, 3)]
    for i, it in enumerate(항목들):
        이름, 판, 값, 기준, 도구 = (list(it) + ["", "", ""])[:5]
        y = y0 + i * 칸
        if i:
            m.append(_선(12, y - 3, 폭 - 12, y - 3, "#eceff3", 0.8))
        색 = {"OK": 초록, "NG": 빨강}.get(판, 주황)
        m.append(_글(20, y + 16, str(이름), 9.5, 먹, 굵게=True))
        m.append(_네모(20 + 이름폭, y + 3, 판폭, 17,
                      {"OK": "#e9f6ef", "NG": "#fdecea"}.get(판, "#fdf5e6"),
                      색, 1.0, 3))
        m.append(_글(20 + 이름폭 + 판폭 / 2, y + 16,
                    {"OK": "통과", "NG": "위반"}.get(판, "안 함"), 9, 색,
                    "middle", 굵게=True))
        m.append(_글(20 + 이름폭 + 판폭 + 12, y + 16, str(값), 9, 먹))
        m.append(_글(20 + 이름폭 + 판폭 + 12 + 값폭, y + 16,
                    f"기준 {기준}" if 기준 else "", 8.4, 흐림))
        if 도구:
            m.append(_글(폭 - 20, y + 16, str(도구), 7.6, 흐림, "end"))
    if 제목:
        m.append(_글(폭 / 2, 18, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(m), 제목)


# ------------------------------------------------------------------ 넷리스트 -> 단계

def 경로뽑기(nl, 경로, 몇=14) -> list:
    """STA 의 임계경로(`[(키, 도착, 이음)]`)를 회로도 단계로 바꾼다.

    **경로가 길면 가운데를 버리지 않고 앞뒤를 남긴다** -- 발사 플롭과 포착 플롭이
    그림에 있어야 사람이 '한 주기 안에 이만큼을 지난다' 를 읽는다.
    """
    단계 = []
    앞 = None
    for (키, 도착, 이음) in 경로:
        인, 핀 = 키
        셀 = nl.인스턴스[인].종류 if 인 in nl.인스턴스 else str(인)
        단계.append({"셀": str(셀).lstrip("\\\\"), "인스턴스": str(인), "핀": 핀,
                   "도착_ps": 도착 * 1e3,
                   "증분_ps": 0.0 if 앞 is None else (도착 - 앞) * 1e3,
                   "이음": 이음 or ""})
        앞 = 도착
    if len(단계) <= 몇:
        return 단계
    앞쪽 = 단계[:몇 // 2]
    뒤쪽 = 단계[-(몇 - 몇 // 2 - 1):]
    가운데 = {"셀": f"… {len(단계)-len(앞쪽)-len(뒤쪽)}단 생략 …", "핀": "",
           "도착_ps": 뒤쪽[0]["도착_ps"],
           "증분_ps": sum(s["증분_ps"] for s in 단계[len(앞쪽):-len(뒤쪽)]),
           "이음": "생략분 합"}
    return 앞쪽 + [가운데] + 뒤쪽


# ------------------------------------------------------------------ UVM 구조도

def uvm구조(수 , 제목="UVM 검증 환경 구조", 폭=660) -> str:
    """강의 화면의 그 테스트벤치 구조도를, **우리 하니스의 실제 클래스와 수**로.

    `수` = {"시퀀스": 202, "드라이버": 1, "모니터": 1, "스코어보드": 1202,
           "커버리지": 92.3, "에이전트": ["cfg(느린 클럭)", "data(빠른 클럭)"], ...}

    **이름을 UVM 것으로 쓴 까닭.** 이 하니스는 SystemVerilog UVM 이 아니라
    verilator 위의 C++ 이다(상용 시뮬레이터가 없다). 그런데 **구조는 UVM 그대로**
    다 -- 시퀀스가 트랜잭션을 만들고, 드라이버가 핀을 흔들고, 모니터는 드라이버를
    모른 채 핀만 보고, 스코어보드가 기준모델과 맞대고, 커버리지가 따로 센다.
    그 대응을 보이려고 UVM 이름을 쓴다. **UVM 을 썼다고 적지 않는다.**
    """
    m = []
    높이 = 452
    바깥 = ("#8a8f98", "#f4f5f7")
    m.append(_네모(10, 34, 폭 - 20, 높이 - 66, 바깥[1], 바깥[0], 1.4, 4))
    m.append(_글(폭 / 2, 50, "Test bench  (tb_nsw_fir.cpp)", 9.5, 먹, "middle", 굵게=True))
    m.append(_네모(20, 58, 폭 - 40, 268, "#dbe7f3", "#6f8fae", 1.2, 3))
    m.append(_글(폭 / 2, 72, f"Test  ({수.get('시험','main()')})", 9, "#2c4a68", "middle", 굵게=True))
    # 시퀀스 두 개
    for i, (이름, x) in enumerate((("Sequence\\n(랜덤 %d)" % 수.get("랜덤", 0), 36),
                                  ("Sequence\\n(지시 %d)" % 수.get("지시", 0), 폭 - 160))):
        m.append(_네모(x, 78, 124, 30, "#eef3d8", "#8a9a5b", 1.1, 3))
        for k, 줄 in enumerate(이름.split("\\n")):
            m.append(_글(x + 62, 91 + k * 11, 줄, 8, 먹, "middle",
                        굵게=(k == 0)))
    # 검증 환경
    m.append(_네모(30, 116, 폭 - 60, 200, "#e6dcf0", "#8b74ad", 1.2, 3))
    m.append(_글(폭 / 2, 130, "Verification Environment", 9, "#4a3a63", "middle", 굵게=True))
    에 = 수.get("에이전트") or ["Agent 1", "Agent 2"]
    칸폭 = 186
    for i, 에이름 in enumerate(에[:2]):
        x = 42 if i == 0 else 폭 - 42 - 칸폭
        m.append(_네모(x, 138, 칸폭, 170, "#dce8f5", "#6f8fae", 1.1, 3))
        m.append(_글(x + 칸폭 / 2, 152, 에이름, 8.4, "#2c4a68", "middle", 굵게=True))
        m.append(_네모(x + 122, 140, 52, 15, "#ffffff", 흐림, 0.9, 2))
        m.append(_글(x + 148, 151, "CFG", 7.4, 흐림, "middle"))
        m.append(_네모(x + 10, 160, 78, 24, "#eef3d8", "#8a9a5b", 1.0, 2))
        m.append(_글(x + 49, 175, "Sequencer", 7.8, 먹, "middle"))
        m.append(_네모(x + 10, 192, 78, 40, "#f6c89a", "#c08040", 1.1, 2))
        m.append(_글(x + 49, 210, "Driver", 8.4, 먹, "middle", 굵게=True))
        m.append(_글(x + 49, 221, 수.get("드라이버글", ["push_coefs()", "run_txn()"])[i][:14],
                    6.8, 흐림, "middle"))
        m.append(_네모(x + 96, 192, 78, 40, "#fdf0e4", "#c08040", 1.1, 2))
        m.append(_글(x + 135, 210, "Monitor", 8.4, 먹, "middle", 굵게=True))
        m.append(_글(x + 135, 221, 수.get("모니터글", ["핀만 본다", "핀만 본다"])[i][:14],
                    6.8, 흐림, "middle"))
        for k, (nx, nm) in enumerate(((x + 14, "Virtual\\nInterface"), (x + 100, "Virtual\\nInterface"))):
            m.append(_네모(nx, 244, 70, 26, "#cfe0f2", "#5b7f9e", 0.9, 2))
            m.append(_글(nx + 35, 255, "Virtual", 6.6, "#2c4a68", "middle"))
            m.append(_글(nx + 35, 264, "Interface", 6.6, "#2c4a68", "middle"))
        m.append(_화살(x + 49, 184, x + 49, 192, 흐림, 1.0))
        m.append(_화살(x + 49, 232, x + 49, 244, 흐림, 1.0))
        m.append(_화살(x + 135, 244, x + 135, 232, 흐림, 1.0))
    # 스코어보드 · 커버리지
    m.append(_네모(폭 / 2 - 84, 160, 168, 34, "#cfe9d8", "#4e8b68", 1.2, 3))
    m.append(_글(폭 / 2, 174, "Scoreboard", 9, 먹, "middle", 굵게=True))
    m.append(_글(폭 / 2, 186, f"골든모델 대조 {수.get('대조',0):,}건 · 불일치 {수.get('불일치',0)}",
                7.2, 흐림, "middle"))
    m.append(_네모(폭 / 2 - 84, 202, 168, 34, "#cfe9d8", "#4e8b68", 1.2, 3))
    m.append(_글(폭 / 2, 216, "Functional Coverage", 9, 먹, "middle", 굵게=True))
    m.append(_글(폭 / 2, 228, f"{수.get('커버리지',0):.1f} % · 빈 {수.get('빈맞은',0)}/{수.get('빈전체',0)}",
                7.2, 흐림, "middle"))
    m.append(_네모(폭 / 2 - 26, 246, 52, 15, "#ffffff", 흐림, 0.9, 2))
    m.append(_글(폭 / 2, 257, "CFG", 7.4, 흐림, "middle"))
    # 모니터 -> 스코어보드/커버리지
    m.append(_화살(42 + 96 + 39, 200, 폭 / 2 - 84, 177, 흐림, 1.0))
    m.append(_화살(폭 - 42 - 칸폭 + 96 + 39, 200, 폭 / 2 + 84, 177, 흐림, 1.0))
    m.append(_화살(42 + 96 + 39, 214, 폭 / 2 - 84, 219, 흐림, 1.0))
    m.append(_화살(폭 - 42 - 칸폭 + 96 + 39, 214, 폭 / 2 + 84, 219, 흐림, 1.0))
    # 인터페이스 · DUT
    for i in range(2):
        x = 52 if i == 0 else 폭 - 52 - 176
        m.append(_네모(x, 332, 176, 22, "#c7ccd2", "#7c838b", 1.1, 2))
        m.append(_글(x + 88, 347, f"Interface ({['cfg_clk','clk'][i]})", 8.2, 먹, "middle"))
        m.append(_선(x + 88, 308, x + 88, 332, 흐림, 0.9, "3,2"))
        m.append(_선(x + 88, 354, x + 88, 364, 흐림, 0.9))
    m.append(_네모(70, 364, 폭 - 140, 30, "#f5c9c2", "#b05c4e", 1.3, 3))
    # **그림틀에 회로 이름을 박지 않는다.** 실측 2026-09-23: 여기에 `nsw_fir` 이
    # 박혀 있어서, 부르는 쪽이 제대로 된 이름을 넘겨도 `nsw_fir (mera_rec …)` 로
    # 찍힌다 -- 어떤 회로를 검증했는지가 그림에서 틀린다.
    m.append(_글(폭 / 2, 379, f"DUT — {수.get('dut', '') or '(이름 없음)'}", 9.2, 먹,
                "middle", 굵게=True))
    m.append(_글(폭 / 2, 390, 수.get("dut부제", ""), 7.2, 흐림, "middle"))
    if 제목:
        m.append(_글(폭 / 2, 18, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(m), 제목)


# ------------------------------------------------------------------ ATE / BIST / 스캔

def ate(수, 제목="ATE — 자동 시험 장비", 폭=620) -> str:
    """강의 화면의 ATE 그림.  Pattern Memory · Clock Generator · Pin Electronics.

    `수` = {"패턴수":512, "메모리_kB":..., "시간_ms":..., "핀":32, "체인":8, "압축":4}
    """
    m = []
    높이 = 300
    m.append(_네모(10, 30, 폭 - 20, 높이 - 46, "#ffffff", 먹, 1.4, 3))
    # 클럭 발생기
    m.append(f'<circle cx="86" cy="118" r="26" fill="#f7f8fa" stroke="{먹}" stroke-width="1.4"/>')
    m.append(f'<path d="M72,124 L72,112 L80,112 L80,124 L88,124 L88,112 L96,112" '
             f'fill="none" stroke="{먹}" stroke-width="1.6"/>')
    m.append(_글(86, 162, "Programmable", 8.2, 먹, "middle", 굵게=True))
    m.append(_글(86, 172, "Clock Generator", 8.2, 먹, "middle", 굵게=True))
    m.append(_글(86, 183, f"시프트 {수.get('시프트_MHz', 50)} MHz", 7.4, 흐림, "middle"))
    # 패턴 메모리
    m.append(_네모(210, 60, 108, 116, "#ffffff", 먹, 1.4, 2))
    m.append(_글(264, 108, "Pattern", 9.5, 먹, "middle", 굵게=True))
    m.append(_글(264, 120, "Memory", 9.5, 먹, "middle", 굵게=True))
    m.append(_글(264, 136, f"{수.get('메모리_kB', 0):,.0f} kB", 8.6, 빨강, "middle", 굵게=True))
    m.append(_글(264, 148, f"패턴 {수.get('패턴수', 0):,}개", 7.4, 흐림, "middle"))
    # 시험 프로그램 (STIL)
    m.append(_네모(360, 62, 86, 78, "#fbfbfc", 흐림, 1.1, 2))
    for k in range(9):
        m.append(_선(368, 76 + k * 7, 438, 76 + k * 7, "#d7dce2", 0.7))
    m.append(_글(403, 152, "Test Program", 8.2, 먹, "middle", 굵게=True))
    m.append(_글(403, 162, "(STIL / WGL)", 7.2, 흐림, "middle"))
    for k in range(4):
        m.append(_화살(360, 78 + k * 16, 318, 82 + k * 16, 흐림, 1.0))
    # 핀 전자
    for i in range(5):
        for x0, 쪽 in ((44, 0), (폭 - 158, 1)):
            m.append(_네모(x0 + i * 5, 196 + i * 3, 96, 56, "#ffffff", 먹, 1.0, 2))
    m.append(_글(92, 262, "Pin Electronics", 8.2, 먹, "middle", 굵게=True))
    m.append(_글(92, 272, f"Cards ({수.get('핀', 32)} ch)", 7.4, 흐림, "middle"))
    m.append(_글(폭 - 110, 262, "Pin Electronics", 8.2, 먹, "middle", 굵게=True))
    m.append(_글(폭 - 110, 272, "Cards", 7.4, 흐림, "middle"))
    # DUT
    m.append(f'<path d="M{폭/2-52:.0f},214 L{폭/2+52:.0f},204 L{폭/2+52:.0f},236 '
             f'L{폭/2-52:.0f},246 Z" fill="#6b7076" stroke="{먹}" stroke-width="1.3"/>')
    for i in range(9):
        m.append(_선(폭 / 2 - 48 + i * 11, 246 - i * 0.9, 폭 / 2 - 48 + i * 11,
                     254 - i * 0.9, 먹, 1.6))
    m.append(_글(폭 / 2, 268, "DUT Pins", 8.4, 먹, "middle", 굵게=True))
    m.append(_글(폭 / 2, 278, f"체인 {수.get('체인', 1)} × 압축 {수.get('압축', 1)}",
                7.4, 흐림, "middle"))
    # 데이터 흐름 (굵은 회색 화살)
    m.append(_네모(258, 176, 12, 22, "#c7ccd2", 흐림, 0.8, 0))
    m.append(_화살(264, 198, 264, 210, 흐림, 1.6))
    m.append(_선(140, 212, 폭 / 2 - 56, 212, 흐림, 1.4))
    m.append(_선(폭 / 2 + 56, 212, 폭 - 160, 212, 흐림, 1.4))
    m.append(_화살(86, 144, 86, 196, 흐림, 1.2))
    m.append(_글(폭 - 24, 290, f"시험 시간 {수.get('시간_ms', 0):,.3f} ms/다이", 8, 빨강,
                "end", 굵게=True))
    if 제목:
        m.append(_글(폭 / 2, 18, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(m), 제목)


def 하이브리드bist(수, 제목="Hybrid BIST — MBIST + LBIST", 폭=620) -> str:
    """강의 화면의 Hybrid BIST 블록도.  BIST Controller 와 그 아래 생성기들."""
    m = []
    높이 = 268
    m.append(_네모(10, 30, 폭 - 20, 높이 - 46, "#ffffff", 먹, 1.4, 3))
    # 제어기
    m.append(_네모(120, 74, 92, 92, "#ffffff", 먹, 1.4, 2))
    m.append(_글(166, 112, "BIST", 9.5, 먹, "middle", 굵게=True))
    m.append(_글(166, 124, "Controller", 9.5, 먹, "middle", 굵게=True))
    for k, (nm, y) in enumerate((("BIST_MODE", 82), ("START", 104), ("CLK", 126),
                                 ("DONE", 148))):
        if nm in ("DONE",):
            m.append(_화살(120, y, 68, y, 흐림, 1.1))
            m.append(_글(64, y + 3.5, nm, 7.6, 먹, "end", 기울임=True))
        else:
            m.append(_화살(68, y, 120, y, 흐림, 1.1))
            m.append(_글(64, y + 3.5, nm, 7.6, 먹, "end", 기울임=True))
    m.append(_글(64, 92, "(0:MBIST/1:LBIST)", 6.4, 흐림, "end"))
    # eNVM
    m.append(_네모(120, 176, 92, 34, "#f7f8fa", 먹, 1.1, 2))
    m.append(_글(166, 190, "eNVM", 8.4, 먹, "middle", 굵게=True))
    m.append(_글(166, 201, "기대 서명 " + str(수.get("서명", "")), 7, 흐림, "middle"))
    m.append(_선(166, 166, 166, 176, 흐림, 1.0))
    # MBIST 점선 상자
    m.append(f'<rect x="246" y="62" width="{폭-266}" height="116" fill="none" '
             f'stroke="{먹}" stroke-width="1.1" stroke-dasharray="4,3" rx="3"/>')
    m.append(_글(폭 - 26, 58, "MBIST", 8.4, 먹, "end", 굵게=True))
    for k, (nm, 부) in enumerate((("Memory Data Generator", f"{수.get('march','March C-')}"),
                                 ("Address Generator", f"깊이 {수.get('깊이',1024):,}"),
                                 ("Comparator", f"{수.get('연산','')}"),
                                 ("Test Data Generator", f"LFSR {수.get('lfsr',23)}비트"))):
        y = 68 + k * 30
        m.append(_네모(254, y, 폭 - 282, 24, "#ffffff", 먹, 1.1, 2))
        m.append(_글(262, y + 15, nm, 8.2, 먹, 굵게=True))
        m.append(_글(폭 - 34, y + 15, 부, 7.2, 흐림, "end"))
        m.append(_화살(212, 112, 254, y + 12, 흐림, 0.9))
        m.append(_화살(폭 - 28, y + 12, 폭 - 16, y + 12, 흐림, 0.9))
    m.append(f'<rect x="246" y="152" width="{폭-266}" height="62" fill="none" '
             f'stroke="{흐림}" stroke-width="1.0" stroke-dasharray="2,3" rx="3"/>')
    m.append(_글(252, 224, "LBIST", 8.4, 흐림, 굵게=True))
    m.append(_글(폭 - 20, 240,
                f"MBIST {수.get('mbist_ms',0):,.3f} ms · LBIST {수.get('lbist_ms',0):,.1f} ms",
                7.8, 빨강, "end", 굵게=True))
    if 제목:
        m.append(_글(폭 / 2, 18, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(m), 제목)


def 스캔체인(수, 제목="스캔 체인 · 압축", 폭=620) -> str:
    """머리 플롭 → 디컴프레서 → 체인들 → 컴프레서 → 꼬리. 강의 화면의 그 그림."""
    m = []
    높이 = 220
    m.append(_네모(10, 30, 폭 - 20, 높이 - 46, "#ffffff", 먹, 1.4, 3))
    체인 = min(int(수.get("체인", 4)), 6)
    for i, y in enumerate((70, 132)):
        m.append(_네모(26, y, 52, 26, "#ffffff", 먹, 1.2, 2))
        m.append(_글(52, y + 12, "Head", 7.6, 먹, "middle"))
        m.append(_글(52, y + 21, "Flop " + str(i + 1), 7.6, 먹, "middle"))
        m.append(_글(52, y + 38, f"tst_scanin{i+1}", 7, 흐림, "middle"))
        m.append(_화살(78, y + 13, 104, y + 13, 빨강, 1.2))
    # 디컴프레서
    m.append(f'<path d="M104,58 L140,74 L140,146 L104,162 Z" fill="#dce8f5" '
             f'stroke="{먹}" stroke-width="1.3"/>')
    m.append(_글(122, 178, "DECOMPRESSOR", 7.4, 먹, "middle", 굵게=True))
    m.append(_글(122, 188, f"{수.get('압축',1)}×", 7.4, 빨강, "middle", 굵게=True))
    # 체인들
    칸 = (폭 - 300) / max(체인, 1)
    for c in range(체인):
        y = 62 + c * (100 / max(체인 - 1, 1)) if 체인 > 1 else 100
        for k in range(4):
            x = 154 + k * (칸 * 0.9)
            m.append(_네모(x, y, min(칸 * 0.6, 34), 18, "#cfe0f2", 먹, 1.0, 2))
            if k < 3:
                m.append(_선(x + min(칸 * 0.6, 34), y + 9, x + 칸 * 0.9, y + 9, 빨강, 1.0))
        m.append(_선(140, 110, 154, y + 9, 빨강, 0.9))
        m.append(_선(154 + 3 * (칸 * 0.9) + min(칸 * 0.6, 34), y + 9, 폭 - 146, 110, 빨강, 0.9))
    # 컴프레서
    m.append(f'<path d="M{폭-146},74 L{폭-110},58 L{폭-110},162 L{폭-146},146 Z" '
             f'fill="#dce8f5" stroke="{먹}" stroke-width="1.3"/>')
    m.append(_글(폭 - 128, 178, "COMPRESSOR", 7.4, 먹, "middle", 굵게=True))
    m.append(_네모(폭 - 92, 96, 52, 26, "#ffffff", 먹, 1.2, 2))
    m.append(_글(폭 - 66, 108, "Tail", 7.6, 먹, "middle"))
    m.append(_글(폭 - 66, 117, "Flop", 7.6, 먹, "middle"))
    m.append(_화살(폭 - 110, 109, 폭 - 92, 109, 빨강, 1.2))
    m.append(_글(폭 / 2, 200,
                f"플롭 {수.get('플롭',0):,}개 · 체인 {수.get('체인',1)}개 · "
                f"시프트 길이 {수.get('시프트길이',0):,.0f} · 패턴 {수.get('패턴수',0):,}개",
                8, 먹, "middle"))
    if 제목:
        m.append(_글(폭 / 2, 18, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(m), 제목)


# ------------------------------------------------------------------ CGIC · 동기화기 · 데이터패스

def cgic(수=None, 제목="CGIC — 통합 클럭 게이팅 셀 (래치 + AND)", 폭=560) -> str:
    """강의 화면의 CGIC 회로도.  래치가 **왜** 있는지가 이 그림의 전부다."""
    수 = 수 or {}
    m = []
    높이 = 216
    m.append(_네모(30, 44, 300, 116, "#ffffff", 먹, 1.3, 3))
    m.append(_글(180, 60, "CGIC (nsw_icg)", 9, 흐림, "middle", 굵게=True))
    # 래치
    m.append(_네모(76, 78, 78, 56, "#f6c89a", "#c08040", 1.4, 3))
    m.append(_글(115, 104, "Latch", 10, 먹, "middle", 굵게=True))
    m.append(_글(115, 116, "(투명: CLK=0)", 6.8, 흐림, "middle"))
    m.append(_글(84, 92, "D", 7.2, 흐림))
    m.append(_글(84, 128, "G", 7.2, 흐림))
    m.append(f'<circle cx="70" cy="124" r="4" fill="#fff" stroke="{먹}" stroke-width="1.2"/>')
    # AND
    m.append(f'<path d="M198,84 L228,84 A24,24 0 0 1 228,132 L198,132 Z" '
             f'fill="#cfe9d8" stroke="{먹}" stroke-width="1.5"/>')
    m.append(_글(216, 112, "&", 12, 먹, "middle", 굵게=True))
    # 배선
    m.append(_화살(8, 90, 76, 90, 먹, 1.4))
    m.append(_글(4, 86, "EN", 8.6, 먹, "end", 굵게=True))
    m.append(_선(8, 138, 66, 138, 먹, 1.4))
    m.append(_선(66, 138, 66, 124, 먹, 1.4))
    m.append(_글(4, 142, "CLK", 8.6, 먹, "end", 굵게=True))
    m.append(_선(40, 138, 40, 152, 먹, 1.2))
    m.append(_선(40, 152, 186, 152, 먹, 1.2))
    m.append(_화살(186, 152, 186, 126, 먹, 1.2))
    m.append(_선(186, 126, 198, 126, 먹, 1.2))
    m.append(_선(154, 106, 186, 106, 먹, 1.4))
    m.append(_화살(186, 106, 198, 96, 먹, 1.4))
    m.append(_글(170, 100, "en_lat", 7, 흐림, "middle"))
    m.append(_화살(252, 108, 350, 108, 먹, 1.6))
    m.append(_글(354, 104, "Gated Clock", 8.6, 먹, 굵게=True))
    m.append(_글(354, 116, "(u_mac.clk)", 7, 흐림))
    # 레지스터 더미
    for i in range(3):
        m.append(_네모(440 + i * 5, 74 + i * 5, 74, 46, "#cfe0f2", "#5b7f9e", 1.2, 3))
    m.append(_글(482, 104, "Set of", 8, 먹, "middle"))
    m.append(_글(482, 115, "Registers", 8, 먹, "middle", 굵게=True))
    m.append(f'<path d="M448,116 L458,122 L448,128 Z" fill="{빨강}"/>')
    m.append(_글(폭 / 2, 180,
                "래치가 없으면 EN 이 <클럭 높은 구간>에 바뀔 때 짧은 펄스가 나간다 — 글리치.",
                8, 흐림, "middle"))
    if 수.get("잰것"):
        m.append(_글(폭 / 2, 194, 수["잰것"], 8.2, 빨강, "middle", 굵게=True))
    if 제목:
        m.append(_글(폭 / 2, 18, 제목, 11.5, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(m), 제목)


def 동기화기(단=2, 잰것="", 제목="CDC — 2단 동기화기와 한주기 펄스", 폭=580) -> str:
    """강의 화면의 `d - q1 - q2 - q3 - pulse` 그림."""
    m = []
    높이 = 196
    m.append(_네모(16, 44, 폭 - 92, 100, "#f4f5f7", 흐림, 1.2, 3))
    x0 = 56
    이름 = ["q1", "q2", "q3"][:max(단, 2) + 1]
    for i, nm in enumerate(이름):
        x = x0 + i * 92
        m.append(_네모(x, 72, 48, 46, "#ffffff", 먹, 1.4, 2))
        m.append(_글(x + 8, 88, "d", 7.4, 흐림))
        m.append(_글(x + 40, 88, "q", 7.4, 흐림, "end"))
        m.append(f'<path d="M{x},108 L{x+8},113 L{x},118" fill="none" stroke="{먹}" '
                 f'stroke-width="1.3"/>')
        m.append(_글(x + 24, 132, nm, 8.4, 먹, "middle", 굵게=True))
        if i:
            m.append(_화살(x - 44, 95, x, 95, 먹, 1.3))
    m.append(_화살(16, 95, x0, 95, 먹, 1.3))
    m.append(_글(12, 91, "d", 9, 먹, "end", 굵게=True))
    # sync2 점선
    m.append(f'<rect x="{x0-8}" y="62" width="{92+64}" height="66" fill="none" '
             f'stroke="{먹}" stroke-width="1.1" stroke-dasharray="4,3" rx="3"/>')
    m.append(_글(x0 + 70, 58, "sync2 (2단)", 8, 먹, "middle", 굵게=True))
    # XOR
    xx = x0 + 2 * 92 + 62
    m.append(f'<path d="M{xx},76 Q{xx+24},95 {xx},114 Q{xx+11},95 {xx},76 Z" '
             f'fill="#e6dcf0" stroke="{먹}" stroke-width="1.4"/>')
    m.append(f'<path d="M{xx-5},76 Q{xx+6},95 {xx-5},114" fill="none" stroke="{먹}" '
             f'stroke-width="1.2"/>')
    m.append(_선(x0 + 92 + 48, 95, xx - 6, 84, 먹, 1.2))
    m.append(_선(x0 + 2 * 92 + 48, 95, xx - 6, 106, 먹, 1.2))
    m.append(_화살(xx + 22, 95, 폭 - 66, 95, 먹, 1.4))
    m.append(_글(폭 - 62, 91, "pulse", 8.6, 먹, 굵게=True))
    m.append(_글(폭 - 62, 103, "(1 주기)", 7, 흐림))
    m.append(_글(폭 / 2, 162,
                "입력과 출력의 레벨이 달라지는 한 주기 동안만 XOR 이 1 이다.",
                8, 흐림, "middle"))
    if 잰것:
        m.append(_글(폭 / 2, 176, 잰것, 8.2, 빨강, "middle", 굵게=True))
    if 제목:
        m.append(_글(폭 / 2, 18, 제목, 11.5, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(m), 제목)


def 데이터패스(단이름들, 블록들, 제목="파이프라인 데이터패스", 폭=680, 높이=300) -> str:
    """강의 화면의 MIPS32 데이터패스 꼴 -- **단 사이에 파이프라인 레지스터 기둥**.

    단이름들 = ["IF_ID", "ID_EX", ...]  기둥에 붙는 이름
    블록들   = [(이름, 단번호, y, w, h, 색, 부제)]  단 번호는 기둥 사이 칸
    """
    m = []
    n = len(단이름들) + 1
    왼 = 24
    칸 = (폭 - 왼 - 30) / n
    기둥폭 = 11
    y0 = 34 if 제목 else 10
    위, 아래 = y0 + 18, 높이 - 46
    for i, nm in enumerate(단이름들):
        x = 왼 + (i + 1) * 칸 - 기둥폭 / 2
        m.append(_네모(x, 위, 기둥폭, 아래 - 위, "#f5c9c2", "#b05c4e", 1.2, 2))
        m.append(_글(x + 기둥폭 / 2, 아래 + 14, nm, 8, "#8a3f32", "middle", 굵게=True))
    for b in 블록들:
        nm, 단, by, bw, bh = b[0], b[1], b[2], b[3], b[4]
        색 = b[5] if len(b) > 5 else "#f5c9c2"
        부 = b[6] if len(b) > 6 else ""
        bx = 왼 + 단 * 칸 + (칸 - bw) / 2
        m.append(_네모(bx, by, bw, bh, 색, "#b05c4e", 1.3, 3))
        m.append(_글(bx + bw / 2, by + bh / 2 + (0 if not 부 else -4), nm, 8.6, 먹,
                    "middle", 굵게=True))
        if 부:
            m.append(_글(bx + bw / 2, by + bh / 2 + 9, 부, 6.8, 흐림, "middle"))
    if 제목:
        m.append(_글(폭 / 2, 18, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(m), 제목)
