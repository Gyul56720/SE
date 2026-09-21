# -*- coding: utf-8 -*-
"""S1 -- 선언 파일의 계보. Makefile 에서 .yml 을 거쳐 SKILL.md 까지."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "edu"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 정의, 유도, 예제, 짚기, 사고, 수  # noqa: E402
from bookA import 정리, 보조정리, 따름정리, 논문, 논문출처, 언어, 직무  # noqa: E402


def 점진공개비용(스킬수, 메타토큰=100, 본문토큰=5000, 발동확률=0.05):
    """스킬 n 개를 달았을 때의 기대 컨텍스트 비용 대 전부 싣기."""
    점진 = 스킬수 * 메타토큰 + 스킬수 * 발동확률 * 본문토큰
    전부 = 스킬수 * (메타토큰 + 본문토큰)
    return 점진, 전부, 전부 / 점진


def 이저장소의스킬():
    """이 저장소가 실제로 들고 있는 SKILL.md 들을 잰다."""
    뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    재 = []
    d = os.path.join(뿌리, ".claude", "skills")
    if os.path.isdir(d):
        for 이름 in sorted(os.listdir(d)):
            p = os.path.join(d, 이름, "SKILL.md")
            if os.path.exists(p):
                글 = open(p, encoding="utf-8").read()
                줄 = 글.count("\n") + 1
                # 앞머리(--- ... ---) 와 본문을 가른다
                앞 = ""
                if 글.startswith("---"):
                    끝 = 글.find("\n---", 3)
                    앞 = 글[3:끝] if 끝 > 0 else ""
                설명 = ""
                for l in 앞.splitlines():
                    if l.startswith("description:"):
                        설명 = l.split(":", 1)[1].strip()
                재.append((이름, 줄, len(앞), len(설명)))
    return 재


def ch_decl():
    스킬 = 이저장소의스킬()
    점진, 전부, 배 = 점진공개비용(40)
    총줄 = sum(s[1] for s in 스킬)

    c = 장(
        "S1", "선언 파일의 계보 — Makefile 에서 .yml, 그리고 SKILL.md 까지",
        "<code>.yml</code> 도 <code>SKILL.md</code> 도 누가 취향으로 고른 것이 아니다. "
        "<b>앞의 것이 무엇에 실패했는가</b>가 다음 것의 모양을 정했다. 그 사슬을 "
        "처음부터 따라가면, <b>새 파일 형식을 발명하는 법</b>도 같이 보인다.",
        쓰는것=["에이전트", "도구", "스키마", "런타임", "프레임워크", "컨텍스트예산",
             "접두사안정성", "선택적주입", "권한경계", "멱등성", "재현성"],
        내놓는것=["선언형", "명령형", "의존그래프", "고정점", "멱등한적용",
              "앞머리", "점진공개", "발동설명", "형식의배신", "구성표류",
              "선언파일계보"],
        특허="""<b>무엇을 앞머리에 올리는가</b>(발동 판단에 필요한 최소 정보)가
        발명 자리다. 앞머리+본문이라는 꼴 자체는 2008년 Jekyll 이고, 파일에 메타데이터를
        붙이는 것은 그보다 훨씬 오래됐다. 새로운 것은 <b>그 메타데이터를 읽는 쪽이
        컴파일러가 아니라 모형</b>이라는 점이다.""")

    c.날것(직무(["AIE.인터페이스", "NAV.깃", "NAV.코딩에이전트", "NAV.감사"]))

    c.글("""이 장은 다른 장들과 성격이 다르다. 수학이 아니라 <b>공학사</b>다. 그런데
    대학원 교재에 이것이 들어가야 하는 이유가 있다 &mdash; <b>에이전트 인프라
    엔지니어가 실제로 만드는 것의 상당 부분이 &lsquo;파일 하나의 규격&rsquo;</b>이기
    때문이다. 그리고 그 규격을 잘못 고르면 그 뒤 몇 년을 앓는다.""")

    # ------------------------------------------------------------------
    c.절("S1.1 첫 번째 갈림길 — 명령을 적을 것인가 사실을 적을 것인가")

    c.날것(정의("명령형 (imperative)",
              "<b>무엇을 하라</b>를 순서대로 적는 것. 셸 스크립트가 그렇다. "
              "읽는 쪽은 적힌 순서대로 실행하기만 한다."))
    c.날것(정의("선언형 (declarative)",
              "<b>무엇이 참이어야 하는가</b>를 적는 것. 순서는 안 적는다. "
              "읽는 쪽이 순서를 <b>스스로 정한다</b>."))

    c.글("""1976년 벨 연구소. 프로그램을 고칠 때마다 셸 스크립트로 전부 다시 컴파일하고
    있었다. Stuart Feldman 이 만든 <code>make</code> 가 한 일은 <b>순서를 안 적는
    것</b>이었다. 대신 &ldquo;<code>a.o</code> 는 <code>a.c</code> 에 딸려 있다&rdquo; 라는
    <b>사실</b>만 적게 했다. 무엇을 먼저 할지는 도구가 정한다.""")

    c.날것(정의("의존 그래프 (dependency graph)",
              "&lsquo;이것은 저것에 딸려 있다&rsquo; 를 간선으로 둔 방향 그래프. "
              "고리가 없으면(DAG) 위상 정렬이 존재하고, 그것이 실행 순서가 된다."))

    c.날것(정리(
        "선언은 순서를 잃어도 답을 안 잃는다",
        """규칙 집합이 고리 없는 의존 그래프를 이루고, 각 규칙의 결과가 그 입력에만
        딸린다고 하자(부작용 없음). 그러면 <b>위상 정렬을 만족하는 어떤 실행 순서를
        택해도 최종 상태가 같다.</b> 특히 서로 의존하지 않는 규칙들은 <b>병렬로</b>
        돌려도 된다.""",
        [("위상 정렬이란 모든 간선 <i>u</i>&rarr;<i>v</i> 에 대해 <i>u</i> 가 <i>v</i> 보다 먼저 오는 나열이다.",
          "정의. 고리가 없으면 반드시 하나 이상 존재한다."),
         ("규칙 <i>v</i> 의 결과는 그 입력들(선행자들의 결과)의 함수 <i>f</i><sub><i>v</i></sub> 다.",
          "부작용이 없다는 가정 &mdash; 전역 상태를 안 읽고 안 쓴다."),
         ("어떤 위상 순서에서든 <i>v</i> 가 실행될 때 선행자들은 모두 이미 실행됐다.",
          "1 의 정의가 바로 그것을 보장한다."),
         ("선행자들의 결과는 (귀납 가정에 의해) 순서와 무관하게 같은 값이다.",
          "그래프의 깊이에 대한 귀납 &mdash; 깊이 0(입력 없음)은 자명하다."),
         ("따라서 <i>f</i><sub><i>v</i></sub> 의 인자가 같고, 함수이므로 결과가 같다.",
          "같은 입력에 같은 출력 &mdash; 2 의 &lsquo;함수&rsquo; 라는 말이 이 걸음을 준다."),
         ("서로 선행 관계가 없는 두 규칙은 어느 쪽을 먼저 둬도 둘 다 위상 순서이므로, 동시 실행도 허용된다.",
          "5 가 순서 무관을 주고, 부작용이 없으므로 간섭도 없다."),
         ("<b>반대로 부작용이 있으면 이 정리가 전부 무너진다.</b>",
          "2 의 가정이 깨지면 4 의 귀납이 성립하지 않는다 &mdash; 같은 규칙이 언제 실행되느냐에 따라 다른 값을 본다."),
         ],
        가정="고리 없음 + 부작용 없음. <b>실제 Makefile 은 둘 다 자주 어긴다</b> &mdash; 그래서 <code>make -j</code> 가 가끔 깨지는 것이고, 그 문제를 정면으로 푼 것이 Nix 와 Bazel 이다."))

    c.날것(짚기("""<b>이 정리가 왜 이 책에 있나.</b> A5 의 오케스트레이션이 똑같은
    문제다. 하위 에이전트들을 병렬로 돌릴 수 있는가? <b>그들이 공유 상태를 안 건드릴
    때만</b>이다. 같은 파일을 두 에이전트가 고치면 정리 30 의 가정 7 에 걸린다.
    <b>&lsquo;선언형 워크플로&rsquo; 라는 말이 에이전트 프레임워크에 자꾸 나오는 이유가
    이것이다</b> &mdash; 순서를 안 적어야 도구가 병렬화·재시도·재개를 할 수 있다."""))

    c.날것(정의("멱등한 적용 (idempotent apply)",
              "같은 선언을 두 번 적용해도 결과가 같은 것. Terraform 의 "
              "<code>apply</code>, 쿠버네티스의 <code>kubectl apply</code> 가 이 성질을 "
              "노린다. <b>그래야 실패한 곳부터 다시 돌릴 수 있다</b>(A9 의 재개)."))

    c.날것(표("명령형과 선언형이 각각 파는 것.",
            ["", "명령형 (스크립트)", "선언형 (규격 파일)"],
            [["적는 것", "무엇을 하라, 순서대로", "무엇이 참이어야 하는가"],
             ["순서", "사람이 정한다", "<b>도구가 정한다</b> &mdash; 정리 30"],
             ["병렬", "사람이 직접 짜야", "공짜로 나온다"],
             ["재시도", "어디부터인지 사람이 안다", "<b>멱등하면 그냥 다시</b>"],
             ["표현력", "무엇이든 된다", "규격이 허용하는 것만"],
             ["샐 때", "&mdash;", "<b>탈출구</b>(<code>run:</code> · "
              "<code>provisioner</code>)로 명령형이 새어 들어온다"]]))

    # ------------------------------------------------------------------
    c.절("S1.2 무엇에 적을 것인가 — 형식의 계보")

    c.날것(유도("각 형식은 <b>앞의 것의 실패</b>에 대한 답이다", [
        ("<b>Makefile</b>(1976) &mdash; 셸 스크립트가 순서를 사람에게 떠넘겼다",
         "의존을 적게 하고 순서는 도구가 정한다. 그런데 <b>탭과 공백을 구별</b>하는 문법이 "
         "남았다 &mdash; 만든 사람이 &ldquo;이미 사용자가 열 몇 명 있어서 못 바꿨다&rdquo; 고 밝힌 자리"),
        ("<b>.ini · .conf</b> &mdash; 평평한 열쇠=값. 중첩이 안 된다",
         "설정이 조금만 커지면 <code>db.host</code> 처럼 점으로 계층을 흉내 내게 된다"),
        ("<b>XML</b>(1998) &mdash; 중첩과 스키마를 얻었다",
         "대신 사람이 못 읽는다. 같은 이름을 열고 닫느라 글자가 두 배고, "
         "Ant 의 <code>build.xml</code> 이 곧 &lsquo;XML 로 쓴 프로그램&rsquo; 이 됐다"),
        ("<b>JSON</b>(2001) &mdash; XML 의 장황함에 대한 답. 자바스크립트 리터럴의 부분집합",
         "가볍고 어디서나 파싱된다. 그런데 <b>주석이 없다</b> &mdash; 만든 사람이 "
         "일부러 뺐다(파서 지시문으로 악용되는 것을 봤기 때문). 설정 파일로 쓰기엔 치명적"),
        ("<b>YAML</b>(2001) &mdash; 사람이 <b>쓰기</b> 좋게. 들여쓰기로 구조, 주석 있음",
         "CI 설정의 기본값이 됐다: <code>.travis.yml</code>(2011) &rarr; "
         "<code>.github/workflows/*.yml</code>(2018) &rarr; 쿠버네티스 매니페스트 &rarr; Ansible"),
        ("<b>TOML</b>(2013) &mdash; YAML 의 모호함에 대한 반작용",
         "&ldquo;명백하게 하나로 읽히게&rdquo; 를 목표로 삼았다. <code>Cargo.toml</code> · "
         "<code>pyproject.toml</code> 이 여기"),
        ("<b>앞머리(front matter)</b>(2008, Jekyll) &mdash; 한 파일에 기계용 머리와 사람용 몸",
         "<code>---</code> 사이에 YAML, 그 밑에 마크다운. <b>이 꼴이 SKILL.md 의 직계 조상이다</b>"),
        ("<b>SKILL.md · AGENTS.md · CLAUDE.md</b>(2024&ndash;) &mdash; 읽는 쪽이 <b>모형</b>이다",
         "컴파일러는 문법만 보지만 모형은 <b>뜻</b>을 본다. 그래서 규격이 느슨해도 되고, "
         "대신 <b>언제 쓰라</b>는 것을 글로 적어야 한다 &mdash; 다음 절"),
    ]))

    c.날것(정리(
        "YAML 의 암묵 변환은 왕복을 깨뜨린다",
        """YAML 1.1 계열 파서는 따옴표 없는 스칼라를 <b>보고 짐작해서</b> 형을 정한다
        (<code>yes</code>·<code>no</code>·<code>on</code>·<code>off</code> &rarr; 불린,
        <code>1.0</code> &rarr; 실수, <code>NO</code> &rarr; 거짓).
        그러므로 <b>&lsquo;값 &rarr; 따옴표 없는 글자 &rarr; 값&rsquo; 왕복이 항등함수가 아니다</b>:
        문자열 <code>"NO"</code> 를 그렇게 적으면 불린 <code>false</code> 로 돌아온다.
        <b>어떤 문자열 값들은 따옴표 없이는 표현할 수 없다.</b>""",
        [("파서의 해석 함수 <i>P</i> 는 글자열을 값으로 보낸다: <i>P</i>(<code>NO</code>) = false.",
          "YAML 1.1 의 불린 정의에 <code>n|N|no|No|NO</code> 가 들어 있다 &mdash; 노르웨이 국가코드가 유명한 사고다."),
         ("직렬화 함수 <i>S</i> 가 문자열 <code>\"NO\"</code> 를 따옴표 없이 <code>NO</code> 로 적었다고 하자.",
          "&lsquo;따옴표를 안 쓴다&rsquo; 는 가정 &mdash; 사람이 손으로 적을 때의 기본 습관이다."),
         ("<i>P</i>(<i>S</i>(<code>\"NO\"</code>)) = <i>P</i>(<code>NO</code>) = false &ne; <code>\"NO\"</code>.",
          "1 과 2 를 합성한 것. 값이 바뀌었다."),
         ("따라서 <i>P</i>&middot;<i>S</i> 가 항등이 아니다 &mdash; 왕복이 깨졌다.",
          "3 이 반례다."),
         ("게다가 <i>P</i> 는 <b>단사도 아니다</b>: <code>no</code>, <code>No</code>, <code>NO</code>, <code>off</code>, <code>false</code> 가 전부 false 로 간다.",
          "여러 글자가 한 값으로 가므로 역함수가 없다."),
         ("그러므로 &lsquo;원하는 값&rsquo; 을 되찾으려면 <b>따옴표라는 추가 정보</b>가 필요하다.",
          "5 에서 역함수가 없으니, 표현 쪽에 구별자를 더하는 수밖에 없다."),
         ("<b>이것이 형식의 성질이지 파서의 버그가 아니다.</b> YAML 1.2 는 불린을 줄였지만 많은 구현이 1.1 동작을 유지한다.",
          "규격이 바뀌어도 이미 깔린 파서들이 안 바뀌므로 실무에서는 여전히 걸린다."),
         ],
        가정="YAML 1.1 계열 파서. 1.2 순정 파서에서는 <code>NO</code> 가 문자열이지만, 실무에서 쓰이는 라이브러리 상당수가 1.1 호환 모드다."))

    c.날것(사고("""<b>이 저장소의 형제 사고.</b> CLAUDE.md 에 적힌 것 &mdash;
    <i>셸 스크립트에 한글 변수명을 쓰지 마라</i> &mdash; 가 정확히 같은 부류다.
    <code>초=25</code> 는 bash 에서 <b>대입이 아니라 명령어</b>로 파싱된다.
    <b>&lsquo;내가 쓴 것&rsquo; 과 &lsquo;도구가 읽은 것&rsquo; 이 다른데 아무도 안 터진다.</b>
    YAML 의 <code>NO</code> 와 bash 의 <code>초=25</code> 는 같은 병이고,
    같은 처방을 받는다 &mdash; <b>형식이 짐작하게 두지 말고 명시하라.</b>"""))

    c.날것(언어(
        "같은 설정 하나를 네 형식으로 — 그리고 각자가 배신하는 자리",
        [("YAML — 사람이 쓰기 가장 편하고, 가장 잘 배신한다",
          """version: 2
country: NO          # <- 불린 false 가 된다 (정리 31)
port: 08080          # <- 앞의 0 때문에 8진수로 읽는 파서가 있다
ratio: 1.0           # <- 문자열 "1.0" 을 원했다면 틀렸다
on:                  # <- GitHub Actions 의 'on' 키가 True 로 파싱되는 유명한 사고
  push:
    branches: [main]
cmd: >-              # >- 는 접은 줄 + 끝 줄바꿈 제거
  echo hello
  world""",
          "<code>on:</code> 이 불린 <code>True</code> 로 읽히는 것은 "
          "<b>GitHub Actions 사용자 거의 전부가 모르고 쓰는 사실</b>이다 &mdash; "
          "액션 쪽 파서가 그것을 되돌려 처리한다. 형식의 짐작을 도구가 덧대서 "
          "막고 있는 것"),
         ("JSON — 짐작이 없다. 대신 주석이 없다",
          """{
  "version": 2,
  "country": "NO",
  "port": 8080,
  "on": { "push": { "branches": ["main"] } }
}""",
          "<b>모호함이 0 이다</b> &mdash; 형이 글자에 다 적혀 있다. "
          "그래서 <b>기계끼리 주고받을 때</b>는 JSON 이 맞고(MCP 가 JSON-RPC 인 이유), "
          "사람이 손으로 고칠 파일로는 주석이 없어 힘들다"),
         ("TOML — 짐작도 없고 주석도 있다. 대신 깊은 중첩이 아프다",
          """version = 2
country = "NO"        # 문자열이 문자열이다
port    = 8080

[on.push]
branches = ["main"]

[[jobs]]              # 배열 안의 표
name = "test\"""",
          "<code>[[...]]</code> 로 표의 배열을 적는데, <b>세 겹 넘게 중첩되면</b> "
          "머리 경로가 길어져 읽기 어렵다. 그래서 Cargo/pyproject 처럼 "
          "<b>얕은 설정</b>에 잘 맞고 CI 워크플로처럼 깊은 것엔 덜 맞는다"),
         ("Dhall / CUE / Starlark — 설정에 <b>타입과 함수</b>를 준다",
          """// CUE: 값과 스키마가 같은 말로 적힌다
#Job: {
    name:    string & !=""
    runs_on: "ubuntu-latest" | "macos-latest"   // 합집합 타입
    timeout: int & >0 & <=360                    // 범위가 곧 타입
}
jobs: [...#Job]""",
          "<b>설정이 커지면 반드시 이 방향으로 간다</b> &mdash; 복붙이 늘고 "
          "오타가 배포를 깨기 때문이다. 대가는 <b>새 언어를 하나 더 배우는 것</b>이고, "
          "그래서 대부분의 팀이 YAML 에 주석을 달며 버틴다")],
        짚기="""<b>형식을 고르는 것은 &lsquo;누가 이 파일을 틀리게 쓸 것인가&rsquo; 를
        고르는 것이다.</b> 기계끼리면 JSON, 사람이 자주 고치면 TOML 이나 YAML,
        깊고 반복이 많으면 CUE 계열. 그리고 <b>어느 것을 고르든 검증기를 같이 만든다</b>
        &mdash; 형식이 막아 주지 않는 것은 전부 당신이 막아야 한다."""))

    # ------------------------------------------------------------------
    c.절("S1.3 읽는 쪽이 모형일 때 — 앞머리와 점진 공개")

    c.글("""여기서 계보가 꺾인다. <code>.yml</code> 까지는 읽는 쪽이 <b>프로그램</b>
    이었다. <code>SKILL.md</code> 부터는 읽는 쪽이 <b>모형</b>이다. 그 차이가 규격의
    모든 것을 바꾼다.""")

    c.날것(표("읽는 쪽이 바뀌면 무엇이 바뀌나.",
            ["", "컴파일러가 읽을 때", "모형이 읽을 때"],
            [["문법 위반", "즉시 오류", "<b>대개 그냥 읽어 낸다</b> &mdash; 더 위험하다"],
             ["모호함", "허용 안 됨", "글로 풀어 쓰면 됨"],
             ["&lsquo;언제 쓰나&rsquo;", "호출하는 코드가 정한다",
              "<b>파일 안에 글로 적어야 한다</b> &mdash; 이것이 새로운 부분"],
             ["비용", "파싱 시간", "<b>컨텍스트 토큰</b> &mdash; A6 의 예산"],
             ["확장", "버전 필드 · 스키마", "글을 더 쓰면 된다"],
             ["실패", "빌드 깨짐", "<b>조용히 안 쓰임</b> &mdash; 가장 나쁜 실패"]]))

    c.날것(정의("앞머리 (front matter)",
              "파일 맨 위의 <code>---</code> 사이에 넣는 기계용 메타데이터. "
              "그 아래는 사람(또는 모형)이 읽는 본문. <b>한 파일에 두 독자</b>를 "
              "담는 꼴이고, 2008년 Jekyll 이 퍼뜨렸다."))
    c.날것(정의("발동 설명 (triggering description)",
              "&lsquo;이 스킬이 무엇을 하고 <b>언제</b> 써야 하는가&rsquo; 를 적은 한 문단. "
              "모형이 요청과 대조해 스킬을 꺼낼지 정하는 <b>유일한 근거</b>다. "
              "규격상 필수이고 최대 1024자다."))
    c.날것(정의("점진 공개 (progressive disclosure)",
              "필요할 때 필요한 만큼만 컨텍스트에 싣는 것. 스킬은 세 층이다 &mdash; "
              "<b>메타데이터</b>(항상), <b>본문</b>(발동될 때), "
              "<b>딸린 파일·스크립트</b>(읽거나 실행할 때)."))

    c.날것(논문(
        "Agent Skills — 공식 규격 (Anthropic, platform.claude.com 문서)",
        "platform.claude.com/docs/en/agents-and-tools/agent-skills/overview", "전문",
        """Skills use Claude's VM environment&hellip; This filesystem-based architecture
        enables {1}progressive disclosure: Claude loads information in stages as needed,
        rather than consuming context upfront{/1}.
        &mdash; Level 1: Metadata (always loaded). The Skill's YAML frontmatter provides
        discovery information&hellip; {2}The description is what Claude matches your request
        against when determining whether to trigger the Skill, so it must say both what
        the Skill does and when to use it{/2}. This lightweight approach means you can
        install many Skills without context penalty:
        {3}until a Skill is triggered, only its name and description occupy context{/3}.
        &mdash; Level 3: Scripts run through bash, and
        {4}only their output enters context{/4}.""",
        [("점진 공개 — 미리 다 싣지 않고 필요할 때 단계적으로",
          "이 장의 정리 32 가 그 비용을 수로 준다. 세 층의 토큰 비용이 "
          "각각 ~100 / &lt;5k / 0 이라고 문서가 못박는다."),
         ("description 이 발동 판단의 근거이므로 &lsquo;무엇을&rsquo; 과 &lsquo;언제&rsquo; 를 둘 다 써야",
          "<b>이것이 .yml 과 갈리는 지점이다.</b> CI 워크플로는 <code>on:</code> 필드가 "
          "기계적으로 발동을 정하지만, 스킬은 <b>자연어 설명과 요청의 대조</b>로 "
          "정해진다 &mdash; 규격이 아니라 글이 발동을 정한다."),
         ("발동 전에는 이름과 설명만 컨텍스트를 차지한다",
          "그래서 스킬을 수십 개 달아도 부담이 작다. 정리 32 가 이 주장을 "
          "&lsquo;발동확률 &lt; 1 이면 항상 이득&rsquo; 으로 정확히 만든다."),
         ("스크립트는 코드가 아니라 <b>출력만</b> 컨텍스트에 들어간다",
          "A7 의 도구 실행과 같은 원리다 &mdash; 결정적인 일은 코드에 맡기고 "
          "모형은 결과만 본다. 토큰도 아끼고 재현성(A3)도 얻는다.")],
        왜중요="""<b>확인수준이 &lsquo;전문&rsquo; 인 이 책의 유일한 자리다.</b> 이 문서는
        이 세션에서 실제로 끝까지 읽었다(<code>platform.claude.com</code> 이 열려 있었다).
        아래 규격 표의 숫자는 전부 그 문서에서 온 것이고, 추측이 아니다."""))

    c.날것(표("<code>SKILL.md</code> 규격 &mdash; <b>공식 문서에서 읽은 그대로.</b>",
            ["항목", "규칙", "왜 그런가 (이 책의 해석)"],
            [["<code>name</code>",
              "필수 · 최대 64자 · 소문자/숫자/하이픈만 · XML 태그 불가 · "
              "<code>anthropic</code>·<code>claude</code> 금지",
              "디렉터리 이름이자 식별자다. 대소문자 구별이 없는 파일시스템에서도 "
              "같게 보이려고 소문자만. 예약어 금지는 <b>사칭 방지</b>"],
             ["<code>description</code>",
              "필수 · 비어 있으면 안 됨 · 최대 1024자 · XML 태그 불가",
              "<b>발동의 유일한 근거.</b> 1024자 상한은 &lsquo;항상 실리는 것&rsquo; 이라 "
              "컨텍스트 예산의 문제 &mdash; 스킬 하나당 약 100 토큰"],
             ["1층 메타데이터", "항상 실림 · 스킬당 ~100 토큰", "발동 판단에 필요한 최소"],
             ["2층 본문", "발동될 때 · 5k 토큰 미만 권장", "절차 지식 &mdash; 워크플로와 주의"],
             ["3층 딸린 파일", "읽을 때만 · <b>안 읽으면 0</b>",
              "참고 자료는 크기 제한이 사실상 없다"],
             ["스크립트", "bash 로 실행 · <b>출력만</b> 컨텍스트에",
              "코드를 읽히는 대신 <b>돌린다</b> &mdash; 결정적이고 싸다"],
             ["놓는 자리 (Claude Code)",
              "<code>~/.claude/skills/</code>(개인) · "
              "<code>.claude/skills/</code>(프로젝트)",
              "<b>프로젝트 것은 git 에 들어간다</b> &mdash; 규율이 코드와 같이 버전 관리된다"]]))

    c.날것(정리(
        "점진 공개가 이득인 조건",
        """스킬 <i>n</i> 개, 스킬 하나의 메타데이터 <i>m</i> 토큰, 본문 <i>B</i> 토큰,
        한 대화에서 스킬 하나가 발동될 확률 <i>p</i> 라 하자. 기대 컨텍스트 비용은
        <div class="math">점진 공개: <i>n</i>(<i>m</i> + <i>pB</i>)
        &nbsp;&nbsp;&nbsp; 전부 싣기: <i>n</i>(<i>m</i> + <i>B</i>)</div>
        이므로 <b><i>p</i> &lt; 1 이면 언제나 점진 공개가 싸고</b>, 절약 배수는
        (<i>m</i>+<i>B</i>)/(<i>m</i>+<i>pB</i>) 다. <i>B</i> &gg; <i>m</i> 이면
        그 배수가 <b>1/<i>p</i> 에 가까워진다.</b>""",
        [("점진 공개에서 각 스킬은 메타데이터 <i>m</i> 을 확실히 싣는다.",
          "1층은 언제나 시스템 프롬프트에 들어간다 &mdash; 문서가 그렇게 말한다."),
         ("본문 <i>B</i> 는 발동될 때만 실리므로 기댓값이 <i>pB</i> 다.",
          "확률 <i>p</i> 로 <i>B</i>, 아니면 0 인 확률변수의 기댓값."),
         ("기댓값은 선형이므로 스킬 <i>n</i> 개의 합이 <i>n</i>(<i>m</i>+<i>pB</i>).",
          "독립이 아니어도 된다 &mdash; 기댓값의 선형성은 독립을 안 요구한다."),
         ("전부 싣기는 <i>p</i>=1 인 특수한 경우다.",
          "3 에 <i>p</i>=1 을 넣으면 <i>n</i>(<i>m</i>+<i>B</i>)."),
         ("<i>p</i>&lt;1 이면 <i>pB</i>&lt;<i>B</i> 이므로 점진이 작다.",
          "3 과 4 의 비교 &mdash; <i>m</i> 은 양쪽에 같이 있다."),
         ("배수 = (<i>m</i>+<i>B</i>)/(<i>m</i>+<i>pB</i>). <i>B</i>&gg;<i>m</i> 이면 <i>B</i>/(<i>pB</i>) = 1/<i>p</i>.",
          "분자·분모를 <i>B</i> 로 나누고 <i>m</i>/<i>B</i>&rarr;0 을 적용."),
         (f"대조: <i>n</i>=40 · <i>m</i>=100 · <i>B</i>=5000 · <i>p</i>=0.05 이면 "
          f"점진 {수(점진)} 토큰 대 전부 {수(전부)} 토큰 &mdash; {수(배, 3)} 배.",
          "문서가 준 수(~100 · &lt;5k)를 그대로 넣어 빌드할 때 계산했다."),
         ("<b>그리고 이 정리가 <i>p</i> 를 낮추는 것의 값어치도 말해 준다</b> &mdash; 발동 설명이 정확할수록 <i>p</i> 가 작아지고 절약이 커진다.",
          "6 의 배수가 1/<i>p</i> 이므로 <i>p</i> 를 반으로 줄이면 절약이 두 배다."),
         ],
        가정="발동이 스킬마다 독립일 필요는 없다(기댓값의 선형성). 다만 <b>여러 스킬이 동시에 발동되면</b> 실제 비용이 합으로 커진다 &mdash; <i>p</i> 를 &lsquo;평균 발동 수/<i>n</i>&rsquo; 으로 읽으면 그대로 성립한다."))

    c.날것(짚기(f"""<b>정리 32 의 마지막 걸음이 실무의 전부다.</b> 발동 설명이 부정확하면
    <i>p</i> 가 올라가고(엉뚱한 요청에 발동), 너무 좁으면 <i>p</i>=0 이 되어
    <b>있는데 안 쓰인다</b>. 후자가 더 흔하고 더 나쁘다 &mdash; <b>아무 일도 안 나므로
    아무도 모른다.</b> 이 저장소의 <code>jaso</code> 스킬 설명이
    {수(스킬[2][3] if len(스킬) > 2 else 0)}자로 긴 이유가 그것이다:
    &lsquo;자소서를 써 달라&rsquo; 만이 아니라 &lsquo;지원동기를 어떻게 쓰나&rsquo; ·
    &lsquo;AI 판별에 걸리나&rsquo; 까지 <b>사용자가 실제로 쓰는 말을 나열</b>해 두었다."""))

    c.날것(표(f"이 저장소가 실제로 들고 있는 스킬 {len(스킬)}개 (합 {수(총줄)}줄). "
            f"<b>빌드할 때 파일을 읽어 잰 것이다.</b>",
            ["스킬", "SKILL.md 줄 수", "앞머리 글자", "description 글자", "1024 한도 대비"],
            [[f"<code>{이름}</code>", f"{수(줄)}", f"{수(앞)}", f"{수(설명)}",
              f"{수(100*설명/1024, 3)}&nbsp;%"] for 이름, 줄, 앞, 설명 in 스킬]))

    # ------------------------------------------------------------------
    c.절("S1.4 같은 계보의 다른 가지 — CLAUDE.md · AGENTS.md · .yml")

    c.날것(표("에이전트가 읽는 파일 네 가지. <b>언제 실리는가가 전부를 가른다.</b>",
            ["파일", "언제 실리나", "누가 쓰나", "무엇에 쓰나"],
            [["<code>CLAUDE.md</code>",
              "<b>항상</b> (세션 시작에 통째로)",
              "그 저장소의 사람들",
              "어기면 안 되는 규율 &mdash; 짧아야 한다. 길면 컨텍스트를 상시 먹는다"],
             ["<code>AGENTS.md</code>",
              "항상 (도구에 따라)",
              "그 저장소의 사람들",
              "도구 중립 규약. 여러 코딩 에이전트가 같은 파일을 읽자는 합의"],
             ["<code>SKILL.md</code>",
              "<b>설명만 항상 · 본문은 발동될 때</b>",
              "그 일을 해 본 사람",
              "특정 작업의 절차 지식. 많이 달아도 싸다(정리 32)"],
             ["<code>.github/workflows/*.yml</code>",
              "에이전트 컨텍스트에 <b>안 실린다</b>",
              "그 저장소의 사람들",
              "<b>기계가 실행한다</b> &mdash; 모형이 읽을 필요가 없다"]]))

    c.날것(짚기("""<b>가장 흔한 설계 실수는 이 표의 첫 줄과 셋째 줄을 혼동하는 것이다.</b>
    &ldquo;중요하니까 CLAUDE.md 에 적자&rdquo; 가 쌓이면 CLAUDE.md 가 수천 줄이 되고,
    <b>모든 대화가 그 비용을 낸다.</b> 규칙은 두 종류로 갈라야 한다 &mdash;
    <b>언제나 참인 것</b>(CLAUDE.md, 짧게)과 <b>특정 작업을 할 때만 필요한 것</b>
    (SKILL.md, 얼마든지 길게). 이 저장소의 CLAUDE.md 가 &lsquo;백그라운드 실행&rsquo; ·
    &lsquo;rebase 금지&rsquo; 처럼 <b>어느 작업에서나 어길 수 있는 것</b>만 담고,
    자소서 절차는 스킬로 뺀 이유다."""))

    c.날것(정의("구성 표류 (configuration drift)",
              "선언 파일이 말하는 상태와 실제 상태가 갈라지는 것. "
              "<b>선언형의 고유한 병</b>이다 &mdash; 명령형은 애초에 &lsquo;지금 상태&rsquo; 를 "
              "주장하지 않는다."))
    c.날것(정의("형식의 배신 (format betrayal)",
              "적은 대로 읽히지 않는 것. YAML 의 <code>NO</code>(정리 31), "
              "Makefile 의 탭, bash 의 한글 변수명. <b>문법 검사는 통과하는데 "
              "뜻이 다르다</b> &mdash; 그래서 가장 늦게 발견된다."))

    c.날것(사고(f"""<b>이 저장소의 실측.</b> <code>.github/workflows/gates.yml</code> 의
    <code>cancel-in-progress</code> 를 무조건 <code>true</code> 로 두었더니,
    머지를 잇달아 하는 동안 main 의 게이트가 <b>여섯 번 연속 취소</b>됐다
    (#1744·#1747·#1751·#1754·#1770·#1773). 워크플로는 &lsquo;성공&rsquo; 도 &lsquo;실패&rsquo; 도
    아닌 &lsquo;취소&rsquo; 였고, <b>main 은 한 번도 결론이 안 났다.</b> 지금은
    <code>cancel-in-progress: ${{{{ github.ref != 'refs/heads/main' }}}}</code> 로
    <b>main 에서만 안 끊는다.</b> 선언 파일의 한 줄이 &lsquo;검사했는가&rsquo; 를
    통째로 결정한 자리다 &mdash; <i>검사하지 않은 초록불이 검사한 빨간불보다 나쁘다</i>
    의 워크플로판."""))

    c.날것(개념(
        "선언 파일을 검사하는 법",
        """<b>이론.</b> 선언 파일은 <b>실행되기 전에는 아무것도 안 알려 준다.</b>
        그리고 실행될 때는 대개 운영 중이다. 그래서 선언 파일은 <b>실행 전에
        검사하는 장치</b>를 반드시 같이 가져야 한다 &mdash; 형식이 막아 주는 것보다
        훨씬 많은 것을 사람이 막아야 하기 때문이다.""",
        어디에="""CI 워크플로 · 배포 매니페스트 · 스킬 · 에이전트 규율 파일""",
        언제="""파일을 고칠 때마다. <b>커밋 전</b>이 가장 좋다 &mdash; 머지하고 나서
        알면 이 저장소가 다섯 번 앓은 그 병이다(CLAUDE.md 의 &lsquo;머지하지 않은
        PR 의 명령&rsquo;)""",
        어떻게="""(1) 문법 검사(<code>yamllint</code> · <code>actionlint</code>) &rarr;
        (2) <b>스키마 검사</b>(JSON Schema · CUE) &rarr;
        (3) <b>의미 검사</b> &mdash; 이 저장소의 게이트처럼 &lsquo;이 규칙이 실제로
        걸리는가&rsquo; 를 <b>망가뜨려 보고</b> 확인 &rarr;
        (4) 스킬이면 <b>발동되는지</b>를 검사한다 &mdash; 설명만 있고 안 불리는
        스킬은 없는 것과 같다""",
        산업코드="""# (3) 이 핵심이다. 규칙이 '있다' 가 아니라 '문다' 를 검사한다.
def test_스킬_앞머리가_규격에_맞는다():
    for p in Path(".claude/skills").glob("*/SKILL.md"):
        head = p.read_text().split("---")[1]
        meta = yaml.safe_load(head)
        assert re.fullmatch(r"[a-z0-9-]{1,64}", meta["name"]), p
        assert 0 < len(meta["description"]) <= 1024, p
        assert "claude" not in meta["name"] and "anthropic" not in meta["name"]
        # 그리고 **일부러 망가뜨린 판**이 빨간불을 내는지도 본다
        assert not 규격검사({"name": "Claude-Thing", "description": ""})""",
        주의="""<b>(4) 를 검사하는 팀이 거의 없다.</b> 스킬이 안 불리는 것은
        오류가 아니라 <b>침묵</b>이고, 침묵은 검사에 안 걸린다. 최소한
        &lsquo;이 요청에는 이 스킬이 떠야 한다&rsquo; 는 표본 몇 개를 두고
        회귀로 돌려야 한다 &mdash; 이 저장소가 <code>test_dispatch.py</code> 로
        하는 일이 그것이다."""))

    c.날것(유도("이 장을 한 문단으로", [
        ("선언형은 순서를 도구에게 넘기는 거래다",
         "정리 30 &mdash; 부작용이 없으면 순서가 답을 안 바꾸고, 그래서 병렬·재시도·재개가 공짜"),
        ("각 형식은 앞의 것이 실패한 자리에 답한 것이다",
         "Make(순서) &rarr; XML(중첩) &rarr; JSON(장황함) &rarr; YAML(사람) &rarr; TOML(모호함)"),
        ("그리고 모든 형식은 어딘가에서 배신한다",
         "정리 31 &mdash; YAML 의 암묵 변환은 왕복을 깨뜨린다"),
        ("읽는 쪽이 모형이 되면 규격이 느슨해지고 <b>글</b>이 규격의 일부가 된다",
         "&lsquo;언제 쓰나&rsquo; 를 파일 안에 적어야 한다 &mdash; description 이 발동의 유일한 근거"),
        ("그러면 비용이 파싱 시간이 아니라 <b>컨텍스트 토큰</b>이 된다",
         "그래서 층을 나눈다 &mdash; 점진 공개"),
        ("그 층 나누기가 이득인 조건은 정확히 계산된다",
         "정리 32 &mdash; 발동확률 <i>p</i>&lt;1 이면 언제나, 절약은 대략 1/<i>p</i>"),
        ("그리고 선언 파일은 실행 전에 검사하지 않으면 아무것도 안 알려 준다",
         "문법 · 스키마 · <b>의미</b> · <b>발동</b> 네 층으로 검사한다"),
    ]))

    c.날것(논문출처([
        ["Anthropic, <i>Agent Skills</i> 공식 문서",
         "platform.claude.com/docs/en/agents-and-tools/agent-skills/overview",
         "<b>전문</b>", "S1.3 의 규격 표 전부 &mdash; 이 책에서 전문을 읽은 유일한 출처"],
        ["Feldman, <i>Make &mdash; A Program for Maintaining Computer Programs</i>",
         "Bell Labs (1979)", "<b>조각</b>", "S1.1 의 계보. 정리 30 은 직접 세웠다"],
        ["YAML 1.1 / 1.2 규격", "yaml.org", "<b>조각</b>",
         "정리 31 의 암묵 변환 &mdash; 이 세션에서 yaml.org 는 막혀 있었다"],
    ]))

    return c.완성()
