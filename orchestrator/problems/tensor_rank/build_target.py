"""표적 텐서를 만든다. 심판과 문제 기술서가 **같은 파일**을 읽게 하려는 것이다.

행렬곱 텐서 <n,m,p> 의 정의. C = A*B 에서 A 는 n x m, B 는 m x p, C 는 n x p 이고

    c_{ik} = sum_j a_{ij} b_{jk}

이다. 이것을 세 벡터공간의 텐서 하나로 적는다. alpha = (i,j), beta = (j,k),
gamma = (i,k) 로 색인을 평평하게 펴고

    T = sum_{i,j,k}  e_alpha (x) e_beta (x) e_gamma

라 두면, T 의 랭크 M 분해

    T = sum_{r=1}^{M} u_r (x) v_r (x) w_r

가 곧 **곱셈을 M 번만 쓰는 행렬곱 알고리즘**이다:

    m_r = (sum_alpha u_r[alpha] a_alpha) * (sum_beta v_r[beta] b_beta)
    c_gamma = sum_r w_r[gamma] m_r

확인. c_{ik} = sum_r w_r[(i,k)] * sum_{alpha,beta} u_r[alpha] v_r[beta] a_alpha b_beta
            = sum_{alpha,beta} a_alpha b_beta * T[alpha, beta, (i,k)]
            = sum_j a_{ij} b_{jk}   (T 의 정의에서 alpha=(i,j), beta=(j,k) 만 살아남는다)

<3,3,3> 을 고른 이유는 **답이 알려져 있지 않기 때문**이다. 문헌은 랭크가 19 이상
23 이하라는 것까지만 안다 -- 하한 19 는 Blaeser (1999/2003), 상한 23 은 Laderman (1976)
이다. 그 사이 다섯 값 중 어느 것이 참인지는 열려 있다.

사다리를 24 -> 23 -> 22 로 놓는다. 24 는 23 이 존재하므로 존재가 보장되고, 23 은
1976 년의 결과를 재현하는 것이며, **22 는 존재 여부 자체가 미지다.** 50 년 동안
손계산 · 수치최적화 · 충족문제 풀이 · 강화학습이 각자 시도했지만 아무도 22 를 찾지
못했고, 없다는 증명도 없다. 그러니 22 는 기존 방법을 잘 돌려서 닿는 자리가 아니다.

같이 넣는 두 case 는 심판을 검사하기 위한 것이다:

  w_state  랭크 3, **경계랭크(border rank) 2**. 계수를 발산시키면 2항으로 오차를 0 에
           임의로 가깝게 만들 수 있지만 정확히 0 으로는 못 만든다. 수치 최적화가 잔차만
           보고 "찾았다"고 말하는 지점이 정확히 여기다. 심판이 이것을 거부하지 못하면
           <3,3,3> 에서의 어떤 결과도 믿을 수 없다.
  mm222    랭크 7 (Strassen). **알려진 답이 있는 유일한 발판**이다. 전부 거부하는 심판도
           고장이므로, 통과해야 하는 case 가 하나는 있어야 한다.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def matmul_tensor(n: int, m: int, p: int) -> dict:
    """<n,m,p> 행렬곱 텐서. 0/1 성분만 n*m*p 개 있는 성긴 텐서다."""
    ent = []
    for i in range(n):
        for j in range(m):
            for k in range(p):
                ent.append([i * m + j, j * p + k, i * p + k, 1])
    return {"shape": [n * m, m * p, n * p], "entries": ent}


def w_tensor() -> dict:
    """W 상태. T = e0(x)e0(x)e1 + e0(x)e1(x)e0 + e1(x)e0(x)e0.

    랭크는 3, 경계랭크는 2 다. 후자는 다음 극한에서 나온다:

        (1/eps) * [ (e0+eps*e1)(x)(e0+eps*e1)(x)(e0+eps*e1) - e0(x)e0(x)e0 ]
        = T + O(eps)

    eps -> 0 이면 오차는 0 으로 가지만 계수는 1/eps 로 발산한다. 어떤 유한한 eps 에서도
    정확한 2항 분해는 아니다."""
    return {"shape": [2, 2, 2],
            "entries": [[0, 0, 1, 1], [0, 1, 0, 1], [1, 0, 0, 1]]}


def build() -> dict:
    return {
        "cases": [
            {"id": "w_state", "kind": "w", "budget": 3,
             "known": {"rank": 3, "border_rank": 2},
             "note": "랭크 3, 경계랭크 2 -- 계수 발산으로 2항에 임의로 가까워진다",
             **w_tensor()},
            {"id": "mm222", "kind": "matmul", "dims": [2, 2, 2], "budget": 7,
             "known": {"rank": 7},
             "note": "Strassen. 7 이 최적임이 증명되어 있다",
             **matmul_tensor(2, 2, 2)},
            {"id": "mm333", "kind": "matmul", "dims": [3, 3, 3], "budget": 24,
             "known": {"lower": 19, "upper": 23},
             "note": "열린 문제. 하한 19, 상한 23. 사다리는 24 -> 23 -> 22 이고 22 가 최종 "
                     "목표다. 24 는 23 이 있으므로 존재가 보장되고, 23 은 1976 년의 결과이며, "
                     "22 는 존재 여부 자체가 미지다 -- 50 년간 아무도 찾지 못했고 없다는 "
                     "증명도 없다",
             **matmul_tensor(3, 3, 3)},
        ],
        "lattice": {"coef_max": 8, "den_max": 12},
    }


def main() -> int:
    tgt = build()
    out = HERE / "target.json"
    out.write_text(json.dumps(tgt, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in tgt["cases"]:
        print(f"{c['id']:9} shape={c['shape']}  nnz={len(c['entries']):3}  "
              f"예산 M<={c['budget']}  기지={c['known']}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
