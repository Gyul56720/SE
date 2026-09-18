# -*- coding: utf-8 -*-
import json
inv = json.load(open("/home/user/survey/inventory.json"))
F = {}
for f in ("figs_a.json","figs_b.json","figs_c.json"):
    F.update(json.load(open(f"/home/user/survey/{f}")))
def fig(n, wide=False):
    d = F[str(n)]; c = ' class="wide"' if wide else ""
    return f'<figure{c}>{d["svg"]}<figcaption>Fig.&nbsp;{n}.&nbsp; {d["cap"]}</figcaption></figure>'
def tbl(n, cap, head, rows, wide=False):
    c = ' class="tbl wide"' if wide else ' class="tbl"'
    h = "".join(f"<th>{x}</th>" for x in head)
    r = "".join("<tr>"+"".join(f"<td>{x}</td>" for x in row)+"</tr>" for row in rows)
    return f'<div{c}><table><caption>Table&nbsp;{n}.&nbsp; {cap}</caption><tr>{h}</tr>{r}</table></div>'
def byname(n):
    return next(f for f in inv["files"] if f["name"] == n)

ch, qr, sv, po = byname("cholesky.hpp"), byname("qrf.hpp"), byname("svd.hpp"), byname("potrf.hpp")

S3 = """
<h2>III. The Linear-Algebra Family</h2>

<p class="noind">The Vitis solver family implements matrix decompositions that recur throughout
wireless detection, radar beamforming, state estimation and computational finance. All four
files share a structure: a traits template carrying internal types and architecture switches;
two or three alternative implementations of the same mathematics; a dispatcher that selects
among them; and a stream-interfaced top-level entry point. We treat <code>cholesky.hpp</code>
in detail because it exhibits the pattern most clearly, then note what differs in the others.</p>

<h3>A. Cholesky Decomposition &mdash; <code>cholesky.hpp</code> (%d lines)</h3>

<h4>1) Problem and contract</h4>
<p class="noind">Given a Hermitian positive-definite matrix <i>A</i>, the decomposition produces
a lower triangular <i>L</i> with <i>A</i>&nbsp;=&nbsp;<i>LL</i><sup>H</sup>. The public entry
point is stream-interfaced and, critically, returns a status:</p>

<pre>template &lt;bool LowerTriangularL, int RowsColsA,
          class InputType, class OutputType,
          typename TRAITS = choleskyTraits&lt;LowerTriangularL,
                            RowsColsA, InputType, OutputType&gt; &gt;
int cholesky(hls::stream&lt;InputType&gt;&amp;  matrixAStrm,
             hls::stream&lt;OutputType&gt;&amp; matrixLStrm);</pre>

<p>The return type is <code>int</code>, not <code>void</code>. If a diagonal entry becomes
negative&mdash;which happens exactly when <i>A</i> is not positive definite&mdash;the core sets
<code>return_code = 1</code> and the caller can act. This is a deliberate interface decision and
it is, as Section VI-H argues, the single most commonly omitted feature in student and
portfolio IP.</p>

<h4>2) The traits structure</h4>
<p class="noind">Parameterisation is carried by a traits template rather than by a long list of
template arguments:</p>

<pre>template &lt;bool LowerTriangularL, int RowsColsA,
          typename InputType, typename OutputType&gt;
struct choleskyTraits {
    typedef InputType  PROD_T;        // product
    typedef InputType  ACCUM_T;       // accumulator
    typedef InputType  ADD_T;         // subtract
    typedef InputType  DIAG_T;        // diagonal
    typedef InputType  RECIP_DIAG_T;  // 1/diagonal
    typedef InputType  OFF_DIAG_T;    // off-diagonal
    typedef OutputType L_OUTPUT_T;    // stored result
    static const int ARCH          = 1;
    static const int INNER_II      = 1;
    static const int UNROLL_FACTOR = 1;
    static const int UNROLL_DIM    = (LowerTriangularL ? 1 : 2);
    static const int ARCH2_ZERO_LOOP = true;
};</pre>

<p>Two things are notable. First, <em>seven distinct internal types</em> are named. The width of
a product is not the width of an accumulator, and neither is the width at which a reciprocal
should be stored; conflating them either wastes area or overflows. Second, the same structure
carries <em>architecture</em> switches. The consumer of this IP selects a circuit by choosing a
number, and the vendor ships three circuits for one algorithm.</p>

<p>The template is specialised for <code>hls::x_complex</code>, <code>std::complex</code>,
<code>ap_fixed</code>, and complex forms of <code>ap_fixed</code>. The specialisations differ
in the widths they assign: complex accumulation needs additional headroom, and fixed-point
reciprocals need more fractional bits than the value they invert.</p>

%s

<h4>3) The three architectures</h4>
<p class="noind">Fig. 2 summarises the selection. <code>choleskyBasic</code> is the reference:
minimum resources, maximum latency. <code>choleskyAlt</code> reduces latency at the cost of
resources and stores <i>L</i> packed into a one-dimensional array of
(<i>N</i><sup>2</sup>&minus;<i>N</i>)/2 words, halving memory. The price is an address
computation on every iteration:</p>

<pre>int i_sub1 = i - 1;
int i_off  = ((i_sub1 * i_sub1 - i_sub1) / 2) + i_sub1;
...
prod = -L_internal[i_off + k] * hls::x_conj(L_internal[j_off + k]);</pre>

<p><code>choleskyAlt2</code> reverses that decision, and the source comment states the reason
without ambiguity:</p>

<pre>// To avoid array index calculations every iteration this
// architecture uses a simple 2D array rather than a
// optimized/packed triangular matrix.</pre>

<p>The address arithmetic sits on the recurrence that determines the achievable initiation
interval. Doubling the memory removes it. Fig. 3 contrasts the two layouts. This is the first
of the general rules we extract: <em>when address generation limits the initiation interval,
spend memory to delete it.</em></p>

%s

<h4>4) Elimination of division</h4>
<p class="noind">Both improved architectures store the reciprocal of the diagonal rather than
the diagonal itself. The comment is explicit: the intent is to avoid the latency of a divide in
the inner loop. Every subsequent off-diagonal update is then a multiplication by
<code>diag_internal[j]</code>. A dedicated helper, <code>cholesky_rsqrt</code>, is specialised
for <code>ap_fixed</code> so that the reciprocal square root is computed once per column in the
appropriate format.</p>

<p>The same move recurs throughout hardware arithmetic and it generalises beyond
reciprocals: a normalisation by a constant factor <i>&alpha;</i>&nbsp;=&nbsp;3/4 is written as
<code>(|v| * 3) &gt;&gt; 2</code> rather than as a division, and a scaling by a power of two is
a shift. Division is the one arithmetic primitive with no cheap hardware realisation, and
production code arranges never to need it in a loop.</p>

<h4>5) Partial sums and the necessity of banking</h4>
<p class="noind">The highest-performance architecture carries two auxiliary arrays:</p>

<pre>ACCUM_T square_sum_array[RowsColsA];
ACCUM_T product_sum_array[RowsColsA];

#pragma HLS ARRAY_PARTITION variable = square_sum_array
        cyclic dim = 1 factor = UNROLL_FACTOR
#pragma HLS ARRAY_PARTITION variable = product_sum_array
        cyclic dim = 1 factor = UNROLL_FACTOR
#pragma HLS ARRAY_PARTITION variable = L_internal
        cyclic dim = UNROLL_DIM factor = UNROLL_FACTOR</pre>

<p>Rather than recomputing an inner product for each output element, the algorithm sweeps one
column and updates the partial sums of <em>every</em> row simultaneously. Fig. 4 shows the
dataflow. The unrolled inner loop therefore requires <code>UNROLL_FACTOR</code> concurrent
accesses to each array, which a single memory with two ports cannot supply. Cyclic partitioning
by the same factor creates exactly the banks required (Fig. 14).</p>

<p>The dependency runs in one direction only: the partition factor is derived from the unroll
factor, not chosen independently. This is why <code>ARRAY_PARTITION</code> is the third most
frequent directive in the corpus (Table 2) and why, in practice, an initiation interval that
refuses to reach one is almost always a memory-port problem rather than an arithmetic one.</p>

%s

<h4>6) Debug separation</h4>
<p class="noind">Diagnostic output is present but excluded from synthesis:</p>

<pre>if (cholesky_sqrt_op(A_minus_sum, new_L_diag)) {
#ifndef __SYNTHESIS__
    printf("ERROR: Trying to find the square root of a negative number\\n");
#endif
    return_code = 1;
}</pre>

<p>The pattern separates two audiences. During C simulation the message identifies which input
broke the decomposition; after synthesis the same condition is still detected and still
reported, but through the return code, which costs one flip-flop.</p>

<h4>7) Function inventory</h4>
<p class="noind">The file defines %d functions and %d template declarations. Besides the three
architectures and the dispatcher, the helpers are: <code>cholesky_rsqrt</code> (two
overloads), <code>cholesky_prod_sum_mult</code> (three overloads, covering real, x_complex and
std::complex mixed-type products), and <code>cholesky_sqrt_op</code>. The overload sets exist
because <code>hls::x_complex</code> does not support multiplication by a real of a different
type; rather than widening the operand, the library supplies the exact operation needed.</p>

<h3>B. QR Factorisation &mdash; <code>qrf.hpp</code> (%d lines)</h3>

<p class="noind">QR factorisation is implemented by Givens rotations rather than by
Gram&ndash;Schmidt or Householder reflections. The choice is a hardware one: a Givens rotation
touches exactly two rows and requires only a 2&times;2 product, so the computation decomposes
into a regular array of identical small operations with short dependence chains. Modified
Gram&ndash;Schmidt, by contrast, has a long serial reduction per column, and Householder needs
a full-vector norm before any output is produced.</p>

%s

<p>The core helpers are <code>qrf_givens</code>, which computes the rotation coefficients
<i>c</i>, <i>s</i> and the resulting <i>r</i>; and <code>qrf_mm</code>, which applies a
2&times;2 rotation to a pair of values. A variant, <code>qrf_mm_or_mag</code>, takes
<code>use_mag</code> and <code>extra_pass</code> flags and selects between applying the rotation
and substituting a precomputed magnitude. The <code>extra_pass</code> mechanism exists to
handle fixed-point cases where a single pass loses accuracy; the same function body serves both
passes, parameterised by a flag, rather than being duplicated.</p>

<p><code>qrf_givens</code> has three overloads covering the real, <code>x_complex</code> and
<code>std::complex</code> cases. The file declares %d templates in %d lines&mdash;the highest
template density in the solver family&mdash;because every arithmetic helper is specialised per
input type rather than being written once against a generic numeric concept.</p>

<p>The basic architecture, <code>qrf_basic</code>, is stream-interfaced like Cholesky. As in
<code>cholesky.hpp</code>, a traits structure selects the architecture and carries the internal
types; %d HLS pragmas appear in the file, with <code>PIPELINE</code> on the rotation-application
loops and <code>ARRAY_PARTITION</code> on the working matrix.</p>

<h3>C. Singular Value Decomposition &mdash; <code>svd.hpp</code> (%d lines)</h3>

<p class="noind">At %d lines this is the largest file in the solver family and the second
largest in the corpus. It implements two-sided Jacobi SVD: repeated application of rotation
pairs that annihilate off-diagonal elements, iterated in sweeps until the off-diagonal norm
falls below a tolerance.</p>

%s

<p>The structure differs from Cholesky and QR in one respect that matters for HLS. The number
of sweeps is <em>not known at compile time</em>; it depends on the data. This is the canonical
irregular case, and the file handles it the only way available:</p>

<pre>#pragma HLS loop_tripcount max = ...</pre>

<p>The directive does not constrain the hardware. It supplies the reporting tool with an
expected bound so that latency estimates are meaningful. The hardware itself must terminate on
a data-dependent condition, which means the block has variable latency and its consumer must be
prepared for it. This is precisely the property that makes irregular algorithms expensive in
HLS: the pipeline can still be filled, but the schedule cannot be static.</p>

<p>Two architectures are provided. <code>svdBasic</code> processes one index pair at a time.
<code>svdPairs</code> exploits the fact that rotations acting on disjoint index pairs commute,
and processes several concurrently; this is the classical parallel-ordering optimisation, and it
is exposed to the IP consumer through the architecture switch in the traits structure.
<code>calc_angle</code> computes the rotation angles and is specialised for the complex cases.
The file carries %d pragmas, the highest count in the solver family.</p>

<h3>D. Blocked Cholesky &mdash; <code>potrf.hpp</code> (%d lines)</h3>

<p class="noind">This file sits at what the Vitis Libraries call level 2: a composition layer
above the level-1 kernels. Its entry point deliberately mirrors the LAPACK name and signature:</p>

<pre>template &lt;typename T, int NMAX, int NCU&gt;
void potrf(int m, T* A, int lda, int&amp; info);</pre>

<p>Three observations. The matrix dimension <code>m</code> is a <em>runtime</em> argument while
<code>NMAX</code> is a compile-time bound&mdash;the hardware is built for the maximum and the
runtime value controls how much of it is exercised. <code>NCU</code>, the number of computation
units, is the folding parameter: rows are distributed across <code>NCU</code> engines,
with the working array declared as
<code>dataA[NCU][(N+NCU-1)/NCU][N]</code> so that the unit index is the outermost dimension and
each unit owns a private bank. And <code>info</code> is an output reference carrying the LAPACK
failure convention, again making the failure path explicit.</p>

<p>The internal decomposition is into <code>chol_col</code>, <code>chol_jj</code>,
<code>chol_col_wrapper</code> and <code>cholesky_core</code>. The separation between a
<em>wrapper</em> that distributes work across units and a <em>core</em> that performs the
factorisation is the level-1/level-2 boundary in miniature: the core is the reusable kernel, the
wrapper is the integration decision. %d pragmas appear in only %d lines, the highest density in
the solver family, because at this level almost every array must be explicitly banked across
the <code>NCU</code> dimension.</p>

%s
""" % (ch["lines"], fig(2, True), fig(3), fig(4, True),
       len(ch["funcs"]), ch["templates"],
       qr["lines"], fig(5), qr["templates"], qr["lines"], sum(qr["pragmas"].values()),
       sv["lines"], sv["lines"], fig(6), sum(sv["pragmas"].values()),
       po["lines"], sum(po["pragmas"].values()), po["lines"],
       tbl(4, "Solver family: structure of the four files.",
           ["File", "Lines", "Fn", "Tmpl", "Prag", "Architectures provided"],
           [["<code>cholesky.hpp</code>", ch["lines"], len(ch["funcs"]), ch["templates"],
             sum(ch["pragmas"].values()), "Basic / Alt / Alt2"],
            ["<code>qrf.hpp</code>", qr["lines"], len(qr["funcs"]), qr["templates"],
             sum(qr["pragmas"].values()), "basic + magnitude/extra-pass variants"],
            ["<code>svd.hpp</code>", sv["lines"], len(sv["funcs"]), sv["templates"],
             sum(sv["pragmas"].values()), "svdBasic / svdPairs"],
            ["<code>potrf.hpp</code>", po["lines"], len(po["funcs"]), po["templates"],
             sum(po["pragmas"].values()), "NCU-parallel blocked"]], wide=True))

open("/home/user/survey/part2.html","w").write(S3)
print("part2 written:", len(S3), "chars")
