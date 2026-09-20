# -*- coding: utf-8 -*-
"""T9 -- The channel: where the loss comes from, measured term by term."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch

# --- 잰 것: serdes.채널물리 의 삽입손실을 주파수 네 점에서 (f 는 1/UI) -------
# 0.5/UI 가 나이퀴스트다.  도체는 sqrt(f), 유전은 f 로 는다 -- 아래 표가 그것을
# 두 배씩 올라가며 확인한다(6.0 -> 8.5 -> 12.0 -> 17.0 는 sqrt(2) 배씩이다).
잰삽입손실 = {
    "도체만 (12 dB)": {0.125: -6.0, 0.25: -8.5, 0.5: -12.0, 1.0: -17.0},
    "유전만 (8 dB)": {0.125: -2.0, 0.25: -4.0, 0.5: -8.0, 1.0: -16.0},
    "둘 다": {0.125: -8.0, 0.25: -12.5, 0.5: -20.0, 1.0: -33.0},
}
# 반사 노치: (계수, 지연UI) -> (잰 위치 /UI, 잰 깊이 dB)
잰노치 = {(0.2, 4): (0.1250, -1.94), (0.35, 11): (0.0454, -3.75),
        (0.35, 2): (0.2502, -3.74)}


def _노치이론(계수, 지연):
    return 1.0 / (2 * 지연), 20 * math.log10(abs(1 - 계수))


def ch_channel():
    c = 장(
        "T9", "The Channel — Where the Loss Comes From, Term by Term",
        "Loss you can equalise. Reflections you cannot. Knowing which one you have is "
        "the difference between a receiver design and a board redesign.",
        쓰는것=["전압", "주파수", "위상", "로그", "적분",
              "심볼간간섭", "펄스응답", "커서", "CTLE", "FFE", "DFE",
              "아이다이어그램"],
        내놓는것=["특성임피던스", "전송선", "삽입손실", "표피효과", "유전손실",
                "반사계수", "리턴로스", "노치", "비아스터브", "백드릴",
                "근단누화", "원단누화", "S파라미터", "채널규격", "COM"],
        특허="""Channel patents belong to the board and connector houses, not to the IP
        house — but the <b>receiver</b> patents that matter are all responses to channel
        pathology: equalisers that adapt to a notch instead of fighting it, schemes that
        detect and cancel a specific reflection, and crosstalk cancellation that uses the
        aggressor's own data as a reference. Read this chapter as a catalogue of the
        problems your receiver will be asked to solve, and notice which of them
        equalisation <i>cannot</i> solve — those are where the inventions are.""")

    c.글("""The previous chapter treated the channel as a loss number. That number is a
    sum of physically distinct terms which scale differently with frequency, come from
    different parts of the system, and — crucially — respond differently to
    equalisation. A receiver designer who knows only 'the channel is 20 dB' cannot tell
    whether the design is difficult or impossible.""")

    # ------------------------------------------------------------------
    c.절("T9.1 The four terms, and how to tell them apart from one measurement")

    c.날것(개념(
        "삽입손실 (insertion loss) as a fitted sum",
        """<p>The IEEE 802.3 channel specifications fit measured insertion loss with
        <b>IL(f) = a<sub>0</sub> + a<sub>1</sub>√f + a<sub>2</sub>f + a<sub>4</sub>f²</b>,
        and each term has a physical owner:</p>
        <ul>
        <li><b>a<sub>0</sub> (flat)</b> — connectors, bond wires, anything whose loss
        does not care about frequency.</li>
        <li><b>a<sub>1</sub>√f — skin effect.</b> Current crowds into a surface layer
        whose depth goes as 1/√f, so the effective resistance goes as √f. This is the
        copper.</li>
        <li><b>a<sub>2</sub>f — dielectric loss.</b> The board material's loss tangent;
        energy goes into heating the substrate. This is the laminate choice.</li>
        <li><b>a<sub>4</sub>f² — roughness and radiation.</b> Surface treatment of the
        copper, and whatever the trace radiates.</li>
        </ul>
        <p>Fitting a measurement to this form tells you <b>which purchase order fixes
        it</b>: better copper, better laminate, fewer connectors, or none of the above.</p>""",
        어디에="Reading any channel specification, budgeting a link before a board "
             "exists, and arguing with the system architect about the laminate.",
        언제="At the very start. The fit decides whether the receiver needs 3 taps or "
            "15, and that decision sizes the whole receiver.",
        어떻게="Take the measured S21 in dB, fit the four coefficients over the band of "
             "interest, and look at which term dominates at Nyquist. Below is the same "
             "decomposition measured on this repository's channel model.",
        산업코드="""# Fitting a real S21 to the standard form -- four numbers that a board
# engineer can act on. (numpy, on a Touchstone file read with scikit-rf.)
import numpy as np, skrf
ntwk = skrf.Network('channel.s4p')
f    = ntwk.f / f_nyquist                      # normalise to Nyquist
IL   = 20*np.log10(np.abs(ntwk.s[:, 1, 0]))    # dB, and it is NEGATIVE
A    = np.vstack([np.ones_like(f), np.sqrt(f), f, f*f]).T
a, *_ = np.linalg.lstsq(A, IL, rcond=None)
print(f"flat {a[0]:.2f} dB | skin {a[1]:.2f} | dielectric {a[2]:.2f} | rough {a[3]:.2f}")
# If |a[2]| dominates at Nyquist, the fix is laminate, not copper.""",
        주의="""A fit over the wrong band tells you the wrong thing. Fit over the band
            the <b>signal</b> occupies (DC to roughly 1.5× Nyquist), not over whatever
            range the VNA happened to sweep — the f² term in particular is nearly
            unconstrained below Nyquist and will absorb whatever the fit needs."""))

    c.날것(표("Measured insertion loss of this model's channel, by term "
             "(f in units of 1/UI; Nyquist = 0.5)",
        ["Channel", "0.125", "0.25", "0.5 (Nyquist)", "1.0"],
        [[이름] + [수(잰삽입손실[이름][f], 4, "dB") for f in (0.125, 0.25, 0.5, 1.0)]
         for 이름 in 잰삽입손실]))

    c.날것(유도("Reading the physics straight out of that table", [
        ("The skin-effect row goes −6.0 → −8.5 → −12.0 → −17.0 dB as frequency "
         "doubles.",
         f"Each step multiplies by {수(8.5/6.0,4)} ≈ √2 — which is what "
         "a<sub>1</sub>√f predicts. <b>The model implements what the standard's form "
         "says, and the measurement confirms it.</b>"),
        ("The dielectric row goes −2.0 → −4.0 → −8.0 → −16.0 dB.",
         "Exactly 2× per doubling — the a<sub>2</sub>f term, confirmed the same way."),
        ("At low frequency the conductor term dominates (−6.0 against −2.0); by 1.0/UI "
         "they are comparable (−17.0 against −16.0).",
         "<b>The dominant loss mechanism changes across the band</b>, so 'the channel "
         "is copper-limited' is only ever true at a stated frequency."),
        ("The combined row is the sum of the two in dB, to within the read-out "
         "precision.",
         f"−6.0 + −2.0 = −8.0 measured; −12.0 + −8.0 = −20.0 measured. The terms are "
         "<b>independent</b>, which is why fitting them separately is legitimate."),
    ]))

    # ------------------------------------------------------------------
    c.절("T9.2 Reflections: the part equalisation cannot fix")

    c.날것(정의("전송선 · 특성임피던스 (transmission line, Z₀)",
        "Above the frequency at which a trace is a meaningful fraction of a wavelength, "
        "it stops being a wire and becomes a <b>transmission line</b>: a structure that "
        "carries a travelling wave whose voltage-to-current ratio is fixed by geometry "
        "and dielectric, Z₀ = √(L/C) per unit length. A wave meeting a different Z₀ is "
        "partly reflected — which is the subject of the rest of this section, and the "
        "reason 'impedance' is a specification on a board and not just a number in "
        "Ohm's law."))

    c.날것(정의("반사계수 (reflection coefficient), ρ",
        "At an impedance discontinuity, ρ = (Z₂ − Z₁)/(Z₂ + Z₁) of the incident wave is "
        "sent back. A 10 % impedance error gives ρ ≈ 0.05; a via stub, a connector "
        "footprint or a package ball can give far more."))

    c.날것(유도("Where a reflection puts its notch, and how deep", [
        ("A reflection returns after a round-trip delay τ and adds to the direct path.",
         "One echo, one delay — the simplest case, and the one that already explains "
         "most measured channels."),
        ("The transfer function becomes H(f)·(1 − ρ·e<sup>−j2πfτ</sup>) for an "
         "inverting reflection.",
         "Direct plus delayed copy: interference, not attenuation."),
        ("It cancels where the delayed copy is in anti-phase, i.e. at "
         "f = 1/(2τ), 3/(2τ), …",
         "<b>The notch position tells you the distance</b> — and in a real board that "
         "is how a stub is identified."),
        ("Its depth is 20·log₁₀(1 − ρ).",
         "Depth measures the magnitude of the discontinuity."),
    ]))

    c.날것(표("Measured against the closed form — an independent cross-check",
        ["ρ", "Delay (UI)", "Notch position (measured)", "Position (theory)",
         "Depth (measured)", "Depth (theory)"],
        [[수(ρ, 3), 수(d, 3),
          수(잰노치[(ρ, d)][0], 4, "/UI"), 수(_노치이론(ρ, d)[0], 4, "/UI"),
          수(잰노치[(ρ, d)][1], 4, "dB"), 수(_노치이론(ρ, d)[1], 4, "dB")]
         for (ρ, d) in 잰노치]))

    c.날것(사고("""The first attempt at that measurement reported the notch at
    0.894/UI for a reflection whose theory says 0.125/UI — a factor of seven wrong, from
    a plot that looked entirely reasonable. The cause: the code took the <b>minimum of
    the insertion loss</b>, and at high frequency the smooth loss is far deeper than any
    notch, so the minimum was simply the top of the band. <b>The trivial explanation had
    not been excluded.</b> Dividing by the reflection-free channel first — comparing
    like with like — put every number within 0.2 % of theory."""))

    c.날것(개념(
        "Why a notch is worse than loss of the same depth",
        """<p>A linear equaliser inverts the channel. Inverting a smooth roll-off costs
        noise amplification proportional to the gain applied — expensive but bounded.
        Inverting a <b>notch</b> requires enormous gain at one frequency, and at that
        frequency the received signal is not merely small, it has been cancelled: there
        is almost no signal to amplify, only noise. <b>The information at that frequency
        is gone.</b></p>
        <p>This is why the same 20 dB of flat loss and 20 dB of notch are entirely
        different problems, and why board reviews chase impedance discontinuities rather
        than trace length.</p>""",
        어디에="Board and package review, connector selection, and the decision of "
             "whether a channel is workable at all before a receiver is designed.",
        언제="Before committing to a data rate. A notch inside the signal band is a "
            "board fix, not a receiver fix.",
        어떻게="Look at <b>return loss (S11)</b>, not only insertion loss. A channel "
             "with good IL and poor RL has its energy going somewhere, and a DFE can "
             "cancel a <i>post-cursor</i> echo but only if it lands within the tap span "
             "— an echo 40 UI away needs 40 taps.",
        산업코드="""# Where the echo lands decides whether ANY receiver can fix it.
#   round-trip 40 mm on FR4, eps_eff ~ 4.0  ->  t = 2*0.040/(3e8/2) = 533 ps
#   at 25 Gbaud (40 ps/UI)                  ->  13 UI away
# A 13-tap DFE can reach it; a 4-tap one cannot, and no amount of CTLE helps.
# THIS calculation belongs in the datasheet's integration section, because the
# customer's board is what decides it.""",
        주의="""A DFE cancels a reflection only if the reflection is <b>past</b> the main
            cursor and within the tap span. Pre-cursor reflections (from a discontinuity
            near the transmitter) are not reachable by a DFE at all, and an FFE that
            tries amplifies the noise at exactly the frequency the notch removed."""))

    # ------------------------------------------------------------------
    c.절("T9.3 Crosstalk, and which kind actually hurts")

    c.날것(표("Near-end and far-end crosstalk",
        ["", "NEXT (near end)", "FEXT (far end)"],
        [["Where it couples", "Aggressor's transmitter into your receiver, at the same "
          "end", "Aggressor's transmitter into your receiver, at the far end"],
         ["Attenuated by the channel?", "<b>No</b> — it never traverses the channel",
          "Yes — it travels the same lossy path as the signal"],
         ["Relative to the signal", "Full-strength aggressor against your "
          "channel-attenuated signal", "Both attenuated, so the ratio is roughly "
          "preserved"],
         ["Grows with", "Coupling length and edge rate",
          "Coupling length, and it grows with frequency"],
         ["Fixed by", "Separation, shielding, and <b>not routing TX beside RX</b>",
          "Spacing, dielectric choice, and cancellation in the receiver"],
         ["Which dominates", "<b>Long, lossy channels</b> — the signal is small and the "
          "aggressor is not", "Short channels and dense parallel buses"]]))

    c.날것(짚기("""The asymmetry in that table is the practical point. On a 30 dB channel
    your signal arrives 30 dB down while a NEXT aggressor arrives at full strength — so
    an aggressor coupled at −40 dB is only 10 dB below your signal. <b>NEXT is a
    layout-review item, not a receiver item</b>: no equaliser can subtract a signal it
    has never seen. FEXT, by contrast, has traversed the same channel and is in some
    architectures <i>cancellable</i>, because the aggressor's data is available on the
    same die."""))

    # ------------------------------------------------------------------
    c.절("T9.4 The via, the package, and what the standards do about it")

    c.날것(개념(
        "비아 스터브 (via stub) and back-drilling",
        """<p>A via that carries a signal from layer 2 to layer 3 in a twelve-layer
        board leaves the rest of the barrel — layers 4 to 12 — connected and unused.
        That stub is an open transmission line, and an open stub of length λ/4 presents
        a <b>short</b> at its resonant frequency: the signal is shorted to nothing at
        f = c/(4·L·√ε<sub>r</sub>).</p>
        <p>The fix is mechanical: <b>back-drill</b> the unused barrel away, leaving a
        stub short enough that the resonance sits above the band. It costs a
        manufacturing step, and the decision belongs to whoever writes the channel
        specification — which is why an IP datasheet should state the channel it assumes
        rather than a bare 'supports 25 Gb/s'.</p>""",
        어디에="Any board with more than a few layers running above ~10 Gb/s; the "
             "package substrate; the connector footprint.",
        언제="Board stack-up review — long before silicon exists, and the one review "
            "where an IP vendor's input is genuinely valuable.",
        어떻게="Compute the resonance from stub length, compare against 1.5× Nyquist, "
             "and if it lands in band, back-drill or change layers. State the assumed "
             "channel — including whether back-drilling is assumed — in the "
             "integration guide.",
        산업코드="""# Stub resonance, and the line that belongs in INTEGRATION.md.
#   stub 1.5 mm, eps_r 4.0  ->  f = c/(4*L*sqrt(eps_r))
#                             = 3e8/(4*1.5e-3*2) = 25 GHz
# At 25 Gbaud (Nyquist 12.5 GHz) that is 2x Nyquist -- survivable.
# At 50 Gbaud (Nyquist 25 GHz) it sits ON Nyquist -- fatal, back-drill required.
#
# INTEGRATION.md:
#   Channel assumed: <= 20 dB insertion loss at Nyquist, return loss <= -12 dB,
#   no via stub resonance below 1.5x Nyquist (back-drilling assumed above 25 Gb/s).""",
        주의="""The resonance depends on √ε<sub>r</sub>, and the effective ε<sub>r</sub>
            of a via barrel is not the laminate's datasheet number — it is closer to the
            bulk value than the stripline's effective value. Using the wrong one moves
            the predicted resonance by tens of per cent, which is the difference between
            'above the band' and 'in it'."""))

    c.날것(표("How a channel is actually specified, and what each part binds",
        ["Specification", "What it is", "What it binds"],
        [["S-parameters (.s4p)", "Measured 4-port network, differential",
          "Everything — the other rows are summaries of it"],
         ["Insertion loss at Nyquist", "|S21| in dB",
          "Equaliser strength; the first number anyone quotes"],
         ["Return loss (S11)", "Reflected energy",
          "Whether the loss is smooth or has notches"],
         ["ICR / ICN", "Integrated crosstalk ratio / noise",
          "Layout separation and connector choice"],
         ["<b>COM</b> (channel operating margin)", "A single dB figure from a "
          "standardised reference receiver applied to the measured S-parameters",
          "Pass/fail for Ethernet compliance — <b>and it is the number the customer "
          "will run</b>, not your simulation"]]))

    c.날것(짚기("""COM deserves a sentence of its own. It takes the measured channel,
    applies a <b>specified</b> reference transmitter and receiver (fixed equaliser
    architecture, fixed noise, fixed jitter), and returns one number in dB. That makes
    channels comparable, which is its purpose — but it also means a receiver that is
    better than the reference gets no credit, and one that is differently structured may
    be penalised. <b>Know your COM before promising a channel reach</b>, because the
    customer will compute it and will not care that your receiver is cleverer."""))

    # ------------------------------------------------------------------
    c.절("T9.5 What to do with this on Monday")

    c.날것(쓰는자리([
        ["삽입손실 · 표피효과 · 유전손실", "Before sizing the receiver",
         "Tap count, and which purchase order would reduce the problem"],
        ["반사계수 · 노치", "Board and package review",
         "Whether the channel is workable at all — equalisation will not fix a notch"],
        ["근단누화 · 원단누화", "Layout review",
         "Separation rules, and whether cancellation is even possible"],
        ["비아스터브 · 백드릴", "Stack-up, before fabrication",
         "A manufacturing step, and a line in the integration guide"],
        ["S파라미터 · COM", "The customer conversation",
         "The number they will actually compute — make sure you computed it first"]]))

    c.글(f"""The measured results to carry: in this model the skin-effect term rises as
    √f ({수(6.0,3,'dB')} → {수(8.5,3,'dB')} → {수(12.0,3,'dB')} → {수(17.0,3,'dB')}
    across four doublings) while the dielectric term rises as f
    ({수(2.0,3,'dB')} → {수(4.0,3,'dB')} → {수(8.0,3,'dB')} → {수(16.0,3,'dB')}) — so
    which one dominates depends on where you look. And a reflection of ρ = 0.2 at 4 UI
    puts a {수(-1.94,3,'dB')} notch at exactly {수(0.125,3)}/UI, matching the closed
    form to within {수(0.2,2,'%')}: <b>reflections are predictable, and that is precisely
    why they should be designed out rather than equalised.</b>""")

    c.글("""The next chapter returns to the inside of the chip and to a circuit family
    that trades bandwidth for accuracy in a way no continuous-time circuit can: switched
    capacitors.""")

    return c.완성()
