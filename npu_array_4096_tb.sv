module npu_array_4096_tb;
    logic clk, rst_n;
    logic signed [32767:0] act_flat;
    logic        [8191:0]  weight_flat;
    logic valid_in;
    logic signed [20:0] Y_rtl;
    logic valid_out;

    integer f_act, f_w, f_out;
    integer status_a, status_w;
    integer val_a, val_w;
    integer i;

    npu_array_4096 dut (.*);

    initial begin
        clk = 0; forever #5 clk = ~clk;
    end

    initial begin
        f_act = $fopen("array_act.txt", "r");
        f_w = $fopen("array_w.txt", "r");
        f_out = $fopen("array_results.txt", "w");

        rst_n = 0; valid_in = 0; #20;
        rst_n = 1; #10;

        while (!$feof(f_act) && !$feof(f_w)) begin
            rst_n = 0; #10; rst_n = 1; #10;
            
            for (i = 0; i < 4096; i++) begin
                status_a = $fscanf(f_act, "%d", val_a);
                status_w = $fscanf(f_w, "%d", val_w);
                act_flat[i*8 +: 8] = val_a[7:0];
                weight_flat[i*2 +: 2] = val_w[1:0];
            end

            valid_in = 1; #10;
            valid_in = 0; #10;
            $fdisplay(f_out, "%d", Y_rtl);
        end

        $fclose(f_act);
        $fclose(f_w);
        $fclose(f_out);
        $finish;
    end
endmodule
