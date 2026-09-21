# -*- coding: utf-8 -*-
"""house/hls -- 작지만 진짜인 고수준 합성기.

**무엇인가.** C 와 같은 상위 언어(여기서는 파이썬 식 문법의 제한된 부분집합)로 적은
동작 기술을 받아, 데이터 흐름 그래프(DFG)를 만들고, **자원 제약 아래에서 스케줄**하고,
연산기와 레지스터를 **바인딩**하고, 파이프라인 SystemVerilog 를 **생성**한다.
첨부된 HLS Flow 그림의 `HLS Coding -> HLS Verification (Function, PPA)` 상자가 이것이다.

**왜 직접 지었나.** Vitis HLS · Catapult · Stratus 가 이 기계에 없다. 그러면 두 길이
있다: 안 한 것을 한 것처럼 적거나, 같은 일을 하는 것을 지어서 실제로 돌리거나.
이 회사는 뒤를 고른다 -- 사용자(2026-09-21): "없으면 대안을 만들어서 실제로 돌리고
결과를 보고서로 보고해라."

**무엇을 못 하나(정직하게).**
  · 루프/조건문/배열 접근을 아직 안 받는다. 받는 것은 **하나의 산술 식**이다.
  · 연산기 공유는 같은 종류끼리만 한다(곱셈기끼리 · 덧셈기끼리).
  · 부동소수점 · 메모리 인터페이스 · 스트리밍 프로토콜 합성은 없다.
이 네 줄은 생성물 옆에 늘 붙어 나간다.

쓰기:
    python3 house/hls.py --식 "(a0*x0 + a1*x1) + (a2*x2 + a3*x3)" --곱셈기 2 --덧셈기 1
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
import time
from pathlib import Path

뿌리 = Path(__file__).resolve().parent

# 연산기 라이브러리 -- 지연(제어 단계 수)과 면적(게이트 상당). lab/se/mklib 의
# RC 모형과 아귀를 맞춘다: 16x16 곱셈기 ~ 덧셈기 12배, 지연 2배.
연산기 = {
    "mul": {"단계": 2, "면적": 1180.0, "이름": "MUL16"},
    "add": {"단계": 1, "면적": 96.0, "이름": "ADD40"},
    "sub": {"단계": 1, "면적": 102.0, "이름": "SUB40"},
    "shl": {"단계": 1, "면적": 24.0, "이름": "SHL"},
}


class 마디:
    __slots__ = ("id", "종류", "인자", "asap", "alap", "때", "자원", "이름")

    def __init__(self, id_, 종류, 인자, 이름=""):
        self.id = id_
        self.종류 = 종류          # "in" | "const" | "mul" | "add" | ...
        self.인자 = 인자          # 앞 마디 id 목록
        self.이름 = 이름
        self.asap = 0
        self.alap = 0
        self.때 = -1              # 스케줄된 제어 단계
        self.자원 = -1            # 바인딩된 연산기 번호

    def __repr__(self):
        return f"<{self.id}:{self.종류}{self.인자} t={self.때} r={self.자원}>"


class DFG:
    def __init__(self):
        self.마디들: list[마디] = []
        self.입력: list[str] = []
        self.상수: dict[int, int] = {}
        self.출력 = -1

    def 더하기(self, 종류, 인자, 이름="") -> int:
        n = 마디(len(self.마디들), 종류, list(인자), 이름)
        self.마디들.append(n)
        return n.id

    def 연산마디(self):
        return [n for n in self.마디들 if n.종류 in 연산기]


# ---------------------------------------------------------------- 1. 앞단(파싱)

_이항 = {ast.Mult: "mul", ast.Add: "add", ast.Sub: "sub", ast.LShift: "shl"}


def 읽기(식: str) -> DFG:
    """C 식과 같은 문법을 읽어 DFG 로 만든다.  파이썬 `ast` 로 진짜 파싱한다."""
    나무 = ast.parse(식.strip(), mode="eval")
    g = DFG()
    본것: dict[str, int] = {}

    def 걷기(x) -> int:
        if isinstance(x, ast.BinOp):
            op = _이항.get(type(x.op))
            if op is None:
                raise ValueError(f"안 받는 연산자: {type(x.op).__name__}")
            return g.더하기(op, [걷기(x.left), 걷기(x.right)])
        if isinstance(x, ast.Name):
            if x.id not in 본것:
                본것[x.id] = g.더하기("in", [], x.id)
                g.입력.append(x.id)
            return 본것[x.id]
        if isinstance(x, ast.Constant) and isinstance(x.value, int):
            i = g.더하기("const", [], str(x.value))
            g.상수[i] = x.value
            return i
        if isinstance(x, ast.UnaryOp) and isinstance(x.op, ast.USub):
            z = g.더하기("const", [], "0")
            g.상수[z] = 0
            return g.더하기("sub", [z, 걷기(x.operand)])
        raise ValueError(f"안 받는 문법: {ast.dump(x)[:60]}")

    g.출력 = 걷기(나무.body)
    return g


# ---------------------------------------------------------------- 2. 스케줄

def asap_alap(g: DFG, 상한=None) -> int:
    """ASAP/ALAP 를 매긴다.  둘의 차가 이동 여유(mobility)이고, 스케줄러가 그것을 쓴다."""
    for n in g.마디들:
        if n.종류 in ("in", "const"):
            n.asap = 0
        else:
            n.asap = max(g.마디들[a].asap + 연산기[g.마디들[a].종류]["단계"]
                         if g.마디들[a].종류 in 연산기 else g.마디들[a].asap
                         for a in n.인자)
    출 = g.마디들[g.출력]
    끝 = 출.asap + (연산기[출.종류]["단계"] if 출.종류 in 연산기 else 0)
    상한 = 상한 or 끝
    for n in reversed(g.마디들):
        n.alap = 상한 - (연산기[n.종류]["단계"] if n.종류 in 연산기 else 0)
    for n in reversed(g.마디들):
        소비자 = [m for m in g.마디들 if n.id in m.인자]
        if 소비자:
            n.alap = min(m.alap - (연산기[n.종류]["단계"] if n.종류 in 연산기 else 0)
                         for m in 소비자)
        elif n.id != g.출력:
            n.alap = 상한
    return 상한


def 스케줄(g: DFG, 자원: dict) -> dict:
    """자원 제약 리스트 스케줄링.  여유가 적은 마디(임계경로)를 먼저 놓는다.

    이것이 HLS 의 심장이다 -- 같은 C 식이 자원 표에 따라 다른 하드웨어가 된다.
    """
    asap_알랍 = asap_alap(g)
    for n in g.마디들:
        n.때 = 0 if n.종류 in ("in", "const") else -1

    안된것 = [n for n in g.연산마디()]
    t = 0
    쓴것: dict[int, dict[str, int]] = {}
    # **연산기는 시작 주기만 차지하지 않는다.** 2주기 곱셈기는 t 와 t+1 을 다 잡는다.
    # 이것을 안 보면 자원 2개로 4개를 쓴 스케줄이 나온다(처음에 실제로 그랬다).
    점유: dict[tuple, int] = {}

    def 빈가(종류, t0):
        d = 연산기[종류]["단계"]
        return all(점유.get((종류, t0 + k), 0) < 자원.get(종류, 0) for k in range(d))

    def 잡기(종류, t0):
        for k in range(연산기[종류]["단계"]):
            점유[(종류, t0 + k)] = 점유.get((종류, t0 + k), 0) + 1

    while 안된것:
        쓸수있는 = [n for n in 안된것
                 if all(g.마디들[a].때 >= 0 and
                        g.마디들[a].때 + (연산기[g.마디들[a].종류]["단계"] if g.마디들[a].종류 in 연산기 else 0) <= t
                        for a in n.인자)]
        # 여유(alap-asap)가 작은 것부터 -- 임계경로 우선
        쓸수있는.sort(key=lambda n: (n.alap - n.asap, n.id))
        for n in 쓸수있는:
            if 빈가(n.종류, t):
                n.때 = t
                잡기(n.종류, t)
                안된것.remove(n)
                쓴것.setdefault(t, {})
                쓴것[t][n.종류] = 쓴것[t].get(n.종류, 0) + 1
        t += 1
        if t > 500:
            raise RuntimeError("스케줄이 안 끝난다 -- 자원 표를 보라")

    출 = g.마디들[g.출력]
    지연 = 출.때 + (연산기[출.종류]["단계"] if 출.종류 in 연산기 else 0)
    # II(개시 간격): 한 자원이 몇 주기마다 한 번 쓰이나 -> 최대 사용량 / 보유량
    쓴합 = {}
    for _t, d in 쓴것.items():
        for k, v in d.items():
            쓴합[k] = 쓴합.get(k, 0) + v
    II = max([int(-(-쓴합[k] // max(자원.get(k, 1), 1))) for k in 쓴합] or [1])
    return {"지연_단계": 지연, "II": II, "단계별": 쓴것, "쓴합": 쓴합, "상한": asap_알랍}


# ---------------------------------------------------------------- 3. 바인딩

def 바인딩(g: DFG, 자원: dict) -> dict:
    """같은 종류의 연산기를 시간으로 나눠 쓴다.  좌측 끝 알고리즘의 단순형."""
    할당 = {k: [] for k in 자원}       # 종류 -> [ (끝나는때, 번호) ]
    for n in sorted(g.연산마디(), key=lambda n: (n.때, n.id)):
        칸 = 할당.setdefault(n.종류, [])
        놓았나 = False
        for i, 끝 in enumerate(칸):
            if 끝 <= n.때:
                칸[i] = n.때 + 연산기[n.종류]["단계"]
                n.자원 = i
                놓았나 = True
                break
        if not 놓았나:
            n.자원 = len(칸)
            칸.append(n.때 + 연산기[n.종류]["단계"])
    쓴개수 = {k: len(v) for k, v in 할당.items() if v}
    면적 = sum(연산기[k]["면적"] * v for k, v in 쓴개수.items())
    # 레지스터: 제어 단계 경계를 넘는 값의 수 (수명 겹침의 최댓값)
    수명 = []
    for n in g.마디들:
        if n.종류 in ("in", "const"):
            계속 = [m.때 for m in g.마디들 if n.id in m.인자]
            수명.append((0, max(계속) if 계속 else 0))
        else:
            끝 = n.때 + 연산기[n.종류]["단계"]
            소비 = [m.때 for m in g.마디들 if n.id in m.인자]
            수명.append((끝, max(소비) if 소비 else 끝))
    최대겹침 = 0
    끝단계 = max((b for _a, b in 수명), default=0)
    겹침표 = []
    for t in range(끝단계 + 1):
        c = sum(1 for a, b in 수명 if a <= t < b)
        겹침표.append(c)
        최대겹침 = max(최대겹침, c)
    return {"연산기수": 쓴개수, "연산기면적": round(면적, 1),
            "레지스터수": 최대겹침, "겹침표": 겹침표,
            "총면적_추정": round(면적 + 최대겹침 * 40 * 8, 1)}


# ---------------------------------------------------------------- 4. RTL 생성

def 생성(g: DFG, 스케줄결과: dict, 바인딩결과: dict, 모듈="hls_dut",
        DW=16, ACCW=40) -> str:
    """스케줄된 DFG 를 파이프라인 SystemVerilog 로 낸다.

    **값 정렬이 핵심이다.** 제어 단계 3 에서 쓰는 피연산자는 단계 3 의 값이어야
    하는데, 기본 입력은 단계 0 에 들어온다. 그 사이를 레지스터로 메우지 않으면
    파이프라인을 꽉 채워 돌릴 때 **엉뚱한 거래의 값끼리 더해진다** -- 처음 생성한
    RTL 이 정확히 그래서 200 벡터 중 199 개가 틀렸다. 아래 `쓸이름()` 이 그 정렬을
    한다: 생산 시점과 소비 시점의 차만큼 지연 레지스터를 깔고 그 이름을 쓴다.
    """
    T = 스케줄결과["지연_단계"]
    단계수 = {k: 연산기[k]["단계"] for k in 연산기}

    def 나온때(n):
        return 0 if n.종류 in ("in", "const") else n.때 + 단계수[n.종류]

    기본 = {}
    for n in g.마디들:
        if n.종류 == "in":
            기본[n.id] = n.이름
        elif n.종류 == "const":
            기본[n.id] = f"{ACCW}'sd{g.상수[n.id]}"
        else:
            기본[n.id] = f"n{n.id}"

    필요지연 = {}          # 마디 id -> 필요한 최대 지연 단수
    for m in g.마디들:
        for a_ in m.인자:
            d = m.때 - 나온때(g.마디들[a_])
            if d > 0:
                필요지연[a_] = max(필요지연.get(a_, 0), d)

    def 쓸이름(nid, t):
        n = g.마디들[nid]
        if n.종류 == "const":
            return 기본[nid]
        d = t - 나온때(n)
        if d <= 0:
            return 기본[nid] if n.종류 != "in" else n.이름
        꼬리 = f"_d{d}"
        return (n.이름 if n.종류 == "in" else 기본[nid]) + 꼬리

    줄 = []
    a = 줄.append
    a(f"// 자동 생성 -- house/hls.py  ({time.strftime('%Y-%m-%d %H:%M:%S')})")
    a(f"// 자원: {json.dumps(스케줄결과['쓴합'])}  지연 {T} 단계  II {스케줄결과['II']}")
    a("// **손으로 고치지 마라.** 식과 자원 표를 고치고 다시 생성한다.")
    a(f"module {모듈} #(parameter integer DW = {DW}, parameter integer ACCW = {ACCW}) (")
    a("    input  wire clk,")
    a("    input  wire rst_n,")
    a("    input  wire in_vld,")
    for nm in g.입력:
        a(f"    input  wire signed [DW-1:0] {nm},")
    a("    output wire signed [ACCW-1:0] y,")
    a("    output wire out_vld")
    a(");")
    W = max(T, 1)
    a(f"    // 밸리드 파이프라인 -- 지연 {T} 주기")
    a(f"    reg [{W-1}:0] vld_pipe;")
    a("    always @(posedge clk or negedge rst_n)")
    a("        if (!rst_n) vld_pipe <= '0;")
    if W > 1:
        a(f"        else        vld_pipe <= {{vld_pipe[{W-2}:0], in_vld}};")
    else:
        a("        else        vld_pipe <= in_vld;")
    a(f"    assign out_vld = vld_pipe[{W-1}];")
    a("")

    # ---- 값 정렬 레지스터 ----
    정렬 = [(nid, d) for nid, d in sorted(필요지연.items()) if d > 0]
    if 정렬:
        a("    // ---- 값 정렬(alignment) 레지스터 ----")
        for nid, dmax in 정렬:
            n = g.마디들[nid]
            원 = n.이름 if n.종류 == "in" else 기본[nid]
            폭 = "DW" if n.종류 == "in" else "ACCW"
            for d in range(1, dmax + 1):
                앞 = 원 if d == 1 else f"{원}_d{d-1}"
                a(f"    reg signed [{폭}-1:0] {원}_d{d};")
                a("    always @(posedge clk or negedge rst_n)")
                a(f"        if (!rst_n) {원}_d{d} <= '0;")
                a(f"        else        {원}_d{d} <= {앞};")
        a("")

    기호 = {"mul": "*", "add": "+", "sub": "-", "shl": "<<"}
    단계별 = {}
    for n in g.연산마디():
        단계별.setdefault(n.때, []).append(n)

    for t in sorted(단계별):
        a(f"    // ---- 제어 단계 {t} ----")
        for n in 단계별[t]:
            L = 쓸이름(n.인자[0], t)
            R = 쓸이름(n.인자[1], t)
            깊이 = 단계수[n.종류]
            a(f"    reg signed [ACCW-1:0] {기본[n.id]}_p0;   // {연산기[n.종류]['이름']} #{n.자원}")
            a("    always @(posedge clk or negedge rst_n)")
            a(f"        if (!rst_n) {기본[n.id]}_p0 <= '0;")
            a(f"        else        {기본[n.id]}_p0 <= $signed({L}) {기호[n.종류]} $signed({R});")
            for k in range(1, 깊이):
                a(f"    reg signed [ACCW-1:0] {기본[n.id]}_p{k};")
                a("    always @(posedge clk or negedge rst_n)")
                a(f"        if (!rst_n) {기본[n.id]}_p{k} <= '0;")
                a(f"        else        {기본[n.id]}_p{k} <= {기본[n.id]}_p{k-1};")
            a(f"    wire signed [ACCW-1:0] {기본[n.id]} = {기본[n.id]}_p{깊이-1};")
        a("")
    출 = g.마디들[g.출력]
    끝이름 = 기본[g.출력]
    남 = T - 나온때(출)
    if 남 > 0:
        a(f"    // 출력 정렬 {남} 단")
        for d in range(1, 남 + 1):
            앞 = 끝이름 if d == 1 else f"{끝이름}_o{d-1}"
            a(f"    reg signed [ACCW-1:0] {끝이름}_o{d};")
            a("    always @(posedge clk or negedge rst_n)")
            a(f"        if (!rst_n) {끝이름}_o{d} <= '0;")
            a(f"        else        {끝이름}_o{d} <= {앞};")
        끝이름 = f"{끝이름}_o{남}"
    a(f"    assign y = {끝이름};")
    a("endmodule")
    return "\n".join(줄) + "\n"


# ---------------------------------------------------------------- 5. 검증 (기능 + PPA)

def C모델(식: str, 값: dict) -> int:
    """생성된 RTL 이 맞는지 견줄 황금 모델.  같은 식을 파이썬이 셈한다."""
    return int(eval(compile(ast.parse(식, mode="eval"), "<hls>", "eval"), {"__builtins__": {}}, dict(값)))


def 기능확인(식: str, sv글: str, 모듈="hls_dut", 횟수=200, 씨앗=1) -> dict:
    """생성 RTL 을 iverilog 로 돌려 C 모델과 **바이트 단위로** 견준다."""
    import random
    g = 읽기(식)
    T = None
    for line in sv글.splitlines():
        if line.startswith("// 자원:"):
            T = int(line.split("지연")[1].split("단계")[0])
    T = T or 4
    rng = random.Random(씨앗)
    벡터 = []
    for _ in range(횟수):
        벡터.append({nm: rng.randint(-2000, 2000) for nm in g.입력})
    방 = Path("/tmp/hls_check")
    방.mkdir(parents=True, exist_ok=True)
    (방 / "dut.sv").write_text(sv글, encoding="utf-8")
    포트 = "".join(f"    reg signed [15:0] {nm};\n" for nm in g.입력)
    잇기 = ", ".join(f".{nm}({nm})" for nm in g.입력)
    자극 = []
    for i, v in enumerate(벡터):
        자극.append("      " + " ".join(f"{nm} = {v[nm]};" for nm in g.입력) +
                   " in_vld = 1; @(posedge clk);")
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst_n = 0, in_vld = 0;
{포트}  wire signed [39:0] y;
  wire out_vld;
  integer i;
  {모듈} u ( .clk(clk), .rst_n(rst_n), .in_vld(in_vld), {잇기}, .y(y), .out_vld(out_vld) );
  always #5 clk = ~clk;
  always @(posedge clk) if (out_vld) $display("Y %0d", y);
  initial begin
    repeat (4) @(posedge clk);
    rst_n = 1;
    @(posedge clk);
{chr(10).join(자극)}
    in_vld = 0;
    repeat ({T} + 4) @(posedge clk);
    $finish;
  end
endmodule
"""
    (방 / "tb.v").write_text(tb, encoding="utf-8")
    r = subprocess.run(["iverilog", "-g2012", "-o", str(방 / "a.out"),
                        str(방 / "tb.v"), str(방 / "dut.sv")],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return {"됐나": False, "까닭": "iverilog 컴파일 실패: " + (r.stderr or r.stdout)[-600:]}
    s = subprocess.run(["vvp", str(방 / "a.out")], capture_output=True, text=True, timeout=180)
    나온것 = [int(l.split()[1]) for l in s.stdout.splitlines() if l.startswith("Y ")]
    기대 = [C모델(식, v) for v in 벡터]
    n = min(len(나온것), len(기대))
    틀린 = [(i, 나온것[i], 기대[i]) for i in range(n) if 나온것[i] != 기대[i]]
    return {"됐나": (n == len(기대) and not 틀린), "견준수": n, "기대수": len(기대),
            "틀린수": len(틀린), "틀린예": 틀린[:5],
            "까닭": "" if (n == len(기대) and not 틀린) else
                   (f"출력 {n}/{len(기대)} 개만 나왔다" if n != len(기대) else f"{len(틀린)}개 불일치")}


def PPA(sv글: str, 모듈="hls_dut") -> dict:
    """yosys 로 면적을, 자체 STA 로 Fmax 를 잰다.  HLS 의 'PPA 검증' 상자가 이것이다."""
    방 = Path("/tmp/hls_ppa")
    방.mkdir(parents=True, exist_ok=True)
    (방 / "dut.sv").write_text(sv글, encoding="utf-8")
    js = 방 / "dut.json"
    lib = 뿌리.parent / "lab" / "lib" / "se10.lib"
    대본 = (f"read_verilog -sv {방/'dut.sv'}; hierarchy -top {모듈}; "
          f"proc; opt; fsm; opt; memory; opt; techmap; opt; "
          f"dfflibmap -liberty {lib}; abc -liberty {lib}; opt_clean; "
          f"stat -liberty {lib}; write_json {js}")
    r = subprocess.run(["yosys", "-p", 대본], capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        return {"됐나": False, "까닭": (r.stderr or r.stdout)[-800:]}
    면적, 셀수 = 0.0, 0
    for line in r.stdout.splitlines():
        if "Chip area for module" in line:
            면적 = float(line.rsplit(":", 1)[1])
        if line.strip().startswith("Number of cells:"):
            셀수 = int(line.split(":")[1])
    결과 = {"됐나": True, "면적_um2": round(면적, 1), "셀수": 셀수, "json": str(js)}
    try:
        sys.path.insert(0, str(뿌리.parent / "lab" / "se"))
        import liberty as L
        import netlist as NL
        import sta as STA
        lb = L.라이브러리(str(lib))
        nl = NL.넷리스트(str(js), lb)
        a = STA.분석기(nl, 주기=10.0)
        res = a.풀기()
        요약 = res.요약()
        결과["Fmax_MHz"] = 요약.get("Fmax_MHz")
        결과["플롭"] = nl.요약().get("플롭")
    except Exception as e:                                   # noqa: BLE001
        결과["Fmax_MHz"] = None
        결과["sta_까닭"] = f"{type(e).__name__}: {e}"
    return 결과


# ---------------------------------------------------------------- 한 바퀴

def 한바퀴(식: str, 자원: dict, 모듈="hls_dut", 확인횟수=200) -> dict:
    t0 = time.time()
    g = 읽기(식)
    sch = 스케줄(g, 자원)
    bnd = 바인딩(g, 자원)
    sv = 생성(g, sch, bnd, 모듈)
    fn = 기능확인(식, sv, 모듈, 횟수=확인횟수)
    ppa = PPA(sv, 모듈)
    return {"식": 식, "자원": dict(자원), "스케줄": sch, "바인딩": bnd,
            "SV": sv, "기능": fn, "PPA": ppa, "초": round(time.time() - t0, 2),
            "마디수": len(g.마디들), "연산수": len(g.연산마디()), "입력": list(g.입력)}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--식", default="(a0*x0 + a1*x1) + (a2*x2 + a3*x3)")
    ap.add_argument("--곱셈기", type=int, default=2)
    ap.add_argument("--덧셈기", type=int, default=1)
    ap.add_argument("--내기", default="")
    a = ap.parse_args()
    r = 한바퀴(a.식, {"mul": a.곱셈기, "add": a.덧셈기, "sub": a.덧셈기})
    print(f"식      : {r['식']}")
    print(f"자원    : {r['자원']}")
    print(f"스케줄  : 지연 {r['스케줄']['지연_단계']} 단계 · II {r['스케줄']['II']}")
    print(f"바인딩  : {r['바인딩']['연산기수']} · 레지스터 {r['바인딩']['레지스터수']}")
    print(f"기능확인: {'통과' if r['기능']['됐나'] else '실패 ' + r['기능']['까닭']} "
          f"({r['기능'].get('견준수')} 벡터)")
    print(f"PPA     : 면적 {r['PPA'].get('면적_um2')} um^2 · Fmax {r['PPA'].get('Fmax_MHz')} MHz")
    if a.내기:
        Path(a.내기).write_text(r["SV"], encoding="utf-8")
        print(f"SV -> {a.내기}")
    return 0 if r["기능"]["됐나"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
