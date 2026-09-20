# -*- coding: utf-8 -*-
"""T14 -- Reliability: what the circuit looks like after ten years."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

kB = 8.617e-5          # eV/K
수명시간 = 10 * 365 * 24


def _AF온도(Ea, T낮, T높):
    """T높 에서 스트레스한 것이 T낮 에 비해 몇 배 빠른가 (Arrhenius)."""
    return math.exp(Ea / kB * (1 / (T낮 + 273.15) - 1 / (T높 + 273.15)))


def _BTI외삽(n, 스트레스h=1000.0):
    return (수명시간 / 스트레스h) ** n


def _전압가속(감마, dV):
    return math.exp(감마 * dV)


def ch_rel():
    c = 장(
        "T14", "Reliability — What the Circuit Looks Like After Ten Years",
        "Every parameter in this book drifts. A design signed off at time zero has "
        "been signed off for the wrong day.",
        쓰는것=["전압", "전류", "온도", "지수함수", "로그", "확률", "정규분포",
              "문턱전압", "트랜스컨덕턴스", "슬랙", "정착시간", "펠그롬법칙",
              "오프셋", "최소동작전압", "전압강하"],
        내놓는것=["BTI", "HCI", "TDDB", "일렉트로마이그레이션", "아레니우스",
                "가속계수", "활성화에너지", "블랙식", "와이블", "번인",
                "노화인지설계", "수명목표"],
        특허="""Reliability physics belongs to the foundry; the IP-side claims are about
        <b>surviving it</b>: circuits that sense their own degradation and compensate
        (adaptive body bias, adaptive voltage scaling driven by on-die ageing monitors),
        topologies whose critical parameter is a ratio of two equally aged devices
        rather than an absolute, and duty-cycling schemes that let devices recover.
        The last one is worth noticing — <b>BTI partially recovers when the stress is
        removed</b>, which turns a physics constant into a design variable.""")

    c.글("""A transistor that meets its specification on the day it is made will not meet
    it in ten years. Thresholds shift, oxides break down, and metal atoms move. None of
    this is a defect: it is the ordinary ageing of the materials, it is characterised
    and modelled by the foundry, and it is <b>your job to budget for it</b> — because a
    timing signoff at time zero is a signoff for a chip that has not yet been
    shipped.""")

    # ------------------------------------------------------------------
    c.절("T14.1 The four mechanisms, and what each one eats")

    c.날것(표("The mechanisms you must budget for",
        ["Mechanism", "What physically happens", "What it degrades",
         "Worst when"],
        [["<b>BTI</b> (bias temperature instability)",
          "Charge trapping at the oxide interface under gate bias",
          "|V<sub>th</sub>| rises → speed falls, offsets drift",
          "High temperature, high V<sub>GS</sub>, DC bias (no recovery)"],
         ["<b>HCI</b> (hot carrier injection)",
          "Energetic carriers damage the drain-end oxide",
          "Drive current falls, mismatch grows",
          "High V<sub>DS</sub> <i>while switching</i> — fast edges, high activity"],
         ["<b>TDDB</b> (time-dependent dielectric breakdown)",
          "The gate oxide eventually conducts, permanently",
          "The device — it is a <b>hard failure</b>, not a drift",
          "High field, thin oxide, large total gate area"],
         ["<b>Electromigration</b>",
          "Momentum transfer from electrons moves metal atoms",
          "Wires open or short — also a hard failure",
          "High current density, DC (unidirectional) current, high temperature"]]))

    c.날것(짚기("""Two of these are <b>drifts</b> and two are <b>failures</b>, and they
    need different arithmetic. A drift is budgeted as a margin: you sign off timing with
    a degraded library and accept the area cost. A failure is budgeted as a
    <i>probability</i>: you compute the fraction of parts that fail before the lifetime
    target and compare it against the allowed FIT rate. Mixing the two — for instance
    treating TDDB as 'a bit more V<sub>th</sub> drift' — produces a design that meets
    its timing and fails its qualification."""))

    # ------------------------------------------------------------------
    c.절("T14.2 Acceleration: how a 1000-hour test predicts ten years")

    c.날것(개념(
        "아레니우스 가속 (Arrhenius acceleration)",
        f"""<p>Wear-out rates follow exp(−E<sub>a</sub>/kT), so raising the temperature
        multiplies the rate by a computable factor:
        AF = exp[(E<sub>a</sub>/k)(1/T<sub>use</sub> − 1/T<sub>stress</sub>)].</p>
        <p>With E<sub>a</sub> = 0.9 eV, stressing at 125 °C instead of 85 °C is
        <b>{수(_AF온도(0.9,85,125),3)}× faster</b> — which is how a 1000-hour oven test
        stands in for years of field use. The same arithmetic run backwards is the
        familiar rule of thumb: every 10 °C of cooling roughly
        {수(_AF온도(0.9,100,110),3)}× the life.</p>""",
        어디에="Qualification planning, and the argument with the thermal engineer "
             "about junction temperature.",
        언제="Whenever a lifetime is claimed. A lifetime without a temperature is not a "
            "specification.",
        어떻게="Pick E<sub>a</sub> from the foundry's model for the mechanism in "
             "question — <b>not a generic 0.7 eV</b> — and state it alongside the "
             "result, because the answer depends on it strongly.",
        산업코드="""# The same 1000-hour test, read with three different activation energies.
# This is why Ea must be quoted with any lifetime claim.
Ea = {0.7: 9.8, 0.9: 18.7, 1.1: 35.9}     # AF from 85 C to 125 C
# 1000 h at 125 C therefore stands for 9800 h / 18700 h / 35900 h at 85 C
#   -> 1.1 years / 2.1 years / 4.1 years.
# The SAME DATA supports "passes 1 year" or "passes 4 years" depending on a
# number the report often does not state.""",
        주의=f"""Activation energy is per <b>mechanism</b>, and using one number for a
            mixed failure population is the standard way to get a lifetime wrong by
            {수(_AF온도(1.1,85,125)/_AF온도(0.7,85,125),3)}×. If a qualification report
            does not say which mechanism and which E<sub>a</sub>, it has not made a
            claim you can check."""))

    c.날것(표("Acceleration factor from 85 °C use to 125 °C stress",
        ["E_a", "AF (125 °C vs 85 °C)", "10 °C cooling buys", "1000 h stress stands for"],
        [[수(Ea, 2, "eV"), 수(_AF온도(Ea, 85, 125), 3) + "×",
          수(_AF온도(Ea, 100, 110), 3) + "×",
          수(1000 * _AF온도(Ea, 85, 125) / 8760, 3, "년")]
         for Ea in (0.7, 0.9, 1.1)]))

    c.날것(예제(
        "A 1000-hour BTI stress: what does it say about ten years?",
        f"""BTI's threshold shift grows as a power law in time, ΔV<sub>th</sub> ∝
        t<sup>n</sup>, with n typically {수(0.15,3)}–{수(0.25,3)}. A part is stressed
        for 1000 hours and shows some shift.""",
        f"""Ten years is {수(수명시간,6)} hours, or {수(수명시간/1000,4)}× the stress
        time. The shift grows by that ratio raised to n.""",
        f"""n = {수(0.15,3)} → {수(_BTI외삽(0.15),3)}×;
        n = {수(0.20,3)} → {수(_BTI외삽(0.20),3)}×;
        n = {수(0.25,3)} → {수(_BTI외삽(0.25),3)}×.
        <b>The same measurement predicts a shift that differs by
        {수(_BTI외삽(0.25)/_BTI외삽(0.15),3)}× depending on an exponent nobody
        measured in this test.</b>""",
        """Extrapolating a power law from one time point. With a single stress duration,
        n is an assumption, not a measurement — and the answer is roughly linear in it.
        A credible BTI characterisation stresses at <b>several durations</b> and fits n;
        anything else is a number with an unstated multiplier.""",
        덧=표("Voltage acceleration, for the same reason",
             ["γ", "100 mV overvoltage ages it"],
             [[수(g, 3, "/V"), 수(_전압가속(g, 0.1), 3) + "×"]
              for g in (8, 12, 16)])))

    c.날것(짚기(f"""Voltage acceleration is the reason a design must never be
    characterised only at nominal. At γ = {수(12,2,'/V')} — a typical value — running
    100 mV above nominal ages the device {수(_전압가속(12,0.1),3)}× faster, so a rail
    that overshoots during a DVFS transition can consume years of budget in seconds.
    <b>The reliability question about DVFS is not the average voltage; it is the
    transients.</b>"""))

    # ------------------------------------------------------------------
    c.절("T14.3 Electromigration, and the rule that surprises digital designers")

    c.날것(개념(
        "블랙 식 (Black's equation) and why AC is easier than DC",
        f"""<p>MTF = A·J<sup>−n</sup>·exp(E<sub>a</sub>/kT), with n ≈ 2 for the usual
        regime. Lifetime falls as the <b>square</b> of current density and rises
        exponentially as temperature falls: at E<sub>a</sub> = 0.9 eV, cooling a wire
        from {수(110,3,'°C')} to {수(85,3,'°C')} buys
        {수(_AF온도(0.9,85,110),3)}× its life.</p>
        <p>The part that surprises digital designers: <b>bidirectional (AC) current is
        far less damaging than unidirectional (DC)</b>, because atoms pushed one way are
        partly pushed back. EM rules therefore give a much higher limit for signal nets
        than for power nets — and the nets that fail are almost always power, clock
        drivers, or any signal with a duty cycle far from 50 %.</p>""",
        어디에="Power grid sizing, clock-tree driver outputs, and the output stage of "
             "any driver with a static current.",
        언제="Checked automatically by the EM/IR tools at signoff — but <b>designed "
            "for</b> long before, since the grid's width is a floorplan decision.",
        어떻게="Keep current density below the foundry's limit at the <b>maximum</b> "
             "junction temperature, and remember the limit depends on the duty cycle "
             "and direction. Vias are usually the binding constraint, not wires: one "
             "via carries far less than the wire it connects.",
        산업코드="""# What the EM report actually flags, in order of frequency:
#   1. VIAS on power straps -- a single via where four were needed
#   2. Clock driver outputs -- high activity, high capacitance, one direction of
#      net current per edge
#   3. Long thin nets from a pad to a block at the far side of the die
# The fix for (1) and (2) is always the same: more parallel vias, wider metal,
# and it is FREE if done at floorplan time and expensive after routing.""",
        주의=f"""EM limits are specified at a temperature. A design checked at 85 °C
            and run at 110 °C has {수(_AF온도(0.9,85,110),3)}× less margin than the
            report says — and the junction temperature of a block just woken from sleep
            is not the average temperature anybody simulated."""))

    # ------------------------------------------------------------------
    c.절("T14.4 Designing for the tenth year, not the first")

    c.날것(표("How each mechanism enters the design flow",
        ["Mechanism", "Enters as", "Who owns it"],
        [["BTI / HCI", "A <b>degraded timing library</b> — signoff runs twice, at "
          "time zero and at end of life", "Timing signoff; the margin is the design's"],
         ["TDDB", "A limit on gate area at a given field, and a FIT budget",
          "Foundry rules; the designer chooses the oxide type"],
         ["Electromigration", "Current-density checks on every net",
          "Physical design, but the grid was decided at floorplan"],
         ["Ageing mismatch", "σ(ΔV<sub>th</sub>) grows over life, so offsets and "
          "V<sub>min</sub> get worse", "Analog designer — and it is often forgotten"]]))

    c.날것(사고("""The last row is the one that catches analog designs. BTI is not only a
    mean shift; it has a <b>spread</b>, and that spread adds to the mismatch of T12. A
    comparator whose offset was trimmed at test drifts back, because the two halves age
    differently — and they age differently precisely because they carry different
    duty cycles. <b>A trimmed offset is trimmed for the day it was trimmed.</b> Designs
    that must hold an offset for ten years either re-trim in the field (auto-zero, T10)
    or are built so that both halves age identically by construction."""))

    c.날것(개념(
        "노화 인지 설계 (ageing-aware design)",
        """<p>Three things make a design survive its tenth year, and none of them is
        margin alone:</p>
        <ul>
        <li><b>Balance the stress.</b> If a differential pair's two sides see different
        duty cycles, they will diverge. Swapping roles periodically (chopping, T10) makes
        them age together.</li>
        <li><b>Prefer ratios of aged devices.</b> A reference built from two devices that
        age identically drifts far less than one built from an absolute.</li>
        <li><b>Allow recovery.</b> BTI recovers partially when the bias is removed; a
        circuit that is DC-biased for ten years gets the worst case, and one that is
        duty-cycled does not.</li>
        </ul>""",
        어디에="Any IP with a ten-year or automotive lifetime target, and any analog "
             "block whose accuracy is trimmed.",
        언제="At topology selection. None of these can be retrofitted.",
        어떻게="Run the ageing simulation the PDK provides (a degraded model deck), "
             "with the <b>real</b> duty cycles — not with everything at DC — and check "
             "the offset and V<sub>min</sub> at end of life, not just the timing.",
        산업코드="""* Ageing simulation: the same netlist, twice, with the PDK's aged models.
.lib 'models/pdk.lib' tt
.option reliability_analysis          $ vendor-specific; every PDK has one
.param age_years = 10
.param duty_cycle = 0.5               $ THIS is the parameter people get wrong --
                                      $ a DC-biased device is duty_cycle = 1.0
.op
.measure op vth_shift param='v(m1.vth_aged) - v(m1.vth_fresh)'
* Sign off BOTH decks. A design that only passes fresh is a design that only
* passes on the day it is made.""",
        주의="""Ageing models are statistical and conservative, and running them at the
            worst corner <i>and</i> worst duty cycle <i>and</i> worst temperature
            simultaneously produces a design that cannot be built. The skill is
            choosing which combinations are physically possible — a DC-biased device at
            maximum temperature is, but maximum activity at maximum temperature and
            minimum voltage usually is not."""))

    # ------------------------------------------------------------------
    c.절("T14.5 What to do with this on Monday")

    c.날것(쓰는자리([
        ["BTI · HCI", "Timing signoff, run twice",
         "The end-of-life margin, and therefore the area"],
        ["아레니우스 · 가속계수", "Qualification planning and datasheet claims",
         "What a 1000-hour test is allowed to say"],
        ["블랙식 · 일렉트로마이그레이션", "Power grid and driver sizing at floorplan",
         "Wire widths and via counts — free early, expensive late"],
        ["노화인지설계", "Topology selection for anything trimmed",
         "Whether the trim survives to year ten"],
        ["수명목표", "The datasheet",
         "The lifetime, <b>with its temperature and duty cycle</b> — or it says nothing"]]))

    c.글(f"""The numbers to carry: at E<sub>a</sub> = {수(0.9,2,'eV')} a 125 °C stress
    runs {수(_AF온도(0.9,85,125),3)}× faster than 85 °C use, so 1000 hours stands for
    {수(1000*_AF온도(0.9,85,125)/8760,3,'년')} — and with a different E<sub>a</sub> the
    same data says {수(1000*_AF온도(0.7,85,125)/8760,3,'년')} or
    {수(1000*_AF온도(1.1,85,125)/8760,3,'년')}. A lifetime claim without its
    E<sub>a</sub>, its temperature and its duty cycle is not a claim. And 100 mV of
    overvoltage ages a device {수(_전압가속(12,0.1),3)}× faster, which is why the
    transients of a DVFS scheme matter more than its average.""")

    c.글("""The next chapter is where all of this becomes geometry: the layout, where
    a schematic that is correct in every respect can still fail.""")

    return c.완성()
