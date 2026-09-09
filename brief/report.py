"""**보고서.** 받아서 · 재고 · 검사하고 · 적는다. 못 받치면 **수를 안 적는다.**

    python3 brief/report.py --출처                       # 무엇을 쓸 수 있나 (호출 0회)
    python3 brief/report.py 주식 --것 코스피,나스닥,다우
    python3 brief/report.py 주식 --것 코스피 --저장 brief/ledger/주식.json
    python3 brief/report.py 주식 --원장 brief/ledger/주식.json   # 받지 않고 그것으로
    python3 brief/report.py 주식 --것 코스피 --진단      # 받되 **보고서는 안 낸다**

    끝값 0  보고서를 냈다     1  관문 hard 위반     3  미검증 -- 못 냈다

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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brief import derive as DV                                     # noqa: E402
from brief import gate as GT                                       # noqa: E402
from brief import ledger as LG                                     # noqa: E402
from brief import source as SRC                                    # noqa: E402


def build(src, led) -> list:
    """원장 -> 수. 줄마다 원장 값과 셈한 값을 함께."""
    facts = []
    for r in led.줄:
        facts += DV.raw_facts(led, r["id"], ("Close",), src.단위)
        facts += DV.row_facts(led, r["id"], src.셈, src.단위)
    return facts


def render(src, led, facts, vs) -> str:
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
    head = f"{'대상':<12}{'종가':>12}" + "".join(f"{n:>12}" for n in names)
    out.append(head)
    out.append("-" * len(head))
    for r in led.줄:
        rid = r["id"]
        mine = {f.이름: f for f in facts
                if (f.인자 and f.인자[0] == rid) or (f.근거 and f.근거[0][0] == rid)}
        cells = []
        close = mine.get("Close")
        cells.append(f"{close.값:>12,.2f}" if close and "Close" not in bad else f"{'--':>12}")
        for n in names:
            f = mine.get(n)
            cells.append(f"{f.값:>12,.2f}" if f and n not in bad else f"{'--':>12}")
        out.append(f"{rid:<12}" + "".join(cells))
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
    a = ap.parse_args(argv)

    if a.list_src or not a.출처:
        print("쓸 수 있는 출처:")
        for s in SRC.SOURCES.values():
            ok, why = s.쓸수있나()
            print(f"  {s.이름:<6} {s.설명}")
            print(f"         셈: {', '.join(s.셈)} · 신선도 {s.신선}일"
                  + ("" if ok else f"  **{why}**"))
            if s.별칭:
                print(f"         부를 수 있는 이름: {', '.join(list(s.별칭)[:10])}")
        print()
        print("  출처를 늘리는 것은 brief/source.py 에 Source 하나를 등록하는 일이다.")
        print("  가져오기·검사·셈·관문은 한 벌이라 새로 짜지 않는다.")
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

    facts = build(src, led)
    vs = GT.check(facts, led, src)
    print(render(src, led, facts, vs))
    return 1 if GT.hard(vs) else 0


if __name__ == "__main__":
    raise SystemExit(main())
