module test_debug;
    logic signed [7:0] act;
    logic signed [20:0] ext;
    logic signed [20:0] acc;

    initial begin
        act = -8'sd128;
        ext = {{13{act[7]}}, act};
        acc = 21'sd0 - ext;
        $display("act = %d, ext = %d, acc = %d", act, ext, acc);
    end
endmodule
