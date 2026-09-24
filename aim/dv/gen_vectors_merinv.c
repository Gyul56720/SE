// AIM2 의 역 Mersenne S-box Mer[e_1]^-1 벡터를 **레퍼런스가** 낸다.
// aim2_sbox_exponents[0] 이 곧 e~ 다 (AIM2-I 의 e_1=49).
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "field.h"
#include "params.h"
#include "aim2_constant.h"
static uint64_t seed = 0x243f6a8885a308d3ULL;
static uint64_t nxt(void){ seed ^= seed<<13; seed ^= seed>>7; seed ^= seed<<17; return seed; }
int main(int argc, char **argv){
  int n = (argc>1)? atoi(argv[1]) : 32;
  for (int k=0;k<n;k++){
    gf x, y;
    for (int i=0;i<AIM2_NUM_WORDS_FIELD;i++) x[i]=nxt();
    if (k==0) for (int i=0;i<AIM2_NUM_WORDS_FIELD;i++) x[i]=0;
    if (k==1){ x[0]=1; for(int i=1;i<AIM2_NUM_WORDS_FIELD;i++) x[i]=0; }
    gf_exp(y, x, aim2_sbox_exponents[0]);
    printf("%016llx%016llx %016llx%016llx\n",
      (unsigned long long)x[1],(unsigned long long)x[0],
      (unsigned long long)y[1],(unsigned long long)y[0]);
  }
  return 0; }
