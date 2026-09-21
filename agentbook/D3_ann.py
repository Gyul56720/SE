# -*- coding: utf-8 -*-
"""D3 -- 근사 최근접 이웃. 정확함을 얼마나 팔아 속도를 사는가."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "edu"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 정의, 유도, 예제, 짚기, 사고, 수  # noqa: E402
from bookA import 정리, 보조정리, 따름정리, 논문출처, 언어, 직무  # noqa: E402


def ivf재현율(N=4000, d=48, 군집=64, 탐색군집=(1, 2, 4, 8, 16), k=10, 질의수=60,
           씨=20260921):
    """IVF 를 **실제로 지어** 재현율을 잰다. k-평균 몇 바퀴 + 목록 탐색.

    돌려주는 것: [(탐색한 군집 수, recall@k, 본 후보 비율), ...]
    """
    r = random.Random(씨)
    # 덩어리진 데이터 (실제 임베딩처럼 -- 균등이면 IVF 가 원래 안 듣는다)
    중심수 = 24
    중심 = [[r.gauss(0, 1) for _ in range(d)] for _ in range(중심수)]
    X = []
    for _ in range(N):
        c = 중심[r.randrange(중심수)]
        X.append([v + r.gauss(0, 0.35) for v in c])

    # k-평균 (5 바퀴)
    C = [X[r.randrange(N)][:] for _ in range(군집)]
    소속 = [0] * N
    for _ in range(5):
        for i, x in enumerate(X):
            소속[i] = min(range(군집), key=lambda j: sum(
                (a - b) ** 2 for a, b in zip(x, C[j])))
        합 = [[0.0] * d for _ in range(군집)]
        셈 = [0] * 군집
        for i, x in enumerate(X):
            셈[소속[i]] += 1
            for t in range(d):
                합[소속[i]][t] += x[t]
        for j in range(군집):
            if 셈[j]:
                C[j] = [v / 셈[j] for v in 합[j]]
    목록 = [[] for _ in range(군집)]
    for i in range(N):
        목록[소속[i]].append(i)

    결과 = []
    질의 = [[v + r.gauss(0, 0.35) for v in 중심[r.randrange(중심수)]]
          for _ in range(질의수)]
    참답 = []
    for q in 질의:
        d2 = sorted(range(N), key=lambda i: sum(
            (a - b) ** 2 for a, b in zip(q, X[i])))
        참답.append(set(d2[:k]))
    for nprobe in 탐색군집:
        맞 = 0
        본것 = 0
        for qi, q in enumerate(질의):
            가까운군집 = sorted(range(군집), key=lambda j: sum(
                (a - b) ** 2 for a, b in zip(q, C[j])))[:nprobe]
            후보 = [i for j in 가까운군집 for i in 목록[j]]
            본것 += len(후보)
            상위 = sorted(후보, key=lambda i: sum(
                (a - b) ** 2 for a, b in zip(q, X[i])))[:k]
            맞 += len(참답[qi] & set(상위))
        결과.append((nprobe, 맞 / (질의수 * k), 본것 / (질의수 * N)))
    return 결과


def 층기댓값(N, mL=1 / math.log(2.0)):
    """HNSW 의 최대 층 기댓값 ~ mL * ln N."""
    return mL * math.log(N)


def pq바이트(d, m, bits=8, 원본바이트=4):
    """곱 양자화의 압축비."""
    원본 = d * 원본바이트
    압축 = m * bits / 8
    return 원본, 압축, 원본 / 압축


def ch_ann():
    표IVF = ivf재현율()
    o, p, 비 = pq바이트(1536, 96)

    c = 장(
        "D3", "근사 최근접 이웃 — 정확함을 팔아 속도를 산다",
        "백만 개를 전부 훑으면 답은 정확하지만 느리다. 벡터 DB 가 하는 일은 "
        "<b>재현율을 조금 팔아 지연을 자릿수로 줄이는 것</b>이고, 그 거래를 "
        "<b>눈금으로</b> 다루는 것이 이 장이다.",
        쓰는것=["임베딩", "최대내적탐색", "MIPS환원", "거리집중", "재현율", "정밀도",
             "코사인유사도", "차원의저주", "무작위사영"],
        내놓는것=["근사최근접이웃", "재현율지연교환", "IVF", "탐색군집수", "곱양자화",
              "HNSW", "항해가능작은세상", "계층그래프", "필터링검색", "색인재구축"],
        특허="""<b>필터와 색인을 같이 태우는 법</b>(메타데이터 조건이 붙은 ANN)과
        <b>갱신이 잦은 색인</b>이 발명 자리다. 필터링은 지금도 제대로 푼 제품이
        드물다 &mdash; 아래 D3.4.""")

    c.날것(직무(["NAV.RAG", "NAV.최적화", "NAV.서빙"]))

    c.날것(정의("근사 최근접 이웃 (ANN)",
              "최근접 이웃을 <b>대개</b> 찾는 자료구조. &lsquo;대개&rsquo; 를 재는 자가 "
              "재현율이다 &mdash; 참 상위 <i>k</i> 중 몇 개를 실제로 돌려줬나."))
    c.날것(정의("재현율-지연 교환 (recall&ndash;latency tradeoff)",
              "ANN 의 모든 손잡이(탐색 군집 수 · <code>ef</code> · 양자화 비트)는 "
              "결국 이 한 곡선 위의 점을 고르는 것이다. <b>한 점만 보고 제품을 "
              "비교하면 안 된다 &mdash; 곡선을 봐야 한다.</b>"))

    # ------------------------------------------------------------------
    c.절("D3.1 왜 정확한 색인이 고차원에서 죽는가")

    c.날것(정리(
        "거리가 집중되면 삼각부등식 가지치기가 듣지 않는다",
        """거리 기반 색인(볼 트리 · M-트리 등)은 &lsquo;군집 <i>c</i> 의 중심까지 거리
        <i>D</i> 와 반지름 <i>R</i> 에 대해 <i>D</i> &minus; <i>R</i> &gt; &tau;
        이면 그 군집을 통째로 건너뛴다&rsquo; 로 가지를 친다. 그런데 D1 의 정리 18 처럼
        모든 거리가 [(1&minus;&delta;)&mu;, (1+&delta;)&mu;] 에 몰리면,
        <b>&tau; &ge; (1&minus;&delta;)&mu; 이므로 <i>R</i> &gt; 2&delta;&mu; 인 군집은
        하나도 못 건너뛴다.</b> 고차원에서 &delta; &rarr; 0 이면 가지치기가 사실상
        사라지고 전수 탐색이 된다.""",
        [("가지치기 조건은 <i>D</i> &minus; <i>R</i> &gt; &tau; 다(&tau; 는 지금까지 찾은 <i>k</i> 번째 거리).",
          "삼각부등식: 군집 안 어느 점까지의 거리도 <i>D</i>&minus;<i>R</i> 이상이다."),
         ("&tau; 는 어떤 실제 점까지의 거리이므로 &tau; &ge; (1&minus;&delta;)&mu;.",
          "모든 거리가 그 구간 안에 있다는 가정."),
         ("<i>D</i> &le; (1+&delta;)&mu; 도 같은 이유로 성립한다.",
          "중심까지의 거리도 그 구간 안이다."),
         ("그러므로 <i>D</i> &minus; <i>R</i> &gt; &tau; 가 되려면 (1+&delta;)&mu; &minus; <i>R</i> &gt; (1&minus;&delta;)&mu;, 즉 <i>R</i> &lt; 2&delta;&mu;.",
          "2 와 3 을 1 에 넣어 <i>R</i> 에 대해 풀었다."),
         ("&delta; = <i>O</i>(1/&radic;<i>d</i>) 이므로 <i>d</i> 가 크면 <i>R</i> 이 아주 작은 군집만 잘린다.",
          "D1 정리 18 의 3 번 걸음 &mdash; 상대 요동이 1/&radic;<i>d</i> 로 준다."),
         ("그런데 군집의 반지름이 그만큼 작으려면 군집 수가 지수적으로 많아야 한다.",
          "공간을 반지름 2&delta;&mu; 짜리 공으로 덮으려면 (&mu;/&delta;&mu;)<sup><i>d</i></sup> 개가 필요하다 &mdash; 덮개 수 논증."),
         ("따라서 시간이나 공간 중 하나가 지수적으로 커진다 &mdash; 정확한 고차원 최근접 이웃의 알려진 벽이다.",
          "5 와 6 &mdash; 잘 자르려면 군집이 많아야 하고, 군집이 적으면 안 잘린다."),
         ],
        가정="등방 가정 아래의 &delta; 다. 실제 임베딩은 덜 집중돼서 벽이 덜 가파르다 &mdash; 그래서 ANN 이 실제로 듣는다."))

    c.날것(짚기("""<b>이 정리가 벡터 DB 의 존재 이유다.</b> &ldquo;정확히 찾되 빠르게&rdquo; 가
    고차원에서 불가능에 가깝기 때문에, 모든 제품이 <b>정확함을 조금 판다</b>.
    그래서 벡터 DB 를 고를 때 물어야 할 첫 질문은 &ldquo;빠른가&rdquo; 가 아니라
    <b>&ldquo;재현율 95&nbsp;% 에서 얼마나 빠른가&rdquo;</b> 다."""))

    # ------------------------------------------------------------------
    c.절("D3.2 IVF — 나누고 몇 칸만 본다")

    c.날것(정의("IVF (inverted file index)",
              "벡터를 <i>k</i>-평균으로 군집 <i>n</i><sub>list</sub> 개로 나누고, "
              "질의 때 가까운 군집 <i>n</i><sub>probe</sub> 개만 훑는 것. "
              "역색인의 &lsquo;낱말&rsquo; 자리에 &lsquo;군집&rsquo; 이 들어간 꼴이라 이름이 그렇다."))

    c.글(f"""아래 표는 <b>빌드할 때 실제로 IVF 를 지어 잰 것</b>이다 &mdash;
    덩어리진 {수(4000)} 점 · {수(48)} 차원 · 군집 {수(64)} 개 · 질의 {수(60)} 개,
    참 답은 전수 탐색으로 구했다.""")

    c.날것(표("IVF 의 재현율-비용 곡선. <b>곡선이지 한 점이 아니다.</b>",
            ["탐색 군집 <i>n</i><sub>probe</sub>", "recall@10", "본 후보 비율",
             "한마디"],
            [[f"{n}", f"{수(r, 4)}", f"{수(100*f, 3)}&nbsp;%",
              ("거의 안 보고 절반 이상 맞힌다" if n == 1 else
               "<b>여기쯤이 실무의 동작점</b>" if r >= 0.9 and n <= 8 else
               "전수에 가까워진다" if f > 0.2 else "올라가는 중")]
             for n, r, f in 표IVF]))

    c.날것(짚기(f"""<b>표의 모양을 보라.</b> 후보의 {수(100*표IVF[2][2], 3)}&nbsp;% 만
    보고 재현율 {수(표IVF[2][1], 4)} 를 얻는다. 이것이 ANN 이 파는 물건이고,
    <b>데이터가 덩어리져 있을 때만</b> 이 장사가 된다 &mdash; 균등하게 흩어진
    데이터에서는 IVF 가 무작위 표본과 다를 바 없다. 그리고 실제 임베딩은
    덩어리져 있다(D1.3 의 내재 차원)."""))

    c.날것(정의("곱 양자화 (product quantization, PQ)",
              "<i>d</i> 차원을 <i>m</i> 토막으로 쪼개고 토막마다 코드북(보통 256개)을 "
              "두어 <b>바이트 <i>m</i> 개</b>로 벡터 하나를 표현하는 것. 거리 계산이 "
              "표 조회 <i>m</i> 번으로 바뀐다."))

    c.날것(보조정리(
        "곱 양자화의 오차는 토막별 오차의 합이다",
        """<i>x</i> 를 <i>m</i> 개 토막 <i>x</i><sup>(1)</sup>&hellip;<i>x</i><sup>(<i>m</i>)</sup>
        으로 자르고 각각 양자화해 <i>q</i>(<i>x</i>) 를 만들면
        <b>E</b>&#8214;<i>x</i>&minus;<i>q</i>(<i>x</i>)&#8214;<sup>2</sup>
        = &Sigma;<sub><i>j</i></sub><b>E</b>&#8214;<i>x</i><sup>(<i>j</i>)</sup>&minus;
        <i>q</i><sub><i>j</i></sub>(<i>x</i><sup>(<i>j</i>)</sup>)&#8214;<sup>2</sup>
        이다. 따라서 토막 수 <i>m</i> 을 늘리면 오차가 준다(대신 바이트가 는다).""",
        [("제곱 노름은 좌표별 제곱의 합이고, 토막은 좌표를 겹치지 않게 나눈 것이다.",
          "&#8214;<i>v</i>&#8214;<sup>2</sup> = &Sigma;<sub><i>t</i></sub><i>v</i><sub><i>t</i></sub><sup>2</sup> 를 토막 경계로 묶었다."),
         ("각 토막의 양자화는 그 토막 좌표에만 작용한다.",
          "PQ 의 정의 &mdash; 토막마다 독립적인 코드북."),
         ("그러므로 차 벡터의 제곱 노름이 토막별 차의 제곱 노름의 합이다.",
          "1 과 2."),
         ("기댓값은 선형이므로 합이 그대로 나온다.",
          "<b>E</b>[&Sigma;] = &Sigma;<b>E</b>."),
         (f"대조: <i>d</i>={수(1536)} float32 는 {수(o)}&nbsp;B 인데 "
          f"<i>m</i>={수(96)} 바이트 PQ 는 {수(p)}&nbsp;B &mdash; {수(비, 3)} 배 압축.",
          "빌드할 때 계산한 값이다."),
         ],
        가정="토막 경계가 고정돼 있다. OPQ 는 먼저 회전을 학습해 토막 간 상관을 없애 오차를 더 줄인다."))

    # ------------------------------------------------------------------
    c.절("D3.3 HNSW — 그래프를 걸어 내려간다")

    c.날것(정의("항해 가능한 작은 세상 (navigable small world)",
              "대부분 가까운 이웃과 이어져 있지만 <b>멀리 가는 간선이 몇 개</b> 섞인 "
              "그래프. 탐욕적으로 &lsquo;목표에 더 가까운 이웃&rsquo; 으로만 걸어도 짧은 "
              "걸음에 도착한다."))
    c.날것(정의("HNSW (hierarchical navigable small world)",
              "그런 그래프를 <b>층으로</b> 쌓은 것. 위층은 성기고 멀리 뛰며, "
              "아래층은 조밀하다. 위에서 대충 찾아 내려오고 아래에서 다듬는다."))

    c.날것(정리(
        "HNSW 의 층 수는 log <i>N</i> 에 비례한다",
        """점마다 층을 <i>&#8467;</i> = &lfloor;&minus;ln(<i>u</i>)&middot;<i>m</i><sub>L</sub>&rfloor;
        (<i>u</i> ~ Uniform(0,1)) 로 뽑으면, <i>N</i> 개 점의 <b>최대 층</b>의 기댓값이
        <i>m</i><sub>L</sub> ln <i>N</i> + <i>O</i>(1) 이다.
        <i>m</i><sub>L</sub> = 1/ln 2 이면 대략 log<sub>2</sub> <i>N</i> 이다.""",
        [("P(<i>&#8467;</i> &ge; <i>k</i>) = P(&minus;ln <i>u</i> &ge; <i>k</i>/<i>m</i><sub>L</sub>) = P(<i>u</i> &le; e<sup>&minus;<i>k</i>/<i>m</i><sub>L</sub></sup>) = e<sup>&minus;<i>k</i>/<i>m</i><sub>L</sub></sup>.",
          "<i>u</i> 가 균등분포라 P(<i>u</i>&le;<i>a</i>) = <i>a</i>. 즉 <i>&#8467;</i> 는 기하분포 꼴이다."),
         ("<i>N</i> 개가 독립이면 P(최대 &lt; <i>k</i>) = (1&minus;e<sup>&minus;<i>k</i>/<i>m</i><sub>L</sub></sup>)<sup><i>N</i></sup>.",
          "모두가 <i>k</i> 미만일 확률 &mdash; 독립이라 곱."),
         ("<i>k</i> = <i>m</i><sub>L</sub>(ln <i>N</i> + <i>c</i>) 를 넣으면 e<sup>&minus;<i>k</i>/<i>m</i><sub>L</sub></sup> = e<sup>&minus;<i>c</i></sup>/<i>N</i>.",
          "지수를 정리한 것."),
         ("그러면 (1 &minus; e<sup>&minus;<i>c</i></sup>/<i>N</i>)<sup><i>N</i></sup> &rarr; exp(&minus;e<sup>&minus;<i>c</i></sup>).",
          "(1&minus;<i>a</i>/<i>N</i>)<sup><i>N</i></sup> &rarr; e<sup>&minus;<i>a</i></sup> 라는 표준 극한."),
         ("즉 최대 층은 <i>m</i><sub>L</sub> ln <i>N</i> 주위에 <b>상수 폭</b>으로 몰려 있다(굼벨 꼴).",
          "4 의 극한분포가 <i>c</i> 에만 딸리고 <i>N</i> 에 안 딸린다 &mdash; 위치만 ln <i>N</i> 을 따라 움직인다."),
         ("기댓값을 꼬리합으로 쓰면 <b>E</b>[최대] = &Sigma;<sub><i>k</i>&ge;1</sub>P(최대&ge;<i>k</i>) = <i>m</i><sub>L</sub> ln <i>N</i> + <i>O</i>(1).",
          "5 에서 분포가 위치만 옮겨 가는 꼴이므로 평균도 그렇다."),
         (f"대조: <i>N</i>={수(1000000)} 에서 {수(층기댓값(1000000), 3)} 층 "
          f"&mdash; {수(1000000)} 개를 스무 층 남짓으로 훑는다는 뜻이다.",
          "위 식에 수를 넣었다."),
         ],
        가정="층 배정이 독립. 탐색이 층마다 상수 걸음이라는 것은 <b>별도의 가정</b>이고, 그것이 성립하려면 각 층 그래프가 항해 가능해야 한다 &mdash; 이 부분은 경험적이다."))

    c.날것(짚기("""<b>정직하게 적자면, HNSW 의 전체 <i>O</i>(log <i>N</i>) 은 정리가 아니다.</b>
    층 수가 log <i>N</i> 인 것은 위에서 증명했지만, <b>층마다 걸음이 상수</b>라는 부분은
    그래프가 잘 만들어졌다는 경험적 가정이다. 그래서 HNSW 는 &lsquo;증명된 자료구조&rsquo; 가
    아니라 <b>아주 잘 듣는 경험적 자료구조</b>다 &mdash; 논문도 그렇게 말한다.
    이 구별을 흐리는 글이 많은데, <b>보장이 없는 곳에서는 재는 수밖에 없다</b>."""))

    c.날것(표("세 색인의 성격. <b>&lsquo;무엇이 최고&rsquo; 가 아니라 &lsquo;무엇이 어디에&rsquo; 다.</b>",
            ["", "메모리", "지음 비용", "갱신", "재현율 손잡이"],
            [["<b>전수</b>", "원본 그대로", "없다", "즉시", "없다 (항상 1.0)"],
             ["<b>IVF(+PQ)</b>", "<b>가장 작다</b> &mdash; PQ 로 수십 배 압축",
              "<i>k</i>-평균 한 번", "군집이 낡으면 다시 지어야",
              "<i>n</i><sub>probe</sub>"],
             ["<b>HNSW</b>", "가장 크다 &mdash; 간선을 다 들고 있다",
              "가장 비싸다", "<b>삽입이 싸다</b>", "<code>ef_search</code>"]]))

    # ------------------------------------------------------------------
    c.절("D3.4 필터 — 여기서 대부분의 제품이 샌다")

    c.날것(정의("필터링 검색 (filtered ANN)",
              "&lsquo;이 테넌트의, 지난 30일의, 공개된&rsquo; 문서 중에서 최근접을 찾는 것. "
              "에이전트 시스템에서는 <b>거의 모든 질의</b>가 이 꼴이다."))

    c.날것(표("필터를 거는 세 방법, 그리고 각각이 틀리는 자리.",
            ["방법", "어떻게", "무엇이 잘못되나"],
            [["<b>먼저 거르고</b> (pre-filter)",
              "조건에 맞는 것만 모아 전수 탐색",
              "조건을 만족하는 것이 많으면 <b>ANN 을 아예 못 쓴다</b>"],
             ["<b>나중에 거르고</b> (post-filter)",
              "ANN 으로 상위 <i>K</i> 를 받고 조건으로 거른다",
              "<b>조용히 빈손이 된다</b> &mdash; 상위 100개가 전부 다른 테넌트 것이면 "
              "0 개가 남는다. 코드는 정상, 결과만 없다"],
             ["<b>색인 안에서</b> (filter-aware)",
              "그래프 탐색 중에 조건을 보고 건너뛴다",
              "구현이 어렵다. 조건이 아주 선택적이면 <b>그래프가 끊겨</b> "
              "탐색이 도달 못 하는 구역이 생긴다"]]))

    c.날것(사고("""<b>&lsquo;나중에 거르기&rsquo; 가 왜 위험한지.</b> 이 저장소의 원칙
    &mdash; <i>검사하지 않은 초록불이 검사한 빨간불보다 나쁘다</i> &mdash; 가 정확히
    이 자리다. post-filter 는 <b>오류를 안 낸다.</b> 그냥 빈 결과를 준다. 그러면
    에이전트는 &ldquo;관련 문서가 없습니다&rdquo; 라고 <b>자신 있게</b> 답한다. 사용자는
    문서가 없는 줄 안다. <b>검색이 0건을 냈을 때 그것이 진짜 0건인지 필터가 먹은
    것인지를 런타임이 구별해서 말해야 한다</b> &mdash; 이것이 이 절의 실무적 결론이다."""))

    c.날것(개념(
        "재현율을 운영 지표로 들고 있는다",
        """<b>이론.</b> ANN 의 모든 손잡이는 재현율-지연 곡선 위의 점을 고른다.
        그런데 <b>재현율은 운영 중에 조용히 떨어진다</b> &mdash; 데이터가 늘어
        군집이 낡고(IVF), 삭제가 쌓여 그래프에 구멍이 나고(HNSW), 분포가 바뀐다.
        그러므로 재현율은 <b>지어 놓고 잊는 값이 아니라 감시하는 값</b>이다.""",
        어디에="""벡터 검색을 쓰는 모든 자리. 특히 문서가 계속 들어오는 시스템""",
        언제="""색인을 지은 직후 한 번, 그리고 <b>주기적으로</b>. 임베딩 모형을
        바꾸면 반드시""",
        어떻게="""(1) 고정된 질의 집합 <i>Q</i> 를 둔다 &rarr; (2) 주기적으로
        <b>전수 탐색으로 참 답</b>을 구한다(표본만 &mdash; 1000 질의면 충분) &rarr;
        (3) recall@<i>k</i> 를 재서 원장에 적는다 &rarr; (4) 임계 아래로 떨어지면
        색인을 다시 짓는다""",
        산업코드="""# 전수 탐색이 비싸서 못 한다는 말은 대개 틀리다 -- 표본이면 된다.
def recall_at_k(index, X, queries, k=10, sample=200):
    hits = 0
    for q in random.sample(queries, sample):
        truth = set(brute_force_topk(X, q, k))     # 느려도 200번뿐
        got   = set(index.search(q, k))
        hits += len(truth & got)
    return hits / (sample * k)

ledger.append({"ts": now(), "recall@10": recall_at_k(idx, X, Q),
               "n_docs": len(X), "index_built_at": idx.built_at})""",
        주의="""<b>재현율을 한 번도 안 재고 운영하는 시스템이 대부분이다.</b>
        그리고 그런 시스템에서 &ldquo;요즘 답이 별로다&rdquo; 가 나오면 모형을 의심하고
        프롬프트를 고친다 &mdash; <b>원인이 검색인데.</b> 이 저장소의 규율대로,
        <b>사소한 설명(검색이 낡았다)을 먼저 재서 죽여야</b> 한다."""))

    c.날것(언어(
        "같은 ANN 질의를 네 인터페이스로",
        [("Python — faiss (직접 들고 있을 때)",
          """import faiss, numpy as np

d, nlist = 768, 4096
quant = faiss.IndexFlatIP(d)                   # 군집 중심용
index = faiss.IndexIVFPQ(quant, d, nlist, m=96, nbits=8)
index.train(X)                                 # k-평균 -- 표본 10만이면 충분
index.add(X)
index.nprobe = 16                              # 재현율 손잡이 (D3.2 의 표)
D, I = index.search(q[None, :], 10)""",
          "<code>train()</code> 을 <b>안 부르면 add 가 터진다</b> &mdash; IVF 는 "
          "군집을 먼저 배워야 한다. 데이터가 바뀌어도 train 은 자동으로 다시 "
          "안 된다: <b>낡은 군집을 들고 운영하는 사고가 여기서 난다</b>"),
         ("TypeScript — Qdrant 클라이언트",
          """const res = await client.search("docs", {
  vector: qvec,
  limit: 10,
  filter: { must: [{ key: "tenant", match: { value: tenantId } }] },
  params: { hnsw_ef: 128 },        // 재현율 손잡이
  with_payload: true,
});
if (res.length === 0) {
  // **필터가 먹은 것인지 진짜 없는 것인지 구별한다** (D3.4)
  const anyDoc = await client.count("docs", { filter: tenantFilter });
  throw new EmptyResult(anyDoc.count === 0 ? "문서 없음" : "필터+ANN 이 먹음");
}""",
          "<code>filter</code> 를 서버에 넘기면 Qdrant 는 색인 안에서 건다 "
          "(filter-aware). <b>클라이언트에서 거르면 post-filter 가 되어 D3.4 의 "
          "두 번째 줄에 걸린다</b> &mdash; 같은 코드처럼 보이는데 완전히 다르다"),
         ("SQL — pgvector, 이미 postgres 가 있을 때",
          """SET LOCAL hnsw.ef_search = 100;      -- 세션마다 재현율 손잡이

SELECT id, 1 - (emb <=> $1) AS score
FROM   docs
WHERE  tenant_id = $2 AND created_at > now() - interval '30 days'
ORDER  BY emb <=> $1
LIMIT  10;""",
          "<b>플래너가 색인을 쓸지 안 쓸지를 혼자 정한다</b> &mdash; "
          "<code>WHERE</code> 가 선택적이면 순차 스캔이 더 싸다고 판단해 색인을 "
          "안 탄다. <code>EXPLAIN ANALYZE</code> 로 확인하지 않으면 모른다"),
         ("셸 — 색인 상태를 사람이 보는 한 줄",
          """# 재현율이 아니라 '언제 지었나' 부터 본다 (D3.4 의 사고)
psql -Atc "SELECT relname,
                  pg_size_pretty(pg_relation_size(oid)),
                  to_char(greatest(last_vacuum, last_autovacuum),
                          'YYYY-MM-DD') AS vac
           FROM pg_class c JOIN pg_stat_user_tables s ON s.relid = c.oid
           WHERE relname LIKE '%emb%'" | column -t""",
          "운영에서 가장 먼저 보는 것은 알고리즘이 아니라 <b>색인이 언제 것인가</b> 다")],
        짚기="""<b>네 칸의 공통 함정은 하나다 &mdash; 아무도 재현율을 안 잰다.</b>
        faiss 는 <code>nprobe</code>, Qdrant 는 <code>hnsw_ef</code>,
        pgvector 는 <code>ef_search</code> 를 손잡이로 주지만, <b>그 손잡이를 어디에
        둬야 하는지는 재 봐야만 안다</b>. 기본값은 누군가의 데이터에 맞춘 값이지
        당신 데이터에 맞춘 값이 아니다."""))

    c.날것(유도("이 장을 한 문단으로", [
        ("고차원에서 정확한 색인은 가지를 못 친다",
         "정리 24 &mdash; 거리 집중이 삼각부등식 가지치기를 무력화한다"),
        ("그래서 모든 벡터 DB 는 재현율을 판다",
         "질문은 &lsquo;빠른가&rsquo; 가 아니라 &lsquo;재현율 95&nbsp;% 에서 얼마나 빠른가&rsquo; 다"),
        ("IVF 는 나누고 몇 칸만 본다",
         "덩어리진 데이터에서만 듣는다 &mdash; 실측 표가 그 곡선이다"),
        ("PQ 는 토막마다 코드북을 둬 오차를 나눠 갖는다",
         "보조정리 25 &mdash; 오차가 토막별로 더해지므로 <i>m</i> 이 손잡이"),
        ("HNSW 의 층 수는 증명된 log <i>N</i> 이고, 걸음 수는 경험이다",
         "정리 26 &mdash; 그 구별을 흐리지 않는다"),
        ("필터가 붙으면 셋 다 어려워진다",
         "특히 post-filter 는 <b>조용히 빈손</b>이 된다"),
        ("그리고 재현율은 운영 중에 낡는다",
         "지표로 들고 있어야 한다 &mdash; 안 재면 모형을 탓하게 된다"),
    ]))

    c.날것(논문출처([
        ["Malkov &amp; Yashunin, <i>Efficient and robust ANN search using HNSW</i>",
         "arXiv:1603.09320", "<b>조각</b>", "정리 26 의 층 배정 규칙"],
        ["J&eacute;gou 외, <i>Product Quantization for NN Search</i>",
         "TPAMI 2011", "<b>조각</b>", "보조정리 25 &mdash; 증명은 직접 했다"],
        ["Beyer 외, <i>When Is Nearest Neighbor Meaningful?</i>", "ICDT 1999",
         "<b>조각</b>", "정리 24 의 바탕(D1 정리 18)"],
    ]))

    return c.완성()
