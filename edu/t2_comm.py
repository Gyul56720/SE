# -*- coding: utf-8 -*-
"""이론편 II -- 통신, 정보이론과 부호, 링크 설계."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from book import 표, svg그림
from figs import svg, box, txt, arr, line, poly


def _fig_eye():
    b = []
    b.append(line(40, 30, 40, 150)); b.append(line(40, 150, 300, 150))
    for dy in (0, 6, -6, 12, -12):
        b.append(f'<path d="M50,{50+dy} Q110,{50+dy} 170,{120-dy} T290,{50+dy}" '
                 f'stroke="#888" stroke-width="0.8" fill="none"/>')
        b.append(f'<path d="M50,{120-dy} Q110,{120-dy} 170,{50+dy} T290,{120-dy}" '
                 f'stroke="#888" stroke-width="0.8" fill="none"/>')
    b.append(line(170, 40, 170, 150, "3,3"))
    b.append(txt(174, 48, "최적 표본 위상", 8))
    b.append(arr(170, 78, 170, 92)); b.append(arr(170, 92, 170, 78))
    b.append(txt(196, 90, "눈 높이 = 잡음 여유", 8))
    b.append(txt(170, 168, "눈 폭 = 지터 여유", 8, "middle"))
    b.append(txt(170, 195, "눈이 닫히면 등화기가 필요하다 — 채널 손실이 ISI 를 만든다",
                 9, "middle", 'font-style="italic"'))
    return svg(330, 208, "".join(b))


def _fig_link():
    b = []
    블록 = [("TX\nFFE", 30), ("채널", 130), ("CTLE", 230), ("ADC", 320),
            ("FFE", 400), ("DFE", 480), ("슬라이서", 560)]
    for 이름, x in 블록:
        w = 84 if 이름 == "슬라이서" else 76
        b.append(box(x, 40, w, 40, 이름.replace("\n", " "), None, 9))
        if x > 30:
            b.append(arr(x - 24, 60, x, 60))
    b.append(arr(0, 60, 30, 60))
    b.append(arr(644, 60, 680, 60))
    b.append(box(380, 120, 180, 30, "적응 (부호-부호 LMS)", None, 9, "#eef7f2"))
    b.append(arr(470, 120, 440, 80))
    b.append(arr(560, 130, 600, 90))
    b.append(box(200, 120, 120, 30, "CDR", None, 9, "#f4eefa"))
    b.append(arr(260, 120, 300, 85))
    b.append(txt(340, 180, "데이터패스는 심볼률 — 적응과 CDR 은 훨씬 느린 률로 돈다",
                 9, "middle", 'font-style="italic"'))
    return svg(690, 195, "".join(b))


def ch_comm():
    s = ['<h1 id="comm">통신 이론 &mdash; 링크를 설계한다는 것</h1>']
    s.append("<h2>1. 변조: 무엇을 무엇에 싣나</h2>")
    s.append(표("변조 방식과 하드웨어 함의",
        ["방식", "심볼당 비트", "필요 SNR(상대)", "IP 관점"],
        [["NRZ (PAM2)", "1", "기준", "슬라이서 1개. 가장 단순"],
         ["<b>PAM4</b>", "2", "<b>+9.54 dB</b>", "슬라이서 3개. 100G/lane 표준"],
         ["PAM6/PAM8", "2.58/3", "더 나쁨", "802.3 일부. 선형성 요구 급증"],
         ["BPSK", "1", "기준", "무선 기준"],
         ["QPSK", "2", "동일(E<sub>b</sub>/N<sub>0</sub> 기준)", "I/Q 두 채널"],
         ["16/64/256-QAM", "4/6/8", "각 +6 dB/단계", "EVM 요구 급증"],
         ["<b>OFDM</b>", "가변", "&mdash;",
          "IFFT/FFT 필수. PAPR 문제. 주파수선택 채널에 강함"]]))
    s.append("""<div class="ms"><b>PAM4 의 9.54 dB 는 어디서 오나.</b> 레벨을
    &plusmn;1, &plusmn;1/3 로 정규화하면(최대 진폭을 NRZ 와 같게) 인접 레벨 간격이
    2 에서 2/3 로 줄어든다. 오류확률은 최소거리에 걸리므로
    20log<sub>10</sub>(3) = <b>9.54 dB</b> 의 손해다. 대신 같은 보드율로 두 배의 비트를
    나른다. <b>100G/lane 이 PAM4 를 쓰는 이유는 채널이 56 GHz 를 못 통과하기
    때문</b>이다 &mdash; 보드율을 낮추고 진폭 축에서 벌충한다. 이 맞교환이
    <b>FEC 를 필수로 만든 원인</b>이기도 하다.</div>""")

    s.append("<h2>2. 채널과 ISI</h2>")
    s.append(svg그림(_fig_eye(),
        "아이 다이어그램. 채널 손실이 심볼을 퍼뜨려 이웃 심볼에 겹치면(ISI) 눈이 닫힌다."))
    s.append("""<div class="bs"><b>ISI(심볼간 간섭)</b> 는 채널의 임펄스 응답이
    1 심볼보다 길어서 생긴다. 주파수 영역에서 보면 채널이 저역통과라 고주파 성분이
    깎이고, 시간 영역에서는 펄스가 퍼진다. <b>등화(equalization)</b> 는 그 역을
    적용해 펴는 일이다.</div>""")
    s.append(표("등화기 종류",
        ["등화기", "어디에", "원리", "대가"],
        [["<b>TX FFE (pre-emphasis)</b>", "송신", "미리 고주파를 키워 보낸다",
          "송신 전력 여유를 먹는다"],
         ["<b>CTLE</b>", "수신 아날로그", "고주파 부스트 영점",
          "<b>잡음도 같이 키운다</b>"],
         ["<b>RX FFE</b>", "수신 디지털", "FIR 로 역필터",
          "잡음 증폭. pre-cursor 도 제거 가능"],
         ["<b>DFE</b>", "수신 디지털", "<b>이미 판정한 심볼</b>을 빼므로 잡음을 안 키운다",
          "post-cursor 만. <b>오류 전파</b>. 1 UI 안에 닫혀야 함"],
         ["MLSE / Viterbi", "수신", "최우 수열 추정", "복잡도 지수적"]]))
    s.append("""<div class="ms"><b>DFE 의 1 UI 되먹임 제약이 아키텍처를 정한다.</b>
    첫 탭은 <i>직전 심볼의 판정</i>이 필요하므로, 슬라이서 &rarr; 합산 &rarr; 다음 슬라이서
    경로가 <b>1 심볼 주기 안에</b> 닫혀야 한다. 56 GBd 면 1 UI = 17.86 ps 다.
    래치 지연 + 합산기 + 배선 + 셋업만으로 이 예산을 넘긴다. 그래서 <b>투기적 언롤</b>
    (직전 심볼의 모든 경우를 미리 계산해 두고 판정 결과로 먹스만 고름)과
    <b>sub-rate 병렬화</b>(여러 위상으로 나눠 각 경로의 주기를 늘림)를 쓴다.
    <b>등화기 IP 의 난이도는 수학이 아니라 이 타이밍 예산에서 온다.</b></div>""")

    s.append("<h2>3. 동기 &mdash; CDR</h2>")
    s.append(표("CDR 방식",
        ["방식", "원리", "특징"],
        [["<b>Bang-Bang (Alexander)</b>", "데이터와 엣지를 함께 샘플, 부호만",
          "구현 단순. 지터 전달이 비선형"],
         ["<b>Mueller-Müller</b>", "보드율 샘플만으로 타이밍 오차 추정",
          "<b>2배 오버샘플 불필요</b> &mdash; ADC 기반 수신기의 표준"],
         ["Gardner", "2배 오버샘플, 심볼 무관", "무선에서 흔함"],
         ["초과샘플링", "3~8배 샘플 후 다수결", "저속. OpenSERDES 가 이 방식"]]))
    s.append("""<div class="ms"><b>지터 전달과 지터 허용.</b> CDR 은 2차 루프로
    모델링되며 <b>루프 대역폭</b>이 핵심 파라미터다. 대역폭이 넓으면 입력 지터를 잘
    따라가지만(지터 허용 &uarr;) 그 지터를 출력으로 <b>전달</b>한다. 좁으면 반대다.
    규격(예: PCIe · 802.3)은 <b>지터 전달 마스크</b>와 <b>지터 허용 마스크</b>를 동시에
    규정하므로, 루프 대역폭은 두 제약 사이의 창에 들어가야 한다.
    <b>모델에서 CDR 을 &lsquo;이상적 타이밍&rsquo;으로 두면 이 사양을 전혀 검증하지
    못한다</b> &mdash; 별도의 지터 모델이 필요하고, 그것이 시스템 모델링 팀의 일이다.</div>""")
    s.append(svg그림(_fig_link(),
        "ADC-DSP 기반 고속 수신기의 전형. 데이터패스와 적응/CDR 이 다른 률로 돈다."))

    s.append("<h2>4. 링크 예산</h2>")
    s.append(표("유선 링크 예산 항목 (SerDes 기준)",
        ["항목", "단위", "설명"],
        [["삽입손실 IL", "dB@Nyq", "채널이 깎는 양. 30 dB 급이 롱리치"],
         ["반사 RL/ILD", "dB", "임피던스 불연속. 커넥터·비아"],
         ["크로스토크 NEXT/FEXT", "dB", "이웃 레인 간섭"],
         ["송신 지터 (RJ/DJ)", "ps", "무작위/결정론 분리"],
         ["<b>COM</b>", "dB", "<b>Channel Operating Margin</b> &mdash; 802.3 의 통합 지표"],
         ["pre-FEC BER", "&mdash;", "슬라이서가 내는 값. KP4 면 ~2e&minus;4 가 문턱"],
         ["post-FEC BER/FLR", "&mdash;", "최종 요구. 10<sup>&minus;15</sup> 급"]]))
    s.append("""<div class="warn"><b>&ldquo;BER 10<sup>&minus;12</sup>&rdquo; 는 낡은
    요구다.</b> FEC 이전 세대(10G/25G NRZ)의 기준이고, 100G/lane 이상에서는
    <b>pre-FEC BER 이 10<sup>&minus;4</sup> 수준</b>이어도 정상이다. 등화기 성능을
    평가할 때 기준을 잘못 잡으면 &ldquo;우리 등화기가 규격 미달&rdquo; 또는 반대로
    &ldquo;여유가 넘친다&rdquo;는 틀린 결론이 나온다. <b>판정 기준은 항상
    pre-FEC BER 대 FEC 문턱이다.</b></div>""")
    return "\n".join(s)


def ch_coding():
    s = ['<h1 id="coding">정보이론과 오류정정 부호</h1>']
    s.append("<h2>1. 용량과 한계</h2>")
    s.append("""<div class="math">C = B log<sub>2</sub>(1 + SNR) &nbsp;&nbsp;[bit/s]
    &nbsp;&nbsp;&nbsp;(샤넌&ndash;하틀리)</div>""")
    s.append("""<div class="ms"><b>이 식이 IP 설계에 주는 것.</b> 채널 용량은
    &ldquo;어떤 부호로도 이 이상은 못 보낸다&rdquo;는 상한이다. 설계 회의에서
    &ldquo;부호를 더 좋게 하면 되지 않나&rdquo;라는 요구가 나올 때, 현재 동작점이
    용량에서 얼마나 떨어져 있는지를 계산해 보이면 논쟁이 끝난다. 현대 부호(LDPC·터보·극
    부호)는 <b>용량에서 0.1&ndash;1 dB 이내</b>까지 와 있으므로, 남은 이득은 대개
    <b>부호가 아니라 등화·동기·구현손실</b>에 있다.</div>""")
    s.append(표("주요 부호와 특성",
        ["부호", "구조", "복호", "쓰이는 곳"],
        [["<b>해밍/SECDED</b>", "선형 블록", "신드롬",
          "<b>메모리 ECC</b>. 1비트 정정 2비트 검출"],
         ["BCH", "순회", "BM + Chien", "플래시 · 광통신"],
         ["<b>RS(리드-솔로몬)</b>", "비이진 순회, GF(2<sup>m</sup>)",
          "신드롬&rarr;BM&rarr;Chien&rarr;Forney",
          "<b>이더넷 KP4</b> · 저장장치 · 방송"],
         ["합성곱", "상태기계", "<b>Viterbi</b>", "레거시 무선 · 위성"],
         ["터보", "병렬 연접 + 인터리버", "BCJR 반복", "3G/4G"],
         ["<b>LDPC</b>", "희소 패리티검사 행렬", "신뢰전파(min-sum)",
          "<b>5G NR</b> · Wi-Fi · 802.3ca"],
         ["<b>극(Polar)</b>", "채널 분극", "SC / SCL", "5G 제어채널"],
         ["<b>연접(concatenated)</b>", "외부 RS + 내부 이진",
          "내부&rarr;외부 순차", "<b>802.3dj 224G</b>"]]))

    s.append("<h2>2. RS 부호 &mdash; 왜 하드웨어에 잘 맞나</h2>")
    s.append("""<div class="bs">RS 는 <b>심볼 단위</b> 부호다. GF(2<sup>m</sup>) 의
    한 원소(= m 비트)가 한 심볼이고, t 심볼까지 정정한다. <b>한 심볼 안에서 몇 비트가
    틀렸든 한 개로 센다</b> &mdash; 그래서 <b>버스트 오류에 강하다</b>.</div>""")
    s.append("""<div class="ms"><b>왜 PAM4 링크가 RS 를 쓰는가.</b> PAM4 슬라이서가
    틀릴 때 이웃 레벨로 틀리므로 그레이 부호에서는 1비트 오류지만, <b>DFE 오류 전파</b>나
    <b>버스트 잡음</b>이 있으면 연속 심볼이 함께 틀린다. 심볼 단위 정정이 그 구조에
    맞는다. 또 GF(2<sup>10</sup>) 이면 한 심볼이 10비트 = PAM4 다섯 심볼이므로
    정렬이 자연스럽다. <b>부호 선택은 채널의 오류 &lsquo;모양&rsquo;을 보고 한다</b> &mdash;
    랜덤 비트 오류면 이진 부호, 버스트면 비이진 부호.</div>""")
    s.append(표("RS 복호기 설계 파라미터",
        ["파라미터", "영향", "전형값(KP4)"],
        [["m (필드 크기)", "심볼 폭, 곱셈기 크기", "10"],
         ["n, k", "부호율 = k/n", "544, 514 &rarr; 94.5%"],
         ["t = (n&minus;k)/2", "정정 능력", "15 심볼"],
         ["병렬도 P", "처리량 = P 심볼/사이클", "레인당 요구에 맞춤"],
         ["BM 변형", "임계경로", "inversionless / reformulated"],
         ["Chien 병렬도", "지연", "n/P 사이클"],
         ["인터리빙 깊이", "버스트 내성", "802.3 은 4레인 인터리브"]]))

    s.append("<h2>3. LDPC &mdash; 반복 복호의 구조</h2>")
    s.append("""<div class="bs">LDPC 는 <b>희소한</b> 패리티검사 행렬 <b>H</b> 로
    정의된다. 복호는 변수노드와 검사노드가 <b>신뢰도(LLR)</b>를 주고받는 반복
    메시지 전달이다.</div>""")
    s.append("""<div class="math">L(x) = log( P(x=0) / P(x=1) )</div>""")
    s.append(표("LDPC 복호 방식",
        ["방식", "정확도", "복잡도", "비고"],
        [["합-곱(SPA)", "최적에 가까움", "tanh 필요. 비쌈", "기준"],
         ["<b>min-sum</b>", "약간 손실", "최소값+부호만",
          "<b>하드웨어 표준</b>"],
         ["정규화/오프셋 min-sum", "손실 대부분 회복", "상수 곱/뺄셈 하나", "실무 선택"],
         ["<b>계층(layered)</b> 스케줄", "수렴 반복수 절반",
          "층 간 의존 &rarr; 파이프라인 해저드", "면적 효율 최고"]]))
    s.append("""<div class="ms"><b>계층 복호의 파이프라인 해저드.</b> 층 <i>i</i> 가
    갱신한 변수노드를 층 <i>j</i> 가 곧바로 읽으면, 파이프라인 깊이 D 만큼 기다려야 한다.
    층 순서를 바꾸면 대기(stall)가 줄어든다 &mdash; <b>조합 최적화 문제</b>다.
    주의할 점: 단순한 조합 공식으로 계산한 스톨 수는 <b>상한</b>일 뿐이고, 실제
    사이클 정확 모델과 다를 수 있다. 저자의 실측에서 BG1, D=4 일 때 공식은 108, 사이클
    모델과 RTL 은 <b>80</b> 이었다(손실 70.1% &rarr; 62.0%). <b>스케줄 최적화의 목적함수를
    공식으로 두면 잘못된 해를 찾는다.</b> 반드시 사이클 정확 모델로 재라.</div>""")
    s.append("""<div class="warn"><b>LDPC 의 고정소수점은 RS 와 반대다.</b> LLR 은
    부호가 확률 판정을 뜻하므로 <b>감싸기(wrap)가 부호를 뒤집으면 복호가 붕괴</b>한다.
    반드시 <b>포화</b>해야 한다. 저자의 실측: 폭을 3비트 줄였을 때 포화는 BLER 0.250,
    감싸기는 1.000 이었다. 반면 등화기 데이터패스는 감싸기가 안전한 경우가 많다 &mdash;
    <b>같은 &lsquo;고정소수점&rsquo;이라도 블록마다 규칙이 반대다.</b></div>""")

    s.append("<h2>4. Viterbi &mdash; 상태기계 복호</h2>")
    s.append("""<p>합성곱 부호의 최우 복호. 상태 수 2<sup><i>K</i>&minus;1</sup>
    (K = 구속장) 의 트렐리스에서 최단 경로를 찾는다. 하드웨어는 세 블록이다.</p>""")
    s.append(표("Viterbi 복호기의 세 블록",
        ["블록", "하는 일", "병목"],
        [["BMU (가지 척도)", "수신값과 각 가지의 거리", "병렬화 쉬움"],
         ["<b>ACS (덧셈-비교-선택)</b>", "경로 척도 갱신",
          "<b>되먹임 고리 &mdash; 임계경로</b>. 여기가 속도를 정한다"],
         ["SMU (생존 경로)", "역추적 또는 레지스터 교환", "메모리 대역"]]))
    s.append("""<div class="ms"><b>ACS 고리를 푸는 표준 기법이 &lsquo;radix-4&rsquo;
    와 &lsquo;retiming&rsquo;</b> 이다. radix-4 는 두 스텝을 한 번에 처리해 고리를
    절반의 빈도로 돌린다(면적 증가). 이것은 DFE 의 <b>투기적 언롤</b>, RS 의
    <b>reformulated BM</b> 과 <b>같은 문제에 대한 같은 해법</b>이다 &mdash;
    <i>되먹임 고리의 논리 깊이를 줄이거나 고리를 도는 빈도를 낮춘다.</i>
    <b>이 패턴을 알아보면 처음 보는 블록도 어디가 병목인지 바로 짚는다.</b></div>""")
    return "\n".join(s)
