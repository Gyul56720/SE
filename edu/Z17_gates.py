# -*- coding: utf-8 -*-
"""Volume III, Part Z17 -- From one transistor to our datapath."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, derive
import sch


def ch_gates():
    s = ['<h1 id="z17">Z17. From One Transistor to Our Datapath</h1>']

    s.append("""<p>This part builds the equaliser upward from a single transistor. Nothing
    is assumed. If you know that a computer is made of transistors and nothing more
    specific than that, start here; by the end you will be able to read the gate-level
    schematic of the adder inside the filter and say why it is shaped the way it is.</p>

    <p>The reason this matters to someone writing RTL or HLS is not nostalgia. Every
    decision the previous parts made &mdash; why saturation costs more than truncation,
    why a 9-bit adder is not an 8-bit adder, why the critical path runs where it does,
    why you register a signal before it leaves the chip &mdash; is a fact about these
    drawings. You can write RTL without them and you will write slower RTL.</p>""")

    s.append("<h2>Z17.1 The switch</h2>")
    s.append("""<p>A MOSFET is a voltage-controlled switch with three terminals that matter:
    <b>gate</b>, <b>source</b> and <b>drain</b>. Current flows between source and drain
    when the gate says so. There are two flavours and they are opposites:</p>""")

    s.append(tab("The two switches",
        ["Type", "Turns on when its gate is", "Good at passing", "Where it goes"],
        [["<b>NMOS</b>", "high (1)", "a strong 0", "between the output and <b>ground</b>"],
         ["<b>PMOS</b>", "low (0)", "a strong 1", "between the output and <b>VDD</b>"]]))

    s.append("""<p>The third column is the one people skip and then get wrong. An NMOS can
    pull a node down to 0&nbsp;V cleanly but cannot pull it all the way up to VDD &mdash;
    it stops roughly a threshold voltage short. A PMOS is the mirror image. So neither type
    alone can build a good logic gate, and <em>that</em> is why every static CMOS gate
    contains both: PMOS above to pull up, NMOS below to pull down. The circuit family is
    called <b>complementary</b> MOS for exactly this reason.</p>""")

    s.append("<h2>Z17.2 The inverter, and why CMOS won</h2>")
    s.append(fig(sch.씨모스인버터(), """The CMOS inverter: one PMOS pull-up, one NMOS
    pull-down, gates tied together. This is the smallest complete CMOS gate and the
    template for every other one. The red bar at the top is the supply (VDD); the striped
    symbol at the bottom is ground (0&nbsp;V)."""))

    s.append(derive("Why this circuit inverts, and why it costs no static power",
        [("Input A = 0. The PMOS gate sees 0, so the PMOS is <b>on</b>. The NMOS gate "
          "sees 0, so the NMOS is <b>off</b>.",
          "From the table above: PMOS turns on with a low gate, NMOS with a high gate."),
         ("With only the PMOS on, the output node is connected to VDD and disconnected "
          "from ground. Y is pulled up to 1.",
          "The only conducting path from Y goes to the supply."),
         ("Input A = 1. Now the PMOS is off and the NMOS is on, so Y is connected to "
          "ground and disconnected from VDD. Y is pulled down to 0.",
          "The mirror image of the previous step."),
         ("In both steady states exactly one of the two devices conducts, so there is "
          "<b>no path from VDD to ground</b>.",
          "A path from supply to ground would be a short circuit drawing continuous "
          "current."),
         ("Therefore a CMOS gate that is not switching draws (almost) no current.",
          "This is the property that let CMOS displace every earlier logic family. "
          "Power is consumed charging and discharging capacitance when the output "
          "<i>changes</i>, which is why dynamic power is proportional to activity and "
          "frequency."),
         ("The word &lsquo;almost&rsquo; is doing real work at modern nodes.",
          "Sub-threshold leakage and gate leakage mean an idle gate does draw a small "
          "current, and below roughly 28&nbsp;nm leakage becomes a first-order design "
          "problem. Part&nbsp;X43 covers what is done about it.")]))

    s.append("<h2>Z17.3 NAND: pull-up and pull-down are duals</h2>")
    s.append("""<p>Now the gate that everything is actually built from. The rule that
    generates every static CMOS gate is a single sentence: <b>build the pull-down network
    from NMOS so that it conducts exactly when the output should be 0, then build the
    pull-up network as its dual.</b></p>""")

    s.append(fig(sch.씨모스낸드(), """A 2-input CMOS NAND. The two NMOS are in
    <b>series</b>: current only reaches ground when A and B are both 1, which is exactly
    when NAND's output should be 0. The two PMOS are in <b>parallel</b>: a path to VDD
    exists when A is 0 <i>or</i> B is 0. Series means AND; parallel means OR."""))

    s.append(tab("Reading the NAND schematic as a truth table",
        ["A", "B", "Pull-down (series NMOS)", "Pull-up (parallel PMOS)", "Y"],
        [["0", "0", "both off &rarr; open", "both on &rarr; conducts", "<b>1</b>"],
         ["0", "1", "top off &rarr; open", "left on &rarr; conducts", "<b>1</b>"],
         ["1", "0", "bottom off &rarr; open", "right on &rarr; conducts", "<b>1</b>"],
         ["1", "1", "both on &rarr; <b>conducts</b>", "both off &rarr; open", "<b>0</b>"]]))

    s.append(derive("Why the pull-up is the dual of the pull-down, always",
        [("The output must be driven to exactly one value in every input combination.",
          "If neither network conducts the output floats (high-impedance, value "
          "undefined); if both conduct you have a short from VDD to ground."),
         ("So the pull-up must conduct exactly when the pull-down does not &mdash; the "
          "two conditions are logical complements.",
          "That is what &lsquo;exactly one&rsquo; means."),
         ("The pull-down for NAND conducts when (A AND B).",
          "Series transistors both have to be on, and NMOS is on for a 1."),
         ("Its complement is NOT(A AND B) = (NOT A) OR (NOT B), by De&nbsp;Morgan's law.",
          "De&nbsp;Morgan converts a negated conjunction into a disjunction of "
          "negations."),
         ("PMOS is on for a 0, so a PMOS whose gate is A implements (NOT A). An OR of "
          "two conditions is a <b>parallel</b> connection.",
          "Either path alone is enough to conduct."),
         ("Hence: series NMOS below, parallel PMOS above. Swap series and parallel and "
          "you get NOR instead.",
          "NOR's pull-down is parallel (output 0 when A OR B) and its pull-up is series.")]))

    s.append("""<p>Two consequences worth carrying into RTL. First, <b>NAND and NOR are
    the cheap gates</b> &mdash; four transistors each. AND and OR are <em>more</em>
    expensive, because CMOS naturally produces an inversion and a non-inverting gate is a
    NAND followed by an inverter: six transistors. This is why synthesis tools cheerfully
    rewrite your logic into seas of NANDs, and why the classic identity
    AND(a,b) = NOT(NAND(a,b)) is worth recognising in a netlist.</p>

    <p>Second, <b>series transistors are slow</b>. A 4-input NAND has four NMOS in series
    and its pull-down is roughly four times weaker than an inverter's. That is why wide
    gates get decomposed into trees, and why a 17-bit ripple adder is not simply
    &lsquo;a bit slower&rsquo; than an 8-bit one.</p>""")

    s.append("<h2>Z17.4 Pull-up resistors &mdash; a different thing with a similar name</h2>")
    s.append("""<p>The phrase &ldquo;pull-up&rdquo; is used for two different circuits and
    conflating them causes real design errors.</p>""")

    s.append(fig(sch.개방드레인과정적씨모스(),
        """Two things called &ldquo;pull-up&rdquo;. <b>Left:</b> a real resistor on a
        board, holding an open-drain line high until some device pulls it low. <b>Right:</b>
        a PMOS pull-up network inside a CMOS gate. Only the left one is a resistor; the
        right one is the transistor network of Z17.2."""))

    s.append(tab("Resistor pull-up versus transistor pull-up",
        ["", "Pull-up resistor (board level)", "PMOS pull-up (inside a gate)"],
        [["What it is", "A physical resistor, typically 1&ndash;10&nbsp;k&Omega;",
          "A transistor network, the dual of the pull-down"],
         ["Where", "On the PCB or inside an I/O pad", "Inside every static CMOS gate"],
         ["Why", "The line has <b>no</b> active driver for the high state &mdash; "
                 "open-drain or open-collector outputs can only pull down",
          "Every state is actively driven"],
         ["Static current", "Yes &mdash; whenever the line is held low, current flows "
                            "through the resistor to ground",
          "No &mdash; exactly one network conducts"],
         ["Speed", "Slow rising edge: RC charging of the bus capacitance. This is why "
                   "I&sup2;C is limited to 100&nbsp;kHz/400&nbsp;kHz/1&nbsp;MHz modes",
          "Fast: the PMOS actively charges the node"],
         ["Typical use", "I&sup2;C SDA/SCL, shared interrupt lines, reset lines, "
                         "strapping pins, unused inputs",
          "All ordinary logic"],
         ["Relevance to our IP", "<b>None inside the block.</b> It appears at the chip "
                                 "boundary and in the CSR bus pads",
          "Every gate the filter synthesises into"]]))

    s.append(ex("Sizing a pull-up resistor, and why the choice is a squeeze",
        given="An I&sup2;C bus at 3.3&nbsp;V with 200&nbsp;pF of bus capacitance. The "
              "standard requires the low level to stay below 0.4&nbsp;V while a device "
              "sinks at most 3&nbsp;mA, and the rise time to be under 300&nbsp;ns for "
              "400&nbsp;kHz fast mode.",
        method="The lower bound comes from current: R must be large enough that "
               "(VDD&minus;V<sub>OL</sub>)/R does not exceed the sink current. The upper "
               "bound comes from speed: the RC rise to the input threshold must fit in "
               "the rise-time budget, which for 0&nbsp;&rarr;&nbsp;0.7&nbsp;VDD takes "
               "about 1.2&nbsp;RC.",
        numbers="Lower bound: R &ge; (3.3&minus;0.4)/3&nbsp;mA = <b>967&nbsp;&Omega;</b>. "
                "Upper bound: R &le; 300&nbsp;ns/(1.2&times;200&nbsp;pF) = "
                "<b>1250&nbsp;&Omega;</b>. So R must sit between roughly 1.0 and "
                "1.25&nbsp;k&Omega; &mdash; a narrow window.",
        trap="The window being this narrow is the finding, not an arithmetic slip. The "
             "usual reflex is to grab the familiar 4.7&nbsp;k&Omega; part, which violates "
             "the upper bound by nearly 4&times; and produces a bus that works on the "
             "bench at low speed and fails at 400&nbsp;kHz with long traces. If the window "
             "closes entirely, the fix is not a different resistor &mdash; it is less bus "
             "capacitance, or an active terminator.",
        extra="Note what dominates: capacitance. Halving C doubles the upper bound. On a "
              "board, capacitance is trace length and the number of devices, so the "
              "electrical problem is really a layout problem."))

    s.append("<h2>Z17.5 The clock, and why anything is clocked at all</h2>")
    s.append("""<p>Combinational logic has no memory: outputs follow inputs after a delay.
    To build anything that accumulates, you need an element that <em>holds</em>. The
    universal one is the edge-triggered <b>D flip-flop</b>: it samples its D input at the
    rising edge of the clock and holds that value on Q until the next rising edge.</p>""")

    s.append(fig(sch.파형([
        ("clk", "_^_^_^_^"),
        ("d",   "__^^__^^"),
        ("q",   "___^^__^"),
    ]), """A D flip-flop. Q takes the value D had at the rising edge and holds it for the
    whole cycle. Note that Q changes only at rising edges, never in between &mdash; that
    is the entire point."""))

    s.append("""<p>The clock is not there to make things go. It is there to make things
    <em>agree on when</em>. Combinational paths through different amounts of logic finish
    at different times; without a clock, a downstream block cannot know whether what it is
    looking at is the final answer or a value still settling. The clock defines an instant
    at which everything is required to have settled, and the design's job is to make that
    true.</p>""")

    s.append(tab("The two timing constraints, and what violating each looks like",
        ["Constraint", "What it requires", "Fix if violated", "Symptom"],
        [["<b>Setup</b>", "Data must arrive at the flop at least t<sub>su</sub> "
                          "<i>before</i> the edge. Limits the <b>longest</b> path.",
          "Shorten the logic, add a pipeline stage, or slow the clock.",
          "Works at low frequency, fails above some clock rate. Reproducible."],
         ["<b>Hold</b>", "Data must remain stable at least t<sub>h</sub> <i>after</i> the "
                         "edge. Limits the <b>shortest</b> path.",
          "Add delay (buffers). <b>Slowing the clock does not help.</b>",
          "Fails at every frequency. Usually a silicon respin &mdash; which is why hold "
          "violations are feared more than setup."]]))

    s.append("""<p>That asymmetry is worth memorising: a setup failure is a performance
    bug, a hold failure is a functional bug. It is also why Part&nbsp;Z15's measurement
    needed a registered timing shell &mdash; a path that starts or ends outside the chip
    has no flop at one end, so neither constraint is defined and the tool has nothing to
    report.</p>""")

    s.append("<h2>Z17.6 Our adder, at gate level</h2>")
    s.append("""<p>Now put it together. The filter's first operation is
    <code>a0 = x0 + x3</code> on 8-bit signed values producing 9 bits. An adder is built
    from full adders, and a full adder is built from the gates above.</p>""")

    s.append(fig(sch.전가산기(),
        """One full adder: sum = a XOR b XOR cin, cout = (a AND b) OR (cin AND (a XOR b)).
        Five gates. The 9-bit fold adder in the filter is nine of these chained, with each
        cout feeding the next cin &mdash; a ripple-carry adder."""))

    s.append(ex("Why the carry chain sets the critical path",
        given="A ripple-carry adder of N bits. Each full adder's carry output takes about "
              "2 gate delays (one AND, one OR) after its carry input is valid.",
        method="The last bit's carry cannot be computed until every earlier carry has "
               "rippled through. Count gate delays along that chain.",
        numbers="Roughly 2N gate delays for N bits: <b>18</b> for the 9-bit fold adder, "
                "<b>34</b> for a 17-bit accumulator. The sum bits themselves add only "
                "one more XOR after their carry arrives.",
        trap="The tempting conclusion is that our filter's critical path is the adder. "
             "It is not, and assuming so sends you optimising the wrong thing. The "
             "measured designs in Z15 use iCE40's dedicated carry chain (SB_CARRY), which "
             "is far faster than generic gates &mdash; the hand design used 48 of them. "
             "On this fabric the multiply-by-constant shift-add network, not the ripple, "
             "dominates. <b>Count gates to understand the structure; measure the tool "
             "output to know the number.</b>",
        extra="This is also why fast-adder architectures exist &mdash; carry-lookahead, "
              "carry-select, prefix adders &mdash; trading area for a logarithmic rather "
              "than linear carry depth. On an FPGA you usually get the vendor's carry "
              "chain and the question does not arise; in an ASIC the synthesiser picks "
              "from a library of adder architectures based on your timing constraint."))

    s.append("<h2>Z17.7 Why saturation costs more than wrapping</h2>")
    s.append("""<p>Part&nbsp;Z16 justified saturation on system grounds: a wrap flips the
    sign and the slicer decides exactly wrong. Here is what it costs, in gates.</p>""")

    s.append(tab("Truncate versus saturate, at gate level",
        ["Operation", "What the hardware does", "Cost"],
        [["Truncate (wrap) to 8 bits", "Discard the upper bits. Route 8 wires, ignore "
                                       "the rest.",
          "<b>Zero gates.</b> It is a renaming of wires."],
         ["Saturate to 8 bits", "Detect whether the value exceeds the 8-bit range, and if "
                                "so substitute the limit. Needs two comparisons and an "
                                "8-bit 2-to-1 multiplexer.",
          "Two comparators plus a mux &mdash; tens of gates, and it sits <b>after</b> the "
          "adder, so it adds directly to the critical path."]]))

    s.append("""<p>This explains a result in Part&nbsp;Z15 that looked backwards at first.
    Narrowing the accumulator from 32 bits to 18 <em>should</em> have shrunk the design,
    but the narrowed variant came out larger in Bambu's estimate &mdash; because the
    narrowing was implemented with <code>sat()</code> at every accumulation step, and each
    of those saturations bought comparators that the plain 32-bit accumulation did not
    need. The width saving was real and the saturation cost was larger.</p>

    <p>The lesson generalises: <b>narrowing a datapath is only free if you narrow it
    somewhere the value provably cannot overflow.</b> In the final tuned design the
    accumulator is wide enough that no intermediate saturation is needed at all &mdash;
    Z16.7 derived the bound, 32,766, which fits in 17 bits &mdash; and saturation happens
    exactly once, at the output, where the specification demands it.</p>""")

    s.append("<h2>Z17.8 The whole stack, one page</h2>")
    s.append(tab("Every level, and what our filter looks like there",
        ["Level", "Our filter at this level", "Who works here"],
        [["System", "One box in the receive chain, between ADC and DFE",
          "Architect; the spec of Z16.4 is written here"],
         ["RTL / HLS", "40 lines of Verilog, or 12 lines of C++ plus a build command",
          "You, in Parts Z14&ndash;Z15"],
         ["Netlist", "338&ndash;1218 cells depending on how the C++ was typed",
          "Synthesis (<code>yosys</code>); you read its report"],
         ["Gate", "SB_LUT4 &times;228, SB_CARRY &times;97 &mdash; NANDs and carry chains "
                  "in a specific arrangement",
          "The tool; you influence it through coding style and constraints"],
         ["Transistor", "Each LUT4 is a small memory plus a mux tree; each is CMOS "
                        "pull-up/pull-down as in Z17.2",
          "The FPGA vendor, or in an ASIC the standard-cell library team"],
         ["Silicon", "Configuration bits in an iCE40, or diffused transistors in a mask set",
          "The foundry"]]))

    s.append("""<p>The practical point of having walked down this stack is that the levels
    are not independent. A choice at the top &mdash; &ldquo;saturate rather than
    wrap&rdquo; &mdash; became comparators and a mux at the gate level, which became area
    and delay in the measurements of Part&nbsp;Z15, which fed back into the specification
    in Z16.4. An engineer who can only see one level cannot follow that chain, and will
    make the choice at the top without knowing what it costs at the bottom.</p>""")

    return "\n".join(s)
