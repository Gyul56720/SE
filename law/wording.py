"""문언 장부 -- **novel/wording.py 를 뒤집은 것.**

소설의 말맛 장부는 "같은 뜻 다른 꼴" 을 세어서 **적게 쓴 쪽으로 민다.** 한쪽으로 몰리면
글이 비슷해지기 때문이다. 거기서 다양성은 미덕이다.

법은 정반대다. **문언은 바꿔 쓰면 안 된다.**

    조문: 명할 수 있다        문서: 명하여야 한다        -> 재량이 기속으로 바뀐다
    조문: 등록 및 신고        문서: 등록 또는 신고        -> 요건 두 개가 하나로 준다
    조문: 3년 이내            문서: 3년 이전              -> 기산과 포함이 달라진다
    조문: 준용한다            문서: 적용한다              -> 그대로 쓰는지 고쳐 쓰는지가 갈린다
    조문: 재물                문서: 재산상 이익           -> 횡령과 배임이 갈린다

다섯 줄 전부 **낱말 하나 차이인데 결론이 갈린다.** 그리고 다섯 줄 전부 조문 원문과 대조하면
기계가 판정한다 -- 취향이 아니다.

가져온 방법은 novel/wording.py 와 같다: **뜻이 아니라 꼴로 가른다.** 정규식으로 범주별
표현을 뽑아 세는 것까지 똑같고, 다른 것은 판정뿐이다. 소설은 원고 안에서의 분포를 보고,
법은 **조문 원문과 견준다.**

    W001  서법      기속 / 재량 / 금지
    W002  접속      결합(및) / 선택(또는)
    W003  경계      포함(이상·이하·이내) / 불포함(초과·미만·이전)
    W004  법효과어  적용 / 준용 / 간주(본다) / 추정
    W005  용어 치환 조문의 낱말을 뜻이 비슷해 보이는 다른 낱말로 바꿔 썼는가

판정 규칙은 하나다. **문서가 쓴 값이 인용한 조문에 하나도 없으면 위반이다.** 조문에 그
범주가 아예 없으면(견줄 것이 없으면) 판정하지 않는다 -- 과잉 기각하는 심판은 맞는 답도
버린다(novel/gate.py 가 배운 것).

    python3 law/wording.py 법이론서              # 위반
    python3 law/wording.py 법이론서 --trace      # 낱말이 어느 조문에 근거하는지
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from law import corpus as CP                                          # noqa: E402

# 범주 -> 값 -> 꼴. **뜻이 아니라 꼴로 가른다.**
AXES = {
    "W001": ("서법", {
        # '-하여야 한다 / -에 처한다 / -로 한다' 는 기속이다. 여지가 없다.
        "기속": re.compile(r"(하여야|해야|하여야만)\s*(한다|하며|하고|하는)"
                          r"|에\s*처한다|(으로|로)\s*한다\b|하여야\s*할"),
        # '-할 수 있다' 는 재량이다. 이 한 낱말이 처분의 성질을 바꾼다.
        "재량": re.compile(r"[가-힣]\s*수\s*있다|재량"),
        # 금지는 부정과 다르다. '아니한다'(사실의 부정)를 여기 넣으면 안 된다.
        "금지": re.compile(r"하여서는\s*아니\s*[되된]|하지\s*못한다|할\s*수\s*없다"),
    }),
    "W002": ("접속", {
        "결합": re.compile(r"및\s|\s및\b|아울러|모두\s*(갖|마치|충족)"),
        "선택": re.compile(r"또는|이거나|하거나|\b중\s*(하나|어느)"),
    }),
    "W003": ("경계", {
        # 한국어는 조사가 붙는다. `까지\b` 로 적었더니 "까지는/까지도" 에서 안 걸렸다.
        "포함": re.compile(r"이상|이하|이내|까지"),
        # **'이전' 은 두 뜻이다** -- 시간의 이전과 소유권 이전(移轉). 이 관문이 잡으려는
        # 것은 앞의 것뿐이라, 앞에 시간 단위가 붙은 경우만 센다. 낱말 하나가 결론을
        # 바꾼다는 말은 이 관문 자신에게도 적용된다.
        "불포함": re.compile(r"초과|미만|전까지|(?<=[년월일시분초])\s*이전|그\s*이전"),
    }),
    "W004": ("법효과어", {
        "적용": re.compile(r"적용한다|적용된다|적용하는"),
        "준용": re.compile(r"준용"),
        "간주": re.compile(r"(으로|로)\s*본다|간주"),
        "추정": re.compile(r"추정"),
    }),
}

# **바꿔 쓰면 안 되는 짝.** 뜻이 비슷해 보이지만 법효과가 다르다.
#
# 닫힌 목록이라야 기계가 볼 수 있다. 늘리려면 여기 한 줄을 더한다 -- 짝의 두 낱말이
# **같은 자리에서 서로 갈음될 수 있고, 갈음하면 결론이 달라지는** 것만 넣는다. 그냥
# 뜻이 다른 두 낱말(예: 원고/피고)은 여기 들어올 것이 아니다. 서로 헷갈릴 자리가 없다.
#
# 준용/적용과 추정/간주는 여기 없다 -- W004(법효과어)가 이미 본다. 두 곳에서 세면 같은
# 잘못이 두 번 점수에 들어가고, 튜너가 그 규칙을 실제보다 나쁘게 본다.
PAIRS = [
    # ── 민법 총칙 ────────────────────────────────────────────────
    ("무효", "취소"),                  # 처음부터 없다 / 취소해야 없어진다
    ("취소", "철회"),                  # 소급해 없앤다 / 장래를 향해 거둔다
    ("선의", "악의"),                  # 몰랐다 / 알았다
    ("고의", "과실"),
    ("과실", "중과실"),                # 경과실로 족한가 / 중대한 것이라야 하는가
    ("무과실책임", "과실책임"),
    ("소멸시효", "제척기간"),          # 중단·정지가 있다 / 없다
    ("시효중단", "시효정지"),          # 다시 처음부터 / 그동안 멈춘다
    ("추인", "추완"),                  # 흠 있는 행위를 받아들인다 / 빠진 것을 채운다
    ("대리", "대표"),                  # 별개 인격 / 기관
    ("무권대리", "표현대리"),          # 효력 없다 / 본인에게 미친다
    ("임의대리", "법정대리"),
    ("조건", "기한"),                  # 올지 모른다 / 반드시 온다
    ("기간", "기한"),
    ("정지조건", "해제조건"),          # 생긴다 / 없어진다
    # ── 물권 ────────────────────────────────────────────────────
    ("점유", "소유"),
    ("직접점유", "간접점유"),
    ("물권", "채권"),                  # 누구에게나 / 상대방에게만
    ("등기", "등록"),
    ("질권", "저당권"),                # 넘겨받는다 / 그대로 둔다
    ("유치권", "동시이행항변권"),      # 물권 / 채권적 항변
    ("전세권", "임차권"),              # 물권 / 채권
    ("대항력", "우선변제권"),          # 버틴다 / 먼저 받는다
    ("선의취득", "시효취득"),
    # ── 채권 ────────────────────────────────────────────────────
    ("이행지체", "이행불능"),          # 늦었다 / 이제 못 한다
    ("채무불이행", "불법행위"),        # 약속을 어겼다 / 남에게 손해를 입혔다
    ("해제", "해지"),                  # 소급 / 장래
    ("연대채무", "부진정연대채무"),    # 부담부분이 있다 / 없다
    ("보증", "연대보증"),              # 최고·검색의 항변이 있다 / 없다
    ("이행이익", "신뢰이익"),
    ("손해배상", "손실보상"),          # 위법한 침해 / 적법한 침해
    ("원상회복", "부당이득반환"),
    ("하자담보책임", "채무불이행책임"),
    ("특정물", "종류물"),
    ("변제", "공탁"),
    ("경개", "준소비대차"),
    # ── 민사소송 ────────────────────────────────────────────────
    ("각하", "기각"),                  # 소송요건이 없다 / 이유가 없다
    ("인용", "기각"),
    ("증명", "소명"),                  # 확신 / 그럴듯함
    ("본증", "반증"),
    ("기판력", "집행력"),
    ("기판력", "형성력"),
    ("처분권주의", "변론주의"),
    ("당사자적격", "소의 이익"),
    ("청구의 포기", "청구의 인낙"),    # 내가 진다 / 상대가 이긴다를 인정
    ("확인의 소", "이행의 소"),
    ("이행의 소", "형성의 소"),
    ("항소", "상고"),                  # 사실심 / 법률심
    ("항소", "항고"),                  # 판결 / 결정·명령
    ("재판상 자백", "자백간주"),
    ("필수적 공동소송", "통상 공동소송"),
    ("소송대리", "소송수행"),
    # ── 형법 ────────────────────────────────────────────────────
    ("재물", "재산상 이익"),           # 횡령·절도 / 배임·사기
    ("절도", "횡령"),                  # 남의 점유를 깬다 / 내가 맡은 것을 갖는다
    ("횡령", "배임"),
    ("사기", "공갈"),                  # 속인다 / 겁준다
    ("공갈", "강도"),                  # 반항을 억압하지 않는다 / 억압한다
    ("미수", "예비"),
    ("예비", "음모"),
    ("중지미수", "장애미수"),          # 필요적 감면 / 임의적 감경
    ("불능미수", "불능범"),            # 처벌한다 / 안 한다
    ("공동정범", "방조"),
    ("공동정범", "교사"),
    ("간접정범", "공동정범"),
    ("위법성조각", "책임조각"),        # 적법하다 / 나무랄 수 없다
    ("정당방위", "긴급피난"),          # 부당한 침해 / 위난
    ("정당방위", "자구행위"),          # 침해 중 / 침해 뒤
    ("정당행위", "정당방위"),
    ("상상적 경합", "실체적 경합"),    # 하나의 행위 / 여러 행위
    ("법조경합", "상상적 경합"),
    ("친고죄", "반의사불벌죄"),        # 고소가 있어야 / 처벌불원이면 못 한다
    ("몰수", "추징"),                  # 물건 / 값
    ("벌금", "과료"),
    ("벌금", "과태료"),                # 형벌 / 행정질서벌
    ("작위", "부작위"),
    ("결과범", "거동범"),
    ("침해범", "위험범"),
    # ── 형사소송 ────────────────────────────────────────────────
    ("체포", "구속"),
    ("피의자", "피고인"),              # 기소 전 / 기소 후
    ("고소", "고발"),                  # 피해자 등 / 제3자
    ("증거능력", "증명력"),            # 쓸 수 있는가 / 얼마나 믿을 만한가
    ("전문증거", "원본증거"),
    ("무죄", "면소"),
    ("무죄", "공소기각"),              # 본안 판단 / 절차 흠
    ("기소유예", "무혐의"),
    ("압수", "수색"),
    ("긴급체포", "현행범체포"),
    ("재심", "비상상고"),              # 사실인정 잘못 / 법령위반
    ("자백", "자인"),
    ("구속영장", "압수수색영장"),
    # ── 헌법·행정 ───────────────────────────────────────────────
    ("제한", "침해"),                  # 정당화될 수 있다 / 이미 위헌이다
    ("위헌", "헌법불합치"),            # 즉시 효력 상실 / 잠정 적용
    ("한정위헌", "한정합헌"),
    ("법률유보", "의회유보"),
    ("과잉금지", "과소보호금지"),
    ("자기관련성", "직접성"),
    ("직접성", "현재성"),
    ("보충성", "청구기간"),
    ("기속행위", "재량행위"),
    ("직권취소", "철회"),
    ("처분", "행정지도"),              # 다툴 수 있다 / 원칙적으로 못 한다
    ("무효확인", "취소소송"),
    ("하자의 승계", "하자의 치유"),
    ("신뢰보호", "신의성실"),
    # ── 어디에나 ────────────────────────────────────────────────
    ("즉시", "지체 없이"),             # 곧바로 / 정당한 사유가 있으면 늦출 수 있다
    ("지체 없이", "상당한 기간 내"),
]

# **짧은 용어를 품고 있어 오탐을 만드는 긴 낱말들.**
#
# 부분문자열로 보면 '무과실' 안의 '과실', '제척기간' 안의 '기간', '소유권' 안의 '소유'
# 가 따로 잡힌다(실측으로 둘 다 확인했다). 아래 낱말들을 스캐너에 같이 넣어 **긴 것부터
# 먹게** 하면, 이것들이 먼저 소비되므로 안에 든 짧은 용어가 안 잡힌다. 짝에는 안 쓴다.
MASKS = (
    "소유권", "소유자", "점유권", "점유자", "점유이전", "소유권이전",
    "과실상계", "과실비율", "고의과실", "무과실",
    "취소소송", "취소판결", "취소사유", "무효사유", "무효등확인",
    "증명책임", "주장증명책임", "소명자료",
    "기간만료", "기한이익", "존속기간", "청산기간", "제소기간",
    "연대보증인", "보증인", "보증채무",
    "손해배상액", "배상액", "배상책임",
    "해제조건부", "정지조건부",
    "미수범", "예비음모", "방조범", "교사범", "정범",
    "고발장", "고소장", "고소권자",
    "처분권", "처분문서", "처분성",
    "제한능력", "제한물권", "행위제한",
    "등기부", "등기신청", "등록면허세",
)

_WS = re.compile(r"\s+")

# **조문 인용을 잇는 접속사는 요건의 접속이 아니다.**
# 실측: "제32조 및 제43조 등의 조문에서..." 가 W002 로 기각됐다. 여기서 '및' 은 조문
# 번호 둘을 잇는 말이지 요건 둘을 묶는 말이 아니다. 견주기 전에 지운다.
_CIT_CONJ = re.compile(
    r"(제\s*\d+\s*조(?:\s*의\s*\d+)?)\s*(?:및|또는|와|과|이나|,)\s*(?=제\s*\d+\s*조)")

# **필자의 당위는 조문의 서법이 아니다.**
# 실측: "관련 법정 절차와 해석 기준을 엄격히 검토해야 한다는 점에서" 가 W001 로 기각됐다.
# 조문이 재량인데 문서가 기속이라고 본 것인데, 그 '해야 한다' 는 조문을 옮긴 것이 아니라
# 읽는 사람에게 하는 말이었다. 닫힌 목록이라야 기계가 가른다.
_AUTHOR_DUTY = re.compile(
    r"(검토|유의|주의|숙지|확인|구별|구분|기억|판단|참고|이해|명심|고려|살펴)"
    r"\s*(?:하여야|해야)\s*(?:한다|합니다|하며|하고|할)")


def _for_compare(sent: str) -> str:
    """조문과 견주기 전에 문장에서 **조문의 것이 아닌 꼴**을 지운다."""
    prev = None
    while prev != sent:                      # 인용이 셋 이상 이어질 수 있다
        prev = sent
        sent = _CIT_CONJ.sub(r"\1 ", sent)
    return _AUTHOR_DUTY.sub(" ", sent)


def _flat(t: str) -> str:
    """띄어쓰기를 지운다. '재산상 이익' 과 '재산상이익' 은 같은 낱말이다."""
    return _WS.sub("", t)


# 긴 것부터 늘어놓는다 -- 정규식 선택지는 왼쪽부터 시도되므로 이것이 곧 최장일치다.
_ALL_TERMS = sorted({t for p in PAIRS for t in p} | set(MASKS),
                    key=lambda t: -len(_flat(t)))
_TERM_RE = re.compile("|".join(re.escape(_flat(t)) for t in _ALL_TERMS))


def terms_in(text: str) -> set:
    """텍스트에 나타난 법률용어. **긴 것부터 먹는다.**

    '무과실' 안의 '과실', '제척기간' 안의 '기간', '소유권' 안의 '소유' 를 따로 세면
    멀쩡한 문장이 기각된다(실측으로 둘 다 확인했다). findall 은 겹치지 않게 훑으므로,
    긴 낱말이 먼저 소비되면 그 안의 짧은 용어는 잡히지 않는다.
    """
    return set(_TERM_RE.findall(_flat(text)))


def bucket(text: str) -> dict:
    """범주별로 어떤 값이 나타나는가. novel/wording.py 의 count() 자리."""
    out = {}
    for rule, (_, forms) in AXES.items():
        hits = {v for v, pat in forms.items() if pat.search(text)}
        if hits:
            out[rule] = hits
    return out


def _sentences(text: str) -> list:
    text = _WS.sub(" ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _targets(sent, doc, corpus):
    """이 문장이 부른 조문들의 원문. 원장이 안 담은 법령은 빠진다(미검증)."""
    out = []
    for c in CP.find_citations(sent):
        body = corpus.text(c.statute or getattr(doc, "statute", None), c.article)
        if body:
            out.append((c.raw, body))
    return out


def check(doc, corpus) -> list:
    """W001~W005. gate.py 의 CHECKS 규약(doc, corpus) 을 그대로 따른다."""
    from law.gate import Violation

    out = []
    for name, text in doc.sections.items():
        sev = "hard" if name.startswith(("2.", "3.")) else "soft"
        for sent in _sentences(text):
            tg = _targets(sent, doc, corpus)
            if not tg:
                continue
            raws = ", ".join(r for r, _ in tg)
            joined = " ".join(b for _, b in tg)
            mine, theirs = bucket(_for_compare(sent)), bucket(joined)
            for rule, vals in mine.items():
                ref = theirs.get(rule)
                if not ref:                       # 조문에 그 범주가 없다 -- 견줄 것이 없다
                    continue
                gone = vals - ref
                if gone:
                    axis = AXES[rule][0]
                    # **접속은 기각하지 않는다.** 인용을 잇는 '및' 을 지워도, 문장 단위
                    # 집합 비교로는 그 접속사가 **어느 요건 둘을 묶는지**를 못 짚는다.
                    # 조문 어딘가에 '또는' 이 있고 문서가 다른 자리에서 '및' 을 썼다는
                    # 것만으로 기각하면 멀쩡한 문장을 버린다(실측 4건이 그랬다).
                    # 판정할 자격이 없는 것은 보고로 내린다.
                    out.append(Violation(
                        rule, "soft" if rule == "W002" else sev,
                        f"{doc.path.name} · {name}",
                        f"{axis}: 조문({raws})은 {'/'.join(sorted(ref))} 인데 "
                        f"문서는 {'/'.join(sorted(gone))} 로 적었다"))
            st, at = terms_in(sent), terms_in(joined)
            for a, b in PAIRS:
                for used, other in ((a, b), (b, a)):
                    fu, fo = _flat(used), _flat(other)
                    if fu in st and fo in at and fu not in at and fo not in st:
                        out.append(Violation(
                            "W005", sev, f"{doc.path.name} · {name}",
                            f"조문({raws})은 {other!r} 인데 문서는 {used!r} 로 바꿔 적었다"))
    return out


def trace(doc, corpus) -> list:
    """**낱말이 어디에 근거하는가.** 문장마다 (조문, 근거 있는 값, 근거 없는 값).

    관문이 아니라 보고다. "글자 하나하나를 근거를 바탕으로" 가 실제로 어디까지 되고
    어디부터 안 되는지를 눈으로 보게 하는 것이 목적이다.
    """
    rows = []
    for name, text in doc.sections.items():
        for sent in _sentences(text):
            tg = _targets(sent, doc, corpus)
            cits = CP.find_citations(sent)
            if not cits:
                continue
            if not tg:
                rows.append((name, sent, [c.raw for c in cits], [], [], True))
                continue
            joined = " ".join(b for _, b in tg)
            mine, theirs = bucket(_for_compare(sent)), bucket(joined)
            grounded, ungrounded = [], []
            for rule, vals in mine.items():
                axis = AXES[rule][0]
                for v in sorted(vals):
                    (grounded if v in theirs.get(rule, ()) else ungrounded)\
                        .append(f"{axis}:{v}")
            rows.append((name, sent, [r for r, _ in tg], grounded, ungrounded, False))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="문언 대조 -- 낱말 하나가 결론을 바꾼다")
    ap.add_argument("target", nargs="?", default="법이론서")
    ap.add_argument("--corpus", default=str(CP.CORPUS_DIR))
    ap.add_argument("--trace", action="store_true", help="낱말의 근거를 늘어놓는다")
    a = ap.parse_args(argv)

    from law.gate import parse
    corpus = CP.load(a.corpus)
    t = Path(a.target)
    files = sorted(t.rglob("*.md")) if t.is_dir() else [t]
    files = [f for f in files if not f.name.lower().startswith("readme")]

    hard = soft = 0
    unver = 0
    for f in files:
        doc = parse(f)
        if a.trace:
            for name, sent, raws, g, u, missing in trace(doc, corpus):
                if missing:
                    unver += 1
                    continue
                mark = "근거 없음: " + ", ".join(u) if u else "전부 근거 있음"
                print(f"[{f.name} · {name}] {', '.join(raws)}  {mark}")
                if u:
                    print(f"    {sent[:90]}")
            continue
        for v in check(doc, corpus):
            print(f"  {v}")
            hard += v.severity == "hard"
            soft += v.severity == "soft"
    if a.trace:
        if unver:
            print(f"\n원장에 없어 대조 못 한 문장 {unver}개")
        return 0
    print(f"\n문언 대조: 문서 {len(files)}개 · hard {hard} · soft {soft}")
    if not corpus:
        print("원장이 비어 있다 -- 대조할 조문이 없으면 이 관문은 아무것도 못 본다.")
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
