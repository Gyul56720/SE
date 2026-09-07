"""**낱말 하나가 결론을 바꾼다** -- 문언 관문 W001~W005 가 그것을 잡는가.

novel/wording.py 는 같은 뜻 다른 꼴을 세어 다양성을 밀지만, 법에서 문언은 바꿔 쓰면
안 된다. 여기서 검사하는 다섯 쌍은 전부 **낱말 하나 차이인데 결론이 갈리는** 것이다:

    명할 수 있다 / 명하여야 한다     재량 / 기속
    등록 및 신고 / 등록 또는 신고     요건 둘 / 요건 하나
    3년 이내 / 3년 이전               포함 / 불포함
    준용한다 / 적용한다               그대로 / 고쳐서
    재산상 이익 / 재물                배임 / 횡령

    python3 tests/test_law_wording.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from law import corpus as CP                                          # noqa: E402
from law import gate as G                                             # noqa: E402
from law import wording as WD                                         # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "law_corpus"
CORPUS = CP.load(FIXTURE)

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


SECTIONS = ("1. 왜 알아야 하는가", "2. 조문과 이론", "3. 핵심 법리", "4. 해석기법",
            "5. 실무상 흔한 오해", "6. 사례 적용 (학습용 창작 사례, 실제 판례 아님)",
            "7. 연습 사실관계", "8. 다음 주제와의 연결")


def doc(sentence: str, where: str = "2. 조문과 이론"):
    body = ['---', 'title: "검사용"', 'domain: "00_검사"', 'tags: "[검사]"',
            'key_principle: "검사"', 'source_statute: "가상시험법"', '---', '']
    for name in SECTIONS:
        body.append(f"## {name}")
        body.append((sentence if name == where else "가상의 내용.") + "\n")
    tmp = Path(tempfile.mkdtemp()) / "검사문서.md"
    tmp.write_text("\n".join(body), encoding="utf-8")
    return G.parse(tmp)


def rules(vs):
    return sorted({v.rule for v in vs})


print("[회귀] 조문 분리기가 본문 안의 참조에서 끊기지 않는다")
t22 = CORPUS.text("가상시험법", "22")
ok(t22 and "준용한다" in t22,
   f"제22조 본문이 '제12조를 준용한다' 까지 온전하다 (얻은 값 {t22!r})")
ok("청산 기간" in (CORPUS.text("가상시험법", "12") or ""),
   "참조에 덮이지 않고 진짜 제12조가 남아 있다")

print()
print("[W001 서법] 재량을 기속으로 바꾸면 처분의 성질이 바뀐다")
d = doc("제20조에 따라 행정청은 시정을 명하여야 한다.")
vs = WD.check(d, CORPUS)
ok("W001" in rules(vs) and vs[0].severity == "hard",
   f"조문은 '명할 수 있다'(재량)인데 '명하여야 한다'(기속) -> hard (얻은 값 {rules(vs)})")
ok("재량" in vs[0].detail and "기속" in vs[0].detail,
   f"무엇이 무엇으로 바뀌었는지 적는다 ({vs[0].detail})")
ok(not WD.check(doc("제20조에 따라 행정청은 시정을 명할 수 있다."), CORPUS),
   "조문대로 '명할 수 있다' 로 쓰면 통과")

print()
print("[W002 접속] 및 을 또는 으로 바꾸면 요건 둘이 하나로 준다")
vs = WD.check(doc("제21조는 등록 또는 신고를 요구한다."), CORPUS)
ok("W002" in rules(vs), f"조문은 '및'(결합)인데 '또는'(선택) -> hard (얻은 값 {rules(vs)})")
ok(not [v for v in WD.check(doc("제21조는 등록 및 신고를 모두 요구한다."), CORPUS)
        if v.rule == "W002"],
   "조문대로 '및' 로 쓰면 통과")

print()
print("[W003 경계] 이내 를 이전 으로 바꾸면 그 날이 안에 드는지가 바뀐다")
vs = WD.check(doc("제12조는 해산일부터 3년 이전에 종결할 것을 정한다."), CORPUS)
ok("W003" in rules(vs), f"조문은 '이내'(포함)인데 '이전'(불포함) (얻은 값 {rules(vs)})")
ok(not [v for v in WD.check(doc("제12조는 3년 이내에 종결하여야 한다고 정한다."), CORPUS)
        if v.rule == "W003"],
   "조문대로 '이내' 로 쓰면 통과")

print()
print("[W004 법효과어] 준용 을 적용 으로 바꾸면 다른 법이 된다")
vs = WD.check(doc("제22조는 청산에 관하여 제12조를 적용한다."), CORPUS)
ok(rules(vs) == ["W004"],
   f"준용 -> 적용은 W004 한 번만 잡는다 (얻은 값 {rules(vs)})")
ok(not [x for x in WD.PAIRS if set(x) == {"준용", "적용"}],
   "준용/적용은 PAIRS 에 없다 -- 두 곳에서 세면 같은 잘못이 점수에 두 번 들어간다")

print()
print("[W005 용어] 재산상 이익을 재물로 바꾸면 배임이 횡령이 된다")
vs = WD.check(doc("제7조는 재물을 취득한 자를 처벌한다."), CORPUS)
ok("W005" in rules(vs) and "재산상 이익" in vs[0].detail,
   f"조문은 '재산상 이익' 인데 '재물' 로 적었다 (얻은 값 {[v.detail for v in vs]})")
ok(not [v for v in WD.check(doc("제7조는 재산상 이익을 취득한 자를 처벌한다."), CORPUS)
        if v.rule == "W005"],
   "조문의 낱말 그대로 쓰면 통과")

print()
print("[W005 실무 목록] 짝이 늘어도 같은 자리에서 잡는다")
vs = WD.check(doc("제30조에 따라 청구를 기각한다."), CORPUS)
ok("W005" in rules(vs) and "각하" in vs[0].detail,
   f"조문은 '각하' 인데 '기각' 으로 적었다 -- 소송요건과 본안이 갈린다 "
   f"(얻은 값 {[v.detail for v in vs]})")
vs = WD.check(doc("제31조는 소명으로 족하다고 정한다."), CORPUS)
ok("W005" in rules(vs),
   f"조문은 '증명'(확신) 인데 '소명'(그럴듯함) 으로 적었다 (얻은 값 {rules(vs)})")
ok(len(WD.PAIRS) >= 100, f"짝 목록이 실무 수준으로 늘었다 (지금 {len(WD.PAIRS)}쌍)")

print()
print("[오탐 방지] 긴 낱말 안에 든 짧은 용어를 따로 세지 않는다")
ok(WD.terms_in("무과실 책임을 정한다") == {"무과실책임"},
   f"'무과실' 안의 '과실' 을 안 센다 (얻은 값 {WD.terms_in('무과실 책임을 정한다')})")
ok("기간" not in WD.terms_in("제척기간이 지났다"),
   "'제척기간' 안의 '기간' 을 안 센다")
ok("소유" not in WD.terms_in("소유권이전 등기를 마쳤다"),
   "'소유권이전' 안의 '소유' 를 안 센다")
ok(WD.terms_in("재산상 이익") == WD.terms_in("재산상이익"),
   "띄어쓰기가 달라도 같은 낱말로 본다")
ok(not WD.check(doc("제7조는 재산상이익을 취득한 자를 처벌한다."), CORPUS),
   "조문이 '재산상 이익' 이고 문서가 '재산상이익' 이면 통과 -- 띄어쓰기로 기각하지 않는다")

print()
print("[실측이 잡은 오탐] 진짜 문서를 돌려 보고 좁힌 것들")
vs = WD.check(doc("제20조 및 제21조 등의 조문에서 재량과 요건을 다룬다."), CORPUS)
ok(not [v for v in vs if v.rule == "W002"],
   f"조문 인용을 잇는 '및' 은 요건의 접속이 아니다 (얻은 값 {rules(vs)})")
vs = WD.check(doc("제20조와 제12조의 절차를 엄격히 검토해야 한다는 점에서 나온다."), CORPUS)
ok(not [v for v in vs if v.rule == "W001"],
   f"필자의 당위('검토해야 한다')는 조문의 서법이 아니다 (얻은 값 {rules(vs)})")
vs = WD.check(doc("제21조는 등록 또는 신고를 요구한다."), CORPUS)
ok([v.severity for v in vs if v.rule == "W002"] == ["soft"],
   "접속은 기각하지 않는다 -- 어느 요건 둘을 묶는지 문장 단위로는 못 짚는다")

print()
print("[과잉 기각 방지] 견줄 것이 없으면 판정하지 않는다")
ok(not WD.check(doc("제3조에 따르면 행정청은 무엇이든 할 수 있다."), CORPUS),
   "조문에 서법 표현이 아예 없으면 문서가 무엇을 써도 안 잡는다")
ok(not WD.check(doc("형법 제356조는 10년 이하의 징역에 처하여야 한다."), CORPUS),
   "원장이 안 담은 법령(형법)은 미검증 -- 기각하지 않는다")

print()
print("[절에 따른 무게] 조문·법리 절은 hard, 나머지는 soft")
vs = WD.check(doc("제20조에 따라 명하여야 한다.", where="5. 실무상 흔한 오해"), CORPUS)
ok([v.severity for v in vs] == ["soft"],
   f"오해 절에서는 soft (얻은 값 {[v.severity for v in vs]})")

print()
print("[근거 표시] 낱말이 어느 조문에 근거하는지 늘어놓는다")
rows = WD.trace(doc("제20조에 따라 행정청은 시정을 명하여야 한다."), CORPUS)
hit = [r for r in rows if r[2] and "제20조" in r[2][0]]
ok(hit and "서법:기속" in hit[0][4],
   f"'기속' 이 근거 없는 값으로 잡힌다 (얻은 값 {hit[0][4] if hit else None})")
rows = WD.trace(doc("제20조에 따라 행정청은 시정을 명할 수 있다."), CORPUS)
hit = [r for r in rows if r[2] and "제20조" in r[2][0]]
ok(hit and "서법:재량" in hit[0][3] and not hit[0][4],
   f"조문대로 쓰면 근거 있는 값에 들어간다 (얻은 값 {hit[0][3] if hit else None})")

print()
print("[배선] gate.py 가 W 관문을 같이 돌린다")
vs, _, _ = G.check(doc("제20조에 따라 행정청은 시정을 명하여야 한다."), CORPUS)
ok("W001" in {v.rule for v in vs}, "law/gate.py 의 CHECKS 에 실려 있다")

print()
if fails:
    print(f"문언: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("문언 관문 W001~W005: 서법 · 접속 · 경계 · 법효과어 · 용어 치환 -- RED/GREEN 통과")
