r"""
G017 -- 잘못된 이스케이프가 남아 있지 않은가.

**실측 2026-09-08, VM 로그 첫 줄이 이것이었다:**

    /home/ubuntu/SE/mathdrift/spread.py:455: SyntaxWarning: invalid escape sequence '\i'

`\inf` 를 평범한 문자열(독스트링 포함)에 쓰면 파이썬이 경고한다. LaTeX 을 다루는
저장소라 `\lambda` `\inf` `\sum` 이 독스트링에 흔하고, 그래서 이것이 계속 난다.

## 왜 게이트인가 -- 경고일 뿐인데

세 가지가 걸린다.

  1. **경고가 곧 오류가 된다.** 파이썬 3.12 에서 SyntaxWarning 이 됐고 3.15 에서
     SyntaxError 가 될 예정이다. 지금 안 고치면 나중에 임포트가 통째로 막힌다.
  2. **로그를 더럽힌다.** 24시간 런의 로그 첫 줄이 경고면 진짜 신호를 가린다.
  3. **글자가 실제로 바뀐다.** `"\n"` 은 줄바꿈이지 백슬래시-n 이 아니다. 문서에
     적은 식과 실제로 담긴 식이 달라진다 -- 이 저장소가 `_fix_escapes` 에서
     겪은 바로 그 문제의 반대쪽이다.

## 고치는 법

문자열 앞에 `r` 을 붙인다. 독스트링도 `r\"\"\"` 로 쓸 수 있다.
"""
from __future__ import annotations

import warnings

RULE_ID = "G017"
TITLE = "LaTeX 이 파이썬 문자열을 깨지 않는가"
ORIGIN = "VM 로그 2026-09-08"

_SKIP = {".git", "venv", "__pycache__", "node_modules", "inbox"}


def check(ctx) -> "list[str]":
    bad: list[str] = []
    for f in ctx.python_files():
        try:
            src = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                compile(src, str(f), "exec")
            except SyntaxError:
                continue        # 문법 오류는 G012 가 임포트로 잡는다
            for w in caught:
                if "escape" in str(w.message):
                    bad.append(f"{ctx.rel(f)}:{w.lineno} -- {w.message}. "
                               "문자열 앞에 `r` 을 붙여라 (독스트링도 된다). "
                               "3.15 에서 SyntaxError 가 된다")
    return bad
