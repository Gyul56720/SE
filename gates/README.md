# gates/ -- 강제 게이트

`gatekeeper.py`가 커밋 직전에 여기 있는 검사를 전부 돌린다. 하나라도 위반되면
`discord_bot_server.git_sync()`가 커밋하지 않고 위반 목록을 그대로 Discord에 돌려준다.

## 왜 메모리가 아니라 게이트인가

이 저장소의 에이전트는 사고를 낼 때마다 `public_agent_memory/`에 진단 노트를 썼다.
노트의 질은 높았다 -- "제약 자기소거", "재작성은 무관한 불변식을 조용히 버린다" 같은
관찰은 정확했다. 그런데 행동은 바뀌지 않았다. 실측 기록(2026-08-28):

```
20:16  "고친 코드는 push 전에 임포트부터 시켜봐라" 저장
20:35  "py_compile은 문법만 잡는다, 임포트를 해봐야 한다" 다시 저장
20:37  임포트가 불가능한 코드를 push -> 봇 기동 불가
```

진단이 저장소의 마크다운 파일에 있을 뿐 실행 경로 어디에도 연결돼 있지 않았다.
게이트는 에이전트가 읽어야 작동하는 것이 아니라, 커밋 경로 위에 놓여서 읽지 않아도
작동한다. 그것이 유일한 차이다.

## 승격 절차 -- 손으로 추가하지 않는다

새 게이트는 `self_challenge.py`의 red-green 증명을 통과해야만 들어온다.
`Public_agent/challenge.py`가 `EXPECTED_SHA256`으로 풀이자의 자기 확신을 배제하듯,
게이트도 실행 증거로 판정한다.

```
python3 self_challenge.py prove --candidate <검사.py> --broken-commit <사고커밋>
```

- **RED** -- 고치기 전 트리에서 반드시 위반을 보고해야 한다.
  통과해버리면 그 진단은 실제 원인이 아니었다.
- **GREEN** -- 고친 뒤 트리에서는 통과해야 한다.
  실패하면 수정이 실제로는 고치지 못한 것이다.

둘 다 성립할 때만 `PROVEN=1`이고, 그때 `gates/`로 복사된다.

`tests/test_gates_on_incidents.py`가 기존 게이트들에 대해 이 증명을 매번 다시 돌린다.

## 게이트 규약

```python
RULE_ID  = "G007"
TITLE    = "한 줄 설명"
ORIGIN   = "사고 커밋 해시"
EVIDENCE = "public_agent_memory/....md"   # 없으면 ""
def check(ctx) -> list[str]: ...          # 위반 목록. 빈 리스트면 통과.
```

`ctx`는 `gatekeeper.GateContext` -- `repo`, `rel()`, `python_files()`,
`tracked_files()`, `diff_numstat()`를 준다. 게이트가 직접 subprocess를 부르지 않게
해서 임시 저장소를 물려 테스트할 수 있게 한다.

## 현재 게이트

| ID | 무엇을 막는가 | 사고 |
|---|---|---|
| G001 | `@tool` 독스트링 소실 / 밀려난 문자열 리터럴 | b32aa78 |
| G002 | 로컬 모듈 간 top-level 임포트 순환 | b32aa78 |
| G003 | 권한·제약·안전장치 서술 코드의 소거 (래칫 방지) | 1a82685 |
| G004 | 자격증명 커밋 / 로그 출력 | run_bot_loop.sh |
| G005 | 핵심 파일 대량 삭제 (자기 재작성) | 1a82685 |
| G006 | 데코레이터가 미정의 이름 참조 (임포트 시 NameError) | 1a82685 |

G003에는 이 체계 자신을 지키는 항목이 들어 있다 -- `git_sync`의
`gatekeeper.run_gates` 호출, `gatekeeper.run_gates` 정의, `self_challenge.prove`
정의가 사라지면 커밋이 막힌다. 게이트 한 줄만 지우면 전부 무력화되는 것이
제약 자기소거의 정확한 재현이기 때문이다.
