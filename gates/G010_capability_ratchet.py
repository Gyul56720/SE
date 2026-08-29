"""
G010 -- 능력 래칫: 이미 도달 가능함이 증명된 기준을 후퇴시키는 커밋을 막는다.

이 게이트가 잡는 것은 특정 값(예: b=2 m=7)이 아니라 추론 실패의 '유형'이다:
에이전트가 어떤 변경을 "개선"이라 주장하면서, 정작 그 변경이 목표에 유리한지 측정하지 않아
'이미 되던 것'을 못 되게 만드는 것(그럴듯한 퇴보). 이번 세션 실측: SE가 CP-ALS에 리지
정규화를 넣고 "대폭 개선"이라 보고했으나, 실제로는 순수 ALS가 잔차 ~1e-13로 정확히 풀던
b=2 m=7 조차 1.3e-4에서 정체해 verifier 를 통과하지 못하게 만들었다. 근거 없는 개선
주장 -- G008(검증한다면 실제로 검산했음을 보여라), 무결성경고(저장했다면 원격에 있음을
보여라)와 같은 계열의 규율을 "개선했다면 기존 능력을 후퇴시키지 않았음을 보여라"로 확장한다.

동작: benchmarks.json 의 각 기준을, 현재 searcher/verifier 로 '넉넉한 예산'으로 재현
시도한다. 기준이 통과하면 OK. 통과 못 하면 후퇴로 보고 차단한다.

확률적 알고리즘과의 모순 방지 (중요): CP-ALS 는 restart 운에 따라 결과가 흔들린다. 그래서
이 게이트는 fail-closed 가 아니라 '관대'하게 설계한다 -- 넉넉한 seed/iter 예산으로 여러 번
시도해서 '한 번이라도' 통과하면 OK 로 본다. 예산 안에서 한 번도 못 하면 그때만 후퇴로
간주한다(진짜 능력 상실). 평가 자체가 불가능한 환경(numpy 없음, 파일 없음)에서는 조용히
건너뛴다. 이 관대함은 G007 의 '애매하면 통과' 철학과 같다.

계층: 이 게이트는 G008/G009(심판 자체의 무결성) 위에 얹힌다 -- 심판이 정직하다는 전제에서
'그 심판으로 잰 능력'이 후퇴했는지를 본다. 대상이 다르므로(verifier vs searcher) 겹치거나
모순되지 않는다. G005(대량 재작성 분량)가 못 잡는 '소량이지만 능력을 깨는 변경'을 메운다.
"""
from __future__ import annotations

import importlib.util
import json

RULE_ID = "G010"
TITLE = "이미 도달 가능한 기준을 후퇴시키지 않는가 (능력 래칫)"
ORIGIN = "2026-08-29 리지 정규화가 b=2 m=7 정확해 도달을 막은 '그럴듯한 퇴보'"
EVIDENCE = ""

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


def check(ctx) -> "list[str]":
    reg_path = (ctx.repo / _DIR / "benchmarks.json").resolve()
    searcher_path = (ctx.repo / _DIR / "searcher.py").resolve()
    verifier_path = (ctx.repo / _DIR / "verifier.py").resolve()
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
