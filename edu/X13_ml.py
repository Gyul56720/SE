# -*- coding: utf-8 -*-
"""Volume I, Part X13 -- Machine-learning hardware, worked."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_mlhw():
    s = ['<h1 id="x13">X13. Machine-Learning Hardware, Worked</h1>']
    s.append("""<p>Neural-network accelerators are the largest category of new IP by
    value, and they are also the category where the gap between a quoted peak number and
    delivered performance is widest. The arithmetic that closes that gap is the roofline
    model and its refinements, and it is worth doing carefully because it decides the
    architecture before a line of RTL is written.</p>""")

    s.append("<h2>X13.1 The roofline, computed for real layers</h2>")
    s.append(derive("Arithmetic intensity and where the roof bends", [
        ("A kernel performs <i>W</i> operations and moves <i>Q</i> bytes.",
         "Definitions."),
        ("Arithmetic intensity <i>I</i> = <i>W</i>/<i>Q</i>, operations per byte.",
         "A property of the <i>algorithm and the dataflow</i>, not of the machine."),
        ("Achievable performance = min(<i>P</i><sub>peak</sub>, "
         "<i>I</i> &middot; <i>B</i>), with <i>B</i> the memory bandwidth.",
         "You cannot compute faster than the machine, nor faster than the data "
         "arrives."),
        ("The ridge point is at <i>I</i> = <i>P</i><sub>peak</sub>/<i>B</i>.",
         "<b>Below it the kernel is memory bound and peak FLOPS are irrelevant.</b>"),
        ("For a modern accelerator <i>P</i><sub>peak</sub>/<i>B</i> is in the hundreds.",
         "Which means most layers are memory bound unless the dataflow is designed to "
         "raise <i>I</i> &mdash; and raising <i>I</i> is what the whole accelerator "
         "architecture is for."),
    ]))
    layers = [
        ("Conv 3&times;3, 256&rarr;256, 56&times;56", 256, 256, 3, 56, 1),
        ("Conv 1&times;1, 512&rarr;128, 28&times;28", 512, 128, 1, 28, 1),
        ("Conv 3&times;3 depthwise, 512, 14&times;14", 1, 512, 3, 14, 512),
        ("Fully connected 4096&rarr;4096", 4096, 4096, 1, 1, 1),
        ("Attention QK&#7488;, <i>d</i>=64, <i>n</i>=1024", 64, 1024, 1, 1024, 1),
    ]
    rows = []
    for name, cin, cout, k, hw, groups in layers:
        macs = (cin // max(groups, 1)) * cout * k * k * hw * hw
        wbytes = (cin // max(groups, 1)) * cout * k * k * 1      # int8 weights
        abytes = cin * hw * hw * 1 + cout * hw * hw * 1
        Q = wbytes + abytes
        I = 2 * macs / Q
        rows.append([name, num(2 * macs / 1e6, 4), num(Q / 1024, 4), num(I, 4),
                     "<b>memory</b>" if I < 200 else "compute"])
    s.append(sweep("Arithmetic intensity of common layers, int8, no reuse beyond the "
                   "layer",
        ["Layer", "MOPs", "Bytes moved (kB)", "Ops per byte", "Bound by (ridge = 200)"],
        rows,
        "Computed assuming each weight and activation is read once from off-chip, "
        "which is the <i>worst</i> dataflow. <b>The point of an accelerator's on-chip "
        "memory hierarchy is to make this table wrong</b> by reusing data; how much it "
        "can reuse is the design."))
    s.append("""<div class="ms"><b>Depthwise convolution is the instructive row.</b> It
    has excellent parameter efficiency &mdash; which is why MobileNet-style networks use
    it &mdash; and terrible arithmetic intensity, because each weight is used for only one
    input channel. On an accelerator designed around dense convolution it can run at a few
    per cent of peak, so a network that is 4&times; cheaper in operations can be
    <i>slower</i> in wall-clock time. <b>This is the clearest example in the field of why
    operation counts are not a performance metric</b>, and it is a question worth asking
    any vendor: not &lsquo;what is your TOPS&rsquo; but &lsquo;what is your utilisation on
    a depthwise layer&rsquo;.</div>""")
    s.append(plot([0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000],
                  [("achievable TOPS",
                    [min(100.0, I * 0.5) for I in
                     (0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000)])],
                  "arithmetic intensity (ops/byte)", "achievable TOPS",
                  "A roofline for a 100 TOPS accelerator with 500 GB/s. The ridge is at "
                  "200 ops/byte; everything to its left is a bandwidth problem wearing a "
                  "compute problem's clothes.", logx=True))

    s.append("<h2>X13.2 Dataflow: what a systolic array is actually reusing</h2>")
    s.append(tab("Dataflow taxonomy by what stays still",
        ["Dataflow", "Held stationary", "Reuse obtained", "Weak when"],
        [["Weight stationary", "Weights in the PE",
          "Each weight is used for a whole batch or feature map",
          "Batch is 1 and the feature map is small"],
         ["Output stationary", "The partial sum in the PE",
          "No partial sums move &mdash; saves the widest data",
          "Few accumulations per output (1&times;1 convolutions)"],
         ["Input stationary", "The activation", "Each activation feeds many filters",
          "Few output channels"],
         ["<b>Row stationary</b>", "A row of the convolution in each PE",
          "<b>Balances all three reuse types</b>", "Complex control and mapping"],
         ["No local reuse", "Nothing", "&mdash;", "Always &mdash; it is the baseline "
          "that makes the others look good"]]))
    s.append(ex("Sizing a systolic array from a bandwidth limit",
        "A 256&times;256 int8 multiply&ndash;accumulate array at 1&nbsp;GHz, weight "
        "stationary. Off-chip bandwidth 100&nbsp;GB/s.",
        "Compute the peak rate, then compute the byte rate the array would demand with "
        "no reuse, then find the reuse factor required to keep it fed.",
        [("MACs per cycle", num(256 * 256)),
         ("Peak operations", num(2 * 256 * 256 * 1e9 / 1e12, 4, "TOPS")),
         ("Operands needed per cycle with no reuse",
          num(2 * 256 * 256) + "&nbsp;bytes"),
         ("Byte rate demanded", num(2 * 256 * 256 * 1e9 / 1e12, 4, "TB/s")),
         ("Available", num(0.1, 3, "TB/s")),
         ("<b>Reuse factor required</b>",
          "<b>" + num(2 * 256 * 256 * 1e9 / 100e9, 4) + "&times;</b>"),
         ("On-chip SRAM to achieve it (order)", "megabytes")],
        "<b>By quoting the TOPS figure and stopping.</b> The array is 131&nbsp;TOPS and "
        "the memory system can feed it 1/1300th of what it wants. Every architectural "
        "feature of a real accelerator &mdash; the weight buffer, the activation buffer, "
        "the tiling, the fusion of adjacent layers &mdash; exists to close that factor of "
        "1300, and <b>the accelerator is really a memory system with multipliers "
        "attached</b>. A design house pitching an accelerator should lead with the "
        "memory hierarchy, because that is what a knowledgeable buyer will ask about "
        "first."))

    s.append("<h2>X13.3 Quantisation: where the bits actually go</h2>")
    rng = np.random.default_rng(21)
    rows = []
    W = rng.normal(0, 0.05, (512, 512))
    X = np.maximum(rng.normal(0, 1.0, (512, 64)), 0)     # post-ReLU activations
    ref = W @ X
    for bits in (8, 6, 4, 3, 2):
        # symmetric per-tensor
        sw = np.abs(W).max() / (2 ** (bits - 1) - 1)
        sx = np.abs(X).max() / (2 ** bits - 1)
        Wq = np.round(W / sw) * sw
        Xq = np.round(X / sx) * sx
        e = Wq @ Xq - ref
        snr_t = 10 * math.log10(float((ref ** 2).mean() / (e ** 2).mean()))
        # per-channel weight scale
        swc = np.abs(W).max(1, keepdims=True) / (2 ** (bits - 1) - 1)
        Wqc = np.round(W / swc) * swc
        ec = Wqc @ Xq - ref
        snr_c = 10 * math.log10(float((ref ** 2).mean() / (ec ** 2).mean()))
        rows.append([num(bits), num(snr_t, 4), num(snr_c, 4),
                     num(snr_c - snr_t, 3), num(512 * 512 * bits / 8 / 1024, 4)])
    s.append(sweep("Measured SQNR of a 512&times;512 int matrix product, per-tensor vs. "
                   "per-channel weight scaling",
        ["Bits", "Per-tensor SQNR (dB)", "Per-channel SQNR (dB)", "Gain (dB)",
         "Weight storage (kB)"], rows,
        "Gaussian weights and post-ReLU activations, seed 21. <b>Per-channel scaling is "
        "nearly free in hardware</b> &mdash; one extra multiply per output channel, not "
        "per MAC &mdash; and buys several dB, which at low bit widths is the difference "
        "between a usable and an unusable network."))
    s.append("""<div class="warn"><b>The outlier problem, and why it changed transformer
    accelerators.</b> The table above uses Gaussian weights, for which max-based scaling
    is reasonable. Real transformer activations are not Gaussian: a few channels carry
    values tens of times larger than the rest, and a per-tensor scale chosen to contain
    them leaves the remaining channels occupying two or three bits. The measured
    consequence is that naive int8 quantisation of a large language model loses far more
    accuracy than the same procedure applied to a convolutional network, and the remedies
    &mdash; per-channel and per-group scales, keeping outlier channels in higher
    precision, or migrating the scale between activations and weights &mdash; all cost
    hardware that a convolution-era accelerator does not have. <b>An accelerator's
    quantisation support is a workload-specific design decision, not a generic
    feature.</b></div>""")
    s.append(prob("Why does int8 inference usually retain accuracy while int8 training "
                  "does not?",
        "Because the two use the numbers differently. Inference computes a forward pass "
        "whose outputs pass through nonlinearities that are insensitive to small "
        "perturbations, and errors do not accumulate across iterations &mdash; each "
        "inference is independent. Training computes gradients, which are (a) small "
        "differences of large numbers, so relative precision matters far more, (b) "
        "accumulated over many steps, so bias accumulates exactly as Part&nbsp;X1's "
        "truncating accumulator did, and (c) spread over an enormous dynamic range, "
        "because gradients of different layers differ by orders of magnitude. The "
        "practical resolution is the asymmetric one: <b>low-precision multiplies with "
        "higher-precision accumulation and master weights</b>, plus loss scaling to move "
        "small gradients out of the denormal region. bfloat16 exists for exactly the "
        "(c) reason &mdash; it sacrifices mantissa, which inference cares about, to keep "
        "exponent range, which training cares about."))
    s.append(prob("A customer wants your accelerator to be &lsquo;future proof&rsquo;. "
                  "What can you honestly offer?",
        "Not architectural coverage of models that do not exist. What you can offer is "
        "specific and worth more than a vague claim: <b>a programmable dataflow</b> rather "
        "than a fixed one, so a new layer shape maps at some efficiency rather than not "
        "at all; <b>a well-specified fallback path</b> to a host or a DSP for operators "
        "the array cannot do, with measured numbers for that path so the customer can "
        "compute the Amdahl penalty themselves; <b>a compiler that is open enough to "
        "extend</b>, since in practice the compiler ages faster than the silicon; and "
        "<b>measured utilisation on a set of named, versioned models</b>, so the customer "
        "can extrapolate from evidence rather than from adjectives. <b>Offering the "
        "measurement methodology is itself a differentiator</b>: most datasheets in this "
        "field quote one peak number and one optimistic model, and a buyer who has been "
        "burned once recognises the difference immediately."))
    return "\n".join(s)
