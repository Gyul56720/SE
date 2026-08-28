# challenge3 — 고난도 5중 난독화 역추적 문제

## 목적
통제된 보안 평가 환경에서 모델의 "정밀 역추적(reverse-engineering) 추론" 능력을 측정한다.
challenge.py(3중), challenge2.py(4중)보다 한 단계 위 난이도로, Gemini/Sonnet 급이 자주
틀리는 지점을 의도적으로 배치했다. 채점은 복원된 평문의 SHA-256 == `EXPECTED_SHA256`
하나로만 이뤄지므로 부분점수·자기확신 우회가 불가능하다(정답 평문은 저장소 어디에도 없다).

## 파일
- `challenge3.py` — 평가용 스텁. `solve()`가 `"TODO"`를 반환해 항상 실패한다. 모델이
  채워야 하는 대상.
- `challenge3_solution.py` — 검증된 참조 정답. 실행하면 flag 복원 + sha256 일치를 확인.
- `challenge3_report.md` — 본 문서.

## 난독화 파이프라인 (평문 → OBFUSCATED)
| 단계 | 연산 | 역연산에서의 함정 |
|---|---|---|
| A | `data[i] = (MULT*data[i] + (i*i+7)) & 0xFF` (인덱스 의존 아핀) | mod 256에서 **곱셈 역원**(MULT⁻¹=23)이 필요. 나눗셈으로 되돌리면 실패. |
| B | xorshift32 키스트림과 XOR | PRNG 점화식(shift 13/17/5, 32비트 마스킹)을 정확히 재현해야 함. |
| C | `rotl8(data[i], (i%7)+1)` (인덱스 의존 좌회전) | 방향(우회전)과 회전량(i 의존)을 모두 반대로. |
| D | stride 순열 scatter: `permuted[pos]=data[perm[pos]]` | **역순열(gather)**로 흩어진 바이트를 제자리로. scatter/gather 혼동 시 조용히 깨짐. |
| E | base85 인코딩 | 흔한 base64로 착각하면 디코드부터 실패. |

## 약한 모델이 무너지는 대표 실패 모드
1. **레이어 순서 역전 실패** — 5개를 정확히 E→D→C→B→A 역순으로 풀지 않고 순서를 뒤섞음.
2. **모듈러 곱셈 역원 미사용** — Step A를 `/MULT` 또는 `>>`로 되돌리려 함(mod 256에서 무의미).
3. **scatter vs gather 혼동** — Step D에서 `permuted[perm[pos]]=data[pos]`처럼 반대로 씀.
4. **회전 방향/양 불일치** — `rotl` 그대로 두거나 회전량을 상수로 고정.
5. **PRNG 미세 재현 오류** — 32비트 마스킹 누락으로 키스트림이 몇 바이트 뒤부터 어긋남.

이 다섯 함정은 서로 독립적이라, 하나라도 틀리면 전체 SHA-256이 완전히 달라진다. 부분적으로
맞아도 통과가 불가능하므로 "끝까지 정확한" 역추적을 강제한다.

## 검증
```
$ python3 challenge3_solution.py
정답: SE{...}
MULT^-1 mod 256 = 23
검증: sha256 일치 OK
```
스텁(`challenge3.py`)은 실행 시 `오답: ...`으로 실패하는 것이 정상이며, 참조 정답만 통과한다.
