r"""seek 검사들이 같이 쓰는 고정물. **본문이 없다** -- 임포트해도 아무것도 안 돈다.

두 사슬(길이 1~3 · 10~12)과 덜 푼 가지들. 사슬이 하나면 모두가 서로의 조상이나
후손이라 무작위로 고를 남이 없어서 대조군이 안 선다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import problem as PR                                # noqa: E402


def 판정(k):
    return (f"def judge(x):\n"
            f"    if not isinstance(x, list) or len(x) != {k}:\n"
            f"        raise ValueError('{k}개가 아니다')\n"
            f"    return sum(x) == 1\n")


def 꼴맞춤(k):
    """무엇이 오든 제 꼴로 우겨넣는다 -- 부모가 누구든 보존이 선다."""
    return (f"def embed(x):\n    y = list(x)[:{k}]\n"
            f"    return y + [0] * ({k} - len(y))\n")


def 부모확인(부, k):
    """부모의 꼴을 확인하고 옮긴다 -- 남이 오면 터진다."""
    return (f"def embed(x):\n"
            f"    if len(x) != {부}:\n        raise ValueError('남의 것이다')\n"
            f"    y = list(x)[:{k}]\n    return y + [0] * ({k} - len(y))\n")


def 답(k):
    return [1] + [0] * (k - 1)


# (id, 길이, 부모, 연산자, 옮김, 답있나)
세상 = [
    ("A0", 1, "-", "씨앗", None, True),
    ("A1", 2, "A0", "부모봄", "부모확인", True),
    ("A2", 3, "A1", "꼴만봄", "꼴맞춤", True),
    ("B0", 10, "-", "씨앗", None, True),
    ("B1", 11, "B0", "부모봄", "부모확인", True),
    ("B2", 12, "B1", "꼴만봄", "꼴맞춤", True),
    ("C0", 20, "-", "씨앗", None, False),          # 부모만 없음
    ("C1", 21, "C0", "덜푼것", "꼴맞춤", True),
    ("D0", 30, "-", "씨앗", None, True),           # 자식만 없음
    ("D1", 31, "D0", "덜푼것", "꼴맞춤", False),
    ("E0", 40, "-", "씨앗", None, False),          # 둘 다 없음
    ("E1", 41, "E0", "덜푼것", "꼴맞춤", False),
    # **한 연산자 안에 잰 것과 못 잰 것이 같이 있는 자리.** 이것이 없으면 분모를
    # 걸음 수로 바꿔도 표가 안 변해서, 사보타주가 red 를 못 낸다(실측: exit=0).
    ("F0", 50, "-", "씨앗", None, True),
    ("F1", 51, "F0", "섞임", "꼴맞춤", True),
    ("F2", 52, "F1", "섞임", "꼴맞춤", False),
]
길이 = {i: k for i, k, *_ in 세상}


def 원장() -> dict:
    led = PR.blank()
    for pid, k, par, op, 옮, 있 in 세상:
        rec = {"id": pid, "물음": pid, "표본": "def sample(rng):\n    return []\n",
               "판정": 판정(k),
               "옮김": ("" if 옮 is None else
                        (꼴맞춤(k) if 옮 == "꼴맞춤" else 부모확인(길이[par], k))),
               "계보": {"부모": par, "연산자": op},
               "깊이": 0 if par == "-" else 1}
        if 있:
            rec["답"] = 답(k)
        led["problems"].append(rec)
    led["seq"] = len(세상)
    return led


