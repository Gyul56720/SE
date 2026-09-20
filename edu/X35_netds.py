# -*- coding: utf-8 -*-
"""Volume I, Part X35 -- Hardware data structures: CAM, hashing, Bloom filters."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_hwds():
    s = ['<h1 id="x35">X35. Hardware Data Structures: CAM, Hashing and Bloom '
         'Filters</h1>']
    s.append("""<p>Networking, storage and security IP spend most of their logic looking
    things up. The structures that do it are a small, well-understood family with sharply
    different cost profiles, and choosing among them is one of the clearest cases in this
    book where an architectural decision is settled by arithmetic rather than by
    preference.</p>""")

    s.append("<h2>X35.1 The lookup family</h2>")
    s.append(tab("Lookup structures compared",
        ["Structure", "Query", "Area per entry", "Power", "Updates", "Used for"],
        [["RAM (direct index)", "1 cycle", "1 bit/bit", "Low", "1 cycle",
          "Small, dense key spaces"],
         ["<b>Binary CAM</b>", "<b>1 cycle, all entries in parallel</b>",
          "<b>~8&ndash;10 transistors per bit</b>",
          "<b>Very high &mdash; every cell compares every cycle</b>", "1 cycle",
          "MAC address tables, tag matching"],
         ["<b>Ternary CAM</b>", "1 cycle, with don't-cares",
          "<b>~16 transistors per bit</b>", "<b>Higher still</b>",
          "Needs priority ordering &mdash; <b>insertion can require moving entries</b>",
          "<b>Longest-prefix routing, ACLs</b>"],
         ["Hash table", "1&ndash;2 cycles typical", "~1 bit/bit plus load factor",
          "Low", "1 cycle, except on collision",
          "Flow tables, caches"],
         ["<b>Cuckoo hash</b>", "<b><i>d</i> parallel probes, worst case bounded</b>",
          "~1.05 bits/bit at high load", "Low",
          "<b>Insertion can cascade</b>", "<b>Flow tables where a bounded query time "
          "is required</b>"],
         ["Trie / tree", "log <i>n</i> memory accesses", "Pointer overhead",
          "Low", "Simple", "Prefix matching in software"],
         ["<b>Bloom filter</b>", "<i>k</i> probes",
          "<b>~10 bits per entry for 1&nbsp;% false positive</b>", "Low", "Insert only",
          "<b>A cheap pre-filter in front of an expensive lookup</b>"]]))
    s.append("""<div class="ms"><b>TCAM is the structure that decides the cost of a
    router, and it is worth knowing why it is so expensive.</b> A ternary cell stores
    three states &mdash; 0, 1 and don't-care &mdash; which needs two storage bits plus
    comparison logic, roughly sixteen transistors against six for SRAM. Worse, every cell
    compares on every lookup, so power is proportional to the whole table rather than to
    the entry found: a large TCAM can dissipate tens of watts doing nothing but matching.
    <b>The architectural responses all reduce the number of cells that must compare</b>
    &mdash; partition the table by prefix length and activate only relevant banks, put a
    small filter in front, or replace TCAM with an algorithmic trie in SRAM and accept
    multiple accesses. Every high-end switch datasheet's power figure is substantially a
    statement about this one structure.</div>""")
    rows = []
    for entries in (1e3, 1e4, 1e5, 1e6):
        w = 144
        sram_bits = entries * w
        tcam_bits = entries * w * 2
        rows.append([num(int(entries)), num(w), num(sram_bits / 8 / 1024 / 1024, 4),
                     num(tcam_bits * 16 / 6 / 8 / 1024 / 1024, 4),
                     num(entries * w * 1.2e-15 * 1e9 * 1e-3, 4)])
    s.append(sweep("TCAM cost against table size, 144-bit keys (indicative "
                   "16&nbsp;T/cell against 6&nbsp;T SRAM, 1&nbsp;GHz lookup)",
        ["Entries", "Key bits", "SRAM-equivalent (MB)",
         "TCAM area as SRAM-equivalent (MB)", "Match-line power (W, indicative)"], rows,
        "<b>Indicative constants, not a vendor datasheet.</b> The shape is the point: "
        "area roughly five times SRAM for the same bits, and a power term that grows "
        "with table size independently of the traffic."))

    s.append("<h2>X35.2 Hashing: the birthday problem decides your table size</h2>")
    s.append(derive("Why a hash table needs to be much larger than its contents", [
        ("With <i>n</i> items in <i>m</i> buckets, the probability that a particular "
         "pair collides is 1/<i>m</i>.",
         "Uniform hashing assumption."),
        ("There are <i>n</i>(<i>n</i>&minus;1)/2 pairs, so the expected number of "
         "colliding pairs is about <i>n</i><sup>2</sup>/(2<i>m</i>).",
         "Linearity of expectation."),
        ("<b>Collisions start appearing when <i>n</i> &asymp; &radic;<i>m</i></b>, not "
         "when <i>n</i> &asymp; <i>m</i>.",
         "The birthday paradox. <b>This is the fact that surprises people sizing "
         "tables.</b>"),
        ("The longest chain with <i>n</i> = <i>m</i> is "
         "&Theta;(log <i>n</i>/log log <i>n</i>) &mdash; about 5&ndash;8 for realistic "
         "sizes.",
         "So a single-probe hardware lookup fails often enough to matter."),
        ("<b>Two hash functions and a choice of the emptier bucket reduces the longest "
         "chain to log log <i>n</i>.</b>",
         "The power of two choices: an exponential improvement from one extra probe. "
         "<b>This is why hardware hash tables are multi-way.</b>"),
    ]))
    rng = np.random.default_rng(13)
    rows = []
    for load in (0.25, 0.5, 0.75, 0.9, 0.95):
        m = 4096
        n = int(load * m)
        trials = 30
        one, two = [], []
        for _ in range(trials):
            b1 = np.zeros(m, int)
            keys = rng.integers(0, 1 << 30, n)
            h1 = keys % m
            for h in h1:
                b1[h] += 1
            one.append(int(b1.max()))
            b2 = np.zeros(m, int)
            ha = keys % m
            hb = (keys * 2654435761) % m
            for a, b_ in zip(ha, hb):
                if b2[a] <= b2[b_]:
                    b2[a] += 1
                else:
                    b2[b_] += 1
            two.append(int(b2.max()))
        rows.append([num(load, 4), num(n), num(float(np.mean(one)), 4),
                     num(float(np.mean(two)), 4),
                     num(float(np.mean(one)) / float(np.mean(two)), 4)])
    s.append(sweep("Measured longest bucket in a 4096-bucket table, one hash against "
                   "two-choice hashing, 30 trials per point",
        ["Load factor", "Keys", "Longest bucket, 1 hash",
         "Longest bucket, 2 choices", "Ratio"], rows,
        "Simulated with random keys, seed 13. <b>The second hash roughly halves the "
        "worst bucket at every load</b>, which in hardware is the difference between "
        "a lookup engine that must handle eight-deep chains and one that handles "
        "four."))
    s.append(ex("Sizing a flow table for a bounded lookup time",
        "A network block must look up 200&#8239;000 flows at 100&nbsp;Gbit/s, one "
        "lookup per 64-byte packet, with a <i>bounded</i> lookup time of two memory "
        "accesses.",
        "Bounded worst case rules out chaining. Compute what a 4-way cuckoo table "
        "costs at a load factor it can sustain.",
        [("Packet rate at 64&nbsp;B", num(100e9 / (64 + 20) / 8 / 1e6, 4, "Mpps")),
         ("Lookups per second", num(100e9 / (64 + 20) / 8, 3)),
         ("Flows", num(200000)),
         ("Cuckoo load factor achievable at 4 ways", num(0.97, 3)),
         ("Buckets needed", num(int(200000 / 0.97))),
         ("Entries at 4 per bucket", num(int(200000 / 0.97 / 4) * 4)),
         ("Memory at 64&nbsp;B per entry",
          num(int(200000 / 0.97) * 64 / 1024 / 1024, 4, "MB")),
         ("Probes per lookup", num(4) + " (parallel, one bucket read)"),
         ("Worst-case accesses", num(2))],
        "<b>By choosing the average-case structure for a worst-case requirement.</b> "
        "Chained hashing has a superb average and an unbounded tail, and a networking "
        "datapath is judged on the tail: a lookup that occasionally takes eight accesses "
        "either stalls the pipeline or drops the packet. <b>Cuckoo hashing buys a "
        "bounded query at the cost of a potentially long <i>insertion</i></b>, which is "
        "the right trade because insertions are rare and can be handled by a slow path. "
        "Recognising which operation must be bounded is the whole of the design "
        "decision."))

    s.append("<h2>X35.3 Bloom filters: paying memory for certainty in one direction</h2>")
    s.append(derive("The false-positive rate, and the optimal number of hashes", [
        ("A Bloom filter is <i>m</i> bits; inserting an item sets <i>k</i> bits chosen "
         "by <i>k</i> hashes.",
         "No item is stored &mdash; only its fingerprint in the bit array."),
        ("After <i>n</i> insertions, the probability a given bit is still zero is "
         "(1&minus;1/<i>m</i>)<sup><i>kn</i></sup> &asymp; "
         "e<sup>&minus;<i>kn</i>/<i>m</i></sup>.",
         "Independent settings."),
        ("A query gives a false positive when all <i>k</i> bits happen to be set: "
         "<b><i>p</i> = (1&minus;e<sup>&minus;<i>kn</i>/<i>m</i></sup>)<sup><i>k</i></sup></b>.",
         "<b>Never a false negative</b> &mdash; that asymmetry is the whole "
         "value."),
        ("Minimising over <i>k</i> gives <i>k</i> = (<i>m</i>/<i>n</i>)ln&nbsp;2.",
         "And then <i>p</i> = 2<sup>&minus;<i>k</i></sup>."),
        ("<b>So about 1.44&nbsp;log<sub>2</sub>(1/<i>p</i>) bits per item, regardless "
         "of how large the items are.</b>",
         "A 1&nbsp;% filter costs about 10 bits per item whether the items are 32-bit "
         "or 1500-byte. <b>That independence from key size is why it is used in front "
         "of expensive lookups.</b>"),
    ]))
    rows = []
    for bits_per in (4, 8, 10, 12, 16, 20):
        k = max(1, round(bits_per * math.log(2)))
        p = (1 - math.exp(-k / bits_per)) ** k
        rows.append([num(bits_per), num(k), num(p, 3), num(p * 100, 3),
                     num(bits_per * 1e6 / 8 / 1024 / 1024, 4)])
    s.append(sweep("Bloom filter false-positive rate against bits per item",
        ["Bits/item", "Optimal hashes <i>k</i>", "False positive", "(%)",
         "Memory for 10<sup>6</sup> items (MB)"], rows,
        "Computed from the closed form. <b>Ten bits per item buys about one per cent</b>, "
        "and each further factor of ten costs about 3.3 bits &mdash; a very good rate "
        "of exchange when the alternative is storing the keys."))
    s.append(prob("Where does a Bloom filter belong in an IP block, and where does it "
                  "not?",
        "It belongs wherever a <b>negative answer is common and an expensive lookup can "
        "be skipped</b>, and where a false positive costs only wasted work rather than a "
        "wrong result. Concretely: in front of a TCAM or an off-chip table, to avoid the "
        "access entirely for the majority of keys that are absent; in a cache to avoid "
        "probing a way; in a coherence directory to avoid a snoop. In each case the "
        "filter is an optimisation and the real structure still answers. <b>It does not "
        "belong anywhere the answer is used directly</b>, because a false positive is "
        "then a wrong answer &mdash; and it does not belong where deletions are needed, "
        "because a plain Bloom filter cannot delete (clearing a bit may un-insert another "
        "item); that needs a counting Bloom filter at four times the memory, and at that "
        "point a small hash table is often better. <b>The design question to ask is: "
        "what is the measured fraction of negative queries?</b> A filter in front of a "
        "table that is usually hit is pure cost, and that fraction is a property of the "
        "customer's traffic, which means it belongs in the datasheet as an assumption."))
    return "\n".join(s)
