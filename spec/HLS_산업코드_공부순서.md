# 실제로 팔리는 HLS 코드 -- 무엇을 어떤 순서로 볼 것인가

2026-09-18 에 받았다. **라이선스가 둘로 갈린다** -- 파일을 열어 확인했다.

    Vitis_solver · Vitis_security · Vitis_dsp_fft    Apache-2.0  (Xilinx/AMD)
    finn_hlslib                                     **BSD-3-Clause**  (Xilinx)

첫 판에 "전부 Apache-2.0" 이라고 적었다가 고쳤다. 둘 다 재배포를 허용하지만 조건이
다르다 -- BSD-3 은 이름을 광고에 못 쓰게 하는 조항이 따로 있다. 저작권 표시는 파일
머리에 그대로 있다. 저장소에는 넣지 않았다 -- 남의 코드로
우리 트리를 채울 이유가 없다. 받은 자리는 `/home/user/hls_study` 이고 사용자에게
묶어서 보냈다.

## 받은 것 -- 11,900 줄

| 묶음 | 줄 | 무엇인가 |
|---|---|---|
| **finn_hlslib** | 6,528 | Xilinx 가 배포하는 **양자화 신경망 가속기 IP**. 16 파일 |
| **Vitis_solver** | 3,198 | AMD 가 **IP 로 파는 선형대수**. Cholesky(732) · QR/Givens(889) · SVD/Jacobi(1577) |
| **Vitis_security** | 1,966 | **AES-128/192/256**(1010) · SHA-224/256(854) + 공용 타입 |
| Vitis_solver_L2 | 200 | `potrf.hpp` 블록 Cholesky, `NCU` 로 병렬화 |

**Vitis_solver 는 우리가 버린 MMSE 검출기의 바로 그 블록이다** -- `A = H^H H + s^2 I`
를 푸는 Cholesky·QR 이 AMD 의 판매 품목이다. "MMSE 검출기 IP" 가 실제로 어떤 꼴로
팔리는지가 그 네 파일이다.
| Vitis_dsp_fft | 25 | `vt_fft.hpp` **include 허브뿐** -- 실제 FFT 구현은 **못 받았다**(경로 404) |

**FFT 는 받은 것이 아니다.** 25줄짜리 헤더 하나이고 그것이 가리키는 구현 파일은
전부 404 였다. "FFT 를 받았다" 고 말하면 거짓이라 여기 적어 둔다.

**어디서 못 받았나:** `ap_fixed.h` · `hls_stream.h` · `hls_x_complex.h` 는 GitHub 에
없다 -- **Vitis HLS 설치본 안에** 있다. 그래서 이 코드들은 여기서 컴파일이 안 된다.
읽는 데는 문제없고, 돌리려면 Vitis HLS 가 필요하다. (`raw.githubusercontent.com` 만
열려 있어서 디렉터리 목록을 못 본다. `#include` 를 따라가며 받았다.)

## 이 코드들이 실제로 쓰는 pragma -- 무엇을 공부해야 하는지가 여기 있다

    pipeline        109      II 를 못 박는다. **제일 많다**
    inline           84      함수 경계를 없앤다
    UNROLL           92
    ARRAY_PARTITION  79      **메모리 뱅킹.** 여기서 막히면 II 가 안 나온다
    DEPENDENCE       30      "이 의존은 거짓이다" 라고 도구에게 알린다
    loop_tripcount   12      **루프 횟수를 모를 때** (불규칙한 코드의 표시)
    STREAM           10
    BIND_STORAGE      7      BRAM/URAM/LUTRAM 을 고른다

세 번째 줄과 네 번째 줄이 핵심이다. **HLS 에서 II 가 안 나오는 이유는 거의 언제나
(가) 메모리 포트가 모자라거나 (나) 도구가 의존을 과하게 본 것**이다.

---

## 공부 순서

### 1단계 -- `Vitis_solver/cholesky.hpp` 의 **Traits 구조체** (43~200줄)

**"IP 를 어떻게 파라미터화하는가" 의 산업 표준 답이 여기 있다.** 우리가 `cnu(D, W)`
함수 인자로 한 것을 이들은 타입으로 한다.

```cpp
template <bool LowerTriangularL, int RowsColsA, typename InputType, typename OutputType>
struct choleskyTraits {
    typedef InputType PROD_T;      // 곱의 내부 타입
    typedef InputType ACCUM_T;     // 누산기 타입      <- 우리가 손으로 세던 그 폭
    typedef InputType DIAG_T;      // 대각 원소
    typedef InputType RECIP_DIAG_T;// 1/sqrt(대각)
    static const int ARCH = 1;        // 0=기본 1=저지연 2=더 저지연   <- 같은 수학, 다른 회로
    static const int INNER_II = 1;    // 안쪽 루프의 II 목표
    static const int UNROLL_FACTOR = 1;
    static const int UNROLL_DIM = (LowerTriangularL ? 1 : 2);
};
```

배울 것 셋:

1. **내부 타입이 전부 이름을 갖는다.** `PROD_T` · `ACCUM_T` · `ADD_T` 가 따로다.
   우리가 `nrldpcfix.py` 에서 워드폭 W 하나로 뭉뚱그린 것을 이들은 **자리마다 나눈다.**
   고정소수점 IP 에서 폭을 하나로 두면 반드시 어딘가 낭비거나 어딘가 넘친다
2. **`ARCH` 로 같은 수학의 회로를 셋 중 고르게 한다.** IP 벤더가 지연/면적 선택지를
   파는 방식이 이것이다. 우리 `D`(파이프라인 깊이)가 같은 자리다
3. **타입별 특수화** -- `float` · `std::complex` · `ap_fixed` · `hls::x_complex` 마다
   Traits 를 따로 특수화한다. 복소수는 누산 폭이 다르기 때문이다

### 2단계 -- `finn_hlslib/mvau.hpp` 의 **접기(folding)**

```cpp
template<unsigned MatrixW, unsigned MatrixH, unsigned SIMD, unsigned PE, unsigned MMV, ...>
  unsigned const NF = MatrixH / PE;    // 세로로 몇 번 나눠 도나
  unsigned const SF = MatrixW / SIMD;  // 가로로 몇 번 나눠 도나
  decltype(activation.init(0,0)) accu[MMV][PE];
  #pragma HLS ARRAY_PARTITION variable=accu complete dim=0
```

**자원과 처리율을 맞바꾸는 손잡이가 `SIMD` 와 `PE` 단 둘이다.** 행렬이 아무리 커도
회로 크기는 `SIMD x PE` 로 정해지고, 나머지는 `NF x SF` 사이클에 걸쳐 접어서 돈다.

이것이 우리 LDPC 의 `Z`(리프팅=병렬도)와 **정확히 같은 구조**다. Z=384 를 다 펼치면
못 만들고, Z/4 씩 네 번 접으면 만들어진다. FINN 이 그것을 어떻게 이름 붙이고 어떻게
누산기를 나누는지 보면 우리 층 파이프라인의 설계가 그대로 나온다.

### 3단계 -- `Vitis_security/aes.hpp` -- **규칙적인 IP 의 본보기**

AES 는 분기가 없고 라운드 수가 고정이다. 그래서 HLS 가 제일 잘하는 종류다.
S-box 를 어떻게 두는지(`ARRAY_PARTITION` vs `BIND_STORAGE`), 라운드를 어떻게 펼치는지
보라. **우리 CNU 와 같은 부류**다.

### 4단계 -- `Vitis_solver/qrf.hpp` · `svd.hpp` -- **반복이 데이터에 달린 경우**

SVD 는 Jacobi 회전을 수렴할 때까지 돈다 -- 몇 번인지 컴파일 시점에 모른다.
`loop_tripcount` 가 왜 필요한지, 도구가 지연을 어떻게 "추정" 하는지가 여기 나온다.
**우리 LDPC 의 조기 종료와 같은 문제다.**

### 5단계 -- `Vitis_solver_L2/potrf.hpp` -- 블록 분해

큰 행렬을 타일로 쪼개 도는 법. L1(핵심 커널)과 L2(그것을 엮는 층)를 **왜 나누는지**
가 보인다. IP 납품에서 이 층 나눔이 곧 인터페이스 설계다.

---

## MIPS · RISC-V 의 HLS 코드는 **못 받았다**

찾으려 한 것은 **CHStone** 의 `mips.c` 다 -- HLS 벤치마크의 사실상 표준이고 MIPS
프로세서를 C 로 쓴 것이 들어 있다. 미러 네 곳을 찔러 봤는데 전부 404 였다.

**왜 더 못 찾나:** `raw.githubusercontent.com` 은 열려 있지만 `github.com`(HTML)과
`api.github.com` 과 `codeload`(tar) 는 **403** 이다. 그래서 **정확한 경로를 알 때만**
받을 수 있고 디렉터리를 뒤질 수가 없다. 경로를 알려 주시면 바로 받는다.

**그리고 솔직히 -- 프로세서를 HLS 로 쓰는 것은 공부 대상으로 좋지 않다.** CHStone 의
`mips.c` 는 *HLS 도구를 시험하려고* 만든 벤치마크지 실제로 파는 IP 가 아니다. 진짜
프로세서 IP(ARM · RISC-V 상용)는 전부 RTL 로 쓴다 -- 제어가 불규칙해서 HLS 의 결과
품질이 안 나오기 때문이다. 앞 답에서 말한 그 이유 그대로다.

**실제로 팔리는 HLS IP 를 보고 싶으면 위 1~5단계가 바로 그것이다.** AMD 가 Vitis
라이브러리로 파는 것이고, FINN 은 Xilinx 가 배포하는 것이다.
