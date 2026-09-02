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
    output logic [1:0]              s_axi_mem_bresp,
    output logic                    s_axi_mem_bvalid,
    input  logic                    s_axi_mem_bready,

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

    // AXI-Lite Registered Handshaking to prevent combinational loops & incorrect ready assumptions
    logic r_csr_awready, r_csr_wready, r_csr_bvalid;
    logic r_csr_arready, r_csr_rvalid;
    logic [31:0] r_csr_rdata;

    assign s_axi_csr_awready = r_csr_awready;
    assign s_axi_csr_wready  = r_csr_wready;
    assign s_axi_csr_bresp   = 2'b00;
    assign s_axi_csr_bvalid  = r_csr_bvalid;

    assign s_axi_csr_arready = r_csr_arready;
    assign s_axi_csr_rresp   = 2'b00;
    assign s_axi_csr_rvalid  = r_csr_rvalid;
    assign s_axi_csr_rdata   = r_csr_rdata;

    // AWREADY & WREADY handshake logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r_csr_awready <= 1'b1;
            r_csr_wready  <= 1'b1;
        end else begin
            if (s_axi_csr_awvalid && r_csr_awready) r_csr_awready <= 1'b0;
            else if (r_csr_bvalid && s_axi_csr_bready) r_csr_awready <= 1'b1;

            if (s_axi_csr_wvalid && r_csr_wready) r_csr_wready <= 1'b0;
            else if (r_csr_bvalid && s_axi_csr_bready) r_csr_wready <= 1'b1;
        end
    end

    // BVALID response logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r_csr_bvalid <= 1'b1; // FAULT INJECTED
        end else begin
            if (s_axi_csr_awvalid && s_axi_csr_wvalid && r_csr_awready && r_csr_wready) begin
                r_csr_bvalid <= 1'b1;
            end else if (r_csr_bvalid && s_axi_csr_bready) begin
                r_csr_bvalid <= 1'b1; // FAULT INJECTED
            end
        end
    end

    // ARREADY read address handshake
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r_csr_arready <= 1'b1;
        end else begin
            if (s_axi_csr_arvalid && r_csr_arready) r_csr_arready <= 1'b0;
            else if (r_csr_rvalid && s_axi_csr_rready) r_csr_arready <= 1'b1;
        end
    end

    // RVALID & RDATA Retention logic:
    // Once RVALID goes high, it and RDATA MUST remain stable until s_axi_csr_rready is asserted.
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r_csr_rdata  <= 32'h0;
            r_csr_rvalid <= 1'b0;
        end else begin
            if (s_axi_csr_arvalid && r_csr_arready) begin
                r_csr_rvalid <= 1'b1;
                case (s_axi_csr_araddr[7:0])
                    8'h00: r_csr_rdata <= {30'h0, reg_done, reg_busy};
                    8'h04: r_csr_rdata <= {{11{reg_result[20]}}, reg_result};
                    8'h08: r_csr_rdata <= cycle_cnt;
                    default: r_csr_rdata <= 32'h0;
                endcase
            end else if (r_csr_rvalid && s_axi_csr_rready) begin
                r_csr_rvalid <= 1'b0;
            end
        end
    end

    // CSR Write control register
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg_start <= 1'b0;
        end else if (s_axi_csr_awvalid && s_axi_csr_wvalid && r_csr_awready && r_csr_wready && (s_axi_csr_awaddr[7:0] == 8'h00)) begin
            reg_start <= s_axi_csr_wdata[0];
        end else begin
            reg_start <= 1'b0;
        end
    end

    // High-Bandwidth AXI Memory Write Response (B-Channel) Support & Handshaking
    logic r_mem_awready, r_mem_wready, r_mem_bvalid;
    assign s_axi_mem_awready = r_mem_awready;
    assign s_axi_mem_wready  = r_mem_wready;
    assign s_axi_mem_bresp   = 2'b00;
    assign s_axi_mem_bvalid  = r_mem_bvalid;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r_mem_awready <= 1'b1;
            r_mem_wready  <= 1'b1;
        end else begin
            if (s_axi_mem_awvalid && r_mem_awready) r_mem_awready <= 1'b0;
            else if (r_mem_bvalid && s_axi_mem_bready) r_mem_awready <= 1'b1;

            if (s_axi_mem_wvalid && r_mem_wready) r_mem_wready <= 1'b0;
            else if (r_mem_bvalid && s_axi_mem_bready) r_mem_wready <= 1'b1;
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r_mem_bvalid <= 1'b0;
        end else begin
            if (s_axi_mem_awvalid && s_axi_mem_wvalid && r_mem_awready && r_mem_wready) begin
                r_mem_bvalid <= 1'b1;
            end else if (r_mem_bvalid && s_axi_mem_bready) begin
                r_mem_bvalid <= 1'b0;
            end
        end
    end

    // D-FlipFlop Inferencing for memory writes (No Latches)
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i = 0; i < 4096; i++) begin
                act_mem[i]    <= 8'sh0;
                weight_mem[i] <= 2'b00;
            end
        end else if (s_axi_mem_wvalid && s_axi_mem_awvalid && r_mem_awready && r_mem_wready) begin
            if (s_axi_mem_awaddr < 32'h1000) begin
                // Activation Memory (Addr: 0x000 ~ 0xFFF)
                for (int i = 0; i < 16; i++) begin
                    if ((s_axi_mem_awaddr + i) < 4096) begin
                        act_mem[s_axi_mem_awaddr + i] <= s_axi_mem_wdata[i*8 +: 8];
                    end
                end
            end else if (s_axi_mem_awaddr >= 32'h1000 && s_axi_mem_awaddr < 32'h1400) begin
                // Weight Memory (Addr: 0x1000 ~ 0x13FF)
                // Use registered base calculation instead of in-always temporary variable to avoid latches
                for (int i = 0; i < 64; i++) begin
                    if ((((s_axi_mem_awaddr - 32'h1000) * 4) + i) < 4096) begin
                        weight_mem[((s_axi_mem_awaddr - 32'h1000) * 4) + i] <= s_axi_mem_wdata[i*2 +: 2];
                    end
                end
            end
        end
    end

    // Operand Gating & Clock Gating: Prevent any combinational transitions in PEs during Idle
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

    // NPU Array 4096 Core Instance (Internally contains Quadrant-Segmented Routing to prevent Routing Congestion)
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
