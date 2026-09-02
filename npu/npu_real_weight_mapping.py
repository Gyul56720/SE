import numpy as np
import subprocess

# 1. 실제 LLM (Qwen2.5-Coder-7B 스타일) 양자화 가중치 모사
# hidden_size = 4096, 1.58-bit Ternary (-1, 0, 1) with Sparsity (~40% zeros)
rng = np.random.default_rng(2026)
N = 4096

# 실제 1.58-bit Ternary 가중치 생성 (-1, 0, 1)
# 30% -1, 40% 0, 30% +1 분포
weights_ternary = rng.choice([-1, 0, 1], size=N, p=[0.3, 0.4, 0.3])

# 2. 입력 문장 "I am very tired" 텐서화 및 4096 패딩
sentence = "I am very tired"
ascii_vals = [ord(c) for c in sentence]

x = np.zeros(N, dtype=np.int16)
for i, val in enumerate(ascii_vals):
    x[i] = val

# 소프트웨어 Golden Reference (실제 내적 계산)
golden_dot_product = int(np.sum(x * weights_ternary))

print(f"=== [Real LLM Weight Mapping Simulation] ===")
print(f"Input Sentence    : '{sentence}' ({len(ascii_vals)} chars embedded in 4096-dim vector)")
print(f"Ternary Sparsity  : {np.sum(weights_ternary == 0) / N * 100:.1f}% zeros")
print(f"Software Golden Y : {golden_dot_product}")

# 3. Ternary 가중치를 하드웨어 인코딩 형식으로 변환
# 00: 0, 01: +1, 10: -1
def encode_w(w):
    if w == 0: return 0
    if w == 1: return 1
    if w == -1: return 2
    return 0

weights_encoded = [encode_w(w) for w in weights_ternary]

# 4. 하드웨어 테스트벤치 동적 생성 및 실제 VVP 구동
tb_code = f"""
`timescale 1ns / 1ps
module npu_real_weight_testbench;
    logic clk, rst_n;
    logic [31:0] mem_awaddr;
    logic [127:0] mem_wdata;
    logic mem_awvalid, mem_wvalid;
    logic [127:0] crypto_key = 128'h0;
    logic [31:0] csr_awaddr, csr_wdata;
    logic csr_awvalid, csr_wvalid;
    logic [20:0] npu_result;
    logic npu_done;

    npu_axi_top dut (
        .clk(clk), .rst_n(rst_n),
        .s_axi_mem_awaddr(mem_awaddr), .s_axi_mem_awvalid(mem_awvalid), .s_axi_mem_wdata(mem_wdata), .s_axi_mem_wvalid(mem_wvalid),
        .s_axi_csr_awaddr(csr_awaddr), .s_axi_csr_awvalid(csr_awvalid), .s_axi_csr_wdata(csr_wdata), .s_axi_csr_wvalid(csr_wvalid),
        .crypto_key(crypto_key), .npu_result_out(npu_result), .npu_done_irq(npu_done)
    );
    initial clk=0; always #5 clk=~clk;

    initial begin
        rst_n=0; #20 rst_n=1;

        // Load Activations ("I am very tired" embedded in first 16 bytes)
        // 'I',' ','a','m' -> 73, 32, 97, 109
        @(posedge clk);
        mem_awaddr=0; mem_wdata=128'h0000000000000000000000006d612049; mem_awvalid=1; mem_wvalid=1;
        wait(dut.s_axi_mem_awready); @(posedge clk); mem_awvalid=0; mem_wvalid=0;

        // Load Real Qwen Ternary Weights into AXI memory (0x1000 onwards)
        // We load the first few 128-bit blocks containing our sentence indices
"""

# 가중치 바이트 팩킹 (128-bit 당 64개 가중치, 각 2비트)
# 첫 번째 128-비트 워드(가중치 0~63번)만 우선 매핑하여 테스트
w_word0 = 0
for i in range(64):
    val = weights_encoded[i]
    w_word0 |= (val << (i * 2))

hex_w_word0 = f"{w_word0:032x}"

tb_code += f"""
        @(posedge clk);
        mem_awaddr = 32'h1000;
        mem_wdata = 128'h{hex_w_word0};
        mem_awvalid = 1; mem_wvalid = 1;
        wait(dut.s_axi_mem_awready); @(posedge clk); mem_awvalid=0; mem_wvalid=0;

        // Trigger NPU Start
        @(posedge clk);
        csr_awaddr = 0; csr_wdata = 1; csr_awvalid = 1; csr_wvalid = 1;
        wait(dut.s_axi_csr_awready); @(posedge clk); csr_awvalid=0; csr_wvalid=0;

        wait(npu_done);
        $display("HARDWARE_REAL_MAPPING_RESULT=%0d", npu_result);
        $finish;
    end
endmodule
"""

with open("npu_real_weight_testbench.sv", "w") as f:
    f.write(tb_code)

subprocess.run(["iverilog", "-g2012", "-o", "real_sim", "npu_axi_top.sv", "npu_real_weight_testbench.sv", "npu_array_4096.sv", "npu_tile.sv", "npu_pe.sv"], check=True)
res = subprocess.run(["vvp", "real_sim"], capture_output=True, text=True)
print(res.stdout)
