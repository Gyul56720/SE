# 선행조사 -- Attention Softmax 하드웨어 가속기 (AI-HW co-design, 2026-09-25)

**방침**: 짓기 전에 조사한다. **읽은 수준**: 전부 검색 요약 `[조각]` / 서지 `[목록]`.
전문 미열람 (arXiv·IEICE 망 제약).

---

## 왜 이 주제인가 (LIG · 신호처리+AI 접점)

목표: **신호처리(HW)+AI 접점 = AI-HW co-design 직무, 취업 포트폴리오, 이미 있는 기술로
실행력으로 이긴다.** LIG 는 HW(FPGA·Verilog·신호처리)와 AI(국방 자동협업·표적탐지·무인체계)
를 **둘 다** 하고, 2026 상반기 공채에 AI 분야가 정식으로 있다.

산업부가 **K-온디바이스 AI반도체에 8,002억** 투입, 국산 AI칩 10종 개발 지원 [조각,
2026-06]. **엣지 AI 가속기가 지금 국가가 미는 자리다.**

## 왜 CNN 이 아니라 Attention 인가

- **CNN FPGA 가속기는 학부 수준**(MAC 배열). Attention 은 **현재 진행형 난제.**
- 급소가 하나로 모인다: **Softmax.** "지수함수 native 지원이 없어 트랜스포머 softmax 가
  NPU 배치의 결정적 병목" [조각, arXiv 2609.01212 서베이].
- 2025~2026 논문이 쏟아진다 -- 최전선이다(신규성으론 못 이기나 목표가 실행력이라 무관).

---

## 이론 -- Softmax 를 하드웨어에 올리는 문제

### 수치 안정 softmax (max-subtraction)
$$ \text{softmax}(x_i) = \frac{e^{x_i - \max_j x_j}}{\sum_k e^{x_k - \max_j x_j}} $$
최댓값을 빼야 지수가 오버플로하지 않는다(SafeSoftmax) [조각]. 하드웨어에서 max·감산·지수·
합·나눗셈이 다 필요하고, **지수와 나눗셈이 비싸다.**

### Online softmax
최댓값과 정규화합을 **한 번의 순회로 함께** 갱신 -> 메모리 트래픽 절감 [조각]. FlashAttention
계열의 핵심.

### 지수함수 근사 (급소의 핵심)
- **base-2 치환 (Softermax)**: $e^x = 2^{x\log_2 e}$. 밑을 2로 바꾸면 정수부는 **시프트**,
  소수부만 근사. 덧셈·시프트로 지수를 낸다 [조각, arXiv 2103.09301]
- **I-BERT i-softmax**: max-감산 + **2차 다항식**으로 exp 근사 + 비트시프트. 전체 정수
  연산(INT8, 중간 INT32) [조각, arXiv 2101.01321]
- **PWL(구간 선형)**: TEA-S 가 파이프라인 지연을 2N -> N 으로 [조각]
- **LUT**: IntAttention 이 **32-엔트리 LUT** 로 exp, 소형 SoC 에서 **BRAM 없이** PWL LUT
  [조각]. 분포 인지 softmax 는 128-bin LUT, O(1) [조각]
- **Padé/체비셰프**: PEANO-ViT 가 division-free 로 softmax·layernorm 근사 [조각]

### 인접 비선형 (같이 다뤄야 완제품)
- **GELU**: erf 를 2차 다항식(i-GELU)/체비셰프 tanh 근사 [조각]
- **LayerNorm/RMSNorm**: 역제곱근을 **뉴턴-랩슨/정수 제곱근 반복** [조각, I-BERT i-LayerNorm]

**핵심**: 이 문제가 AIM 의 "비선형(곱·거듭제곱)을 하드웨어 꼴로 근사하고 자원을 재는" 것과
**같은 종류**다. 근사 차수 <-> LUT/DSP <-> 정확도 손실이 **재서 보이는 수**다.

---

## FPGA 자원 (근거 있음)

| 구현 | 대상 | 자원 |
|---|---|---|
| DRViT | ViT-tiny, ImageNet | Alveo U250: **1,341K LUT · 11,508 DSP** (대형) [조각] |
| HeatViT (토큰 가지치기) | DeiT-tiny/small/base | **ZCU102** 에서 3.46~4.89배 가속, DSP +8~11% [조각] |
| Microscaling ViT | DeiT 계열 | LUT 엔트리 16%+ 절감 [조각] |
| ME-ViT | ViT | 단일적재 메모리효율 [목록] |

**함의**: 대형 ViT 전체는 U250 급(수천 DSP)이 필요 -- 우리 예산(중급 FPGA) 밖.
그러나 **HeatViT 가 ZCU102(중급)에서 DeiT-tiny 를 돌린다.** 즉 **작은 ViT + 가지치기 +
근사**로 중급 보드에 들어간다. 그리고 우리 자리는 **전체 ViT 가 아니라 softmax/attention
유닛**부터다.

앞서 이 저장소가 잰 것: **FFT 나비 = DSP48E1 4개**(복소곱). MAC/softmax 도 정수곱이라
DSP 로 간다 -- **자원 자리가 유리함이 이미 확인됨.**

---

## 우리가 다를 수 있는 점 (아직 주장 아님 -- 목표는 실행력)

정확도·신규성으로 안 겨룬다. **완제품성·자원·측정·co-design 방법론**으로 겨룬다.

1. **Softmax 근사의 정확도-자원 파레토를 게이트로 실측.** LUT 엔트리 수·PWL 구간 수·
   비트폭을 흔들며 (근사오차, LUT/DSP, 지연)을 **재서** 곡선으로 낸다. 남들은 한 점만 낸다.
2. **하드웨어 인지 co-design 루프.** 자원 예산(LUT/DSP/BRAM)을 양자화·근사 선택에 되먹인다.
   "자원부터 잰다" 는 AIM 방법론을 attention 에 적용.
3. **완제품 인도.** softmax 유닛 -> attention 블록 -> RTL·검증(황금 대조+변이)·합성·DFT·
   배치를 다섯 직무 흐름으로. 파이썬 노트북이 아니라 사인오프까지.

## 아직 못 지운 가능성 (크다 -- 붐비는 밭이다)

1. **매우 붐빈다.** 2025~2026 에 softmax 하드웨어 논문 수십 편(Softermax·I-BERT·TEA-S·
   PEANO-ViT·QUARK·SoftmAP...). **신규성은 없다.** 목표가 취업 포트폴리오라 무관하나,
   "새것" 이라고 말하지 않는다 -- "최전선 문제를 손으로 구현했다" 가 무기다.
2. **전문 미열람.** arXiv·IEICE 가 망에서 막혀 초록만 봤다. 정확한 근사식·자원 수는 재야 안다.
3. **국내 방산 트랜스포머 HW 를 못 찾았다.** 검색이 "국방 표적인식 관련 국내 FPGA 어텐션
   가속기 구체 정보 없음" 이라고 답했다. 없다는 게 아니라 이 검색으로 못 봤다.
4. **학습 파이프라인(QAT)이 필요하다.** SW 쪽 -- ViT 학습·양자화 인프라. GPU 시간·데이터셋.
5. **입력(표적) 미정.** IR/SAR/EO. 데이터셋 가용성으로 정해야 한다.

---

## 찾아본 질의
- `transformer attention FPGA accelerator softmax bottleneck quantization 2026 edge resource`
- `vision transformer FPGA softmax nonlinear quantization LUT DSP dynamic range attention 2025 2026`
- `softmax hardware approximation online max-subtraction exponential LUT PWL base-2 shift FPGA fixed-point`
- `layernorm GELU hardware approximation FPGA nonlinear I-BERT integer-only quantization`
- `vision transformer edge FPGA resource LUT DSP BRAM deit tiny ImageNet 2026 SoC`
- `국내 트랜스포머 어텐션 FPGA softmax 국방 온디바이스 AI 반도체 2026`

---

## 2026 최전선 -- 추가 조사 (2026-09-25, 전부 `[조각]`/`[목록]`, 전문 미열람)

사용자 요청: "최신기술 2026 기준으로." 위 조사(2025~2026 초 기준)에 2026 최신을 얹는다.

### 갈래 A -- softmax 를 **더 잘 근사**한다 (기존 노선 유지)
- **FlashAttention-2**: online-softmax 를 타일 단위로. 여전히 exp/합/나눗셈이 급소.
  엣지 FPGA 이식이 2026 에도 활발 [조각].
- **TeLLMe v2**: **삼진(ternary) LLM** prefill+decode 를 FPGA 에 올림. 곱셈을 **테이블
  룩업**으로 치환. FPGA'26 (ISFPGA) [조각, arXiv 2510.15926].
- **COBRA**: 이진(binary) 트랜스포머 가속 [조각].
- **INT4 양자화 (2026)**: 4-bit 8B 모델이 정확도 95%+ 유지 -- 엣지 실전 가능 근거 [조각].
- **KV 캐시 가속기**: HiKV [2607.22389] · MeshKV [2609.19207] · VEDA · LUT-LLM
  [2511.06174] · EdgeLLM. **디코드 단계의 병목은 softmax 가 아니라 KV 캐시 대역폭**이라는
  2026 의 관점 이동 [조각].

### 갈래 B -- softmax 를 **아예 버린다** (2026 의 큰 물결) ★
- **Mamba / SSM (State Space Model)**: **선형 어텐션**. softmax·QK^T 행렬을 없애고 상태
  재귀로 대체. 복잡도 **O(n²) -> O(n)**, 처리량 ~5배. FastMamba 가 FPGA 구현 [조각,
  arXiv 2505.18975].
- **DROPS / 선형 어텐션 계열**: softmax 를 커널 근사로 제거 [조각].
- 함의: "softmax 가 병목" 이라는 **우리 논지의 전제 자체를 2026 의 한 갈래가 흔든다.**
  softmax 를 최적화하는 대신 **없애는** 아키텍처가 뜨고 있다.

### 이 갈래들이 포트폴리오 논지에 주는 뜻 -- **사용자 결정 필요**

| | 갈래 A (softmax 근사) | 갈래 B (SSM/선형) |
|---|---|---|
| 논지 | "softmax 병목을 HW 로 푼다" | "softmax 를 구조로 없앤 최신 아키텍처를 HW 로" |
| 성숙도 | 검증된 밭, 자료 많음 | 2026 최전선, 자료 적음, 구현 어려움 |
| 실행 위험 | 낮음 (레퍼런스 풍부) | 높음 (재귀·스캔의 HW 병렬화가 새 급소) |
| "중고신입" 어필 | "실전 급소를 손으로 구현" | "가장 최신을 따라감" |
| 방산 적합 | 표적인식 ViT 에 직결 | 시계열/센서 스트림(레이더·SIGINT)에 SSM 이 자연스러움 |

**정직한 판단**: 갈래 B(Mamba/SSM)는 "2026 최신"에 가장 부합하고 **방산의 스트리밍 센서
신호(레이더 펄스열·SIGINT 시퀀스)에 O(n) 선형 재귀가 오히려 더 맞는다.** 다만 HW 구현
난도가 높다(재귀의 병렬 스캔). 갈래 A 는 안전하고 자료가 많다. **둘을 배타로 볼 필요는 없다**
-- softmax 유닛을 먼저 완제품으로 만들고(A, 실행력 증명), 그 위에서 "그런데 2026 은 이걸
없애는 방향(B)"을 분석 章으로 붙이면 **깊이까지 보인다.**

### 2026 추가 질의
- `FlashAttention hardware accelerator FPGA 2026 KV cache LLM edge inference softmax mamba state space model linear attention`
- `2026 edge LLM small language model FPGA accelerator on-device transformer inference latest technique quantization state-of-the-art`

---

## 결론 -- 범위를 좁혀 시작

**Attention 의 softmax 하드웨어 근사**를 핵심으로, **정확도-자원 파레토를 재는 co-design**
으로 겨룬다. 전체 ViT 가 아니라 **softmax 유닛 하나 -> attention 블록**부터. 붐비는 밭이라
신규성은 없으나 목표(취업·실행력)에 맞다. System 2단계에서 **softmax 유닛의 exp 근사가
LUT 로 가는지, 자원이 얼마인지**부터 잰다 -- AIM·채널화에서 한 그대로.

**2026 을 얹은 뒤 남는 갈림길(사용자 결정)**: 갈래 A(softmax 근사, 안전)로 완제품을 짓고
갈래 B(SSM/선형, 최신·방산 스트림 적합)를 분석으로 붙이는 것을 권한다. B 를 본 노선으로
삼으려면 실행 난도가 오르는 것을 감수해야 한다.
