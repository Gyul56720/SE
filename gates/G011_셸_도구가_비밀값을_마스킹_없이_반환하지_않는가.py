"""
G011 -- 셸 도구가 비밀값을 채널로 흘려보내지 않는가.

사고 유형(2026-09-02 분석 F4): 공개 채널은 화이트리스트가 없는데 run_shell은 임의 셸을
그대로 실행했다. 그래서 그 채널을 볼 수 있는 누구나 `cat .env` 한 줄로 Discord 봇 토큰과
Gemini API 키를 Discord로 뽑아낼 수 있었다. G004는 '커밋되는 파일'의 자격증명만 보므로
stdout으로 나가는 이 경로를 전혀 막지 못한다 -- 그래서 별도 게이트가 필요하다.

무엇을 잡는가:
  1. secret_filter.py 가 없거나 redact_secrets/child_env 가 사라짐.
  2. 마스킹이 실제로 동작하지 않음(행동 검증) -- 가짜 비밀값을 환경에 넣고 그 값이
     redact_secrets 출력에 그대로 남아 있으면 위반. 함수 이름만 남기고 속을 비우는
     '무력화'를 잡는다.
  3. bot_tools.run_shell 이 자식 환경 정리(env=child_env())를 하지 않거나, 출력을
     redact_secrets 로 거르지 않고 반환함.

무엇을 안 잡는가: 셸을 가진 상대가 값을 쪼개거나 다른 인코딩으로 내보내는 우회. 그건
게이트가 아니라 프로세스 격리(별도 사용자/컨테이너)의 몫이다. 여기서 지키는 것은
"한 줄로 새는 경로가 다시 열리지 않는다"는 것뿐이다.
"""
from __future__ import annotations

import ast
import importlib.util
import os
import sys

RULE_ID = "G011"
TITLE = "셸 도구가 비밀값을 마스킹 없이 반환하지 않는가"
ORIGIN = "2026-09-02 분석 F4 (공개 채널 run_shell 비밀값 유출 경로)"
EVIDENCE = "reports/20260902_agent_analysis.md"

_FILTER_REL = "secret_filter.py"
_TOOLS_REL = "bot_tools.py"


def _load_filter(repo):
    """검사 대상 저장소의 secret_filter 를 그 저장소 기준으로 임포트한다."""
    path = repo / _FILTER_REL
    sys.path.insert(0, str(repo))
    try:
        spec = importlib.util.spec_from_file_location("_g011_secret_filter", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(repo))


def _run_shell_body(repo) -> "ast.FunctionDef | None":
    try:
        tree = ast.parse((repo / _TOOLS_REL).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run_shell":
            return node
    return None


def check(ctx) -> "list[str]":
    violations: list[str] = []
    repo = ctx.repo

    if not (repo / _FILTER_REL).is_file():
        return [f"{_FILTER_REL} 이(가) 없다 -- 셸 출력에서 비밀값을 지우는 유일한 지점이다. "
                f"이게 없으면 공개 채널에서 `cat .env` 한 줄로 토큰이 새어 나간다."]

    # 1) 행동 검증: 가짜 비밀을 넣고 실제로 지워지는지 본다. 이름만 남은 껍데기를 잡는다.
    canary_name, canary_value = "G011_CANARY_API_KEY", "canary-secret-value-0123456789"
    previous = os.environ.get(canary_name)
    os.environ[canary_name] = canary_value
    try:
        mod = _load_filter(repo)
    except Exception as e:
        return [f"{_FILTER_REL} 를 임포트할 수 없다: {type(e).__name__}: {e}"]
    finally:
        if previous is None:
            os.environ.pop(canary_name, None)
        else:
            os.environ[canary_name] = previous

    for fn in ("redact_secrets", "child_env"):
        if not hasattr(mod, fn):
            violations.append(f"{_FILTER_REL}: '{fn}' 이(가) 없다 -- run_shell 이 이 함수를 부른다.")
    if violations:
        return violations

    os.environ[canary_name] = canary_value
    try:
        masked = mod.redact_secrets(f"leak={canary_value}")
    except Exception as e:
        return [f"{_FILTER_REL}: redact_secrets 가 예외로 죽는다: {type(e).__name__}: {e}"]
    finally:
        if previous is None:
            os.environ.pop(canary_name, None)
        else:
            os.environ[canary_name] = previous
    if canary_value in masked:
        violations.append(
            f"{_FILTER_REL}: redact_secrets 가 환경변수 {canary_name} 의 값을 지우지 못했다 "
            f"-- 마스킹이 무력화됐다.")

    # 2) run_shell 이 실제로 두 겹을 다 쓰는가.
    fn = _run_shell_body(repo)
    if fn is None:
        violations.append(f"{_TOOLS_REL}: run_shell 을 찾을 수 없다.")
        return violations
    src = ast.unparse(fn)
    if "child_env()" not in src:
        violations.append(
            f"{_TOOLS_REL}: run_shell 이 자식 프로세스 환경을 정리하지 않는다"
            f"(env=child_env() 가 없다) -- 공개 채널에서 printenv 로 키가 그대로 나간다.")
    if src.count("redact_secrets") < 2:
        violations.append(
            f"{_TOOLS_REL}: run_shell 이 stdout/stderr 를 redact_secrets 로 거르지 않고 "
            f"반환한다 -- `cat .env` 결과가 그대로 채널에 실린다.")
    return violations
