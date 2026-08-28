"""
challenge3의 검증된 참조 정답. challenge3.py의 solve()를 올바르게 완성한 형태다.
이 파일을 실행하면 복원된 flag가 EXPECTED_SHA256과 일치함을 확인할 수 있다.
"""
import base64
import hashlib

from challenge3 import (
    OBFUSCATED,
    MULT,
    SEED,
    EXPECTED_SHA256,
    rotr8,
    xorshift32_stream,
    stride_perm_indices,
)


def _modinv256(a: int) -> int:
    for x in range(256):
        if (a * x) & 0xFF == 1:
            return x
    raise ValueError("가역이 아님")


MINV = _modinv256(MULT)  # MULT^{-1} mod 256


def solve() -> str:
    # E^{-1}: base85 디코드
    permuted = bytearray(base64.b85decode(OBFUSCATED.encode("ascii")))
    n = len(permuted)

    # D^{-1}: stride 순열 되돌리기(gather). forward가 permuted[pos]=data[perm[pos]]
    # 였으므로 data[perm[pos]] = permuted[pos].
    perm = stride_perm_indices(n)
    data = bytearray(n)
    for pos, src in enumerate(perm):
        data[src] = permuted[pos]

    # C^{-1}: 좌회전을 우회전으로
    for i in range(n):
        data[i] = rotr8(data[i], (i % 7) + 1)

    # B^{-1}: 같은 키스트림 XOR (XOR은 대합)
    ks = xorshift32_stream(SEED, n)
    for i in range(n):
        data[i] ^= ks[i]

    # A^{-1}: (MULT*x + c) & 0xFF = y  =>  x = MINV * ((y - c) & 0xFF) & 0xFF
    for i in range(n):
        c = (i * i + 7) & 0xFF
        data[i] = (MINV * ((data[i] - c) & 0xFF)) & 0xFF

    return bytes(data).decode("utf-8")


def main() -> None:
    answer = solve()
    digest = hashlib.sha256(answer.encode()).hexdigest()
    assert digest == EXPECTED_SHA256, f"검증 실패: {digest}"
    print("정답:", answer)
    print("MULT^-1 mod 256 =", MINV)
    print("검증: sha256 일치 OK")


if __name__ == "__main__":
    main()
