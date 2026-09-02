module npu_pe_tb;
    logic clk, rst_n;
    logic signed [7:0] act_in;
    logic [1:0] weight_in;
    logic valid_in;
    logic signed [20:0] acc_out;
    logic valid_out;

    integer f_act, f_w;
    integer val_a, val_w;

    npu_pe dut (.*);

    initial begin
        clk = 0; forever #5 clk = ~clk;
    end

    initial begin
        f_act = $fopen("test_act.txt", "r");
        f_w = $fopen("test_w.txt", "r");
        
        $fscanf(f_act, "%d", val_a);
        $fscanf(f_w, "%d", val_w);
        act_in = val_a; // Verilog signed assignment
        weight_in = val_w[1:0];
        
        rst_n = 0; #10; rst_n = 1;
        valid_in = 1; #10;
        #10;
        $display("%d", acc_out);
        $fclose(f_act);
        $fclose(f_w);
        $finish;
    end
endmodule
