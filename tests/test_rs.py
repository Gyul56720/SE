# -*- coding: utf-8 -*-
"""RS 부호기/복호기 검사.

**이 파일이 막으려는 거짓초록 다섯:**

  1. 오류를 0개 넣고 '복호기가 동작한다' 고 말하는 것
  2. 오정정(성공이라 했는데 원본이 아님)을 성공으로 세는 것
  3. 부호화 결과가 진짜 코드워드인지 안 보는 것
  4. t+1 개에서 '전부 검출된다' 고 단정하는 것 -- **RS 는 그렇지 않다**
  5. 망가진 복호기가 통과하는 것
"""
import pytest
import gf
import rs

작은 = rs.RS(gf.필드(4, 0b10011), 15, 9)        # t=3
중간 = rs.RS(gf.필드(8, 0x11d), 255, 239)       # t=8, 흔한 부호


def test_부호화_결과는_진짜_코드워드다():
    """신드롬이 전부 0 이어야 한다. 이게 아니면 부호기가 틀렸다."""
    for c in (작은, 중간, rs.KP4()):
        메시지 = [(i * 7 + 3) % (c.f.n + 1) for i in range(c.k)]
        말 = c.부호화(메시지)
        assert len(말) == c.n
        assert 말[: c.k] == 메시지, "조직적 부호인데 앞부분이 메시지가 아니다"
        assert not any(c.신드롬(말)), f"{c.n},{c.k}: 부호화 결과의 신드롬이 0 이 아니다"


def test_생성다항식_차수():
    for c in (작은, 중간, rs.KP4()):
        assert len(c.g) - 1 == 2 * c.t, (c.n, c.k, len(c.g))


def test_t개까지는_반드시_고쳐진다():
    """**오류 개수를 명시적으로 넣는다.** 0개만 돌리는 것은 검사가 아니다."""
    for c, 시행 in ((작은, 40), (중간, 12), (rs.KP4(), 6)):
        for e in range(1, c.t + 1):
            r = rs.측정(c, e, 시행=시행, 씨앗=100 + e)
            assert r["고침"] == 시행, (c.n, e, r)
            assert r["**오정정**"] == 0, (c.n, e, r)
            assert r["검출된실패"] == 0, (c.n, e, r)
            assert r["무의미"] is False


def test_0개시험은_무의미로_표시된다():
    """오류 0개 시험은 통과해도 아무 뜻이 없다. 그 사실이 반환에 남아야 한다."""
    r = rs.측정(작은, 0, 시행=10)
    assert r["고침"] == 10
    assert r["무의미"] is True, "0개 시험인데 무의미 표시가 없다"


def test_t초과에서는_원본복원이_보장되지_않는다():
    """**RS 는 t+1 개를 전부 검출하지 못한다.** 일부는 다른 코드워드로 간다.

    '전부 검출된다' 고 쓰면 그것이 과장이다. 여기서는 **고치지는 못한다**만
    주장한다 -- 그것은 참이다.
    """
    r = rs.측정(작은, 작은.t + 1, 시행=120, 씨앗=3)
    assert r["고침"] == 0, "t+1 개인데 원본으로 복원됐다 -- 불가능하다"
    assert r["검출된실패"] + r["**오정정**"] == 120
    assert r["**오정정**"] > 0, (
        "작은 부호(15,9)에서 t+1 개 오정정이 한 번도 없다 -- 표본이 너무 작거나 "
        "복호기가 과하게 보수적이다. 이 수는 0 이 아니어야 정상이다")


def test_신드롬0이면_손대지_않는다():
    c = 작은
    말 = c.부호화([1] * c.k)
    r = c.복호(말)
    assert r["성공"] and r["고친수"] == 0 and r["신드롬0"] is True
    assert r["말"] == 말


def test_복호결과에_성공과_고친수가_반드시_있다():
    """호출자가 실패를 못 보고 지나가지 않게 하는 계약."""
    c = 작은
    말 = c.부호화(list(range(c.k)))
    for 넣을오류 in (0, 1, c.t, c.t + 1):
        받음 = list(말)
        for i in range(넣을오류):
            받음[i * 2] ^= 5
        r = c.복호(받음)
        assert "성공" in r and "고친수" in r, r
        assert isinstance(r["성공"], bool)


def test_자리와_크기가_실제_오류와_맞는다():
    c = 중간
    메시지 = [(i * 13) % 256 for i in range(c.k)]
    말 = c.부호화(메시지)
    자리 = [0, 5, 100, 254, 17, 200, 33, 91]      # t=8 개
    받음 = list(말)
    for p in 자리:
        받음[p] ^= 0xA5
    r = c.복호(받음)
    assert r["성공"], r
    assert r["고친수"] == len(자리)
    assert r["자리"] == sorted(자리), (r["자리"], sorted(자리))
    assert r["말"] == 말
    assert r["메시지"] == 메시지


def test_망가진_복호기는_잡힌다():
    """**검사가 무는지 재는 검사.** 신드롬을 조용히 0 으로 만들면
    복호기는 '오류 없음' 이라고 답하게 된다. 그게 통과하면 안 된다."""
    c = rs.RS(gf.필드(4, 0b10011), 15, 9)
    원래 = c.신드롬
    c.신드롬 = lambda r: [0] * (2 * c.t)
    res = rs.측정(c, 2, 시행=20, 씨앗=1)
    assert res["고침"] < 20, "신드롬을 0 으로 박았는데 전부 고쳐졌다 -- 검사가 안 문다"
    c.신드롬 = 원래


def test_망가진_부호기는_잡힌다():
    c = rs.RS(gf.필드(4, 0b10011), 15, 9)
    원래 = c.부호화
    c.부호화 = lambda m: list(m) + [0] * (c.n - c.k)   # 패리티를 0 으로
    말 = c.부호화([1, 2, 3, 4, 5, 6, 7, 8, 9])
    assert any(c.신드롬(말)), "패리티를 0 으로 박았는데 신드롬이 0 이다"
    c.부호화 = 원래


def test_잘못된_인자는_거부된다():
    f = gf.필드(4, 0b10011)
    with pytest.raises(ValueError):
        rs.RS(f, 15, 15)                 # k == n
    with pytest.raises(ValueError):
        rs.RS(f, 15, 10)                 # n-k 가 홀수
    with pytest.raises(ValueError):
        rs.RS(f, 16, 9)                  # n > 2^m-1
    with pytest.raises(ValueError):
        작은.부호화([1, 2, 3])            # 길이 틀림
    with pytest.raises(ValueError):
        작은.복호([1, 2, 3])


def test_KP4_제원():
    c = rs.KP4()
    assert (c.n, c.k, c.t, c.f.m) == (544, 514, 15, 10)
    assert c.f.확인됨 is False, "규격으로 확인하지도 않고 확인됨 을 세웠다"


def test_fcr이_달라도_성질은_산다():
    """첫 근 지수를 규격에서 못 봤다. 어떤 값이든 t 개 정정은 서야 한다."""
    for fcr in (0, 1, 2, 7):
        c = rs.RS(gf.필드(4, 0b10011), 15, 9, fcr=fcr)
        r = rs.측정(c, c.t, 시행=30, 씨앗=fcr)
        assert r["고침"] == 30, (fcr, r)
        assert r["**오정정**"] == 0, (fcr, r)


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _run
    _run.돌리기(globals())
