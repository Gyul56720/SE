"""**거절이 제대로 되는가** -- 원장이 못 받치는 승률을 안 내놓는가.

    python3 tests/test_lol_predict.py

이 파일이 붙드는 것은 정확도가 아니라 **입 다무는 능력**이다. 공개 채널에서 난 사고는
둘인데(실측 2026-09-09) 방향이 정반대다:

    도구를 안 써 보고 "불가능하다"        -- 할 수 있는데 안 했다
    데이터 없이 "55% 대 45%"             -- 못 하는데 한 척했다

둘째가 더 나쁘다. 화면에서 지어낸 55% 와 계산한 55% 는 똑같이 생겼기 때문이다.
`predict.py` 는 못 받치면 끝값 3 으로 나가야 하고, 그때 화면에 숫자가 없어야 한다.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lol import corpus as CP                                       # noqa: E402
from lol import predict as PD                                      # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


def write(dirpath, name, rows, head=True):
    p = Path(dirpath) / name
    lines = []
    if head:
        lines.append(json.dumps({"_원장": "lol", "받은날": "2026-09-09",
                                 "출처": "검사"}, ensure_ascii=False))
    lines += [json.dumps(r, ensure_ascii=False) for r in rows]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def game(d, b, r, w, **kw):
    return {"date": d, "blue": b, "red": r, "winner": w, **kw}


def run(argv):
    """predict.main 을 부르고 (끝값, 화면) 을 돌려준다."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = PD.main(argv)
    return code, buf.getvalue()


def league(n=12):
    """A~D 가 서로 도는 원장. 각 팀이 몸풀기를 넘길 만큼."""
    teams = ["A팀", "B팀", "C팀", "D팀"]
    out = []
    for i in range(n):
        b, r = teams[i % 4], teams[(i + 1) % 4]
        out.append(game(f"2026-0{1 + i // 28}-{1 + i % 28:02d}", b, r,
                        b if i % 3 else r))
    return out


print("── 원장: 머리글 없는 파일은 **안 읽는다** ──────────────")
with tempfile.TemporaryDirectory() as d:
    write(d, "머리글없음.jsonl", league(8), head=False)
    c = CP.load(d)
    ok(len(c) == 0, "머리글이 없으면 한 줄도 안 싣는다 -- 언제 것인지 모르는 원장은 못 쓴다")
    ok(c.dropped > 0, f"안 실었다는 것을 세어 둔다 ({c.dropped}줄) -- 조용히 빼지 않는다")

with tempfile.TemporaryDirectory() as d:
    write(d, "좋음.jsonl", league(8))
    c = CP.load(d)
    ok(len(c) == 8, f"머리글이 있으면 읽는다 ({len(c)}경기)")
    ok(c.headers and c.headers[0]["받은날"] == "2026-09-09", "받은 날짜를 들고 있다")

print()
print("── 원장: 승자가 두 팀 중 하나가 아니면 **안 받는다** ────")
with tempfile.TemporaryDirectory() as d:
    write(d, "섞임.jsonl", [
        game("2026-01-01", "A팀", "B팀", "A팀"),
        game("2026-01-02", "A팀", "B팀", ""),            # 무승부·미기록
        game("2026-01-03", "A팀", "B팀", "C팀"),          # 딴 팀이 승자
        game("2026-01-04", "A팀", "A팀", "A팀"),          # 자기끼리
        game("2026-01-05", "", "B팀", "B팀"),             # 팀이 빔
    ])
    c = CP.load(d)
    ok(len(c) == 1, f"쓸 수 있는 한 줄만 실린다 ({len(c)}경기)")
    ok(c.dropped == 4, f"나머지 넷을 세어 둔다 ({c.dropped}) -- 0.5 로 세면 레이팅이 기운다")

print()
print("── 원장: 같은 경기를 두 번 세지 않는다 ─────────────────")
with tempfile.TemporaryDirectory() as d:
    write(d, "가.jsonl", [game("2026-01-01", "A팀", "B팀", "A팀")])
    write(d, "나.jsonl", [game("2026-01-01", "A팀", "B팀", "A팀")])
    ok(len(CP.load(d)) == 1, "두 파일에 같은 경기가 있어도 하나로 센다 -- "
                             "두 번 세면 레이팅이 두 배 움직인다")

print()
print("── 이름: 못 좁히면 **고르지 않는다** ───────────────────")
with tempfile.TemporaryDirectory() as d:
    write(d, "l.jsonl", league(12) + [game("2026-03-01", "T1", "Hanwha Life Esports", "T1")])
    c = CP.load(d)
    ok(c.resolve("T1")[0] == "T1", "정확히 같은 이름")
    ok(c.resolve("t1")[0] == "T1", "대소문자만 다른 것도 찾는다")
    ok(c.resolve("HLE")[0] == "Hanwha Life Esports", "별칭 HLE -> 원장의 이름")
    ok(c.resolve("한화생명")[0] == "Hanwha Life Esports", "한글 별칭도")
    got, cands = c.resolve("팀")
    ok(got is None and len(cands) > 1,
       f"'팀' 처럼 여럿에 걸리면 **None 이다** (후보 {len(cands)}개) -- 임의로 고르면 "
       "다른 팀의 승률을 내놓는 것이다")
    got, cands = c.resolve("없는팀")
    ok(got is None and cands == [], "아예 없으면 None 이고 후보도 없다")
    ok(c.resolve("Gen.G")[0] is None,
       "별칭 표에 있어도 **원장에 없으면 안 푼다** -- 없는 이름을 지어내지 않는다")

print()
print("── predict: 못 받치면 끝값 3 이고 **화면에 숫자가 없다** ─")
with tempfile.TemporaryDirectory() as d:
    code, out = run(["A팀", "B팀", "--경로", d])
    ok(code == 3, "빈 원장 -> 끝값 3")
    ok("미검증" in out and "%" not in out, "미검증이라 적고 승률을 안 찍는다")
    ok("fetch.py" in out, "무엇을 하라고 알려 준다")

with tempfile.TemporaryDirectory() as d:
    write(d, "l.jsonl", league(12))
    code, out = run(["없는팀", "A팀", "--경로", d])
    ok(code == 3 and "미검증" in out, "원장에 없는 팀 -> 끝값 3")
    ok("%" not in out, "그때도 숫자를 안 찍는다")

    code, out = run(["팀", "A팀", "--경로", d])
    ok(code == 3 and "후보" in out, "여럿에 걸리면 후보를 보여 주고 끝값 3")

    write(d, "적음.jsonl", [game("2026-05-01", "새팀", "A팀", "새팀")])
    code, out = run(["새팀", "A팀", "--경로", d])
    ok(code == 3, "몸풀기 미만인 팀 -> 끝값 3")
    ok("1500" in out and "%" not in out,
       "왜 못 내는지(시작값에서 안 움직였다)를 적고 숫자는 안 찍는다")

print()
print("── predict: 받칠 수 있으면 **숫자와 성적을 같이** 찍는다 ─")
with tempfile.TemporaryDirectory() as d:
    write(d, "l.jsonl", league(60))
    code, out = run(["A팀", "B팀", "--경로", d])
    ok(code == 0, "끝값 0")
    ok("%" in out, "승률을 찍는다")
    ok("브라이어" in out or "못 쟀다" in out,
       "**승률 옆에 그 승률의 성적이 반드시 있다** -- 하나만 적으면 검사받지 않은 "
       "숫자를 검사받은 것으로 읽는다")
    ok("모델이 안 보는 것" in out and "로스터" in out,
       "무엇을 안 보는 모델인지 매번 같이 적는다")
    ok("블루" in out and "레드" in out and "진영 모름" in out,
       "진영별로 갈라 찍는다 -- 하나로 뭉개면 어느 가정의 값인지 사라진다")

    code, bo5 = run(["A팀", "B팀", "--경로", d, "--세트", "5"])
    ok("Bo5" in bo5 and "독립" in bo5,
       "다전제를 물으면 독립 가정이라는 한계를 같이 적는다")

    code, out = run(["--경로", d, "--팀"])
    ok(code == 0 and "A팀" in out, "--팀 은 원장에 있는 이름을 그대로 보여 준다")

print()
if fails:
    print(f"예측: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("원장 검사 · 이름 좁히기 · **거절 네 갈래** · 승률과 성적 나란히 -- 통과")
