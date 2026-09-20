# -*- coding: utf-8 -*-
"""한국어 질문을 **영어 교재의 말**로 바꾼다.

## 왜 필요한가

교재는 영어로 지었고(사용자 지시: 토큰을 아끼려고 영어로 쓰고 번역은 따로),
사용자는 한국어로 묻는다.  "준안정 상태 MTBF 어떻게 잡아?" 를 그대로
영어 본문에 대고 훑으면 **한 글자도 안 맞는다.**  그러면 찾기가 빈손으로
오고, 봇은 근거 없이 기억으로 답하게 된다 -- 이 저장소가 가장 싫어하는 꼴이다.

## 못 바꾼 말을 숨기지 않는다

표에 없는 한국어 말은 바꿀 수 없다.  그때 **조용히 빠뜨리지 않고**
`못바꾼말` 로 돌려준다.  답에 그것이 적히면, 왜 엉뚱한 절이 왔는지
사용자가 바로 안다 -- 그리고 그 말을 표에 더하면 된다.

표를 늘릴 때는 `tests/test_kb.py` 의 물음-정답 짝을 같이 늘린다.
**늘린 말이 실제로 옳은 절을 끌어오는지 기계가 본다.**
"""
import re

# 한국어 -> 영어 교재 말.  긴 것부터 맞춘다(아래에서 길이순 정렬).
표 = {
    # --- 소자 ---
    "문턱전압": "threshold voltage vth",
    "과구동": "overdrive voltage vov gate source",
    "차단영역": "cutoff region subthreshold",
    "차단": "cutoff region",
    "선형영역": "triode linear region",
    "삼극관": "triode region",
    "포화영역": "saturation region",
    "포화": "saturation",
    "아문턱": "subthreshold conduction swing",
    "서브스레숄드": "subthreshold swing",
    "트랜스컨덕턴스": "transconductance gm",
    "출력저항": "output resistance ro early voltage",
    "채널길이변조": "channel length modulation lambda early",
    "바디효과": "body effect back gate bias",
    "기판효과": "body effect",
    "누설": "leakage current subthreshold gate induced drain",
    "게이트용량": "gate capacitance cox cgs cgd",
    "이동도": "mobility carrier velocity saturation",
    "속도포화": "velocity saturation short channel",
    "단채널": "short channel effect dibl",
    "공핍": "depletion region",
    "반전층": "inversion layer strong weak inversion",
    "약반전": "weak inversion subthreshold",
    "공정변이": "process variation corner mismatch",
    "코너": "process corner ss ff tt slow fast",
    "미스매치": "mismatch pelgrom sigma matching",
    "펠그롬": "pelgrom mismatch coefficient area",
    "산화막": "gate oxide tox",
    "모스": "mosfet transistor nmos pmos",
    "트랜지스터": "transistor mosfet device",

    # --- 디지털 회로 ---
    "인버터": "cmos inverter",
    "논리게이트": "logic gate nand nor",
    "낸드": "nand gate",
    "노어": "nor gate",
    "풀업": "pull up network pmos",
    "풀다운": "pull down network nmos",
    "전파지연": "propagation delay tpd",
    "지연": "delay propagation",
    "슬루": "slew rate transition time",
    "천이시간": "transition time slew",
    "논리적노력": "logical effort electrical effort fanout",
    "팬아웃": "fanout fo4 load",
    "부하": "load capacitance fanout",
    "엘모어": "elmore delay rc wire",
    "배선지연": "wire interconnect rc delay repeater",
    "리피터": "repeater buffer insertion wire",
    "스택": "stack series transistor",
    "전달게이트": "transmission gate pass",
    "동적논리": "dynamic logic domino precharge",
    "도미노": "domino dynamic logic",
    "표준셀": "standard cell library liberty",
    "라이브러리": "liberty library cell characterization",
    "특성화": "characterization liberty nldm ccs",
    "구동세기": "drive strength cell sizing",
    "사이징": "sizing gate size drive",

    # --- 순차·타이밍 ---
    "플립플롭": "flip flop dff register",
    "래치": "latch transparent level sensitive",
    "셋업": "setup time constraint",
    "홀드": "hold time constraint",
    "셋업타임": "setup time",
    "홀드타임": "hold time",
    "타이밍": "timing static analysis sta path",
    "정적타이밍": "static timing analysis sta",
    "임계경로": "critical path worst slack",
    "슬랙": "slack setup hold timing",
    "스큐": "clock skew",
    "지터": "jitter clock uncertainty",
    "클럭": "clock tree period frequency",
    "클럭트리": "clock tree synthesis cts skew",
    "클럭게이팅": "clock gating enable power",
    "준안정": "metastability metastable resolution",
    "준안정상태": "metastability metastable window",
    "결정시간": "resolution time constant metastability",
    "동기화기": "synchronizer two flop cdc",
    "이중동기화": "two flip flop synchronizer",
    "그레이코드": "gray code pointer fifo cdc",
    "비동기": "asynchronous cdc handshake",
    "클럭도메인": "clock domain crossing cdc",
    "재수렴": "reconvergence cdc multi bit",
    "리셋": "reset synchronous asynchronous release",
    "리셋동기화": "reset synchronizer recovery removal",
    "리커버리": "recovery removal reset timing",
    "다중사이클": "multicycle path exception",
    "거짓경로": "false path timing exception",

    # --- 검증 ---
    "검증": "verification testbench coverage",
    "테스트벤치": "testbench stimulus checker",
    "골든모델": "golden model reference c++",
    "커버리지": "coverage functional code bins",
    "변이점수": "mutation score escape",
    "변이": "mutation testing escape",
    "자해검사": "self check corrupt golden negative test",
    "형식검증": "formal verification property assertion bmc",
    "정형검증": "formal property proof induction",
    "어서션": "assertion sva property",
    "등가검증": "equivalence checking lec",
    "제약랜덤": "constrained random stimulus",
    "회귀": "regression suite nightly",
    "서명": "signoff gate checklist",
    "사인오프": "signoff criteria",

    # --- 아키텍처·RTL ---
    "파이프라인": "pipeline stage register retiming",
    "리타이밍": "retiming pipeline balance",
    "스키드버퍼": "skid buffer ready valid backpressure",
    "역압": "backpressure ready valid stall",
    "핸드셰이크": "handshake ready valid",
    "버스": "bus axi apb interconnect",
    "상태기계": "state machine fsm encoding",
    "유한상태기계": "fsm state machine one hot",
    "레지스터맵": "register map csr apb address",
    "고정소수점": "fixed point quantization width",
    "양자화": "quantization error noise bits",
    "포화연산": "saturation clipping overflow",
    "넘침": "overflow wrap saturate",
    "반올림": "rounding convergent truncation",
    "비트폭": "bit width word length growth",
    "누산기": "accumulator adder datapath",
    "가산기": "adder carry lookahead ripple",
    "곱셈기": "multiplier booth wallace partial product",
    "나눗셈": "divider restoring newton",
    "시프트": "shifter barrel",
    "메모리": "memory sram register file",
    "에스램": "sram bitcell bitline sense amplifier noise margin",
    "디램": "dram refresh bank row",
    "피포": "fifo depth pointer full empty",
    "큐": "queue fifo latency throughput",

    # --- 신호·통신 ---
    "표본화": "sampling nyquist aliasing",
    "엘리어싱": "aliasing folding nyquist",
    "오버샘플링": "oversampling ratio noise shaping",
    "필터": "filter fir iir response",
    "등화": "equalization ffe dfe ctle",
    "등화기": "equalizer dfe ffe tap",
    "판정귀환": "decision feedback equalizer dfe",
    "아이다이어그램": "eye diagram opening margin",
    "지터버짓": "jitter budget rj dj bathtub",
    "비트에러율": "bit error rate ber",
    "링크버짓": "link budget loss margin",
    "직렬화": "serializer serdes parallel",
    "클럭복원": "clock data recovery cdr",
    "위상고정": "phase locked loop pll",
    "피엘엘": "pll loop filter vco charge pump",
    "디엘엘": "dll delay locked loop",
    "브이시오": "vco oscillator phase noise",
    "위상잡음": "phase noise oscillator jitter",
    "전하펌프": "charge pump pll current",
    "루프필터": "loop filter bandwidth stability pll",
    "분주기": "divider prescaler pll",
    "확산스펙트럼": "spread spectrum ssc clocking",
    "프리엠파시스": "pre emphasis de emphasis driver",
    "채널손실": "channel loss insertion skin dielectric",
    "반사": "reflection impedance mismatch termination",
    "종단": "termination impedance matching",
    "임피던스": "impedance transmission line",
    "전송선": "transmission line characteristic impedance",
    "크로스토크": "crosstalk coupling aggressor victim",
    "디엠퍼시스": "de emphasis equalization transmit",

    # --- 부호 ---
    "부호화": "encoding coding line code",
    "선로부호": "line code 8b10b 64b66b dc balance",
    "스크램블러": "scrambler lfsr polynomial",
    "디스패리티": "running disparity 8b10b balance",
    "콤마": "comma character alignment k28",
    "오류정정": "error correction ecc fec",
    "해밍": "hamming code sec ded syndrome",
    "패리티": "parity bit check",
    "신드롬": "syndrome decoder error",
    "씨알씨": "crc polynomial checksum",
    "리드솔로몬": "reed solomon galois field",
    "엘디피씨": "ldpc parity check min sum",
    "비터비": "viterbi trellis decoder",
    "인터리버": "interleaver burst error",

    # --- 전력·물리 ---
    "전력": "power dynamic static switching",
    "동적전력": "dynamic power switching activity capacitance",
    "누설전력": "leakage power static",
    "전력영역": "power domain upf isolation retention",
    "전압섬": "voltage island power domain",
    "레벨시프터": "level shifter voltage domain",
    "아이솔레이션": "isolation cell power gating",
    "리텐션": "retention flop state power gating",
    "파워게이팅": "power gating sleep transistor",
    "디브이에프에스": "dvfs voltage frequency scaling",
    "전원무결성": "power integrity ir drop decap",
    "아이알드롭": "ir drop power grid",
    "디캡": "decoupling capacitor decap",
    "일렉트로마이그레이션": "electromigration current density reliability",
    "열": "thermal temperature hotspot",
    "노화": "aging bti hci reliability",
    "정전기": "esd protection clamp",
    "레이아웃": "layout floorplan place route",
    "플로어플랜": "floorplan macro placement",
    "배치배선": "place and route congestion",
    "디알씨": "drc design rule check",
    "엘브이에스": "lvs layout versus schematic",
    "기생": "parasitic extraction rc",
    "안테나": "antenna rule diode layout",

    # --- 아날로그 ---
    "증폭기": "amplifier gain stage ota",
    "연산증폭기": "operational amplifier opamp ota",
    "차동쌍": "differential pair tail current",
    "전류미러": "current mirror bias",
    "캐스코드": "cascode gain output impedance",
    "밴드갭": "bandgap reference ptat ctat",
    "기준전압": "reference voltage bandgap",
    "바이어스": "bias current point operating",
    "피드백": "feedback loop gain stability",
    "위상여유": "phase margin stability compensation",
    "보상": "compensation miller pole zero",
    "극점": "pole zero frequency response",
    "잡음": "noise thermal flicker kt/c",
    "열잡음": "thermal noise resistor kt",
    "플리커": "flicker 1/f noise",
    "스위치커패시터": "switched capacitor charge redistribution",
    "차지인젝션": "charge injection clock feedthrough",
    "비교기": "comparator offset kickback",
    "에이디씨": "adc converter sar pipeline sigma delta",
    "디에이씨": "dac converter resolution inl dnl",
    "시그마델타": "sigma delta modulator noise shaping",
    "축차비교": "sar successive approximation adc",
    "유효비트": "enob sndr effective number of bits",
    "비선형": "nonlinearity inl dnl distortion",
    "샘플홀드": "sample and hold track",

    # --- 도구·흐름 ---
    "합성": "synthesis yosys netlist mapping",
    "논리합성": "logic synthesis optimization mapping",
    "배치": "placement",
    "타이밍제약": "sdc constraint create clock",
    "제약파일": "sdc constraints timing",
    "에이치엘에스": "high level synthesis hls c++",
    "고수준합성": "high level synthesis hls pragma",
    "시뮬레이션": "simulation iverilog verilator",
    "파형": "waveform vcd gtkwave",
    "린트": "lint rule check",
    "네트리스트": "netlist gate level",
    "스파이스": "spice simulation netlist",
    "피피지에이": "fpga lut ice40 nextpnr",

    # --- 사업·문서 ---
    "데이터시트": "datasheet specification numbers",
    "납품": "deliverable package handoff",
    "스펙": "specification requirements interface",
    "특허": "patent claim prior art",
    "청구항": "patent claim independent dependent",
    "선행기술": "prior art search novelty",
    "라이선스": "license royalty ip business",
    "값매기기": "pricing ip value",
    "포트폴리오": "portfolio ip products",

    # --- 구조·마이크로아키텍처 (2차 보강 2026-09-20) ---
    "언롤링": "unrolling unrolled speculative loop",
    "루프언롤링": "loop unrolling speculation",
    "투기": "speculative speculation precompute",
    "룩어헤드": "look ahead lookahead recursion parallel",
    "재귀": "recursion feedback loop iteration",
    "되먹임": "feedback loop recursive",
    "임계루프": "critical loop iteration bound recursion",
    "반복한계": "iteration bound recursion throughput",
    "접기": "folding resource sharing time multiplex",
    "폴딩": "folding resource sharing",
    "병렬화": "parallel unfold throughput area",
    "자원공유": "resource sharing area multiplexer",
    "원핫": "one hot encoding state",
    "우선순위": "priority encoder arbitration",
    "중재기": "arbiter round robin grant request",
    "아비터": "arbiter fairness grant",
    "라운드로빈": "round robin arbitration fairness",
    "크로스바": "crossbar switch interconnect",
    "처리량": "throughput bandwidth rate",
    "지연시간": "latency cycles",
    "면적": "area gate count lut utilization",
    "전력소모": "power consumption dynamic leakage",
    "수율": "yield defect density",
    "성능": "performance throughput frequency",
    "병목": "bottleneck critical path limiting",
    "버퍼": "buffer fifo queue depth",
    "인터럽트": "interrupt request status register",
    "디버그": "debug trace visibility",
    "스캔": "scan chain dft shift capture",
    "스캔체인": "scan chain atpg test",
    "테이프아웃": "tape out mask signoff",
    "파운드리": "foundry process node pdk",
    "피디케이": "pdk process design kit",
    "패키지": "package bond wire bump",
    "인터포저": "interposer 2.5d chiplet",
    "칩렛": "chiplet die to die interface",
    "리던던시": "redundancy repair spare",
    "워치독": "watchdog timeout recovery",
    "시뮬레이션속도": "simulation speed runtime cycles per second",
    "검증시간": "verification time runtime regression",
    "회귀시험": "regression suite nightly",
    "체크섬": "checksum crc integrity",
    "커버그룹": "covergroup bins functional coverage",
    "랜덤시드": "seed random stimulus reproducible",
    "파형덤프": "waveform vcd fsdb dump",
    "합성제약": "sdc constraint synthesis timing",
    "타이밍예외": "timing exception false path multicycle",
    "유틸라이제이션": "utilization density placement",
    "혼잡": "congestion routing placement",
    "클럭분배": "clock distribution tree mesh",
    "게이트수": "gate count area equivalent",
    "표준편차": "sigma standard deviation variation",
    "몬테카를로": "monte carlo variation yield",
    "감도": "sensitivity derivative variation",
    "여유": "margin guard band slack",
    "마진": "margin guard band",
    "버짓": "budget allocation margin",
    # --- 조사가 붙어도 걸리게, 밑말 자체를 넣는다 (실측 2026-09-20:
    #     "배선에" · "단수를" 가 못 바꾼 말로 나왔다) ---
    "배선": "wire interconnect routing metal",
    "단수": "stage count number of stages",
    "노력": "effort logical electrical",
    "여유": "margin slack guard band",
    "상태": "state condition operating point",
    "동작점": "operating point bias condition",
    "파형": "waveform transition edge",
    "잡음여유": "noise margin static butterfly",
    "게이트": "gate logic cell transistor gate",
    "소자": "device transistor mosfet",
    "회로": "circuit schematic topology",
    "설계": "design implementation methodology",
    "구현": "implementation rtl netlist",
    "합성기": "synthesis tool yosys",
    "시험": "test verification stimulus",
    "측정": "measurement measured characterization",
    "규격": "specification standard requirement",
    "표준": "standard specification protocol",
    "오차": "error deviation tolerance",
    "한계": "limit bound maximum",
    # --- 표준 ---
    "미피": "mipi csi dsi d-phy lane",
    "씨에스아이": "mipi csi-2 packet ecc",
    "디에스아이": "mipi dsi display packet",
    "피시아이": "pcie link training ltssm gen",
    "이더넷": "ethernet gmac mac phy",
    "지맥": "gmac ethernet mac gmii",
    "에이엑스아이": "axi burst channel id outstanding",
    "에이피비": "apb register bus psel penable",
    "제이택": "jtag tap boundary scan",
}

# 영어 줄임말 -> 본문이 실제로 쓰는 말.
#
# 실측 2026-09-20: "IR drop 과 decap 을 어떻게 잡아?" 가 PDN 장(X32)을 못 찾았다.
# 본문은 `decoupling capacitor` 라고 적고 사용자는 `decap` 이라고 쓴다 -- 코퍼스
# 전체에 `decap` 은 **한 번** 나온다.  줄임말은 현장에서 쓰는 말이고 교재는 풀어
# 쓰니, 둘을 여기서 잇는다.  이어 두지 않으면 **가장 자주 쓰는 말로 물었을 때
# 못 찾는다** -- 가장 나쁜 실패다.
영어별칭 = {
    "decap": "decoupling capacitor bypass",
    "ir drop": "voltage drop power grid resistive",
    "snm": "static noise margin sram butterfly",
    "mtbf": "mean time between failures metastability resolution",
    "fo4": "fanout of four delay inverter",
    "cdc": "clock domain crossing synchronizer",
    "sta": "static timing analysis slack path",
    "dfe": "decision feedback equalizer tap",
    "ffe": "feed forward equalizer tap precursor",
    "ctle": "continuous time linear equalizer peaking",
    "cdr": "clock and data recovery phase detector",
    "ber": "bit error rate",
    "enob": "effective number of bits sndr",
    "inl": "integral nonlinearity converter",
    "dnl": "differential nonlinearity converter",
    "sdc": "synopsys design constraints create_clock timing",
    "upf": "unified power format power domain isolation retention",
    "ecc": "error correcting code hamming syndrome",
    "crc": "cyclic redundancy check polynomial",
    "axi": "axi burst channel outstanding handshake",
    "apb": "apb register bus psel penable",
    "csi": "mipi csi-2 camera packet lane",
    "dsi": "mipi dsi display packet lane",
    "ltssm": "link training status state machine pcie",
    "fifo": "fifo depth pointer full empty",
    "lut": "lookup table fpga logic",
    "sram": "sram bitcell bitline sense amplifier",
    "dram": "dram refresh row bank activate",
    "esd": "electrostatic discharge clamp protection",
    "dvfs": "dynamic voltage frequency scaling",
    "bti": "bias temperature instability aging",
    "hci": "hot carrier injection aging",
    "em": "electromigration current density",
    "snr": "signal to noise ratio",
    "sndr": "signal to noise and distortion ratio",
    "pvt": "process voltage temperature corner",
    "rtl": "register transfer level verilog",
    "hls": "high level synthesis c++ pragma",
    "pdn": "power delivery network target impedance",
    "cts": "clock tree synthesis skew",
    "drc": "design rule check layout",
    "lvs": "layout versus schematic",
    "ate": "automatic test equipment production test",
    "dft": "design for test scan atpg",
    "atpg": "automatic test pattern generation fault coverage",
    "bist": "built in self test memory",
    "sva": "systemverilog assertion property",
    "uvm": "universal verification methodology sequence",
    "vip": "verification ip protocol checker",
    "trm": "technical reference manual register",
    "pll": "phase locked loop loop filter vco",
    "vco": "voltage controlled oscillator phase noise",
    "adc": "analog to digital converter",
    "dac": "digital to analog converter",
    "ota": "operational transconductance amplifier",
    "gm": "transconductance gm/id",
    "kt/c": "sampling noise kt over c",
    "8b/10b": "8b10b running disparity comma",
    "64b/66b": "64b66b scrambler sync header",
    "serdes": "serializer deserializer link",
    "phy": "physical layer analog front end",
    "mac": "media access control ethernet",
    "gmii": "gigabit media independent interface",
    "qor": "quality of results area timing power",
    "fmax": "maximum frequency critical path",
}

# 영어로 물어도 그대로 통하게 -- 한글 열쇠만 바꾼다.
_열쇠 = sorted(표, key=len, reverse=True)
_한글 = re.compile(r"[가-힣]+")

# 주제를 하나도 안 가리키는 물음말.  못 바꿨다고 **보고할 필요도 없다** --
# 보고가 잡음으로 차면 정작 빠진 전문 용어가 안 보인다.
흔한말 = {
    "무엇", "뭐야", "뭔가", "뭐고", "어떻게", "어떤", "어디", "언제", "왜냐",
    "알려줘", "설명", "설명해", "해줘", "주세요", "인가", "인지", "하는",
    "되는", "이란", "라는", "무슨", "그리고", "하면", "때문", "정도", "관련",
    "방법", "경우", "사용", "부분", "이유", "처럼", "이렇게", "그것",
    "우리", "내가", "지금", "다시", "가장", "조금", "제일", "전부", "모두",
    "차이", "비교", "장단점", "예시", "예를", "들어", "대해", "대한", "관해",
    "있나", "있어", "없나", "없어", "인데", "인가요", "일까", "할까", "한가",
    "커지나", "작아지나", "늘어나", "줄어드",
}


def 넓히기(질문: str):
    """(찾기에 쓸 말, 바꾼 것, 못 바꾼 한국어 말)

    **못 바꾼 한국어 말은 찾기에 쓰지 않는다.**  실측 2026-09-20: "SRAM 의 SNM 이
    뭐야?" 가 SRAM 장이 아니라 한국어로 쓰인 엉뚱한 장들을 끌어왔다 -- "뭐야" ·
    "어떻게" 같은 **물음말이 한국어 장과 맞아서**다.  그런 말은 주제를 하나도
    가리키지 않는데 점수만 흔든다.  그래서 돌려주는 첫 칸(찾기에 쓸 말)에는
    **영어와, 표에 있어서 뜻을 아는 한국어 말만** 담는다.  못 바꾼 말은 셋째 칸으로
    나가 답에 적힌다 -- 버리는 것이 아니라 **보이게** 하는 것이다.
    """
    # 한국어 낱말 사이의 띄어쓰기를 지우고 맞춘다.  실측 2026-09-20: 표의 열쇠는
    # `클럭도메인` 인데 사용자는 "클럭 도메인" 이라고 쓴다 -- 붙여 쓴 열쇠가 영영
    # 안 맞아 CDC 장을 못 찾았다.  띄어쓰기는 뜻을 안 바꾸므로 맞추기 전에 지운다.
    남은 = re.sub(r"(?<=[가-힣])\s+(?=[가-힣])", "", 질문)
    더한것 = []
    바뀐것 = {}
    for k in _열쇠:
        if k in 남은:
            바뀐것[k] = 표[k]
            더한것.append(표[k])
            더한것.append(k)          # 한국어로 쓰인 장도 같은 말로 맞는다
            남은 = 남은.replace(k, " ")
    # 못 바꾼 말은 **원래 물음의 낱말 그대로** 적는다.  띄어쓰기를 지운 사본에서
    # 뽑으면 "깍두기 볶음밥 레시피" 가 `깍두기볶음밥레시피` 한 덩이로 나와, 사용자가
    # 어느 말이 빠졌는지 못 읽는다(실측 2026-09-20).
    맞은것 = "".join(바뀐것)
    못바꾼 = sorted({w for w in _한글.findall(질문)
                   if len(w) >= 2 and w not in 맞은것
                   and w not in 흔한말
                   and not any(w in k or k in w for k in 바뀐것)})
    영어만 = " ".join(re.findall(r"[A-Za-z0-9/._+-]+", 질문))
    낮춤 = " " + 질문.lower() + " "
    for k, v in 영어별칭.items():
        if re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", 낮춤):
            바뀐것[k] = v
            더한것.append(v)
    return (영어만 + " " + " ".join(더한것)).strip(), 바뀐것, 못바꾼


def 표크기():
    return len(표)
