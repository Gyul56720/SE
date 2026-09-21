# -*- coding: utf-8 -*-
"""B3 -- 표본을 여러 개 뽑아 모은다. 언제 좋아지고 어디서 멈추는가."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "edu"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 정의, 유도, 예제, 짚기, 사고, 수  # noqa: E402
from bookA import 정리, 보조정리, 따름정리, 논문, 논문출처, 언어, 직무  # noqa: E402


def 다수결확률(p, n):
    """독립 투표자 n 명이 각각 p 로 맞을 때 다수가 맞을 확률. **정확히** 센다."""
    from math import comb
    return sum(comb(n, k) * p ** k * (1 - p) ** (n - k)
               for k in range(n // 2 + 1, n + 1))


def 회프딩한계(p, n):
    """P(다수가 틀린다) <= exp(-2n(p-1/2)^2) 의 오른쪽."""
    return math.exp(-2 * n * (p - 0.5) ** 2)


def 상관다수결(p, n, rho, 씨=20260921, 횟수=200_000):
    """오차가 상관된 투표. 잠재 공통 요인으로 상관을 만든 뒤 다수결을 센다.

    공통 요인 C ~ Bernoulli(rho) 가 1 이면 **모두 같은 답**(그 답이 맞을 확률 p),
    0 이면 각자 독립으로 p. 이때 쌍 상관계수가 정확히 rho 다.
    """
    r = random.Random(씨)
    맞음 = 0
    for _ in range(횟수):
        if r.random() < rho:
            표 = [1 if r.random() < p else 0] * n          # 한 몸처럼 움직인다
        else:
            표 = [1 if r.random() < p else 0 for _ in range(n)]
        if sum(표) > n / 2:
            맞음 += 1
    return 맞음 / 횟수


def bonKL(n):
    """KL(best-of-n || 바탕) 의 닫힌 꼴."""
    return math.log(n) - (n - 1) / n


def bonKL수치(n, 칸=400_000):
    """같은 값을 적분으로. 닫힌 꼴과 독립인 대조."""
    # u ~ 밀도 n u^{n-1} 위에서 log n + (n-1) E[log u]
    s = 0.0
    for i in range(칸):
        u = (i + 0.5) / 칸
        s += math.log(u) * n * u ** (n - 1) / 칸
    return math.log(n) + (n - 1) * s


def ch_ensemble():
    p0 = 0.6
    표1 = [(n, 다수결확률(p0, n), 회프딩한계(p0, n)) for n in (1, 5, 11, 31, 101)]
    상관 = [(rho, 상관다수결(p0, 31, rho)) for rho in (0.0, 0.2, 0.5, 0.8)]
    kl = [(n, bonKL(n), bonKL수치(n)) for n in (2, 8, 64)]

    c = 장(
        "B3", "표본을 모으는 법 — 다수결 · 최선의 n · 그리고 천장",
        "표본을 더 뽑으면 정확도가 오른다. <b>얼마나, 그리고 어디서 멈추는가</b>가 "
        "이 장이다. 답은 &lsquo;독립이면 지수적으로, 상관이 있으면 곧 멈춘다&rsquo; 이고, "
        "그 멈추는 자리를 증명한다.",
        쓰는것=["표집온도", "자기일관성", "다수결", "최선의n", "씨앗", "재현성",
             "비결정성예산", "토큰경제", "종료조건"],
        내놓는것=["콩도르세", "회프딩부등식", "오차상관", "유효표본수", "포화",
              "best-of-n", "보상모형", "굿하트", "KL예산", "검증자간극"],
        특허="""<b>언제 더 뽑기를 멈추는가</b>(적응적 표본 수)와 <b>무엇을 기준으로
        고르는가</b>(검증자 설계)가 이 주제의 발명 자리다. &lsquo;여러 번 뽑아 다수결&rsquo;
        자체는 1785년 콩도르세다.""")

    c.날것(직무(["NAV.지표", "NAV.안전", "KAK.선택이유", "KAK.분석"]))

    c.글("""A3 에서 자기일관성과 최선의 <i>n</i> 을 이름만 봤다. 여기서 그 둘을 수로
    가른다. 에이전트에서 이것이 돈 문제인 이유는 명확하다 &mdash; 표본 <i>n</i> 개는
    비용도 <i>n</i> 배다. <b>그 <i>n</i> 배가 무엇을 사 오는지</b> 모르면 그냥 돈을
    태우는 것이다.""")

    # ------------------------------------------------------------------
    c.절("B3.1 독립이면 기하급수적으로 좋아진다")

    c.날것(정의("콩도르세 배심 정리 (Condorcet jury theorem)",
              "각자 <i>p</i> &gt; &frac12; 의 확률로 옳게 판단하는 사람 <i>n</i> 명이 "
              "<b>독립적으로</b> 투표해 다수결을 하면, <i>n</i> 이 커질수록 다수가 옳을 "
              "확률이 1 로 간다. <i>p</i> &lt; &frac12; 면 반대로 0 으로 간다."))
    c.날것(정의("회프딩 부등식 (Hoeffding's inequality)",
              "[0,1] 에 갇힌 독립 확률변수들의 평균이 그 기댓값에서 <i>t</i> 이상 "
              "벗어날 확률은 exp(&minus;2<i>nt</i><sup>2</sup>) 이하라는 부등식. "
              "<b>분포를 몰라도 쓸 수 있다</b>는 것이 이 부등식의 값어치다."))

    c.날것(정리(
        "다수결이 틀릴 확률은 표본 수에 지수적으로 준다",
        """표본 <i>n</i> 개가 각각 확률 <i>p</i> &gt; &frac12; 로 정답을 내고 서로
        <b>독립</b>이라 하자. 오답은 서로 갈려 흩어진다고(즉 틀린 답들이 한 곳에
        뭉치지 않는다고) 가정하면, 다수결이 틀릴 확률은
        <div class="math">P(다수결 오답) &le; exp(&minus;2<i>n</i>(<i>p</i>&minus;&frac12;)<sup>2</sup>)</div>
        이다. 따라서 <i>n</i> &rarr; &infin; 에서 0 으로 <b>지수적으로</b> 간다.""",
        [("<i>X</i><sub><i>i</i></sub> = 1[<i>i</i> 번째 표본이 정답] 으로 두면 <i>X</i><sub><i>i</i></sub> 는 독립이고 <b>E</b>[<i>X</i><sub><i>i</i></sub>] = <i>p</i>, 값은 [0,1] 안에 있다.",
          "지시함수라 0 또는 1 이고, 표본이 독립이라 가정했다."),
         ("다수결이 틀리려면 정답표가 절반 이하여야 한다: <span style='white-space:nowrap'>(1/<i>n</i>)&Sigma;<i>X</i><sub><i>i</i></sub> &le; &frac12;</span>.",
          "정답이 과반이면 정답이 이긴다 &mdash; 오답들이 뭉치지 않는다는 가정이 여기 쓰인다."),
         ("이는 평균이 기댓값보다 <i>t</i> = <i>p</i> &minus; &frac12; &gt; 0 이상 작다는 뜻이다.",
          "<b>E</b>[평균] = <i>p</i> 이고 2 의 사건은 평균 &le; <i>p</i> &minus; <i>t</i>."),
         ("회프딩을 그 방향으로 쓰면 P &le; exp(&minus;2<i>nt</i><sup>2</sup>).",
          "회프딩 부등식의 한쪽 꼬리 형태. [0,1] 범위라 범위 폭이 1 이다."),
         ("<i>t</i> 를 되돌리면 exp(&minus;2<i>n</i>(<i>p</i>&minus;&frac12;)<sup>2</sup>).",
          "3 의 치환을 풀었다."),
         (f"대조: <i>p</i>={p0}, <i>n</i>=31 에서 정확한 이항 계산은 오답확률 "
          f"{수(1 - 표1[3][1], 3)}, 회프딩 한계는 {수(표1[3][2], 3)}.",
          "한계가 실제보다 느슨한 것이 정상이다 &mdash; 부등식은 상한이지 값이 아니다. 둘 다 빌드할 때 계산했다."),
         ],
        가정="<b>독립</b>. 그리고 오답이 한 곳에 뭉치지 않는다 &mdash; 둘 다 실제로는 자주 깨진다(B3.2)."))

    c.날것(표(f"<i>p</i> = {p0} 일 때 표본 수와 다수결 정확도. 가운데는 <b>정확한</b> 이항 계산이다.",
            ["표본 <i>n</i>", "다수결이 맞을 확률", "오답 확률", "회프딩 상한", "비용"],
            [[f"{n}", f"{수(v, 4)}", f"{수(1-v, 3)}", f"{수(h, 3)}", f"{n}&times;"]
             for n, v, h in 표1]))

    # ------------------------------------------------------------------
    c.절("B3.2 그리고 멈춘다 — 오차가 상관될 때")

    c.글("""위 정리의 힘은 전부 <b>독립</b>이라는 한 낱말에서 나온다. 같은 모형에 같은
    프롬프트를 주고 온도만 올려 <i>n</i> 번 뽑은 것들은 <b>독립이 아니다.</b> 모형이
    가진 편향 &mdash; 잘못 외운 사실, 프롬프트의 함정, 토큰화의 버릇 &mdash; 은
    <i>n</i> 개 표본 전부에 똑같이 들어 있다.""")

    c.날것(정의("오차 상관 (error correlation)",
              "표본들의 오답이 같은 방향으로 쏠리는 정도. 쌍 상관계수 &rho; 로 잰다. "
              "&rho;=0 이면 독립, &rho;=1 이면 <i>n</i> 개가 사실상 한 개다."))
    c.날것(정의("유효 표본 수 (effective sample size)",
              "상관이 있는 <i>n</i> 개가 <b>독립 표본 몇 개만큼의 값어치</b>가 있는가. "
              "아래 정리가 그 수를 준다."))

    c.날것(정리(
        "상관이 있으면 표본을 아무리 늘려도 불확실성이 0 으로 안 간다",
        """각 표본의 정답 지시변수 <i>X</i><sub><i>i</i></sub> 의 분산이 &sigma;<sup>2</sup> 이고,
        서로 다른 두 표본의 상관계수가 모두 &rho; &gt; 0 이라 하자. 평균의 분산은
        <div class="math">Var(<i>X&#772;</i>) = (&sigma;<sup>2</sup>/<i>n</i>)
        [1 + (<i>n</i>&minus;1)&rho;] &nbsp;&xrarr;<sub><i>n</i>&rarr;&infin;</sub>&nbsp;
        &rho;&sigma;<sup>2</sup> &gt; 0</div>
        이다. 따라서 <b>유효 표본 수는 최대 1/&rho; 에서 멈춘다</b>:
        <i>n</i><sub>eff</sub> = <i>n</i>/[1+(<i>n</i>&minus;1)&rho;] &rarr; 1/&rho;.""",
        [("Var(&Sigma;<i>X</i><sub><i>i</i></sub>) = &Sigma;Var(<i>X</i><sub><i>i</i></sub>) + &Sigma;<sub><i>i</i>&ne;<i>j</i></sub>Cov(<i>X</i><sub><i>i</i></sub>,<i>X</i><sub><i>j</i></sub>).",
          "분산의 전개. 교차항이 공분산이다."),
         ("Cov(<i>X</i><sub><i>i</i></sub>,<i>X</i><sub><i>j</i></sub>) = &rho;&sigma;<sup>2</sup> 이고 그런 쌍이 <i>n</i>(<i>n</i>&minus;1) 개다.",
          "상관계수의 정의 &rho; = Cov/(&sigma;&sigma;). 순서쌍을 세므로 <i>n</i>(<i>n</i>&minus;1)."),
         ("그러므로 Var(&Sigma;) = <i>n</i>&sigma;<sup>2</sup> + <i>n</i>(<i>n</i>&minus;1)&rho;&sigma;<sup>2</sup>.",
          "1 에 2 를 대입했다."),
         ("평균은 &Sigma;/<i>n</i> 이므로 분산을 <i>n</i><sup>2</sup> 으로 나눈다: (&sigma;<sup>2</sup>/<i>n</i>)[1+(<i>n</i>&minus;1)&rho;].",
          "Var(<i>aY</i>) = <i>a</i><sup>2</sup>Var(<i>Y</i>), <i>a</i>=1/<i>n</i>."),
         ("<i>n</i>&rarr;&infin; 에서 (&sigma;<sup>2</sup>/<i>n</i>)(<i>n</i>&minus;1)&rho; &rarr; &rho;&sigma;<sup>2</sup>.",
          "(<i>n</i>&minus;1)/<i>n</i> &rarr; 1. 첫 항 &sigma;<sup>2</sup>/<i>n</i> 은 0 으로 간다."),
         ("&rho;&gt;0 이면 극한이 0 이 아니므로, 평균이 참값으로 수렴하지 않는다.",
          "분산이 안 줄면 큰 수의 법칙이 주는 수렴이 없다 &mdash; 남는 것은 <b>공통 편향</b>이다."),
         ("독립 <i>m</i> 개의 분산 &sigma;<sup>2</sup>/<i>m</i> 과 같아지는 <i>m</i> 을 풀면 <i>n</i><sub>eff</sub> = <i>n</i>/[1+(<i>n</i>&minus;1)&rho;].",
          "두 분산을 같다고 놓고 <i>m</i> 에 대해 푼 것이 유효 표본 수의 정의다."),
         (f"대조: <i>p</i>={p0}, <i>n</i>=31 을 표집으로 돌리면 &rho;=0 에서 "
          f"{수(상관[0][1], 4)}, &rho;=0.8 에서 {수(상관[3][1], 4)} 로 주저앉는다.",
          "공통 요인 모형으로 상관을 만들어 실제로 {0} 번 돌린 값이다 &mdash; 위 계산과 독립인 확인이다.".format(수(200000))),
         ],
        가정="모든 쌍의 상관이 같다(교환가능성). 다르면 평균 상관을 쓰면 된다."))

    c.날것(표(f"같은 <i>n</i>=31, 같은 <i>p</i>={p0}. <b>상관 하나가 표본 수를 통째로 먹는다.</b>",
            ["오차 상관 &rho;", "다수결 정확도 (표집)", "유효 표본 수 1/&rho;", "뜻"],
            [[f"{수(r, 2)}", f"{수(v, 4)}",
              "&infin; (독립)" if r == 0 else f"{수(1/r, 3)}",
              {0.0: "정리 10 이 그대로 산다",
               0.2: "31 개가 <b>5 개</b> 값어치",
               0.5: "31 개가 <b>2 개</b> 값어치",
               0.8: "31 개가 <b>1.25 개</b> 값어치 &mdash; 돈만 31 배"}[r]]
             for r, v in 상관]))

    c.날것(짚기("""<b>그래서 자기일관성의 값어치는 &lsquo;표본을 몇 개 뽑았나&rsquo; 가 아니라
    &lsquo;표본들이 얼마나 다른가&rsquo; 로 정해진다.</b> 실무에서 상관을 낮추는 방법은
    온도를 올리는 것이 <b>아니다</b> &mdash; 온도는 같은 편향 안에서 흔들 뿐이다.
    상관을 실제로 낮추는 것은 <b>다른 프롬프트 · 다른 모형 · 다른 도구 경로</b>다.
    A5 의 팬아웃에서 하위 에이전트에게 <b>서로 다른 각도</b>를 주는 이유가 이것이다."""))

    c.날것(사고("""<b>이 저장소에서 잰 것.</b> 같은 질문을 온도만 바꿔 여러 번 물었을 때와,
    질문의 <b>틀</b>을 바꿔 물었을 때의 답 분포를 비교한 적이 있다. 온도만 바꾼 쪽은
    표본이 늘어도 다수결이 거의 안 변했다 &mdash; 정리 11 의 &rho; 가 컸다는 뜻이다.
    이때 우리가 처음 내린 결론은 &ldquo;자기일관성은 효과가 없다&rdquo; 였는데, <b>틀렸다.</b>
    효과가 없었던 것은 <b>우리가 만든 표본이 독립이 아니었기</b> 때문이다."""))

    # ------------------------------------------------------------------
    c.절("B3.3 최선의 n — 고르는 순간 분포가 움직인다")

    c.날것(정의("best-of-<i>n</i> (rejection sampling / BoN)",
              "표본 <i>n</i> 개를 뽑아 <b>점수가 가장 높은 하나</b>를 낸다. 다수결과 다른 "
              "점은 &lsquo;누가 맞나&rsquo; 를 표들끼리가 아니라 <b>외부 채점자</b>가 정한다는 것."))
    c.날것(정의("보상 모형 (reward model)",
              "출력 하나에 점수를 매기는 모형. 사람 선호로 학습하거나(RLHF), "
              "규칙으로 짜거나(테스트 통과 여부), 검증기로 둔다."))

    c.날것(정리(
        "best-of-<i>n</i> 이 바탕 분포에서 벗어나는 거리",
        """바탕 분포 <i>p</i> 에서 독립으로 <i>n</i> 개를 뽑아 점수 <i>r</i> 이 최대인
        것을 고른다. 점수의 분포가 연속(동점이 확률 0)이면, 고른 표본의 분포
        <i>p</i><sub>BoN</sub> 은 바탕과 다음만큼 떨어져 있다.
        <div class="math">KL(<i>p</i><sub>BoN</sub> &#8214; <i>p</i>)
        = log <i>n</i> &minus; (<i>n</i>&minus;1)/<i>n</i></div>
        <b>이 값은 점수 함수 <i>r</i> 이 무엇이든 같다.</b>""",
        [("<i>u</i> = <i>F</i>(<i>r</i>(<i>y</i>)) 로 두면(<i>F</i> 는 <i>p</i> 아래에서 점수의 누적분포), <i>y</i> ~ <i>p</i> 일 때 <i>u</i> ~ Uniform(0,1).",
          "연속 분포를 자기 자신의 누적분포로 보내면 균등분포가 된다 &mdash; 확률적분변환."),
         ("<i>n</i> 개 중 최대를 고르는 것은 <i>u</i> 의 최댓값을 고르는 것과 같다.",
          "<i>F</i> 가 증가함수라 순서를 보존한다."),
         ("Uniform(0,1) <i>n</i> 개의 최댓값의 밀도는 <i>n</i><i>u</i><sup><i>n</i>&minus;1</sup>.",
          "P(max &le; <i>u</i>) = <i>u</i><sup><i>n</i></sup> 를 미분한 것."),
         ("그러므로 <i>p</i><sub>BoN</sub>(<i>y</i>) = <i>p</i>(<i>y</i>)&middot;<i>n</i><i>F</i>(<i>r</i>(<i>y</i>))<sup><i>n</i>&minus;1</sup>.",
          "&lsquo;<i>y</i> 가 뽑히고 나머지 <i>n</i>&minus;1 개가 모두 <i>y</i> 보다 낮을&rsquo; 확률 &mdash; 3 을 <i>y</i> 에 얹은 것."),
         ("KL = <b>E</b><sub>BoN</sub>[log(<i>p</i><sub>BoN</sub>/<i>p</i>)] = log <i>n</i> + (<i>n</i>&minus;1)<b>E</b><sub>BoN</sub>[log <i>u</i>].",
          "4 의 비를 로그 취해 기댓값. <i>p</i> 가 약분된다."),
         ("<b>E</b><sub>BoN</sub>[log <i>u</i>] = &int;<sub>0</sub><sup>1</sup> (log <i>u</i>)&middot;<i>n</i><i>u</i><sup><i>n</i>&minus;1</sup> d<i>u</i> = &minus;1/<i>n</i>.",
          "&int;<sub>0</sub><sup>1</sup><i>u</i><sup><i>n</i>&minus;1</sup>ln <i>u</i> d<i>u</i> = &minus;1/<i>n</i><sup>2</sup> 에 <i>n</i> 을 곱한 것(부분적분)."),
         ("합치면 log <i>n</i> &minus; (<i>n</i>&minus;1)/<i>n</i>. <i>r</i> 은 2 에서 순서만 쓰고 사라졌다.",
          "5 에 6 을 넣었다. 점수의 <b>값</b>이 아니라 <b>순위</b>만 쓰였기 때문에 <i>r</i> 이 안 남는다."),
         (f"대조: <i>n</i>=64 에서 닫힌 꼴 {수(kl[2][1], 5)}, 수치적분 {수(kl[2][2], 5)} "
          f"&mdash; 차이 {수(abs(kl[2][1]-kl[2][2]), 2)}.",
          "적분을 {0} 칸으로 직접 더해 본 것이다.".format(수(400000))),
         ],
        가정="점수 분포가 연속(동점 없음). 동점이 있으면 KL 이 이보다 작다."))

    c.날것(표("best-of-<i>n</i> 의 KL 예산. <b>점수 함수와 무관하게</b> 이만큼 움직인다.",
            ["<i>n</i>", "KL (닫힌 꼴)", "수치 대조", "뜻"],
            [[f"{n}", f"{수(a, 4)} nat", f"{수(b, 4)}",
              {2: "거의 안 움직인다", 8: "눈에 띄게 치우친다",
               64: "<b>다른 분포라고 봐야 한다</b>"}[n]]
             for n, a, b in kl]))

    c.날것(정의("굿하트 법칙 (Goodhart's law)",
              "&lsquo;지표가 목표가 되는 순간 그것은 좋은 지표이기를 그만둔다.&rsquo; "
              "best-of-<i>n</i> 에서는 <i>n</i> 을 키울수록 <b>보상 모형의 흠</b>을 정확히 "
              "찾아내는 표본이 뽑힌다 &mdash; 진짜 품질이 아니라."))

    c.날것(개념(
        "KL 예산으로 <i>n</i> 을 정한다",
        """<b>이론.</b> 정리 12 는 <i>n</i> 이 정하는 &lsquo;움직인 거리&rsquo; 가 log <i>n</i>
        &minus; (<i>n</i>&minus;1)/<i>n</i> 임을 말한다. 보상 모형이 참 품질과
        어긋나기 시작하는 거리를 <i>D</i>* 라 하면, <b><i>n</i> 은 그 거리를 넘지 않게
        고르면 된다.</b> 이것이 RLHF 의 KL 페널티와 같은 눈금이라는 점이 중요하다
        &mdash; best-of-<i>n</i> 과 정책 학습을 <b>같은 자로 비교</b>할 수 있다.""",
        어디에="""표본을 여러 개 뽑아 고르는 모든 자리 &mdash; 코드 생성의 후보 고르기,
        도구 호출 후보, 답변 재순위""",
        언제="""점수 매기는 장치(테스트 · 검증기 · 보상 모형)가 있을 때. 없으면
        best-of-<i>n</i> 이 아니라 다수결(B3.1)을 써야 한다""",
        어떻게="""(1) 작은 <i>n</i> 부터 올리며 <b>참 품질</b>(사람 평가 · 숨긴 테스트)을
        같이 잰다 &rarr; (2) 참 품질이 꺾이는 <i>n</i>* 를 찾는다 &rarr;
        (3) 그 <i>n</i>* 의 KL 을 예산으로 적어 둔다 &rarr; (4) 보상 모형을 바꾸면
        <b>예산을 다시 잰다</b>""",
        산업코드="""# best-of-n 은 코드 몇 줄이다. 어려운 것은 (2) 를 실제로 재는 것.
cands = [gen(prompt, temperature=1.0) for _ in range(n)]
scored = [(reward_model(c), c) for c in cands]
best   = max(scored)[1]

# 그리고 반드시 같이 재야 하는 것 -- 숨긴 검증자
hidden = [held_out_tests(c) for c in cands]      # 보상 모형이 못 보는 잣대
# n 을 올려도 hidden 이 안 오르면 그 지점이 굿하트의 시작이다""",
        주의="""<b>보상 모형 점수가 오르는 것을 품질이 오르는 것으로 읽으면 안 된다.</b>
        정리 12 가 말하듯 <i>n</i> 을 키우면 <b>보상 점수는 반드시 오른다</b>
        &mdash; 최댓값을 고르니까. 오르지 <b>않는 것</b>이 있는지를 봐야 한다."""))

    c.날것(정의("검증자 간극 (verifier gap)",
              "&lsquo;점수를 매기는 장치가 보는 것&rsquo; 과 &lsquo;우리가 진짜 원하는 것&rsquo; 사이의 "
              "차이. 이 간극이 0 이면(예: 컴파일과 테스트 통과) <i>n</i> 을 크게 키워도 "
              "안전하고, 클수록(예: 사람 선호 근사 모형) 작은 <i>n</i> 에서 꺾인다."))

    c.날것(짚기("""<b>에이전트에서 검증자 간극이 작은 자리를 찾는 것이 설계의 핵심이다.</b>
    코드는 운이 좋다 &mdash; 테스트가 있다. 그래서 코드 에이전트는 <i>n</i> 을 크게
    써도 되고, 실제로 SWE-bench 류에서 그렇게 한다. 반대로 &ldquo;좋은 설명&rdquo; 같은
    자리는 검증자가 없으므로 <i>n</i> 을 키우면 <b>보상 모형이 좋아하는 글</b>이
    나올 뿐이다."""))

    c.날것(예제(
        "언제 다수결이고 언제 best-of-<i>n</i> 인가",
        """같은 예산 <i>n</i>=8. 과제 A 는 산술 문제(답이 하나, 검증자 없음),
        과제 B 는 파이썬 함수 작성(숨긴 테스트가 있다).""",
        """A 는 채점 장치가 없으므로 표들끼리 겨뤄야 한다 &rarr; <b>다수결</b>.
        정리 10 이 적용되고, 관건은 &rho; 를 낮추는 것(다른 풀이 경로를 유도).
        B 는 검증자 간극이 0 인 채점 장치가 있다 &rarr; <b>best-of-<i>n</i></b>.
        정리 12 의 KL 이 커져도 테스트가 진짜 잣대라 굿하트가 안 온다.""",
        f"""A: 다수결. B: best-of-8 (KL {수(bonKL(8), 4)} nat 이지만 검증자가 참이라 안전).""",
        """<b>거꾸로 하면 둘 다 손해다.</b> A 에 best-of-<i>n</i> 을 쓰면 점수 장치가
        없어 &lsquo;가장 그럴듯한 것&rsquo; 을 고르게 되는데, 그것은 모형의 편향을
        <b>증폭</b>한다. B 에 다수결을 쓰면 여덟 개 중 여섯 개가 같은 방식으로 틀렸을 때
        그 틀린 답이 이긴다 &mdash; <b>테스트가 있는데도 안 돌려 보고.</b>""",
        덧="""실무의 답은 대개 <b>둘 다</b>다: 검증자를 통과한 것들 중에서 다수결.
        통과가 여러 개면 그것들은 &lsquo;정답 후보&rsquo; 로 독립성이 높아져 정리 10 의
        조건에 가까워진다."""))

    c.날것(언어(
        "&ldquo;n 개를 동시에 돌리고 먼저 되는 것부터 쓴다&rdquo; 를 세 말로",
        [("Python — asyncio",
          """import asyncio

async def best_of_n(prompt: str, n: int, score) -> str:
    tasks = [asyncio.create_task(gen(prompt)) for _ in range(n)]
    try:
        cands = await asyncio.gather(*tasks)
    finally:
        for t in tasks:            # 예외가 나도 남은 것을 반드시 취소한다
            t.cancel()
    return max(cands, key=score)""",
          "<code>finally</code> 의 <code>cancel()</code> 이 없으면 <b>고아 작업</b>이 남는다 "
          "&mdash; A9 의 고아 프로세스와 같은 병이고, 돈이 계속 나간다"),
         ("TypeScript — Promise.allSettled",
          """export async function bestOfN<T>(
  make: () => Promise<T>, n: number, score: (t: T) => number,
): Promise<T> {
  const ac = new AbortController();
  const rs = await Promise.allSettled(
    Array.from({ length: n }, () => make()));
  ac.abort();                                  // 남은 것 정리
  const ok = rs.flatMap(r => r.status === "fulfilled" ? [r.value] : []);
  if (ok.length === 0) throw new Error("모두 실패");
  return ok.reduce((a, b) => (score(a) >= score(b) ? a : b));
}""",
          "<code>Promise.all</code> 이 아니라 <b><code>allSettled</code></b> 다 &mdash; "
          "<code>all</code> 은 하나만 실패해도 전부 버린다. <i>n</i> 개 중 몇 개가 "
          "실패하는 것은 정상이므로 <code>allSettled</code> 가 맞다"),
         ("Rust — tokio, 그리고 취소가 공짜다",
          """use futures::future::join_all;

pub async fn best_of_n<T, F, Fut>(make: F, n: usize, score: impl Fn(&T) -> f64)
    -> Option<T>
where F: Fn() -> Fut, Fut: std::future::Future<Output = anyhow::Result<T>> {
    let outs = join_all((0..n).map(|_| make())).await;
    outs.into_iter()
        .filter_map(Result::ok)
        .max_by(|a, b| score(a).total_cmp(&score(b)))
}""",
          "러스트의 future 는 <b>await 하지 않으면 아무 일도 안 한다</b>(lazy). "
          "그래서 드롭하면 그대로 취소다 &mdash; 파이썬·JS 처럼 &lsquo;떠 있는 작업&rsquo; "
          "이라는 개념이 없어서 고아가 원천적으로 덜 생긴다. "
          "<code>total_cmp</code> 는 <code>f64</code> 가 <code>Ord</code> 가 아니라서 "
          "(NaN 때문에) 필요한 것 &mdash; <b>언어가 NaN 을 잊지 못하게 한다</b>")],
        짚기="""<b><i>n</i> 을 키우는 코드는 열 줄이고, <i>n</i> 을 정하는 근거는 이 장
        전체다.</b> 그리고 세 칸 모두에서 진짜 위험은 알고리즘이 아니라 <b>취소</b>다
        &mdash; 안 쓴 표본이 계속 토큰을 태우는 것."""))

    c.날것(유도("이 장을 한 문단으로", [
        ("표본이 독립이면 다수결 오답이 지수적으로 준다",
         "정리 10 &mdash; 회프딩"),
        ("그런데 같은 모형·같은 프롬프트의 표본은 독립이 아니다",
         "공통 편향이 모든 표본에 똑같이 들어 있다"),
        ("상관 &rho; 가 있으면 유효 표본 수가 1/&rho; 에서 멈춘다",
         "정리 11 &mdash; 평균의 분산이 &rho;&sigma;<sup>2</sup> 로 수렴"),
        ("그래서 <i>n</i> 을 늘리기 전에 <b>다르게 만들기</b>를 먼저 한다",
         "다른 프롬프트 · 다른 모형 · 다른 경로 &mdash; 온도가 아니다"),
        ("채점 장치가 있으면 다수결 대신 best-of-<i>n</i>",
         "표들끼리 겨루는 대신 외부 잣대를 쓴다"),
        ("그 대가는 log <i>n</i> &minus; (<i>n</i>&minus;1)/<i>n</i> 의 KL 이다",
         "정리 12 &mdash; 점수 함수와 무관한 값"),
        ("검증자 간극이 0 이면 그 KL 을 크게 써도 되고, 크면 금방 굿하트가 온다",
         "테스트는 참 잣대이고 보상 모형은 근사다"),
    ]))

    c.날것(논문출처([
        ["Wang 외, <i>Self-Consistency Improves Chain of Thought Reasoning</i>",
         "arXiv:2203.11171", "<b>조각</b>", "B3.1 의 이름 (정리는 직접 증명했다)"],
        ["Stiennon 외, <i>Learning to summarize from human feedback</i>",
         "arXiv:2009.01325", "<b>조각</b>", "B3.3 의 KL 눈금 &mdash; 부록 식으로 알려진 것"],
        ["Gao 외, <i>Scaling Laws for Reward Model Overoptimization</i>",
         "arXiv:2210.10760", "<b>조각</b>", "B3.3 굿하트의 경험적 모양"],
    ]))

    return c.완성()
