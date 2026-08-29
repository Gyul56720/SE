## [VULN-001] /run 엔드포인트 내 `subprocess.run(shell=True)` 사용에 따른 OS Command Injection (RCE)
- 위치: target_app/app.py:42
- 유형: 원격 코드 실행 (Remote Code Execution, CWE-78)
- 재현:
  1. `session.json`의 `role`이 `"admin"`인 상태에서,
  2. POST /run 엔드포인트로 JSON 데이터 `{"cmd": "whoami; cat .env.fake"}`를 전송한다.
  3. `shell=True` 조건 하에서 임의의 쉘 명령어 체이닝이 가능해져 본래 의도와 무관한 가짜 환경 변수 내용(`.env.fake`) 등 시스템 파일이 노출된다.
- 영향: 관리자 권한 승격 시 혹은 권한 오염 시 공격자가 호스트 OS 서버를 완전히 장악하고 민감한 자격 증명을 탈취할 수 있는 심각한 위험이 있다.
- 제안 패치:
  - `shell=True`를 비활성화(`shell=False`)하고 실행할 파일 경로와 인자를 배열(List) 형태로 안전하게 파싱하여 쉘 인젝션을 근본적으로 차단한다.
