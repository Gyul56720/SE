# -*- coding: utf-8 -*-
"""Volume I, Part X6 -- The FFT as a hardware block, worked.

The FFT is the most-implemented signal-processing block in existence and the one
most often implemented badly, because the algorithm is taught as an operation
count and built as a memory system.  This part computes both.
"""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def _f_bfly():
    b = []
    b += [line(30, 40, 150, 40, w=1.1), line(30, 100, 150, 100, w=1.1)]
    b += [line(30, 40, 150, 100, w=1.1), line(30, 100, 150, 40, w=1.1)]
    b += [f'<circle cx="150" cy="40" r="7" fill="#fff" stroke="#000" stroke-width="1"/>']
    b += [f'<circle cx="150" cy="100" r="7" fill="#fff" stroke="#000" stroke-width="1"/>']
    b += [txt(150, 44, "+", 10, "middle"), txt(150, 104, "&minus;", 10, "middle")]
    b += [f'<circle cx="96" cy="100" r="9" fill="#eef2f7" stroke="#000" stroke-width="1"/>']
    b += [txt(96, 104, "&times;", 9, "middle"), txt(96, 122, "W", 9, "middle"),
          txt(104, 126, "k", 7)]
    b += [txt(18, 44, "a", 10, "end"), txt(18, 104, "b", 10, "end")]
    b += [arr(157, 40, 196, 40), arr(157, 100, 196, 100)]
    b += [txt(204, 44, "a + W b", 10), txt(204, 104, "a &minus; W b", 10)]
    b += [txt(160, 156, "One radix-2 butterfly: one complex multiply, two complex adds.",
              9, "middle")]
    b += [txt(160, 172, "An N-point FFT is (N/2)log2 N of these, and the wiring between "
                        "them is the hard part.", 9, "middle", 'font-style="italic"')]
    return svg(330, 182, "".join(b))


def ch_fft():
    s = ['<h1 id="x6">X6. The FFT as a Hardware Block, Worked</h1>']
    s.append(fig(_f_bfly(), "The radix-2 decimation-in-time butterfly."))

    s.append("<h2>X6.1 The operation count, and why it is the wrong cost model</h2>")
    rows = []
    for N in (64, 256, 1024, 4096, 16384, 65536):
        dft = N * N
        r2 = (N // 2) * int(math.log2(N))
        r4 = (3 * N / 8) * (math.log2(N) / 2) * 2
        rows.append([num(N), num(dft), num(r2), num(int(dft / r2)),
                     num(int(r4)), num(N * int(math.log2(N)))])
    s.append(sweep("Complex multiplies for the DFT and for radix-2 / radix-4 FFTs",
        ["<i>N</i>", "DFT: <i>N</i><sup>2</sup>", "Radix-2: (<i>N</i>/2)log<sub>2</sub><i>N</i>",
         "Speed-up", "Radix-4 (approx.)", "Memory accesses &asymp; <i>N</i>log<sub>2</sub><i>N</i>"],
        rows,
        "The last column is the one that decides the architecture. Multiplies are cheap "
        "in a modern process; moving <i>N</i>log<sub>2</sub><i>N</i> complex words in and "
        "out of memory is not."))
    N = 4096
    s.append(ex("Multiplies are not the bottleneck &mdash; memory bandwidth is",
        f"A {N}-point complex FFT, 16-bit I and Q, to be completed in 10&nbsp;&micro;s. "
        "One multiplier can do 1 complex multiply per cycle at 500&nbsp;MHz; an SRAM port "
        "can do one 32-bit access per cycle at the same rate.",
        "Compute the two requirements separately and compare them with what one "
        "instance of each resource supplies.",
        [("Complex multiplies", num((N // 2) * int(math.log2(N)))),
         ("Multiplier-cycles available in 10&nbsp;&micro;s per multiplier", num(5000)),
         ("Multipliers needed", num(math.ceil((N // 2) * math.log2(N) / 5000))),
         ("Memory accesses (read 2, write 2 per butterfly)",
          num(4 * (N // 2) * int(math.log2(N)))),
         ("SRAM-port-cycles available per port", num(5000)),
         ("SRAM ports needed",
          num(math.ceil(4 * (N // 2) * math.log2(N) / 5000))),
         ("Ratio ports : multipliers",
          num(math.ceil(4 * (N // 2) * math.log2(N) / 5000) /
              math.ceil((N // 2) * math.log2(N) / 5000), 3))],
        "<b>By sizing the block from the multiply count, which is the number every "
        "textbook gives.</b> The memory requirement is four times larger and it is the "
        "one that will not be met by adding a cheap resource, because an SRAM with four "
        "times the ports is not four times the area &mdash; it is worse. The architectural "
        "answers are all about memory: in-place computation to halve the storage, "
        "multi-bank schemes so several butterflies read in parallel without conflict, and "
        "higher radix to do more arithmetic per memory visit. <b>Radix-4's real "
        "attraction is that it halves the number of memory passes</b>, not that it saves "
        "25&nbsp;% of the multiplies."))

    s.append("<h2>X6.2 Three architectures and where each belongs</h2>")
    s.append(tab("FFT architectures",
        ["Architecture", "Throughput", "Area", "Latency", "Where it belongs"],
        [["Single butterfly + memory", "1 butterfly / cycle",
          "smallest", "<i>N</i>log<sub>2</sub><i>N</i>/2 cycles",
          "Control-plane spectral analysis; anything not on the critical path"],
         ["<b>Pipelined (SDF / SDC)</b>", "<b>1 sample / cycle, streaming</b>",
          "log<sub>2</sub><i>N</i> butterflies + <i>N</i> words of delay",
          "&asymp;<i>N</i> cycles",
          "<b>OFDM receivers, channelisers &mdash; anything with a continuous stream</b>"],
         ["Parallel / SSR", "<i>P</i> samples / cycle",
          "<i>P</i>&times; the pipeline", "&lt; <i>N</i>/<i>P</i>",
          "When the sample rate exceeds the clock, which is the normal case above "
          "1&nbsp;GS/s"],
         ["Fully parallel (spatial)", "one transform / cycle",
          "<i>N</i>log<sub>2</sub><i>N</i>/2 butterflies", "log<sub>2</sub><i>N</i> stages",
          "Small <i>N</i> only; radar pulse compression, some optical DSP"]]))
    s.append("""<div class="ms"><b>Why the streaming architectures are named after their
    commutators rather than their butterflies.</b> Single-path delay feedback (SDF) and
    single-path delay commutator (SDC) differ in how the delay line is arranged around the
    butterfly, and that arrangement &mdash; not the arithmetic &mdash; determines the
    total memory, which is the dominant cost. An <i>N</i>-point radix-2 SDF pipeline needs
    exactly <i>N</i>&minus;1 words of delay in total, distributed as <i>N</i>/2,
    <i>N</i>/4, &hellip;, 1 across the stages. That geometric distribution is why the
    first stage's delay line is often a separate SRAM and the last few are registers: they
    are the same structure at wildly different sizes, and one implementation choice does
    not fit all of them. <b>An HLS-generated FFT that uses the same memory style
    throughout is leaving a large amount of area on the table</b>, and this is one of the
    clearest places where a hand-written IP block still beats a generated one.</div>""")
    rows = []
    for N in (64, 256, 1024, 4096, 16384):
        st = int(math.log2(N))
        rows.append([num(N), num(st), num(N - 1), num(st),
                     num(st * 3), num(N // 2)])
    s.append(sweep("Resources of a radix-2 SDF pipeline",
        ["<i>N</i>", "Stages", "Total delay words", "Butterflies",
         "Real multipliers (3-mult complex)", "Largest single delay line"], rows,
        "The last column is why the first stage dominates the floorplan."))

    s.append("<h2>X6.3 Fixed point in the FFT: scaling schedules</h2>")
    s.append("""<p>Each radix-2 stage can double the magnitude of the data. Over
    log<sub>2</sub><i>N</i> stages that is a growth of <i>N</i>, so a 4096-point transform
    can grow its input by 12 bits. Three strategies exist and they give measurably
    different results.</p>""")
    rng = np.random.default_rng(17)
    def fft_fixed(x, W, mode):
        """Radix-2 DIT FFT with a scaling schedule, fixed point."""
        n = x.size
        stages = int(math.log2(n))
        q = lambda v, F: np.round(v * (1 << F)) / (1 << F)
        # bit-reverse
        idx = np.array([int(f"{i:0{stages}b}"[::-1], 2) for i in range(n)])
        X = x[idx].astype(complex)
        F = W - 2
        X = q(X.real, F) + 1j * q(X.imag, F)
        for sgi in range(stages):
            m = 1 << (sgi + 1)
            w = np.exp(-2j * np.pi * np.arange(m // 2) / m)
            w = q(w.real, F) + 1j * q(w.imag, F)
            for k in range(0, n, m):
                a = X[k:k + m // 2]
                b = X[k + m // 2:k + m] * w
                b = q(b.real, F) + 1j * q(b.imag, F)
                X[k:k + m // 2] = a + b
                X[k + m // 2:k + m] = a - b
            if mode == "always":
                X = X / 2
            elif mode == "conditional" and np.abs(X).max() > 0.5:
                X = X / 2
            X = q(X.real, F) + 1j * q(X.imag, F)
        return X
    Nf = 256
    rows = []
    for name, mode in (("Scale every stage", "always"),
                       ("Conditional (block floating point)", "conditional"),
                       ("No scaling &mdash; grow the word", "never")):
        snrs, grow = [], []
        for trial in range(8):
            x = (rng.normal(0, 0.12, Nf) + 1j * rng.normal(0, 0.12, Nf))
            ref = np.fft.fft(x)
            if mode == "always":
                ref = ref / Nf
            got = fft_fixed(x, 16, mode)
            e = got - ref
            snrs.append(10 * math.log10(float((np.abs(ref) ** 2).mean() /
                                              max((np.abs(e) ** 2).mean(), 1e-30))))
            grow.append(float(np.abs(got).max()) / float(np.abs(x).max()))
        g = float(np.max(grow))
        rows.append([f"<b>{name}</b>", num(float(np.mean(snrs)), 4),
                     num(float(np.min(snrs)), 4), num(g, 3),
                     num(max(0.0, math.log2(g)), 3)])
    s.append(sweep(f"Measured SQNR and measured magnitude growth of a {Nf}-point 16-bit "
                   "FFT under three scaling schedules, 8 random trials each",
        ["Schedule", "Mean SQNR (dB)", "Worst SQNR (dB)",
         "Measured peak growth &times;", "Extra integer bits the growth demands"], rows,
        "The growth column is measured on a noise-like input, so it is far below the "
        "worst-case bound of <i>N</i>: a random input does not align in phase. "
        "<b>The measured figure is not a bound</b> &mdash; a single tone at a bin centre "
        "would reach the bound, and a design justified by this column alone would "
        "overflow on the first sine wave a customer applied. Unconditional scaling is "
        "safe and loses precision every stage. Block floating point recovers most of it "
        "at the cost of a magnitude detector and an exponent that must travel with the "
        "data &mdash; <b>and that exponent is an interface</b>, which a specification "
        "frequently forgets to mention."))
    s.append("""<div class="warn"><b>The block-floating-point exponent is part of the
    output.</b> A block that returns a mantissa array and keeps the exponent internal has
    returned meaningless numbers. This is a real and recurring integration bug: the FFT
    passes its own tests, in which the reference is scaled the same way, and fails in the
    system, where the next block assumes a fixed scale. <b>Any scaling that depends on the
    data must appear in the port list.</b></div>""")
    s.append(prob("An OFDM receiver uses a 2048-point FFT. The input is an ADC output "
                  "with 10 effective bits. How many bits should the FFT carry "
                  "internally, and why is &lsquo;10 + log<sub>2</sub>2048 = 21&rsquo; the "
                  "wrong answer?",
        "It is wrong in both directions. It is too pessimistic because the worst-case "
        "growth of <i>N</i> assumes every input conspires to align in phase at one output "
        "bin; for a noise-like OFDM signal the growth is closer to &radic;<i>N</i>, about "
        "5.5 bits, and unconditional scaling by 2 per stage over-attenuates such a signal "
        "by the same factor. It is too optimistic because it accounts only for range and "
        "not for the <i>accumulated quantisation noise</i> of the twiddle multiplies, "
        "which adds roughly half a bit per stage of precision loss. The correct procedure "
        "is Part&nbsp;X1's: state the end-to-end metric (for OFDM, the EVM the "
        "constellation demands), then sweep the internal word length against that metric "
        "and read off the knee. <b>The answer is a measurement, and it depends on the "
        "signal statistics, which is why an FFT IP block's datasheet must state the input "
        "statistics its SQNR figure was measured with.</b>"))

    s.append("<h2>X6.4 Twiddle factors: the quiet memory</h2>")
    rows = []
    for N in (256, 1024, 4096, 16384, 65536):
        full = N // 2
        octant = N // 8 + 1
        rows.append([num(N), num(full), num(full * 32 / 8 / 1024, 3),
                     num(octant), num(octant * 32 / 8 / 1024, 3),
                     num(full / octant, 3)])
    s.append(sweep("Twiddle-factor ROM: full table vs. one-eighth with symmetry, "
                   "16-bit I and Q",
        ["<i>N</i>", "Full entries", "Full ROM (kB)", "&frac18; entries",
         "&frac18; ROM (kB)", "Saving"], rows,
        "The eighth-table exploits the symmetries of the unit circle; recovering the "
        "other seven octants costs a few multiplexers and a conditional negate and swap. "
        "For <i>N</i>&nbsp;=&nbsp;65&#8239;536 the difference is between a ROM that fits "
        "on a corner of the block and one that dominates it."))
    s.append("""<div class="bs"><b>The symmetries, so the multiplexer logic makes
    sense.</b> <i>W</i><sub><i>N</i></sub><sup><i>k</i></sup> =
    e<sup>&minus;2&pi;i<i>k</i>/<i>N</i></sup> traces the unit circle clockwise. Cosine is
    even and sine is odd about the real axis, giving the lower half from the upper half;
    the quarter-turn identity exchanges sine and cosine, giving the second quadrant from
    the first; and the eighth-turn identity does the same within a quadrant. So the ROM
    stores angles from 0 to &pi;/4 and the address decoder computes three bits &mdash;
    which octant &mdash; that control a swap of the I and Q outputs and two sign
    inversions. The whole recovery is combinational and adds perhaps two gate delays,
    against a ROM eight times smaller.</div>""")
    s.append(prob("Instead of a ROM, twiddles can be generated by a CORDIC rotator or by "
                  "a recursive oscillator <i>w</i>[<i>n</i>+1] = <i>w</i>[<i>n</i>] "
                  "&middot; <i>W</i>. When is each appropriate?",
        "The recursive oscillator is the cheapest &mdash; one complex multiply per "
        "twiddle &mdash; and is <b>unusable in a fixed-point pipeline</b> because it is a "
        "marginally stable recursion: quantisation error accumulates in both magnitude "
        "and phase, and over the thousands of twiddles of a large transform the magnitude "
        "drifts away from unity. It is acceptable only with periodic re-seeding from a "
        "small ROM, which is a hybrid rather than a replacement. CORDIC is exact to its "
        "iteration count and costs only shifts and adds, making it attractive in FPGA "
        "fabric where multipliers are a scarce hard resource but LUTs are plentiful; it "
        "costs latency, which a pipelined design can absorb. <b>The ROM wins in ASIC</b>, "
        "where a small compiled ROM is dense and the alternative spends timing budget. "
        "As so often, the right answer is set by which resource the target technology "
        "makes expensive, not by any property of the algorithm."))
    return "\n".join(s)
