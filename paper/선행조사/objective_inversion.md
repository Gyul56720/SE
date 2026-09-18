# 목적함수 역전 -- 선행조사 (진행 중)

주제: FEC 보호 수신기의 HLS 설계공간에서 FPGA 자원 · ASIC 면적 · post-FEC BER 이
서로 다른 최적해를 주는가. 제안서: `제안_목적함수역전.html`

조사일 2026-09-18. **모든 인용이 검색 조각 수준이다.** nature · ACM · arXiv · IEEE 전문이
이 환경에서 egress 차단이라 한 편도 못 열었다. 우회하지 않았다.

## 가장 가까운 선행연구

- **워드길이 최적화 (목적함수 = 정확도/MSE)** -- MiniBit: Lee·Constantinides 외,
  "Accuracy-Guaranteed Bit-Width Optimization", *IEEE TCAD* 2006 `[출처:조각]` ·
  "Optimum Wordlength Search Using Sensitivity Information", *EURASIP JASP* 2006,
  doi:10.1155/ASP/2006/92849 `[출처:조각]` ·
  Winandy 외, "Automated Fixed-Point Precision Optimization for FPGA Synthesis", 2025 `[출처:조각]`
- **LDPC 복호기 양자화 대 BER -- 표준 관행이다** `[출처:조각]`
  3비트 약 0.25 dB · 4비트 0.1 dB 미만 · 5비트면 부동소수점과 동등 · BP 는 5~6비트가 통상.
  "Design of LDPC Decoders for Low Error Rate Performance" (Berkeley) 등.
  -> **복호기 내부 양자화는 우리 대상이 아니다.** 우리는 복호기 앞단이다.
- **DFE 버스트 -> FEC 열화 -- 알려져 있다** `[출처:조각]`
  "100+ Gb/s Ethernet FEC Analysis", *Signal Integrity Journal* 2019 -- RS(544,514) 는
  오류의 성질에 매우 민감하고, 원시 BER 2e-4 라도 오류가 무작위면 무오류로 돈다.
  "The DFE must be viewed as a source of burst errors."
  특허 US8555132 "Modification of error statistics behind equalizer to improve inter-working
  with different FEC codes" · arXiv:2306.07873 (IM/DD 의 DFE 버스트 대응 연판정)
- **post-FEC 를 최적화 기준으로** -- Yang 외, "Pre-FEC and Post-FEC BER as Criteria for
  Optimizing Wireline Transceivers", ISCAS 2021 `[출처:조각]`. 대상은 송수신기 설정.
- **HLS 대 HDL Coder 대 RTL 비교** -- "Comparison of Compilers for Generating a Hardware
  Description Based on an Imperative Program: HDL Coder and Vitis HLS" (2025) `[출처:조각]` ·
  arXiv:1806.10672 · arXiv:2305.13351 (Wi-Fi 트랜시버) · arXiv:2509.08067
- **자동 DSE** -- HLSPilot(ICCAD'24) · iDSE(arXiv:2505.22086) · ChatHLS(arXiv:2507.00642) ·
  HLS-Seek(arXiv:2605.13536) · TimelyHLS(arXiv:2507.17962) `[출처:조각]`

## 우리가 그것과 다른 점

부품은 전부 남이 했다. 다른 것은 **조합** 하나다 -- 세 축(FPGA 자원 · ASIC 면적 ·
post-FEC BER)을 **같은 설계공간 위에** 동시에 올려놓고 순위가 어긋나는지 잰다.
이 연구는 새 알고리즘을 주장하지 않는다. 주장하는 것은 측정된 사실이고, 그 사실이
자동 DSE 의 목적함수 설계에 주는 함의다.

우리가 직접 계산해 가진 것(인용이 아니다): pre-FEC BER 고정 시 post-FEC 가
1.7e-14 ~ 2.262e-4 로 열 자리 벌어지고, KP4 RS(544,514) 에서 버스트 B>=16 심볼이면
부호화 이득이 정확히 0 이다. t=15 꼬리합에서 나온 산술이다.

## 찾아본 질의

- quantization bit width optimization LDPC decoder BER fixed-point standard practice
- fixed-point saturation overflow equalizer error bursts clustering degrades FEC receiver DSP
- post-FEC BER aware wordlength optimization quantization error clustering burst LDPC RS
- word-length optimization bit-width sensitivity analysis communication BER constraint Constantinides
- "HDL Coder" versus "Vivado HLS" comparison FPGA resource utilization Fmax quality of results
- LLM high-level synthesis 2025 2026 ChatHLS ForgeHLS agentic HLS verification

## 아직 못 지운 가능성

1. **전문을 한 편도 못 봤다.** 위 다섯 줄은 각각 전문 확인이 필요하다. 특히 Yang(ISCAS 2021)이
   고정소수점까지 다루면 H2 가 크게 약해진다.
2. **ICASSP · SiPS · DATE · ASAP 을 안 훑었다.** 워드길이 논문의 본거지다.
3. **광통신(coherent) 쪽.** arXiv:2605.17521 (coherent 수신기 고정소수점 정밀도 영향) 못 열었다.
4. **FPGA 대 ASIC 자원 상관** 자체를 다룬 문헌을 아직 안 찾았다. H1 이 이미 알려진 것일 수 있다 --
   **다음 조사에서 이걸 제일 먼저 판다.**
5. **다목적 DSE(Pareto) 문헌.** HLS DSE 는 이미 다목적(면적-지연)을 다룬다. "축을 더 넣는다" 가
   그 틀 안에서 자명한 확장으로 읽힐 위험이 있다.
