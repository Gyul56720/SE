# -*- coding: utf-8 -*-
"""T20 -- Signoff: the checks that decide whether geometry may be manufactured."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch
import sch_flow

# ---------------------------------------------------------------------------
# 코너의 곱셈 -- 가정이 아니라 셈이다.  각 축의 칸 수만 가정한다.
# ---------------------------------------------------------------------------
축 = [("Process", 3, "slow / typical / fast — and slow-n/fast-p corners on top "
                     "of that in a mixed-signal part"),
     ("Voltage", 2, "nominal and the low end of the regulator's tolerance"),
     ("Temperature", 3, "−40 °C, 25 °C, 125 °C"),
     ("RC (interconnect)", 3, "cmin / cworst / rcworst — extraction corners are "
                              "independent of the device corners"),
     ("Mode", 4, "functional, scan-shift, scan-capture, low-power retention")]
코너시간 = 2.0          # h, 코너 하나를 STA 로 도는 시간 (가정)

# 온도 반전 모형.  T1 의 소자 식을 그대로 쓴다 -- 새 모형을 만들지 않는다.
Vth0, KAPPA, ALPHA, T0 = 0.45, 0.8e-3, 1.3, 300.0


def 지연(V, T):
    """delay ∝ C·V / I_d,  I_d ∝ µ(T)·(V − Vth(T))^α,  µ ∝ T^−1.5."""
    Vth = Vth0 - KAPPA * (T - T0)
    과구동 = V - Vth
    if 과구동 <= 0:
        return float("inf")
    return V * (T / T0) ** 1.5 / 과구동 ** ALPHA


def 반전전압_닫힌꼴(T=T0):
    """d(ln delay)/dT = 1.5/T − ακ/(V−Vth) = 0  ->  V − Vth = ακT/1.5."""
    return Vth0 + ALPHA * KAPPA * T / 1.5


def 반전전압_수치(T=T0, 낮=0.50, 높=1.50, 판=80):
    """같은 값을 **식 없이** -- 수치 미분의 부호가 바뀌는 곳을 이분법으로 찾는다."""
    h = 0.01

    def 기울기(V):
        return (지연(V, T + h) - 지연(V, T - h)) / (2 * h)

    for _ in range(판):
        가 = 0.5 * (낮 + 높)
        if 기울기(가) < 0:            # 아직 반전 쪽
            낮 = 가
        else:
            높 = 가
    return 0.5 * (낮 + 높)


def 코너수():
    n = 1
    for _, k, _ in 축:
        n *= k
    return n


def ch_signoff():
    c = 장(
        "T20", "Signoff — The Checks That Decide Whether It May Be Built",
        "Every signoff check answers one narrow question, and the failures that "
        "reach silicon live in the gaps between them.",
        쓰는것=["사인오프", "구현흐름", "DRC", "LVS", "안테나위반", "밀도규칙",
              "추출", "SPEF", "SDF", "SDC", "정적타이밍분석", "OCV", "슬랙",
              "ECO", "GDS", "전압강하", "일렉트로마이그레이션", "블랙식",
              "상세배선", "클럭스큐", "문턱전압", "누설전류", "래치업"],
        내놓는것=["물리검증", "ERC", "금속채움", "CMP", "코너", "MMMC",
                "온도반전", "정적IR", "동적IR", "스위칭벡터", "기능ECO",
                "금속ECO", "스페어셀", "테이프아웃", "마스크"],
        특허="""Signoff itself is the least patent-encumbered part of the flow — the
        rules belong to the foundry and the checks are commodity. What <i>is</i> filed
        heavily is <b>ECO automation</b>: choosing which spare cells to use and how to
        reroute with the minimum disturbance, so that a fix does not invalidate the
        signoff that has already been paid for. That is a direct attack on the cost
        computed in T17.""")

    c.글("""A routed design is a set of polygons and a claim: that these polygons, made
    in this process, will behave the way the RTL said. Signoff is the set of
    independent checks that test that claim before anyone spends mask money on it. Each
    check is a different tool with a different model of the design, and it is worth
    being precise about which question each one answers — because <b>the failures that
    reach silicon are almost never inside a check; they are in the space between
    two</b>.""")

    # ------------------------------------------------------------------
    c.절("T20.1 What each check actually asserts")

    c.날것(표("The signoff set, stated as claims",
        ["Check", "The claim it establishes", "What it cannot see"],
        [["<b>DRC</b>", "The geometry obeys every manufacturing rule the foundry "
          "publishes for this process and this metal stack",
          "Whether the geometry implements the design. A DRC-clean empty die passes"],
         ["<b>LVS</b>", "The devices and connections extracted from the layout match "
          "the netlist, device for device and net for net",
          "Whether the <i>netlist</i> is right. LVS compares the layout to the "
          "schematic; if the schematic is wrong, LVS confirms the error"],
         ["<b>ERC</b>", "No floating gates, no unconnected wells, no supply shorted "
          "through a device that was not meant to conduct",
          "Anything dynamic — it is a topology check"],
         ["<b>Antenna</b> (T19)", "No metal segment collects enough charge during "
          "etch to damage a gate oxide", "Nothing about the finished circuit"],
         ["<b>Density / fill</b>", "Every layer's local metal density is inside the "
          "window CMP requires",
          "The capacitance the fill adds — that is extraction's job, and it must be "
          "re-run <b>after</b> fill"],
         ["<b>EM / IR</b>", "No wire exceeds its current-density limit for the "
          "required lifetime (T14), and no node sags below the budget",
          "Whether the switching activity used to drive it resembles the real "
          "workload — see T20.3"],
         ["<b>STA</b>", "Every timing path meets setup and hold, at every corner in "
          "the list, in every mode in the list",
          "Paths the SDC excluded, and modes nobody listed"]]))

    c.날것(짚기("""Read the third column as a list of where to look after a silicon
    failure. Each check is sound; each is narrow; and the narrowness is deliberate,
    because a check that tried to establish everything could not be run in finite time.
    <b>The engineering judgement in signoff is not in running the checks — it is in
    knowing what the union of them leaves out.</b>"""))

    c.날것(개념(
        "금속 채움 (metal fill) and the extraction it invalidates",
        """<p>Chemical-mechanical polishing removes material at a rate that depends on
        the local pattern density. A region with little metal polishes faster and ends
        up thinner, which changes both resistance and the thickness of the dielectric
        above it. The foundry therefore requires every layer's density to sit inside a
        window, and the flow satisfies that by adding <b>fill</b> — floating or grounded
        metal shapes in the empty areas.</p>
        <p>Fill is added after routing, which means it is added <b>after</b> the
        extraction that timing signoff used. Those shapes are metal next to signal
        wires; they add capacitance. Grounded fill adds it predictably; floating fill
        adds a smaller, harder-to-model amount.</p>
        <p>So the order is: route, fill, <b>re-extract</b>, re-run STA. A flow that
        signs off timing on the pre-fill extraction has signed off a design that will
        not be manufactured.</p>""",
        어디에="Between detail routing and final timing signoff.",
        언제="Always. The only variation is whether the fill is inserted by the P&amp;R "
            "tool or by the physical-verification tool, and the two do not produce "
            "identical results.",
        어떻게="Insert fill, re-extract with fill present, re-run the corner set, and "
             "<b>diff the slack</b> against the pre-fill run. A small, uniform "
             "degradation is expected; a large change on a few nets means fill landed "
             "next to a long, critical, sparsely-surrounded wire.",
        산업코드="""# The diff that must exist before tape-out:
#   path                   slack pre-fill   slack post-fill   delta
#   u_dsp/…/mac_out[17]        +45 ps           +31 ps        -14 ps
#   u_if/…/clk_gate_en          +88 ps           +12 ps        -76 ps   <- look
# A -76 ps outlier is a wire that was alone in an empty region and is now
# surrounded by fill. It is real, it is predictable, and it is missed by any
# flow that signs off before filling.""",
        주의="""Fill also changes the inductance and the return path of high-speed
            signals, which matters for the links of T8 far more than for logic. For
            those, ask for fill exclusion zones — and remember that an exclusion zone
            is a density violation unless the surrounding area compensates."""))

    # ------------------------------------------------------------------
    c.절("T20.2 Corners multiply, and most of them are dominated")

    c.날것(그림(sch_flow.코너곱셈(),
        "Why signoff runs on a farm. The axes are independent of each other, so "
        "they multiply rather than add — and the corner list is therefore "
        "negotiated rather than assumed."))

    c.날것(유도("Where the signoff runtime comes from", [
        (" · ".join(f"{이름}: {k}" for 이름, k, _ in 축) + ".",
         "Each axis is independent of the others — that is why they multiply rather "
         "than add. The counts are assumed and typical."),
        (f"That is {' × '.join(str(k) for _, k, _ in 축)} = <b>{코너수()}</b> "
         "corner-mode combinations.",
         "Multiplication. Nothing subtle is happening; that is the point."),
        (f"At {수(코너시간,2,' h')} per STA run, a full set is "
         f"{수(코너수()*코너시간,4,' h')} of compute.",
         f"{수(코너수()*코너시간/24,3,' days')} on one machine — which is why signoff "
         "runs on a farm and why the corner list is negotiated rather than assumed."),
        ("A single ECO invalidates all of it.",
         "This is T17's loop-cost arithmetic in its most expensive form: the last "
         "stage in the chain is the largest one."),
    ]))

    c.날것(표("The axes, and why each one is there",
        ["Axis", "Values", "Why it cannot be dropped"],
        [[이름, str(k), 왜] for 이름, k, 왜 in 축]))

    c.날것(개념(
        "MMMC — analysing modes and corners together instead of one at a time",
        f"""<p>The {코너수()} combinations above are not {코너수()} separate analyses in
        a modern flow. Multi-mode multi-corner analysis loads the several mode
        constraints and the several corner libraries into one session and propagates
        once, sharing the work that is common between them.</p>
        <p>The saving is real but it is not the main reason to use it. The main reason
        is that <b>optimisation must see all the corners at once</b>. Fixing a setup
        violation at the slow corner by adding drive strength can create a hold
        violation at the fast corner; a tool that sees one corner at a time will
        oscillate between them, and that oscillation is exactly the non-convergence of
        T17 with p ≥ 1.</p>""",
        어디에="Post-CTS optimisation onwards, and all of signoff.",
        언제="From the first optimisation that can make a corner-dependent trade — "
            "which in practice means as soon as hold fixing starts.",
        어떻게="Define the analysis views explicitly (a view is one mode plus one "
             "delay corner plus one RC corner), mark which are for setup and which for "
             "hold, and <b>check that the list covers the product's real operating "
             "envelope</b> rather than the list inherited from the previous project.",
        산업코드="""# An analysis-view list is a specification, not a configuration:
#   view              mode        delay corner   rc corner   checks
#   func_ss_cw        functional  ss_0.9v_125c   cworst      setup
#   func_ff_cb        functional  ff_1.1v_m40c   cbest       hold
#   shift_ss_cw       scan_shift  ss_0.9v_125c   cworst      setup
#   shift_ff_cb       scan_shift  ff_1.1v_m40c   cbest       hold
# The question to ask of this table is not "is it right" but
# "which operating condition of the product is NOT in it".""",
        주의="""Scan-shift mode is the one most often forgotten and the one most often
            broken, because its clock structure is different from the functional one
            and its hold requirements are severe. A part that fails only on the tester
            is usually a shift-mode timing problem, not a defect."""))

    c.글("""The corner list is long partly because the dominance people expect does not
    hold. The intuition is that the slow corner bounds setup and the fast corner bounds
    hold, so two corners would do. That intuition comes from a regime where delay
    increases monotonically with temperature — and modern low-voltage operation is not
    in that regime.""")

    c.날것(유도("Temperature inversion, from the device model of T1", [
        ("Delay ∝ C·V / I<sub>d</sub>, with I<sub>d</sub> ∝ µ(T)·(V − V<sub>th</sub>"
         "(T))<sup>α</sup>.",
         "The α-power form from T1. α ≈ 1.3 for a short-channel device."),
        ("Mobility falls with temperature: µ ∝ T<sup>−1.5</sup>. That makes the part "
         "<b>slower</b> when hot.",
         "Phonon scattering. This is the effect everyone knows."),
        (f"Threshold also falls with temperature: dV<sub>th</sub>/dT ≈ "
         f"−{수(KAPPA*1e3,2,' mV/K')}. That makes the part <b>faster</b> when hot.",
         "The Fermi level moves with temperature. This is the effect that gets "
         "forgotten."),
        ("Which one wins depends on the overdrive V − V<sub>th</sub>, because the "
         "threshold shift is a large fraction of a small overdrive and a small "
         "fraction of a large one.",
         "The two effects enter multiplicatively, so the comparison is between their "
         "logarithmic derivatives."),
        ("d(ln delay)/dT = 1.5/T − ακ/(V − V<sub>th</sub>). Setting it to zero gives "
         "V − V<sub>th</sub> = ακT/1.5.",
         "Differentiate and solve. The result depends on nothing but the two "
         "temperature coefficients and α."),
        (f"At {수(T0,4,' K')} that is an overdrive of "
         f"{수(ALPHA*KAPPA*T0/1.5,4,' V')}, i.e. "
         f"V ≈ {수(반전전압_닫힌꼴(),4,' V')}.",
         "Below that supply the part is <b>slowest when cold</b>, and the corner list "
         "must contain both temperature extremes for setup."),
    ]))

    줄 = []
    for V in (1.8, 1.2, 0.9, 0.75, 0.65, 0.6):
        기준 = 지연(V, 25 + 273.15)
        값 = [지연(V, Tc + 273.15) / 기준 for Tc in (-40, 25, 125)]
        줄.append([수(V, 3, " V")] + [수(v, 4, "×") for v in 값] +
                  ["<b>inverted</b>" if 값[2] < 값[0] else "normal"])
    c.날것(표("Delay against temperature, normalised to 25 °C",
        ["Supply", "−40 °C", "25 °C", "125 °C", "Which is the slow corner"], 줄))

    c.날것(짚기(f"""The table stops at {수(0.6,3,' V')} for a reason worth stating: at
    −40 °C this model's threshold is {수(Vth0 - KAPPA*(233.15-T0),4,' V')}, so below
    about {수(Vth0 - KAPPA*(233.15-T0),3,' V')} of supply the device has no overdrive
    at all when cold and the delay is not merely long, it is undefined. That is not an
    artefact — it is the near-threshold regime, and it is why a low-voltage retention
    mode has a minimum supply specified at the <b>cold</b> corner."""))

    _닫, _수 = 반전전압_닫힌꼴(), 반전전압_수치()
    c.날것(짚기(f"""<b>The independent control.</b> The crossover supply is computed
    twice: once from the closed form V = V<sub>th0</sub> + ακT/1.5, giving
    {수(_닫,5,' V')}, and once by bisecting on the sign of a <i>numerically
    differentiated</i> delay, using none of that algebra, giving {수(_수,5,' V')} —
    a disagreement of {수(1e3*abs(_닫-_수),3,' mV')}. And the trivial explanation is
    killed by the table rather than argued away: if the effect were an artefact of the
    normalisation, the 'inverted' verdict would not move with supply, and it
    does."""))

    c.날것(사고("""A design signed off at 125 °C and typical voltage failed at −40 °C in
    a cold-start test. It was a low-voltage retention mode: at that supply the part was
    slowest cold, and the corner list — inherited from a 1.8 V project where the
    intuition held — contained only the hot corner for setup. <b>Nothing in the flow was
    broken. The list of what to check was written by someone applying a rule that had
    stopped being true.</b>"""))

    # ------------------------------------------------------------------
    c.절("T20.3 EM and IR signoff need something the design does not contain")

    c.날것(정의("정적 IR (static IR) · 동적 IR (dynamic IR) · 스위칭 벡터",
        "<b>Static</b> IR analysis distributes an average current over the grid and "
        "solves the resistive network — the calculation of T18. <b>Dynamic</b> IR "
        "analysis solves the grid with the supply's inductance and decoupling "
        "included (T13), driven by the current waveform that a particular pattern of "
        "switching produces. That pattern is the <b>switching vector</b>, and it is "
        "not part of the design: it has to be supplied."))

    c.날것(짚기("""This is the one signoff check whose answer depends on an input that
    is neither in the netlist nor in the constraints. Choose a quiet vector and the
    analysis passes; choose the worst one and it may not — and nothing in the flow tells
    you which you chose. <b>The honest procedure is to state, in the signoff report,
    which vectors were used and why they are believed to bound the real workload</b>,
    and to treat a dynamic-IR pass without that statement as an unverified claim rather
    than a result."""))

    c.날것(표("Three ways to get a vector, and what each is worth",
        ["Source", "How representative", "What it misses"],
        [["<b>Functional simulation</b> of a real workload",
          "Best available — it is the actual switching",
          "Only covers the workload you simulated, and long simulations produce "
          "enormous activity files"],
         ["<b>Vectorless</b> (tool-propagated probabilities from a few toggle rates)",
          "Adequate for a first pass and for finding gross grid errors",
          "Correlation. It assumes blocks switch independently, and the failures come "
          "from everything switching at once"],
         ["<b>Scan-capture pattern</b>",
          "The worst case for many designs and rarely analysed",
          "Nothing — it is often the real answer, because scan capture switches far "
          "more of the die simultaneously than any functional mode does"]]))

    c.날것(예제("Which mode sets the peak current?",
        "The block of T18/T19 draws 350 mW functionally. In scan-shift mode every "
        "flop toggles on every cycle, and the shift clock runs at a quarter of the "
        "functional frequency.",
        "Functional switching activity for logic is typically 10–20 % of nodes per "
        "cycle; shift activity approaches 50 % of flops per cycle. Take the clock "
        "network as fixed (it toggles either way) and compare the flop-output "
        "switching: roughly 0.15 → 0.5 is a factor of about 3.3 in that component, "
        "against a factor of 0.25 from the slower clock.",
        "Shift mode draws roughly <b>0.8×</b> the functional switching power in that "
        "component — comparable, not obviously smaller. The peak is set by whichever "
        "mode runs its clock fastest at high activity, and on many parts that is "
        "scan <i>capture</i>, not shift.",
        "The numbers above are ratios of assumptions, not measurements, and should "
        "not be quoted as results. The conclusion that survives is structural: "
        "<b>test modes are not low-power modes</b>, and a grid signed off only "
        "against functional vectors has not been signed off against the mode that "
        "will run first, on the tester, on every part shipped.",
        덧="""This is also why test engineers reduce shift frequency and use
        low-power ATPG that limits simultaneous toggling — not for test quality, but
        because the part cannot supply the current. That constraint belongs in the
        floorplan discussion of T18, and it usually arrives after it."""))

    # ------------------------------------------------------------------
    c.절("T20.4 Changing a signed-off design")

    c.날것(표("Two kinds of ECO, and what each one costs",
        ["Kind", "What changes", "Which signoff must be redone"],
        [["<b>Metal-only ECO</b> (uses spare cells)",
          "Routing only. The function comes from cells already placed and already on "
          "the mask, rewired on the metal layers",
          "Everything downstream of routing: extraction, STA, EM/IR, DRC, LVS. But "
          "only the changed masks are re-made — which is the entire point"],
         ["<b>Functional ECO</b> (new cells)",
          "Placement and routing. New instances go into gaps, displacing what was "
          "there", "All of the above, and every mask is new"]]))

    c.날것(개념(
        "스페어 셀 (spare cells) — paying now for the option to change later",
        """<p>Spare cells are unused gates — typically a mix of NANDs, NORs, inverters
        and flops — scattered through the placement and tied off. They cost area and
        leakage and do nothing. What they buy is the ability to implement a logic
        change by <b>rewiring metal only</b>, because the transistors the change needs
        are already on the diffusion masks.</p>
        <p>The economics are a straightforward option price. A full mask set at an
        advanced node costs millions; a metal-only revision costs a fraction of it and
        takes weeks rather than months. Spending 1–2 % of the area on spares is cheap
        insurance if the probability of needing a change is anything but negligible —
        and on a first silicon it never is.</p>""",
        어디에="Inserted at placement, distributed rather than clustered.",
        언제="Every design that will have a first silicon. Omit them only on a "
            "well-understood derivative of a proven part.",
        어떻게="Scatter them so that any region has some within reach — a spare cell "
             "500 µm from the fix is not usable, because the wire that reaches it "
             "breaks the timing the fix was made to satisfy. Include flops: the "
             "changes you cannot predict are usually sequential.",
        산업코드="""# A spare-cell plan is a distribution, not a count:
#   region      spares: inv  nand2  nor2  dff     nearest-spare distance
#   core NW           24     16     16     8            < 60 um
#   core NE           24     16     16     8            < 60 um
#   near macro A       6      4      4     2            < 90 um   <- thin
# 'We have 400 spare cells' says nothing. 'No point in the core is more
# than 90 um from a spare flop' is the statement that makes an ECO possible.""",
        주의="""Tie the spare inputs off properly and check that ERC sees them as
            tied. An untied spare gate is a floating input — the failure mode is
            excess current through a half-on inverter, and it passes DRC, LVS and STA
            because none of them is looking for it."""))

    c.날것(정의("테이프아웃 (tape-out)",
        "The point at which the GDS is released to the mask shop. It is a commercial "
        "event rather than a technical one: after it, changing the design costs a "
        "mask set. Everything this chapter describes exists to make the claim that "
        "the release is safe — and the honest form of that claim always includes the "
        "list of what was <b>not</b> checked."))

    # ------------------------------------------------------------------
    c.절("T20.5 What to do with this on Monday")

    c.날것(쓰는자리([
        ["물리검증 · ERC · 금속채움 · CMP", "Before every tape-out",
         "Whether the geometry is manufacturable, and whether timing was signed off "
         "on the geometry that will actually be made"],
        ["코너 · MMMC · 온도반전", "Writing the analysis-view list",
         "Whether the corner list covers the product, or the previous project"],
        ["정적IR · 동적IR · 스위칭벡터", "Power-integrity signoff",
         "Whether the vectors bound the real workload — including test modes"],
        ["기능ECO · 금속ECO · 스페어셀", "Placement, months before you need them",
         "Whether a post-silicon fix costs a metal revision or a full mask set"],
        ["테이프아웃 · 마스크", "The release decision",
         "What you are asserting, and what you are not"],
    ]))

    c.글(f"""The numbers to carry: {코너수()} corner-mode combinations at
    {수(코너시간,2,' h')} each is {수(코너수()*코너시간/24,3,' days')} of compute that
    one ECO throws away — the strongest quantitative argument in this book for fixing
    things early. And the crossover overdrive of {수(ALPHA*KAPPA*T0/1.5,4,' V')}
    is why "slow is hot" stopped being a safe rule: below about
    {수(반전전압_닫힌꼴(),3,' V')} of supply, in this model, the slow corner is the
    cold one.""")

    c.글("""The part can now be built. Whether an individual die works is a different
    question again, answered not by a tool but by a machine with the die in it — and
    that is the last chapter of this arc.""")

    return c.완성()
