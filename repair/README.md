# repair -- 문제는 하네스가 스스로 푼다

```
재현 명령(끝값 0 = 해결) + 증상
  ├ 실측  sandbox 에서 재현 -> 끝값·꼬리
  ├ 원인  제2의 뇌: dig/harvest 한 바퀴(증상) + graph 조회 -> 참고
  ├ 제안  수리기(모델): {"꼴": "패치"|"명령"|"사람", ...}  -- 제안만 한다
  ├ 시도  패치 -> 작업 트리에 적용(toolgate) -> sandbox 재현 -> 실패면 되돌림
  │       명령 -> sandbox 에서 `명령 && 재현` -> 통과면 진짜로
  └ 판정  재현 명령의 끝값. 최대 N바퀴. 사람에게는 남은 한 가지만.
끝: repair/ledger.jsonl + public_agent_memory/<때>_고치기_<증상>.md -> graph/night 가 장기기억으로
```

사용자 규정(2026-09-11): "문제 생기면 -> tool 호출 -> sandbox 에서 시도 -> tool 호출 -> …
-> 해결. 유저에게는 최소한의 요구만. 실패 이유는 기억에 넣고 night 로 압축해 장기기억으로."

```bash
python3 repair/run.py --명령 'python3 mailer.py --진단' --증상 '5.7.8 Username and Password not accepted'
python3 repair/run.py --명령 'python3 tests/test_x.py' --증상 'AssertionError' --바퀴 3
python3 tests/test_repair.py
```

디스코드: `!고치기 <재현 명령> :: <증상>` (관리 채널, 백그라운드) · `!고치기 상태`.
에이전트: `repair(command, symptom)` 도구 -- 프롬프트가 "오류를 만나면 손으로 세 번 하지 말고
이것을 불러라" 고 시킨다. 못 푼 증상은 `dig/harvest --틈` 의 검색어가 되어 다음 바퀴에
제2의 뇌가 채운다.
