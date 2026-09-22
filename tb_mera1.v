module tb_mera1;
    reg clk;
    reg rst_n;
    reg [255:0] s_axis_tdata;
    reg s_axis_tvalid;
    wire s_axis_tready;

    mera1_core uut (
        .clk(clk),
        .rst_n(rst_n),
        .s_axis_tdata(s_axis_tdata),
        .s_axis_tvalid(s_axis_tvalid),
        .s_axis_tready(s_axis_tready)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0; rst_n = 0; s_axis_tdata = 0; s_axis_tvalid = 0;
        #10 rst_n = 1;
        #10 s_axis_tdata = 256'hAAAA_BBBB_CCCC_DDDD_EEEE_FFFF_0000_1111_2222_3333_4444_5555_6666_7777_8888_9999;
        s_axis_tvalid = 1;
        #10;
        if (s_axis_tready) $display("PASS");
        else $display("FAIL");
        $finish;
    end
endmodule
