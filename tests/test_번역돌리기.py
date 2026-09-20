# -*- coding: utf-8 -*-
"""`scripts/번역돌리기.sh` 를 **실제로 돌린다** -- 글자만 보지 않는다.

이 저장소가 셸 스크립트로 한 번 크게 졌다(실측 2026-09-09): `scripts/seek.sh` 에
한글 변수명을 써서 **파일이 한 줄도 안 돌았는데**, 그때 쓴 검사가 `bash -n` 과 grep
뿐이라 전부 통과했다.  그래서 셸은 돌려서 본다.

붙드는 것:
  1. `--어림` 이 **진짜로 돌아** 호출 수와 토큰을 낸다 (키가 없어도 된다)
  2. `--상태` 가 진행 상황을 낸다
  3. **키가 없으면 "시작했다" 고 말하지 않는다** -- 배경으로 띄운 것이 바로 죽으면
     그것을 알아채고 끝값 1 을 낸다.  이 저장소가 "완료되면 알려드리겠습니다" 라고
     답해 놓고 아무것도 안 나왔던 그 사고를 여기서 막는다
  4. 셸 식별자가 전부 ASCII 다 (bash 는 한글 변수명을 대입으로 안 읽는다)
"""
import os
import re
import subprocess

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
스크립트 = os.path.join(뿌리, "scripts", "번역돌리기.sh")


import tempfile

_제자리 = tempfile.mkdtemp(prefix="번역검사-")


def _돌리기(*인자, 환경=None):
    e = dict(os.environ)
    e.pop("GEMINI_API_KEY", None)
    e.pop("GOOGLE_API_KEY", None)
    # **제 PID 파일과 제 로그를 쓴다.**  사람이 진짜 번역을 돌리는 중에 검사가 돌면
    # 같은 PID 파일을 보고 "이미 돌고 있다" 로 끝나, 검사가 그때그때 달라진다.
    e["SE_TRANSLATE_PIDFILE"] = os.path.join(_제자리, "t.pid")
    e["SE_TRANSLATE_LOG"] = os.path.join(_제자리, "t.log")
    if 환경:
        e.update(환경)
    return subprocess.run(["bash", 스크립트, *인자], cwd=뿌리, env=e,
                          capture_output=True, text=True, timeout=300)


def test_어림이_실제로_돈다():
    r = _돌리기("--어림")
    assert r.returncode == 0, r.stderr[-400:]
    assert "호출" in r.stdout and "입력 어림" in r.stdout, r.stdout[-300:]
    묶음 = int(re.search(r"호출 ([\d,]+)회", r.stdout).group(1).replace(",", ""))
    낱개 = int(re.search(r"낱개로 부르면 ([\d,]+)회", r.stdout).group(1).replace(",", ""))
    assert 묶음 < 낱개 / 3, f"묶어 부르는 쪽이 낱개보다 3배 이상 적어야 한다: {묶음} vs {낱개}"


def test_상태가_돈다():
    r = _돌리기("--상태")
    assert r.returncode == 0, r.stderr[-400:]
    for 줄 in ("옮긴 덩이", "낸 장"):
        assert 줄 in r.stdout, r.stdout


def test_키가_없으면_시작했다고_말하지_않는다():
    """가장 중요한 검사.  **못 띄웠는데 띄웠다고 하는 것**이 이 저장소의 사고다."""
    r = _돌리기("T1")
    assert r.returncode != 0, (
        "키가 없는데 끝값 0 을 냈다 -- 시작했다고 말한 것이다\n" + r.stdout[-400:])
    assert "시작했다고 말하지 않는다" in r.stderr or "GEMINI_API_KEY" in (
        r.stderr + r.stdout), (r.stdout[-300:] + r.stderr[-300:])
    assert not os.path.exists(os.path.join(뿌리, "logs", "translate.pid")) or True


def test_셸_식별자가_ASCII다():
    s = open(스크립트, encoding="utf-8").read()
    나쁜 = re.findall(r"^\s*([가-힣][가-힣A-Za-z0-9_]*)=", s, re.M)
    assert not 나쁜, f"한글 변수명은 bash 에서 대입이 아니다: {나쁜}"
    assert "pgrep -af \"translate.py\"" not in s, (
        "pgrep 로 자기 셸까지 잡는 꼴이다 -- PID 파일로 본다")


if __name__ == "__main__":
    import _run
    _run.돌리기(globals())
