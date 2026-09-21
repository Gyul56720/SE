# -*- coding: utf-8 -*-
"""R0 -- LangChain. 누가 왜 만들었고, 무엇이 되고 무엇이 안 됐나."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "edu"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 정의, 유도, 예제, 짚기, 사고, 수  # noqa: E402
from bookA import (정리, 보조정리, 따름정리, 논문출처, 언어, 직무, 레포,  # noqa: E402
                   소스, 말풀이)
import dia  # noqa: E402


def zoo(이름):
    여기 = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(여기, "zoo.json"), encoding="utf-8") as f:
        return json.load(f)[이름]


def ch_langchain():
    lc = zoo("langchain")
    파이썬 = lc["말"].get("Python", {})
    마크 = lc["말"].get("Markdown", {})

    c = 장(
        "R0", "LangChain — 처음으로 &lsquo;모형 위의 층&rsquo; 을 만든 것",
        "2022년 10월, 모형에 말을 거는 일은 <b>문자열을 이어 붙이고 답을 손으로 "
        "뜯는 것</b>이었다. LangChain 은 그 반복을 없애려고 나왔고, 그 과정에서 "
        "<b>지금 모든 프레임워크가 쓰는 낱말들</b>을 만들었다.",
        쓰는것=["에이전트", "프레임워크", "런타임", "도구", "스키마", "제어루프",
             "ReAct", "검색", "임베딩", "RAG", "메모리", "컨텍스트",
             "선언형", "하이럼의법칙", "채택비용"],
        내놓는것=["사슬", "프롬프트템플릿", "출력파서", "일관된인터페이스", "LCEL",
              "파이프연산자", "지연평가", "콜백", "추상화세금", "공급자중립",
              "러너블"],
        특허="""프레임워크의 <b>인터페이스</b>는 대개 특허가 안 된다. 발명이 일어나는
        자리는 그 인터페이스가 가능하게 하는 <b>최적화</b>다 &mdash; 일관된 계약 위에서
        배치·스트리밍·재시도·캐시를 <b>한 번만</b> 구현하는 것.""")

    c.날것(직무(["NAV.프레임워크", "NAV.RAG", "AIE.프레임워크"]
              if False else ["NAV.프레임워크", "NAV.RAG", "AIE.코어"]))

    # ------------------------------------------------------------------
    c.절("R0.1 먼저 말부터 — 이 장에서 걸려 넘어지는 낱말들")

    c.글("""이 부(11부)는 남의 코드를 읽는다. 코드를 읽을 때 사람을 멈추게 하는 것은
    알고리즘이 아니라 <b>낱말</b>이다. &ldquo;무엇으로 감싼다&rdquo;, &ldquo;추상화한다&rdquo;,
    &ldquo;주입한다&rdquo; 같은 말이 설명 없이 나오면 그 뒤가 통째로 안 읽힌다. 그래서
    장마다 이 표를 먼저 둔다.""")

    c.날것(말풀이([
        ("감싼다", "wrap",
         "이미 있는 것을 <b>그대로 두고</b> 그 바깥에 얇은 껍질을 씌워, 껍질이 대신 "
         "불리게 하는 것. 속은 안 바뀌고 <b>부르는 방법</b>만 바뀐다.",
         "선물을 포장하는 것과 같다. 물건은 그대로인데 겉모습이 통일된다. "
         "OpenAI·Anthropic·로컬 모형을 각각 감싸면 <b>부르는 쪽은 하나만 알면 된다</b>."),
        ("추상화", "abstraction",
         "여러 개의 서로 다른 것에서 <b>공통된 모양</b>만 뽑아 이름을 붙이는 것. "
         "그 이름으로 말하면 개별 차이를 몰라도 된다.",
         "&lsquo;추(抽)&rsquo; 는 뽑아낸다는 뜻이다. 차이를 버리고 공통을 <b>뽑아낸다</b>."),
        ("인터페이스", "interface",
         "&lsquo;이 이름의 함수를 이런 인자로 부르면 이런 것이 돌아온다&rsquo; 는 <b>약속</b>. "
         "구현이 아니라 약속이다.",
         "면(face)과 면이 맞닿는(inter) 자리. 두 쪽이 만나는 경계면이고, "
         "<b>경계면만 지키면 안쪽은 마음대로</b> 해도 된다."),
        ("계약", "contract",
         "인터페이스가 약속하는 것의 전부 &mdash; 인자·반환값뿐 아니라 "
         "<b>예외·순서·부작용</b>까지. 문서에 적힌 것만이 아니라 "
         "<b>사람들이 실제로 기대게 된 것</b>도 포함된다(S2 의 하이럼의 법칙).",
         "법률 용어를 그대로 빌렸다. 어기면 <b>부르는 쪽이 깨진다</b>."),
        ("주입", "injection / DI",
         "필요한 것을 <b>자기가 만들지 않고 밖에서 받는</b> 것. "
         "<code>llm = OpenAI()</code> 대신 <code>def __init__(self, llm)</code>.",
         "밖에서 안으로 <b>찔러 넣는다</b>. 이렇게 하면 검사할 때 가짜를 "
         "대신 넣을 수 있다 &mdash; 그것이 이 기법의 존재 이유다."),
        ("지연 평가", "lazy evaluation",
         "식을 <b>만들어만 두고 아직 계산하지 않는</b> 것. 값이 실제로 필요할 때 계산한다.",
         "게으르다(lazy). 시켜도 안 하고 있다가 <b>정말 필요해지면</b> 한다. "
         "덕분에 &lsquo;무엇을 할지&rsquo; 를 먼저 다 조립한 뒤 한꺼번에 최적화할 수 있다."),
        ("콜백", "callback",
         "&lsquo;이 일이 일어나면 이 함수를 불러 달라&rsquo; 고 미리 건네 두는 함수.",
         "되(back) 부른다(call). 내가 부르는 게 아니라 <b>그쪽이 나를 되부른다</b>."),
        ("직렬화", "serialization",
         "메모리 위의 객체를 <b>저장하거나 전송할 수 있는 바이트 줄</b>로 펴는 것. "
         "되돌리는 것이 역직렬화.",
         "줄(serial)로 세운다. 나무처럼 가지 친 구조를 한 줄로 늘어놓는 것."),
        ("제네릭", "generic",
         "&lsquo;어떤 타입이든 받는&rsquo; 을 <b>타입으로</b> 적는 것. "
         "<code>Runnable[Input, Output]</code> 은 &lsquo;Input 을 받아 Output 을 내는 "
         "러너블&rsquo; 이다.",
         "일반적(generic)이라는 뜻. 하나의 코드가 여러 타입에 두루 쓰인다."),
        ("추상 기반 클래스", "ABC, abstract base class",
         "<b>직접 만들 수는 없고</b> 물려받아서만 쓰는 클래스. "
         "&lsquo;이 함수들은 반드시 구현해라&rsquo; 를 강제한다.",
         "기반(base)이 되는 추상(abstract) 클래스. 파이썬에서는 "
         "<code>class X(ABC)</code> 로 적고, 빠진 메서드가 있으면 "
         "<b>인스턴스를 만들 때</b> 터진다."),
    ]))

    # ------------------------------------------------------------------
    c.절("R0.2 2022년 10월 — 무엇이 문제였나")

    c.날것(레포(
        "langchain-ai/langchain",
        "github.com/langchain-ai/langchain", lc["커밋"],
        [("첫 커밋", "<code>18aeb7201</code> &middot; <b>2022-10-24</b> &middot; "
                  "Harrison Chase &middot; 메시지는 한 줄, <code>initial commit</code>"),
         ("이 책이 읽은 커밋", f"<code>{lc['커밋']}</code> ({lc['커밋날'][:10]})"),
         ("규모", f"파이썬 {수(파이썬.get('줄', 0))}줄 &middot; "
                f"마크다운 {수(마크.get('줄', 0))}줄 &middot; "
                f"파일 {수(lc.get('파일수', 0))}개"),
         ("이 책이 읽은 파일",
          "<code>libs/core/langchain_core/runnables/base.py</code> &middot; "
          "첫 커밋의 <code>langchain/chains/llm.py</code>"),
         ("정직하게 적자면",
          "이 저장소는 <b>한 사람이 읽을 수 있는 크기가 아니다</b>. 이 장이 다루는 "
          "것은 <b>알맹이 하나</b>(Runnable 계약)와 <b>그 알맹이가 생기기 전</b>의 "
          "모습이다. 통합 코드 수백 개는 안 읽었고, 읽은 척도 안 한다")],
        한마디="이 장의 모든 수는 실제로 클론해 잰 것이다."))

    c.글("""2022년 10월의 상황을 정확히 재구성해 보자. GPT-3 API 가 있고, 사람들이
    그것으로 무언가를 만들기 시작했다. 그런데 <b>모든 프로젝트가 같은 네 가지를
    다시 짓고 있었다.</b>""")

    c.날것(dia.견줌(
        "2022년, 모든 프로젝트가 다시 짓던 것",
        ["프롬프트에 변수를 꽂는 문자열 조립",
         "모형 API 를 부르고 재시도·타임아웃을 거는 코드",
         "답에서 원하는 조각을 뜯어내는 파서",
         "그 셋을 이어 붙이는 흐름 제어",
         "그리고 모형을 바꾸면 <b>전부 다시</b>"],
        "LangChain 이 이름을 붙인 것",
        ["PromptTemplate — 변수 꽂기",
         "LLM / ChatModel — 공급자 중립 껍질",
         "OutputParser — 답을 자료로",
         "Chain — 이어 붙이기",
         "이름이 생기자 <b>남의 것을 가져다 쓸 수</b> 있게 됐다"],
        제목="R0.2 — 프레임워크가 하는 일은 대개 '이름을 붙이는 것' 이다",
        폭=640, 왼색="빨강", 오른색="초록"))

    c.날것(정의("사슬 (chain)",
              "여러 걸음을 <b>순서대로</b> 이어 하나처럼 부르게 만든 것. "
              "LangChain 의 이름이 여기서 나왔다 &mdash; Lang(uage model) + Chain."))
    c.날것(정의("프롬프트 템플릿 (prompt template)",
              "변수 자리를 비워 둔 프롬프트. <code>\"{question} 에 답하라\"</code> 처럼 "
              "적어 두고 실행할 때 값을 꽂는다. <b>프롬프트를 코드에서 떼어내는</b> "
              "첫걸음이었다."))
    c.날것(정의("출력 파서 (output parser)",
              "모형이 낸 <b>글</b>을 프로그램이 쓸 <b>자료</b>로 바꾸는 것. "
              "B1 의 제약 디코딩이 나오기 전에는 이것이 유일한 방법이었다 "
              "&mdash; 뱉게 두고 뜯는다."))
    c.날것(정의("공급자 중립 (provider-agnostic)",
              "OpenAI 든 Anthropic 이든 로컬 모형이든 <b>같은 방법으로</b> 부르게 "
              "만드는 것. 프레임워크가 파는 물건의 상당 부분이 이것이다."))

    c.날것(소스("lc_llmchain_2022",
             설명="""<b>2022년 10월 24일, 첫 커밋의 <code>LLMChain</code>.</b>
             지금의 LangChain 과 전혀 다르게 생겼다 &mdash; 그리고 바로 그래서
             읽을 값어치가 있다. <b>프레임워크의 알맹이가 무엇이었는지</b>가
             40줄 안에 다 보인다.""",
             풀이=[
                 (11, "<b><code>class LLMChain(Chain, BaseModel)</code></b> &mdash; "
                      "두 개를 물려받는다. <code>Chain</code> 은 &lsquo;이어 붙일 수 있는 "
                      "것&rsquo; 이라는 약속이고, <code>BaseModel</code> 은 pydantic 의 "
                      "것으로 <b>타입 검사와 직렬화</b>를 공짜로 준다"),
                 (14, "<code>prompt: Prompt</code> &mdash; 프롬프트가 <b>문자열이 아니라 "
                      "객체</b>다. 이 한 줄이 &lsquo;프롬프트를 코드에서 떼어낸다&rsquo; 의 시작"),
                 (15, "<code>llm: LLM</code> &mdash; 모형도 <b>주입</b>된다. 안에서 "
                      "<code>openai.Completion.create</code> 를 직접 부르지 않는다. "
                      "그래서 검사할 때 가짜 모형을 넣을 수 있다"),
                 (20, "<code>extra = Extra.forbid</code> &mdash; <b>모르는 필드를 "
                      "거절한다.</b> 오타 난 인자가 조용히 무시되는 것을 막는 설정이고, "
                      "프레임워크가 <b>사용자의 실수를 잡아 주기로</b> 한 첫 자리다"),
                 (25, "<code>input_keys</code> &mdash; &lsquo;나는 이 이름들을 받는다&rsquo; 를 "
                      "<b>자기가 선언한다.</b> 이어 붙이는 쪽이 앞 걸음의 출력과 "
                      "뒤 걸음의 입력이 맞는지 <b>실행 전에</b> 볼 수 있게 된다"),
                 (30, "<code>output_keys</code> &mdash; 짝이 되는 선언. 이 둘이 "
                      "<b>타입 없는 파이썬에서 타입 검사를 흉내</b> 낸 것이다"),
                 (34, "<code>_run()</code> &mdash; 진짜 일. 아래 세 줄이 전부다"),
                 (35, "프롬프트가 요구하는 이름만 <b>골라낸다</b>. 남는 것을 "
                      "그냥 넘기지 않는다"),
                 (36, "<code>prompt.format(**selected)</code> &mdash; 변수를 꽂아 "
                      "<b>진짜 문자열</b>을 만든다"),
             ],
             접기=[(16, 19), (21, 24), (26, 29), (31, 33)]))

    c.날것(짚기("""<b>이 40줄이 왜 중요한가.</b> 2022년의 &lsquo;프레임워크&rsquo; 는
    <b>구조체 하나 + 함수 하나</b>였다. 그런데 그 구조체가 정한 것 &mdash;
    <i>프롬프트는 객체다 / 모형은 주입된다 / 입출력 이름을 스스로 선언한다</i> &mdash;
    가 지금까지 살아남았다. <b>프레임워크의 값어치는 코드량이 아니라 &lsquo;무엇을
    강제했는가&rsquo; 에 있다</b>(S2 의 다섯 판단 중 두 번째)."""))

    # ------------------------------------------------------------------
    c.절("R0.3 그리고 문제가 생겼다 — 사슬이 너무 많아졌다")

    c.글("""<code>LLMChain</code> 다음에 <code>SequentialChain</code>,
    <code>RetrievalQAChain</code>, <code>ConversationalRetrievalChain</code>,
    <code>MapReduceChain</code>&hellip; 이 계속 늘었다. 각각이 <b>자기만의
    <code>run()</code> 서명</b>과 자기만의 인자 이름을 가졌다.""")

    c.날것(dia.블록도(
        [("LLMChain", 0, 0, "run(**kwargs)", "회색"),
         ("SequentialChain", 1, 0, "run(input)", "회색"),
         ("RetrievalQA", 2, 0, "run(query)", "회색"),
         ("MapReduceChain", 3, 0, "run(docs)", "회색"),
         ("부르는 쪽", 0, 1, "네 가지를 다 외워야 한다|배치·스트리밍은 각자 따로", "빨강")],
        [("LLMChain", "부르는 쪽", "", True), ("SequentialChain", "부르는 쪽", "", True),
         ("RetrievalQA", "부르는 쪽", "", True), ("MapReduceChain", "부르는 쪽", "", True)],
        제목="문제: 사슬마다 부르는 법이 다르다", 폭=660))

    c.날것(정의("추상화 세금 (abstraction tax)",
              "추상화가 주는 이득보다 <b>그것을 배우고 우회하는 비용</b>이 커지는 것. "
              "&lsquo;그냥 API 를 직접 부르는 게 빠르겠다&rsquo; 는 말이 나오면 세금이 "
              "이득을 넘은 것이다."))

    c.날것(사고("""<b>이 저장소가 겪은 같은 병.</b> `bot_tools.py` 는 langchain 을
    들여서, <b>langchain 이 없는 환경에서는 통째로 임포트가 안 된다.</b> 그래서
    순수한 경로 가드 하나를 검사하려 해도 프레임워크 전체가 필요했다. 답은
    <code>mailattach.py</code> 로 <b>프레임워크에 안 딸린 부분을 떼어내는</b>
    것이었다 &mdash; 추상화 세금을 안 내는 자리를 만드는 것."""))

    # ------------------------------------------------------------------
    c.절("R0.4 LCEL — 하나의 계약으로 전부를 덮는다")

    c.날것(정의("러너블 (Runnable)",
              "LangChain 의 <b>단 하나의 계약</b>. &lsquo;<code>invoke</code> 로 하나를 "
              "처리하고, <code>batch</code> 로 여럿을, <code>stream</code> 으로 흘려 "
              "낸다&rsquo; 를 약속한다. 프롬프트도 모형도 파서도 검색기도 <b>전부 이것</b>이다."))
    c.날것(정의("LCEL (LangChain Expression Language)",
              "러너블을 <code>|</code> 로 이어 붙여 파이프라인을 <b>식으로</b> 적는 방법. "
              "<code>prompt | model | parser</code>."))
    c.날것(정의("파이프 연산자 (<code>|</code>)",
              "왼쪽의 출력을 오른쪽의 입력으로 넘기는 연산자. 파이썬에서 "
              "<code>a | b</code> 는 <code>a.__or__(b)</code> 를 부르므로, "
              "<b>클래스가 <code>__or__</code> 를 정의하면 <code>|</code> 의 뜻을 "
              "자기가 정할 수 있다</b>(연산자 오버로딩)."))

    c.날것(소스("lc_runnable_class",
             설명="""<b>지금 LangChain 의 알맹이.</b> 이 11줄이 이 프레임워크가
             파는 물건 전부다.""",
             풀이=[
                 (133, "<b><code>class Runnable(ABC, Generic[Input, Output])</code></b><br>"
                       "&middot; <code>ABC</code> = 추상 기반 클래스. <b>직접 못 만들고</b> "
                       "물려받아야 한다<br>"
                       "&middot; <code>Generic[Input, Output]</code> = &lsquo;Input 을 받아 "
                       "Output 을 내는&rsquo; 을 <b>타입으로</b> 적은 것. "
                       "<code>Runnable[str, dict]</code> 처럼 쓴다"),
                 (134, "한 줄 설명이 계약의 전부를 말한다 &mdash; "
                       "<b>invoke &middot; batch &middot; stream &middot; transform "
                       "&middot; compose</b>. 이 다섯이 되면 러너블이다"),
                 (139, "<code>invoke</code>/<code>ainvoke</code> &mdash; 하나를 하나로. "
                       "<b><code>a</code> 접두사가 비동기</b>(async)를 뜻한다"),
                 (140, "<code>batch</code> &mdash; 여럿을 여럿으로. "
                       "<b>기본 구현이 스레드 풀로 invoke 를 병렬 호출</b>하고, "
                       "더 잘할 수 있는 구현은 이것을 덮어쓴다"),
                 (141, "<code>stream</code> &mdash; 다 나오기 전에 조각부터. "
                       "A2 의 TTFT 가 여기에 달렸다"),
             ]))

    c.날것(소스("lc_or",
             설명="""<b><code>|</code> 가 실제로 하는 일.</b> 27줄 중 <b>마지막 한 줄</b>이
             진짜 코드이고, 나머지는 전부 타입 선언과 문서다. 이 비율 자체가
             &lsquo;프레임워크는 계약을 파는 것&rsquo; 이라는 말의 증거다.""",
             풀이=[
                 (648, "<code>def __or__(self, other)</code> &mdash; 파이썬이 "
                       "<code>a | b</code> 를 볼 때 부르는 메서드"),
                 (650, "오른쪽에 올 수 있는 것이 <b>러너블만이 아니다</b>. "
                       "이 뒤 네 줄이 &lsquo;함수도 되고, 사전도 되고&rsquo; 를 타입으로 적는다"),
                 (655, "<code>Mapping[str, ...]</code> &mdash; 사전을 주면 "
                       "<b>여러 갈래로 동시에</b> 흘린다. "
                       "<code>{\"a\": chain1, \"b\": chain2}</code>"),
                 (667, "<b>여기가 중요하다.</b> 문서가 <code>NotImplemented</code> 를 "
                       "<b>일부러 안 돌려준다</b>고 밝힌다 &mdash; 파이썬은 "
                       "<code>NotImplemented</code> 를 보면 오른쪽의 "
                       "<code>__ror__</code> 을 시도하는데, 그러면 <b>남의 "
                       "<code>|</code> 구현에 조용히 넘어간다</b>. "
                       "그 침묵을 막으려고 <b>터뜨리기로</b> 한 것"),
                 (674, "<b><code>return RunnableSequence(self, coerce_to_runnable(other))</code></b><br>"
                       "&middot; 실행이 아니라 <b>객체 생성</b>이다 &mdash; 지연 평가<br>"
                       "&middot; <code>coerce_to_runnable</code> 이 함수·사전을 "
                       "러너블로 <b>감싼다</b> &mdash; R0.1 의 그 &lsquo;감싼다&rsquo;"),
             ],
             접기=[(656, 666), (668, 673)]))

    c.날것(dia.파이프(
        [("PromptTemplate", "Runnable[dict, str]", "파랑"),
         ("ChatModel", "Runnable[str, Message]", "보라"),
         ("OutputParser", "Runnable[Message, dict]", "초록")],
        제목="prompt | model | parser — 셋 다 같은 계약이라 이어진다",
        아래글="타입이 맞아야 이어진다: dict → str → Message → dict",
        폭=640))

    c.날것(정리(
        "일관된 계약이 있으면 최적화를 한 번만 짜면 된다",
        """모든 구성요소가 같은 계약 (<i>invoke</i>, <i>batch</i>, <i>stream</i>) 을
        따르고, 각 구성요소의 <i>batch</i> 가 <b>원소별</b>이라 하자 &mdash; 즉
        batch(<i>f</i>, [<i>x</i><sub>1</sub>&hellip;<i>x</i><sub><i>n</i></sub>])
        = [invoke(<i>f</i>, <i>x</i><sub>1</sub>)&hellip;invoke(<i>f</i>, <i>x</i><sub><i>n</i></sub>)].
        그러면 사슬 <i>g</i> &compfn; <i>f</i> 에 대해
        <div class="math">batch(<i>g</i>&compfn;<i>f</i>, <b>X</b>)
        = batch(<i>g</i>, batch(<i>f</i>, <b>X</b>))</div>
        가 성립한다. 즉 <b>사슬의 배치를 사슬 클래스가 따로 구현할 필요가 없다</b>
        &mdash; 부분의 배치를 이어 붙이면 그것이 전체의 배치다.""",
        [("batch(<i>g</i>&compfn;<i>f</i>, <b>X</b>) 의 <i>i</i> 번째 원소는 정의에 의해 invoke(<i>g</i>&compfn;<i>f</i>, <i>x</i><sub><i>i</i></sub>) 다.",
          "원소별 가정을 합성 러너블에 적용한 것."),
         ("합성의 invoke 는 invoke(<i>g</i>, invoke(<i>f</i>, <i>x</i><sub><i>i</i></sub>)) 다.",
          "<code>RunnableSequence</code> 의 정의 &mdash; 앞의 출력을 뒤의 입력으로 넘긴다."),
         ("batch(<i>f</i>, <b>X</b>) 의 <i>i</i> 번째는 invoke(<i>f</i>, <i>x</i><sub><i>i</i></sub>) 다.",
          "<i>f</i> 에 원소별 가정을 적용."),
         ("그러므로 batch(<i>g</i>, batch(<i>f</i>, <b>X</b>)) 의 <i>i</i> 번째는 invoke(<i>g</i>, invoke(<i>f</i>, <i>x</i><sub><i>i</i></sub>)) 다.",
          "3 을 <i>g</i> 의 원소별 가정에 넣었다."),
         ("2 와 4 가 같으므로 두 쪽의 모든 원소가 같다.",
          "길이도 같으므로 수열로서 같다."),
         ("<b>따라서 batch 를 각 원소가 구현하면 합성은 공짜로 얻는다.</b> stream 도 같은 논증이 가는데, 다만 <i>g</i> 가 <b>조각을 조각으로</b> 보낼 수 있을 때만이다.",
          "stream 은 원소별이 아니라 <b>조각별</b>이어야 한다 &mdash; 아래 정리 37 이 그 조건을 다룬다."),
         ],
        가정="<b>원소별(pointwise)</b>이 핵심 가정이다. 실제 모형 배치는 원소별이 아니다 &mdash; B2 의 정리 5 가 말하듯 배치가 처리량을 바꾼다. 그래서 진짜 최적화는 각 구성요소가 <code>batch</code> 를 <b>덮어써서</b> 얻는다."))

    c.날것(정리(
        "스트리밍은 합성을 뚫고 지나가지 않는다",
        """사슬 <i>g</i> &compfn; <i>f</i> 에서 <i>f</i> 가 조각을 흘려도, <i>g</i> 가
        <b>전체 입력을 봐야 첫 출력을 낼 수 있는</b> 연산이면 사슬 전체의 첫 조각은
        <i>f</i> 가 <b>끝난 뒤</b>에야 나온다. 즉 스트리밍은 <b>사슬의 모든 마디가
        조각을 조각으로 보낼 때만</b> 끝까지 전달된다.""",
        [("<i>g</i> 가 첫 출력 조각을 내려면 그 조각이 의존하는 입력이 모두 있어야 한다.",
          "인과성 &mdash; 아직 안 받은 입력에 의존하는 출력을 낼 수는 없다."),
         ("<i>g</i> 가 &lsquo;전체를 봐야 하는&rsquo; 연산이면(예: 정렬, 합계, JSON 파싱) 첫 조각이 전체 입력에 의존한다.",
          "정의상 그렇다 &mdash; 마지막 원소가 결과를 바꿀 수 있으면 그 전에는 못 낸다."),
         ("그러면 <i>f</i> 가 마지막 조각을 낸 뒤에야 <i>g</i> 의 첫 조각이 나온다.",
          "1 과 2."),
         ("따라서 사슬의 TTFT 는 <i>f</i> 의 <b>전체 완료 시간</b> 이상이다.",
          "3 &mdash; 스트리밍의 이득이 그 마디에서 사라진다."),
         ("<b>따름</b>: 출력 파서를 사슬 끝에 두면 스트리밍이 죽는다. JSON 파싱은 닫는 괄호를 봐야 하기 때문이다.",
          "2 의 예. 이것이 LangChain 에 <code>JsonOutputParser</code> 의 <b>부분 파싱</b> 판이 따로 있는 이유다."),
         ],
        가정="조각 단위 전달이 가능한 매체(생성자/비동기 반복자)를 쓴다."))

    c.날것(짚기("""<b>정리 37 이 실무에서 하는 말.</b> &ldquo;스트리밍을 켰는데 왜 안
    흐르죠?&rdquo; 의 답은 거의 언제나 <b>사슬 어딘가에 전체를 기다리는 마디가 있다</b>
    이다. 가장 흔한 범인이 <b>구조화 출력 파서</b>다. B1 의 제약 디코딩이 이 문제를
    다른 층에서 푼다 &mdash; 파싱을 뒤로 미루는 대신 <b>애초에 문법을 지키게</b> 해서,
    조각마다 이미 유효하게 만든다."""))

    # ------------------------------------------------------------------
    c.절("R0.5 계층 — 무엇이 어디에 있나")

    c.날것(dia.계층([
        ("langchain-core", "의존성 거의 없음", "Runnable 계약 · 메시지 · 프롬프트 · 도구 정의", "진파랑"),
        ("langchain", "core 에 의존", "체인 · 에이전트 · 검색기 등 조립물", "파랑"),
        ("langchain-openai / -anthropic / …", "공급자별 패키지", "각 API 를 러너블로 감싼다", "보라"),
        ("langchain-community", "가장 큼", "수백 개 통합 — 품질 편차가 크다", "회색"),
    ], 제목="R0.5 — 패키지 계층 (아래로 갈수록 의존이 많다)",
        오른쪽라벨="", 폭=600))

    c.날것(짚기("""<b>이 쪼개기 자체가 상처의 기록이다.</b> 처음에는 전부 한 패키지였다.
    그러면 <b>통합 하나가 깨지면 전체 설치가 깨진다</b>. 그래서 알맹이(core)를 떼어내고,
    공급자를 따로 빼고, 나머지를 community 로 밀었다. <b>S2 의 다섯 판단 중 다섯째
    &mdash; 무엇을 안 넣을 것인가 &mdash; 를 나중에 하려면 이렇게 비싸다.</b>"""))

    # ------------------------------------------------------------------
    c.절("R0.6 어떻게 쓰나 — 그리고 언제 쓰지 않나")

    c.날것(언어(
        "같은 RAG 한 줄을 네 가지 방식으로 &mdash; <b>추상화 세금이 어디서 생기는지</b>",
        [("LangChain LCEL — 가장 짧다",
          """from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

prompt = ChatPromptTemplate.from_template(
    "다음 문맥만 써서 답하라.\\n\\n{context}\\n\\n질문: {question}")

chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | ChatOpenAI(model="gpt-4o-mini")
    | StrOutputParser()
)
answer = chain.invoke("이 저장소의 커밋 규칙은?")     # 동기
async for tok in chain.astream("..."): ...          # 스트리밍 공짜
results = chain.batch(["q1", "q2", "q3"])           # 배치 공짜""",
          "<b>사전이 첫 마디인 것</b>에 주목하라 &mdash; <code>{\"context\": ..., "
          "\"question\": ...}</code> 가 두 갈래를 <b>동시에</b> 흘린다(R0.4 의 655줄). "
          "<code>astream</code>·<code>batch</code> 를 따로 안 짜도 되는 것이 "
          "정리 36 이 말한 이득이다"),
         ("직접 짜기 — 무엇을 잃고 무엇을 얻나",
          """import asyncio, openai

async def rag(question: str) -> str:
    docs = await retrieve(question)                  # 내 함수
    ctx = "\\n\\n".join(d.text for d in docs)
    r = await openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user",
                   "content": f"다음 문맥만 써서 답하라.\\n\\n{ctx}\\n\\n질문: {question}"}])
    return r.choices[0].message.content

# 배치? 직접 짠다. 스트리밍? 직접 짠다. 재시도? 직접 짠다.""",
          "<b>읽기는 이쪽이 쉽다.</b> 무슨 일이 나는지 열 줄에 다 보인다. "
          "대신 배치·스트리밍·재시도·추적을 <b>전부 직접</b> 짜야 하고, "
          "모형을 바꾸면 이 함수를 고쳐야 한다. "
          "<b>한 번 쓰고 마는 코드면 이쪽이 옳다</b>"),
         ("LangGraph — 사슬이 아니라 그래프가 필요할 때",
          """from langgraph.graph import StateGraph, END

g = StateGraph(State)
g.add_node("retrieve", retrieve_node)
g.add_node("grade",    grade_node)      # 문서가 쓸 만한가?
g.add_node("rewrite",  rewrite_node)    # 아니면 질문을 고쳐 다시
g.add_node("answer",   answer_node)
g.add_conditional_edges("grade",
    lambda s: "answer" if s["ok"] else "rewrite")
g.add_edge("rewrite", "retrieve")       # **되돌아가는 간선** -- 사슬로는 못 한다
app = g.compile(checkpointer=saver)""",
          "<b><code>|</code> 로는 고리를 못 만든다.</b> 파이프는 한 방향이고, "
          "&lsquo;아니면 다시&rsquo; 는 방향이 되돌아간다. "
          "<b>LangGraph 가 생긴 이유가 정확히 이 한 줄</b>이고, 다음 장(R1)의 주제다"),
         ("셸 — 그리고 이게 정답인 경우가 생각보다 많다",
          """# 코드베이스 질문이면 임베딩보다 ripgrep 이 낫다 (D2 의 결론)
ctx=$(rg -n -C 3 --max-count 3 "$PAT" -g '!*.lock' | head -c 4000)

jq -n --arg c "$ctx" --arg q "$QUESTION" \\
   '{model:"claude-sonnet-4", max_tokens:1024,
     messages:[{role:"user",
       content:("다음 문맥만 써서 답하라.\\n\\n"+$c+"\\n\\n질문: "+$q)}]}' \\
| curl -sS --fail-with-body -H "x-api-key: $KEY" \\
       -H 'content-type: application/json' -d @- \\
       https://api.anthropic.com/v1/messages \\
| jq -r '.content[0].text'""",
          "프레임워크도 SDK 도 없다. <b>파이프라인이 정확히 이 모양일 때</b>는 "
          "이것이 가장 적은 움직이는 부품을 가진다. "
          "<code>--fail-with-body</code> 가 없으면 HTTP 400 의 본문이 사라져 "
          "<b>왜 실패했는지 모르게</b> 된다")],
        짚기="""<b>네 칸을 가르는 기준은 &lsquo;무엇이 바뀔 것인가&rsquo; 다.</b>
        모형이 바뀔 것 같으면 첫째, 흐름이 바뀔 것 같으면 셋째, 아무것도 안 바뀔 것
        같으면 둘째나 넷째. <b>프레임워크는 변화에 대한 보험이고, 보험료가 곧
        추상화 세금이다.</b>"""))

    c.날것(개념(
        "LangChain 을 쓸 자리와 안 쓸 자리",
        """<b>이론.</b> 프레임워크가 주는 것은 <b>일관된 계약</b>이고, 그 계약이
        값어치를 하려면 <b>계약을 여러 번 갈아 끼워야</b> 한다. 갈아 끼울 일이
        없으면 계약은 그냥 배워야 할 것이 하나 더 있는 것이다.""",
        어디에="""공급자를 바꿔 가며 비교할 때 &middot; 같은 파이프라인을 여러 모형으로
        돌릴 때 &middot; 통합(벡터 DB · 로더 · 파서)을 많이 붙일 때 &middot;
        추적(LangSmith)이 필요할 때""",
        언제="""<b>두 번째 공급자를 붙일 때부터.</b> 하나뿐이면 직접 부르는 것이
        거의 언제나 낫다""",
        어떻게="""(1) <code>langchain-core</code> 만 의존한다 &mdash;
        <code>community</code> 는 필요한 것만 골라 붙인다 &rarr;
        (2) 사슬이 <b>고리</b>를 필요로 하는 순간 LangGraph 로 옮긴다(R1) &rarr;
        (3) 스트리밍이 필요하면 <b>사슬의 모든 마디</b>가 조각을 흘리는지 본다
        (정리 37) &rarr; (4) 프레임워크가 못 하는 일은 <b>프레임워크 밖에서</b>
        한다 &mdash; 억지로 안에 넣지 않는다""",
        산업코드="""# 이 저장소가 실제로 택한 것: **얇게 쓴다**
# bot_tools.py 는 langchain 의 @tool 데코레이터와 ReAct 에이전트만 쓴다.
from langchain_core.tools import tool

@tool
def send_email(to: str, subject: str, body: str, attach: str = "") -> str:
    \"\"\"도구 설명이 곧 모형이 읽는 명세다 -- 이 docstring 이 프롬프트에 들어간다.\"\"\"
    ...

# 그리고 **순수 로직은 프레임워크 밖에** 둔다.
# mailattach.py 는 langchain 을 안 들인다 -- 그래야 검사가 환경에 안 걸린다.""",
        주의="""<b>도구의 docstring 이 프롬프트가 된다</b>는 것을 모르고 짜면,
        모형이 도구를 언제 쓸지 판단할 근거가 없어진다. S1 의 발동 설명과 같은
        자리이고, <b>여기서 <i>p</i> 를 낮추는 것이 곧 토큰을 아끼는 것</b>이다
        (S1 의 정리 32)."""))

    c.날것(유도("이 장을 한 문단으로", [
        ("2022년 10월, 모두가 같은 넷을 다시 짓고 있었다",
         "프롬프트 조립 · 모형 호출 · 답 파싱 · 이어 붙이기"),
        ("LangChain 은 그것들에 <b>이름</b>을 붙였다",
         "Prompt · LLM · OutputParser · Chain &mdash; 이름이 생기자 남의 것을 쓸 수 있게 됐다"),
        ("첫 판의 알맹이는 40줄이었고, 그 안의 결정이 지금까지 남았다",
         "프롬프트는 객체 · 모형은 주입 · 입출력 이름을 스스로 선언"),
        ("사슬이 늘자 <b>부르는 법이 사슬마다 달라졌다</b>",
         "추상화 세금이 이득을 넘기 시작한 자리"),
        ("그래서 계약을 하나로 합쳤다 &mdash; Runnable",
         "invoke · batch · stream 셋만 지키면 무엇이든 이어 붙는다"),
        ("<code>|</code> 는 실행이 아니라 <b>조립</b>이다",
         "지연 평가 &mdash; 다 조립한 뒤에 한꺼번에 최적화할 수 있다"),
        ("일관된 계약 덕에 배치가 공짜로 합성된다",
         "정리 36 &mdash; 원소별이면 부분의 배치가 전체의 배치"),
        ("그런데 스트리밍은 공짜가 아니다",
         "정리 37 &mdash; 전체를 기다리는 마디가 하나라도 있으면 거기서 끊긴다"),
        ("그리고 <code>|</code> 로는 <b>고리</b>를 못 만든다",
         "그것이 다음 장 LangGraph 의 존재 이유다"),
    ]))

    c.날것(논문출처([
        ["langchain-ai/langchain 소스", f"github @ {lc['커밋']}", "<b>코드</b>",
         "R0 전체 &mdash; Runnable 계약 · <code>__or__</code> · 첫 커밋의 LLMChain"],
        ["같은 저장소의 첫 커밋", "github @ 18aeb7201 (2022-10-24)", "<b>코드</b>",
         "R0.2 의 계보 &mdash; 날짜와 작성자는 git 이력에서 읽었다"],
    ]))

    return c.완성()
