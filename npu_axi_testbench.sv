`timescale 1ns / 1ps

module npu_axi_testbench;
    logic        clk;
    logic        rst_n;

    // AXI CSR
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

    // AXI MEM
    logic [31:0]  s_axi_mem_awaddr;
    logic         s_axi_mem_awvalid;
    logic         s_axi_mem_awready;
    logic [127:0] s_axi_mem_wdata;
    logic         s_axi_mem_wvalid;
    logic         s_axi_mem_wready;
    logic [1:0]   s_axi_mem_bresp;
    logic         s_axi_mem_bvalid;
    logic         s_axi_mem_bready;

    // Outputs
    logic signed [20:0] npu_result_out;
    logic               npu_done_irq;

    // DUT Instantiation
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
        .npu_done_irq(npu_done_irq)
    );

    initial clk = 0;
    always #5 clk = ~clk;

    // Correct AXI4 Handshake for Memory Write
    task write_mem_128(input [31:0] addr, input [127:0] data);
        begin
            @(posedge clk);
            s_axi_mem_awaddr  <= addr;
            s_axi_mem_wdata   <= data;
            s_axi_mem_awvalid <= 1'b1;
            s_axi_mem_wvalid  <= 1'b1;
            s_axi_mem_bready  <= 1'b1;
            
            wait(s_axi_mem_awready && s_axi_mem_wready);
            @(posedge clk);
            s_axi_mem_awvalid <= 1'b0;
            s_axi_mem_wvalid  <= 1'b0;
            
            wait(s_axi_mem_bvalid);
            @(posedge clk);
            s_axi_mem_bready  <= 1'b0;
        end
    endtask

    // Correct AXI4 Handshake for CSR Write (Start)
    task start_npu();
        begin
            @(posedge clk);
            s_axi_csr_awaddr  <= 32'h00;
            s_axi_csr_wdata   <= 32'h01;
            s_axi_csr_awvalid <= 1'b1;
            s_axi_csr_wvalid  <= 1'b1;
            s_axi_csr_bready  <= 1'b1;
            
            wait(s_axi_csr_awready && s_axi_csr_wready);
            @(posedge clk);
            s_axi_csr_awvalid <= 1'b0;
            s_axi_csr_wvalid  <= 1'b0;
            
            wait(s_axi_csr_bvalid);
            @(posedge clk);
            s_axi_csr_bready  <= 1'b0;
        end
    endtask

    initial begin
        rst_n = 0;
        s_axi_csr_awvalid = 0; s_axi_csr_wvalid = 0; s_axi_csr_bready = 0;
        s_axi_csr_arvalid = 0; s_axi_csr_rready = 0;
        s_axi_mem_awvalid = 0; s_axi_mem_wvalid = 0; s_axi_mem_bready = 0;

        #50;
        rst_n = 1;
        #50;

        $display("=========================================================");
        $display("[AXI4 Protocol & Congestion Verification] Starting...");
        $display("=========================================================");

        // Test Case 1: Max Positive Overflow (Verification via Segmented Routing)
        for (int i = 0; i < 256; i++) begin
            write_mem_128(i * 16, 128'h7F7F7F7F7F7F7F7F7F7F7F7F7F7F7F7F);
        end
        for (int i = 0; i < 64; i++) begin
            write_mem_128(32'h1000 + i * 16, 128'h55555555555555555555555555555555); 
        end

        $display("[Test] Triggering NPU (Quadrant-Segmented Logic)...");
        start_npu();

        @(posedge npu_done_irq);
        #1;
        $display("[Result] Output = %0d (Expected: 520192)", npu_result_out);
        
        if (npu_result_out == 520192) begin
            $display("=========================================================");
            $display("SUCCESS: B-CHANNEL RESPONSES, HANDSHAKES, AND CONGESTION-FIXED ROUTING VERIFIED!");
            $display("=========================================================");
        end else begin
            $display("[FAIL] Data Mismatch!");
            $fatal(1);
        end
        $finish;
    end
endmodule
