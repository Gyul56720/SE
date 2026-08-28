"""
자가 진단 -> red-green 증명 -> 강제 게이트 승격.

이 저장소는 이미 제3자 검증을 해봤다(Public_agent/verify.py -- 생성자와 분리된 claude -p
호출로 diff를 재검토한다). 그 파일 주석이 스스로 한계를 적어뒀다: claude 토큰이 소진되면
검증이 항상 미승인을 반환한다. 제3자 모델은 (1) 쿼터에 종속되고 (2) 그 자신도 환각하며
(3) 판단 주체를 늘려도 판단의 성질은 그대로다.

Public_agent/challenge.py에는 그 문제가 없다. EXPECTED_SHA256은 풀이자가 위조할 수 없고,
심판이 모델이 아니라 exit code다. 자가 진단에 같은 구조를 쓴다.

  진단이 옳다는 증거는 말이 아니라 두 번의 실행 결과다.

  RED   -- 고치기 전 트리에서 후보 검사를 돌리면 반드시 위반을 보고해야 한다.
           통과해버리면 그건 원인이 아니었다는 뜻이다. 여기서 에이전트의 자기 확신이 깨진다.
  GREEN -- 고친 뒤 트리에서 돌리면 반드시 통과해야 한다.
           실패하면 수정이 실제로는 고치지 못한 것이다.

둘 다 성립할 때만 PROVEN=1 이고, 그때 비로소 후보 검사가 gates/ 로 승격되어 이후 모든
커밋을 막는 강제 게이트가 된다. 증명되지 않은 진단은 산문 노트로도 남기지 않는다 --
읽히지 않는 노트가 늘어나는 것이 이 저장소가 겪은 바로 그 실패였다.

사용:
    python3 self_challenge.py prove --candidate <검사파일.py> --broken-commit <사고커밋>
    python3 self_challenge.py prove --candidate <검사파일.py> --broken-tree <디렉터리>

후보 검사 파일은 gates/__init__.py의 게이트 규약(RULE_ID, TITLE, ORIGIN, EVIDENCE,
check(ctx))을 따라야 한다. 증명되면 gates/<RULE_ID>_<슬러그>.py 로 복사된다.

종료 코드: 증명 성공 0, 실패 1. 표준출력 마지막 줄에 PROVEN=1 또는 PROVEN=0 을 찍는다.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
GATES_DIR = REPO_DIR / "gates"

sys.path.insert(0, str(REPO_DIR))
import gatekeeper  # noqa: E402


def _load_candidate(path: Path):
    spec = importlib.util.spec_from_file_location(f"candidate_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"후보 검사를 로드할 수 없다: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for attr in ("RULE_ID", "TITLE", "check"):
        if not hasattr(mod, attr):
            raise RuntimeError(f"후보 검사에 {attr}가 없다 -- gates/__init__.py의 규약을 따르라")
    return mod


def _materialize_commit(commit: str, dest: Path) -> None:
    """사고 커밋의 트리를 dest에 펼친다. 게이트가 git을 물어볼 수 있으므로 저장소로 만든다."""
    archive = subprocess.run(["git", "archive", commit], cwd=REPO_DIR, capture_output=True)
    if archive.returncode != 0:
        raise RuntimeError(f"git archive {commit} 실패: {archive.stderr.decode()[:300]}")
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)
    subprocess.run(["git", "init", "-q", str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(dest), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "incident tree"], check=True, capture_output=True)


def prove(candidate_path: Path, broken_commit: str | None, broken_tree: Path | None) -> "tuple[int, str]":
    """(PROVEN 값, 사람이 읽을 보고서)를 돌려준다. PROVEN은 증명되면 1, 아니면 0."""
    mod = _load_candidate(candidate_path)
    lines = [f"후보 검사: {mod.RULE_ID} -- {mod.TITLE}", f"파일: {candidate_path}"]

    # --- RED: 고치기 전 트리에서 반드시 걸려야 한다 ---
    with tempfile.TemporaryDirectory() as tmp:
        broken_dir = Path(tmp)
        if broken_commit:
            _materialize_commit(broken_commit, broken_dir)
            origin = broken_commit
        elif broken_tree:
            shutil.copytree(broken_tree, broken_dir, dirs_exist_ok=True)
            origin = str(broken_tree)
        else:
            return 0, "고치기 전 상태(--broken-commit 또는 --broken-tree)를 지정해야 한다."
        try:
            red_violations = list(mod.check(gatekeeper.GateContext(broken_dir)))
        except Exception as e:
            return 0, "\n".join(lines + [f"RED 실행 중 후보 검사가 죽었다: {type(e).__name__}: {e}"])

    lines.append(f"\n[RED] 고치기 전 트리({origin})에서 실행")
    if not red_violations:
        lines += [
            "  위반 없음 -> RED 불성립.",
            "  이 검사는 사고 당시 코드에서도 통과한다. 즉 진단이 실제 원인을 짚지 못했다.",
            "  자기 확신이 아니라 이 실행 결과가 판정한다 -- 진단을 다시 세워라.",
        ]
        return 0, "\n".join(lines)
    for v in red_violations[:10]:
        lines.append(f"  - {v}")
    lines.append(f"  위반 {len(red_violations)}건 -> RED 성립 (원인을 짚었다)")

    # --- GREEN: 고친 뒤 트리(현재 워킹트리)에서는 통과해야 한다 ---
    try:
        green_violations = list(mod.check(gatekeeper.GateContext(REPO_DIR)))
    except Exception as e:
        return 0, "\n".join(lines + [f"\n[GREEN] 후보 검사가 죽었다: {type(e).__name__}: {e}"])

    lines.append("\n[GREEN] 현재 워킹트리에서 실행")
    if green_violations:
        for v in green_violations[:10]:
            lines.append(f"  - {v}")
        lines += [
            f"  위반 {len(green_violations)}건 -> GREEN 불성립.",
            "  수정이 실제로는 고치지 못했다. 고친 뒤에 다시 증명하라.",
        ]
        return 0, "\n".join(lines)
    lines.append("  위반 없음 -> GREEN 성립 (수정이 실제로 고쳤다)")
    return 1, "\n".join(lines)


def promote(candidate_path: Path, mod) -> Path:
    """증명된 후보를 gates/ 로 승격한다. 이 시점부터 모든 커밋이 이 검사를 통과해야 한다."""
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "_", mod.TITLE).strip("_").lower()[:40] or "gate"
    dest = GATES_DIR / f"{mod.RULE_ID}_{slug}.py"
    shutil.copy2(candidate_path, dest)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prove", help="후보 검사를 red-green으로 증명하고, 통과하면 게이트로 승격한다")
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--broken-commit", help="사고가 살아있는 커밋 해시")
    p.add_argument("--broken-tree", type=Path, help="사고가 살아있는 디렉터리")
    p.add_argument("--no-promote", action="store_true", help="증명만 하고 승격은 하지 않는다")
    args = parser.parse_args()

    try:
        proven, report = prove(args.candidate, args.broken_commit, args.broken_tree)
    except Exception as e:
        print(f"증명 절차 실패: {type(e).__name__}: {e}")
        print("PROVEN=0")
        return 1

    print(report)
    if proven and not args.no_promote:
        dest = promote(args.candidate, _load_candidate(args.candidate))
        print(f"\n승격: {dest.relative_to(REPO_DIR)} -- 이제부터 모든 커밋이 이 게이트를 통과해야 한다.")
    print(f"\nPROVEN={proven}")
    return 0 if proven else 1


if __name__ == "__main__":
    raise SystemExit(main())
