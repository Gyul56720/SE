# -*- coding: utf-8 -*-
"""Volume I, Part X9 -- Computer arithmetic beyond the adder, worked."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_arith2():
    s = ['<h1 id="x9">X9. Computer Arithmetic Beyond the Adder, Worked</h1>']
    s.append("""<p>Addition and multiplication are solved problems with known structures.
    Division, square root, and the transcendental functions are not: each admits several
    algorithms with genuinely different latency, area and accuracy, and choosing among
    them is a recurring task for anyone specifying a datapath. This part computes the
    trade-offs instead of listing them.</p>""")

    s.append("<h2>X9.1 Adders: the latency&ndash;area curve, computed</h2>")
    rows = []
    for n in (8, 16, 32, 64, 128):
        rows.append([num(n), num(n), num(int(math.ceil(math.log2(n))) * 2 + 2,),
                     num(int(n * math.log2(n) / 2)),
                     num(int(2 * math.sqrt(n))), num(int(2 * n))])
    s.append(sweep("Adder structures: delay in gate levels and area in full-adder "
                   "equivalents",
        ["Width <i>n</i>", "Ripple delay", "Kogge&ndash;Stone delay",
         "Kogge&ndash;Stone area", "Carry-select delay (&radic;<i>n</i> blocks)",
         "Carry-select area"], rows,
        "Delays are counted in two-input gate levels from the standard prefix "
        "constructions; they are architectural counts, not library timing. "
        "<b>Kogge&ndash;Stone is logarithmic in delay and <i>n</i>log<i>n</i> in area and "
        "wiring</b> &mdash; and the wiring, not the gates, is what makes it expensive in "
        "a real floorplan."))
    s.append("""<div class="ms"><b>Why the prefix-adder family is a design space rather
    than a single answer.</b> Every parallel-prefix adder computes the same carry
    prefixes; they differ in how the prefix tree is shaped, and the shape trades three
    quantities against each other: logic depth, fan-out, and wiring tracks.
    Kogge&ndash;Stone minimises depth at maximum wire count; Brent&ndash;Kung minimises
    wires at twice the depth; Han&ndash;Carlson interleaves the two and sits between;
    Ladner&ndash;Fischer trades fan-out for wires. In a modern process <b>the wiring term
    usually dominates</b>, so the textbook's favourite (Kogge&ndash;Stone) is often not
    the synthesiser's choice, and a designer who insists on it by instantiation can make
    the block slower. The right procedure is to let the tool choose from its library and
    to check the result, not to specify the topology in the RTL.</div>""")

    s.append("<h2>X9.2 Multipliers: partial products and how to not add them</h2>")
    rows = []
    for n in (8, 16, 24, 32, 53):
        pp_simple = n
        pp_booth2 = math.ceil(n / 2) + 1
        pp_booth3 = math.ceil(n / 3) + 1
        wallace_depth = 0
        k = pp_booth2
        while k > 2:
            k = (k // 3) * 2 + k % 3
            wallace_depth += 1
        rows.append([num(n), num(pp_simple), num(pp_booth2), num(pp_booth3),
                     num(wallace_depth), num(int(pp_booth2 * n * 0.6))])
    s.append(sweep("Partial-product counts and reduction depth",
        ["Operand width <i>n</i>", "Simple PP rows", "Radix-4 Booth rows",
         "Radix-8 Booth rows", "Wallace 3:2 reduction levels (from radix-4)",
         "Approx. full adders in the tree"], rows,
        "Radix-8 Booth needs a 3&times; multiple, which costs an adder and a carry "
        "chain up front; it pays only when the row saving outweighs that, which for "
        "<i>n</i>&nbsp;&ge;&nbsp;32 it usually does. The 53 row is the IEEE-754 "
        "double-precision significand."))
    s.append(ex("Why a multiplier ends in one wide adder",
        "A 32&times;32 multiplier built as radix-4 Booth encoding plus a "
        "carry-save reduction tree.",
        "Count the stages and see where the delay goes. Carry-save addition has "
        "<i>constant</i> delay per level regardless of width, because no carry "
        "propagates; only the final conversion from carry-save to binary needs a "
        "carry-propagate adder.",
        [("Booth rows", num(17)),
         ("Reduction levels to reach 2 rows", num(6)),
         ("Delay of the tree (&asymp;2 gate levels per level)", num(12) + " gate levels"),
         ("Final 64-bit carry-propagate adder (Kogge&ndash;Stone)",
          num(int(math.ceil(math.log2(64))) * 2 + 2) + " gate levels"),
         ("Final adder as a fraction of total delay",
          num((math.ceil(math.log2(64)) * 2 + 2) /
              (12 + math.ceil(math.log2(64)) * 2 + 2) * 100, 3, "%"))],
        "<b>By optimising the reduction tree and leaving the final adder to the "
        "synthesiser's default.</b> The final adder is a third of the delay of the whole "
        "multiplier, and it is the one part that is a plain carry-propagate problem. "
        "It is also the reason <b>a multiply-accumulate is cheaper than a multiply "
        "followed by an add</b>: keep the product in carry-save form, feed it into the "
        "accumulator's reduction tree, and pay for exactly one carry-propagate adder at "
        "the end of the whole accumulation rather than one per operation. Any datapath "
        "that multiplies and then sums should be examined for this."))

    s.append("<h2>X9.3 Division and square root: digit recurrence against Newton</h2>")
    s.append(tab("Two families, and what each is for",
        ["", "Digit recurrence (SRT)", "Multiplicative (Newton&ndash;Raphson, "
         "Goldschmidt)"],
        [["Produces", "One radix-<i>r</i> digit per iteration",
          "Doubles the number of correct bits per iteration"],
         ["Iterations for 53 bits", "27 at radix 4", "About 4 from an 8-bit seed"],
         ["Per-iteration cost", "A small adder and a quotient-digit selection table",
          "<b>Two full multiplies</b>"],
         ["Exact remainder", "<b>Yes &mdash; available for free</b>",
          "No; needs a final correction step"],
         ["Correct rounding", "Straightforward from the remainder",
          "<b>Requires care</b>; this is where implementations go wrong"],
         ["Latency", "Long, predictable", "Short if multipliers are already there"],
         ["Reuses", "Nothing", "The existing multiplier array"],
         ["Chosen when", "Area matters, or the remainder is needed (integer division, "
          "modulo)", "A fast multiplier already exists (every FPU)"]]))
    s.append("""<div class="warn"><b>The Pentium FDIV bug was a digit-selection table with
    five missing entries.</b> An SRT divider chooses each quotient digit from a lookup
    indexed by truncated partial remainder and divisor; the table has redundant regions so
    that a slightly wrong estimate can be corrected later, which is exactly what makes the
    algorithm fast and exactly what makes a missing entry hard to find by random testing.
    The entries were unreachable for almost all operand pairs. The lesson for a
    verification plan is specific and permanent: <b>a table-driven arithmetic unit must be
    verified over the table's index space, not over the operand space.</b> Random operands
    reach the interesting table entries with probability near zero; enumerating the index
    space takes minutes.</div>""")
    rows = []
    for bits in (24, 53, 113):
        for seed in (8, 12, 16):
            it = 0
            b = seed
            while b < bits:
                b *= 2
                it += 1
            rows.append([num(bits), num(seed), num(it), num(2 * it),
                         num(math.ceil(bits / 2)), num(math.ceil(bits / 3))])
    s.append(sweep("Iteration counts: Newton&ndash;Raphson against SRT",
        ["Result bits", "Seed table bits", "Newton iterations", "Multiplies",
         "SRT radix-4 iterations", "SRT radix-8 iterations"], rows,
        "Newton's iteration count is logarithmic in the precision and the seed table's "
        "size trades directly against it &mdash; four extra table bits routinely remove "
        "an entire iteration, which is two multiplies. <b>This is the cheapest "
        "optimisation in the whole unit</b> and is frequently left on the table."))
    s.append(prob("A block needs <i>y</i> = <i>a</i>/<i>b</i> where <i>b</i> changes "
                  "rarely and <i>a</i> changes every cycle. What is the right structure?",
        "Not a divider. Compute <i>r</i>&nbsp;=&nbsp;1/<i>b</i> once, when <i>b</i> "
        "changes, and multiply every cycle. The reciprocal can take as long as it likes "
        "&mdash; a slow iterative unit, or even a microcoded sequence &mdash; because it "
        "is off the critical path, and the per-cycle cost collapses to one multiply. "
        "<b>The general principle is worth naming: look for the operand that changes "
        "slowly and move work onto it.</b> The same observation produces the "
        "coefficient-folding in a fixed-coefficient FIR, the precomputed tables in a "
        "modular-arithmetic unit, and the slow adaptation loop of a SerDes equaliser. "
        "The one caution is accuracy: <i>a</i>&nbsp;&middot;&nbsp;(1/<i>b</i>) is not "
        "correctly rounded even when both operations are, so a unit claiming IEEE "
        "compliance cannot take this shortcut without a correction step."))

    s.append("<h2>X9.4 CORDIC: rotations without multipliers</h2>")
    s.append(derive("Why the strange constants work", [
        ("A rotation by &theta; is (<i>x</i>cos&theta; &minus; <i>y</i>sin&theta;, "
         "<i>x</i>sin&theta; + <i>y</i>cos&theta;).",
         "Definition."),
        ("Factor out cos&theta;: the rotation becomes cos&theta; times a shear with "
         "tan&theta;.",
         "Algebra. The scale factor is now separate from the shape."),
        ("Choose &theta;<sub><i>i</i></sub> with tan&theta;<sub><i>i</i></sub> = "
         "2<sup>&minus;<i>i</i></sup>. Then the shear is two shifts and two adds.",
         "<b>This is the whole trick</b>: restrict the allowed angles so the "
         "multiplication becomes a shift."),
        ("Any angle in the convergence range is reachable as "
         "&Sigma;&plusmn;&theta;<sub><i>i</i></sub>.",
         "Because &theta;<sub><i>i</i></sub> &lt; &Sigma;<sub><i>j</i>&gt;<i>i</i></sub>"
         "&theta;<sub><i>j</i></sub>, so the remaining steps can always correct an "
         "overshoot &mdash; the same redundancy argument that makes SRT division work."),
        ("The accumulated scale &Pi;cos&theta;<sub><i>i</i></sub> &rarr; 0.607253 is "
         "<b>independent of the angle</b>, because every step rotates by the same "
         "magnitude and only the sign varies.",
         "So it can be compensated once, at the end, or folded into surrounding "
         "coefficients for free."),
    ]))
    K = 1.0
    rows = []
    for nit in (8, 12, 16, 20, 24):
        K = 1.0
        for i in range(nit):
            K *= 1 / math.sqrt(1 + 4.0 ** -i)
        # measured accuracy
        errs = []
        for th in np.linspace(-0.9, 0.9, 41):
            x, y, z = 1.0, 0.0, th
            for i in range(nit):
                d = 1.0 if z >= 0 else -1.0
                x, y = x - d * y * 2.0 ** -i, y + d * x * 2.0 ** -i
                z -= d * math.atan(2.0 ** -i)
            errs.append(abs(x * K - math.cos(th)))
        rows.append([num(nit), num(K, 8), num(float(np.max(errs)), 3),
                     num(-math.log2(max(float(np.max(errs)), 1e-30)), 3),
                     num(nit * 2)])
    s.append(sweep("Measured CORDIC accuracy against iteration count "
                   "(rotation mode, 41 angles)",
        ["Iterations", "Scale factor <i>K</i>", "Max |error| in cos",
         "Effective bits", "Adds"], rows,
        "One bit of accuracy per iteration, exactly as the theory predicts, and the "
        "scale factor converges quickly to its limit. The last column is the cost: "
        "two adds and two shifts per iteration and no multiplier anywhere."))
    s.append("""<div class="bs"><b>The three CORDIC modes, and what each computes.</b> In
    <i>rotation</i> mode the algorithm drives the angle accumulator to zero and the
    coordinates come out rotated &mdash; giving sine and cosine, and the complex rotation
    a mixer or an FFT twiddle needs. In <i>vectoring</i> mode it drives <i>y</i> to zero
    instead, and what accumulates is the original angle &mdash; giving arctangent and
    magnitude, which is exactly the operation a Cartesian-to-polar conversion, an AM
    detector or a phase detector performs. Substituting hyperbolic angles
    (tanh&nbsp;instead of tan) gives a third mode that computes exponentials, logarithms
    and square roots, with some iterations repeated to preserve convergence. <b>One
    structure, three modes, most of the transcendental functions a DSP block needs</b>
    &mdash; which is why CORDIC survives in fabric where multipliers are the scarce
    resource.</div>""")

    s.append("<h2>X9.5 Floating point: what the standard actually requires</h2>")
    rows = []
    for name, ew, mw in (("binary16 (half)", 5, 10), ("bfloat16", 8, 7),
                         ("binary32 (single)", 8, 23), ("TF32", 8, 10),
                         ("binary64 (double)", 11, 52), ("FP8 E4M3", 4, 3),
                         ("FP8 E5M2", 5, 2)):
        bias = 2 ** (ew - 1) - 1
        emax = 2 ** ew - 2 - bias
        emin = 1 - bias
        eps = 2.0 ** -(mw + 1)
        rows.append([name, num(1 + ew + mw), num(ew), num(mw),
                     num(mw + 1), num(eps, 3),
                     num(-math.log10(2.0 ** -(mw + 1)), 3)])
    s.append(sweep("Floating-point formats in current use",
        ["Format", "Total bits", "Exponent bits", "Stored mantissa bits",
         "Significand bits (with hidden 1)", "Machine epsilon", "Decimal digits"], rows,
        "bfloat16 and binary16 are the same width and differ entirely in how they split "
        "it: bfloat16 keeps binary32's exponent range and throws away precision, which "
        "is the right trade for neural-network training because the failure mode there "
        "is overflow of a gradient, not rounding of a weight."))
    s.append(ex("Why 0.1 + 0.2 &ne; 0.3, in bits",
        "IEEE-754 binary64 arithmetic.",
        "0.1 and 0.2 are not representable: in binary they are infinite repeating "
        "fractions, so each is rounded to 53 significant bits. The sum of the two "
        "rounded values is then itself rounded. Print the exact decimal expansions.",
        [("0.1 stored as", f"{0.1:.20f}"),
         ("0.2 stored as", f"{0.2:.20f}"),
         ("0.1 + 0.2 =", f"{0.1 + 0.2:.20f}"),
         ("0.3 stored as", f"{0.3:.20f}"),
         ("Difference", num(abs((0.1 + 0.2) - 0.3), 3)),
         ("Difference in units in the last place",
          num(abs((0.1 + 0.2) - 0.3) / 2.0 ** -54, 3))],
        "<b>By concluding that floating point is unreliable.</b> It is exactly reliable: "
        "every operation above returned the correctly rounded result, and the standard "
        "guarantees that. What is unreliable is the assumption that decimal literals are "
        "representable. The consequences for hardware verification are direct: a "
        "bit-exact comparison against a reference model is only meaningful if both use "
        "the same rounding mode and the same order of operations, <b>and floating-point "
        "addition is not associative</b>, so a reference model that sums an array in a "
        "different order than the RTL will disagree with it while both are correct. "
        "Specify the summation order, or specify a tolerance and justify it."))
    s.append(prob("A neural-network accelerator uses bfloat16 multipliers with binary32 "
                  "accumulation. Why not accumulate in bfloat16 too?",
        "Because accumulation is where precision is lost and multiplication is not. A "
        "bfloat16 multiply of two 8-bit significands produces a 16-bit exact product, "
        "and rounding it back to 8 bits costs one rounding. Summing <i>N</i> such "
        "products in bfloat16 costs <i>N</i> roundings, each of half an LSB of a number "
        "with only 8 significand bits, and &mdash; worse &mdash; once the running sum is "
        "2<sup>8</sup> times larger than the next term, that term is <b>absorbed "
        "entirely</b> and contributes nothing. For <i>N</i> in the hundreds or thousands, "
        "which a convolution reduction routinely is, the sum silently stops growing. "
        "Binary32 accumulation has 24 significand bits and pushes the absorption "
        "threshold out by 2<sup>16</sup>. <b>The general rule is that a reduction needs "
        "more precision than its operands</b>, which is why every practical mixed-"
        "precision unit, from a DSP MAC to a tensor core, is asymmetric in exactly this "
        "way."))
    return "\n".join(s)
