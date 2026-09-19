# -*- coding: utf-8 -*-
"""Volume I, Part X40 -- The coverage map: which theory an IP block actually uses."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import prob, num


# (topic, where it is used in IP, this book's chapter)
MAP = [
    ("Signals and systems, LTI, convolution",
     "Every filter, equaliser, channel model", "A1, E1, X22"),
    ("Fourier, Laplace, z-transform, poles and zeros",
     "Filter design, loop stability, spectral analysis", "A2, X23"),
    ("Sampling, aliasing, reconstruction",
     "Every converter boundary; rate change", "A3, X22, X12"),
    ("Probability, random processes, noise",
     "Link budgets, yield, jitter, metastability", "A4, X25, X16, X3"),
    ("Detection and estimation, likelihood, CRB",
     "Receivers, synchronisation, calibration loops", "X25"),
    ("Information theory, capacity, entropy",
     "Code choice, compression, quantiser design", "I1, X25, X29"),
    ("Linear algebra, SVD, conditioning",
     "MIMO, beamforming, calibration, word lengths", "A5, X24, X30"),
    ("Numerical methods, iteration, refinement",
     "Dividers, square root, matrix engines", "X9, X24"),
    ("Optimisation: convex, ILP, graph algorithms",
     "Every EDA tool; word-length allocation; scheduling", "I3, X26"),
    ("Boolean algebra, BDD, SAT",
     "Equivalence checking, formal, ATPG", "Z2, X33"),
    ("Automata and FSM theory",
     "Control logic, protocol checkers, parsers", "Z3, C2"),
    ("Graph theory",
     "STA, retiming, clock skew scheduling, routing", "I4, X26, X34"),
    ("Finite fields and modular arithmetic",
     "Reed-Solomon, BCH, AES, GCM, RSA, ECC", "I2, X5, X36"),
    ("Number theory",
     "Public-key engines, NTT for post-quantum", "R1, X36"),
    ("Coding theory: block, convolutional, LDPC, polar",
     "Every link and every storage device", "F2, X5, X29"),
    ("Cryptographic primitives and side channels",
     "Security IP, roots of trust, secure boot", "H3, X15, X36"),
    ("Fixed-point arithmetic, quantisation, dither",
     "Every DSP block without exception", "X1"),
    ("Computer arithmetic: adders, multipliers, division, CORDIC",
     "Every datapath", "C1, X9"),
    ("Floating point and mixed precision",
     "DSP, ML accelerators, scientific blocks", "X9, X13"),
    ("Semiconductor device physics",
     "Delay, leakage, variability, reliability", "L1, B1, X16"),
    ("CMOS circuits, logical effort, sizing",
     "Every gate; the sizing the tool performs", "B2, X26, X34"),
    ("Timing: setup, hold, skew, corners, OCV",
     "Sign-off of every block", "B3, X2"),
    ("Metastability and clock domain crossing",
     "Every multi-clock design", "C3, X3"),
    ("Interconnect RC, crosstalk, transmission lines",
     "Long wires, I/O, package, board", "B4, X14, G1"),
    ("Power: dynamic, leakage, DVFS, gating",
     "Every block's specification", "B2, X7"),
    ("Power delivery network, IR drop, di/dt",
     "Any block with large switching current", "X32"),
    ("Thermal", "Packaging limits, throttling, reliability", "L3, X16"),
    ("Analogue blocks: kT/C, matching, gain-bandwidth",
     "Converters, PHYs, PLLs, sensor interfaces", "B5, X31"),
    ("Data converters and time interleaving",
     "Every mixed-signal boundary; SerDes DSP receivers", "X12, X31"),
    ("PLL, CDR, jitter and phase noise",
     "Every clock and every link", "X12, X21, X39"),
    ("Feedback and control in digital loops",
     "Adaptation, AGC, calibration, thermal", "L4, X21"),
    ("Memory: SRAM, DRAM, ECC, multi-port",
     "The largest object in most blocks", "J1, X10"),
    ("Caches and coherence",
     "Processor and accelerator subsystems", "D3, X28"),
    ("Computer architecture: ISA, pipelines, hazards",
     "Processor IP; any block behind one", "D1, D2, X19"),
    ("Interconnect protocols and ordering",
     "Every block's boundary", "J3, X11, X37"),
    ("Queueing and performance modelling",
     "Buffer sizing, QoS, latency budgets", "Q1, X18"),
    ("Hardware data structures: CAM, hashing, Bloom",
     "Networking, storage, security IP", "X35"),
    ("Compression and entropy coding",
     "Codecs, storage, trace", "J4, X20"),
    ("Image and colour science",
     "Camera and display IP", "M3, X38"),
    ("Wireless PHY: OFDM, MIMO, synchronisation",
     "Modem IP", "K1, X30"),
    ("Wireline PHY: equalisation, PAM, FEC",
     "SerDes, Ethernet, PCIe", "F1, X4, Y2, Y3"),
    ("Electromagnetics and antennas",
     "RF front ends, package, EMC", "G1, Q4"),
    ("Radar and sensing signal processing",
     "Automotive and industrial IP", "G2"),
    ("Machine learning and quantisation",
     "NPU IP and any block that embeds one", "M2, X13"),
    ("Logic synthesis, mapping, retiming",
     "The flow every block passes through", "X34"),
    ("Physical design, congestion, floorplanning",
     "What your RTL makes easy or impossible", "N2, X14"),
    ("Design for test: scan, ATPG, BIST, compression",
     "Every chip that is manufactured", "R2, X27"),
    ("Reliability, yield, statistics, functional safety",
     "Pricing, qualification, automotive markets", "K3, N3, X16"),
    ("Verification theory: coverage, mutation, formal",
     "Half the effort of every block", "H1, X8, X33"),
    ("High-level synthesis internals",
     "Exploration; some production blocks", "Q2, Y12"),
    ("Hardware-software interface, registers, drivers",
     "Every block with a control plane", "M1, Y10"),
]

OUT = [
    ("Compiler theory beyond HLS scheduling",
     "A block does not compile; the tool does"),
    ("Operating system internals",
     "Relevant to the driver author, not to the RTL"),
    ("Distributed consensus",
     "A chip is not a distributed system in that sense"),
    ("Computability and complexity as such",
     "Except where it classifies an EDA problem &mdash; that part is in X26"),
    ("Quantum computing",
     "Included briefly for context only; no current IP block uses it"),
    ("Database theory, web systems, graphics rendering pipelines",
     "Different industries"),
]


def ch_map():
    s = ['<h1 id="x40">X40. The Coverage Map: Which Theory an IP Block Uses</h1>']
    s.append(f"""<p>This book covers the theory that is used when designing, modelling
    and verifying semiconductor IP, and deliberately does not cover theory that is not.
    This part is the map: <b>{len(MAP)} topic areas</b>, what each one is used for in a
    real block, and where it is treated here. It is meant to be read as a checklist
    &mdash; if you are asked about a block and cannot find its theory in this table, the
    table has a gap and the gap is worth reporting.</p>""")
    rows = [[f"<b>{t}</b>", u, f"<code>{c}</code>"] for t, u, c in MAP]
    s.append(tab("Theory used in IP design, and where this book treats it",
        ["Topic", "Where it is used in a real block", "Chapters"], rows))
    s.append("<h2>X40.1 What is deliberately left out, and why</h2>")
    s.append("""<p>Excluding material is a decision that should be stated rather than
    left as an omission a reader discovers. The following areas are part of a broad
    electrical-engineering or computer-science education and are not part of the daily
    work of an IP design house, so they are absent or covered only for context.</p>""")
    s.append(tab("Out of scope, with the reason",
        ["Area", "Why it is not here"],
        [[f"<b>{a}</b>", r] for a, r in OUT]))
    s.append("""<div class="note"><b>The boundary is a judgement and it moves.</b> Two of
    the rows above were inside the boundary twenty years ago and are outside it now, and
    at least one &mdash; machine learning &mdash; moved the other way within a decade. The
    test applied here is concrete: <b>does a working IP engineer use this to make a
    decision about a block?</b> If a topic only ever appears as background for a decision
    someone else makes, it is context rather than content, and this book says so instead
    of padding.</div>""")
    s.append(prob("You are handed a block type this map does not cover. How do you find "
                  "its theory?",
        "Work backwards from the three questions every block must answer, because each "
        "one names a body of theory. <b>What does it compute, and how accurately?</b> "
        "That is the algorithm and its numerical behaviour &mdash; a signal-processing, "
        "coding or arithmetic question, and Parts&nbsp;X1 and X24 give the tools for the "
        "accuracy half whatever the algorithm is. <b>How fast must it go, and what does "
        "that cost?</b> That is Part&nbsp;X2's timing budget and Part&nbsp;X18's "
        "queueing, and the answer is always a parallelism and memory-bandwidth analysis "
        "&mdash; Part&nbsp;X13's roofline applies far outside machine learning. <b>How "
        "will you know it is right?</b> That is Part&nbsp;X8, and it is domain "
        "independent. <b>Only the first question has domain-specific theory</b>, and for "
        "that the fastest route is the standard's own reference implementation plus one "
        "survey paper, read in the order Part&nbsp;Y6 prescribes. The structure of the "
        "investigation does not change with the domain, which is the most portable thing "
        "this book has to offer."))
    return "\n".join(s)
