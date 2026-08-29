"""
G007 후보 -- requirements.txt의 각 줄이 설치 가능한 실제 의존성인가.

사고: 2026-08-29. 관리 채널에서 "requirements.txt에 X 추가하고 커밋" 요청을 받은 봇이
자리표시자 'X'를 실제 패키지명으로 해석해 넣고 커밋했다고 보고했다(해시 539e168). 실제로는
원격에 반영되지 않았지만(그 문제는 원격 반영 검증이 따로 잡는다), 만약 반영됐다면
requirements.txt에 pip이 설치할 수 없는 'X'가 들어가 배포가 깨졌을 것이다.

py_compile도 임포트 검사도 이걸 못 잡는다 -- requirements.txt는 파이썬 코드가 아니다.
그래서 별도 검사가 필요하다.

무엇을 잡는가:
  1. PEP 508로 파싱조차 안 되는 줄 (이름 없는 '==1.0', 공백 낀 토큰 등).
  2. 문법은 유효하지만 자리표시자/쓰레기로 보이는 이름 -- 'X' 한 글자, TODO/FIXME,
     foo/bar/baz, changeme, your_package, <...> 등. 'X'는 PEP 508상 유효한 이름이라
     파싱만으로는 안 걸리므로 이 목록으로 별도로 막는다.

무엇을 안 잡는가: "이 패키지가 PyPI에 실제로 존재하는가"는 네트워크가 필요해서 커밋
게이트로 부적합하다. 자리표시자/쓰레기라는 명백한 신호만 본다(오탐에 fail-closed --
애매하면 통과시킨다).
"""
from __future__ import annotations

RULE_ID = "G007"
TITLE = "requirements.txt의 각 줄이 설치 가능한 실제 의존성인가"
ORIGIN = "2026-08-29 requirements X 삽입 시도"
EVIDENCE = ""

# 문법은 유효하지만 사람이 자리표시자로 쓰는 이름들. 실제 패키지명과 겹칠 위험이 낮은 것만.
_PLACEHOLDER_NAMES = {
    "x", "y", "z", "todo", "fixme", "foo", "bar", "baz", "qux",
    "changeme", "placeholder", "yourpackage", "your_package", "package",
    "example", "somepackage", "mypackage", "tbd", "xxx",
}


def _iter_requirement_lines(text: str):
    """(줄번호, 원본줄) 중 실제 의존성 지정으로 봐야 하는 것만. 주석/빈줄/옵션줄
    (-r, -e, --hash 등)과 환경마커 연속줄은 건너뛴다."""
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-") or line.startswith("--"):
            continue  # -r other.txt, -e ., --extra-index-url 등
        # 인라인 주석 제거
        line = line.split(" #", 1)[0].strip()
        if line:
            yield i, line


def check(ctx) -> "list[str]":
    from packaging.requirements import Requirement, InvalidRequirement

    violations: list[str] = []
    for path in ctx.tracked_files():
        if path.name != "requirements.txt" and not path.name.startswith("requirements"):
            continue
        if path.suffix not in ("", ".txt"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = ctx.rel(path)
        for line_no, spec in _iter_requirement_lines(text):
            try:
                req = Requirement(spec)
            except InvalidRequirement as e:
                violations.append(f"{rel}:{line_no} 파싱 불가한 의존성 줄 '{spec}' -- {e}")
                continue
            if req.name.lower() in _PLACEHOLDER_NAMES:
                violations.append(
                    f"{rel}:{line_no} 자리표시자로 보이는 패키지명 '{req.name}' -- "
                    f"실제 설치 가능한 이름인지 확인하라 (pip install이 깨진다)"
                )
    return violations
