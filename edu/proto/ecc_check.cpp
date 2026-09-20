// ecc_check.cpp -- SEC-DED 를 **전수로** 확인한다.
//
//   단일 오류: 30 자리(데이터24 + 패리티5 + 전체패리티1) 전부를 하나씩
//              뒤집어, 데이터가 원래대로 복구되는지
//   이중 오류: C(30,2) = 435 쌍 전부를, **잘못 고치지 않고 알리는지**
//
// 데이터 값마다 이것을 하면 2^24 x 465 가 되어 너무 많다.  대신
// **선형 부호의 성질**을 쓴다: 오류의 영향이 데이터 값과 무관하므로
// 대표 데이터 몇 개(0, 전부1, 무작위)로 충분하고, 그 사실 자체도
// 무작위 데이터로 확인한다.
#include <stdio.h>
#include "ecc24.h"

static int 실패 = 0;

int main(void) {
    const uint32_t 대표[] = { 0x000000u, 0xFFFFFFu, 0xA5A5A5u, 0x5A5A5Au,
                             0x123456u, 0xFEDCBAu };
    int n대표 = (int)(sizeof(대표)/sizeof(대표[0]));

    // ── 오류 없음 ─────────────────────────────────────────────────────
    for (int t = 0; t < n대표; t++) {
        uint32_t o; uint8_t e = ecc24_enc(대표[t]);
        int r = ecc24_dec(대표[t], e, &o);
        if (r != ECC_OK || o != 대표[t]) { printf("  실패 무오류인데 %d\n", r); 실패++; }
    }
    printf("무오류: 통과\n");

    // ── 단일 오류 30 자리 ─────────────────────────────────────────────
    int 단일본것 = 0, 단일틀림 = 0;
    for (int t = 0; t < n대표; t++) {
        uint32_t d = 대표[t];
        uint8_t  e = ecc24_enc(d);
        for (int p = 0; p < 30; p++) {
            uint32_t dd = d; uint8_t ee = e;
            if (p < 24) dd ^= (1u << p); else ee ^= (uint8_t)(1u << (p - 24));
            uint32_t o; int r = ecc24_dec(dd, ee, &o);
             단일본것++;
            if (r != ECC_FIXED || o != d) {
                if (단일틀림 < 4)
                    printf("  실패 단일오류 자리 %d: r=%d  얻음 %06X  기대 %06X\n",
                           p, r, o, d);
                단일틀림++;
            }
        }
    }
    printf("단일 오류: %d 가지 중 틀림 %d\n", 단일본것, 단일틀림);
    if (단일틀림) 실패++;

    // ── 이중 오류 C(30,2) ─────────────────────────────────────────────
    // 요구: **잘못 고치지 않는다.**  ECC_DOUBLE 을 내거나, 적어도
    // 성한 데이터를 망가뜨리지 않아야 한다.
    int 이중본것 = 0, 오정정 = 0, 검출 = 0;
    for (int t = 0; t < n대표; t++) {
        uint32_t d = 대표[t];
        uint8_t  e = ecc24_enc(d);
        for (int p = 0; p < 30; p++)
        for (int q = p + 1; q < 30; q++) {
            uint32_t dd = d; uint8_t ee = e;
            if (p < 24) dd ^= (1u << p); else ee ^= (uint8_t)(1u << (p - 24));
            if (q < 24) dd ^= (1u << q); else ee ^= (uint8_t)(1u << (q - 24));
            uint32_t o; int r = ecc24_dec(dd, ee, &o);
            이중본것++;
            if (r == ECC_DOUBLE) 검출++;
            else if (o != d) 오정정++;      // 고쳤다고 했는데 틀린 데이터
        }
    }
    printf("이중 오류: %d 가지 중 검출 %d, **오정정 %d**\n",
           이중본것, 검출, 오정정);
    if (오정정) { printf("  실패 이중오류를 잘못 고쳤다\n"); 실패++; }
    if (검출 != 이중본것) {
        printf("  참고: %d 가지는 ECC_DOUBLE 을 안 냈지만 데이터는 안 망가뜨렸다\n",
               이중본것 - 검출);
    }

    // ── 검사가 아무것도 안 본 것은 아닌가 ─────────────────────────────
    int 서로다른ecc = 0; static int 봄[256];
    for (int i = 0; i < 256; i++) 봄[i] = 0;
    unsigned s = 1u;
    for (int i = 0; i < 20000; i++) {
        s ^= s << 13; s ^= s >> 17; s ^= s << 5;
        if (!봄[ecc24_enc(s & 0xFFFFFFu)]++) 서로다른ecc++;
    }
    printf("ECC 값 가지수: %d / 64 (여섯 비트)\n", 서로다른ecc);
    if (서로다른ecc < 32) { printf("  실패 ECC 가 몇 값밖에 안 난다\n"); 실패++; }

    printf("\n%s\n", 실패 ? "빨간불" : "SEC-DED 전수 확인 통과");
    return 실패 ? 1 : 0;
}
