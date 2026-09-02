module npu_array_256 (
    input  logic                clk,
    input  logic                rst_n,
    input  logic signed [2047:0] act_flat,    // 256 * 8-bit
    input  logic        [511:0]  weight_flat, // 256 * 2-bit
    input  logic                valid_in,
    output logic signed [20:0]  Y_rtl,
    output logic                valid_out
);
    logic signed [20:0] tile_sum [15:0];
    logic tile_valid [15:0];

    genvar i;
    generate
        for (i = 0; i < 16; i++) begin : tile_array
            npu_tile tile_inst (
                .clk(clk), .rst_n(rst_n),
                .act_flat(act_flat[i*128 +: 128]),
                .weight_flat(weight_flat[i*32 +: 32]),
                .valid_in(valid_in),
                .tile_out(tile_sum[i]),
                .valid_out(tile_valid[i])
            );
        end
    endgenerate

    logic signed [20:0] lvl1 [7:0];
    logic signed [20:0] lvl2 [3:0];
    logic signed [20:0] lvl3 [1:0];
    logic signed [20:0] lvl4;
    logic [4:0] valid_pipe;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_pipe <= '0;
            lvl4 <= '0;
        end else begin
            valid_pipe <= {valid_pipe[3:0], tile_valid[0]};
            for (int k=0; k<8; k++) lvl1[k] <= tile_sum[2*k] + tile_sum[2*k+1];
            for (int k=0; k<4; k++) lvl2[k] <= lvl1[2*k] + lvl1[2*k+1];
            for (int k=0; k<2; k++) lvl3[k] <= lvl2[2*k] + lvl2[2*k+1];
            lvl4 <= lvl3[0] + lvl3[1];
        end
    end
    assign Y_rtl = lvl4;
    assign valid_out = valid_pipe[4];
endmodule
