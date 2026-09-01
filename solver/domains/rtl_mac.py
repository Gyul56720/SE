"""
RTL 도메인 -- INT8 MAC(곱셈-누산) 유닛. NPU/추론 가속기의 최소 연산 프리미티브.

왜 이 블록인가: "토큰/초, INT4·INT8 양자화 가속, 초저지연"이 모두 얹히는 밑바닥이 내적
누산기다. systolic array 의 한 칸(PE)이 바로 이것이고, 양자화 GEMM 의 핵심이 이것이다.
NPU 전체보다 이 한 블록부터가 현실적이고, 오라클이 가장 깨끗하다.

오라클이 위조 불가인 이유 (텐서 rank 와 같은 원리): 정답이 '수학으로 정의'된다. INT8×INT8 을
누산한 INT32 값은 양자화 산술로 유일하게 결정된다 -- Furiosa 든 누구의 NPU 든 이 값을 내야
한다. 그래서 외부 데이터도, 특정 회사 코드도 필요 없다. 다만 정답을 '검사'하려면 후보가 낸
Verilog 를 실제로 시뮬레이션해야 하므로 iverilog(또는 verilator)가 필요하다 -- 그게 이
도메인이 텐서보다 '무거운' 이유다.

부정 행위 차단: 테스트 벡터를 매 채점마다 새로 뽑아 테스트벤치에 심는다. 고정 벡터면 후보가
출력을 하드코딩해 통과할 수 있다 -- 신선한 무작위 벡터는 후보가 실제로 산술을 구현하게 강제한다.
(텐서에서 '부분점수 없음'으로 근사 위조를 막은 것과 같은 취지.)

점수(정확성은 하드 게이트, 품질은 그라디언트 -- 텐서와 판박이):
    기능 검증 실패        -> 0.0   (틀린 하드웨어는 가치 0. 부분점수 없음.)
    기능 검증 통과        -> 1.0 + (baseline_area - area) / baseline_area
      - baseline(사람이 쓴 정확한 설계)의 면적을 재현하면 1.0.
      - 더 작은 면적(게이트/셀 수)이면 그만큼 높다. yosys 합성으로 잰다.
      - yosys 가 없으면 정확한 설계는 전부 1.0(면적 비교 생략) -- 기능만으로도 루프는 돈다.

계약: 후보의 solve(data_dir, out_path) 는 out_path 에 Verilog 모듈 'dut' 를 쓴다.
포트는 고정이다(아래 DUT_INTERFACE). 데이터는 안 읽는다 -- 정답이 정의로 주어지므로.

이 환경에는 iverilog/yosys 가 없어 실제 시뮬레이션은 VM 에서 돈다. 이 파일의 채점 로직은
시뮬레이터 호출을 주입 가능하게(_SIM_HOOK) 만들어, 도구 없이도 채점 규칙만 따로 검증한다.
"""
from __future__ import annotations

import os
import random
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

DUT_INTERFACE = """module dut(
    input                clk,
    input                rst,    // 동기 리셋, active-high
    input                en,     // en=1 인 사이클에 한 번 누산
    input  signed [7:0]  a,
    input  signed [7:0]  b,
    output signed [31:0] acc     // acc <= acc + a*b (부호 있는 32비트, 오버플로 없게 벡터 길이 제한)
);"""

VEC_LEN = 64          # |acc| 최대 = 64*128*127 ≈ 1.04M < 2^31 -> 32비트 안에서 오버플로 없음
NUM_TRIALS = 4        # 서로 다른 무작위 벡터로 여러 번 -- 우연 통과를 줄인다


# ---------------------------------------------------------------- 골든 모델

def golden_acc(pairs) -> int:
    """정답 누산값. INT8×INT8 -> INT32 누산. 이 값이 곧 오라클이다(정의로 주어짐)."""
    acc = 0
    for a, b in pairs:
        acc += a * b
    # 32비트 two's complement 로 랩(벡터 길이를 제한해 실제로는 랩이 안 일어남).
    acc &= 0xFFFFFFFF
    return acc - (1 << 32) if acc & 0x80000000 else acc


def _random_vectors(seed: int):
    rng = random.Random(seed)
    return [[(rng.randint(-128, 127), rng.randint(-128, 127)) for _ in range(VEC_LEN)]
            for _ in range(NUM_TRIALS)]


# ---------------------------------------------------------------- 테스트벤치 생성

def make_testbench(vectors) -> str:
    """무작위 벡터를 심은 자기 검사 테스트벤치. 각 trial 마다 리셋 후 누산, 골든과 비교.
    전부 맞으면 'ALL_PASS', 하나라도 틀리면 'FAIL trial=k got=.. exp=..' 을 출력한다."""
    lines = [
        "`timescale 1ns/1ps",
        "module tb;",
        "  reg clk=0, rst=0, en=0;",
        "  reg signed [7:0] a=0, b=0;",
        "  wire signed [31:0] acc;",
        "  integer errors=0;",
        "  dut u_dut(.clk(clk), .rst(rst), .en(en), .a(a), .b(b), .acc(acc));",
        "  always #5 clk = ~clk;",
        "  task apply_reset; begin",
        "    @(negedge clk); rst=1; en=0; @(negedge clk); rst=0; end",
        "  endtask",
        "  initial begin",
    ]
    for k, vec in enumerate(vectors):
        exp = golden_acc(vec)
        lines.append(f"    // ---- trial {k} ----")
        lines.append("    apply_reset;")
        for (a, b) in vec:
            lines.append(f"    @(negedge clk); en=1; a={a}; b={b};")
        lines.append("    @(negedge clk); en=0;")
        lines.append("    @(negedge clk);")   # 마지막 누산이 acc 에 반영될 시간
        lines.append(f"    if (acc !== 32'sd{exp}) begin")
        lines.append(f'      $display("FAIL trial={k} got=%0d exp={exp}", acc); errors=errors+1;')
        lines.append("    end")
    lines += [
        '    if (errors==0) $display("ALL_PASS");',
        "    $finish;",
        "  end",
        "  initial begin #100000; $display(\"FAIL timeout\"); $finish; end",
        "endmodule",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- 시뮬레이터 (기능 검증)

_SIM_HOOK = None    # 테스트에서 (dut_src, tb_src) -> (ok: bool, detail: str) 를 주입


def simulate(dut_path: Path, seed: int) -> dict:
    """iverilog 로 dut+tb 를 컴파일·실행해 기능을 검증한다. (ok, detail).
    _SIM_HOOK 이 있으면 그것을 쓴다(도구 없는 환경에서 채점 규칙만 시험하기 위해)."""
    dut_src = Path(dut_path).read_text(encoding="utf-8")
    tb_src = make_testbench(_random_vectors(seed))

    if _SIM_HOOK is not None:
        ok, detail = _SIM_HOOK(dut_src, tb_src)
        return {"ok": ok, "detail": detail, "sim": "mock"}

    if not shutil.which("iverilog"):
        return {"ok": False, "detail": "iverilog 가 없다 -- 'sudo apt install iverilog' 후 재시도",
                "sim": "missing"}

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "dut.v").write_text(dut_src, encoding="utf-8")
        (tmp / "tb.v").write_text(tb_src, encoding="utf-8")
        vvp = tmp / "a.out"
        comp = subprocess.run(["iverilog", "-g2012", "-o", str(vvp),
                               str(tmp / "dut.v"), str(tmp / "tb.v")],
                              capture_output=True, text=True, timeout=120)
        if comp.returncode != 0:
            return {"ok": False, "detail": f"컴파일 실패: {(comp.stderr or comp.stdout)[-600:]}",
                    "sim": "iverilog"}
        run = subprocess.run(["vvp", str(vvp)], capture_output=True, text=True, timeout=120)
        out = (run.stdout or "") + (run.stderr or "")
        ok = "ALL_PASS" in out and "FAIL" not in out
        return {"ok": ok, "detail": out.strip()[-600:], "sim": "iverilog"}


# ---------------------------------------------------------------- 면적 (품질)

def synth_area(dut_path: Path) -> dict:
    """yosys 로 일반 게이트에 합성해 셀 수를 센다. 없으면 None(면적 비교 생략)."""
    if not shutil.which("yosys"):
        return {"area": None, "detail": "yosys 없음 -- 면적 비교 생략"}
    with tempfile.TemporaryDirectory() as tmp:
        script = f"read_verilog -sv {dut_path}\nsynth -top dut\nstat\n"
        sp = Path(tmp) / "s.ys"
        sp.write_text(script, encoding="utf-8")
        r = subprocess.run(["yosys", "-q", "-s", str(sp)], capture_output=True, text=True,
                           timeout=180)
        out = (r.stdout or "") + (r.stderr or "")
        m = re.search(r"Number of cells:\s+(\d+)", out)
        if r.returncode != 0 or not m:
            return {"area": None, "detail": f"합성 실패: {out[-400:]}"}
        return {"area": int(m.group(1)), "detail": f"cells={m.group(1)}"}


# ---------------------------------------------------------------- 채점

def score_rtl(dut_path: Path, cfg: dict) -> dict:
    """정확성 하드 게이트 + 면적 그라디언트. baseline_area 는 config 에 없으면 첫 정답에서 잡는다."""
    seed = int(cfg.get("eval_seed", 12345))
    sim = simulate(Path(dut_path), seed)
    if not sim["ok"]:
        return {"combined": 0.0, "functional": False, "area": None,
                "error": sim["detail"], "sim": sim["sim"]}
    area = synth_area(Path(dut_path))["area"]
    base = cfg.get("baseline_area")
    if area is None or base is None or base <= 0:
        combined = 1.0
    else:
        combined = 1.0 + (base - area) / base
    return {"combined": combined, "functional": True, "area": area,
            "baseline_area": base, "sim": sim["sim"]}
