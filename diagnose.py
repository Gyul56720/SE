"""diagnose -- 증상에서 **증거를 캐고 가설을 판정한다.** 모델에게 묻기 전에.

사용자(2026-09-11): "왜 나의 에이전트는 이런 식의 사고과정을 거치면서 스스로 해결하지
못하는거야? 너의 사고 과정처럼 나의 에이전트로 사고하면서 스스로 문제를 찾고 코드를
수정하게 만들어줘."

맞는 물음이다. `repair` 는 **증상을 모델에 넘기는** 루프다: 실측 -> dig/graph 로 참고를
모으고 -> 모델이 패치를 제안 -> 판에서 재현. 그런데 같은 자리에서 두 번 막혔을 때 내가
실제로 한 일은 그것이 아니었다.

    트레이스백의 줄번호를 읽었다 -> 지금 HEAD 의 그 함수는 거기가 아니다
    -> 옛 커밋들을 짚어 보니 `fae206d` 의 줄번호와 맞는다
    -> **도는 코드가 낡았다.** 고침이 틀린 게 아니라 도착하지 않은 것이다
    -> 그러면 고침을 파일 안에 두는 방식 자체가 틀렸다 -> 부르는 쪽을 고친다

이 중 어디에도 모델이 필요 없다. 전부 **저장소에 적혀 있는 사실**이다. 그런데 에이전트는
그것을 캘 줄 몰라서 "제안없음" 을 냈고, 열쇠를 못 찾았을 때는 사람 탓으로 돌렸다.

그래서 여기 두는 것은 **결정적 탐침들**이다. 모델이 없어도 돈다(키가 없을 때도 돈다는
뜻이다 -- 그때가 바로 도움이 가장 필요한 때다).

  판이낡았나   트레이스백의 (파일·줄·함수) 가 지금 HEAD 와 맞는가. 안 맞으면 **어느
               커밋의 줄번호와 맞는지** 찾아 준다 -- '도는 코드가 낡았다' 를 코드가 판정
  머지했나     그 파일을 건드린 내 커밋이 origin/main 밖에 있는가 (이 저장소가 여섯 번 앓은 병)
  모듈이어디에 `No module named X` 에서 X 가 **저장소 안에 있는가**. 있으면 없는 게 아니라
               sys.path 문제다 -- 고칠 길이 전혀 다르다
  부르는꼴     그 진입점을 스크립트 꼴로 부르는가 (entrypoints)
  전에났나     같은 지문이 원장에 있는가. **고친 뒤에 또 났으면** 원인이 코드가 아니라 도달이다
  열쇠         빈 후보 풀·쿼터 꼴이면 값의 꼴로 훑어 무엇이 있는지 적는다

각 가설은 **판정명령**을 들고 다닌다 -- 사람도 에이전트도 그 끝값으로 다시 확인할 수 있다.

    python3 -m diagnose --글 "$(cat logs/improve.log)"
    python3 -m diagnose --파일 logs/improve.log --json
끝값: 0 가설을 짚었다 · 3 증상을 못 읽었다 · 1 읽었으나 짚을 것이 없다
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_자리꼴 = re.compile(r'File "([^"]+)", line (\d+), in (\S+)')
_예외꼴 = re.compile(r"^(\w+(?:Error|Exception|Warning))(?::\s*(.*))?$", re.M)
_없는모듈꼴 = re.compile(r"No module named '([^']+)'")


# ------------------------------------------------------------------ 증상 읽기
def 증상파싱(글: str, repo=None) -> dict:
    """트레이스백에서 **다툴 수 없는 사실**만 뽑는다. 해석은 뒤에서 한다."""
    repo = Path(repo or REPO)
    글 = 글 or ""
    자리 = []
    for m in _자리꼴.finditer(글):
        파일, 줄, 함수 = m.group(1), int(m.group(2)), m.group(3)
        rel = 파일
        for 뿌리표 in (str(repo), "/home/ubuntu/SE", "/home/user/SE"):
            if 파일.startswith(뿌리표 + "/"):
                rel = 파일[len(뿌리표) + 1:]
                break
        자리.append({"파일": rel, "원래경로": 파일, "줄": 줄, "함수": 함수})
    예외, 말 = "", ""
    for m in _예외꼴.finditer(글):
        예외, 말 = m.group(1), (m.group(2) or "").strip()
    없는 = _없는모듈꼴.search(글)
    return {"예외": 예외, "말": 말, "자리": 자리,
            "없는모듈": 없는.group(1).split(".")[0] if 없는 else "",
            "지문": f"{예외}:{(없는.group(1) if 없는 else 말)[:60]}"}


def _git(repo: Path, *a, 초=30) -> "tuple[int, str]":
    try:
        p = subprocess.run(["git", "-C", str(repo), *a], capture_output=True,
                           text=True, errors="replace", timeout=초)
        return p.returncode, (p.stdout or "")
    except (OSError, subprocess.SubprocessError):
        return 127, ""


def _함수가_그줄을_덮나(본: str, 함수: str, 줄: int) -> bool:
    """그 판의 그 파일에서 `함수` 가 `줄` 을 품는가. ast 로 본다 -- 눈대중이 아니다."""
    try:
        나무 = ast.parse(본)
    except SyntaxError:
        return False
    for n in ast.walk(나무):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 함수:
            끝 = getattr(n, "end_lineno", None) or n.lineno
            if n.lineno <= 줄 <= 끝:
                return True
    if 함수 in ("<module>", "<string>"):
        return 0 < 줄 <= len(본.splitlines())
    return False


# ------------------------------------------------------------------ 탐침들
def 판이낡았나(자리: dict, repo=None, 몇=60) -> dict:
    """**이 탐침이 이 모듈의 요점이다.**

    트레이스백의 (파일·줄·함수) 가 지금 HEAD 와 안 맞으면, 옛 커밋들을 짚어 **어느 판의
    줄번호와 맞는지** 찾는다. 맞는 판이 나오면 도는 코드는 그 판이다 -- 고침이 틀린 게
    아니라 **도착하지 않은 것**이다. 이 둘은 고칠 길이 완전히 다르다."""
    repo = Path(repo or REPO)
    파일, 줄, 함수 = 자리["파일"], 자리["줄"], 자리["함수"]
    p = repo / 파일
    if not p.is_file():
        return {"이름": "판이낡았나", "판정": "모름", "말": f"{파일} 이 지금 트리에 없다"}
    본 = p.read_text(encoding="utf-8", errors="replace")
    if _함수가_그줄을_덮나(본, 함수, 줄):
        return {"이름": "판이낡았나", "판정": "아니다",
                "말": f"{파일}:{줄} 의 `{함수}` 가 지금 HEAD 와 맞는다 -- 도는 코드는 최신이다"}
    rc, out = _git(repo, "log", f"-{몇}", "--format=%H %h %s", "--", 파일)
    if rc != 0:
        return {"이름": "판이낡았나", "판정": "모름", "말": "git log 를 못 읽었다"}
    for line in out.splitlines():
        sha, 짧, 제목 = (line.split(" ", 2) + ["", ""])[:3]
        rc2, 옛 = _git(repo, "show", f"{sha}:{파일}")
        if rc2 != 0:
            continue
        if _함수가_그줄을_덮나(옛, 함수, 줄):
            rc3, _ = _git(repo, "merge-base", "--is-ancestor", sha, "HEAD")
            return {"이름": "판이낡았나", "판정": "그렇다", "커밋": 짧,
                    "말": (f"**도는 코드가 낡았다.** {파일}:{줄} 의 `{함수}` 는 지금 HEAD 가 아니라 "
                           f"`{짧}` ({제목[:40]}) 의 줄번호와 맞는다."
                           + (" 그 커밋은 HEAD 의 조상이다 -- 고침이 그 뒤에 있다."
                              if rc3 == 0 else " 그 커밋은 HEAD 계보에 없다.")),
                    "고칠거리": (("코드를 또 고치지 마라. 둘 중 하나다: **고침이 아직 안 닿았거나**(머지·배포를 "
                                 "보라), **이 트레이스백이 옛 실행의 것**이다(로그가 덧쓰기면 옛 줄이 남는다 -- "
                                 "이 실행이 쓴 출력만 다시 보라). `python3 -m diagnose --도달 <커밋>` 이 가른다.")
                                if rc3 == 0 else
                                "코드를 또 고치지 마라. **고침이 도착하지 않은 것이다.** 머지됐는지 · 배포가 돌았는지 보라."),
                    "판정명령": f"git log -1 --format=%h -- {파일}"}
    return {"이름": "판이낡았나", "판정": "모름",
            "말": f"{파일}:{줄} 의 `{함수}` 가 최근 {몇}개 판 어디와도 안 맞는다 (판이 아주 낡았거나 남의 트리다)"}


def 도달확인(커밋: str, repo=None) -> dict:
    """트레이스백이 가리키는 판(`커밋`)과 **지금 도는 판**·origin/main 을 견준다.

    지금 HEAD 가 그 판의 후손이면 그 트레이스백은 지금 코드에서 날 수 없다 -- 옛 실행의
    글이다(또는 프로세스가 배포 전에 떠 있던 것). HEAD 가 origin/main 뒤면 배포가 안 닿았다."""
    repo = Path(repo or REPO)
    rc, head = _git(repo, "rev-parse", "--short", "HEAD")
    head = head.strip()
    rc1, _ = _git(repo, "merge-base", "--is-ancestor", 커밋, "HEAD")
    후손 = rc1 == 0
    _git(repo, "fetch", "-q", "origin", "main", 초=60)
    rc2, 뒤 = _git(repo, "rev-list", "--count", "HEAD..origin/main")
    뒤 = int(뒤.strip() or 0) if rc2 == 0 else -1
    if 후손 and 뒤 == 0:
        return {"이름": "도달확인", "판정": "그렇다", "말":
                f"**지금 판 {head} 는 origin/main 과 같고 `{커밋}` 의 후손이다.** 그 트레이스백은 지금 "
                "코드에서 날 수 없다 -- 옛 실행의 글이거나, 배포 전에 떠 있던 프로세스의 것이다.",
                "고칠거리": "고칠 코드가 없다. 이 실행이 쓴 출력만 보라(덧쓰기 로그의 옛 줄을 읽지 마라)."}
    if 후손 and 뒤 > 0:
        return {"이름": "도달확인", "판정": "그렇다", "말":
                f"지금 판 {head} 는 `{커밋}` 의 후손이지만 **origin/main 보다 {뒤}커밋 뒤다** -- 배포가 안 닿았다.",
                "고칠거리": "배포(또는 git pull)가 돌아야 한다. 코드를 고칠 일이 아니다."}
    if not 후손:
        return {"이름": "도달확인", "판정": "그렇다", "말":
                f"지금 판 {head} 는 `{커밋}` 의 후손이 아니다 -- 다른 갈래거나 되돌려진 판이다.",
                "고칠거리": "어느 갈래가 배포됐는지 보라."}
    return {"이름": "도달확인", "판정": "모름", "말": f"origin/main 을 못 읽었다 (판 {head})"}


def 머지했나(파일: str, repo=None) -> dict:
    """그 파일을 건드린 내 커밋이 origin/main 밖에 있는가.

    이 저장소가 여섯 번 앓은 병이다 -- 고쳐 놓고 머지를 안 해서, 사람은 안 바뀐 숫자를
    보고 '고침이 무력하다' 고 읽는다."""
    repo = Path(repo or REPO)
    rc, out = _git(repo, "log", "--format=%h %s", "origin/main..HEAD", "--", 파일)
    if rc != 0:
        return {"이름": "머지했나", "판정": "모름", "말": "origin/main 을 못 읽었다 (fetch 가 필요할 수 있다)"}
    줄들 = [l for l in out.splitlines() if l.strip()]
    if not 줄들:
        return {"이름": "머지했나", "판정": "아니다", "말": f"{파일} 을 건드린 커밋이 전부 origin/main 에 있다"}
    return {"이름": "머지했나", "판정": "그렇다",
            "말": f"**{파일} 을 건드린 커밋 {len(줄들)}개가 origin/main 밖에 있다**: "
                  + "; ".join(줄들[:3]),
            "고칠거리": "밀고 · PR 내고 · **바로 머지**한 뒤에야 그 변경을 쓰는 명령을 줘라 (CLAUDE.md)",
            "판정명령": f"git log --oneline origin/main..HEAD -- {파일}"}


def 모듈이어디에(이름: str, repo=None) -> dict:
    """`No module named X` 에서 X 가 **저장소 안에 있는가.**

    있으면 '없는' 것이 아니라 sys.path 가 못 닿는 것이다 -- 고칠 길이 전혀 다르다.
    (설치하라고 하면 안 된다. 실측: 이 착각이 `plan` 에서 두 번 났다.)"""
    repo = Path(repo or REPO)
    꾸 = repo / 이름
    있 = (꾸.is_dir() and (꾸 / "__init__.py").is_file()) or (repo / f"{이름}.py").is_file()
    if not 있:
        return {"이름": "모듈이어디에", "판정": "아니다",
                "말": f"`{이름}` 은 저장소에 없다 -- 바깥 꾸러미다(설치·requirements 를 보라)"}
    return {"이름": "모듈이어디에", "판정": "그렇다",
            "말": f"**`{이름}` 은 저장소 안에 있다** ({이름}/ 또는 {이름}.py). 없는 게 아니라 "
                  f"sys.path 가 못 닿는 것이다 -- 설치할 것이 아니다.",
            "고칠거리": "부르는 쪽을 `python3 -m 꾸러미.모듈` 로 바꿔라 (sys.path[0] 이 뿌리가 된다)",
            "판정명령": f"python3 -c 'import {이름}'"}


def 부르는꼴(파일: str, repo=None) -> dict:
    """그 진입점을 스크립트 꼴로 부르는 자리가 있는가 (entrypoints 가 센다)."""
    repo = Path(repo or REPO)
    try:
        import entrypoints as E
    except ImportError:
        return {"이름": "부르는꼴", "판정": "모름", "말": "entrypoints 를 못 들였다"}
    for x in E.스크립트꼴호출(repo):
        if x["파일"] == 파일:
            남 = [c for c in x["부른곳"] if c != 파일]
            return {"이름": "부르는꼴", "판정": "그렇다",
                    "말": f"**{파일} 을 스크립트 꼴로 부르는 자리가 있다**: {', '.join(남[:3]) or '제 문서'}",
                    "고칠거리": f"`python3 -m {x['모듈']}` 로 부르면 파일이 어떤 판이든 산다",
                    "판정명령": "python3 entrypoints.py --위험만"}
    return {"이름": "부르는꼴", "판정": "아니다", "말": f"{파일} 은 스크립트 꼴로 안 불린다"}


def 전에났나(지문: str, repo=None) -> dict:
    """같은 지문이 원장에 있는가. **고친 뒤에 또 났으면** 원인이 코드가 아니라 도달이다."""
    repo = Path(repo or REPO)
    본것 = []
    for rel in ("repair/ledger.jsonl", "improve/ledger.jsonl"):
        p = repo / rel
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if 지문 and 지문[:40] in json.dumps(d, ensure_ascii=False):
                본것.append(d)
    if not 본것:
        return {"이름": "전에났나", "판정": "아니다", "말": "원장에 같은 지문이 없다 -- 처음 보는 증상이다"}
    고친적 = [d for d in 본것 if d.get("해결") or d.get("판정") in ("해결", "고침")]
    if 고친적:
        return {"이름": "전에났나", "판정": "그렇다", "말":
                f"**전에 {len(본것)}번 났고 그중 {len(고친적)}번은 '고쳤다' 고 적혀 있다.** "
                "고친 것이 또 났다면 원인은 코드가 아니라 **도달**이다(머지·배포·부르는 꼴).",
                "고칠거리": "같은 패치를 또 내지 마라. 판이낡았나 · 머지했나 · 부르는꼴 을 먼저 보라",
                "판정명령": "python3 -m diagnose --파일 <로그>"}
    return {"이름": "전에났나", "판정": "그렇다",
            "말": f"전에 {len(본것)}번 났는데 아직 안 고쳐졌다 -- 되풀이되는 증상이다"}


def 열쇠(repo=None) -> dict:
    """빈 후보 풀·쿼터 꼴이면 **무엇이 있는지** 적는다. 사람 탓으로 돌리기 전에."""
    try:
        from orchestrator import llm_pool as L
        말 = L.키찾은꼴()
    except Exception as e:
        return {"이름": "열쇠", "판정": "모름", "말": f"열쇠를 못 봤다: {type(e).__name__}"}
    if 말.startswith("키 "):
        return {"이름": "열쇠", "판정": "아니다", "말": f"{말} -- 키는 있다. 쿼터·한도를 보라"}
    return {"이름": "열쇠", "판정": "그렇다", "말": 말,
            "고칠거리": ("**사람 탓으로 돌리기 전에** 위 이름들을 보라. 이름은 아무것이나 되고 "
                        "값이 `AIza…` 꼴이면 잡힌다. 정말 없을 때만 사람에게 청한다."),
            "판정명령": "python3 -c \"from orchestrator import llm_pool as L; print(L.키찾은꼴())\""}


# ------------------------------------------------------------------ 진단
def 진단(글: str, repo=None) -> dict:
    """증상 -> 증거 -> 가설(판정명령을 들고 다닌다). **모델을 안 쓴다.**"""
    repo = Path(repo or REPO)
    증 = 증상파싱(글, repo)
    결과 = {"증상": 증, "증거": [], "가설": []}
    if not 증["예외"] and not 증["자리"]:
        결과["말"] = "트레이스백을 못 읽었다 -- 증상 글이 아니다"
        return 결과

    깊 = 증["자리"][-1] if 증["자리"] else None
    if 깊:
        결과["증거"].append(판이낡았나(깊, repo))
        결과["증거"].append(머지했나(깊["파일"], repo))
        결과["증거"].append(부르는꼴(깊["파일"], repo))
    if 증["없는모듈"]:
        결과["증거"].append(모듈이어디에(증["없는모듈"], repo))
    if "빈 후보 풀" in (글 or "") or "후보" in 증["말"] or "API_KEY" in (글 or ""):
        결과["증거"].append(열쇠(repo))
    결과["증거"].append(전에났나(증["지문"], repo))

    # **순서가 곧 우선순위다.** 도는 코드가 낡았으면 다른 이야기는 전부 헛것이다 --
    # 무엇을 고쳐도 그 판에는 안 들어 있다. 그것부터 짚는다.
    차례 = ["판이낡았나", "머지했나", "모듈이어디에", "부르는꼴", "열쇠", "전에났나"]
    잰것 = {e["이름"]: e for e in 결과["증거"]}
    for 이름 in 차례:
        e = 잰것.get(이름)
        if e and e["판정"] == "그렇다" and e.get("고칠거리"):
            결과["가설"].append({"무엇": e["말"], "고칠거리": e["고칠거리"],
                               "판정명령": e.get("판정명령", ""), "탐침": 이름})
    return 결과


def 보고(d: dict) -> str:
    증 = d["증상"]
    줄 = [f"증상: {증['예외']}: {증['말'][:70]}" if 증["예외"] else "증상: (못 읽었다)"]
    if 증["자리"]:
        깊 = 증["자리"][-1]
        줄.append(f"  터진 자리: {깊['파일']}:{깊['줄']} in {깊['함수']}")
    if not d["증거"]:
        return "\n".join(줄 + ["  " + d.get("말", "짚을 것이 없다")])
    줄.append("  -- 증거(저장소가 말해 준 것, 모델 안 씀) --")
    for e in d["증거"]:
        표 = {"그렇다": "!!", "아니다": "  ", "모름": "??"}[e["판정"]]
        줄.append(f"   {표} {e['이름']:<12} {e['말']}")
    if d["가설"]:
        줄.append(f"  -- 가설 {len(d['가설'])}개 (앞엣것부터) --")
        for i, h in enumerate(d["가설"], 1):
            줄.append(f"   {i}. {h['고칠거리']}")
            if h["판정명령"]:
                줄.append(f"      확인: {h['판정명령']}")
    else:
        줄.append("  -- 짚을 가설이 없다. 여기서부터 모델에게 묻는다 --")
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="증상에서 증거를 캐고 가설을 판정한다(모델 안 씀)")
    ap.add_argument("--글", default="", help="트레이스백이 든 글")
    ap.add_argument("--파일", default="", help="그 글이 든 파일(로그)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--저장소", default="")
    ap.add_argument("--도달", default="", help="트레이스백이 가리키는 판 -- 지금 판과 견준다")
    a = ap.parse_args()
    if a.도달:
        d = 도달확인(a.도달, Path(a.저장소) if a.저장소 else None)
        print(f"{d['말']}\n  -> {d.get('고칠거리', '')}")
        return 0 if d["판정"] == "그렇다" else 1
    글 = a.글
    if a.파일:
        try:
            글 = Path(a.파일).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"파일을 못 읽었다: {e}")
            return 3
    repo = Path(a.저장소) if a.저장소 else None
    d = 진단(글, repo)
    print(json.dumps(d, ensure_ascii=False, indent=1) if a.json else 보고(d))
    if not d["증상"]["예외"] and not d["증상"]["자리"]:
        return 3
    return 0 if d["가설"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
