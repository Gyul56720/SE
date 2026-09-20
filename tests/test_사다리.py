# -*- coding: utf-8 -*-
"""**논리 점프를 기계가 막는다** -- 대학원 이론서(T 계열)의 개념 사다리.

사용자 지시: *"한국어로. 고등학교 졸업생이 봐도 이해하기 쉽게. 즉, 논리적으로
계속 이어져야해. 논리 jump 없이."*

`edu/bookK.py` 가 장마다 두 가지를 선언하게 한다.

    쓰는것   : 이 장이 **이미 안다고 전제하는** 개념
    내놓는것 : 이 장이 **처음 정의하는** 개념

그 선언을 아무도 안 보면 선언은 장식이다.  bookK 의 독스트링은 처음부터
"`tests/test_사다리.py` 가 본다" 고 적고 있었는데 **그 파일이 없었다** --
검사가 있다고 적힌 자리에 검사가 없는 것이 이 저장소가 가장 경계하는 꼴이다
(검사하지 않은 초록불).  그래서 짓는다.

붙드는 것:
  1. 장을 순서대로 읽을 때 **아직 안 나온 개념을 쓰는 장**이 없다
  2. 같은 개념을 **두 장이 처음 정의**하지 않는다 (어느 쪽이 먼저인지 흐려진다)
  3. **자해검사** -- 일부러 어긴 장을 끼우면 이 검사가 빨개진다
"""
import os
import sys

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(뿌리, "edu"))

import bookK  # noqa: E402

# 읽는 순서대로.  장을 더하면 여기에 더한다.
차례 = [("T1_device", "ch_device"), ("T2_delay", "ch_delay"),
      ("T3_meta", "ch_meta"), ("T4_noise", "ch_noise"),
      ("T5_sample", "ch_sample"), ("T6_dataconv", "ch_dataconv"),
      ("T7_pll", "ch_pll"), ("T8_serdes", "ch_serdes"),
      ("T9_channel", "ch_channel"), ("T10_switchcap", "ch_switchcap"),
      ("T11_bias", "ch_bias"), ("T12_match", "ch_match"),
      ("T13_pi", "ch_pi"), ("T14_rel", "ch_rel"),
      ("T15_layout", "ch_layout"), ("T16_esd", "ch_esd"),
      ("T17_flow", "ch_flow"),
      ("T18_floorplan", "ch_floorplan"),
      ("T19_pnr", "ch_pnr"),
      ("T20_signoff", "ch_signoff"),
      ("T21_dv", "ch_dv"),
      ("T22_ate", "ch_ate"),
      ("T23_lab", "ch_lab")]


def _짓기():
    """장들을 순서대로 지어 bookK.장들 에 등록한다."""
    import importlib
    bookK.장들.clear()
    for m, fn in 차례:
        mod = importlib.import_module(m)
        importlib.reload(mod)
        getattr(mod, fn)()
    return list(bookK.장들)


def test_순서대로_읽을_때_점프가_없다():
    장들 = _짓기()
    assert len(장들) == len(차례), f"장이 {len(장들)}개 등록됐다 -- {차례}"
    어김, _ = bookK.사다리검사(장들)
    assert not 어김, "앞에서 안 나온 개념을 쓴다:\n" + "\n".join(
        f"  {번호}: {', '.join(것들)}" for 번호, 것들 in 어김)


def test_같은_개념을_두_장이_처음_정의하지_않는다():
    장들 = _짓기()
    _, 처음 = bookK.사다리검사(장들)
    낸것 = [c for ch in 장들 for c in ch.내놓는것]
    assert len(낸것) == len(set(낸것)), (
        "두 번 정의된 개념: "
        + ", ".join(sorted({c for c in 낸것 if 낸것.count(c) > 1})))
    # 정말로 쌓였나 -- 밑바닥(고교)만 있고 아무것도 안 는 것도 통과가 아니다
    새것 = {k for k, v in 처음.items() if v != "고교"}
    assert len(새것) >= 20, f"이 책이 새로 정의한 개념이 {len(새것)}개뿐이다"


def test_자해_어긴_장을_끼우면_빨개진다():
    """검사가 빨개질 수 있음을 증명한다 -- 안 그러면 통과가 아무 뜻이 없다."""
    장들 = _짓기()
    나쁜장 = bookK.장("TX", "일부러 어긴 장", "앞에서 안 나온 말을 쓴다",
                   쓰는것=["아무도안정의한개념"], 내놓는것=["임시개념"])
    어김, _ = bookK.사다리검사(장들 + [나쁜장])
    assert 어김, "어긴 장을 끼웠는데도 초록이다 -- 사다리검사가 아무것도 안 본다"
    assert 어김[0][0] == "TX", 어김
    bookK.장들.remove(나쁜장)


def test_중복정의도_자해로_잡힌다():
    장들 = _짓기()
    겹친장 = bookK.장("TY", "같은 것을 또 정의하는 장", "중복",
                   쓰는것=[], 내놓는것=[장들[0].내놓는것[0]])
    어김, _ = bookK.사다리검사(장들 + [겹친장])
    assert any(번호 == "TY" for 번호, _ in 어김), 어김
    bookK.장들.remove(겹친장)


def test_영어판에_순수_한국어가_안_남는다():
    """사용자(2026-09-20): "영어 교안도 pdf로 제공해줘."

    본문은 이미 영어였는데 **틀 글자와 그림 라벨과 개념 이름이 한국어**였다.
    `bookK.언어("en")` · `sch.언어("en")` 이 그것을 갈아 끼운다.  여기서는
    **괄호 밖에 한국어만 있는 글자가 남지 않았는지** 본다 -- 괄호 안의 용어 병기
    (`aperture jitter (구경지터)`)는 남겨 두는 것이 맞다.
    """
    import re
    import sch
    try:
        bookK.언어("en")
        sch.언어("en")
        장들 = _짓기()
        나쁨 = []
        for ch in 장들:
            h = ch.완성()
            본문 = re.sub(r"<pre.*?</pre>", "", h, flags=re.S)
            for t in re.findall(r">([^<]*[가-힣][^<]*)<", 본문):
                t = t.strip()
                if not t or re.search(r"\([^)]*[가-힣][^)]*\)", t):
                    continue          # 용어 병기는 괜찮다
                if not re.search(r"[A-Za-z0-9]", t):
                    나쁨.append((ch.번호, t[:60]))
        assert not 나쁨, "영어판에 한국어만 든 글자가 남았다:\n" + "\n".join(
            f"  {n}: {t}" for n, t in 나쁨[:10])
    finally:
        bookK.언어("ko")
        sch.언어("ko")
        _짓기()


def test_모든_개념에_영어_이름이_있다():
    import 개념영문
    장들 = _짓기()
    개념 = set()
    for ch in 장들:
        개념 |= set(ch.쓰는것) | set(ch.내놓는것)
    빠진 = sorted(c for c in 개념 if c not in 개념영문.영문)
    assert not 빠진, f"영어 이름이 없는 개념: {빠진}"


if __name__ == "__main__":
    import _run
    _run.돌리기(globals())
