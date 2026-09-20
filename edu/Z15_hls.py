# -*- coding: utf-8 -*-
"""Volume III, Part Z15 -- HLS: what it costs, and how to make it win."""
import sys, os, json
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, E
from wex import ex, derive, sweep, num

MODEL = "/home/user/SE/edu/model"
잰것 = json.load(open(os.path.join(MODEL, "잰것.json"), encoding="utf-8"))


def _평균(xs):
    return sum(xs) / len(xs)


def ch_hls():
    s = ['<h1 id="z15">Z15. HLS &mdash; What It Costs, and How to Make It Win</h1>']

    s.append("""<p>High-level synthesis has two well-known drawbacks. The first is that it
    does not always compile what you give it. The second is quality of results: the
    generated RTL can use noticeably more of the device than RTL a person would have
    written. Both are real, and both are measured in this part on a filter that exists in
    this repository.</p>

    <p>But &ldquo;generated RTL is worse than hand RTL&rdquo; is not a law. It is what
    happens when the C++ is written as if it were software. If you understand the
    specification, the architecture you actually want, and what the HLS tool does with what
    you wrote, the generated RTL can beat hand-written RTL &mdash; and below it does, by
    1.38&times; in clock frequency. The rest of this part is how.</p>""")

    s.append("<h2>Z15.1 Drawback one: what the tool refuses</h2>")
    s.append("""<p>Before any quality question there is a compile question. These are
    one-variable controls run against PandA Bambu 2024.10 in this container: each row
    changes exactly one thing from the row above, so the cause is not inferred.</p>""")

    s.append(tab("What Bambu accepts and refuses &mdash; one-variable controls",
        ["Control", "What changed", "Result"],
        [["1", "Pure C, 8-tap FIR", "rc=0, Verilog produced, 101.0&nbsp;MHz"],
         ["2", "Control 1 plus <b>one line</b>: <code>#pragma HLS PIPELINE II=1</code>",
          "rc=11 &mdash; <code>Loop pipelining pragma not supported</code>"],
         ["3", "C++ templates, no pragmas", "rc=0, Verilog produced"],
         ["4a", "<code>ap_uint</code> only", "rc=0, Verilog, 119&ndash;147&nbsp;MHz"],
         ["4b", "<code>hls::stream</code> only",
          "rc=1 &mdash; crash in <code>FixStructsPassedByValue</code>"],
         ["5", "<code>ap_fixed</code> complex 8&times;8 Cholesky",
          "rc=124 &mdash; 40-minute timeout in the front end"]]))

    s.append("""<p>Control&nbsp;2 is the important one: the same file, one line added, a
    hard failure. The blocker is not C++ and not the algorithm &mdash; it is the
    <em>pragma dialect</em>. Every vendor has its own, and pragmas are exactly the part of
    an HLS source that does not port. Control&nbsp;4a is the pleasant surprise: Xilinx's
    arbitrary-precision integer type compiles fine on a tool that has nothing to do with
    Xilinx, because it is ordinary C++ templates. Control&nbsp;4b is the unpleasant one,
    and it has no workaround.</p>""")

    s.append("""<p>The design rule that falls out of this table, and the one
    <code>edu/model/ipmodel.h</code> follows: <b>put the algorithm in portable C++ and keep
    every tool-specific thing out of it.</b> No pragmas in the header, no vendor stream
    types, no heavy template arithmetic. Then the same header compiles under
    <code>g++</code> as the golden model and under the HLS tool as the design, and
    retargeting to a different HLS tool is a build-script change rather than a
    rewrite.</p>""")

    s.append("<h2>Z15.2 Drawback two: quality of results, measured</h2>")
    iw = 잰것["인터페이스폭"]
    s.append("""<p>The filter is four taps, 8-bit samples, constant symmetric coefficients.
    Written naturally in C++ &mdash; <code>int</code> parameters, <code>int</code>
    accumulator, the way anybody would write it &mdash; and handed to Bambu, it produces
    this:</p>""")

    s.append(tab("The same algorithm, the same tool, only the C types differ",
        ["HLS source", "Port width", "Cells", "SB_LUT4", "SB_CARRY"],
        [["<code>int fir_top(int,int,int,int)</code>",
          f"{iw['naive_int포트']['포트폭']} bit", f"{iw['naive_int포트']['cells']:,}",
          f"{iw['naive_int포트']['SB_LUT4']:,}", str(iw['naive_int포트']['SB_CARRY'])],
         ["<code>signed char fir_top_tuned(signed char&times;4)</code>",
          f"{iw['tuned_int8포트']['포트폭']} bit", str(iw['tuned_int8포트']['cells']),
          str(iw['tuned_int8포트']['SB_LUT4']), str(iw['tuned_int8포트']['SB_CARRY'])]]))

    s.append(ex("Where a 4-tap filter's 890 LUTs came from",
        given="A 4-tap FIR with constant coefficients needs, by hand, about 200 LUT4 on "
              "this device. The naive HLS version used %s."
              % f"{iw['naive_int포트']['SB_LUT4']:,}",
        method="Compare the two rows above. The algorithm is identical &mdash; the same "
               "header, the same arithmetic, verified bit-identical. Only the C parameter "
               "types differ.",
        numbers="%.2f&times; reduction (%s cells to %s) from changing <code>int</code> to "
                "<code>signed char</code> in the function signature. Nothing else changed."
                % (iw["배율"], f"{iw['naive_int포트']['cells']:,}",
                   iw['tuned_int8포트']['cells']),
        trap="The tempting explanation is &ldquo;HLS tools are bloated.&rdquo; It is not "
             "that. C's integer promotion rules widen <code>char</code> and "
             "<code>short</code> operands to <code>int</code> before arithmetic, so a C++ "
             "source that says <code>int</code> is <em>requesting</em> a 32-bit datapath "
             "and 32-bit ports. The tool built what the source asked for. A person writing "
             "Verilog types <code>[7:0]</code> and cannot make this mistake &mdash; which "
             "is most of why naive HLS loses to hand RTL.",
        extra="This is the single largest QoR lever in HLS and it costs one line. It is "
              "also the first thing to check when generated RTL comes back four times too "
              "big."))

    s.append("<h2>Z15.3 Making the comparison honest</h2>")
    s.append("""<p>Three things had to be fixed before any number in the next table meant
    anything. Each of them, left unfixed, produces a confident and wrong result.</p>""")

    s.append(tab("Three ways this comparison was wrong before it was right",
        ["Problem", "Symptom", "Fix"],
        [["The two designs computed different functions",
          "None &mdash; area numbers looked fine and meant nothing",
          "Verify both against the same C++ golden vectors first. Every design in the "
          "next table passes 400 vectors with 0 mismatches."],
         ["Reset polarity differed",
          "The generated RTL never asserted <code>done</code>; 400/400 &ldquo;failed&rdquo;",
          "Bambu defaults to <b>active-low</b> reset; the hand RTL used active-high. "
          "<code>--reset-level=high --reset-type=sync</code>."],
         ["Frequency was measured on the wrong path",
          "Adding pipeline registers made Fmax <i>fall</i> (324&nbsp;MHz &rarr; "
          "74&nbsp;MHz), and the hand RTL reported no frequency at all",
          "nextpnr reports register-to-register paths only. Wrap every design in an "
          "identical registered timing shell (<code>fir_shell.v</code>) so the path "
          "being measured is the datapath."]]))

    s.append("""<p>The third deserves emphasis because it is the kind of error that
    survives review. The numbers before the fix were not noise &mdash; they were stable
    across seeds and they were monotonic in the wrong direction. A stable, reproducible,
    completely meaningless measurement is the most dangerous kind, because every instinct
    says to trust it. What made it visible was not a tool warning; it was noticing that
    <em>more registers cannot make a design slower</em>, and refusing to write the number
    down until that contradiction was explained.</p>""")

    s.append("<h2>Z15.4 The sweep &mdash; where HLS loses and where it wins</h2>")
    q = 잰것["QoR"]
    손파이프 = [r for r in q["행"] if r["이름"] == "손RTL 3단 파이프"][0]
    기준f = _평균(손파이프["Fmax"])
    기준lc = 손파이프["LC"]

    rows = []
    for r in q["행"]:
        f = _평균(r["Fmax"])
        rows.append([
            r["이름"].replace("손RTL", "Hand").replace("조합", "combinational")
                     .replace("3단 파이프", "3-stage pipeline").replace("HLS clock=", "HLS @ "),
            str(r["LC"]),
            "%.1f" % f,
            str(r["지연"]),
            "%.2f&times;" % (f / 기준f),
            "%.2f&times;" % (r["LC"] / 기준lc),
        ])
    s.append(tab("Area, frequency and latency &mdash; all verified against the same C++ "
                 "golden model (0 mismatches in 400 vectors each)",
        ["Design", "LC", "Fmax (MHz)", "Latency (cyc)",
         "Fmax vs hand pipe", "Area vs hand pipe"], rows))

    s.append("""<p>Frequency is the mean of three placer seeds; the spread was under
    7&nbsp;% on every row, so the differences below are larger than the noise. Device is
    iCE40 HX8K, <code>nextpnr-ice40 --freq 300 --placer heap</code>.</p>""")

    best = max(q["행"], key=lambda r: _평균(r["Fmax"]))
    s.append(ex("Does the generated RTL beat the hand-written RTL?",
        given="Hand-written 3-stage pipeline: %d LC at %.1f MHz, latency %d. "
              "Best HLS point (%s): %d LC at %.1f MHz, latency %d."
              % (기준lc, 기준f, 손파이프["지연"], best["이름"], best["LC"],
                 _평균(best["Fmax"]), best["지연"]),
        method="Compare each axis separately. There is no single QoR number; area, "
               "frequency and latency trade against each other.",
        numbers="Frequency: %.2f&times; <b>better</b>. Area: %.2f&times; worse. "
                "Latency: %.1f&times; worse."
                % (_평균(best["Fmax"]) / 기준f, best["LC"] / 기준lc,
                   best["지연"] / 손파이프["지연"]),
        trap="Two trivial explanations had to be killed. First, that the hand RTL was a "
             "straw man: the comparison is against a hand-written <i>pipelined</i> design, "
             "not the single-cycle one, precisely so the answer is not rigged. Second, "
             "that tightening the constraint always helps: it does not. At 2&nbsp;ns and "
             "1&nbsp;ns the generated design is both <b>larger and slower</b> than at "
             "3&nbsp;ns. The knee is at 3&nbsp;ns and you only find it by sweeping.",
        extra="So the answer is: yes on frequency, no on area and latency, and only at "
              "one point in the sweep. Anyone quoting the 1.38&times; without the "
              "1.51&times; area and 3&times; latency is selling, not measuring."))

    s.append("<h2>Z15.5 The method &mdash; how to get better QoR than hand RTL</h2>")
    s.append("""<p>The 1.38&times; did not come from the tool being clever. It came from
    four things, in this order. Each is a thing you do, not a thing the tool does.</p>""")

    s.append(derive("Why the generated RTL could win at all",
        [("Write the interface at the true width, not the C default.",
          "Measured above: %.2f&times; area from this alone. Until this is done, nothing "
          "else matters &mdash; the design is four times too big and every later "
          "measurement is taken on the wrong design." % iw["배율"]),
         ("Express the architecture you want, not just the arithmetic you want.",
          "The folded form computes h0(x0+x3)+h1(x1+x2): two multipliers instead of four. "
          "The tool will not discover the symmetry; you state it, and "
          "<code>equiv.cpp</code> proves you stated it correctly."),
         ("Let the tool re-schedule, and sweep the constraint.",
          "One number, <code>--clock-period</code>, produced five different "
          "microarchitectures with latencies 2, 4, 9, 12 and 18 cycles. In hand RTL each "
          "of those is a redesign; here each is a rebuild."),
         ("Pick the knee from the sweep rather than the tightest point.",
          "The best frequency is at 3&nbsp;ns, not at 1&nbsp;ns. Constraining harder past "
          "the knee adds registers that the fabric cannot exploit, so area rises and "
          "frequency falls.")]))

    s.append("""<p>Step three is where the structural advantage lives, and it is worth
    being precise about what it is. The tool is not out-scheduling a human. A human given
    a week could hand-pipeline this filter to 3&nbsp;ns and would probably land smaller
    than 386&nbsp;LC. The advantage is that the sweep above cost <b>four rebuilds and no
    design work</b>, so five architectures were evaluated instead of one. Hand RTL usually
    gets pipelined once, for one target, because re-pipelining is expensive and risky; it
    then stays that way when the target moves. The generated design is re-derived from the
    specification every time.</p>

    <p>That is the real claim, and it is narrower and more useful than &ldquo;HLS beats
    hand RTL.&rdquo; <b>Hand RTL beats HLS at a point you have already designed for. HLS
    beats hand RTL at a point you have not.</b> In a one-person design house, where nobody
    has a week to re-pipeline a block because a customer moved the clock from 75 to
    100&nbsp;MHz, the second case is the one that keeps happening.</p>""")

    s.append("<h2>Z15.6 Where this result stops being true</h2>")
    s.append("""<p>Stating the conditions under which a measurement flips is not a
    disclaimer; it is part of the measurement. This one flips under any of these:</p>""")

    s.append(tab("Invalidation conditions for Z15.4",
        ["Condition", "Why the result changes"],
        [["A different fabric",
          "iCE40 has no DSP blocks usable here, so constant multiplies became LUT "
          "shift-adds. On a device with hard multipliers the area picture changes "
          "completely."],
         ["Wider data or more taps",
          "At 4 taps the hand design is small enough for one person to hold in mind. The "
          "argument for HLS gets <i>stronger</i> with size, but this table does not prove "
          "that &mdash; it was not measured here."],
         ["A hand design with more than 3 stages",
          "The comparison is against a 3-stage hand pipeline. A 6-stage hand pipeline "
          "would likely beat the 3&nbsp;ns HLS point on both axes. What it would cost in "
          "engineer-days is not in the table."],
         ["A different HLS tool",
          "Bambu's scheduler is not Vitis HLS's. The pragma dialect result in Z15.1 "
          "guarantees the sources are not portable unchanged."]]))

    s.append("""<p>The last row is the one to plan around commercially. An IP built on one
    HLS tool's pragmas is tied to that tool. An IP built the way
    <code>edu/model/ipmodel.h</code> is built &mdash; portable C++, tool-specific settings
    on the command line &mdash; is not, and that portability is worth more than the few
    percent a vendor pragma might buy.</p>""")

    return "\n".join(s)
