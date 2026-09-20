# -*- coding: utf-8 -*-
"""Volume III, Part Y14 -- The open-source flow a one-person house can actually run."""
import sys, os, shutil, subprocess, math
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num


def _ver(cmd, args):
    p = shutil.which(cmd)
    if not p:
        return None, None
    try:
        r = subprocess.run([cmd] + args, capture_output=True, text=True, timeout=30)
        out = (r.stdout or r.stderr).strip().splitlines()
        return p, (out[0][:60] if out else "")
    except Exception:
        return p, ""


def ch_toolchain():
    s = ['<h1 id="y14">Y14. The Flow a One-Person House Can Actually Run</h1>']
    s.append("""<p>Commercial EDA licences cost more per year than a one-person house
    earns. That fact shapes what such a house can sell, and the honest answer is that a
    great deal is possible with free tools and one thing is not. This part sets out which
    is which, and measures what is actually installed in the environment this book was
    built in.</p>""")

    s.append("<h2>Y14.1 What is installed here, measured</h2>")
    rows = []
    for cmd, args, role in (("iverilog", ["-V"], "Event-driven Verilog/SystemVerilog "
                             "simulation"),
                            ("verilator", ["--version"], "Cycle-accurate compiled "
                             "simulation; fast regressions"),
                            ("yosys", ["-V"], "RTL synthesis to a gate netlist"),
                            ("gtkwave", ["--version"], "Waveform viewing"),
                            ("python3", ["--version"], "Modelling, scripting, this book"),
                            ("gcc", ["--version"], "Reference models in C/C++")):
        path, ver = _ver(cmd, args)
        rows.append([f"<code>{cmd}</code>", role,
                     "yes" if path else "<b>not installed</b>",
                     E(ver) if ver else "&mdash;"])
    s.append(sweep("Tools present in the container this book was rendered in, checked at "
                   "build time",
        ["Tool", "Role", "Present", "Version reported"], rows,
        "Probed by running each tool. <b>The verification agent of Part&nbsp;Y4 uses "
        "the first of these and nothing else</b>, which is the point: a complete "
        "model-versus-RTL regression loop needs one free simulator."))

    s.append("<h2>Y14.2 What the free flow can and cannot do</h2>")
    s.append(tab("Capability, honestly assessed",
        ["Activity", "Free flow", "Note"],
        [["Modelling and algorithm work", "<b>Complete</b>",
          "Python, NumPy, C++ &mdash; nothing is missing"],
         ["RTL simulation", "<b>Complete for most purposes</b>",
          "Verilator is fast; Icarus handles constructs Verilator does not"],
         ["<b>UVM</b>", "<b>Partial</b>",
          "UVM needs constrained randomisation and full class support; free simulators "
          "have improved but are not equivalent. cocotb is a viable different answer"],
         ["Formal property checking", "Usable",
          "SymbiYosys and its solvers; capacity below commercial tools"],
         ["Lint and CDC", "Partial",
          "Verilator lint is good; dedicated CDC sign-off tools have no free equivalent"],
         ["Synthesis to a gate netlist", "<b>Yes</b>",
          "Yosys, with open cell libraries"],
         ["Place and route", "<b>Yes for open PDKs</b>",
          "OpenROAD and the open PDK flows"],
         ["<b>Sign-off STA in a commercial process</b>", "<b>No</b>",
          "<b>Needs the foundry's timing libraries, which come with an NDA and a "
          "commercial tool</b>"],
         ["Tape-out to a commercial foundry", "<b>No</b>",
          "This is the line a free flow does not cross"]]))
    s.append("""<div class="ms"><b>The line falls exactly where a soft-IP business
    wants it.</b> Everything on the seller's side of a soft-IP transaction &mdash;
    modelling, RTL, verification, and enough synthesis to quote area and frequency
    credibly &mdash; is reachable with free tools. Everything on the buyer's side
    &mdash; sign-off in their process, with their libraries, in their flow &mdash; is
    theirs to run and they already have the licences. <b>A design house selling RTL
    therefore does not need a tape-out flow</b>, and recognising that is the difference
    between a viable plan and one that requires six figures of tooling before the first
    sale. The caveat to state to customers is equally clear: your frequency and area
    numbers come from an open flow and an open library, and they will re-run them; give
    them the scripts so they can.</div>""")
    s.append(ex("What credible area and frequency numbers cost to produce",
        "You want to quote &lsquo;150&nbsp;kGE at 500&nbsp;MHz&rsquo; for a block, "
        "with evidence, using only free tools.",
        "Enumerate what is needed and what each step actually establishes.",
        [("Synthesis with Yosys to an open library", "area in gate equivalents"),
         ("Static timing with OpenSTA on that netlist", "a frequency, in that library"),
         ("What this does <i>not</i> establish",
          "<b>performance in the customer's process</b>"),
         ("What makes it credible anyway",
          "the <i>ratio</i> transfers; publish the library and the scripts"),
         ("Additional cost", num(0, 3, "USD")),
         ("What a customer will still do", "re-run it in their flow"),
         ("What they are really buying",
          "<b>the assurance that the number is not invented</b>")],
        "<b>By quoting a number from an open flow as though it were a sign-off "
        "number.</b> It is not, and a customer who discovers the elision stops trusting "
        "the rest of the datasheet. The correct presentation names the library, the "
        "tool and the version, states that it is a pre-layout estimate in an open "
        "process, and offers the scripts. <b>That presentation is more persuasive than "
        "an unattributed larger claim</b>, for the same reason the known-issue list of "
        "Part&nbsp;Y5 is: it is checkable."))

    s.append("<h2>Y14.3 A regression setup that survives one person</h2>")
    s.append(tab("What to automate first, in order of return",
        ["Automate", "Why it is first", "Effort"],
        [["<b>One command that runs everything</b>",
          "<b>If the regression is three commands, it will be run less often, and the "
          "one that is skipped is the one that would have caught it</b>", "Hours"],
         ["Deterministic seeds recorded with results",
          "A failure you cannot reproduce is a failure you cannot fix", "Hours"],
         ["<b>A self-check that the checkers bite</b>",
          "<b>Otherwise a green regression means nothing &mdash; the theme of this "
          "entire book</b>", "A day"],
         ["Results to a ledger, not to a terminal",
          "You will be asked what changed between last week and now", "A day"],
         ["Overnight running with the correct detachment",
          "Part&nbsp;Y4's <code>setsid</code>/<code>nohup</code>/<code>disown</code> "
          "pattern &mdash; the obvious way silently does nothing", "Hours"],
         ["Mutation testing of the suite", "Turns &lsquo;we have tests&rsquo; into a "
          "number you can quote", "Days &mdash; and it is what a customer remembers"]]))
    s.append("""<div class="warn"><b>The failure that ends solo projects is not a hard
    bug; it is losing the ability to reproduce.</b> Six months in, with several branches,
    a half-changed model and results in a terminal scrollback, the question &lsquo;did
    this ever pass?&rsquo; becomes unanswerable, and from that point every decision is a
    guess. The defence is cheap and must be built before it is needed: <b>every run
    records its commit, its seeds, its tool versions and its results to a file that is
    committed</b>. This book's own repository does exactly this, and the rule that
    produced it is worth repeating: a check that leaves no record is a check nobody can
    audit, including you.</div>""")
    s.append(prob("Which free simulator should a one-person house standardise on?",
        "Both, for different jobs, and the reasoning generalises. <b>Verilator</b> for "
        "the bulk regression: it compiles to C++ and runs one to two orders of magnitude "
        "faster than event-driven simulation, which is what makes an overnight run worth "
        "having; its restrictions (two-state by default, synthesisable subset, no timing "
        "constructs) are mostly acceptable for a testbench driven from C++ or cocotb. "
        "<b>Icarus</b> for the cases Verilator refuses: four-state X-propagation, "
        "gate-level simulation with delays, and legacy constructs. <b>The important "
        "discipline is to keep the RTL compiling under both</b>, because each catches "
        "things the other permits &mdash; Verilator's lint is stricter than most "
        "commercial tools, and Icarus's four-state semantics catch reset and "
        "initialisation bugs that a two-state run hides. Two simulators disagreeing about "
        "your design is information, and it is free."))
    return "\n".join(s)
