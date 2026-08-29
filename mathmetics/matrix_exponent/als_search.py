"""ALS 기반 CP 텐서 분해로 3x3 행렬곱 rank-23 정확해 수렴 여부를 확인하는 장시간 탐색."""
import numpy as np
import json
import time
import sys

def matmul_tensor(n):
    T = np.zeros((n*n, n*n, n*n))
    for i in range(n):
        for k in range(n):
            for j in range(n):
                T[i*n+k, k*n+j, i*n+j] = 1
    return T

def als_once(T, rank, iters, rng, l2=1e-8):
    n1, n2, n3 = T.shape
    A = rng.standard_normal((n1, rank))
    B = rng.standard_normal((n2, rank))
    C = rng.standard_normal((n3, rank))
    T1 = T.reshape(n1, n2*n3)
    T2 = T.transpose(1,0,2).reshape(n2, n1*n3)
    T3 = T.transpose(2,0,1).reshape(n3, n1*n2)
    I = np.eye(rank) * l2
    for it in range(iters):
        KR = np.einsum('ir,jr->ijr', B, C).reshape(n2*n3, rank)
        A = T1 @ KR @ np.linalg.inv(KR.T @ KR + I)
        KR = np.einsum('ir,jr->ijr', A, C).reshape(n1*n3, rank)
        B = T2 @ KR @ np.linalg.inv(KR.T @ KR + I)
        KR = np.einsum('ir,jr->ijr', A, B).reshape(n1*n2, rank)
        C = T3 @ KR @ np.linalg.inv(KR.T @ KR + I)
    Trec = np.einsum('ir,jr,kr->ijk', A, B, C)
    err = np.linalg.norm(Trec - T)
    return err, A, B, C

def main():
    n = 3
    rank = 23
    T = matmul_tensor(n)
    rng = np.random.default_rng(42)
    log_path = "mathmetics/matrix_exponent/logs/als_progress.jsonl"
    best_err = np.inf
    restart = 0
    start = time.time()
    max_seconds = 3300  # 55분, 다음 체크인 전에 안전하게 끝나도록
    while time.time() - start < max_seconds:
        restart += 1
        err, A, B, C = als_once(T, rank, iters=4000, rng=rng)
        improved = err < best_err
        if improved:
            best_err = err
            np.savez("mathmetics/matrix_exponent/logs/als_best_rank23.npz", A=A, B=B, C=C)
        record = {
            "ts": time.time(),
            "restart": restart,
            "err": float(err),
            "best_err": float(best_err),
            "elapsed_sec": round(time.time() - start, 1),
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        print(json.dumps(record), flush=True)
        if best_err < 1e-6:
            print("CONVERGED", flush=True)
            break

if __name__ == "__main__":
    main()
