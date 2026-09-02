module npu_axi_testbench;
    logic clk, rst_n;
    logic [31:0]  s_axi_awaddr;
    logic         s_axi_awvalid;
    logic         s_axi_awready;
    logic [31:0]  s_axi_wdata;
    logic         s_axi_wvalid;
    logic         s_axi_wready;
    logic [1:0]   s_axi_bresp;
    logic         s_axi_bvalid;
    logic         s_axi_bready;

    logic [31:0]  s_axi_mem_awaddr;
    logic [127:0] s_axi_mem_wdata;
    logic         s_axi_mem_wvalid;
    logic         s_axi_mem_wready;

    logic [20:0]  npu_result_out;
    logic         npu_done_irq;

    npu_axi_top dut (.*);

    initial begin clk = 0; forever #5 clk = ~clk; end

    task axi_write_mem(input [31:0] addr, input [127:0] data);
        s_axi_mem_awaddr = addr;
        s_axi_mem_wdata = data;
        s_axi_mem_wvalid = 1;
        @(posedge clk);
        while(!s_axi_mem_wready) @(posedge clk);
        s_axi_mem_wvalid = 0;
    endtask

    task axi_write_ctrl(input [31:0] addr, input [31:0] data);
        s_axi_awaddr = addr;
        s_axi_wdata = data;
        s_axi_awvalid = 1;
        s_axi_wvalid = 1;
        @(posedge clk);
        s_axi_awvalid = 0;
        s_axi_wvalid = 0;
    endtask

    integer f_act, f_w;
    logic [7:0]  tmp_byte;
    logic [1:0]  tmp_ternary;
    logic [127:0] tmp_data;
    integer i, j;

    initial begin
        rst_n = 0; s_axi_awvalid = 0; s_axi_wvalid = 0; s_axi_mem_wvalid = 0;
        #20; rst_n = 1; #20;

        // 1. Load Activation Data (4096 bytes)
        f_act = $fopen("array_act_hex.txt", "r");
        for (i=0; i<256; i++) begin
            for (j=0; j<16; j++) begin
                $fscanf(f_act, "%h", tmp_byte);
                tmp_data[j*8 +: 8] = tmp_byte;
            end
            axi_write_mem(i*16, tmp_data);
        end
        $fclose(f_act);

        // 2. Load Weight Data (4096 * 2 bits = 1024 bytes)
        f_w = $fopen("array_w_hex.txt", "r");
        for (i=0; i<64; i++) begin
            for (j=0; j<64; j++) begin
                $fscanf(f_w, "%b", tmp_ternary);
                tmp_data[j*2 +: 2] = tmp_ternary;
            end
            axi_write_mem(32'h1000 + i*16, tmp_data);
        end
        $fclose(f_w);

        // 3. Trigger Start
        axi_write_ctrl(32'h2000, 32'h1);

        // 4. Wait for Done
        wait(npu_done_irq);
        $display("RESULT: %d", npu_result_out);
        #20;
        $finish;
    end
endmodule
