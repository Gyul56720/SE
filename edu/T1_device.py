# -*- coding: utf-8 -*-
"""T1 -- The MOSFET as four different machines."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

# --- 이 장에서 쓰는 수는 전부 여기서 계산한다 ---------------------------
# 대표적인 저전력 28 nm 공정의 공개된 어림값.  정확한 수는 파운드리
# 문서에만 있으므로, 여기서는 **자릿수와 관계**를 보이는 데 쓴다.
VDD   = 0.9          # V
VT    = 0.35         # V, 표준 Vt 소자
SS    = 85e-3        # V/decade, 아문턱 기울기
I0    = 100e-9       # A/um, Vgs=Vt 에서의 전류
COX   = 1.6e-2       # F/m^2
MU    = 300e-4       # m^2/Vs
TOX   = 1.2e-9       # m


def _leak(vgs, vt=VT, ss=SS, i0=I0):
    """아문턱 누설 -- Vgs 가 Vt 보다 낮을 때 전류는 10^((Vgs-Vt)/SS) 로 준다."""
    return i0 * 10 ** ((vgs - vt) / ss)


def _ron(vgs, w_over_l, vt=VT, mu=MU, cox=COX):
    """선형 영역의 온저항.  Vds -> 0 극한."""
    return 1.0 / (mu * cox * w_over_l * (vgs - vt))


def ch_device():
    c = 장(
        "T1", "The MOSFET as Four Different Machines",
        "One device, four operating regions — and you design a different circuit in each.",
        쓰는것=["전압", "전류", "저항", "전기장", "전하", "전자", "지수함수",
              "로그", "미분", "옴의법칙"],
        내놓는것=["문턱전압", "차단영역", "선형영역", "포화영역", "아문턱영역",
                "온저항", "아문턱기울기", "누설전류", "트랜스컨덕턴스",
                "채널길이변조", "출력저항", "바디효과", "게이트용량"],
        특허="""Device-level invention is largely closed to a fabless IP house — the
        foundry owns the device. <b>What is open is how you choose among the devices
        you are given.</b> Claims in shipping IP portfolios routinely read on
        <i>selection and arrangement</i>: a retention latch that uses high-V<sub>t</sub>
        devices only on the state-holding node while the read path stays standard-V<sub>t</sub>;
        a level shifter whose pull-up stack is sized so that the contention current is
        bounded across corners; a sampling switch whose bootstrap network holds
        V<sub>GS</sub> constant so that R<sub>on</sub> is signal-independent. All three are
        device-region arguments, and all three are patentable as circuits. Read this
        chapter asking <i>which region am I in, and what does that buy me</i> — that
        question is where the claims come from.""")

    c.글("""A MOSFET is usually introduced as a switch, and for a first digital course
    that is enough. It is not enough to design production IP. The same four-terminal
    device behaves as four qualitatively different machines depending on the voltages you
    put on it, and a working designer moves between all four — often inside one block.
    A sampling front end uses the device as a <i>resistor</i>; the comparator behind it
    uses the device as an <i>amplifier</i>; the digital logic behind that uses it as a
    <i>switch</i>; and the leakage that drains the battery while all of it sits idle is
    the device acting as a <i>very bad switch</i> in the region nobody designed for.""")

    c.글("""This chapter establishes the four regions, then — for each — states where you
    use it, when you reach for it, how you apply it, and what the code that ships with a
    real IP deliverable looks like. Nothing here is included unless it is used later in
    this book.""")

    # ------------------------------------------------------------------
    c.절("T1.1 What the gate actually does")

    c.글("""Before the regions, one physical fact, because every later equation rests on
    it. The gate is one plate of a capacitor. The channel — the thin sheet of silicon
    under the oxide — is the other. Between them sits an insulator a few atoms thick.""")

    c.날것(정의("Gate oxide capacitance per unit area, C<sub>ox</sub>",
        f"""ε<sub>ox</sub>/t<sub>ox</sub>. With a physical oxide thickness of
        {수(TOX*1e9, 2, 'nm')} and ε<sub>ox</sub> ≈ 3.9 ε<sub>0</sub>, this is about
        {수(COX*1e3, 3, 'mF/m²')} — roughly {수(COX*1e-12*1e18/1e-15, 3)} fF per square
        micrometre. Everything the transistor does is proportional to it."""))

    c.날것(유도("Why gate voltage controls current at all", [
        ("Put a positive voltage on the gate of an NMOS. The gate is one plate of a "
         "capacitor, so it stores charge Q = C<sub>ox</sub>·V per unit area.",
         "That is the definition of capacitance. No transistor physics yet."),
        ("The opposite charge must appear on the other plate — in the silicon, directly "
         "under the oxide.",
         "A capacitor holds equal and opposite charge on its plates."),
        ("In p-type silicon the mobile negative charge is electrons, which are scarce. "
         "Below some gate voltage the silicon supplies the required charge by pushing "
         "<i>holes</i> away instead, leaving fixed negative acceptor ions.",
         "Depleting the majority carriers is cheaper than creating minority carriers."),
        ("Above some gate voltage the depletion stops growing and the silicon starts "
         "supplying <b>mobile electrons</b> instead. That sheet of electrons is the "
         "channel.",
         "Once the surface is pulled far enough, attracting electrons costs less energy "
         "than widening the depletion region."),
        ("<b>That crossover gate voltage is the threshold voltage V<sub>t</sub>.</b>",
         "It is not a switch trip point designed into the device; it is the voltage at "
         "which the silicon changes which kind of charge it supplies."),
        ("Above V<sub>t</sub>, the mobile charge in the channel is "
         "Q<sub>ch</sub> = C<sub>ox</sub>(V<sub>GS</sub> − V<sub>t</sub>) per unit area.",
         "The first V<sub>t</sub> worth of gate voltage went into depletion; only the "
         "excess produces mobile charge."),
        ("Current is charge times velocity, and velocity is mobility times field: "
         "I = W·Q<sub>ch</sub>·μ·E.",
         "Drift current, the same relation that gives Ohm's law in a resistor."),
    ]))

    c.글("""That last line is the whole device. Every equation below is this relation with
    a different assumption about how the field E varies along the channel. The quantity
    <b>V<sub>GS</sub> − V<sub>t</sub></b> appears so often it has a name: the
    <b>overdrive</b>, written V<sub>ov</sub>. When a designer says &ldquo;I ran that
    device at 150 millivolts of overdrive&rdquo;, this is the number.""")

    c.날것(짚기("""<b>V<sub>t</sub> is not one number.</b> It moves with temperature
    (roughly −1 mV/°C), with body bias, with channel length, with how close the
    neighbouring polysilicon is, and it differs from die to die and from transistor to
    transistor on the same die. A design that works only for the nominal V<sub>t</sub>
    does not work. Chapter T12 makes this quantitative; for now, treat every
    V<sub>t</sub> in this chapter as the centre of a distribution."""))

    # ------------------------------------------------------------------
    c.절("T1.2 Region 1 — cutoff: the switch that does not quite switch off")

    c.날것(개념(
        "Cutoff and subthreshold leakage",
        f"""<p>Below threshold the channel is not empty — it is exponentially sparse. The
        current does not stop; it falls by a factor of ten for every
        <b>{수(SS*1e3, 3, 'mV')}</b> that V<sub>GS</sub> drops below V<sub>t</sub>. That
        slope is the <b>subthreshold swing</b>, S, and it is the single most important
        number in a low-power design.</p>

        <p>I<sub>leak</sub> = I<sub>0</sub> · 10<sup>(V<sub>GS</sub> − V<sub>t</sub>)/S</sup></p>

        <p>S has a floor. The channel charge responds to the surface potential through a
        Boltzmann factor, so S ≥ (kT/q)·ln10 = <b>{수(1.380649e-23*300/1.602176634e-19*math.log(10)*1e3, 3, 'mV/decade')}</b>
        at room temperature, and real devices land 20–40 % above that because part of the
        gate voltage is lost to the depletion capacitance. <b>This floor is why leakage
        became the dominant power term as supplies scaled</b>: you cannot lower
        V<sub>t</sub> to keep speed without paying exponentially in leakage, and you
        cannot make the exponent steeper.</p>""",
        어디에="""Standby power of every block you ship. Retention registers. Memory
        arrays (where leakage is multiplied by millions of cells). Power gating and the
        sizing of the header/footer switch. Any IP sold with a quoted standby current —
        which is most of them.""",
        언제="""Whenever you write a leakage number into a datasheet; whenever you choose
        between device flavours in synthesis; whenever a customer asks for a retention
        mode. Also whenever a block is mostly idle — an equaliser that runs for 3 % of the
        time is a leakage problem, not a dynamic-power problem.""",
        어떻게="""Get I<sub>off</sub> per micrometre of width from the foundry's
        characterisation at the worst corner (highest temperature, lowest V<sub>t</sub>,
        highest supply — leakage worsens in the opposite direction from speed). Multiply
        by the total width in the block. Multiply again by the temperature factor — a rule
        of thumb is 2× per 10 °C, which follows directly from the S equation because S
        itself is proportional to T. Then decide: if the answer exceeds budget, move the
        non-critical paths to high-V<sub>t</sub> cells and re-time.""",
        산업코드="""// Liberty (.lib) — what the foundry actually ships you.
// This is the leakage the synthesiser reads. Note that it is
// state-dependent: a NAND2 leaks differently per input pattern,
// because the stacked device changes the internal node voltage.

cell (NAND2_X1) {
    area : 1.596 ;
    cell_leakage_power : 4.2851e+03 ;        // nW, the default
    leakage_power () {
        when            : "!A1 & !A2" ;
        value           : 1.8032e+03 ;       // both off: stack effect helps
    }
    leakage_power () {
        when            : "A1 & !A2" ;
        value           : 4.9210e+03 ;
    }
    leakage_power () {
        when            : "A1 & A2" ;
        value           : 6.1104e+03 ;       // both on: worst
    }
    ...
}

# Synthesis — trade leakage against timing by device flavour.
# The tool will use LVT only where it must to close timing.
set_db library  [list  sc9_base_svt.lib  sc9_base_hvt.lib  sc9_base_lvt.lib ]
set_db leakage_power_effort         high
set_db dynamic_power_effort         medium
# Forbid the leaky flavour outside the critical paths:
set_dont_use  [get_lib_cells */*_LVT*]
# ... place and route, then selectively re-enable on failing paths:
set_dont_use -false [get_lib_cells */BUF_X*_LVT]""",
        주의="""Quoting leakage at nominal temperature. Leakage roughly doubles per
        10 °C, so a 25 °C number is <b>8–16× optimistic</b> against a 125 °C automotive
        corner. A datasheet that says &ldquo;standby 12 µA&rdquo; without naming the
        temperature, supply and corner is not a specification — and a customer who
        discovers the real number at their thermal limit will not buy from you again."""))

    c.날것(예제(
        "Leakage of a block, done the way a datasheet requires",
        주어진=f"""A block with 40,000 gates, average device width 0.8 µm per gate
        (both n and p), I<sub>off</sub> = {수(_leak(0)*1e9, 3, 'nA/µm')} at V<sub>GS</sub> = 0,
        25 °C, typical corner. The customer runs it at 105 °C and asks for the
        worst-case standby current.""",
        푸는법="""Total width, times I<sub>off</sub> per micrometre, times the
        temperature factor (2× per 10 °C), times the corner factor for fast-fast silicon
        (typically 2–3× on leakage).""",
        답=f"""Width = 40,000 × 0.8 = 32,000 µm. At 25 °C, typical:
        32,000 × {수(_leak(0)*1e9, 3)} nA = <b>{수(32000*_leak(0)*1e6, 3, 'µA')}</b>.
        Temperature: 105 − 25 = 80 °C, so 2<sup>8</sup> = 256×.
        Corner: ×2.5. Total ≈ <b>{수(32000*_leak(0)*1e6*256*2.5/1000, 3, 'mA')}</b>.""",
        함정="""The 25 °C typical number and the 105 °C fast number differ by
        <b>640×</b> here. Engineers quote the first because it is the one the tool prints
        by default. The second is the one the customer measures. Always state the
        triple — temperature, supply, process corner — next to the number; a leakage
        figure without it is meaningless.""",
        덧="""The factor-of-2-per-10 °C rule is an approximation of the exponential; for
        a real deliverable you read the number off the foundry's corner tables rather than
        extrapolating. The point of the estimate is to know, early, whether you are within
        a factor of two of the budget or a factor of fifty."""))

    # ------------------------------------------------------------------
    c.절("T1.3 Region 2 — triode: the transistor as a resistor")

    c.날것(개념(
        "Triode (linear) region and on-resistance",
        """<p>Turn the gate well above V<sub>t</sub> and hold the drain close to the
        source. Now the channel exists along its whole length and the field along it is
        nearly uniform, so the device behaves like a resistor whose value the gate
        controls:</p>

        <p>I<sub>D</sub> = μC<sub>ox</sub>(W/L)[(V<sub>GS</sub> − V<sub>t</sub>)V<sub>DS</sub>
        − V<sub>DS</sub>²/2]</p>

        <p>For small V<sub>DS</sub> the square term vanishes and the device is simply</p>

        <p>R<sub>on</sub> = 1 / [μC<sub>ox</sub>(W/L)(V<sub>GS</sub> − V<sub>t</sub>)]</p>

        <p><b>Read that denominator.</b> R<sub>on</sub> is inversely proportional to
        overdrive. If the signal you are passing moves V<sub>S</sub>, then V<sub>GS</sub>
        moves with it, and <b>the resistance changes with the signal</b>. A
        signal-dependent resistance in a sampling path is distortion, and it is the
        reason bootstrapped switches exist.</p>""",
        어디에="""Every transmission gate and pass gate. The sampling switch at the
        front of every ADC and every track-and-hold. Power-gating headers and footers.
        The programmable resistors in a CTLE. Write drivers in SRAM. Any place a digital
        signal must be routed rather than regenerated.""",
        언제="""When you need to <i>connect</i> two nodes rather than <i>drive</i> one.
        The moment you catch yourself writing &ldquo;pass the signal through&rdquo; rather
        than &ldquo;buffer the signal&rdquo;, you are in triode and R<sub>on</sub>
        matters.""",
        어떻게=f"""Budget the settling first, then size from it. A switch with
        resistance R charging capacitance C settles with time constant τ = RC; to settle
        to N bits you need t<sub>settle</sub> ≥ RC·ln(2<sup>N+1</sup>). Invert for R, then
        use R<sub>on</sub> = 1/[μC<sub>ox</sub>(W/L)V<sub>ov</sub>] to get W/L. Then
        <b>check R<sub>on</sub> at the worst signal level</b>, not at mid-scale: for an
        NMOS passing a rising signal, V<sub>GS</sub> shrinks as the signal rises and
        R<sub>on</sub> blows up near V<sub>DD</sub> − V<sub>t</sub>.""",
        산업코드="""* SPICE — the measurement you actually run on a sampling switch.
* You are not checking that it works; you are checking how Ron varies
* with the signal, because that variation is the distortion.

.param vin_val=0.45
M1  drain gate source bulk nch  W=2u  L=30n
Vg  gate  0  DC 0.9
Vs  source 0 DC 'vin_val'
Vd  drain  0 DC 'vin_val+1m'      $ 1 mV across the switch: stay in triode
.dc vin_val 0 0.9 0.01
.measure dc ron  PARAM='1m/I(Vd)'  $ R = V/I at each input level
.alter
.param boot=1                      $ repeat with a bootstrapped gate
.end

// Verilog-AMS behavioural model used in mixed-signal top-level sims.
// A digital verification engineer meets this, not the SPICE deck.
module sw_nmos (inout d, inout s, input g);
    parameter real ron_nom = 250.0;     // ohms at mid-scale
    parameter real roff    = 1e12;
    analog begin
        // Ron rises as (Vgs - Vt) falls: this is the term that matters.
        real vgs, ron;
        vgs = V(g) - V(s);
        ron = (vgs > 0.35) ? ron_nom * 0.55 / (vgs - 0.35) : roff;
        I(d,s) <+ V(d,s) / ron;
    end
endmodule""",
        주의="""Sizing the switch at mid-scale and declaring it done. R<sub>on</sub> at
        the top of the input range can be several times its mid-scale value, and the
        settling error it causes is <i>signal-dependent</i> — which means it is harmonic
        distortion, not noise, and averaging will not remove it. Sweep R<sub>on</sub>
        across the full input range and size for the worst point."""))

    c.날것(예제(
        "Sizing a sampling switch from the settling requirement",
        주어진=f"""A 10-bit converter samples onto C = 1 pF in 2 ns. Supply
        {수(VDD, 2, 'V')}, V<sub>t</sub> = {수(VT, 2, 'V')}, and the worst-case input is
        0.5 V, so V<sub>ov</sub> = 0.9 − 0.5 − 0.35 = {수(VDD-0.5-VT, 2, 'V')}.""",
        푸는법="""Settling to 10 bits needs the error below ½ LSB, i.e.
        e<sup>−t/τ</sup> &lt; 2<sup>−11</sup>, so t/τ &gt; 11·ln2 = 7.62. Use a 2× margin
        on τ for the rest of the path, then solve R from τ = RC, then W/L from
        R<sub>on</sub>.""",
        답=f"""τ ≤ 2 ns / 7.62 = {수(2e-9/7.62*1e12, 3, 'ps')}. With 2× margin,
        τ = {수(2e-9/7.62/2*1e12, 3, 'ps')}. R = τ/C = {수(2e-9/7.62/2/1e-12, 3, 'Ω')}.
        Then W/L = 1/(μC<sub>ox</sub>·R·V<sub>ov</sub>) =
        <b>{수(1/(MU*COX*(2e-9/7.62/2/1e-12)*(VDD-0.5-VT)), 3)}</b>.""",
        함정=f"""Using V<sub>ov</sub> at the <i>mid-scale</i> input (0.45 V) instead of
        the worst-case input gives V<sub>ov</sub> = {수(VDD-0.45-VT, 2, 'V')} and a W/L
        about {수((VDD-0.45-VT)/(VDD-0.5-VT), 3)}× smaller — and then the switch misses
        its settling target exactly where the signal is largest, which is where the
        distortion is most visible. <b>Size switches at the worst signal level, not the
        average one.</b>"""))

    # ------------------------------------------------------------------
    c.절("T1.4 Region 3 — saturation: the transistor as a current source")

    c.날것(개념(
        "Saturation, transconductance, and output resistance",
        """<p>Raise V<sub>DS</sub> above the overdrive and the channel <i>pinches off</i>
        near the drain: the local V<sub>GS</sub> there falls to V<sub>t</sub> and no more
        mobile charge exists. Beyond that point, raising the drain voltage no longer
        raises the current much. The device has become a current source controlled by the
        gate:</p>

        <p>I<sub>D</sub> = ½ μC<sub>ox</sub>(W/L)(V<sub>GS</sub> − V<sub>t</sub>)²
        · (1 + λV<sub>DS</sub>)</p>

        <p>Two derived quantities do all the work in analog design:</p>

        <p><b>Transconductance</b> g<sub>m</sub> = ∂I<sub>D</sub>/∂V<sub>GS</sub>
        = 2I<sub>D</sub>/V<sub>ov</sub>. How much current you get per volt of input —
        i.e. the gain-producing term.</p>

        <p><b>Output resistance</b> r<sub>o</sub> = ∂V<sub>DS</sub>/∂I<sub>D</sub>
        ≈ 1/(λI<sub>D</sub>). How close to an ideal current source it is. The term λ
        exists because pinch-off moves with drain voltage — <b>channel-length
        modulation</b> — and it is worse for short channels, which is why analog blocks
        use devices several times the minimum length.</p>

        <p>Their product g<sub>m</sub>r<sub>o</sub> = 2/(λV<sub>ov</sub>) is the intrinsic
        gain: <b>the most voltage gain one transistor can give you.</b> It falls as
        processes scale, which is why modern analog design leans on digital assistance
        rather than on raw gain.</p>""",
        어디에="""Comparators and sense amplifiers — the pre-amp stage. Every current
        mirror and bias network. CTLE and the analogue front end of a SerDes. Level
        shifters during the transition. Ring-oscillator delay cells in a PLL. Anywhere the
        circuit must <i>amplify</i> rather than <i>switch</i>.""",
        언제="""When the question is &ldquo;how much gain&rdquo; or &ldquo;how much
        current, independent of the load&rdquo;. Also, unexpectedly, in <i>digital</i>
        analysis: during a logic transition both devices pass through saturation, and the
        short-circuit current that flows then is the term T4 uses to explain why slow
        input edges cost power.""",
        어떻게="""Design with g<sub>m</sub>/I<sub>D</sub> rather than with W/L. Pick the
        g<sub>m</sub> you need from the gain or the noise requirement; pick
        g<sub>m</sub>/I<sub>D</sub> from the speed/power trade (high g<sub>m</sub>/I<sub>D</sub>
        ≈ low overdrive ≈ efficient but slow; low g<sub>m</sub>/I<sub>D</sub> ≈ high
        overdrive ≈ fast but power-hungry); that fixes I<sub>D</sub>; read W/L off the
        foundry's characterised g<sub>m</sub>/I<sub>D</sub> curves. This works across
        processes and does not rely on the square-law equation, which stops being accurate
        below about 100 nm.""",
        산업코드="""* The gm/ID sweep every analog team runs once per process,
* then reuses for every block. You are not simulating a circuit here;
* you are characterising the device so design becomes look-up.

.param L_val=100n
M1  d g 0 0 nch  W=10u  L='L_val'
Vg  g 0 DC 0.5
Vd  d 0 DC 0.45          $ hold Vds at VDD/2, in saturation
.dc Vg 0.2 0.9 0.005
.measure dc gm_id  PARAM='deriv(I(Vd),V(g))/I(Vd)'
.measure dc ft     PARAM='deriv(I(Vd),V(g))/(2*3.14159*cgg)'
.step param L_val list 30n 60n 100n 200n 500n
.end

// What a digital designer sees of all this: a characterised cell.
// The analog block arrives as a .lib timing/power view plus a
// behavioural model. You must still know what is inside, because
// the constraints you write depend on it.
cell (CMP_STRONGARM) {
    pin (CLK)  { direction : input;  clock : true;  capacitance : 4.8; }
    pin (VINP) { direction : input;  capacitance : 12.1; }
    pin (OUTP) { direction : output;
                 timing () {
                     related_pin  : "CLK" ;
                     timing_type  : rising_edge ;
                     cell_rise (delay_template) { ... }
                 } }
    // The number a digital designer must not ignore:
    // the comparator has a metastability window like any bistable.
    // T3 derives it; the vendor states it here.
}""",
        주의="""Using the square-law equation for design in a modern process. Below
        roughly 100 nm the velocity of carriers saturates, the exponent drifts from 2
        toward 1, and the equation can be wrong by tens of percent. It remains excellent
        for <i>reasoning</i> — it tells you the right direction and the right
        sensitivity — and useless for <i>numbers</i>. Reason with the equation, size from
        the characterised curves."""))

    # ------------------------------------------------------------------
    c.절("T1.5 Region 4 — subthreshold as a design space, not only as leakage")

    c.날것(개념(
        "Subthreshold operation",
        f"""<p>The same exponential that produces leakage is a usable transfer
        characteristic. Biased below V<sub>t</sub>, the device gives
        g<sub>m</sub>/I<sub>D</sub> at its maximum — about
        <b>{수(1/(SS/math.log(10)), 3, 'V⁻¹')}</b>, set only by S — which is the best
        current efficiency any MOSFET can offer. The cost is speed: f<sub>T</sub> falls by
        orders of magnitude, and the exponential dependence on V<sub>t</sub> means that
        device-to-device V<sub>t</sub> mismatch turns into <i>current</i> mismatch of tens
        of percent.</p>

        <p>So subthreshold is the region you choose when energy per operation dominates
        and speed does not, and the region you are forced into when a supply droops. It is
        also the region a <b>retention</b> circuit lives in: state is held by a device
        that is barely on.</p>""",
        어디에="""Always-on domains — wake-up logic, watchdog timers, retention
        registers. Sensor front ends. Bias generators that must survive at very low
        current. And, negatively, every leakage path in every block you ship.""",
        언제="""When the duty cycle is very low and the energy budget is per-operation
        rather than per-second. When a customer asks for a retention mode with a quoted
        microamp figure. When you are asked to survive a supply that collapses toward
        V<sub>t</sub>.""",
        어떻게="""Accept that matching, not speed, will set your area. In strong
        inversion, current mismatch tracks V<sub>t</sub> mismatch through
        g<sub>m</sub>/I<sub>D</sub>; in subthreshold g<sub>m</sub>/I<sub>D</sub> is at its
        maximum, so the <i>same</i> V<sub>t</sub> mismatch produces the <i>largest</i>
        current mismatch. Size the devices from the matching requirement (T12's Pelgrom
        relation), then check speed, rather than the other way round.""",
        산업코드="""# UPF (Unified Power Format) — how the always-on domain is
# declared to the tools. A digital IP deliverable that supports
# retention ships this file, and it is as much a part of the
# product as the RTL.

create_power_domain PD_ALWAYS_ON -elements {u_wake u_timer}
create_power_domain PD_CORE      -elements {u_dsp u_eq}   -scope .

create_supply_net  VDD_AON  -domain PD_ALWAYS_ON
create_supply_net  VDD_CORE -domain PD_CORE
set_domain_supply_net PD_CORE -primary_power_net VDD_CORE \\
                              -primary_ground_net VSS

# Retention: state survives while VDD_CORE collapses.
set_retention  RET_CORE -domain PD_CORE \\
    -retention_power_net VDD_AON -retention_ground_net VSS \\
    -save_signal  {u_dsp/ret_save  high} \\
    -restore_signal {u_dsp/ret_restore low}

# Isolation: outputs of a collapsed domain must not float into
# the always-on domain, or the always-on logic burns crowbar current.
set_isolation ISO_CORE -domain PD_CORE \\
    -isolation_power_net VDD_AON -clamp_value 0 \\
    -applies_to outputs
set_isolation_control ISO_CORE -domain PD_CORE \\
    -isolation_signal u_pmc/iso_en -isolation_sense high""",
        주의="""Forgetting isolation. When a power domain collapses, its outputs drift
        to an intermediate voltage. Feed that into an always-on gate and <b>both</b> its
        devices conduct — the always-on domain then draws milliamps instead of microamps,
        and the retention mode you sold does not exist. This is one of the most common
        integration failures in low-power IP, and it is invisible in RTL simulation
        because RTL has no intermediate voltage."""))

    # ------------------------------------------------------------------
    c.절("T1.6 Two second-order effects you cannot ignore")

    c.날것(개념(
        "Body effect",
        """<p>V<sub>t</sub> is quoted for source tied to bulk. Lift the source above the
        bulk and the depletion region under the channel widens, so more gate voltage is
        needed before inversion: V<sub>t</sub> rises. The dependence is
        V<sub>t</sub> = V<sub>t0</sub> + γ(√(2φ<sub>F</sub> + V<sub>SB</sub>)
        − √(2φ<sub>F</sub>)), and γ is a process constant of order 0.2–0.5 √V.</p>

        <p>The practical consequence: <b>a device whose source is not at the rail is
        weaker than the library says.</b></p>""",
        어디에="""Stacked devices in NAND/NOR — the upper NMOS has its source above
        ground. Pass-gate chains. Cascode current sources. Multiplexer trees built from
        transmission gates. Any place transistors are in series.""",
        언제="""Whenever you stack. A 4-input NAND is not simply 4× slower than an
        inverter — it is worse, because the upper devices are body-effected. This is one
        reason wide gates are decomposed into trees rather than built flat.""",
        어떻게="""For hand analysis, add the V<sub>t</sub> shift and recompute the
        overdrive of the upper device. For real sizing, let the characterised library
        handle it — the .lib delay tables already contain the effect — but <b>know it is
        there</b> so that a stacked structure you invent is not assumed to scale
        linearly. If the stack is deep, insert a buffer instead.""",
        산업코드="""// Why you will not find `body effect` in an RTL file, but will
// feel it: the synthesiser's cell choice reflects it.
// These two are logically identical and time very differently.

assign y = ~(a & b & c & d);          // maps to NAND4 — deep stack

wire ab = ~(a & b);                   // maps to NAND2 + NAND2 + NOR2
wire cd = ~(c & d);                   // shallower stacks, more cells
assign y = ~(~ab | ~cd) ? 1'b0 : 1'b1;

// Liberty shows the penalty directly. Compare the intrinsic delays:
//   NAND2_X1  cell_rise (A1) ~ 0.021 ns
//   NAND3_X1  cell_rise (A1) ~ 0.031 ns
//   NAND4_X1  cell_rise (A1) ~ 0.045 ns     <- worse than linear""",
        주의="""Assuming a stack of n devices is n times slower. Body effect and the
        internal node capacitances make it super-linear, and above three or four the
        penalty grows fast. If a synthesised netlist contains NAND4s on a critical path,
        that is usually the first thing to restructure."""))

    c.날것(개념(
        "Gate capacitance — the load you are driving",
        f"""<p>The gate you drive is a capacitor: C<sub>g</sub> ≈ C<sub>ox</sub>·W·L,
        plus overlap capacitance that does not scale with L. For
        {수(TOX*1e9,2,'nm')} oxide this is of order
        <b>{수(COX*1e-6*1e15, 3, 'fF/µm²')}</b> of gate area.</p>

        <p>This single fact ties the whole of digital design together: the output of one
        gate must charge the input capacitance of the next, so <b>delay is proportional to
        the ratio of load capacitance to drive strength</b>. That ratio is the
        <i>electrical effort</i> of T2, and it is why sizing is a chain problem rather
        than a per-gate problem.</p>

        <p>There is also a term that bites in analog and in high-speed digital: the
        gate-to-drain overlap capacitance C<sub>gd</sub> appears at the output
        <i>multiplied by the gain</i> of the stage (Miller effect). In a comparator
        pre-amp this can dominate the load; in a digital gate it is why the input
        capacitance seen during a transition is larger than the static value.</p>""",
        어디에="""Every delay calculation. Clock-tree power (the clock drives enormous
        total gate capacitance, which is why clock gating is the first power optimisation).
        Input capacitance you quote in a datasheet so a customer can budget their driver.""",
        언제="""Always, in digital. Specifically when you write the input capacitance
        line of an IP datasheet, and when you decide how many loads one cell may drive.""",
        어떻게="""Express loads in units of a minimum inverter's input capacitance and
        the arithmetic becomes tractable by hand — this is exactly what logical effort
        (T2) formalises. For the deliverable, state input capacitance per pin in the .lib
        and in the datasheet; integrators use it to size their drivers and to build the
        clock tree.""",
        산업코드="""// The datasheet line that comes from this, and the .lib it matches.
// If these two disagree, the customer's timing closure fails and
// they will find out before you do.

pin (D) {
    direction          : input ;
    capacitance        : 1.412 ;       // fF — what the integrator budgets
    rise_capacitance   : 1.455 ;
    fall_capacitance   : 1.369 ;
    max_transition     : 0.300 ;       // ns — beyond this, delay tables
}                                      //      are extrapolated, not valid

// SDC the customer writes against your block:
set_load       0.0014   [get_ports eq_out*]    ;# pF
set_driving_cell -lib_cell BUF_X4 [get_ports adc_data*]
set_max_transition 0.300 [current_design]""",
        주의="""Letting a net exceed <code>max_transition</code>. Beyond that point the
        library's delay tables are being extrapolated, and the timing report is no longer
        characterised data — it is a guess with a confident number next to it. Treat a
        max-transition violation as a hard error, not a warning."""))

    # ------------------------------------------------------------------
    c.절("T1.7 Which region, for which job")

    c.날것(표("The four regions as four design tools",
        ["Region", "Condition", "The device behaves as", "You use it for",
         "The number that matters"],
        [["Cutoff", "V<sub>GS</sub> &lt; V<sub>t</sub>", "a leaky open switch",
          "standby, retention, power gating",
          "I<sub>off</sub> and subthreshold swing S"],
         ["Triode", "V<sub>GS</sub> &gt; V<sub>t</sub>, V<sub>DS</sub> &lt; V<sub>ov</sub>",
          "a gate-controlled resistor",
          "pass gates, sampling switches, power switches",
          "R<sub>on</sub>, and how it varies with the signal"],
         ["Saturation", "V<sub>GS</sub> &gt; V<sub>t</sub>, V<sub>DS</sub> &gt; V<sub>ov</sub>",
          "a voltage-controlled current source",
          "amplifiers, comparators, current mirrors, CTLE",
          "g<sub>m</sub>, r<sub>o</sub>, g<sub>m</sub>/I<sub>D</sub>"],
         ["Subthreshold", "V<sub>GS</sub> slightly &lt; V<sub>t</sub>",
          "an exponential transconductor",
          "always-on blocks, ultra-low-power, retention",
          "S, and V<sub>t</sub> mismatch"]]))

    c.글("""A digital cell spends almost all of its time in the first two rows and passes
    briefly through the third on every transition. That brief passage is not a detail: it
    is the short-circuit current of T2 and the regeneration of T3, and two of the hardest
    problems in this book — metastability and comparator resolution — are entirely
    arguments about what happens while a device sits in saturation instead of settling
    into triode or cutoff.""")

    c.날것(사고("""A production sampling switch was sized from its mid-scale
    R<sub>on</sub> and met its settling target in simulation at every corner. Silicon
    showed second-harmonic distortion 12 dB worse than simulated. The cause was that the
    verification sweep held the input at mid-scale while checking settling, and swept the
    input only while checking gain — so the combination that mattered, <i>large input and
    tight settling</i>, was never simulated. Nothing in the design was wrong; the
    <b>verification grid</b> was wrong. T21 turns this into a rule: sweep the axes
    together, not one at a time."""))

    c.날것(쓰는자리([
        ["Subthreshold swing S", "every block's standby spec",
         "the leakage number in your datasheet, and whether retention is possible"],
        ["R<sub>on</sub> and its signal dependence", "sampling switch, pass gates, power switch",
         "settling time, distortion, IR drop across the power switch"],
        ["g<sub>m</sub>/I<sub>D</sub>", "comparator pre-amp, CTLE, bias",
         "gain and noise per unit of current — i.e. the power budget"],
        ["Channel-length modulation λ", "current mirrors, cascodes",
         "how much the bias current moves with output voltage"],
        ["Body effect γ", "stacked logic, transmission-gate trees",
         "why deep stacks are super-linearly slow"],
        ["Gate capacitance C<sub>g</sub>", "every delay and clock-power calculation",
         "the input capacitance line of your datasheet"],
    ]))

    return c.완성()
