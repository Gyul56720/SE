### 행렬 곱셈 지수 탐색을 위한 탐색기 설계

수행한 작업:
1. `git pull`을 통해 최신 `mathmetics/matrix_exponent/` 구조 확보.
2. `verifier.py`의 무결성 및 `propose()`의 호출 가능성 로컬 검증 완료(정상 출력: `(True, 'ok')`).
3. `verifier.py`와 `searcher.py`의 구조 분석 완료.
    - `verifier.py`는 `MAX_ATOL=1e-6`, `MIN_TRIALS=20`을 고정하고, `b`와 `b^2` 크기에서 무조건 검증을 수행하도록 설계됨(검증 우회 불가).
    - `searcher.py`는 `propose()` 함수를 통해 스킴 dict를 반환하도록 설계됨.

향후 계획:
- `searcher.py`의 `propose()` 함수를 개선하여 단순 Strassen 복사가 아닌, 확률적 탐색(무작위 계수 조정)이나 최적화 알고리즘 기반의 스킴 생성을 구현할 예정.
- `self_improve_loop.py`를 실행하여 정직한 REJECTED_ROLLBACK을 쌓아가며 탐색을 시작함.
