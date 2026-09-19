# -*- coding: utf-8 -*-
"""제4부 -- 칩을 만들 때 / 업계 표준 / 논문 / IP 아이디어."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from book import 표, 줄수, E


def ch_soc():
    s = ['<h1 id="soc">SoC 하나를 만들려면 어떤 IP 가 필요한가</h1>']
    s.append("""<p>&ldquo;칩을 만든다&rdquo;는 말은 실무에서 <b>IP 를 고르고 붙이고
    검증한다</b>는 뜻이다. 자체 설계하는 것은 차별화 블록 한둘이고 나머지는 산다.
    아래는 일반적인 SoC 의 구성이고, <b>어느 것이 사는 것이고 어느 것이 만드는 것인지</b>
    를 같이 적는다.</p>""")
    s.append(표("SoC 필수 IP 목록과 조달 방식",
        ["계층", "IP", "보통 어떻게", "이 교안의 실물"],
        [["<b>연산</b>", "CPU 코어 (RISC-V · Arm)", "라이선스(Arm) 또는 오픈(RISC-V)",
          "<code>cva6</code> · <code>cv32e40p</code> · <code>rocket-chip</code>"],
         ["", "DSP · NPU · GPU", "라이선스 또는 자체", "<code>finn_hlslib</code>(QNN)"],
         ["<b>메모리</b>", "DDR/LPDDR 컨트롤러 + PHY", "<b>반드시 산다</b>(PHY 는 하드매크로)", "&mdash;"],
         ["", "SRAM 컴파일러", "파운드리/메모리벤더", "&mdash;"],
         ["", "캐시 · 스크래치패드", "자체 또는 코어에 포함", "<code>cva6</code> 내부"],
         ["<b>연결</b>", "버스/NoC (AXI · TileLink · AHB · APB)", "오픈 또는 라이선스",
          "<code>pulp-platform/axi</code> {0:,}줄 · <code>apb</code>"],
         ["", "기본 셀(FIFO · CDC · 아비터)", "자체 라이브러리",
          "<code>common_cells</code> {1:,}줄"],
         ["<b>입출력</b>", "PCIe · Ethernet · USB · MIPI · SerDes PHY",
          "<b>PHY 는 반드시 산다</b>. 컨트롤러는 선택",
          "<code>verilog-pcie</code> · <code>verilog-ethernet</code> · <code>corundum</code>"],
         ["", "SPI · I2C · I3C · UART · GPIO", "오픈/자체. 싸다",
          "OpenTitan 에 전부 있다"],
         ["<b>보안</b>", "RoT · AES · SHA · RSA/ECC · TRNG · OTP · 키관리",
          "산업 표준 요구(OCP · FIPS)",
          "<code>opentitan</code> · <code>caliptra-rtl</code>"],
         ["<b>기반</b>", "PLL · 클럭생성 · 리셋 · 전력관리(PMU)", "파운드리 IP", "&mdash;"],
         ["", "디버그(JTAG · 트레이스)", "표준 필수",
          "<code>pulp-platform/riscv-dbg</code>"],
         ["", "DFT(스캔 · MBIST · BSD)", "EDA 삽입", "&mdash;"],
         ["", "eFuse · 온도/전압 센서", "파운드리", "&mdash;"]]
        .__class__([[a,b,c,d.format(줄수('ip','pulp-platform_axi'), 줄수('ip','pulp-platform_common_cells')) if '{0' in d or '{1' in d else d] for a,b,c,d in [
         ["<b>연산</b>", "CPU 코어 (RISC-V · Arm)", "라이선스(Arm) 또는 오픈(RISC-V)",
          "<code>cva6</code> · <code>cv32e40p</code> · <code>rocket-chip</code>"],
         ["", "DSP · NPU · GPU", "라이선스 또는 자체", "<code>finn_hlslib</code>(QNN)"],
         ["<b>메모리</b>", "DDR/LPDDR 컨트롤러 + PHY", "<b>반드시 산다</b>(PHY 는 하드매크로)", "&mdash;"],
         ["", "SRAM 컴파일러", "파운드리/메모리벤더", "&mdash;"],
         ["", "캐시 · 스크래치패드", "자체 또는 코어에 포함", "<code>cva6</code> 내부"],
         ["<b>연결</b>", "버스/NoC (AXI · TileLink · AHB · APB)", "오픈 또는 라이선스",
          "<code>pulp-platform/axi</code> {0:,}줄"],
         ["", "기본 셀(FIFO · CDC · 아비터)", "자체 라이브러리",
          "<code>common_cells</code> {1:,}줄"],
         ["<b>입출력</b>", "PCIe · Ethernet · USB · MIPI · SerDes PHY",
          "<b>PHY 는 반드시 산다</b>. 컨트롤러는 선택",
          "<code>verilog-pcie</code> · <code>corundum</code>"],
         ["", "SPI · I2C · I3C · UART · GPIO", "오픈/자체. 싸다", "OpenTitan 에 전부"],
         ["<b>보안</b>", "RoT · AES · SHA · RSA/ECC · TRNG · OTP · 키관리",
          "산업 표준 요구(OCP · FIPS)", "<code>opentitan</code> · <code>caliptra-rtl</code>"],
         ["<b>기반</b>", "PLL · 클럭생성 · 리셋 · 전력관리(PMU)", "파운드리 IP", "&mdash;"],
         ["", "디버그(JTAG · 트레이스)", "표준 필수", "<code>pulp-platform/riscv-dbg</code>"],
         ["", "DFT(스캔 · MBIST · BSD)", "EDA 삽입", "&mdash;"],
         ["", "eFuse · 온도/전압 센서", "파운드리", "&mdash;"]]])))

    s.append("""<div class="ms"><b>&ldquo;PHY 는 산다&rdquo;가 반복되는 이유.</b>
    PHY 는 아날로그/혼성신호이고 <b>공정에 강하게 묶인다</b>. 7nm PHY 를 5nm 로 옮기는
    것은 재설계에 가깝다. 그래서 파운드리·전문업체가 공정별로 하드 매크로(GDS)로 판다.
    디지털 IP(RTL)는 공정 무관이라 이식이 싸다. <b>이 경계가 IP 시장의 가격 구조를
    만든다</b> &mdash; 하드 매크로가 비싸고, 소프트 IP 는 상대적으로 싸다.</div>""")

    s.append("<h2>칩을 만들 때 꼭 생각해야 하는 것</h2>")
    s.append(표("설계 착수 전 점검표 &mdash; 놓치면 테이프아웃 뒤에 드러난다",
        ["항목", "물어야 할 것", "놓쳤을 때"],
        [["<b>클럭 도메인</b>", "도메인이 몇 개인가? 모든 교차에 동기화기가 있나?",
          "메타스테이빌리티. <b>재현 안 되는 간헐 오류</b>"],
         ["<b>리셋</b>", "비동기 assert / 동기 deassert 인가? 리셋 트리 지연은?",
          "리셋 해제 시점이 달라 FSM 이 엇갈린다"],
         ["<b>전력 도메인</b>", "꺼지는 블록이 있나? 아이솔레이션 셀 · 리텐션은?",
          "전원이 꺼진 블록의 출력이 X 로 퍼진다"],
         ["<b>DFT</b>", "스캔 체인이 모든 FF 를 덮나? MBIST 가 모든 SRAM 을?",
          "양산 테스트 커버리지 부족 &rarr; 불량 유출"],
         ["<b>디버그</b>", "칩이 안 뜨면 무엇을 볼 수 있나?",
          "<b>브링업 불가.</b> 가장 비싼 실패"],
         ["<b>레지스터맵</b>", "단일 원천에서 RTL·문서·드라이버·UVM 을 생성하나?",
          "소프트웨어와 하드웨어가 어긋난다"],
         ["<b>보안 경계</b>", "비밀이 지나는 경로가 어디까지인가? 디버그로 새나?",
          "JTAG 로 키가 나온다"],
         ["<b>타이밍 예외</b>", "false path · multicycle 을 누가 검토했나?",
          "잘못 선언한 예외 = 검증 안 된 경로"],
         ["<b>SDC/제약</b>", "합성·STA 제약이 RTL 가정과 맞나?",
          "합성은 통과, 실리콘은 실패"],
         ["<b>IP 통합</b>", "산 IP 의 가정(클럭비 · 리셋순서 · 초기화)을 지켰나?",
          "벤더는 &lsquo;문서에 있다&rsquo;고 답한다"],
         ["<b>ECO 여유</b>", "스페어 셀을 뿌려 뒀나?",
          "금속만 고치는 수정이 불가능해져 풀마스크 재제작"],
         ["<b>패키지/IO</b>", "핀 수 · SI/PI · ESD 가 검토됐나?", "동작은 하는데 보드에서 실패"]]))
    return "\n".join(s)


def ch_std():
    s = ['<h1 id="std">업계 표준 &mdash; 무엇을 알고 있어야 하나</h1>']
    s.append("""<p>IP 를 다룬다는 것은 표준을 다룬다는 뜻이다. 아래는 모델링 팀이
    마주치는 순서대로다. <b>전부 외울 필요는 없고, 무엇이 어디를 규정하는지</b>를
    알면 된다.</p>""")
    s.append(표("언어 · 방법론 표준",
        ["표준", "번호", "무엇", "모델링 팀에서"],
        [["SystemVerilog", "IEEE 1800", "설계 + 검증 언어",
          "DPI-C 절을 반드시 읽어라. 모델을 붙이는 통로다"],
         ["Verilog", "IEEE 1364", "구형 설계 언어", "레거시 IP 에서 만난다"],
         ["VHDL", "IEEE 1076", "설계 언어", "유럽·항공/방산 IP"],
         ["<b>SystemC</b>", "IEEE 1666", "C++ 하드웨어 모델링",
          "<b>가상 플랫폼의 표준.</b> TLM-2.0 포함"],
         ["UVM", "IEEE 1800.2", "검증 방법론", "DV 가 쓴다. 용어를 알아야 대화가 된다"],
         ["UPF", "IEEE 1801", "전력 의도 기술", "저전력 설계의 의도를 적는다"],
         ["IP-XACT", "IEEE 1685", "IP 메타데이터 · 레지스터맵",
          "레지스터맵 단일 원천의 표준 형식"],
         ["SDF / SDC", "IEEE 1497 / 사실상 표준", "지연 · 타이밍 제약", "&mdash;"],
         ["PSL / SVA", "IEEE 1850 / 1800 내", "속성 · 단언", "형식 검증의 언어"]]))
    s.append(표("인터페이스 · 프로토콜 표준",
        ["영역", "표준", "핵심 개념"],
        [["온칩 버스", "<b>AMBA AXI4 / AXI4-Lite / AXI4-Stream</b> (Arm)",
          "채널 5개 · 핸드셰이크(VALID/READY) · 버스트 · 아웃오브오더(ID)"],
         ["", "AHB · APB (Arm)", "저속 주변장치는 APB"],
         ["", "TileLink (RISC-V 계열)", "캐시 일관성까지 규정"],
         ["", "TL-UL (OpenTitan)", "TileLink Uncached Lightweight"],
         ["", "CHI (Arm)", "일관성 · 다중 코어"],
         ["칩간", "<b>PCIe</b> (PCI-SIG) Gen1~Gen6", "PHY · 링크 · 트랜잭션 3계층"],
         ["", "<b>CXL</b>", "PCIe 물리계층 위의 메모리 일관성"],
         ["", "UCIe", "칩렛 다이-투-다이"],
         ["네트워크", "<b>IEEE 802.3</b> Ethernet",
          "Clause 별 구성: 49(64b/66b PCS) · 91(RS-FEC) · 161(802.3ck)"],
         ["메모리", "JEDEC DDR4/5 · LPDDR5 · HBM", "타이밍 파라미터가 곧 규격"],
         ["저속", "I2C · I3C(MIPI) · SPI · UART", "가장 자주 쓰는 주변장치"],
         ["디버그", "IEEE 1149.1 JTAG · RISC-V Debug Spec", "브링업의 생명선"]]))
    s.append(표("암호 · 보안 표준",
        ["표준", "무엇", "검증에서"],
        [["<b>FIPS-197</b>", "AES", "시험 벡터가 부록에 있다"],
         ["FIPS-180-4", "SHA-1/2", "&mdash;"],
         ["FIPS-202", "SHA-3 / SHAKE (Keccak)", "OpenTitan <code>kmac</code>"],
         ["FIPS-186", "DSA/ECDSA", "&mdash;"],
         ["FIPS-203/204/205", "<b>양자내성(ML-KEM · ML-DSA · SLH-DSA)</b>",
          "Caliptra 에 ML-DSA 구현이 있다"],
         ["NIST SP 800-90A/B/C", "난수 생성(DRBG · 엔트로피)",
          "OpenTitan <code>csrng</code> · <code>entropy_src</code>"],
         ["NIST CAVP", "암호 알고리즘 검증 프로그램", "<b>벡터의 출처</b>"],
         ["ISO/IEC 17825", "부채널 시험", "TVLA 방법론"],
         ["<b>OCP Caliptra</b>", "데이터센터 RoT 사양", "이 교안에 RTL 이 들어 있다"]]))
    s.append("""<div class="note"><b>실무 팁.</b> IEEE 802 계열 규격은
    <b>&ldquo;Get IEEE 802&rdquo; 프로그램으로 무료</b>다. PCI-SIG · JEDEC 는 회원사만
    본다(회사가 회원이면 사내 포털에 있다). NIST FIPS 는 전부 무료다.
    <b>첫 주에 당신 블록의 규격 원문을 확보하라.</b> 남의 요약으로 모델을 쓰면 그 요약의
    오해가 칩에 들어간다.</div>""")
    return "\n".join(s)


def ch_paper():
    s = ['<h1 id="paper">논문 활용법 &mdash; 실무에서 어떻게 쓰나</h1>']
    s.append("""<p>모델링 팀에서 논문은 <b>읽는 대상이 아니라 도구</b>다. 쓰임새가
    분명하다.</p>""")
    s.append(표("실무에서 논문이 쓰이는 네 가지 자리",
        ["쓰임", "무엇을 찾나", "어디서", "주의"],
        [["<b>구조 선택</b>", "같은 기능의 여러 회로 중 무엇이 왜 나은가",
          "JSSC · ISSCC · VLSI · DAC/ICCAD",
          "논문의 수는 <b>가장 유리한 조건</b>에서 나온다. 조건을 먼저 읽어라"],
         ["<b>알고리즘 근거</b>", "왜 이 수식이 맞는가, 수렴 조건은",
          "IEEE Trans. · arXiv", "구현 논문과 이론 논문을 구분하라"],
         ["<b>공격/취약점</b>", "우리 대책이 이미 깨졌나",
          "CHES · CCS · USENIX Security", "보안 IP 는 <b>필수</b>"],
         ["<b>표준의 배경</b>", "규격이 왜 그렇게 정해졌나",
          "표준화 기구 기고문(IEEE 802 public 디렉터리 등)",
          "<b>규격 본문보다 기고문이 더 잘 설명한다</b>"]]))
    s.append("<h2>논문을 읽는 순서 (30분 안에 판단하기)</h2>")
    s.append("""<ol>
    <li><b>표/그림부터</b> 본다. 무엇을 쟀는지가 거기 있다</li>
    <li><b>실험 조건</b>을 찾는다. 공정 · 전압 · 온도 · 채널 · 데이터셋. <b>여기가
        비교 가능성을 정한다</b></li>
    <li><b>기준선(baseline)</b>이 무엇인지 본다. 약한 기준선과 비교했으면 수가 커 보인다</li>
    <li>그제서야 <b>방법</b>을 읽는다</li>
    <li>마지막에 <b>한계/future work</b> 를 읽는다. 저자가 아는 약점이 거기 있다</li>
    </ol>""")
    s.append("""<div class="warn"><b>실무에서 가장 위험한 인용은 &ldquo;읽지 않고 쓴
    인용&rdquo;이다.</b> 초록과 검색 조각만 보고 &ldquo;이 방식이 좋다&rdquo;고 보고하면,
    조건이 우리와 다를 때 몇 달을 버린다. <b>확인 수준을 표시하는 습관</b>을 권한다 &mdash;
    전문을 읽었나(전문) · 초록만인가(초록) · 검색 조각인가(조각). 이 교안 저자의 저장소는
    문서에 그 표시를 강제한다.</div>""")
    s.append("<h2>어디서 찾나 (접근 가능성 순)</h2>")
    s.append(표("문헌 접근 경로",
        ["경로", "무엇", "비용"],
        [["<b>arXiv</b>", "프리프린트. 통신·ML·아키텍처가 많다", "무료"],
         ["<b>표준화 기구 공개 디렉터리</b>", "IEEE 802 기고문 등. <b>보물창고</b>", "무료"],
         ["<b>Get IEEE 802</b>", "802 계열 규격 원문", "무료"],
         ["NIST 간행물", "FIPS · SP 800 시리즈", "무료"],
         ["IACR ePrint", "암호 논문 전량", "무료"],
         ["IEEE Xplore · ACM DL", "JSSC · ISSCC · TC 등", "회사/학교 구독"],
         ["회사 내부 위키 · 이전 프로젝트 문서", "<b>가장 관련성 높다</b>", "무료"],
         ["벤더 IP 사양서(PG/PB/데이터시트)", "실제 납품물의 형태", "공개된 것이 많다"]]))
    return "\n".join(s)


def ch_idea():
    s = ['<h1 id="idea">IP 아이디어 &mdash; 무엇을 제안할 것인가</h1>']
    s.append("""<p>&ldquo;IP 아이디어를 생각해 오라&rdquo;는 과제에 대한 실무적 접근.
    <b>새 알고리즘을 제안하는 자리가 아니다.</b> 디자인 하우스가 파는 것은 알고리즘이
    아니라 <b>PPA · 인터페이스 · 검증 · 납품 패키지</b>다.</p>""")
    s.append("""<div class="note"><b>판단 기준 다섯.</b> (1) 표준이 있어 정답이 외부에
    있는가 (2) 수요가 구조적인가(규격이 강제하는가) (3) 우리가 가진 공정/도구로 만들 수
    있는가 (4) 특허가 데이터패스를 막고 있지 않은가 (5) 기존 공개 구현이 있는가 &mdash;
    <b>있으면 기준선이 생기는 것이라 오히려 유리하다.</b></div>""")
    s.append(표("아이디어 후보 &mdash; 표준이 수요를 강제하는 것들",
        ["#", "IP", "왜 수요가 있나", "난이도", "정답의 출처"],
        [["1", "<b>RS-FEC KP4</b> RS(544,514)/GF(2<sup>10</sup>)",
          "100G 이상 이더넷이 <b>규격으로 강제</b>. 800G·1.6T 로 계속 간다",
          "중", "IEEE 802.3 Clause 91/161"],
         ["2", "<b>연접 FEC</b>(외부 RS-KP4 + 내부 Hamming(128,120))",
          "802.3dj(224G/lane)가 2023~24 채택. <b>공개 구현이 안 보인다</b>",
          "중상", "802.3dj 기고문"],
         ["3", "<b>100G+ PCS</b>(멀티레인 분배 · AM · gearbox)",
          "상용은 &lsquo;soft PCS&rsquo; 로 판다. 오픈에는 10G 까지만 있다",
          "중", "IEEE 802.3"],
         ["4", "<b>양자내성 암호(ML-KEM/ML-DSA) 가속기</b>",
          "FIPS 203/204 확정. 모든 RoT 가 넣어야 한다",
          "상", "FIPS 203/204 + Caliptra 참조"],
         ["5", "<b>TRNG + DRBG</b>(SP 800-90A/B)",
          "보안칩 필수. 인증이 까다로워 진입장벽",
          "중상", "NIST SP 800-90 · OpenTitan"],
         ["6", "<b>AXI/CHI 프로토콜 검사기</b>(형식 속성 포함)",
          "모든 SoC 가 필요. 재사용성 최고", "중", "AMBA 규격"],
         ["7", "<b>CDC/리셋 검증 IP</b>", "간헐 버그의 최대 원인", "중", "사내 규칙"],
         ["8", "<b>레지스터맵 단일원천 생성기</b>(IP-XACT &rarr; RTL/UVM/문서/드라이버)",
          "모든 팀이 자체 제작해 쓴다. 표준화 여지", "중", "IEEE 1685"],
         ["9", "<b>ECC 가 붙은 SRAM 래퍼</b>(SECDED · 스크러빙)",
          "안전/보안 요구가 강제(ISO 26262 · FIPS)", "하중", "Hamming/Hsiao 코드"],
         ["10", "<b>MIPI I3C 컨트롤러</b>", "센서 인터페이스 세대교체 중",
          "중", "MIPI 규격(회원)"]]))
    s.append("<h2>제안서에 반드시 들어가야 하는 것</h2>")
    s.append(표("IP 제안서 뼈대",
        ["절", "내용", "빠지면"],
        [["1. 수요", "어느 규격/제품이 이것을 <b>강제</b>하는가", "&lsquo;있으면 좋은 것&rsquo;이 된다"],
         ["2. 선행", "상용 · 오픈 구현을 <b>이름과 규모로</b>. 없다고 쓰지 말 것",
          "이미 있는 것을 만들게 된다"],
         ["3. 차별", "PPA · 파라미터 범위 · 인터페이스 · 검증 패키지 중 무엇으로",
          "&lsquo;더 좋다&rsquo;만 남는다"],
         ["4. 규격 접근", "원문을 구할 수 있는가", "착수 불가"],
         ["5. 특허", "데이터패스 특허를 조사했는가", "팔 수 없는 물건이 된다"],
         ["6. 검증 계획", "정답이 어디서 오는가. 골든 모델은 무엇인가",
          "&lsquo;돌아간다&rsquo;에서 멈춘다"],
         ["7. 규모 추정", "<b>기준선과 비교한</b> 줄 수 · 기간 · 인원",
          "일정이 근거 없이 잡힌다"],
         ["8. 실패 조건", "<b>무엇이 참이면 이 제안이 무효인가</b>",
          "무효화 조건이 없는 주장은 광고다"]]))
    s.append("""<div class="ms"><b>8번이 제안서의 질을 가른다.</b> &ldquo;이 조건에서는
    우리가 진다&rdquo;를 먼저 적은 제안은 신뢰를 얻는다. 예: &ldquo;MATLAB SerDes
    Toolbox + HDL Coder 가 데이터패스까지 RTL 을 생성한다면 이 제안의 3절은 무효다&rdquo;
    &mdash; 이렇게 적고 실제로 확인하는 것이 실무다.</div>""")
    return "\n".join(s)
