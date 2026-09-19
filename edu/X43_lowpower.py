# -*- coding: utf-8 -*-
"""Volume I, Part X43 -- Power intent: domains, retention, isolation, UPF."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def _f_pd():
    b = []
    b.append(f'<rect x="14" y="20" width="160" height="110" fill="#eef7f2" '
             f'stroke="#2a7f5f" stroke-width="1.2" stroke-dasharray="5,3"/>')
    b.append(txt(94, 36, "always-on domain", 8, "middle"))
    b.append(box(30, 46, 128, 26, "power controller", None, 8))
    b.append(box(30, 86, 128, 26, "retention control", None, 8))
    b.append(f'<rect x="206" y="20" width="176" height="110" fill="#fbf2f2" '
             f'stroke="#a33" stroke-width="1.2" stroke-dasharray="5,3"/>')
    b.append(txt(294, 36, "switchable domain", 8, "middle"))
    b.append(box(222, 46, 144, 26, "the block's logic", None, 8))
    b.append(box(222, 86, 144, 26, "retention flops", None, 8))
    b.append(f'<rect x="178" y="52" width="22" height="60" fill="#fff" '
             f'stroke="#000" stroke-width="1"/>')
    b.append(txt(189, 86, "ISO", 7, "middle"))
    b.append(txt(198, 150, "Isolation cells clamp every signal leaving the switched "
                           "domain.", 9, "middle"))
    b.append(txt(198, 164, "Without them, a floating input burns static current in the "
                           "domain that is still on.", 9, "middle",
                 'font-style="italic"'))
    return svg(400, 174, "".join(b))


def ch_powerintent():
    s = ['<h1 id="x43">X43. Power Intent: Domains, Retention and Isolation</h1>']
    s.append("""<p>Power gating is the only technique that attacks leakage to near zero,
    and it is the one that changes an IP block's interface, its reset behaviour and its
    verification plan. A vendor whose block supports it properly is selling something
    materially different from one whose block does not.</p>""")
    s.append(fig(_f_pd(), "A switchable power domain and the cells that make it safe."))

    s.append("<h2>X43.1 The four special cells, and what each prevents</h2>")
    s.append(tab("Low-power cells",
        ["Cell", "Sits", "Prevents", "Cost"],
        [["<b>Isolation</b>", "On every signal leaving a switched domain",
          "<b>A floating value driving the always-on domain</b>, which causes static "
          "crowbar current in the receiving gate",
          "One gate per signal, plus the enable's routing"],
         ["<b>Level shifter</b>", "Between domains at different voltages",
          "A low-voltage 1 failing to turn off a high-voltage PMOS &mdash; again "
          "static current", "One cell per signal; slower than a buffer"],
         ["<b>Retention flop</b>", "Replacing flops whose state must survive",
          "<b>Losing state on power-down</b>",
          "<b>20&ndash;30&nbsp;% larger than a normal flop, plus always-on routing for "
          "the save/restore signals</b>"],
         ["Power switch", "Between the always-on rail and the domain",
          "&mdash;", "Area, and <b>IR drop through the switch when on</b>; the "
          "switching itself is an inrush event (Part&nbsp;X32)"],
         ["Always-on buffer", "On signals crossing a domain that is off",
          "A signal path being cut", "Special placement"]]))
    s.append(ex("Is retention worth it, or should the block re-initialise?",
        "A block with 20&#8239;000 flops, of which 3&#8239;000 hold configuration and "
        "17&#8239;000 hold datapath state. Leakage when on is 12&nbsp;mW. The alternative "
        "to retention is for software to rewrite the configuration on wake.",
        "Compare three options on area, wake latency and residual leakage. Retention "
        "flops still leak, because their storage is always on.",
        [("Retain everything: retention flops", num(20000)),
         ("Area penalty at 25&nbsp;%", num(20000 * 0.25) + " flop-equivalents"),
         ("Residual leakage (retention cells stay powered)",
          num(12 * 0.15, 4, "mW") + " (~15&nbsp;%)"),
         ("<b>Retain configuration only</b>", num(3000) + " retention flops"),
         ("Area penalty", num(3000 * 0.25) + " flop-equivalents"),
         ("Residual leakage", num(12 * 0.03, 4, "mW")),
         ("Retain nothing: software rewrite",
          num(0) + " retention flops"),
         ("Wake latency added", "<b>thousands of register writes over APB</b>"),
         ("Best for a block woken rarely", "<b>retain configuration only</b>")],
        "<b>By retaining everything because it is simplest.</b> Datapath state is "
        "usually worthless across a power-down &mdash; the block was idle, so there is "
        "nothing in flight &mdash; and retaining it costs area and leakage for nothing. "
        "<b>The design work is to partition state into what must survive and what must "
        "not</b>, and then to make the latter's reset unconditional so that a wake-up is "
        "indistinguishable from a cold start. That partition is a specification item and "
        "is the single most useful thing a vendor can document about power "
        "behaviour."))

    s.append("<h2>X43.2 What UPF adds, and why RTL alone is not enough</h2>")
    s.append(derive("Why power intent lives outside the RTL", [
        ("RTL describes function; it has no notion of a supply.",
         "A Verilog module does not say which rail powers it."),
        ("Power domains, switches, isolation and retention are <i>structural</i> and "
         "depend on the floorplan and the process.",
         "The same RTL is used with and without power gating in different products."),
        ("<b>So they are described in a separate file &mdash; UPF or CPF &mdash; that "
         "the tools read alongside.</b>",
         "Synthesis inserts the cells, verification simulates the power states, and "
         "place-and-route builds the switch network."),
        ("Simulation must then model a powered-down domain as X, and check that "
         "isolation is enabled before power goes away.",
         "<b>This is the verification that cannot be done in RTL alone</b>, and it is "
         "where the bugs are."),
        ("The power state table enumerates the legal combinations of domain states.",
         "<b>And the illegal ones are what must be proven unreachable</b> &mdash; a "
         "formal problem of exactly the kind Part&nbsp;X33 recommends."),
    ]))
    rows = []
    for domains in (2, 3, 4, 5, 6):
        states = 2 ** domains
        legal = domains + 1
        rows.append([num(domains), num(states), num(legal),
                     num(states - legal), num(states * (states - 1))])
    s.append(sweep("Power-state space against domain count",
        ["Switchable domains", "Combinations", "Typically legal states",
         "Illegal states to exclude", "Ordered transitions"], rows,
        "The legal column assumes a simple nested hierarchy &mdash; each domain "
        "requires the ones below it. <b>The transition column is the verification "
        "burden</b>, and it is quadratic, which is why power-state machines are kept "
        "deliberately simple and why a block that demands its own independent domain is "
        "expensive to integrate."))
    s.append("""<div class="warn"><b>The classic power-gating bug is an isolation enable
    that arrives too late, and it is not a functional bug in the usual sense.</b> If power
    is removed before isolation is enabled, the outputs float for a short interval;
    downstream gates in the always-on domain then sit at an intermediate level and
    conduct, drawing a current spike that is invisible to functional simulation and shows
    up as excess power or, in the worst case, as damage. <b>The sequence is: assert
    isolation, assert retention save, then remove power &mdash; and the reverse on
    wake.</b> Getting it right is a small state machine; proving it right requires
    power-aware simulation, and asserting it is what a UPF-aware formal check does. An IP
    block that supplies its own power-control sequence and the assertions that check it is
    removing a whole class of integration risk.</div>""")

    s.append("<h2>X43.3 DVFS: the controller and its constraints</h2>")
    rows = []
    for v, f in ((0.9, 1200), (0.8, 1000), (0.7, 800), (0.6, 600), (0.5, 400)):
        p = (v / 0.9) ** 2 * (f / 1200)
        e = (v / 0.9) ** 2
        rows.append([num(v, 3), num(f), num(p, 4), num(e, 4),
                     num(f / 1200, 4), num(p / (f / 1200), 4)])
    s.append(sweep("A DVFS operating-point table, normalised to the top point",
        ["<i>V</i> (V)", "<i>f</i> (MHz)", "Relative power",
         "Relative energy per operation", "Relative throughput",
         "Power per unit throughput"], rows,
        "<b>Energy per operation falls monotonically as voltage drops</b> (the "
        "<i>V</i><sup>2</sup> term), which is Part&nbsp;X7's result in the form a "
        "system actually uses. The last column is what a governor optimises when the "
        "work must be finished by a deadline rather than as fast as possible."))
    s.append(prob("Why is &lsquo;race to idle&rsquo; sometimes better than running "
                  "slowly, when X43.2 shows energy per operation is lowest at low "
                  "voltage?",
        "Because the block is not the only thing consuming power. Running at the top "
        "operating point finishes the work sooner and lets the <i>whole subsystem</i> "
        "&mdash; memory, interconnect, PLLs, the always-on logic, and any peripheral "
        "waiting on the result &mdash; enter a low-power state earlier. That static and "
        "shared component does not scale with the block's voltage, so the comparison is "
        "between (fast, high dynamic, short time, then everything off) and (slow, low "
        "dynamic, long time, everything on throughout). <b>Race to idle wins when the "
        "fixed overhead per unit time is large relative to the block's own dynamic "
        "power</b>, which is common in small IP blocks inside large systems and uncommon "
        "in a block that dominates its chip. <b>The crossover is computable</b> from the "
        "block's dynamic power at each point, the platform's idle power, and the "
        "entry/exit energy of the low-power state &mdash; and it is worth computing "
        "rather than asserting, because both answers appear in the literature and both "
        "are right for their own systems."))
    return "\n".join(s)
