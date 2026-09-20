// proto_check.cpp -- 8b/10b 부호를 **그 부호의 정의로** 전수 확인한다.
//
// 왜 이렇게 검사하나
// -------------------
// 정규 표(IEEE 802.3 Clause 36 Table 36-1/36-2)를 이 컨테이너에서 못 받는다
// (망이 막혀 403 이 난다).  그러면 두 가지 길이 있다.
//
//   (1) "아마 맞을 것이다" 하고 넘어간다        <- 이 저장소가 다섯 번 진 길
//   (2) **부호의 설계 목표를 성질로 적고 전수로 확인한다**
//
// (2)를 한다.  8b/10b 가 존재하는 이유가 곧 성질이다:
//
//   P1 전단사       RD 마다 코드워드가 서로 달라야 한다.  겹치면 복호 불가
//   P2 RD 유계      running disparity 가 -1 과 +1 만 오간다.  DC 균형의 정의
//   P3 연속 5 이하  같은 비트가 6개 이어지면 CDR 이 클럭을 잃는다
//   P4 콤마 유일    K.28.5 의 7비트 무늬가 데이터 흐름 어디에도 안 나와야
//                   정렬 기준이 된다
//
// 표에 오타가 있으면 이 넷 중 하나가 거의 반드시 깨진다.  그러니 넷을 다
// 통과하는 것은 **약한 진술이 아니다** -- 다만 "표준과 바이트까지 같다" 는
// 아니고, 그 구별을 흐리지 않는다.
#include <stdio.h>
#include <string.h>
#include "enc8b10b.h"

static int 실패 = 0;

static void 봄(int 참, const char *말, ...) {
    if (!참) { printf("  실패  %s\n", 말); 실패++; }
}

// 코드워드를 10비트 문자열로 (a 가 먼저 전송된다 = 왼쪽)
static void bits10(uint32_t c, char *out) {
    for (int i = 0; i < 10; i++) out[i] = (char)('0' + ((c >> (9 - i)) & 1u));
    out[10] = 0;
}

// 이어 붙인 비트열에서 **가장 긴 같은 비트 연속**
static int maxrun(const char *s) {
    int best = 0, cur = 0;
    char prev = 0;
    for (const char *p = s; *p; p++) {
        cur = (*p == prev) ? cur + 1 : 1;
        prev = *p;
        if (cur > best) best = cur;
    }
    return best;
}

// 전송되는 모든 코드워드를 훑기 위한 표
struct 항 { uint8_t data; int k; int rd_in, rd_out; uint32_t code; };
static 항 모든[1200];
static int 개수 = 0;

int main(void) {
    // ── 모든 (data, K, RD) 조합을 만든다 ──────────────────────────────
    for (int rd = -1; rd <= 1; rd += 2) {
        for (int d = 0; d < 256; d++) {
            uint32_t c; int r;
            if (!enc8b10b((uint8_t)d, 0, rd, &c, &r)) continue;
            모든[개수++] = (항){ (uint8_t)d, 0, rd, r, c };
        }
        // K.28.x 여덟 개
        for (int y = 0; y < 8; y++) {
            uint32_t c; int r;
            uint8_t d = (uint8_t)((y << 5) | 28);
            if (!enc8b10b(d, 1, rd, &c, &r)) continue;
            모든[개수++] = (항){ d, 1, rd, r, c };
        }
    }
    printf("코드워드 %d 개 (RD 두 값 x (데이터 256 + K.28.x 8))\n", 개수);
    봄(개수 == 528, "528 개가 나온다");

    // ── P1: 같은 RD 안에서 코드워드가 서로 다른가 ─────────────────────
    int 겹침 = 0;
    for (int rd = -1; rd <= 1; rd += 2) {
        static int 본적[1024];
        memset(본적, 0, sizeof(본적));
        for (int i = 0; i < 개수; i++) {
            if (모든[i].rd_in != rd) continue;
            if (본적[모든[i].code]++) 겹침++;
        }
    }
    printf("P1 전단사: 겹치는 코드워드 %d 개\n", 겹침);
    봄(겹침 == 0, "P1 겹치는 코드워드가 없다");

    // ── P2: RD 가 -1 / +1 만 오가는가 ─────────────────────────────────
    int 벗어남 = 0;
    for (int i = 0; i < 개수; i++)
        if (모든[i].rd_out != -1 &&모든[i].rd_out != 1) 벗어남++;
    printf("P2 RD 유계: 범위를 벗어난 것 %d 개\n", 벗어남);
    봄(벗어남 == 0, "P2 RD 가 +-1 을 안 벗어난다");

    // ── P3: 이어 붙였을 때 같은 비트가 5 를 넘는가 ────────────────────
    // **코드워드 하나만 보면 안 된다.**  경계에서 이어지는 것이 문제다.
    int 넘김 = 0, 최장 = 0;
    항 나쁜a = {0,0,0,0,0}, 나쁜b = {0,0,0,0,0};
    for (int i = 0; i < 개수; i++) {
        for (int j = 0; j < 개수; j++) {
            if (모든[j].rd_in != 모든[i].rd_out) continue;
            char s[24], t[12];
            bits10(모든[i].code, s);
            bits10(모든[j].code, t);
            strcat(s, t);
            int r = maxrun(s);
            if (r > 최장) { 최장 = r; 나쁜a = 모든[i]; 나쁜b = 모든[j]; }
            if (r > 5) 넘김++;
        }
    }
    printf("P3 연속 비트: 최장 %d, 5 를 넘는 이음 %d 개\n", 최장, 넘김);
    if (최장 > 5)
        printf("     보기: D%d.%d(K%d,RD%+d) -> D%d.%d(K%d,RD%+d)\n",
               나쁜a.data & 31, 나쁜a.data >> 5, 나쁜a.k, 나쁜a.rd_in,
               나쁜b.data & 31, 나쁜b.data >> 5, 나쁜b.k, 나쁜b.rd_in);
    봄(최장 <= 5, "P3 같은 비트가 5 를 안 넘는다");

    // ── P4: 콤마가 데이터 흐름에 안 나오는가 ──────────────────────────
    // 콤마 = 7비트 무늬 0011111 또는 1100000.  이것이 데이터 이음 어디에도
    // 나오지 않아야 수신기가 그것을 보고 바이트 경계를 잡을 수 있다.
    const char *콤마[2] = { "0011111", "1100000" };
    int 콤마사고 = 0;
    for (int i = 0; i < 개수; i++) {
        if (모든[i].k) continue;                       // 데이터끼리만
        for (int j = 0; j < 개수; j++) {
            if (모든[j].k) continue;
            if (모든[j].rd_in != 모든[i].rd_out) continue;
            char s[24], t[12];
            bits10(모든[i].code, s);
            bits10(모든[j].code, t);
            strcat(s, t);
            for (int c = 0; c < 2; c++)
                if (strstr(s, 콤마[c])) 콤마사고++;
        }
    }
    printf("P4 콤마 유일: 데이터 이음에서 콤마가 보인 횟수 %d\n", 콤마사고);
    봄(콤마사고 == 0, "P4 데이터에는 콤마가 안 나온다");

    // ── 확인이 아무것도 안 본 것은 아닌가 ─────────────────────────────
    // 이 저장소의 관문: 결과가 한 가지뿐이면 그 검사는 무의미하다.
    static int 본코드[1024];
    memset(본코드, 0, sizeof(본코드));
    int 서로다른 = 0;
    for (int i = 0; i < 개수; i++)
        if (!본코드[모든[i].code]++) 서로다른++;
    printf("서로 다른 코드워드 %d 개 (1024 중)\n", 서로다른);
    봄(서로다른 > 300, "**코드워드가 여러 가지다** -- 몇 개뿐이면 표가 안 채워진 것이다");

    printf("\n%s\n", 실패 ? "빨간불" : "P1~P4 전부 통과");
    return 실패 ? 1 : 0;
}
