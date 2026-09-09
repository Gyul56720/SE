r"""유한 반군 -- **대수.** 대상: 곱셈표.

원소 4개 위의 결합적 이항연산 중 **항등원이 없는** 것. 결합법칙은 4^3=64 개
삼중쌍을 다 보므로 완전 판정이고, 항등원 없음도 4개를 다 본다.
"""

물음 = "원소 4개 위에 결합적이면서 항등원이 없는 이항연산이 있는가"


def sample(rng):
    """4x4 곱셈표. 칸마다 0~3."""
    return [[rng.randrange(4) for _ in range(4)] for _ in range(4)]


def judge(x):
    """결합법칙 64개 + 항등원 없음 4개. **완전 판정.**"""
    if not isinstance(x, (list, tuple)) or len(x) != 4:
        raise ValueError("표가 4줄이 아니다")
    표 = []
    for 줄 in x:
        if not isinstance(줄, (list, tuple)) or len(줄) != 4:
            raise ValueError("줄이 4칸이 아니다: %r" % (줄,))
        칸 = [int(v) for v in 줄]
        if any(not (0 <= v < 4) for v in 칸):
            raise ValueError("칸이 0~3 이 아니다: %r" % (칸,))
        표.append(칸)
    for a in range(4):
        for b in range(4):
            for c in range(4):
                if 표[표[a][b]][c] != 표[a][표[b][c]]:
                    return False
    for e in range(4):
        if all(표[e][a] == a and 표[a][e] == a for a in range(4)):
            return False                      # 항등원이 있으면 안 받는다
    return True
