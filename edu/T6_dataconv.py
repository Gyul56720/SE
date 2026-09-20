# -*- coding: utf-8 -*-
"""T6 -- Data converters: the same limits, spent differently."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

k볼츠만 = 1.380649e-23
T상온 = 300.0
VFS = 1.0
CU = 1e-15                 # F, 잘 맞는 단위 커패시터의 현실적인 하한


def _허용정합(N):
    """3σ DNL < 0.5 LSB 를 만족하는 단위 커패시터 상대 표준편차."""
    return 0.5 / (3 * math.sqrt(2 ** N - 1))


def _정합총C(N, Cu=CU):
    return Cu * 2 ** N


def _잡음총C(N, VFS=VFS):
    """kT/C 만 보면 이만큼이면 된다 (양자화 잡음과 같아지는 점)."""
    LSB = VFS / 2 ** N
    return 12 * k볼츠만 * T상온 / LSB ** 2


def ch_dataconv():
    c = 장(
        "T6", "Data Converters — Where Each Architecture Spends the Same Limits",
        "No architecture beats kT/C, jitter or mismatch. They differ in which one they "
        "pay first, and that is the entire basis on which you choose.",
        쓰는것=["전압", "전류", "전하", "확률", "표준편차", "로그", "SNR",
              "SNDR", "ENOB", "kTC잡음", "구경지터", "표본화정리",
              "오버샘플링비", "잡음성형", "차지인젝션", "정적잡음여유"],
        내놓는것=["플래시ADC", "축차비교ADC", "파이프라인ADC", "시간인터리브",
                "용량DAC", "전류구동DAC", "세그먼테이션", "INL", "DNL",
                "미싱코드", "단조성", "중복성", "디지털보정", "글리치에너지",
                "정합"],
        특허="""Converter patents cluster in three places and the pattern is worth
        seeing: <b>switching schemes</b> that lower the energy of a SAR's capacitive DAC
        (monotonic, split-cap, V<sub>cm</sub>-based — all the same array, switched
        differently); <b>calibration</b> that measures a physical error once and
        subtracts it in the digital domain forever; and <b>interleaving corrections</b>
        for gain, offset and timing skew between slices. All three share a shape:
        <i>accept the analog error and remove it somewhere cheaper.</i> That is the most
        reliably patentable idea in mixed-signal design, and it is available in almost
        every block.""")

    c.글("""Converter architecture looks like a catalogue and is really a single
    question: given a resolution and a sample rate, which fundamental limit do you hit
    first, and which architecture lets you pay that one in the currency you have? Every
    architecture faces the same kT/C, the same jitter, the same mismatch. What differs
    is how many times per conversion each limit is paid.""")

    # ------------------------------------------------------------------
    c.절("T6.1 The map, and what sets each boundary")

    c.날것(표("The four architectures, and the limit that stops each",
        ["Architecture", "Comparisons per sample", "Practical range",
         "What stops it"],
        [["Flash", "2<sup>N</sup> − 1 in parallel",
          "4–8 b, up to tens of GS/s",
          "Area and input capacitance double per bit; 2<sup>N</sup> comparator offsets "
          "must each be < ½ LSB"],
         ["SAR", "N in series (one per cycle)",
          "8–14 b, up to ~100 MS/s per slice",
          "The DAC settling chain: N settlings per sample, each to the full accuracy"],
         ["Pipeline", "~1.5 b per stage, concurrent",
          "10–16 b, 50 MS/s–1 GS/s",
          "Inter-stage gain accuracy and the op-amp that provides it"],
         ["ΔΣ", "1 (or few) at OSR× the rate",
          "16–24 b, kHz–MHz bandwidth",
          "Loop stability and the OSR the process can clock"],
         ["Time-interleaved", "M slices of any of the above",
          "Extends speed, not resolution",
          "<b>Mismatch between slices</b> — gain, offset and sampling-instant skew "
          "appear as spurs at f<sub>s</sub>/M"]]))

    c.날것(짚기("""The last row is the one that surprises people. Interleaving M slices
    multiplies throughput by M and leaves resolution <i>worse</i>, because three new
    error terms appear that do not exist in a single converter. Timing skew between
    slices is the hardest: it is a jitter problem (T5) that is <b>deterministic</b>, so
    it produces spurs rather than a noise floor, and a spur at a predictable frequency
    is exactly what a customer's spectrum plot will show."""))

    # ------------------------------------------------------------------
    c.절("T6.2 The SAR's capacitor array: where matching beats noise")

    c.글("""A SAR converter is a binary search implemented with a capacitive DAC. Its
    accuracy therefore rests on capacitor ratios, and the design question is simply how
    big the unit capacitor must be. Two independent requirements set it, and which one
    wins is not obvious until you compute both.""")

    c.날것(유도("Two requirements on the same capacitor, and where they cross", [
        ("Requirement 1 — <b>noise</b>: the array is the sampling capacitor, so "
         "kT/C<sub>total</sub> must stay below the quantisation noise (T4).",
         f"For {VFS:g} V full scale this gives C ≥ 12kT·2<sup>2N</sup>/V<sub>FS</sub>²: "
         f"{수(_잡음총C(12)*1e12,3,'pF')} at 12 bits."),
        ("Requirement 2 — <b>matching</b>: DNL at the mid-scale transition is dominated "
         "by the mismatch of the largest capacitor against the sum of the rest.",
         f"3σ DNL < ½ LSB needs σ<sub>u</sub>/C<sub>u</sub> < "
         f"{수(_허용정합(12)*100,3,'%')} at 12 bits — and by Pelgrom (T12) that "
         "relative sigma is fixed by <i>area</i>."),
        (f"A capacitor that matches to that level is about {수(CU*1e15,2,'fF')} in a "
         "modern MOM-capacitor process, which makes the 12-bit array "
         f"{수(_정합총C(12)*1e12,3,'pF')} — "
         f"{수(_정합총C(12)/_잡음총C(12),3)}× larger than the noise requirement.",
         "<b>At 12 bits the array is set by matching, not by noise.</b> Sizing it from "
         "kT/C alone gives a converter with an excellent noise floor and visible DNL "
         "steps."),
        (f"At 14 bits the two requirements are {수(_정합총C(14)*1e12,3,'pF')} and "
         f"{수(_잡음총C(14)*1e12,3,'pF')} — they have converged.",
         "Above ~14 bits noise takes over and the unit capacitor can be whatever "
         "matches; below it, matching rules. <b>Knowing which side you are on tells you "
         "which knob does anything.</b>"),
    ]))

    c.날것(표("Which limit sizes the SAR array (V_FS = 1 V, unit cap "
             f"{수(CU*1e15,2,'fF')})",
        ["Bits", "Matching needs σ_u/C_u <", "Array from matching",
         "Array from kT/C", "Binds"],
        [[str(N), 수(_허용정합(N)*100, 3, "%"),
          수(_정합총C(N)*1e12, 3, "pF"), 수(_잡음총C(N)*1e12, 3, "pF"),
          ("<b>matching</b>" if _정합총C(N) > _잡음총C(N) else "<b>noise</b>")]
         for N in (10, 12, 14)]))

    c.날것(개념(
        "Redundancy — buying back settling time with one extra bit",
        """<p>A plain binary search has no way to recover from a wrong decision: if the
        DAC has not settled when the comparator fires, the bit is wrong and every
        subsequent bit refines the wrong interval. Redundancy changes the radix so that
        successive ranges <b>overlap</b> — each step can correct an earlier error of up
        to the overlap.</p>
        <p>The cost is one or two extra cycles; the benefit is that early cycles no
        longer need to settle to the full N-bit accuracy, only to within the overlap.
        Since settling time is logarithmic in accuracy (T2), <b>relaxing the early
        cycles is most of the conversion time</b>.</p>""",
        어디에="Every modern high-speed SAR, and the inter-stage stages of pipelines "
             "(where it is called 1.5-bit-per-stage).",
        언제="Whenever the conversion must be fast. It is nearly free in area and it "
            "is the difference between a 10 MS/s and a 100 MS/s SAR at the same "
            "resolution.",
        어떻게="Choose a sub-binary radix (e.g. 1.86 instead of 2), size the capacitors "
             "accordingly, and reconstruct the output digitally with the correction "
             "weights. The weights can also be <b>calibrated</b>, which turns capacitor "
             "mismatch into a measured constant rather than an error.",
        산업코드="""// Non-binary SAR reconstruction. The weights are NOT powers of two,
// and they are per-chip once calibration has run.
localparam int W [0:N] = '{2048, 1088, 576, 320, 176, 96, 56, 32, 18, 10, 6, 4, 2, 1};
always_comb begin
    code = 0;
    for (int i = 0; i <= N; i++) if (bit_decision[i]) code += W[i];
end
// The sum of weights EXCEEDS full scale on purpose -- that surplus is the redundancy.
// A design review question worth asking: what happens if the weights are wrong by 1%?
// (Answer: nothing, until the error exceeds the overlap -- which is the point.)""",
        주의="""Redundancy protects against <b>incomplete settling and comparator
            noise</b>, not against a DAC that is monotonically wrong. If a capacitor is
            mis-sized beyond the overlap, redundancy hides the symptom in simple tests
            and leaves a code-dependent error that only a full INL sweep reveals."""))

    # ------------------------------------------------------------------
    c.절("T6.3 Static linearity: INL, DNL, and the two ways a converter lies")

    c.날것(정의("DNL (차등 비선형성)",
        "The deviation of each code's width from 1 LSB. DNL = −1 LSB means the code "
        "has <b>zero width — a missing code</b>, and the converter is no longer "
        "monotonic there."))

    c.날것(정의("INL (적분 비선형성)",
        "The cumulative deviation of each transition point from the ideal straight line "
        "— the running sum of DNL. It is what distortion measurements see; DNL is what "
        "a control loop feels."))

    c.날것(표("Which one to care about, and when",
        ["Application", "The one that matters", "Why"],
        [["Audio / RF spectrum", "INL",
          "Curvature is distortion; the customer's FFT shows harmonics"],
         ["Closed-loop control (e.g. a DAC in a servo)", "DNL and monotonicity",
          "A non-monotonic code inverts the loop's sign locally and can oscillate"],
         ["Sensor threshold detection", "DNL", "A missing code is a value the system "
          "can never report"],
         ["Digital calibration of another block", "INL",
          "The correction is only as good as the reference curve"]]))

    c.날것(사고("""A converter can pass an SNDR test and be badly non-monotonic. A
    sine-wave histogram test averages over all codes; a single missing code moves SNDR
    by a fraction of a dB and is invisible. <b>Static linearity needs its own test</b> —
    a slow ramp or a code-density sweep — and an IP deliverable that reports only SNDR
    has not characterised the part."""))

    # ------------------------------------------------------------------
    c.절("T6.4 The DAC side: segmentation and glitch energy")

    c.날것(개념(
        "세그먼테이션 (segmentation) — thermometer where it matters, binary where it does not",
        """<p>A fully binary DAC has the worst possible glitch at mid-scale: every
        switch changes at once, and their timing skew produces a transient whose area
        (<b>glitch energy</b>, in V·s) does not average out — it appears as distortion
        at the update rate. A fully thermometer-coded DAC has no such transition but
        needs 2<sup>N</sup>−1 elements and the decoder to drive them.</p>
        <p>Real DACs segment: the top M bits thermometer, the rest binary. M is chosen
        so that the largest simultaneous switching event is small enough, and the
        practical answer is usually 4–6 — the decoder cost grows as 2<sup>M</sup> while
        the glitch improvement saturates.</p>""",
        어디에="Current-steering DACs for transmitters and waveform generators; the "
             "reference DACs inside pipeline ADCs; any DAC whose output is observed in "
             "the frequency domain.",
        언제="Whenever SFDR is specified. A binary DAC's mid-scale glitch usually sets "
            "SFDR before any static error does.",
        어떻게="Segment the MSBs, match the unit current sources by layout (common "
             "centroid, dummies), and <b>randomise or rotate</b> the selection of unit "
             "elements (DEM) so residual mismatch becomes noise instead of a spur.",
        산업코드="""// Segmented decode: 6 thermometer MSBs + 8 binary LSBs.
// The point of the thermometer part is that consecutive codes change ONE element.
logic [62:0] therm;
always_comb begin
    therm = '0;
    for (int i = 0; i < 63; i++) therm[i] = (code[13:8] > i);
end
// Dynamic element matching: rotate the starting index so that element mismatch
// is spread across codes and appears as a raised noise floor, not as a spur.
always_ff @(posedge clk) rot <= rot + code[13:8];
assign sel = {therm, therm} >> rot;     // barrel rotate""",
        주의="""DEM converts a spur into noise — it does not remove the error. If the
            spectrum requirement is a noise floor, that is a win; if it is total noise
            power, it is neutral. Reporting 'SFDR improved by 15 dB' after enabling DEM
            without also reporting the noise floor is the kind of half-truth a customer
            finds in their own lab."""))

    # ------------------------------------------------------------------
    c.절("T6.5 What to do with this on Monday")

    c.날것(쓰는자리([
        ["플래시ADC · 축차비교ADC · 파이프라인ADC · 시간인터리브",
         "Architecture selection, first week", "Which limit you will be paying"],
        ["용량DAC · 세그먼테이션", "Sizing the array before any transistor",
         "Unit capacitor, total area, and the reference driver's current"],
        ["중복성 · 디지털보정", "Speed and yield",
         "How much settling accuracy the early cycles can be spared"],
        ["INL · DNL · 미싱코드", "Characterisation and the datasheet",
         "Whether the part is usable in a control loop, not just in a spectrum"],
        ["글리치에너지", "Any DAC observed in the frequency domain",
         "SFDR, and how many thermometer bits to pay for"]]))

    c.글(f"""The number to carry from this chapter: at 12 bits a SAR's capacitor array is
    <b>{수(_정합총C(12)/_잡음총C(12),3)}× larger than noise alone would require</b>,
    because matching sets it — and at 14 bits that factor is
    {수(_정합총C(14)/_잡음총C(14),3)}, where noise has taken over. Design the 12-bit part
    from the matching requirement and the 14-bit part from kT/C, and you are sizing the
    same array by two different physics because the crossover sits between them.""")

    c.글("""The next chapters leave the converter and take up the circuit that decides
    <i>when</i> all of this happens — the phase-locked loop — where the same trade
    between noise, bandwidth and power appears in a feedback system rather than in a
    capacitor.""")

    return c.완성()
