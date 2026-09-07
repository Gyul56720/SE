"""생성자 -- **관문을 모르는가**가 이 검사의 본체다.

이 저장소는 같은 자리에서 두 번 데었다.

  · `novel/gate.py`      관문을 나중에 붙였더니 원고가 통과하려고 균질해졌다
  · `mathdrift/spread.py` 발산 프롬프트에 심판을 실었더니 20개 중 20개가 "없음" 이
    됐고, 더 나쁘게는 발산이 사양서가 됐다

그래서 프롬프트에 관문 낱말이 실리는지를 **닫힌 목록으로** 검사한다. 다시 새어
들어가면 그 자리에서 걸린다. 그리고 **네트워크를 안 탄다** -- 가짜 물음이를 주면
가짜로만 돈다(진짜 API 로 새면 검사가 쿼터를 먹고, 키 없는 기계에서는 빨간불이 된다).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from law import corpus as CP                                          # noqa: E402
from law import gate as G                                             # noqa: E402
from law import write as WR                                           # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "law_corpus"
CORPUS = CP.load(FIXTURE)
fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


P = WR.prompt("가상시험법", "청산 기간의 준용",
              WR.articles("가상시험법", ["22"], CORPUS), CORPUS)

print("[관문을 모른다] **생성자에 심판을 실으면 원고가 사양서가 된다**")
# 닫힌 목록이라야 기계가 가른다. 뜻으로 재면 언젠가 샌다.
샘 = [w for w in ("관문", "게이트", "위반", "기각", "심판", "돌연변이",
                 "L001", "L004", "W001", "W004", "hard", "soft")
      if w in P]
ok(not 샘, f"프롬프트에 관문 낱말이 없다 (샌 것 {샘})")

print()
print("[재료를 준다] **원장에서 꺼낸 원문이 실제로 실린다**")
ok("제12조를 준용한다" in P, "인용한 조문의 원문이 프롬프트에 있다")
# 조문은 자기 안에 다 적지 않는다 -- 제22조만 주면 '3년' 이 어디에도 없다.
ok("3년 이내에 종결하여야 한다" in P,
   "**준용된 조문도 같이 준다** -- 안 주면 모델이 기억에서 꺼내 온다")
ok("지어내지 말고 모른다고 적으십시오" in P, "모르는 것은 모른다고 적으라고 시킨다")
ok(all(f"## {s}" in P for s in WR.SECTIONS), "여덟 절을 이름 그대로 시킨다")

print()
print("[없는 조문] **조용히 빼지 않는다**")
# 빼고 쓰면 모델이 그 조문을 기억에서 꺼내 오고, 그 문서는 원장에 없는 것을 근거로
# 삼은 채 관문을 통과한다 -- 대조할 수 없는 것이 대조된 척하는 자리다.
try:
    WR.articles("가상시험법", ["9999"], CORPUS)
    ok(False, "원장에 없는 조문을 달라고 하면 멈춘다")
except SystemExit as e:
    ok("9999" in str(e) and "fetch" in str(e),
       f"원장에 없는 조문이면 멈추고 무엇을 받으라고 말한다 ({str(e)[:40]}...)")

print()
print("[울타리] 모델이 씌운 코드 블록을 벗긴다")
ok(WR.clean("```markdown\n---\ntitle: \"가\"\n---\n본문\n```") == '---\ntitle: "가"\n---\n본문\n',
   "front-matter 의 --- 를 울타리로 오해하지 않는다")
ok(WR.clean("  본문  ") == "본문\n", "울타리가 없으면 그대로 둔다")

print()
print("[배선] **가짜 물음이를 주면 네트워크를 안 탄다**")
_문서 = ('---\ntitle: "청산 기간의 준용"\ndomain: 00_검사\ntags: [법이론서]\n'
        'key_principle: "청산은 3년 이내에 종결하여야 한다."\n'
        'source_statute: "가상시험법"\n---\n\n# 청산 기간의 준용\n\n'
        + "".join(f"## {s}\n제22조에 따라 청산은 3년 이내에 종결하여야 한다.\n\n"
                  for s in WR.SECTIONS))
_본 = []
_path = WR.write("가상시험법", "청산 기간의 준용", ["22"], CORPUS,
                 ask=lambda t: (_본.append(t), "```markdown\n" + _문서 + "\n```")[1],
                 out=Path(tempfile.mkdtemp()))
ok(len(_본) == 1 and "제12조를 준용한다" in _본[0], "받은 프롬프트가 그대로 나간다")
_doc = G.parse(_path)
ok(not G.check_structure(_doc),
   f"쓴 것이 8절·front-matter 규약을 지킨다 (얻은 값 {[str(v) for v in G.check_structure(_doc)]})")

print()
print("[심판은 여기 없다] 생성자는 관문을 임포트하지 않는다")
_src = (ROOT / "law" / "write.py").read_text(encoding="utf-8")
ok("from law import gate" not in _src and "import law.gate" not in _src,
   "law/write.py 가 gate 를 임포트하지 않는다 -- 임포트하면 언젠가 프롬프트로 샌다")

print()
if fails:
    print(f"생성자: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("생성자: 관문 무지 · 재료 · 2홉 · 없는 조문 · 울타리 · 배선 -- RED/GREEN 통과")
