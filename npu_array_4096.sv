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
    logic signed [20:0] tile_sum [255:0];
    logic tile_valid [255:0];

    genvar i;
    generate
        for (i = 0; i < 256; i++) begin : tile_array
            npu_tile tile_inst (
                .clk(clk),
                .rst_n(rst_n),
                .act_flat(act_flat[i*128 +: 128]),
                .weight_flat(weight_flat[i*32 +: 32]),
                .valid_in(valid_in),
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

    // 9-bit Shift Register for 100% Timing Alignment
    logic [8:0] valid_pipe;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_pipe <= 9'b0;
            for (int k = 0; k < 128; k++) tree_lvl1[k] <= 21'sd0;
            for (int k = 0; k < 64;  k++) tree_lvl2[k] <= 21'sd0;
            for (int k = 0; k < 32;  k++) tree_lvl3[k] <= 21'sd0;
            for (int k = 0; k < 16;  k++) tree_lvl4[k] <= 21'sd0;
            for (int k = 0; k < 8;   k++) tree_lvl5[k] <= 21'sd0;
            for (int k = 0; k < 4;   k++) tree_lvl6[k] <= 21'sd0;
            for (int k = 0; k < 2;   k++) tree_lvl7[k] <= 21'sd0;
            tree_lvl8 <= 21'sd0;
        end else begin
            valid_pipe <= {valid_pipe[7:0], tile_valid[0]};

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
    assign valid_out = valid_pipe[8]; // 정확히 9사이클째 출력
endmodule
