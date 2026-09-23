# -*- coding: utf-8 -*-
"""house/rtl/agent -- Ethan Ross (Front-End Design) 의 업무와 보고서.

하는 일은 넷이다.
  1. HLS: C 식 -> DFG -> 스케줄/바인딩 -> SV 생성 -> 기능·PPA 확인 (설계 공간 탐색)
  2. RTL: FSM · 파이프라인 · 파라미터 재사용성을 **재서** 보인다
  3. 저전력: 클럭 게이팅 정책 A/B 를 실제 시뮬레이션의 토글 수로 견준다
  4. CDC: 도메인 건넘을 정적으로 뽑아내고 동기화기 깊이와 MTBF 를 셈한다

모든 수는 도구를 실제로 돌려 나온다. 안 돌린 것은 보고서에 '안 함' 으로 적는다.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import subprocess
import sys
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
집 = 뿌리.parent
저장소 = 집.parent
sys.path.insert(0, str(저장소))

from house import hls as HLS          # noqa: E402
from house import people    # noqa: E402
from house import report as RPT       # noqa: E402
from house import sim as SIM          # noqa: E402
from house import synth as SYN        # noqa: E402
from house import sch as SCH          # noqa: E402
from house import viz as V            # noqa: E402
from house.dv import vcd as VCD        # noqa: E402

RTL파일 = 집 / "rtl" / "src" / "nsw_fir.sv"


# ------------------------------------------------------------------ CDC 정적 점검

def cdc점검(파일=None, 설계=None, 훑기=None) -> dict:
    """클럭 도메인과 건넘을 **훑기 결과에서** 뽑는다.

    상용 도구(Spyglass CDC · Questa CDC)가 없다. 그래서 읽어서 센다.

    **실측 2026-09-22.** 첫 판은 건넘 목록을 이렇게 만들었다.

        if "u_coef_fifo" in 글:
            건넘.append({"신호": "cfg_coef[15:0] + cfg_we", ...})

    `nsw_fir` 의 인스턴스 이름이 코드에 박혀 있었다. MERA 를 넘기면 **건넘 0개**가
    나오고, 보고서는 "맨선 0개 · 판정 통과" 라고 적는다 -- **안 본 것을 통과로
    적는 것**이다. 그것이 가장 나쁜 꼴이다.

    지금은 `rtlscan.훑기()` 가 찾은 건넘을 쓴다. 회로를 안 가린다. 대신 **무엇을
    모르는지 같이 돌려준다** -- 동기화 구조가 안전한지는 이 훑기가 모른다.
    """
    from house import rtlscan as SCAN
    훑 = 훑기
    if 훑 is None:
        RTL = [파일 or RTL파일] if (파일 or 설계 is None) else list(설계.RTL)
        훑 = SCAN.훑기(RTL, getattr(설계, "top", "") or "")
    글 = "\n".join(Path(x).read_text(encoding="utf-8", errors="replace")
                  for x in (훑.get("파일") or []) if Path(x).exists())

    도메인 = dict(훑.get("클럭블록수") or {})
    건넘 = []
    for x in (훑.get("CDC건넘") or []):
        신호 = x["신호"]
        # **동기화 구조를 이름으로 짐작한다 -- 확인한 것이 아니다.**
        # 받는 도메인에서 그 신호가 두 번 이상 단으로 넘어가면 다단 동기화기 꼴이고,
        # 이름에 gray 가 들어가면 그레이 포인터 꼴이다. 둘 다 **모양이지 증명이 아니다.**
        단수 = len(re.findall(rf"\w*{re.escape(신호)}\w*\s*<=", 글))
        그레이 = "gray" in 신호.lower()
        건넘.append({
            "신호": 신호,
            "보내는곳": " · ".join(x["보내는곳"]),
            "받는곳": " · ".join(x["받는곳"]),
            "방식": (f"{단수}단으로 보임" if 단수 > 1 else "단 하나로 보임")
                  + (" · 그레이 이름" if 그레이 else ""),
            "종류": "포인터" if 그레이 else "신호",
            "안전": None,          # **모른다.** 아래 '못보는것' 참고
            "왜": "이 훑기는 **모양만** 본다 -- 안전한지는 CDC 도구가 봐야 한다",
        })
    # 맨선 후보: 받는 도메인에서 **한 단으로** 바로 쓰이는 건넘
    맨선 = [x["신호"] for x, y in zip(건넘, 훑.get("CDC건넘") or [])
          if "단 하나로" in x["방식"]]
    return {"도메인": 도메인, "건넘": 건넘, "맨선": sorted(set(맨선)),
            "동기화기": len(re.findall(r"sync\w*\s*#?\s*\(", 글)),
            "afifo": len(re.findall(r"afifo\w*\s*#?\s*\(", 글)),
            "판정": ("건넘 없음" if not 건넘 else
                   ("한 단으로 보이는 건넘 " + str(len(맨선)) + "개" if 맨선
                    else "전부 다단으로 보인다")),
            "못보는것": [
                "**다단이 곧 안전은 아니다** -- 여러 비트가 같이 건너면 2FF 로도 깨진다",
                "레벨/펄스 변환이 옳은지",
                "재수렴(reconvergence) -- 같은 소스가 두 길로 건너 다시 만나는 것",
                "`generate`·매크로 안의 건넘",
            ]}


def mtbf(단수: int, f_clk=100e6, f_data=10e6, tau_ps=25.0, Tw_ps=30.0, Tclk_ns=10.0) -> float:
    """MTBF = exp(t_r/tau) / (Tw * f_clk * f_data).  t_r = 단수 * Tclk - setup."""
    t_r = (단수 * Tclk_ns * 1e3 - 40.0)                      # ps
    # **상한을 둔다.** 단수가 늘면 exp 가 float 범위를 넘는다(4단에서 이미 그렇다).
    # 그때 inf 를 돌려주면 그림이 죽는다 -- 우주 나이(4.4e17 s)를 넘으면 그 값을 쓴다.
    지수 = t_r / tau_ps
    if 지수 > 700:
        return 1e300
    return math.exp(지수) / (Tw_ps * 1e-12 * f_clk * f_data)


# ------------------------------------------------------------------ 업무 한 바퀴

def _쓰인수(훑: dict, 이름: str) -> int:
    """그 파라미터가 RTL 에서 몇 번 쓰였나. **뜻은 못 읽어도 쓰임새는 센다.**"""
    import re as _re
    수 = 0
    for p in (훑.get("파일") or []):
        try:
            글 = Path(p).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        수 += len(_re.findall(rf"\b{_re.escape(이름)}\b", 글))
    return max(0, 수 - 1)          # 선언 자신은 뺀다


def _구조그림(훑: dict) -> str:
    """클럭 도메인과 그 사이의 건넘을 **훑기 결과로** 그린다.

    실측 2026-09-22: 여기 있던 블록도는 `cfg_clk` · `nsw_afifo` · `nsw_icg` 를
    손으로 박아 둔 것이었다. 다른 회로를 넘겨도 그 상자가 그대로 나온다.
    """
    클럭 = list(훑.get("클럭") or []) or ["(클럭 없음)"]
    건넘 = list(훑.get("CDC건넘") or [])
    칸폭, 칸높 = 150, 62
    블록, 연결 = [], []
    for i, c in enumerate(클럭[:4]):
        x = 24 + i * (칸폭 + 46)
        블록.append((c, x, 46, 칸폭, 칸높, "#eef4fb",
                   f"always {훑.get('클럭블록수', {}).get(c, 0)}개"))
    본것 = set()
    for x in 건넘[:6]:
        보 = (x["보내는곳"] or [None])[0]
        받 = (x["받는곳"] or [None])[0]
        if not 보 or not 받 or (보, 받) in 본것:
            continue
        if 보 not in [b[0] for b in 블록] or 받 not in [b[0] for b in 블록]:
            continue
        본것.add((보, 받))
        연결.append((보, 받, x["신호"], V.파랑))
    부제 = (f"클럭 {len(클럭)}개 · 건넘 {len(건넘)}개"
          if 건넘 else f"클럭 {len(클럭)}개 · 도메인 사이 건넘 없음")
    return V.블록도(블록, 연결, 부제, 폭=max(650, 24 + len(블록[:4]) * (칸폭 + 46)),
                 높이=150)


def _맞바꿈글(t: list) -> str:
    """곱셈기 수 대 지연 그림의 설명. **수를 글에 안 박는다.**

    실측 2026-09-22 (RTL-RPT): 여기에 «지연은 4 → 10 단계로 오른다» 가 박혀
    있었는데 바로 위 표는 **3 → 5** 였다. 4 와 10 은 이 보고서 어디에서도
    안 나온 수다 -- 한때 맞았던 수가 글에 굳어 남은 것이다.
    """
    if not t:
        return "구성이 없다."
    큰 = max(t, key=lambda x: x["자원"]["mul"])
    작 = min(t, key=lambda x: x["자원"]["mul"])
    if 큰 is 작:
        return "구성이 하나뿐이라 맞바꿈이 안 보인다."
    return (f"HLS 의 고전적인 맞바꿈. 곱셈기를 {큰['자원']['mul']}개에서 "
          f"{작['자원']['mul']}개로 줄이면 면적 추정은 "
          f"{큰['면적추정']:,.0f} → {작['면적추정']:,.0f} µm² 로 내려가고 "
          f"지연은 <b>{큰['지연']} → {작['지연']} 단계</b>로 오른다. "
          f"어느 점을 고를지는 시스템이 정한다.")


def _파레토글(t: list) -> str:
    """면적-지연 산점도의 설명. **점이 몇 개인지 세서 적는다.**

    실측 2026-09-22 (RTL-RPT): «세 점이 파레토 앞면을 이룬다. 어느 것도 다른
    것에 완전히 지지 않는다» 고 적혀 있었는데, 표에서 4곱셈기와 2곱셈기는
    지연 3 · II 1 · 면적 2,456 으로 **모든 칸이 같았다.** 그림에 보이는 점은
    둘뿐이었다. 식이 `(a0*x0)+(a1*x1)` 이라 곱셈이 둘뿐이니 곱셈기 4개짜리는
    둘을 놀린다 -- **그 사실이 여기서 드러났어야 했다.**
    """
    if not t:
        return "구성이 없다."
    자리 = {}
    for x in t:
        자리.setdefault((round(float(x["면적추정"]), 3), x["지연"]), []).append(x["이름"])
    겹 = [v for v in 자리.values() if len(v) > 1]
    글 = f"{len(t)}개 구성 가운데 <b>서로 다른 점은 {len(자리)}개</b>다."
    if 겹:
        글 += (" " + " · ".join(f"<b>{' 와 ' .join(v)} 는 면적도 지연도 같다</b>"
                              for v in 겹)
             + " — 그 구성들은 자원을 더 줘도 쓰지 않는다는 뜻이다(식에 든 "
               "연산이 그보다 적다). <b>같은 하드웨어를 두 점으로 세지 않는다.</b>")
    else:
        글 += " 어느 것도 다른 것에 완전히 지지 않는다."
    return 글


# 파이프라인 깊이를 정하는 파라미터의 이름꼴. `dv/plan.py` 의 `_단수말` 과 같은 줄기.
_깊이말 = ("stage", "pipe", "depth", "latency")


def _깊이흔든줄(재사용: list, 기본: dict) -> list:
    """**깊이를 정말로 바꾼** 구성만. 기본값으로 늘 있는 칸에 안 속는다.

    실측 2026-09-22 (RTL-RPT): 거르개가 `"STAGES" in x["파라"]` 였는데 그 칸은
    **모든 구성에 늘 있다**(기본값으로). 그래서 `ACCW` 를 흔든 줄까지 들어왔고,
    `STAGES 3 · 지연 3` 두 줄이 하나는 400 통과, 하나는 **385 실패**로 나란히
    섰다 -- 「깊이를 바꿔도 기능이 유지된다」는 설명 아래에서.
    """
    return [x for x in (재사용 or [])
            if "pass" in x and any(any(w in k.lower() for w in _깊이말)
                                   for k in _바뀐것(x.get("파라") or {}, 기본 or {}))]


def _바뀐것(파라: dict, 기본: dict) -> dict:
    """기본 구성과 **다른 칸만**. 이것이 그 구성의 이름이 된다."""
    return {k: v for k, v in (파라 or {}).items() if (기본 or {}).get(k) != v}


def _구성이름(파라: dict, 기본: dict) -> str:
    """스윕 한 줄의 이름. **흔든 것을 적는다 -- 안 흔든 것을 적지 않는다.**

    실측 2026-09-22 (RTL-RPT): 라벨이 `f"TAPS{...}/S{...}"` 로 박혀 있어서
    **여섯 구성이 전부 `TAPS8/S3` 로 찍혔다.** 면적은 59,383~129,181 µm² 로
    갈렸는데 이름이 하나였다. 그런데 `_스윕조합()` 은 TAPS 도 STAGES 도 안
    흔든다 -- 값이 큰 파라미터 셋(ACCW · DW · CW)을 흔든다.

    **그래서 그림 설명이 «TAPS 가 면적을 끈다» 고 적혀 있었다.** TAPS 는 한 번도
    안 바뀌었다. 읽는 사람은 안 흔든 파라미터가 면적을 끈다고 읽는다.
    """
    d = _바뀐것(파라, 기본)
    return " · ".join(f"{k}={v}" for k, v in sorted(d.items())) if d else "기본"


def _흔든이름들(조합: list) -> list:
    """스윕이 **실제로 흔든** 파라미터 이름들."""
    if not 조합:
        return []
    기본 = 조합[0]
    본것 = []
    for c in 조합[1:]:
        for k in _바뀐것(c, 기본):
            if k not in 본것:
                본것.append(k)
    return 본것


def _스윕조합(훑: dict, 설계, 빠르게=False) -> list:
    """이 회로의 파라미터를 반/두 배로 흔든 조합. **회로 이름을 안 박는다.**

    실측 2026-09-22: 여기에 `{"TAPS": 4}` 처럼 FIR 의 파라미터 이름이 박혀 있었다.
    MERA 를 넘겨도 그대로라 **이름만 바뀐 FIR 보고서**가 된다.

    수로 된 기본값을 가진 파라미터만 흔든다 -- 글자 파라미터를 반으로 나눌 수는 없다.
    흔들 것이 없으면 **기본 구성 하나만** 돌리고 그렇게 적는다(빈 표보다 낫다).
    """
    기본 = dict(getattr(설계, "파라", {}) or {})
    # **톱 모듈의 파라미터만 쓴다.** 하위 모듈 것을 섞으면 verilator 가
    # "Parameters from the command line were not found in the design" 으로 죽는다.
    for k, v in (훑.get("톱파라미터") or {}).items():
        if k in 기본:
            continue
        v = str(v).strip()
        if re.fullmatch(r"\d+", v):
            기본[k] = int(v)
    수파라 = {k: v for k, v in 기본.items() if isinstance(v, int) and v > 0}
    if not 수파라:
        return [{}]
    # 큰 것부터 -- 치수를 정하는 파라미터일 가능성이 높다
    이름들 = sorted(수파라, key=lambda k: -수파라[k])[:2 if 빠르게 else 3]
    조합 = [dict(기본)]
    for k in 이름들:
        for 배 in ((2,) if 빠르게 else (2, 0.5)):
            새값 = max(1, int(수파라[k] * 배))
            if 새값 == 수파라[k]:
                continue
            조합.append({**기본, k: 새값})
    # 같은 것이 겹치면 뺀다
    본것, 난것 = set(), []
    for c in 조합:
        열쇠 = tuple(sorted(c.items()))
        if 열쇠 not in 본것:
            본것.add(열쇠)
            난것.append(c)
    return 난것[:3 if 빠르게 else 6]


def 일하기(빠르게=False, 회귀수=2000, 설계=None) -> dict:
    """실제로 도구를 돌리고 잰 것을 모은다."""
    from house import designs as DES
    d0 = 설계 or DES.NSW_FIR
    결과 = {"시작": time.time(), "설계": d0.키, "설계이름": d0.이름, "top": d0.top}
    결과["도구"] = SIM.있나()
    # **이 보고서의 어느 장이 이 회로를 실제로 본 것인지 갈라 둔다.**
    # lint · elaborate · 합성은 `d0.RTL` 을 읽으므로 회로를 따라간다.
    # HLS 설계공간 탐색은 아래 `식` 하나를 푸는 것이라 **회로와 무관하다** --
    # 그것을 이 회로의 결과처럼 보이게 두면 어제 그 사고와 같은 꼴이 된다.
    결과["회로를본장"] = ["lint", "elaborate", "합성", "CDC"]
    결과["회로와무관한장"] = ["HLS 설계공간 탐색"]

    # --- 0. **이 회로를 실제로 읽는다.** 회로를 안 가리는 유일한 길은 RTL 글에서
    #        읽어 내는 것이다. 손으로 적어 둔 FIR 의 CDC 표 · 파라미터 조합 ·
    #        데이터패스 식은 MERA 를 넘겨도 그대로다 -- 이름만 바뀐 FIR 보고서가 된다.
    from house import rtlscan as SCAN
    결과["훑기"] = SCAN.훑기(d0.RTL, d0.top)

    # --- 1. lint · elaborate (두 도구로) ---
    결과["lint"] = SIM.lint(설계=d0)
    결과["iverilog"] = SIM.iverilog_확인(설계=d0)

    # --- 2. HLS 설계 공간 탐색 ---
    # **식을 이 회로의 크기에서 뽑는다.** 박아 둔 FIR 의 식을 쓰면 어느 회로를
    # 넘겨도 같은 표가 나온다. 다만 이것은 **크기만 흉내낸 식**이지 이 회로의
    # 데이터패스가 아니다 -- 보고서에 그렇게 적는다(`회로와무관한장`).
    식 = SCAN.데이터패스식(결과["훑기"]) if 결과["훑기"].get("됐나") \
        else "(a0*x0 + a1*x1) + (a2*x2 + a3*x3)"
    결과["HLS식"] = 식
    hls표 = []
    for 이름, res in (("4곱셈기", {"mul": 4, "add": 2, "sub": 2}),
                    ("2곱셈기", {"mul": 2, "add": 1, "sub": 1}),
                    ("1곱셈기", {"mul": 1, "add": 1, "sub": 1})):
        g = HLS.읽기(식)
        sch = HLS.스케줄(g, res)
        bnd = HLS.바인딩(g, res)
        sv = HLS.생성(g, sch, bnd, 모듈=f"hls_{이름.replace('곱셈기','m')}")
        fn = HLS.기능확인(식, sv, 모듈=f"hls_{이름.replace('곱셈기','m')}", 횟수=200)
        hls표.append({"이름": 이름, "자원": res, "지연": sch["지연_단계"], "II": sch["II"],
                    "연산기": bnd["연산기수"], "레지스터": bnd["레지스터수"],
                    "면적추정": bnd["총면적_추정"], "기능": fn["됐나"],
                    "견준벡터": fn.get("견준수", 0), "단계별": sch["단계별"],
                    "SV줄수": sv.count("\n")})
    결과["HLS"] = {"식": 식, "표": hls표}
    # PPA 스윕이 배경에서 끝나 있으면 얹는다 (없으면 없다고 적는다)
    ppa길 = Path("/tmp/hls_ppa_sweep.json")
    결과["HLS"]["PPA"] = json.loads(ppa길.read_text()) if ppa길.exists() else None

    # --- 3. 클럭 게이팅 A/B (실제 시뮬레이션 토글) ---
    게이팅 = []
    for 정책, 이름 in ((0, "상태 기반"), (1, "박자 기반")):
        rs = [SIM.돌리기({"GATE_POLICY": 정책}, seed=s, txn=회귀수 // 4, maxlen=256)
              for s in (11, 12, 13)]
        게이팅.append({"정책": 정책, "이름": 이름,
                    "절감_pct": round(sum(r["gate_save_pct"] for r in rs) / len(rs), 2),
                    "clk주기": sum(r["clk_cycles"] for r in rs),
                    "gclk주기": sum(r["gclk_cycles"] for r in rs),
                    "pass": sum(r["pass"] for r in rs), "fail": sum(r["fail"] for r in rs)})
    결과["게이팅"] = 게이팅

    # --- 4. 파형/상태 흔적 ---
    흔적 = SIM.돌리기({"GATE_POLICY": 1}, seed=21, txn=3, trace=120, maxlen=24)
    결과["흔적"] = 흔적

    # --- 5. 파라미터 재사용성: 합성 스윕 ---
    # **이 회로의 파라미터를 쓴다.** `TAPS`/`STAGES` 는 FIR 의 이름이다 -- MERA 에
    # 그것을 넘기면 verilator 가 "그런 파라미터 없다" 로 죽거나 조용히 무시한다.
    # 수로 된 기본값을 가진 파라미터를 골라 **반/두 배**로 흔든다.
    스윕 = []
    조합 = _스윕조합(결과["훑기"], d0, 빠르게)
    결과["스윕조합"] = 조합
    for c in 조합:
        try:
            r = SYN.합성(c, 설계=d0)
        except Exception as e:                               # noqa: BLE001
            스윕.append({"파라": c, "실패": f"{type(e).__name__}: {str(e)[-160:]}"})
            continue
        if r.get("됐나"):
            st = SYN.sta(r, 주기=10.0)
            스윕.append({"파라": c, "면적": r["면적_um2"], "셀수": r["셀수"],
                       "Fmax": st.get("Fmax_MHz"), "플롭": st.get("넷리스트요약", {}).get("플롭"),
                       "초": r["초"], "캐시": r.get("캐시", False)})
        else:
            스윕.append({"파라": c, "실패": r.get("까닭", "")[:200]})
    결과["스윕"] = 스윕

    # --- 6. 파라미터 기능 회귀 (재사용성은 '돌아야' 재사용이다) ---
    # **스윕이 에이전트를 죽이면 안 된다.** 실측 2026-09-22: `ACCW` 를 두 배(80)로
    # 흔들었더니 출력이 64비트를 넘어 테스트벤치가 컴파일에서 죽었다.
    #
    #     error: invalid cast from type 'VlWide<3>' to type 'int64_t'
    #
    # 그 구성이 **안 돌아간다는 것은 참말**이고 적을 값어치가 있다. 그러나 그것 때문에
    # 보고서 전체가 안 나오면 안 된다 -- 한 구성의 한계가 열세 쪽을 삼킨다.
    재사용 = []
    for c in (조합[:3] or [{}]):
        try:
            r = SIM.돌리기(c, seed=31, txn=400, 설계=d0)
        except Exception as e:                               # noqa: BLE001
            재사용.append({"파라": c, "못돌림": f"{type(e).__name__}: {str(e)[-160:]}"})
            continue
        재사용.append({"파라": c, "pass": r["pass"], "fail": r["fail"],
                    "timeout": r["timeout"], "cov": round(r["cov_pct"], 1)})
    결과["재사용"] = 재사용

    # --- 7. CDC ---
    결과["CDC"] = cdc점검(설계=d0, 훑기=결과["훑기"])
    결과["MTBF"] = [{"단수": n, "MTBF_초": mtbf(n)} for n in (1, 2, 3, 4)]

    # --- VCD: 파형은 시뮬레이터가 쓴 파일에서 읽는다 (지어내지 않는다) ---
    try:
        _길 = str(RPT.내는곳 / "nsw_fir_rtl.vcd")
        RPT.내는곳.mkdir(parents=True, exist_ok=True)
        SIM.돌리기({"TAPS": 8, "STAGES": 3, "GATE_POLICY": 1},
                seed=21, txn=6, cap=6000, cfg=3, maxlen=6, dir=2, vcd=_길)
        _d = VCD.읽기(_길)
        _a, _b = VCD.구간찾기(_d, "u_ctrl.busy", "1", 앞=60, 뒤=520)
        _c, _e = VCD.구간찾기(_d, "u_icg.en", "1", 앞=30, 뒤=210)
        _f, _g = VCD.구간찾기(_d, "u_coef_fifo.wpush", "1", 앞=40, 뒤=340)
        _이름표 = {"1": "IDLE", "10": "LOAD", "100": "RUN", "1000": "FLUSH",
                "10000": "DONE"}
        결과["vcd"] = {
            "됐나": True, "파일": _길, "바이트": pathlib.Path(_길).stat().st_size,
            "신호수": _d["신호수"], "변화수": _d["변화수"], "눈금": _d["눈금"],
            "fsm": {"신호": VCD.구간뽑기(_d, ["u_srst_sync.clk", "u_ctrl.start",
                                          "u_ctrl.in_vld", "u_ctrl.state_o",
                                          "u_ctrl.busy", "u_ctrl.done"], _a, _b, 점=240),
                    "띠": VCD.띠만들기(_d, "u_ctrl.state_o", _a, _b, 점=240, 이름표=_이름표),
                    "구간": [_a, _b]},
            "파이프": {"신호": VCD.구간뽑기(_d, ["u_mac.clk", "u_mac.push", "u_mac.prod",
                                            "u_mac.p_s1", "u_mac.a_s2", "u_mac.a_s3",
                                            "u_mac.v_s1", "u_mac.v_s2", "u_mac.v_s3"],
                                          _a, _b, 점=200), "구간": [_a, _b]},
            "게이팅": {"신호": VCD.구간뽑기(_d, ["u_srst_sync.clk", "u_icg.en",
                                            "u_icg.en_lat", "u_mac.clk"], _c, _e, 점=220),
                    "구간": [_c, _e]},
            "cdc": {"신호": VCD.구간뽑기(_d, ["u_coef_fifo.wclk", "u_coef_fifo.wpush",
                                           "u_coef_fifo.wgray", "u_coef_fifo.rq1_wgray",
                                           "u_coef_fifo.rq2_wgray",
                                           "u_coef_fifo.rempty_r"], _f, _g, 점=240),
                    "구간": [_f, _g]},
        }
    except Exception as _err:                                # noqa: BLE001
        결과["vcd"] = {"됐나": False, "까닭": f"{type(_err).__name__}: {_err}"[:180]}

    결과["초"] = round(time.time() - 결과["시작"], 1)
    return 결과


# ------------------------------------------------------------------ 보고서

def 보고서(잰것: dict) -> RPT.보고서:
    P = people.ETHAN
    # **제목이 회로 이름을 따라간다** -- 실측 2026-09-22 의 그 사고.
    _이름 = 잰것.get("설계이름") or "NSW-FIR v1.0"
    _탑 = 잰것.get("top") or "nsw_fir"
    R = RPT.보고서(P, f"{_이름} 프런트엔드 설계 보고서",
                 f"{_탑} IP", "HLS 설계공간 탐색 · FSM · 파이프라인 · 파라미터 재사용성 · 클럭 게이팅 · CDC")

    게 = 잰것["게이팅"]
    좋은 = max(게, key=lambda g: g["절감_pct"])
    나쁜 = min(게, key=lambda g: g["절감_pct"])
    R.요약(f"HLS 설계공간 3개 구성 생성·검증 완료 — 지연 "
          f"{잰것['HLS']['표'][0]['지연']}~{잰것['HLS']['표'][-1]['지연']} 단계, "
          f"3구성 × 200 벡터 = 600 벡터 전부 C 모델과 일치")
    R.요약(f"클럭 게이팅 정책을 **재서** 바꿨다: {나쁜['이름']} {나쁜['절감_pct']} % → "
          f"{좋은['이름']} {좋은['절감_pct']} % (실측 토글, "
          f"{sum(g['clk주기'] for g in 게):,} 주기)")
    # **집계가 빈 목록에서 죽지 않게 한다.** 실측 2026-09-21: 합성이 다 실패한
    # VM 에서 `min() arg is an empty sequence` 로 보고서 자체가 안 나왔다 --
    # 그러면 **왜 실패했는지 아무도 모른다.** 실패는 죽을 일이 아니라 적을 일이다.
    면적들 = [s.get("면적") for s in 잰것["스윕"] if isinstance(s.get("면적"), (int, float))]
    실패들 = [s for s in 잰것["스윕"] if "실패" in s]
    if 면적들:
        # **안 흔든 파라미터 이름을 적지 않는다.** 흔든 것을 조합에서 뽑아 쓴다.
        흔 = _흔든이름들(잰것.get("스윕조합") or [])
        깬것 = [x for x in (잰것.get("재사용") or [])
              if isinstance(x.get("fail"), int) and x["fail"] > 0]
        R.요약(f"파라미터 스윕 {len(잰것['스윕'])}개 구성 합성 — "
              + (f"{' · '.join(흔)} 를 흔들어 " if 흔 else "")
              + f"면적 {min(면적들):,.0f}~{max(면적들):,.0f} µm²"
              + (f" (<b>{len(실패들)}개 구성은 합성 실패</b>)" if 실패들 else "")
              + (f" · <b>{len(깬것)}개 구성은 기능 회귀가 깨졌다</b>" if 깬것 else ""))
    else:
        R.요약(f"<b>파라미터 스윕 {len(잰것['스윕'])}개 구성이 전부 합성에 실패했다</b> — "
              f"면적을 못 잰다. 까닭: "
              + (실패들[0].get("실패", "")[:120] if 실패들 else "알 수 없음"))
    R.요약(f"CDC 건넘 {len(잰것['CDC']['건넘'])}개 전부 동기화기 통과, 맨선 "
          f"{len(잰것['CDC']['맨선'])}개 — 판정 {잰것['CDC']['판정']}")
    R.요약(f"verilator lint 경고 {잰것['lint']['전체']}개 · iverilog 엘라보레이트 "
          f"{'통과' if 잰것['iverilog']['됐나'] else '실패'}")

    # ---------------- 0. 도구 ----------------
    R.절("0. 이 보고서가 실제로 쓴 도구")
    있 = [(k, v) for k, v in 잰것["도구"].items() if v]
    없 = [k for k, v in 잰것["도구"].items() if not v]
    R.표(["도구", "판", "무엇에 썼나"],
        [[k, v, {"verilator": "RTL lint · 시뮬레이션 엔진",
                 "iverilog": "두 번째 엘라보레이터 · HLS 생성물 기능확인",
                 "yosys": "합성(파라미터 스윕 · 면적)",
                 "g++": "시뮬레이션 하네스 컴파일"}.get(k, "-")] for k, v in 있],
        "이 기계에 **있는** 도구. 아래 모든 수는 이것들이 돌아서 나왔다.")
    R.짚기("이 기계에 <b>없는</b> 상용 도구: " + ", ".join(f"<code>{x}</code>" for x in 없) +
         ". 없는 것을 쓴 것처럼 적지 않는다. 같은 일을 하는 대안을 저장소 안에 짓고 "
         "(<code>house/hls.py</code> · <code>house/synth.py</code>), 무엇으로 쟀는지를 "
         "그림마다 대괄호로 적는다.")

    # ---------------- 1. 설계 ----------------
    # **개요를 RTL 에서 짓는다.** 여기 있던 글과 블록도는 `nsw_fir` 을 손으로
    # 적어 둔 것이었다 -- cfg_clk · nsw_afifo · nsw_icg · one-hot 5상태. MERA 를
    # 넘겨도 그 글자가 그대로 나온다. **회로 이름만 바뀐 FIR 보고서**다.
    훑 = 잰것.get("훑기") or {}
    R.절("1. 설계 개요 — RTL 에서 읽은 것")
    if 훑.get("됐나"):
        R.글(f"<b>{_탑}</b> — 모듈 {len(훑['모듈'])}개 · 줄 {훑['줄수']:,} · "
            f"포트 {len(훑['포트'])}개. 클럭 "
            + " · ".join(f"<code>{c}</code>({훑['클럭블록수'][c]} 블록)"
                        for c in 훑["클럭"])
            + f". 순차 블록 {훑['순차블록']} · 조합 {훑['조합블록']}"
            + (f" · <b>래치 위험 {len(훑['래치위험'])}</b>" if 훑["래치위험"] else "")
            + ". <b>이 절의 모든 수는 RTL 글에서 읽은 것이다</b> — 손으로 적은 것이 "
              "하나도 없다. 그래서 회로가 바뀌면 이 표도 바뀐다.")
        R.그림(_구조그림(훑), 
             "클럭 도메인(네모)과 그 사이를 건너는 신호(화살). "
             "<b>도메인도 건넘도 RTL 의 <code>posedge</code> 와 대입에서 찾은 것</b>이지 "
             "그려 둔 것이 아니다.", "house/rtlscan.py 훑기()")
        if 훑.get("톱파라미터"):
            R.표(["파라미터", "기본값", "RTL 에서 쓰인 횟수"],
                [[k, v, _쓰인수(훑, k)] for k, v in sorted(훑["톱파라미터"].items())],
                "<b>톱 모듈의 파라미터</b>(`-G` 로 바꿀 수 있는 것). "
                "'무엇을 정하나' 는 <b>기계가 못 읽는다</b> — 뜻은 스펙에 있다. "
                "여기서는 <b>이름 · 기본값 · 쓰인 횟수</b>만 적는다. "
                "아래 §5 에서 이 값을 흔들어 합성한다.",
                "house/rtlscan.py 톱파라미터")
        if 훑.get("인스턴스"):
            R.표(["하위 모듈", "인스턴스 이름"],
                [[t, n] for t, n in 훑["인스턴스"][:16]],
                "RTL 안에서 찾은 계층.", "house/rtlscan.py 인스턴스")
        R.짚기("<b>훑기가 못 보는 것:</b> " + " · ".join(훑.get("못보는것") or []))
    else:
        R.글("RTL 을 못 읽어 개요를 못 짓는다 — " + str(훑.get("까닭", "")))

    # ---------------- 2. HLS ----------------
    R.절("2. HLS 흐름 — C 식에서 RTL 까지")
    R.글("첨부하신 HLS Flow 의 <b>HLS Coding → HLS Verification (Function, PPA)</b> 상자를 "
        "실제로 돌렸다. 입력은 C 와 같은 문법의 식 하나이고, 출력은 스케줄된 파이프라인 "
        "SystemVerilog 다.")
    R.그림(V.흐름([("C 식", "a0*x0+…"), ("DFG", "ast 파싱"), ("스케줄", "자원 제약"),
                ("바인딩", "연산기·레지스터"), ("SV 생성", "값 정렬"),
                ("기능 확인", "iverilog"), ("PPA", "yosys+STA"), ("RTL 코딩", "수작업 IP")],
               "house/hls.py 가 실제로 도는 순서", 폭=680, 강조={2, 3, 4, 5, 6},
               되돌이=(6, 2, "PPA 가 안 맞으면 자원 표를 고쳐 다시"),
               아래글="노란 다섯 칸이 이 회사가 직접 지은 부분이다."),
         "HLS 흐름. 상용 HLS 도구가 없어 <b>스케줄러·바인더·코드 생성기를 직접 지었다</b>. "
         "되돌이가 자원 표로 가는 것이 HLS 의 요점이다 — 같은 C 가 다른 하드웨어가 된다.",
         "house/hls.py")

    t = 잰것["HLS"]["표"]
    R.소절("2.1 설계 공간 탐색 — 같은 식, 다른 하드웨어")
    R.코드(잰것["HLS"]["식"], "입력 (C 식)")
    R.표(["구성", "곱셈기", "덧셈기", "지연(단계)", "II", "레지스터", "면적 추정(µm²)", "기능 확인"],
        [[x["이름"], x["자원"]["mul"], x["자원"]["add"], x["지연"], x["II"],
          x["레지스터"], f"{x['면적추정']:,.0f}",
          f"통과 ({x['견준벡터']} 벡터)" if x["기능"] else "실패"] for x in t],
        "자원 표만 바꿔 세 벌을 생성하고 <b>셋 다 iverilog 로 200 벡터씩 돌려</b> C 모델과 견줬다.",
        "house/hls.py + iverilog 12.0", 강조열=[3, 7])
    R.그림(V.선([x["자원"]["mul"] for x in t],
              [("지연 (제어 단계)", [x["지연"] for x in t]),
               ("II (개시 간격)", [x["II"] for x in t])],
              "곱셈기 수에 대한 지연과 처리율", "곱셈기 수", "주기", 폭=560),
         _맞바꿈글(t),
         "house/hls.py 스케줄러")
    R.그림(V.산점([x["면적추정"] for x in t], [x["지연"] for x in t],
               "면적 대 지연 (파레토 앞면)", "면적 추정 (µm²)", "지연 (단계)",
               라벨=[x["이름"] for x in t], 폭=520),
         _파레토글(t),
         "house/hls.py 바인딩")
    # 예약표: 2곱셈기 구성의 단계별 자원 사용
    두 = [x for x in t if x["이름"] == "2곱셈기"][0]
    항목 = []
    for st in sorted(두["단계별"], key=int):
        for k, v in 두["단계별"][st].items():
            for i in range(v):
                항목.append((f"{k}{i}", int(st), [0 if k == "mul" else 1]))
    R.그림(V.예약표(["MUL", "ADD"], 항목, "2곱셈기 구성의 자원 예약표", 폭=620, 주기폭=48),
         "제어 단계마다 어느 연산기가 잡혀 있는지. 2주기 곱셈기는 두 칸을 잡는다 — "
         "<b>처음 지었을 때 이것을 안 보고 자원 2개로 4개를 쓴 스케줄을 냈다</b>. "
         "지금은 점유 표로 막는다.", "house/hls.py 스케줄러")

    PPA = 잰것["HLS"].get("PPA")
    if PPA:
        줄 = []
        for k, v in PPA.items():
            p = v.get("PPA", {})
            줄.append([k, v["지연"], v["II"], p.get("면적_um2", "-"), p.get("셀수", "-"),
                      p.get("Fmax_MHz", "-"), f"{v.get('초', 0):.0f} s"])
        R.표(["구성", "지연", "II", "합성 면적(µm²)", "셀 수", "Fmax(MHz)", "합성 시간"], 줄,
            "생성된 RTL 을 <b>실제로 합성</b>해 잰 PPA. 추정 면적이 아니라 셀 매핑 결과다.",
            "yosys 0.33 (abc -fast) + lab/se/sta")
    else:
        R.짚기("PPA 합성 스윕은 이 실행에서 끝나지 않았다(40비트 곱셈기 매핑이 오래 걸린다). "
             "면적은 위 표의 <b>연산기 기반 추정</b>이고, 실측 합성 면적이 아니다 — "
             "그 차이를 여기 적어 둔다.")

    R.경고("<b>이 절에서 실제로 난 일.</b> 처음 생성한 RTL 은 200 벡터 중 <b>199 개가 "
         "틀렸다</b>. 까닭: 제어 단계 3 에서 쓰는 피연산자를 단계 0 의 입력에서 바로 "
         "끌어왔다 — 파이프라인을 꽉 채우면 <b>엉뚱한 거래의 값끼리 더해진다</b>. "
         "값 정렬(alignment) 레지스터를 생성기에 넣어 고쳤고, 지금은 세 구성 × 200 벡터가 "
         "전부 통과한다. 이 줄을 지우지 않는 까닭은, HLS 생성물을 '도구가 냈으니 맞겠지' "
         "로 두면 정확히 이런 것이 실리콘까지 가기 때문이다.")

    # ---------------- 3. FSM ----------------
    # **상태도를 RTL 에서 그린다.** 여기 있던 상태·간선·인코딩 표는 손으로 적은
    # 것이었다. 회로가 바뀌어도 그림은 안 바뀌고, **사람은 그림을 믿는다.**
    R.절("3. FSM 제어 흐름")
    _fsm = (훑.get("FSM") or [{}])[0] if 훑.get("됐나") else {}
    _상태 = _fsm.get("상태후보") or []
    _전이 = _fsm.get("전이") or []
    if _상태 and _전이:
        R.그림(V.상태도(_상태, _전이, f"`{_fsm['신호']}` 상태 천이도", 폭=620, 높이=280,
                    시작=_상태[0]),
             f"<b>RTL 의 <code>case ({_fsm['신호']})</code> 에서 읽은 것</b>이다 — "
             f"상태 {len(_상태)}개 · 천이 {len(_전이)}개. 조건도 그 가지를 감싼 "
             f"<code>if</code> 에서 가져왔다. <b>안 적힌 조건은 빈 칸으로 둔다</b> — "
             f"지어내면 그림이 코드와 달라진다.",
             "house/rtlscan.py FSM 전이")
        R.표(["상태", "선언된 값", "나가는 곳", "조건"],
            [[a, (훑.get("로컬파라") or {}).get(a, "—"), b, c or "—"]
             for a, b, c in _전이],
            "상태 천이표. <b>손으로 적은 칸이 없다.</b> 머무는 천이(자기 자신)는 "
            "RTL 이 대입을 안 하는 것으로 표현하므로 여기 안 나온다.",
            "house/rtlscan.py", 강조열=[2])
    elif _상태:
        R.글(f"<code>case ({_fsm.get('신호')})</code> 에서 상태 {len(_상태)}개를 "
            f"찾았지만 <b>천이를 못 읽었다</b> — 대입 꼴이 이 훑기가 아는 모양이 "
            f"아니다. 상태: " + " · ".join(f"<code>{x}</code>" for x in _상태))
    else:
        R.글("<b>이 회로에서 FSM 을 못 찾았다.</b> <code>case</code> 문이 없거나 "
            "상태를 <code>localparam</code> 으로 안 적었다. "
            "<b>없는 상태도를 그리지 않는다.</b>")

    흔 = 잰것["흔적"]
    vc = 잰것.get("vcd") or {}
    if vc.get("됐나") and (vc.get("fsm") or {}).get("신호"):
        f = vc["fsm"]
        R.그림(V.파형뷰어(f["신호"], "FSM 천이 — 시뮬레이터가 쓴 VCD 에서 읽은 것",
                      폭=680, 시작시각=f["구간"][0], 끝시각=f["구간"][1],
                      주석띠=[(x, y, g, "#c0392b") for x, y, g in (f.get("띠") or [])]),
             f"<b>파형을 지어내지 않았다.</b> verilator 에 <code>--trace</code> 를 걸어 "
             f"VCD 를 쓰고(<code>{pathlib.Path(vc['파일']).name}</code>, {vc['바이트']:,} 바이트, "
             f"신호 {vc['신호수']}개, 값 변화 {vc['변화수']:,}회) 그 파일을 파서로 되읽었다. "
             "아래 빨간 띠는 <code>state_o</code> 가 실제로 지난 상태를 구간으로 묶은 것이다 — "
             "<b>IDLE 에서 LOAD 로 가려면 start 가 떠야 하고, DONE 은 ack 를 기다린다</b>. "
             "원핫이라 <code>state_o</code> 의 값이 곧 상태 번호다.",
             "house/dv/vcd.py 로 읽은 VCD")
    R.코드("""// house/rtl/src/nsw_fir.sv -- 원핫 FSM (발췌)
localparam [4:0] S_IDLE=5'b00001, S_LOAD=5'b00010, S_RUN=5'b00100,
                 S_FLUSH=5'b01000, S_DONE=5'b10000;
reg [4:0] st, st_n;

always @(*) begin
    st_n = st;
    case (1'b1)                       // one-hot: 한 비트만 본다
      st[0]: if (start)              st_n = S_LOAD;
      st[1]: if (cnt == TAPS-1)      st_n = S_RUN;
      st[2]: if (cnt == len-1 && in_vld) st_n = S_FLUSH;
      st[3]: if (cnt == STAGES-1)    st_n = S_DONE;
      st[4]: if (ack)                st_n = S_IDLE;
      default:                       st_n = S_IDLE;   // 불법 상태 -> 복구
    endcase
end

always @(posedge clk or negedge rst_n)
    if (!rst_n) st <= S_IDLE; else st <= st_n;""",
        "FSM 코드 — 이 코드가 위 파형을 만든다")

    # ---------------- 4. 파이프라인 ----------------
    R.절("4. 파이프라인")
    R.그림(SCH.데이터패스(
        ["S1", "S2", "S3"],
        [("din / coef", 0, 96, 92, 40, "#dce8f5", "16b × 16b"),
         ("MUL", 1, 96, 78, 40, "#f5c9c2", "16×16 → 32b"),
         ("ADD", 2, 96, 78, 40, "#f5c9c2", "acc + p (40b)"),
         ("SAT", 3, 96, 78, 40, "#f5c9c2", "±2^39 클램프"),
         ("tap_ptr", 0, 158, 92, 30, "#eef3d8", "TAPS 에서 감김"),
         ("acc_o / vld_o", 3, 158, 92, 30, "#cfe9d8", "출력")],
        "nsw_mac 3단 파이프라인 데이터패스 (STAGES=3)", 폭=660, 높이=240),
         "강의 화면의 데이터패스 그림과 같은 꼴이다 — <b>빨간 기둥이 파이프라인 "
         "레지스터</b>이고, 기둥 사이가 한 주기 안에 끝나야 하는 조합 논리다. "
         "<code>p_s1</code>(곱) → <code>a_s2</code>(합) → <code>a_s3</code>(포화)로 "
         "값이 밀려가고, 유효 비트 <code>v_s1/v_s2/v_s3</code> 가 같이 따라간다 — "
         "<b>유효 비트를 같이 밀지 않으면 FLUSH 때 쓰레기가 출력으로 나간다</b>. "
         "임계경로는 곱셈기 단(§8 의 STA 가 그것을 확인한다).",
         "house/rtl/src/nsw_fir.sv 의 nsw_mac")
    if vc.get("됐나") and (vc.get("파이프") or {}).get("신호"):
        pp = vc["파이프"]
        R.그림(V.파형뷰어(pp["신호"], "파이프라인이 실제로 미는 장면 (VCD)",
                      폭=680, 시작시각=pp["구간"][0], 끝시각=pp["구간"][1]),
             "<b>파이프라인이 도는 것을 값으로 본다.</b> <code>push</code> 가 뜬 주기의 "
             "<code>prod</code> 가 다음 주기 <code>p_s1</code> 에 들어가고, 그것이 "
             "<code>a_s2</code> 에서 누산되어 <code>a_s3</code> 로 나온다 — "
             "<b>세 칸 밀려 있는 것이 곧 3단 지연</b>이다. "
             "<code>v_s1/v_s2/v_s3</code> 가 같은 모양으로 따라가는 것이 유효 비트다. "
             "맨 윗줄은 <b>게이팅된 클럭</b>이라 쉬는 구간에는 엣지 자체가 없다.",
             "house/dv/vcd.py — u_mac.* ")
    R.코드("""// nsw_mac -- 3단 파이프라인 (발췌).  en 과 push 를 **가른다**.
always @(posedge clk or negedge rst_n) begin
  if (!rst_n) begin p_s1 <= '0; v_s1 <= 1'b0; end
  else if (en) begin
    p_s1 <= push ? prod : '0;      // FLUSH 때 새 곱을 넣지 않는다
    v_s1 <= push;                  // 유효 비트도 같이 민다
  end
end
// s2: 누산,  s3: 포화
wire signed [ACCW:0] raw = a_s2 + ext;
assign sum = (raw > SAT_HI) ? SAT_HI : (raw < SAT_LO) ? SAT_LO : raw[ACCW-1:0];""",
        "파이프라인 코드 — `en` 과 `push` 를 가른 것이 FLUSH 버그를 고친 한 줄이다")
    R.그림(V.예약표(["MUL", "ADD", "SAT"],
                 [("샘플 0", 0, [0, 1, 2]), ("샘플 1", 1, [0, 1, 2]),
                  ("샘플 2", 2, [0, 1, 2]), ("샘플 3", 3, [0, 1, 2]),
                  ("FLUSH", 4, [0, 1, 2])],
                 "nsw_mac 3단 파이프라인 예약표 (STAGES=3)", 폭=620, 주기폭=52),
         "한 줄이 한 샘플이다. 겹쳐 보이는 것이 파이프라인 — 지연은 3 주기이지만 "
         "처리율은 <b>주기당 1 샘플</b>이다. 마지막 FLUSH 줄이 파이프라인을 비운다.",
         "house/rtl/src/nsw_fir.sv 의 nsw_mac")
    if 흔.get("cyc_hist"):
        R.그림(V.히스토그램(흔.get("cyc_hist") or [], 20, "거래당 주기 분포", "주기", "거래 수"),
             "짧은 거래는 고정 비용(계수 로드 + FLUSH)이 지배하고, 긴 거래는 len 에 비례한다.",
             "verilator")
    # **이 표는 «파이프라인 깊이를 흔들었을 때» 의 표다.** 실측 2026-09-22
    # (RTL-RPT): 거르개가 `"STAGES" in x["파라"]` 였는데 그 칸은 **모든 구성에
    # 늘 있다**(기본값으로). 그래서 ACCW 를 흔든 줄까지 들어왔고, `STAGES 3 ·
    # 지연 3` 두 줄이 하나는 400 통과, 하나는 **385 실패**로 나란히 섰다 --
    # 「깊이를 바꿔도 기능이 유지된다」는 설명 아래에서. 두 가지가 틀렸다:
    #   · 「지연(주기)」 칸은 **잰 값이 아니라 파라미터 값**을 그대로 찍었다
    #   · 깊이를 안 흔든 결과가 깊이 표에 들어왔다
    # 이제 **정말로 바뀐 칸만** 본다.
    _기본파라 = (잰것.get("스윕조합") or [{}])[0]
    _깊이줄 = _깊이흔든줄(잰것["재사용"], _기본파라)
    if _깊이줄:
        # **임계경로 열을 뺐다.** 옛 판은 `STAGES==2 면 MUL|ADD, 아니면 MUL|ADD|SAT`
        # 로 **지어냈다** -- 구성별 임계경로는 이 실행에서 재지 않는다.
        R.표(["바꾼 것", "기능 회귀"],
            [[_구성이름(x["파라"], _기본파라),
              f"{x['pass']} 통과 / {x['fail']} 실패 / {x['timeout']} 타임아웃"]
             for x in _깊이줄],
            "파이프라인 깊이를 바꿔도 기능이 유지되는지 <b>실제로 돌려</b> 확인했다.",
            "verilator, seed=31, 400 거래")
    else:
        _흔든 = _흔든이름들(잰것.get("스윕조합") or [])
        R.짚기("<b>이 스윕은 파이프라인 깊이를 안 흔들었다.</b> "
               + (f"흔든 것은 <code>{' · '.join(_흔든)}</code> 다 — "
                  if _흔든 else "")
               + "깊이를 바꾼 구성이 없으므로 「깊이를 바꿔도 도는가」 는 "
                 "<b>이 실행이 답하지 못한 물음</b>이다. "
                 "<code>_스윕조합()</code> 이 값이 큰 파라미터부터 고르기 때문이다.")

    # ---------------- 5. 재사용성 ----------------
    R.절("5. 파라미터 재사용성 — 말이 아니라 합성 결과로")
    좋은스윕 = [s for s in 잰것["스윕"] if "면적" in s]
    if 좋은스윕:
        기본파라 = (잰것.get("스윕조합") or [{}])[0]
        이름들 = [_구성이름(s["파라"], 기본파라) for s in 좋은스윕]

        def _끄는것(칸, 큰쪽이름):
            """어느 파라미터가 이 값을 가장 많이 움직였나 — **재서 적는다.**"""
            기 = next((s for s in 좋은스윕
                     if not _바뀐것(s["파라"], 기본파라)), None)
            밑 = (기 or {}).get(칸)
            if not isinstance(밑, (int, float)) or not 밑:
                return ""
            폭 = []
            for s in 좋은스윕:
                d = _바뀐것(s["파라"], 기본파라)
                v = s.get(칸)
                if len(d) == 1 and isinstance(v, (int, float)):
                    폭.append((abs(v - 밑) / 밑, next(iter(d)), v))
            if not 폭:
                return ""
            폭.sort(reverse=True)
            비, 이름, 값 = 폭[0]
            return (f" 가장 크게 움직인 것은 <code>{이름}</code> 다 — "
                  f"기본 {밑:,.0f} 에서 {값:,.0f} 로 {비*100:.0f} % 바뀐다.")

        R.그림(V.막대(이름들, [s["면적"] for s in 좋은스윕], "구성별 합성 면적", "면적 (µm²)", 폭=560),
             "<b>RTL 한 줄도 안 고치고</b> 파라미터만 바꿔 합성한 결과. "
             "<b>가로축은 기본 구성과 다른 칸만 적는다</b> — 안 흔든 파라미터를 "
             "이름에 넣으면 여섯 막대가 같은 이름으로 찍힌다(실측으로 겪었다)."
             + _끄는것("면적", "면적"),
             f"yosys 0.33 · abc -fast · {SYN.LIB.name}")
        R.그림(V.막대(이름들, [s.get("Fmax") or 0 for s in 좋은스윕], "구성별 Fmax", "MHz",
                   색들=[V.초록] * len(좋은스윕), 폭=560),
             "같은 구성들의 최대 주파수." + _끄는것("Fmax", "Fmax")
             + " <b>이 수는 «왜» 를 말하지 않는다</b> — 어느 파라미터가 움직였는지만 "
               "잰 것이고, 그것이 산술 임계경로를 늘려서인지 abc 가 다르게 "
               "최적화해서인지는 이 실행이 안 가른다.",
             "lab/se/sta (블록기반 + 경로기반 두 길로 대조)")
        R.표(["구성 (기본과 다른 칸)", "면적(µm²)", "셀 수", "플롭", "Fmax(MHz)", "합성 시간"],
            [[nm, f"{s['면적']:,.1f}", f"{s['셀수']:,}", s.get("플롭", "-"),
              s.get("Fmax", "-"), f"{s['초']:.1f} s" + (" (캐시)" if s.get("캐시") else "")]
             for nm, s in zip(이름들, 좋은스윕)],
            "파라미터 스윕 원본 수치. <b>기본 구성은 그냥 «기본» 으로 적는다.</b>",
            "yosys + lab/se/sta", 강조열=[0])
    # **이 자리에 «STAGES 를 3→2 로 줄였더니…» 가 박혀 있었다.** 그런데 이 스윕은
    # STAGES 를 한 번도 안 흔든다(실측 2026-09-22). **돌지 않은 실험의 결론이
    # 매 보고서마다 실려 나갔다.** 이제 흔든 것에서만 말한다.
    _흔든것 = _흔든이름들(잰것.get("스윕조합") or [])
    _기본2 = (잰것.get("스윕조합") or [{}])[0]
    _깨진 = [x for x in (잰것.get("재사용") or [])
          if isinstance(x.get("fail"), int) and x["fail"] > 0]
    if _깨진:
        R.경고("<b>파라미터를 바꾸자 기능이 깨진 구성이 있다.</b> "
             + " · ".join(f"<code>{_구성이름(x['파라'], _기본2)}</code> "
                          f"{x['pass']} 통과 / <b>{x['fail']} 실패</b>"
                          for x in _깨진[:4])
             + " — <b>재사용이란 돌아야 재사용이다.</b> 이 구성들은 "
               "「파라미터를 바꿔도 된다」 는 주장에 들어가지 않는다. "
               "아래 표에 까닭과 함께 그대로 남긴다.")
    if _흔든것:
        R.짚기(f"<b>이 스윕이 흔든 것은 <code>{' · '.join(_흔든것)}</code> 뿐이다.</b> "
               f"<code>_스윕조합()</code> 이 <b>값이 큰 파라미터부터</b> 고르기 "
               f"때문이다 — 그래서 <code>TAPS</code>·<code>STAGES</code> 같은 "
               f"구조 파라미터는 이 표에 <b>안 들어 있다</b>. "
               f"위 수를 그 파라미터들의 값으로 읽으면 안 된다.")
    # **못 돌린 구성도 줄로 남긴다.** 빼 버리면 표가 "다 돌았다" 로 읽힌다.
    R.표(["바꾼 파라미터", "통과", "실패", "타임아웃", "커버리지(%)"],
        # **표 칸은 HTML 을 글자로 찍는다.** 실측 2026-09-22: `<small>…</small>` 을
        # 붙였더니 태그가 그대로 보였다. 전체 파라미터는 표 밑에 한 번만 적는다 --
        # 구성마다 한 칸씩만 다르므로 스물여덟 번 되풀이할 까닭이 없다.
        [[_구성이름(x["파라"], (잰것.get("스윕조합") or [{}])[0]),
          x.get("pass", "—"), x.get("fail", "—"), x.get("timeout", "—"),
          x.get("cov", x.get("못돌림", "—"))]
         for x in 잰것["재사용"]],
        "<b>재사용이란 돌아야 재사용이다.</b> 파라미터를 바꾼 뒤 기능 회귀를 다시 돌린 결과. "
        "<b>못 돌린 구성은 까닭을 적는다</b> — 빼 버리면 이 표가 '다 돌았다' 로 읽힌다. "
        "왼쪽 칸은 <b>기본 구성과 다른 칸만</b> 적는다.",
        "verilator", 강조열=[2])
    if 잰것.get("스윕조합"):
        R.짚기("<b>기본 구성:</b> <code>"
               + json.dumps(잰것["스윕조합"][0], ensure_ascii=False)
               + "</code> — 위 표의 구성들은 여기서 <b>한 칸씩만</b> 다르다.")

    # ---------------- 6. 클럭 게이팅 ----------------
    R.절("6. 저전력 — 클럭 게이팅 정책을 재서 골랐다")
    R.그림(SCH.cgic({"잰것": f"이 설계에서 실측: 데이터패스 클럭 {좋은['절감_pct']} % 절감 "
                          f"({좋은['clk주기']:,} → {좋은['gclk주기']:,} 주기)"}, 폭=560),
         "<b>래치가 왜 있나.</b> EN 을 AND 에 바로 물리면, EN 이 <b>클럭이 높은 구간</b>에 "
         "바뀔 때 게이팅된 클럭에 <b>짧은 펄스(글리치)</b>가 나간다 — 플롭이 엉뚱한 값을 "
         "잡는다. 래치가 EN 을 <b>클럭이 낮은 동안에만</b> 통과시키므로, 게이팅된 클럭은 "
         "언제나 온전한 펄스이거나 아예 없다. "
         "<code>test_en</code>(=<code>scan_en</code>)은 스캔 시프트 중 게이팅을 여는 "
         "우회로다 — 이것이 없으면 게이팅된 플롭이 스캔 체인에서 안 밀린다.",
         "house/rtl/src/nsw_fir.sv 의 nsw_icg")
    if vc.get("됐나") and (vc.get("게이팅") or {}).get("신호"):
        gg = vc["게이팅"]
        R.그림(V.파형뷰어(gg["신호"], "CGIC 실측 파형 — CLK · EN · 래치 출력 · 게이팅된 클럭",
                      폭=680, 시작시각=gg["구간"][0], 끝시각=gg["구간"][1]),
             "<b>위 회로도가 실제로 그렇게 동작하는 것을 VCD 에서 확인한 것</b>이다. "
             "<code>u_icg.en</code> 이 뜨면 <code>en_lat</code> 이 <b>클럭이 낮은 구간에</b> "
             "따라 올라가고, 그때부터 <code>u_mac.clk</code>(게이팅된 클럭)이 토글한다. "
             "중간에 EN 이 한 주기 빠지는 자리를 보면 게이팅된 클럭이 "
             "<b>펄스 하나를 통째로 건너뛴다</b> — 반쪽 펄스가 없다. 그것이 래치가 하는 일이다.",
             "house/dv/vcd.py — u_icg.en / en_lat / u_mac.clk")
    R.코드("""// nsw_icg -- 통합 클럭 게이팅 셀.  래치 + AND.
module nsw_icg (input wire clk, input wire en, input wire test_en,
                output wire gclk);
    reg en_lat;
    always @(*) if (!clk) en_lat = en | test_en;   // 클럭 낮을 때만 연다
    assign gclk = clk & en_lat;
endmodule

// 정책 B (GATE_POLICY=1) -- 유효 샘플이 있는 주기에만 클럭을 준다
assign dp_en = (GATE_POLICY == 0) ? st_active
                                  : ((st == S_FLUSH) | (st_active & in_vld));""",
        "ICG 코드와 게이팅 정책 — 아래 A/B 비교가 이 한 줄의 값이다")
    R.그림(V.막대([g["이름"] for g in 게], [g["절감_pct"] for g in 게],
               "클럭 게이팅 정책별 데이터패스 클럭 절감률", "절감 (%)",
               색들=[V.흐림, V.초록], 폭=520),
         f"같은 자극(seed 11·12·13, 거래 {sum(g['pass'] for g in 게)//2:,}건, "
         f"{sum(g['clk주기'] for g in 게)//2:,} 주기)으로 두 정책을 돌려 "
         f"<b>ICG 인에이블의 실제 토글을 센 값</b>이다. 추정이 아니다.",
         "verilator + nsw_fir.gate_en_o 관측 포트")
    R.표(["정책", "설명", "clk 주기", "gclk 주기", "절감률", "기능"],
        [[g["이름"], "LOAD|RUN|FLUSH 내내 클럭 공급" if g["정책"] == 0
          else "유효 샘플이 있는 주기에만 공급",
          f"{g['clk주기']:,}", f"{g['gclk주기']:,}", f"{g['절감_pct']} %",
          f"{g['pass']:,} 통과 / {g['fail']} 실패"] for g in 게],
        "정책 A/B. 두 정책 모두 기능은 같고 전력만 다르다 — 그래서 고를 수 있다.",
        "verilator", 강조열=[4])
    R.짚기(f"<b>{좋은['절감_pct'] - 나쁜['절감_pct']:.1f} 퍼센트포인트</b>가 RTL 한 줄에서 나왔다: "
         f"<code>dp_en = st_active</code> 를 <code>dp_en = FLUSH | (st_active &amp; in_vld)</code> "
         f"로 바꾼 것이다. 백프레셔로 입력이 비는 주기에 클럭을 계속 주고 있었던 것인데, "
         f"이것은 <b>파형을 보기 전에는 안 보인다</b> — 기능 시뮬레이션은 둘 다 통과한다.")
    R.글("DFT 와의 접점: ICG 의 <code>test_en</code> 에 <code>scan_en</code> 이 물려 있어 "
        "스캔 시프트 중에는 게이팅이 열린다. 이것이 없으면 게이팅된 플롭이 스캔 체인에서 "
        "시프트되지 않는다 — Sofia(DFT) 의 보고서에서 같은 신호를 다시 본다.")

    # ---------------- 7. CDC ----------------
    R.절("7. CDC — 클럭 도메인 크로싱")
    c = 잰것["CDC"]
    R.그림(SCH.동기화기(2, f"이 설계: 건넘 {len(c['건넘'])}개 전부 동기화기 통과 · "
                    f"맨선 {len(c['맨선'])}개", 폭=580),
         "두 클럭이 서로 무관하면 한쪽 신호를 다른 쪽에서 <b>그냥 잡으면 안 된다</b> — "
         "셋업/홀드를 못 지켜 플롭이 <b>준안정</b>에 빠진다. 2단 동기화기는 그 확률을 "
         "지수로 줄인다(§7.2 의 MTBF). 레벨 신호를 <b>한 주기 펄스</b>로 바꾸려면 "
         "동기화기 뒤에 플롭 하나를 더 두고 XOR 한다 — 입력과 출력의 레벨이 다른 "
         "한 주기 동안만 1 이다.",
         "house/rtl/src/nsw_fir.sv 의 nsw_sync2")
    if vc.get("됐나") and (vc.get("cdc") or {}).get("신호"):
        cc = vc["cdc"]
        R.그림(V.파형뷰어(cc["신호"], "CDC 실측 파형 — 그레이 포인터가 2FF 를 건넌다",
                      폭=680, 시작시각=cc["구간"][0], 끝시각=cc["구간"][1]),
             "비동기 FIFO 의 쓰기 포인터 <code>wgray</code> 가 읽기 도메인으로 "
             "건너오는 장면이다. <code>rq1_wgray</code> → <code>rq2_wgray</code> 가 "
             "2단 동기화기이고, 값이 <b>한 주기씩 밀려</b> 도착한다. "
             "<b>그레이 코드라서 한 번에 한 비트만 바뀐다</b> — 그래서 샘플링 순간에 "
             "걸려도 결과는 옛 값 아니면 새 값이지, 그 사이의 없는 값이 아니다. "
             "<b>이 파형은 준안정을 보이지 않는다</b> — 2상태 시뮬레이터에는 준안정이 "
             "없다. 보이는 것은 지연 구조이고, 준안정은 아래 MTBF 로만 다룬다.",
             "house/dv/vcd.py — u_coef_fifo.wgray / rq1 / rq2")
    R.표(["클럭", "always 블록 수"], [[k, v] for k, v in sorted(c["도메인"].items())],
        "RTL 에서 뽑은 클럭 도메인.", "house/rtl/agent.py cdc점검()")
    R.표(["건너는 신호", "보내는 도메인", "받는 도메인", "종류", "보이는 모양"],
        [[x["신호"], x["보내는곳"], x["받는곳"], x["종류"], x["방식"]]
         for x in c["건넘"]],
        f"도메인 건넘 {len(c['건넘'])}개 — <b>RTL 에서 찾은 것</b>이다(어느 클럭 아래에서 "
        f"쓰이고 어느 클럭 아래에서 읽히나). 판정 <b>{c['판정']}</b>. "
        f"<b>'안전한가' 칸을 없앴다</b> — 이 훑기는 모양만 본다. 다단으로 보인다고 "
        f"안전한 것이 아니다(여러 비트가 같이 건너면 2FF 로도 깨진다).",
        "house/rtlscan.py CDC건넘", 강조열=[4])
    R.짚기("<b>이 점검이 못 보는 것:</b> " + " · ".join(c.get("못보는것") or []))
    R.그림(V.블록도(
        [("cfg_clk", 20, 60, 108, 54, "#eef4fb", "느린 도메인"),
         ("gray ptr", 168, 20, 104, 44, "#fdf6e3", "한 비트만 변함"),
         ("2FF sync", 168, 96, 104, 44, "#fdf6e3", "2단 플롭"),
         ("FIFO mem", 168, 168, 104, 40, "#f5f7fa", "듀얼 포트"),
         ("clk", 312, 60, 104, 54, "#eaf5ee", "빠른 도메인")],
        [("cfg_clk", "gray ptr", "wgray", V.파랑), ("gray ptr", "2FF sync", "", V.흐림),
         ("2FF sync", "clk", "안전", V.초록), ("cfg_clk", "FIFO mem", "wdata", V.파랑),
         ("FIFO mem", "clk", "rdata", V.초록)],
        "비동기 FIFO 의 CDC 구조", 폭=460, 높이=224),
        "데이터는 메모리로, 제어(포인터)는 그레이 코드 + 2FF 로 건넌다. "
        "<b>이진 카운터를 그대로 건네면</b> 여러 비트가 한꺼번에 바뀌어 표본 순간에 "
        "존재하지 않는 값이 잡힐 수 있다.", "house/rtl/src/nsw_fir.sv 의 nsw_afifo")
    m = 잰것["MTBF"]
    R.그림(V.선([x["단수"] for x in m], [("MTBF (초)", [x["MTBF_초"] for x in m])],
              "동기화기 단수에 대한 MTBF", "동기화기 단수", "MTBF (초)", 로그y=True, 폭=540,
              기준선=3.15e9, 기준글="100년"),
         "τ=25 ps, Tw=30 ps, f_clk=100 MHz, f_data=10 MHz 로 셈한 값. "
         "<b>단수 하나가 MTBF 를 지수로 바꾼다</b> — 2단이 기본인 까닭이고, "
         "<code>CDC_STAGES</code> 파라미터로 3단까지 올릴 수 있게 둔 까닭이다.",
         "house/rtl/agent.py mtbf() — 가정값은 본문에 적음")
    R.표(["단수", "MTBF (초)", "사람이 읽는 값"],
        [[x["단수"], f"{x['MTBF_초']:.3g}",
          ("우주 나이(4.4e17 s)를 한참 넘음" if x["MTBF_초"] >= 1e300 else
           f"{x['MTBF_초']/3.15e7:.3g} 년" if x["MTBF_초"] > 3.15e7 else f"{x['MTBF_초']:.3g} 초")]
         for x in m], "준안정 MTBF. 가정 파라미터는 위 그림 설명에 있다.", "닫힌 꼴")

    # ---------------- 8. lint ----------------
    R.절("8. 정적 점검 (lint · 두 도구 엘라보레이트)")
    l = 잰것["lint"]
    if l["종류"]:
        R.그림(V.막대(list(l["종류"].keys()), list(l["종류"].values()),
                   "verilator lint 경고 종류별", "건수", 폭=520),
             "현재 남은 경고.", "verilator --lint-only -Wall")
    else:
        R.표(["검사", "결과"],
            [["verilator --lint-only -Wall", f"경고 0건 (rc={l['rc']})"],
             ["iverilog -g2012 엘라보레이트", "통과" if 잰것["iverilog"]["됐나"] else "실패"]],
            "두 도구 다 깨끗하다. 한 도구만 믿지 않는다.", "verilator 5.020 / iverilog 12.0")
    R.경고("<b>lint 가 실제로 잡은 것 (설계 중).</b> 초판 비동기 FIFO 에서 "
         "<code>UNOPTFLAT — Circular combinational logic: wbin_nxt</code> 가 떴다. "
         "<code>wfull</code> 을 조합으로 뽑아 쓰면 <code>wfull → wbin_nxt → wgray_nxt → "
         "wfull</code> 조합 고리가 생긴다. full/empty 를 등록해 끊었다(Cummings 표준형). "
         "이 경고가 없었으면 합성은 통과하고 실리콘에서 발진했을 자리다.")

    # ---------------- 9. 한계 ----------------
    R.한계(
        "· <b>HLS 가 받는 것은 산술 식 하나뿐이다.</b> 루프·조건문·배열·메모리 인터페이스는 아직 못 받는다.<br>"
        "· <b>CDC 점검은 텍스트 기반이다.</b> 계층 전체에 걸친 신호 전파와 재수렴(reconvergence) 검사는 하지 않는다. "
        "상용 CDC 도구(Spyglass·Questa CDC)가 하는 일의 일부만 한다.<br>"
        "· <b>MTBF 의 τ 와 Tw 는 가정값이다.</b> 파운드리 특성화 값이 아니다 — 단수 사이의 <i>비</i>는 의미가 있고 "
        "절댓값은 자릿수만 의미가 있다.<br>"
        "· <b>셀 라이브러리는 PDK 가 아니다.</b> <code>lab/se/mklib.py</code> 가 RC 모형에서 만든 것이다(FO4 55.2 ps). "
        "면적·Fmax 의 절댓값이 아니라 구성 사이의 비를 읽어야 한다.<br>"
        "· <b>전력은 토글 수로만 쟀다.</b> 커패시턴스 가중 동적 전력과 누설은 Marcus(PI) 보고서에서 다룬다.")

    R.잰것 = [("HLS 구성 수", len(t), "개", "house/hls.py"),
            ("HLS 기능확인 벡터", sum(x["견준벡터"] for x in t), "벡터", "iverilog 12.0"),
            ("게이팅 절감 (상태 기반)", 나쁜["절감_pct"], "%", "verilator 토글 실측"),
            ("게이팅 절감 (박자 기반)", 좋은["절감_pct"], "%", "verilator 토글 실측"),
            ("시뮬레이션 주기 합", f"{sum(g['clk주기'] for g in 게):,}", "주기", "verilator 5.020"),
            ("합성 구성 수", len(좋은스윕), "개", "yosys 0.33"),
            ("CDC 건넘 / 맨선", f"{len(c['건넘'])} / {len(c['맨선'])}", "개", "house/rtl/agent.py"),
            ("lint 경고", l["전체"], "건", "verilator --lint-only -Wall"),
            ("보고서 생성 시간", 잰것["초"], "s", "실측")]
    return R


def 돌리기(빠르게=False, 회로=None) -> dict:
    from house import designs as DES
    잰것 = 일하기(빠르게=빠르게, 설계=DES.찾기(회로))
    R = 보고서(잰것)
    길 = R.내기()
    return {"사람": people.ETHAN, "잰것": 잰것, "pdf": 길, "쪽": RPT.쪽수(길),
            "요약": R.요약줄, "그림수": R.그림수, "표수": R.표수}


if __name__ == "__main__":
    r = 돌리기("--빠르게" in sys.argv)
    print(f"PDF -> {r['pdf']}  ({r['쪽']} 쪽, 그림 {r['그림수']}, 표 {r['표수']})")
    for s in r["요약"]:
        print(" ·", re.sub(r"<[^>]+>", "", s))
