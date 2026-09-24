# 선행조사 -- KpqC 표준 알고리즘의 마스킹 하드웨어 (2026-09 기준)

**한 줄**: 한국 표준 양자내성암호(KpqC) 4종은 2025-01 에 확정됐고, **부채널 공격은 2025~2026 에
나왔는데 하드웨어 방어는 하나도 없다.** 그리고 제도가 그 방어를 요구한다.

**읽은 수준**: 전문을 읽은 것은 없다. `[출처:조각]` 검색 요약, `[출처:목록]` 제목만.
`mjos.fi` 는 **망에서 차단**되어 못 읽었다.

---

## 왜 지금인가 -- 시한이 걸려 있다

- **KpqC 최종 4종 확정 (2025-01)**: KEM **NTRU+ · SMAUG-T**, 전자서명 **AIMer · HAETAE**
  [출처:조각, pqcmp.kr / 바이라인네트워크 2026-02]
- **NTRU+ 는 2026년 방송통신표준 정보보호 분야 국가표준 선정을 목표로 표준 초안을 제출**하고
  표준위원회 심사 중 [출처:조각, 스마트투데이 2026-06]
- **2026년에 통신·금융·국방·교통·우주 5개 분야 시범전환 실증 추진.**
  2035년까지 국가 주요 정보통신 기반시설에 PQC 적용 [출처:조각, 보안뉴스/펜타시큐리티 2026]
- 국내 공공·방산은 **KCMVP** 검증필 암호모듈을 요구하고, KCMVP 는
  **KS X ISO/IEC 19790:2015 / 24759:2015** 기반이다. **AES·DES 는 검증 대상이 아니다**
  [출처:조각, KISA seed.kisa.or.kr]
- **ISO/IEC 17825 는 ISO/IEC 19790 부속서 F 에서 규범적으로 참조되는 "승인된 비침입 공격 완화
  시험 척도" 이며, 보안수준 3·4 에 적용된다.** 수준 3·4 는 SPA·DPA 를 포함한 비침입 물리공격을
  일정 수준으로 완화할 것을 요구하고, 17825 가 표본 수·시험 시간·합불 기준을 정한다
  [출처:조각, iso.org / Secure-IC]. 2016 판에 이어 **17825:2024** 개정판이 있다.

즉 **"국산 PQC 를 국방에 넣는다"는 일정이 이미 2026 에 있고, 그 모듈이 수준 3·4 를 받으려면
부채널 완화를 시험으로 통과해야 한다.**

---

## 가장 가까운 선행연구

### (1) KpqC 부채널 -- **공격은 이미 여러 편, 방어는 소프트웨어뿐**

- **SMAUG-SCA** (ACM AsiaCCS): SMAUG-T 에 대한 **최초의 전력 부채널 공격**. Random Forest,
  XGBoost, FCN 으로 시험 정확도 >94%, **10 트레이스 미만으로 비밀키 복구, 성공확률 >99.9%**
  [출처:조각, dl.acm.org/10.1145/3779208.3804885]
- **ICISC 2025**: *Side-Channel Leakage Assessment of SMAUG-T: Exploiting Hamming Weight
  Patterns in Polynomial-to-Message Conversion* [출처:조각, Springer]
- Bernstein, *Report on evaluation of KpqC Round-2 candidates* (2024-12-26): SMAUG-T 에
  상수시간이 아닌 부속 루틴이 있어 효율적 키복구가 가능하다는 주장 [출처:조각, cr.yp.to]
- *SMAUG(-T), Revisited: Timing-secure, More Compact, Less Failure* [출처:목록]
- eprint 2023/1437, *Performance and Implementation Security Analysis of KpqC* [출처:목록]
- **MPCitH(AIMer 계열)**: *Single Trace Side-Channel Attack on the MPC-in-the-Head
  Framework* (eprint 2024/1882, NIST 6차 PQC 표준화 학회 2025). MPCitH 구현은 부채널에
  취약하며 **값 하나만 새어도 프로토콜 보안이 깨진다** [출처:조각]. 방어는
  *SNI-in-the-head* (ACM CCS 2020) [출처:목록]
- **SMAUG-T 의 대응은 소프트웨어다**: single-write byte assembly, randomized bit-ordering,
  **1차 불리언 마스킹**, temporal hiding [출처:조각]

### (2) PQC 마스킹 **하드웨어** -- Kyber/Saber 밖으로 안 나갔다

> *"Kyber 와 Saber 외에는 완전 마스킹 하드웨어 구현이 발표된 PQC 기법이 없으며, 둘 다
> FPGA 를 대상으로 하고 1차 보안만 다룬다."*
> [출처:조각, *A Masked Pure-Hardware Implementation of Kyber*, NIST 4차 PQC 학회 **2022**]

**이 문장은 2022년 것이다.** 다만 2026 검색에서 나온 것도 전부 Kyber/ML-KEM 이었다:
- arXiv:2606.31681 *Exploring Side-Channel Protections in Hardware Implementations of
  PQC ML-KEM Verification* [출처:목록]
- arXiv:2407.02452 하드웨어 친화 셔플링 대응(Kyber), eprint 2024/1194 지역 마스킹 NTT
  하드웨어, arXiv:2508.03062 NTT 고장검출 [출처:목록]

### (3) 마스킹 하드웨어 **형식검증** -- 2026 에 가장 활발한 자리

- **PROLEAD** (TCHES): 강건 프로빙 적대자가 탐침하는 시뮬레이션 중간값의 통계적 독립을
  자동 분석. **전력모델이 필요 없고 게이트 수준 넷리스트 상태만 시뮬**한다. 전체 암호
  구현을 다룰 수 있고 **글리치와 전이의 결합 결함**까지 잡는다 [출처:조각]
- **SILVER** (CASA Bochum 2020): ROBDD 로 정확한 통계적 독립 검증. **거짓양성 없음**,
  대가는 확장성. glitch-extended · PINI 합성성 검증 [출처:조각]
- **COCO/CocoAlma · fullverif**: 전이 누출을 강건 프로빙 모델에서 다룸 [출처:조각]
- **Prover / ProverNG** (eprint 2024/1202, Springer): SILVER 의 ROBDD 를 변수축약·휴리스틱
  열거로 확장, SILVER 가 시간초과하는 S-box 도 검증 [출처:조각]
- **2026 PQC 전용 검증 논문들**:
  - arXiv:**2604.15249** *Structural Dependency Analysis for Masked NTT Hardware:
    Scalable Pre-Silicon Verification of Post-Quantum Cryptographic Accelerators*
  - arXiv:**2604.25878** *Prime-Field PINI: Machine-Checked Composition Theorems for
    Post-Quantum NTT Masking*
  - arXiv:**2603.18939** *Controller-Datapath Aware Verification of Masked Hardware
    Generated via High-Level Synthesis*
  - Zenodo *Decision-Grade Masking* (2026): 1차 AES S-box 의 강건 d-프로빙 보안에 대해
    **RTL·합성 넷리스트·PROLEAD 설정·Docker 까지 묶은 증거 사슬** [출처:조각]
  - 마스킹된 Ascon-p S-box 를 **COCO·PROLEAD·SILVER 세 독립 도구로** order-d 보안 증명
    [출처:조각]

### (4) 제도 쪽 비판

- eprint 2019/1013, *A Critical Analysis of ISO 17825* [출처:목록]
- Saarinen, *Applicability of ISO Standard Side-Channel Leakage Tests to PQC*
  -- **mjos.fi 가 망에서 차단되어 못 읽었다.** 제목상 이 주제의 핵심일 가능성이 크다

---

## 2판 (2026-09-24) -- 큰 칸 셋을 닫았다. 빈 자리가 훨씬 좁아졌다

### (닫힘) "Kyber/Saber 뿐" 은 **죽은 문장이다**

1판이 인용한 문장은 **2022년** 것이었다. 2023~2026 으로 좁혀 다시 보니 폭발적이다.

- **마스킹 ML-DSA 하드웨어**: eprint 2024/1817 *Improved ML-DSA Hardware Implementation
  With First Order Masking* [출처:목록]
- **ML-DSA + ML-KEM 통합 마스킹 하드웨어**: PeerJ CS *Two birds, one mask:
  side-channel-resistant unified hardware for ML-DSA and ML-KEM* [출처:조각]
- **마스킹 HQC**: eprint 2025/1344 *Side-Channel Sensitivity Analysis on HQC: Towards a
  Fully Masked Implementation*, *Masked Vector Sampling for HQC* (2025) [출처:조각]
- **eprint 2026/1265** *A Billion Hard CRYSTALS: Exploring Practical Aspects of Arithmetic
  Masking for PQC in Hardware* [출처:목록]
- **HADES (CHES 2025)**: 임의 차수 마스킹의 설계공간탐색을 **자동화**하는 프레임워크
  [출처:조각]. -- 1판의 못지운칸 8번(자동생성 도구)이 **현실이었다.**
  "손으로 마스킹한다" 는 기여가 크게 줄어든다.
- Reed-Solomon 부호 기반 마스킹의 ML-KEM 적용 (IACR CiC) [출처:목록]
- **PoSyn** (arXiv:2506.08252) *Secure Power Side-Channel Aware Synthesis* [출처:목록]

### (닫힘·중요) **1차 마스킹 하드웨어는 이미 깨지고 있다**

- *A side-channel attack on a masked hardware implementation of CRYSTALS-Kyber*,
  J. Cryptographic Engineering **2025**: **1차 마스킹 Kyber-512 FPGA 구현**에 대해
  해밍거리 누출 모형으로 **실용적 메시지 복구**. 복호화 중 **마스킹된 메시지 디코딩
  함수의 취약점**을 쓴다 [출처:조각]
- *Revisiting the Masking Strategy: A Side-Channel Attack on CRYSTALS-Kyber*,
  IEEE TIFS **2025** [출처:목록]

**그러니 "1차 마스킹 하드웨어를 만들었다" 는 2026 에 방어로서 불충분하다.**

### (닫힘) 국내 -- 이미 하는 연구실이 있다

- **DGIST PAC Lab**: KpqC 알고리즘의 소프트웨어 및 **하드웨어(PIM/FPGA) 효율적 구현**
  연구 중 [출처:조각, 연구실 홈페이지]. 다만 목록상 **"효율적 구현" 이지 마스킹이 아니다**
- **국민대 암호및보안공학연구실**: KpqC 선정 알고리즘의 **검증 방법론** [출처:조각]
- 정보보호학회논문지: NCC/MQ-Sign 키복구 부채널 분석(2024), MEDS 하드웨어 가속 부채널
  동향(KIPS 2024), NIST PQC Round 3 격자 부채널 대응 동향(2021) [출처:목록]
- 국내 리뷰가 적고 있다: **"KpqC 후보 알고리즘에 대한 부채널 공격 연구는 아직 초기 단계이고,
  대응기법 연구도 불충분하다"** [출처:조각]

### (**안 닫힘**) KCMVP 가 방산에 요구하는 보안수준

확인한 것: **소프트웨어·펌웨어는 최대 보안수준 2, 수준 3·4 는 하드웨어만 도달 가능**
[출처:조각]. 수준 1 은 "비밀이 아닌 업무자료 보호" 수준 [출처:조각]. 올해 국방·금융·우주 등
5개 핵심 산업으로 확대됐고 KSE 보안칩이 군용 무전기에 적용 [출처:조각].

**그러나 방산 모듈이 수준 3 이상을 요구한다는 직접 근거는 못 찾았다.**
수준 1·2 면 ISO 17825 부채널 시험이 안 걸리고, **이 주제의 제도 근거가 사라진다.**
이 칸은 여전히 빨강이다.

---

## 3판 -- 남은 자리를 다시 좁힌다: AIMer(MPCitH)

위를 겪고 나면 "SMAUG-T 에 마스킹을 붙인다" 는 **적용 연구**다. NIST 알고리즘 쪽 방법이
이미 있고 자동화 도구까지 있으므로, 2026 물결과 겨루면 약하다. 대신 한 칸이 남는다.

| | 있는가 |
|---|---|
| MPCitH **하드웨어** | **있다** -- TCHES 2024 *High-Performance Hardware Implementation of MPCitH and Picnic3*; *Efficient FPGA Implementations of LowMC and Picnic*(2019); *MPSpeed: Accelerating Mirath on FPGA*(eprint 2026/206) |
| MPCitH **마스킹** | **있다, 다만 소프트웨어** -- *Side-Channel Protections for Picnic Signatures*(2021), KKW 영지식 증명을 임의 차수로 마스킹, **ARM Cortex-M4 1차**, 오버헤드 1.8~5.5배 |
| **둘의 교집합(마스킹 MPCitH 하드웨어)** | **찾지 못했다** |
| AIMer 전용 | **찾지 못했다** |

왜 이 칸이 구조적으로 다른가:

1. **AIMer 에는 NTT 가 없다.** 2026 형식검증 물결(Prime-Field PINI, 마스킹 Barrett 축약,
   NTT 파이프라인 합성성, 구조적 의존성 분석)은 **전부 격자의 NTT·모듈러 산술**을 겨눈다.
   AIMer 는 GF(2^λ) 곱과 해시가 본체라 **그 정리들이 통째로 안 닿는다.**
   -- **이것은 내 추론이다. 재 보지 않았다.**
2. **MPCitH 는 값 하나만 새어도 프로토콜 보안이 깨진다** [출처:조각, eprint 2024/1882].
   마스킹 필요성이 구조적으로 강하다.
3. 마스킹 비용이 **해시 호출에 몰린다**(1.8~5.5배). 하드웨어에서 이 구조가 어떻게 되는지는
   소프트웨어 결과로 예측되지 않는다.

## 우리가 그것과 다른 점

1. **소프트웨어 1차 마스킹은 하드웨어로 그대로 옮겨지지 않는다.** 글리치와 전이 때문이다 --
   PROLEAD·SILVER·COCO 가 존재하는 이유가 정확히 그것이다. SMAUG-T 에는 소프트웨어 1차
   불리언 마스킹이 있지만, **그것이 하드웨어에서 1차 보안이라는 보장은 없다.**
2. **KpqC 알고리즘의 마스킹 하드웨어가 (찾은 범위에서) 하나도 없다.** 발표된 완전 마스킹
   하드웨어는 Kyber 와 Saber 뿐이다.
3. **공격은 나왔고 방어는 없다.** SMAUG-T 는 10 트레이스 미만으로 키가 털렸다.
4. **제도가 요구한다.** KCMVP 수준 3·4 → ISO 19790 부속서 F → ISO 17825 의 SPA/DPA 완화 시험.
5. **장비 없이 시작할 수 있다.** PROLEAD 는 넷리스트 시뮬만 쓴다 -- 부채널 측정 장비가
   없어도 1차 결과가 나온다. 이 저장소에 이미 yosys 합성·넷리스트·관문이 있다.

### 다만 아직 주장이 아닌 것

SMAUG-T 는 sparse secret 과 LWE/LWR 혼합 구조라 Kyber 의 마스킹 부품(특히 압축·비교와
산술↔불리언 변환)이 그대로 안 붙을 것으로 **추정**한다. **재 보지 않았다.** 이것이 사실이어야
"Kyber 마스킹을 옮기면 되는 것 아니냐" 에 답할 수 있다.

---

## 찾아본 질의

- `KCMVP 검증기준 부채널 분석 ISO/IEC 17825 비침입 공격 시험 암호모듈 보안수준 요구`
- `KpqC 양자내성암호 국가 표준 2026 HAETAE AIMer SMAUG-T NTRU+ 국가표준 선정 현황`
- `KpqC hardware implementation FPGA NTRU+ SMAUG-T HAETAE AIMer accelerator ASIC`
- `masked hardware formal verification PROLEAD SILVER COCO glitch robust probing security 2026 tool`
- `KpqC side-channel attack analysis SMAUG-T NTRU+ HAETAE AIMer power analysis masking countermeasure`
- `ISO/IEC 19790 Annex F non-invasive attack mitigation ISO/IEC 17825 security level 3 4 requirement`
- `SMAUG-T masking first-order countermeasure protected implementation sparse secret LWE LWR`
- `AIMer MPC-in-the-head side channel HAETAE rejection sampling hyperball sampling masking`
- `masked hardware implementation lattice KEM FPGA first-order glitch robust probing 2026 Kyber NTT`

## 아직 못 지운 가능성

**가장 중요한 것부터.**

1. **KCMVP 가 방산에 요구하는 보안수준이 몇인지 확인 못 했다.** 수준 1·2 라면 부채널 시험
   요구가 없고, 그러면 이 주제의 제도 근거가 크게 약해진다. **이 칸을 먼저 닫아야 한다.**
2. **"Kyber/Saber 외에 없다" 는 2022년 문장이다.** 2023~2026 사이에 다른 기법의 마스킹
   하드웨어가 나왔을 수 있다. 연도를 좁혀 다시 봐야 한다.
3. **국내 문헌을 검색하지 않았다.** 한국정보보호학회 논문지·ICISC·KpqC 워크숍에 KpqC 마스킹
   하드웨어가 이미 있을 수 있다. **국내 연구실이 이미 하고 있을 가능성이 가장 크다.**
4. Saarinen 의 *ISO 표준 부채널 시험의 PQC 적용성* 을 **못 읽었다**(망 차단).
5. NTRU+ 의 부채널·마스킹을 **따로 검색하지 않았다.** SMAUG-T 쪽만 봤다.
6. AIMer(MPCitH)·HAETAE(rejection/hyperball sampling) 는 각각 한 번씩만 봤다.
   HAETAE 의 거절 샘플링은 Dilithium 계열에서 알려진 누출 자리인데 확인 안 했다.
7. ISO/IEC 17825:2024 본문·ISO/IEC 19790 부속서 F 본문 미열람(유료).
8. 마스킹 하드웨어 자동 생성(예: AGEMA 계열)을 검색하지 않았다. 이미 도구가 있으면
   "손으로 마스킹한다" 는 기여가 줄어든다.

**여덟 칸이 비어 있다. 특히 1번과 3번을 닫기 전에는 "없다" 고 말하지 않는다.**

---

# 못 지운 가능성 -- 2판 갱신

**닫힌 것**: (2) "Kyber/Saber 뿐" -- 죽었다. 2024~2026 에 ML-DSA·ML-KEM 통합·HQC 까지
있고 자동화 프레임워크(HADES, CHES 2025)도 있다. / (3) 국내 -- DGIST PAC Lab 이 KpqC
하드웨어 구현을, 국민대가 검증 방법론을 하고 있다. / (8) 자동 생성 도구 -- 현실이었다.

**여전히 빨강**

1. **KCMVP 가 방산에 요구하는 보안수준 (제일 크다).** 수준 1·2 면 ISO 17825 가 안 걸리고
   제도 근거가 무너진다. 웹 검색으로는 안 나온다 -- **국가정보원/KISA 에 직접 묻거나
   검증필 암호모듈 목록의 실제 보안수준 분포를 봐야 한다.**
2. **DGIST PAC Lab 의 실제 발표물을 못 찾았다.** 연구실 소개만 봤다. 이미 마스킹까지
   했는지, 어느 알고리즘인지 모른다. **직접 확인해야 한다(논문 목록·학위논문).**
3. **"마스킹 MPCitH 하드웨어가 없다" 는 한 번의 검색 결과다.** TCHES·CHES·eprint 를
   연도별로 훑지 않았다.
4. **AIMer 에 NTT 검증 정리가 안 닿는다는 것은 내 추론이다.** 재지 않았다.
5. Saarinen, *Applicability of ISO Standard Side-Channel Leakage Tests to PQC* --
   `mjos.fi` 망 차단으로 여전히 못 읽음.
6. NTRU+ 부채널·마스킹을 따로 검색하지 않았다.
7. HAETAE 의 거절/hyperball 샘플링 누출 -- 확인 안 했다.
   (Dilithium 계열 거절 샘플링 마스킹은 이미 연구가 있다 [출처:조각])
8. ISO/IEC 17825:2024 · 19790 부속서 F 본문 미열람(유료).

**1번과 2번을 닫기 전에는 이 주제를 시작하지 않는다.** 1번이 빨강이면 제도 근거가 없고,
2번이 빨강이면 국내에서 이미 하고 있는 것이다 -- CRPA 에서 무너진 것과 같은 자리다.

---

# 3판 (나) 시도 결과 -- **닫지 못했다. 망이 막는다.**

국내 DB·기관 자료를 직접 치려 했으나 **에이전시 프록시가 정책으로 막는다.** 차단 확인된 곳:

    nis.go.kr (검증필 암호모듈 목록)     sites.google.com (DGIST PAC Lab)
    koreascience.kr                      hiic.re.kr (KCMVP 현황과 과제)
    his.pusan.ac.kr                      eprint.iacr.org  ← 이 주제의 1차 출처
    mjos.fi                              digilent.com

**WebSearch(검색 요약)만 나간다.** 즉 목록을 세거나 본문을 읽는 일은 이 세션에서 못 한다.

## 그래도 검색으로 나온 것 -- 둘 다 3판 주장을 더 깎는다

1. **TCHES, *Gadget-based Masking of Streamlined NTRU Prime*** [출처:목록,
   tches.iacr.org/article/11238]. **NTRU 계열 하드웨어의 가젯 기반 마스킹이 이미 있다.**
   NTRU+ 는 NTRU 기반이므로 "NTRU+ 마스킹 하드웨어" 의 방법 자리도 비어 있지 않다.
2. **ICISC 2025** (서울, 2025-11-19~21, 74편 중 28편)의 분과가
   **「Side-Channel & Fault Analysis in PQC」**, **「Implementation & Hardware
   Acceleration」** 이다 [출처:조각, Springer 978-981-95-8034-7]. SMAUG-T 누출 평가
   논문이 바로 이 프로시딩에 실렸다. **국내 학계가 지금 이 자리에서 일하고 있다.**
3. eprint 2026/2066 *Optimizing HAETAE and SMAUG-T on Cortex-M4* [출처:목록] --
   PAC Lab 계열로 보이나 **소프트웨어**다.

## 판정 -- ③ 은 초록이 아니다

| 칸 | 상태 |
|---|---|
| KpqC 마스킹 **하드웨어** 자체 | 여전히 못 찾음 (그러나 **검색 요약으로만** 봤다) |
| 마스킹 **방법**의 신규성 | **없다.** ML-KEM/ML-DSA/HQC/NTRU Prime 가젯 마스킹, HADES 자동화 |
| 1차 마스킹의 충분성 | **없다.** 2025 에 1차 마스킹 Kyber FPGA 가 깨졌다 |
| 국내 선점 위험 | **높다.** ICISC 2025 에 전용 분과, DGIST·국민대가 진행 중 |
| 제도 근거(KCMVP 방산 수준) | **미확인.** 국내 검증필의 70%+ 가 S/W(=최대 수준 2) |

**"방산이 수준 3 이상을 요구한다" 를 확인하지 못한 채로는 제도 근거를 쓸 수 없다.**
그리고 그것을 확인할 길이 이 세션에 없다.

## 오늘 배운 것 -- 방법이 틀렸다

오늘 네 주제를 제안했고 **네 번 다 선행조사에서 깎였다**: 검증계량학(보수적 베이즈 학파),
CRPA 항재밍(상용·국내 양산), KpqC 마스킹(2024~2026 물결·국내 진행), 그리고 EHD 냉각
(고르기 전에 막음).

패턴이 분명하다. **"비어 있는 자리" 를 먼저 찾고 거기에 주제를 맞추려 했다.**
그런데 국방에 필요하고 박사급으로 어려운 자리는 **비어 있지 않다. 비어 있으면 대개
필요하지 않거나 못 하는 자리다.** 다음 판은 이 순서로 하지 않는다.
