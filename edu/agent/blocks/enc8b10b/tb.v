// tb.v -- 하니스 규약에 맞춘 테스트벤치.
//   stim.txt 를 읽고 out.txt 에 16진수 한 줄씩 낸다.
//   cycles.txt 에 걸린 사이클을 적는다 (처리량 검사용).
//
// stim.txt 한 줄:  "<data 10진> <k 0|1>"
// out.txt  두 줄 (자극 한 줄마다):
//   1) {err, rd, code[9:0]}  -- rd 를 같이 싣는다.  RD 가 출력에 안 실리면
//      RD 상태기계의 결함이 값 비교에 안 잡힌다
//   2) **놀고 있는 사이클의 code_valid** -- 0 이어야 한다
//
// 2)가 왜 있나 -- 변이 점수가 시켰다
// -----------------------------------
// 첫 판은 1)만 냈다.  변이 점수 71.4 % 에 탈출 여섯 중 하나가 이것이었다:
//
//     code_valid <= valid & ~bad_k;   ->   valid | ~bad_k;
//
// 이 변이는 valid 가 0 인 사이클에 code_valid 를 **가짜로 띄운다.**  그런데
// 테스트벤치가 valid 가 1 인 사이클만 봤으므로 **아무 차이도 안 났다.**
// 자극이 놀고 있는 구간을 아예 안 밟은 것이다.
//
// 이것이 변이 점수의 쓸모다.  "틀림 0" 은 검사가 무는지 말해 주지 않는다.
`timescale 1ns/1ps
module tb;
    reg clk = 0, rst = 1, valid = 0, k = 0;
    reg [7:0] data;
    wire [9:0] code;
    wire code_valid, rd, err;

    enc8b10b dut (.clk(clk), .rst(rst), .valid(valid), .data(data), .k(k),
                  .code(code), .code_valid(code_valid), .rd(rd), .err(err));

    always #5 clk = ~clk;

    integer fi, fo, fc, rc, n, cyc;
    reg [31:0] a, b;

    // 사이클 세기.  리셋이 풀린 뒤부터 센다.
    always @(posedge clk) if (!rst) cyc = cyc + 1;

    initial begin
        n = 0; cyc = 0;
        fi = $fopen("stim.txt", "r");
        fo = $fopen("out.txt", "w");
        if (fi == 0 || fo == 0) begin $display("파일 열기 실패"); $finish; end
        repeat (4) @(posedge clk);
        rst = 0;
        repeat (2) @(posedge clk);

        rc = 2;
        while (rc == 2) begin
            rc = $fscanf(fi, "%d %d\n", a, b);
            if (rc != 2) begin end else begin
                @(negedge clk);
                data = a[7:0]; k = b[0]; valid = 1'b1;
                @(negedge clk);
                valid = 1'b0;
                @(posedge clk);
                // {err, rd, code} 를 낸다.
                $fwrite(fo, "%03x\n", {err, rd, code});
                // 그리고 **놀고 있는 사이클을 한 번 본다.**  valid 가 0 이니
                // code_valid 도 0 이어야 한다.  1 이면 눈에 띄는 값을 낸다.
                @(posedge clk);
                $fwrite(fo, "%03x\n", code_valid ? 12'hFFF : 12'h000);
                n = n + 1;
            end
        end
        $fclose(fi);
        $fclose(fo);
        fc = $fopen("cycles.txt", "w");
        $fwrite(fc, "%0d\n", cyc);
        $fclose(fc);
        $finish;
    end
endmodule
