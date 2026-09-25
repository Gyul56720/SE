// AIMer 레퍼런스로 RTL 대조 벡터를 만든다. **정답은 레퍼런스가 낸다 -- 내가 짓지 않는다.**
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "field.h"
#include "params.h"
static uint64_t 씨 = 0x243f6a8885a308d3ULL;   // pi -- 재현되게 고정한다
static uint64_t 다음(void){ 씨 ^= 씨<<13; 씨 ^= 씨>>7; 씨 ^= 씨<<17; return 씨; }
int main(int argc, char **argv){
  int n = (argc>1)? atoi(argv[1]) : 64;
  static const uint64_t e7[AIM2_NUM_WORDS_FIELD] = {7, 0};
  for (int k=0;k<n;k++){
    gf x, y, s, m, p;
    for (int i=0;i<AIM2_NUM_WORDS_FIELD;i++){ x[i]=다음(); y[i]=다음(); }
    if (k==0){ for(int i=0;i<AIM2_NUM_WORDS_FIELD;i++){x[i]=0;y[i]=0;} }       // 0 도 본다
    if (k==1){ x[0]=1; for(int i=1;i<AIM2_NUM_WORDS_FIELD;i++)x[i]=0; y[0]=1; for(int i=1;i<AIM2_NUM_WORDS_FIELD;i++)y[i]=0; }
    gf_sqr(s, x); gf_mul(m, x, y); gf_exp(p, x, e7);
    printf("%016llx%016llx %016llx%016llx %016llx%016llx %016llx%016llx %016llx%016llx\n",
      (unsigned long long)x[1],(unsigned long long)x[0],
      (unsigned long long)y[1],(unsigned long long)y[0],
      (unsigned long long)s[1],(unsigned long long)s[0],
      (unsigned long long)m[1],(unsigned long long)m[0],
      (unsigned long long)p[1],(unsigned long long)p[0]);
  }
  return 0; }
