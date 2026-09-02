# compression — 실제 가중치로 압축 코덱을 탐색한다

목표: **int8 을 압축력과 복원력 두 축에서 동시에 이기는 코덱**을 자가개선 루프로 찾는다.
JPEG 을 사람이 설계한 자리에 탐색을 놓되, 무엇이 더 나은가는 LLM 이 아니라 심판이 정한다.

```
실제 모델 가중치 ──> design 셋 ──> orchestrator 가 코덱을 쓴다
                                        │
                                  judge 가 격리 실행해 채점 (LLM 이 만든 심판이 아니다)
                                        │
                      통과 ──> holdout 셋으로 재채점 ──> 두 축 모두 이기면 챔피언 교체
```

## 파일

| 파일 | 역할 |
|---|---|
| `weights.py` | safetensors Range 요청으로 실제 모델 가중치의 행렬 몇 개만 받아 캐시. 이름 해시로 design/holdout 분리 |
| `judge.py` | **독립 심판.** 코덱을 별도 프로세스로 격리 실행해 실제 blob 길이와 `P(x)=P'(x)` 오차를 재고 int8 과 비교 |
| `_worker.py` | encode/decode 를 각각 따로 돌리는 자식 프로세스 |
| `search.py` | 자가개선 루프. orchestrator 런의 최종 노드 verifier 를 judge 로 **갈아끼운다** |
| `codecs/int8.py` | 기준선. 채널별 대칭 int8 (max-abs 스케일) |
| `codecs/fp16.py` | 상한 기준선. 16 bits, 오차 ~0 |
| `codecs/ternary_b158.py` | BitNet b1.58 3진 + 5진 패킹. 1.73 bits, 오차 0.78 |
| `codecs/int8_clip.py` | 첫 개선안. MSE 최적 클리핑 + fp16 스케일 |

## 코덱 계약

```python
def encode(W: np.ndarray) -> bytes      # W 는 2차원 float32
def decode(blob: bytes) -> np.ndarray   # 같은 모양의 float32
```

`decode` 는 blob 말고 아무것도 받지 않는다. shape·스케일 등 복원에 필요한 모든 것이
blob 안에 있어야 한다. 표준 라이브러리 + numpy 만.

## 두 축

- **압축력** `bits/weight = 8 * len(blob) / W.size` — 코덱의 주장이 아니라 실제 바이트 수
- **복원력** `||W@X - W'@X|| / ||W@X||` — 가중치 오차가 아니라 **행렬곱 출력**의 오차.
  레이어를 프로그램 `P(x) = W@x` 로 보면 이것이 `P(x) ≈ P'(x)` 검사다

한 축만 이기는 것은 통과가 아니다. 3진은 압축력을 4.7배 이기고 복원력에서 31배 진다.
fp16 은 복원력을 이기고 압축력에서 2배 진다.

## 심판이 막는 것 / 못 막는 것

**막는다** (실측으로 확인, `tests/test_compression_judge.py`)

| 부정행위 | 어떻게 막히나 |
|---|---|
| 원본을 모듈 전역에 숨기기 | encode/decode 가 **다른 프로세스**라 전역이 사라진다 |
| blob 에 원본 경로만 담기 | decode 전에 원본 `.npy` 를 **지운다** |
| 임시 디렉토리에 원본 은닉 | encode 전후 파일 스냅샷 비교로 잡는다 |
| 실행마다 다른 결과 | 두 번 encode 해서 blob 이 같아야 한다 |
| decode 가 모양을 잃음 | 원본 shape 과 비교한다 |
| 비트 수 속이기 | 실제 blob 길이로만 잰다 (원본 그대로 담으면 32 bits) |
| 설계한 행렬로 채점 | holdout 셋은 설계 과정이 보지 못한다 |

**못 막는다** — 코덱이 `/tmp` 밖 절대경로에 원본을 숨기는 것. 진짜 격리는 컨테이너/
네임스페이스가 필요하다. 여기서 막는 것은 "무심코 새는" 경로와 "그럴듯하게 속이는" 경로다.

## 쓰는 법

```bash
# 1. 실제 가중치를 받는다 (네트워크가 되는 곳에서 한 번)
python3 compression/weights.py fetch                      # 기본 Qwen/Qwen2.5-0.5B
python3 compression/weights.py fetch --repo <repo> --file model.safetensors

# 네트워크가 없으면 배관 시험용 합성 (실제 성능이 아니고 결과에 표시된다)
python3 compression/weights.py synthetic

# 2. 코덱 하나 채점
python3 compression/judge.py --codec compression/codecs/int8_clip.py
python3 compression/judge.py --codec <내_코덱.py> --json

# 3. 자가개선 루프 (GEMINI_API_KEY 필요)
python3 compression/search.py --status        # 현재 챔피언 점수
python3 compression/search.py --rounds 5

# 4. 심판 자신의 회귀 검사
python3 tests/test_compression_judge.py
```

## 합성 데이터로는 답이 안 나온다

합성 가우시안으로 채점하면 "가우시안을 잘 압축하는 코덱"이 나온다. 실제 LLM 가중치는
채널마다 스케일이 다르고 소수의 outlier 가 채널의 해상도를 잡아먹는다 — int8 per-channel 이
표준이 된 이유가 그 구조다.

실측: 처음 만든 합성 가중치는 행별 `max/std` 가 3.2 였고, 그 데이터에서는 MSE 최적 클리핑이
**단 한 채널도** 고르지 않았다(전부 비율 1.0 = 기존 max-abs). outlier 를 행마다 넣어
`max/std` 를 8.7 로 올리자 그때부터 클리핑이 의미를 갖기 시작했다. 실제 가중치의 분포는
그보다 더 극단적이다. `judge` 는 합성으로 돌면 결과에 `⚠ 합성 데이터`를 찍는다.

## 지금 상태

합성 데이터 기준 (실제 가중치를 받으면 숫자가 달라진다):

| 코덱 | bits/weight | 압축 | 함수오차 |
|---|---|---|---|
| fp16 | 16.00 | 2.0x | 0.00021 |
| int8 (기준선) | 8.13 | 3.9x | 0.02518 |
| int8_clip | 8.06 | 4.0x | 0.02517 |
| ternary_b158 | 1.73 | 18.5x | 0.77821 |

`int8_clip` 이 두 축을 이기지만 차이가 5번째 자리다 — 클리핑이 합성 데이터에서 거의 일을
안 하기 때문이고, 이득은 대부분 fp16 스케일에서 나온다. 실제 가중치에서 다시 재야 한다.

## 다음

- 실제 가중치 캐시(VM 에서 `weights.py fetch`)
- `search.py --rounds N` 을 systemd 서비스로 (matrix-search 와 같은 방식)
- 코덱이 노리면 좋을 방향: 블록 단위 스케일, 벡터 양자화/코드북, 잔차 2단계, outlier 분리
  저장(희소 + 저비트 본체)
