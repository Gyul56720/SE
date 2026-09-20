# -*- coding: utf-8 -*-
"""Volume III, Part Z21 -- Building protocol IP when you cannot get the spec."""
import sys, os, json
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, E
from wex import ex, derive
import sch

PROTO = "/home/user/SE/edu/proto"
잰것 = json.load(open(os.path.join(PROTO, "잰것.json"), encoding="utf-8"))


def ch_protospec():
    s = ['<h1 id="z21">Z21. Building Protocol IP When You Cannot Get the Spec</h1>']

    s.append("""<p>Every previous part of this volume built a block whose definition was
    ours to choose. A protocol block is different: its correctness is defined by a
    document somebody else wrote, and for the protocols a design house most wants to sell
    into &mdash; MIPI CSI-2, PCIe, Ethernet &mdash; that document is expensive,
    membership-gated, or both.</p>

    <p>This part is about what to do then. It is not a workaround chapter. The discipline
    it describes &mdash; separate what you can prove from what you have assumed, and
    publish the boundary &mdash; is the same discipline you need <em>with</em> the spec in
    hand, because having the document does not mean you implemented it correctly.</p>""")

    s.append("<h2>Z21.1 The honest starting position</h2>")
    s.append("""<p>The container this book is built in has no outbound network: a
    <code>CONNECT</code> to <code>ieee802.org</code> returns 403. So the normative tables
    for 8b/10b and the MIPI packet-header ECC were not available while the blocks in
    Parts&nbsp;Z22 and&nbsp;Z23 were written. That is stated first, because everything
    else in those parts has to be read against it.</p>

    <p>There are exactly three things you can do in that position, and only the third is
    defensible:</p>""")

    s.append(tab("Three responses to a missing specification",
        ["Response", "What it produces", "Verdict"],
        [["Write the constants from memory and ship",
          "A block that looks finished and is wrong in ways nobody will notice until "
          "integration.",
          "<b>No.</b> This part demonstrates concretely why &mdash; three sets of "
          "remembered constants were wrong, and one was not even a valid code."],
         ["Refuse to build anything",
          "Nothing. The structure, the verification harness and the microarchitecture are "
          "all independent of the exact table values.",
          "<b>No.</b> It throws away the 90&nbsp;% of the work that does not depend on "
          "the document."],
         ["Build it, prove everything provable, and publish the boundary",
          "A block that is correct by construction on every property you can state, with "
          "a written list of what remains unverified and how to close it.",
          "<b>Yes.</b> This is what Parts Z22&ndash;Z23 do."]]))

    s.append("<h2>Z21.2 What &ldquo;provable without the document&rdquo; means</h2>")
    s.append("""<p>A protocol constant is not arbitrary. It was chosen to make the code
    satisfy properties &mdash; and those properties are usually stated in the open
    literature even when the tables are not. That gives you a check with real teeth:
    <b>assert the properties the constants exist to provide, and test them
    exhaustively.</b></p>""")

    s.append(tab("The two blocks, and what each property buys",
        ["Block", "Property asserted", "What a wrong constant would do"],
        [["8b/10b", "Bijective within each running disparity",
          "Two data bytes encode to the same codeword &rarr; the link cannot decode at "
          "all."],
         ["", "Running disparity stays in {&minus;1, +1}",
          "DC wander on an AC-coupled link &rarr; the receiver's slicer drifts off "
          "centre."],
         ["", "No more than 5 identical bits in a row, <b>across codeword boundaries</b>",
          "The CDR loses lock. This is the property that caught two of the three defects "
          "below."],
         ["", "The comma pattern never occurs in data",
          "The receiver aligns to a false byte boundary and every subsequent byte is "
          "garbage."],
         ["24+6 ECC", "All 29 single-error syndromes distinct and non-zero",
          "Two different single-bit errors look identical &rarr; the decoder "
          "&lsquo;corrects&rsquo; the wrong bit."],
         ["", "No double-error syndrome equals a single-error syndrome",
          "A 2-bit error is silently &lsquo;fixed&rsquo; into a 3-bit error. Worse than "
          "no ECC."]]))

    s.append("""<p>Every one of those is checkable by enumeration on a laptop in under a
    second, and every one of them failed at least once during this work.</p>""")

    s.append("<h2>Z21.3 What the checks actually caught</h2>")
    s.append("""<p>Six defects, all found by machine, none found by reading the code. They
    are listed in full because the pattern matters more than any one of them.</p>""")

    rows = []
    for f in 잰것["찾은결함"]:
        rows.append([f["어디"], f["무엇"], f["어떻게"]])
    s.append(tab("Every defect found while building the two protocol blocks",
        ["Where", "What was wrong", "How it surfaced"], rows))

    s.append(ex("The defect that would have shipped",
        given="The MIPI CSI-2 packet-header ECC parity masks, written from memory, were "
              "about to go into both the C++ model and the RTL.",
        method="Before writing any code with them, count the syndromes: each of the 24 "
               "data bits and 6 parity bits must produce a distinct, non-zero syndrome, "
               "or the code cannot even correct single errors.",
        numbers="<b>27 distinct syndromes out of the 30 required</b>, and 96 pairs where "
                "a double-bit error is indistinguishable from a single-bit error.",
        trap="The tempting reading is &ldquo;close enough, it is mostly right.&rdquo; It "
             "is not mostly right &mdash; it is <b>not a single-error-correcting code at "
             "all</b>. Three of the 24 data bits share a syndrome with another bit, so "
             "roughly one single-bit header error in ten would be &lsquo;corrected&rsquo; "
             "by flipping the wrong bit, turning a recoverable error into a corrupted "
             "packet length. A block like this passes a random-data regression perfectly, "
             "because random data contains no bit errors.",
        extra="The check that caught it is four lines of Python and it ran before any "
              "Verilog existed. The cost of not running it would have been discovered at "
              "a customer's integration bench, months later, as &lsquo;your ECC sometimes "
              "makes things worse&rsquo;."))

    s.append("<h2>Z21.4 The pattern in the three 8b/10b defects</h2>")
    s.append("""<p>Three separate defects in the encoder all had the same root, and it was
    not a typo. It was <b>a compression rule that was really an unstated hypothesis</b>.</p>""")

    s.append(derive("How a good idea became three bugs",
        [("The 8b/10b tables have two columns &mdash; one per running disparity. Writing "
          "both invites a typo in one column only.",
          "A typo in one column is invisible to any check that only exercises the other."),
         ("Observation: most second-column entries are the bitwise complement of the "
          "first, and entries with zero disparity appear in both columns unchanged.",
          "True for the majority of entries, which is what made it convincing."),
         ("So: store one column, derive the other. Half the table, half the typo surface.",
          "This reasoning is correct as far as it goes, and the comment in the first "
          "draft said exactly this."),
         ("<b>But &lsquo;zero disparity implies one codeword&rsquo; is a hypothesis, not "
          "a fact.</b>",
          "A 4-bit code with two ones and two zeros has disparity zero &mdash; and so "
          "does its complement. Both are legal on disparity grounds, so disparity alone "
          "cannot pick one."),
         ("What picks between them is <b>run length</b>, not disparity.",
          "D.x.3 is 1100 after one six-bit prefix and 0011 after another, because "
          "<code>001111</code> followed by <code>1100</code> puts six ones in a row and "
          "breaks the CDR."),
         ("The compression therefore collapsed nine genuinely-distinct table entries "
          "into one each, and the property check found it: 1082 run-length violations "
          "and 2048 false commas.",
          "Then, after fixing the 4-bit tables, 556 violations remained &mdash; the same "
          "hypothesis was also wrong for exactly one 5b/6b entry, D.07 "
          "(<code>111000</code>/<code>000111</code>).")]))

    s.append("""<p>The lesson generalises past 8b/10b: <b>every scheme for not writing
    something down twice encodes an assumption about why the two copies agree.</b> When
    that assumption is right, the scheme removes a whole class of error &mdash; the
    register-map generator of Part&nbsp;Z4 and the single-C++-source flow of
    Part&nbsp;Z14 both work exactly this way. When it is wrong, it replaces typos with a
    <em>systematic</em> error, which is much harder to see, because every instance is
    wrong in the same plausible way.</p>

    <p>The difference between the two cases is not cleverness. It is whether you checked.</p>""")

    s.append("<h2>Z21.5 The provenance ledger</h2>")
    s.append("""<p>The repository already requires this for paper citations
    (Gate&nbsp;G022): every claim carries how well it was verified. Protocol constants get
    the same treatment, because they are the same kind of claim.</p>""")

    s.append(tab("Confirmation level for every constant in edu/proto",
        ["Constant", "Level", "What that means here"],
        [["8b/10b 5b/6b and 3b/4b tables", "<b>property-proven, not source-verified</b>",
          "All four defining properties hold exhaustively over all 528 codewords and "
          "every codeword pair. The normative tables were not available for comparison."],
         ["8b/10b well-known codewords (K.28.5, D21.5, D10.2, &hellip;)",
          "<b>corroborated</b>",
          "Seven widely-quoted codewords match exactly. Weak evidence &mdash; the same "
          "memory produced both &mdash; but it is independent of the property proof."],
         ["K.28.x selection (K.23.7 etc. omitted)", "<b>scoped out, deliberately</b>",
          "Only K.28.x is implemented. Stated in the datasheet rather than left for a "
          "customer to discover."],
         ["24+6 ECC parity masks", "<b>constructed, explicitly not MIPI</b>",
          "A valid SEC-DED built from first principles and proven exhaustively. It is "
          "<b>not</b> byte-compatible with CSI-2 and the header of "
          "<code>ecc24.h</code> says so in the first paragraph."],
         ["Ethernet FCS CRC-32 (Part Z1)", "<b>independently verified</b>",
          "Checked against Python's <code>zlib.crc32</code>, an implementation written by "
          "somebody else from the standard. This is the strongest level available and it "
          "is available only because a free reference implementation exists."]]))

    s.append("""<p>Notice how much the last row differs from the rest. Ethernet's CRC-32
    is fully pinned down not because the Ethernet standard is easier to read, but because
    <b>somebody shipped a free, widely-used implementation of it</b>. When you are
    choosing which protocol block to build first as a one-person house, the existence of
    an independent reference implementation is worth more than the clarity of the
    specification &mdash; it is the difference between &ldquo;proven&rdquo; and
    &ldquo;argued&rdquo;.</p>""")

    s.append("<h2>Z21.6 What to write in the datasheet</h2>")
    s.append("""<p>All of the above is worthless if it stays in a commit message. The
    boundary between proven and assumed belongs on the page the customer reads, phrased
    without hedging:</p>""")

    s.append("<pre><code>" + E("""## 확인 수준 (Verification status)

이 블록은 다음을 **전수로** 확인했다:
  * 코드워드 528 개가 RD 마다 서로 다르다 (전단사)
  * running disparity 가 -1 / +1 을 벗어나지 않는다
  * 같은 비트가 5 개를 넘게 이어지지 않는다 -- **코드워드 이음 전부에서**
  * 콤마 무늬가 데이터 흐름에 나타나지 않는다

이 블록은 다음을 **확인하지 못했다**:
  * IEEE 802.3 Clause 36 Table 36-1/36-2 와 바이트까지 같은가
    -> 상호운용 시험 전에 그 표로 대조할 것.  구조는 그대로 쓸 수 있고
       바꿀 곳은 `enc8b10b.v` 의 case 문 두 개뿐이다.
  * K.23.7 · K.27.7 · K.29.7 · K.30.7 (일부러 뺐다)
  * 복호기 (이 판은 부호기만이다)""") + "</code></pre>")

    s.append("""<p>A customer who reads that knows exactly what they are buying and what
    work remains. A customer who reads &ldquo;IEEE 802.3 compliant&rdquo; on a block that
    was never compared to IEEE 802.3 finds out later, and tells other people.</p>

    <p>There is a commercial argument here too, and it is not the obvious one. Publishing
    the boundary does not make the block look weaker &mdash; it makes it look
    <em>measured</em>, and it is the only version of the claim that survives contact with
    a reviewer. Every vendor says &ldquo;compliant&rdquo;. Almost none says which of their
    properties were checked by enumeration and which by reading.</p>""")

    return "\n".join(s)
