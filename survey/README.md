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
