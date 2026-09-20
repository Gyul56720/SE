# -*- coding: utf-8 -*-
"""T8 -- The serial link: measured with this repository's own channel model.

수는 전부 `serdes.링크()` 와 `serdes.커서들()` 을 **돌려서** 얻었다.  이 장의
표를 다시 내려면 `edu/측정/serdes_표.py` 를 돌린다.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

# --- 잰 것 (serdes.링크, PRBS, 씨앗 1·2·3 합산) ---------------------------
# 표본 수는 씨앗 셋을 합쳐 420,000 비트(구성 비교) / 630,000 비트(성한 동작점).
잰BER = {
    (10, "none"): (1, 420000), (10, "CTLE"): (0, 420000),
    (10, "CTLE+FFE3"): (0, 420000), (10, "CTLE+FFE3+DFE4"): (0, 420000),
    (20, "none"): (56704, 420000), (20, "CTLE"): (3201, 420000),
    (20, "CTLE+FFE3"): (2601, 420000), (20, "CTLE+FFE3+DFE4"): (1616, 420000),
    (30, "none"): (113102, 420000), (30, "CTLE"): (94687, 420000),
    (30, "CTLE+FFE3"): (104321, 420000), (30, "CTLE+FFE3+DFE4"): (103552, 420000),
}
잰SNR쓸기 = {26: (2226, 630000), 30: (9, 630000), 34: (0, 630000), 38: (0, 630000)}
잰성한점 = {"none": (81496, 630000), "CTLE": (40, 630000),
          "CTLE+FFE5": (0, 630000), "CTLE+FFE5+DFE6": (0, 630000)}
잰커서 = {                      # 메인, 선행1, 후행1, ISI 합, peak-distortion 눈높이
    10: (3.3876, 0.3476, 1.3286, 4.2336, -1.6921),
    20: (1.6929, 0.5473, 1.0346, 5.4439, -7.5021),
    30: (0.9185, 0.4871, 0.7437, 5.6809, -9.5247),
}


def _ber(t):
    오류, 비트 = t
    if 오류 == 0:
        return (f"&lt; {수(3.0/비트, 3)} <span style='color:#888'>"
                "(0 errors, rule of three)</span>")
    return 수(오류 / 비트, 3)


def ch_serdes():
    c = 장(
        "T8", "The Serial Link — Measured, Including Where It Does Not Work",
        "A link is the one block where the channel is someone else's problem and "
        "entirely your responsibility.",
        쓰는것=["전압", "주파수", "위상", "확률", "표준편차", "로그", "적분",
              "SNR", "구경지터", "위상잡음", "적분지터", "루프대역폭",
              "엘리어싱", "ENOB", "열잡음"],
        내놓는것=["심볼간간섭", "펄스응답", "커서", "선행커서", "후행커서",
                "최악왜곡", "아이다이어그램", "CTLE", "FFE", "DFE",
                "오류전파", "비트오류율", "3의법칙", "클럭데이터복원",
                "지터허용", "PAM4"],
        특허="""Link patents concentrate where the loop is: speculative (unrolled) DFE
        that removes the feedback multiply from the critical path; adaptation schemes
        that converge without a training sequence; CDR phase detectors that tolerate
        more ISI; and, lately, ADC-based receivers whose equalisation is entirely
        digital. <b>This repository's own research sits in that first family</b>, and
        the argument there is the one from T2: the invention is <i>where the delay was
        moved</i>, not how fast the transistor is.""")

    c.글("""Everything in a serial link is a consequence of one fact: the channel is a
    low-pass filter with far less bandwidth than the symbol rate, so each symbol arrives
    smeared across its neighbours. The receiver's job is to undo that smearing well
    enough that a slicer can decide, and the measurements below — run with this
    repository's own channel and link model — show both how much equalisation buys and,
    more usefully, <b>where it buys nothing at all</b>.""")

    # ------------------------------------------------------------------
    c.절("T8.1 The pulse response, and the numbers that come out of it")

    c.날것(정의("커서 (cursor)",
        "The samples of the channel's pulse response taken at symbol intervals. The "
        "<b>main cursor</b> is the one the slicer uses; everything before it is a "
        "<b>pre-cursor</b> and everything after a <b>post-cursor</b>. The sum of the "
        "magnitudes of all non-main cursors is the worst-case ISI."))

    c.날것(표("Measured pulse response of this model's channel (sps = 8)",
        ["Loss", "Main", "Pre-cursor 1", "Post-cursor 1", "Σ|ISI|",
         "Worst-case eye"],
        [[수(l, 3, "dB"), 수(m, 4), 수(pre, 4), 수(post, 4), 수(isi, 4),
          f"<b>{수(eye,4)}</b>"]
         for l, (m, pre, post, isi, eye) in sorted(잰커서.items())]))

    c.날것(짚기(f"""Read the last column carefully. At <b>every</b> loss — including
    {수(10,2,'dB')}, where the link runs essentially error-free — the worst-case eye is
    <b>negative</b>. That is not a contradiction: worst-case (peak-distortion) analysis
    assumes the data pattern that maximises every interferer simultaneously, and that
    pattern is astronomically rare. <b>Peak distortion is a bound, not a prediction.</b>
    A design signed off on it alone is over-designed; a design that ignores it has no
    bound at all. Both numbers belong in the deliverable."""))

    c.날것(유도("Why loss shows up as post-cursors, and why that matters", [
        ("A lossy channel attenuates high frequencies more than low ones.",
         "Skin effect (∝√f) and dielectric loss (∝f). Both are physics of the medium, "
         "not of the driver."),
        ("A sharp edge is therefore spread in time: the pulse response develops a long "
         "tail.",
         f"Measured at {수(20,2,'dB')}: the first post-cursor is {수(잰커서[20][2],4)} "
         f"against a main cursor of {수(잰커서[20][0],4)} — "
         f"<b>{수(잰커서[20][2]/잰커서[20][0]*100,3,'%')} of the signal arrives one "
         "symbol late</b>."),
        ("The tail is <i>causal and past</i> — it depends on symbols already decided.",
         "That is exactly what makes a decision-feedback equaliser possible: the "
         "receiver already knows those bits, so it can subtract their contribution "
         "without amplifying noise."),
        ("Pre-cursors are not, so they can only be handled by a filter that looks "
         "<i>ahead</i> — an FFE, which is linear and therefore amplifies noise along "
         "with signal.",
         f"Measured pre-cursor at {수(20,2,'dB')} is {수(잰커서[20][1],4)}, a third of "
         "the post-cursor. This asymmetry is why receivers use both kinds of "
         "equaliser rather than one."),
    ]))

    # ------------------------------------------------------------------
    c.절("T8.2 What each equaliser actually buys — measured")

    c.날것(표("BER against channel loss and equalisation (SNR = 26 dB, PRBS, "
             "seeds 1·2·3 combined, 420,000 bits per cell)",
        ["Loss", "No EQ", "CTLE 6 dB", "+ FFE 3", "+ DFE 4"],
        [[수(l, 3, "dB")] + [_ber(잰BER[(l, k)])
                            for k in ("none", "CTLE", "CTLE+FFE3", "CTLE+FFE3+DFE4")]
         for l in (10, 20, 30)]))

    c.날것(사고(f"""<b>The 30 dB row is not a result — it is a broken operating point.</b>
    Every configuration sits at a BER of roughly {수(0.25,2)}, which is what a slicer
    does when the eye is fully closed: it guesses. Comparing equalisers there is
    comparing coin flips, and the apparent finding that FFE is <i>worse</i> than CTLE
    alone ({수(잰BER[(30,'CTLE+FFE3')][0]/잰BER[(30,'CTLE+FFE3')][1],3)} against
    {수(잰BER[(30,'CTLE')][0]/잰BER[(30,'CTLE')][1],3)}) is noise, not physics.
    <p>This repository has a rule for exactly this, learned the hard way: <b>check the
    operating point is healthy before reporting anything measured on it.</b> A BER near
    0.5, an equaliser that did not converge, a wrong sampling phase — all of them
    produce numbers that look like data.</p>"""))

    c.날것(표(f"Finding a healthy operating point: SNR sweep at {수(20,2,'dB')} loss "
             "with CTLE + FFE 5 + DFE 6 (630,000 bits per row)",
        ["SNR", "Errors", "BER"],
        [[수(s, 3, "dB"), str(t[0]), _ber(t)] for s, t in sorted(잰SNR쓸기.items())]))

    c.날것(표(f"The same comparison at a <b>healthy</b> operating point "
             f"({수(20,2,'dB')} loss, SNR = {수(34,2,'dB')})",
        ["Configuration", "Errors", "BER"],
        [[k, str(v[0]), _ber(v)] for k, v in 잰성한점.items()]))

    c.날것(개념(
        "3의법칙 (rule of three) — what zero errors is allowed to mean",
        f"""<p>Two rows above report <b>zero errors</b>. Zero errors is not a BER of
        zero; it is an upper bound. With no errors in n bits, the 95 % confidence upper
        bound on the error rate is 3/n — the <b>rule of three</b>. For the
        {수(630000,6)}-bit runs that is {수(3/630000,3)}.</p>
        <p>So the measurement says CTLE + FFE and CTLE + FFE + DFE are both below
        {수(3/630000,3)}, and it says <b>nothing about which is better</b>. Reporting
        that DFE 'made no difference' would be a claim the data does not support; the
        honest statement is that this run could not distinguish them, and that
        distinguishing them needs roughly 100× more bits or a worse channel.</p>""",
        어디에="Every BER measurement, every compliance report, and every datasheet line "
             "that contains the letters BER.",
        언제="Whenever the error count is small — which, for any link worth shipping, "
            "is always.",
        어떻게="Report errors and bits, not just the ratio. If errors = 0, quote the "
             "3/n bound and the confidence level. To claim 1e-12 you must observe at "
             "least 3e12 bits, which at 25 Gb/s is two minutes — and at 1e-15, a day.",
        산업코드="""# The line that belongs in every link report.
#   errors = 0 in 6.30e5 bits  ->  BER < 4.8e-6 (95% confidence, rule of three)
# NOT "BER = 0".
def ber_bound(errors, bits, conf=0.95):
    if errors == 0:
        import math
        return -math.log(1 - conf) / bits        # 3.0/bits at 95%
    return errors / bits                         # point estimate; add a CI for small n
# And the check that catches the broken operating point before any of this matters:
assert 0.0 <= ber < 0.2, f"BER {ber} -- the eye is closed; this run measured nothing" """,
        주의="""A BER of exactly 0.5 usually means a polarity or alignment bug, not a
            bad channel — the receiver is comparing against an inverted or misaligned
            reference. A BER near 0.25 with PAM4 means the same thing one level up.
            <b>Check for these before blaming the equaliser</b>: they are far more
            common than a genuinely closed eye."""))

    # ------------------------------------------------------------------
    c.절("T8.3 The three equalisers, and the one that can make things worse")

    c.날것(표("What each equaliser does to signal and to noise",
        ["", "CTLE", "FFE", "DFE"],
        [["Where", "Analog, before sampling", "Analog or digital, linear FIR",
          "After the slicer, feedback"],
         ["Handles", "Broad high-frequency loss", "Pre- and post-cursors",
          "<b>Post-cursors only</b>"],
         ["Noise", "Amplifies it with the signal",
          "Amplifies it — gain at high frequency is noise gain",
          "<b>Does not</b> — it subtracts known symbols"],
         ["Cost", "Small; a few devices and a peaking network",
          "Taps × multipliers; the tap count grows with the tail",
          "A multiply-add <b>inside one symbol period</b> — the timing wall of T2"],
         ["Fails when", "The loss is not a smooth slope (reflections)",
          "Noise is already the limit", "A wrong decision propagates (error burst)"]]))

    c.날것(개념(
        "오류전파 (error propagation), and why DFE is still worth it",
        """<p>A DFE subtracts the contribution of symbols it has already decided. If a
        decision is wrong, it subtracts the wrong thing, which makes the next decision
        more likely to be wrong — errors arrive in bursts rather than singly.</p>
        <p>The effect is real and it is smaller than intuition suggests: for a
        one-tap DFE the burst length is short because the error has to survive the next
        correct decision. What matters downstream is not the BER but the <b>burst
        structure</b>, because the FEC that follows was designed for a burst length. A
        link that meets its BER and violates the assumed burst distribution will fail
        after decoding while every pre-FEC measurement looks fine.</p>""",
        어디에="Every receiver above ~10 dB of loss, and every conversation with the "
             "FEC designer.",
        언제="Whenever the post-cursor tail is significant relative to the main cursor — "
            f"at {수(20,2,'dB')} in this model the first post-cursor alone is "
            f"{수(잰커서[20][2]/잰커서[20][0]*100,3,'%')} of the main.",
        어떻게="Measure the burst-length distribution, not just BER, and hand it to "
             "whoever sizes the interleaver. Unrolling (speculation) removes the "
             "feedback multiply from the critical path — the T2 argument — at the cost "
             "of 2<sup>k</sup> parallel slicers for k unrolled taps.",
        산업코드="""// Unrolled (speculative) first DFE tap: both outcomes are precomputed,
// and the previous decision only selects. The multiply leaves the loop.
always_comb begin
    d_if_prev0 = (sample >  +c1) ;      // precomputed thresholds
    d_if_prev1 = (sample >  -c1) ;
end
always_ff @(posedge clk) prev <= prev ? d_if_prev1 : d_if_prev0;   // 2:1 mux only
// The loop now contains a mux and a flop instead of a multiply-add.
// Cost: one extra slicer per unrolled tap, and 2^k for k taps.""",
        주의="""Unrolling is only a win if the loop was the critical path. Measure first:
            in this repository's own measurement of a DFE at a realistic operating point
            the feedback taps were |c| ≤ 0.041 — <b>the loop was idle</b>, and the real
            critical path was the slicer. Optimising an idle loop is the most expensive
            kind of correct work."""))

    # ------------------------------------------------------------------
    c.절("T8.4 Recovering the clock, and the jitter that decides whether you can")

    c.날것(개념(
        "클럭데이터복원 (CDR) — the PLL of T7 with the data as its reference",
        """<p>There is no separate clock wire. The receiver extracts timing from the
        data's own transitions using a phase detector (Alexander/bang-bang, or a linear
        Mueller-Müller) driving the same second-order loop as T7. Everything from that
        chapter applies, with two changes: the 'reference' arrives only when the data
        transitions, and the loop must <b>track</b> the transmitter's spread-spectrum
        modulation while <b>rejecting</b> high-frequency jitter.</p>
        <p>That is the jitter tolerance mask: below the CDR bandwidth the receiver
        follows the jitter (so large amplitudes are tolerated); above it, the receiver
        cannot follow and the jitter eats the eye directly.</p>""",
        어디에="Every receiver in every serial standard — PCIe, USB, Ethernet, MIPI, "
             "SATA, HDMI.",
        언제="CDR bandwidth is fixed by the standard's jitter-tolerance mask and by the "
            "spread-spectrum profile it must track; it is not a free parameter.",
        어떻게="Take the standard's mask, place the CDR bandwidth so the tolerance curve "
             "sits above it with margin, and check that the transmit PLL's jitter "
             "(T7) plus the residual falls inside the budget.",
        산업코드="""# The budget is a SUM, and each term has an owner.
#   TX PLL jitter (T7)          0.30 ps rms   <- clock design
#   TX driver / ISI (DJ)        0.15 UI pp    <- output stage and package
#   Channel ISI residual        0.20 UI pp    <- equalisation, this chapter
#   RX CDR tracking error       0.05 UI pp    <- loop bandwidth
#   Sampler aperture (T5)       0.10 ps rms   <- sampling network
# Random terms add in QUADRATURE, deterministic ones LINEARLY -- mixing the two
# rules is the most common budgeting error, and it always errs optimistic.""",
        주의="""Spread-spectrum clocking is a <b>requirement to track</b>, not a
            disturbance to reject: a CDR whose bandwidth is too low to follow a 33 kHz
            SSC profile loses lock on a compliant transmitter. A receiver that works on
            the bench with a clean generator and fails against real hosts is usually
            this."""))

    # ------------------------------------------------------------------
    c.절("T8.5 What to do with this on Monday")

    c.날것(쓰는자리([
        ["펄스응답 · 커서 · 최악왜곡", "Before choosing any equaliser",
         "How many taps of what kind — and the bound that goes in the datasheet"],
        ["CTLE · FFE · DFE", "Receiver architecture",
         "Noise amplification versus error propagation, and the timing wall"],
        ["3의법칙", "Every BER number you report",
         "Whether the measurement supports the claim at all"],
        ["오류전파", "The interface with FEC",
         "Interleaver depth — the number the FEC designer needs from you"],
        ["클럭데이터복원 · 지터허용", "Compliance",
         "CDR bandwidth, which the standard has already chosen for you"]]))

    c.글(f"""Two measured results to carry. At {수(20,2,'dB')} of loss and
    SNR {수(34,2,'dB')}, CTLE alone takes the link from
    {_ber(잰성한점['none']).split(' ')[0]} to
    {_ber(잰성한점['CTLE']).split(' ')[0]} — a factor of about
    {수(잰성한점['none'][0]/max(1,잰성한점['CTLE'][0]),3)} — and adding FFE pushes it
    below what {수(630000,6)} bits can resolve. And at {수(30,2,'dB')} of loss with the
    same SNR, <b>no equaliser does anything at all</b>, because the operating point
    itself is broken. Reporting the second table without that sentence would be the
    exact failure this book's rules exist to prevent.""")

    c.글("""The next chapter goes underneath the model used here and asks where the
    channel's loss actually comes from — and what a package, a via and a connector do to
    the numbers above.""")

    return c.완성()
