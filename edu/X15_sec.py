# -*- coding: utf-8 -*-
"""Volume I, Part X15 -- Hardware security, worked."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_hwsec():
    s = ['<h1 id="x15">X15. Hardware Security, Worked</h1>']
    s.append("""<p>Security is where a plausible-looking design is most often wrong,
    because the adversary is not a random input but a person who reads your datasheet.
    This part covers the parts of hardware security that are arithmetic &mdash; how many
    traces an attack needs, how much entropy a source really has, how long a key survives
    &mdash; because those are the parts a designer can actually bound.</p>""")

    s.append("<h2>X15.1 Side channels: the attack is a statistics problem</h2>")
    s.append(derive("Why correlation power analysis works, and how many traces it needs", [
        ("Dynamic power depends on the number of bits that switch, which depends on the "
         "data being processed.",
         "Part X7's &alpha;<i>CV</i><sup>2</sup><i>f</i>: &alpha; is data dependent."),
        ("Choose an intermediate value <i>v</i> = <i>f</i>(plaintext, key guess) that "
         "the device computes, e.g. an AES S-box output.",
         "It must depend on a small part of the key so the guesses can be enumerated."),
        ("Predict the leakage as a model, commonly the Hamming weight of <i>v</i>.",
         "A crude model that works because switching count correlates with it."),
        ("Correlate the predicted leakage with the measured power across many traces, "
         "for every key guess.",
         "The correct guess correlates; the others do not, because their predicted "
         "values are effectively random with respect to the device's actual "
         "computation."),
        ("The number of traces needed is <i>n</i> &asymp; "
         "3 + 8(<i>Z</i><sub>&alpha;</sub>/ln((1+&rho;)/(1&minus;&rho;)))<sup>2</sup>.",
         "Fisher's z-transform of the correlation coefficient. <b>Quadratic in "
         "1/&rho;</b>, which is why reducing the signal by a factor of ten costs the "
         "attacker a factor of a hundred in traces."),
    ]))
    rows = []
    Z = 4.0
    for rho in (0.5, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005):
        n = 3 + 8 * (Z / math.log((1 + rho) / (1 - rho))) ** 2
        rows.append([num(rho, 3), num(int(n)),
                     num(n / (3 + 8 * (Z / math.log(1.5 / 0.5)) ** 2), 4),
                     num(n * 1e-3 / 3600, 3)])
    s.append(sweep("Traces needed for a correlation attack against the leakage "
                   "correlation &rho; (99.99&nbsp;% confidence)",
        ["&rho;", "Traces needed", "Relative to &rho; = 0.5",
         "Acquisition hours at 1&nbsp;ms per trace"], rows,
        "Computed from the z-transform expression. <b>Read the last column as the "
        "security margin</b>: an unprotected implementation falls in minutes, and each "
        "factor of ten in leakage reduction costs the attacker a factor of a hundred in "
        "time. A countermeasure does not have to be perfect, it has to move this "
        "column past the value of the key."))
    s.append(tab("Countermeasures, what each does to &rho;, and what it costs",
        ["Countermeasure", "Mechanism", "Effect", "Cost"],
        [["<b>Masking</b>", "Split each secret into shares whose individual "
          "distributions are independent of the secret",
          "<b>Removes first-order leakage entirely</b>; the attacker must combine "
          "<i>d</i>+1 points, and the trace count grows exponentially in <i>d</i>",
          "2&ndash;4&times; area and a source of fresh randomness every cycle"],
         ["Hiding (dual rail, WDDL)", "Make switching activity constant",
          "Reduces &rho;, does not remove it &mdash; routing imbalance leaks",
          "2&times; area, careful layout"],
         ["Shuffling", "Randomise the order of independent operations",
          "Divides &rho; by roughly the number of permuted slots",
          "Cheap; combines well with masking"],
         ["Noise injection", "Add uncorrelated activity",
          "Reduces &rho; by the amplitude ratio",
          "Power; <b>attacker averages it away &mdash; buys time, not security</b>"],
         ["Frequency randomisation", "Jitter the clock",
          "Misaligns traces; defeated by alignment preprocessing",
          "Cheap and weak on its own"],
         ["Key refresh", "Limit the traces available per key",
          "<b>Caps the attack directly</b>", "Protocol support"]]))
    s.append("""<div class="warn"><b>A masked implementation that is not verified at the
    gate level is usually not masked.</b> Masking is a property of the <i>computation</i>,
    and synthesis optimises computations. If the tool finds that two shares are combined
    in a common subexpression &mdash; which is exactly the kind of optimisation it is good
    at &mdash; the shares meet in one gate and the first-order leakage returns, while the
    RTL still looks masked. There is a second, subtler failure: even without optimisation,
    a <b>glitch</b> in combinational logic can momentarily present a function of both
    shares, which is why threshold implementations are designed to be glitch-resistant by
    construction rather than merely share-correct. <b>The verification here is formal
    leakage analysis on the netlist</b>, not inspection of the source.</div>""")

    s.append("<h2>X15.2 Entropy: counting what a random number generator really has</h2>")
    s.append(ex("A ring-oscillator TRNG, entropy per bit",
        "Two free-running ring oscillators, one sampled by the other. Jitter "
        "accumulates over the sampling interval; the accumulated timing uncertainty is "
        "&sigma;&nbsp;=&nbsp;12&nbsp;ps and the sampled oscillator's period is "
        "<i>T</i>&nbsp;=&nbsp;400&nbsp;ps.",
        "The min-entropy of the sampled bit depends on how much of a period the "
        "uncertainty spans. A standard stochastic-model estimate is "
        "<i>H</i> &asymp; 1 &minus; (4/&pi;<sup>2</sup>)"
        "e<sup>&minus;4&pi;<sup>2</sup>&sigma;<sup>2</sup>/<i>T</i><sup>2</sup></sup>, "
        "which goes to 1 when the jitter covers a period and to 0 when it is small.",
        [("&sigma;/<i>T</i>", num(12 / 400, 4)),
         ("Exponent argument",
          num(4 * math.pi ** 2 * (12 / 400) ** 2, 4)),
         ("Estimated entropy per raw bit",
          num(1 - (4 / math.pi ** 2) * math.exp(-4 * math.pi ** 2 * (12 / 400) ** 2), 4)),
         ("Raw bits needed per full-entropy bit",
          num(1 / (1 - (4 / math.pi ** 2) *
                   math.exp(-4 * math.pi ** 2 * (12 / 400) ** 2)), 4)),
         ("If &sigma; falls to 3&nbsp;ps (a quieter supply): entropy",
          num(1 - (4 / math.pi ** 2) * math.exp(-4 * math.pi ** 2 * (3 / 400) ** 2), 4)),
         ("Raw bits per full-entropy bit then",
          num(1 / max(1e-9, 1 - (4 / math.pi ** 2) *
                      math.exp(-4 * math.pi ** 2 * (3 / 400) ** 2)), 4))],
        "<b>By testing the output of the conditioner instead of the source.</b> A "
        "cryptographic hash applied to a biased source produces output that passes every "
        "statistical test &mdash; that is what a hash does &mdash; while containing only "
        "as much entropy as went in. <b>The test must be applied to the raw source</b>, "
        "with an online health test that keeps checking it in the field, because the "
        "quantity being relied on (&sigma;) depends on supply noise, temperature and "
        "ageing, and an attacker with access to the supply can reduce it deliberately. "
        "The second row from the bottom is that attack expressed as arithmetic."))
    s.append("""<div class="ms"><b>Why the standards insist on min-entropy rather than
    Shannon entropy.</b> Shannon entropy is an average; an adversary guesses the most
    likely value. A source that emits 0 with probability 0.9 has Shannon entropy 0.47 bits
    and min-entropy &minus;log<sub>2</sub>(0.9)&nbsp;=&nbsp;0.15 bits, and the second
    number is the one that bounds an attacker's success. For a key of <i>k</i> bits
    assembled from such a source, the attacker's work is 2 raised to the total
    <i>min</i>-entropy, not the total Shannon entropy &mdash; a factor of 2<sup>0.32</sup>
    per bit, which over 256 bits is a factor of 10<sup>24</sup>. <b>Using the wrong
    entropy measure is not conservative rounding, it is a wrong security
    claim.</b></div>""")

    s.append("<h2>X15.3 Fault attacks and the cost of detection</h2>")
    rows = []
    for name, scheme, det, cost in (
            ("None", "&mdash;", "0&nbsp;%", "0&nbsp;%"),
            ("Parity on registers", "1 bit per word", "single-bit faults", "3&ndash;12&nbsp;%"),
            ("Duplication", "Run twice, compare", "any single fault", "&gt;100&nbsp;%"),
            ("Time redundancy", "Run twice in sequence", "transient faults only",
             "0&nbsp;% area, 100&nbsp;% time"),
            ("Inverse check", "Decrypt the ciphertext and compare",
             "any fault in the datapath", "~100&nbsp;% time"),
            ("Infective computation", "Spread the fault so the output is useless",
             "prevents exploitation rather than detecting", "moderate")):
        rows.append([f"<b>{name}</b>", scheme, det, cost])
    s.append(sweep("Fault-attack countermeasures",
        ["Countermeasure", "Mechanism", "Catches", "Overhead"], rows,
        "The classic differential fault attack on RSA-CRT recovers the private key from "
        "<b>one</b> faulty signature, which is why the inverse check &mdash; verify the "
        "signature before releasing it &mdash; is standard there despite its cost. "
        "<b>When one fault is enough, probabilistic countermeasures are not.</b>"))
    s.append(prob("A customer asks for a &lsquo;secure&rsquo; AES block. What do you ask "
                  "them before quoting?",
        "Four questions, because &lsquo;secure&rsquo; alone does not specify anything. "
        "<b>What is the attacker's physical access?</b> A block in a server that an "
        "attacker cannot touch needs no side-channel countermeasures; a smart card that "
        "the attacker owns needs every one of them, and the area difference is a factor "
        "of three. <b>How many operations per key?</b> This bounds the traces available "
        "and therefore the required leakage reduction directly, via the table in X15.1. "
        "<b>What certification is required?</b> Common Criteria or FIPS levels prescribe "
        "specific countermeasures and specific evidence, and the evidence costs more than "
        "the design. <b>What is the throughput and latency requirement?</b> Masking costs "
        "randomness per cycle, and a design that must run at line rate may not be able to "
        "afford the randomness generation. <b>A quote given without these answers will "
        "be wrong by a large factor in one direction or the other</b>, and a vendor who "
        "asks them is demonstrating exactly the competence being bought."))
    s.append(prob("Why is a hardware root of trust harder than storing a key in fuses?",
        "Because the key is the easy part. A root of trust must establish, at every boot, "
        "that the first code to run is the code the owner intended &mdash; which requires "
        "immutable boot code, a verified signature chain, and protection of the "
        "verification itself from the fault and side-channel attacks above. It must "
        "survive the states nobody designs for: reset during an update, a power glitch "
        "mid-verification, a debug interface left enabled. It needs a way to revoke a "
        "compromised key and to roll forward a version counter that cannot be rolled "
        "back, which means monotonic storage, which means more fuses and a policy for "
        "them. And it must do all this while remaining <b>debuggable in the field by the "
        "legitimate owner</b>, which is the requirement that quietly reopens every door "
        "the rest closed. <b>The key in fuses is perhaps five per cent of the work</b>; "
        "the rest is the state machine around it, and that state machine is where the "
        "published attacks land."))
    return "\n".join(s)
