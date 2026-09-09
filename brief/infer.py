"""**나열에서 추론으로.** 명제를 세우고 기준선과 견준다. LLM 호출 0회.

    "코스피 +1.44%"                        <- 나열. 원장을 다시 말한 것이다
    "평균 +0.09%, 표준편차 1.02"            <- 이것도 나열이다. 원장의 요약일 뿐
    "이 움직임은 최근 250일에서 상위 3%,
     명제 6개 보정 후 p=0.18 -- **평범하다**"  <- 추론. 기준선이 있고 판정이 있다

## 무엇이 추론인가 -- 이 저장소가 이미 세 번 답했다

    law         원고/피고 쪽을 각각 돌려 **결론이 갈리는 자리**를 계산하고 뒤집어 본다
    lol         승률을 **기준선과 견준다.** 못 이기면 못 이겼다고 적는다
    mathdrift   유도 사슬이 이어지는가를 sympy 가 판정한다. 미정은 미정이라 한다

셋 다 같은 꼴이다: **명제 · 기준선 · 기계 판정 · 그리고 못 하겠으면 못 하겠다고 한다.**
여기서도 그것만 한다.

## 판정은 셋이고, **`못잼` 이 제일 자주 나온다**

| | |
|---|---|
| `이례` | 기준선 아래서 이만한 일이 일어나기 어렵다 |
| `평범` | 기준선으로 설명된다 -- **대부분 여기다** |
| **`못잼`** | 이 원장 크기로는 **어느 쪽인지 정할 수가 없다** |

셋째가 요점이다. 원장이 짧으면 무슨 값이 나와도 이례라고 말할 수 **없다** -- 도달
가능한 최소 p 가 문턱보다 크기 때문이다. 그것을 모르고 "상위 3%!" 라고 하면, 20개를
훑어보고 제일 놀라운 것을 고른 것과 구별되지 않는다.

## 정규분포를 가정하지 않는다

수익률은 꼬리가 두껍다. z 를 정규분포로 읽으면 이례를 과장한다 -- 그리고 그 과장이
정확히 사람들이 시황에서 하는 일이다. 여기서는 **경험분위**만 쓴다: 과거 표본 중 몇
개가 오늘보다 작았나. 분포를 안 가정하므로 틀릴 자리가 하나 줄어든다.

## 명제를 여러 개 세우면 그중 하나는 반드시 놀랍다

칸 넷에 명제를 여덟 개 세우고 그중 제일 낮은 p 를 집어 오면, 아무 일도 없는 날에도
"오늘의 이례" 가 나온다. **Holm 보정**으로 세운 개수만큼 문턱을 조인다. 세운 개수를
화면에 같이 적는다 -- 보정했다는 말만 있고 몇 개였는지 없으면 검사할 수가 없다.

## 한 줄에 기대는 결론은 약한 결론이다

`law` 의 뒤집기 검사(J005: 그 요건의 답이 갈릴 때 결론이 갈리는가)를 여기 옮겼다.
과거 표본에서 **줄 하나를 빼 보고** 판정이 뒤집히면 그렇게 적는다. 뒤집힌다고
기각하지는 않는다 -- 짚어 주는 것이 일이다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ALPHA = 0.05
MIN_N = 20          # 과거 표본이 이보다 적으면 아예 명제를 안 세운다


@dataclass
class 명제:
    말: str
    종류: str                   # 이례 · 동조 · 배합
    관측: float = 0.0
    기준: str = ""
    분위: float | None = None   # 과거 표본에서 오늘이 선 자리 (0~1)
    n: int = 0                  # 과거 표본 수
    p: float | None = None      # 단독 p (경험적, 양측)
    p보정: float | None = None
    판정: str = "못잼"
    근거: tuple = ()
    뒤집기: str = ""
    셈: str = ""
    이진: bool = False          # 0/1 지표인가 -- 도달 가능한 최소 p 가 다르다


def 변화(led, col: str) -> list:
    """이어진 두 줄 사이의 변화율(%). **줄이 날짜순이라고 본다.**

    앞 값이 0 이면 그 걸음은 없다 -- 0 으로 나누지 않고 채우지도 않는다.
    """
    v = [(r["id"], r.get(col)) for r in led.줄
         if isinstance(r.get(col), (int, float))]
    out = []
    for (i0, a), (i1, b) in zip(v, v[1:]):
        if a:
            out.append((i1, (b - a) / a * 100.0))
    return out


def 분위of(과거: list, x: float) -> tuple:
    """(분위, 양측 p). **정규분포를 안 쓴다** -- 과거 표본에서 세기만 한다.

    p 는 `2 * min((k+1)/(n+1), (n-k+1)/(n+1))` 로, +1 은 과거에 없던 값이
    p=0 이 되는 것을 막는다. 표본 n 개로 도달 가능한 최소 p 는 `2/(n+1)` 이고,
    그것이 `최소p()` 가 돌려주는 값이다.
    """
    n = len(과거)
    if n == 0:
        return None, None
    k = sum(1 for y in 과거 if y <= x)
    lo, hi = (k + 1) / (n + 1), (n - k + 1) / (n + 1)
    return k / n, min(1.0, 2 * min(lo, hi))


def 기저(과거: list, 오늘: float) -> tuple:
    """**이진 지표는 순위로 재면 안 된다.** 기저율이 곧 p 다.

    실측 2026-09-09 -- 이 자리에서 자가 뒤집혔다. 방향 일치(0/1)와 배합(0/1)을
    `분위of` 로 쟀더니, 오늘 값 1 은 과거 표본의 **최댓값이라 언제나 최상위 분위**가
    되어 일치율이 66% 든 5% 든 똑같이 최소 p 를 냈다. 자가 무엇을 재든 같은 답을
    주면 그것은 자가 아니다(`mathdrift` 의 낱말 겹침 자가 두 번 뒤집힌 그 자리다).

    이진에서 물어야 할 것은 **"오늘 일어난 일이 과거에 얼마나 잦았나"** 이고,
    그 비율이 그대로 한쪽 p 다. 한 번도 없었다고 p=0 이라 하지 않는다 --
    라플라스로 `(k+1)/(n+1)` 을 쓴다. 그래서 이진의 도달 가능한 최소 p 는 `1/(n+1)`.
    """
    n = len(과거)
    if n == 0:
        return None, None
    k = sum(1 for y in 과거 if y == 오늘)
    return k / n, min(1.0, (k + 1) / (n + 1))


def 최소p(n: int, 이진: bool = False) -> float:
    """표본 n 개로 **도달 가능한** 가장 작은 p.

    이것이 문턱보다 크면 무슨 값이 나와도 이례라고 말할 수 없다 -- 원장이 짧아서
    못 하는 것이지 평범해서가 아니다. 그 둘을 섞으면 안 된다.

    이진(한쪽)은 `1/(n+1)`, 연속(양측 순위)은 `2/(n+1)` 로 서로 다르다. 하나로
    뭉뚱그리면 이진 명제가 실제보다 못 잰다고 나오거나 그 반대가 된다.
    """
    if n <= 0:
        return 1.0
    return (1.0 if 이진 else 2.0) / (n + 1)


def holm(ps: list) -> list:
    """Holm 보정. 세운 명제 수만큼 문턱을 조인다. 단조성을 지킨다."""
    m = len(ps)
    if not m:
        return []
    order = sorted(range(m), key=lambda i: (ps[i] is None, ps[i]))
    out = [None] * m
    앞 = 0.0
    for j, i in enumerate(order):
        if ps[i] is None:
            continue
        앞 = max(앞, min(1.0, (m - j) * ps[i]))
        out[i] = 앞
    return out


def _판정(p보정, n, m: int, 이진: bool = False) -> str:
    """**못 잴 수 있음을 먼저 본다.** 못 잰 것을 평범이라 하면 거짓말이다."""
    if n < MIN_N or p보정 is None:
        return "못잼"
    if min(1.0, m * 최소p(n, 이진)) >= ALPHA:
        return "못잼"
    return "이례" if p보정 < ALPHA else "평범"


# ── 명제를 세운다 ────────────────────────────────────────────────────
def 이례(led, col: str) -> 명제 | None:
    """마지막 걸음이 그 계열의 과거 분포에서 어디인가."""
    ch = 변화(led, col)
    if len(ch) < 2:
        return None
    (오늘id, 오늘), 과거 = ch[-1], [v for _, v in ch[:-1]]
    q, p = 분위of(과거, 오늘)
    return 명제(말=f"{col} 의 오늘 움직임({오늘:+.2f}%)이 평소와 다른가",
                종류="이례", 관측=오늘, 기준=f"같은 계열의 과거 {len(과거)}걸음",
                분위=q, n=len(과거), p=p,
                근거=tuple((r["id"], col) for r in led.줄
                           if isinstance(r.get(col), (int, float))),
                셈="경험분위 (정규분포 가정 없음)")


def 동조(led, a: str, b: str) -> 명제 | None:
    """두 계열이 평소 같은 방향인가, 그리고 오늘은?"""
    ca, cb = dict(변화(led, a)), dict(변화(led, b))
    같이 = [(i, ca[i], cb[i]) for i in ca if i in cb]
    if len(같이) < 2:
        return None
    과거, 오늘 = 같이[:-1], 같이[-1]
    일치 = [1.0 if (x > 0) == (y > 0) else 0.0 for _, x, y in 과거]
    if not 일치:
        return None
    오늘일치 = 1.0 if (오늘[1] > 0) == (오늘[2] > 0) else 0.0
    q, p = 기저(일치, 오늘일치)          # 이진이므로 기저율이 곧 p 다
    율 = sum(일치) / len(일치)
    return 명제(말=f"{a} 와 {b} 가 오늘 "
                  f"{'같은' if 오늘일치 else '**다른**'} 방향인 것이 이례인가",
                종류="동조", 관측=오늘일치,
                기준=f"과거 {len(일치)}걸음의 방향 일치율 {율:.0%}",
                분위=q, n=len(일치), p=p,
                근거=tuple((i, a) for i, _, _ in 같이) + tuple((i, b) for i, _, _ in 같이),
                이진=True, 셈="오늘과 같은 방향 관계가 과거에 얼마나 잦았나 (기저율)")


def 배합(led, cols: list) -> 명제 | None:
    """오늘의 **오름/내림 배합**이 과거에 얼마나 자주 나왔나.

    "국내는 오르고 미국은 내렸다" 가 정확히 이 물음이다. 관측으로는 늘 참이고,
    물어야 할 것은 **그것이 드문 일인가**다. 기저율이 답한다.
    """
    ch = {c: dict(변화(led, c)) for c in cols}
    ids = sorted(set.intersection(*[set(v) for v in ch.values()])) if ch else []
    if len(ids) < 2:
        return None
    def 꼴(i):
        return tuple(ch[c][i] > 0 for c in cols)
    과거, 오늘 = [꼴(i) for i in ids[:-1]], 꼴(ids[-1])
    같은꼴 = [1.0 if x == 오늘 else 0.0 for x in 과거]
    q, p = 기저(같은꼴, 1.0)             # 이진이므로 기저율이 곧 p 다
    율 = sum(같은꼴) / len(같은꼴)
    보임 = " · ".join(f"{c}{'↑' if u else '↓'}" for c, u in zip(cols, 오늘))
    return 명제(말=f"오늘 배합({보임})이 드문가",
                종류="배합", 관측=율,
                기준=f"과거 {len(과거)}걸음 중 같은 배합 {int(sum(같은꼴))}번 ({율:.0%})",
                분위=q, n=len(같은꼴), p=p,
                근거=tuple((i, c) for c in cols for i in ids),
                이진=True, 셈="같은 배합이 과거에 얼마나 잦았나 (기저율)")


def 뒤집기(led, m: 명제, 세운수: int) -> str:
    """과거 표본에서 **줄 하나를 빼면** 판정이 뒤집히는가.

    `law/issue.py` 의 뒤집기 검사와 같은 자리다 -- 한 줄에 기대는 결론은 약한
    결론이다. **기각하지 않는다.** 짚어 주는 것이 일이다.
    """
    if m.종류 != "이례" or m.n < MIN_N:
        return ""
    col = m.근거[0][1] if m.근거 else ""
    ch = 변화(led, col)
    if len(ch) < 3:
        return ""
    오늘, 과거 = ch[-1][1], [v for _, v in ch[:-1]]
    본래 = m.판정
    for i in range(len(과거)):
        빼고 = 과거[:i] + 과거[i + 1:]
        _, p = 분위of(빼고, 오늘)
        if _판정(min(1.0, 세운수 * p) if p is not None else None,
                 len(빼고), 세운수, m.이진) != 본래:
            return f"과거 한 걸음({i + 1}번째)만 빼도 판정이 바뀐다 -- 약한 결론이다"
    return "과거 어느 한 걸음을 빼도 판정이 그대로다"


def 따져보기(led, cols=None) -> list:
    """원장에서 명제를 **세우고 보정하고 판정한다.** 이것이 추론 층 전부다.

    명제를 몇 개 세웠는지가 판정에 들어간다 -- 많이 세울수록 문턱이 조여진다.
    많이 세워 놓고 제일 놀라운 것만 보여 주는 것이 시황이 늘 하는 일이고,
    보정은 정확히 그것을 막는다.
    """
    cols = list(cols) if cols else [
        c for c in (led.줄[0] if led.줄 else {}) if c != "id"
        and isinstance(led.줄[0].get(c), (int, float))]
    ms = [x for x in (이례(led, c) for c in cols) if x]
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            x = 동조(led, cols[i], cols[j])
            if x:
                ms.append(x)
    if len(cols) >= 2:
        x = 배합(led, cols)
        if x:
            ms.append(x)
    보정 = holm([x.p for x in ms])
    for x, pb in zip(ms, 보정):
        x.p보정 = pb
        x.판정 = _판정(pb, x.n, len(ms), x.이진)
    for x in ms:
        x.뒤집기 = 뒤집기(led, x, len(ms))
    return ms


def 요약(ms: list) -> dict:
    n = len(ms)
    got = {k: sum(1 for m in ms if m.판정 == k) for k in ("이례", "평범", "못잼")}
    가능 = [m for m in ms if m.판정 != "못잼"]
    필요 = None
    if ms and not 가능:
        # 이 크기로는 아무것도 못 가른다. **몇 걸음이 있어야 하는지 적어 준다.**
        필요 = int(2 * n / ALPHA) - 1     # 연속 명제 기준(더 빡빡한 쪽)
    return {"세운수": n, **got, "필요표본": 필요}
