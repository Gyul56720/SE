`timescale 1ns / 1ps

module npu_axi_top (
    input  logic                    clk,
    input  logic                    rst_n,

    // AXI-Lite Control/Status Register (CSR) Interface
    input  logic [31:0]             s_axi_csr_awaddr,
    input  logic                    s_axi_csr_awvalid,
    output logic                    s_axi_csr_awready,
    input  logic [31:0]             s_axi_csr_wdata,
    input  logic                    s_axi_csr_wvalid,
    output logic                    s_axi_csr_wready,
    output logic [1:0]              s_axi_csr_bresp,
    output logic                    s_axi_csr_bvalid,
    input  logic                    s_axi_csr_bready,

    input  logic [31:0]             s_axi_csr_araddr,
    input  logic                    s_axi_csr_arvalid,
    output logic                    s_axi_csr_arready,
    output logic [31:0]             s_axi_csr_rdata,
    output logic [1:0]              s_axi_csr_rresp,
    output logic                    s_axi_csr_rvalid,
    input  logic                    s_axi_csr_rready,

    // High-Bandwidth AXI Memory Write Interface (128-bit data bus)
    input  logic [31:0]             s_axi_mem_awaddr,
    input  logic                    s_axi_mem_awvalid,
    output logic                    s_axi_mem_awready,
    input  logic [127:0]            s_axi_mem_wdata,
    input  logic                    s_axi_mem_wvalid,
    output logic                    s_axi_mem_wready,

    // Interrupt / Result Direct Ports
    output logic signed [20:0]      npu_result_out,
    output logic                    npu_done_irq
);

    // 4096 INT8 Activations (4KB) & 4096 2-bit Weights (1KB)
    logic signed [7:0] act_mem [4095:0];
    logic        [1:0] weight_mem [4095:0];

    logic signed [32767:0] act_flat_reg;
    logic        [8191:0]  weight_flat_reg;

    // Control & Status Signals
    logic        reg_start;
    logic        reg_busy;
    logic        reg_done;
    logic signed [20:0] reg_result;
    logic [31:0] cycle_cnt;

    // AXI-Lite Handshake Logic
    assign s_axi_csr_awready = 1'b1;
    assign s_axi_csr_wready  = 1'b1;
    assign s_axi_csr_bresp   = 2'b00;
    assign s_axi_csr_bvalid  = s_axi_csr_awvalid && s_axi_csr_wvalid;

    assign s_axi_csr_arready = 1'b1;
    assign s_axi_csr_rresp   = 2'b00;

    // CSR Read logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s_axi_csr_rdata  <= 32'h0;
            s_axi_csr_rvalid <= 1'b0;
        end else if (s_axi_csr_arvalid && s_axi_csr_arready) begin
            s_axi_csr_rvalid <= 1'b1;
            case (s_axi_csr_araddr[7:0])
                8'h00: s_axi_csr_rdata <= {30'h0, reg_done, reg_busy}; // Status Register
                8'h04: s_axi_csr_rdata <= {{11{reg_result[20]}}, reg_result}; // Result Output
                8'h08: s_axi_csr_rdata <= cycle_cnt; // Cycle Counter
                default: s_axi_csr_rdata <= 32'h0;
            endcase
        end else if (s_axi_csr_rready) begin
            s_axi_csr_rvalid <= 1'b0;
        end
    end

    // CSR Write logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg_start <= 1'b0;
        end else if (s_axi_csr_awvalid && s_axi_csr_wvalid && (s_axi_csr_awaddr[7:0] == 8'h00)) begin
            reg_start <= s_axi_csr_wdata[0];
        end else begin
            reg_start <= 1'b0; // Pulse start
        end
    end

    // AXI Memory Slave Logic for Activations and Weights
    assign s_axi_mem_awready = 1'b1;
    assign s_axi_mem_wready  = 1'b1;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i = 0; i < 4096; i++) begin
                act_mem[i]    <= 8'sh0;
                weight_mem[i] <= 2'b00;
            end
        end else if (s_axi_mem_wvalid && s_axi_mem_awvalid) begin
            if (s_axi_mem_awaddr < 32'h1000) begin
                // Activation Memory (Addr: 0x000 ~ 0xFFF)
                for (int i = 0; i < 16; i++) begin
                    if ((s_axi_mem_awaddr + i) < 4096)
                        act_mem[s_axi_mem_awaddr + i] <= s_axi_mem_wdata[i*8 +: 8];
                end
            end else if (s_axi_mem_awaddr >= 32'h1000 && s_axi_mem_awaddr < 32'h1400) begin
                // Weight Memory (Addr: 0x1000 ~ 0x13FF)
                logic [31:0] w_base;
                w_base = (s_axi_mem_awaddr - 32'h1000) * 4;
                for (int i = 0; i < 64; i++) begin
                    if ((w_base + i) < 4096)
                        weight_mem[w_base + i] <= s_axi_mem_wdata[i*2 +: 2];
                end
            end
        end
    end

    // Power Optimization / Operand Gating:
    // Only latch memory into core operand registers when `reg_start` is triggered.
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            act_flat_reg    <= '0;
            weight_flat_reg <= '0;
        end else if (reg_start) begin
            for (int j = 0; j < 4096; j++) begin
                act_flat_reg[j*8 +: 8]    <= act_mem[j];
                weight_flat_reg[j*2 +: 2] <= weight_mem[j];
            end
        end
    end

    // NPU Array 4096 Core Instance
    logic signed [20:0] core_out;
    logic               core_valid_out;

    npu_array_4096 core_inst (
        .clk(clk),
        .rst_n(rst_n),
        .act_flat(act_flat_reg),
        .weight_flat(weight_flat_reg),
        .valid_in(reg_start),
        .Y_rtl(core_out),
        .valid_out(core_valid_out)
    );

    // Status Tracking & FSM
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg_busy   <= 1'b0;
            reg_done   <= 1'b0;
            reg_result <= 21'sh0;
            cycle_cnt  <= 32'h0;
        end else begin
            if (reg_start) begin
                reg_busy  <= 1'b1;
                reg_done  <= 1'b0;
                cycle_cnt <= 32'h0;
            end else if (reg_busy) begin
                cycle_cnt <= cycle_cnt + 1;
                if (core_valid_out) begin
                    reg_busy   <= 1'b0;
                    reg_done   <= 1'b1;
                    reg_result <= core_out;
                end
            end
        end
    end

    assign npu_result_out = reg_result;
    assign npu_done_irq   = reg_done;

endmodule
