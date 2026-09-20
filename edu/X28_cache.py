# -*- coding: utf-8 -*-
"""Volume I, Part X28 -- Caches and coherence, worked."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_cache():
    s = ['<h1 id="x28">X28. Caches and Coherence, Worked</h1>']
    s.append("""<p>Any IP block that sits behind a cache inherits its behaviour, and any
    block that contains one inherits its complexity. This part computes the three things
    that decide a cache design &mdash; the miss rate, the coherence traffic and the
    verification burden &mdash; because all three are routinely underestimated.</p>""")

    s.append("<h2>X28.1 The three Cs, measured rather than recited</h2>")
    s.append(derive("Why a cache works at all", [
        ("Programs exhibit <b>temporal locality</b>: a referenced address is likely to "
         "be referenced again soon.",
         "Loops, stacks, repeatedly used variables."),
        ("And <b>spatial locality</b>: addresses near a referenced one are likely "
         "next.",
         "Arrays, instruction streams, structures."),
        ("A cache exploits the first by keeping recent data and the second by fetching "
         "a whole line.",
         "The line size is the knob that trades one against the other."),
        ("Misses classify as <b>compulsory</b> (first touch), <b>capacity</b> (working "
         "set exceeds the cache) and <b>conflict</b> (associativity too low).",
         "Hill's three Cs. <b>Each has a different fix</b>, which is why the "
         "classification is worth measuring rather than guessing."),
        ("Compulsory misses fall with line size; conflict misses fall with "
         "associativity; capacity misses fall only with capacity.",
         "<b>So a miss-rate problem must be classified before it can be addressed.</b> "
         "Doubling associativity does nothing for a capacity problem, and the tool will "
         "not tell you which you have."),
    ]))
    rng = np.random.default_rng(7)

    def simulate(refs, lines, ways, linesz):
        """Return (misses, compulsory, capacity, conflict).

        The three Cs are classified the standard way: run a **fully associative
        LRU cache of the same capacity** alongside.  A miss that the fully
        associative cache also takes is compulsory or capacity; a miss it would
        have hit is a conflict miss, caused purely by the limited associativity.

        The obvious shortcut -- "call it capacity once the working set exceeds
        the cache" -- was tried first and reported **zero conflict misses on
        every row**, which the build's constant-column scan caught.  It was not
        measuring conflicts at all.
        """
        sets_ = max(1, lines // ways)
        tags = [dict() for _ in range(sets_)]
        order = [[] for _ in range(sets_)]
        fa = {}
        fa_order = []
        miss = comp = cap = conf = 0
        seen = set()
        for a in refs:
            bl = a // linesz
            st = bl % sets_
            tg = bl // sets_
            # --- fully associative reference
            fa_hit = bl in fa
            if fa_hit:
                fa_order.remove(bl)
                fa_order.append(bl)
            else:
                if len(fa) >= lines:
                    ev = fa_order.pop(0)
                    del fa[ev]
                fa[bl] = True
                fa_order.append(bl)
            # --- the cache under test
            if tg in tags[st]:
                order[st].remove(tg)
                order[st].append(tg)
                continue
            miss += 1
            if bl not in seen:
                comp += 1
                seen.add(bl)
            elif fa_hit:
                conf += 1          # the fully associative cache had it
            else:
                cap += 1
            if len(tags[st]) >= ways:
                ev = order[st].pop(0)
                del tags[st][ev]
            tags[st][tg] = True
            order[st].append(tg)
        return miss, comp, cap, conf

    # A reference stream with both a strided walk (which defeats a small cache)
    # and a tight loop (which fits), so that all three miss classes occur.
    N = 60000
    stride = 64
    refs = []
    for i in range(N // 2):
        refs.append((i * stride) % (1 << 20))
        refs.append((i % 512) * 8)

    # A second stream, built deliberately to collide.  Four arrays are separated
    # by exactly the cache size, and each walks only a quarter of the sets, so the
    # whole working set is 4 x 64 = 256 lines -- exactly the cache's capacity.
    # It therefore *fits*, and whether it hits depends only on associativity:
    # direct-mapped puts all four arrays in the same set and thrashes; four ways
    # holds all four.
    #
    # The first attempt used a quarter-sized stride and walked all 256 sets, which
    # made the working set four times the capacity.  The measurement then showed a
    # 100 % miss rate at every associativity -- capacity-bound, not conflict-bound,
    # and the opposite of what the surrounding text claimed.
    CAP = 256 * 64
    refs2 = []
    for i in range(N // 8):
        for k in range(4):
            refs2.append(k * CAP + (i % 64) * 64)

    rows = []
    for name, rf in (("mixed strided + loop", refs), ("<b>four colliding arrays</b>",
                                                      refs2)):
        for ways in (1, 2, 4, 8):
            m, c, ca, co = simulate(rf, lines=256, ways=ways, linesz=64)
            rows.append([name if ways == 1 else "", num(ways), num(m),
                         num(m / len(rf), 4), num(c), num(ca), num(co)])
    s.append(sweep("Measured three-Cs breakdown for a 16&nbsp;kB cache (256 lines of "
                   "64&nbsp;B) on two reference streams",
        ["Stream", "Ways", "Misses", "Miss rate", "Compulsory", "Capacity",
         "Conflict"], rows,
        "Each miss is classified by running a fully associative cache of the same "
        "capacity alongside: a miss the fully associative cache would have hit is a "
        "conflict miss. <b>The two streams are the two regimes.</b> The first is "
        "capacity-bound &mdash; it touches far more data than fits, so associativity "
        "buys almost nothing (59 conflict misses out of 33&#8239;707). The second is "
        "conflict-bound by construction: its working set is exactly the cache's "
        "capacity, so it fits, and only associativity decides whether it hits. <b>A miss-rate number without this breakdown cannot tell you which "
        "you have</b>, and the two have different fixes."))
    rows = []
    for linesz in (16, 32, 64, 128, 256):
        lines = 16384 // linesz
        m, c, ca, co = simulate(refs, lines=lines, ways=4, linesz=linesz)
        rows.append([num(linesz), num(lines), num(m), num(m / len(refs), 4),
                     num(c), num(m * linesz / 1024, 5)])
    s.append(sweep("Same 16&nbsp;kB cache, 4-way, as line size is swept",
        ["Line (B)", "Lines", "Misses", "Miss rate", "Compulsory",
         "Bytes fetched (kB)"], rows,
        "The last column is the point that miss rate alone hides: <b>a longer line "
        "lowers the miss rate and raises the bandwidth</b>, because each miss moves more "
        "data. A design judged on miss rate will choose lines that are too long for the "
        "memory system it has."))

    s.append("<h2>X28.2 Average memory access time, and why it is the only metric</h2>")
    s.append(ex("Two caches, one better miss rate, and the wrong winner",
        "Cache A: 2&nbsp;% miss rate, 2-cycle hit. Cache B: 1.4&nbsp;% miss rate, "
        "3-cycle hit (it is larger and more associative). Miss penalty 60 cycles.",
        "Average memory access time is hit time plus miss rate times penalty. "
        "Compute both and then find the penalty at which they cross.",
        [("Cache A AMAT", num(2 + 0.02 * 60, 4) + " cycles"),
         ("Cache B AMAT", num(3 + 0.014 * 60, 4) + " cycles"),
         ("Winner at 60-cycle penalty", "<b>A</b>"),
         ("Crossover penalty",
          num((3 - 2) / (0.02 - 0.014), 4) + " cycles"),
         ("Winner at 200-cycle penalty (DRAM)",
          "<b>B</b> &mdash; " + num(3 + 0.014 * 200, 4) + " vs " +
          num(2 + 0.02 * 200, 4)),
         ("What this depends on",
          "<b>the memory system, which is the customer's, not yours</b>")],
        "<b>By optimising the miss rate.</b> Miss rate is a property of the cache and "
        "the workload; AMAT is a property of the whole system, and the two rank designs "
        "differently whenever the hit time changes. The crossover above is at "
        "167&nbsp;cycles, so the same two caches swap places between an SRAM-backed "
        "system and a DRAM-backed one. <b>An IP block containing a cache must therefore "
        "state the miss penalty its configuration was chosen for</b>, and ideally make "
        "the configuration a parameter, because the customer's penalty is not yours."))
    rows = []
    for pen in (10, 20, 40, 80, 160, 320):
        a = 2 + 0.02 * pen
        b_ = 3 + 0.014 * pen
        rows.append([num(pen), num(a, 4), num(b_, 4),
                     "A" if a < b_ else "<b>B</b>", num(abs(a - b_) / min(a, b_) * 100, 3)])
    s.append(sweep("The same two caches across miss penalties",
        ["Miss penalty (cycles)", "AMAT A", "AMAT B", "Winner", "Margin (%)"], rows,
        "Computed from the definitions. <b>The winner changes in the middle of the "
        "range a real product spans</b>, which is the general reason cache parameters "
        "are made configurable rather than fixed."))

    s.append("<h2>X28.3 Coherence: the protocol and its traffic</h2>")
    s.append(tab("MESI states and what each permits",
        ["State", "Meaning", "Read hit", "Write hit", "On a remote read"],
        [["<b>M</b>odified", "Dirty, exclusive", "Yes", "<b>Yes, silently</b>",
          "Write back, go to S"],
         ["<b>E</b>xclusive", "Clean, exclusive", "Yes",
          "<b>Yes, silently &mdash; this is why E exists</b>", "Go to S"],
         ["<b>S</b>hared", "Clean, possibly shared", "Yes",
          "<b>No &mdash; must invalidate others first</b>", "Stay S"],
         ["<b>I</b>nvalid", "Not present", "Miss", "Miss", "&mdash;"]]))
    s.append("""<div class="ms"><b>The E state exists entirely to make private data
    cheap.</b> Without it, a line loaded by a read would be S, and the first write to it
    would need a bus transaction to invalidate copies that do not exist. Since most data
    in most programs is private, that transaction would be pure waste on the common path.
    E says &lsquo;clean and I am the only holder&rsquo;, so the write is silent. The cost
    is that the interconnect must be able to tell a requester whether anyone else has a
    copy &mdash; a shared signal on a bus, or a directory lookup &mdash; which is a real
    structural requirement that exists solely to support this optimisation. <b>It is a
    good example of a protocol state that looks redundant on a state diagram and is
    load-bearing in the traffic.</b></div>""")
    rows = []
    for cores in (2, 4, 8, 16, 32, 64):
        snoop = cores * (cores - 1)
        dir_bits = cores
        dir_overhead = cores / (64 * 8) * 100
        rows.append([num(cores), num(snoop), num(cores - 1),
                     num(dir_bits), num(dir_overhead, 4),
                     "snoop" if cores <= 8 else "<b>directory</b>"])
    s.append(sweep("Coherence cost against core count",
        ["Cores", "Snoop messages per miss (all-to-all)",
         "Snoops each cache must absorb", "Directory bits per line (full bit vector)",
         "Directory overhead (% of line)", "Practical choice"], rows,
        "Snooping broadcasts, so its traffic is quadratic in cores and every cache must "
        "absorb every other cache's misses &mdash; which becomes the bottleneck long "
        "before the wires do. <b>A directory is linear in traffic and pays a storage "
        "overhead</b>, and the crossover in practice is around eight to sixteen cores."))
    s.append("""<div class="warn"><b>Coherence is where verification cost explodes, and
    the reason is combinatorial.</b> A four-state protocol with four caches has
    4<sup>4</sup> combinations of state for one address, and the interesting bugs involve
    two addresses, an eviction in flight, and a request that arrives between the two
    halves of another transaction. The state space is far beyond directed testing, and
    random testing hits the interesting corners rarely. <b>This is the clearest case in
    the book for formal verification</b>: a coherence protocol is exactly the kind of
    deep, narrow state space that model checking handles and simulation does not, and
    proving the protocol at the specification level &mdash; before any RTL &mdash; is
    standard practice at companies that ship coherent systems. What formal cannot do is
    prove the <i>implementation</i> matches the protocol at scale, so both are
    needed.</div>""")
    s.append(prob("Your accelerator has a private cache and the host writes its input "
                  "buffer. What are the choices, and what does each cost?",
        "Four, in increasing order of hardware and decreasing order of software burden. "
        "<b>Uncached access</b>: the accelerator does not cache the buffer at all; "
        "correct by construction, and it gives up locality entirely, which for a "
        "streaming accelerator that touches each byte once is often the right answer. "
        "<b>Software coherence</b>: the driver flushes and invalidates around each "
        "transfer; cheap in hardware, and it is a source of extremely nasty bugs because "
        "a missing invalidate is intermittent and data-dependent, and the failure "
        "appears in the customer's driver rather than in your block. <b>IO coherence "
        "(one-way)</b>: the accelerator's accesses snoop the host caches but not the "
        "reverse; this is what most SoC interconnects offer today, it removes the flush "
        "burden for host-written data, and it costs interconnect support rather than "
        "accelerator complexity. <b>Full coherence</b>: the accelerator participates in "
        "the protocol as a peer, which gives the best performance for fine-grained "
        "sharing and costs a coherent cache controller plus the verification burden "
        "described above. <b>For a design house the recommendation is usually the third "
        "option</b>: it captures most of the benefit, the complexity lives in the "
        "customer's interconnect where it already exists, and it does not put a protocol "
        "state machine into your verification scope."))
    return "\n".join(s)
