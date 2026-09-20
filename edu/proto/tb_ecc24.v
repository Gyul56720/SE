`timescale 1ns/1ps
module tb;
    reg  [23:0] data_in; reg [5:0] ecc_in;
    wire [5:0]  ecc_out; wire [23:0] data_fixed;
    wire        err_single, err_double;
    ecc24 dut(.data_in(data_in), .ecc_in(ecc_in), .ecc_out(ecc_out),
              .data_fixed(data_fixed), .err_single(err_single), .err_double(err_double));
    integer fd, rc, n, bad;
    reg [31:0] a,b,c,d,e,f;
    initial begin
        n=0; bad=0;
        fd=$fopen("vec.txt","r");
        if(fd==0) begin $display("FAIL vec.txt"); $finish; end
        rc=6;
        while(rc==6) begin
            rc=$fscanf(fd,"%d %d %d %d %d %d\n",a,b,c,d,e,f);
            if(rc!=6) begin end else begin
                data_in=a[23:0]; ecc_in=b[5:0];
                #1;
                if(ecc_out!==c[5:0] || data_fixed!==d[23:0]
                   || err_single!==e[0] || err_double!==f[0]) begin
                    if(bad<6) $display("FAIL 줄 %0d: ecc %b/%b fixed %h/%h s %b/%b d %b/%b",
                        n, ecc_out, c[5:0], data_fixed, d[23:0], err_single, e[0], err_double, f[0]);
                    bad=bad+1;
                end
                n=n+1;
            end
        end
        $fclose(fd);
        $display("잰것 %0d  틀림 %0d", n, bad);
        if(n<64) $display("쓸모없음 벡터가 %0d 개뿐이다", n);
        $finish;
    end
endmodule
