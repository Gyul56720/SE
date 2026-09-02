module npu_pe (
    input  logic               clk,
    input  logic               rst_n,
    input  logic signed [7:0]  act_in,
    input  logic [1:0]         weight_in, // 00:0, 01:+1, 10:-1, 11:reserved
    input  logic               valid_in,
    output logic signed [20:0] acc_out,
    output logic               valid_out
);
    logic signed [20:0] ext_act;
    logic signed [20:0] term_val;

    assign ext_act = {{13{act_in[7]}}, act_in};

    // Combinational MUX Logic
    always_comb begin
        case (weight_in)
            2'b01:   term_val = ext_act;   // +1
            2'b10:   term_val = -ext_act;  // -1
            default: term_val = 21'sd0;    // 00 or 11 Bypass
        endcase
    end

    // 1-Cycle Pipelined Output Register
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc_out   <= 21'sd0;
            valid_out <= 1'b0;
        end else begin
            acc_out   <= term_val;
            valid_out <= valid_in;
        end
    end
endmodule
