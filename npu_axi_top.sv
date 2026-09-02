`timescale 1ns / 1ps
module npu_axi_top (
    input  logic clk, rst_n,
    input  logic [31:0] s_axi_csr_awaddr, s_axi_csr_awvalid, output logic s_axi_csr_awready,
    input  logic [31:0] s_axi_csr_wdata, s_axi_csr_wvalid, output logic s_axi_csr_wready,
    output logic [1:0] s_axi_csr_bresp, output logic s_axi_csr_bvalid, input logic s_axi_csr_bready,
    input  logic [31:0] s_axi_csr_araddr, s_axi_csr_arvalid, output logic s_axi_csr_arready,
    output logic [31:0] s_axi_csr_rdata, output logic [1:0] s_axi_csr_rresp, output logic s_axi_csr_rvalid, input logic s_axi_csr_rready,
    input  logic [31:0] s_axi_mem_awaddr, s_axi_mem_awvalid, output logic s_axi_mem_awready,
    input  logic [127:0] s_axi_mem_wdata, s_axi_mem_wvalid, output logic s_axi_mem_wready,
    output logic [1:0] s_axi_mem_bresp, output logic s_axi_mem_bvalid, input logic s_axi_mem_bready,
    input  logic [127:0] crypto_key,
    output logic signed [20:0] npu_result_out, output logic npu_done_irq
);
    logic signed [7:0] act_mem [4095:0];
    logic [1:0] weight_mem [4095:0];
    initial begin
        for(int i=0; i<4096; i++) begin act_mem[i]=0; weight_mem[i]=0; end
    end
    always_ff @(posedge clk) begin
        if (s_axi_mem_awvalid && s_axi_mem_wvalid) begin
            if (s_axi_mem_awaddr >= 32'h1000) begin
                for(int i=0; i<64; i++) weight_mem[(s_axi_mem_awaddr-32'h1000)*64 + i] <= (s_axi_mem_wdata[i*2 +: 2] ^ crypto_key[i*2 +: 2]);
            end else begin
                for(int i=0; i<16; i++) act_mem[s_axi_mem_awaddr*16 + i] <= s_axi_mem_wdata[i*8 +: 8];
            end
        end
    end
    logic signed [32767:0] act_flat;
    logic [8191:0] weight_flat;
    for (genvar g=0; g<4096; g++) begin
        assign act_flat[g*8 +: 8] = act_mem[g];
        assign weight_flat[g*2 +: 2] = weight_mem[g];
    end
    logic start, done; logic signed [20:0] res;
    always_ff @(posedge clk) if(s_axi_csr_awvalid && s_axi_csr_awaddr==0) start <= s_axi_csr_wdata[0]; else start <= 0;
    npu_array_4096 core (.clk(clk), .rst_n(rst_n), .act_flat(act_flat), .weight_flat(weight_flat), .valid_in(start), .Y_rtl(res), .valid_out(done));
    assign npu_result_out = res; assign npu_done_irq = done;
    assign s_axi_mem_awready = 1; assign s_axi_mem_wready = 1; assign s_axi_mem_bvalid = 1;
endmodule
