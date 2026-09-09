"""**받은 것을 그대로 믿지 않는가** -- 네트워크 없이 검사한다.

    python3 tests/test_lol_fetch.py

이 검사가 왜 특히 중요한가: **네트워크 경로는 에이전트 컨테이너에서 못 돌려 봤다**
(egress 정책이 lol.fandom.com 을 막는다, 실측 2026-09-09 `connect_rejected`).
그러니 "받아 보니 되더라" 로는 아무것도 못 말한다. 대신 **받았다고 치고** 그 응답을
넣었을 때 저장 판정이 어떻게 되는지를 붙든다.

제일 무서운 갈래는 실패가 아니라 **조용한 성공**이다. Cargo 필드 이름이 하나 바뀌면
`winner` 가 빈 값으로 오는데, 그것을 저장해 버리면 레이팅이 조용히 기운다.
`law/fetch.py` 가 인증키 오류 XML 을 두고 겪은 그 자리다.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lol import corpus as CP                                       # noqa: E402
from lol import fetch as FT                                        # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


def cargo(*rows):
    """Cargo 가 돌려주는 꼴 그대로."""
    return {"cargoquery": [{"title": r} for r in rows]}


GOOD = [{"date": "2026-01-15 09:00:00", "blue": "T1", "red": "Gen.G",
         "winner": "T1", "tournament": "LCK/2026", "patch": "16.1"},
        {"date": "2026-01-16 09:00:00", "blue": "Hanwha Life Esports", "red": "T1",
         "winner": "T1", "tournament": "LCK/2026", "patch": "16.1"}]

print("── 질의를 옳게 짜는가 ─────────────────────────────────")
u = FT.query_url('SG.Tournament LIKE "%LCK%"', offset=500)
ok("action=cargoquery" in u and "format=json" in u, "action 과 format")
ok("ScoreboardGames" in u, "표 이름이 실린다")
ok("offset=500" in u, "쪽 넘기기가 실린다")
for src, dst in (("SG.WinTeam", "winner"), ("SG.Team1", "blue"), ("SG.Team2", "red")):
    ok(f"{src}%3D{dst}" in u or f"{src}={dst}" in u.replace("%3D", "="),
       f"**별칭으로 받는다**: {src} -> {dst}")
ok("order_by" in u and "ASC" in u.replace("%20", " ").replace("+", " "),
   "시간순으로 받는다 -- walk 가 시간순을 전제한다")

print()
print("── 응답 꼴 ───────────────────────────────────────────")
ok(FT.rows_of(cargo(*GOOD)) == GOOD, "Cargo 꼴을 우리 칸으로 옮긴다")
ok(FT.rows_of({}) == [], "빈 응답 -> 빈 목록")
ok(FT.rows_of({"error": {"code": "badquery"}}) == [],
   "**오류 응답을 경기로 안 읽는다** -- law 가 인증키 오류 XML 로 겪은 자리")
ok(FT.rows_of({"cargoquery": "이건 목록이 아니다"}) == [], "꼴이 다르면 빈 목록")
ok(FT.rows_of(cargo({"blue": "T1"}))[0]["winner"] == "",
   "없는 칸은 빈 문자열이다 -- None 이 아니라")

print()
print("── **스키마가 어긋나면 저장하지 않는다** ────────────────")
v = FT.inspect(GOOD)
ok(v["통과"] and v["쓸것"] == 2, "멀쩡한 것은 통과")

drift = [{**g, "winner": ""} for g in GOOD]
ok(not FT.inspect(drift)["통과"],
   "**승자가 빈 값이면 안 받는다** -- 필드 별칭이 바뀐 모습이다")

wrong = [{**g, "winner": "어느 쪽도 아닌 팀"} for g in GOOD]
ok(not FT.inspect(wrong)["통과"], "승자가 두 팀 중 하나가 아니어도 안 받는다")

ok(not FT.inspect([])["통과"], "한 줄도 안 왔으면 안 받는다")

mixed = GOOD * 5 + drift          # 10 좋음 + 2 나쁨 = 83%
ok(FT.inspect(mixed)["통과"] and FT.inspect(mixed)["버릴것"] == 2,
   "몇 줄쯤 깨진 것은 그 줄만 버리고 통과 (10/12)")
mostly_bad = GOOD + drift * 5     # 2 좋음 + 10 나쁨 = 17%
ok(not FT.inspect(mostly_bad)["통과"],
   "대부분이 깨졌으면 **통째로 안 받는다** -- 그건 줄 문제가 아니라 스키마 문제다")

print()
print("── 손으로 넣는 길도 **같은 검사를 받는다** ──────────────")
with tempfile.TemporaryDirectory() as d:
    csv = Path(d) / "a.csv"
    csv.write_text("DateTime UTC,Team1,Team2,WinTeam,Tournament\n"
                   "2026-02-01 10:00:00,T1,DRX,T1,LCK\n"
                   "2026-02-02 10:00:00,DRX,T1,T1,LCK\n", encoding="utf-8")
    rows = FT.from_file(csv)
    ok(len(rows) == 2 and rows[0]["blue"] == "T1" and rows[0]["winner"] == "T1",
       "Oracle Elixir 식 칸 이름(DateTime UTC/Team1/WinTeam)을 알아본다")
    ok(FT.inspect(rows)["통과"], "그리고 같은 검사를 통과한다")

    js = Path(d) / "b.json"
    js.write_text(json.dumps([{"date": "2026-02-03", "blue": "A", "red": "B",
                               "winner": "A"}]), encoding="utf-8")
    ok(FT.from_file(js)[0]["blue"] == "A", "JSON 배열도 받는다")

    bad = Path(d) / "c.csv"
    bad.write_text("날짜,팀1,팀2\n2026-02-01,T1,DRX\n", encoding="utf-8")
    ok(not FT.inspect(FT.from_file(bad))["통과"],
       "**못 알아본 칸은 빈 값이 되고 검사가 잡는다** -- 손으로 넣었다고 안 봐준다")

print()
print("── 저장 -> 원장 왕복 ─────────────────────────────────")
with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "lck.jsonl"
    n = FT.save(GOOD, out, "검사용 출처", "where 절")
    ok(n == 2, "두 경기를 적었다")
    head = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    ok(head["_원장"] == "lol" and head["출처"] == "검사용 출처" and head.get("받은날"),
       "**첫 줄이 머리글이다** -- 출처와 받은 날짜가 거기 있다")
    c = CP.load(d)
    ok(len(c) == 2, f"corpus.load 가 그대로 읽는다 ({len(c)}경기)")
    ok(c.games[0].blue == "T1" and c.games[0].blue_won,
       "왕복해도 승패가 안 뒤집힌다")
    ok([g.date for g in c.games] == sorted(g.date for g in c.games),
       "시간순으로 정렬돼 나온다")

print()
print("── 저장 안 하는 길 ───────────────────────────────────")
with tempfile.TemporaryDirectory() as d:
    code = FT.main(["--파일", "없는파일.csv", "--출처", ""])
    ok(code == 2, "--파일 인데 --출처 가 없으면 끝값 2 -- 어디서 온 것인지 모르는 원장은 못 쓴다")
    ok(FT.main([]) == 2, "--대회 도 --where 도 없으면 끝값 2")

print()
if fails:
    print(f"받아오기: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("질의 · 응답 파싱 · **스키마 어긋남 거절** · 손으로 넣기 · 왕복 -- 통과")
print("  (네트워크 경로 자체는 이 컨테이너에서 막혀 있어 검사되지 않았다 -- VM 에서 --진단)")
