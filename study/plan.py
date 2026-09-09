"""**교안 -- 확인된 약점만 모은다.** 일반론을 안 쓴다.

교안이 "확률을 열심히 하세요" 가 되면 아무 소용이 없다. 그런 말은 오답노트를 안 봐도
쓸 수 있고, 안 보고 쓴 것이라 학생 것이 아니다. 그래서 여기서는 **줄마다 근거를
붙인다** -- 이 태그를 왜 넣었는지, 어느 문제에서 그랬는지.

    약함  ->  교안에 넣는다. 근거 문제 id 를 함께
    못잼  ->  **넣지 않는다.** 대신 "몇 문제 더 풀면 갈린다" 를 적는다
    평범  ->  넣지 않는다. 넣으면 없는 약점을 가르치게 된다

`brief` 가 '평범' 을 '주목할 만하다' 로 못 바꾸게 한 것과 같은 자리다. 못 잰 것을
약점으로 올리면, 학생은 멀쩡한 데를 붙들고 정작 약한 데를 안 본다.
"""
from __future__ import annotations

from study import note as NT
from study import weak as WK


def 오답노트(n: NT.공책, 태그: str = "") -> str:
    """틀린 것만. **문제·낸 답·정답·해설·그때 쓴 메모를 다 붙인다.**

    줄이지 않는다 -- 오답노트에서 줄인 것은 다시 못 본다.
    """
    틀림 = n.틀린것()
    if 태그:
        틀림 = [a for a in 틀림 if 태그 in (n.문제.get(a.문제id).태그
                                          if n.문제.get(a.문제id) else [])]
    if not 틀림:
        푼 = len([a for a in n.시도 if a.맞았나 is not None])
        return (f"# 오답노트\n\n틀린 것이 없다 (채점된 시도 {푼}개)."
                + ("" if 푼 else "\n**아직 채점된 것이 없다** -- "
                                 "`--답 <문제id> '<답>'` 으로 풀고 나서 보라."))
    out = [f"# 오답노트 ({len(틀림)}문제)"]
    for i, a in enumerate(틀림, 1):
        q = n.문제.get(a.문제id)
        if not q:
            continue
        out.append("")
        out.append(f"## {i}. [{q.id}] {' · '.join(q.태그) or '(태그없음)'}")
        out.append(f"  문제:   {q.말}")
        if q.보기:
            out.append(f"  보기:   {' | '.join(q.보기)}")
        out.append(f"  낸 답:  {a.낸답}")
        out.append(f"  정답:   {q.정답}")
        if q.해설:
            out.append(f"  해설:   {q.해설}")
        if a.메모:
            out.append(f"  내 메모: {a.메모}")
        if a.짚은것:
            out.append(f"  짚은 것: {a.짚은것}")
        if q.출처:
            out.append(f"  출처:   {q.출처}")
        else:
            out.append("  출처:   **없음** -- 어디서 온 문제인지 모르면 "
                       "정답도 못 되짚는다")
    return "\n".join(out)


def 사유보고(n: NT.공책) -> str:
    """**구체적인 취약점.** 과목이 아니라 어긋난 자리."""
    사없 = n.사유없는것()
    것들 = WK.사유취약점(n)
    if not 것들:
        말 = ["# 취약점 (구체)", "", "아직 셀 것이 없다."]
        if 사없:
            말.append(f"틀린 것 {len(사없)}개에 **무엇이 어긋났는지가 안 적혔다** -- "
                     "적히지 않으면 셈에 안 들어간다:")
            말.append("  python3 study/run.py --사유프롬프트     # 모델에게 줄 것")
            말.append("  python3 study/run.py --사유 <문제id> '<무엇이 어긋났나>'")
        return "\n".join(말)

    W = 것들[0].n
    out = ["# 취약점 (구체) -- 과목이 아니라 **어긋난 자리**", "",
           f"틀린 것 {W}개 · 사유 {len(것들)}가지", ""]
    for w in 것들:
        p = "-" if w.p보정 is None else f"{w.p보정:.3f}"
        out.append(f"  [{w.판정}] {w.틀린}번 — {w.태그}")
        out.append(f"       문제: {', '.join(w.문제들[:12])} · 보정 p={p}")
    out.append("")
    from study import tag as TG
    닮 = TG.닮은쌍([w.태그 for w in 것들])
    if 닮:
        out.append("  **묶기엔 모자란데 닮은 것** -- 사람이 보고 같으면 "
                   "같은 말로 다시 적어라(그러면 되풀이로 세어진다):")
        for a, b, v in 닮[:6]:
            out.append(f"    {v:.2f}  {a}\n          ~  {b}")
        out.append("")
    out.append("  자: 틀린 것이 사유마다 **고르게 흩어졌다면** 한 사유에 "
               f"{W}/{len(것들)}번쯤이다. 그보다 잦으면 되풀이다. "
               "고르게 흩어졌다는 가정 위의 셈이다.")
    if 사없:
        out.append("")
        out.append(f"  사유가 안 적힌 것 {len(사없)}개는 **셈에 안 들어간다**: "
                   "`--사유프롬프트` 또는 `--사유 <문제id> '<무엇이>'`")
    return "\n".join(out)


def 취약점보고(n: NT.공책) -> str:
    전, 틀, p0 = WK.전체기저(n)
    것들 = WK.취약점(n)
    out = [f"# 취약점  (채점된 문제 {전}개 · 전체 오답률 {p0:.0%})", ""]
    if not 것들:
        return "\n".join(out + ["아직 센 것이 없다. 문제를 풀고 채점부터."])

    m = sum(1 for w in 것들 if w.p is not None) or 1
    약, 못 = [w for w in 것들 if w.판정 == "약함"], [w for w in 것들 if w.판정 == "못잼"]
    for w in 것들:
        out.append(f"  {w}")
        if w.문제들:
            out.append(f"       틀린 문제: {', '.join(w.문제들[:12])}")
        if w.판정 == "못잼":
            더 = WK.몇개더(w, p0, m=m)
            out.append("       **못 잰 것이지 잘하는 것이 아니다.** " +
                       (f"이 태그로 {더}문제쯤 더 풀면 갈린다"
                        if 더 > 0 else
                        ("지금 표본으로 이미 갈릴 수 있다(다른 까닭)" if 더 == 0
                         else "전체 오답률이 이대로면 아무리 풀어도 못 가른다")))
    out.append("")
    out.append(f"  세운 태그 {m}개 -- Holm 으로 문턱을 조였다. 안 조이면 "
               "여럿 훑는 것만으로 하나가 나빠 보인다.")
    if not 약:
        out.append("  **약하다고 말할 수 있는 태그가 없다.** " +
                   ("표본이 짧아서다(위의 '못잼')." if 못 else
                    "고르게 하고 있다는 뜻이다."))
    return "\n".join(out)


def 교안(n: NT.공책, 제목: str = "") -> str:
    """**확인된 약점만.** 근거·순서·다시 풀 문제까지."""
    전, 틀, p0 = WK.전체기저(n)
    것들 = WK.취약점(n)
    약 = [w for w in 것들 if w.판정 == "약함"]
    못 = [w for w in 것들 if w.판정 == "못잼"]

    out = [f"# 교안 -- {제목 or '오답노트에서 뽑은 것'}", "",
           f"바탕: 채점된 문제 {전}개 · 전체 오답률 {p0:.0%} · "
           f"태그 {len(것들)}개", ""]

    사약미리 = [w for w in WK.사유취약점(n) if w.판정 == "약함"]
    if not 약 and not 사약미리:
        out.append("## 아직 교안을 못 만든다")
        out.append("")
        out.append("**약하다고 말할 수 있는 태그가 하나도 없다.** 여기서 일반론"
                   "('개념을 다지세요')을 쓸 수는 있지만, 그것은 이 오답노트를 안 보고도"
                   " 쓸 수 있는 말이라 네 것이 아니다.")
        if 못:
            m = sum(1 for w in 것들 if w.p is not None) or 1
            out.append("")
            out.append("몇 문제를 더 풀면 갈리는지:")
            for w in 못[:10]:
                더 = WK.몇개더(w, p0, m=m)
                out.append(f"  · {w.태그}: 지금 {w.n}문제 -> " +
                           (f"**{더}문제쯤 더**" if 더 > 0 else "이미 갈릴 수 있다"
                            if 더 == 0 else "전체 오답률이 이대로면 못 가른다"))
        return "\n".join(out)

    사약 = [w for w in WK.사유취약점(n) if w.판정 == "약함"]
    if 사약:
        # **이것이 사용자가 요구한 구체성이다.** 태그(과목)는 그 다음이다.
        out.append("## 되풀이되는 어긋남 -- **여기부터 고친다**")
        out.append("")
        for i, w in enumerate(사약, 1):
            out.append(f"### {i}. {w.태그}")
            out.append(f"  {w.틀린}번 되풀이 (틀린 것 {w.n}개 중) · "
                       f"보정 p={w.p보정:.3f}")
            for qid in w.문제들:
                q, a = n.문제.get(qid), n.마지막(qid)
                if not q:
                    continue
                out.append(f"    [{qid}] {q.말[:70]}")
                out.append(f"          낸 답 {a.낸답 if a else '?'}  /  정답 {q.정답}")
            out.append("  다시 풀 것: " + ", ".join(w.문제들))
            out.append("")

    if not 약:
        out.append("## 과목 수준에서는 갈린 것이 없다")
        out.append("")
        out.append("태그(과목)로는 약하다고 말할 만한 것이 없다. 위의 어긋남이 "
                   "**더 좁고 더 쓸모 있는 자리**다.")
        out.append("")
        out.append("## 이 교안이 안 보는 것")
        out.append("")
        out.append("  · **왜** 그렇게 어긋나는가 -- 세는 것으로는 되풀이까지다")
        out.append("  · 사유가 옳게 붙었는가 -- 틀리면 이 셈이 통째로 어긋난다")
        return "\n".join(out)
    out.append("## 과목 수준에서 -- 어떤 차례로")
    out.append("")
    out.append("확실한 것부터 놓았다(보정 p 가 작은 순). **이 차례가 곧 근거의 세기다.**")
    for i, w in enumerate(약, 1):
        out.append("")
        out.append(f"### {i}. {w.태그}")
        out.append(f"  얼마나: {w.틀린}/{w.n} 틀림 ({w.오답률:.0%}) · "
                   f"전체 {w.기저:.0%} · 보정 p={w.p보정:.3f}")
        out.append(f"  왜 넣었나: 전체 오답률 {w.기저:.0%} 짜리 사람이 이 태그에서 "
                   f"{w.n}문제 중 {w.틀린}문제를 틀릴 확률이 {w.p보정:.1%} 다. "
                   "우연으로 보기 어렵다")
        out.append("  근거 문제:")
        for qid in w.문제들:
            q = n.문제.get(qid)
            a = n.마지막(qid)
            if not q:
                continue
            out.append(f"    [{qid}] {q.말[:80]}")
            out.append(f"          낸 답 {a.낸답 if a else '?'}  /  정답 {q.정답}")
            if a and a.짚은것:
                out.append(f"          짚은 것: {a.짚은것}")
            elif a and a.메모:
                out.append(f"          내 메모: {a.메모}")
        out.append("  다시 풀 것: " + (", ".join(w.문제들) or "-"))

    if 못:
        out.append("")
        out.append("## 여기 안 넣은 것 -- **못 잰 것이지 잘하는 것이 아니다**")
        out.append("")
        m = sum(1 for x in 것들 if x.p is not None) or 1
        for w in 못[:12]:
            더 = WK.몇개더(w, p0, m=m)
            out.append(f"  · {w.태그} ({w.틀린}/{w.n}) -- " +
                       (f"{더}문제쯤 더 풀면 갈린다" if 더 > 0
                        else "이미 갈릴 수 있다" if 더 == 0
                        else "전체 오답률이 이대로면 못 가른다"))

    out.append("")
    out.append("## 이 교안이 안 보는 것")
    out.append("")
    out.append("  · **왜** 틀렸는가 -- 세는 것으로는 태그까지다. 까닭은 오답노트의 "
               "'짚은 것' 에 사람이 적는다")
    out.append("  · 태그가 옳게 붙었는가 -- 태그가 틀리면 이 셈이 통째로 어긋난다")
    out.append("  · 이 문제들이 시험을 대표하는가 -- 오답노트는 푼 것만 담는다")
    return "\n".join(out)
