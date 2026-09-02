`timescale 1ns / 1ps

module npu_axi_top (
    input  logic                    clk,
    input  logic                    rst_n,

    // AXI-Lite CSR Interface
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

    // High-Bandwidth AXI Memory Interface
    input  logic [31:0]             s_axi_mem_awaddr,
    input  logic                    s_axi_mem_awvalid,
    output logic                    s_axi_mem_awready,
    input  logic [127:0]            s_axi_mem_wdata,
    input  logic                    s_axi_mem_wvalid,
    output logic                    s_axi_mem_wready,
    output logic [1:0]              s_axi_mem_bresp,
    output logic                    s_axi_mem_bvalid,
    input  logic                    s_axi_mem_bready,

    // Tessera-style Inline Crypto Key
    input  logic [127:0]            secret_crypto_key,

    output logic signed [20:0]      npu_result_out,
    output logic                    npu_done_irq
);

    // Internal Memories
    logic signed [7:0] act_mem [4095:0];
    logic        [1:0] weight_mem [4095:0];

    // Inline Crypto Engine: Real-time decryption of weights
    logic [127:0] decrypted_wdata;
    assign decrypted_wdata = s_axi_mem_wdata ^ secret_crypto_key;

    // Control registers
    logic        reg_start, reg_busy, reg_done;
    logic signed [20:0] reg_result;

    // AXI Memory Handshake
    logic r_mem_awready, r_mem_wready, r_mem_bvalid;
    assign s_axi_mem_awready = r_mem_awready;
    assign s_axi_mem_wready  = r_mem_wready;
    assign s_axi_mem_bvalid  = r_mem_bvalid;
    assign s_axi_mem_bresp   = 2'b00;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r_mem_awready <= 1'b1;
            r_mem_wready  <= 1'b1;
            r_mem_bvalid  <= 1'b0;
        end else begin
            if (s_axi_mem_awvalid && s_axi_mem_wvalid && r_mem_awready && r_mem_wready) begin
                r_mem_bvalid <= 1'b1;
                if (s_axi_mem_awaddr >= 32'h1000) begin
                    for (int i=0; i<64; i++) 
                        weight_mem[((s_axi_mem_awaddr-32'h1000)*4)+i] <= decrypted_wdata[i*2 +: 2];
                end else begin
                    for (int i=0; i<16; i++) 
                        act_mem[s_axi_mem_awaddr + i] <= s_axi_mem_wdata[i*8 +: 8];
                end
            end else if (r_mem_bvalid && s_axi_mem_bready) begin
                r_mem_bvalid <= 1'b0;
            end
        end
    end

    // CSR Handshake & Read Logic
    assign s_axi_csr_awready = 1'b1;
    assign s_axi_csr_wready  = 1'b1;
    assign s_axi_csr_bresp   = 2'b00;
    assign s_axi_csr_bvalid  = s_axi_csr_awvalid && s_axi_csr_wvalid;
    assign s_axi_csr_arready = 1'b1;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg_start <= 1'b0;
            s_axi_csr_rvalid <= 1'b0;
            s_axi_csr_rdata <= 32'h0;
        end else begin
            if (s_axi_csr_awvalid && s_axi_csr_wvalid && s_axi_csr_awaddr[7:0] == 8'h00) 
                reg_start <= s_axi_csr_wdata[0];
            else 
                reg_start <= 1'b0;

            if (s_axi_csr_arvalid) begin
                s_axi_csr_rvalid <= 1'b1;
                case (s_axi_csr_araddr[7:0])
                    8'h00: s_axi_csr_rdata <= {30'h0, reg_done, reg_busy};
                    8'h04: s_axi_csr_rdata <= {{11{reg_result[20]}}, reg_result};
                    default: s_axi_csr_rdata <= 32'h0;
                endcase
            end else if (s_axi_csr_rready) begin
                s_axi_csr_rvalid <= 1'b0;
            end
        end
    end

    // Flatten to Core
    logic signed [32767:0] act_flat;
    logic        [8191:0]  weight_flat;
    
    for (genvar g=0; g<4096; g++) begin : gen_flat
        assign act_flat[g*8 +: 8]    = act_mem[g];
        assign weight_flat[g*2 +: 2] = weight_mem[g];
    end

    npu_array_4096 core_inst (
        .clk(clk),
        .rst_n(rst_n),
        .act_flat(act_flat),
        .weight_flat(weight_flat),
        .valid_in(reg_start),
        .Y_rtl(reg_result),
        .valid_out(reg_done)
    );

    assign npu_result_out = reg_result;
    assign npu_done_irq   = reg_done;
    assign reg_busy       = 1'b0;

endmodule
