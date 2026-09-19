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
