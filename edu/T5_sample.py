# -*- coding: utf-8 -*-
"""T5 -- Sampling: aperture, jitter, aliasing, and the wall they build together."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

k볼츠만 = 1.380649e-23
T상온 = 300.0


def _지터SNR(fin, tj):
    """무상관 표본 지터만 있을 때의 SNR (dB)."""
    return -20 * math.log10(2 * math.pi * fin * tj)


def _필요지터(비트, fin):
    """N 비트가 되려면 지터가 얼마여야 하나 (초, rms)."""
    return 1.0 / (2 * math.pi * fin * 2 ** 비트)


def _enob(snr):
    return (snr - 1.76) / 6.02


def ch_sample():
    c = 장(
        "T5", "Sampling — Where a Continuous Signal Becomes a Number",
        "Two clocks decide everything: when you sample, and how precisely you know "
        "when. The second one is what limits every high-speed converter shipping today.",
        쓰는것=["전압", "주파수", "위상", "적분", "미분", "확률", "표준편차",
              "로그", "RC지연", "슬루", "kTC잡음", "열잡음", "SNR", "SNDR",
              "ENOB", "잡음대역폭"],
        내놓는것=["표본화정리", "엘리어싱", "나이키스트", "대역통과표본화",
                "구경시간", "구경지터", "지터한계SNR", "추적유지",
                "트래킹대역폭", "차지인젝션", "클럭피드스루", "부트스트랩스위치",
                "오버샘플링비", "잡음성형", "데시메이션"],
        특허="""The sampling instant is the most contested square millimetre in a
        high-speed converter, and the patents show it: bootstrapped switches that hold
        V<sub>GS</sub> constant so the on-resistance does not depend on the signal;
        clock paths that deliberately do <i>not</i> share a buffer with anything else;
        sampling schemes that cancel charge injection by symmetry rather than by
        trimming; and, one level up, time-interleaved architectures whose entire
        difficulty is that each slice samples at a slightly wrong instant. <b>Every one
        of these is an argument about the aperture, not about the amplifier.</b>""")

    c.글("""Sampling is usually taught as an idealisation — multiply by an impulse train,
    observe the spectrum repeat, avoid overlap. That story is correct and it is not the
    one that limits hardware. A real sampler closes a switch for a finite time, through
    a finite resistance, at an instant known only to within some picoseconds, onto a
    capacitor whose size was already fixed by kT/C in T4. Each of those four words —
    finite, finite, instant, capacitor — costs resolution, and the one that dominates
    above a few hundred megahertz is the third.""")

    # ------------------------------------------------------------------
    c.절("T5.1 Aliasing is not a theorem you obey, it is a filter you buy")

    c.날것(유도("From the impulse train to the folded spectrum", [
        ("Sampling at f<sub>s</sub> multiplies the signal by a train of impulses spaced "
         "T<sub>s</sub> = 1/f<sub>s</sub>.",
         "The idealisation. Everything about aliasing follows from this one step; the "
         "non-idealities come later and do not change it."),
        ("Multiplication in time is convolution in frequency, and the impulse train's "
         "spectrum is itself an impulse train spaced f<sub>s</sub>.",
         "So the input spectrum is <b>copied</b> to every multiple of f<sub>s</sub>."),
        ("Copies overlap unless the input is confined to a band narrower than "
         "f<sub>s</sub>/2.",
         "Nyquist. Note what it does <i>not</i> say: it says nothing about where the "
         "band sits, only how wide it is."),
        ("Everything above f<sub>s</sub>/2 folds down and is <b>indistinguishable</b> "
         "from a real signal afterwards.",
         "No digital processing can undo it — the information that told the two apart "
         "was destroyed at the sampler. This is why an anti-alias filter is an analog "
         "component and cannot be moved into software."),
        ("<b>Noise folds too</b>, and by the same rule.",
         "A front end with 5 GHz of bandwidth sampled at 200 MHz folds 50 bands of "
         "thermal noise onto the signal — a 17 dB penalty. <b>Bandwidth you do not "
         "need is not free</b>; it is noise you pay for."),
    ]))

    c.날것(개념(
        "Bandpass sampling — using the folding on purpose",
        """<p>Nyquist constrains the <i>width</i> of the band, not its position. A signal
        occupying 100 MHz centred at 2.4 GHz can be sampled at 250 MS/s, provided the
        band falls entirely inside one Nyquist zone and the sampler's input bandwidth
        reaches 2.4 GHz. The alias <i>is</i> the wanted signal, translated down for
        free.</p>
        <p>The cost is precise: the sampling <b>aperture</b> must be good enough for
        2.4 GHz even though the sample rate is 250 MHz — jitter is referred to the input
        frequency, not the clock rate. That trade (no mixer, but a far harder clock) is
        the whole engineering decision.</p>""",
        어디에="RF receivers that digitise at IF, software-defined radio front ends, and "
             "any instrument that must capture a narrow band sitting at a high "
             "frequency.",
        언제="When the band is narrow relative to its centre frequency and you would "
            "otherwise pay for a downconversion mixer and its LO.",
        어떻게="Pick f<sub>s</sub> so the band lands strictly inside a single zone "
             "(k·f<sub>s</sub>/2 to (k+1)·f<sub>s</sub>/2), add a <b>bandpass</b> "
             "anti-alias filter — a low-pass is useless here — and budget the jitter "
             "against the RF carrier.",
        산업코드="""// Zone check, written as an assertion rather than a comment.
// A band that straddles a zone boundary is a silent failure: it still samples,
// and the output is two overlapped copies.
localparam real FS = 250e6, FC = 2.4e9, BW = 100e6;
initial begin
    int k = $floor(2.0*(FC - BW/2)/FS);
    assert ($floor(2.0*(FC + BW/2)/FS) == k)
        else $fatal(1, "band straddles a Nyquist zone boundary -- pick another FS");
end""",
        주의="""The anti-alias filter for bandpass sampling must reject <b>every other
            zone</b>, not just frequencies above f<sub>s</sub>/2. Engineers who reuse a
            low-pass filter here get a receiver that works in the lab (where the only
            signal present is the wanted one) and fails in the field."""))

    # ------------------------------------------------------------------
    c.절("T5.2 Aperture jitter — the wall")

    c.날것(정의("구경지터 (aperture jitter)",
        "The rms uncertainty in the instant at which the sampler actually captures the "
        "signal. It comes from the clock path (phase noise, supply-induced delay "
        "modulation, thermal noise in the last buffer) and from the sampler itself, and "
        "it is <b>referred to the input frequency</b>, not the sample rate."))

    c.날것(유도("Why jitter costs more as the signal gets faster", [
        ("A sine v(t) = A·sin(2πf<sub>in</sub>t) has slope dv/dt = 2πf<sub>in</sub>A·cos(…).",
         "The slope is what converts a time error into a voltage error — this is the "
         "whole mechanism."),
        ("A timing error Δt therefore produces a voltage error Δv = (dv/dt)·Δt, worst "
         "at the zero crossing where the slope is greatest.",
         "The largest error happens where the signal is <i>changing</i> fastest, not "
         "where it is largest."),
        ("With rms jitter σ<sub>t</sub> and a full-scale sine, the rms error is "
         "2πf<sub>in</sub>·(A/√2)·σ<sub>t</sub>, and the signal rms is A/√2.",
         "The amplitude cancels — <b>jitter-limited SNR does not depend on signal "
         "amplitude</b>, which is why you cannot back away from it by scaling down."),
        ("SNR = −20·log<sub>10</sub>(2πf<sub>in</sub>σ<sub>t</sub>).",
         "One equation, two variables, no device parameters. It is a property of the "
         "clock and the input frequency alone."),
        (f"At f<sub>in</sub> = 1 GHz, 100 fs of jitter gives "
         f"{수(_지터SNR(1e9,1e-13),3,'dB')} — "
         f"{수(_enob(_지터SNR(1e9,1e-13)),3)} bits.",
         "<b>100 fs is already a hard clock.</b> This is why 12-bit gigahertz converters "
         "are difficult in a way that has nothing to do with the comparator."),
    ]))

    c.날것(표("Jitter-limited SNR and ENOB (uncorrelated aperture jitter only)",
        ["f_in", "1 ps", "300 fs", "100 fs", "30 fs"],
        [[수(f/1e9, 3, "GHz")] +
         [f"{_지터SNR(f,tj):.1f} dB / {_enob(_지터SNR(f,tj)):.1f} b"
          for tj in (1e-12, 3e-13, 1e-13, 3e-14)]
         for f in (1e8, 1e9, 5e9)]))

    c.날것(예제(
        "What clock does a 12-bit, 1 GHz-input converter need?",
        """The design target is 12 effective bits at a 1 GHz input. Assume jitter is the
        only error source — an optimistic assumption that makes the answer a <b>lower
        bound</b> on how good the clock must be.""",
        """Invert the SNR expression: σ<sub>t</sub> = 1/(2π·f<sub>in</sub>·2<sup>N</sup>).""",
        f"""σ<sub>t</sub> = {수(_필요지터(12,1e9)*1e15, 3, 'fs')} rms. For 14 bits it is
        {수(_필요지터(14,1e9)*1e15, 3, 'fs')}.""",
        """Comparing that number against the jitter quoted for a clock <i>source</i>.
        The specification that matters is the jitter <b>at the sampling switch</b>,
        after the whole distribution path — buffers, level shifters, the divider, and
        whatever supply noise the digital side injected into them. A 20 fs source
        behind a noisy buffer chain is a 200 fs sampler, and the datasheet of the source
        will not tell you that.""",
        덧=표("Required rms aperture jitter at f_in = 1 GHz",
             ["Bits", "σ_t required"],
             [[str(N), 수(_필요지터(N, 1e9)*1e15, 3, "fs")]
              for N in (8, 10, 12, 14, 16)])))

    c.날것(짚기("""Jitter and kT/C add in <b>power</b>, not in amplitude, and they scale
    in opposite directions with frequency: kT/C is flat while jitter worsens by 6 dB per
    octave of input frequency. There is therefore always a crossover frequency, and
    knowing which side of it you are on tells you which knob does anything. Below it,
    spend area on capacitance. Above it, spend power on the clock — <b>a bigger sampling
    capacitor buys nothing in a jitter-limited design</b>, and it is the most common way
    to waste a redesign."""))

    # ------------------------------------------------------------------
    c.절("T5.3 The switch itself: charge injection, feedthrough, and bootstrapping")

    c.날것(그림(sch.모스("NMOS", 150, 90) + sch.전원(240, 30),
        "The sampling switch. Its on-resistance sets the tracking bandwidth; its channel "
        "charge lands on the sampling capacitor when it turns off."))

    c.날것(표("Three errors the switch adds, and what each depends on",
        ["Error", "Mechanism", "Scales with", "Signal-dependent?"],
        [["Charge injection", "The channel's inversion charge has to go somewhere when "
          "the device turns off; roughly half lands on C<sub>s</sub>",
          "W·L·C<sub>ox</sub>·(V<sub>GS</sub>−V<sub>th</sub>) / C<sub>s</sub>",
          "<b>Yes</b> — V<sub>GS</sub> depends on the sampled level, so it becomes "
          "distortion, not offset"],
         ["Clock feedthrough", "C<sub>gd</sub> couples the falling clock edge onto the "
          "capacitor", "C<sub>ov</sub>/(C<sub>ov</sub>+C<sub>s</sub>) · V<sub>clk</sub>",
          "No (to first order) — mostly a fixed offset"],
         ["R<sub>on</sub> modulation", "The switch's on-resistance depends on "
          "V<sub>GS</sub> = V<sub>clk</sub> − v<sub>in</sub>",
          "1/(μC<sub>ox</sub>(W/L)(V<sub>GS</sub>−V<sub>th</sub>))",
          "<b>Yes</b> — a signal-dependent time constant is signal-dependent settling, "
          "which is distortion"]]))

    c.날것(개념(
        "The bootstrapped switch",
        """<p>Hold the switch's gate at v<sub>in</sub> + V<sub>DD</sub> instead of at
        V<sub>DD</sub>, using a capacitor pre-charged to V<sub>DD</sub> and flipped onto
        the gate during the tracking phase. Then V<sub>GS</sub> is constant regardless
        of the signal, so R<sub>on</sub> is constant and the charge injected at turn-off
        is constant — <b>signal-dependent errors become offsets</b>, and offsets are
        harmless in a differential design.</p>
        <p>It also solves a reliability problem that is easy to miss: without
        bootstrapping, a switch passing a signal near ground sees V<sub>GS</sub> =
        V<sub>DD</sub>, which in an advanced node may exceed the oxide's rating over
        the device's lifetime (T14).</p>""",
        어디에="The input sampling network of essentially every SAR and pipeline ADC "
             "above 10 bits, and in high-linearity switched-capacitor filters.",
        언제="When THD or SFDR matters more than area. A plain NMOS switch is fine for "
            "8 bits and hopeless at 12.",
        어떻게="Size the bootstrap capacitor ≫ the gate capacitance it must drive, "
             "check the reliability of every node across the clock phases, and verify "
             "distortion with a <b>two-tone</b> transient, not a single tone — "
             "intermodulation exposes the residual signal dependence a single tone hides.",
        산업코드="""* The check that matters, and the one people skip.
* A single tone can look clean while IM3 is terrible.
Vin1 in1 0 SIN(0 0.45 100.1MEG)
Vin2 in2 0 SIN(0 0.45 103.3MEG)
.tran 10p 20u
.four 100.1MEG v(sampled)          $ harmonic distortion
* and post-process the FFT for IM3 at 2*f1-f2 = 96.9 MHz -- the number the
* customer will measure and the one that exposes Ron modulation.""",
        주의="""Bootstrapping makes the gate voltage exceed the supply, so every node in
            the bootstrap network must be checked against the oxide limit at the
            <b>fast, high-voltage, low-temperature corner</b> — the opposite corner from
            the one that limits performance. A bootstrap circuit verified only at
            typical is a reliability report waiting to happen."""))

    # ------------------------------------------------------------------
    c.절("T5.4 Oversampling: buying bits with time")

    c.날것(유도("Why oversampling helps, and how much", [
        ("Quantisation noise power is LSB²/12 <b>regardless of the sample rate</b>.",
         "The quantiser does not know how fast it is being clocked; the error per "
         "sample has the same distribution."),
        ("That fixed power is spread over the Nyquist band, 0 to f<sub>s</sub>/2.",
         "So the noise <i>density</i> is LSB²/12 divided by f<sub>s</sub>/2 — "
         "sampling faster dilutes it."),
        ("Filtering down to the signal band B keeps only the fraction "
         "2B/f<sub>s</sub> of it.",
         "Define the oversampling ratio OSR = f<sub>s</sub>/(2B)."),
        ("SNR improves by 10·log<sub>10</sub>(OSR): <b>3 dB, or half a bit, per "
         "doubling</b>.",
         "This is plain oversampling, with no feedback. Going from 8 to 12 bits this "
         "way needs OSR = 256 — expensive but occasionally the right answer for a slow "
         "sensor."),
        ("A ΔΣ modulator <b>shapes</b> the noise instead of merely spreading it, giving "
         "(6L+3) dB per doubling for an L-th-order loop.",
         "The loop pushes quantisation noise out of the band. A 2nd-order modulator "
         "gains 15 dB per octave of OSR — this is why ΔΣ dominates audio and precision "
         "sensing, and why it is useless at gigahertz signal bandwidths."),
    ]))

    c.날것(표("What oversampling buys, per doubling of OSR",
        ["Architecture", "SNR gain per 2× OSR", "Bits per 2× OSR", "Where it wins"],
        [["Plain oversampling + decimation", "3 dB", "0.5",
          "Cheap resolution on slow signals; anti-alias filter relief"],
         ["ΔΣ, 1st order", "9 dB", "1.5", "Simple, but idle tones"],
         ["ΔΣ, 2nd order", "15 dB", "2.5", "Audio, precision sensors"],
         ["ΔΣ, 3rd+ order / MASH", "21 dB+", "3.5+",
          "Where stability engineering is worth it"]]))

    c.날것(짚기("""Oversampling relieves the <b>anti-alias filter</b> as much as it buys
    resolution, and that is often the real reason to do it. Sampling a 20 kHz audio band
    at 44.1 kHz demands a filter that is flat at 20 kHz and dead at 22.05 kHz — a brutal
    analog problem. Sampling at 2.8 MHz moves the requirement to 'dead at 1.4 MHz',
    which is a single RC. <b>The filter that disappears is usually worth more than the
    half-bit.</b>"""))

    # ------------------------------------------------------------------
    c.절("T5.5 What to do with this on Monday")

    c.날것(쓰는자리([
        ["엘리어싱 · 나이키스트", "Choosing f_s and the anti-alias filter",
         "The filter order — and whether it is analog or can be shared with "
         "oversampling"],
        ["구경지터", "Clocking architecture, before the converter is designed",
         "Whether the target ENOB is reachable at all at that input frequency"],
        ["대역통과표본화", "RF and IF receiver front ends",
         "Whether a mixer can be removed, and what the clock must then cost"],
        ["차지인젝션 · 부트스트랩스위치", "The sampling network of any ≥10-bit converter",
         "THD and SFDR, and the oxide-reliability check that goes with it"],
        ["오버샘플링비 · 잡음성형", "Slow, precise signal paths",
         "Whether resolution can be bought with time instead of capacitance"]]))

    c.글(f"""The number to carry: at a 1 GHz input, <b>12 effective bits requires
    {수(_필요지터(12,1e9)*1e15, 3, 'fs')} rms of aperture jitter</b>, measured at the
    switch and not at the clock source. Every architecture decision in a high-speed
    converter — interleaving, bandpass sampling, where the clock buffer sits — is
    downstream of that one line.""")

    c.글("""The next chapter turns the sampled voltage into a code, and finds that the
    architectures differ less in accuracy than in <i>where</i> they spend the same
    fundamental limits.""")

    return c.완성()
