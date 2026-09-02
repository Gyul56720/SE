module full_exhaustive_tb;
    logic clk, rst_n;
    logic signed [7:0] act_in;
    logic [1:0] weight_in;
    logic valid_in;
    logic signed [20:0] acc_out;
    logic valid_out;

    integer f_in, f_out;
    integer status;
    integer cur_x, cur_w_code;

    npu_pe dut (.*);

    initial begin
        clk = 0; forever #5 clk = ~clk;
    end

    initial begin
        f_in = $fopen("all_stimulus.txt", "r");
        f_out = $fopen("all_results.txt", "w");
        
        rst_n = 0;
        valid_in = 0;
        #20;
        rst_n = 1;
        #10;

        while (!$feof(f_in)) begin
            status = $fscanf(f_in, "%d %d\n", cur_x, cur_w_code);
            if (status == 2) begin
                // Reset accumulator for single operation test
                rst_n = 0; #10; rst_n = 1; #10;
                
                act_in = cur_x;
                weight_in = cur_w_code[1:0];
                valid_in = 1;
                #10;
                valid_in = 0;
                #10;
                $fdisplay(f_out, "%d %d %d", cur_x, cur_w_code, acc_out);
            end
        end

        $fclose(f_in);
        $fclose(f_out);
        $finish;
    end
endmodule
