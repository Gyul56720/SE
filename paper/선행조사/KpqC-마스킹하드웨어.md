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
