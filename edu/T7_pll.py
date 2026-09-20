# -*- coding: utf-8 -*-
"""T7 -- The phase-locked loop: a feedback system whose output is time."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

# --- 설계점 (2.5 GHz 출력, 25 MHz 기준) ----------------------------------
F0    = 2.5e9
FREF  = 25e6
N     = int(F0 / FREF)          # 100
ICP   = 100e-6                  # A
KVCO  = 500e6 * 2 * math.pi     # rad/s/V
ZETA  = 0.9
FL    = 1e6                     # 목표 루프 대역폭
# 출력에서 본 위상잡음 밀도 (rad^2/Hz)
S_IN  = 1e-11                   # 루프 안 평탄 바닥 (기준·분주기·CP) ~ -110 dBc/Hz
S_V1M = 1e-10                   # VCO, 1 MHz 오프셋에서 ~ -100 dBc/Hz


def _wn():
    return 2 * math.pi * FL / (2 * ZETA)


def _CR():
    wn = _wn()
    C = ICP * KVCO / (2 * math.pi * N * wn ** 2)
    R = 2 * ZETA / (wn * C)
    return C, R


def _정착():
    return 4.0 / (ZETA * _wn())


def _svco(f):
    return S_V1M * (1e6 / f) ** 2


def _지터(fL, f0=F0):
    """루프 대역폭 fL 일 때의 적분 지터.  (rad rms, s rms)"""
    tot, f = 0.0, 1e3
    while f < 1e9:
        df = f * 0.02
        LP = 1 / (1 + (f / fL) ** 2)
        HP = (f / fL) ** 4 / (1 + (f / fL) ** 2) ** 2
        tot += (S_IN * LP + _svco(f) * HP) * df
        f += df
    j = math.sqrt(2 * tot)
    return j, j / (2 * math.pi * f0)


쓸기 = [(fL, _지터(fL)[1]) for fL in (1e5, 3e5, 6e5, 1e6, 2e6, 3e6, 6e6, 1e7, 2e7)]
최적 = min(쓸기, key=lambda t: t[1])


def ch_pll():
    C, R = _CR()
    c = 장(
        "T7", "The Phase-Locked Loop — a Feedback System Whose Output Is Time",
        "Every other block treats the clock as given. This one makes it, and the "
        "trade it faces has no good side: the bandwidth that suppresses one noise "
        "source lets in the other.",
        쓰는것=["전압", "전류", "주파수", "위상", "적분", "미분", "로그",
              "확률", "표준편차", "트랜스컨덕턴스", "출력저항", "RC지연",
              "열잡음", "플리커잡음", "구경지터", "SNR", "잡음대역폭"],
        내놓는것=["위상검출기", "전하펌프", "루프필터", "전압제어발진기",
                "분주기", "고리이득", "감쇠비", "자연주파수", "루프대역폭",
                "위상잡음", "적분지터", "기준스퍼", "분수분주", "델타시그마변조",
                "확산스펙트럼", "락검출", "전원푸싱"],
        특허="""PLL patents are almost never about the loop equation — that is 1930s
        control theory. They are about <b>what the loop is allowed to see</b>: fractional
        dividers whose quantisation noise is shaped away from the band that matters;
        charge pumps whose up/down mismatch is cancelled by replication rather than
        trimmed; digital loops that replace the analog filter with an accumulator and
        therefore scale with the process; and spread-spectrum schemes that modulate the
        divider to move radiated energy off a regulated frequency. All of these are
        arrangements around an unchanged loop.""")

    c.글("""A PLL is the only block in this book whose output quantity is <i>time</i>.
    Everything else in the chapters so far has treated the clock as an input with some
    jitter attached; here the jitter is manufactured, and the design question is how to
    manufacture as little of it as possible from two sources that respond to the loop in
    opposite ways.""")

    c.날것(그림(sch.블록도(
        [["PFD", "CP", "LPF", "VCO", "÷N"]],
        칸=96, 간격=28,
        설명={"PFD": "phase-frequency\ndetector", "CP": "charge pump\nI_CP",
             "LPF": "R + C\n(the zero)", "VCO": "K_VCO", "÷N": "divider\nx N noise"}),
        "The charge-pump PLL. The divider closes the loop, and it is also what "
        "multiplies every noise source inside the loop by N."))

    # ------------------------------------------------------------------
    c.절("T7.1 What the loop actually controls")

    c.날것(유도("From the phase detector to a second-order system", [
        ("The phase-frequency detector produces a signal proportional to the phase "
         "<i>error</i> between the reference and the divided output.",
         "Phase, not frequency — frequency is the derivative, which is why a PLL locks "
         "frequency as a side effect of locking phase and why the loop has an inherent "
         "integrator."),
        ("The charge pump converts that error into a current of ±I<sub>CP</sub>, "
         "applied for the duration of the error pulse.",
         "The average current is I<sub>CP</sub>·Δφ/2π — a linear phase-to-current gain "
         "of I<sub>CP</sub>/2π A/rad."),
        ("The filter integrates that current on C, and the VCO integrates voltage into "
         "phase with gain K<sub>VCO</sub>.",
         "<b>Two integrators in the loop.</b> That is why a plain capacitor makes the "
         "loop unconditionally unstable and why a zero (the series R) is not optional."),
        ("Open-loop gain: G(s) = (I<sub>CP</sub>/2π)·(1/sC)(1+sRC)·(K<sub>VCO</sub>/s)·(1/N).",
         "Two poles at the origin and a zero at 1/RC. The zero supplies the phase margin."),
        ("Closed-loop this is a standard second-order system with "
         "ω<sub>n</sub> = √(I<sub>CP</sub>K<sub>VCO</sub>/(2πNC)) and "
         "ζ = (R/2)√(I<sub>CP</sub>K<sub>VCO</sub>C/(2πN)).",
         "Everything else in this chapter is an argument about where to place those two "
         "numbers."),
        (f"For the worked design (f<sub>0</sub> = {수(F0/1e9,3,'GHz')}, "
         f"f<sub>ref</sub> = {수(FREF/1e6,3,'MHz')}, N = {N}, "
         f"I<sub>CP</sub> = {수(ICP*1e6,3,'µA')}, "
         f"K<sub>VCO</sub> = {수(KVCO/(2*math.pi)/1e6,3,'MHz/V')}), targeting "
         f"f<sub>L</sub> = {수(FL/1e6,2,'MHz')} with ζ = {수(ZETA,2)}: "
         f"C = {수(C*1e12,3,'pF')}, R = {수(R/1e3,3,'kΩ')}.",
         f"Settling to 1 % takes about 4/(ζω<sub>n</sub>) = {수(_정착()*1e6,3,'µs')} — "
         "which is the number a system architect actually asks for."),
    ]))

    c.날것(짚기(f"""The divider is where the unpleasantness enters. Every noise source
    <i>inside</i> the loop — reference, PFD, charge pump, divider — is multiplied by
    N² in power at the output, which is {수(20*math.log10(N),3,'dB')} for N = {N}. This
    is why a PLL that multiplies by 100 has a far worse in-band phase noise floor than
    the crystal it started from, and why designs that need very low jitter use the
    highest reference frequency they can (a smaller N), not the most convenient one."""))

    # ------------------------------------------------------------------
    c.절("T7.2 The trade with no good side: loop bandwidth")

    c.날것(개념(
        "Which noise the loop suppresses, and which it lets through",
        """<p>The loop is a <b>low-pass</b> for everything inside it (reference, PFD,
        charge pump, divider) and a <b>high-pass</b> for the VCO. Inside the loop
        bandwidth the feedback forces the output to track the reference, so the VCO's
        own noise is corrected; outside it, the loop is too slow to correct anything and
        the VCO runs free.</p>
        <p>So widening the loop suppresses more VCO noise and admits more reference-path
        noise; narrowing it does the reverse. <b>There is always an optimum, and it is
        the only design variable in the loop that has one.</b></p>""",
        어디에="Any clock generator, every SerDes transmit and receive PLL, the clock "
             "for a data converter, and the on-chip clock of an SoC that must meet a "
             "jitter budget.",
        언제="Fixed early: the loop bandwidth constrains the VCO specification and the "
            "reference choice, and changing it late changes both.",
        어떻게="Integrate the shaped densities and sweep. The optimum is usually where "
             "the in-band floor and the VCO's free-running noise cross — which can be "
             "read straight off a phase-noise plot without any integration.",
        산업코드="""# Phase noise measurement, and the integration that turns it into jitter.
# The instrument gives L(f) in dBc/Hz; the number the customer wants is rms jitter.
#   sigma_t = sqrt( 2 * integral( 10^(L(f)/10) df ) ) / (2*pi*f0)
# THE INTEGRATION LIMITS ARE PART OF THE SPECIFICATION.
#   PCIe: 10 kHz - 20 MHz (with the protocol's own filter applied)
#   JESD204B: 100 Hz - 20 MHz
#   Ethernet: often 12 kHz - 20 MHz
# A jitter number quoted without its limits is not comparable to any other one.""",
        주의="""Integrating from 'DC' is meaningless — the integral of the VCO's
            1/f<sup>3</sup> region diverges, and every standard therefore specifies a
            lower limit. Two vendors quoting 'sub-picosecond jitter' over different
            limits are not making comparable claims, and the narrower limit usually
            belongs to the worse part."""))

    c.날것(그림(sch.곡선(
        [("integrated jitter", [(fL / 1e6, t * 1e15) for fL, t in 쓸기], "#c0392b")],
        가로="loop bandwidth (MHz)", 세로="rms jitter (fs)",
        표시=[(최적[0] / 1e6, 최적[1] * 1e15, f"{수(최적[0]/1e6,2,'MHz')}")],
        가로눈금=[0.1, 5, 10, 20]),
        f"""Integrated jitter against loop bandwidth for the worked design (in-band
        floor ≈ −110 dBc/Hz, VCO ≈ −100 dBc/Hz at 1 MHz). The optimum is
        {수(최적[0]/1e6,2,'MHz')} at {수(최적[1]*1e15,3,'fs')} rms — and it is
        <b>shallow</b>: 1 MHz and 3 MHz are within
        {수((max(t for fL,t in 쓸기 if fL in (1e6,3e6))/최적[1]-1)*100, 2, '%')} of it.
        Choose the side that eases whichever block is harder."""))

    c.날것(표("Integrated jitter against loop bandwidth (computed, not recalled)",
        ["Loop BW", "rms phase", "rms jitter @ 2.5 GHz"],
        [[수(fL/1e6, 3, "MHz"), 수(_지터(fL)[0]*1e6, 4, "µrad"), 수(t*1e15, 4, "fs")]
         for fL, t in 쓸기]))

    c.날것(짚기("""The shallowness is the practical result. A factor of three in loop
    bandwidth costs a few per cent of jitter, so the bandwidth should be chosen for the
    <b>other</b> constraints it controls — settling time, reference spur suppression,
    tolerance to VCO pulling — rather than squeezed against a flat optimum. Engineers
    who spend a week finding the exact minimum have optimised the one axis that does not
    move."""))

    # ------------------------------------------------------------------
    c.절("T7.3 Spurs: the errors that are not noise")

    c.날것(정의("기준스퍼 (reference spur)",
        "A discrete tone at an offset equal to the reference frequency (and its "
        "harmonics), caused by any periodic disturbance of the control voltage at the "
        "comparison rate — charge-pump up/down mismatch, leakage on the filter "
        "capacitor, or coupling from the reference into the VCO."))

    c.날것(표("Where a spur comes from, and what actually removes it",
        ["Cause", "Mechanism", "Fix that works", "Fix that does not"],
        [["CP current mismatch", "Up and down currents differ, so the loop must sit at "
          "a non-zero phase error and the pump fires every cycle",
          "Replica bias that servos I<sub>up</sub> to I<sub>dn</sub>",
          "Lowering I<sub>CP</sub> — it scales the spur and the loop gain together"],
         ["Filter leakage", "Capacitor and switch leakage drain the control node "
          "between updates", "Thicker-oxide devices on the filter node; larger C",
          "More loop gain — the disturbance is at the input"],
         ["Supply / substrate coupling", "Reference edges couple into the VCO directly",
          "Physical separation, a regulator for the VCO, differential tuning",
          "Anything inside the loop — <b>the loop never sees this path</b>"],
         ["Fractional-N quantisation", "The divider alternates between integers, so the "
          "phase error is periodic by construction",
          "ΔΣ modulation to shape it, plus enough loop filtering",
          "A slower reference"]]))

    c.날것(개념(
        "분수분주 (fractional-N) and the noise it creates on purpose",
        """<p>An integer-N loop can only produce multiples of the reference. Dividing by
        an average of N.f — switching between N and N+1 — produces any frequency, at the
        cost of a periodic phase error whose spectrum is concentrated at the fraction's
        repeat rate. A ΔΣ modulator <b>randomises and shapes</b> that sequence so the
        error becomes high-frequency noise, which the loop filter then attenuates.</p>
        <p>The trade is explicit: fractional-N buys frequency resolution and pays for it
        in noise <i>outside</i> the loop bandwidth, which is exactly the region a wide
        loop cannot filter. <b>This is why fractional-N designs tend to use narrower
        loops than integer-N ones</b>, which in turn makes the VCO's own noise matter
        more — the chapter's central trade, reappearing.</p>""",
        어디에="Any system needing a frequency that is not a multiple of the available "
             "crystal: radio LOs, SerDes with several line rates from one reference, "
             "audio clocks, spread-spectrum clocking.",
        언제="When the required output frequency grid is finer than the reference. "
            "Prefer integer-N whenever the system architecture allows choosing the "
            "crystal — it is always quieter.",
        어떻게="Choose the modulator order (2nd–3rd is usual), check for <b>idle tones</b> "
             "at rational fractions, and verify that the shaped noise is far enough "
             "outside the loop bandwidth that the filter's roll-off has caught it.",
        산업코드="""// Behavioural PLL for system simulation -- real-valued, event driven.
// It models what the DIGITAL side needs (frequency, lock time, jitter injection)
// and nothing else. Replacing this with a transistor model in an SoC simulation is
// how a regression that used to take 10 minutes starts taking a week.
module pll_behav #(parameter real FREF=25.0e6, parameter int N=100,
                   parameter real LOCK_US=2.0, parameter real JIT_RMS=0.8e-12)
                  (input logic ref_clk, rst_n, output logic out_clk, output logic locked);
    real period = 1.0/(FREF*N);
    initial begin out_clk = 0; locked = 0; end
    always #(1s*period/2) out_clk = ~out_clk;             // ideal edges
    initial begin @(posedge rst_n); #(LOCK_US*1us); locked = 1; end
endmodule
// SDC: the output is a GENERATED clock -- declaring it as a second create_clock
// makes STA treat the two domains as unrelated and silently stops checking paths.
// create_generated_clock -name pll_out -source [get_ports ref_clk] \\
//     -multiply_by 100 [get_pins u_pll/out_clk]""",
        주의="""Declaring the PLL output with <code>create_clock</code> instead of
            <code>create_generated_clock</code> is a common and expensive SDC error: the
            tool then has no phase relationship between reference and output, treats
            every crossing between them as asynchronous, and <b>stops reporting the
            paths you care about</b> while the report still looks clean."""))

    # ------------------------------------------------------------------
    c.절("T7.4 What actually breaks")

    c.날것(표("Failures that do not show up in the loop equations",
        ["Failure", "Symptom", "Root cause", "What finds it"],
        [["Supply pushing", "Output frequency moves with V<sub>DD</sub>; jitter "
          "correlates with digital activity",
          "K<sub>VCO,supply</sub> is not zero — the VCO is a voltage-controlled "
          "oscillator in more ways than intended",
          "Sweep the supply in simulation and measure df/dV; budget it against the "
          "PDN's ripple (T13)"],
         ["VCO pulling", "A spur appears at the offset of a nearby strong signal",
          "Injection locking through substrate or supply from another oscillator or a "
          "high-power output", "Two-tone bench measurement; floorplan review"],
         ["False lock", "Locks to a harmonic or to the wrong edge; works after reset "
          "sometimes", "A phase detector without frequency capability, or a divider "
          "that starts in an illegal state", "Start-up sweeps across corners and "
          "initial conditions — not one nominal run"],
         ["Lock detect lies", "'Locked' asserts before the loop has settled",
          "The detector compares phase within a window that is wider than the "
          "specification needs", "Check the detector's window against the actual "
          "settling time; make the system wait for both"]]))

    c.날것(사고("""Supply pushing is the one that ambushes digital-heavy SoCs. A VCO with
    a supply sensitivity of 1 %/V sitting on a rail with 30 mV of activity-dependent
    ripple sees its frequency modulated at whatever rate the digital load switches —
    which is not a constant, and is correlated with exactly the workload the customer
    runs. It appears in the lab as 'jitter that depends on the software'. The fix is a
    dedicated regulator for the VCO, and it must be designed in from the start because
    it changes the floorplan and the supply count."""))

    # ------------------------------------------------------------------
    c.절("T7.5 What to do with this on Monday")

    c.날것(쓰는자리([
        ["고리이득 · 감쇠비 · 루프대역폭", "Loop filter design",
         "C and R, and therefore settling time and area"],
        ["위상잡음 · 적분지터", "The jitter budget, before the VCO is specified",
         "Which of VCO noise or in-band floor you must spend on"],
        ["기준스퍼", "Spectrum compliance and receiver desense",
         "Charge-pump topology and the filter node's leakage budget"],
        ["분수분주 · 델타시그마변조", "Frequency planning",
         "Whether the crystal can be chosen to avoid fractional-N entirely"],
        ["전원푸싱", "Floorplan and PDN",
         "Whether the VCO needs its own regulator — a decision that is hard to reverse"]]))

    c.글(f"""The numbers to carry: for this worked design the loop filter is
    C = {수(C*1e12,3,'pF')} and R = {수(R/1e3,3,'kΩ')}, settling in
    {수(_정착()*1e6,3,'µs')}; the jitter optimum sits at
    {수(최적[0]/1e6,2,'MHz')} of loop bandwidth and is <b>shallow enough that the
    bandwidth should be chosen for settling and spur requirements instead</b>. And the
    divider multiplies every in-band noise source by {수(20*math.log10(N),3,'dB')} —
    which is the strongest argument for the highest reference frequency the system can
    provide.""")

    c.글("""The next chapter puts this clock to work: a serial link, where the same
    jitter must be budgeted against a channel that has already closed most of the eye.""")

    return c.완성()
