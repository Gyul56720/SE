# -*- coding: utf-8 -*-
"""판매 가능 관문(`edu/house/release.sh`)을 **실제로 돌려** 본다.

## 왜 관문도 검사해야 하나

관문은 "팔 수 있다/없다" 를 말하는 장치다.  그런 장치의 고전적 실패는
**아무것도 안 하고 통과를 내는 것**이다.  그래서 두 가지를 본다.

    1. 성한 판에서 통과가 나오나
    2. **블록을 일부러 망치면 반드시 실패가 나오나**

2번이 핵심이다.  1번만 보는 검사는 관문이 전부 통과를 찍게 만들어도 초록이다.

관문은 HEAD 의 임시 워크트리에서 돈다.  `SE_RELEASE_DIR` 로 자리를 줄 수 있어
여기서는 **작업 디렉터리를 복사해** 쓴다 -- 커밋 안 된 변경도 검사하기 위해서다
(관문 자체의 동작을 보는 검사이지, 커밋 위생을 보는 검사가 아니다).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import pytest

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
관문 = os.path.join(뿌리, "edu", "house", "release.sh")

있나 = all(shutil.which(x) for x in ("iverilog", "vvp", "verilator", "yosys"))
pytestmark = pytest.mark.skipif(
    not (있나 and os.path.exists(관문)),
    reason="iverilog/verilator/yosys 또는 release.sh 가 없다")


def _판만들기():
    d = tempfile.mkdtemp(prefix="relgate_")
    for sub in ("edu", "gf.py", "rs.py"):
        s = os.path.join(뿌리, sub)
        t = os.path.join(d, sub)
        if os.path.isdir(s):
            shutil.copytree(s, t,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pdf"))
        elif os.path.exists(s):
            shutil.copy2(s, t)
    return d


def _돌리기(판, 블록, 제한=1200):
    env = dict(os.environ, SE_RELEASE_DIR=판)
    return subprocess.run(["bash", os.path.join(판, "edu", "house", "release.sh"),
                           블록],
                          capture_output=True, text=True, timeout=제한,
                          cwd=뿌리, env=env)


def test_성한_블록은_관문을_통과한다():
    판 = _판만들기()
    try:
        r = _돌리기(판, "gf_mul")
        assert "실패" not in r.stdout.split("== 집 전체 ==")[0], r.stdout
        assert r.returncode in (0, 2), r.stdout + r.stderr
        assert "자해검사" in r.stdout and "변이점수" in r.stdout
        assert "합성" in r.stdout
    finally:
        shutil.rmtree(판, ignore_errors=True)


@pytest.mark.parametrize("전,후,무엇", [
    ("if (p[M-1]) p", "if (p[M-2]) p", "회귀"),
    ("acc = acc ^ p;", "acc = acc | p;", "회귀"),
])
def test_망친_블록은_관문이_반드시_막는다(전, 후, 무엇):
    """RTL 을 망쳐 놓고 관문이 **통과를 내지 않는지** 본다."""
    판 = _판만들기()
    try:
        p = os.path.join(판, "edu", "agent", "blocks", "gf_mul", "gf_mul.v")
        t = open(p, encoding="utf-8").read()
        assert 전 in t, f"심을 자리를 못 찾았다: {전!r}"
        open(p, "w", encoding="utf-8").write(t.replace(전, 후))
        r = _돌리기(판, "gf_mul")
        assert r.returncode != 0, (
            "블록을 망쳤는데 관문이 통과를 냈다 -- 관문이 안 문다\n" + r.stdout)
        assert "실패" in r.stdout, r.stdout
    finally:
        shutil.rmtree(판, ignore_errors=True)


def test_문서가_없으면_관문이_막는다():
    """산출물 문서 하나를 지우면 관문이 실패로 내는지."""
    판 = _판만들기()
    try:
        os.remove(os.path.join(판, "edu", "house", "KNOWN_ISSUES.md"))
        r = _돌리기(판, "gf_mul")
        assert r.returncode != 0, (
            "알려진문제 문서를 지웠는데 관문이 통과를 냈다\n" + r.stdout)
        assert "KNOWN_ISSUES" in r.stdout
    finally:
        shutil.rmtree(판, ignore_errors=True)


def test_관문이_못잰_것을_초록이라고_안_한다():
    """성능한계도 성능해당없음도 없는 블록은 '못 쟀다' 로 나오고 종료코드가 2 다."""
    판 = _판만들기()
    try:
        bp = os.path.join(판, "edu", "agent", "blocks", "gf_mul", "block.py")
        t = open(bp, encoding="utf-8").read()
        t = re.sub(r"\n성능해당없음 = .*?\n\s*\)\n", "\n", t, flags=re.S)
        assert "성능해당없음" not in t, "선언을 못 지웠다"
        open(bp, "w", encoding="utf-8").write(t)
        r = _돌리기(판, "gf_mul")
        assert "못쟀다" in r.stdout, r.stdout
        assert r.returncode == 2, (
            f"못 잰 것이 있는데 종료코드가 {r.returncode} 다 -- "
            "모르는 것은 안 된 것으로 다뤄야 한다\n" + r.stdout)
    finally:
        shutil.rmtree(판, ignore_errors=True)


if __name__ == "__main__":
    import sys as _s, os as _o
    _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
    import _run
    _run.돌리기(globals())
