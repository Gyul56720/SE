r"""불 회로 -- **계산 복잡도.** 대상: 게이트 목록.

3입력 다수결을 AND/OR 게이트 4개로. 입력 2^3=8 개를 다 보므로 완전 판정이다.
게이트 t 는 앞선 것(입력 3개 + 앞 게이트 t개)만 참조한다 -- 순환이 없다.
"""

물음 = "3입력 다수결(MAJ3)을 AND · OR 게이트 4개로 만들 수 있는가"


def sample(rng):
    """게이트 4개. 각각 [연산(0=AND,1=OR), 왼쪽, 오른쪽]. 마지막 게이트가 출력."""
    out = []
    for t in range(4):
        쓸수있는것 = 3 + t
        out.append([rng.randrange(2),
                    rng.randrange(쓸수있는것), rng.randrange(쓸수있는것)])
    return out


def judge(x):
    """입력 8가지를 다 돌린다. **완전 판정.**"""
    if not isinstance(x, (list, tuple)) or len(x) != 4:
        raise ValueError("게이트가 4개가 아니다")
    회로 = []
    for t, g in enumerate(x):
        연산, a, b = int(g[0]), int(g[1]), int(g[2])
        if 연산 not in (0, 1):
            raise ValueError("연산이 AND(0)나 OR(1)이 아니다: %r" % (연산,))
        if not (0 <= a < 3 + t and 0 <= b < 3 + t):
            raise ValueError("앞선 것만 참조할 수 있다: %r" % (g,))
        회로.append((연산, a, b))
    for bits in range(1 << 3):
        값 = [(bits >> t) & 1 for t in range(3)]
        for 연산, a, b in 회로:
            값.append(값[a] & 값[b] if 연산 == 0 else 값[a] | 값[b])
        if 값[-1] != (1 if sum(값[:3]) >= 2 else 0):
            return False
    return True
