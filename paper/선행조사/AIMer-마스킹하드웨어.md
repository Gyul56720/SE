# 선행조사 -- AIMer / AIM 의 마스킹 하드웨어

**방침이 바뀌었다.** 빈 밭을 찾지 않는다. **붐비는 밭(PQC 마스킹 하드웨어, 2024~2026)에서
아직 아무도 안 디딘 한 걸음**을 고른다. 방법을 새로 만들지 않고 이미 있는 가젯 위에 선다.

**읽은 수준**: 전부 검색 요약이다. **이 주제의 1차 출처가 전부 망에서 막혔다**(아래 참조).

---

## 고른 걸음

**AIMer 의 일방향 함수 AIM 을 FPGA 로 짓고, 그 비선형부를 기존 합성 가능 가젯으로 마스킹하고,
형식도구로 검증한다.**

왜 이 걸음인가: **AIM/AIMer 의 FPGA 하드웨어 구현이 검색 범위에서 보이지 않는다.**
마스킹 이전에 구현 자체가 없다. 그런데 AIMer 는 KpqC 전자서명 표준(2025-01 확정)이고,
2026 에 국방 포함 5개 분야 시범전환이 걸려 있다.

## 가장 가까운 선행연구

### AIM/AIMer 구현 -- **전부 소프트웨어 또는 양자회로다**
- **eprint 2023/1151** *High-speed Implementation of AIM symmetric primitives within AIMer
  digital signature* (Lee·Jang·Kwon·Sim·Song·**Seo**, 한성대 계열). **Mer 연산 최적화**와
  **선형층 연산 단순화**로 레퍼런스 대비 최대 **97.9%** 개선. 스스로 **"AIM 구현을 최적화한
  첫 연구"** 라 적는다 [출처:조각]. -- **소프트웨어**("기존 레퍼런스 코드 대비")
- **eprint 2026/1417** *Accelerating the AIMer Post-Quantum Signature with AVX-512* --
  VPCLMULQDQ 로 이진체 곱을 병렬화, 512비트 레지스터당 **MPC 4자** 처리 [출처:조각].
  -- **소프트웨어**
- **eprint 2023/337** *Quantum Implementation of AIM: Aiming for Low-Depth* [출처:목록]
  -- **양자 회로**. FPGA 가 아니다
- **AIMer 표준 코드는 2026-01 공개된 이식 가능 C 레퍼런스이고 프로세서별 최적화가 없다**
  [출처:조각]
- AIM 원논문: eprint 2022/1387 *AIM: Symmetric Primitive for Shorter Signatures with
  Stronger Security* [출처:목록]. AIMer 는 **AIM2 + BN++ 증명계**로 이뤄진다 [출처:조각]

### MPCitH 하드웨어는 있다 -- 다만 AIMer 가 아니다
- TCHES 2024, *High-Performance Hardware Implementation of MPCitH and Picnic3* [출처:조각]
- eprint 2019/1368 *Efficient FPGA Implementations of LowMC and Picnic* [출처:목록]
- eprint 2026/206 *MPSpeed: Accelerating Mirath on FPGA* [출처:목록]
- 다른 PQC 서명의 FPGA 가속기: SPHINCS-256(TCHES), **CROSS**(NIST 6차 PQC 학회 2025),
  Dilithium, Falcon [출처:목록] -- **AIMer 만 없다**

### MPCitH 마스킹은 있다 -- 다만 소프트웨어다
- *Side-Channel Protections for Picnic Signatures* (2021): KKW 영지식 증명계를 **임의 차수로**
  마스킹. 구현은 **ARM Cortex-M4 1차**. 오버헤드 **1.8~5.5배**, 비용이 **해시 호출에 몰린다**
  [출처:조각]
- eprint 2024/1882 (NIST 6차 PQC 학회 2025) MPCitH 단일 트레이스 공격.
  **값 하나만 새어도 프로토콜 보안이 깨진다** [출처:조각]
- *SNI-in-the-head* (ACM CCS 2020) [출처:목록]

### 우리가 올라설 기계 (이미 있다 -- 새로 만들지 않는다)
- **HPC1 / HPC3.1** 곱 가젯 -- **모든 유한체 F_p^n 에서 동작**, 랜덤성 재사용 전략
  [출처:조각, TCHES *Efficient and Composable Masked AES S-Box Designs Using Optimized
  Inverters*, article 11942]
- Canright 식 **체 분해**(큰 체의 연산을 작은 체의 곱·합·역원 조합으로) [출처:조각]
- GF(2^n) 마스킹 역원 [출처:목록, Oswald 계열]
- **검증 도구**: PROLEAD(넷리스트 시뮬만, 전력모델 불필요, 글리치+전이),
  SILVER(ROBDD 정확·거짓양성 없음), COCO/CocoAlma, Prover/ProverNG [출처:조각]

## 우리가 그것과 다른 점

1. **AIM 의 FPGA 구현이 없다.** 소프트웨어 최적화(2023/1151, 2026/1417)와 양자회로(2023/337)
   뿐이다. 하드웨어는 첫 걸음이다.
2. **비선형부의 성격이 다르다.** AIM 의 비선형은 **Mersenne 거듭제곱** `x^(2^e - 1)` 이다.
   AES 의 GF(2^8) 역원(x^254)과 달리 **체가 훨씬 크고 지수가 파라미터**다. 체 분해 전략,
   곱 깊이, **랜덤성 비용**이 전부 달라질 수밖에 없다.
   -- **주의: 규격서를 못 읽어 n 과 e 를 확인하지 못했다. 아래 참조.**
3. **2026 형식검증 물결이 안 닿는 자리일 수 있다.** Prime-Field PINI, 마스킹 Barrett 축약,
   NTT 파이프라인 합성성 -- 전부 **격자의 소수체·NTT** 를 겨눈다. AIM 은 GF(2^n) 과 해시가
   본체다. -- **이것은 추론이다. 재지 않았다.**
4. **마스킹 비용이 해시에 몰린다**(소프트웨어 실측 1.8~5.5배). 하드웨어에서 이 분포가
   어떻게 되는지는 소프트웨어 결과로 예측되지 않는다.

## 찾아본 질의

- `AIM one-way function hardware implementation FPGA AIMer signature Mersenne S-box exponentiation accelerator`
- `masked hardware GF(2^n) field inversion large S-box threshold implementation Mersenne exponentiation masking gadget randomness cost`
- `"High-speed Implementation of AIM" eprint 2023/1151 software optimization ARM AVX hardware FPGA which platform`
- `AIMer FPGA hardware accelerator implementation ASIC "AIM" post-quantum signature Korean hardware architecture 2025 2026`
- `masked hardware implementation MPC-in-the-head signature AIMer Picnic FPGA side-channel countermeasure`
- `KpqC SMAUG-T NTRU+ AIMer HAETAE hardware FPGA masking side-channel` (eprint·tches·arxiv 한정)
- (앞선 조사) `KpqC-마스킹하드웨어.md` 의 질의 아홉 개

## 아직 못 지운 가능성 -- **망 차단이 제일 크다**

**이 세션에서 1차 출처를 하나도 못 읽었다.** 프록시가 정책으로 막는 곳:

    eprint.iacr.org   ← 이 분야의 1차 출처. IACR 검색 자체를 못 했다
    csrc.nist.gov     ← AIMer 규격서. 그래서 AIM 의 구조·파라미터 미확인
    koreascience.kr · his.pusan.ac.kr · hiic.re.kr · nis.go.kr · sites.google.com · mjos.fi

그리고 GitHub 레퍼런스 코드는 **세션 저장소 범위 밖**이다(`gyul56720/se` 만 허용).

1. **AIM 하드웨어 논문이 eprint 에 있어도 나는 못 본다.** "없다" 가 아니라 **"검색 요약에
   안 나왔다"** 이다. 이 차이가 오늘 네 번 나를 틀리게 했다.
2. **AIM 의 n·e·S-box 개수·선형층을 모른다.** 규격서를 못 읽었다. 이걸 모르면 RTL 을
   정확히 못 친다 -- **Phase 0 의 선행조건이다.**
3. **AIM1 과 AIM2 의 차이를 모른다.** AIMer 는 AIM2 를 쓴다고만 봤다.
4. **한성대 Seo 그룹**이 소프트웨어(2023/1151)에서 하드웨어로 이미 갔을 수 있다.
   국내 논문 경로가 전부 막혀 확인 못 했다. **KpqC 때 국내 선점이 실제였다.**
5. TCHES/CHES 목차를 연도별로 훑지 않았다.
6. AIMer 의 다른 부분(BN++ 증명계, Keccak) 하드웨어를 따로 안 봤다.

## Phase 0 를 시작하려면 무엇이 있어야 하나

**AIMer 규격서(PDF) 또는 레퍼런스 C 코드.** 둘 다 공개 자료이고 이 세션에서만 못 닿는다.
받는 순간 시작한다:

    0-a  AIM 의 Mer S-box 를 RTL 로 짓는다 (마스킹 없음)
    0-b  레퍼런스 벡터로 정확성 대조                     ← 여기까지 장비 0원
    0-c  yosys 합성 -> 넷리스트 -> 이 저장소의 관문에 태운다
    1    HPC 가젯으로 1차 마스킹 -> PROLEAD/SILVER 검증
    2    AIM 전체 -> AIMer 로 확장
    3    FPGA 보드 실측 (면적·지연·랜덤성), 그 뒤 TVLA
