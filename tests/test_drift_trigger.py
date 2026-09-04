"""DRIFT 트리거 -- **다른 세션이 바로 붙일 수 있어야 한다.**

스크립트와 문서와 스킬이 따로 놀면 트리거가 아니다. 사용자는 문서에 적힌 명령을 치는데
스크립트에 그 명령이 없으면, 그 사람은 무엇이 틀렸는지도 모른 채 막힌다. 그래서 셋이
같은 것을 말하는지 여기서 본다.

실행: python3 tests/test_drift_trigger.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

fails = []


def ok(cond, label):
    print(f"    {'OK  ' if cond else '실패'} {label}")
    if not cond:
        fails.append(label)


SH = ROOT / "scripts" / "drift.sh"
DOC = ROOT / "novel" / "DRIFT.md"
SKILL = ROOT / ".claude" / "skills" / "drift" / "SKILL.md"

print("[있는가] 트리거 · 사용법 · 스킬")
ok(SH.exists(), "scripts/drift.sh")
ok(SH.stat().st_mode & 0o111, "실행 권한이 있다  ← 없으면 사용자가 bash 를 앞에 붙여야 한다")
ok(DOC.exists(), "novel/DRIFT.md")
ok(SKILL.exists(), ".claude/skills/drift/SKILL.md  ← 다른 세션이 /drift 로 부른다")

sh, doc, skill = SH.read_text(), DOC.read_text(), SKILL.read_text()

print()
print("[일치] **문서에 적힌 명령이 스크립트에 실제로 있는가**")
COMMANDS = ("start", "go", "status", "read", "save", "send", "watch", "stop", "world")
for c in COMMANDS:
    ok(re.search(rf"^\s+{c}[\)|]", sh, re.M) is not None, f"drift.sh {c}")
    ok(f"drift.sh {c}" in doc or f"$D {c}" in doc, f"문서가 {c} 를 설명한다")

print()
print("[스킬] 프런트매터가 온전한가  ← 깨지면 스킬 목록에 안 뜬다")
m = re.match(r"---\n(.*?)\n---\n", skill, re.S)
ok(m is not None, "프런트매터가 있다")
if m:
    ok(re.search(r"^name: drift$", m.group(1), re.M) is not None, "name: drift")
    desc = re.search(r"^description: (.+)$", m.group(1), re.M)
    ok(desc is not None and len(desc.group(1)) > 60,
       "description 이 언제 쓰는지까지 말한다  ← 짧으면 다른 세션이 못 찾는다")

print()
print("[규칙] **산문은 Claude 가 쓰지 않는다** -- 스킬이 이걸 다시 못박는가")
ok("산문을 직접 지어내지 마라" in skill, "이 세션에서 소설 문장을 짓지 않는다")
ok("Claude 로 대신하지 않는다" in skill, "키가 없으면 사실대로 실패한다")
ok("pkill" in skill and "쓰지 마라" in skill, "pkill -f 를 금지한다  ← 자기 셸까지 죽는다")

print()
print("[안전] 스크립트가 스스로를 프로세스로 세지 않는가")
print("      ← pgrep -af 'novel/flow.py' 는 이 스크립트를 쓰는 셸까지 잡는다(실측).")
out = subprocess.run(["bash", str(SH), "status"],
                     env={"PATH": "/usr/bin:/bin", "SE_DIR": str(ROOT),
                          "BOOK": "/nonexistent/none.json", "HOME": "/tmp"},
                     capture_output=True, text=True, timeout=60)
ok("돌고 있지 않다" in out.stdout,
   f"돌지 않을 때 돌지 않는다고 말한다  ← 자기 자신을 잡으면 start 가 거부된다")
ok("원고가 아직 없다" in out.stdout, "원고가 없으면 없다고 말한다")

print()
print("[내보내기] **원고는 VM 안 JSON 에만 있다** -- 손에 들어오는 길이 있어야 한다")
from novel import deliver                                             # noqa: E402
ok(hasattr(deliver, "send_file"), "novel/deliver.py 가 파일로 올린다")
okd, why = deliver.send_file("본문", "a.txt")
ok(not okd and "자격증명" in why,
   "자격증명이 없으면 사실대로 말한다  ← 조용히 성공한 척하면 사용자는 기다리기만 한다")
body, ctype = deliver._multipart({"payload_json": "{}"}, "1화.txt", "본문".encode())
ok(ctype.startswith("multipart/form-data") and "1화.txt".encode() in body,
   "multipart 를 손으로 짠다  ← 이것 하나로 의존성을 늘리지 않는다")
ok("토큰은 절대 찍지 않는다" in Path(deliver.__file__).read_text(encoding="utf-8"),
   "실패해도 자격증명을 로그에 흘리지 않는다")
ok("send" in sh and "deliver.py" in sh, "drift.sh send 가 그것을 부른다")

print()
print("[연결] 저장소 README 에서 찾아갈 수 있는가")
root = (ROOT / "README.md").read_text()
ok("DRIFT" in root and "novel/DRIFT.md" in root, "루트 README 가 DRIFT 를 가리킨다")
ok("DRIFT.md" in (ROOT / "novel" / "README.md").read_text(),
   "novel/README 가 두 갈래를 갈라 준다  ← 조립과 흐름은 다른 물건이다")

print()
if fails:
    print(f"트리거: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("트리거: 존재 · 명령 일치 · 스킬 · 규칙 · 자기검출 · 연결 -- 통과")
