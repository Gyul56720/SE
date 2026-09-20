# -*- coding: utf-8 -*-
"""Volume III, Part Z16 -- Before any code: the system, the spec, the schematic."""
import sys
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, derive
import sch


def ch_sysarch():
    s = ['<h1 id="z16">Z16. Before Any Code &mdash; System, Spec, Schematic</h1>']

    s.append("""<p>Everything so far in this volume started from a piece of RTL or a piece
    of C++. That is the wrong end. In a real design house the code is the <em>fifth</em>
    thing you produce, and by the time you type it most of the decisions that matter are
    already made. This part walks the four things that come first, for the same 4-tap
    equaliser the previous parts built: where it sits in a system, what it is responsible
    for, what its specification says, and what it looks like as a drawing &mdash; all the
    way down to transistors.</p>

    <p>Nothing here assumes prior hardware knowledge. If you have written C++ and never
    seen a schematic, this part and the two after it are written for you.</p>""")

    s.append("<h2>Z16.1 What problem this IP exists to solve</h2>")
    s.append("""<p>A serial link sends bits down a copper trace. At 10&nbsp;Gb/s a bit is
    100&nbsp;picoseconds wide, and a 30&nbsp;cm PCB trace behaves like a low-pass filter:
    high frequencies are attenuated more than low ones. The consequence has a name &mdash;
    <b>inter-symbol interference</b> (ISI). Energy from bit <i>n</i> is still arriving when
    bit <i>n</i>+1 is being sampled, so the receiver's decision about one bit depends on
    the bits around it.</p>""")

    s.append(fig(sch.파형([
        ("sent",     "_^^_^__^"),
        ("received", "xxxxxxxx"),
        ("clk",      "_^_^_^_^"),
    ]), """What the channel does. The transmitted waveform (top) is clean. The received
    waveform is smeared across bit boundaries &mdash; drawn as &lsquo;unknown&rsquo;
    because at the sampling instant its value depends on neighbouring bits, not just the
    current one. Recovering the top row from the middle row is the equaliser's job."""))

    s.append("""<p>An equaliser undoes that smearing. A <b>feed-forward equaliser</b>
    (FFE) does it with a filter whose response approximates the inverse of the channel:
    take the last few samples, scale each by a coefficient, add them up. That sum is the
    filter this book has been building. Four taps, 8-bit samples, coefficients
    {&minus;18, 111, 111, &minus;18} in Q1.7 &mdash; a mild high-frequency boost, which is
    exactly the shape that undoes a mild low-pass channel.</p>""")

    s.append(ex("Why those coefficients have that shape",
        given="The coefficients are {&minus;18, 111, 111, &minus;18} in Q1.7, i.e. "
              "{&minus;0.141, 0.867, 0.867, &minus;0.141}.",
        method="Sum them to get the DC (zero-frequency) gain. Alternate their signs and "
               "sum to get the Nyquist (highest-frequency) gain.",
        numbers="DC gain = (&minus;18+111+111&minus;18)/128 = 186/128 = <b>1.453</b>. "
                "Nyquist gain = (&minus;18&minus;111+111+18)/128 = 0/128 = <b>exactly "
                "zero</b>. The filter passes DC at 1.45&times; and has a perfect null at "
                "the highest representable frequency.",
        trap="That is a <b>low-pass</b> response &mdash; and not a mild one: a null at "
             "Nyquist is what a smoothing filter does, the opposite of what an equaliser "
             "is supposed to do. The negative outer taps make it <i>look</i> like a "
             "boost, but the adjacent equal centre taps dominate and their sum "
             "111&minus;111 cancels exactly at Nyquist. Treat this filter as what it "
             "is &mdash; a worked example with realistic structure, arithmetic and "
             "saturation behaviour &mdash; not as a coefficient set anyone should ship. "
             "Real FFE coefficients are adapted at run time by an LMS loop against the "
             "measured channel, and the sign pattern is typically the other way round.",
        extra="This is the difference between a teaching example and a product. The "
              "structure, widths, saturation, handshake and verification in this book are "
              "all real. The coefficient values are placeholders, and the book says so "
              "rather than letting the reader assume otherwise."))

    s.append("<h2>Z16.2 Where it sits &mdash; the whole receive chain</h2>")
    s.append("""<p>The filter is one box in a chain. Knowing the boxes on either side is
    not background reading; it is what determines your interface, your latency budget and
    your clock.</p>""")

    s.append(fig(sch.블록도([
        ["CTLE", "VGA / AGC", "ADC", "FFE"],
        ["DFE", "Slicer", "CDR", "Deserializer"],
        ["PCS", "MAC", "AXI", "SoC"],
    ], 칸=118, 설명={
        "CTLE": "아날로그 등화기\n연속시간, 이득 고정",
        "VGA / AGC": "이득 조절\n진폭을 ADC 범위로",
        "ADC": "표본화+양자화\n여기서 아날로그가 끝난다",
        "FFE": "★ 우리 IP\n4탭 FIR",
        "DFE": "판정귀환 등화기\n고리가 있다",
        "Slicer": "0/1 판정\n비교기 한 개",
        "CDR": "클럭 복원\n위상 고정",
        "Deserializer": "직렬→병렬\n예: 1비트→64비트",
        "PCS": "64b/66b, 스크램블러\n정렬, FEC",
        "MAC": "프레임, CRC\nMTU 처리",
        "AXI": "버스 인터페이스\nDMA로 메모리에",
        "SoC": "CPU, 드라이버",
    }), """The 10&nbsp;Gb/s receive chain. Our IP is the fourth box. Everything before it
    is analogue or mixed-signal; everything after it is ordinary synchronous digital
    logic. The boundary sits at the ADC &mdash; which is exactly why the IP's input is an
    8-bit two's-complement sample and not a voltage."""))

    s.append(tab("Each neighbour, and what it forces on our design",
        ["Block", "What it does", "What it forces on us"],
        [["CTLE", "Continuous-time linear equaliser: an analogue filter that boosts high "
                  "frequencies before sampling.",
          "It removes the bulk of the ISI, so our digital FFE only has to clean up the "
          "residue &mdash; which is why 4 taps is enough and 40 is not needed."],
         ["VGA / AGC", "Variable-gain amplifier with automatic gain control: scales the "
                       "signal so it fills the ADC's input range.",
          "It guarantees our input occupies most of the 8-bit range. If AGC is broken our "
          "input is tiny and the filter output is mostly quantisation noise &mdash; a "
          "failure that looks like our bug."],
         ["ADC", "Analogue-to-digital converter: turns a voltage into an 8-bit number, "
                 "once per unit interval.",
          "<b>Defines our input format.</b> 8-bit, two's complement, Q1.7, one sample per "
          "clock. Everything about our widths comes from this box."],
         ["DFE", "Decision-feedback equaliser: subtracts the known ISI contribution of "
                 "already-decided bits. Contains a feedback loop.",
          "It sits immediately after us and its loop must close in one unit interval. Our "
          "latency is in series with nothing critical, but our <b>throughput</b> must be "
          "one sample per clock or the DFE starves."],
         ["Slicer", "A comparator: decides 0 or 1 from the equalised sample.",
          "It consumes our 8-bit output and only really needs the sign plus a few bits of "
          "margin &mdash; which is why saturating (rather than wrapping) matters so much: "
          "a wrap flips the sign and the slicer decides exactly wrong."],
         ["CDR", "Clock and data recovery: extracts the sampling clock from the data.",
          "It provides our clock. Our design must be fully synchronous to it and must "
          "tolerate its reset sequencing."],
         ["PCS / MAC", "Protocol layers: alignment, 64b/66b coding, FEC, framing, CRC.",
          "Far enough away not to constrain us directly, but they set the overall latency "
          "budget the whole chain is measured against."]]))

    s.append("<h2>Z16.3 &ldquo;Front end&rdquo; and &ldquo;back end&rdquo; mean two "
             "different things</h2>")
    s.append("""<p>This trips up every newcomer, because the same two words name two
    unrelated axes and practitioners switch between them without warning.</p>""")

    s.append(tab("Two meanings of front-end / back-end",
        ["Axis", "Front end", "Back end", "Where our IP is"],
        [["<b>Signal chain</b> (where in the data path)",
          "Analogue and mixed-signal: CTLE, VGA, ADC, CDR. Deals in volts and "
          "picoseconds.",
          "Digital: PCS, MAC, bus, software. Deals in bits and packets.",
          "First block of the digital back end &mdash; immediately after the ADC."],
         ["<b>Design flow</b> (where in the schedule)",
          "RTL design, verification, synthesis-for-estimate. Produces a netlist. This is "
          "where this book lives.",
          "Floorplan, place and route, clock tree, timing closure, DRC/LVS, GDSII "
          "tape-out.",
          "Parts Z14&ndash;Z15 are flow front-end. <code>synth.sh</code>'s "
          "<code>nextpnr</code> step is the smallest possible taste of flow back-end."]]))

    s.append("""<p>So &ldquo;our IP is in the back end&rdquo; and &ldquo;we are doing
    front-end work&rdquo; are both true at once, and mean different things. When someone
    says it, ask which axis.</p>""")

    s.append("<h2>Z16.4 The specification, written before the code</h2>")
    s.append("""<p>A specification is not a description of what you built. It is the
    contract you write first, and then check what you built against. Here is the real one
    for this block. Every row is a number a customer can hold you to, and every row was
    measured in Parts&nbsp;Z14&ndash;Z15 &mdash; the spec came first and the measurements
    came back to fill it in.</p>""")

    s.append(tab("IP specification: 4-tap feed-forward equaliser",
        ["Item", "Value", "How it is verified"],
        [["Function", "y[n] = sat<sub>8</sub>( (&Sigma; h[i]&middot;x[n&minus;i]) &gt;&gt; 7 )",
          "Exhaustive C++ equivalence over all 2<sup>32</sup> inputs (Z14.3)"],
         ["Input", "4 &times; 8-bit signed, Q1.7, one sample per clock",
          "Testbench drives all corner combinations plus random"],
         ["Output", "1 &times; 8-bit signed, Q1.7, saturating",
          "Saturation exercised by corner vectors; all 256 output codes seen"],
         ["Coefficients", "Compile-time constants, symmetric",
          "Symmetry asserted at build; folding verified bit-exact against unfolded"],
         ["Throughput", "1 sample/clock, no back-pressure",
          "Cycle count checked in the harness, not just values"],
         ["Latency", "1 clock (combinational variant) / 3 clocks (pipelined)",
          "Measured start-to-done in simulation"],
         ["Clock", "Single clock, synchronous, rising edge", "Lint (no latches, no "
          "multiple drivers) plus synthesis"],
         ["Reset", "Synchronous, <b>active high</b>", "Explicitly stated because the HLS "
          "tool defaults to active low &mdash; see Z15.3"],
         ["Area", "252 LC (hand) / 386 LC (HLS @3ns) on iCE40 HX8K",
          "yosys + nextpnr, three placer seeds"],
         ["F<sub>max</sub>", "76.9 MHz (hand, 3-stage) / 106.0 MHz (HLS @3ns)",
          "nextpnr with a registered timing shell"],
         ["Deliverables", "RTL, C++ model, testbench, vectors, synthesis script, "
          "datasheet, integration guide, known issues",
          "<code>edu/house/release.sh</code> gates all of them"]]))

    s.append("""<p>Two rows are worth pausing on. The <b>reset polarity</b> row exists
    because getting it wrong cost a debugging session in Part&nbsp;Z15 &mdash; a
    specification that does not pin down polarity, edge and synchronicity has not specified
    the reset at all. And <b>throughput</b> is a separate row from latency because a
    value-only regression cannot see a block getting slower; Part&nbsp;Z1 caught a mutant
    that broke throughput while keeping every output value correct.</p>""")

    s.append("<h2>Z16.5 What else you must own to ship this</h2>")
    s.append("""<p>A 4-tap filter is not a product. A customer who buys &ldquo;an
    equaliser&rdquo; expects a block they can drop into a chip, and that means a
    surprising amount of surrounding machinery. For a one-person design house the
    question is not whether you need these &mdash; you do &mdash; but which you write,
    which you take from an open collection, and which you decline to support.</p>""")

    s.append(tab("Supporting IP, and the one-person make/buy call",
        ["What", "Why it is needed", "Call"],
        [["Register file / CSR block",
          "Coefficients, bypass, status, ID. No customer accepts a block with no "
          "software interface.",
          "<b>Make.</b> Generated from one description &mdash; <code>edu/house/regmap.py</code> "
          "emits RTL, C header, docs and IP-XACT from a single source."],
         ["APB or AXI-Lite bridge", "How the CSRs are reached from the SoC.",
          "<b>Make</b> (APB is ~100 lines and fully specified) or take an open one. "
          "AXI-Lite is bigger; buy or adapt."],
         ["Clock-domain crossing / FIFO",
          "The CSR bus and the data path are usually on different clocks.",
          "<b>Buy or adopt.</b> CDC is the single most common source of bugs that pass "
          "simulation and fail silicon. Do not hand-roll a synchroniser."],
         ["Reset synchroniser", "An asynchronous reset release violates recovery/removal "
                                "timing on every flop it reaches.",
          "<b>Make</b>, from the standard two-flop pattern, and lint for it."],
         ["PLL / CDR", "Provides the clock.",
          "<b>Decline.</b> This is analogue IP. A one-person digital house does not build "
          "a CDR; you specify the clock you need and document it."],
         ["SerDes PHY", "Serialiser, driver, receiver front end.",
          "<b>Decline.</b> Same reason, larger."],
         ["DFT / scan insertion", "Manufacturing test. Without it the chip cannot be "
                                  "screened.",
          "<b>Defer to the integrator</b>, but write RTL that is scan-friendly: no gated "
          "clocks you invented, no latches, no async logic."],
         ["Lint and CDC rule decks", "Customers run them and send you the report.",
          "<b>Make.</b> <code>verilator --lint-only -Wall</code> is free and catches most "
          "of it; ship the clean report as a deliverable."],
         ["Documentation set", "Datasheet, integration guide, known issues.",
          "<b>Make.</b> This is the cheapest thing you can do to look like a real vendor, "
          "and the thing most one-person efforts skip."]]))

    s.append("""<p>The honest summary of that table: the filter is perhaps 15&nbsp;% of the
    work of selling the filter. Parts&nbsp;Y and&nbsp;Z4 build the other 85&nbsp;%.</p>""")

    s.append("<h2>Z16.6 The five levels of drawing</h2>")
    s.append("""<p>&ldquo;Schematic&rdquo; is not one thing. The same design is drawn at
    five levels of detail and each answers a different question. Knowing which level you
    are being shown is half of reading a drawing.</p>""")

    s.append(tab("Levels of representation, from system to silicon",
        ["Level", "What a box is", "What a line is", "Question it answers", "Where in this book"],
        [["System", "A whole function (ADC, MAC)", "A stream of data",
          "Does the architecture close?", "Z16.2, above"],
         ["Block / RTL", "A module with ports", "A named bus of bits",
          "What are the interfaces and widths?", "Z16.7"],
         ["Datapath", "An adder, a multiplier, a register", "A bundle of wires",
          "Where does the critical path run?", "Z17.4"],
         ["Gate", "A NAND, a flip-flop", "One wire carrying one bit",
          "How many gates deep is it?", "Z17.3"],
         ["Transistor", "One MOSFET", "One node", "Why does a gate behave as it does?",
          "Z17.1&ndash;Z17.2"]]))

    s.append("<h2>Z16.7 Our IP at block level</h2>")
    s.append("""<p>This is the drawing that belongs at the top of the datasheet. Boxes are
    modules, lines are buses, and the widths are on the lines because a width mismatch is
    the most common integration failure there is.</p>""")

    s.append(fig(sch.블록도([
        ["x[n]  8b", "shift reg\n4 x 8b", "fold\n2 adders", "multiply\n2 const", "shift+sat\n>>7, clip", "y[n]  8b"],
    ], 칸=104, 간격=26, 설명={
        "shift reg\n4 x 8b": "x[n]..x[n-3]",
        "fold\n2 adders": "9b 두 개",
        "multiply\n2 const": "17b",
        "shift+sat\n>>7, clip": "8b",
    }), """The equaliser at block level. Reading left to right: samples enter and are held
    in a 4-deep shift register; symmetric pairs are added (9 bits, because adding two
    8-bit numbers needs 9); each sum is multiplied by one constant coefficient (17 bits);
    the result is shifted right by 7 to return to Q1.7 and saturated back to 8 bits. Every
    width change on this diagram is a place where a bug can hide silently."""))

    s.append(derive("Why every width on that diagram is what it is",
        [("The input is 8 bits because the ADC produces 8 bits.",
          "The interface is set by the neighbour, not by us."),
         ("The fold adders are 9 bits, not 8.",
          "Adding two <i>n</i>-bit signed numbers can need <i>n</i>+1 bits: "
          "127+127 = 254, which does not fit in 8-bit signed. Truncating here would be "
          "wrong only for large inputs &mdash; a bug that passes random testing."),
         ("The multiply result is 17 bits.",
          "9-bit operand times 8-bit coefficient gives up to 17 bits. The accumulator is "
          "declared 18 in the C++ model, and the maximum magnitude is "
          "127&times;(18+111+111+18) = 32,766, which fits in 17 bits signed with room "
          "to spare &mdash; so the 18-bit saturation in the model never actually fires."),
         ("The shift is by 7, not 8.",
          "Both sample and coefficient are Q1.7, so their product is Q2.14. Returning to "
          "Q1.7 means discarding 7 fractional bits."),
         ("The output saturates to 8 bits rather than wrapping.",
          "The next block is a slicer that decides sign. A wrap turns a large positive "
          "into a large negative and the slicer decides exactly wrong; a saturate is "
          "wrong in magnitude but right in sign.")]))

    s.append("""<p>That last derivation is the whole argument for drawing before coding. It
    took five steps and no Verilog, and it fixed every width in the design. Written the
    other way round &mdash; code first, widths discovered during debug &mdash; each of
    those five steps becomes a regression failure somebody has to chase.</p>""")

    return "\n".join(s)
