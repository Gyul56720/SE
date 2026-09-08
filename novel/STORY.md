# 스토리가 재미없다 -- 논문이 가리키는 구멍과 고친 자리

사용자 평(2026-09-08): "필력도 좋고 대사도 좋은데, 스토리가 재미없어."

문체는 잰 것으로 고쳤다(`style.ROPAN`, 원작 4편 378만 자). 스토리는 우리에게 잰 것이
없다. 그래서 **연구가 이미 잰 것**을 빌린다. 아래는 전부 실제 논문이고, 각각이 이
파이프라인의 어느 구멍을 가리키는지, 그래서 어디를 고쳤는지 적는다.

## 1. 재미는 사건이 아니라 사건을 보여 주는 순서에서 온다

**Brewer & Lichtenstein (1982), "Stories are to entertain: A structural-affect theory of
stories."** 그리고 그것을 실험으로 확인한 Hoeken & van Vliet (2000, *Poetics*).

이야기가 주는 정서는 셋뿐이고, 셋 다 **같은 사건을 다른 순서로 보여 주는 것**에서 온다.

| 정서 | 어떻게 | 독자가 아는 것 · 인물이 아는 것 |
|---|---|---|
| 서스펜스 | 결과를 **미룬다** | 독자가 위험을 먼저 안다, 인물은 모른다 |
| 궁금증 | 결과를 **먼저** 보여 주고 원인을 감춘다 | 독자가 결과만 안다 |
| 놀람 | 예상 밖인데 되돌아보면 근거가 있다 | 아무도 몰랐다, 그런데 앞에 있었다 |

Hoeken & van Vliet 은 독자가 결말을 **알고 있어도** 서스펜스가 선다는 것, 놀람 하나가
들어간 이야기가 더 높이 평가되고 더 잘 기억된다는 것을 보였다.

**구멍.** DRIFT 의 사건(`shock.draw` · `genre.event`)은 그 자리에서 **다 보여 준다.**
미루는 것도, 감추는 것도, 되돌아볼 근거를 심어 두는 것도 없다. 그래서 일은 많은데
긴장이 없다.

**고친 자리.** `tension.SHAPES` -- 덩어리마다 서스펜스 · 궁금증 · 놀람 중 하나를 꼴로
준다. 놀람은 여섯에 하나다(자주 놀라면 놀람이 아니다). 놀람은 반드시 [세계]에 이미
놓인 것에서 나와야 한다 -- 새 것을 꺼내 놀래키는 것은 속임수다.

## 2. 독자가 중요하다고 느끼는 사건은 인과로 많이 이어진 사건이다

**Trabasso & van den Broek (1985), "Causal thinking and the representation of narrative
events," *Journal of Memory and Language* 24.**

이야기를 사건들의 인과망으로 그리면, 독자가 **기억하고 · 요약에 남기고 · 중요하다고
판단하는** 사건은 극적인 사건이 아니라 **다른 사건과 인과로 많이 이어진 사건**이다.
연결이 없는 사건은 아무리 커도 요약에서 빠진다.

**구멍.** 사건축은 무작위로 뽑힌다. 앞 덩어리와 인과가 없다. 프롬프트는 "이미 있는 것에
붙여라" 고 하지만 **무엇에** 붙일지 안 준다. "일은 벌어지는데 재미없다" 의 정체가
이것이다 -- 연결이 없는 사건의 나열.

**고친 자리.**
- 추출이 `chain` 한 칸을 더 낸다: "앞 덩어리의 무엇 → 이번 덩어리의 무엇". 원장에 최근
  24개가 남는다.
- `tension.brief` 가 다음 덩어리에 그 사슬(없으면 가장 최근에 열린 것)을 **이름을
  대고** 주고, 이번 대목의 일은 그중 하나 **때문에** 벌어져야 한다고 한다.

## 3. 서스펜스 = 다음 순간 믿음이 얼마나 흔들릴 수 있는가

**Ely, Frankel & Kamenica (2015), "Suspense and Surprise," *Journal of Political Economy*
123(1).**

서스펜스를 **다음 기간 믿음의 분산**으로, 놀람을 **지난 기간 믿음과의 거리**로 정의하고
최적 정보 공개를 푼다. 결과가 뻔하면 분산이 0 이고, 서스펜스를 최대로 하려면 믿음이
한 방향으로 가지 않고 **오락가락**해야 한다.

Wilmot & Keller (2020, ACL) 은 이것을 언어모델로 재서 사람의 서스펜스 판정과 거의 같은
정확도를 얻었다 -- "앞으로 얼마나 불확실한가" 가 "지금 얼마나 뜻밖인가" 보다 잘 맞는다.

**구멍.** 성장 단계(`serial.STAGES`)는 마디 단위로 진다 → 버틴다 → 이긴다 다. 마디
안에서는 한 방향이다. 지는 마디는 내리 지고, 이기는 마디는 내리 이긴다 -- 분산이 죽는다.

**고친 자리.** `tension.swing` -- 셋에 하나는 단계와 **반대로** 간다. 지는 마디에서
작게 이기는 덩어리(웹소설이 사이다라고 부르는 것), 이기는 마디에서 되맞는 덩어리.

## 4. 서스펜스는 좋아하는 인물에게 나쁜 결과가 다가올 때만 선다

**Zillmann 의 정서적 성향 이론**, 그리고 그것을 확인한 **Knobloch-Westerwick & Keplinger
(2006), "Mystery appeal," *Media Psychology* 8(3).** 인물에 대한 개입이 서스펜스의
조건이고, 드라마는 **부정적 결과**에 매달려야 한다.

**구멍.** 관계 축에 "웃는 적" 이 있지만 뽑힐 때만 있다. 적이 수를 두지 않는 덩어리가
대부분이라 화자에게 다가오는 나쁜 결과가 없다. 위험이 없으면 서스펜스가 설 자리가 없다.

**고친 자리.** `tension.enemy_moves` -- 둘에 하나, 적이 이 대목에서 실제로 무엇을 한다.
독자는 그것을 보고 화자는 다는 못 본다(1절의 서스펜스와 맞물린다). 적에게 이유가 있어야
한다.

## 5. 궁금증은 무엇을 모르는지 아는 순간 생긴다

**Loewenstein (1994), "The psychology of curiosity," *Psychological Bulletin* 116(1).**
궁금증은 정보 간극이 **눈에 띌 때** 생긴다. 막연히 모르는 것은 궁금하지 않다.

한국 웹소설 연재가 회차 끝을 답이 안 난 자리에서 끊는 것이 이것의 실천이다(전기수가
가장 중요한 대목에서 침묵하던 것). 유료화 이후 회차 구조가 클리셰의 반복과 변주로
굳었다는 것은 KCI 논문(웹소설 유료화에 따른 플랫폼과 서사의 변화 양상 연구)이 짚었다.

**구멍.** 원장의 "열린 것" 은 추출기가 적을 뿐, 독자에게 그것이 열려 있다는 것을 **보여
주라**고는 안 한다. 그리고 덩어리가 정리된 자리에서 끝난다.

**고친 자리.** `tension.brief` 의 끊기 -- 마지막 문장은 답이 안 난 자리다. 정리는 다음
대목의 첫 줄이 한다. 독자가 무엇을 모르는지 알게 하고 끊는다.

## 참고: 형태 연구는 쓰지 않았다

Toubia, Berger & Eliashberg (2021, *PNAS*) 는 5만 편의 의미 진행을 재서 **빨리 움직이는
이야기가 더 좋아진다**(영화)는 것을 보였고, Boyd, Blackburn & Pennebaker (2020, *Science
Advances*) 는 4만 편에서 무대 → 진행 → 인지 긴장의 순서를 찾았지만 **규범 구조를
따르는 것과 인기는 무관**했다. 둘 다 "무엇을 쓰라" 를 주지 않아서 규칙으로 안 옮겼다.
빠른 진행은 이미 갈래 꾸러미가 "이 대목이 끝났을 때 세계가 달라져 있어야 한다" 로
시키고 있다.

## 재지 않는다

이 다섯은 아직 정규식으로 못 잰다. Wilmot & Keller 의 자는 언어모델 호출이 든다. 그래서
`tension.py` 는 **프롬프트만** 바꾼다. 잰 값이 생기면 그때 자를 단다 -- 지어낸 자는 안
단다(rhythm.py:116 이 겪은 것).

## 출처

- Brewer, W. F., & Lichtenstein, E. H. (1982). Stories are to entertain: A structural-affect theory of stories. *Journal of Pragmatics*, 6, 473–486. (Technical Report No. 265, ERIC ED222854)
- Hoeken, H., & van Vliet, M. (2000). Suspense, curiosity, and surprise: How discourse structure influences the affective and cognitive processing of a story. *Poetics*, 27(4), 277–286.
- Trabasso, T., & van den Broek, P. (1985). Causal thinking and the representation of narrative events. *Journal of Memory and Language*, 24, 612–630.
- Ely, J., Frankel, A., & Kamenica, E. (2015). Suspense and surprise. *Journal of Political Economy*, 123(1), 215–260.
- Wilmot, D., & Keller, F. (2020). Modelling suspense in short stories as uncertainty reduction over neural representation. *ACL 2020*, 1763–1788.
- Knobloch-Westerwick, S., & Keplinger, C. (2006). Mystery appeal: Effects of uncertainty and resolution on the enjoyment of mystery. *Media Psychology*, 8(3), 193–212.
- Loewenstein, G. (1994). The psychology of curiosity: A review and reinterpretation. *Psychological Bulletin*, 116(1), 75–98.
- Toubia, O., Berger, J., & Eliashberg, J. (2021). How quantifying the shape of stories predicts their success. *PNAS*, 118(26).
- Boyd, R. L., Blackburn, K. G., & Pennebaker, J. W. (2020). The narrative arc: Revealing core narrative structures through text analysis. *Science Advances*, 6(32).
- 웹소설 유료화에 따른 플랫폼과 서사의 변화 양상 연구. KCI ART002308911.

---

# 2. 플롯이 문제인가, 연출이 문제인가 (2026-09-08, 두 번째 물음)

사용자: "스토리랑 전개가 재미가 없어. 플롯이 재미가 없는 걸까? 연출을 못하는 걸까?"

**둘 다다. 그런데 뿌리는 하나다.** 이 파이프라인의 생성 단위는 3,200자 **덩어리**이고,
플롯도 연출도 그보다 **큰 단위(회차 · 장면)** 와 **작은 단위(비트)** 에 산다. 회차 층이
없다. 플롯 문제와 연출 문제는 그 빈 층을 양쪽에서 본 것이다.

## 실측 -- 지금 프롬프트

    길이 6,226자 · 머리표 9개 · "마라/말라" 12개 · "해라" 5개
    장면 · 회차 · 요약이라는 말: 3번 (전부 금지문 안에서)
    "줄거리를 미리 정하지 마라. 지금 문장에서 다음 문장이 나오게 하라."  (flow.py:1297)

## 플롯 쪽 -- 왜 재미없나

| 근거 | 무엇을 밝혔나 | 여기서는 |
|---|---|---|
| Tian et al. 2024 (EMNLP) | 사람 이야기는 서스펜스 · 각성이 높고 중반 이후 더 벌어진다. LLM 이야기는 **대좌절과 절정을 못 세운다** -- 그래서 긴장이 없다. 담화 특징을 명시하면 40% 넘게 나아진다 | 전환점이 **하나도 지정되지 않는다.** 사건축은 무작위이고 성장 단계는 마디 단위 방향뿐이다 |
| Papalampidi & Keller 2019 (TRIPOD) | 잘 짜인 이야기는 전환점 다섯 -- 기회 · 계획 변경 · 돌아올 수 없는 지점 · 대좌절 · 절정 -- 으로 여섯 단계가 나뉜다 | 빚(serial)은 **상태**다. 어느 빚이 대좌절이고 어느 것이 절정인지 없다 |
| Zwaan et al. 1995 (사건 색인 모형) | 독자는 인물의 **의도**(목표)를 축으로 이야기를 따라간다 | 회차마다 주인공이 **지금 원하는 것 · 방해 · 결과 미정**이 없다. 도착지는 방향이지 욕망이 아니다 |
| Yang et al. 2023 (DOC) · Mirowski et al. 2023 (Dramatron) | 계획 없는 장문 생성은 표류한다. 개요 → 장면 → 대사의 계층이 일관성을 만든다 | "줄거리를 미리 정하지 마라" 가 **원칙**이다. 문체를 위해 넣었고, 값은 플롯으로 치렀다 |

## 연출 쪽 -- 왜 재미없나

| 근거 | 무엇을 밝혔나 | 여기서는 |
|---|---|---|
| Chakrabarty et al. 2024 (TTCW, CHI) | 전문가 이야기는 **시간을 늘이고 줄인다**(장면 vs 요약). LLM 은 그 조작이 없다 -- 14개 검사에서 3~10배 덜 통과 | 모든 덩어리가 같은 꼴이다. 장면과 요약의 구분이 없고, 시간 압축을 시키지 않는다 |
| Tian et al. 2024 | LLM 이야기의 각성 곡선은 **평평**하다 | "이 대목이 끝났을 때 세계가 달라져 있어야" + 덩어리마다 새 사건 = 늘 중간 세기. 쌓이지 않는다 |
| Sternberg (설명의 배분) · Genette (순서 · 지속) | 연출은 **무엇을 언제 얼마나** 보여 주느냐다 | 화자는 꼬리 몇천 자만 본다. 긴장이 어디까지 쌓였는지 모르니 올릴 수도 없다 |
| 잰 것만 남는다 (이 저장소의 실측) | 추출 · 손질 루프가 모순과 리듬만 잰다 | 파이프라인은 **재는 것**을 최적화한다. 문체가 좋아진 이유가 그것이고, 긴장이 안 좋아진 이유도 그것이다 |

## 그래서 -- 회차 층을 넣는다

**A. 회차 각본, 호출 한 번** (권한다)
- 약 5,000자마다 디렉터(Claude)가 **회차 카드**를 낸다: 주인공이 이번 회차에 원하는 것 ·
  방해 · 답은 회차 끝에(극적 질문), 비트 셋(각각 장면인지 요약인지, 세기가 앞보다
  높은지), 이번 회차에 전환점이 오면 어느 것인지(다섯 중), 끝 갈고리.
- 덩어리는 자유 이어 쓰기가 아니라 **비트를 쓴다.** 문체 규율은 그대로다.
- 전환점 다섯을 빚 위에 얹는다: 첫 빚 = 기회, 중간 = 계획 변경 · 돌아올 수 없는 지점,
  마지막 앞 = 대좌절, 끝 = 절정. serial.STAGES 가 이미 그 방향이다 -- 이름을 붙이고
  회차 카드가 그것을 실행한다.
- 값: 회차당 호출 +1 (약 6%). Tian 의 실측이 이 방향에서 40% 를 봤다.

**B. 긴장 상태를 원장에** -- 추출이 "지금 무엇이 위협하고 얼마나 가까운가" 를 적고,
tension.brief 가 앞 회차보다 **높게** 시킨다. A 없이는 약하다.

**C. 연출 자** -- 비트마다 장면/요약을 지정하고 요약 비트에는 시간 압축을 허용한다.
"줄거리를 미리 정하지 마라" 를 뺀다. A 와 같이 간다.

**D. 재기** -- 회차마다 서스펜스를 언어모델로 잰다(Wilmot & Keller 2020 방식). 호출이
들어서 나중이다.

## 출처 (2절)

- Tian, Y. et al. (2024). Are Large Language Models Capable of Generating Human-Level Narratives? *EMNLP 2024*. https://aclanthology.org/2024.emnlp-main.978/
- Papalampidi, P., Keller, F., & Lapata, M. (2019). Movie Plot Analysis via Turning Point Identification. *EMNLP 2019*. https://aclanthology.org/D19-1180/
- Chakrabarty, T. et al. (2024). Art or Artifice? Large Language Models and the False Promise of Creativity. *CHI 2024*. https://dl.acm.org/doi/10.1145/3613904.3642731
- Mirowski, P. et al. (2023). Co-Writing Screenplays and Theatre Scripts with Language Models. *CHI 2023*. https://dl.acm.org/doi/full/10.1145/3544548.3581225
- Yang, K. et al. (2023). DOC: Improving Long Story Coherence With Detailed Outline Control. *ACL 2023*.
- Zwaan, R. A., Langston, M. C., & Graesser, A. C. (1995). The construction of situation models in narrative comprehension: An event-indexing model. *Psychological Science*, 6(5).
