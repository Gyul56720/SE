# -*- coding: utf-8 -*-
import json, html
inv  = json.load(open("/home/user/survey/inventory.json"))
deep = json.load(open("/home/user/survey/deep.json"))
E = html.escape

def tbl(cap, head, rows, wide=True):
    c=' class="tbl wide"' if wide else ' class="tbl"'
    cp=f'<caption>{cap}</caption>' if cap else ''
    h="".join(f"<th>{x}</th>" for x in head)
    r="".join("<tr>"+"".join(f"<td>{x}</td>" for x in row)+"</tr>" for row in rows)
    return f'<div{c}><table>{cp}<tr>{h}</tr>{r}</table></div>'
def C(s): return f'<code>{E(str(s))}</code>'

# ================= Appendix A : corpus + vendor inventory =================
A=['<h2>Appendix A<br/>Complete File Inventory</h2>',
   '<p class="noind">Section A-I lists the analysed corpus; Section A-II lists the 51 vendor '
   'headers whose retrieval is described in Section II-A and which the corpus requires in order '
   'to compile. Together they are every source file this study touched.</p>',
   '<h3>A-I. The Analysed Corpus</h3>']
rows=[]
for f in inv["files"]:
    rows.append([C(f["rel"]), f'{f["lines"]:,}', f'{f["bytes"]:,}', len(f["funcs"]),
                 f["templates"], len(f["classes"]), len(f["defines"]), len(f["labels"]),
                 sum(f["pragmas"].values()), f["license"]])
rows.append(["<b>Total</b>", f'<b>{inv["total_lines"]:,}</b>',
             f'<b>{sum(f["bytes"] for f in inv["files"]):,}</b>',
             f'<b>{sum(len(f["funcs"]) for f in inv["files"])}</b>',
             f'<b>{sum(f["templates"] for f in inv["files"])}</b>',
             f'<b>{sum(len(f["classes"]) for f in inv["files"])}</b>',
             f'<b>{sum(len(f["defines"]) for f in inv["files"])}</b>',
             f'<b>{sum(len(f["labels"]) for f in inv["files"])}</b>',
             f'<b>{sum(sum(f["pragmas"].values()) for f in inv["files"])}</b>',"&mdash;"])
A.append(tbl("Table&nbsp;A1.&nbsp; The analysed corpus.",
             ["File","Lines","Bytes","Fn","Tmpl","Cls","Def","Lbl","Prag","Licence"],rows))

A.append('<h3>A-II. Vendor Header Closure</h3>')
A.append('<p class="noind">These headers are not part of the surveyed IP; they are the '
         'arbitrary-precision, stream and mathematics infrastructure the IP is written against. '
         'They were located as described in Section II-A and are listed here because without '
         'them nothing in Appendix A-I compiles, and because their own size&mdash;%s lines '
         'against the corpus\'s %s&mdash;is itself a finding about what HLS C++ rests on.</p>'
         % (f'{sum(f["lines"] for f in deep["vendor"]):,}', f'{inv["total_lines"]:,}'))
vr=[]
for f in deep["vendor"]:
    vr.append([C(f["rel"]), f'{f["lines"]:,}', f'{f["bytes"]:,}',
               len(f["classes"]), len(f["funcs"]), len(f["defines"])])
vr.append(["<b>Total (51 files)</b>", f'<b>{sum(f["lines"] for f in deep["vendor"]):,}</b>',
           f'<b>{sum(f["bytes"] for f in deep["vendor"]):,}</b>',
           f'<b>{sum(len(f["classes"]) for f in deep["vendor"])}</b>',
           f'<b>{sum(len(f["funcs"]) for f in deep["vendor"])}</b>',
           f'<b>{sum(len(f["defines"]) for f in deep["vendor"])}</b>'])
A.append(tbl("Table&nbsp;A2.&nbsp; Vendor header closure (retrieved, not surveyed).",
             ["Header","Lines","Bytes","Cls","Fn","Def"],vr))

for cap,key,fn in [("Table&nbsp;A3.&nbsp; All named loop labels.","labels",lambda f:f["labels"]),
                   ("Table&nbsp;A4.&nbsp; All preprocessor macro definitions.","defines",lambda f:f["defines"]),
                   ("Table&nbsp;A5.&nbsp; All include directives.","includes",lambda f:f["includes"])]:
    rr=[[C(f["name"]), ", ".join(C(x) for x in fn(f))] for f in inv["files"] if fn(f)]
    A.append(tbl(cap,["File","Entries"],rr))

# ================= Appendix B : pragma index =================
B=['<h2>Appendix B<br/>Complete Pragma Index</h2>',
   '<p class="noind">All %d <code>#pragma HLS</code> directives, by file and line, in full text.</p>'
   % sum(sum(f["pragmas"].values()) for f in inv["files"])]
for f in inv["files"]:
    if not f["pragma_lines"]: continue
    B.append(f'<p class="noind"><b>{C(f["rel"])}</b> &mdash; {sum(f["pragmas"].values())} directives</p>')
    B.append(tbl("",["Line","Directive"],[[p["line"],C(p["text"])] for p in f["pragma_lines"]],wide=False))

# ================= Appendix C : full class reference =================
ncls=sum(len(f["classes"]) for f in deep["files"])
Cx=['<h2>Appendix C<br/>Complete Class and Struct Reference</h2>',
    '<p class="noind">Every one of the %d class and struct definitions in the corpus, with its '
    'template parameter list, base clause, member typedefs, static constants and member '
    'functions. This is the full interface of the surveyed IP.</p>' % ncls]
for f in deep["files"]:
    if not f["classes"]: continue
    Cx.append(f'<p class="noind"><b>{C(f["rel"])}</b> &mdash; {len(f["classes"])} definitions</p>')
    for c in f["classes"]:
        head=f'{c["kind"]} {c["name"]}{c["spec"]}'
        Cx.append(f'<p class="noind" style="margin-top:4pt"><b>{E(head)}</b> '
                  f'<span class="kv">(line {c["line"]}, {c["body_lines"]} lines)</span></p>')
        rows=[]
        if c["tmpl"]:  rows.append(["template", C(c["tmpl"])])
        if c["bases"]: rows.append(["inherits", C(c["bases"])])
        for t in c["typedefs"]: rows.append(["typedef", C(t)])
        for s in c["statics"]:  rows.append(["static", C(s)])
        for r,n,p in c["methods"]:
            rows.append(["method", C(f'{r} {n}({p})')])
        if rows: Cx.append(tbl("",["Kind","Declaration"],rows,wide=False))

# ================= Appendix D : full function reference =================
nfn=sum(len(f["funcs"]) for f in deep["files"])
D=['<h2>Appendix D<br/>Complete Function Reference</h2>',
   '<p class="noind">Every one of the %d free-function definitions in the corpus, with its '
   'template parameter list and full parameter list.</p>' % nfn]
for f in deep["files"]:
    if not f["funcs"]: continue
    D.append(f'<p class="noind"><b>{C(f["rel"])}</b> &mdash; {len(f["funcs"])} definitions</p>')
    rows=[]
    for x in sorted(f["funcs"], key=lambda k:k["line"]):
        sig=f'{x["ret"]} {x["name"]}({x["params"]})'
        rows.append([x["line"], (C(x["tmpl"]) + "<br/>" if x["tmpl"] else "") + C(sig)])
    D.append(tbl("",["Line","Signature"],rows,wide=False))

# ================= Appendix E : vendor class index =================
vc=sum(len(f["classes"]) for f in deep["vendor"])
Ex=['<h2>Appendix E<br/>Vendor Header Class Index</h2>',
    '<p class="noind">The %d class and struct definitions in the vendor closure, by header. '
    'These are listed by name only: they are infrastructure the corpus consumes, not the subject '
    'of this survey, but their extent shows how much machinery the arbitrary-precision types '
    'require.</p>' % vc]
vr=[]
for f in deep["vendor"]:
    if not f["classes"]: continue
    vr.append([C(f["rel"]), len(f["classes"]),
               ", ".join(C(c["name"]) for c in f["classes"][:40])
               + (" &hellip;" if len(f["classes"])>40 else "")])
Ex.append(tbl("Table&nbsp;E1.&nbsp; Classes defined in the vendor closure.",
              ["Header","N","Definitions"],vr))

REF = open("/home/user/survey/_refs.html").read() if False else """
<h2>References</h2>
<ol class="ref">
<li>AMD/Xilinx, <i>Vitis Libraries &mdash; Solver</i>: <code>cholesky.hpp</code>,
<code>qrf.hpp</code>, <code>svd.hpp</code>, <code>potrf.hpp</code>, <code>x_matrix_utils.hpp</code>,
<code>math_helper.hpp</code>. Apache-2.0. <span class="kv">[full text read]</span></li>
<li>AMD/Xilinx, <i>Vitis Libraries &mdash; Security</i>: <code>aes.hpp</code>,
<code>sha224_256.hpp</code>, <code>types.hpp</code>, <code>utils.hpp</code>. Apache-2.0.
<span class="kv">[full text read]</span></li>
<li>Xilinx, <i>FINN-hlslib</i>, sixteen files (Appendix A-I). BSD-3-Clause.
<span class="kv">[full text read]</span></li>
<li>Xilinx, <i>HLS_arbitrary_Precision_Types</i>: <code>ap_int.h</code>, <code>ap_fixed.h</code>
and their bases, references and specialisations. <span class="kv">[used to compile; read in part]</span></li>
<li>Xilinx, <i>hls-lib-stream</i>: <code>hls_stream.h</code>.
<span class="kv">[used to compile; read in part]</span></li>
<li>Xilinx, <i>hls-utilities</i>: <code>hls_math.h</code>, <code>hls_x_complex.h</code>,
<code>hls_half.h</code>, <code>hls_fpo.h</code> and the <code>etc/hls_*_apfixed.h</code> kernels.
<span class="kv">[used to compile; read in part]</span></li>
<li>Xilinx, <i>merlin-compiler</i>: <code>ap_axi_sdata.h</code>, <code>x_hls_utils.h</code>,
<code>x_hls_traits.h</code>, <code>x_hls_defines.h</code>, <code>std_complex_utils.h</code>.
<span class="kv">[used to compile; read in part]</span></li>
<li>Third-party mirror <code>xliu0709/WinoCNN</code>: <code>gmp.h</code>, <code>mpfr.h</code>.
<span class="kv">[weaker provenance than 4&ndash;7; noted in Section II-A]</span></li>
<li>Accellera Systems Initiative, <i>UVM Core</i>. <span class="kv">[partial read]</span></li>
<li>lowRISC, <i>OpenTitan</i> AES block, 37 RTL files. <span class="kv">[headers of all 37 read]</span></li>
<li>OpenHW Group, <i>CVA6</i>, <code>core/Flist.cva6</code>. <span class="kv">[file list read]</span></li>
<li>IEEE Std 1800, <i>SystemVerilog</i>. <span class="kv">[not read; named only]</span></li>
<li>NIST, FIPS 197 and FIPS 180-4. <span class="kv">[not read; named only]</span></li>
</ol>
<p class="noind" style="font-size:8.2pt; margin-top:6pt"><i>Note on citation practice.</i> Each
reference states how far it was read. References 12 and 13 were not consulted; no claim in this
paper depends on their content. References 4&ndash;8 were compiled against rather than read in
full, and reference 8 has weaker provenance than the Xilinx-owned repositories above it.</p>
"""
open("/home/user/survey/part5.html","w").write("\n".join(A+B+Cx+D+Ex)+REF)
print("part5:", len("\n".join(A+B+Cx+D+Ex)+REF), "chars   classes", ncls, " funcs", nfn, " vendor cls", vc)
