---
topic: '고치기: 조사 0566d1e0: tests/test_mathdrift_prove.py 가 빨강이다: '틀린 걸음은 거'
---

# 고치기 루프 -- 조사 0566d1e0: tests/test_mathdrift_prove.py 가 빨강이다: '틀린 걸음은 거짓 -- 사슬이 끊겼다고 말한다' 실

재현 명령: `python3 tests/test_mathdrift_prove.py`

## 해 본 것
1. [조사] **가설 확인**: `IndexError`는 `_v2["걸음"]`이 빈 리스트였기 때문 → `_prover.py` 자식 프로세스가 `ModuleNotFoundError: No module named 'sympy'`로 -> **초록**

## 판정
해결됐다 (바퀴 1)

## 다음에 같은 증상이면
위의 해결 바퀴를 먼저 해 보고, 실패한 바퀴는 건너뛰어라.
