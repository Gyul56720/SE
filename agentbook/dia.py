# -*- coding: utf-8 -*-
"""이 책의 그림 엔진 -- **SVG 를 직접 짓는다.**

사용자 지시(2026-09-21): "ip 교안에서 쓴 것처럼 다이어그램 중요해. 다이어그램 많이
이해하기 쉽게."

`house/sch.py` 는 EDA 전용(게이트 기호 · 스캔 체인 · CGIC)이라 여기서는 못 쓴다.
에이전트 이론서에 필요한 그림은 다른 부류다 -- 블록과 화살표, 층, 시간 축,
그래프, 나무, 곡선. 그것들을 여기 둔다.

**규칙 하나: 이 파일의 어떤 함수도 수를 지어내지 않는다.** 그리는 것은 인자로
받은 수뿐이다. 그래야 장에서 계산한 값이 그림과 어긋나지 않는다.
"""
import math

글꼴 = '"NanumGothic","Nanum Gothic","DejaVu Sans",sans-serif'
등폭 = '"NanumGothicCoding","DejaVu Sans Mono",monospace'

색 = {
    "진파랑": "#123f6d", "파랑": "#4a7fb5", "연파랑": "#dce8f4",
    "초록": "#3f8f63", "연초록": "#dcefe4", "빨강": "#a83f3f", "연빨강": "#f7e2e2",
    "보라": "#7a5ba8", "연보라": "#e9e2f4", "노랑": "#c9a227", "연노랑": "#fdf6dd",
    "회색": "#6b7680", "연회색": "#eef1f4", "검정": "#1a1a1a", "흰색": "#ffffff",
}


def _글(x, y, t, 크기=10, 색깔="#1a1a1a", 가운데=True, 굵게=False, 폰트=None):
    a = ' text-anchor="middle"' if 가운데 else ''
    b = ' font-weight="bold"' if 굵게 else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family={폰트 or 글꼴} '
            f'font-size="{크기}"{a}{b} fill="{색깔}">{_e(t)}</text>')


def _e(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _상자(x, y, w, h, 채움="#ffffff", 선="#123f6d", 굵기=1.4, r=3, 점선=False):
    d = ' stroke-dasharray="4 3"' if 점선 else ''
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{r}" fill="{채움}" stroke="{선}" stroke-width="{굵기}"{d}/>')


def _화살(x1, y1, x2, y2, 색깔="#123f6d", 굵기=1.4, 점선=False, 머리="end"):
    d = ' stroke-dasharray="5 3"' if 점선 else ''
    m = f' marker-end="url(#촉)"' if 머리 in ("end", "both") else ''
    m += f' marker-start="url(#촉뒤)"' if 머리 in ("start", "both") else ''
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{색깔}" stroke-width="{굵기}"{d}{m}/>')


def _굽은화살(x1, y1, x2, y2, 휨=0.3, 색깔="#123f6d", 굵기=1.4, 점선=False):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    cx, cy = mx - dy * 휨, my + dx * 휨
    d = ' stroke-dasharray="5 3"' if 점선 else ''
    return (f'<path d="M {x1:.1f} {y1:.1f} Q {cx:.1f} {cy:.1f} {x2:.1f} {y2:.1f}" '
            f'fill="none" stroke="{색깔}" stroke-width="{굵기}"{d} '
            f'marker-end="url(#촉)"/>')


def _틀(폭, 높이, 속):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {폭} {높이}" '
            f'width="100%" style="max-width:{폭}px">'
            '<defs>'
            '<marker id="촉" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            '<path d="M 0 0 L 10 5 L 0 10 z" fill="#123f6d"/></marker>'
            '<marker id="촉뒤" viewBox="0 0 10 10" refX="1" refY="5" '
            'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            '<path d="M 10 0 L 0 5 L 10 10 z" fill="#123f6d"/></marker>'
            '<marker id="촉빨강" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            '<path d="M 0 0 L 10 5 L 0 10 z" fill="#a83f3f"/></marker>'
            '</defs>'
            f'{속}</svg>')


# ---------------------------------------------------------------------------
# 1. 블록도 -- 상자와 화살표
# ---------------------------------------------------------------------------
def 블록도(마디들, 간선들=(), 폭=660, 칸높이=46, 줄틈=34, 제목=None):
    """마디 = (이름, 열, 행, 부제, 색이름). 간선 = (from이름, to이름, 라벨, 점선).

    열·행은 격자 좌표(0부터). 상자 크기는 자동.
    """
    열수 = max(m[1] for m in 마디들) + 1
    행수 = max(m[2] for m in 마디들) + 1
    여백 = 10
    머리 = 22 if 제목 else 0
    칸폭 = (폭 - 여백 * 2 - (열수 - 1) * 18) / 열수
    높이 = 머리 + 여백 * 2 + 행수 * 칸높이 + (행수 - 1) * 줄틈
    자리 = {}
    몸 = []
    if 제목:
        몸.append(_글(폭 / 2, 15, 제목, 11, 색["진파랑"], 굵게=True))
    for 이름, c, r, 부제, 색이름 in 마디들:
        x = 여백 + c * (칸폭 + 18)
        y = 머리 + 여백 + r * (칸높이 + 줄틈)
        자리[이름] = (x, y, 칸폭, 칸높이)
        채움 = 색.get("연" + 색이름, 색["연회색"])
        선 = 색.get(색이름, 색["진파랑"])
        몸.append(_상자(x, y, 칸폭, 칸높이, 채움, 선))
        몸.append(_글(x + 칸폭 / 2, y + (18 if 부제 else 칸높이 / 2 + 4),
                    이름, 10, 색["검정"], 굵게=True))
        if 부제:
            for i, 줄 in enumerate(str(부제).split("|")[:2]):
                몸.append(_글(x + 칸폭 / 2, y + 31 + i * 11, 줄, 8, 색["회색"]))
    for e in 간선들:
        a, b, 라벨, 점선 = (list(e) + ["", False])[:4]
        if a not in 자리 or b not in 자리:
            continue
        ax, ay, aw, ah = 자리[a]
        bx, by, bw, bh = 자리[b]
        if abs(ay - by) < 1:                       # 같은 줄 -- 옆으로
            if ax < bx:
                x1, y1, x2, y2 = ax + aw, ay + ah / 2, bx, by + bh / 2
            else:
                x1, y1, x2, y2 = ax, ay + ah / 2, bx + bw, by + bh / 2
            몸.append(_화살(x1, y1, x2, y2))
            if 라벨:
                몸.append(_글((x1 + x2) / 2, y1 - 4, 라벨, 7.6, 색["회색"]))
        else:                                       # 다른 줄 -- 아래로
            x1, y1 = ax + aw / 2, (ay + ah if ay < by else ay)
            x2, y2 = bx + bw / 2, (by if ay < by else by + bh)
            몸.append(_화살(x1, y1, x2, y2, 점선=점선))
            if 라벨:
                몸.append(_글((x1 + x2) / 2 + 26, (y1 + y2) / 2, 라벨, 7.6, 색["회색"]))
    return _틀(폭, 높이, "".join(몸))


# ---------------------------------------------------------------------------
# 2. 계층 -- 쌓인 층 (컨텍스트 예산 · 메모리 계층 · 점진 공개)
# ---------------------------------------------------------------------------
def 계층(층들, 폭=560, 층높이=40, 제목=None, 오른쪽라벨="비용"):
    """층 = (이름, 오른쪽글, 설명, 색이름). 위가 첫 원소."""
    여백 = 10
    머리 = 24 if 제목 else 0
    높이 = 머리 + 여백 * 2 + len(층들) * (층높이 + 6)
    몸 = []
    if 제목:
        몸.append(_글(폭 / 2, 16, 제목, 11, 색["진파랑"], 굵게=True))
    라벨폭 = 96
    for i, (이름, 오른, 설명, 색이름) in enumerate(층들):
        y = 머리 + 여백 + i * (층높이 + 6)
        w = 폭 - 여백 * 2 - 라벨폭
        몸.append(_상자(여백, y, w, 층높이, 색.get("연" + 색이름, 색["연회색"]),
                     색.get(색이름, 색["진파랑"])))
        몸.append(_글(여백 + 10, y + (17 if 설명 else 층높이 / 2 + 4), 이름, 10,
                    색["검정"], 가운데=False, 굵게=True))
        if 설명:
            몸.append(_글(여백 + 10, y + 30, 설명, 8, 색["회색"], 가운데=False))
        몸.append(_글(폭 - 여백 - 4, y + 층높이 / 2 + 4, 오른, 9,
                    색.get(색이름, 색["진파랑"]), 가운데=False, 폰트=등폭))
    return _틀(폭, 높이, "".join(몸))


# ---------------------------------------------------------------------------
# 3. 시퀀스도 -- 누가 누구를 언제 부르나 (MCP 악수 · 도구 호출)
# ---------------------------------------------------------------------------
def 시퀀스(참가자들, 메시지들, 폭=640, 줄틈=30, 제목=None):
    """참가자 = 이름 문자열. 메시지 = (from, to, 글, 점선, 색이름)."""
    여백 = 10
    머리 = (24 if 제목 else 0) + 30
    높이 = 머리 + len(메시지들) * 줄틈 + 30
    n = len(참가자들)
    간격 = (폭 - 여백 * 2) / n
    x자리 = {p: 여백 + 간격 * (i + 0.5) for i, p in enumerate(참가자들)}
    몸 = []
    if 제목:
        몸.append(_글(폭 / 2, 16, 제목, 11, 색["진파랑"], 굵게=True))
    for p in 참가자들:
        x = x자리[p]
        몸.append(_상자(x - 간격 / 2 + 6, 머리 - 28, 간격 - 12, 22,
                     색["연파랑"], 색["진파랑"]))
        몸.append(_글(x, 머리 - 13, p, 9, 색["진파랑"], 굵게=True))
        몸.append(f'<line x1="{x:.1f}" y1="{머리-4}" x2="{x:.1f}" y2="{높이-14}" '
                 f'stroke="{색["회색"]}" stroke-width="0.8" stroke-dasharray="3 3"/>')
    for i, m in enumerate(메시지들):
        a, b, 글, 점선, 색이름 = (list(m) + ["", False, "진파랑"])[:5]
        y = 머리 + 10 + i * 줄틈
        x1, x2 = x자리[a], x자리[b]
        c = 색.get(색이름, 색["진파랑"])
        if a == b:                                  # 자기 자신 -- 고리
            몸.append(f'<path d="M {x1:.1f} {y:.1f} q 26 0 26 12 q 0 12 -26 12" '
                     f'fill="none" stroke="{c}" stroke-width="1.3" '
                     f'marker-end="url(#촉)"/>')
            몸.append(_글(x1 + 34, y + 6, 글, 8, c, 가운데=False))
        else:
            몸.append(_화살(x1 + (9 if x2 > x1 else -9), y,
                         x2 - (9 if x2 > x1 else -9), y, c, 1.3, 점선))
            몸.append(_글((x1 + x2) / 2, y - 5, 글, 8, c))
    return _틀(폭, 높이, "".join(몸))


# ---------------------------------------------------------------------------
# 4. 상태기계
# ---------------------------------------------------------------------------
def 상태기계(상태들, 전이들, 폭=620, 제목=None, 반지름=32):
    """상태 = (이름, x비율, y비율, 색이름). 전이 = (from, to, 라벨, 휨)."""
    머리 = 24 if 제목 else 0
    높이 = 머리 + 200
    몸 = []
    if 제목:
        몸.append(_글(폭 / 2, 16, 제목, 11, 색["진파랑"], 굵게=True))
    자리 = {}
    for 이름, fx, fy, 색이름 in 상태들:
        x, y = 20 + fx * (폭 - 40), 머리 + 20 + fy * 160
        자리[이름] = (x, y)
        몸.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{반지름}" '
                 f'fill="{색.get("연"+색이름, 색["연회색"])}" '
                 f'stroke="{색.get(색이름, 색["진파랑"])}" stroke-width="1.5"/>')
        몸.append(_글(x, y + 4, 이름, 9, 색["검정"], 굵게=True))
    for t in 전이들:
        t = list(t)
        모자란 = [None, None, "", 0.22][len(t):]     # 빠진 **뒤칸만** 채운다
        a, b, 라벨, 휨 = (t + 모자란)[:4]
        (ax, ay), (bx, by) = 자리[a], 자리[b]
        if a == b:
            몸.append(f'<path d="M {ax-14:.1f} {ay-28:.1f} q -22 -30 22 -30 '
                     f'q 44 0 22 30" fill="none" stroke="{색["보라"]}" '
                     f'stroke-width="1.3" marker-end="url(#촉)"/>')
            몸.append(_글(ax, ay - 64, 라벨, 8, 색["보라"]))
            continue
        d = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / d, (by - ay) / d
        몸.append(_굽은화살(ax + ux * 반지름, ay + uy * 반지름,
                       bx - ux * 반지름, by - uy * 반지름, 휨, 색["보라"], 1.3))
        mx, my = (ax + bx) / 2 - (by - ay) * 휨 * 0.7, (ay + by) / 2 + (bx - ax) * 휨 * 0.7
        몸.append(_글(mx, my - 4, 라벨, 8, 색["보라"]))
    return _틀(폭, 높이, "".join(몸))


# ---------------------------------------------------------------------------
# 5. 방향 그래프 (LangGraph 의 StateGraph 같은 것)
# ---------------------------------------------------------------------------
def 그래프(마디들, 간선들, 폭=620, 높이=260, 제목=None):
    """마디 = (이름, x비율, y비율, 색이름, 부제). 간선 = (a, b, 라벨, 점선)."""
    머리 = 24 if 제목 else 0
    H = 머리 + 높이
    몸 = []
    if 제목:
        몸.append(_글(폭 / 2, 16, 제목, 11, 색["진파랑"], 굵게=True))
    자리, w, h = {}, 104, 34
    for 이름, fx, fy, 색이름, 부제 in 마디들:
        x, y = 14 + fx * (폭 - 28 - w), 머리 + 10 + fy * (높이 - 30 - h)
        자리[이름] = (x, y)
        몸.append(_상자(x, y, w, h, 색.get("연" + 색이름, 색["연회색"]),
                     색.get(색이름, 색["진파랑"]), r=14 if 색이름 == "회색" else 3))
        몸.append(_글(x + w / 2, y + (15 if 부제 else h / 2 + 4), 이름, 9,
                    색["검정"], 굵게=True))
        if 부제:
            몸.append(_글(x + w / 2, y + 27, 부제, 7.4, 색["회색"]))
    for e in 간선들:
        a, b, 라벨, 점선 = (list(e) + ["", False])[:4]
        (ax, ay), (bx, by) = 자리[a], 자리[b]
        if abs(ay - by) < 6:
            x1, y1 = (ax + w, ay + h / 2) if ax < bx else (ax, ay + h / 2)
            x2, y2 = (bx, by + h / 2) if ax < bx else (bx + w, by + h / 2)
        else:
            x1, y1 = ax + w / 2, (ay + h if ay < by else ay)
            x2, y2 = bx + w / 2, (by if ay < by else by + h)
        몸.append(_화살(x1, y1, x2, y2, 색["진파랑"], 1.3, 점선))
        if 라벨:
            몸.append(_글((x1 + x2) / 2, (y1 + y2) / 2 - 4, 라벨, 7.4, 색["회색"]))
    return _틀(폭, H, "".join(몸))


# ---------------------------------------------------------------------------
# 6. 타임라인 -- 슈퍼스텝 · 파이프라인 · 배치
# ---------------------------------------------------------------------------
def 타임라인(줄들, 칸수, 폭=640, 줄높이=26, 제목=None, 칸이름=None):
    """줄 = (라벨, [(시작칸, 길이, 글, 색이름), ...])."""
    여백, 라벨폭 = 10, 84
    머리 = (24 if 제목 else 0) + 16
    높이 = 머리 + len(줄들) * (줄높이 + 5) + 10
    칸폭 = (폭 - 여백 * 2 - 라벨폭) / 칸수
    몸 = []
    if 제목:
        몸.append(_글(폭 / 2, 16, 제목, 11, 색["진파랑"], 굵게=True))
    for k in range(칸수 + 1):
        x = 여백 + 라벨폭 + k * 칸폭
        몸.append(f'<line x1="{x:.1f}" y1="{머리-6}" x2="{x:.1f}" y2="{높이-8}" '
                 f'stroke="#dde3ea" stroke-width="0.7"/>')
        if k < 칸수:
            몸.append(_글(x + 칸폭 / 2, 머리 - 10,
                        (칸이름[k] if 칸이름 and k < len(칸이름) else str(k)),
                        7.4, 색["회색"]))
    for i, (라벨, 토막들) in enumerate(줄들):
        y = 머리 + i * (줄높이 + 5)
        몸.append(_글(여백 + 라벨폭 - 6, y + 줄높이 / 2 + 4, 라벨, 8.4,
                    색["진파랑"], 가운데=False, 굵게=True))
        for t in 토막들:
            s, L, 글, 색이름 = (list(t) + ["", "파랑"])[:4]
            x = 여백 + 라벨폭 + s * 칸폭
            몸.append(_상자(x + 1, y, L * 칸폭 - 2, 줄높이,
                         색.get("연" + 색이름, 색["연회색"]),
                         색.get(색이름, 색["파랑"]), 1.1, r=2))
            if 글:
                몸.append(_글(x + L * 칸폭 / 2, y + 줄높이 / 2 + 3.5, 글, 7.8,
                            색["검정"]))
    return _틀(폭, 높이, "".join(몸))


# ---------------------------------------------------------------------------
# 7. 나무 -- 탐색 (ToT · MCTS)
# ---------------------------------------------------------------------------
def 나무(층들, 폭=620, 층높이=58, 제목=None, 강조=()):
    """층 = [(이름, 부모index 또는 None, 색이름), ...]. 층 0 이 뿌리."""
    머리 = 24 if 제목 else 0
    높이 = 머리 + len(층들) * 층높이 + 16
    몸 = []
    if 제목:
        몸.append(_글(폭 / 2, 16, 제목, 11, 색["진파랑"], 굵게=True))
    자리 = []
    for d, 층 in enumerate(층들):
        n = len(층)
        칸 = (폭 - 24) / n
        이번 = []
        y = 머리 + 14 + d * 층높이
        for i, (이름, 부모, 색이름) in enumerate(층):
            x = 12 + 칸 * (i + 0.5)
            이번.append((x, y))
            r = 15
            채움 = 색.get("연" + 색이름, 색["연회색"])
            굵 = 2.4 if (d, i) in 강조 else 1.3
            몸.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{채움}" '
                     f'stroke="{색.get(색이름, 색["진파랑"])}" stroke-width="{굵}"/>')
            몸.append(_글(x, y + 3.5, 이름, 8, 색["검정"], 굵게=True))
            if 부모 is not None and d > 0:
                px, py = 자리[d - 1][부모]
                몸.append(f'<line x1="{px:.1f}" y1="{py+15:.1f}" x2="{x:.1f}" '
                         f'y2="{y-15:.1f}" stroke="{색["회색"]}" stroke-width="1"/>')
        자리.append(이번)
    return _틀(폭, 높이, "".join(몸))


# ---------------------------------------------------------------------------
# 8. 꺾은선 -- 곡선 하나 이상 (후회 · 재현율 · 비용)
# ---------------------------------------------------------------------------
def 꺾은선(계열들, x이름="", y이름="", 폭=560, 높이=220, 제목=None,
        로그x=False, 로그y=False):
    """계열 = (이름, [(x, y), ...], 색이름)."""
    왼, 아래, 위, 오른 = 46, 34, (26 if 제목 else 12), 12
    W, H = 폭 - 왼 - 오른, 높이 - 위 - 아래
    모든x = [p[0] for _, 점, _ in 계열들 for p in 점]
    모든y = [p[1] for _, 점, _ in 계열들 for p in 점]
    x0, x1 = min(모든x), max(모든x)
    y0, y1 = min(모든y), max(모든y)
    y0 = min(y0, 0) if y0 > 0 and not 로그y else y0
    if x1 == x0:
        x1 = x0 + 1
    if y1 == y0:
        y1 = y0 + 1

    def fx(v):
        if 로그x:
            return 왼 + W * (math.log(max(v, 1e-9)) - math.log(max(x0, 1e-9))) / \
                (math.log(max(x1, 1e-9)) - math.log(max(x0, 1e-9)))
        return 왼 + W * (v - x0) / (x1 - x0)

    def fy(v):
        if 로그y:
            return 위 + H - H * (math.log(max(v, 1e-9)) - math.log(max(y0, 1e-9))) / \
                (math.log(max(y1, 1e-9)) - math.log(max(y0, 1e-9)))
        return 위 + H - H * (v - y0) / (y1 - y0)

    몸 = []
    if 제목:
        몸.append(_글(폭 / 2, 15, 제목, 11, 색["진파랑"], 굵게=True))
    몸.append(f'<rect x="{왼}" y="{위}" width="{W}" height="{H}" fill="#fbfcfd" '
             f'stroke="#dde3ea" stroke-width="0.8"/>')
    for i in range(5):
        v = y0 + (y1 - y0) * i / 4
        y = fy(v)
        몸.append(f'<line x1="{왼}" y1="{y:.1f}" x2="{왼+W}" y2="{y:.1f}" '
                 f'stroke="#e8edf2" stroke-width="0.6"/>')
        몸.append(_글(왼 - 5, y + 3, f"{v:.3g}", 7.4, 색["회색"], 가운데=False))
    for i in range(5):
        v = x0 + (x1 - x0) * i / 4
        몸.append(_글(fx(v), 위 + H + 12, f"{v:.3g}", 7.4, 색["회색"]))
    for 이름, 점, 색이름 in 계열들:
        c = 색.get(색이름, 색["파랑"])
        d = " ".join(f'{"M" if i == 0 else "L"} {fx(px):.1f} {fy(py):.1f}'
                     for i, (px, py) in enumerate(점))
        몸.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="1.8"/>')
        for px, py in 점:
            몸.append(f'<circle cx="{fx(px):.1f}" cy="{fy(py):.1f}" r="2.2" '
                     f'fill="{c}"/>')
        lx, ly = fx(점[-1][0]), fy(점[-1][1])
        몸.append(_글(min(lx + 4, 폭 - 4), ly - 4, 이름, 7.8, c, 가운데=False))
    if x이름:
        몸.append(_글(왼 + W / 2, 높이 - 4, x이름, 8.4, 색["회색"]))
    if y이름:
        몸.append(f'<text x="11" y="{위+H/2:.1f}" font-family={글꼴} font-size="8.4" '
                 f'fill="{색["회색"]}" text-anchor="middle" '
                 f'transform="rotate(-90 11 {위+H/2:.1f})">{_e(y이름)}</text>')
    return _틀(폭, 높이, "".join(몸))


# ---------------------------------------------------------------------------
# 9. 막대 -- 견줌
# ---------------------------------------------------------------------------
def 막대(항목들, 폭=560, 높이=None, 제목=None, 단위="", 가로=True):
    """항목 = (이름, 값, 색이름, 오른쪽글)."""
    n = len(항목들)
    줄높이 = 24
    머리 = 24 if 제목 else 8
    높이 = 높이 or (머리 + n * (줄높이 + 5) + 12)
    라벨폭, 값폭 = 130, 74
    W = 폭 - 라벨폭 - 값폭 - 16
    최대 = max(abs(v) for _, v, _, _ in 항목들) or 1
    몸 = []
    if 제목:
        몸.append(_글(폭 / 2, 16, 제목, 11, 색["진파랑"], 굵게=True))
    for i, (이름, 값, 색이름, 오른) in enumerate(항목들):
        y = 머리 + i * (줄높이 + 5)
        몸.append(_글(라벨폭 - 6, y + 줄높이 / 2 + 4, 이름, 8.6, 색["검정"],
                    가운데=False))
        w = W * abs(값) / 최대
        몸.append(_상자(라벨폭, y, max(w, 1), 줄높이,
                     색.get("연" + 색이름, 색["연파랑"]),
                     색.get(색이름, 색["파랑"]), 1.1, r=2))
        몸.append(_글(라벨폭 + w + 6, y + 줄높이 / 2 + 4, 오른 or f"{값:g}{단위}",
                    8.2, 색.get(색이름, 색["파랑"]), 가운데=False, 폰트=등폭))
    return _틀(폭, 높이, "".join(몸))


# ---------------------------------------------------------------------------
# 10. 격자 -- 어텐션 마스크 · KV 블록 · 커버리지
# ---------------------------------------------------------------------------
def 격자(행수, 열수, 칠하기, 폭=420, 제목=None, 행이름=None, 열이름=None,
       칸글=None):
    """칠하기(r, c) -> 색이름 또는 None."""
    여백 = 10
    라벨 = 30 if 행이름 else 0
    머리 = (24 if 제목 else 0) + (14 if 열이름 else 0)
    칸 = min((폭 - 여백 * 2 - 라벨) / 열수, 26)
    높이 = 머리 + 여백 * 2 + 행수 * 칸
    몸 = []
    if 제목:
        몸.append(_글(폭 / 2, 16, 제목, 11, 색["진파랑"], 굵게=True))
    for c in range(열수):
        if 열이름:
            몸.append(_글(여백 + 라벨 + c * 칸 + 칸 / 2, 머리 - 4,
                        열이름[c] if c < len(열이름) else str(c), 7, 색["회색"]))
    for r in range(행수):
        y = 머리 + 여백 + r * 칸
        if 행이름:
            몸.append(_글(여백 + 라벨 - 4, y + 칸 / 2 + 3,
                        행이름[r] if r < len(행이름) else str(r), 7, 색["회색"],
                        가운데=False))
        for c in range(열수):
            x = 여백 + 라벨 + c * 칸
            nm = 칠하기(r, c)
            몸.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{칸-1:.1f}" '
                     f'height="{칸-1:.1f}" fill="'
                     f'{색.get("연"+nm, 색["흰색"]) if nm else "#ffffff"}" '
                     f'stroke="#d5dde6" stroke-width="0.6"/>')
            if 칸글:
                t = 칸글(r, c)
                if t:
                    몸.append(_글(x + 칸 / 2, y + 칸 / 2 + 3, t, 6.6, 색["검정"]))
    return _틀(폭, 높이, "".join(몸))


# ---------------------------------------------------------------------------
# 11. 파이프 -- 단계 사슬 (화살표 모양)
# ---------------------------------------------------------------------------
def 파이프(단계들, 폭=640, 높이=58, 제목=None, 아래글=None):
    """단계 = (이름, 부제, 색이름)."""
    머리 = 24 if 제목 else 4
    아래 = 16 if 아래글 else 0
    H = 머리 + 높이 + 아래
    n = len(단계들)
    여백, 겹 = 8, 12
    w = (폭 - 여백 * 2 + 겹 * (n - 1)) / n
    몸 = []
    if 제목:
        몸.append(_글(폭 / 2, 16, 제목, 11, 색["진파랑"], 굵게=True))
    for i, (이름, 부제, 색이름) in enumerate(단계들):
        x = 여백 + i * (w - 겹)
        y = 머리
        c = 색.get(색이름, 색["파랑"])
        f = 색.get("연" + 색이름, 색["연파랑"])
        d = (f"M {x:.1f} {y} L {x+w-겹:.1f} {y} L {x+w:.1f} {y+높이/2:.1f} "
             f"L {x+w-겹:.1f} {y+높이} L {x:.1f} {y+높이} "
             f"L {x+겹:.1f} {y+높이/2:.1f} Z")
        몸.append(f'<path d="{d}" fill="{f}" stroke="{c}" stroke-width="1.3"/>')
        몸.append(_글(x + w / 2, y + (22 if 부제 else 높이 / 2 + 4), 이름, 9,
                    색["검정"], 굵게=True))
        if 부제:
            몸.append(_글(x + w / 2, y + 35, 부제, 7.2, 색["회색"]))
    if 아래글:
        몸.append(_글(폭 / 2, H - 4, 아래글, 7.8, 색["회색"]))
    return _틀(폭, H, "".join(몸))


# ---------------------------------------------------------------------------
# 12. 견줌판 -- 왼쪽/오른쪽 두 판을 나란히
# ---------------------------------------------------------------------------
def 견줌(왼제목, 왼줄들, 오른제목, 오른줄들, 폭=640, 제목=None, 왼색="빨강",
       오른색="초록"):
    머리 = 24 if 제목 else 0
    n = max(len(왼줄들), len(오른줄들))
    높이 = 머리 + 34 + n * 19 + 12
    w = (폭 - 26) / 2
    몸 = []
    if 제목:
        몸.append(_글(폭 / 2, 16, 제목, 11, 색["진파랑"], 굵게=True))
    for j, (t, 줄들, 색이름, x) in enumerate(
            ((왼제목, 왼줄들, 왼색, 8), (오른제목, 오른줄들, 오른색, 18 + w))):
        c = 색.get(색이름, 색["회색"])
        몸.append(_상자(x, 머리 + 6, w, 높이 - 머리 - 14,
                     색.get("연" + 색이름, 색["연회색"]), c, 1.2))
        몸.append(f'<rect x="{x:.1f}" y="{머리+6:.1f}" width="{w:.1f}" height="22" '
                 f'rx="3" fill="{c}"/>')
        몸.append(_글(x + w / 2, 머리 + 21, t, 9.4, 색["흰색"], 굵게=True))
        for i, 줄 in enumerate(줄들):
            몸.append(_글(x + 9, 머리 + 44 + i * 19, "· " + 줄, 8.2, 색["검정"],
                        가운데=False))
    return _틀(폭, 높이, "".join(몸))
