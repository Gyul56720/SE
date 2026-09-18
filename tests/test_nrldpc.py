"""5G NR LDPC 부동소수 골든 검사. **거짓 초록 다섯 자리를 하나씩 문다.**

빠른 검사(25초) 안에 들도록 작은 Z 와 적은 블록으로 돈다. 큰 Z 쓸기는
`sweep_ldpc.py` 가 백그라운드에서 한다.
"""
import numpy as np

import nrldpc as L


# ---------------------------------------------------------------- 표 자체
def test_기저행렬_원소수가_표준값과_맞는다():
    assert len(L.기저행렬("BG1")) == 316
    assert len(L.기저행렬("BG2")) == 197


def test_두_독립출처가_값까지_같다():
    """py3gpp 와 sionna. 둘이 어긋나면 어느 쪽도 못 믿는다."""
    for bg in ("BG1", "BG2"):
        a = L.기저행렬(bg)
        b = L.기저행렬(bg, 파일=L.표자리 / f"nr_{bg.lower()}_sionna.csv")
        assert a == b, f"{bg}: 두 출처가 어긋난다"


def test_리프팅집합이_51개이고_겹치지_않는다():
    전부 = [z for s in L.리프팅집합 for z in s]
    assert len(전부) == 51
    assert len(set(전부)) == 51
    assert max(전부) == 384 and min(전부) == 2


def test_부호_구조가_표준과_맞는다():
    c1, c2 = L.부호("BG1", 32), L.부호("BG2", 32)
    assert (c1.행수, c1.열수, c1.Kb) == (46, 68, 22)
    assert (c2.행수, c2.열수, c2.Kb) == (42, 52, 10)
    assert abs(c1.부호율 - 1 / 3) < 1e-9
    assert abs(c2.부호율 - 1 / 5) < 1e-9
    assert c1.K == 22 * 32 and c2.K == 10 * 32


# ---------------------------------------------------------------- 부호화
def test_부호화한_것이_신드롬0이다():
    for bg in ("BG1", "BG2"):
        c = L.부호(bg, 8)
        rng = np.random.default_rng(0)
        for _ in range(8):
            assert c.신드롬0(L.부호화(c, rng.integers(0, 2, size=(c.Kb, c.Z))))


def test_영부호어도_신드롬0이다():
    c = L.부호("BG1", 16)
    assert c.신드롬0(np.zeros((c.열수, c.Z), dtype=np.int8))


def test_거짓초록2_영부호어와_무작위부호어가_같은_BLER을_낸다():
    """대칭성이 깨지는 버그를 영부호어는 통째로 숨긴다.

    표본이 적으므로 **같음을 증명하지 않는다** -- 크게 어긋나면 잡는다.
    """
    c = L.부호("BG2", 8)
    영 = L.측정(c, -2.0, 블록수=80, 씨=5)
    무 = L.측정(c, -2.0, 블록수=80, 씨=5, 부호어=L.무작위부호어(c))
    assert abs(영["BLER"] - 무["BLER"]) < 0.15, (영["BLER"], 무["BLER"])


# ---------------------------------------------------------------- 복호기
def test_거짓초록1_수렴여부를_반드시_같이_낸다():
    c = L.부호("BG2", 8)
    r = L.복호(c, L.채널llr(np.zeros((c.열수, c.Z), np.int8), -6.0,
                        np.random.default_rng(0), c), 최대반복=5)
    assert "수렴" in r and "쓴반복" in r
    assert isinstance(r["수렴"], bool)


def test_거짓초록3_조기종료가_실제로_문다():
    """높은 SNR 에서 반복을 다 쓰면 조기종료가 안 도는 것이다."""
    c = L.부호("BG2", 8)
    r = L.측정(c, 0.0, 블록수=30, 씨=2, 최대반복=20)
    assert r["평균반복"] < 20.0, "조기종료가 안 문다"
    끔 = L.측정(c, 0.0, 블록수=10, 씨=2, 최대반복=20)
    # 조기종료를 끄면 반드시 다 쓴다
    직접 = L.복호(c, L.채널llr(np.zeros((c.열수, c.Z), np.int8), 0.0,
                          np.random.default_rng(2), c), 최대반복=20, 조기종료=False)
    assert 직접["쓴반복"] == 20
    assert 끔["평균반복"] <= 20.0


def test_거짓초록4_오류0을_BLER0이라_부르지_않는다():
    c = L.부호("BG2", 8)
    r = L.측정(c, 3.0, 블록수=20, 씨=7)
    assert r["블록오류"] == 0
    assert r["상한만"] is True
    assert "상한" in r["말"]


def test_거짓초록5_미수렴을_센다():
    c = L.부호("BG2", 8)
    r = L.측정(c, -8.0, 블록수=12, 씨=11, 최대반복=6)
    assert r["미수렴"] > 0, "이 SNR 에서 다 수렴했다면 수렴판정이 헐겁다"


def test_SNR을_올리면_BLER이_내려간다():
    c = L.부호("BG2", 8)
    앞 = L.측정(c, -3.0, 블록수=60, 씨=13)["BLER"]
    뒤 = L.측정(c, -1.0, 블록수=60, 씨=13)["BLER"]
    assert 앞 > 뒤, (앞, 뒤)


def test_펑처된_자리의_LLR은_0이다():
    c = L.부호("BG1", 8)
    llr = L.채널llr(np.zeros((c.열수, c.Z), np.int8), 0.0,
                  np.random.default_rng(0), c)
    assert np.all(llr[:L.펑처기저열] == 0.0)
    assert np.any(llr[L.펑처기저열:] != 0.0)


def test_신드롬이_틀린_부호어를_거른다():
    """신드롬 검사가 **아무것이나 통과시키면** 조기종료가 거짓이 된다."""
    c = L.부호("BG2", 8)
    rng = np.random.default_rng(1)
    cw = L.부호화(c, rng.integers(0, 2, size=(c.Kb, c.Z)))
    assert c.신드롬0(cw)
    cw[3, 0] ^= 1
    assert not c.신드롬0(cw), "한 비트를 뒤집었는데 신드롬이 0 이다"
