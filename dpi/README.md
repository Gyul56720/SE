# DPI-C 레퍼런스 모델 -- SystemVerilog 가 C++ 골든을 부른다

`ldpcrtl.cnu()` 가 낸 Verilog 를, **C++ 로 쓴 비트정확 레퍼런스**와 매 벡터 맞댄다.

    cnu_ref.cpp   C++ 레퍼런스 (nrldpcfix / ldpcrtl.골든CNU 와 같은 식)
    cnu_tb.sv     SystemVerilog 벤치. import "DPI-C" 로 위를 부른다

## 돌리는 법

    python3 -c "import ldpcrtl; open('/tmp/cnu.v','w').write(ldpcrtl.cnu(4,6))"
    verilator --binary --timing --top-module cnu_tb dpi/cnu_tb.sv /tmp/cnu.v dpi/cnu_ref.cpp -o sim
    ./obj_dir/sim

## 실측 (2026-09-18)

    PASS  2000 vectors, RTL == C++ DPI reference
    RTL 을 틀리게(min1/min2 뒤바꿈)  -> 벡터 번호까지 찍어 잡는다
    C++ 를 틀리게(3/4 -> 4/4)        -> 역시 잡는다
    파이썬 골든 vs C++  3000 벡터    -> 불일치 0

**세 언어가 같은 답을 낸다: 파이썬 == C++ == Verilog.**

## 시뮬레이터 지원 (실측)

    verilator 5.020   import "DPI-C" 를 그대로 받고 C++ 를 같이 컴파일한다   OK
    iverilog          import "DPI-C" 에서 syntax error -- VPI 로 따로 붙여야 한다

## 실무에서 터지는 자리 넷

1. **부호 확장.** SV 의 `signed [5:0]` 을 DPI 의 `int` 로 넘길 때 `int'()` 캐스팅을
   빼면 **0-확장**되어 음수가 큰 양수가 된다. 조용히 틀린다. 이 벤치가 캐스팅을 한다
2. **32비트 넘는 폭.** `int` 로는 안 되고 `svBitVecVal` 배열로 넘겨야 한다
3. **상태.** DPI 함수가 `static` 을 들고 있으면 여러 인스턴스가 **공유**한다.
   레퍼런스 모델은 되도록 순수 함수로 둔다 (이 파일이 그렇다)
4. **C 가 SV 를 되부르려면** `context` 키워드가 필요하다

## UVM 의 DPI 와 다른 것이다

UVM 공식 소스(`uvm_dpi.cc`, 2,658 바이트)의 DPI 는 **인프라 글루**다 --
`uvm_hdl_read/deposit/force`(레지스터 백도어) · `uvm_re_comp/exec`(SV 에 정규식이
없어서 C 것을 빌림) · 툴 이름/커맨드라인. **알고리즘 모델이 아니다.**

레퍼런스 모델은 UVM 이 주는 것이 아니라 **프로젝트마다 직접 붙이는 것**이고,
이 폴더가 그 예다.
