## [VULN-003] load_role()의 JSONDecodeError 예외 미처리로 인한 서비스 거부(DoS)
- 위치: target_app/app.py:27-30
- 유형: 서비스 거부 (Denial of Service, CWE-754)
- 재현:
  1. `session.json` 파일이 비어 있거나 손상된 JSON 포맷(예: 쓰기 도중 레이스 컨디션 등)으로 저장될 경우,
  2. `/admin` 또는 `/run` 엔드포인트 호출 시 `json.loads`에서 `JSONDecodeError` 예외가 발생하여 처리되지 않고 500 내부 서버 오류가 발생한다.
- 영향: 유효한 요청을 처리하지 못하고 서버 엔드포인트 장애를 유발한다.
- 제안 패치:
  - `try-except` 블록으로 `(json.JSONDecodeError, OSError)`를 처리하여 파싱 실패 시 기본 안전 값인 `"user"` 역할을 반환하도록 방어한다.
