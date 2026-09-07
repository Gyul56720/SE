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
# **실측으로 골랐다**(2026-09-07). 엎은 원고 둘에 창 다섯 벌을 대고 시작점을 옮겨
# 가며 흔들림을 봤다. 10,000/2,500 이 두 원고 모두에서 흔들림 2 로 제일 고르다.
#
#     창/보폭        원고1 흔들림   원고2 흔들림
#      5,000/1,250        3             4
#      8,000/2,000        1             4      ← 한쪽만 좋다
#     10,000/2,500        2             2      ← 고른다
#     12,000/3,000        3             0      ← 한쪽만 좋다
#     15,000/3,000        4             4
#
# 창이 커야 하는 이유는 밀도다 -- 감성어가 천 자당 7개뿐이라 작은 창은 몇십 개로
# 평균을 낸다. 다만 너무 키우면 점이 줄어 반전 자체를 못 센다(15,000 이 그 자리).
WIN = int(os.environ.get("DRIFT_TURN_WIN", "10000"))
STRIDE = int(os.environ.get("DRIFT_TURN_STRIDE", "2500"))
# 이보다 창이 적으면 반전을 세지 않는다. 네 점에서 "많다" 는 말은 성립하지 않는다.
MIN_WINDOWS = int(os.environ.get("DRIFT_TURN_MIN_WINDOWS", "8"))
# **원고 길이의 바닥. 사용자가 정한 운영점이다**(2026-09-07) -- 논문에서 유도한 수가
# 아니다. 논문은 5만 **낱말** 이상 영어 소설만 썼고, 그것을 한국어 글자로 옮길 근거를
# 못 찾았다(EVIDENCE.md 22절). 그래서 사람이 5만 **자**로 정했다.
MIN_CHARS = int(os.environ.get("DRIFT_TURN_MIN_CHARS", "50000"))
# 시작점을 몇 군데서 재서 흔들림을 볼까.
ORIGINS = 4
# 논문이 보고한 소설의 반전 수. **우리 목표가 아니라 견줄 자리다** -- 영어 소설
# 5만 낱말 이상에서 나온 수이고, 우리 원고에 그대로 적용된다는 근거는 없다.
# 무엇보다 **창과 보폭이 다르면 이 수를 나란히 둘 수 없다** -- 반전 수는 점의 개수에
# 따라 커진다. 논문의 보폭을 못 찾았으므로 직접 비교는 성립하지 않는다.
PAPER_MEAN, PAPER_SD = 9.92, 3.14

# **그래서 밀도로 본다.** 만 자당 몇 번 뒤집히는가 -- 창 수에 안 휘둘린다.
#
# 목표 2.5. **잰 값이 아니라 사람이 정한 방향이다**(2026-09-07, "조금 더 올리는 게
# 재밌을 것 같아"). 바닥은 실측에서 왔다 -- **재미없다고 엎은 원고 셋이 만 자당
# 1.26 · 1.52 · 2.09 였다.** 목표를 그보다 위에 둔다.
#
# 엎은 원고에서 **목표를 뽑은 것이 아니라 바닥을 뽑았다.** 그 둘은 다르다 -- 재미없다고
# 버린 것에서 목표를 뽑으면 재미없음을 목표로 삼는 것이지만(EVIDENCE.md 5절),
# 그것을 "적어도 이보다는" 의 바닥으로 쓰는 것은 반대 방향이다.
# **밀도는 창에 매여 있다.** 같은 원고도 창 5,000 에서 1.99, 창 10,000 에서 1.19 다.
# 아래 수는 전부 위 기본 창(10,000/2,500)에서 잰 것이고, 창을 바꾸면 같이 다시 잡아야
# 한다.
AIM = float(os.environ.get("DRIFT_TURN_AIM", "1.5"))
DROPPED = (1.03, 1.19)           # 엎은 원고 둘의 밀도. 바닥이지 목표가 아니다.

_HANGUL = re.compile(r"[가-힣]")
_CACHE: dict | None = None


REPO = "https://github.com/park1200656/KnuSentiLex"


class MissingLexicon(RuntimeError):
    pass


def fetch(dest: Path | None = None) -> Path:
    """**사전을 실제로 받아 온다.** 저장소에 못 담으니(라이선스 표기 없음) 받아서 쓴다.

    손으로 한 줄 치게 하면 VM 에서는 그 한 줄을 빼먹고 도구가 조용히 안 도는 날이
    온다 -- 이 저장소가 '코드가 서버에 도달하지 못하는' 경로로 네 번 데인 그 자리다.
    그래서 없으면 여기서 받는다."""
    import subprocess
    dest = Path(dest or LEX_PATH).parent
    if (dest / "SentiWord_Dict.txt").is_file():
        return dest / "SentiWord_Dict.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", REPO, str(dest)],
                   check=True, capture_output=True, timeout=120)
    got = dest / "SentiWord_Dict.txt"
    if not got.is_file():
        raise MissingLexicon(f"받아 왔는데 파일이 없다: {got}")
    return got


def lexicon(auto: bool = True) -> dict:
    """{낱말: 극성}. **이모티콘은 뺀다** -- 사전의 그 부분은 부호가 뒤집힌 것이 섞여
    있고(웃는 얼굴이 -1), 우리 산문에 나오지도 않는다."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not LEX_PATH.is_file():
        if auto:
            try:
                fetch()
            except Exception as e:
                raise MissingLexicon(
                    f"감성사전이 없고 받아 오지도 못했다: {LEX_PATH}\n"
                    f"  받아 오다 난 것: {type(e).__name__}\n"
                    f"  손으로: git clone --depth 1 {REPO} novel/knu\n"
                    "  또는 DRIFT_SENTI_LEX 로 경로를 줘라.") from e
        else:
            raise MissingLexicon(
                f"감성사전이 없다: {LEX_PATH}\n"
                f"  받아라: git clone --depth 1 {REPO} novel/knu\n"
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
    """(평균 극성, 걸린 감성어 수).

    **제일 긴 것부터 맞춘다.** 짧은 것을 먼저 잡으면 긴 항목이 영영 안 걸린다.

    **앞이 한글이면 건너뛴다.** 형태소 분석기가 없어서 부분 문자열로 맞추는데, 그러면
    낱말 **안쪽**이 걸린다. 실측(2만 자)에서 이렇게 잡히던 것들:

        떨어진 · 벌어진  ->  '어진'(+2)  다섯 번
        떨어져서         ->  '져서'(-1)  네 번
        그때가           ->  '때가'(-1)  네 번

    앞 글자가 한글이면 그 자리는 낱말의 시작이 아니다. 이 검사 하나로 위 셋이 전부
    0이 됐다(164개 -> 139개). 뒤는 안 본다 -- 한국어는 조사와 어미가 붙으므로
    뒤까지 막으면 '좋다가' 같은 활용이 통째로 안 걸린다.

    **그래도 남는 한계**: 동음이의와 문체어는 못 가른다. 실측에서 제일 많이 걸린 것이
    '낡은'(18회)인데 그건 이 작가의 문체이지 사건의 정서가 아니다. 형태소 분석기를
    붙이기 전까지 이 자는 **거친 근사**다(EVIDENCE.md 22절)."""
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
                if i > 0 and _HANGUL.match(text[i - 1]):
                    continue                      # 낱말 안쪽이다
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
    need = max(MIN_CHARS, win + stride * (MIN_WINDOWS - 1))
    if len(text) < need:
        return {"ok": False, "why": "짧다", "chars": len(text), "win": win,
                "stride": stride, "need": need}
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
            "hits_per_window": round(sum(hits) / len(hits), 1),
            # **만 자당 반전.** 창 수에 안 휘둘리는 수라 원고끼리 견줄 수 있다.
            "density": round(counts[0] / (len(text) / 10000), 2)}


def from_book(path, win: int = WIN, stride: int = STRIDE) -> dict:
    book = json.loads(Path(path).read_text(encoding="utf-8"))
    return measure("".join(book.get("chunks") or []), win, stride)


def brief(book: dict) -> str:
    """**프롬프트에 얹을 되먹임.** 뒤집힘이 모자랄 때만 말한다.

    **자를 시키지 않고 일을 시킨다.** "감성어를 더 넣어라" 라고 하면 모델은 사전을
    맞추러 간다 -- 밝은 낱말과 어두운 낱말을 번갈아 뿌리면 이 자는 속는다. 그것은
    이야기가 뒤집힌 것이 아니라 낱말이 뒤집힌 것이다.

    그래서 되먹임에는 **정서가 · 감성어 · 반전 수를 한 글자도 안 싣는다.** 대신
    국면으로 말한다 -- 잘 되던 것이 틀어지거나, 막혔던 것이 풀리거나.

    기각하지 않는다. 5만 자 아래에서는 아무 말도 안 한다(잴 수가 없다)."""
    chunks = book.get("chunks") or []
    if not chunks:
        return ""
    try:
        m = measure("".join(chunks))
    except MissingLexicon:
        return ""                       # 사전이 없으면 조용히 빠진다. 집필을 막지 않는다
    if not m.get("ok") or m["density"] >= AIM:
        return ""
    return """[국면] **요즘 판이 한 방향으로만 간다.**

  * 이 대목에서 **한 번 뒤집어라.** 잘 풀리던 것이 틀어지거나, 막혀 있던 것이 풀리거나.
  * 뒤집는 것은 **사건이지 기분이 아니다.** 인물이 갑자기 우울해지는 것 말고, 무엇이
    실제로 달라져서 앞의 계산이 어긋나게 해라.
  * 크게 뒤집을 필요는 없다. 다만 **뒤집힌 뒤의 세계에서 다음 문장이 나와야** 한다 --
    뒤집고 원래대로 돌아오면 그건 안 뒤집힌 것이다.
  * 이미 이번 대목이 뒤집히는 자리면 그대로 가라."""


def table(m: dict) -> str:
    if not m.get("ok"):
        return (f"원고가 짧다 -- {m['chars']:,}자. 창 {m['win']:,} · 보폭 {m['stride']:,} 로"
                f" 재려면 최소 {m['need']:,}자가 필요하다(창 {MIN_WINDOWS}개).\n"
                "  창을 줄이면 잴 수는 있지만 값이 더 흔들린다 -- 밀도가 낮아서다.")
    trust = ("믿을 만하다" if m["spread"] <= 1 else
             "**믿지 마라**" if m["spread"] >= 4 else "반쯤만 믿어라")
    d = m["density"]
    verdict = ("**목표 위다.**" if d >= AIM else
               "목표에 못 미친다 -- 더 뒤집어야 한다." if d >= max(DROPPED) else
               "엎은 원고와 같은 자리다." if d >= min(DROPPED) else
               "**엎은 원고보다도 낮다.**")
    return "\n".join([
        f"{m['chars']:,}자 · 창 {m['win']:,} · 보폭 {m['stride']:,} · 창 {m['windows']}개"
        f" · 창당 감성어 {m['hits_per_window']:.0f}개",
        "",
        f"  **반전 {m['turns']}회** · 평균 크기 {m['amp']:.4f}",
        f"  **만 자당 {d}회** (목표 {AIM}) -- {verdict}",
        f"  흔들림 {m['spread']} (시작점 {ORIGINS}군데: {m['counts']}) -- {trust}",
        "",
        f"  바닥: 재미없다고 엎은 원고 {len(DROPPED)}벌이 만 자당"
        f" {' · '.join(str(x) for x in DROPPED)} 였다(같은 창에서 잰 것).",
        f"  견줄 자리: 논문의 영어 소설이 평균 {PAPER_MEAN}회 · SD {PAPER_SD}."
        " **나란히 두지 마라** -- 창·보폭이 다르면 반전 수는 비교가 안 된다.",
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
