"""
G015 -- 검사 파일의 종료 블록이 파일 맨 끝에 있는가.

사고: 2026-09-07. 하루에 **다섯 번** 같은 것을 찾았다.

  tests/test_llm_pool_rpm.py   611줄짜리 파일의 252줄에 종료 블록
  tests/test_flow.py           605줄 중 402줄
  tests/test_genre.py          473줄 중 251줄
  tests/test_style.py          233줄 중 205줄
  (test_llm_pool_rpm 은 옮기고 나서야 진짜 제품 버그 둘이 드러났다 --
   핀이 선호를 덮던 것과, 벌점 먹은 키가 묶음에 얹혀 나가던 것)

무슨 일이 벌어지나. 검사 파일은 이렇게 끝난다:

    if fails:
        print(f"...: {len(fails)}개 실패 -- {fails}")
        sys.exit(1)
    print("... -- 통과")

이 블록 **뒤에** 검사를 덧붙이면, 그 검사들은 실패를 화면에 찍고도 **종료 코드를
0 으로 남긴다.** scripts/tests.sh 는 종료 코드로 판정하므로 스위트는 초록이다.
사람은 초록불을 보고, 화면 어딘가의 '실패' 줄은 스크롤 위로 흘러간다.

이 저장소가 제일 싫어하는 것 그대로다:
**검사하지 않은 초록불은 검사한 빨간불보다 나쁘다.**

왜 게이트인가. 다섯 번이면 개별 실수가 아니라 파일 꼴의 성질이다 -- 검사를 파일
끝에 덧붙이는 습관(자연스럽다)과 종료 블록이 본문 사이에 있는 구조가 만나면
**반드시** 이렇게 된다. 사람이 조심해서 될 일이 아니라 기계가 막을 일이다.

고치는 법은 하나다. **종료 블록을 파일 맨 끝으로 옮긴다.**
"""
from __future__ import annotations

import re

RULE_ID = "G015"
TITLE = "검사의 종료 블록이 파일 맨 끝에 있는가"
ORIGIN = "2026-09-07"

# 종료 블록의 표지. `sys.exit(1)` 과 `raise SystemExit(1)` 둘 다 쓰인다.
_EXIT = re.compile(r"^\s*(sys\.exit\(1\)|raise SystemExit\(1\))\s*$")

# 종료 블록 뒤에 남아도 되는 것들. 요약 print 와 닫는 괄호, 주석, 빈 줄이다.
_TAIL_OK = re.compile(r"^\s*(#|\)|\]|\}|$)|^print\(|^\s+")

# 이 게이트가 보지 않는 파일. `main()` 을 돌려 `raise SystemExit(main())` 으로 끝나는
# 꼴은 종료가 함수 안에 있어서 이 문제가 생기지 않는다.
_MAIN_STYLE = re.compile(r"raise SystemExit\(main\(\)\)|sys\.exit\(main\(\)\)")


def check(ctx) -> "list[str]":
    repo = ctx.repo
    tests = repo / "tests"
    if not tests.is_dir():
        return []

    out: list[str] = []
    for path in sorted(tests.glob("test_*.py")):
        try:
            lines = path.read_text(encoding="utf-8").split("\n")
        except Exception as e:                      # 읽히지 않으면 말은 한다
            out.append(f"tests/{path.name}: 읽지 못했다 ({type(e).__name__})")
            continue
        text = "\n".join(lines)
        if _MAIN_STYLE.search(text):
            continue                                # 종료가 함수 안이다 -- 이 문제가 없다

        hits = [i for i, l in enumerate(lines) if _EXIT.match(l)]
        if not hits:
            continue                                # 종료 블록이 아예 없는 파일은 G015 밖이다

        last = hits[-1]
        # 종료 뒤에 **실제 검사**가 있는지 본다. 요약 print · 주석 · 빈 줄은 괜찮다.
        after = []
        for i in range(last + 1, len(lines)):
            l = lines[i]
            if not l.strip() or _TAIL_OK.match(l):
                continue
            after.append((i + 1, l.strip()))
        if after:
            n, first = after[0]
            out.append(
                f"tests/{path.name}: 종료 블록이 {last + 1}줄에 있는데 파일은 "
                f"{len(lines)}줄이다 -- {n}줄부터 {len(after)}개 문장이 종료 코드에 "
                f"영향을 못 준다(첫 줄: {first[:60]}). "
                f"**실패해도 스위트는 초록으로 본다.** 종료 블록을 맨 끝으로 옮겨라.")
    return out
