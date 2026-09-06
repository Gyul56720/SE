"""표본과 원고를 **같은 자로 재서 수 한 줄로 만든다.**

여기가 이 개편의 바닥이다. 지금까지는 프롬프트를 고치고 나서 "나아진 것 같다" 를 눈으로
판단했다 -- 이 저장소에서 되돌린 것들이 전부 그래서 생겼다. 재는 것이 있으면 고친 뒤
가까워졌는지 멀어졌는지가 수로 나온다.

**원문은 여기서 끝난다.** 표본 소설은 이 파일이 읽고, 밖으로 나가는 것은 수뿐이다.
프롬프트에는 원문이 단 한 글자도 들어가지 않는다 -- 토큰도 토큰이지만, 원문 조각이
프롬프트에 들어가면 원고가 그것으로 도배된다는 것을 이 저장소에서 다섯 번 겪었다.

축은 novel/TAXONOMY.md 의 다섯 층에서 가져온다. 지금 재는 것은 문면층과 담화층 일부고,
나머지는 빈칸으로 둔다 -- 없는 것을 있는 척하지 않는다.

실행:
    python3 novel/profile.py novel/corpus              # 작품마다 한 줄
    python3 novel/profile.py novel/corpus --units      # 토막마다 한 줄
    python3 novel/profile.py novel/corpus --json out.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import diffusion, echo, grain, rhythm, voice, wording      # noqa: E402

# **낱낱까지 잰다.** 한 작품을 흉내 낼 때 켠다 -- 문장 길이와 대사 몫이 맞아도 낱말과
# 문법이 다르면 다른 글이다. 여러 작품의 평균에 대고 켜면 그 평균은 어느 작품의 것도
# 아니라서, 낱낱까지 맞추라는 요구가 아무 데도 없는 글을 만든다.
GRAIN = os.environ.get("DRIFT_GRAIN", "") not in ("", "0", "false")

# 이보다 짧은 토막은 안 잰다. 꼬리 조각에서 나온 비율은 통계가 아니라 잡음이다.
MIN_UNIT = 1500

# **축.** 이름 -> (재는 함수, 무엇인가). 여기 있는 것이 곧 우리가 볼 수 있는 전부다.
# 늘리는 것은 언제든 되지만, 늘린 축은 프롬프트가 아니라 **점수**에 먼저 들어간다.
_BASE = ("sent_len sent_var long short da_share end_var glue climb dialog talk_len "
         "rally para_len repeat outside "
         # **서사층 대용.** 의미를 안 읽고 이야기의 결만 잰다.
         "names newname scene clock askrate").split()
# 낱낱 축은 grain 이 낸다(품사 · 조사 · 어미 · 어휘 · 부호). GRAIN 을 끄면 안 붙는다.
AXES = _BASE + (grain.axes() + voice.axes() if GRAIN else [])


def _sent(text: str) -> list:
    tell, _ = rhythm._lines(text)
    return [s for s in tell if s.strip()]


def _entropy(counts) -> float:
    """고르게 흩어져 있으면 1, 하나로 몰려 있으면 0. 종결어미와 문장 성분에 쓴다."""
    tot = sum(counts)
    if tot <= 0:
        return 0.0
    ps = [c / tot for c in counts if c > 0]
    if len(ps) < 2:
        return 0.0
    h = -sum(p * math.log(p) for p in ps)
    return h / math.log(len(counts))


def measure(text: str) -> dict:
    """토막 하나의 프로필. **비율과 분포만** 담는다 -- 길이에 안 휘둘려야 견줄 수 있다."""
    tell = _sent(text)
    if not tell:
        return {}
    lens = [len(s) for s in tell]
    m = rhythm.measure(text)
    short, long_, bulk, rally = diffusion._talk4(text)[:4]
    # **문단은 빈 줄이 아니라 줄바꿈으로 갈린다.** 빈 줄로 갈랐더니 표본 넷이 전부
    # 토막 크기 그대로 나왔다(5,013 · 5,011 · 5,003자) -- 소설 원문에는 빈 줄이 없다.
    paras = [p for p in text.split("\n") if p.strip()]
    ends = [len(rx.findall(text)) for rx in wording.ENDINGS.values()]
    out = {
        "sent_len":  sum(lens) / len(lens),          # 문장 평균 길이
        "sent_var":  rhythm.spread(lens),            # 길이의 들쭉날쭉함
        "long":      m["long"],                      # 긴 문장 몫
        "short":     sum(l < 20 for l in lens) / len(lens),
        "da_share":  m["da"],                        # 짧은 '-다' 몫
        "end_var":   _entropy(ends),                 # 종결어미가 고른가
        "glue":      rhythm.glue(text),              # 문장당 이어 붙인 절
        "climb":     m["climb"] / max(1, m["n"]),    # 서술문당 점층
        "dialog":    m["talk"],                      # 대사 줄 몫
        "talk_len":  bulk,                           # 긴 대사의 몫
        "rally":     rally,                          # 가장 길게 주고받은 턴
        "para_len":  sum(len(p) for p in paras) / len(paras) if paras else 0.0,
        "repeat":    echo.selfish(text)[0],          # 제 안에서 되풀이한 몫
        "outside":   _outside(text),                 # 밖을 적은 몫
        "names":     _names(text)[0],                # 이름이 몇 개나 도는가(천 자당)
        "newname":   _names(text)[1],                # 그중 한 번만 나오고 마는 몫
        "scene":     _scene(text),                   # 자리·때가 바뀌는 자국(천 자당)
        "clock":     _clock(text),                   # 시한·약속이 걸린 문장의 몫
        "askrate":   _ask(text),                     # 묻는 문장의 몫
        "_n":        len(tell),
        "_chars":    len(text),
    }
    if GRAIN:
        out.update(grain.measure(text))
        out.update(voice.measure(text))
    return out


# **밖(외현)을 재는 대용.** 밖에서 온 것에는 이름표가 붙는다 -- 수 · 고유명사 표기 ·
# 따옴표 안 든 표기 · 단위. 이것이 많은 문장을 밖을 본 문장으로 센다. 정확하지는 않지만
# 작품끼리 견주는 데는 쓸 수 있다(같은 자로 재기 때문이다).
_MARK = re.compile(r"(\d|[A-Za-z]{2,}|[%°㎡㎞㎏]|번지|호실|층|년생|시 \d|분|초)")


def _outside(text: str) -> float:
    tell = _sent(text)
    if not tell:
        return 0.0
    return sum(bool(_MARK.search(s)) for s in tell) / len(tell)


# **관측을 늘리는 두 번째 손잡이.** 토막을 겹쳐 가며 훑으면 같은 표본에서 더 많은
# 점이 나온다. 이웃한 창은 서로 겹치니 완전히 독립은 아니지만, 우리가 쓰려는 것은
# **폭(10~90%)** 이라 그 편향은 작고 폭 추정은 훨씬 안정된다.
STRIDE = float(os.environ.get("DRIFT_PROFILE_STRIDE", "1.0"))


def windows(text: str, size: int, stride: float) -> list:
    """겹치는 창으로 자른다. stride=1.0 이면 안 겹친다."""
    if stride >= 1.0 or len(text) <= size:
        return [text[i:i + size] for i in range(0, len(text), size)] or [text]
    step = max(1, int(size * stride))
    out = [text[i:i + size] for i in range(0, max(1, len(text) - size + 1), step)]
    return [w for w in out if len(w) >= MIN_UNIT]


# **이름.** 형태소 분석기 없이 근사한다 -- 조사가 붙는 2자 이상 낱말 가운데 여러 번
# 나오는 것. 사람 이름인지 물건 이름인지는 안 가른다. 우리가 보려는 것은 "이 대목에
# 몇 개의 것이 돌고 있는가" 와 "한 번 나오고 버려지는 비율" 이다.
_WORD2 = re.compile(r"[가-힣]{2,}")
_STOP2 = frozenset((
    "그는", "그가", "나는", "내가", "우리", "그녀", "그들", "사람", "생각", "자신",
    "때문", "동안", "하나", "여기", "거기", "이제", "다시", "조금", "그때", "얼마",
    "것이", "것을", "것은", "이야기", "그것", "이것", "저것", "정도", "이런", "그런"))


def _names(text: str) -> tuple:
    tell, _ = rhythm._lines(text)
    if not tell:
        return 0.0, 0.0
    seen: dict = {}
    for s in tell:
        for w in _WORD2.findall(s):
            if w not in _STOP2:
                seen[w] = seen.get(w, 0) + 1
    many = [w for w, c in seen.items() if c >= 2]
    once = [w for w, c in seen.items() if c == 1]
    per = 1000 / max(1, len(text))
    return len(many) * per, len(once) / max(1, len(seen))


# **장면이 바뀌는 자국.** 자리와 때가 옮겨 갈 때 한국어는 첫머리에 표를 남긴다.
_SCENE = re.compile(
    r"(다음 ?날|이튿날|그날 밤|아침|저녁|새벽|한참|얼마 뒤|잠시 뒤|그리고 나서|"
    r"도착|들어서|나와서|나서자|돌아와|올라가|내려가|건너|향해|떠나|출발)")
_CLOCK = re.compile(
    r"(까지|기한|마감|약속|시간이 없|늦으면|남았|남지 않|앞으로 \d|이틀|사흘|일주일|"
    r"내일|모레|당장|서둘)")


def _scene(text: str) -> float:
    tell, _ = rhythm._lines(text)
    return len([s for s in tell if _SCENE.search(s)]) * 1000 / max(1, len(text))


def _clock(text: str) -> float:
    tell, _ = rhythm._lines(text)
    return len([s for s in tell if _CLOCK.search(s)]) / max(1, len(tell))


def _ask(text: str) -> float:
    lines = [l for l in text.splitlines() if l.strip()]
    return sum("?" in l for l in lines) / max(1, len(lines))


def unit_files(root) -> list:
    """corpus.py 가 떨군 토막들. 원본 txt 는 안 읽는다 -- 자른 것만 본다."""
    root = Path(root)
    out = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        out += [(d.name, f) for f in sorted(d.glob("*.txt"))]
    return out


def profile(root, only: list | None = None) -> dict:
    """작품마다 {축: [토막별 값]}. only 를 주면 그 작품만 -- **갈래가 다른 것을 한
    통에 넣으면 어느 쪽도 아닌 값이 나온다**(실측: 웹소설과 번역 문학과 교양서를 같이
    재니 대사 몫이 0.01~0.29 로 벌어졌다. 그 폭은 어느 작품의 것도 아니다)."""
    works: dict = {}
    for work, f in unit_files(root):
        if only and work not in only:
            continue
        text = f.read_text(encoding="utf-8")
        if len(text) < MIN_UNIT:
            continue
        for piece in (windows(text, len(text), 1.0) if STRIDE >= 1.0
                      else windows(text, max(MIN_UNIT, len(text) // 2), STRIDE)):
            m = measure(piece)
            if not m:
                continue
            w = works.setdefault(work, {k: [] for k in AXES})
            # **없는 축은 안 담는다.** 자국이 하나도 없어서 못 잰 축(voice 의 시제 ·
            # 인칭)을 0 으로 채우면 "안 쓴다" 와 "알 수 없다" 가 같아지고, 그 0 들이
            # 폭을 아래로 끌어내린다.
            for k in AXES:
                if k in m:
                    w[k].append(m[k])
    return works


def summary(vals: list) -> dict:
    """가운뎃값과 폭. **평균이 아니라 가운뎃값**이다 -- 토막 하나가 튀어도 안 흔들린다."""
    if not vals:
        return {"mid": 0.0, "lo": 0.0, "hi": 0.0, "n": 0}
    v = sorted(vals)
    n = len(v)
    return {"mid": v[n // 2], "lo": v[max(0, n // 10)], "hi": v[min(n - 1, n * 9 // 10)],
            "n": n}


def digest(works: dict) -> dict:
    """작품별 요약 + 전체 요약. 이것이 목표값의 원천이 된다."""
    out = {"works": {}, "all": {}}
    pool: dict = {k: [] for k in AXES}
    for work, axes in works.items():
        out["works"][work] = {k: summary(v) for k, v in axes.items()}
        for k in AXES:
            pool[k] += axes[k]
    out["all"] = {k: summary(v) for k, v in pool.items()}
    return out


def _fmt(v: float) -> str:
    """큰 수와 작은 수를 같은 폭에 담는다 -- 문단 길이만 천 단위라 칸이 깨졌다."""
    return f"{v:>9,.0f}" if abs(v) >= 100 else f"{v:>9.2f}"


def table(dig: dict, units: bool = False) -> str:
    works = sorted(dig["works"])
    head = f"{'축':<10}" + "".join(f"{w[:7]:>9}" for w in works) + f"{'전체':>11}"
    rows = [head, "-" * len(head)]
    for k in AXES:
        line = f"{k:<10}"
        for w in works:
            line += _fmt(dig["works"][w][k]["mid"])
        a = dig["all"][k]
        line += f"  {_fmt(a['mid']).strip():>7} ({_fmt(a['lo']).strip()}~{_fmt(a['hi']).strip()})"
        rows.append(line)
    n = sum(dig["works"][w][AXES[0]]["n"] for w in works)
    rows.append(f"\n토막 {n}개 · 작품 {len(works)}편")
    return "\n".join(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="표본을 재서 프로필을 낸다")
    ap.add_argument("root", help="corpus.py --write 로 만든 폴더")
    ap.add_argument("--json", default="", help="여기에 저장한다")
    ap.add_argument("--units", action="store_true", help="토막마다 한 줄로 찍는다")
    a = ap.parse_args(argv)

    works = profile(a.root)
    if not works:
        print(f"잰 것이 없다: {a.root}\n"
              f"  python3 novel/corpus.py {a.root} --write 를 먼저 돌려야 한다.",
              file=sys.stderr)
        return 1
    dig = digest(works)
    if a.units:
        for work, axes in sorted(works.items()):
            for i in range(len(axes[AXES[0]])):
                print(work, i + 1, " ".join(f"{k}={axes[k][i]:.2f}" for k in AXES))
    print(table(dig))
    if a.json:
        Path(a.json).write_text(json.dumps(dig, ensure_ascii=False, indent=1),
                                encoding="utf-8")
        print(f"\n-> {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
