`timescale 1ns / 1ps
module npu_real_weight_testbench;
    logic clk, rst_n;
    logic [127:0] mem_wdata;
    logic [31:0] mem_awaddr;
    logic mem_awvalid, mem_wvalid, mem_bready;
    logic mem_bvalid;

    npu_axi_top dut (
        .clk(clk), .rst_n(rst_n),
        .s_axi_mem_awaddr(mem_awaddr), .s_axi_mem_awvalid(mem_awvalid), 
        .s_axi_mem_wdata(mem_wdata), .s_axi_mem_wvalid(mem_wvalid),
        .s_axi_mem_bready(mem_bready), .s_axi_mem_bvalid(mem_bvalid),
        .npu_result_out(result), .npu_done_irq(done)
    );
    logic [20:0] result; logic done;
    initial clk=0; always #5 clk=~clk;
    
    initial begin
        rst_n=0; #20 rst_n=1;
        
        // 1. Load ASCII: 'I'(73), ' '(32), 'a'(97), 'm'(109)
        @(posedge clk);
        mem_awaddr=0; mem_wdata={32'd0, 8'd109, 8'd97, 8'd32, 8'd73};
        mem_awvalid=1; mem_wvalid=1; mem_bready=1;
        wait(mem_bvalid); @(posedge clk); mem_awvalid=0; mem_wvalid=0;

        // 2. Load Weights (Ternary 64 values: 1 for index 0, 1, 2, 3)
        // 2'b01 is +1. Word = 0x5555...
        @(posedge clk);
        mem_awaddr=32'h1000; mem_wdata=128'h55555555555555555555555555555555;
        mem_awvalid=1; mem_wvalid=1;
        wait(mem_bvalid); @(posedge clk); mem_awvalid=0; mem_wvalid=0;

        #50;
        $display("MAPPING_TEST_COMPLETE");
        $finish;
    end
endmodule
