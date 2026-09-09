"""**생성자.** 원장에서 꺼낸 사실을 주고 자소서 한 벌을 받는다. 심판은 여기 없다.

    python3 jaso/write.py --표 내원장.json --문항 "<문항 원문>" --회사 무봉테크
    python3 jaso/write.py --표 내원장.json --문항원장 --벌 4 --낼곳 자소서.md
    python3 jaso/write.py --표 내원장.json --문항 "..." --프롬프트만   # 무엇을 주는지

## 왜 생성자가 관문을 몰라야 하는가

이 저장소가 세 번 데었다.

  · `novel/gate.py` -- 관문을 나중에 붙였더니 원고가 관문을 통과하려고 균질해졌다
  · `mathdrift/spread.py` -- 발산 프롬프트에 심판을 실었더니 발산이 사양서가 됐다
  · `law/write.py` -- 그래서 처음부터 안 실었다

자소서에서는 더 나쁘다. **관문 이름을 알려 주면 관문을 통과하는 거짓말이 나온다.**
"원장에 있는 수만 쓰라" 고 하면 모델은 원장의 수를 아무 데나 끼워 넣어 J002 를
통과시키고, 그 문장은 통과했는데 틀린 문장이 된다. 그래서 **이 파일의 프롬프트에는
J·P·E 가 한 글자도 없다.** `tests/test_jaso_write.py` 가 그것을 고정한다.

여기가 아는 것은 둘뿐이다 -- **문항 원문**과 **원장에서 꺼낸 사실**.

## 한 벌이 아니라 여러 벌

```
문항 하나 ──> n 벌 ──> 관문 ──> hard 0 인 것들 ──> soft 가 적은 것을 고른다
                 ↑                                        │
        심판을 안 싣는다                          고른 까닭을 적는다
```

일반 LLM 이 지는 마지막 자리가 이것이다 -- **한 번 쓰고 끝낸다.** `seek/` 가 도약을
사람이 아니라 기계로 판정한 자리와 같은 배치다. 사람이 고르지 않고, 다만 **왜 그것이
남았는지**는 사람이 읽을 수 있게 적는다.

## 모델

**Gemini 를 쓴다.** 산문이 토큰의 대부분이라 구독으로 청구할 자리가 아니다
(`CLAUDE.md` 의 배치 그대로 -- 디렉터만 Claude, 산문은 Gemini).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import corpus as CP                                        # noqa: E402
from jaso import gate as GT                                          # noqa: E402
from jaso import item as IT                                          # noqa: E402
from jaso import ledger as LG                                        # noqa: E402

_POOL = None


def _풀에게(글: str) -> str:
    """기본 물음이. 후보 풀은 한 번만 세운다 -- build_pool 이 키마다 모델을 조회한다."""
    global _POOL
    if _POOL is None:
        sys.path.insert(0, str(ROOT / "orchestrator"))
        import llm_pool
        pool = llm_pool.build_pool()
        if not pool:
            raise RuntimeError("LLM 후보 풀이 비었다 -- GEMINI_API_KEY 를 설정하라")
        _POOL = (llm_pool, pool)
    mod, pool = _POOL
    return mod.call(pool, 글, pool_id="jaso")[0]


# ---------------------------------------------------------------- 재료 고르기

def 고르기(q: IT.문항, L: LG.원장, 쓴것: set = frozenset()) -> tuple:
    """이 문항에 줄 (항목들, 생각들). **안 쓴 것을 먼저 준다.**

    한 경험을 여러 문항에 돌려 쓰면 한 벌을 통째로 읽는 사람에게 재료가 하나뿐인
    것으로 보인다. 그래서 이미 쓴 것은 뒤로 민다 -- 빼지는 않는다(뺐다가 줄 것이
    없어지면 그 문항은 지어낸 것으로 채워진다).
    """
    종류 = {r.종류 for r in q.요구}
    def 점수(h):
        s = (0 if h.id in 쓴것 else 100)
        s += 20 if (h.잰것 and "결과" in 종류) else 0
        s += 10 * len(LG.말앵커(h)) // 5 + 5 * len(h.한일)
        return s
    항목 = sorted(L.항목들, key=점수, reverse=True)[:3]
    갈래 = {"이유": "지원동기", "지원동기": "지원동기", "계획": "포부",
           "성찰": "성찰", "지목": "가치"}
    쓸생각 = [g for g in L.생각들
             if g.갈래 in {갈래[r.종류] for r in q.요구 if r.종류 in 갈래}]
    return 항목, 쓸생각


def _사실(h: LG.항목) -> str:
    줄 = [f"- 무엇: {h.이름}" + (f" ({h.갈래})" if h.갈래 else ""),
          f"- 어디: {h.곳}" if h.곳 else "",
          f"- 언제: {' ~ '.join(h.언제)}" + (f" ({h.개월}개월)" if h.개월 else ""),
          f"- 내가 맡은 것: {h.역할}",
          f"- 같이 한 사람: {h.같이}명" if h.같이 else ""]
    for x in h.한일:
        줄.append(f"- 한 일: {x}")
    for m in h.잰것:
        if m.쓸수있나:
            줄.append(f"- 잰 것: {m.무엇} {m.전}{m.단위} -> {m.후}{m.단위} "
                     f"(잰 방법: {m.어떻게})")
        else:
            줄.append(f"- {m.무엇}: 달라지긴 했으나 **재지 않았다** "
                     "(수를 쓰지 말고 무엇이 달라졌는지만 쓸 것)")
    if h.쓴것:
        줄.append(f"- 쓴 것: {', '.join(h.쓴것)}")
    return "\n".join(x for x in 줄 if x)


def 프롬프트(q: IT.문항, 항목: list, 생각: list, 회사: str = "",
           직무: str = "") -> str:
    """**관문 이야기가 한 줄도 없다.** 문항과 원장에서 꺼낸 사실뿐이다."""
    재료 = "\n\n".join(f"### 경험 {i}\n{_사실(h)}" for i, h in enumerate(항목, 1))
    말 = "\n".join(f"- ({g.갈래}) {g.말}" for g in 생각)
    칸 = (f"{q.하한}자 이상 {q.상한}자 이내" if q.하한 and q.상한
          else (f"{q.상한}자 이내" if q.상한 else "글자 수 제한이 안 적혀 있습니다"))
    공백 = "공백을 포함해" if q.공백포함 else "공백을 빼고"
    어디 = (f"{회사} " if 회사 else "") + (f"{직무} 직무 " if 직무 else "")
    return f"""당신은 {어디}지원자 본인입니다. 아래 문항에 대한 자기소개서 답변을
1인칭으로 씁니다.

## 문항

{q.원문}

## 제 실제 경험 (이것 말고 다른 재료는 없습니다)

{재료 or "(없습니다)"}

{"## 제가 직접 적어 둔 말" + chr(10) + chr(10) + 말 if 말 else ""}

## 재료를 벗어나지 않는 법

**위에 없는 것은 지어내지 마십시오.** 회사 이름·수·기간·직책·도구 이름을 새로
만들지 마십시오. 위에 적힌 수는 적힌 그대로만 쓰고, 바꾸거나 반올림하지 마십시오.
'재지 않았다' 고 적힌 것에는 수를 붙이지 마십시오 -- 무엇이 달라졌는지 말로만 씁니다.
제가 맡은 것이 '참여' 라고 적혀 있으면 참여라고 씁니다.

쓸 말이 모자라면 **채우지 말고 짧게 끝내십시오.** 빈 곳은 제가 채웁니다.

## 어떻게 쓰나

- 겪은 순서가 아니라 **무엇을 보고 무엇을 했고 무엇이 달라졌는지** 순서로 씁니다.
- 위 경험에서만 나올 수 있는 것(고유한 이름·수·상황)을 문단마다 하나는 둡니다.
- 저를 설명하는 형용사 대신 제가 한 일을 씁니다.
- 누가 했는지 드러나게 씁니다.

## 길이

{칸} ({공백} 셉니다). 이 범위를 지키십시오.

본문만 출력하십시오. 제목·머리말·설명을 붙이지 마십시오."""


_울타리 = re.compile(r"^\s*```[a-z]*\s*\n|\n```\s*$")


def 벗기기(글: str) -> str:
    return _울타리.sub("", (글 or "").strip()).strip()


# ---------------------------------------------------------------- 여러 벌

def 한벌(q: IT.문항, L: LG.원장, 회사="", 직무="", 쓴것=frozenset(),
        묻기=None) -> tuple:
    항목, 생각 = 고르기(q, L, 쓴것)
    글 = 벗기기((묻기 or _풀에게)(프롬프트(q, 항목, 생각, 회사, 직무)))
    return 글, [h.id for h in 항목]


def 재기(q: IT.문항, 본문: str, L: LG.원장, 회사="", 직무="") -> tuple:
    """이 한 벌을 관문에 건다. `(hard 수, soft 수, 위반들)`."""
    머리 = (f"---\n회사: \"{회사}\"\n직무: \"{직무}\"\n---\n\n"
           f"## {q.번호 + '. ' if q.번호 else ''}{q.원문}\n\n{본문}\n")
    vs, _, _ = GT.검사(GT.읽기(머리), L)
    return (len([v for v in vs if v.등급 == "hard"]),
            len([v for v in vs if v.등급 == "soft"]), vs)


def 쓰기(q: IT.문항, L: LG.원장, 벌: int = 3, 회사="", 직무="",
        쓴것=frozenset(), 묻기=None) -> dict:
    """n 벌 뽑고 **관문이 고른다.** 사람이 안 고른다."""
    것들 = []
    for _ in range(max(1, 벌)):
        try:
            글, 쓴항목 = 한벌(q, L, 회사, 직무, 쓴것, 묻기)
        except Exception as e:                    # 한 벌이 죽어도 나머지는 살린다
            것들.append({"글": "", "왜": f"{type(e).__name__}: {e}", "hard": 99,
                        "soft": 99, "위반": [], "항목": []})
            continue
        h, s, vs = 재기(q, 글, L, 회사, 직무)
        것들.append({"글": 글, "hard": h, "soft": s, "위반": vs, "항목": 쓴항목,
                    "왜": ""})
    글있는것 = [x for x in 것들 if x["글"].strip()]
    성한것 = [x for x in 글있는것 if not x["hard"]]
    # **한 벌도 글을 못 받았으면 뽑지 않는다.**
    #
    # 실측: 키가 없는 데서 돌렸더니 모든 벌이 예외로 죽었는데, `min` 이 빈 글을 골라
    # `0자` 짜리 자소서가 파일로 나왔다. 화면에는 "[씀] 자소서.md" 가 찍히고 관문은
    # J005(0자)로 빨간불을 냈다 -- **없는 것보다 나쁘다.** 사람은 파일이 생긴 것을
    # 먼저 보고, 빨간불은 글이 나쁜 탓이라고 읽는다. 실제로는 아무것도 안 나온 것이다.
    뽑힘 = (min(성한것 or 글있는것, key=lambda x: (x["hard"], x["soft"], -len(x["글"])))
           if 글있는것 else None)
    return {"문항": q, "것들": 것들, "뽑힘": 뽑힘, "성한것": len(성한것),
            "벌": len(것들), "글있나": bool(글있는것),
            "왜": " · ".join(sorted({x["왜"] for x in 것들 if x["왜"]}))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="자소서를 쓴다 (관문은 모른다)")
    ap.add_argument("--표", dest="표", required=True, help="경험 원장 JSON")
    ap.add_argument("--문항", dest="문항", action="append", default=[])
    ap.add_argument("--문항원장", action="store_true")
    ap.add_argument("--곳", default=str(CP.문항DIR))
    ap.add_argument("--회사", default="")
    ap.add_argument("--직무", default="")
    ap.add_argument("--벌", dest="벌", type=int, default=3)
    ap.add_argument("--낼곳", default="")
    ap.add_argument("--프롬프트만", dest="dry", action="store_true",
                    help="부르지 않고 프롬프트만 찍는다 -- 무엇을 주는지 눈으로 본다")
    a = ap.parse_args(argv)

    L = LG.읽기(a.표)
    if not L:
        print("원장이 비었다 -- **쓸 재료가 없다.** 먼저 물어라:\n"
              "  python3 jaso/ask.py --표 원장.json --문항 \"...\"", file=sys.stderr)
        return 3
    막힌것 = LG.hard(LG.검사(L))
    if 막힌것:
        print("원장에 hard 위반이 있다 -- 이 위에서 쓰면 판정이 뜻을 못 갖는다:",
              file=sys.stderr)
        for v in 막힌것:
            print(f"  {v}", file=sys.stderr)
        return 1

    문항들 = [IT.쪼개기(x, str(i + 1)) for i, x in enumerate(a.문항)]
    if a.문항원장:
        문항들 += [q.쪼갠것() for q in CP.읽기(a.곳).문항들]
    if not 문항들:
        ap.error("--문항 이나 --문항원장 을 주십시오")

    if a.dry:
        for q in 문항들:
            항목, 생각 = 고르기(q, L)
            print(프롬프트(q, 항목, 생각, a.회사, a.직무))
            print("=" * 70)
        return 0

    벌들, 쓴것, 조각 = [], set(), []
    for q in 문항들:
        r = 쓰기(q, L, a.벌, a.회사, a.직무, 쓴것)
        if not r["글있나"]:
            print(f"\n**문항 {q.번호 or '?'} 에서 한 벌도 글을 못 받았다: {r['왜']}**",
                  file=sys.stderr)
            print("  (GEMINI_API_KEY 가 있는 데서 돌려라 -- 빈 파일은 안 쓴다)",
                  file=sys.stderr)
            return 3
        벌들.append(r)
        쓴것 |= set(r["뽑힘"]["항목"])
        조각.append(f"## {q.번호 + '. ' if q.번호 else ''}{q.원문}\n\n"
                   f"{r['뽑힘']['글']}\n")
        print(f"[문항 {q.번호 or '?'}] {r['벌']}벌 중 hard 0 인 것 {r['성한것']}벌 "
              f"-> soft {r['뽑힘']['soft']}건인 것을 골랐다")
        for x in r["것들"]:
            print(f"    {'뽑힘' if x is r['뽑힘'] else '   '} "
                  f"hard {x['hard']} · soft {x['soft']} · {len(x['글'])}자"
                  + (f" · {x['왜'][:50]}" if x["왜"] else ""))

    글 = (f"---\n회사: \"{a.회사}\"\n직무: \"{a.직무}\"\n---\n\n"
         + "\n".join(조각))
    if a.낼곳:
        Path(a.낼곳).write_text(글, encoding="utf-8")
        print(f"\n[씀] {a.낼곳}")
        print(f"이제 심판을 돌린다:  python3 jaso/gate.py {a.낼곳} "
              f"--표 {a.표} -v")
    else:
        print("\n" + 글)
    남은hard = sum(r["뽑힘"]["hard"] for r in 벌들)
    if 남은hard:
        print(f"\n**hard {남은hard}건이 남았다.** 어느 벌도 통과하지 못했다 -- "
              "고른 것은 그중 덜 나쁜 것이지 통과한 것이 아니다")
    return 1 if 남은hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
