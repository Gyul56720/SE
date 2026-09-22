---
topic: '고치기: ValueError: Header values may not contain linefeed or carria'
---

# 고치기 루프 -- ValueError: Header values may not contain linefeed or carriage return characters

재현 명령: `--설계 ### 3. FIR Functional Requirements

본 IP는 AXI4-Stream 기반의 실시간 FIR 필터 IP이며, 입력 샘플에 대해 고정 계수 FIR 연산을 수행하여 출력 스트림을 생성해`

## 해 본 것
1. [패치] 패치 거절 -- 설계_문서.md: 파일이 없다: 설계_문서.md -- 새 파일은 run_shell 로 만들되 작게 -> **거절** -- 입력값에 줄바꿈(linefeed)이나 특수 문자가 포함되어 헤더 처리 과정에서 발생한 ValueError를 해결하기 위해, 비정상적으로 끝나는 문장을 온전한 문장으로 수정하고 텍스트 내 제어 문자를 제거했습니다.
2. [깨진제안] ```json
{"꼴": "명령", "command": "python3 -c 'with open(\"설계_문서.md\", \"w\", encoding=\"utf-8\") as f: f.write(\"### 3. FI -> **거절** -- JSON 꼴이 아니다
3. [패치] 패치 거절 -- 설계_문서.md: 파일이 없다: 설계_문서.md -- 새 파일은 run_shell 로 만들되 작게 -> **반복** -- 입력값의 마지막 글자가 '해'로 끝나 문장이 불완전하여, 이를 완성된 문장으로 수정함.

## 판정
못 풀었다 (바퀴 3)

## 남은 것 (사람만 할 수 있는 한 가지)
같은 제안을 되풀이한다 -- 코드로는 더 못 간다 (바퀴 3). 마지막 꼬리: 	-abefhkmnptuvxBCEHPT or -o option

## 다음에 같은 증상이면
위의 해결 바퀴를 먼저 해 보고, 실패한 바퀴는 건너뛰어라.
