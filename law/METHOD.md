# 쟁점은 어떻게 잡히는가 -- 출처에서 가져온 절차

이 문서는 의견이 아니라 **인용**이다. "변호사는 이렇게 한다" 를 내 기억에서 적으면 그건
이 저장소가 막으려는 바로 그것(근거 없는 단정)이 된다. 그래서 세 갈래에서 끌어왔고,
어디서 무엇을 가져왔는지 항목마다 적었다.

> **확인 경로 주의.** 이 세션의 조직 egress 정책이 arxiv.org · aclanthology.org ·
> proceedings.neurips.cc · 대부분의 학술 호스트를 막는다(403). 그래서 아래 내용은
> **검색 결과 요약으로 확인한 것**이고 원문 PDF 를 열어 대조한 것이 아니다. 인용 문구는
> 검색이 돌려준 문장 수준까지만 신뢰할 것. 쪽수·정확한 표현이 필요하면 원문을 봐야 한다.
> (같은 이유로 조문 원장도 `law/corpus/` 에 사람이 넣는다 -- 심판이 대조하는 자리에
> 확인 안 된 텍스트를 넣지 않는다.)

---

## 1. 독일 -- 규범에서 사안으로 (요건사실론의 뿌리)

한국의 요건사실론은 일본 사법연수소를 거쳐 들어온 독일 법학방법론이다. 위키백과
'요건사실론' 항목은 이것을 "일정한 법률효과를 발생시키는 **법률요건을 확정한 뒤** 그에
해당하는 사실에 관한 **주장·증명책임의 소재**와 당사자가 제출하여야 하는 **공격방어방법의
배열**을 명확히 하는" 것으로 적는다. 세 덩어리가 그대로 스키마가 된다.

### 1-1. Gutachtenstil -- 한 요건을 검토하는 최소 단위 (4단계)

독일 법과대학 교안이 한결같이 적는 순서다:

    Obersatz  -> Definition -> Subsumtion -> Ergebnis
    (가설)      (요건 정의)   (사안 대입)    (결론)

- **Obersatz** 는 민사에서 `Wer will was von wem woraus?`(누가 · 무엇을 · 누구에게 ·
  무슨 근거로) 형식이어야 한다. 당사자 · 청구 목적 · 근거 조문이 그 안에 다 들어간다.
- **Definition** 은 검토할 요건을 추상적으로 정의한다.
- **Subsumtion** 은 사안이 그 정의에 "맞는지" 본다.
- **Ergebnis** 는 Obersatz 를 긍정 또는 부정으로 닫는다.

출처: Uni Trier 교안 `UEbersicht_Subsumtion_und_Gutachten.pdf`, FU Berlin 교안
`__8_Gutachtenstil.pdf`, Lecturio/JurCase 해설.

**여기서 가져온 것:** 쟁점은 문단이 아니라 **요건 하나에 대한 닫힌 질문**이다. 근거 조문과
당사자가 없으면 Obersatz 가 못 서고, Obersatz 가 없으면 쟁점이 아니다.

### 1-2. Anspruchsprüfung -- 민사 청구의 3단계 순서

    1. Anspruch entstanden        청구권이 발생했는가   (rechtshindernde Einwendung 없음)
    2. Anspruch nicht untergegangen  소멸하지 않았는가  (rechtsvernichtende Einwendung 없음)
    3. Anspruch durchsetzbar      관철 가능한가         (rechtshemmende Einrede 없음)

결정적인 구별 하나: **Einwendung 은 직권으로 고려되지만, Einrede(항변)는 의무자가
원용해야만 고려된다.** 검색이 돌려준 문장 그대로: "Rechtshemmende Einwendungen are
generally not considered ex officio but only when invoked by the obligor, and are called
Einreden." 같은 단계 안에서 항변들 사이의 검토 순서는 대체로 무의미하다.

출처: jura-online.de `Anspruchsaufbau` / `Durchsetzbarkeit von Ansprüchen (Einreden)`,
Uni Trier `rep_sonst_anspruch.pdf`, FU Berlin `AGschemataHähnchen.pdf`,
Springer `Prüfungsreihenfolge bei mehreren Anspruchsgrundlagen`.

**여기서 가져온 것:** 쟁점에는 **단계**가 붙는다(성립/소멸/행사). 그리고 원용이 필요한
항변사항을 원용도 없이 쟁점으로 세우면 그건 절차적으로 틀린 쟁점이다 -- 기계가 볼 수 있다.

### 1-3. 형법 -- 3단 구조의 순서 의존성

    Tatbestandsmäßigkeit -> Rechtswidrigkeit -> Schuld
    (구성요건 해당성)        (위법성)            (책임)

검색이 돌려준 문장: "The order is not arbitrary: only when there is conduct that satisfies
the criminal statute does the question of justification arise, and only when it is unlawful
does the question of culpability arise."

출처: rechtswissenschaft-verstehen.de `Dreistufiger Deliktsaufbau`, TU Dresden
`Uebersicht-zum-Deliktsaufbau.pdf`, Uni Potsdam 형법 교안.

**여기서 가져온 것:** 앞 단계가 무너지면 뒤 단계 쟁점은 **논할 자리가 없다.** 이건 취향이
아니라 순서 규칙이고, `novel/gate.py` 의 개연성 사슬(도달 가능성)과 같은 모양이다.

### 1-4. Relationstechnik -- 실무가 실제로 쟁점을 뽑는 방법

독일 사법연수생(Referendar)이 배우는 사건 처리 기법. 다섯 정거장으로 나뉜다:

| 정거장 | 무엇을 보는가 |
|---|---|
| Prozessstation | 소가 적법한가 (소송요건) |
| **Klägerstation** | **원고의 진술만으로** 청구가 이유 있는가 (Schlüssigkeit) |
| **Beklagtenstation** | **피고의 진술까지 넣으면** 이유 없어지는가 (Erheblichkeit) |
| Beweisstation | 증거조사 결과로는 어떻게 되는가 |
| Tenorierungs-/Entscheidungsstation | 주문을 어떻게 낼 것인가 |

Beklagtenstation 은 Klägerstation 과 구조가 동일하다(같은 요건표를 반대편에서 다시 돈다).

출처: de.wikipedia `Relationstechnik`, Jura Online `Relationstechnik`, Kaiserseminare
`kaiser-relationsklausur.pdf`, stephanherold.com `08_Relationsgutachten.pdf`.

**여기서 가져온 것 -- 이 문서에서 제일 중요한 대목.** 쟁점은 사람이 "중요해 보인다" 고
고르는 것이 **아니다.** 같은 요건표를 원고 쪽에서 한 번, 피고 쪽에서 한 번 돌렸을 때
**결론이 갈리는 자리**가 쟁점이다. 그러면 쟁점 도출은 판단이 아니라 **차집합 연산**이 된다.
LLM 에게 "쟁점을 뽑아줘" 라고 물을 이유가 없어진다.

### 1-5. Engisch / Larenz -- 시선은 규범과 사안 사이를 오간다

Engisch 의 표현 `Hin- und Herwandern des Blicks zwischen Obersatz und Lebenssachverhalt`
(대전제와 생활사안 사이를 오가는 시선). Larenz 가 `Methodenlehre der Rechtswissenschaft`
에서 이어받았다. 검색 요약: "the case to be decided often gains its contours only from the
applicable legal norm, while conversely the legal norm is chosen with regard to a specific
factual situation -- a special manifestation of the hermeneutic circle."

**여기서 가져온 것:** 요건 추출과 사실 추출은 **한 번에 끝나지 않는다.** 파이프라인이
'조문 -> 요건 -> 사실 대입' 한 방향 직선이면 안 되고, 요건이 사실을 다시 부르는 왕복이
있어야 한다. 다만 왕복은 무한할 수 있으므로 회수를 세고 끊는 것은 기계가 한다.

### 1-6. Savigny -- 해석기법 절(4절)의 근거

네 canones: **grammatisch · logisch · historisch · systematisch**. 검색 요약이 두 가지를
분명히 한다: (1) 넷은 서로 다른 방법이 아니라 **한 방법의 요소들**이고 위계가 없다,
(2) **목적론적 해석(teleologisch)은 Savigny 의 것이 아니다** -- 그는 자기가 인정한 네 개
밖의 기준으로 정해지는 '법의 목적' 을 해석 기준으로 인정하지 않으려 했다.

출처: de.wikipedia `Auslegung (Recht)`, klartext-jura.de, JURIQ `Die klassischen
Auslegungskriterien`.

**여기서 가져온 것:** 기존 문서의 '4. 해석기법' 절은 지금 임의로 이름 붙인 기법을 쓴다.
canon 을 **닫힌 목록**으로 두면 기계가 검사할 수 있다 -- 문언/체계/역사/목적 중 무엇을
썼는지 적게 하고, 목적론을 쓰면 Savigny 가 아니라 후대 방법론이라는 것까지 표시하게 한다.

### 1-7. Alexy -- 기계가 어디까지 볼 수 있는지를 정해주는 구분

`Theorie der juristischen Argumentation`: 법적 결정의 정당화는 **내적 정당화(interne
Rechtfertigung)** 와 **외적 정당화(externe Rechtfertigung)** 로 갈린다. 내적 정당화는
"결정이 인용된 전제들로부터 논리적으로 따라 나오는가" 이고 **판결삼단논법의 연역 구조**를
갖는다. 외적 정당화는 그 **전제들 자체**를 정당화하는 일이고, Alexy 는 여기에 여섯 논거군
(해석 · 도그마틱 · 선례 · 일반실천논증 · 경험논증 · 특수법적 논증형식)을 둔다.

**여기서 가져온 것 -- 이 저장소의 원칙에 딱 맞는 이론적 근거.** 기계 관문이 판정할 수 있는
것은 **내적 정당화**뿐이다. 전제가 옳은가(외적 정당화)는 기계의 관할이 아니다. 그래서
`law/gate.py` 가 "인용한 조문이 실재하는가 · 수량이 조문의 것인가 · 앞뒤가 모순인가" 만
보고 "법리가 타당한가" 는 안 보는 것이 임의의 절충이 아니라 **원리에 맞는 선긋기**다.

---

## 2. 미국 -- 사안에서 사안으로 (판례론)

독일 쪽이 규범에서 내려온다면 미국 판례론은 사안에서 옆으로 간다. 우리 파이프라인은
**판례 원장이 없어서 아직 판례를 인용하지 못하지만**(`law/gate.py` L004), 판례론이 쟁점
구조에 주는 것이 따로 있다.

### 2-1. Levi -- 판례법의 3단계

Edward H. Levi, *An Introduction to Legal Reasoning* (Univ. of Chicago Press, 1949;
원래 16 U. Chi. L. Rev. 501 (1948)). 검색이 돌려준 문장 그대로:

> "similarity is seen between cases; next the rule of law inherent in the first case is
> announced; then the rule of law is made applicable to the second case."

Levi 는 법적 추론이 "알려진 규칙 체계를 사실에 적용하는 것" 이라는 겉모습과 달리 실제로는
**앞선 사건과의 같음·다름을 정하는 과정**(reasoning by example)이라고 본다.

### 2-2. Goodhart -- ratio 는 '판사가 중요하다고 본 사실 + 그에 기초한 결정'

Arthur L. Goodhart, "Determining the Ratio Decidendi of a Case", 40 Yale L.J. 161 (1930).
핵심 두 가지: (1) **판결문에 적힌 논증이 곧 구속력 있는 원리가 아니다.** (2) ratio 를 찾으려면
먼저 판사가 **material 로 취급한 사실**과 그에 기초한 결정을 정해야 한다. Goodhart 의
문장: "It is by his choice of the material facts that the judge creates law."

### 2-3. Abramowicz & Stearns -- holding 의 정의

Michael Abramowicz & Maxwell Stearns, "Defining Dicta", 57 Stan. L. Rev. 953 (2005).
그들의 정의:

> "A holding consists of those propositions along the chosen decisional path or paths of
> reasoning that are actually decided, are based upon the facts of the case, and lead to
> the judgment."

그리고 'necessary to the outcome' 는 단독 기준으로는 **필요조건도 충분조건도 아니다.**

**여기서 가져온 것 -- 쟁점의 기계 판정 기준.** "판결에 이른다(lead to the judgment)" 를
뒤집으면 검사 가능한 조건이 나온다: **그 요건의 답이 갈릴 때 결론이 갈리는가.** 갈리지
않으면 그것은 쟁점이 아니라 방론이다. 이건 취향이 아니라 뒤집기 검사로 판정된다.

### 2-4. 판례 구속의 형식화 -- 쟁점이 구속의 단위다

- Frederick Schauer, "Precedent", 39 Stan. L. Rev. 571 (1987).
- Larry Alexander, "Constrained by Precedent", 63 S. Cal. L. Rev. 1 (1989) --
  natural model / **rule model** / result model 을 가른다. 검색 요약: rule model 에서는
  선례 법원이 "if X, Y, Z then decide for A" 라는 규칙을 선포하고 후행 법원이 그것에
  구속된다. Alexander 는 result model 을 "quite unattractive and perhaps ultimately
  incoherent" 라고 본다.
- John F. Horty & Trevor Bench-Capon, "A factor-based definition of precedential
  constraint", *Artificial Intelligence and Law* 20 (2012) -- HYPO/CATO 의 factor·dimension
  위에서 **reason model** 을 형식화한다. 법원은 앞선 결정이 내린 **이유들의 저울질과
  모순되지 않는** 결론에 구속된다.
- Trevor Bench-Capon & Katie Atkinson, "Precedential Constraint: The Role of Issues",
  ICAIL 2021 (DOI 10.1145/3462757.3466062) -- **구속을 쟁점 단위로 쪼갠다.**
- Trevor Bench-Capon, "Using Issues to Explain Legal Decisions", arXiv:2106.14688 (XAILA
  2021) -- 판결 설명의 구조를 **쟁점**이 준다.

**여기서 가져온 것:** 미국 AI&Law 전통에서 쟁점은 이미 **구속과 설명의 단위**로 쓰인다.
쟁점마다 찬성 요소(pro-plaintiff factor)와 반대 요소가 붙고, 그 저울질이 쟁점 단위로
비교된다. 우리 스키마가 쟁점에 '양측 주장' 을 필수로 두는 근거가 여기다 -- 한쪽 주장만
있는 것은 쟁점이 아니라 설명이다.

---

## 3. 한국 -- 다섯 갈래의 심사 순서

독일에서 순서를, 미국에서 판례 다루는 법을 가져왔다면 실제로 쓸 것은 한국법이다. 다섯
갈래 각각이 **자기 순서표**를 갖고 있고, 그 순서표가 곧 쟁점이 설 자리를 정한다.

### 3-1. 형법 -- 3단계 범죄체계론

    구성요건해당성 -> 위법성 -> 책임

합일태적 범죄체계론에서 범죄의 성립요건은 이 셋이다. 구성요건에 해당하고, 위법하며,
책임이 있어야 비로소 범죄가 된다. 위법성 단계는 **조각사유**(정당행위 · 정당방위 ·
긴급피난 등)가 있으면 위법성이 없고, 책임 단계도 조각사유(형사미성년자 · 심신상실자의
행위 · 강요된 행위)가 있으면 범죄가 성립하지 않는다.

출처: 위키문헌 『글로벌 세계 대백과사전』 「구성요건해당성」, 나무위키 「형법/총론」,
로톡 「범죄가 성립하기 위한 3단계」.

**독일 Deliktsaufbau(1-3)와 같은 구조이고 순서 의존성도 같다.** 그래서 코드에서는 형법과
독일 형법을 같은 단계 테이블로 다룬다.

### 3-2. 민법 -- 법률요건분류설

증명책임 분배의 통설·판례는 **법률요건분류설**이다. 법규의 구조·형식에서 기준을 찾고,
**각 당사자는 자기에게 유리한 법규의 요건사실을 증명**한다. 네 갈래로 나뉜다:

| 규정 | 누가 지는가 | 독일 대응 |
|---|---|---|
| 권리근거규정 | 권리 발생을 주장하는 쪽(원고) | Anspruchsgrundlage |
| 권리장애규정 | 다투는 쪽(피고) | rechtshindernde Einwendung |
| 권리소멸(멸각)규정 | 다투는 쪽(피고) | rechtsvernichtende Einwendung |
| 권리저지규정 | 다투는 쪽(피고) | rechtshemmende Einrede |

항변사유는 권리장애사실 · 권리소멸사실 · 권리저지사실로 갈린다.

출처: nepla 「증명책임의 분배」 · 「증명책임과 주장책임의 관계」, 나무위키 「증명책임」,
KCI 「법률요건분류설과 증명책임의 전환」 · 「항고소송에서의 증명책임 분배」.

**한국 민법의 4분류가 독일 3단계(1-2)와 그대로 대응한다.** 코드의 단계 테이블이 둘을
같은 것으로 다루는 근거가 여기다 -- 내가 맞춘 것이 아니라 계수 관계가 그렇다.

### 3-3. 민사소송법 -- 변론주의와 쟁점정리, 그리고 기판력의 범위

- **변론주의**: 사실인정의 기초가 되는 소송자료 제출은 당사자의 책임이다. **주요사실의
  주장책임은 당사자에게 있고**, 자백의 구속력도 변론주의가 적용되는 주요사실에 한한다.
  직권증거조사는 예외다.
- **쟁점정리는 절차로 제도화되어 있다.** 변론준비절차는 변론이 효율적·집중적으로
  실시되도록 **당사자의 주장과 증거를 정리**하는 절차다. 서면 변론준비절차는 4개월 내에
  마쳐야 하고, 그 안에 쟁점정리가 끝나면 변론기일로, 못 끝내면 **변론준비기일(쟁점정리
  기일)** 을 지정해 마저 한다.
- **기판력은 주문에 포함된 것에 한한다**(민사소송법 제216조 제1항). 판결이유 중의 판단에는
  미치지 않는다. **유일한 예외가 상계 항변**으로, 상계를 주장한 청구의 성립 여부 판단은
  **상계로 대항한 액수 한도에서** 기판력을 갖는다(같은 조 제2항).

출처: 대한민국 법원 전자민원센터 「변론준비기일(쟁점정리)」, 찾기쉬운 생활법령정보
「변론절차」, 국가법령정보센터/CaseNote 민사소송법 제216조, nepla 「자백의 구속력」,
나무위키 「변론주의」.

**여기서 가져온 것 -- 2-3(holding)과 같은 자리를 한국법이 조문으로 말한다.** 판결이유 중의
판단은 원칙적으로 구속력이 없고, **결론(주문)에 액수만큼 영향을 준 상계 항변만** 예외로
구속력을 갖는다. 즉 한국 실정법도 "결론을 움직인 것" 과 "움직이지 않은 것" 을 갈라 대우한다.
우리 뒤집기 검사(J005)가 임의의 기준이 아니라는 근거다.

### 3-4. 형사소송법 -- 준비절차에서 쟁점을 확정한다

    공판준비절차(주장·입증계획 서면 / 공판준비기일)
      -> 모두진술 -> **쟁점 및 증거관계 정리**
      -> 부인하면 증거조사 / 인정하면 간이공판절차 회부
      -> 피고인신문 -> 최종변론 -> 변론종결 -> 선고

재판장은 효율적·집중적 심리를 위하여 사건을 공판준비절차에 부칠 수 있다. 공소사실·적용
법조를 **명확하게 하는 행위**와 그 **추가·철회·변경 허가**가 이 절차에서 이루어진다.

출처: 대한민국 법원 전자민원센터 「형사소송절차안내」 · 「형사소송절차 흐름도」,
찾기쉬운 생활법령정보 「공판절차 개요」, nepla 「공판 전 준비절차」, 나무위키 「공판준비절차」.

> **조문 번호는 여기 적지 않는다.** 이 항목을 조사하면서 검색 요약이 형사소송법 조문
> 대응을 틀리게 돌려줬다 -- "제307조(위법수집증거배제), 제308조의2(거증책임)" 이라고
> 적어 왔는데, 이는 통상 알려진 대응(제307조 증거재판주의 · 제308조의2 위법수집증거
> 배제)과 어긋난다. 어느 쪽이 맞는지는 **조문 원장으로만 정해진다.** 그래서 이 문서는
> 형소법 조문 번호를 단정하지 않고 비워둔다. `law/gate.py` 의 L001 이 문서에 요구하는
> 규율을 이 문서 자신에게도 적용한 것이다.
>
> 이건 이 파이프라인이 왜 필요한지를 보여주는 실측 사례이기도 하다. **요약 한 번을
> 거치는 것만으로 조문 대응이 뒤집혔다.**

### 3-5. 헌법 -- 적법요건과 본안 3단계 심사

    [적법요건] 청구인능력 · 자기관련성 · 직접성 · 현재성 · 보충성 · 청구기간
    [본  안]  1) 보호영역   기본권의 보호범위에 드는가
              2) 제한       공권력이 그것을 제한했는가
              3) 정당화     제한이 헌법적으로 정당화되는가

정당화 단계의 핵심 기준이 **과잉금지원칙 4요소**다: **목적의 정당성 · 수단의 적합성 ·
침해(피해)의 최소성 · 법익의 균형성.** 헌법재판소는 그 헌법적 근거로 대부분의 판례에서
**헌법 제37조 제2항**을 들고, 특히 "필요한 경우에 한하여" 라는 문구에서 비례원칙을
도출한다. 같은 항이 **본질적 내용 침해금지**도 정한다.

적법요건 쪽에서: 자기관련성은 반사적 이해관계만 갖는 제3자를 배제하고, 직접성은 집행행위를
거치지 않고 **법률 그 자체로** 자유 제한·의무 부과·권리 박탈이 생기는 경우를 말하며,
보충성은 다른 구제절차를 모두 거칠 것을 요구한다.

출처: 대한법률구조공단 「헌법소원(일반론) > **요건사실**」, 국가법령정보센터 대한민국헌법
제37조, 위키백과 「과잉금지의 원칙」, 법무법인 지평 헌법 칼럼(과잉금지원칙의 의의와 한계),
『헌법재판실무제요』(국회도서관 소장).

**여기서 가져온 것:** 헌법도 요건사실로 정리된다는 것을 법률구조공단이 항목 제목으로
보여준다. 그리고 적법요건 -> 본안은 **엄격한 순서 의존**이다(적법요건이 깨지면 본안 쟁점은
논할 자리가 없다). 과잉금지 4요소도 순서가 있는 연쇄라 앞이 부정되면 뒤를 볼 필요가 없다.
형법 3단계와 같은 모양이고, 코드에서 같은 도구로 다룬다.

### 3-6. 다섯 갈래를 한 표로

| 갈래 | 단계 (순서 의존) | 앞단계 부담 | 뒷단계 부담 |
|---|---|---|---|
| 민법 | 권리근거 -> 권리장애 -> 권리소멸 -> 권리저지 | 원고 | 피고 |
| 민사소송법 | (절차) 소송요건 -> 본안 / 주장 -> 증거 | 당사자(변론주의) | 당사자 |
| 형법 | 구성요건해당성 -> 위법성 -> 책임 | 검사 | 검사(조각사유 부존재) |
| 형사소송법 | 공소사실 특정 -> 증거능력 -> 사실인정 | 검사 | 검사 |
| 헌법 | 적법요건 -> 보호영역 -> 제한 -> 정당화(과잉금지 4) | 청구인 | 국가 |

이 표가 `law/issue.py` 의 단계 테이블 그대로다. 쟁점은 **어느 갈래의 몇 번째 단계에
걸려 있는지**가 정해져야 쟁점이고, 그게 정해지면 증명책임자도 따라 정해진다 -- 그래서
기계가 검사할 수 있다.

---

## 4. 기계 쪽 -- 무엇이 실제로 안 되는지에 대한 실측

### 4-1. 환각은 가정이 아니라 측정값이다

- Matthew Dahl, Varun Magesh, Mirac Suzgun, Daniel E. Ho, "Large Legal Fictions:
  Profiling Legal Hallucinations in Large Language Models", arXiv:2401.01301,
  *Journal of Legal Analysis* 16 (2024). 무작위 연방 판례에 대한 검증 가능한 질문에서
  환각률 **ChatGPT-4 58% ~ Llama 2 88%**.
- Varun Magesh 외, "Hallucination-Free? Assessing the Reliability of Leading AI Legal
  Research Tools", arXiv:2405.20362, *J. Empirical Legal Studies* 22 (2025).
  **Lexis+ AI 17%, Westlaw AI-Assisted Research 33%** 환각. 정확도는 각각 65% / 41%,
  Ask Practical Law AI 19%. 즉 **RAG 를 붙여도 없어지지 않는다.**

**여기서 가져온 것:** `law/gate.py` 의 L001(인용 실재성)과 L004(판례 인용 금지)가 과한
장치가 아니라는 근거. 상용 법률 RAG 도 3분의 1까지 틀리는데, 대조 원장 없이 통과시키면
그건 심판이 아니다.

### 4-2. 쟁점·요건 분해는 이미 벤치마크의 축이다

- Neel Guha 외, "LegalBench", arXiv:2308.11462 (NeurIPS 2023 D&B). **162개 과제**를
  IRAC(Issue-Rule-Application-Conclusion) 위에서 여섯 갈래로 나눈다: issue-spotting,
  rule-recall, rule-application, rule-conclusion, interpretation, rhetorical-understanding.
  issue-spotting 의 정의: "tasks in which an LLM must determine if a set of facts raise a
  particular set of legal questions, implicate an area of the law, or are relevant to a
  specific party."
- Sergio Servantez 외, "Chain of Logic: Rule-Based Reasoning with Large Language Models",
  arXiv:2402.10400 (Findings of ACL 2024). 여러 **요소(element)** 로 이루어진 합성 규칙을
  **분해(요소별 독립 판단) -> 재결합(논리식으로 합침)** 한다. IRAC 에서 착안했다고 밝힌다.
- Nils Holzenberger & Benjamin Van Durme, "Factoring Statutory Reasoning as Language
  Understanding Challenges", ACL 2021 / arXiv:2105.07903. 조문 추론을 Prolog 구조를 빌려
  네 과제로 쪼갠다: **argument identification · argument coreference · structure
  extraction · argument instantiation.** 앞의 셋은 조문만으로 가능하다.
- Cong Jiang & Xiaolei Yang, "Legal Syllogism Prompting", ICAIL 2023 / arXiv:2307.08321.
  대전제=법, 소전제=사실, 결론=판결.

**여기서 가져온 것:** 요건 분해(Chain of Logic) + 조문에서 요건·인자 뽑기(Holzenberger)는
LLM 이 **할 수 있다고 보고된** 일이다. 반면 "쟁점을 뽑아라" 는 그 자체로 평가가 어려운
열린 과제다. 그래서 **LLM 에게는 요건과 주장을 뽑게 하고, 쟁점은 기계가 도출한다.**

### 4-3. 한국어·독일어 쪽 최근 것

- KoBLEX, EMNLP 2025 / arXiv:2509.01324. 한국어 **조문 근거 다단계** 법률 QA.
  226문항(1홉 55 · 2홉 125 · 3홉 46; 4홉은 필터링에서 제거). ParSeR 검색과 LF-Eval 평가.
  -> 한국 법 QA 에서도 **조문 근거를 물고 가는 것**이 축이다.
- BenGER, arXiv:2605.28183. 독일법 **포섭 기반** 추론 벤치마크. 596개 서술형 사례 과제 +
  531개 도그마틱 과제. 루브릭이 **Gutachtenstil 을 그대로 축으로 쓴다**: issue
  identification · legal grounding · doctrinal knowledge · subsumption quality ·
  methodological structure.
  -> 우리 쟁점 스키마의 필드가 이 루브릭과 같은 자리를 짚는다.

### 4-4. 증명책임의 형식화

Henry Prakken & Giovanni Sartor, "Formalising arguments about the burden of persuasion",
ICAIL 2007; "A logical analysis of burdens of proof", in *Legal Evidence and Proof* (2009).
설득책임은 **어느 당사자가 무엇을 증명해야 이기는지**를 정하고 재판 내내 바뀌지 않는다.
설득책임을 진 주장은, 그것을 부정하는 주장을 엄격히 이기지 못하는 한 패배한다.

**여기서 가져온 것:** 쟁점에 '증명책임자' 필드가 있어야 하는 이유. 그리고 증명책임 배분이
단계에서 자동으로 따라 나온다(성립=청구자, 소멸·행사저지=상대방)는 것 -- 기계가 검사한다.

---

## 5. 위에서 나온 절차를 그대로 코드로

세 갈래가 같은 데로 모인다. **쟁점은 생성물이 아니라 도출물이다.**

    [1] 근거규범 확정        Anspruchsgrundlage / 구성요건        <- 조문 원장 대조
    [2] 요건 분해            Tatbestandsmerkmale, 단계 표시       <- Chain of Logic
    [3] 주장 배치            원고/피고(검사/피고인) 각자의 주장    <- Relationstechnik
    [4] Klägerstation        원고 주장만으로 청구가 서는가
    [5] Beklagtenstation     피고 주장을 넣으면 무너지는가
    [6] 쟁점 = [4]와 [5]가 갈리는 요건                            <- 차집합, 판단 아님
    [7] 결과 의존성 검사     답이 갈릴 때 결론이 갈리는가          <- Goodhart/holding
    [8] 포섭                 요건별 Gutachtenstil 4단계

LLM 이 하는 일은 [1][2][3][8] 이다 -- 전부 조문과 사실에 근거가 있어 대조 가능한 일이다.
**[4][5][6][7] 은 코드가 한다.** 그래서 "쟁점을 잘 뽑았는가" 가 취향 논쟁이 되지 않는다.

구현: `law/issue.py`(스키마와 도출) · `law/issuegate.py`(관문 J001~J009) ·
`tests/test_law_issue.py`(관문마다 RED/GREEN).

## 6. 이 문서가 말하지 않는 것

여기 있는 것은 **쟁점의 구조**에 대한 출처다. 어떤 쟁점이 실제로 이기는가, 어느 학설이
옳은가는 외적 정당화(1-7)의 문제이고 이 파이프라인의 관할이 아니다. 그리고 한국법 실무의
세부(요건사실 배분의 개별 판례 태도 등)는 위 출처들로 커버되지 않는다 -- 그건 사법연수원
『요건사실론』과 각 분야 실무제요를 봐야 하고, 이 저장소는 그것을 **조문 원장처럼 사람이
넣어주는 자료**로 다룬다.
