"""**반전.** 정서가 궤적이 몇 번, 얼마나 크게 뒤집히는가.

문헌에서 **수가 붙은 유일한 성공 공식**이다(`EVIDENCE.md` 21절). Knight, Rocklage &
Bart (2024), *Science Advances* -- 영화 · TV · 소설 · 모금 피치 약 3만 편의 정서가
궤적에서 반전의 수와 크기를 재고 성공과 대조했다. **소설은 다운로드가 110% 늘었다**
(반전이 가장 많고 큰 쪽이 가장 적은 쪽의 두 배 이상). 영화 평점 최대 +1.4, 모금
달성 확률 +39%p.

## 진단만 한다 -- 되먹임을 안 건다

**프롬프트에 안 실린다. 원고를 못 건드린다.** 아래 '흔들림' 이 말하듯 이 자는 아직
안정적이지 않고, 흔들리는 자로 되먹임을 걸면 그 흔들림이 그대로 원고로 들어간다.
C층 지표에 기각 권한을 주지 않는 것과 같은 이유다(`SUCCESS.md`).

## 자가 제 신뢰도를 같이 낸다

같은 글이면 **어디서부터 자르든 같은 수**가 나와야 한다. 그래서 시작점을 여러 개
옮겨 가며 재고 그 **폭**을 함께 찍는다. 폭이 크면 그 수를 믿지 말라는 뜻이다 --
흔들린다는 사실을 숨기는 것보다 같이 내놓는 편이 정직하다.

## 창은 겹친다

논문은 소설에 1만 낱말 창을 썼다고 하는데, 5만 낱말 소설을 그렇게 자르면 창이 다섯
개다. 다섯 점에서 방향이 바뀌는 것은 많아야 세 번인데 논문이 보고한 반전은 **평균
9.92** 다. 고정 분할로는 그 수가 안 나온다 -- 창이 겹친다고 볼 수밖에 없다.
우리 실측도 같은 곳을 가리켰다(겹치자 시작점 의존이 줄었다).

## 사전은 저장소에 안 들어간다

KNU 한국어 감성사전을 쓴다. **라이선스 표기가 없어** 여기 담지 않고 경로에서 읽는다.

    git clone --depth 1 https://github.com/park1200656/KnuSentiLex novel/knu

`DRIFT_SENTI_LEX` 로 다른 경로를 줄 수 있다.

실행:
    python3 novel/turn.py novel/drift.json
    python3 novel/turn.py novel/drift.json --win 5000 --stride 1250
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent
LEX_PATH = Path(os.environ.get("DRIFT_SENTI_LEX", HERE / "knu" / "SentiWord_Dict.txt"))

# 창과 보폭. 실측에서 창이 클수록 안정됐다 -- 감성어 밀도가 천 자당 5~25개뿐이라
# 작은 창은 몇십 개로 평균을 낸다. **이 값은 잰 것이 아니라 출발점이다.**
WIN = int(os.environ.get("DRIFT_TURN_WIN", "5000"))
STRIDE = int(os.environ.get("DRIFT_TURN_STRIDE", "1250"))
# 이보다 창이 적으면 반전을 세지 않는다. 네 점에서 "많다" 는 말은 성립하지 않는다.
MIN_WINDOWS = int(os.environ.get("DRIFT_TURN_MIN_WINDOWS", "8"))
# 시작점을 몇 군데서 재서 흔들림을 볼까.
ORIGINS = 4
# 논문이 보고한 소설의 반전 수. **우리 목표가 아니라 견줄 자리다** -- 영어 소설
# 5만 낱말 이상에서 나온 수이고, 우리 원고에 그대로 적용된다는 근거는 없다.
PAPER_MEAN, PAPER_SD = 9.92, 3.14

_HANGUL = re.compile(r"[가-힣]")
_CACHE: dict | None = None


class MissingLexicon(RuntimeError):
    pass


def lexicon() -> dict:
    """{낱말: 극성}. **이모티콘은 뺀다** -- 사전의 그 부분은 부호가 뒤집힌 것이 섞여
    있고(웃는 얼굴이 -1), 우리 산문에 나오지도 않는다."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not LEX_PATH.is_file():
        raise MissingLexicon(
            f"감성사전이 없다: {LEX_PATH}\n"
            "  받아라: git clone --depth 1 "
            "https://github.com/park1200656/KnuSentiLex novel/knu\n"
            "  또는 DRIFT_SENTI_LEX 로 경로를 줘라.")
    out: dict = {}
    for line in LEX_PATH.read_text(encoding="utf-8").splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) != 2:
            continue
        w, v = parts[0].strip(), parts[1].strip()
        if not w or not _HANGUL.search(w):
            continue
        try:
            out[w] = int(v)
        except ValueError:
            continue
    _CACHE = out
    return out


def valence(text: str) -> tuple:
    """(평균 극성, 걸린 감성어 수). **제일 긴 것부터 맞춘다** -- 짧은 것을 먼저 잡으면
    낱말 안쪽이 걸린다."""
    lex = lexicon()
    if not lex:
        return 0.0, 0
    longest = max(len(w) for w in lex)
    tot = n = i = 0
    L = len(text)
    while i < L:
        for k in range(min(longest, L - i), 1, -1):
            w = text[i:i + k]
            if w in lex:
                tot += lex[w]
                n += 1
                i += k
                break
        else:
            i += 1
    return (tot / n if n else 0.0), n


def series(text: str, win: int, stride: int, off: int = 0) -> list:
    t = text[off:]
    return [valence(t[i:i + win])[0] for i in range(0, len(t) - win + 1, stride)]


def _smooth(xs: list, k: int = 3) -> list:
    out = []
    for i in range(len(xs)):
        lo, hi = max(0, i - k // 2), min(len(xs), i + k // 2 + 1)
        out.append(sum(xs[lo:hi]) / (hi - lo))
    return out


def reversals(vals: list) -> tuple:
    """(뒤집힌 횟수, 평균 크기). 매끄럽게 한 뒤 기울기의 부호가 바뀌는 자리를 센다.

    크기 문턱을 따로 두지 않는다 -- 문턱을 두면 그 수가 또 짐작이 된다. 대신 매끄럽게
    해서 잔떨림을 없앤다."""
    s = _smooth(vals)
    d = [b - a for a, b in zip(s, s[1:])]
    d = [x for x in d if abs(x) > 1e-9]
    if len(d) < 2:
        return 0, 0.0
    swings = [abs(a) + abs(b) for a, b in zip(d, d[1:]) if a * b < 0]
    return len(swings), (sum(swings) / len(swings) if swings else 0.0)


def measure(text: str, win: int = WIN, stride: int = STRIDE) -> dict:
    """반전 수와 크기, 그리고 **그 수를 믿어도 되는가**."""
    if len(text) < win + stride * (MIN_WINDOWS - 1):
        return {"ok": False, "why": "짧다", "chars": len(text), "win": win,
                "stride": stride, "need": win + stride * (MIN_WINDOWS - 1)}
    counts, mags, hits = [], [], []
    for j in range(ORIGINS):
        off = (stride * j) // ORIGINS
        vals = series(text, win, stride, off)
        c, m = reversals(vals)
        counts.append(c)
        mags.append(m)
        hits.append(valence(text[off:off + win])[1])
    return {"ok": True, "chars": len(text), "win": win, "stride": stride,
            "windows": len(series(text, win, stride)),
            "turns": counts[0], "spread": max(counts) - min(counts),
            "counts": counts, "amp": round(sum(mags) / len(mags), 4),
            "hits_per_window": round(sum(hits) / len(hits), 1)}


def from_book(path, win: int = WIN, stride: int = STRIDE) -> dict:
    book = json.loads(Path(path).read_text(encoding="utf-8"))
    return measure("".join(book.get("chunks") or []), win, stride)


def table(m: dict) -> str:
    if not m.get("ok"):
        return (f"원고가 짧다 -- {m['chars']:,}자. 창 {m['win']:,} · 보폭 {m['stride']:,} 로"
                f" 재려면 최소 {m['need']:,}자가 필요하다(창 {MIN_WINDOWS}개).\n"
                "  창을 줄이면 잴 수는 있지만 값이 더 흔들린다 -- 밀도가 낮아서다.")
    trust = ("믿을 만하다" if m["spread"] <= 1 else
             "**믿지 마라**" if m["spread"] >= 4 else "반쯤만 믿어라")
    return "\n".join([
        f"{m['chars']:,}자 · 창 {m['win']:,} · 보폭 {m['stride']:,} · 창 {m['windows']}개"
        f" · 창당 감성어 {m['hits_per_window']:.0f}개",
        "",
        f"  **반전 {m['turns']}회** · 평균 크기 {m['amp']:.4f}",
        f"  흔들림 {m['spread']} (시작점 {ORIGINS}군데: {m['counts']}) -- {trust}",
        "",
        f"  견줄 자리: 논문의 영어 소설이 평균 {PAPER_MEAN} · SD {PAPER_SD}."
        " **우리 목표가 아니다** -- 5만 낱말 이상 영어 소설에서 나온 수다.",
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="정서가 궤적이 몇 번 뒤집히는가 (진단만)")
    ap.add_argument("path", help="drift.json")
    ap.add_argument("--win", type=int, default=WIN)
    ap.add_argument("--stride", type=int, default=STRIDE)
    a = ap.parse_args(argv)
    try:
        m = from_book(a.path, a.win, a.stride)
    except MissingLexicon as e:
        print(e, file=sys.stderr)
        return 1
    print("반전 (EVIDENCE.md 21·22절) -- **진단만 한다. 프롬프트에 안 실린다.**\n")
    print(table(m))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
