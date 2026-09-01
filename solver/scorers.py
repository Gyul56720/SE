"""
채점기 레지스트리 -- 도메인마다 다른 심판을 루프에 꽂는다.

improve.py 는 도메인을 모른다. config.json 의 "scorer" 이름으로 여기서 채점 함수를 찾아 쓴다.
채점 함수의 계약: evaluate(out_csv: Path, cfg: dict) -> dict 이고, 반환 dict 에는 반드시
"combined"(높을수록 좋음)가 있어야 한다. 루프는 그 값만으로 챔피언 교체를 판정한다.

이렇게 분리하는 이유: 세포 추적은 심판이 '데이터'(ground_truth.csv)였고, 텐서 rank 는 심판이
'수학적 정의'다. 전자는 데이터가 없으면 못 돌고, 후자는 데이터 없이 돈다. 같은 루프가 둘 다
돌게 하려면 심판만 갈아끼우면 되게 해야 한다.

"needs_ground_truth" 는 start.py 가 시작 전에 무엇을 요구할지 결정한다 -- 데이터 기반 심판은
정답 파일이 없으면 표류하므로 시작을 막고, 정의 기반 심판은 그 검사를 건너뛴다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "domains"))


def _cell_tracking(out_csv: Path, cfg: dict) -> dict:
    import metric
    import task as taskmod
    gt = taskmod.read_submission(Path(cfg["data_dir"]) / "train" / "ground_truth.csv")
    pred = taskmod.read_submission(out_csv)
    return metric.score(pred, gt)


def _tensor_rank(out_csv: Path, cfg: dict) -> dict:
    import tensor_rank as TR
    n = int(cfg.get("n", 2))
    s = TR.score_decomposition(TR.read_decomposition_csv(out_csv), n)
    # 루프는 "combined" 로 판정한다. 이 도메인의 점수를 그 이름으로 노출한다.
    return {"combined": s["score"], **s}


CELL_CONTRACT = (
    "출력 계약: def solve(data_dir, out_csv) 는 data_dir 안의 각 .zarr(또는 .npy) 를 읽어 "
    "out_csv 에 제출 형식(node/edge 행)으로 쓴다."
)

TENSOR_CONTRACT = (
    "이 과제는 데이터가 없다 -- 정답이 수학으로 정의된다(n×n 행렬곱 텐서). "
    "def solve(data_dir, out_csv) 는 data_dir/config.json 에서 n 을 읽고, out_csv 에 "
    "행렬곱 텐서의 저rank 분해를 쓴다. 데이터 파일은 읽지 않는다.\n"
    "출력 CSV 형식: 헤더 'kind,r,i,j,val' 다음, 각 항 r(0..rank-1)마다\n"
    "  U,r,i,-1,val  (좌행렬을 편 인덱스 i=0..n^2-1 의 계수)\n"
    "  V,r,i,-1,val  (우행렬)\n"
    "  W,r,i,-1,val  (결과행렬)\n"
    "  lambda,r,-1,-1,val\n"
    "편 인덱스 규약: A[i,k]->i*n+k, B[k,j]->k*n+j, C[i,j]->i*n+j. val 은 정수 또는 'a/b' 분수.\n"
    "채점: 분해가 정확 유리수 산술로 텐서를 재현하면 통과(틀리면 0점, 부분점수 없음). "
    "통과 시 rank 가 낮을수록 점수가 높다. 목표는 표준 n^3 보다 적은 곱셈 수(항 수)를 찾는 것 "
    "-- 2×2면 8을 7로 줄인 Strassen 이 유명한 예다. 항을 결합해 rank 를 낮춰라."
)

REGISTRY = {
    "cell_tracking": {"evaluate": _cell_tracking, "needs_ground_truth": True,
                      "baseline": "baseline.py", "contract": CELL_CONTRACT},
    "tensor_rank":   {"evaluate": _tensor_rank, "needs_ground_truth": False,
                      "baseline": "domains/tensor_baseline.py", "contract": TENSOR_CONTRACT},
}


def get(name: str) -> dict:
    if name not in REGISTRY:
        raise KeyError(f"알 수 없는 scorer '{name}'. 등록된 것: {sorted(REGISTRY)}")
    return REGISTRY[name]
