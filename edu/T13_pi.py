# -*- coding: utf-8 -*-
"""T13 -- Power integrity: the network every other block sits on."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

# --- 이 장의 PDN (가지 = ESR, ESL, C, 개수) -------------------------------
PDN = [(0.005, 5e-9, 100e-6, 10),     # 보드 벌크
       (0.010, 1e-9, 1e-6, 20),       # 세라믹
       (0.030, 0.2e-9, 100e-9, 50),   # 패키지
       (2.0, 0.002e-9, 20e-9, 1)]     # 온다이 decap
VDD, 리플, I최대 = 1.0, 0.05, 10.0


def _Z(f, 가지들=None):
    w = 2 * math.pi * f
    Y = 0j
    for R, L, C, n in (가지들 or PDN):
        Y += 1 / complex(R / n, w * L / n - 1 / (w * C * n))
    return abs(1 / Y)


def _목표():
    return VDD * 리플 / I최대


def _프로필(가지들=None, 배율=1.03):
    f, 점 = 1e3, []
    while f < 1e10:
        점.append((f, _Z(f, 가지들)))
        f *= 배율
    return 점


def _봉우리(가지들=None):
    점 = _프로필(가지들)
    return [(f, z) for i, (f, z) in enumerate(점)
            if 0 < i < len(점) - 1 and z > 점[i-1][1] and z > 점[i+1][1]]


# ESR 을 키우며 본 봉우리 (계산해 둔 것 -- 본문 표가 쓴다)
def _감쇠쓸기():
    난것 = []
    for esr in (0.005, 0.01, 0.03, 0.1, 0.3):
        g = [PDN[0], (esr, 1e-9, 1e-6, 20), PDN[2], PDN[3]]
        pk = _봉우리(g)
        가장 = max(pk, key=lambda t: t[1])
        난것.append((esr, 가장[0], 가장[1]))
    return 난것


def ch_pi():
    목표 = _목표()
    봉 = _봉우리()
    감쇠 = _감쇠쓸기()
    최적감쇠 = min(감쇠, key=lambda t: t[2])
    c = 장(
        "T13", "Power Integrity — the Network Everything Else Sits On",
        "The supply is not a node; it is an impedance with a frequency response, and "
        "your IP's worst jitter usually comes from its peak.",
        쓰는것=["전압", "전류", "저항", "주파수", "로그", "특성임피던스",
              "RC지연", "엘모어지연", "위상잡음", "전원푸싱",
              "전원제거비", "구경지터"],
        내놓는것=["목표임피던스", "PDN", "ESR", "ESL", "반공진", "감쇠",
                "디캡", "전류미분", "전압강하", "동시스위칭잡음", "리플버짓"],
        특허="""Power delivery is a board and package discipline, but the IP-side claims
        are real and they all have the same shape: <b>make the block insensitive
        instead of making the supply clean.</b> Regulators local to a sensitive block,
        differential and supply-referenced signalling, bias schemes whose output does
        not track V<sub>DD</sub>, and clock distribution that is immune to supply
        modulation. Every one of them is cheaper than lowering a PDN's impedance by the
        same factor.""")

    c.글("""Every block in this book assumed a supply. This chapter is about what that
    supply actually is: a network of capacitors and inductances whose impedance varies
    by two orders of magnitude across frequency, with <b>peaks at frequencies nobody
    designed</b>. The current your IP draws flows through that impedance and becomes a
    voltage on your own supply — and the failures it causes appear as jitter (T7),
    reference drift (T11), or timing failures that correlate with software.""")

    # ------------------------------------------------------------------
    c.절("T13.1 The specification is an impedance, not a voltage")

    c.날것(개념(
        "목표 임피던스 (target impedance)",
        f"""<p>Z<sub>target</sub> = V<sub>DD</sub>·(allowed ripple)/I<sub>max</sub>.
        For {수(VDD,2,'V')}, {수(리플*100,2,'%')} ripple and {수(I최대,3,'A')} of
        transient current that is <b>{수(목표*1e3,3,'mΩ')}</b> — and it must hold
        <i>at every frequency the load actually contains</i>, not on average.</p>
        <p>This turns a vague requirement ('clean supply') into a curve that can be
        measured, simulated and signed off, which is the whole reason the concept
        exists.</p>""",
        어디에="Board design, package design, and the on-die grid — and it is the "
             "number your IP's integration guide should state as a requirement.",
        언제="Before the package is chosen. The package's inductance sets the "
            "mid-frequency impedance and cannot be fixed later by board capacitors.",
        어떻게="Take the block's maximum transient current and its spectral content, "
             "set the allowed ripple from the most sensitive circuit (usually a PLL or "
             "a reference, not the logic), and check the impedance curve against it "
             "<b>at the peaks</b>.",
        산업코드="""# What an IP deliverable should say, so the integrator can meet it.
# INTEGRATION.md:
#   Supply: 1.0 V +/- 5%, Z_pdn <= 5 mOhm from DC to 200 MHz at the block's pins.
#   Peak transient: 10 A over 2 ns at the start of a burst (di/dt = 5 A/ns).
#   On-die decoupling included in the macro: 20 nF.
#   The PLL supply (VDDA) requires a separate regulator; sharing it with the
#   digital rail has been measured to add 0.4 ps rms jitter at 1 GHz.
# Without these four lines the integrator guesses, and the guess is usually wrong
# in the direction that makes your IP look bad.""",
        주의="""A flat target is a simplification. The real requirement is the load's
            current spectrum times the impedance, integrated where the victim circuit is
            sensitive — a 20 mΩ peak at 1.4 MHz matters enormously to a PLL whose loop
            bandwidth is 1 MHz (T7) and not at all to a logic block."""))

    c.날것(표("Measured impedance of this chapter's PDN "
             f"(target {수(목표*1e3,3,'mΩ')})",
        ["Frequency", "|Z|", "Meets target?"],
        [[수(f/1e6, 4, "MHz"), 수(_Z(f)*1e3, 4, "mΩ"),
          ("yes" if _Z(f) <= 목표 else "<b>no</b>")]
         for f in (1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 5e9)]))

    c.날것(그림(sch.곡선(
        [("|Z| (mΩ)", [(math.log10(f), z * 1e3) for f, z in _프로필(배율=1.35)],
          "#c0392b"),
         ("target", [(math.log10(f), 목표 * 1e3) for f in (1e3, 1e10)], "#1f6feb")],
        가로="log10(f / Hz)", 세로="|Z| (mΩ)",
        표시=[(math.log10(봉[0][0]), 봉[0][1] * 1e3,
             f"{수(봉[0][0]/1e6,3,'MHz')}")],
        가로눈금=[3, 5, 7, 9]),
        f"""The impedance profile. It meets the target over most of the range and
        <b>violates it at the anti-resonance</b> — {수(봉[0][1]*1e3,4,'mΩ')} at
        {수(봉[0][0]/1e6,3,'MHz')}, {수(봉[0][1]/목표,3)}× the target. The peak, not
        the average, is the specification."""))

    # ------------------------------------------------------------------
    c.절("T13.2 Anti-resonance: why adding a capacitor can make it worse")

    c.날것(유도("Where the peak comes from", [
        ("A real capacitor is series R–L–C: capacitive below its self-resonance, "
         "<b>inductive above it</b>.",
         "ESL comes from the package and the mounting; it is why a 100 µF bulk "
         "capacitor does nothing at 100 MHz."),
        ("Put two capacitors in parallel. Between their self-resonances, one is "
         "already inductive and the other is still capacitive.",
         "An inductor in parallel with a capacitor is a <b>parallel resonant tank</b>, "
         "and a parallel tank has <i>high</i> impedance at resonance."),
        ("So the combination has a peak where the individual parts each had a dip.",
         f"Measured on this PDN: peaks at {수(봉[0][0]/1e6,3,'MHz')} "
         f"({수(봉[0][1]*1e3,4,'mΩ')}) and "
         f"{수(봉[1][0]/1e6,3,'MHz') if len(봉)>1 else '—'} "
         f"({수(봉[1][1]*1e3,4,'mΩ') if len(봉)>1 else '—'})."),
        ("The peak's height is set by the <b>damping</b> — the ESR in the loop.",
         "Which produces the result below, and it is the one that surprises people."),
    ]))

    c.날것(표("Increasing ESR to lower the peak (the ceramic branch)",
        ["Ceramic ESR", "Peak frequency", "Peak |Z|", ""],
        [[수(e*1e3, 4, "mΩ"), 수(f/1e6, 3, "MHz"), 수(z*1e3, 4, "mΩ"),
          ("<b>minimum</b>" if abs(e - 최적감쇠[0]) < 1e-12 else "")]
         for e, f, z in 감쇠]))

    c.날것(짚기(f"""Read that table twice. Going from {수(감쇠[0][0]*1e3,3,'mΩ')} to
    {수(최적감쇠[0]*1e3,4,'mΩ')} of ESR — making each capacitor <b>worse</b> by the
    usual figure of merit — lowers the anti-resonance peak from
    {수(감쇠[0][2]*1e3,4,'mΩ')} to {수(최적감쇠[2]*1e3,4,'mΩ')}, a factor of
    {수(감쇠[0][2]/최적감쇠[2],3)}. Past the optimum it rises again, because the branch
    stops conducting at all. <b>'Lowest ESR' is not the specification; the right ESR
    is.</b> This is why controlled-ESR capacitors exist and why a well-meaning
    substitution to a 'better' part can break a board that was working."""))

    # ------------------------------------------------------------------
    c.절("T13.3 The three droops, and which one is yours")

    c.날것(표("A current step produces three separate droops",
        ["Droop", "Time scale", "Set by", "Fixed by"],
        [["First", "sub-ns to a few ns", "On-die grid resistance and on-die decap",
          "More on-die decap, a denser grid — <b>inside the die, nothing else helps</b>"],
         ["Second", "tens of ns", "Package inductance against package and on-die "
          "capacitance", "Package choice, more package capacitance, more bumps"],
         ["Third", "µs", "Board capacitance and the regulator's loop bandwidth",
          "Bulk capacitance, regulator response"]]))

    c.날것(개념(
        "di/dt, and why the derivative is the enemy",
        """<p>The resistive drop I·R is easy to compute and rarely the problem. The
        inductive drop is L·di/dt, and di/dt in a modern digital block is enormous: a
        clock-gated domain waking up can move amperes in nanoseconds.</p>
        <p>Worse, di/dt is <b>periodic and correlated with the workload</b>. A processor
        running a loop that alternates between a heavy and a light instruction produces
        a current square wave at whatever rate the loop runs — which can land exactly on
        an anti-resonance. The classic symptom: a machine that fails one specific
        benchmark and passes everything else.</p>""",
        어디에="Any design with clock gating, power gating, or a bursty accelerator — "
             "which is every SoC.",
        언제="At architecture time. Staggering the wake-up of a wide datapath is a "
            "micro-architectural decision, not a physical one.",
        어떻게="Stagger enables over several cycles, ramp clock-gate release, and "
             "<b>never</b> release a whole power domain on one edge. On the analysis "
             "side, drive the PDN model with the real current profile, not a step.",
        산업코드="""// The cheapest di/dt fix in RTL: stagger the ungating.
// Releasing 64 lanes on one edge is a current step; releasing them over 8 cycles
// is the same charge with 1/8 the di/dt, and usually nobody notices the latency.
always_ff @(posedge clk) begin
    if (wake) stagger <= {stagger[6:0], 1'b1};     // 8-deep shift
    else      stagger <= '0;
end
generate for (genvar i = 0; i < 64; i++)
    assign lane_en[i] = stagger[i/8];
endgenerate
// Measured effect belongs in the integration guide: peak di/dt with and without.""",
        주의="""Simulating the PDN with a current <b>step</b> gives the worst case and
            is useful, but it hides resonance: a step contains all frequencies at
            declining amplitude, while the real failure is a periodic load that
            concentrates energy at one frequency. Drive the model with the real
            workload's current spectrum as well."""))

    c.날것(사고("""Supply noise reaches your IP through two doors, and only one of them
    is the supply. The first is direct: V<sub>DD</sub> moves, and a VCO's frequency
    moves with it (T7's pushing). The second is the <b>substrate</b>: current returning
    through the die's bulk modulates body voltages, which modulates thresholds (T1's
    body effect). The second path does not appear in any PDN impedance plot, and it is
    why physical separation and guard rings matter even when the supply is separately
    regulated."""))

    # ------------------------------------------------------------------
    c.절("T13.4 What to do with this on Monday")

    c.날것(쓰는자리([
        ["목표임피던스", "The integration guide you ship",
         "The requirement the integrator must meet — state it or inherit their guess"],
        ["반공진 · 감쇠", "Board and package capacitor selection",
         "Which capacitors, and that 'lowest ESR' is the wrong criterion"],
        ["전류미분", "RTL and micro-architecture",
         "Whether wake-up is staggered — a free fix at design time, expensive later"],
        ["디캡", "Floorplan",
         "How much on-die capacitance fits, and the leakage it costs"],
        ["동시스위칭잡음", "I/O design",
         "How many simultaneous outputs are allowed to switch"]]))

    c.글(f"""The computed results to carry: this PDN meets its
    {수(목표*1e3,3,'mΩ')} target at most frequencies and misses it by
    {수(봉[0][1]/목표,3)}× at a {수(봉[0][0]/1e6,3,'MHz')} anti-resonance that no
    component has by itself. And raising the ceramic branch's ESR from
    {수(감쇠[0][0]*1e3,3,'mΩ')} to {수(최적감쇠[0]*1e3,4,'mΩ')} <b>lowers</b> that peak
    by {수(감쇠[0][2]/최적감쇠[2],3)}× — the one place in this book where making a
    component worse makes the system better.""")

    c.글("""The next chapter takes the longest time scale of all: what happens to these
    circuits after they have been running for ten years.""")

    return c.완성()
