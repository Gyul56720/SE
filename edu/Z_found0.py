# -*- coding: utf-8 -*-
"""Volume I, Part 0 -- Entry-level foundations (the gentle start)."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from figs import svg, box, txt, arr, line, poly


def _f_abstraction():
    b = []
    levels = [("System / architecture", "what the chip does"),
              ("Micro-architecture", "how it is organised"),
              ("RTL", "registers and logic between them"),
              ("Gate / netlist", "AND, OR, flip-flops"),
              ("Transistor / circuit", "MOSFETs, R, C"),
              ("Device physics", "carriers, fields"),
              ("Materials", "silicon, oxide, metal")]
    y = 24
    for name, sub in levels:
        b.append(box(60, y, 250, 34, name, sub, 9))
        if y > 24:
            b.append(arr(185, y - 12, 185, y))
        y += 46
    b.append(txt(340, 130, "Each level hides the one below it.", 9))
    b.append(txt(340, 150, "An abstraction leaks when the level", 9))
    b.append(txt(340, 168, "below changes the answer above.", 9))
    b.append(txt(340, 196, "Most hard bugs are leaks.", 9, "start", 'font-weight="bold"'))
    return svg(560, y + 6, "".join(b))


def ch_abstraction():
    s = ['<h1 id="z1">Z1. How a Chip Is Described: Levels of Abstraction</h1>']
    s.append("""<p>This chapter is the gentlest in the book and the one that everything
    else refers back to. A modern chip contains on the order of 10<sup>10</sup>
    transistors; no person reasons about them individually. The field copes by stacking
    abstractions, each hiding the one beneath. Knowing the stack &mdash; and knowing where
    it leaks &mdash; is the organising skill of the discipline.</p>""")
    s.append(fig(_f_abstraction(), "The abstraction stack. Work at one level, but know "
                                   "which level below will eventually intrude."))
    s.append(tab("What each level is, and who works there",
        ["Level", "Unit of thought", "Typical artefact", "Role"],
        [["System", "Throughput, latency, power budget",
          "Architecture document, performance model", "System architect"],
         ["Micro-architecture", "Pipelines, buffers, state machines",
          "Block diagrams, cycle-accurate model", "Micro-architect, modelling engineer"],
         ["<b>RTL</b>", "Registers and the logic between them",
          "SystemVerilog / VHDL", "<b>Design engineer</b>"],
         ["Gate", "Boolean functions, standard cells",
          "Netlist", "Synthesis tool (not usually a person)"],
         ["Circuit", "Transistors, resistance, capacitance",
          "SPICE netlist", "Analogue / custom designer"],
         ["Device", "Carrier transport, fields", "Compact models (BSIM)", "Device engineer"],
         ["Materials", "Doping, oxides, metals", "Process recipe", "Process engineer"]]))
    s.append("""<div class="bs">The middle of this stack is where digital IP work
    happens. A digital designer writes RTL and trusts the synthesis tool to produce gates,
    the library to characterise them, and the process to build them. The trust is
    well-founded almost all of the time.</div>""")
    s.append("""<div class="ms"><b>Almost all of the time is the important qualifier,
    and the exceptions form a checklist worth memorising.</b> Abstractions leak in a small
    number of recurring ways, each of which appears later in this book:
    <ul>
    <li><b>Timing</b> &mdash; RTL describes behaviour without delay, but a real gate takes
    time, so a functionally correct design can fail (Chapter B3).</li>
    <li><b>Metastability</b> &mdash; a flip-flop is modelled as producing 0 or 1, but a
    real one can do neither for a while (Chapter C3).</li>
    <li><b>Power</b> &mdash; RTL has no notion of energy, yet switching activity and
    glitching are decided by RTL structure (Chapter B2).</li>
    <li><b>Physical size</b> &mdash; RTL has no geometry, but wire delay depends on it
    (Chapter B4).</li>
    <li><b>Side channels</b> &mdash; two circuits computing the same function can be
    distinguished by their power consumption (Chapter H3).</li>
    <li><b>Radiation and ageing</b> &mdash; a stored bit is assumed permanent; physically
    it is not (Chapter K3).</li>
    </ul>
    <b>A useful way to read the rest of this book is as a systematic tour of these
    leaks</b>, because they are exactly the places where an engineer's judgement is still
    required and a tool cannot be trusted alone.</div>""")

    s.append("<h2>Z1.2 The design flow in one page</h2>")
    s.append(tab("From idea to silicon",
        ["Phase", "Input", "Output", "Principal risk"],
        [["Specification", "Requirements", "Written specification", "Ambiguity"],
         ["Modelling", "Specification", "Reference model", "Misreading the specification"],
         ["RTL design", "Specification", "Synthesisable RTL", "Functional error"],
         ["Verification", "RTL + model", "Coverage, bug reports", "<b>Missing a case</b>"],
         ["Synthesis", "RTL + constraints + library", "Gate netlist", "Wrong constraints"],
         ["Place and route", "Netlist + floorplan", "Layout", "Congestion, timing"],
         ["Sign-off", "Layout", "GDSII", "An unchecked corner"],
         ["Fabrication", "GDSII", "Wafers", "Yield"],
         ["Bring-up", "Packaged parts", "Working system", "<b>No visibility</b>"],
         ["Production test", "&mdash;", "Sorted devices", "Test escape"]]))
    s.append("""<div class="warn"><b>The cost of fixing a defect rises by roughly an order
    of magnitude at each phase boundary.</b> A specification ambiguity caught while writing
    the specification costs an hour. Caught in verification it costs a week. Caught at
    bring-up it costs a mask set &mdash; hundreds of thousands to millions of dollars and
    a three-month schedule slip. This asymmetry, not perfectionism, is why the industry
    invests so heavily in front-end rigour, and it is the economic reason a modelling team
    exists at all.</div>""")
    return "\n".join(s)


def ch_boolean():
    s = ['<h1 id="z2">Z2. Boolean Algebra and Combinational Logic</h1>']
    s.append("""<div class="bs">Digital logic rests on a two-element Boolean algebra with
    operations AND (&middot;), OR (+) and NOT (&prime;). Its axioms give the identities
    used to simplify expressions, and every combinational circuit is the realisation of
    some Boolean function.</div>""")
    s.append(tab("Identities used constantly",
        ["Name", "Statement"],
        [["Identity", "<i>A</i>&middot;1 = <i>A</i>, &nbsp; <i>A</i>+0 = <i>A</i>"],
         ["Null", "<i>A</i>&middot;0 = 0, &nbsp; <i>A</i>+1 = 1"],
         ["Idempotence", "<i>A</i>&middot;<i>A</i> = <i>A</i>"],
         ["Complement", "<i>A</i>&middot;<i>A</i>&prime; = 0, &nbsp; <i>A</i>+<i>A</i>&prime; = 1"],
         ["<b>De Morgan</b>",
          "(<i>A</i>&middot;<i>B</i>)&prime; = <i>A</i>&prime;+<i>B</i>&prime;, &nbsp; "
          "(<i>A</i>+<i>B</i>)&prime; = <i>A</i>&prime;&middot;<i>B</i>&prime;"],
         ["Absorption", "<i>A</i> + <i>A</i>&middot;<i>B</i> = <i>A</i>"],
         ["Consensus",
          "<i>AB</i> + <i>A</i>&prime;<i>C</i> + <i>BC</i> = <i>AB</i> + <i>A</i>&prime;<i>C</i>"],
         ["Shannon expansion",
          "<i>f</i> = <i>x</i>&middot;<i>f</i>|<sub><i>x</i>=1</sub> + "
          "<i>x</i>&prime;&middot;<i>f</i>|<sub><i>x</i>=0</sub>"]]))
    s.append("""<div class="ms"><b>Two of these are more than algebra.</b> De Morgan's laws
    are the reason CMOS is built from NAND and NOR rather than AND and OR: a CMOS gate is
    naturally inverting, so <i>every</i> logic function must be expressible in inverting
    gates, which De Morgan guarantees. The <b>consensus term</b> is the redundant product
    that can be removed without changing the function &mdash; but removing it can create a
    <i>static hazard</i>, a momentary glitch when inputs change. In synchronous logic a
    glitch before the next clock edge is harmless and the term is removed for area; in
    asynchronous logic or in a clock-gating enable it is not, and the redundant term must
    be kept. <b>The same simplification is correct in one context and a bug in another,
    which is why hazard-free synthesis is a distinct option in the tools.</b></div>""")
    s.append(tab("Representations of a Boolean function",
        ["Form", "Size", "Canonical?", "Use"],
        [["Truth table", "2<sup><i>n</i></sup> rows", "Yes", "Definition; small functions"],
         ["Karnaugh map", "2<sup><i>n</i></sup>", "No", "Hand minimisation up to ~5 variables"],
         ["Sum of products", "Varies", "No (unless canonical)", "PLA, two-level synthesis"],
         ["Quine&ndash;McCluskey", "&mdash;", "&mdash;", "Exact minimisation; exponential"],
         ["Espresso", "&mdash;", "&mdash;", "Heuristic; what tools actually use"],
         ["BDD", "Order-dependent", "<b>Yes</b>", "Equivalence checking"],
         ["AIG", "Compact", "No", "<b>Modern synthesis and formal engines</b>"]]))

    s.append("<h2>Z2.2 Standard combinational blocks</h2>")
    s.append(tab("The building blocks every design contains",
        ["Block", "Function", "Cost", "Note"],
        [["Multiplexer", "Select one of <i>n</i> inputs",
          "<i>n</i>&minus;1 two-input muxes, or a tree",
          "<b>A mux is functionally complete</b> &mdash; any function can be built from muxes"],
         ["Decoder", "<i>n</i> &rarr; 2<sup><i>n</i></sup> one-hot", "2<sup><i>n</i></sup> gates",
          "Address decoding, instruction decode"],
         ["Encoder / priority encoder", "one-hot &rarr; binary", "&mdash;",
          "Interrupt arbitration, leading-zero detection"],
         ["Comparator", "Equality or magnitude", "XOR tree / subtract",
          "Magnitude comparison is an adder in disguise"],
         ["Shifter / barrel shifter", "Shift by a variable amount",
          "log<sub>2</sub><i>n</i> mux stages", "Used in floating point, in gearboxes"],
         ["Adder", "See Chapter C1", "&mdash;", "The most studied block in the field"],
         ["Parity / population count", "XOR tree / adder tree", "&mdash;",
          "ECC, binary neural networks"]]))
    s.append("""<div class="ms"><b>The observation that a multiplexer is functionally
    complete is more than a curiosity: it is why FPGAs work.</b> An FPGA's logic element is
    a small lookup table, which is physically a multiplexer tree driven by configuration
    bits. Any four-input function is realised by loading sixteen bits. The entire
    programmable-logic industry rests on the Shannon expansion identity in the table
    above. <b>Recognising that a familiar identity is the foundation of a product category
    is the kind of connection this book is trying to make routine.</b></div>""")
    return "\n".join(s)


def ch_sequential():
    s = ['<h1 id="z3">Z3. Sequential Logic and State</h1>']
    s.append("""<div class="bs">A combinational circuit's output depends only on its
    present inputs. Adding memory &mdash; elements that hold a value &mdash; produces
    sequential logic, whose output depends on the history of inputs. That history is
    summarised in the <b>state</b>.</div>""")
    s.append(tab("Storage elements",
        ["Element", "Behaviour", "Use", "Hazard"],
        [["SR latch", "Set/reset, level sensitive", "Building block",
          "Forbidden input combination"],
         ["<b>D latch</b>", "Transparent when enabled", "Time borrowing, low-power designs",
          "<b>Transparency complicates timing analysis</b>"],
         ["<b>D flip-flop</b>", "Captures on a clock edge", "The standard element",
          "Setup/hold must be met"],
         ["Master&ndash;slave", "Two latches in series", "How a flip-flop is built",
          "&mdash;"],
         ["Pulsed latch", "Narrow transparency window", "High performance", "Timing complexity"],
         ["Register file", "Array with multiple ports", "Processors", "Port count costs area"]]))
    s.append("""<div class="warn"><b>Unintentional latches are one of the most common RTL
    defects.</b> In a combinational <code>always</code> block, if some path through the
    logic leaves a signal unassigned, the synthesiser must remember its previous value and
    therefore infers a latch. The design usually still simulates correctly, but a latch in
    a nominally combinational path is a timing analysis problem and often a functional one.
    The defence is mechanical: assign a default value at the top of every combinational
    block, cover every branch, and treat the lint warning as an error. <b>This is the first
    check in any RTL review.</b></div>""")
    s.append(tab("Finite state machine styles",
        ["Style", "Output depends on", "Property"],
        [["<b>Moore</b>", "State only",
          "Outputs are registered and glitch-free; one cycle of latency"],
         ["<b>Mealy</b>", "State and inputs",
          "Faster response; <b>outputs can glitch and create combinational paths</b>"],
         ["Registered Mealy", "State and registered inputs", "Compromise; usually preferred"]]))
    s.append("""<div class="ms"><b>The Moore/Mealy choice has a direct consequence at
    module boundaries.</b> A Mealy output is a combinational function of an input, so
    connecting two Mealy modules can create a path that runs through both in a single
    cycle &mdash; or, if each one's input depends on the other's output, a combinational
    loop. This is the general form of the valid/ready loop described in Chapter C2.
    <b>For an IP block, registering all outputs (Moore style) costs one cycle of latency
    and removes an entire class of integration failures</b>, which is usually the right
    trade for something a stranger will instantiate.</div>""")

    s.append("<h2>Z3.2 Counters, shift registers and LFSRs</h2>")
    s.append(tab("Sequential building blocks",
        ["Block", "Function", "Where used"],
        [["Binary counter", "Increment", "Addressing, timing"],
         ["<b>Gray counter</b>", "One bit changes per step",
          "<b>CDC-safe pointers</b>, low-power encoding"],
         ["Johnson counter", "Twisted ring", "Multi-phase clock generation"],
         ["Shift register", "Serial movement", "Serialisers, delay lines"],
         ["<b>LFSR</b>", "Shift with XOR feedback",
          "<b>PRBS generation, scramblers, CRC, BIST, test patterns</b>"],
         ["<b>CRC</b>", "Polynomial remainder", "Frame check sequences"]]))
    s.append("""<div class="ms"><b>The LFSR is the most reused structure in
    communications hardware, and all of its uses are the same mathematics.</b> An LFSR
    computes a remainder modulo a polynomial over GF(2). Choose a primitive polynomial and
    it cycles through all 2<sup><i>n</i></sup>&minus;1 non-zero states, giving a
    maximal-length pseudo-random sequence &mdash; that is a PRBS generator, and also a
    scrambler. Feed data in as you shift and the final state is the remainder &mdash; that
    is a CRC. Use it to produce stimulus and to compact responses and you have built-in
    self test. <b>One circuit, four products, because they are one piece of algebra.</b>
    Chapter I2 develops the algebra; this is where it first appears.</div>""")
    return "\n".join(s)


def ch_circuits():
    s = ['<h1 id="z4">Z4. Circuit Analysis: the Minimum Needed</h1>']
    s.append(tab("Laws and elements",
        ["Item", "Statement", "Digital-design relevance"],
        [["KCL", "Currents into a node sum to zero", "Power grid analysis"],
         ["KVL", "Voltages around a loop sum to zero", "IR drop"],
         ["Ohm", "<i>V</i> = <i>IR</i>", "Wire and switch resistance"],
         ["Capacitor", "<i>i</i> = <i>C</i>&nbsp;d<i>v</i>/d<i>t</i>",
          "<b>The dominant load in CMOS</b>"],
         ["Inductor", "<i>v</i> = <i>L</i>&nbsp;d<i>i</i>/d<i>t</i>",
          "Package and board; cause of supply noise"],
         ["RC time constant", "&tau; = <i>RC</i>",
          "<b>Gate delay, wire delay, rise time</b>"],
         ["Th&eacute;venin / Norton", "Source equivalents", "Driver modelling, termination"],
         ["Superposition", "Linear circuits only", "Noise analysis"]]))
    s.append("""<div class="bs">For digital work the essential relation is the RC charging
    curve: a capacitor charged through a resistor reaches 63% of its final value in one
    time constant &tau;&nbsp;=&nbsp;<i>RC</i>, and about 50% in 0.69&tau;. Since a logic
    gate switches when its input crosses the threshold near mid-supply, <b>propagation
    delay is approximately 0.69<i>R</i><sub>on</sub><i>C</i><sub>load</sub></b>.</div>""")
    s.append("""<div class="ms"><b>That single expression explains most of digital design
    practice.</b> Delay is proportional to load capacitance, so driving many gates is slow
    &mdash; hence buffer trees. Delay is proportional to on-resistance, which falls as
    transistor width rises, so wider devices are faster &mdash; but a wider device presents
    a larger capacitance to <i>its</i> driver, which is why sizing is a chain optimisation
    rather than a local one, and why the logical-effort method of Chapter B2 exists.
    Dynamic energy is <i>CV</i><sup>2</sup> per transition, which is why lowering supply
    voltage is the strongest power lever and why it costs speed. <b>Four consequences from
    one equation; this is the level of leverage that makes a small amount of circuit
    theory worth carrying.</b></div>""")
    s.append(tab("Frequency-domain concepts a digital engineer meets",
        ["Concept", "Meaning", "Where encountered"],
        [["Impedance <i>Z</i>(&omega;)", "Generalised resistance", "Power delivery, termination"],
         ["Pole / zero", "Roots of the denominator / numerator",
          "Filter and loop design"],
         ["Bode plot", "Magnitude and phase versus frequency", "PLL loop stability"],
         ["Q factor", "Energy stored / dissipated per cycle",
          "Resonance in power networks, oscillator phase noise"],
         ["Phase margin", "Stability measure", "<b>Any feedback loop, including a PLL</b>"],
         ["Bandwidth &times; gain", "Roughly constant for an amplifier",
          "Why high gain and high speed conflict"]]))
    return "\n".join(s)
