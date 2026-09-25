# FPGA 기반 실시간 마이크로 도플러 대드론 분류기: 자원-제약 관점의 엣지 신호처리 설계

**A Resource-Constrained FPGA Architecture for Real-Time Micro-Doppler Counter-UAS Classification**

*제안서 (Research & Development Proposal) · IEEE 논문 형식*
*Nowon Silicon Works · 2026-09-25*

> **인용 정직성 고지**: 이 제안서의 참고문헌은 **2026-09-25 웹 검색으로 식별**한 것이며,
> 표시가 없는 한 **전문(全文)을 읽지 않았다**. 검색 요약만 본 것은 각주에 `[조각]` 으로
> 표시한다. 실측 수치(§V, §VI)는 이 저장소에서 실제로 계산·합성한 것이고, 그 방법을 본문에
> 밝힌다. 아직 재지 않은 것은 "미측정"으로 명시한다.

---

## Abstract

Counter-unmanned-aerial-system (C-UAS) sensing must distinguish small drones from
biological clutter such as birds under low signal-to-noise ratio (SNR) and low radar
cross-section (RCS) conditions. Micro-Doppler analysis of rotor blades is the established
discriminant, but reported systems emphasize *classification accuracy* — a problem now
largely solved by convolutional neural networks (F1 ≈ 0.997 for binary detection) — while
leaving the *real-time, edge-resource* question underexplored. This proposal targets that
gap. We present a fixed-point short-time Fourier transform (STFT) spectrogram pipeline and
a lightweight classifier, sized to fit on a mid-range Zynq-class FPGA (≤ 100 만원 budget),
and we ground every architectural claim in measured logic-synthesis resource. Our first
measurement shows the 256-point FFT butterfly maps to **4 DSP48E1 slices** per unit — the
complex multiply is DSP-friendly, in contrast to Galois-field arithmetic that our prior
work found to explode into pure look-up-table (LUT) logic. Consequently the FFT is *not*
the bottleneck (156× timing headroom at 100 MHz), which reorients the design effort toward
the classifier and the drone-versus-bird false-alarm problem. We propose a hybrid
feature-plus-shallow-network discriminant and a hardware-in-the-loop verification flow in
which the golden reference is produced by an independent numerical model, never by the RTL
itself.

**Keywords** — counter-UAS, micro-Doppler, STFT, FPGA, edge signal processing,
drone classification, fixed-point, resource estimation.

---

## I. 서론 (Introduction)

### A. 배경과 동기 (Motivation)

저비용 소형 무인기(sUAS)의 대량·군집 운용이 2026년 방공의 지배적 위협으로 부상했다.
미 육군은 **100대 규모 스웜**에 대해 AI·전자전·레이더를 결합한 대응을 시험하고 있으며[1],
전자공격(EW)이 RF 명령링크·위성항법 의존을 노리는 저비용 1차 방어층으로 자리 잡았다[1].
국내에서는 방위사업청이 **2026년까지 244억 원 규모의 「한국형 재머」 개발**을 추진하고
(LIG넥스원 참여), 업계는 2026년을 K-안티드론 수출 원년으로 전망한다[2].

C-UAS 는 **탐지(detect) → 식별(classify) → 무력화(defeat)** 세 계층으로 구성된다.
본 제안은 **식별 계층의 실시간 엣지 신호처리**에 집중한다. 무력화(재밍·레이저)는
국내 대기업이 이미 체계개발 중이며[2], 재밍 송신은 능동 공격 장비이므로 본 연구의
범위에서 명시적으로 제외한다. 본 연구의 산출물은 **아군 방공 자산이 위협을 식별하기
위한 수동/능동 센서 신호처리**로 한정된다.

### B. 문제의 급소 (The Core Difficulty)

소형 드론은 **저 RCS·저속**이라 실시간 신뢰 분류가 어렵다[3]. 특히 X-대역에서 10 cm²
RCS 의 새가 소형 드론과 유사한 레이더 신호를 만들어 **오경보(false alarm)** 를 유발한다[4].
회전 날개가 만드는 **마이크로 도플러(micro-Doppler)** 측대역이 드론과 새를 가르는 가장
강한 판별 특징이며, 단시간 푸리에 변환(STFT) 스펙트로그램이 이를 가장 잘 드러낸다[5].

### C. 기여 (Contribution)

기존 연구가 정확도(F1 ≈ 0.997[6])에 집중한 반면, 본 제안의 기여는 **자원·지연·엣지**에 있다.

1. **자원 측정 기반 설계.** FFT·STFT·분류기의 LUT/DSP/BRAM 을 합성으로 실측하고,
   중급 FPGA 한 장에 들어가는 최소 구성을 제시한다(§VI).
2. **DSP 친화성의 정량적 근거.** 복소곱이 DSP48 슬라이스로 매핑됨을 실측으로 보인다 —
   이는 갈루아체 산술이 순수 LUT 로 폭발하던 우리 선행 결과[본 저장소]와 대조된다.
3. **드론-대-새 오경보를 겨냥한 경량 판별기.** 정확도를 최우선하는 대형 CNN 대신,
   물리 특징(측대역 간격·HERM 선폭·스펙트럼 대칭성) + 얕은 분류기의 자원-정확도 절충을
   제시한다.
4. **검증에서 정답의 독립성.** 황금 기준을 독립 수치 모델이 생성하며 RTL 이 스스로
   정답을 만들지 않는다(§VII).

---

## II. 이론적 배경 (Theory and Physics)

### A. 도플러와 마이크로 도플러 (Doppler and Micro-Doppler)

반경 방향 속도 $v$ 로 이동하는 산란체의 도플러 편이는

$$ f_d = \frac{2v}{\lambda} = \frac{2 v f_c}{c} \tag{1} $$

여기서 $\lambda$ 는 파장, $f_c$ 는 반송 주파수, $c$ 는 광속이다. 회전하는 날개의 끝단
속도는

$$ v_{\text{tip}} = \omega r = 2\pi \frac{N_{\text{rpm}}}{60} r \tag{2} $$

이고, 날개 끝단의 **최대 마이크로 도플러** 편이는 식 (1)에 $v_{\text{tip}}$ 을 대입하여

$$ f_{\mu,\max} = \frac{2 v_{\text{tip}}}{\lambda}
   = \frac{4\pi r f_c}{60 c} N_{\text{rpm}}. \tag{3} $$

**본 저장소 실측 (`cuas/model/param.py`)**: X-대역 $f_c=10$ GHz ($\lambda = 30$ mm),
프로펠러 반경 $r = 0.12$ m, $N_{\text{rpm}} = 15{,}000$ 일 때
$v_{\text{tip}} = 188.5$ m/s, $f_{\mu,\max} = 12.6$ kHz. 대역별 값을 표 I 에 정리한다.

**표 I. 대역별 최대 마이크로 도플러 (r=0.12 m, 15,000 rpm, 계산값)**

| 대역 | $f_c$ | $\lambda$ | $f_{\mu,\max}$ |
|---|---|---|---|
| X | 10 GHz | 30.0 mm | 12.6 kHz |
| K | 24 GHz | 12.5 mm | 30.2 kHz |
| mmWave | 77 GHz | 3.9 mm | 96.8 kHz |

날개 회전은 반송파 주위에 **HERM(HElicopter Rotor Modulation) 선(line)** 이라 불리는
등간격 측대역을 만든다. 날개 수 $N_b$, 회전율 $f_{\text{rot}}$ 에 대해 측대역 간격은

$$ \Delta f = N_b \cdot f_{\text{rot}} \tag{4} $$

이며, 이 간격과 선폭·대칭성이 드론(강한 등간격 측대역)과 새(성기고 좁은 날갯짓 성분)를
가르는 물리적 근거다[5].

### B. 표본화 요건 (Sampling Requirement)

식 (3)의 최대 마이크로 도플러를 왜곡 없이 담으려면 나이퀴스트에 따라
$f_s > 2 f_{\mu,\max}$ 여야 한다. X-대역 12.6 kHz 에 대해 본 설계는 여유를 두어
$f_s = 40$ kHz 를 택한다.

### C. 단시간 푸리에 변환 (STFT)

이산 STFT 는

$$ X[m,k] = \sum_{n=0}^{N-1} x[n + mH]\, w[n]\, e^{-j 2\pi k n / N} \tag{5} $$

로 정의된다. $N$ 은 창 길이, $H$ 는 홉(hop), $w[n]$ 은 창 함수(본 설계는 Hann)이다.
**스펙트로그램**은 크기 제곱

$$ S[m,k] = \bigl| X[m,k] \bigr|^2 \tag{6} $$

이며, 시간-주파수 평면에서 마이크로 도플러 측대역이 수평 줄무늬로 나타난다.

**시간-주파수 절충(Gabor limit).** 창 길이 $T_w = N/f_s$ 가 길수록 주파수 분해능
$\Delta_f = f_s/N$ 이 좋아지지만 시간 분해능이 나빠진다. 날개 한 바퀴를 담는 최적
관측시간은 약 20 ms 로 보고되며[5], 창 길이 41 ms 급이 쓰인다[7]. 본 설계는
$N=256$, $H=64$, $f_s=40$ kHz 로 창 길이 6.4 ms, 분해능 156 Hz, **관측 20 ms 당 9 홉**을
얻는다(본 저장소 실측). 짧은 창을 여러 홉으로 겹쳐 시간 분해능을 확보하는 선택이다.

### D. 레이더 방정식과 검출 (Radar Equation, CFAR)

능동 레이더의 수신 전력은

$$ P_r = \frac{P_t\, G^2\, \lambda^2\, \sigma}{(4\pi)^3\, R^4} \tag{7} $$

로, 소형 드론의 작은 RCS $\sigma$ 와 $R^4$ 감쇠가 낮은 SNR 을 만든다[3]. 잡음·클러터
배경에서 일정 오경보율을 유지하려면 **CFAR(Constant False Alarm Rate)** 검출을 쓴다.
셀-평균 CFAR 의 적응 문턱은

$$ T = \alpha \cdot \frac{1}{M} \sum_{i=1}^{M} x_i, \qquad
   \alpha = M\!\left(P_{fa}^{-1/M} - 1\right) \tag{8} $$

이며, $M$ 은 참조셀 수, $P_{fa}$ 는 설계 오경보율이다. 본 시스템은 스펙트로그램 위에서
CFAR 로 측대역 후보를 뽑고 그 구조로 분류한다.

---

## III. 관련 연구와 한계 (Related Work and Limitations)

### A. 탐지·식별의 네 갈래

| 갈래 | 원리 | 성숙도 |
|---|---|---|
| RF 지문 | 드론↔조종기 전파 수동 감청 | **정확도 포화**: CNN F1 ≈ 0.997[6] |
| 마이크로 도플러 레이더 | 회전 날개 도플러 측대역 | 드론-대-새가 **열린 문제**[8] |
| 광학/영상 | 카메라 + 검출 | 별개 분야, 붐빔 |
| 음향 | 마이크 배열 | 근거리 한정 |

### B. 무엇이 이미 해결되었나

RF 지문 기반 분류는 2-클래스에서 F1 ≈ 0.997 에 이르렀고 오픈 드론 데이터베이스까지
공개되어 있다[6]. 마이크로 도플러 + 기계학습 역시 "우호적 조건에서" 드론-새 판별을
사실상 해결했다[8].

### C. 무엇이 남았나 — 본 제안의 자리

두 가지가 열려 있다.

1. **성능의 급락 조건.** 지상 클러터 속, 근접 편대 비행, 훈련 데이터 밖 프로펠러
   특성에서 성능이 급격히 나빠진다[8]. 기종 세분류는 10-클래스에서 정확도가
   46.8% 로 떨어진다[6].
2. **실시간 엣지 자원.** 대부분의 보고가 GPU/서버에서 정확도를 재며, **중급 FPGA
   한 장에 탐지→스펙트로그램→분류가 들어가는지**는 정량적으로 덜 다뤄졌다. 검색상
   RF FPGA 실시간 구현은 RFSoC 급 스펙트럼 분석 사례에 집중되어 있고[9][10],
   RFSoC(4x2 학술가 약 $2,499)는 본 예산을 초과한다.

**본 제안은 (2)에 답하고 (1)을 겨냥한다.** 정확도는 학계가 이겼으므로 정확도로 겨루지
않고, **자원·지연·엣지 실현성**과 **오경보 저감**으로 겨룬다.

### D. 한계의 정직한 명시

본 제안이 넘지 못하는 선을 미리 밝힌다.

- **레이더 하드웨어 부재.** 현 단계는 합성 도플러 신호로 검증한다. 실 드론 마이크로
  도플러와의 정합성은 미측정이다.
- **RF 지문 FPGA 구현 선행 미확정.** 이미 다수 존재할 수 있으나 전문 확인 미완(IEEE
  Xplore 접근 제약).
- **분류기 자원 미측정.** FFT 자원만 실측했고 분류기는 다음 단계다.

---

## IV. 시스템 구조 (System Architecture)

### A. 데이터흐름 (회로도 — 블록 수준)

```
   RF 프런트엔드 (SDR / 레이더 수신)
        │  IQ, fs = 40 kHz (복소, Q1.15)
        ▼
   ┌──────────────────────┐
   │ ① 이동 창 버퍼        │  듀얼포트 BRAM, N=256, 홉=64
   │   (sliding window)    │
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ ② Hann 창 곱          │  상수 계수 ROM × 256, DSP
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ ③ FFT-256 (radix-2)   │  ◀── 자원 급소. 실측 완료(§VI)
   │   나비 × 트위들 ROM   │      DSP48E1 4/나비
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ ④ |·|² → log          │  복소 크기제곱(DSP) + LUT 근사 log
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ ⑤ 스펙트로그램 프레임  │  256(주파수) × 9(시간) BRAM
   │   조립 + CFAR 문턱     │  식 (8)
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ ⑥ 특징 추출 + 분류기  │  측대역 간격·선폭·대칭성 → 얕은 분류기
   └──────────┬───────────┘
              ▼
        판정 {드론 / 새 / 잡음}  + 신뢰도
```

### B. 인터페이스

- **제어**: AXI4-Lite (파라미터·문턱·모드 레지스터)
- **데이터 입력**: AXI4-Stream (IQ)
- **결과 출력**: AXI4-Lite 레지스터 또는 인터럽트 (판정·신뢰도·타임스탬프)

이 표준 인터페이스가 있어야 **IP(지식재산)** 로서 상용 SoC 흐름에 통합된다.

---

## V. 알고리즘 (Algorithm)

### A. 전처리·STFT

```
입력: IQ 스트림 x[n], 파라미터 (N, H, w[])
반복 (홉 m 마다):
  1. 창 버퍼에 최근 N 표본 적재
  2. seg[n] = x[n + mH] * w[n]           # 식 (5) 내부
  3. X = FFT_N(seg)                        # radix-2 DIT
  4. S[m,k] = |X[k]|^2                     # 식 (6)
출력: 스펙트로그램 S[m,k]  (256 × 9 프레임)
```

### B. 특징 추출 (물리 기반)

대형 CNN 대신, 마이크로 도플러 물리에서 나온 저차원 특징을 우선한다:

1. **측대역 간격** $\Delta f$ — 식 (4). 자기상관 첨두로 추정.
2. **HERM 선폭** — 각 측대역의 반치폭. 날개 강성·수와 연관.
3. **스펙트럼 대칭성** — 상·하 측대역 에너지 비. 드론은 대칭, 새는 비대칭 경향.
4. **본체 도플러** — 중심 첨두 위치·이동.
5. **시간 변동성** — 홉 간 스펙트로그램 상관(정상성).

### C. 분류기 (자원-정확도 절충)

- **경량 경로(주력)**: 위 5특징 → 결정트리/소형 MLP. 수백 LUT 급, 지연 극소.
- **정밀 경로(선택)**: 256×9 스펙트로그램 → 양자화 소형 CNN(FINN/hls4ml 흐름). 자원↑.

두 경로의 자원·정확도를 실측 비교하는 것이 본 연구의 정량적 산출물이다.

### D. 드론-대-새 판별의 핵심

식 (4)의 등간격성 지표를 문턱화한다: 드론은 강한 주기적 측대역
($\Delta f = N_b f_{\text{rot}}$, 수백 Hz 등간격), 새는 성기고 낮은 날갯짓 주파수
(~10 Hz)와 약한 측대역을 보인다. **본 저장소 황금모델 실측**: 드론 신호는 312 Hz 부근
측대역 첨두, 새 신호는 0 Hz 부근 집중, 잡음은 스펙트럼 전역 분산(`cuas/model/golden.py`).

---

## VI. 하드웨어 설계와 자원 (Hardware Design and Resource)

### A. 고정소수 형식

Q1.15 (16-bit) 를 기준으로 한다. 복소곱 후 `>>> 15` 로 정규화한다(본 저장소
`cuas/rtl/fft256.v`). 스펙트로그램 정밀도가 분류에 충분한지는 미측정 — 검증 단계에서
황금 부동소수와의 오차를 잰다.

### B. FFT 나비 자원 — **실측**

256-점 radix-2 나비 하나를 Xilinx 7-시리즈(xc7)로 논리합성(yosys `synth_xilinx`)한 결과:

**표 II. FFT-256 나비 1개의 자원 (본 저장소 실측, yosys `synth_xilinx -family xc7`)**

| 자원 | 수 |
|---|---|
| DSP48E1 | **4** |
| LUT2 | 95 |
| CARRY4 | 24 |

**핵심 관찰**: 식 (5)의 복소곱 $W\cdot B$ 가 **DSP48 슬라이스로 매핑**된다. 이는
우리 선행 연구에서 GF($2^{128}$) 무캐리 곱이 DSP 를 쓰지 못하고 순수 LUT 로 폭발했던
것(S-box 하나 20,000–32,000 LUT)과 **정반대**다. 정수 곱과 체(field) 곱의 하드웨어
자리가 근본적으로 다르다.

### C. FFT-256 전체 예산과 보드 대조 — **실측 기반 산정**

**표 III. FFT-256 설계 대안과 자원**

| 설계 | DSP | 사이클/FFT |
|---|---|---|
| 완전 펼침(상한) | 4,096 | 1 |
| 나비 1개 재사용 | **4** | 1,024 |
| 단당 나비 1개(8단 파이프) | **32** | ~128 |

**표 IV. 예산 내 FPGA 보드와 적합성**

| 보드 | DSP | LUT | 재사용 | 파이프 |
|---|---|---|---|---|
| Zynq-7020 (Pynq-Z2) | 220 | 53,200 | O | O |
| ZU3EG (Ultra96) | 360 | 71,000 | O | O |
| ZU7EV (ZCU104) | 1,728 | 230,000 | O | O |

### D. 처리량 — **여유 확인**

홉마다 FFT 하나가 필요하므로 요구 처리량은 $f_s/H = 40{,}000/64 = 625$ FFT/s. 100 MHz
클록에서 FFT 하나에 160,000 사이클 여유가 있어, 나비 1개 재사용(1,024 사이클)도
**156배 여유**다. **결론: FFT 는 병목이 아니다.** 남는 DSP·처리량을 분류기에 배분한다.

### E. 설계 함의

AIM 가속기에서 "보드에 들어가나?" 가 물음이었던 것과 달리, 본 시스템은 FFT 단계가
넉넉히 들어간다. 따라서 설계 노력은 **분류기 자원**과 **오경보 저감**으로 이동한다.

---

## VII. 검증 계획 (Verification Plan)

이 저장소의 규율(**검사하지 않은 초록불이 검사한 빨간불보다 나쁘다**)을 따른다.

1. **정답의 독립성.** 황금 스펙트로그램을 독립 numpy 모델(`cuas/model/golden.py`)이
   생성한다. RTL 이 스스로 정답을 만들지 않는다.
2. **고정소수 오차 예산.** RTL Q1.15 스펙트로그램과 부동소수 황금값의 상대 오차를
   빈(bin)별로 재고, 분류 정확도에 미치는 영향을 재문턱화로 확인한다.
3. **자해(변이) 검사.** RTL 을 일부러 망가뜨려(트위들 오류·창 계수 오류·비트reversal
   오류) 검사가 실제로 빨개지는지 본다.
4. **회로 인도.** RTL·검증·합성·DFT·배치를 사내 다섯 직무 흐름(RTL/DV/SYN/DFT/PD)에
   넘겨 라이브러리 매핑된 면적·타이밍·스캔·결함수준을 받는다.

---

## VIII. 표준·산업 기준 (Standards and Industry Criteria)

- **인터페이스**: AMBA AXI4 / AXI4-Lite / AXI4-Stream (ARM) — IP 통합 표준.
- **하드웨어 설계보증**: 항공전자 전개 시 RTCA **DO-254**(Design Assurance for Airborne
  Electronic Hardware)를 목표 수준으로 삼는다. *본 제안은 DO-254 원문 미열람 — 목표
  수준·DAL 매핑은 후속 확인 필요.*
- **환경·EMI**: 방산 전개 시 **MIL-STD-461**(전자파 적합성) 및 **MIL-STD-810**(환경)
  대상. *구체 시험 항목 미확인.*
- **검증 방법론**: 기능검증에 UVM(IEEE 1800.2) 구조를, 커버리지 교환에 Accellera
  **UCIS 1.0** 을 지향. *현 흐름은 도구 제약으로 UVM 구조를 C++/SystemVerilog 로 대체.*

*표준 항목은 제도 근거로 제시하되, 각 규격 원문을 아직 읽지 않았음을 밝힌다. 실제 인증
계획 수립 시 원문 대조가 선행되어야 한다.*

---

## IX. 신기술 제시 (Proposed Novelty)

기존 연구가 **정확도**를 최적화 목표로 삼은 데 반해, 본 제안의 신규성은 목적함수를
**자원-정확도 파레토**로 바꾸는 데 있다.

1. **자원-우선 마이크로 도플러 파이프라인.** 정확도가 포화된 분야에서, 동일 정확도를
   유지하는 **최소 FPGA 자원 구성**을 실측으로 제시한다.
2. **물리 특징 + 얕은 분류기의 드론-대-새 판별.** 식 (4)의 등간격성을 명시적 특징으로
   써서, 대형 CNN 없이 오경보를 저감하고 자원을 절약한다. 이 경로의 자원-정확도를
   대형 CNN 경로와 정량 비교한다.
3. **측정 기반 설계 방법론의 이전.** 우리의 선행 검증-계량 관점(회로를 사내 다섯 직무에
   넘겨 라이브러리 매핑 수를 받는)을 신호처리 IP 에 적용한다.

*신규성 주장은 §III·§X 의 미확인 선행연구가 닫힌 뒤에만 확정한다. 현 단계는 "후보"다.*

---

## X. 한계와 위험 (Limitations and Risks)

| 항목 | 상태 | 대응 |
|---|---|---|
| 레이더 하드웨어 없음 | 합성 도플러만 | SDR/레이더 확보 시 실측. 그전까지 합성으로 배관·자원 |
| RF 지문 FPGA 선행 미확정 | IEEE 전문 접근 제약 | 마이크로 도플러로 차별화, 전문 확인 후 재조정 |
| 분류기 자원 미측정 | FFT 만 실측 | 다음 단계에서 경량/CNN 경로 실측 |
| 고정소수 정밀도 | 미측정 | 검증에서 오차 예산화 |
| 황금모델 물리 충실도 | 단순 합성 | 문헌 기반 HERM 모형으로 정교화 |
| 규격 원문 미열람 | DO-254·MIL-STD | 인증 계획 전 원문 대조 |

**부정 결과를 지우지 않는다**: 본 제안의 전신인 AIM 가속기는 (a) 전체 서명의 3% 비중,
(b) GF 곱이 DSP 미사용으로 자원 폭발이라는 이유로 FPGA 제품에 부적합함을 실측으로
확인하고 접었다. 본 주제는 그 실패에서 **"자원부터 잰다"** 는 교훈을 적용해 선정되었다.

---

## XI. 참고문헌 (References)

> 아래는 2026-09-25 웹 검색으로 식별한 문헌이다. `[조각]` 은 검색 요약만 확인했음을,
> 표시 없는 항목은 서지 정보만 확인했음을 뜻한다. **전문 확인은 후속 과제다.**

[1] U.S. Army XVIII Airborne Corps, "AI and electronic warfare against mass drone swarms,"
Army Recognition, 2026. [조각]

[2] "국내 안티드론 개발 현황 (LIG넥스원 소형무인기대응체계, 한국형 재머 244억 원)," 한국인터넷방송통신학회논문지 및 산업 보도, 2024–2026. [조각]

[3] "Real-time reliable classification difficulty under low RCS/low velocity," in
*A Survey on Detection, Classification, and Tracking of UAVs using Radar and Communications Systems*, arXiv:2402.05909, 2024. [조각]

[4] "Radar micro-Doppler signatures of drones and birds at K-band and W-band,"
*Scientific Reports*, vol. 8, art. 35880, 2018. [조각]

[5] "Adaptive STFT for UAV Micro-Doppler Signature Analysis," DTIC AD1116524; and
micro-Doppler dwell-time analysis (~20 ms blade cycle). [조각]

[6] "RF-based drone detection and identification using deep learning approaches: an
initiative towards a large open source drone database," *Future Generation Computer
Systems*, vol. 100, 2019 (F1 ≈ 0.997 binary; 46.8% at 10 classes). [조각]

[7] STFT window ~41 ms for spectrogram analysis (micro-Doppler literature). [조각]

[8] "Advance and Refinement: The Evolution of UAV Detection and Classification
Technologies," arXiv:2409.05985, 2024 (performance degradation under clutter, close
formation, out-of-distribution propellers). [조각]

[9] "Custom-Designed Signal Processing Application for RFSoC FPGA Platform,"
IEEE Conf., doc. 10721695 (ZU48DR, ADC+FFT in PL). [조각]

[10] "Wideband spectrum monitoring on Zynq-7000 (Welch method, real-time 96 MHz,
<1 ms/window, frequency-hopping detection)." [조각]

[11] Real Digital, "RFSoC 4x2 board," academic price $2,499 (예산 초과 근거). [조각]

[12] Accellera, "Unified Coverage Interoperability Standard (UCIS) 1.0," 2012.

[13] ARM, "AMBA AXI and ACE Protocol Specification" (AXI4/AXI4-Lite/AXI4-Stream).

[14] RTCA, "DO-254: Design Assurance Guidance for Airborne Electronic Hardware." *원문 미열람.*

---

*본 제안서의 실측 수치(표 I–IV)는 저장소 `cuas/` 에서 재현 가능하다:
`python3 cuas/model/param.py`, `python3 -m cuas.model.golden`,
`yosys -p "read_verilog -sv cuas/rtl/fft256.v; synth_xilinx -top fft256_bfly -family xc7; stat"`.*
