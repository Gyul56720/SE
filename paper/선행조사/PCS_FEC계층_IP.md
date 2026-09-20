# B. PCS / FEC 계층 IP -- 선행조사

조사일 2026-09-19. `SerDes_DSP등화기_IP.md` 10절에서 갈라진 길 B 를 판다.
**짓기 전에 쓴다** (G024).

## 0. 조사 조건 -- 이번에 무엇이 열렸고 무엇이 막혔나

    curl 직접          ieee802.org · standards.ieee.org · mathworks · arxiv -> **전부 000**
    WebFetch           ieee802.org · signalintegrityjournal · eecg.utoronto.ca
                       -> **전부 EGRESS_BLOCKED.**  허용 도메인이 좁다
    WebSearch          **된다** (제목·URL·요약)
    GitHub 검색 API    **된다** -- 저장소 검색 · 코드 검색
    git clone          **된다** -- 받아서 직접 셌다

**논문도 규격도 전문을 못 봤다.** 아래에서 `[출처:전문]` 은 **클론한 저장소**뿐이다.

## 1. 상용은 빽빽하다

| 벤더 | 물건 | 확인 |
|---|---|---|
| **AMD/Xilinx** | 100G IEEE 802.3bj **및 802.3ck** RS-FEC LogiCORE. RS(528,514) KR4 · **RS(544,514) KP4** 지원. 암호화 RTL + Verilog 예제 | `[출처:조각]` |
| **Hitek Systems** | `HTK-RSFEC-N544-K514` -- N=544, K=514, t=15, m=10 복호기. KP4 규격 | `[출처:조각]` |
| **Creonic** | IEEE 802.3bj Reed-Solomon codec, KP4 (544,514), 심볼 15개 정정 | `[출처:조각]` |
| Synopsys | 100G Ethernet PCS IP | `[출처:목록]` |
| Comcores · MoSys/Peraso · Chip Interfaces | Ethernet PCS 100G~1.6T · 100G Gearbox with RS-FEC | `[출처:목록]` |

상용 PCS IP 가 내놓는 기능 목록 `[출처:조각]`:

    스크램블러/디스크램블러 · 64b/66b 부호기/복호기 · multi-lane distribution
    · alignment marker 삽입/제거 · block sync · gearbox · 클럭 분리 FIFO
    · RS-FEC (KR4/KP4)

**"soft PCS layer deliverable" 이 팔리는 물건이라는 9절의 발견이 여기서 확인된다.**

## 2. 공개 구현 -- 받아서 셌다. 10G 는 있고 100G 와 FEC 는 없다

| 저장소 | 별 | 규모 | 확인 |
|---|---|---|---|
| **alexforencich/verilog-ethernet** | 3,099 | RTL 98파일 **35,839줄** | **`[출처:전문]`** 클론 |
| fpganinja/taxi | 940 | SystemVerilog | **`[출처:전문]`** 클론 |
| RS Verilog 저장소 전체 | 0~27 | 작다 | `[출처:목록]` |

### verilog-ethernet 에 **있는** 것 -- 10G BASE-R PCS, 3,496줄

    xgmii_baser_enc_64.v        284줄   64b/66b 부호기
    xgmii_baser_dec_64.v        417줄   64b/66b 복호기
    axis_baser_tx_64.v          792줄
    axis_baser_rx_64.v          560줄
    eth_phy_10g_rx_frame_sync.v 146줄   블록 동기
    eth_phy_10g_rx_ber_mon.v    124줄   BER 모니터
    eth_phy_10g_rx_watchdog.v   172줄
    eth_phy_10g_{rx,tx}{,_if}.v 737줄
    lfsr.v                              스크램블러
                                -----
                                3,496줄

**정정: 처음에 "PCS 가 없다" 고 셌는데 틀렸다.** `*pcs*` 파일명으로 찾아서 0 이 나왔다.
실제 이름은 `eth_phy_10g_*` 와 `axis_baser_*` 다(BASE-R 이 64b/66b PCS 다).
**내 검색이 틀린 것이지 저장소가 빈 것이 아니었다.**

### verilog-ethernet 에 **없는** 것

    RS-FEC                      파일 0
    100G 이상 PCS               100g|multilane|alignment|deskew 매칭 **0**
    multi-lane distribution     없음
    alignment marker            없음
    gearbox (>10G)              없음

`fpganinja/taxi` 에서 PCS 로 걸리는 것은 **Xilinx IP 를 부르는 `.tcl` 래퍼뿐**이다
(`sgmii_pcs_pma_0.tcl` 등). 자체 PCS 가 아니다.

### RS 구현은 작고 전부 GF(2^8) 계열이다

    GitHub 저장소 검색 "reed-solomon verilog"     **13개**.  별 0~27
    winsonbook/Reed-Solomon-  (별 27)             3,683줄.  심볼 8비트, 3심볼 정정
    wyvernSemi/eccExamples    (별 10)             542줄.  발표자료 예제
    코드 검색 "GF(2^10)" + reed solomon + verilog  **0건**
    저장소 검색 KP4 / RS(544,514) 계열             **0건**

**공개된 GF(2^10) KP4 Verilog 구현을 못 찾았다.**
다만 **GitHub 검색은 전수가 아니다** -- 아래 6절.

## 3. 특허 -- 알고리즘은 늙었고, 구현 특허는 확인이 덜 됐다

| | 연도 | 상태 |
|---|---|---|
| Reed-Solomon 부호 자체 | 1960 | 특허 개념 밖 |
| Berlekamp-Massey | 1968~69 | 만료 |
| Chien search · Forney | 1964~65 | 만료 |
| **US 7,010,739** inversionless BM 오류평가기 | 2006 등록 | 출원 2003 근처 -> **만료 근처/만료** `[출처:조각]` |
| **US 7,249,310** 동 계열 | 2007 등록 | 동상 `[출처:조각]` |
| US 7,051,267 고속 RS 복호기 | 2006 등록 | 동상 `[출처:목록]` |

**A 와 대비된다.** A 의 US 9,077,574 는 2015 등록으로 **2033년 전후까지 살아 있다.**
B 의 핵심 알고리즘 특허는 **만료됐거나 만료 근처**다.

**그러나 KP4 고유 특허를 전혀 안 봤다.** 4-lane interleaving · 심볼 분배 · transcoding
같은 802.3 고유 부분에 최근 특허가 있을 수 있다. 검색에 Xilinx 의
"Details of 4-lane Interleaved 100G FEC" 발표자료가 떴다 -- **그 영역을 안 봤다.**

## 4. 그리고 새로운 것이 하나 있다 -- 802.3dj 연접 FEC

| | 내용 | 확인 |
|---|---|---|
| 외부 부호 | **RS KP4 (544,514,15) over GF(2^10)** -- 기존 그대로 | `[출처:조각]` |
| 내부 부호 | **Hamming (128,120)** = 확장 Hamming(127,120) + 패리티 1비트 | `[출처:조각]` |
| 대상 | 200 Gbps/lane IM-DD, **800GBASE-R · 1.6TBASE-R** | `[출처:조각]` |
| 시기 | 2023~2024 채택 | `[출처:조각]` |

**구조: 강한 비이진 외부 부호(버스트 정정) + 단순 이진 내부 부호(랜덤 비트 정정).**

이것이 B 에서 가장 값있는 자리일 수 있다 -- **KP4 단독은 2014년부터 있었지만 연접
구조는 새것**이고, 공개 구현은 KP4 단독조차 없다.

**다만 IEEE 기고문을 하나도 못 읽었다** (`ieee802.org` EGRESS_BLOCKED).
위 표는 전부 검색 요약이다. **인터리빙 방식 · 복호 순서 · 지연 예산을 모른다.**

## 5. 실무 관문 -- 규격을 읽을 수 있는가

구현하려면 IEEE 802.3 **Clause 91**(RS-FEC) 과 **Clause 161**(802.3ck) 의 본문이
있어야 한다. 심볼 분배 · 인터리빙 · alignment marker 처리가 전부 거기 있다.

    이 컨테이너에서 standards.ieee.org  ->  **000. 못 받는다**

    그러나 **"Get IEEE 802" 로 802 계열 규격은 무료 공개**된다 `[출처:조각]`
    -> **사용자가 받을 수 있다. 이것이 B 의 실행 가능성을 가르는 한 가지다**

규격을 못 읽으면 B 는 시작할 수 없다. **다음 걸음의 첫 항목이다.**

## 6. 규모 -- 기준선이 하나 더 생겼다

    verilog-ethernet 의 10G PCS (단일 레인, FEC 없음)      3,496줄
    AMD Vitis security (AES+SHA, 코어 2개)                 1,970줄
    AMD Vitis solver                                       3,458줄

10G 단일 레인 PCS 가 3,496줄이다. **우리 목표 3,000~5,000줄이 맞는 크기임을
독립된 기준선이 확인해 준다.** KP4 부호기+복호기(신드롬·BM·Chien·Forney)만으로
2,000~3,000줄, 여기에 골든 모델·생성기·테스트벤치가 붙는다.

## 7. A 와 B 비교 -- 잰 것만

| | A. DSP 등화기 데이터패스 | B. PCS/FEC |
|---|---|---|
| 특허 | **US 9,077,574 직격, ~2033 생존** | 핵심 알고리즘 만료. **KP4 고유는 미조사** |
| 규격 접근 | 규격 없음(구현 자유) | **Clause 91/161 필요. Get IEEE 802 로 무료** |
| 공개 선행 | OpenSERDES 556줄, 등화기 없음 | verilog-ethernet 10G PCS 3,496줄, **FEC 없음** |
| 상용 | Cadence·Synopsys·Alphawave·Credo (하드 매크로 동봉) | AMD·Creonic·Hitek·Synopsys·Comcores (**순수 소프트 IP**) |
| 공정 의존 | 없음(디지털) | 없음 |
| 우리 자산 | `afe/eqrtl/specdfe` 1,771줄 | `fec/pam/comply` 607줄 (**분석만. 부호기/복호기 없음**) |
| 새것이 있나 | 없음 -- 1990년대 구조 | **802.3dj 연접 FEC(2024)** |
| MATLAB 위협 | **SerDes Toolbox 가 적응 엔진 RTL 생성** | **Communications Toolbox 가 RS 코덱 HDL 생성** (7.1절) |

**B 가 A 보다 나은 칸은 특허와 새것 둘이다. MATLAB 칸은 B 도 맞았다.**

## 7.1 B 에도 같은 검사를 했다 -- 그리고 같은 것이 나왔다

8절에 "아직 안 봤다" 로 남기지 않고 바로 확인했다. A 를 죽인 검사다.

| 무엇 | 확인 |
|---|---|
| `comm.HDLRSEncoder` / `comm.HDLRSDecoder` System object -- **HDL 생성 가능** | `[출처:조각]` |
| Simulink `Integer-Input RS Encoder HDL Optimized` / `Integer-Output RS Decoder HDL Optimized` -- "HDL 코드 생성과 하드웨어 배치에 적합한 아키텍처" | `[출처:조각]` |
| 문서의 예시는 **RS(255,239)** 이고 규격 지원으로 언급되는 것은 **IEEE 802.16** | `[출처:조각]` |
| **KP4 / RS(544,514) / GF(2^10) 직접 지원은 확인되지 않았다** | 검색이 그렇게 답했다 |

**그러나 이것이 B 를 죽이지는 않는다. 이유를 정확히 적는다.**

MATLAB 이 주는 것은 **RS 코덱 코어**다. 802.3 의 **RS-FEC 서브계층**은 코덱보다
넓다 -- Clause 91 이 규정하는 것은 이것들이다:

    transcoding            64b/66b -> 256b/257b
    심볼 분배              4 레인에 걸친 interleaving
    alignment marker 처리  FEC 경계와의 정렬
    코드워드 인터리빙      Xilinx 발표자료 "Details of 4-lane Interleaved 100G FEC"
    비트/심볼 매핑         규격 고유

**코덱은 RS-FEC IP 의 일부이지 전부가 아니다.**  A 에서 "adaptation engine 은
데이터패스가 아니다" 라고 한 것과 같은 종류의 구분이고, **A 때와 똑같이 이것도
내 읽기일 뿐이다** -- mathworks.com 은 여전히 EGRESS_BLOCKED 다.

**사용자가 확인할 자리 둘:**

    1. HDL RS 블록이 m=10 (GF(2^10)) 과 N=544 를 받는가?
       -> 받으면 코덱 부분은 MATLAB 이 낸다
    2. 802.3 RS-FEC 서브계층(transcoding · 레인 분배 · AM 처리)을 내는 블록이 있는가?
       -> 있으면 B 도 A 처럼 다시 짜야 한다

## 8. 아직 안 본 것 -- **"없다" 라고 쓰지 않는다**

  1. **IEEE 802.3 규격 본문을 못 봤다.** Clause 91 · 161 · 802.3dj 초안 전부.
     구현의 전제 조건이고 아직 없다
  2. **IEEE 802.3dj 기고문을 하나도 못 읽었다.** 4절은 검색 요약뿐이다
  3. **KP4 고유 특허(4-lane interleaving · 심볼 분배 · transcoding)를 안 봤다**
  4. ~~MATLAB 이 RS-FEC RTL 을 내는지~~ -> **7.1절에서 봤다.** RS 코덱 HDL 블록은
     있다. **다만 m=10/N=544 지원 여부와 802.3 서브계층 지원 여부는 여전히 모른다**
  5. **상용 PCS IP 의 사양서(PG/PB 문서)를 안 봤다.** 무엇을 납품해야 IP 인지 모른다
  6. **GitHub 검색은 전수가 아니다.** 코드 검색은 색인된 것만, 저장소 검색은
     메타데이터만 본다. 비공개·미색인 구현이 있을 수 있다
  7. **OpenROAD/OpenLane 생태계, chipyard, BAG 를 안 봤다**

## 9. 찾아본 질의

    open source RS-FEC KP4 RS(544,514) Reed-Solomon GF(2^10) Verilog RTL implementation github 802.3
    commercial Ethernet PCS IP core deliverables 802.3ck 100G lane RS-FEC gearbox datasheet what is included
    Reed-Solomon KP4 RS-FEC patent landscape expired Berlekamp-Massey syndrome decoder patents 802.3 essential
    IEEE 802.3dj 224G per lane FEC concatenated inner code Hamming outer RS 2025 2026 decision
    Get IEEE 802 program free download 802.3 standard clause 91 RS-FEC public access no cost
    (GitHub API) reed-solomon FEC 544 514 KP4 ethernet verilog / KP4 "RS-FEC" / "GF(2^10)" reed solomon
    (GitHub API) verilog-ethernet / reed-solomon verilog
