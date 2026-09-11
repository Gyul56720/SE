# 기억 요지 -- 원장에서 지어진 파생 문서

> **손으로 고치지 마라.** 다음 밤일(`scripts/night.sh`)이 덮는다. 진실은
> `graph/ledger.jsonl`(색인)과 `graph/edges.jsonl`(판정)에 있고, 이 문서는
> 거기서 다시 지어진다. 지은 때: 2026-09-11 03:21 UTC

## 새 갈래 -- 원장 분포에 없던 기억 (기준선=이례, 검증 통과)

- **202608·self·mod·code·안전한** -- # 안전한 단위 테스트 실행기 self-modification 실제 코드 예시 4: ```python import subprocess def run_tests(): return subprocess.run(["pytest"]) ``` `<public_agent_memory/20260827-180004_self_mod_code_4.md>`
- **202608·cot·self·mod·ast** -- # AST 노드 주입 [CoT 및 Self-Correction 적용 수집 결과] ```python import ast def inject_code(tree, node): tree.body.append(node); return tree ``` `<public_agent_memory/20260827-190003_cot_self_mod_3.md>`
- **202608·testing·self·prompt·testing_self** -- # testing_self prompt ```python # Anthropic 논문 기반 고품질 추론(CoT + Self-Correction) 테스팅 프롬프트 저장 파일 TESTING_PROMPT = """너는 엄격한 논리와 단계별 검증을 거쳐 답변하 `<public_agent_memory/20260827-193000_testing_self_prompt.md>`
- **202608·편입·영어·준비·계획** -- # 편입 영어 준비 계획 사용자가 편입 영어 준비 계획을 거듭 요청하였음. 1년 기준 시기별 로드맵(어휘·문법 -> 구문·논리 -> 유형별 심화 -> 기출/파이널)과 영역별(어휘, 문법, 독해, 논리) 상세 전략, 수험 원칙을 포함한 종합 계획을 수립 `<public_agent_memory/20260828-041841_편입_영어_준비_계획.md>`
- **202608·loopdesk·사태·피드백·할루시네이션** -- # Loopdesk 사태 피드백 및 할루시네이션 방지 대책 Loopdesk 사태 피드백: 퍼블릭 웹 검색이 안티봇(Bot Detection) 정책이나 차단으로 실패했을 때, 미확인된 키워드나 과장된 슬로건("The World's First Truly  `<public_agent_memory/20260828-043743_Loopdesk_사태_피드백_및_할루시네이션_방지_대책.md>`
- **202608·보고·규범과·메모리·정책의** -- # 보고 규범과 메모리 정책의 한계 2026-08-28 채점에서 확인된 두 가지. 1. 보고 과장 금지. challenge3 보고에서 try/except import fallback을 자동 패스 검색 지원이라고 표현했다. 거짓은 아니지만 실제보다 커  `<public_agent_memory/20260828-152712_보고_규범과_메모리_정책의_한계.md>`
- **202608·코드·제출·검증·습관** -- # 코드 제출 전 검증 습관 challenge3 채점(2026-08-28)에서 지적된 개선점. 다음 제출 때 반복하지 말 것. 1. decode('utf-8', errors='replace')를 쓰면 복원이 틀려도 예외 없이 대체문자로 넘어가 실패가  `<public_agent_memory/20260828-152712_코드_제출_전_검증_습관.md>`
- **202608·작업·전제조건·확인·git** -- # 작업 전 전제조건 확인 2026-08-28 challenge4/5 평가에서 나온 오답노트. 파일이 없다/명령이 실패한다로 막히면 그것을 결론으로 삼지 말고 원인을 한 단계 이상 진단한 뒤 보고하라. 작업트리는 최신이 아닐 수 있다. deploy-o `<public_agent_memory/20260828-183623_작업_전_전제조건_확인.md>`
- **202608·금지·규칙의·범위를·좁게** -- # 금지 규칙의 범위를 좁게 해석하라 challenge4/5 평가(2026-08-28)에서 실제로 난 실패. 'git 히스토리로 삭제된 정답지를 찾지 마라'를 'git 계열 명령 전부 금지'로 넓게 읽고 git pull조차 하지 않아 작업을 시작도 못 `<public_agent_memory/20260828-183625_금지_규칙의_범위를_좁게_해석하라.md>`
- **202608·정직·보고와·자율·진단은** -- # 정직 보고와 자율 진단은 상충하지 않는다 2026-08-28 challenge4/5 평가 결과. 잘한 점과 고칠 점을 함께 남긴다. 잘한 점(유지): 파일이 없자 답을 지어내지 않고 exit code와 에러 메시지를 인용해 정직하게 실패로 보고했다 `<public_agent_memory/20260828-183626_정직_보고와_자율_진단은_상충하지_않는다.md>`

## 깃발 지도 -- 무엇이 얼마나 쌓여 있나

self(16) · mod(14) · code(11) · 코드(7) · git(6) · 커밋(5) · 아니라(5) · 자기(5) · 검증(4) · cot(4) · m22(4) · 동적(3) · 프롬프트(3) · 수정(3) · 추론(3) · 자가(3) · 마라(3) · 3by3(3) · 패치(2) · 함수(2)

노드 57개 · 경고 0개 · 새 갈래 40개. 찾기: `python3 graph/ask.py --말 <깃발>` · 디스코드 `!기억 <말>`
