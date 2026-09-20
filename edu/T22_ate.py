# -*- coding: utf-8 -*-
"""T22 -- From DFT to the tester: test time, test cost, and what escapes anyway."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bookK import 장, 개념, 표, 그림, 정의, 유도, 예제, 짚기, 사고, 수, 쓰는자리
import sch
from T18_floorplan import 코어면적
from T19_pnr import 플롭수

# ---------------------------------------------------------------------------
# 가정과 그 출처.  T18/T19 의 블록을 그대로 이어받는다.
# ---------------------------------------------------------------------------
패턴수 = 5_000          # ATPG 가 낸 패턴 수 (가정)
시프트클럭 = 50e6       # Hz -- 시프트는 전력 때문에 기능 클럭보다 느리다 (T20.3)
포착사이클 = 4          # 패턴 하나당 포착에 드는 사이클 (가정)

테스터값 = 2_000_000.0  # 달러 (가정: 고급 SoC 테스터 한 대)
감가년 = 5
가동률 = 0.70
결함밀도 = 0.10         # 결함/cm^2 (가정)

# 이 블록 하나로는 압축도 수율도 재미있는 자리에 안 온다(아래에서 수로 보인다).
# 그래서 **같은 계산을 큰 SoC 에도** 건다 -- 가정은 여기 한 줄에 모은다.
SoC플롭 = 2_000_000
SoC면적_cm2 = 1.00       # cm^2 (약 100 mm^2)


def 시험시간(체인수, 압축=1, 플롭=None, 패턴=None):
    """다이 하나에 드는 스캔 시험 시간 (초).

    체인 하나의 길이는 플롭수/(체인수·압축) 이다.  압축은 테스터에서 보이는
    체인 수를 늘리는 것과 같다 -- 칩 안에서 해제기가 그만큼 갈라 준다.
    """
    체인길이 = (플롭 or 플롭수) / (체인수 * 압축)
    return (패턴 or 패턴수) * (체인길이 + 포착사이클) / 시프트클럭


def 패턴비트(체인수, 압축=1, 플롭=None, 패턴=None):
    """테스터의 패턴 메모리가 들고 있어야 하는 비트 (입력+출력)."""
    return 2 * (패턴 or 패턴수) * ((플롭 or 플롭수) / 압축)


def 초당값(사이트=1):
    """테스터 1초의 값 (달러).  병렬 시험은 이것을 나눈다."""
    초 = 감가년 * 365 * 24 * 3600 * 가동률
    return 테스터값 / 초 / 사이트


def 수율(면적_cm2=None, D=결함밀도):
    """포아송 수율 Y = exp(−A·D)."""
    A = 면적_cm2 if 면적_cm2 is not None else 코어면적 / 1e8   # µm^2 -> cm^2
    return math.exp(-A * D)


def 결함수준_닫힌꼴(Y, T):
    """윌리엄스–브라운: 시험을 통과한 것 중 불량인 비율 = 1 − Y^(1−T)."""
    return 1 - Y ** (1 - T)


def 결함수준_몬테카를로(Y, T, 판=200_000, 씨=3):
    """같은 수를 **식 없이** -- 다이를 하나씩 지어 결함을 뿌리고 시험해 본다.

    닫힌 꼴은 한 줄도 안 쓴다.  포아송으로 결함 수를 뽑고, 결함마다 확률 T 로
    잡히게 한 뒤, **통과한 것 가운데 결함이 남은 비율**을 센다.
    """
    r = random.Random(씨)
    람다 = -math.log(Y)
    통과, 탈출 = 0, 0
    for _ in range(판):
        # 포아송 뽑기 (Knuth)
        L, p, k = math.exp(-람다), 1.0, 0
        while True:
            p *= r.random()
            if p <= L:
                break
            k += 1
        if k == 0:
            통과 += 1
            continue
        if not any(r.random() < T for _ in range(k)):
            통과 += 1
            탈출 += 1
    return 탈출 / max(1, 통과)


def ch_ate():
    c = 장(
        "T22", "From DFT to the Tester — Time, Cost and What Escapes",
        "Test does not prove a die is good. It bounds how often a bad one ships, "
        "and the bound is computable.",
        쓰는것=["구현흐름", "검증환경", "스코어보드", "사인오프", "테이프아웃",
              "정적타이밍분석", "클럭게이팅", "동적IR", "스위칭벡터", "수율시그마",
              "패드용량", "MMMC", "코너", "번인", "와이블"],
        내놓는것=["스캔", "스캔체인", "ATPG", "고착고장", "천이지연고장",
                "결함커버리지", "스캔압축", "해제기", "압축기", "LBIST", "MBIST",
                "ATE", "핀일렉트로닉스", "패턴메모리", "테스트프로그램",
                "시험시간", "병렬시험", "다이수율", "결함수준", "DPPM",
                "웨이퍼시험", "양품다이"],
        특허="""Test compression is one of the most heavily patented areas in EDA —
        the decompressor architectures (ring generators, broadcast networks, sequential
        linear expanders) are the product, and the ratios they achieve are the
        competitive claim. So is <b>low-power ATPG</b>, which constrains patterns to
        limit simultaneous switching for the reason computed in T20.3. Both exist to
        move the numbers this chapter calculates.""")

    c.글("""A verified design (T21) manufactured through a signed-off flow (T20) still
    produces dies that do not work, because manufacturing is a physical process with
    defects. Test is the operation that separates them, and it is the only stage of the
    whole flow whose cost is paid <b>per part</b> rather than once. That single fact
    determines everything about how it is engineered.""")

    # ------------------------------------------------------------------
    c.절("T22.1 Scan, and the price of observability")

    c.날것(정의("스캔 (scan) · 스캔 체인 (scan chain)",
        "Every flop is replaced by one with a multiplexer on its input, selecting "
        "between the functional D and a scan input. In test mode the flops are wired "
        "into shift registers — <b>chains</b>. This makes every flop both controllable "
        "(shift a value in) and observable (shift the result out), which turns the "
        "intractable problem of testing sequential logic into the tractable one of "
        "testing combinational logic between two register boundaries."))

    c.날것(표("What scan costs, and what it buys",
        ["Cost", "Size", "What is bought"],
        [["Area", "The mux in every flop: roughly 5–10 % of the design",
          "Every flop becomes a test point"],
         ["Timing", "The mux is in the D path — a real delay on every register input",
          "Nothing, directly. This is pure cost, and it is why the scan mux is one of "
          "the most carefully optimised cells in any library"],
         ["Power", "Shift toggles far more nodes than functional operation (T20.3)",
          "Nothing. It constrains the shift frequency, which costs test time"],
         ["Routing", "The chains are long nets crossing the die",
          "Nothing, and chain ordering after placement is how the cost is contained"]]))

    c.날것(표("Fault models, and the defects each one is a proxy for",
        ["Model", "What it assumes", "What it misses"],
        [["<b>Stuck-at</b>", "A node is permanently 0 or 1",
          "Anything timing-dependent. It is a topological model and catches gross "
          "defects well"],
         ["<b>Transition / at-speed</b>",
          "A node changes too slowly to make the next capture",
          "Requires two patterns at functional speed — expensive, and constrained by "
          "the power the part can draw while doing it"],
         ["<b>Bridging</b>", "Two nodes shorted", "Which two — the realistic list "
          "comes from layout extraction, not from the netlist"],
         ["<b>IDDQ</b>", "Quiescent current is elevated when a defect conducts",
          "Nothing subtle, but it stopped working at leaky nodes: the leakage of a "
          "good die became comparable to the defect signal"]]))

    # ------------------------------------------------------------------
    c.절("T22.2 Test time is the design decision")

    c.날것(유도("How long one die takes on the tester", [
        (f"The block of T19 has {플롭수:,} flops.",
         "Carried across so this chapter is about the same chip as the last four."),
        (f"With one chain, applying a pattern means shifting {플롭수:,} cycles.",
         "The chain is a shift register of that length; every pattern must be pushed "
         "all the way in and the result all the way out."),
        (f"ATPG produces about {패턴수:,} patterns for a block of this size.",
         "<b>Assumed</b>, and it varies more with logic structure than with size."),
        (f"At a {수(시프트클럭/1e6,3,' MHz')} shift clock that is "
         f"{수(시험시간(1),4,' s')} per die.",
         "Multiplication. The shift clock is slow because of the power problem of "
         "T20.3, not because the flops cannot run faster."),
        ("Split into N chains and the shift length divides by N.",
         "Chains shift in parallel; the tester drives N inputs and watches N outputs. "
         "<b>The limit is tester channels</b>, not the design."),
        (f"With 100 chains: {수(시험시간(100),4,' s')}. "
         f"With 100 chains and 50× compression: {수(시험시간(100,50),4,' s')}.",
         "Compression puts a decompressor on-chip that fans a few tester channels out "
         "to many internal chains, so the tester-visible chain count rises without "
         "using more channels."),
    ]))

    줄 = []
    for 이름, 플롭, 패턴, 목록 in (
            (f"block ({플롭수//1000}k flops)", 플롭수, 패턴수,
             ((1, 1), (10, 1), (100, 1))),
            (f"SoC ({SoC플롭//1_000_000}M flops)", SoC플롭, 패턴수 * 8,
             ((1, 1), (100, 1), (100, 50), (100, 200)))):
        for 체인, 압축 in 목록:
            t = 시험시간(체인, 압축, 플롭, 패턴)
            줄.append([이름, str(체인), f"{압축}×",
                       수(플롭 / (체인 * 압축), 5), 수(t, 4, " s"),
                       수(패턴비트(체인, 압축, 플롭, 패턴) / 8e6, 4, " MB"),
                       수(t * 초당값(), 4, " $")])
    c.날것(표(f"Test time, pattern volume and cost per die "
        f"(tester at {수(테스터값/1e6,2,' M$')}, {감가년} years, "
        f"{수(100*가동률,3,' %')} utilisation)",
        ["Design", "Chains", "Compression", "Shift length", "Time per die",
         "Pattern memory", "Tester cost per die"], 줄))

    _블록100 = 시험시간(100, 1)
    _소크1 = 시험시간(1, 1, SoC플롭, 패턴수 * 8)
    _소크압 = 시험시간(100, 50, SoC플롭, 패턴수 * 8)
    c.날것(짚기(f"""<b>The block does not need compression; the SoC cannot do without
    it.</b> That contrast is the point of putting both in one table, and it is a useful
    corrective: at {플롭수:,} flops, splitting into 100 chains already brings the test
    to {수(_블록100,4,' s')} and compression on top of that buys a number too small to
    care about. At {SoC플롭:,} flops the same single-chain test is
    {수(_소크1,4,' s')} — {수(_소크1/60,3,' minutes')} per die, which is not a test
    plan, it is a reason the product does not exist — and 100 chains with 50×
    compression brings it to {수(_소크압,4,' s')}, or
    {수(_소크압*초당값(),4,' $')} of tester time per part."""))

    c.날것(짚기("""The <b>pattern memory</b> column deserves separate attention,
    because it is often the binding constraint rather than time. A tester has a finite
    pattern memory, and a pattern set that does not fit must be split into several
    loads, each costing handler and reload time on top of test time. A design that fits
    in memory at 50× compression and does not at 10× has a test cost discontinuity
    that no amount of shift-frequency tuning will smooth out."""))

    c.날것(그림(sch.블록도(
        [["Test program", "Pattern memory", "Pin electronics", "DUT pins"]],
        설명={"Test program": "what to run,\nlimits, binning",
             "Pattern memory": "the vectors,\nper channel",
             "Pin electronics": "drivers, comparators,\nlevels per pin",
             "DUT pins": "the die, on a probe\ncard or in a socket"}),
        "What an ATE is, functionally: a very precise, very expensive pattern player "
        "with a programmable timing generator and one driver/comparator pair per pin. "
        "Everything in the previous table is a statement about one of these boxes."))

    c.날것(개념(
        "병렬 시험 (multi-site test) — the other way to divide the cost",
        f"""<p>Compression reduces the time one die takes. Multi-site test reduces the
        cost of that time by testing several dies at once on the same tester, using
        separate channels for each. The cost per die divides by the site count almost
        exactly, because the tester's cost per second is fixed and the handler's
        overhead is shared.</p>
        <p>The limit is channels and power. A 4-site setup needs four times the
        channels, and the pin count per die therefore decides how many sites fit — which
        is a DFT decision made years earlier, when someone chose how many scan
        channels to bring out.</p>
        <p>For the block above: {수(시험시간(100,50)*초당값(),4,' $')} at one site
        becomes {수(시험시간(100,50)*초당값(4),4,' $')} at four, for the same test
        content and the same quality.</p>""",
        어디에="Production test planning, and — decisively — in the pin budget at "
             "floorplan time.",
        언제="Considered as soon as the package pin list is discussed. Adding scan "
            "channels later is a mask change.",
        어떻게="Count: (tester channels) ÷ (channels per die) = sites. Then check the "
             "power: the tester's DUT power supply must source the shift current of "
             "all sites at once, and that is where 4-site setups actually fail.",
        주의="""Multi-site amplifies a marginal test. If a site has slightly different
            contact resistance or a longer path from the driver, one site will fail
            parts the others pass — and the yield report will show it as a process
            problem. <b>Always check yield per site before investigating a yield
            excursion.</b>"""))

    # ------------------------------------------------------------------
    c.절("T22.3 BIST: moving the tester onto the die")

    c.날것(표("Where BIST wins and where it does not",
        ["Kind", "What it tests", "Why it is better than external patterns there"],
        [["<b>MBIST</b> (memory)",
          "Embedded RAMs, with algorithmic patterns (March tests)",
          "Memories are regular, so the pattern is an <i>algorithm</i>, not data — a "
          "small state machine replaces megabytes of vectors. And embedded memory pins "
          "are not accessible from outside at all"],
         ["<b>LBIST</b> (logic)",
          "Random logic, with an on-chip LFSR feeding the chains and a MISR "
          "compacting the results",
          "It runs at functional speed without a fast tester, and it can be re-run in "
          "the field. Its coverage is lower than ATPG's for the same time, because "
          "the patterns are random rather than targeted"],
         ["<b>Hybrid</b>",
          "LBIST for the bulk, top-up ATPG patterns for what random misses",
          "The combination reaches ATPG-like coverage with a fraction of the pattern "
          "volume — the two are complementary rather than alternatives"]]))

    c.날것(짚기("""The interesting property of MBIST is not that it saves test time. It
    is that <b>an embedded memory has no pins</b>: there is no way to apply a pattern to
    it from outside except through the surrounding logic, which is slow, low-coverage
    and enormously expensive in patterns. MBIST is not an optimisation of external
    memory test; it is the only practical way to do it at all. And once the hardware is
    there it can also repair — blowing fuses to swap in redundant rows — which turns a
    failing die into a good one and is worth more than the test time it saves."""))

    # ------------------------------------------------------------------
    c.절("T22.4 What test is actually worth: yield, coverage and escapes")

    _Yblk = 수율()
    _Y = 수율(SoC면적_cm2)
    c.날것(유도("Die yield, and why test coverage has a price", [
        (f"The core of T18 is {수(코어면적/1e6,4,' mm²')}; the SoC used above is "
         f"{수(SoC면적_cm2*100,4,' mm²')}.",
         "Both carried over. The block's figure ignores the pad ring, so it is an "
         "upper bound; the SoC figure is the one the arithmetic below uses, because "
         "yield is an <b>area</b> story and a small block has nothing interesting to "
         "say about it."),
        (f"With a defect density of {수(결함밀도,3,' /cm²')}, Y = exp(−A·D) is "
         f"{수(100*_Yblk,5,' %')} for the block and {수(100*_Y,4,' %')} for the SoC.",
         "<b>Assumed</b> defect density, and the Poisson model itself is the "
         "optimistic one — real defects cluster, which raises yield above this for the "
         "same average density."),
        ("Of the dies that fail, test catches a fraction T — the fault coverage.",
         "Coverage is measured by ATPG against a fault list, which is itself a model "
         "(T22.1). It is not the fraction of <i>defects</i> caught, and treating it as "
         "such is the standard error here."),
        ("A die ships bad if it has at least one defect and every defect is missed.",
         "The event that matters. It is the intersection of two things, which is why "
         "the answer is not simply 1−T."),
        ("Williams and Brown: the defect level among shipped parts is "
         "<b>DL = 1 − Y<sup>(1−T)</sup></b>.",
         "The classic result. Note its shape: at T = 1 it is zero, and at T = 0 it is "
         "1 − Y, the raw fail rate — both limits are right, which is the first check "
         "any formula should pass."),
    ]))

    줄 = []
    for T in (0.90, 0.95, 0.99, 0.999):
        닫 = 결함수준_닫힌꼴(_Y, T)
        mc = 결함수준_몬테카를로(_Y, T)
        줄.append([수(100 * T, 4, " %"), 수(1e6 * 닫, 5, " DPPM"),
                   수(1e6 * mc, 5, " DPPM"),
                   수(100 * abs(mc - 닫) / 닫, 3, " %")])
    c.날것(표(f"Shipped defect level at the SoC's Y = {수(100*_Y,4,' %')}, "
        f"two independent ways",
        ["Fault coverage T", "Williams–Brown", "Simulated wafer of 200,000 dies",
         "Disagreement"], 줄))

    c.날것(짚기("""<b>Read the disagreement column honestly.</b> The simulation builds
    dies one at a time, scatters Poisson defects into them, lets each defect be caught
    with probability T, and counts how many defective dies got through — using none of
    the formula. The agreement is good at high defect levels and gets worse at low ones,
    and that is <i>expected</i>: at the last row only a few dozen escapes occur in
    200,000 trials, so the Monte-Carlo sampling error is tens of per cent while the
    closed form has none. A disagreement that grows as the event gets rarer is the
    signature of sampling noise, not of a wrong formula — and distinguishing those two
    is exactly the check that makes an independent control worth running."""))

    c.날것(예제("Is 99 % coverage good enough?",
        f"The SoC above, Y = {수(100*_Y,4,' %')}, shipping into an automotive "
        f"customer who specifies under 100 DPPM.",
        f"At T = 99 % the defect level is {수(1e6*결함수준_닫힌꼴(_Y,0.99),4,' DPPM')}. "
        f"At T = 99.9 % it is {수(1e6*결함수준_닫힌꼴(_Y,0.999),4,' DPPM')}. "
        "Solve for the coverage that reaches 100 DPPM: "
        "T = 1 − ln(1−DL)/ln Y.",
        f"T must be at least "
        f"{수(100*(1 - math.log(1-100e-6)/math.log(_Y)),5,' %')}. "
        "Every tenth of a per cent of coverage above 99 % costs patterns, and "
        "patterns cost test time and pattern memory — the table in T22.2.",
        "<b>Coverage is not the only lever, and it is the expensive one.</b> Raising "
        "yield moves the same number: at Y = 95 % rather than "
        f"{수(100*_Y,3,' %')}, the same T = 99 % gives "
        f"{수(1e6*결함수준_닫힌꼴(0.95,0.99),4,' DPPM')} instead of "
        f"{수(1e6*결함수준_닫힌꼴(_Y,0.99),4,' DPPM')}. A defect-density improvement "
        "from the fab is worth more than the last per cent of fault coverage, and it "
        "does not cost test time.",
        덧="""And the model's own limits belong in the answer: fault coverage is
        coverage of a <i>fault model</i>, not of defects. A defect class the model does
        not describe — a resistive via that only fails hot, a marginal timing path —
        contributes to DPPM without appearing anywhere in T. That is what burn-in
        (T14) and at-speed patterns are for, and why an automotive flow uses both
        rather than pushing stuck-at coverage to 99.99 %."""))

    c.날것(사고("""A part met its DPPM target at wafer sort and failed it at the
    customer. The escapes were all marginal at-speed failures on one clock domain: the
    at-speed patterns existed, but shift power forced the capture clock down, and the
    'at-speed' test was running 30 % below functional frequency.
    <b>The coverage number was real and the test it described was not the test that
    ran.</b> Test-time and power constraints change what the patterns mean, and the
    coverage report does not know that."""))

    # ------------------------------------------------------------------
    c.절("T22.5 What to do with this on Monday")

    c.날것(쓰는자리([
        ["스캔 · 스캔체인 · ATPG · 고착고장 · 천이지연고장 · 결함커버리지",
         "DFT planning, before RTL freeze",
         "Whether the part is testable at all, and at what coverage"],
        ["스캔압축 · 해제기 · 압축기 · 시험시간 · 패턴메모리",
         "Choosing chain count and compression ratio",
         "The per-part test cost, which is paid on every part ever shipped"],
        ["ATE · 핀일렉트로닉스 · 테스트프로그램 · 병렬시험",
         "Production planning, and in the pin budget years earlier",
         "How many dies share one tester second"],
        ["LBIST · MBIST", "Any embedded memory; any part that self-tests in the field",
         "The only practical way to test a block with no pins"],
        ["다이수율 · 결함수준 · DPPM · 웨이퍼시험 · 양품다이",
         "Agreeing a quality target with a customer",
         "What coverage that target actually requires — and whether yield is the "
         "cheaper lever"],
    ]))

    c.글(f"""The numbers to carry: on the 2 M-flop SoC, one chain is
    {수(_소크1/60,4,' minutes')} per die and 100 chains with 50× compression is
    {수(_소크압,4,' s')} — a factor of {수(_소크1/_소크압,4,'×')} in a cost that is paid
    on every part ever shipped. And at {수(100*_Y,4,' %')} yield, 99 % fault coverage
    ships
    {수(1e6*결함수준_닫힌꼴(_Y,0.99),4,' DPPM')} — which is the sentence that connects
    a DFT decision made before RTL freeze to a number in a customer's quality
    specification.""")

    c.글("""That closes the implementation arc. It began with a netlist and a set of
    constraints (T17), drew a box and a power grid (T18), placed, clocked and routed
    what was inside it (T19), established that the geometry may be manufactured (T20),
    established that the design was right in the first place (T21), and ended with the
    only question that is asked of every individual part ever shipped: does this one
    work? Every stage was governed by a computed quantity rather than a convention, and
    in every stage the quantity that mattered was the one that could not be seen from
    inside that stage alone.""")

    return c.완성()
