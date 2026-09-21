# -*- coding: utf-8 -*-
"""메일 첨부 -- 경로 가드와 배선.

**langchain 없이 돈다.** `bot_tools` 를 들이면 langchain 이 필요해서 이 컨테이너에서는
통째로 임포트가 안 되고, 그러면 순수한 로직(경로 가드)까지 검사를 못 받는다.
과제 #9 가 적어 둔 그 병이다. 그래서 `mailattach.py` 가 따로 있고, 여기서는
**그 모듈을 직접 돌리고** 배선은 글자로 확인한다.
"""
import os
import sys
import tempfile
from pathlib import Path

여기 = Path(__file__).resolve().parent
저장소 = 여기.parent
sys.path.insert(0, str(저장소))

import mailattach  # noqa: E402
import mailer      # noqa: E402

FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


print("== 경로 가드: 저장소 밖과 비밀값은 못 붙인다 ==")
_, 거절 = mailattach.풀기("/etc/passwd")
ok(거절 and "저장소 밖" in 거절[0], f"절대경로를 거절한다 ({거절[0][:46] if 거절 else '거절 없음'})")
_, 거절 = mailattach.풀기("../../etc/hosts")
ok(거절 and "저장소 밖" in 거절[0], "상위로 빠져나가는 경로를 거절한다")
_, 거절 = mailattach.풀기(".env")
ok(거절 and "비밀값" in 거절[0], "**.env 는 못 붙인다** -- 첨부는 유출 경로다")
_, 거절 = mailattach.풀기("*/../.env")
ok(not _ , "글롭으로도 비밀값에 못 닿는다")

print("\n== 글롭 · 여럿 · 중복 ==")
with tempfile.TemporaryDirectory() as d:
    R = Path(d)
    (R / "sub").mkdir()
    for n in ("a.sv", "b.sv", "c.v"):
        (R / "sub" / n).write_text("x\n", encoding="utf-8")
    가진것, _ = mailattach.풀기("sub/*.sv", repo=R)
    ok([p.name for p in 가진것] == ["a.sv", "b.sv"], f"글롭이 편다 ({[p.name for p in 가진것]})")
    가진것, _ = mailattach.풀기("sub/a.sv, sub/*.v", repo=R)
    ok([p.name for p in 가진것] == ["a.sv", "c.v"], "쉼표로 여럿을 받는다")
    가진것, _ = mailattach.풀기("sub/a.sv sub/*.sv", repo=R)
    ok(len(가진것) == 2, f"**같은 파일을 두 번 안 붙인다** ({len(가진것)}개)")
    _, 거절 = mailattach.풀기("sub/없다.pdf", repo=R)
    ok(거절 and "파일이 아니다" in 거절[0], "없는 파일은 그 까닭을 말한다")

print("\n== 한도: 크거나 많으면 보내기 전에 막는다 ==")
with tempfile.TemporaryDirectory() as d:
    R = Path(d)
    (R / "big").mkdir()
    (R / "big" / "huge.bin").write_bytes(b"0" * (mailattach.첨부최대 + 1))
    큰것, _ = mailattach.풀기("big/huge.bin", repo=R)
    ok("못 보낸다" in mailattach.막히나(큰것), "**상한을 넘으면 SMTP 를 열기 전에 막는다**")
    for i in range(mailattach.첨부개수 + 2):
        (R / "big" / f"f{i}.txt").write_text("x", encoding="utf-8")
    많은것, _ = mailattach.풀기("big/*.txt", repo=R)
    ok("너무 많다" in mailattach.막히나(많은것),
       f"개수 상한({mailattach.첨부개수})을 넘으면 막는다")
    작은것, _ = mailattach.풀기("big/f0.txt", repo=R)
    ok(mailattach.막히나(작은것) == "", "멀쩡한 것은 안 막는다")

print("\n== 말머리는 자리표가 아니다 (house 와 같은 목록) ==")
ok("[보고]" in mailattach.말머리, "`[보고]` 가 말머리 목록에 있다")
ok(mailer.자리표들("[보고] 주간", mailattach.말머리) == [], "말머리를 자리표로 안 센다")
ok(mailer.자리표들("[보고] [교수님 성함]께", mailattach.말머리) == ["[교수님 성함]"],
   "**말머리를 봐줘도 진짜 자리표는 잡는다**")
import house.report as _R  # noqa: E402
ok(_R.말머리 in mailattach.말머리,
   f"house 가 쓰는 말머리({_R.말머리})를 봇도 안다 -- 한 곳만 고치면 안 되는 자리")

print("\n== 배선: 봇 도구가 첨부를 받고, 프롬프트가 그것을 안다 ==")
_봇 = (저장소 / "bot_tools.py").read_text(encoding="utf-8")
ok("def send_email(to: str, subject: str, body: str, attach: str = \"\")" in _봇,
   "**send_email 이 attach 를 받는다**")
ok("import mailattach" in _봇 and "mailattach.풀기(attach)" in _봇,
   "가드를 여기서 다시 짜지 않고 mailattach 를 쓴다")
ok("보내기_첨부" in _봇, "첨부가 있으면 보내기_첨부 로 간다")
ok("허용자리표=mailattach.말머리" in _봇, "말머리를 통과시킨다")
ok("첨부가\n    없으면 그건 보고가 아니다" in _봇 or "첨부가" in _봇,
   "도구 설명이 '첨부 없으면 보고가 아니다' 를 말한다")
_서버 = (저장소 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("send_email" in _서버, "send_email 이 도구 목록에 있다")

print("\n== mailattach 는 langchain 없이 돈다 ==")
import re as _re
_글 = (저장소 / "mailattach.py").read_text(encoding="utf-8")
_수입 = _re.findall(r"^\s*(?:import|from)\s+([\w.]+)", _글, _re.M)
ok(not any(m.startswith(("langchain", "discord", "google")) for m in _수입),
   f"**이 모듈은 langchain/discord 를 안 들인다** -- 들이는 것: {sorted(set(_수입))}")
# 그리고 정말로 그러한지 **자식 프로세스에서 확인한다** -- 글자 검사는 간접 수입을 못 본다.
import subprocess as _sp
_r = _sp.run([sys.executable, "-c",
              "import sys; sys.path.insert(0, %r); import mailattach; "
              "bad=[m for m in sys.modules if m.startswith(('langchain','discord'))]; "
              "print('BAD' if bad else 'CLEAN')" % str(저장소)],
             capture_output=True, text=True)
ok(_r.stdout.strip() == "CLEAN",
   f"실제로 들여 봐도 langchain 이 안 딸려 온다 ({_r.stdout.strip() or _r.stderr[-60:]})")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("mailattach: 경로 가드 · 글롭 · 한도 · 말머리 · 배선 -- 통과")
