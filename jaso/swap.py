"""**치환 검사** -- 회사 이름을 갈아 끼워도 그대로면, 그 문단은 그 회사 것이 아니다.

    python3 jaso/swap.py 자소서.md --표 내원장.json
    python3 jaso/swap.py 자소서.md --표 내원장.json --보기   # 갈아 끼운 글을 눈으로

## 사람이 3초 만에 내리는 판정

읽는 사람은 자소서를 오래 안 본다. 그리고 제일 먼저 알아보는 것이 **돌려쓴 글**이다.

    "저는 귀사의 인재상인 도전정신에 부합하는 인재입니다. 어떤 어려움 앞에서도
     포기하지 않고 끝까지 해내는 성격으로, 맡은 일에 최선을 다해 왔습니다."

회사 이름만 바꾸면 어디에나 들어간다. **일반 LLM 이 기본으로 내놓는 것이 이 글이다** --
재료를 안 줬으니 일반론밖에 쓸 것이 없다.

## LLM 없이 판정된다

'좋은 글인가' 는 취향이지만 **'이 문단에 원장에서 온 것이 박혀 있는가' 는 취향이 아니다.**

    앵커 = 원장에서 온 구체 토큰 (곳 · 프로젝트 이름 · 쓴 기술 · 잰 수 · 인원)

회사 이름과 직무 이름은 앵커가 **아니다** -- 그것이 바로 갈아 끼우는 자리이므로.
원장 앵커가 0 인 문단은 어느 회사 자소서에 넣어도 말이 된다. 그것이 판정이다.

## 문단으로 세고 답변으로 판정한다

문단마다 앵커를 요구하면 이음말 문단("그래서 저는 다음을 배웠습니다")까지 걸린다 --
**과잉 기각하는 심판은 맞는 답도 버린다.** 그래서 두 층으로 본다.

    답변 전체 앵커 0         -> hard.  이 답변은 통째로 돌려쓴 글이다
    앵커 없는 문단이 과반    -> soft.  뼈대는 있는데 살이 일반론이다

`seek/` 가 대조군을 둔 것과 같은 규율로, 검사는 **성한 문단에 초록불이 켜지는 것까지**
본다(`tests/test_jaso_swap.py`). 아무 데나 빨간불이 켜지는 자는 판정이 아니다.

## 못 보는 것

앵커가 박혀 있어도 **그 앵커가 그 회사와 상관있는지는 안 본다.** 그것은 JD 대조(P005)의
일이고 JD 원장이 있어야 한다. 여기가 보는 것은 "이 문단이 **누구의** 글인가" 지
"이 회사에 **맞는** 글인가" 가 아니다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import ledger as LG                                         # noqa: E402

빈줄 = re.compile(r"\n\s*\n")


def 문단들(글: str) -> list:
    """빈 줄로 가른다. 빈 줄이 없으면 통째로 한 문단이다."""
    return [p.strip() for p in 빈줄.split(글 or "") if p.strip()]


def 갈아끼우기(글: str, 회사: str = "", 직무: str = "",
             새회사: str = "□□기업", 새직무: str = "△△직무") -> str:
    """회사·직무 이름을 갈아 끼운 글. **판정에는 안 쓴다 -- 눈으로 보라고 있다.**

    판정은 앵커를 세서 한다(`재기`). 이 함수는 사람이 "정말 그대로 말이 되네" 를
    확인하는 자리다 -- 수가 아니라 눈이 납득해야 고치게 된다.
    """
    out = 글 or ""
    for a, b in ((회사, 새회사), (직무, 새직무)):
        a = (a or "").strip()
        if len(a) >= 2:
            out = out.replace(a, b)
            # '무봉테크' 를 넣었으면 '무봉' 만 쓴 자리도 같이 간다
            if len(a) >= 4:
                out = out.replace(a[:len(a) // 2 + 1], b)
    return out


def 앵커들(문단: str, L: LG.원장) -> dict:
    """이 문단에 박힌 앵커를 항목별로. `{항목id: [앵커, ...]}` -- 빈 것은 뺀다."""
    return {h.id: got for h in L.항목들 if (got := LG.앵커(문단, h))}


def 가리키는것(문단: str, L: LG.원장):
    """이 문단이 말하는 항목. **앵커가 제일 많은 것.** 없으면 None.

    관문 J002·J003·J004 가 "어느 경험을 두고 하는 말인가" 를 정하는 자리다. 어림이지만
    어림이라는 것을 적어 둔다 -- 앵커가 동수면 원장에 먼저 적힌 것을 고른다(안정적으로
    같은 답이 나와야 관문이 흔들리지 않는다).
    """
    got = 앵커들(문단, L)
    if not got:
        return None
    best = max(got.values(), key=len)
    for h in L.항목들:                       # 원장 순서 = 흔들리지 않는 순서
        if h.id in got and len(got[h.id]) == len(best):
            return h
    return None


def 재기(답변: str, L: LG.원장) -> dict:
    """문단마다 앵커를 센다. 판정은 안 한다 -- 세기만 한다."""
    ps = 문단들(답변)
    줄 = [{"문단": p, "앵커": sorted({a for v in 앵커들(p, L).values() for a in v})}
          for p in ps]
    빈 = [r for r in 줄 if not r["앵커"]]
    return {"문단수": len(ps), "빈문단": len(빈), "줄": 줄,
            "앵커수": len({a for r in 줄 for a in r["앵커"]})}


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="치환 검사 -- 회사 이름을 갈아 끼워 본다")
    ap.add_argument("자소서")
    ap.add_argument("--표", dest="표", default="jaso/보기.json", help="경험 원장 JSON")
    ap.add_argument("--회사", default="")
    ap.add_argument("--직무", default="")
    ap.add_argument("--보기", action="store_true", help="갈아 끼운 글을 그대로 보여 준다")
    a = ap.parse_args(argv)

    글 = Path(a.자소서).read_text(encoding="utf-8")
    L = LG.읽기(a.표)
    if not L:
        print("원장이 비었다 -- 앵커가 없으므로 **전부 치환 가능으로 보인다.** "
              "그것은 판정이 아니라 못 잰 것이다", file=sys.stderr)
        return 3

    잰것 = 재기(글, L)
    print(f"문단 {잰것['문단수']}개 · 앵커 없는 문단 {잰것['빈문단']}개 · "
          f"박힌 앵커 {잰것['앵커수']}종")
    for i, r in enumerate(잰것["줄"], 1):
        머리 = re.sub(r"\s+", " ", r["문단"])[:46]
        print(f"  {i:>2}. {'.' if r['앵커'] else 'X'} {머리}…")
        if r["앵커"]:
            print(f"        앵커: {', '.join(r['앵커'][:8])}")
    if a.보기 and (a.회사 or a.직무):
        print("\n── 갈아 끼운 글 ──────────────────────────────")
        print(갈아끼우기(글, a.회사, a.직무))
    if not 잰것["앵커수"]:
        print("\n**앵커가 하나도 없다.** 이 글은 어느 회사에나 들어간다")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
