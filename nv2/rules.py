"""**규칙 등록소 -- 잰다 · 부친다 · 고친다 셋을 갖춰야 들어온다.**

## 왜 이 관문이 있나

앞 판이 죽은 병은 하나였다: **적어 두고 안 부친 규칙.** 다섯 번 났다.

    --persona        기본 경로가 문장론 함수를 안 부른다
    첫회차 규율      디렉터 카드에만 실렸다 -- 쓰는 쪽은 못 봤다
    echo.check       복사를 잡고 "원고는 그대로 쓴다" 로 흘려보냈다
    GENRE 빈 값      도착지도 카드도 안 선다
    [고정] 블록      옛 경로에만 있었다

다섯 번 다 **원고는 멀쩡히 나왔다.** 그래서 아무도 못 알아챘다.

## 관문

규칙이 되려면 넷이 있어야 한다.

    잰다     text -> 수            없으면 규칙이 아니라 **본보기**다(bank.py 로 간다)
    밴드     ruler.band(축)        `ref.json` 에 표본이 있어야 나온다. 짐작한 수는 못 들어온다
    부친다   어긋났을 때 할 말      낮을 때 · 높을 때 둘 다
    고친다   무손실 수리 함수       또는 `되먹임만=True` 라고 **명시**

`tests/test_nv2_rules.py` 가 넷을 다 본다. 하나라도 없으면 빨간불이다.

## 규칙은 셋까지만 부친다

한꺼번에 시키면 안 지켜진다. 어긋난 축이 여섯이어도 **제일 먼 셋**만 말한다.
나머지는 다음 회차에.
"""
from __future__ import annotations

from collections import namedtuple

from nv2 import repair, ruler

Rule = namedtuple("Rule", "축 이름 낮을때 높을때 고친다 되먹임만 왜")

# 한 회차에 부칠 규칙의 최대 수. **셋이다.**
MAX = 3

RULES = (
    Rule("dialog", "대사 줄 몫",
         "대사가 {got:.0%}뿐이다. **따옴표를 열어라** -- 사람이 한 말은 큰따옴표 안에 그대로,"
         " **제 줄에** 놓는다. `…라고 말했다` 로 접으면 그것은 대사가 아니라 요약이고,"
         " 이 자가 세는 것은 따옴표 안의 줄이다.",
         "대사가 {got:.0%}다. 말 사이에 몸과 자리를 넣어라 -- 누가 어디서 무엇을 하며 말하는지.",
         None, True, "라노벨은 설명:묘사:대사 = 1:1:2 다. 대사가 장면을 민다"),

    Rule("sent_len", "문장 길이",
         "문장이 짧다({got:.0f}자). **하나를 오래 보고 자세히 적어라** -- 무엇이 어떤 꼴이고"
         " 어디에 어떻게 놓여 있는지. 절을 '-고 · -면서' 로 잇대서 늘이지는 마라.",
         "문장이 길다({got:.0f}자). 끊어라 -- 끊은 자리마다 무엇이 어떠했는지를 하나씩 넣는다.",
         None, True, "실제 웹소설 1화가 47.6자다. 앞 판은 22.58 로 끌고 있었다"),

    Rule("da_share", "'-다' 로 끝나는 몫",
         "말끝이 흩어져 산만하다. 기본 종결로 돌아오는 자리를 두어라.",
         "짧은 '-다' 로 끝나는 문장이 {got:.0%}다. {hi:.0%} 아래로 내려라 --"
         " **다만 명사로만 끝내지 마라.** 앞 판이 그러다 '…의 걸음.' '…의 침묵.' 으로"
         " 도배됐다. 말끝을 바꾸는 것보다 **따옴표를 여는 편**이 빠르다.",
         None, True, "축 하나를 누르면 다른 축이 부러진다 -- 그래서 짝을 같이 말한다"),

    Rule("names", "천 자당 도는 이름",
         "도는 이름이 적다({got:.1f}). 곁에 사람을 세워라 -- 부를 상대가 없으면 대사가 안 선다.",
         "천 자당 도는 이름이 {got:.0f}개다. {hi:.0f} 아래로 줄여라 -- **새 이름을 그만 던지고**"
         " 이미 있는 사람으로 장면을 굴려라. 넷째부터는 직함이나 생김새로 부른다.",
         None, True, "한 회차에 외우게 할 새 이름은 셋 안쪽"),

    Rule("short", "짧은 문장의 몫",
         "짧은 문장이 없다({got:.0%}). 결정적인 자리에서 한 번 끊어라.",
         "짧은 문장이 {got:.0%}다. 붙일 것은 붙여라 -- 짧은 것만 이어지면 그것도 단조로움이다.",
         None, True, "리듬은 몫이 아니라 배치다"),
)

BY = {r.축: r for r in RULES}


def live() -> list:
    """**밴드가 있는 규칙만 산다.** 표본이 없으면 규칙이 아니다."""
    return [r for r in RULES if ruler.band(r.축)]


def off(text: str) -> list:
    """(규칙, 어느 쪽, 거리, 우리 값). 먼 것부터."""
    m = ruler.measure(text)
    if not m:
        return []
    out = []
    for r in live():
        if r.축 not in m:
            continue
        lo, hi = ruler.band(r.축)
        d = ruler.gap(m[r.축], lo, hi)
        if d > 0:
            out.append((r, "낮" if m[r.축] < lo else "높", d, m[r.축]))
    return sorted(out, key=lambda x: -x[2])


def says(text: str, limit: int = MAX) -> list:
    """이번 회차에 부칠 말. **제일 먼 것부터 셋까지.**"""
    out = []
    for r, side, _d, got in off(text)[:limit]:
        lo, hi = ruler.band(r.축)
        tmpl = r.낮을때 if side == "낮" else r.높을때
        out.append(tmpl.format(got=got, lo=lo, hi=hi, mid=(lo + hi) / 2))
    return out


def gate() -> list:
    """**등록소의 자기 검사.** 넷을 못 갖춘 규칙을 돌려준다. 비어 있어야 한다."""
    bad = []
    for r in RULES:
        if not callable(getattr(ruler, "measure", None)):
            bad.append((r.축, "잴 자가 없다"))
        if r.축 not in ruler.measure("가나다. 라마바.\n\"말.\"\n") and r.축 != "chars":
            bad.append((r.축, "measure 가 이 축을 안 낸다"))
        if not (r.낮을때 and r.높을때):
            bad.append((r.축, "부칠 말이 한쪽뿐이다"))
        if not r.고친다 and not r.되먹임만:
            bad.append((r.축, "고치는 손도 없고 되먹임만이라고 밝히지도 않았다"))
        if not r.왜:
            bad.append((r.축, "왜 있는지 안 적혀 있다"))
    return bad


# **수리는 규칙과 따로 산다.** 정도의 문제가 아니라 무손실인 것들이라 축에 안 매인다.
FIXES = (("되풀이", repair.dedup), ("무대 낱말", repair.rename))
