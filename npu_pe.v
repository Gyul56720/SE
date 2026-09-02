// NPU Processing Element (PE) - Ternary Logic Unit
// Weights: {-1, 0, 1}, Activation: 8-bit Signed, Accumulator: 16-bit Signed
// No multiplier, MUX-based Add/Sub Tree

module npu_pe (
    input wire clk,
    input wire rst_n,
    input wire signed [7:0]  act_in,      // 활성화 값 (Input Activation)
    input wire signed [1:0]  weight_in,   // 가중치 {-1, 0, 1} (2-bit signed: -1=11, 0=00, 1=01)
    input wire               valid_in,
    output reg signed [15:0] acc_out,     // 16-bit 누산기 결과
    output reg               valid_out
);

    // 16-bit signed internal accumulator
    reg signed [15:0] acc;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc <= 16'd0;
            valid_out <= 1'b0;
        end else if (valid_in) begin
            // Ternary Logic based on Weight
            // 00: weight=0 -> pass
            // 01: weight=1 -> acc = acc + act
            // 11: weight=-1 -> acc = acc - act
            case (weight_in)
                2'b01: acc <= acc + $signed(act_in);
                2'b11: acc <= acc - $signed(act_in);
                default: acc <= acc; // weight 0 or undefined: stall/skip
            endcase
            valid_out <= 1'b1;
        end else begin
            valid_out <= 1'b0;
        end
    end

    // Assign to output
    always @(*) begin
        acc_out = acc;
    end

endmodule
