"""**인물끼리 말이 얼마나 다른가.** 시켜 놓고 안 재던 것을 잰다.

`flow` 는 인물 카드에 **말투**를 적어 두고 다음 덩어리부터 그대로 말하게 시킨다.
그런데 그것이 지켜졌는지 재는 자가 없었다 -- 시키기만 하고 안 재는 요구는 이 저장소가
스스로 금지한 것이다(`DATA.md`: "못 재는 것은 프롬프트에도 안 쓴다"). 사용자 평
2026-09-07: *"대사가 너무 별로였다."*

**방법은 문헌에서 가져왔다**(`EVIDENCE.md` 10절) -- From stage to page: language
independent bootstrap measures of distinctiveness in fictional speech
(arXiv 2301.05659 → *Computational Drama Analysis*, de Gruyter 2024). 인물의 말을
**문자 3-gram 분포**로 두고 그 사이의 거리를 잰다. 세 가지가 우리에게 맞다:

  · **언어 독립적**이다 -- 한국어 형태소 분석기가 없어도 된다
  · **한 작품 안에서만** 계산한다 -- 표본도 외부 말뭉치도 다른 작가와의 비교도 필요 없다
  · 문자 3-gram 이라 **말끝 · 호칭 · 말버릇 · 사투리**를 같이 잡는다. 그것이 곧 말투다

## 표본 크기가 거리를 부풀린다 -- 그래서 부트스트랩이다

대사 열 줄로 잰 3-gram 분포와 백 줄로 잰 것은 애초에 다르다. 두 인물의 대사 수가
다르면 **말투가 같아도 거리가 나온다.** 그래서 논문이 부트스트랩을 쓴다.

    사이 거리   A 의 대사와 B 의 대사가 얼마나 다른가
    안 거리     **A 의 대사를 둘로 갈랐을 때** 얼마나 다른가 (= 우연히 생기는 거리)

    벌어짐 = 사이 거리 / 안 거리

**1.0 이면 구별이 안 된다** -- 두 사람의 차이가 한 사람을 둘로 가른 것과 같다는 뜻이다.
클수록 말투가 다르다. 표본 크기의 효과는 분자와 분모에 똑같이 실리므로 나눌 때 지워진다.

## 한계 -- **절대값을 원고끼리 견주지 마라**

실측: 같은 원고를 표본만 두 배로 하니 2.748 → 4.823 이 됐다. 표본이 커지면 안 거리는
0 으로 수렴하는데 사이 거리는 참값으로 수렴하므로, **말투가 진짜 다르면 비율이 계속
커진다.** 그러니 "이 원고는 3.1, 저 원고는 4.4" 같은 비교는 뜻이 없다.

안정적인 것은 **1.0 언저리인가** 하나뿐이다. 말투가 같으면 표본이 얼마든 1.0 근처에
머문다(실측 0.86 · 1.16 · 1.48). 우리가 알고 싶은 것이 정확히 그것이라 이걸로 충분하다 --
**구별이 되는가 안 되는가**. "얼마나 잘 되는가" 는 이 자가 답하지 않는다.

## 누가 한 말인지는 보수적으로만 정한다

귀속을 틀리면 두 인물의 말이 섞여서 **말투가 같다는 잘못된 답**이 나온다. 애매하면
버리는 쪽이 낫다 -- 표본이 줄 뿐이지만, 섞이면 수 자체가 거짓이 된다. 그래서 셋만 본다:

    "..." 하고 민아가 말했다.      같은 줄의 꼬리
    민아가 잔을 내려놓았다.        바로 앞 지문
    "..."                          바로 뒤 지문

이름이 **정확히 하나** 잡힐 때만 귀속하고, 없거나 둘 이상이면 버린다.

실행:
    python3 novel/voicegap.py novel/drift.json
    python3 novel/voicegap.py novel/drift.json --last 12      # 끝의 몇 덩어리만
    python3 novel/voicegap.py novel/drift.json --json out.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os

N = 3                    # 문자 n-gram
# **바닥을 둔다.** 대사 몇 줄로 잰 3-gram 분포는 그 사람의 말투가 아니라 그 몇 줄이다.
# 줄 수와 글자 수를 같이 보는 것은, 여섯 줄이 전부 "네." 일 수 있어서다.
MIN_LINES = int(os.environ.get("DRIFT_VG_MIN_LINES", "6"))
MIN_CHARS = int(os.environ.get("DRIFT_VG_MIN_CHARS", "120"))
ROUNDS = int(os.environ.get("DRIFT_VG_ROUNDS", "40"))
# **되밀기 문턱.** 이 밑이면 "말투가 구별 안 된다" 고 되먹인다. 1.0 이 이론적 기준점이고
# 여기에 여유를 얹었다 -- 시험 표본에서 말투가 같을 때 0.86~1.48 이 나왔다.
# **이것은 잰 값이 아니라 운영점이다.** 실제 원고가 쌓이면 거기서 다시 정한다.
FLOOR = float(os.environ.get("DRIFT_VG_FLOOR", "1.5"))
SEED = "voicegap"        # **재현된다.** 같은 원고면 같은 수가 나와야 되먹임을 믿는다

_QUOTE_OPEN = '"“‘\''
_QUOTE_CLOSE = '"”’\''
# 이름 앞에 붙어 있으면 그 이름이 아니다(예: '수민' 안의 '민'). 뒤는 조사가 붙으므로 안 본다.
_HANGUL = re.compile(r"[가-힣]")


# ------------------------------------------------------------------ 귀속

def _split_line(line: str):
    """대사 줄이면 (대사, 꼬리 지문), 아니면 (None, 줄 전체)."""
    s = line.strip()
    if not s or s[0] not in _QUOTE_OPEN:
        return None, s
    # 닫는 따옴표를 뒤에서 찾는다 -- 대사 안에 따옴표가 또 있을 수 있다.
    for i in range(len(s) - 1, 0, -1):
        if s[i] in _QUOTE_CLOSE:
            return s[1:i], s[i + 1:].strip()
    return s[1:], ""          # 안 닫혔으면 줄 전체가 대사다


def _find_name(text: str, names) -> str:
    """텍스트에서 아는 이름을 찾는다. **정확히 하나일 때만** 돌려준다.

    긴 이름부터 본다 -- '수민' 이 있는데 '민' 을 먼저 잡으면 엉뚱한 사람이 된다.
    그리고 이름 **앞**이 한글이면 다른 낱말의 일부다. 뒤는 조사가 붙으므로 안 본다."""
    hit = set()
    for nm in sorted(names, key=len, reverse=True):
        start = 0
        while True:
            i = text.find(nm, start)
            if i < 0:
                break
            if i == 0 or not _HANGUL.match(text[i - 1]):
                hit.add(nm)
                break
            start = i + 1
    return hit.pop() if len(hit) == 1 else ""


def by_speaker(text: str, names) -> dict:
    """{인물: [대사, ...]}. **애매하면 버린다.**"""
    names = [n for n in names if n and len(n) >= 2]
    lines = [l for l in text.splitlines()]
    out: dict = {}
    for i, line in enumerate(lines):
        said, tail = _split_line(line)
        if said is None or not said.strip():
            continue
        who = _find_name(tail, names) if tail else ""
        if not who:                                   # 바로 앞 지문
            for j in range(i - 1, -1, -1):
                prev = lines[j].strip()
                if not prev:
                    continue
                if _split_line(prev)[0] is None:
                    who = _find_name(prev, names)
                break
        if not who:                                   # 바로 뒤 지문
            for j in range(i + 1, len(lines)):
                nxt = lines[j].strip()
                if not nxt:
                    continue
                if _split_line(nxt)[0] is None:
                    who = _find_name(nxt, names)
                break
        if who:
            out.setdefault(who, []).append(said.strip())
    return out


# ------------------------------------------------------------------ 거리

def grams(texts) -> Counter:
    c: Counter = Counter()
    for t in texts:
        s = " " + re.sub(r"\s+", " ", t).strip() + " "
        for i in range(len(s) - N + 1):
            c[s[i:i + N]] += 1
    return c


def jsd(a: Counter, b: Counter) -> float:
    """옌센-섀넌 발산. 0~1 이고 대칭이며 없는 칸에서 안 터진다."""
    na, nb = sum(a.values()), sum(b.values())
    if not na or not nb:
        return 1.0
    out = 0.0
    for k in set(a) | set(b):
        p, q = a.get(k, 0) / na, b.get(k, 0) / nb
        m = (p + q) / 2
        if p:
            out += p * math.log2(p / m) / 2
        if q:
            out += q * math.log2(q / m) / 2
    return max(0.0, min(1.0, out))


def _rng(*parts) -> random.Random:
    h = hashlib.sha256("|".join(str(p) for p in (SEED, *parts)).encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def _pair(a, b, who_a, who_b) -> tuple:
    """한 쌍의 (사이 거리, 안 거리). **둘을 같은 표본 크기로 잰다.**

    처음엔 안 거리를 반쪽끼리(12 대 12), 사이 거리를 통째로(24 대 24) 쟀다. 3-gram
    분포는 표본이 작을수록 서로 멀어지므로 **안 거리만 부풀었고**, 말투가 같은 두 인물이
    0.4 로 나왔다(실측). 1.0 이 나와야 하는 자리다 -- 자가 편향돼 있었던 것이다.

    그래서 넷 다 같은 크기 h 로 뽑는다: A 를 A1·A2 로, B 를 B1·B2 로 가르고
    안 거리는 d(A1,A2) 와 d(B1,B2), 사이 거리는 d(A1,B1). 크기가 같으니 나눌 때
    표본 효과가 지워진다."""
    h = max(2, min(len(a), len(b)) // 2)
    r = _rng("pair", who_a, who_b, h)
    btw = win = 0.0
    for _ in range(ROUNDS):
        ia, ib = list(range(len(a))), list(range(len(b)))
        r.shuffle(ia); r.shuffle(ib)
        A1 = [a[i] for i in ia[:h]]; A2 = [a[i] for i in ia[h:h * 2]]
        B1 = [b[i] for i in ib[:h]]; B2 = [b[i] for i in ib[h:h * 2]]
        btw += jsd(grams(A1), grams(B1))
        win += (jsd(grams(A1), grams(A2)) + jsd(grams(B1), grams(B2))) / 2
    return btw / ROUNDS, win / ROUNDS


def measure(text: str, names) -> dict:
    """{'voice_gap': 벌어짐, 'pairs': [...], 'speakers': n, 'lines': n, 'skipped': [...]}"""
    said = by_speaker(text, names)
    kept, skipped = {}, []
    for who, ls in said.items():
        if len(ls) >= MIN_LINES and sum(len(x) for x in ls) >= MIN_CHARS:
            kept[who] = ls
        else:
            skipped.append(who)
    out = {"speakers": len(kept), "lines": sum(len(v) for v in kept.values()),
           "skipped": sorted(skipped), "pairs": [], "voice_gap": None}
    if len(kept) < 2:
        return out                     # **잴 수 없으면 없다고 한다.** 0 으로 채우지 않는다
    names_k = sorted(kept)
    for i, a in enumerate(names_k):
        for b in names_k[i + 1:]:
            btw, base = _pair(kept[a], kept[b], a, b)
            out["pairs"].append({"a": a, "b": b, "between": round(btw, 4),
                                 "within": round(base, 4),
                                 "gap": round(btw / base, 3) if base > 0 else None})
    got = sorted(p["gap"] for p in out["pairs"] if p["gap"] is not None)
    if got:
        out["voice_gap"] = round(got[len(got) // 2], 3)      # 가운뎃값
    return out


# ------------------------------------------------------------------ 원고에서

def from_book(path, last: int | None = None) -> dict:
    book = json.loads(Path(path).read_text(encoding="utf-8"))
    chunks = list(book.get("chunks") or [])
    if last:
        chunks = chunks[-last:]
    names = list((book.get("ledger") or {}).get("people") or {})
    return measure("\n".join(chunks), names)


def table(m: dict) -> str:
    if not m.get("speakers"):
        return "귀속된 대사가 없다 -- 지문에 이름이 안 나오거나 원장이 비어 있다."
    if m["voice_gap"] is None:
        return (f"잴 수 있는 인물이 {m['speakers']}명뿐이다 (둘은 있어야 한다).\n"
                f"  대사가 적어 뺀 인물: {', '.join(m['skipped']) or '없음'}")
    rows = [f"인물 {m['speakers']}명 · 귀속된 대사 {m['lines']}줄"
            + (f" · 적어서 뺀 인물 {len(m['skipped'])}명" if m["skipped"] else ""),
            "",
            f"  **벌어짐 {m['voice_gap']}**  (1.0 = 한 사람을 둘로 가른 것과 같다"
            " = 말투가 구별 안 된다)",
            ""]
    for p in sorted(m["pairs"], key=lambda x: x["gap"] or 0):
        rows.append(f"    {p['a']} ↔ {p['b']:8s}  벌어짐 {p['gap']}"
                    f"   (사이 {p['between']} / 안 {p['within']})")
    return "\n".join(rows)


def brief(book: dict, last: int = 8) -> str:
    """**프롬프트에 얹을 되먹임.** 구별이 안 될 때만 말한다.

    기각하지 않는다 -- C층 지표에 기각 권한을 주지 않는 것은 이 저장소가 관문 열셋을
    없애며 산 교훈이고, 4만 편에서 구조 준수와 인기가 무관했다는 결과가 그 근거다
    (SUCCESS.md · EVIDENCE.md 1절). 여기서는 **어느 둘이 같게 들리는지만** 짚는다.

    이름만 싣는다. 대사 원문은 안 싣는다(DATA.md)."""
    chunks = list(book.get("chunks") or [])
    if len(chunks) < 2:
        return ""
    names = list((book.get("ledger") or {}).get("people") or {})
    if len(names) < 2:
        return ""
    m = measure("\n".join(chunks[-last:]), names)
    if m["voice_gap"] is None or m["voice_gap"] >= FLOOR:
        return ""
    near = min((p for p in m["pairs"] if p["gap"] is not None),
               key=lambda p: p["gap"], default=None)
    if not near:
        return ""
    return ("[말투] **두 사람이 같은 목소리로 말한다.**\n"
            f"  · 지금 제일 겹치는 둘: **{near['a']}** 와 **{near['b']}**\n"
            "  · [세계]의 인물 카드에 적힌 **말투**대로 갈라라. 나이 · 자란 데 · 자리가"
            " 다르면 같은 문장을 안 쓴다.\n"
            "  · 갈리는 자리는 **말끝 · 호칭 · 길이**다 -- 누구는 끝을 흐리고 누구는"
            " 끊는다. 누구는 직함으로 부르고 누구는 이름을 부른다. 누구는 한 문장,"
            " 누구는 세 문장.\n"
            "  · 지문으로 설명하지 마라. **대사 자체가 누구 것인지 말해야** 한다.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="인물끼리 말이 얼마나 다른가")
    ap.add_argument("path", help="drift.json")
    ap.add_argument("--last", type=int, default=0, help="끝의 몇 덩어리만 (0=전부)")
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    m = from_book(a.path, a.last or None)
    print(f"방법: 문자 {N}-gram 분포의 부트스트랩 거리 (EVIDENCE.md 10절)\n")
    print(table(m))
    if a.json:
        Path(a.json).write_text(json.dumps(m, ensure_ascii=False, indent=1),
                                encoding="utf-8")
        print(f"\n-> {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
