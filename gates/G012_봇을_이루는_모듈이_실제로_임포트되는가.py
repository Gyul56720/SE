"""
G012 -- 봇을 이루는 모듈이 실제로 임포트되는가.

이 게이트가 G001(독스트링 자리) / G002(임포트 순환) / G006(정의 전 이름 참조)을 대체한다.
셋 다 같은 하나의 실패를 AST로 근사하던 것이었다: **고친 코드를 임포트해보지 않고 push해서
봇이 기동 단계에서 죽는다.** 근사는 근사라서, 셋을 다 통과해도 죽는 방법은 얼마든지 남았다
(오타 난 임포트, 최상위에서 터지는 표현식, 잘못된 데코레이터 인자 …).

사고 기록 그대로:
  - b32aa78 (2026-08-28) 게스트 가드를 `def` 다음 줄에 끼워 독스트링이 사라졌고 langchain의
    @tool 이 "Function must have a docstring" 으로 거부해 봇 전체가 임포트 불가가 됐다.
    같은 커밋에서 agent_memory / public_agent_files 가 bot_tools 와 순환을 만들었다.
  - 1a82685 (2026-08-28) `@client.event` 가 `client` 대입보다 위에 있어 NameError.
  - 그 직전 20:35 에 에이전트 자신이 "py_compile 은 문법만 잡는다, 임포트를 해봐야 한다"를
    메모로 저장하고 20:37 에 임포트 불가 코드를 push 했다. 진단은 처음부터 옳았다 --
    그 진단을 그대로 실행하는 검사가 없었을 뿐이다. 이 게이트가 그 진단이다.

동작: 각 모듈을 **별도 프로세스**에서 임포트해본다(임포트 부작용이 게이트 프로세스를
오염시키지 않게). 봇 진입점(discord_bot_server / main_public)은 임포트만으로 에이전트 풀을
만들므로, 더미 환경변수와 GEMINI_MODEL_POOL 을 넣어 **네트워크 호출 없이** 임포트되게 한다
(모델 목록을 명시하면 build_agent_pool 이 list_available_models 를 부르지 않는다).
봇 실행은 `if __name__ == "__main__"` 가드가 막는다.

무엇을 위반으로 보는가: 코드 결함으로 임포트가 실패하는 것 -- ImportError(순환 포함),
NameError, ValueError(@tool 독스트링 없음이 여기다), SyntaxError, AttributeError, TypeError,
IndentationError.
무엇을 건너뛰는가: 서드파티 미설치(ModuleNotFoundError 중 저장소 밖 모듈), 설정 누락
(KeyError), 네트워크/파일 오류(OSError). 그건 코드가 깨진 게 아니라 환경이 다른 것이다 --
G009/G010 이 numpy 없을 때 건너뛰는 것과 같은 이유다.
"""
from __future__ import annotations

import os
import subprocess
import sys

RULE_ID = "G012"
TITLE = "봇을 이루는 모듈이 실제로 임포트되는가"
ORIGIN = "b32aa78, 1a82685"
EVIDENCE = "public_agent_memory/20260828-201605_고친_코드는_push_전에_임포트부터_시켜봐라.md"

# 임포트해볼 모듈. 봇이 기동할 때 실제로 임포트되는 것들이다.
MODULES = [
    "agent_context", "secret_filter", "quota_tracker", "agent_memory",
    "public_agent_files", "memory_hygiene", "gatekeeper", "self_challenge",
    "bot_tools", "main_public", "discord_bot_server", "log_streamer",
]

# 코드 결함으로 판정하는 예외. 나머지는 환경 차이로 보고 건너뛴다.
_CODE_DEFECTS = {
    "ImportError", "NameError", "ValueError", "SyntaxError", "IndentationError",
    "AttributeError", "TypeError", "UnboundLocalError",
}

# 임포트만으로 네트워크를 타지 않게 하는 더미 환경. GEMINI_MODEL_POOL 을 주면
# build_agent_pool 이 모델 목록 조회(API 호출)를 건너뛴다.
_PROBE_ENV = {
    "DISCORD_BOT_TOKEN": "g012-probe",
    "GEMINI_API_KEY": "g012-probe",
    "DISCORD_CHANNEL_ID": "1",
    "DISCORD_PUBLIC_CHANNEL_ID": "1",
    "GEMINI_MODEL_POOL": "gemini-3.5-flash-lite",
    "SE_GATE_IMPORT_PROBE": "1",
}


# 자식 프로세스에서 도는 임포트 드라이버. 모듈 하나가 죽어도 나머지를 계속 시도하고,
# "모듈이름<탭>예외타입: 메시지" 한 줄씩 뱉는다(성공이면 메시지가 빈 줄).
_DRIVER = """
import importlib, sys
for name in sys.argv[1:]:
    try:
        importlib.import_module(name)
        print(name + "\\t")
    except BaseException as e:
        print(name + "\\t" + type(e).__name__ + ": " + str(e).replace("\\n", " ")[:300])
"""


def _probe_env(repo) -> dict:
    env = dict(os.environ)
    env.update(_PROBE_ENV)
    env["PYTHONPATH"] = str(repo)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _local_modules(repo) -> "set[str]":
    return {p.stem for p in repo.glob("*.py") if p.is_file()}


def _classify(stderr: str, local: "set[str]") -> "tuple[str, str]":
    """(판정, 사람이 읽을 사유). 판정은 'ok' | 'skip' | 'defect'."""
    lines = [l for l in stderr.strip().splitlines() if l.strip()]
    if not lines:
        return "defect", "(표준오류 없음)"
    last = lines[-1]
    exc_type = last.split(":", 1)[0].strip().split(".")[-1]
    if exc_type == "ModuleNotFoundError":
        missing = last.split("'")[1] if "'" in last else ""
        # 저장소 안의 모듈이 없다면 그건 코드 결함(파일을 지웠거나 이름을 틀렸다).
        return ("defect", last) if missing in local else ("skip", last)
    if exc_type in _CODE_DEFECTS:
        return "defect", last
    return "skip", last


def check(ctx) -> "list[str]":
    repo = ctx.repo
    local = _local_modules(repo)
    env = _probe_env(repo)
    targets = [n for n in MODULES if (repo / f"{n}.py").is_file()]
    if not targets:
        return []
    # 모듈마다 인터프리터를 새로 띄우면 langchain/discord 를 그 횟수만큼 다시 로드해서
    # 커밋 경로가 수십 초씩 밀린다. 한 프로세스 안에서 차례로 임포트하고 결과만 줄로
    # 뱉는다 -- 실패한 임포트는 sys.modules 에 남지 않으므로 뒤 모듈을 가리지 않는다.
    proc = subprocess.run(
        [sys.executable, "-c", _DRIVER, *targets],
        cwd=str(repo), env=env, capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        return [f"임포트 검사 자체가 실패했다(returncode={proc.returncode}): "
                f"{proc.stderr.strip()[-300:]}"]

    violations: list[str] = []
    for line in proc.stdout.splitlines():
        if "\t" not in line:
            continue
        name, _, why = line.partition("\t")
        if not why:
            continue  # 임포트 성공.
        verdict, reason = _classify(why, local)
        if verdict == "defect":
            violations.append(
                f"{name}.py 를 임포트할 수 없다 -- 이대로 배포되면 봇이 기동 단계에서 죽는다: {reason}")
    return violations
