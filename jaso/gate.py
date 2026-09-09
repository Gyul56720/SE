"""**자소서의 기계 관문** -- LLM 을 안 쓴다. 위반 목록을 돌려준다.

    python3 jaso/gate.py 자소서.md --표 내원장.json
    python3 jaso/gate.py 자소서.md --표 내원장.json -v        # soft 도 전부
    python3 jaso/gate.py 자소서.md --표 내원장.json --규칙 J002

`law/gate.py` 와 같은 규약 위에 있다. 다른 것은 대조 대상이다 -- 법은 조문 원문이
밖에 있었고, 여기는 **사용자의 경험 원장**이 밖에 있다.

    hard   확실한 위반. 이 벌을 기각한다.
    soft   의심스럽다. 보고하되 기각하지 않는다.
    미검증 원장이 없어 **아직 아무도 안 봤다.** 통과가 아니다.

세 번째가 제일 중요하다. 원장이 비었는데 통과시키면 관문이 있다는 착각만 생기고
환각은 그대로 나간다. 그래서 대조한 주장 수와 못 한 수를 보고가 **늘 같이** 적는다.

## 관문

    J001  근거 실재    원장에 없는 해·기술을 적었는가              hard/soft (원장 필요)
    J002  수치 일치    잰 값이 원장의 그 값과 같은가               hard      (원장 필요)
    J003  기간 정합    기간 길이가 원장과 같은가                   hard/soft (원장 필요)
    J004  역할 승격    원장이 '참여' 인데 '주도' 로 올려 썼는가     hard      (원장 필요)
    J005  글자 수      문항의 상·하한 안인가                       hard
    J006  문항 응답    문항이 물은 것에 다 닿았는가                hard/soft
    J007  구조         무엇이 달라졌는지가 있는가                  soft
    J008  자기모순     한 벌 안에서 같은 경험에 다른 수를 달았는가 hard      (원장 필요)

    P001  치환 가능    회사 이름을 갈아 끼워도 그대로인가          hard/soft (원장 필요)
    P002  주장-근거    '열정적' 뒤에 근거가 붙었는가               soft
    P003  상투구       돌려쓰는 말이 몇 개인가                     soft
    P004  수동·명사화  행위자가 사라졌는가                         soft
    P005  JD 대조      공고의 요구역량에 닿았는가                  (JD 원장 필요)
    P006  재탕         여러 문항이 같은 경험을 돌려 쓰는가         soft

    D001  문장 고름    문장 길이가 다 비슷한가                     soft
    D002  이음말       '또한' · '이를 통해' 로 굴러가는가          soft
    D003  고유 밀도    100자에 원장에서 온 것이 몇 개인가          soft (원장 필요)
    D004  문단 고름    문단이 다 같은 크기인가                     soft
    D005  문항 되풀이  첫 문장이 문항을 되풀이하는가               soft

**D 계열은 판별 프로그램 점수가 아니다.** 어떤 프로그램이 쓰이는지 모르고, 알아도 그
점수를 여기서 재현할 수 없다. 재는 것은 **글이 얼마나 일반적인가** 뿐이고, 겹치는
까닭은 하나다 -- 그 프로그램이 지어낸 글을 알아보는 이유와 사람이 "누구나 쓸 수 있는
글" 이라고 느끼는 이유가 같기 때문이다. **전부 soft 다.** 통계값으로 사람의 글을
기각하면 그 자가 바로 오탐하는 판별 프로그램이 된다.

**J 는 사실을 보고 P 는 설득력을 본다.** J 는 원장이 정하고, P 는 원장이 없으면 못 잰다 --
P001 이 특히 그렇다. 앵커가 없어서 걸린 것인지 **원장이 없어서 앵커를 못 찾은 것**인지
가르지 않으면 그 판정은 거짓말이다. 그래서 원장이 비면 P001 은 위반이 아니라 미검증이다.

## 왜 J002 가 단위까지 보나

실측에서 배웠다. 수만 견주면 어떤 항목의 재는 법에 `30일치` 가 적혀 있는 것만으로
수 `30` 이 원장에 있는 것이 되고, 그러면 **지어낸 `매출 30% 향상` 이 통과한다.**
`30|일` 과 `30|%` 를 갈라야 잡힌다(`jaso/ledger.py` 의 `값앵커`).
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import item as IT                                           # noqa: E402
from jaso import ledger as LG                                         # noqa: E402
from jaso import swap as SW                                           # noqa: E402
from jaso import wording as WD                                        # noqa: E402

위반 = LG.위반

_연도 = re.compile(r"(20\d\d)\s*년")
_개월말 = re.compile(r"(\d+)\s*개월")
_해말 = re.compile(r"(\d+)\s*년\s*(?:간|동안|째|여)")
_명말 = re.compile(r"(\d+)\s*명")
_영문 = re.compile(r"[A-Za-z][A-Za-z0-9+#._-]{1,}")

# 영문이라고 다 기술 이름이 아니다. 이걸 안 빼면 J001 이 `A/B` · `IT` 같은 것을
# 계속 보고하고, 계속 보고하는 관문은 아무도 안 읽는다.
_영문흔한 = {"it", "ai", "ab", "a", "b", "ok", "vs", "etc", "ceo", "cto", "hr",
             "pdf", "ppt", "sw", "hw", "os", "pc", "ui", "ux", "qa", "kpi",
             "oj", "gpa", "toeic", "opic", "team", "the", "and", "for"}


@dataclass
class 답변:
    문항: IT.문항
    본문: str

    @property
    def 문단들(self) -> list:
        return SW.문단들(self.본문)


@dataclass
class 자소서:
    path: Path | None = None
    메타: dict = field(default_factory=dict)
    답변들: list = field(default_factory=list)

    @property
    def 회사(self) -> str:
        return self.메타.get("회사", "")

    @property
    def 직무(self) -> str:
        return self.메타.get("직무", "")

    @property
    def 이름(self) -> str:
        return self.path.name if self.path else "(글)"


def 읽기(글: str, path=None) -> 자소서:
    """front-matter + `## <문항> (700자)` 머리. `law/gate.py` 의 parse 와 같은 꼴이다."""
    raw, 메타 = 글 or "", {}
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            for line in raw[3:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    메타[k.strip()] = v.strip().strip('"').strip("'")
            raw = raw[end + 4:]
    답, cur = [], None
    for line in raw.splitlines():
        m = IT._머리.match(line)
        if m:
            cur = 답변(IT.쪼개기(m.group(2), m.group(1) or ""), "")
            답.append(cur)
        elif cur is not None:
            cur.본문 += line + "\n"
    for a in 답:
        a.본문 = a.본문.strip()
    return 자소서(Path(path) if path else None, 메타, 답)


def _어디(자: 자소서, a: 답변) -> str:
    return f"{자.이름} · 문항 {a.문항.번호 or '?'}"


def 원장말(L: LG.원장) -> set:
    """원장에 적힌 **모든 낱말**(소문자). J001 이 '원장 밖' 을 가릴 때 쓴다.

    앵커보다 넓다 -- 재는 법과 한 일에 적힌 말도 사용자가 실제로 적은 것이므로
    원장 밖이 아니다. **넓게 잡는 쪽으로 튼다**: 좁게 잡으면 성한 말이 계속 걸리고,
    그러면 관문이 아니라 잡음이 된다.
    """
    벌 = []
    for h in L.항목들:
        벌 += [h.이름, h.곳, h.갈래] + h.한일 + h.쓴것
        벌 += [m.무엇 + " " + m.어떻게 + " " + m.단위 for m in h.잰것]
    return {w.lower() for t in 벌 for w in re.split(r"[^\w+#.]+", str(t)) if w}


# ---------------------------------------------------------------- J 계열

def j001_근거실재(자: 자소서, L: LG.원장, **_) -> list:
    """J001 -- 원장에 없는 **해**와 **기술 이름**을 적었는가.

    해는 hard 다: 원장에 2024·2025 뿐인데 '2022년에' 라고 쓰면 그 경험이 원장에 없다.
    기술 이름은 soft 다 -- 일반 명사일 수 있고, 과잉 기각은 맞는 답도 버린다.
    """
    해들 = {y for h in L.항목들 for y in h.연도들}
    말들 = 원장말(L)
    out = []
    for a in 자.답변들:
        for y in sorted(set(_연도.findall(a.본문))):
            if y not in 해들:
                out.append(위반("J001", "hard", _어디(자, a),
                               f"{y}년을 적었는데 원장에는 그 해의 항목이 없다"
                               f" (원장의 해: {', '.join(sorted(해들)) or '없음'})"))
        for w in sorted({t for t in _영문.findall(a.본문)
                         if t.lower() not in _영문흔한}):
            if w.lower() not in 말들 and w.strip() not in (자.회사, 자.직무):
                out.append(위반("J001", "soft", _어디(자, a),
                               f"{w!r} 가 원장에 없다 -- 쓴 적이 없는 것을 적었으면 "
                               "면접에서 물어본다. 정말 썼으면 원장에 넣어라"))
    return out


def j002_수치일치(자: 자소서, L: LG.원장, **_) -> list:
    """J002 -- **잰 값을 주장한 자리**의 수가 원장의 그 값과 같은가. F1 이 잡히는 곳.

    성과 문맥의 수만 본다(`wording.성과수들`). '3학년' · '2025년' 은 값 주장이 아니다.
    판정은 세 갈래다.

        (수, 단위) 가 원장에 있다        통과
        수는 있는데 단위가 다르다        soft -- 같은 수를 다른 데서 가져왔을 수 있다
        수가 원장에 아예 없다            hard -- **지어낸 값이다**

    그리고 잰 방법이 안 적힌 값은 원장에 있어도 **못 쓴다**(E004 가 표를 달아 둔 것).
    안 잰 수를 쓰는 것이 자소서에서 제일 흔한 거짓말이다.
    """
    쌍 = {p for h in L.항목들 for p in LG.값앵커(h)}
    쓸수있는쌍 = {p for h in L.항목들 for p in LG.값앵커(h, 쓸수있는것만=True)}
    맨수 = {v for h in L.항목들 for v in LG.값수(h)}
    out = []
    for a in 자.답변들:
        for 수, 단위, 문장 in WD.성과수들(a.본문):
            key = f"{수}|{LG._단위(단위)}"
            머리 = re.sub(r"\s+", " ", 문장)[:50]
            if key in 쌍:
                if key not in 쓸수있는쌍:
                    out.append(위반("J002", "hard", _어디(자, a),
                                   f"{수}{단위} 는 원장에 있지만 **잰 방법이 안 적혀 "
                                   f"있다** -- 안 잰 수는 못 쓴다: {머리}…"))
                continue
            if 수 in 맨수:
                out.append(위반("J002", "soft", _어디(자, a),
                               f"{수} 는 원장에 있는데 단위가 다르다({단위}) -- "
                               f"다른 지표의 값을 가져왔는지 보라: {머리}…"))
            else:
                out.append(위반("J002", "hard", _어디(자, a),
                               f"**{수}{단위} 가 원장에 없다.** 지어낸 값이다: {머리}…"))
    return out


def j003_기간정합(자: 자소서, L: LG.원장, **_) -> list:
    """J003 -- 문단이 말하는 기간이 원장의 그 항목과 같은가.

    '6개월간' 을 '1년간' 으로 늘려 적는 것은 흔하고, 이력서와 대조되면 바로 걸린다.
    문단이 어느 항목을 말하는지는 앵커로 정한다(`swap.가리키는것`) -- 어림이므로
    가리키는 항목이 없으면 아무 말도 안 한다.
    """
    out = []
    for a in 자.답변들:
        for p in a.문단들:
            h = SW.가리키는것(p, L)
            if h is None or not h.개월:
                continue
            말한달 = ([int(x) for x in _개월말.findall(p)]
                     + [int(x) * 12 for x in _해말.findall(p)])
            for d in 말한달:
                if d != h.개월:
                    out.append(위반("J003", "hard", _어디(자, a),
                                   f"{d}개월이라 적었는데 원장의 [{h.id}] 는 "
                                   f"{h.개월}개월이다 ({'~'.join(h.언제)})"))
            for y in set(_연도.findall(p)):
                if y not in h.연도들:
                    out.append(위반("J003", "soft", _어디(자, a),
                                   f"[{h.id}] 를 말하는 문단인데 {y}년을 적었다 "
                                   f"(그 항목의 해: {', '.join(sorted(h.연도들))})"))
    return out


def j004_역할승격(자: 자소서, L: LG.원장, **_) -> list:
    """J004 -- 원장이 `참여`·`보조`·`관찰` 인데 본문이 `주도`·`총괄` 로 올려 썼는가.

    `law/wording.py` W005 를 그대로 옮긴 자리다. 법에서 '준용' 을 '적용' 으로 바꾸면
    다른 법이 되듯, 이력에서 '참여' 를 '주도' 로 바꾸면 **다른 사실**이 된다. 그리고
    이것은 면접에서 다시 물어보는 자리라 걸리면 그 자리에서 끝난다.
    """
    out = []
    for a in 자.답변들:
        for p in a.문단들:
            h = SW.가리키는것(p, L)
            if h is None or h.역할 == "주도":
                continue
            got = WD.승격(p)
            if got:
                out.append(위반("J004", "hard", _어디(자, a),
                               f"[{h.id}] 는 원장에 `{h.역할}` 인데 "
                               f"`{'`·`'.join(got)}` 로 적었다 -- 한 일이 달라진다. "
                               "정말 주도했으면 원장의 역할을 고쳐라"))
    return out


def j005_글자수(자: 자소서, L=None, **_) -> list:
    """J005 -- 문항이 정한 상·하한 안인가. **원장이 없어도 판정된다.**

    제출 폼이 자르는 자리다. 기계가 100% 판정하는데 사람이 100% 틀린다.
    """
    out = []
    for a in 자.답변들:
        q = a.문항
        n = WD.글자수(a.본문, q.공백포함)
        칸 = "공백 포함" if q.공백포함 else "공백 제외"
        if q.상한 and n > q.상한:
            out.append(위반("J005", "hard", _어디(자, a),
                           f"{n}자 ({칸}) -- 상한 {q.상한}자를 {n - q.상한}자 넘겼다. "
                           "제출 폼에서 잘린다"))
        elif q.하한 and n < q.하한:
            out.append(위반("J005", "hard", _어디(자, a),
                           f"{n}자 ({칸}) -- 하한 {q.하한}자에 {q.하한 - n}자 모자란다"))
        elif q.상한 and n < q.상한 * 0.7:
            out.append(위반("J005", "soft", _어디(자, a),
                           f"{n}자 ({칸}) -- 상한 {q.상한}자의 {n / q.상한:.0%}만 썼다. "
                           "칸을 남기면 할 말이 없다는 뜻으로 읽힌다"))
    return out


# 흔한 말은 '짚은 것' 후보에서 뺀다 -- 안 빼면 아무 문단이나 이어진 것으로 보인다.
_조사 = re.compile(r"(을|를|이|가|은|는|의|에|에서|으로|로|와|과|도|만|께|부터|까지)$")


def _고갱이(글: str, L: LG.원장) -> set:
    """문단의 뜻낱말 후보. **어림이다** -- 형태소 분석기를 안 쓴다."""
    out = set()
    for w in re.split(r"[^\w+#]+", 글 or ""):
        w = _조사.sub("", w)
        if len(w) >= 2 and w not in LG.흔한말 and not w.isdigit():
            out.add(w)
    return out


def j006_문항응답(자: 자소서, L: LG.원장, **_) -> list:
    """J006 -- 문항이 물은 것에 다 닿았는가. **`item.py` 가 쪼갠 요구를 그대로 본다.**

    **hard 는 "요구가 하나도 안 닿았다" 하나뿐이다.** 개별 요구는 soft 다.

    실측: 처음에 요구마다 hard 를 냈더니 성한 답변이 걸렸다 -- 문항이 "어려웠던
    경험" 을 묻는데 답변은 "사람이 계속 빠지는 문제를 만났습니다" 라고 썼다. 어려움을
    분명히 적었는데 표지말 목록에 그 표현이 없었을 뿐이다. **표지말은 어림이고, 어림
    으로 기각하면 맞는 답을 버린다**(`law/gate.py` 가 L005 를 soft 로 둔 자리와 같다).
    하나도 안 닿은 것은 어림이 아니라 사실이므로 그것만 hard 로 남긴다.

    이음 요건(F4)도 soft 다 -- 형태소 분석기 없이 어림으로만 보인다.
    """
    out = []
    for a in 자.답변들:
        찬것, 빈것 = [], []
        for r in a.문항.요구:
            if r.이음인가:
                continue
            (찬것 if (not r.표지 or re.search(r.표지, a.본문)) else 빈것).append(r)
        if 찬것:
            for r in 빈것:
                out.append(위반("J006", "soft", _어디(자, a),
                               f"[{r.id} {r.종류}] {r.말} -- 본문에서 그 자리를 "
                               "못 찾겠다 (표지말로만 보므로 놓칠 수 있다)"))
        elif 빈것:
            out.append(위반("J006", "hard", _어디(자, a),
                           f"요구 {len(빈것)}개 중 **하나도 안 닿았다** -- "
                           "이 답변은 문항이 물은 것에 답하지 않았다"))
        이음 = next((r for r in a.문항.요구 if r.이음인가), None)
        if 이음 and (ps := a.문단들):
            짚은것 = _고갱이(ps[0], L)
            경험쪽 = set()
            for p in ps[1:] or ps:
                if SW.앵커들(p, L):
                    경험쪽 |= _고갱이(p, L)
            if 짚은것 and 경험쪽 and not (짚은것 & 경험쪽):
                out.append(위반("J006", "soft", _어디(자, a),
                               "앞에서 짚은 것과 뒤에 든 경험에 겹치는 말이 하나도 "
                               "없다 -- **역량은 A 라 해 놓고 경험은 B 를 쓴 꼴**일 수 "
                               "있다. 짚은 말을 경험 서술에서 다시 써라"))
    return out


def j007_구조(자: 자소서, L=None, **_) -> list:
    """J007 -- 무엇이 달라졌는지가 있는가. soft.

    상황·행동은 대개 있고 **결과가 빈다.** 문항 종류에 따라 결과를 안 물을 수도 있어서
    soft 다 -- `law/gate.py` L005 가 soft 인 이유와 같다.
    """
    out = []
    for a in 자.답변들:
        if not WD.성과수들(a.본문) and not WD._성과동사.search(a.본문):
            out.append(위반("J007", "soft", _어디(자, a),
                           "무엇이 달라졌는지가 없다 -- 한 일만 있고 결과가 없으면 "
                           "읽는 사람이 기여를 못 잰다"))
    return out


def j008_자기모순(자: 자소서, L: LG.원장, **_) -> list:
    """J008 -- 한 벌 안에서 같은 경험에 서로 다른 수를 달았는가.

    한 문항만 읽으면 안 보이고 **한 벌로 읽어야 보인다** -- 그래서 관문이 한 벌
    단위로 돈다.

    ## 인원은 못 본다 -- 그렇게 적어 둔다

    처음에는 `N명` 도 봤다. 그랬더니 성한 문장이 걸렸다: 한 문단에 "실험군을
    **24000명**씩 두고" 와 "같이 일한 **4명** 중" 이 같이 나오는데, 앞은 표본 크기고
    뒤는 팀 크기다. **둘을 가르려면 뜻을 읽어야 하고, 이 관문은 뜻을 안 읽는다.**
    그래서 기간만 본다 -- 한 항목의 기간은 하나뿐이라 뜻을 안 읽어도 갈린다.
    """
    말한것 = {}
    for a in 자.답변들:
        for p in a.문단들:
            h = SW.가리키는것(p, L)
            if h is None:
                continue
            for v in _개월말.findall(p) + [str(int(y) * 12) for y in _해말.findall(p)]:
                말한것.setdefault((h.id, "개월"), {}).setdefault(v, []).append(
                    _어디(자, a))
    out = []
    for (hid, 자리), vals in sorted(말한것.items()):
        if len(vals) > 1:
            갈래 = " · ".join(f"{v}({vals[v][0].split('문항 ')[-1]}번 문항)"
                            for v in sorted(vals))
            out.append(위반("J008", "hard", 자.이름,
                           f"[{hid}] 의 {자리}를 문항마다 다르게 적었다: {갈래}"))
    return out


# ---------------------------------------------------------------- P 계열

def p001_치환(자: 자소서, L: LG.원장, **_) -> list:
    """P001 -- 회사 이름을 갈아 끼워도 그대로인가. **이 관문이 이 파일의 서명이다.**

    판정은 `jaso/swap.py` 가 세는 앵커로 한다. 회사·직무 이름은 앵커가 아니다 --
    그것이 바로 갈아 끼우는 자리이므로.
    """
    out = []
    for a in 자.답변들:
        잰것 = SW.재기(a.본문, L)
        if not 잰것["문단수"]:
            continue
        if not 잰것["앵커수"]:
            out.append(위반("P001", "hard", _어디(자, a),
                           "**원장에서 온 것이 하나도 안 박혀 있다** -- 회사 이름만 "
                           "바꾸면 어느 회사에나 들어가는 글이다"))
        elif 잰것["빈문단"] * 2 > 잰것["문단수"]:
            out.append(위반("P001", "soft", _어디(자, a),
                           f"문단 {잰것['문단수']}개 중 {잰것['빈문단']}개에 앵커가 "
                           "없다 -- 뼈대는 있는데 살이 일반론이다"))
    return out


def p002_주장근거(자: 자소서, L: LG.원장, **_) -> list:
    """P002 -- '열정적' · '책임감' 같은 자기 신고에 근거가 붙었는가. soft."""
    out = []
    for a in 자.답변들:
        for p in a.문단들:
            if WD.주장문장들(p) and not SW.앵커들(p, L):
                말 = WD.주장문장들(p)[0]
                out.append(위반("P002", "soft", _어디(자, a),
                               f"근거 없는 자기 신고: {re.sub(r'[|]s+', ' ', 말)[:44]}… "
                               "-- 같은 문단에 원장에서 온 것이 하나도 없다"))
    return out


def p003_상투(자: 자소서, L=None, **_) -> list:
    """P003 -- 돌려쓰는 말. soft. **사전은 실측으로 늘린다**(`jaso/wording.py`)."""
    out = []
    for a in 자.답변들:
        got = WD.상투(a.본문)
        if got:
            out.append(위반("P003", "soft", _어디(자, a),
                           f"상투구 {len(got)}개: {' · '.join(got[:6])}"))
    return out


def p004_수동(자: 자소서, L=None, **_) -> list:
    """P004 -- 행위자가 사라졌는가. soft. 문장 다섯에 하나를 넘으면 적는다."""
    out = []
    for a in 자.답변들:
        n, ss = WD.수동밀도(a.본문)
        if ss and n / ss > 0.2:
            out.append(위반("P004", "soft", _어디(자, a),
                           f"문장 {ss}개 중 {n}개가 수동·명사화다 ({n / ss:.0%}) -- "
                           "누가 했는지가 안 보이면 기여를 못 잰다"))
    return out


def p006_재탕(자: 자소서, L: LG.원장, **_) -> list:
    """P006 -- 여러 문항이 같은 경험을 돌려 쓰는가. soft.

    한 경험이 두 문항에 나오는 것 자체는 흔하고 문제가 아닐 수도 있다. 다만 **한 벌을
    통째로 읽는 사람에게는 재료가 하나뿐인 것으로 보인다.**
    """
    쓴것 = {}
    for a in 자.답변들:
        for p in a.문단들:
            h = SW.가리키는것(p, L)
            if h is not None:
                쓴것.setdefault(h.id, set()).add(a.문항.번호 or a.문항.원문[:12])
    out = []
    for hid, 문항들 in sorted(쓴것.items()):
        if len(문항들) > 1:
            out.append(위반("P006", "soft", 자.이름,
                           f"[{hid}] 하나를 문항 {len(문항들)}개에 썼다 "
                           f"({' · '.join(sorted(문항들))}) -- 재료가 하나뿐으로 보인다"))
    return out


# ---------------------------------------------------------------- D 계열 (일반성)

def d001_문장고름(자: 자소서, L=None, **_) -> list:
    """D001 -- 문장 길이가 다 비슷한가. soft.

    사람이 쓴 글은 짧은 문장과 긴 문장이 섞인다. 한 호흡으로 뽑아낸 글은 고르다.
    **판별 프로그램 점수를 예측하는 것이 아니다** -- 읽는 사람이 지루해하는 자리와
    그 프로그램이 보는 자리가 겹칠 뿐이다.
    """
    out = []
    for a in 자.답변들:
        c = WD.문장고름(a.본문)
        if c < 0.35 and len(WD.문장들(a.본문)) >= 5:
            out.append(위반("D001", "soft", _어디(자, a),
                           f"문장 길이가 고르다 (변동 {c:.2f}) -- 짧게 끊는 문장과 "
                           "길게 이어가는 문장이 섞이지 않았다"))
    return out


def d002_이음말(자: 자소서, L=None, **_) -> list:
    """D002 -- 이음말로 굴러가는가. soft. 하나씩은 멀쩡하고 몰려 있으면 군더더기다."""
    out = []
    for a in 자.답변들:
        n, ss = WD.이음밀도(a.본문)
        if ss >= 4 and n / ss > 0.5:
            out.append(위반("D002", "soft", _어디(자, a),
                           f"문장 {ss}개에 이음말이 {n}개다 -- '또한' · '이를 통해' 로 "
                           "굴러가는 글은 뺄 것이 많다는 뜻이다"))
    return out


def d003_고유밀도(자: 자소서, L: LG.원장, **_) -> list:
    """D003 -- 100자에 원장에서 온 것이 몇 개인가. soft. **P001 의 눈금판이다.**

    P001 은 있나 없나를 보고 여기는 얼마나인지를 본다. 앵커가 하나뿐인 1,000자는
    P001 을 통과하지만 읽는 사람에게는 여전히 일반론이다.
    """
    out = []
    for a in 자.답변들:
        n = len(a.본문)
        if n < 200:
            continue
        앵커 = SW.재기(a.본문, L)["앵커수"]
        밀도 = 앵커 * 100 / n
        if 밀도 < 1.0:
            out.append(위반("D003", "soft", _어디(자, a),
                           f"{n}자에 원장에서 온 것이 {앵커}종뿐이다 "
                           f"(100자당 {밀도:.1f}) -- 나머지는 누구나 쓸 수 있는 말이다"))
    return out


def d004_문단고름(자: 자소서, L=None, **_) -> list:
    """D004 -- 문단이 다 같은 크기인가. soft."""
    out = []
    for a in 자.답변들:
        ps = a.문단들
        c = WD.고름([len(p) for p in ps])
        if len(ps) >= 4 and c < 0.2:
            out.append(위반("D004", "soft", _어디(자, a),
                           f"문단 {len(ps)}개가 다 같은 크기다 (변동 {c:.2f}) -- "
                           "틀에 부은 것처럼 보인다"))
    return out


def d005_문항되풀이(자: 자소서, L=None, **_) -> list:
    """D005 -- 첫 문장이 문항을 되풀이하는가. soft. 칸만 먹는다."""
    out = []
    for a in 자.답변들:
        if WD.문항되풀이(a.본문):
            out.append(위반("D005", "soft", _어디(자, a),
                           "첫 문장이 문항을 되풀이한다 -- 읽는 사람은 문항을 이미 "
                           "안다. 그 자리에 첫 장면을 넣어라"))
    return out


검사들 = (d001_문장고름, d002_이음말, d003_고유밀도, d004_문단고름,
          d005_문항되풀이, j001_근거실재, j002_수치일치, j003_기간정합, j004_역할승격, j005_글자수,
          j006_문항응답, j007_구조, j008_자기모순, p001_치환, p002_주장근거,
          p003_상투, p004_수동, p006_재탕)

# 원장이 있어야 판정할 수 있는 것들. 원장이 비면 위반이 아니라 **미검증**이다.
원장필요 = {d003_고유밀도, j001_근거실재, j002_수치일치, j003_기간정합, j004_역할승격,
            j008_자기모순, p001_치환, p002_주장근거, p006_재탕}


def 검사(자: 자소서, L: LG.원장, jd=None) -> tuple:
    """(위반 목록, 대조한 주장 수, 못 한 주장 수).

    **미검증을 따로 두지 않는다.** 따로 두면 hard 도 soft 도 아닌 값이 되어 어느 셈에도
    안 잡히고 조용히 사라진다 -- `law/gate.py` 가 판례 미검증을 같은 칸에 실은 이유다.
    """
    vs, 대조, 미검증 = [], 0, 0
    for fn in 검사들:
        if fn in 원장필요 and not L:
            미검증 += 1
            continue
        vs.extend(fn(자, L))
    for a in 자.답변들:
        대조 += len(WD.성과수들(a.본문)) if L else 0
        미검증 += 0 if L else len(WD.성과수들(a.본문))
    if jd is None:
        미검증 += 1                      # P005 -- JD 원장이 없어 아직 아무도 안 봤다
    return vs, 대조, 미검증


def 판정(vs) -> tuple:
    hard = [v for v in vs if v.등급 == "hard"]
    soft = [v for v in vs if v.등급 == "soft"]
    if hard:
        return False, f"하드 위반 {len(hard)}건 (참고 soft {len(soft)}건)"
    return True, (f"통과 -- 다만 soft {len(soft)}건" if soft else "통과 -- 위반 없음")


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="자소서 기계 관문 (LLM 안 씀)")
    ap.add_argument("자소서")
    ap.add_argument("--표", dest="표", default="", help="경험 원장 JSON")
    ap.add_argument("--규칙", action="append", help="이 관문만 (예: --규칙 J002)")
    ap.add_argument("-v", "--verbose", action="store_true", help="soft 도 전부")
    a = ap.parse_args(argv)

    p = Path(a.자소서)
    if not p.exists():
        print(f"그런 파일이 없다: {p}", file=sys.stderr)
        return 3
    자 = 읽기(p.read_text(encoding="utf-8"), p)
    if not 자.답변들:
        print("문항을 못 찾았다 -- `## <문항> (700자)` 꼴이어야 한다", file=sys.stderr)
        return 3

    L = LG.읽기(a.표) if a.표 else LG.원장()
    if not L:
        print("**원장이 비어 있다 -- 사실 관문이 전부 미검증으로 빠진다.**")
        print("  여기서 나오는 '통과' 는 통과가 아니라 **아무도 안 본 것**이다.\n")
    else:
        무른것 = LG.hard(LG.검사(L))
        if 무른것:
            print("원장에 hard 위반이 있다 -- 판정이 뜻을 못 갖는다:", file=sys.stderr)
            for v in 무른것:
                print(f"  {v}", file=sys.stderr)
            return 1
        print(f"원장: 항목 {len(L)}개\n")

    vs, 대조, 미검증 = 검사(자, L)
    if a.규칙:
        vs = [v for v in vs if v.규칙 in a.규칙]
    hard = [v for v in vs if v.등급 == "hard"]
    soft = [v for v in vs if v.등급 == "soft"]
    ok, 요약 = 판정(vs)
    print(f"{자.이름} · 문항 {len(자.답변들)}개 -- {요약}")
    for v in hard + (soft if a.verbose else []):
        print(f"  {v}")
    print(f"\n{'=' * 62}")
    print(f"hard {len(hard)} · soft {len(soft)}")
    print(f"값 대조: 대조 {대조}건 · 미검증 {미검증}건"
          + ("  <- 원장·JD 를 채우면 이만큼이 검사 대상이 된다" if 미검증 else ""))
    if not a.verbose and soft:
        print("soft 를 보려면 -v")
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
