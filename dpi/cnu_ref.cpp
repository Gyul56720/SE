// LDPC 검사노드(CNU) 의 **C++ 비트정확 레퍼런스 모델**.
// SystemVerilog 테스트벤치가 DPI-C 로 이것을 부른다.
// 파이썬 골든(nrldpcfix.정규화 / ldpcrtl.골든CNU) 과 같은 식이어야 한다.
#include <svdpi.h>
#include <cstdlib>
#include <climits>

static inline int normalize(int v, int num, int shift) {
    int s = (v < 0) ? -1 : 1;          // 0 은 양수로 (파이썬 where(Q>=0,1,-1) 과 같게)
    int m = std::abs(v);
    return s * ((m * num) >> shift);   // 0 쪽으로 버림
}

extern "C" void cnu_ref(int q0, int q1, int q2, int q3,
                        int* r0, int* r1, int* r2, int* r3) {
    const int D = 4;
    int q[D] = {q0, q1, q2, q3};
    int a[D], sign[D];
    for (int i = 0; i < D; i++) { a[i] = std::abs(q[i]); sign[i] = (q[i] >= 0) ? 1 : -1; }

    int idx0 = 0;                                   // 최소가 여럿이면 첫 번째
    for (int i = 1; i < D; i++) if (a[i] < a[idx0]) idx0 = i;
    int min1 = a[idx0], min2 = INT_MAX;
    for (int i = 0; i < D; i++) if (i != idx0 && a[i] < min2) min2 = a[i];

    int sp = 1;
    for (int i = 0; i < D; i++) sp *= sign[i];

    int out[D];
    for (int i = 0; i < D; i++) {
        int mag = (i == idx0) ? min2 : min1;
        out[i] = normalize(sp * sign[i] * mag, 3, 2);
    }
    *r0 = out[0]; *r1 = out[1]; *r2 = out[2]; *r3 = out[3];
}
