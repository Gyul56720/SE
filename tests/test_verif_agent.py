# -*- coding: utf-8 -*-
"""검증 에이전트를 **진짜로 돌려** 본다 -- 버그를 심고, 고치는지 본다.

## 왜 이 검사가 필요한가

`edu/agent/` 는 "빨간불을 찾아서 고친다" 고 주장하는 장치다.  그런 장치의 고전적
실패는 **아무것도 안 하고 초록을 내는 것**이다.  그래서 여기서는 세 가지를 본다.

    1. 성한 DUT 에서 회귀가 초록인가                     (거짓 빨강이 없나)
    2. 버그를 심으면 **반드시** 빨개지는가                (거짓 초록이 없나)
    3. 심은 버그를 수리가 찾아내고, 그 편집이 **안 쓴 씨앗**에서도 초록인가

3번이 핵심이다.  과적합한 편집(실패 사례만 특수처리)이 통과하면 안 된다.

원장은 `SE_LEDGER_ROOT` 로 임시 자리에 쓰게 한다 -- 검사는 재는 것이지
남기는 것이 아니다.
"""
import os, sys, json, shutil, subprocess, tempfile
import pytest

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
에이전트 = os.path.join(뿌리, "edu", "agent")
sys.path.insert(0, 에이전트)

iverilog = shutil.which("iverilog") and shutil.which("vvp")
pytestmark = pytest.mark.skipif(not iverilog, reason="iverilog/vvp 가 없다")


def _블록(이름):
    import importlib.util
    p = os.path.join(에이전트, "blocks", 이름, "block.py")
    spec = importlib.util.spec_from_file_location(f"t_{이름}", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_성한_블록은_초록이고_비교가_문다():
    import harness
    for 이름 in ("gf_mul", "crc32", "rs_syndrome"):
        b = _블록(이름)
        ok, 왜 = harness.자해검사(b)
        assert ok, f"{이름}: 자해검사 실패 -- {왜}"
        r = harness.잰다(b, 시행=300, 씨앗=11)
        assert r.오류 is None, f"{이름}: {r.오류}"
        assert r.틀림 == 0, f"{이름}: 성한 DUT 가 {r.틀림} 개 틀렸다"
        assert r.쓸모있나, f"{이름}: 출력이 {r.서로다른출력} 가지 -- 자극이 무의미하다"


@pytest.mark.parametrize("전,후", [
    ("if (p[M-1]) p", "if (p[M-2]) p"),
    ("acc = acc ^ p;", "acc = acc | p;"),
    ("else        p = (p << 1);", "else        p = (p >> 1);"),
])
def test_심은_버그는_반드시_걸린다(전, 후):
    import harness, vrepair
    b = _블록("gf_mul")
    원본 = open(b.소스들()[0], encoding="utf-8").read()
    망친 = 원본.replace(전, 후)
    assert 망친 != 원본, f"심을 자리를 못 찾았다: {전!r}"
    tb = vrepair.임시블록(b, b.소스들()[0], 망친)
    try:
        r = harness.잰다(tb, 시행=300, 씨앗=11)
        assert r.오류 is None, r.오류
        assert r.틀림 > 0, (
            f"{전!r} -> {후!r} 로 망쳤는데 회귀가 초록이다 -- 검사가 안 문다")
    finally:
        tb.닫기()


@pytest.mark.parametrize("전,후", [
    ("if (p[M-1]) p", "if (p[M-2]) p"),
    ("acc = acc ^ p;", "acc = acc | p;"),
])
def test_수리가_심은_버그를_되돌린다(전, 후):
    import harness, vrepair
    b = _블록("gf_mul")
    원본 = open(b.소스들()[0], encoding="utf-8").read()
    tb = vrepair.임시블록(b, b.소스들()[0], 원본.replace(전, 후))
    try:
        수리 = vrepair.고쳐보기(tb, harness, 씨앗=11, 검증씨앗=12345,
                              시행=300, 후보시간제한=10)
        assert not 수리.get("실패"), f"수리 실패: {수리}"
        # 편집이 실제로 성한 코드와 같은 동작을 내는지 **다시 잰다**
        tb2 = vrepair.임시블록(b, b.소스들()[0], 수리["원문"])
        try:
            for 씨 in (7, 99, 31337):
                r = harness.잰다(tb2, 시행=300, 씨앗=씨)
                assert r.오류 is None and r.틀림 == 0, (
                    f"수리했다는데 씨앗 {씨} 에서 {r.틀림} 개 틀렸다 -- 과적합이다")
        finally:
            tb2.닫기()
    finally:
        tb.닫기()


def test_과적합_편집은_거부된다():
    """실패 사례만 통과시키는 편집을 만들어 넣고, 수리가 그것을 안 고르는지 본다.

    DUT 에 '입력이 3ff 3ff 이면 정답을 그대로 낸다' 는 특수처리를 넣는다.
    이것은 씨앗 11 의 첫 실패를 통과시키지만 다른 입력은 여전히 틀린다.
    """
    import harness, vrepair
    b = _블록("gf_mul")
    원본 = open(b.소스들()[0], encoding="utf-8").read()
    망친 = 원본.replace("if (p[M-1]) p", "if (p[M-2]) p")
    특수 = 망친.replace("assign y = acc;",
                      "assign y = (a == 10'h3ff && b == 10'h3ff) ? 10'h2ba : acc;")
    assert 특수 != 망친
    tb = vrepair.임시블록(b, b.소스들()[0], 특수)
    try:
        r = harness.잰다(tb, 시행=300, 씨앗=11)
        assert r.틀림 > 0, "특수처리만으로 회귀가 초록이 됐다 -- 자극이 너무 약하다"
    finally:
        tb.닫기()


def test_에이전트가_원장을_SE_LEDGER_ROOT_에_쓴다():
    """기관을 진짜로 돌리되 **임시 자리**에 쓰게 한다 (CLAUDE.md 규칙 3)."""
    d = tempfile.mkdtemp(prefix="agled_")
    try:
        env = dict(os.environ, SE_LEDGER_ROOT=d)
        r = subprocess.run(
            [sys.executable, os.path.join(에이전트, "agent.py"),
             "--시간", "0.002", "--시행", "200", "--블록", "gf_mul"],
            capture_output=True, text=True, env=env, timeout=300)
        assert r.returncode == 0, r.stderr[-1500:]
        원장 = os.path.join(d, "verif", "regress.jsonl")
        assert os.path.exists(원장), "원장을 SE_LEDGER_ROOT 아래에 안 썼다"
        줄들 = [json.loads(l) for l in open(원장, encoding="utf-8") if l.strip()]
        assert 줄들, "원장이 비었다"
        assert all(x["자해검사"] for x in 줄들), "자해검사가 실패한 바퀴가 있다"
        assert all(x["판정"] == "초록" for x in 줄들), (
            "성한 블록인데 초록이 아닌 바퀴가 있다: "
            + str([x["판정"] for x in 줄들 if x["판정"] != "초록"][:3]))
        assert any(x["서로다른출력"] >= 2 for x in 줄들)
        # 저장소 안 원장은 안 건드렸어야 한다
        assert not os.path.exists(os.path.join(에이전트, "ledger", "regress.jsonl")), \
            "SE_LEDGER_ROOT 를 줬는데 저장소 원장에도 썼다"
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _run
    _run.돌리기(globals())
