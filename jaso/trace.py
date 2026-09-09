"""**작성 근거 기록** -- 이 문단이 어디서 나왔는지.

    python3 jaso/trace.py 자소서.md --표 내원장.json
    python3 jaso/trace.py 자소서.md --표 내원장.json --답 답.txt --낼곳 근거.md

## 왜 이것이 AI 판별 대비책인가

판별 프로그램에 걸렸을 때 필요한 것은 **회피가 아니라 근거**다. 그리고 이것은 가정이
아니라 그 프로그램들의 성질에서 나온다 -- **오탐이 난다.** 정말 자기가 쓴 글도 걸린다.
그때 "안 썼습니다" 라고 말하는 것과, 언제 어디서 무슨 역할로 한 일이고 그 수를 어떻게
쟀고 무엇을 보여 줄 수 있는지가 적힌 종이를 내미는 것은 다른 일이다.

그 종이가 여기서 나온다. 그리고 **없는 것을 새로 만들지 않는다** -- 원장과 물음·답이
이미 그 기록이었고, 이 파일은 그것을 문단에 맞춰 늘어놓기만 한다.

## 더 중요한 것은 면접이다

원장에 있는 것만 썼으므로 **되물으면 답할 수 있다.** 자소서에서 판별 프로그램보다
훨씬 자주, 훨씬 확실하게 거짓을 잡아내는 자가 면접관이다. `J002`(안 잰 수를 막는 것)와
`J004`(역할 승격을 막는 것)가 애초에 그 자리를 겨냥한 관문이다.

## 이 파일이 안 하는 것

- **판별 점수를 예측하지 않는다.** 어떤 프로그램이 쓰이는지 모른다.
- **탐지를 피하는 손질을 하지 않는다.** 동의어를 바꾸고 문장을 흔들어 점수를 낮추는
  일. 그것은 사실을 하나도 안 바꾸면서 저작자만 속이는 짓이고, 걸리면 그때는
  '지어냈다' 가 아니라 '숨겼다' 가 된다.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import gate as GT                                          # noqa: E402
from jaso import intake as IN                                        # noqa: E402
from jaso import ledger as LG                                        # noqa: E402
from jaso import swap as SW                                          # noqa: E402


def 훑기(자: GT.자소서, L: LG.원장, 답들: dict | None = None) -> list:
    """문항 -> 문단 -> 어느 항목에서 왔나. **못 찾은 문단도 그대로 적는다.**"""
    out = []
    for a in 자.답변들:
        줄 = []
        for p in a.문단들:
            h = SW.가리키는것(p, L)
            줄.append({"문단": p,
                      "항목": h.id if h else "",
                      "앵커": sorted({x for v in SW.앵커들(p, L).values() for x in v}),
                      "증빙": (h.증빙 if h else ""),
                      "언제": (" ~ ".join(h.언제) if h else ""),
                      "역할": (h.역할 if h else "")})
        out.append({"문항": a.문항, "줄": 줄})
    return out


def 글로(자: GT.자소서, L: LG.원장, 훑은것: list, 답들: dict | None = None) -> str:
    벌 = [f"# 작성 근거 기록 -- {자.이름}", "",
         f"- 만든 날: {date.today().isoformat()}",
         f"- 회사 · 직무: {자.회사 or '(안 적힘)'} · {자.직무 or '(안 적힘)'}",
         f"- 경험 원장: 항목 {len(L)}개 · 직접 적은 말 {len(L.생각들)}개", ""]
    붙은문단 = sum(1 for x in 훑은것 for r in x["줄"] if r["항목"])
    온문단 = sum(len(x["줄"]) for x in 훑은것)
    벌 += [f"문단 {온문단}개 중 **{붙은문단}개**가 원장의 항목에 닿아 있다.", ""]

    for x in 훑은것:
        q = x["문항"]
        벌 += [f"## 문항 {q.번호 or ''} {q.원문[:70]}", ""]
        for i, r in enumerate(x["줄"], 1):
            머리 = re.sub(r"\s+", " ", r["문단"])[:64]
            if r["항목"]:
                h = L.찾기(r["항목"])
                벌 += [f"{i}. {머리}…",
                      f"   - 원장 항목: `{r['항목']}` {h.이름 if h else ''}"
                      f" ({r['역할']} · {r['언제']})",
                      f"   - 이 문단에 박힌 것: {', '.join(r['앵커'][:8])}",
                      f"   - 증빙: {r['증빙'] or '**없음 -- 면접에서 물으면 보여 줄 것을 적어 두라**'}"]
                for m in (h.잰것 if h else []):
                    if m.쓸수있나 and any(v in r["앵커"] for v in m.수들):
                        벌.append(f"   - 잰 방법: {m.무엇} {m.전}{m.단위} -> "
                                 f"{m.후}{m.단위} ({m.어떻게})")
            else:
                벌 += [f"{i}. {머리}…",
                      "   - **원장에 닿지 않는 문단이다.** 되물으면 무엇을 말할지 "
                      "미리 정해 두라"]
            벌.append("")
    if L.생각들:
        벌 += ["## 제가 직접 적은 말", ""]
        벌 += [f"- ({g.갈래}) {g.말}" for g in L.생각들] + [""]
    if 답들:
        벌 += ["## 인터뷰 원문 (제가 답한 그대로)", ""]
        벌 += [f"{k}) {v}" for k, v in sorted(답들.items(),
                                            key=lambda x: int(x[0]))] + [""]
    벌 += ["---", "",
          "이 기록은 원장과 답변에서 그대로 뽑은 것이다. "
          "**판별 프로그램 점수를 예측하지 않으며**, 탐지를 피하는 손질도 하지 않았다."]
    return "\n".join(벌) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="이 문단이 어디서 나왔는지 적는다")
    ap.add_argument("자소서")
    ap.add_argument("--표", dest="표", required=True)
    ap.add_argument("--답", dest="답", default="", help="인터뷰 답 원문 (있으면 함께)")
    ap.add_argument("--낼곳", default="")
    a = ap.parse_args(argv)

    p = Path(a.자소서)
    if not p.exists():
        print(f"그런 파일이 없다: {p}", file=sys.stderr)
        return 3
    L = LG.읽기(a.표)
    if not L:
        print("원장이 비었다 -- **적을 근거가 없다.** 그것이 바로 이 기록이 필요한 "
              "까닭이기도 하다", file=sys.stderr)
        return 3
    자 = GT.읽기(p.read_text(encoding="utf-8"), p)
    답들 = (IN.답나누기(Path(a.답).read_text(encoding="utf-8")) if a.답 else None)
    글 = 글로(자, L, 훑기(자, L, 답들), 답들)
    if a.낼곳:
        Path(a.낼곳).write_text(글, encoding="utf-8")
        print(f"[씀] {a.낼곳}")
    else:
        print(글)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
