"""
challenge4 -- 키스트림 시드 복원 문제 (고난도 평가용).

challenge3의 출제 결함을 고친 문제다. challenge3는 주석에 forward 파이프라인 5단계를
그대로 나열하고 역연산 헬퍼(rotr8, xorshift32_stream)까지 완성 상태로 제공해서, 실제로는
역추적이 아니라 "역순으로 옮겨 적기" 과제였다 -- Gemini가 1차 시도에 통과했다.
그래서 이번에는 다음을 지킨다.

  - 역연산 방법을 설명하지 않는다. 단계별 힌트도 없다.
  - 역연산 헬퍼를 제공하지 않는다. 필요하면 직접 작성해야 한다.
  - 그리고 결정적으로, 복호화에 필요한 SEED를 주지 않는다.

아래 encode()는 평문을 CIPHERTEXT로 만든 실제 인코더 전문이다(암호는 공개 알고리즘이고
비밀은 키뿐이라는 원칙대로, 알고리즘은 전부 공개한다). encode()에 넘긴 seed는 64비트
정수이며 이 파일 어디에도 없다. 전수 탐색은 2**64 규모라 현실적인 방법이 아니다.

알려진 사실은 이것뿐이다: 원본 평문은 출력 가능한 ASCII 문자열이다.

solve()는 CIPHERTEXT로부터 원본 평문을 복원해서 반환해야 한다. 채점은 복원값의 SHA-256이
EXPECTED_SHA256과 일치하는지로만 이뤄진다(정답 평문은 이 저장소 어디에도 없다).
"""
import base64
import hashlib

CIPHERTEXT = "lCwTlQw|~}s1#VJPUSBOK(P$~Q%meOF1^EiULp%-q0vf%4;t$Vx}Xk?eqy8d)HxC8%%yA9PXmzAyFi_I<y~B0"
EXPECTED_SHA256 = "c5aa12658c72027d1010da0ffa509dd8bf94da266c3630041cd808d61175598c"

MASK64 = (1 << 64) - 1


def xorshift64_stream(seed: int, n: int) -> "list[int]":
    """xorshift64로 n바이트 키스트림을 만든다. 매 스텝 state를 갱신한 뒤 (state & 0xFF)."""
    s = seed & MASK64
    out = []
    for _ in range(n):
        s ^= (s << 13) & MASK64
        s ^= (s >> 7)
        s ^= (s << 17) & MASK64
        s &= MASK64
        out.append(s & 0xFF)
    return out


def rotl8(b: int, r: int) -> int:
    r &= 7
    return ((b << r) | (b >> (8 - r))) & 0xFF


def perm_indices(n: int) -> "list[int]":
    return ([i for i in range(n) if i % 3 == 0]
            + [i for i in range(n) if i % 3 == 1]
            + [i for i in range(n) if i % 3 == 2])


def encode(plaintext: str, seed: int) -> str:
    """CIPHERTEXT를 만든 인코더 전문. seed는 64비트 정수이며 여기 주어지지 않는다."""
    p = plaintext.encode("ascii")
    n = len(p)
    ks = xorshift64_stream(seed, n)
    t = bytes([p[i] ^ ks[i] for i in range(n)])
    u = bytes([rotl8(t[i], (i % 5) + 1) for i in range(n)])
    idx = perm_indices(n)
    v = bytes([u[j] for j in idx])
    return base64.b85encode(v).decode("ascii")


def solve() -> str:
    # TODO: CIPHERTEXT로부터 원본 평문을 복원해서 반환하라.
    # 위 encode()가 인코더 전문이고, 거기 쓰인 seed는 이 파일에 없다.
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
