# 백그라운드 작업 실행 규칙

`discord_bot_server.py`가 이 세션을 `claude -p`로 실행한다. 응답을 보내고 나면 `claude -p`
프로세스 자체가 곧바로 종료되는데, 이때 Bash tool 안에서 `command &`처럼 셸 job control로만
백그라운드에 올린 프로세스는 부모와 함께 정리되어 같이 죽는다 (실측 확인됨: `python3
ai_concept_generator.py &`로 띄운 뒤 "완료되면 알려드리겠습니다"라고 답했지만, 다음 메시지가
올 때까지 아무것도 생성되지 않은 채 프로세스가 사라져 있었다).

몇 분 이상 걸리는 작업(파일 여러 개 생성, 배치 처리, 리서치 파이프라인 등)을 백그라운드로
돌려야 하면 반드시 아래 패턴을 쓸 것:

```bash
mkdir -p /home/ubuntu/SE/logs
setsid nohup <command> > /home/ubuntu/SE/logs/<작업이름>.log 2>&1 < /dev/null &
disown
echo "PID: $!"
```

- `setsid`: 새 세션을 만들어 부모 프로세스(그리고 claude -p 자체)가 종료돼도 죽지 않게 한다.
- `nohup` + `disown`: SIGHUP과 셸 job table 연결을 모두 끊는다.
- stdin/stdout/stderr를 전부 리다이렉트해서 셸이 닫혀도 안전하게 한다.
- 사용자에게 "백그라운드로 시작했다"고 답하기 전에 `ps -p <PID>`로 실제로 살아있는지 확인부터
  하고, 확인됐을 때만 PID와 로그 파일 경로를 같이 알려줄 것. 확인 없이 "완료되면
  알려드리겠습니다"라고 먼저 말하지 말 것.
- 다음 메시지(재개된 세션)에서 진행 상황을 물어보면 추측하지 말고 로그 파일 내용과
  `ps -p <PID>`로 실제 상태를 확인한 뒤 답할 것.
