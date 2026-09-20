# -*- coding: utf-8 -*-
"""yosys 가 낸 JSON 넷리스트를 읽어 **그래프**로 만든다.

넷리스트는 셀과 넷의 목록이지만 뒤의 단계들이 필요한 것은 그래프다 --
어느 출력이 어느 입력으로 가는가.  여기서 한 번만 만들어 두고 STA · 배치 ·
CTS · 배선 · DFT 가 모두 이것을 쓴다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class 인스턴스:
    이름: str
    종류: str
    연결: dict                     # 핀이름 -> 넷id (한 비트)
    x: float = 0.0                 # 배치가 채운다
    y: float = 0.0
    행: int = -1
    고정: bool = False


@dataclass
class 넷:
    id: int
    이름: str = ""
    몰이: tuple = None             # (인스턴스이름, 핀) 또는 ("PI", 포트)
    싣기: list = field(default_factory=list)    # [(인스턴스이름, 핀), ...]
    상수: str = ""                 # "0" | "1" 이면 상수 넷


class 넷리스트:
    def __init__(self, 길, 라이브러리, 톱=None):
        self.라이브러리 = 라이브러리
        j = json.load(open(길, encoding="utf-8"))
        이름들 = list(j["modules"])
        self.톱 = 톱 or 이름들[0]
        m = j["modules"][self.톱]

        self.인스턴스: dict[str, 인스턴스] = {}
        self.넷: dict[int, 넷] = {}
        self.입력포트: dict[str, list] = {}
        self.출력포트: dict[str, list] = {}
        self.넷이름: dict[int, str] = {}

        for 이름, p in m.get("netnames", {}).items():
            for i, b in enumerate(p["bits"]):
                if isinstance(b, int) and b not in self.넷이름:
                    self.넷이름[b] = 이름 if len(p["bits"]) == 1 else f"{이름}[{i}]"

        for 이름, p in m["ports"].items():
            (self.입력포트 if p["direction"] == "input"
             else self.출력포트)[이름] = p["bits"]

        for 이름, c in m["cells"].items():
            연결 = {}
            for 핀, 비트 in c["connections"].items():
                if len(비트) != 1:
                    raise ValueError(f"{이름}.{핀} 이 여러 비트다 -- "
                                     "techmap 뒤의 넷리스트가 맞나")
                연결[핀] = 비트[0]
            self.인스턴스[이름] = 인스턴스(이름=이름, 종류=c["type"].lstrip("\\"),
                                    연결=연결)

        self._넷짓기()

    # ---------------------------------------------------------------
    def _넷짓기(self):
        def 넷얻기(b):
            if isinstance(b, str):                  # "0" · "1" · "x" · "z"
                key = -1 - "01xz".index(b) if b in "01xz" else -99
                if key not in self.넷:
                    self.넷[key] = 넷(id=key, 이름=f"상수{b}", 상수=b)
                return self.넷[key]
            if b not in self.넷:
                self.넷[b] = 넷(id=b, 이름=self.넷이름.get(b, f"n{b}"))
            return self.넷[b]

        for 이름, 비트들 in self.입력포트.items():
            for i, b in enumerate(비트들):
                n = 넷얻기(b)
                n.몰이 = ("PI", 이름 if len(비트들) == 1 else f"{이름}[{i}]")

        for 인, inst in self.인스턴스.items():
            c = self.라이브러리.셀들.get(inst.종류)
            if c is None:
                raise KeyError(f"{인} 의 셀 {inst.종류} 가 라이브러리에 없다")
            for 핀, b in inst.연결.items():
                n = 넷얻기(b)
                p = c.핀들.get(핀)
                if p is None:
                    raise KeyError(f"{inst.종류} 에 핀 {핀} 이 없다")
                if p.방향 == "output":
                    if n.몰이 is not None:
                        raise ValueError(f"넷 {n.이름} 을 둘이 몬다: "
                                         f"{n.몰이} 와 ({인},{핀})")
                    n.몰이 = (인, 핀)
                else:
                    n.싣기.append((인, 핀))

        for 이름, 비트들 in self.출력포트.items():
            for i, b in enumerate(비트들):
                n = 넷얻기(b)
                n.싣기.append(("PO", 이름 if len(비트들) == 1
                             else f"{이름}[{i}]"))

    # ---------------------------------------------------------------
    @property
    def 플롭들(self):
        return [i for i in self.인스턴스.values()
                if self.라이브러리.셀들[i.종류].순차]

    @property
    def 조합들(self):
        return [i for i in self.인스턴스.values()
                if not self.라이브러리.셀들[i.종류].순차]

    def 총면적(self):
        return sum(self.라이브러리.셀들[i.종류].면적
                   for i in self.인스턴스.values())

    def 부하(self, 넷id):
        """이 넷에 달린 입력 용량의 합 (pF).  배선은 아직 없다."""
        n = self.넷.get(넷id)
        if n is None:
            return 0.0
        s = 0.0
        for 인, 핀 in n.싣기:
            if 인 == "PO":
                s += 0.010                  # 출력 핀의 바깥 부하 (가정)
            else:
                c = self.라이브러리.셀들[self.인스턴스[인].종류]
                s += c.핀들[핀].용량
        return s

    def 클럭넷(self):
        """클럭 핀들이 매달린 넷.  가장 많이 달린 것 하나를 고른다."""
        셈 = {}
        for i in self.플롭들:
            c = self.라이브러리.셀들[i.종류]
            for 핀, b in i.연결.items():
                if c.핀들[핀].클럭:
                    셈[b] = 셈.get(b, 0) + 1
        if not 셈:
            raise ValueError("클럭 핀이 하나도 없다")
        return max(셈, key=셈.get)

    def 요약(self):
        종류셈 = {}
        for i in self.인스턴스.values():
            종류셈[i.종류] = 종류셈.get(i.종류, 0) + 1
        return {
            "톱": self.톱,
            "인스턴스": len(self.인스턴스),
            "플롭": len(self.플롭들),
            "조합": len(self.조합들),
            "넷": len([n for n in self.넷.values() if n.id >= 0]),
            "셀면적_um2": round(self.총면적(), 3),
            "종류별": dict(sorted(종류셈.items(), key=lambda kv: -kv[1])),
        }


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from liberty import 라이브러리
    뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nl = 넷리스트(os.path.join(뿌리, "out", "dsp_top.json"), 라이브러리())
    import pprint
    pprint.pprint(nl.요약())
