r"""escapes -- 파이썬 문자열의 **잘못된 이스케이프를 코드가 고친다.** G017 의 자동 수리.

실측 2026-09-11: 봇이 codify 로 만든 `codify/out/…_수식2.py` 6행의 `\int` 에 G017 이 걸려
커밋이 막혔다. 게이트가 띄우기만 했고 사람이 고쳐야 했다 -- 사용자: "띄우는 게 아니라
자동으로 고쳐줘야지". 그래서 고치는 손을 한 곳에 둔다. codify 는 저장 전에, 게이트는
`--고치기` 로, 같은 함수를 부른다.

어떻게: tokenize 로 STRING 토큰마다 그 리터럴만 compile 해 '경고가 나는가' 를 본다(판정은
코드). 나면 **뜻을 안 바꾸는 쪽으로** 고친다: 유효한 이스케이프(`\n` `\t` `\"` …)가 하나라도
섞여 있으면 잘못된 `\x` 만 `\\x` 로 겹치고(r 을 붙이면 `\n` 이 줄바꿈이 아니게 된다), 하나도
없으면 앞에 `r` 을 붙인다. 어느 쪽이든 다시 compile 해 경고도 오류도 없을 때만 채택한다.
고친 뒤 파일 전체를 다시 compile 해 문법이 멀쩡할 때만 돌려준다. 못 고치면 원문 그대로 0.

    python3 escapes.py <파일...>      # 고친 파일 수를 찍는다. 끝값 0
"""
from __future__ import annotations

import io
import re
import sys
import tokenize
import warnings
from pathlib import Path

_유효 = r"\\(?![\n\\'\"abfnrtvx0-7NuU])"      # 이 뒤에 오면 잘못된 이스케이프다 (str 기준)
_접두 = re.compile(r"^[a-zA-Z]*")


def _경고나나(리터럴: str) -> "bool | None":
    """그 리터럴 하나를 compile 해 본다. True 경고 · False 깨끗 · None 문법 오류(단독으론 못 봄)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            compile(리터럴, "<리터럴>", "eval")
        except SyntaxError:
            return None
    return any("escape" in str(w.message) for w in caught)


def _고친리터럴(tok: str) -> "str | None":
    접두 = _접두.match(tok).group(0)
    if "r" in 접두.lower() or "f" in 접두.lower():
        return None                                     # raw 는 이미 됐고, f-string 은 손대지 않는다
    몸 = tok[len(접두):]
    # **뜻을 바꾸지 않는 쪽으로.** `"\\int\\n"` 에 r 을 붙이면 \\n 이 줄바꿈이 아니게 된다 --
    # 유효한 이스케이프가 하나라도 섞여 있으면 잘못된 것만 `\\\\x` 로 겹치고, 하나도 없으면 r 을 붙인다.
    if re.search(r"\\[\n\\\'\"abfnrtvx0-7NuU]", 몸):
        겹친 = 접두 + re.sub(_유효, r"\\\\", 몸)
        return 겹친 if _경고나나(겹친) is False else None
    후보 = 접두 + "r" + 몸
    if _경고나나(후보) is False:
        return 후보
    겹친 = 접두 + re.sub(_유효, r"\\\\", 몸)
    return 겹친 if _경고나나(겹친) is False else None


def 고치기(src: str) -> "tuple[str, int]":
    """잘못된 이스케이프가 있는 문자열 리터럴을 고친 (새 원문, 고친 수). 못 고치면 (원문, 0)."""
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, SyntaxError):
        return src, 0
    줄들 = src.splitlines(keepends=True)
    고침 = []
    for t in toks:
        if t.type != tokenize.STRING or _경고나나(t.string) is not True:
            continue
        새 = _고친리터럴(t.string)
        if 새:
            고침.append((t.start, t.end, 새))
    if not 고침:
        return src, 0
    # 뒤에서부터 바꿔야 앞의 위치가 안 밀린다
    for (r1, c1), (r2, c2), 새 in sorted(고침, reverse=True):
        앞 = 줄들[r1 - 1][:c1]
        뒤 = 줄들[r2 - 1][c2:]
        줄들[r1 - 1:r2] = [앞 + 새 + 뒤]
    새src = "".join(줄들)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            compile(새src, "<고친것>", "exec")
    except (SyntaxError, Warning):
        return src, 0                                   # 고친 것이 더 나쁘면 안 고친다
    return 새src, len(고침)


def 파일고치기(path) -> int:
    p = Path(path)
    try:
        src = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    새, n = 고치기(src)
    if n:
        p.write_text(새, encoding="utf-8")
    return n


def main() -> int:
    총 = 0
    for a in sys.argv[1:]:
        n = 파일고치기(a)
        총 += n
        print(f"  {'고침' if n else '그대로'} {a} ({n})")
    print(f"고친 리터럴 {총}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
