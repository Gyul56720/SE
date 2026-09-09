r"""**옮기는 사이에 잃지 않는가.**

실측 2026-09-09, 세 번 연달아: 표를 요약해 전달하니 `무작위` 열이 사라졌다. 그
열이 없으면 도약률 100%가 연산자의 공인지 꼴 바꾸기의 그림자인지 알 수가 없는데,
그 구분을 하려고 대조군을 만든 것이었다. 한 번은 더 물어보면 되지만 세 번은 절차의
결손이다.

원장은 무시 목록에 있다 -- VM 이 계속 쓰는 파일이라 추적하면 배포의 `git pull` 이
매번 충돌한다. 그래서 **파생물**을 남긴다. 여기서 재는 것은 그 파생물에 **요약이
잃어버린 것들이 실제로 들어 있는가** 다.

LLM·네트워크 없이 돈다. 실행: python3 tests/test_seek_report.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seek import problem as PR                                # noqa: E402
from seek import report as RP                                 # noqa: E402

# **고정물을 여기 둔다.** 다른 검사에서 끌어오면 그 파일의 본문이 임포트할 때 다
# 돌아 버리고(그쪽은 모듈이 아니라 실행 파일이다), 그쪽이 실패하면 여기가 같이
# 죽는다 -- 왜 죽었는지 알 수 없는 실패다.
from tests._seek_고정물 import 원장                            # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


_led = 원장()
_글 = RP.build(_led, seed=1, n=60)

print("== 요약이 잃어버린 것이 들어 있다 ==")
ok("무작위" in _글, "**`무작위` 열이 있다** -- 세 번 다 이것이 사라졌다")
ok("도약률" in _글, "도약률이 있다")
ok("잰 것이 적어 못 읽는다" in _글, "얇은 분모 표시가 있다  ← 1/1 도 100% 다")
ok("무작위 짝도 비슷하게 내는 연산자" in _글, "지목 줄이 있다")
ok("까닭 모름" in _글 and "합" in _글, "모름 가르기가 다 있다")
ok("도약 비율 -- 진짜" in _글, "대조군의 두 비율이 나란히 있다")

print("\n== 세 자를 다 담는다 ==")
for 머리 in ("## 감사", "## 대조군", "## 셈", "## 도약으로 판정된 걸음"):
    ok(머리 in _글, f"{머리} 가 있다")

print("\n== 도약의 물음을 글자로 적는다 ==")
# 숫자만 남기면 22개가 무엇인지 아무도 못 본다
ok("A1" in _글 and "A2" in _글, "도약으로 판정된 걸음의 id 가 적힌다")
_도 = _글.split("## 도약으로 판정된 걸음")[-1]
ok("부모:" in _도 and "자식:" in _도, "**부모와 자식의 물음을 나란히 적는다**")
ok("부모봄" in _도 or "꼴만봄" in _도, "어느 연산자였는지도 적는다")

print("\n== 도약이 없으면 없다고 적는다 ==")
_빈 = PR.blank()
_빈["problems"].append({"id": "P1", "물음": "씨앗", "표본": "", "판정": "",
                        "옮김": "", "계보": {"부모": "-", "연산자": "씨앗"}, "깊이": 0})
ok("도약으로 판정된 걸음이 없다" in RP.build(_빈, 1, 10),
   "**0개를 빈칸으로 두지 않는다** -- 빈칸은 '아직 안 봤다' 로 읽힌다")

print("\n== 만들어진 파일이라고 적는다 ==")
ok("만들어진 것이다" in _글 and "report.py --쓰기" in _글,
   "손으로 고치면 덮어쓰인다고 말한다")
ok("무시 목록" in _글, "왜 원장이 아니라 이것인지 적는다")

print("\n== 무시 목록에 걸리지 않는다 ==")
_r = subprocess.run(["git", "check-ignore", "seek/report.md"],
                    cwd=Path(__file__).resolve().parent.parent,
                    capture_output=True, text=True)
ok(_r.returncode != 0, "**seek/report.md 는 커밋할 수 있다** -- 이것이 못 올라가면 헛일이다")
_r2 = subprocess.run(["git", "check-ignore", "seek/ledger.json"],
                     cwd=Path(__file__).resolve().parent.parent,
                     capture_output=True, text=True)
ok(_r2.returncode == 0, "원장은 여전히 무시된다 -- 배포의 pull 이 충돌하면 안 된다")

print("\n== --쓰기 가 실제로 남긴다 ==")
_tmp = Path(tempfile.mkdtemp())
_ledp = _tmp / "led.json"
PR.save(_led, _ledp)
_was = RP.나갈곳
RP.나갈곳 = _tmp / "report.md"
try:
    RP.main(["--쓰기", "--path", str(_ledp), "--n", "60"])
    ok(RP.나갈곳.exists() and "무작위" in RP.나갈곳.read_text(encoding="utf-8"),
       "파일이 생기고 그 안에 무작위 열이 있다")
finally:
    RP.나갈곳 = _was

print("\n== 호출 0회다 ==")
_src = (Path(__file__).resolve().parent.parent / "seek" / "report.py").read_text(encoding="utf-8")
ok("llm_pool" not in _src and "GEMINI" not in _src, "보고서는 LLM 을 안 부른다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("seek 보고서: 무작위 열 · 세 자 · 도약 문장 · 무시 목록 -- 통과")
