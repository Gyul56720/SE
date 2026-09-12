---
topic: '고치기: ModuleNotFoundError: No module named 'plan''
---

# 고치기 루프 -- ModuleNotFoundError: No module named 'plan'

재현 명령: `python3 improve/run.py --부탁 핸드폰에서 py랑 md 파일이 안열리는데 pdf로 제공해 줄 수 있는지`

## 해 본 것
1. [명령] 명령 python3 improve/run.py --부탁 "핸드폰에서 py랑 md 파일이 안 열리니 pdf로 제공해 줘" -> **실패** -- 인자가 공백으로 분리되어 파싱 에러 및 plan 모듈을 찾지 못하는 문제가 발생하므로, 전체 요청 문장을 큰따옴표로 묶어 하나의 문자열 인자로 전달합니다.
   [llm_pool] 한 바퀴가 전부 RPM/일시장애다 -- 10초 기다렸다 다시 돈다 (2/3바퀴)
2. [입력] GEMINI_API_KEY -- 현재 환경 변수 및 .env 파일에 GEMINI_API_KEY가 존재하지 않아 LLM 풀을 호출할 수 없습니다. 시스템 자동화 도구(`improve/run.py`)가 제안을 생성하 -> !열쇠 GEMINI_API_KEY=<발급받은 구글 제미나이 API 키> -> **입력오류** -- 현재 환경 변수 및 .env 파일에 GEMINI_API_KEY가 존재하지 않아 LLM 풀을 호출할 수 없습니다. 시스템 자동화 도구(`improve/run.py`)가 제안을 생성하기 위해서는 유효한 API 키 설정이 필수적입니다.

## 판정
못 풀었다 (바퀴 2)

## 남은 것 (사람만 할 수 있는 한 가지)
주어진 정보가 틀렸다 (이용자 측) -- GEMINI_API_KEY -- 현재 환경 변수 및 .env 파일에 GEMINI_API_KEY가 존재하지 않아 LLM 풀을 호출할 수 없습니다. 시스템 자동화 도구(`improve/run.py`)가 제안을 생성하 -> !열쇠 GEMINI_API_KEY=<발급받은 구글 제미나이 API 키>

## 다음에 같은 증상이면
위의 해결 바퀴를 먼저 해 보고, 실패한 바퀴는 건너뛰어라.
