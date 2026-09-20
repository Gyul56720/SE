// fir_top.cpp -- HLS 최상위.  **골든모델과 같은 헤더를 읽는다.**
//
//     fir.h ──┬── equiv.cpp · vectors.cpp (g++)  ──> 골든 벡터
//             └── fir_top.cpp        (bambu)     ──> Verilog
//
// 두 길이 갈라지는 자리가 없다.  이 파일은 껍데기일 뿐이고 알고리즘은
// 한 군데(`fir.h`)에만 있다.
//
// 인자가 배열이 아니라 스칼라 넷인 이유:
// 배열/포인터 인자를 주면 Bambu 가 **메모리 인터페이스**를 만든다 (주소·요청·
// 응답 포트).  그러면 재는 것이 FIR 이 아니라 메모리 컨트롤러가 된다.
// 스칼라 넷이면 포트가 넷이고 데이터패스만 남는다 -- **재려던 것을 잰다.**
#include "fir.h"

extern "C" int fir_top(int x0, int x1, int x2, int x3) {
    int32_t x[NTAP];
    x[0] = x0; x[1] = x1; x[2] = x2; x[3] = x3;
    return (int)fir_tap(x);
}
