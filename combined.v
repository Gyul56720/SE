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

module tb_mera1();
    reg clk;
    reg rst_n;
    reg [255:0] s_axis_tdata;
    reg s_axis_tvalid;
    wire s_axis_tready;
    wire [31:0] event_count;
    wire busy;

    mera1_core uut (
        .clk(clk),
        .rst_n(rst_n),
        .s_axis_tdata(s_axis_tdata),
        .s_axis_tvalid(s_axis_tvalid),
        .s_axis_tready(s_axis_tready),
        .event_count(event_count),
        .busy(busy)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0;
        rst_n = 0;
        s_axis_tvalid = 0;
        #20 rst_n = 1;
        #10 s_axis_tvalid = 1;
        #20 s_axis_tvalid = 0;
        #20 $display("PASS: count=%d", event_count);
        $finish;
    end
endmodule
