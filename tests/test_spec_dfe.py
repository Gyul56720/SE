"""투기적 언롤 DFE 골든 검사. **검사가 실제로 무는지까지 본다.**

이 저장소의 규율: 안 무는 검사는 없느니만 못하다 -- 통과했다는 이유로 더 마음 놓게
만든다. 그래서 S1·S2 는 "맞추면 0" 만 보지 않고 **"어기면 갈린다"** 도 같이 본다.
"""
import random

import specdfe as S

탭수, G, 표본수 = 6, 64, 400


def _짐(seed, 변조, 탭=탭수, 진폭=400, 길이=표본수):
    r = random.Random(seed)
    c = [r.randint(-40, 40) for _ in range(탭)]
    x = [r.randint(-진폭, 진폭) for _ in range(길이)]
    초기 = [r.choice(S.레벨들(변조)) for _ in range(탭)]
    return c, x, 초기


def _포화(v, 폭):
    if 폭 is None:
        return int(v)
    lo, hi = -(1 << (폭 - 1)), (1 << (폭 - 1)) - 1
    return lo if v < lo else hi if v > hi else int(v)


def _다르게(감싸기):
    """`specdfe._감싸기` 를 잠시 바꾼다."""
    원래 = S._감싸기
    S._감싸기 = 감싸기
    return 원래


def test_투기형은_직접형과_같다():
    """**핵심 계약.** 언롤은 수학적 항등이다 -- 다르면 그것은 버그다."""
    for 변조 in (S.NRZ, S.PAM4):
        for N in (1, 2, 3):
            for seed in range(30):
                c, x, 초기 = _짐(seed, 변조)
                W = S.누산최소폭(400, c, 변조)
                a = S.직접형(x, c, G, 변조, 초기, W)
                b = S.투기형(x, c, G, 변조, N, 초기, W)
                assert a == b, f"{변조} N={N} seed={seed} 에서 갈렸다"


def test_S1_초기레지스터를_안_맞추면_갈린다():
    """검사가 **무는지**. 안 물면 S1 은 스펙에 있을 이유가 없다."""
    for 변조 in (S.NRZ, S.PAM4):
        갈림 = 0
        for seed in range(40):
            c, x, _ = _짐(seed, 변조)
            W = S.누산최소폭(400, c, 변조)
            a = S.직접형(x, c, G, 변조, [0] * 탭수, W)
            b = S.투기형(x, c, G, 변조, 1, [S.레벨들(변조)[0]] * 탭수, W)
            갈림 += int(a != b)
        assert 갈림 > 0, f"{변조}: 초기값을 어겼는데 안 갈렸다 -- 검사가 아무것도 안 문다"


def test_S2_감싸기는_순서에_무관하다():
    """2의 보수 감싸기는 mod 2^W 환이다 -> **폭이 모자라도** 두 구조가 같다."""
    for 변조 in (S.NRZ, S.PAM4):
        for seed in range(20):
            c, x, 초기 = _짐(seed, 변조)
            W = S.누산최소폭(400, c, 변조) - 3        # 일부러 모자라게
            a = S.직접형(x, c, G, 변조, 초기, W)
            b = S.투기형(x, c, G, 변조, 3, 초기, W)
            assert a == b, f"{변조} seed={seed}: 감싸기인데 갈렸다"


def test_S2_포화는_두_구조를_가른다():
    """포화는 결합법칙을 안 지킨다 -> 합산 순서가 다른 두 구조가 **다르게 포화한다.**

    이것이 S2 가 스펙에 있는 이유다. 안 갈리면 S2 는 빈 규칙이다.
    """
    원래 = _다르게(lambda v, w: _포화(v, w))
    try:
        갈림 = 0
        for 변조 in (S.NRZ, S.PAM4):
            for seed in range(20):
                c, x, 초기 = _짐(seed, 변조)
                W = S.누산최소폭(400, c, 변조) - 3
                a = S.직접형(x, c, G, 변조, 초기, W)
                b = S.투기형(x, c, G, 변조, 3, 초기, W)
                갈림 += int(a != b)
        assert 갈림 > 0, "포화인데 안 갈렸다 -- S2 를 스펙에서 빼야 한다"
    finally:
        S._감싸기 = 원래


def test_포화라도_폭이_충분하면_안_갈린다():
    """넘치지 않으면 포화가 일어나지 않는다 -- 그러면 순서가 다시 공짜다."""
    원래 = _다르게(lambda v, w: _포화(v, w))
    try:
        for 변조 in (S.NRZ, S.PAM4):
            for seed in range(20):
                c, x, 초기 = _짐(seed, 변조)
                W = S.누산최소폭(400, c, 변조) + 1
                assert S.직접형(x, c, G, 변조, 초기, W) == \
                       S.투기형(x, c, G, 변조, 3, 초기, W)
    finally:
        S._감싸기 = 원래


def test_누산최소폭이_정말로_안_넘친다():
    """닫힌 꼴이 낸 폭에서 **감싸기가 한 번도 일어나지 않아야** 한다."""
    for 변조 in (S.NRZ, S.PAM4):
        for seed in range(20):
            c, x, 초기 = _짐(seed, 변조)
            W = S.누산최소폭(400, c, 변조)
            무한 = S.직접형(x, c, G, 변조, 초기, None)
            유한 = S.직접형(x, c, G, 변조, 초기, W)
            assert 무한 == 유한, f"{변조} seed={seed}: 최소폭인데 결과가 바뀌었다"


def test_비용_셈이_표와_맞는다():
    """`3*4^N` 이 스펙 문서의 표와 같은가."""
    assert [S.갈래수(S.NRZ, N) for N in (1, 2, 3)] == [2, 4, 8]
    assert [S.갈래수(S.PAM4, N) for N in (1, 2, 3)] == [4, 16, 64]
    assert [S.슬라이서수(S.NRZ, N) for N in (1, 2, 3)] == [2, 4, 8]
    assert [S.슬라이서수(S.PAM4, N) for N in (1, 2, 3)] == [12, 48, 192]


def test_슬라이서_문턱이_이상점에서_맞다():
    """이상적 입력 `m*g` 를 넣으면 그 `m` 이 나와야 한다."""
    for 변조 in (S.NRZ, S.PAM4):
        for m in S.레벨들(변조):
            assert S.슬라이서(m * G, G, 변조) == m


def test_N이_탭수를_넘으면_탭수로_잘린다():
    c, x, 초기 = _짐(0, S.NRZ, 탭=3)
    W = S.누산최소폭(400, c, S.NRZ)
    assert S.투기형(x, c, G, S.NRZ, 99, 초기, W) == \
           S.투기형(x, c, G, S.NRZ, 3, 초기, W)


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _run
    _run.돌리기(globals())
