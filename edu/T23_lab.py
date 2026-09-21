# -*- coding: utf-8 -*-
"""T23 -- 흐름을 끝까지 한 번 돌린 결과.  수는 전부 `lab/` 에서 온다."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch
import sch_flow

_기준길 = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "lab", "기준.json")


def 기준():
    """**이 장의 모든 수는 이 파일에서 온다.**

    지어낸 수도, 인용한 수도 아니다.  `python3 lab/run.py` 가 yosys 를 돌리고
    나머지 여덟 단계를 풀어서 낸 것을 그대로 싣는다.  `tests/test_lab.py` 가
    같은 흐름을 다시 돌려서 이 파일과 맞는지 본다 -- 그래서 이 장이 낡으면
    검사가 빨개진다.
    """
    with open(_기준길, encoding="utf-8") as f:
        return json.load(f)["결과"]


def ch_lab():
    R = 기준()
    s, st = R["synth"], R["sta"]
    fp, pl, ct = R["fp"], R["place"], R["cts"]
    rt, so, df, dv = R["route"], R["signoff"], R["dft"], R["dv"]

    c = 장(
        "T23", "The Flow, Run End to End — One Block, Nine Stages, Real Numbers",
        "Every number in this chapter was produced by running the flow in this "
        "repository. None of them is quoted.",
        쓰는것=["구현흐름", "합성", "넷리스트", "정적타이밍분석", "슬랙",
              "표준셀행", "SITE", "점유율", "코어영역", "파워스트라이프",
              "배치", "합법화", "HPWL", "클럭트리합성", "삽입지연", "클럭스큐",
              "전역배선", "상세배선", "탐색수리", "혼잡도", "사인오프",
              "물리검증", "코너", "스캔", "스캔체인", "ATPG", "고착고장",
              "결함커버리지", "결함수준", "DPPM", "시험시간", "스캔압축",
              "검증환경", "스코어보드", "기능커버리지", "크로스커버리지",
              "제약랜덤", "지시시험", "일렉트로마이그레이션", "전압강하"],
        내놓는것=["실습흐름", "회귀기준"],
        특허="""Nothing here is patentable and that is the point: the flow is
        commodity, the value is in knowing what each number means and which of them
        is lying to you.""")

    c.글(f"""The five chapters before this one computed the flow's quantities from
    models. This one runs it. The design is a small MAC with a control FSM, a
    two-flop synchroniser and a gated accumulator; it is synthesised by
    <b>yosys</b> against a cell library generated from the RC model of T2, and the
    remaining eight stages are implemented in this repository because the machine
    has no commercial place-and-route tool. That constraint turned out to be an
    advantage: <b>every intermediate quantity is visible and re-measurable</b>,
    which is exactly what a commercial tool does not give you.""")

    c.날것(짚기(f"""Reproduce everything in this chapter with one command:
    <code>python3 lab/run.py</code>. It takes about eight seconds. Individual
    stages: <code>python3 lab/run.py --stage sta</code> (or
    <code>fp place cts route signoff dft dv</code>). The numbers below are read
    from <code>lab/기준.json</code>, which that command writes, and
    <code>tests/test_lab.py</code> re-runs the flow and checks they still
    agree — so <b>if this chapter goes stale, a test goes red</b>."""))

    # ------------------------------------------------------------------
    c.절("T23.1 The nine stages, and what each one measured")

    c.날것(표("One run, end to end",
        ["Stage", "What it did", "The number that matters"],
        [["<b>01 Synthesis</b> (yosys)",
          f"RTL → {s['인스턴스']} cells, {s['플롭']} flops",
          f"{수(s['셀면적_um2'],6,' µm²')} of cell area — the input to every "
          f"area decision downstream"],
         ["<b>02 STA</b> (pre-route)",
          f"{st['임계경로_단수']}-stage critical path",
          f"F<sub>max</sub> = {수(st['Fmax_MHz'],5,' MHz')}, and the two "
          f"independent methods agree to "
          f"{수(st['두길_차이_ps'],3,' ps')}"],
         ["<b>03 Floorplan</b>",
          f"{fp['행수']} rows × {fp['행당_자리수']} sites at "
          f"{수(100*fp['점유율'],3,' %')} utilisation",
          f"core {수(fp['코어_um'][0],5,' µm')} × "
          f"{수(fp['코어_um'][1],5,' µm')}; the stripe width is set by "
          f"<b>{fp['무는것']}</b>"],
         ["<b>04 Placement</b>",
          "force-directed, then two-sweep legalisation",
          f"HPWL {수(pl['HPWL_전역_um'],6,' µm')} → "
          f"{수(pl['HPWL_합법_um'],6,' µm')}, overlaps {pl['겹침']}"],
         ["<b>05 CTS</b>",
          f"{ct['단수']}-level tree, {ct['버퍼']} buffers",
          f"insertion {수(ct['삽입지연_ps'],5,' ps')}, skew "
          f"{수(ct['스큐_ps'],4,' ps')}"],
         ["<b>06 Routing</b>",
          f"global on a {rt['gcell'][0]}×{rt['gcell'][1]} gcell grid, then "
          f"rip-up and reroute",
          f"{수(rt['총배선길이_um'],6,' µm')} of wire — detour factor "
          f"{수(rt['우회비_배선길이/HPWL'],4,'×')} over HPWL"],
         ["<b>07 Signoff</b>",
          "re-extract, re-run STA with real RC",
          f"F<sub>max</sub> {수(so['배선전']['Fmax_MHz'],5,' MHz')} → "
          f"<b>{수(so['배선후']['Fmax_MHz'],5,' MHz')}</b>"],
         ["<b>08 DFT</b>",
          f"{df['총고장']} stuck-at faults, parallel-pattern fault simulation",
          f"{수(100*df['커버리지'],5,' %')} coverage with "
          f"{df['패턴수']} random patterns"],
         ["<b>09 DV</b>",
          f"{dv['회귀']['거래']} transactions through a UVM-shaped environment",
          f"{dv['회귀']['어긋남']} mismatches; "
          f"{len(dv['변이검사']['변이'])} mutations, "
          f"{dv['변이검사']['구멍']} escaped"]]))

    c.날것(그림(sch_flow.실습흐름({
        "synth": f"{s['인스턴스']} cells, {s['플롭']} flops, "
                 f"{s['셀면적_um2']:.0f} um2",
        "sta": f"Fmax {st['Fmax_MHz']:.2f} MHz, {st['임계경로_단수']} stages, "
               f"two methods agree to {st['두길_차이_ps']} ps",
        "fp": f"core {fp['코어_um'][0]:.1f} x {fp['코어_um'][1]:.1f} um, "
              f"{fp['행수']} rows, stripe width set by {fp['무는것']}",
        "place": f"HPWL {pl['HPWL_전역_um']:.0f} -> {pl['HPWL_합법_um']:.0f} um, "
                 f"overlaps {pl['겹침']}",
        "cts": f"insertion {ct['삽입지연_ps']:.0f} ps, skew "
               f"{ct['스큐_ps']:.0f} ps; balancing costs "
               f"{ct['균형맞추기']['끼운버퍼']} buffers",
        "route": f"{rt['총배선길이_um']:.0f} um, detour "
                 f"{rt['우회비_배선길이/HPWL']}x, overflow {rt['넘친칸']}",
        "signoff": f"Fmax {so['배선전']['Fmax_MHz']:.1f} -> "
                   f"{so['배선후']['Fmax_MHz']:.1f} MHz, drift "
                   f"{so['표류_평균_ps']:.0f} ps",
        "dft": f"{df['총고장']} faults, {df['패턴수']} patterns, "
               f"{100*df['커버리지']:.2f} % coverage",
        "dv": f"{dv['회귀']['거래']} transactions, {dv['회귀']['어긋남']} "
              f"mismatches, {dv['변이검사']['구멍']} mutations escaped",
    }), "The run this chapter reports, stage by stage. Reproduce it with one "
        "command; every box is a number a test re-measures."))

    # ------------------------------------------------------------------
    c.절("T23.2 The four results worth arguing with")    # ------------------------------------------------------------------
    c.절("T23.2 The four results worth arguing with")

    _떨어짐 = 100 * so["Fmax_떨어진비"]
    c.날것(유도("1. Pre-route timing is not optimistic by a little", [
        (f"Synthesis and pre-route STA report "
         f"{수(so['배선전']['Fmax_MHz'],5,' MHz')} with "
         f"{수(so['배선전']['최악슬랙_ns']*1e3,5,' ps')} of slack.",
         "No wire RC at all — the optimistic bound of T17.2."),
        (f"After routing, the same endpoints report "
         f"{수(so['배선후']['Fmax_MHz'],5,' MHz')} and "
         f"{수(so['배선후']['최악슬랙_ns']*1e3,5,' ps')}.",
         "Same netlist, same library, same constraints. The only new "
         "information is where the wires actually went."),
        (f"That is {수(_떨어짐,3,' %')} of F<sub>max</sub>, and the average "
         f"endpoint moved {수(so['표류_평균_ps'],5,' ps')}.",
         "<b>Average</b>, not worst. Every endpoint got worse, because every "
         "net acquired resistance and capacitance it did not have."),
        (f"The design now <b>fails</b>: {so['배선후']['위반_끝점']} "
         "endpoint(s) violate at the target period.",
         "Which is the honest outcome of running a flow without a "
         "physically-aware synthesis step — and the quantitative argument for "
         "having one."),
    ]))

    c.날것(짚기(f"""<b>Kill the trivial explanation.</b> A {수(_떨어짐,3,' %')}
    drop could just mean the wire model is too pessimistic. Two things say
    otherwise. The detour factor is {수(rt['우회비_배선길이/HPWL'],4,'×')} over
    HPWL, which is in the range real routers produce; and the wire delay comes
    from the same R and C per micron used to size the power grid, where the
    resulting IR drop came out sane. Neither is proof. What would be proof is a
    second extraction method, and this lab does not have one —
    <b>so the number is reported with that limitation attached.</b>"""))

    _b = ct["균형맞추기"]
    c.날것(유도("2. Skew is bought, not given", [
        (f"The tree as built by geometry alone has "
         f"{수(ct['스큐_ps'],4,' ps')} of skew on "
         f"{수(ct['삽입지연_ps'],5,' ps')} of insertion delay — "
         f"{수(100*ct['스큐/삽입지연'],4,' %')}.",
         "Clustering by position minimises wire, not arrival time. Nothing in "
         "the construction balances anything."),
        (f"Balancing it to about 2 % costs {_b['끼운버퍼']} extra buffers.",
         "Delay is added to the early branches until they match the late one. "
         "That is what a CTS tool does after it builds the tree."),
        (f"Those buffers raise the clock network's power by "
         f"{수(100*_b['전력_늘어난비'],4,' %')}.",
         "They switch every cycle, like everything else on the clock. "
         "<b>The trade is skew against power and it is quantitative.</b>"),
        (f"Result: {수(_b['맞춘뒤_스큐_ps'],4,' ps')}, i.e. "
         f"{수(100*_b['맞춘뒤_스큐비'],3,' %')} of insertion delay.",
         "Which is the figure the industry quotes, and now it has a price "
         "tag attached."),
    ]))

    c.날것(표("3. The repair loop does not converge — measured",
        ["Pass", "Violations open", "Ratio to the previous pass"],
        [[str(i), str(v),
          ("—" if i == 0 else
           수(rt['탐색수리']['비'][i - 1], 4))]
         for i, v in enumerate(rt["탐색수리"]["열"])]))

    c.날것(짚기(f"""The sequence is {rt['탐색수리']['열']} and the ratios rise
    above 1 repeatedly, so the loop is <b>moving</b> violations rather than
    repairing them — the exact signature T19.4 describes. Two consequences were
    built into the lab because of it. The router keeps the best solution it has
    seen rather than the last one (best {rt['탐색수리']['최선']}, last
    {rt['탐색수리']['열'][-1]}), which is what a real router does and what
    turns "more iterations make it worse" from a conclusion into an artefact.
    And the correct response to a non-converging loop is not another pass: it is
    to go back up the flow — lower the utilisation, spread the placement, add a
    layer."""))

    _잡은 = {x["변이"]: x.get("잡은_검사") for x in dv["변이검사"]["변이"]}
    c.날것(표("4. The mutation campaign found a hole in the checking, not in the "
        "stimulus",
        ["Mutation", "What it breaks", "Caught by"],
        [[x["변이"], x.get("뜻", ""), x.get("잡은_검사", "—")]
         for x in dv["변이검사"]["변이"]]))

    c.날것(사고(f"""The <code>m3_pulse</code> mutation — replacing the one-cycle
    pulse with a level — was <b>not caught</b> by the first regression, and it was
    not caught after adding a directed test that holds <code>start</code> high for
    twenty cycles either. The reason is instructive: with a level, the FSM
    re-triggers as soon as it returns to idle, and the <i>first</i> completion's
    accumulator value is still correct. A value comparison cannot see it.
    <b>The hole was in the checking, not in the stimulus</b>, and it closed only
    when the scoreboard began asserting that each transaction produces exactly one
    <code>done</code>. That single protocol check is what takes the campaign from
    one escape to {dv['변이검사']['구멍']}."""))

    # ------------------------------------------------------------------
    c.절("T23.3 What this lab does not do")

    c.날것(표("Honest limits — read these before quoting any number above",
        ["Not done", "Why it matters", "What would fix it"],
        [["<b>No commercial P&amp;R</b>",
          "The placer, router and CTS here are teaching implementations. Their "
          "absolute quality is not comparable to a production tool",
          "OpenROAD would run this same netlist; the flow is deliberately "
          "structured so it could be swapped in"],
         ["<b>One extraction model</b>",
          "Wire R and C come from a single per-micron constant. The "
          f"{수(_떨어짐,3,' %')} F<sub>max</sub> drop therefore has no "
          "independent control",
          "A second extraction (field solver, or a different model) and a "
          "comparison of the two"],
         ["<b>No DRC, no LVS</b>",
          "Routing produces track counts, not geometry, so nothing here can "
          "assert manufacturability (T20.1)",
          "A real layout database and a rule deck — neither of which exists on "
          "this machine"],
         ["<b>Stuck-at only</b>",
          f"The {수(100*df['커버리지'],5,' %')} coverage is stuck-at coverage. "
          "Transition and bridging faults are not simulated",
          "At-speed patterns and a layout-extracted bridging list (T22.1)"],
         ["<b>Random ATPG only</b>",
          f"{df['남은수']} faults remain and random patterns will not reach "
          "them — this is T21.3's rare-bin problem in its test form",
          "Deterministic ATPG (a D-algorithm or a SAT call) for the residue"],
         ["<b>Power is assumed, not measured</b>",
          "The floorplan's current comes from an assumed W/mm², so the IR and "
          "EM conclusions inherit that assumption",
          "Toggle rates from the DV run, fed back into the power estimate — "
          "the two stages are in the same repository and are not yet "
          "connected"]]))

    c.날것(짚기("""That last row is worth dwelling on, because it is the kind of
    gap that survives for years. The verification run knows exactly how often
    every node toggles. The floorplan needs exactly that number. They are in the
    same program, in the same language, eight seconds apart — and they are not
    connected, so the power number is an assumption while the information that
    would replace it is sitting in the next directory. <b>Most of what looks like
    missing analysis in a real flow is this: two stages that have what the other
    needs and no path between them.</b>"""))

    # ------------------------------------------------------------------
    c.절("T23.4 What to do with this on Monday")

    c.날것(쓰는자리([
        ["실습흐름", "Learning the flow, or testing a change to it",
         "Nine stages you can read, break and re-measure in eight seconds"],
        ["회귀기준", "Every change to lab/ or to this chapter",
         "Whether the numbers in the book still match a real run"],
    ]))

    c.글(f"""Run it, then break something on purpose: raise the utilisation in
    <code>lab/se/floorplan.py</code> until legalisation fails; weaken the
    spreading force until legalisation destroys the placement; delete the
    done-count check in <code>lab/se/dv.py</code> and watch a mutation escape.
    <b>Each of those is a lesson from an earlier chapter arriving as a failure
    you caused</b>, which is the only way this material stops being a list of
    facts. The one command is <code>python3 lab/run.py</code>; the one file that
    holds the flow honest is <code>tests/test_lab.py</code>.""")

    return c.완성()
