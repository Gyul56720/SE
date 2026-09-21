# -*- coding: utf-8 -*-
"""D1 -- 벡터 검색의 수학. 뜻을 왜 좌표로 바꿀 수 있는가."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "edu"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 정의, 유도, 예제, 짚기, 사고, 수  # noqa: E402
from bookA import 정리, 보조정리, 따름정리, 논문출처, 언어, 직무  # noqa: E402


def jl차원(n, eps=0.2, 상수=8.0):
    """JL 보조정리가 요구하는 목표 차원 k >= 8 ln n / eps^2."""
    return math.ceil(상수 * math.log(n) / eps ** 2)


def 거리집중(d, n=1000, 씨=20260921):
    """고차원에서 최근접과 최원접의 비가 1 로 가는 것을 **재서** 보인다."""
    r = random.Random(씨)
    q = [r.gauss(0, 1) for _ in range(d)]
    최소, 최대 = float("inf"), 0.0
    for _ in range(n):
        x = [r.gauss(0, 1) for _ in range(d)]
        s = math.sqrt(sum((a - b) ** 2 for a, b in zip(q, x)))
        최소, 최대 = min(최소, s), max(최대, s)
    return 최대 / 최소


def jl실측(d=2000, k=None, n=300, eps=0.2, 씨=20260921):
    """무작위 사영을 실제로 해서 거리 왜곡의 최댓값을 잰다."""
    k = k or jl차원(n, eps)
    r = random.Random(씨)
    X = [[r.gauss(0, 1) for _ in range(d)] for _ in range(n)]
    R = [[r.gauss(0, 1) / math.sqrt(k) for _ in range(d)] for _ in range(k)]
    Y = [[sum(R[j][t] * x[t] for t in range(d)) for j in range(k)] for x in X]
    최대왜곡 = 0.0
    for i in range(0, n, 7):                      # 표본 쌍만 본다(시간)
        for j in range(i + 1, min(i + 20, n)):
            a = math.dist(X[i], X[j])
            b = math.dist(Y[i], Y[j])
            if a > 0:
                최대왜곡 = max(최대왜곡, abs(b / a - 1))
    return k, 최대왜곡


def ch_vector():
    k1, 왜곡 = jl실측()
    비 = [(d, 거리집중(d)) for d in (2, 16, 256)]

    c = 장(
        "D1", "벡터 검색의 수학 — 뜻을 좌표로 바꾸면 무엇이 보장되나",
        "&ldquo;비슷한 글은 가까운 벡터&rdquo; 는 구호다. 그 구호가 <b>언제 참이고 "
        "차원이 높아지면 무엇이 망가지는지</b>를 증명으로 본다.",
        쓰는것=["검색", "재현율", "정밀도", "의미기억", "에피소드기억", "컨텍스트예산",
             "회프딩부등식"],
        내놓는것=["임베딩", "내적", "코사인유사도", "차원의저주", "거리집중",
              "존슨린덴슈트라우스", "무작위사영", "최대내적탐색", "MIPS환원",
              "정규화", "청킹", "RAG"],
        특허="""<b>무엇을 한 조각으로 묶는가</b>(청킹)와 <b>질의와 문서를 같은 공간에
        놓는 방법</b>(비대칭 인코딩 · 쿼리 확장)이 발명 자리다. 내적으로 유사도를
        재는 것 자체는 1975년 벡터공간모형이다.""")

    c.날것(직무(["NAV.RAG", "NAV.메모리", "KAK.검색에이전트"]))

    c.글("""A8 에서 &lsquo;검색&rsquo; 을 메모리의 한 갈래로 두었다. 4부는 그 검색을
    제대로 판다. 에이전트가 자기 문맥에 무엇을 넣을지 고르는 일(A6 의 선택적 주입)이
    곧 검색이므로, <b>검색이 나쁘면 그 위의 추론이 아무리 좋아도 소용이 없다</b>.""")

    c.날것(정의("RAG (retrieval-augmented generation)",
              "모형의 가중치에 없는 지식을 <b>찾아서 문맥에 넣어</b> 답하게 하는 것. "
              "찾기(retrieval) + 넣기(augmentation) + 짓기(generation) 세 단계이고, "
              "<b>거의 모든 실패는 첫 단계에서 난다</b>."))
    c.날것(정의("임베딩 (embedding)",
              "글 조각 하나를 <i>d</i> 차원 실벡터로 보내는 함수. &lsquo;뜻이 비슷하면 "
              "가깝게&rsquo; 되도록 학습된다. <b>어떤 뜻으로 비슷한지는 학습 데이터가 정한다</b> "
              "&mdash; 그래서 도메인이 다르면 그냥 안 맞는다."))
    c.날것(정의("청킹 (chunking)",
              "긴 문서를 검색 단위로 자르는 것. 너무 잘게 자르면 문맥이 끊기고, "
              "크게 자르면 한 조각에 여러 주제가 섞여 벡터가 <b>평균으로 뭉개진다</b>."))

    # ------------------------------------------------------------------
    c.절("D1.1 내적 · 코사인 · 정규화 — 셋은 같은 것이 아니다")

    c.날것(정의("코사인 유사도 (cosine similarity)",
              "cos(<i>u</i>,<i>v</i>) = &lt;<i>u</i>,<i>v</i>&gt; / (&#8214;<i>u</i>&#8214;&#8214;<i>v</i>&#8214;). "
              "길이를 무시하고 <b>방향만</b> 본다."))

    c.날것(정리(
        "정규화는 순위를 바꾼다",
        """벡터 <i>q</i> 와 후보 <i>a</i>, <i>b</i> 에 대해
        &lt;<i>q</i>,<i>a</i>&gt; &gt; &lt;<i>q</i>,<i>b</i>&gt; 이면서
        cos(<i>q</i>,<i>a</i>) &lt; cos(<i>q</i>,<i>b</i>) 인 경우가 존재한다.
        따라서 <b>&lsquo;내적으로 찾기&rsquo; 와 &lsquo;코사인으로 찾기&rsquo; 는 다른 검색이다.</b>
        모든 벡터의 길이가 같을 때만 둘이 같아진다.""",
        [("<i>q</i> = (1,0), <i>a</i> = (2,2), <i>b</i> = (1,0) 을 잡자.",
          "가장 작은 반례를 고른 것이다."),
         ("&lt;<i>q</i>,<i>a</i>&gt; = 2, &lt;<i>q</i>,<i>b</i>&gt; = 1 이므로 내적은 <i>a</i> 가 이긴다.",
          "성분끼리 곱해 더한 값."),
         ("cos(<i>q</i>,<i>a</i>) = 2/(1&middot;2&radic;2) = 1/&radic;2 &approx; 0.707, cos(<i>q</i>,<i>b</i>) = 1.",
          "내적을 두 길이의 곱으로 나눈 것. &#8214;<i>a</i>&#8214; = 2&radic;2, &#8214;<i>b</i>&#8214; = 1."),
         ("그러므로 코사인은 <i>b</i> 가 이긴다 &mdash; 순위가 뒤집혔다.",
          "2 와 3 을 비교하면 된다."),
         ("길이가 모두 1 이면 cos = 내적이므로 두 순위가 같다.",
          "분모가 1 이 되어 정의가 일치한다."),
         ],
        가정="없다 &mdash; 구체적 반례다."))

    c.날것(짚기("""<b>이것이 실무에서 나는 사고의 모양.</b> 임베딩 모형을 바꿨는데
    한쪽은 정규화된 벡터를 내고 한쪽은 안 낸다. 벡터 DB 의 거리 함수는 그대로
    <code>ip</code>(내적)로 두었다. <b>코드는 멀쩡히 돌고 검색 품질만 조용히 떨어진다.</b>
    긴 문서가 무조건 위로 올라오는 증상이면 이것을 의심한다 &mdash; 길이가 곧 점수가
    되기 때문이다."""))

    # ------------------------------------------------------------------
    c.절("D1.2 최대 내적 탐색은 최근접 이웃 탐색으로 바뀐다")

    c.날것(정의("최대 내적 탐색 (MIPS)",
              "질의 <i>q</i> 에 대해 &lt;<i>q</i>,<i>x</i>&gt; 가 최대인 <i>x</i> 를 "
              "찾는 문제. 추천 · 검색의 표준 꼴인데, <b>거리 기반 자료구조를 바로 "
              "못 쓴다</b> &mdash; 내적은 거리가 아니기 때문이다(삼각부등식이 없다)."))

    c.날것(정리(
        "MIPS 는 차원 하나를 더해 최근접 이웃 문제가 된다",
        """모든 후보의 길이가 <i>M</i> = max<sub><i>x</i></sub>&#8214;<i>x</i>&#8214; 이하라 하자.
        <div class="math"><i>x&#771;</i> = (<i>x</i>, &radic;(<i>M</i><sup>2</sup>&minus;&#8214;<i>x</i>&#8214;<sup>2</sup>)),
        &nbsp;&nbsp; <i>q&#771;</i> = (<i>q</i>, 0)</div>
        로 확장하면, <b>argmax<sub><i>x</i></sub>&lt;<i>q</i>,<i>x</i>&gt;
        = argmin<sub><i>x</i></sub>&#8214;<i>q&#771;</i>&minus;<i>x&#771;</i>&#8214;</b> 이다.
        즉 MIPS 가 유클리드 최근접 이웃 문제로 환원된다.""",
        [("&#8214;<i>x&#771;</i>&#8214;<sup>2</sup> = &#8214;<i>x</i>&#8214;<sup>2</sup> + (<i>M</i><sup>2</sup>&minus;&#8214;<i>x</i>&#8214;<sup>2</sup>) = <i>M</i><sup>2</sup>.",
          "더한 성분의 제곱이 정확히 모자란 만큼이다 &mdash; <b>모든 후보의 길이가 같아진다</b>. 이것이 이 변환의 전부다."),
         ("&#8214;<i>q&#771;</i>&minus;<i>x&#771;</i>&#8214;<sup>2</sup> = &#8214;<i>q&#771;</i>&#8214;<sup>2</sup> + &#8214;<i>x&#771;</i>&#8214;<sup>2</sup> &minus; 2&lt;<i>q&#771;</i>,<i>x&#771;</i>&gt;.",
          "제곱거리의 전개."),
         ("&lt;<i>q&#771;</i>,<i>x&#771;</i>&gt; = &lt;<i>q</i>,<i>x</i>&gt; + 0&middot;&radic;(&middot;) = &lt;<i>q</i>,<i>x</i>&gt;.",
          "<i>q&#771;</i> 의 마지막 성분이 0 이라 더한 차원이 내적에 기여하지 않는다."),
         ("그러므로 &#8214;<i>q&#771;</i>&minus;<i>x&#771;</i>&#8214;<sup>2</sup> = &#8214;<i>q</i>&#8214;<sup>2</sup> + <i>M</i><sup>2</sup> &minus; 2&lt;<i>q</i>,<i>x</i>&gt;.",
          "1 과 3 을 2 에 넣었다."),
         ("앞의 두 항은 <i>x</i> 에 안 딸린 상수다.",
          "&#8214;<i>q</i>&#8214; 은 질의에만, <i>M</i> 은 집합 전체에만 딸린다."),
         ("따라서 거리를 최소화하는 것과 내적을 최대화하는 것이 같다.",
          "상수 &minus; 2&middot;(내적) 을 최소화하는 것이 곧 내적을 최대화하는 것."),
         ],
        가정="<i>M</i> 을 미리 알아야 한다 &mdash; 색인을 지을 때 한 번 계산한다. 새 문서가 더 길면 <i>M</i> 이 바뀌어 <b>전체를 다시 변환</b>해야 한다."))

    c.날것(짚기("""<b>왜 이 정리를 알아야 하나.</b> 벡터 DB 가 &lsquo;내적 색인&rsquo; 을
    지원한다고 할 때, 속에서 하는 일이 대개 이 변환이다. 그리고 위 가정 &mdash;
    <i>M</i> 이 바뀌면 다시 지어야 한다 &mdash; 가 <b>운영에서 진짜 문제</b>가 된다.
    문서를 계속 넣는 시스템에서 어느 날 아주 긴 문서 하나가 들어오면 색인 전체의
    품질이 떨어진다. 그래서 실무에서는 <b>그냥 정규화해서 코사인으로 쓰는</b>
    경우가 많다(정리 16 을 알고 고르는 것이다)."""))

    # ------------------------------------------------------------------
    c.절("D1.3 차원의 저주 — 고차원에서 &lsquo;가깝다&rsquo; 가 뜻을 잃는다")

    c.날것(정의("거리 집중 (concentration of distances)",
              "차원이 커질수록 무작위 점들 사이의 거리가 <b>다 비슷해지는</b> 현상. "
              "최근접과 최원접의 비가 1 로 간다."))

    c.날것(정리(
        "독립 성분이면 최근접/최원접 비가 1 로 간다",
        """질의 <i>q</i> 와 후보들이 <i>d</i> 차원 등방 분포에서 독립으로 뽑힌다고 하자.
        <i>D</i><sub>max</sub>, <i>D</i><sub>min</sub> 을 <i>n</i> 개 후보까지의 최대·최소
        거리라 하면 <i>d</i> &rarr; &infin; 에서
        <div class="math"><i>D</i><sub>max</sub>/<i>D</i><sub>min</sub>
        &nbsp;&xrarr;<sup>P</sup>&nbsp; 1</div>
        이다. 즉 <b>&lsquo;가장 가까운 것&rsquo; 이 &lsquo;가장 먼 것&rsquo; 과 구별되지 않는다.</b>""",
        [("제곱거리 &#8214;<i>q</i>&minus;<i>x</i>&#8214;<sup>2</sup> = &Sigma;<sub><i>t</i>=1</sub><sup><i>d</i></sup>(<i>q</i><sub><i>t</i></sub>&minus;<i>x</i><sub><i>t</i></sub>)<sup>2</sup> 는 독립 항 <i>d</i> 개의 합이다.",
          "성분이 독립이라 가정했다."),
         ("따라서 평균은 <i>d</i>&mu;, 분산은 <i>d</i>&sigma;<sup>2</sup> 에 비례한다.",
          "독립 항의 합에서 평균과 분산이 각각 더해진다."),
         ("거리 자체의 상대 요동은 &radic;(<i>d</i>&sigma;<sup>2</sup>)/(<i>d</i>&mu;) = <i>O</i>(1/&radic;<i>d</i>) 다.",
          "표준편차를 평균으로 나눈 것 &mdash; 변동계수. <i>d</i> 가 커지면 0 으로 간다."),
         ("그러므로 모든 거리가 <i>d</i>&mu; 주위의 폭 <i>O</i>(&radic;<i>d</i>) 띠 안에 몰린다.",
          "2 와 3 &mdash; 평균은 <i>d</i> 에 비례해 커지는데 흩어짐은 &radic;<i>d</i> 로만 커진다."),
         ("<i>n</i> 이 <i>d</i> 에 비해 지수적으로 크지 않으면 최대와 최소도 그 띠 안이다.",
          "꼬리확률이 지수적으로 작아 <i>n</i> 개의 최댓값도 띠를 크게 못 벗어난다(극값 이론)."),
         ("비를 취하면 (<i>d</i>&mu;+<i>O</i>(&radic;<i>d</i>))/(<i>d</i>&mu;&minus;<i>O</i>(&radic;<i>d</i>)) &rarr; 1.",
          "분자·분모를 <i>d</i>&mu; 로 나누면 &plusmn;<i>O</i>(1/&radic;<i>d</i>) 가 0 으로 간다."),
         (f"대조: 실제로 표준정규 점 {수(1000)}개를 뽑아 재면 비가 "
          + " · ".join(f"<i>d</i>={d} 에서 {수(v, 3)}" for d, v in 비) + " 로 준다.",
          "빌드할 때 직접 뽑아 잰 값이다 &mdash; 극한이 아니라 실제 수로 확인한 것."),
         ],
        가정="<b>성분이 독립이고 등방</b>. 실제 임베딩은 <b>이 가정을 어긴다</b> &mdash; 그래서 고차원 임베딩 검색이 그나마 되는 것이다(다음 짚기)."))

    c.날것(짚기("""<b>&ldquo;차원의 저주가 있는데 왜 1536 차원 임베딩이 잘 되나&rdquo; 가
    제대로 된 질문이다.</b> 답: <b>정리 18 의 가정이 깨져서</b>다. 학습된 임베딩은
    등방이 아니다 &mdash; 실제 데이터는 훨씬 낮은 <b>내재 차원</b>의 굽은 면 위에
    몰려 있다. 그래서 겉 차원 <i>d</i>=1536 이어도 유효한 자유도는 수십 수준이다.
    <b>거꾸로 말하면, 임베딩이 도메인과 안 맞아 데이터가 공간에 흩어지는 순간
    정리 18 이 되살아나고 검색이 무작위가 된다.</b> &lsquo;검색이 안 된다&rsquo; 의 가장
    깊은 원인이 이것이다."""))

    # ------------------------------------------------------------------
    c.절("D1.4 차원을 줄여도 거리가 보존된다 — 존슨-린덴슈트라우스")

    c.날것(정의("무작위 사영 (random projection)",
              "<i>d</i>&times;<i>k</i> 무작위 행렬을 곱해 <i>k</i> 차원으로 내리는 것. "
              "<b>데이터를 보지 않고</b> 차원을 줄인다 &mdash; PCA 와 다른 점이 이것이다."))

    c.날것(보조정리(
        "무작위 사영은 한 벡터의 길이를 평균적으로 보존한다",
        """<i>R</i> 의 성분이 <i>N</i>(0, 1/<i>k</i>) 독립일 때, 임의의 고정 벡터
        <i>v</i> 에 대해 <b>E</b>[&#8214;<i>Rv</i>&#8214;<sup>2</sup>] = &#8214;<i>v</i>&#8214;<sup>2</sup>
        이고, &#8214;<i>Rv</i>&#8214;<sup>2</sup>/&#8214;<i>v</i>&#8214;<sup>2</sup> 는 자유도 <i>k</i> 의
        &chi;<sup>2</sup>/<i>k</i> 를 따른다.""",
        [("(<i>Rv</i>)<sub><i>j</i></sub> = &Sigma;<sub><i>t</i></sub><i>R</i><sub><i>jt</i></sub><i>v</i><sub><i>t</i></sub> 는 정규들의 선형결합이므로 정규다.",
          "독립 정규의 선형결합은 정규다."),
         ("그 분산은 &Sigma;<sub><i>t</i></sub><i>v</i><sub><i>t</i></sub><sup>2</sup>&middot;(1/<i>k</i>) = &#8214;<i>v</i>&#8214;<sup>2</sup>/<i>k</i>.",
          "독립이라 분산이 더해지고, 각 <i>R</i><sub><i>jt</i></sub> 의 분산이 1/<i>k</i>."),
         ("서로 다른 <i>j</i> 끼리는 독립이다(행이 독립이므로).",
          "행렬의 성분을 전부 독립으로 뽑았다."),
         ("그러므로 &#8214;<i>Rv</i>&#8214;<sup>2</sup> = &Sigma;<sub><i>j</i>=1</sub><sup><i>k</i></sup>(정규)<sup>2</sup> 이고, 표준화하면 &chi;<sup>2</sup><sub><i>k</i></sub>/<i>k</i> &middot; &#8214;<i>v</i>&#8214;<sup>2</sup>.",
          "독립 표준정규 제곱의 합이 카이제곱의 정의다."),
         ("<b>E</b>[&chi;<sup>2</sup><sub><i>k</i></sub>] = <i>k</i> 이므로 기댓값이 &#8214;<i>v</i>&#8214;<sup>2</sup>.",
          "카이제곱의 평균은 자유도다."),
         ],
        가정="<i>R</i> 의 성분이 독립 정규. 베르누이(&plusmn;1/&radic;<i>k</i>)로 바꿔도 같은 결론이 난다(Achlioptas)."))

    c.날것(정리(
        "존슨-린덴슈트라우스 — 차원은 점의 개수에만 딸린다",
        """점 <i>n</i> 개와 &epsilon; &isin; (0,&frac12;) 에 대해
        <i>k</i> = <i>O</i>(ln <i>n</i> / &epsilon;<sup>2</sup>) 이면, 무작위 사영
        <i>R</i>: &#8477;<sup><i>d</i></sup>&rarr;&#8477;<sup><i>k</i></sup> 가 높은 확률로
        <b>모든 쌍</b>에 대해
        <div class="math">(1&minus;&epsilon;)&#8214;<i>x</i><sub><i>i</i></sub>&minus;<i>x</i><sub><i>j</i></sub>&#8214;
        &le; &#8214;<i>Rx</i><sub><i>i</i></sub>&minus;<i>Rx</i><sub><i>j</i></sub>&#8214;
        &le; (1+&epsilon;)&#8214;<i>x</i><sub><i>i</i></sub>&minus;<i>x</i><sub><i>j</i></sub>&#8214;</div>
        를 만족한다. <b>놀라운 점: <i>k</i> 가 원래 차원 <i>d</i> 와 무관하다.</b>""",
        [("보조정리 19 에 의해 한 쌍의 차 벡터 <i>v</i>=<i>x</i><sub><i>i</i></sub>&minus;<i>x</i><sub><i>j</i></sub> 에 대해 &#8214;<i>Rv</i>&#8214;<sup>2</sup>/&#8214;<i>v</i>&#8214;<sup>2</sup> ~ &chi;<sup>2</sup><sub><i>k</i></sub>/<i>k</i>.",
          "사영이 선형이라 차의 상이 상의 차다 &mdash; <i>R</i>(<i>x</i><sub><i>i</i></sub>&minus;<i>x</i><sub><i>j</i></sub>) = <i>Rx</i><sub><i>i</i></sub>&minus;<i>Rx</i><sub><i>j</i></sub>."),
         ("&chi;<sup>2</sup><sub><i>k</i></sub>/<i>k</i> 가 1 에서 &epsilon; 이상 벗어날 확률은 2exp(&minus;<i>k</i>(&epsilon;<sup>2</sup>&minus;&epsilon;<sup>3</sup>)/4) 이하다.",
          "카이제곱의 표준 집중 부등식(감마 분포의 체르노프 한계)."),
         ("쌍은 <i>n</i>(<i>n</i>&minus;1)/2 &lt; <i>n</i><sup>2</sup> 개다.",
          "서로 다른 두 점을 고르는 경우의 수."),
         ("합집합 한계로 더하면 실패확률 &le; 2<i>n</i><sup>2</sup>exp(&minus;<i>k</i>(&epsilon;<sup>2</sup>&minus;&epsilon;<sup>3</sup>)/4).",
          "어느 한 쌍이라도 벗어날 확률은 각 확률의 합 이하다."),
         ("이 값이 1 보다 작으려면 <i>k</i> &gt; 8 ln <i>n</i>/(&epsilon;<sup>2</sup>&minus;&epsilon;<sup>3</sup>) 이면 충분하다.",
          "양변에 로그를 취해 <i>k</i> 에 대해 푼 것. &epsilon;&lt;&frac12; 이면 &epsilon;<sup>2</sup>&minus;&epsilon;<sup>3</sup> &gt; &epsilon;<sup>2</sup>/2."),
         ("실패확률이 1 보다 작으므로 조건을 만족하는 <i>R</i> 이 <b>존재한다</b>. 게다가 무작위로 뽑으면 높은 확률로 된다.",
          "확률론적 방법(probabilistic method) &mdash; 존재를 보이는 데 구성이 필요 없다."),
         ("<i>d</i> 는 어디에도 안 나왔다.",
          "2 의 집중 부등식이 <i>k</i> 에만 딸리기 때문이다 &mdash; 이것이 정리의 핵심."),
         (f"대조: <i>d</i>=2000 의 점 300 개를 <i>k</i>={수(k1)} 로 실제 사영해 재니 "
          f"최대 왜곡이 {수(왜곡, 3)} (&epsilon;=0.2 안).",
          "빌드할 때 무작위 행렬을 만들어 직접 곱해 본 값이다."),
         ],
        가정="&epsilon; &lt; &frac12;. 상수 8 은 느슨한 편이라 실제로는 더 작은 <i>k</i> 로도 된다."))

    c.날것(표("JL 이 요구하는 목표 차원. <b>점이 백 배 늘어도 차원은 두 배가 안 된다.</b>",
            ["점 개수 <i>n</i>", "&epsilon;=0.1", "&epsilon;=0.2", "&epsilon;=0.5"],
            [[f"{수(n)}", f"{수(jl차원(n, 0.1))}", f"{수(jl차원(n, 0.2))}",
              f"{수(jl차원(n, 0.5))}"]
             for n in (1_000, 100_000, 10_000_000)]))

    c.날것(예제(
        "1536 차원을 128 차원으로 줄여도 되나",
        f"""문서 {수(1000000)} 개. 저장 비용을 12 배 줄이고 싶다.
        허용 왜곡은 &epsilon;=0.2.""",
        f"""JL 은 <i>k</i> &ge; {수(jl차원(1000000, 0.2))} 를 요구한다. 128 은 그보다 작다.
        <b>그러나 JL 은 충분조건이지 필요조건이 아니다</b> &mdash; 실제 임베딩은
        등방이 아니라 내재 차원이 훨씬 낮아, 128 로 줄여도 상위 <i>k</i> 재현율이
        거의 안 떨어지는 경우가 많다.""",
        f"""<b>JL 이 보장하지는 않는다</b>({수(jl차원(1000000, 0.2))} 필요).
        <b>그러니 재라.</b> 줄이기 전후의 recall@10 을 같은 질의 집합으로 재서
        떨어진 만큼을 적는다 &mdash; 보장이 없는 자리는 측정이 대신한다.""",
        """<b>&ldquo;JL 이 안 된다고 했으니 안 된다&rdquo; 도, &ldquo;남들이 하니까 된다&rdquo; 도
        둘 다 틀렸다.</b> JL 은 <b>최악의 데이터</b>에 대한 보장이고, 실제 데이터는
        최악이 아니다. 보장이 없는 곳에서 결론을 내는 유일한 방법은 재는 것이다
        &mdash; 이 저장소의 규율 그대로.""",
        덧="""그리고 무작위 사영보다 <b>학습된 축소</b>(Matryoshka 임베딩처럼 앞쪽
        차원에 정보를 몰아 학습한 것)가 훨씬 낫다. JL 은 <b>데이터를 안 보고도</b>
        이만큼 된다는 하한선이지 최선이 아니다."""))

    c.날것(언어(
        "코사인 검색 한 판을 네 말로",
        [("Python + numpy — 백만 개까지는 이걸로 충분하다",
          """import numpy as np

M = np.load("emb.npy")                 # (N, d) float32
M /= np.linalg.norm(M, axis=1, keepdims=True) + 1e-12   # 한 번만 정규화

def search(q: np.ndarray, k: int = 10):
    q = q / (np.linalg.norm(q) + 1e-12)
    s = M @ q                          # 정규화했으므로 내적 = 코사인
    idx = np.argpartition(-s, k)[:k]   # 전체 정렬 안 한다: O(N)
    return idx[np.argsort(-s[idx])]""",
          "<code>argpartition</code> 이 <code>argsort</code> 보다 빠른 이유는 "
          "<b>상위 k 만 제자리로 보내고 나머지는 안 정렬</b>하기 때문이다 &mdash; "
          "<i>O</i>(<i>N</i>) 대 <i>O</i>(<i>N</i> log <i>N</i>). "
          "<code>+1e-12</code> 는 영벡터에서 0 나누기를 막는다"),
         ("SQL (pgvector) — 데이터베이스가 이미 있으면 가장 싼 길",
          """-- 코사인 거리 연산자는 <=> , 내적은 <#> , L2 는 <->
CREATE INDEX ON docs USING hnsw (emb vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

SELECT id, body, 1 - (emb <=> $1) AS score
FROM   docs
WHERE  tenant_id = $2              -- 격리는 여기서 (A19)
ORDER  BY emb <=> $1
LIMIT  10;""",
          "<b>연산자를 색인과 맞춰야 한다</b> &mdash; <code>vector_cosine_ops</code> 로 "
          "지은 색인에 <code>&lt;#&gt;</code>(내적)로 질의하면 <b>색인을 안 타고</b> "
          "전수 검색이 된다. 느려질 뿐 결과는 나오므로 아무도 안 알아챈다"),
         ("TypeScript — 브라우저/엣지에서 작은 색인",
          """export function cosineTopK(
  mat: Float32Array, n: number, d: number, q: Float32Array, k: number,
): number[] {
  const scores = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    let s = 0;
    for (let t = 0; t < d; t++) s += mat[i * d + t] * q[t];
    scores[i] = s;                                    // 둘 다 정규화 가정
  }
  return Array.from(scores.keys())
    .sort((a, b) => scores[b] - scores[a]).slice(0, k);
}""",
          "<code>Float32Array</code> 를 쓰는 이유는 <b>일반 배열이 박싱된 double</b> "
          "이라 8 배 무겁고 캐시를 다 깨먹기 때문이다. "
          "<code>mat[i*d+t]</code> 처럼 1차원으로 편 것도 같은 이유"),
         ("Rust — 색인을 직접 짤 때",
          """pub fn cosine_top_k(mat: &[f32], d: usize, q: &[f32], k: usize)
    -> Vec<(usize, f32)> {
    assert_eq!(q.len(), d);
    let mut best: Vec<(usize, f32)> = mat
        .chunks_exact(d)                    // 경계가 안 맞으면 남는 조각을 버린다
        .enumerate()
        .map(|(i, row)| (i, row.iter().zip(q).map(|(a, b)| a * b).sum()))
        .collect();
    best.sort_unstable_by(|a, b| b.1.total_cmp(&a.1));
    best.truncate(k);
    best
}""",
          "<code>chunks_exact</code> 는 <b>길이가 안 맞는 꼬리를 아예 안 준다</b> &mdash; "
          "행 경계가 어긋나는 사고를 타입이 아니라 API 가 막는 자리. "
          "<code>sort_unstable_by</code> 는 안정성을 포기해 더 빠른 정렬")],
        짚기="""<b>네 칸 중 실무에서 가장 위험한 것은 두 번째다.</b> SQL 은 <b>틀려도
        답이 나온다</b> &mdash; 색인을 안 타면 느릴 뿐. 나머지 셋은 틀리면 결과가
        이상해져서 금방 안다. <b>조용히 느려지는 것이 조용히 틀리는 것 다음으로
        나쁘다</b>(그리고 둘 다 검사 없이는 안 보인다)."""))

    c.날것(유도("이 장을 한 문단으로", [
        ("내적과 코사인은 다른 검색이다",
         "정리 16 &mdash; 길이가 다르면 순위가 뒤집힌다"),
        ("MIPS 는 차원 하나를 더해 최근접 이웃이 된다",
         "정리 17 &mdash; 모든 후보의 길이를 같게 만드는 것이 전부"),
        ("고차원에서 거리는 다 비슷해진다",
         "정리 18 &mdash; 상대 요동이 <i>O</i>(1/&radic;<i>d</i>)"),
        ("그런데 임베딩은 등방이 아니라서 살아남는다",
         "실제 데이터의 내재 차원이 훨씬 낮다 &mdash; 도메인이 어긋나면 이 구원이 사라진다"),
        ("차원을 줄여도 모든 쌍의 거리가 보존될 수 있다",
         "정리 20 &mdash; 필요한 차원이 ln <i>n</i>/&epsilon;<sup>2</sup>, 원래 차원과 무관"),
        ("다만 그것은 최악에 대한 보장이라 실무에서는 더 줄여도 된다",
         "보장이 없는 자리에서는 recall 을 재서 결정한다"),
    ]))

    c.날것(논문출처([
        ["Johnson &amp; Lindenstrauss (1984)", "Contemp. Math. 26", "<b>조각</b>",
         "정리 20 &mdash; 증명은 이 책이 카이제곱 집중으로 직접 했다"],
        ["Shrivastava &amp; Li, <i>Asymmetric LSH for MIPS</i>", "NIPS 2014",
         "<b>조각</b>", "정리 17 의 변환 &mdash; 증명은 직접 했다"],
        ["Beyer 외, <i>When Is Nearest Neighbor Meaningful?</i>", "ICDT 1999",
         "<b>조각</b>", "정리 18 &mdash; 증명은 직접 했다"],
    ]))

    return c.완성()
