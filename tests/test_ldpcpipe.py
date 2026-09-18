"""층 파이프라인 -- **세 길로 구한 같은 수가 맞는지**.

    1. 조합 공식     시뮬 없이 기저행렬에서 센다   -> 상한
    2. 사이클 모형   발행 시각을 굴린다
    3. RTL 시뮬      스톨 제어기를 iverilog 로

1 >= 2 여야 하고 2 == 3 이어야 한다. 하나라도 어긋나면 어느 하나가 틀린 것이다.
"""
import ldpcpipe as P
import rtl

열수 = {"BG1": 68, "BG2": 52}


def _도구():
    없 = rtl.없는도구("iverilog", "vvp", "yosys")
    assert not 없, f"도구가 없다: {없} -- '통과' 가 아니라 '못 잼' 이다"


def test_비트맵이_기저행렬과_맞다():
    import nrldpc as F
    for bg, 원소 in (("BG1", 316), ("BG2", 197)):
        맵 = P.층비트맵(bg)
        assert sum(bin(m).count("1") for m in 맵) == 원소
        assert len(맵) == (46 if bg == "BG1" else 42)


def test_공식은_상한이다():
    """앞선 멈춤이 벌려 놓은 간격을 공식은 안 본다 -> 항상 크거나 같다."""
    for bg in ("BG1", "BG2"):
        맵 = P.층비트맵(bg)
        for D in (2, 3, 4, 6, 8):
            assert P.공식멈춤(맵, D) >= P.사이클모형(맵, D)["멈춤"], (bg, D)


def test_깊이2에서는_공식과_모형이_같다():
    """날아다니는 층이 하나뿐이면 누적될 여지가 없다 -- 공식이 정확해진다."""
    for bg in ("BG1", "BG2"):
        맵 = P.층비트맵(bg)
        assert P.공식멈춤(맵, 2) == P.사이클모형(맵, 2)["멈춤"]


def test_깊이가_깊어지면_공식이_더_많이_틀린다():
    """이것이 안 성립하면 '공식은 상한' 이라는 설명이 틀린 것이다."""
    맵 = P.층비트맵("BG1")
    차 = [P.공식멈춤(맵, D) - P.사이클모형(맵, D)["멈춤"] for D in (2, 3, 4, 6, 8)]
    assert 차 == sorted(차) and 차[0] == 0 and 차[-1] > 50, 차


def test_깊이1이면_멈춤이_없다():
    for bg in ("BG1", "BG2"):
        맵 = P.층비트맵(bg)
        c = P.사이클모형(맵, 1)
        assert c["멈춤"] == 0 and c["총사이클"] == len(맵)


def test_뒤집은_순서는_같은_값을_낸다():
    """**대칭이다.** 해저드는 (i,j) 쌍과 그 거리에만 달렸는데 뒤집기가 둘 다 보존한다.

    첫 판은 이걸 "순서를 바꾸면 달라진다" 의 본보기로 썼다가 실패했다(80 대 80).
    검사가 틀렸던 것이지 코드가 틀린 게 아니었다. 그래서 대칭으로 적어 둔다 --
    층 스케줄을 탐색할 때 뒤집기를 이웃수로 쓰면 **아무것도 안 움직인다.**
    """
    맵 = P.층비트맵("BG1")
    assert P.사이클모형(맵, 4)["멈춤"] == \
           P.사이클모형(맵, 4, 순서=list(reversed(range(len(맵)))))["멈춤"]


def test_순서를_섞으면_멈춤이_바뀐다():
    """안 바뀌면 층 스케줄이라는 손잡이가 아예 없는 것이다."""
    import random
    맵 = P.층비트맵("BG1")
    자연 = P.사이클모형(맵, 4)["멈춤"]
    rng = random.Random(0)
    값 = set()
    for _ in range(20):
        순 = list(range(len(맵)))
        rng.shuffle(순)
        값.add(P.사이클모형(맵, 4, 순서=순)["멈춤"])
    assert len(값) > 1, 값
    assert any(v != 자연 for v in 값), (자연, 값)


def test_RTL이_사이클모형과_같다():
    _도구()
    for bg in ("BG1", "BG2"):
        맵 = P.층비트맵(bg)
        for D in (2, 3, 4):
            c = P.사이클모형(맵, D)
            s = rtl.시뮬(P.스톨제어기(열수[bg], D, len(맵), 맵),
                       P.벤치(c["멈춤"]), top="tb")
            assert s.get("판정") == "PASS", f"{bg} D={D}: {(s.get('로그') or '')[-200:]}"


def test_벤치가_틀린_기대값을_잡는다():
    """안 잡으면 위 검사는 아무 뜻이 없다."""
    _도구()
    맵 = P.층비트맵("BG2")
    c = P.사이클모형(맵, 4)
    s = rtl.시뮬(P.스톨제어기(52, 4, len(맵), 맵), P.벤치(c["멈춤"] + 1), top="tb")
    assert s.get("판정") != "PASS" or "FAIL" in (s.get("로그") or "")


def test_제어기가_합성된다():
    _도구()
    맵 = P.층비트맵("BG2")
    작 = rtl.합성(P.스톨제어기(52, 2, len(맵), 맵), top="stallctl")
    큰 = rtl.합성(P.스톨제어기(52, 6, len(맵), 맵), top="stallctl")
    assert 작.get("판정") == "PASS" and 큰.get("판정") == "PASS"
    assert 큰["셀수"] > 작["셀수"], (작["셀수"], 큰["셀수"])
