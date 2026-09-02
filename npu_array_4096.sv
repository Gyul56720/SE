module npu_array_4096 (
    input  logic                clk,
    input  logic                rst_n,
    input  logic signed [32767:0] act_flat,    // 4096 * 8-bit = 32768-bit
    input  logic        [8191:0]  weight_flat, // 4096 * 2-bit = 8192-bit
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

    logic signed [20:0] sum;
    integer j;
    always_comb begin
        sum = 21'sd0;
        for (j = 0; j < 256; j++) begin
            sum = sum + tile_sum[j];
        end
    end

    assign Y_rtl = sum;
    assign valid_out = tile_valid[0];
endmodule
