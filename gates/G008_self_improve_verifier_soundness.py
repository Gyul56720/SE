"""
G008 -- 자가 수정 프레임워크의 검증기(verifier)가 "아무것도 검산하지 않고 통과"할 수 있는가.

사고: 2026-08-29. SE 에이전트가 mathmetics/matrix_exponent/ 에 자가 수정 프레임워크를
직접 작성하고, "안전장치(롤백) 검증 완료"라고 보고했다. 그런데 검증은 b=2 스킴 하나로만
했고, verify_scheme(skeleton.py)의 기본 테스트 크기가 sizes=(2,4,8)로 하드코딩돼 있었다.
탐색 목표인 b=3 스킴을 넣으면 2,4,8 모두 3으로 나눠지지 않아 `size % b != 0: continue`로
전부 건너뛰고, 단 한 번도 검산하지 않은 채 (True,"ok")를 반환한다(vacuous truth). 그러면
self_improve_loop이 '틀린' b=3 알고리즘을 omega_eff가 더 낮다는 이유로 NEW_BEST로 채택하고
_last_good_skeleton까지 오염시킨다 -- 안전장치 전체가 조용히 무력화된다.

추론 오류의 뿌리: (1) 성공 케이스 하나(b=2)만 확인하고 전체로 일반화, (2) 경계조건
(size가 b로 안 나눠지는 경우) 미검증, (3) 검증기가 True를 리턴한 것만 보고 '무엇을 몇 번
검산했는가'는 안 봄. 이 진단을 메모리 노트로 남겨도 다음에 안 읽으면 또 반복된다 -- 그래서
커밋 경로 위의 게이트로 강제한다.

무엇을 잡는가:
  self_improve_loop이 실제로 호출하는 방식 그대로(verify_scheme(scheme), sizes 인자 없이)
  탐색 대상이 될 수 있는 b 값들(현재 SCHEME의 b + 2..5)에 대해 각각 '일부러 틀린'
  카나리(canary) 스킴을 만들어 넣는다. 건전한 검증기라면 어떤 b에서든 반드시 False를 돌려줘야
  한다. 어떤 b에서 True를 돌려주면 = 그 b에서 검산을 하나도 안 한다는 뜻이므로 위반으로 막는다.
  현재 SCHEME이 아직 b=2라도, verify가 b=3에서 vacuous하면 '지금' 잡는다 -- SE가 b=3으로
  바꾼 뒤에야 잡으면 이미 오염이 시작된 뒤다.

무엇을 안 잡는가: numpy 등 실행 의존성이 없어 프레임워크를 아예 돌릴 수 없는 환경에서는
평가를 생략한다(코드 결함이 아니라 환경 문제이므로). 프레임워크 파일 자체가 없으면 조용히
통과한다.
"""
from __future__ import annotations

import importlib.util

RULE_ID = "G008"
TITLE = "자가 수정 검증기가 검산 0회로 통과하지 않는가 (vacuous verify 방지)"
ORIGIN = "2026-08-29 matrix_exponent b=3 vacuous-verify 안전장치 우회"
EVIDENCE = ""

# 프레임워크가 늘어나도 재사용되도록, 검사할 (스켈리톤 파일, SCHEME속성, verify함수명) 계약을
# 목록으로 둔다. 새 self-improve 모듈이 생기면 여기에 한 줄 추가하면 된다.
_TARGETS = [
    ("mathmetics/matrix_exponent/skeleton.py", "SCHEME", "verify_scheme"),
]


def _load_module(path):
    spec = importlib.util.spec_from_file_location(f"_g008_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_canary(b: int) -> dict:
    """b x b 블록에서 '반드시 틀린' 스킴. C[0,0]=A00*B00 만 채우고 나머지는 0으로 둔다 --
    b>=2 이면 A@B 와 절대 같을 수 없으므로, 제대로 검산하는 verifier라면 무조건 False."""
    return {
        "b": b,
        "m": 1,
        "A_coeffs": [{(0, 0): 1}],
        "B_coeffs": [{(0, 0): 1}],
        "C_coeffs": [{(0, 0): [(0, 1)]}],
    }


def check(ctx) -> "list[str]":
    violations: list[str] = []

    for rel_path, scheme_attr, verify_name in _TARGETS:
        path = (ctx.repo / rel_path).resolve()
        if not path.is_file():
            continue  # 프레임워크가 없으면 이 게이트는 할 일이 없다.

        try:
            import numpy  # noqa: F401
        except ImportError:
            # 실행 의존성이 없어 행동 검증 불가 -- 환경 문제이지 코드 결함이 아니다.
            continue

        try:
            mod = _load_module(path)
        except Exception as e:
            violations.append(
                f"{rel_path} 를 임포트할 수 없어 검증기 건전성을 확인하지 못했다 -- {e}"
            )
            continue

        scheme = getattr(mod, scheme_attr, None)
        verify = getattr(mod, verify_name, None)
        if scheme is None or not callable(verify):
            violations.append(
                f"{rel_path}: '{scheme_attr}' 또는 '{verify_name}()' 계약이 없다 -- "
                f"자가 수정 프레임워크의 검증기 계약이 깨졌다."
            )
            continue

        try:
            current_b = int(scheme["b"])
        except Exception as e:
            violations.append(f"{rel_path}: {scheme_attr}['b'] 를 읽을 수 없다 -- {e}")
            continue

        if current_b < 2:
            violations.append(
                f"{rel_path}: {scheme_attr}['b']={current_b} -- 블록 크기는 2 이상이어야 한다."
            )
            continue

        # 현재 b + 탐색 범위(2..5)를 모두 찔러서 잠재 결함을 지금 잡는다.
        for b in sorted({current_b, 2, 3, 4, 5}):
            # self_improve_loop이 부르는 방식 그대로: verify(scheme) -- sizes 인자 없이.
            canary = _make_canary(b)
            try:
                result = verify(canary)
            except Exception:
                # 틀린 스킴에서 예외를 던지는 건 '통과시키지 않음'이므로 건전하다.
                continue

            ok = result[0] if isinstance(result, (tuple, list)) else result
            if ok:
                violations.append(
                    f"{rel_path}: {verify_name}() 가 b={b} 인 '명백히 틀린' 스킴을 통과시켰다 "
                    f"(vacuous verify). 기본 테스트 크기가 b로 나눠지지 않아 검산을 0회 하고 "
                    f"통과하는 것으로 보인다 -- self_improve_loop이 b={b} 틀린 알고리즘을 "
                    f"NEW_BEST로 채택할 수 있다. verify 가 이 b의 거듭제곱 크기(b, b^2, ...)를 "
                    f"실제로 검산하고, 검산 대상이 0개면 실패를 반환하도록 고쳐라."
                )

    return violations
