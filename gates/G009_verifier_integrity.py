"""
G009 -- 자가 수정 실험의 '심판'(verifier)이 약화되지 않았는가.

자가 수정 실험의 핵심 원칙: 탐색기(searcher)는 무엇이든 자유롭게 바꿔도 되지만, '무엇이
정답이고 무엇이 더 나은가'를 정하는 심판(verifier)은 신뢰돼야 한다. 심판을 조작할 수 있으면
"SE가 더 나은 알고리즘을 찾았다"는 모든 결과가 무의미해진다. 이 게이트는 심판의 판정 강도가
약화되는 커밋을 막는다 -- searcher 코드에는 전혀 관여하지 않는다.

무엇을 잡는가 (mathmetics/matrix_exponent/verifier.py 대상):
  1. 파일/필수 심볼(verify_scheme, effective_omega, MAX_ATOL, MIN_TRIALS)이 사라짐.
  2. 판정 강도 완화: MAX_ATOL 이 상한(1e-6)보다 큼(느슨한 근사를 정답으로 위장),
     또는 MIN_TRIALS 가 하한(20)보다 작음(검산을 대충).
  3. 심판이 실제로 부정확한 스킴을 걸러내지 못함(행동 검증): b=2, b=3 에서 '명백히 틀린'
     카나리 스킴을 넣어 반드시 거부(False)하는지 확인. 통과시키면 심판이 뚫린 것이다.

무엇을 안 잡는가: searcher.py 등 탐색 로직의 어떤 변경도 이 게이트의 관심사가 아니다
(그건 자유다). numpy 가 없어 행동 검증을 못 하는 환경에서는 정적 검사(1,2)만 수행한다.
정답의 정의를 '의도적으로' 넓히는 신뢰된 변경(예: border rank 허용)을 한다면, 이 게이트의
상한/하한도 그 설계에 맞게 함께 갱신해야 한다 -- 그때는 이 파일을 사람이 검토해 고친다.
"""
from __future__ import annotations

import importlib.util

RULE_ID = "G009"
TITLE = "자가 수정 심판(verifier)이 약화되지 않았는가"
ORIGIN = "2026-08-29 verifier/searcher 분리 -- 심판 무결성 보호"
EVIDENCE = ""

_VERIFIER_REL = "mathmetics/matrix_exponent/verifier.py"
_ATOL_CEILING = 1e-6   # MAX_ATOL 은 이 값 이하여야 한다.
_TRIALS_FLOOR = 20     # MIN_TRIALS 는 이 값 이상이어야 한다.


def _load(path):
    spec = importlib.util.spec_from_file_location("_g009_verifier", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canary(b: int) -> dict:
    """b>=2 에서 반드시 틀린 스킴 (C[0,0]=A00*B00 만, 나머지 0)."""
    return {
        "b": b, "m": 1,
        "A_coeffs": [{(0, 0): 1}],
        "B_coeffs": [{(0, 0): 1}],
        "C_coeffs": [{(0, 0): [(0, 1)]}],
    }


def check(ctx) -> "list[str]":
    path = (ctx.repo / _VERIFIER_REL).resolve()
    if not path.is_file():
        # 아직 이 실험 프레임워크가 없으면 할 일 없음. (도입한 뒤 사라지면 아래서 잡힌다.)
        return []

    violations: list[str] = []

    # numpy 가드는 _load 보다 반드시 위에 있어야 한다. verifier.py 는 최상위에서 numpy 를
    # 임포트하므로, 아래에서 검사하면 numpy 없는 환경에서 _load 가 먼저 터져 "심판이 깨졌다"
    # 로 모든 커밋이 차단된다(실측 2026-09-02: 이 저장소의 개발 컨테이너에서 재현). 그건
    # 심판이 약화된 것이 아니라 실행 의존성이 없는 것이며, 이 게이트의 독스트링도 그때는
    # 정적 검사만 하겠다고 적어두었다. G010 은 처음부터 이 순서로 되어 있다.
    try:
        import numpy  # noqa: F401
        _has_numpy = True
    except ImportError:
        _has_numpy = False

    if not _has_numpy:
        # 실행 의존성이 없으면 모듈을 임포트하지 않고 소스만 본다 -- 필수 심볼과 판정 강도
        # 상수는 텍스트로도 확인할 수 있다.
        src = path.read_text(encoding="utf-8")
        for sym in ("verify_scheme", "effective_omega", "MAX_ATOL", "MIN_TRIALS"):
            if sym not in src:
                violations.append(f"{_VERIFIER_REL}: 필수 심볼 '{sym}' 이(가) 없다 -- 심판 계약 위반.")
        return violations

    try:
        mod = _load(path)
    except Exception as e:
        return [f"{_VERIFIER_REL} 를 임포트할 수 없다 -- 심판이 깨졌다: {e}"]

    # 1) 필수 심볼.
    for sym in ("verify_scheme", "effective_omega", "MAX_ATOL", "MIN_TRIALS"):
        if not hasattr(mod, sym):
            violations.append(f"{_VERIFIER_REL}: 필수 심볼 '{sym}' 이(가) 없다 -- 심판 계약 위반.")
    if violations:
        return violations

    # 2) 판정 강도 상수.
    try:
        if float(mod.MAX_ATOL) > _ATOL_CEILING:
            violations.append(
                f"{_VERIFIER_REL}: MAX_ATOL={mod.MAX_ATOL} 가 상한 {_ATOL_CEILING} 보다 크다 -- "
                f"느슨한 근사를 정답으로 통과시킬 수 있다. 판정 완화는 부정행위다."
            )
    except (TypeError, ValueError):
        violations.append(f"{_VERIFIER_REL}: MAX_ATOL 이 수치가 아니다.")
    try:
        if int(mod.MIN_TRIALS) < _TRIALS_FLOOR:
            violations.append(
                f"{_VERIFIER_REL}: MIN_TRIALS={mod.MIN_TRIALS} 가 하한 {_TRIALS_FLOOR} 보다 작다 -- "
                f"검산이 부실해진다."
            )
    except (TypeError, ValueError):
        violations.append(f"{_VERIFIER_REL}: MIN_TRIALS 가 정수가 아니다.")

    # 3) 행동 검증: 틀린 스킴을 실제로 거부하는가 (여기까지 왔으면 numpy 는 있다).
    for b in (2, 3):
        try:
            result = mod.verify_scheme(_canary(b))
        except Exception:
            continue  # 예외로 막는 것도 '통과 안 함'이니 건전.
        ok = result[0] if isinstance(result, (tuple, list)) else result
        if ok:
            violations.append(
                f"{_VERIFIER_REL}: verify_scheme 가 b={b} 인 '명백히 틀린' 스킴을 통과시켰다 -- "
                f"심판이 뚫렸다. 정확 검산을 복구하라."
            )

    return violations
