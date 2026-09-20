# -*- coding: utf-8 -*-
"""제1부 -- 모델링 팀 실무 매뉴얼.  내일 출근해서 쓰는 것."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from book import 표, 그림, svg그림, 토막, 줄수, E, 파일찾기
import figs_aes


def ch1():
    s = ['<h1 id="c1">1장. 세 팀의 삼각형 &mdash; 당신은 어디에 서 있나</h1>']
    s.append("""<p>반도체 IP 개발 조직은 세 팀으로 나뉜다. 이 구분은 관습이 아니라
    <b>버그를 정의하기 위한 구조</b>다. 세 팀이 없으면 "무엇이 맞는가" 를 정할 수
    없다.</p>""")
    s.append(svg그림(figs_aes.삼각형(),
        "세 팀의 관계. 디자인은 하드웨어를, 모델링은 정답을, DV 는 둘을 맞대는 "
        "장치를 만든다. 회귀(regression)에서 <b>디자인과 모델이 다르면 그것이 "
        "버그다</b> &mdash; 이것이 버그의 조작적 정의다."))

    s.append("<h2>1.1 각 팀이 실제로 만드는 것</h2>")
    s.append(표("세 팀의 산출물 &mdash; 이 교안이 실제로 받아 놓은 코드로",
        ["팀", "만드는 것", "언어", "이 교안의 실물", "규모"],
        [["<b>디자인</b>", "합성 가능한 RTL. 파이프라인 · FSM · 데이터패스",
          "SystemVerilog / Verilog / VHDL",
          "<code>opentitan/hw/ip/aes/rtl</code>", f"{줄수('ip','opentitan/hw/ip/aes/rtl'):,}줄"],
         ["<b>모델링</b>", "참조모델(골든). 명세의 <i>의미</i>를 코드로",
          "C / C++ (SystemC · TLM)",
          "<code>riscv-isa-sim</code> (Spike)", f"{줄수('model','riscv-software-src_riscv-isa-sim'):,}줄"],
         ["<b>DV</b>", "테스트벤치 · 스코어보드 · 커버리지 · 자극 생성",
          "SystemVerilog(UVM) · Python(cocotb)",
          "<code>core-v-verif</code>", f"{줄수('ip','openhwgroup_core-v-verif'):,}줄"]]))

    s.append("""<div class="bs">세 팀이 <b>같은 명세</b>를 서로 다른 두 가지 방법으로
    구현하고, 세 번째 팀이 둘을 비교한다. 두 독립 구현이 같은 답을 내면 명세를 제대로
    읽었을 확률이 높다. 이것이 <i>다중 구현에 의한 검증</i>이고, 우주선 제어기부터
    CPU 까지 같은 원리다.</div>""")
    s.append("""<div class="ms">두 구현이 <b>독립이 아니면</b> 이 논증은 무너진다.
    모델러와 설계자가 같은 사람에게 같은 설명을 듣고, 같은 오해를 하면, 회귀는 초록인데
    칩은 틀린다. 실무에서 이것을 막는 장치가 <i>명세를 문서가 아니라 실행 가능한
    형식모델로 두는 것</i>이다 &mdash; RISC-V 의 Sail 모델
    (<code>riscv/sail-riscv</code>, {0:,}줄)이 그 예다. Sail 은 규격 문서와 C 에뮬레이터를
    <b>같은 원천</b>에서 낸다.</div>""".format(줄수('model','riscv_sail-riscv')))

    s.append("<h2>1.2 왜 모델이 RTL 보다 훨씬 작은가</h2>")
    s.append(svg그림(figs_aes.세구현(),
        "같은 AES 표준(FIPS-197)의 세 구현. 줄 수는 이 교안이 받아 놓은 실제 저장소를 "
        "기계로 센 값이다."))
    s.append("""<p>줄 수 차이가 30배다. <b>알고리즘이 어려워서가 아니다.</b> 알고리즘은
    세 구현이 똑같다. 차이는 전부 하드웨어에만 있는 문제들이다:</p>""")
    s.append(표("RTL 에만 있고 모델에는 없는 것",
        ["RTL 이 추가로 감당하는 것", "왜 모델에는 없나", "OpenTitan AES 의 예"],
        [["클럭 · 리셋 · 파이프라인 단", "모델은 한 번에 한 블록을 계산하고 끝낸다",
          "<code>aes_cipher_control_fsm.sv</code>"],
         ["레지스터맵 · 버스 인터페이스", "모델은 함수 호출로 받는다",
          "<code>aes_reg_top.sv</code>, TL-UL 어댑터"],
         ["부채널 대책(마스킹)", "모델은 전력을 소비하지 않는다",
          "<code>aes_sbox_dom.sv</code>, <code>aes_prng_masking.sv</code>"],
         ["고장주입 대책(이중화)", "모델은 알파입자를 맞지 않는다",
          "<code>aes_cipher_control_fsm_p/n.sv</code>"],
         ["키 삭제 · 수명 관리", "모델은 메모리를 지우지 않아도 된다",
          "<code>aes_prng_clearing.sv</code>"],
         ["합성 제약 · 타이밍 클로저", "모델은 시간을 소비하지 않는다", "SDC · prim_buf 장벽"]]))
    s.append("""<div class="note"><b>모델링 팀의 레버리지가 여기 있다.</b>
    573줄짜리 C 모델이 17,254줄짜리 RTL 의 정답을 정의한다. 30배 적은 코드로
    30배 많은 코드를 붙든다. 대신 <b>모델이 틀리면 전부가 틀린다</b> &mdash;
    그래서 모델은 RTL 보다 더 엄격하게 검토된다.</div>""")
    return "\n".join(s)


def ch2():
    s = ['<h1 id="c2">2장. 모델링 팀이 실제로 쓰는 코드</h1>']
    s.append("""<p>추상적으로 말하지 않는다. RISC-V 의 표준 ISS 인 <b>Spike</b>
    (<code>riscv-software-src/riscv-isa-sim</code>)를 열어 본다. 이것은 실제 업계에서
    RTL 검증의 기준으로 쓰이는 참조모델이고, 이 교안에 전문이 들어 있다.</p>""")

    s.append("<h2>2.1 명령어 하나 = 파일 하나</h2>")
    inst = len([f for f in 파일찾기('model','riscv-software-src_riscv-isa-sim/riscv/insns/')])
    s.append(f"""<p>Spike 의 <code>riscv/insns/</code> 에는 <b>{inst:,}개</b>의 파일이
    있고, 파일 하나가 명령어 하나의 <i>의미</i>다. 본문은 대개 한 줄이다.</p>""")
    s.append(토막('model','riscv-software-src_riscv-isa-sim/riscv/insns/add.h',1,1,
                  'ADD 명령어의 전부'))
    s.append(토막('model','riscv-software-src_riscv-isa-sim/riscv/insns/mulh.h',1,5,
                  'MULH -- XLEN 에 따라 갈린다'))
    s.append("""<div class="bs"><code>WRITE_RD</code>, <code>RS1</code>,
    <code>sext_xlen</code> 은 매크로다. 명령어 본문이 <b>아키텍처 상태를 어떻게
    바꾸는가</b>만 적고, 그것을 어떻게 가져오고 되쓰는지는 매크로가 감춘다. 그래서
    본문이 명세 문장과 거의 1:1 로 읽힌다.</div>""")
    s.append("""<div class="ms">이 설계가 주는 실무 이득은 <b>확장의 비용</b>이다.
    새 확장(extension)이 나오면 <code>insns/</code> 에 파일을 더하고 디코더 표에 한 줄을
    넣으면 된다. 모델 전체를 건드리지 않는다. 당신이 회사에서 만들 모델도 이 구조를
    따라야 한다 &mdash; <b>명령어별 파일 · 매크로로 감춘 상태 접근 · 표로 만든 디코더</b>.
    이것을 처음부터 안 하면 확장 50개째에서 무너진다.</div>""")

    s.append("<h2>2.2 진짜 어려운 부분은 부동소수점이다</h2>")
    sf = 줄수('model','riscv-software-src_riscv-isa-sim/softfloat')
    rv = 줄수('model','riscv-software-src_riscv-isa-sim/riscv/')
    s.append(f"""<p>Spike 의 <code>riscv/</code> 가 {rv:,}줄인데
    <code>softfloat/</code> 만 <b>{sf:,}줄</b>이다. IEEE 754 를 비트 단위로 정확히
    재현하는 것이 명령어 의미를 적는 것보다 무겁다.</p>""")
    s.append("""<div class="ms">왜 그런가. IEEE 754 는 <b>반올림 모드 5가지</b>,
    <b>예외 플래그 5가지</b>, <b>비정규수(subnormal)</b>, <b>NaN 전파 규칙</b>,
    <b>부호 있는 0</b> 을 전부 규정한다. 하드웨어가 이 중 하나라도 다르게 하면
    회귀가 빨개진다. 그런데 컴파일러의 <code>double</code> 연산을 그대로 쓰면
    호스트 CPU 의 반올림에 끌려가므로 <b>정답이 호스트마다 달라진다</b>. 그래서
    Berkeley SoftFloat 같은 <i>비트 단위 정수 구현</i>을 쓴다. 모델링 팀에서
    부동소수점을 맡으면 이 점을 가장 먼저 확인하라 &mdash; <b>호스트 부동소수점을
    쓰고 있지 않은가.</b></div>""")

    s.append("<h2>2.3 모델은 무엇을 흉내내지 <i>않는가</i></h2>")
    s.append(표("ISS 가 모델링하는 것과 하지 않는 것",
        ["모델링한다", "하지 않는다", "그래서 DV 가 감당한다"],
        [["아키텍처 상태(PC · GPR · CSR)", "파이프라인 단계 · 스톨",
          "타이밍은 RTL 만의 진실. 비교는 <i>명령어 retire 시점</i>에 한다"],
         ["메모리 내용", "캐시 히트/미스 · 버스 지연", "성능은 별도 모델(gem5)이 본다"],
         ["예외 · 인터럽트 <i>의미</i>", "인터럽트가 <i>언제</i> 들어오는지",
          "DV 가 인터럽트 시점을 모델에 주입해 맞춘다"],
         ["권한 · 가상메모리 변환", "TLB 교체 정책", "구현 자유 영역"]]))
    s.append("""<div class="warn"><b>이 표의 오른쪽이 실무에서 가장 자주 사고를 낸다.</b>
    모델은 맞는데 비교가 실패한다. 원인은 대개 "모델이 흉내내지 않는 것" 을 비교하려
    했기 때문이다. 실제 사례가 이 교안 안에 있다 &mdash; core-v-verif 의 비교
    코드에 이런 주석이 남아 있다:<br>
    <code>// FIXME: I am removing the static (non-written) register checks, as they
    fail in presence of I and D bus RAM stalls</code><br>
    <b>버스 스톨이 있으면 "바뀌지 않았어야 할 레지스터" 검사가 실패한다.</b> 모델이
    틀린 것이 아니라 비교 시점이 틀린 것이다.</div>""")
    return "\n".join(s)


def ch3():
    s = ['<h1 id="c3">3장. 참조모델을 쓰는 규율 &mdash; 무엇이 &lsquo;골든&rsquo;인가</h1>']
    s.append("""<p>모델링 팀의 코드는 <b>정답</b>으로 쓰인다. 그래서 일반 소프트웨어와
    다른 규율이 붙는다. 아래 일곱은 실무에서 사고가 났던 자리들이고, 이 교안이 받아 놓은
    실제 코드에서 근거를 댄다.</p>""")

    s.append("<h2>3.1 규율 일곱</h2>")
    s.append(표("참조모델 작성 규율",
        ["#", "규율", "지키지 않으면", "근거"],
        [["1", "<b>호스트 산술에 기대지 마라.</b> 폭·반올림·오버플로를 직접 구현한다",
          "같은 모델이 x86 과 ARM 에서 다른 답을 낸다",
          "Spike 가 Berkeley SoftFloat 를 따로 두는 이유"],
         ["2", "<b>상태 접근을 매크로/접근자로 감춰라</b>",
          "명령어 500개를 고칠 일이 생긴다", "<code>WRITE_RD</code> · <code>RS1</code>"],
         ["3", "<b>미정의 동작을 &lsquo;아무거나&rsquo;로 두지 마라.</b> 명시적으로 표시한다",
          "RTL 이 다른 값을 내는데 누가 맞는지 못 정한다", "RISC-V 의 <i>reserved</i> 처리"],
         ["4", "<b>모델은 빨라야 한다.</b> 회귀가 수만 번 돈다",
          "야간 회귀가 아침에 안 끝난다", "Spike 는 인터프리터인데도 표 기반 디코더"],
         ["5", "<b>추적(trace)을 낼 수 있어야 한다</b>",
          "DV 가 비교할 대상이 없다", "RVFI · Spike 의 commit log"],
         ["6", "<b>결정론적이어야 한다.</b> 같은 입력 &rarr; 같은 출력, 항상",
          "재현이 안 되는 버그가 생긴다", "난수는 씨앗을 받아 쓴다"],
         ["7", "<b>규격 문서의 절 번호를 코드에 적어라</b>",
          "3년 뒤 왜 그런지 아무도 모른다", "OpenTitan RTL 의 주석 관행"]]))

    s.append("""<div class="ms"><b>규율 3 이 가장 자주 싸움을 만든다.</b> 명세가
    "이 경우 동작은 정의되지 않는다" 라고 하면, 모델은 무엇을 해야 하는가? 선택지는 셋이다.
    (가) 임의값을 내고 DV 에게 "여기는 비교하지 마라" 고 알린다. (나) RTL 이 내는 값을
    모델도 내도록 맞춘다 &mdash; <b>이러면 모델이 독립성을 잃는다</b>. (다) 모델이
    명시적으로 <i>undefined</i> 표시를 내보내고 DV 가 그 필드를 마스킹한다. <b>(다)가
    정답이다.</b> (나)를 하면 그 순간 그 필드에 대해 검증이 사라지는데, 아무도 모른다.</div>""")

    s.append("<h2>3.2 검사가 &lsquo;무는지&rsquo;부터 확인하라</h2>")
    s.append("""<p>참조모델 검사에서 가장 흔한 거짓 초록은 <b>검사가 아무것도 안 하는
    경우</b>다. 예를 들어 오류 정정 블록의 복호기를 시험하면서 오류를 0개 넣으면,
    복호기가 아무 일도 안 해도 통과한다.</p>""")
    s.append("""<div class="note"><b>실무 습관.</b> 검사를 짜고 나서 <b>일부러 모델을
    망가뜨려 보라.</b> 곱셈에 1을 더하거나, 신드롬을 0으로 박거나, 패리티를 0으로 만들어
    보고 <b>검사가 빨개지는지</b> 본다. 빨개지지 않으면 그 검사는 없는 것과 같다.
    이 교안 저자의 저장소에서는 이것을 검사 파일 안에 같이 둔다:</p>
    <pre class="code">def test_망가진_복호기는_잡힌다():
    원래 = c.신드롬
    c.신드롬 = lambda r: [0] * (2 * c.t)      # 조용히 망가뜨린다
    res = 측정(c, 오류수=2, 시행=20)
    assert res["고침"] &lt; 20, "신드롬을 0 으로 박았는데 전부 고쳐졌다 -- 검사가 안 문다"</pre>
    </div>""")

    s.append("<h2>3.3 모델과 RTL 이 다를 때 누가 틀렸는지 가리는 법</h2>")
    s.append(표("불일치 삼분법 &mdash; 이 순서로 의심한다",
        ["순서", "의심", "확인 방법", "실제 빈도"],
        [["1", "<b>비교가 틀렸다</b> (시점 · 마스킹 · 필드 선택)",
          "모델 단독 / RTL 단독으로 같은 입력을 돌려 로그를 눈으로 본다", "가장 흔하다"],
         ["2", "<b>모델이 틀렸다</b>",
          "명세 조문을 다시 읽는다. 다른 구현(타사 · 오픈소스)과 대조한다", "그 다음"],
         ["3", "<b>RTL 이 틀렸다</b> &mdash; 진짜 버그",
          "최소 재현 케이스를 만들어 설계자에게 넘긴다", "가장 드물다"]]))
    s.append("""<div class="warn"><b>1번을 건너뛰고 3번으로 가면 신뢰를 잃는다.</b>
    "버그 같습니다" 라고 설계자에게 넘겼는데 비교 코드 문제였던 일이 두 번 반복되면,
    세 번째 진짜 버그를 아무도 안 본다. <b>최소 재현 케이스 없이 버그를 넘기지 마라.</b></div>""")
    return "\n".join(s)


def ch4():
    s = ['<h1 id="c4">4장. DV 와의 계약 &mdash; 실제 비교 코드를 읽는다</h1>']
    s.append("""<p>모델과 RTL 을 <b>어떻게</b> 맞대는가. 이 교안에는 실제 CPU 검증환경의
    비교 코드가 들어 있다 &mdash; <code>core-v-verif</code> 의
    <code>uvmt_cv32e40p_step_compare.sv</code>. 파일 머리에 출처가 적혀 있다:</p>""")
    s.append(토막('ip','openhwgroup_core-v-verif/cv32e40p/tb/uvmt/uvmt_cv32e40p_step_compare.sv',
                  22, 26, '이 파일이 어디서 왔는지'))
    s.append("""<div class="bs"><b>Imperas</b> 는 상용 ISS(OVPsim) 회사다. 업계가 쓰는
    패턴을 오픈 프로젝트가 그대로 따른 것이므로, <b>여기서 배우는 구조가 곧 실무
    구조다.</b></div>""")

    s.append("<h2>4.1 step-and-compare: 한 명령어마다 전부 맞댄다</h2>")
    s.append(토막('ip','openhwgroup_core-v-verif/cv32e40p/tb/uvmt/uvmt_cv32e40p_step_compare.sv',
                  141, 168, 'PC 와 GPR 32개를 맞대는 부분'))
    s.append("""<p>구조는 단순하다. 명령어가 retire 될 때마다:</p>
    <ol>
    <li><b>PC</b> 를 맞댄다 &mdash; 모델의 <code>state.pc</code> 대 RTL 의 <code>insn_pc</code></li>
    <li><b>GPR 32개 전부</b> 를 맞댄다. 이번에 쓰인 레지스터는 <i>쓰인 값</i>으로,
        나머지는 <i>바뀌지 않았음</i>을 확인한다</li>
    <li><b>CSR</b> 을 맞댄다 &mdash; <code>mstatus</code>, <code>misa</code>,
        <code>mie</code>, <code>mtvec</code>, <code>mcountinhibit</code> …</li>
    </ol>""")
    s.append("""<div class="ms"><b>2번의 &ldquo;나머지는 바뀌지 않았음&rdquo; 검사가
    중요하다.</b> 쓰인 레지스터만 보면, RTL 이 <i>엉뚱한 레지스터를 추가로 덮어쓰는</i>
    버그를 못 잡는다. 그런데 바로 이 검사가 버스 스톨이 있을 때 실패해서 실무에서
    꺼졌다(같은 파일의 FIXME 주석). <b>커버리지와 실행 가능성의 맞교환</b>이고, 이런
    결정은 반드시 문서에 남겨야 한다. 남기지 않으면 몇 달 뒤 "그 검사는 왜 없지?" 로
    돌아온다.</div>""")

    s.append("<h2>4.2 RVFI &mdash; 비교를 가능하게 하는 표준 포트</h2>")
    rvfi = 줄수('ip','openhwgroup_core-v-verif/lib/uvm_agents/uvma_rvfi')
    s.append(f"""<p>모델과 RTL 을 맞대려면 RTL 이 <b>무엇을 언제 했는지</b> 말해 줘야
    한다. RISC-V 진영의 표준이 <b>RVFI</b>(RISC-V Formal Interface)다. DUT 가 명령어를
    retire 할 때마다 다음을 내보낸다.</p>""")
    s.append(표("RVFI 가 내보내는 것 (핵심 필드)",
        ["필드", "뜻", "비교에서 쓰이는 곳"],
        [["<code>rvfi_valid</code>", "이번 사이클에 명령어가 retire 됐다", "비교 시점을 정한다"],
         ["<code>rvfi_order</code>", "프로그램 순서 번호", "순서 뒤바뀜 검출"],
         ["<code>rvfi_insn</code>", "retire 된 명령어 인코딩", "모델에 같은 것을 먹인다"],
         ["<code>rvfi_pc_rdata/wdata</code>", "명령어 전/후 PC", "분기 정확성"],
         ["<code>rvfi_rs1/rs2_addr,rdata</code>", "읽은 레지스터", "모델 입력 대조"],
         ["<code>rvfi_rd_addr,wdata</code>", "쓴 레지스터", "결과 대조"],
         ["<code>rvfi_mem_addr,rmask,wmask,rdata,wdata</code>", "메모리 접근", "메모리 부작용"],
         ["<code>rvfi_trap</code>", "예외 발생", "예외 의미 대조"]]))
    s.append(f"""<p>이 교안에는 RVFI UVM 에이전트 구현이 {rvfi:,}줄 들어 있고
    (<code>lib/uvm_agents/uvma_rvfi/</code>), DUT 쪽 구현도 있다
    (<code>cv32e40p/bhv/cv32e40p_rvfi.sv</code>).</p>""")
    s.append("""<div class="note"><b>당신 회사에 RVFI 가 없다면 그에 해당하는 것을
    찾아라.</b> 이름이 다를 뿐 모든 팀에 있다 &mdash; retire 트레이스, commit log,
    monitor 포트. <b>없다면 그것을 만드는 것이 첫 과제다.</b> 트레이스 포트가 없으면
    비교 자체를 할 수 없다.</div>""")

    s.append("<h2>4.3 비교 시점 &mdash; 실무에서 제일 많이 싸우는 자리</h2>")
    s.append(표("무엇을 언제 비교할 것인가",
        ["대상", "비교 시점", "함정"],
        [["아키텍처 상태(레지스터 · 메모리)", "명령어 retire 순간",
          "파이프라인 때문에 RTL 내부에는 여러 시점이 공존한다"],
         ["CSR", "retire 직후. 단, 부작용이 늦게 반영되는 것 주의",
          "카운터(<code>mcycle</code>)는 <b>절대 비교하면 안 된다</b> &mdash; 모델에 사이클 개념이 없다"],
         ["인터럽트", "DV 가 모델에 &lsquo;지금 들어왔다&rsquo;고 주입한 뒤",
          "주입 시점이 한 사이클 어긋나면 전부 틀어진다"],
         ["메모리 순서", "약한 순서 모델에서는 <b>단일 시점 비교 불가</b>",
          "리터먼트 순서가 아니라 <i>허용 가능한 순서 집합</i>과 비교해야 한다"],
         ["성능 카운터 · 캐시 상태", "<b>비교하지 않는다</b>", "모델이 흉내내지 않는 영역"]]))
    return "\n".join(s)


def ch5():
    s = ['<h1 id="c5">5장. 첫 주 &mdash; 무엇을 묻고 무엇을 만드나</h1>']
    s.append("<h2>5.1 출근 첫날 물어볼 것 열 가지</h2>")
    s.append(표("첫 주 질문지 (답을 못 받으면 그것 자체가 정보다)",
        ["#", "질문", "왜 중요한가"],
        [["1", "우리 골든 모델은 무엇인가? 자체 제작인가, 상용(Imperas 등)인가?",
          "자체면 당신이 고칠 수 있고, 상용이면 계약 범위가 한계다"],
         ["2", "모델과 RTL 의 <b>트레이스 인터페이스</b>는 무엇인가?",
          "없으면 그것을 만드는 게 첫 과제다"],
         ["3", "회귀는 하루에 몇 번 도나? 한 번에 몇 시간인가?",
          "모델 성능 요구가 여기서 나온다"],
         ["4", "명세는 무엇인가? 표준 문서인가, 사내 스펙인가, 구두인가?",
          "구두면 모델이 사실상의 명세가 된다 &mdash; 책임이 커진다"],
         ["5", "미정의 동작은 어떻게 처리하고 있나?", "3장 1.5절의 (가)(나)(다) 중 무엇인가"],
         ["6", "커버리지는 무엇을 재나? 기능 커버리지가 있나?",
          "없으면 &lsquo;다 돌렸다&rsquo;를 말할 수 없다"],
         ["7", "모델 자체의 검증은 누가 하나?", "대개 공백이다. 여기가 당신의 첫 기여 자리다"],
         ["8", "부동소수점/고정소수점이 있나? 비트 정확한가?", "가장 비싼 버그가 여기서 난다"],
         ["9", "모델은 어떤 언어/빌드인가? C++ 표준은? SystemC 를 쓰나?", "환경 파악"],
         ["10", "지난 6개월에 놓친 버그(escape)가 있었나? 왜 놓쳤나?",
          "<b>이 질문 하나가 나머지 아홉보다 많은 것을 알려 준다</b>"]]))

    s.append("<h2>5.2 도구 &mdash; 이 교안에 실물이 들어 있는 것들</h2>")
    from book import 줄수 as L
    s.append(표("모델링·검증 도구",
        ["도구", "무엇", "규모", "언제 쓰나"],
        [["<b>Verilator</b>", "RTL &rarr; C++ 변환·시뮬레이션", f"{L('model','verilator_verilator'):,}줄",
          "모델과 RTL 을 <b>한 프로세스</b>에서 돌린다. 무료. 사이클 정확"],
         ["<b>SystemC / TLM 2.0</b>", "C++ 하드웨어 모델링 표준",
          f"{L('model','accellera-official_systemc'):,}줄",
          "가상 플랫폼 · 아키텍처 탐색. 대기업 표준"],
         ["<b>cocotb</b>", "파이썬으로 HDL 공동시뮬", f"{L('model','cocotb_cocotb'):,}줄",
          "UVM 없이 빠르게 테스트벤치. 모델이 파이썬일 때"],
         ["<b>Spike</b>", "RISC-V ISS", f"{L('model','riscv-software-src_riscv-isa-sim'):,}줄",
          "참조모델의 교과서"],
         ["<b>Sail</b>", "형식 ISA 명세 &rarr; C 에뮬레이터 생성",
          f"{L('model','riscv_sail-riscv'):,}줄", "명세와 모델을 한 원천에서"],
         ["<b>gem5</b>", "아키텍처 성능 시뮬레이터", f"{L('model','gem5_gem5'):,}줄",
          "성능 예측 · 아키텍처 탐색. <b>기능 모델과 다르다</b>"],
         ["<b>aff3ct</b>", "FEC 시뮬레이터(RS·LDPC·Polar·Turbo)",
          f"{L('model','aff3ct_aff3ct'):,}줄", "통신 IP 참조모델"],
         ["<b>liquid-dsp</b>", "통신 DSP C 라이브러리", f"{L('model','jgaeddert_liquid-dsp'):,}줄",
          "변복조 · 필터 참조"],
         ["<b>OpenSSL</b>", "암호 참조", f"{L('model','openssl_openssl'):,}줄",
          "암호 IP 의 골든. NIST 벡터 포함"],
         ["Verible", "SystemVerilog 파서·린터", f"{L('model','chipsalliance_verible'):,}줄",
          "RTL 을 프로그램으로 다뤄야 할 때"]]))

    s.append("<h2>5.3 DPI-C &mdash; C 모델을 SystemVerilog 에 붙이는 표준 통로</h2>")
    s.append("""<p>IEEE 1800 의 <b>DPI-C</b>(Direct Programming Interface)가 표준 방법이다.
    SystemVerilog 가 C 함수를 직접 부른다.</p>
    <pre class="code"><span class="cap">C 쪽 -- 평범한 C++ 로 컴파일된다</span>
extern "C" void ref_step(const svOpenArrayHandle in, svOpenArrayHandle out);

<span class="cap">SystemVerilog 쪽</span>
import "DPI-C" function void ref_step(input int in[], output int out[]);
...
ref_step(stim, expected);
dut_step(stim, actual);
if (actual !== expected) $fatal(1, "mismatch at vector %0d", i);</pre>""")
    s.append("""<div class="warn"><b>흔한 오해를 하나 정정한다.</b> "UVM 이 DPI 로
    참조모델을 제공한다" 는 말이 돌지만 <b>사실이 아니다</b>. UVM 의 DPI 계층은
    배선용 도구일 뿐이다 &mdash; <code>uvm_hdl_read</code>,
    <code>uvm_hdl_deposit</code>, <code>uvm_hdl_force</code>, 정규식, 도구 이름 질의.
    크기가 그것을 말한다: <code>uvm_component.svh</code> 가 122,681바이트인데
    <code>uvm_dpi.cc</code> 는 2,658바이트다 &mdash; <b>46배</b>.
    <b>알고리즘 모델은 당신이 쓴다.</b> 방법론이 주지 않는다.</div>""")

    s.append("<h2>5.4 첫 달에 만들면 좋은 것</h2>")
    s.append(표("기여할 자리 &mdash; 대개 비어 있다",
        ["만들 것", "왜 비어 있나", "효과"],
        [["<b>모델 자체의 회귀</b>(모델 vs 독립 구현)",
          "모델이 정답이라 아무도 모델을 검사하지 않는다", "가장 비싼 버그를 막는다"],
         ["<b>변이 시험</b>(모델을 일부러 망가뜨려 검사가 무는지)",
          "시간이 없어서 안 한다", "죽은 검사를 찾아낸다"],
         ["<b>커버리지 계측</b>(모델이 어떤 경로를 안 밟았나)",
          "RTL 커버리지만 보는 팀이 많다", "자극의 빈틈을 본다"],
         ["<b>불일치 삼분법 자동화</b>(3.3절)",
          "매번 손으로 판단한다", "분류 시간을 줄인다"],
         ["<b>규격 절번호 &rarr; 코드 위치 표</b>",
          "문서화가 뒤로 밀린다", "새 사람이 올 때마다 값을 한다"]]))
    return "\n".join(s)
