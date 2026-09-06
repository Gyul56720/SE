"""표본 소설을 **화 단위로 자른다** -- 손으로 나누지 않는다.

사람이 미리 분류하면 그 나눔이 곧 편향이다. 원문을 통째로 받아서 기계가 자른다.

자르는 순서.
  1. 원문에 이미 있는 표식으로 자른다 -- 부 · 장 · 화 · 막 · 편 · 프롤로그 · 에필로그,
     마크다운 머리표, 줄표만 있는 구분선, 숫자만 있는 줄.
  2. 표식이 너무 적게 잡히면(연재분을 이어 붙인 파일이 그렇다) **길이로 자른다** --
     빈 줄 뭉치를 경계 후보로 삼아 목표 길이에 가장 가까운 자리에서 끊는다.
  3. 너무 짧은 토막은 앞엣것에 붙인다. 표식이 본문 안에 우연히 들어간 경우다.

**본문은 손대지 않는다.** 공백도 줄바꿈도 원문 그대로 옮긴다 -- 우리가 재려는 것이
바로 그 꼴이기 때문이다. 자른 자리와 머리표만 기록한다.

실행:
    python3 novel/corpus.py novel/corpus/A.txt              # 어떻게 잘리는지만 본다
    python3 novel/corpus.py novel/corpus/A.txt --write      # 실제로 쪼개 저장한다
    python3 novel/corpus.py novel/corpus --write            # 폴더째
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path

# 목표 길이. 웹 연재 한 회가 대개 이 언저리다.
TARGET = 5000
# **표식으로 자른 뒤에도 이만큼을 넘으면 다시 자른다.** 장 하나가 십만 자인 단행본이
# 있다(실측: 한 토막 310,835자). 그걸 한 덩이로 두면 그 작품의 프로필이 열두 점밖에
# 안 되고, 화마다 다른 것을 재겠다는 말이 무의미해진다.
MAX_CHARS = TARGET * 3
# 이보다 짧은 토막은 앞엣것에 붙인다. 표식이 본문에 우연히 섞인 자리를 걸러 낸다.
MIN_CHARS = 800

_NUM = r"(?:\d{1,4}|[一二三四五六七八九十百]{1,6})"

# **표식.** 줄 전체가 표식이어야 한다 -- 본문 한가운데의 "3화 때는" 을 경계로 삼으면
# 원고가 산산조각 난다. 그래서 줄 시작과 끝을 모두 묶는다.
MARKS = [
    ("부", re.compile(rf"^\s*(?:제\s*)?({_NUM})\s*부\b.*$")),
    ("장", re.compile(rf"^\s*(?:제\s*)?({_NUM})\s*장\b.*$")),
    ("화", re.compile(rf"^\s*(?:제\s*)?({_NUM})\s*(?:화|회|편)\b.*$")),
    ("화", re.compile(r"^\s*(프롤로그|에필로그|서장|종장|외전)\b.*$")),
    ("장", re.compile(r"^\s*#{1,3}\s+\S.*$")),
    ("화", re.compile(rf"^\s*{_NUM}\s*[.)]?\s*$")),
    ("화", re.compile(r"^\s*[-=*_·~]{3,}\s*$")),
]


@dataclass
class Unit:
    """자른 토막 하나. 본문과 그 자리를 함께 들고 있는다."""
    order: int
    part: int
    chapter: int
    episode: int
    title: str
    line: int
    body: str

    @property
    def stem(self) -> str:
        return f"{self.part:02d}-{self.chapter:02d}-{self.episode:03d}"


def load(path) -> str:
    """읽어서 줄바꿈만 고른다. **글자는 안 건드린다.**"""
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"읽을 수 있는 인코딩이 없다: {path}")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", text)


def marks(text: str) -> list:
    """표식이 걸린 줄. [(줄번호, 갈래, 그 줄)] 로 돌려준다."""
    out = []
    for i, line in enumerate(text.split("\n")):
        s = line.strip()
        if not s or len(s) > 60:      # 긴 줄은 본문이다
            continue
        for kind, rx in MARKS:
            if rx.match(s):
                out.append((i, kind, s))
                break
    return out


def _by_length(text: str, target: int) -> list:
    """표식이 없을 때. **빈 줄에서만 끊는다** -- 문장 한가운데를 자르면 자가 거짓말한다."""
    lines = text.split("\n")
    breaks, run = [], 0
    for i, line in enumerate(lines):
        run = run + len(line) + 1
        if not line.strip() and run >= target:
            breaks.append(i)
            run = 0
    if breaks:
        return breaks
    # **빈 줄이 하나도 없는 원고가 있다**(실측: 한 장이 310,835자인데 통째로 붙어
    # 있었다). 그때는 줄 경계에서라도 끊는다 -- 문장 한가운데만 아니면 된다.
    run = 0
    for i, line in enumerate(lines):
        run += len(line) + 1
        if run >= target and i + 1 < len(lines):
            breaks.append(i)
            run = 0
    return breaks


def _subsplit(body: str, target: int) -> list:
    """거대한 토막을 빈 줄에서 다시 자른다. 표식으로 자른 결과가 여전히 클 때 쓴다."""
    lines = body.split("\n")
    at = [0] + [i + 1 for i in _by_length(body, target)]
    out = []
    for n, start in enumerate(at):
        end = at[n + 1] if n + 1 < len(at) else len(lines)
        piece = "\n".join(lines[start:end])
        if piece.strip():
            out.append(piece)
    if len(out) > 1:
        return out
    # **줄바꿈조차 없는 원고.** 통째로 한 줄인 파일이 있다. 마지막 수단으로 문장 끝에서
    # 끊는다 -- 여기서도 못 끊으면 그냥 둔다(문장 한가운데를 자르느니 큰 채로 두는 편이
    # 낫다. 자른 자리가 문장 안이면 그 뒤로 모든 자가 거짓말을 한다).
    parts, cur = [], ""
    for sent in re.split(r'(?<=[.!?…"\u201d])\s*', body):
        cur += sent
        if len(cur) >= target:
            parts.append(cur)
            cur = ""
    if cur.strip():
        parts.append(cur)
    return parts if len(parts) > 1 else (out or [body])


def split(text: str, target: int = TARGET, min_chars: int = MIN_CHARS,
          max_chars: int = MAX_CHARS) -> list:
    """토막 목록. 표식이 있으면 표식으로 자르고, **그러고도 큰 것은 길이로 다시** 자른다."""
    lines = text.split("\n")
    found = marks(text)
    # 표식이 본문 길이에 견주어 너무 적으면 못 쓴다 -- 한 덩이가 통째로 남는다.
    use = [m for m in found if m[1] in ("부", "장", "화")]
    if len([m for m in use if m[1] == "화"]) < 2 and len(use) < 2:
        cuts = [(i, "화", "") for i in _by_length(text, target)]
    else:
        cuts = use

    at = sorted({0} | {i for i, _, _ in cuts})
    kind_at = {i: (k, s) for i, k, s in cuts}

    units, part, chapter, episode, order = [], 1, 1, 0, 0
    for n, start in enumerate(at):
        end = at[n + 1] if n + 1 < len(at) else len(lines)
        kind, title = kind_at.get(start, ("화", ""))
        body = "\n".join(lines[start:end])
        if not body.strip():
            continue
        # 너무 짧으면 앞엣것에 붙인다. **다만 앞엣것이 이미 크면 안 붙인다** -- 실측:
        # 27자짜리 조각이 계속 붙어 한 토막이 64,851자가 됐다. 붙이기에 상한이 없으면
        # 2차 분할로 잘라 놓은 것을 이 자리가 도로 이어 붙인다.
        if units and len(body.strip()) < min_chars and len(units[-1].body) < max_chars:
            units[-1].body += "\n" + body
            continue
        if kind == "부":
            part, chapter = part + 1 if units else part, 1
        elif kind == "장" and units:
            chapter += 1
        # **표식으로 잘랐어도 크면 다시 자른다.** 나뉜 조각은 같은 부 · 장에 남는다.
        for piece in (_subsplit(body, target) if len(body) > max_chars else [body]):
            episode += 1
            order += 1
            units.append(Unit(order=order, part=part, chapter=chapter, episode=episode,
                              title=title if piece is body or piece.startswith(title) else "",
                              line=start + 1, body=piece))
    # **앞머리 부스러기는 뒤엣것에 붙인다.** 제목만 있는 첫 줄이 한 토막으로 남는다
    # (실측: 59자 · 61자). 앞에 붙일 것이 없으니 뒤로 붙여야 한다.
    while len(units) > 1 and len(units[0].body.strip()) < min_chars:
        head = units.pop(0)
        units[0].body = head.body + "\n" + units[0].body
        units[0].title = units[0].title or head.body.strip()[:40]
    # **마지막으로 한 번 더 훑는다.** 붙이기와 2차 분할이 서로를 되돌리는 일이 있어서,
    # 다 끝난 뒤 크기를 다시 본다(실측: 79,277자짜리 토막이 남아 있었다).
    final = []
    for u in units:
        if len(u.body) <= max_chars:
            final.append(u)
            continue
        for piece in _subsplit(u.body, target):
            final.append(Unit(order=0, part=u.part, chapter=u.chapter, episode=0,
                              title=u.title, line=u.line, body=piece))
    for i, u in enumerate(final, 1):
        u.order, u.episode = i, i
        u.title = " ".join(u.title.split())[:60]
    return final


def write(units: list, out_dir) -> dict:
    """토막을 파일로 떨군다. 이름에 부 · 장 · 화가 들어가야 나중에 그 축으로 잰다."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    man = {"n": len(units), "units": []}
    for u in units:
        (out / f"{u.stem}.txt").write_text(u.body, encoding="utf-8")
        man["units"].append({k: v for k, v in asdict(u).items() if k != "body"}
                            | {"chars": len(u.body)})
    (out / "manifest.json").write_text(
        json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    return man


def report(path, units: list, rows: int = 0) -> str:
    """rows=0 이면 **전부** 찍는다. 잘린 모양을 보려고 돌리는 것인데 앞 몇 줄만
    보여 주면 뒤쪽이 어떻게 잘렸는지 알 수가 없다."""
    n = len(units)
    sizes = sorted(len(u.body) for u in units)
    head = (f"{Path(path).name}: {n}토막 · 가운뎃값 {sizes[n // 2]:,}자 · "
            f"{sizes[0]:,}~{sizes[-1]:,}자" if n else f"{Path(path).name}: 0토막")
    show = units if rows <= 0 else units[:rows]
    out = [f"  {u.stem}  {len(u.body):>6,}자  {u.title[:34]}" for u in show]
    if len(show) < n:
        out.append(f"  … {n - len(show)}개 더")
    return "\n".join([head] + out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="표본 소설을 화 단위로 자른다")
    ap.add_argument("path", help="txt 파일 또는 그 파일들이 든 폴더")
    ap.add_argument("--write", action="store_true", help="실제로 쪼개 저장한다")
    ap.add_argument("--target", type=int, default=TARGET)
    ap.add_argument("--min", type=int, default=MIN_CHARS)
    ap.add_argument("--max", type=int, default=MAX_CHARS,
                    help="이보다 큰 토막은 길이로 다시 자른다")
    ap.add_argument("--rows", type=int, default=0,
                    help="찍을 토막 수. 0 이면 전부(기본)")
    a = ap.parse_args(argv)

    src = Path(a.path)
    files = sorted(src.glob("*.txt")) if src.is_dir() else [src]
    if not files:
        print(f"txt 가 없다: {src}", file=sys.stderr)
        return 1
    seen: dict = {}
    for f in files:
        text = load(f)
        key = hashlib.sha1(text.encode("utf-8")).hexdigest()
        if key in seen:
            # **같은 작품이 두 번 들어오면 그 작품에 두 배 가중치를 주는 것과 같다.**
            print(f"{f.name}: {seen[key]} 와 글자까지 같다 -- 건너뛴다")
            continue
        seen[key] = f.name
        units = split(text, a.target, a.min, a.max)
        print(report(f, units, a.rows))
        if a.write:
            man = write(units, f.with_suffix(""))
            print(f"  -> {f.with_suffix('')}/ 에 {man['n']}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
