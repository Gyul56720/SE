"""github_write(create_pr: 밀고 PR 열기, **머지는 사람**)를 임시 bare 원격 + 가짜 HTTP 로 붙든다.

격차표 'GitHub 쓰기': 조회만 -> 토큰 + 좁은 도구(create_pr, 머지는 사람). 권한 넓히기라 폭을 딱 이만큼만.

붙드는 것: (1) main 에서는 거절하고 밀지도 않는다, (2) 토큰 없으면 딱 그 값만 청한다(밀기 전에),
(3) 갈래에서는 실제로 원격에 밀리고 PR POST 가 head/base 를 맞게 보낸다, (4) 원격이 앞서 있으면
**merge 로 따라잡고** 다시 민다(--force 없음), (5) 이미 열린 PR 은 그렇다고 말한다,
(6) 이 모듈엔 merge 가 없다, (7) 배선(도구·ADMIN_TOOLS·프롬프트·배포 경로).

망 없이 돈다. 실행: python3 tests/test_create_pr.py
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

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=False)


os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})
root = Path(tempfile.mkdtemp(prefix="test-createpr-"))
bare = root / "remote.git"
git(root, "init", "-q", "--bare", "remote.git")
git(root, "clone", "-q", str(bare), "work")
work = root / "work"
git(work, "checkout", "-qb", "main")
(work / "a.txt").write_text("a\n", encoding="utf-8")
git(work, "add", "-A"); git(work, "commit", "-qm", "init"); git(work, "push", "-q", "-u", "origin", "main")

호출 = []


def 가짜요청(method, url, headers, data):
    호출.append({"method": method, "url": url, "auth": headers.get("Authorization", ""), "body": json.loads(data or b"{}")})
    if 호출[-1]["body"].get("title") == "again":
        return 422, '{"message":"Validation Failed","errors":[{"message":"A pull request already exists for x:feat."}]}'
    return 201, json.dumps({"html_url": "https://github.com/x/y/pull/7", "number": 7})


try:
    GW.요청 = 가짜요청
    GW.토큰 = lambda repo=None: "tok-xyz"

    print("== main 에서는 거절 ==")
    r = GW.pr만들기("t", "b", repo=work)
    ok(not r["됐나"] and "main" in r["왜"] and not 호출, "main 에서는 PR 을 안 열고 HTTP 도 안 부른다")

    print("\n== 토큰 없으면 딱 그 값만 청한다 (밀기 전에) ==")
    git(work, "checkout", "-qb", "feat")
    (work / "b.txt").write_text("b\n", encoding="utf-8"); git(work, "add", "-A"); git(work, "commit", "-qm", "feat1")
    GW.토큰 = lambda repo=None: ""
    r = GW.pr만들기("t", "b", repo=work)
    ok(not r["됐나"] and "GITHUB_TOKEN" in r["왜"] and "!열쇠" in r["왜"], "토큰 없음 -> !열쇠 GITHUB_TOKEN 청함")
    ok(git(bare, "rev-parse", "--verify", "refs/heads/feat").returncode != 0, "토큰 없으면 밀지도 않는다")
    GW.토큰 = lambda repo=None: "tok-xyz"

    print("\n== 갈래: 밀고 PR POST ==")
    r = GW.pr만들기("첫 PR", "본문", repo=work)
    ok(r["됐나"] and r["번호"] == 7 and r["url"].endswith("/pull/7"), f"PR 열림 ({r['왜'][:40]})")
    ok(git(bare, "rev-parse", "--verify", "refs/heads/feat").returncode == 0, "**원격에 실제로 밀렸다**")
    c = 호출[-1]
    ok(c["method"] == "POST" and c["url"].endswith("/pulls") and c["body"]["head"] == "feat" and c["body"]["base"] == "main"
       and c["auth"] == "Bearer tok-xyz", f"POST /pulls head=feat base=main + Bearer ({c['url'][-30:]})")
    ok("머지는 사람" in r["왜"], "보고가 '머지는 사람' 을 말한다")

    print("\n== 원격이 앞서면 merge 로 따라잡고 다시 민다 (--force 없음) ==")
    git(root, "clone", "-q", str(bare), "other")
    other = root / "other"
    git(other, "checkout", "-q", "feat")
    (other / "c.txt").write_text("c\n", encoding="utf-8"); git(other, "add", "-A"); git(other, "commit", "-qm", "other"); git(other, "push", "-q")
    (work / "d.txt").write_text("d\n", encoding="utf-8"); git(work, "add", "-A"); git(work, "commit", "-qm", "mine")
    r = GW.pr만들기("둘째", "", repo=work)
    ok(r["됐나"] and "merge 했다" in r["왜"], f"non-fast-forward -> merge 로 따라잡고 밀었다 ({r['왜'][:50]})")
    원격로그 = git(bare, "log", "--oneline", "feat").stdout
    ok("other" in 원격로그 and "mine" in 원격로그, "**남의 커밋이 안 사라졌다**(force 없음)")

    print("\n== 이미 열린 PR ==")
    r = GW.pr만들기("again", "", repo=work)
    ok(not r["됐나"] and "이미 열려" in r["왜"], "422 already exists -> 그렇다고 말한다")
finally:
    GW.요청 = None
    shutil.rmtree(root, ignore_errors=True)

print("\n== 폭: merge 없음 · 배선 ==")
_src = (뿌리 / "github_write.py").read_text(encoding="utf-8")
ok("def merge" not in _src and "/merge" not in _src, "**이 모듈엔 merge 가 없다 -- 머지는 사람**")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("def create_pr" in _도구 and _서버.count(" create_pr,") >= 2, "create_pr 도구·ADMIN_TOOLS·임포트")
ok("create_pr 도구" in _서버 and "머지는" in _서버, "프롬프트가 create_pr 를 이름을 대고 '머지는 사람' 을 적는다")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"github_write.py"' in _wf, "github_write 가 배포 경로에")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("create_pr: main 거절 · 토큰 청함 · 밀고 POST · merge 따라잡기 · 이미 열림 · merge 없음 · 배선 -- 통과")
