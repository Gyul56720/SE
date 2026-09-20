# 실무 HLS 코드 아키텍처 분석 -- 블록 IP 셋

받아 온 11,900줄을 **코드 수준으로** 읽었다. 무엇을 하는 회로이고, 설계 결정이
코드의 어디에 드러나는가.

---

## ① Cholesky 분해기 -- AMD Vitis Solver, 732줄

**제품에서의 자리** MIMO 검출 · 레이더 빔포밍 · 칼만 필터 · 금융 상관행렬
**계약** `int cholesky(hls::stream<In>& A, hls::stream<Out>& L)` -- A = L·L^H

### 같은 수학, 회로 셋

| ARCH | 함수 | 무엇이 다른가 |
|---|---|---|
| 0 | `choleskyBasic` | 자원 최소, 지연 최대 |
| 1 | `choleskyAlt` | 삼각행렬을 **1D 패킹** `L_internal[(N²-N)/2]` -- 메모리 절반. 대신 주소 계산 |
| 2 | `choleskyAlt2` | **2D 로 되돌림.** 부분합 배열 + `ARRAY_PARTITION cyclic` + `UNROLL FACTOR` |

### 코드에 드러난 설계 결정 다섯

**1. 주소 계산이 II 를 막으면 메모리를 더 써서 없앤다**

ARCH1 은 매 반복 이걸 한다: `i_off = ((i-1)² - (i-1))/2 + (i-1)`
ARCH2 의 주석이 이유를 말한다:

> *"To avoid array index calculations every iteration this architecture uses a simple
> 2D array rather than a optimized/packed triangular matrix."*

**메모리를 두 배 쓰고 지연을 얻는다.** IP 벤더가 ARCH 로 파는 선택지가 이것이다.

**2. 나눗셈을 곱셈으로 바꾼다**

`diag_internal[j]` 에 대각의 **역수**를 저장한다. 주석:

> *"Generate the reciprocal of the diagonal for internal use to avoid the latency of
> a divide in every..."*

우리 `nrldpcfix.정규화(v,3,2) = (|v|*3)>>2` 와 같은 발상이다. **하드웨어에 나눗셈은 없다.**

**3. 부분합을 열 배열로 들고 다닌다 -- 그래서 뱅킹이 필요하다**

```
ACCUM_T square_sum_array[RowsColsA];
ACCUM_T product_sum_array[RowsColsA];
#pragma HLS ARRAY_PARTITION variable = square_sum_array cyclic dim=1 factor = UNROLL_FACTOR
#pragma HLS ARRAY_PARTITION variable = product_sum_array cyclic dim=1 factor = UNROLL_FACTOR
```

열을 한 번 훑으며 **모든 행의 부분합을 동시에** 갱신한다. UNROLL 이 먹으려면 그만큼
동시에 읽어야 하고, 그러려면 배열을 뱅크로 쪼개야 한다.
**메모리 뱅킹이 병렬화의 진짜 제약이다** -- pragma 통계에서 ARRAY_PARTITION 이 79회로
상위인 이유.

**4. 타입이 자리마다 다르다 -- 일곱 개**

```
PROD_T · ACCUM_T · ADD_T · DIAG_T · RECIP_DIAG_T · OFF_DIAG_T · L_OUTPUT_T
```

우리는 `nrldpcfix.py` 에서 워드폭 `W` 하나로 뭉뚱그렸다. **고정소수점 IP 에서 폭이
하나면 반드시 어딘가 낭비거나 어딘가 넘친다.** 곱의 폭과 누산의 폭은 다르다.

**5. 실패를 반환한다**

```cpp
if (cholesky_sqrt_op(A_minus_sum, new_L_diag)) {
#ifndef __SYNTHESIS__
    printf("ERROR: Trying to find the square root of a negative number\n");
#endif
    return_code = 1;
}
```

A 가 양정이 아니면 분해가 안 된다 -- 그걸 **호출자에게 알린다.** 그리고 `printf` 는
`__SYNTHESIS__` 로 감싸 합성에서 사라진다.

---

## ② FINN MVAU -- Xilinx, 310줄. **접기(folding)의 정석**

**제품에서의 자리** FPGA NPU 의 행렬-벡터 곱 + 활성화. 완전연결·컨볼루션이 전부 이걸 쓴다

```cpp
unsigned const NF = MatrixH / PE;      // 세로로 몇 번 접나
unsigned const SF = MatrixW / SIMD;    // 가로로 몇 번 접나
unsigned const TOTAL_FOLD = NF * SF;
for(unsigned i = 0; i < reps * TOTAL_FOLD; i++) {
#pragma HLS pipeline style=flp II=1
```

### 핵심 요령 -- 중첩 루프를 하나로 눌렀다

주석이 이유를 그대로 말한다:

> *"everything merged into a common iteration space (one "big" loop instead of
> smaller nested loops) to get the pipelining the way we want"*

**중첩 루프는 바깥 루프 경계마다 파이프라인이 비워진다(drain).** 하나로 합치고
`sf` · `nf` · `tile` 을 손으로 세면 **II=1 이 끝까지 유지된다.**
HLS 실무에서 제일 큰 요령 중 하나다.

### 나머지

```cpp
if(nf == 0) { inElem = in.read(); inputBuf[sf] = inElem; }   // 입력은 한 번만 읽는다
else        { inElem = inputBuf[sf]; }                        // NF 번 재사용
decltype(activation.init(0,0))  accu[MMV][PE];
#pragma HLS ARRAY_PARTITION variable=accu complete dim=0       // 누산기는 전부 레지스터
```

**하드웨어 크기는 `SIMD x PE` 로 고정이고, 행렬이 커지면 사이클만 는다.**
우리 LDPC 의 Z(리프팅=병렬도)와 정확히 같은 구조 -- Z=384 를 다 펼치면 못 만들고,
Z/P 씩 접어 돈다. FINN 의 SIMD/PE 가 우리 P(부분속도)의 자리다.

---

## ③ AES-128 -- AMD Vitis Security, 1010줄

**제품에서의 자리** MACsec(이더넷 링크 암호화) · IPsec · SSD 자체암호화 · TLS 오프로드

```cpp
state = plaintext ^ key_list[0];
for (round_counter = 1; round_counter <= 10; round_counter++) {
    for (int i = 0; i < 16; i++) {
#pragma HLS unroll
        state(i*8+7, i*8) = ssbox[state(i*8+7, i*8)];        // SubBytes
    }
    tmp_1 = state(15,8);  state(15,8) = state(47,40); ...     // ShiftRows
    ...
    if (round_counter < 10) { GFMul2/GFMul3 ... }             // MixColumns
}
```

### 배울 것 넷

**1. `ap_uint<128>` 비트 슬라이스가 곧 배선이다.** ShiftRows 는
`state(15,8) = state(47,40)` 같은 대입뿐이다. C 로는 배열 복사처럼 보이지만
하드웨어에서는 **선을 바꿔 꽂는 것이고 게이트가 0개다.**

**2. S-box 를 LUTRAM 에 박는다.** `#pragma HLS resource variable=iibox core=ROM_nP_LUTRAM`
-- BRAM 이 아니다. 16개를 동시에 읽어야 하므로 포트가 둘뿐인 BRAM 으로는 안 된다.

**3. 키 확장과 블록 처리가 분리돼 있다.** `updateKey()` / `process()`.
키가 안 바뀌면 확장을 다시 안 한다. **상태를 언제 다시 계산할지가 IP 설계의 요령이다.**

**4. PPA 손잡이가 사실상 하나다** -- 라운드 루프를 언롤할지.
언롤하면 10단 파이프라인(면적 ~10배, 처리율 ~10배), 안 하면 10사이클 순회.

---

## 우리 코드와 견주면 -- 무엇이 비는가

| 그들이 하는 것 | 우리 | 해야 할 것 |
|---|---|---|
| 내부 타입을 자리마다 나눔 (7개) | `W` 하나 | **곱 · 누산 · 출력 폭을 나눈다** |
| `ARCH` 로 회로 선택지를 판다 | 없음 | **D(파이프라인 깊이) · N(언롤)을 그 자리에 둔다** (이미 있음) |
| 나눗셈을 역수 곱으로 | 이미 그렇게 함 | -- |
| 중첩 루프를 하나로 눌러 II=1 | RTL 직접 작성이라 해당 없음 | 생성기가 같은 일을 함 |
| 메모리 뱅킹을 pragma 로 | 생성기가 직접 배선 | -- |
| **실패를 반환한다** | **없음** | **골든과 RTL 모두 오류 코드를 내게 한다** |
| `__SYNTHESIS__` 로 디버그 분리 | 없음 | 해당 없음 (합성 대상이 아님) |

**제일 큰 구멍은 마지막에서 둘째다.** 우리 CNU 도 LDPC 복호기도 **실패를 알리지 않는다.**
Cholesky 가 `return_code` 를 내듯, 복호기는 "반복 상한까지 안 수렴함" 을 내야 한다.
`nrldpc.복호()` 는 이미 `수렴` 을 내고 있지만 **RTL 쪽에 그 신호가 없다.**
