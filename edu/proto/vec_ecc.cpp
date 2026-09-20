// vec_ecc.cpp -- ECC 골든 벡터.  각 줄: data24 ecc_in  ->  ecc_out fixed single double
#include <stdio.h>
#include <stdlib.h>
#include "ecc24.h"
int main(int argc, char **argv){
    int n=(argc>1)?atoi(argv[1]):500; unsigned s=(argc>2)?(unsigned)atoi(argv[2]):1u; if(!s)s=1u;
    for(int i=0;i<n;i++){
        s^=s<<13; s^=s>>17; s^=s<<5;
        uint32_t d = s & 0xFFFFFFu;
        uint8_t  e = ecc24_enc(d);
        uint32_t dd = d; uint8_t ee = e;
        // 오류를 계획적으로 섞는다: 무오류 / 단일 / 이중을 고루
        int mode = i % 3;
        if (mode == 1) {                       // 단일 오류
            int p = (int)(s % 30u);
            if (p < 24) dd ^= (1u<<p); else ee ^= (uint8_t)(1u<<(p-24));
        } else if (mode == 2) {                // 이중 오류
            int p = (int)(s % 30u), q = (int)((s>>8) % 30u);
            if (p == q) q = (q + 1) % 30;
            if (p < 24) dd ^= (1u<<p); else ee ^= (uint8_t)(1u<<(p-24));
            if (q < 24) dd ^= (1u<<q); else ee ^= (uint8_t)(1u<<(q-24));
        }
        uint32_t o; int r = ecc24_dec(dd, ee, &o);
        int single = (r==ECC_FIXED)||(r==ECC_OK && 0);
        int dbl    = (r==ECC_DOUBLE);
        // RTL 은 opar 를 err_single 로 낸다 -- 무오류면 0, 단일이면 1
        if (r==ECC_OK) single = 0;
        printf("%u %u %u %u %d %d\n", dd, (unsigned)ee,
               (unsigned)ecc24_enc(dd), o, single, dbl);
    }
    return 0;
}
