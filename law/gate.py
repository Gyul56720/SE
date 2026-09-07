"""법 학습자료의 기계 관문 -- LLM 을 쓰지 않는다. 위반 목록을 돌려준다.

novel/gate.py 와 같은 규약 위에 있다. 다른 것은 대조 대상이다. 소설은 원장을 지어내야
했지만 법은 조문 원문이 밖에 있다(law/corpus.py). 그래서 여기 관문들은 소설의 어떤
관문보다 판정이 확실하다 -- "인용한 조문이 실재하는가" 는 취향이 아니다.

판정은 셋으로 갈린다:

    hard  -- 확실한 위반. 문서를 기각한다.
    soft  -- 의심스럽다. 보고하되 기각하지 않는다.
    미검증 -- 원장이 그 법령을 안 담고 있어 **아직 아무도 안 봤다.** 통과가 아니다.

세 번째가 이 파일에서 제일 중요하다. 코퍼스가 비었는데 인용을 통과시키면 심판이 있다는
착각만 생기고 환각은 그대로 나간다. 그래서 검증한 인용 수와 못 한 인용 수를 보고서가
항상 같이 적는다.

관문 목록:

    L001  인용 실재성   조문이 원장에 있는가                    hard (원장 필요)
    L002  인용문 일치   따옴표로 옮긴 문장이 원문에 있는가       hard (원장 필요)
    L003  수량 일치     법정형·기간·금액이 그 조문의 것인가      hard (원장 필요)
    L004  판례 인용     사건번호를 지어냈는가                    hard
    L005  무근거 단정   조문 절에서 인용도 유보도 없이 단정하는가 soft
    L006  자기모순      한 문서가 같은 조문에 다른 법정형을 다는가 hard
    L007  구조          8절과 front-matter 규약을 지키는가       hard
    L008  창작 라벨     지어낸 사실관계에 그렇다고 적었는가      hard
    W001  서법          기속/재량/금지를 조문대로 썼는가         hard (원장 필요)
    W002  접속          및/또는을 조문대로 썼는가                hard (원장 필요)
    W003  경계          이상·이내/초과·이전을 조문대로 썼는가    hard (원장 필요)
    W004  법효과어      적용/준용/간주/추정을 조문대로 썼는가    hard (원장 필요)
    W005  용어 치환     조문의 낱말을 비슷한 다른 낱말로 바꿨는가 hard (원장 필요)

W 계열은 law/wording.py 에 따로 있다. novel/wording.py 를 뒤집은 것이다 -- 소설은 같은 뜻
다른 꼴을 세어 다양성을 밀지만, 법에서 문언은 바꿔 쓰면 안 된다. 낱말 하나가 결론을 바꾼다:
'명할 수 있다'(재량)를 '명하여야 한다'(기속)로, '및'을 '또는'으로, '준용'을 '적용'으로,
'재물'을 '재산상 이익'으로 바꾸면 전부 다른 법이 된다.

L004 가 hard 인 이유: 판례 원문 원장이 없다. 대조할 수 없는 인용은 통과시키면 그대로
환각이 되므로, 원장이 생기기 전까지는 **사건번호 인용 자체를 금지**한다. 판례를 언급하려면
'판례 확인 필요' 로 남기면 된다 -- 기존 문서들이 이미 그렇게 하고 있다.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import corpus as CP                                          # noqa: E402
from law import wording as WD                                         # noqa: E402

REQUIRED_META = ("title", "domain", "tags", "key_principle", "source_statute")

REQUIRED_SECTIONS = (
    "1. 왜 알아야 하는가",
    "2. 조문과 이론",
    "3. 핵심 법리",
    "4. 해석기법",
    "5. 실무상 흔한 오해",
    "6. 사례 적용",
    "7. 연습 사실관계",
    "8. 다음 주제와의 연결",
)

# 대법원 사건번호. '2020다12345', '99도1234' 꼴.
CASE_NO = re.compile(r"\b(19|20)?\d{2}\s*[다도누허카마므브즈나가]\s*\d{2,6}\b")
CASE_WORD = re.compile(r"대법원[^.\n]{0,40}?(선고|판결|결정)")

# 유보 표시. 이게 있으면 '원장 밖' 이라고 스스로 밝힌 것이다.
RESERVED = re.compile(r"명시되지\s*않(음|았)|확인\s*필요|추가\s*검토|알\s*수\s*없")

# 창작 사실관계 라벨. 실측한 17개 문서의 표기 편차를 모두 받는다.
CREATED_LABEL = re.compile(
    r"실제\s*판례\S{0,2}\s*아|가상의?\s|가상\s*사실|학습용")

# **작은따옴표는 빼 둔다.** 한국어에서 '…' 는 조문 인용이 아니라 강조로 훨씬 자주 쓰인다.
# 실측: 법이론서에서 L002 가 잡은 유일한 hard 가 "'진정한 청산 종결'을 전제로" 였다 --
# 필자가 만든 말에 강조를 준 것이지 조문을 옮긴 것이 아니었다.
QUOTED = re.compile(r"[\"“”「『]([^\"“”「」『』\n]{8,})[\"“”」』]")

# 법정형 표기. L006(자기모순)이 보는 자리.
PENALTY = re.compile(
    r"(?P<num>\d[\d,]*(?:[억만천백십][\d,]*)*)\s*(?P<unit>년|개월|일|억원|만원|원)\s*"
    r"이하의\s*(?P<kind>징역|금고|구류|벌금|과태료|과료)"
)

# 단정 어미. 인용 없이 이렇게 끝나면 근거가 어디인지 알 수 없다.
ASSERTIVE = re.compile(r"(합니다|입니다|됩니다|있습니다|한다|이다|된다)\s*[.。]?\s*$")

# 앞 문장을 이어받는 말. 이런 문장은 근거가 앞 문장에 있으므로 인용이 없어도 정상이다.
# 이걸 안 걸러서 L005 가 '따라서 ~합니다' 같은 정상 문장을 계속 보고했다(실측 10건 중 4건).
CONNECTIVE = re.compile(r"^(이는|이|그|따라서|그러므로|즉|다만|또한|한편|반면|"
                        r"그러나|여기서|본 조문|이러한|위와 같이|결국)")


@dataclass
class Violation:
    rule: str
    severity: str        # "hard" | "soft"
    where: str
    detail: str

    def __str__(self):
        return f"[{self.rule}/{self.severity}] {self.where}: {self.detail}"


@dataclass
class Doc:
    path: Path
    meta: dict
    sections: dict       # "2. 조문과 이론" -> 본문
    body: str

    @property
    def statute(self):
        return CP.normalize_statute(self.meta.get("source_statute") or None)

    def section(self, prefix: str) -> str:
        for name, text in self.sections.items():
            if name.startswith(prefix):
                return text
        return ""


def parse(path: Path) -> Doc:
    raw = path.read_text(encoding="utf-8")
    meta, body = {}, raw
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            for line in raw[3:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            body = raw[end + 4:]
    sections, cur = {}, None
    for line in body.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            sections[cur] = ""
        elif cur is not None:
            sections[cur] += line + "\n"
    return Doc(path, meta, sections, body)


def _sentences(text: str) -> list:
    """문장으로 자른다. **자는 corpus 에 한 벌만 둔다** -- 여기와 wording.py 가
    각자 들고 있으면 언젠가 갈라지고, 갈라지면 보고와 판정이 어긋난다."""
    return CP.sentences(text)


def _resolve(cit, doc: Doc):
    """인용의 소속 법령. 본문에 법령명이 없으면 front-matter 의 선언을 쓴다."""
    return cit.statute or doc.statute


# ---------------------------------------------------------------- 관문들

def check_citations(doc: Doc, corpus) -> tuple:
    """L001 -- 인용한 조문이 원장에 실재하는가. 환각 인용을 잡는 자리.

    원장이 그 법령을 안 담고 있으면 위반이 아니라 **미검증**으로 센다. 심판이 못 본 것을
    통과라고 부르지 않기 위해서다.

    법령명 없이 쓴 인용이 선언 법령에는 없고 원장의 다른 법령에는 있으면 soft 로 내린다.
    조문을 지어낸 것이 아니라 법령명을 안 밝힌 것일 수 있고, 그건 기각할 일이 아니다.
    """
    out, checked, unverified = [], 0, 0
    for name, text in doc.sections.items():
        for cit in CP.find_citations(text):
            statute = _resolve(cit, doc)
            if not corpus.covers(statute):
                unverified += 1
                continue
            checked += 1
            if corpus.has(statute, cit.article):
                continue
            elsewhere = corpus.statutes_with(cit.article)
            if elsewhere and not cit.statute:
                out.append(Violation(
                    "L001", "soft", f"{doc.path.name} · {name}",
                    f"{cit.raw} 이 선언 법령({statute})에 없다. "
                    f"{'/'.join(elsewhere)} 에는 있다 -- 법령명을 밝혀라"))
            else:
                out.append(Violation(
                    "L001", "hard", f"{doc.path.name} · {name}",
                    f"{statute} 에 {cit.raw} 이 없다 (원장 대조)"))
    return out, checked, unverified


def check_quotes(doc: Doc, corpus) -> list:
    """L002 -- 따옴표로 옮긴 조문이 원문에 실제로 그렇게 적혀 있는가.

    공백만 지우고 부분 문자열로 본다. 조사 하나 바꾼 것까지 잡자는 게 아니라, 조문에
    없는 문장을 조문인 것처럼 인용하는 것을 잡는다.
    """
    out = []
    for name, text in doc.sections.items():
        for sent in _sentences(text):
            cits = CP.find_citations(sent)
            if not cits:
                continue
            targets = []
            for c in cits:
                body = corpus.text(_resolve(c, doc), c.article)
                if body:
                    targets.append(re.sub(r"\s+", "", body))
            if not targets:
                continue
            for q in QUOTED.findall(sent):
                if CP.CITATION.search(q):      # 조문 번호를 부른 것뿐이면 인용이 아니다
                    continue
                flat = re.sub(r"\s+", "", q)
                if not any(flat in t for t in targets):
                    out.append(Violation(
                        "L002", "hard", f"{doc.path.name} · {name}",
                        f"조문에 없는 문장을 인용부호로 옮겼다: {q[:40]!r}"))
    return out


def check_quantities(doc: Doc, corpus) -> list:
    """L003 -- 법정형·기간·금액이 그 조문의 것인가.

    '10년 이하의 징역 또는 3천만원 이하의 벌금' 은 조문에 그대로 적힌 값이라 대조된다.
    표기('3천만원' / '1500만원')는 값으로 바꿔 비교하므로 표기 차이로 기각하지 않는다.

    조문 절·법리 절에서는 hard, 나머지 절에서는 soft 다. 사례 절의 숫자는 사실관계에서
    지어낸 금액일 수 있고(그건 창작 사례니 정상이다), 조문 절의 숫자는 조문에서 왔어야
    한다.
    """
    out = []
    for name, text in doc.sections.items():
        sev = "hard" if name.startswith(("2.", "3.")) else "soft"
        for sent in _sentences(text):
            cits = CP.find_citations(sent)
            if not cits:
                continue
            allowed, covered = set(), False
            for c in cits:
                statute = _resolve(c, doc)
                if corpus.has(statute, c.article):
                    covered = True
                    allowed |= corpus.quantities_of(statute, c.article)
                    # **준용된 조문의 수량도 이 조문의 수량이다.** "제22조에 따라 3년
                    # 이내" 에서 제22조가 "제12조를 준용한다" 뿐이면 3년은 제12조에
                    # 있다. 여기를 안 따라가면 맞게 쓴 수량을 없는 수량이라고 기각한다.
                    for _, borrowed in corpus.via(statute, c.article):
                        allowed |= {q.key() for q in CP.quantities(borrowed)}
            if not covered:
                continue
            nums = CP.quantities(sent)
            # **지어낸 사건의 수는 조문의 수가 아니다.**
            #
            # 실측: "청산인 갑은 3주 기간을 넘겨 **5주** 만에 등기하였다" 가 기각됐다.
            # 그런데 문서는 완전히 옳다 -- 3주는 제94조대로 적었고 5주는 지어낸 사건의
            # 사실이며, 바로 다음 문장이 "5주 만에 등기한 것은 법정 기간을 도과한
            # 것이다" 라고 제대로 결론짓는다.
            #
            # 이건 그냥 오탐이 아니다. **조문의 수를 안 벗어나는 사례는 쓸모없는
            # 사례**인데, 그것을 벌하면 다음 원고는 조문의 수만 되뇌는 사례를 쓴다.
            # 유보 문장을 벌해서 환각을 권하게 되는 것과 같은 꼴이다.
            #
            # 그래서 **창작 라벨이 붙은 블록에서는**, 조문의 수를 하나라도 맞게 썼으면
            # 나머지 수는 사실로 본다. W 계열이 "그 범주에서 하나라도 맞게 썼으면
            # 나머지는 일상 용법이다" 로 정한 것과 같은 원리다. 맞게 쓴 수가 하나도
            # 없으면 그대로 기각한다 -- "제94조는 5주간 내에 등기하여야 한다" 는
            # 사례 안에 있어도 조문을 잘못 옮긴 것이다.
            if CREATED_LABEL.search(text) and any(q.key() in allowed for q in nums):
                continue
            for q in nums:
                if q.key() not in allowed:
                    out.append(Violation(
                        "L003", sev, f"{doc.path.name} · {name}",
                        f"{q.raw} 이 인용한 조문("
                        f"{', '.join(c.raw for c in cits)})에 없는 수량이다"))
    return out


def check_case_citation(doc: Doc, corpus=None) -> list:
    """L004 -- 판례 사건번호를 지어냈는가. 원장이 없으므로 인용 자체를 금지한다.

    법률 LLM 의 1위 실패 모드가 없는 판례를 있는 것처럼 부르는 것이다. 대법원 판결문의
    공개 원장이 없어서 대조할 수 없는 동안은, 통과시키는 것보다 못 쓰게 하는 쪽이 맞다.
    '판례 확인 필요' 로 남기는 것은 막지 않는다 -- 그건 모른다고 밝힌 것이다.
    """
    out = []
    for name, text in doc.sections.items():
        for m in CASE_NO.finditer(text):
            out.append(Violation("L004", "hard", f"{doc.path.name} · {name}",
                                 f"대조할 수 없는 사건번호: {m.group(0)!r}"))
        for m in CASE_WORD.finditer(text):
            out.append(Violation("L004", "hard", f"{doc.path.name} · {name}",
                                 f"판례를 특정해 인용했다: {m.group(0)[:40]!r}"))
    return out


def check_ungrounded(doc: Doc, corpus=None) -> list:
    """L005 -- '조문과 이론' 절에서 인용도 유보도 없이 단정하는가. soft 다.

    이 절의 규약은 '제공된 조문 원문에 따르면' 으로 말하고, 원문 밖은 '명시되지 않음,
    학설/판례 확인 필요' 로 남기는 것이다. 둘 다 없는 단정문은 어디서 왔는지 알 수 없다.

    한국어 어미 검사는 정밀도가 100% 가 아니므로 기각하지 않고 보고만 한다. novel/gate.py
    가 soft 를 따로 둔 이유와 같다 -- 과잉 기각하는 심판은 맞는 답도 버린다.
    """
    out = []
    for sent in _sentences(doc.section("2.")):
        if len(sent) < 25 or not ASSERTIVE.search(sent):
            continue
        if CP.find_citations(sent) or RESERVED.search(sent) or CONNECTIVE.match(sent):
            continue
        out.append(Violation("L005", "soft", f"{doc.path.name} · 2. 조문과 이론",
                             f"근거 인용도 유보도 없는 단정: {sent[:45]}..."))
    return out


def check_self_contradiction(doc: Doc, corpus=None) -> list:
    """L006 -- 한 문서가 같은 조문에 서로 다른 법정형을 다는가. 원장 없이도 돈다.

    novel/gate.py 의 check_facts(V010, 같은 키가 다른 값으로 재선언되는 것)를 옮긴 것이다.
    소설에서 '설정 모순' 이던 자리가 법에서는 '앞에서는 10년이라 하고 뒤에서는 5년이라
    한다' 가 된다. 밖의 원장이 없어도 판정되므로 코퍼스가 비어도 이 관문은 살아 있다.
    """
    seen, out = {}, []
    for name, text in doc.sections.items():
        for sent in _sentences(text):
            cits = CP.find_citations(sent)
            if not cits:
                continue
            for m in PENALTY.finditer(CP.CITATION.sub(" ", sent)):
                val = CP.kor_number(m.group("num"))
                if val is None:
                    continue
                unit = m.group("unit")
                val *= {"억원": 10**8, "만원": 10**4}.get(unit, 1)
                cls = "기간" if unit in ("년", "개월", "일") else "금액"
                for c in cits:
                    key = (_resolve(c, doc), c.article, m.group("kind"), cls)
                    prev = seen.get(key)
                    if prev is None:
                        seen[key] = (val, m.group(0), name)
                    elif prev[0] != val:
                        out.append(Violation(
                            "L006", "hard", f"{doc.path.name} · {name}",
                            f"제{c.article}조의 {m.group('kind')}을 "
                            f"{prev[1]}({prev[2]})과 {m.group(0)} 둘로 적었다"))
    return out


def check_structure(doc: Doc, corpus=None) -> list:
    """L007 -- 8절 구조와 front-matter 규약. 기계가 보기 제일 쉬운 자리다."""
    out = []
    for key in REQUIRED_META:
        if not doc.meta.get(key):
            out.append(Violation("L007", "hard", doc.path.name,
                                 f"front-matter 에 {key} 가 없다"))
    names = list(doc.sections)
    for want in REQUIRED_SECTIONS:
        if not any(n.startswith(want) for n in names):
            out.append(Violation("L007", "hard", doc.path.name,
                                 f"'{want}' 절이 없다"))
    return out


def check_created_facts(doc: Doc, corpus=None) -> list:
    """L008 -- 지어낸 사실관계에 지어냈다고 적었는가.

    사례 절의 사실관계는 창작이다. 창작인 것은 문제가 아니고, **창작인지 아닌지 읽는
    사람이 구별할 수 없는 것**이 문제다. 절 제목에 라벨이 있어도 본문 블록마다 다시
    적게 한다 -- 옵시디언에서는 블록만 따로 잘려 나가고, 그때 제목은 따라가지 않는다.
    """
    out = []
    for prefix, sev in (("6.", "hard"), ("7.", "soft")):
        text = doc.section(prefix)
        if not text.strip():
            continue
        blocks = re.split(r"^###\s+", text, flags=re.M)[1:] or [text]
        for blk in blocks:
            head = blk.splitlines()[0].strip() if blk.strip() else "?"
            if not CREATED_LABEL.search(blk):
                out.append(Violation(
                    "L008", sev, f"{doc.path.name} · {prefix} {head}",
                    "창작 사실관계인데 그렇다는 표시가 블록 안에 없다"))
    return out


CHECKS = (check_citations, check_quotes, check_quantities, check_case_citation,
          check_ungrounded, check_self_contradiction, check_structure,
          check_created_facts, WD.check)


def check(doc: Doc, corpus) -> tuple:
    """(위반 목록, 검증된 인용 수, 미검증 인용 수)."""
    out, checked, unverified = check_citations(doc, corpus)
    for fn in CHECKS:
        if fn is check_citations:
            continue
        out.extend(fn(doc, corpus))
    return out, checked, unverified


def verdict(violations) -> tuple:
    """(통과 여부, 요약). hard 가 하나라도 있으면 기각한다."""
    hard = [v for v in violations if v.severity == "hard"]
    soft = [v for v in violations if v.severity == "soft"]
    if hard:
        return False, f"하드 위반 {len(hard)}건 (참고 soft {len(soft)}건)"
    if soft:
        return True, f"통과 -- 다만 soft {len(soft)}건"
    return True, "통과 -- 위반 없음"


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="법 학습자료 기계 관문")
    ap.add_argument("target", nargs="?", default="법이론서",
                    help="검사할 파일 또는 디렉터리")
    ap.add_argument("--corpus", default=str(CP.CORPUS_DIR), help="조문 원장 디렉터리")
    ap.add_argument("--rule", action="append", help="이 관문만 본다 (예: --rule L004)")
    ap.add_argument("-v", "--verbose", action="store_true", help="soft 도 전부 출력")
    args = ap.parse_args(argv)

    corpus = CP.load(args.corpus)
    target = Path(args.target)
    files = sorted(target.rglob("*.md")) if target.is_dir() else [target]
    files = [f for f in files if not f.name.lower().startswith("readme")]
    if not files:
        print(f"검사할 문서가 없다: {target}")
        return 1

    print(f"원장: {'비어 있음 -- 인용 대조 관문은 미검증으로 빠진다' if not corpus else ''}")
    for name, arts in sorted(corpus.articles.items()):
        print(f"  {name}: 조문 {len(arts)}개")

    total_hard = total_soft = total_checked = total_unverified = 0
    rejected = []
    for path in files:
        doc = parse(path)
        vs, checked, unverified = check(doc, corpus)
        if args.rule:
            vs = [v for v in vs if v.rule in args.rule]
        hard = [v for v in vs if v.severity == "hard"]
        soft = [v for v in vs if v.severity == "soft"]
        total_hard += len(hard)
        total_soft += len(soft)
        total_checked += checked
        total_unverified += unverified
        if hard:
            rejected.append(path)
        if hard or (soft and args.verbose):
            ok, summary = verdict(vs)
            print(f"\n{path}  -- {summary}")
            for v in hard + (soft if args.verbose else []):
                print(f"  {v}")

    print(f"\n{'=' * 60}")
    print(f"문서 {len(files)}개 · 기각 {len(rejected)}개 · "
          f"hard {total_hard} · soft {total_soft}")
    print(f"인용 대조: 검증 {total_checked}건 · 미검증 {total_unverified}건"
          + ("  <- 원장을 채우면 이만큼이 검사 대상이 된다" if total_unverified else ""))
    if not args.verbose and total_soft:
        print("soft 를 보려면 -v")
    return 1 if total_hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
