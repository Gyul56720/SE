# 대한민국 맞춤형 AI 날씨 파이프라인 설계서

## 1. 개요
사용자의 자연어 질의("내일 날씨 어때?")를 입력받아 실시간 기상 데이터를 수집하고, 대한민국 표준시(KST) 보정 및 고도화된 LLM(고급 추론 모델)을 거쳐 사용자 친화적 자연어 메시지로 변환·제공하는 End-to-End 파이프라인입니다.

---

## 2. 파이프라인 아키텍처

```
[사용자 입력 (Discord / CLI / Web)]
           │
           ▼
 [1. 의도 및 위치 추출 (Intent & NER Engine)]
           │
           ├─ 위치 지정됨 (예: 서울, 부산) ──> 해당 지역 좌표 매핑
           └─ 위치 미지정 ───────────────> 기본 위치(서울) 또는 IP 기반 탐색
           │
           ▼
 [2. 실시간 기상 데이터 수집 (Weather API Fetcher)]
           │
           ├─ 기상청 오픈 API (단기예보 / 중기예보)
           └─ 글로벌 백업 (wttr.in / OpenWeatherMap)
           │
           ▼
 [3. KST 시간대 보정 및 데이터 정제 (Timezone & Data Normalization)]
           │
           ├─ UTC ──> KST(Asia/Seoul, UTC+9) 변환
           └─ 강수량, 기온, 습도, 풍속 구조화된 JSON 정제
           │
           ▼
 [4. 고급 추론 LLM 분석 및 맞춤형 페르소나 가공 (LLM Reasoning Layer)]
           │
           ├─ 체감 온도, 우산 소지 여부, 외출 팁 도출
           └─ 불필요한 기상 용어 제거 및 공감형/친화적 말투 적용
           │
           ▼
 [5. 최종 응답 출력 (Response Formatter)]
```

---

## 3. 핵심 단계별 구현 상세

### ① 의도 및 위치 추출 (Intent & NER)
* 사용자의 발화에서 **지역**(서울, 부산 등)과 **시점**(오늘, 내일, 주말)을 파싱합니다.
* 예: `"내일 부산 날씨 알려줘"` ➔ `target_location="Busan"`, `target_date="tomorrow"`

### ② 실시간 데이터 수집 (Data Fetching)
* 기상청 API 또는 wttr.in(JSON 포맷)을 비동기로 호출하여 기온, 강수확률, 날씨 상태 코드를 수집합니다.
* *코드 예시 (Python Async Fetcher)*:
  ```python
  import httpx
  
  async def fetch_weather(location: str) -> dict:
      url = f"https://wttr.in/{location}?format=j1"
      async with httpx.AsyncClient() as client:
          resp = await client.get(url)
          return resp.json()
  ```

### ③ KST 시간대 보정 (Timezone Alignment)
* 서버가 UTC 환경이더라도 `zoneinfo.ZoneInfo("Asia/Seoul")`를 사용하여 현재 및 예보 시간을 KST 기준으로 정확히 매핑합니다.

### ④ 고급 추론 및 사용자 친화적 포맷팅 (LLM Layer)
* 수집된 raw JSON 데이터를 LLM에 주입하여, 단순 수치 나열이 아닌 **"사용자 맞춤형 브리핑"**으로 변환합니다.
* **출력 가이드라인**:
  * 🌡️ **기온 및 체감**: 아침/낮 기온 변화와 입어야 할 옷차림 제안.
  * ☂️ **강수 정보**: 우산 필요 여부 및 강수 집중 시간대 안내.
  * 😊 **어조(Tone)**: 친근하고 다정한 비서 톤.

---

## 4. 기대 효과
1. **정확성**: KST 표준시 엄격 보정으로 시간대 오작동 방지.
2. **사용자 경험(UX)**: 복잡한 기상 차트나 raw JSON 대신 한눈에 들어오는 요약과 실생활 조언 제공.
3. **확장성**: Discord 봇, 웹 서비스, API 서버 등 다양한 인터페이스에 모듈 단위로 즉시 이식 가능.
