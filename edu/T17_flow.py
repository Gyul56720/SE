# -*- coding: utf-8 -*-
"""T17 -- The implementation flow: what each stage decides, and what it hands over."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch
import sch_flow


# ---------------------------------------------------------------------------
# 재는 것 1 -- 되돌이 한 바퀴의 값
#
# 단계마다 돌리는 시간이 있다.  k 단계에서 잡힌 잘못은 **1..k 를 다시 돌려야**
# 고쳐진다(앞 단계의 출력이 뒤 단계의 입력이므로).  그 합이 한 바퀴의 값이다.
# 아래 시간은 **가정이고 그렇게 적는다** -- 100 만 인스턴스 블록, 서버 한 대.
# ---------------------------------------------------------------------------
단계 = [
    ("Elaboration + lint",        0.2),
    ("Simulation (regression)",   6.0),
    ("Logic synthesis",           4.0),
    ("Floorplan + power plan",    1.0),
    ("Placement",                 5.0),
    ("CTS",                       3.0),
    ("Routing",                  14.0),
    ("Extraction + signoff STA", 10.0),
    ("Physical verification",     8.0),
]


def _되돌이값(k):
    """k 번째 단계(0부터)에서 잘못이 잡혔을 때 다시 돌려야 하는 시간의 합."""
    return sum(t for _, t in 단계[: k + 1])


def _바퀴수(p, 항=200):
    """고침 하나가 확률 p 로 새 위반을 하나 낳을 때 기대 바퀴 수.

    분기과정이다.  한 바퀴가 평균 p 개의 다음 바퀴를 낳으므로 기대 총 바퀴 수는
    기하급수 1 + p + p^2 + ... = 1/(1-p) 이고, p >= 1 이면 **발산한다**.
    여기서는 닫힌 꼴을 쓰지 않고 **항을 더해서** 낸다 -- 아래 대조와 독립이게.
    """
    s, 항값 = 0.0, 1.0
    for _ in range(항):
        s += 항값
        항값 *= p
    return s


def _바퀴수_몬테카를로(p, 판=20000, 씨=11):
    """같은 수를 **다른 길로** -- 분기과정을 실제로 돌려 본다.

    닫힌 꼴도 급수도 쓰지 않는다.  위반 하나에서 시작해 각 고침이 확률 p 로
    새 위반을 낳게 하고, 큐가 빌 때까지 센 고침 수의 평균을 낸다.
    """
    r = random.Random(씨)
    총 = 0
    for _ in range(판):
        큐, 센것 = 1, 0
        while 큐 and 센것 < 5000:
            큐 -= 1
            센것 += 1
            if r.random() < p:
                큐 += 1
        총 += 센것
    return 총 / 판


def ch_flow():
    c = 장(
        "T17", "The Implementation Flow — What Each Stage Decides",
        "Every stage removes a degree of freedom. The cost of a mistake is the "
        "cost of putting that freedom back.",
        쓰는것=["RC지연", "배선지연", "슬루", "슬랙", "도착시각", "요구시각",
              "OCV", "플로어플랜", "추상화뷰", "추출", "GDS", "DRC", "LVS",
              "리셋동기화기", "리커버리"],
        내놓는것=["구현흐름", "합성", "넷리스트", "표준셀라이브러리",
                "타이밍라이브러리", "LEF", "DEF", "SDC", "SPEF", "SDF",
                "정적타이밍분석", "타이밍수렴", "ECO", "배선부하모델",
                "물리인지합성", "사인오프"],
        특허="""The flow itself is not patentable, but two things inside it are and
        both are actively litigated: <b>timing prediction before the geometry exists</b>
        (estimating post-route delay from an RTL or netlist feature set, so the loop
        closes in minutes rather than days) and <b>ECO placement</b> — inserting fixes
        into a routed design without disturbing what already met timing. Both attack
        the same economics this chapter computes: the flow's cost is dominated by how
        many times you go round it.""")

    c.글("""A design does not become a chip in one step. It passes through a chain of
    tools, each of which takes a description that is free in some respect and returns
    one that is not: synthesis fixes which gates exist, placement fixes where they are,
    CTS fixes when each one is clocked, routing fixes which metal carries which net.
    <b>Each stage removes a degree of freedom, and no later stage can put it back
    cheaply.</b> That single sentence explains the shape of the whole flow — why the
    effort is front-loaded, why the file formats look the way they do, and why the
    quantity a project manager actually tracks is not progress but <i>iteration
    count</i>.""")

    # ------------------------------------------------------------------
    c.절("T17.1 The chain, and what crosses each boundary")

    c.날것(그림(sch_flow.구현흐름고리(),
        "The same chain drawn as the flow actually runs it. The grey arrows are "
        "STA, which sees the design twice — once on the netlist, where the wires "
        "are estimated, and once on the layout, where they are real. The two "
        "coloured loops are what this chapter costs out: the orange one re-runs "
        "synthesis, the red one re-runs everything."))

    c.날것(그림(sch.블록도(
        [["RTL", "Synthesis", "Floorplan", "Placement"],
         ["CTS", "Routing", "Signoff", "GDS / tape-out"]],
        설명={"RTL": "behaviour\n+ SDC",
             "Synthesis": "gates chosen\nnetlist + SDC",
             "Floorplan": "die, rows, IO\npower grid",
             "Placement": "each cell's\nlocation",
             "CTS": "clock arrival\nfixed",
             "Routing": "metal assigned\nparasitics real",
             "Signoff": "STA / DRC / LVS\nEM-IR",
             "GDS / tape-out": "geometry\nto the mask shop"}),
        "The digital implementation flow. Every arrow is a file, and the file formats "
        "in T17.2 are what make the arrow possible at all."))

    c.날것(정의("구현 흐름 (implementation flow)",
        "The ordered chain of tools that turns an RTL description plus a set of "
        "constraints into manufacturable geometry. Ordered, because each stage's "
        "output is the next stage's input — and because <b>the information each stage "
        "needs about the stages after it does not exist yet</b>. That last clause is "
        "the source of every difficulty in this chapter."))

    c.날것(짚기("""The flow is a chain, but the <b>information</b> runs the other way.
    Synthesis must choose gate sizes to meet a delay it cannot know, because the delay
    depends on wire lengths that placement has not chosen yet. Placement must choose
    locations to meet a delay it cannot know, because routing has not happened. Every
    stage is therefore <b>estimating its own successor</b>, and the quality of that
    estimate — not the quality of the optimisation — decides how many times you go
    round."""))

    c.날것(표("What crosses each boundary, and what it is for",
        ["File", "Written by", "Carries", "The failure when it is wrong"],
        [["<b>.v / .sv</b> (netlist)", "Synthesis",
          "Which cells exist and how they connect",
          "Nothing later can add a register that RTL did not describe"],
         ["<b>.lib</b> (Liberty)", "The foundry / library vendor",
          "Delay, transition, power and constraint tables for every cell, "
          "<b>one file per corner</b>",
          "Timing signed off at a corner the silicon never sees"],
         ["<b>.lef</b>", "Library vendor + macro owner",
          "Abstract geometry: cell outline, pin shapes, blockages, routing layers",
          "The router cannot reach a pin (T15.3) — found after routing, fixed in the "
          "floorplan"],
         ["<b>.def</b>", "Place &amp; route",
          "The actual placement and routing: every instance's location, every net's "
          "metal", "This is the design; a DEF that loses a power connection is a "
          "silent short-to-nothing"],
         ["<b>.sdc</b>", "<b>The designer</b>",
          "Clocks, IO timing, false and multicycle paths, derates",
          "The only file in this list a tool cannot generate — and the one that "
          "decides what 'meets timing' <i>means</i>"],
         ["<b>.spef</b>", "Extraction",
          "Per-net R and C from the real geometry",
          "Pre-route estimates replace it, and the estimate is optimistic"],
         ["<b>.sdf</b>", "STA",
          "Back-annotated delays for gate-level simulation",
          "Simulation passes on delays that signoff never agreed to"],
         ["<b>.gds</b> / <b>.oas</b>", "The flow's last step",
          "Every polygon on every mask layer", "This is what is manufactured"]]))

    c.날것(사고("""A block met timing at every corner and failed in silicon at cold.
    The SDC had a <code>set_false_path</code> on a reset that was genuinely asynchronous
    on assertion — and synchronous on <b>de-assertion</b> (T3, X42). The false path
    removed the one check that would have caught the recovery violation. Nothing in the
    flow was wrong; the file that says what the flow should check was wrong, and it is
    the one file nobody generates automatically."""))

    # ------------------------------------------------------------------
    c.절("T17.2 The estimate that every stage makes about its successor")

    c.날것(개념(
        "배선 부하 모델 (wire-load model) and why it was abandoned",
        """<p>Classical synthesis estimated a net's capacitance from its <b>fanout</b>
        using a table supplied with the library: a 4-fanout net in a block of this size
        has, statistically, this much wire on it. It is a defensible estimate when wire
        delay is a small part of the path.</p>
        <p>It stopped being defensible for the reason computed in X14: wire delay does
        not scale with the transistors. Once the wire is a large fraction of the path,
        a <i>statistical</i> wire length is useless, because the paths that fail are
        exactly the ones whose wires are <b>not</b> typical. The estimate is right on
        average and wrong where it matters.</p>
        <p>The replacement is <b>physical-aware synthesis</b>: synthesis runs a coarse
        placement internally, so its wire lengths come from positions rather than from
        a table. It does not make the estimate exact — it makes it wrong in the same
        direction as the next stage, which is what a usable estimate must be.</p>""",
        어디에="Every synthesis run of a block large enough that the longest wires "
             "cross a meaningful fraction of the die.",
        언제="Always, now. The wire-load flow survives only in very small blocks and "
            "in teaching material.",
        어떻게="Give synthesis the floorplan (die outline, macro positions, IO "
             "locations) before it optimises, not after. Then compare its predicted "
             "slack with post-route slack on the same paths — <b>that difference is "
             "the number that tells you whether your flow converges</b>.",
        산업코드="""# The correlation check that belongs in every block's log. Not
# "did it meet timing" -- how far the estimate moved between stages.
#
#   path                 synth slack   place slack   route slack   drift
#   u_alu/…/sum[31]        +120 ps       +85 ps        -40 ps      -160 ps
#   u_ctl/…/state[2]        +95 ps       +90 ps        +70 ps       -25 ps
#
# A drift column that is large and negative means the flow is not converging:
# you are not closing timing, you are discovering it.""",
        주의="""A synthesis run that reports large positive slack on a physically
            aware flow is not good news by itself — check that the floorplan it used is
            the floorplan place-and-route will use. An optimistic estimate made against
            a stale floorplan is worse than no estimate, because it is believed."""))

    # ------------------------------------------------------------------
    c.절("T17.3 What a loop costs, measured")

    c.글("""The flow's economics are not about tool quality. They are about where in
    the chain a mistake is found. A problem discovered at stage <i>k</i> requires
    re-running stages 1 through <i>k</i>, because each stage consumed the output of the
    one before it. The table below uses <b>assumed</b> runtimes for a
    one-million-instance block on a single server — assumed, and marked as such, because
    the real numbers depend on the tool, the machine and the design. What does not
    depend on those is the <b>shape</b>: the cost of a loop grows superlinearly with how
    late it closes, because the expensive stages are at the end.""")

    줄 = []
    for i, (이름, t) in enumerate(단계):
        누적 = _되돌이값(i)
        줄.append([이름, 수(t, 3, " h"), 수(누적, 3, " h"),
                   수(누적 / _되돌이값(0), 3, "×")])
    c.날것(표("Runtime per stage (assumed), and the cost of a loop that closes there",
        ["Stage", "Runs for", "A loop closing here costs", "Relative to a lint loop"],
        줄))

    _마지막 = _되돌이값(len(단계) - 1)
    _처음 = _되돌이값(0)
    c.글(f"""Read the last row: a problem found in physical verification costs
    {수(_마지막, 4, ' h')} of compute to re-reach that point, against
    {수(_처음, 3, ' h')} for the same problem found by lint —
    a factor of {수(_마지막/_처음, 3, '×')}. And that is only the machine time. The
    engineer's time, the calendar days, and the fact that the fix now has to be made
    without disturbing everything that already closed, are all on top of it.""")

    c.날것(짚기("""This is the entire argument for front-loading. It is not a cultural
    preference for careful RTL; it is arithmetic. The stages are ordered cheap-to-
    expensive, so <b>any check you can move earlier is multiplied by the ratio
    above</b>. That is why lint, CDC analysis, formal equivalence and a synthesis run
    with a real floorplan are run constantly, and why 'we will fix it in the backend' is
    a decision to pay several hundred times more for the same fix."""))

    # ------------------------------------------------------------------
    c.절("T17.4 Why timing closure sometimes does not close")

    c.글("""The loop cost above assumes you go round once. The harder question is how
    many times you go round — and there the flow has a property that surprises people
    the first time they meet it: <b>closure can diverge</b>. Fixing one violation
    changes the design, and a changed design can create violations that were not there
    before. Upsizing a cell to fix a setup path loads its driver; inserting a buffer
    takes placement space and pushes a neighbour; a hold fix adds delay a setup path
    was relying on not having.""")

    c.날것(유도("Expected number of fixes when each fix can create another", [
        ("Start with one violation. Fixing it is one unit of work.",
         "That is the work we are counting — one ECO applied and re-analysed."),
        ("Each fix creates a new violation with probability <i>p</i>, independently.",
         "This is the modelling assumption, and it is the one to argue with. It says "
         "a fix's side effects do not depend on how many fixes came before."),
        ("The process is then a branching process with mean offspring <i>p</i>.",
         "One parent, <i>p</i> children on average — the standard Galton–Watson form."),
        ("Generation <i>n</i> has expected size <i>p<sup>n</sup></i>.",
         "Expectation is multiplicative across independent generations."),
        ("Total expected work is 1 + p + p² + … = 1/(1−p) for p &lt; 1.",
         "Geometric series. Its sum is the <b>total</b> number of fixes, not the "
         "number of rounds of the tool."),
        ("For p ≥ 1 the series diverges: closure does not converge at all.",
         "Each fix creates at least one more on average, so the queue never empties. "
         "The design does not need a better engineer; it needs a change of "
         "floorplan, constraints or target frequency.")]))

    줄 = []
    for p in (0.1, 0.3, 0.5, 0.7, 0.9, 0.95):
        급수 = _바퀴수(p)
        mc = _바퀴수_몬테카를로(p)
        줄.append([수(p, 2), 수(급수, 4), 수(mc, 4),
                   수(100 * abs(mc - 급수) / 급수, 2, " %")])
    c.날것(표("Expected total fixes, two independent ways",
        ["p (a fix creates another)", "Series 1+p+p²+…",
         "Simulated branching process", "Disagreement"],
        줄))

    c.날것(짚기(f"""The two columns are computed by <b>different methods</b> — a summed
    series and a simulated queue that never uses the series — and they agree to within
    {수(max(100*abs(_바퀴수_몬테카를로(p)-_바퀴수(p))/_바퀴수(p) for p in (0.1,0.3,0.5,0.7,0.9)), 2, ' %')}
    over the range shown. That agreement is what licenses the claim; a single
    calculation would not, because the trivial explanation for a clean-looking curve is
    that it is the same arithmetic printed twice."""))

    c.날것(예제("Is this block going to close?",
        "Round 1 of ECO fixed 400 violations and the next STA run reported 260 new "
        "ones that did not exist before. Round 2 fixed those 260 and produced 180 new.",
        "Estimate p from the observed ratios: 260/400 = 0.65 and 180/260 ≈ 0.69. "
        "Take p ≈ 0.67. Expected total remaining work from the 180 now open is "
        "180/(1−0.67).",
        f"About {수(180/(1-0.67), 3)} more fixes — roughly three more rounds of "
        f"the same size. It converges, slowly, <b>if p stays at 0.67</b>.",
        "p is not a constant. It rises as utilisation rises and as the remaining "
        "violations get harder, so a p measured on the easy fixes underestimates the "
        "tail. Two consecutive rounds with a rising ratio is the signal to stop doing "
        "ECOs and change something structural — the arithmetic above says that once p "
        "reaches 1 no amount of ECO effort terminates.",
        덧="""<b>The independent check that matters here is not mathematical.</b>
        Before believing p, confirm the new violations are genuinely new paths and not
        the same paths re-reported after a constraint change — a tool that re-reports is
        the trivial explanation for an apparent p, and it is measured by diffing the
        endpoint lists, not by looking at the counts."""))

    # ------------------------------------------------------------------
    c.절("T17.5 What to do with this on Monday")

    c.날것(쓰는자리([
        ["구현흐름 · 사인오프", "Planning any block",
         "Which checks you can afford to run, and how often"],
        ["배선부하모델 · 물리인지합성", "Setting up synthesis",
         "Whether your early slack numbers mean anything"],
        ["LEF · DEF · SDC · SPEF · SDF", "Every handoff",
         "What you owe the next stage and what you are owed"],
        ["타이밍수렴 · ECO", "When the backend stops converging",
         "Whether to keep fixing or to change the floorplan or the frequency"],
    ]))

    c.글("""The next three chapters walk the chain in order and compute what each stage
    actually decides: the floorplan and the power grid that everything else sits on
    (T18), placement, clock tree and routing (T19), and the signoff checks that decide
    whether the geometry may be manufactured (T20).""")

    return c.완성()
