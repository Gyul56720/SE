# -*- coding: utf-8 -*-
"""Volume III, Part Z23 -- The packet header ECC, and why headers get more than payloads."""
import sys, os, json
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, derive
import sch

PROTO = "/home/user/SE/edu/proto"
잰것 = json.load(open(os.path.join(PROTO, "잰것.json"), encoding="utf-8"))
EC = 잰것["ecc24"]


def _c(s):
    return "<pre><code>" + E(s) + "</code></pre>"


def ch_ecc():
    s = ['<h1 id="z23">Z23. The Packet Header ECC &mdash; Why Headers Get More Than '
         'Payloads</h1>']

    s.append("""<p>A MIPI CSI-2 short packet is four bytes: one Data Identifier, two Word
    Count, one ECC. A long packet adds a payload and a 16-bit CRC at the end. So the
    header gets an <b>error-correcting</b> code and the payload gets a merely
    <b>error-detecting</b> one, and the header's code costs a quarter of the header's own
    size.</p>

    <p>That asymmetry looks wasteful until you ask what each failure costs. This part
    builds the header code, proves it, and puts it on silicon.</p>""")

    s.append("<h2>Z23.1 Why the header is worth more protection</h2>")
    s.append(fig(sch.블록도([
        ["Sensor", "CSI-2 TX", "D-PHY lanes", "CSI-2 RX", "ISP"],
    ], 칸=118, 설명={
        "CSI-2 TX": "패킷을 만든다\n헤더+ECC, 페이로드+CRC",
        "D-PHY lanes": "차동 1~4 레인\n여기서 비트가 깨진다",
        "CSI-2 RX": "★ 이 장의 블록\n헤더를 먼저 푼다",
        "ISP": "영상 처리\n디모자이크 등",
    }), """The camera path. The receiver must read Word Count out of the header to know
    where the payload ends &mdash; and therefore where the <i>next</i> packet begins."""))

    s.append(derive("Why a 1-bit header error is not a 1-bit problem",
        [("The header's Word Count says how many payload bytes follow.",
          "The receiver has no other way to find the packet boundary; CSI-2 packets are "
          "not self-delimiting."),
         ("A single bit flipped in Word Count changes that length &mdash; by 1, or by "
          "32768 if it lands in the top bit.",
          "Binary weighting means the damage is not proportional to the number of bits "
          "flipped."),
         ("The receiver then looks for the next packet header at the wrong offset.",
          "It reads payload bytes as a header, whose ECC will not check, whose Word Count "
          "is garbage."),
         ("<b>The error does not stop.</b> Every subsequent packet in the frame is "
          "misaligned.",
          "One bit has cost an entire video frame, and possibly re-synchronisation time "
          "beyond it."),
         ("Whereas a single bit flipped in the payload corrupts one pixel.",
          "The CRC flags the packet as bad; the frame is imperfect but its structure "
          "survives. An ISP can interpolate one pixel."),
         ("Therefore: correct the header, merely detect on the payload.",
          "The cost asymmetry is thousands to one, so the protection asymmetry is "
          "justified. This is the same reasoning that puts ECC on DRAM address lines "
          "before data lines.")]))

    s.append("<h2>Z23.2 What SEC-DED means, precisely</h2>")
    s.append(tab("Three codes, three guarantees",
        ["Code", "1-bit error", "2-bit error", "Cost for 24 data bits"],
        [["Parity (1 bit)", "detected", "<b>missed</b>", "1 bit"],
         ["Hamming SEC (5 bits)", "<b>corrected</b>",
          "<b>miscorrected</b> &mdash; silently turned into a 3-bit error", "5 bits"],
         ["Extended Hamming SEC-DED (6 bits)", "<b>corrected</b>",
          "detected, <b>not</b> corrected", "6 bits"]]))

    s.append("""<p>The middle row is the trap, and it is why the sixth bit is not
    optional. A plain Hamming code always produces a syndrome that names some bit, so
    given a 2-bit error it confidently flips a third one. You end up worse off than with
    no ECC at all. The extra overall-parity bit is what lets the decoder say &ldquo;I do
    not know&rdquo; &mdash; the same distinction this repository insists on everywhere
    else, here implemented in six wires.</p>""")

    s.append(ex("How one extra bit buys double-error detection",
        given="5 Hamming parity bits give each of the 30 bit positions a distinct 5-bit "
              "syndrome. Add a 6th bit that is the parity of the entire codeword.",
        method="Work out what each error class does to the syndrome and to the overall "
               "parity, separately.",
        numbers="A <b>single</b> error flips an odd number of bits, so overall parity "
                "becomes 1, and the syndrome is non-zero and names the bit. A "
                "<b>double</b> error flips an even number, so overall parity returns to "
                "0, while the syndrome (the XOR of two distinct non-zero syndromes) is "
                "still non-zero. So <i>syndrome non-zero with parity 0</i> is a signature "
                "no single error can produce.",
        trap="The decoder must compute overall parity <b>directly from the received "
             "codeword</b>, not by re-encoding the received data and comparing the 6th "
             "bit. Re-encoding folds the syndrome's own parity into the comparison: the "
             "result is 1&nbsp;XOR&nbsp;parity(syndrome), which is 0 for every data bit "
             "whose syndrome has odd weight. Measured &mdash; the first version of "
             "<code>ecc24_dec</code> did exactly this and reported <b>90 of 180 single "
             "errors as double errors</b>, i.e. refused to correct half of the "
             "correctable ones.",
        extra="That bug is instructive because it is <i>conservative</i>: it never "
              "corrupts data, it just declines to fix things it could have fixed. In the "
              "field it would look like an unexplained doubling of the dropped-frame "
              "rate, with no corrupted output to point at &mdash; the kind of defect that "
              "gets blamed on the cable for a year."))

    s.append("<h2>Z23.3 Constructing the code</h2>")
    s.append("""<p>Part&nbsp;Z21 explained why the remembered MIPI parity masks were
    discarded: counted before use, they produced %s. So the code here is built from first
    principles instead, and is <b>not</b> byte-compatible with CSI-2. The construction is
    four lines:</p>""" % EC.get("_", "27 distinct syndromes out of the 30 required"))

    s.append(_c("""# 24 데이터 비트에 신드롬을 배정한다.
# 무게 1 짜리 패턴은 **패리티 비트 자신의 오류**가 쓰므로 데이터에 주면 안 된다.
cand = [s for s in range(1, 32) if bin(s).count('1') >= 2]   # 26 개
syn  = cand[:24]                                             # 24 개만 쓴다

# 패리티 i 의 마스크 = 신드롬의 i 번째 비트가 1 인 데이터 비트들
masks = [[b for b in range(24) if (syn[b] >> i) & 1] for i in range(5)]""")) 

    s.append(derive("Why the syndromes must have weight &ge; 2",
        [("Each parity bit can itself be corrupted in transit.",
          "The ECC field travels over the same lanes as the data."),
         ("If parity bit <i>i</i> flips, the recomputed syndrome is 2<sup><i>i</i></sup> "
          "&mdash; a weight-1 pattern.",
          "Only that one parity check disagrees."),
         ("So the five weight-1 patterns are already spoken for, and no data bit may be "
          "assigned one.",
          "Otherwise a flipped parity bit and a flipped data bit look identical, and the "
          "decoder corrupts good data trying to fix a parity bit that nothing depends on."),
         ("Of the 31 non-zero 5-bit patterns, 26 have weight &ge; 2, and we need 24.",
          "It fits, with two spare. Had we needed 27 data bits, 5 parity bits would not "
          "have been enough."),
         ("Verified rather than argued: all 29 syndromes distinct, none zero, no "
          "double-error syndrome colliding with a single-error syndrome.",
          "%s" % EC["성질전수확인"]["신드롬_서로다름"])]))

    s.append("<h2>Z23.4 Proven exhaustively</h2>")
    p = EC["성질전수확인"]
    s.append(tab("edu/proto/ecc_check.cpp",
        ["Case", "Enumerated", "Result"],
        [["No error", "6 representative data values",
          "all report ECC_OK, data unchanged"],
         ["Single error", "%d (30 bit positions &times; 6 data values)" % p["단일오류"]["본것"],
          "<b>%d</b> wrong &mdash; every one corrected" % p["단일오류"]["틀림"]],
         ["Double error", "%d (all C(30,2) pairs &times; 6 data values)"
          % p["이중오류"]["본것"],
          "<b>%d</b> detected, <b>%d</b> miscorrections"
          % (p["이중오류"]["검출"], p["이중오류"]["오정정"])],
         ["Not degenerate", "20,000 random headers",
          "<b>%d</b> of 64 possible ECC values seen" % p["ECC값가지수"]]]))

    s.append("""<p>Six representative data values rather than all 2<sup>24</sup>, because
    the code is <b>linear</b>: the syndrome of a corrupted codeword depends only on the
    error pattern, not on the data underneath it. That is a property worth stating rather
    than assuming, so the six values span all-zeros, all-ones and four irregular patterns,
    and they all agree &mdash; which is the evidence that linearity holds in the
    implementation and not merely in the theory.</p>""")

    s.append("<h2>Z23.5 The circuit is a pile of XOR trees</h2>")
    s.append(_c("""// `^(vector)` 는 리덕션 XOR -- 모든 비트를 XOR 한다.
// 이 한 글자가 14입력 XOR 나무 하나다.  C++ 에는 이런 연산자가 없다.
wire [4:0] p;
assign p[0] = ^(data_in & M0);
assign p[1] = ^(data_in & M1);
assign p[2] = ^(data_in & M2);
assign p[3] = ^(data_in & M3);
assign p[4] = ^(data_in & M4);
wire p5 = (^data_in) ^ (^p);

// 신드롬 -> 비트 자리.  각 데이터 비트의 신드롬은 그 비트가 어느 마스크에
// 들어 있는가로 정해진다.  전부 상수라 합성기가 통째로 푼다.
genvar g;
generate
    for (g = 0; g < 24; g = g + 1) begin : gen_fix
        wire [4:0] s_g = { M4[g], M3[g], M2[g], M1[g], M0[g] };
        assign fix[g] = (syn == s_g) & opar & (syn != 5'd0);
    end
endgenerate
assign data_fixed = data_in ^ fix;"""))

    s.append("""<p>Three things in that fragment are worth naming. The reduction XOR
    (<code>^vector</code>) has no C++ equivalent and collapses a 14-input parity tree into
    one character &mdash; Part&nbsp;Z18.6 lists the others. The
    <code>generate</code> loop builds 24 comparators whose right-hand sides are all
    compile-time constants, so synthesis evaluates <code>s_g</code> away entirely and what
    remains is 24 five-bit constant comparisons. And the block is named
    (<code>gen_fix</code>) because an unnamed generate block gets called
    <code>genblk1</code>, and every constraint and waveform that references it breaks the
    day somebody inserts another loop above it.</p>""")

    s.append("<h2>Z23.6 What it costs</h2>")
    a = EC["면적"]
    s.append(tab("Synthesis, iCE40 HX8K",
        ["Measure", "Value", "Note"],
        [["Cells", str(a["cells"]), "yosys <code>synth_ice40</code>"],
         ["SB_LUT4", str(a["SB_LUT4"]), "All of them &mdash; pure combinational logic"],
         ["Flip-flops", str(a["플립플롭"]), a["뜻"]],
         ["Verilator <code>-Wall</code>", "0 warnings", "Clean"],
         ["RTL vs C++ golden", "%d vectors, %d wrong"
          % (EC["RTL회귀"]["벡터"], EC["RTL회귀"]["틀림"]),
          "Stimulus mixes no-error, single-error and double-error 1:1:1"],
         ["Self-check", EC["RTL회귀"]["자해검사"],
          "Corrupting one golden value makes the comparison fail"]]))

    s.append("""<p>%d LUTs, zero flip-flops, and it corrects any single-bit error in a
    camera packet header. For comparison the 8b/10b encoder of Part&nbsp;Z22 is %d LUTs.
    Both are small enough that the interesting engineering is entirely in the verification
    and the specification, not in the gates &mdash; which is the usual situation for
    protocol IP and the reason Parts&nbsp;Y and&nbsp;Z4 spend so much more time on
    deliverables than on RTL.</p>""" % (a["SB_LUT4"], 잰것["enc8b10b"]["면적"]["SB_LUT4"]))

    s.append("""<p>The stimulus mix in that table is the part most easily got wrong. A
    regression built from random headers contains <b>no bit errors at all</b>, so it
    exercises only the <code>ECC_OK</code> path &mdash; the correction logic, which is the
    entire point of the block, would never run. Errors have to be <em>injected</em>, and
    injected in the proportions you care about.</p>""")

    s.append("<h2>Z23.7 Swapping in the real masks</h2>")
    s.append("""<p>Because the construction is separated from the structure, making this
    block CSI-2 interoperable is a table change, not a redesign:</p>""")

    s.append(tab("What changes, and what does not",
        ["Item", "Changes?"],
        [["<code>ECC_MASK[5]</code> in <code>ecc24.h</code>", "<b>Yes</b> &mdash; five constants"],
         ["<code>M0</code>&ndash;<code>M4</code> in <code>ecc24.v</code>",
          "<b>Yes</b> &mdash; the same five values"],
         ["Encoder, decoder, syndrome decode, correction logic", "No"],
         ["<code>ecc_check.cpp</code> and all four proofs", "No &mdash; re-run them"],
         ["Testbench and golden generator", "No"],
         ["Area, timing, interface", "No"]]))

    s.append("""<p>And the proofs are exactly what you re-run after the swap, because a
    transcription error in five hex constants is precisely the failure this part opened
    with. The value of having built the harness first is that checking somebody else's
    constants costs one command.</p>""")

    return "\n".join(s)
