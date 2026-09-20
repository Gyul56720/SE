# -*- coding: utf-8 -*-
"""T12 -- Matching: two identical devices are not identical."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

AVT = 5e-3      # V·µm -- 측정에 넣은 Pelgrom 계수

# --- 잰 것 (edu/측정/mismatch.py, ngspice 몬테카를로 80판) -----------------
# "WxL" -> [면적 µm², σ_Vt mV, 거울비 평균, 거울비 σ %]
잰면적 = {
    "1x0.2": [0.20, 11.18, 0.9779, 14.16],
    "2x0.4": [0.80, 5.59, 0.9876, 7.17],
    "4x0.8": [3.20, 2.80, 0.9934, 3.61],
    "8x1.6": [12.80, 1.40, 0.9966, 1.81],
}
잰전류 = {"1u": 22.10, "10u": 7.17, "100u": 2.29}


def ch_match():
    c = 장(
        "T12", "Matching — Two Identical Devices Are Not Identical",
        "The only accurate thing on a chip is a ratio, and even that is a "
        "distribution. Everything precise is built on knowing its width.",
        쓰는것=["전압", "전류", "확률", "평균", "분산", "표준편차", "정규분포",
              "로그", "제곱근", "문턱전압", "트랜스컨덕턴스", "정합",
              "최소동작전압", "INL", "DNL", "PTAT", "온도계수"],
        내놓는것=["펠그롬법칙", "랜덤불일치", "계통불일치", "공통중심",
                "더미소자", "일치도면적", "수율시그마", "중요도표본",
                "오프셋", "트림", "레이아웃의존효과"],
        특허="""Matching itself cannot be patented — it is statistics — but every scheme
        that <b>buys accuracy without area</b> can be: dynamic element matching, chopper
        and auto-zero offset cancellation, digital foreground and background calibration,
        and layout techniques that cancel gradients. Notice the shape again: since
        σ falls only as 1/√area, buying 4× accuracy with area costs <b>16×</b> the
        silicon — so almost every commercially interesting idea in precision analog is
        an alternative to paying that.""")

    c.글("""Two transistors drawn identically, adjacent, in the same orientation, still
    differ. Dopant atoms are discrete and land at random; the gate edge is not perfectly
    straight; the oxide thickness varies atom by atom. The resulting parameter
    difference is a random variable, and precision analog design is the discipline of
    <b>knowing its standard deviation and budgeting for its tail</b>.""")

    # ------------------------------------------------------------------
    c.절("T12.1 Pelgrom's law, and why it is a square root")

    c.날것(개념(
        "펠그롬 법칙 (Pelgrom's law)",
        """<p>For two adjacent identically drawn devices, the standard deviation of a
        parameter difference falls as the square root of area:
        <b>σ(ΔV<sub>th</sub>) = A<sub>VT</sub>/√(W·L)</b>, with A<sub>VT</sub> in mV·µm
        — a per-process constant that the foundry measures and publishes (a few mV·µm,
        improving slowly with each node).</p>
        <p>The square root is not empirical curve-fitting: the mismatch comes from
        counting statistics on independent microscopic events (dopant placement, edge
        roughness), and the relative fluctuation of a count of N independent events
        falls as 1/√N. <b>Area is the count.</b></p>""",
        어디에="Every current mirror, differential pair, comparator, capacitor array, "
             "and SRAM cell in the design. Also in the yield model — this is the "
             "distribution that V<sub>min</sub> (T4) is a tail of.",
        언제="Before drawing anything precise: the required σ fixes the minimum area, "
            "and the minimum area often fixes the whole block's size and its parasitic "
            "capacitance, and therefore its speed.",
        어떻게="Work backwards from the specification. If an offset of 5 mV at 3σ is "
             "allowed, then σ(ΔV<sub>th</sub>) ≤ 1.67 mV, so W·L ≥ "
             f"(A<sub>VT</sub>/1.67 mV)². With A<sub>VT</sub> = {수(AVT*1e3,2,'mV·µm')} "
             f"that is {수((AVT/1.67e-3)**2,3,'µm²')} — <b>per device</b>.",
        산업코드="""* Mismatch in a PDK is a MODEL PARAMETER, not something you add by hand.
* The foundry supplies statistical models; you enable them and run Monte Carlo:
.lib 'models/pdk.lib' mc              $ NOT the 'tt' corner -- the statistical deck
.mc 200 op                            $ 200 samples
.measure op ios param='abs(i(vd2)-i(vd1))'
* AND THEN: the corners and the mismatch are DIFFERENT analyses.
*   corner  = global shift  (all devices move together)
*   mismatch = local spread (devices move independently)
* Running 'tt + mismatch' and calling it worst case misses the combination that
* actually fails: slow corner AND an unlucky pair.""",
        주의="""A<sub>VT</sub> applies to the <b>difference between two adjacent
            devices</b>. Using it for the absolute value of one device, or for devices
            on opposite sides of the die, is wrong in both directions: the absolute
            spread is larger (it includes global process variation) and the
            device-to-device correlation across a die is a different model entirely."""))

    c.날것(표("Measured: current-mirror ratio versus device area "
             f"(ngspice Monte Carlo, 80 samples, A_VT = {수(AVT*1e3,2,'mV·µm')}, "
             "I_ref = 10 µA)",
        ["W × L", "Area", "σ(ΔV_th)", "Mean ratio", "σ(ratio)"],
        [[k, 수(v[0], 3, "µm²"), 수(v[1], 4, "mV"), 수(v[2], 5),
          f"<b>{수(v[3],3,'%')}</b>"] for k, v in 잰면적.items()]))

    c.날것(유도("Reading Pelgrom straight out of that table", [
        (f"Area {수(0.2,2,'µm²')} → σ(ratio) = {수(잰면적['1x0.2'][3],4,'%')}; "
         f"area {수(0.8,2,'µm²')} → {수(잰면적['2x0.4'][3],4,'%')}.",
         f"Area ×4, σ ÷{수(잰면적['1x0.2'][3]/잰면적['2x0.4'][3],3)} — the square-root "
         "law, measured, not assumed."),
        (f"The next two steps repeat it: ÷{수(잰면적['2x0.4'][3]/잰면적['4x0.8'][3],3)} "
         f"and ÷{수(잰면적['4x0.8'][3]/잰면적['8x1.6'][3],3)}.",
         "Three independent confirmations of the same exponent. <b>If a measurement "
         "like this does not give √, the model or the harness is wrong</b> — and that "
         "is the fastest check available on a mismatch setup."),
        (f"The <b>mean</b> ratio is not 1: it rises from {수(잰면적['1x0.2'][2],5)} "
         f"toward {수(잰면적['8x1.6'][2],5)} as the devices grow.",
         "A symmetric V<sub>th</sub> error maps to an <i>asymmetric</i> current error — "
         "the square-law is convex, so the average of the ratio is pulled below 1. "
         "<b>Mismatch biases the mean, not only the spread</b>, and the effect vanishes "
         "only as the spread does."),
    ]))

    # ------------------------------------------------------------------
    c.절("T12.2 The other knob: overdrive")

    c.날것(표("Measured: the same device, different bias current "
             "(W/L = 2/0.4, 80 samples)",
        ["I_ref", "σ(ratio)", "Relative to 10 µA"],
        [[k.replace("u", " µA"), 수(v, 4, "%"),
          수(v / 잰전류["10u"], 3) + "×"] for k, v in 잰전류.items()]))

    c.날것(유도("Why more current matches better, and what it costs", [
        ("A V<sub>th</sub> error δ produces a current error through the "
         "transconductance: δI = g<sub>m</sub>·δ.",
         "The device does not know why its gate voltage is effectively different."),
        ("Relative current mismatch is therefore σ(I)/I = (g<sub>m</sub>/I<sub>D</sub>)·σ(ΔV<sub>th</sub>).",
         "<b>g<sub>m</sub>/I<sub>D</sub> is the whole story</b> (T1). High g<sub>m</sub> "
         "per amp — the efficient, low-power operating point — is also the "
         "<i>worst-matching</i> one."),
        ("In strong inversion g<sub>m</sub>/I<sub>D</sub> = 2/V<sub>ov</sub>, so "
         "σ(I)/I = 2σ(ΔV<sub>th</sub>)/V<sub>ov</sub>.",
         f"Measured: {수(잰전류['1u'],4,'%')} at 1 µA against "
         f"{수(잰전류['100u'],4,'%')} at 100 µA — "
         f"{수(잰전류['1u']/잰전류['100u'],3)}× better for 100× the current, which is "
         "the √ again (V<sub>ov</sub> ∝ √I)."),
        ("In weak inversion g<sub>m</sub>/I<sub>D</sub> saturates at ~1/(nV<sub>T</sub>) "
         "≈ 25–30 V⁻¹ and matching is at its worst.",
         "<b>This is why a subthreshold current mirror is a bad current mirror</b>, and "
         "why ultra-low-power analog pays for its efficiency in area."),
    ]))

    c.날것(짚기("""Those two tables are the whole design space. Accuracy can be bought
    with <b>area</b> (σ ∝ 1/√WL) or with <b>overdrive</b> (σ ∝ 1/V<sub>ov</sub>), and
    both have a square-root character, so both are expensive. Everything else in
    precision analog — chopping, auto-zero, DEM, digital calibration — exists to avoid
    paying either."""))

    # ------------------------------------------------------------------
    c.절("T12.3 The mismatch that is not random")

    c.날것(정의("계통 불일치 (systematic mismatch)",
        "A difference that is the same on every die: a gradient in oxide thickness "
        "across the wafer, a temperature gradient from a nearby power device, stress "
        "from the package or from a neighbouring well, or simply different surroundings "
        "on the two sides of a pair. <b>It does not average out over samples</b>, so no "
        "amount of Monte Carlo finds it."))

    c.날것(표("Two kinds of mismatch, and what each responds to",
        ["", "Random", "Systematic"],
        [["Source", "Discrete dopants, edge roughness — counting statistics",
          "Gradients, stress, different neighbours, thermal"],
         ["Scales as", "1/√(W·L)", "Does not scale with area — <b>it can get worse</b>, "
          "since a larger device spans more of the gradient"],
         ["Found by", "Monte Carlo", "Layout review, and measurement on silicon"],
         ["Removed by", "Area, overdrive, calibration",
          "<b>Layout</b>: common centroid, dummies, identical orientation and "
          "surroundings"],
         ["Typical size", f"{수(잰면적['2x0.4'][3],3,'%')} for a "
          f"{수(0.8,2,'µm²')} mirror (measured above)",
          "0.1–1 % from a gradient across a few hundred µm"]]))

    c.날것(개념(
        "공통 중심 배치 (common-centroid layout) and dummies",
        """<p>Split each device of a matched pair into pieces and interleave them so both
        devices share the same centre of mass: A B B A, or a checkerboard for a
        two-dimensional gradient. A <b>linear</b> gradient then affects both halves
        equally and cancels to first order.</p>
        <p><b>Dummy devices</b> at the edges solve a different problem: the outermost
        real device has a different neighbour than the inner ones, so etch and stress
        differ. Dummies give every real device identical surroundings, at the cost of
        area that does nothing electrically.</p>""",
        어디에="Every matched pair that matters: differential pairs, current-mirror "
             "arrays, capacitor arrays in converters (T6), bandgap BJT arrays (T11).",
        언제="At layout, and it must be specified <b>by the designer</b> — a layout "
            "engineer cannot infer which devices must match from a netlist.",
        어떻게="Mark matched groups in the schematic, require common-centroid with "
             "dummies, keep orientation identical (never mirror a device to save area), "
             "route the two halves symmetrically, and keep the pair away from the "
             "package's stress maxima — typically the die corners.",
        산업코드="""// The instruction that must reach the layout engineer. A netlist
// does not carry it, so it goes in the constraint file AND the schematic.
//   match_group  : M1 M2      common_centroid = ABBA, dummies = 2 each side
//   orientation  : identical (NO mirroring -- STI stress is not symmetric)
//   routing      : symmetric; equal parasitic on both gates
//   keep_out     : > 50 um from the die seal ring and from any power device
// Verified by an LVS-with-matching check, not by inspection:
//   assert centroid(M1) == centroid(M2) within 0.5 um""",
        주의="""Common centroid cancels a <b>linear</b> gradient. A quadratic one — which
            is what a nearby heat source produces — is not cancelled, and interleaving
            can even make it worse by spreading the device over more of the curvature.
            For thermal gradients the answer is distance and orientation relative to the
            isotherms, not interleaving."""))

    c.날것(사고("""Mismatch is also the reason SRAM V<sub>min</sub> (T4) is a yield
    question rather than a design-point question. An array of 10 million cells needs the
    <b>worst</b> cell to work, which is roughly a −5.5σ event. Ordinary Monte Carlo with
    a thousand samples cannot see that tail at all — it would take on the order of
    10<sup>8</sup> samples. Production flows therefore use <b>importance sampling</b>
    or analytic tail methods, and a report that says 'Monte Carlo passed, 1000 samples'
    for a memory has not addressed the question it was asked."""))

    # ------------------------------------------------------------------
    c.절("T12.4 What to do with this on Monday")

    c.날것(쓰는자리([
        ["펠그롬법칙 · 일치도면적", "Sizing any matched device",
         "The minimum area — which then sets parasitics and speed"],
        ["트랜스컨덕턴스 · 랜덤불일치", "Choosing the bias point",
         "Whether the efficient operating point is affordable"],
        ["계통불일치 · 공통중심 · 더미소자", "Layout constraints, written by the designer",
          "What the layout engineer must be told, because the netlist does not say it"],
        ["수율시그마 · 중요도표본", "Memory and any large array",
         "How many σ the design must survive, and which method can see that far"],
        ["트림 · 디지털보정", "When area becomes unaffordable",
         "Whether to pay in silicon or in test time"]]))

    c.글(f"""The measured results to carry: current-mirror mismatch falls as the square
    root of area — {수(잰면적['1x0.2'][3],4,'%')} →
    {수(잰면적['2x0.4'][3],4,'%')} → {수(잰면적['4x0.8'][3],4,'%')} →
    {수(잰면적['8x1.6'][3],4,'%')} for four doublings of area — and as the square root
    of current: {수(잰전류['1u'],4,'%')} at 1 µA against
    {수(잰전류['100u'],4,'%')} at 100 µA. <b>Both knobs cost a square</b>, and that
    single fact is why calibration exists.""")

    c.글("""The next chapter leaves the devices and takes up the network that feeds them
    all — the power delivery network — where the same 'it is a distribution' argument
    reappears as a question about impedance and time.""")

    return c.완성()
