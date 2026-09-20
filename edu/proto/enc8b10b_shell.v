// enc8b10b_shell.v -- 타이밍 껍데기.  Fmax 를 재려면 필요하다.
//
// `enc8b10b` 는 출력을 이미 레지스터에 담지만 **입력은 핀에서 온다.**
// 그러면 진짜 임계경로(data -> 표 mux -> code 레지스터)가 제약 없는
// I/O 경로가 되어 nextpnr 이 안 센다.  Part Z15 에서 이것 때문에
// 324 MHz 라는 뜻 없는 수를 얻었다.  입력을 레지스터로 끊는다.
module enc8b10b_shell (
    input        clk,
    input        rst,
    input        valid_i,
    input  [7:0] data_i,
    input        k_i,
    output reg [9:0] code_o,
    output reg       code_valid_o,
    output reg       rd_o,
    output reg       err_o
);
    reg       valid_q, k_q;
    reg [7:0] data_q;
    always @(posedge clk) begin
        valid_q <= valid_i;  data_q <= data_i;  k_q <= k_i;
    end

    wire [9:0] code_w;
    wire cv_w, rd_w, err_w;
    enc8b10b dut (.clk(clk), .rst(rst), .valid(valid_q), .data(data_q), .k(k_q),
                  .code(code_w), .code_valid(cv_w), .rd(rd_w), .err(err_w));

    always @(posedge clk) begin
        code_o <= code_w;  code_valid_o <= cv_w;  rd_o <= rd_w;  err_o <= err_w;
    end
endmodule
