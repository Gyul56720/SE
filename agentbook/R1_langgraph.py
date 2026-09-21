# -*- coding: utf-8 -*-
"""R1 -- LangGraph. 사슬로 못 하는 것: 고리, 병렬 병합, 그리고 멈췄다 잇기."""
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


def ch_langgraph():
    lg = zoo("langgraph")
    파이썬 = lg["말"].get("Python", {})

    c = 장(
        "R1", "LangGraph — 고리가 필요해지는 순간",
        "<code>|</code> 는 한 방향이다. &lsquo;아니면 다시&rsquo; 를 적을 수 없다. "
        "LangGraph 는 <b>파이프를 그래프로 바꾸고</b>, 그 대가로 "
        "<b>상태가 무엇인지 직접 정의하게</b> 만든다.",
        쓰는것=["사슬", "LCEL", "파이프연산자", "러너블", "지연평가", "일관된인터페이스",
             "상태기계", "제어루프", "종료조건", "걸음예산", "체크포인트", "재개",
             "실행id", "팬아웃", "합치기", "사람개입", "선언형", "의존그래프", "고정점"],
        내놓는것=["상태그래프", "슈퍼스텝", "BSP", "채널", "리듀서", "조건부간선",
              "체크포인터", "스레드", "중단과재개", "시간여행", "지속실행"],
        특허="""<b>무엇을 체크포인트에 담는가</b>와 <b>중단 지점을 어디에 두는가</b>가
        발명 자리다. BSP 자체는 1990년 Valiant 이고 Pregel 은 2010년 구글이다 &mdash;
        새로운 것은 <b>그 모형을 사람이 끼어들 수 있는 실행에 얹은 것</b>이다.""")

    c.날것(직무(["NAV.상태", "NAV.프레임워크", "AIE.런타임", "AIE.코어"]))

    # ------------------------------------------------------------------
    c.절("R1.1 말부터")

    c.날것(말풀이([
        ("BSP", "bulk synchronous parallel",
         "계산을 <b>단계(슈퍼스텝)</b>로 끊고, 한 단계 안에서는 모두가 "
         "<b>같은 옛 상태</b>를 읽고 각자 계산한 뒤, 단계 끝에서 <b>한꺼번에</b> "
         "상태를 갱신하는 모형.",
         "덩어리(bulk)로 동기화(synchronous)한다. 매 순간이 아니라 "
         "<b>단계 경계에서만</b> 맞춘다 &mdash; 그래서 단계 안은 자유롭게 병렬이다."),
        ("슈퍼스텝", "super-step",
         "BSP 의 한 단계. &lsquo;읽기 &rarr; 계산 &rarr; 쓰기 &rarr; 장벽&rsquo; 한 바퀴.",
         "보통의 한 걸음(step)보다 큰 단위라 <b>초(super)</b>가 붙었다."),
        ("채널", "channel",
         "상태의 <b>칸 하나</b>. 노드는 채널에 쓰고 채널에서 읽는다. "
         "채널마다 <b>여럿이 동시에 쓸 때 어떻게 합칠지</b>를 자기가 안다.",
         "물이 흐르는 통로. 여러 곳에서 들어온 물이 <b>한 통로에서 합쳐진다</b>."),
        ("리듀서", "reducer",
         "한 채널에 여러 값이 들어왔을 때 <b>하나로 접는</b> 함수. "
         "<code>operator.add</code> 를 주면 이어 붙이고, 안 주면 &lsquo;덮어쓰기&rsquo; 다.",
         "줄인다(reduce). 여러 개를 하나로 줄인다 &mdash; 함수형 프로그래밍의 "
         "<code>fold</code> 와 같은 것."),
        ("결합법칙", "associativity",
         "(<i>a</i>&oplus;<i>b</i>)&oplus;<i>c</i> = <i>a</i>&oplus;(<i>b</i>&oplus;<i>c</i>). "
         "<b>괄호를 어디 치든 같다</b>.",
         "묶는(associate) 방법이 결과를 안 바꾼다는 뜻. "
         "이것이 있어야 <b>병렬로 나눠 접어도</b> 된다."),
        ("가환법칙", "commutativity",
         "<i>a</i>&oplus;<i>b</i> = <i>b</i>&oplus;<i>a</i>. <b>순서를 바꿔도 같다</b>.",
         "자리를 바꾼다(commute). 병렬 실행은 순서를 보장 안 하므로, "
         "<b>이것이 없으면 결과가 실행마다 달라진다</b>."),
        ("체크포인터", "checkpointer",
         "슈퍼스텝마다 <b>상태 전체를 저장</b>하는 것. 메모리·SQLite·Postgres 판이 있다.",
         "A9 에서 나온 그 체크포인트다. 여기서는 <b>프레임워크가 자동으로</b> 한다."),
        ("스레드", "thread",
         "체크포인트들이 <b>이어진 한 줄</b>. 대화 하나, 작업 하나. "
         "<code>thread_id</code> 로 구별한다.",
         "실(thread)처럼 이어진다. OS 의 스레드와 <b>다른 뜻</b>이니 조심할 것 "
         "&mdash; 여기서는 &lsquo;하나의 대화 이력&rsquo; 이다."),
        ("지속 실행", "durable execution",
         "프로세스가 죽어도 <b>죽은 자리부터</b> 다시 이어지는 실행. "
         "상태가 매 단계 밖에 저장돼 있어야 가능하다.",
         "지속(durable)된다 &mdash; 프로세스보다 오래 산다는 뜻."),
    ]))

    # ------------------------------------------------------------------
    c.절("R1.2 사슬이 못 하는 세 가지")

    c.날것(dia.견줌(
        "사슬 (LCEL) 로 못 하는 것",
        ["<b>고리</b> — '문서가 나쁘면 질문을 고쳐 다시 검색'",
         "<b>병합</b> — 세 갈래를 병렬로 돌리고 결과를 한 칸에 모으기",
         "<b>중단</b> — 사람이 승인할 때까지 멈췄다가 잇기",
         "<b>부분 재개</b> — 다섯째 마디에서 죽었을 때 거기서부터",
         "이유는 하나다: <b>파이프에는 상태가 없다</b>"],
        "그래서 LangGraph 가 바꾼 것",
        ["간선이 <b>되돌아갈 수 있다</b> (조건부 간선)",
         "채널마다 <b>리듀서</b>가 병합 규칙을 안다",
         "<code>interrupt</code> 로 슈퍼스텝 사이에서 멈춘다",
         "슈퍼스텝마다 <b>체크포인트</b>가 남는다",
         "대신 <b>상태를 직접 정의</b>해야 한다 — 이것이 대가다"],
        제목="R1.2 — 무엇을 얻고 무엇을 내주나", 폭=660,
        왼색="빨강", 오른색="초록"))

    c.날것(dia.그래프(
        [("START", 0.0, 0.0, "회색", ""),
         ("retrieve", 0.28, 0.0, "파랑", "문서를 찾는다"),
         ("grade", 0.56, 0.0, "보라", "쓸 만한가?"),
         ("answer", 0.86, 0.0, "초록", "답한다"),
         ("rewrite", 0.56, 0.72, "노랑", "질문을 고친다"),
         ("END", 0.86, 0.72, "회색", "")],
        [("START", "retrieve", ""), ("retrieve", "grade", ""),
         ("grade", "answer", "ok"), ("grade", "rewrite", "bad"),
         ("rewrite", "retrieve", "다시", True), ("answer", "END", "")],
        제목="Corrective RAG — 점선이 사슬로는 못 그리는 간선이다",
        폭=640, 높이=230))

    c.날것(정의("상태 그래프 (StateGraph)",
              "마디가 <b>상태를 읽고 상태의 일부를 돌려주는 함수</b>이고, 간선이 "
              "<b>다음에 어느 마디로 가는지</b>를 정하는 그래프. 마디는 상태 전체를 "
              "받고 <b>바뀐 칸만</b> 돌려준다."))
    c.날것(정의("조건부 간선 (conditional edge)",
              "다음 마디를 <b>함수가 정하는</b> 간선. "
              "<code>add_conditional_edges(\"grade\", lambda s: ...)</code>. "
              "여기서 <b>같은 마디로 돌아가는 값</b>을 내면 그것이 고리다."))

    # ------------------------------------------------------------------
    c.절("R1.3 슈퍼스텝 — 한 걸음이 실제로 무엇인가")

    c.날것(dia.타임라인(
        [("retrieve", [(0, 1, "실행", "파랑")]),
         ("grade", [(1, 1, "실행", "보라")]),
         ("rewrite", [(2, 1, "실행", "노랑")]),
         ("retrieve", [(3, 1, "실행", "파랑")]),
         ("체크포인트", [(0, 1, "cp0", "회색"), (1, 1, "cp1", "회색"),
                    (2, 1, "cp2", "회색"), (3, 1, "cp3", "회색")])],
        4, 칸이름=["슈퍼스텝 0", "슈퍼스텝 1", "슈퍼스텝 2", "슈퍼스텝 3"],
        제목="한 슈퍼스텝 = 읽기 → 실행 → 쓰기 → 저장. 그 경계마다 멈출 수 있다",
        폭=640))

    c.날것(소스("lg_tick",
             설명="""<b>LangGraph 의 심장.</b> <code>PregelLoop.tick()</code> 한 번이
             슈퍼스텝 한 번이다. 이 함수가 <code>True</code> 를 돌려주는 동안 루프가
             돈다 &mdash; A4 에서 본 제어 루프가 여기서는 <b>이 한 함수</b>다.""",
             풀이=[
                 (599, "<code>def tick(self) -> bool</code> &mdash; <b>돌려주는 값이 "
                       "&lsquo;더 돌아야 하나&rsquo;</b> 다. 루프의 종료 조건이 "
                       "<b>반환값 하나</b>에 들어 있다"),
                 (607, "<code>if self.step > self.stop</code> &mdash; <b>걸음 예산</b>"
                       "(A4.2 의 네 종료 조건 중 셋째). 없으면 고리가 영원히 돈다"),
                 (609, "<code>self.status = \"out_of_steps\"</code> &mdash; "
                       "<b>왜 멈췄는지를 남긴다.</b> 그냥 <code>False</code> 만 "
                       "돌려주면 성공과 예산 소진이 구별이 안 된다"),
                 (613, "<code>prepare_next_tasks(...)</code> &mdash; <b>이번 단계에 "
                       "무엇을 돌릴지</b>를 정한다. 인자를 보면 이 프레임워크가 무엇을 "
                       "들고 있는지가 다 보인다: 체크포인트 · 밀린 쓰기 · 마디 · 채널 · "
                       "저장소 · 재시도 정책 · 캐시 정책"),
                 (628, "<code>updated_channels</code> &mdash; <b>지난 단계에 바뀐 채널</b>만 "
                       "본다. 바뀐 칸을 구독하는 마디만 깨우는 것이고, 이것이 "
                       "&lsquo;그래프를 매번 통째로 훑지 않는&rsquo; 방법이다"),
                 (654, "<code>if not self.tasks: self.status = \"done\"</code> &mdash; "
                       "<b>깨울 마디가 없으면 끝이다.</b> 이것이 Pregel 의 종료 조건이고, "
                       "&lsquo;아무도 할 일이 없다&rsquo; 를 <b>고정점</b>이라 부른다"),
                 (659, "<code>_reapply_writes_to_succeeded_nodes</code> &mdash; "
                       "<b>재개의 알맹이.</b> 지난번에 성공했던 마디의 쓰기를 다시 "
                       "적용한다 &mdash; 그 마디를 <b>다시 실행하지 않고</b>"),
             ],
             접기=[(600, 606), (614, 627), (629, 653)]))

    c.날것(정리(
        "슈퍼스텝 안에서는 실행 순서가 결과를 바꾸지 않는다",
        """한 슈퍼스텝에서 (i) 모든 마디가 <b>같은</b> 채널 스냅숏을 읽고,
        (ii) 마디의 쓰기는 단계가 끝날 때까지 채널에 반영되지 않으며,
        (iii) 마디에 채널 밖 부작용이 없다고 하자. 그러면 그 단계에서 마디들을
        <b>어떤 순서로 실행하든, 또는 동시에 실행하든</b> 단계 끝의 채널 상태가
        같다.""",
        [("마디 <i>v</i> 의 출력은 그 입력 스냅숏 <i>S</i> 의 함수 <i>f</i><sub><i>v</i></sub>(<i>S</i>) 다.",
          "(iii) 에 의해 다른 것에 의존하지 않는다 &mdash; 부작용이 없다."),
         ("모든 마디가 같은 <i>S</i> 를 읽는다.",
          "(i) 이 그것을 말한다. 단계 안에서 <i>S</i> 는 <b>읽기 전용</b>이다."),
         ("따라서 각 마디의 쓰기 집합 <i>W</i><sub><i>v</i></sub> = <i>f</i><sub><i>v</i></sub>(<i>S</i>) 는 <b>언제 실행되든 같다</b>.",
          "1 과 2 &mdash; 같은 함수에 같은 입력."),
         ("단계 끝에서 채널 <i>k</i> 의 새 값은 리듀서 &oplus;<sub><i>k</i></sub> 로 그 채널에 쓴 값들을 접은 것이다.",
          "BSP 의 쓰기 단계 정의."),
         ("쓴 값들의 <b>집합</b>은 3 에 의해 순서와 무관하다.",
          "어느 마디가 무엇을 쓰는지가 정해져 있으므로."),
         ("그러므로 리듀서가 <b>결합적이고 가환적</b>이면 접은 결과도 순서와 무관하다.",
          "결합·가환이면 유한 집합의 fold 가 순서에 안 딸린다."),
         ("<b>리듀서가 그렇지 않으면 이 정리가 깨진다</b> &mdash; 그 경우 프레임워크는 동시 쓰기를 <b>거절해야</b> 한다.",
          "6 의 가정이 빠지면 결과가 비결정적이 된다. 다음 절의 <code>LastValue</code> 가 그래서 예외를 던진다."),
         ],
        가정="(iii) 이 실무에서 가장 자주 깨진다 &mdash; 마디가 파일을 쓰거나 외부 API 를 부르면 부작용이 있다. 그때는 이 정리가 <b>채널 상태에만</b> 적용되고, 바깥 세계는 A9 의 멱등성으로 따로 지켜야 한다."))

    # ------------------------------------------------------------------
    c.절("R1.4 두 마디가 같은 칸에 쓰면 — 리듀서")

    c.날것(dia.블록도(
        [("node A", 0, 0, "→ {\"docs\": [d1]}", "파랑"),
         ("node B", 1, 0, "→ {\"docs\": [d2]}", "보라"),
         ("채널 docs", 0, 1, "리듀서가 접는다|operator.add → [d1, d2]", "초록"),
         ("채널 answer", 1, 1, "리듀서 없음(LastValue)|둘이 쓰면 **예외**", "빨강")],
        [("node A", "채널 docs", "write"), ("node B", "채널 docs", "write"),
         ("node A", "채널 answer", "write"), ("node B", "채널 answer", "write")],
        제목="같은 슈퍼스텝에 두 마디가 한 칸에 쓸 때", 폭=640))

    c.날것(소스("lg_lastvalue",
             설명="""<b>리듀서가 없는 채널.</b> 12줄인데, 그중 <b>7줄이 거절</b>이다.
             이 비율이 설계 결정 전부를 말한다.""",
             풀이=[
                 (58, "값이 없으면 아무 일도 안 한다"),
                 (59, "<b><code>if len(values) != 1</code></b> &mdash; 한 단계에 "
                      "<b>둘 이상이 들어오면 터뜨린다</b>"),
                 (61, "오류 메시지가 <b>고치는 법까지</b> 말한다 &mdash; "
                      "&lsquo;Use an Annotated key to handle multiple values&rsquo;. "
                      "즉 <b>리듀서를 달아라</b>"),
                 (62, "<code>error_code=ErrorCode.INVALID_CONCURRENT_GRAPH_UPDATE</code>"
                      " &mdash; 오류에 <b>코드</b>가 붙어 있다. "
                      "S2 의 &lsquo;오류는 타입이어야 한다&rsquo; 가 이것"),
                 (66, "여기까지 왔으면 값이 정확히 하나다. 그제야 덮어쓴다"),
             ]))

    c.날것(짚기("""<b>이 거절이 왜 옳은 설계인가.</b> 정리 38 의 걸음 7 이 그 답이다.
    <code>LastValue</code> 는 &lsquo;마지막 것이 이긴다&rsquo; 인데, <b>병렬 실행에는
    &lsquo;마지막&rsquo; 이 없다.</b> 그러면 결과가 실행마다 달라진다 &mdash; A3 의 재현성이
    통째로 깨진다. 조용히 하나를 고르는 대신 <b>터뜨려서 설계자가 리듀서를 정하게</b>
    만드는 것이 이 프레임워크의 선택이다. <i>검사하지 않은 초록불이 검사한 빨간불보다
    나쁘다</i> 와 같은 규율이다."""))

    c.날것(소스("lg_binop",
             설명="""<b>리듀서가 있는 채널.</b> <code>Annotated[list, operator.add]</code>
             처럼 달아 두면 이쪽이 쓰인다.""",
             풀이=[
                 (126, "첫 값이면 접지 않고 그대로 앉힌다 &mdash; "
                       "<b>항등원이 필요 없게</b> 하는 방법. "
                       "<code>operator.add</code> 에 빈 리스트를 주면 되지만, "
                       "임의의 연산자에는 항등원이 없을 수 있다"),
                 (130, "<code>_get_overwrite(value)</code> &mdash; 특별한 표식을 단 값은 "
                       "<b>접지 않고 통째로 갈아 끼운다</b>. 누적 채널을 "
                       "&lsquo;초기화&rsquo; 하는 유일한 길"),
                 (132, "<b><code>if seen_overwrite: raise</code></b> &mdash; "
                       "한 단계에 덮어쓰기가 두 번이면 터뜨린다. "
                       "<code>LastValue</code> 와 같은 논리 &mdash; "
                       "<b>순서가 없는 곳에서 순서에 기대면 거절</b>"),
                 (141, "<code>self.value = self.operator(self.value, value)</code>"
                       " &mdash; <b>이 한 줄이 리듀서다.</b> 왼쪽으로 접는다(fold-left)"),
             ]))

    c.날것(정리(
        "리듀서가 결합적·가환적이어야 병렬 병합이 결정적이다",
        """채널 <i>k</i> 에 한 슈퍼스텝에서 값
        <i>w</i><sub>1</sub>&hellip;<i>w</i><sub><i>m</i></sub> 이 쓰였다고 하자.
        접는 순서가 실행 순서에 딸린다면, 결과가 순서와 무관할
        <b>필요충분조건</b>은 &oplus;<sub><i>k</i></sub> 가 그 값들 위에서
        결합적이고 가환적인 것이다.""",
        [("<b>충분</b>: 결합·가환이면 어떤 순열로 접어도 같은 값이 나온다.",
          "유한 개의 원소에 대한 표준 결과 &mdash; 두 성질이 있으면 fold 가 순서에 무관하다."),
         ("<b>필요</b>: 가환이 아니면 <i>a</i>&oplus;<i>b</i> &ne; <i>b</i>&oplus;<i>a</i> 인 두 값이 있다.",
          "가환이 아니라는 것의 정의."),
         ("두 마디가 각각 <i>a</i>, <i>b</i> 를 쓰게 하면, 실행 순서에 따라 결과가 달라진다.",
          "2 를 그대로 구성한 반례."),
         ("결합이 아니면 세 값으로 같은 구성을 만들 수 있다.",
          "(<i>a</i>&oplus;<i>b</i>)&oplus;<i>c</i> &ne; <i>a</i>&oplus;(<i>b</i>&oplus;<i>c</i>) 인 삼중항을 잡는다."),
         ("<b>따라서 둘 다 필요하다.</b>",
          "3 과 4 가 각각 하나씩을 반증한다."),
         ("<code>operator.add</code> 는 리스트에서 결합적이지만 <b>가환이 아니다</b>([1]+[2] &ne; [2]+[1]).",
          "리스트 이어 붙이기는 순서를 보존한다."),
         ("<b>그러므로 LangGraph 의 기본 리듀서를 병렬 팬아웃에 쓰면 원소의 순서가 실행마다 달라질 수 있다.</b> 값의 집합은 같지만 순서는 아니다.",
          "6 과 3 &mdash; 실무에서 <i>내용은 맞는데 순서가 뒤집히는</i> 버그로 나타난다."),
         ("순서까지 결정적으로 만들려면 마디마다 <b>고정된 키</b>로 쓰고 읽을 때 정렬하거나, 리듀서를 <b>정렬 삽입</b>으로 정의한다.",
          "가환성을 회복시키는 두 방법 &mdash; 키를 주면 순서가 값의 함수가 된다."),
         ],
        가정="값들이 한 단계 안에서 모인다. 단계를 넘어가는 누적은 이 정리가 아니라 정리 38 의 (ii) 가 지킨다."))

    c.날것(예제(
        "세 갈래를 병렬로 돌렸는데 결과 순서가 실행마다 다르다",
        """세 검색기(벡터 · BM25 · 그래프)를 팬아웃하고 결과를
        <code>Annotated[list[Doc], operator.add]</code> 채널에 모은다.
        같은 질의로 두 번 돌렸더니 <b>문서 집합은 같은데 순서가 다르다</b>.""",
        """정리 39 의 걸음 6&ndash;7 이다. 리스트 이어 붙이기는 결합적이지만
        가환이 아니므로, 어느 갈래가 먼저 끝나느냐에 따라 앞자리가 달라진다.
        그리고 <b>상위 <i>k</i> 를 자르는 하류 단계가 있으면 그 순서가 답을 바꾼다</b>.""",
        """리듀서를 고친다. 각 문서에 <b>출처와 점수</b>를 달고,
        리듀서를 &lsquo;이어 붙인 뒤 (점수, 출처이름) 으로 정렬&rsquo; 로 정의한다.
        그러면 순서가 <b>값의 함수</b>가 되어 실행 순서와 무관해진다.
        (D2 의 RRF 가 바로 이 꼴이다 &mdash; 순위만 쓰므로 실행 순서에 안 딸린다.)""",
        """<b>&ldquo;집합이 같으니 괜찮다&rdquo; 가 함정이다.</b> 하류에 자르기·
        첫 문서 우대·프롬프트 앞자리 배치가 있으면 순서가 곧 답이다. 그리고 이 버그는
        <b>재현이 안 되므로</b> 가장 늦게 발견된다 &mdash; A3 의 재현성이 왜 예산
        항목인지 보여주는 자리.""",
        덧="""거꾸로, <b>순서가 정말 상관없는</b> 채널이라면(예: 집계용 카운터)
        가환인 리듀서(<code>operator.add</code> on int, <code>max</code>, 합집합)를
        쓰면 되고, 그때는 정리 39 가 그냥 만족된다."""))

    # ------------------------------------------------------------------
    c.절("R1.5 체크포인트 — 멈췄다 잇는 것이 공짜가 되는 자리")

    c.날것(dia.계층([
        ("스레드 (thread_id)", "대화 하나", "체크포인트들이 이어진 한 줄", "진파랑"),
        ("체크포인트 (checkpoint_id)", "슈퍼스텝 하나", "그 시점의 채널 전부 + 다음 할 일", "파랑"),
        ("채널 값", "상태의 칸들", "리듀서가 접어 넣은 결과", "보라"),
        ("밀린 쓰기 (pending writes)", "실패한 마디의 몫", "재개할 때 다시 적용된다", "노랑"),
    ], 제목="R1.5 — 체크포인터가 들고 있는 것", 오른쪽라벨="", 폭=600))

    c.날것(정리(
        "체크포인트가 있으면 재개가 처음부터 다시 돌린 것과 같다",
        """슈퍼스텝 <i>t</i> 의 체크포인트가 (a) 그 시점의 모든 채널 값과
        (b) 그 단계에서 <b>이미 성공한 마디들의 쓰기</b>를 담고 있고,
        마디가 채널 밖 부작용이 없다면, <i>t</i> 에서 재개한 실행의 최종 상태는
        <b>처음부터 끊김 없이 돌린 실행</b>의 최종 상태와 같다.""",
        [("<i>t</i> 에서의 채널 상태가 (a) 에 의해 복원된다.",
          "체크포인트가 담고 있는 것이 바로 그것이다."),
         ("<i>t</i> 단계에서 성공했던 마디들은 다시 실행되지 않고 그 쓰기가 재적용된다.",
          "(b) 와 <code>tick()</code> 의 <code>_reapply_writes_to_succeeded_nodes</code>."),
         ("정리 38 의 3 에 의해 그 마디들이 다시 실행되었어도 같은 쓰기를 냈을 것이다.",
          "같은 스냅숏에서 같은 함수 &mdash; 재실행과 재적용이 구별되지 않는다."),
         ("실패했던 마디는 같은 스냅숏에서 다시 실행되므로, 끊김 없는 실행에서의 그 마디 실행과 같다.",
          "역시 정리 38 의 3."),
         ("따라서 단계 <i>t</i> 의 끝 상태가 두 실행에서 같다.",
          "3 과 4 가 모든 마디를 덮는다."),
         ("<i>t</i> 이후는 귀납으로 같다.",
          "같은 상태에서 같은 규칙으로 진행하므로."),
         ("<b>다만 부작용은 이 정리 밖이다</b> &mdash; 재적용되지 않고 재실행되는 마디가 메일을 두 번 보낼 수 있다.",
          "가정에서 부작용 없음을 요구했다. 실무에서는 A9 의 멱등 키가 이 구멍을 막는다."),
         ],
        가정="모형 호출이 결정적이어야 (3) 이 엄밀히 성립한다. 온도 &gt; 0 이면 &lsquo;같은 쓰기&rsquo; 가 아니라 &lsquo;같은 분포&rsquo; 다 &mdash; 그래서 체크포인트가 <b>모형의 출력까지</b> 담는 것이 중요하다."))

    c.날것(짚기("""<b>마지막 가정이 이 장에서 가장 실무적인 문장이다.</b> 체크포인트가
    &lsquo;어디까지 갔는지&rsquo; 만 담고 <b>모형이 무엇을 냈는지</b>를 안 담으면, 재개할 때
    모형을 다시 불러야 하고 그러면 다른 답이 나온다. LangGraph 가 마디의 <b>출력</b>을
    채널에 넣어 저장하는 것이 그래서 중요하다 &mdash; 재개가 <b>재실행이 아니라
    재생</b>이 된다(7부 C1 의 주제)."""))

    c.날것(dia.시퀀스(
        ["사람", "앱", "LangGraph", "체크포인터"],
        [("사람", "앱", "질문", False, "진파랑"),
         ("앱", "LangGraph", "invoke(thread_id=42)", False, "진파랑"),
         ("LangGraph", "체크포인터", "put(cp0)", False, "회색"),
         ("LangGraph", "LangGraph", "슈퍼스텝 실행", False, "보라"),
         ("LangGraph", "체크포인터", "put(cp1)", False, "회색"),
         ("LangGraph", "앱", "interrupt — 승인 필요", False, "빨강"),
         ("앱", "사람", "이 도구를 실행할까요?", False, "노랑"),
         ("사람", "앱", "승인", False, "초록"),
         ("앱", "LangGraph", "invoke(None, thread_id=42)", False, "초록"),
         ("LangGraph", "체크포인터", "get(cp1) — 그 자리부터", False, "회색"),
         ("LangGraph", "앱", "최종 답", False, "진파랑")],
        제목="사람 개입(human-in-the-loop)은 체크포인트가 있어야 가능하다",
        폭=640, 줄틈=26))

    # ------------------------------------------------------------------
    c.절("R1.6 코드로 — 같은 일을 사슬과 그래프로")

    c.날것(언어(
        "같은 Corrective RAG 를 두 가지로",
        [("LCEL — 고리를 못 적으니 파이썬으로 감싼다",
          """chain = prompt | model | parser

def corrective_rag(q: str, max_tries: int = 3) -> str:
    for _ in range(max_tries):            # **고리가 프레임워크 밖에 있다**
        docs = retriever.invoke(q)
        if grade(docs, q):
            return chain.invoke({"context": docs, "question": q})
        q = rewrite(q)                     # 상태를 지역 변수로 들고 다닌다
    return FAILED_MSG   # 고리를 다 돌고도 못 찾으면
# 상태는 지역 변수 q 뿐이다 -- 죽으면 사라진다
""",
          "<b>돌아간다.</b> 그리고 작은 문제에는 이게 맞다. "
          "잃는 것은 <b>체크포인트·중단·관측</b>이다 &mdash; 이 함수가 3번째 "
          "바퀴에서 죽으면 처음부터 다시다"),
         ("LangGraph — 고리를 그래프에 적는다",
          """from typing import Annotated, TypedDict
import operator
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    question: str
    docs: Annotated[list, operator.add]   # 리듀서 -- 여러 마디가 모아 쓴다
    tries: Annotated[int, operator.add]   # 가환 -- 순서 무관 (정리 39)
    answer: str                            # 리듀서 없음 -- 둘이 쓰면 터진다

def retrieve(s: State) -> dict:
    return {"docs": search(s["question"]), "tries": 1}

def route(s: State) -> str:
    if grade(s["docs"], s["question"]):   return "answer"
    if s["tries"] >= 3:                    return END      # **걸음 예산**
    return "rewrite"

g = StateGraph(State)
g.add_node("retrieve", retrieve)
g.add_node("rewrite",  lambda s: {"question": rewrite(s["question"])})
g.add_node("answer",   lambda s: {"answer": chain.invoke(s)})
g.add_edge(START, "retrieve")
g.add_conditional_edges("retrieve", route)
g.add_edge("rewrite", "retrieve")         # 되돌아가는 간선
g.add_edge("answer", END)

app = g.compile(checkpointer=SqliteSaver.from_conn_string("cp.db"))
app.invoke({"question": q, "docs": [], "tries": 0},
           config={"configurable": {"thread_id": "42"}})""",
          "<b><code>tries</code> 에 <code>operator.add</code> 를 단 것</b>에 주목하라 "
          "&mdash; 정수 덧셈은 결합적이고 가환적이라 정리 39 를 만족한다. "
          "<code>answer</code> 에는 일부러 리듀서를 안 달았다: "
          "<b>두 마디가 답을 쓰는 것은 버그</b>이므로 터지는 게 맞다"),
         ("상태를 TypedDict 로 적는 이유",
          """# 이것이 이 프레임워크가 요구하는 '대가' 다.
# 사슬에서는 상태가 함수의 지역 변수였다. 그래프에서는
# **상태가 자료형으로 선언돼야** 한다 -- 체크포인터가 직렬화해야 하니까.

class State(TypedDict):
    question: str                          # 직렬화 가능해야 한다
    docs: Annotated[list, operator.add]     # 리듀서를 타입에 붙인다
    # conn: psycopg.Connection              # <- 못 넣는다. 직렬화가 안 된다""",
          "<b>직렬화할 수 없는 것은 상태에 못 넣는다.</b> DB 연결·파일 핸들·소켓은 "
          "<code>config</code> 로 주입하거나 마디 안에서 열고 닫아야 한다. "
          "정리 40 의 &lsquo;체크포인트가 상태 전부를 담는다&rsquo; 가 요구하는 것")],
        짚기="""<b>세 칸이 말하는 것 하나</b>: 고리를 프레임워크 밖에 두면 코드는
        짧아지고 <b>관측·재개·중단을 전부 잃는다</b>. 그래프 안에 두면 그 셋을 얻고
        <b>상태를 자료형으로 선언하는 비용</b>을 낸다. 작은 것은 왼쪽, 오래 도는 것은
        오른쪽이다."""))

    c.날것(레포(
        "langchain-ai/langgraph",
        "github.com/langchain-ai/langgraph", lg["커밋"],
        [("이 책이 읽은 것",
          "<code>libs/langgraph/langgraph/pregel/_loop.py</code> 의 "
          "<code>tick()</code> &middot; "
          "<code>channels/last_value.py</code> &middot; "
          "<code>channels/binop.py</code>"),
         ("규모", f"파이썬 {수(파이썬.get('줄', 0))}줄 &middot; "
                f"파일 {수(lg.get('파일수', 0))}개"),
         ("패키지가 쪼개진 모양",
          "<code>langgraph</code>(알맹이) &middot; "
          "<code>checkpoint</code> / <code>-sqlite</code> / <code>-postgres</code> "
          "&middot; <code>prebuilt</code> &middot; <code>sdk-py</code> / "
          "<code>sdk-js</code> &middot; <code>cli</code> &mdash; "
          "<b>체크포인터가 따로 떨어져 있는 것</b>이 설계의 핵심을 말한다"),
         ("이름의 출처",
          "README 가 <b>Pregel</b>(구글, 2010)과 <b>Apache Beam</b> 에서 왔다고 "
          "밝힌다. 공개 인터페이스는 <b>NetworkX</b> 를 닮게 했다고 적혀 있다"),
         ("정직하게 적자면",
          "이 장은 <code>tick()</code> 한 함수와 채널 두 개를 읽었다. "
          "<code>prepare_next_tasks</code> 안쪽(어느 마디를 깨울지 정하는 논리)과 "
          "인터럽트 구현은 <b>안 읽었다</b>")],
        한마디="정리 38~40 이 실제 코드에서 어떤 이름으로 나타나는가."))

    c.날것(사고("""<b>이 저장소가 같은 자리에서 겪은 것.</b> 다섯 엔지니어를 병렬로
    돌렸을 때, 각자가 <code>house/out/</code> 에 PDF 를 쓰고 <b>같은 원장 파일에
    한 줄씩 덧붙였다.</b> 원장은 채널이고 덧붙이기는 리듀서다 &mdash; 그런데 그
    리듀서가 <b>파일 append</b> 였다. 두 프로세스가 같은 순간에 쓰면 줄이 섞인다.
    LangGraph 의 리듀서가 <b>메모리 안에서</b> 접는 이유가 이것이고, 우리는
    <code>SE_LEDGER_ROOT</code> 로 검사용 원장을 갈라서 같은 문제를 피했다."""))

    c.날것(유도("이 장을 한 문단으로", [
        ("<code>|</code> 는 한 방향이라 고리를 못 적는다",
         "&lsquo;아니면 다시&rsquo; 가 필요한 순간 사슬이 끝난다"),
        ("그래서 마디와 간선으로 바꾼다",
         "조건부 간선이 같은 마디를 가리키면 그것이 고리다"),
        ("한 걸음은 슈퍼스텝이다 &mdash; 읽기 · 실행 · 쓰기 · 저장",
         "BSP. <code>tick()</code> 한 번이 그것이고 반환값이 종료 조건이다"),
        ("단계 안에서는 실행 순서가 결과를 안 바꾼다",
         "정리 38 &mdash; 모두가 같은 스냅숏을 읽고 쓰기는 단계 끝에 모인다"),
        ("여럿이 한 칸에 쓰면 리듀서가 접는다",
         "결합적·가환적이어야 결정적이다(정리 39). 아니면 <b>거절하는 것이 옳다</b>"),
        ("<code>operator.add</code> 는 가환이 아니다",
         "리스트 순서가 실행마다 달라진다 &mdash; 재현 안 되는 가장 흔한 버그"),
        ("슈퍼스텝마다 체크포인트가 남는다",
         "정리 40 &mdash; 재개가 끊김 없는 실행과 같아진다(부작용만 빼고)"),
        ("그 대가는 <b>상태를 자료형으로 선언하는 것</b>이다",
         "직렬화 못 하는 것은 상태에 못 들어간다"),
    ]))

    c.날것(논문출처([
        ["langchain-ai/langgraph 소스", f"github @ {lg['커밋']}", "<b>코드</b>",
         "R1 전체 &mdash; tick() · LastValue · BinaryOperatorAggregate"],
        ["Malewicz 외, <i>Pregel: A System for Large-Scale Graph Processing</i>",
         "SIGMOD 2010", "<b>조각</b>", "R1.3 의 BSP 모형 (정리는 직접 세웠다)"],
        ["Valiant, <i>A Bridging Model for Parallel Computation</i>",
         "CACM 1990", "<b>조각</b>", "BSP 의 출처"],
    ]))

    return c.완성()
