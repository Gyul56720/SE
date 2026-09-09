"""**계산이 맞는가** -- Elo·다전제·진영 이점. LLM 도 네트워크도 필요 없다.

    python3 tests/test_lol_elo.py

여기서 제일 중요한 검사는 `look-ahead` 다. 경기를 걸으며 레이팅을 갱신할 때 **그
경기로 갱신한 뒤에** 그 경기를 예측하면 답을 보고 찍는 것이고, 그러면 백테스트가
아름답게 나오고 실전에서 무너진다. 그 사고는 **화면에서 안 보인다** -- 점수가 좋아
보일 뿐이다. 그래서 검사가 그 자리를 붙든다.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lol import corpus as CP                                       # noqa: E402
from lol import elo as EL                                          # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


def g(date, blue, red, winner):
    return CP.Game(date=date, blue=blue, red=red, winner=winner)


print("── 공식 ──────────────────────────────────────────────")
ok(abs(EL.expect(1500, 1500) - 0.5) < 1e-12, "같은 레이팅이면 정확히 0.5")
ok(abs(EL.expect(1900, 1500) - 10 / 11) < 1e-9,
   f"400점 차이는 10:1 이다 ({EL.expect(1900, 1500):.4f})")
ok(abs(EL.expect(1500, 1900) + EL.expect(1900, 1500) - 1.0) < 1e-12,
   "두 방향의 합은 1")
ok(abs(EL.to_elo(EL.expect(1600, 1500)) - 100.0) < 1e-6,
   "to_elo 는 expect 의 역함수다 -- 승률과 점수의 단위를 잇는 자리")

print()
print("── **예측이 갱신보다 먼저다** (look-ahead) ─────────────")
games = [g("2026-01-01", "A", "B", "A")]
_, rows, _ = EL.walk(games, bias=0.0)
ok(abs(rows[0]["p_blue"] - 0.5) < 1e-12,
   f"첫 경기의 예측은 0.5 여야 한다 -- 둘 다 1500 이므로 (실제 {rows[0]['p_blue']:.4f})")

r, rows, _ = EL.walk([g("2026-01-01", "A", "B", "A"),
                      g("2026-01-02", "A", "B", "A")], bias=0.0)
ok(rows[1]["p_blue"] > 0.5,
   f"두 번째 경기는 첫 경기를 반영해 0.5 를 넘어야 한다 ({rows[1]['p_blue']:.4f})")
ok(rows[1]["p_blue"] < 1.0, "그래도 1.0 은 아니다 -- 한 경기가 전부를 정하지 않는다")
ok(r["A"] > 1500 > r["B"], "이긴 쪽이 오르고 진 쪽이 내린다")
ok(abs((r["A"] - 1500) + (r["B"] - 1500)) < 1e-9,
   "오른 만큼 내린다 -- 총합이 보존된다(제로섬)")

print()
print("── 몇 경기째인가를 옳게 세는가 (몸풀기 제외용) ─────────")
_, rows, _ = EL.walk([g("2026-01-01", "A", "B", "A"),
                      g("2026-01-02", "A", "C", "C"),
                      g("2026-01-03", "B", "C", "B")], bias=0.0)
ok(rows[0]["n_blue"] == 0 and rows[0]["n_red"] == 0, "첫 경기는 둘 다 0경기째")
ok(rows[1]["n_blue"] == 1 and rows[1]["n_red"] == 0, "A 는 1경기, C 는 0경기")
ok(rows[2]["n_blue"] == 1 and rows[2]["n_red"] == 1, "B 도 C 도 각각 1경기 치렀다")

print()
print("── 진영 이점은 **재는 것**이지 선언이 아니다 ───────────")
few = [g(f"2026-01-{i+1:02d}", "A", "B", "A") for i in range(10)]
ok(EL.side_bias(few) == 0.0,
   f"경기가 {len(few)}개뿐이면 0.0 -- 모르는 것을 그럴듯한 값으로 안 채운다")

many = ([g(f"2026-02-{i+1:02d}", "A", "B", "A") for i in range(60)]
        + [g(f"2026-03-{i+1:02d}", "A", "B", "B") for i in range(40)])
b = EL.side_bias(many)
ok(b > 0, f"블루가 60% 이기면 진영 이점이 양수다 ({b:+.1f} Elo)")
ok(abs(b - EL.to_elo(0.6)) < 1e-9,
   f"그 값은 승률 0.6 을 만드는 레이팅 차이와 같아야 한다 ({EL.to_elo(0.6):.1f})")
ok(EL.side_bias([]) == 0.0, "빈 원장에서 0.0 -- 나눗셈으로 안 죽는다")

print()
print("── 다전제 ────────────────────────────────────────────")
ok(abs(EL.series(0.6, 1) - 0.6) < 1e-12, "Bo1 은 그대로")
ok(abs(EL.series(0.5, 5) - 0.5) < 1e-12, "반반이면 Bo5 도 반반")
ok(abs(EL.series(0.6, 3) - 0.648) < 1e-9, f"Bo3 p=0.6 -> 0.648 ({EL.series(0.6, 3):.6f})")
ok(abs(EL.series(0.6, 5) - 0.68256) < 1e-9, f"Bo5 p=0.6 -> 0.68256 ({EL.series(0.6, 5):.6f})")
ok(abs(EL.series(0.6, 5) + EL.series(0.4, 5) - 1.0) < 1e-12, "양쪽 합은 1")
ok(EL.series(0.6, 5) > EL.series(0.6, 3) > EL.series(0.6, 1),
   "**판이 길수록 센 쪽이 유리하다** -- 다전제가 우연을 걷어낸다")

print()
print("── 합성 원장에서 **세기 순서를 되찾는가** ──────────────")
# 정답을 아는 세계를 만든다. 팀마다 진짜 세기를 주고, 그 세기대로 승패를 뽑는다.
# 그러면 "우리 파이프라인이 그 순서를 되찾는가" 를 실제로 잴 수 있다 --
# mathdrift 의 `recall.py` 가 Strassen 을 시금석으로 삼는 것과 같은 자리다.
TRUE = {"S": 1800, "A": 1650, "B": 1500, "C": 1350, "D": 1200}
rng = random.Random(20260909)
teams = list(TRUE)
synth = []
for i in range(1200):
    x, y = rng.sample(teams, 2)
    p = EL.expect(TRUE[x], TRUE[y])
    synth.append(g(f"2026-{1 + i // 300:02d}-{1 + i % 28:02d}", x, y,
                   x if rng.random() < p else y))

r, _, _ = EL.walk(synth, bias=0.0)
order = [t for t, _ in sorted(r.items(), key=lambda kv: -kv[1])]
ok(order == ["S", "A", "B", "C", "D"],
   f"진짜 순서를 되찾았다: {' > '.join(order)}")
spread = r["S"] - r["D"]
ok(400 < spread < 900,
   f"S 와 D 의 차이 {spread:.0f} 는 진짜 차이 600 근처다 -- 크기까지 얼추 맞는다")
print(f"       되찾은 레이팅: " + " · ".join(f"{t} {r[t]:.0f}(참 {TRUE[t]})" for t in order))

print()
if fails:
    print(f"Elo: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("Elo 계산 · look-ahead 없음 · 진영 이점 측정 · 다전제 · 세기 회수 -- 통과")
