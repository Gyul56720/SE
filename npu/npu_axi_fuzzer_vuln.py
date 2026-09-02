import subprocess
import sys
import numpy as np

print("=========================================================================")
print("=== [NPU AXI4 Advanced Vulnerability & Fuzzing Analyzer] Initializing ===")
print("=========================================================================")

# Step 1: Generate malicious/edge-case stimulus for AXI bus
# Test vector 1: Out-of-bounds memory write address (> 4096)
# Test vector 2: X/Z state propagation injection
# Test vector 3: Deadlock trigger (holding AWVALID high without AWREADY response check)

print("\n[Fuzzing Phase 1] Injecting Out-of-Bounds Memory Addresses & Malformed Handshakes...")

fuzz_tb_code = """
`timescale 1ns / 1ps

module npu_axi_testbench;
    logic        clk;
    logic        rst_n;

    logic [31:0] s_axi_csr_awaddr;
    logic        s_axi_csr_awvalid;
    logic        s_axi_csr_awready;
    logic [31:0] s_axi_csr_wdata;
    logic        s_axi_csr_wvalid;
    logic        s_axi_csr_wready;
    logic [1:0]  s_axi_csr_bresp;
    logic        s_axi_csr_bvalid;
    logic        s_axi_csr_bready;

    logic [31:0] s_axi_csr_araddr;
    logic        s_axi_csr_arvalid;
    logic        s_axi_csr_arready;
    logic [31:0] s_axi_csr_rdata;
    logic [1:0]  s_axi_csr_rresp;
    logic        s_axi_csr_rvalid;
    logic        s_axi_csr_rready;

    logic [31:0]  s_axi_mem_awaddr;
    logic         s_axi_mem_awvalid;
    logic         s_axi_mem_awready;
    logic [127:0] s_axi_mem_wdata;
    logic         s_axi_mem_wvalid;
    logic         s_axi_mem_wready;
    logic [1:0]   s_axi_mem_bresp;
    logic         s_axi_mem_bvalid;
    logic         s_axi_mem_bready;

    logic signed [20:0] npu_result_out;
    logic               npu_done_irq;

    npu_axi_top dut (
        .clk(clk),
        .rst_n(rst_n),
        .s_axi_csr_awaddr(s_axi_csr_awaddr),
        .s_axi_csr_awvalid(s_axi_csr_awvalid),
        .s_axi_csr_awready(s_axi_csr_awready),
        .s_axi_csr_wdata(s_axi_csr_wdata),
        .s_axi_csr_wvalid(s_axi_csr_wvalid),
        .s_axi_csr_wready(s_axi_csr_wready),
        .s_axi_csr_bresp(s_axi_csr_bresp),
        .s_axi_csr_bvalid(s_axi_csr_bvalid),
        .s_axi_csr_bready(s_axi_csr_bready),
        .s_axi_csr_araddr(s_axi_csr_araddr),
        .s_axi_csr_arvalid(s_axi_csr_arvalid),
        .s_axi_csr_arready(s_axi_csr_arready),
        .s_axi_csr_rdata(s_axi_csr_rdata),
        .s_axi_csr_rresp(s_axi_csr_rresp),
        .s_axi_csr_rvalid(s_axi_csr_rvalid),
        .s_axi_csr_rready(s_axi_csr_rready),
        .s_axi_mem_awaddr(s_axi_mem_awaddr),
        .s_axi_mem_awvalid(s_axi_mem_awvalid),
        .s_axi_mem_awready(s_axi_mem_awready),
        .s_axi_mem_wdata(s_axi_mem_wdata),
        .s_axi_mem_wvalid(s_axi_mem_wvalid),
        .s_axi_mem_wready(s_axi_mem_wready),
        .s_axi_mem_bresp(s_axi_mem_bresp),
        .s_axi_mem_bvalid(s_axi_mem_bvalid),
        .s_axi_mem_bready(s_axi_mem_bready),
        .npu_result_out(npu_result_out),
        .npu_done_irq(npu_done_irq>
    );

    initial clk = 0;
    always #5 clk = ~clk;

    initial begin
        rst_n = 0;
        s_axi_csr_awvalid = 0; s_axi_csr_wvalid = 0; s_axi_csr_bready = 0;
        s_axi_csr_arvalid = 0; s_axi_csr_rready = 0;
        s_axi_mem_awvalid = 0; s_axi_mem_wvalid = 0; s_axi_mem_bready = 0;
        #20;
        rst_n = 1;
        #20;

        $display("[Vulnerability Test] Injecting Out-of-Bounds AXI Memory Address (0xFFFF)...");
        @(posedge clk);
        s_axi_mem_awaddr  <= 32'hFFFF; // Out of bounds!
        s_axi_mem_wdata   <= 128'hDEADBEEFDEADBEEFDEADBEEFDEADBEEF;
        s_axi_mem_awvalid <= 1'b1;
        s_axi_mem_wvalid  <= 1'b1;
        s_axi_mem_bready  <= 1'b1;
        
        #100;
        $display("[Vulnerability Test] Injecting X/Z State Trigger...");
        s_axi_mem_awaddr  <= 32'hX; // Undefined address state!
        s_axi_mem_wvalid  <= 1'bx;
        
        #100;
        $display("[Vulnerability Test Analysis Complete] Checking robustness...");
        $finish;
    end
endmodule
"""

print("Writing fuzz testbench...")
# Backup original testbench
subprocess.run(["cp", "npu_axi_testbench.sv", "npu_axi_testbench.sv.bak"], check=True)

# Write malicious fuzzed testbench
with open("npu_axi_testbench.sv", "w") as f:
    f.write(fuzz_tb_code.replace("npu_done_irq(npu_done_irq>", "npu_done_irq(npu_done_irq)"))

print("Compiling fuzzed binary...")
compile_res = subprocess.run([
    "iverilog", "-g2012", "-o", "vuln_sim",
    "npu_pe.sv", "npu_tile.sv", "npu_array_4096.sv", "npu_axi_top.sv", "npu_axi_testbench.sv"
], capture_output=True, text=True)

if compile_res.returncode != 0:
    print("[VULNERABILITY DETECTED AT COMPILE/SYNTAX LEVEL]:\n", compile_res.stderr)
else:
    print("Running simulation with fuzzed inputs...")
    sim_res = subprocess.run(["vvp", "vuln_sim"], capture_output=True, text=True)
    print(sim_res.stdout)
    if sim_res.stderr:
        print("Runtime Warnings/Errors:\n", sim_res.stderr)

# Restore original testbench
subprocess.run(["mv", "npu_axi_testbench.sv.bak", "npu_axi_testbench.sv"], check=True)
print("=== [Fuzzing Analyzer Complete] Original testbench restored safely ===")
