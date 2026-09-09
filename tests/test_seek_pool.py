r"""seek 가 **제 반복문을 짜지 않고** orchestrator/llm_pool 로 나가는가.

llm_pool.py 는 729줄인데 그 대부분이 하나를 아는 데 쓰인다 -- **429 가 두 가지라는
것.** 분당 한도는 60초면 풀리고 오늘 치 소진은 자정까지 간다. 둘을 같게 다루면
멀쩡한 키를 하루 종일 봉인한다(tests/test_llm_pool_rpm.py 가 그 자리를 붙든다).

여기서 재는 것은 seek 가 그 앎을 **빌려 쓰는가** 다. 제 for 문으로 키를 돌리면
그 앎이 하나도 안 실린다.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_seek_pool.py
"""
from __future__ import annotations

import io
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import orchestrator                                           # noqa: E402
from seek import spread as SP                                 # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


class FakePool:
    """llm_pool 대역. 무엇을 어떻게 불렀는지만 적는다."""

    def __init__(self, pool=None, blow=0):
        self.pool = [("kA:m0", None), ("kA:m1", None), ("kB:m0", None)] if pool is None else pool
        self.부름 = []
        self.blow = blow                                      # 앞의 몇 번을 터뜨릴까

    def build_pool(self):
        return self.pool

    def call(self, pool, prompt, pool_id="orchestrator", verbose=True, **kw):
        self.부름.append({"pool_id": pool_id, "verbose": verbose, "n": len(pool)})
        if len(self.부름) <= self.blow:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return ('[{"연산자": "자원 풀기", "물음": "x", '
                '"표본": "def sample(rng):\\n    return [1]\\n", '
                '"판정": "def judge(x):\\n    return True\\n", '
                '"옮김": "def embed(x):\\n    return list(x)\\n"}]'), "kA:m0"


class FakeQuota:
    """quota_tracker 대역. 살아 있는 후보 수를 마음대로 정한다."""

    def __init__(self, alive=True):
        self.alive = alive

    def is_dead(self, label):
        return False

    def remaining(self, label, limit=None):
        return 100 if self.alive else 0

    def is_rpm_cooling(self, label):
        return not self.alive


def 갈아끼우고(fake_pool, fake_quota, fn):
    was_p = getattr(orchestrator, "llm_pool", None)
    was_q = sys.modules.get("quota_tracker")
    orchestrator.llm_pool = fake_pool
    sys.modules["orchestrator.llm_pool"] = fake_pool
    sys.modules["quota_tracker"] = fake_quota
    try:
        return fn()
    finally:
        if was_p is None:
            delattr(orchestrator, "llm_pool")
        else:
            orchestrator.llm_pool = was_p
        sys.modules.pop("orchestrator.llm_pool", None)
        if was_q is None:
            sys.modules.pop("quota_tracker", None)
        else:
            sys.modules["quota_tracker"] = was_q


def 원장(tmp: Path) -> Path:
    """seed.json 을 그대로 베껴 쓴다 -- 진짜 원장을 안 건드린다."""
    src = Path(__file__).resolve().parent.parent / "seek" / "seed.json"
    dst = tmp / "led.json"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dst


import tempfile                                               # noqa: E402

TMP = Path(tempfile.mkdtemp())

print("== llm_pool 로 나간다 ==")
_p = FakePool()
_out = io.StringIO()
with redirect_stdout(_out):
    갈아끼우고(_p, FakeQuota(), lambda: SP.main(
        ["--n", "1", "--batch", "1", "--path", str(원장(TMP))]))
ok(len(_p.부름) == 1, f"llm_pool.call 로 간다 -- 딱 한 번 (얻은 값 {len(_p.부름)})")
ok(_p.부름 and _p.부름[0]["pool_id"] == "seek",
   "pool_id 가 'seek' 다  ← 잔량 장부가 다른 파이프라인과 안 섞인다")
ok(_p.부름 and _p.부름[0]["n"] == 3, "풀을 통째로 넘긴다 -- 후보 고르기는 llm_pool 이 한다")

print("\n== 왜 막혔는지 기본으로 보인다 ==")
ok(_p.부름 and _p.부름[0]["verbose"] is True,
   "**verbose 기본이 참이다** -- 끄면 30분 돌고 '호출 실패' 한 줄만 남는다")
_q = FakePool()
with redirect_stdout(io.StringIO()):
    갈아끼우고(_q, FakeQuota(), lambda: SP.main(
        ["--n", "1", "--batch", "1", "--조용히", "--path", str(원장(TMP))]))
ok(_q.부름 and _q.부름[0]["verbose"] is False, "--조용히 를 주면 끈다 -- 고를 수 있게만 한다")

print("\n== 쓸 수 있는 후보가 없으면 안 돈다 ==")
_dead = FakePool()
_out = io.StringIO()
_rc = 갈아끼우고(_dead, FakeQuota(alive=False),
              lambda: (lambda: SP.main(["--n", "20", "--path", str(원장(TMP))]))())
ok(_rc == 3, f"3 을 준다 (얻은 값 {_rc})")
ok(len(_dead.부름) == 0,
   f"**호출을 0회 한다** -- 20바퀴 돌며 429 를 20번 쌓지 않는다 (얻은 값 {len(_dead.부름)})")

_out = io.StringIO()
with redirect_stdout(_out):
    _rc2 = 갈아끼우고(_dead, FakeQuota(alive=False), lambda: SP.check(20, 3))
_t = _out.getvalue()
ok(_rc2 == 3 and "429" in _t, "--점검 이 왜 못 도는지 말한다")
ok("분당 한도로 쉬는 중" in _t, "**60초짜리와 하루짜리를 갈라 찍는다** -- 같게 찍으면 오해한다")

print("\n== 연달아 막히면 남은 바퀴를 안 돈다 ==")
_boom = FakePool(blow=99)
with redirect_stdout(io.StringIO()):
    갈아끼우고(_boom, FakeQuota(), lambda: SP.main(
        ["--n", "30", "--batch", "1", "--path", str(원장(TMP))]))
ok(len(_boom.부름) == 2,
   f"두 번 다 막히면 멈춘다 -- 30바퀴를 안 돈다 (얻은 값 {len(_boom.부름)})")

_once = FakePool(blow=1)
with redirect_stdout(io.StringIO()):
    갈아끼우고(_once, FakeQuota(), lambda: SP.main(
        ["--n", "3", "--batch", "1", "--path", str(원장(TMP))]))
ok(len(_once.부름) == 3,
   f"**한 번 막힌 것으로는 안 멈춘다** -- 다음 후보가 받아 줄 수 있다 (얻은 값 {len(_once.부름)})")

print("\n== 제 반복문을 안 짠다 ==")
_src = (Path(__file__).resolve().parent.parent / "seek" / "spread.py").read_text(encoding="utf-8")
for 금지 in ("import requests", "generativeai", "GEMINI_API_KEY=", "for key in"):
    ok(금지 not in _src, f"{금지!r} 가 없다 -- 키 순회는 llm_pool 것이다")
ok("llm_pool.call(" in _src, "llm_pool.call 을 부른다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("seek 풀: 경유 · verbose · 사전점검 · 연속실패 정지 -- 통과")
