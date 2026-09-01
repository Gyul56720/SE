# 가설: 출발점 -- 표준 n^3 알고리즘. 맞지만 rank 를 하나도 못 줄인다(score=1.0).
"""
텐서 rank 도메인의 베이스라인 solve. 표준 행렬곱 알고리즘을 그대로 분해로 낸다.

일부러 rank 를 안 줄인다. 바닥(맞는 분해, score 1.0)을 만들어 두는 것이 목적이다. LLM 은
여기서 항을 합쳐 rank 를 낮추는 것을 노린다 -- 2x2면 8->7(Strassen), 그 이하로.
정답은 수학으로 정의되므로 data_dir 의 데이터 파일은 읽지 않고 config.json 의 n 만 읽는다.
"""
import csv, json, os


def solve(data_dir: str, out_csv: str) -> None:
    cfg_path = os.path.join(data_dir, "config.json")
    n = 2
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as f:
            n = int(json.load(f).get("n", 2))
    rows = [("kind", "r", "i", "j", "val")]
    r = 0
    for i in range(n):
        for j in range(n):
            for k in range(n):
                a = i * n + k          # A[i,k]
                b = k * n + j          # B[k,j]
                c = i * n + j          # C[i,j]
                rows.append(("U", r, a, -1, 1))
                rows.append(("V", r, b, -1, 1))
                rows.append(("W", r, c, -1, 1))
                rows.append(("lambda", r, -1, -1, 1))
                r += 1
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
