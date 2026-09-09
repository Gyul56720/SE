"""**자 -- 재고, 밴드를 내고, 무엇이 틀렸는지 말한다.**

## 밴드는 잰 것에서만 나온다

앞 판이 여기서 죽었다. 표본이 **다른 갈래**였다 -- `sent_len` 가운뎃값 22.58 인데
실제 웹소설 1화는 **47.6** 이었다. 폭이 19.76~59.34 라 우리 26.1 도 "정상" 이었고,
그래서 아무도 늘리라고 안 하면서 동시에 22.58 로 끌고 있었다. 그것이 "문장이 짧고
단조롭다" 의 기전 전부다.

그래서 nv2 는 **`ref.json` 에 표본이 없는 축에는 밴드를 안 준다.** 밴드가 없으면
규칙이 아니고, 규칙이 아니면 프롬프트에 실리지 않는다. 짐작한 수는 못 들어온다.

표본이 하나뿐이면 폭도 하나에서 나온다 -- 그래서 **±`WIDE`** 로 넉넉히 준다.
표본이 늘면 10~90% 폭으로 바뀐다.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

REF = Path(__file__).resolve().parent / "ref.json"

# 표본 하나에서 폭을 낼 때 쓰는 여유. 한 점에서 좁게 내면 그것은 잰 것이 아니라
# 그 점을 박는 것이다.
WIDE = 0.25
# `names` 만 더 넉넉히 -- 한 편의 등장인물 수는 편차가 크다.
EXTRA = {"names": 0.5}

_QUOTE = re.compile(r'^\s*["“”「『]')
_SPLIT = re.compile(r"(?<=[.!?…。])\s+")
_ENDS = {
    "다": re.compile(r"다[.!?…]"), "까": re.compile(r"[까냐니][?.]"),
    "군": re.compile(r"[군네지][.!…]"), "것": re.compile(r"것[이었]?다[.]"),
    "명사": re.compile(r"[가-힣][^\s]{0,6}(음|함|기|것|뿐|채|말|뿐)[.]"),
}


def _lines(text: str):
    """서술 줄과 대사 줄로 가른다. **대사는 제 줄에 있어야 대사로 센다.**"""
    tell, talk = [], []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        (talk if _QUOTE.match(s) else tell).append(s)
    return tell, talk


def _sents(tell: list) -> list:
    out = []
    for line in tell:
        out += [s.strip() for s in _SPLIT.split(line) if s.strip()]
    return out


def _entropy(counts) -> float:
    tot = sum(counts)
    ps = [c / tot for c in counts if c > 0]
    if tot <= 0 or len(ps) < 2:
        return 0.0
    return -sum(p * math.log(p) for p in ps) / math.log(len(counts))


# **이름 대용.** 한국어에는 대문자가 없어서 고유명사를 꼴로만 가려야 한다.
#
# 첫 판은 "두 번 넘게 나오는 두~네 글자" 로 셌다가 `속에서` · `낮게` · `위로` · `몸을`
# 을 이름으로 잡았다(실측 2026-09-09). **잘못 답하는 자는 없느니만 못하다** -- 그
# 수를 믿고 "이름을 줄여라" 를 부치면 멀쩡한 원고를 망가뜨린다.
#
# 그래서 조건을 둘 건다: 조사를 뗀 **몸통**이 두 번 넘게 나오고, **서로 다른 격조사
# 둘 이상**과 붙는다. 사람과 자리는 여러 격으로 쓰이지만 부사어는 한 꼴로만 쓰인다.
_JOSA = ("이가", "가", "이", "은", "는", "을", "를", "의", "에게", "께", "께서", "과", "와",
         "도", "만", "밖에", "이라", "라고", "이야", "야", "님", "씨")
# 몸통이 이것으로 끝나면 이름이 아니다 -- 조사를 떼고도 남는 부사·동사 꼬리.
_NOT = ("에서", "으로", "면서", "지만", "니까", "어서", "아서", "하게", "게", "듯", "처럼",
        "같이", "보다", "까지", "부터", "마다", "조차", "라도", "든지")


def _stem(word: str) -> str:
    for j in sorted(_JOSA, key=len, reverse=True):
        if word.endswith(j) and len(word) - len(j) >= 2:
            return word[: -len(j)], j
    return word, ""


def _names(text: str) -> list:
    """여러 격으로 도는 몸통 = 이름 대용. (천 자당 수는 부르는 쪽에서 나눈다)"""
    seen: dict = {}
    for w in re.findall(r"[가-힣]{2,}", text):
        st, j = _stem(w)
        if len(st) < 2 or len(st) > 4 or st.endswith(_NOT):
            continue
        d = seen.setdefault(st, {"n": 0, "j": set()})
        d["n"] += 1
        if j:
            d["j"].add(j)
    return [k for k, d in seen.items() if d["n"] >= 3 and len(d["j"]) >= 2]


def measure(text: str) -> dict:
    """비율만 담는다 -- 길이에 안 휘둘려야 견줄 수 있다."""
    text = (text or "").strip()
    if not text:
        return {}
    tell, talk = _lines(text)
    sents = _sents(tell)
    if not sents:
        return {"dialog": 1.0 if talk else 0.0, "chars": len(text)}
    lens = [len(s) for s in sents]
    mean = sum(lens) / len(lens)
    var = sum((x - mean) ** 2 for x in lens) / len(lens)
    paras = [p for p in text.split("\n") if p.strip()]
    turning = _names(text)
    return {
        "sent_len": mean,
        "sent_var": (var ** 0.5) / mean if mean else 0.0,
        "short": sum(1 for x in lens if x < 20) / len(lens),
        "da_share": sum(1 for s in sents if s.rstrip('"”’\'').endswith(("다.", "다!", "다?"))) / len(sents),
        "end_var": _entropy([len(rx.findall(text)) for rx in _ENDS.values()]),
        "dialog": len(talk) / max(1, len(tell) + len(talk)),
        "names": len(turning) / max(1, len(text) / 1000),
        "para_len": sum(len(p) for p in paras) / max(1, len(paras)),
        "chars": len(text),
    }


# ---------------------------------------------------------------- 표본과 밴드

def samples() -> list:
    try:
        return json.loads(REF.read_text(encoding="utf-8")).get("표본") or []
    except Exception:
        return []


def _mid(vals: list):
    vals = sorted(v for v in vals if isinstance(v, (int, float)))
    if not vals:
        return None
    n = len(vals)
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2


def band(axis: str):
    """(하한, 상한). **표본이 없으면 None** -- 그러면 규칙이 아니다."""
    got = [s[axis] for s in samples() if isinstance(s.get(axis), (int, float))]
    if not got:
        return None
    if len(got) >= 5:                       # 표본이 늘면 10~90% 폭으로
        got = sorted(got)
        return (got[len(got) // 10], got[-1 - len(got) // 10])
    m = _mid(got)
    w = WIDE + EXTRA.get(axis, 0.0)
    return (round(m * (1 - w), 2), round(m * (1 + w), 2))


def gap(v: float, lo: float, hi: float) -> float:
    """밴드 폭으로 나눈 거리. 축이 달라도 견줄 수 있게."""
    span = max(hi - lo, 1e-9)
    return (lo - v) / span if v < lo else (v - hi) / span if v > hi else 0.0


def record(name: str, m: dict, where: str = "") -> int:
    """잰 것을 표본에 더한다. 같은 이름이면 갈아 끼운다."""
    try:
        doc = json.loads(REF.read_text(encoding="utf-8"))
    except Exception:
        doc = {"_": "실제 1화를 잰 것.", "표본": []}
    from datetime import date
    row = {"이름": name, "언제": date.today().isoformat(), "출처": where}
    row.update({k: (round(v, 2) if isinstance(v, float) else v) for k, v in m.items()})
    doc["표본"] = [s for s in doc.get("표본") or [] if s.get("이름") != name] + [row]
    REF.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return len(doc["표본"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="재고, 표본과 견준다")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--기록", dest="keep", default="", help="표본으로 남긴다(이름)")
    a = ap.parse_args(argv)
    rows = []
    for f in a.files:
        p = Path(f)
        if not p.exists():
            print(f"없는 파일: {f}", file=sys.stderr)
            return 2
        m = measure(p.read_text(encoding="utf-8"))
        rows.append((p.stem, m))
        if a.keep:
            print(f"표본에 남겼다 -- 이제 {record(a.keep, m, f'ruler --기록 ({p.name})')}편",
                  file=sys.stderr)
    axes = ["sent_len", "sent_var", "short", "da_share", "dialog", "names", "para_len", "chars"]
    print("  " + "축".ljust(10) + "".join(n[:10].rjust(12) for n, _ in rows) + "밴드".rjust(16))
    for k in axes:
        b = band(k)
        line = "  " + k.ljust(10)
        for _, m in rows:
            line += (f"{m[k]:,.2f}" if k in m else "-").rjust(12)
        line += (f"{b[0]:.2f}~{b[1]:.2f}" if b else "(표본 없음)").rjust(16)
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
