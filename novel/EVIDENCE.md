# 재미를 가르는 것 — 문헌에서 찾은 것과, 그래서 무엇을 할 것인가

> **읽은 깊이를 먼저 밝힌다.** 이 컨테이너의 망 정책이 학술 PDF 대부분을 막았다
> (Cambridge · Dagstuhl · Semantic Scholar · 국내 DB 전부 egress 차단). 그래서 아래는
> **초록과 요약 수준으로 읽은 것**이고, 전문을 본 것이 아니다. 수를 그대로 옮겨 쓰기
>전에 원문을 확인해야 한다. 확인 안 된 것은 아래에 표시해 두었다.

---

## 1. 제일 중요한 발견 — 구조를 지키는 것은 인기와 무관하다

**Boyd, Blackburn & Pennebaker (2020), *Science Advances*.** 소설·영화 각본 등 전통 서사
약 4만 편과 비전통 서사 약 2만 편을 계산언어학으로 재서, 보편 구조 셋을 찾았다.

| | 무엇 | 언어적 자국 | 언제 |
|---|---|---|---|
| **staging** (무대 세우기) | 장면과 관계를 깔아 준다 | 전치사 · 관사 | 도입에 최고 |
| **plot progression** (진행) | 사람이 서로에게 한다 | 조동사 · 부사 · 대명사 | 그 뒤로 상승 |
| **cognitive tension** (인지적 긴장) | 생각하고 따지고 원인을 캔다 | 인지처리 낱말 | 중후반 상승-하강 |

그리고 이 논문의 결론에 이런 문장이 있다:

> *"No evidence emerged to indicate that adherence to normative story structures was
> related to the popularity of the story."*
> (규범적 서사 구조를 따르는 것이 인기와 관련 있다는 증거는 나오지 않았다.)

**이것이 이 저장소가 이미 적어 둔 말의 외부 검증이다** -- README 6번, *"관문은 바닥을
지키지 천장을 만들지 않는다. 다 통과한 텍스트가 지루할 수 있다."*

**따라서**: 구조 축(staging · progression · tension)은 **리포트로만** 만든다. 게이트로
만들면 안 된다. 4만 편이 아니라고 말한 것을 우리가 강제할 이유가 없다.

## 2. 문체는 성공을 예측한다 — 다만 문학 소설에서

**Ashok, Feng & Choi (2013), EMNLP, "Success with Style".** 문체만으로 소설의 성공을
최대 84% 정확도로 갈랐다(영화 89%).

| | 성공작에 많다 | 성공작에 적다 |
|---|---|---|
| 품사 | 전치사 · 명사 · 대명사 · 한정사 · 형용사 | -- |
| 동사 | **생각하는 동사**(알아차렸다 · 기억했다) · 인용 동사(말했다) | **행동·감정을 그대로 말하는 동사**(원했다 · 울었다 · 환호했다) |

그리고 **성공할수록 가독성 지표(Flesch · Gunning Fog)는 낮았다.** 저자 본인이 인과가
아니라 상관이라고 못박았다.

**주의 -- 그대로 옮기면 안 된다.** 대상이 Gutenberg 의 문학 소설이다. 한국 웹소설
실무는 정확히 **반대**를 말한다(단문 · 가독성 · 모바일). 두 결론이 부딪히는 것이
아니라 **다른 시장의 이야기**다. 우리 표본이 로판이어야 하는 이유가 여기 하나 더 붙는다.

**쓸 수 있는 것은 동사 쪽이다.** "울었다 · 화가 났다" 로 감정을 직접 말하지 않고
생각과 인용으로 미는 것은 이미 `style.py` 의 규율("나는 아팠다 는 성의가 없다")과
같은 방향이고, 이제 근거가 붙었다.

## 3. 몰입은 네 차원으로 잰다 — 사람에게 물을 때 쓸 자

**Busselle & Bilandzic (2009), *Media Psychology*, "Measuring Narrative Engagement".**
서사 몰입을 넷으로 가른다. 전체 신뢰도 α ≈ .80 이상.

  1. **서사 이해** -- 이야기가 이해되는가
  2. **주의 집중** -- 딴생각이 안 나는가
  3. **서사적 현존** -- 그 세계 안에 있었는가
  4. **정서적 몰입** -- 인물의 일이 내 일 같았는가

즐거움 · 이야기 관련 태도 · 서사 처리의 생리 지표와 정적 상관이 확인됐다.

**따라서**: `SUCCESS.md` 의 B층에 내가 지어낸 2문항 대신 **이 네 차원을 쓴다.** 표준
도구가 있는데 자작 문항을 쓸 이유가 없다.

## 4. 서스펜스와 서프라이즈는 형식적으로 정의된다

**Ely, Frankel & Kamenica (2015), *Journal of Political Economy*, "Suspense and Surprise".**
베이즈 청중의 믿음 궤적으로 둘을 정의한다.

| | 정의 |
|---|---|
| **서스펜스** | **다음 시점 믿음의 분산**이 클수록 크다 |
| **서프라이즈** | **지금 믿음이 직전 믿음에서 멀수록** 크다 |

그리고 둘은 상충한다 -- 정보를 어떻게 흘리느냐로 어느 쪽을 키울지가 갈린다.

**여기가 우리 원장과 정확히 맞물린다.** `flow` 의 `open`(던져지고 아직 안 닫힌 것)이
곧 믿음의 분산을 만드는 것들이다. 몇 개가 동시에 열려 있고, 언제 닫히고, 닫힐 때
얼마나 뒤집히는가 -- 전부 셀 수 있다.

**PITQ (potentially inquiry-terminating questions).** 서스펜스는 아무 질문이나 열려
있다고 생기지 않고, **답이 나면 탐구가 끝날 수도 있는 질문**이 열려 있고 **다른 질문은
열린 채로** 남아 있을 때 생긴다. → 우리 `open` 을 **핵심 질문 / 곁 질문**으로 갈라야
한다는 뜻이다. 지금은 한 통이다.

## 5. 절단은 효과가 있다 — 다만 갚아야 한다

**절단신공 실험** (참가자 133명, 드라마 3~4화, 자기보고 + 피부전도 + 코르티솔). 절단은
**즐거움 · 각성 · 계속 볼 의향**을 모두 올렸다. Zeigarnik 효과(끝나지 않은 일이 더
오래 기억된다)가 그 바닥에 있다.

그런데 같이 나온 것이 더 중요하다: **다음 화가 중심 질문을 합리적인 시간 안에 풀지
않으면 몰입이 떨어진다.**

**따라서**: 절단만 세면 안 된다. **회수 주기**(`payoff`)를 같이 세야 한다. 빚만 쌓는
원고는 절단을 잘 하는 원고가 아니라 갚지 않는 원고다.

## 6. 대사 비중은 좋고 나쁨이 아니라 목소리다

**Lin & Hsieh (2019), LDK, "The Secret to Popular Chinese Web Novels".** 인기 웹소설의
언어 특징을 말뭉치로 쟀다. 키워드 · 기능어 · 어휘 다양성이 갈래·문체와 밀접했고,
**대사 비중은 그 이야기의 서술 목소리를 드러낸다**고 보고한다.

**따라서**: "대사가 많을수록 좋다" 는 명제가 아니다. **갈래마다 다른 값**이고, 그래서
갈래 저울에 두는 것이 옳다. 다만 그 수는 **로판 표본에서 나와야** 한다.

## 7. 로판이 무엇으로 굴러가는가 — 국내 학술

`대중서사연구` · `비교문학` 등에 실린 로맨스판타지 연구들이 공통으로 지목하는 것.

**신계급주의.** 불특정 시공간, 특히 **서유럽 왕정국가**가 배경이다. 인물들은 계급사회를
무리 없이 받아들이고, 뚜렷한 신분 질서가 세계의 전제다. 서사는 두 축이다 --
**귀족·왕족과의 혼인** 한 축, **거상·마법사 같은 전문 분야에서의 성공** 한 축.

**책빙의물.** 21세기 한국에 살던 인물이 **상층계급 인물에 빙의**한 뒤, 그 인물이 지닌
**부와 권력을 놓치지 않으려 권력 투쟁**을 벌인다. 기존 서사에 대한 상호텍스트적
해석에서 나왔고 차원이동 · 회귀 · 대체역사와 친연성이 있다.

**회귀물.** 복수에 성공하려면 **착하고 순종적인 성격에서 벗어나야** 한다. 그리고 회귀
후 가장 공을 들이는 것이 **사람**이다 -- 인재를 뽑고 주변 인물을 적재적소에 배치하는
**인적 재배치**가 우선한다.

**이것이 지금 우리 로판 팩에 빠져 있는 것이다.** 나는 혼약 · 파혼 · 사교계 예법을
넣었는데, 논문이 지목하는 엔진은 **권력 투쟁**과 **인적 재배치**다. 예법은 그 위에
얹히는 표면이다.

## 8. 실무가 말하는 수

전부 관행이고 학술 근거가 아니다. **가정으로 두고 연재로 검증한다.**

| 무엇 | 값 |
|---|---|
| 회차 분량 | 5,000~6,000자 (유료 연재 5,500자 권장) |
| 연재 주기 | 주 5~7회 |
| 이탈 최대 지점 | **1화 → 2화**. 3화까지 붙들면 그 뒤는 완만해진다 |
| 문체 | 단문 중심 · 대사 위주 · 문단이 짧다 (모바일) |
| 1화 | "1화에 모든 것을 갈아 넣는다" |

---

## 그래서 계획을 이렇게 고친다

### 고칠 것

| | 지금 | 근거 | 어떻게 |
|---|---|---|---|
| 1 | 로판 팩이 **사교계 예법**에 치우쳤다 | 7절 -- 엔진은 권력 투쟁과 인적 재배치다 | 관계·사건에 그 둘을 넣는다 |
| 2 | `outside: (0.10, 0.22)` | **근거 없음.** 내가 방금 지어낸 수다 | **뺀다** |
| 3 | B층이 자작 2문항 | 3절 -- 표준 도구가 있다 | 몰입 4차원으로 바꾼다 |
| 4 | `open` 이 한 통이다 | 4절 PITQ -- 핵심 질문과 곁 질문은 다르다 | 갈라서 센다 |
| 5 | 절단만 세려 했다 | 5절 -- 안 갚으면 몰입이 떨어진다 | `payoff`(회수 주기)를 같이 센다 |

### 안 할 것 — 그리고 그 이유

| | 왜 안 하나 |
|---|---|
| Boyd 의 3요소를 **게이트로** 만들기 | 1절. 4만 편에서 구조 준수와 인기가 무관했다. 리포트로만 |
| Ashok 의 "가독성이 낮을수록 성공" 을 로판에 적용 | 2절. 대상이 문학 소설이다. 웹소설은 반대 시장이다 |
| 대사 비중을 "높을수록 좋다" 로 두기 | 6절. 갈래의 목소리이지 품질 지표가 아니다 |
| 실무의 수를 targets 에 손으로 적기 | 8절은 관행이다. `targets.py` 규칙대로 **표본에서** 뽑는다 |

### 순서

1. **로판 팩에 권력 투쟁·인적 재배치를 넣는다** (7절) -- 표본 없이 지금 된다
2. **`outside` 짐작을 뺀다** (2번) -- 지금 된다
3. **`open` 을 핵심/곁으로 가른다** (4절 PITQ) -- 코드 작업
4. **`payoff` 축을 만든다** (5절) -- 3번 위에 얹힌다
5. **B층 문항을 몰입 4차원으로** (3절) -- 문서 작업
6. **로판 표본 → targets 재산출** -- 사람이 표본을 넣어야
7. **연재 → 연독률** -- 1절이 말하듯, 결국 이것만이 진짜 답이다

---

## 출처

- Boyd, Blackburn & Pennebaker (2020). The narrative arc: Revealing core narrative
  structures through text analysis. *Science Advances*.
  https://www.science.org/doi/10.1126/sciadv.aba2196
- Ashok, Feng & Choi (2013). Success with Style: Using Writing Style to Predict the
  Success of Novels. *EMNLP*. https://news.stonybrook.edu/newsroom/press-release/general/01062014choi/
- Busselle & Bilandzic (2009). Measuring Narrative Engagement. *Media Psychology* 12(4).
  https://www.tandfonline.com/doi/abs/10.1080/15213260903287259
- Ely, Frankel & Kamenica (2015). Suspense and Surprise. *Journal of Political Economy*
  123(1). https://www.journals.uchicago.edu/doi/abs/10.1086/677350
- The linguistic basis of narrative suspense (PITQ). *Language and Cognition*, Cambridge.
  https://www.cambridge.org/core/journals/language-and-cognition/article/linguistic-basis-of-narrative-suspense-narrative-suspense-depends-on-potentially-inquiryterminating-questions/5EE1B5222149BEC6D76B2BB4C354F67C
- Lin & Hsieh (2019). The Secret to Popular Chinese Web Novels: A Corpus-Driven Study.
  *LDK*. https://drops.dagstuhl.de/entities/document/10.4230/OASIcs.LDK.2019.24
- 절단신공 실험: The role of cliffhangers in serial entertainment.
  https://www.buffalo.edu/ubnow/stories/2023/06/hahn-cliffhangers.html
- 한국 웹소설의 '책빙의물'의 특성 연구 -- 로맨스판타지 장르를 중심으로. 대중서사연구.
  https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002623646
- 로맨스 판타지 웹소설의 신계급주의와 서사 특징 -- 책빙의물과 회귀물을 중심으로.
  https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002818510
- 로맨스 판타지의 성장 서사와 모빌리티. 비교문학.
  https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE11775219
- 웹소설 서술·연재 관행: 나무위키 「웹소설/특징/서술」
  https://namu.wiki/w/%EC%9B%B9%EC%86%8C%EC%84%A4/%ED%8A%B9%EC%A7%95/%EC%84%9C%EC%88%A0
