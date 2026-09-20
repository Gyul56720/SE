"""CNU Verilog 가 `nrldpcfix` 와 **비트까지 같은지** 실제로 돌려서 본다.

## 도구가 없으면 '못 잼' 이지 '통과' 가 아니다

`tests/test_nnfix.py` 는 iverilog 가 없으면 `ok(True, "건너뜀")` 으로 **통과**시킨다.
그러면 검사가 아무것도 안 무는 환경에서도 초록이 뜬다 -- 과제 #9(G012 사고증명이
discord/langchain 없으면 안 문다)와 **같은 병**이다. 이 파일은 도구가 없으면
실패한다. 이 컨테이너와 CI 에 iverilog·verilator·yosys 가 다 있으므로, 없어졌다면
그것이야말로 알아야 할 일이다.

## 이 판의 거짓 초록

**합성해서 셀 수를 보고하고는 그 회로가 맞는 답을 내는지 안 보는 것.**
틀린 회로가 제일 작다. 그래서 면적을 보기 전에 한 값씩 맞춘다.
"""
import numpy as np

import ldpcrtl as R
import rtl


def _도구():
    없 = rtl.없는도구("iverilog", "vvp", "yosys", "verilator")
    assert not 없, f"도구가 없다: {없} -- 이건 '통과' 가 아니라 '못 잼' 이다"


# ---------------------------------------------------------------- 골든 쪽
def test_골든CNU가_복호기_안의_식과_같다():
    """떼어 낸 검사노드가 `nrldpcfix.복호` 의 그것과 같은 답을 내야 한다."""
    import nrldpcfix as X
    rng = np.random.default_rng(0)
    for _ in range(200):
        d = int(rng.integers(3, 8))
        q = rng.integers(-31, 32, size=d)
        # 복호기 안의 식을 그대로 다시 쓴다 (벡터 한 줄짜리로)
        a = np.abs(q)
        순 = np.argsort(a)
        m1, m2 = a[순[0]], a[순[1]]
        부호 = np.where(q >= 0, 1, -1)
        기대 = X.정규화(int(np.prod(부호)) * 부호 *
                     np.where(np.arange(d) == 순[0], m2, m1), 3, 2)
        assert list(R.골든CNU(q)) == list(기대)


def test_동점은_답을_안_바꾼다():
    """동점이면 min2 == min1 이라 어느 쪽을 최소로 골라도 같다.

    이것이 성립해야 RTL 이 `a_i <= min1` 이라는 헐거운 규칙을 써도 된다.
    """
    for q in ([5, 5, 9, -2], [-7, 7, 7, 7], [3, -3, 3, -3]):
        v = np.array(q)
        a = np.abs(v)
        동점 = len(a) - len(set(a.tolist()))
        assert 동점 > 0
        기대 = R.골든CNU(v)
        # 최소가 여럿이면 그 자리들의 크기가 전부 같아야 한다
        최소자리 = np.nonzero(a == a.min())[0]
        if len(최소자리) > 1:
            assert len(set(np.abs(기대[최소자리]).tolist())) == 1


# ---------------------------------------------------------------- RTL 쪽
def test_RTL이_골든과_한_값씩_같다():
    _도구()
    for D, W in ((4, 6), (6, 5), (3, 8)):
        d = R.cnu(D, W)
        tb, n = R.테스트벤치(D, W, 벡터수=80, 씨=D * 10 + W)
        s = rtl.시뮬(d, tb, top="tb")
        로그 = (s.get("로그") or "")
        assert s.get("판정") == "PASS", f"D={D} W={W}: {로그[-300:]}"
        assert "PASS" in 로그 and "FAIL" not in 로그, 로그[-300:]


def test_틀린_RTL은_잡힌다():
    """벤치가 **무는지** 본다. 안 물면 위 검사는 아무 뜻이 없다."""
    _도구()
    d = R.cnu(4, 6).replace("? min2 : min1", "? min1 : min2")   # 최소 두 개를 뒤바꾼다
    tb, _ = R.테스트벤치(4, 6, 벡터수=80, 씨=7)
    s = rtl.시뮬(d, tb, top="tb")
    assert s.get("판정") != "PASS" or "FAIL" in (s.get("로그") or ""), \
        "일부러 틀린 회로가 통과했다 -- 벤치가 아무것도 안 문다"


def test_합성이_되고_셀수가_D와_W를_따라_는다():
    _도구()
    작 = rtl.합성(R.cnu(3, 4), top="cnu")
    큰D = rtl.합성(R.cnu(10, 4), top="cnu")
    큰W = rtl.합성(R.cnu(3, 8), top="cnu")
    for r in (작, 큰D, 큰W):
        assert r.get("판정") == "PASS"
    assert 큰D["셀수"] > 작["셀수"] and 큰W["셀수"] > 작["셀수"]


def test_린트가_남긴_경고를_숨기지_않는다():
    """지금 하나 남아 있다: 시프트로 버리는 하위 2비트가 '안 쓰인다' 는 경고.

    **숨기지 않는다.** 없어지면 이 검사가 실패해서 알려 준다.
    """
    _도구()
    l = rtl.린트(R.cnu(4, 6))
    로그 = l.get("로그") or ""
    assert "UNUSEDSIGNAL" in 로그 and "pr0" in 로그, \
        f"경고가 바뀌었다 -- 문서를 고쳐라: {로그[:200]}"


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _run
    _run.돌리기(globals())
