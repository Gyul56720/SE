import subprocess
import os

hi_tb_code = """
`timescale 1ns / 1ps

module npu_hi_testbench;
    logic clk, rst_n;
    logic [127:0] crypto_key = 128'h0; // 암호화 없이 명확한 연산 확인

    logic [31:0] csr_awaddr, csr_wdata, csr_araddr;
    logic csr_awvalid, csr_awready, csr_wvalid, csr_wready, csr_bvalid, csr_bready;
    logic csr_arvalid, csr_arready, csr_rvalid, csr_rready;

    logic [31:0] mem_awaddr;
    logic [127:0] mem_wdata;
    logic mem_awvalid, mem_awready, mem_wvalid, mem_wready, mem_bvalid, mem_bready;

    logic signed [20:0] npu_result;
    logic npu_done;

    npu_axi_top dut (
        .clk(clk), .rst_n(rst_n),
        .s_axi_csr_awaddr(csr_awaddr), .s_axi_csr_awvalid(csr_awvalid), .s_axi_csr_awready(csr_awready),
        .s_axi_csr_wdata(csr_wdata), .s_axi_csr_wvalid(csr_wvalid), .s_axi_csr_wready(csr_wready),
        .s_axi_csr_bresp(), .s_axi_csr_bvalid(csr_bvalid), .s_axi_csr_bready(csr_bready),
        .s_axi_csr_araddr(csr_araddr), .s_axi_csr_arvalid(csr_arvalid), .s_axi_csr_arready(csr_arready),
        .s_axi_csr_rdata(), .s_axi_csr_rresp(), .s_axi_csr_rvalid(csr_rvalid), .s_axi_csr_rready(csr_rready),
        .s_axi_mem_awaddr(mem_awaddr), .s_axi_mem_awvalid(mem_awvalid), .s_axi_mem_awready(mem_awready),
        .s_axi_mem_wdata(mem_wdata), .s_axi_mem_wvalid(mem_wvalid), .s_axi_mem_wready(mem_wready),
        .s_axi_mem_bresp(), .s_axi_mem_bvalid(mem_bvalid), .s_axi_mem_bready(mem_bready),
        .crypto_key(crypto_key), .npu_result_out(npu_result), .npu_done_irq(npu_done)
    );

    initial clk = 0;
    always #5 clk = ~clk;

    initial begin
        rst_n = 0; csr_awvalid = 0; csr_wvalid = 0; csr_bready = 0;
        csr_arvalid = 0; csr_rready = 0; mem_awvalid = 0; mem_wvalid = 0; mem_bready = 0;
        #20; rst_n = 1; #20;

        $display("=== [Debug] Injecting 'Hi' Tensor Stream ===");

        // 1. Load 'Hi' Activations: 72, 105
        @(posedge clk);
        mem_awaddr = 32'h0; 
        mem_wdata  = {112'd0, 8'd105, 8'd72};
        mem_awvalid = 1; mem_wvalid = 1; mem_bready = 1;
        wait(mem_bvalid); @(posedge clk); mem_awvalid = 0; mem_wvalid = 0;

        // 2. Load Weights (+1, i.e., 2'b01)
        @(posedge clk);
        mem_awaddr = 32'h1000;
        mem_wdata  = 128'h55555555555555555555555555555555; 
        mem_awvalid = 1; mem_wvalid = 1; mem_bready = 1;
        wait(mem_bvalid); @(posedge clk); mem_awvalid = 0; mem_wvalid = 0;

        // 3. Settling Time (Allow memory write to propagate)
        repeat(10) @(posedge clk);

        // 4. Trigger NPU
        @(posedge clk);
        csr_awaddr = 32'h00; csr_wdata = 32'h01; csr_awvalid = 1; csr_wvalid = 1; csr_bready = 1;
        wait(csr_bvalid); @(posedge clk); csr_awvalid = 0; csr_wvalid = 0;

        // 5. Wait for Done
        wait(npu_done);
        $display("=== [Result] Final Output Vector Dot Product = %0d ===", npu_result);
        
        $finish;
    end
endmodule
"""

with open("npu_hi_testbench.sv", "w") as f:
    f.write(hi_tb_code)

subprocess.run(["iverilog", "-g2012", "-o", "hi_sim", "npu_axi_top.sv", "npu_hi_testbench.sv", "npu_array_4096.sv", "npu_tile.sv", "npu_pe.sv"], check=True)
res = subprocess.run(["vvp", "hi_sim"], capture_output=True, text=True)
print(res.stdout)
