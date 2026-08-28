"""
강제 게이트 러너 -- gates/ 아래의 모든 게이트를 돌리고, 하나라도 위반되면 exit 1.

이 파일이 존재하는 이유는 한 문장으로 요약된다: 산문은 읽히지 않으면 아무것도 막지 못한다.

2026-08-28의 실측 기록. 에이전트는 20:16에 "고친 코드는 push 전에 임포트부터 시켜봐라"를
저장했고, 20:35에 "py_compile은 문법만 잡는다, 임포트를 해봐야 한다"를 다시 저장했고,
20:37에 임포트가 불가능한 코드를 push했다. 진단의 질이 문제가 아니었다 -- 진단이 저장소의
마크다운 파일에 남아 있을 뿐 실행 경로 어디에도 연결돼 있지 않았던 것이 문제다.

그래서 게이트는 에이전트가 읽어야 작동하는 것이 아니라, 커밋 경로 위에 놓여서 읽지 않아도
작동한다. discord_bot_server.git_sync()가 커밋 직전에 이걸 부르고, 위반이 있으면 커밋을
하지 않고 위반 목록을 그대로 Discord에 돌려준다.

사용:
    python3 gatekeeper.py            # 통과 0 / 위반 1
    python3 gatekeeper.py --list     # 등록된 게이트 목록
    from gatekeeper import run_gates; report = run_gates()
"""
from __future__ import annotations

import importlib
import pkgutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
_SKIP_DIRS = {".git", "venv", "__pycache__", "node_modules", "inbox"}


class GateContext:
    """게이트가 저장소를 들여다볼 때 쓰는 창구. 게이트가 직접 subprocess를 부르지 않게
    해서, 테스트에서 임시 저장소를 물려 돌릴 수 있게 한다."""

    def __init__(self, repo: Path | None = None):
        self.repo = Path(repo or REPO_DIR).resolve()

    def rel(self, path: Path) -> str:
        try:
            return str(Path(path).resolve().relative_to(self.repo))
        except ValueError:
            return str(path)

    def python_files(self) -> "list[Path]":
        out = []
        for path in self.repo.rglob("*.py"):
            # rglob은 "public_agent.py"처럼 .py로 끝나는 '디렉터리'도 물어온다 (이 저장소에
            # 실제로 하나 있다) -- is_file()로 걸러야 게이트가 IsADirectoryError로 죽지 않는다.
            if not path.is_file():
                continue
            if any(part in _SKIP_DIRS for part in path.relative_to(self.repo).parts):
                continue
            out.append(path)
        return sorted(out)

    def tracked_files(self) -> "list[Path]":
        """git이 추적 중인 파일 + 아직 스테이지 안 된 새 파일. .gitignore로 걸러진 것
        (.env 등)은 애초에 커밋되지 않으므로 보지 않는다."""
        res = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=self.repo, capture_output=True, text=True,
        )
        if res.returncode != 0:
            return self.python_files()
        return [p for p in (self.repo / line for line in res.stdout.splitlines() if line.strip())
                if p.is_file()]

    def diff_numstat(self) -> str:
        """HEAD 대비 아직 커밋되지 않은 변경의 numstat (스테이지 여부 무관)."""
        res = subprocess.run(
            ["git", "diff", "HEAD", "--numstat"], cwd=self.repo, capture_output=True, text=True,
        )
        return res.stdout if res.returncode == 0 else ""


@dataclass
class GateResult:
    rule_id: str
    title: str
    violations: "list[str]" = field(default_factory=list)
    error: str = ""

    @property
    def passed(self) -> bool:
        return not self.violations and not self.error


@dataclass
class GateReport:
    results: "list[GateResult]"

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    def summary(self) -> str:
        if self.passed:
            names = ", ".join(r.rule_id for r in self.results)
            return f"[게이트 통과] {len(self.results)}개 검사 ({names})"
        lines = ["[게이트 차단] 커밋하지 않았다. 아래를 고친 뒤 다시 시도하라."]
        for r in self.results:
            if r.passed:
                continue
            lines.append(f"\n{r.rule_id} -- {r.title}")
            if r.error:
                lines.append(f"  - (게이트 자체 오류) {r.error}")
            for v in r.violations:
                lines.append(f"  - {v}")
        return "\n".join(lines)


def load_gates() -> list:
    import gates as gates_pkg
    modules = []
    for info in sorted(pkgutil.iter_modules(gates_pkg.__path__), key=lambda i: i.name):
        if info.name.startswith("_"):
            continue
        modules.append(importlib.import_module(f"gates.{info.name}"))
    return modules


def run_gates(repo: Path | None = None) -> GateReport:
    """모든 게이트를 돌린다. 게이트 하나가 예외로 죽어도 나머지를 계속 돌리되, 그 게이트는
    실패로 친다 -- fail-closed. 검사가 고장 났을 때 조용히 통과시키는 것이 가장 나쁘다."""
    ctx = GateContext(repo)
    results = []
    for mod in load_gates():
        rule_id = getattr(mod, "RULE_ID", mod.__name__)
        title = getattr(mod, "TITLE", "")
        try:
            results.append(GateResult(rule_id, title, list(mod.check(ctx))))
        except Exception as e:
            results.append(GateResult(rule_id, title, error=f"{type(e).__name__}: {e}"))
    return GateReport(results)


def main() -> int:
    if "--list" in sys.argv:
        for mod in load_gates():
            print(f"{mod.RULE_ID}  {mod.TITLE}")
            print(f"        사고: {mod.ORIGIN}" + (f" / 근거: {mod.EVIDENCE}" if mod.EVIDENCE else ""))
        return 0
    report = run_gates()
    print(report.summary())
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
