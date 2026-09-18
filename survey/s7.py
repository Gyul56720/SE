# -*- coding: utf-8 -*-
import json, html
inv = json.load(open("/home/user/survey/inventory.json"))
E = html.escape

def tbl(cap, head, rows, wide=True, num=None):
    c = ' class="tbl wide"' if wide else ' class="tbl"'
    cp = f'<caption>{cap}</caption>' if cap else ''
    h = "".join(f"<th>{x}</th>" for x in head)
    r = "".join("<tr>"+"".join(f"<td>{x}</td>" for x in row)+"</tr>" for row in rows)
    return f'<div{c}><table>{cp}<tr>{h}</tr>{r}</table></div>'

# ---------- Appendix A ----------
A = ['<h2>Appendix A<br/>Complete File Inventory</h2>',
     '<p class="noind">Every file in the corpus, with the metadata extracted mechanically as '
     'described in Section II-C. Lines and bytes are exact; function, template and class counts '
     'are pattern-matched and carry the caveat stated in Section VIII.</p>']
rows = []
for f in inv["files"]:
    rows.append([f'<code>{E(f["rel"])}</code>', f'{f["lines"]:,}', f'{f["bytes"]:,}',
                 len(f["funcs"]), f["templates"], len(f["classes"]),
                 len(f["defines"]), len(f["labels"]),
                 sum(f["pragmas"].values()), f["license"]])
rows.append(["<b>Total</b>", f'<b>{inv["total_lines"]:,}</b>',
             f'<b>{sum(f["bytes"] for f in inv["files"]):,}</b>',
             f'<b>{sum(len(f["funcs"]) for f in inv["files"])}</b>',
             f'<b>{sum(f["templates"] for f in inv["files"])}</b>',
             f'<b>{sum(len(f["classes"]) for f in inv["files"])}</b>',
             f'<b>{sum(len(f["defines"]) for f in inv["files"])}</b>',
             f'<b>{sum(len(f["labels"]) for f in inv["files"])}</b>',
             f'<b>{sum(sum(f["pragmas"].values()) for f in inv["files"])}</b>', "&mdash;"])
A.append(tbl("Table&nbsp;A1.&nbsp; Complete file inventory.",
             ["File", "Lines", "Bytes", "Fn", "Tmpl", "Cls", "Def", "Lbl", "Prag", "Licence"], rows))

A.append('<p>Table A2 lists every class and struct definition found, and Table A3 every named '
         'loop label. Loop labels are included because in this corpus they are not decoration: '
         'they are the handles by which a directive or a synthesis report refers to a loop.</p>')
cr = []
for f in inv["files"]:
    if f["classes"]:
        cr.append([f'<code>{E(f["name"])}</code>',
                   ", ".join(f'<code>{E(c["name"])}</code>' for c in f["classes"])])
A.append(tbl("Table&nbsp;A2.&nbsp; All class and struct definitions.",
             ["File", "Definitions"], cr))
lr = []
for f in inv["files"]:
    if f["labels"]:
        lr.append([f'<code>{E(f["name"])}</code>',
                   ", ".join(f'<code>{E(x)}</code>' for x in f["labels"])])
A.append(tbl("Table&nbsp;A3.&nbsp; All named loop labels.", ["File", "Labels"], lr))

mr = []
for f in inv["files"]:
    if f["defines"]:
        mr.append([f'<code>{E(f["name"])}</code>',
                   ", ".join(f'<code>{E(x)}</code>' for x in f["defines"])])
A.append(tbl("Table&nbsp;A4.&nbsp; All preprocessor macro definitions.", ["File", "Macros"], mr))

ir = []
for f in inv["files"]:
    if f["includes"]:
        ir.append([f'<code>{E(f["name"])}</code>',
                   ", ".join(f'<code>{E(x)}</code>' for x in f["includes"])])
A.append(tbl("Table&nbsp;A5.&nbsp; All include directives (the dependency closure of Section II-A).",
             ["File", "Includes"], ir))

# ---------- Appendix B ----------
B = ['<h2>Appendix B<br/>Complete Pragma Index</h2>',
     '<p class="noind">All %d <code>#pragma HLS</code> directives in the corpus, by file and '
     'line. This table is the evidence for every pragma count quoted in the body of the paper.</p>'
     % sum(sum(f["pragmas"].values()) for f in inv["files"])]
for f in inv["files"]:
    if not f["pragma_lines"]: continue
    rows = [[p["line"], f'<code>{E(p["text"])}</code>'] for p in f["pragma_lines"]]
    B.append(f'<p class="noind"><b><code>{E(f["rel"])}</code></b> &mdash; '
             f'{sum(f["pragmas"].values())} directives</p>')
    B.append(tbl("", ["Line", "Directive"], rows, wide=False))

# ---------- Appendix C ----------
C = ['<h2>Appendix C<br/>Complete Function Index</h2>',
     '<p class="noind">All %d function definitions located by the extraction pass, by file and '
     'line, with return type. Template parameter lists are omitted for space; they appear in the '
     'source at the line given.</p>'
     % sum(len(f["funcs"]) for f in inv["files"])]
for f in inv["files"]:
    if not f["funcs"]: continue
    rows = [[x["line"], f'<code>{E(x["ret"])}</code>', f'<code>{E(x["name"])}</code>']
            for x in sorted(f["funcs"], key=lambda k: k["line"])]
    C.append(f'<p class="noind"><b><code>{E(f["rel"])}</code></b> &mdash; {len(f["funcs"])} definitions</p>')
    C.append(tbl("", ["Line", "Returns", "Name"], rows, wide=False))

REF = """
<h2>References</h2>
<ol class="ref">
<li>AMD/Xilinx, <i>Vitis Libraries &mdash; Solver Library</i>, source files
<code>solver/L1/include/hw/cholesky.hpp</code>, <code>qrf.hpp</code>, <code>svd.hpp</code> and
<code>solver/L2/include/hw/MatrixDecomposition/potrf.hpp</code>, Apache License 2.0. Retrieved
September 18, 2026. <span class="kv">[full text read]</span></li>
<li>AMD/Xilinx, <i>Vitis Libraries &mdash; Security Library</i>, source files
<code>security/L1/include/xf_security/aes.hpp</code>, <code>sha224_256.hpp</code>,
<code>types.hpp</code>, <code>utils.hpp</code>, Apache License 2.0. Retrieved September 18,
2026. <span class="kv">[full text read]</span></li>
<li>Xilinx, <i>FINN-hlslib</i>, sixteen source files as listed in Appendix A, BSD 3-Clause
licence. Retrieved September 18, 2026. <span class="kv">[full text read]</span></li>
<li>Accellera Systems Initiative, <i>UVM Core</i>, source files <code>uvm_pkg.sv</code>,
<code>uvm_component.svh</code>, <code>uvm_sequence.svh</code>, <code>dpi/uvm_dpi.cc</code>.
Consulted for the comparison in Section VI-H. <span class="kv">[partial read]</span></li>
<li>lowRISC, <i>OpenTitan</i>, AES intellectual-property block, 37 register-transfer-level
source files. Consulted to establish the generated-versus-handwritten ratio cited in Section
VII. <span class="kv">[headers of all 37 files read]</span></li>
<li>OpenHW Group, <i>CVA6</i>, file list <code>core/Flist.cva6</code>. Consulted for the
language distribution cited in Section VII. <span class="kv">[file list read]</span></li>
<li>IEEE Standard for SystemVerilog, IEEE Std 1800. Referenced for the Direct Programming
Interface semantics discussed in Section VI-H. <span class="kv">[not read; cited for the
standard's existence only]</span></li>
<li>National Institute of Standards and Technology, <i>Advanced Encryption Standard</i>,
FIPS 197, and <i>Secure Hash Standard</i>, FIPS 180-4. Referenced as the specifications
implemented by the cryptographic family. <span class="kv">[not read in this study]</span></li>
</ol>

<p class="noind" style="font-size:8.2pt; margin-top:6pt"><i>Note on citation practice.</i> Each
reference carries a bracketed statement of how far it was actually read. References 7 and 8 were
not consulted during this work and are cited only to name the standards that the surveyed code
implements; no claim in this paper depends on their content.</p>
"""

open("/home/user/survey/part5.html","w").write("\n".join(A+B+C) + REF)
print("part5 written:", len("\n".join(A+B+C)+REF), "chars")
