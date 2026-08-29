## [VULN-002] /admin 엔드포인트의 타이밍 공격 취약점 및 환경 변수 부재 처리 미흡
- 위치: target_app/app.py:35-37
- 유형: 인증 검증 취약점 (CWE-208 / CWE-287)
- 재현:
  1. `X-Api-Key` 헤더와 환경변수 `ADMIN_API_KEY`의 비교를 `api_key != os.environ.get("ADMIN_API_KEY")`로 수행.
  2. 단순 문자열 비교 연산자(`!=`)는 글자가 일치하는 위치에 따라 응답 시간에 미세한 차이를 발생시켜 공격자가 타이밍 분석을 통해 API Key를 유추할 수 있다.
  3. 환경 변수 `ADMIN_API_KEY`가 설정되지 않은 경우(`None`), 잘못된 키 검증 상태가 될 수 있다.
- 영향: 인증 우회 및 API Key 노출 가능성.
- 제안 패치:
  - `secrets.compare_digest` 또는 `hmac.compare_digest`를 사용하여 상수 시간(Constant-Time) 비교를 수행한다.
  - `ADMIN_API_KEY` 환경 변수가 유효하게 설정되어 있지 않다면 무조건 접근을 거부하도록 안전장치를 추가한다.
