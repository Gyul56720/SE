# -*- coding: utf-8 -*-
"""house/sim -- verilator 를 부르는 한 곳.

다섯 사람이 다 시뮬레이션을 쓴다(RTL 은 게이팅 A/B, DV 는 회귀, DFT 는 스캔,
PD 는 토글률). 그래서 빌드와 실행을 여기 한 곳에 두고, **파라미터가 같으면 다시
빌드하지 않는다** -- 빌드가 3초, 실행이 0.09초라 캐시가 없으면 빌드가 곧 비용이다.

도구가 없으면 숨기지 않는다: `있나()` 가 무엇이 없는지 그대로 돌려준다.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent
저장소 = 뿌리.parent
RTL = 뿌리 / "rtl" / "src" / "nsw_fir.sv"
TB = 뿌리 / "dv" / "tb_nsw_fir.cpp"
빌드방 = Path(os.getenv("HOUSE_BUILD", "/tmp/nsw_build"))


def 있나() -> dict:
    """어떤 도구가 실제로 있나.  보고서 머리에 그대로 적는다."""
    def v(cmd, arg="--version"):
        p = shutil.which(cmd)
        if not p:
            return None
        try:
            out = subprocess.run([p, arg], capture_output=True, text=True, timeout=20)
            return (out.stdout + out.stderr).strip().splitlines()[0][:80]
        except Exception:                                    # noqa: BLE001
            return p
    return {
        "verilator": v("verilator"),
        "iverilog": v("iverilog", "-V"),
        "yosys": v("yosys", "-V"),
        "g++": v("g++", "--version"),
        # 상용 도구 -- 없는 것을 없다고 적는다
        "vcs": v("vcs"), "xrun": v("xrun"), "questa": v("vsim"),
        "design_compiler": v("dc_shell"), "primetime": v("pt_shell"),
        "opensta": v("sta"), "innovus": v("innovus"), "tessent": v("tessent"),
        "klayout": v("klayout"), "magic": v("magic"),
    }


def _서명(파라: dict, 추가: str = "") -> str:
    h = hashlib.sha1()
    h.update(json.dumps(파라, sort_keys=True).encode())
    h.update(RTL.read_bytes())
    h.update(TB.read_bytes())
    h.update(추가.encode())
    return h.hexdigest()[:12]


def 빌드(파라: dict | None = None, 추적=False) -> Path:
    """verilator 로 시뮬레이터를 짓고 실행 파일 경로를 돌려준다."""
    파라 = 파라 or {}
    키 = _서명(파라, "trace" if 추적 else "")
    방 = 빌드방 / 키
    실행 = 방 / "simv"
    if 실행.exists():
        return 실행
    방.mkdir(parents=True, exist_ok=True)
    cmd = ["verilator", "--cc", str(RTL), "--top-module", "nsw_fir",
           "--exe", str(TB), "--Mdir", str(방), "-o", "simv",
           "-CFLAGS", "-O2", "-Wno-fatal"]
    for k, v in 파라.items():
        cmd += [f"-G{k}={v}"]          # verilator 는 붙여 써야 한다 (-G NAME=V 는 파일로 읽는다)
    if 추적:
        cmd += ["--trace"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError("verilator 빌드 실패:\n" + (r.stderr or r.stdout)[-2000:])
    m = subprocess.run(["make", "-C", str(방), "-f", "Vnsw_fir.mk", "simv", "-s", "-j4"],
                       capture_output=True, text=True, timeout=600)
    if m.returncode != 0 or not 실행.exists():
        raise RuntimeError("C++ 빌드 실패:\n" + (m.stderr or m.stdout)[-2000:])
    return 실행


def 돌리기(파라: dict | None = None, **옵션) -> dict:
    """한 번 돌리고 JSON 을 돌려준다.  옵션: seed · txn · cap · cfg · trace · maxlen · vcd"""
    실행 = 빌드(파라, 추적=bool(옵션.get("vcd")))
    cmd = [str(실행)]
    for k in ("seed", "txn", "cap", "cfg", "trace", "maxlen", "dir"):
        if k in 옵션 and 옵션[k] is not None:
            cmd += [f"--{k}", str(옵션[k])]
    if 옵션.get("vcd"):
        cmd += ["--vcd", str(옵션["vcd"])]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=옵션.get("초", 900))
    걸린 = time.time() - t0
    줄 = [l for l in r.stdout.splitlines() if l.startswith("{")]
    if not 줄:
        raise RuntimeError(f"시뮬레이터가 JSON 을 안 냈다 (rc={r.returncode}):\n{r.stdout[-800:]}\n{r.stderr[-800:]}")
    d = json.loads(줄[-1])
    d["_초"] = round(걸린, 4)
    d["_파라"] = dict(파라 or {})
    d["_rc"] = r.returncode
    return d


def 회귀(파라: dict | None = None, 씨앗들=range(1, 21), **옵션) -> list:
    """여러 씨앗으로 돌린다.  회귀란 한 번이 아니라 여러 번이다."""
    out = []
    for s in 씨앗들:
        out.append(돌리기(파라, seed=s, **옵션))
    return out


def lint(파일=None) -> dict:
    """verilator lint.  경고를 종류별로 센다 -- '깨끗하다' 를 수로 말한다."""
    파일 = 파일 or RTL
    r = subprocess.run(["verilator", "--lint-only", "-Wall", str(파일), "--top-module", "nsw_fir"],
                       capture_output=True, text=True, timeout=120)
    글 = r.stdout + r.stderr
    종류 = {}
    for line in 글.splitlines():
        if line.startswith("%Warning-") or line.startswith("%Error"):
            이름 = line.split(":")[0].replace("%Warning-", "").replace("%Error-", "ERR:")
            종류[이름] = 종류.get(이름, 0) + 1
    return {"rc": r.returncode, "종류": 종류, "전체": sum(종류.values()), "글": 글[-3000:]}


def iverilog_확인(파일=None) -> dict:
    """두 번째 도구로 같은 RTL 을 엘라보레이트한다.  한 도구만 믿지 않는다."""
    파일 = 파일 or RTL
    out = Path("/tmp/nsw_elab.vvp")
    r = subprocess.run(["iverilog", "-g2012", "-o", str(out), "-s", "nsw_fir", str(파일)],
                       capture_output=True, text=True, timeout=120)
    return {"rc": r.returncode, "글": (r.stdout + r.stderr)[-1500:], "됐나": r.returncode == 0}
