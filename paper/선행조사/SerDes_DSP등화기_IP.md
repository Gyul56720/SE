# SerDes DSP 등화기 IP -- 선행조사

조사일 2026-09-19. **코드보다 먼저 커밋한다** (G024).
이 문서를 사용자가 보고 나서 짓는다. 다섯 번 이걸 안 해서 졌다.

## 조사 조건 -- 무엇을 실제로 볼 수 있었나

이전 조사(`투기적언롤DFE.md`, 2026-09-18)는 **전부 차단된 상태**에서 쓰였고
`[출처:기억]` 이라고 정직하게 적혀 있었다. 이번에는 다르다.

    curl 직접 접근    arxiv · semanticscholar · dblp · ieee · scholar · mathworks
                      -> **전부 000**
    WebFetch          arxiv.org · mathworks.com -> **EGRESS_BLOCKED**
    WebSearch         **된다.** 제목 · URL · 요약 조각을 받는다
    git clone         **된다.** 저장소는 통째로 받아서 읽었다

그래서 확인수준이 셋으로 갈린다. **표마다 표시한다.**

  · `[출처:전문]` -- 실제로 받아서 읽은 것 (클론한 저장소)
  · `[출처:조각]` -- 검색 요약만 본 것. 논문 본문을 안 봤다
  · `[출처:목록]` -- 제목만 본 것

## 1. 가장 큰 위협 -- MATLAB 이 이미 한다

| 무엇 | 확인 | 우리와 겹치는 곳 |
|---|---|---|
| **SerDes Toolbox + HDL Coder**: 100G dual-summing-node DFE PAM4 수신기의 **적응 엔진을 합성 가능한 RTL 로 생성** | `[출처:조각]` | **정면으로 겹친다.** "DFE 를 RTL 로 만든다" 는 계획은 이 한 줄에 죽는다 |
| SerDes Toolbox 블록 라이브러리: CTLE · FFE · DFE · CDR, 적응 알고리즘 시뮬레이션 | `[출처:조각]` | 시스템 모델 전체를 덮는다 |
| Architectural 112G PAM4 **ADC-Based** SerDes Model (예제) | `[출처:조각]` | 우리가 가려던 구조 그대로 예제로 있다 |
| 생성 RTL 이 반영하는 것: PAM4 임계값 복원 · DFE 탭 가중치 조정 · 클럭 위상 민감도 | `[출처:조각]` | 고정소수점 변환까지 자동이다 |

**이것을 모르고 짓기 시작했으면 여섯 번째 패배였다.**

### 그런데 이것이 끝이 아닌 이유

    확인된 것   적응 엔진(adaptation engine)의 RTL 생성
    확인 안 된 것  데이터패스 전체 · 병렬화(sub-rate) · 투기적 언롤 · 타이밍 클로저

MathWorks 문서가 일관되게 부르는 이름은 **"adaptation engine"** 이다.
적응 엔진은 탭 가중치를 **갱신하는** 낮은 속도의 블록이고, 심볼마다 도는
**데이터패스**와 다르다. 56 GBd 에서 병목은 데이터패스지 적응 엔진이 아니다
(아래 3절의 우리 실측). **다만 이것은 내 읽기이고, 문서 전문을 못 봤다.**
`mathworks.com` 이 EGRESS_BLOCKED 다. **확인 전에는 빈틈이라고 주장하지 않는다.**

### 라이선스 의존성 -- 확인 실패

SerDes Toolbox 가 Fixed-Point Designer · HDL Coder 를 **필수로 요구하는지 확인 못 했다.**
검색이 요구사항 페이지를 찾았지만 내용을 안 준다. **사용자가 확인해야 하는 자리다** --
HDL Coder 가 없으면 위 위협의 절반은 해당되지 않는다.

## 2. 공개 구현은 어디까지 와 있나 -- 직접 받아서 셌다

| 무엇 | 확인 | 실제 내용 |
|---|---|---|
| **SparcLab/OpenSERDES** (GitHub) | **`[출처:전문]`** 클론해서 읽음 | 아래 |
| OpenSerDes, Kumar K · Chatterjee · Sen, **DATE 2021**, arXiv:2105.13256 | `[출처:조각]` | 위 저장소의 논문. sky130 전디지털 SerDes. 초록이 FFE/TX · DFE/RX 를 "논의한다" 고 나오지만 **본문을 못 봤다** |

**클론해서 센 것 (이것은 실측이다):**

    OpenSERDES 블록        Serializer · DeSerializer · DFF · NAND · Inverter_Based_Tx
                           · Resistive_FB_inverter · OverSampling_CDR
                           · Receiver_Bypassing_CDR
    진짜 RTL               **556줄**  (serialiser 249 + deserialiser 307)
    나머지 205,294줄       전부 `.lvs.v` 넷리스트 · GDS · SPICE
    **등화기**             **없다.** FFE 도 DFE 도 CTLE 도 파일이 없다

    기술: Skywater OpenPDK 130nm · 도구: OpenLane, Cadence Virtuoso

**공개된 sky130 SerDes 에 DSP 등화기가 없다.** 이것이 이번 조사의 두 번째 발견이다.
다만 **GitHub 전체를 훑은 것이 아니다** -- 아래 6절에 못 본 곳을 적는다.

## 3. 투기적/언롤 DFE -- 선행연구가 두텁다 (이전 조사 확인수준 상향)

이전 문서가 `[출처:기억]` 으로 적었던 것을 이제 `[출처:목록]` 으로 올린다.
제목이 실재함을 확인했다. **본문은 여전히 하나도 못 봤다.**

| 논문 (제목만 확인) | 확인 |
|---|---|
| 25 Gb/s 5.99 pJ/bit SerDes RX, CTLE + **quarter-rate adaptive loop-unrolling 5-tap DFE**, 28 nm | `[출처:목록]` |
| **100 Gb/s 1.1 pJ/b PAM-4 RX, Dual-Mode 1-Tap PAM-4 / 3-Tap NRZ Speculative DFE**, 14 nm FinFET, ISSCC | `[출처:목록]` |
| 52 Gb/s ADC-Based PAM-4 RX, **Partially Unrolled DFE**, 65 nm | `[출처:목록]` |
| 60 Gb/s PAM4 Wireline RX, 2-Tap Direct DFE, JSSC 2020 (Caltech) | `[출처:목록]` |
| 112 Gb/s PAM4 **ADC-Based** SerDes RX, Resonant AFE, Long-Reach (16-tap FFE + 1-tap DFE, 64-way TI ADC, MM-CDR) | `[출처:조각]` |
| **Feedforward Nonlinear Equalizer** for Short-to-Medium-Reach Wireline, arXiv:2606.08313 (2026) | `[출처:목록]` |

**결론은 이전 문서와 같고, 더 단단해졌다: 투기적 언롤 DFE 는 논문 주제가 아니다.**
1990년대부터 표준 구조이고 지금도 매년 나온다. 우리는 **IP 로 간다.**

### 이 저장소가 이미 잰 것 (이것은 우리 실측이다)

    afe.dfe1탭예산(56e9)    고리 31.0 ps  vs  1 UI 17.86 ps   여유 **-13.14 ps**
    1탭 언롤(먹스 3 ps)     26.0 ps       vs  17.86 ps        -> 38.5 GBd 한계
    래치+배선+준비만        23 ps > 17.86 ps
                            -> **언롤만으로는 56 GBd 에 절대 못 닿는다.**
                               sub-rate 병렬화가 **필수**다
    sky130 FO4 = 48 ps      ngspice 실측 -> 최대 약 1 GHz

**이 수가 우리 위치를 정한다.** 아날로그 56 GBd 는 sky130 으로 불가능하다.
디지털 sub-rate 데이터패스는 가능하다.

## 4. 그래서 우리가 다른 점 -- 주장할 수 있는 것만 적는다

| | 주장 | 근거 |
|---|---|---|
| O | **열린 도구만으로 도는 DSP 등화기 IP 체인.** MATLAB 계열 라이선스 없이 Python + Verilator + yosys + sky130 | 이 컨테이너에서 전부 도는 것을 오늘 확인 |
| O | **공개 sky130 SerDes 에 없는 블록**을 채운다 (OpenSERDES 에 등화기 없음) | 2절, 클론 실측 |
| O | **고정소수점 규칙을 재서 문서화**한다 -- 자동 변환이 숨기는 것 | 저장소 실측 2건: 되먹임 레지스터 초기값(103/200 불일치), wrap vs saturate |
| △ | 적응 엔진이 아니라 **데이터패스**를 다룬다 | MathWorks 문서 전문을 못 봐서 **확인 전이다** |
| X | 알고리즘 신규성 | 없다. 3절이 그렇게 말한다 |
| X | 56 GBd 실리콘 | 못 한다. sky130 FO4 48 ps |

**X 를 지우지 않는다.** 과장하지 않는 것이 이 저장소의 규율이다.

## 5. 규모 -- 어디까지 갈 것인가

기준선을 세어 정한다. 추측이 아니다.

    AMD Vitis solver  (Cholesky+QRF+SVD+utils)   4파일   3,458줄
    AMD Vitis security (AES+SHA+types+utils)     4파일   1,970줄
    Xilinx FINN                                 16파일   6,544줄
    (참고) 가장 큰 단일 파일 slidingwindow.h              2,096줄

    우리가 이미 가진 것
      LDPC 체인 (골든->고정소수점->Verilog->DPI-C->파이프라인)      766줄 + 검사 691줄
      SerDes 자산 afe.py · eqrtl.py · pam.py                      1,638줄

**목표: 납품물 3,000~5,000줄 + 검사 1,000~1,500줄.**

근거: Vitis security(AES+SHA) 가 1,970줄로 **두 개의 완성된 코어**다. 우리는
등화기 하나를 데이터패스+적응+생성기+테스트벤치까지 하므로 그 1.5~2.5배가 맞다.
FINN 의 6,544줄은 **16개 블록의 구성 키트**라 우리 규모가 아니다.

    ~500줄    장난감. 포트폴리오로 안 쳐준다
    ~1,000줄  단일 블록. "돌아간다" 수준
    3,000~5,000줄  **여기** -- 파라미터화 · 검증 · 납품 패키지가 들어간 IP
    10,000줄+  블록 여러 개의 라이브러리. 혼자 할 일이 아니다

## 6. 아직 못 지운 가능성 -- **"없다" 라고 말하지 않는다**

  1. **MathWorks 문서 전문을 하나도 못 봤다.** SerDes Toolbox 가 데이터패스 RTL 까지
     생성할 가능성이 남아 있다. 남으면 4절의 △ 가 X 가 되고 계획을 다시 짜야 한다.
     **사용자가 MATLAB 을 열어 확인할 수 있는 자리다. 그것이 다음 걸음이다.**
  2. **논문 본문을 하나도 못 봤다.** arXiv · IEEE 전부 차단. 3절은 제목과 요약뿐이다.
  3. **GitHub 를 체계적으로 훑지 않았다.** 검색 한 번과 저장소 하나를 받았을 뿐이다.
     `chipyard` · `BAG` · Berkeley 계열 아날로그 생성기는 **안 봤다**.
  4. **상용 IP 카탈로그를 안 봤다** (Synopsys · Cadence · Alphawave · Credo).
     팔리는 물건의 사양서를 봐야 "납품 패키지" 의 기준을 안다.
  5. **특허를 안 봤다.** 검색에 `US9077574B1` (Avago, FFE-DFE-DFFE 데이터패스) 가
     떴다. 데이터패스 쪽은 특허가 두터울 수 있다 -- **IP 를 팔 거면 봐야 한다.**

## 7. 찾아본 질의

    ADC-based DSP SerDes receiver 112G PAM4 digital equalizer FFE DFE architecture
    MATLAB SerDes Toolbox HDL Coder fixed-point FFE DFE CDR RTL generation wireline
    MATLAB SerDes Toolbox "dual-summing-node DFE" HDL Coder generated RTL limitations
    open source SerDes DSP equalizer RTL github FFE DFE Verilog wireline receiver
    speculative unrolled DFE loop unrolling half-rate 2024 2025 wireline receiver ISSCC JSSC
    OpenSerDes arXiv 2105.13256 process-portable all-digital serial link FFE DFE taps abstract
    SerDes Toolbox required products Simulink Fixed-Point Designer HDL Coder license dependencies

---

# 추가 조사 2026-09-19 (2차) -- 특허와 상용 카탈로그

6절의 못 본 곳 4·5번을 채웠다. **둘 다 계획을 바꾼다.**

## 8. 특허 -- 우리가 가려던 구조가 이미 특허다

| 특허 | 권리자 | 내용 | 확인 |
|---|---|---|---|
| **US 9,077,574 B1** (2015-07-07 등록) | Avago Technologies (현 Broadcom) | DSP SerDes 수신기, **FFE-DFE-DFFE 데이터패스**. 요약에 **"8-way parallel, 2-tap, fully unrolled DFE"** 와 **"8-way parallel FIR FFE"** 가 명시된다 | `[출처:조각]` |
| **US 8,787,439** (2014-07-22 등록) | (동 계열) | **DFFE**. "탭 수가 늘어도 하드웨어가 지수로 안 늘면서 DFE 를 병렬 구현" | `[출처:조각]` |
| **US 8,837,570** | (동 계열) | **Receiver with parallel decision feedback equalizers** | `[출처:목록]` |
| GB 2497144 A | | SERDES 수신기용 FFE | `[출처:목록]` |

### 왜 이것이 직격탄인가

3절의 우리 실측이 말한 결론은 이것이었다:

    래치+배선+준비만 23 ps > 1 UI 17.86 ps
    -> 언롤만으로는 56 GBd 에 못 닿는다.  **sub-rate 병렬화가 필수다**

그리고 US 9,077,574 의 요약에 있는 것이 정확히 **"8-way parallel + fully unrolled
DFE"** 다. **물리가 강요하는 해답이 하나뿐이라 우리가 거기로 갔고, 2013년에 이미
거기 가 있었다.**

### 그러나 -- 청구항을 안 봤다

**특허의 범위는 요약이 아니라 청구항이 정한다.** 나는 요약과 검색 조각만 봤다.
`image-ppubs.uspto.gov` 링크가 검색에 떴지만 **본문을 안 받았다.**

  · 청구항이 좁으면(특정 탭 수 · 특정 DFFE 조합) 우리가 비껴갈 수 있다
  · 청구항이 넓으면 데이터패스 쪽은 포기해야 한다
  · **출원 2013년 근처면 존속기간은 2033년 전후다.** 아직 살아 있다

**연구·학습·비상업 구현은 특허와 무관하다.** 문제가 되는 것은 **파는 것**이다.
사용자의 목표가 취업 포트폴리오면 이 특허는 **막지 않는다.** IP 를 팔 거면 막는다.

## 9. 상용 SerDes IP 는 어떻게 팔리나 -- 그리고 여기서 길이 갈린다

| 벤더 | 물건 | 확인 |
|---|---|---|
| Cadence | 112G-ULR / 112G-VSR PAM4 SerDes PHY, 1G~116Gbps | `[출처:조각]` |
| Synopsys | Multi-Protocol 112G PHY IP (PCIe 6.0 · 400G/800G Ethernet · CXL · JESD204C …) | `[출처:조각]` |
| **Alphawave** | 112G/224G SerDes. **"hardened PMA layer and a soft PCS layer deliverable"** | `[출처:조각]` |
| Credo | 112G PAM4 SerDes IP on **TSMC N3 / N7 / N6** | `[출처:조각]` |

### 구조적 발견 -- PHY 는 두 쪽으로 팔린다

    PHY = PCS  +  PMA(+PMD)

    PMA/PMD   ADC · AFE · CDR · 직렬화 · 비트 타이밍
              -> **하드 매크로.**  TSMC N3/N7 같은 선단 공정에 박혀 나온다
              -> 우리가 접근 불가.  sky130 FO4 48 ps 가 그것을 말한다

    PCS       64b/66b 인코딩 · 프레임 구획 · deskew · **gearbox** · **RS-FEC**
              · 레인 정렬 · fault 전달
              -> **소프트 IP.  RTL 로 납품된다**
              -> **공정 무관.  우리가 할 수 있다**

**Alphawave 가 "hardened PMA + soft PCS" 라고 명시적으로 나눠 판다.** 이것이 이번
조사에서 가장 값있는 한 줄이다.

## 10. 그래서 길이 셋으로 갈렸다

| | 길 | 특허 | 공정 | 우리 자산 | 판정 |
|---|---|---|---|---|---|
| A | **DSP 등화기 데이터패스** (FFE/DFE, sub-rate 병렬 + 언롤) | **US 9,077,574 직격** | 디지털이라 무관 | `afe.py` `eqrtl.py` `specdfe.py` 1,771줄 | 포트폴리오면 OK, **팔면 막힘** |
| B | **PCS / FEC 계층** (RS-FEC KP4 · gearbox · 64b/66b · 레인 정렬) | **미조사** | 무관 | `fec.py` `pam.py` `comply.py` 607줄 | **상용 납품 형태와 일치.** 유망 |
| C | 아날로그 AFE/ADC/CDR | | **선단 공정 필수** | 없음 | **불가** |

### B 를 새로 주목하는 이유

  1. **상용 납품 경계와 정확히 일치한다** -- "soft PCS layer deliverable" 이 팔리는 물건이다
  2. **특허 지뢰가 데이터패스보다 얕을 가능성** -- PCS 는 IEEE 802.3 **표준**이다.
     표준 기술은 보통 FRAND 이거나 특허가 만료됐다. **다만 이것은 추정이고, 8절처럼
     조사해야 한다 -- 아직 안 했다**
  3. **우리가 이미 KP4 를 잰다** -- `fec.py` 가 RS(544,514) 문턱을 계산한다.
     다만 **부호기/복호기 구현은 없다.** 계산만 한다. 거기가 지을 자리다
  4. **LDPC 체인에서 배운 것이 그대로 옮겨간다** -- 골든 -> 고정소수점 -> Verilog
     -> DPI-C -> 파이프라인 모델. GF(2^10) RS 도 같은 뼈대다

## 11. 갱신된 "못 지운 가능성"

  1. **MathWorks 문서 전문** -- 여전히 못 봄. **사용자가 확인 중**
  2. **논문 본문** -- 여전히 하나도 못 봄
  3. **GitHub 체계적 훑기** -- 여전히 안 함
  4. ~~상용 IP 카탈로그~~ -> **9절에서 봄** (요약 수준)
  5. ~~특허~~ -> **8절에서 봄. 그러나 청구항을 안 읽었다** -- 범위를 모른다
  6. **새로 생김: PCS/FEC 쪽 특허를 전혀 안 봤다.** B 를 고르면 8절을 그쪽에
     다시 해야 한다
  7. **새로 생김: 상용 PCS IP 의 사양서를 안 봤다.** 무엇을 납품해야 "IP" 인지
     기준을 아직 모른다
