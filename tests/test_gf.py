# -*- coding: utf-8 -*-
"""GF(2^m) 검사 -- **검사가 무는지부터 본다.**

이 저장소의 규율: 검사하지 않은 초록불이 검사한 빨간불보다 나쁘다.
그래서 검사마다 '일부러 망가뜨리면 빨개지는가' 를 같이 둔다.
"""
import pytest
import gf


def test_KP4필드가_진짜_필드다():
    f = gf.KP4필드()
    r = gf.검증(f, 표본=0)          # 1023개 전수
    assert r["필드인가"], r
    assert r["원소수"] == 1023
    assert r["본원소"] == 1023, "표본을 0 으로 줬는데 전수가 아니다"


def test_작은필드_전수():
    for m, poly in ((2, 0b111), (3, 0b1011), (4, 0b10011), (8, 0x11d)):
        f = gf.필드(m, poly)
        r = gf.검증(f, 표본=0)
        assert r["필드인가"], (m, hex(poly), r)


def test_원시가_아닌_다항식은_거부된다():
    """x^4+x^3+x^2+x+1 은 기약이지만 **원시가 아니다** (alpha 위수 5).
    이걸 조용히 받으면 곱셈표가 틀린 채로 돈다."""
    with pytest.raises(ValueError, match="원시다항식이 아니다"):
        gf.필드(4, 0b11111)


def test_최고차항_검사():
    with pytest.raises(ValueError, match="최고차항"):
        gf.필드(4, 0b1011)          # x^3+x+1 -- m=4 인데 3차다


def test_검증이_망가진_곱셈을_문다():
    """**검사가 무는지 재는 검사.** 곱셈을 조용히 틀리게 바꾸면 검증이 빨개져야 한다."""
    f = gf.필드(4, 0b10011)
    assert gf.검증(f, 표본=0)["필드인가"]

    원래 = f.곱하기
    f.곱하기 = lambda a, b: (원래(a, b) ^ 1) if (a and b) else 원래(a, b)
    r = gf.검증(f, 표본=0)
    assert not r["필드인가"], "곱셈을 망가뜨렸는데 검증이 통과했다 -- 검사가 안 문다"
    assert r["역원실패"] > 0
    f.곱하기 = 원래


def test_검증이_망가진_역원을_문다():
    f = gf.필드(4, 0b10011)
    원래 = f.역원
    f.역원 = lambda a: 원래(a) if a == 1 else 1     # 전부 1 을 돌려준다
    r = gf.검증(f, 표본=0)
    assert not r["필드인가"], "역원을 망가뜨렸는데 통과했다"
    f.역원 = 원래


def test_0의_역원은_예외():
    f = gf.KP4필드()
    with pytest.raises(ZeroDivisionError):
        f.역원(0)
    with pytest.raises(ZeroDivisionError):
        f.나누기(1, 0)


def test_알파_주기():
    f = gf.KP4필드()
    assert f.알파(0) == 1
    assert f.알파(f.n) == 1, "alpha^(2^m-1) != 1"
    assert f.알파(-1) == f.역원(f.알파(1))


def test_거듭제곱이_반복곱셈과_같다():
    """독립 대조 -- 표를 쓰는 거듭제곱을 **다른 길**로 한 번 더 구한다."""
    f = gf.필드(8, 0x11d)
    for a in (2, 3, 7, 255, 100):
        acc = 1
        for e in range(20):
            assert f.거듭(a, e) == acc, (a, e)
            acc = f.곱하기(acc, a)


def test_미확인_표시가_붙어_있다():
    """KP4 필드 다항식은 규격으로 확인 못 했다. 그 사실이 **코드에 남아** 있어야 한다."""
    f = gf.KP4필드()
    assert f.확인됨 is False, "확인하지도 않고 확인됨=True 로 바꿨다"
    assert "미확인" in repr(f)
