# -*- coding: utf-8 -*-
"""정적 타이밍 분석 -- 도착·요구·슬랙, 그리고 임계경로.

## 무엇을 하나

타이밍 그래프를 짓는다.  마디는 (인스턴스, 핀) 이고 이음은 두 가지다.

    셀 이음   입력핀 -> 출력핀.  지연은 `.lib` 의 표에서 (출력 부하, 입력 천이)
    넷 이음   출력핀 -> 실린 입력핀들.  지연은 배선 모형에서

시작점은 **PI 와 플롭의 Q** 이고, 끝점은 **PO 와 플롭의 D** 다.  클럭 핀은
조합 이음이 아니므로 그래프를 끊는다 -- 그래서 그래프가 비순환이 되고,
위상 순서로 한 번 훑으면 도착시각이 다 나온다.

## 왜 두 가지로 재나

블록 기반(여기 `풀기`)은 마디마다 최대를 취하며 한 번 훑는다 -- 빠르지만
**정말 그 값이 어떤 경로의 값인지**는 안 보인다.  경로 기반(`경로최대`)은
경로를 실제로 따라가며 잰다.  둘은 같은 답을 내야 한다.  안 그러면 둘 중
하나가 틀린 것이고, **하나만 있으면 틀린 줄도 모른다.**
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class 마디:
    키: tuple
    도착: float = 0.0
    천이: float = 0.020            # ns, 시작점의 기본 입력 천이
    요구: float = float("inf")
    앞: tuple = None               # 임계경로를 되짚을 때 쓴다
    앞이음: str = ""


@dataclass
class 결과:
    주기: float
    최악슬랙: float
    위반수: int
    임계경로: list = field(default_factory=list)
    끝점들: list = field(default_factory=list)
    마디들: dict = field(default_factory=dict)

    def 요약(self):
        return {
            "주기_ns": round(self.주기, 4),
            "최악슬랙_ns": round(self.최악슬랙, 5),
            "Fmax_MHz": round(1e3 / (self.주기 - self.최악슬랙), 2)
            if self.주기 - self.최악슬랙 > 0 else None,
            "위반_끝점": self.위반수,
            "임계경로_단수": len(self.임계경로),
        }


class 분석기:
    def __init__(self, nl, 주기=10.0, 배선지연=None, 배선부하=None,
                 입력천이=0.020, 클럭스큐=0.0):
        """`배선지연(넷id, 인스턴스, 핀) -> ns`, `배선부하(넷id) -> pF`.

        둘 다 없으면 **배선이 없는 셈**으로 잰다 -- 합성 직후의 낙관적인 값이고,
        그 낙관이 얼마인지는 T17.2 가 말한 그 표류로 나중에 드러난다.
        """
        self.nl = nl
        self.lib = nl.라이브러리
        self.주기 = 주기
        self.클럭스큐 = 클럭스큐
        self.입력천이 = 입력천이
        self._배선지연 = 배선지연 or (lambda n, i, p: 0.0)
        self._배선부하 = 배선부하 or (lambda n: 0.0)
        self.클럭 = nl.클럭넷()
        self.마디: dict[tuple, 마디] = {}
        self.앞으로: dict[tuple, list] = {}      # 키 -> [(다음키, 종류)]
        self.시작: list[tuple] = []
        self.끝: list[tuple] = []
        self._그래프()

    # ---------------------------------------------------------------
    def _마디(self, 키):
        if 키 not in self.마디:
            self.마디[키] = 마디(키=키)
            self.앞으로.setdefault(키, [])
        return self.마디[키]

    def _그래프(self):
        nl, lib = self.nl, self.lib
        for 이름, inst in nl.인스턴스.items():
            c = lib.셀들[inst.종류]
            출력 = [p.이름 for p in c.출력핀]
            for 입 in c.입력핀:
                if 입.클럭 or 입.이름 == "RN":
                    continue                   # 클럭·비동기 리셋은 안 잇는다
                if c.순차:
                    continue                   # 순차셀의 D 는 끝점이다
                for 출 in 출력:
                    self._마디((이름, 입.이름))
                    self._마디((이름, 출))
                    self.앞으로[(이름, 입.이름)].append(((이름, 출), "셀"))

        for n in nl.넷.values():
            if n.상수 or n.몰이 is None:
                continue
            if n.id == self.클럭:
                continue                       # 클럭망은 CTS 가 따로 본다
            출키 = ("PI", n.몰이[1]) if n.몰이[0] == "PI" else n.몰이
            self._마디(출키)
            for 인, 핀 in n.싣기:
                if 인 == "PO":
                    입키 = ("PO", 핀)
                else:
                    c = lib.셀들[nl.인스턴스[인].종류]
                    if c.핀들[핀].클럭 or 핀 == "RN":
                        continue
                    입키 = (인, 핀)
                self._마디(입키)
                self.앞으로[출키].append((입키, f"넷:{n.id}"))

        # 시작점: PI 와 플롭의 Q.  끝점: PO 와 플롭의 D.
        for 포트 in nl.입력포트:
            pass
        for 키 in list(self.마디):
            인, 핀 = 키
            if 인 == "PI":
                self.시작.append(키)
            elif 인 == "PO":
                self.끝.append(키)
            elif 인 in nl.인스턴스:
                c = lib.셀들[nl.인스턴스[인].종류]
                if c.순차 and 핀 in [p.이름 for p in c.출력핀]:
                    self.시작.append(키)
                elif c.순차 and 핀 == "D":
                    self.끝.append(키)
        for i in nl.플롭들:
            self.끝.append((i.이름, "D"))
            self._마디((i.이름, "D"))
        self.끝 = sorted(set(self.끝))
        self.시작 = sorted(set(self.시작))

    # ---------------------------------------------------------------
    def 출력부하(self, 인, 핀):
        """이 출력 핀이 보는 부하 (pF) -- 실린 입력 용량 + 배선 용량."""
        inst = self.nl.인스턴스.get(인)
        if inst is None:
            return 0.010
        b = inst.연결[핀]
        return self.nl.부하(b) + self._배선부하(b)

    def _이음지연(self, 키, 다음, 종류):
        인, 핀 = 키
        if 종류 == "셀":
            c = self.lib.셀들[self.nl.인스턴스[인].종류]
            출 = 다음[1]
            부하 = self.출력부하(인, 출)
            t = self.마디[키].천이
            d = self.lib.지연(self.nl.인스턴스[인].종류, 출, 핀, 부하, t)
            s = self.lib.천이(self.nl.인스턴스[인].종류, 출, 핀, 부하, t)
            return d, s
        넷id = int(종류.split(":")[1])
        return self._배선지연(넷id, 다음[0], 다음[1]), self.마디[키].천이

    def 위상순서(self):
        진입 = {k: 0 for k in self.마디}
        for k, 다음들 in self.앞으로.items():
            for n, _ in 다음들:
                진입[n] = 진입.get(n, 0) + 1
        큐 = [k for k, v in 진입.items() if v == 0]
        순서 = []
        while 큐:
            k = 큐.pop()
            순서.append(k)
            for n, _ in self.앞으로.get(k, ()):
                진입[n] -= 1
                if 진입[n] == 0:
                    큐.append(n)
        if len(순서) != len(self.마디):
            남 = [k for k, v in 진입.items() if v > 0][:5]
            raise ValueError(f"타이밍 그래프에 고리가 있다 (예: {남})")
        return 순서

    # ---------------------------------------------------------------
    def 풀기(self):
        """블록 기반 -- 위상 순서로 한 번 훑으며 최대 도착시각을 민다."""
        for k in self.마디:
            m = self.마디[k]
            m.도착, m.천이, m.앞, m.앞이음 = -1e30, self.입력천이, None, ""
        for k in self.시작:
            self.마디[k].도착 = 0.0
            self.마디[k].천이 = self.입력천이
        # 플롭 Q 는 클럭-Q 지연만큼 늦게 뜬다
        for i in self.nl.플롭들:
            키 = (i.이름, "Q")
            if 키 in self.마디:
                부하 = self.출력부하(i.이름, "Q")
                self.마디[키].도착 = self.lib.지연(i.종류, "Q", "CK", 부하,
                                              self.입력천이)
                self.마디[키].천이 = self.lib.천이(i.종류, "Q", "CK", 부하,
                                              self.입력천이)

        for k in self.위상순서():
            m = self.마디[k]
            if m.도착 < -1e29:
                continue
            for 다음, 종류 in self.앞으로.get(k, ()):
                d, s = self._이음지연(k, 다음, 종류)
                n = self.마디[다음]
                if m.도착 + d > n.도착:
                    n.도착 = m.도착 + d
                    n.천이 = s
                    n.앞, n.앞이음 = k, 종류

        끝점들 = []
        for k in self.끝:
            m = self.마디.get(k)
            if m is None or m.도착 < -1e29:
                continue
            인, 핀 = k
            if 인 == "PO":
                여유 = self.주기
            else:
                셋업 = self.lib.제약(self.nl.인스턴스[인].종류, "D", "셋업")
                여유 = self.주기 + self.클럭스큐 - 셋업
            끝점들.append((여유 - m.도착, k, m.도착, 여유))
        끝점들.sort()
        최악 = 끝점들[0] if 끝점들 else (0.0, None, 0, 0)
        r = 결과(주기=self.주기, 최악슬랙=최악[0],
                위반수=sum(1 for s, *_ in 끝점들 if s < 0),
                끝점들=끝점들, 마디들=self.마디)
        if 최악[1]:
            r.임계경로 = self.되짚기(최악[1])
        return r

    def 되짚기(self, 끝키):
        경로, k = [], 끝키
        while k is not None:
            m = self.마디[k]
            경로.append((k, m.도착, m.앞이음))
            k = m.앞
        return list(reversed(경로))

    # ---------------------------------------------------------------
    def 경로최대(self, 끝키):
        """**경로 기반** -- 같은 값을 다른 길로 구한다.

        블록 기반이 마디마다 최대를 취하는 것과 달리, 여기서는 끝점에서
        거꾸로 재귀하며 **경로를 따라** 최대를 찾는다.  천이가 경로에 따라
        달라지므로 단순한 메모이제이션이 아니라 (마디, 들어온 천이) 를
        열쇠로 삼는다.  두 값이 어긋나면 둘 중 하나가 틀린 것이다.
        """
        뒤로 = {}
        for k, 다음들 in self.앞으로.items():
            for n, 종류 in 다음들:
                뒤로.setdefault(n, []).append((k, 종류))

        시작집합 = set(self.시작)
        플롭Q = {}
        for i in self.nl.플롭들:
            키 = (i.이름, "Q")
            부하 = self.출력부하(i.이름, "Q")
            플롭Q[키] = (self.lib.지연(i.종류, "Q", "CK", 부하, self.입력천이),
                       self.lib.천이(i.종류, "Q", "CK", 부하, self.입력천이))

        메모 = {}

        def 재귀(키):
            """(그 마디까지의 최대 도착, 그때의 천이)."""
            if 키 in 메모:
                return 메모[키]
            if 키 in 플롭Q:
                메모[키] = 플롭Q[키]
                return 메모[키]
            if 키 in 시작집합:
                메모[키] = (0.0, self.입력천이)
                return 메모[키]
            최선 = (-1e30, self.입력천이)
            for 앞키, 종류 in 뒤로.get(키, ()):
                a, s = 재귀(앞키)
                if a < -1e29:
                    continue
                if 종류 == "셀":
                    인, 핀 = 앞키
                    c종 = self.nl.인스턴스[인].종류
                    부하 = self.출력부하(인, 키[1])
                    d = self.lib.지연(c종, 키[1], 핀, 부하, s)
                    ns = self.lib.천이(c종, 키[1], 핀, 부하, s)
                else:
                    d, ns = self._배선지연(int(종류.split(":")[1]),
                                        키[0], 키[1]), s
                if a + d > 최선[0]:
                    최선 = (a + d, ns)
            메모[키] = 최선
            return 최선

        import sys
        옛 = sys.getrecursionlimit()
        sys.setrecursionlimit(max(옛, 20000))
        try:
            return 재귀(끝키)[0]
        finally:
            sys.setrecursionlimit(옛)


def 경로글(경로, nl):
    """임계경로를 사람이 읽게."""
    줄 = []
    앞 = None
    for (키, 도착, 이음) in 경로:
        인, 핀 = 키
        종 = nl.인스턴스[인].종류 if 인 in nl.인스턴스 else 인
        증 = "" if 앞 is None else f"  (+{(도착-앞)*1e3:7.1f} ps {이음})"
        줄.append(f"  {도착*1e3:8.1f} ps  {종:9s} {인}/{핀}{증}")
        앞 = 도착
    return "\n".join(줄)
