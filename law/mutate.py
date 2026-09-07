"""**관문이 진짜 잡는가** -- 낱말 하나를 일부러 틀리게 심고 잡히는지 본다.

실측 2026-09-07. 조문 원장을 채우고 법이론서 17개를 돌리니 어긋남이 0이었다. 좋은
소식처럼 보이지만 **그것만으로는 아무것도 증명하지 못한다.** 관문이 잘 만들어져서 0일
수도 있고, 아무것도 못 잡는 관문이라서 0일 수도 있다. 둘을 가르는 것이 이 파일이다.

`self_challenge.py` 가 이 저장소에 정한 규율 그대로다:

    진단이 옳다는 증거는 말이 아니라 두 번의 실행 결과다.
    RED   -- 고장난 입력에서 반드시 위반을 보고해야 한다.
    GREEN -- 멀쩡한 입력에서 반드시 통과해야 한다.

어긋남 0 은 GREEN 이다. 이 파일이 RED 를 만든다 -- **진짜 문서에** 낱말 하나를 바꿔
심고, 관문이 그것을 잡는지 센다.

심는 자리는 아무 데나가 아니다. **관문이 판정할 자격이 있는 자리에만 심는다.** 조문에
그 범주가 아예 없는 자리에 심어 놓고 "못 잡았다" 고 하는 것은 관문을 모함하는 것이다.
그래서 돌연변이마다 심을 수 있는 자리를 먼저 찾고, 심은 수와 잡은 수를 같이 적는다.

    python3 law/mutate.py 법이론서              # 종류별로 몇 개 심어 몇 개 잡았나
    python3 law/mutate.py 법이론서 --miss       # 놓친 것을 문장까지 보여준다

놓친 것이 있으면 그 자리가 다음에 고칠 곳이다. 놓친 것이 없으면 그때 비로소
"어긋남 0" 이 문서가 깨끗하다는 뜻이 된다.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import corpus as CP                                          # noqa: E402
from law import gate as GT                                            # noqa: E402
from law import wording as WD                                         # noqa: E402

# 심을 자리를 찾을 때는 조문 절·법리 절만 본다. 거기가 hard 판정 구역이다.
HARD_SECTIONS = ("2.", "3.")

# **반쪽짜리 돌연변이를 심지 않는다.**
#
# 실측(법이론서 17개, 186개 심어 152개 잡음)에서 놓친 34개를 뜯어보니 대부분이 심는
# 방식의 문제였다. 한 문장에 같은 꼴이 여럿일 때 첫 번째만 바꾸면(`count=1`) 나머지가
# 그대로 남는다:
#
#     원문   5년 이하의 징역 또는 1천500만원 이하의 벌금
#     반쪽   5년 초과의 징역 또는 1천500만원 이하의 벌금   <- '포함' 이 아직 남았다
#
# 그러면 문서가 조문의 값을 여전히 말하고 있으므로 관문이 넘긴다(부분 일치 규칙). 그건
# 관문이 눈이 없는 것이 아니라 **결함이 애매하게 심긴 것**이다. 문장 안의 같은 꼴은
# 전부 바꾼다 -- 그래야 "이 문장은 조문과 어긋난다" 가 분명해진다.


def _sentences(text):
    return WD._sentences(text)


def _cited(sent, doc, corpus):
    """이 문장이 부른 조문들의 (표기, 원문). 원장에 없는 것은 빠진다."""
    return WD._targets(sent, doc, corpus)


# ---------------------------------------------------------------- 돌연변이

def m_modality(sent, arts):
    """W001 -- 조문이 재량이면 문서를 기속으로, 기속이면 재량으로 바꾼다."""
    for _, body in arts:
        kinds = WD.bucket(body).get("W001", set())
        if "재량" in kinds and re.search(r"할\s*수\s*있", sent):
            return re.sub(r"할\s*수\s*있(다|습니다|으며)", "하여야 한다", sent)
        if "기속" in kinds and re.search(r"하여야\s*(한다|합니다)", sent):
            return re.sub(r"하여야\s*(한다|합니다)", "할 수 있다", sent)
    return None


def m_bound(sent, arts):
    """W003 -- 조문이 '이내' 면 문서를 '초과' 로."""
    for _, body in arts:
        kinds = WD.bucket(body).get("W003", set())
        if "포함" in kinds and re.search(r"이내|이하", sent):
            return re.sub(r"이내|이하", "초과", sent)
        if "불포함" in kinds and re.search(r"초과|미만", sent):
            return re.sub(r"초과|미만", "이내", sent)
    return None


def m_effect(sent, arts):
    """W004 -- 조문이 '준용' 이면 문서를 '적용' 으로, '추정' 이면 '간주' 로."""
    for _, body in arts:
        kinds = WD.bucket(body).get("W004", set())
        if "준용" in kinds and "준용" in sent:
            return sent.replace("준용", "적용")
        if "추정" in kinds and "추정" in sent:
            return sent.replace("추정", "간주")
    return None


def m_term(sent, arts):
    """W005 -- 조문에 있는 낱말을 바꿔 쓰면 안 되는 짝으로 갈아 끼운다."""
    for _, body in arts:
        seen = WD.terms_in(body)
        for a, b in WD.PAIRS:
            for used, other in ((a, b), (b, a)):
                if WD._flat(used) in seen and used in sent \
                        and WD._flat(other) not in seen:
                    return sent.replace(used, other)
    return None


def m_conj(sent, arts):
    """W002 -- 조문이 두 낱말을 묶은 접속사를 문서에서 뒤집는다."""
    for _, body in arts:
        flat = WD._flat(body)
        for m in WD._CONJ_PAIR.finditer(sent):
            x, conj, y = m.group(1), m.group(2), m.group(3)
            for fx in WD._stems(WD._flat(x)):
                for fy in WD._stems(WD._flat(y)):
                    if re.search(re.escape(fx) + r"(및|또는|이나|와|과)"
                                 + re.escape(fy), flat):
                        flip = "또는" if WD._CONJ_KIND[conj] == "결합" else "및"
                        return sent[:m.start(2)] + flip + sent[m.end(2):]
    return None


def m_citation(sent, arts, doc=None, corpus=None):
    """L001 -- 조문 번호를 **원장에 정말 없는** 것으로 바꾼다. 환각 인용을 흉내 낸다.

    처음에는 무턱대고 +700 을 했다. 그러면 민법(제1192조까지)처럼 조문이 많은 법령에서는
    바꾼 번호가 **실재해서** 환각이 아니게 된다 -- 실측에서 61개 중 22개를 그래서 놓쳤다.
    원장에 없는 번호를 찾을 때까지 올린다.
    """
    m = CP.CITATION.search(sent)
    if not m:
        return None
    statute = None
    for c in CP.find_citations(sent):
        statute = c.statute or (doc.statute if doc is not None else None)
        break
    n = int(m.group("jo"))
    for step in (700, 1700, 3700, 7700, 9700):
        cand = n + step
        if corpus is None or not corpus.has(statute, str(cand)):
            return sent[:m.start()] + f"제{cand}조" + sent[m.end():]
    return None


def m_quantity(sent, arts):
    """L003 -- 조문에 적힌 수를 다른 수로 바꾼다."""
    for _, body in arts:
        for q in CP.quantities(body):
            if q.raw in sent:
                head = re.match(r"\d[\d,]*", q.raw)
                if not head:
                    continue
                bad = str(int(head.group(0).replace(",", "")) + 3)
                return sent.replace(q.raw, bad + q.raw[head.end():], 1)
    return None


def m_case(sent, arts):
    """L004 -- 없는 판례를 지어 넣는다."""
    return sent.rstrip(".") + " (대법원 2019다54321 판결 참조)."


MUTATIONS = (
    ("W001 서법", m_modality, "W001"),
    ("W002 접속", m_conj, "W002"),
    ("W003 경계", m_bound, "W003"),
    ("W004 법효과어", m_effect, "W004"),
    ("W005 용어치환", m_term, "W005"),
    ("L001 인용실재", m_citation, "L001"),
    ("L003 수량", m_quantity, "L003"),
    ("L004 판례", m_case, "L004"),
)


# ---------------------------------------------------------------- 돌리기

def _rewrite(path: Path, old: str, new: str) -> Path:
    """문장 하나만 갈아 끼운 사본. 원본은 건드리지 않는다.

    **줄 단위로 바꾼다.** 처음에는 파일 전체를 한 줄로 뭉개고 바꿨는데, 그러면 `## 절`
    머리가 사라져 문서가 통째로 빈 문서가 된다. 그 사본에는 인용도 절도 없으니 관문이
    아무것도 안 잡고, 결과는 "심은 13개를 하나도 못 잡았다" 로 나왔다 -- **관문이 아니라
    재는 자가 고장난 것이었다.** 자를 먼저 의심해야 한다는 것이 이 저장소의 규율이다.

    문장이 여러 줄에 걸쳐 있으면 바꾸지 않고 건너뛴다(심은 수에서도 빠진다).
    """
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, line in enumerate(lines):
        flat = re.sub(r"[ \t]+", " ", line.rstrip("\n"))
        if old not in flat:
            continue
        lines[i] = flat.replace(old, new, 1) + ("\n" if line.endswith("\n") else "")
        tmp = Path(tempfile.mkdtemp()) / path.name
        tmp.write_text("".join(lines), encoding="utf-8")
        return tmp
    return None                               # 줄바꿈이 낀 문장은 건너뛴다


def run(target, corpus, want_miss: bool = False) -> dict:
    """문서마다 돌연변이를 심고 잡히는지 센다."""
    t = Path(target)
    files = sorted(t.rglob("*.md")) if t.is_dir() else [t]
    files = [f for f in files if not f.name.lower().startswith("readme")]
    tally = {name: {"심음": 0, "잡음": 0, "놓친것": []} for name, _, _ in MUTATIONS}

    for path in files:
        doc = GT.parse(path)
        for sec, text in doc.sections.items():
            if not sec.startswith(HARD_SECTIONS):
                continue
            for sent in _sentences(text):
                arts = _cited(sent, doc, corpus)
                if not arts or WD._MISCONCEPTION.search(sent):
                    continue
                for name, make, rule in MUTATIONS:
                    bad = (make(sent, arts, doc, corpus)
                           if make is m_citation else make(sent, arts))
                    if not bad or bad == sent:
                        continue
                    tmp = _rewrite(path, sent, bad)
                    if tmp is None:
                        continue
                    tally[name]["심음"] += 1
                    vs, _, _ = GT.check(GT.parse(tmp), corpus)
                    if any(v.rule == rule for v in vs):
                        tally[name]["잡음"] += 1
                    elif want_miss:
                        tally[name]["놓친것"].append((path.name, sec, bad[:100]))
    return tally


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="관문이 진짜 잡는지 -- 낱말 하나를 틀리게 심어 본다")
    ap.add_argument("target", nargs="?", default="법이론서")
    ap.add_argument("--corpus", default=str(CP.CORPUS_DIR))
    ap.add_argument("--miss", action="store_true", help="놓친 것을 문장까지 보여준다")
    a = ap.parse_args(argv)

    if not Path(a.target).exists():
        print(f"그런 경로가 없다: {a.target}\n"
              f"(옵션은 띄어 쓴다 -- `법이론서 --miss`)", file=sys.stderr)
        return 2
    corpus = CP.load(a.corpus)
    if not corpus:
        print("원장이 비어 있다. law/fetch.py 로 조문을 먼저 받아라.", file=sys.stderr)
        return 2

    tally = run(a.target, corpus, a.miss)
    print(f"{'돌연변이':<16}{'심음':>6}{'잡음':>6}{'놓침':>6}")
    total_p = total_c = 0
    for name, _, _ in MUTATIONS:
        t = tally[name]
        total_p += t["심음"]
        total_c += t["잡음"]
        print(f"{name:<16}{t['심음']:>6}{t['잡음']:>6}{t['심음'] - t['잡음']:>6}")
    print(f"{'합계':<16}{total_p:>6}{total_c:>6}{total_p - total_c:>6}")

    blind = [n for n, _, _ in MUTATIONS
             if tally[n]["심음"] and tally[n]["잡음"] == 0]
    none = [n for n, _, _ in MUTATIONS if not tally[n]["심음"]]
    if blind:
        print(f"\n**하나도 못 잡은 것: {', '.join(blind)}** -- 그 관문은 지금 눈이 없다")
    if none:
        print(f"심을 자리가 없던 것: {', '.join(none)} "
              f"(이 문서 묶음에 해당 자리가 없다 -- 관문 잘못이 아니다)")
    if a.miss:
        for name, _, _ in MUTATIONS:
            for f, sec, sent in tally[name]["놓친것"][:5]:
                print(f"\n[놓침 {name}] {f} · {sec}\n    {sent}")
    return 1 if blind else 0


if __name__ == "__main__":
    raise SystemExit(main())
