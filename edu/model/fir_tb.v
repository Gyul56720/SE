// fir_tb.v -- 손RTL 과 HLS 가 낸 RTL 을 **같은 벡터로** 잰다.
//
//     iverilog -g2012 -DDUT=fir4_hand      -o a.out fir_tb.v fir4_hand.v
//     iverilog -g2012 -DDUT=fir_top_tuned  -o a.out fir_tb.v fir_top_tuned.v
//
// 인터페이스를 맞춰 뒀으므로 테스트벤치가 하나면 된다.  DUT 이름만 바꾼다.
`timescale 1ns/1ps
`ifndef DUT
 `define DUT fir4_hand
`endif
module tb;
    reg clock = 0, reset = 1, start_port = 0;
    reg signed [7:0] x0, x1, x2, x3;
    wire done_port;
    wire signed [7:0] return_port;

    `DUT dut (.clock(clock), .reset(reset), .start_port(start_port),
              .x0(x0), .x1(x1), .x2(x2), .x3(x3),
              .done_port(done_port), .return_port(return_port));

    always #5 clock = ~clock;

    integer fd, rc, i, got, exp, bad, n;
    reg signed [31:0] a, b, c, d, e;

    initial begin
        bad = 0; n = 0;
        fd = $fopen("vec.txt", "r");
        if (fd == 0) begin $display("FAIL vec.txt 를 못 연다"); $finish; end

        // 리셋을 **여러 사이클** 준다.  한 사이클만 주면 HLS 가 낸 FSM 이
        // 초기 상태로 안 간다 -- 실측으로 그랬다.
        repeat (4) @(posedge clock);
        reset = 0;
        // 리셋을 뗀 뒤에도 **여러 사이클을 준다**.  실측: 한 사이클만 주면
        // HLS 가 낸 FSM 이 첫 `start_port` 를 놓쳐서 **첫 벡터 하나만**
        // done 을 안 냈다 (나머지 399 개는 다 맞았다).  하나만 틀리는 결함은
        // "가끔 틀린다" 로 읽혀 몇 주를 먹는다 -- 여기서 죽인다.
        repeat (4) @(posedge clock);

        // `disable <라벨>` 로 빠져나가지 않는다 -- 아직 시작 안 한 블록을
        // disable 하는 것은 시뮬레이터마다 뜻이 다르다.  평범한 플래그를 쓴다.
        rc = 5;
        while (rc == 5) begin
            rc = $fscanf(fd, "%d %d %d %d %d\n", a, b, c, d, e);
            if (rc != 5) begin end else begin
            // 자극은 negedge 에 넣는다.  posedge 에 넣고 posedge 에 재면
            // 경주가 난다 -- 이 저장소가 crc32_stream 에서 이미 물린 자리다.
            @(negedge clock);
            x0 = a[7:0]; x1 = b[7:0]; x2 = c[7:0]; x3 = d[7:0];
            start_port = 1;
            @(negedge clock);
            start_port = 0;
            // done 을 기다린다.  손RTL 은 1사이클, HLS 는 여러 사이클일 수 있다.
            // **기다리지 않고 고정 사이클을 세면 둘 중 하나가 틀린다.**
            i = 0;
            while (done_port !== 1'b1 && i < 64) begin @(posedge clock); i = i + 1; end
            if (i >= 64) begin
                $display("FAIL done_port 가 64 사이클 안에 안 왔다 (줄 %0d)", n);
                bad = bad + 1;
            end else begin
                got = $signed(return_port);
                exp = $signed(e[7:0]);
                if (got !== exp) begin
                    if (bad < 8)
                        $display("FAIL x=%0d,%0d,%0d,%0d  기대 %0d  얻음 %0d", a,b,c,d, exp, got);
                    bad = bad + 1;
                end
            end
            n = n + 1;
            end
        end
        $fclose(fd);
        $display("잰것 %0d  틀림 %0d", n, bad);
        if (n < 16) $display("쓸모없음 벡터가 %0d 개뿐이다", n);
        $finish;
    end
endmodule
