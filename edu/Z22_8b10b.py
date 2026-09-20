# -*- coding: utf-8 -*-
"""Volume III, Part Z22 -- 8b/10b: one block, two markets."""
import sys, os, json
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, derive
import sch

PROTO = "/home/user/SE/edu/proto"
잰것 = json.load(open(os.path.join(PROTO, "잰것.json"), encoding="utf-8"))
E8 = 잰것["enc8b10b"]


def _c(s):
    return "<pre><code>" + E(s) + "</code></pre>"


def _읽기(이름, 시작, 줄수):
    t = open(os.path.join(PROTO, 이름), encoding="utf-8").read().splitlines()
    return "\n".join(t[시작:시작 + 줄수])


def ch_8b10b():
    s = ['<h1 id="z22">Z22. 8b/10b &mdash; One Block, Two Markets</h1>']

    s.append("""<p>Of everything a one-person design house could build first, an 8b/10b
    encoder is unusually well chosen, for a reason that has nothing to do with the
    technology: <b>the same block sells into PCIe and into Ethernet.</b> PCIe Gen1 and
    Gen2 use it as the physical-layer line code; so does 1000BASE-X, the gigabit Ethernet
    PCS. So do SATA, DisplayPort, Fibre Channel and USB&nbsp;3 Gen1. One verification
    effort, one datasheet, several customers who do not compete with each other.</p>""")

    s.append("<h2>Z22.1 Where it sits</h2>")
    s.append(fig(sch.블록도([
        ["MAC / TLP", "Scrambler", "8b/10b", "Serialiser", "Driver"],
        ["Receiver", "CDR", "Deserialiser", "Comma align", "8b/10b dec"],
    ], 칸=112, 설명={
        "8b/10b": "★ 이 장의 블록\n8비트 -> 10비트",
        "Scrambler": "반복 무늬를 흩는다\nEMI 와 짧은 주기 방지",
        "Serialiser": "10비트 -> 직렬\n10x 클럭",
        "CDR": "데이터에서\n클럭을 뽑는다",
        "Comma align": "K.28.5 를 보고\n바이트 경계를 잡는다",
        "8b/10b dec": "10 -> 8, 오류 검출",
    }), """The transmit chain (top) and receive chain (bottom). Our encoder is the last
    digital stage before serialisation. The two blocks that depend on it most are drawn
    on the receive side: the CDR needs the transitions 8b/10b guarantees, and comma
    alignment works only because the comma pattern cannot occur in data."""))

    s.append("""<p>Read that diagram as a list of obligations rather than a picture. The
    CDR cannot recover a clock from a long run of identical bits, so the code must bound
    run length. The AC coupling capacitors in the channel cannot pass DC, so the code must
    bound the imbalance between ones and zeros. The deserialiser has no idea where a byte
    starts, so the code must provide a pattern that means &lsquo;here&rsquo; and cannot be
    forged by data. Each of those is one of the four properties Part&nbsp;Z21 proved.</p>""")

    s.append("<h2>Z22.2 What the code does, in one worked byte</h2>")
    s.append(derive("Encoding 0x00 with running disparity &minus;1",
        [("Split the byte into low 5 bits and high 3 bits: 0x00 &rarr; x = 0, y = 0. "
          "This is written D0.0.",
          "The code is built from a 5b/6b stage and a 3b/4b stage. The naming D<i>x</i>.<i>y</i> "
          "is universal in the literature."),
         ("Look up x = 0 in the 5b/6b table for RD = &minus;1: <code>100111</code>.",
          "Four ones and two zeros, so its disparity is +2."),
         ("Running disparity was &minus;1; adding +2 gives +1.",
          "This is why the table for RD = &minus;1 holds the codeword with positive "
          "disparity: it pulls the imbalance back toward zero."),
         ("Now look up y = 0 in the 3b/4b table, <b>using the updated disparity</b> "
          "RD = +1: <code>0100</code>.",
          "One one and three zeros, disparity &minus;2. The 3b/4b stage sees the "
          "disparity <i>after</i> the 6-bit stage, not the disparity the byte started "
          "with &mdash; a detail that is easy to get wrong and that the property check "
          "catches immediately."),
         ("RD becomes +1 &minus; 2 = &minus;1, and the codeword is "
          "<code>100111</code>&nbsp;<code>0100</code>.",
          "Back where we started, which is exactly what bounded running disparity means."),
         ("Check the result: <code>1001110100</code> has five ones and five zeros, and "
          "its longest run is two.",
          "Verified against the published value for D0.0 as one of the seven "
          "corroboration vectors.")]))

    s.append(fig(sch.파형([
        ("data 0x00", "^^^^^^^^"),
        ("coded",     "^__^^^_^"),
        ("clk",       "_^_^_^_^"),
    ]), """Why the code exists, drawn. An all-zero byte sent raw (top, shown held) offers
    the receiver's clock-recovery loop no transitions at all. The same byte encoded
    (middle) carries five transitions in ten bits. The encoder's job is to make every
    byte look like the middle trace."""))

    s.append("<h2>Z22.3 The four properties, proven</h2>")
    p = E8["성질전수확인"]
    s.append("""<p>Part&nbsp;Z21 explained why these are the right things to check. Here
    is what they came back as, over all %d codewords and every ordered pair of codewords
    that can actually follow one another:</p>""" % p["코드워드수"])

    s.append(tab("Exhaustive property check, edu/proto/proto_check.cpp",
        ["Property", "Why the code needs it", "Result"],
        [["P1 &mdash; bijective within each disparity",
          "Otherwise two bytes share a codeword and the link cannot decode.",
          "<b>%d</b> collisions" % p["P1_전단사_겹침"]],
         ["P2 &mdash; running disparity stays in {&minus;1, +1}",
          "DC balance on an AC-coupled channel.",
          "<b>%d</b> excursions" % p["P2_RD가_범위밖"]],
         ["P3 &mdash; at most 5 identical bits in a row",
          "The CDR needs transitions to hold lock.",
          "longest run <b>%d</b>, violations <b>%d</b>"
          % (p["P3_최장연속비트"], p["P3_5초과_이음"])],
         ["P4 &mdash; comma never appears in data",
          "Byte alignment depends on the comma being unforgeable.",
          "<b>%d</b> occurrences" % p["P4_데이터에서_콤마"]],
         ["Not degenerate", "A check that only ever sees a few values proves nothing.",
          "<b>%d</b> distinct codewords of 1024" % p["서로다른코드워드"]]]))

    s.append("""<p>The third row is worth dwelling on, because it is the one that cannot
    be checked by looking at a codeword. A run of six can straddle a boundary: each
    codeword is individually fine and the pair is not. That is why the checker enumerates
    <em>pairs</em>, filtered by which disparity each one can follow &mdash; and it is why
    the two table-compression defects of Part&nbsp;Z21 were invisible until it ran.</p>""")

    s.append(ex("Why the longest run is exactly 5 and not 4",
        given="P3 reports a longest run of %d, and that is a pass rather than a failure."
              % p["P3_최장연속비트"],
        method="Ask what produces the run of 5 and whether it is avoidable.",
        numbers="The comma itself. K.28.5 is <code>0011111010</code> &mdash; five ones in "
                "a row, by construction. Any code that also bounded data runs at 5 "
                "without exception would have no pattern left that data cannot produce.",
        trap="The tempting reading of &lsquo;longest run = 5&rsquo; is that the design "
             "only just passes and a small change might push it to 6. The opposite is "
             "true: the 5 is <b>designed in</b>, it occurs only in K codes, and the data "
             "codewords are strictly better behaved. Reporting the maximum without saying "
             "where it comes from would leave a reader with the wrong impression of the "
             "margin.",
        extra="This is the general shape of the run-length/alignment trade. The comma "
              "must be distinguishable from data, so it must do something data cannot. "
              "Making the bound tighter for data is what buys the comma its "
              "distinctiveness."))

    s.append("<h2>Z22.4 The circuit</h2>")
    s.append("""<p>The encoder is almost entirely combinational. There is exactly one bit
    of state in the whole block.</p>""")

    s.append(fig(sch.블록도([
        ["data[4:0]", "5b/6b mux", "six[5:0]"],
        ["data[7:5]", "3b/4b mux", "four[3:0]"],
    ], 칸=118, 설명={
        "5b/6b mux": "32 x 2 항목\nrd 가 열을 고른다",
        "3b/4b mux": "8 x 2 항목\nrd_mid 가 열을 고른다",
        "six[5:0]": "불균형으로\nrd_mid 를 만든다",
        "four[3:0]": "불균형으로\nrd_next 를 만든다",
    }), """The datapath. Two table lookups (which synthesise to multiplexers), two
    popcount-and-compare blocks to update the disparity, and one flip-flop holding it.
    The 3b/4b stage is selected by <code>rd_mid</code> &mdash; the disparity <i>after</i>
    the 6-bit stage &mdash; which is the sequencing the worked example in Z22.2 walked
    through."""))

    s.append(derive("Why the running disparity register is one bit wide",
        [("Running disparity is conventionally described as a signed accumulator.",
          "That is how the literature explains it, and it invites an implementation with "
          "a width and a saturation question."),
         ("But P2 proves it only ever takes the values &minus;1 and +1.",
          "Every codeword has disparity &minus;2, 0 or +2, and the table selection always "
          "moves it back toward zero."),
         ("Two possible values need exactly one bit: 0 means &minus;1, 1 means +1.",
          "The accumulator, its width, and its saturation logic all disappear."),
         ("So the entire sequential state of an 8b/10b encoder is one flip-flop.",
          "Measured: the synthesised block has %d flip-flops &mdash; %s. Exactly one of "
          "them is the protocol state."
          % (E8["면적"]["플립플롭"], E8["면적"]["플립플롭_내역"])),
         ("<b>Knowing an invariant is what bought that.</b>",
          "The proof did not just check the design; it simplified it. This is the usual "
          "return on proving a property rather than assuming it.")]))

    s.append("<h2>Z22.5 The one-bit-state rule, in code</h2>")
    s.append(_c("""// 6비트 코드워드의 불균형만큼 RD 가 움직인다.  -2 / 0 / +2 뿐이다.
// $countones 대신 손으로 더한다 -- iverilog 가 -g2012 에서도 그것을
// 안 받는 판이 있다.  **도구에 안 기대는 쪽을 고른다.**
wire [2:0] six_ones = {2'b0, six[5]} + {2'b0, six[4]} + {2'b0, six[3]}
                    + {2'b0, six[2]} + {2'b0, six[1]} + {2'b0, six[0]};

// 1의 개수가 4 면 +2, 3 이면 0, 2 면 -2.  rd 는 1비트다.
wire rd_mid = (six_ones == 3'd4) ? 1'b1 :
              (six_ones == 3'd2) ? 1'b0 : rd;"""))

    s.append("""<p>Two details in six lines. The manual popcount avoids
    <code>$countones</code>, which some simulator builds reject even in
    <code>-g2012</code> mode &mdash; when a construct buys you nothing but a dependency,
    do not take the dependency. And the <code>rd</code> fall-through in the last line is
    the disparity-zero case: the codeword does not move the imbalance, so the register
    holds. Writing that as an explicit <code>else</code> rather than letting it fall out
    of an incomplete assignment is what keeps <code>always_comb</code> from inferring a
    latch (Part&nbsp;Z18.5).</p>""")

    s.append("<h2>Z22.6 Verification</h2>")
    r = E8["RTL회귀"]
    m = E8["변이점수"]
    s.append(tab("What was run against the encoder",
        ["Check", "Result", "What it establishes"],
        [["Exhaustive property proof (C++)",
          "P1&ndash;P4 all pass, %d codewords" % p["코드워드수"],
          "The code is internally consistent and does what 8b/10b exists to do."],
         ["Published codeword spot-check", "%d of %d match"
          % (E8["독립대조"]["일치"], E8["독립대조"]["널리인용되는코드워드"]),
          "Weak but independent corroboration that these are <i>the</i> tables."],
         ["RTL vs C++ golden, streamed", "%d vectors, %d wrong, %d distinct outputs"
          % (r["벡터"], r["틀림"], r["서로다른출력"]),
          "The hand-written Verilog agrees with the independently written C++, "
          "<b>including the disparity carried between codewords</b>."],
         ["Self-check (corrupt one golden value)", r["자해검사"],
          "The comparison can actually fail. Without this the row above means nothing."],
         ["Mutation score", "%d/%d = %.0f&nbsp;%%, %d judged equivalent"
          % (m["잡힘"], m["변이수"], m["점수"] * 100, m["등가로판정됨"]),
          "The tests <i>bite</i>. This is a different question from &lsquo;do the tests "
          "pass&rsquo;."]]))

    s.append("""<p>The stream matters more than the count. The golden generator threads
    running disparity from one vector to the next, so the expected value on line 2000
    depends on every line before it. A single disagreement anywhere makes everything after
    it wrong &mdash; the regression cannot quietly pass with a broken state machine, which
    is the failure mode a per-codeword test would have.</p>""")

    s.append(ex("What the mutation score found that %d passing vectors did not"
                % r["벡터"],
        given="The regression passed %d streamed vectors with 0 mismatches. Mutation "
              "scoring then reported 71.4&nbsp;%% with six escapes." % r["벡터"],
        method="Look at each surviving mutant and ask why the tests cannot see it.",
        numbers="Five were <b>provably equivalent</b> &mdash; OR replaced by XOR in a "
                "condition whose terms are mutually exclusive, verified over all "
                "32&times;2 = 64 inputs with zero differences. The sixth was real: "
                "<code>code_valid &lt;= valid &amp; ~bad_k</code> mutated to "
                "<code>|</code> survived.",
        trap="The real one is not a subtle bug &mdash; the mutant asserts "
             "<code>code_valid</code> on every idle cycle, which would break any "
             "downstream consumer immediately. It survived because the testbench "
             "<b>never looked at an idle cycle</b>. The stimulus drove a transaction "
             "every beat, so the entire idle path was unexercised. No amount of "
             "additional random data would have found it.",
        extra="The fix was to observe <code>code_valid</code> during a deliberate idle "
              "beat after each transaction, which took four lines and moved the score to "
              "%.0f&nbsp;%%. This is the same lesson as the throughput mutant in "
              "Part&nbsp;Z1: a regression measures what you told it to look at, and "
              "mutation scoring is how you find out what you forgot."
              % (m["점수"] * 100)))

    s.append("<h2>Z22.7 What it costs</h2>")
    a, pn = E8["면적"], E8["PnR"]
    fm = pn["Fmax_MHz"]
    s.append(tab("Synthesis and place-and-route, iCE40 HX8K",
        ["Measure", "Value", "Note"],
        [["Cells (standalone)", str(a["단독_cells"]), "yosys <code>synth_ice40</code>"],
         ["SB_LUT4", str(a["SB_LUT4"]), "The two table multiplexers dominate"],
         ["SB_CARRY", str(a["SB_CARRY"]), "The popcount adders"],
         ["Flip-flops", str(a["플립플롭"]), a["플립플롭_내역"]],
         ["ICESTORM_LC (with timing shell)", str(pn["ICESTORM_LC"]),
          "Includes the shell's input registers"],
         ["F<sub>max</sub>", "%.1f / %.1f / %.1f MHz" % tuple(fm),
          "Three placer seeds; spread under 2&nbsp;%"],
         ["Verilator <code>-Wall</code>", "0 warnings", "Clean, not suppressed"]]))

    s.append("""<p>%d LUTs and %d flip-flops for a block that sits in the datapath of
    every PCIe Gen2 lane in the world. But the frequency is the number that decides what
    this block is actually good for, and it is worth doing that arithmetic rather than
    assuming.</p>""" % (a["SB_LUT4"], a["플립플롭"]))

    s.append(ex("Is this fast enough to sell?",
        given="The encoder reaches %.1f&nbsp;MHz on iCE40 HX8K at one byte per clock. "
              "1000BASE-X carries 1&nbsp;Gb/s of payload; PCIe Gen2 runs 5&nbsp;GT/s per "
              "lane and 8b/10b passes 8 payload bits per 10 transmitted." % min(fm),
        method="Convert each protocol's payload rate into the byte rate the encoder must "
               "accept, then compare.",
        numbers="1000BASE-X needs 1&nbsp;Gb/s &divide; 8 = <b>125&nbsp;Mbyte/s</b>. PCIe "
                "Gen2 needs 5&nbsp;GT/s &times; 8/10 &divide; 8 = "
                "<b>500&nbsp;Mbyte/s</b> per lane. At one byte per clock this block "
                "delivers %.1f&nbsp;Mbyte/s &mdash; <b>%.0f&nbsp;%% of gigabit Ethernet "
                "and %.0f&nbsp;%% of one PCIe Gen2 lane.</b> It meets neither."
                % (min(fm), min(fm) / 125 * 100, min(fm) / 500 * 100),
        trap="The tempting sentence to write was &lsquo;comfortably past gigabit "
             "Ethernet&rsquo; &mdash; it was in the first draft of this page, and it was "
             "wrong by a factor of 1.5. %.1f&nbsp;MHz sounds fast, and a block being "
             "small and clean invites the assumption that it is also fast enough. "
             "<b>Neither area nor cleanliness implies throughput; only the arithmetic "
             "does.</b> The same draft also multiplied %.2f by 8 and got 686 instead of "
             "679." % (min(fm), min(fm)),
        extra="The fix is architectural, not a matter of squeezing the timing. Encoding "
              "two bytes per clock gives %.0f&nbsp;Mbyte/s, which clears 1000BASE-X with "
              "margin; the two encoders are independent except that the second must take "
              "the first's updated disparity, so the disparity path becomes the critical "
              "path. PCIe Gen2 needs six bytes per clock at this frequency, which on this "
              "fabric is not the right answer &mdash; that part belongs on a faster "
              "process." % (min(fm) * 2)))

    s.append("""<p>So the honest positioning is: on this FPGA, at one byte per clock, the
    block is a demonstration rather than a shippable PHY. Widened to two bytes per clock
    it is a plausible 1000BASE-X part. PCIe Gen2 is a different process, not a different
    day of optimisation. A datasheet that says that is more useful than one that quotes
    %.1f&nbsp;MHz and leaves the division to the reader.</p>""" % min(fm))

    s.append("<h2>Z22.8 What is not in the box</h2>")
    s.append("""<p>Stated here rather than left for a customer to find:</p>""")
    s.append(tab("Known limitations",
        ["Gap", "Consequence", "Effort to close"],
        [["Encoder only &mdash; no decoder",
          "Half a link. A decoder needs the inverse tables plus invalid-codeword and "
          "disparity-error detection.",
          "Comparable to the encoder, plus error reporting. The property harness is "
          "reusable as-is."],
         ["Only K.28.x control codes",
          "K.23.7, K.27.7, K.29.7 and K.30.7 are unavailable. Enough for alignment and "
          "framing; not enough for every protocol's ordered sets.",
          "Small &mdash; those four take the 5b/6b data table with the K 3b/4b table."],
         ["Not compared to the normative tables",
          "Byte-exact interoperability is unproven. See Part&nbsp;Z21.",
          "One afternoon with the document, and only the two <code>case</code> statements "
          "change."],
         ["No scrambler",
          "8b/10b bounds run length but does not break up repeating patterns, which "
          "concentrate EMI at one frequency.",
          "Separate block; an LFSR and an XOR."]]))

    s.append("""<p>That table is the honest version of &ldquo;production ready&rdquo;. The
    verification is real and unusually thorough for a block this size; the scope is
    genuinely narrow. Both halves belong in the datasheet, because a customer who
    discovers the second half after buying will not believe the first.</p>""")

    return "\n".join(s)
