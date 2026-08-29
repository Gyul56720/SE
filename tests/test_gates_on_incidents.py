"""
게이트의 red-green 증명 -- 게이트 자신도 challenge.py와 같은 방식으로 검증한다.

Public_agent/challenge.py는 EXPECTED_SHA256이라는 위조 불가능한 오라클을 코드 안에 두고,
풀이가 맞으면 exit 0 / 틀리면 exit 1로 판정한다. 풀이자가 "내가 맞다"고 우길 수 없다.

게이트에도 같은 것이 필요하다. "이 검사가 그 사고를 잡는다"는 주장은 주장일 뿐이다. 유일한
증거는 실제 사고 커밋의 트리를 꺼내 게이트를 돌렸을 때 정말로 실패하느냐다.

  RED   -- 사고 커밋의 트리에서 해당 게이트가 반드시 위반을 보고해야 한다.
           통과해버리면 그 게이트는 원인을 짚지 못한 것이고, 승격될 자격이 없다.
  GREEN -- 고친 뒤(현재 HEAD)의 트리에서는 통과해야 한다.

두 조건이 다 성립할 때만 그 게이트가 실효를 가진다. 이 파일이 그것을 매번 다시 증명한다.

실행: python3 tests/test_gates_on_incidents.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import gatekeeper  # noqa: E402

# (사고 커밋, 무엇이 터졌는가, 그 트리에서 반드시 걸려야 하는 게이트들)
INCIDENTS = [
    ("1a82685", "게스트 제한 11줄을 위해 discord_bot_server.py 190줄을 삭제한 자기 재작성",
     {"G003"}),
    ("b32aa78", "게스트 가드를 def 다음 줄에 삽입 -> 독스트링 소실 + 순환 임포트",
     {"G001", "G002"}),
    ("1ea4304", "run_bot_loop.sh가 저장소를 grep해 토큰을 찾아 로그로 출력",
     {"G004"}),
]


def _materialize(commit: str, dest: Path) -> None:
    """해당 커밋의 트리를 dest에 펼치고, 현재의 게이트 구현을 얹는다.
    (사고 당시에는 게이트가 존재하지 않았으므로 검사 코드는 지금 것을 쓴다.)"""
    archive = subprocess.run(["git", "archive", commit], cwd=REPO, capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)
    subprocess.run(["git", "init", "-q", str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "add", "-A"], check=True,
                   capture_output=True)
    subprocess.run(["git", "-C", str(dest), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "incident tree"], check=True, capture_output=True)


def _fired(report) -> "set[str]":
    return {r.rule_id for r in report.results if not r.passed}


def _synthetic_requirements_incident() -> "tuple[str, set[str]]":
    """2026-08-29 requirements 'X' 삽입 사고는 원격에 반영되지 않아 커밋 트리가 없다.
    사고를 재현한 합성 트리를 만들어 G007이 발동하는지 본다."""
    import shutil, tempfile
    tmp = tempfile.mkdtemp()
    archive = subprocess.run(["git", "archive", "HEAD"], cwd=REPO, capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", tmp], input=archive.stdout, check=True)
    (Path(tmp) / "requirements.txt").write_text("requests>=2.31.0\nX\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", tmp], check=True)
    subprocess.run(["git", "-C", tmp, "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", tmp, "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "req incident"], check=True, capture_output=True)
    return tmp, {"G007"}


def main() -> int:
    failures: list[str] = []

    for commit, what, expected in INCIDENTS:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            _materialize(commit, dest)
            fired = _fired(gatekeeper.run_gates(dest))
        missing = expected - fired
        status = "RED 성립" if not missing else "RED 실패"
        print(f"[{commit}] {what}\n    기대 {sorted(expected)} / 실제 발동 {sorted(fired)} -> {status}")
        if missing:
            failures.append(
                f"{commit}: {sorted(missing)} 가 사고 트리에서 발동하지 않았다 -- "
                f"이 게이트는 해당 원인을 잡지 못한다"
            )

    syn_tree, syn_expected = _synthetic_requirements_incident()
    syn_fired = _fired(gatekeeper.run_gates(Path(syn_tree)))
    syn_missing = syn_expected - syn_fired
    print(f"[합성:requirements X 삽입] 기대 {sorted(syn_expected)} / 발동 {sorted(syn_fired)} "
          f"-> {'RED 성립' if not syn_missing else 'RED 실패'}")
    if syn_missing:
        failures.append(f"합성 requirements 사고에서 {sorted(syn_missing)} 미발동")

    report = gatekeeper.run_gates(REPO)
    print(f"\n[HEAD] 현재 트리 -> {'GREEN 성립' if report.passed else 'GREEN 실패'}")
    if not report.passed:
        failures.append("현재 HEAD가 게이트를 통과하지 못한다:\n" + report.summary())

    if failures:
        print("\n=== 실패 ===")
        for f in failures:
            print(" -", f)
        return 1
    print("\n모든 게이트가 red-green 증명을 통과했다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
