# 투기적 언롤 DFE IP -- 선행조사

조사일 2026-09-18. **코드보다 먼저 커밋한다** (G024, `spec/IP_투기적언롤DFE.md` 0단계).

## 조사 조건 -- 정직하게

**전문을 하나도 못 봤다.** 이 컨테이너에서 arxiv.org · nature.com · ieee 계열이 전부
EGRESS_BLOCKED 다. 아래는 **내 학습 지식**이고 검색 조각조차 아니다. 그래서 확인수준을
`[출처:기억]` 으로 적는다 -- `[출처:조각]` 보다 낮다. **인용으로 쓰지 않는다.**

## 가장 가까운 선행연구

| | 무엇 | 우리와 겹치는 곳 |
|---|---|---|
| 투기적(언롤) DFE 그 자체 | 1990년대부터 와이어라인 표준 구조. Kasturia & Winters 계열, 이후 모든 상용 SerDes | **완전히 겹친다. 새롭지 않다** `[출처:기억]` |
| 반속도/1-4속도 DFE | 고속 링크의 기본 아키텍처 | **완전히 겹친다** `[출처:기억]` |
| 언롤 깊이 대 면적 쓸기 | ASIC SerDes 논문에 사례가 있을 것 | 아마 겹친다 |

## 그래서 이것은 논문 주제가 아니다 -- 그것이 결정이다

**이 갈래는 처음부터 IP 개발로 간다.** 여덟 번 주제를 죽인 필터(논문 신규성)를
여기 적용하면 여기서도 죽는다. 적용하지 않는다.

  · 디자인하우스가 파는 IP 중 알고리즘이 새로운 것은 거의 없다
  · 파는 것은 **PPA · 인터페이스 · 검증 · 납품 패키지** 다
  · 참조 구현이 많은 것은 **비교 기준선이 많다**는 뜻이므로 IP 기준으로는 유리하다

**논문으로 낼 생각이면 이 문서가 그 자리에서 막는다.** 낼 것은 IP 다.

## 이 저장소에만 있는 빈틈 (그리고 그것이 우리가 짓는 이유)

```
afe.py:409   "그래서 고속 DFE 는 unrolled(투기적) 구조로 간다"   <- 이름만 부른다
eqrtl.py     ffe · ffe_da · dfe(직접형) · ffe_dfe · ffe_tbl · invrom
             ^^ 투기적 언롤 DFE 생성기가 없다
```

문헌의 빈틈이 아니라 **이 저장소의 빈틈**이다. IP 개발에서는 그것이 옳은 종류의 빈틈이다.

## 찾아본 질의 (전부 차단되어 결과를 못 봄)

- speculative unrolled decision feedback equalizer DFE loop unrolling 1 UI timing
- half-rate quarter-rate DFE architecture 112G PAM4 SerDes critical path
- unrolled DFE area cost speculation depth tradeoff ASIC
- DFE first tap feedback timing closure slicer count PAM4 3*4^N

## 아직 못 지운 가능성

1. 언롤 깊이 대 (면적 · Fmax · BER) 쓸기를 **sky130 같은 공개 PDK 로** 낸 표가 이미
   있을 수 있다. 확인 못 했다
2. 우리가 낼 "언롤만으로는 56 GBd 에 못 닿는다" 는 **afe.py 기본값에 의존**한다.
   실리콘 값이 다르면 결론이 움직인다. 감도를 같이 내야 한다
3. PAM4 언롤의 슬라이서 수를 `3*4^N` 으로 세는 것이 맞는지 -- 부분 투기(첫 탭만 4갈래,
   나머지는 직접형)로 줄이는 변형이 문헌에 있을 것이다. **이건 우리가 쓸기로 답한다**
