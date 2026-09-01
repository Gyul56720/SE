"""
RTL MAC 도메인의 골든 모델·테스트벤치 생성 검증 (iverilog 없이 돌아가는 부분만).

실제 Verilog 시뮬레이션은 iverilog 가 필요해 VM 에서 돈다. 이 파일은 그 아래층 --
'정답이 무엇인가'(골든 모델)와 '그 정답을 어떻게 심판에 심는가'(테스트벤치 생성) -- 만
도구 없이 증명한다. 골든이 틀리면 그 위의 모든 채점이 틀리므로 여기가 바닥이다.
"""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "solver" / "domains"))
import rtl_mac as R   # noqa: E402


def main() -> int:
    fails = []
    def chk(c, l):
        print(("  OK   " if c else "  FAIL ") + l)
        if not c: fails.append(l)

    # 골든이 순진한 합과 일치
    for seed in range(5):
        for vec in R._random_vectors(seed):
            naive = sum(a * b for a, b in vec)
            chk(R.golden_acc(vec) == naive, f"골든==순진한합 (seed{seed}) {R.golden_acc(vec)}")
            break

    # 경계값
    chk(R.golden_acc([(127, 127)] * 1) == 127 * 127, "127*127")
    chk(R.golden_acc([(-128, -128)]) == 16384, "(-128)*(-128)=16384")
    chk(R.golden_acc([]) == 0, "빈 벡터 -> 0")

    # 벡터 길이가 32비트 안에서 오버플로 없음을 보장하는가
    worst = R.golden_acc([(127, 127)] * R.VEC_LEN)
    chk(-(2**31) <= worst < 2**31, f"최악 누산 {worst} 이 32비트 안 (오버플로 없음)")

    # 테스트벤치에 골든 기대값이 실제로 심겼는가 (부정행위 차단의 핵심)
    vecs = R._random_vectors(42)
    tb = R.make_testbench(vecs)
    chk(f"32'sd{R.golden_acc(vecs[0])}" in tb, "trial0 의 골든 기대값이 tb 에 심긴다")
    chk("ALL_PASS" in tb and "FAIL trial" in tb, "tb 가 PASS/FAIL 을 출력한다")
    chk("u_dut(.clk(clk)" in tb, "tb 가 dut 을 고정 포트로 인스턴스화한다")
    chk(tb.count("    apply_reset;") == R.NUM_TRIALS, f"trial 마다 리셋 ({R.NUM_TRIALS}회)")

    # 채점 규칙: 시뮬레이터를 목으로 갈아끼워 하드 게이트·면적 그라디언트 확인
    R._SIM_HOOK = lambda dut, tb: (True, "ALL_PASS")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        dut = Path(d) / "dut.v"; dut.write_text("module dut(); endmodule")
        s = R.score_rtl(dut, {"baseline_area": 100})   # yosys 없으면 area None -> 1.0
        chk(s["functional"] and s["combined"] == 1.0, f"기능 통과 -> 1.0 (area 비교 불가시) {s}")
    R._SIM_HOOK = lambda dut, tb: (False, "FAIL trial=0 got=1 exp=2")
    with tempfile.TemporaryDirectory() as d:
        dut = Path(d) / "dut.v"; dut.write_text("module dut(); endmodule")
        s = R.score_rtl(dut, {})
        chk(s["combined"] == 0.0 and not s["functional"], f"기능 실패 -> 0.0 (부분점수 없음) {s}")
    R._SIM_HOOK = None

    print("\n" + ("RTL 골든/테스트벤치/채점규칙 통과" if not fails else f"실패: {fails}"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
