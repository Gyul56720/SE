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

agg={}
for f in inv["files"]:
    for k,v in f["pragmas"].items(): agg[k]=agg.get(k,0)+v
tot=sum(agg.values())
strm={f["name"]: f["types"].get("hls::stream<",0) for f in inv["files"]}
top_strm=sorted(strm.items(), key=lambda kv:-kv[1])[:8]
dens=sorted(((f["name"], 100.0*sum(f["pragmas"].values())/max(f["lines"],1),
              sum(f["pragmas"].values()), f["lines"]) for f in inv["files"]),
            key=lambda x:-x[1])[:10]

S6 = """
<h2>VI. Cross-Cutting Analysis</h2>

<p class="noind">Having read the three families separately, we now ask what they share. The
families were written by different teams for unrelated domains under different licences, so
agreement between them is evidence about HLS practice rather than about one project's
conventions.</p>

<h3>A. Pragma Usage as a Map of the Difficulty</h3>

<p class="noind">Table 2 gave the raw distribution. The interpretation is more useful than the
numbers. Directives fall into three groups by what they tell the tool.</p>

<p><i>Scheduling directives</i>&mdash;<code>PIPELINE</code>, <code>UNROLL</code>,
<code>INLINE</code>, <code>LOOP_MERGE</code>&mdash;state the designer's throughput intent.
They express what the circuit should do. <i>Structural directives</i>&mdash;
<code>ARRAY_PARTITION</code>, <code>RESOURCE</code>, <code>BIND_STORAGE</code>,
<code>STREAM</code>&mdash;make that intent physically possible by supplying ports and choosing
primitives. <i>Assertions</i>&mdash;<code>DEPENDENCE</code>,
<code>LOOP_TRIPCOUNT</code>&mdash;supply knowledge the compiler cannot derive.</p>

<p>The ratio between the first two groups is the practical lesson. Scheduling directives
outnumber structural ones, but a scheduling directive without its matching structural directive
does not fail loudly; it silently produces a worse initiation interval. The corpus never unrolls
an array-touching loop without partitioning the array, and the partition factor is always
derived from the unroll factor rather than chosen independently.</p>

<p>The assertion group is small but marks the hardest places. <code>DEPENDENCE</code> is an
unchecked promise: if the designer is wrong about a dependence being false, the hardware is
wrong and simulation of the C model will not reveal it. <code>LOOP_TRIPCOUNT</code> marks
data-dependent iteration and appears predominantly in <code>svd.hpp</code>, the one genuinely
irregular algorithm in the corpus.</p>

%s

<h3>B. Parameterisation: Traits Versus Template Arguments</h3>

<p class="noind">Two strategies appear. The solver family uses a <em>traits structure</em>: a
small number of template arguments select the traits type, and the traits type carries both the
internal numeric types and the architecture switches. The FINN family uses <em>direct template
arguments</em>: <code>SIMD</code>, <code>PE</code>, <code>MMV</code> and the interpretation
types appear in the function signature.</p>

<p>The difference is not stylistic. A traits structure is preferable when the parameters are
numerous, interdependent and mostly defaulted&mdash;the consumer overrides one field and
inherits the rest, and specialisations can adjust widths coherently for complex or fixed-point
inputs. Direct arguments are preferable when the parameters are few, orthogonal and always
supplied. Cholesky has seven internal types that must vary together with the input type;
enumerating them at every call site would be unusable. The MVAU has three folding parameters
that the caller must always choose deliberately; hiding them in a traits structure would
obscure the only decision that matters.</p>

<p>Both are strictly better than the third option, which the corpus never uses: runtime
parameters. Every structural parameter in all 25 files is a compile-time constant, because a
runtime-variable fold factor would require the hardware to be built for the maximum anyway.
The one runtime dimension in the corpus is <code>potrf</code>'s matrix order <code>m</code>,
and there the compile-time <code>NMAX</code> still sizes the circuit.</p>

<h3>C. Memory Architecture</h3>

<p class="noind">Three partitioning modes appear and the choice among them is determined by the
access pattern, not by preference.</p>

<ul>
<li><code>complete</code>&mdash;every element becomes a register. Used for the MVAU accumulator
array, which is small and entirely rewritten each cycle.</li>
<li><code>cyclic</code>&mdash;element <i>i</i> goes to bank <i>i</i>&nbsp;mod&nbsp;<i>f</i>.
Used for the Cholesky partial-sum arrays, where consecutive elements are consumed in the same
cycle by an unrolled loop of stride one.</li>
<li><code>block</code>&mdash;contiguous ranges per bank. Appropriate when different units own
disjoint regions, as in <code>potrf</code>, where the working array is declared
<code>dataA[NCU][...][N]</code> so that the unit index is already the outermost dimension and
no partitioning directive is needed at all.</li>
</ul>

<p>The last case is worth emphasising because it is the cheapest technique in the corpus:
<em>choosing the array's dimension order so that the parallel index is outermost makes banking
implicit.</em> No pragma is required when the declaration already expresses the intent.</p>

<h3>D. Interface Style</h3>

<p class="noind">Table 7 shows where <code>hls::stream</code> is used. The concentration is
extreme: FINN uses streams for every inter-stage connection, and the Vitis solvers use them only
at the top-level entry points while working on arrays internally.</p>

%s

<p>The consequence is architectural. Because FINN stages communicate only through streams, they
share no arrays, so no false dependences can arise between them and each may be scheduled
concurrently with an independent initiation interval. Back-pressure is implicit in the blocking
read. The cost is that every stage must be written in a streaming style, and that a stage which
genuinely needs random access to a large buffer&mdash;such as the sliding-window
generator&mdash;must manage that buffer internally and present a stream interface outward. That
is exactly why <code>slidingwindow.h</code> is the largest file in the corpus.</p>

<p>The solver family makes the opposite trade. A matrix decomposition needs random access to the
working matrix by nature, so the internal representation is an array and only the boundary is
streamed. The lesson for a designer is that the interface style should follow the access
pattern of the algorithm, and that a streaming interface at the boundary can be provided
regardless of what happens inside.</p>

<h3>E. Folding and the Resource&ndash;Throughput Trade</h3>

<p class="noind">Every core in the corpus exposes a resource&ndash;throughput control, and in
every case it takes the same form: a compile-time divisor that maps problem size onto cycles
while holding the arithmetic area fixed.</p>

%s

<p>The names differ&mdash;<code>UNROLL_FACTOR</code> in Cholesky, <code>NCU</code> in
<code>potrf</code>, <code>SIMD</code> and <code>PE</code> in the MVAU, round-loop unrolling in
AES&mdash;but the structure is identical. Given a problem of size <i>N</i> and a fold factor
<i>P</i>, the circuit contains <i>O</i>(<i>P</i>) arithmetic and executes in
<i>O</i>(<i>N</i>/<i>P</i>) cycles. What differs between the families is only how many
independent fold dimensions exist: one for AES, one for <code>potrf</code>, two for the MVAU
(<code>SIMD</code> across inputs and <code>PE</code> across outputs), and three if
<code>MMV</code> is counted.</p>

<p>This observation generalises to hand-written RTL without modification. A sub-rate parallel
datapath in a serialiser&ndash;deserialiser receiver, where <i>P</i> lanes each run at 1/<i>P</i>
of the symbol rate, is the same construction with the same trade.</p>

<h3>F. Loop Structure and the Initiation Interval</h3>

<p class="noind">Three techniques recur.</p>

<p><i>Flattening.</i> The MVAU merges nested fold loops into one iteration space and maintains
the counters by hand, because a nested pipeline drains at each outer boundary (Fig. 8). The cost
of the drain is the pipeline depth times the number of outer iterations, which for a deeply
folded layer dominates.</p>

<p><i>Recurrence shortening.</i> The Cholesky ARCH 2 decision&mdash;replacing packed indexing
with a plain two-dimensional array&mdash;is a recurrence-shortening move. The address
computation sat on the loop-carried path; removing it shortens the recurrence and allows a
lower initiation interval.</p>

<p><i>Partial-sum carrying.</i> Rather than recomputing an inner product per output, both
Cholesky ARCH 2 and the MVAU carry partial sums in arrays and update them all in one sweep. This
converts a reduction, which has a long dependence chain, into an accumulation across independent
banks.</p>

<p>All three are RTL techniques stated in C. None of them is about the C++ language.</p>

<h3>G. Numeric Type Management</h3>

<p class="noind">The corpus never uses one width for a whole datapath. Cholesky names seven
internal types; the MVAU deduces the accumulator type from the activation object with
<code>decltype</code>; FINN separates <em>storage</em> from <em>interpretation</em> so that a
packed memory can be read as signed or unsigned without copying.</p>

<p>The underlying rule is that the width of a product, the width of an accumulator and the
width of a stored result are three different quantities. A product of two <i>w</i>-bit operands
needs 2<i>w</i> bits; an accumulation of <i>n</i> such products needs
2<i>w</i>&nbsp;+&nbsp;&lceil;log<sub>2</sub>&nbsp;<i>n</i>&rceil;; the stored result may be
narrower than either. Collapsing them to one parameter either wastes area at the product or
overflows at the accumulator, and the failure mode of the latter is silent.</p>

<h3>H. Failure Reporting and Debug Separation</h3>

<p class="noind">Two conventions appear in every family. Failures are reported through a return
value or an output reference: <code>cholesky</code> returns <code>int</code>,
<code>potrf</code> writes <code>info</code> following the LAPACK convention, and the FINN
thresholding classes saturate rather than wrap. Diagnostic output is present but excluded from
synthesis by <code>#ifndef __SYNTHESIS__</code> or by a macro that expands to nothing unless a
debug symbol is defined.</p>

<p>The combination matters because the two audiences are different. During C simulation the
designer wants a message identifying the offending input. In hardware the consumer wants a
status bit it can branch on. Providing only the first leaves the deployed circuit silent; the
corpus provides both and pays one flip-flop for it.</p>

<h2>VII. Extracted Design Rules</h2>

<p class="noind">Fig. 19 collects the eight moves that appear in all three families. We restate
them here as rules, with the evidence for each and an assessment of whether the rule is specific
to HLS or transfers to hand-written RTL.</p>

%s

%s

<p>Seven of the eight transfer unchanged. Only rule 4, loop flattening, is phrased in a way
specific to HLS&mdash;but its content, that a controller should not idle at a loop boundary, is
an ordinary finite-state-machine concern. The conclusion we draw is that the transferable
content of this corpus is architectural, and that a designer who internalises these eight moves
has acquired something largely independent of whether the eventual output is produced by a
synthesis tool or written by hand.</p>

<h2>VIII. Threats to Validity</h2>

<p class="noind">We state the limits of this study explicitly, because a survey that does not is
inviting its reader to over-generalise.</p>

<p><i>The corpus compiles; it was not synthesised.</i> After the header closure described in
Section II-A was resolved, 25 of the 26 corpus files compile under <code>g++ -std=c++14</code>
against the public Xilinx headers, and a small program exercising
<code>ap_uint</code>, <code>ap_int</code>, <code>ap_fixed</code> and
<code>hls::stream</code> builds and runs. This establishes that the sources are well formed and
that the types behave as the text assumes. It establishes nothing about hardware. No file was
put through a synthesis tool, because none is available in our environment: there is no Vitis
HLS, no Catapult, and no open-source C-to-RTL compiler that accepts this dialect. Consequently
every statement in Sections III&ndash;V about scheduling, initiation interval, area or the
circuit a pragma induces remains an <em>inference from source text and from the stated intent
in comments</em>. We have measured no latency, area or frequency figure for this corpus and
report none.</p>

<p><i>The compilation is with a different compiler.</i> Vitis HLS uses a Clang-derived front end
with its own extensions; we used GCC with <code>-fpermissive</code>, which was required because
one Xilinx macro, <code>_AP_UNUSED_PARAM</code>, is rejected by GCC's stricter template
name-lookup rules. A file that compiles under GCC therefore does not prove it compiles under
Vitis HLS, although the converse failure would have been strong evidence of a problem.</p>

<p><i>The sample is small and vendor-biased.</i> Three families, two vendors, both from the same
FPGA ecosystem. Patterns common to all three may reflect a shared house style or shared tool
constraints rather than a general truth about HLS. An application-specific-integrated-circuit
HLS flow using a different tool might differ in ways this corpus cannot reveal.</p>

<p><i>Function extraction is regular-expression based.</i> The inventory in the appendices was
produced by pattern matching, not by parsing C++. Macro-generated definitions and unusual
declarator syntax may be missed or miscounted. The counts should be read as close approximations
with a systematic bias toward undercounting, not as exact figures from a compiler front end.</p>

<p><i>Reading is interpretation.</i> Where a comment states intent we quote it. Where no comment
exists, the architectural reading in Sections III through V is our inference, and a reader with
access to the original designers might learn that a decision was made for a reason we did not
identify.</p>

<p><i>The corpus is a snapshot.</i> Files were retrieved on a single date from the default
branch of each repository. These are living projects; the line counts will change.</p>

<h2>IX. Conclusion</h2>

<p class="noind">We surveyed 11,917 lines of production high-level-synthesis C++ across three
independently developed IP families: matrix decompositions, cryptographic primitives, and
quantised neural-network operators. Every file was inventoried mechanically and read in full.</p>

<p>The principal finding is that the transferable content of this code is not the C++ and not
the pragmas considered individually, but a small set of architectural moves that the three
families share despite having nothing else in common. A core is parameterised so that
architecture is a consumer choice; state that outlives one datum gets its own entry point;
problem size maps to cycles through a fold factor while arithmetic area stays fixed; loops are
flattened so that the pipeline does not drain; every array an unrolled loop touches is banked,
with the factor derived from the unroll factor; division is removed by storing reciprocals;
failure is reported through a status the caller can act on; and debug code is separated by
<code>__SYNTHESIS__</code>.</p>

<p>Seven of these eight apply without modification to hand-written register-transfer-level
design. This is, we think, the most useful thing the corpus has to say to a designer deciding
how much to invest in HLS: the tool is a means of expressing these decisions, not a substitute
for making them. The decisions are the skill.</p>

<p>The study's principal limitation is that it is a reading, not a measurement. We could not
compile the corpus, and we report no performance figures for it. A natural continuation would
be to reproduce two or three of these cores in an open toolchain, synthesise them, and test
whether the architectural choices the source makes are the ones a measurement would endorse.</p>
""" % (fig(19, True),
       tbl(7, "Concentration of stream interfaces (top eight files).",
           ["File", "<code>hls::stream</code> uses", "Interface style"],
           [[f"<code>{n}</code>", v,
             "streaming throughout" if "finn" in next(f["group"] for f in inv["files"] if f["name"]==n)
             else "streamed boundary, array interior"] for n, v in top_strm if v]),
       tbl(8, "The folding parameter in each core.",
           ["Core", "Fold parameter", "Fixed hardware", "Cycles"],
           [["<code>cholesky</code> ARCH 2", "<code>UNROLL_FACTOR</code>",
             "<i>O</i>(<i>P</i>) multiply-accumulate", "<i>O</i>(<i>N</i><sup>3</sup>/<i>P</i>)"],
            ["<code>potrf</code>", "<code>NCU</code>", "<i>NCU</i> column engines",
             "<i>O</i>(<i>N</i><sup>3</sup>/<i>NCU</i>)"],
            ["<code>svdPairs</code>", "concurrent index pairs", "rotation units",
             "sweeps &times; <i>N</i>/2<i>P</i>"],
            ["MVAU", "<code>SIMD</code> &times; <code>PE</code>",
             "<code>SIMD</code>&times;<code>PE</code> MACs", "<i>NF</i> &times; <i>SF</i>"],
            ["VVAU", "<code>PE</code>", "<code>PE</code> MACs", "kernel &times; <i>NF</i>"],
            ["AES", "round-loop unroll", "1 to 10 round stages", "10 down to 1"],
           ], wide=True),
       fig(19) if False else "",
       tbl(9, "The eight rules, their evidence, and whether they transfer to hand-written RTL.",
           ["#", "Rule", "Evidence in the corpus", "Transfers to RTL"],
           [["1", "Parameterise architecture, not just size",
             "<code>choleskyTraits::ARCH</code> selects three circuits; <code>svdBasic</code> vs <code>svdPairs</code>",
             "Yes &mdash; a generator parameter"],
            ["2", "Give long-lived state its own entry point",
             "<code>aesEnc::updateKey</code> vs <code>process</code>; MVAU weight reuse across <i>NF</i>",
             "Yes"],
            ["3", "Fold: fixed arithmetic, size maps to cycles",
             "<code>SIMD</code>&times;<code>PE</code>; <code>NCU</code>; <code>UNROLL_FACTOR</code>",
             "Yes &mdash; sub-rate parallelism"],
            ["4", "Flatten nested loops to hold II = 1",
             "MVAU merged iteration space with manual <code>sf</code>/<code>nf</code> counters",
             "Partly &mdash; becomes FSM design"],
            ["5", "Bank every array an unrolled loop touches",
             "<code>ARRAY_PARTITION cyclic factor = UNROLL_FACTOR</code> in <code>choleskyAlt2</code>",
             "Yes &mdash; explicit memory instances"],
            ["6", "Remove division; store reciprocals",
             "<code>diag_internal</code> holds 1/<i>L<sub>jj</sub></i>; pooling multiplies by 1/area",
             "Yes"],
            ["7", "Report failure through a status",
             "<code>cholesky</code> returns <code>int</code>; <code>potrf</code> writes <code>info</code>",
             "Yes &mdash; a status port"],
            ["8", "Separate debug from synthesis",
             "<code>#ifndef __SYNTHESIS__</code>; <code>_XF_SECURITY_PRINT</code>",
             "Yes &mdash; <code>`ifndef SYNTHESIS</code>"],
           ], wide=True))

open("/home/user/survey/part4.html","w").write(S6)
print("part4 written:", len(S6), "chars")
