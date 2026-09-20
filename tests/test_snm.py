# -*- coding: utf-8 -*-
"""교재 T4 에 실린 SNM 수가 **정말 그 측정에서 나온 것인지** 붙든다.

붙드는 것 셋:

1. **추출기가 옳다** -- 두 극한(이득이 아주 큰 인버터 → V_DD/2, 이득 1 → 0)으로
   확인한다.  ngspice 없이 돈다.  이 검사가 없을 때 추출기가 두 번 틀렸고, 두 번 다
   **수는 그럴듯했다**.
2. **교재의 수 = 측정의 수** -- ngspice 가 있는 자리에서는 다시 재서 T4 에 박힌
   표와 대조한다.  붙여 넣은 수가 조용히 낡는 것을 막는다.
3. **경향이 옳다** -- read SNM 은 셀비 β 가 커지면 커지고, hold 보다 작다.
   실측으로 이 경향이 뒤집혀서 배선 버그(접근 트랜지스터 게이트가 워드라인이
   아니라 비트라인)를 잡았다.  값이 아니라 경향이 잡았다.
"""
import os
import shutil
import sys

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(뿌리, "edu"))
sys.path.insert(0, os.path.join(뿌리, "edu", "측정"))

import snm as 측정                                    # noqa: E402
import T4_noise                                       # noqa: E402

있나 = shutil.which("ngspice") is not None


def test_추출기가_두_극한을_맞춘다():
    큰, 평 = 측정.자해()
    assert 0.45 < 큰 < 0.52, f"이득이 큰 인버터는 V_DD/2 이어야 한다: {큰}"
    assert 평 < 0.02, f"이득 1 이면 눈이 없다 -- 0 이어야 한다: {평}"


def test_이득이_커질수록_여유가_커진다():
    """자해검사 -- 이득을 깎으면 SNM 이 줄어야 한다.

    (납작한 곡선으로 0 을 요구하지 않는다: 이득 0 인 VTC 는 애초에 쌍안정이
    아니라 '눈' 이라는 말이 뜻을 잃는다.  기하는 0.5 를 주고 그것은 추출기의
    잘못이 아니다.  **쌍안정을 잃는 경계는 이득 1 이고**, 거기서 0 이 나오는 것은
    위 검사가 이미 본다.)
    """
    V = 1.0
    xs = [i / 1000 * V for i in range(1001)]

    def 곧은VTC(A):
        # 기울기 -A 의 직선 VTC, 0 과 V 에서 잘린다
        return [max(0.0, min(V, V / 2 - A * (x - V / 2))) for x in xs]

    난것 = [측정.snm(xs, 곧은VTC(A), V) for A in (1.0, 2.0, 4.0, 8.0, 32.0)]
    assert 난것 == sorted(난것), f"이득이 커지는데 여유가 안 커진다: {난것}"
    assert 난것[0] < 0.02, f"이득 1 에서 {난것[0]} -- 쌍안정이 아닌데 여유가 있다"
    assert 난것[-1] > 0.4, f"이득 32 에서 {난것[-1]} -- V_DD/2 에 가까워야 한다"


def test_경향_read_는_hold_보다_작고_베타가_커지면_커진다():
    표 = T4_noise.잰SNM
    for b in 표["read"]:
        assert 표["read"][b] < 표["hold"][b], (b, 표["read"][b], 표["hold"][b])
    읽 = [표["read"][b] for b in sorted(표["read"])]
    assert 읽 == sorted(읽), f"read SNM 이 β 에 대해 단조증가가 아니다: {읽}"
    홀 = [표["hold"][b] for b in sorted(표["hold"])]
    assert 홀 == sorted(홀, reverse=True), f"hold SNM 은 β 에 대해 조금 줄어든다: {홀}"


def test_전압을_내리면_무너진다():
    v = T4_noise.잰Vmin
    assert v[1.0] > v[0.5] * 2, f"V_min 무너짐이 안 보인다: {v}"
    assert v[0.5] < 0.12, f"0.5 V 에서 여유가 {v[0.5]} 나 남았다 -- 셀이 안 무너졌다"


def test_교재의_수가_측정과_같다():
    """ngspice 가 있으면 **다시 재서** 대조한다 -- 박힌 수가 낡는 것을 막는다."""
    if not 있나:
        print("    (ngspice 가 없다 -- 재현 대조는 개발 자리에서만 돈다. "
              "추출기 검사는 위에서 이미 돌았다)")
        return
    for 이름, 읽기 in (("hold", False), ("read", True)):
        for b in (1.0, 2.0, 3.0):
            xs, ys = 측정.곡선(beta=b, 읽기=읽기)
            assert xs, "ngspice 가 있는데 곡선이 비었다"
            난것 = round(측정.snm(xs, ys), 4)
            박힌것 = T4_noise.잰SNM[이름][b]
            assert abs(난것 - 박힌것) < 0.002, (
                f"{이름} β={b}: 교재 {박힌것} vs 지금 잰 것 {난것} -- "
                "T4_noise.잰SNM 을 고치거나 덱이 바뀐 까닭을 적어라")


if __name__ == "__main__":
    import _run
    _run.돌리기(globals())
