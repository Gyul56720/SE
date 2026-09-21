# -*- coding: utf-8 -*-
"""D2 -- 어휘 검색. BM25 의 모든 항이 어디서 나왔는가, 그리고 왜 아직 안 죽었는가."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "edu"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 정의, 유도, 예제, 짚기, 사고, 수  # noqa: E402
from bookA import 정리, 보조정리, 따름정리, 논문출처, 언어, 직무  # noqa: E402


def idf(N, n):
    return math.log((N - n + 0.5) / (n + 0.5) + 1)


def 포화(tf, k1=1.2):
    return tf * (k1 + 1) / (tf + k1)


def bm25(tf, dl, avgdl, N, n, k1=1.2, b=0.75):
    분모 = tf + k1 * (1 - b + b * dl / avgdl)
    return idf(N, n) * tf * (k1 + 1) / 분모


def rrf(순위들, k=60):
    return sum(1.0 / (k + r) for r in 순위들)


def ch_lexical():
    N = 1_000_000
    tf표 = [(t, 포화(t)) for t in (1, 2, 5, 10, 50)]
    idf표 = [(n, idf(N, n)) for n in (1, 100, 10_000, 500_000)]

    c = 장(
        "D2", "어휘 검색 — BM25 의 세 항과 혼합 순위",
        "벡터가 못 찾는 것이 있다. <b>정확한 낱말</b>이다 &mdash; 오류 코드, 함수 "
        "이름, 사람 이름, 모델 번호. 그것을 찾는 40년 된 식을 <b>처음부터</b> 세운다.",
        쓰는것=["검색", "재현율", "정밀도", "임베딩", "청킹", "RAG", "코사인유사도"],
        내놓는것=["역색인", "용어빈도", "역문서빈도", "BM25", "포화", "길이정규화",
              "혼합검색", "상호순위융합", "재순위", "어휘간극"],
        특허="""<b>어떻게 섞는가</b>(가중 합 · 상호순위융합 · 학습된 융합)와
        <b>질의 확장</b>이 발명 자리다. BM25 자체는 1994년 Robertson 외이고 공개돼 있다.""")

    c.날것(직무(["NAV.RAG", "KAK.브라우징", "KAK.환경"]))

    c.글("""&ldquo;임베딩이 있는데 왜 아직 BM25 를 쓰나&rdquo; 는 좋은 질문이고, 답은
    <b>둘이 서로 다른 실패를 한다</b> 는 것이다. 벡터는 <code>ERR_CONN_RESET</code> 을
    &lsquo;연결 오류 비슷한 것&rsquo; 으로 뭉개고, BM25 는 &lsquo;차를 못 타겠다&rsquo; 와
    &lsquo;자동차 운행 불가&rsquo; 를 다른 것으로 본다. 에이전트의 검색 도구는 거의 언제나
    <b>둘 다</b> 있어야 한다.""")

    c.날것(정의("역색인 (inverted index)",
              "&lsquo;낱말 &rarr; 그 낱말이 든 문서 목록&rsquo; 표. 문서 &rarr; 낱말의 반대라서 "
              "&lsquo;역&rsquo; 이다. 질의 낱말의 목록만 꺼내 합치면 되므로 <b>문서 수가 아니라 "
              "질의 낱말 수</b>에 비례한다."))
    c.날것(정의("어휘 간극 (vocabulary mismatch)",
              "묻는 사람의 낱말과 문서의 낱말이 다른 것. 어휘 검색의 근본 한계이고, "
              "임베딩이 풀려는 문제가 정확히 이것이다."))

    # ------------------------------------------------------------------
    c.절("D2.1 IDF 는 어디서 나왔나 — 확률적 적합성")

    c.날것(정의("용어 빈도 · 역문서 빈도 (TF · IDF)",
              "TF 는 이 문서에 낱말이 몇 번 나왔나, IDF 는 그 낱말이 <b>전체에서 "
              "얼마나 드문가</b>. 드문 낱말이 나오면 정보가 많다는 직관을 식으로 "
              "옮긴 것 &mdash; 아래에서 <b>직관이 아니라 유도로</b> 얻는다."))

    c.날것(정리(
        "IDF 는 적합 확률의 로그 오즈비에서 나온다",
        """문서가 적합(<i>R</i>)한지 아닌지를 두고, 낱말 <i>t</i> 의 출현
        <i>x</i><sub><i>t</i></sub>&isin;{0,1} 들이 <b>조건부 독립</b>이라 하자.
        <i>p</i><sub><i>t</i></sub> = P(<i>x</i><sub><i>t</i></sub>=1|<i>R</i>),
        <i>q</i><sub><i>t</i></sub> = P(<i>x</i><sub><i>t</i></sub>=1|&not;<i>R</i>) 로 두면,
        문서 순위를 정하는 데 쓰이는 로그 오즈비는 출현한 낱말들에 대해
        <div class="math">&Sigma;<sub><i>t</i>:<i>x</i><sub><i>t</i></sub>=1</sub>
        log [<i>p</i><sub><i>t</i></sub>(1&minus;<i>q</i><sub><i>t</i></sub>) /
        <i>q</i><sub><i>t</i></sub>(1&minus;<i>p</i><sub><i>t</i></sub>)]</div>
        이다. 적합 문서를 모르는 상태에서 <i>p</i><sub><i>t</i></sub> = &frac12; 로 두고
        <i>q</i><sub><i>t</i></sub> &approx; <i>n</i><sub><i>t</i></sub>/<i>N</i> 으로 추정하면
        각 항이 <b>log((<i>N</i>&minus;<i>n</i><sub><i>t</i></sub>)/<i>n</i><sub><i>t</i></sub>)</b>
        &mdash; 즉 IDF 가 된다.""",
        [("베이즈에 의해 P(<i>R</i>|<i>d</i>)/P(&not;<i>R</i>|<i>d</i>) = [P(<i>d</i>|<i>R</i>)/P(<i>d</i>|&not;<i>R</i>)]&middot;[P(<i>R</i>)/P(&not;<i>R</i>)].",
          "오즈 꼴의 베이즈 정리. 뒤 인수는 문서에 안 딸리므로 순위에 영향이 없다."),
         ("조건부 독립 가정에서 P(<i>d</i>|<i>R</i>) = &prod;<sub><i>t</i></sub> <i>p</i><sub><i>t</i></sub><sup><i>x</i><sub><i>t</i></sub></sup>(1&minus;<i>p</i><sub><i>t</i></sub>)<sup>1&minus;<i>x</i><sub><i>t</i></sub></sup>.",
          "독립이면 결합확률이 곱이 된다."),
         ("비를 취해 로그를 씌우면 &Sigma;<sub><i>t</i></sub>[<i>x</i><sub><i>t</i></sub> log(<i>p</i><sub><i>t</i></sub>/<i>q</i><sub><i>t</i></sub>) + (1&minus;<i>x</i><sub><i>t</i></sub>)log((1&minus;<i>p</i><sub><i>t</i></sub>)/(1&minus;<i>q</i><sub><i>t</i></sub>))].",
          "2 를 <i>R</i> 과 &not;<i>R</i> 에 각각 적용해 나눈 뒤 로그의 곱셈을 합으로 폈다."),
         ("두 번째 항을 &Sigma;<sub>모든 <i>t</i></sub> log((1&minus;<i>p</i>)/(1&minus;<i>q</i>)) &minus; &Sigma;<sub><i>x</i><sub><i>t</i></sub>=1</sub> log(&middot;) 로 쪼개면 앞 덩어리가 문서와 무관한 상수가 된다.",
          "<i>x</i><sub><i>t</i></sub>=0 인 항을 &lsquo;전부&rsquo; 에서 &lsquo;나온 것&rsquo; 을 빼는 꼴로 다시 쓴 것 &mdash; 표준 변형이다."),
         ("남는 것은 출현한 낱말에 대한 &Sigma; log[<i>p</i>(1&minus;<i>q</i>)/(<i>q</i>(1&minus;<i>p</i>))].",
          "3 과 4 를 합치고 상수를 버렸다 &mdash; 순위만 보면 되므로."),
         ("<i>p</i><sub><i>t</i></sub>=&frac12; 를 넣으면 <i>p</i>(1&minus;<i>p</i>) 부분이 1 이 되어 log((1&minus;<i>q</i><sub><i>t</i></sub>)/<i>q</i><sub><i>t</i></sub>) 만 남는다.",
          "적합 문서를 모를 때의 무정보 가정. &frac12;/(1&minus;&frac12;)=1."),
         ("<i>q</i><sub><i>t</i></sub> = <i>n</i><sub><i>t</i></sub>/<i>N</i> 을 넣으면 log((<i>N</i>&minus;<i>n</i><sub><i>t</i></sub>)/<i>n</i><sub><i>t</i></sub>).",
          "부적합 문서가 거의 전부이므로 <i>q</i> 를 전체 문서빈도로 근사한다."),
         ("실무의 +0.5 와 +1 은 <i>n</i><sub><i>t</i></sub>=0 또는 <i>n</i><sub><i>t</i></sub>&gt;<i>N</i>/2 에서 값이 발산·음수가 되는 것을 막는 평활이다.",
          "log((<i>N</i>&minus;<i>n</i>+0.5)/(<i>n</i>+0.5)+1) 이 그 꼴이고, 바깥 +1 이 음수를 막는다."),
         ],
        가정="<b>조건부 독립</b>은 명백히 거짓이다(낱말은 같이 다닌다). 그래도 순위 매기기에는 놀랄 만큼 잘 듣는다 &mdash; 나이브 베이즈가 잘 듣는 것과 같은 이유."))

    c.날것(표(f"IDF 의 값. 전체 문서 {수(N)} 개 기준.",
            ["그 낱말이 든 문서 수", "IDF", "뜻"],
            [[f"{수(n)}", f"{수(v, 4)}",
              {1: "거의 유일하다 &mdash; 이 낱말 하나로 문서가 정해진다",
               100: "특이하다 &mdash; 오류 코드 · 고유명사",
               10_000: "흔하다",
               500_000: "절반에 있다 &mdash; <b>거의 정보가 없다</b>"}[n]]
             for n, v in idf표]))

    # ------------------------------------------------------------------
    c.절("D2.2 포화 — 왜 100번 나온다고 100배가 아닌가")

    c.날것(정의("포화 (saturation)",
              "낱말이 두 번 나오면 한 번보다 낫지만 <b>두 배로 낫지는 않다</b>는 것. "
              "BM25 의 <i>tf</i>(<i>k</i><sub>1</sub>+1)/(<i>tf</i>+<i>k</i><sub>1</sub>) "
              "항이 이것을 만든다."))

    c.날것(정리(
        "BM25 의 TF 항은 증가하고 오목하며 위로 막혀 있다",
        """<i>f</i>(<i>x</i>) = <i>x</i>(<i>k</i><sub>1</sub>+1)/(<i>x</i>+<i>k</i><sub>1</sub>),
        <i>x</i> &ge; 0, <i>k</i><sub>1</sub> &gt; 0 은
        (i) <i>f</i>(0)=0, (ii) <i>f</i>&prime;&gt;0, (iii) <i>f</i>&Prime;&lt;0,
        (iv) <i>f</i>(<i>x</i>) &rarr; <i>k</i><sub>1</sub>+1 을 만족한다.
        따라서 <b>한 낱말이 아무리 많이 나와도 그 낱말의 기여는
        <i>k</i><sub>1</sub>+1 배 IDF 를 못 넘는다.</b>""",
        [("<i>f</i>(0) = 0.",
          "분자에 <i>x</i> 가 인수로 있다."),
         ("<i>f</i>(<i>x</i>) = (<i>k</i><sub>1</sub>+1)[1 &minus; <i>k</i><sub>1</sub>/(<i>x</i>+<i>k</i><sub>1</sub>)] 로 다시 쓴다.",
          "<i>x</i>/(<i>x</i>+<i>k</i><sub>1</sub>) = 1 &minus; <i>k</i><sub>1</sub>/(<i>x</i>+<i>k</i><sub>1</sub>) 를 대입한 것."),
         ("<i>f</i>&prime;(<i>x</i>) = (<i>k</i><sub>1</sub>+1)<i>k</i><sub>1</sub>/(<i>x</i>+<i>k</i><sub>1</sub>)<sup>2</sup> &gt; 0.",
          "2 를 미분했다. 모든 인수가 양수."),
         ("<i>f</i>&Prime;(<i>x</i>) = &minus;2(<i>k</i><sub>1</sub>+1)<i>k</i><sub>1</sub>/(<i>x</i>+<i>k</i><sub>1</sub>)<sup>3</sup> &lt; 0.",
          "3 을 한 번 더 미분했다 &mdash; 부호가 음수라 오목하다."),
         ("<i>x</i>&rarr;&infin; 에서 2 의 대괄호가 1 로 가므로 극한이 <i>k</i><sub>1</sub>+1.",
          "<i>k</i><sub>1</sub>/(<i>x</i>+<i>k</i><sub>1</sub>) &rarr; 0."),
         (f"그러므로 <i>k</i><sub>1</sub>=1.2 에서 상한이 {수(2.2, 2)} 이고, "
          f"<i>tf</i>=50 에서 이미 {수(포화(50), 4)} 로 상한에 거의 닿는다.",
          "5 의 극한값과 <i>f</i>(50) 을 빌드할 때 계산한 것."),
         ],
        가정="<i>k</i><sub>1</sub> &gt; 0. <i>k</i><sub>1</sub> 이 작을수록 빨리 포화한다(<i>k</i><sub>1</sub>&rarr;0 이면 사실상 &lsquo;있다/없다&rsquo;)."))

    c.날것(표("포화의 모양 (<i>k</i><sub>1</sub>=1.2). <b>다섯 번과 쉰 번의 차이가 거의 없다.</b>",
            ["용어 빈도 <i>tf</i>", "TF 항", "한 번 대비"],
            [[f"{t}", f"{수(v, 4)}", f"{수(v/포화(1), 3)}&times;"] for t, v in tf표]))

    c.날것(짚기("""<b>포화가 없으면 무슨 일이 나는지가 이 항의 존재 이유다.</b>
    순진한 TF-IDF 는 &ldquo;검색&nbsp;검색&nbsp;검색&nbsp;&hellip;&rdquo; 을 백 번 쓴 스팸
    문서를 1위로 올린다. 포화는 <b>스팸에 대한 방어</b>이고, 동시에 &lsquo;이 문서가
    이 주제를 다루는가&rsquo; 라는 이진 질문에 가까운 것이 진짜 신호라는 사실을 담고 있다."""))

    c.날것(유도("길이 정규화 항 <i>b</i> 는 무엇을 막는가", [
        ("긴 문서는 그냥 우연히 낱말을 더 많이 담는다",
         "길이가 두 배면 아무 낱말이나 대략 두 배 나온다"),
        ("그러면 TF 만 보고는 &lsquo;주제를 다룬다&rsquo; 와 &lsquo;길어서 스쳤다&rsquo; 를 못 가른다",
         "두 경우 모두 <i>tf</i> 가 크다"),
        ("그래서 분모의 <i>k</i><sub>1</sub> 을 문서 길이에 따라 키운다: <i>k</i><sub>1</sub>(1&minus;<i>b</i>+<i>b</i>&middot;<i>dl</i>/avgdl)",
         "긴 문서일수록 분모가 커져 같은 <i>tf</i> 가 더 낮은 점수를 받는다"),
        ("<i>b</i>=0 이면 길이를 무시하고, <i>b</i>=1 이면 완전히 길이로 나눈다",
         "대괄호가 각각 1 과 <i>dl</i>/avgdl 이 된다"),
        ("기본값 0.75 는 &lsquo;대체로 정규화하되 완전히는 아니게&rsquo; 다",
         "긴 문서가 실제로 내용이 더 많은 경우도 있으므로 전부 나누면 과하다"),
        ("<b>에이전트의 청킹이 이 항을 무력화할 수 있다</b>",
         "조각 길이를 다 똑같이 잘라 놓으면 <i>dl</i>/avgdl &approx; 1 이라 <i>b</i> 가 아무 일도 안 한다"),
    ]))

    # ------------------------------------------------------------------
    c.절("D2.3 섞기 — 점수를 더하지 말고 순위를 더한다")

    c.날것(정의("혼합 검색 (hybrid search)",
              "어휘 검색과 벡터 검색의 결과를 합쳐 하나의 순위를 만드는 것."))
    c.날것(정의("상호순위 융합 (reciprocal rank fusion, RRF)",
              "문서 <i>d</i> 의 점수를 &Sigma;<sub>시스템 <i>s</i></sub> "
              "1/(<i>k</i> + rank<sub><i>s</i></sub>(<i>d</i>)) 로 두는 것. "
              "<b>점수가 아니라 순위만</b> 쓴다."))

    c.날것(정리(
        "RRF 는 점수 눈금에 영향받지 않는다",
        """각 시스템의 점수에 <b>순서를 보존하는 임의의 변환</b>(단조증가 함수)을
        걸어도 RRF 의 결과는 바뀌지 않는다. 반면 <b>점수를 가중합하는 융합은
        바뀐다.</b>""",
        [("RRF 는 rank<sub><i>s</i></sub>(<i>d</i>) 만 인자로 받는다.",
          "정의를 보면 점수값이 식에 안 들어간다."),
         ("단조증가 변환 &phi; 를 점수에 걸어도 정렬 순서는 안 바뀐다.",
          "<i>a</i>&lt;<i>b</i> &hArr; &phi;(<i>a</i>)&lt;&phi;(<i>b</i>) 가 단조증가의 정의."),
         ("따라서 rank 가 안 바뀌고, RRF 점수도 안 바뀐다.",
          "1 과 2."),
         ("반면 가중합 &alpha;<i>s</i><sub>1</sub>+(1&minus;&alpha;)<i>s</i><sub>2</sub> 에서 <i>s</i><sub>1</sub> 을 100 배 하면 사실상 <i>s</i><sub>1</sub> 만 남는다.",
          "&phi;(<i>x</i>)=100<i>x</i> 는 단조증가인데 합의 결과를 완전히 바꾼다 &mdash; 반례."),
         ("BM25 점수는 위로 안 막혀 있고 코사인은 [&minus;1,1] 이라 눈금이 애초에 다르다.",
          "정리 22 에서 BM25 의 한 낱말 기여 상한이 (<i>k</i><sub>1</sub>+1)&middot;IDF 이고 낱말 수만큼 더해진다 &mdash; 코사인과 비교 가능한 눈금이 아니다."),
         ("그러므로 정규화 없이 둘을 더하는 것은 <b>암묵적으로 한쪽을 고르는 것</b>이다.",
          "4 와 5 &mdash; 눈금 차이가 곧 가중치가 된다."),
         ],
        가정="순위에 동점이 없다. 동점 처리 규칙이 다르면 결과가 갈릴 수 있다."))

    c.날것(예제(
        "RRF 의 <i>k</i>=60 은 무엇을 하나",
        """시스템 A 에서 1위, 시스템 B 에서 100위인 문서 X.
        두 시스템 모두에서 10위인 문서 Y.""",
        f"""X = 1/(60+1) + 1/(60+100) = {수(rrf([1, 100]), 4)}.
        Y = 2/(60+10) = {수(rrf([10, 10]), 4)}.""",
        f"""<b>Y 가 이긴다</b> ({수(rrf([10,10]), 4)} &gt; {수(rrf([1,100]), 4)}).
        <i>k</i> 가 클수록 상위권의 우대가 완만해져서 <b>&lsquo;두 시스템이 모두
        그런대로 좋다고 한 것&rsquo;</b> 이 <b>&lsquo;하나만 아주 좋다고 한 것&rsquo;</b> 을 이긴다.""",
        f"""<b><i>k</i> 를 작게 두면 반대가 된다.</b> <i>k</i>=1 이면
        X = {수(rrf([1, 100], 1), 4)}, Y = {수(rrf([10, 10], 1), 4)} 로 X 가 이긴다.
        <i>k</i> 는 &lsquo;마법 상수&rsquo; 가 아니라 <b>합의를 얼마나 중시하는가</b> 라는
        설계 결정이다 &mdash; 그리고 대부분의 구현이 60 을 아무 생각 없이 베낀다.""",
        덧="""에이전트에서는 대개 합의를 중시하는 쪽(<i>k</i> 크게)이 맞다.
        한 시스템이 1위로 올린 엉뚱한 문서가 문맥에 들어가면 그 뒤 추론이 통째로
        오염되기 때문이다(A6 의 컨텍스트 오염)."""))

    c.날것(개념(
        "에이전트의 검색 도구는 둘을 다 준다",
        """<b>이론.</b> 벡터는 어휘 간극을 메우고 BM25 는 정확한 낱말을 잡는다.
        둘의 실패가 <b>상관되지 않으므로</b>(B3 의 정리 11 을 떠올려라) 합치면
        실제로 이득이 난다 &mdash; 자기일관성이 상관 때문에 포화하는 것과 반대다.""",
        어디에="""에이전트가 부르는 <code>search</code> 도구 하나 안에서. 도구를
        둘로 나누면 <b>모형이 매번 어느 것을 쓸지 고민</b>하게 되어 걸음이 는다""",
        언제="""거의 언제나. 코드베이스 · 로그 · 사내 문서처럼 <b>고유명사가 많은</b>
        자료일수록 BM25 쪽 기여가 크다""",
        어떻게="""(1) 두 색인을 따로 둔다 &rarr; (2) 각각 상위 <i>K</i>&prime;(&approx;50)를
        받는다 &rarr; (3) RRF 로 합친다 &rarr; (4) 상위 <i>K</i>(&approx;10)만
        <b>재순위 모형</b>에 넣는다 &rarr; (5) 최종 <i>k</i> 개를 문맥에 넣는다""",
        산업코드="""def search(q: str, k: int = 8) -> list[Doc]:
    lex = bm25_index.top(q, 50)             # 정확한 낱말
    vec = vector_index.top(embed(q), 50)    # 뜻
    fused = {}
    for src in (lex, vec):                  # RRF -- 점수가 아니라 순위
        for r, d in enumerate(src, start=1):
            fused[d.id] = fused.get(d.id, 0.0) + 1.0 / (60 + r)
    top = sorted(fused, key=fused.get, reverse=True)[:25]
    return cross_encoder_rerank(q, top)[:k]  # 비싼 모형은 25개에만""",
        주의="""<b>(4) 의 재순위를 빼먹으면 혼합의 이득 대부분이 날아간다.</b>
        RRF 는 두 순위를 합칠 뿐 <b>질의와 문서를 같이 보지 않는다</b>.
        교차 인코더는 둘을 한 입력으로 넣어 보므로 훨씬 정확하고, 25개에만 쓰면
        비용도 감당된다. 이것이 &lsquo;검색 &rarr; 재순위&rsquo; 두 단계 구조의 이유다."""))

    c.날것(사고("""<b>이 저장소에서 난 일.</b> 코드 검색을 임베딩만으로 하던 판에서,
    <code>pgrep -af</code> 를 찾는 질의가 <code>pkill -f</code> 문단을 1위로 올렸다.
    뜻으로는 가깝다 &mdash; 둘 다 &lsquo;프로세스를 패턴으로 찾는다&rsquo; 다. 그런데
    CLAUDE.md 가 말하는 것은 정확히 <b>그 둘의 차이</b>였다(<code>pkill -f</code> 는
    자기 셸까지 죽인다). <b>어휘 검색이 필요한 자리가 바로 이런 곳이다</b> &mdash;
    글자 하나가 뜻을 뒤집는 자리."""))

    c.날것(언어(
        "역색인 한 조각을 세 말로",
        [("Python — 표준 라이브러리만으로",
          """from collections import defaultdict
import math, re

class BM25:
    def __init__(self, docs: list[str], k1=1.2, b=0.75):
        self.k1, self.b = k1, b
        self.inv: dict[str, dict[int, int]] = defaultdict(dict)
        self.dl = []
        for i, d in enumerate(docs):
            toks = re.findall(r"\\w+", d.lower())
            self.dl.append(len(toks))
            for t in toks:
                self.inv[t][i] = self.inv[t].get(i, 0) + 1
        self.N, self.avgdl = len(docs), sum(self.dl) / max(1, len(docs))

    def idf(self, t: str) -> float:
        n = len(self.inv.get(t, ()))
        return math.log((self.N - n + 0.5) / (n + 0.5) + 1)""",
          "<code>defaultdict</code> 이 &lsquo;없으면 만든다&rsquo; 를 공짜로 준다. "
          "<b>그리고 그것이 위험하다</b> &mdash; 오타 난 낱말을 조회해도 빈 칸이 "
          "<i>생겨서</i> 색인이 조용히 자란다"),
         ("Java (Spring) — 검색이 서비스 경계 뒤에 있을 때",
          """@RestController
@RequestMapping("/search")
public class SearchController {

    private final HybridSearchService svc;        // 생성자 주입 -- 필드 주입 금지

    public SearchController(HybridSearchService svc) { this.svc = svc; }

    @GetMapping
    public List<DocDto> search(
            @RequestParam @NotBlank String q,
            @RequestParam(defaultValue = "8") @Min(1) @Max(50) int k) {
        return svc.hybrid(q, k);                  // BM25 + 벡터 + RRF
    }
}""",
          "스프링의 알맹이는 <b>의존성 주입</b>이다 &mdash; <code>new</code> 를 직접 "
          "안 쓰고 컨테이너가 넣어 준다. 그래서 검사에서 가짜 서비스로 갈아 끼울 수 "
          "있다. <code>@Min/@Max</code> 는 <b>선언으로</b> 검증하는 자리 &mdash; "
          "<code>k=10000</code> 같은 요청이 서비스 코드에 닿기 전에 막힌다. "
          "필드 주입(<code>@Autowired</code> 를 필드에) 대신 생성자 주입을 쓰는 이유는 "
          "<b>의존성을 못 빠뜨리게</b> 컴파일러가 붙들기 때문이다"),
         ("셸 — 색인 없이 급할 때. 그리고 이게 의외로 자주 맞다",
          """# ripgrep 은 .gitignore 를 존중하고 병렬로 읽는다
rg --json -S -C 2 -g '!*.lock' "$PAT" \\
  | jq -r 'select(.type=="match")
           | "\\(.data.path.text):\\(.data.line_number)\\t\\(.data.lines.text)"' \\
  | head -n 40

# -S  대소문자 자동(소문자 질의면 무시, 대문자 있으면 구별)
# -C 2 앞뒤 두 줄 -- 청킹을 명령줄에서 하는 셈""",
          "<b>코드베이스에서는 이 한 줄이 벡터 검색보다 나은 경우가 많다.</b> "
          "정확한 낱말이 전부이고, 색인을 지을 필요도 최신성 문제도 없다. "
          "에이전트의 검색 도구를 설계할 때 <b>먼저 이것으로 되는지</b>를 봐야 한다")],
        짚기="""세 칸이 서로 다른 <b>층</b>이다 &mdash; 알고리즘(Python) ·
        서비스 경계(Spring) · 그냥 도구(셸). 에이전트 검색 도구를 만들 때
        <b>어느 층에서 풀 문제인지</b>를 먼저 정해야 한다. 대부분의 &lsquo;RAG
        파이프라인&rsquo; 은 셸 한 줄로 되는 일에 세 층을 다 쌓은 것이다."""))

    c.날것(유도("이 장을 한 문단으로", [
        ("IDF 는 직관이 아니라 로그 오즈비에서 나온다",
         "정리 21 &mdash; 조건부 독립 + 무정보 가정"),
        ("TF 항은 포화한다",
         "정리 22 &mdash; 증가·오목·유계. 스팸 방어이자 &lsquo;다루는가&rsquo; 라는 이진 신호"),
        ("길이 항 <i>b</i> 는 &lsquo;길어서 스친 것&rsquo; 을 깎는다",
         "긴 문서가 우연히 낱말을 더 담기 때문"),
        ("벡터와 어휘는 <b>다른 실패</b>를 한다",
         "그래서 합치면 실제로 이득이다 &mdash; B3 의 상관 이야기와 정반대 방향"),
        ("합칠 때는 점수가 아니라 순위를 더한다",
         "정리 23 &mdash; 눈금이 다르면 가중합은 암묵적으로 한쪽만 쓴다"),
        ("그리고 합친 상위 몇십 개만 교차 인코더에 넣는다",
         "질의와 문서를 같이 보는 유일한 단계이고, 비싸서 좁혀 놓고 쓴다"),
    ]))

    c.날것(논문출처([
        ["Robertson &amp; Walker, <i>Some simple effective approximations to "
         "the 2-Poisson model</i>", "SIGIR 1994", "<b>조각</b>",
         "정리 21·22 &mdash; 유도는 이 책이 직접 했다"],
        ["Cormack 외, <i>Reciprocal Rank Fusion</i>", "SIGIR 2009", "<b>조각</b>",
         "정리 23 의 이름과 <i>k</i>=60 관행"],
    ]))

    return c.완성()
