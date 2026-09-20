# -*- coding: utf-8 -*-
"""T19 -- Placement, clock tree and routing: where the netlist becomes geometry."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch
from T18_floorplan import 코어변, 코어면적, 인스턴스, 행높이, 자리폭, 전력 as 블록전력

# ---------------------------------------------------------------------------
# 가정과 그 출처.  T18 의 블록을 그대로 이어받는다 -- 두 장이 다른 칩을 말하면
# 수를 비교할 수 없다.
# ---------------------------------------------------------------------------
배선피치 = 0.56          # µm (가정: 행높이 5.04 = 9 트랙 × 0.56)
신호층 = 4               # 전원이 가져가고 남은 신호 배선층 수 (가정)
평균넷길이 = 30.0        # µm (가정 -- 아래에서 이 가정이 결론을 어떻게 흔드는지 잰다)
넷수 = 인스턴스          # 셀 하나에 출력 하나 (가정)

늦은배수, 이른배수 = 1.07, 0.93     # OCV 디레이트 (가정: ±7 %)
공통몫 = 0.98                        # 두 잎이 공유하는 경로의 비 (가정)

플롭수 = 20_000
팬아웃 = 16
클럭부하 = 4.0e-15        # F, 플롭 하나의 클럭 핀 용량 (가정)
버퍼부하 = 3.0e-15        # F, 클럭 버퍼 하나의 입력 용량 (가정)
주파수, VDD = 500e6, 1.8


def 트랙공급():
    """배선할 수 있는 총 길이 (µm).  순수한 기하 -- 가정이 아니라 계산이다."""
    return 신호층 * (코어변 / 배선피치) * 코어변


def 배선수요(평균=None):
    return 넷수 * (평균 if 평균 is not None else 평균넷길이)


def OCV스큐비():
    """삽입지연의 몇 배가 OCV 스큐로 나오나 -- 첨부 슬라이드의 그 산술."""
    return 1.00 * 늦은배수 - 공통몫 * 이른배수


def 클럭단수(n=플롭수, f=팬아웃):
    return math.ceil(math.log(n) / math.log(f))


def 클럭버퍼수(n=플롭수, f=팬아웃):
    """잎에서 뿌리까지 층층이 쌓았을 때의 버퍼 수 -- 등비합으로 센다."""
    수, 남 = 0, n
    while 남 > 1:
        남 = math.ceil(남 / f)
        수 += 남
    return 수


def 클럭전력(게이팅=0.0):
    """클럭망의 동적 전력.  `게이팅` 은 꺼 두는 시간의 비."""
    C = 플롭수 * 클럭부하 + 클럭버퍼수() * 버퍼부하
    return (1 - 게이팅) * C * VDD ** 2 * 주파수


def 수리반복(시작, q, 한계=60):
    """한 바퀴가 남은 위반의 (1-q) 를 없앤다고 할 때의 감소 열."""
    열, v = [], float(시작)
    for _ in range(한계):
        열.append(v)
        v *= q
        if v < 1:
            break
    return 열


def ch_pnr():
    c = 장(
        "T19", "Placement, Clock Tree and Routing",
        "Three stages, three decisions: where each cell is, when it is clocked, "
        "and which metal carries which net.",
        쓰는것=["구현흐름", "넷리스트", "표준셀행", "SITE", "점유율", "코어영역",
              "전원그리드", "파워스트라이프", "정적타이밍분석", "슬랙", "OCV",
              "배선지연", "RC지연", "슬루", "엘모어지연", "리피터", "논리적노력",
              "SDC", "DEF", "ECO", "타이밍수렴", "MTBF", "동기화기깊이",
              "안테나규칙", "필러셀", "디캡"],
        내놓는것=["배치", "합법화", "HPWL", "타이밍주도배치", "혼잡도", "트랙",
                "gcell", "렌트법칙", "클럭트리합성", "삽입지연", "클럭스큐",
                "유용스큐", "클럭메시", "H트리", "클럭게이팅", "CGIC",
                "전역배선", "상세배선", "탐색수리", "안테나위반"],
        특허="""Two areas here are patent-dense and worth knowing about before you
        reinvent them. <b>Clock-tree structures</b> — mesh, multi-source CTS, and the
        hybrid schemes that use a mesh at the top and trees below — are heavily filed,
        because skew is worth frequency and frequency is worth money. So is
        <b>detailed routing with machine-learned congestion prediction</b>, which tries
        to move the congestion information earlier, for exactly the loop-cost reason
        computed in T17.""")

    c.글("""The floorplan of T18 produced a box, a grid of power and a set of rows. What
    is inside the box is still a netlist — a list of cells and connections, with no
    positions. The three stages of this chapter give it geometry, and each of them fixes
    something the next one cannot change: placement fixes distance, clock-tree synthesis
    fixes arrival time, routing fixes the actual parasitics. After routing, the design
    has no remaining degrees of freedom except the small, local, expensive ones called
    ECOs.""")

    # ------------------------------------------------------------------
    c.절("T19.1 Placement: an optimisation with a discrete constraint")

    c.날것(정의("합법화 (legalisation)",
        "The step that moves cells from wherever the optimiser wanted them to the "
        "nearest <b>legal</b> position: on a row, snapped to a site boundary (T18), "
        "not overlapping another cell, respecting every placement rule the library "
        "carries. Global placement solves a continuous problem; legalisation projects "
        "the answer back onto the discrete set of positions that actually exist."))

    c.날것(짚기("""That two-step structure — solve a relaxed continuous problem, then
    project — is why placement quality reports show a jump at legalisation. The
    continuous solution is a lower bound nobody can achieve. <b>If the jump is large,
    the cause is almost always density</b>: the optimiser piled cells where there was no
    room, and legalisation had to move them a long way. That is a floorplan or
    utilisation problem reported by the placer, not a placer problem."""))

    c.날것(표("What each placement objective actually minimises",
        ["Objective", "The quantity", "When it is the right one"],
        [["<b>Wirelength (HPWL)</b>",
          "Sum over nets of the half-perimeter of the net's bounding box",
          "The default. Cheap to evaluate and differentiable enough to optimise; a "
          "good proxy for both delay and congestion when neither is critical"],
         ["<b>Timing-driven</b>",
          "Weighted wirelength, where a net's weight rises with how critical its path "
          "is", "Once timing is close. It trades total wirelength for the few paths "
          "that decide F<sub>max</sub>"],
         ["<b>Congestion-driven</b>",
          "Predicted routing demand per region, spread out",
          "When routing fails rather than timing. It deliberately <i>increases</i> "
          "wirelength to make the design routable at all"]]))

    c.날것(사고("""A block was re-placed with aggressive timing weights after a marginal
    STA run. Worst slack improved by 40 ps and the design became unroutable: the placer
    had pulled the critical datapath into a tight cluster, and the region's routing
    demand went past supply. <b>The three objectives above are in tension, and
    optimising one while not measuring the others is how a converging flow stops
    converging.</b>"""))

    # ------------------------------------------------------------------
    c.절("T19.2 Congestion: supply, demand, and why the average lies")

    c.날것(정의("트랙 (track) · gcell · 혼잡도 (congestion)",
        "A <b>track</b> is one routable line on one metal layer, at the layer's pitch. "
        "The router divides the core into <b>gcells</b> (global routing cells, a few "
        "tens of tracks across) and, for each gcell edge, compares the number of wires "
        "that must cross it with the number of tracks available. <b>Congestion</b> is "
        "that ratio. Above 1, some net cannot be routed there and must detour — or, if "
        "everything nearby is also above 1, cannot be routed at all."))

    공급 = 트랙공급()
    수요 = 배선수요()
    c.날것(유도("Track supply for the T18 block — pure geometry", [
        (f"The core is {수(코어변,4,' µm')} on a side (T18).",
         "Carried over so the two chapters describe the same chip."),
        (f"At a routing pitch of {수(배선피치,3,' µm')}, one layer offers "
         f"{수(코어변/배선피치,5)} tracks across the core.",
         "Core width divided by pitch. <b>Assumed pitch</b>, consistent with the "
         "5.04 µm row height being nine tracks."),
        (f"Each track runs the full {수(코어변,4,' µm')}.",
         "Length available per track, ignoring blockages — an upper bound, and it is "
         "worth remembering that it is one."),
        (f"With {신호층} usable signal layers, supply is "
         f"{수(공급/1e6,4,' m')} of routing.",
         "Layers the power grid did not take. That subtraction is where T18 and this "
         "chapter meet: stripes consume tracks."),
        (f"Demand is {넷수:,} nets × {수(평균넷길이,3,' µm')} average = "
         f"{수(수요/1e6,4,' m')}.",
         "<b>The average net length is the weak link in this estimate</b> and it is "
         "assumed. It is also the only quantity here that a real flow measures rather "
         "than predicts."),
        (f"Global ratio: {수(수요/공급,3)}.",
         "Comfortably below 1 — and the next paragraph explains why that tells you "
         "almost nothing."),
    ]))

    줄 = []
    for 평균 in (20.0, 30.0, 45.0, 60.0, 80.0):
        r = 배선수요(평균) / 공급
        줄.append([수(평균, 3, " µm"), 수(배선수요(평균) / 1e6, 4, " m"), 수(r, 3),
                   "routable on average" if r < 0.7 else
                   ("marginal" if r < 1.0 else "<b>impossible</b>")])
    c.날것(표("How much the conclusion depends on the one assumed number",
        ["Assumed average net length", "Demand", "Demand ÷ supply", "Reading"], 줄))

    c.날것(짚기(f"""Two honest statements about the table. First, the estimate is
    <b>dominated by an assumption</b>: a factor of four in the average net length moves
    the answer from comfortable to impossible, and no amount of care in the geometry
    changes that. Second, and more important: <b>the global ratio is the wrong
    quantity</b>. Routing fails locally. A design at a global
    {수(수요/공급,3)} can have gcells above 1.0 in a region a hundred microns across,
    and those gcells are what decides whether the router finishes. This is the same
    structural error as T18's uniform power map — an average that is right everywhere
    and useful nowhere."""))

    c.날것(개념(
        "렌트 법칙 (Rent's rule) — why routing demand grows faster than area",
        """<p>Empirically, if you draw a boundary around <i>N</i> randomly chosen
        connected cells in a real design, the number of connections crossing that
        boundary is <b>T = k·N<sup>p</sup></b>, with <i>p</i> typically between 0.5 and
        0.75 for logic. The exponent is a measure of how much a design communicates
        with itself.</p>
        <p>The consequence for routing is direct. A region of area A holds N ∝ A cells
        and must carry T ∝ N<sup>p</sup> connections across its boundary, while the
        boundary itself offers track capacity ∝ √A ∝ N<sup>0.5</sup>. For any
        <b>p &gt; 0.5</b> — that is, for essentially all real logic — demand outgrows
        supply as the block gets bigger. <b>This is why routing does not get easier
        when you add metal layers to a growing design, and why hierarchy exists.</b></p>
        <p>It is an empirical law, not a theorem, and it should be used as one: measure
        <i>p</i> on your own netlists by counting crossings for randomly chosen
        partitions, and be suspicious of a quoted value.</p>""",
        어디에="Estimating whether a block should be partitioned, and predicting "
             "congestion before a placement exists.",
        언제="At the architecture stage, when block sizes are still negotiable — "
            "which is the only time the answer can be acted on cheaply (T17).",
        어떻게="Partition the netlist at several sizes, count boundary nets, fit "
             "log T against log N. A p above about 0.7 says the block will be "
             "congestion-limited and should be split or given more metal.",
        산업코드="""# Measuring p on your own netlist instead of quoting a textbook value:
#   N      T (crossings)     log-log fit -> p
#   100        68
#   1000      271
#   10000    1090            p ~ 0.60,  k ~ 4.3
# Then: a 100k-instance block implies ~ 4.3 * 100000^0.60 crossings at the
# top level -- compare with the tracks its perimeter actually offers.""",
        주의="""Rent's rule describes <i>average</i> connectivity. A design with a
            broadcast bus or a large crossbar violates it locally in exactly the place
            that will fail, so a good global p is not a routability guarantee — it is a
            reason to look at the structures the law does not describe."""))

    # ------------------------------------------------------------------
    c.절("T19.3 Clock-tree synthesis: why insertion delay costs skew")

    c.날것(정의("삽입지연 (insertion delay) · 클럭스큐 (clock skew)",
        "<b>Insertion delay</b> (or latency) is the time from the clock's entry point "
        "to a flop's clock pin. <b>Skew</b> is the difference in insertion delay "
        "between two flops. Setup and hold analysis cares about skew; latency, on its "
        "own, cancels out of the launch-capture comparison — which is why the "
        "textbook answer is 'latency does not matter'. The textbook answer is wrong in "
        "silicon, for the reason computed next."))

    c.날것(그림(sch.블록도(
        [["Clock root", "Level 1 buffers", "Level 2 buffers", "Flops"]],
        설명={"Clock root": "one source",
             "Level 1 buffers": f"fanout {팬아웃}",
             "Level 2 buffers": "…repeat until\nevery flop is fed",
             "Flops": f"{플롭수:,} sinks"}),
        f"A buffered clock tree. With a fanout of {팬아웃} and {플롭수:,} sinks it is "
        f"{클럭단수()} levels deep and holds about {클럭버퍼수():,} buffers — every one "
        f"of which is a source of the variation computed below."))

    c.날것(유도("How on-chip variation turns latency into skew", [
        ("Two flops share the clock path up to the point where the tree branches.",
         "By construction — the tree is a tree. Call the shared fraction the "
         f"<b>common path</b>; here it is {수(100*공통몫,3,' %')} of the latency "
         "(assumed)."),
        ("OCV analysis derates the launch path late and the capture path early.",
         "It must assume the worst combination of process and environment variation "
         "between two points on the die, because STA has no way to know which "
         "combination silicon will present."),
        (f"With ±7 % derates, the late path is ×{수(늦은배수,3)} and the early path "
         f"×{수(이른배수,3)}.",
         "<b>Assumed</b> derate values; real ones come from the foundry and depend on "
         "distance and on the number of stages in the path."),
        (f"Effective skew = 1.00×{수(늦은배수,3)} − {수(공통몫,3)}×{수(이른배수,3)} = "
         f"{수(100*OCV스큐비(),4,' %')} of the insertion delay.",
         "The common part does not cancel, because the two derates applied to it are "
         "different. Only <b>common-path pessimism removal</b> gives that part back, "
         "and only for the path that is genuinely shared."),
        (f"So a tree whose real skew is 2 % of latency is analysed as though it were "
         f"{수(100*OCV스큐비(),3,' %')}.",
         "<b>This is the answer to 'why does latency matter'.</b> Latency is "
         "multiplied by the derate difference and reappears as skew — so a deep tree "
         "costs frequency even when it is perfectly balanced."),
    ]))

    줄 = []
    for 지연 in (200e-12, 400e-12, 600e-12, 900e-12, 1.2e-9):
        유효 = OCV스큐비() * 지연
        줄.append([수(지연 * 1e12, 4, " ps"), 수(0.02 * 지연 * 1e12, 4, " ps"),
                   수(유효 * 1e12, 4, " ps"),
                   수(100 * 유효 / (1 / 주파수), 3, " %")])
    c.날것(표(f"What insertion delay costs, at {수(주파수/1e6,3,' MHz')} "
        f"({수(1e12/주파수,4,' ps')} period)",
        ["Insertion delay", "Real skew (2 %)", "Skew after OCV derate",
         "of the clock period"], 줄))

    c.날것(짚기(f"""Read the last column. At {수(1.2e-9*1e12,4,' ps')} of insertion
    delay, OCV alone consumes
    {수(100*OCV스큐비()*1.2e-9/(1/주파수),3,' %')} of the period before a single gate
    has switched. <b>The engineering target in CTS is therefore not skew alone but
    latency and skew together</b>, and the most effective fix is usually structural:
    fewer levels, a shorter path from the root, or a different distribution
    topology."""))

    c.날것(표("Three clock distribution structures, and what each one buys",
        ["Structure", "Skew", "Power and area", "When to use it"],
        [["<b>Buffered tree</b> (CTS default)",
          "Good, and controllable per-sink; latency grows with depth",
          "Lowest — only the buffers the fanout requires",
          "Nearly always. It is the only one that supports useful skew and gating"],
         ["<b>H-tree</b>",
          "Excellent by construction — every leaf is the same distance from the root",
          "Higher; it ignores where the sinks actually are",
          "Regular arrays where the sinks really are on a grid: an ADC's comparators, "
          "a mesh of identical tiles"],
         ["<b>Clock mesh</b>",
          "Lowest. The mesh shorts the leaves together, so local variation averages "
          "instead of accumulating",
          "Highest — a large, always-switching capacitance, and difficult to analyse "
          "because the mesh has no unique path",
          "High-frequency cores where skew is the binding constraint and the power is "
          "worth paying"]]))

    c.날것(개념(
        "유용 스큐 (useful skew) — spending the clock deliberately",
        """<p>Skew is not only an error. If a path from A to B is tight, delivering B's
        clock <i>later</i> gives that path more time — and takes the same amount from
        B's own outgoing path. CTS tools do this deliberately: they solve for a set of
        arrival times that maximises the worst slack across the design rather than
        equalising arrivals.</p>
        <p>It is genuinely free frequency, and it has a genuine cost: <b>the design now
        depends on the clock tree being what the analysis assumed</b>. A tree balanced
        to zero skew degrades gracefully when a buffer is slower than modelled; a tree
        carrying 80 ps of useful skew on a critical path degrades into a hold violation,
        which is not fixable by slowing the clock.</p>""",
        어디에="Inside CTS and again in post-CTS optimisation.",
        언제="When a handful of paths block frequency and everything else has margin "
            "— the classic case for it.",
        어떻게="Bound it. Allow useful skew up to a fraction of the period, keep hold "
             "margin explicitly larger on the paths that use it, and re-check at every "
             "corner, because the skew and the path delay do not track each other "
             "across corners.",
        산업코드="""# The report to read after CTS, per critical endpoint:
#   endpoint        latency   useful skew   setup slack   hold slack
#   u_alu/acc[7]     412 ps      +80 ps        +12 ps        +9 ps   <- thin
#   u_ctl/st[1]      398 ps        0 ps        +95 ps       +60 ps
# An endpoint living on useful skew with 9 ps of hold margin is a silicon
# failure waiting for a slow corner. Bound the skew, not just the slack.""",
        주의="""Useful skew and clock gating interact badly if the gating cell sits on
            a path carrying skew: enabling and disabling changes the loading on the
            branch and therefore the skew it delivers. Keep gating cells above the
            point where useful skew is applied."""))

    c.날것(개념(
        "클럭 게이팅 (clock gating) and the latch that makes it legal",
        f"""<p>A clock network switches every cycle whether or not the flops it feeds
        have anything to do. Gating it off is the single largest dynamic-power lever in
        a digital design. The circuit that does it — the <b>integrated clock-gating
        cell</b> (CGIC) — is a latch followed by an AND, and the latch is not
        optional.</p>
        <p><b>Why the latch.</b> ANDing the enable directly with the clock produces a
        glitch whenever the enable changes while the clock is high: a partial pulse that
        is long enough to be seen by a flop and short enough to violate its minimum
        pulse width. The latch is transparent while the clock is <i>low</i>, so the
        enable can only change during the low phase and is held stable for the whole
        high phase. The gated clock is then always a full pulse or no pulse.</p>
        <p>The clock network of the block assumed here is {플롭수:,} flop clock pins
        plus about {클럭버퍼수():,} buffers — roughly
        {수(1e15*(플롭수*클럭부하+클럭버퍼수()*버퍼부하),4,' fF')} of capacitance
        switching at {수(주파수/1e6,3,' MHz')}, which is
        {수(1e3*클럭전력(),4,' mW')}. Gating it off 60 % of the time saves
        {수(1e3*(클럭전력()-클럭전력(0.6)),4,' mW')}.</p>
        <p><b>Check that against the block, not against itself.</b> T18 assumed the
        whole block draws {수(1e3*블록전력,4,' mW')}. The clock network computed here
        is {수(100*클럭전력()/블록전력,3,' %')} of that &mdash; high, and it should be:
        this is an ungated tree feeding {플롭수:,} flops, which is precisely the design
        that motivates gating. Gating 60 % of it returns
        {수(100*(클럭전력()-클럭전력(0.6))/블록전력,3,' %')} of the whole block's
        power. Had the fraction come out at 5 % or at 90 %, the right response would be
        to distrust the capacitance assumptions rather than to report the saving.</p>""",
        어디에="Inserted by synthesis wherever the RTL has an enable, and again by "
             "hand where the RTL does not express one.",
        언제="Everywhere. The question is not whether to gate but at what granularity "
            "— one CGIC per 8 flops is typical; one per flop costs more than it saves.",
        어떻게="Write the RTL so the enable is visible (<code>if (en) q &lt;= d;</code> "
             "rather than a recirculating mux), then check the report for the "
             "percentage of flops actually gated. Ungated flops in a low-power design "
             "are usually an RTL style problem, not a tool problem.",
        산업코드="""// The RTL that lets the tool insert a CGIC:
always_ff @(posedge clk) if (en) q <= d;          // gateable

// The RTL that prevents it -- the clock still toggles every cycle:
always_ff @(posedge clk) q <= en ? d : q;         // recirculating mux

// Both simulate identically. Only the first one saves power, and the
// difference does not appear anywhere in functional verification.""",
        주의="""A gated clock is a new clock as far as CDC and STA are concerned. It
            needs its own constraint, and the enable itself must be timed — an enable
            that arrives late enough to violate the latch's setup produces exactly the
            glitch the latch was there to prevent."""))

    # ------------------------------------------------------------------
    c.절("T19.4 Routing, in two passes and a repair loop")

    c.날것(표("Why routing is not one algorithm",
        ["Pass", "Works on", "Decides", "What it deliberately ignores"],
        [["<b>Global route</b>", "The gcell grid",
          "Which gcells each net passes through, and on which layers",
          "Exact wire positions, most design rules — it is a capacity problem, not a "
          "geometry problem"],
         ["<b>Detail route</b>", "Real tracks and vias inside each gcell",
          "The actual metal: every segment, every via, every jog",
          "Nothing — this pass must produce DRC-clean geometry"],
         ["<b>Search and repair</b>", "The remaining violations",
          "Rip up the offending wires and route them again, with the violation as a "
          "penalty", "Optimality. It is a local repair loop, and it is iterative "
          "because each repair can create new violations"]]))

    c.날것(짚기("""The split exists because the two problems have different shapes.
    Global routing is a flow problem on a graph of a few thousand nodes and is solved
    nearly optimally. Detail routing is a geometry problem with hundreds of rules, in
    a space far too large to search — so it is solved greedily, net by net, and the
    greediness is exactly what search-and-repair afterwards cleans up."""))

    열 = 수리반복(4200, 0.45)
    줄 = [[str(i), 수(int(round(v)), 5),
           수(int(round(v - 열[i])) if i < len(열) - 1 else 0, 5)]
          for i, v in enumerate(열[:8])]
    c.날것(표("A converging repair loop: each pass removes 55 % of what is left",
        ["Iteration", "Violations open", "Removed this pass"], 줄))

    c.날것(예제("Is this repair loop going to finish?",
        "After detail routing a block reports 4,200 DRC violations. Successive "
        "search-and-repair passes report 4,200 → 2,310 → 1,290 → 980 → 910 → 890.",
        "The first two ratios are about 0.55 and 0.56 — a clean geometric decay. The "
        "last three are 0.76, 0.93, 0.98: the decay has stopped. Fit the tail rather "
        "than the head, because the tail is what decides termination.",
        "<b>It will not finish.</b> A ratio approaching 1 means the remaining "
        "violations are not being repaired but moved — the same congested region "
        "handed back and forth. The residue of roughly 890 is structural: not enough "
        "track supply where those nets have to go.",
        "The trivial explanation must be killed before concluding anything structural: "
        "confirm the violations are the <b>same</b> ones, in the same place, and not a "
        "fresh set each pass. Diff the violation coordinates between passes. If they "
        "move, the loop is thrashing on a global shortage; if they sit still, it is one "
        "local cause — often a macro pin that cannot be reached (T15.3).",
        덧="""The remedy is never another repair pass. It is upstream: lower "
        utilisation in that region, spread the placement, add a routing layer, or "
        change the pin access. That is T17's loop-cost arithmetic arriving in "
        practice — the fix is cheap where the cause is and expensive where the "
        symptom is."""))

    c.날것(개념(
        "안테나 위반 (antenna violation) — a rule that is about manufacturing, not "
        "about the circuit",
        """<p>During etch, a long metal segment connected to a gate but not yet
        connected to any diffusion acts as a charge collector; the accumulated charge
        discharges through the thin oxide and damages it. The rule bounds the ratio of
        connected metal area to gate area <b>at every intermediate stage of
        manufacturing</b>, not in the finished chip.</p>
        <p>That last clause is what makes it confusing: a layout can be antenna-clean
        when complete and violate the rule at metal 2, because metal 3 — which would
        have connected the segment to a diode — does not exist yet at that point in the
        process.</p>
        <p>The two fixes are to break the long segment by jumping to a higher layer
        (so the collector is never large on any one layer) or to add a small diode that
        provides a discharge path. Routers insert both automatically; the reason to
        understand it is that the fixes cost area and delay on nets that are usually
        already critical.</p>""",
        어디에="After detail routing, as part of physical verification (T20).",
        언제="Every time. It is not optional and not negotiable with the foundry.",
        어떻게="Let the router fix it, then look at <b>where</b> it had to: a cluster "
             "of antenna fixes marks a net that is long, on one layer, and reaching a "
             "gate — often a clock or a reset, which are precisely the nets where the "
             "added diode capacitance is least welcome.",
        주의="""An antenna diode on a clock leaf adds capacitance to a branch CTS
            already balanced, and it is added <b>after</b> CTS. Re-check skew after
            antenna fixing rather than assuming the tree survived it."""))

    # ------------------------------------------------------------------
    c.절("T19.5 What to do with this on Monday")

    c.날것(쓰는자리([
        ["배치 · 합법화 · HPWL · 타이밍주도배치", "Every placement run",
         "Whether the jump at legalisation is telling you the floorplan is too dense"],
        ["혼잡도 · 트랙 · gcell · 렌트법칙", "Before routing, and before partitioning",
         "Whether this block can be routed at all at this size"],
        ["클럭트리합성 · 삽입지연 · 클럭스큐 · 유용스큐 · 클럭메시 · H트리",
         "After placement", "How much of the period the clock network consumes "
         "before any logic runs"],
        ["클럭게이팅 · CGIC", "RTL, and then the gating report",
         "The largest single dynamic-power lever, and whether your RTL style allows it"],
        ["전역배선 · 상세배선 · 탐색수리 · 안테나위반", "After CTS",
         "Whether the repair loop converges, and what to change upstream if it "
         "does not"],
    ]))

    c.글(f"""The number to carry is the OCV multiplication:
    {수(100*OCV스큐비(),4,' %')} of insertion delay reappears as analysed skew under
    ±7 % derates with a {수(100*공통몫,3,' %')} common path. It is the reason a clock
    tree is engineered for latency as well as balance, the reason clock meshes exist
    despite their power, and the quantitative content of the advice to keep the clock
    tree shallow.""")

    c.글("""The geometry now exists and is, as far as the router is concerned, finished.
    Whether it may be manufactured is a separate question, answered by a separate set of
    tools, and that is the next chapter.""")

    return c.완성()
