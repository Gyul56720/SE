# -*- coding: utf-8 -*-
"""이론편 I -- 신호 및 시스템, 확률, DSP."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from book import 표, svg그림
from figs import svg, box, txt, arr, line, poly
import math


def _fig_lti():
    b = [box(190, 40, 150, 46, "LTI 시스템", "h[n]", 10)]
    b.append(arr(60, 63, 190, 63)); b.append(txt(62, 55, "x[n]", 10))
    b.append(arr(340, 63, 470, 63)); b.append(txt(400, 55, "y[n] = (x * h)[n]", 10))
    b.append(txt(265, 118, "시간불변 + 선형  ⇒  임펄스응답 하나가 시스템 전부를 정한다",
                 9, "middle", 'font-style="italic"'))
    b.append(txt(265, 140, "Y(z) = H(z)·X(z)    —  합성곱이 곱셈이 된다", 10, "middle"))
    return svg(520, 155, "".join(b))


def _fig_sample():
    b = []
    b.append(txt(20, 22, "원신호 대역 B", 9))
    for k, lab in ((0, "0"), (150, "f_s"), (300, "2f_s")):
        b.append(poly([(60+k-38, 78), (60+k, 38), (60+k+38, 78)], arrow=False))
        b.append(txt(60+k, 92, lab, 9, "middle"))
    b.append(line(20, 78, 420, 78))
    b.append(txt(20, 118, "f_s > 2B 이면 복제본이 겹치지 않는다 — 나이퀴스트", 9))
    b.append(txt(20, 136, "겹치면 되돌릴 수 없다: 에일리어싱은 정보 손실이다", 9,
                 "start", 'fill="#a33"'))
    return svg(440, 150, "".join(b))


def ch_lti():
    s = ['<h1 id="lti">신호와 시스템 &mdash; 모든 DSP IP 의 바닥</h1>']
    s.append("""<p>하드웨어 IP 를 설계하든 모델링하든, 다루는 대상은 <b>신호</b>이고
    만드는 것은 <b>시스템</b>이다. 이 장은 그 언어를 정리한다. 이미 아는 내용이라도
    <b>&lsquo;하드웨어에서 무엇을 뜻하는가&rsquo;</b>를 함께 보라 &mdash; 그것이 교과서와
    실무를 잇는 다리다.</p>""")

    s.append("<h2>1. 선형 시불변(LTI) 시스템</h2>")
    s.append("""<div class="bs">시스템 <i>T</i>{&middot;} 가
    <b>선형</b>(중첩이 성립: <i>T</i>{<i>ax</i><sub>1</sub>+<i>bx</i><sub>2</sub>}
    = <i>aT</i>{<i>x</i><sub>1</sub>}+<i>bT</i>{<i>x</i><sub>2</sub>})이고
    <b>시불변</b>(입력을 미루면 출력도 그만큼 미뤄짐)이면 LTI 라 한다.
    LTI 시스템은 <b>임펄스 응답 <i>h</i>[<i>n</i>] 하나로 완전히 결정</b>된다.</div>""")
    s.append("""<div class="math">y[n] = &sum;<sub>k</sub> x[k] h[n&minus;k]
    &equiv; (x * h)[n]</div>""")
    s.append(svg그림(_fig_lti(),
        "LTI 시스템과 합성곱. 변환 영역에서 합성곱은 곱셈이 되며, 이 성질이 "
        "필터 설계 · FFT 가속 · 등화기 이론 전부의 출발점이다."))
    s.append("""<div class="ms"><b>하드웨어에서 LTI 가 뜻하는 것.</b> LTI 이면
    &ldquo;계수 <i>h</i>[<i>k</i>]&rdquo; 만 저장하면 되고, 연산은 곱-누산(MAC)의 합이다.
    그래서 FIR 필터는 <b>MAC 배열 + 지연선</b> 이라는 단일 구조로 환원된다.
    <b>비선형이거나 시변이면 이 환원이 깨진다</b> &mdash; 예를 들어 판정 되먹임
    등화기(DFE)는 슬라이서(비선형) 때문에 LTI 가 아니고, 그래서 중첩 원리로 해석할 수
    없으며 오류 전파(error propagation)라는 고유 현상이 생긴다. <b>모델링에서
    &ldquo;LTI 인가&rdquo;를 먼저 묻는 습관이 중요하다.</b></div>""")

    s.append("<h2>2. 변환 &mdash; 왜 셋이나 있나</h2>")
    s.append(표("네 가지 변환과 쓰임",
        ["변환", "정의역", "핵심 성질", "IP 설계에서"],
        [["<b>푸리에 (DTFT/DFT)</b>", "이산시간 &rarr; 주파수",
          "합성곱 &rarr; 곱, 파시발 등식",
          "스펙트럼 해석 · FFT 블록 · 채널 응답"],
         ["<b>Z 변환</b>", "이산시간 &rarr; 복소 <i>z</i>",
          "지연 <i>z</i><sup>&minus;1</sup>, 극·영점",
          "<b>IIR 안정성</b> · 필터 구조 · 되먹임 해석"],
         ["<b>라플라스</b>", "연속시간 &rarr; 복소 <i>s</i>",
          "미분 &rarr; <i>s</i> 곱",
          "아날로그 필터 · PLL 루프 · 전송선"],
         ["<b>힐베르트</b>", "실수 &rarr; 해석신호", "음의 주파수 제거",
          "I/Q 생성 · SSB · 포락선 검출"]]))
    s.append("""<div class="ms"><b>Z 평면에서 안정성.</b> 인과적 IIR 이 BIBO 안정이려면
    모든 극이 <b>단위원 내부</b>에 있어야 한다(|<i>z</i>|&lt;1). 계수를 양자화하면 극이
    움직이고, <b>단위원 밖으로 나가면 발산</b>한다. 그래서 고정소수점 IIR 은
    <i>직접형</i>이 아니라 <b>2차 절편(biquad) 종속 연결</b>로 구현한다 &mdash;
    2차 절편은 극이 두 개뿐이라 계수 양자화에 대한 극 이동이 작기 때문이다.
    <b>이것이 &ldquo;수학적으로 같은 전달함수인데 구현이 다르면 성능이 다르다&rdquo;의
    대표 사례다.</b> 모델이 부동소수점 직접형으로 돼 있고 RTL 이 고정소수점 biquad 면
    둘은 <b>당연히</b> 다르다 &mdash; 비교 기준을 먼저 정해야 한다.</div>""")

    s.append("<h2>3. 표본화와 에일리어싱</h2>")
    s.append(svg그림(_fig_sample(),
        "표본화는 스펙트럼을 f<sub>s</sub> 간격으로 복제한다. 복제본이 겹치면(에일리어싱) "
        "원신호를 되돌릴 수 없다."))
    s.append("""<div class="math">f<sub>s</sub> &gt; 2B &nbsp;&nbsp;(나이퀴스트 조건)</div>""")
    s.append("""<div class="ms"><b>대역통과 표본화(undersampling).</b> 신호가
    [<i>f</i><sub>L</sub>, <i>f</i><sub>H</sub>] 에만 있으면 <i>f</i><sub>s</sub> 가
    2<i>f</i><sub>H</sub> 보다 훨씬 작아도 된다. 조건은
    2<i>f</i><sub>H</sub>/<i>n</i> &le; <i>f</i><sub>s</sub> &le;
    2<i>f</i><sub>L</sub>/(<i>n</i>&minus;1) 을 만족하는 정수 <i>n</i> 이 존재하는 것.
    이것이 <b>RF 수신기에서 ADC 속도를 낮추는 표준 기법</b>이다. 대가는 ADC 의
    <i>입력 대역폭</i>(샘플러의 아날로그 대역)이 <i>f</i><sub>H</sub> 이상이어야 한다는
    것 &mdash; <b>표본화율과 입력 대역폭은 다른 사양이다.</b> 데이터시트에서 이 둘을
    혼동하면 설계가 무너진다.</div>""")
    s.append("""<div class="warn"><b>안티에일리어싱 필터는 되돌릴 수 없는 결정이다.</b>
    표본화 <i>전에</i> 아날로그로 걸러야 한다. 한 번 접힌 스펙트럼은 디지털로 어떤
    처리를 해도 분리되지 않는다. <b>DSP 가 고칠 수 없는 몇 안 되는 손상</b>이고,
    그래서 시스템 분담에서 아날로그 쪽 사양으로 못박힌다.</div>""")

    s.append("<h2>4. 확률 · 잡음 · 성능 지표</h2>")
    s.append(표("통신/신호 IP 에서 쓰는 잡음과 지표",
        ["양", "정의 / 식", "어디서 나오나"],
        [["열잡음", "<i>N</i> = <i>kTB</i>. &minus;174 dBm/Hz @ 290K",
          "모든 수신기의 하한"],
         ["잡음지수 NF", "입력 SNR / 출력 SNR (dB)",
          "LNA 가 전체 NF 를 지배(Friis 식)"],
         ["Friis", "F = F<sub>1</sub> + (F<sub>2</sub>&minus;1)/G<sub>1</sub> + &hellip;",
          "<b>첫 단 이득이 크면 뒷단 잡음이 묻힌다</b>"],
         ["SNR", "신호전력/잡음전력", "모든 성능의 출발"],
         ["E<sub>b</sub>/N<sub>0</sub>", "비트당 에너지 / 잡음밀도",
          "<b>변조 방식을 공평하게 비교하는 축</b>"],
         ["BER", "비트오류율", "링크 품질"],
         ["Q 함수", "Q(x) = &frac12;erfc(x/&radic;2)",
          "BER = Q(&radic;(2E<sub>b</sub>/N<sub>0</sub>)) (BPSK)"],
         ["EVM", "오차벡터 크기 (%)", "송신기 품질. SNR 과 대응"],
         ["ENOB", "(SNDR&minus;1.76)/6.02", "ADC 의 <b>실효</b> 비트수"],
         ["SFDR", "최대 스퓨어 대비 (dBc)", "ADC/DAC 선형성"],
         ["위상잡음", "L(&Delta;f) (dBc/Hz)", "PLL/VCO. 지터로 환산된다"]]))
    s.append("""<div class="ms"><b>ENOB 이 왜 중요한가.</b> 12비트 ADC 를 샀는데
    ENOB 이 9.5 라면 <b>실제 분해능은 9.5비트</b>다. 모델에서 12비트로 양자화하면
    RTL/실리콘보다 낙관적인 성능이 나온다. <b>시스템 모델에는 ENOB 을 넣어야 한다.</b>
    특히 고속 ADC 는 <i>지터</i>가 ENOB 을 제한한다:
    SNR<sub>jitter</sub> = &minus;20log<sub>10</sub>(2&pi;<i>f</i><sub>in</sub>&sigma;<sub>t</sub>).
    56 GS/s 급에서 입력 14 GHz, 지터 100 fs 면
    SNR &asymp; 41 dB &rarr; ENOB &asymp; 6.5 로 <b>지터가 분해능을 정한다.</b></div>""")

    s.append("<h2>5. 랜덤 과정과 상관</h2>")
    s.append("""<div class="bs"><b>정상성(stationarity)</b>: 통계가 시간에 불변.
    <b>광의 정상(WSS)</b> 이면 평균이 상수이고 자기상관이 시간차에만 의존한다.
    <b>위너&ndash;킨친 정리</b>: WSS 과정의 <b>전력스펙트럼밀도는 자기상관의
    푸리에 변환</b>이다.</div>""")
    s.append("""<div class="math">S<sub>xx</sub>(f) = &#8497;{R<sub>xx</sub>(&tau;)}
    &nbsp;&nbsp;&nbsp; R<sub>xx</sub>(&tau;) = E[x(t)x*(t&minus;&tau;)]</div>""")
    s.append("""<div class="ms"><b>왜 IP 설계자가 이 정리를 써야 하나.</b> 적응 필터
    (LMS · RLS)의 최적해가 <b>위너 해</b> <b>w</b> = <b>R</b><sup>&minus;1</sup><b>p</b>
    이고, 여기서 <b>R</b> 이 입력 자기상관행렬, <b>p</b> 가 상호상관벡터다.
    수렴 속도는 <b>R</b> 의 <b>고유값 퍼짐</b>(&lambda;<sub>max</sub>/&lambda;<sub>min</sub>)이
    정한다 &mdash; 퍼짐이 크면 LMS 가 느리다. 그래서 채널이 심하게 주파수 선택적이면
    LMS 대신 RLS 나 주파수영역 적응을 쓴다. <b>&ldquo;적응이 안 수렴한다&rdquo;는 버그
    보고의 상당수가 실은 고유값 퍼짐 문제</b>이고, 모델링 팀이 이것을 계산해 보여 주면
    논쟁이 끝난다.</div>""")
    return "\n".join(s)


def _fig_fir():
    b = []
    x = 40
    for i in range(4):
        b.append(box(x, 30, 52, 30, f"z⁻¹", None, 9))
        if i: b.append(arr(x-18, 45, x, 45))
        b.append(arr(x+26, 60, x+26, 92))
        b.append(box(x, 92, 52, 26, f"×h{i}", None, 9))
        b.append(arr(x+26, 118, x+26, 140))
        x += 70
    b.append(arr(10, 45, 40, 45)); b.append(txt(12, 38, "x[n]", 9))
    b.append(box(40, 140, 262, 26, "Σ", None, 11))
    b.append(arr(302, 153, 340, 153)); b.append(txt(305, 146, "y[n]", 9))
    b.append(txt(171, 190, "탭 N개 → 곱셈기 N개 · 지연 N−1개 · 가산 N−1개", 9, "middle"))
    b.append(txt(171, 207, "대칭 계수면 곱셈기가 절반 (folded FIR)", 9, "middle",
                 'font-style="italic"'))
    return svg(360, 220, "".join(b))


def ch_dsp():
    s = ['<h1 id="dsp">디지털 신호처리 블록 &mdash; 산업용 구조 총람</h1>']
    s.append("<h2>1. FIR 필터</h2>")
    s.append(svg그림(_fig_fir(), "직접형 FIR. 탭 수가 곧 곱셈기 수다."))
    s.append(표("FIR 구조와 비용",
        ["구조", "곱셈기", "특징", "언제"],
        [["직접형", "N", "가장 단순", "N 이 작을 때"],
         ["<b>전치(transposed)</b>", "N", "임계경로가 곱셈기 1개 + 가산 1개로 <b>일정</b>",
          "고속. 거의 항상 이쪽"],
         ["<b>대칭 접기(folded)</b>", "&lceil;N/2&rceil;", "선형위상 계수의 대칭 이용",
          "선형위상 FIR 이면 무조건"],
         ["다상(polyphase)", "N/M", "데시메이션/보간과 결합", "샘플률 변환"],
         ["분산산술(DA)", "0 (LUT)", "곱셈기 없이 LUT+누산",
          "계수가 고정이고 FPGA LUT 가 남을 때"],
         ["<b>CSD / 시프트-가산</b>", "0", "계수를 2의 거듭제곱 합으로",
          "계수 고정 · ASIC 면적 최소화"]]))
    s.append("""<div class="ms"><b>전치형의 임계경로가 왜 일정한가.</b> 직접형은 출력
    가산기가 <b>N&minus;1 단 트리(또는 체인)</b>를 거친다 &mdash; N 이 커지면 경로가
    길어진다. 전치형은 각 탭의 곱셈 결과가 <b>지연 레지스터 사이의 가산기 하나</b>만
    거치므로 경로가 N 과 무관하다. 대가는 입력 <i>x</i>[<i>n</i>] 이 모든 곱셈기로
    가는 <b>높은 팬아웃</b>이고, 버퍼 트리로 해결한다. <b>같은 전달함수, 다른 회로,
    다른 최대 주파수</b> &mdash; 이 장 전체를 관통하는 주제다.</div>""")

    s.append("<h2>2. IIR 필터와 고정소수점</h2>")
    s.append(표("IIR 구조 비교",
        ["구조", "곱셈기", "계수 민감도", "한계사이클"],
        [["직접형 I", "2N+1", "<b>높다</b>(고차일수록 극 이동 큼)", "있음"],
         ["직접형 II", "2N+1", "높다", "내부 오버플로 위험 큼"],
         ["<b>2차 절편 종속(cascade biquad)</b>", "5&times;(N/2)",
          "<b>낮다</b> &mdash; 절편마다 극 2개", "절편별로 국소화"],
         ["격자(lattice)", "많다", "<b>가장 낮다</b>. 반사계수 |k|&lt;1 이 안정성",
          "구조적으로 안정"],
         ["상태공간", "가변", "설계 자유도 큼", "&mdash;"]]))
    s.append("""<div class="warn"><b>한계 사이클(limit cycle).</b> 고정소수점 IIR 은
    입력이 0 이어도 <b>출력이 0 으로 안 가고 작은 진동을 유지</b>할 수 있다. 반올림
    오차가 되먹임으로 순환하기 때문이다. 모델이 부동소수점이면 이 현상이 없으므로
    <b>모델과 RTL 이 다르다 &mdash; 그런데 RTL 이 맞다(그것이 실제 회로다).</b>
    대책은 오차 되먹임(error feedback) 또는 비트 확장. <b>명세에 &ldquo;한계 사이클
    진폭 &le; X LSB&rdquo; 를 적어야 한다.</b></div>""")

    s.append("<h2>3. 다중 샘플률 &mdash; 데시메이션 · 보간 · CIC</h2>")
    s.append("""<div class="bs"><b>데시메이션</b>(M배 감소)은 <i>먼저 걸러내고</i>
    솎아낸다 &mdash; 순서를 바꾸면 에일리어싱이 생긴다. <b>보간</b>(L배 증가)은
    <i>먼저 0 을 끼워넣고</i> 걸러낸다 &mdash; 끼워넣기가 스펙트럼 이미지를 만들고
    필터가 그것을 지운다.</div>""")
    s.append("""<div class="math">H<sub>CIC</sub>(z) =
    [ (1 &minus; z<sup>&minus;RM</sup>) / (1 &minus; z<sup>&minus;1</sup>) ]<sup>N</sup></div>""")
    s.append("""<div class="ms"><b>CIC(Cascaded Integrator-Comb) 가 왜 특별한가.</b>
    <b>곱셈기가 하나도 없다</b> &mdash; 적분기 N개와 콤 N개, 즉 가산기와 레지스터뿐이다.
    그래서 매우 높은 샘플률에서 쓸 수 있고, ADC 직후 첫 데시메이션 단의 표준이다.
    대가는 <b>통과대역 처짐(droop)</b> 이고, 뒤에 작은 FIR(보상 필터)을 붙여 편다.
    주의할 점은 <b>적분기의 비트 폭</b>: 적분기는 누적하므로
    <i>W</i><sub>out</sub> = <i>W</i><sub>in</sub> +
    <i>N</i>log<sub>2</sub>(<i>RM</i>) 만큼 커진다. 이 폭을 아끼려다 <b>2의 보수
    감싸기</b>에 의존하는 고전적 트릭이 있는데(중간 오버플로가 최종에서 상쇄됨),
    <b>포화로 바꾸면 즉시 깨진다.</b> 2부 &lsquo;수 체계&rsquo; 장의 원리가 여기서
    구체적으로 나타난다.</div>""")

    s.append("<h2>4. FFT</h2>")
    s.append(표("FFT 알고리즘과 하드웨어 사상",
        ["알고리즘", "복잡도", "특징", "하드웨어"],
        [["기수-2 DIT/DIF", "(N/2)log<sub>2</sub>N 나비", "가장 단순",
          "메모리 기반 또는 파이프라인"],
         ["기수-4 / 분할기수", "곱셈 수 감소", "제어 복잡",
          "고성능 ASIC"],
         ["<b>파이프라인 (SDF/MDC)</b>", "&mdash;",
          "연속 스트림 처리. 단마다 지연선", "통신 OFDM 표준 구조"],
         ["<b>SSR / 다중샘플</b>", "&mdash;", "클럭당 여러 샘플",
          "<b>클럭보다 빠른 데이터율</b>에 필수"],
         ["Winograd / 소인수", "곱셈 최소", "길이 제약", "특수 목적"]]))
    s.append("""<div class="ms"><b>FFT 의 진짜 비용은 곱셈이 아니라 메모리와 배선이다.</b>
    N=4096 파이프라인 FFT 에서 나비 연산기는 몇 개뿐이지만 <b>지연선 총량이 N 워드</b>에
    이른다. 또 비트반전(bit-reversal) 재배열이 메모리 대역을 먹는다. 그래서 실제
    설계에서는 <i>출력 순서를 비트반전 그대로 두고 다음 블록이 그 순서로 소비</i>하게
    만들어 재배열을 없애는 일이 흔하다 &mdash; <b>블록 경계를 넘는 최적화</b>이고,
    모델이 이것을 반영하지 않으면 &ldquo;출력 순서가 다르다&rdquo;는 가짜 불일치가 난다.
    <b>모델과 RTL 의 인터페이스 규약에 &lsquo;출력 순서&rsquo;를 명시하라.</b></div>""")

    s.append("<h2>5. NCO · CORDIC · 룩업</h2>")
    s.append(표("삼각함수/회전을 하드웨어로 만드는 법",
        ["방법", "원리", "비용", "언제"],
        [["<b>LUT</b>", "표를 읽는다", "ROM 2<sup>k</sup>&times;W",
          "각도 분해능이 낮을 때"],
         ["LUT + 보간", "표 + 1차/2차 보간", "작은 ROM + 곱셈기",
          "표를 줄이고 싶을 때"],
         ["<b>CORDIC</b>", "시프트-가산 회전 반복",
          "<b>곱셈기 0</b>, 반복 n회", "각도/크기 모두 필요할 때"],
         ["사분면 대칭 이용", "1/4 만 저장", "표 1/4", "항상 같이 쓴다"],
         ["Taylor / 다항 근사", "다항식", "곱셈기 몇 개", "정밀도 요구가 특수할 때"]]))
    s.append("""<div class="ms"><b>CORDIC 의 이득 보정.</b> 회전 모드의 CORDIC 은
    각 반복에서 벡터 크기를 &radic;(1+2<sup>&minus;2i</sup>) 배 늘린다. 총 이득
    <i>K</i> = &prod;&radic;(1+2<sup>&minus;2i</sup>) &asymp; 1.64676 은
    <b>반복 횟수에만 의존하고 데이터와 무관</b>하므로, 마지막에 상수 1/K 를 곱하거나
    <b>입력을 미리 1/K 배</b> 해 두면 된다. 후자가 곱셈기를 없앤다.
    <b>모델이 이 보정을 빠뜨리면 RTL 과 정확히 1.6468배 차이</b>가 나고, 이것은
    진단하기 쉬운 편에 속한다 &mdash; 비율이 일정한 불일치는 대개 스케일 문제다.</div>""")

    s.append("<h2>6. 적응 필터</h2>")
    s.append(표("적응 알고리즘",
        ["알고리즘", "갱신식", "수렴", "복잡도"],
        [["<b>LMS</b>", "w &larr; w + &mu; e x*",
          "느림. 고유값 퍼짐에 민감", "O(N)"],
         ["NLMS", "&mu; 를 |x|<sup>2</sup> 로 정규화", "입력 세기 변화에 강건", "O(N)"],
         ["부호 LMS", "부호만 사용", "더 느림", "<b>곱셈기 없음</b> &mdash; 하드웨어에 유리"],
         ["<b>RLS</b>", "역상관행렬 갱신", "빠름", "O(N<sup>2</sup>) &mdash; 비싸다"],
         ["주파수영역 LMS", "블록 FFT", "빠름", "O(N log N)"],
         ["<b>부호-부호 LMS</b>", "e 와 x 둘 다 부호", "가장 느림",
          "<b>가산기만</b>. 고속 SerDes 적응의 표준"]]))
    s.append("""<div class="ms"><b>왜 고속 링크는 부호-부호 LMS 를 쓰나.</b>
    56 GBd 에서 탭 갱신을 심볼률로 돌릴 수 없다 &mdash; 곱셈기가 그 속도로 못 돈다.
    그런데 적응은 <b>느려도 된다</b>(채널은 천천히 변한다). 그래서 부호만 취해
    XOR/가산으로 갱신하고, 수백~수천 심볼에 한 번씩 누적 갱신한다.
    <b>&ldquo;데이터패스는 심볼률, 적응은 훨씬 느린 률&rdquo;</b> 이라는 분리가
    모든 고속 수신기의 구조다. 모델링할 때 이 <b>두 클럭 도메인</b>을 명시적으로
    분리하지 않으면 RTL 과 갱신 시점이 어긋난다.</div>""")
    return "\n".join(s)
