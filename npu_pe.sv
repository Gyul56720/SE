module npu_pe (
    input  logic               clk,
    input  logic               rst_n,
    input  logic signed [7:0]  act_in,
    input  logic [1:0]         weight_in,
    input  logic               valid_in,
    output logic signed [20:0] acc_out,
    output logic               valid_out
);
    logic signed [20:0] acc;
    wire signed [20:0] ext_act;

    assign ext_act = {{13{act_in[7]}}, act_in};

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc <= 21'sd0;
            valid_out <= 1'b0;
        end else if (valid_in) begin
            case (weight_in)
                2'b01:   acc <= acc + ext_act; // +1: Add
                2'b10:   acc <= acc - ext_act; // -1: Sub
                default: acc <= acc;           //  0, 11: Bypass
            endcase
            valid_out <= 1'b1;
        end else begin
            valid_out <= 1'b0;
        end
    end

    assign acc_out = acc;
endmodule
