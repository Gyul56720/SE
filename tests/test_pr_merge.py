"""github_write 의 열린pr · pr상태 · pr머지하기 와 investigate.머지확정 을 가짜 HTTP 로 붙든다.

사용자(2026-09-12): "최대한 스스로 하고 문제가 있을 경우에만 의견 물어봐." 머지는 코드가 문제를 잰 뒤
정한다(investigate.머지위험 -- tests/test_investigate.py). 여기는 그 아래 GitHub 층: 무엇을 묻고
무엇을 누르는지. 망 없이 돈다.

실행: python3 tests/test_pr_merge.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import github_write as GW  # noqa: E402
from investigate import run as I  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


호출 = []
머지응답 = {"status": 200, "body": {"merged": True, "sha": "abcdef1234567890"}}


def 가짜요청(method, url, headers, data):
    호출.append((method, url))
    if method == "GET" and url.endswith("/pulls?state=open&per_page=50"):
        return 200, json.dumps([{"number": 3, "title": "다른 것", "html_url": "https://x/pull/3", "head": {"ref": "other"}},
                                {"number": 7, "title": "[조사 ab12] pdf", "html_url": "https://x/pull/7", "head": {"ref": "fix/ab12"}}])
    if method == "GET" and url.endswith("/pulls/7"):
        return 200, json.dumps({"merged": False, "mergeable": True, "mergeable_state": "clean", "additions": 40, "deletions": 3,
                                "html_url": "https://x/pull/7", "head": {"ref": "fix/ab12", "sha": "deadbeef"}})
    if method == "GET" and url.endswith("/pulls/7/files?per_page=100"):
        return 200, json.dumps([{"filename": "a.py", "status": "modified", "additions": 40, "deletions": 3}])
    if method == "GET" and url.endswith("/commits/deadbeef/check-runs"):
        return 200, json.dumps({"check_runs": [{"name": "gates", "status": "completed", "conclusion": "success"}]})
    if method == "PUT" and url.endswith("/pulls/7/merge"):
        return 머지응답["status"], json.dumps(머지응답["body"])
    return 404, '{"message":"Not Found"}'


os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})
root = Path(tempfile.mkdtemp(prefix="test-prmerge-"))
try:
    GW.요청 = 가짜요청
    GW.토큰 = lambda repo=None: "tok"

    print("== 열린 PR 을 갈래로도 제목으로도 찾는다 ==")
    r = GW.열린pr(갈래="fix/ab12")
    ok(r["됐나"] and r["번호"] == 7, f"갈래로 ({r})")
    r = GW.열린pr(제목에="[조사 ab12]")
    ok(r["됐나"] and r["번호"] == 7 and r["갈래"] == "fix/ab12", "제목으로")
    r = GW.열린pr(갈래="없는갈래", 제목에="[조사 zz]")
    ok(not r["됐나"] and "열린 PR 이 없다" in r["왜"], "없으면 없다고 한다")

    print("\n== pr상태: 머지 판단에 필요한 사실만 ==")
    s = GW.pr상태(7)
    ok(s["됐나"] and s["겹침"] is False and s["더함"] == 40 and s["파일들"][0]["경로"] == "a.py"
       and s["검사"][0]["결론"] == "success", f"겹침 · 줄 수 · 파일 · CI ({s['검사']})")
    ok(I.머지위험(s) == ([], []), "이 상태는 문제도 알림도 없다 -> 코드가 붙인다")

    print("\n== pr머지하기: PUT /merge, 판단은 안 한다 ==")
    호출.clear()
    m = GW.pr머지하기(7)
    ok(m["됐나"] and m["sha"] == "abcdef123456" and 호출 == [("PUT", f"{GW.API}/repos/{GW.저장소이름()}/pulls/7/merge")], f"머지됨 ({m})")
    머지응답.update(status=405, body={"message": "Pull Request is not mergeable"})
    m = GW.pr머지하기(7)
    ok(not m["됐나"] and "405" in m["왜"] and "not mergeable" in m["왜"], f"거절은 그대로 말한다 ({m['왜']})")
    머지응답.update(status=200, body={"merged": True, "sha": "abcdef1234567890"})
    GW.토큰 = lambda repo=None: ""
    ok(not GW.pr머지하기(7)["됐나"] and "GITHUB_TOKEN" in GW.pr머지하기(7)["왜"], "토큰이 없으면 그것만이 사람 몫이다")
    GW.토큰 = lambda repo=None: "tok"

    print("\n== 머지확정: 사람이 문제를 보고도 붙이기로 한 것 -- 누르고 main 으로 돌아온다 ==")
    bare = root / "remote.git"
    subprocess.run(["git", "-C", str(root), "init", "-q", "--bare", "remote.git"], check=True)
    subprocess.run(["git", "-C", str(root), "clone", "-q", str(bare), "work"], check=True, capture_output=True)
    work = root / "work"
    g = lambda *a: subprocess.run(["git", "-C", str(work), *a], capture_output=True, text=True)  # noqa: E731
    g("checkout", "-qb", "main"); (work / "a.txt").write_text("a\n"); g("add", "-A"); g("commit", "-qm", "init"); g("push", "-q", "-u", "origin", "main")
    g("checkout", "-qb", "fix/ab12"); (work / "b.txt").write_text("b\n"); g("add", "-A"); g("commit", "-qm", "fix")
    말 = I.머지확정(7, repo=work)
    ok("머지됨" in 말 and "main 으로 돌아왔다" in 말 and g("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "main",
       f"**누르고 main 으로 돌아온다** ({말[:80]})")
    머지응답.update(status=405, body={"message": "not mergeable"})
    ok("못 함" in I.머지확정(7, repo=work), "거절이면 그렇다고 말한다")

    print("\n== _머지기본: 문제가 없으면 붙이고, 있으면 안 붙이고 문제를 적는다 ==")
    머지응답.update(status=200, body={"merged": True, "sha": "abcdef1234567890"})
    g("checkout", "-q", "fix/ab12")
    r = I._머지기본(work, "ab12")
    ok(r["됐나"] and r["번호"] == 7 and r["문제"] == [] and r.get("갈래정리") == "main 으로 돌아왔다", f"문제 없음 -> 붙였다 ({r['왜']})")
    I.줄수상한, _원상한 = 10, I.줄수상한
    호출.clear()
    r = I._머지기본(work, "ab12")
    I.줄수상한 = _원상한
    ok(not r["됐나"] and r["문제"] and "상한" in r["문제"][0] and "!조사 머지 7" in r["왜"] and ("PUT", f"{GW.API}/repos/{GW.저장소이름()}/pulls/7/merge") not in 호출,
       f"문제 있음 -> **안 누르고** 무엇이 문제인지 적는다 ({r['왜']})")
finally:
    GW.요청 = None
    shutil.rmtree(root, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("pr_merge: 열린 PR · 상태 · 머지 · 확정 · 문제면 안 누름 -- 통과")
