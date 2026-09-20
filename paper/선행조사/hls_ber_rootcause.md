# HLS 통신 PHY 고정소수점 BER 열화 자동 원인추적 -- 선행조사

조사일 2026-09-18. **모든 인용은 검색 조각(snippet) 수준이다.** nature.com · eecg.utoronto.ca
둘 다 egress 차단이라 전문을 못 봤다(우회하지 않았다). 아래 판단은 그 한계 위의 판단이다.

## 가장 가까운 선행연구

### [1] 제안된 워크플로 자체 -- 이미 SCI 저널에 있다
- "Towards the transformation of MATLAB models into FPGA-Based hardware accelerators",
  *Scientific Reports* 16:5027 (2026), doi:10.1038/s41598-026-36033-z. `[출처:조각]`
  조각이 말하는 것: **layer-wise, verification-oriented methodology**. "At each stage of the
  MATLAB–C++–FPGA workflow, golden output based verification is performed by comparing layer
  activations from a HLS-based C++ model and the hardware implementation against reference
  outputs obtained in MATLAB." 층별 MAE < 1.5e-3.
  -> **제안의 그림(MATLAB golden → HLS C++ → FPGA, 단계별 대조로 열화 위치 찾기)과 같다.**
  다른 점은 대상이 신경망 층이고 지표가 MAE 라는 것뿐이다.

### [2] HLS 를 층 넘어 되짚는 디버거 -- 성숙했다
- Hestia: An Efficient Cross-Level Debugger for High-Level Synthesis, **MICRO 2024**,
  doi:10.1109/MICRO61859.2024.00062, 아티팩트 github.com/pku-liang/hestia-artifact `[출처:조각]`
  "equivalent mapping across different levels, Hestia facilitates bug identification and
  **localization**, providing breakpoints and stepping at multiple granularities."
- J. Goeders, S. Wilton, "Signal-Tracing Techniques for In-System FPGA Debugging of HLS
  Circuits", *IEEE TCAD* 2016, doi:10.1109/TCAD.2016.2565204 -- 소스 변수 19배 관측 `[출처:조각]`
- "Effective FPGA debug for high-level synthesis generated circuits" (Goeders·Wilton) `[출처:조각]`
- "Debugging in the brave new world of reconfigurable hardware", **ASPLOS 2022**,
  doi:10.1145/3503222.3507701 `[출처:조각]`
- "Bringing source-level debugging frameworks to hardware generators", **DAC 2022**,
  doi:10.1145/3489517.3530603 `[출처:조각]`
  -> **"FPGA 증거를 HLS 소스로 되짚어 버그를 국소화한다" 는 이미 한 분야다.**

### [3] "어느 연산·어느 비트폭이 정확도를 깎았나" -- 20년 된 분야
- D. Lee, G. Constantinides 외, MiniBit: "Accuracy-Guaranteed Bit-Width Optimization",
  *IEEE TCAD* 2006 -- 신호별 range/precision 해석, 해석적 오차모델 `[출처:조각]`
- "Optimum Wordlength Search Using Sensitivity Information", *EURASIP JASP* 2006,
  doi:10.1155/ASP/2006/92849 -- **신호별 민감도 = 원인 기여도 순위** `[출처:조각]`
- Winandy 외, "Automated Fixed-Point Precision Optimization for FPGA Synthesis", 2025 --
  "systematically propagates numerical errors through computations to infer variable-specific
  fixed-point formats that guarantee user-specified accuracy" `[출처:조각]`
- "Wordlength optimization with complexity-and-distortion measure and its application to
  **broadband wireless demodulator** design" -- 통신 수신기에 이미 적용됨 `[출처:조각]`
- "Word-Length Aware DSP Hardware Design Flow Based on High-Level Synthesis",
  *J. Signal Process. Syst.* (Springer) `[출처:조각]`

### [4] 소프트웨어 쪽 정밀도 원인추적 -- 도구가 다 있다
- Precimonious, **SC 2013** -- delta debugging 으로 변수별 정밀도 탐색 `[출처:조각]`
- Blame Analysis, **ICSE 2016** -- shadow execution 으로 둔감한 변수를 탐색공간에서 제거 `[출처:조각]`
- FpDebug (Valgrind) -- 고정밀 병행 실행 + slicing 으로 **오차의 전파를 추적** `[출처:조각]`
- CHEF-FP, arXiv:2304.06441 `[출처:조각]`

### [5] 상용 도구가 이미 판다 -- 이게 제일 아프다
- MathWorks **Fixed-Point Designer + HDL Coder** `[출처:조각]`
  · 넘침이 난 값을 **코드 리포트에서 빨갛게** 표시한다 -- 줄 단위 국소화
  · NumericTypeScope 히스토그램: 변수별 in-range / out-of-range / **below precision**
  · "Log inputs and outputs for comparison plots": 출력마다 float 대 fixed 와 **그 차이** 도시
  · simulation range + derived(static) range 로 타입 제안
  -> 제안서의 "자동 추적" 중 상당 부분이 **이미 제품 기능**이다. 심사자가 첫 줄에 물을 것이다.

### [6] 내가 탈출구로 쓰려던 것도 점유돼 있다
- Yang 외, "Pre-FEC and Post-FEC BER as Criteria for Optimizing Wireline Transceivers",
  **ISCAS 2021** (Toronto) `[출처:조각]`
  조각: "in some cases the pre-FEC and post-FEC BER optima coincide, particularly with error
  bursts. **DFE error propagation can have significant impact on post-FEC BER.**"
  -> "MSE 말고 post-FEC BER 을 기준으로 삼자" 는 착상은 이미 있다. 다만 저들이 고른 것은
  **송수신기 설정**이고 **HLS 고정소수점 귀속**은 아닌 것으로 보인다(조각 수준 판단).

## 우리가 그것과 다른 점

정직하게: **제안된 형태 그대로는 다른 점이 없다.** [1]이 워크플로를, [2]가 국소화를,
[3][4]가 비트폭 귀속을, [5]가 제품으로 이미 한다.

남는 틈은 하나뿐이고 얇다.

> **[3][4][5]의 귀속은 전부 MSE/MAE/SNR 을 오차 지표로 쓴다. 통신 PHY 에서 정작 중요한 것은
> post-FEC BER 이고, 둘은 같은 순위를 주지 않는다.**

이게 빈말이 아닌 이유는 우리가 이미 정확히 계산해 뒀다: **pre-FEC BER 을 고정한 채로도
post-FEC BER 이 1.7e-14 부터 2.262e-4 까지 열 자리 넘게 벌어진다.** 오직 오류가 코드워드
안에서 뭉치느냐(clustering)에만 달려 있고, KP4 RS(544,514) 에서 버스트 길이 B>=16 심볼이면
**부호화 이득이 정확히 0** 이 된다. 이건 모형이 아니라 산술이다(t=15 꼬리합).

MAE 가 같은 두 구현이 post-FEC 에서 열 자리 차이가 날 수 있다는 뜻이다. **포화(saturation)와
넘침은 오류를 뭉치게 만들고, 반올림 잡음은 흩뿌린다** -- MAE 는 이 둘을 구별하지 못한다.

그래서 반증 가능한 주장은 이렇게 된다:

> **주장.** 고정소수점 HLS PHY 에서 연산별 기여도를 MSE 로 매긴 순위와 post-FEC BER 로 매긴
> 순위는 어긋난다. 어긋나는 비율은 오류 뭉침을 만드는 결함(포화·넘침·클리핑)에서 높고
> 반올림 결함에서 낮다.
>
> **무효화 조건.** 주입한 결함이 전부 반올림형이거나, 동작점이 FEC 문턱에서 멀면 두 순위가
> 일치해 주장이 깨진다. 그러면 결과는 "MSE 로 충분하다" 는 **부정 결과**이고, 그대로 적는다.

## 찾아본 질의

- source-level debugging high-level synthesis FPGA root cause localization Goeders Wilton
- MATLAB Fixed-Point Designer float to fixed point mismatch localization overflow logging HDL Coder
- word-length optimization bit-width sensitivity analysis communication systems BER constraint FPGA Constantinides
- automated fault localization high-level synthesis fixed-point quantization error attribution FPGA 2024 2025
- Hestia cross-level debugger high-level synthesis MICRO 2024
- "BER degradation" fixed-point FPGA golden reference MATLAB comparison methodology PHY debugging root cause
- Precimonious FPDebug automated precision tuning root cause floating point error localization tools
- post-FEC BER aware wordlength optimization fixed-point quantization error clustering burst LDPC Reed-Solomon
- fault injection ground truth evaluation debugging tool localization accuracy precision recall hardware HLS mutation

## 아직 못 지운 가능성

1. **전문을 하나도 못 봤다.** nature.com 과 eecg.utoronto.ca 가 egress 차단이다. [1]이 정말
   통신이 아니라 신경망인지, [6]이 정말 고정소수점을 안 다루는지는 **조각으로 판단한 것**이다.
   이 둘의 전문 확인이 이 주제의 생사를 가른다 -- 사용자님이 학교 망에서 봐 주셔야 한다.
2. **광통신(coherent) 쪽을 얕게 팠다.** arXiv:2605.17521 "FPGA-Based Experimental Analysis of
   Fixed-Point Precision Impact on SOP Estimation in Coherent Communications Receivers" 가
   두 번 걸렸는데 못 열었다. 제목만으로도 가깝다.
3. **DSP/통신 학회(ICASSP · SiPS · DATE · ASAP)를 안 훑었다.** wordlength 논문의 본거지다.
4. **특허를 안 봤다.** Xilinx "Circuit for and method of determining error spacing in an input
   signal"(US10644844) 가 오류 간격 측정으로 걸렸다 -- 오류 뭉침 계측은 상용 IP 가 있을 수 있다.
5. **LDPC 양자화 문헌.** "adaptive quantization post-processing eliminates BER floors" 계열이
   "양자화가 post-FEC 를 어떻게 망치나" 를 이미 다뤘을 수 있다.
