module npu_tile (
    input  logic               clk,
    input  logic               rst_n,
    input  logic signed [127:0] act_flat,
    input  logic        [31:0]  weight_flat,
    input  logic               valid_in,
    output logic signed [20:0] tile_out,
    output logic               valid_out
);
    logic signed [20:0] pe_acc [15:0];
    logic pe_valid [15:0];

    genvar i;
    generate
        for (i = 0; i < 16; i++) begin : pe_array
            npu_pe pe_inst (
                .clk(clk),
                .rst_n(rst_n),
                .act_in(act_flat[i*8 +: 8]),
                .weight_in(weight_flat[i*2 +: 2]),
                .valid_in(valid_in),
                .acc_out(pe_acc[i]),
                .valid_out(pe_valid[i])
            );
        end
    endgenerate

    // Balanced Binary Tree Reduction for 16 PEs (16 -> 8 -> 4 -> 2 -> 1)
    logic signed [20:0] stage1 [7:0];
    logic signed [20:0] stage2 [3:0];
    logic signed [20:0] stage3 [1:0];
    logic signed [20:0] stage4;

    always_comb begin
        for (int k = 0; k < 8; k++)  stage1[k] = pe_acc[2*k] + pe_acc[2*k+1];
        for (int k = 0; k < 4; k++)  stage2[k] = stage1[2*k] + stage1[2*k+1];
        for (int k = 0; k < 2; k++)  stage3[k] = stage2[2*k] + stage2[2*k+1];
        stage4 = stage3[0] + stage3[1];
    end

    assign tile_out  = stage4;
    assign valid_out = pe_valid[0];
endmodule
