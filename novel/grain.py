"""**낱낱까지 재는 자** -- 한 작품에 맞출 때 쓴다.

profile.py 의 열아홉 축은 성기다. 문장 길이와 대사 몫이 맞아도 **낱말과 문법이 다르면**
다른 글이다. 여기서는 그 아래로 내려간다: 품사 분포 · 조사 · 어미 · 어휘의 다양성 ·
문장 성분의 순서.

형태소 분석기(kiwipiepy)가 있으면 그것으로 품사를 가른다. 없으면 **정규식으로 근사한다** --
없다고 아무것도 안 재는 것보다 거칠게라도 재는 편이 낫다. 어느 쪽으로 쟀는지는 함께 적는다.

**이 자는 한 작품을 겨눌 때만 쓴다.** 여러 작품의 평균에 대면 그 평균은 어느 작품의
것도 아니라서, 낱낱까지 맞추라는 요구가 아무 데도 없는 글을 만든다.
"""
from __future__ import annotations

import math
import re
from collections import Counter

# 조사 -- 한국어 문장의 뼈대. 이것의 분포가 문장 성분의 분포에 가깝다.
JOSA = ("은", "는", "이", "가", "을", "를", "의", "에", "에서", "에게", "와", "과",
        "도", "만", "로", "으로", "부터", "까지", "보다", "처럼", "라고", "이나")
# 연결어미 -- 문장을 어떻게 잇는가.
CONN = ("고", "며", "면서", "는데", "은데", "아서", "어서", "다가", "지만", "거나",
        "면", "니까", "려고", "도록", "듯이", "자")
# 종결어미 -- 문장을 어떻게 닫는가.
ENDS = ("다", "었다", "았다", "였다", "ㄴ다", "는다", "겠다", "것이다", "까", "지",
        "군", "구나", "네", "야", "라", "어", "죠", "요")

_TOKEN = re.compile(r"[가-힣]+")
_HANJA = re.compile(r"[一-鿿]")
_LATIN = re.compile(r"[A-Za-z]")
_DIGIT = re.compile(r"\d")


def _kiwi():
    try:
        from kiwipiepy import Kiwi
        return Kiwi()
    except Exception:
        return None


_K = None
_TRIED = False


def kiwi():
    global _K, _TRIED
    if not _TRIED:
        _K, _TRIED = _kiwi(), True
    return _K


def _dist(counts: Counter, keys) -> dict:
    tot = sum(counts.get(k, 0) for k in keys) or 1
    return {k: counts.get(k, 0) / tot for k in keys}


def _entropy(vals) -> float:
    ps = [p for p in vals if p > 0]
    if len(ps) < 2:
        return 0.0
    return -sum(p * math.log(p) for p in ps) / math.log(len(vals))


def pos_share(text: str) -> dict:
    """품사 몫. 분석기가 있으면 태그로, 없으면 꼴로 근사한다."""
    k = kiwi()
    if k is None:
        return {}
    got = Counter()
    for tok in k.tokenize(text):
        got[tok.tag[:2]] += 1
    tot = sum(got.values()) or 1
    keep = ("NN", "NP", "VV", "VA", "MA", "MM", "JK", "JX", "EF", "EC", "ET", "XS", "SF")
    return {f"pos_{t}": got.get(t, 0) / tot for t in keep}


# **줄과 줄 사이.** 문장 하나하나가 닮아도 **지문 뒤에 대사가 오는지, 대사가 몇 줄
# 이어지는지, 대사에 지문이 붙는지**가 다르면 다른 글로 읽힌다. 그것이 이 작품의
# 목소리다. 여기서는 줄의 갈래를 서술(n) 과 대사(t) 로 보고 그 이음을 센다.
_QLINE = re.compile(r'^\s*[\"\u201c\u2018\'(\[]')
_TAG = re.compile(r'[\"\u201d\u2019]\s*\S')     # 닫는 따옴표 뒤에 글자가 더 있다 = 지문이 붙었다


def _kind(line: str) -> str:
    return "t" if _QLINE.match(line.strip()) else "n"


def flow_shape(text: str) -> dict:
    """줄의 이음. 전이 확률과 대사 덩이의 길이."""
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) < 4:
        return {}
    ks = [_kind(l) for l in lines]
    pairs = list(zip(ks, ks[1:]))
    def p(a, b):
        tot = sum(1 for x, _y in pairs if x == a) or 1
        return sum(1 for x, y in pairs if x == a and y == b) / tot
    runs, cur = [], 0
    for k in ks:
        if k == "t":
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    talk = [l for l, k in zip(lines, ks) if k == "t"]
    tot_t = len(talk) or 1
    return {
        "n2t":      p("n", "t"),                       # 지문 다음에 대사가 올 확률
        "t2t":      p("t", "t"),                       # 대사 다음에 또 대사
        "t2n":      p("t", "n"),                       # 대사 다음에 지문
        "talk_run": (sum(runs) / len(runs)) if runs else 0.0,   # 대사가 몇 줄씩 이어지나
        "talk_max": max(runs) if runs else 0,
        "tag_rate": sum(bool(_TAG.search(l)) for l in talk) / tot_t,  # 대사에 지문이 붙은 몫
        "q_rate":   sum("?" in l for l in talk) / tot_t,
        "ex_rate":  sum("!" in l for l in talk) / tot_t,
        "ell_rate": sum(("…" in l or "..." in l) for l in talk) / tot_t,
        "talk_len2": sum(len(l.strip()) for l in talk) / tot_t,     # 대사 한 줄의 길이
        "open_t":   1.0 if ks[0] == "t" else 0.0,      # 이 토막이 대사로 여는가
        "close_t":  1.0 if ks[-1] == "t" else 0.0,     # 대사로 닫는가
    }


def measure(text: str) -> dict:
    """낱낱의 지문. 전부 비율이라 길이에 안 휘둘린다."""
    words = _TOKEN.findall(text)
    n = len(words) or 1
    josa = Counter()
    conn = Counter()
    ends = Counter()
    for w in words:
        for j in sorted(JOSA, key=len, reverse=True):
            if w.endswith(j) and len(w) > len(j):
                josa[j] += 1
                break
        for c in sorted(CONN, key=len, reverse=True):
            if w.endswith(c) and len(w) > len(c):
                conn[c] += 1
                break
    for s in re.split(r"[.!?…]", text):
        s = s.strip()
        if not s:
            continue
        for e in sorted(ENDS, key=len, reverse=True):
            if s.endswith(e):
                ends[e] += 1
                break

    uniq = len(set(words))
    out = {
        # **어휘의 다양성.** 같은 낱말을 얼마나 돌려쓰는가 -- 문체의 지문 중 제일 굵다.
        "ttr":      uniq / n,
        "hapax":    sum(1 for w, c in Counter(words).items() if c == 1) / max(1, uniq),
        "wordlen":  sum(len(w) for w in words) / n,
        # 조사 · 연결어미 · 종결어미가 얼마나 고르게 흩어졌는가
        "josa_var": _entropy(list(_dist(josa, JOSA).values())),
        "conn_var": _entropy(list(_dist(conn, CONN).values())),
        "end_var2": _entropy(list(_dist(ends, ENDS).values())),
        "josa_rate": sum(josa.values()) / n,
        "conn_rate": sum(conn.values()) / n,
        # 글자 종류 -- 한자 · 로마자 · 숫자를 얼마나 섞는가
        "hanja":    len(_HANJA.findall(text)) / max(1, len(text)),
        "latin":    len(_LATIN.findall(text)) / max(1, len(text)),
        "digit":    len(_DIGIT.findall(text)) / max(1, len(text)),
        "comma":    text.count(",") / max(1, len(text)) * 100,
        "quote":    (text.count('"') + text.count("“")) / max(1, len(text)) * 100,
        "dash":     (text.count("--") + text.count("—")) / max(1, len(text)) * 100,
    }
    for j in ("은", "는", "이", "가", "을", "를", "의", "에", "도", "만"):
        out[f"josa_{j}"] = josa.get(j, 0) / n
    out.update(pos_share(text))
    out.update(flow_shape(text))
    return out


def axes() -> list:
    """이 자가 내는 축 이름. 분석기 유무에 따라 달라진다.

    **줄이 몇 개는 있어야 줄 사이를 잰다.** 짧은 표본으로 물으면 flow_shape 가 빈
    것을 돌려주고, 그러면 이름 목록에서 대사 축이 통째로 빠진다."""
    probe = "\n".join(["가나다 라마바 사아자 차카타 파하."] * 3
                       + ['"어."', "타카파 차자아 사바마."] * 2)
    return sorted(measure(probe).keys())


def how() -> str:
    return "형태소 분석기" if kiwi() else "정규식 근사(kiwipiepy 를 깔면 품사까지 잰다)"
