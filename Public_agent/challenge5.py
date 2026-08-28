"""
challenge5 -- 선행 제약이 있는 부분집합 선택 최적화 (초고난도 평가용).

challenge3(역순 전사), challenge4(키스트림 시드 복원)에 이은 세 번째 문제다. 이번에는
암호 역추적이 아니라 조합 최적화가 관문이다.

# 문제
아래 build_instance()가 만드는 인스턴스는 n개의 항목으로 이뤄진다. 각 항목 i에는 정수
가중치 w[i]가 있다(양수면 이익, 음수면 비용). 그리고 선행 제약 목록 edges가 있는데,
(u, v)는 "u를 고르려면 v도 반드시 함께 골라야 한다"는 뜻이다.

이 제약을 지키는 부분집합 S를 실행가능해라 부른다. 즉 모든 (u, v)에 대해
u가 S에 있으면 v도 S에 있어야 한다(빈 집합과 전체 집합도 실행가능하다).

    목표: 실행가능한 S 중에서 sum(w[i] for i in S)를 최대로 만드는 S를 찾아라.

그 최적 S는 유일하다(출제 시 확인했다). 최적값과 최적 S는 이 파일에 없다.

# 채점
최적 S를 아래 규칙으로 열쇠로 바꾸면 CIPHERTEXT가 복호화되어 평문이 나온다.

    bits = ''.join('1' if i in S else '0' for i in range(n))    # 길이 n 비트 문자열
    key  = sha256(bits.encode()).digest()
    키스트림 = sha256(key + b'|' + str(counter).encode()).digest() 를 counter=0,1,2,...
              로 이어붙인 바이트열
    평문 = base85디코드(CIPHERTEXT) XOR 키스트림

solve()는 그 평문을 반환해야 한다. 채점은 복원값의 SHA-256이 EXPECTED_SHA256과
일치하는지로만 이뤄진다. 최적이 아닌 S를 쓰면 열쇠가 달라져 복호화 결과가 무의미한
바이트가 되므로, 부분점수는 없다.

# 주의
n은 234다. 실행가능한 부분집합을 전부 훑는 것은 경로가 아니다.
아래 is_feasible()과 value()는 후보를 스스로 검사해보라고 넣어둔 것이다.
"""
import base64
import hashlib

INSTANCE_SEED = 0x5A1B5381
EXPECTED_SHA256 = "f1e3d11623432bd3adf5916f638f5ff4e3c46c7123e10c81e23a7c10a07d42a4"
CIPHERTEXT = "CR<`xW*c_vM5F?r3jXk6bm+_9gRoA1qN`!fMsY-z;6E9~=Z-;*rbstH(B&6KvB=u(Saske74NRzwpBS@6Wb;1x-{z"

MASK64 = (1 << 64) - 1


class PRNG:
    """인스턴스 재현용 xorshift64* PRNG (파이썬 버전에 무관하게 같은 값이 나오도록 직접 구현)."""

    def __init__(self, seed: int):
        self.s = seed & MASK64

    def next(self) -> int:
        s = self.s
        s ^= (s << 13) & MASK64
        s ^= (s >> 7)
        s ^= (s << 17) & MASK64
        self.s = s & MASK64
        return (self.s * 0x2545F4914F6CDD1D) & MASK64

    def below(self, k: int) -> int:
        return self.next() % k


def build_instance(seed: int = INSTANCE_SEED, n_groups: int = 26, infra_per: int = 3,
                   rew_per: int = 6, share_pct: int = 30):
    """(w, edges)를 결정적으로 생성한다. w[i]는 항목 i의 가중치,
    edges의 (u, v)는 'u를 고르면 v도 골라야 한다'는 선행 제약이다."""
    rng = PRNG(seed)
    w: list[int] = []
    ginfra: list[list[int]] = []
    for _ in range(n_groups):
        gi = []
        for _ in range(infra_per):
            gi.append(len(w))
            w.append(-(150 + rng.below(350)))
        ginfra.append(gi)
    cost = [-sum(w[i] for i in ginfra[g]) for g in range(n_groups)]
    greward: list[list[int]] = []
    for g in range(n_groups):
        ratio = 55 + rng.below(95)
        target = cost[g] * ratio // 100
        gr = []
        rem = target
        for k in range(rew_per):
            share = rem // (rew_per - k) if k < rew_per - 1 else rem
            v = max(1, share + rng.below(21) - 10)
            gr.append(len(w))
            w.append(v)
            rem -= v
        greward.append(gr)
    edges: list[tuple[int, int]] = []
    for g in range(n_groups):
        for r in greward[g]:
            for i in ginfra[g]:
                edges.append((r, i))
            if rng.below(100) < share_pct:
                og = rng.below(n_groups)
                if og != g:
                    edges.append((r, ginfra[og][rng.below(infra_per)]))
    for g in range(n_groups):
        if g and rng.below(100) < 40:
            edges.append((ginfra[g][0], ginfra[rng.below(g)][rng.below(infra_per)]))
    return w, edges


def is_feasible(S, edges) -> bool:
    """S가 선행 제약을 모두 지키는지 검사한다."""
    S = set(S)
    return all((u not in S) or (v in S) for u, v in edges)


def value(S, w) -> int:
    return sum(w[i] for i in S)


def decrypt(S, n: int) -> str:
    """부분집합 S를 열쇠로 삼아 CIPHERTEXT를 복호화한다."""
    bits = "".join("1" if i in set(S) else "0" for i in range(n))
    key = hashlib.sha256(bits.encode()).digest()
    data = base64.b85decode(CIPHERTEXT.encode("ascii"))
    ks = b""
    c = 0
    while len(ks) < len(data):
        ks += hashlib.sha256(key + b"|" + str(c).encode()).digest()
        c += 1
    return bytes(a ^ b for a, b in zip(data, ks)).decode("utf-8", errors="replace")


def solve() -> str:
    # TODO: build_instance()의 (w, edges)에 대해 실행가능한 부분집합 중 가중치 합이
    # 최대인 S를 찾고, decrypt(S, len(w))로 평문을 복원해서 반환하라.
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
