// $_DLATCH_N_ (enable 이 낮을 때 투명) 을 LATX1 + INVX1 로 매핑한다.
// yosys 0.33 의 dfflibmap 은 래치를 안 매핑하므로 techmap 으로 직접 건다.
module \$_DLATCH_N_ (input E, input D, output Q);
  wire en_n;
  INVX1 u_inv (.A(E), .Y(en_n));
  LATX1 u_lat (.G(en_n), .D(D), .Q(Q));
endmodule
