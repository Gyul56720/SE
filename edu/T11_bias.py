# -*- coding: utf-8 -*-
"""T11 -- Bias and references: making a number that does not move."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

# --- 잰 것 (edu/측정/bandgap.py, ngspice, 기본 BJT 모델, -40~125 °C) --------
# PTAT 이득(R3) 쓸기: R3 kΩ -> (평균 V_ref, 박스 TC ppm/°C)
잰PTAT = {
    6: (1.5678, 817.8), 8: (1.3243, 385.6), 9: (1.2425, 202.5),
    9.8: (1.18891, 68.8), 10.0: (1.17682, 37.0), 10.2: (1.16519, 12.7),
    10.3: (1.15954, 15.5), 11: (1.1228, 113.7), 12: (1.0776, 251.4),
    14: (1.0061, 494.5),
}
잰면적비 = {4: (0.97726, 602.5), 8: (1.17682, 37.0),
          16: (1.37318, 484.7), 32: (1.56779, 817.8)}
최적R3 = 10.2


def ch_bias():
    c = 장(
        "T11", "Bias and References — Making a Number That Does Not Move",
        "Everything else in this book assumes a stable current or voltage exists. "
        "Making one costs more thought than using one.",
        쓰는것=["전압", "전류", "저항", "온도", "지수함수", "로그", "미분",
              "문턱전압", "트랜스컨덕턴스", "출력저항", "정합", "플리커잡음",
              "열잡음", "등가저항"],
        내놓는것=["PTAT", "CTAT", "밴드갭기준", "곡률보정", "온도계수",
                "시동회로", "퇴화동작점", "전원제거비", "부하조정",
                "일정gm바이어스", "기준전류", "트리밍"],
        특허="""References are an old field with a live patent stream, and it clusters
        in three places: <b>curvature correction</b> (every scheme that cancels the
        V<sub>BE</sub> non-linearity the plain bandgap leaves behind), <b>low-voltage
        operation</b> (current-mode and resistive-divider bandgaps that work below
        1.2 V, which the classic topology cannot), and <b>trim and calibration</b>
        (one-point trim schemes that infer the curvature from a single measurement).
        The first and third are the same idea seen twice: <i>accept a physical error and
        remove it somewhere cheaper</i> — the pattern from T6.""")

    c.글("""A chip has no accurate absolute quantities. Resistors vary ±20 %, capacitors
    ±10 %, threshold voltages by tens of millivolts, and everything moves with
    temperature. Yet a data converter needs a reference stable to a fraction of an LSB,
    and an amplifier needs a bias current that does not double over the automotive
    temperature range. This chapter is about where that stability comes from — and
    the answer is that it is <b>constructed by cancelling two opposite temperature
    dependencies against each other</b>, which is why it is never free and never
    perfect.""")

    # ------------------------------------------------------------------
    c.절("T11.1 Two things a process gives you for free, both temperature-dependent")

    c.날것(정의("CTAT (complementary to absolute temperature)",
        "A quantity that <b>falls</b> with temperature. The base-emitter voltage of a "
        "bipolar transistor at fixed current is the canonical one: V<sub>BE</sub> ≈ "
        "0.7 V at room temperature with a slope of about −2 mV/°C, and it is <i>not</i> "
        "linear — the curvature it leaves behind is the floor on every plain bandgap."))

    c.날것(정의("PTAT (proportional to absolute temperature)",
        "A quantity that <b>rises</b> proportionally with absolute temperature. The "
        "difference between two V<sub>BE</sub>s at a current-density ratio N is exactly "
        "PTAT: ΔV<sub>BE</sub> = (kT/q)·ln N. It is <b>linear in T by construction</b>, "
        "and it depends only on a ratio and on physical constants — not on process."))

    c.날것(유도("Why adding them in the right proportion gives ~1.2 V", [
        ("V<sub>BE</sub>(T) falls at about −2 mV/°C; ΔV<sub>BE</sub> = (kT/q)·ln N "
         "rises at +0.086·ln N mV/°C.",
         "For N = 8, that is +0.179 mV/°C — far too small on its own, which is why it "
         "must be amplified."),
        ("Amplify the PTAT term by R1/R3 and add: "
         "V<sub>ref</sub> = V<sub>BE</sub> + (R1/R3)·ΔV<sub>BE</sub>.",
         "The gain is a <b>resistor ratio</b> — the one accurate thing a process "
         "offers (T10), which is why this topology survived."),
        ("Choose the ratio so the slopes cancel at the temperature of interest.",
         "One equation, one unknown. The cancellation is exact only at one temperature "
         "because V<sub>BE</sub> is curved and the PTAT term is straight."),
        ("The value at which the slopes cancel is the silicon bandgap extrapolated to "
         "0 K — about 1.2 V. <b>You do not choose it; it chooses itself.</b>",
         f"Measured below: the best temperature coefficient lands at "
         f"V<sub>ref</sub> = {수(잰PTAT[최적R3][0],5,'V')}. Nobody designed that "
         "number — it is where the cancellation happens to occur."),
    ]))

    # ------------------------------------------------------------------
    c.절("T11.2 The measurement: a sharp optimum, and what sets its floor")

    c.날것(표("Measured temperature coefficient against PTAT gain "
             "(ngspice, −40…125 °C, N = 8, box method)",
        ["R3", "V_ref", "TC", ""],
        [[수(r, 4, "kΩ"), 수(v, 5, "V"), 수(tc, 4, " ppm/°C"),
          ("<b>optimum</b>" if r == 최적R3 else "")]
         for r, (v, tc) in sorted(잰PTAT.items())]))

    c.날것(그림(sch.곡선(
        [("TC", [(r, tc) for r, (v, tc) in sorted(잰PTAT.items())], "#c0392b")],
        가로="R3 (kΩ) — sets the PTAT gain", 세로="TC (ppm/°C)",
        표시=[(최적R3, 잰PTAT[최적R3][1], "12.7")],
        가로눈금=[6, 10, 14]),
        """The optimum is <b>sharp</b>, unlike the PLL's loop-bandwidth optimum in T7:
        a 2 % error in the ratio triples the temperature coefficient. That is the
        difference between an optimum set by a <i>cancellation</i> and one set by a
        <i>sum of two opposing costs</i> — and it is why references are trimmed and
        loop filters are not."""))

    c.날것(예제(
        "How accurately must that ratio be set?",
        f"""The measured optimum is R3 = {수(최적R3,4,'kΩ')} giving
        {수(잰PTAT[최적R3][1],4,' ppm/°C')}. Neighbouring points:
        {수(10.0,3,'kΩ')} → {수(잰PTAT[10.0][1],4,' ppm/°C')} and
        {수(10.3,3,'kΩ')} → {수(잰PTAT[10.3][1],4,' ppm/°C')}.""",
        """Compute the fractional ratio error at each point and compare with the TC
        degradation.""",
        f"""A {수((최적R3-10.0)/최적R3*100,2,'%')} error costs
        {수(잰PTAT[10.0][1]/잰PTAT[최적R3][1],3)}× the temperature coefficient.
        <b>Sub-per-cent ratio accuracy is required</b>, which is a matching problem
        (T12) and usually a trim.""",
        """Assuming the optimum found in simulation is the optimum in silicon. The
        cancellation depends on V<sub>BE</sub>'s actual slope, which is a process
        parameter with its own spread — so the optimum <b>moves per lot</b>. This is
        precisely why production references are trimmed at test, and why a design that
        cannot be trimmed must be designed for the <i>worst-case</i> optimum offset,
        not the nominal one."""))

    c.날것(표("The same knob from the other side: area ratio N at fixed R3 = 10 kΩ",
        ["N", "V_ref", "TC"],
        [[str(n), 수(v, 5, "V"), 수(tc, 4, " ppm/°C")]
         for n, (v, tc) in sorted(잰면적비.items())]))

    c.날것(짚기("""Both tables tune the same physical quantity — the PTAT gain — and both
    show the same sharp optimum. The practical difference is cost: N enters as ln N, so
    doubling the area ratio buys only 0.69 of a unit of gain, while the resistor ratio
    is linear and free. <b>That is why real designs use a modest N (8 is almost
    universal) and set the fine adjustment with resistors</b> — the area would otherwise
    be enormous for a ratio that a resistor provides for nothing."""))

    c.날것(개념(
        "곡률 (curvature) — the floor the plain topology cannot cross",
        f"""<p>The measured best is {수(잰PTAT[최적R3][1],4,' ppm/°C')}, and no choice
        of ratio does better. The reason is structural: V<sub>BE</sub>(T) contains a
        T·ln T term while the PTAT correction is exactly linear in T, so their
        difference cannot be zero everywhere. What remains is a bow — the reference is
        equal at two temperatures and off in between.</p>
        <p>Curvature-corrected references add a third term with the right curvature
        (from a resistor's own temperature coefficient, from a PTAT² current, or from
        the difference of two V<sub>BE</sub>s at different current
        <i>temperature dependencies</i>) and reach single-digit ppm/°C. Each of those
        schemes costs area and a new sensitivity, which is why the plain topology is
        still shipped wherever tens of ppm are enough.</p>""",
        어디에="Any reference feeding a converter of 12 bits or more, and any system "
             "specified over the automotive or industrial temperature range.",
        언제="Compare the reference's drift with the converter's LSB over the operating "
            "range before choosing. At 12 bits and 1 V full scale an LSB is 244 µV; a "
            f"{수(잰PTAT[최적R3][1],4,' ppm/°C')} reference drifts "
            f"{수(잰PTAT[최적R3][1]*1e-6*1.2*165*1e6,3,'µV')} over 165 °C — "
            "<b>about 10 LSB</b>, which is why converters are specified at a "
            "temperature and references are trimmed.",
        어떻게="Measure TC as a box (max−min over the range, not a local slope), report "
             "the range it was measured over, and state whether it is trimmed. Those "
             "three facts make two references comparable; without them, nothing does.",
        산업코드="""* Box TC, which is what a datasheet means, and the local slope,
* which is what a naive .measure gives.  They differ by 2-5x.
.dc TEMP -40 125 5
.measure dc vmax MAX v(out)
.measure dc vmin MIN v(out)
.measure dc vavg AVG v(out)
.measure dc tc_box param='(vmax-vmin)/vavg/165*1e6'   $ ppm/degC -- the honest one
* Reporting a slope taken at 27 C as 'the TC' is the standard way to make a
* reference look 3x better than it is.""",
        주의="""A temperature coefficient quoted without its range is not a
            specification. The box method over −40…125 °C and a local slope at 27 °C can
            differ by a factor of five on the <b>same</b> circuit, and the second number
            is the one that appears in optimistic datasheets."""))

    # ------------------------------------------------------------------
    c.절("T11.3 The failure mode that has nothing to do with temperature")

    c.날것(개념(
        "시동 회로 (start-up) and the degenerate operating point",
        """<p>A bandgap's loop has <b>two</b> stable solutions: the intended one, and
        the one where every current is zero. Zero is perfectly self-consistent — no
        current means no V<sub>BE</sub>, which means no current — and nothing in the
        loop distinguishes it from the useful solution.</p>
        <p>A start-up circuit injects a small current when the reference is near zero
        and then <b>gets out of the way</b>. Both halves matter: a start-up that keeps
        conducting adds its own temperature dependence to the output, and a start-up
        that is too weak leaves a fraction of parts dead on the slow corner.</p>""",
        어디에="Every bandgap, every constant-g<sub>m</sub> bias cell, every circuit "
             "whose bias is derived from itself.",
        언제="It is not optional and it is not a nominal-corner check: the zero state is "
            "reached by a slow supply ramp, by a brown-out, or by any sequence the "
            "designer did not think of.",
        어떻게="Simulate the <b>supply ramp</b>, not the operating point, at every "
             "corner and at several ramp rates including a very slow one. Then force "
             "the output to zero with an initial condition and verify that it recovers.",
        산업코드="""* The two simulations that must both pass. The .op alone proves nothing --
* it simply finds A solution, and a degenerate circuit HAS a solution.
.tran 1u 500u                        $ 1) slow supply ramp
Vcc vcc 0 PWL(0 0 400u 1.8)          $   400 us ramp -- deliberately slow
.measure tran vref_final FIND v(ref) AT=480u

.ic v(ref)=0                         $ 2) forced into the dead state
.tran 1u 100u
.measure tran vref_rec FIND v(ref) AT=90u
* Both must land at the design value. A circuit that passes .op and fails these
* is a part that works on the bench and fails in the field at cold start.""",
        주의="""The most common start-up bug is not the absence of the circuit but its
            <b>strength at the fast corner</b>: a start-up device sized for the slow
            corner may still be injecting current at the fast one, shifting the
            reference by a few millivolts in a way that tracks process. Check that the
            start-up current is essentially zero once the loop is up — at every
            corner."""))

    # ------------------------------------------------------------------
    c.절("T11.4 A reference has three specifications, not one")

    c.날것(표("What a reference must guarantee",
        ["Specification", "What it is", "Fails as", "Set by"],
        [["Temperature coefficient", "Drift over the operating range",
          "Gain error that changes with ambient",
          "PTAT/CTAT balance, curvature, trim"],
         ["<b>PSRR</b>", "Rejection of supply noise, at frequency",
          "The converter's noise floor rises when the digital side is busy",
          "The amplifier's supply rejection <b>and the layout</b>"],
         ["Load regulation", "Output shift versus load current",
          "The reference moves when the converter samples — a code-dependent error",
          "Output impedance and the buffer, not the core"],
         ["Noise", "Integrated output noise in band",
          "Directly adds to the converter's noise floor (T4)",
          "Resistor thermal noise and the amplifier's 1/f"]]))

    c.날것(사고("""Load regulation is the specification that surprises digital
    integrators. A SAR converter's reference is not a DC load: it draws a charge pulse
    at every bit trial, and the reference must settle between trials to the full
    accuracy of the conversion (T10's settling argument, applied to a load that changes
    every cycle). A reference that meets its DC specification perfectly can still
    produce a converter with <b>code-dependent INL</b>, because the charge demanded
    depends on the code being tested. <b>The fix is a local decoupling capacitor sized
    against the charge per trial</b> — and that capacitor is often larger than the
    converter's own array."""))

    c.날것(개념(
        "일정 g_m 바이어스 (constant-g_m bias)",
        """<p>Most analog specifications — bandwidth, noise, gain — depend on
        g<sub>m</sub>, not on current. A bias that holds current constant therefore holds
        the <i>wrong</i> thing: g<sub>m</sub> = √(2μC<sub>ox</sub>(W/L)I) still moves
        with mobility, which moves with temperature and process.</p>
        <p>The constant-g<sub>m</sub> cell sets g<sub>m</sub> = 1/(R·(1−1/√K)) by
        forcing the source-degeneration resistor to define it — so g<sub>m</sub> now
        tracks a <b>resistor</b> rather than a mobility. It does not remove the
        dependence; it <i>moves it</i> to a component whose variation you can choose by
        picking a resistor type.</p>""",
        어디에="The bias of amplifiers, comparators, output drivers — anything whose "
             "bandwidth must be stable across corners.",
        언제="When bandwidth or noise must hold across process and temperature. It is "
            "the default for signal-path bias in mixed-signal IP.",
        어떻게="Pick the resistor type deliberately (poly resistors and diffusion "
             "resistors have very different temperature coefficients), and remember "
             "this cell also has a degenerate zero state — it needs its own start-up.",
        산업코드="""* What the bias must actually hold, checked across corners.
* Constant CURRENT is the wrong target; constant gm is the right one.
.dc TEMP -40 125 5
.measure dc gm_min MIN @m.xamp.m1[gm]
.measure dc gm_max MAX @m.xamp.m1[gm]
.measure dc gm_spread param='(gm_max-gm_min)/gm_min*100'   $ percent
* A constant-current bias typically gives 30-40% here; constant-gm, under 10%.""",
        주의="""Constant-g<sub>m</sub> makes g<sub>m</sub> track 1/R, so the circuit's
            bandwidth now depends on the resistor's temperature coefficient — which for
            a diffusion resistor can be thousands of ppm/°C. Choosing the resistor is
            part of the design, not a layout detail."""))

    # ------------------------------------------------------------------
    c.절("T11.5 What to do with this on Monday")

    c.날것(쓰는자리([
        ["PTAT · CTAT · 밴드갭기준", "Any converter or precision block",
         "The reference topology and whether it must be trimmed"],
        ["온도계수 · 곡률보정", "System specification over temperature",
         "Whether tens of ppm are enough or curvature correction is needed"],
        ["시동회로 · 퇴화동작점", "Every self-biased cell",
         "Whether the part comes up at cold start — at every corner"],
        ["전원제거비 · 부하조정", "Integration with the digital side",
         "The decoupling the reference needs, and who pays for it"],
        ["일정gm바이어스", "Signal-path bias",
         "Whether bandwidth holds across corners, and which resistor type"]]))

    c.글(f"""The measured result to carry: the plain bandgap's best temperature
    coefficient in this simulation is {수(잰PTAT[최적R3][1],4,' ppm/°C')} at
    V<sub>ref</sub> = {수(잰PTAT[최적R3][0],5,'V')}, and the optimum is <b>sharp</b> —
    a {수((최적R3-10.0)/최적R3*100,2,'%')} ratio error costs
    {수(잰PTAT[10.0][1]/잰PTAT[최적R3][1],3)}× the drift. Everything else in this
    chapter follows from that sharpness: it is why references are trimmed, why matching
    (the next chapter) is the limiting discipline, and why the value nobody chose —
    1.2 V — is printed on every datasheet in the field.""")

    c.글("""The next chapter takes the assumption this one has been leaning on — that two
    identically drawn devices are identical — and replaces it with a distribution.""")

    return c.완성()
