# -*- coding: utf-8 -*-
"""Volume III, Part Z5 -- Choosing the first product, concretely."""
import sys, os, math
sys.path.insert(0, "/home/user/SE/edu")
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num


# 후보를 재는 잣대와 가중치.  가중치는 **1인 하우스** 기준이다 -- 큰 회사면 다르다.
잣대 = [
    ("규격을 구할 수 있나", 3, "못 구하면 못 만든다. 끝"),
    ("독립 골든모델이 있나", 3, "혼자 검증하는 유일한 길"),
    ("소프트 IP 인가", 3, "하드 매크로는 아날로그와 공정 접근이 필요하다"),
    ("표준이 바뀌는 중인가", 2, "기존 공급자의 블록이 낡는다 -- 들어갈 틈"),
    ("공급자가 적은가", 2, "많으면 가격으로 진다"),
    ("가족으로 번지나", 2, "둘째 셋째가 싸진다"),
    ("이름 댈 고객이 있나", 3, "없으면 투기다"),
    ("검증이 기계화되나", 2, "에이전트가 밤새 할 수 있나"),
]

후보 = [
    ("RS-FEC (KP4) 복호기",
     {"규격을 구할 수 있나": 1, "독립 골든모델이 있나": 3, "소프트 IP 인가": 3,
      "표준이 바뀌는 중인가": 3, "공급자가 적은가": 2, "가족으로 번지나": 3,
      "이름 댈 고객이 있나": 0, "검증이 기계화되나": 3},
     "규격 조문(Clause 91)을 아직 못 봤다 -- 그것이 1번 걸림돌"),
    ("AES-GCM 엔진",
     {"규격을 구할 수 있나": 3, "독립 골든모델이 있나": 3, "소프트 IP 인가": 3,
      "표준이 바뀌는 중인가": 0, "공급자가 적은가": 0, "가족으로 번지나": 2,
      "이름 댈 고객이 있나": 0, "검증이 기계화되나": 3},
     "규격도 시험벡터도 공짜인데 **공급자가 너무 많다**"),
    ("ML-KEM (Kyber) NTT 코어",
     {"규격을 구할 수 있나": 3, "독립 골든모델이 있나": 3, "소프트 IP 인가": 3,
      "표준이 바뀌는 중인가": 3, "공급자가 적은가": 3, "가족으로 번지나": 2,
      "이름 댈 고객이 있나": 0, "검증이 기계화되나": 3},
     "규격 공개, 참조 구현 공개, 표준이 막 확정, 공급자 적음"),
    ("MIPI CSI-2 수신기",
     {"규격을 구할 수 있나": 1, "독립 골든모델이 있나": 1, "소프트 IP 인가": 2,
      "표준이 바뀌는 중인가": 1, "공급자가 적은가": 1, "가족으로 번지나": 2,
      "이름 댈 고객이 있나": 0, "검증이 기계화되나": 2},
     "규격이 유료 회원제, PHY 가 하드 매크로 -- 1인에게 무겁다"),
    ("이더넷 PCS (802.3dj 내부코드)",
     {"규격을 구할 수 있나": 1, "독립 골든모델이 있나": 2, "소프트 IP 인가": 3,
      "표준이 바뀌는 중인가": 3, "공급자가 적은가": 3, "가족으로 번지나": 3,
      "이름 댈 고객이 있나": 0, "검증이 기계화되나": 3},
     "소프트·바뀌는 중·공급자 적음. 규격 조문이 다시 걸림돌"),
]


def ch_first():
    s = ['<h1 id="z5">Z5. Choosing the First Product, Concretely</h1>']
    s.append("""<p>Part&nbsp;Y8 gives the criteria. This part applies them to real
    candidates with weights chosen for a one-person house, and arrives at a
    recommendation &mdash; including the one column that is currently zero for every
    candidate, which is the honest headline.</p>""")

    s.append("<h2>Z5.1 The scorecard</h2>")
    rows = [[f"<b>{n}</b>", num(w), why] for n, w, why in 잣대]
    s.append(sweep("Criteria and weights for a one-person house",
        ["Criterion", "Weight", "Why this weight"], rows,
        "<b>Weight 3 means a zero here kills the candidate</b> regardless of the rest. "
        "A larger company would weight &lsquo;specification obtainable&rsquo; at 1, "
        "because a membership is a rounding error in its budget; for one person it is a "
        "gate."))
    머리 = ["Candidate"] + [n.split()[0] + "…" for n, _, _ in 잣대] + \
           ["<b>Total</b>", "Note"]
    rows = []
    for 이름, 점수들, 말 in 후보:
        총 = sum(점수들[k] * w for k, w, _ in 잣대)
        rows.append([f"<b>{이름}</b>"] + [num(점수들[k]) for k, _, _ in 잣대] +
                    [f"<b>{총}</b>", 말])
    최대 = sum(3 * w for _, w, _ in 잣대)
    s.append(sweep(f"Scored 0&ndash;3 per criterion, weighted; maximum possible {최대}",
        머리, rows,
        "<b>Scores are judgements, and stating them as numbers is what makes them "
        "arguable.</b> A reader who disagrees can change one cell and see whether the "
        "ranking moves &mdash; which is the point of a scorecard and the reason it beats "
        "a paragraph of reasoning."))
    최고 = max(후보, key=lambda c: sum(c[1][k] * w for k, w, _ in 잣대))
    s.append(f"""<div class="ms"><b>On these weights the winner is
    {E(최고[0])}</b>, and the reason is worth reading off the table rather than taking on
    trust: it is the only candidate that scores 3 on <i>all four</i> of specification
    availability, independent golden model, soft RTL, and a changing standard with few
    suppliers. The post-quantum transition put a new, fully public, algorithmically
    demanding block into a market whose incumbents built their portfolios around RSA and
    ECC. <b>And Part&nbsp;X6's entire FFT analysis transfers to the NTT</b> &mdash; same
    radix choices, same twiddle symmetries, same memory-versus-multiplier trade, with
    modular arithmetic replacing complex arithmetic. A team that has built an FFT has most
    of it.</div>""")
    s.append("""<div class="warn"><b>Every candidate scores zero on &lsquo;a customer you
    can name&rsquo;, and that is the real finding.</b> The scorecard ranks technical and
    market fit; it cannot manufacture demand. Six good rows and a zero in that column
    describes a project, not a business. <b>The action the table implies is not to start
    building the winner &mdash; it is to spend the next two weeks turning that column
    into a non-zero</b>, by talking to people who buy this kind of block, and to let what
    they say re-score the other rows. A candidate that scores 40 with a named customer
    beats one that scores 48 without.</div>""")

    s.append("<h2>Z5.2 Sizing the winner before committing</h2>")
    s.append(ex("What an NTT core costs to build, estimated from the structure",
        "ML-KEM uses a 256-point NTT over the prime <i>q</i>&nbsp;=&nbsp;3329, so "
        "coefficients are 12 bits and the modulus is small. Compare against the FFT "
        "arithmetic of Part&nbsp;X6.",
        "Count butterflies, multipliers and memory the same way Part&nbsp;X6 does, then "
        "convert to weeks with Part&nbsp;Y8's plan.",
        [("Transform size", num(256)),
         ("Stages (radix 2)", num(int(math.log2(256)))),
         ("Butterflies per transform", num(256 // 2 * int(math.log2(256)))),
         ("Coefficient width", num(12) + " bits"),
         ("Modular multiplier (12&times;12 then reduce)",
          "<b>small &mdash; a few hundred gates</b>"),
         ("Coefficient memory", num(256 * 12 / 8, 4) + "&nbsp;bytes"),
         ("Twiddle ROM (128 entries)", num(128 * 12 / 8, 4) + "&nbsp;bytes"),
         ("<b>Compared with a 4096-point complex FFT</b>",
          "<b>two orders of magnitude smaller</b>"),
         ("Plausible effort from Part&nbsp;Y8's plan",
          "<b>half of the 39 weeks &mdash; the block is small, the verification is "
          "not</b>")],
        "<b>By sizing the arithmetic and forgetting that the verification does not "
        "shrink with the datapath.</b> The core is small; the golden model, the "
        "known-answer vectors from the standard, the constant-time argument "
        "(Part&nbsp;X36), the register map, the documentation and the release gate are "
        "the same work they would be for a block ten times larger. <b>That asymmetry is "
        "good news for a first product</b> &mdash; it means a small block can carry a "
        "full-quality wrapper, which is exactly what a first product needs to "
        "demonstrate."))

    s.append("<h2>Z5.3 The two weeks before you write any RTL</h2>")
    rows = [
        ["Day 1&ndash;2", "Prior-art note (Part&nbsp;Y6): closest work, how we differ, "
         "queries run, **where we have not looked**",
         "Committed before any code &mdash; the repository's own rule"],
        ["Day 3&ndash;5", "Read the standard; write down every ambiguity",
         "The ambiguity list is your first deliverable and your first sales document"],
        ["Day 6&ndash;8", "<b>Golden model in Python, checked against the standard's "
         "known-answer vectors</b>",
         "<b>If the vectors do not match, you have misread the standard &mdash; find "
         "out now, not in month four</b>"],
        ["Day 9&ndash;10", "Architecture study: word lengths, parallelism, memory "
         "(Parts&nbsp;X1, X6)",
         "Produces the area and throughput numbers you will quote"],
        ["Day 11&ndash;12", "<b>Talk to three potential customers</b> with the "
         "ambiguity list and the architecture study",
         "<b>This is the step that turns the zero column into a number</b>"],
        ["Day 13&ndash;14", "Re-score the candidates with what they said",
         "The scorecard was a guess until this point"],
    ]
    s.append(sweep("Two weeks, and what each part produces",
        ["When", "What", "Why it is in this order"], rows,
        "<b>No RTL in fourteen days, and that is deliberate.</b> Every item above "
        "changes what the RTL should be, and each is cheap to redo and expensive to "
        "redo after the RTL exists."))
    s.append(prob("You cannot get three customer conversations. Now what?",
        "Treat that as data about the market rather than as an obstacle to route around. "
        "If nobody will spend twenty minutes discussing a block they might buy, the "
        "likeliest explanations are that the block is not a problem they have, that they "
        "already have a supplier they are satisfied with, or that you have not found the "
        "right people &mdash; and the third is the only one that is your mistake to fix. "
        "<b>Widen the search before widening the scope</b>: the people who answer are "
        "rarely procurement; they are engineers, and they are reachable through the "
        "standards body's working group, the open-source projects around the protocol, "
        "and conference and plugfest attendee lists. <b>A useful substitute when "
        "conversations genuinely cannot be had is a public artefact that attracts "
        "them</b> &mdash; the golden model published with the standard's vectors, a note "
        "on an ambiguity you found in the specification, a comparison of the open "
        "implementations. Part&nbsp;Y6's argument for publishing applies exactly here: "
        "it is how a house nobody has heard of becomes findable. <b>What is not an "
        "answer is to start building and hope</b>, because the 39 weeks are spent either "
        "way and only one of the two ends with someone to sell to."))
    return "\n".join(s)
