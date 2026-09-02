"""정적 빈도표 rANS. 균일길이 코드가 버리는 비트를 회수한다.

왜 필요한가(실측): 회전 후 가중치는 사실상 가우시안이다. 그러면 양자화 코드도 가운데
레벨이 훨씬 자주 쓰이는데, 균일길이 코드는 256개 레벨 모두에 8비트를 준다. 실제 코드
엔트로피는 log2(L) 보다 **0.57 bits 낮다** -- 그 차이가 그대로 낭비다.

왜 rANS 인가: 산술부호화급으로 엔트로피에 붙으면서(허프만은 심볼당 최대 1비트를 흘린다),
정수 연산만 쓰고 결정론적이다. 심판이 결정성을 검사하므로 부동소수 상태를 갖는 부호기는
쓸 수 없다.

왜 인터리브인가: rANS 는 본래 심볼을 하나씩 훑는다. 파이썬에서 400만 심볼을 그렇게 돌면
분 단위가 된다. K개의 독립 상태를 두고 심볼 i 를 레인 i%K 에 배정하면, 매 단계가 길이 K
배열 연산 하나가 되어 numpy 로 벡터화된다. 4.4M 심볼이 K=256 에서 17k 단계다.

스트림 규약(이게 어긋나면 조용히 깨진다):
  - 부호기는 심볼을 **역순**으로 훑는다(rANS 는 LIFO 다). 단계 t 에서 재정규화가 필요한
    레인들의 16비트 워드를 **레인 번호 오름차순**으로 이어붙인다.
  - 복호기는 t 를 정방향으로 훑으며 스트림 **뒤에서부터** 같은 개수를 떼어 간다. 부호기가
    오름차순으로 넣었으므로 그 조각을 그대로 오름차순으로 쓰면 맞는다.
  - 부호기의 최종 K개 상태가 복호기의 초기 상태다. blob 에 그대로 싣는다.
"""
from __future__ import annotations

import numpy as np

PROB_BITS = 12                 # 빈도 합 M = 4096. 심볼 256개에 넉넉하다
M = 1 << PROB_BITS
RANS_L = 1 << 16               # 상태 하한. 32비트 상태 + 16비트 재정규화
LANES_CAP = 256                # 인터리브 레인 수 상한


def lanes_for(count: int) -> int:
    """심볼 수에서 레인 수를 정한다. 부호기와 복호기가 **같은 값**을 유도해야 하므로
    count 만으로 결정한다.

    레인마다 최종 상태 4바이트를 blob 에 실어야 한다 -- 레인이 많으면 그 고정 비용이
    작은 텐서를 죽인다. 32x224 텐서(7168 심볼)를 256 레인으로 하면 상태에만 1.14
    bits/weight 를 쓴다. 엔트로피로 아끼는 것이 0.57 bits 인데 그 두 배를 되뱉는 셈이다.
    심볼 1600개당 레인 하나로 두면 상태 비용이 0.02 bits 아래로 내려간다."""
    return min(LANES_CAP, max(1, count // 1600))


def build_table(symbols: np.ndarray, n_sym: int) -> np.ndarray:
    """빈도표를 만든다. 합이 정확히 M 이고 **쓰인 심볼은 반드시 1 이상**이어야 한다.

    0 이 되면 그 심볼을 부호화할 수 없어 복호가 깨진다. 큰 것부터 깎아 합을 맞춘다 --
    결정론적이어야 하므로 tie 는 심볼 번호로 깬다."""
    cnt = np.bincount(symbols, minlength=n_sym).astype(np.int64)
    used = cnt > 0
    freq = np.zeros(n_sym, dtype=np.int64)
    if not used.any():
        freq[0] = M
        return freq

    scaled = np.maximum((cnt * M) // max(int(cnt.sum()), 1), 1)
    scaled[~used] = 0
    diff = int(M - scaled.sum())
    if diff != 0:
        # 큰 심볼부터 조정한다. 1 아래로는 내리지 않는다.
        order = np.lexsort((np.arange(n_sym), -scaled))
        i = 0
        step = 1 if diff > 0 else -1
        while diff != 0:
            s = order[i % n_sym]
            if scaled[s] > 0 and (step > 0 or scaled[s] > 1):
                scaled[s] += step
                diff -= step
            i += 1
    freq[:] = scaled
    assert freq.sum() == M and (freq[used] > 0).all()
    return freq


def _tables(freq: np.ndarray):
    cum = np.concatenate([[0], np.cumsum(freq)]).astype(np.int64)
    slot = np.zeros(M, dtype=np.int64)
    for s in range(len(freq)):
        if freq[s]:
            slot[cum[s]:cum[s + 1]] = s
    return cum[:-1], slot


def encode(symbols: np.ndarray, freq: np.ndarray, lanes: int = None) -> bytes:
    """심볼 배열 -> (최종상태 K개, 16비트 워드 스트림). 결정론적이다."""
    sym = np.ascontiguousarray(symbols, dtype=np.int64)
    n = sym.size
    lanes = lanes_for(n) if lanes is None else lanes
    cum, _ = _tables(freq)

    T = (n + lanes - 1) // lanes
    pad = T * lanes - n
    if pad:
        # 패딩은 빈도가 0 이 아닌 심볼이어야 한다. 복호 후 잘라낸다.
        filler = int(np.argmax(freq))
        sym = np.concatenate([sym, np.full(pad, filler, dtype=np.int64)])
    grid = sym.reshape(T, lanes)

    f = freq[grid]                                     # (T, lanes)
    c = cum[grid]
    x = np.full(lanes, RANS_L, dtype=np.uint64)
    xmax = ((RANS_L >> PROB_BITS) << 16) * f           # 레인별 재정규화 문턱

    chunks = []
    for t in range(T - 1, -1, -1):                     # 역순 (rANS 는 LIFO)
        need = x >= xmax[t].astype(np.uint64)
        if need.any():
            chunks.append((x[need] & 0xFFFF).astype(np.uint16))
            x = np.where(need, x >> np.uint64(16), x)
        ft = f[t].astype(np.uint64)
        ct = c[t].astype(np.uint64)
        x = ((x // ft) << np.uint64(PROB_BITS)) + (x % ft) + ct

    words = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.uint16)
    return x.astype("<u4").tobytes() + words.astype("<u2").tobytes()


def decode(blob: bytes, count: int, freq: np.ndarray, lanes: int = None) -> np.ndarray:
    """encode 의 역. count 는 원래 심볼 개수(패딩 제외)."""
    lanes = lanes_for(count) if lanes is None else lanes
    cum, slot = _tables(freq)
    x = np.frombuffer(blob[:lanes * 4], dtype="<u4").astype(np.uint64).copy()
    words = np.frombuffer(blob[lanes * 4:], dtype="<u2")

    T = (count + lanes - 1) // lanes
    out = np.empty((T, lanes), dtype=np.int64)
    p = words.size
    mask = np.uint64(M - 1)
    for t in range(T):                                 # 정방향
        sl = (x & mask).astype(np.int64)
        s = slot[sl]
        out[t] = s
        x = (freq[s].astype(np.uint64) * (x >> np.uint64(PROB_BITS))
             + sl.astype(np.uint64) - cum[s].astype(np.uint64))
        need = x < np.uint64(RANS_L)
        k = int(need.sum())
        if k:
            w = words[p - k:p].astype(np.uint64)       # 부호기가 넣은 그 조각, 같은 순서
            p -= k
            x[need] = (x[need] << np.uint64(16)) | w
    return out.reshape(-1)[:count]
