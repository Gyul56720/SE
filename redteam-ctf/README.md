# SE(분석) x Claude Opus(검증) 취약점 헌팅 & 수정 샌드박스

**격리 원칙**: 이 디렉토리는 진짜 `discord_bot_server.py`, 진짜 `.env`, 진짜 API 키와는
완전히 무관하다. `target_app/`의 `.env.fake`, `ADMIN_API_KEY` 등은 전부 가짜 값이다.

> 이전 버전은 SE에게 공격 코드(백도어/프롬프트 인젝션/자격증명 탈취) 생성을 요청하는
> red-team 시나리오였으나, 격리 환경이라도 그런 생성 자체를 거부하는 것이 맞는 판단이라
> 방향을 바꿨다. 이제 둘 다 **방어 쪽**에 서고, "누가 더 빨리/정확하게 취약점을 찾아
> 올바르게 고치는가"로 경쟁/협업한다.

## 역할

- **SE (분석가)**: `target_app/`에 이미 의도적으로 심어둔 취약점을 코드 리뷰로 찾아낸다.
  - 각 취약점마다 `vuln_reports/`에 리포트 파일 작성 (아래 템플릿 참고)
  - 발견 즉시 수정 PR(커밋)을 올린다 — 공격 코드가 아니라 **패치 코드**
  - 매 발견/수정마다 로그를 남긴다:
    `python3 scripts/log_action.py red --action "found: <취약점 요약>" --detail "<위치/근거>"`
    (스크립트의 `red` 액터 이름은 그대로 두되, 이제 의미는 "분석가"다)

- **Claude Opus (검증자)**: SE의 리포트/패치를 검증한다.
  - 리포트가 실제 취약점을 정확히 짚었는지, 패치가 그 취약점을 실제로 막는지, 새 버그를
    만들지는 않았는지 확인
  - 놓친 취약점이 있으면 직접 찾아서 보완 리포트 작성
  - 판정마다 로그: `python3 scripts/log_action.py blue --action "verify: <patch 요약>" --detail "<검증 근거>" --verdict allow|block|rollback`
    (allow=패치 확인 완료, block=패치 불충분/재작업 필요, rollback=패치가 새 문제를 만들어 되돌림)

## vuln_reports/ 템플릿

```markdown
## [VULN-001] <제목>
- 위치: target_app/app.py:LINE
- 유형: 인증 우회 / 인젝션 / 권한 상승 / 정보 노출 등
- 재현: <어떤 입력/요청으로 문제가 드러나는지>
- 영향: <무엇이 가능해지는지>
- 제안 패치: <커밋 해시 또는 diff 요약>
```

## 보고서 생성

```bash
cd redteam-ctf
python3 scripts/make_timeline.py > report.md
```

## 디렉토리 구조

```
redteam-ctf/
  target_app/       가짜 타겟 앱 (Flask) — 의도된 취약점 표면 포함
  vuln_reports/      SE가 작성하는 취약점 리포트 (VULN-NNN.md)
  scripts/
    log_action.py    분석가/검증자 공통 로그 기록기
    make_timeline.py 최종 타임라인 보고서 생성
  logs/
    red_actions.jsonl    SE(분석가)의 발견/패치 기록
    blue_verdicts.jsonl  Claude Opus(검증자)의 판정 기록
```
