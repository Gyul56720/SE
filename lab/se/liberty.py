# -*- coding: utf-8 -*-
"""`.lib` 를 읽는다.

**범용 Liberty 파서가 아니다.**  `mklib.py` 가 낸 꼴만 읽는다 -- 그것이
이 실습이 쓰는 유일한 라이브러리이므로.  범용 파서인 척하면 남의 .lib 를
먹였을 때 조용히 틀린 값을 내놓는다.  그래서 모르는 꼴을 만나면 **터진다.**
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
기본길 = os.path.join(뿌리, "lib", "se10.lib")


@dataclass
class 타이밍:
    관련핀: str
    종류: str                     # "조합" | "클럭Q" | "셋업" | "홀드"
    감: str = ""
    상승: list = field(default_factory=list)      # [[..], ..] 2차원
    하강: list = field(default_factory=list)
    상승천이: list = field(default_factory=list)
    하강천이: list = field(default_factory=list)


@dataclass
class 핀:
    이름: str
    방향: str
    용량: float = 0.0
    함수: str = ""
    클럭: bool = False
    최대부하: float = 0.0
    타이밍들: list = field(default_factory=list)


@dataclass
class 셀:
    이름: str
    면적: float
    핀들: dict = field(default_factory=dict)
    순차: bool = False

    @property
    def 입력핀(self):
        return [p for p in self.핀들.values() if p.방향 == "input"]

    @property
    def 출력핀(self):
        return [p for p in self.핀들.values() if p.방향 == "output"]

    def 자리수(self, 자리폭=0.660, 행높이=5.040):
        return self.면적 / (자리폭 * 행높이)


class 라이브러리:
    def __init__(self, 길=None):
        self.길 = 길 or 기본길
        self.셀들: dict[str, 셀] = {}
        self.축천이: list[float] = []
        self.축부하: list[float] = []
        self.전압 = 1.8
        self._읽기()

    # -- 표 찾기 -----------------------------------------------------------
    def 지연(self, 셀이름, 출력핀, 관련핀, 부하_pF, 천이_ns, 상승=True):
        """보간해서 지연을 낸다 (ns).  축 밖은 **바깥쪽 기울기로 늘린다.**"""
        c = self.셀들[셀이름]
        for t in c.핀들[출력핀].타이밍들:
            if t.관련핀 == 관련핀 and t.종류 in ("조합", "클럭Q"):
                return self._보간(t.상승 if 상승 else t.하강, 천이_ns, 부하_pF)
        raise KeyError(f"{셀이름}.{출력핀} 에 {관련핀} 관련 타이밍이 없다")

    def 천이(self, 셀이름, 출력핀, 관련핀, 부하_pF, 천이_ns, 상승=True):
        c = self.셀들[셀이름]
        for t in c.핀들[출력핀].타이밍들:
            if t.관련핀 == 관련핀 and t.종류 in ("조합", "클럭Q"):
                return self._보간(t.상승천이 if 상승 else t.하강천이,
                                 천이_ns, 부하_pF)
        raise KeyError(f"{셀이름}.{출력핀} 에 {관련핀} 천이표가 없다")

    def 제약(self, 셀이름, 입력핀, 종류):
        """셋업/홀드 (ns).  표가 상수라 축을 안 본다 -- mklib 가 그렇게 낸다."""
        for t in self.셀들[셀이름].핀들[입력핀].타이밍들:
            if t.종류 == 종류:
                return t.상승[0][0]
        raise KeyError(f"{셀이름}.{입력핀} 에 {종류} 제약이 없다")

    def _보간(self, 표, x, y):
        return _2차원보간(self.축천이, self.축부하, 표, x, y)

    # -- 읽기 ---------------------------------------------------------------
    def _읽기(self):
        글 = open(self.길, encoding="utf-8").read()
        글 = re.sub(r"/\*.*?\*/", "", 글, flags=re.S)
        글 = 글.replace("\\\n", " ")

        m = re.search(r'lu_table_template\s*\(dly\)\s*\{(.*?)\}', 글, re.S)
        if not m:
            raise ValueError("dly 표틀이 없다 -- mklib.py 가 낸 파일이 맞나")
        self.축천이 = _수열(re.search(r'index_1\s*\("([^"]+)"\)', m.group(1)))
        self.축부하 = _수열(re.search(r'index_2\s*\("([^"]+)"\)', m.group(1)))

        v = re.search(r'nom_voltage\s*:\s*([\d.]+)', 글)
        if v:
            self.전압 = float(v.group(1))

        for 덩이 in _블록들(글, "cell"):
            이름, 몸 = 덩이
            면적 = float(re.search(r'area\s*:\s*([\d.]+)', 몸).group(1))
            c = 셀(이름=이름, 면적=면적, 순차="ff (" in 몸 or "ff(" in 몸)
            for 핀이름, 핀몸 in _블록들(몸, "pin"):
                방향 = re.search(r'direction\s*:\s*(\w+)', 핀몸).group(1)
                용량 = re.search(r'capacitance\s*:\s*([\d.]+)', 핀몸)
                함수 = re.search(r'function\s*:\s*"([^"]*)"', 핀몸)
                최대 = re.search(r'max_capacitance\s*:\s*([\d.]+)', 핀몸)
                p = 핀(이름=핀이름, 방향=방향,
                      용량=float(용량.group(1)) if 용량 else 0.0,
                      함수=함수.group(1) if 함수 else "",
                      클럭="clock : true" in 핀몸,
                      최대부하=float(최대.group(1)) if 최대 else 0.0)
                for _, t몸 in _블록들(핀몸, "timing"):
                    p.타이밍들.append(_타이밍읽기(t몸))
                c.핀들[핀이름] = p
            self.셀들[이름] = c
        if not self.셀들:
            raise ValueError(f"{self.길} 에서 셀을 하나도 못 읽었다")


def _타이밍읽기(몸):
    관련 = re.search(r'related_pin\s*:\s*"([^"]+)"', 몸).group(1)
    종류표 = re.search(r'timing_type\s*:\s*(\w+)', 몸)
    감 = re.search(r'timing_sense\s*:\s*(\w+)', 몸)
    if 종류표 and 종류표.group(1) == "setup_rising":
        종류 = "셋업"
    elif 종류표 and 종류표.group(1) == "hold_rising":
        종류 = "홀드"
    elif 종류표 and 종류표.group(1) == "rising_edge":
        종류 = "클럭Q"
    else:
        종류 = "조합"
    t = 타이밍(관련핀=관련, 종류=종류, 감=감.group(1) if 감 else "")
    for 키, 자리 in (("cell_rise", "상승"), ("cell_fall", "하강"),
                   ("rise_transition", "상승천이"),
                   ("fall_transition", "하강천이"),
                   ("rise_constraint", "상승"), ("fall_constraint", "하강")):
        m = re.search(키 + r'\s*\(\w+\)\s*\{\s*values\s*\((.*?)\)\s*;', 몸, re.S)
        if m:
            setattr(t, 자리, [_수열2(s) for s in re.findall(r'"([^"]+)"',
                                                          m.group(1))])
    return t


def _수열(m):
    return [float(x) for x in m.group(1).split(",")]


def _수열2(s):
    return [float(x) for x in s.split(",")]


def _블록들(글, 말):
    """`말 (이름) { ... }` 을 중괄호 짝을 세며 뽑는다."""
    나온것 = []
    for m in re.finditer(말 + r'\s*\(\s*([\w\d_]*)\s*\)\s*\{', 글):
        i = m.end() - 1
        깊이, j = 0, i
        while j < len(글):
            if 글[j] == "{":
                깊이 += 1
            elif 글[j] == "}":
                깊이 -= 1
                if 깊이 == 0:
                    break
            j += 1
        나온것.append((m.group(1), 글[i + 1:j]))
    return 나온것


def _2차원보간(축1, 축2, 표, x, y):
    """축 안이면 선형보간, 밖이면 **가장자리 기울기로 늘린다.**

    자르지 않는 이유: 잘라 버리면 부하가 큰 넷의 지연이 조용히 작게 나오고,
    그 조용함이 이 저장소가 가장 싫어하는 꼴이다.
    """
    def 자리(축, v):
        if v <= 축[0]:
            return 0, (v - 축[0]) / (축[1] - 축[0])
        for k in range(len(축) - 1):
            if v <= 축[k + 1]:
                return k, (v - 축[k]) / (축[k + 1] - 축[k])
        k = len(축) - 2
        return k, (v - 축[k]) / (축[k + 1] - 축[k])

    i, a = 자리(축1, x)
    j, b = 자리(축2, y)
    v00, v01 = 표[i][j], 표[i][j + 1]
    v10, v11 = 표[i + 1][j], 표[i + 1][j + 1]
    return ((1 - a) * ((1 - b) * v00 + b * v01)
            + a * ((1 - b) * v10 + b * v11))


if __name__ == "__main__":
    L = 라이브러리()
    print(f"{L.길}")
    print(f"셀 {len(L.셀들)}개 · 전압 {L.전압} V")
    print(f"천이축 {L.축천이} · 부하축 {L.축부하}")
    for 이름 in sorted(L.셀들):
        c = L.셀들[이름]
        print(f"  {이름:9s} 면적 {c.면적:8.4f} ({c.자리수():.1f} 자리)"
              f" 핀 {len(c.핀들)} {'[순차]' if c.순차 else ''}")
    print("보기: INVX1 A->Y, 부하 0.008 pF, 천이 0.04 ns ->",
          f"{L.지연('INVX1','Y','A',0.008,0.040)*1e3:.1f} ps")
    print("보기: DFFX1 셋업", f"{L.제약('DFFX1','D','셋업')*1e3:.1f} ps",
          "홀드", f"{L.제약('DFFX1','D','홀드')*1e3:.1f} ps")
