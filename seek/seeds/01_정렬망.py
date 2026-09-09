r"""정렬망 -- **조합 최적화.** 대상: 비교기 목록."""

물음 = "5선 정렬망을 비교기 9개로 만들 수 있는가 (크기)"


def sample(rng):
    """비교기 9개. 각각 (i, j), i < j."""
    out = []
    for _ in range(9):
        i = rng.randrange(5 - 1)
        j = rng.randrange(i + 1, 5)
        out.append([i, j])
    return out


def judge(x):
    """**0/1 원리.** 0과 1로만 된 입력 2^5 개를 다 정렬하면 모든 입력을 정렬한다.
    유한 소진이라 이 판정은 완전하다 -- 근사도 표본도 아니다."""
    if not isinstance(x, (list, tuple)) or len(x) != 9:
        raise ValueError("비교기가 9개가 아니다")
    net = []
    for c in x:
        i, j = int(c[0]), int(c[1])
        if not (0 <= i < j < 5):
            raise ValueError("비교기 꼴이 아니다: %r" % (c,))
        net.append((i, j))
    for bits in range(1 << 5):
        v = [(bits >> t) & 1 for t in range(5)]
        for i, j in net:
            if v[i] > v[j]:
                v[i], v[j] = v[j], v[i]
        if any(v[t] > v[t + 1] for t in range(5 - 1)):
            return False
    return True
