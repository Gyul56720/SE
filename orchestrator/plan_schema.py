"""
plan 스키마: 문제를 하위 작업(algorithm)들의 DAG 로 표현하는 데이터 모델.

왜 git-영속 JSON DAG 인가 (인메모리/그래프DB 아님): 이 저장소에서 반복 실증됐듯,
인메모리 상태(LangGraph MemorySaver 등)는 프로세스 재시작에 소실되고, 메모리 노트는
읽히지 않으면 무효다. 유일하게 신뢰 가능한 복원 기반은 git 이다. 그래서 plan 은 파일
(plan.json)로 저장되고, 각 노드의 solve 코드/결과도 파일로 커밋된다 -- 프로세스가 죽어도
plan.json 을 다시 읽어 verified 노드는 건너뛰고 미완 노드부터 재개할 수 있다(복원).

노드(Node): 하나의 하위 작업.
  id        : 고유 식별자
  goal      : 이 노드가 무엇을 푸는지(자연어)
  deps      : 선행 노드 id 목록 (이들의 결과가 입력으로 들어온다)
  component : solve(inputs: dict) -> dict 를 정의한 파이썬 파일 경로(런 디렉토리 기준)
  verifier  : check(output: dict, inputs: dict) -> (bool, str) 를 정의한 파일#함수
  status    : "pending" | "verified" | "failed"
  result_ref: 검증된 결과가 저장된 파일 경로(런 디렉토리 기준)
  attempts  : 시도 이력(실패 사유 누적 -> 같은 실패 반복 방지)

Plan:
  problem : 원 문제 설명
  nodes   : Node 목록
  final   : 최종 답을 내는 노드 id (모든 하위 노드에 의존)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Node:
    id: str
    goal: str
    component: str
    verifier: str
    deps: list = field(default_factory=list)
    status: str = "pending"
    result_ref: str = ""
    attempts: list = field(default_factory=list)


@dataclass
class Plan:
    problem: str
    nodes: list
    final: str

    @staticmethod
    def load(path) -> "Plan":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        nodes = [Node(**n) for n in raw["nodes"]]
        return Plan(problem=raw["problem"], nodes=nodes, final=raw["final"])

    def save(self, path):
        Path(path).write_text(
            json.dumps({"problem": self.problem, "final": self.final,
                        "nodes": [asdict(n) for n in self.nodes]},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")

    def node(self, node_id: str) -> Node:
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(node_id)

    def validate(self) -> list:
        """구조 오류 목록 반환(빈 리스트면 정상). 사이클/미정의 의존/final 부재를 잡는다."""
        errs = []
        ids = {n.id for n in self.nodes}
        if len(ids) != len(self.nodes):
            errs.append("중복된 노드 id 가 있다.")
        if self.final not in ids:
            errs.append(f"final 노드 '{self.final}' 가 노드 목록에 없다.")
        for n in self.nodes:
            for d in n.deps:
                if d not in ids:
                    errs.append(f"노드 '{n.id}' 의 의존 '{d}' 가 정의되지 않았다.")
        if not errs and self._has_cycle():
            errs.append("DAG 에 사이클이 있다.")
        return errs

    def _has_cycle(self) -> bool:
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n.id: WHITE for n in self.nodes}

        def dfs(u):
            color[u] = GRAY
            for d in self.node(u).deps:
                if color[d] == GRAY:
                    return True
                if color[d] == WHITE and dfs(d):
                    return True
            color[u] = BLACK
            return False

        return any(color[n.id] == WHITE and dfs(n.id) for n in self.nodes)

    def topo_order(self) -> list:
        """의존이 먼저 오도록 정렬된 노드 id 목록."""
        order, seen = [], set()

        def visit(u):
            if u in seen:
                return
            for d in self.node(u).deps:
                visit(d)
            seen.add(u)
            order.append(u)

        for n in self.nodes:
            visit(n.id)
        return order

    def ready_nodes(self) -> list:
        """의존이 모두 verified 이고 자신은 아직 verified 가 아닌 노드 id."""
        out = []
        for nid in self.topo_order():
            n = self.node(nid)
            if n.status == "verified":
                continue
            if all(self.node(d).status == "verified" for d in n.deps):
                out.append(nid)
        return out
