module mera1_core (
    input wire clk,
    input wire rst_n,
    input wire [255:0] s_axis_tdata,
    input wire s_axis_tvalid,
    output wire s_axis_tready,
    output wire [31:0] event_count,
    output wire busy
);
    reg [31:0] count;
    reg active;
    assign s_axis_tready = 1'b1;
    assign event_count = count;
    assign busy = active;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= 32'd0;
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
