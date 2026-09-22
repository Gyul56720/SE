module mera1_core (
    clk,
    rst_n,
    s_axis_tdata,
    s_axis_tvalid,
    s_axis_tready,
    event_count,
    busy
);
    input clk;
    input rst_n;
    input [255:0] s_axis_tdata;
    input s_axis_tvalid;
    output s_axis_tready;
    output [31:0] event_count;
    output busy;

    reg [31:0] count;
    reg active;
    assign s_axis_tready = 1'b1;
    assign event_count = count;
    assign busy = active;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= 32'b0;
            active <= 1'b0;
        end else begin
            if (s_axis_tvalid) begin
                count <= count + 1'b1;
                active <= 1'b1;
            end else begin
                active <= 1'b0;
            end
        end
    end
endmodule
