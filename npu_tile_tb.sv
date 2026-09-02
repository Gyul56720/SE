module npu_tile_tb;
    logic clk, rst_n;
    logic signed [7:0] act_in [15:0];
    logic [1:0] weight_in [15:0];
    logic valid_in;
    logic signed [20:0] tile_out;
    logic valid_out;

    integer f_in, f_out;
    integer status;
    integer cur_x [15:0];
    integer cur_w [15:0];
    integer i;

    npu_tile dut (.*);

    initial begin
        clk = 0; forever #5 clk = ~clk;
    end

    initial begin
        f_in = $fopen("tile_stimulus.txt", "r");
        f_out = $fopen("tile_results.txt", "w");

        rst_n = 0; valid_in = 0; #20;
        rst_n = 1; #10;

        while (!$feof(f_in)) begin
            // 16개 X와 16개 W 읽기
            status = $fscanf(f_in, "%d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d\n",
                cur_x[0], cur_x[1], cur_x[2], cur_x[3], cur_x[4], cur_x[5], cur_x[6], cur_x[7],
                cur_x[8], cur_x[9], cur_x[10], cur_x[11], cur_x[12], cur_x[13], cur_x[14], cur_x[15],
                cur_w[0], cur_w[1], cur_w[2], cur_w[3], cur_w[4], cur_w[5], cur_w[6], cur_w[7],
                cur_w[8], cur_w[9], cur_w[10], cur_w[11], cur_w[12], cur_w[13], cur_w[14], cur_w[15]
            );

            if (status == 32) begin
                rst_n = 0; #10; rst_n = 1; #10; // Reset PE state for single vector check
                for (i = 0; i < 16; i++) begin
                    act_in[i] = cur_x[i];
                    weight_in[i] = cur_w[i][1:0];
                end
                valid_in = 1; #10;
                valid_in = 0; #10;
                $fdisplay(f_out, "%d", tile_out);
            end
        end

        $fclose(f_in);
        $fclose(f_out);
        $finish;
    end
endmodule
