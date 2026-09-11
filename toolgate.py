"""도구 호출 시점 게이트 -- 명령이 **돌기 전에** 본다. 커밋 게이트(gates/)의 앞단이다.

gates/ 는 커밋 경로에 있다. 그래서 G020 이 게이트 삭제를 잡는 것은 **이미 지운 뒤**,
git_sync 가 커밋하려는 순간이다. 그 사이에 봇은 지워진 게이트 없이 돌고, 사용자는
"지웠다" 는 답을 먼저 본다. 실행 전에 거절하면 그 창이 없다 -- Claude Code 의
PreToolUse 훅이 하는 일을 run_shell 앞에 둔 것이다.

규칙은 **닫힌 목록**이고 하나하나 이 저장소가 겪은 사고나 CLAUDE.md 의 금지에 묶여
있다. 넓게 잡지 않는다 -- 늘 우는 경보는 아무도 안 듣고, 관리 채널의 셸 전권은 사용자가
명시 요청한 것이라 좁혀서는 안 된다. 읽기(cat · grep · git diff · ls)는 무엇이든 통과한다.

경로 게이트(`경로풀기`)는 edit_file · read_file 이 쓴다: 저장소 밖 · .git · .env · 게이트
파일 · 판정 원장은 편집 도구로 못 만진다(게이트는 self_challenge 승격으로만 생기고 고침은
사람 리뷰, 원장은 각 모듈이 덧쓴다).

쓰기:
    python3 toolgate.py '<셸 명령>'     # 0 통과 · 1 차단(까닭을 찍는다)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent

판정원장 = r"(eval/ledger\.jsonl|router/ledger\.jsonl|graph/edges\.jsonl|intent/ledger\.jsonl)"
# 한 명령 토막 안에서(파이프·세미콜론·& 를 안 넘는다).
_안 = r"[^|;&\n]*"
# 단일 > 만. >> 는 덧쓰기라 원장에 허용된다.
_덮어쓰기 = r"(?<![>&])>(?!>)\s*"
# **동사는 명령 자리에서만 잡는다** -- 줄 처음 · `|;&(` 뒤 · sudo 뒤. 따옴표 안의 rm 은
# 명령이 아니다(실측: 첫 판이 `grep -n 'rm -rf' gates/*.py` 를 게이트 삭제로 찍었다 --
# 늘 우는 경보는 아무도 안 듣는다). 그래서 `bash -c 'rm -rf gates/'` 같은 **우회는 못
# 막는다** -- 이 게이트는 실수를 막지 적대적 우회를 막지 않는다. 우회는 커밋 게이트(G020)가
# 뒤에서 잡는다. 두 겹이다.
_명령자리 = r"(?:^|[|;&(`])\s*(?:sudo\s+(?:-\S+\s+)*)?"


def _동사(*동사들: str) -> str:
    return _명령자리 + r"(?:" + "|".join(동사들) + r")\b"


# git 전역 옵션: -C <경로> · -c <k=v> · --no-pager 같은 --옵션. 이것들 다음이 하위 명령이다.
_git옵션 = r"\s+(?:-[Cc]\s+\S+\s+|--?[a-zA-Z][\w-]*(?:=\S+)?\s+)*"


# (이름, 정규식, 까닭). 까닭에는 근거가 적힌다 -- 규칙만 있고 까닭이 없으면 다음 사람이 푼다.
규칙들 = [
    ("게이트 삭제·이동",
     re.compile(_동사("rm", "mv", "truncate", "shred") + rf"{_안}\bgates/", re.M),
     "게이트는 지우거나 옮기지 않는다 (G020, 사고 1a82685: 제약이 조용히 사라짐)"),
    ("게이트에 쓰기",
     re.compile(rf"({_덮어쓰기}gates/\S+|{_동사('cp', 'tee')}{_안}\bgates/|{_동사('sed')}{_안}\s-i{_안}\bgates/)", re.M),
     "게이트 파일에 직접 쓰지 않는다 -- self_challenge prove 로 승격하고, 고침은 사람 리뷰"),
    ("판정 원장 덮어쓰기",
     re.compile(rf"({_덮어쓰기}{판정원장}|{_동사('rm', 'truncate', 'shred')}{_안}\b{판정원장}|{_동사('sed')}{_안}\s-i{_안}\b{판정원장})", re.M),
     "판정 원장은 append-only 다 (G020). 덧쓰기(>>)는 된다 -- 각 모듈이 그렇게 적는다"),
    ("통째 삭제",
     re.compile(_동사("rm") + r"\s+(-[a-zA-Z]*r[a-zA-Z]*|--recursive)\s+(--?\S+\s+)*(/|\.|\*|~|\$HOME|/home\S*|" + re.escape(str(REPO)) + r")(\s|$|/\s|/$)", re.M),
     "저장소·홈을 통째로 지우지 않는다"),
    # git 은 **하위 명령 자리**만 본다 -- `git commit -m 'rebase 금지'` 의 rebase 는 메시지다
    # (실측: 첫 판이 그것을 rebase 로 찍었다). git 뒤에는 전역 옵션(-C 경로 · -c k=v · --no-pager)
    # 만 올 수 있고 그 다음 낱말이 하위 명령이다.
    ("force push",
     re.compile(_동사("git") + rf"{_git옵션}push\b{_안}(--force\b|--force-with-lease\b|\s-f\b)", re.M),
     "CLAUDE.md: --force / --force-with-lease 금지 -- 봇 커밋과 다른 세션의 일이 통째로 사라진다"),
    ("rebase",
     re.compile(_동사("git") + rf"{_git옵션}rebase\b", re.M),
     "CLAUDE.md: 봇이 같이 쓰는 브랜치에서 rebase 금지 -- merge 를 써라 (실측 4회 사고)"),
    ("자기 셸 살해",
     re.compile(_동사("pkill") + r"\s+(-\S+\s+)*-f\s+['\"]?(python|claude|discord|bash|se[-_])", re.M),
     "CLAUDE.md: pkill -f 는 명령줄에 그 말이 든 자기 셸까지 죽인다 -- pgrep -af 로 PID 를 보고 kill"),
]

# 편집 도구가 못 만지는 자리. 읽기는 .env 만 막는다(비밀값).
_편집금지 = (re.compile(r"^gates/[^/]+\.py$"), re.compile("^" + 판정원장 + "$"),
          re.compile(r"^\.git(/|$)"), re.compile(r"^\.env(\.|$)"),
          re.compile(r"^self_challenge\.py$"), re.compile(r"^gatekeeper\.py$"))
_읽기금지 = (re.compile(r"^\.env(\.|$)"), re.compile(r"^\.git/"))


def 검사(명령: str) -> str:
    """차단이면 까닭을, 통과면 빈 문자열을 돌려준다."""
    명령 = 명령 or ""
    for 이름, 꼴, 까닭 in 규칙들:
        if 꼴.search(명령):
            return f"[{이름}] {까닭}"
    return ""


def 경로풀기(path: str, 쓰기: bool = False, repo=None) -> Path:
    """저장소 안 상대경로로 푼다. 밖이거나 금지 자리면 ValueError."""
    repo = Path(repo or REPO).resolve()
    rel = (path or "").strip()
    if not rel or rel.startswith(("~",)):
        raise ValueError(f"경로가 비었거나 홈을 가리킨다: {path!r}")
    p = (repo / rel).resolve() if not rel.startswith("/") else Path(rel).resolve()
    if p != repo and repo not in p.parents:
        raise ValueError(f"저장소 밖의 경로는 만질 수 없다: {path!r}")
    안 = str(p.relative_to(repo))
    금지들 = _편집금지 if 쓰기 else _읽기금지
    for 꼴 in 금지들:
        if 꼴.search(안):
            what = "편집" if 쓰기 else "읽기"
            raise ValueError(f"{안} 은(는) 도구로 {what}할 수 없는 자리다 -- "
                             + ("게이트는 self_challenge 승격으로, 원장은 각 모듈이 덧쓴다, "
                                "비밀값·.git 은 손대지 않는다" if 쓰기 else "비밀값이다"))
    return p


def main() -> int:
    if len(sys.argv) < 2:
        print("쓰기: python3 toolgate.py '<셸 명령>'")
        return 3
    까닭 = 검사(" ".join(sys.argv[1:]))
    if 까닭:
        print(f"차단 {까닭}")
        return 1
    print("통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
