"""**경기를 받아 원장에 넣는다.** `law/fetch.py` 와 같은 규율이다.

    python3 lol/fetch.py --진단                          # 부르되 **저장 안 한다**
    python3 lol/fetch.py --대회 'LCK/2026 Season'        # 받아서 lol/corpus/ 에
    python3 lol/fetch.py --파일 받은것.csv --출처 'Oracle Elixir'   # 손으로 넣기

출처는 Leaguepedia(lol.fandom.com)의 Cargo API 다. **키가 필요 없다.**

## 받은 것을 그대로 믿지 않는다

`law/fetch.py` 가 "조문 머리(`제N조`)가 하나도 없으면 저장하지 않는다" 고 한 자리다.
인증키 오류 XML 이 원장에 들어가면 심판이 그것을 정답으로 삼는다 -- 여기서는 필드
이름이 하나만 바뀌어도 승자가 전부 빈 값이 되고, 그러면 **레이팅이 조용히 기운다.**

그래서 저장 전에 두 가지를 본다.

    1. 줄이 하나라도 왔는가
    2. `winner` 가 `blue` 나 `red` 와 **글자 그대로 같은가** -- 이것이 스키마 검사다

둘째가 요점이다. 필드 별칭이 틀리면 승자가 딴 값이 되고, 그러면 이 검사가 걸린다.
걸리면 **저장하지 않고 받은 첫 줄을 그대로 찍는다** -- 실제 스키마를 눈으로 보라고.

## 이 코드는 이 컨테이너에서 못 돌려 봤다

에이전트 세션의 조직 egress 정책이 `lol.fandom.com` 을 막는다(실측 2026-09-09:
`connect_rejected`, 403). `law/METHOD.md` 가 arxiv 에 대해 적어 둔 것과 같은 처지다.
그래서 **네트워크 경로는 여기서 검사되지 않았다.** VM 에서 `--진단` 부터 돌려라 --
그 명령은 아무것도 저장하지 않으므로 원장을 더럽힐 수 없다.

파싱과 검사는 네트워크 없이 검사한다(`tests/test_lol_fetch.py`).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lol import corpus as CP                                       # noqa: E402

API = "https://lol.fandom.com/api.php"
UA = "SE-lol-corpus/1.0 (https://github.com/gyul56720/se)"
PAGE = 500          # Cargo 의 한 번 상한

# 우리 칸 <- Cargo 필드. **별칭으로 받는다** -- 필드 이름이 바뀌면 별칭이 안 붙어서
# 아래 검사가 걸리고, 조용히 빈 값이 실리지 않는다.
FIELDS = {
    "date": "SG.DateTime_UTC",
    "blue": "SG.Team1",
    "red": "SG.Team2",
    "winner": "SG.WinTeam",
    "tournament": "SG.Tournament",
    "patch": "SG.Patch",
}


def query_url(where: str, offset: int = 0, limit: int = PAGE) -> str:
    fields = ",".join(f"{src}={dst}" for dst, src in FIELDS.items())
    q = {
        "action": "cargoquery", "format": "json",
        "tables": "ScoreboardGames=SG", "fields": fields, "where": where,
        "order_by": "SG.DateTime_UTC ASC", "limit": str(limit), "offset": str(offset),
    }
    return f"{API}?{urllib.parse.urlencode(q)}"


def get(url: str, timeout: float = 30.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:   # noqa: S310
        return json.loads(r.read().decode("utf-8", errors="replace"))


def rows_of(payload: dict) -> list:
    """Cargo 응답 -> 우리 칸의 dict 목록. **꼴이 다르면 빈 목록이다.**"""
    items = payload.get("cargoquery")
    if not isinstance(items, list):
        return []
    out = []
    for it in items:
        t = it.get("title") if isinstance(it, dict) else None
        if isinstance(t, dict):
            out.append({k: (str(t.get(k) or "").strip()) for k in FIELDS})
    return out


def inspect(rows: list) -> dict:
    """저장해도 되는가. **판정하고 왜 그런지 같이 돌려준다.**"""
    good = [r for r in rows if r["winner"] and r["winner"] in (r["blue"], r["red"])]
    bad = [r for r in rows if r not in good]
    ok = bool(rows) and len(good) >= max(1, int(len(rows) * 0.8))
    return {"받은것": len(rows), "쓸것": len(good), "버릴것": len(bad),
            "통과": ok, "good": good, "bad": bad[:3]}


def save(rows: list, out: Path, source: str, note: str = "") -> int:
    """머리글 한 줄 + 경기 한 줄씩. **머리글이 없으면 corpus.load 가 안 읽는다.**"""
    out.parent.mkdir(parents=True, exist_ok=True)
    head = {"_원장": "lol", "받은날": date.today().isoformat(),
            "출처": source, "질의": note, "경기수": len(rows)}
    with out.open("w", encoding="utf-8") as f:
        f.write(json.dumps(head, ensure_ascii=False) + "\n")
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


def from_file(path: Path) -> list:
    """손으로 넣는 길. CSV 든 JSON 이든 받아서 우리 칸으로 옮긴다.

    네트워크가 막힌 자리에서도 원장을 채울 수 있어야 한다 -- 그리고 이 길로 들어온
    것도 **같은 검사를 받는다.** 손으로 넣었다고 봐주면 그 자리가 구멍이 된다.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json" or text.lstrip().startswith(("[", "{")):
        data = json.loads(text)
        raw = data if isinstance(data, list) else data.get("games", [])
    else:
        import csv
        import io
        raw = list(csv.DictReader(io.StringIO(text)))
    # 흔한 다른 이름들을 받아 준다. 못 알아본 칸은 빈 값이고, 그러면 검사가 잡는다.
    alt = {"date": ("date", "DateTime UTC", "DateTime_UTC", "gamedate", "일시"),
           "blue": ("blue", "Team1", "team1", "blueteam", "블루"),
           "red": ("red", "Team2", "team2", "redteam", "레드"),
           "winner": ("winner", "WinTeam", "winteam", "승자"),
           "tournament": ("tournament", "Tournament", "league", "대회"),
           "patch": ("patch", "Patch", "패치")}
    out = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        out.append({k: str(next((r[n] for n in names if r.get(n) not in (None, "")), "")).strip()
                    for k, names in alt.items()})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="경기를 받아 원장에 넣는다")
    ap.add_argument("--대회", dest="tournament", default="",
                    help="Leaguepedia 대회 이름 (예: 'LCK/2026 Season/Summer Season')")
    ap.add_argument("--where", default="", help="Cargo where 절을 통째로")
    ap.add_argument("--파일", dest="file", default="", help="CSV/JSON 을 손으로 넣는다")
    ap.add_argument("--출처", dest="source", default="", help="--파일 일 때 출처를 적는다")
    ap.add_argument("--진단", dest="diag", action="store_true",
                    help="부르되 **저장하지 않는다**. 원장을 더럽힐 수 없다")
    ap.add_argument("--최대", dest="cap", type=int, default=2000)
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)

    # ── 손으로 넣는 길 ────────────────────────────────────────────────
    if a.file:
        if not a.source:
            print("--파일 로 넣을 때는 --출처 를 적어라. 어디서 온 것인지 모르는 "
                  "원장은 못 쓴다.")
            return 2
        rows = from_file(Path(a.file))
        v = inspect(rows)
        print(f"읽은 것 {v['받은것']}줄 · 쓸 것 {v['쓸것']} · 버릴 것 {v['버릴것']}")
        if not v["통과"]:
            print("**저장하지 않는다** -- 승자가 두 팀 중 하나가 아닌 줄이 너무 많다.")
            for r in v["bad"]:
                print(f"    {r}")
            return 1
        out = Path(a.out) if a.out else CP.CORPUS_DIR / f"{Path(a.file).stem}.jsonl"
        n = save(v["good"], out, a.source, f"파일: {a.file}")
        print(f"저장: {out}  ({n}경기)")
        return 0

    # ── 받아 오는 길 ──────────────────────────────────────────────────
    where = a.where or (f'SG.Tournament LIKE "%{a.tournament}%"' if a.tournament else "")
    if not where:
        print("--대회 나 --where 중 하나는 있어야 한다.")
        return 2

    rows, offset = [], 0
    while len(rows) < a.cap:
        url = query_url(where, offset)
        try:
            got = rows_of(get(url))
        except Exception as e:                                # noqa: BLE001
            print(f"못 받았다: {type(e).__name__}: {str(e)[:160]}")
            print(f"  질의: {url[:200]}")
            print("  에이전트 컨테이너에서는 lol.fandom.com 이 막혀 있다(egress 정책). "
                  "VM 에서 돌려라.")
            return 1
        if not got:
            break
        rows += got
        offset += PAGE
        if len(got) < PAGE:
            break

    v = inspect(rows)
    print(f"받은 것 {v['받은것']}줄 · 쓸 것 {v['쓸것']} · 버릴 것 {v['버릴것']}")
    if not v["통과"]:
        print("**저장하지 않는다** -- `winner` 가 `blue`/`red` 와 안 맞는다. "
              "필드 별칭이 바뀌었을 수 있다. 받은 첫 줄을 그대로 찍는다:")
        for r in (rows[:2] or [{}]):
            print(f"    {r}")
        return 1
    if a.diag:
        print("**--진단 이므로 저장하지 않는다.** 위 수가 그럴듯하면 --진단 을 떼고 다시.")
        for r in v["good"][:3]:
            print(f"    {r}")
        return 0
    stem = (a.tournament or "cargo").replace("/", "_").replace(" ", "_")
    out = Path(a.out) if a.out else CP.CORPUS_DIR / f"{stem}.jsonl"
    n = save(v["good"], out, "lol.fandom.com Cargo ScoreboardGames", where)
    print(f"저장: {out}  ({n}경기)")
    print(f"다음: python3 lol/score.py            # 이 원장에서 모델이 기준선을 이기나")
    print(f"      python3 lol/predict.py T1 HLE   # 승률")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
