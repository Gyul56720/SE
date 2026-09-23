# -*- coding: utf-8 -*-
"""**스윕 보고서가 안 흔든 파라미터를 주인공으로 세우지 않는가.**

실측 2026-09-22, `20260922_EthanRoss_RTL.pdf` (RTL-RPT) 에서 난 일:

    Table 7   여섯 구성이 전부 `TAPS=8, STAGES=3` 으로 찍혔다
              그런데 면적은 59,383 ~ 129,181 µm² 로 갈렸다
    Fig 12    설명이 «TAPS 가 계수 메모리와 카운터 폭을 통해 면적을 끈다»
    Fig 13    설명이 «파이프라인 단수를 줄이면(S2) Fmax 가 내려간다»
    §5 경고   «STAGES 를 3→2 로 줄였더니 Fmax 가 올라갔다» -- 한 문단 통째로

**`_스윕조합()` 은 TAPS 도 STAGES 도 한 번도 안 흔든다.** 값이 큰 파라미터
셋(ACCW · DW · CW)을 흔든다. 그러니 저 네 줄은 **돌지 않은 실험의 결론**이
매 보고서마다 실려 나간 것이다.

    과장하지 않는다 -- 표제는 유리한 구석에서 나온 수가 아니다 (CLAUDE.md)

여기서 붙드는 것은 하나다: **이름과 설명이 잰 것에서 나오는가.**

실행: python3 tests/test_스윕이름.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


from house.rtl import agent as RA       # noqa: E402
from house import designs as DES        # noqa: E402
from house import rtlscan as SCAN       # noqa: E402


def 민글(s):
    return re.sub(r"<[^>]+>", "", s)


_기본 = {"TAPS": 8, "DW": 16, "CW": 16, "ACCW": 40, "STAGES": 3}
_조합 = [_기본, {**_기본, "ACCW": 80}, {**_기본, "ACCW": 20}, {**_기본, "DW": 32}]

# ============================================ 1. 이름은 **흔든 것**만 적는다
_이름들 = [RA._구성이름(c, _기본) for c in _조합]
ok(_이름들 == ["기본", "ACCW=80", "ACCW=20", "DW=32"],
   f"구성 이름이 기본과 **다른 칸만** 적는다 ({_이름들})")
ok(len(set(_이름들)) == len(_이름들),
   "**네 구성이 네 이름을 받는다** — 여섯 막대가 한 이름으로 찍히던 자리다")
ok(not any("TAPS" in n or "STAGES" in n for n in _이름들),
   "**안 흔든 `TAPS`·`STAGES` 가 이름에 안 들어간다**")
ok(RA._흔든이름들(_조합) == ["ACCW", "DW"],
   f"흔든 파라미터를 세어 돌려준다 ({RA._흔든이름들(_조합)})")

# ============================================ 2. 진짜 스윕이 무엇을 흔드나
# **이것이 이 검사의 뿌리다.** 코드가 TAPS 를 안 흔든다는 것을 여기서 못 박는다.
_d = DES.찾기("fir")
_조합2 = RA._스윕조합(SCAN.훑기(_d.RTL, _d.top), _d)
_흔든2 = RA._흔든이름들(_조합2)
ok(_흔든2, f"nsw_fir 스윕이 무언가를 흔든다 ({_흔든2})")
ok("TAPS" not in _흔든2 and "STAGES" not in _흔든2,
   f"**nsw_fir 스윕은 TAPS·STAGES 를 안 흔든다** — 그러니 그 이름으로 말하면 "
   f"안 된다 (흔든 것: {_흔든2})")

# ============================================ 3. 깊이 표에 딴것이 안 들어온다
# 옛 거르개는 `"STAGES" in x["파라"]` 였는데 그 칸은 **모든 구성에 늘 있다**.
_재사용 = [
    {"파라": _기본, "pass": 400, "fail": 0, "timeout": 0},
    {"파라": {**_기본, "ACCW": 20}, "pass": 15, "fail": 385, "timeout": 0},
    {"파라": {**_기본, "STAGES": 2}, "pass": 400, "fail": 0, "timeout": 0},
]
_깊이 = RA._깊이흔든줄(_재사용, _기본)
ok(len(_깊이) == 1 and _깊이[0]["파라"]["STAGES"] == 2,
   f"**깊이를 정말로 바꾼 줄만 고른다** ({len(_깊이)}줄)")
ok(not any(x["fail"] == 385 for x in _깊이),
   "**`ACCW` 를 흔든 385 실패 줄이 「깊이」 표에 안 들어온다** — "
   "「깊이를 바꿔도 기능이 유지된다」 설명 아래 앉아 있던 줄이다")
ok(RA._깊이흔든줄([{"파라": _기본, "pass": 400, "fail": 0, "timeout": 0},
                {"파라": {**_기본, "ACCW": 20}, "pass": 1, "fail": 9, "timeout": 0}],
               _기본) == [],
   "깊이를 안 흔들었으면 **빈 목록** — 표 대신 「안 흔들었다」 를 적게 된다")

# ============================================ 4. 설명의 수가 자료에서 나온다
# 옛 판: «지연은 4 → 10 단계로 오른다». 바로 위 표는 3 → 5 였다.
_t = [{"이름": "4곱셈기", "자원": {"mul": 4, "add": 2}, "지연": 3, "II": 1, "면적추정": 2456},
     {"이름": "2곱셈기", "자원": {"mul": 2, "add": 1}, "지연": 3, "II": 1, "면적추정": 2456},
     {"이름": "1곱셈기", "자원": {"mul": 1, "add": 1}, "지연": 5, "II": 2, "면적추정": 1916}]
_맞 = 민글(RA._맞바꿈글(_t))
ok("3 → 5 단계" in _맞, f"지연을 **표와 같은 수**로 적는다 ({_맞[-46:].strip()})")
ok("4 → 10" not in _맞, "**«4 → 10» 이 안 나온다** — 어디에서도 잰 적 없는 수였다")
_t2 = [dict(x) for x in _t]
_t2[2]["지연"] = 9
ok("3 → 9 단계" in 민글(RA._맞바꿈글(_t2)),
   "**자료를 바꾸면 설명의 수도 바뀐다** — 글에 안 박혀 있다는 뜻이다")

# ============================================ 5. 같은 점을 두 개로 안 센다
_파 = 민글(RA._파레토글(_t))
ok("서로 다른 점은 2개" in _파, f"**세 구성이지만 점은 둘**이라고 적는다 ({_파[:40]})")
ok("4곱셈기" in _파 and "2곱셈기" in _파 and "같다" in _파,
   "**어느 둘이 같은지 이름을 댄다** — 식에 곱셈이 둘뿐이라 넷을 줘도 논다")
_t3 = [dict(x) for x in _t]
_t3[0]["면적추정"] = 3200
ok("서로 다른 점은 3개" in 민글(RA._파레토글(_t3)),
   "겹치지 않으면 셋으로 센다 — 세는 것이지 적어 둔 것이 아니다")

# ============================================ 6. 지어낸 문장이 지워졌다
# **docstring 을 걷어내고 본다.** 고친 함수들의 docstring 이 옛 문장을 그대로
# 인용해 둬서(무엇이 틀렸었는지 남기려고) 글자만 보면 「아직 있다」로 읽힌다 --
# 글자를 보는 검사는 **산 주장과 사후 기록을 못 가른다**. 주석도 같이 턴다.
import ast          # noqa: E402
import io           # noqa: E402
import tokenize     # noqa: E402

_원소스 = (뿌리 / "house" / "rtl" / "agent.py").read_text(encoding="utf-8")


def _독스트링뺀소스(글: str) -> str:
    나무 = ast.parse(글)
    뺄자리 = []
    for n in ast.walk(나무):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)) and ast.get_docstring(n, clean=False):
            d = n.body[0]
            뺄자리.append((d.lineno, d.end_lineno))
    줄 = 글.splitlines()
    for a, b in 뺄자리:
        for i in range(a - 1, b):
            줄[i] = ""
    남 = "\n".join(줄)
    # 주석도 턴다
    나온것 = []
    for tok in tokenize.generate_tokens(io.StringIO(남).readline):
        if tok.type != tokenize.COMMENT:
            나온것.append(tok.string)
    return "\n".join(나온것)


_소스 = _독스트링뺀소스(_원소스)
ok(len(_소스) < len(_원소스), "docstring·주석을 걷어내고 본다 (산 주장만 남긴다)")
ok("4 → 10 단계" in _원소스,
   "**옛 문장은 docstring 에 기록으로 남아 있다** — 무엇이 틀렸었는지 지우지 않는다")
for 없어야, 뭐 in (
    ('f"TAPS{s[', "그림 라벨에 박힌 `TAPS{...}/S{...}`"),
    ("TAPS 가 계수 메모리와 카운터 폭을 통해 면적을 끈다", "«TAPS 가 면적을 끈다»"),
    ("4 → 10 단계", "«지연 4 → 10 단계»"),
    ("세 점이 파레토 앞면을 이룬다", "«세 점이 파레토 앞면»"),
    ("STAGES</code> 를 3→2 로 줄였더니", "«STAGES 를 3→2 로 줄였더니» 한 문단"),
    ("TAPS/STAGES 만 바꿔 면적", "요약 줄의 «TAPS/STAGES 만 바꿔»"),
):
    ok(없어야 not in _소스, f"**지웠다**: {뭐}")
ok("_구성이름" in _소스 and "_흔든이름들" in _소스 and "_깊이흔든줄" in _소스,
   "그 자리를 **재는 함수**가 대신한다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("스윕이름: 흔든 것만 적는다 · 깊이 표가 안 섞인다 · 설명의 수가 자료에서 난다 -- 통과")
