# -*- coding: utf-8 -*-
"""구현 흐름의 그림들 -- T17~T22 가 쓰는 그림을 여기 모은다.

사용자(2026-09-20): *"각각 다이어그램 처럼 설명해줘. 모든 내용 저런 사진 써서."*
붙여 준 강의 화면의 그림들 -- 플로어플랜(파워링·스트라이프·코너셀·IO필러),
RTL→합성→PD→레이아웃→타이밍수렴 고리, 클럭트리 대 클럭메시, CGIC 와 그 파형,
펄스 동기화기, 스캔 압축, ATE, 하이브리드 BIST, UVM 테스트벤치 -- 를 이 책의
그림으로 짓는다.

`sch.py` 에 안 넣고 따로 두는 까닭: sch.py 는 소자·회로 기호를 들고 있고
여기는 **시스템·흐름 블록도**다.  섞으면 둘 다 안 읽힌다.

배선을 손으로 하면 빠뜨린다 -- sch.py 의 그 교훈 그대로, 좌표는 전부 한 자리에
모아 두고 그림마다 함수 하나가 책임진다.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sch
from sch import svg, 선, 글, 상자, 점, 게이트, 파형, 먹, 회, 빨, 파, 초

연 = "#eef4fb"      # 옅은 파랑 채움
연초 = "#eaf5ee"
연빨 = "#fbeeee"
연노 = "#fdf6e3"
보 = "#7b4bbf"      # 전원 스트라이프(강의 화면의 보라)


def _화살(x1, y1, x2, y2, 색=먹, 굵기=1.6, 점선=None):
    """끝에 삼각형이 달린 선.  방향이 없는 블록도는 읽을 수 없다."""
    import math
    o = 선((x1, y1), (x2, y2), 색=색, 굵기=굵기, 점선=점선)
    a = math.atan2(y2 - y1, x2 - x1)
    L, W = 7.0, 3.6
    p1 = (x2, y2)
    p2 = (x2 - L * math.cos(a) + W * math.sin(a),
          y2 - L * math.sin(a) - W * math.cos(a))
    p3 = (x2 - L * math.cos(a) - W * math.sin(a),
          y2 - L * math.sin(a) + W * math.cos(a))
    return o + (f'<path d="M{p1[0]:.1f},{p1[1]:.1f} L{p2[0]:.1f},{p2[1]:.1f} '
                f'L{p3[0]:.1f},{p3[1]:.1f} Z" fill="{색}"/>')


def _꺾쇠(pts, 색=먹, 굵기=1.6, 점선=None):
    """여러 점을 잇고 마지막 토막에만 화살촉을 단다."""
    o = ""
    for a, b in zip(pts, pts[1:-1]):
        o += 선(a, b, 색=색, 굵기=굵기, 점선=점선)
    o += _화살(*pts[-2], *pts[-1], 색=색, 굵기=굵기, 점선=점선)
    return o


def _라벨선(x1, y1, x2, y2, 글자, 색=회):
    """바깥에서 그림 안을 가리키는 지시선 -- 강의 화면의 그 꼴."""
    return (선((x1, y1), (x2, y2), 색=색, 굵기=1.0)
            + f'<path d="M{x1},{y1} l6,-3 l0,6 Z" fill="{색}"/>'
            + 글(x2 + 5, y2 + 4, 글자, 크기=10, 색=먹))


# ===========================================================================
# 1. 플로어플랜 -- 강의 화면의 그 그림 (코너셀 · 파워링 · 스트라이프 · IO필러)
# ===========================================================================
def 플로어플랜():
    W, H = 560, 430
    L, T = 24, 18                      # 다이 왼쪽 위
    D = 330                            # 다이 한 변
    패드 = 26                          # 패드 링 두께
    o = ""

    # --- 다이 테두리
    o += 상자(L, T, D, D, 채움="#fff")

    # --- 코너 셀 넷
    for cx, cy in ((L, T), (L + D - 패드, T), (L, T + D - 패드),
                   (L + D - 패드, T + D - 패드)):
        o += 상자(cx, cy, 패드, 패드, 채움="#cfe0f2")

    # --- 패드 링: 패드(진한 칸)와 IO 필러(옅은 칸)를 번갈아
    칸 = (D - 2 * 패드) / 9.0
    for k in range(9):
        진 = (k % 2 == 0)
        c = "#d7e8f7" if 진 else "#ececec"
        x = L + 패드 + k * 칸
        o += 상자(x, T, 칸, 패드, 채움=c)                          # 위
        o += 상자(x, T + D - 패드, 칸, 패드, 채움=c)                # 아래
        y = T + 패드 + k * 칸
        o += 상자(L, y, 패드, 칸, 채움=c)                          # 왼쪽
        o += 상자(L + D - 패드, y, 패드, 칸, 채움=c)                # 오른쪽

    # --- 파워 링 두 겹 (VDD / VSS)
    for i, off in enumerate((패드 + 10, 패드 + 20)):
        s = L + off
        e = D - 2 * off
        o += f'<rect x="{s}" y="{T+off}" width="{e}" height="{e}" fill="none" ' \
             f'stroke="{먹}" stroke-width="3"/>'

    # --- 코어 영역
    코 = 패드 + 30
    코변 = D - 2 * 코
    o += 상자(L + 코, T + 코, 코변, 코변, 채움=연초)

    # --- 파워 스트라이프: 가로 5줄 + 세로 5줄, 링에서 링까지
    링s, 링e = L + 패드 + 10, L + D - 패드 - 10
    for k in range(5):
        y = T + 코 + 코변 * (k + 0.5) / 5
        o += 선((링s, y), (링e, y), 색=보, 굵기=5)
        x = L + 코 + 코변 * (k + 0.5) / 5
        o += 선((x, T + 패드 + 10), (x, T + D - 패드 - 10), 색=보, 굵기=3)

    # --- 표준셀 행 (코어 안, 아주 옅게) -- 배치가 이 위에 앉는다
    for k in range(12):
        y = T + 코 + 코변 * (k + 0.5) / 12
        o += 선((L + 코 + 3, y), (L + 코 + 코변 - 3, y), 색="#b9d6c4", 굵기=1,
                점선="2,3")

    # --- 지시선
    x끝 = L + D + 14
    o += _라벨선(L + 패드 / 2, T + 패드 / 2, x끝, T + 26, "Corner cell")
    o += _라벨선(L + 패드 + 12, T + 패드 + 15, x끝, T + 60, "Power Rings")
    o += _라벨선(L + 코 + 코변 * 0.3, T + 코 + 코변 * 0.1, x끝, T + 96,
                 "Power Stripes")
    o += _라벨선(L + 코 + 코변 * 0.6, T + 코 + 코변 * 0.55, x끝, T + 132,
                 "Core Area")
    o += _라벨선(L + 코 + 코변 * 0.2, T + 코 + 코변 * 0.8, x끝, T + 168,
                 "standard-cell rows")
    o += _라벨선(L + D - 패드 / 2, T + D * 0.62, x끝, T + 204, "I/O Pad")
    o += _라벨선(L + D - 패드 / 2, T + D * 0.74, x끝, T + 240, "I/O Filler")

    # --- 아래 설명 한 줄
    o += 글(L, T + D + 26,
            "Special route builds rings and stripes BEFORE any signal is routed —",
            크기=10, 색=회)
    o += 글(L, T + D + 40,
            "the tracks they take are gone, and the router fits into what is left.",
            크기=10, 색=회)
    return svg(W, H, o)


# ===========================================================================
# 2. 구현 흐름 고리 -- RTL → 합성 → 넷리스트 → PD → 레이아웃 → 타이밍 수렴
# ===========================================================================
def 구현흐름고리():
    W, H = 640, 286
    y = 96
    bw, bh, gap = 92, 44, 26
    이름 = ["RTL", "Logic\nSynthesis", "Netlist", "Physical\nDesign",
          "Layout", "Timing\nClosure"]
    채움 = [연노, "#e8e8e8", 연, "#e8e8e8", 연, 연초]
    o = ""
    x = 18
    자리 = []
    for n, c in zip(이름, 채움):
        o += 상자(x, y, bw, bh, n, 채움=c)
        자리.append(x)
        x += bw + gap
    for a in 자리[:-1]:
        o += _화살(a + bw, y + bh / 2, a + bw + gap - 2, y + bh / 2)

    # STA 가 보는 두 자리 (넷리스트 · 레이아웃)
    o += 상자(자리[1] + 20, y + 96, 240, 34, "Static Timing Analysis (STA)",
              채움="#e8e8e8")
    for i in (2, 4):
        o += 선((자리[i] + bw / 2, y + bh), (자리[i] + bw / 2, y + 96), 색=회,
                굵기=1.3, 점선="4,3")
        o += _화살(자리[i] + bw / 2, y + 96, 자리[i] + bw / 2, y + bh + 4,
                   색=회, 굵기=1.3, 점선="4,3")

    # 되돌이 고리 -- 뒤에서 앞으로
    o += _꺾쇠([(자리[4] + bw / 2, y), (자리[4] + bw / 2, y - 46),
                (자리[0] + bw / 2, y - 46), (자리[0] + bw / 2, y - 4)],
               색=빨, 굵기=1.6)
    o += 글((자리[0] + 자리[4]) / 2 + bw / 2, y - 52,
            "a loop that closes HERE costs every stage before it (T17.3)",
            맞춤="middle", 크기=10, 색=빨)
    o += _꺾쇠([(자리[3] + bw / 2, y), (자리[3] + bw / 2, y - 22),
                (자리[1] + bw / 2, y - 22), (자리[1] + bw / 2, y - 4)],
               색="#e08a2e", 굵기=1.4)
    o += 글(자리[1] + bw + 6, y - 26, "re-synthesise", 크기=9.5, 색="#e08a2e")

    o += 글(18, y + 158,
            "Each stage removes a degree of freedom. The information each stage "
            "needs about its successor does not exist yet —", 크기=10, 색=회)
    o += 글(18, y + 172,
            "so every stage estimates the next one, and the estimate's drift is "
            "what decides how many times you go round.", 크기=10, 색=회)
    return svg(W, H, o)


# ===========================================================================
# 3. 클럭 트리 대 클럭 메시
# ===========================================================================
def 클럭트리대메시():
    W, H = 620, 300
    o = ""

    def 삼각(x, y, 색=먹, 채움="#fff", s=7):
        return (f'<path d="M{x-s},{y-s} L{x+s},{y-s} L{x},{y+s} Z" '
                f'fill="{채움}" stroke="{색}" stroke-width="1.4"/>')

    # --- 왼쪽: 트리
    o += 글(140, 22, "Clock Tree", 맞춤="middle", 크기=13, 굵게=True)
    뿌리 = (140, 44)
    o += 삼각(*뿌리, 채움="#f4d7d7")
    단1 = [(80, 96), (200, 96)]
    for p in 단1:
        o += 선((뿌리[0], 뿌리[1] + 7), (뿌리[0], 70), 색=파)
        o += 선((뿌리[0], 70), (p[0], 70), 색=파)
        o += 선((p[0], 70), (p[0], p[1] - 7), 색=파)
        o += 삼각(*p, 채움="#fde8cf")
    잎 = []
    for p in 단1:
        for dx in (-32, 32):
            q = (p[0] + dx, 158)
            o += 선((p[0], p[1] + 7), (p[0], 128), 색=파)
            o += 선((p[0], 128), (q[0], 128), 색=파)
            o += 선((q[0], 128), (q[0], q[1] - 7), 색=파)
            o += 삼각(*q, 채움="#f4d7d7")
            잎.append(q)
    for q in 잎:
        o += 선((q[0], q[1] + 7), (q[0], 186), 색=파)
        o += 상자(q[0] - 9, 186, 18, 18, 채움="#dbe7f5")

    # 잎마다 조금씩 다른 도착 -- 스큐
    o += 선((잎[0][0], 214), (잎[-1][0], 214), 색=회, 굵기=1)
    for i, q in enumerate(잎):
        d = (0, 3, 5, 9)[i]
        o += 선((q[0], 210), (q[0], 218 + d), 색=빨, 굵기=2)
    o += 글(140, 240, "arrivals differ → skew", 맞춤="middle", 크기=10, 색=빨)

    # --- 오른쪽: 메시
    o += 글(450, 22, "Clock Mesh", 맞춤="middle", 크기=13, 굵게=True)
    o += 삼각(450, 44, 채움="#f4d7d7")
    for dx in (-60, 60):
        o += 선((450, 51), (450, 70), 색=파)
        o += 선((450, 70), (450 + dx, 70), 색=파)
        o += 선((450 + dx, 70), (450 + dx, 89), 색=파)
        o += 삼각(450 + dx, 96, 채움="#fde8cf")
    # 격자
    for k in range(5):
        x = 372 + k * 39
        o += 선((x, 120), (x, 196), 색=파, 굵기=2.2)
    for k in range(3):
        y = 120 + k * 38
        o += 선((372, y), (528, y), 색=파, 굵기=2.2)
    for dx in (-60, 60):
        o += 선((450 + dx, 103), (450 + dx, 120), 색=파)
    for k in range(4):
        o += 상자(378 + k * 39, 202, 18, 18, 채움="#dbe7f5")
        o += 선((387 + k * 39, 196), (387 + k * 39, 202), 색=파)
    o += 선((378, 232), (528, 232), 색=회, 굵기=1)
    for k in range(4):
        o += 선((387 + k * 39, 228), (387 + k * 39, 237), 색=초, 굵기=2)
    o += 글(450, 258, "the mesh shorts the leaves → variation averages",
            맞춤="middle", 크기=10, 색=초)

    o += 선((300, 30), (300, 270), 색="#ddd", 굵기=1, 점선="4,4")
    o += 글(140, 276, "lowest power · useful skew possible · latency grows "
            "with depth", 맞춤="middle", 크기=9.5, 색=회)
    o += 글(450, 276, "lowest skew · highest power · no unique path to analyse",
            맞춤="middle", 크기=9.5, 색=회)
    return svg(W, H, o)


# ===========================================================================
# 4. OCV 가 삽입지연을 스큐로 바꾼다 -- 강의 화면의 그 산술
# ===========================================================================
def OCV스큐():
    W, H = 600, 250
    o = ""
    o += 글(300, 20, "Why insertion delay costs skew", 맞춤="middle", 크기=13,
            굵게=True)
    뿌리x, y0 = 60, 58
    갈림x = 330
    o += 글(뿌리x - 34, y0 + 5, "clock", 크기=10)
    o += 선((뿌리x, y0), (갈림x, y0), 색=파, 굵기=3)
    o += 글((뿌리x + 갈림x) / 2, y0 - 8, "common path — 98 % of the latency",
            맞춤="middle", 크기=10)
    o += 점(갈림x, y0, 3.2, 파)
    # 두 갈래
    o += 선((갈림x, y0), (갈림x + 40, y0 - 26), 색=파, 굵기=2.4)
    o += 선((갈림x + 40, y0 - 26), (520, y0 - 26), 색=파, 굵기=2.4)
    o += 선((갈림x, y0), (갈림x + 40, y0 + 26), 색=파, 굵기=2.4)
    o += 선((갈림x + 40, y0 + 26), (520, y0 + 26), 색=파, 굵기=2.4)
    o += 상자(520, y0 - 42, 46, 32, "launch", 채움="#dbe7f5")
    o += 상자(520, y0 + 10, 46, 32, "capture", 채움="#dbe7f5")
    o += 글(354, y0 - 34, "derated LATE  × 1.07", 크기=10, 색=빨)
    o += 글(354, y0 + 48, "derated EARLY × 0.93", 크기=10, 색=초)

    # 계산
    바 = 150
    o += 글(60, 바, "effective skew", 크기=11, 굵게=True)
    o += 글(60, 바 + 20, "= 1.00 × 1.07  −  0.98 × 0.93", 크기=12)
    o += 글(60, 바 + 40, "= 1.070 − 0.9114", 크기=12)
    o += 글(60, 바 + 60, "= 15.86 % of the insertion delay", 크기=13,
            굵게=True, 색=빨)
    o += 글(330, 바 + 20,
            "The common part does NOT cancel:", 크기=10, 색=회)
    o += 글(330, 바 + 34,
            "the two derates applied to it differ.", 크기=10, 색=회)
    o += 글(330, 바 + 52,
            "So a perfectly balanced tree still", 크기=10, 색=회)
    o += 글(330, 바 + 66,
            "spends 15.9 % of its latency on skew —", 크기=10, 색=회)
    o += 글(330, 바 + 80,
            "which is why CTS targets latency too.", 크기=10, 색=회)
    return svg(W, H, o)


# ===========================================================================
# 5. 클럭 게이팅 (CGIC) -- 래치 + AND, 그리고 파형
# ===========================================================================
def 클럭게이팅():
    회로 = ""
    # 래치
    회로 += 상자(96, 40, 62, 46, "Latch", 채움="#fde8cf")
    회로 += 글(70, 52, "EN", 맞춤="end", 크기=11)
    회로 += _화살(74, 48, 96, 48)
    회로 += 글(70, 108, "CLK", 맞춤="end", 크기=11, 색=파)
    회로 += 선((74, 104), (84, 104), 색=파)
    회로 += 선((84, 104), (84, 76), 색=파)
    회로 += _화살(84, 76, 96, 76, 색=파)      # 래치는 CLK 이 낮을 때 열린다
    회로 += 글(100, 96, "open while CLK low", 크기=9, 색=회)
    # AND
    회로 += 게이트("AND", 200, 46, 40, 34)
    회로 += _화살(158, 56, 200, 56)
    회로 += 선((84, 104), (180, 104), 색=파)
    회로 += 선((180, 104), (180, 74), 색=파)
    회로 += _화살(180, 74, 200, 74, 색=파)
    회로 += _화살(240, 63, 286, 63, 색=파, 굵기=2)
    회로 += 글(290, 59, "Gated Clock", 크기=11, 색=파)
    회로 += 상자(290, 74, 84, 40, "Set of\nRegisters", 채움="#dbe7f5")
    회로 += 선((330, 70), (330, 74), 색=파)
    회로 += 상자(66, 132, 320, 34,
                "CGIC — integrated clock-gating cell", 채움=연, 점선="5,4")
    윗 = svg(400, 180, 회로)

    아래 = 파형([("CLK", "^_^_^_^_^_"),
               ("EN", "__^^^^____"),
               ("Latch out", "___^^^^___"),
               ("Gated Clock", "___^_^_^__")],
              폭=34, 높이=20, 간격=12, x0=92)
    설명 = svg(560, 58, (
        글(8, 16, "Without the latch, EN changing while CLK is high produces a "
          "GLITCH:", 크기=10.5, 색=빨)
        + 글(8, 32, "a partial pulse, long enough for a flop to see and short "
             "enough to violate", 크기=10.5, 색=회)
        + 글(8, 46, "its minimum pulse width. The latch confines EN changes to "
             "the low phase.", 크기=10.5, 색=회)))
    return 윗 + 아래 + 설명


# ===========================================================================
# 6. 펄스 동기화기 -- d → q1 → q2 → q3 → XOR → pulse
# ===========================================================================
def 펄스동기화기():
    회로 = ""
    회로 += 글(16, 26, "d", 크기=11)
    회로 += _화살(24, 40, 54, 40)
    x = 54
    이름 = ["q1", "q2", "q3"]
    for i, n in enumerate(이름):
        회로 += sch.플롭(x, 20, 라벨="", w=44, h=50)
        회로 += 글(x + 52, 36, n, 크기=11)
        if i < 2:
            회로 += _화살(x + 44, 40, x + 78, 40)
        x += 78
    회로 += 상자(46, 6, 116, 82, 채움="none", 점선="5,4", 색=회)
    회로 += 글(104, 102, "sync2 — two flops", 맞춤="middle", 크기=10, 색=회)
    # XOR
    회로 += 게이트("XOR", 296, 24, 42, 34)
    회로 += 선((132, 40), (132, 120), 색=먹)          # q2 를 XOR 로
    회로 += 선((132, 120), (284, 120), 색=먹)
    회로 += 선((284, 120), (284, 48), 색=먹)
    회로 += _화살(284, 48, 296, 48)
    회로 += 점(132, 40)
    회로 += _화살(288, 34, 296, 34)
    회로 += 선((254, 40), (288, 40), 색=먹)
    회로 += 선((288, 40), (288, 34), 색=먹)
    회로 += _화살(338, 41, 376, 41, 굵기=2)
    회로 += 글(380, 37, "pulse", 크기=11, 굵게=True)
    회로 += 글(380, 52, "one cycle", 크기=9.5, 색=회)
    회로 += 글(16, 150, "Different input–output levels across one flop "
              "→ exactly one cycle of difference.", 크기=10, 색=회)
    윗 = svg(450, 170, 회로)

    아래 = 파형([("clk", "^_^_^_^_^_^_"),
               ("d", "_^^^^^^^^___"),
               ("q1", "__^^^^^^^^__"),
               ("q2", "___^^^^^^^^_"),
               ("q3", "____^^^^^^^^"),
               ("pulse", "___^____^___")],
              폭=30, 높이=18, 간격=10, x0=62)
    return 윗 + 아래


# ===========================================================================
# 7. 스캔 압축 -- 해제기 → 내부 체인들 → 압축기
# ===========================================================================
def 스캔압축():
    W, H = 600, 260
    o = ""
    o += 글(300, 20, "Scan compression: a few tester channels, many internal "
            "chains", 맞춤="middle", 크기=12, 굵게=True)
    # 왼쪽 테스터 채널
    for k, y in enumerate((70, 110, 150)):
        o += 글(16, y + 4, f"tst_scanin{k+1}", 크기=10)
        o += _화살(92, y, 130, y, 색=빨)
    o += f'<path d="M130,52 L176,76 L176,152 L130,176 Z" fill="{연} ' \
         f'" stroke="{먹}" stroke-width="1.6"/>'
    o += 글(153, 118, "DE-", 맞춤="middle", 크기=10)
    o += 글(153, 130, "COMP", 맞춤="middle", 크기=10)
    # 내부 체인 여섯
    for k in range(6):
        y = 56 + k * 22
        o += _화살(176, y, 214, y, 색=회, 굵기=1.2)
        for j in range(4):
            o += 상자(214 + j * 38, y - 8, 30, 16, 채움="#dbe7f5")
            if j < 3:
                o += 선((244 + j * 38, y), (252 + j * 38, y), 색=회, 굵기=1.2)
        o += _화살(366, y, 400, y, 색=회, 굵기=1.2)
    o += 글(290, 42, "internal scan chains (short)", 맞춤="middle", 크기=10,
            색=회)
    # 압축기
    o += f'<path d="M400,52 L446,76 L446,152 L400,176 Z" fill="{연초}" ' \
         f'stroke="{먹}" stroke-width="1.6"/>'
    o += 글(423, 118, "COMP", 맞춤="middle", 크기=10)
    for k, y in enumerate((70, 110, 150)):
        o += _화살(446, y, 500, y, 색=빨)
        o += 글(506, y + 4, f"scanout{k+1}", 크기=10)

    o += 글(16, 208, "Shift length = flops / (chains × compression). The tester "
            "sees 3 channels; the die has 6 chains.", 크기=10, 색=회)
    o += 글(16, 224, "Test time AND pattern memory both fall in the same "
            "proportion — and memory is often the binding one.", 크기=10, 색=회)
    o += 글(16, 240, "lab: python3 lab/run.py --stage dft   (measures both on "
            "the real netlist)", 크기=10, 색=초)
    return svg(W, H, o)


# ===========================================================================
# 8. ATE -- 테스트 프로그램 · 패턴 메모리 · 핀 일렉트로닉스 · DUT
# ===========================================================================
def ATE구조():
    W, H = 580, 300
    o = ""
    o += 상자(330, 24, 120, 54, "Test\nProgram", 채움=연노)
    o += 상자(190, 24, 110, 54, "Pattern\nMemory", 채움="#fff")
    o += _화살(330, 50, 302, 50)
    o += 글(196, 96, "vectors, per channel", 크기=9.5, 색=회)

    # 프로그래머블 클럭 발생기
    o += 상자(40, 24, 128, 54, "Programmable\nClock Generator", 채움="#fff")
    o += f'<circle cx="104" cy="104" r="17" fill="#fff" stroke="{먹}" ' \
         f'stroke-width="1.5"/>'
    o += 선((96, 108), (96, 100), 색=파)
    o += 선((96, 100), (104, 100), 색=파)
    o += 선((104, 100), (104, 108), 색=파)
    o += 선((104, 108), (112, 108), 색=파)
    o += 선((104, 78), (104, 87), 색=먹)

    # 핀 일렉트로닉스 카드 (겹친 카드 넷)
    for k in range(4):
        o += 상자(36 + k * 7, 150 + k * 7, 96, 66, 채움="#fff")
    o += 게이트("INV", 52, 168, 30, 22)
    o += 게이트("AND", 52, 196, 30, 22)
    o += 글(24, 236, "Pin Electronics Cards", 크기=10)
    for k in range(4):
        o += 상자(420 + k * 7, 150 + k * 7, 96, 66, 채움="#fff")
    o += 게이트("INV", 452, 168, 30, 22)
    o += 게이트("AND", 452, 196, 30, 22)

    # 버스: 패턴 메모리 → 핀 카드 양쪽
    o += 선((245, 78), (245, 128), 색=회, 굵기=6)
    o += 선((120, 128), (470, 128), 색=회, 굵기=6)
    o += _화살(120, 128, 120, 150, 색=회, 굵기=6)
    o += _화살(470, 128, 470, 150, 색=회, 굵기=6)
    o += 선((104, 121), (104, 128), 색=파)
    o += 점(245, 128, 3.5, 회)

    # DUT
    o += 상자(210, 196, 156, 40, "", 채움="#8f8f8f")
    for k in range(9):
        x = 216 + k * 17
        o += 선((x, 236), (x, 248), 색="#555", 굵기=2.4)
    o += 글(288, 262, "DUT Pins", 맞춤="middle", 크기=11, 굵게=True)
    for k in range(3):
        y = 202 + k * 11
        o += _화살(196, y, 210, y, 색=먹, 굵기=1.2)
        o += _화살(380, y, 366, y, 색=먹, 굵기=1.2)

    o += 글(16, 288, "Cost per die = (test time) × (tester $/second ÷ sites). "
            "Everything DFT does is an attack on one of those three.",
            크기=10, 색=회)
    return svg(W, H, o)


# ===========================================================================
# 9. 하이브리드 BIST -- 컨트롤러 + MBIST + LBIST + eNVM
# ===========================================================================
def 하이브리드BIST():
    W, H = 560, 280
    o = ""
    o += 상자(14, 14, 532, 250, "", 채움="#fff", 점선="6,4", 색=회)
    o += 글(24, 32, "Hybrid BIST", 크기=12, 굵게=True)

    o += 상자(40, 60, 108, 56, "BIST\nController", 채움=연노)
    for k, n in enumerate(("BIST_MODE", "START", "CLK", "DONE", "ERROR")):
        y = 56 + k * 16
        if n in ("DONE", "ERROR"):
            o += _화살(40, y, 20, y)
            o += 글(16, y + 4, n, 맞춤="end", 크기=9.5)
        else:
            o += _화살(16, y, 40, y)
            o += 글(12, y + 4, n, 맞춤="end", 크기=9.5)
    o += 상자(40, 150, 108, 44, "eNVM\ntest pattern", 채움="#fff")
    o += 선((94, 116), (94, 150), 색=먹)
    o += 글(40, 214, "LBIST", 크기=11, 굵게=True)
    o += 상자(26, 132, 136, 100, "", 채움="none", 색=회, 점선="4,3")

    # MBIST 쪽 상자 넷
    o += 상자(200, 42, 336, 200, "", 채움="#f4f4f4", 점선="5,4", 색=회)
    o += 글(524, 58, "MBIST", 맞춤="end", 크기=11, 굵게=True)
    for k, n in enumerate(("Memory Data Generator", "Address Generator",
                           "Comparator", "Test Data Generator")):
        y = 68 + k * 42
        o += 상자(216, y, 246, 32, n, 채움="#fff")
        o += _화살(148, 88, 216, y + 16, 색=회, 굵기=1.2)
        o += _화살(462, y + 16, 500, y + 16, 색=회, 굵기=1.2)

    o += 글(24, 258, "An embedded memory has no pins. MBIST is not an "
            "optimisation of external memory test — it is the only way to do "
            "it at all.", 크기=10, 색=회)
    return svg(W, H, o)


# ===========================================================================
# 10. UVM 테스트벤치 -- 강의 화면의 그 중첩 상자들
# ===========================================================================
def UVM테스트벤치():
    W, H = 640, 470
    o = ""
    o += 상자(10, 10, 620, 400, "", 채움="#f2f2f2")
    o += 글(320, 28, "Test bench", 맞춤="middle", 크기=12, 굵게=True)
    o += 상자(24, 36, 592, 292, "", 채움="#dfe8f5")
    o += 글(320, 54, "Test", 맞춤="middle", 크기=12, 굵게=True)
    o += 상자(38, 62, 564, 254, "", 채움="#ece2f6")
    o += 글(320, 80, "Verification Environment", 맞춤="middle", 크기=11.5,
            굵게=True)

    for i, x0 in ((1, 52), (2, 372)):
        o += 상자(x0, 92, 212, 206, "", 채움="#dbe7f5")
        o += 글(x0 + 106, 110, f"Agent {i}", 맞춤="middle", 크기=11, 굵게=True)
        o += 상자(x0 + 148, 96, 52, 22, "CFG", 채움="#fff")
        o += 상자(x0 + 12, 120, 88, 26, "Sequencer", 채움="#fff")
        o += 상자(x0 + 12, 158, 88, 46, "Driver", 채움="#f6c99b")
        o += 상자(x0 + 110, 158, 88, 46, "Monitor", 채움="#fbe6d2")
        o += 상자(x0 + 12, 216, 60, 30, "Virtual\nInterface", 채움="#bcd4ef")
        o += 상자(x0 + 110, 216, 60, 30, "Virtual\nInterface", 채움="#bcd4ef")
        o += _화살(x0 + 56, 146, x0 + 56, 158)
        o += _화살(x0 + 42, 204, x0 + 42, 216)
        o += _화살(x0 + 140, 216, x0 + 140, 204)
        # 시퀀스는 바깥(Test)에서 들어온다
        o += 상자(x0 + 6, 40, 96, 22, "Sequence", 채움="#e9f0d8")
        o += _화살(x0 + 54, 62, x0 + 54, 120)

    # 스코어보드 · 커버리지
    o += 상자(276, 118, 108, 40, "Scoreboard", 채움="#dff0dc")
    o += 상자(268, 172, 124, 44, "Functional\nCoverage", 채움="#dff0dc")
    o += 상자(300, 232, 56, 24, "CFG", 채움="#fff")
    for x0, 쪽 in ((52, 1), (372, -1)):
        o += _화살(x0 + 198 if 쪽 > 0 else x0 + 110, 172,
                   276 if 쪽 > 0 else 392, 138)
        o += _화살(x0 + 198 if 쪽 > 0 else x0 + 110, 188,
                   268 if 쪽 > 0 else 392, 192)

    # 인터페이스와 DUT
    for x0 in (60, 380):
        o += 상자(x0, 334, 196, 26, "Interface", 채움="#c9c9c9")
        o += 선((x0 + 70, 316), (x0 + 70, 334), 색=먹, 점선="3,3")
        o += 선((x0 + 126, 316), (x0 + 126, 334), 색=먹, 점선="3,3")
        o += _화살(x0 + 98, 360, x0 + 98, 372)
    o += 상자(60, 372, 516, 30, "DUT", 채움="#f5d3d3")

    o += 글(10, 428, "The upper path drives; the lower path observes. They are "
            "deliberately NOT connected to each other —", 크기=10, 색=회)
    o += 글(10, 442, "a monitor that trusts the driver's intent cannot detect a "
            "driver that drove the wrong thing.", 크기=10, 색=회)
    o += 글(10, 458, "Coverage says you TRIED it. Only the scoreboard says it "
            "WORKED.", 크기=10.5, 색=빨)
    return svg(W, H, o)


# ===========================================================================
# 11. 표준셀 행과 자리(SITE)
# ===========================================================================
def 표준셀행():
    W, H = 580, 250
    o = ""
    o += 글(10, 20, "SITE coreSite  CLASS CORE ;  SIZE 0.660 BY 5.040 ;",
            크기=11.5, 굵게=True)
    y0, 행h, 자리w = 40, 42, 13
    for r in range(4):
        y = y0 + r * 행h
        # 전원 레일 위아래
        o += 선((20, y), (470, y), 색=빨, 굵기=4)
        o += 선((20, y + 행h - 6), (470, y + 행h - 6), 색=초, 굵기=4)
        # 자리 격자
        for k in range(34):
            o += 선((20 + k * 자리w, y + 3), (20 + k * 자리w, y + 행h - 9),
                    색="#e0e0e0", 굵기=1)
    o += 글(478, y0 + 4, "VDD rail", 크기=10, 색=빨)
    o += 글(478, y0 + 행h - 2, "VSS rail", 크기=10, 색=초)

    # 셀 몇 개 -- 자리의 정수배로
    놓기 = [(0, 0, 2, "INV"), (0, 2, 4, "NAND2"), (0, 6, 9, "DFF"),
          (1, 1, 4, "NAND2"), (1, 5, 9, "XOR2"), (1, 14, 2, "INV"),
          (2, 0, 7, "AOI21"), (2, 7, 5, "NOR2"), (2, 12, 8, "DFF"),
          (3, 3, 4, "AND2"), (3, 7, 7, "MUX2")]
    for r, s, w, n in 놓기:
        y = y0 + r * 행h
        o += 상자(20 + s * 자리w, y + 3, w * 자리w, 행h - 12, n,
                  채움="#dbe7f5")

    o += 선((20, 214), (20 + 자리w, 214), 색=먹, 굵기=1.4)
    o += 선((20, 210), (20, 218), 색=먹, 굵기=1.4)
    o += 선((20 + 자리w, 210), (20 + 자리w, 218), 색=먹, 굵기=1.4)
    o += 글(20 + 자리w + 6, 218, "one SITE = 0.660 µm", 크기=10)
    o += 글(300, 218, "row height 5.040 µm = 9 routing tracks", 크기=10, 색=회)
    o += 글(10, 240, "Digital layout is a TILING, not a free placement. "
            "Legalisation is the projection back onto this grid.",
            크기=10, 색=회)
    return svg(W, H, o)


# ===========================================================================
# 12. 전역 배선 → 상세 배선 → 탐색 수리
# ===========================================================================
def 배선세걸음():
    W, H = 620, 270
    o = ""
    칸, 격 = 26, 8

    def 격자(x0, y0, 혼잡=None):
        s = ""
        for i in range(격):
            for j in range(격):
                c = "#fff"
                if 혼잡:
                    v = 혼잡(i, j)
                    if v > 1.0:
                        c = "#f3c9c9"
                    elif v > 0.8:
                        c = "#fbe8cf"
                    elif v > 0.5:
                        c = "#eaf3ea"
                s += 상자(x0 + i * 칸, y0 + j * 칸, 칸, 칸, 채움=c, 색="#ddd")
        return s

    import math
    o += 글(16, 22, "1. Global route", 크기=11.5, 굵게=True)
    o += 격자(16, 32, lambda i, j: 1.2 * math.exp(
        -((i - 4) ** 2 + (j - 3) ** 2) / 6.0) + 0.45)
    for pts in ([(1, 6), (1, 3), (5, 3)], [(0, 1), (4, 1), (4, 5)],
                [(6, 7), (6, 4), (2, 4)]):
        p = [(16 + i * 칸 + 칸 / 2, 32 + j * 칸 + 칸 / 2) for i, j in pts]
        o += 선(*p, 색=파, 굵기=2)
    o += 글(16, 32 + 격 * 칸 + 18, "per-gcell capacity, not geometry",
            크기=9.5, 색=회)

    o += 글(226, 22, "2. Detail route", 크기=11.5, 굵게=True)
    x0 = 226
    for k in range(10):
        o += 선((x0 + 6, 38 + k * 18), (x0 + 190, 38 + k * 18), 색="#e6e6e6",
                굵기=1)
    for y, a, b in ((56, 10, 120), (92, 40, 170), (128, 6, 96),
                    (164, 70, 186)):
        o += 선((x0 + a, y), (x0 + b, y), 색=파, 굵기=2.4)
        o += 선((x0 + b, y), (x0 + b, y + 18), 색=파, 굵기=2.4)
        o += 상자(x0 + b - 3, y + 15, 6, 6, 채움=빨, 색=빨)
    o += 글(x0, 32 + 격 * 칸 + 18, "real tracks, real vias, every DRC rule",
            크기=9.5, 색=회)

    o += 글(444, 22, "3. Search and repair", 크기=11.5, 굵게=True)
    바 = [4200, 1890, 850, 383, 172]
    for k, v in enumerate(바):
        h = 100 * v / 바[0]
        o += 상자(452 + k * 30, 150 - h, 22, h, 채움="#f3c9c9", 색=빨)
        o += 글(463 + k * 30, 164, str(k), 맞춤="middle", 크기=9, 색=회)
    o += 글(452, 180, "violations per pass", 크기=9.5, 색=회)
    o += 글(452, 196, "ratio → 1 means the loop", 크기=9.5, 색=빨)
    o += 글(452, 210, "is MOVING violations,", 크기=9.5, 색=빨)
    o += 글(452, 224, "not repairing them.", 크기=9.5, 색=빨)

    o += 글(16, 258, "Global routing is a flow problem on a small graph and is "
            "solved nearly optimally; detail routing is a geometry problem far "
            "too large to search.", 크기=10, 색=회)
    return svg(W, H, o)


# ===========================================================================
# 13. 코너의 곱셈 -- 축이 곱해진다는 것을 그림으로
# ===========================================================================
def 코너곱셈():
    W, H = 600, 250
    o = ""
    축 = [("Process", 3, ["ss", "tt", "ff"]),
         ("Voltage", 2, ["nom", "low"]),
         ("Temperature", 3, ["−40", "25", "125"]),
         ("RC", 3, ["cmin", "cworst", "rcworst"]),
         ("Mode", 4, ["func", "shift", "capture", "retention"])]
    x = 16
    곱 = 1
    for 이름, n, 값들 in 축:
        o += 글(x, 28, 이름, 크기=11, 굵게=True)
        for k, v in enumerate(값들):
            o += 상자(x, 38 + k * 26, 84, 20, v, 채움=연)
        곱 *= n
        x += 100
        if x < 500:
            o += 글(x - 12, 62, "×", 맞춤="middle", 크기=16, 색=빨)
    o += 글(16, 176, f"3 × 2 × 3 × 3 × 4  =  {곱} corner-mode combinations",
            크기=13, 굵게=True)
    o += 글(16, 198, f"× 2 h of STA each  =  {곱*2/24:.0f} days of compute",
            크기=12, 색=빨)
    o += 글(16, 222, "and a single ECO throws all of it away. That is T17.3's "
            "loop cost in its most expensive form.", 크기=10, 색=회)
    return svg(W, H, o)


_목록 = {
    "플로어플랜": 플로어플랜, "구현흐름고리": 구현흐름고리,
    "클럭트리대메시": 클럭트리대메시, "OCV스큐": OCV스큐,
    "클럭게이팅": 클럭게이팅, "펄스동기화기": 펄스동기화기,
    "스캔압축": 스캔압축, "ATE구조": ATE구조, "하이브리드BIST": 하이브리드BIST,
    "UVM테스트벤치": UVM테스트벤치, "표준셀행": 표준셀행,
    "배선세걸음": 배선세걸음, "코너곱셈": 코너곱셈,
}


if __name__ == "__main__":
    몸 = ""
    for 이름, f in _목록.items():
        몸 += f"<h2>{이름}</h2>\n<div>{f()}</div>\n"
    길 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "원문", "그림맛보기.html")
    os.makedirs(os.path.dirname(길), exist_ok=True)
    open(길, "w", encoding="utf-8").write(
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<style>body{font-family:system-ui;max-width:860px;margin:2em auto}'
        'h2{margin-top:2em;border-top:2px solid #333;padding-top:.6em}</style>'
        '</head><body><h1>구현 흐름 그림 맛보기</h1>' + 몸 + '</body></html>')
    print(f"{len(_목록)}개 그림 -> {길}")
