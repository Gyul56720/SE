# -*- coding: utf-8 -*-
"""매뉴얼이 쓰는 그림을 SVG 파일로 낸다.

    python3 manual/그림만들기.py

왜 파일로 내나: 마크다운 안에 SVG 를 직접 넣으면 GitHub 등이 제대로
안 그린다.  `<img src="그림/x.svg">` 로 거는 것이 어디서나 보인다.

그림은 `edu/sch.py` 가 그린다 -- 교재와 매뉴얼이 **같은 그림 라이브러리**를
쓴다.  두 벌로 그리면 한쪽만 고치는 사고가 난다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "edu"))
import sch  # noqa: E402

여기 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "그림")

그림들 = [
    ("시스템아키텍처", sch.시스템아키텍처),
    ("동기화기",       sch.동기화기),
    ("다중비트깨짐",   sch.다중비트깨짐),
    ("리셋동기화기",   sch.리셋동기화기),
    ("조합고리",       sch.조합고리),
    ("스키드버퍼",     sch.스키드버퍼),
    ("폭성장",         sch.폭성장),
    ("파이프라인전후", sch.파이프라인전후),
    ("씨모스낸드",     sch.씨모스낸드),
    ("전가산기",       sch.전가산기),
    ("플립플롭파형",   lambda: sch.파형([("clk", "_^_^_^_^"),
                                        ("d",   "__^^__^^"),
                                        ("q",   "___^^__^")])),
]


def 만들기():
    os.makedirs(여기, exist_ok=True)
    난것 = []
    for 이름, 함수 in 그림들:
        s = 함수()
        # SVG 에는 마크다운이 없다.  별표가 남았으면 화면에 그대로 보인다.
        별 = sch.글자에별이없나(s)
        if 별:
            raise SystemExit(f"{이름}: SVG 글자에 마크다운 별표가 남았다 {별[:2]}")
        p = os.path.join(여기, 이름 + ".svg")
        open(p, "w", encoding="utf-8").write(s)
        난것.append((이름, len(s)))
    return 난것


if __name__ == "__main__":
    for 이름, n in 만들기():
        print(f"  {이름}.svg  {n:,} 바이트")
    print(f"\n{len(그림들)} 개를 {여기} 에 냈다")
