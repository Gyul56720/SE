# -*- coding: utf-8 -*-
"""house/people -- the five engineers.

These are not people, they are **roles**. They carry names because a report
needs a signatory (the corporate mail template demands one) and because five
reports coming from five different responsibilities should be visible as such
at a glance.

Each person has a `role` (what they are accountable for), `tools` (what they
actually invoke) and `artifacts` (what they leave behind). **The tools column
lists only what really runs in this repository** -- the commercial stack
(VCS, Verdi, DC, ICC2, Tessent, PrimeTime) is not on this machine. We do not
write as if we used something we did not. Instead we build an equivalent
inside the repo and every report states what the measurement was taken with.
"""
from __future__ import annotations

COMPANY = "Nowon Silicon Works"
COMPANY_SHORT = "NSW"
DOMAIN = "nowonsilicon.dev"       # for the signature block; the actual sender is SMTP_USER


class Person:
    def __init__(self, key, name, title, team, role, tools, artifacts, tagline,
                 pronouns="they/them"):
        self.key = key
        self.name = name
        self.title = title
        self.team = team
        self.role = role
        self.tools = tools
        self.artifacts = artifacts
        self.tagline = tagline
        self.pronouns = pronouns

    @property
    def email(self) -> str:
        first = self.name.split()[0].lower()
        last = self.name.split()[-1].lower()
        return f"{first}.{last}@{DOMAIN}"

    @property
    def signature(self) -> str:
        return f"{COMPANY} / {self.team} / {self.title}"

    def __repr__(self):
        return f"<Person {self.key} {self.name}>"


# --------------------------------------------------------------------------
# Five engineers. The disciplines are exactly the five the user specified --
# RTL (+HLS), DV, PI (synthesis), DFT, PD. Two of them are women.
# --------------------------------------------------------------------------

ETHAN = Person(
    "rtl", "Ethan Ross", "Staff Engineer", "Front-End Design",
    role="HLS and RTL design. Takes a C++ behavioural description through "
         "scheduling and binding to RTL (HLS), and writes SystemVerilog for FSM "
         "control flow, pipelining, parameterised reuse, clock/reset structure, "
         "clock-gating power optimisation and CDC.",
    tools=["house/hls (in-house HLS: DFG -> schedule -> bind -> SV emission)",
           "verilator 5.020 --lint-only -Wall (RTL lint)",
           "iverilog / vvp (elaborate and functional check)",
           "house/rtl/cdc.py (static CDC check -- domain propagation, "
           "synchroniser recognition)"],
    artifacts=["SystemVerilog RTL", "FSM state table and diagram",
               "pipeline reservation table", "CDC crossing inventory",
               "clock-gating toggle comparison, before and after"],
    tagline="Turns a specification into logic that runs, and explains in numbers "
            "why the logic has the shape it has.",
    pronouns="he/him")

PRIYA = Person(
    "dv", "Priya Raghavan", "Verification Lead", "Design Verification",
    role="Stands up a UVM-shaped verification environment, throws thousands to "
         "tens of thousands of constrained-random transactions at the DUT and "
         "judges them with a scoreboard. Closes functional and code coverage, "
         "and proves the checkers actually bite by injecting mutations. "
         "'Verification is done' is a claim that may only be made with coverage "
         "numbers and mutation results.",
    tools=["verilator 5.020 (--cc, C++ harness) -- hundreds of thousands of "
           "cycles per second",
           "house/dv/uvm_like.py (agent/driver/monitor/scoreboard/coverage)",
           "house/dv/mutate.py (RTL mutation injection -- proves checkers bite)",
           "iverilog/vvp (a second simulator, for cross-checking)"],
    artifacts=["coverage closure curve", "cross-coverage heat map",
               "mutation survival table", "per-transaction mismatch log",
               "regression statistics (seeds, cycles, errors)"],
    tagline="Having written all the code proves nothing. Having thrown ten "
            "thousand transactions at it proves something.",
    pronouns="she/her")

MARCUS = Person(
    "syn", "Marcus Webb", "Principal Engineer",
    "Synthesis & Physical Implementation (PI)",
    role="Maps RTL to a netlist, applies the SDC constraints and runs STA across "
         "the full PVT corner set. Confirms in numbers that timing still closes "
         "when voltage, temperature and process move, and that the UPF power "
         "domains really do switch off and back on.",
    tools=["yosys (synthesis -- a real tool)",
           "house/syn/sdc.py (SDC parser: create_clock, set_input_delay, "
           "false/multicycle paths)",
           "house/syn/sta_pvt.py (extends lab/se/sta across PVT corners, OCV derate)",
           "house/syn/upf.py (UPF-lite: power domains, isolation, retention)"],
    artifacts=["per-corner slack table and plot",
               "critical-path stage-by-stage delay decomposition",
               "power breakdown (dynamic/leakage)", "temperature-inversion curve",
               "UPF domain state table"],
    tagline="Closing in one corner is not closing. Closing in 216 corners is closing.",
    pronouns="he/him")

SOFIA = Person(
    "dft", "Sofia Almeida", "Senior Engineer", "Design for Test",
    role="Inserts scan chains so the inside becomes observable, generates patterns "
         "with ATPG, and adds BIST so the chip can test itself. Computes how many "
         "bad dice escape across a million-unit run (DPPM) and sets the coverage "
         "target from that number.",
    tools=["house/dft/scan.py (scan insertion, chain ordering, shift length)",
           "house/dft/atpg.py (random + deterministic ATPG, parallel-pattern "
           "fault simulation)",
           "house/dft/bist.py (MBIST March C-, LBIST LFSR/MISR signature)",
           "house/dft/yield_.py (Williams-Brown DL, Monte-Carlo cross-check)"],
    artifacts=["fault-coverage curve", "pattern count vs test time and cost",
               "chain length vs compression ratio", "MBIST March algorithm table",
               "DPPM vs coverage curve"],
    tagline="Test does not prove a die is good. It bounds how many bad ones escape.",
    pronouns="she/her")

KENJI = Person(
    "pd", "Kenji Tanaka", "Staff Engineer", "Physical Design",
    # **경계를 적는다.** 이 단계는 보통 고객 SoC 쪽 일이다 -- IP 하우스의 인도물은
    # RTL · 테스트벤치 · 제약 · PPA 표까지다. 우리는 이 단계를 실제로 돌리지만
    # 그것은 **시연**이지 인도물이 아니다(house/flow.py 의 갈래).
    role="Runs the back-end flow end to end as a DEMONSTRATION, not as a "
         "deliverable: floorplan and power grid, placement and routing, CTS, "
         "sign-off checks, and a GDSII stream written to spec. In an IP house "
         "this stage normally belongs to the customer's SoC team -- what we "
         "hand over is RTL, testbench, constraints and a PPA table.",
    tools=["house/pd (extends lab/se floorplan, place, cts, route, signoff)",
           "house/pd/gds.py (writes the GDSII stream binary directly -- real spec)",
           "house/pd/drc.py (spacing, minimum width, density rule checks)",
           "no klayout -> the GDS is read back with our own parser for a "
           "round-trip check"],
    artifacts=["floorplan and placement drawings", "congestion heat map",
               "clock-tree drawing and skew distribution", "IR-drop map",
               "GDSII file with per-layer shape counts "
               "(a demonstration that the writer follows the stream spec -- "
               "NOT an IP deliverable)"],
    tagline="The other four can be right and the chip still dies here. "
            "Geometry does not negotiate.",
    pronouns="he/him")

EVERYONE = [ETHAN, PRIYA, MARCUS, SOFIA, KENJI]
BY_KEY = {p.key: p for p in EVERYONE}
BY_NAME = {p.name.lower(): p for p in EVERYONE}

# Aliases -- what a human actually types in Discord. `!company verification`
# and `!company priya` both resolve. Korean aliases stay: they are *input*,
# not output, and dropping them would break how the user already talks to it.
ALIASES = {
    "rtl": "rtl", "design": "rtl", "hls": "rtl", "frontend": "rtl",
    "ethan": "rtl", "ross": "rtl", "설계": "rtl",
    "dv": "dv", "verification": "dv", "verify": "dv", "uvm": "dv",
    "priya": "dv", "raghavan": "dv", "검증": "dv",
    "syn": "syn", "synthesis": "syn", "pi": "syn", "sta": "syn",
    "marcus": "syn", "webb": "syn", "합성": "syn",
    "dft": "dft", "test": "dft", "scan": "dft", "atpg": "dft",
    "sofia": "dft", "almeida": "dft", "테스트": "dft",
    "pd": "pd", "physical": "pd", "layout": "pd", "gds": "pd",
    "kenji": "pd", "tanaka": "pd", "물리설계": "pd", "레이아웃": "pd",
}


def find(text: str):
    """Pick an owner from what a human typed. None if nothing matches."""
    t = (text or "").strip().lower()
    if not t:
        return None
    if t in ALIASES:
        return BY_KEY[ALIASES[t]]
    for k, v in ALIASES.items():
        if k in t:
            return BY_KEY[v]
    return None


def org_chart() -> str:
    """A one-screen org chart, ready to paste into Discord."""
    lines = [f"**{COMPANY}** ({COMPANY_SHORT}) -- one-person design house, "
             f"5 engineers", ""]
    for p in EVERYONE:
        lines.append(f"· **{p.name}** -- {p.team} / {p.title}  (`!company {p.key}`)")
        lines.append(f"   {p.tagline}")
    return "\n".join(lines)
