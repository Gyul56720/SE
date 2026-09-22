module tb;
    reg clk;
    reg rst_n;
    reg load;
    reg [3:0] d;
    wire [3:0] q;

    simple_counter u0 (.clk(clk), .rst_n(rst_n), .load(load), .d(d), .q(q));

    initial begin
        $dumpfile("test.vcd"); $dumpvars(0, tb);
        clk = 0; rst_n = 0; load = 0; d = 4'h0;
        #15 rst_n = 1;
        #20 load = 1; d = 4'h5;
        #10 load = 0;
        #100;
        $display("PASS");
        $finish;
    end
    always #5 clk = ~clk;
endmodule
