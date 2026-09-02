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
    # 원래 G001(독스트링 자리) + G002(임포트 순환)를 기대했다. 2026-09-02 에 그 둘과
    # G006(정의 전 이름 참조)을 G012(실제 임포트)로 통합했다 -- 셋 다 "임포트해보지 않고
    # push해서 봇이 기동 단계에서 죽는다"는 하나의 실패를 AST 로 근사하던 것이었다.
    ("b32aa78", "게스트 가드를 def 다음 줄에 삽입 -> 독스트링 소실 + 순환 임포트",
     {"G012"}),
    ("1ea4304", "run_bot_loop.sh가 저장소를 grep해 토큰을 찾아 로그로 출력",
     {"G004"}),
    ("c3b3b88", "공개 채널 run_shell이 비밀값을 마스킹 없이 그대로 반환(cat .env 한 줄로 유출)",
     {"G011"}),
]


def _commit_exists(commit: str) -> bool:
    """이 클론에 해당 커밋이 있는가. shallow clone(예: CI의 fetch-depth 1)에서는 사고 커밋이
    없어서 git archive가 exit 128로 죽고, 그러면 이 스위트가 스택트레이스로 중단돼 나머지
    사고까지 검증하지 못했다(실측 2026-09-02). 없으면 SKIP으로 넘어가고 그 사실을 출력한다
    -- 전체 이력이 필요하다는 뜻이지, 게이트가 실패했다는 뜻이 아니다."""
    return subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"],
                          cwd=REPO, capture_output=True).returncode == 0


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


# _synthetic_requirements_incident 는 2026-09-02 에 제거했다. 그것이 증명하던 G007
# (requirements.txt 자리표시자 검사)을 같이 지웠기 때문이다 -- 사고 1건이 그마저 원격에
# 반영되지 않은 미수였고, 잡을 수 있는 것은 'X'/'TODO' 같은 명백한 쓰레기뿐이었다.
# "실제로 설치되는가"는 네트워크가 필요해 커밋 게이트에 담을 수 없다.


def main() -> int:
    failures: list[str] = []

    skipped: list[str] = []
    for commit, what, expected in INCIDENTS:
        if not _commit_exists(commit):
            print(f"[{commit}] {what}\n    SKIP -- 이 클론에 커밋이 없다(shallow clone). "
                  f"전체 이력으로 받아야 검증된다: git fetch --unshallow")
            skipped.append(commit)
            continue
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

    report = gatekeeper.run_gates(REPO)
    print(f"\n[HEAD] 현재 트리 -> {'GREEN 성립' if report.passed else 'GREEN 실패'}")
    if not report.passed:
        failures.append("현재 HEAD가 게이트를 통과하지 못한다:\n" + report.summary())

    if failures:
        print("\n=== 실패 ===")
        for f in failures:
            print(" -", f)
        return 1
    if skipped:
        print(f"\n건너뛴 사고 {len(skipped)}건(커밋 없음): {', '.join(skipped)}")
    print("\n검증한 범위에서 모든 게이트가 red-green 증명을 통과했다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
