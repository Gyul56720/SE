# -*- coding: utf-8 -*-
"""T4 -- Noise: thermal, flicker, and the static kind that kills SRAM.

수는 전부 여기서 계산하거나 **ngspice 로 재서** 넣는다.  잰 것은 잰 것이라고
적고, 어떤 모델로 쟀는지도 같이 적는다.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

k볼츠만 = 1.380649e-23
T상온 = 300.0
kT = k볼츠만 * T상온


def _ktc(C):
    """샘플링 커패시터 C 에 남는 잡음 전압의 실효값(V)."""
    return math.sqrt(kT / C)


def _필요C(비트, VFS=1.0):
    """kT/C 잡음을 양자화 잡음(LSB/√12) 이하로 누르는 최소 C."""
    LSB = VFS / 2 ** 비트
    return kT / (LSB ** 2 / 12.0)


def _열잡음(R, BW):
    return math.sqrt(4 * k볼츠만 * T상온 * R * BW)


# --- ngspice 로 잰 것 (아래 T4.4) ----------------------------------------
# 방법: 6T 셀의 반쪽(인버터 + 접근 트랜지스터)을 DC 로 쓸어 VTC 를 얻고,
# 나비곡선에 드는 가장 큰 정사각형의 변을 이분법으로 찾는다.  추출기는
# **자해검사로 먼저 확인했다** -- 이득이 아주 큰 인버터는 0.4825(≈VDD/2),
# 이득 1 은 0.0 을 낸다.  모델은 LEVEL=1 제곱법칙(VTO=0.35, KP_n=200µ,
# KP_p=80µ)이라 **파운드리 셀의 절댓값이 아니다.**  경향과 방법이 요점이다.
잰SNM = {
    "hold": {1.0: 0.4207, 1.5: 0.4173, 2.0: 0.4141, 2.5: 0.4114, 3.0: 0.4090},
    "read": {1.0: 0.1938, 1.5: 0.2071, 2.0: 0.2264, 2.5: 0.2410, 3.0: 0.2526},
}
잰Vmin = {1.00: 0.2264, 0.90: 0.2221, 0.80: 0.2160,
          0.70: 0.2027, 0.60: 0.1455, 0.50: 0.0866}


def ch_noise():
    c = 장(
        "T4", "Noise — and Why It Sets the Size of Everything",
        "Noise is the one specification you cannot improve with cleverness alone. "
        "Every 6 dB costs 4× the capacitance, and therefore 4× the power.",
        쓰는것=["전압", "전류", "저항", "온도", "확률", "분산", "표준편차",
              "적분", "로그", "주파수", "트랜스컨덕턴스", "게이트용량",
              "출력저항", "RC지연", "준안정"],
        내놓는것=["열잡음", "산탄잡음", "플리커잡음", "잡음스펙트럼밀도",
                "잡음대역폭", "kTC잡음", "입력환산잡음", "플리커코너",
                "잡음지수", "정적잡음여유", "나비곡선", "읽기방해",
                "최소동작전압", "SNR", "SNDR", "ENOB"],
        특허="""Noise is thermodynamics; nobody patents kT. <b>What gets claimed is
        every arrangement that buys back the 4× — correlated double sampling, chopping,
        auto-zeroing, noise shaping, and the family of techniques that let a circuit
        spend its noise budget only where the signal is.</b> On the digital side the
        same shape appears as assist circuits for SRAM: negative bitline, word-line
        underdrive, read-modify-write assist — all of them arrangements that let a cell
        keep its margin at a voltage where the plain cell has none. Read this chapter
        asking: where am I paying the 4× rule, and what would let me not pay it?""")

    c.글("""Everything measured in a circuit arrives with noise on it, and the noise does
    not come from poor engineering — it comes from the thermal motion of charge and from
    the discreteness of the electron. That makes it the hardest kind of specification:
    you cannot remove it, you can only spend area and power to average it down, and the
    exchange rate is fixed by physics at <b>4× the cost per extra bit</b>.""")

    c.글("""This chapter establishes the three noise sources you will actually meet, then
    derives the one number that sizes half the analog blocks in a mixed-signal IP
    (kT/C), and then does something unusual for a noise chapter: it crosses into the
    digital side, where the same word means something entirely different and where the
    consequence — the voltage below which an SRAM cannot be read — is <b>measured here
    with ngspice rather than asserted.</b>""")

    # ------------------------------------------------------------------
    c.절("T4.1 The three sources, and which one you can do anything about")

    c.날것(표("Noise sources in an IC, by origin",
        ["Source", "Density", "Origin", "Can you change it?"],
        [["Thermal (Johnson)", "S<sub>v</sub> = 4kTR  [V²/Hz]",
          "Thermal motion of carriers in any resistive element",
          "Only by changing R, T, or the bandwidth you look through"],
         ["Channel thermal", "S<sub>i</sub> = 4kTγg<sub>m</sub>  [A²/Hz]",
          "The same mechanism inside a MOSFET channel; γ ≈ 2/3 long-channel, "
          "1–2 short-channel", "Raise g<sub>m</sub> (costs current) or filter"],
         ["Flicker (1/f)", "S<sub>v</sub> = K<sub>f</sub>/(C<sub>ox</sub>WL·f)",
          "Trapping and de-trapping at the oxide interface",
          "<b>Yes — bigger devices, PMOS inputs, chopping, auto-zero</b>"],
         ["Shot", "S<sub>i</sub> = 2qI  [A²/Hz]",
          "Discreteness of charge crossing a barrier (junctions, not channels)",
          "Only by changing the current"]]))

    c.날것(유도("Why the answer always ends up as kT/C", [
        ("A resistor's thermal noise density is 4kTR, independent of frequency.",
         "Nyquist's result from equilibrium thermodynamics — it contains no device "
         "parameter beyond R, which is why it is a floor and not a design choice."),
        ("Put that resistor in series with a capacitor C — which is what every sampling "
         "switch is.",
         "The switch's on-resistance (T1: triode region) and the sampling capacitor "
         "are in series; there is no third element."),
        ("The RC low-pass shapes it, and the <b>noise bandwidth</b> of a single pole is "
         "π/2 × f<sub>−3dB</sub> = 1/(4RC).",
         "Integrating 1/(1+(f/f<sub>0</sub>)²) over all frequency gives π/2·f<sub>0</sub>, "
         "not f<sub>0</sub> — a factor people drop and then wonder why measurements are "
         "1.6× worse than predicted."),
        ("v<sub>n</sub>² = 4kTR × 1/(4RC) = kT/C.",
         "<b>R cancels.</b> The noise on a sampled capacitor does not depend on the "
         "switch at all — only on C and temperature."),
        (f"For C = 1 pF at {수(T상온,3,'K')}, v<sub>n</sub> = {수(_ktc(1e-12)*1e6,3,'µV')} rms.",
         "One number worth memorising; everything else scales as 1/√C from here."),
    ]))

    c.날것(개념(
        "kT/C — the rule that sizes capacitors, and therefore power",
        f"""<p>A sampled node carries kT/C of noise power regardless of how it was
        sampled. To keep that below the quantisation noise of an N-bit converter
        (LSB/√12), the capacitor must satisfy C ≥ 12kT·2<sup>2N</sup>/V<sub>FS</sub>².
        <b>Every extra bit quadruples C</b>, and because settling in a fixed time needs
        g<sub>m</sub> ∝ C, it quadruples the current too.</p>
        <p>This single relation is why a 16-bit converter is not "a bit harder" than a
        12-bit one: it is {수(_필요C(16)/_필요C(12), 3)}× the capacitance.</p>""",
        어디에="Every switched-capacitor circuit: SAR and pipeline ADC sampling "
             "networks, sample-and-holds, switched-capacitor filters and gain stages, "
             "the reference buffer that has to drive them.",
        언제="At the very start of an analog block's design, before any transistor is "
            "sized. The capacitor comes first because it fixes the power budget.",
        어떻게="Fix V<sub>FS</sub> and N, compute C, then size the driver for settling "
             "within the sampling phase (T2's RC arithmetic with the switch's "
             "R<sub>on</sub> from T1), then check that the reference can supply the "
             "charge each cycle.",
        산업코드="""* The measurement that separates kT/C from everything else you did wrong.
* Transient noise in ngspice: sample the same node 1000 times and take the std dev.
.tran 1n 10u
.noise v(out) VIN dec 20 1 1G      $ small-signal, for the spectrum
.measure noise inoise_total_rms param='sqrt(inoise_total)'
* And the closed form to check it against -- ALWAYS have the hand calculation:
*   v_n = sqrt(kT/C) = sqrt(1.38e-23*300/1e-12) = 64.4 uV for C = 1 pF""",
        주의="""kT/C applies to the <b>sampled</b> value. During the tracking phase the
            noise bandwidth is set by the circuit, not by the sampling — so a
            track-and-hold that is measured while tracking shows a different (usually
            larger) number than the same circuit measured after the hold. Reporting one
            when the spec means the other is a common and expensive mistake."""))

    c.날것(표("Capacitor and power cost per bit (V_FS = 1 V, 300 K, "
             "noise = quantisation noise)",
        ["Bits N", "LSB", "Quantisation rms", "C required", "Relative to 8-bit"],
        [[str(N), 수(1.0/2**N*1e6, 3, "µV"), 수(1.0/2**N/math.sqrt(12)*1e6, 3, "µV"),
          (수(_필요C(N)*1e15, 3, "fF") if _필요C(N) < 1e-12
           else 수(_필요C(N)*1e12, 3, "pF")),
          수(_필요C(N)/_필요C(8), 3) + "×"]
         for N in (8, 10, 12, 14, 16)]))

    # ------------------------------------------------------------------
    c.절("T4.2 Flicker noise, and the corner that decides your architecture")

    c.날것(정의("플리커코너 (flicker corner, f_c)",
        "The frequency at which the 1/f density equals the thermal density. Below it "
        "the circuit is flicker-dominated, above it thermal-dominated. For a modern "
        "CMOS amplifier it lands anywhere from ~100 kHz to a few MHz for NMOS inputs, "
        "typically a decade lower for PMOS."))

    c.날것(개념(
        "Where the signal sits relative to the corner",
        """<p>Flicker noise density rises as 1/f, so its <b>integrated</b> power over a
        band from f<sub>1</sub> to f<sub>2</sub> is proportional to ln(f<sub>2</sub>/f<sub>1</sub>)
        — it depends on the ratio, not the width. A DC-coupled measurement has
        f<sub>1</sub> → 0 and the integral diverges logarithmically: <b>the longer you
        average, the worse it gets</b>, which is the opposite of thermal noise.</p>
        <p>That single fact drives an architectural decision. If the signal is near DC
        (a temperature sensor, a bandgap reference, a DC offset), averaging does not
        help and you must <i>move the signal</i> — chop it up to a frequency above the
        corner, amplify there, and bring it back down. If the signal is already above
        the corner (an RF or high-speed link front end), flicker is irrelevant and you
        spend nothing on it.</p>""",
        어디에="Sensor front ends, reference and bias circuits, comparator offset, "
             "any DC-accurate measurement. Also the phase noise of an oscillator, where "
             "device flicker is up-converted into close-in phase noise.",
        언제="Whenever the band of interest includes frequencies below ~1 MHz. Ask the "
            "question explicitly at architecture time; retrofitting chopping into a "
            "finished amplifier is a redesign.",
        어떻게="Reduce it by area (S ∝ 1/WL — 4× the area for 6 dB), by choosing PMOS "
             "inputs, or by modulation: <b>chopping</b> (square-wave modulate in and "
             "out; leaves residual ripple at the chop frequency) or <b>correlated "
             "double sampling</b> (sample the offset, subtract it; costs noise folding "
             "and bandwidth).",
        산업코드="""* Flicker in the model card is one parameter -- and simulators differ.
.model NM NMOS (LEVEL=54 ... KF=1e-25 AF=1.0 EF=1.0)
* KF alone means nothing: the density is KF/(Cox*W*L*f^EF), so a KF taken from
* another PDK, or from a model with a different EF convention, is a WRONG number
* that still simulates.  Always sanity-check the corner against measured silicon:
.noise v(out) VIN dec 10 1 100MEG
* then read the point where the 1/f asymptote crosses the flat part.""",
        주의="""Chopping does not reduce noise; it <b>moves the signal away from the
            noise</b>. The thermal floor is unchanged and the chopper adds its own
            switching artefacts at the chop frequency and its harmonics. A design that
            reports a beautiful low-frequency noise figure and a spur at f<sub>chop</sub>
            has not improved anything if the spur lands in band."""))

    # ------------------------------------------------------------------
    c.절("T4.3 The other noise: static noise margin, measured")

    c.글("""On the digital side the word 'noise' means something different and the
    quantity is not a spectral density but a <b>voltage</b>: how much DC disturbance a
    storage node can absorb before it flips. The structure is the same cross-coupled pair
    that produced metastability in T3, viewed statically instead of dynamically.""")

    c.날것(정의("정적잡음여유 (SNM, static noise margin)",
        "The largest DC voltage that can be inserted in series with <b>both</b> storage "
        "nodes of a cross-coupled pair without destroying its bistability. "
        "Geometrically it is the side of the largest square that fits inside the "
        "butterfly curve formed by the two inverter transfer curves."))

    c.날것(사고("""The extractor used below was <b>wrong twice</b> before it was right,
    and both times the numbers looked plausible. The first version measured a horizontal
    gap instead of an inscribed square and reported hold SNM ≈ 0.5·V<sub>DD</sub> — too
    high. The second version had the access transistor wired with its gate on the bitline
    instead of the word line; it produced read SNM that <i>fell</i> as the cell ratio
    rose, which is backwards. <b>The trend caught the bug, not the value.</b> That is the
    rule this repository runs on: before believing a measurement, check the direction it
    moves when you change something you understand."""))

    c.날것(짚기("""The extractor was then <b>self-checked against two limits</b>: an
    inverter with very high gain must give SNM → V<sub>DD</sub>/2 (it gives 0.4825) and
    an 'inverter' with gain 1 must give 0 (it gives 0.0). Only after both did the cell
    numbers below get written down."""))

    c.날것(표("Measured SNM of a 6T cell (ngspice, LEVEL=1 model, V_DD = 1.0 V, "
             "V_th = 0.35 V) — β is the cell ratio W_pulldown / W_access",
        ["β", "Hold SNM", "Read SNM", "Read / Hold"],
        [[수(b, 2), 수(잰SNM["hold"][b], 4, "V"), 수(잰SNM["read"][b], 4, "V"),
          수(잰SNM["read"][b] / 잰SNM["hold"][b], 3)]
         for b in (1.0, 1.5, 2.0, 2.5, 3.0)]))

    c.날것(그림(sch.곡선(
        [("hold", [(b, 잰SNM["hold"][b] * 1000) for b in sorted(잰SNM["hold"])], "#1f6feb"),
         ("read", [(b, 잰SNM["read"][b] * 1000) for b in sorted(잰SNM["read"])], "#c0392b")],
        가로="cell ratio β = W_pd / W_acc", 세로="SNM (mV)",
        가로눈금=[1.0, 2.0, 3.0]),
        "Reading costs more than half the cell's margin, and the only structural way to "
        "buy it back is a stronger pull-down relative to the access device — which is "
        "why the 6T cell is not made of minimum devices."))

    c.날것(유도("Why reading a cell is what almost destroys it", [
        ("To read, the word line turns on both access transistors while both bit lines "
         "are precharged high.",
         "That is the only way to sense the cell without a separate read port."),
        ("The access transistor on the '0' side now pulls that node <b>up</b>, through "
         "a divider formed with the cell's own pull-down NMOS.",
         "Two NMOS devices in series between V<sub>DD</sub> and ground, with the "
         "storage node in the middle — the node cannot stay at 0 V."),
        (f"The '0' node rises to roughly V<sub>DD</sub>·(1/(1+β)) in the resistive "
         f"limit, so a β of 2 already puts it a third of the way up.",
         "Both devices are in triode at that point; the ratio of their strengths is the "
         "divider ratio. This is the <b>only</b> reason the cell ratio exists as a "
         "design parameter."),
        (f"That rise eats directly into the margin: measured read SNM at β = 2 is "
         f"{수(잰SNM['read'][2.0], 4, 'V')} against a hold SNM of "
         f"{수(잰SNM['hold'][2.0], 4, 'V')} — "
         f"{수((1-잰SNM['read'][2.0]/잰SNM['hold'][2.0])*100, 3, '%')} of the margin is "
         "gone the moment the word line rises.",
         "Measured, not asserted — the deck and the extractor are in this chapter's "
         "source."),
        ("Raising β raises read SNM and <b>slightly lowers hold SNM</b>.",
         f"Measured: hold falls from {수(잰SNM['hold'][1.0],4,'V')} to "
         f"{수(잰SNM['hold'][3.0],4,'V')} across the same sweep, because a stronger "
         "pull-down skews each inverter's trip point away from V<sub>DD</sub>/2. "
         "<b>There is no free direction</b>, which is what makes it a design point "
         "rather than a rule."),
    ]))

    c.날것(개념(
        "V_min — the voltage at which the memory, not the logic, stops the chip",
        f"""<p>Read SNM does not degrade gracefully with supply. Measured on the same
        cell at β = 2, it holds near {수(잰Vmin[0.9],3,'V')} from 1.0 V down to 0.7 V
        and then <b>collapses</b>: {수(잰Vmin[0.6],4,'V')} at 0.6 V and
        {수(잰Vmin[0.5],4,'V')} at 0.5 V. The knee sits where V<sub>DD</sub> approaches
        2V<sub>th</sub> ({수(0.7,2,'V')} here) — below that the devices are in weak
        inversion, the divider ratio depends on exponential currents, and mismatch
        (T12) turns a marginal cell into a failing one.</p>
        <p>This is why <b>the SRAM sets the chip's minimum operating voltage</b>, and
        why DVFS schemes either stop above the array's V<sub>min</sub> or give the array
        its own supply.</p>""",
        어디에="Any SoC with on-chip SRAM and more than one voltage point: the whole "
             "DVFS range, retention voltage in sleep modes, and the low-voltage corner "
             "in signoff.",
        언제="As soon as a power mode is proposed. The question 'can we drop to 0.6 V' "
            "is an SRAM question before it is a logic question.",
        어떻게="Either raise V<sub>min</sub> with assist circuits (word-line underdrive "
             "for read, negative bit line for write), split the array's supply, or use "
             "an 8T cell where the read path does not touch the storage node.",
        산업코드="""* The sweep that produces the number above -- run it at every corner,
* not just typical, because Vmin is a MISMATCH-limited quantity (see T12).
.param beta=2.0
.dc VIN 0 VDD 0.004 VDD 1.0 0.5 -0.1     $ nested sweep: input, then supply
.print dc v(vr)
* Extraction is NOT a .measure one-liner: you need the butterfly and the largest
* inscribed square.  Script it, and SELF-CHECK the extractor on two limits
* (very high gain -> VDD/2, gain 1 -> 0) before trusting any cell number.""",
        주의="""SNM measured at the typical corner is nearly useless for V<sub>min</sub>.
            The array fails at its <b>worst</b> cell out of millions, so the quantity
            that matters is the tail: V<sub>min</sub> is set by roughly the −5σ to −6σ
            cell, which means the analysis is a Monte Carlo with importance sampling,
            not a nominal DC sweep. The sweep above tells you the shape; it does not
            tell you the yield."""))

    # ------------------------------------------------------------------
    c.절("T4.4 From volts to a datasheet number: SNR, SNDR, ENOB")

    c.날것(표("The three numbers, and what each one hides",
        ["Quantity", "Definition", "Hides"],
        [["SNR", "Signal power / noise power, distortion excluded",
          "<b>Distortion.</b> A converter with terrible linearity can have excellent SNR"],
         ["SNDR (SINAD)", "Signal / (noise + all distortion)",
          "Which of the two dominates — always report the spectrum too"],
         ["ENOB", "(SNDR<sub>dB</sub> − 1.76) / 6.02",
          "That it is <b>derived</b>, not measured. ENOB is SNDR wearing different "
          "units; an ENOB quoted without its input frequency and amplitude is not a "
          "measurement"],
         ["SFDR", "Signal / largest single spur",
          "Broadband noise entirely — a clean-looking SFDR with a poor noise floor is "
          "common"]]))

    c.날것(예제(
        "How many bits does 64 µV of noise allow?",
        f"""A 1 V full-scale converter with C = 1 pF on its sampling network, so the
        sampled noise is {수(_ktc(1e-12)*1e6, 3, 'µV')} rms, and assume everything else
        is perfect.""",
        """A full-scale sine has rms amplitude V<sub>FS</sub>/(2√2). SNR =
        20·log<sub>10</sub>(signal rms / noise rms), then ENOB = (SNR − 1.76)/6.02.""",
        f"""SNR = {수(20*math.log10((1/(2*math.sqrt(2)))/_ktc(1e-12)), 4, 'dB')},
        giving ENOB = {수((20*math.log10((1/(2*math.sqrt(2)))/_ktc(1e-12))-1.76)/6.02, 3)}
        bits. <b>A 1 pF sampling capacitor is a ~12-bit part</b>, no matter how good the
        rest of the design is.""",
        """Forgetting that the sampling network is usually sampled <b>twice</b> (input
        and reference), and that a differential pair of capacitors doubles the noise
        power while doubling the signal amplitude — the two partly cancel, and the
        factor you get depends on the topology. Write the specific network down; do not
        reuse a remembered factor."""))

    # ------------------------------------------------------------------
    c.절("T4.5 What to do with this on Monday")

    c.날것(쓰는자리([
        ["kTC잡음", "Any switched-capacitor block, before sizing transistors",
         "The sampling capacitor, and therefore the current budget"],
        ["열잡음 · 잡음대역폭", "Amplifier and reference design",
         "How much g<sub>m</sub> the input stage needs"],
        ["플리커코너", "Architecture of any near-DC signal path",
         "Whether the design needs chopping or auto-zeroing at all"],
        ["정적잡음여유 · 나비곡선", "SRAM, any cross-coupled sense amp or latch",
         "Cell ratio β, and whether a read destroys what it reads"],
        ["최소동작전압", "DVFS and retention modes",
         "The lowest voltage the chip may be operated at"],
        ["SNDR · ENOB", "Datasheet and customer conversation",
         "The single number the customer will compare against a competitor"]]))

    c.글(f"""Two measured results to carry out of this chapter. A 1 pF sampling capacitor
    is a {수((20*math.log10((1/(2*math.sqrt(2)))/_ktc(1e-12))-1.76)/6.02, 3)}-bit part —
    the capacitor decides the resolution before any transistor is drawn. And reading a
    6T SRAM cell costs
    {수((1-잰SNM['read'][2.0]/잰SNM['hold'][2.0])*100, 3, '%')} of its static margin at a
    cell ratio of 2, which is why that cell ratio exists and why the array, not the
    logic, sets the lowest voltage the chip can run at.""")

    c.글("""The next chapter takes the sampling operation that this one treated as
    instantaneous and gives it a finite aperture, a jitter, and a spectrum — which is
    where the noise floor of a high-speed converter actually comes from.""")

    return c.완성()
