# -*- coding: utf-8 -*-
"""제3부 -- IP 블록별 교안: AES."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from book import 표, svg그림, 토막, 줄수, E
import figs_aes


def aes():
    s = ['<h1 id="aes">AES 블록 &mdash; 암호 IP 의 표준 사례</h1>']
    rtl = 줄수('ip', 'opentitan/hw/ip/aes/rtl')
    s.append(f"""<div class="kvbar"><b>표준</b> FIPS&#8209;197 (NIST, 2001) &nbsp;&bull;&nbsp;
    <b>블록</b> 128비트 &nbsp;&bull;&nbsp; <b>키</b> 128/192/256비트 &nbsp;&bull;&nbsp;
    <b>라운드</b> 10/12/14 &nbsp;&bull;&nbsp;
    <b>이 교안의 실물</b> C 골든 573줄 · HLS C++ 1,011줄 · 양산 RTL {rtl:,}줄</div>""")

    # ---------------------------------------------------------------- 1
    s.append("<h2>1. 왜 AES 를 먼저 배우나</h2>")
    s.append("""<p>AES 는 IP 교육의 표준 예제다. 이유가 네 가지다.</p>
    <ol>
    <li><b>정답이 공개돼 있다.</b> NIST 가 시험 벡터를 낸다. 맞고 틀림에 이견이 없다</li>
    <li><b>알고리즘이 작다.</b> 라운드 함수 네 개가 전부다</li>
    <li><b>그런데 실제 IP 는 크다.</b> 30배 차이가 어디서 오는지가 곧 &lsquo;IP 란
        무엇인가&rsquo;에 대한 답이다</li>
    <li><b>거의 모든 칩에 들어간다.</b> 보안 부트 · 저장장치 암호화 · 통신 링크</li>
    </ol>""")

    # ---------------------------------------------------------------- 2
    s.append("<h2>2. 수학 &mdash; GF(2<sup>8</sup>) 위에서 도는 암호</h2>")
    s.append("""<div class="bs">AES 의 모든 산술은 <b>유한체 GF(2<sup>8</sup>)</b> 에서
    일어난다. 원소는 바이트 하나(0&ndash;255)이고, 각 바이트를 <b>7차 이하 다항식의
    계수</b>로 읽는다. 예를 들어 <code>0x57 = 0101&nbsp;0111</code> 은
    <i>x</i><sup>6</sup>+<i>x</i><sup>4</sup>+<i>x</i><sup>2</sup>+<i>x</i>+1 이다.</div>""")
    s.append("""<p><b>덧셈</b>은 계수별 XOR 이다. 표수 2 이므로 덧셈과 뺄셈이 같다.
    <b>곱셈</b>은 다항식 곱 뒤 기약다항식으로 나눈 나머지를 취한다. AES 가 정한
    기약다항식은</p>
    <div class="math">m(x) = x<sup>8</sup> + x<sup>4</sup> + x<sup>3</sup> + x + 1
    &nbsp;&nbsp;(0x11B)</div>
    <p>구현에서는 <code>x</code> 를 곱하는 연산(<code>xtime</code>)만 있으면 임의 곱셈을
    만들 수 있다. 골든 모델의 실물은 이렇다.</p>""")
    s.append(토막('model', 'kokke_tiny-AES-c/aes.c', 294, 297,
                  'x 를 곱한다 -- 왼쪽 시프트, 넘치면 0x1B 로 환원'))
    s.append("""<div class="ms"><b>왜 <code>0x1b</code> 인가.</b> 기약다항식 0x11B 에서
    최고차항 <i>x</i><sup>8</sup>(=0x100)을 뺀 나머지가 0x1B 다. 왼쪽 시프트로 8비트를
    넘으면 <i>x</i><sup>8</sup> 항이 생기는데, 그것을
    <i>x</i><sup>4</sup>+<i>x</i><sup>3</sup>+<i>x</i>+1 로 바꿔 더하는 것이 곧
    <code>^ 0x1b</code> 다. <b>조건부를 쓰지 않고 곱셈으로 쓴 것</b>(<code>* 0x1b</code>)에
    주목하라 &mdash; 분기를 없애 <i>실행 시간이 데이터에 의존하지 않게</i> 한 것이다.
    타이밍 부채널 대책의 가장 기초적인 형태다.</div>""")

    s.append("<h3>2.1 S-box &mdash; 표가 아니라 두 연산의 합성이다</h3>")
    s.append("""<p>S-box 는 256바이트 표로 주어지지만, <b>표는 정의가 아니라 계산 결과</b>다.
    정의는 이렇다.</p>
    <div class="math">S(a) = A &middot; a<sup>&minus;1</sup> &oplus; b</div>
    <p>즉 (i) GF(2<sup>8</sup>) 에서의 <b>곱셈 역원</b>을 구하고(0은 0으로), (ii) 비트에
    대한 <b>아핀 변환</b>(고정 행렬 A 와 상수 b=0x63)을 적용한다.</p>""")
    s.append("""<div class="ms"><b>이 구분이 하드웨어에서 결정적이다.</b> 표로 두면
    256바이트 ROM 하나다 &mdash; 작고 빠르다. 그런데 <b>표 참조는 마스킹할 수 없다.</b>
    부채널 대책으로 값을 난수로 가리려면(<i>x</i> 대신 <i>x</i>&oplus;<i>m</i> 을 들고
    다니려면), 연산이 그 마스킹과 <i>호환</i>되어야 한다. 표 참조는 호환되지 않는다 &mdash;
    <i>S</i>(<i>x</i>&oplus;<i>m</i>) 은 <i>S</i>(<i>x</i>) 와 아무 관계가 없다.
    그래서 <b>역원을 산술로 다시 쓴다.</b></div>""")
    s.append(svg그림(figs_aes.탑필드(),
        "S-box 를 표로 두느냐 산술로 분해하느냐. Canright 의 탑 필드(tower field) 분해는 "
        "GF(2<sup>8</sup>) 역원을 GF(2<sup>4</sup>), GF(2<sup>2</sup>) 연산으로 내린다. "
        "느리고 크지만 <b>마스킹할 수 있다</b>."))
    s.append("""<p>OpenTitan 의 AES 는 <b>S-box 구현을 여섯 벌</b> 가지고 있다. 파라미터로
    고른다.</p>""")
    s.append(표("OpenTitan AES 의 S-box 구현 여섯 가지 (실측 줄 수)",
        ["파일", "줄", "방식", "언제 고르나"],
        [["<code>aes_sbox_lut.sv</code>", "120", "평범한 256바이트 표",
          "부채널이 위협이 아닐 때. 가장 작고 빠르다"],
         ["<code>aes_sbox_canright.sv</code>", "70", "탑 필드 분해, 마스킹 없음",
          "면적을 줄이고 싶을 때(표보다 작을 수 있다)"],
         ["<code>aes_sbox_canright_masked.sv</code>", "486", "탑 필드 + 1차 마스킹",
          "부채널 대책이 필요할 때"],
         ["<code>aes_sbox_canright_masked_noreuse.sv</code>", "450",
          "마스크 재사용을 막은 판", "재사용이 누설을 만든다는 분석 이후의 판"],
         ["<code>aes_sbox_dom.sv</code>", "<b>1,077</b>",
          "Domain-Oriented Masking", "<b>가장 강한 대책.</b> 가장 크다"],
         ["<code>aes_sbox.sv</code>", "144", "위를 고르는 래퍼", "&mdash;"]]))
    s.append("""<div class="warn"><b>같은 함수를 아홉 배 크기로 다시 쓰는 것</b>이
    보안 IP 의 현실이다. <code>aes_sbox_lut.sv</code> 120줄 대
    <code>aes_sbox_dom.sv</code> 1,077줄. 수학적으로 둘은 <b>완전히 같은 함수</b>다.
    모델은 둘을 구분하지 않는다 &mdash; <b>모델은 부채널을 검증할 수 없다.</b> 그것은
    별도의 평가(TVLA · 전력 측정)로 간다. <b>모델링 팀이 이 경계를 알고 있어야 한다:
    &ldquo;회귀 초록 = 안전&rdquo; 이 아니다.</b></div>""")

    s.append("<h3>2.2 ShiftRows 와 MixColumns</h3>")
    s.append("""<p><b>ShiftRows</b> 는 상태 행렬의 <i>r</i>번째 행을 왼쪽으로 <i>r</i>바이트
    순환시킨다. <b>하드웨어에서는 배선만 바뀐다 &mdash; 논리 게이트가 0개다.</b>
    모델에서는 루프가 도니 비용이 있어 보이지만, 실제로는 공짜다. 모델의 줄 수가
    하드웨어 비용을 말해 주지 않는 좋은 예다.</p>
    <p><b>MixColumns</b> 는 각 열을 GF(2<sup>8</sup>) 위의 고정 다항식과 곱한다.</p>
    <div class="math">c(x) = 03&middot;x<sup>3</sup> + 01&middot;x<sup>2</sup>
    + 01&middot;x + 02 &nbsp;&nbsp;(mod x<sup>4</sup>+1)</div>""")
    s.append(토막('model', 'kokke_tiny-AES-c/aes.c', 300, 313, 'MixColumns 골든'))
    s.append("""<div class="ms">계수가 <b>02 와 03 뿐</b>인 것이 설계다.
    02 곱은 <code>xtime</code> 한 번, 03 곱은 <code>xtime</code> 한 번 + XOR 한 번이다.
    그래서 곱셈기가 필요 없다 &mdash; <b>시프트와 XOR 만으로 끝난다.</b> 위 골든 코드가
    <code>Tmp</code>(열 전체 XOR)를 한 번 계산해 네 번 재사용하는 것도 같은 이유다.
    AES 는 <i>처음부터 하드웨어를 보고 설계된 암호</i>이고, 이것이 Rijndael 이 표준으로
    뽑힌 이유 중 하나다.</div>""")
    s.append(svg그림(figs_aes.라운드(),
        "AES 한 라운드. 네 단계 중 <b>논리 게이트를 쓰는 것은 SubBytes 와 MixColumns 뿐</b>"
        "이다. ShiftRows 는 배선, AddRoundKey 는 XOR 128개."))

    # ---------------------------------------------------------------- 3
    s.append("<h2>3. 세 구현을 나란히 읽는다</h2>")
    s.append(표("같은 AES, 세 팀, 세 언어",
        ["", "C 골든모델", "HLS C++", "양산 RTL"],
        [["저장소", "<code>kokke/tiny-AES-c</code>",
          "AMD Vitis Security Library", "<code>lowRISC/opentitan</code>"],
         ["줄 수", "573", "1,011", f"<b>{rtl:,}</b>"],
         ["쓰는 팀", "모델링 · DV", "FPGA 가속 설계", "디자인"],
         ["S-box", "<code>static const uint8_t sbox[256]</code>",
          "<code>#pragma HLS resource ... ROM_nP_LUTRAM</code>", "구현 6가지 중 선택"],
         ["병렬성", "없음(순차)", "<code>UNROLL</code> 15 · <code>PIPELINE</code> 8",
          "라운드당 1사이클 ~ 완전 언롤까지 파라미터"],
         ["부채널", "고려 안 함", "고려 안 함", "<b>DOM 마스킹 · PRNG</b>"],
         ["고장주입", "고려 안 함", "고려 안 함", "<b>FSM 이중화 · 상보 논리</b>"],
         ["버스", "함수 인자", "<code>hls::stream</code> / AXI", "TL-UL + 섀도우 레지스터"],
         ["검증", "NIST 벡터", "C 시뮬레이션", "UVM + 형식 + 부채널 평가"]]))
    s.append("""<div class="note"><b>모델링 팀 관점의 요점.</b> 왼쪽 열이 당신의
    산출물이다. 573줄이지만 <b>오른쪽 두 열의 정답을 정의한다.</b> 그래서 왼쪽 열에서
    실수하면 아무도 못 잡는다 &mdash; 오른쪽이 왼쪽에 맞춰지기 때문이다. 이것이
    3장에서 말한 <i>모델 자체의 검증</i>이 필요한 이유다. AES 는 다행히 NIST 벡터가
    있어 외부 정답이 존재한다. <b>사내 알고리즘에는 그것이 없다.</b></div>""")

    # ---------------------------------------------------------------- 4
    s.append("<h2>4. 물리 &mdash; RTL 에만 있는 세계</h2>")
    s.append("<h3>4.1 부채널: 전력이 비밀을 말한다</h3>")
    s.append("""<div class="bs">CMOS 회로는 비트가 <b>바뀔 때</b> 전류를 쓴다. 그래서
    소비 전력이 내부 값에 의존한다. 공격자가 칩의 전원선에 저항 하나를 달고 수천 번의
    암호화를 측정하면, 통계로 키 바이트를 하나씩 복원할 수 있다 &mdash;
    <b>차분 전력 분석(DPA)</b>.</div>""")
    s.append("""<div class="ms"><b>마스킹의 원리.</b> 비밀 <i>x</i> 를 직접 들고 다니지
    않고, 난수 <i>m</i> 으로 쪼개 (<i>x</i>&oplus;<i>m</i>, <i>m</i>) 두 몫으로 들고 다닌다.
    각 몫은 <i>x</i> 와 통계적으로 독립이므로 1차 누설이 사라진다. 문제는
    <b>비선형 연산</b>이다. XOR 은 몫별로 따로 해도 되지만, 곱셈은 몫을 섞어야 하고 그
    과정에서 중간값이 잠깐 <i>x</i> 에 의존할 수 있다(글리치).
    <b>Domain-Oriented Masking(DOM)</b> 은 몫을 &lsquo;도메인&rsquo;으로 나누고 도메인을
    넘는 곱에 <b>새 난수를 더한 뒤 레지스터로 끊어</b> 글리치 전파를 막는다.
    <code>aes_sbox_dom.sv</code> 가 1,077줄인 이유고, <code>aes_prng_masking.sv</code> 가
    필요한 이유다 &mdash; <b>마스킹은 난수를 계속 먹는다.</b></div>""")
    s.append(표("부채널 대책의 대가 (OpenTitan AES 실측 줄 수 기준)",
        ["항목", "LUT S-box", "DOM S-box", "배수"],
        [["줄 수", "120", "1,077", "<b>9.0배</b>"],
         ["난수 소모", "없음", "S-box 호출마다", "&mdash;"],
         ["지연", "조합논리 1단", "레지스터 여러 단", "파이프라인 깊어짐"],
         ["검증", "NIST 벡터로 충분", "<b>+ TVLA 전력 평가 필요</b>", "&mdash;"]]))

    s.append("<h3>4.2 고장 주입: 레이저와 전압 글리치</h3>")
    s.append("""<div class="bs">공격자가 칩에 레이저를 쏘거나 전원을 순간적으로 흔들어
    플립플롭 하나를 뒤집으면, 라운드 카운터가 건너뛰어 <b>암호화가 덜 된 상태로 출력</b>될
    수 있다. 그런 출력 한두 개면 키가 복원된다(차분 고장 분석, DFA).</div>""")
    s.append(svg그림(figs_aes.이중화FSM(),
        "OpenTitan 의 제어 FSM 이중화. 같은 FSM 을 정논리와 부논리로 두 벌 돌리고 "
        "상보성을 검사한다."))
    s.append(토막('ip', 'lowRISC_opentitan/hw/ip/aes/rtl/aes_cipher_control_fsm_n.sv',
                  7, 13, '왜 부논리 판을 따로 두는가 -- RTL 주석 원문'))
    s.append("""<div class="ms"><b><code>prim_buf</code> 합성 장벽</b>에 주목하라.
    인버터를 그냥 넣으면 합성기가 &ldquo;<code>!!x = x</code>&rdquo; 라며 없애 버리고
    두 FSM 이 같은 회로로 병합된다. 그러면 이중화가 사라지는데 <b>기능 검증은 통과한다</b>.
    그래서 합성기가 넘지 못하는 장벽을 세운다. <b>이것은 RTL 코드가 아니라 합성 제약의
    문제이고, 모델에는 대응물이 전혀 없다.</b> 모델링 팀이 이 영역을 &lsquo;내 일이
    아니다&rsquo;라고 알아 두는 것이 중요하다 &mdash; 모르면 왜 RTL 이 그렇게 이상하게
    생겼는지 설명이 안 된다.</div>""")

    s.append("<h3>4.3 섀도우 레지스터와 키 삭제</h3>")
    s.append(표("양산 보안 IP 에만 있는 블록들 (OpenTitan AES)",
        ["파일", "줄", "하는 일", "모델에 대응물이"],
        [["<code>aes_ctrl_reg_shadowed.sv</code>", "&mdash;",
          "제어 레지스터를 두 벌 두고 두 번 써야 반영. 글리치로 설정이 바뀌는 것을 막는다",
          "없음"],
         ["<code>aes_prng_clearing.sv</code>", "&mdash;",
          "키·상태를 0 이 아니라 <b>난수로</b> 덮는다. 0 으로 덮으면 잔류 전하로 읽힐 수 있다",
          "없음"],
         ["<code>aes_prng_masking.sv</code>", "151", "마스킹용 난수 공급", "없음"],
         ["<code>aes_reg_top.sv</code>", "&mdash;", "TL-UL 버스 &rarr; 레지스터맵", "함수 인자"],
         ["<code>aes_ghash.sv</code>", "&mdash;", "GCM 모드의 GF(2<sup>128</sup>) 곱",
          "모드는 대개 소프트웨어"]]))

    # ---------------------------------------------------------------- 5
    s.append("<h2>5. 검증 &mdash; 이 블록을 어떻게 맞다고 말하나</h2>")
    s.append(표("AES 검증 층위",
        ["층위", "무엇으로", "무엇을 잡나", "못 잡는 것"],
        [["NIST 시험 벡터(KAT)", "FIPS-197 부록 · NIST CAVP",
          "기능 오류. <b>여기서 틀리면 나머지는 볼 필요 없다</b>",
          "경계 조건 · 상태 전이"],
         ["제약 랜덤 + 골든 비교", "UVM + C 모델",
          "모드 전환 · 키 변경 · 백투백 · 중단",
          "부채널 · 고장"],
         ["형식 검증", "속성(assertion) 증명",
          "FSM 도달 불가 상태 · 데드락 · 레지스터 접근 규칙",
          "데이터패스 전체(상태공간이 너무 크다)"],
         ["부채널 평가", "TVLA · 전력 측정",
          "마스킹 결함 · 글리치 누설", "기능 오류"],
         ["고장 주입 시뮬", "게이트 레벨 플립 주입",
          "이중화가 실제로 잡는지", "물리적 레이저 특성"]]))
    s.append("""<div class="note"><b>모델링 팀이 담당하는 것은 위 두 층이다.</b>
    NIST 벡터를 모델에 먹여 통과시키고, 그 모델을 DV 가 RTL 과 맞댄다. 아래 세 층은
    각각 형식검증팀 · 보안평가팀 · DFT/신뢰성팀이 본다. <b>그런데 &ldquo;우리 AES 는
    검증됐다&rdquo;는 말이 어느 층을 뜻하는지 늘 물어야 한다.</b></div>""")

    s.append("<h2>6. 이 블록에서 가져갈 일반 원리</h2>")
    s.append(표("AES 에서 배운 것이 다른 블록에도 적용된다",
        ["원리", "AES 에서", "다른 곳에서"],
        [["정답은 외부에서 온다", "NIST KAT", "IEEE 규격 벡터 · 표준 적합성 시험"],
         ["표는 정의가 아니라 결과다", "S-box = 역원 + 아핀",
          "모든 LUT 는 원래 계산이 있다. 그 계산이 최적화의 여지다"],
         ["같은 함수, 여러 회로", "S-box 6가지", "곱셈기 · 나눗셈기 · CORDIC · 정렬망"],
         ["모델이 못 보는 층이 있다", "부채널 · 고장",
          "타이밍 · 전력 · EMI · 노화. <b>기능 회귀 초록 &ne; 출하 가능</b>"],
         ["파라미터가 곧 제품군이다", "키 길이 · S-box 선택 · 언롤",
          "하나의 소스로 여러 PPA 점을 판다. 이것이 IP 비즈니스다"]]))
    return "\n".join(s)
