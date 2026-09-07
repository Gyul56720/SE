"""**관문이 진짜 잡는가를 재는 자**가 제대로 재는지.

law/mutate.py 는 낱말 하나를 일부러 틀리게 심고 관문이 잡는지 센다. 그 자 자체가
틀리면 "다 잡았다" 는 거짓 초록이 나온다. 그래서 여기서 두 가지를 본다:

    심은 것을 관문이 잡는가        -- 잡아야 한다
    심을 자리가 아닌 곳에 안 심는가 -- 조문에 그 범주가 없으면 심지 않는다

    python3 tests/test_law_mutate.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from law import corpus as CP                                          # noqa: E402
from law import gate as G                                             # noqa: E402
from law import mutate as MU                                          # noqa: E402

CORPUS = CP.load(ROOT / "tests" / "fixtures" / "law_corpus")

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


# **절 이름을 줄여 쓰면 안 된다.** L007 이 여덟 절을 이름으로 본다.
SECTIONS = ("1. 왜 알아야 하는가", "2. 조문과 이론", "3. 핵심 법리", "4. 해석기법",
            "5. 실무상 흔한 오해", "6. 사례 적용 (학습용 창작 사례, 실제 판례 아님)",
            "7. 연습 사실관계", "8. 다음 주제와의 연결")


def make(sentence, where="2. 조문과 이론"):
    b = ['---', 'title: "x"', 'domain: "x"', 'tags: "x"',
         'key_principle: "x"', 'source_statute: "가상시험법"', '---', '']
    for n in SECTIONS:
        b.append(f"## {n}")
        b.append((sentence if n == where else "가상의 내용.") + "\n")
    b.insert(-1, "")
    d = Path(tempfile.mkdtemp())
    (d / "검사문서.md").write_text("\n".join(b), encoding="utf-8")
    return d


def arts(sentence):
    doc = G.parse(next(make(sentence).glob("*.md")))
    return MU._cited(sentence, doc, CORPUS)


print("[심기] 조문이 정한 것과 반대로 낱말을 바꾼다")
s = "제20조에 따라 행정청은 시정을 명할 수 있다."
ok("하여야 한다" in (MU.m_modality(s, arts(s)) or ""),
   f"조문이 재량이면 기속으로 심는다 (얻은 값 {MU.m_modality(s, arts(s))!r})")
s = "제12조는 해산일부터 3년 이내에 종결하여야 한다."
ok("초과" in (MU.m_bound(s, arts(s)) or ""), "조문이 '이내' 면 '초과' 로 심는다")
s = "제22조는 청산에 관하여 제12조를 준용한다."
ok("적용" in (MU.m_effect(s, arts(s)) or ""), "조문이 '준용' 이면 '적용' 으로 심는다")
s = "제7조는 재산상 이익을 취득한 자를 처벌한다."
ok("재물" in (MU.m_term(s, arts(s)) or ""), "조문의 낱말을 짝으로 갈아 끼운다")
s = "제21조는 등록 및 신고를 모두 요구한다."
ok("또는" in (MU.m_conj(s, arts(s)) or ""), "조문이 묶은 두 낱말의 접속사를 뒤집는다")
s = "제7조에 따른다."
ok("제707조" in (MU.m_citation(s, arts(s)) or ""), "없는 조문 번호로 바꾼다")
s = "제7조는 5년 이하의 징역에 처한다."
ok("8년" in (MU.m_quantity(s, arts(s)) or ""),
   f"조문의 수를 다른 수로 바꾼다 (얻은 값 {MU.m_quantity(s, arts(s))!r})")
ok("대법원" in MU.m_case("제7조에 따른다.", []), "없는 판례를 지어 넣는다")

print()
print("[안 심기] 관문이 판정할 자격이 없는 자리에는 심지 않는다")
s = "제3조에 따르면 이 법은 효력이 없다."
ok(MU.m_modality(s, arts(s)) is None,
   "조문에 서법 표현이 없으면 서법 돌연변이를 안 심는다")
ok(MU.m_bound(s, arts(s)) is None, "조문에 경계 표현이 없으면 안 심는다")
ok(MU.m_effect(s, arts(s)) is None, "조문에 법효과어가 없으면 안 심는다")
s = "제3조는 시험 및 검사를 정한다."
ok(MU.m_conj(s, arts(s)) is None,
   "조문이 그 두 낱말을 접속사로 안 묶으면 접속 돌연변이를 안 심는다")

print()
print("[한 바퀴] 심은 것을 관문이 실제로 잡는다")
문서 = make("제20조에 따라 행정청은 시정을 명할 수 있다. "
            "제12조는 해산일부터 3년 이내에 종결하여야 한다. "
            "제7조는 재산상 이익을 취득한 자를 5년 이하의 징역에 처한다.")
tally = MU.run(문서, CORPUS, want_miss=True)
심음 = sum(t["심음"] for t in tally.values())
잡음 = sum(t["잡음"] for t in tally.values())
ok(심음 >= 5, f"심을 자리를 찾았다 ({심음}개)")
ok(심음 == 잡음,
   f"심은 것을 하나도 안 놓쳤다 ({잡음}/{심음}) "
   f"놓친 것: {[(n, t['놓친것']) for n, t in tally.items() if t['놓친것']]}")
for 이름 in ("W001 서법", "W003 경계", "W005 용어치환", "L001 인용실재", "L004 판례"):
    ok(tally[이름]["잡음"] >= 1, f"{이름} 을 심어 잡았다")

print()
print("[깨끗한 문서] 안 건드리면 관문이 조용하다 (GREEN)")
doc = G.parse(next(문서.glob("*.md")))
vs, _, _ = G.check(doc, CORPUS)
ok(not [v for v in vs if v.severity == "hard"],
   f"원본은 hard 0건 (얻은 값 {[str(v) for v in vs if v.severity == 'hard']})")

print()
if fails:
    print(f"돌연변이: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("관문 증명: 심기 · 안 심기 · 잡기 · 원본 통과 -- RED/GREEN 통과")
