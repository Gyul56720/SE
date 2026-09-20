# -*- coding: utf-8 -*-
"""T21 -- The verification environment: what it proves, and what coverage does not."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch
import sch_flow


def 조화수(K):
    return sum(1.0 / i for i in range(1, K + 1))


def 쿠폰_닫힌꼴(K):
    """고르게 뽑을 때 K 칸을 모두 채우기까지의 기대 시험 수 = K·H_K."""
    return K * 조화수(K)


def 쿠폰_몬테카를로(K, 판=2000, 씨=7):
    """같은 수를 **식 없이** -- 실제로 뽑아서 다 찰 때까지 센다."""
    r = random.Random(씨)
    총 = 0
    for _ in range(판):
        본, n = set(), 0
        while len(본) < K:
            본.add(r.randrange(K))
            n += 1
        총 += n
    return 총 / 판


def 희귀칸_기대(p):
    """확률 p 인 칸 하나를 처음 맞히기까지의 기대 시험 수 (기하분포)."""
    return 1.0 / p


def 남은버그(관측, q):
    """버그 발견률이 매기간 q 배로 준다면 앞으로 더 나올 버그의 기대 수."""
    return 관측 * q / (1 - q)


def _읽기(n):
    if n < 1e3:
        return "comfortable"
    if n < 1e5:
        return "an overnight regression"
    return "<b>will never happen — write a directed test</b>"


def ch_dv():
    c = 장(
        "T21", "The Verification Environment — What It Proves",
        "Coverage says you tried it. Only the checker says it worked. "
        "Confusing the two is the most expensive mistake in verification.",
        쓰는것=["구현흐름", "넷리스트", "CDC검증", "준안정", "동기화기깊이",
              "비동기FIFO", "핸드셰이크", "그레이코드", "사인오프", "ECO",
              "정적타이밍분석", "타이밍수렴"],
        내놓는것=["검증환경", "테스트벤치", "에이전트", "시퀀스", "시퀀서",
                "드라이버", "모니터", "스코어보드", "참조모델", "가상인터페이스",
                "기능커버리지", "커버그룹", "커버포인트", "크로스커버리지",
                "제약랜덤", "어서션", "커버리지닫기", "지시시험", "회귀"],
        특허="""Verification methodology is published rather than patented — the
        methodology libraries are open source, which is the point of them. What is
        filed is around <b>coverage-directed test generation</b>: using the coverage
        result to steer the constraint solver towards the bins that are still empty,
        which is a direct attack on the coupon-collector arithmetic computed in this
        chapter.""")

    c.글("""Everything after this chapter's stage in the flow assumes the RTL is right.
    Synthesis will faithfully implement a bug; place-and-route will close timing on it;
    signoff will certify that it is manufacturable. <b>Verification is the only stage
    that can answer whether the design does what it was supposed to do</b>, and it is
    the stage that consumes the most engineering effort on almost every project. This
    chapter is about the structure that effort takes, and about the one distinction
    that decides whether the effort was worth anything.""")

    # ------------------------------------------------------------------
    c.절("T21.1 The structure, and why it is split the way it is")

    c.날것(그림(sch.블록도(
        [["Sequence", "Sequencer", "Driver", "DUT"],
         ["DUT ", "Monitor", "Scoreboard", "Pass / fail"]],
        설명={"Sequence": "what to do,\nabstractly",
             "Sequencer": "arbitrates between\nsequences",
             "Driver": "turns an item into\npin wiggles",
             "DUT": "the design",
             "DUT ": "the same design",
             "Monitor": "watches pins,\nrebuilds items",
             "Scoreboard": "compares against\na reference model",
             "Pass / fail": "the only verdict\nthat means anything"}),
        "The two halves of an agent. The upper path drives; the lower path observes "
        "and judges. They are deliberately not connected to each other — the monitor "
        "reconstructs what happened from the pins, so that a driver bug cannot hide "
        "itself by telling the scoreboard what it intended."))

    c.날것(그림(sch_flow.UVM테스트벤치(),
        "The environment in full. Read it as two halves that meet only at the "
        "DUT: sequences drive down the left of each agent, monitors observe up "
        "the right, and the scoreboard in the middle is the only thing that ever "
        "says the design is wrong."))

    c.날것(표("Each component, and the one question it answers",
        ["Component", "Answers", "Why it is separate from its neighbour"],
        [["<b>Sequence</b>", "What transactions should happen?",
          "It is written per test and knows nothing about pins — so the same sequence "
          "runs on a different bus protocol"],
         ["<b>Sequencer</b>", "In what order, when several sequences compete?",
          "Arbitration is a policy, and policies change per test while drivers do not"],
         ["<b>Driver</b>", "How is one transaction expressed on the wires?",
          "It is the only component that knows the protocol's timing. Everything "
          "above it is protocol-agnostic"],
         ["<b>Monitor</b>", "What actually happened on the wires?",
          "<b>It must be independent of the driver.</b> A monitor that trusts the "
          "driver's intent cannot detect a driver that drove the wrong thing"],
         ["<b>Scoreboard</b>", "Was it correct?",
          "It holds the reference model. It is the only component whose failure means "
          "the DUT is wrong"],
         ["<b>Coverage collector</b>", "What did we try?",
          "It must not judge. Mixing coverage and checking produces a testbench that "
          "reports 100 % of nothing"],
         ["<b>Config object</b>", "Which of the above exist, and how are they set up?",
          "So that one environment serves a block, a subsystem and the chip, with the "
          "agents that do not apply turned off rather than deleted"]]))

    c.날것(개념(
        "가상 인터페이스 (virtual interface) — the one construct with no software "
        "analogue",
        """<p>The testbench's driver and monitor are <b>class objects</b>: created at
        run time, garbage-collected, passed around by handle. The pins they must wiggle
        belong to a <b>module instance</b>, which is created at elaboration and exists
        for the whole simulation. A class cannot hold a reference to a static
        elaborated object directly, because at the time the class is written the
        instance does not exist.</p>
        <p>A virtual interface is the bridge: a handle, held by the class, pointing at
        an interface instance that <i>was</i> elaborated. The testbench's configuration
        step sets it, and after that the driver can drive real pins from dynamic
        code.</p>
        <p>The most common failure in a new environment is a null virtual interface —
        the driver was built before anything assigned it. It is not a subtle bug, but
        it is unfamiliar, because no ordinary software language has this split between
        two object lifetimes.</p>""",
        어디에="Every agent that touches the DUT.",
        언제="Set during the build/connect phase, before any sequence runs.",
        어떻게="Assign it from the top-level module into the configuration database, "
             "and have every driver and monitor fetch it during build — then "
             "<b>assert that it is non-null</b> rather than letting the first pin "
             "access fail with a null-handle error a thousand cycles later.",
        산업코드="""// Top level, where both worlds meet:
my_if  dut_if (.clk(clk));                 // elaborated: exists for the run
my_dut u_dut  (.p(dut_if));

initial begin
  // Hand the elaborated thing to the dynamic world, by name:
  uvm_config_db#(virtual my_if)::set(null, "*", "vif", dut_if);
  run_test();
end

// In the driver's build phase -- and check it, do not assume it:
if (!uvm_config_db#(virtual my_if)::get(this, "", "vif", vif))
  `uvm_fatal("NOVIF", "virtual interface was never set")""",
        주의="""Clocking blocks matter here: driving a DUT input from the testbench
            without one races with the DUT's own evaluation at the clock edge, and the
            race is resolved differently by different simulators. A testbench that
            passes on one simulator and fails on another is almost always a missing
            clocking block, not a tool bug."""))

    # ------------------------------------------------------------------
    c.절("T21.2 Coverage is a measure of stimulus, not of correctness")

    c.날것(정의("기능 커버리지 (functional coverage) · 커버포인트 · 크로스",
        "A <b>coverpoint</b> samples a value and sorts it into <b>bins</b>; a "
        "<b>covergroup</b> collects coverpoints and is sampled at a defined event; a "
        "<b>cross</b> is the set of bin combinations of two or more coverpoints. "
        "Coverage is the fraction of bins that have been hit at least once. Note what "
        "that definition does <b>not</b> contain: any reference to whether the design "
        "behaved correctly when the bin was hit."))

    c.날것(짚기("""<b>100 % functional coverage with a scoreboard that never fires is
    100 % evidence of nothing.</b> Coverage answers 'did the stimulus reach this
    situation'. Correctness is answered only by the scoreboard and the assertions. The
    two are reported side by side, they look similar, and they measure entirely
    different things — and a green coverage report is the most persuasive way to ship a
    bug, because it is a number, it is high, and nobody asks what it counted."""))

    c.날것(사고("""A block shipped with every covergroup at 100 %. The scoreboard's
    compare method had an early <code>return</code> added during debugging and never
    removed: it checked the first beat of each burst and silently passed the rest. Every
    bin was hit. Nothing was compared. The escape was found by a customer, and the
    testbench that missed it had a perfect coverage report throughout.
    <b>The check that would have caught it is not more coverage — it is a mutation
    test: change one bit of the DUT's output and confirm the scoreboard goes
    red.</b>"""))

    c.날것(개념(
        "자해 검사 (mutation testing) for a testbench",
        """<p>A testbench is a program that is supposed to fail when the design is
        wrong. Nothing in a normal regression ever exercises that property — every run
        is against a design that is (by then) right, so the failure path is never
        taken.</p>
        <p>The fix is to break the design on purpose: invert a bit in a response, drop
        a transaction, delay a handshake by one cycle, corrupt a byte in the middle of
        a burst. Then run the regression and confirm it goes red, and confirm
        <b>which</b> check caught it. A mutation nothing catches is a hole in the
        checking, located precisely.</p>
        <p>This is the same discipline that this book applies to its own numbers: a
        measurement that cannot come out wrong has not measured anything.</p>""",
        어디에="Every environment, at least once per major block, and in CI if you "
             "can afford the runtime.",
        언제="Before believing a coverage report. A mutation campaign is the only "
            "evidence that the coverage number is attached to a checker at all.",
        어떻게="Keep a list of mutations as a file, each with the check that is "
             "expected to catch it. Run them; a mutation caught by <i>no</i> check, or "
             "caught only by a timeout, is a finding.",
        산업코드="""# mutations.txt -- and the expected catcher, which is the real content
#   id  mutation                          expected catcher
#   m1  invert resp[0]                    scoreboard data compare
#   m2  drop every 8th write              scoreboard transaction count
#   m3  delay ready by 1 cycle            protocol assertion a_ready_stable
#   m4  return wrong burst length         scoreboard length compare
#   m5  corrupt byte 3 of burst           scoreboard data compare
#
# Result column after the run. Any row whose catcher is "none" or
# "test timeout" is a hole -- a timeout means nothing noticed, it just
# stopped.""",
        주의="""A mutation caught by every check is not a good result either — it
            means the mutation was too coarse to locate anything. The useful mutations
            are the ones caught by exactly one check, because those map a check to the
            failure it is responsible for."""))

    # ------------------------------------------------------------------
    c.절("T21.3 Why crosses explode: the arithmetic of random closure")

    c.날것(유도("How long random stimulus takes to fill K bins", [
        ("Assume each test lands in one of K bins, uniformly and independently.",
         "<b>The assumption to argue with.</b> Real constrained-random stimulus is "
         "neither uniform nor independent — but this case is the optimistic one, so "
         "what it computes is a lower bound on the effort."),
        ("With j bins already hit, the chance a test hits a new one is (K−j)/K.",
         "Counting. The remaining bins are K−j of the K."),
        ("So the expected number of tests to go from j to j+1 is K/(K−j).",
         "A geometric waiting time has mean 1/p."),
        ("Summing over j = 0…K−1 gives K·(1 + 1/2 + … + 1/K) = K·H<sub>K</sub>.",
         "Expectation is additive even though the waits are not independent of each "
         "other's outcomes."),
        ("H<sub>K</sub> ≈ ln K + 0.577, so the cost is about K·ln K.",
         "Slightly worse than linear in the number of bins — which is fine. The "
         "problem is not this factor; it is that <b>K itself is a product</b> when "
         "you cross."),
    ]))

    줄 = []
    for K in (10, 100, 1000):
        닫 = 쿠폰_닫힌꼴(K)
        mc = 쿠폰_몬테카를로(K, 2000 if K < 1000 else 300)
        줄.append([f"{K:,}", 수(닫, 5), 수(mc, 5),
                   수(100 * abs(mc - 닫) / 닫, 3, " %")])
    줄.append([f"{10000:,}", 수(쿠폰_닫힌꼴(10000), 6),
               "<i>not simulated</i>",
               "<i>the point: it is already ~10⁵ tests</i>"])
    c.날것(표("Expected tests to fill every bin, two independent ways",
        ["Bins K", "K·H<sub>K</sub>", "Simulated draw-until-full", "Disagreement"],
        줄))

    c.날것(짚기(f"""The two columns are computed by different means — a summed series and
    an actual repeated drawing that uses none of it — and they agree to within a few
    per cent, with the residual being the Monte-Carlo sampling error at
    {수(300,3)} trials for the largest case. That is what licenses the last row, which
    is the one that matters: <b>crossing two 100-bin coverpoints makes K = 10,000 and
    turns a {수(쿠폰_닫힌꼴(100),4)}-test job into a
    {수(쿠폰_닫힌꼴(10000),6)}-test one.</b> A cross is not a small addition to a
    coverage model; it is a multiplication of the closure effort."""))

    c.날것(표("And that was the optimistic case — one rare bin dominates everything",
        ["Probability of the rarest bin", "Expected tests to hit it once",
         "What it means in practice"],
        [[수(p, 4), 수(희귀칸_기대(p), 5), _읽기(희귀칸_기대(p))]
         for p in (1e-2, 1e-3, 1e-4, 1e-5, 1e-6)]))

    c.날것(짚기("""The uniform calculation understates the problem badly, because random
    closure is governed by the <b>rarest</b> bin, not the average. The last rows are the
    quantitative reason directed tests still exist in a constrained-random flow: a
    corner with probability 10⁻⁶ under the constraints will not be reached by adding
    machines. It is reached by changing the constraints for one test, or by writing
    that test by hand — and either way, by someone deciding it matters, which is a
    design decision and not a verification one."""))

    c.날것(예제("Should we add this cross?",
        "A proposal to cross 'transfer size' (8 bins) with 'address alignment' "
        "(4 bins) with 'outstanding transactions' (16 bins).",
        f"K = 8 × 4 × 16 = {8*4*16}. Under uniform random stimulus that is about "
        f"{수(쿠폰_닫힌꼴(8*4*16),5)} tests to fill. But check the legality first: "
        "a 1-byte transfer cannot be 8-byte-misaligned, so a good fraction of the "
        f"{8*4*16} bins are unreachable by construction.",
        f"Add it, with the illegal combinations declared <code>illegal_bins</code> "
        f"rather than left empty. The reachable count is what closure is measured "
        f"against; leaving {8*4*16} as the denominator guarantees the report never "
        f"reaches 100 % and trains everyone to ignore it.",
        "The trap is the opposite of the obvious one. The danger is not that the "
        "cross is too expensive — it is that an un-pruned cross produces a coverage "
        "number that can never reach its target, and a target that is known to be "
        "unreachable stops being a target. <b>An honest 100 % over reachable bins is "
        "worth more than an honest 87 % over a denominator nobody trusts.</b>",
        덧="""Declaring illegal bins has a second benefit that is worth more than the
        first: an <code>illegal_bins</code> that <i>fires</i> is an immediate error. It
        turns a statement about what cannot happen into a check that it did not."""))

    # ------------------------------------------------------------------
    c.절("T21.4 Knowing when to stop")

    c.글("""Coverage closure is a necessary condition for stopping, not a sufficient
    one. The question a project actually has to answer is different: <i>how many bugs
    are still in there?</i> That cannot be measured directly, but the rate at which
    bugs are being found can be, and a decaying rate carries information.""")

    c.날것(유도("Estimating the bugs you have not found yet", [
        ("Suppose the number of new bugs found per week falls by a constant factor q.",
         "An empirical observation in many projects, and the assumption this estimate "
         "rests on. It is not a law."),
        ("Then the bugs still to come are n·q + n·q² + … = n·q/(1−q), "
         "where n is this week's count.",
         "Geometric series, the same one as T17's ECO convergence — and it fails the "
         "same way when q approaches 1."),
        ("With n = 4 found this week and q = 0.7, that is "
         f"{수(남은버그(4,0.7),3)} more.",
         "Substitution. The number is small enough to be encouraging and uncertain "
         "enough to be dangerous, which is why the next step is the important one."),
        ("<b>Now kill the trivial explanation.</b> The rate can fall because bugs are "
         "running out, or because effort fell, or because the tests stopped changing.",
         "Three causes, one observable. Distinguishing them is not optional — two of "
         "the three mean the estimate is meaningless."),
        ("Measure effort and new-stimulus rate alongside the bug count.",
         "Constant simulation hours and rising coverage with a falling bug rate is "
         "evidence. A falling bug rate with a falling regression count is a "
         "<b>measurement of the team's schedule</b>, not of the design."),
    ]))

    줄 = []
    for q in (0.5, 0.7, 0.85, 0.95):
        줄.append([수(q, 3), 수(남은버그(4, q), 4),
                   "converging" if q < 0.8 else
                   ("slow" if q < 0.9 else "<b>no information — do not ship on this</b>")])
    c.날것(표("Four bugs this week: what the decay rate implies",
        ["q (week-on-week ratio)", "Expected bugs remaining", "Reading"], 줄))

    c.날것(짚기("""The last row is the honest one. At q = 0.95 the estimate is
    {} more bugs, and the model's error bars are far wider than that number — the
    geometric assumption is doing all the work. <b>An estimate whose value is dominated
    by an unverified assumption should be reported as an assumption, not as an
    estimate</b>, which is the same rule this book applies to every number in
    it.""".format(수(남은버그(4, 0.95), 3))))

    # ------------------------------------------------------------------
    c.절("T21.5 What to do with this on Monday")

    c.날것(쓰는자리([
        ["검증환경 · 테스트벤치 · 에이전트 · 시퀀스 · 시퀀서 · 드라이버 · 모니터",
         "Building an environment", "Whether it can be reused at the next level up"],
        ["스코어보드 · 참조모델 · 어서션", "Every environment, first",
         "The only components that can say the design is wrong"],
        ["기능커버리지 · 커버그룹 · 커버포인트 · 크로스커버리지",
         "Planning the coverage model", "What the stimulus reached — and nothing more"],
        ["제약랜덤 · 지시시험 · 커버리지닫기 · 회귀",
         "Deciding where to spend simulation time",
         "Which bins random will never reach, so you write them by hand"],
        ["가상인터페이스", "Connecting the environment to the DUT",
         "The one construct that has no analogue in ordinary software"],
    ]))

    c.글(f"""The numbers to carry: filling K bins with uniform random stimulus costs
    about K·ln K tests, so a cross of two 100-bin points costs
    {수(쿠폰_닫힌꼴(10000),6)} rather than {수(쿠폰_닫힌꼴(100),4)} — crosses multiply
    the closure effort, and pruning illegal combinations is therefore engineering
    rather than tidiness. And a bin with probability 10⁻⁶ takes
    {수(희귀칸_기대(1e-6),6)} tests to reach once, which is the arithmetic that keeps
    directed tests alive.""")

    c.글("""Verification establishes that the design is right. It says nothing about
    whether a particular piece of silicon was manufactured correctly — that question is
    answered by a machine with the die in it, and answering it cheaply is the subject of
    the last chapter.""")

    return c.완성()
