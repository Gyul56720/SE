import base64
import hashlib
import sys

OBFUSCATED = "SRlME3VhZXV6ZWVmdW95"
KEY = 0x2A
EXPECTED_SHA256 = "cf259f5748329bf7e72548ec4a9e4287a6d6e6d8ccf579b8015dc6fcce80281d"


def solve() -> str:
    # TODO: OBFUSCATED는 "역순 -> XOR(KEY) -> base64"로 생성된 3중 난독화 문자열이다.
    # 이 함수는 원본 평문(flag)을 복원해서 반환해야 한다. 지금은 빈 스켈레톤이라
    # 항상 틀린 값을 반환해서 아래 검증에서 실패한다.
    b = base64.b64decode(OBFUSCATED)
    x = bytes([c ^ KEY for c in b])
    return x[::-1].decode()


def main() -> None:
    answer = solve()
    digest = hashlib.sha256(answer.encode()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"오답: sha256({answer!r}) = {digest}, 기대값과 다름")
    print("정답:", answer)


if __name__ == "__main__":
    main()
