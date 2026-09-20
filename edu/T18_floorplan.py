# -*- coding: utf-8 -*-
"""T18 -- Floorplan and power plan: the geometry everything else sits on."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch
import sch_flow

# ---------------------------------------------------------------------------
# 이 장이 쓰는 수 -- 전부 여기서 한 번만 정하고 아래에서 계산한다.
# 표준셀 자리(SITE)는 **가정이 아니다**: 실제 라이브러리의 LEF 가 이 꼴이다
#   SITE coreSite  CLASS CORE ;  SIZE 0.660 BY 5.040 ;
# 나머지(공정 상수)는 가정이고, 쓰는 자리마다 가정이라고 적는다.
# ---------------------------------------------------------------------------
자리폭, 행높이 = 0.660, 5.040        # µm -- LEF SITE
평균자리수 = 4                        # 셀 하나가 차지하는 자리 수 (가정)
인스턴스 = 100_000
점유율 = 0.70
VDD, 전력 = 1.8, 0.350               # V, W (T19 가 이 중 클럭망 몫을 계산한다)
Rs_상층, Rs_M1 = 0.040, 0.400        # Ω/sq (가정: 두꺼운 상층 금속 / M1)
W_M1 = 0.600                          # µm, 셀 행의 전원 레일 폭 (가정)
Jmax = 2.0                            # mA/µm, 상층 금속 EM 한계 (가정, T14 블랙식)
IR예산비 = 0.03

셀면적 = 평균자리수 * 자리폭 * 행높이          # µm^2
총셀면적 = 인스턴스 * 셀면적                    # µm^2
코어면적 = 총셀면적 / 점유율                    # µm^2
코어변 = math.sqrt(코어면적)                    # µm, 정사각 코어
행수 = 코어변 / 행높이
전류 = 전력 / VDD                               # A
IR예산 = IR예산비 * VDD                         # V


def 스트라이프_IR폭(N):
    """N 줄일 때 IR 예산을 맞추는 스트라이프 한 줄의 폭 (µm).

    한 줄이 I/N 을 나르고 부하가 고르게 걸리며 양끝에서 먹인다:
    강하 = (Rs·L/w)·(I/N)/8.  이것을 예산과 같게 놓고 w 로 푼다.
    """
    return Rs_상층 * 코어변 * (전류 / N) / (8 * IR예산)


def 스트라이프_EM폭(N):
    """EM 한계를 맞추는 폭.  양끝 급전이므로 최대 전류는 I/(2N) 이다."""
    return (전류 / (2 * N)) * 1e3 / Jmax


def 레일강하(N):
    """셀 행의 레일에서 생기는 강하 -- 스트라이프 사이 간격 p 에 제곱으로 는다."""
    p = 코어변 / N
    I_행 = 전류 * (행높이 * p) / 코어면적          # 그 구간이 먹는 전류
    return Rs_M1 * p / W_M1 * I_행 / 8


def 격자해(N, 조각=400):
    """닫힌 꼴을 **안 쓰고** 같은 강하를 구한다 -- 키르히호프를 그냥 푼다.

    양끝이 0 V 로 묶인 저항 사다리에 전류를 고르게 뽑아 내고 마디 전압을
    선형 연립으로 푼다.  유도에 나온 식은 여기 한 줄도 안 들어간다.
    """
    import numpy as np
    w = 스트라이프_IR폭(N)
    r = Rs_상층 * (코어변 / 조각) / w
    i = (전류 / N) / 조각
    n = 조각 - 1
    A = np.zeros((n, n))
    b = np.full(n, -i)
    for k in range(n):
        A[k, k] = -2 / r
        if k:
            A[k, k - 1] = 1 / r
        if k + 1 < n:
            A[k, k + 1] = 1 / r
    return float(abs(np.linalg.solve(A, b)).max())


def 열점강하(N, 몫=0.30, 면적몫=0.10):
    """전류의 `몫` 이 면적의 `면적몫` 에 몰렸을 때 그 자리의 레일 강하.

    고른 부하 모형이 스트라이프 수에 거의 안 움직인다는 것을 보고 나서
    **왜 그래도 촘촘히 까는가**를 재는 자리다.
    """
    p = 코어변 / N
    열점변 = math.sqrt(면적몫 * 코어면적)
    구간 = min(p, 열점변)
    I_행 = (전류 * 몫) * (행높이 * 구간) / (열점변 ** 2)
    return Rs_M1 * 구간 / W_M1 * I_행 / 8


def ch_floorplan():
    c = 장(
        "T18", "Floorplan and Power Plan — The Geometry Everything Sits On",
        "Placement, clock and routing all optimise inside a box somebody drew. "
        "This chapter computes the box.",
        쓰는것=["플로어플랜", "구현흐름", "LEF", "DEF", "사인오프", "전압강하",
              "목표임피던스", "PDN", "디캡", "동시스위칭잡음", "일렉트로마이그레이션",
              "블랙식", "하드매크로", "핀배치", "패드용량", "클램프"],
        내놓는것=["다이", "코어영역", "점유율", "종횡비", "표준셀행", "SITE",
                "전원그리드", "파워링", "파워스트라이프", "스페셜라우트",
                "IO패드링", "코너셀", "IO필러", "필러셀", "탭셀", "킵아웃",
                "패드제한다이", "코어제한다이"],
        특허="""Power-grid synthesis — deciding stripe pitch and width automatically
        from a power map rather than from a designer's rule of thumb — is an active
        area, as is <b>floorplanning by machine learning</b>, where a model proposes
        macro placements. Both are attempts to automate the one stage of the flow that
        is still mostly judgement, and both are judged by exactly the numbers this
        chapter computes: IR drop, congestion and area.""")

    c.글("""Every later stage optimises <i>inside</i> a boundary that this stage draws.
    Placement cannot use area the floorplan did not allocate; the clock tree cannot be
    shorter than the distance between the flops the floorplan separated; routing cannot
    use tracks the power grid consumed. <b>The floorplan is the only stage whose
    mistakes cannot be fixed downstream</b> — which is why it is drawn first and why
    almost nothing about it is automatic.""")

    # ------------------------------------------------------------------
    c.절("T18.1 From a gate count to a rectangle")

    c.날것(그림(sch_flow.플로어플랜(),
        "The floorplan, from the outside in: the pad ring with its corner cells "
        "and fillers, two power rings, the stripes that cross the core, and the "
        "rows the cells will sit on. Every element in this drawing is sized by a "
        "calculation in this chapter."))

    c.날것(정의("자리 (SITE) and the 표준셀 행 (standard-cell row)",
        "A digital library does not place cells anywhere. It defines a <b>site</b> — "
        "the smallest placement unit — and cells are integer multiples of it. Rows are "
        "one site high and run the width of the core; a cell snaps to a site boundary "
        "in a row. Everything about digital area arithmetic follows from this: the "
        "layout is a <b>tiling</b>, not a free placement."))

    c.날것(그림(sch_flow.표준셀행(),
        "Rows, sites and the two supply rails that run the length of every row. "
        "A cell occupies a whole number of sites and snaps to a site boundary; "
        "that is what makes digital area arithmetic a tiling problem."))

    c.날것(표("A real SITE definition, and what each number means",
        ["LEF", "Value here", "What it decides"],
        [["<code>SITE coreSite</code>", "the name", "Which rows this cell may sit in; "
          "a library can define more than one (e.g. a double-height row)"],
         ["<code>CLASS CORE</code>", "core", "Core cells, as opposed to <code>PAD</code> "
          "sites in the I/O ring"],
         ["<code>SIZE 0.660 BY 5.040</code>",
          f"{수(자리폭,3,' µm')} × {수(행높이,4,' µm')}",
          "Row height (fixed by the library, and the reason cell area is quantised) "
          "and the placement grid in x"]]))

    c.날것(유도("Core area from an instance count", [
        (f"One site is {수(자리폭,3,' µm')} × {수(행높이,4,' µm')} = "
         f"{수(자리폭*행높이,4,' µm²')}.",
         "Read straight off the LEF above."),
        (f"Take an average cell of {평균자리수} sites, so "
         f"{수(셀면적,4,' µm²')} per instance.",
         "<b>Assumed.</b> The real figure comes from the synthesis area report and "
         "differs per design — a datapath-heavy block is wider, a control block "
         "narrower."),
        (f"{인스턴스:,} instances therefore occupy "
         f"{수(총셀면적/1e6,4,' mm²')} of cell area.",
         "Multiplication. This is cell area only — no routing space, no power grid, "
         "no gaps."),
        (f"At {수(100*점유율,3,' %')} utilisation the core is "
         f"{수(코어면적/1e6,4,' mm²')}.",
         "Utilisation is cell area ÷ core area. The rest is deliberately empty so the "
         "router has somewhere to go and the ECO stage has somewhere to put a buffer."),
        (f"A square core is {수(코어변,4,' µm')} on a side, which is "
         f"{수(행수,4)} rows.",
         "Square minimises the longest wire for a given area, so it is the default "
         "starting point — not a requirement."),
    ]))

    c.날것(개념(
        "점유율 (utilisation) — the number that trades area against everything else",
        f"""<p>Utilisation is the fraction of the core occupied by cells. It is the
        floorplan's single most consequential knob, and it is <b>not</b> a quality
        metric: high utilisation is not good engineering, it is a bet.</p>
        <p>Raising it shrinks the die and therefore the cost per part. It also removes
        the space that routing, clock buffers, hold-fix buffers and post-route ECOs all
        need. A block that is routable and closes timing at
        {수(100*점유율,3,' %')} can become unroutable at 80 % — not gradually, but as
        a cliff, because congestion is a threshold phenomenon (X14).</p>
        <p>The honest way to choose it is to <b>measure</b>: run the flow at several
        values and look at where routing time and DRC-violation count start rising
        superlinearly. That knee is the design's limit, and it moves with the
        design.</p>""",
        어디에="Chosen at the floorplan, before any placement exists.",
        언제="Revisited whenever the design grows — an RTL change of 10 % in gate "
            "count changes utilisation, and nobody reruns the floorplan for it.",
        어떻게="Start low (60–70 %) for a first pass so that the flow converges at "
             "all, then raise it once timing closes, watching congestion maps rather "
             "than the utilisation number itself.",
        산업코드="""# The floorplan sweep that should exist in every block's history.
#  util   route time   DRC after route   worst slack   die
#  0.60      9 h            0               +60 ps    1.90 mm^2
#  0.70     14 h            0               +40 ps    1.63 mm^2
#  0.75     22 h           41               -15 ps    1.52 mm^2   <- knee
#  0.80     49 h          890              -120 ps    1.43 mm^2
# The knee, not the smallest die, is the answer.""",
        주의="""Utilisation computed by the tool usually excludes macro area and
            blockages. Two flows quoting '70 %' can mean different things; compare
            <b>cell area ÷ (core area − macro area)</b> explicitly before believing a
            comparison between blocks."""))

    # ------------------------------------------------------------------
    c.절("T18.2 The ring of pads, and which dimension is really limiting")

    c.날것(그림(sch.블록도(
        [["I/O pad ring", "Power ring", "Stripes + rails", "Core rows"]],
        설명={"I/O pad ring": "pads, fillers,\ncorner cells",
             "Power ring": "around the core,\nfed from the pads",
             "Stripes + rails": "special route,\nbefore signals",
             "Core rows": "placement snaps\nto SITE"}),
        "The floorplan from the outside in. Each layer feeds the next: the pads feed "
        "the ring, the ring feeds the stripes, the stripes feed the row rails, the "
        "rails feed the cells."))

    c.날것(표("The cells in the I/O ring that are not I/O",
        ["Cell", "What it is for", "What happens without it"],
        [["<b>Corner cell</b>",
          "Carries the pad ring's power and signal buses around the 90° turn",
          "The ring's supply buses are four disconnected segments; the pads on one "
          "side have no return path"],
         ["<b>I/O filler</b>",
          "Fills the gaps between pads so the ring's buses are continuous and the "
          "implant and well layers are legal",
          "Broken supply bus and a DRC forest at every gap"],
         ["<b>Filler cell</b> (core)",
          "Same idea inside the core: continuity of the n-well and the power rails "
          "between placed cells",
          "Floating well regions and rail discontinuities — LVS and DRC failures, "
          "found late"],
         ["<b>Tap cell</b>",
          "Ties the well and substrate to supply at a bounded spacing",
          "Latch-up (T16). The spacing is a foundry rule, not a preference"]]))

    c.날것(개념(
        "패드 제한 다이 (pad-limited) vs 코어 제한 다이 (core-limited)",
        """<p>Two independent things set the die size: the area the logic needs, and the
        perimeter the pads need. A die is <b>core-limited</b> if the logic sets the size
        and the pads fit comfortably around it; it is <b>pad-limited</b> if the pad
        count forces a perimeter larger than the logic requires, leaving the core partly
        empty.</p>
        <p>The distinction decides what is worth optimising. In a core-limited die,
        every gate you remove is money. In a pad-limited die, removing gates is
        <b>free of charge and free of benefit</b> — the die does not shrink — and the
        only levers are pad pitch, staggered or area-array pads, and reducing pin
        count.</p>""",
        어디에="The very first floorplan estimate, before any RTL is final.",
        언제="As soon as the pin list exists. It is one multiplication and it changes "
            "what the team should spend its time on for the next six months.",
        어떻게="Compute the perimeter the pads need (pad count × pitch, allowing for "
             "the four corner cells) and the side of the square core the logic needs. "
             "Whichever is larger sets the die.",
        산업코드="""# One line of arithmetic that reorders a project's priorities:
#   pads = 120,  pad pitch = 50 um  ->  perimeter = 6000 um -> side = 1500 um
#   logic needs a core side of                                       1278 um
#   => PAD-LIMITED. Shrinking the netlist buys nothing. Reduce pins,
#      or stagger the pads, or accept the empty core and fill it with decap.""",
        주의="""An empty core in a pad-limited die is not waste if you use it: it is
            the cheapest decoupling capacitance you will ever get (T13), and it costs
            only the fill cells."""))

    _패드수, _패드피치 = 120, 50.0
    _패드변 = _패드수 * _패드피치 / 4
    c.날것(예제("Is this die pad-limited?",
        f"{_패드수} pads at {수(_패드피치,3,' µm')} pitch, and the logic of T18.1 "
        f"needing a core side of {수(코어변,4,' µm')}.",
        f"Perimeter needed by the pads is {_패드수}×{수(_패드피치,3,' µm')} = "
        f"{수(_패드수*_패드피치,5,' µm')}, i.e. a side of {수(_패드변,4,' µm')}. "
        f"Compare with the core side.",
        ("<b>Pad-limited</b>" if _패드변 > 코어변 else "<b>Core-limited</b>") +
        f" — the pads need {수(_패드변,4,' µm')} a side against the logic's "
        f"{수(코어변,4,' µm')}, so the " +
        ("pads set the die and there is "
         f"{수((_패드변**2-코어면적)/1e6,3,' mm²')} of core the logic does not use."
         if _패드변 > 코어변 else "logic sets the die."),
        "The pad pitch is not free to choose: it is set by the package's bond-wire or "
        "bump capability, and a pitch that the package cannot assemble is not a "
        "floorplan, it is a wish. Ask the package house for the number before the "
        "arithmetic, not after.",
        덧="""The same comparison decides whether to use an <b>area-array</b> (flip-chip)
        pad arrangement, which removes the perimeter constraint entirely at the cost of
        a more expensive package and a different ESD strategy (T16)."""))

    # ------------------------------------------------------------------
    c.절("T18.3 Sizing the power grid — and what actually forces it to be dense")

    c.글(f"""The core draws {수(전류*1e3,4,' mA')} at {수(VDD,2,' V')} for the
    {수(전력*1e3,3,' mW')} assumed above. That current has to arrive through metal,
    and the metal has to satisfy two separate constraints that have nothing to do with
    each other: the <b>voltage</b> must not sag more than the budget (T13), and the
    <b>current density</b> must not exceed the electromigration limit that T14's Black
    equation sets for the required lifetime. Sizing the grid means satisfying both, and
    knowing which of the two is binding.""")

    c.날것(유도("IR drop along a stripe fed from both ends", [
        ("A stripe of length L and width w has resistance R = R<sub>s</sub>L/w.",
         "Sheet resistance times the number of squares. R<sub>s</sub> is a process "
         "constant per metal layer."),
        ("The load is not at the end; it is distributed along the stripe.",
         "The cells that draw current are spread over the rows the stripe crosses."),
        ("Feed it from both ends and let the current per unit length be i = I/L.",
         "Both ends is what a power ring gives you — this is why the ring exists."),
        ("Current at distance x from one end is I/2 − i·x.",
         "Half the total enters each end; it is consumed as it travels."),
        ("Drop to the centre is ∫₀<sup>L/2</sup>(I/2 − i x)(R<sub>s</sub>/w)dx "
         "= R·I/8.",
         "Elementary integral; the L² terms collect into R = R<sub>s</sub>L/w."),
        ("So the worst drop on the stripe is <b>R·I/8</b>, at the centre.",
         "Compare with R·I for an end-fed point load: distributing the load and "
         "feeding both ends is a factor of 8. That factor is the whole reason a grid "
         "is a grid."),
    ]))

    줄 = []
    for N in (2, 4, 8, 16, 32):
        w_ir, w_em = 스트라이프_IR폭(N), 스트라이프_EM폭(N)
        줄.append([str(N), 수(w_ir, 3, " µm"), 수(w_em, 3, " µm"),
                   "<b>EM</b>" if w_em > w_ir else "<b>IR</b>",
                   수(N * max(w_ir, w_em), 4, " µm"),
                   수(100 * N * max(w_ir, w_em) / 코어변, 3, " %")])
    c.날것(표(f"Stripe width required, for a {수(100*IR예산비,2,' %')} "
        f"({수(IR예산*1e3,3,' mV')}) IR budget and an EM limit of "
        f"{수(Jmax,2,' mA/µm')}",
        ["Stripes", "Width for IR", "Width for EM", "Which binds",
         "Total metal width", "of the core width"], 줄))

    c.날것(짚기(f"""Look at the last two columns: <b>the total metal width does not
    change with the number of stripes.</b> Both constraints scale as 1/N per stripe, so
    N stripes of width w/N cost exactly what one stripe of width w costs. The naive
    conclusion — "the stripe count is free, pick anything" — is wrong, and finding out
    <i>why</i> it is wrong is the point of the rest of this section. The uniform-load
    model above is missing the path from the stripe to the cell."""))

    c.날것(유도("What the stripe count actually buys", [
        ("A cell does not connect to a stripe; it connects to the rail in its row.",
         "Rails run horizontally in every row at the library's row pitch; stripes run "
         "vertically over them and drop down through vias."),
        ("So the current travels along the rail from the nearest stripe, over a "
         "distance up to half the stripe pitch p = L/N.",
         "The rail is fed from the stripes on both sides of it, which is the same "
         "both-ends geometry as before, at a smaller scale."),
        ("The rail segment between two stripes carries the current of the area it "
         "serves: I·(row height × p)/L².",
         "Uniform current density over the core, times the area of that segment."),
        ("Its drop is (R<sub>s,M1</sub>·p/w<sub>rail</sub>)·I<sub>seg</sub>/8, "
         "which is ∝ p².",
         "One factor of p from the resistance, one from the current the longer segment "
         "collects. <b>This</b> is where N appears."),
        (f"At N = 4 that is {수(레일강하(4)*1e3,3,' mV')}; at N = 1, "
         f"{수(레일강하(1)*1e3,3,' mV')}.",
         "Computed from the numbers at the top of this chapter. Still small — which "
         "is an honest result and not the one most people expect."),
    ]))

    c.날것(표("The drop, decomposed — uniform load",
        ["Stripes", "On the stripe", "On the row rail", "Total", "Budget"],
        [[str(N), 수(IR예산 * 1e3, 3, " mV"), 수(레일강하(N) * 1e3, 3, " mV"),
          수((IR예산 + 레일강하(N)) * 1e3, 4, " mV"), 수(IR예산 * 1e3, 3, " mV")]
         for N in (1, 2, 4, 8, 16)]))

    _격자 = 격자해(4)
    c.날것(짚기(f"""<b>The independent control.</b> The stripe drop above comes from the
    integral in the derivation. To check the algebra rather than trust it, the same
    stripe is also solved as a 400-segment resistive ladder with both ends grounded and
    the current drawn uniformly — Kirchhoff's laws and a linear solve, using none of the
    formula. It gives {수(_격자*1e3,5,' mV')} against the closed form's
    {수(IR예산*1e3,5,' mV')}, a disagreement of
    {수(100*abs(_격자-IR예산)/IR예산,2,' %')}. That check validates the
    <i>arithmetic</i>. It does not validate the <i>model</i>: both assume a uniform load
    and an ideal ring, and the next paragraph is about what happens when that assumption
    fails."""))

    c.날것(사고(f"""A block signed off with {수(IR예산*1e3,3,' mV')} of static IR drop
    failed at speed. The static analysis was correct and irrelevant: the current was not
    uniform. A hard macro in one corner drew a third of the total from a tenth of the
    area, and the switching was correlated — the whole datapath clocked at once. Static
    IR analysis averages over time and space, and <b>both averages were wrong in the
    same direction</b>."""))

    줄 = []
    for N in (2, 4, 8, 16, 32):
        h = 열점강하(N)
        줄.append([str(N), 수(코어변 / N, 4, " µm"), 수(레일강하(N) * 1e3, 3, " mV"),
                   수(h * 1e3, 3, " mV"), 수(h / 레일강하(N), 3, "×")])
    c.날것(표("Where a dense grid earns its tracks: 30 % of the current in 10 % of "
        "the area",
        ["Stripes", "Pitch", "Rail drop, uniform", "Rail drop, hot spot",
         "Ratio"], 줄))

    c.날것(짚기(f"""<b>Kill the trivial reading first.</b> The ratio column is
    {수(열점강하(8)/레일강하(8),3,'×')} and stays there, and it is not a discovery: it
    is exactly the local power-density ratio, 0.30/0.10. Nothing subtle happened. What
    <i>is</i> useful is the consequence, because the rail drop goes as p²: to hold the
    same drop under a 3× density you must reduce the pitch by √3 =
    {수(math.sqrt(3),4)}, i.e. put about {수(100*(math.sqrt(3)-1),3,' %')} more stripes
    over the hot region than over the rest. That is a number you can act on, and it is
    the quantitative form of the rule practitioners state without the derivation:
    <b>grid density is set by the worst local power density, not by the average</b>.
    The scheduling corollary follows — you cannot size the grid before you know where
    the power is, so the floorplan and the power plan are revised together once a real
    power map exists, not drawn once at the start."""))

    c.날것(개념(
        "스페셜 라우트 (special route) — why power is routed before signals",
        """<p>The power grid is not routed by the signal router. It is built first, by a
        separate step, and the signal router then treats it as an obstacle. The reason is
        that power routing has properties signal routing does not: the shapes are wide,
        regular, on fixed layers, connected to everything, and their width is decided by
        analysis rather than by connectivity.</p>
        <p>The order also encodes the priority. Tracks the grid takes are gone; the
        router must fit the design into what is left. <b>Doing it the other way round
        would mean sizing the power grid to whatever space the signals happened to
        leave</b>, which is exactly backwards — the grid's width comes from IR and EM
        limits that do not negotiate.</p>""",
        어디에="Immediately after the floorplan, before placement is legalised and "
             "long before signal routing.",
        언제="Re-run whenever the power map changes materially — a new macro, a "
            "frequency change, a different operating voltage.",
        어떻게="Rings around the core and around each macro; stripes at the pitch the "
             "hot-spot analysis demands; then the rail connections, then the via "
             "arrays at every crossing. Check EM at the <b>vias</b>, not only in the "
             "metal — a via array is usually the current bottleneck.",
        산업코드="""# The order, and why each step is where it is:
#   1  add_io_ring          pads, corner cells, fillers      <- perimeter fixed
#   2  add_power_ring       core ring, macro rings           <- both-end feed exists
#   3  add_stripes          pitch from the hot-spot map      <- tracks consumed here
#   4  connect_rails        stripes down to every row rail
#   5  add_via_arrays       every crossing; check EM per via
#   6  ...only now: place, cts, route""",
        주의="""Via electromigration is usually the binding constraint and is the one
            most often missed, because metal width is visible in the layout and via
            count is not. A stripe sized correctly for EM, dropping to a rail through
            two vias, fails at the vias."""))

    # ------------------------------------------------------------------
    c.절("T18.4 What to do with this on Monday")

    c.날것(쓰는자리([
        ["다이 · 코어영역 · 점유율 · 종횡비", "First floorplan, before any RTL freeze",
         "Whether the part is affordable, and which dimension to optimise"],
        ["패드제한다이 · 코어제한다이 · IO패드링 · 코너셀 · IO필러",
         "As soon as the pin list exists",
         "Whether shrinking the logic buys anything at all"],
        ["파워링 · 파워스트라이프 · 전원그리드 · 스페셜라우트",
         "Immediately after the floorplan",
         "IR drop, EM lifetime, and how many routing tracks are left"],
        ["필러셀 · 탭셀 · 킵아웃", "Before physical verification",
         "Whether the geometry is legal at all (T20)"],
    ]))

    c.글(f"""The numbers to carry out of this chapter are structural rather than
    specific. Total grid metal is set by the total current and does not depend on how
    you divide it; grid <b>pitch</b> is set by the worst local power density and is
    invisible to a uniform analysis — in the example above the hot spot multiplies the
    rail drop by {수(열점강하(4)/레일강하(4),3,'×')} at the same stripe count. And the
    factor of 8 in the both-ends distributed-load result is the quantitative reason the
    power distribution is a ring and a grid rather than a tree.""")

    c.글("""With a box, a grid and a set of rows, the tools can finally start moving
    things. The next chapter is what they do with them: placement, the clock tree, and
    routing.""")

    return c.완성()
