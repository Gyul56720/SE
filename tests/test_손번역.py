# -*- coding: utf-8 -*-
"""손으로 옮길 때 쓰는 연장과, **느슨해진 대조가 여전히 무는가.**

사용자(2026-09-21): *"너가 그냥 써줘."*  Gemini 키가 없는 자리에서 교재를 직접
옮기게 되었고, 그때 옮기는 일은 사람이 하되 검사는 기계가 한다.

## 왜 대조를 느슨하게 했나 -- 그리고 왜 그것이 위험한가

순서만 보는 태그 검사는 **옳은 한국어 번역을 틀렸다고 낸다.**  영어
"for every <b>85 mV</b> that V<sub>GS</sub> drops" 가 한국어에서는
"V<sub>GS</sub> 가 ... <b>85 mV</b> 내려갈 때마다" 가 되어 태그 순서가 바뀐다.
태그는 하나도 안 늘고 안 줄었는데도 그렇다.

그래서 **구조 태그는 순서까지, 안쪽 태그는 블록 안의 개수**만 본다.
느슨하게 만든 검사는 **못 무는 검사가 되기 쉽다** -- 그래서 여기서 일부러
망가뜨려 보고 전부 무는지 확인한다.  이 파일이 없으면 위의 완화는
'검사하지 않은 초록불' 이다.

    python3 tests/test_손번역.py
"""
from __future__ import annotations

import os
import sys

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(뿌리, "edu"))
sys.path.insert(0, os.path.join(뿌리, "edu", "번역"))

import translate  # noqa: E402
import 손번역  # noqa: E402

fails = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        fails.append(말)


원 = """<div class="개념"><p>The current falls by a factor of ten for every
<b>85&nbsp;mV</b> that V<sub>GS</sub> drops below V<sub>t</sub>.</p>
<table><tbody><tr><th>Where</th><td>Standby power of 40,000 gates.</td></tr>
<tr><th>When</th><td>Whenever <i>idle</i>.</td></tr></tbody></table>
<pre><code>cell (NAND2_X1) { area : 1.596 ; }</code></pre></div>"""

옮 = """<div class="개념"><p>V<sub>GS</sub> 가 V<sub>t</sub> 아래로
<b>85&nbsp;mV</b> 내려갈 때마다 전류는 열 배씩 준다.</p>
<table><tbody><tr><th>어디에</th><td>게이트 40,000 개의 대기 전력.</td></tr>
<tr><th>언제</th><td><i>놀고</i> 있을 때마다.</td></tr></tbody></table>
<pre><code>cell (NAND2_X1) { area : 1.596 ; }</code></pre></div>"""

print("[어순] 태그가 문장 안에서 자리를 옮긴 것은 통과해야 한다")
ok(not translate.대조(원, 옮),
   f"어순이 바뀐 옳은 번역이 통과한다 (얻은 값 {translate.대조(원, 옮)})")
ok(translate.태그열(원) != translate.태그열(옮),
   "그런데 **순서만 보는 옛 검사로는 달랐다** -- 완화가 필요했던 것이 맞다")

print()
print("[자해] 느슨해진 검사가 **진짜 잘못은 여전히 무는가**")
깨기 = [
    ("td 하나를 지운다", 옮.replace("<td>게이트 40,000 개의 대기 전력.</td>", "")),
    ("코드 속을 바꾼다", 옮.replace("1.596", "9.999")),
    ("수를 지운다", 옮.replace("40,000", "여러")),
    ("<b> 를 옆 블록으로 옮긴다",
     옮.replace("<b>85&nbsp;mV</b>", "85&nbsp;mV")
       .replace("<td>게이트", "<td><b></b>게이트")),
    ("<i> 를 지운다", 옮.replace("<i>놀고</i>", "놀고")),
    ("문단을 통째로 빠뜨린다", 옮.replace(
        "<p>V<sub>GS</sub> 가 V<sub>t</sub> 아래로\n<b>85&nbsp;mV</b> "
        "내려갈 때마다 전류는 열 배씩 준다.</p>", "<p></p>")),
    ("표를 통째로 빠뜨린다", 옮[:옮.index("<table")] + 옮[옮.index("<pre>"):]),
]
for 이름, 나쁜것 in 깨기:
    문제 = translate.대조(원, 나쁜것)
    ok(bool(문제), f"{이름} -> 잡는다 ({(문제 or ['**못 잡음**'])[0][:56]})")

print()
print("[숫자] 문장부호가 붙은 수를 '빠졌다' 고 잘못 내지 않는다")
ok(not translate.대조("<p>so t/τ &gt; 11·ln2 = 7.62.</p>",
                     "<p>따라서 t/τ &gt; 11·ln2 = 7.62 다.</p>"),
   "영어 '= 7.62.' 와 한국어 '= 7.62 다.' 는 같은 수로 본다")
ok(bool(translate.대조("<p>7.62 and 3.14</p>", "<p>7.62 만</p>")),
   "**진짜로 빠진 수는 여전히 잡는다**")

print()
print("[조각] 나눈 것을 이으면 원문이다")
장 = 손번역.이론장들()
ok(len(장) >= 20, f"이론서 장이 {len(장)}개 보인다")
나쁨 = []
for c in 장:
    h = 손번역.원문(c["모듈"])
    if "".join(손번역.나누기(h)) != h:
        나쁨.append(c["모듈"])
ok(not 나쁨, f"모든 장에서 조각을 이으면 원문과 같다 (얻은 값 {나쁨})")
ok(all(len(손번역.나누기(손번역.원문(c["모듈"]))) >= 1 for c in 장),
   "장마다 조각이 하나 이상 나온다")

print()
print("[낸 것] 이미 낸 한국어 장은 전부 대조를 통과한다")
ok(손번역.검사(보고=lambda *a: None), "낸 장이 전부 통과한다")

print()
if fails:
    print(f"손번역: {len(fails)}개 실패")
    for m in fails:
        print("   -", m)
    sys.exit(1)
print("손번역: 어순 완화 · 자해 일곱 · 숫자 부호 · 조각 왕복 · 낸 것 대조 -- 통과")
