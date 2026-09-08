"""선택형 -- **관문을 거꾸로 쓴다.** 그러나 조문이 말해 주는 자리에서만.

출제자가 오답을 만드는 축(서법·접속·경계·법효과어·용어)이 W001~W005 와 같다는 것이
이 파일의 전제다. 그래서 관문이 잡는 것이 곧 오답 지문이다.

**적은 채로 정확한 것**이 목표다 -- 조문이 말해 주지 않는 자리에서 답을 지어내면
그건 이 저장소가 막으려는 바로 그것이다. 그래서 검사의 절반이 '안 답하는가' 다.

    python3 tests/test_law_mcq.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import corpus as CP                                          # noqa: E402
from law import exam as EX                                            # noqa: E402
from law import mcq as MQ                                             # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "law_corpus"
CORPUS = CP.load(FIXTURE)
fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


print("[물음 읽기] 옳은 것을 고르라는지 아닌지를 뒤집으면 답이 뒤집힌다")
for 물음, 답 in (("다음 중 옳지 않은 것은?", "옳지않은"),
                 ("옳은 것을 모두 고른 것은?", "옳은"),
                 ("적절하지 않은 것은?", "옳지않은"),
                 ("이에 관한 설명이다.", "?")):
    ok(MQ.polarity(물음) == 답, f"{물음!r} -> {답} (얻은 값 {MQ.polarity(물음)})")

print()
print("[선택지 꼴] 지문인가 · 보기 조합인가 · OX 조합인가")
_지문 = EX.parse("문 1.\n옳지 않은 것은?\n① 제22조에 따라 청산한다.\n② 다른 지문이다.\n")[0]
_조합 = EX.parse("문 2.\n옳은 것을 고른 것은?\nㄱ. 가\nㄴ. 나\n① ㄱ\n② ㄱ, ㄴ\n")[0]
_ox = EX.parse("문 3.\n옳은 것과 옳지 않은 것을 조합한 것은?\nㄱ. 가\n① ㄱ(○), ㄴ(×)\n② ㄱ(×), ㄴ(○)\n")[0]
ok(MQ.shape(_지문) == "지문", f"지문 꼴 (얻은 값 {MQ.shape(_지문)})")
ok(MQ.shape(_조합) == "조합", f"보기 조합 꼴 (얻은 값 {MQ.shape(_조합)})")
ok(MQ.shape(_ox) == "OX", f"OX 조합 꼴 (얻은 값 {MQ.shape(_ox)})")

print()
print("[푼다] 조문과 어긋나는 지문이 **정확히 하나**일 때만 답한다")
# 가상시험법 제12조는 '3년 내에' 다. '5년' 으로 바꾼 지문이 조문과 어긋난다.
_원문 = CORPUS.text("가상시험법", "12")
ok(_원문 and "3년" in _원문, f"고정점: 제12조에 '3년' 이 있다 (얻은 값 {(_원문 or '')[:40]!r})")
q = EX.parse("문 5.\n다음 중 옳지 않은 것은?\n"
             "① 제12조에 따라 3년 내에 하여야 한다.\n"
             "② 제12조에 따라 5년 내에 하여야 한다.\n")[0]
r = MQ.solve(q, CORPUS)
ok(r["고름"] == 2, f"조문과 어긋난 ②를 짚는다 (얻은 값 {r['고름']} · {r.get('왜못품')})")
ok(r["근거"], "왜 그것인지 근거가 남는다")

print()
print("[안 푼다] **어긋남을 못 찾은 것은 옳다는 뜻이 아니다** (미검증 != 통과)")
q = EX.parse("문 6.\n다음 중 옳지 않은 것은?\n"
             "① 제12조에 따라 3년 내에 하여야 한다.\n"
             "② 판례에 따르면 그렇지 않다.\n")[0]
r = MQ.solve(q, CORPUS)
ok(r["고름"] == 0 and "못 찾았다" in r["왜못품"],
   f"어긋난 지문이 없으면 안 답한다 (얻은 값 {r['고름']} · {r['왜못품'][:40]})")

q = EX.parse("문 7.\n다음 중 옳지 않은 것은?\n"
             "① 제12조에 따라 5년 내에 하여야 한다.\n"
             "② 제12조에 따라 7년 내에 하여야 한다.\n")[0]
r = MQ.solve(q, CORPUS)
ok(r["고름"] == 0 and "2개다" in r["왜못품"],
   f"어긋난 것이 둘이면 안 답한다 -- 하나는 자가 헛짚은 것이다 (얻은 값 {r['왜못품'][:44]})")

q = EX.parse("문 8.\n다음 중 옳지 않은 것은?\n① 판례에 의한다.\n② 다른 판례에 의한다.\n")[0]
r = MQ.solve(q, CORPUS)
ok(r["고름"] == 0 and "조문이 안 걸렸다" in r["왜못품"],
   f"조문이 하나도 안 걸리면 안 답한다 (얻은 값 {r['왜못품'][:40]})")

q = EX.parse("문 9.\n이에 관한 설명이다.\n① 제12조에 따라 5년 내에 하여야 한다.\n")[0]
ok(MQ.solve(q, CORPUS)["고름"] == 0, "물음 꼴을 못 읽으면 안 답한다 -- 뒤집히면 답이 뒤집힌다")

print()
print("[보고] **답한 것만 센다** -- 안 답한 것은 틀린 게 아니라 안 푼 것이다")
_행 = [{"번호": 1, "고름": 2, "근거": [], "왜못품": ""},
       {"번호": 2, "고름": 0, "근거": [], "왜못품": "조문이 안 걸렸다"},
       {"번호": 3, "고름": 5, "근거": [], "왜못품": ""}]
_r = MQ.report(_행, {1: 2, 2: 3, 3: 1})
ok("답한 것 2개" in _r and "정답 1/2" in _r,
   f"분모가 '답한 것' 이다 (얻은 값 {[l.strip() for l in _r.splitlines() if '정답' in l]})")
ok("안 푼 것 1개" in _r, "안 푼 것이 몇 개인지 따로 적는다 -- 그만큼이 조문으로 안 보이는 자리다")
ok("못 푼 까닭" in _r, "왜 못 풀었는지를 까닭별로 센다 -- 다음에 무엇을 채울지가 거기 있다")

print()
if fails:
    print(f"선택형: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("선택형: 물음 읽기 · 선택지 꼴 · 하나일 때만 답함 · 안 푼 것을 갈라 셈 -- 통과")
