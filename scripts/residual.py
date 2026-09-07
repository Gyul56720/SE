"""**재는 축으로 설명 안 되는 차이를 찾는다.** 빠진 축을 사람이 떠올리지 않게.

지금까지 축은 이렇게 늘었다: 사용자가 "대사도 특이하다" 고 하면 대사 축을 붙이고,
"편지" 라고 하면 삽입 칸을 붙였다. **말한 것만 재고 말 안 한 것은 영영 안 잰다.**
목록을 먼저 적어 두는 것으로는 모자랐다 -- 적을 때 떠오르지 않은 것은 목록에도
없었다(조판층이 통째로 빠져 있었다).

그래서 열거를 **생성이 아니라 검색**으로 바꾼다.

    원고가 재는 축을 전부 표본의 폭 안에 맞췄는데도 다르게 읽힌다면,
    **그 차이가 아직 축이 아닌 것**이다.

표본과 원고에서 낱말 · 어절 꼬리 · 문장 첫머리 · 말끝 · 글자 세 낱 · 줄 꼴 · 부호를
전부 세어 **차이가 큰 순으로** 세운다. 그리고 그중 이미 재는 축으로 설명되는 것
(조사 · 연결어미 · 종결어미 · 부호)을 걸러낸다. 남은 것이 **빠진 축의 후보**다.

    python3 scripts/residual.py novel/corpus/A novel/final.json
    python3 scripts/residual.py novel/corpus/A novel/drift.json --top 15

호출 0회. 견주는 자는 log-odds ratio(Monroe et al. 2008 의 결) -- 글 길이가 달라도
견줄 수 있고, 몇 번 안 나온 것이 위로 튀지 않는다.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import corpus, grain, rhythm                               # noqa: E402

# 이보다 적게 나온 것은 안 본다. 한두 번짜리는 차이가 아니라 우연이다.
MIN_N = int(__import__("os").environ.get("DRIFT_RESIDUAL_MIN", "5"))

_WORD = re.compile(r"[가-힣]+")
_PUNCT = re.compile(r"[^\w\s가-힣]")


def read(path) -> str:
    """폴더면 토막을 다 잇고, .json 이면 덩어리를 잇고, .txt 면 그대로."""
    p = Path(path)
    if p.is_dir():
        return "\n".join(corpus.load(f) for f in sorted(p.glob("*.txt")))
    if p.suffix == ".json":
        d = json.loads(p.read_text(encoding="utf-8"))
        return "\n".join(d.get("chunks") or [])
    return corpus.load(p)


def families(text: str) -> dict:
    """세는 갈래. **갈래를 갈라 세는 것이 중요하다** -- 다 섞으면 흔한 낱말이 위를
    덮고 문장 첫머리나 줄 꼴 같은 드문 자국이 안 보인다."""
    tell, talk = rhythm._lines(text)
    sents = [s for s in tell if s.strip()]
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    words = _WORD.findall(text)
    return {
        "낱말": Counter(words),
        "어절 꼬리": Counter(w[-2:] for w in words if len(w) >= 2),
        "문장 첫 어절": Counter(s.split()[0] for s in sents if s.split()),
        "말끝": Counter(s.rstrip()[-3:] for s in sents if len(s.rstrip()) >= 3),
        "글자 세 낱": Counter(w[j:j + 3] for w in words
                               for j in range(max(0, len(w) - 2))),
        "줄 첫 글자": Counter(l[0] for l in lines),
        "줄 끝 글자": Counter(l[-1] for l in lines),
        "부호": Counter(_PUNCT.findall(text)),
        "대사 첫 어절": Counter(t.strip('"“”\'‘’ ').split()[0]
                                for t in talk if t.strip('"“”\'‘’ ').split()),
    }


def logodds(a: Counter, b: Counter, prior: float = 0.5) -> list:
    """**어느 쪽에 얼마나 치우쳤나.** 몫의 차가 아니라 로그 승산비를 쓴다 -- 글 길이가
    달라도 견줄 수 있고, 흔한 것과 드문 것을 같은 자로 볼 수 있다."""
    keys = set(a) | set(b)
    # 분모는 **양쪽 낱말 가짓수를 합쳐** 잡는다. 한쪽에만 있는 것을 셀 때 그쪽
    # 가짓수만 쓰면 분모가 0이 되어 터진다(실측).
    v = len(keys)
    na = (sum(a.values()) or 1) + prior * v
    nb = (sum(b.values()) or 1) + prior * v
    out = []
    for k in keys:
        ca, cb = a.get(k, 0), b.get(k, 0)
        if ca + cb < MIN_N:
            continue
        la = math.log((ca + prior) / max(1e-9, na - ca - prior))
        lb = math.log((cb + prior) / max(1e-9, nb - cb - prior))
        var = 1 / (ca + prior) + 1 / (cb + prior)
        out.append(((la - lb) / math.sqrt(var), k, ca, cb))
    out.sort(reverse=True)
    return out


# 이미 재는 축으로 설명되는 것. 여기 걸리면 새 축 후보가 아니다 -- 그 축을 맞추면
# 따라 맞는다.
_KNOWN = set(grain.JOSA) | set(grain.CONN) | set(grain.ENDS) | set(".,!?…\"'“”‘’-—()[]")


def known(kind: str, tok: str) -> str:
    if kind == "부호" and tok in _KNOWN:
        return "부호 축"
    if kind == "어절 꼬리" and tok in _KNOWN:
        return "조사·어미 축"
    if kind == "말끝" and any(tok.endswith(e) for e in grain.ENDS):
        return "종결어미 축"
    return ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sample", help="표본(폴더 · txt)")
    ap.add_argument("draft", help="우리 원고(json · txt · 폴더)")
    ap.add_argument("--top", type=int, default=10, help="갈래마다 몇 개씩")
    ap.add_argument("--all", action="store_true", help="이미 재는 축까지 다 보여준다")
    a = ap.parse_args(argv)

    sa, dr = read(a.sample), read(a.draft)
    if not sa.strip() or not dr.strip():
        print("읽을 글이 없다", file=sys.stderr)
        return 1
    print(f"표본 {len(sa):,}자 · 원고 {len(dr):,}자 (적어도 {MIN_N}번 나온 것만 본다)\n")

    fa, fd = families(sa), families(dr)
    for kind in fa:
        rows = logodds(fa[kind], fd[kind])
        if not rows:
            continue
        rows = [r for r in rows if a.all or not known(kind, r[1])]
        # **부호로 가른다.** 위에서 잘라 뒤집으면 같은 것이 양쪽에 나온다(실측).
        pos = [r for r in rows if r[0] > 1.0][:a.top]
        neg = [r for r in rows if r[0] < -1.0][-a.top:][::-1]
        if not pos and not neg:
            continue
        print(f"[{kind}]")
        for tag, part in (("표본에 짙다", pos), ("원고에 짙다", neg)):
            got = [f"{k}({ca}:{cb})" + (f" ←{known(kind, k)}" if known(kind, k) else "")
                   for _z, k, ca, cb in part]
            print(f"  {tag}: " + (" · ".join(got) if got else "이렇다 할 것이 없다"))
        print()

    print("읽는 법: **표본에만 짙은데 이미 재는 축으로 설명 안 되는 것**이 빠진 축의")
    print("후보다. 괄호는 (표본 횟수:원고 횟수). 후보를 축으로 만들기 전에 그것이")
    print("작품을 실제로 가르는지 먼저 본다 -- 못 가르는 자는 토큰만 먹는다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
