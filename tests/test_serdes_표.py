# -*- coding: utf-8 -*-
"""T8 에 박힌 수가 **지금 다시 재도 같은지** 본다.

교재가 인용하는 링크 수는 `edu/측정/serdes_표.py` 에서 나왔다.  붙여 넣은 수는
모형이 바뀌면 조용히 낡는다 -- 그때 교재는 있지도 않은 실험을 인용하게 된다.

여기서 하는 것 넷:
  1. **커서는 다시 재서 맞춘다** (빠르다 -- 채널 한 번씩)
  2. BER 은 표본을 줄여 **자릿수만** 맞춘다 (전량은 몇 분이라 CI 에 안 맞는다)
  3. **경향** -- 손실이 커지면 메인 커서가 줄고 ISI 가 는다
  4. **판정 규율** -- 30 dB 행은 BER≈0.25 라 '망가진 동작점' 이고, 교재가 그렇게
     적고 있는지 글에서 확인한다(수만 옮기고 경고를 빠뜨리면 그 표는 거짓말이 된다)
"""
import os
import sys

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 뿌리)
sys.path.insert(0, os.path.join(뿌리, "edu"))
sys.path.insert(0, os.path.join(뿌리, "edu", "측정"))

import serdes_표 as 측정                                   # noqa: E402
import T8_serdes                                          # noqa: E402


def test_커서가_교재의_수와_같다():
    지금 = 측정.커서재기()
    for l, 박힌 in T8_serdes.잰커서.items():
        난것 = 지금[l]
        for i, (a, b) in enumerate(zip(박힌, 난것)):
            assert abs(a - b) < 1e-3, (
                f"{l}dB 커서 {i}: 교재 {a} vs 지금 {b} -- "
                "T8_serdes.잰커서 를 고치거나 모형이 바뀐 까닭을 적어라")


def test_손실이_커지면_메인이_줄고_ISI_가_는다():
    m = [T8_serdes.잰커서[l][0] for l in (10, 20, 30)]
    isi = [T8_serdes.잰커서[l][3] for l in (10, 20, 30)]
    assert m == sorted(m, reverse=True), f"메인 커서가 단조감소가 아니다: {m}"
    assert isi == sorted(isi), f"ISI 가 단조증가가 아니다: {isi}"


def test_최악왜곡은_10dB_에서도_닫혀_있다():
    """교재의 요점 -- 최악왜곡은 **예측이 아니라 한계**다."""
    for l in (10, 20, 30):
        assert T8_serdes.잰커서[l][4] < 0, l
    오류, 비트 = T8_serdes.잰BER[(10, "none")]
    assert 오류 / 비트 < 1e-4, (
        f"10 dB 에서 실제 BER 이 {오류/비트} -- 최악왜곡이 닫혔는데 링크도 닫혔다면 "
        "이 장의 논지가 성립하지 않는다")


def test_BER_이_자릿수로_재현된다():
    """표본을 줄여 빠르게 -- 자릿수(10배 안)만 본다."""
    지금 = 측정.재기(비트=20000)
    for 열쇠, (오류, 비트) in T8_serdes.잰BER.items():
        l, 이름 = 열쇠
        k = f"{l}|{이름}"
        if k not in 지금:
            continue
        박힌율 = 오류 / 비트
        난율 = 지금[k][0] / 지금[k][1]
        if 박힌율 < 1e-4:                       # 0 에 가까운 것끼리는 자릿수를 못 잰다
            assert 난율 < 1e-3, (k, 난율)
            continue
        assert 0.1 <= (난율 + 1e-9) / (박힌율 + 1e-9) <= 10, (
            f"{k}: 교재 {박힌율:.3e} vs 지금 {난율:.3e} -- 자릿수가 다르다")


def test_망가진_동작점이라고_적혀_있다():
    """수만 옮기고 경고를 빠뜨리면 그 표는 거짓말이 된다."""
    글 = T8_serdes.ch_serdes()
    assert "broken operating point" in 글, "30 dB 행을 '망가진 동작점' 이라고 안 적었다"
    assert "rule of three" in 글, "오류 0 을 BER 0 이라 하지 않는다고 안 적었다"


if __name__ == "__main__":
    import _run
    _run.돌리기(globals())
