# -*- coding: utf-8 -*-
import json
inv = json.load(open("/home/user/survey/inventory.json"))
F = {}
for f in ("figs_a.json","figs_b.json","figs_c.json"): F.update(json.load(open(f"/home/user/survey/{f}")))
def fig(n, wide=False):
    d=F[str(n)]; c=' class="wide"' if wide else ""
    return f'<figure{c}>{d["svg"]}<figcaption>Fig.&nbsp;{n}.&nbsp; {d["cap"]}</figcaption></figure>'
def tbl(n,cap,head,rows,wide=False):
    c=' class="tbl wide"' if wide else ' class="tbl"'
    h="".join(f"<th>{x}</th>" for x in head)
    r="".join("<tr>"+"".join(f"<td>{x}</td>" for x in row)+"</tr>" for row in rows)
    return f'<div{c}><table><caption>Table&nbsp;{n}.&nbsp; {cap}</caption><tr>{h}</tr>{r}</table></div>'
def bn(n): return next(f for f in inv["files"] if f["name"]==n)
aes, sha = bn("aes.hpp"), bn("sha224_256.hpp")
FN = {f["name"]: f for f in inv["files"] if f["group"]=="finn_hlslib"}

S4 = """
<h2>IV. The Cryptographic Family</h2>

<p class="noind">The security family is the most regular code in the corpus. Block ciphers and
hash functions have fixed round counts, no data-dependent branching and no dynamic memory
behaviour; they are, in the terms of Section VI-F, the case HLS handles best. The value of
reading them lies not in algorithmic subtlety but in seeing how bit-level manipulation is
expressed and how storage primitives are chosen.</p>

<h3>A. Advanced Encryption Standard &mdash; <code>aes.hpp</code> (%s lines)</h3>

<h4>1) Class organisation</h4>
<p class="noind">The file defines %s classes. The root, <code>aesTable</code>, holds the
substitution tables. <code>aesEnc&lt;W&gt;</code> and <code>aesDec&lt;W&gt;</code> are primary
templates whose bodies are empty; the work is done in explicit specialisations for
<i>W</i>&nbsp;&isin;&nbsp;{128,&nbsp;192,&nbsp;256}. This is a deliberate choice over a runtime
key-length parameter: each key length has a different round count and a different key schedule,
and specialising eliminates both from the hardware.</p>

<h4>2) Separation of key expansion from block processing</h4>
<p class="noind">Each specialisation exposes two members:</p>

<pre>void updateKey(ap_uint&lt;W&gt; cipherkey);
void process(ap_uint&lt;128&gt; plaintext,
             ap_uint&lt;W&gt;   cipherkey,
             ap_uint&lt;128&gt;&amp; ciphertext);</pre>

<p>The expanded schedule lives in <code>key_list[]</code> between calls. A session that
encrypts many blocks under one key runs the schedule once. Fig. 12 shows the split. The general
principle&mdash;<em>identify state that outlives one datum and give it its own entry
point</em>&mdash;recurs in FINN, where weights are loaded once and reused across
<code>NF</code> folds, and in the solver family, where a factorisation is amortised over many
right-hand sides.</p>

%s

<h4>3) The round function</h4>
<p class="noind">The round body is worth quoting because it shows how bit manipulation maps to
hardware:</p>

<pre>state = plaintext ^ key_list[0];
for (round_counter = 1; round_counter &lt;= 10; round_counter++) {
    for (int i = 0; i &lt; 16; i++) {
#pragma HLS unroll
        state(i*8+7, i*8) = ssbox[state(i*8+7, i*8)];   // SubBytes
    }
    tmp_1 = state(15, 8);
    state(15, 8)  = state(47, 40);                      // ShiftRows
    state(47, 40) = state(79, 72);
    ...
    if (round_counter &lt; 10) { /* MixColumns: GFMul2, GFMul3 */ }
    state ^= key_list[round_counter];
}</pre>

<p>ShiftRows consists entirely of bit-slice assignments on an <code>ap_uint&lt;128&gt;</code>.
In software this is data movement; in hardware it is <em>rewiring</em> and costs nothing. The
permutation is free, and recognising which operations are free is a large part of reading HLS
code correctly. Fig. 11 shows the round datapath with this annotation.</p>

%s

<h4>4) Storage selection</h4>
<p class="noind">The substitution tables carry an explicit resource directive:</p>

<pre>#pragma HLS resource variable = iibox core = ROM_nP_LUTRAM</pre>

<p>The choice of LUT-based ROM over block RAM is forced by the access pattern. SubBytes is
unrolled over all sixteen bytes, so sixteen independent lookups must complete in one cycle. A
block RAM offers two ports; distributed LUT ROM can be replicated as many times as the
unrolled loop requires. The pragma is not a hint here, it is a correctness-of-schedule
requirement, and it illustrates the same dependency seen in the solver family: unrolling is only
legal when the memory can serve it.</p>

<h4>5) Galois-field arithmetic</h4>
<p class="noind">MixColumns requires multiplication in GF(2<sup>8</sup>) by the constants 2 and
3. The file provides <code>GFMul2</code> and <code>GFMul3</code> as helper functions rather than
using a general multiplier. Multiplication by 2 is a shift and a conditional exclusive-or with
the field polynomial; multiplication by 3 is that result exclusive-ored with the operand. Both
reduce to a handful of gates. The decryption path additionally requires multiplication by 9,
11, 13 and 14, which is why <code>aesDec</code> is larger than <code>aesEnc</code> and why
inverse MixColumns dominates the decryption area.</p>

<h4>6) The single PPA control</h4>
<p class="noind">Unlike the solver family, this file exposes no architecture switch. The
resource&ndash;throughput trade is controlled by whether the round loop is unrolled: rolled, the
core occupies one round of logic and takes ten cycles per block; fully unrolled, it becomes a
ten-stage pipeline with roughly ten times the area and ten times the throughput. Partial
unrolling gives intermediate points. This one-dimensional design space is characteristic of
fixed-round cryptographic primitives.</p>

<h3>B. SHA-224/256 &mdash; <code>sha224_256.hpp</code> (%s lines)</h3>

<p class="noind">The hash core is organised as a small dataflow pipeline rather than as a single
function: message padding, message-schedule generation and the round loop are separate stages
connected by streams. Fig. 13 shows the arrangement. Because the schedule word
<i>W</i><sub>t</sub> for round <i>t</i> depends only on earlier schedule words, the schedule
stage can run ahead of the compression stage, and the two overlap.</p>

%s

<p>The file carries %s pragmas in %s lines&mdash;a density of %.1f per hundred lines, the
highest in the corpus. Two features account for this. The round loop is fully unrolled over the
eight working variables, each of which becomes a register, and the rotation and shift operations
on 32-bit words become fixed wiring. And the file supports both SHA-224 and SHA-256 from one
body, differing only in the initial hash value and the truncation of the output, so the
conditional paths need explicit scheduling control.</p>

<p>Debug support follows the pattern seen in <code>cholesky.hpp</code>: a
<code>_XF_SECURITY_PRINT</code> macro is defined to nothing unless <code>_DEBUG</code> is set,
and <code>&lt;cstdio&gt;</code> is included only when <code>__SYNTHESIS__</code> is undefined.</p>

<h3>C. Shared Types and Utilities</h3>

<p class="noind">Two small files complete the family. <code>xf_security/types.hpp</code> (58
lines) defines packed structures used as stream payloads&mdash;typically a data word paired
with an end-of-message flag&mdash;so that control travels with data through the stream network
rather than on side channels. <code>xf_security/utils.hpp</code> (44 lines) provides endianness
conversion and word-assembly helpers. Neither contains a pragma, and both are pure type
definitions; they are included here for completeness of coverage.</p>

%s

<h2>V. The Quantised Neural-Network Family</h2>

<p class="noind">FINN-hlslib is the largest and most fragmented part of the corpus: %s files and
%s lines. The fragmentation is structural rather than incidental. An accelerator is assembled by
instantiating a chain of stream-connected stages, each of which is independently folded, and
each stage is a separate header. Fig. 10 shows a representative chain.</p>

%s

<h3>A. Matrix&ndash;Vector&ndash;Activate Unit &mdash; <code>mvau.hpp</code> (%s lines)</h3>

<h4>1) Folding</h4>
<p class="noind">This is the computational core of the library and the clearest statement of the
folding idea in the corpus:</p>

<pre>template&lt;unsigned MatrixW, unsigned MatrixH,
         unsigned SIMD, unsigned PE, unsigned MMV, ... &gt;
void Matrix_Vector_Activate_Batch(hls::stream&lt;TI&gt; &amp;in,
                                  hls::stream&lt;TO&gt; &amp;out,
                                  TW const &amp;weights,
                                  TA const &amp;activation,
                                  int const reps, R const &amp;r) {
  unsigned const NF = MatrixH / PE;     // vertical folds
  unsigned const SF = MatrixW / SIMD;   // horizontal folds
  unsigned const TOTAL_FOLD = NF * SF;</pre>

<p>The physical arithmetic is <code>SIMD</code>&times;<code>PE</code> multiply&ndash;accumulate
units, fixed at compile time. A larger matrix does not produce a larger circuit; it produces
more cycles. Fig. 7 shows the tiling. Three parameters&mdash;<code>SIMD</code>,
<code>PE</code> and <code>MMV</code>&mdash;span the entire resource&ndash;throughput design
space of the layer, and the same two divisions determine both the cycle count and the buffer
depths.</p>

%s

<h4>2) Loop flattening</h4>
<p class="noind">The nested fold loops are merged into a single iteration space, and the source
comment states why:</p>

<pre>// everything merged into a common iteration space (one "big"
// loop instead of smaller nested loops) to get the
// pipelinening the way we want
unsigned const TOTAL_FOLD = NF * SF;
for(unsigned i = 0; i &lt; reps * TOTAL_FOLD; i++) {
#pragma HLS pipeline style=flp II=1
  ...
  if(++sf == SF) { sf = 0; ... ++nf; }
}</pre>

<p>A nested loop pipeline drains at every outer-loop boundary: the inner pipeline empties
before the outer iteration advances, and the cost is proportional to the pipeline depth times
the number of outer iterations. Flattening removes the boundary entirely and the counters
<code>sf</code>, <code>nf</code> and <code>tile</code> are maintained by hand. Fig. 8
illustrates the difference. This is among the most transferable techniques in the corpus,
because the same reasoning applies verbatim to a hand-written RTL controller.</p>

%s

<h4>3) Input reuse and accumulator placement</h4>
<p class="noind">Two further decisions are visible in the same loop body:</p>

<pre>if(nf == 0) { inElem = in.read(); inputBuf[sf] = inElem; }
else        { inElem = inputBuf[sf]; }
...
decltype(activation.init(0,0)) accu[MMV][PE];
#pragma HLS ARRAY_PARTITION variable=accu complete dim=0</pre>

<p>The input vector is read from the stream exactly once and buffered for reuse across the
<code>NF</code> vertical folds; the buffer depth is <code>SF</code>, not the matrix width. And
the accumulator array is partitioned <em>completely</em>, which turns every element into a
register. Complete partitioning is appropriate here because the array is small and every element
is written every cycle; cyclic partitioning, as used in the solver family, is the right choice
when the array is large and the access stride is one.</p>

<p>The accumulator type is deduced with <code>decltype(activation.init(0,0))</code> rather than
being named. The activation object therefore determines the accumulator width, which keeps the
numeric contract in one place instead of two.</p>

<h3>B. Vector&ndash;Vector&ndash;Activate &mdash; <code>vvau.hpp</code> (%s lines)</h3>

<p class="noind">The depthwise counterpart of the MVAU. In a depthwise convolution each output
channel depends on exactly one input channel, so the weight matrix is block diagonal and the
<code>SIMD</code> dimension collapses. The file is %s lines with %s pragmas and mirrors the MVAU
structure&mdash;the same flattened loop, the same folding counters&mdash;with the inner product
taken over the kernel window rather than over input channels.</p>

<h3>C. Sliding Window Generator &mdash; <code>slidingwindow.h</code> (%s lines)</h3>

<p class="noind">At %s lines this is the largest file in the entire corpus, larger than any
solver, and it computes no arithmetic at all. Its task is to convert a raster-order pixel
stream into the sequence of overlapping <i>K</i>&times;<i>K</i> windows that the MVAU consumes:
the hardware equivalent of <code>im2col</code>. Fig. 9 shows the line-buffer structure.</p>

%s

<p>The size is explained by the number of cases. Stride one and stride greater than one need
different buffer management; padding must be synthesised at the borders; the input may be
narrower or wider than the buffer word; depthwise and standard convolutions traverse channels
differently; and the buffer itself may be mapped to block RAM, LUT RAM or URAM depending on its
size. The file carries %s pragmas, second only to <code>slidingwindow</code>'s own size in the
corpus, and %s distinct function definitions covering these combinations.</p>

<p>That a data-movement block is the largest component is itself a finding. In quantised
inference the multiply&ndash;accumulate array is cheap; delivering operands to it at rate is
expensive. The same asymmetry appears in the solver family, where memory banking rather than
arithmetic determines the achievable initiation interval.</p>

<h3>D. Stream Utilities &mdash; <code>streamtools.h</code> (%s lines)</h3>

<p class="noind">%s functions in %s lines, all of signature stream-to-stream. The
operations are: width conversion in both directions, padding and cropping of feature maps,
duplication of a stream to several consumers, limiting the number of packets, insertion of
explicit FIFOs, flattening and lane interleaving. Fig. 16 illustrates width conversion.</p>

%s

<p>Width conversion deserves comment because it is what makes independent folding possible. If
stage <i>A</i> naturally produces <code>SIMD_A</code> values per cycle and stage <i>B</i>
consumes <code>SIMD_B</code>, a converter between them lets each stage be folded for its own
resource budget without forcing a common word size on the whole chain. Without it the folding
factors of adjacent stages would be coupled, and the design space would collapse to a single
global parameter.</p>

<h3>E. Pooling &mdash; <code>maxpool.h</code> (%s lines)</h3>

<p class="noind">%s functions and %s pragmas. Max pooling over binary values degenerates to a
logical OR, and the file provides that specialisation separately from the general comparison
tree. The general case reuses the sliding-window machinery to present pooling windows, then
reduces each window with a comparator tree whose depth is logarithmic in the window size.
Average pooling is also present and is more expensive: it requires an adder tree and a division
by the window area, which is implemented as a multiplication by a precomputed reciprocal&mdash;
the same substitution seen in <code>cholesky.hpp</code>.</p>

<h3>F. Activations and Thresholding &mdash; <code>activations.hpp</code> (%s lines)</h3>

<p class="noind">%s class definitions in %s lines. The central idea is that for a quantised
network the activation function and the re-quantisation step collapse into a single comparison
against a monotone threshold set. Instead of scaling an accumulator and applying a nonlinearity,
the hardware compares the accumulator against
<i>T</i><sub>0</sub>&nbsp;&lt;&nbsp;<i>T</i><sub>1</sub>&nbsp;&lt;&nbsp;&hellip; and emits the
index of the interval. Fig. 17 shows the structure.</p>

%s

<p>The consequence is that no multiplier appears in the activation path at all. The classes
provided include <code>Identity</code>, binary and multi-bit thresholding with per-channel
parameters, and variants that fold a bias into the threshold set. The
<code>activation.init(nf, pe)</code> member seen in the MVAU belongs to this interface: it
supplies the initial accumulator value, which is how a bias is added without an extra adder.</p>

<h3>G. Weight Storage &mdash; <code>weights.hpp</code> (%s lines)</h3>

<p class="noind">%s classes in %s lines. The file adapts the logical weight matrix to the
physical organisation the folded datapath needs. The MVAU requests
<code>weights.weights(tile)</code> and expects <code>PE</code> rows of <code>SIMD</code> values;
the storage class is responsible for having arranged the memory so that this is a single
access. For binary networks the packing is dense&mdash;<code>SIMD</code> weights occupy
<code>SIMD</code> bits&mdash;and the file provides a specialised adapter for that case. The
%s pragmas are all storage-binding directives.</p>

<h3>H. Type Interpretation &mdash; <code>interpret.hpp</code> (%s lines)</h3>

<p class="noind">%s classes and %s pragmas in %s lines. This file answers a question that does
not arise in floating-point code: given a packed bit vector, what numbers does it represent?
The interpreters cover unsigned and signed binary, ternary, and fixed-point encodings, and they
are supplied to the MVAU as the <code>TSrcI</code>, <code>TDstI</code> and
<code>TWeightI</code> template parameters. Separating interpretation from storage means that the
same packed memory can be read as signed or unsigned without copying, and that the
multiply&ndash;accumulate primitive can specialise on the pair of interpretations it is given.</p>

<h3>I. Multiply&ndash;Accumulate Primitives &mdash; <code>mac.hpp</code> (%s lines)</h3>

<p class="noind">The lowest level of the library. The header comment states the intent: perform
the product of two operands and let HLS choose the best resource. For binary operands the
product is an exclusive-nor and the accumulation is a population count, so no DSP block is used
at all. For higher precisions the operation maps to a DSP slice. The file carries %s pragmas in
%s lines and exists so that the MVAU body can be written once against an abstract
<code>mac&lt;SIMD&gt;</code> regardless of the precision in use.</p>

<h3>J. Direct Memory Access &mdash; <code>dma.h</code> (%s lines)</h3>

<p class="noind">The boundary between the accelerator and the memory system. The header comment
describes it as a block accessing AXI4 memory and producing HLS streams. Two directions are
provided, memory-to-stream and stream-to-memory, with the burst length and the AXI word width
as template parameters. %s functions in %s lines. This is where the
<code>INTERFACE</code> pragmas that define the external protocol appear, and it is the only part
of the library that knows about addresses; every other stage sees streams only.</p>

<h3>K. Layer Composition &mdash; <code>convlayer.h</code> (%s lines)</h3>

<p class="noind">%s functions in %s lines with only %s pragmas. The file contains almost no
logic: it instantiates a sliding-window generator, an MVAU and the required stream adapters, and
wires them together. The low pragma count is the point&mdash;composition is structural, and the
scheduling decisions have already been made inside the components. This is the level at which an
IP consumer works, and the parameter list of the layer function is the union of the folding
parameters of its parts.</p>

<h3>L. Fault Tolerance &mdash; <code>tmrcheck.hpp</code> (%s lines)</h3>

<p class="noind">Triple modular redundancy: three replicas of a computation, a majority vote,
and an error flag raised when the replicas disagree. Fig. 18 shows the structure. Its presence
in a neural-network library is worth noting. It is the only component in the corpus that
addresses reliability rather than performance, and it indicates that the library targets
deployments&mdash;automotive, aerospace&mdash;where a functional-safety argument is required.
The cost is a factor of three in area, which is why it is an opt-in component rather than a
property of the datapath.</p>

%s

<h3>M. Remaining Components</h3>

<p class="noind"><code>upsample.hpp</code> (%s lines) implements nearest-neighbour upsampling for
square feature maps, used in decoder paths. <code>mmv.hpp</code> (%s lines) defines the
multiple-matrix-vector type that carries several pixels through one datapath.
<code>utils.hpp</code> (%s lines) provides a non-synthesisable stream logger for debugging,
guarded so that it disappears in hardware. <code>bnn-library.h</code> (%s lines) is a
convenience header that includes the others and contains no definitions of its own. All four are
listed in full in Appendix A.</p>

%s
""" % (aes["lines"], len(aes["classes"]), fig(12), fig(11),
       sha["lines"], fig(13),
       sum(sha["pragmas"].values()), sha["lines"],
       100.0*sum(sha["pragmas"].values())/sha["lines"],
       tbl(5, "Cryptographic family: structure of the four files.",
           ["File", "Lines", "Fn", "Cls", "Prag", "Standard"],
           [["<code>aes.hpp</code>", aes["lines"], len(aes["funcs"]), len(aes["classes"]),
             sum(aes["pragmas"].values()), "FIPS 197, key 128/192/256"],
            ["<code>sha224_256.hpp</code>", sha["lines"], len(sha["funcs"]),
             len(sha["classes"]), sum(sha["pragmas"].values()), "FIPS 180-4"],
            ["<code>xf_security/types.hpp</code>", bn("types.hpp")["lines"], 0, 0, 0,
             "stream payload types"],
            ["<code>xf_security/utils.hpp</code>", bn("utils.hpp")["lines"], 0, 0, 0,
             "endianness and word assembly"]], wide=True),
       len(FN), f'{sum(f["lines"] for f in FN.values()):,}', fig(10, True),
       FN["mvau.hpp"]["lines"], fig(7),
       fig(8),
       FN["vvau.hpp"]["lines"], FN["vvau.hpp"]["lines"], sum(FN["vvau.hpp"]["pragmas"].values()),
       FN["slidingwindow.h"]["lines"], f'{FN["slidingwindow.h"]["lines"]:,}', fig(9, True),
       sum(FN["slidingwindow.h"]["pragmas"].values()), len(FN["slidingwindow.h"]["funcs"]),
       FN["streamtools.h"]["lines"], len(FN["streamtools.h"]["funcs"]),
       f'{FN["streamtools.h"]["lines"]:,}', fig(16),
       FN["maxpool.h"]["lines"], len(FN["maxpool.h"]["funcs"]), sum(FN["maxpool.h"]["pragmas"].values()),
       FN["activations.hpp"]["lines"], len(FN["activations.hpp"]["classes"]), FN["activations.hpp"]["lines"],
       fig(17),
       FN["weights.hpp"]["lines"], len(FN["weights.hpp"]["classes"]), FN["weights.hpp"]["lines"],
       sum(FN["weights.hpp"]["pragmas"].values()),
       FN["interpret.hpp"]["lines"], len(FN["interpret.hpp"]["classes"]),
       sum(FN["interpret.hpp"]["pragmas"].values()), FN["interpret.hpp"]["lines"],
       FN["mac.hpp"]["lines"], sum(FN["mac.hpp"]["pragmas"].values()), FN["mac.hpp"]["lines"],
       FN["dma.h"]["lines"], len(FN["dma.h"]["funcs"]), FN["dma.h"]["lines"],
       FN["convlayer.h"]["lines"], len(FN["convlayer.h"]["funcs"]), FN["convlayer.h"]["lines"],
       sum(FN["convlayer.h"]["pragmas"].values()),
       FN["tmrcheck.hpp"]["lines"], fig(18),
       FN["upsample.hpp"]["lines"], FN["mmv.hpp"]["lines"], FN["utils.hpp"]["lines"],
       FN["bnn-library.h"]["lines"],
       tbl(6, "FINN-hlslib: all sixteen files.",
           ["File", "Lines", "Fn", "Cls", "Prag", "Role"],
           [[f'<code>{n}</code>', FN[n]["lines"], len(FN[n]["funcs"]), len(FN[n]["classes"]),
             sum(FN[n]["pragmas"].values()), r] for n, r in [
             ("slidingwindow.h","raster stream to convolution windows"),
             ("streamtools.h","width conversion, padding, duplication, FIFO"),
             ("maxpool.h","max and average pooling"),
             ("activations.hpp","threshold-based quantised activation"),
             ("convlayer.h","composition of a convolution layer"),
             ("mvau.hpp","matrix-vector-activate, the compute core"),
             ("interpret.hpp","bit-vector to number interpretation"),
             ("vvau.hpp","depthwise vector-vector-activate"),
             ("dma.h","AXI4 memory to stream and back"),
             ("mac.hpp","multiply-accumulate primitives"),
             ("tmrcheck.hpp","triple modular redundancy"),
             ("upsample.hpp","nearest-neighbour upsampling"),
             ("weights.hpp","packed weight storage adapter"),
             ("utils.hpp","non-synthesisable stream logger"),
             ("mmv.hpp","multiple-matrix-vector payload type"),
             ("bnn-library.h","aggregate include header"),
           ]], wide=True))

open("/home/user/survey/part3.html","w").write(S4)
print("part3 written:", len(S4), "chars")
