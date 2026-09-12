---
topic: '고치기: 조사 f867ea29: [목표] scripts/ledgerstat.py 가 repair/ledger.json'
---

# 고치기 루프 -- 조사 f867ea29: [목표] scripts/ledgerstat.py 가 repair/ledger.jsonl 에 없는 열쇠(귀속·맞춘수·틀린수

재현 명령: `python3 tests/test_목표_f867ea29.py`

## 해 본 것
1. [조사] 가설: h1 예측: 재현=0 게이트=0 감사=0 감사:tests/test_mail.py=0 -> **빨강 ['감사']**
2. [조사] 가설: h2 예측: 재현=0 게이트=0 감사=0 감사:tests/test_mail.py=0 -> **빨강 ['감사']** -- 전에났나
3. [조사] 가설: h3 예측: 재현=0 게이트=0 감사=0 감사:tests/test_목표_f867ea29.py=0 -> **빨강 ['감사']** -- 전에났나
4. [조사] 가설: h4 예측: 재현=0 게이트=0 감사=0 감사:tests/test_목표_f867ea29.py=0 -> **초록** -- 전에났나

## 판정
해결됐다 (바퀴 4)

## 다음에 같은 증상이면
위의 해결 바퀴를 먼저 해 보고, 실패한 바퀴는 건너뛰어라.
