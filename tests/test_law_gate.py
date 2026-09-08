"""법 기계 관문이 **실제로 걸리는가**. 걸리는 것을 보여주지 못한 관문은 관문이 아니다.

이 저장소가 self_challenge.py 로 배운 것: 진단이 진짜인지 알려면 고장난 입력에서 실패
(RED)하고 멀쩡한 입력에서 통과(GREEN)하는 것을 둘 다 보여야 한다. 그래서 관문마다
'지어낸 문서' 와 '멀쩡한 문서' 를 짝으로 넣는다.

원장은 tests/fixtures/law_corpus/ 의 **가상 법령**을 쓴다. 실제 조문을 검사 고정값으로
쓰면 법 개정 때 검사가 빨개지고, 더 나쁘게는 옛 조문이 정답 자리에 남는다.

    python3 tests/test_law_gate.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import corpus as CP                                          # noqa: E402
from law import gate as G                                             # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "law_corpus"

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


def doc(sections: dict, meta: dict | None = None):
    """문서 하나를 임시 파일로 만든다. 관문은 파일에서 읽는 것을 전제한다."""
    m = {"title": "검사용", "domain": "00_검사", "tags": "[검사]",
         "key_principle": "검사", "source_statute": "가상시험법"}
    m.update(meta or {})
    body = "---\n" + "\n".join(f'{k}: "{v}"' for k, v in m.items() if v) + "\n---\n\n"
    # 빠진 절은 자동으로 채운다. 절 이름이 아니라 **번호 앞자리**로 맞춰야 한다 --
    # 제목에 괄호가 붙은 절("6. 사례 적용 (학습용 ...)")을 이름으로 맞추다가 같은 절이
    # 두 벌 생겼고, 관문이 그중 빈 쪽을 읽어 멀쩡한 문서를 기각했다(실측).
    out = dict(sections)
    for name in G.REQUIRED_SECTIONS:
        num = name.split(".")[0] + "."
        if not any(k.startswith(num) for k in out):
            out[name] = "내용.\n"
    for name in sorted(out, key=lambda k: int(k.split(".")[0])):
        body += f"## {name}\n{out[name]}\n"
    tmp = Path(tempfile.mkdtemp()) / "검사문서.md"
    tmp.write_text(body, encoding="utf-8")
    return G.parse(tmp)


CORPUS = CP.load(FIXTURE)
EMPTY = CP.Corpus()

print("[원장] 조문 원문을 조문 단위로 담는다")
ok(CORPUS.covers("가상시험법"), "코퍼스 파일 이름이 법령명이 된다")
ok(CORPUS.has("가상시험법", "7") and CORPUS.has("가상시험법", "7의2"),
   "제7조와 제7조의2 를 다른 조문으로 담는다")
ok(not CORPUS.covers("형법"), "안 넣은 법령은 담고 있지 않다고 답한다")
ok(CP.kor_number("1천500만") == 15_000_000 and CP.kor_number("3천만") == 30_000_000,
   "'1천500만' 과 '3천만' 을 값으로 바꾼다 (표기 차이로 기각하지 않기 위해)")
ok(CP.normalize_statute("도시정비법") == "도시 및 주거환경정비법",
   "줄여 쓴 법령명을 정식 명칭으로 편다")
cits = CP.find_citations("민법 제703조와 제704조. 이 법 제7조의2 를 본다")
ok([c.article for c in cits] == ["703", "704", "7의2"], "조문 인용을 순서대로 뽑는다")
ok(cits[0].statute == "민법" and cits[1].statute == "민법",
   "'민법 제703조와 제704조' 는 둘 다 민법에 맨다 (같은 문장 안에서 이어받는다)")
ok(cits[2].statute is None,
   "문장이 바뀌면 앞 법령명을 안 끌어오고, '이 법' 은 법령명으로 세지 않는다")

# **실측이 잡은 새는 자리.** "사단법인은 ... 제40조" 에서 '사단법' 을 법령명으로 잡아
# 그 인용이 위반도 통과도 아닌 '미검증' 으로 조용히 샜다. 민법 제40조를 대조할 수 있는데
# 안 한 것이다. 돌연변이 검사(law/mutate.py)가 없는 조문 번호를 심었는데 안 잡혀서 드러났다.
for 문장, 무엇 in (("사단법인은 사원의 결합체로서 제40조에 따른다", "사단법인"),
                 ("반면 재단법인은 제43조에 따라 출연이 필요하다", "재단법인")):
    ok(CP.find_citations(문장)[0].statute is None,
       f"'{무엇}' 에서 법령명을 만들어내지 않는다")
ok(CP.find_citations("형법 제129조부터 제132조까지")[0].statute == "형법",
   "진짜 법령명은 그대로 잡는다")
ok(CP.normalize_statute("헌법") == "대한민국헌법",
   "문서가 '헌법' 이라 쓰면 원장의 '대한민국헌법' 으로 잇는다")

print()
print("[L001] 없는 조문을 인용하면 기각한다 -- 환각 인용")
d = doc({"2. 조문과 이론": "제99조에 따르면 청산인은 지정된다.\n"})
vs, checked, unver = G.check_citations(d, CORPUS)
ok(any(v.rule == "L001" and v.severity == "hard" for v in vs),
   f"원장에 없는 제99조 -> hard (얻은 값 {[str(v) for v in vs]})")
ok(checked == 1 and unver == 0, f"검증 1건 · 미검증 0건 (얻은 값 {checked}/{unver})")

d = doc({"2. 조문과 이론": "제7조에 따르면 5년 이하의 징역에 처한다.\n"})
vs, checked, unver = G.check_citations(d, CORPUS)
ok(not vs and checked == 1, "실재하는 조문은 통과한다")

d = doc({"2. 조문과 이론": "제99조에 따르면 청산인은 지정된다.\n"})
vs, checked, unver = G.check_citations(d, EMPTY)
ok(not vs and unver == 1 and checked == 0,
   "원장이 비면 같은 인용이 기각이 아니라 **미검증**으로 센다")

print()
print("[L002] 조문에 없는 문장을 인용부호로 옮기면 기각한다")
d = doc({"2. 조문과 이론": '제7조는 "청산인은 즉시 사임하여야 한다"고 규정한다.\n'})
ok(any(v.rule == "L002" for v in G.check_quotes(d, CORPUS)), "지어낸 인용문 -> hard")
d = doc({"2. 조문과 이론": '제7조는 "5년 이하의 징역 또는 1천500만원 이하의 벌금"으로 정한다.\n'})
ok(not G.check_quotes(d, CORPUS), "원문에 있는 문구를 옮긴 것은 통과한다")

d = doc({"2. 조문과 이론": "제7조가 정하는 '가상의 임무 위배'는 넓게 읽힌다.\n"})
ok(not G.check_quotes(d, CORPUS),
   "작은따옴표는 강조다 -- 한국어에서 '…' 를 조문 인용으로 보면 멀쩡한 문장이 기각된다")

print()
print("[원장] 조 제목이 없는 조문도 잡는다 (헌법이 그렇게 생겼다)")
ok(CORPUS.has("가상시험법", "40") and CORPUS.has("가상시험법", "41"),
   "제목 없이 본문이 바로 오는 조문도 머리로 본다")
ok("제12조 및 제40조에 따른다" in (CORPUS.text("가상시험법", "42") or ""),
   "줄 첫머리에 와도 번호가 뒤로 가면 머리가 아니라 참조다")

print()
print("[L003] 그 조문에 없는 법정형·기간을 붙이면 기각한다 -- 오귀속")
d = doc({"2. 조문과 이론": "제7조는 7년 이하의 징역에 처하도록 규정하고 있습니다.\n"})
vs = G.check_quantities(d, CORPUS)
ok(any(v.rule == "L003" and v.severity == "hard" for v in vs),
   f"제7조는 5년인데 7년이라 적었다 -> hard (얻은 값 {[v.detail for v in vs]})")
d = doc({"2. 조문과 이론": "제7조는 1500만원 이하의 벌금에 처하도록 규정합니다.\n"})
ok(not G.check_quantities(d, CORPUS),
   "'1천500만원' 을 '1500만원' 으로 쓴 것은 같은 값이라 통과한다")
d = doc({"6. 사례 적용": "가상의 사실관계. 제7조 위반으로 2천만원의 손해가 났다.\n"})
ok(all(v.severity == "soft" for v in G.check_quantities(d, CORPUS)),
   "사례 절의 지어낸 금액은 기각하지 않고 보고만 한다")

print()
print("[L004] **원장이 있으면 대조하고, 없으면 금지한다** -- 둘을 섞지 않는다")
d = doc({"3. 핵심 법리": "대법원 2020다12345 판결은 이를 확인하였습니다.\n"})
vs = G.check_case_citation(d)
ok(any(v.rule == "L004" and v.severity == "hard" for v in vs),
   "판례 원장이 비어 있으면 사건번호 -> hard (대조할 수 없으니까)")
ok(any("원장이 비어" in v.detail for v in vs),
   f"왜 막았는지 적는다 -- 지어냈다는 뜻이 아니다 (얻은 값 {[v.detail[:30] for v in vs]})")
d = doc({"3. 핵심 법리": "구체적 범위는 조문 원문에 명시되지 않음, 학설/판례 확인 필요합니다.\n"})
ok(not G.check_case_citation(d), "'판례 확인 필요' 로 남긴 것은 막지 않는다")

# RED: 원장을 채웠는데도 실재하는 판례를 계속 막으면, 원장을 채운 보람이 없다.
_판례원장 = Path(tempfile.mkdtemp())
(_판례원장 / "2018다287522.txt").write_text(
    "# 2018다287522 · 대법원 · 20200521 · 건물인도\n# 받은 것\n\n[판시사항]\n...\n",
    encoding="utf-8")
_찬원장 = CP.Corpus()
_찬원장.cases = CP.load_cases(_판례원장)
d = doc({"3. 핵심 법리": "대법원 2018다287522 판결.\n"})
ok(not [v for v in G.check_case_citation(d, _찬원장) if "2018다287522" in v.detail],
   f"원장에 있는 사건번호는 통과한다 (얻은 값 {[v.detail for v in G.check_case_citation(d, _찬원장)]})")
d = doc({"3. 핵심 법리": "2099다99999 참조.\n"})
_vs = G.check_case_citation(d, _찬원장)
ok(any("원장에 없는" in v.detail for v in _vs),
   f"원장에 없는 사건번호는 기각한다 -- 지어낸 것으로 본다 (얻은 값 {[v.detail for v in _vs]})")

print()
print("[L006] 한 문서가 같은 조문에 다른 법정형을 달면 기각한다 -- 원장 없이도 돈다")
d = doc({"2. 조문과 이론": "제7조는 5년 이하의 징역에 처한다.\n",
         "5. 실무상 흔한 오해": "제7조는 3년 이하의 징역이라고 오해합니다.\n"})
ok(any(v.rule == "L006" for v in G.check_self_contradiction(d)),
   "5년과 3년 -> hard (원장 없이 문서 안에서만 판정)")
d = doc({"2. 조문과 이론": "제7조는 5년 이하의 징역 또는 1천500만원 이하의 벌금에 처한다.\n"})
ok(not G.check_self_contradiction(d),
   "징역과 벌금은 종류가 달라 모순이 아니다")

print()
print("[L007] 구조 규약")
d = doc({"2. 조문과 이론": "제7조.\n"}, meta={"source_statute": ""})
ok(any("source_statute" in v.detail for v in G.check_structure(d)),
   "source_statute 가 비면 hard -- 인용의 소속을 정할 수 없다")
d.sections.pop("7. 연습 사실관계", None)
ok(any("연습 사실관계" in v.detail for v in G.check_structure(d)), "절이 빠지면 hard")

print()
print("[L008] 지어낸 사실관계에 지어냈다고 적었는가")
d = doc({"6. 사례 적용 (학습용 창작 사례, 실제 판례 아님)":
         "### 사례 1\n**사실관계:** A 법인이 해산하였으나 청산인이 없었다.\n"})
ok(any(v.rule == "L008" and v.severity == "hard" for v in G.check_created_facts(d)),
   "절 제목에만 라벨이 있고 블록 안에는 없으면 hard")
d = doc({"6. 사례 적용 (학습용 창작 사례, 실제 판례 아님)":
         "### 사례 1\n**사실관계:** 가상의 A 법인이 해산하였다.\n"})
ok(not [v for v in G.check_created_facts(d) if v.severity == "hard"],
   "블록 안에 '가상의' 가 있으면 통과한다")

print()
print("[창작 사례의 수] **조문의 수를 안 벗어나는 사례는 쓸모없는 사례다**")
# 실측: "청산인 갑은 3주 기간을 넘겨 **5주** 만에 등기하였다" 가 기각됐다. 그런데
# 문서는 완전히 옳다 -- 3주는 제94조대로 적었고 5주는 지어낸 사건의 사실이며, 문장이
# "5주 만에 등기한 것은 법정 기간을 도과한 것이다" 라고 제대로 결론짓는다.
# 그것을 벌하면 다음 원고는 조문의 수만 되뇌는 사례를 쓴다.
_창작 = ("학습용으로 새로 창작한 가상의 사실관계이며 실제 판례가 아님.\n\n"
       "제12조는 3년 이내에 종결할 것을 요구하므로, 5년 만에 종결한 것은 도과다.\n")
ok(not G.check_quantities(doc({"6. 사례 적용": _창작}), CORPUS),
   "창작 블록에서 조문의 수(3년)를 맞게 썼으면 지어낸 수(5년)는 사실로 본다")
# **여기서 멈춰야 한다.** 맞게 쓴 수가 하나도 없으면 조문을 잘못 옮긴 것이다.
ok(len(G.check_quantities(doc({"6. 사례 적용":
        "학습용으로 새로 창작한 가상의 사실관계.\n\n제12조는 5년 이내에 종결하여야 한다.\n"}),
        CORPUS)) == 1,
   "사례 안이라도 '제12조는 5년 이내' 는 조문을 잘못 옮긴 것이라 그대로 잡는다")
# 창작 라벨이 없는 절은 지어낸 사실관계의 자리가 아니다.
ok(len(G.check_quantities(doc({"2. 조문과 이론":
        "제12조는 3년 이내여야 하는데 실무는 5년을 쓴다.\n"}), CORPUS)) == 1,
   "조문 절에서는 완화하지 않는다 -- 거기 숫자는 조문에서 왔어야 한다")

print("[2홉] **조문이 끌어다 쓰는 조문까지 한 홉 따라간다**")
# 민법 제724조는 청산인의 직무를 "제87조의 규정을 준용한다" 로만 정한다. 제724조
# 본문만 보면 청산인의 직무에 관한 서술은 영영 '견줄 값 없음' 이다 -- 안 보는 자리가
# 넓으면 어긋남 0 은 뜻이 없다. KoBLEX(EMNLP 2025)가 한국법에서 이것이 실제 병목임을
# 226문항으로 보여준다(1홉 55 · 2홉 125 · 3홉 46).
def via(a):
    return [n for n, _ in CORPUS.via("가상시험법", a)]


ok(via("22") == ["제12조"], f"준용을 따라간다 (얻은 값 {via('22')})")
ok(via("7의2") == ["제7조"], f"'제7조의 죄' 도 따라간다 -- 가중 구성요건의 본체다 "
   f"(얻은 값 {via('7의2')})")
ok(via("51") == ["전조(제50조)"], f"'전조' 는 원장 차례에서 바로 앞 조문이다 -- "
   f"제N조의2 가 있으므로 N-1 이 아니다 (얻은 값 {via('51')})")
# **넓히는 쪽이 곧 눈이 밝아지는 것은 아니다.** 단순 지시까지 따라가면 조문 하나로
# 법 전체가 딸려 오고, 그러면 무엇이든 조문 어딘가에 있으므로 어긋남이 영영 안 난다.
ok(via("42") == [], f"'제12조 및 제40조에 따른다' 는 단순 지시라 안 따라간다 "
   f"(얻은 값 {via('42')})")
ok(via("12") == [], f"끌어다 쓰는 것이 없으면 빈 목록 (얻은 값 {via('12')})")

# L003 도 같이 따라가야 한다. 안 그러면 **맞게 쓴 수량을 없는 수량이라고 기각한다.**
ok(not G.check_quantities(doc({"2. 조문과 이론": "제22조에 따라 청산은 3년 이내에 종결한다."}), CORPUS),
   "준용된 제12조의 '3년' 은 제22조를 인용해도 맞는 수량이다")
ok(len(G.check_quantities(doc({"2. 조문과 이론": "제22조에 따라 청산은 5년 이내에 종결한다."}), CORPUS)) == 1,
   "그래도 조문에 없는 '5년' 은 그대로 잡는다 -- 넓힌 것이지 눈을 감은 것이 아니다")

print("[회귀] 실제 문서 17개에서 관문이 돌고, 닫힌책 규율이 지켜져 있는가")
real = Path(__file__).resolve().parent.parent / "법이론서"
if real.is_dir():
    files = sorted(real.rglob("*.md"))
    case_hits, struct_hits, parsed = 0, 0, 0
    for f in files:
        rd = G.parse(f)
        parsed += 1
        case_hits += len(G.check_case_citation(rd))
        struct_hits += len(G.check_structure(rd))
    # **수를 못 박지 않는다.** 전에는 "문서 17개" 라 적었는데, 민사소송법 네 편이
    # 들어오자 그 자리에서 깨졌다 -- 원고가 늘어난 것은 좋은 일인데 자가 그것을
    # 실패로 셌다. 여기서 보려는 것은 "진짜 문서 위에서 관문이 돌았는가" 이지
    # 문서가 몇 개인가가 아니다. 0 이면 이 절 전체가 헛돈 것이므로 그것만 막는다.
    ok(parsed == len(files) and parsed >= 17,
       f"법이론서 문서를 하나도 안 빠뜨리고 읽는다 (읽은 값 {parsed} · 파일 {len(files)})")
    ok(case_hits == 0,
       f"지어낸 판례 인용 0건 -- 조문 안에서만 말하는 규율이 지켜졌다 (얻은 값 {case_hits})")
    ok(struct_hits == 0, f"8절·front-matter 규약 위반 0건 (얻은 값 {struct_hits})")
else:
    print("  건너뜀 법이론서/ 가 없다")

print()
if fails:
    print(f"법 관문: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("법 관문 L001~L008: 지어낸 인용·오귀속·자기모순·창작 라벨 -- RED/GREEN 통과")
