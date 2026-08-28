import sys
import os
import collections
import hashlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from Public_agent.challenge5 import build_instance, is_feasible, value, decrypt, EXPECTED_SHA256
except ModuleNotFoundError:
    from challenge5 import build_instance, is_feasible, value, decrypt, EXPECTED_SHA256

class Dinic:
    def __init__(self, n, source, sink):
        self.n = n
        self.source = source
        self.sink = sink
        self.graph = [[] for _ in range(n)]
        self.edges = []
        
    def add_edge(self, u, v, cap):
        self.graph[u].append(len(self.edges))
        self.edges.append({'u': u, 'v': v, 'cap': cap, 'flow': 0})
        self.graph[v].append(len(self.edges))
        self.edges.append({'u': v, 'v': u, 'cap': 0, 'flow': 0})

    def bfs(self):
        self.level = [-1] * self.n
        self.level[self.source] = 0
        q = collections.deque([self.source])
        while q:
            u = q.popleft()
            for edge_idx in self.graph[u]:
                edge = self.edges[edge_idx]
                if edge['cap'] - edge['flow'] > 0 and self.level[edge['v']] == -1:
                    self.level[edge['v']] = self.level[u] + 1
                    q.append(edge['v'])
        return self.level[self.sink] != -1

    def dfs(self, u, pushed, ptr):
        if pushed == 0 or u == self.sink:
            return pushed
        for i in range(ptr[u], len(self.graph[u])):
            ptr[u] = i
            edge_idx = self.graph[u][i]
            edge = self.edges[edge_idx]
            v = edge['v']
            tr = edge['cap'] - edge['flow']
            if self.level[u] + 1 != self.level[v] or tr == 0:
                continue
            push = self.dfs(v, min(pushed, tr), ptr)
            if push == 0:
                continue
            self.edges[edge_idx]['flow'] += push
            self.edges[edge_idx ^ 1]['flow'] -= push
            return push
        return 0

    def max_flow(self):
        flow = 0
        INF = float('inf')
        while self.bfs():
            ptr = [0] * self.n
            while True:
                pushed = self.dfs(self.source, INF, ptr)
                if pushed == 0:
                    break
                flow += pushed
        return flow

    def get_min_cut_source_side(self):
        visited = [False] * self.n
        q = collections.deque([self.source])
        visited[self.source] = True
        while q:
            u = q.popleft()
            for edge_idx in self.graph[u]:
                edge = self.edges[edge_idx]
                if edge['cap'] - edge['flow'] > 0 and not visited[edge['v']]:
                    visited[edge['v']] = True
                    q.append(edge['v'])
        return visited

def solve() -> str:
    w, edges = build_instance()
    n = len(w)

    source = n
    sink = n + 1
    dinic = Dinic(n + 2, source, sink)

    INF = 10**15
    for i in range(n):
        if w[i] > 0:
            dinic.add_edge(source, i, w[i])
        elif w[i] < 0:
            dinic.add_edge(i, sink, -w[i])

    for u, v in edges:
        dinic.add_edge(u, v, INF)

    dinic.max_flow()
    visited = dinic.get_min_cut_source_side()

    S = [i for i in range(n) if visited[i]]
    if not is_feasible(S, edges):
        raise ValueError("Derived subset S is not feasible")

    return decrypt(S, n)

def main():
    recovered = solve()
    digest = hashlib.sha256(recovered.encode()).hexdigest()
    match = digest == EXPECTED_SHA256

    print(f"Recovered string: {recovered}")
    print(f"Calculated SHA-256: {digest}")
    print(f"Expected SHA-256: {EXPECTED_SHA256}")
    print(f"Match status: {match}")

    if not match:
        raise ValueError("SHA-256 mismatch!")

if __name__ == "__main__":
    main()
