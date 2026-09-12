"""plan -- **계획 승인.** 저장소를 고치는 요청이면 diff 를 먼저 보이고, 사람이 승인해야 실제 트리에 닿는다.

격차표(SE vs Claude Code) '계획 승인': intent 는 목표 단위 승인이고, Claude Code 의 plan mode 는
위험한 한 작업의 계획을 먼저 보이고 승인한다. 여기서는 계획을 **말이 아니라 diff 로** 둔다:

    !계획 켜기 <요청>   HEAD 를 그림자 워크트리로 꺼낸다. 그 뒤 edit_file · run_shell 은 **그림자**에서 돈다
    !계획 보기          그림자의 git diff (이것이 '계획' 이다 -- 모델의 설명이 아니라 코드가 만든 차이)
    !계획 시험          **격리 판에서 미리 돌려 본다**(문법·게이트·바뀐 파일의 검사) -- 승인의 전제다
    !계획 승인          diff 를 실제 트리에 `git apply --index` -- **리허설이 초록일 때만**. 안 붙으면 코드가 거절
    !계획 버림          그림자를 버린다. 실제 트리는 처음부터 안 건드렸다

승인 주체가 사람인 것은 intent 와 같은 자리(관리 채널 화이트리스트, allow_write)가 지킨다.
게이트(toolgate: gates/·판정 원장·.env)는 그림자 안에서도 그대로 걸린다 -- 경로풀기(repo=그림자).
상태는 plan/state.json 한 장(gitignore) -- 봇이 재시작해도 그림자가 어디 있는지 안다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# 스크립트로 돌 때(`python3 plan/store.py --시험`) sys.path[0] 은 plan/ 이다 -- rehearsal 을 못 찾는다.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
상태상대 = "plan/state.json"
리허설기 = None      # 검사 주입: (repo, 판, 초) -> dict(rehearsal.시험 의 꼴). None 이면 진짜 rehearsal


def _git(repo: Path, *args: str, 입력: str = None):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          input=입력, timeout=120)


def 읽기(repo=None) -> "dict | None":
    p = Path(repo or REPO) / 상태상대
    if not p.is_file():
        return None
    try:
        s = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None
    if not s.get("판") or not Path(s["판"]).is_dir():
        return None
    return s


def 현재판(repo=None) -> "Path | None":
    """켜져 있으면 그림자 워크트리 경로, 아니면 None -- edit_file · run_shell 이 이것으로 갈린다."""
    s = 읽기(repo)
    return Path(s["판"]) if s else None


def 켜기(요청: str, repo=None, 누가: str = "cli") -> str:
    repo = Path(repo or REPO)
    s = 읽기(repo)
    if s:
        return f"이미 켜져 있다 [{s['id']}] -- `!계획 보기` · `!계획 승인` · `!계획 버림` 중 하나로 먼저 끝내라"
    tmp = Path(tempfile.mkdtemp(prefix="se-plan-"))
    r = _git(repo, "worktree", "add", "--detach", str(tmp), "HEAD")
    if r.returncode != 0:
        return f"그림자를 못 꺼냈다: {r.stderr.strip()[:200]}"
    아이디 = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    s = {"id": 아이디, "판": str(tmp), "요청": (요청 or "").strip()[:300], "누가": 누가,
         "때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    p = repo / 상태상대
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    return (f"계획판 켜짐 [{아이디}] -- 지금부터 edit_file · run_shell 은 그림자({tmp.name})에서 돈다. "
            f"실제 트리는 `!계획 승인` 전엔 안 바뀐다")


def _diff(판: Path, 이진: bool = False) -> str:
    _git(판, "add", "-N", ".")           # 새 파일도 diff 에 보이게(intent-to-add)
    args = ["diff", "--binary"] if 이진 else ["diff"]
    return _git(판, *args).stdout


def 보기(repo=None) -> str:
    s = 읽기(repo)
    if not s:
        return "계획판이 꺼져 있다 -- `!계획 켜기 <요청>`"
    판 = Path(s["판"])
    stat = _git(판, "diff", "--stat").stdout.strip()
    d = _diff(판)
    if not d.strip():
        return f"[{s['id']}] 아직 바뀐 것이 없다 (요청: {s['요청'][:80]})"
    영 = ""
    try:
        import impact
        r = impact.영향(판, 커밋=False)
        if r["파일"]:
            영 = "\n\n" + impact.보고(r)          # 계획은 diff 만이 아니다 -- 무엇에 딸려 움직이는지까지
    except Exception:                              # noqa: BLE001 -- 보고용
        영 = ""
    return f"[{s['id']}] 요청: {s['요청'][:80]}\n{stat}{영}\n\n{d}"


def _해시(판: Path) -> str:
    return hashlib.sha256(_diff(판, 이진=True).encode("utf-8")).hexdigest()[:12]


def 시험하기(repo=None, 초: int = 180, 전부: bool = False, 전부초: int = 1800) -> str:
    """**승인 전에 격리 판에서 돌려 본다.** 결과를 지금 diff 의 해시와 함께 상태에 적는다."""
    repo = Path(repo or REPO)
    s = 읽기(repo)
    if not s:
        return "계획판이 꺼져 있다 -- `!계획 켜기 <요청>`"
    판 = Path(s["판"])
    import rehearsal
    _리허설 = 리허설기 or (lambda repo, 판, 초, 전부=False, 전부초=1800:
                        rehearsal.시험(repo, 판=판, 초=초, 전부=전부, 전부초=전부초))
    r = _리허설(repo, 판, 초, 전부=전부, 전부초=전부초)      # 주입된 가짜도 전부 모드를 본다
    s["시험"] = {"해시": _해시(판), "통과": bool(r["통과"]), "때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "걸린초": r["걸린초"], "전부": bool(전부), "회귀": r.get("회귀")}
    (repo / 상태상대).write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    return rehearsal.보고(r)  # 보고는 늘 진짜 꼴로 찍는다


def 승인(repo=None, 누가: str = "cli", 건너뛰기: bool = False) -> str:
    """diff 를 실제 트리에 붙인다. 판정은 `git apply --index` 의 끝값 -- 사람도 모델도 아니다."""
    repo = Path(repo or REPO)
    s = 읽기(repo)
    if not s:
        return "계획판이 꺼져 있다 -- 승인할 것이 없다"
    판 = Path(s["판"])
    d = _diff(판, 이진=True)
    if not d.strip():
        _끄기(repo, s)
        return f"[{s['id']}] 바뀐 것이 없어 그대로 끈다"
    # **돌려 보지 않은 코드는 실제 트리에 안 붙인다.** 사용자(2026-09-11): 샌드박스가 있는데
    # 미리 돌려 보지 않고 붙이고 있었다. 리허설이 초록이어야 하고, 그 초록은 **지금 이 diff** 의 것이어야 한다.
    시 = s.get("시험") or {}
    지금해시 = _해시(판)
    if not 건너뛰기:
        if not 시:
            return (f"[{s['id']}] **아직 안 돌려 봤다 -- 붙이지 않았다.** `!계획 시험` 으로 격리 판에서 "
                    f"문법·게이트·검사를 먼저 돌려라(그것이 초록이어야 승인이 된다)")
        if 시.get("해시") != 지금해시:
            return (f"[{s['id']}] **시험한 뒤 코드가 또 바뀌었다 -- 붙이지 않았다.** `!계획 시험` 을 다시 돌려라 "
                    f"(시험한 diff {시.get('해시', '?')} · 지금 {지금해시})")
        if not 시.get("통과"):
            return (f"[{s['id']}] **리허설이 빨강이었다 -- 붙이지 않았다.** 먼저 고치고 `!계획 시험` 을 다시 돌려라 "
                    f"({시.get('때', '')})")
    # **색인을 먼저 새로 고친다.** 실측 2026-09-12: 파일을 쓰고 커밋하고 같은 초 안에 승인하면
    # `git apply --index` 가 "does not match index" 로 거절했다(간헐 -- 8번 중 1번). git 은 mtime 이
    # 색인 갱신과 같은 초면 그 항목을 못 믿는다(racy git). 새로 고치면 내용을 다시 읽어 확정한다.
    _git(repo, "update-index", "-q", "--refresh")
    r = _git(repo, "apply", "--index", "--whitespace=nowarn", "-", 입력=d)
    if r.returncode != 0:
        return (f"[{s['id']}] **적용 실패 -- 코드가 거절했다**: {r.stderr.strip()[:300]}\n"
                f"실제 트리에 같은 자리를 먼저 고친 것이 있을 때 이렇게 된다. 계획판은 그대로 둔다 -- "
                f"`!계획 보기` 로 확인하고 `!계획 버림` 하거나 실제 트리를 정리하라")
    파일수 = len([l for l in _git(판, "diff", "--name-only").stdout.splitlines() if l.strip()])
    _끄기(repo, s)
    시말 = "리허설 초록 뒤" if not 건너뛰기 else "**리허설 건너뜀**"
    return (f"[{s['id']}] 적용됨 -- {파일수}개 파일이 실제 트리(index)에 올랐다 ({시말}, 승인: {누가}). "
            f"커밋은 git_sync 가 한다")


def 버림(repo=None) -> str:
    repo = Path(repo or REPO)
    s = 읽기(repo)
    if not s:
        return "계획판이 꺼져 있다"
    _끄기(repo, s)
    return f"[{s['id']}] 버렸다 -- 실제 트리는 처음부터 안 건드렸다"


def _끄기(repo: Path, s: dict) -> None:
    판 = s.get("판")
    if 판:
        _git(repo, "worktree", "remove", "--force", 판)
        _git(repo, "worktree", "prune")
    p = repo / 상태상대
    if p.is_file():
        p.unlink()


def 상태(repo=None) -> str:
    s = 읽기(repo)
    if not s:
        return "계획판 꺼짐"
    시 = s.get("시험") or {}
    시말 = ("시험 안 함" if not 시 else
          ("초록" if 시.get("통과") else "빨강") + (" (그 뒤 또 바뀜)" if 시.get("해시") != _해시(Path(s["판"])) else ""))
    return f"계획판 켜짐 [{s['id']}] 요청: {s['요청'][:80]} (그림자 {Path(s['판']).name}) · 리허설: {시말}"


def main() -> int:
    ap = argparse.ArgumentParser(description="계획판(그림자 diff 승인)")
    ap.add_argument("--상태", action="store_true")
    ap.add_argument("--켜기", default="")
    ap.add_argument("--보기", action="store_true")
    ap.add_argument("--시험", action="store_true")
    ap.add_argument("--전부", action="store_true", help="레포 전체 시뮬(회귀)까지")
    ap.add_argument("--승인", action="store_true")
    ap.add_argument("--건너뛰기", action="store_true", help="리허설 없이 승인(사람이 명시할 때만)")
    ap.add_argument("--버림", action="store_true")
    ap.add_argument("--저장소", default="")
    a = ap.parse_args()
    repo = Path(a.저장소) if a.저장소 else None
    if a.켜기:
        print(켜기(a.켜기, repo))
    elif a.보기:
        print(보기(repo))
    elif a.시험:
        print(시험하기(repo, 전부=a.전부))
    elif a.승인:
        print(승인(repo, 건너뛰기=a.건너뛰기))
    elif a.버림:
        print(버림(repo))
    else:
        print(상태(repo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
