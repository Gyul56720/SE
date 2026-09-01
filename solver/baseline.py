"""
출발점 해법 -- 사람이 쓴 바닥. LLM 이 개선할 대상이자, 루프의 첫 비교 기준이다.

일부러 단순하고, 일부러 numpy 만으로 돈다. 이유가 둘이다:
  1. 챔피언이 없으면 '개선'이라는 말이 성립하지 않는다. 점수가 낮아도 바닥이 있어야 한다.
  2. 이 환경에 scipy/skimage/zarr 가 없을 수 있다. 무거운 의존성을 깔고 시작하면 루프가
     첫 반복부터 임포트 오류로 죽는다. 있으면 쓰고 없으면 물러서는 경로를 둔다.

파이프라인 (전부 고전적, GPU 불필요):
    검출  -- 타임포인트마다 상위 분위수로 이진화하고, 국소 최대점을 비최대 억제로 골라
             세포 중심 후보를 만든다.
    연결  -- 인접 프레임 사이를 스케일된 물리 거리 기준 최적 이분 매칭으로 잇는다.
             (탐욕 최근접이 아니라 전역 최적 배정이다 -- 밀집 구간에서 차이가 크다.)
    분열  -- 배정되지 않고 남은 다음 프레임 노드가 어떤 부모 근처에 있으면 두 번째 딸로 붙인다.
             부모 하나가 딸 둘을 가지면 그 노드가 division 이 된다.

여기서 명백히 약한 곳(= LLM 이 노릴 곳):
  - 검출 임계값이 고정 분위수다. 밝기 분포가 다른 데이터셋에서 무너진다.
  - 세포 크기·모양을 전혀 안 본다. 붙어 있는 두 세포를 하나로 셀 수 있다.
  - 연결이 한 프레임만 본다. 한 프레임 놓치면 계보가 끊긴다(gap closing 없음).
  - 분열 판정이 거리 하나뿐이다. 밝기 변화나 모양 변화를 안 본다.
"""
from __future__ import annotations

import csv
import math
import os
import sys

import numpy as np

SCALE_ZYX = (1.625, 0.40625, 0.40625)     # µm / voxel (대회 명세)
MAX_LINK_UM = 7.0                          # 프레임 간 이동 상한 (매칭 상한과 같은 값에서 출발)
DETECT_PERCENTILE = 99.3
MIN_SEP_VOXEL = 6                          # 비최대 억제 반경 (y/x 기준)


# ---------------------------------------------------------------- 입력

def load_volume(path: str):
    """(T, Z, Y, X) 배열로 읽는다. .zarr 는 zarr 로, .npy 는 numpy 로."""
    if path.endswith(".npy"):
        return np.load(path)
    import zarr                                     # 없으면 여기서 명확히 터진다
    z = zarr.open(path, mode="r")
    arr = z if hasattr(z, "shape") else z[list(z.array_keys())[0]]
    a = np.asarray(arr)
    while a.ndim > 4:                               # (T,C,Z,Y,X) 같은 경우 채널 축 축소
        a = a.max(axis=1)
    return a


def find_inputs(data_dir: str) -> list:
    out = []
    for name in sorted(os.listdir(data_dir)):
        if name.endswith(".zarr") or name.endswith(".npy"):
            out.append((name.rsplit(".", 1)[0], os.path.join(data_dir, name)))
    return out


# ---------------------------------------------------------------- 검출

def detect(vol3d: np.ndarray) -> list:
    """한 타임포인트의 (z, y, x) 중심 후보. 상위 분위수 이진화 + 비최대 억제."""
    v = np.asarray(vol3d, dtype=np.float32)
    if v.size == 0:
        return []
    thr = np.percentile(v, DETECT_PERCENTILE)
    idx = np.argwhere(v >= thr)
    if idx.size == 0:
        return []
    vals = v[idx[:, 0], idx[:, 1], idx[:, 2]]
    order = np.argsort(-vals)
    idx = idx[order]

    # 비최대 억제: 밝은 것부터 집고, 이미 집은 중심에 가까우면 버린다.
    picked = []
    sz, sy, sx = SCALE_ZYX
    rad_um = MIN_SEP_VOXEL * sy
    for p in idx:
        pz, py, px = float(p[0]), float(p[1]), float(p[2])
        ok = True
        for q in picked:
            d = math.sqrt(((pz - q[0]) * sz) ** 2 + ((py - q[1]) * sy) ** 2
                          + ((px - q[2]) * sx) ** 2)
            if d < rad_um:
                ok = False
                break
        if ok:
            picked.append((pz, py, px))
        if len(picked) >= 4000:                     # 폭주 방지
            break
    return picked


# ---------------------------------------------------------------- 연결

def _dist_um(a, b) -> float:
    sz, sy, sx = SCALE_ZYX
    return math.sqrt(((a[0] - b[0]) * sz) ** 2 + ((a[1] - b[1]) * sy) ** 2
                     + ((a[2] - b[2]) * sx) ** 2)


# 헝가리안을 이 파일 안에 들고 있는 이유: 이 코드는 후보로 복사돼 다른 디렉토리에서
# 실행된다. solver/metric.py 를 상대 임포트하면 그 순간 깨지고, LLM 이 만든 모든 수정본이
# 똑같이 실패한다(실측으로 잡았다). 해법 코드는 자립해야 한다.
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


def _assign(cost: np.ndarray) -> list:
    try:
        from scipy.optimize import linear_sum_assignment
        r, c = linear_sum_assignment(cost)
        return list(zip(r.tolist(), c.tolist()))
    except Exception:                               # noqa: BLE001
        return _hungarian(cost)


def link(prev_pts: list, cur_pts: list) -> tuple:
    """(배정 목록, 남은 현재 프레임 인덱스). 전역 최적 배정 후 상한 밖은 버린다."""
    if not prev_pts or not cur_pts:
        return [], list(range(len(cur_pts)))
    cost = np.full((len(prev_pts), len(cur_pts)), 1e6, dtype=float)
    for i, a in enumerate(prev_pts):
        for j, b in enumerate(cur_pts):
            d = _dist_um(a, b)
            if d <= MAX_LINK_UM:
                cost[i, j] = d
    pairs = [(i, j) for i, j in _assign(cost) if cost[i, j] <= MAX_LINK_UM]
    used = {j for _, j in pairs}
    return pairs, [j for j in range(len(cur_pts)) if j not in used]


def attach_divisions(prev_pts: list, cur_pts: list, pairs: list, leftover: list) -> list:
    """배정 안 된 현재 노드를 가장 가까운 부모에 두 번째 딸로 붙인다 -> 그 부모가 division."""
    extra = []
    for j in leftover:
        best_i, best_d = None, MAX_LINK_UM
        for i, _ in pairs:
            d = _dist_um(prev_pts[i], cur_pts[j])
            if d < best_d:
                best_i, best_d = i, d
        if best_i is not None:
            extra.append((best_i, j))
    return extra


# ---------------------------------------------------------------- 전체

def track(vol: np.ndarray) -> tuple:
    """(T,Z,Y,X) -> (nodes, edges). nodes: id -> (t,z,y,x)."""
    nodes, edges = {}, []
    next_id = 1
    prev_pts, prev_ids = [], []
    for t in range(vol.shape[0]):
        pts = detect(vol[t])
        ids = []
        for (z, y, x) in pts:
            nodes[next_id] = (t, z, y, x)
            ids.append(next_id)
            next_id += 1
        pairs, leftover = link(prev_pts, pts)
        for i, j in pairs:
            edges.append((prev_ids[i], ids[j]))
        for i, j in attach_divisions(prev_pts, pts, pairs, leftover):
            edges.append((prev_ids[i], ids[j]))
        prev_pts, prev_ids = pts, ids
    return nodes, edges


def solve(data_dir: str, out_csv: str) -> None:
    rows = []
    i = 0
    for name, path in find_inputs(data_dir):
        vol = load_volume(path)
        if vol.ndim == 3:                            # (Z,Y,X) 한 장이면 T=1 로 본다
            vol = vol[None]
        nodes, edges = track(vol)
        for nid, (t, z, y, x) in nodes.items():
            rows.append([i, name, "node", nid, int(t), int(round(z)), int(round(y)),
                         int(round(x)), -1, -1])
            i += 1
        for s, d in edges:
            rows.append([i, name, "edge", -1, -1, -1, -1, -1, s, d])
            i += 1
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "dataset", "row_type", "node_id", "t", "z", "y", "x",
                    "source_id", "target_id"])
        w.writerows(rows)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용: python3 baseline.py <data_dir> <out.csv>", file=sys.stderr)
        raise SystemExit(2)
    solve(sys.argv[1], sys.argv[2])
    print(f"제출 파일을 썼다: {sys.argv[2]}")
