module npu_tile (
    input  logic               clk,
    input  logic               rst_n,
    input  logic signed [127:0] act_flat,    // 16 * 8-bit = 128-bit packed
    input  logic        [31:0]  weight_flat, // 16 * 2-bit = 32-bit packed
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

    logic signed [20:0] sum;
    integer j;
    always_comb begin
        sum = 21'sd0;
        for (j = 0; j < 16; j++) begin
            sum = sum + pe_acc[j];
        end
    end

    assign tile_out = sum;
    assign valid_out = pe_valid[0];
endmodule
