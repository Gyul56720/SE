# <블록 이름> — 통합 가이드

> **목표: 이 문서를 읽고 전화 없이 붙일 수 있게 한다.**
> 설명이 아니라 **복사해 붙일 코드**를 넣는다.

---

## 1. 파일

```
rtl/<블록>.v        합성 대상. 이것만 합성한다
tb/<블록>_tb.v      테스트벤치. 합성하지 않는다
model/golden.cpp    골든모델. 참고용
```

합성에는 `rtl/` 만 넣는다. 테스트벤치를 같이 넣으면 `$fopen` 때문에
합성이 실패한다.

## 2. 인스턴스 — 복사해서 쓴다

```verilog
<블록> #(
    .IN_W  (8),      // TODO
    .OUT_W (8)       // TODO
) u_<블록> (
    .clk       (sys_clk),     // TODO MHz 이하
    .rst       (sys_rst),     // TODO 극성, 최소 TODO 클럭
    .in_valid  (TODO),
    .in_data   (TODO),        // signed [7:0]
    .out_valid (TODO),
    .out_data  (TODO)
);
```

> 포트는 **이름으로** 잇는다. 순서로 이으면 포트가 추가될 때 조용히 어긋난다.

## 3. 리셋 시퀀스

```verilog
initial begin
    sys_rst = 1'b1;
    repeat (TODO) @(posedge sys_clk);   // 최소 TODO 클럭
    sys_rst = 1'b0;
end
```

**극성: TODO.** 반대로 넣으면 블록이 통째로 안 돈다(출력이 영영 안 나온다).
증상이 "완전히 죽은 것" 처럼 보여 원인이 멀어 보이는 고전적 함정이다.

## 4. 클럭

| 항목 | 값 |
|---|---|
| 클럭 개수 | TODO |
| 최대 주파수 | TODO MHz (소자 TODO) |
| CDC 필요? | TODO |

## 5. 데이터 넣는 법

```verilog
// TODO 예시 파형 또는 코드
// in_valid 를 1로 올리고 같은 클럭에 in_data 를 실는다.
// TODO 클럭 뒤 out_valid 와 함께 결과가 나온다.
```

back-pressure: TODO (없으면 "없음 — 매 클럭 받을 수 있다")

## 6. 직접 돌려 보기

```bash
g++ -O2 -o golden model/golden.cpp
./golden vec 400 1 > vec.txt
iverilog -g2012 -o sim.out tb/<블록>_tb.v rtl/<블록>.v
vvp sim.out          # "틀림 0" 이 나와야 한다
```

## 7. 합성

```bash
yosys -p "read_verilog -sv rtl/<블록>.v; synth_<소자> -top <블록>; stat"
```

> 합성 후 **플립플롭 수가 TODO 개**인지 확인할 것. 다르면 도구 설정이
> 다른 것이니 연락 바란다.

## 8. 자주 묻는 것

| 질문 | 답 |
|---|---|
| 리셋을 비동기로 써도 되나? | TODO |
| 클럭을 더 올리려면? | TODO (데이터패스를 넓히거나 파이프라인 추가) |
| 파라미터를 바꿔도 되나? | TODO (검증된 조합: TODO) |
| 출력이 계속 0 이다 | 리셋 극성을 확인한다. 3절 |
| 출력이 계속 x 다 | 리셋이 안 걸렸다. 최소 클럭 수 확인 |

## 9. 연락처

TODO
