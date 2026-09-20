# -*- coding: utf-8 -*-
"""Volume III, Part Z19 -- The C++ used for hardware, explained keyword by keyword."""
import sys, os
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, E
from wex import ex, derive

MODEL = "/home/user/SE/edu/model"


def _c(s):
    return "<pre><code>" + E(s) + "</code></pre>"


def ch_cppsyntax():
    s = ['<h1 id="z19">Z19. The C++ Used for Hardware, Keyword by Keyword</h1>']

    s.append("""<p>The model layer in <code>edu/model/</code> is about 250 lines of C++,
    and almost every line uses a keyword that means something slightly different when the
    output is a circuit rather than a program. This part goes through them. It assumes you
    can write C++ and explains what each construct <em>costs in hardware</em>, which is
    the part no C++ book covers.</p>""")

    s.append("<h2>Z19.1 <code>inline</code> &mdash; and why it matters more here</h2>")
    s.append(_c("""static inline int32_t asr(int32_t v, int n) {
    return (v < 0) ? ~((~v) >> n) : (v >> n);
}"""))

    s.append(tab("What <code>inline</code> actually does",
        ["Belief", "Reality"],
        [["&ldquo;It tells the compiler to inline the function.&rdquo;",
          "It is a <b>hint</b>, and modern compilers ignore it for inlining decisions. "
          "<code>-O2</code> inlines small functions whether or not you write it."],
         ["&ldquo;It is about speed.&rdquo;",
          "Its actual <b>required</b> meaning is a linkage rule: it permits the same "
          "function to be defined in multiple translation units without a duplicate-symbol "
          "error. That is why it is mandatory for a function body in a header."],
         ["&ldquo;In HLS it makes things faster.&rdquo;",
          "In HLS it changes <b>what hardware is built</b>. An inlined function is "
          "flattened into the caller's datapath; a non-inlined one may become a separate "
          "module that is <i>shared</i> between call sites, with arbitration logic."]]))

    s.append("""<p>That last row is the hardware-specific part. If four call sites share
    one non-inlined multiply-accumulate, the tool builds one instance and a state machine
    that takes turns &mdash; small and slow. Inline them and you get four instances in
    parallel &mdash; large and fast. In C++ this is a performance micro-decision; in HLS
    it is an architecture decision.</p>""")

    s.append("""<p>In <code>edu/model/</code> everything is <code>static inline</code> in
    headers because the same header is compiled by <code>g++</code> (where the linkage
    rule is what matters) and by <code>bambu</code> (where full flattening into one
    datapath is what we want). <code>static</code> here means internal linkage &mdash; the
    function is private to each translation unit &mdash; and combined with
    <code>inline</code> it is the conventional way to put a small helper in a header.</p>""")

    s.append("<h2>Z19.2 The five meanings of <code>static</code></h2>")
    s.append("""<p>C++ reused one keyword for several unrelated jobs. Three of them appear
    in the model code, and one of them is a bug waiting to happen in HLS.</p>""")

    s.append(tab("<code>static</code>, by position",
        ["Where it appears", "What it means", "Hardware consequence"],
        [["On a function at namespace scope<br><code>static inline int32_t asr(...)</code>",
          "Internal linkage: not visible to other translation units.",
          "None &mdash; a linker concept."],
         ["On a variable at namespace scope<br><code>static const int32_t TH[4] = {...}</code>",
          "Internal linkage, plus (with <code>const</code>) a compile-time-known value.",
          "<b>Large.</b> Constant coefficients let the tool replace multipliers with "
          "shift-adds. See Z19.4."],
         ["On a local variable inside a function<br><code>static int count = 0;</code>",
          "One instance, shared by all calls, persisting between them.",
          "<b>Becomes state.</b> In HLS this infers a register or a RAM that survives "
          "across invocations &mdash; usually not what you meant, and it silently makes a "
          "pure function impure."],
         ["On a class member", "Shared by all objects.",
          "Not used in synthesisable code."],
         ["In an anonymous namespace (the modern alternative)",
          "Same as internal linkage for names.", "None."]]))

    s.append("""<p>The third row is the trap. A C++ programmer writes
    <code>static</code> inside a function to keep a counter cheaply. In HLS that counter
    becomes a register whose value carries between calls, so the generated block is no
    longer a function of its inputs &mdash; and the golden-model comparison that passed in
    C++ can fail in RTL, or worse, pass in both while the block is unusable because two
    instances would interfere. <b>In synthesisable C++, a function-local
    <code>static</code> is almost always a mistake.</b></p>""")

    s.append("<h2>Z19.3 <code>const</code>, <code>constexpr</code>, and <code>enum</code></h2>")
    s.append(_c("""// 이 저장소가 실제로 쓰는 세 가지, 그리고 왜 각각인가

// (1) enum -- 정수 상수를 묶는다.  `ipmodel.h` 가 이걸 쓴다
enum {
    SAMP_F = 7,
    COEF_F = 7,
    ACC_F  = SAMP_F + COEF_F,   // 다른 멤버를 참조할 수 있다
    NTAP   = 4
};
// 왜 enum 인가: **저장 공간을 절대 차지하지 않는다**.  주소를 가질 수 없으므로
// 컴파일러가 메모리를 잡을 여지가 없다.  옛날 C++ 에서 "enum hack" 이라
// 불리던 관용구인데, HLS 에서는 여전히 가장 안전한 컴파일 시간 상수다.

// (2) static const 배열 -- 값 여러 개를 묶을 때
static const int32_t FIR_H[NTAP] = { -18, 111, 111, -18 };
// 배열은 enum 으로 못 만든다.  `static const` 가 대신한다.
// **이 값이 컴파일 시간에 보이는 것이 면적의 핵심이다** (Z19.4).

// (3) constexpr -- 컴파일 시간 계산이 필요할 때
constexpr int32_t sat_hi(int n) { return (1 << (n - 1)) - 1; }
static const int32_t HI = sat_hi(8);       // 127, 컴파일 시간에 계산됨
// `const` 는 "안 바꾼다" 이고 `constexpr` 은 "컴파일 시간에 값을 안다" 이다.
// 둘은 다르다:
const int  a = rand();        // 합법.  런타임 값인데 안 바뀔 뿐
constexpr int b = rand();     // **컴파일 오류**.  컴파일 시간에 알 수 없다"""))

    s.append(tab("Which to use, in synthesisable C++",
        ["Need", "Use", "Why not the others"],
        [["A single integer constant", "<code>enum</code> or <code>constexpr</code>",
          "<code>static const int</code> also works but may take storage if its address "
          "is ever taken."],
         ["An array of constants", "<code>static const T[]</code>",
          "<code>enum</code> cannot hold arrays. Mark it <code>const</code> or the tool "
          "must assume it can change and builds a RAM."],
         ["A value computed from other constants", "<code>constexpr</code> function",
          "A normal function may not be evaluated at compile time, so the result is not "
          "a constant to the HLS tool."],
         ["A run-time-settable coefficient", "A function parameter, deliberately",
          "This is the opposite choice and it costs real multipliers &mdash; make it "
          "consciously."]]))

    s.append("<h2>Z19.4 Why <code>const</code> on the coefficients is worth "
             "hundreds of gates</h2>")
    s.append(ex("Constant multiply versus variable multiply",
        given="The filter computes <code>a1 * 111</code>. In one version 111 is a "
              "<code>static const</code>; in the other it arrives as a function parameter.",
        method="A constant multiply can be expanded into shifts and adds at compile time. "
               "111 = 64+32+8+4+2+1, so it is a sum of six shifted copies &mdash; or, "
               "better, 111 = 128&minus;16&minus;1, which is three terms.",
        numbers="Constant: about 2 adders and 1 subtractor of 9&ndash;17 bits &mdash; "
                "roughly 40&ndash;50 LUT4 on iCE40. Variable: a full 9&times;8 "
                "array multiplier, roughly 150&ndash;200 LUT4, or a hard DSP block where "
                "one exists.",
        trap="The trivial explanation to kill is &ldquo;the tool is smart.&rdquo; It is "
             "not being smart; it is being given different information. Make the "
             "coefficient a parameter and the same tool produces the big version, because "
             "it now must handle every possible coefficient value. The measured evidence "
             "is in Z15: the tuned design used 97 SB_CARRY and <b>zero</b> hard "
             "multipliers, because every multiply had a compile-time-constant operand.",
        extra="The design consequence for a sellable IP: if customers need programmable "
              "coefficients, you pay for real multipliers and you must say so in the "
              "datasheet. If the coefficients are fixed at build time, you can offer a "
              "block a quarter the size. These are two different products, and the "
              "difference is one <code>const</code>."))

    s.append("<h2>Z19.5 Fixed-width types, and integer promotion</h2>")
    s.append(_c("""#include <stdint.h>     // int8_t, int16_t, int32_t, uint32_t ...

// `int` 은 쓰지 마라 -- 크기가 구현마다 다르고, HLS 에서는 **포트 폭이 된다**.
// Z15 의 실측: 인자를 `int` 로 두면 포트가 32비트가 되어 면적이 3.6배가 됐다.

// 정수 승격 (integer promotion) -- C++ 이 조용히 32비트로 올리는 규칙
int8_t  a = 100, b = 100;
auto    c = a + b;        // c 의 타입은 int8_t 가 **아니라 int** 다!
// a+b = 200 이고, int8_t 였다면 -56 으로 넘쳤을 것이다.  int 라서 200 이 된다.
//
// 이것이 모델과 RTL 이 갈라지는 대표적인 자리다:
//   C++ 모델:  200 (int 로 승격돼서)
//   RTL:       -56 (8비트로 짰으면)
// **모델이 하드웨어보다 관대하다.**  그래서 `ipmodel.h` 는 폭을 손으로
// 못박는다 -- `sat(v, 8)` 이 그 일을 한다.

// 규칙: `char`·`short`·`bool` 과 그 unsigned 판은 산술 연산 전에
// 전부 `int` 로 올라간다.  `int` 보다 큰 타입은 안 올라간다.

// 부호 있는 것과 없는 것을 섞으면 더 나쁘다
int32_t  x = -1;
uint32_t y = 1;
bool     z = (x < y);     // **false** 다.  x 가 unsigned 로 변환돼 4294967295 가 된다
// 컴파일러가 -Wsign-compare 로 경고한다.  **경고를 켜고 오류로 다뤄라.**"""))

    s.append("<h2>Z19.6 References, pointers, and what they become</h2>")
    s.append(_c("""// C++ 의 세 가지 전달 방식과, HLS 가 각각 무엇으로 만드는가

int32_t f1(int32_t x);          // 값 전달  -> 입력 포트 하나
int32_t f2(const int32_t *x);   // 포인터    -> **메모리 인터페이스**
int32_t f3(const int32_t &x);   // 참조      -> 값 전달과 같게 취급되는 경우가 많다
void    f4(int32_t &out);       // 비-const 참조 -> 출력 포트

// 포인터가 위험한 이유 -- `fir_top.cpp` 가 그래서 스칼라 넷을 받는다:
//
//   int fir_top(const int *x)   ->  bambu 가 주소·요청·응답 포트를 만든다.
//                                   재는 것이 FIR 이 아니라 메모리 컨트롤러가 된다
//   int fir_top(int,int,int,int) -> 포트 넷.  데이터패스만 남는다
//
// 그래서 모델 안에서는 배열(`const int32_t *x`)을 쓰고,
// **HLS 최상위에서만** 스칼라로 펴서 넘긴다.  안쪽은 인라인되므로
// 포인터가 남지 않는다.

// 합성 가능한 C++ 에서 **없는** 것들:
//   * 동적 할당 (new/delete/malloc) -- 하드웨어에 힙이 없다
//   * 재귀 -- 깊이가 컴파일 시간에 안 정해지면 회로 크기를 못 정한다
//   * 가상 함수 -- 런타임 디스패치는 하드웨어에 없다
//   * 함수 포인터 -- 같은 이유
//   * 예외 (try/catch) -- 스택 되감기가 없다
//   * std::vector, std::string, std::map -- 전부 동적 할당이다"""))

    s.append("""<p>The list of absences is the real lesson. Synthesisable C++ is a
    <em>subset</em>: fixed-size data, no dynamic anything, no indirection that cannot be
    resolved at compile time. What remains is essentially C with templates &mdash; which
    is why the model layer looks the way it does, and why a C++ programmer's instincts
    about abstraction have to be held in check.</p>""")

    s.append("<h2>Z19.7 Templates &mdash; the one abstraction that survives</h2>")
    s.append(_c("""// 템플릿은 **컴파일 시간에 전부 풀린다**.  그래서 합성된다.
// 하드웨어에서 템플릿 인자는 곧 **비트폭과 개수**다.

template<int W>
static inline int32_t sat_t(int32_t v) {
    constexpr int32_t hi = (1 << (W - 1)) - 1;
    constexpr int32_t lo = -hi - 1;
    return v > hi ? hi : (v < lo ? lo : v);
}
// sat_t<8>(x) 와 sat_t<18>(x) 는 **서로 다른 하드웨어**를 낳는다.
// C++ 의 `template<int>` 가 SystemVerilog 의 `parameter` 와 같은 자리다.

// 탭 수까지 템플릿으로 빼면 4탭과 16탭이 한 소스에서 나온다
template<int N>
static inline int32_t fir_n(const int32_t *x, const int32_t *h) {
    int32_t acc = 0;
    for (int i = 0; i < N; i++) acc += x[i] * h[i];   // N 이 상수 -> 언롤됨
    return acc;
}

// 그런데 대가가 있다 -- 실측이다.
// survey/synth/합성결과.md: `ap_fixed` 로 된 복소 8x8 Cholesky 는
// Bambu 프론트엔드에서 **40분 타임아웃(rc=124)** 이 났다.  템플릿 깊이가
// 깊어지면 HLS 도구가 프론트엔드에서 죽는다.
//
// 규칙: **얕은 템플릿은 공짜, 깊은 템플릿은 도구를 죽인다.**
// `template<int W>` 정도는 안전하고, 템플릿이 템플릿을 부르는 수학
// 라이브러리는 위험하다."""))

    s.append("<h2>Z19.8 Namespaces and <code>::</code>, the C++ side</h2>")
    s.append(_c("""namespace fir {
    enum { NTAP = 4 };
    static const int32_t H[NTAP] = { -18, 111, 111, -18 };
    static inline int32_t tap(const int32_t *x);
}

// 쓰는 쪽 -- SystemVerilog 의 package 와 문법이 거의 같다
int32_t y = fir::tap(x);
int     n = fir::NTAP;

using namespace fir;      // SV 의 `import fir_pkg::*;`
int32_t y2 = tap(x);

// `::` 의 다른 얼굴들
::global_thing            // 전역 네임스페이스 (SV 의 $unit:: 에 해당)
std::int32_t              // 표준 라이브러리
MyClass::method           // 클래스 멤버
MyClass::Nested::value    // 중첩
enum class E { A };  E::A // 범위 있는 enum (SV 의 state_e::IDLE 과 같다)"""))

    s.append(tab("<code>::</code>, side by side",
        ["Purpose", "C++", "SystemVerilog"],
        [["Named scope", "<code>namespace fir { }</code> &rarr; <code>fir::H</code>",
          "<code>package fir_pkg; endpackage</code> &rarr; <code>fir_pkg::H</code>"],
         ["Bring it all in", "<code>using namespace fir;</code>",
          "<code>import fir_pkg::*;</code>"],
         ["Scoped enum member", "<code>enum class E{A};</code> &rarr; <code>E::A</code>",
          "<code>typedef enum {A} e_t;</code> &rarr; <code>e_t::A</code>"],
         ["Standard library", "<code>std::</code>", "<code>std::</code> (mailbox, "
          "semaphore)"],
         ["Global scope", "<code>::name</code>", "<code>$unit::name</code>"],
         ["Class member", "<code>C::m</code>", "<code>C::m</code> (verification classes)"],
         ["<b>Not</b> a thing", "&mdash;", "There is no <code>-&gt;</code> for scope; "
          "SystemVerilog uses <code>.</code> for instance members and hierarchy"]]))

    s.append("""<p>So the answer to &ldquo;I only know C++, what is <code>::</code>?&rdquo;
    is: it is the same operator you already know, and SystemVerilog borrowed it
    deliberately. The construct behind it &mdash; <code>package</code> &mdash; is the
    direct analogue of <code>namespace</code>, with one difference that matters: a
    SystemVerilog package must be <em>compiled before</em> its users, because there is no
    two-pass name resolution and no forward declaration.</p>""")

    s.append("<h2>Z19.9 The flags the build actually uses</h2>")
    s.append(_c("""# 골든모델을 컴파일할 때
g++ -O2 -I. -o vectors vectors.cpp

#   -O2   최적화.  등가성 전수 확인이 29.7초가 된 것이 이 덕이다.
#         -O0 이면 수 분이 걸린다 -- 그러면 전수를 포기하게 되고,
#         포기하면 표본으로 내려간다.  **최적화 플래그가 검증 전략을 바꾼다.**
#   -I.   헤더 탐색 경로.  `fir.h` 를 찾는다

# 켜 둘 만한 경고 -- 모델과 RTL 이 갈라지는 자리를 짚는다
g++ -O2 -Wall -Wextra -Wsign-compare -Wconversion -Werror ...
#   -Wconversion    폭이 줄어드는 암묵 변환을 경고한다.  HLS 에서 이것이
#                   곧 비트 잘림이다
#   -Wsign-compare  Z19.5 의 부호 섞임
#   -Werror         경고를 오류로.  경고는 안 읽히고 오류는 읽힌다

# HLS 로 넘길 때 -- 같은 헤더, 다른 도구
bambu --top-fname=fir_top_tuned -I/home/user/SE/edu/model \\
      --clock-period=3 --reset-level=high --reset-type=sync \\
      fir_top_tuned.cpp

#   --top-fname      어느 함수가 최상위 모듈이 되는가
#   -I               g++ 와 **같은** 경로.  같은 헤더를 읽는다는 뜻이다
#   --clock-period   목표 주기(ns).  Z15 에서 이 숫자 하나로
#                    마이크로아키텍처 다섯 개를 얻었다
#   --reset-level    active high/low.  **기본값이 low 라서** 한 번 물렸다
#   --reset-type     sync/async/no"""))

    s.append("""<p>The two commands read the same header with the same include path. That
    is the whole design of the model layer in one line of shell: if the paths ever diverge,
    the golden model stops being the thing that was synthesised, and the comparison becomes
    decoration.</p>""")

    return "\n".join(s)
