# -*- coding: utf-8 -*-
"""house/viz -- 보고서에 들어갈 그림을 손으로 그린 SVG 로 낸다.

**왜 손으로 그리나.** 사용자(2026-09-21): "언어로만 '~했다' 로 보고했는데 그게 아니라,
시뮬레이션 결과나 tool 을 사용한 결과를 반드시 그림 혹은 그래프로 시각화해서 제시해야
한다." 그러니 그림은 장식이 아니라 **보고의 본문**이다. 본문을 외부 백엔드(matplotlib
폰트 캐시 · Agg 버전)에 맡기면 어느 VM 에서 글자가 네모로 깨졌을 때 보고 자체가 깨진다.
SVG 를 직접 적으면 weasyprint 가 그대로 벡터로 PDF 에 넣고, 글꼴은 아래 한 곳에서만
정한다.

**그리는 것은 잰 값뿐이다.** 이 파일의 어느 함수도 값을 지어내지 않는다 -- 축의 범위와
눈금만 만든다. 값이 비면 빈 그림을 내고 "잰 것이 없다" 고 적는다. 거짓 그래프는
거짓 문장보다 나쁘다(사람이 더 믿는다).
"""
from __future__ import annotations

import html
import math

글꼴 = "'NanumGothic','Noto Sans CJK KR',sans-serif"
등폭 = "'NanumGothicCoding','DejaVu Sans Mono',monospace"

# 색 -- 한 벌로 고정한다. 보고서 다섯 개가 같은 회사에서 나온 것으로 보여야 한다.
먹 = "#1b1b1f"
흐림 = "#8a8f98"
선색 = "#c9ced6"
바탕 = "#ffffff"
연바탕 = "#f5f7fa"
빨강 = "#c0392b"
파랑 = "#1f6feb"
초록 = "#137333"
주황 = "#e08a2e"
보라 = "#7b4bbf"
청록 = "#0f9b8e"
계열 = [파랑, 빨강, 초록, 주황, 보라, 청록, "#8a8f98"]


def _e(s) -> str:
    return html.escape(str(s), quote=True)


def _수(x, 자리=4) -> str:
    """축 눈금용 짧은 수.  1000 단위는 k/M 로 줄인다."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if v != v or v in (float("inf"), float("-inf")):
        return "-"
    a = abs(v)
    if a >= 1e9:
        return f"{v/1e9:.2f}G"
    if a >= 1e6:
        return f"{v/1e6:.2f}M"
    if a >= 1e4:
        return f"{v/1e3:.1f}k"
    if a == 0:
        return "0"
    if a < 1e-3:
        return f"{v:.1e}"
    s = f"{v:.{자리}g}"
    return s


def svg(폭, 높이, 몸, 제목="") -> str:
    """바깥 틀.  max-width 로 PDF 와 브라우저 둘 다에서 안 넘친다."""
    t = f"<title>{_e(제목)}</title>" if 제목 else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {폭} {높이}" '
            f'width="100%" style="max-width:{폭}px;height:auto" '
            f'font-family={_e(글꼴)!s} font-size="11">{t}{몸}</svg>')


def _글(x, y, s, 크기=11, 색=None, 맞춤="start", 굵게=False, 기울임=False, 글꼴이름=None):
    색 = 색 or 먹
    w = ' font-weight="bold"' if 굵게 else ""
    i = ' font-style="italic"' if 기울임 else ""
    f = f' font-family="{글꼴이름}"' if 글꼴이름 else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{색}" font-size="{크기}" '
            f'text-anchor="{맞춤}"{w}{i}{f}>{_e(s)}</text>')


# ---------------------------------------------------------------- 상자 안에 글 앉히기
# **실측 2026-09-22 (제안서 `mera_rec`).** 그림 두 장의 글자가 상자 밖으로 넘쳐
# 서로 겹쳤다. SVG `<text>` 는 **저 혼자 안 줄어들고 안 접힌다** -- 넘치면 그냥 넘친다.
# 흐름도의 칸은 70 px 인데 "스펙 판독(코드, 모델 없이)" 는 10.5 px 에서 150 px 가 넘는다.
#
# 같은 그림에 markup 찌꺼기도 같이 찍혀 있었다. 원본이 `"스펙 판독\\n(코드…)"` 라
# 파이썬 글자에 **역슬래시와 n 이 그대로** 들어 있었고, SVG 는 그것을 줄바꿈으로
# 안 읽으니 `판독\n(코드` 로 보였다. `**이 제안서**` 의 별표도 마찬가지다 --
# SVG 에 markdown 은 없다. **찍히는 자리에서 턴다.**
_넓은글자 = ((0x1100, 0x115F), (0x2E80, 0xA4CF), (0xAC00, 0xD7A3), (0xF900, 0xFAFF),
         (0xFE30, 0xFE6F), (0xFF00, 0xFF60), (0xFFE0, 0xFFE6))


def 글자너비(s: str, 크기: float) -> float:
    """대충의 렌더 너비(px). **정확한 값이 아니라 어림이다** -- 글꼴 메트릭이 없다.

    한글·한자·전각은 한 칸, 나머지는 반 칸 조금 넘게 잡는다. 어림이지만 "넘치는가"
    를 가리기에는 넉넉하다(넘침은 대개 두 배씩 난다).
    """
    w = 0.0
    for ch in s or "":
        o = ord(ch)
        w += 1.0 if any(a <= o <= b for a, b in _넓은글자) else 0.55
    return w * 크기


def 군말털기(s: str) -> str:
    """찍기 전에 markup 찌꺼기를 턴다. `\n` 두 글자와 `**` 를 없앤다."""
    t = (s or "").replace("\\n", " ").replace("\n", " ")
    while "**" in t:
        t = t.replace("**", "")
    return " ".join(t.split())


def 앉히기(s: str, 크기: float, 최대너비: float, 줄수: int = 1) -> "tuple[list, float]":
    """(줄들, 쓸 글자크기). 상자에 들어가게 접고 줄이고, 그래도 넘치면 자른다.

    순서가 있다. **접기 -> 줄이기 -> 자르기.** 자르는 것이 마지막인 까닭은 자르면
    뜻이 사라지기 때문이다. 줄이기는 6.5 px 에서 멈춘다 -- 그 아래는 읽을 수 없고,
    읽을 수 없는 글자는 안 찍은 것과 같다.
    """
    s = 군말털기(s)
    if not s:
        return [], 크기
    낱말 = s.split(" ")
    for 시도 in (크기, 크기 * 0.9, 크기 * 0.8, max(6.5, 크기 * 0.7)):
        줄, 이번 = [], ""
        넘 = False
        for w in 낱말:
            후보 = f"{이번} {w}".strip()
            if 글자너비(후보, 시도) <= 최대너비 or not 이번:
                이번 = 후보
            else:
                줄.append(이번)
                이번 = w
            if len(줄) >= 줄수:
                넘 = True
                break
        if 이번 and not 넘:
            줄.append(이번)
        if not 넘 and len(줄) <= 줄수 and all(글자너비(x, 시도) <= 최대너비 for x in 줄):
            return 줄, 시도
    # 여기까지 왔으면 접어도 줄여도 안 들어간다 -- 자른다
    크 = max(6.5, 크기 * 0.7)
    줄 = []
    남 = s
    for _ in range(줄수):
        if not 남:
            break
        take = 남
        while take and 글자너비(take, 크) > 최대너비:
            take = take[:-1]
        줄.append(take)
        남 = 남[len(take):].strip()
    if 남 and 줄:
        꼬 = 줄[-1]
        while 꼬 and 글자너비(꼬 + "…", 크) > 최대너비:
            꼬 = 꼬[:-1]
        줄[-1] = 꼬 + "…"
    return 줄, 크


def _칸글(cx, y, s, 크기, 색, 최대너비, 줄수=1, 굵게=False, 줄간격=None):
    """상자 가운데에 앉힌 글. 여러 줄이면 `y` 를 첫 줄의 기준선으로 쓴다."""
    줄, 크 = 앉히기(s, 크기, 최대너비, 줄수)
    간 = 줄간격 or (크 + 1.5)
    return "".join(_글(cx, y + i * 간, t, 크, 색, "middle", 굵게=굵게)
                   for i, t in enumerate(줄))


def _선(x1, y1, x2, y2, 색=None, 굵기=1.0, 점선=None):
    색 = 색 or 선색
    d = f' stroke-dasharray="{점선}"' if 점선 else ""
    return (f'<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}" fill="none" '
            f'stroke="{색}" stroke-width="{굵기}"{d}/>')


def _네모(x, y, w, h, 채움="none", 선=None, 굵기=1.2, r=3):
    선 = 선 or 먹
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0):.1f}" height="{max(h,0):.1f}" '
            f'fill="{채움}" stroke="{선}" stroke-width="{굵기}" rx="{r}"/>')


def _화살(x1, y1, x2, y2, 색=None, 굵기=1.4):
    """끝에 삼각형이 붙은 선.  marker 를 안 쓴다 -- 일부 PDF 엔진이 marker 를 흘린다."""
    색 = 색 or 먹
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    bx, by = x2 - ux * 7, y2 - uy * 7
    px, py = -uy * 3.6, ux * 3.6
    return (_선(x1, y1, bx, by, 색, 굵기) +
            f'<path d="M{x2:.1f},{y2:.1f} L{bx+px:.1f},{by+py:.1f} '
            f'L{bx-px:.1f},{by-py:.1f} Z" fill="{색}"/>')


def _축(x0, y0, 폭, 높이, x범위, y범위, x눈금, y눈금, x이름="", y이름="", 로그y=False):
    """왼쪽·아래 축과 눈금.  좌표 변환 함수 두 개를 같이 돌려준다."""
    xa, xb = x범위
    ya, yb = y범위
    if xb == xa:
        xb = xa + 1
    if yb == ya:
        yb = ya + 1

    def X(v):
        return x0 + (v - xa) / (xb - xa) * 폭

    def Y(v):
        if 로그y:
            la, lb = math.log10(max(ya, 1e-300)), math.log10(max(yb, 1e-300))
            lv = math.log10(max(v, 1e-300))
            return y0 + 높이 - (lv - la) / (lb - la or 1) * 높이
        return y0 + 높이 - (v - ya) / (yb - ya) * 높이

    몸 = [_선(x0, y0, x0, y0 + 높이, 흐림, 1.2), _선(x0, y0 + 높이, x0 + 폭, y0 + 높이, 흐림, 1.2)]
    for v in y눈금:
        y = Y(v)
        몸.append(_선(x0, y, x0 + 폭, y, "#eceff3", 1.0))
        몸.append(_선(x0 - 4, y, x0, y, 흐림, 1.0))
        몸.append(_글(x0 - 7, y + 3, _수(v), 9, 흐림, "end"))
    for v in x눈금:
        x = X(v)
        몸.append(_선(x, y0 + 높이, x, y0 + 높이 + 4, 흐림, 1.0))
        몸.append(_글(x, y0 + 높이 + 15, _수(v), 9, 흐림, "middle"))
    if x이름:
        몸.append(_글(x0 + 폭 / 2, y0 + 높이 + 30, x이름, 10, 먹, "middle"))
    if y이름:
        cy = y0 + 높이 / 2
        몸.append(f'<text x="14" y="{cy:.1f}" font-size="10" fill="{먹}" '
                  f'transform="rotate(-90 14 {cy:.1f})" text-anchor="middle">{_e(y이름)}</text>')
    return "".join(몸), X, Y


def _눈금만들기(a, b, n=5, 로그=False):
    # **무한/NaN 을 막는다.** MTBF 처럼 지수로 커지는 양은 float 범위를 넘는다
    # (실측: 동기화기 4단에서 inf -> OverflowError). 그림이 죽는 대신 축을 자른다.
    상한 = 1e300
    if a != a or abs(a) == float("inf"):
        a = 0.0 if a != a or a < 0 else 상한
    if b != b or abs(b) == float("inf"):
        b = 상한
    a, b = min(a, 상한), min(b, 상한)
    if 로그:
        la, lb = math.log10(max(a, 1e-300)), math.log10(max(b, 1e-300))
        step = max(1, int(math.ceil((lb - la) / max(n, 1))))
        out, k = [], int(math.floor(la))
        while k <= math.ceil(lb):
            out.append(10.0 ** k)
            k += step
        return out
    if b <= a:
        b = a + 1
    raw = (b - a) / max(n, 1)
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            step = m * mag
            break
    else:
        step = 10 * mag
    first = math.ceil(a / step) * step
    out, v = [], first
    while v <= b + step * 1e-9:
        out.append(round(v, 12))
        v += step
    return out or [a, b]


def 빈그림(말="잰 것이 없다", 폭=520, 높이=120) -> str:
    몸 = (_네모(1, 1, 폭 - 2, 높이 - 2, 연바탕, 선색, 1.0) +
         _글(폭 / 2, 높이 / 2 + 4, 말, 12, 흐림, "middle"))
    return svg(폭, 높이, 몸)


# ---------------------------------------------------------------- 데이터 그림

def 막대(이름들, 값들, 제목="", y이름="", 색들=None, 폭=560, 높이=240, 값글=True,
        기준선=None, 기준글="") -> str:
    """세로 막대.  `기준선` 을 주면 빨간 점선과 이름을 같이 그린다(예산·규격)."""
    if not 이름들 or not 값들:
        return 빈그림()
    값들 = [float(v) for v in 값들]
    x0, y0 = 62, 30 if 제목 else 16
    W, H = 폭 - x0 - 24, 높이 - y0 - 46
    상 = max(값들 + ([기준선] if 기준선 is not None else []))
    하 = min(값들 + ([기준선] if 기준선 is not None else []) + [0.0])
    pad = (상 - 하) * 0.12 or (abs(상) * 0.12 or 1)
    y범위 = (하 - (pad if 하 < 0 else 0), 상 + pad)
    눈금 = _눈금만들기(*y범위, 5)
    축, X, Y = _축(x0, y0, W, H, (0, len(값들)), y범위, [], 눈금, "", y이름)
    몸 = [축]
    칸 = W / len(값들)
    for i, (nm, v) in enumerate(zip(이름들, 값들)):
        c = (색들[i] if 색들 and i < len(색들) else 계열[i % len(계열)])
        bx = x0 + i * 칸 + 칸 * 0.18
        bw = 칸 * 0.64
        y1, y0b = Y(v), Y(0)
        몸.append(_네모(bx, min(y1, y0b), bw, abs(y0b - y1), c, c, 0.6, 2))
        몸.append(_글(bx + bw / 2, y0 + H + 15, str(nm), 9, 먹, "middle"))
        if 값글:
            몸.append(_글(bx + bw / 2, min(y1, y0b) - 4, _수(v), 9, 먹, "middle", 굵게=True))
    if 기준선 is not None:
        y = Y(기준선)
        몸.append(_선(x0, y, x0 + W, y, 빨강, 1.6, "5,3"))
        몸.append(_글(x0 + W - 2, y - 5, 기준글 or f"기준 {_수(기준선)}", 9, 빨강, "end", 굵게=True))
    if 제목:
        몸.append(_글(폭 / 2, 17, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(몸), 제목)


def 선(x들, 계열들, 제목="", x이름="", y이름="", 폭=560, 높이=250, 로그y=False,
      점표시=True, 기준선=None, 기준글="") -> str:
    """계열들 = [(이름, [y...]), ...]"""
    계열들 = [(n, [float(v) for v in ys]) for n, ys in 계열들 if ys]
    if not x들 or not 계열들:
        return 빈그림()
    x들 = [float(v) for v in x들]
    x0, y0 = 62, 30 if 제목 else 16
    W, H = 폭 - x0 - 24, 높이 - y0 - 48
    모든y = [v for _, ys in 계열들 for v in ys] + ([기준선] if 기준선 is not None else [])
    if 로그y:
        모든y = [v for v in 모든y if v > 0] or [1.0]
        y범위 = (min(모든y) / 3, max(모든y) * 3)
    else:
        lo, hi = min(모든y), max(모든y)
        pad = (hi - lo) * 0.12 or (abs(hi) * 0.12 or 1)
        y범위 = (lo - pad, hi + pad)
    y눈금 = _눈금만들기(*y범위, 5, 로그y)
    x눈금 = _눈금만들기(min(x들), max(x들), 5)
    축, X, Y = _축(x0, y0, W, H, (min(x들), max(x들)), y범위, x눈금, y눈금, x이름, y이름, 로그y)
    몸 = [축]
    for i, (nm, ys) in enumerate(계열들):
        c = 계열[i % len(계열)]
        pts = [(X(x), Y(y)) for x, y in zip(x들, ys)]
        d = " ".join(("M" if k == 0 else "L") + f"{px:.1f},{py:.1f}" for k, (px, py) in enumerate(pts))
        몸.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="1.9"/>')
        if 점표시:
            몸 += [f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.3" fill="{c}"/>' for px, py in pts]
        몸.append(_글(폭 - 26, y0 + 12 + i * 13, nm, 9.5, c, "end", 굵게=True))
    if 기준선 is not None:
        y = Y(기준선)
        몸.append(_선(x0, y, x0 + W, y, 빨강, 1.6, "5,3"))
        몸.append(_글(x0 + 3, y - 5, 기준글 or f"기준 {_수(기준선)}", 9, 빨강, "start", 굵게=True))
    if 제목:
        몸.append(_글(폭 / 2, 17, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(몸), 제목)


def 산점(xs, ys, 제목="", x이름="", y이름="", 폭=520, 높이=250, 색=None, 라벨=None) -> str:
    if not xs or not ys:
        return 빈그림()
    xs, ys = [float(v) for v in xs], [float(v) for v in ys]
    x0, y0 = 62, 30 if 제목 else 16
    W, H = 폭 - x0 - 24, 높이 - y0 - 48
    xr = (min(xs), max(xs))
    yr = (min(ys), max(ys))
    xp = (xr[1] - xr[0]) * 0.08 or 1
    yp = (yr[1] - yr[0]) * 0.12 or 1
    축, X, Y = _축(x0, y0, W, H, (xr[0] - xp, xr[1] + xp), (yr[0] - yp, yr[1] + yp),
                  _눈금만들기(xr[0] - xp, xr[1] + xp, 5), _눈금만들기(yr[0] - yp, yr[1] + yp, 5),
                  x이름, y이름)
    몸 = [축]
    c = 색 or 파랑
    for i, (x, y) in enumerate(zip(xs, ys)):
        몸.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="3.0" fill="{c}" fill-opacity="0.78"/>')
        if 라벨 and i < len(라벨):
            몸.append(_글(X(x) + 5, Y(y) - 4, 라벨[i], 8.5, 흐림))
    if 제목:
        몸.append(_글(폭 / 2, 17, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(몸), 제목)


def 히스토그램(값들, 칸수=24, 제목="", x이름="", y이름="건수", 폭=560, 높이=230) -> str:
    값들 = [float(v) for v in 값들 if v == v]
    if not 값들:
        return 빈그림()
    lo, hi = min(값들), max(값들)
    if hi == lo:
        hi = lo + 1
    w = (hi - lo) / 칸수
    통 = [0] * 칸수
    for v in 값들:
        k = min(칸수 - 1, int((v - lo) / w))
        통[k] += 1
    x0, y0 = 62, 30 if 제목 else 16
    W, H = 폭 - x0 - 24, 높이 - y0 - 46
    y눈금 = _눈금만들기(0, max(통), 4)
    축, X, Y = _축(x0, y0, W, H, (lo, hi), (0, max(통) * 1.1), _눈금만들기(lo, hi, 5), y눈금, x이름, y이름)
    몸 = [축]
    for k, n in enumerate(통):
        bx = X(lo + k * w)
        bw = max(W / 칸수 - 1, 1)
        몸.append(_네모(bx, Y(n), bw, Y(0) - Y(n), 파랑, 파랑, 0.4, 1))
    if 제목:
        몸.append(_글(폭 / 2, 17, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(몸), 제목)


def 히트맵(격자, 제목="", x이름="", y이름="", 폭=520, 높이=None, 색낮음="#eef4fb",
         색높음="#c0392b", 값글=False, x라벨=None, y라벨=None) -> str:
    """격자 = [[v,...], ...]  -- 혼잡도·커버리지 크로스·IR 강하에 쓴다."""
    if not 격자 or not 격자[0]:
        return 빈그림()
    R, C = len(격자), len(격자[0])
    x0, y0 = 46, 30 if 제목 else 14
    칸 = max(6, min(26, (폭 - x0 - 60) // C))
    높이 = 높이 or (y0 + R * 칸 + 44)
    lo = min(min(r) for r in 격자)
    hi = max(max(r) for r in 격자)
    rng = (hi - lo) or 1

    def 색(v):
        t = (v - lo) / rng
        a = tuple(int(색낮음[i:i + 2], 16) for i in (1, 3, 5))
        b = tuple(int(색높음[i:i + 2], 16) for i in (1, 3, 5))
        return "#" + "".join(f"{int(a[i]+(b[i]-a[i])*t):02x}" for i in range(3))

    몸 = []
    for r in range(R):
        for c in range(C):
            v = 격자[r][c]
            몸.append(_네모(x0 + c * 칸, y0 + r * 칸, 칸 - 1, 칸 - 1, 색(v), "#ffffff", 0.4, 1))
            if 값글 and 칸 >= 18:
                몸.append(_글(x0 + c * 칸 + 칸 / 2, y0 + r * 칸 + 칸 / 2 + 3, _수(v, 2), 7.5,
                            먹 if (v - lo) / rng < 0.6 else "#ffffff", "middle"))
    bx = x0 + C * 칸 + 16
    for i in range(20):
        t = i / 19
        몸.append(_네모(bx, y0 + R * 칸 - (i + 1) * (R * 칸 / 20), 12, R * 칸 / 20 + 0.6,
                      색(lo + rng * t), "none", 0, 0))
    몸.append(_글(bx + 15, y0 + 8, _수(hi), 8.5, 흐림))
    몸.append(_글(bx + 15, y0 + R * 칸, _수(lo), 8.5, 흐림))
    if x라벨:
        for c, s in enumerate(x라벨[:C]):
            몸.append(_글(x0 + c * 칸 + 칸 / 2, y0 + R * 칸 + 13, s, 8, 흐림, "middle"))
    if y라벨:
        for r, s in enumerate(y라벨[:R]):
            몸.append(_글(x0 - 5, y0 + r * 칸 + 칸 / 2 + 3, s, 8, 흐림, "end"))
    if x이름:
        몸.append(_글(x0 + C * 칸 / 2, 높이 - 8, x이름, 10, 먹, "middle"))
    if 제목:
        몸.append(_글(폭 / 2, 17, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(몸), 제목)


def 게이지묶음(항목들, 제목="", 폭=560, 칸높이=26) -> str:
    """항목들 = [(이름, 값0~1, 오른쪽글, 색)] -- 커버리지·점유율 같은 비율에 쓴다."""
    if not 항목들:
        return 빈그림()
    y0 = 30 if 제목 else 10
    높이 = y0 + len(항목들) * 칸높이 + 12
    이름폭, 값폭 = 160, 92
    W = 폭 - 이름폭 - 값폭 - 20
    몸 = []
    for i, it in enumerate(항목들):
        nm, v = it[0], max(0.0, min(1.0, float(it[1])))
        글 = it[2] if len(it) > 2 else f"{v*100:.1f} %"
        c = it[3] if len(it) > 3 else (초록 if v >= 0.9 else (주황 if v >= 0.7 else 빨강))
        y = y0 + i * 칸높이
        몸.append(_글(이름폭 - 6, y + 15, nm, 10, 먹, "end"))
        몸.append(_네모(이름폭, y + 5, W, 14, 연바탕, 선색, 0.8, 3))
        몸.append(_네모(이름폭, y + 5, W * v, 14, c, c, 0.4, 3))
        몸.append(_글(이름폭 + W + 8, y + 16, 글, 9.5, 먹, "start", 굵게=True))
    if 제목:
        몸.append(_글(폭 / 2, 17, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(몸), 제목)


# ---------------------------------------------------------------- 회로/흐름 그림

def 흐름(단계들, 제목="", 폭=640, 강조=None, 아래글="", 되돌이=None) -> str:
    """가로 흐름도.  단계들 = [(윗줄, 아랫줄)] 또는 ["이름"].

    `되돌이` = (뒤단계i, 앞단계j, 라벨) 이면 i 에서 j 로 돌아가는 빨간 화살을 얹는다.
    """
    if not 단계들:
        return 빈그림()
    단계들 = [(s, "") if isinstance(s, str) else s for s in 단계들]
    n = len(단계들)
    여백, 간격 = 14, 22
    칸 = max(70, (폭 - 여백 * 2 - 간격 * (n - 1)) / n)
    실폭 = 여백 * 2 + 칸 * n + 간격 * (n - 1)
    y0 = 58 if (제목 or 되돌이) else 20
    # **상자 높이는 글이 정한다.** 46 으로 박아 두면 두 줄짜리 이름이 상자를 뚫는다.
    속폭 = 칸 - 8
    앉은것 = []
    for a, b in 단계들:
        A, ca = 앉히기(a, 10.5, 속폭, 2)
        B, cb = 앉히기(b, 9, 속폭, 1) if b else ([], 9)
        앉은것.append((A, ca, B, cb))
    줄수최대 = max((len(A) + len(B)) for A, _, B, _ in 앉은것) if 앉은것 else 1
    상자높이 = max(46, 14 + 줄수최대 * 13)
    높이 = y0 + 상자높이 + 8 + (26 if 아래글 else 8)
    몸 = []
    for i, (a, b) in enumerate(단계들):
        A, ca, B, cb = 앉은것[i]
        x = 여백 + i * (칸 + 간격)
        칠 = "#fdf6e3" if (강조 and i in 강조) else "#ffffff"
        가운데 = y0 + 상자높이 / 2
        몸.append(_네모(x, y0, 칸, 상자높이, 칠, 먹, 1.5))
        총 = len(A) + len(B)
        첫 = 가운데 - (총 - 1) * 6.5 + 3.5
        for j, t in enumerate(A):
            몸.append(_글(x + 칸 / 2, 첫 + j * 13, t, ca, 먹, "middle", 굵게=True))
        for j, t in enumerate(B):
            몸.append(_글(x + 칸 / 2, 첫 + (len(A) + j) * 13, t, cb, 흐림, "middle"))
        if i < n - 1:
            몸.append(_화살(x + 칸, 가운데, x + 칸 + 간격, 가운데))
    if 되돌이:
        i, j, lab = 되돌이
        xi = 여백 + i * (칸 + 간격) + 칸 / 2
        xj = 여백 + j * (칸 + 간격) + 칸 / 2
        top = y0 - 26
        몸.append(_선(xi, y0, xi, top, 빨강, 1.5))
        몸.append(_선(xi, top, xj, top, 빨강, 1.5))
        몸.append(_화살(xj, top, xj, y0 - 2, 빨강, 1.5))
        몸.append(_글((xi + xj) / 2, top - 5, lab, 9, 빨강, "middle", 굵게=True))
    if 제목:
        몸.append(_글(실폭 / 2, 17, 제목, 12, 먹, "middle", 굵게=True))
    if 아래글:
        몸.append(_글(여백, 높이 - 10, 아래글, 9, 흐림))
    return svg(실폭, 높이, "".join(몸), 제목)


def 상태도(상태들, 간선들, 제목="", 폭=600, 높이=260, 시작=None) -> str:
    """FSM 거품도.  상태들 = ["IDLE",...], 간선들 = [(a,b,조건)].

    자기 자신으로 가는 간선은 위에 고리로 그린다.
    """
    if not 상태들:
        return 빈그림()
    n = len(상태들)
    cx, cy = 폭 / 2, 높이 / 2 + (10 if 제목 else 0)
    R = min(폭, 높이) * 0.33
    r = 27
    자리 = {}
    for i, s in enumerate(상태들):
        th = -math.pi / 2 + 2 * math.pi * i / n
        자리[s] = (cx + R * math.cos(th) * 1.45, cy + R * math.sin(th))
    몸 = []
    for a, b, cond in 간선들:
        if a not in 자리 or b not in 자리:
            continue
        ax, ay = 자리[a]
        bx, by = 자리[b]
        if a == b:
            몸.append(f'<path d="M{ax-12:.1f},{ay-r+4:.1f} C{ax-30:.1f},{ay-r-34:.1f} '
                      f'{ax+30:.1f},{ay-r-34:.1f} {ax+12:.1f},{ay-r+4:.1f}" fill="none" '
                      f'stroke="{흐림}" stroke-width="1.3"/>')
            몸.append(_글(ax, ay - r - 26, cond, 8.5, 흐림, "middle"))
            continue
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        몸.append(_화살(ax + ux * r, ay + uy * r, bx - ux * (r + 2), by - uy * (r + 2), 흐림, 1.3))
        mx, my = (ax + bx) / 2 - uy * 11, (ay + by) / 2 + ux * 11
        몸.append(_글(mx, my, cond, 8.5, 파랑, "middle"))
    for s in 상태들:
        x, y = 자리[s]
        칠 = "#fdf6e3" if s == 시작 else "#eef4fb"
        몸.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{칠}" stroke="{먹}" stroke-width="1.5"/>')
        몸.append(_글(x, y + 4, s, 9.5, 먹, "middle", 굵게=True))
    if 시작 and 시작 in 자리:
        x, y = 자리[시작]
        몸.append(_화살(x - r - 26, y, x - r - 2, y, 먹, 1.6))
        몸.append(_글(x - r - 28, y - 7, "reset", 8.5, 먹, "end"))
    if 제목:
        몸.append(_글(폭 / 2, 17, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(몸), 제목)


def 파형(신호들, 제목="", 폭=640, 칸=26, 주기폭=26, 표시=None) -> str:
    """디지털 파형.  신호들 = [(이름, "0011xx1", 종류)] -- 종류: "bit" | "bus".

    bus 이면 문자열의 글자마다 한 칸을 차지하는 값으로 그린다(육각 모양).
    `표시` = [(주기, 글, 색)] 이면 그 주기에 세로 표시선을 얹는다.
    """
    if not 신호들:
        return 빈그림()
    이름폭 = 96
    N = max(len(v) for _, v, *_ in 신호들)
    y0 = 34 if 제목 else 14
    높이 = y0 + len(신호들) * 칸 + 30
    실폭 = 이름폭 + N * 주기폭 + 24
    몸 = []
    for c in range(N + 1):
        x = 이름폭 + c * 주기폭
        몸.append(_선(x, y0 - 4, x, y0 + len(신호들) * 칸, "#eceff3", 0.8))
    for c in range(N):
        몸.append(_글(이름폭 + c * 주기폭 + 주기폭 / 2, y0 - 8, str(c), 8, 흐림, "middle"))
    for i, sg in enumerate(신호들):
        nm, v = sg[0], sg[1]
        종류 = sg[2] if len(sg) > 2 else "bit"
        y = y0 + i * 칸
        hi, lo = y + 5, y + 19
        몸.append(_글(이름폭 - 8, y + 15, nm, 9.5, 먹, "end", 글꼴이름=등폭))
        if 종류 == "bit":
            앞 = None
            d = []
            for c, ch in enumerate(v):
                x = 이름폭 + c * 주기폭
                lvl = hi if ch in "1H" else lo
                if ch in "xX":
                    몸.append(_네모(x, hi, 주기폭, lo - hi, "#f3dede", 빨강, 0.6, 1))
                    앞 = None
                    continue
                if 앞 is not None and 앞 != lvl:
                    d.append(f"L{x:.1f},{lvl:.1f}")
                d.append(("M" if 앞 is None else "L") + f"{x:.1f},{lvl:.1f}")
                d.append(f"L{x+주기폭:.1f},{lvl:.1f}")
                앞 = lvl
            if d:
                몸.append(f'<path d="{" ".join(d)}" fill="none" stroke="{파랑}" stroke-width="1.7"/>')
        else:
            for c, ch in enumerate(v):
                x = 이름폭 + c * 주기폭
                if ch in " -":
                    continue
                몸.append(f'<path d="M{x+3:.1f},{(hi+lo)/2:.1f} L{x+6:.1f},{hi:.1f} '
                          f'L{x+주기폭-6:.1f},{hi:.1f} L{x+주기폭-3:.1f},{(hi+lo)/2:.1f} '
                          f'L{x+주기폭-6:.1f},{lo:.1f} L{x+6:.1f},{lo:.1f} Z" '
                          f'fill="#eef4fb" stroke="{파랑}" stroke-width="1.1"/>')
                몸.append(_글(x + 주기폭 / 2, (hi + lo) / 2 + 3.5, ch, 8.5, 먹, "middle", 글꼴이름=등폭))
    for t in (표시 or []):
        c, g = t[0], t[1]
        col = t[2] if len(t) > 2 else 빨강
        x = 이름폭 + c * 주기폭 + 주기폭 / 2
        몸.append(_선(x, y0 - 4, x, y0 + len(신호들) * 칸, col, 1.4, "4,3"))
        몸.append(_글(x, y0 + len(신호들) * 칸 + 14, g, 8.5, col, "middle", 굵게=True))
    if 제목:
        몸.append(_글(실폭 / 2, 17, 제목, 12, 먹, "middle", 굵게=True))
    return svg(실폭, 높이, "".join(몸), 제목)


def 예약표(단계이름들, 항목들, 제목="", 폭=640, 칸높이=24, 주기폭=44) -> str:
    """파이프라인 예약표.  항목들 = [(이름, 시작주기, [단계i...])].

    한 줄이 한 거래이고, 칸 하나가 (주기, 단계) 다.  겹쳐 보이는 것이 파이프라인이다.
    """
    if not 항목들:
        return 빈그림()
    이름폭 = 78
    N = max(시작 + len(단계) for _, 시작, 단계 in 항목들)
    y0 = 48 if 제목 else 26
    높이 = y0 + len(항목들) * 칸높이 + 22
    실폭 = 이름폭 + N * 주기폭 + 16
    몸 = []
    for c in range(N):
        x = 이름폭 + c * 주기폭
        몸.append(_선(x, y0 - 16, x, y0 + len(항목들) * 칸높이, "#eceff3", 0.8))
        몸.append(_글(x + 주기폭 / 2, y0 - 20, f"T{c}", 8.5, 흐림, "middle"))
    for i, (nm, 시작, 단계) in enumerate(항목들):
        y = y0 + i * 칸높이
        몸.append(_글(이름폭 - 8, y + 16, nm, 9, 먹, "end", 글꼴이름=등폭))
        for k, st in enumerate(단계):
            x = 이름폭 + (시작 + k) * 주기폭
            c = 계열[st % len(계열)] if isinstance(st, int) else 파랑
            이름 = 단계이름들[st] if isinstance(st, int) and st < len(단계이름들) else str(st)
            몸.append(_네모(x + 2, y + 3, 주기폭 - 4, 칸높이 - 7, c, c, 0.5, 3))
            몸.append(_글(x + 주기폭 / 2, y + 17, 이름, 8.5, "#ffffff", "middle", 굵게=True))
    if 제목:
        몸.append(_글(실폭 / 2, 17, 제목, 12, 먹, "middle", 굵게=True))
    return svg(실폭, 높이, "".join(몸), 제목)


def 블록도(블록들, 연결들, 제목="", 폭=640, 높이=300) -> str:
    """자리를 직접 주는 블록도.  블록들 = [(이름, x, y, w, h, 색, 부제)].

    연결들 = [(a, b, 라벨, 색)] -- 블록 이름으로 잇는다.  CDC 경계 · 클럭 도메인에 쓴다.
    """
    자리 = {}
    몸 = []
    for b in 블록들:
        nm, x, y, w, h = b[0], b[1], b[2], b[3], b[4]
        색칠 = b[5] if len(b) > 5 else "#ffffff"
        부제 = b[6] if len(b) > 6 else ""
        자리[nm] = (x, y, w, h)
        몸.append(_네모(x, y, w, h, 색칠, 먹, 1.5))
        # **상자 폭에 맞춰 앉힌다.** 실측 2026-09-22: 부제가 26자에서 잘려 있었는데도
        # 142 px 상자를 220 px 로 뚫고 나가 옆 상자와 겹쳤다. 글자 수가 아니라 **폭**이다.
        몸.append(_칸글(x + w / 2, y + (h / 2 + 3 if not 부제 else h / 2 - 4), nm,
                      10, 먹, w - 8, 1, 굵게=True))
        if 부제:
            몸.append(_칸글(x + w / 2, y + h / 2 + 8, 부제, 8.5, 흐림, w - 8, 2))
    for c in 연결들:
        a, b = c[0], c[1]
        라벨 = c[2] if len(c) > 2 else ""
        색칠 = c[3] if len(c) > 3 else 먹
        if a not in 자리 or b not in 자리:
            continue
        ax, ay, aw, ah = 자리[a]
        bx, by, bw, bh = 자리[b]
        if bx >= ax + aw:
            p1, p2 = (ax + aw, ay + ah / 2), (bx, by + bh / 2)
        elif bx + bw <= ax:
            p1, p2 = (ax, ay + ah / 2), (bx + bw, by + bh / 2)
        elif by >= ay + ah:
            p1, p2 = (ax + aw / 2, ay + ah), (bx + bw / 2, by)
        else:
            p1, p2 = (ax + aw / 2, ay), (bx + bw / 2, by + bh)
        몸.append(_화살(p1[0], p1[1], p2[0], p2[1], 색칠, 1.4))
        if 라벨:
            몸.append(_글((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 - 5, 라벨, 8.5, 색칠, "middle"))
    if 제목:
        몸.append(_글(폭 / 2, 17, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(몸), 제목)


def 레이아웃(코어_um, 행들, 셀들, 배선=None, 제목="", 폭=560, 스트라이프=None) -> str:
    """배치 결과를 진짜 좌표로 그린다.  셀들 = [(x,y,w,h,종류)] (um).

    종류: "seq"(플롭) · "comb" · "buf" -- 색을 달리해서 클럭 트리가 보이게 한다.
    """
    W, H = 코어_um
    y0 = 30 if 제목 else 12
    그릴폭 = 폭 - 24
    s = 그릴폭 / max(W, 1e-9)
    높이 = y0 + H * s + 40
    몸 = [_네모(12, y0, W * s, H * s, "#fbfcfd", 먹, 1.4, 2)]
    for r in (행들 or []):
        몸.append(_선(12, y0 + r * s, 12 + W * s, y0 + r * s, "#eceff3", 0.5))
    for st in (스트라이프 or []):
        몸.append(_네모(12 + st * s - 1.2, y0, 2.4, H * s, "#d9c9f0", "none", 0, 0))
    색표 = {"seq": 빨강, "comb": 파랑, "buf": 초록, "icg": 주황}
    for c in 셀들:
        x, y, w, h = c[0], c[1], c[2], c[3]
        종류 = c[4] if len(c) > 4 else "comb"
        몸.append(_네모(12 + x * s, y0 + y * s, max(w * s, 0.7), max(h * s - 0.6, 1.0),
                      색표.get(종류, 파랑), "none", 0, 0.5))
    for ln in (배선 or []):
        x1, y1, x2, y2 = ln
        몸.append(_선(12 + x1 * s, y0 + y1 * s, 12 + x2 * s, y0 + y2 * s, "#9db9d6", 0.45))
    for i, (k, v) in enumerate(색표.items()):
        몸.append(_네모(12 + i * 62, 높이 - 22, 10, 10, v, "none", 0, 2))
        몸.append(_글(12 + i * 62 + 14, 높이 - 13, k, 8.5, 흐림))
    몸.append(_글(폭 - 12, 높이 - 13, f"코어 {W:.1f} × {H:.1f} µm", 8.5, 흐림, "end"))
    if 제목:
        몸.append(_글(폭 / 2, 17, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(몸), 제목)


def 표(머리, 줄들, 강조열=None, 폭=None) -> str:
    """HTML 표.  그림이 아닌 것은 표로 낸다 -- 수를 그림으로만 내면 못 읽는다."""
    th = "".join(f"<th>{_e(h)}</th>" for h in 머리)
    tr = []
    for r in 줄들:
        tds = []
        for i, v in enumerate(r):
            cls = ' class="hi"' if (강조열 and i in 강조열) else ""
            tds.append(f"<td{cls}>{v if isinstance(v, str) and v.startswith('<') else _e(v)}</td>")
        tr.append("<tr>" + "".join(tds) + "</tr>")
    st = f' style="max-width:{폭}px"' if 폭 else ""
    return f'<table class="d"{st}><thead><tr>{th}</tr></thead><tbody>{"".join(tr)}</tbody></table>'


def 전원계획(다이, 코어, 스트라이프x, 스트라이프폭, 링폭=2.0, 행수=0,
          제목="", 폭=440) -> str:
    """다이 · 패드링 · 코어 · 전원 링 · 스트라이프를 실제 치수로 그린다.

    강의 화면의 그 그림이지만 **수가 이 칩의 것**이다.  스트라이프 폭은 보이게
    하려고 최소 1.5 px 로 잡아 그린다 -- 실제 폭은 글로 같이 적는다.
    """
    DW, DH = 다이
    CW, CH = 코어
    y0 = 30 if 제목 else 12
    그릴폭 = 폭 - 24
    s = 그릴폭 / max(DW, 1e-9)
    높이 = y0 + DH * s + 46
    ox, oy = (DW - CW) / 2, (DH - CH) / 2
    몸 = [_네모(12, y0, DW * s, DH * s, "#f4f6f9", 먹, 1.4, 2)]          # 다이
    몸.append(_네모(12 + ox * s, y0 + oy * s, CW * s, CH * s, "#ffffff", 흐림, 1.0, 1))
    # 전원 링 -- 코어 둘레
    링 = max(링폭 * s, 2.0)
    for (rx, ry, rw, rh) in ((ox, oy, CW, 0), (ox, oy + CH, CW, 0),
                             (ox, oy, 0, CH), (ox + CW, oy, 0, CH)):
        몸.append(_네모(12 + rx * s - 링 / 2, y0 + ry * s - 링 / 2,
                      max(rw * s, 링), max(rh * s, 링), "#e05c3e", "none", 0, 0))
    for x in 스트라이프x:
        몸.append(_네모(12 + x * s - max(스트라이프폭 * s, 1.5) / 2, y0 + oy * s,
                      max(스트라이프폭 * s, 1.5), CH * s, "#8e6fc0", "none", 0, 0))
    for k in range(행수):
        ry = oy + CH * (k + 0.5) / max(행수, 1)
        몸.append(_선(12 + ox * s, y0 + ry * s, 12 + (ox + CW) * s, y0 + ry * s,
                     "#eceff3", 0.4))
    몸.append(_글(12 + (ox + CW / 2) * s, y0 + (oy + CH / 2) * s, "CORE",
                10, 흐림, "middle", 굵게=True))
    몸.append(_글(14, y0 + 12, "PAD RING", 8.5, 흐림))
    for i, (c, t) in enumerate((("#e05c3e", "전원 링"), ("#8e6fc0", "스트라이프"))):
        몸.append(_네모(12 + i * 86, 높이 - 26, 10, 10, c, "none", 0, 2))
        몸.append(_글(12 + i * 86 + 14, 높이 - 17, t, 8.5, 흐림))
    몸.append(_글(폭 - 12, 높이 - 17,
                f"다이 {DW:.0f}×{DH:.0f} / 코어 {CW:.0f}×{CH:.0f} µm", 8.5, 흐림, "end"))
    몸.append(_글(폭 - 12, 높이 - 6,
                f"스트라이프 {len(스트라이프x)}개 × {스트라이프폭:.3f} µm", 8.5, 흐림, "end"))
    if 제목:
        몸.append(_글(폭 / 2, 17, 제목, 12, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(몸), 제목)


# ================================================================== 실제 도구 화면
#
# 아래 셋은 **상용 도구의 화면을 흉내 낸 것이 아니라, 같은 정보를 같은 꼴로 내는
# 것**이다. 파형 뷰어는 VCD 에서 읽은 시각과 값만 그리고, 커버그룹 창은 시뮬이
# 낸 빈 개수만 그린다. 흉내 낸 것은 배치와 색뿐이다.

def 파형뷰어(신호들, 제목="", 폭=680, 칸=22, 시작시각=0, 끝시각=None,
          눈금="ps", 표시=None, 주석띠=None) -> str:
    """파형 뷰어 화면.  검은 판에 초록 파형 -- ModelSim/Verdi 가 내는 그 꼴이다.

    신호들 = [(이름, "0011xx", "bit"|"bus")]  (house/dv/vcd.뽑기 · 원시 가 내는 꼴)
    표시   = [(칸번호, 글, 색)]      세로 커서
    주석띠 = [(시작칸, 끝칸, 글, 색)] 아래에 구간을 표시한다 -- 강의 화면의
             Start / Address / Ack / Stop 띠가 그것이다
    """
    if not 신호들:
        return 빈그림("VCD 에서 뽑은 신호가 없다")
    이름폭 = 118
    N = max(len(v) for _, v, *_ in 신호들)
    그릴폭 = 폭 - 이름폭 - 16
    주기폭 = 그릴폭 / max(N, 1)
    y0 = 34 if 제목 else 12
    머리 = 18
    띠높이 = 20 * (1 + max([0] + [i for i, _ in enumerate(주석띠 or [])]) // 8) if 주석띠 else 0
    높이 = y0 + 머리 + len(신호들) * 칸 + (26 if 표시 else 8) + (띠높이 + 10 if 주석띠 else 0)
    판위 = y0 + 머리
    판아래 = 판위 + len(신호들) * 칸
    m = [_네모(이름폭, 판위 - 2, 그릴폭, 판아래 - 판위 + 4, "#101418", "#2b3138", 1.0, 2),
         _네모(6, 판위 - 2, 이름폭 - 8, 판아래 - 판위 + 4, "#f7f8fa", "#d7dce2", 1.0, 2)]
    # 시각 눈금자
    칸수 = max(1, N // 8)
    for c in range(0, N + 1, 칸수):
        x = 이름폭 + c * 주기폭
        m.append(_선(x, 판위 - 2, x, 판아래, "#232a31", 0.8))
        t = 시작시각 + (끝시각 - 시작시각) * c / max(N, 1) if 끝시각 else c
        m.append(_글(x, 판위 - 6, f"{t:,.0f}{눈금 if 끝시각 else ''}", 7.2, 흐림, "middle"))
    for i, sg in enumerate(신호들):
        nm, v = sg[0], sg[1]
        종류 = sg[2] if len(sg) > 2 else "bit"
        y = 판위 + i * 칸
        hi, lo = y + 4, y + 칸 - 5
        if i % 2:
            m.append(_네모(이름폭, y, 그릴폭, 칸, "#161b20", "none", 0, 0))
        m.append(_글(이름폭 - 14, y + 칸 / 2 + 3.5, nm, 8.4, 먹, "end", 글꼴이름=등폭))
        if 종류 == "bit":
            앞 = None
            d = []
            for c, ch in enumerate(v):
                x = 이름폭 + c * 주기폭
                if ch in "xXzZ":
                    m.append(_네모(x, hi, 주기폭, lo - hi, "#5a2323", "#c0392b", 0.6, 0))
                    앞 = None
                    continue
                lvl = hi if ch in "1H" else lo
                if 앞 is not None and 앞 != lvl:
                    d.append(f"L{x:.2f},{lvl:.2f}")
                d.append(("M" if 앞 is None else "L") + f"{x:.2f},{lvl:.2f}")
                d.append(f"L{x+주기폭:.2f},{lvl:.2f}")
                앞 = lvl
            if d:
                m.append(f'<path d="{" ".join(d)}" fill="none" stroke="#35d07f" '
                         f'stroke-width="1.5"/>')
        else:
            c = 0
            while c < len(v):
                j = c
                while j + 1 < len(v) and v[j + 1] == v[c]:
                    j += 1
                x0 = 이름폭 + c * 주기폭
                x1 = 이름폭 + (j + 1) * 주기폭
                ch = v[c]
                색 = "#c0392b" if ch == "x" else "#35d07f"
                채 = "#5a2323" if ch == "x" else "#12301f"
                꺾 = min(3.0, (x1 - x0) / 3)
                m.append(f'<path d="M{x0+꺾:.2f},{hi:.2f} L{x1-꺾:.2f},{hi:.2f} '
                         f'L{x1:.2f},{(hi+lo)/2:.2f} L{x1-꺾:.2f},{lo:.2f} '
                         f'L{x0+꺾:.2f},{lo:.2f} L{x0:.2f},{(hi+lo)/2:.2f} Z" '
                         f'fill="{채}" stroke="{색}" stroke-width="1.1"/>')
                if x1 - x0 > 13:
                    m.append(_글((x0 + x1) / 2, (hi + lo) / 2 + 3, ch, 7.4, "#9fe8c2",
                                "middle", 글꼴이름=등폭))
                c = j + 1
    for t in (표시 or []):
        c, g = t[0], t[1]
        col = t[2] if len(t) > 2 else "#e8c547"
        x = 이름폭 + c * 주기폭
        m.append(_선(x, 판위 - 2, x, 판아래, col, 1.3, "3,2"))
        m.append(_글(x, 판아래 + 13, g, 8, col, "middle", 굵게=True))
    for k, b in enumerate(주석띠 or []):
        c0, c1, g = b[0], b[1], b[2]
        col = b[3] if len(b) > 3 else "#c0392b"
        x0 = 이름폭 + c0 * 주기폭
        x1 = 이름폭 + c1 * 주기폭
        yy = 판아래 + 6 + (k % 2) * 18
        m.append(_네모(x0, yy, max(x1 - x0, 2), 15, "none", col, 1.2, 2))
        m.append(_글((x0 + x1) / 2, yy + 11, g, 7.6, col, "middle", 굵게=True))
    if 제목:
        m.append(_글(폭 / 2, 18, 제목, 11.5, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(m), 제목)


def 커버그룹(줄들, 제목="Covergroups", 폭=620, 칸=21) -> str:
    """커버리지 창.  줄들 = [(들여쓰기, 종류, 이름, 퍼센트, 목표, 빈설명)].

    종류: "pkg"(꾸러미) · "type"(커버그룹) · "cvp"(커버포인트) · "cross"(교차).
    상용 커버리지 뷰어가 내는 것과 **같은 칸**을 낸다 -- Name / Coverage /
    Goal / % of Goal / Status.  퍼센트는 시뮬이 실제로 센 빈 수에서 온다.
    """
    if not 줄들:
        return 빈그림("커버리지 줄이 없다")
    y0 = 30 if 제목 else 8
    머리 = 20
    높이 = y0 + 머리 + len(줄들) * 칸 + 12
    이름폭, 값폭, 목표폭, 비폭 = 246, 62, 46, 58
    막대x = 이름폭 + 값폭 + 목표폭 + 비폭 + 16
    막대폭 = 폭 - 막대x - 46
    m = [_네모(8, y0, 폭 - 16, 머리 + len(줄들) * 칸 + 4, "#ffffff", "#b9c0c8", 1.0, 2),
         _네모(9, y0 + 1, 폭 - 18, 머리 - 2, "#dfe4ea", "none", 0, 0)]
    for t, x, a in (("Name", 16, "start"), ("Coverage", 이름폭 + 값폭, "end"),
                    ("Goal", 이름폭 + 값폭 + 목표폭, "end"),
                    ("% of Goal", 이름폭 + 값폭 + 목표폭 + 비폭, "end"),
                    ("Status", 막대x + 2, "start")):
        m.append(_글(x, y0 + 14, t, 8.2, "#31383f", a, 굵게=True))
    for i, r in enumerate(줄들):
        들, 종, 이름, 퍼, 목, 설 = (list(r) + ["", "", "", 0, 100, ""])[:6]
        y = y0 + 머리 + i * 칸
        if i % 2:
            m.append(_네모(9, y, 폭 - 18, 칸, "#f6f8fa", "none", 0, 0))
        표 = {"pkg": "▣", "type": "▤", "cvp": "▫", "cross": "✕"}.get(종, "·")
        m.append(_글(16 + 들 * 14, y + 14, f"{표} {이름}", 8.2,
                    먹 if 종 in ("pkg", "type") else "#454b54",
                    굵게=(종 in ("pkg", "type")), 글꼴이름=등폭))
        m.append(_글(이름폭 + 값폭, y + 14, f"{퍼:.1f}%", 8.2, 먹, "end", 글꼴이름=등폭))
        m.append(_글(이름폭 + 값폭 + 목표폭, y + 14, f"{목:.0f}", 8.2, 흐림, "end"))
        비 = min(100.0, 퍼 / max(목, 1e-9) * 100)
        m.append(_글(이름폭 + 값폭 + 목표폭 + 비폭, y + 14, f"{비:.1f}%", 8.2,
                    먹 if 비 >= 100 else 빨강, "end", 글꼴이름=등폭,
                    굵게=(비 < 100)))
        m.append(_네모(막대x, y + 4, 막대폭, 13, "#ffffff", "#9aa2ab", 0.8, 1))
        찬 = 막대폭 * min(1.0, 비 / 100)
        색 = "#1fc35a" if 비 >= 100 else ("#e8c547" if 비 >= 70 else "#e05c3e")
        if 찬 > 0:
            m.append(_네모(막대x, y + 4, 찬, 13, 색, "none", 0, 1))
        m.append(_글(폭 - 14, y + 14, f"{설}", 7.4, 흐림, "end"))
    if 제목:
        m.append(_글(폭 / 2, 17, 제목, 11.5, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(m), 제목)


def 플로어플랜도(다이, 코어, 스트라이프x, 스트라이프폭, 가로스트라이프=5, 링폭=2.0,
            패드수=32, 제목="", 폭=470) -> str:
    """강의 화면의 플로어플랜 그림 -- Corner cell · I/O Pad · Filler · Power Ring ·
    Stripe · Core Area 를 **라벨까지** 붙여 그린다.  치수는 실제 값이다."""
    DW, DH = 다이
    CW, CH = 코어
    y0 = 30 if 제목 else 10
    그릴 = 폭 - 170
    s_ = 그릴 / max(DW, 1e-9)
    높이 = y0 + DH * s_ + 30
    ox, oy = (DW - CW) / 2, (DH - CH) / 2
    X0 = 14
    m = [_네모(X0, y0, DW * s_, DH * s_, "#ffffff", 흐림, 1.0, 1)]
    패드 = max((DW - CW) / 2 * 0.42 * s_, 7)
    칸 = max(4, 패드수 // 4)
    # I/O 패드와 필러
    for i in range(칸):
        for (px, py, w, h) in ((X0 + 패드 + i * (DW * s_ - 2 * 패드) / 칸, y0,
                                (DW * s_ - 2 * 패드) / 칸 - 1, 패드),
                               (X0 + 패드 + i * (DW * s_ - 2 * 패드) / 칸,
                                y0 + DH * s_ - 패드, (DW * s_ - 2 * 패드) / 칸 - 1, 패드),
                               (X0, y0 + 패드 + i * (DH * s_ - 2 * 패드) / 칸, 패드,
                                (DH * s_ - 2 * 패드) / 칸 - 1),
                               (X0 + DW * s_ - 패드,
                                y0 + 패드 + i * (DH * s_ - 2 * 패드) / 칸, 패드,
                                (DH * s_ - 2 * 패드) / 칸 - 1)):
            m.append(_네모(px, py, w, h,
                          "#d6f0f2" if i % 2 else "#dcdfe3", "#b6bcc4", 0.5, 0))
    for (cx, cy) in ((X0, y0), (X0 + DW * s_ - 패드, y0),
                     (X0, y0 + DH * s_ - 패드), (X0 + DW * s_ - 패드, y0 + DH * s_ - 패드)):
        m.append(_네모(cx, cy, 패드, 패드, "#a8d8e0", "#7fa8b4", 0.7, 0))
    # 전원 링 2겹
    for k, 여 in enumerate((6, 11)):
        m.append(_네모(X0 + ox * s_ - 여, y0 + oy * s_ - 여,
                      CW * s_ + 2 * 여, CH * s_ + 2 * 여, "none", "#8a8f98", 1.2, 0))
    # 코어
    m.append(_네모(X0 + ox * s_, y0 + oy * s_, CW * s_, CH * s_, "#f2f8f4", "#9aa2ab", 0.9, 0))
    # 스트라이프
    for x in 스트라이프x:
        m.append(_네모(X0 + x * s_ - max(스트라이프폭 * s_, 2.2) / 2, y0 + oy * s_ - 11,
                      max(스트라이프폭 * s_, 2.2), CH * s_ + 22, "#7b3fbf", "none", 0, 0))
    for k in range(가로스트라이프):
        yy = oy + CH * (k + 0.5) / max(가로스트라이프, 1)
        m.append(_네모(X0 + ox * s_ - 11, y0 + yy * s_ - 1.6,
                      CW * s_ + 22, 3.2, "#7b3fbf", "none", 0, 0))
    # 라벨
    라벨 = [("Corner cell", X0 + DW * s_ - 패드 / 2, y0 + 패드 / 2),
          ("Power Rings", X0 + ox * s_ + CW * s_ + 9, y0 + oy * s_ - 8),
          ("Power Stripes", X0 + (스트라이프x[len(스트라이프x) // 2] if 스트라이프x else ox) * s_,
           y0 + oy * s_ + CH * s_ * 0.24),
          ("Core Area", X0 + ox * s_ + CW * s_ * 0.6, y0 + oy * s_ + CH * s_ * 0.5),
          ("I/O Pad", X0 + DW * s_ - 패드 / 2, y0 + DH * s_ * 0.66),
          ("I/O Filler", X0 + DW * s_ - 패드 / 2, y0 + DH * s_ * 0.8)]
    for i, (t, ax, ay) in enumerate(라벨):
        tx = 폭 - 150
        ty = y0 + 16 + i * 17
        m.append(_선(ax, ay, tx - 4, ty - 3, "#6b7076", 0.6))
        m.append(_글(tx, ty, t, 7.6, 먹))
    m.append(_글(X0, 높이 - 8, f"다이 {DW:.0f} × {DH:.0f} µm · 코어 {CW:.0f} × {CH:.0f} µm · "
                f"스트라이프 {len(스트라이프x)} × {스트라이프폭:.3f} µm · 패드 {패드수}개",
                7.4, 흐림))
    if 제목:
        m.append(_글(폭 / 2, 18, 제목, 11.5, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(m), 제목)


def 레이아웃뷰어(코어_um, 셀들, 배선=None, 클럭=None, 제목="", 폭=560, 층수=4) -> str:
    """레이아웃 뷰어 화면 -- 검은 판에 금속 층을 색으로 겹쳐 그린다.

    강의 화면의 그 빽빽한 그림이다.  `배선` = [(x1,y1,x2,y2,층)],
    `클럭` = [(x1,y1,x2,y2)] 는 흰 선으로 따로 그린다(CTS 뷰어의 그 하이라이트).
    """
    W, H = 코어_um
    y0 = 30 if 제목 else 10
    판폭 = 폭 - 108
    s_ = 판폭 / max(W, 1e-9)
    높이 = y0 + H * s_ + 26
    층색 = ["#c0392b", "#2e86c1", "#27ae60", "#d4ac0d", "#8e44ad", "#16a085"]
    m = [_네모(96, y0, W * s_, H * s_, "#07090b", "#3b4148", 1.0, 1)]
    # 왼쪽 층 목록 (뷰어의 그 패널)
    m.append(_네모(8, y0, 82, min(H * s_, 16 + 층수 * 13 + 8), "#eceff3", "#b9c0c8", 0.9, 2))
    m.append(_글(14, y0 + 12, "Layers", 7.6, 먹, 굵게=True))
    for i in range(층수):
        m.append(_네모(14, y0 + 17 + i * 13, 9, 9, 층색[i % len(층색)], "none", 0, 1))
        m.append(_글(28, y0 + 25 + i * 13, f"M{i+1}", 7.2, 먹))
    for c in 셀들:
        x, y, w, h = c[0], c[1], c[2], c[3]
        종 = c[4] if len(c) > 4 else "comb"
        색 = {"seq": "#7b241c", "icg": "#7d6608"}.get(종, "#1a3b2a")
        m.append(_네모(96 + x * s_, y0 + y * s_, max(w * s_, 0.6),
                      max(h * s_ - 0.5, 0.9), 색, "none", 0, 0))
    for ln in (배선 or []):
        x1, y1, x2, y2 = ln[0], ln[1], ln[2], ln[3]
        L = ln[4] if len(ln) > 4 else 0
        m.append(_선(96 + x1 * s_, y0 + y1 * s_, 96 + x2 * s_, y0 + y2 * s_,
                     층색[L % len(층색)], 0.45))
    for ln in (클럭 or []):
        m.append(_선(96 + ln[0] * s_, y0 + ln[1] * s_, 96 + ln[2] * s_, y0 + ln[3] * s_,
                     "#ffffff", 0.5))
    m.append(_글(폭 - 8, 높이 - 8, f"{W:.0f} × {H:.0f} µm", 7.4, 흐림, "end"))
    if 제목:
        m.append(_글(폭 / 2, 18, 제목, 11.5, 먹, "middle", 굵게=True))
    return svg(폭, 높이, "".join(m), 제목)
