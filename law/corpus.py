"""조문 원장 -- 심판이 대조할 **바깥의 사실**.

소설에서 기계 관문이 볼 수 있는 것을 만들려면 세계 원장(관계·비밀·설정)을 인공적으로
쌓아야 했다. 법은 그 원장이 이미 밖에 있다. 조문 원문이 그것이다. 이 파일은 그 원문을
읽어 들여 "제356조가 실재하는가", "그 조문에 3천만원이 적혀 있는가" 를 문자열과 숫자로
답할 수 있게만 만든다. 해석은 하지 않는다.

**원장이 없으면 심판도 없다.** 대조할 원문이 없는데 인용을 판정하면 그건 LLM 이 LLM 을
채점하는 구조로 되돌아가는 것이다(mathgen/README 가 하지 말라고 적어둔 그 구조). 그래서
코퍼스가 담지 않은 법령의 인용은 **위반이 아니라 '미검증'** 으로 따로 세어 보고한다.
기각도 통과도 아니다 -- 아직 아무도 안 봤다는 뜻이다.

## 코퍼스 넣는 법

    law/corpus/<법령명>.txt

파일 이름의 확장자를 뗀 것이 법령명이 된다(`law/corpus/형법.txt` -> "형법").
내용은 국가법령정보센터에서 복사한 조문 원문 그대로면 된다:

    # 시행 2026-01-01          <- '#' 로 시작하는 줄은 메타로 보고 버린다
    제355조(횡령, 배임) ①타인의 재물을 보관하는 자가 ... 5년 이하의 징역 ...
    ②전항의 방법으로 ...
    제356조(업무상의 횡령과 배임) 업무상의 임무에 위배하여 전조의 죄를 범한 자는
    10년 이하의 징역 또는 3천만원 이하의 벌금에 처한다.

`제N조` / `제N조의M` 이 나오는 자리에서 끊어 조문 단위로 담는다. 항·호는 조문 본문 안에
그대로 남겨둔다 -- 인용이 `제355조제1항` 이어도 대조는 조문 단위로 한다. 항 단위 대조는
①②③ 원문자 표기와 '제1항' 표기가 섞이는 문제가 있어 아직 하지 않는다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"

# 문서가 줄여 쓰는 이름 -> 코퍼스 파일 이름. 필요하면 여기 늘린다.
ALIASES = {
    "도시정비법": "도시 및 주거환경정비법",
    "도정법": "도시 및 주거환경정비법",
    "민집법": "민사집행법",
    "형소법": "형사소송법",
    "민소법": "민사소송법",
}

# 본문에 나타나는 법령명. 인용 앞에 붙어 있으면 그 법령의 조문으로 본다.
STATUTE_NAME = re.compile(
    r"(?:[가-힣]{2,20}에\s*관한\s*법률|[가-힣]{1,12}법(?:률)?|[가-힣 ]{4,30}정비법)"
)

# 법으로 끝나지만 법령명이 아닌 말들. '민법' 을 받으려고 앞자리를 1자까지 열었더니
# '이 법', '방법' 까지 법령명으로 잡혔다. 잘못 잡힌 이름은 원장에 없으므로 그 인용이
# 조용히 '미검증' 으로 새 나간다 -- 기각보다 나쁘다. 그래서 여기서 막는다.
NOT_A_STATUTE = {
    "법", "이법", "그법", "본법", "동법", "당법", "방법", "위법", "적법", "불법",
    "합법", "탈법", "입법", "사법", "공법", "현행법", "특별법", "일반법", "실체법",
    "절차법", "성문법", "관습법", "국내법", "국제법", "상위법", "하위법", "구법", "신법",
}

# 조문 인용. 제356조 / 제356조의2 / 제355조제1항제2호
CITATION = re.compile(
    r"제\s*(?P<jo>\d+)\s*조(?:\s*의\s*(?P<ji>\d+))?"
    r"(?:\s*제\s*(?P<hang>\d+)\s*항)?(?:\s*제\s*(?P<ho>\d+)\s*호)?"
)

# 조문 본문을 끊는 자리. **줄 첫머리에 오고, 뒤에 조 제목 괄호나 항 번호가 붙은 것만.**
#
# 처음에는 `제N조` 를 아무 데서나 끊었다. 그러면 본문 안의 **참조**에서도 끊긴다 --
# "제22조(준용) 가상법인의 청산에 관하여는 제12조를 준용한다" 가 제22조와 제12조 둘로
# 잘려 제22조 본문이 "…관하여는" 에서 끝났다(실측). 준용·전조 참조는 한국 법령 어디에나
# 있으므로 이건 특수한 사고가 아니다. 게다가 같은 번호가 두 벌 생기면 긴 쪽을 남기는
# 규칙 탓에, 짧은 진짜 조문이 긴 참조 꼬리에 덮일 수도 있었다.
# **헌법에는 조 제목이 없다.** 조 제목 괄호나 항 번호가 붙은 것만 머리로 보았더니
# 대한민국헌법이 조문 머리 130개 중 75개만 잡혔다(실측). "제10조 모든 국민은..." 처럼
# 제목 없이 곧바로 본문이 오는 조문이 통째로 빠진 것이다. 그래서 **뒤에 공백이 오는 것도**
# 머리로 받는다. 대신 아래 '번호는 커진다' 규칙으로 참조를 걸러낸다.
_ARTICLE_HEAD = re.compile(
    r"^[ \t]*제\s*(\d+)\s*조(?:\s*의\s*(\d+))?"
    r"(?=\s*[(（]|\s*[①-⑮]|[ \t]+\S|[ \t]*$)",
    re.M)

_MAG = {"억": 10**8, "만": 10**4, "천": 10**3, "백": 100, "십": 10}

# 수량 표현. '3천만원', '1천500만원', '10년' 을 한 덩어리로 잡는다.
QUANTITY = re.compile(
    r"(?P<num>\d[\d,]*(?:[억만천백십][\d,]*)*)\s*"
    r"(?P<unit>개월|년|월|일|주|시간|억원|만원|원|퍼센트|%)"
)

_UNIT_CLASS = {
    "년": ("기간", 365), "개월": ("기간", 30), "월": ("기간", 30),
    "주": ("기간", 7), "일": ("기간", 1),
    "시간": ("시간", 1),
    "억원": ("금액", 10**8), "만원": ("금액", 10**4), "원": ("금액", 1),
    "퍼센트": ("비율", 1), "%": ("비율", 1),
}


def kor_number(s: str):
    """'3천만' -> 30000000. 숫자와 억/만/천/백/십이 섞인 표기를 값으로 바꾼다.

    한국 법령의 금액은 '1천500만원' 처럼 아라비아 숫자와 한자 자릿수가 섞인다.
    문자열로 비교하면 '1천500만원' 과 '1500만원' 이 다른 값으로 잡혀 멀쩡한 인용을
    기각한다. 값으로 바꿔서 비교한다.
    """
    total = cur = num = 0
    seen = False
    for ch in s.replace(",", "").strip():
        if ch.isdigit():
            num = num * 10 + int(ch)
            seen = True
        elif ch in _MAG:
            seen = True
            mag = _MAG[ch]
            # '만원'(=1만) 처럼 앞에 수가 없으면 1로 본다. 다만 '3천만' 의 '만' 처럼
            # 앞자리(cur)가 이미 차 있으면 더할 것이 없다 -- 여기에 1을 더해서
            # 3천만이 30,010,000 이 됐다(실측).
            base = num if num else (0 if cur else 1)
            if mag >= 10**4:
                cur = (cur + base) * mag
                total += cur
                cur = num = 0
            else:
                cur += base * mag
                num = 0
        else:
            return None
    return total + cur + num if seen else None


@dataclass(frozen=True)
class Quantity:
    """수량 하나. 값과 단위 종류만 남긴다 -- 표기 차이는 여기서 지워진다."""
    raw: str
    value: int
    kind: str          # 기간 | 금액 | 비율 | 시간

    def key(self):
        return (self.kind, self.value)


def quantities(text: str) -> list:
    """문장에서 수량을 뽑는다. 인용 토큰(제356조)의 숫자는 세지 않는다."""
    cleaned = CITATION.sub(" ", text)
    out = []
    for m in QUANTITY.finditer(cleaned):
        val = kor_number(m.group("num"))
        if val is None:
            continue
        kind, mult = _UNIT_CLASS[m.group("unit")]
        out.append(Quantity(m.group(0), val * mult, kind))
    return out


@dataclass(frozen=True)
class Citation:
    """본문에 나타난 인용 하나."""
    raw: str
    statute: str | None    # 인용 바로 앞에 법령명이 있었으면 그것, 없으면 None
    article: str           # '356' 또는 '356의2'
    hang: str | None
    ho: str | None

    def label(self) -> str:
        head = f"{self.statute} " if self.statute else ""
        return f"{head}제{self.article.replace('의', '조의')}조" \
            if "의" in self.article else f"{head}제{self.article}조"


def normalize_statute(name: str | None) -> str | None:
    if not name:
        return None
    name = re.sub(r"\s+", " ", name).strip()
    return ALIASES.get(name.replace(" ", ""), ALIASES.get(name, name))


def find_citations(text: str) -> list:
    """조문 인용을 뽑는다. 같은 문장 안 **앞 40자**에 법령명이 있으면 그 법령에 붙인다.

    '민법 제703조' 는 민법으로, 그냥 '제703조' 는 소속 미상(None)으로 돌려준다.
    미상은 나중에 문서 front-matter 의 source_statute 로 메운다 -- 그게 규약이다.
    """
    out = []
    for m in CITATION.finditer(text):
        window = text[max(0, m.start() - 40):m.start()]
        window = re.split(r"[.!?\n]", window)[-1]     # 앞 문장의 법령명은 안 끌어온다
        names = [n for n in STATUTE_NAME.findall(window)
                 if n.replace(" ", "") not in NOT_A_STATUTE]
        statute = normalize_statute(names[-1]) if names else None
        article = m.group("jo") + (f"의{m.group('ji')}" if m.group("ji") else "")
        out.append(Citation(m.group(0), statute, article,
                            m.group("hang"), m.group("ho")))
    return out


@dataclass
class Corpus:
    """법령명 -> {조문번호: 조문 원문}."""
    articles: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)

    def covers(self, statute: str | None) -> bool:
        """이 법령을 원장이 담고 있는가. 아니면 그 인용은 '미검증' 이다."""
        return normalize_statute(statute) in self.articles

    def text(self, statute: str | None, article: str):
        return self.articles.get(normalize_statute(statute), {}).get(article)

    def has(self, statute: str | None, article: str) -> bool:
        return self.text(statute, article) is not None

    def statutes_with(self, article: str) -> list:
        """이 조문 번호를 가진 법령들. 법령명 없이 인용된 것을 되짚을 때 쓴다."""
        return [s for s, arts in self.articles.items() if article in arts]

    def quantities_of(self, statute: str | None, article: str) -> set:
        body = self.text(statute, article)
        return {q.key() for q in quantities(body)} if body else set()

    def __bool__(self):
        return bool(self.articles)


def _parse_articles(raw: str) -> dict:
    body = "\n".join(l for l in raw.splitlines() if not l.lstrip().startswith("#"))
    # **조문 번호는 커진다.** 줄 첫머리에 오는 `제N조 ...` 가운데 번호가 앞으로 돌아가는
    # 것은 조문 머리가 아니라 참조다("제12조 및 제13조에 따른다" 가 줄 첫머리에 올 수
    # 있다). 이 한 줄이 제목 없는 조문을 받으면서 생긴 위험을 도로 막는다.
    #
    # 부작용 하나를 알고 둔다: 부칙은 번호가 제1조부터 다시 시작하므로 여기서 떨어진다.
    # 원장은 본칙을 대조하는 자리라 지금은 그것이 맞다.
    heads, last = [], (0, 0)
    for m in _ARTICLE_HEAD.finditer(body):
        key = (int(m.group(1)), int(m.group(2) or 0))
        if key <= last:
            continue
        heads.append(m)
        last = key
    out = {}
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        key = m.group(1) + (f"의{m.group(2)}" if m.group(2) else "")
        chunk = body[m.start():end].strip()
        # 같은 조문이 두 번 나오면(개정 전후 병기 등) 긴 쪽을 남긴다.
        if len(chunk) > len(out.get(key, "")):
            out[key] = chunk
    return out


def load(root: Path | str = CORPUS_DIR) -> Corpus:
    """코퍼스 디렉터리를 읽는다. 비어 있으면 빈 원장을 돌려준다 -- 오류가 아니다.

    빈 원장으로도 구조·자기모순·판례 라벨 관문은 돈다. 인용 대조 관문만 '미검증' 으로
    빠진다. 무엇이 검증되고 무엇이 안 됐는지는 보고서가 항상 같이 적는다.
    """
    root = Path(root)
    corpus = Corpus()
    if not root.is_dir():
        return corpus
    for path in sorted(root.glob("*.txt")) + sorted(root.glob("*.md")):
        if path.name.lower().startswith("readme"):
            continue
        arts = _parse_articles(path.read_text(encoding="utf-8"))
        if not arts:
            continue
        name = normalize_statute(path.stem)
        corpus.articles.setdefault(name, {}).update(arts)
        corpus.sources[name] = str(path)
    return corpus


if __name__ == "__main__":
    c = load()
    if not c:
        print(f"원장이 비어 있다. {CORPUS_DIR} 에 조문 원문을 넣어라 (형식은 이 파일 docstring).")
    for name, arts in sorted(c.articles.items()):
        nums = sorted(arts, key=lambda a: (int(a.split("의")[0]), a))
        print(f"{name}: 조문 {len(arts)}개  [{c.sources[name]}]")
        print(f"  {', '.join('제' + n + '조' for n in nums[:20])}"
              + (" ..." if len(nums) > 20 else ""))
