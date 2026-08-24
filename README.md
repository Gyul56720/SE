![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Gemini](https://img.shields.io/badge/LLM-Gemini_API-orange)
![Obsidian](https://img.shields.io/badge/Output-Obsidian_Vault-purple)
![Status](https://img.shields.io/badge/status-personal_research_tool-lightgrey)

# 논문 리서치 파이프라인 (Paper Research Pipeline)

키워드 하나 입력하면 arXiv/Semantic Scholar/OpenAlex에서 논문을 자동 수집하고, Gemini로
핵심 주장과 수학/아키텍처를 구조화 추출해서, Obsidian vault에 발전 계보가 위키링크로
자동 연결된 노트로 쌓아주는 개인 연구 자동화 파이프라인.

---

## 목차

- [개요](#개요)
- [주요 특징](#주요-특징)
- [시작하기](#시작하기)
- [사용법](#사용법)
- [프로젝트 구조](#프로젝트-구조)
- [기술 스택 & 의존성](#기술-스택--의존성)
- [실전 검증 결과](#실전-검증-결과)
- [기여 가이드](#기여-가이드)
- [라이선스](#라이선스)
- [연락처](#연락처)
- [참고자료](#참고자료)
- [문제 해결](#문제-해결)
- [로드맵](#로드맵)

---

## 개요

논문 서베이를 할 때 "이 개념이 어디서 왔고 뭘 개선했는지" 발전 계보를 손으로 추적하는 게
가장 오래 걸리는 작업이다. 이 프로젝트는 그 과정을 3단계 Agent로 쪼개서 자동화한다.

1. **수집** — 기간 구간별로 여러 논문 소스에서 후보를 모으고 중복 제거 (LLM 미사용)
2. **분석** — Gemini로 각 논문의 핵심 주장 / "무엇을 어떻게 확장했는지" / 수치 / 한계를 구조화 추출
3. **정리** — Obsidian 마크다운으로 써서 `predecessor::` 위키링크로 발전 계보 그래프를 자동 연결

추가로 수학/하드웨어 구조가 중요한 논문(TPU, roofline model 등)을 위해 별도 Agent가 공식과
아키텍처 스펙(배열 크기, bit-width, 처리량, clock 등 실제 수치 포함)을 뽑아 정리한다.

**핵심 특징 요약**
- 4개 기간 구간(2005-13/14-18/19-22/23-30)별 자동 수집 + 중복 제거
- 발전 계보를 Obsidian 그래프뷰로 시각화 (predecessor 위키링크 자동 매칭)
- 수식(수치 대입 예 포함) + 시스템 아키텍처 구조를 논문별로 별도 정리
- gap 판단 + citation walk로 키워드 매칭이 놓친 논문까지 찾는 적응형 모드
- vault 전체를 대상으로 근거를 단 Q&A (paper-qa 연동)

## 주요 특징

- **다중 소스 수집**: arXiv / Semantic Scholar / OpenAlex 3개 API를 공통 포맷으로 정규화 후 병합, (제목, 연도) 기준 중복 제거
- **구조화 분석**: 논문마다 `core_claim` / `upgrades_from` / `key_numbers` / `limitations` / `one_line_summary`를 JSON 스키마로 강제 추출 (환각 방지)
- **발전 계보 자동 연결**: `upgrades_from` 텍스트에서 같은 배치의 다른 논문 제목이 언급되면 자동으로 `predecessor::` 위키링크 삽입
- **적응형 리서치(`--deep`)**: 지금까지 찾은 계보를 Gemini에 보여주고 "빠진 세대 있나?" 판단시켜 후속 검색어 생성 + 인용 그래프(citation walk) 탐색
- **수학/구조 추출(`--math`)**: 논문 원문 PDF에서 공식(수치 대입 예 포함)과 아키텍처 구성 요소(구조/역할/규격 수치)를 뽑아 `mathmetics/` 폴더에 논문 이름으로 저장
- **키워드 압축(`keyword_synthesizer.py`)**: 정돈 안 된 raw 키워드/텍스트 뭉치를 LLM으로 압축해 검색용 keyword 문장으로 재조립 후 파이프라인에 바로 연결
- **오픈액세스 사본 자동 조회(Unpaywall)**: arXiv ID가 없는 DOI-only 논문도 `sources/unpaywall.py`가
  저작권자가 스스로 공개한 합법 사본을 DOI로 찾아본다 (로그인/인증 불필요, 이메일은 API 식별용)
- **vault 전체 Q&A**: paper-qa + Gemini로 지금까지 쌓인 노트 전체를 근거로 인용 달린 답변 생성

## 시작하기

### 요구사항

- OS: macOS / Linux (Windows는 venv 활성화 명령만 다름)
- Python 3.9 이상 (`paper-qa 4.9.0` 기준 로컬 검증됨)
- Gemini API 키 (필수)
- Obsidian vault 경로 (결과물이 쌓일 곳)
- 선택: Semantic Scholar API 키, Groq API 키, OpenAlex/Unpaywall 연락용 이메일

### 설치

```bash
git clone <this-repo-url>
cd paper_research_pipeline_v2

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

`.env`에 최소 두 줄만 채우면 된다:

```env
GEMINI_API_KEY=발급받은_키
OBSIDIAN_VAULT_PATH=/실제/Obsidian/vault/경로/PaperResearch
```

나머지(`GROQ_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `OPENALEX_MAILTO`)는 비워도 동작한다 —
각각 없을 때 fallback이 이미 코드에 들어있다.

### 빠른 시작

```bash
# 개별 소스 동작 확인 (키 없이 바로 돼야 정상)
python3 sources/arxiv_source.py
python3 gemini_client.py        # GEMINI_API_KEY 필요, 자기소개 문장이 나오면 정상

# 최소 실행: 키워드 하나로 수집→분석→정리
python3 main.py "roofline model"
```

끝나면 vault 루트의 `mathmetics/<키워드>/Survey Notes/` 아래에 `.md` 노트가 쌓인다.
Obsidian에서 그래프뷰를 열면 위키링크로 연결된 발전 계보가 보인다.

## 사용법

### 기본 파이프라인

```bash
python3 main.py "roofline model"
```

`PERIOD_BUCKETS`(기본 4개 구간) 별로 상위 `--top-n`(기본 6)편씩 모아 분석 후 정리한다.

### 적응형 리서치 (gap 판단 + citation walk)

```bash
python3 main.py "roofline model" --deep
```

### 통합 파이프라인 (수집→분석→정리→수학/구조 추출)

```bash
python3 main.py "roofline model" --math
python3 main.py "roofline model" --deep --math --domain "전자전기컴퓨터"
```

검색 결과(Survey Notes)는 `mathmetics/<키워드>/Survey Notes`에, `--domain`을 주면
`mathmetics/<도메인>/<키워드>/Survey Notes`처럼 도메인별로 중첩 정리된다.
`--math`는 PDF가 있는 후보마다 원문을 받아 수식/아키텍처를 뽑아 `mathmetics/` 폴더 바로 밑에
(하위 폴더 없이 평평하게) 논문 이름으로 쓴다 -- 검색 결과용 서브폴더와 겹치지 않는다.

### 논문 한 편만 수학/구조 추출

```bash
python3 math_review.py --list                    # Survey Notes 목록 번호 확인
python3 math_review.py --index 3                  # 3번 논문 추출
python3 math_review.py --arxiv-id 1704.04760       # arXiv ID 직접 지정
python3 math_review.py --pdf ./my_paper.pdf        # 로컬 PDF 직접 지정
python3 math_review.py --image ./photos/eq.jpg --ask "이 유도 과정 설명해줘"   # 수식 사진 질의
```

### 키워드 압축 후 검색 (2단계 추상화: 검색어 2개 + 폴더 2단계)

```bash
python3 keyword_synthesizer.py --file raw_keywords.txt --search
python3 keyword_synthesizer.py "roofline, operational intensity, TPU 로드맵"   # 압축만
```

정돈 안 된 키워드 나열을 Gemini에게 주면 두 가지를 뽑는다:
- **검색어**: 중요도(weight) 기준 상위 2개 영문 구(phrase)만 남겨서 arXiv에는 `(all:"a" OR all:"b")
  AND submittedDate:[...]` 형태로 질의한다. 원문을 그대로(예: 20단어) 검색어로 쓰면 arXiv 쿼리
  파서가 깨져서 날짜 필터가 무시되는 버그가 있었다 (실측 확인: 2005-2013 구간 검색에 2025년 논문이
  나옴) -- 2개로 압축하고 따옴표로 phrase를 명시해서 고쳤다.
- **폴더 구조**: `folder_domain`(상위, 추상적 분야) / `folder_topic`(하위, 구체적 주제) 2단계로만,
  그 이상 세분화하지 않는다.

`--search`를 주면 바로 `main.py` 파이프라인에 연결한다. 압축 로그는 `keyword_synthesis_log.jsonl`에 누적된다.

### Q&A

```bash
python3 main.py --ask "TPU와 GPU의 roofline 차이가 뭐야?"
```

vault에 쌓인 노트 전체를 대상으로 근거를 인용해 답한다. 첫 실행은 인덱싱 때문에 시간이 걸릴 수 있다.

## 프로젝트 구조

```
paper_research_pipeline_v2/
├── README.md                  (이 파일)
├── requirements.txt
├── .env.example                → 복사해서 .env로 만들고 키 채울 것
├── config.py                   모든 모듈이 공유하는 설정, note_folder() 경로 규칙
├── sources/
│   ├── arxiv_source.py         arXiv API (키 불필요)
│   ├── semantic_scholar.py     Semantic Scholar API (키 없어도 동작, 있으면 더 빠름)
│   └── openalex.py             OpenAlex API (키 불필요, Google Scholar 대체재)
├── collector.py                1. 자료 수집 Agent — LLM 미사용
├── gemini_client.py            Gemini REST 호출 공용 래퍼 (재시도/JSON 파싱)
├── analyzer.py                 2. 자료 분석 Agent — Gemini로 구조화 추출
├── organizer.py                3. 자료 정리 Agent — Obsidian 마크다운 기록
├── research_graph.py           (선택) 적응형 리서치 루프 — gap 판단 + citation walk
├── qa_setup.py                 Q&A 레이어 — paper-qa + Gemini
├── deep_review.py              (선택) 논문 한 편 PDF 원문 기반 장문 리뷰
├── math_extractor.py           수학 공식(수치 포함) + 아키텍처 구조 추출 Agent
├── math_review.py              수학/구조 추출 CLI 진입점
├── keyword_synthesizer.py      raw 텍스트/키워드 뭉치 → LLM 압축 → keyword → 파이프라인 실행
└── main.py                     통합 CLI 진입점
```

## 기술 스택 & 의존성

| 구성 | 내용 |
|---|---|
| 언어 | Python 3.9+ |
| LLM | Google Gemini API (REST, `gemini_client.py`가 SDK 없이 직접 호출) |
| 논문 소스 | arXiv API, Semantic Scholar API, OpenAlex API |
| Q&A 엔진 | [paper-qa](https://github.com/Future-House/paper-qa) 4.9.0 |
| 출력 | Obsidian vault (Markdown + YAML frontmatter + wikilink) |

`requirements.txt`:

```
requests>=2.31.0
python-dotenv>=1.0.0
arxiv>=2.1.0
paper-qa
```

## 실전 검증 결과

이 파이프라인은 실제 API 호출로 end-to-end 검증했다 (더미/모킹 아님).

| 검증 항목 | 결과 |
|---|---|
| 키워드 압축 → 검색 → 수집 → 분석 → 정리 (`keyword_synthesizer.py --search`) | raw 키워드 텍스트 → 가중치 상위 2개 검색어 + 2단계 폴더로 재조립 → arXiv에서 4개 기간 구간 전부에 걸쳐 연도가 실제로 맞는 논문 11편 수집 → `.md` 11개 생성 성공 (당시엔 `Paper Pipeline/...`에 썼으나 이후 저장 위치가 `mathmetics/...`로 바뀜) |
| 검색 결과 저장 위치를 `mathmetics/` 하위로 변경 후 재검증 | `main.py "GPU roofline" --top-n 1` 실행 → `mathmetics/GPU roofline/Survey Notes/`에 정상 생성, 기존 `mathmetics/` 최상위 4개 파일은 md5 동일(안 건드림) 확인 |
| arXiv 날짜 필터 버그 재현·수정 | 긴(20단어) 키워드를 따옴표 없이 `all:`에 넣으면 `submittedDate` 필터가 무시됨을 실측 확인(2005-2013 구간 검색에 2025/2026년 논문이 나옴) → 검색어를 가중치 상위 2개 phrase로 줄이고 `all:"phrase"`로 따옴표 처리 후 재검증, 4개 구간 모두 연도가 맞는 논문만 나옴 |
| 수학/아키텍처 추출 (`math_review.py`) | arXiv PDF 확보 가능한 논문 3편에서 수식(수치 대입 예 포함) + 아키텍처 구조 노트 생성 성공 |
| 예시: TPU 논문 아키텍처 추출 | 256×256 MAC 배열(65,536개 8-bit MAC), 피크 92 TOPS @ 700MHz, Unified Buffer 24 MiB, Ridge Point 1350 ops/byte 등 논문 실제 수치가 노트에 정확히 반영됨 |
| Semantic Scholar 429(rate limit) 상황 | 지수 백오프 재시도 후에도 실패 시 arXiv/OpenAlex로 자연 fallback되어 전체 파이프라인은 계속 진행됨 |
| DOI만 있고 arXiv가 없는 논문 (5/8편) → Unpaywall 조회 | 실제 DOI 6건으로 조회한 결과 5건에서 `best_oa_location` URL 찾음 (ACM/IEEE 호스팅) — 나머지 1건(TPU 논문, arXiv로는 이미 확보됨)은 OA 사본 자체가 없음 |
| Unpaywall이 찾은 URL로 실제 다운로드 시도 | ACM(`dl.acm.org`)·IEEE(`ieeexplore.ieee.org`) 호스팅 URL은 5건 모두 403/418로 봇 차단됨 — Unpaywall의 OA 라벨과 별개로 퍼블리셔가 자동화 요청을 막는 게 현실적 한계. 결국 해당 5편은 `--pdf`로 사람이 직접 받은 파일을 넣어야 함 (의도된 동작, 존재하지 않는 PDF를 지어내지 않음) |

## 기여 가이드

개인 연구용 저장소지만 이슈/PR은 환영한다.

- **이슈**: 재현 가능한 최소 예제(키워드, 사용한 플래그, 에러 메시지 전문)와 함께 등록
- **PR**: 모듈 하나당 책임 하나 원칙 유지 (예: 새 논문 소스는 `sources/`에 `Paper` 데이터클래스로 정규화해서 추가)
- **코드 스타일**: 기존 파일처럼 `from __future__ import annotations` + dataclass + 타입 힌트, LLM 호출은 항상 `gemini_client.generate_json()`으로 스키마 강제
- **로컬 개발 환경**: 위 [설치](#설치) 절차 그대로. `python3 -m py_compile <파일>`로 문법 확인 후 실제 키워드로 한 번 돌려서 검증할 것

## 라이선스

현재 별도 라이선스 파일이 없는 개인 연구 저장소다. 재사용/배포 전에는 저장소 소유자에게 문의할 것.

## 연락처

- GitHub: [Gyul56720/paper-research-pipeline-v2](https://github.com/Gyul56720/paper-research-pipeline-v2)
- 이슈/문의는 GitHub Issues로 남길 것

## 참고자료

- [Roofline: An Insightful Visual Performance Model](https://dl.acm.org/doi/10.1145/1498765.1498785) — Williams, Waterman, Patterson (2009)
- [In-Datacenter Performance Analysis of a Tensor Processing Unit](https://arxiv.org/abs/1704.04760) — Jouppi et al. (2017), arXiv:1704.04760
- [Gemini API 문서](https://ai.google.dev/gemini-api/docs)
- [arXiv API](https://info.arxiv.org/help/api/index.html)
- [Semantic Scholar API](https://www.semanticscholar.org/product/api)
- [OpenAlex API](https://docs.openalex.org/)
- [paper-qa](https://github.com/Future-House/paper-qa)
- [Obsidian](https://obsidian.md/)

## 문제 해결

| 증상 | 원인 | 조치 |
|---|---|---|
| `429` 에러가 analyzer/research_graph 단계에서 반복 | Gemini 무료 RPM 초과 | `gemini_client.py`에 이미 지수 백오프가 들어있음. 계속 나면 `--top-n`을 줄이거나 `--deep` 빼고 실행 |
| `generationConfig.responseSchema` 관련 400 에러 | Gemini 구조화 출력 스키마 형식이 API 버전에 따라 다를 수 있음 | `analyzer.py`/`research_graph.py`의 `SCHEMA`/`GAP_SCHEMA`에서 `"type": "OBJECT"` 대신 소문자 `"object"`로 바꿔볼 것 |
| paper-qa 쪽에서 `OPENAI_API_KEY` 관련 에러 | paper-qa의 LLM 역할(llm/summary_llm/agent.agent_llm/embedding) 중 하나라도 명시 안 하면 OpenAI로 fallback됨 | `qa_setup.py`가 넷 다 명시하고 있는지 확인. 특히 `embedding` 필드를 빼먹기 쉬움 |
| `gemini/gemini-embedding-2` 관련 404/model not found | 임베딩 모델명이 계정/리전에 따라 아직 없을 수 있음 | `qa_setup.py`의 `EMBEDDING_MODEL`을 구버전인 `gemini/text-embedding-004`로 교체 |
| `.env`를 채웠는데도 `GEMINI_API_KEY가 비어있다` 경고 | `.env`가 아니라 `.env.example`을 수정했거나, 실행 위치가 프로젝트 루트가 아님 | `cp .env.example .env` 했는지, 루트에서 실행 중인지 확인 |
| DOI만 있고 arXiv가 없는 논문에서 `math_review.py`/`--math`가 여전히 실패 | `sources/unpaywall.py`가 DOI로 합법 오픈액세스 URL을 찾아도(콘솔에 `[Unpaywall] ... 발견` 출력됨), ACM/IEEE 등 퍼블리셔가 자동화 요청 자체를 403/418로 차단하는 경우가 흔함 | 자동 로그인/봇 차단 우회는 지원 안 함(퍼블리셔 ToS 위반 소지). 기관 VPN·도서관으로 직접 받은 PDF를 `--pdf ./파일.pdf`로 넣을 것 |
| `UNPAYWALL_EMAIL`을 안 채웠는데도 Unpaywall 조회가 항상 실패(None) | Unpaywall API는 `example.com` 같은 placeholder 이메일을 거부함 | `.env`의 `UNPAYWALL_EMAIL` 또는 `OPENALEX_MAILTO`에 실제로 받는 이메일을 채울 것 |

## 로드맵

- **오케스트레이션을 LangGraph로**: 지금 `research_graph.deep_collect()`의 for-loop을 그대로
  [google-gemini/gemini-fullstack-langgraph-quickstart](https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart)의
  노드 함수로 옮기면 스트리밍/체크포인팅이 생긴다.
- **Obsidian을 MCP로 노출**: [obsidian-local-rest-api](https://github.com/coddingtonbear/obsidian-local-rest-api)를
  설치하면 이 vault를 MCP 서버로 노출해서 Claude Desktop 등에서도 직접 조회할 수 있다.
  이 경우 `organizer.py`의 `out_path.write_text(...)` 부분만 REST API 호출로 바꾸면 된다.
- **실제 PDF까지 vault에 두기**: 지금은 `.md` 요약만 인덱싱한다. `c.pdf_url`을 실제로 다운로드해서
  같은 폴더에 넣어두면 paper-qa가 원문까지 근거로 써서 더 정확하게 답한다.
- **퍼블리셔 봇 차단 우회(브라우저 헤더/헤드리스)**: Unpaywall이 찾아준 ACM/IEEE URL이 403/418로
  막히는 경우가 있다. `requests`에 더 정교한 헤더를 주거나 헤드리스 브라우저로 우회하는 건
  퍼블리셔 ToS와 다시 충돌할 수 있어 신중히 검토할 것 — 지금은 실패 시 `--pdf` 수동 지정으로 유도한다.
