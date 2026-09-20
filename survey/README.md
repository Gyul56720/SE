# HLS IP 서베이 -- 재현 방법

`HLS_IP_Survey.pdf` (32쪽, JCN/IEEE 2단)를 만드는 전체 파이프라인.

    extract.py    /home/user/hls_study 의 25개 파일을 구조적으로 훑어 inventory.json 을 만든다
                  파일마다: 줄수·바이트·라이선스·머리말·include·template 수·class·#define·
                  루프 라벨·함수 정의(반환형+줄번호)·pragma(줄번호+전문)·타입 사용 횟수
    figs.py       IEEE 풍 선화 SVG 헬퍼
    fig_a/b/c.py  그림 19장 (아키텍처 다이어그램 + 실측 데이터 막대그래프)
    s1.py         표제·초록·I 서론·II 말뭉치와 방법론
    s3.py         III 선형대수 계열 (cholesky · qrf · svd · potrf)
    s4.py         IV 암호 계열 · V 신경망 계열 (FINN 16파일 전부)
    s6.py         VI 횡단분석 · VII 설계규칙 · VIII 한계 · IX 결론
    s7.py         부록 A(파일 전수) · B(pragma 전수 445개) · C(함수 전수 176개) · 참고문헌
    style.css     JCN 2단 레이아웃 (running head · Fig./Table 캡션 · 각주 running element)

    $ python3 extract.py && python3 fig_a.py && python3 fig_b.py && python3 fig_c.py
    $ python3 s1.py && python3 s3.py && python3 s4.py && python3 s6.py && python3 s7.py
    $ python3 -c "..."   # weasyprint 로 조립·렌더 (survey.html -> PDF)

## 왜 자동 추출인가

"빠짐없이 봤다" 는 주장이지 사실이 아니다. 부록 A~C 가 `inventory.json` 에서 **기계로**
생성되므로, 본문이 인용하는 모든 수(파일 수 · 줄 수 · 함수 176 · template 216 · class 75 ·
pragma 445)가 같은 원천에서 나온다. 기억으로 적은 수가 없다.

## 정직하게 적은 한계 (본문 VIII)

  · **한 파일도 컴파일하지 않았다.** ap_fixed.h · hls_stream.h 등 9개 헤더가 Vitis HLS
    설치본 안에 있어 공개 저장소에 없다. 회로 동작에 관한 모든 진술은 소스에서의 추론이다
  · 지연·면적·주파수를 **하나도 재지 않았고 보고하지도 않는다**
  · 함수 추출이 정규식 기반이라 매크로 생성 정의를 놓칠 수 있다 (과소계수 쪽으로 치우침)
  · 벤더 둘, 같은 FPGA 생태계 -- 공통점이 HLS 일반의 진실인지 사내 관행인지 가를 수 없다
  · 참고문헌마다 **어디까지 읽었는지**를 대괄호로 적었다 (전문 / 부분 / 안 읽음)

---

# IP 스펙 문서 (`HLS_IP_Specification.pdf`, 591쪽)

서베이 논문과는 **다른 문서**다. 서베이는 IEEE 2단 조사 논문이고, 이쪽은 디자인
하우스가 IP 를 넘길 때 같이 주는 **스펙 문서**다.

    srcapp.py       말뭉치 27파일(12,277줄) + 벤더헤더 51파일(38,760줄) 을
                    줄번호를 붙여 전문 그대로 HTML 로 옮긴다.  요약하지 않는다.
                    LLM 이 끼지 않는다 -- 디스크의 바이트를 그대로 복사한다.
    spec_style.css  1단 본문(스펙 문서는 2단을 안 쓴다) + 소스부록만 2단 5.9pt
    spec.py         표지 · 판본이력 · 목차(target-counter) · 9개 장 · 부록 A~F

    $ python3 extract.py && python3 extract2.py
    $ python3 fig_a.py && python3 fig_b.py && python3 fig_c.py
    $ python3 srcapp.py && python3 spec.py

## 목차 구조는 정하지 않고 **셌다**

AMD 가 Vitis Libraries 저장소에 IP 문서를 같이 공개한다. `solver/docs` ·
`security/docs` · `dsp/docs` 의 **.rst 127개**를 받아 절 제목을 뽑고 빈도를 매겼다.

    Overview 34 · Entry Point 29 · Device Support 29 · Template Parameters 29
    Ports 28 · Access Functions 27 · Design Notes 26 · Code Example 26
    Supported Data Types 20 · Implementation on FPGA 20 · Profiling 18 · Constraints 17

3~6장의 코어별 절이 이 순서다. `docs.amd.com` 은 이 환경에서 막혀 있고(000),
**읽지 않은 문서는 인용하지 않았다.**

## 수는 전부 한 원천에서 나온다

`inventory.json` / `deep.json` 이 유일한 원천이다. 손으로 적은 수는 없다.
프라그마 총계는 `pragma_lines` 길이 합과 **assertion 으로 대조**한다 --
첫 판이 파일별 `{종류:개수}` 사전의 **키만 세어 73** 을 냈다(정답 445).

## 정직하게 적은 것

  · 어느 코어도 합성하지 않았다 -> 타이밍·면적·주파수 수치가 **한 개도 없다**
  · 벤더 헤더가 비공개라던 초판 주장을 **철회**하고 판본 이력에 남겼다
  · `bnn-library.h` 가 헤더 3개를 놓친다던 주장도 **2/3 이 틀렸다** (clang -H 로 확인)
  · `vt_fft.hpp` 는 구현부가 404 라 **인터페이스만** 있다. 그렇게 적었다
