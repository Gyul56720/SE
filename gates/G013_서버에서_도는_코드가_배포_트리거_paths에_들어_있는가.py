"""
G013 -- 서버에서 실제로 도는 코드가 배포 트리거에 들어 있는가.

이 저장소가 세 번 겪은 실패다: **코드는 좋아졌는데 서버에 도달하지 못한다.**
deploy-oracle.yml 은 `paths:` 에 적힌 파일이 바뀔 때만 배포된다. 그 목록에서 빠진 파일은
고쳐도 VM 이 계속 옛 코드를 들고 돈다.

  - searcher.py 가 빠져 있어서 탐색기를 통째로 갈아엎어도 배포가 안 됐다(주석에 기록됨).
  - bot_tools.py / quota_tracker.py 가 빠져 있어서 에러 분류·쿼터 로직을 고쳐도 배포가
    안 됐다(주석에 기록됨).
  - 그리고 2026-09-02 현재 gates/ 와 gatekeeper.py 가 빠져 있다 -- 강제 장치 자신이
    서버에 도달하지 못한다. 앞의 둘보다 나쁘다: 새 게이트를 승격해도 VM 의 커밋 경로는
    옛 게이트 집합으로 계속 돈다.

두 번은 주석으로 기록됐고 세 번째가 그대로 났다. 기록은 재발을 못 막는다 -- 검사가 막는다.

동작: deploy/*.service 의 ExecStart 가 가리키는 파이썬 파일에서 시작해 저장소 안 모듈의
임포트 폐포를 구하고, 여기에 강제 장치(gatekeeper.py, gates/**, self_challenge.py),
유닛 파일, 워크플로 자신을 더한 집합이 workflow 의 paths: 로 전부 덮이는지 본다.

무엇을 안 잡는가: paths 에 있으나 실제로는 안 쓰는 파일(과잉은 해롭지 않다), 그리고
배포 스크립트가 실제로 무엇을 하는지(그건 이 게이트의 관심사가 아니다).
"""
from __future__ import annotations

import ast
import re

RULE_ID = "G013"
TITLE = "서버에서 도는 코드가 배포 트리거 paths에 들어 있는가"
ORIGIN = "2026-09-02 분석 F3 (gates/ 와 gatekeeper.py 가 deploy paths 에 없음)"
EVIDENCE = "reports/20260902_agent_analysis.md"

_WORKFLOW_REL = ".github/workflows/deploy-oracle.yml"
# 커밋 경로를 이루는 강제 장치. 서버의 git_sync 가 이걸 부르므로 반드시 최신이어야 한다.
_ENFORCEMENT = ["gatekeeper.py", "self_challenge.py", "gates/**"]
_EXECSTART = re.compile(r"^ExecStart=.*?([\w./-]+\.py)", re.M)
_LIST_ITEM = re.compile(r'^\s*-\s*"?([^"#]+?)"?\s*$')


def _workflow_paths(repo) -> "list[str] | None":
    path = repo / _WORKFLOW_REL
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        stripped = line.strip()
        if not inside:
            if stripped.startswith("paths:"):
                inside = True
            continue
        if not stripped or stripped.startswith("#"):
            continue
        m = _LIST_ITEM.match(line)
        if m:
            out.append(m.group(1).strip())
            continue
        break  # paths 블록 끝.
    return out


def _covered(rel: str, patterns: "list[str]") -> bool:
    for pat in patterns:
        regex = "^" + re.escape(pat).replace(r"\*\*", ".*").replace(r"\*", "[^/]*") + "$"
        if re.match(regex, rel):
            return True
    return False


def _import_closure(repo, entries: "list[str]") -> "set[str]":
    """저장소 안 모듈만 따라가는 임포트 폐포(상대경로 문자열 집합)."""
    local = {p.stem: p.name for p in repo.glob("*.py") if p.is_file()}
    seen: set[str] = set()
    stack = list(entries)
    while stack:
        rel = stack.pop()
        if rel in seen or not (repo / rel).is_file():
            continue
        seen.add(rel)
        try:
            tree = ast.parse((repo / rel).read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names = [node.module.split(".")[0]]
            for name in names:
                if name in local and local[name] not in seen:
                    stack.append(local[name])
    return seen


def check(ctx) -> "list[str]":
    repo = ctx.repo
    patterns = _workflow_paths(repo)
    if patterns is None:
        return []  # 이 저장소에 배포 워크플로가 없으면 할 일 없음.
    if not patterns:
        return [f"{_WORKFLOW_REL}: paths: 목록을 읽지 못했다 -- 배포 트리거를 확인할 수 없다."]

    services = sorted(p for p in (repo / "deploy").glob("*.service")) if (repo / "deploy").is_dir() else []
    entries: list[str] = []
    required: list[str] = [_WORKFLOW_REL]
    for svc in services:
        required.append(f"deploy/{svc.name}")
        for match in _EXECSTART.finditer(svc.read_text(encoding="utf-8")):
            rel = match.group(1).split("/SE/")[-1].lstrip("/")
            if (repo / rel).is_file():
                entries.append(rel)
    required += sorted(_import_closure(repo, entries))
    required += _ENFORCEMENT

    violations = []
    for rel in dict.fromkeys(required):
        if rel.endswith("/**"):
            # 디렉터리 요구는 그 디렉터리를 덮는 패턴이 있는지로 본다.
            if not any(p.startswith(rel[:-3]) for p in patterns):
                violations.append(
                    f"{_WORKFLOW_REL}: '{rel}' 가 paths 에 없다 -- 이 디렉터리만 고친 커밋은 "
                    f"배포되지 않아 서버가 옛 코드를 들고 돈다.")
            continue
        if not _covered(rel, patterns):
            violations.append(
                f"{_WORKFLOW_REL}: '{rel}' 가 paths 에 없다 -- 서버가 실행하는 파일인데 "
                f"이 파일만 고치면 배포가 트리거되지 않는다.")
    return violations
