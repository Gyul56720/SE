"""**보고서.** 받아서 · 재고 · 검사하고 · 적는다. 못 받치면 **수를 안 적는다.**

    python3 brief/report.py --출처목록                   # 무엇이 등록돼 있나 (호출 0회)
    python3 brief/report.py 주식 --것 코스피,나스닥,다우
    python3 brief/report.py 주식 --원장 brief/ledger/주식.json   # 받지 않고 그것으로

    # **등록 안 된 것도 그 자리에서.** 티켓값이든 무엇이든
    python3 brief/report.py --탐색 --url '<주소>'        # 무엇이 오는지만 (저장 안 함)
    python3 brief/report.py --url '<주소>' --key 날짜

    끝값 0  보고서를 냈다     1  관문 hard 위반     3  미검증 -- 못 냈다

## 표에 없어도 된다 -- 그런데 규율은 안 풀린다

출처를 미리 등록해 두는 것 자체가 하드코딩이다. 내가 예상한 도메인만 되기 때문이다.
그래서 `--url` 로 처음 보는 API 를 그 자리에서 붙인다. 그때 밖(사람이든 모델이든)이
정하는 것은 **어디를 볼 것인가**뿐이고, 수는 여전히 아무도 못 만든다:

    url 을 지어내면      fetch 가 실패한다        -> 미검증, 수 0개
    스키마를 지어내면    도착한 것과 안 맞는다     -> inspect 가 거절한다
    칸을 안 적으면       도착한 것에서 읽는다      -> 짐작이 아니라 관측이다
    값을 지어내면        **B004 가 다시 세서 잡는다**

`law/METHOD.md` 의 분업 그대로다 -- LLM 은 조문에서 요건을 뽑고(대조 가능한 일),
쟁점은 코드가 도출한다. 여기서 **출처 제안이 그 '요건 뽑기' 자리**다.

## 왜 '나열' 이 아닌가

물음이 "오늘 주식 시장 보고해줘" 일 때 값을 그대로 늘어놓으면, 읽는 사람은 그 수들이
검사를 받았는지 알 수 없다. 여기서 나가는 보고서는 **세 층**으로 되어 있다.

    원장    무엇을 언제 어디서 받았나          <- 되짚을 수 있는 자리
    셈      그 줄에서 코드가 센 것              <- 규칙 이름과 식이 같이 적힌다
    관문    그 수가 원장에서 왔는가             <- **다시 세서 대조한 결과**

셋째가 `law/` 에서 가져온 것이다. 법이론서가 "인용한 조문이 실재하는가" 를 통과해야
나가듯, 여기 수는 B001~B004 를 통과해야 나간다. **hard 위반이 있으면 그 수를
화면에 안 적는다** -- 검사에 걸린 수를 보여 주면서 "다만 검사에 걸렸습니다" 라고
덧붙이면, 읽는 사람은 수를 먼저 읽고 단서를 나중에 읽는다.

## 해석은 하지 않는다

"왜 올랐는가" 는 이 파이프라인의 관할이 아니다(`law/METHOD.md` 1-7 의 외적 정당화).
여기서 나가는 것은 **센 것과 그 셈의 출처**뿐이고, 원인을 붙이면 그 순간 근거 없는
단정이 된다 -- B005 가 그것을 잡는다.
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brief import derive as DV                                     # noqa: E402
from brief import gate as GT
from brief import infer as INF                                       # noqa: E402
from brief import ledger as LG                                     # noqa: E402
from brief import source as SRC                                    # noqa: E402


def 폭(s: str) -> int:
    """화면에서 차지하는 칸 수. 한글·한자·가나는 두 칸이다.

    `len()` 으로 맞추면 한글 표가 통째로 어긋난다 -- 이 저장소의 출력은 대부분
    한국어라 그냥 깨진 표가 된다. 읽으라고 내는 표가 안 읽히면 안 낸 것과 같다.
    """
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def 채움(s: str, n: int, 오른쪽: bool = False) -> str:
    """폭 `n` 에 맞춰 채운다. 넘치면 자른다 -- 자르는 편이 표가 밀리는 것보다 낫다."""
    s = str(s)
    while 폭(s) > n:
        s = s[:-1]
    pad = " " * max(0, n - 폭(s))
    return (pad + s) if 오른쪽 else (s + pad)


def 수칸들(led) -> list:
    """원장에서 수인 칸. **id 는 뺀다** -- 그것은 가리키는 이름이지 재는 값이 아니다."""
    cols, seen = [], set()
    for r in led.줄:
        for k, v in r.items():
            if k != "id" and isinstance(v, (int, float)) and k not in seen:
                seen.add(k)
                cols.append(k)
    return cols


def build(src, led) -> list:
    """원장 -> 수.

    **출처가 셈을 적어 뒀으면 그것을, 아니면 칸마다 요약을 낸다.** 뒤쪽이 처음 보는
    출처에서 도는 길이다 -- 칸이 수이기만 하면 개수·최소·중앙·평균·최대·표준편차는
    무엇에든 뜻이 있다. 티켓값이든 기온이든.
    """
    facts = []
    if src.셈:
        for r in led.줄:
            facts += DV.raw_facts(led, r["id"], ("Close",), src.단위)
            facts += DV.row_facts(led, r["id"], src.셈, src.단위)
        return facts
    for c in 수칸들(led):
        facts += DV.col_facts(led, c, 단위=src.단위)
    return facts


def render_infer(ms, vs) -> list:
    """**따져 본 것** -- 나열 위에 얹히는 층. 명제 · 기준선 · 판정.

    여기 없는 것이 요점이다: 원인도 전망도 없다. 있는 것은 "이 움직임이 이 원장의
    기준선 아래서 놀라운가" 하나뿐이고, 대개 답은 **아니거나 모르겠다**이다.
    """
    if not ms:
        return ["## 따져 본 것", "",
                "  **명제를 하나도 못 세웠다.** 걸음이 모자란다 -- 추론에는 시계열이"
                " 있어야 한다.", "",
                "  오늘 값 몇 개로는 '평소와 다른가' 를 물을 수 없다. 견줄 평소가"
                " 원장에 없기 때문이다.", ""]
    s = INF.요약(ms)
    out = ["## 따져 본 것", ""]
    out.append(f"  명제 {s['세운수']}개 · 이례 {s['이례']} · 평범 {s['평범']} · "
               f"**못잼 {s['못잼']}**   (Holm 보정, 문턱 {INF.ALPHA})")
    out.append("")
    for m in sorted(ms, key=lambda x: (x.판정 != "이례", x.p보정 if x.p보정 is not None else 1)):
        표 = {"이례": "**이례**", "평범": "평범", "못잼": "**못잼**"}[m.판정]
        out.append(f"  [{표}] {m.말}")
        out.append(f"        기준선: {m.기준}")
        if m.p is not None:
            out.append(f"        p {m.p:.3f} -> 보정 {m.p보정:.3f}"
                       + (f" · 분위 {m.분위:.0%}" if m.분위 is not None else "")
                       + f" · 표본 {m.n}")
        if m.판정 == "못잼":
            out.append(f"        표본 {m.n}걸음 · 명제 {s['세운수']}개로 도달 가능한 최소 p 는 "
                       f"{min(1.0, s['세운수'] * INF.최소p(m.n, m.이진)):.3f} "
                       f"-- 문턱을 못 넘는다")
        if m.뒤집기:
            out.append(f"        뒤집기: {m.뒤집기}")
        out.append("")
    if s["필요표본"]:
        out.append(f"  **이 원장 크기로는 어느 명제도 가를 수 없다.** 명제 "
                   f"{s['세운수']}개를 이 문턱에서 가르려면 걸음이 최소 "
                   f"{s['필요표본']}개는 있어야 한다.")
        out.append("")
    out.append("  이 층이 하는 말은 하나다 -- **이 움직임이 이 원장의 기준선 아래서")
    out.append("  놀라운가.** 왜 그런지도, 앞으로 어떻게 될지도 여기서는 말하지 않는다.")
    out.append("")
    return out


def render_generic(src, led, facts, vs, 추론절=()) -> str:
    """셈이 안 적힌 출처의 보고서 -- 칸마다 요약 + 따져 본 것."""
    bad = GT.막힌것(vs, facts)
    cols = 수칸들(led)
    out = [f"# {src.이름} 보고 -- {src.설명}", ""]
    out.append(f"원장  받은날 {led.받은날 or '?'} · 줄 {len(led)}개"
               + (f" · 버린 줄 {led.버린것}개" if led.버린것 else "")
               + (f" · 나이 {led.나이()}일" if led.나이() is not None else ""))
    out.append(f"질의  {led.질의[:110]}")
    out.append("")
    if GT.hard(vs):
        out.append("**관문 hard 위반이 있어 아래에서 해당 수를 뺐다.**")
        out.append("")
    out.append("## 칸마다")
    out.append("")
    names = list(DV.기본요약)
    cw = max([폭(c) for c in cols] + [4]) + 2
    head = 채움("칸", cw) + "".join(채움(n, 13, True) for n in names)
    out.append(head)
    out.append("-" * 폭(head))
    by = {f.이름: f for f in facts}
    for c in cols:
        cells = []
        for n in names:
            f = by.get(f"{c}.{n}")
            cells.append(채움(f"{f.값:,.2f}" if f and f.이름 not in bad else "--", 13, True))
        out.append(채움(c, cw) + "".join(cells))
    out.append("")
    out.append("  셈: " + " · ".join(f"{n} = {DV.ACROSS[n][1]}" for n in names))
    out.append("  `--` 는 못 셌거나 관문에 걸린 자리다. 0 이 아니다.")
    out.append("")
    if len(led) <= 25:
        out.append("## 줄마다")
        out.append("")
        iw = max([폭(str(r["id"])) for r in led.줄] + [4]) + 2
        h = 채움("id", iw) + "".join(채움(c, 15, True) for c in cols)
        out.append(h)
        out.append("-" * 폭(h))
        for r in led.줄:
            out.append(채움(r["id"], iw) + "".join(
                채움(f"{r.get(c):,.2f}" if isinstance(r.get(c), (int, float)) else "--",
                     15, True) for c in cols))
        out.append("")
    else:
        out.append(f"  (줄이 {len(led)}개라 낱낱이 안 적는다. "
                   f"원장 파일에 다 있다)")
        out.append("")
    out += 추론절
    out.append("## 관문")
    out.append("")
    out.append("  " + GT.report(vs).replace("\n", "\n  "))
    out.append("")
    out.append("## 이 보고서가 안 보는 것")
    out.append("")
    out.append("  · **칸의 뜻** -- 이름이 무엇을 가리키는지는 출처가 정하지 여기서 모른다")
    out.append("  · 왜 그런 값인가 -- 원인은 이 원장으로 판정되지 않는다")
    out.append("  · 여기 없는 줄 -- 물은 것만 받았다")
    return "\n".join(out)


def render(src, led, facts, vs, 추론절=()) -> str:
    """보고서. **hard 에 걸린 수는 여기서 빠진다.**"""
    bad = GT.막힌것(vs, facts)
    out = []
    out.append(f"# {src.이름} 보고 -- {src.설명}")
    out.append("")
    out.append(f"원장  받은날 {led.받은날 or '?'} · 줄 {len(led)}개"
               + (f" · 버린 줄 {led.버린것}개" if led.버린것 else "")
               + (f" · 나이 {led.나이()}일" if led.나이() is not None else ""))
    out.append(f"질의  {led.질의[:110]}")
    out.append("")

    if GT.hard(vs):
        out.append("**관문 hard 위반이 있어 아래에서 해당 수를 뺐다.**")
        out.append("")

    # ── 줄마다 ────────────────────────────────────────────────────
    out.append("## 잰 것")
    out.append("")
    names = list(src.셈)
    dw = max([폭(str(r["id"])) for r in led.줄] + [4]) + 2
    head = 채움("대상", dw) + 채움("종가", 13, True) + "".join(채움(n, 13, True) for n in names)
    out.append(head)
    out.append("-" * 폭(head))
    for r in led.줄:
        rid = r["id"]
        mine = {f.이름: f for f in facts
                if (f.인자 and f.인자[0] == rid) or (f.근거 and f.근거[0][0] == rid)}
        cells = []
        close = mine.get("Close")
        cells.append(채움(f"{close.값:,.2f}" if close and "Close" not in bad else "--",
                          13, True))
        for n in names:
            f = mine.get(n)
            cells.append(채움(f"{f.값:,.2f}" if f and n not in bad else "--", 13, True))
        out.append(채움(rid, dw) + "".join(cells))
    out.append("")
    out.append("  셈: " + " · ".join(
        f"{n} = {DV.RULES[n][3]}" for n in names if n in DV.RULES))
    out.append("  `--` 는 못 셌거나 관문에 걸린 자리다. 0 이 아니다.")
    out.append("")

    # ── 여러 줄에 걸친 것 ─────────────────────────────────────────
    key = names[0] if names else ""
    if key and key not in bad:
        up, down, flat = DV.한방향인가(facts, key)
        rank = DV.순위(facts, key)
        spread = DV.흩어짐(facts, key)
        out.append("## 가로질러 본 것")
        out.append("")
        out.append(f"  {key}  오른 것 {up} · 내린 것 {down} · 그대로 {flat}"
                   f"   (대상 {up + down + flat}개)")
        if rank:
            out.append(f"  가장 큼   {rank[0][0]} {rank[0][1]:+.2f}")
            out.append(f"  가장 작음 {rank[-1][0]} {rank[-1][1]:+.2f}")
        if spread:
            out.append(f"  흩어짐    {spread.값:.2f} (표본표준편차, n={len(rank)})")
            out.append("  흩어짐이 크면 대상들이 **같이 움직이지 않았다**는 뜻이다. "
                       "왜 그런지는 여기서 말하지 않는다.")
        out.append("")

    # ── 관문 ──────────────────────────────────────────────────────
    out += 추론절
    out.append("## 관문")
    out.append("")
    out.append("  " + GT.report(vs).replace("\n", "\n  "))
    out.append("")
    out.append("## 이 보고서가 안 보는 것")
    out.append("")
    out.append("  · 왜 그렇게 움직였는가 -- 원인은 이 원장으로 판정되지 않는다")
    out.append("  · 앞으로 어떻게 되는가 -- 예측 모델이 아니다")
    out.append(f"  · 여기 없는 대상 -- 물은 것만 받았다 ({len(led)}개)")
    return "\n".join(out)


def 내놓기(src, led, 따질=()) -> int:
    """재고 · 따지고 · 검사하고 · 적는다. **세 층이 한 자리를 지난다.**

    나열(칸마다)과 추론(따져 본 것)이 같은 관문을 지나야 한다 -- 한쪽만 검사받으면
    검사 안 받은 쪽으로 주장이 몰린다.
    """
    facts = build(src, led)
    # **좁혀 물으면 가를 힘이 세진다.** 명제를 m 개 세우면 Holm 이 m 배로 조이므로,
    # 칸 다섯을 다 물으면 명제가 16개가 되어 1년치로도 아무것도 못 가른다.
    # 하나만 물으면 같은 원장에서 갈린다 -- 미리 정해 묻는 것이 훑는 것보다 강하다.
    claims = INF.따져보기(led, 따질 or None)
    vs = GT.check(facts, led, src, claims=claims)
    절 = render_infer(claims, vs)
    print(render(src, led, facts, vs, 절) if src.셈
          else render_generic(src, led, facts, vs, 절))
    return 1 if GT.hard(vs) else 0


def probe(src) -> int:
    """**무엇이 오는지만 본다.** 저장도 보고도 안 한다 -- 원장을 더럽힐 수 없다.

    처음 보는 출처를 붙일 때 첫 걸음이다. 스키마를 짐작해서 적어 넣고 틀리면 그
    틀린 스키마가 원장에 박히는데, 여기서 한 번 보면 **적어 넣을 것이 관측이 된다.**
    `lol/fetch.py --진단` · `mathdrift --check` 와 같은 자리다.
    """
    try:
        body = LG.get(src.url)
    except Exception as e:                                    # noqa: BLE001
        print(f"**못 받았다** -- {type(e).__name__}: {str(e)[:150]}")
        print(f"  url: {src.url[:110]}")
        print("  받은 것이 없으므로 무엇이 오는지도 말할 수 없다.")
        return 3
    rows = LG.parse(src, body)
    if not rows:
        print(f"받기는 했는데 **줄을 못 찾았다** ({len(body)}바이트, 꼴={src.꼴}).")
        print("  받은 것 앞머리:")
        print("    " + body[:300].replace("\n", "\n    "))
        print("  --꼴 이나 --경로 를 줘서 어디를 보라고 알려 줘라. "
              "짐작으로 채우지 않는다.")
        return 3
    본 = LG.살펴보기(rows)
    v = LG.inspect(src, rows)
    print(f"줄 {본['줄수']}개 · 칸 {len(본['칸'])}개  (꼴={src.꼴})")
    print()
    print(f"  칸        {', '.join(본['칸'][:14])}"
          + (" ..." if len(본["칸"]) > 14 else ""))
    print(f"  **수인 칸** {', '.join(본['수칸']) or '(없다 -- 셀 것이 없다)'}")
    print(f"  key 후보  {', '.join(본['key후보'][:6]) or '(없다 -- 자리번호로 가리킨다)'}")
    print()
    print("  첫 줄:")
    for r in rows[:2]:
        print(f"    {dict(list(r.items())[:8])}")
    print()
    if v["통과"]:
        쓴 = v.get("쓴것", {})
        print(f"  이대로 저장할 수 있다 (쓸 줄 {len(v['good'])}개 · "
              f"버릴 줄 {v['버린것']}개 · key={쓴.get('key') or '자리번호'})")
        print("  **--탐색 을 떼면** 받아서 재고 관문까지 돌린다.")
    else:
        print(f"  **이대로는 저장 안 된다**: {'; '.join(v['왜'])}")
        print("  --key 나 --수칸 으로 무엇을 쓸지 정해 주면 된다.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="원장 -> 셈 -> 관문 -> 보고서")
    ap.add_argument("출처", nargs="?", default="")
    ap.add_argument("--것", dest="items", default="",
                    help="쉼표로 (예: 코스피,나스닥,다우)")
    ap.add_argument("--원장", dest="from_ledger", default="",
                    help="받지 않고 저장된 원장으로 (호출 0회)")
    ap.add_argument("--저장", dest="save", default="")
    ap.add_argument("--진단", dest="diag", action="store_true",
                    help="받되 보고서는 안 낸다 -- 무엇이 왔는지만 본다")
    ap.add_argument("--출처목록", dest="list_src", action="store_true")
    # ── 즉석 출처. **등록 없이 그 자리에서** ───────────────────────────
    ap.add_argument("--url", default="", help="처음 보는 API 를 그 자리에서 붙인다")
    ap.add_argument("--탐색", dest="probe", action="store_true",
                    help="url 을 받아 **무엇이 오는지만** 본다 (저장도 보고도 안 한다)")
    ap.add_argument("--꼴", dest="fmt", default="", choices=["", "csv", "json"])
    ap.add_argument("--경로", dest="path", default="", help="json 에서 줄이 있는 자리")
    ap.add_argument("--key", default="", help="줄을 가리킬 칸")
    ap.add_argument("--칸", dest="cols", default="", help="쉼표로. 비우면 도착한 것에서 읽는다")
    ap.add_argument("--수칸", dest="ncols", default="", help="쉼표로. 비우면 스스로 가린다")
    ap.add_argument("--따질", dest="ask_cols", default="",
                    help="추론에서 **이 칸만** 묻는다 (쉼표). 좁힐수록 가를 힘이 세진다")
    ap.add_argument("--시계열", dest="series", default="",
                    help="쉼표로. 일별 내력을 받아 날짜로 맞춘다 -- **추론은 이것이 있어야 한다**")
    a = ap.parse_args(argv)
    따질 = tuple(c.strip() for c in a.ask_cols.split(",") if c.strip())

    # ── 시계열: 추론이 설 수 있는 유일한 자리 ──────────────────────
    if a.series:
        src = SRC.get("시계열")
        조각, 못받은 = [], []
        for 이름 in [x.strip() for x in a.series.split(",") if x.strip()]:
            sym = SRC.심볼(src, [이름])[0]
            one, err = LG.fetch(src, 심볼=sym)
            (못받은.append(f"{이름}({sym}): {err}") if err
             else 조각.append((이름, one, "Close")))
        if not 조각:
            print("**미검증** -- 하나도 못 받아 보고서를 낼 수 없다.")
            for w in 못받은:
                print(f"  {w}")
            print("  받은 것이 없으므로 **수를 하나도 적지 않는다.**")
            return 3
        if 못받은:
            print(f"(못 받은 것 {len(못받은)}개는 빼고 간다: "
                  f"{', '.join(w.split(':')[0] for w in 못받은)})")
        led = LG.합치기(조각)
        if a.save:
            LG.save(led, Path(a.save))
            print(f"원장 저장: {a.save}  ({len(led)}줄)")
        return 내놓기(src, led, 따질)

    # ── 즉석 출처 ─────────────────────────────────────────────────
    if a.url:
        src = SRC.즉석(a.url, 꼴=a.fmt, 경로=a.path, key=a.key,
                       칸=[c for c in a.cols.split(",") if c.strip()],
                       수칸=[c for c in a.ncols.split(",") if c.strip()],
                       이름=a.출처 or "즉석")
        if a.probe:
            return probe(src)
        led, err = LG.fetch(src)
        if err:
            print("**미검증** -- 받지 못해 보고서를 낼 수 없다.")
            print(f"  url: {a.url[:110]}")
            print(f"  까닭: {err}")
            print("  받은 것이 없으므로 **수를 하나도 적지 않는다.** "
                  "url 이 틀렸으면 --탐색 으로 무엇이 오는지부터 보라.")
            return 3
        if a.save:
            LG.save(led, Path(a.save))
            print(f"원장 저장: {a.save}  ({len(led)}줄)")
        return 내놓기(src, led, 따질)

    if a.list_src or not a.출처:
        미확인 = [s for s in SRC.SOURCES.values() if s.미확인]
        print("등록된 출처:")
        for s in SRC.SOURCES.values():
            ok, why = s.쓸수있나()
            표 = "**[미확인]**" if s.미확인 else f"[확인 {s.확인}]"
            print(f"  {s.이름:<6} {표} {s.설명}")
            print(f"         셈: {', '.join(s.셈) or '(없음 -- 칸마다 요약)'} · "
                  f"신선도 {s.신선}일" + ("" if ok else f"  **{why}**"))
            if s.별칭:
                print(f"         부를 수 있는 이름: {', '.join(list(s.별칭)[:10])}")
        if 미확인:
            print()
            print(f"  **미확인 {len(미확인)}개 -- 도는 것을 아무도 안 봤다.** 표에 있다는")
            print("  것만으로 쓸 수 있어 보이지만 아니다(실측 2026-09-09: Stooq 세 줄이")
            print("  전부 404 였다). 쓰기 전에 먼저:")
            print(f"    python3 brief/report.py {미확인[0].이름} --것 <것> --탐색")
        print()
        print("  **표에 없어도 된다.** 처음 보는 API 는 그 자리에서 붙인다:")
        print("    python3 brief/report.py --탐색 --url '<주소>'   # 무엇이 오는지만")
        print("    python3 brief/report.py --url '<주소>' --key <칸>")
        print("  자주 쓸 것만 brief/source.py 에 등록해 별칭과 셈을 붙인다.")
        print("  가져오기·검사·셈·관문은 어느 길로 오든 한 벌이다.")
        return 0 if a.list_src else 3

    src = SRC.get(a.출처)
    if src is None:
        print(f"**미검증** -- 그런 출처가 없다: {a.출처!r}")
        print(f"  있는 것: {', '.join(SRC.SOURCES)}")
        print("  비슷한 것을 골라 주지 않는다 -- 딴 것을 그 이름으로 보고하게 된다.")
        return 3

    # ── 원장 ──────────────────────────────────────────────────────
    if a.from_ledger:
        led = LG.load(Path(a.from_ledger))
        if led is None:
            print(f"**미검증** -- 원장을 못 읽었다: {a.from_ledger}")
            print("  머리글(출처·받은날)이 없는 파일은 안 읽는다. "
                  "언제 것인지 모르는 원장은 못 쓴다.")
            return 3
    else:
        if not a.items:
            print(f"**미검증** -- 무엇을 받을지 안 정해졌다. --것 으로 대상을 적어라.")
            print(f"  예: python3 brief/report.py {src.이름} --것 "
                  f"{','.join(list(src.별칭)[:3])}")
            return 3
        syms = SRC.심볼(src, a.items.split(","))
        led, err = LG.fetch(src, 심볼=",".join(syms))
        if err:
            print(f"**미검증** -- 받지 못해 보고서를 낼 수 없다.")
            print(f"  출처: {src.이름} ({src.설명})")
            print(f"  까닭: {err}")
            if src.미확인:
                print("  **이 출처는 도는 것을 아무도 안 봤다**(확인 칸이 비어 있다). "
                      "주소가 틀렸을 수 있다 --")
                print("  고치려 하기 전에 `--url` 로 다른 출처를 붙이는 편이 빠를 때가 많다:")
                print("    python3 brief/report.py --탐색 --url '<되는 주소>'")
            print("  받은 것이 없으므로 **수를 하나도 적지 않는다.** "
                  "기억에서 채우면 그것은 보고가 아니라 창작이다.")
            return 3
        if a.save:
            LG.save(led, Path(a.save))
            print(f"원장 저장: {a.save}  ({len(led)}줄)")

    if a.diag:
        print(f"받은 줄 {len(led)}개 · 버린 줄 {led.버린것}개 · 받은날 {led.받은날}")
        for r in led.줄[:5]:
            print(f"    {r}")
        print("**--진단 이므로 보고서는 안 낸다.**")
        return 0

    return 내놓기(src, led, 따질)


if __name__ == "__main__":
    raise SystemExit(main())
