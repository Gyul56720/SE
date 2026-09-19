# -*- coding: utf-8 -*-
"""Volume III, Part Y10 -- The register map and the software interface."""
import sys, math, json
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


# A worked example register map, defined once and rendered several ways.  The
# point of defining it as data is the point of the chapter.
REGS = [
    {"name": "ID", "off": 0x00, "access": "RO", "reset": 0x1A2B0100,
     "fields": [("VENDOR", 31, 16, "RO", "Vendor identifier, constant"),
                ("BLOCK", 15, 8, "RO", "Block identifier"),
                ("VERSION", 7, 0, "RO", "Major.minor, BCD")],
     "why": "Proves supply, clock, reset, bus and decode in one read (Part Y7)."},
    {"name": "SCRATCH", "off": 0x04, "access": "RW", "reset": 0x00000000,
     "fields": [("DATA", 31, 0, "RW", "Any value; no hardware effect")],
     "why": "Proves the write path independently of any functional side effect."},
    {"name": "CTRL", "off": 0x08, "access": "RW", "reset": 0x00000000,
     "fields": [("ENABLE", 0, 0, "RW", "1 starts the datapath"),
                ("SOFT_RESET", 1, 1, "W1S", "Self-clearing; resets the datapath only"),
                ("LOOPBACK", 2, 2, "RW", "Internal loopback for bring-up"),
                ("LANES", 7, 4, "RW", "Active lane count minus one")],
     "why": "Everything that changes behaviour, in one register the driver can "
            "read-modify-write atomically."},
    {"name": "STATUS", "off": 0x0C, "access": "RO", "reset": 0x00000000,
     "fields": [("READY", 0, 0, "RO", "Datapath has completed initialisation"),
                ("ALIGNED", 1, 1, "RO", "Lane alignment achieved"),
                ("STATE", 7, 4, "RO", "Current link state, for debug")],
     "why": "Live state. Never latched -- a latched status needs a clear, and a "
            "clear is a race."},
    {"name": "IRQ_STATUS", "off": 0x10, "access": "W1C", "reset": 0x00000000,
     "fields": [("ERR_CRC", 0, 0, "W1C", "A CRC error occurred"),
                ("ERR_ECC", 1, 1, "W1C", "An uncorrectable ECC error occurred"),
                ("OVERFLOW", 2, 2, "W1C", "Receive buffer overflowed")],
     "why": "Write-1-to-clear so two drivers cannot clear each other's bits."},
    {"name": "IRQ_ENABLE", "off": 0x14, "access": "RW", "reset": 0x00000000,
     "fields": [("MASK", 2, 0, "RW", "One bit per IRQ_STATUS bit")],
     "why": "Separate from status so masking never loses an event."},
    {"name": "ERR_COUNT", "off": 0x18, "access": "RC", "reset": 0x00000000,
     "fields": [("COUNT", 31, 0, "RC", "Errors since last read; saturates")],
     "why": "Read-to-clear and saturating: a counter that wraps silently is worse "
            "than one that sticks at maximum."},
]


def ch_regmap():
    s = ['<h1 id="y10">Y10. The Register Map and the Software Interface</h1>']
    s.append("""<p>The register map is the part of a block that software sees, the part a
    customer integrates against, and the part that is hardest to change after release.
    It is also, in most projects, the artefact with the least design attention per hour of
    downstream consequence. This part works through one map in full and states the rules
    that each entry follows.</p>""")

    s.append("<h2>Y10.1 A worked map</h2>")
    rows = []
    for r in REGS:
        rows.append([f"<code>0x{r['off']:02X}</code>", f"<b>{r['name']}</b>",
                     r["access"], f"0x{r['reset']:08X}", r["why"]])
    s.append(sweep("A minimal but complete register map, and why each register exists",
        ["Offset", "Register", "Access", "Reset", "Why it is here"], rows,
        "Seven registers. <b>Three of them (ID, SCRATCH, LOOPBACK) exist only for "
        "bring-up and debug</b>, and they are the ones most often omitted by a designer "
        "who is thinking about function rather than about the week the customer spends "
        "getting first traffic."))
    for r in REGS[:4]:
        frows = [[f"{hi}:{lo}" if hi != lo else str(hi), f"<code>{nm}</code>", ac, ds]
                 for nm, hi, lo, ac, ds in r["fields"]]
        s.append(tab(f"<code>{r['name']}</code> at offset 0x{r['off']:02X}, reset "
                     f"0x{r['reset']:08X}",
                     ["Bits", "Field", "Access", "Description"], frows))

    s.append("<h2>Y10.2 Access types, and the race each one prevents</h2>")
    s.append(tab("Register access types",
        ["Type", "Behaviour", "The problem it solves", "Where it goes wrong"],
        [["RO", "Read only", "&mdash;", "Writing is silently ignored &mdash; "
          "specify that, or software will assume it faulted"],
         ["RW", "Read and write", "&mdash;",
          "<b>Read-modify-write on a register hardware also writes loses the "
          "hardware's update</b>"],
         ["<b>W1C</b>", "Write 1 to clear a bit",
          "<b>Two drivers clearing different bits do not clobber each other</b>",
          "A driver that writes 0xFFFFFFFF clears events it never handled"],
         ["W1S / W1T", "Write 1 to set / toggle", "Same, for setting",
          "&mdash;"],
         ["RC", "Read clears", "A counter read without a separate write",
          "<b>A debugger that reads registers disturbs state</b> &mdash; mark such "
          "registers so tools skip them"],
         ["WO", "Write only", "Command registers", "Unreadable state cannot be "
          "restored after suspend; prefer RW with a self-clearing bit"],
         ["RW1", "Writable once until reset", "Lockable configuration",
          "Software must know the lock exists"]]))
    s.append("""<div class="warn"><b>The read-modify-write race is the defect this table
    exists to prevent, and it is worth stating concretely.</b> Suppose STATUS bits lived
    in CTRL. A driver reads CTRL, changes ENABLE, and writes it back. Between the read and
    the write, hardware set an error bit. The write puts back the old value of that bit
    and the error is lost &mdash; silently, rarely, and only under load. <b>The rule is
    structural: never mix software-written and hardware-written bits in one register</b>,
    and where an event must be cleared by software, use W1C so that the write names
    exactly the bits it intends. This costs one extra register and removes a class of bug
    that is close to undebuggable in the field.</div>""")

    s.append("<h2>Y10.3 One source, many outputs</h2>")
    s.append("""<p>A register map appears in at least six places. Maintaining them by hand
    guarantees they diverge, and the divergence is discovered by a driver author at the
    worst moment.</p>""")
    s.append(tab("What is generated from the register description, and who consumes it",
        ["Artefact", "Consumer", "What divergence costs"],
        [["RTL register file", "The design", "&mdash;"],
         ["C header with offsets and field masks", "The driver author",
          "A driver that writes the wrong bit"],
         ["<b>IP-XACT or SystemRDL</b>", "<b>The customer's integration tooling</b>",
          "<b>Manual integration &mdash; increasingly a purchase blocker</b>"],
         ["Documentation tables", "Everyone", "A datasheet that lies"],
         ["UVM register model", "Verification",
          "Tests that pass against a stale model"],
         ["Debugger description", "Bring-up", "Wrong values read during the week "
          "they matter most"]]))
    s.append(ex("The cost of maintaining six copies by hand",
        "A 60-register map, six artefacts, and a change rate of roughly 8 register "
        "changes per month during development.",
        "Count the edits and the probability that at least one is missed, assuming a "
        "2&nbsp;% chance of missing any individual edit.",
        [("Artefacts", num(6)),
         ("Edits per month", num(8 * 6)),
         ("Edits over a 9-month project", num(8 * 6 * 9)),
         ("P(no edit missed) at 2&nbsp;% per edit",
          num(0.98 ** (8 * 6 * 9), 3)),
         ("Expected number missed", num(8 * 6 * 9 * 0.02, 3)),
         ("Effort to build a generator", "1&ndash;2 weeks"),
         ("Effort saved", num(8 * 6 * 9 * 0.05 / 40, 3) + " weeks, plus the bugs")],
        "<b>By evaluating the generator against the edit effort alone.</b> The edits are "
        "cheap; the missed ones are not, and the expected count here is about nine. "
        "Each is a divergence between what software believes and what hardware does, "
        "found at integration. <b>The generator's value is in the defects it removes, "
        "not the keystrokes</b>, and stating it that way is also how to justify the two "
        "weeks to a manager who sees only the keystrokes."))
    s.append(prob("What should a register do when software writes a reserved bit?",
        "Define it, and define it in the direction that leaves you room. The two "
        "defensible choices are <b>&lsquo;reserved, write zero, read undefined&rsquo;</b> "
        "and <b>&lsquo;reserved, preserve on write, read as written&rsquo;</b>. The "
        "second is much better for forward compatibility: software does a "
        "read-modify-write and unknowingly preserves bits a future version defines, so an "
        "old driver keeps working with new hardware. The first is simpler and breaks that "
        "property. What is <i>not</i> acceptable is leaving it unspecified, because "
        "software will discover the behaviour empirically and depend on it, and you will "
        "then be unable to change it. <b>The same principle applies to every "
        "&lsquo;don't care&rsquo; in a specification</b>: an unspecified behaviour is not "
        "free, it is a behaviour your customers will come to rely on before you have "
        "decided what it should be."))
    s.append(prob("Your block is in a power domain that can be switched off. What does "
                  "that do to the register map?",
        "It adds a requirement that is easy to miss and expensive to retrofit: "
        "<b>every register software may need after resume must be restorable</b>. That "
        "means no write-only registers whose value cannot be read back, no state that "
        "exists only in hardware counters software cannot reconstruct, and a documented "
        "save/restore list telling the driver exactly which offsets to store. It also "
        "raises a design question about which registers should be in an always-on "
        "domain &mdash; typically the ones controlling wake-up and the power sequence "
        "itself, since a register that controls power-up cannot live in the domain being "
        "powered up. <b>Getting this wrong produces a block that works until the first "
        "suspend/resume cycle</b>, which in a mobile or automotive product is within "
        "minutes of the customer first running real software on it."))
    return "\n".join(s)
