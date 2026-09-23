# -*- coding: utf-8 -*-
"""**보고서에 마크다운·태그가 글자로 새지 않는가 -- 렌더해서 잰다.**

실측 2026-09-23, MERA 제안서(`mera1_event_recorder`)에서 난 일:

    Table 1   관문 1·2 + rtlscan CDC건넘 (**RDC 없음**)
    Table 7   비동기로 걸고 **동기로 푸는** 것이 규칙이다

표 칸에 마크다운 `**` 가 그대로 찍혔다. `house/flow.py` 와 `house/specq.py` 의
글에 적혀 있던 것이다 -- 보고서는 HTML 이라 `**` 가 굵게가 되지 않는다.

## 그리고 그 반대도 있었다

`<b>` 로 바꿨더니 이번엔 **`&lt;b&gt;` 로 찍혔다.** `viz.표()` 가 칸을
`v.startswith("<")` 일 때만 원시 HTML 로 냈기 때문이다 -- **첫 글자가
무엇이냐로 칸 전체의 뜻이 갈리는 덫**이다. 이 저장소가 두 번 걸렸다
(`<small>` · `<b>`). 지금은 전부 escape 한 뒤 꾸미기 태그만 되살린다.

## 글자를 보는 검사로는 못 잡는다

두 줄에 걸쳐 적힌 문자열(`"… **몇 비트를 "  "실제로 …**"`)은 소스에서 안 걸린다.
그래서 **렌더해서** 잰다.

실행: python3 tests/test_보고서글자.py
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


from house import arch as A                                  # noqa: E402
from house import req as REQ                                 # noqa: E402
from house import viz as V                                   # noqa: E402
from house.dv import trace as TRACE                          # noqa: E402

_보임 = re.compile(r"<(style|script)[^>]*>.*?</\1>", re.S | re.I)


def 보이는글(h: str) -> str:
    """사람이 **PDF 에서 보는 글자**만. `<style>` 속 CSS 는 안 보인다.

    이 걷어냄이 없으면 내가 CSS 주석에 적은 `**한 줄이…**` 가 「샜다」로
    잡힌다 -- 첫 판이 실제로 그랬다. **안 보이는 것을 샜다고 하면 안 된다.**
    """
    return re.sub(r"<[^>]+>", " ", _보임.sub(" ", h))


_요청 = ("# MERA-1 v1.0 Event Recorder Core\n\n| 항목 | 값 |\n|---|---|\n"
       "| 채널 수 | 1 |\n| PRE | 4096 complex sample |\n\n"
       "AXI4-Stream 256-bit. 제어는 AXI4-Lite. DDR 출력은 AXI4-MM master.\n"
       "aresetn. sticky flag. 500 MHz. 0.8 V. 누산기를 쓴다.\n")

_m = A.일하기(_요청)
# 모델이 채우는 칸을 손으로 넣어 **그 길도** 렌더된다(목표 → 요구사항 → 겹침).
_m["_s"].목표 = [{"항목": "클럭 주파수", "값": "500 MHz"},
              {"항목": "공급 전압", "값": "0.8 V"},
              {"항목": "처리율", "값": "고성능"}]
_m["요구"] = REQ.붙이기(_m["_s"], _m.get("미정"))
_m["이음"] = TRACE.걸기(_m["요구"], _m["계획"])
_h = A.보고서(_m).html()
_글 = 보이는글(_h)

# ============================================ 1. 마크다운이 안 샌다
_마크 = re.findall(r"\*\*[^*\n]{1,80}\*\*", _글)
ok(not _마크, f"**마크다운 `**` 가 안 보인다**"
   + (f" — 샌 것 {len(_마크)}개: {_마크[:2]}" if _마크 else ""))
_별 = re.findall(r"(?<![\w*])\*[^*\n]{2,40}\*(?![\w*])", _글)
ok(not _별, f"홑별표 기울임도 안 보인다 ({_별[:2]})")

# ============================================ 2. 태그가 글자로 안 찍힌다
_샌태그 = re.findall(r"&lt;/?(?:b|i|code|small|br|sub|sup)&gt;", _h)
ok(not _샌태그, f"**HTML 태그가 글자로 안 찍힌다** ({len(_샌태그)}개)")
ok("<b>" in _h and _h.count("<b>") > 30,
   f"굵게는 실제로 굵게 나간다 ({_h.count('<b>')}개)")

# ============================================ 3. 표 칸의 덫을 없앴다
# 옛 판: `v if v.startswith("<") else _e(v)` -- 첫 글자로 칸 전체가 갈렸다.
_칸 = V.표(["ㄱ"], [["비동기로 걸고 <b>동기로 푸는</b> 것"]])
ok("<b>동기로 푸는</b>" in _칸,
   "**문장 중간의 `<b>` 가 굵게 나간다** — 첫 글자가 `<` 가 아니어도")
ok("<b>없다</b>" in V.표(["ㄱ"], [["<b>없다</b>"]]),
   "칸 전체가 태그인 옛 쓰임도 그대로 돈다")
ok("&lt;script&gt;" in V.표(["ㄱ"], [["<script>x</script>"]]),
   "**꾸미기 아닌 태그는 여전히 escape 된다** — 살리는 것은 흰 목록뿐이다")
ok("&amp;" in V.표(["ㄱ"], [["a & b"]]), "앰퍼샌드도 escape 된다")

# ============================================ 4. 쪽 사이에서 줄이 안 갈라진다
# 실측: `REQ-MERA1-015` 가 앞쪽 끝에 **번호만** 남고 내용은 다음 쪽으로 갔다.
ok("table.d tr { page-break-inside: avoid" in _h,
   "**표의 한 줄이 쪽 사이에서 안 갈라진다**")
ok("table.d thead { display: table-header-group" in _h,
   "머리줄을 다음 쪽에도 되풀이한다")

# ============================================ 5. 겹쳐 보이는 요구사항을 알린다
# REQ-001 `주파수_Hz = 5e+08` ↔ REQ-0NN `클럭 주파수: 500 MHz` 는 같은 사실이다.
_겹 = _m["요구"]["겹쳐보임"]
ok(len(_겹) >= 2, f"**같은 것을 두 번 센 짝을 찾는다** "
   f"({[(a['id'], b['id'], c) for a, b, c in _겹][:2]})")
ok("쌍은 같은 것을 두 번 센" in _글, "제안서가 그것을 알린다")
_아이디 = [x["id"] for x in _m["요구"]["요구사항"]]
ok(len(set(_아이디)) == len(_아이디), "**묶지는 않는다** — 번호는 그대로 다 있다")

# ============================================ 6. 측정이 안 보이는 것을 세지 않는다
ok("**" in _h and "**" not in _글,
   "**`<style>` 속 CSS 주석의 `**` 를 「샜다」로 안 센다** — "
   "안 보이는 것을 샜다고 하면 거짓 빨간불이다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("보고서글자: 마크다운 안 샘 · 태그 안 샘 · 표 칸 덫 없앰 · 겹침 알림 -- 통과")
