# -*- coding: utf-8 -*-
"""**디스코드 2000자 벽을 양쪽에서 넘는가.**

사용자(2026-09-22): "2000자 제한 때문에 스펙이 전부 안들어가 이건 어떻게 해결해야할까?"

벽은 양쪽에 있다.

    들어오는 쪽   한 메시지 2000자. 진짜 IP 요구사항서는 그보다 길다
                  (2026-09-21 MERA HAS 편지가 4천 자 넘었다)
                  -> **첨부 파일**에는 그 벽이 없다. `inbox.붙이기()`
    나가는 쪽     전에는 `reply[:2000]` -- **말없이 잘랐다**
                  -> `쪼개기()` 가 줄 경계에서 나눠 보낸다

**둘 다 '잘렸다' 를 적는다.** 말없이 자르는 것이 이 벽의 병이다 -- 사람이 보는 것과
실제가 다른데 다르다는 표시가 없다.

모델도 망도 없이 돈다. 실행: python3 tests/test_inbox.py
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import inbox  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


# ---------------------------------------------------------------- 들어오는 쪽
print("[들어오는 쪽] 첨부가 2000자 벽을 넘는가")
_d = Path(tempfile.mkdtemp(prefix="test-inbox-"))
_긴스펙 = "# MERA-1 요구사항\n" + "\n".join(
    f"{i}. AXI4-Stream 256-bit, PRE 4K / POST 16K, junction 0~100C" for i in range(200))
(_d / "spec.md").write_text(_긴스펙, encoding="utf-8")
ok(len(_긴스펙) > 2000, f"**표본이 벽보다 길다** ({len(_긴스펙):,}자) -- 안 그러면 아무것도 안 잰다")

_글, _말 = inbox.붙이기("이 스펙으로 설계해줘", [str(_d / "spec.md")])
ok(len(_글) > 2000, f"**붙인 뒤에는 2000자를 넘는다** ({len(_글):,}자)")
ok("이 스펙으로 설계해줘" in _글, "사람이 친 말이 앞에 남는다")
ok("PRE 4K / POST 16K" in _글, "**첨부 속의 수가 요청 글에 실제로 들어온다**")
ok(_말 and "spec.md" in _말[0] and "자 읽음" in _말[0],
   f"**몇 자 읽었는지 적는다** ({_말})")

_없, _말2 = inbox.붙이기("그냥 물음", [])
ok(_없 == "그냥 물음" and _말2 == [], "첨부가 없으면 본문 그대로, 할 말도 없다")

print()
print("[못 읽는 것] 말없이 넘기지 않는다")
(_d / "그림.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)
_g, _m = inbox.붙이기("이거 봐", [str(_d / "그림.png")])
ok(_g == "이거 봐", "**바이너리는 안 붙인다** -- 깨진 바이트를 스펙으로 읽게 된다")
ok(_m and "못 읽음" in _m[0], f"그런데 **못 읽었다고 적는다** ({_m})")
_n, _m2 = inbox.붙이기("x", [str(_d / "없는파일.md")])
ok(_m2 and "없다" in _m2[0], f"없는 파일도 그렇게 적는다 ({_m2})")
(_d / "빈.md").write_text("   \n", encoding="utf-8")
ok("비어" in (inbox.붙이기("x", [str(_d / "빈.md")])[1] or [""])[0], "빈 파일도 적는다")

print()
print("[상한] 잘랐으면 잘랐다고 적는다")
(_d / "아주긴.md").write_text("나" * (inbox.파일당최대 + 5000), encoding="utf-8")
_글3, _말3 = inbox.붙이기("설계", [str(_d / "아주긴.md")])
ok(len(_글3) < inbox.파일당최대 + 3000, f"파일당 상한을 지킨다 ({len(_글3):,}자)")
ok("여기서 잘랐다" in _글3, "**글 안에 잘랐다고 적는다** -- 모델도 그것을 본다")

_여럿 = []
for i in range(5):
    (_d / f"큰{i}.md").write_text("다" * 30_000, encoding="utf-8")
    _여럿.append(str(_d / f"큰{i}.md"))
_글4, _말4 = inbox.붙이기("설계", _여럿, 상한=50_000)
ok(len(_글4) <= 50_000 + 2000, f"총 상한도 지킨다 ({len(_글4):,}자)")
ok(any("상한에 닿아" in x for x in _말4), f"**남은 첨부를 안 읽었다고 적는다** ({_말4[-1][:40]})")

ok(inbox.읽을수있나("a/b/spec.md") and inbox.읽을수있나("x.pdf")
   and inbox.읽을수있나("t.sv") and not inbox.읽을수있나("x.png"),
   "어느 꼴을 글로 읽는지 물을 수 있다")

# ---------------------------------------------------------------- 나가는 쪽
print()
print("[나가는 쪽] 긴 답을 말없이 자르지 않는가")
_src = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
_m = re.search(r"답한도 = .*?\ndef 쪼개기.*?\n    return 쪽들\n", _src, re.S)
ok(_m is not None, "`쪼개기` 를 봇에서 꺼내 온다 -- 닮은꼴을 새로 짓지 않는다")
_ns: dict = {}
exec(_m.group(0), _ns)                                        # noqa: S102
쪼 = _ns["쪼개기"]
한도 = _ns["답한도"]

ok(쪼("") == [], "빈 답은 아무것도 안 보낸다")
ok(쪼("안녕") == ["안녕"], "짧으면 한 통, 쪽 표시도 안 붙인다")

_긴답 = "\n".join(f"{i}번 줄 " + "가" * 60 for i in range(200))
_쪽 = 쪼(_긴답)
ok(len(_쪽) > 1, f"긴 답은 여러 통으로 나뉜다 ({len(_긴답):,}자 -> {len(_쪽)}통)")
ok(max(len(x) for x in _쪽) <= 2000,
   f"**어느 통도 디스코드 한도를 안 넘는다** (가장 긴 통 {max(len(x) for x in _쪽)}자)")
ok(all(f"({i+1}/{len(_쪽)})" in t for i, t in enumerate(_쪽)),
   "몇 쪽 중 몇 쪽인지 적는다 -- 받는 사람이 빠진 것을 알 수 있다")

_한줄 = "x" * 9000
ok(max(len(x) for x in 쪼(_한줄)) <= 2000,
   "**줄바꿈이 하나도 없어도 쪼갠다** -- 줄 경계만 믿으면 한 줄짜리 답에서 터진다")

_아주긴 = "\n".join("줄 " + "나" * 80 for i in range(1000))
_많 = 쪼(_아주긴)
ok(len(_많) <= _ns["최대쪽"], f"채널을 도배하지 않는다 ({len(_많)}통)")
ok("여기서 잘랐다" in _많[-1], "**그때는 잘랐다고 적는다** -- 말없이 자르지 않는다")

print()
print("[배선] 봇이 실제로 그 길을 쓰는가")
# **주석이 아니라 부르는 자리를 본다.** 첫 판이 `"reply[:2000]" not in _src` 였는데
# 그 말을 적은 **내 주석**에 걸렸다 -- 글자를 세는 검사의 그 병이다.
ok("message.reply(reply[:2000])" not in _src,
   "**`await message.reply(reply[:2000])` 가 사라졌다** -- 그 한 줄이 벽이었다")
ok("_길게답하기(message, reply)" in _src, "쪼개 보내는 길로 바뀌었다")
ok("import inbox" in _src, "봇이 inbox 를 들인다")
ok("inbox.붙이기" in _src, "**고정 명령 길에서 첨부를 붙인다** -- 전에는 content 만 봤다")
_앞 = _src[_src.index("reply = await asyncio.to_thread(dispatch.run, 본문"):]
ok("dispatch.앞세울것, 본문" in _앞,
   "**자연어 앞세우기도 붙인 본문을 본다** -- 한쪽만 고치면 첨부가 반만 닿는다")
_dep = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok("inbox.py" in _dep, "**배포가 inbox.py 를 싣는다** -- 안 실으면 VM 에서 임포트가 죽는다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("inbox: 첨부로 벽 넘기 · 못 읽는 것 · 상한 · 답 쪼개기 · 배선 -- 통과")
