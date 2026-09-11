"""ci_watch -- main 의 CI(gates.yml) 마지막 결론을 **봇이 읽는다.** 빨강이면 그 검사 이름까지.

실측 2026-09-11: main 의 gates.yml 이 60회 연속 초록 0(실패 35 · 취소 25)이었다 -- 09-10 의
페르소나 전환으로 소설 검사 10개가 깨진 채, 봇이 그 위에 자가 커밋을 35번 넘게 쌓았다.
CI 는 뒤늦게 알려 주는데 **아무도 읽지 않았다**. 그래서 읽는 손을 코드에 둔다:

  · commit_guard 가 자가 수정 커밋 전에 부른다 -- 빨강이면 커밋을 막고 그 검사부터 고치게
  · 봇이 주기적으로(CI_WATCH_SEC, 기본 2h) 불러 상태가 바뀌면 관리 채널에 알린다

판정은 GitHub 의 conclusion 문자열이 한다. 조회가 안 되면 '못잼' -- 빨강으로도 초록으로도
안 친다(막기엔 근거가 없고, 통과시키기엔 모른다 -- 그래서 경고만).

    python3 ci_watch.py            # 끝값 0 초록 · 1 빨강 · 3 못잼
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent
API = "https://api.github.com"
상태상대 = "logs/ci_watch.json"
요청 = None       # (url, headers) -> (status:int, body:str)  -- 검사가 꽂는다


def 저장소이름() -> str:
    return os.environ.get("SE_REPO", "Gyul56720/SE").strip() or "Gyul56720/SE"


def _토큰(repo=None) -> str:
    try:
        from dig.harvest import env값
        return (env값("GITHUB_TOKEN", repo) or "").strip()
    except Exception:                                  # noqa: BLE001
        return (os.environ.get("GITHUB_TOKEN") or "").strip()


def _요청기본(url: str, headers: dict):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        return 0, str(e)


def _헤더(repo=None) -> dict:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "SE-agent"}
    t = _토큰(repo)
    if t:
        h["Authorization"] = f"Bearer {t}"
    return h


def 마지막실행(workflow: str = "gates.yml", branch: str = "main", repo=None) -> "dict | None":
    """branch 의 마지막 **완료된** 실행. {"결론","sha","url","번호","때","id"} 또는 None(못잼)."""
    url = f"{API}/repos/{저장소이름()}/actions/workflows/{workflow}/runs?branch={branch}&status=completed&per_page=1"
    status, body = (요청 or _요청기본)(url, _헤더(repo))
    if status != 200:
        return None
    try:
        runs = json.loads(body).get("workflow_runs") or []
    except ValueError:
        return None
    if not runs:
        return None
    r = runs[0]
    return {"결론": r.get("conclusion") or "?", "sha": (r.get("head_sha") or "")[:7], "url": r.get("html_url", ""),
            "번호": r.get("run_number", 0), "때": r.get("updated_at", ""), "id": r.get("id", 0),
            "제목": (r.get("display_title") or "")[:60]}


def 실패검사들(run_id: int, repo=None) -> "list[str]":
    """그 실행의 실패 job 로그에서 `실패 test_*.py` 줄을 뽑는다. 로그를 못 받으면 []."""
    if not run_id:
        return []
    h = _헤더(repo)
    status, body = (요청 or _요청기본)(f"{API}/repos/{저장소이름()}/actions/runs/{run_id}/jobs", h)
    if status != 200:
        return []
    try:
        jobs = json.loads(body).get("jobs") or []
    except ValueError:
        return []
    out: list[str] = []
    for j in jobs:
        if j.get("conclusion") != "failure":
            continue
        s2, log = (요청 or _요청기본)(f"{API}/repos/{저장소이름()}/actions/jobs/{j.get('id')}/logs", h)
        if s2 != 200:
            continue
        for m in re.finditer(r"실패\s+(test_[\w가-힣]+\.py)", log):
            if m.group(1) not in out:
                out.append(m.group(1))
    return out


def 보기(repo=None, 검사이름도: bool = True) -> dict:
    """{"상태": "초록"|"빨강"|"못잼", "sha","url","번호","실패":[...],"말"}."""
    r = 마지막실행(repo=repo)
    if r is None:
        return {"상태": "못잼", "sha": "", "url": "", "번호": 0, "실패": [],
                "말": "main CI 결론을 못 읽었다(망·권한) -- 모르는 것은 초록이 아니다"}
    if r["결론"] == "success":
        return {"상태": "초록", "sha": r["sha"], "url": r["url"], "번호": r["번호"], "실패": [],
                "말": f"main CI 초록 (#{r['번호']} {r['sha']})"}
    실패 = 실패검사들(r["id"], repo) if 검사이름도 else []
    말 = (f"**main CI 빨강** (#{r['번호']} {r['sha']} {r['결론']}) {r['url']}"
         + (f"\n  실패 검사: {', '.join(실패)}" if 실패 else "\n  실패 검사 이름은 로그를 못 받아 모른다(GITHUB_TOKEN 필요)"))
    return {"상태": "빨강", "sha": r["sha"], "url": r["url"], "번호": r["번호"], "실패": 실패, "말": 말}


def 바뀌었나(보기결과: dict, repo=None) -> bool:
    """지난번 알린 것과 (상태, sha, 실패 목록) 이 다르면 True 로 하고 새 상태를 적는다 -- 같은 빨강을 2h 마다 되풀이해 알리지 않는다."""
    p = Path(repo or REPO) / 상태상대
    지난 = None
    if p.is_file():
        try:
            지난 = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            지난 = None
    지금 = {"상태": 보기결과["상태"], "sha": 보기결과["sha"], "실패": 보기결과["실패"]}
    if 지난 and all(지난.get(k) == v for k, v in 지금.items()):
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({**지금, "때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                            ensure_ascii=False), encoding="utf-8")
    return True


def 캐시보기(repo=None, 최대나이초: float = 4 * 3600) -> dict:
    """**망을 안 타고** 지난번 감시가 적어 둔 결론을 읽는다 -- 봇의 답변 경로(git_sync)에서 쓴다.
    파일이 없거나 오래됐으면 못잼: 모르는 것으로 막지 않는다(감시가 곧 채운다)."""
    p = Path(repo or REPO) / 상태상대
    if not p.is_file():
        return {"상태": "못잼", "sha": "", "url": "", "번호": 0, "실패": [],
                "말": "main CI 결론이 아직 없다(감시가 곧 채운다)"}
    try:
        j = json.loads(p.read_text(encoding="utf-8"))
        나이 = time.time() - p.stat().st_mtime
    except (ValueError, OSError):
        return {"상태": "못잼", "sha": "", "url": "", "번호": 0, "실패": [], "말": "CI 상태 파일을 못 읽었다"}
    if 나이 > 최대나이초:
        return {"상태": "못잼", "sha": j.get("sha", ""), "url": "", "번호": 0, "실패": j.get("실패", []),
                "말": f"main CI 결론이 낡았다({int(나이/60)}분 전) -- 막지 않는다"}
    상태 = j.get("상태", "못잼")
    실패 = j.get("실패", [])
    return {"상태": 상태, "sha": j.get("sha", ""), "url": "", "번호": 0, "실패": 실패,
            "말": (f"main CI {상태} ({j.get('sha', '')})" + (f" 실패 검사: {', '.join(실패)}" if 실패 else ""))}


def main() -> int:
    r = 보기()
    print(r["말"])
    return {"초록": 0, "빨강": 1}.get(r["상태"], 3)


if __name__ == "__main__":
    raise SystemExit(main())
