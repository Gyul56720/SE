"""
G014 -- 공개 채널 쓰기 도구의 경로 제한이 실제로 탈출을 막는가 (행동 검증).

G003 은 `_resolve_inside_memory` / `_resolve_inside_output` 이라는 **문자열이 파일에 있는지**
만 본다. 그래서 함수 껍데기만 남기고 속을 `return (MEMORY_DIR / filename)` 으로 비워도
G003 은 통과한다 -- 제약의 이름만 남고 제약은 사라지는 상태다. 같은 계열의 실패를 이미
겪었다(1a82685: 제약을 서술한 코드가 조용히 사라짐).

공개 채널은 화이트리스트가 없다. 그 채널을 보는 누구나 save_memory / write_public_answer 를
부를 수 있으므로, 이 두 함수의 경로 제한은 "있다고 적혀 있는 것"이 아니라 "실제로 막는 것"
이어야 한다. 그래서 G011 이 마스킹을 카나리로 검증하듯, 여기서도 탈출 경로를 실제로 넣어
ValueError 가 나는지 확인한다.

검사 방법: 대상 저장소의 agent_memory / public_agent_files 를 임포트해서 아래 카나리를
resolver 에 먹인다. 하나라도 통과(예외 없이 경로를 돌려줌)하면 위반이다.
서드파티가 필요 없는 모듈이라 어느 환경에서도 돈다.
"""
from __future__ import annotations

import importlib.util
import sys

RULE_ID = "G014"
TITLE = "공개 채널 쓰기 도구의 경로 제한이 실제로 탈출을 막는가"
ORIGIN = "2026-09-02 분석 (G003은 문자열 존재만 확인 -- 껍데기만 남아도 통과한다)"
EVIDENCE = "public_agent_memory/20260828-202744_제약_자기소거_--_나를_막는_규칙을_내가_지우는_일.md"

# (모듈 파일, resolver 이름, 무엇을 지키는가)
_TARGETS = [
    ("agent_memory.py", "_resolve_inside_memory", "public_agent_memory/ 밖으로 쓰기"),
    ("public_agent_files.py", "_resolve_inside_output", "Public_agent/ 밖으로 쓰기"),
]

# 폴더를 벗어나는 입력들. 어느 것도 통과해서는 안 된다.
_ESCAPES = [
    "../escaped.md",
    "../../etc/passwd",
    "sub/../../escaped.md",
    "/etc/passwd",
    "nested/dir/file.md",
]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(ctx) -> "list[str]":
    repo = ctx.repo
    violations: list[str] = []
    sys.path.insert(0, str(repo))
    try:
        for filename, resolver_name, what in _TARGETS:
            path = repo / filename
            if not path.is_file():
                violations.append(f"{filename} 이(가) 없다 -- {what} 를 막는 유일한 지점이다.")
                continue
            try:
                mod = _load(path, f"_g014_{path.stem}")
            except Exception as e:
                violations.append(f"{filename} 를 임포트할 수 없다: {type(e).__name__}: {e}")
                continue
            resolver = getattr(mod, resolver_name, None)
            if resolver is None:
                violations.append(f"{filename}: '{resolver_name}' 이(가) 없다 -- {what} 가 열린다.")
                continue
            for canary in _ESCAPES:
                try:
                    resolved = resolver(canary)
                except ValueError:
                    continue  # 정상 -- 막았다.
                except Exception as e:
                    violations.append(
                        f"{filename}: {resolver_name}({canary!r}) 가 ValueError 가 아닌 "
                        f"{type(e).__name__} 로 죽는다 -- 호출부가 이 예외를 잡지 못한다.")
                    continue
                violations.append(
                    f"{filename}: {resolver_name}({canary!r}) 가 막히지 않고 {resolved} 를 "
                    f"돌려줬다 -- {what} 가 가능하다. 경로 제한이 이름만 남고 무력화됐다.")
    finally:
        sys.path.remove(str(repo))
    return violations
