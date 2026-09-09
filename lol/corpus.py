"""**경기 원장.** law/corpus.py 가 조문에 대해 하는 일을 프로 경기에 대해 한다.

    python3 lol/corpus.py                 # 원장에 무엇이 담겼나
    python3 lol/corpus.py --팀            # 팀마다 몇 경기인가

## 언제 것인지 모르는 원장은 못 쓴다

`law/fetch.py` 가 조문 파일 첫 줄에 시행일자와 받은 날짜를 적는 것과 같다. 여기서는
JSONL 첫 줄이 **머리글**이고, 머리글이 없는 파일은 **안 읽는다.** 승률 예측에서 이게
법보다 더 중요하다 -- 조문은 몇 달 그대로지만 레이팅은 **어제 경기 하나로 바뀐다.**
언제까지의 원장인지 모르면 그 승률이 무엇의 승률인지 아무도 모른다.

## 이름은 원장이 정한다

`T1` 이 `T1` 인지 `SKT T1` 인지는 우리가 정하는 것이 아니라 원장에 적힌 대로다.
별칭(`ALIASES`)은 **원장에 실재하는 이름으로만** 풀린다 -- 없는 이름으로 풀리면
그것은 지어낸 것이고, 지어낸 이름으로 낸 승률은 지어낸 승률이다.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS_DIR = HERE / "corpus"

# 사람이 부르는 이름 -> 원장에 적힌 이름의 **후보들**. 원장에 있는 것만 쓴다.
# 여기 없는 이름을 지어내지 않는다 -- 못 찾으면 못 찾았다고 말하는 것이 답이다.
ALIASES = {
    "t1": ["T1", "SK Telecom T1"],
    "skt": ["T1", "SK Telecom T1"],
    "hle": ["Hanwha Life Esports"],
    "한화생명": ["Hanwha Life Esports"],
    "한화": ["Hanwha Life Esports"],
    "젠지": ["Gen.G"],
    "geng": ["Gen.G"],
    "gen": ["Gen.G"],
    "kt": ["KT Rolster"],
    "담원": ["Dplus KIA", "DWG KIA", "DAMWON Gaming"],
    "dk": ["Dplus KIA", "DWG KIA"],
    "드플": ["Dplus KIA"],
    "농심": ["Nongshim RedForce"],
    "광동": ["Kwangdong Freecs"],
    "브리온": ["BNK FearX", "Fredit BRION"],
    "디알엑스": ["DRX"],
    "drx": ["DRX"],
}


@dataclass
class Game:
    date: str = ""          # "2026-01-15 09:00:00" (UTC)
    blue: str = ""
    red: str = ""
    winner: str = ""        # blue 또는 red 와 글자 그대로 같아야 한다
    tournament: str = ""
    patch: str = ""

    @property
    def blue_won(self) -> bool:
        return self.winner == self.blue


@dataclass
class Corpus:
    games: list = field(default_factory=list)
    headers: list = field(default_factory=list)
    dropped: int = 0        # 꼴이 안 맞아 안 실은 줄. **조용히 빼지 않는다**

    def __len__(self) -> int:
        return len(self.games)

    @property
    def last_date(self) -> str:
        return self.games[-1].date if self.games else ""

    @property
    def first_date(self) -> str:
        return self.games[0].date if self.games else ""

    def teams(self) -> dict:
        """팀 -> 경기 수."""
        n = {}
        for g in self.games:
            n[g.blue] = n.get(g.blue, 0) + 1
            n[g.red] = n.get(g.red, 0) + 1
        return n

    def resolve(self, name: str) -> tuple:
        """사람이 친 이름 -> (원장에 적힌 이름, 왜). **못 찾으면 지어내지 않는다.**

        돌려주는 둘째 값이 후보 목록이다 -- 여럿이면 고르지 않고 사람에게 묻는다.
        하나로 좁혀지지 않은 것을 임의로 고르면, 그 뒤의 승률은 **다른 팀의 승률**이다.
        """
        have = self.teams()
        if name in have:
            return name, [name]
        low = {t.lower(): t for t in have}
        if name.lower() in low:
            return low[name.lower()], [low[name.lower()]]
        for cand in ALIASES.get(name.lower().replace(" ", ""), []):
            if cand in have:
                return cand, [cand]
        hits = [t for t in have if name.lower() in t.lower()]
        return (hits[0], hits) if len(hits) == 1 else (None, hits)


def _row(d: dict) -> Game | None:
    """한 줄을 경기로. **승자가 두 팀 중 하나가 아니면 안 받는다.**

    실측으로 이 자리가 무섭다: Cargo 가 무승부·몰수·미기록 경기에 빈 `winner` 를
    돌려주는데, 그것을 0.5 로 세거나 blue 로 세면 레이팅이 조용히 기운다. 원장은
    **모르는 경기를 안 받는 편**이 낫다 -- 미검증은 통과가 아니다.
    """
    g = Game(date=str(d.get("date") or ""), blue=str(d.get("blue") or ""),
             red=str(d.get("red") or ""), winner=str(d.get("winner") or ""),
             tournament=str(d.get("tournament") or ""), patch=str(d.get("patch") or ""))
    if not (g.date and g.blue and g.red):
        return None
    if g.blue == g.red:                       # 같은 팀끼리는 경기가 아니다
        return None
    if g.winner not in (g.blue, g.red):       # 승자가 안 적혔거나 딴 이름이다
        return None
    return g


def load(path=None) -> Corpus:
    """원장 디렉터리의 `*.jsonl` 을 전부 읽는다. **머리글 없는 파일은 안 읽는다.**"""
    root = Path(path or CORPUS_DIR)
    c = Corpus()
    if not root.is_dir():
        return c
    seen = set()
    for f in sorted(root.glob("*.jsonl")):
        lines = [l for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not lines:
            continue
        try:
            head = json.loads(lines[0])
        except json.JSONDecodeError:
            c.dropped += len(lines)
            continue
        if not isinstance(head, dict) or "_원장" not in head:
            # 언제 것인지 모르는 원장은 못 쓴다. 통째로 안 읽는다.
            c.dropped += len(lines)
            continue
        c.headers.append({"파일": f.name, **head})
        for line in lines[1:]:
            try:
                g = _row(json.loads(line))
            except json.JSONDecodeError:
                g = None
            if g is None:
                c.dropped += 1
                continue
            key = (g.date, g.blue, g.red)
            if key in seen:                   # 같은 경기를 두 번 세면 레이팅이 두 배 움직인다
                continue
            seen.add(key)
            c.games.append(g)
    c.games.sort(key=lambda g: (g.date, g.blue, g.red))
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="경기 원장에 무엇이 담겼나")
    ap.add_argument("--경로", dest="path", default=str(CORPUS_DIR))
    ap.add_argument("--팀", dest="show_teams", action="store_true")
    a = ap.parse_args(argv)

    c = load(a.path)
    if not c.games:
        print(f"원장이 비어 있다: {a.path}")
        print("  python3 lol/fetch.py --대회 'LCK/2026 Season' 로 먼저 받아라")
        return 3
    print(f"경기 {len(c)}개 · {c.first_date[:10]} ~ {c.last_date[:10]} · 팀 {len(c.teams())}개")
    for h in c.headers:
        print(f"  {h['파일']}  받은날 {h.get('받은날', '?')}  출처 {h.get('출처', '?')}")
    if c.dropped:
        print(f"  **안 실은 줄 {c.dropped}개** (승자가 두 팀 중 하나가 아니거나 꼴이 안 맞다)")
    if a.show_teams:
        print()
        for t, n in sorted(c.teams().items(), key=lambda kv: -kv[1]):
            print(f"  {n:>4}경기  {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
