# AutoRegressivePatcher Self-Correction 루프 결과 (Challenge 2)

- **성공 여부**: 성공 (Exit Code 0)
- **소요된 Iteration 횟수**: 2회
- **최종 구현 코드**:
```python
def lcg_keystream(seed: int, n: int) -> list:
    state = seed
    stream = []
    for _ in range(n):
        state = (1103515245 * state + 12345) % (2**31)
        stream.append(state & 0xFF)
    return stream


def _nibble_swap(b: int) -> int:
    return ((b & 0x0F) << 4) | ((b & 0xF0) >> 4)


def solve() -> str:
    raw = base64.b85decode(OBFUSCATED.encode())
    swapped = bytes([_nibble_swap(b) for b in raw])
    stream = lcg_keystream(SEED, len(swapped))
    xor_ed = bytes([s ^ k for s, k in zip(swapped, stream)])
    return xor_ed[::-1].decode()
```
- **최종 정답 플래그**: `SE_HARD_v3rify_ok`
