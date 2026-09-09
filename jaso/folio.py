"""**포트폴리오는 문항이 다른 자소서다.** 그래서 생성자도 관문도 새로 안 만든다.

    python3 jaso/folio.py --표 내원장.json --사실만          # LLM 0회. 원장 그대로
    python3 jaso/folio.py --표 내원장.json --낼곳 포트폴리오.md   # 산문 (Gemini)
    python3 jaso/folio.py --표 내원장.json --문항만          # 무엇을 물어 쓸 것인가

## 왜 새 파이프라인이 아닌가

자소서와 포트폴리오는 **재료가 같다.** 둘 다 원장의 항목에서 나오고, 둘 다 지어낸
수와 승격된 역할에서 무너진다. 다른 것은 **무엇을 묻느냐**뿐이다.

    자소서    회사가 정한 문항에 답한다
    포트폴리오 **항목마다** 같은 것을 묻는다 -- 무엇을 맡아 무엇을 했고 무엇이 달라졌나

그래서 여기서 하는 일은 **항목마다 문항을 하나씩 만드는 것**이고, 그 뒤는 `write.py`
와 `gate.py` 가 그대로 받는다. 새 생성자를 만들면 관문을 두 벌 갖게 되고, 두 벌은
언젠가 갈라진다(`brain/README.md`).

## `--사실만` 이 기본에 가깝다

포트폴리오는 자소서와 달리 **표가 산문보다 나은 자리가 많다.** 기간·역할·쓴 것·잰 값과
재는 법은 늘어놓는 편이 읽힌다. 그래서 `--사실만` 은 LLM 을 한 번도 안 부르고 원장을
그대로 낸다 -- 키가 없어도 돌고, 지어낼 자리가 아예 없다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import gate as GT                                          # noqa: E402
from jaso import item as IT                                          # noqa: E402
from jaso import ledger as LG                                        # noqa: E402
from jaso import trace as TR                                         # noqa: E402
from jaso import write as WR                                         # noqa: E402


def 문항만들기(L: LG.원장, 칸: int = 600) -> list:
    """항목마다 문항 하나. **`item.py` 가 쪼갤 수 있는 말로 적는다.**

    '무엇을 맡아' 가 지목, '어떻게' 가 행동, '무엇이 달라졌' 이 결과로 갈린다 --
    그래야 J006 이 빈 자리를 잡고 `ask.py` 가 그 자리를 물을 수 있다.
    """
    out = []
    for i, h in enumerate(L.항목들, 1):
        이름 = h.이름 or h.id
        out.append(IT.쪼개기(
            f"[{이름}] 에서 본인이 무엇을 맡았는지, 어떤 문제를 어떻게 풀었는지, "
            f"그 결과 무엇이 달라졌는지 구체적 경험을 바탕으로 기술하시오. ({칸}자 이내)",
            str(i)))
    return out


def 사실로(L: LG.원장, 이름: str = "") -> str:
    """**LLM 0회.** 원장을 그대로 늘어놓는다. 지어낼 자리가 없다."""
    벌 = [f"# 포트폴리오{' -- ' + 이름 if 이름 else ''}", ""]
    for h in L.항목들:
        벌 += [f"## {h.이름 or h.id}" + (f"  ({h.갈래})" if h.갈래 else ""), ""]
        줄 = [("곳", h.곳), ("기간", " ~ ".join(h.언제) +
                           (f"  ({h.개월}개월)" if h.개월 else "")),
             ("맡은 것", h.역할), ("같이", f"{h.같이}명" if h.같이 else ""),
             ("쓴 것", ", ".join(h.쓴것)), ("증빙", h.증빙)]
        벌 += [f"| {k} | {v} |" for k, v in 줄 if v]
        if 벌[-1].startswith("|"):
            벌.insert(len(벌) - sum(1 for k, v in 줄 if v), "| | |")
            벌.insert(len(벌) - sum(1 for k, v in 줄 if v), "|---|---|")
        벌.append("")
        if h.한일:
            벌 += ["**한 일**", ""] + [f"- {x}" for x in h.한일] + [""]
        쓸수있는것 = [m for m in h.잰것 if m.쓸수있나]
        못쓰는것 = [m for m in h.잰것 if not m.쓸수있나]
        if 쓸수있는것:
            벌 += ["**잰 것**", "", "| 무엇 | 전 | 후 | 어떻게 쟀나 |", "|---|---|---|---|"]
            벌 += [f"| {m.무엇} | {m.전}{m.단위} | {m.후}{m.단위} | {m.어떻게} |"
                  for m in 쓸수있는것] + [""]
        if 못쓰는것:
            벌 += ["**달라지긴 했으나 재지 않은 것** (수를 붙이지 않는다)", ""]
            벌 += [f"- {m.무엇}" for m in 못쓰는것] + [""]
    if L.생각들:
        벌 += ["## 제가 직접 적은 말", ""] + [f"- ({g.갈래}) {g.말}" for g in L.생각들]
        벌 += [""]
    빈증빙 = [h.id for h in L.항목들 if not h.증빙.strip()]
    if 빈증빙:
        벌 += ["---", "",
              f"증빙이 안 적힌 항목: {', '.join(빈증빙)} -- "
              "**면접에서 물으면 무엇을 보여 줄지 정해 두라**", ""]
    return "\n".join(벌) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="포트폴리오 -- 문항이 다른 자소서다")
    ap.add_argument("--표", dest="표", required=True)
    ap.add_argument("--이름", default="")
    ap.add_argument("--칸", dest="칸", type=int, default=600)
    ap.add_argument("--벌", dest="벌", type=int, default=3)
    ap.add_argument("--낼곳", default="")
    ap.add_argument("--사실만", action="store_true", help="LLM 0회. 원장 그대로")
    ap.add_argument("--문항만", action="store_true", help="무엇을 물어 쓸 것인가")
    a = ap.parse_args(argv)

    L = LG.읽기(a.표)
    if not L:
        print("원장이 비었다 -- **쓸 재료가 없다.** 먼저 물어라:\n"
              "  python3 jaso/run.py --이름 <이름> --문항 \"...\"", file=sys.stderr)
        return 3
    막힌것 = LG.hard(LG.검사(L))
    if 막힌것:
        for v in 막힌것:
            print(f"  {v}", file=sys.stderr)
        print("원장에 hard 위반이 있다 -- 고치기 전에는 그 위에서 못 쓴다",
              file=sys.stderr)
        return 1

    qs = 문항만들기(L, a.칸)
    if a.문항만:
        for q in qs:
            print(f"\n[{q.번호}] {q.원문}")
            for r in q.요구:
                print(f"    {r.id} [{r.종류}] {r.말}")
        return 0

    if a.사실만:
        글 = 사실로(L, a.이름)
    else:
        조각, 쓴것 = [], set()
        for q in qs:
            r = WR.쓰기(q, L, a.벌, a.이름, "", 쓴것)
            if not r["글있나"]:
                print(f"\n**한 벌도 글을 못 받았다: {r['왜']}**\n"
                      "  (GEMINI_API_KEY 가 있는 데서 돌려라 -- 빈 파일은 안 쓴다. "
                      "`--사실만` 은 키 없이 돈다)", file=sys.stderr)
                return 3
            쓴것 |= set(r["뽑힘"]["항목"])
            h = L.찾기(r["뽑힘"]["항목"][0]) if r["뽑힘"]["항목"] else None
            조각.append(f"## {h.이름 if h else q.번호}\n\n{r['뽑힘']['글']}\n")
            print(f"  [{q.번호}] {r['벌']}벌 중 hard 0 인 것 {r['성한것']}벌 "
                  f"-> soft {r['뽑힘']['soft']}건인 것")
        글 = (f"---\n이름: \"{a.이름}\"\n---\n\n# 포트폴리오\n\n" + "\n".join(조각))

    if a.낼곳:
        Path(a.낼곳).write_text(글, encoding="utf-8")
        print(f"[씀] {a.낼곳}")
    else:
        print(글)

    if not a.사실만 and a.낼곳:
        자 = GT.읽기(Path(a.낼곳).read_text(encoding="utf-8"), Path(a.낼곳))
        vs, 대조, 미검증 = GT.검사(자, L)
        hard = [v for v in vs if v.등급 == "hard"]
        print(f"\n관문: hard {len(hard)} · soft {len(vs) - len(hard)} · "
              f"값 대조 {대조}건 · 미검증 {미검증}건")
        for v in vs:
            print(f"  {v}")
        근거 = Path(a.낼곳).with_name(Path(a.낼곳).stem + "_근거.md")
        근거.write_text(TR.글로(자, L, TR.훑기(자, L)), encoding="utf-8")
        print(f"[씀] {근거}")
        return 1 if hard else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
