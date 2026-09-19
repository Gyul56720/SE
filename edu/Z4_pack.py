# -*- coding: utf-8 -*-
"""Volume III, Part Z4 -- The deliverable pack, built and gated."""
import sys, os, re, subprocess
sys.path.insert(0, "/home/user/SE/edu")
sys.path.insert(0, "/home/user/SE/edu/house")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num

HOUSE = "/home/user/SE/edu/house"


def ch_pack():
    s = ['<h1 id="z4">Z4. The Deliverable Pack, Built and Gated</h1>']
    s.append("""<p>Part&nbsp;Y5 lists what a customer receives. This part builds it. Every
    artefact named here exists in this repository, every generator named here runs, and
    the gate that checks them is run while this page is rendered. A book that describes a
    deliverable pack without producing one is teaching the habit it warns
    against.</p>""")

    s.append("<h2>Z4.1 What is in the repository</h2>")
    rows = []
    for rel, what in (
            ("edu/house/regmap.py",
             "한 맵에서 RTL · C 헤더 · 문서 · IP-XACT 를 낸다"),
            ("edu/house/release.sh", "판매 가능 관문 전체를 한 번에 돌린다"),
            ("edu/house/DATASHEET.md", "데이터시트 (잰 수와 그 조건)"),
            ("edu/house/INTEGRATION.md", "통합 가이드 (전화하지 않고 끝낼 수 있게)"),
            ("edu/house/KNOWN_ISSUES.md", "알려진 제한 (없다고 적지 않는다)"),
            ("edu/agent/harness.py", "골든모델 대 RTL, 자해검사와 처리량 포함"),
            ("edu/agent/mutscore.py", "변이 점수 -- 검사가 무는지를 수로"),
            ("edu/agent/vrepair.py", "한 곳 편집 수리, 과적합 관문 포함"),
            ("edu/agent/agent.py", "밤새 도는 고리"),
            ("tests/test_verif_agent.py", "에이전트를 실제로 돌려 보는 검사"),
            ("tests/test_release_gate.py", "**관문 자체를 망가뜨려 보는 검사**")):
        p = os.path.join("/home/user/SE", rel)
        n = (len(open(p, encoding="utf-8").read().splitlines())
             if os.path.exists(p) else 0)
        rows.append([f"<code>{E(rel)}</code>", what,
                     num(n) if n else "<b>없다</b>"])
    s.append(sweep("The pack, with line counts read from disk at build time",
        ["File", "What it is", "Lines"], rows,
        "<b>Counted by reading the files as this page was rendered.</b> A row showing "
        "zero would mean the book is describing something that does not exist, which "
        "is the failure this table is designed to make visible."))

    s.append("<h2>Z4.2 One source, four outputs &mdash; measured</h2>")
    try:
        import regmap
        m = regmap.예제
        outs = [("RTL (Verilog)", regmap.rtl(m)),
                ("C header", regmap.c헤더(m)),
                ("Markdown (datasheet section)", regmap.마크다운(m)),
                ("IP-XACT", regmap.ipxact(m))]
        rows = [[n, num(len(t.splitlines())), num(len(t))] for n, t in outs]
        s.append(sweep(f"Generated from one map of {len(m.레지스터들)} registers and "
                       f"{sum(len(r.필드들) for r in m.레지스터들)} fields",
            ["Output", "Lines", "Characters"], rows,
            "Generated at build time. <b>Part&nbsp;Y10 computed that maintaining six "
            "copies by hand over a nine-month project has an expected nine missed "
            "edits</b>; the generator is a day's work and removes all nine."))
        s.append("""<div class="ms"><b>The map validates itself, and that is most of the
        value.</b> The definition refuses overlapping bit ranges, offsets that are not
        word-aligned, reset values too wide for their field, unknown access types,
        duplicate offsets, and &mdash; the one that matters most &mdash; a hardware-written
        field declared <code>RW</code>, which is the read-modify-write race of
        Part&nbsp;Y10. <b>Each of those is a defect that a hand-written map produces
        regularly and that nothing downstream detects</b>: the RTL compiles, the header
        compiles, the documentation looks right, and the bug appears in the customer's
        driver.</div>""")
    except Exception as e:
        s.append(f'<div class="warn">regmap did not run: {E(str(e))[:200]}</div>')

    s.append("<h2>Z4.3 What the gate says today</h2>")
    try:
        r = subprocess.run(["bash", os.path.join(HOUSE, "release.sh")],
                           capture_output=True, text=True, timeout=1500,
                           cwd="/home/user/SE")
        out = r.stdout
        블록 = re.findall(r"== (\w+) ==\n((?:  .*\n)+)", out)
        rows = []
        for 이름, 본문 in 블록:
            if 이름 == "집":
                continue
            p = 본문.count("통과")
            f = 본문.count("실패")
            u = 본문.count("못쟀다")
            셀 = re.search(r"셀 (\d+)개", 본문)
            점수 = re.search(r"변이점수\s+([\d.]+)%", 본문)
            rows.append([f"<code>{E(이름)}</code>", num(p), num(f), num(u),
                         (점수.group(1) + "&nbsp;%") if 점수 else "&mdash;",
                         num(int(셀.group(1))) if 셀 else "&mdash;"])
        총 = re.search(r"통과 (\d+) · 실패 (\d+) · 못쟀다 (\d+)", out)
        s.append(sweep("The release gate, run while this page was rendered",
            ["Block", "Passed", "Failed", "Unmeasured", "Mutation score",
             "Cells (yosys, open library)"], rows,
            (f"Totals: <b>{총.group(1)} passed, {총.group(2)} failed, "
             f"{총.group(3)} unmeasured.</b> " if 총 else "")
            + "The cell counts are from an open-source synthesis flow and an open "
              "library; <b>they are not an area figure in any customer's process</b>, "
              "and Part&nbsp;Y14's rule says to present them with that stated rather "
              "than to quote a bigger number without it."))
        if 총 and 총.group(2) != "0":
            s.append('<div class="warn"><b>The gate is currently failing.</b> The row '
                     'above is the live state, not an aspiration.</div>')
    except Exception as e:
        s.append(f'<div class="warn">Could not run the release gate: '
                 f'{E(type(e).__name__)}: {E(str(e))[:200]}</div>')

    s.append("<h2>Z4.4 Three generator bugs the gate found</h2>")
    s.append("""<p>The register-map generator was written from Part&nbsp;Y10's argument
    and looked correct. The agent and the gate found three defects in it, none of which
    any amount of reading would have found, and each is instructive about a different
    failure mode.</p>""")
    s.append(tab("What was found, and by which gate",
        ["Bug", "Found by", "Why reading would not have found it"],
        [["<b>An ID register could not hold a constant.</b> Every RO field was wired "
          "to a hardware input, so a vendor code read as zero",
          "The regression, against an independent model",
          "<b>The generator was internally consistent</b> &mdash; it did exactly what "
          "its author intended, and the intention was incomplete"],
         ["<b>A read-clear register cleared during the APB setup phase.</b> "
          "<code>rd</code> was <code>psel &amp; ~pwrite</code>, missing "
          "<code>penable</code>",
          "The regression, after the stimulus was extended",
          "It reads as correct; the defect is in the protocol's two-phase timing, which "
          "only a running comparison exposes"],
         ["<b>A software-set field had an unused hardware port.</b> W1S defaulted to "
          "hardware-driven, which is wrong for the common case",
          "<code>verilator -Wall</code> (UNUSEDSIGNAL)",
          "An unused port is harmless functionally and is a question the integrator "
          "has to ask you"]]))
    s.append("""<div class="warn"><b>And the mutation score found the stimulus hole that
    hid the second one.</b> Before it ran, the register-file regression was green on 400
    accesses and scored 58.3&nbsp;%. Five escapes all pointed at the same place: the
    hardware-side inputs were tied to zero, so the W1C and RC paths had never executed.
    Driving them turned up two real failures within minutes. <b>The green regression was
    not wrong &mdash; those 400 accesses did match &mdash; and it was nearly
    worthless.</b> That distinction is the whole argument for measuring whether a suite
    bites rather than whether it passes.</div>""")
    s.append(prob("You have one week before a customer evaluation. What do you build "
                  "first?",
        "Not more features. Build, in this order, the things the evaluation will "
        "actually test. <b>First the gate</b>, because everything else is easier to "
        "trust once one command produces the numbers; a day. <b>Then the mutation "
        "score</b>, because it is the single artefact that distinguishes you from a "
        "supplier who says &lsquo;we tested it thoroughly&rsquo;, and because it will "
        "find the stimulus holes you do not know about; half a day plus whatever it "
        "turns up. <b>Then the known-issue list</b>, which costs an afternoon and is "
        "read as competence rather than as weakness. <b>Then the integration guide</b>, "
        "written as if for someone you will never speak to. <b>Only then the "
        "datasheet</b>, because by that point every number in it exists and is "
        "reproducible &mdash; which means writing it takes an hour instead of a day and "
        "none of it is invented. <b>A week spent this way produces a smaller block that "
        "can be bought; a week spent on features produces a larger one that cannot.</b>"))
    return "\n".join(s)
