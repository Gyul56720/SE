module automotive_fir_top (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [15:0]  x_in,
    output wire [39:0]  y_out
);

    // 8-Tap Coefficients: Dolph-Chebyshev window (approx for 40dB sidelobe attenuation)
    // Quantized to 16-bit signed integers
    // h = [1024, 4096, 12288, 16384, 16384, 12288, 4096, 1024]
    localparam [15:0] H0 = 16'sd1024;
    localparam [15:0] H1 = 16'sd4096;
    localparam [15:0] H2 = 16'sd12288;
    localparam [15:0] H3 = 16'sd16384;
    localparam [15:0] H4 = 16'sd16384;
    localparam [15:0] H5 = 16'sd12288;
    localparam [15:0] H6 = 16'sd4096;
    localparam [15:0] H7 = 16'sd1024;

    // Stage 0: Input delay line (shift register)
    reg [15:0] x0, x1, x2, x3, x4, x5, x6, x7;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            x0 <= 0; x1 <= 0; x2 <= 0; x3 <= 0;
            x4 <= 0; x5 <= 0; x6 <= 0; x7 <= 0;
        end else begin
            x0 <= x_in;
            x1 <= x0;
            x2 <= x1;
            x3 <= x2;
            x4 <= x3;
            x5 <= x4;
            x6 <= x5;
            x7 <= x6;
        end
    end

    // Stage 1: 16x16 Signed Multipliers
    reg signed [31:0] m0, m1, m2, m3, m4, m5, m6, m7;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            m0 <= 0; m1 <= 0; m2 <= 0; m3 <= 0;
            m4 <= 0; m5 <= 0; m6 <= 0; m7 <= 0;
        end else begin
            m0 <= $signed(x0) * $signed(H0);
            m1 <= $signed(x1) * $signed(H1);
            m2 <= $signed(x2) * $signed(H2);
            m3 <= $signed(x3) * $signed(H3);
            m4 <= $signed(x4) * $signed(H4);
            m5 <= $signed(x5) * $signed(H5);
            m6 <= $signed(x6) * $signed(H6);
            m7 <= $signed(x7) * $signed(H7);
        end
    end

    // Stage 2: Adder Tree Level 2 (Registered to meet 500MHz timing)
    reg signed [33:0] sum_l2_0, sum_l2_1;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sum_l2_0 <= 0;
            sum_l2_1 <= 0;
        end else begin
            sum_l2_0 <= ($signed(m0) + $signed(m1)) + ($signed(m2) + $signed(m3));
            sum_l2_1 <= ($signed(m4) + $signed(m5)) + ($signed(m6) + $signed(m7));
        end
    end

    // Stage 3: Final Accumulator / Level 3 Adder
    reg signed [39:0] y_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y_reg <= 0;
        end else begin
            y_reg <= $signed(sum_l2_0) + $signed(sum_l2_1);
        end
    end

    assign y_out = y_reg;

endmodule
