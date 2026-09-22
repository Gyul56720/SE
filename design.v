module mera1_core (
    input clk,
    input rst_n,
    input [255:0] s_axis_tdata,
    input s_axis_tvalid,
    output s_axis_tready
);
    assign s_axis_tready = 1'b1;
endmodule
