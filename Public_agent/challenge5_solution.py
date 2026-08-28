"""
challenge5의 검증된 참조 정답.

핵심은 이 문제가 NP-hard가 아니라는 것을 알아보는 데 있다. "선행 제약을 지키는 부분집합의
가중치 합 최대화"는 그래프 이론에서 최대 폐포(maximum closure) 문제이고, 최대 폐포는
최소 절단(min-cut)으로 정확히, 다항 시간에 풀린다(Picard, 1976).

  - 소스 s에서 w[i] > 0인 항목 i로 용량 w[i]인 간선을 놓는다.
  - w[i] < 0인 항목 i에서 싱크 t로 용량 -w[i]인 간선을 놓는다.
  - 선행 제약 (u, v)마다 u -> v로 용량 무한대인 간선을 놓는다.
  - 최적값 = (양수 가중치의 합) - (최대 유량)
  - 최적 부분집합 = 잔여 그래프에서 s로부터 도달 가능한 항목들

무한대 간선 덕분에 최소 절단은 선행 제약을 절대 끊지 못하고, 따라서 s쪽 집합은 항상
실행가능하다. 탐욕법/국소탐색이 왜 실패하는지도 여기서 드러난다 -- 이 인스턴스는 단독으로
이득인 수가 하나도 없어서 지역적으로는 공집합이 극대점이지만, 전역 최적은 2254다.

유일성은 최소 해집합과 최대 해집합을 각각 구해서 확인한다. 최적 폐포들은 격자(lattice)를
이루므로 최소해(s에서 도달 가능)와 최대해(t로 도달 불가능)가 같으면 최적해가 유일하다.
"""
import hashlib
from collections import deque

from challenge5 import build_instance, is_feasible, value, decrypt, EXPECTED_SHA256


class Dinic:
    def __init__(self, n: int):
        self.n = n
        self.g: list[list[list]] = [[] for _ in range(n)]

    def add(self, u: int, v: int, c: int) -> None:
        self.g[u].append([v, c, len(self.g[v])])
        self.g[v].append([u, 0, len(self.g[u]) - 1])

    def _bfs(self, s: int, t: int) -> bool:
        self.lv = [-1] * self.n
        self.lv[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for v, c, _ in self.g[u]:
                if c > 0 and self.lv[v] < 0:
                    self.lv[v] = self.lv[u] + 1
                    q.append(v)
        return self.lv[t] >= 0

    def _dfs(self, u: int, t: int, f: int) -> int:
        if u == t:
            return f
        while self.it[u] < len(self.g[u]):
            e = self.g[u][self.it[u]]
            v = e[0]
            if e[1] > 0 and self.lv[v] == self.lv[u] + 1:
                d = self._dfs(v, t, min(f, e[1]))
                if d > 0:
                    e[1] -= d
                    self.g[v][e[2]][1] += d
                    return d
            self.it[u] += 1
        return 0

    def maxflow(self, s: int, t: int) -> int:
        total = 0
        while self._bfs(s, t):
            self.it = [0] * self.n
            while True:
                f = self._dfs(s, t, float("inf"))
                if f == 0:
                    break
                total += f
        return total

    def reachable_from(self, s: int) -> list[bool]:
        seen = [False] * self.n
        seen[s] = True
        q = deque([s])
        while q:
            u = q.popleft()
            for v, c, _ in self.g[u]:
                if c > 0 and not seen[v]:
                    seen[v] = True
                    q.append(v)
        return seen

    def can_reach(self, t: int) -> list[bool]:
        radj: list[list[int]] = [[] for _ in range(self.n)]
        for u in range(self.n):
            for v, c, _ in self.g[u]:
                if c > 0:
                    radj[v].append(u)
        seen = [False] * self.n
        seen[t] = True
        q = deque([t])
        while q:
            u = q.popleft()
            for v in radj[u]:
                if not seen[v]:
                    seen[v] = True
                    q.append(v)
        return seen


def max_closure(w, edges):
    """최대 폐포를 min-cut으로 정확히 푼다. (최소최적해, 최대최적해, 최적값)."""
    n = len(w)
    s, t = n, n + 1
    d = Dinic(n + 2)
    INF = sum(abs(x) for x in w) + 1
    pos = 0
    for i, wi in enumerate(w):
        if wi > 0:
            d.add(s, i, wi)
            pos += wi
        elif wi < 0:
            d.add(i, t, -wi)
    for u, v in edges:
        d.add(u, v, INF)
    flow = d.maxflow(s, t)
    rs = d.reachable_from(s)
    ct = d.can_reach(t)
    smin = frozenset(i for i in range(n) if rs[i])
    smax = frozenset(i for i in range(n) if not ct[i])
    return smin, smax, pos - flow


def solve() -> str:
    w, edges = build_instance()
    smin, _, _ = max_closure(w, edges)
    return decrypt(smin, len(w))


def main() -> None:
    w, edges = build_instance()
    smin, smax, opt = max_closure(w, edges)
    assert smin == smax, "최적해가 유일하지 않다"
    assert is_feasible(smin, edges), "최적해가 실행가능하지 않다"
    assert value(smin, w) == opt, "최적값 불일치"
    answer = decrypt(smin, len(w))
    digest = hashlib.sha256(answer.encode()).hexdigest()
    assert digest == EXPECTED_SHA256, f"검증 실패: {digest}"
    print(f"n = {len(w)}, 간선 = {len(edges)}")
    print(f"최적값 = {opt}, |S*| = {len(smin)} ({len(smin)/len(w):.0%}), 유일해 = True")
    print("정답:", answer)
    print("검증: sha256 일치 OK")


if __name__ == "__main__":
    main()
