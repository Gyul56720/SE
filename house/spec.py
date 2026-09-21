# -*- coding: utf-8 -*-
"""house/spec -- **자연어 요청을 스펙으로 바꾼다.** 짓기 전에 무엇을 지을지 적는 자리.

사용자는 이렇게 시킨다:

    자동차 범퍼에 들어가는 TTD 회로의 전력 문제를 해결해줄 수 있는 회로를 구상해줘

이 한 줄에서 RTL 로 바로 뛰면 안 된다. 이 저장소가 다섯 번 진 방식이 그것이다
(CLAUDE.md '짓기 전에 조사한다'). 순서는 이렇다:

    요청 -> 읽기() -> 스펙 초안 -> **선행조사** -> 아키텍처 제안 -> (사람 승인) -> RTL

## 코드가 먼저 읽고, 모델이 다듬는다

`읽기()` 는 **모델 없이** 도는 규칙 기반 판독기다. 쓰임새(자동차/의료/소비자) ·
풀려는 것(전력/속도/면적/신뢰성) · 수(전압 · 주파수 · 비트수 · 온도) 를 글에서
뽑는다. 키가 없어도 여기까지는 돈다 -- **모델이 죽어도 코드가 읽은 것은 남는다**
(`jaso/heed.py` 가 같은 규율을 쓴다).

모델이 있으면 `다듬기()` 가 그 위에 블록 분할 · 인터페이스 · 모드를 채운다.
**모델이 채운 칸은 그렇게 표시한다** -- 어디까지가 글에서 읽은 것이고 어디부터가
모델의 제안인지 보고서에 갈라 적어야 하기 때문이다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


# ------------------------------------------------------------------ 낱말표
#
# **여기 없는 말은 '모른다' 로 남긴다.** 넘겨짚어 채우면 스펙이 아니라 소설이 된다.

쓰임새표 = {
    "자동차": ["자동차", "차량", "범퍼", "차", "ADAS", "adas", "automotive", "전장",
            "주차", "충돌", "차선"],
    "의료": ["의료", "medical", "심박", "혈당", "임플란트", "환자"],
    "산업": ["산업", "공장", "모터", "인버터", "PLC", "로봇"],
    "소비자": ["소비자", "스마트폰", "웨어러블", "이어폰", "consumer", "휴대"],
    "우주항공": ["위성", "우주", "항공", "방사선", "rad-hard"],
    "통신": ["통신", "모뎀", "SerDes", "serdes", "이더넷", "5G", "기지국"],
    # Measured 2026-09-21: a request to scale the FIR/MAC into an NPU PE array
    # came back with an **empty** use-case list. The edge-inference market --
    # which is where a MAC array is actually sold -- had no entry at all.
    "엣지추론": ["엣지", "edge", "온디바이스", "on-device", "추론", "inference",
              "NPU", "npu", "신경망", "뉴럴", "TOPS", "tops", "AI 가속"],
    "데이터센터": ["데이터센터", "datacenter", "서버", "학습 가속", "HBM", "hbm"],
}

문제표 = {
    "전력": ["전력", "소비", "배터리", "저전력", "발열", "power", "누설", "대기전류",
           "소모", "전류"],
    "속도": ["속도", "빠르", "지연", "레이턴시", "처리율", "throughput", "주파수",
           "타이밍", "latency"],
    "면적": ["면적", "작게", "비용", "게이트 수", "다이", "area", "싸게"],
    "정밀도": ["정밀", "분해능", "해상도", "resolution", "정확", "오차", "ps", "피코"],
    "신뢰성": ["신뢰", "안전", "ASIL", "asil", "고장", "안전성", "functional safety",
            "진단", "자가진단"],
}

회로표 = {
    "TDC": ["TDC", "tdc", "TTD", "ttd", "time-to-digital", "비행시간", "ToF", "tof",
            "시간 측정", "초음파", "라이다", "lidar"],
    "ADC": ["ADC", "adc", "아날로그 디지털"],
    "FIR": ["FIR", "fir", "필터", "MAC", "mac", "누산", "컨볼루션"],
    "UART": ["UART", "uart", "시리얼", "RS-232"],
    "SPI": ["SPI", "spi"],
    "I2C": ["I2C", "i2c", "IIC"],
    "AXI": ["AXI", "axi", "APB", "apb", "AHB", "ahb", "버스", "레지스터 맵"],
    # **"코어" 를 CPU 로 읽지 않는다.** 실측 2026-09-21: "NPU 코어로 확장" 이라는
    # 요청이 CPU 로 잡혔다. 이 저장소에서 "코어" 는 IP 코어를 뜻하는 일이 훨씬 많다.
    "CPU": ["CPU", "cpu", "RISC-V", "risc-v", "프로세서", "마이크로프로세서",
            "명령어 세트", "ISA"],
    "NPU": ["NPU", "npu", "신경망 가속", "뉴럴 가속", "AI 가속", "추론 가속",
            "PE 어레이", "PE array", "시스톨릭", "systolic", "텐서 코어",
            "MAC 어레이", "TOPS", "tops"],
    "가속기": ["가속기", "accelerator", "오프로드", "offload", "코프로세서"],
    "암호": ["AES", "aes", "SHA", "sha", "암호", "crypto"],
    "CRC": ["CRC", "crc", "체크섬"],
    "PWM": ["PWM", "pwm", "모터 구동"],
    "FIFO": ["FIFO", "fifo", "버퍼"],
}

# 수를 뽑는 자리.  단위를 붙여 적는 습관을 그대로 받는다.
_수패턴 = [
    ("주파수_Hz", r"(\d+(?:\.\d+)?)\s*(GHz|MHz|kHz|Hz)", {"GHz": 1e9, "MHz": 1e6,
                                                         "kHz": 1e3, "Hz": 1}),
    ("전압_V", r"(\d+(?:\.\d+)?)\s*(mV|V)\b", {"mV": 1e-3, "V": 1}),
    ("전류_A", r"(\d+(?:\.\d+)?)\s*(nA|uA|µA|mA|A)\b", {"nA": 1e-9, "uA": 1e-6,
                                                       "µA": 1e-6, "mA": 1e-3, "A": 1}),
    ("전력_W", r"(\d+(?:\.\d+)?)\s*(nW|uW|µW|mW|W)\b", {"nW": 1e-9, "uW": 1e-6,
                                                       "µW": 1e-6, "mW": 1e-3, "W": 1}),
    ("분해능_s", r"(\d+(?:\.\d+)?)\s*(fs|ps|ns|us|µs|ms)\b", {"fs": 1e-15, "ps": 1e-12,
                                                             "ns": 1e-9, "us": 1e-6,
                                                             "µs": 1e-6, "ms": 1e-3}),
    ("거리_m", r"(\d+(?:\.\d+)?)\s*(mm|cm|m)\b", {"mm": 1e-3, "cm": 1e-2, "m": 1}),
    ("온도_C", r"(-?\d+(?:\.\d+)?)\s*(?:°\s*)?C\b", None),
    ("비트", r"(\d+)\s*(?:비트|bit|b)\b", None),
    # These three decide the whole shape of an NPU request and were all missed.
    ("PE수", r"(\d+)\s*(?:개\s*)?(?:PE|pe|MAC|mac)\b", None),
    # Commercial IP specs quote a *menu* of configurations, not one number --
    # Ethos-U55 is sold as 32/64/128/256 MACs per cycle. A plain "(\d+) PE"
    # pattern grabs only the last one, so the other three configurations are
    # silently dropped and the proposal designs for one point instead of four.
    ("설정목록", r"\b(\d+(?:\s*/\s*\d+){1,6})\s*(?:개\s*)?(?:PE|pe|MAC|mac|탭|tap)", None),
    ("정밀도_비트", r"\bINT\s?(\d+)\b|\bint(\d+)\b", None),
    ("TOPS", r"(\d+(?:\.\d+)?)\s*(?:TOPS|tops|TOPs)\b", None),
]


@dataclass
class 스펙:
    요청: str = ""
    쓰임새: list = field(default_factory=list)
    문제: list = field(default_factory=list)
    회로: list = field(default_factory=list)
    수: dict = field(default_factory=dict)
    # 아래는 모델이 채우는 칸 -- 비어 있으면 비어 있다고 적는다
    이름: str = ""
    한줄: str = ""
    블록: list = field(default_factory=list)      # [{"이름","하는일"}]
    포트: list = field(default_factory=list)      # [{"이름","방향","폭","뜻"}]
    클럭: list = field(default_factory=list)      # [{"이름","주기_ns","도메인"}]
    모드: list = field(default_factory=list)      # [{"이름","전력","무엇"}]
    목표: list = field(default_factory=list)      # [{"항목","값","어떻게 잴 것인가"}]
    검증계획: list = field(default_factory=list)  # [{"시나리오","노리는 것"}]
    위험: list = field(default_factory=list)
    모른다: list = field(default_factory=list)    # **채우지 못한 칸**
    출처: dict = field(default_factory=dict)      # 칸 -> "글에서 읽음" | "모델 제안"

    def 사전(self) -> dict:
        return {k: getattr(self, k) for k in
                ("요청", "쓰임새", "문제", "회로", "수", "이름", "한줄", "블록",
                 "포트", "클럭", "모드", "목표", "검증계획", "위험", "모른다", "출처")}

    def 읽은것만(self) -> dict:
        """**글에서 실제로 읽은 것만.** 모델이 채운 것은 뺀다."""
        return {"쓰임새": self.쓰임새, "문제": self.문제, "회로": self.회로, "수": self.수}


def 읽기(요청: str) -> 스펙:
    """모델 없이 도는 판독기.  **넘겨짚지 않는다** -- 못 읽은 것은 `모른다` 로 남는다."""
    글 = 요청 or ""
    낮 = 글.lower()
    s = 스펙(요청=글.strip())

    for 갈래, 말들 in 쓰임새표.items():
        if any(w.lower() in 낮 for w in 말들):
            s.쓰임새.append(갈래)
    for 갈래, 말들 in 문제표.items():
        if any(w.lower() in 낮 for w in 말들):
            s.문제.append(갈래)
    for 갈래, 말들 in 회로표.items():
        if any(w.lower() in 낮 for w in 말들):
            s.회로.append(갈래)

    for 이름, 패, 배수 in _수패턴:
        for m in re.finditer(패, 글):
            잡힌 = m.group(1)
            if 잡힌 is None:                 # 갈래가 여럿인 패턴(INT8|int8)의 빈 쪽
                잡힌 = next((g for g in m.groups() if g), None)
            if 잡힌 is None:
                continue
            # A configuration *menu* ("32/64/128/256") is one match holding
            # several numbers. float() throws on it and the old loop swallowed
            # that with `continue` -- so the whole menu vanished without a word.
            조각 = [x.strip() for x in str(잡힌).split("/")] if "/" in str(잡힌) \
                else [str(잡힌)]
            for 조 in 조각:
                try:
                    v = float(조)
                except ValueError:
                    continue
                if 배수:
                    단위 = m.group(2) if m.lastindex and m.lastindex >= 2 else None
                    v *= 배수.get(단위, 1)
                s.수.setdefault(이름, []).append(v)

    for 칸, 값 in (("쓰임새", s.쓰임새), ("문제", s.문제), ("회로", s.회로)):
        if 값:
            s.출처[칸] = "글에서 읽음"
    if s.수:
        s.출처["수"] = "글에서 읽음"

    # **못 읽은 것을 적는다.** 이것이 사람에게 물을 목록이 된다.
    if not s.회로:
        s.모른다.append("어떤 회로인지 -- 글에 아는 회로 이름이 없다")
    if not s.문제:
        s.모른다.append("무엇을 풀려는지 -- 전력/속도/면적/정밀도/신뢰성 중 무엇인가")
    if "주파수_Hz" not in s.수:
        s.모른다.append("동작 주파수")
    if "전압_V" not in s.수:
        s.모른다.append("공급 전압")
    if not s.쓰임새:
        s.모른다.append("어디에 쓰는지 (온도 등급 · 안전 등급이 여기서 나온다)")
    return s


# ------------------------------------------------------------------ 모델이 채우는 칸

프롬프트 = """너는 디지털 IP 설계 아키텍트다. 아래 요청을 **설계 스펙**으로 바꿔라.

요청:
{요청}

코드가 글에서 읽어 낸 것 (이미 확인된 사실이다. 뒤집지 마라):
{읽은것}

규칙:
1. **모르는 것을 지어내지 마라.** 근거 없이 정할 수 없는 값은 "모른다" 목록에 넣어라.
2. 이것은 **디지털 RTL** 로 구현할 수 있는 블록이어야 한다. 아날로그(비교기·PLL·
   LDO·밴드갭)가 필요하면 그것은 블록 목록에 **"외부 아날로그"** 로 적고, 우리가
   짤 디지털 부분만 포트로 받아라.
3. 목표(goal)마다 **어떻게 잴 것인가**를 같이 적어라. 잴 방법이 없는 목표는 목표가
   아니다.
4. 검증 시나리오를 5개 이상 적어라. 각각 **무엇을 노리는지** 적어라.
5. 위험(risk)에는 이 설계가 실패할 수 있는 구체적 경로를 적어라.

아래 JSON 만 출력해라. 다른 말은 쓰지 마라.

{{"이름": "소문자 영문 짧은 이름 (모듈 이름이 된다, 예: nsw_tdc)",
 "한줄": "이 회로가 무엇인지 한 줄",
 "블록": [{{"이름": "...", "하는일": "..."}}],
 "포트": [{{"이름": "...", "방향": "input|output", "폭": 1, "뜻": "..."}}],
 "클럭": [{{"이름": "clk", "주기_ns": 10.0, "도메인": "..."}}],
 "모드": [{{"이름": "...", "전력": "...", "무엇": "..."}}],
 "목표": [{{"항목": "...", "값": "...", "어떻게 잴 것인가": "..."}}],
 "검증계획": [{{"시나리오": "...", "노리는 것": "..."}}],
 "위험": ["..."],
 "모른다": ["..."]}}
"""


def 다듬기(s: 스펙, 묻기=None) -> 스펙:
    """모델에게 나머지 칸을 채우게 한다.  **모델이 없으면 그대로 돌려준다.**

    `묻기` 는 검사에서 가짜 모델을 끼우는 자리다(str -> str).
    """
    if 묻기 is None:
        묻기 = _기본묻기
    글 = 프롬프트.format(요청=s.요청,
                      읽은것=json.dumps(s.읽은것만(), ensure_ascii=False, indent=1))
    try:
        답 = 묻기(글)
    except Exception as e:                                   # noqa: BLE001
        s.모른다.append(f"모델을 못 불렀다: {type(e).__name__}: {e}"[:160])
        return s
    d = _json뽑기(답)
    if not d:
        s.모른다.append("모델이 JSON 을 안 냈다 -- 스펙의 나머지 칸이 비었다")
        return s
    for 칸 in ("이름", "한줄"):
        if d.get(칸):
            setattr(s, 칸, str(d[칸]))
            s.출처[칸] = "모델 제안"
    for 칸 in ("블록", "포트", "클럭", "모드", "목표", "검증계획", "위험"):
        if isinstance(d.get(칸), list) and d[칸]:
            setattr(s, 칸, d[칸])
            s.출처[칸] = "모델 제안"
    for x in (d.get("모른다") or []):
        if x not in s.모른다:
            s.모른다.append(str(x))
    return s


def _기본묻기(글: str) -> str:
    import sys
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parent.parent / "orchestrator"))
    import llm_pool
    pool = llm_pool.build_pool()
    if not pool:
        raise RuntimeError("LLM 후보 풀이 비었다 -- GEMINI_API_KEY 가 없다")
    return llm_pool.call(pool, 글, pool_id="house_spec")[0]


def _json뽑기(글: str):
    """모델이 ```json 울타리를 치거나 앞뒤에 말을 붙여도 뽑아낸다."""
    if not 글:
        return None
    t = 글.strip()
    if "```" in t:
        조각 = t.split("```")
        for c in 조각:
            c = c.strip()
            if c.startswith("json"):
                c = c[4:].strip()
            if c.startswith("{"):
                t = c
                break
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b <= a:
        return None
    try:
        return json.loads(t[a:b + 1])
    except json.JSONDecodeError:
        return None
