"""
능력 래칫 -- 이미 도달 가능함이 증명된 기준을 후퇴시켰는지 검사한다.

원래 커밋 게이트(G010)였다. 개념은 그대로 두고 **자리만 옮겼다**: 이 검사는 b=2 에서
seed 12개 x 2000 iter 의 CP-ALS 를 실제로 돌린다. 그걸 매 커밋 경로에서 하면 Discord 응답
뒤 git_sync 가 GIT_MUTEX 를 쥔 채 수 초~수십 초를 쓰고, 그 사이 다른 스레드의 저장이 밀린다.
탐색 결과의 후퇴는 커밋 단위로 확인해야 할 성질도 아니다 -- 루프가 밤새 도는 동안 재보면 된다.

그래서 이제 이 검사는 커밋을 막지 않고, scripts/check_improve.sh(서버 상태 점검)와 수동
실행으로 돈다. 커밋 경로에는 심판 자체의 무결성을 보는 G009(싸다, ~0ms)만 남는다.

무엇을 보는가: benchmarks.json 의 각 기준을 현재 searcher/verifier 로 넉넉한 예산으로
재현 시도한다. 한 번이라도 통과하면 능력 유지(확률적 알고리즘이므로 관대하게 본다).
예산 안에서 한 번도 못 하면 그때만 후퇴로 보고 exit 1.

사용:
    python3 scripts/capability_ratchet.py         # 통과 0 / 후퇴 1
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

_DIR = "mathmetics/matrix_exponent"
# 관대한 예산: 여러 seed 로 재현 시도, '한 번이라도' 통과하면 능력 유지로 인정.
_MATMUL_BUDGET = {2: {"seeds": 12, "iters": 2000}}   # b별 예산 (b=2 는 확실히 도달 가능)


def _load(path):
    spec = importlib.util.spec_from_file_location(f"_g010_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _check_matmul_scheme(searcher, verifier, bench) -> str:
    """b,m 기준을 넉넉한 예산으로 재현 시도. 한 번이라도 verifier 통과하면 '' (OK),
    예산 내내 실패하면 후퇴 사유 반환."""
    b, m = int(bench["b"]), int(bench["m"])
    budget = _MATMUL_BUDGET.get(b, {"seeds": 8, "iters": 1500})
    T = searcher.matmul_tensor(b)
    best = 1.0
    for seed in range(budget["seeds"]):
        U, V, W, res = searcher.cp_als(T, m, iters=budget["iters"], seed=seed)
        best = min(best, res)
        if res < 1e-9:
            scheme = searcher.factors_to_scheme(U, V, W, b, m)
            ok, _ = verifier.verify_scheme(scheme)
            if ok:
                return ""  # 능력 유지 확인.
    return (f"기준 '{bench['id']}' (b={b}, m={m}) 을 넉넉한 예산"
            f"(seeds={budget['seeds']}, iters={budget['iters']})으로도 재현하지 못했다 "
            f"(최소 잔차 {best:.2e}). searcher 변경이 '이미 되던' 능력을 후퇴시킨 것으로 보인다 "
            f"-- 변경이 정말 개선인지 측정했는가? 후퇴시키는 변경(예: 정확해를 편향시키는 "
            f"정규화)을 되돌리거나 고쳐라.")


def run(repo) -> "list[str]":
    reg_path = (repo / _DIR / "benchmarks.json").resolve()
    searcher_path = (repo / _DIR / "searcher.py").resolve()
    verifier_path = (repo / _DIR / "verifier.py").resolve()
    if not (reg_path.is_file() and searcher_path.is_file() and verifier_path.is_file()):
        return []  # 프레임워크가 없으면 할 일 없음.

    try:
        import numpy  # noqa: F401
    except ImportError:
        return []  # 실행 의존성 없으면 평가 불가 -- 조용히 건너뛴다.

    try:
        registry = json.loads(reg_path.read_text(encoding="utf-8"))
        benches = registry.get("benchmarks", [])
    except Exception as e:
        return [f"{_DIR}/benchmarks.json 을 읽을 수 없다: {e}"]

    try:
        searcher = _load(searcher_path)
        verifier = _load(verifier_path)
    except Exception as e:
        return [f"{_DIR} 모듈 임포트 실패로 능력 래칫을 확인하지 못했다: {e}"]

    violations: list[str] = []
    for bench in benches:
        kind = bench.get("kind")
        if kind == "matmul_scheme":
            # searcher 가 계약(matmul_tensor/cp_als/factors_to_scheme)을 지켜야 재현 가능하다.
            if not all(hasattr(searcher, fn) for fn in ("matmul_tensor", "cp_als", "factors_to_scheme")):
                violations.append(
                    f"기준 '{bench['id']}' 재현에 필요한 searcher 계약"
                    f"(matmul_tensor/cp_als/factors_to_scheme)이 없다 -- 능력 래칫을 확인할 수 없다.")
                continue
            msg = _check_matmul_scheme(searcher, verifier, bench)
            if msg:
                violations.append(msg)
        # 다른 kind 는 미지원 -- 조용히 건너뛴다(새 유형은 여기에 추가).
    return violations


def main() -> int:
    violations = run(REPO)
    if not violations:
        print("[능력 래칫] 후퇴 없음 -- 등록된 기준을 모두 재현했다(또는 평가 불가 환경).")
        return 0
    print("[능력 래칫] 후퇴 감지")
    for v in violations:
        print(f"  - {v}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
