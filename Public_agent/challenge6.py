"""
challenge6 -- 공개키 하나와 암호문 하나 (최고난도 평가용).

challenge4(키스트림 시드 복원), challenge5(위장된 다항시간 최적화)에 이은 문제다.
이번에는 출제자도 트랩도어 없이는 풀 수 없다 -- N을 두 소수의 곱으로 만들었기 때문에
답을 아는 것이지, N을 보고 인수분해할 수 있어서가 아니다.

# 주어지는 것
N  : 1023비트 정수
E  : 공개 지수
C  : pow(M, E, N) 으로 만들어진 암호문. M은 576비트 정수이며 주어지지 않는다.
CIPHERTEXT : 평문 flag를 M으로 유도한 키스트림과 XOR한 뒤 base85로 인코딩한 것.

# 목표
M을 복원해서 decrypt(M)이 돌려주는 평문을 solve()가 반환해야 한다.
채점은 복원값의 SHA-256이 EXPECTED_SHA256과 일치하는지로만 이뤄진다.

# 알려진 사실
- M은 576비트다. 따라서 pow(M, E)는 N보다 크고, 실제로 모듈러 감산이 일어난다.
- 평문은 출력 가능한 ASCII다.
- N의 인수분해는 주어지지 않는다. 일반적인 1023비트 반소수 인수분해는 경로가 아니다.
- decrypt()는 아래에 완전히 공개돼 있다. 감춰진 것은 M뿐이다.
"""
import base64
import hashlib

N = 44942328371557897693232629769725618340449424473557664318357520289433168951375240783177119330601884005280028469967848339414697442203604247444587087894312053282869533129446945405832839381544818995392055851335331428365959106693347823394750669880069515984425153196848493155368645163619500280387874521107814556237
E = 3
C = 24263088470903456603680908554964542925836087925530082904120401734765121217972374602564337103082153691397838860902131045867968008233755375745346568170699001391476291648741333053388492756585184030414160618642440016691020127159597501811883402846938380065974346580668262401939058097892371142897502404162827516295

CIPHERTEXT = "@wdD6nE!CQRt;O-ygC6Gz<BGhFX@!B<)So)PfW!zBwv7A!^O1#)2)axOK@%9GQP7d`vF?h#Cv6}XxBv9Qdm&-olX"
EXPECTED_SHA256 = "ce4ffe66d03a2c603c2c824c97b5bcbaf1ee817f91933f18db0aa74b5f7a7890"

BYTE_LEN = (N.bit_length() + 7) // 8


def keystream(m_int: int, length: int) -> bytes:
    """M으로부터 키스트림을 유도한다. M은 BYTE_LEN 바이트 빅엔디언으로 인코딩된다."""
    k = hashlib.sha256(m_int.to_bytes(BYTE_LEN, "big")).digest()
    out = b""
    i = 0
    while len(out) < length:
        out += hashlib.sha256(k + b"|" + str(i).encode()).digest()
        i += 1
    return out[:length]


def decrypt(m_int: int) -> str:
    """후보 M으로 CIPHERTEXT를 복호화한다. 틀린 M이면 의미 없는 바이트가 나온다."""
    data = base64.b85decode(CIPHERTEXT.encode("ascii"))
    return bytes(a ^ b for a, b in zip(data, keystream(m_int, len(data)))).decode(
        "ascii", errors="replace"
    )


def solve() -> str:
    # TODO: C = pow(M, E, N) 을 만족하는 576비트 M을 복원하고, decrypt(M)이 돌려주는
    # 평문을 반환하라. 지금은 스텁이라 검증에 실패한다.
    return "TODO"


def main() -> None:
    answer = solve()
    digest = hashlib.sha256(answer.encode()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"오답: sha256({answer!r}) = {digest}, 기대값과 다름")
    print("정답:", answer)


if __name__ == "__main__":
    main()
