
`timescale 1ns / 1ps
module npu_sentence_testbench;
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
        
        // Load Sentence ASCII values into AXI memory (15 chars packed into 128-bit words)
        // Word 0: 'I'(73), ' '(32), 'a'(97), 'm'(109) -> 0x6d612049
        @(posedge clk);
        mem_awaddr=0; mem_wdata=128'h0000000000000000000000006d612049; mem_awvalid=1; mem_wvalid=1;
        wait(dut.s_axi_mem_awready); @(posedge clk); mem_awvalid=0; mem_wvalid=0;

        // Word 1: ' '(32), 'v'(118), 'e'(101), 'r'(114)
        @(posedge clk);
        mem_awaddr=1; mem_wdata=128'h00000000000000000000000072657620; mem_awvalid=1; mem_wvalid=1;
        wait(dut.s_axi_mem_awready); @(posedge clk); mem_awvalid=0; mem_wvalid=0;

        // Word 2: 'y'(121), ' '(32), 't'(116), 'i'(105)
        @(posedge clk);
        mem_awaddr=2; mem_wdata=128'h00000000000000000000000069742079; mem_awvalid=1; mem_wvalid=1;
        wait(dut.s_axi_mem_awready); @(posedge clk); mem_awvalid=0; mem_wvalid=0;

        // Word 3: 'r'(114), 'e'(101), 'd'(100)
        @(posedge clk);
        mem_awaddr=3; mem_wdata=128'h000000000000000000000000646572; mem_awvalid=1; mem_wvalid=1;
        wait(dut.s_axi_mem_awready); @(posedge clk); mem_awvalid=0; mem_wvalid=0;

        // Load Weights (+1 for indices 0 to 14) -> 0x5555...
        @(posedge clk);
        mem_awaddr=32'h1000; mem_wdata=128'h55555555555555555555555555555555; mem_awvalid=1; mem_wvalid=1;
        wait(dut.s_axi_mem_awready); @(posedge clk); mem_awvalid=0; mem_wvalid=0;

        // Trigger NPU
        @(posedge clk);
        csr_awaddr=0; csr_wdata=1; csr_awvalid=1; csr_wvalid=1;
        wait(dut.s_axi_csr_awready); @(posedge clk); csr_awvalid=0; csr_wvalid=0;

        wait(npu_done);
        $display("HARDWARE_RESULT=%0d (Expected Sum: 1365)", npu_result);
        $finish;
    end
endmodule
