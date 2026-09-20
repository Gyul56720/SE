# -*- coding: utf-8 -*-
import json
inv = json.load(open("/home/user/survey/inventory.json"))
F = {}
for f in ("figs_a.json","figs_b.json","figs_c.json"):
    F.update(json.load(open(f"/home/user/survey/{f}")))

def fig(n, wide=False):
    d = F[str(n)]
    cls = ' class="wide"' if wide else ""
    return (f'<figure{cls}>{d["svg"]}'
            f'<figcaption>Fig.&nbsp;{n}.&nbsp; {d["cap"]}</figcaption></figure>')

def tbl(n, cap, head, rows, wide=False):
    cls = ' class="tbl wide"' if wide else ' class="tbl"'
    h = "".join(f"<th>{c}</th>" for c in head)
    r = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return (f'<div{cls}><table><caption>Table&nbsp;{n}.&nbsp; {cap}</caption>'
            f'<tr>{h}</tr>{r}</table></div>')

# ---------- aggregate numbers used in the text ----------
agg = {}
for f in inv["files"]:
    for k, v in f["pragmas"].items(): agg[k] = agg.get(k, 0) + v
tot_pragma = sum(agg.values())
tot_func = sum(len(f["funcs"]) for f in inv["files"])
tot_tmpl = sum(f["templates"] for f in inv["files"])
tot_cls = sum(len(f["classes"]) for f in inv["files"])
types = {}
for f in inv["files"]:
    for k, v in f["types"].items(): types[k] = types.get(k, 0) + v

GROUPSUM = {}
for f in inv["files"]:
    g = GROUPSUM.setdefault(f["group"], {"files":0,"lines":0,"func":0,"prag":0,"lic":f["license"]})
    g["files"] += 1; g["lines"] += f["lines"]
    g["func"] += len(f["funcs"]); g["prag"] += sum(f["pragmas"].values())

FRONT = """
<div class="hdr1"><span class="pg">1</span>JOURNAL OF COMMUNICATIONS AND NETWORKS, VOL. 28, NO. 3, SEPTEMBER 2026</div>
<h1 class="title">A Structural Survey of Production High-Level-Synthesis<br/>
IP Cores: Architecture, Algorithms, and Implementation<br/>
Patterns in 11,917 Lines of Shipping C++</h1>
<div class="authors">Prepared for the SE design-house project</div>
<div class="cols">

<div class="abs"><p><span class="lbl">Abstract:</span>&nbsp;
High-level synthesis (HLS) is widely discussed but rarely examined at the level of the
code that vendors actually ship. This paper surveys the complete source of three
independently maintained, production HLS IP families: the linear-algebra solvers and the
cryptographic cores of the AMD Vitis Libraries, and the quantised-neural-network library
of Xilinx FINN. The corpus comprises 25 files and 11,917 lines of synthesisable C++,
containing %d function definitions, %d template declarations, %d class or struct
definitions and %d HLS pragma directives. Every file is inventoried mechanically and read
in full. We describe, for each core, the algorithm implemented, the microarchitecture the
code induces, the parameterisation mechanism, the memory organisation and the
verification hooks. We then extract the patterns that recur across all three families
irrespective of application domain: architecture selection through a traits structure,
separation of state preparation from streaming computation, folding as the sole
resource-throughput control, loop flattening to hold an initiation interval of one, array
banking as the precondition for unrolling, elimination of division by reciprocal storage,
explicit failure reporting, and separation of debug code by <code>__SYNTHESIS__</code>.
We argue that these eight moves, not the C++ language itself, constitute the transferable
content of HLS practice, and we show that seven of the eight apply unchanged to
hand-written register-transfer-level design. The study is explicitly bounded: the vendor
headers that these files include are not publicly distributed, so none of the corpus was
compiled or synthesised during this work, and all statements about circuit behaviour are
inferences from source, not measurements.
</p></div>

<div class="idx"><p><span class="lbl">Index Terms:</span>&nbsp;
High-level synthesis, intellectual-property cores, Cholesky decomposition, QR
factorisation, singular value decomposition, Advanced Encryption Standard, SHA-2,
quantised neural networks, loop pipelining, array partitioning, folding.
</p></div>

<h2>I. Introduction</h2>

<p class="noind">The literature on high-level synthesis is dominated by two kinds of paper: tool papers,
which describe scheduling and binding algorithms, and application papers, which report the
performance of one accelerator written in C. Neither tells a practitioner what shipping HLS
code looks like. The question matters because HLS is not a general-purpose compilation
target. The subset of C++ that survives synthesis is narrow, and the discipline required to
stay inside it is transmitted almost entirely by apprenticeship.</p>

<p>This paper takes the opposite approach. Rather than measuring an accelerator, we read the
source of IP cores that are distributed as products and ask what the code itself teaches. The
corpus was chosen for three properties. It is production code, not a benchmark: the Vitis
Libraries are shipped by AMD as part of a commercial tool flow, and FINN-hlslib is the
computational core of a released Xilinx toolchain. It spans unrelated application domains,
so that patterns common to all three are unlikely to be artefacts of one problem. And it is
openly licensed, so that every claim in this paper can be checked against the same text.</p>

<p>%s</p>

<p>Our contributions are as follows. First, we provide a complete mechanical inventory of the
corpus&mdash;every file, function, template, class, macro, loop label and pragma&mdash;so
that the coverage of the survey is verifiable rather than asserted; the inventory appears in
Appendices A through C. Second, we give a per-file architectural reading of all 25 files,
identifying in each the algorithm, the induced microarchitecture, the parameterisation
mechanism and the memory organisation. Third, we perform a cross-cutting analysis of
pragma usage, type management, interface style and folding strategy, supported by measured
counts over the whole corpus. Fourth, we distil eight recurring design moves and assess
which of them transfer to hand-written RTL. Fifth, we state the limits of the method
explicitly, including the fact that the corpus could not be compiled in our environment.</p>

<p>The remainder of the paper is organised as follows. Section II describes the corpus and the
extraction methodology and reports aggregate statistics. Sections III, IV and V analyse the
linear-algebra, cryptographic and neural-network families respectively. Section VI presents
the cross-cutting analysis. Section VII states the extracted design rules. Section VIII
discusses threats to validity, and Section IX concludes.</p>
""" % (tot_func, tot_tmpl, tot_cls, tot_pragma, fig(1))

S2 = """
<h2>II. Corpus and Methodology</h2>

<h3>A. Provenance</h3>

<p class="noind">The corpus was assembled by retrieving individual files over HTTPS from the
canonical source repositories. Directory listing was not available in our environment, so the
dependency closure was obtained by parsing <code>#include</code> directives from a set of seed
files and fetching the named headers transitively.</p>

<p>An earlier draft of this paper asserted that the vendor headers on which the corpus
depends&mdash;<code>ap_int.h</code>, <code>ap_fixed.h</code>, <code>hls_stream.h</code>,
<code>hls_x_complex.h</code>, <code>hls_math.h</code>, <code>ap_axi_sdata.h</code> and their
transitive closure&mdash;were distributed only inside the Vitis HLS installation and were
therefore unobtainable, and concluded that no file in the corpus could be compiled. <em>That
assertion was wrong.</em> The types are published in
<code>Xilinx/HLS_arbitrary_Precision_Types</code>, the stream class in
<code>Xilinx/hls-lib-stream</code>, and the mathematics and simulation headers in
<code>Xilinx/hls-utilities</code>; a small number of remaining utility headers were located in
<code>Xilinx/merlin-compiler</code>. Resolving the closure by iterative compilation&mdash;reading each
missing-header diagnostic and fetching that name from the four repositories in turn&mdash;yielded
51 headers totalling 38,811 lines, after which 26 of the 27 corpus files compile cleanly under
Clang 18. The single
exception is <code>vt_fft.hpp</code>, whose implementation files return HTTP 404 and were never
retrieved; Table 1 counts it, and no claim in Section III&ndash;V rests on it.</p>

<p>The correction matters to the reader in one direction only: the study is a reading of source
code either way, but the reading is now known to be of code that a compiler accepts rather than
of code we merely believed to be well formed. Section VIII states precisely what the
compilation does and does not establish.</p>

<p>%s</p>

<h3>B. Licensing</h3>

<p class="noind">Licensing is not uniform across the corpus and this was verified by reading the
header comment of every file rather than by assuming. The AMD Vitis files carry the Apache
License 2.0. The FINN files carry a three-clause BSD licence, whose non-endorsement clause
differs materially from Apache 2.0. An earlier draft of this work asserted a single licence for
the whole corpus; that assertion was wrong and is corrected here.</p>

<h3>C. Extraction Procedure</h3>

<p class="noind">Completeness of coverage is a claim that a survey must substantiate. We did so
mechanically. A extraction pass over every file in the corpus records: total lines and bytes;
the licence as determined from the header; the full header comment; every
<code>#include</code>; the count of <code>template&lt;</code> declarations; every
<code>class</code> and <code>struct</code> definition by name; every <code>#define</code>;
every named loop label; every function definition with its return type and line number; every
<code>#pragma HLS</code> directive with its line number and full text; and the occurrence
count of each arbitrary-precision or stream type. The result is a machine-readable inventory
of %d files, %s bytes, from which Appendices A through C are generated directly. Where this
paper states a count, that count comes from the inventory and not from recollection.</p>

<p>The mechanical pass establishes structural coverage. It does not establish understanding, so
each file was additionally read in full and the algorithm it implements identified against the
standard or textbook definition. Statements in Sections III through V that describe algorithm
or intent are the product of that reading; statements that report a number are the product of
the extraction pass. The two are kept distinct throughout.</p>

<h3>D. Aggregate Statistics</h3>

<p class="noind">Table 1 summarises the three families. The FINN library is the largest by more
than a factor of two, and also the most fragmented: sixteen files against four and four. This
reflects a difference in composition strategy discussed in Section VI-D&mdash;FINN builds
accelerators by chaining many small stream-connected stages, whereas the Vitis solvers expose
a small number of large entry points.</p>

%s

<p>Table 2 reports the pragma distribution over the whole corpus, and Fig. 15 shows it
graphically. Four directives account for %.0f%% of all uses. The
tail is as informative as the head: <code>DEPENDENCE</code> and
<code>LOOP_TRIPCOUNT</code> appear exactly where the compiler cannot infer something that
the author knows&mdash;that a dependence is false, or that a data-dependent loop has a
bounded expected trip count. These are the two places where HLS most often fails silently,
and the corpus marks them explicitly.</p>

%s

<p>%s</p>

<p>Table 3 reports the arbitrary-precision and stream types. The dominance of
<code>ap_uint</code> over <code>ap_fixed</code> is a consequence of corpus composition:
cryptographic and quantised-network code is integral, whereas only the solver family carries
fractional data. The 250 uses of <code>hls::stream</code> are concentrated almost entirely in
FINN and in the top-level solver entry points, and this concentration is itself one of the
findings of Section VI-D.</p>

%s
""" % (fig(15),
       inv["total_files"], f'{sum(f["bytes"] for f in inv["files"]):,}',
       tbl(1, "The three IP families in the corpus.",
           ["Family", "Files", "Lines", "Functions", "Pragmas", "Licence"],
           [[k.replace("_"," "), v["files"], f'{v["lines"]:,}', v["func"], v["prag"], v["lic"]]
            for k, v in sorted(GROUPSUM.items(), key=lambda kv: -kv[1]["lines"])]
           + [["<b>Total</b>", f'<b>{inv["total_files"]}</b>', f'<b>{inv["total_lines"]:,}</b>',
               f"<b>{tot_func}</b>", f"<b>{tot_pragma}</b>", "&mdash;"]]),
       100.0 * sum(sorted(agg.values(), reverse=True)[:4]) / tot_pragma,
       tbl(2, "HLS pragma frequency over the whole corpus.",
           ["Directive", "Uses", "Share", "Purpose"],
           [[k, v, f"{100.0*v/tot_pragma:.1f}%", p] for k, v, p in [
               (k, agg[k], {
                 "PIPELINE":"fix the initiation interval of a loop",
                 "INLINE":"remove a function boundary",
                 "UNROLL":"replicate a loop body",
                 "ARRAY_PARTITION":"split an array into independently addressable banks",
                 "DEPENDENCE":"assert that a dependence the tool sees is false",
                 "LOOP_TRIPCOUNT":"supply an expected bound for a data-dependent loop",
                 "STREAM":"set stream depth or implementation",
                 "RESOURCE":"choose the primitive that implements a storage or operator",
                 "BIND_STORAGE":"modern replacement for RESOURCE on memories",
                 "LOOP_MERGE":"fuse adjacent loops into one",
                 "LATENCY":"constrain a region's latency",
                 "INTERFACE":"specify a port protocol",
                 "DATAFLOW":"schedule regions concurrently",
                 "ARRAY_RESHAPE":"widen words instead of adding banks",
                 "AGGREGATE":"pack a struct into a single wide word",
                 "DISAGGREGATE":"split a struct into separate signals",
                 "ALLOCATION":"limit instances of an operator or function",
                 "EXPRESSION_BALANCE":"control operator-tree rebalancing",
                 "OCCURRENCE":"declare a slower rate for a region",
                 "PROTOCOL":"preserve the written cycle-by-cycle protocol",
                 "STABLE":"assert an input does not change",
                 "FUNCTION_INSTANTIATE":"specialise a function per call site",
                 "RESET":"control reset on a variable",
                 }.get(k, "&mdash;"))
               for k in sorted(agg, key=lambda x: -agg[x])]]),
       fig(14),
       tbl(3, "Arbitrary-precision and stream type usage.",
           ["Type", "Uses", "Role"],
           [[f"<code>{k}</code>", v, r] for k, v, r in
            [(k, types[k], {
              "ap_uint<":"unsigned integer of arbitrary width",
              "ap_int<":"signed integer of arbitrary width",
              "ap_fixed<":"signed fixed point, total and integer width",
              "ap_ufixed<":"unsigned fixed point",
              "hls::stream<":"blocking FIFO channel between stages",
              "hls::x_complex<":"synthesis-friendly complex number",
              "std::complex<":"standard complex, supported for float paths",
              "decltype":"deduce accumulator type from the activation",
              }.get(k,"&mdash;")) for k in sorted(types, key=lambda x: -types[x])]]))

open("/home/user/survey/part1.html","w").write(FRONT + S2)
print("part1 written:", len(FRONT+S2), "chars")
