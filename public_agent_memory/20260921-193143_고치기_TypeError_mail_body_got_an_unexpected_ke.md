---
topic: '고치기: TypeError: mail_body() got an unexpected keyword argument '첨'
---

# 고치기 루프 -- TypeError: mail_body() got an unexpected keyword argument '첨부이름'

재현 명령: `--설계 MERA-1 v1.0 Event Recorder Core 를 ASIC 으로 설계한다.
입력은 256-bit canonical AXI4-Stream, 1채널 I/Q 16+16bit = 32bit/sample,`

## 해 본 것

## 판정
못 풀었다 (바퀴 0)

## 남은 것 (사람만 할 수 있는 한 가지)
모델을 못 불렀지만 **저장소가 답했다**: `python3 -m house.run` 로 부르면 파일이 어떤 판이든 산다
  근거: **house/run.py 을 스크립트 꼴로 부르는 자리가 있다**: eda_prompt.py, relay.py, tests/test_house.py
  확인: python3 entrypoints.py --위험만

## 다음에 같은 증상이면
위의 해결 바퀴를 먼저 해 보고, 실패한 바퀴는 건너뛰어라.
