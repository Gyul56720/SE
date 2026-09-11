"""impact -- "이 코드를 고치면 **무엇이 딸려 움직이는가**" 를 코드가 센다.

사용자(2026-09-11): "봇이 '만약에 코드를 이렇게 고치면 발생하는 모든 경우의 수' 를 파악해야 한다."

실측(바로 이 저장소에서, 같은 날): git_sync 가 부르는 것을 게이트 하나에서 문지기 셋으로
바꿨다. 문지기 안에 **검사 전체 + GitHub 조회**를 넣었는데, `git_sync` 는 관리 채널
**답변 경로 안에서** 돈다(_handle_admin_message -> GIT_LOCK -> run_in_executor). 즉 사람이
답을 받기 전에 몇 분을 기다리게 되고, 기억만 적는 커밋까지 main 빨강에 인질이 된다.
**고친 사람도 그것을 안 짚었다.** 짚어 준 것은 사람의 의심이었다. 그 의심을 코드로 옮긴다.

**정직하게**: '모든 경우의 수' 를 다 세는 것은 불가능하다(정지 문제). 이것이 세는 것은 넷이다.

  1. 역의존  -- 바뀐 모듈을 **누가 임포트하는가**(전이적으로). ast 로 센다
  2. 진입점  -- 그 사슬이 **어느 입구에 닿는가**(답변 경로 · 커밋 경로 · 게이트 · 24h 루프 …)
                입구마다 '여기 닿으면 무엇이 위험한가' 를 표로 적어 둔다
  3. 검사    -- 그 변경을 **어느 검사가 덮는가**(audit.검사찾기 를 그대로 쓴다 -- 두 벌 금지)
  4. 표지    -- 바뀐 글에 새로 들어온 위험(망 호출 · 긴 잠 · subprocess · 게이트 글자)

    python3 impact.py                    # 미커밋 변경
    python3 impact.py --커밋             # HEAD~1..HEAD
    python3 impact.py --파일 a.py b.py   # 지정
    끝값 0 (보고만 한다 -- 막는 것은 commit_guard 의 일이다)
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
_건너뜀 = {".git", "venv", "__pycache__", "node_modules", "inbox"}

# 입구마다: (모듈, 그 안에 있어야 하는 이름, 왜 위험한가). 이름이 빈 문자열이면 모듈만 본다.
진입점표 = [
    ("discord_bot_server", "_handle_admin_message",
     "관리 채널 **답변 경로** -- 여기서 느려지면 사람이 답을 그만큼 기다린다(망 호출·검사 실행을 넣지 마라)"),
    ("discord_bot_server", "_git_sync_locked",
     "**커밋 경로** -- 여기서 막히면 봇이 답은 해도 아무것도 저장하지 못한다(기억·원장까지)"),
    ("discord_bot_server", "on_ready",
     "봇 기동 -- 여기서 터지면 봇이 아예 안 뜬다"),
    ("main_public", "",
     "공개 채널 -- 화이트리스트가 없는 자리다. 권한이 넓어지면 여기부터 샌다"),
    ("gatekeeper", "run_gates",
     "**게이트** -- 여기가 무력해지면 G001~G020 전부가 조용히 꺼진다"),
    ("commit_guard", "검사",
     "커밋 문지기 -- 여기가 헐거워지면 검사·CI 문이 같이 헐거워진다"),
    ("dispatch", "run",
     "고정 명령 라우팅 -- 모든 `!명령` 이 여기를 지난다"),
    ("bot_tools", "",
     "에이전트 도구 -- 봇이 부르는 손이다. 임포트가 깨지면 도구가 통째로 사라진다"),
    ("agent_memory", "",
     "기억 저장·커밋 경로"),
]

표지규칙 = [
    (r"\burllib\b|\brequests\b|urlopen|http[s]?://", "망 호출",
     "답변 경로에 닿으면 사람이 그만큼 기다린다. 시간 상한과 캐시를 확인하라"),
    (r"subprocess\.(run|Popen|call)", "바깥 프로세스",
     "시간 상한(timeout)이 있는지, 답변 경로에서 도는지 확인하라"),
    (r"time\.sleep\(\s*([1-9]\d{1,}|\d+\.\d+)\s*\)", "긴 잠",
     "답변 경로에서 자면 그대로 지연이다"),
    (r"while\s+True", "무한 되풀이",
     "멈출 조건과 바퀴 상한이 있는지 확인하라(이 저장소 규율: 3~5 바퀴)"),
    (r"run_gates|gates/|self_challenge", "게이트 글자",
     "안전장치 자체를 만진다 -- G003 이 붙들고 있는 자리인지 확인하라"),
    (r"os\.remove|shutil\.rmtree|--force|\brm\s+-rf", "지우기",
     "지운 것은 못 되돌린다. 원장·남의 커밋에 닿는지 확인하라"),
]


def _파이썬들(repo: Path) -> "list[Path]":
    out = []
    for p in repo.rglob("*.py"):
        if p.is_file() and not any(x in _건너뜀 for x in p.relative_to(repo).parts):
            out.append(p)
    return out


def _모듈이름(repo: Path, p: Path) -> str:
    rel = p.relative_to(repo).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def 임포트그래프(repo=None) -> "tuple[dict, dict]":
    """(모듈 -> 그가 임포트하는 것들, 모듈 -> 그를 임포트하는 것들). 저장소 안의 모듈만 센다."""
    repo = Path(repo or REPO)
    파일들 = _파이썬들(repo)
    이름들 = {_모듈이름(repo, p): p for p in 파일들}
    앞: dict[str, set] = {m: set() for m in 이름들}
    뒤: dict[str, set] = {m: set() for m in 이름들}
    for m, p in 이름들.items():
        try:
            나무 = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError):
            continue
        for n in ast.walk(나무):
            대상 = []
            if isinstance(n, ast.Import):
                대상 = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
                대상 = [n.module] + [f"{n.module}.{a.name}" for a in n.names]
            for d in 대상:
                # 'dig.harvest' 든 'dig' 든, 저장소 안의 모듈로 맞춰 본다
                후보 = d if d in 이름들 else d.rsplit(".", 1)[0]
                if 후보 in 이름들 and 후보 != m:
                    앞[m].add(후보)
                    뒤[후보].add(m)
    return 앞, 뒤


def 역의존(모듈: str, 뒤: dict, 깊이: int = 6) -> "list[str]":
    """그 모듈을 (전이적으로) 임포트하는 모듈들. 가까운 것부터."""
    본 = {모듈}
    층 = [모듈]
    out = []
    for _ in range(깊이):
        다음 = []
        for m in 층:
            for x in sorted(뒤.get(m, ())):
                if x not in 본:
                    본.add(x)
                    다음.append(x)
                    out.append(x)
        if not 다음:
            break
        층 = 다음
    return out


def 닿는진입점(모듈들: "set[str]", repo=None) -> "list[tuple[str, str]]":
    """그 모듈 집합이 닿는 입구와 '왜 위험한가'. (입구, 왜)."""
    repo = Path(repo or REPO)
    out = []
    for 모듈, 이름, 왜 in 진입점표:
        if 모듈 not in 모듈들:
            continue
        if 이름:
            p = repo / (모듈.replace(".", "/") + ".py")
            try:
                if 이름 not in p.read_text(encoding="utf-8", errors="replace"):
                    continue
            except OSError:
                continue
        딱지 = f"{모듈}.{이름}" if 이름 else 모듈
        out.append((딱지, 왜))
    return out


def 바뀐글(repo: Path, 커밋: bool, 파일들: "list[str]") -> str:
    args = ["diff", "HEAD~1", "HEAD"] if 커밋 else ["diff", "HEAD"]
    r = subprocess.run(["git", "-C", str(repo), *args, "--", *파일들] if 파일들 else ["git", "-C", str(repo), *args],
                       capture_output=True, text=True, timeout=60)
    return "\n".join(l for l in (r.stdout or "").splitlines() if l.startswith("+") and not l.startswith("+++"))


def 표지들(더한글: str) -> "list[tuple[str, str]]":
    out = []
    for 패턴, 이름, 왜 in 표지규칙:
        if re.search(패턴, 더한글):
            out.append((이름, 왜))
    return out


def 영향(repo=None, 커밋: bool = False, 파일들: "list[str]" = None) -> dict:
    from audit import run as A
    repo = Path(repo or REPO)
    if 파일들 is None:
        변경 = A.변경파일(repo, 커밋)
        파일들 = [] if 변경 is None else [c for c in 변경 if c.endswith(".py")]
    if not 파일들:
        return {"파일": [], "역의존": {}, "진입점": [], "검사": {}, "안덮임": [], "표지": [], "봤나": True}
    앞, 뒤 = 임포트그래프(repo)
    역: dict[str, list] = {}
    닿음: set[str] = set()
    for rel in 파일들:
        m = rel[:-3].replace("/", ".")
        if m.endswith(".__init__"):
            m = m[: -len(".__init__")]
        if m not in 뒤:
            continue
        역[rel] = 역의존(m, 뒤)
        닿음.add(m)
        닿음.update(역[rel])
    걸림, 안덮임 = A.검사찾기(repo, 파일들)
    return {"파일": 파일들, "역의존": 역, "진입점": 닿는진입점(닿음, repo), "검사": 걸림,
            "안덮임": 안덮임, "표지": 표지들(바뀐글(repo, 커밋, 파일들)), "봤나": True}


def 보고(r: dict) -> str:
    if not r["파일"]:
        return "영향: 바뀐 .py 가 없다"
    줄 = [f"영향 분석 -- 바뀐 코드 {len(r['파일'])}개: " + ", ".join(r["파일"][:6])]
    for rel, 역 in r["역의존"].items():
        줄.append(f"  {rel} 를 부르는 것 {len(역)}개" + (": " + ", ".join(역[:8]) if 역 else " (없음 -- 홀로 선 모듈)"))
    if r["진입점"]:
        줄.append("  **닿는 입구** -- 여기까지 딸려 움직인다:")
        for 딱지, 왜 in r["진입점"]:
            줄.append(f"      · {딱지}: {왜}")
    else:
        줄.append("  닿는 입구 없음 -- 봇의 산 경로에는 안 닿는다")
    if r["표지"]:
        줄.append("  **더한 글의 표지**:")
        for 이름, 왜 in r["표지"]:
            줄.append(f"      · {이름}: {왜}")
    덮는 = sorted({t for ts in r["검사"].values() for t in ts})
    줄.append(f"  덮는 검사 {len(덮는)}개" + (": " + ", ".join(Path(t).name for t in 덮는[:8]) if 덮는 else " -- **없다**"))
    if r["안덮임"]:
        줄.append("  검사 없는 변경(버그가 샌다면 여기): " + ", ".join(r["안덮임"][:5]))
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="이 변경이 무엇에 닿는지 센다(보고만 한다)")
    ap.add_argument("--커밋", action="store_true")
    ap.add_argument("--파일", nargs="*", default=None)
    ap.add_argument("--저장소", default="")
    a = ap.parse_args()
    r = 영향(Path(a.저장소) if a.저장소 else None, 커밋=a.커밋, 파일들=a.파일)
    print(보고(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
