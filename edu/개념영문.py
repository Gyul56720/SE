# -*- coding: utf-8 -*-
"""사다리 개념의 **영어 이름** -- 영어판 틀에서 쓴다.

`bookK` 의 사다리는 개념을 한국어 열쇠로 들고 있다(`쓰는것`·`내놓는것`).  그
열쇠는 **기계가 순서를 검사하는 데 쓰는 이름**이라 한국어여도 상관없지만,
영어판 PDF 의 "Before you read this / New in this chapter" 상자에 그대로 찍히면
영어 독자가 읽을 수 없다.

그래서 여기 한 벌만 둔다.  없는 열쇠는 **그대로 둔다**(빠뜨린 것이 눈에 띄게).
`tests/test_사다리.py` 가 T 계열의 모든 개념에 영어 이름이 있는지 본다.
"""
영문 = {
    # --- 소자 ---
    "문턱전압": "threshold voltage", "차단영역": "cutoff region",
    "선형영역": "triode region", "포화영역": "saturation region",
    "아문턱영역": "subthreshold region", "아문턱기울기": "subthreshold swing",
    "온저항": "on-resistance", "트랜스컨덕턴스": "transconductance",
    "출력저항": "output resistance", "채널길이변조": "channel-length modulation",
    "바디효과": "body effect", "게이트용량": "gate capacitance",
    "누설전류": "leakage current",
    # --- 지연 ---
    "RC지연": "RC delay", "엘모어지연": "Elmore delay",
    "논리적노력": "logical effort", "전기적노력": "electrical effort",
    "기생지연": "parasitic delay", "FO4": "FO4 delay", "슬루": "slew",
    "단락전류": "short-circuit current", "배선지연": "wire delay",
    "리피터": "repeater", "NLDM": "NLDM", "비선형지연모델": "non-linear delay model",
    "도착시각": "arrival time", "요구시각": "required time", "슬랙": "slack",
    "OCV": "on-chip variation",
    # --- 준안정·CDC ---
    "준안정": "metastability", "결정시간상수": "resolution time constant",
    "해결시간": "resolution time", "준안정창": "metastability window",
    "MTBF": "MTBF", "동기화기깊이": "synchroniser depth",
    "다중비트문제": "multi-bit crossing", "재수렴": "reconvergence",
    "그레이코드": "gray code", "핸드셰이크": "handshake",
    "비동기FIFO": "asynchronous FIFO", "리셋동기화기": "reset synchroniser",
    "리커버리": "recovery time", "리무벌": "removal time",
    "CDC검증": "CDC verification", "준정적신호": "quasi-static signal",
    # --- 잡음 ---
    "열잡음": "thermal noise", "산탄잡음": "shot noise",
    "플리커잡음": "flicker noise", "잡음스펙트럼밀도": "noise spectral density",
    "잡음대역폭": "noise bandwidth", "kTC잡음": "kT/C noise",
    "입력환산잡음": "input-referred noise", "플리커코너": "flicker corner",
    "잡음지수": "noise figure", "정적잡음여유": "static noise margin",
    "나비곡선": "butterfly curve", "읽기방해": "read disturb",
    "최소동작전압": "V_min", "SNR": "SNR", "SNDR": "SNDR", "ENOB": "ENOB",
    # --- 표본화 ---
    "표본화정리": "sampling theorem", "엘리어싱": "aliasing",
    "나이키스트": "Nyquist", "대역통과표본화": "bandpass sampling",
    "구경시간": "aperture time", "구경지터": "aperture jitter",
    "지터한계SNR": "jitter-limited SNR", "추적유지": "track and hold",
    "트래킹대역폭": "tracking bandwidth", "차지인젝션": "charge injection",
    "클럭피드스루": "clock feedthrough", "부트스트랩스위치": "bootstrapped switch",
    "오버샘플링비": "oversampling ratio", "잡음성형": "noise shaping",
    "데시메이션": "decimation",
    # --- 변환기 ---
    "플래시ADC": "flash ADC", "축차비교ADC": "SAR ADC",
    "파이프라인ADC": "pipeline ADC", "시간인터리브": "time interleaving",
    "용량DAC": "capacitive DAC", "전류구동DAC": "current-steering DAC",
    "세그먼테이션": "segmentation", "INL": "INL", "DNL": "DNL",
    "미싱코드": "missing code", "단조성": "monotonicity",
    "중복성": "redundancy", "디지털보정": "digital calibration",
    "글리치에너지": "glitch energy", "정합": "matching",
    # --- PLL ---
    "위상검출기": "phase detector", "전하펌프": "charge pump",
    "루프필터": "loop filter", "전압제어발진기": "VCO", "분주기": "divider",
    "고리이득": "loop gain", "감쇠비": "damping factor",
    "자연주파수": "natural frequency", "루프대역폭": "loop bandwidth",
    "위상잡음": "phase noise", "적분지터": "integrated jitter",
    "기준스퍼": "reference spur", "분수분주": "fractional-N",
    "델타시그마변조": "delta-sigma modulation", "확산스펙트럼": "spread spectrum",
    "락검출": "lock detect", "전원푸싱": "supply pushing",
    # --- 링크 ---
    "심볼간간섭": "intersymbol interference", "펄스응답": "pulse response",
    "커서": "cursor", "선행커서": "pre-cursor", "후행커서": "post-cursor",
    "최악왜곡": "peak distortion", "아이다이어그램": "eye diagram",
    "CTLE": "CTLE", "FFE": "FFE", "DFE": "DFE",
    "오류전파": "error propagation", "비트오류율": "bit error rate",
    "3의법칙": "rule of three", "클럭데이터복원": "clock and data recovery",
    "지터허용": "jitter tolerance", "PAM4": "PAM4",
    # --- 채널 ---
    "특성임피던스": "characteristic impedance", "전송선": "transmission line",
    "삽입손실": "insertion loss", "표피효과": "skin effect",
    "유전손실": "dielectric loss", "반사계수": "reflection coefficient",
    "리턴로스": "return loss", "노치": "notch", "비아스터브": "via stub",
    "백드릴": "back-drilling", "근단누화": "NEXT", "원단누화": "FEXT",
    "S파라미터": "S-parameters", "채널규격": "channel specification", "COM": "COM",
    # --- 스위치드 커패시터 ---
    "등가저항": "equivalent resistance", "두상클럭": "two-phase clocks",
    "겹침없음": "non-overlap", "바닥판표본화": "bottom-plate sampling",
    "SC적분기": "switched-capacitor integrator", "되먹임계수": "feedback factor",
    "정착시간": "settling time", "유한이득오차": "finite-gain error",
    "상관이중표본화": "correlated double sampling", "자동영점": "auto-zeroing",
    "전하보존": "charge conservation", "기생무감": "parasitic-insensitive",
    # --- 기준·바이어스 ---
    "PTAT": "PTAT", "CTAT": "CTAT", "밴드갭기준": "bandgap reference",
    "곡률보정": "curvature correction", "온도계수": "temperature coefficient",
    "시동회로": "start-up circuit", "퇴화동작점": "degenerate operating point",
    "전원제거비": "PSRR", "부하조정": "load regulation",
    "일정gm바이어스": "constant-g_m bias", "기준전류": "reference current",
    "트리밍": "trimming", "트림": "trim",
    # --- 정합 ---
    "펠그롬법칙": "Pelgrom's law", "랜덤불일치": "random mismatch",
    "계통불일치": "systematic mismatch", "공통중심": "common centroid",
    "더미소자": "dummy devices", "일치도면적": "matching area",
    "수율시그마": "yield sigma", "중요도표본": "importance sampling",
    "오프셋": "offset", "레이아웃의존효과": "layout-dependent effects",
    # --- 전원 ---
    "목표임피던스": "target impedance", "PDN": "PDN", "ESR": "ESR", "ESL": "ESL",
    "반공진": "anti-resonance", "감쇠": "damping", "디캡": "decoupling capacitor",
    "전류미분": "di/dt", "전압강하": "IR drop",
    "동시스위칭잡음": "simultaneous switching noise", "리플버짓": "ripple budget",
    # --- 신뢰성 ---
    "BTI": "BTI", "HCI": "HCI", "TDDB": "TDDB",
    "일렉트로마이그레이션": "electromigration", "아레니우스": "Arrhenius",
    "가속계수": "acceleration factor", "활성화에너지": "activation energy",
    "블랙식": "Black's equation", "와이블": "Weibull", "번인": "burn-in",
    "노화인지설계": "ageing-aware design", "수명목표": "lifetime target",
    # --- 레이아웃 ---
    "기생": "parasitics", "웰근접효과": "well proximity effect",
    "STI응력": "STI stress", "밀도규칙": "density rules",
    "안테나규칙": "antenna rules", "추출": "extraction", "LVS": "LVS", "DRC": "DRC",
    "플로어플랜": "floorplan", "핀배치": "pin placement",
    "추상화뷰": "abstract view", "GDS": "GDS",
    "하드매크로": "hard macro", "소프트매크로": "soft macro",
    # --- ESD ---
    "정전기방전": "electrostatic discharge", "인체모델": "human body model",
    "기계모델": "machine model", "충전소자모델": "charged device model",
    "클램프": "clamp", "스냅백": "snapback", "설계창": "design window",
    "유지전압": "holding voltage", "트리거전압": "trigger voltage",
    "전류경로": "current path", "패드용량": "pad capacitance",
    "이차항복": "second breakdown", "래치업": "latch-up",
}


# --- 밑바닥(고교)도 영어판에서는 영어로 ------------------------------------
영문.update({
    "사칙연산": "arithmetic", "분수": "fractions", "지수": "exponents",
    "로그": "logarithms", "제곱근": "square roots", "절댓값": "absolute value",
    "부등식": "inequalities", "일차함수": "linear functions",
    "이차함수": "quadratic functions", "지수함수": "exponential functions",
    "로그함수": "logarithmic functions", "삼각함수": "trigonometric functions",
    "수열": "sequences", "등비수열": "geometric series", "극한": "limits",
    "미분": "differentiation", "적분": "integration", "벡터": "vectors",
    "행렬": "matrices", "확률": "probability", "평균": "mean",
    "분산": "variance", "표준편차": "standard deviation",
    "정규분포": "normal distribution", "순열조합": "permutations and combinations",
    "복소수": "complex numbers", "좌표평면": "the coordinate plane",
    "그래프읽기": "reading graphs",
    "힘": "force", "질량": "mass", "가속도": "acceleration", "일": "work",
    "에너지": "energy", "운동량": "momentum", "속도": "velocity",
    "전하": "charge", "전기력": "electric force", "전기장": "electric field",
    "전위": "potential", "전압": "voltage", "전류": "current",
    "저항": "resistance", "옴의법칙": "Ohm's law", "직렬": "series",
    "병렬": "parallel", "자기장": "magnetic field",
    "전자기유도": "electromagnetic induction", "파동": "waves",
    "주파수": "frequency", "파장": "wavelength", "진폭": "amplitude",
    "위상": "phase", "온도": "temperature", "열": "heat",
    "원자": "atoms", "전자": "electrons", "원자핵": "the nucleus",
    "주기율표": "the periodic table", "공유결합": "covalent bonds",
    "이온": "ions", "이진법": "binary", "논리": "logic", "집합": "sets",
    "함수개념": "the idea of a function",
    # --- 구현 흐름 (T17~) ---
    "구현흐름": "implementation flow", "합성": "logic synthesis",
    "넷리스트": "netlist", "표준셀라이브러리": "standard-cell library",
    "타이밍라이브러리": "timing library (.lib)", "LEF": "LEF (abstract view)",
    "DEF": "DEF (placed and routed design)", "SDC": "SDC (design constraints)",
    "SPEF": "SPEF (extracted parasitics)", "SDF": "SDF (back-annotated delays)",
    "정적타이밍분석": "static timing analysis", "타이밍수렴": "timing closure",
    "ECO": "ECO (engineering change order)", "배선부하모델": "wire-load model",
    "물리인지합성": "physically aware synthesis", "사인오프": "signoff",
    # --- 플로어플랜·전원계획 (T18) ---
    "다이": "die", "코어영역": "core area", "점유율": "utilisation",
    "종횡비": "aspect ratio", "표준셀행": "standard-cell row", "SITE": "SITE",
    "전원그리드": "power grid", "파워링": "power ring",
    "파워스트라이프": "power stripe", "스페셜라우트": "special route",
    "IO패드링": "I/O pad ring", "코너셀": "corner cell", "IO필러": "I/O filler",
    "필러셀": "filler cell", "탭셀": "tap cell", "킵아웃": "keep-out",
    "패드제한다이": "pad-limited die", "코어제한다이": "core-limited die",
    # --- 배치·CTS·배선 (T19) ---
    "배치": "placement", "합법화": "legalisation", "HPWL": "HPWL (wirelength)",
    "타이밍주도배치": "timing-driven placement", "혼잡도": "congestion",
    "트랙": "routing track", "gcell": "gcell", "렌트법칙": "Rent's rule",
    "클럭트리합성": "clock-tree synthesis", "삽입지연": "insertion delay",
    "클럭스큐": "clock skew", "유용스큐": "useful skew", "클럭메시": "clock mesh",
    "H트리": "H-tree", "클럭게이팅": "clock gating",
    "CGIC": "integrated clock-gating cell", "전역배선": "global routing",
    "상세배선": "detail routing", "탐색수리": "search and repair",
    "안테나위반": "antenna violation",
    # --- 사인오프 (T20) ---
    "물리검증": "physical verification", "ERC": "ERC (electrical rule check)",
    "금속채움": "metal fill", "CMP": "CMP (chemical-mechanical polishing)",
    "코너": "corner", "MMMC": "multi-mode multi-corner analysis",
    "온도반전": "temperature inversion", "정적IR": "static IR analysis",
    "동적IR": "dynamic IR analysis", "스위칭벡터": "switching vector",
    "기능ECO": "functional ECO", "금속ECO": "metal-only ECO",
    "스페어셀": "spare cell", "테이프아웃": "tape-out", "마스크": "mask",
    # --- 검증 환경 (T21) ---
    "검증환경": "verification environment", "테스트벤치": "testbench",
    "에이전트": "agent", "시퀀스": "sequence", "시퀀서": "sequencer",
    "드라이버": "driver", "모니터": "monitor", "스코어보드": "scoreboard",
    "참조모델": "reference model", "가상인터페이스": "virtual interface",
    "기능커버리지": "functional coverage", "커버그룹": "covergroup",
    "커버포인트": "coverpoint", "크로스커버리지": "cross coverage",
    "제약랜덤": "constrained-random stimulus", "어서션": "assertion",
    "커버리지닫기": "coverage closure", "지시시험": "directed test",
    "회귀": "regression",
    # --- DFT 에서 테스터까지 (T22) ---
    "스캔": "scan", "스캔체인": "scan chain", "ATPG": "ATPG",
    "고착고장": "stuck-at fault", "천이지연고장": "transition (at-speed) fault",
    "결함커버리지": "fault coverage", "스캔압축": "scan compression",
    "해제기": "decompressor", "압축기": "compactor", "LBIST": "logic BIST",
    "MBIST": "memory BIST", "ATE": "ATE (automatic test equipment)",
    "핀일렉트로닉스": "pin electronics", "패턴메모리": "pattern memory",
    "테스트프로그램": "test program", "시험시간": "test time",
    "병렬시험": "multi-site test", "다이수율": "die yield",
    "결함수준": "defect level", "DPPM": "DPPM (defective parts per million)",
    "웨이퍼시험": "wafer sort", "양품다이": "known-good die",
})


def 영어로(말):
    """없으면 **그대로 둔다** -- 빠뜨린 것이 눈에 띄어야 한다."""
    return 영문.get(말, 말)
