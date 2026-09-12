"""github_write -- GitHub **쓰기는 이 좁은 문**: 지금 갈래를 밀고 PR 을 연다. 머지는 **코드가 문제를 잰 뒤**(investigate.머지위험) 문제가 없을 때만, 있으면 사람이 `!조사 머지 <번호>` 로.

격차표(SE vs Claude Code) 'GitHub 쓰기': 조회만 하던 것을 PR 생성까지. 권한을 넓히는 일이라
마지막에 두었고, 넓히는 폭도 딱 이만큼이다 -- 이 모듈에는 merge 함수가 **없다**. 머지는
사람이 GitHub 에서 누른다(이 저장소 규율: 승인 주체는 사람).

    · main 에서는 안 연다 -- 갈래를 만들어라
    · 밀기는 gitsync 규칙대로: non-fast-forward 면 merge 로 따라잡고 다시 민다. --force 없음
    · 토큰은 .env 의 GITHUB_TOKEN (dig/harvest 와 같은 env값) -- 없으면 `!열쇠 GITHUB_TOKEN=...` 을 청한다
    · HTTP 요청은 주입 가능(요청) -- 검사는 망 없이 가짜로 돈다

    python3 github_write.py --title '...' --body '...'        # 끝값 0 열림 · 1 거절/실패 · 3 토큰 없음
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.request
from pathlib import Path

import gitsync

REPO = Path(__file__).resolve().parent
API = "https://api.github.com"
요청 = None      # (method, url, headers, data:bytes|None) -> (status:int, body:str)  -- 검사가 꽂는다


def 저장소이름() -> str:
    return os.environ.get("SE_REPO", "Gyul56720/SE").strip() or "Gyul56720/SE"


def 토큰(repo=None) -> str:
    try:
        from dig.harvest import env값
        return (env값("GITHUB_TOKEN", repo) or "").strip()
    except Exception:                                  # noqa: BLE001
        return (os.environ.get("GITHUB_TOKEN") or "").strip()


def _요청기본(method: str, url: str, headers: dict, data: "bytes | None"):
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def _git(repo: Path):
    def run(args):
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=120)
    return run


def 밀기(repo=None) -> "tuple[bool, str, str]":
    """지금 갈래를 origin 에 민다. (됐나, 갈래, 무슨 일). main 은 거절. --force 는 없다."""
    repo = Path(repo or REPO)
    git = _git(repo)
    br = git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    if not br or br in ("HEAD", "main", "master"):
        return False, br, f"`{br or 'HEAD'}` 에서는 PR 을 못 연다 -- 갈래를 만들어 거기서 열어라"
    p = git(["push", "-u", "origin", br])
    if p.returncode == 0:
        return True, br, "밀었다"
    caught, why = gitsync.reconcile(git)
    if not caught:
        return False, br, f"밀기 실패 뒤 따라잡기도 실패: {why}"
    p2 = git(["push", "-u", "origin", br])
    if p2.returncode != 0:
        return False, br, f"따라잡고도 밀기 실패: {p2.stderr.strip()[:200]}"
    return True, br, f"{why} 뒤 밀었다"


def pr만들기(title: str, body: str = "", base: str = "main", repo=None) -> dict:
    """PR 을 연다. 돌려주는 것: {됐나, url, 번호, 갈래, 왜}. 머지는 하지 않는다."""
    repo = Path(repo or REPO)
    title = (title or "").strip()
    if not title:
        return {"됐나": False, "왜": "제목이 비었다", "갈래": "", "url": "", "번호": 0}
    tok = 토큰(repo)
    if not tok:
        return {"됐나": False, "갈래": "", "url": "", "번호": 0,
                "왜": "GITHUB_TOKEN 이 없다 -- 사람만 발급할 수 있다. `!열쇠 GITHUB_TOKEN=<값>` 꼴로 청하라"}
    됐나, br, 말 = 밀기(repo)
    if not 됐나:
        return {"됐나": False, "왜": 말, "갈래": br, "url": "", "번호": 0}
    payload = json.dumps({"title": title[:250], "body": body or "", "head": br, "base": base}).encode("utf-8")
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
               "Content-Type": "application/json", "User-Agent": "SE-agent"}
    status, text = (요청 or _요청기본)("POST", f"{API}/repos/{저장소이름()}/pulls", headers, payload)
    try:
        j = json.loads(text) if text else {}
    except ValueError:
        j = {}
    if status == 201:
        return {"됐나": True, "url": j.get("html_url", ""), "번호": int(j.get("number") or 0), "갈래": br,
                "왜": f"{말} · 열렸다 -- 머지는 코드가 문제를 잰 뒤 정한다(문제 없으면 붙인다)"}
    if status == 422 and "already exists" in text:
        return {"됐나": False, "갈래": br, "url": "", "번호": 0,
                "왜": f"{br} 의 PR 이 이미 열려 있다 -- 새로 열 것 없이 그 PR 을 보라"}
    msg = (j.get("message") or text)[:200]
    return {"됐나": False, "갈래": br, "url": "", "번호": 0, "왜": f"GitHub 가 {status} 로 거절: {msg}"}


def _헤더(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
            "Content-Type": "application/json", "User-Agent": "SE-agent"}


def _GET(url: str, tok: str):
    status, text = (요청 or _요청기본)("GET", url, _헤더(tok), None)
    try:
        return status, (json.loads(text) if text else None)
    except ValueError:
        return status, None


def 열린pr(갈래: str = "", 제목에: str = "", repo=None) -> dict:
    """열린 PR 하나 -- 갈래(head.ref)가 같거나 제목에 그 글이 든 것. {됐나, 번호, url, 갈래, 제목, 왜}."""
    tok = 토큰(repo)
    if not tok:
        return {"됐나": False, "번호": 0, "url": "", "갈래": "", "제목": "", "왜": "GITHUB_TOKEN 이 없다"}
    status, j = _GET(f"{API}/repos/{저장소이름()}/pulls?state=open&per_page=50", tok)
    if status != 200 or not isinstance(j, list):
        return {"됐나": False, "번호": 0, "url": "", "갈래": "", "제목": "", "왜": f"GitHub 가 {status} 로 답했다"}
    for pr in j:
        ref = (pr.get("head") or {}).get("ref") or ""
        if (갈래 and ref == 갈래) or (제목에 and 제목에 in (pr.get("title") or "")):
            return {"됐나": True, "번호": int(pr.get("number") or 0), "url": pr.get("html_url", ""),
                    "갈래": ref, "제목": pr.get("title", ""), "왜": ""}
    return {"됐나": False, "번호": 0, "url": "", "갈래": "", "제목": "", "왜": f"열린 PR 이 없다 (갈래 {갈래!r} · 제목 {제목에!r})"}


def pr상태(번호: int, repo=None) -> dict:
    """머지 판단에 필요한 사실만: {됐나, 머지됨, 겹침, 상태, 갈래, 더함, 뺌, 파일들:[{경로,상태,더함,뺌}], 검사:[{이름,상태,결론}], 왜}."""
    tok = 토큰(repo)
    if not tok:
        return {"됐나": False, "왜": "GITHUB_TOKEN 이 없다"}
    base = f"{API}/repos/{저장소이름()}"
    status, pr = _GET(f"{base}/pulls/{int(번호)}", tok)
    if status != 200 or not isinstance(pr, dict):
        return {"됐나": False, "왜": f"PR #{번호} 를 못 읽었다 ({status})"}
    _, 파일 = _GET(f"{base}/pulls/{int(번호)}/files?per_page=100", tok)
    파일들 = [{"경로": f.get("filename", ""), "상태": f.get("status", ""), "더함": int(f.get("additions") or 0),
             "뺌": int(f.get("deletions") or 0)} for f in (파일 if isinstance(파일, list) else [])]
    sha = (pr.get("head") or {}).get("sha") or ""
    _, cr = _GET(f"{base}/commits/{sha}/check-runs", tok) if sha else (0, None)
    검사 = [{"이름": c.get("name", ""), "상태": c.get("status", ""), "결론": c.get("conclusion") or ""}
          for c in ((cr or {}).get("check_runs") or [])] if isinstance(cr, dict) else []
    return {"됐나": True, "머지됨": bool(pr.get("merged")), "겹침": pr.get("mergeable") is False,
            "상태": pr.get("mergeable_state") or "", "갈래": (pr.get("head") or {}).get("ref") or "",
            "더함": int(pr.get("additions") or 0), "뺌": int(pr.get("deletions") or 0),
            "파일들": 파일들, "검사": 검사, "url": pr.get("html_url", ""), "왜": ""}


def pr머지하기(번호: int, repo=None) -> dict:
    """PR 을 머지한다(merge 커밋). {됐나, sha, 왜}. **여기는 판단하지 않는다** -- 부르는 쪽이 판정을 끝낸 뒤에만 온다."""
    tok = 토큰(repo)
    if not tok:
        return {"됐나": False, "sha": "", "왜": "GITHUB_TOKEN 이 없다"}
    payload = json.dumps({"merge_method": "merge"}).encode("utf-8")
    status, text = (요청 or _요청기본)("PUT", f"{API}/repos/{저장소이름()}/pulls/{int(번호)}/merge", _헤더(tok), payload)
    try:
        j = json.loads(text) if text else {}
    except ValueError:
        j = {}
    if status == 200 and j.get("merged"):
        return {"됐나": True, "sha": str(j.get("sha", ""))[:12], "왜": "머지됨"}
    return {"됐나": False, "sha": "", "왜": f"GitHub 가 {status} 로 거절: {(j.get('message') or text or '')[:160]}"}


def 보고(r: dict) -> str:
    if r["됐나"]:
        return f"PR #{r['번호']} 열림 <{r['url']}> (갈래 {r['갈래']}) -- {r['왜']}"
    return f"PR 못 엶 -- {r['왜']}"


def main() -> int:
    ap = argparse.ArgumentParser(description="지금 갈래를 밀고 PR 을 연다 (머지는 코드가 잰 뒤)")
    ap.add_argument("--title", required=True)
    ap.add_argument("--body", default="")
    ap.add_argument("--base", default="main")
    ap.add_argument("--저장소", default="")
    a = ap.parse_args()
    r = pr만들기(a.title, a.body, a.base, repo=Path(a.저장소) if a.저장소 else None)
    print(보고(r))
    if r["됐나"]:
        return 0
    return 3 if "GITHUB_TOKEN" in r["왜"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
