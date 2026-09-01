# 가설: 출발점 -- 교과서적으로 정확한 행동 수준 MAC. 면적 최적화는 안 함(바닥을 만든다).
"""
RTL MAC 도메인의 베이스라인 solve. 정확하지만 면적을 안 줄인 행동(behavioral) 설계를 낸다.

일부러 단순하다. 바닥(기능 통과, score 1.0)을 만드는 것이 목적이고, LLM 은 여기서 같은 기능을
유지한 채 면적/타이밍을 줄이는 것을 노린다 -- 부분곱 인코딩(Booth), 파이프라이닝, 자원 공유 등.
정답이 산술로 정의되므로 data_dir 은 안 읽는다. out_path 에 Verilog 를 쓴다.
"""


def solve(data_dir: str, out_path: str) -> None:
    v = """// INT8 MAC 누산기 (베이스라인, 행동 수준)
module dut(
    input                clk,
    input                rst,
    input                en,
    input  signed [7:0]  a,
    input  signed [7:0]  b,
    output signed [31:0] acc
);
    reg signed [31:0] acc_r;
    assign acc = acc_r;
    always @(posedge clk) begin
        if (rst)      acc_r <= 32'sd0;
        else if (en)  acc_r <= acc_r + a * b;   // 부호 있는 곱, 32비트 누산
    end
endmodule
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(v)
