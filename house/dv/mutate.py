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

RTL = 집 / "rtl" / "src" / "nsw_fir.sv"
TB = 집 / "dv" / "tb_nsw_fir.cpp"

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


def 적용(변이, 방: Path) -> "Path | None":
    """변이를 걸어 RTL 사본을 만든다.  원문을 못 찾으면 None(조용히 넘어가지 않는다)."""
    글 = RTL.read_text(encoding="utf-8")
    _id, _설명, 원, 새, _잡, _갈래 = 변이
    if 원 not in 글:
        return None
    방.mkdir(parents=True, exist_ok=True)
    길 = 방 / "nsw_fir.sv"
    길.write_text(글.replace(원, 새, 1), encoding="utf-8")
    return 길


def 한변이(변이, txn=400, 씨앗들=(101, 102, 103), 초=600, 지시=20, maxlen=2000) -> dict:
    """변이를 걸고 회귀를 돌린다.  '빨개졌나' 가 답이다."""
    id_, 설명, _원, _새, 잡, 갈래 = 변이
    t0 = time.time()
    방 = Path(tempfile.mkdtemp(prefix=f"mut_{id_}_"))
    try:
        길 = 적용(변이, 방)
        if 길 is None:
            return {"id": id_, "설명": 설명, "적용": False, "잡혔나": None,
                    "까닭": "원문을 못 찾았다 — RTL 이 바뀌었다. 변이 표를 고쳐라",
                    "잡아야": 잡, "갈래": 갈래, "초": 0}
        빌드 = 방 / "build"
        r = subprocess.run(
            ["verilator", "--cc", str(길), "--top-module", "nsw_fir",
             "--exe", str(TB), "--Mdir", str(빌드), "-o", "simv",
             "-CFLAGS", "-O2", "-Wno-fatal", "-Wno-LATCH", "-Wno-UNOPTFLAT",
             "-Wno-WIDTHEXPAND", "-Wno-CASEINCOMPLETE"],
            capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return {"id": id_, "설명": 설명, "적용": True, "잡혔나": True,
                    "잡은것": "verilator 빌드 실패 (정적으로 잡힘)",
                    "잡아야": 잡, "갈래": 갈래, "초": round(time.time() - t0, 1)}
        m = subprocess.run(["make", "-C", str(빌드), "-f", "Vnsw_fir.mk", "simv", "-s", "-j4"],
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


def 한바퀴(txn=400, 씨앗들=(101, 102, 103), 지시=20) -> list:
    return [한변이(v, txn=txn, 씨앗들=씨앗들, 지시=지시) for v in 변이들]


if __name__ == "__main__":
    for r in 한바퀴():
        표 = "잡힘" if r["잡혔나"] else ("못잡음" if r["잡혔나"] is False else "적용실패")
        print(f"{r['id']:<13} {r.get('갈래','?'):<5} {표:<7} "
              f"{r.get('잡은것', r.get('까닭',''))[:52]}  ({r['초']}s)")
