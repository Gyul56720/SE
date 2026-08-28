"""
challenge3 -- 5중 난독화 역추적 문제 (고난도 평가용).

challenge.py / challenge2.py 보다 상위 난이도. 아래 solve()는 스텁이라 항상 틀린 값을
반환한다. 모델은 OBFUSCATED가 만들어진 순서를 정확히 역으로 풀어 원본 flag를 복원하는
solve()를 완성해야 한다. 검증은 복원값의 SHA-256이 EXPECTED_SHA256과 일치하는지로만
이뤄진다(정답 평문은 파일 어디에도 없다).

난이도 포인트(약한 모델이 자주 틀리는 지점):
  - 5개 레이어를 정확히 "역순"으로, 각각 올바른 역연산으로 풀어야 한다.
  - Step A의 인덱스 의존 아핀 변환은 mod 256에서 곱셈 역원(MULT^{-1} mod 256)이 필요하다.
    단순히 나눗셈으로 되돌리려 하면 실패한다.
  - Step C의 비트 회전은 회전 방향과 회전량(i에 의존)을 정확히 반대로 맞춰야 한다.
  - Step D의 stride 순열은 "역순열"을 만들어 흩어진 바이트를 제자리로 모아야 한다.
    scatter(뿌리기)와 gather(모으기)를 헷갈리면 조용히 깨진다.
"""
import base64
import hashlib

OBFUSCATED = "`pCnhyDUgmOr!n8>)k?-{cm`v^1CCvY#O=zSM^h+n3T5tSGUEC$FzR"
MULT = 167            # Step A 곱셈 상수 (홀수 -> mod 256에서 가역)
SEED = 0x1F35A2C7     # Step B xorshift32 시드
EXPECTED_SHA256 = "f1bd25d07fd16662e11dcaab94415ddd412dbcbebfba81e938cbd779e16d6a8e"


def rotl8(b: int, r: int) -> int:
    r &= 7
    return ((b << r) | (b >> (8 - r))) & 0xFF


def rotr8(b: int, r: int) -> int:
    r &= 7
    return ((b >> r) | (b << (8 - r))) & 0xFF


def xorshift32_stream(seed: int, n: int) -> "list[int]":
    """xorshift32 PRNG로 n바이트 키스트림 생성. 매 스텝 state를 갱신한 뒤 (state & 0xFF).
    점화식: s ^= s<<13; s ^= s>>17; s ^= s<<5  (모두 32비트로 마스킹)."""
    s = seed & 0xFFFFFFFF
    out = []
    for _ in range(n):
        s ^= (s << 13) & 0xFFFFFFFF
        s ^= (s >> 17)
        s ^= (s << 5) & 0xFFFFFFFF
        s &= 0xFFFFFFFF
        out.append(s & 0xFF)
    return out


def stride_perm_indices(n: int) -> "list[int]":
    """Step D 순열: 짝수 인덱스 먼저, 그다음 홀수 인덱스. 즉 [0,2,4,...,1,3,5,...].
    forward 인코딩은 permuted[pos] = data[perm[pos]] (scatter)로 만들었다."""
    return [i for i in range(0, n, 2)] + [i for i in range(1, n, 2)]


def solve() -> str:
    # TODO: OBFUSCATED는 원본 평문에 아래 순서로 5개 레이어를 적용해 만들어졌다.
    # 이 함수는 그 과정을 정확히 역으로 풀어 원본 평문을 반환해야 한다.
    #
    #   forward (평문 -> OBFUSCATED):
    #     A. data[i] = (MULT * data[i] + (i*i + 7)) & 0xFF        # 인덱스 의존 아핀
    #     B. data[i] ^= xorshift32_stream(SEED, n)[i]             # 키스트림 XOR
    #     C. data[i] = rotl8(data[i], (i % 7) + 1)                # 인덱스 의존 좌회전
    #     D. permuted[pos] = data[stride_perm_indices(n)[pos]]    # stride 순열(scatter)
    #     E. base85 인코딩
    #
    # 지금은 스텁이라 원문과 무관한 값을 반환해서 검증에 실패한다.
    return "TODO"


def main() -> None:
    answer = solve()
    digest = hashlib.sha256(answer.encode()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"오답: sha256({answer!r}) = {digest}, 기대값과 다름")
    print("정답:", answer)


if __name__ == "__main__":
    main()
