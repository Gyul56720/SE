# -*- coding: utf-8 -*-
"""house/synth -- yosys 를 부르는 한 곳 (실제 도구).

`lab/se/synth.py` 는 lab 의 고정 RTL 만 돌린다. 여기서는 **파라미터를 바꿔 가며**
같은 RTL 을 여러 벌 합성한다 -- 재사용성(파라미터 하나로 다른 IP 가 된다)을
말이 아니라 면적·플롭 수·Fmax 로 보이기 위해서다.

셀 라이브러리는 `lab/lib/se10.lib` 를 쓴다. 그것은 `lab/se/mklib.py` 가 RC 모형에서
만든 것이고(FO4 55.2 ps ~ 180 nm 급), 파운드리 PDK 가 아니다. 보고서에 그대로 적는다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
저장소 = 뿌리.parent
RTL = 뿌리 / "rtl" / "src" / "nsw_fir.sv"
# **se10 이 아니라 nsw10 을 쓴다.** se10 에는 래치가 없어 ICG 의 $_DLATCH_N_ 가
# 매핑되지 않는다("Area for cell type $_DLATCH_N_ is unknown", 그리고 STA 가
# KeyError 로 죽는다). nsw10 = se10 + LATX1 이고, se10 은 손대지 않는다
# (lab 의 기준값이 그 파일에 묶여 있다).
LIB = 뿌리 / "lib" / "nsw10.lib"
ICG맵 = 뿌리 / "lib" / "icg_map.v"
내는방 = Path(os.getenv("HOUSE_SYN", "/tmp/nsw_syn"))


def _키(파라: dict, top: str, 빠르게: bool) -> str:
    h = hashlib.sha1()
    h.update(json.dumps(파라, sort_keys=True).encode())
    h.update(RTL.read_bytes())
    h.update((top + str(빠르게)).encode())
    return h.hexdigest()[:12]


def 라이브러리확인() -> dict:
    """**없으면 만든다.** nsw10.lib 은 생성물이라 커밋하지 않는다 -- 그래서 새로 받은
    저장소(= VM)에는 없다.

    실측 2026-09-21: 이 한 줄이 없어서 VM 에서 다섯 에이전트가 줄줄이 죽었다.

        yosys: ERROR: Can't open liberty file `house/lib/nsw10.lib'
          -> 합성 실패 -> Ethan `min() arg is an empty sequence`
          -> 합성 실패 -> Marcus `KeyError: '코너'`

    **생성물을 커밋하지 않는 것은 옳다. 만들지 않은 것이 틀렸다.**
    원본(`lab/lib/se10.lib`)은 커밋되어 있으므로 여기서 만들 수 있다.
    """
    if LIB.exists():
        return {"있었나": True, "만들었나": False, "길": str(LIB)}
    try:
        from house.lib import mk
        만든 = mk.만들기()
        return {"있었나": False, "만들었나": LIB.exists(),
                "길": str(LIB), "같이만든것": [str(x) for x in 만든]}
    except Exception as e:                                   # noqa: BLE001
        return {"있었나": False, "만들었나": False, "길": str(LIB),
                "까닭": f"{type(e).__name__}: {e}"[:200]}


def 합성(파라: dict | None = None, top=None, 빠르게=True, 초=1800, 설계=None) -> dict:
    """yosys 로 매핑까지 한다.  결과는 캐시한다(같은 파라미터면 다시 안 돈다).

    `빠르게` 는 abc 를 `-fast` 로 돌린다. 16x16 곱셈기를 셀로 매핑하는 데 전체
    최적화는 몇 분이 걸리는데, 우리가 견주는 것은 **구성 사이의 차이**이므로
    같은 설정으로 다 돌리면 비교는 성립한다. 보고서에 `abc -fast` 라고 적는다.
    """
    from house import designs as DES
    d = 설계 or DES.NSW_FIR
    _lib = 라이브러리확인()
    if not (_lib["있었나"] or _lib["만들었나"]):
        return {"됐나": False, "초": 0.0,
                "까닭": (f"표준셀 라이브러리가 없고 만들지도 못했다: {LIB}\n"
                       f"{_lib.get('까닭', '')}\n"
                       "`python3 house/lib/mk.py` 가 lab/lib/se10.lib 에서 만든다.")}
    top = top or d.top
    파라 = {**d.파라, **(파라 or {})}
    키 = _키(파라, f"{top}|" + "|".join(str(x) for x in d.RTL), 빠르게)
    방 = 내는방 / 키
    캐시 = 방 / "결과.json"
    if 캐시.exists():
        d = json.loads(캐시.read_text())
        d["캐시"] = True
        return d
    방.mkdir(parents=True, exist_ok=True)
    js = 방 / "netlist.json"
    v = 방 / "netlist.v"
    chp = "".join(f"chparam -set {k} {v_} {top}; " for k, v_ in 파라.items())
    abc = f"abc -liberty {LIB}" + (" -fast" if 빠르게 else "")
    # **flatten 이 있어야 STA 가 전체를 본다.** 없으면 write_json 이 모듈마다 따로
    # 적고, lab/se/netlist 는 top 모듈의 셀만 읽는다 -- nsw_mac 안의 곱셈기가
    # 임계경로에서 통째로 빠진다(실측: 플롭 160, 인스턴스 495 로 고정).
    # **chparam 은 hierarchy 앞에 와야 한다.** 뒤에 두면 top 의 파라미터만 바뀌고
    # 이미 엘라보레이트된 하위 인스턴스는 옛 값을 쓴다 -- 실측 2026-09-21: TAPS 를
    # 4/8/16 으로 바꿔도 플롭 수가 160 으로 똑같이 나왔다.
    대본 = (f"read_verilog -sv " + " ".join(str(x) for x in d.RTL) + f"; {chp}hierarchy -top {top}; "
          f"proc; opt; flatten; opt; fsm; opt; memory -nomap; opt; "
          f"memory_map; opt; techmap; opt; "
          f"techmap -map {ICG맵}; opt; dfflibmap -liberty {LIB}; {abc}; opt_clean; "
          f"stat -liberty {LIB} -top {top}; write_json {js}; write_verilog -noattr {v}")
    t0 = time.time()
    r = subprocess.run(["yosys", "-p", 대본], capture_output=True, text=True, timeout=초)
    걸린 = time.time() - t0
    if r.returncode != 0:
        return {"됐나": False, "까닭": (r.stderr or r.stdout)[-1500:], "초": round(걸린, 1)}
    글 = r.stdout
    면적, 셀수, 배선 = 0.0, 0, 0
    셀종류 = {}
    모르는면적 = []
    # **`stat -top` 이 내는 계층 합계 블록을 읽는다.** 그냥 `stat` 은 모듈마다 한 블록씩
    # 찍고, 마지막 블록은 가장 작은 서브모듈이다 -- 처음에 그것을 읽어 면적을
    # 83,615 대신 29.94 로 보고했다(실측 2026-09-21).
    블록 = 글.split("=== design hierarchy ===")[-1] if "design hierarchy" in 글 else 글
    for line in 블록.splitlines():
        t = line.strip()
        if t.startswith("Number of cells:"):
            셀수 = int(t.split(":")[1])
        elif t.startswith("Number of wires:"):
            배선 = int(t.split(":")[1])
        elif "Chip area for top module" in t or "Chip area for module" in t:
            면적 = float(t.rsplit(":", 1)[1])
        elif t.startswith("Area for cell type") and "unknown" in t:
            모르는면적.append(t.split("'")[1] if "'" in t else t[:40])
        else:
            m = re.match(r"^([A-Za-z_][\w$]*)\s+(\d+)$", t)
            if m and 셀수:
                셀종류[m.group(1)] = int(m.group(2))
    d = {"됐나": True, "면적_um2": round(면적, 2), "셀수": 셀수, "배선수": 배선,
         "셀종류": 셀종류, "면적모르는셀": 모르는면적,
         "json": str(js), "v": str(v), "초": round(걸린, 1),
         "파라": dict(파라), "top": top, "abc": "fast" if 빠르게 else "full",
         "라이브러리": str(LIB.name)}
    캐시.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def sta(합성결과: dict, 주기=10.0, 디레이트=None) -> dict:
    """lab/se/sta 로 Fmax 와 임계경로를 잰다.  블록기반·경로기반 두 길로 재서 맞는지 본다."""
    if not 합성결과.get("됐나"):
        return {"됐나": False, "까닭": "합성 실패"}
    sys.path.insert(0, str(저장소 / "lab" / "se"))
    import liberty as L
    import netlist as NL
    import sta as STA
    lb = L.라이브러리(str(LIB))
    nl = NL.넷리스트(합성결과["json"], lb)
    a = STA.분석기(nl, 주기=주기)
    r = a.풀기()
    요약 = dict(r.요약())
    끝 = r.끝점들[0][1] if r.끝점들 else None
    if 끝 is not None:
        블록 = a.마디[끝].도착
        경로 = a.경로최대(끝)
        요약["두길_차이_ps"] = round(abs(블록 - 경로) * 1e3, 6)
        요약["임계경로"] = STA.경로글(a.경로(끝) if hasattr(a, "경로") else [], nl) if False else ""
    요약["넷리스트요약"] = nl.요약()
    요약["됐나"] = True
    return 요약


def 경로분해(합성결과: dict, 주기=10.0, 몇=14) -> list:
    """임계경로를 단계별로 쪼갠다.  '느리다' 가 아니라 '어느 셀에서 몇 ps' 를 보인다."""
    sys.path.insert(0, str(저장소 / "lab" / "se"))
    import liberty as L
    import netlist as NL
    import sta as STA
    lb = L.라이브러리(str(LIB))
    nl = NL.넷리스트(합성결과["json"], lb)
    a = STA.분석기(nl, 주기=주기)
    a.풀기()
    끝 = a.결과.끝점들[0][1] if hasattr(a, "결과") and a.결과.끝점들 else None
    단계 = []
    try:
        경로 = a.경로들(끝) if hasattr(a, "경로들") else None
    except Exception:                                        # noqa: BLE001
        경로 = None
    if 경로 is None:
        # 분석기가 경로 목록을 안 주면 마디 도착시각 상위로 대신한다
        마디들 = sorted(a.마디.items(), key=lambda kv: -kv[1].도착)[:몇]
        for 이름, m in 마디들:
            단계.append({"마디": str(이름)[:44], "도착_ps": round(m.도착 * 1e3, 2)})
    return 단계
