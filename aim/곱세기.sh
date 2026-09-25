#!/usr/bin/env bash
# AIMer 레퍼런스의 GF(2^n) 곱/제곱 횟수를 실제로 세어 마스킹 예산을 낸다.
#
# 왜 있나: 1차 마스킹 하드웨어에서 **곱마다 신선한 랜덤이 든다.** 제곱은 GF(2^n)
# 에서 Frobenius -- 선형이라 몫별로 따로 하면 되고 랜덤이 안 든다. 그래서 곱의
# 개수가 랜덤성 예산(그리고 TRNG 처리량)을 직접 정한다.
#
# 계측 방법 주의: `ld --wrap` 은 **같은 파일 안의 호출을 못 잡는다.**
# gf_exp 와 gf_mul 이 둘 다 field128.c 안이라 처음에 곱이 통째로 빠졌다
# (keypair 가 0 으로 나와서 들켰다). 그래서 소스에 직접 계수기를 넣는다.
set -euo pipefail
KPQ=${KPQ:-/home/user/kpqc-cryptocraft/kpqclean_ver2}
VAR=${1:-128f}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
SRC="$KPQ/crypto_sign/AIMer$VAR/clean"
[ -d "$SRC" ] || { echo "레퍼런스가 없다: $SRC"; echo "  git clone --depth 1 https://github.com/kpqc-cryptocraft/kpqclean_ver2 $KPQ"; exit 2; }
cp "$SRC"/*.c "$SRC"/*.h "$OUT"/
python3 - "$OUT" <<'PY'
import re, sys, pathlib, glob
d = pathlib.Path(sys.argv[1])
f = next(iter(glob.glob(str(d/"field*.c"))))
p = pathlib.Path(f); s = p.read_text()
s = s.replace("#include", "unsigned long AIMCNT_mul=0, AIMCNT_muladd=0, AIMCNT_sqr=0;\n#include", 1)
for fn, ctr in (("gf_mul","AIMCNT_mul"), ("gf_mul_add","AIMCNT_muladd"), ("gf_sqr","AIMCNT_sqr")):
    m = re.search(rf"\nvoid {fn}\(gf [^)]*\)\n\{{", s)
    if not m: sys.exit(f"{fn} 정의를 못 찾았다 -- 레퍼런스가 바뀌었다")
    s = s[:m.end()] + f"\n  {ctr}++;" + s[m.end():]
p.write_text(s)
PY
cat > "$OUT/세기.c" <<'EOF'
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "api.h"
extern unsigned long AIMCNT_mul, AIMCNT_muladd, AIMCNT_sqr;
static void 리셋(void){ AIMCNT_mul=AIMCNT_muladd=AIMCNT_sqr=0; }
static unsigned long 곱(void){ return AIMCNT_mul+AIMCNT_muladd; }
int main(void){
  uint8_t pk[CRYPTO_PUBLICKEYBYTES], sk[CRYPTO_SECRETKEYBYTES];
  static uint8_t sig[CRYPTO_BYTES]; size_t n=0; uint8_t m[32]; memset(m,0xA5,sizeof m);
  printf("%-8s %-10s %10s %12s %10s %12s\n","","","gf_mul","gf_mul_add","gf_sqr","곱 합계");
  리셋(); crypto_sign_keypair(pk,sk);
  unsigned long kg=곱();
  printf("%-8s %-10s %10lu %12lu %10lu %12lu\n",CRYPTO_ALGNAME,"keypair",AIMCNT_mul,AIMCNT_muladd,AIMCNT_sqr,kg);
  리셋(); crypto_sign_signature(sig,&n,m,sizeof m,NULL,0,sk);
  unsigned long sg=곱();
  printf("%-8s %-10s %10lu %12lu %10lu %12lu\n","","sign",AIMCNT_mul,AIMCNT_muladd,AIMCNT_sqr,sg);
  리셋(); int r=crypto_sign_verify(sig,n,m,sizeof m,NULL,0,pk);
  printf("%-8s %-10s %10lu %12lu %10lu %12lu\n","","verify",AIMCNT_mul,AIMCNT_muladd,AIMCNT_sqr,곱());
  if (r) { printf("\n검증 실패(rc=%d) -- 이 실행의 수는 못 쓴다\n", r); return 1; }
  printf("\n서명 길이 %zu B · 검증 통과\n", n);
  printf("1차 마스킹에서 곱마다 신선한 랜덤 %d 비트를 쓴다면(모형):\n", AIM2_NUM_BITS_FIELD);
  printf("  keypair %.2f KB · 서명 %.1f KB/회\n",
         kg*(double)AIM2_NUM_BITS_FIELD/8/1024, sg*(double)AIM2_NUM_BITS_FIELD/8/1024);
  return 0; }
EOF
gcc -O2 -DPARAMS=$VAR -I"$OUT" -I"$KPQ/common" -o "$OUT/세기" "$OUT/세기.c" \
    "$OUT"/field*.c "$OUT"/aim2.c "$OUT"/hash.c "$OUT"/tree.c "$OUT"/sign.c \
    "$KPQ"/common/fips202.c "$KPQ"/common/randombytes.c
"$OUT/세기"
