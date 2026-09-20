# -*- coding: utf-8 -*-
"""Volume III, Part Z14 -- The C++ model layer: one source, two destinations."""
import sys, os, json
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, derive, sweep, num

MODEL = "/home/user/SE/edu/model"
잰것 = json.load(open(os.path.join(MODEL, "잰것.json"), encoding="utf-8"))


def _읽기(이름, 시작=None, 줄수=None):
    t = open(os.path.join(MODEL, 이름), encoding="utf-8").read().splitlines()
    if 시작 is not None:
        t = t[시작:시작 + (줄수 or 20)]
    return "\n".join(t)


def ch_cppmodel():
    s = ['<h1 id="z14">Z14. The C++ Model Layer &mdash; One Source, Two Destinations</h1>']

    s.append("""<p>Ask a working design house where its models live and you rarely hear
    &ldquo;SystemVerilog.&rdquo; You hear C or C++. The RTL is what you sell; the C++ is
    what tells you the RTL is right, and increasingly it is also what <em>generates</em>
    the RTL. This part builds that layer for real. Every file named here is in this
    repository, compiles with <code>g++</code>, and is exercised while this page
    renders.</p>""")

    s.append("<h2>Z14.1 Why the model is C++ and not Python</h2>")
    s.append("""<p>Earlier parts of this book used Python golden models (<code>zlib</code>
    for CRC-32, <code>gf.py</code> for the Galois field). That was right for those blocks:
    the model existed already, independently, which is the property that makes a golden
    model worth having. It stops being right the moment the model has to do two jobs:</p>""")

    s.append(tab("What the model layer has to do, and what language can do it",
        ["Job", "Python", "C++", "Why"],
        [["Be the verification reference", "yes", "yes",
          "Both express the algorithm exactly."],
         ["Run billions of vectors", "no", "yes",
          "Measured below: 144&nbsp;M evaluations/s in C++. CPython is ~1000&times; slower."],
         ["Be the HLS input", "no", "yes",
          "Every HLS tool in industry takes C, C++ or SystemC. None takes Python."],
         ["Be bit-accurate to the RTL", "awkward", "yes",
          "Python ints are arbitrary precision. Overflow and truncation must be "
          "simulated by hand; in C++ the fixed-width types do it."]]))

    s.append("""<p>The third row is the one that changes the architecture of the whole
    flow. If the model is also the HLS input, then the model and the RTL <em>cannot
    disagree</em>, because there is only one description:</p>""")

    s.append("""<figure><figcaption>One source, two destinations</figcaption>
<pre>
                    edu/model/fir.h          &lt;- 알고리즘은 여기에만 있다
                          |
            +-------------+-------------+
            |                           |
        g++ -O2                     bambu (HLS)
            |                           |
     equiv.cpp   vectors.cpp        fir_top.v
     (전수 등가성)  (골든 벡터)       (파는 물건)
            |                           |
            +-----------+---------------+
                        |
                   iverilog: 같은 벡터로 RTL 을 잰다
</pre></figure>""")

    s.append("""<p>The conventional flow has three descriptions &mdash; a Python model, a
    C++ HLS source and hand-written RTL &mdash; and therefore three chances to disagree.
    When they disagree, nobody knows which is right, because each was written from the
    spec by a different person on a different day. The structure above removes two of the
    three.</p>""")

    s.append("<h2>Z14.2 The shared header, and why it has no vendor types</h2>")
    s.append("""<p><code>edu/model/ipmodel.h</code> declares the fixed-point contract. It
    deliberately uses <code>int32_t</code> and hand-written saturation rather than
    <code>ap_fixed</code> or <code>hls::stream</code>. That was not a style choice; it was
    measured. Part&nbsp;Z15 gives the four one-variable controls that forced it.</p>""")

    s.append("<pre><code>" + E(_읽기("ipmodel.h", 55, 22)) + "</code></pre>")

    s.append("""<p>Two details in that code are worth the ink, because both are places
    where a model and an RTL silently part company.</p>""")

    s.append(derive("Why the shift is written as a shift and not a division",
        [("The RTL computes <code>acc[16:7]</code> &mdash; an arithmetic right shift by 7.",
          "That is what the hardware does; a shift is free, a divider is not."),
         ("In C, <code>acc / 128</code> rounds toward zero. <code>acc &gt;&gt; 7</code> "
          "rounds toward negative infinity.",
          "Integer division truncates toward zero by definition (C99 6.5.5); a shift "
          "discards low bits, which floors."),
         ("For <code>acc = -1</code>: division gives 0, shift gives &minus;1.",
          "&minus;1/128 = &minus;0.0078 truncates to 0; &minus;1 &gt;&gt; 7 = &minus;1."),
         ("So writing the model with division makes it disagree with the RTL on every "
          "negative value whose magnitude is below the shift amount.",
          "That is roughly half of all small negative accumulator values &mdash; common "
          "in an equaliser sitting near zero."),
         ("Therefore <code>asr()</code> is written as a shift, with the sign handled "
          "explicitly so it does not rely on implementation-defined behaviour.",
          "C++ left negative right-shift implementation-defined until C++20.")]))

    s.append("""<p>The second is saturation versus wrapping. A wrap turns a large positive
    accumulator into a large negative one, which drives the slicer to exactly the wrong
    decision; a saturate is still wrong but wrong in the same direction. The model
    saturates because the RTL saturates, and the RTL saturates because the specification
    says so. All three have to agree or the comparison is theatre.</p>""")

    s.append("<h2>Z14.3 Proving three architectures equal &mdash; by exhaustion</h2>")
    eq = 잰것["등가성"]
    s.append("""<p><code>fir.h</code> contains the same filter written three ways: the
    textbook form, a width-narrowed form, and a symmetry-folded form that uses two
    multipliers instead of four. They have to compute the same function. Most projects
    establish that by running a few thousand random vectors and declaring victory. Here
    the input space is four 8-bit samples, so it has exactly %s points &mdash; and that is
    small enough to check <em>all of them</em>.</p>""" % f"{eq['입력공간']:,}")

    s.append(tab("Exhaustive equivalence, measured",
        ["Quantity", "Value", "What it means"],
        [["Input space", f"{eq['입력공간']:,}", "256<sup>4</sup> &mdash; every possible input"],
         ["Wall time", f"{eq['초']:.1f} s", "g++ -O2, one core"],
         ["Rate", f"{eq['초당']:,}/s", "Each point evaluates all three variants"],
         ["Disagreements", str(eq["변형간_다름"]),
          "Not &ldquo;none found&rdquo; &mdash; <b>none exist</b>"],
         ["Distinct outputs", str(eq["출력값가지수"]),
          "All 256 output codes occur, so the check is not degenerate"]]))

    s.append("""<p>That last row is the gate this repository puts on every measurement. A
    comparison that only ever sees one output value has proved nothing, however many
    vectors it ran. <code>equiv.cpp</code> counts distinct outputs and exits non-zero if
    there are fewer than two &mdash; the same rule the RTL harness applies in
    Part&nbsp;Z1.</p>""")

    s.append("""<p>The word &ldquo;proof&rdquo; is used carefully. This is exhaustive over
    the <em>stated</em> input space, which is the combinational function of four samples.
    It says nothing about the sequential wrapper, the reset behaviour, or the handshake.
    Those need different arguments &mdash; and in Part&nbsp;Z15 one of them costs us a
    bug.</p>""")

    s.append("<h2>Z14.4 What verification time actually looks like</h2>")
    v = 잰것["검증속도"]
    s.append("""<p>&ldquo;C++ simulates a thousand times faster than RTL&rdquo; is repeated
    everywhere and is almost never measured by the person repeating it. Measuring it on
    this design produces a more useful answer than the folklore.</p>""")

    s.append(tab("Vectors per second, same algorithm, same machine",
        ["Path", "Vectors/s", "Relative", "What is included"],
        [["C++, compute only", f"{v['Cpp_순수계산_초당']:,}", f"{v['배율_순수계산']:,}&times;",
          "The arithmetic, nothing else (<code>equiv.cpp</code>)"],
         ["C++, formatted to a file", f"{v['Cpp_printf_벡터초']:,}", f"{v['배율_printf']}&times;",
          "Same arithmetic plus <code>printf</code> of five integers"],
         ["RTL, iverilog + vvp", f"{v['RTL_iverilog_벡터초']:,}", "1&times;",
          "Event-driven simulation of the synthesisable design"]]))

    s.append(ex("Where the speed advantage goes",
        given="C++ computes at %s/s but emits formatted vectors at only %s/s."
              % (f"{v['Cpp_순수계산_초당']:,}", f"{v['Cpp_printf_벡터초']:,}"),
        method="Divide. The ratio is the cost of text formatting relative to the "
               "algorithm itself.",
        numbers="%.0f&times;. Formatting five integers as decimal text costs about %.0f "
                "times more than computing the filter output."
                % (v['Cpp_순수계산_초당'] / v['Cpp_printf_벡터초'],
                   v['Cpp_순수계산_초당'] / v['Cpp_printf_벡터초']),
        trap="The obvious reading is &ldquo;file I/O is slow.&rdquo; It was measured and "
             "it is not: writing 200,000 vectors to a file ran at 5,110,455/s and "
             "discarding them to <code>/dev/null</code> ran at 5,398,353/s &mdash; a 5&nbsp;% "
             "difference. The cost is <code>printf</code>'s decimal conversion, not the "
             "disk. Replacing text with a binary buffer, or comparing in memory and never "
             "serialising at all, recovers the other 96&nbsp;%.",
        extra="The practical rule: a C++ reference that talks to the RTL through a text "
              "file throws away almost all of its speed advantage. Use the file for the "
              "few thousand vectors the RTL will actually run, and keep the billion-vector "
              "sweeps entirely inside C++."))

    s.append("""<p>So the honest version of the folklore is: the algorithm is about
    1,600&times; faster in C++, and a badly plumbed harness will give you 57&times;. Both
    are worth having; they buy different things. The 57&times; path is how you drive the
    RTL. The 1,600&times; path is how you settle the algorithm before any RTL exists
    &mdash; and that is where the schedule is actually won, because a bug found in the
    C++ costs minutes and the same bug found in a gate-level regression costs
    days.</p>""")

    s.append("<h2>Z14.5 Order of work, and what it saves</h2>")
    s.append(tab("Where each class of defect should die",
        ["Defect class", "Cheapest place to catch it", "Cost if it escapes to RTL"],
        [["Algorithm wrong (wrong formula, wrong rounding)", "C++, exhaustive or bulk",
          "Days &mdash; the RTL is right and the spec is wrong, which is the slowest kind "
          "of debug"],
         ["Overflow / width", "C++ with fixed-width types",
          "Weeks &mdash; appears as &ldquo;fails occasionally&rdquo;"],
         ["Handshake, reset, backpressure", "RTL only",
          "Cannot be found in C++; budget RTL time for exactly this"],
         ["Timing / area", "Synthesis and P&amp;R only",
          "Cannot be found in simulation at all"]]))

    s.append("""<p>The two lower rows are why HLS does not remove the need for RTL
    verification. It removes the top two rows, which are most of the defects by count, and
    leaves the bottom two, which are most of the defects by <em>difficulty</em>.
    Part&nbsp;Z15 hits one of the third-row defects within ten minutes of first running the
    generated RTL.</p>""")

    return "\n".join(s)
