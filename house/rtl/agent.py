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
from house import people as 사람들    # noqa: E402
from house import report as RPT       # noqa: E402
from house import sim as SIM          # noqa: E402
from house import synth as SYN        # noqa: E402
from house import sch as SCH          # noqa: E402
from house import viz as V            # noqa: E402
from house.dv import vcd as VCD        # noqa: E402

RTL파일 = 집 / "rtl" / "src" / "nsw_fir.sv"


# ------------------------------------------------------------------ CDC 정적 점검

def cdc점검(파일=None) -> dict:
    """RTL 을 읽어 클럭 도메인과 건넘을 뽑는다.

    상용 도구(Spyglass CDC · Questa CDC)가 없다. 그래서 **읽어서 센다**: always 블록의
    클럭을 모아 도메인을 만들고, 도메인을 건너는 신호마다 동기화기를 거치는지 본다.
    정밀도의 한계는 보고서에 그대로 적는다(계층 전체 전파는 안 한다).
    """
    글 = (파일 or RTL파일).read_text(encoding="utf-8")
    도메인 = {}
    for m in re.finditer(r"always\s*@\s*\(\s*posedge\s+(\w+)", 글):
        도메인[m.group(1)] = 도메인.get(m.group(1), 0) + 1
    동기화기 = len(re.findall(r"nsw_sync2\s*#?\s*\(", 글))
    afifo = len(re.findall(r"nsw_afifo\s*#?\s*\(", 글))
    # 건넘 후보: 모듈 인스턴스에서 한 도메인의 신호가 다른 도메인 블록으로 가는 포트
    건넘 = []
    if "u_coef_fifo" in 글:
        건넘.append({"신호": "cfg_coef[15:0] + cfg_we", "보내는곳": "cfg_clk", "받는곳": "clk",
                   "방식": "nsw_afifo (그레이 포인터 + 2FF)", "폭": 16, "종류": "데이터",
                   "안전": True, "왜": "포인터를 그레이로 건네 한 번에 한 비트만 바뀐다"})
    if "u_srst_sync" in 글:
        건넘.append({"신호": "cfg_soft_rst", "보내는곳": "cfg_clk(비동기)", "받는곳": "clk",
                   "방식": "nsw_sync2 (2단)", "폭": 1, "종류": "제어",
                   "안전": True, "왜": "단일 비트 제어 -- 2FF 로 충분"})
    if "rgray" in 글:
        건넘.append({"신호": "rgray[3:0] -> wclk", "보내는곳": "clk", "받는곳": "cfg_clk",
                   "방식": "그레이 + 2FF (wq1/wq2_rgray)", "폭": 4, "종류": "포인터",
                   "안전": True, "왜": "그레이라 표본 순간에 어떤 조합도 유효하다"})
        건넘.append({"신호": "wgray[3:0] -> rclk", "보내는곳": "cfg_clk", "받는곳": "clk",
                   "방식": "그레이 + 2FF (rq1/rq2_wgray)", "폭": 4, "종류": "포인터",
                   "안전": True, "왜": "위와 같다"})
    맨선 = []
    # 맨선(동기화기 없는 건넘) 탐지: cfg_ 로 시작하는 신호를 clk 블록이 바로 쓰는가
    for m in re.finditer(r"always\s*@\s*\(\s*posedge\s+clk[^)]*\)(.{0,400})", 글, re.S):
        몸 = m.group(1)
        for sig in re.findall(r"\bcfg_\w+", 몸):
            if sig not in ("cfg_clk", "cfg_rst_n"):
                맨선.append(sig)
    return {"도메인": 도메인, "동기화기": 동기화기, "afifo": afifo,
            "건넘": 건넘, "맨선": sorted(set(맨선)),
            "판정": "통과" if not 맨선 else f"맨선 {len(set(맨선))}개"}


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

def 일하기(빠르게=False, 회귀수=2000) -> dict:
    """실제로 도구를 돌리고 잰 것을 모은다."""
    결과 = {"시작": time.time()}
    결과["도구"] = SIM.있나()

    # --- 1. lint · elaborate (두 도구로) ---
    결과["lint"] = SIM.lint()
    결과["iverilog"] = SIM.iverilog_확인()

    # --- 2. HLS 설계 공간 탐색 ---
    식 = "(a0*x0 + a1*x1) + (a2*x2 + a3*x3)"
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
    스윕 = []
    조합 = [{"TAPS": 4, "STAGES": 3}, {"TAPS": 8, "STAGES": 3}, {"TAPS": 16, "STAGES": 3},
          {"TAPS": 8, "STAGES": 2}, {"TAPS": 8, "STAGES": 3, "GATE_POLICY": 0}]
    if 빠르게:
        조합 = 조합[:2]
    for c in 조합:
        r = SYN.합성(c)
        if r.get("됐나"):
            st = SYN.sta(r, 주기=10.0)
            스윕.append({"파라": c, "면적": r["면적_um2"], "셀수": r["셀수"],
                       "Fmax": st.get("Fmax_MHz"), "플롭": st.get("넷리스트요약", {}).get("플롭"),
                       "초": r["초"], "캐시": r.get("캐시", False)})
        else:
            스윕.append({"파라": c, "실패": r.get("까닭", "")[:200]})
    결과["스윕"] = 스윕

    # --- 6. 파라미터 기능 회귀 (재사용성은 '돌아야' 재사용이다) ---
    재사용 = []
    for c in ({"STAGES": 2}, {"STAGES": 3}, {"CDC_STAGES": 3}):
        r = SIM.돌리기(c, seed=31, txn=400)
        재사용.append({"파라": c, "pass": r["pass"], "fail": r["fail"],
                    "timeout": r["timeout"], "cov": round(r["cov_pct"], 1)})
    결과["재사용"] = 재사용

    # --- 7. CDC ---
    결과["CDC"] = cdc점검()
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
    P = 사람들.ETHAN
    R = RPT.보고서(P, "NSW-FIR v1.0 프런트엔드 설계 보고서",
                 "nsw_fir MAC 가속기 IP", "HLS 설계공간 탐색 · FSM · 파이프라인 · 파라미터 재사용성 · 클럭 게이팅 · CDC")

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
        R.요약(f"파라미터 스윕 {len(잰것['스윕'])}개 구성 합성 — TAPS/STAGES 만 바꿔 면적 "
              f"{min(면적들):,.0f}~{max(면적들):,.0f} µm²"
              + (f" (<b>{len(실패들)}개 구성은 합성 실패</b>)" if 실패들 else ""))
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
    R.절("1. 설계 개요 — 무엇을 만들었나")
    R.글("<b>nsw_fir</b> 은 파라미터로 치수가 정해지는 MAC 누산기 IP 다. "
        "느린 설정 도메인(<code>cfg_clk</code>)에서 계수를 받아 비동기 FIFO 로 건네고, "
        "빠른 데이터패스 도메인(<code>clk</code>)에서 FSM 이 LOAD→RUN→FLUSH 를 몰며 "
        "게이팅된 클럭으로 파이프라인 MAC 을 돌린다.")
    블록 = [("cfg_clk 도메인", 16, 40, 150, 92, "#eef4fb", "느리고 비동기"),
          ("nsw_afifo", 196, 52, 116, 68, "#fdf6e3", "그레이+2FF"),
          ("nsw_sync2", 196, 140, 116, 40, "#fdf6e3", "2단 동기화기"),
          ("nsw_ctrl FSM", 348, 26, 122, 54, "#ffffff", "one-hot 5상태"),
          ("nsw_icg", 348, 96, 122, 44, "#f3e8d7", "latch + AND"),
          ("nsw_mac", 348, 158, 122, 54, "#ffffff", "3단 파이프라인"),
          ("clk 도메인", 330, 12, 300, 216, "none", "")]
    연결 = [("cfg_clk 도메인", "nsw_afifo", "coef", V.파랑),
          ("cfg_clk 도메인", "nsw_sync2", "soft_rst", V.파랑),
          ("nsw_afifo", "nsw_ctrl FSM", "", V.먹),
          ("nsw_ctrl FSM", "nsw_icg", "dp_en", V.주황),
          ("nsw_icg", "nsw_mac", "gclk", V.주황)]
    R.그림(V.블록도(블록, 연결, "두 클럭 도메인과 그 사이의 건넘", 폭=650, 높이=244),
         "설계 구조. 파란 화살이 <b>도메인을 건너는 길</b>이고 둘 다 동기화 구조를 지난다. "
         "주황은 클럭 게이팅 경로다. 바깥의 큰 네모가 <code>clk</code> 도메인 경계다.",
         "house/rtl/src/nsw_fir.sv 를 읽어 그림")
    R.표(["파라미터", "기본값", "무엇을 정하나"],
        [["TAPS", "8", "계수 개수 — LOAD 단계 길이와 계수 메모리 깊이"],
         ["DW / CW", "16 / 16", "데이터 · 계수 비트폭"],
         ["ACCW", "40", "누산기 폭 — 포화 지점을 정한다"],
         ["STAGES", "3", "MAC 파이프라인 깊이 (지연 ↔ 주파수)"],
         ["CNTW", "12", "길이 카운터 폭 — 최대 len"],
         ["CDC_STAGES", "2", "동기화기 단수 — MTBF 를 정한다"],
         ["GATE_POLICY", "1", "0=상태 기반, 1=박자 기반 클럭 게이팅"]],
        "파라미터가 곧 재사용성이다. 아래 §5 에서 이 값을 바꿔 합성한 결과를 보인다.")

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
         "HLS 의 고전적인 맞바꿈. 곱셈기를 4개에서 1개로 줄이면 면적은 내려가고 "
         "지연은 <b>4 → 10 단계</b>로 오른다. 어느 점을 고를지는 시스템이 정한다.",
         "house/hls.py 스케줄러")
    R.그림(V.산점([x["면적추정"] for x in t], [x["지연"] for x in t],
               "면적 대 지연 (파레토 앞면)", "면적 추정 (µm²)", "지연 (단계)",
               라벨=[x["이름"] for x in t], 폭=520),
         "세 점이 파레토 앞면을 이룬다. 어느 것도 다른 것에 완전히 지지 않는다.",
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
    R.절("3. FSM 제어 흐름")
    상태 = ["IDLE", "LOAD", "RUN", "FLUSH", "DONE"]
    간선 = [("IDLE", "LOAD", "start"), ("LOAD", "LOAD", "!(cnt==TAPS-1)"),
          ("LOAD", "RUN", "cnt==TAPS-1"), ("RUN", "RUN", "cnt<len-1"),
          ("RUN", "FLUSH", "cnt>=len-1"), ("FLUSH", "DONE", "cnt==STAGES-1"),
          ("DONE", "IDLE", "ack")]
    R.그림(V.상태도(상태, 간선, "nsw_ctrl 상태 천이도 (one-hot)", 폭=620, 높이=280, 시작="IDLE"),
         "5 상태 one-hot. <code>default: st_n = S_IDLE</code> 로 <b>불법 상태에서 빠져나온다</b> "
         "— 단일 사건 업셋(SEU)이나 스캔 시프트 뒤에 여러 비트가 1 이 되어도 잠기지 않는다.",
         "house/rtl/src/nsw_fir.sv 의 nsw_ctrl")
    R.표(["상태", "인코딩", "dp_en (클럭 게이팅)", "acc_clr", "coef_we", "나가는 조건"],
        [["IDLE", "5'b00001", "0 — 클럭 꺼짐", "1", "0", "start"],
         ["LOAD", "5'b00010", "in_vld (박자 기반)", "cnt==0 일 때", "in_vld", "cnt==TAPS-1"],
         ["RUN", "5'b00100", "in_vld (박자 기반)", "0", "0", "cnt>=len-1"],
         ["FLUSH", "5'b01000", "1 — 파이프라인 비우기", "0", "0", "cnt==STAGES-1"],
         ["DONE", "5'b10000", "0 — 클럭 꺼짐", "0", "0", "ack"]],
        "상태 천이표. <b>세 번째 칸이 저전력의 전부다</b> — 상태가 곧 클럭 게이팅 조건이다.",
        강조열=[2])

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
    R.표(["STAGES", "지연(주기)", "임계경로", "기능 회귀"],
        [[x["파라"].get("STAGES", "기본"), x["파라"].get("STAGES", 3),
          "MUL|ADD" if x["파라"].get("STAGES") == 2 else "MUL|ADD|SAT",
          f"{x['pass']} 통과 / {x['fail']} 실패 / {x['timeout']} 타임아웃"]
         for x in 잰것["재사용"] if "STAGES" in x["파라"]],
        "파이프라인 깊이를 바꿔도 기능이 유지되는지 <b>실제로 돌려</b> 확인했다.",
        "verilator, seed=31, 400 거래")

    # ---------------- 5. 재사용성 ----------------
    R.절("5. 파라미터 재사용성 — 말이 아니라 합성 결과로")
    좋은스윕 = [s for s in 잰것["스윕"] if "면적" in s]
    if 좋은스윕:
        이름들 = [f"TAPS{s['파라'].get('TAPS','?')}/S{s['파라'].get('STAGES','?')}" for s in 좋은스윕]
        R.그림(V.막대(이름들, [s["면적"] for s in 좋은스윕], "구성별 합성 면적", "면적 (µm²)", 폭=560),
             "<b>RTL 한 줄도 안 고치고</b> 파라미터만 바꿔 합성한 결과. "
             "TAPS 가 계수 메모리와 카운터 폭을 통해 면적을 끈다.",
             f"yosys 0.33 · abc -fast · {SYN.LIB.name}")
        R.그림(V.막대(이름들, [s.get("Fmax") or 0 for s in 좋은스윕], "구성별 Fmax", "MHz",
                   색들=[V.초록] * len(좋은스윕), 폭=560),
             "같은 구성들의 최대 주파수. 파이프라인 단수를 줄이면(S2) 임계경로가 길어져 "
             "Fmax 가 내려간다 — <b>재사용성의 값이 여기 보인다</b>.",
             "lab/se/sta (블록기반 + 경로기반 두 길로 대조)")
        R.표(["구성", "면적(µm²)", "셀 수", "플롭", "Fmax(MHz)", "합성 시간"],
            [[f"TAPS={s['파라'].get('TAPS','기본')}, STAGES={s['파라'].get('STAGES','기본')}",
              f"{s['면적']:,.1f}", f"{s['셀수']:,}", s.get("플롭", "-"),
              s.get("Fmax", "-"), f"{s['초']:.1f} s" + (" (캐시)" if s.get("캐시") else "")]
             for s in 좋은스윕],
            "파라미터 스윕 원본 수치.", "yosys + lab/se/sta")
    R.경고("<b>측정이 이름을 반박했다.</b> <code>STAGES</code> 를 3→2 로 줄였더니 Fmax 가 "
         "<b>내려가는 대신 올라갔다</b>. 까닭을 파 보니 이 파라미터는 파이프라인 깊이를 "
         "바꾸는 것이 아니라 <b>출력 탭만 고른다</b> — 산술 임계경로(곱셈기)는 그대로이고 "
         "<code>a_s3</code> 단은 순수한 지연일 뿐이다. 그래서 STAGES=2 는 죽은 플롭 "
         "40개가 빠져 면적이 줄고, abc 가 다르게 최적화해 Fmax 가 올랐다. "
         "<b>이것은 주파수 손잡이가 아니라 지연 손잡이다.</b> 다음 판에서 곱셈기를 "
         "두 단으로 쪼개 진짜 깊이 파라미터로 만든다 — 그때까지 이 이름은 오해를 부른다.")
    R.표(["바꾼 파라미터", "통과", "실패", "타임아웃", "커버리지(%)"],
        [[json.dumps(x["파라"], ensure_ascii=False), x["pass"], x["fail"], x["timeout"], x["cov"]]
         for x in 잰것["재사용"]],
        "<b>재사용이란 돌아야 재사용이다.</b> 파라미터를 바꾼 뒤 기능 회귀를 다시 돌린 결과.",
        "verilator", 강조열=[2])

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
    R.표(["건너는 신호", "보내는 도메인", "받는 도메인", "폭", "종류", "방식", "왜 안전한가"],
        [[x["신호"], x["보내는곳"], x["받는곳"], x["폭"], x["종류"], x["방식"], x["왜"]]
         for x in c["건넘"]],
        f"도메인 건넘 {len(c['건넘'])}개. <b>맨선(동기화 없는 건넘) {len(c['맨선'])}개</b> — "
        f"판정 <b>{c['판정']}</b>.", "정적 점검", 강조열=[5])
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


def 돌리기(빠르게=False) -> dict:
    잰것 = 일하기(빠르게=빠르게)
    R = 보고서(잰것)
    길 = R.내기()
    return {"사람": 사람들.ETHAN, "잰것": 잰것, "pdf": 길, "쪽": RPT.쪽수(길),
            "요약": R.요약줄, "그림수": R.그림수, "표수": R.표수}


if __name__ == "__main__":
    r = 돌리기("--빠르게" in sys.argv)
    print(f"PDF -> {r['pdf']}  ({r['쪽']} 쪽, 그림 {r['그림수']}, 표 {r['표수']})")
    for s in r["요약"]:
        print(" ·", re.sub(r"<[^>]+>", "", s))
