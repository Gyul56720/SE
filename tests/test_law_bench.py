"""판결문 대조 자 -- **판례 하나가 곧 정답지다.** 갈라야 재고, 못 가르면 그렇다고 말한다.

    python3 tests/test_law_bench.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import bench as B                                            # noqa: E402
from law import corpus as CP                                          # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "law_corpus"
CORPUS = CP.load(FIXTURE)
fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


# fetch.py 가 저장하는 꼴 그대로. 조문은 가상시험법 -- 실제 법령이 아니다.
판례 = """# 2020다1111 · 대법원 · 20210101 · 대여금
# 받은 것

[판시사항]
소비대차에서 변제 항변과 소멸시효 항변의 판단 순서

[판결요지]
변제가 인정되면 시효는 볼 것이 없다.

[참조조문]
가상시험법 제7조, 제7조의2, 제12조

[판례내용]
【주 문】
원고의 청구를 기각한다. 소송비용은 원고가 부담한다.

【이 유】
1. 기초사실
원고는 2015. 3. 1. 피고에게 1천만 원을 빌려주었다. 피고는 2016. 3. 1. 이를 갚았다고 주장한다.
2. 당사자의 주장
원고는 대여금의 반환을 구하고, 피고는 변제하였고 설령 아니더라도 시효가 완성되었다고 다툰다.
3. 판단
가. 변제 항변에 관하여
영수증의 기재에 비추어 피고가 2016. 3. 1. 변제한 사실이 인정된다.
나. 소멸시효 항변에 관하여
변제로 채권이 소멸한 이상 더 나아가 판단할 필요가 없다.
"""

print("[가르기] 판례 파일을 판시사항·주문·이유로, 이유를 사실관계·판단으로 가른다")
sec = B.split(판례)
ok(sec["참조조문"].startswith("가상시험법") and "기각한다" in sec["주문"] and "기초사실" in sec["이유"],
   f"[참조조문]·【주문】·【이유】를 잡는다 (얻은 값 주문={sec['주문'][:12]!r})")
facts, judgment, 갈림 = B.facts_of(sec["이유"])
ok(갈림 and "기초사실" in facts and "판단" in judgment and "영수증" not in facts,
   "이유를 '판단' 머리에서 가른다 -- 판단 절이 사실관계로 새면 정답이 입력에 섞인다")
_, _, 못 = B.facts_of("아무 머리도 없는 이유 본문이다.")
ok(not 못, "판단 머리가 없으면 못 갈랐다고 답한다 -- 반쯤 가른 채 재지 않는다")

print()
print("[주문] 글자로만 결론을 읽는다")
for 글, 답 in (("피고는 원고에게 1천만 원을 지급하라.", "인용"),
               ("원고의 청구를 기각한다.", "기각"),
               ("이 사건 소를 각하한다.", "각하"),
               ("1. 피고는 원고에게 3백만 원을 지급하라. 2. 원고의 나머지 청구를 기각한다.", "일부인용"),
               ("항소를 기각한다.", "기각")):
    ok(B.verdict_of(글) == 답, f"{글[:22]!r} -> {답} (얻은 값 {B.verdict_of(글)})")

print()
print("[참조조문] 판결문이 스스로 어느 조문이 문제인지 말한다")
st, nums = B.refs_of("가상시험법 제7조, 제7조의2, 제12조")
ok(st == ["가상시험법"] and nums == ["7", "7의2", "12"], f"법령·조 번호를 뽑는다 (얻은 값 {st} {nums})")

print()
print("[관문을 모른다] 정답을 뽑는 프롬프트에 심판을 실으면 정답이 심판에 맞춰진다")
_p = B.points_prompt("3. 판단 ...")
샘 = [w for w in ("관문", "게이트", "위반", "기각", "심판", "뒤집기", "J001", "도출", "derive") if w in _p]
ok(not 샘, f"쟁점 목록 프롬프트에 관문 낱말이 없다 (샌 것 {샘})")
_src = (Path(__file__).resolve().parent.parent / "law" / "bench.py").read_text(encoding="utf-8")
ok("from law import gate" not in _src and "from law import issuegate" not in _src,
   "자는 관문을 임포트하지 않는다 -- 자와 심판은 다른 물건이다")

print()
print("[끝까지] 가짜 물음이로 한 건을 재고 두 수가 나온다")
요건표 = """{"domain": "민사", "claim": "대여금", "elements": [
 {"id": "합의", "text": "소비대차 합의", "stage": "권리근거", "statute": "가상시험법", "article": "7", "kind": "사실"},
 {"id": "변제", "text": "변제", "stage": "권리소멸", "statute": "가상시험법", "article": "7의2", "kind": "사실"},
 {"id": "시효", "text": "소멸시효 완성", "stage": "권리저지", "statute": "가상시험법", "article": "12", "kind": "법률", "invoked": true}],
 "positions": {"합의": {"원고": true, "피고": true}, "변제": {"원고": false, "피고": true},
               "시효": {"원고": false, "피고": true}}}"""
쟁점목록 = "- 변제이(가) 인정되는가\n- 소멸시효 완성이(가) 인정되는가\n- 지연손해금 기산일이(가) 인정되는가"


def _가짜(prompt):
    return 쟁점목록 if "법원이" in prompt else 요건표


_d = Path(tempfile.mkdtemp())
_f = _d / "2020다1111.txt"
_f.write_text(판례, encoding="utf-8")
row = B.bench_one(_f, _가짜, CORPUS)
ok(row["갈림"] and row["주문"] == "기각", f"갈리고 주문을 읽었다 (얻은 값 {row['주문']})")
ok(row["재현율"] is not None and abs(row["재현율"] - 2 / 3) < 0.01,
   f"법원 쟁점 3개 중 2개를 짚었다 -> 재현율 2/3 (얻은 값 {row['재현율']})")
ok(row["결론일치"] is True, f"주문 기각 = 파이프라인 기각 (얻은 값 결론 {row.get('결론')})")
못짚음 = [p for p, m, _ in row["쟁점"] if m is None]
ok(못짚음 == ["지연손해금 기산일이(가) 인정되는가"],
   f"못 짚은 쟁점이 무엇인지 남는다 -- 그것이 다음에 고칠 자리다 (얻은 값 {못짚음})")

_g = _d / "못가름.txt"
_g.write_text(판례.replace("3. 판단", "3. 결론"), encoding="utf-8")
row2 = B.bench_one(_g, _가짜, CORPUS)
ok(row2.get("못가름") and row2["재현율"] is None,
   f"못 가른 건은 점수를 안 낸다 (얻은 값 {row2.get('못가름')})")
_r = B.report([row, row2])
ok("잰 것 1건" in _r and "못 가른 것 1건" in _r and "67%" in _r,
   f"보고서가 잰 것과 못 가른 것을 갈라 적는다 (얻은 값 {_r.splitlines()[0]})")

print()
if fails:
    print(f"판결문 대조: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("판결문 대조: 가르기 · 주문 · 참조조문 · 관문 무지 · 끝까지 -- 통과")
