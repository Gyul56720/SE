import base64
import hashlib

OBFUSCATED = "9YA@34&q?yM$1aP@pm-=lK"
SEED = 0xACE5
EXPECTED_SHA256 = "7c89ef9c9e56c2be62b98c1895faa30b8eb074fc636b764c26ff82480150e520"


def lcg_keystream(seed: int, n: int) -> list:
    # TODO: LCG(Linear Congruential Generator)로 n바이트짜리 키스트림을 만든다.
    # 점화식: state_{i+1} = (1103515245 * state_i + 12345) mod 2**31
    # 매 스텝 state를 먼저 갱신한 뒤 (state & 0xFF)를 키스트림 바이트로 취한다.
    # 지금은 스텁이라 항상 전부 0을 반환해서 아래 solve()가 틀린 값을 낸다.
    state = seed
    stream = []
    for _ in range(n):
        state = (1103515245 * state + 12345) % (2**31)
        stream.append(state & 0xFF)
    return stream


def _nibble_swap(b: int) -> int:
    return ((b & 0x0F) << 4) | ((b & 0xF0) >> 4)


def solve() -> str:
    # TODO: OBFUSCATED는 다음 순서로 만들어졌다 (역으로 풀어야 함):
    #   1. 평문을 바이트로 인코딩 후 바이트 순서를 뒤집는다 (data[::-1])
    #   2. lcg_keystream(SEED, len(data))로 만든 키스트림과 바이트 단위 XOR
    #   3. 각 바이트에 니블 스왑(상위/하위 4비트 교환) 적용
    #   4. base85로 인코딩
    # 이 함수는 원본 평문을 복원해서 반환해야 한다. 지금은 빈 스켈레톤이라 항상 빈
    # 문자열을 반환해서 검증에 실패한다.
    raw = base64.b85decode(OBFUSCATED.encode())
    swapped = bytes([_nibble_swap(b) for b in raw])
    stream = lcg_keystream(SEED, len(swapped))
    xor_ed = bytes([s ^ k for s, k in zip(swapped, stream)])
    return xor_ed[::-1].decode()


def main() -> None:
    answer = solve()
    digest = hashlib.sha256(answer.encode()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"오답: sha256({answer!r}) = {digest}, 기대값과 다름")
    print("정답:", answer)


if __name__ == "__main__":
    main()
