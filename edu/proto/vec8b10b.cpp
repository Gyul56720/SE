// vec8b10b.cpp -- 8b/10b 골든 벡터를 낸다.
//
//     ./vec8b10b <개수> <씨앗>  >  vec.txt
//
// 각 줄:  data k  기대코드(10진)  기대rd(0=-1,1=+1)
//
// **흐름으로 낸다.**  코드워드 하나씩 따로 보면 RD 상태기계를 안 본다 --
// 8b/10b 에서 틀리기 쉬운 자리가 바로 RD 이월이다.  그래서 한 줄의
// 정답이 앞줄 전체에 달려 있게 만든다.  한 군데만 어긋나도 그 뒤가
// 전부 틀리므로, 회귀가 **조용히 통과할 수 없다.**
#include <stdio.h>
#include <stdlib.h>
#include "enc8b10b.h"

int main(int argc, char **argv) {
    int n = (argc > 1) ? atoi(argv[1]) : 1000;
    unsigned s = (argc > 2) ? (unsigned)atoi(argv[2]) : 1u;
    if (!s) s = 1u;
    int rd = -1;

    for (int i = 0; i < n; i++) {
        uint8_t d; int k = 0;
        if (i < 8) {                 // K.28.x 여덟 개를 먼저 다 밟는다
            d = (uint8_t)((i << 5) | 28); k = 1;
        } else if (i < 16) {         // 대체부호가 걸리는 D.x.7 자리들
            static const int xs[8] = {17, 18, 20, 11, 13, 14, 7, 31};
            d = (uint8_t)((7 << 5) | xs[i - 8]);
        } else if ((i % 37) == 0) {  // 이따금 콤마를 끼워 정렬을 흉내낸다
            d = 0xBC; k = 1;         // K.28.5
        } else {
            s ^= s << 13; s ^= s >> 17; s ^= s << 5;
            d = (uint8_t)(s & 0xFFu);
        }
        uint32_t c; int r;
        if (!enc8b10b(d, k, rd, &c, &r)) { k = 0; d = 0; enc8b10b(d, 0, rd, &c, &r); }
        printf("%u %d %u %d\n", (unsigned)d, k, c, (r > 0) ? 1 : 0);
        rd = r;
    }
    return 0;
}
