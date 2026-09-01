"""
로컬 채점기 -- 자가 개선 루프의 심판(verifier).

이 파일이 이 시스템 전체의 무게를 진다. 이유는 orchestrator 와 같다: LLM 이 제안한 해법을
'채택'하려면 그것이 더 낫다는 것을 판정할 신뢰 가능한 기준이 있어야 한다. 리더보드는 하루에
몇 번밖에 못 두드리고 테스트 정답도 없으므로, 손에 든 라벨 데이터 위에서 대회 지표를 그대로
재현하는 채점기가 유일한 심판이다. 이게 부정확하면 루프는 '개선'이 아니라 '표류'가 된다.

대회 설명에 적힌 정의를 그대로 옮긴 부분:
  - 물리 스케일 z=1.625, y=x=0.40625 µm/voxel. 매칭 거리 상한 7.0 µm.
  - 타임포인트마다 예측 노드 <-> 정답 노드를 스케일된 중심 거리로 최적 이분 매칭.
  - 예측 엣지는 '양 끝점이 모두 매칭되고, 그 매칭된 정답 노드 쌍이 정답 엣지일 때' TP.
  - edge Jaccard = TP / (TP + FP + FN), 노드 수 과다 예측에 대한 페널티로 보정.
  - division = 나가는 엣지가 2개 이상인 노드. 정답 division 마다, 예측 그래프에 분열 직전
    단계를 덮으면서 두 딸 계보에 모두 닿는 연결 요소가 있으면 TP.
  - 표본별 edge Jaccard 는 (TP+FP+FN) 가중 평균, division 은 전체 micro 평균.

대회 설명만으로는 확정할 수 없어 '가정'으로 둔 부분 -- 반드시 알고 쓸 것:
  A. "노드 수 과다 예측에 대한 페널티"의 정확한 식이 공개되지 않았다. 여기서는 예측 노드가
     정답 노드보다 많을 때 min(1, n_gt / n_pred) 를 곱한다. 보수적인(점수를 낮게 보는) 선택이다.
  B. 정답이 sparse 하게만 라벨링돼 있다는 점 때문에, '매칭되지 않은 예측 노드'를 낀 엣지는
     FP 로 세지 않는다(라벨이 없는 진짜 세포일 수 있으므로). 매칭된 노드끼리 이어졌는데 정답에
     그 엣지가 없을 때만 FP 다. 설명의 "metric accounts for it" 을 이렇게 읽었다.
  C. division 의 '분열 직전 단계를 덮는다'를 여기서는 '정답 분열 노드에 매칭된 예측 노드가
     존재하고, 그 노드에서 나가는 예측 엣지들이 두 딸 노드에 각각 매칭된 예측 노드에 닿는다'로
     구현했다. 연결 요소를 몇 프레임까지 추적할지는 명시돼 있지 않아 1홉으로 제한했다.

따라서 로컬 점수는 리더보드 점수와 다를 수 있다. 루프가 재는 것은 '이 채점기 기준의 개선'이며,
그 사실을 숨기지 않는 것이 이 파일의 계약이다. 리더보드 점수를 알게 되면 calibrate() 로
로컬-리더보드 차이를 기록해 두라 -- 그 차이가 크면 A/B/C 가정을 먼저 의심해야 한다.

의존: numpy 만 필수. scipy 가 있으면 최적 이분 매칭에 linear_sum_assignment 를 쓰고,
없으면 같은 결과를 내는 순수 파이썬 헝가리안 구현으로 물러선다(작은 문제에서 동일함을
tests 에서 확인한다).
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

# 대회 명세에 박힌 상수.
SCALE_ZYX = (1.625, 0.40625, 0.40625)   # µm / voxel
MAX_MATCH_UM = 7.0


# ---------------------------------------------------------------- 이분 매칭

def _hungarian(cost: np.ndarray) -> list:
    """O(n^3) 헝가리안. (row, col) 목록 반환. scipy 가 없을 때의 대체 경로."""
    c = np.array(cost, dtype=float)
    n, m = c.shape
    if n == 0 or m == 0:
        return []
    transposed = n > m
    if transposed:
        c = c.T
        n, m = m, n
    INF = float("inf")
    u = [0.0] * (n + 1)
    v = [0.0] * (m + 1)
    p = [0] * (m + 1)
    way = [0] * (m + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [INF] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], INF, 0
            for j in range(1, m + 1):
                if used[j]:
                    continue
                cur = c[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j], way[j] = cur, j0
                if minv[j] < delta:
                    delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    pairs = [(p[j] - 1, j - 1) for j in range(1, m + 1) if p[j] > 0]
    return [(b, a) for a, b in pairs] if transposed else pairs


def optimal_matching(cost: np.ndarray) -> list:
    if cost.size == 0:
        return []
    try:
        from scipy.optimize import linear_sum_assignment
        r, c = linear_sum_assignment(cost)
        return list(zip(r.tolist(), c.tolist()))
    except Exception:                                          # noqa: BLE001
        return _hungarian(cost)


# ---------------------------------------------------------------- 그래프 표현

class Tracks:
    """노드(t, z, y, x)와 엣지(source_id -> target_id)로 이루어진 계보 그래프."""

    def __init__(self, nodes: dict, edges: list):
        self.nodes = nodes                                     # node_id -> (t, z, y, x)
        self.edges = [(int(s), int(d)) for s, d in edges]
        self.by_t = defaultdict(list)
        for nid, (t, *_rest) in nodes.items():
            self.by_t[int(t)].append(nid)
        self.out = defaultdict(list)
        for s, d in self.edges:
            self.out[s].append(d)

    @staticmethod
    def from_rows(rows) -> "Tracks":
        """제출 CSV 의 행 목록(dict) -> Tracks. row_type 으로 노드/엣지를 가른다."""
        nodes, edges = {}, []
        for r in rows:
            if str(r["row_type"]).strip() == "node":
                nodes[int(r["node_id"])] = (int(r["t"]), float(r["z"]), float(r["y"]),
                                            float(r["x"]))
            else:
                edges.append((int(r["source_id"]), int(r["target_id"])))
        return Tracks(nodes, edges)

    def divisions(self) -> dict:
        """분열 노드 -> 딸 노드 목록 (나가는 엣지가 2개 이상)."""
        return {s: d for s, d in self.out.items() if len(d) >= 2}


def _dist_um(a, b) -> float:
    sz, sy, sx = SCALE_ZYX
    return math.sqrt(((a[1] - b[1]) * sz) ** 2 + ((a[2] - b[2]) * sy) ** 2
                     + ((a[3] - b[3]) * sx) ** 2)


def match_nodes(pred: Tracks, gt: Tracks) -> dict:
    """타임포인트마다 최적 이분 매칭. 예측 node_id -> 정답 node_id (7 µm 이내만)."""
    mapping = {}
    for t, gt_ids in gt.by_t.items():
        pred_ids = pred.by_t.get(t, [])
        if not pred_ids or not gt_ids:
            continue
        cost = np.full((len(pred_ids), len(gt_ids)), 1e6, dtype=float)
        for i, pid in enumerate(pred_ids):
            for j, gid in enumerate(gt_ids):
                d = _dist_um(pred.nodes[pid], gt.nodes[gid])
                if d <= MAX_MATCH_UM:
                    cost[i, j] = d
        for i, j in optimal_matching(cost):
            if cost[i, j] <= MAX_MATCH_UM:
                mapping[pred_ids[i]] = gt_ids[j]
    return mapping


# ---------------------------------------------------------------- 점수

def edge_counts(pred: Tracks, gt: Tracks, mapping: dict) -> tuple:
    """(TP, FP, FN). 가정 B: 매칭 안 된 예측 노드를 낀 엣지는 세지 않는다."""
    gt_edges = set(gt.edges)
    tp = fp = 0
    covered = set()
    for s, d in pred.edges:
        gs, gd = mapping.get(s), mapping.get(d)
        if gs is None or gd is None:
            continue                                            # sparse 라벨 -- 판단 보류
        if (gs, gd) in gt_edges:
            tp += 1
            covered.add((gs, gd))
        else:
            fp += 1
    fn = len(gt_edges) - len(covered)
    return tp, fp, fn


def node_penalty(pred: Tracks, gt: Tracks) -> float:
    """가정 A: 노드를 과다 예측하면 min(1, n_gt/n_pred) 를 곱한다."""
    n_pred, n_gt = len(pred.nodes), len(gt.nodes)
    if n_pred <= n_gt or n_pred == 0:
        return 1.0
    return n_gt / n_pred


def division_counts(pred: Tracks, gt: Tracks, mapping: dict) -> tuple:
    """(TP, FP, FN). 가정 C: 정답 분열 노드에 매칭된 예측 노드에서 나가는 엣지가
    두 딸 각각에 매칭된 노드로 닿으면 TP(1홉)."""
    rev = {}
    for p, g in mapping.items():
        rev.setdefault(g, p)                                    # 정답 -> 예측 (1:1 매칭)
    gt_div = gt.divisions()
    pred_div = pred.divisions()

    tp = 0
    matched_pred_parents = set()
    for gparent, gkids in gt_div.items():
        pparent = rev.get(gparent)
        if pparent is None:
            continue
        reached = {mapping.get(c) for c in pred.out.get(pparent, [])}
        if sum(1 for gk in gkids if gk in reached) >= 2:
            tp += 1
            matched_pred_parents.add(pparent)
    fn = len(gt_div) - tp
    # 예측이 분열이라 했는데 정답 분열에 대응되지 않은 것 -- 단, 정답에 라벨이 없는 노드는 제외
    fp = sum(1 for p in pred_div
             if p not in matched_pred_parents and mapping.get(p) is not None)
    return tp, fp, fn


def score_sample(pred: Tracks, gt: Tracks) -> dict:
    mapping = match_nodes(pred, gt)
    etp, efp, efn = edge_counts(pred, gt, mapping)
    denom = etp + efp + efn
    raw = (etp / denom) if denom else 0.0
    adj = raw * node_penalty(pred, gt)
    dtp, dfp, dfn = division_counts(pred, gt, mapping)
    return {"edge_tp": etp, "edge_fp": efp, "edge_fn": efn,
            "edge_jaccard_raw": raw, "edge_jaccard": adj, "edge_weight": denom,
            "div_tp": dtp, "div_fp": dfp, "div_fn": dfn,
            "matched_nodes": len(mapping), "pred_nodes": len(pred.nodes),
            "gt_nodes": len(gt.nodes)}


def score(pred_by_dataset: dict, gt_by_dataset: dict) -> dict:
    """표본별 edge Jaccard 는 (TP+FP+FN) 가중 평균, division 은 micro 평균.
    combined = (edge + division) / 2 -- 대회 설명의 '결합 지표'를 이렇게 읽었다."""
    per, wsum, wacc = {}, 0.0, 0.0
    dtp = dfp = dfn = 0
    for name, gt in gt_by_dataset.items():
        pred = pred_by_dataset.get(name) or Tracks({}, [])
        s = score_sample(pred, gt)
        per[name] = s
        wacc += s["edge_jaccard"] * s["edge_weight"]
        wsum += s["edge_weight"]
        dtp += s["div_tp"]; dfp += s["div_fp"]; dfn += s["div_fn"]
    edge = (wacc / wsum) if wsum else 0.0
    ddenom = dtp + dfp + dfn
    div = (dtp / ddenom) if ddenom else 0.0
    missing = sorted(set(gt_by_dataset) - set(pred_by_dataset))
    return {"combined": (edge + div) / 2.0, "edge_jaccard": edge, "division_jaccard": div,
            "division_tp": dtp, "division_fp": dfp, "division_fn": dfn,
            "missing_datasets": missing, "per_dataset": per}
