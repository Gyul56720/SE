// ---------------------------------------------------------------------------
// tb_dsp -- **얇은** 테스트벤치.  판단은 여기서 하지 않는다.
//
// UVM 꼴에서 이 파일이 맡는 것은 '가상 인터페이스' 자리뿐이다: 파일에서 자극을
// 받아 핀을 흔들고, 매 클럭 핀을 읽어 파일에 적는다.  무엇을 넣을지(시퀀스),
// 무엇이 맞는지(스코어보드), 무엇을 해 봤는지(커버리지)는 전부 파이썬 쪽
// (`lab/se/dv.py`)에 있다.
//
// 왜 이렇게 가르나: iverilog 는 UVM 을 못 돌린다.  그렇다고 판단까지 Verilog
// 로 옮기면 참조모델이 DUT 와 같은 언어·같은 머릿속에서 나와 **둘이 같이
// 틀리기** 쉽다.  갈라 두면 참조모델을 다른 방식으로 쓸 수 있다.
//
//   자극 파일 한 줄 = rst_n start a b   (hex, 빈칸 구분)
//
// **Verilog 식별자에 한글을 쓰지 마라** (실측: `reg [1023:0] 자극길` 에서
// iverilog 가 syntax error 를 냈다).  셸과 같은 이유다 -- 주석만 한글로 쓴다.
//   응답 파일 한 줄 = cycle state acc done
// ---------------------------------------------------------------------------
`timescale 1ns/1ps
module tb_dsp;
    parameter integer N = 4096;
    parameter W = 8;

    reg clk = 1'b0;
    reg rst_n, start_async;
    reg [W-1:0] a, b;
    wire [2*W+1:0] acc;
    wire done;
    wire [1:0] state_o;

    dsp_top #(.W(W)) dut (
        .clk(clk), .rst_n(rst_n), .start_async(start_async),
        .a(a), .b(b), .acc(acc), .done(done), .state_o(state_o));

    integer fin, fout, code, i, n;
    reg [31:0] v_rst, v_start, v_a, v_b;
    reg [1023:0] stim_path, resp_path;

    always #5 clk = ~clk;          // 100 MHz

    initial begin
        if (!$value$plusargs("stim=%s", stim_path)) stim_path = "lab/out/stim.txt";
        if (!$value$plusargs("resp=%s", resp_path)) resp_path = "lab/out/resp.txt";
        fin  = $fopen(stim_path, "r");
        fout = $fopen(resp_path, "w");
        if (fin == 0) begin $display("ERROR: cannot open stimulus file"); $finish; end

        rst_n = 1'b0; start_async = 1'b0; a = 0; b = 0;
        @(posedge clk); @(posedge clk);

        n = 0;
        for (i = 0; i < N; i = i + 1) begin
            code = $fscanf(fin, "%h %h %h %h\n", v_rst, v_start, v_a, v_b);
            if (code != 4) i = N;
            else begin
                rst_n       = v_rst[0];
                start_async = v_start[0];
                a           = v_a[W-1:0];
                b           = v_b[W-1:0];
                @(posedge clk);
                #1;                        // 핀이 안정된 뒤에 읽는다
                $fwrite(fout, "%0d %0d %0d %0d\n", n, state_o, acc, done);
                n = n + 1;
            end
        end
        $fclose(fin); $fclose(fout);
        $display("tb_dsp: %0d cycles", n);
        $finish;
    end
endmodule
