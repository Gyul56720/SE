module npu_axi_top #(
    parameter int DATA_WIDTH = 128,
    parameter int ADDR_WIDTH = 32
)(
    input  logic                    clk,
    input  logic                    rst_n,

    // AXI4-Lite Slave Interface
    input  logic [ADDR_WIDTH-1:0]   s_axi_awaddr,
    input  logic                    s_axi_awvalid,
    output logic                    s_axi_awready,
    input  logic [31:0]             s_axi_wdata,
    input  logic                    s_axi_wvalid,
    output logic                    s_axi_wready,
    output logic [1:0]              s_axi_bresp,
    output logic                    s_axi_bvalid,
    input  logic                     s_axi_bready,

    // AXI4 Full Slave Interface
    input  logic [ADDR_WIDTH-1:0]   s_axi_mem_awaddr,
    input  logic [DATA_WIDTH-1:0]   s_axi_mem_wdata,
    input  logic                    s_axi_mem_wvalid,
    output logic                    s_axi_mem_wready,

    output logic [20:0]             npu_result_out,
    output logic                    npu_done_irq
);

    logic [7:0]  act_mem [4095:0];
    logic [1:0]  weight_mem [4095:0];

    logic [32767:0] act_flat;
    logic [8191:0]  weight_flat;
    logic           npu_start;
    logic           npu_done;
    logic [20:0]    npu_result;

    // Fixed Memory Mapping Logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i=0; i<4096; i++) begin
                act_mem[i] <= 8'd0;
                weight_mem[i] <= 2'b0;
            end
        end else if (s_axi_mem_wvalid && s_axi_mem_wready) begin
            if (s_axi_mem_awaddr < 32'h1000) begin
                // s_axi_mem_awaddr는 바이트 주소이므로 그대로 사용 가능 (0, 16, 32...)
                for (int i=0; i<16; i++) act_mem[s_axi_mem_awaddr + i] <= s_axi_mem_wdata[i*8 +: 8];
            end else if (s_axi_mem_awaddr >= 32'h1000 && s_axi_mem_awaddr < 32'h1400) begin
                // Weight 주소는 0x1000부터 시작. 
                // 주소당 128비트(64개 Ternary)가 들어옴. 
                // (addr - 1000) 은 바이트 오프셋. 1바이트당 4개 가중치.
                for (int i=0; i<64; i++) weight_mem[(s_axi_mem_awaddr - 32'h1000)*4 + i] <= s_axi_mem_wdata[i*2 +: 2];
            end
        end
    end

    genvar g;
    generate
        for (g=0; g<4096; g++) begin : flat_map
            assign act_flat[g*8 +: 8]      = act_mem[g];
            assign weight_flat[g*2 +: 2]   = weight_mem[g];
        end
    endgenerate

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            npu_start <= 1'b0;
            s_axi_awready <= 1'b1;
            s_axi_wready <= 1'b1;
        end else if (s_axi_awvalid && s_axi_awready && s_axi_awaddr == 32'h2000) begin
            npu_start <= s_axi_wdata[0];
        end else begin
            npu_start <= 1'b0;
        end
    end

    npu_array_4096 #(.PIPE_STAGES(8)) core (
        .clk(clk),
        .rst_n(rst_n),
        .act_flat(act_flat),
        .weight_flat(weight_flat),
        .valid_in(npu_start),
        .Y_rtl(npu_result),
        .valid_out(npu_done)
    );

    assign npu_result_out = npu_result;
    assign npu_done_irq   = npu_done;
    assign s_axi_mem_wready = 1'b1;

    // Status and Response logic (Simplified)
    assign s_axi_bresp = 2'b00;
    assign s_axi_bvalid = 1'b1;

endmodule
