# 행렬 역변환 없는 MMSE 검출기 IP -- 선행조사 (진행 중)

파이프라인(사용자 지시): 통신 회로 IP 중 병목을 찾고 -> 기존 알고리즘을 적용 ->
MATLAB 황금모델 -> HLS 코드 -> 시뮬레이션. 작고 사소해도 좋고, 어려운 회로가 아니어도 좋다.
추가: **알고리즘의 회로적 구성이 아직 안 이루어진 경우도 좋다.**

조사일 2026-09-18. **모든 인용이 검색 조각 수준이다.** 전문 미확인(egress 차단, 우회 안 함).

## 병목 -- 문헌이 그대로 적은 것

massive MIMO 의 MMSE/ZF 검출은 K x K 채널 상관행렬 역변환이 필요하고 O(K^3) 이다.

  "ZF precoding in massive MIMO systems suffers from high implementation complexity of
   O(K^3) owing to the inversion of a K x K channel correlation matrix"      `[출처:조각]`
  "linear MMSE detection has been shown to achieve near-optimal performance but suffers
   from excessively high complexity due to the large-scale matrix inversion"  `[출처:조각]`

## 가장 가까운 선행연구 -- 기존 알고리즘과 기존 회로

- **반복법으로 O(M^2)** -- Neumann series(NSE) · Newton iteration · **Gauss-Seidel** ·
  SOR · Jacobi · Richardson · conjugate gradient · OCD `[출처:조각]`
- **비교 결과가 이미 문헌에 있다**: GS 가 NSE 보다 효율적이고 역변환 자체가 없다.
  CG 와 OCD 가 복잡도 최저에 성능 수용 가능. -> **우리가 고를 필요가 없다** `[출처:조각]`
- **하드웨어 기준선(숫자가 있다)** `[출처:조각]`
  · Virtex-7, 128 BS 안테나 x 8 사용자, GS 기반 검출기 **732 Mb/s**, MMSE 근접 오류율
  · 상관 채널용 수정 NSE + tridiagonal 근사 **630 Mb/s**
  · Cornell VIP "Large-Scale MIMO Detection for 3GPP LTE" (JSTSP 2014)
- **NSE 수렴 가속** -- Joint Newton iteration + Neumann series (Math. Probl. Eng. 2016) ·
  Joint weighted NSE + GS soft-output · GS + NSE 결합 precoding (IEEE 2025) `[출처:조각]`

## 회로가 아직 (거의) 없는 자리 -- 분야가 스스로 적은 구멍

Deep unfolding (반복법에 학습 가능한 스텝 크기를 붙임) 서베이:

  "Hardware implementation complexity is **typically not considered** in the literature on
   deep unfolding, with only a few exceptions presenting FPGA and ASIC implementation
   results. It remains **largely unclear how the additional trainable parameters** required
   by unfolded algorithms **affect the hardware implementation complexity and achieved
   throughput**."                                                             `[출처:조각]`
  (arXiv:1906.05774 서베이 / arXiv:2502.05952 종합 리뷰 계열)

**그런데 반례가 있다 -- "최초" 라고 말하면 거짓이다.**
  · arXiv:2501.14861 "A Deep-Unfolding-Optimized Coordinate-Descent Data-Detector ASIC for
    mmWave Massive MIMO" -- **22 nm FD-SOI 로 실제 제작하고 측정**했다 `[출처:조각]`
  · arXiv:1906.03814 Learned Conjugate Gradient Descent Network (시뮬레이션)

-> 안전하게 말할 수 있는 것은 **"드물다"** 와 **"서베이가 미지라고 적었다"** 까지다.

## 우리가 그것과 다른 점

- 층 1(안전): GS 검출기 IP 를 HLS 로. 문헌 기준선(732 Mb/s)과 견준다. 새로울 것 없음
- 층 2(질문): **워드길이 x 반복 횟수** 격자. 반복법 논문은 보통 반복만 쓸고,
  워드길이 논문은 보통 반복을 고정한다 -- **이 인상은 아직 확인 안 된 것이다**
- 층 3: 학습 파라미터(deep unfolding)를 붙였을 때 하드웨어 비용 -- 서베이가 미지라 한 칸

## 찾아본 질의

- massive MIMO detection matrix inversion bottleneck FPGA Neumann conjugate gradient Gauss-Seidel
- RIS reconfigurable intelligent surface channel estimation overhead OMP hardware 6G
- deep unfolding MIMO detection network FPGA hardware implementation gap simulation only
- RIS phase shift configuration real-time hardware FPGA implementation research gap 6G

## 아직 못 지운 가능성 -- 다음 조사 순서

1. **(1순위) 워드길이 x 반복 격자를 이미 잰 문헌이 있는가.** 있으면 층 2가 죽는다.
   반복법 하드웨어 논문들이 정밀도 쓸기를 같이 했을 가능성이 높다 -- 확인해야 한다.
2. **deep unfolding 하드웨어 구현 목록을 제대로 세지 않았다.** "드물다" 도 근거가 약하다.
   서베이 한 편의 문장에 기대고 있다.
3. **RIS 갈래를 덜 팠다.** RIS 채널추정 오버헤드(소자 수에 비례하는 파일럿)는 문헌이
   "open problem" 이라 적었고, OMP 가 표준 해법이다. 다만 OMP 는 동적 제어흐름 때문에
   HLS 로 짓기가 GS 보다 훨씬 까다롭다 -- 그래서 2순위로 둔다.
4. **기준선 숫자의 조건을 모른다.** 732 Mb/s 가 어떤 클럭·정밀도·반복 횟수인지
   전문에서 확인해야 견줄 수 있다.
