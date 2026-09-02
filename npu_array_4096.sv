`timescale 1ns / 1ps

module npu_array_4096 #(
    parameter int PIPE_STAGES = 8
)(
    input  logic                clk,
    input  logic                rst_n,
    input  logic signed [32767:0] act_flat,
    input  logic        [8191:0]  weight_flat,
    input  logic                valid_in,
    output logic signed [20:0]  Y_rtl,
    output logic                valid_out
);
    // Quadrant-Segmented Input Fanout Registers to eliminate Routing Congestion
    logic signed [8191:0] act_q0, act_q1, act_q2, act_q3;
    logic        [2047:0] weight_q0, weight_q1, weight_q2, weight_q3;
    logic                 valid_q0, valid_q1, valid_q2, valid_q3;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            act_q0    <= '0; weight_q0 <= '0; valid_q0 <= 1'b0;
            act_q1    <= '0; weight_q1 <= '0; valid_q1 <= 1'b0;
            act_q2    <= '0; weight_q2 <= '0; valid_q2 <= 1'b0;
            act_q3    <= '0; weight_q3 <= '0; valid_q3 <= 1'b0;
        end else begin
            act_q0    <= act_flat[0*8192 +: 8192];
            weight_q0 <= weight_flat[0*2048 +: 2048];
            valid_q0  <= valid_in;

            act_q1    <= act_flat[1*8192 +: 8192];
            weight_q1 <= weight_flat[1*2048 +: 2048];
            valid_q1  <= valid_in;

            act_q2    <= act_flat[2*8192 +: 8192];
            weight_q2 <= weight_flat[2*2048 +: 2048];
            valid_q2  <= valid_in;

            act_q3    <= act_flat[3*8192 +: 8192];
            weight_q3 <= weight_flat[3*2048 +: 2048];
            valid_q3  <= valid_in;
        end
    end

    logic signed [20:0] tile_sum [255:0];
    logic tile_valid [255:0];

    genvar i;
    generate
        // Quadrant 0
        for (i = 0; i < 64; i++) begin : tile_q0
            npu_tile tile_inst (
                .clk(clk),
                .rst_n(rst_n),
                .act_flat(act_q0[i*128 +: 128]),
                .weight_flat(weight_q0[i*32 +: 32]),
                .valid_in(valid_q0),
                .tile_out(tile_sum[i]),
                .valid_out(tile_valid[i])
            );
        end
        // Quadrant 1
        for (i = 64; i < 127; i++) begin : tile_q1
            npu_tile tile_inst (
                .clk(clk),
                .rst_n(rst_n),
                .act_flat(act_q1[(i-64)*128 +: 128]),
                .weight_flat(weight_q1[(i-64)*32 +: 32]),
                .valid_in(valid_q1),
                .tile_out(tile_sum[i]),
                .valid_out(tile_valid[i])
            );
        end
        // Quadrant 1 boundary tile to avoid compilation bounds issues
        npu_tile tile_q1_boundary (
            .clk(clk),
            .rst_n(rst_n),
            .act_flat(act_q1[63*128 +: 128]),
            .weight_flat(weight_q1[63*32 +: 32]),
            .valid_in(valid_q1),
            .tile_out(tile_sum[127]),
            .valid_out(tile_valid[127])
        );
        // Quadrant 2
        for (i = 128; i < 192; i++) begin : tile_q2
            npu_tile tile_inst (
                .clk(clk),
                .rst_n(rst_n),
                .act_flat(act_q2[(i-128)*128 +: 128]),
                .weight_flat(weight_q2[(i-128)*32 +: 32]),
                .valid_in(valid_q2),
                .tile_out(tile_sum[i]),
                .valid_out(tile_valid[i])
            );
        end
        // Quadrant 3
        for (i = 192; i < 256; i++) begin : tile_q3
            npu_tile tile_inst (
                .clk(clk),
                .rst_n(rst_n),
                .act_flat(act_q3[(i-192)*128 +: 128]),
                .weight_flat(weight_q3[(i-192)*32 +: 32]),
                .valid_in(valid_q3),
                .tile_out(tile_sum[i]),
                .valid_out(tile_valid[i])
            );
        end
    endgenerate

    // 8-stage Balanced Binary Reduction Registers
    logic signed [20:0] tree_lvl1 [127:0];
    logic signed [20:0] tree_lvl2 [63:0];
    logic signed [20:0] tree_lvl3 [31:0];
    logic signed [20:0] tree_lvl4 [15:0];
    logic signed [20:0] tree_lvl5 [7:0];
    logic signed [20:0] tree_lvl6 [3:0];
    logic signed [20:0] tree_lvl7 [1:0];
    logic signed [20:0] tree_lvl8;

    // 10-bit Shift Register for 100% Timing Alignment (1 cycle quadrant fanout + 1 cycle PE + 8 cycle tree)
    logic [9:0] valid_pipe;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_pipe <= 10'b0;
            for (int k = 0; k < 128; k++) tree_lvl1[k] <= 21'sd0;
            for (int k = 0; k < 64;  k++) tree_lvl2[k] <= 21'sd0;
            for (int k = 0; k < 32;  k++) tree_lvl3[k] <= 21'sd0;
            for (int k = 0; k < 16;  k++) tree_lvl4[k] <= 21'sd0;
            for (int k = 0; k < 8;   k++) tree_lvl5[k] <= 21'sd0;
            for (int k = 0; k < 4;   k++) tree_lvl6[k] <= 21'sd0;
            for (int k = 0; k < 2;   k++) tree_lvl7[k] <= 21'sd0;
            tree_lvl8 <= 21'sd0;
        end else begin
            valid_pipe <= {valid_pipe[8:0], tile_valid[0]};

            for (int k = 0; k < 128; k++) tree_lvl1[k] <= tile_sum[2*k] + tile_sum[2*k+1];
            for (int k = 0; k < 64;  k++) tree_lvl2[k] <= tree_lvl1[2*k] + tree_lvl1[2*k+1];
            for (int k = 0; k < 32;  k++) tree_lvl3[k] <= tree_lvl2[2*k] + tree_lvl2[2*k+1];
            for (int k = 0; k < 16;  k++) tree_lvl4[k] <= tree_lvl3[2*k] + tree_lvl3[2*k+1];
            for (int k = 0; k < 8;   k++) tree_lvl5[k] <= tree_lvl4[2*k] + tree_lvl4[2*k+1];
            for (int k = 0; k < 4;   k++) tree_lvl6[k] <= tree_lvl5[2*k] + tree_lvl5[2*k+1];
            for (int k = 0; k < 2;   k++) tree_lvl7[k] <= tree_lvl6[2*k] + tree_lvl6[2*k+1];
            tree_lvl8 <= tree_lvl7[0] + tree_lvl7[1];
        end
    end

    assign Y_rtl     = tree_lvl8;
    assign valid_out = valid_pipe[9];
endmodule
