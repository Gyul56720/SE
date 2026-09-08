"""사안 -> 요건표 생성자. **관문을 모르는가**가 이 검사의 본체다.

`law/write.py` 와 같은 규율이다: 생성자에 심판을 실으면 원고가 사양서가 된다. 요건표에
심판(J001~J011)을 실으면 관문을 통과하는 요건표만 나오고 진짜 다툴 자리가 빠진다.

그리고 **네트워크를 안 탄다** -- 가짜 물음이를 주면 가짜로만 돈다.

    python3 tests/test_law_brief.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import brief as B                                            # noqa: E402
from law import corpus as CP                                          # noqa: E402
from law import issue as IS                                           # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "law_corpus"
CORPUS = CP.load(FIXTURE)
fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


print("[관문을 모른다] **생성자에 심판을 실으면 요건표가 사양서가 된다**")
# 제22조로 만든다 -- 제7조는 조문 제목이 '가상 위반행위' 라 조문 글이 검사 목록에 걸린다.
# 재는 것은 생성자가 **제 말로** 관문을 입에 올리는가이지, 조문에 그 낱말이 있는가가 아니다.
_p = B.prompt("원고가 피고에게 1천만원을 빌려주었다. 피고는 갚았다고 한다.", "민사",
              [("가상시험법", "22", CORPUS.text("가상시험법", "22"))])
샘 = [w for w in ("관문", "게이트", "위반", "기각", "심판", "뒤집기", "J001", "J005",
                  "issuegate", "도출", "derive") if w in _p]
ok(not 샘, f"프롬프트에 관문 낱말이 없다 (샌 것 {샘})")
ok("가상시험법 제22조" in _p and "이 밖의 조문은 쓰지 마십시오" in _p,
   "조문을 주고 그 밖은 쓰지 말라고 한다 -- 닫힌 책")
ok("전부" in _p and "재항변" in _p and "약해 보여도" in _p,
   "적힌 주장만 옮기지 말고 양쪽이 세울 수 있는 것을 전부 세우라고 한다")
ok("사람 이름은 쓰지 말고" in _p, "이름 대신 역할로 부르게 한다")

_src = (Path(__file__).resolve().parent.parent / "law" / "brief.py").read_text(encoding="utf-8")
ok("from law import gate" not in _src and "from law import issuegate" not in _src
   and "import law.gate" not in _src and "import law.issuegate" not in _src,
   "생성자는 관문을 임포트하지 않는다")

print()
print("[가짜 물음이] 네트워크 없이 요건표가 만들어지고, 그것으로 쟁점이 계산된다")
_답 = """```json
{
 "domain": "민사",
 "claim": "원고가 피고에게 대여금 1천만원의 반환을 구한다",
 "elements": [
  {"id": "합의", "text": "소비대차 합의", "stage": "권리근거", "statute": "가상시험법",
   "article": "7", "kind": "사실", "evidence": ["차용증"], "source": "사안 1문장"},
  {"id": "변제", "text": "변제", "stage": "권리소멸", "statute": "가상시험법",
   "article": "7의2", "kind": "사실", "evidence": ["영수증"], "source": "사안 2문장"},
  {"id": "시효", "text": "소멸시효 완성", "stage": "권리저지", "statute": "가상시험법",
   "article": "12", "kind": "법률", "canon": "문언", "invoked": true, "source": "가능한 항변"},
  {"id": "승인", "text": "채무 승인으로 중단", "stage": "권리저지", "statute": "가상시험법",
   "article": "12", "kind": "사실", "defeats": "시효", "source": "가능한 재항변"}
 ],
 "positions": {"합의": {"원고": true, "피고": true}, "변제": {"원고": false, "피고": true},
               "시효": {"원고": false, "피고": true}, "승인": {"원고": true, "피고": false}}
}
```"""
_부름 = []


def _가짜(text):
    _부름.append(text)
    return _답


case = B.brief("사안", "민사", ["가상시험법"], ["7", "7의2", "12"], corpus=CORPUS, ask=_가짜)
ok(len(_부름) == 1, f"한 번 부른다 (얻은 값 {len(_부름)})")
ok(isinstance(case, IS.Case) and len(case.elements) == 4,
   f"울타리를 벗기고 요건표로 읽는다 (얻은 값 {len(case.elements)}개 요건)")
ok(case.element("승인").defeats == "시효", "재항변의 과녁이 실린다")
ok(case.element("시효").source == "가능한 항변", "어디서 왔는지(source)가 남는다 -- 사람이 볼 것")
_쟁점 = {i.element for i in IS.derive(case)}
ok(_쟁점 == {"변제", "시효", "승인"}, f"그 요건표에서 쟁점이 계산된다 (얻은 값 {sorted(_쟁점)})")
_왕복 = json.loads(IS.dump(case))
ok(_왕복["elements"][3]["defeats"] == "시효", "dump 한 JSON 이 issue.py 가 읽는 꼴 그대로다")

print()
print("[말한다] 못 만들면 조용히 넘기지 않는다")
try:
    B.brief("사안", "민사", ["가상시험법"], ["999"], corpus=CORPUS, ask=_가짜)
    ok(False, "원장에 없는 조문인데 예외가 안 났다")
except RuntimeError as e:
    ok("원장에 하나도 없다" in str(e), "원장에 없는 조문은 부르기 전에 말한다")
try:
    B.parse("모델이 JSON 대신 설명을 했습니다.")
    ok(False, "JSON 이 없는데 예외가 안 났다")
except ValueError as e:
    ok("JSON 이 없다" in str(e), "JSON 이 없으면 말한다")
try:
    B.parse('{"domain": "민사", "elements": []}')
    ok(False, "positions 가 없는데 예외가 안 났다")
except ValueError as e:
    ok("positions" in str(e), "칸이 빠지면 말한다")

print()
if fails:
    print(f"요건표 생성: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("요건표 생성: 관문 무지 · 닫힌 책 · 양측 최대화 · 가짜 물음이 · 말한다 -- 통과")
