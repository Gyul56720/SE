`timescale 1ns / 1ps
module simple_testbench;
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
        
        // 1. Load Activations: 'H'(72), 'i'(105) at index 0 and 1
        mem_awaddr=0; mem_wdata={112'd0, 8'd105, 8'd72}; mem_awvalid=1; mem_wvalid=1;
        #10 mem_awvalid=0; mem_wvalid=0;

        // 2. Load Weights: Set weights for index 0 and 1 to +1 (2'b01)
        // Each 128-bit word holds 64 weights (2 bits each). 0x5555... means all +1.
        #10;
        mem_awaddr=32'h1000; mem_wdata=128'h55555555555555555555555555555555; mem_awvalid=1; mem_wvalid=1;
        #10 mem_awvalid=0; mem_wvalid=0;

        // 3. Trigger NPU Start
        #10;
        csr_awaddr=0; csr_wdata=1; csr_awvalid=1; csr_wvalid=1;
        #10 csr_awvalid=0; csr_wvalid=0;

        wait(npu_done);
        $display("RESULT=%0d (Expected for H=72 + i=105 with weight +1: 177)", npu_result);
        $finish;
    end
endmodule
