"""**무손실 수리 -- 잡았으면 고친다.**

앞 판은 복사를 잡고도 `"못 고친 N건은 장부에 적어 두고 원고는 그대로 쓴다"` 로
흘려보냈다. 실측: 같은 대목 다섯 줄 279자(전체의 17%)가 두 번 적힌 원고가 그대로
사용자에게 갔다. **재는 자는 멀쩡했고 그 값이 원고를 못 고쳤을 뿐이다.**

## 무엇을 고쳐도 되나

**여기서 고치는 것은 무손실인 것뿐이다.** 이 저장소의 규율은 "과잉 기각은 글을
없앤다" 인데, 그것은 **정도의 문제**에 대한 말이다. 아래는 정도의 문제가 아니다:

    되풀이   그 글 안에 이미 한 번 있는 줄을 지운다 -- 읽는 사람이 잃는 것이 없다
    무대 낱말 우리끼리 쓰는 말("화자")을 이름으로 바꾼다 -- 이름을 알 때만

정도의 문제(문장 길이 · 대사 몫)는 여기서 안 건드린다. 그것은 다음 회차에 말한다.
"""
from __future__ import annotations

import re

# 되풀이가 이 아래면 손대지 않는다. 후렴처럼 일부러 한 번 되풀이한 것까지 지우면
# 그것이야말로 과잉이다.
TOL = 0.06
# 이보다 짧은 줄은 되풀이로 안 센다. 같은 대사를 두 번 하는 것은 복사가 아니라 성격이다.
MIN = 12

_NORM = re.compile(r"[\s“”\"'‘’.,!?…·\-—()\[\]]+")

# **우리끼리 쓰는 말.** 프롬프트가 주인공을 "화자" 라 부르고 회차의 뼈대를 "비트" 라
# 부른다 -- 원고에 나올 이유가 없는 말이다. 실측: 사용자 원고 1,115자에 "화자" 일곱 번.
# 이름이 없으면 모델은 **우리가 부르는 말을 이름으로 쓴다.**
#
# 흔한 낱말은 안 넣는다 -- "주인공" 은 인물이 소설 얘기를 하다 쓸 수 있고 "쾌감" 은
# 그냥 낱말이다. 늑대소년이 되면 진짜 새는 자리가 묻힌다.
STAGE = ("화자", "비트", "갈고리", "전환점", "덩어리", "프롬프트", "원장", "회차")


def _norm(s: str) -> str:
    return _NORM.sub("", s)


def selfish(text: str) -> tuple:
    """그대로 복사한 줄의 몫과 그 줄들."""
    lines = [l.strip() for l in text.splitlines() if len(_norm(l)) >= MIN]
    seen, dup = set(), []
    for l in lines:
        n = _norm(l)
        (dup.append(l) if n in seen else None)
        seen.add(n)
    total = sum(len(l) for l in lines)
    return (sum(len(l) for l in dup) / total if total else 0.0), dup


def dedup(text: str) -> tuple:
    """복사한 줄을 지운다. 첫 번째는 남는다. (남은 글, 지운 글자수)"""
    if selfish(text)[0] <= TOL:
        return text, 0
    out, seen = [], set()
    for line in text.splitlines():
        n = _norm(line)
        if len(n) >= MIN:
            if n in seen:
                continue
            seen.add(n)
        out.append(line)
    kept = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    return kept, len(text) - len(kept)


def stage(text: str) -> list:
    """새어 나온 무대 뒤의 낱말. (낱말, 몇 번)"""
    return sorted([(w, text.count(w)) for w in STAGE if w in text], key=lambda x: -x[1])


def rename(text: str, who: str = "") -> tuple:
    """'화자' 를 이름으로 바꾼다. **이름을 알 때만** -- 모르면 손대지 않고 되먹임으로 넘긴다."""
    if not who or "화자" not in text:
        return text, 0
    n = text.count("화자")
    return text.replace("화자", who), n


# **비트를 옮겨 적은 자국.** 카드의 비트는 "…한다" 로 적혀 있고 원고는 과거형이다.
# 과거형 산문 사이의 현재형 요약문이 곧 베낀 자국이다(실측: 사용자 원고에 셋).
_NOW = re.compile(r"(?<![들][은는])[가-힣]{2,}(한다|된다|친다|온다|간다|본다|든다|난다|선다|._다)[.]$")


def copied(text: str, beats: list) -> list:
    """카드의 비트를 그대로 옮긴 문장들. 고칠 수는 없으니 **되먹임으로만** 넘긴다."""
    if not beats:
        return []
    keys = [set(re.findall(r"[가-힣]{2,}", str(b))) for b in beats if str(b).strip()]
    out = []
    for line in text.splitlines():
        for s in re.split(r"(?<=[.!?…])\s+", line.strip()):
            s = s.strip()
            if len(s) < 8 or not s.endswith("다."):
                continue
            w = set(re.findall(r"[가-힣]{2,}", s))
            for k in keys:
                if k and len(w & k) >= max(2, len(k) // 2):
                    out.append(s)
                    break
    return out


def run(text: str, who: str = "", beats=()) -> tuple:
    """무손실 수리를 다 건다. (고친 글, [무엇을 했나], [되먹임으로 넘길 것])"""
    did, owed = [], []
    text, cut = dedup(text)
    if cut:
        did.append(f"그대로 복사한 줄 {cut:,}자를 지웠다 -- 첫 번째만 남긴다")
    text, n = rename(text, who)
    if n:
        did.append(f"'화자' {n}번을 «{who}» 로 바꿨다")
    leak = stage(text)
    if leak:
        w, c = leak[0]
        owed.append(f"원고에 **무대 뒤의 낱말**이 나왔다 -- “{w}” {c}번."
                    " 그건 우리가 쓰는 말이지 이 세계의 낱말이 아니다."
                    " **사람을 이름이나 호칭으로 불러라.**")
    cp = copied(text, list(beats))
    if cp:
        owed.append(f"각본의 줄을 그대로 옮겨 적었다 ({len(cp)}군데). 예: “{cp[0][:34]}…”"
                    " **각본은 무슨 일이 벌어지는지 적어 둔 메모지 문장이 아니다** --"
                    " 사람이 움직이고 말하는 장면으로 풀어라.")
    return text, did, owed
