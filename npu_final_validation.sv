`timescale 1ns / 1ps
module npu_final_validation;
    logic clk, rst_n;
    logic [31:0] mem_awaddr, csr_awaddr, csr_wdata;
    logic [127:0] mem_wdata;
    logic mem_awvalid, mem_wvalid, mem_bready, mem_bvalid;
    logic csr_awvalid, csr_wvalid, csr_bready, csr_bvalid;
    logic signed [20:0] result;
    logic done;

    npu_axi_top dut (
        .clk(clk), .rst_n(rst_n),
        .s_axi_mem_awaddr(mem_awaddr), .s_axi_mem_awvalid(mem_awvalid), .s_axi_mem_wdata(mem_wdata), .s_axi_mem_wvalid(mem_wvalid),
        .s_axi_mem_bready(mem_bready), .s_axi_mem_bvalid(mem_bvalid),
        .s_axi_csr_awaddr(csr_awaddr), .s_axi_csr_awvalid(csr_awvalid), .s_axi_csr_wdata(csr_wdata), .s_axi_csr_wvalid(csr_wvalid),
        .s_axi_csr_bready(csr_bready), .s_axi_csr_bvalid(csr_bvalid),
        .crypto_key(128'h0), .npu_result_out(result), .npu_done_irq(done)
    );
    initial clk=0; always #5 clk=~clk;
    
    initial begin
        rst_n=0; #20 rst_n=1;

        // 1. Load Activations: 'H'(72), 'i'(105)
        @(posedge clk);
        mem_awaddr=0; mem_wdata={112'd0, 8'd105, 8'd72};
        mem_awvalid=1; mem_wvalid=1; mem_bready=1;
        wait(mem_bvalid); @(posedge clk); mem_awvalid=0; mem_wvalid=0;

        // 2. Load Weights: All +1 (0x55...) for indices 0,1. 
        @(posedge clk);
        mem_awaddr=32'h1000; mem_wdata=128'h00000000000000000000000000000055; // Only weight 0,1 are +1
        mem_awvalid=1; mem_wvalid=1;
        wait(mem_bvalid); @(posedge clk); mem_awvalid=0; mem_wvalid=0;

        // 3. Trigger NPU
        @(posedge clk);
        csr_awaddr=0; csr_wdata=1; csr_awvalid=1; csr_wvalid=1; csr_bready=1;
        wait(csr_bvalid); @(posedge clk); csr_awvalid=0; csr_wvalid=0;

        // 4. Wait for Final Result
        wait(done);
        $display("FINAL_VALIDATION_RESULT=%0d", result);
        if (result == 177) $display("SUCCESS: Final Validation Passed for 'Hi'");
        else $display("FAILURE: Expected 177, Got %0d", result);
        $finish;
    end
endmodule
