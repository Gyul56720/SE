"""**스킬이 부르는 명령이 실제로 도는가.** 그리고 포트폴리오.

    python3 tests/test_jaso_skill.py

## 왜 이 검사가 있나

이 저장소가 다섯 번 앓은 병이 **"그런 옵션이 없다"** 였다(`CLAUDE.md`: #64 `--판례`
없음 · #67 `--이력` 없음). 스킬 파일은 그 병이 제일 잘 나는 자리다 -- 에이전트가 거기
적힌 대로 치고, 틀린 옵션이면 사용자는 그 자리에서 막힌다. **그리고 스킬 파일은
아무도 안 돌려 본다.**

그래서 여기서 돌려 본다. `SKILL.md` 에 적힌 `python3 …/jaso/X.py --옵션` 을 전부
캐서, 그 파일이 있는지와 그 옵션을 argparse 가 아는지 `--help` 로 확인한다.

## 그리고 트리거

`description` 이 트리거다. 사용자가 실제로 쓸 말("자소서 만들어줘" · "포트폴리오
적어줘")이 거기 들어 있어야 스킬이 뜬다. 안 뜨면 Claude 는 이 파이프라인이 있는 줄
모르고 **자소서를 직접 지어낸다** -- 정확히 막으려던 그 결과다.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import folio as FO                                      # noqa: E402
from jaso import ledger as LG                                     # noqa: E402

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


스킬 = ROOT / ".claude" / "skills" / "jaso" / "SKILL.md"
글 = 스킬.read_text(encoding="utf-8") if 스킬.is_file() else ""


print("── 트리거 -- 사용자가 실제로 쓸 말이 들어 있는가 ────────")
ok(스킬.is_file(), f"스킬 파일이 있다 ({스킬.relative_to(ROOT)})")
머리 = 글.split("---")[1] if 글.startswith("---") else ""
설명 = next((l.split(":", 1)[1] for l in 머리.splitlines()
            if l.startswith("description:")), "")
ok(설명.strip(), "description 이 있다 -- **이것이 트리거다**")
for 말 in ("자소서", "자기소개서", "포트폴리오", "문항", "AI 판별"):
    ok(말 in 설명, f"{말!r} 로 뜬다")
ok("name: jaso" in 머리, "이름이 jaso")


print("\n── **적힌 명령이 실제로 도는가** (다섯 번 앓은 병) ───────")
본것 = set()
for m in re.finditer(r"python3 [^\n]*?/(jaso/\w+\.py)((?:\s+--?[^\s\\]+)*)", 글):
    파일, 옵션들 = m.group(1), m.group(2)
    깃발 = [x for x in re.findall(r"--[^\s\\=]+", 옵션들)]
    키 = (파일, tuple(깃발))
    if 키 in 본것:
        continue
    본것.add(키)
    p = ROOT / 파일
    if not p.is_file():
        ok(False, f"{파일} 이 없다 -- 스킬이 없는 파일을 부른다")
        continue
    도움 = subprocess.run([sys.executable, str(p), "--help"],
                         capture_output=True, text=True, cwd=str(ROOT))
    ok(도움.returncode == 0, f"{파일} --help 가 돈다")
    없는것 = [f for f in 깃발 if f not in 도움.stdout]
    ok(not 없는것, f"{파일} {' '.join(깃발) or '(옵션 없음)'}"
                  + (f"  <- **없는 옵션: {없는것}**" if 없는것 else ""))
ok(len(본것) >= 8, f"스킬이 명령 {len(본것)}줄을 부른다 (다 검사했다)")


print("\n── 스킬이 어기면 안 되는 것을 적어 두었는가 ─────────────")
for 말, 왜 in (("직접 지어내지 마라", "이 세션에서 자소서를 쓰면 대조를 안 받는다"),
              ("원장을 지어내지 마라", "공고문으로 이력을 만들면 전부 미검증이다"),
              ("남의 합격 자소서", "표절 검사 DB 가 정확히 그것이다"),
              ("탐지 회피", "사실은 안 바꾸면서 저작자만 속인다")):
    ok(말 in 글, f"{말!r} -- {왜}")
ok("끝값" in 글 and "사람 차례" in 글,
   "**끝값 2 가 사람 차례라는 것**이 적혀 있다 -- 대신 답하면 원장이 오염된다")
ok("학교·회사·문항을 네가 정하지 마라" in 글,
   "**배포판에서 지원처를 세션이 정하지 않는다** -- 그것을 아는 사람은 사용자뿐이다")

print("\n── 스킬이 적은 끝값이 **실제 끝값과 같은가** ──────────")
표 = "\n".join(l for l in 글.splitlines() if l.lstrip().startswith(("0  ", "1  ", "3  ")))
ok("문항이 없다" not in 표,
   "**끝값 3 자리에 '문항이 없다' 가 없다** -- 이제 그것은 2(사람 차례)다. "
   "실측 교훈: 낡은 메모가 오래 남아 잘못된 데를 가리킨다")
with tempfile.TemporaryDirectory() as d:
    난것 = subprocess.run(
        [sys.executable, str(ROOT / "jaso" / "run.py"), "--터", str(Path(d) / "빈손")],
        capture_output=True, text=True, cwd=str(ROOT))
    ok(난것.returncode == 2,
       f"아무것도 안 주고 부르면 끝값 {난것.returncode} == 2 -- 스킬이 적은 대로다")
    ok("어디에 내는 것입니까" in 난것.stdout,
       "**되묻는 말이 화면에 나온다** -- 스킬은 이것을 그대로 전하라고 적고 있다")


print("\n── 포트폴리오 -- 문항이 다른 자소서다 ───────────────────")
L = LG.읽기(str(ROOT / "jaso" / "보기.json"))
qs = FO.문항만들기(L)
ok(len(qs) == len(L), f"항목마다 문항 하나 ({len(qs)}개)")
종류 = {r.종류 for q in qs for r in q.요구}
ok({"행동", "결과", "경험"} <= 종류,
   f"**`item.py` 가 쪼갤 수 있는 말로 적는다** ({sorted(종류)}) -- 안 그러면 J006 이 "
   "빈 자리를 못 잡고 `ask.py` 가 그 자리를 못 묻는다")
ok("행동" in 종류,
   "(회귀 못) '어떻게 **풀었는지**' 가 행동으로 잡힌다 -- 실측: 활용형이 사전에 "
   "없어 그 요구가 통째로 사라졌었다")
ok(all(q.상한 for q in qs), "글자 수가 붙는다 -- J005 가 잰다")

글2 = FO.사실로(L, "홍길동")
ok("2.1%" in 글2 and "2.6%" in 글2, "잰 값이 그대로")
ok("2주간 A/B" in 글2, "**재는 법이 같이 나온다** -- 수만 보이면 되물을 수 없다")
ok("커밋 로그" in 글2, "증빙이 나온다")
ok("참여" in 글2, "역할이 원장 그대로 -- 승격할 자리가 없다")
안잰것 = LG.읽기([{"id": "P9", "이름": "무엇", "곳": "어디", "역할": "참여",
                "언제": ["2025-01", "2025-06"], "증빙": "",
                "잰것": [{"무엇": "매출", "전": "100", "후": "130", "단위": "%",
                        "어떻게": ""}]}])
글3 = FO.사실로(안잰것)
ok("130" not in 글3 and "재지 않은 것" in 글3,
   "**잰 방법이 없는 수는 아예 안 내놓는다** -- 내놓으면 그대로 옮겨 적힌다")
ok("증빙이 안 적힌 항목" in 글3, "증빙 없는 것을 화면에 적는다")
ok("LLM" not in 글2 and FO.사실로(LG.원장()) is not None,
   "`--사실만` 은 키가 없어도 돈다 (빈 원장에도 안 죽는다)")

print()
print(f"실패 {len(fails)}건" if fails else "전부 통과")
raise SystemExit(1 if fails else 0)
