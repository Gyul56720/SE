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
    못박힌수: list = field(default_factory=list)  # [(항목, 값)] 요청 표에서 그대로
    출처: dict = field(default_factory=dict)      # 칸 -> "글에서 읽음" | "모델 제안"

    def 사전(self) -> dict:
        return {k: getattr(self, k) for k in
                ("요청", "쓰임새", "문제", "회로", "수", "이름", "한줄", "블록",
                 "포트", "클럭", "모드", "목표", "검증계획", "위험", "모른다", "출처")}

    def 읽은것만(self) -> dict:
        """**글에서 실제로 읽은 것만.** 모델이 채운 것은 뺀다."""
        return {"쓰임새": self.쓰임새, "문제": self.문제, "회로": self.회로, "수": self.수}


# 첨부를 이어 붙일 때 `inbox.붙이기()` 가 넣는 구분선. **요청 글이 아니다.**
#
# 실측 2026-09-22: 이 줄이 안 벗겨진 채 흘러 들어가 제안서 표지에 이렇게 찍혔다.
#
#     Project: ----- 첨부: 1551965127165608020_spec.md ----- # MERA-1 v1.0 Event Record
#
# 제목·요약·설계 이름이 전부 이 줄에서 뽑히므로 한 군데만 새도 문서 전체가 지저분해진다.
_첨부줄 = re.compile(r"^\s*-{3,}\s*첨부:.*?-{3,}\s*$", re.M)


def 요청다듬기(요청: str) -> str:
    """첨부 구분선을 벗긴다. 글의 내용은 한 글자도 안 건드린다."""
    return _첨부줄.sub("", 요청 or "").strip()


# 요청의 마크다운 표에서 **사람이 못박은 수**를 그대로 들고 온다.
#
# **실측 2026-09-22.** MERA 요청은 값을 표로 적었다 -- PRE 4096 · POST 16384 ·
# payload 80 KiB · header 64 byte · burst 64-beat · address 64-bit · data 128-bit.
# 그런데 제안서의 판독표에는 **주파수·전압·온도 셋만** 실렸다. 나머지는 낱말표에
# 없어서 통째로 안 보였고, 사람은 "내가 못박은 수를 읽기는 했나" 를 알 길이 없었다.
#
# 낱말표를 늘리는 것으로는 안 된다 -- 다음 IP 는 또 다른 이름을 쓴다. **표는
# 사람이 이미 칸을 갈라 놓은 자리다.** 거기 있는 것을 그대로 옮긴다.
_표줄 = re.compile(r"^\s*\|(?P<항목>[^|]+)\|(?P<값>[^|]+)\|\s*$", re.M)
_수있나 = re.compile(r"\d")
_칸머리 = ("항목", "값", "이름", "규격", "---", "===")


def 표에서읽기(요청: str) -> list:
    """[(항목, 값)] -- 요청의 `| 항목 | 값 |` 표에서 **수가 든 줄만**.

    **고치지도 풀지도 않는다.** 사람이 쓴 그대로 옮긴다. 여기서 해석하면 그
    해석이 틀렸을 때 사람은 제가 무엇을 적었는지조차 못 되짚는다.
    """
    난것, 본것 = [], set()
    for m in _표줄.finditer(요청 or ""):
        항 = m.group("항목").strip().strip("*` ")
        값 = m.group("값").strip().strip("` ")
        if not 항 or not 값 or not _수있나.search(값):
            continue
        if any(항.startswith(h) or set(항) <= set("-: ") for h in _칸머리):
            continue
        열쇠 = (항.lower(), 값.lower())
        if 열쇠 in 본것:
            continue
        본것.add(열쇠)
        난것.append((항, 값.replace("**", "")))
    return 난것


def 읽기(요청: str) -> 스펙:
    """모델 없이 도는 판독기.  **넘겨짚지 않는다** -- 못 읽은 것은 `모른다` 로 남는다."""
    글 = 요청다듬기(요청)
    낮 = 글.lower()
    s = 스펙(요청=글.strip())
    s.못박힌수 = 표에서읽기(글)

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
6. **코드가 못 읽은 칸을 네가 읽어라.** 위의 '읽어 낸 것' 에서 `쓰임새`·`문제`·`회로`·
   `수` 가 비어 있으면, 요청 글에 **실제로 적혀 있는 것만** 뽑아 `판독` 에 넣어라.
   글에 없으면 비워 둬라 -- **지어내면 아래 모든 수가 그 위에 쌓인다.**
   · 쓰임새: 자동차 · 의료 · 소비자 · 통신 · 계측/시험장비 · 항공우주 · 산업 …
   · 문제: 속도 · 면적 · 전력 · 정밀도 · 신뢰성 중 글이 말하는 것
   · 회로: FIR · ADC · FIFO · AXI · FSM · SRAM … 글이 말하는 갈래
   · 수: {{"주파수_Hz": [...], "전압_V": [...], "비트": [...], "깊이": [...]}} 꼴

아래 JSON 만 출력해라. 다른 말은 쓰지 마라.

{{"판독": {{"쓰임새": [], "문제": [], "회로": [], "수": {{}}}},
 "이름": "소문자 영문 짧은 이름 (모듈 이름이 된다, 예: nsw_tdc)",
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


def 다듬기(s: 스펙, 묻기=None, 덧붙임: str = "") -> 스펙:
    """모델에게 나머지 칸을 채우게 한다.  **모델이 없으면 그대로 돌려준다.**

    `묻기` 는 검사에서 가짜 모델을 끼우는 자리다(str -> str).
    """
    if 묻기 is None:
        묻기 = _기본묻기
    글 = 프롬프트.format(요청=s.요청,
                      읽은것=json.dumps(s.읽은것만(), ensure_ascii=False, indent=1))
    if 덧붙임:
        # **관문이 찾은 결함을 그대로 돌려준다.** `gen.py` 가 빨간 관문의 오류 원문을
        # 모델에 돌려주는 것과 같다 -- 사람이 옮겨 적지 않는다.
        글 += "\n\n" + 덧붙임
    try:
        답 = 묻기(글)
    except Exception as e:                                   # noqa: BLE001
        s.모른다.append(f"모델을 못 불렀다: {type(e).__name__}: {e}"[:160])
        return s
    d = _json뽑기(답)
    if not d:
        s.모른다.append("모델이 JSON 을 안 냈다 -- 스펙의 나머지 칸이 비었다")
        return s
    # **코드가 못 읽은 판독 칸을 모델이 채운다 -- 그리고 그 사실을 적는다.**
    #
    # 사용자(2026-09-22): "파이썬 조건문으로 쓰지 말고, LLM 이 한번 개입해주면 안되?
    # 너무 hard 한데 format 이" · "나는 너의 도움 없이 돌아가는 discord bot 을 만들고
    # 싶어."
    #
    # 맞는 말이다. 낱말표는 **내가 아는 IP 만** 읽는다. 실측 2026-09-22: 요청이
    # "계측·시험장비용" 이라고 **글자 그대로** 적었는데 판독이 `쓰임새 없음` 을 냈다 --
    # 표에 그 말이 없어서다. 그러면 다음 IP 마다 사람이 표를 고쳐 줘야 하고, 그것은
    # 봇이 혼자 도는 것이 아니다.
    #
    # 그렇다고 판독을 통째로 모델에 넘기지는 않는다. 규칙 판독은 **공짜이고 같은 답을
    # 두 번 준다** -- 그 값어치를 버릴 이유가 없다. 그래서 순서를 둔다:
    #
    #     규칙이 읽는다 -> 빈 칸만 모델이 읽는다 -> **어디서 온 값인지 칸마다 적는다**
    #
    # 마지막이 없으면 이 장치는 '그럴듯하게 채워진 스펙' 을 낳는다. 보고서의 출처 칸이
    # 그래서 있다.
    판독 = d.get("판독") or {}
    for 칸 in ("쓰임새", "문제", "회로"):
        if getattr(s, 칸):
            continue                                  # 규칙이 읽었으면 모델이 못 뒤집는다
        값 = 판독.get(칸) or []
        값 = [str(x).strip() for x in 값 if str(x).strip()][:6]
        if 값:
            setattr(s, 칸, 값)
            s.출처[칸] = "모델 제안"
    if not s.수 and isinstance(판독.get("수"), dict):
        수 = {}
        for k, v in 판독["수"].items():
            벌 = v if isinstance(v, list) else [v]
            숫 = []
            for x in 벌:
                try:
                    숫.append(float(x))
                except (TypeError, ValueError):
                    continue
            if 숫:
                수[str(k)] = 숫
        if 수:
            s.수 = 수
            s.출처["수"] = "모델 제안"

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
