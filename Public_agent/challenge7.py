"""
challenge7 -- 공개키 하나와 암호문 하나.

# 주어지는 것
N  : 1023비트 정수
E  : 공개 지수
C  : pow(M, E, N). M은 576비트 정수이며 주어지지 않는다.
CIPHERTEXT : 평문 flag를 M으로 유도한 키스트림과 XOR한 뒤 base85로 인코딩한 것.

# 목표
M을 복원해 decrypt(M)이 돌려주는 평문을 solve()가 반환해야 한다.
채점은 복원값의 SHA-256이 EXPECTED_SHA256과 일치하는지로만 이뤄진다.

# 알려진 사실
- M은 576비트다. 따라서 pow(M, E)는 N보다 크고 실제로 모듈러 감산이 일어난다.
- 평문은 출력 가능한 ASCII다.
- N의 인수분해는 주어지지 않는다.
- decrypt()는 아래에 완전히 공개돼 있다. 감춰진 것은 M뿐이다.
"""
import base64
import hashlib

N = 48524581369841512345420173010106877947706763352269527505509269220878801573744789616185445481149510835500349544354654975338923172957371758765581894012497443213196241108263140787298985451174406677934660558606064165389773406773861076216300877651108420979893510599149570796162471472167964877902794716314391811489
E = 3
C = 22561319719259119611544433223759253461628007687057772728881569499308758217235987063565695032514381705037401446150651238471724716757202835629694861692855187849206090610809185478539336800209900637049243426980730901422460994414382478026737946801949222959455556704651306650296309848800889679831469445803207647192

CIPHERTEXT = "JX+tf>d1_&MSGPq(iw{Fsz7RT0FffzwIfZvXG8}XsmjTaHuC4pNr!v^XDv3_N$E+Y&2KF%2tCAbq91CFxXe!ETpMEI_y"
EXPECTED_SHA256 = "e37ef11d057967b43c544de1164efcb31e9cb5705e438a3df1c4a7d7f9898739"

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
