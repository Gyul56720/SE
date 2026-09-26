"""**VM 봇 git push 토큰 인증을 붙든다.** 실측 2026-09-26 (재발방지).

## 왜

VM 봇의 `git push` 가 `fatal: could not read Username for 'https://github.com'` 로
계속 실패했다. origin 이 자격증명 없는 https 라 git 이 대화형으로 username 을 물었고
TTY 가 없어 죽었다. gitsync.인증푸시 가 `.env` 의 GITHUB_TOKEN 을 push URL 에 심어
그 구멍을 메운다(설정엔 안 남기고, 실패 메시지에서 토큰을 적출).

## 무엇을 붙드나

  1. 인증 URL 구성: https + 토큰 -> x-access-token URL, 기존 자격증명 제거,
     https 아니거나 토큰 없으면 None(설정 안 바꿈).
  2. **토큰 적출**: git 이 실패 시 URL(토큰 포함)을 뱉어도 반환 메시지엔 안 남는다.
  3. 토큰 있으면 인증 URL 로 민다(가짜 git 으로 인자 확인).
  4. 토큰 없으면 평범한 push -- 진짜 로컬 bare 원격에 커밋이 실제로 도착한다.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

루트 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(루트))

import gitsync


def CP(out="", err="", rc=0):
    return subprocess.CompletedProcess(args=[], returncode=rc, stdout=out, stderr=err)


def test_인증url_구성():
    assert gitsync._인증url("https://github.com/O/R.git", "TOK") == \
        "https://x-access-token:TOK@github.com/O/R.git"
    # 기존 자격증명은 지우고 새로 심는다
    assert gitsync._인증url("https://old:cred@github.com/O/R", "TOK") == \
        "https://x-access-token:TOK@github.com/O/R"
    # https 아니거나 토큰 없으면 손대지 않는다(None)
    assert gitsync._인증url("git@github.com:O/R.git", "TOK") is None
    assert gitsync._인증url("https://github.com/O/R", "") is None


def test_토큰_적출():
    글 = "fatal: unable to access https://x-access-token:SEKRET@github.com/O/R"
    assert "SEKRET" not in gitsync._적출(글, "SEKRET")
    assert "***" in gitsync._적출(글, "SEKRET")
    assert gitsync._적출("깨끗", "") == "깨끗"


def test_인증푸시_토큰있으면_인증url_실패시_토큰적출():
    def fake(a):
        if a[0] == "rev-parse":
            return CP("mybr")
        if a[0] == "remote":
            return CP("https://github.com/O/R.git")
        if a[0] == "push":
            assert any("x-access-token:TOK@github.com" in x for x in a), a  # 인증 URL 로 민다
            assert "--force" not in " ".join(a)                            # --force 없음
            return CP("", "fatal: unable to access https://x-access-token:TOK@github.com/O/R: 404", 1)
        return CP("")
    rc, msg = gitsync.인증푸시(fake, repo=None, 토큰="TOK")
    assert rc == 1
    assert "TOK" not in msg and "***" in msg          # 토큰이 메시지에 안 남는다


def test_인증푸시_토큰없으면_평범한_푸시가_실제로_민다():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="인증푸시-"))
    try:
        bare = tmp / "remote.git"
        work = tmp / "work"
        subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
        subprocess.run(["git", "init", str(work)], check=True, capture_output=True)

        def git(a):
            return subprocess.run(["git", "-C", str(work), *a], capture_output=True, text=True)

        for kv in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
            git(["config", *kv])
        git(["remote", "add", "origin", str(bare)])   # 파일 경로 origin -> https 아님
        (work / "a.txt").write_text("hi", encoding="utf-8")
        git(["add", "-A"]); git(["commit", "-m", "first"])
        br = git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()

        rc, msg = gitsync.인증푸시(git, br, 토큰="")   # 토큰 없음 -> 평범한 push
        assert rc == 0, msg
        # bare 원격에 커밋이 실제로 도착했나
        got = subprocess.run(["git", "-C", str(bare), "rev-parse", br],
                             capture_output=True, text=True)
        want = git(["rev-parse", "HEAD"]).stdout.strip()
        assert got.returncode == 0 and got.stdout.strip() == want
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _run
    _run.돌리기(globals())
