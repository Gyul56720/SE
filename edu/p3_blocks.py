# -*- coding: utf-8 -*-
"""제3부 -- IP 블록별 교안 (AES 외)."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from book import 표, 토막, 줄수, svg그림, 파일찾기
from figs import svg, box, txt, arr, line, poly


def _fig_axi():
    b = []
    b.append(box(30, 30, 120, 40, "마스터", None, 10, "#eef7f2"))
    b.append(box(400, 30, 120, 40, "슬레이브", None, 10, "#f4eefa"))
    y = 95
    for 이름, 방향 in (("AW  주소 쓰기", "→"), ("W   데이터 쓰기", "→"),
                       ("B   쓰기 응답", "←"), ("AR  주소 읽기", "→"),
                       ("R   데이터 읽기", "←")):
        b.append(box(190, y, 170, 26, 이름, None, 9))
        if 방향 == "→":
            b.append(arr(150, y + 13, 190, y + 13))
            b.append(arr(360, y + 13, 400, y + 13))
        else:
            b.append(arr(400, y + 13, 360, y + 13))
            b.append(arr(190, y + 13, 150, y + 13))
        y += 34
    b.append(txt(275, 75, "독립된 5채널 — 각각 VALID/READY 핸드셰이크", 9, "middle"))
    b.append(txt(275, 282, "채널이 독립이므로 읽기와 쓰기가 동시에, 순서 없이 진행된다",
                 9, "middle", 'font-style="italic"'))
    return svg(555, 295, "".join(b))


def _fig_fifo():
    b = []
    b.append(box(40, 50, 90, 40, "쓰기", "clk_w", 9, "#eef7f2"))
    b.append(box(330, 50, 90, 40, "읽기", "clk_r", 9, "#f4eefa"))
    b.append(box(160, 40, 130, 60, "듀얼포트 RAM", None, 10))
    b.append(arr(130, 70, 160, 70))
    b.append(arr(290, 70, 330, 70))
    b.append(box(140, 125, 80, 30, "wptr", None, 9))
    b.append(box(240, 125, 80, 30, "rptr", None, 9))
    b.append(arr(180, 125, 180, 100))
    b.append(arr(280, 125, 280, 100))
    b.append(box(120, 175, 220, 30, "그레이 코드로 교차", None, 9, "#fbf2f2"))
    b.append(arr(200, 155, 200, 175))
    b.append(arr(260, 155, 260, 175))
    b.append(txt(230, 232,
                 "그레이 코드는 한 번에 한 비트만 바뀐다 — 동기화 중 잘못 읽혀도 ±1 이다",
                 9, "middle", 'font-style="italic"'))
    b.append(txt(230, 249,
                 "±1 은 full/empty 를 보수적으로 만들 뿐 데이터를 깨지 않는다",
                 9, "middle", 'font-style="italic"'))
    return svg(470, 262, "".join(b))


def axi():
    n = 줄수('ip', 'pulp-platform_axi')
    s = ['<h1 id="axi">AXI 인터커넥트 &mdash; 모든 SoC 의 등뼈</h1>']
    s.append(f"""<div class="kvbar"><b>표준</b> Arm AMBA AXI4 / AXI4-Lite / AXI4-Stream
    &nbsp;&bull;&nbsp; <b>이 교안의 실물</b> <code>pulp-platform/axi</code> {n:,}줄
    &nbsp;&bull;&nbsp; <b>형식 검증된 구현</b> <code>ZipCPU/wb2axip</code>
    {줄수('ip','ZipCPU_wb2axip'):,}줄</div>""")
    s.append(svg그림(_fig_axi(),
        "AXI4 의 다섯 채널. 각 채널이 독립이고 VALID/READY 로만 흐른다."))
    s.append("""<div class="bs"><b>핸드셰이크 규칙이 전부다.</b> 보내는 쪽이
    <code>VALID</code>, 받는 쪽이 <code>READY</code>. 둘 다 1인 클럭 엣지에 한 박자가
    넘어간다. <b>한 번 올린 VALID 는 전송이 끝날 때까지 내리면 안 된다</b> &mdash;
    이 규칙 하나를 어기면 프로토콜 위반이고, 검사기가 잡는다.</div>""")
    s.append(표("AXI 에서 모델링 팀이 꼭 알아야 할 것",
        ["개념", "뜻", "왜 모델에 영향을 주나"],
        [["<b>버스트</b>(AWLEN/ARLEN)", "한 주소로 여러 박자",
          "메모리 모델이 버스트 경계를 알아야 한다"],
         ["<b>ID</b>(AWID/ARID)", "여러 트랜잭션을 구분",
          "<b>같은 ID 는 순서 보장, 다른 ID 는 순서 없음</b> &mdash; 스코어보드 설계가 갈린다"],
         ["<b>아웃오브오더</b>", "응답이 요청 순서와 다를 수 있다",
          "모델이 &lsquo;순서대로&rsquo;를 가정하면 틀린다"],
         ["<b>4KB 경계</b>", "버스트는 4KB 를 넘을 수 없다", "자극 생성 제약"],
         ["<b>WSTRB</b>", "바이트 단위 쓰기 마스크",
          "부분 쓰기를 모델이 처리해야 한다"],
         ["<b>응답 코드</b>", "OKAY · EXOKAY · SLVERR · DECERR",
          "오류 경로도 명세의 일부다"],
         ["<b>배타 접근</b>", "load-reserved / store-conditional 용",
          "모델링이 까다롭다. 모니터가 상태를 들고 있어야 한다"]]))
    s.append("""<div class="ms"><b>ID 와 순서가 검증의 핵심이다.</b> AXI 는 <i>같은
    ID</i> 안에서만 순서를 보장한다. 그래서 스코어보드는 &ldquo;큐 하나&rdquo;가 아니라
    <b>ID별 큐</b>여야 한다. 이것을 모르고 단일 큐로 만들면, 정상 동작을 오류로
    보고하거나(거짓 실패) 진짜 순서 위반을 놓친다(거짓 통과). <b>모델링 팀이 이
    구조를 DV 에 알려 주는 것이 흔한 협업 지점이다.</b></div>""")
    s.append(f"""<p><code>ZipCPU/wb2axip</code> 는 단언이
    {[f for f in 파일찾기('ip','ZipCPU_wb2axip')] and sum(f['단언'] for f in 파일찾기('ip','ZipCPU_wb2axip')):,}개
    들어 있는 <b>형식 검증된</b> AXI/Wishbone 브리지다. 프로토콜 속성을 어떻게 적는지
    보려면 여기가 가장 좋은 교재다.</p>""")
    return "\n".join(s)


def fifo():
    n = 줄수('ip', 'pulp-platform_common_cells')
    s = ['<h1 id="fifo">FIFO · CDC 기본 셀 &mdash; 가장 많이 쓰이고 가장 많이 틀린다</h1>']
    s.append(f"""<div class="kvbar"><b>이 교안의 실물</b>
    <code>pulp-platform/common_cells</code> {n:,}줄 &mdash; <code>fifo_v3</code>,
    <code>cdc_2phase</code>, <code>cdc_fifo_gray</code>, <code>rr_arb_tree</code>,
    <code>stream_*</code> 등</div>""")
    s.append(svg그림(_fig_fifo(),
        "비동기 FIFO. 포인터를 그레이 코드로 바꿔 교차시키는 것이 핵심이다."))
    s.append("""<div class="ms"><b>왜 그레이 코드인가.</b> 이진 카운터 7&rarr;8 은
    <code>0111&rarr;1000</code> 으로 <b>네 비트가 동시에</b> 바뀐다. 다른 클럭에서 이걸
    샘플하면 비트마다 도착 시점이 달라 <code>1111</code> 같은 <b>존재한 적 없는 값</b>을
    읽을 수 있다. 그레이 코드는 인접값이 <b>1비트만</b> 다르므로, 최악의 경우에도
    &ldquo;이전 값 또는 다음 값&rdquo;을 읽는다. 그 오차는 full/empty 판정을
    <b>보수적으로</b> 만들 뿐이다 &mdash; 실제보다 꽉 찼다고 보거나 비었다고 볼 뿐,
    <b>데이터를 깨지 않는다.</b> 이것이 안전한 설계의 전형이다: <i>틀리더라도 안전한
    방향으로 틀리게 만든다.</i></div>""")
    s.append(표("FIFO 관련 실무 함정",
        ["함정", "증상", "대책"],
        [["깊이가 버스트를 못 받는다", "생산자가 스톨 &rarr; 전체 파이프라인 정지",
          "최악 버스트 + 지연을 계산해 깊이를 정한다"],
         ["full/empty 를 한 클럭 늦게 본다", "오버런/언더런",
          "거의 참(almost_full) 신호를 쓴다"],
         ["2단 동기화기를 다중비트에", "값이 깨진다", "그레이 코드 또는 핸드셰이크"],
         ["리셋이 두 도메인에서 비대칭", "한쪽만 초기화돼 포인터가 어긋남",
          "리셋도 CDC 대상이다"],
         ["깊이 1 FIFO 를 레지스터로 대체", "백프레셔 타이밍이 달라짐",
          "<code>stream_register</code> 같은 검증된 셀을 쓴다"]]))
    s.append("""<div class="note"><b>모델링 팀 관점.</b> 기능 모델에는 FIFO 깊이가
    없다 &mdash; 무한 큐로 둔다. 그래서 <b>깊이 부족으로 인한 성능 저하나 데드락은
    모델이 절대 못 잡는다.</b> 이것은 성능 모델(SystemC TLM 또는 사이클 근사 모델)의
    영역이다. 두 모델을 구분해 두는 것이 중요하다.</div>""")
    return "\n".join(s)


def cpu():
    s = ['<h1 id="cpu">RISC-V 코어 &mdash; 모델링 팀의 주무대</h1>']
    s.append(표("이 교안에 들어 있는 RISC-V 구현들",
        ["코어", "줄 수", "성격", "배울 점"],
        [["<code>openhwgroup/cva6</code>", f"{줄수('ip','openhwgroup_cva6'):,}",
          "64비트 응용 프로세서. 리눅스 부팅. 다수 테이프아웃",
          "MMU · 캐시 · 분기예측이 있는 진짜 코어"],
         ["<code>openhwgroup/cv32e40p</code>", f"{줄수('ip','openhwgroup_cv32e40p'):,}",
          "32비트 임베디드. PULP 계열", "<b>step-compare 검증의 예제</b>"],
         ["<code>YosysHQ/picorv32</code>", f"{줄수('ip','YosysHQ_picorv32'):,}",
          "초소형. FPGA 에 널리 쓰임", "가장 읽기 쉬운 RISC-V RTL"],
         ["<code>olofk/serv</code>", f"{줄수('ip','olofk_serv'):,}",
          "<b>비트 직렬</b> 세계 최소 RISC-V", "극단적 면적 최적화의 사례"],
         ["<code>chipsalliance/rocket-chip</code>", f"{줄수('ip','chipsalliance_rocket-chip'):,}",
          "Chisel(Scala) 생성기. SiFive 계보", "RTL 을 <b>생성</b>하는 방식"]]))
    s.append("""<div class="ms"><b>Rocket 이 Chisel 인 것이 중요하다.</b> RTL 을 직접
    쓰는 대신 <b>프로그램이 RTL 을 만든다</b>. 파라미터를 바꾸면 다른 코어가 나온다.
    IP 비즈니스의 본질(하나의 소스로 여러 PPA 점을 판다)이 언어 차원에 들어간 것이다.
    단점은 생성된 Verilog 가 사람이 읽기 어렵다는 것 &mdash; 디버그와 검증이
    까다로워진다. <b>실무에서 이 맞교환은 여전히 논쟁 중이다.</b></div>""")
    s.append("<h2>코어 모델링에서 반드시 정해야 하는 것</h2>")
    s.append(표("ISA 모델의 설계 결정",
        ["결정", "선택지", "영향"],
        [["명령어 표현", "파일 하나에 하나(Spike) vs 거대 switch",
          "확장성. Spike 방식이 옳다"],
         ["디코더", "표 기반 vs 조건 트리", "속도와 유지보수"],
         ["메모리", "평면 배열 vs 페이지 테이블 vs MMU 완전 모델",
          "권한/가상메모리 검증 여부가 갈린다"],
         ["예외 우선순위", "규격이 정한 순서를 그대로",
          "<b>여기가 자주 틀린다.</b> 동시 발생 시 순서"],
         ["인터럽트 주입", "DV 가 시점을 준다 vs 모델이 정한다",
          "전자라야 RTL 과 맞출 수 있다"],
         ["카운터(mcycle 등)", "<b>모델링하지 않는다</b>", "사이클 개념이 없다"],
         ["미정의 동작", "명시적 표시 + DV 마스킹", "3장의 (다)"]]))
    s.append("""<div class="warn"><b>예외 우선순위가 모델링의 최대 함정이다.</b>
    한 명령어가 동시에 여러 예외 조건을 만족할 수 있다(정렬 오류 + 페이지 폴트 + 권한
    위반). 규격은 우선순위 표를 준다. 모델이 그 순서를 잘못 구현하면 <b>평소에는 안
    보이다가</b> 특정 조합에서만 터진다. <b>첫 주에 규격의 예외 우선순위 표를 찾아
    모델과 대조하라.</b></div>""")
    return "\n".join(s)


def fec():
    s = ['<h1 id="fec">RS-FEC &mdash; 통신 IP 의 필수 블록</h1>']
    s.append("""<div class="kvbar"><b>표준</b> IEEE 802.3 Clause 91 (KP4) &nbsp;&bull;&nbsp;
    <b>부호</b> RS(544,514) over GF(2<sup>10</sup>), t=15 심볼 &nbsp;&bull;&nbsp;
    <b>쓰임</b> 100G 이상 이더넷 <b>필수</b></div>""")
    s.append("""<div class="bs"><b>왜 FEC 가 필수가 됐나.</b> 옛날 링크는 BER
    10<sup>&minus;12</sup> 를 물리계층이 직접 맞췄다. 100G/lane 이 되면 그것이 불가능해져,
    <b>슬라이서는 10<sup>&minus;4</sup> 수준으로 내고 FEC 가 10<sup>&minus;15</sup> 로
    내린다</b>는 분업으로 바뀌었다. 그래서 FEC 는 선택이 아니라 규격이 강제하는
    블록이다.</div>""")
    s.append(표("RS 복호기의 네 단계 &mdash; 모델과 RTL 이 같은 구조를 쓴다",
        ["단계", "하는 일", "수학", "하드웨어 비용"],
        [["신드롬", "S<sub>i</sub> = r(&alpha;<sup>fcr+i</sup>), i=0..2t&minus;1",
          "다항식 평가 2t회", "GF 곱셈기 2t개 (병렬)"],
         ["Berlekamp-Massey", "오류위치다항식 &sigma;(x) 를 찾는다",
          "최단 LFSR 합성", "반복 2t회. <b>되먹임 고리 &mdash; 임계경로</b>"],
         ["Chien 탐색", "&sigma;(x) 의 근 = 오류 위치",
          "n개 원소 전수 대입", "n/병렬도 사이클"],
         ["Forney", "오류 크기 계산", "&omega;(x)/&sigma;&prime;(x)",
          "GF 나눗셈(역원 테이블)"]]))
    s.append("""<div class="ms"><b>BM 단계가 아키텍처를 정한다.</b> 신드롬과 Chien 은
    전수 병렬화가 쉽다(독립 계산). BM 은 <b>반복마다 이전 결과가 필요한 되먹임</b>이라
    병렬화가 어렵다. 그래서 고속 RS 복호기는 <i>inversionless</i> BM(역원 제거),
    <i>reformulated</i> BM(임계경로 단축) 같은 변형을 쓴다. <b>모델에서는 어느 판을 써도
    결과가 같다</b> &mdash; 그래서 모델은 가장 읽기 쉬운 판으로 쓰고, RTL 이 다른 판을
    쓰더라도 비교는 성립한다. <b>이것이 모델과 RTL 이 &lsquo;같은 알고리즘&rsquo;일
    필요가 없다는 좋은 예다. 같은 <i>함수</i>이면 된다.</b></div>""")
    s.append("<h2>검사가 반드시 확인해야 하는 성질</h2>")
    s.append(표("RS 복호기 검사 설계",
        ["넣는 오류", "기대", "이 검사가 없으면"],
        [["0개", "손대지 않는다", "<b>이것만 하면 검사가 아니다</b> &mdash; 복호기가 놀아도 통과"],
         ["1 ~ t개", "<b>전부 정정</b>, 오정정 0", "정정 능력 미검증"],
         ["t+1개 이상", "<b>원본 복원은 불가능</b>",
          "&lsquo;전부 검출된다&rsquo;고 쓰면 <b>과장</b>이다 &mdash; 일부는 다른 코드워드로 간다"],
         ["경계(t 와 t+1)", "정확히 t 에서 갈린다", "off-by-one"],
         ["정정 후 재검사", "신드롬이 0 인지 다시 잰다", "오정정을 성공으로 보고한다"]]))
    s.append("""<div class="warn"><b>&ldquo;t+1개는 전부 검출된다&rdquo;는 틀린 문장이다.</b>
    RS 는 t 개까지 정정하고 그 이상은 <b>검출하거나 오정정한다</b>. 저자의 실측:
    RS(15,9), t=3 에서 오류 4개를 120회 넣으니 <b>검출 117 · 오정정 3</b> 이었다.
    IP 사양서에 이 확률을 적는 것이 정직한 문서다.</div>""")
    return "\n".join(s)
