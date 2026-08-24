# 논문 리서치 파이프라인

키워드 하나 넣으면: arXiv/Semantic Scholar/OpenAlex에서 기간별로 논문을 모으고(자료 수집) →
Gemini로 각 논문의 핵심 주장/선행 연구 대비 확장점을 구조화 추출하고(자료 분석) →
Obsidian vault에 `predecessor::` 위키링크가 걸린 마크다운으로 정리한다(자료 정리).
그래프뷰를 열면 "발전 과정"이 자동으로 트리 형태로 보인다. 이후 paper-qa로 vault 전체에 Q&A도 가능.

이 저장소의 코드는 전부 이 환경에서 문법 검사 + 오프라인 로직(중복제거/슬러그 생성/YAML frontmatter 파싱/JSON 파싱)을
실제로 실행해서 검증했다. 다만 arXiv·Semantic Scholar·OpenAlex·Gemini 라이브 API 호출 자체는
네트워크가 막힌 샌드박스라 이 환경에서 못 돌려봤다 — 아래 "실행" 단계에서 처음 돌릴 때 이 부분만 실제 확인이 필요하다.

## 폴더 구조

```
paper_research_pipeline/
├── README.md              (이 파일)
├── requirements.txt
├── .env.example            → 복사해서 .env로 만들고 키 채울 것
├── config.py                모든 모듈이 공유하는 설정
├── sources/
│   ├── arxiv_source.py      arXiv API (키 불필요)
│   ├── semantic_scholar.py  Semantic Scholar API (키 없어도 동작, 있으면 더 빠름)
│   └── openalex.py          OpenAlex API (키 불필요, Google Scholar 대체재)
├── collector.py             1. 자료 수집 Agent — LLM 미사용
├── gemini_client.py         Gemini REST 호출 공용 래퍼
├── analyzer.py               2. 자료 분석 Agent — Gemini로 구조화 추출
├── organizer.py               3. 자료 정리 Agent — Obsidian 마크다운 기록
├── research_graph.py          (선택) 적응형 리서치 루프 — gap 판단 + citation walk
├── qa_setup.py                 Q&A 레이어 — paper-qa + Gemini
└── main.py                     CLI 진입점
```

## 설치

### 0. 요구사항
- Python 3.11 이상 (paper-qa 최소 요구사항)
- 이미 연동되어 있다는 Gemini API 키

### 1. 가상환경 + 의존성

```bash
cd paper_research_pipeline
python3 -m venv venv
source venv/bin/activate        # Windows는 venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env`를 열어서 최소한 이 두 줄만 채우면 된다:

```
GEMINI_API_KEY=이미_갖고있는_그_키
OBSIDIAN_VAULT_PATH=/실제/Obsidian/vault/경로/PaperResearch
```

나머지(`GROQ_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `OPENALEX_MAILTO`)는 비워둬도 동작한다 — 각각 없을 때의
fallback이 코드에 이미 들어있다 (Groq 없으면 Q&A 근거요약도 Gemini로, S2 키 없으면 초당 1회로 스로틀, mailto
없으면 OpenAlex 기본 풀 사용).

### 3. 동작 확인 (개별 모듈)

전체를 돌리기 전에 소스 하나씩 확인하면 어디서 막히는지 알기 쉽다:

```bash
python3 sources/arxiv_source.py          # 키 불필요, 바로 돼야 정상
python3 sources/semantic_scholar.py      # 키 불필요, 바로 돼야 정상
python3 sources/openalex.py              # 키 불필요, 바로 돼야 정상
python3 gemini_client.py                 # GEMINI_API_KEY 필요 - 한 문장 자기소개가 나오면 정상
```

## 실행

### 기본 파이프라인 (수집 → 분석 → 정리)

```bash
python3 main.py "roofline model"
```

`config.py`의 `PERIOD_BUCKETS`(기본 2005-13 / 14-18 / 19-22 / 23-30) 구간별로 상위 6편씩 모으고,
각각을 Gemini로 분석해서 vault에 `.md`로 쓴다. 끝나면 Obsidian에서 그래프뷰를 열어볼 것.

### 적응형 리서치 (gap 판단 + citation walk 포함)

```bash
python3 main.py "roofline model" --deep
```

이러면 `research_graph.py`가 개입해서: 지금까지 찾은 계보를 Gemini에게 보여주고 "빠진 세대 있어?"를
물은 뒤 후속 검색을 스스로 만들고, 각 논문의 인용 그래프(누가 이 논문을 인용했는지 / 이 논문은 뭘 인용했는지)를
따라가며 키워드 매칭으론 못 찾는 논문까지 찾는다. LLM 호출이 늘어나니 무료 한도가 빠듯하면 기본 모드부터 써볼 것.

### Q&A

```bash
python3 main.py --ask "TPU와 GPU의 roofline 차이가 뭐야?"
```

vault에 쌓인 노트 전체를 대상으로 인용 달아 답한다. 첫 실행 시 paper-qa가 vault를 인덱싱하느라
시간이 좀 걸릴 수 있다.

## 자주 만날 수 있는 문제

| 증상 | 원인 | 조치 |
|---|---|---|
| `429` 에러가 analyzer/research_graph 단계에서 반복 | Gemini 무료 RPM 초과 | `gemini_client.py`에 이미 지수 백오프가 들어있음. 계속 나면 `--top-n`을 줄이거나 `--deep` 빼고 실행 |
| `generationConfig.responseSchema` 관련 400 에러 | Gemini 구조화 출력 스키마 형식이 API 버전에 따라 다를 수 있음 | `analyzer.py`/`research_graph.py`의 `SCHEMA`/`GAP_SCHEMA`에서 `"type": "OBJECT"` 대신 소문자 `"object"`로 바꿔볼 것 |
| paper-qa 쪽에서 `OPENAI_API_KEY` 관련 에러 | paper-qa의 LLM 역할(llm/summary_llm/agent.agent_llm/embedding) 중 하나라도 명시 안 하면 OpenAI로 fallback됨 | `qa_setup.py`가 넷 다 명시하고 있는지 확인. 특히 `embedding` 필드를 빼먹기 쉬움 |
| `gemini/gemini-embedding-2` 관련 404/model not found | 임베딩 모델명이 계정/리전에 따라 아직 없을 수 있음 | `qa_setup.py`의 `EMBEDDING_MODEL`을 구버전인 `gemini/text-embedding-004`로 교체 |
| `.env`를 채웠는데도 `GEMINI_API_KEY가 비어있다` 경고 | `.env`가 아니라 `.env.example`을 수정했거나, 실행 위치가 프로젝트 루트가 아님 | `cp .env.example .env` 했는지, 루트에서 실행 중인지 확인 |

## 각 파일이 정확히 뭘 하는지

| 파일 | LLM 호출 | 역할 |
|---|---|---|
| `sources/*.py` | 없음 | 3개 API를 공통 `Paper` 포맷으로 정규화 |
| `collector.py` | 없음 | 병합 + 정규화된 (제목,연도)로 중복제거 + 기간 버킷팅 |
| `gemini_client.py` | - | REST 호출 공용 래퍼 (재시도/JSON 파싱 포함) |
| `analyzer.py` | 논문당 1회 | 구조화 추출 (core_claim/upgrades_from/key_numbers/limitations) |
| `organizer.py` | 없음 | 마크다운 생성 + predecessor 위키링크 자동 매칭 |
| `research_graph.py` | iteration당 1회 (gap 판단만) | 적응형 탐색 + citation walk |
| `qa_setup.py` | 질문당 여러 번 (evidence 요약) | paper-qa 설정 + 질의응답 |

## 다음 단계로 업그레이드하고 싶다면

- **오케스트레이션을 LangGraph로**: 지금 `research_graph.deep_collect()`의 for-loop을 그대로
  [google-gemini/gemini-fullstack-langgraph-quickstart](https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart)의
  노드 함수로 옮기면 스트리밍/체크포인팅이 생긴다.
- **Obsidian을 MCP로 노출**: [obsidian-local-rest-api](https://github.com/coddingtonbear/obsidian-local-rest-api)를
  설치하면 이 vault를 PROGNOS MCP 서버 옆에 나란히 두고 Claude Desktop 등에서도 직접 조회할 수 있다.
  이 경우 `organizer.py`의 `out_path.write_text(...)` 부분만 REST API 호출로 바꾸면 된다.
- **실제 PDF까지 vault에 두기**: 지금은 `.md` 요약만 인덱싱한다. `c.pdf_url`을 실제로 다운로드해서
  같은 폴더에 넣어두면 paper-qa가 원문까지 근거로 써서 더 정확하게 답한다.
