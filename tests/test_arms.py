"""팔 -- **한 런에서 수십 개 관측을 얻는다.**

지시문을 한 번 고치고 런을 통째로 다시 돌리면 사이클마다 관측이 하나다. 그건
최적화가 아니라 생성이다. 덩어리마다 다른 설정을 배정하고 결과를 함께 적으면,
같은 호출 수로 관측이 덩어리 수만큼 생긴다.

실행: python3 tests/test_arms.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import arms, dyn, flow                                     # noqa: E402

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


print("[배정] **덩어리마다 다른 설정** -- 재현되게")
_ids = [dyn.arm("씨", i)["id"] for i in range(30)]
ok(len(set(_ids)) >= 4, f"여러 팔이 돌아간다 ({len(set(_ids))}가지)")
ok(dyn.arm("씨", 7) == dyn.arm("씨", 7), "같은 원고·번호면 같다  ← 이어 써도 재현된다")
ok(dyn.arm("씨", 7) != dyn.arm("다른", 7), "원고가 다르면 다르다")
ok(all(set(a) >= {"asks", "slack", "aim"} for a in dyn.ARMS), "흔드는 것이 셋이다")

print()
print("[적기] **배정과 결과를 함께 적는다** -- 따로 적으면 짝을 못 맞춘다")
_bk = flow.blank()
_bk["chunks"] = ["그는 갔다.\n" * 300]
flow.write_prompt(_bk)
ok(_bk.get("_arm"), f"프롬프트를 만들 때 팔이 정해진다 ({_bk.get('_arm')})")
ok(_bk["_arm"]["asks"] <= 6, "싣는 수가 팔에서 온다")

print()
print("[세기] **몇 번 안 보고 이겼다고 하지 않는다**")
_rows = []
for i in range(40):
    a = dict(dyn.ARMS[i % 6], id=i % 6)
    _rows.append({"n": i, "arm": a, "gap": 0.30 + 0.05 * (i % 6)})
_t = arms.tally(_rows)
ok(len(_t) == 6, f"팔마다 모은다 ({len(_t)}개)")
ok(arms.best(_t)["arm"]["id"] == 0, "제일 가까운 팔을 고른다")
_few = arms.tally(_rows[:3])
ok(arms.best(_few) is None, f"{arms.MIN_SEEN}번은 봐야 한다  ← 서너 번은 우연이다")

print()
print("[굳히기] **이긴 설정을 파일로 남긴다**")
_p = Path(tempfile.mkdtemp()) / "arm.json"
_was = arms.PICKED
try:
    arms.PICKED = _p
    ok(arms.apply(_t) == 0, "굳힌다")
    _got = json.loads(_p.read_text(encoding="utf-8"))
    ok(_got["arm"]["id"] == 0 and _got["본 횟수"] >= arms.MIN_SEEN,
       "무엇을 몇 번 보고 골랐는지 함께 적는다")
    ok(arms.apply(_few) == 1, "모자라면 안 굳힌다")
finally:
    arms.PICKED = _was

print()
print("[표] **어느 설정이 이기는지 한눈에**")
_tb = arms.table(_t)
ok("이긴 팔" in _tb and "평균 거리" in _tb, "표로 찍는다")
ok(arms.table({}).startswith("적힌 것이 없다"), "빈 것도 말이 되게 찍는다")

print()
print("[루프] **끊기지 않게 띄운다**")
_sh = (Path(__file__).resolve().parent.parent / "scripts" / "tune_loop.sh").read_text(
    encoding="utf-8")
for _k in ("setsid", "nohup", "disown", "pgrep -af"):
    ok(_k in _sh, f"백그라운드 규칙을 지킨다: {_k}")
ok("ps -p $!" not in _sh, "ps -p $! 로 확인하지 않는다  ← 거짓 음성을 낸다")
ok("pkill" not in _sh, "pkill 을 안 쓴다  ← 제 셸까지 죽인다")
ok("--stop" in _sh and "STOP" in _sh, "멈추는 길이 있다")
ok("|| true" in _sh or "continue" in _sh, "한 단계가 실패해도 루프는 안 선다")
ok("quota_show.py --brief" in _sh,
   "한도를 먼저 묻는다  ← 다 소진된 채로 두드리면 429 만 쌓인다")
ok("sleep 300" in _sh, "쓸 후보가 없으면 기다린다  ← 자정에 하루치가 풀린다")
_q = (Path(__file__).resolve().parent.parent / "scripts" / "quota_show.py").read_text(
    encoding="utf-8")
ok("--brief" in _q and "return 0 if (alive or unseen) else 3" in _q,
   "한도가 한 줄과 종료 코드로도 나온다  ← 밤새 도는 쪽은 표를 못 읽는다")

print()
if fails:
    print(f"팔: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("팔: 배정 · 적기 · 세기 · 굳히기 · 표 · 루프 -- 통과")

print()
print("[검증에서 나온 것] **밤을 날리던 자리들**")
print("      ← 워크플로가 14개를 확인해 줬다. 그중 루프를 세우거나 데이터를 망치는 것.")
ok("now + CHARS" in _sh,
   "이어 쓸 때 목표를 증분으로 넘긴다  ← --chars 는 누적 목표라 2바퀴부터 0자였다")
ok("$qcode" in _sh and "-ne 3" in _sh,
   "한도 코드 3(소진)과 고장을 가른다  ← 고장을 소진으로 읽으면 밤새 쉬기만 한다")
ok('-eq 4' in _sh, "부를 후보가 아예 없으면 기다리지 않고 선다")
ok('>> "$LOG" 2>&1 < /dev/null' in _sh,
   "로그를 덮어쓰지 않는다  ← 밤새 무슨 일이 있었는지 남아야 한다")
_ra = (Path(__file__).resolve().parent.parent / "scripts" / "run_all.sh").read_text(
    encoding="utf-8")
ok("novel/final.json" in _ra and "pgrep -f \"novel/final.json\"" in _ra,
   "최종 집필은 **우리가 띄운 것만** 기다린다  ← 남의 flow.py 를 열두 시간 붙잡았다")
ok("waited" in _ra and "43200" in _ra, "기다리기에 상한이 있다")
ok('if ! BOOK=' in _ra, "집필을 못 띄우면 거기서 선다  ← 0자짜리를 성공처럼 찍었다")
ok("0자를 성공처럼 찍지 않는다" in _ra, "빈 결과를 성공으로 안 찍는다")
# **좁힌 목표를 조용히 덮지 않는다.** 루프를 띄울 때마다 표본 전체를 다시 재서,
# 사람이 --only A --tight 로 한 작품에 맞춰 둔 목표(67토막·1편)가 네 작품
# 평균(461토막·4편)으로 갈아엎혔다. 여섯 시간을 그 자로 배웠다.
ok("1편" in _ra and "덮지 않는다" in _ra,
   "이미 한 작품에 맞춘 목표가 있으면 안 덮는다")
ok("ONLY" in _ra and "--only" in _ra, "겨눌 작품을 ONLY 로 준다")

from novel import tuner as _T                                         # noqa: E402
ok("대상" in Path(_T.__file__).read_text(encoding="utf-8"),
   "튜너가 이미 결론 난 시도를 다시 심판하지 않는다  ← 채택한 것을 되돌렸다")
ok(_T._clean("고친 지시문:\n```\n끊어라.\n```") == "끊어라.",
   "되받은 것에서 머리말과 코드펜스를 걷어낸다")
ok(_T._clean('"따옴표"') == "따옴표", "따옴표도 걷어낸다")
_src2 = Path(_T.__file__).read_text(encoding="utf-8")
ok("총점은 **지킴목**" in _src2 or "지킴목" in _src2,
   "총점은 지킴목으로만 쓴다  ← 축 하나의 개선이 예순아홉 축의 흔들림에 묻힌다")

# **여섯 시간에 한 축만 두드렸다.** nosubj 를 다섯 바퀴 연속으로 고쳐 보고 다섯 번
# 다 되돌렸다. 제일 먼 축은 그동안 그대로였으니 다음 바퀴도 같은 축이 뽑혔다.
print("\n[한 축에 갇히지 않는다]")
import json as _json, tempfile as _tf                                # noqa: E402
with _tf.TemporaryDirectory() as _t:
    _log = Path(_t) / "tune.jsonl"
    _was = _T.LOG
    try:
        _T.LOG = _log
        ok(_T.cooling() == set(), "장부가 비면 쉬는 축이 없다")
        _log.write_text("\n".join(_json.dumps(r, ensure_ascii=False) for r in [
            {"무엇": "되돌림", "축": "nosubj"},
            {"무엇": "되돌림", "축": "nosubj"}]), encoding="utf-8")
        ok(_T.cooling() == {"nosubj"},
           f"내리 두 번 되돌린 축은 쉰다 ({_T.cooling()})")
        _log.write_text(_log.read_text(encoding="utf-8") + "\n"
                        + _json.dumps({"무엇": "채택", "축": "nosubj"}, ensure_ascii=False),
                        encoding="utf-8")
        ok(_T.cooling() == set(), "한 번이라도 먹히면 다시 본다")
        # 쉬는 축을 빼면 다음으로 먼 축이 뽑힌다
        _s = {"total": 0.5, "axes": {"a": {"gap": 0.9, "got": 0, "lo": 1, "hi": 2},
                                     "b": {"gap": 0.4, "got": 0, "lo": 1, "hi": 2}}}
        _sc = _T.SC.score
        try:
            _T.SC.score = lambda _p: _s
            ok(_T.worst("x", skip=set())[0] == "a", "안 쉬면 제일 먼 축")
            ok(_T.worst("x", skip={"a"})[0] == "b", "쉬는 축은 건너뛴다")
            ok(_T.worst("x", skip={"a", "b"})[0] == "a",
               "전부 쉬면 그냥 제일 먼 것을 쓴다  ← 아무것도 안 하는 것보다 낫다")
        finally:
            _T.SC.score = _sc
    finally:
        _T.LOG = _was
