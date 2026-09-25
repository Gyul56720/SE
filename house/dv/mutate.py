# -*- coding: utf-8 -*-
"""house/dv/mutate -- 검사기가 정말로 무는지 증명한다.

**왜 필요한가.** 회귀가 초록이라는 것은 두 가지 중 하나다: 설계가 옳거나, 검사기가
아무것도 안 보거나. 보통의 회귀는 그 둘을 못 가른다 -- 실패 경로를 한 번도 안 타기
때문이다. 그래서 **설계를 일부러 망가뜨리고 회귀가 빨개지는지 본다.**

각 변이는 (이름, 설명, 무엇이 잡아야 하나) 를 가진다. 아무것도 안 잡는 변이는
검사의 구멍이고, 그 자리가 정확히 짚인다.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
집 = 뿌리.parent
저장소 = 집.parent
sys.path.insert(0, str(저장소))

RTL = 집 / "rtl" / "src" / "nsw_fir.sv"     # 기본값(FIR). **설계를 주면 그것을 쓴다**
TB = 집 / "dv" / "tb_nsw_fir.cpp"


def _설계(설계=None):
    """설계를 안 주면 FIR 로 떨어진다 -- 옛 부름과 호환되게."""
    if 설계 is not None:
        return 설계
    from house import designs as DES
    return DES.NSW_FIR

# 변이 하나 = (id, 설명, 원문, 바꿀것, 잡아야 하는 검사, 갈래)
#
# **갈래를 나누는 까닭.** 안 잡힌 변이가 다 검사의 구멍인 것은 아니다. 셋을 갈라야
# 보고서가 쓸모 있다:
#   "기능"   -- 기능 시뮬로 잡혀야 한다. 안 잡히면 **검사의 구멍**이다
#   "구조"   -- 2-state 시뮬레이터가 원리상 못 본다(준안정·글리치·표본 위험).
#               정적 CDC 점검이나 이벤트 기반 시뮬이 잡아야 한다
#   "무해"   -- 변이가 사실 버그가 아니다. 설계가 여유를 갖고 있다는 뜻이고,
#               그 여유가 얼마인지를 알려 준다
변이들 = [
    ("m1_flush",
     "FLUSH 를 두 주기 줄인다 — 파이프라인이 안 비워진 채 DONE",
     "S_FLUSH: if (cnt == STAGES[CNTW-1:0] - 1)",
     "S_FLUSH: if (cnt == STAGES[CNTW-1:0] - 3)",
     "스코어보드 값 비교", "기능"),
    ("m1b_flush1",
     "FLUSH 를 한 주기만 줄인다 — 설계에 여유가 있는지 재는 변이",
     "S_FLUSH: if (cnt == STAGES[CNTW-1:0] - 1)",
     "S_FLUSH: if (cnt == STAGES[CNTW-1:0] - 2)",
     "안 잡히면 FLUSH 가 한 주기 길다는 뜻(무해)", "무해"),
    ("m2_push",
     "FLUSH 중에도 곱을 계속 밀어 넣는다 — 누산기가 더럽혀진다",
     "                p_s1 <= push ? prod : '0;",
     "                p_s1 <= prod;",
     "스코어보드 값 비교", "기능"),
    ("m3_tapstuck",
     "계수 포인터를 0 에 묶는다 — 늘 coef[0] 만 쓴다",
     "        else if (run_beat) tap_ptr <= (tap_ptr == TAPS[$clog2(TAPS)-1:0] - 1) ? '0 : tap_ptr + 1'b1;",
     "        else if (run_beat) tap_ptr <= '0;",
     "스코어보드 값 비교", "기능"),
    ("m3b_tapwrap",
     "계수 포인터가 TAPS 에서 안 감긴다",
     "        else if (run_beat) tap_ptr <= (tap_ptr == TAPS[$clog2(TAPS)-1:0] - 1) ? '0 : tap_ptr + 1'b1;",
     "        else if (run_beat) tap_ptr <= tap_ptr + 1'b1;",
     "TAPS 가 2의 거듭제곱이면 포인터 폭이 저절로 감긴다(무해)", "무해"),
    ("m4_sat",
     "포화를 없앤다 — 넘치면 감긴다",
     "    wire signed [ACCW-1:0] sum = ovf ? (raw[ACCW] ? SAT_LO : SAT_HI) : raw[ACCW-1:0];",
     "    wire signed [ACCW-1:0] sum = raw[ACCW-1:0];",
     "스코어보드 값 비교 — **지시 시험이 있어야만** 잡힌다", "기능"),
    ("m5_sync1",
     "CDC 동기화기를 1단으로 줄인다 — 준안정 노출",
     "    parameter integer CDC_STAGES = 2,",
     "    parameter integer CDC_STAGES = 1,",
     "정적 CDC 점검 (2-state 시뮬은 준안정을 못 본다)", "구조"),
    ("m6_done",
     "done 을 두 주기 낸다 — 프로토콜 위반",
     "    assign done    = st[4];",
     "    assign done    = st[4] | st[3];",
     "프로토콜 검사 (거래당 done 정확히 1)", "기능"),
    ("m7_gray",
     "FIFO 포인터를 그레이 대신 이진으로 건넨다 — CDC 고전 버그",
     "        else         begin wbin <= wbin_nxt; wgray <= wgray_nxt; wfull_r <= full_nxt; end",
     "        else         begin wbin <= wbin_nxt; wgray <= wbin_nxt; wfull_r <= full_nxt; end",
     "정적 CDC 점검 (주기 정확 시뮬은 표본 위험을 못 만든다)", "구조"),
    ("m8_icg",
     "ICG 의 래치를 없앤다 — 글리치 클럭",
     "    always @(*) if (!clk) en_lat = en | test_en;   // clk 낮을 때만 투명 (의도한 래치)",
     "    always @(*) en_lat = en | test_en;   // 래치 제거 (변이)",
     "lint / 이벤트 기반 시뮬 (verilator 는 글리치를 못 본다)", "구조"),
]


def 적용(변이, 방: Path, 설계=None) -> "Path | None":
    """변이를 걸어 RTL 사본을 만든다.  원문을 못 찾으면 None(조용히 넘어가지 않는다).

    **회로 이름을 안 박는다.** 예전에는 `nsw_fir.sv` 로 썼다 -- 다른 회로를 넘겨도
    파일 이름이 FIR 이라 top 을 못 찾았다.
    """
    d = _설계(설계)
    src = Path(d.RTL[0]) if getattr(d, "RTL", None) else RTL
    글 = src.read_text(encoding="utf-8")
    _id, _설명, 원, 새, _잡, _갈래 = 변이
    if 원 not in 글:
        return None
    방.mkdir(parents=True, exist_ok=True)
    길 = 방 / f"{d.top}.sv"
    길.write_text(글.replace(원, 새, 1), encoding="utf-8")
    return 길


def 한변이(변이, txn=400, 씨앗들=(101, 102, 103), 초=600, 지시=20, maxlen=2000, 설계=None) -> dict:
    """변이를 걸고 회귀를 돌린다.  '빨개졌나' 가 답이다."""
    id_, 설명, _원, _새, 잡, 갈래 = 변이
    d = _설계(설계)
    t0 = time.time()
    방 = Path(tempfile.mkdtemp(prefix=f"mut_{id_}_"))
    try:
        길 = 적용(변이, 방, 설계=d)
        if 길 is None:
            return {"id": id_, "설명": 설명, "적용": False, "잡혔나": None,
                    "까닭": "원문을 못 찾았다 — RTL 이 바뀌었다. 변이 표를 고쳐라",
                    "잡아야": 잡, "갈래": 갈래, "초": 0}
        빌드 = 방 / "build"
        r = subprocess.run(
            ["verilator", "--cc", str(길), "--top-module", d.top,
             "--exe", str(d.TB or TB), "--Mdir", str(빌드), "-o", "simv"]
            + [f"-G{k}={v}" for k, v in (getattr(d, "파라", None) or {}).items()]
            + ["-CFLAGS", "-O2", "-Wno-fatal", "-Wno-LATCH", "-Wno-UNOPTFLAT",
               "-Wno-WIDTHEXPAND", "-Wno-CASEINCOMPLETE"],
            capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return {"id": id_, "설명": 설명, "적용": True, "잡혔나": True,
                    "잡은것": "verilator 빌드 실패 (정적으로 잡힘)",
                    "잡아야": 잡, "갈래": 갈래, "초": round(time.time() - t0, 1)}
        m = subprocess.run(["make", "-C", str(빌드), "-f", f"V{d.top}.mk", "simv", "-s", "-j4"],
                           capture_output=True, text=True, timeout=600)
        if m.returncode != 0:
            return {"id": id_, "설명": 설명, "적용": True, "잡혔나": True,
                    "잡은것": "C++ 빌드 실패 (정적으로 잡힘)",
                    "잡아야": 잡, "갈래": 갈래, "초": round(time.time() - t0, 1)}
        합 = {"fail": 0, "timeout": 0, "proto_err": 0, "pass": 0}
        for s in 씨앗들:
            p = subprocess.run([str(빌드 / "simv"), "--seed", str(s), "--txn", str(txn),
                                "--dir", str(지시), "--maxlen", str(maxlen), "--cap", "900000"],
                               capture_output=True, text=True, timeout=초)
            줄 = [l for l in p.stdout.splitlines() if l.startswith("{")]
            if not 줄:
                합["timeout"] += txn
                continue
            import json as _j
            d = _j.loads(줄[-1])
            for k in 합:
                합[k] += d.get(k, 0)
        잡혔 = (합["fail"] + 합["timeout"] + 합["proto_err"]) > 0
        잡은 = []
        if 합["fail"]:
            잡은.append(f"스코어보드 {합['fail']}건")
        if 합["proto_err"]:
            잡은.append(f"프로토콜(done 수) {합['proto_err']}건")
        if 합["timeout"]:
            잡은.append(f"타임아웃 {합['timeout']}건")
        return {"id": id_, "설명": 설명, "적용": True, "잡혔나": 잡혔,
                "잡은것": " · ".join(잡은) or "아무 검사도 안 물었다",
                "잡아야": 잡, "갈래": 갈래, "통계": 합, "초": round(time.time() - t0, 1)}
    finally:
        shutil.rmtree(방, ignore_errors=True)


# 회로마다 변이가 다르다 -- 변이는 **그 RTL 의 글자**를 바꾸는 것이기 때문이다.
# 목록이 없는 회로에 FIR 의 변이를 걸면 원문을 못 찾아 전부 '적용실패' 가 나고,
# 그것이 '검사가 약하다' 로 읽힌다. **그래서 없는 것은 없다고 말한다.**
# --- AIM2 역 Mersenne S-box (KpqC AIMer) --------------------------------
#
# **모드마다 쓰이는 모듈이 다르다.** MODE=0(이진법)은 제곱기를 쓰고 Frobenius 를 안
# 쓰며, MODE=1(가수)은 그 반대다. 그래서 목록을 갈라 놓는다 -- 안 쓰는 모듈에 변이를
# 걸면 안 잡히는 것이 당연한데 그것이 '검사의 구멍' 으로 잘못 읽힌다.
#
# **생성 파일(nsw_aim.sv)은 gf128.vh 를 모듈마다 한 벌씩 품는다.** `적용()` 이 첫
# 판만 바꾸므로, 여러 벌에 같은 글이 있는 자리(clmul·reduce 본문)는 **첫 벌이 어느
# 모듈의 것인지**가 결과를 가른다. 그래서 여기서는 **모듈에 하나뿐인 글**을 노린다.

_AIM_공통 = [
    ("a_mul_aa",
     "곱셈기가 b 대신 a 를 곱한다 — 제곱이 되어 버린다",
     "assign z = gf128_reduce(gf128_clmul(a, b));",
     "assign z = gf128_reduce(gf128_clmul(a, a));",
     "레퍼런스 벡터 비교", "기능"),
]

_AIM_가수 = _AIM_공통 + [
    ("a_frob_e49",
     "Frobenius 지수 49 를 50 으로 — 가수의 첫 걸음이 틀린다",
     "wire [127:0] u0 = frob_pow(a,  49);",
     "wire [127:0] u0 = frob_pow(a,  50);",
     "레퍼런스 벡터 비교", "기능"),
    ("a_step_add",
     "덧셈 걸음 하나를 배가 걸음으로 — 가수가 d 에 안 닿는다",
     "2: step_rom = {1'b1, 7'd68};",
     "2: step_rom = {1'b0, 7'd68};",
     "레퍼런스 벡터 비교", "기능"),
    ("a_sel_stuck",
     "Frobenius 먹스를 0 에 묶는다 — 모든 걸음이 같은 지수를 쓴다",
     ".sel(i[2:0])",
     ".sel(3'd0)",
     "레퍼런스 벡터 비교", "기능"),
    ("a_early_done",
     "한 걸음 일찍 끝낸다 — 마지막 곱이 빠진다",
     "if (i == NSTEP - 1) begin",
     "if (i == NSTEP - 2) begin",
     "레퍼런스 벡터 비교", "기능"),
]

_AIM_이진 = _AIM_공통 + [
    ("a_bin_always",
     "지수 비트를 안 보고 늘 곱한다 — e~ 가 전부 1 인 꼴이 된다",
     "if (ETILDE[i[6:0]]) acc <= mul_o;",
     "acc <= mul_o;",
     "레퍼런스 벡터 비교", "기능"),
    ("a_bin_early",
     "127 번째 걸음에서 끝낸다 — 마지막 제곱·곱이 빠진다",
     "if (i == 8'd127) begin",
     "if (i == 8'd126) begin",
     "레퍼런스 벡터 비교", "기능"),
    ("a_reduce_poly",
     "축약 다항식의 x^7 항을 x^6 으로 — 체가 달라진다 (첫 벌 = gf128_sqr)",
     "t   = ({7'd0, hi} << 7)",
     "t   = ({7'd0, hi} << 6)",
     "레퍼런스 벡터 비교", "기능"),
]

회로별변이 = {"fir": 변이들, "aim_chain": _AIM_가수, "aim_bin": _AIM_이진}


def 한바퀴(txn=400, 씨앗들=(101, 102, 103), 지시=20, 설계=None) -> list:
    d = _설계(설계)
    목록 = 회로별변이.get(d.키)
    if not 목록:
        return [{"id": "(없음)", "설명": f"{d.키} 회로의 변이 목록이 없다",
                 "적용": False, "잡혔나": None,
                 "까닭": ("이 회로에 걸 변이를 아직 안 적었다. **FIR 의 변이를 대신 돌리지 "
                        "않는다** -- 원문을 못 찾아 전부 적용실패가 나고 그것이 '검사가 "
                        "약하다' 로 잘못 읽힌다. house/dv/mutate.py 의 `회로별변이` 에 "
                        f"'{d.키}' 를 더해라."),
                 "잡아야": "-", "갈래": "-", "초": 0}]
    return [한변이(v, txn=txn, 씨앗들=씨앗들, 지시=지시, 설계=d) for v in 목록]


if __name__ == "__main__":
    for r in 한바퀴():
        표 = "잡힘" if r["잡혔나"] else ("못잡음" if r["잡혔나"] is False else "적용실패")
        print(f"{r['id']:<13} {r.get('갈래','?'):<5} {표:<7} "
              f"{r.get('잡은것', r.get('까닭',''))[:52]}  ({r['초']}s)")
