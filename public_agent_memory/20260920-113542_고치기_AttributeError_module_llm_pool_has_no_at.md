---
topic: '고치기: AttributeError: module 'llm_pool' has no attribute 'ask''
---

# 고치기 루프 -- AttributeError: module 'llm_pool' has no attribute 'ask'

재현 명령: `bash scripts/번역돌리기.sh --진단`

## 해 본 것
1. [사람] 환경 변수 GEMINI_API_KEY 설정 -> **사람** -- 증상에서 '키가 없다'고 명시되었으며, 이는 코드 수정이 아닌 API 접근을 위한 사용자 인증 정보 입력이 필요한 상황입니다.

## 판정
못 풀었다 (바퀴 1)

## 남은 것 (사람만 할 수 있는 한 가지)
환경 변수 GEMINI_API_KEY 설정

## 다음에 같은 증상이면
위의 해결 바퀴를 먼저 해 보고, 실패한 바퀴는 건너뛰어라.
