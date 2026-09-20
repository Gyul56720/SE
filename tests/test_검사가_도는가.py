# -*- coding: utf-8 -*-
"""관문이 검사를 **정말 돌리는지** 본다 -- 임포트만 하고 초록을 내지 않는지.

## 실측 2026-09-19 -- 이 저장소의 관문이 여든 개 남짓을 안 돌리고 있었다

`scripts/tests.sh` 와 `scripts/precheck.sh` 는 둘 다 검사 파일을
**`python3 tests/test_*.py`** 로 돌린다.  이 저장소의 검사 대부분은 모듈 수준에서
재고 `sys.exit(1)` 로 끝나므로 그렇게 해도 돈다.

그런데 `def test_...()` 만 쓰고 `__main__` 이 없는 파일은 **임포트만 되고 끝난다**.
종료 코드 0, 0.14 초.  관문은 `OK` 를 찍는다.  실측으로 그런 파일이 열 개였고
검사 함수 91 개가 관문에서 한 번도 돈 적이 없었다:

    test_agent_context test_dpi_ref test_gf test_ldpcpipe test_ldpcrtl
    test_nrldpc test_nrldpcfix test_rs test_spec_dfe test_verif_agent

`tests/_run.py` 가 그 파일들을 스크립트로도 돌게 한다.  이 검사는 **구멍이 다시
열리지 않게** 붙든다.

## 이 검사가 보는 것 두 가지

1. `def test_` 가 있는 모든 파일에 `__main__` 블록이 있나 (구조)
2. runner 가 **실패를 정말 실패로 내나** (동작) -- 일부러 깨뜨려 확인한다

2번이 없으면 이 검사 자체가 거짓초록을 낼 수 있다: 구조만 보는 검사는
runner 가 모든 것을 삼켜도 통과한다.
"""
import os
import re
import subprocess
import sys
import tempfile

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
검사자리 = os.path.join(뿌리, "tests")


def _pytest꼴(경로):
    t = open(경로, encoding="utf-8").read()
    return re.search(r"^def test_", t, re.M) is not None, ("__main__" in t)


def test_pytest꼴_파일은_전부_스크립트로도_돈다():
    나쁜 = []
    for f in sorted(os.listdir(검사자리)):
        if not (f.startswith("test_") and f.endswith(".py")):
            continue
        있다, 메인 = _pytest꼴(os.path.join(검사자리, f))
        if 있다 and not 메인:
            나쁜.append(f)
    assert not 나쁜, (
        "def test_ 를 쓰면서 __main__ 이 없는 파일이 있다. 관문은 이것을 "
        "임포트만 하고 OK 를 찍는다 -- 끝에 이 두 줄을 붙여라:\n"
        "    if __name__ == \"__main__\":\n"
        "        import _run; _run.돌리기(globals())\n"
        f"해당 파일: {나쁜}")


def test_runner_는_실패를_실패로_낸다():
    """일부러 깨뜨린 검사 파일을 runner 로 돌려 **1 이 나오는지** 본다."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "test_망친것.py")
        open(p, "w", encoding="utf-8").write(
            "def test_통과한다():\n    assert True\n\n"
            "def test_망했다():\n    assert 1 == 2, '일부러 깨뜨린 것'\n\n"
            'if __name__ == "__main__":\n'
            "    import sys\n"
            f"    sys.path.insert(0, {검사자리!r})\n"
            "    import _run\n"
            "    _run.돌리기(globals())\n")
        r = subprocess.run([sys.executable, p], capture_output=True, text=True,
                           timeout=120)
        assert r.returncode != 0, (
            "일부러 깨뜨린 검사를 runner 가 초록으로 냈다 -- runner 가 안 문다\n"
            + r.stdout + r.stderr)
        assert "망했다" in (r.stdout + r.stderr), (
            "실패했다고는 했는데 어느 것이 실패했는지 안 적었다")


def test_runner_는_통과를_통과로_낸다():
    """거짓 빨강도 안 된다 -- 성한 파일은 0 이라야 한다."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "test_성한것.py")
        open(p, "w", encoding="utf-8").write(
            "def test_하나():\n    assert True\n\n"
            "def test_둘():\n    assert 2 + 2 == 4\n\n"
            'if __name__ == "__main__":\n'
            "    import sys\n"
            f"    sys.path.insert(0, {검사자리!r})\n"
            "    import _run\n"
            "    _run.돌리기(globals())\n")
        r = subprocess.run([sys.executable, p], capture_output=True, text=True,
                           timeout=120)
        assert r.returncode == 0, (r.stdout + r.stderr)
        assert "2 통과" in r.stdout, r.stdout


def test_runner_는_parametrize_를_펼친다():
    """곱집합이 실제로 도는지 -- 세 경우 중 하나만 깨뜨려 본다."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "test_펼침.py")
        open(p, "w", encoding="utf-8").write(
            "import pytest\n\n"
            "@pytest.mark.parametrize('n', [1, 2, 3])\n"
            "def test_n(n):\n    assert n != 2, f'{n} 에서 깨진다'\n\n"
            'if __name__ == "__main__":\n'
            "    import sys\n"
            f"    sys.path.insert(0, {검사자리!r})\n"
            "    import _run\n"
            "    _run.돌리기(globals())\n")
        r = subprocess.run([sys.executable, p], capture_output=True, text=True,
                           timeout=120)
        out = r.stdout + r.stderr
        assert r.returncode != 0, "parametrize 를 안 펼쳐서 깨진 경우를 못 봤다\n" + out
        assert "2 통과" in out and "1 실패" in out, (
            "세 경우 중 둘 통과 하나 실패라야 한다 -- 펼치기가 이상하다\n" + out)


def test_runner_는_fixture_를_조용히_건너뛰지_않는다():
    """못 돌리는 것은 **못 돌린다고 말하고 실패**해야 한다. 조용한 통과가 제일 나쁘다."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "test_픽스처.py")
        open(p, "w", encoding="utf-8").write(
            "def test_뭔가(tmp_path):\n    assert tmp_path\n\n"
            'if __name__ == "__main__":\n'
            "    import sys\n"
            f"    sys.path.insert(0, {검사자리!r})\n"
            "    import _run\n"
            "    _run.돌리기(globals())\n")
        r = subprocess.run([sys.executable, p], capture_output=True, text=True,
                           timeout=120)
        assert r.returncode != 0, "fixture 를 못 채우는데 초록을 냈다"
        assert "fixture" in (r.stdout + r.stderr)


if __name__ == "__main__":
    import sys as _s, os as _o
    _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
    import _run
    _run.돌리기(globals())
