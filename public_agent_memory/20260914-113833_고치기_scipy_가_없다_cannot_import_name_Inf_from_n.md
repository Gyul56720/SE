---
topic: '고치기: scipy 가 없다: cannot import name 'Inf' from 'numpy''
---

# 고치기 루프 -- scipy 가 없다: cannot import name 'Inf' from 'numpy'

재현 명령: `python3 tests/test_cut.py`

## 해 본 것
1. [명령] 명령 pip install 'numpy<2.0.0' 'scipy<1.13.0' -> **실패** -- 현재 설치된 NumPy 2.5.3 버전과 기존 SciPy 버전 간의 호환성 문제가 발생하여, SciPy가 요구하는 NumPy 버전 범위(1.21.6 <= v < 1.28.0이나, SciPy 구버전의 API 충돌 방지를 위해 안정적인 1.x 버전대)로 재설치하여 의존성 충돌 및 'Inf'
   hint: See PEP 668 for the detailed specification.
2. [명령] 명령 python3 -m venv venv && ./venv/bin/pip install numpy<2.0.0 scipy<1.13.0 && ./venv/bin/python tests/t -> **실패** -- PEP 668 정책으로 인해 시스템 전체에 패키지를 설치하는 대신 가상 환경(venv)을 생성하여 의존성을 격리 설치하고 테스트를 실행합니다.
   bash: line 1: 2.0.0: No such file or directory
3. [패치] 패치 거절 -- tests/test_cut.py: old 가 파일에 없다 -> **거절** -- 최신 numpy 2.0 버전부터 'numpy.Inf' 속성이 제거되었습니다. scipy가 내부적으로 이 속성을 참조할 때 발생하는 오류를 막기 위해 호환성 패치를 추가합니다.

## 판정
못 풀었다 (바퀴 3)

## 남은 것 (사람만 할 수 있는 한 가지)
3바퀴를 다 해 봤다 -- 마지막 꼬리: bash: line 1: 2.0.0: No such file or directory

## 다음에 같은 증상이면
위의 해결 바퀴를 먼저 해 보고, 실패한 바퀴는 건너뛰어라.
