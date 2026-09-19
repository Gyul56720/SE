# -*- coding: utf-8 -*-
"""AES 교안 전용 선화 다이어그램 (자체 SVG, 래스터 없음)."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from figs import svg, box, txt, arr, line, poly


def 삼각형():
    """디자인 / 모델링 / DV 의 삼각형."""
    b = []
    b.append(box(40, 30, 175, 52, "디자인 팀", "SystemVerilog / VHDL"))
    b.append(box(365, 30, 175, 52, "모델링 팀", "C / C++ 참조모델"))
    b.append(box(200, 155, 180, 56, "DV 팀", "비교 테스트벤치"))
    b.append(arr(127, 82, 265, 155))
    b.append(arr(452, 82, 320, 155))
    b.append(txt(140, 125, "RTL 트레이스", 9, "middle"))
    b.append(txt(440, 125, "기대값", 9, "middle"))
    b.append(box(200, 245, 180, 40, "불일치 = 버그", None, 10, "#fbeaea"))
    b.append(arr(290, 211, 290, 245))
    b.append(txt(290, 305, "회귀에서 둘이 다르면 그것이 버그다", 9, "middle",
                 'font-style="italic"'))
    return svg(580, 320, "".join(b))


def 라운드():
    """AES 한 라운드의 데이터패스."""
    b = []
    x = 30
    for 이름, 부제 in (("SubBytes", "S-box &times;16"),
                       ("ShiftRows", "배선만"),
                       ("MixColumns", "GF(2^8) 곱"),
                       ("AddRoundKey", "XOR")):
        b.append(box(x, 55, 118, 50, 이름, 부제, 10))
        if x > 30:
            b.append(arr(x - 22, 80, x, 80))
        x += 140
    b.append(arr(0, 80, 30, 80))
    b.append(txt(4, 72, "state", 9))
    b.append(arr(578, 80, 610, 80))
    b.append(box(450, 150, 118, 38, "라운드 키", None, 9, "#eef2f7"))
    b.append(arr(509, 150, 509, 105))
    b.append(txt(305, 200, "라운드 10회(128비트 키). 마지막 라운드는 MixColumns 없음",
                 9, "middle", 'font-style="italic"'))
    b.append(txt(305, 25, "면적은 여기서 갈린다: SubBytes 만 조합논리가 아니다",
                 9, "middle"))
    return svg(620, 215, "".join(b))


def 탑필드():
    """S-box 를 LUT 로 두느냐 탑 필드로 분해하느냐."""
    b = []
    b.append(box(25, 40, 175, 92, "", None, 10, "#f6f8fa"))
    b.append(txt(112, 62, "LUT 방식", 11, "middle", 'font-weight="bold"'))
    b.append(txt(112, 82, "256바이트 표를 그대로", 9, "middle"))
    b.append(txt(112, 98, "작다 &bull; 빠르다", 9, "middle"))
    b.append(txt(112, 118, "전력 부채널에 샌다", 9, "middle", 'fill="#a33"'))

    b.append(box(300, 20, 250, 135, "", None, 10, "#f4eefa"))
    b.append(txt(425, 42, "탑 필드(Canright) 방식", 11, "middle",
                 'font-weight="bold"'))
    b.append(box(320, 55, 210, 26, "GF(2^8) 역원", None, 9))
    b.append(arr(425, 81, 425, 92))
    b.append(box(320, 92, 210, 26, "GF(2^4) 연산으로 분해", None, 9))
    b.append(arr(425, 118, 425, 129))
    b.append(box(320, 129, 210, 22, "GF(2^2) &rarr; 마스킹 가능", None, 9))

    b.append(arr(200, 86, 300, 86))
    b.append(txt(250, 78, "재작성", 9, "middle"))
    b.append(txt(287, 185,
                 "같은 함수 &mdash; 다른 회로. 표는 못 가리고, 산술은 가릴 수 있다",
                 9, "middle", 'font-style="italic"'))
    return svg(575, 200, "".join(b))


def 이중화FSM():
    """긍정/부정 FSM 이중화로 고장주입 막기."""
    b = []
    b.append(box(45, 35, 165, 48, "FSM (정논리)", "aes_..._fsm_p", 10))
    b.append(box(45, 115, 165, 48, "FSM (부논리)", "aes_..._fsm_n", 10))
    b.append(box(300, 75, 150, 48, "상보성 검사", None, 10, "#fbeaea"))
    b.append(arr(210, 59, 300, 90))
    b.append(arr(210, 139, 300, 110))
    b.append(arr(450, 99, 520, 99))
    b.append(txt(524, 95, "경보", 10))
    b.append(txt(255, 195,
                 "고장이 양쪽을 같은 방향으로 뒤집으면 상보성이 깨진다 &mdash; 그때 잡는다",
                 9, "middle", 'font-style="italic"'))
    b.append(txt(255, 212,
                 "합성기가 인버터를 FSM 안으로 밀어 넣으므로 두 벌이 같은 회로가 되지 않는다",
                 9, "middle", 'font-style="italic"'))
    return svg(560, 225, "".join(b))


def 세구현():
    """같은 AES 의 세 구현과 크기."""
    b = []
    자료 = [("C 골든모델", "tiny-AES-c", 573, "#2a7f5f"),
            ("HLS C++", "Vitis aes.hpp", 1011, "#123f6d"),
            ("양산 RTL", "OpenTitan AES", 17254, "#7a4fa3")]
    최대 = 17254
    y = 45
    for 이름, 파일, 줄, 색 in 자료:
        w = max(18, int(430 * 줄 / 최대))
        b.append(f'<rect x="150" y="{y}" width="{w}" height="30" fill="{색}" '
                 f'opacity="0.82"/>')
        b.append(txt(144, y + 20, 이름, 10, "end", 'font-weight="bold"'))
        b.append(txt(156 + w, y + 20, f"{줄:,}줄  ({파일})", 9))
        y += 46
    b.append(txt(300, 190,
                 "같은 표준, 같은 정답. 크기는 30배 차이난다",
                 10, "middle", 'font-style="italic"'))
    b.append(txt(300, 208,
                 "차이는 알고리즘이 아니라 부채널 · 고장주입 · 레지스터맵 · 검증이다",
                 9, "middle"))
    return svg(620, 220, "".join(b))
