"""
challenge4의 검증된 참조 정답.

핵심은 seed를 전수 탐색하지 않고 대수적으로 복원하는 것이다. 근거는 두 가지다.

1) xorshift64의 상태 전이는 GF(2) 위에서 선형이다. shift와 XOR만 쓰므로 state_k는
   초기 seed 64비트의 선형 함수이고, 상수항이 없다(seed=0이면 영원히 0). 따라서
   중첩 원리가 정확히 성립한다: seed = XOR(e_j)에 대한 키스트림 비트 = XOR(e_j별 비트).

2) 평문이 ASCII라 모든 바이트의 최상위 비트가 0이다. XOR 직후 값 t[i] = p[i] ^ ks[i]
   에서 MSB(t[i]) = MSB(ks[i])가 되므로, 바이트 하나마다 seed 64비트에 대한 선형
   방정식이 하나씩 생긴다. 68바이트면 방정식 68개 > 미지수 64개다.

그래서 기저 seed=1<<j 64개를 각각 굴려 MSB 열을 뽑아 계수행렬을 만들고, GF(2) 가우스
소거로 seed를 유일하게 결정한다(rank 64 확인). 이후는 키스트림을 재생성해 XOR만 하면 된다.
"""
import base64
import hashlib

from challenge4 import (
    CIPHERTEXT, EXPECTED_SHA256, xorshift64_stream, perm_indices,
)


def rotr8(b: int, r: int) -> int:
    r &= 7
    return ((b >> r) | (b << (8 - r))) & 0xFF


def _strip_key_independent_layers(ct: str) -> bytes:
    """base85 -> 순열 역 -> 회전 역. 여기까지는 seed 없이 되돌릴 수 있다."""
    v = base64.b85decode(ct.encode("ascii"))
    n = len(v)
    u = bytearray(n)
    for pos, src in enumerate(perm_indices(n)):
        u[src] = v[pos]
    return bytes(rotr8(u[i], (i % 5) + 1) for i in range(n))


def _recover_seed(t: bytes) -> int:
    """MSB 누출 + GF(2) 선형성으로 seed를 복원한다."""
    n = len(t)
    rhs_bits = [(t[i] >> 7) & 1 for i in range(n)]

    # 기저별 MSB 시퀀스 -> 방정식 i의 계수 벡터(64비트)
    basis = [[(k >> 7) & 1 for k in xorshift64_stream(1 << j, n)] for j in range(64)]
    equations = []
    for i in range(n):
        coef = 0
        for j in range(64):
            if basis[j][i]:
                coef |= 1 << j
        equations.append((coef, rhs_bits[i]))

    pivots: dict[int, tuple[int, int]] = {}
    for coef, rhs in equations:
        for bit in range(64):
            if not (coef >> bit) & 1:
                continue
            if bit in pivots:
                pcoef, prhs = pivots[bit]
                coef ^= pcoef
                rhs ^= prhs
            else:
                pivots[bit] = (coef, rhs)
                break
    if len(pivots) != 64:
        raise ValueError(f"해가 유일하지 않다 (rank={len(pivots)}). 방정식이 부족하다.")

    seed = 0
    for bit in sorted(pivots, reverse=True):
        pcoef, prhs = pivots[bit]
        val = prhs
        for higher in range(bit + 1, 64):
            if (pcoef >> higher) & 1 and (seed >> higher) & 1:
                val ^= 1
        if val:
            seed |= 1 << bit
    return seed


def solve() -> str:
    t = _strip_key_independent_layers(CIPHERTEXT)
    seed = _recover_seed(t)
    ks = xorshift64_stream(seed, len(t))
    return bytes(t[i] ^ ks[i] for i in range(len(t))).decode("ascii")


def main() -> None:
    t = _strip_key_independent_layers(CIPHERTEXT)
    seed = _recover_seed(t)
    answer = solve()
    digest = hashlib.sha256(answer.encode()).hexdigest()
    assert digest == EXPECTED_SHA256, f"검증 실패: {digest}"
    print("복원한 seed: 0x%016X" % seed)
    print("정답:", answer)
    print("검증: sha256 일치 OK")


if __name__ == "__main__":
    main()
