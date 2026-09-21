# -*- coding: utf-8 -*-
"""house/dv/vcd -- **시뮬레이터가 쓴 VCD 를 읽는다.** 파형을 지어내지 않는다.

verilator 가 `--vcd` 로 뱉은 Value Change Dump 를 규격대로 파싱한다.
($timescale · $scope · $var · $upscope · $enddefinitions · #시각 · 값변화)

**왜 이 파일이 있나.** "시뮬레이션 결과를 그림으로" 를 지키는 길은 둘뿐이다 --
시뮬레이터의 출력 파일을 읽거나, 아니면 지어내거나. 뒤엣것은 그림은 나오지만
아무것도 증명하지 않는다. 그래서 여기서 진짜 파일을 읽고, 읽은 시각·값만 그린다.

    d = 읽기("out.vcd")
    d["신호"]["nsw_fir.clk"] -> [(시각, "1"), (시각, "0"), ...]
    표본 = 뽑기(d, ["clk","in_vld","state_o"], 시작=None, 주기수=24)
"""
from __future__ import annotations

import re
from pathlib import Path


def 읽기(길) -> dict:
    """VCD 파일 하나를 통째로 읽는다.  돌려주는 것:

        {"눈금": "1ps", "신호": {풀이름: [(시각, 값글)]}, "폭": {풀이름: 비트수},
         "끝시각": int}
    """
    글 = Path(길).read_text(encoding="utf-8", errors="replace")
    머리, _, 몸 = 글.partition("$enddefinitions")
    눈금 = ""
    m = re.search(r"\$timescale\s+(.+?)\s*\$end", 머리, re.S)
    if m:
        눈금 = " ".join(m.group(1).split())

    # $var <종류> <폭> <기호> <이름> [<비트범위>] $end
    기호이름: dict[str, str] = {}
    폭: dict[str, int] = {}
    길목: list[str] = []
    for 줄 in 머리.splitlines():
        줄 = 줄.strip()
        if 줄.startswith("$scope"):
            조각 = 줄.split()
            if len(조각) >= 3:
                길목.append(조각[2])
        elif 줄.startswith("$upscope"):
            if 길목:
                길목.pop()
        elif 줄.startswith("$var"):
            조각 = 줄.split()
            if len(조각) >= 5:
                w, 기호, 이름 = int(조각[2]), 조각[3], 조각[4]
                풀 = ".".join(길목 + [이름])
                기호이름[기호] = 풀
                폭[풀] = w

    신호: dict[str, list] = {v: [] for v in 기호이름.values()}
    때 = 0
    끝 = 0
    for 줄 in 몸.splitlines():
        줄 = 줄.strip()
        if not 줄 or 줄.startswith("$"):
            continue
        if 줄[0] == "#":
            try:
                때 = int(줄[1:])
                끝 = max(끝, 때)
            except ValueError:
                pass
            continue
        if 줄[0] in "bB":                       # 다비트: b<값> <기호>
            조각 = 줄.split()
            if len(조각) == 2:
                값, 기호 = 조각[0][1:], 조각[1]
                이름 = 기호이름.get(기호)
                if 이름:
                    신호[이름].append((때, 값))
        elif 줄[0] in "rR":                     # 실수 -- 이 설계엔 없다
            continue
        else:                                   # 한비트: 0<기호> / 1<기호> / x<기호>
            값, 기호 = 줄[0], 줄[1:]
            이름 = 기호이름.get(기호)
            if 이름:
                신호[이름].append((때, 값))
    return {"눈금": 눈금, "신호": 신호, "폭": 폭, "끝시각": 끝,
            "신호수": len(신호), "변화수": sum(len(v) for v in 신호.values())}


def 찾기(d: dict, 꼬리: str) -> "str | None":
    """`in_vld` 처럼 꼬리만 줘도 풀이름을 찾는다."""
    for 이름 in d["신호"]:
        if 이름 == 꼬리 or 이름.endswith("." + 꼬리):
            return 이름
    return None


def 값(이력: list, 때: int) -> str:
    """그 시각에 유효한 값 (마지막 변화).  변화 전이면 'x'."""
    가장 = "x"
    for t, v in 이력:
        if t <= 때:
            가장 = v
        else:
            break
    return 가장


def 클럭엣지(d: dict, 클럭="clk") -> list:
    """클럭의 상승엣지 시각들 -- 표본을 여기에 맞춘다(시뮬레이터가 보는 그 순간)."""
    이름 = 찾기(d, 클럭)
    if not 이름:
        return []
    엣지, 앞 = [], "0"
    for t, v in d["신호"][이름]:
        if 앞 in "0x" and v == "1":
            엣지.append(t)
        앞 = v
    return 엣지


def 뽑기(d: dict, 이름들, 시작주기=0, 주기수=24, 클럭="clk") -> list:
    """클럭 엣지마다 표본을 떠 파형 그림이 먹는 꼴로 만든다.

    돌려주는 것: [(이름, "0011..", "bit"|"bus")] -- viz.파형 이 바로 먹는다.
    다비트는 16진수 글자로 접는다(한 칸에 한 값).
    """
    엣지 = 클럭엣지(d, 클럭)
    엣지 = 엣지[시작주기:시작주기 + 주기수]
    if not 엣지:
        return []
    out = []
    for 꼬리 in 이름들:
        이름 = 찾기(d, 꼬리)
        if not 이름:
            continue
        w = d["폭"].get(이름, 1)
        이력 = d["신호"][이름]
        if w == 1:
            글 = "".join(값(이력, t) for t in 엣지)
            out.append((꼬리, 글.replace("z", "x"), "bit"))
        else:
            칸 = []
            for t in 엣지:
                v = 값(이력, t)
                try:
                    칸.append(format(int(v, 2), "X"))
                except ValueError:
                    칸.append("x")
            out.append((꼬리, "".join(칸), "bus"))
    return out


def 원시(d: dict, 이름들, 끝시각=None, 점=600) -> list:
    """**클럭에 맞추지 않고** 원래 시각 그대로 뽑는다 -- 게이팅된 클럭처럼
    엣지가 사라지는 신호는 클럭 표본으로는 못 본다(빠진 펄스가 안 보인다)."""
    끝 = 끝시각 or d["끝시각"] or 1
    걸음 = max(1, 끝 // 점)
    시각들 = list(range(0, 끝 + 1, 걸음))[:점]
    out = []
    for 꼬리 in 이름들:
        이름 = 찾기(d, 꼬리)
        if not 이름:
            continue
        w = d["폭"].get(이름, 1)
        이력 = d["신호"][이름]
        if w == 1:
            out.append((꼬리, "".join(값(이력, t) for t in 시각들).replace("z", "x"), "bit"))
        else:
            칸 = []
            for t in 시각들:
                v = 값(이력, t)
                try:
                    칸.append(format(int(v, 2), "X"))
                except ValueError:
                    칸.append("x")
            out.append((꼬리, "".join(칸), "bus"))
    return out


def 구간찾기(d: dict, 꼬리: str, 값="1", 앞=40, 뒤=260) -> tuple:
    """그 신호가 처음 `값` 이 되는 시각 둘레의 구간을 돌려준다.

    **그림에 쓸 구간을 손으로 고르지 않으려고 있다.** 손으로 고르면 "잘 나온
    데만 골랐다" 가 되고, 그것은 이 저장소가 경계하는 바로 그 일이다.
    여기서는 규칙이 하나다 -- 그 사건이 처음 일어나는 데를 본다.
    """
    이름 = 찾기(d, 꼬리)
    if not 이름:
        return (0, min(d["끝시각"], 앞 + 뒤))
    for t, v in d["신호"][이름]:
        if v == 값:
            return (max(0, t - 앞), min(d["끝시각"], t + 뒤))
    return (0, min(d["끝시각"], 앞 + 뒤))


def 구간뽑기(d: dict, 이름들, 시작, 끝, 점=240) -> list:
    """[시작, 끝] 만 원시 해상도로 뽑는다."""
    걸음 = max(1, (끝 - 시작) // 점)
    시각들 = list(range(시작, 끝 + 1, 걸음))[:점]
    out = []
    for 꼬리 in 이름들:
        이름 = 찾기(d, 꼬리)
        if not 이름:
            continue
        w = d["폭"].get(이름, 1)
        이력 = d["신호"][이름]
        if w == 1:
            out.append((꼬리, "".join(값(이력, t) for t in 시각들).replace("z", "x"), "bit"))
        else:
            칸 = []
            for t in 시각들:
                v = 값(이력, t)
                try:
                    칸.append(format(int(v, 2), "X"))
                except ValueError:
                    칸.append("x")
            out.append((꼬리, "".join(칸), "bus"))
    return out


def 띠만들기(d: dict, 꼬리: str, 시작, 끝, 점=240, 이름표=None) -> list:
    """한 신호의 값이 바뀌는 구간을 주석 띠로 만든다 (FSM 상태 -> LOAD/RUN/...).

    강의 화면의 `Start | Device ID | Ack | Stop` 띠와 같은 것을, **우리 FSM 이
    실제로 지난 상태**로 만든다.
    """
    이름 = 찾기(d, 꼬리)
    if not 이름:
        return []
    걸음 = max(1, (끝 - 시작) // 점)
    시각들 = list(range(시작, 끝 + 1, 걸음))[:점]
    이력 = d["신호"][이름]
    띠, c = [], 0
    vals = [값(이력, t) for t in 시각들]
    while c < len(vals):
        j = c
        while j + 1 < len(vals) and vals[j + 1] == vals[c]:
            j += 1
        g = (이름표 or {}).get(vals[c], vals[c])
        if g and j - c >= 2:
            띠.append((c, j + 1, str(g)))
        c = j + 1
    return 띠
