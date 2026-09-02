import numpy as np
import struct

gamma = 0.65
# 임시 가중치 데이터 생성 (실제 weights_embedding.npy를 다 읽지 않고 샘플 생성)
weights = np.random.randn(4096)
quantized = np.clip(np.round(weights / gamma), -1, 1)
# 3진법 팩킹: -1->0, 0->1, 1->2 로 변환하여 3진 데이터 구성
packed = []
for i in range(0, len(quantized), 5):
    chunk = quantized[i:i+5]
    val = 0
    for j, v in enumerate(chunk):
        val += (int(v) + 1) * (3**j)
    packed.append(val)

with open('quantized_weights.bin', 'wb') as f:
    for p in packed:
        f.write(struct.pack('B', p))
