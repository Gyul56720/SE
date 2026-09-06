"""**말하기의 갈래로 프롬프트를 가른다** -- 한 덩어리 안에서도 요구가 달라진다.

프롬프트가 하나면 묘사도 대사도 같은 요구를 받는다. 그런데 작품을 가르는 것은
"묘사 몇 줄 하다가 대사로 넘어가 몇 턴 주고받는가" 이고 그것은 덩어리 단위로는 안
잡힌다. 그래서 줄을 다섯 갈래로 보고 표본에서 그 이음을 배운다(LLM 0회).

여기서 고정하는 계약:

  · **맺음은 대목 한가운데에 안 나온다** -- 표본에서 맺음은 늘 마지막 줄이라 나가는
    전이가 없다. 중간에 뽑히면 다음 분포가 비어 묘사로 떨어지고, 대목 한가운데에
    "닫아라" 가 실린다(실제로 그랬다)
  · **배운 적 없으면 아무 말도 안 한다** -- modes.json 이 없으면 흐름 줄이 통째로
    빠지고 프롬프트는 예전 그대로다. 없는 흐름을 지어내서 시키지 않는다
  · **갈래가 바뀌면 실리는 축이 바뀐다** -- 대사를 쓰는 자리에 문단 길이를 설명해
    봐야 지켜지지 않는다. 여덟 줄뿐인 설명 자리를 지금 쓰는 것에 준다
  · **mode 는 state 가 아니다** -- novel/state.py 는 오케스트레이션의 세계 상태다.
    같은 이름으로 덮으면 drive · gate · overnight 이 통째로 죽는다(한 번 그랬다)

실행: python3 tests/test_mode.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import mode as MD, profile as PF                          # noqa: E402

fails = []


def ok(cond, label):
    print(("  OK  " if cond else "  실패 ") + label)
    if not cond:
        fails.append(label)


SAMPLE = Path(__file__).resolve().parent / "sample_job.txt"
TEXT = SAMPLE.read_text(encoding="utf-8")

print("[배운다 -- 호출 0회]")
m = MD.learn([TEXT])
ok(bool(m.get("trans")), "표본에서 전이를 배운다")
ok(all(abs(sum(m["trans"][a].values()) - 1.0) < 1e-6 or
       sum(m["trans"][a].values()) == 0 for a in MD.STATES),
   "전이는 갈래마다 합이 1이거나 비어 있다")
ok(all(m["run"][a] >= 1.0 for a in MD.STATES), "머무름은 한 줄 이상이다")

print("\n[맺음은 마지막에만]")
bad = 0
for n in range(40):
    st = MD.plan(m, "seed", n, 24)
    if not st:
        continue
    if "맺음" in st[:-1]:
        bad += 1
    if st[-1] != "맺음":
        bad += 1
ok(bad == 0, f"마흔 덩어리에서 맺음이 한가운데 안 나온다 (어긋남 {bad})")

print("\n[덩어리마다 다르다 · 같은 덩어리는 같다]")
a0 = MD.plan(m, "seed", 0, 24)
a0b = MD.plan(m, "seed", 0, 24)
a3 = MD.plan(m, "seed", 3, 24)
ok(a0 == a0b, "같은 씨앗·같은 덩어리는 같은 열이다(해시로 굴린다)")
ok(a0 != a3, "덩어리가 바뀌면 열도 바뀐다")

print("\n[갈래가 바뀌면 볼 축이 바뀐다]")
w_talk = MD.watched(["대사"])
w_desc = MD.watched(["묘사"])
ok("dialog" in w_talk and "dialog" not in w_desc, "대사 자리에서만 대사 몫을 본다")
ok("para_len" in w_desc and "para_len" not in w_talk,
   "문단 길이는 묘사 자리에서만 본다")
ok(set(MD.watched(["묘사", "대사"])) == set(w_desc) | set(w_talk),
   "여러 갈래가 나오면 축이 합쳐진다")

print("\n[프롬프트]")
txt = MD.render(a0)
ok("→" in txt and "줄" in txt, "밟을 순서를 한 줄로 준다")
ok(all(MD.SAY[s] in txt for s in set(a0)), "나오는 갈래마다 무엇을 하라고 말한다")
ok(all(MD.SAY[s] not in txt for s in MD.STATES if s not in set(a0)),
   "안 나오는 갈래는 한 글자도 안 싣는다")
ok(MD.render([]) == "", "배운 적 없으면 아무 말도 안 한다")

print("\n[compose 와의 배선]")
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "modes.json"
    MD.save(m, str(p))
    _was = MD.PATH
    try:
        MD.PATH = str(p)
        loaded = MD.load()
        ok(loaded.get("trans") == m["trans"], "쓴 것을 그대로 읽는다")
        from novel import compose
        book = {"seed_id": "s1", "first": "첫 문장이다.", "chunks": []}
        on = compose.build(book)
        MD.PATH = str(Path(d) / "없다.json")
        off = compose.build(book)
    finally:
        MD.PATH = _was
ok("[이 대목의 흐름]" in on, "배웠으면 흐름이 프롬프트에 실린다")
ok("[이 대목의 흐름]" not in off, "안 배웠으면 흐름 줄이 통째로 빠진다")
ok("[이번 대목의 수]" in off, "그래도 수는 그대로 실린다 -- 예전과 같아진다")

print("\n[갈래마다 다른 수]")
ok(all(k not in MD.BLIND for k in ("sent_len", "para_len", "glue")),
   "문장 축은 갈래별로 잰다")
ok(all(k in MD.BLIND for k in ("n2t", "t2t", "dialog", "scene")),
   "이음 축은 갈래별로 안 잰다 -- 대사 줄만 모으면 n2t 가 언제나 0이다")
parts = MD.split(TEXT)
ok(set(parts) <= set(MD.STATES) and sum(len(v) for v in parts.values()) > 0,
   f"글을 갈래별 글로 가른다 ({' · '.join(f'{k} {len(v)}자' for k, v in parts.items())})")

with tempfile.TemporaryDirectory() as d:
    tm = Path(d) / "targets.modes.json"
    tm.write_text(json.dumps({"modes": {
        "묘사": {"sent_len": {"lo": 40.0, "mid": 42.0, "hi": 44.0}},
        "대사": {"talk_len2": {"lo": 15.0, "mid": 16.0, "hi": 17.0}}}},
        ensure_ascii=False), encoding="utf-8")
    _was = MD.NUMS
    try:
        MD.NUMS = str(tm)
        from novel import compose as CP
        st = ["묘사", "묘사", "대사", "맺음"]
        ex = CP.mode_nums("s1", 0, st)
        txt = MD.render(st, ex)
    finally:
        MD.NUMS = _was
lines = {l.strip(): l for l in txt.splitlines()}
ok("묘사" in ex and "40" <= ex["묘사"].split()[-1][:2] <= "44",
   f"묘사 자리에는 묘사에서 잰 문장 길이가 붙는다 -- {ex.get('묘사','')}")
ok("talk_len2" not in str(ex.get("묘사", "")) and "대사" in ex,
   "대사 자리 수가 묘사 자리에 안 붙는다")
ok("맺음" not in ex, "잰 적 없는 갈래에는 수가 안 붙는다(빈 줄을 지어내지 않는다)")
ok(ex["묘사"] in txt and ex["대사"] in txt, "그 수가 프롬프트에 실린다")

print("\n[대사에는 따옴표를 벗기고 잰다]")
# rhythm 은 따옴표로 시작하는 줄을 문장에서 뺀다. 대사 줄만 모아 놓으면 잴 문장이
# 거의 안 남아서, A 의 대사 갈래 sent_len 이 4~21자로 나왔다 -- 대사 길이가 아니라
# 대사 사이에 낀 몇 줄의 길이였다.
_talk = '"가자. 지금 당장 가야 한다."\n"왜?"\n"늦었으니까."\n' * 30
_raw = PF.measure(_talk)
_bare = PF.measure(MD.unquote(_talk))
ok("sent_len" not in _raw, "따옴표를 안 벗기면 잴 문장이 없다  ← 여기가 그 잘못이었다")
ok(_bare.get("sent_len", 0) > 0, f"벗기면 대사 문장이 잰다 ({_bare.get('sent_len', 0):.1f}자)")
ok(MD.unquote('"가자."') == "가자.", "따옴표만 벗기고 글자는 안 건드린다")
ok("talk_len2" in MD.QUOTED and "sent_len" not in MD.QUOTED,
   "따옴표가 있어야 나오는 축은 벗기지 않은 것에서 가져온다")

print("\n[이름이 겹치지 않는다]")
from novel import state as WORLD                                      # noqa: E402
ok(hasattr(WORLD, "AXES") and hasattr(WORLD, "Novel"),
   "novel/state.py 는 여전히 세계 상태다(drive · gate 가 여기서 읽는다)")
ok(WORLD.__file__ != MD.__file__, "mode 와 state 는 다른 파일이다")

print()
if fails:
    print(f"말하기 갈래: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("말하기 갈래: 배움 · 맺음 · 갈래별 축 · 배선 · 이름 -- 통과")
