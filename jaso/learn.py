"""**작법을 배운다.** 남의 자소서가 아니라 **공개된 작성 가이드**에서.

    python3 jaso/learn.py --질의 "자기소개서 피해야 할 표현" --몇 8
    python3 jaso/learn.py --url 'https://<대학 취업지원센터 안내>'
    python3 jaso/learn.py --배운것          # 지금 사전에 무엇이 붙었나
    python3 jaso/learn.py --모델            # 자유 서술에서 Gemini 로 뽑는다(대조한다)

## 남의 자소서는 안 받는다 -- 기능이 무너지기 때문이다

도덕론이 아니다. 세 군데가 동시에 깨진다.

    원장에 넣으면   J001~J004 가 **남의 이력**을 대조한다. 생성자는 남의 경험을
                    당신 것처럼 쓴다
    표절 검사       한국 채용 실무의 주력은 AI 판별이 아니라 표절 검사이고, 그 DB 가
                    정확히 '인터넷에 도는 합격 자소서' 다. **가장 확실히 걸리는 길이다**
    면접            되물으면 답할 것이 없다. `trace.py` 가 낼 근거가 없다

그래서 받는 것은 **작법**(글 쓰는 법)뿐이고, 그것은 원장(사실)과 다른 자리에 담긴다.

    jaso/ledger  사실.   **사람만 채운다** (`intake.py`)
    jaso/corpus/작법  글 쓰는 법. 밖에서 온다. **관문의 사전을 늘린다**

## 배운 것이 사전을 늘린다 -- 그리고 사전은 검사받는다

지금 상투구(P003) · 이음말(D002) · 주장어(P002) 사전은 손으로 적은 씨앗이다. 가이드
문서들은 "이런 표현은 피하라" 를 실제로 열거하므로, 그것을 캐서 사전을 늘리면
**관문이 실측으로 강해진다.**

그런데 사전이 오염되면 **성한 글이 걸린다.** '저는' 이 상투구로 들어오면 모든 자소서가
P003 을 문다. 그래서 배운 낱말은 세 관문을 지나야 사전에 붙는다.

    C001  뽑은 표현이 **출처 원문에 글자 그대로** 있는가        hard -- 없으면 버린다
    C002  출처가 적혔는가                                        hard
    C003  **성한 표본을 걸지 않는가**                            hard -- 걸면 안 받는다

C003 이 요점이다. `tests/fixtures/자소서_성한것.md` 는 원장에 붙은 글이고 P003 이
지금 조용하다. **배운 낱말이 그 글을 걸면 그 낱말이 틀린 것이다** -- 사전을 늘리다가
관문을 못 쓰게 만드는 것을 막는 자리이고, `law/mutate.py` 의 GREEN 과 같은 규율이다.

## 모델은 뽑기만 하고 판정은 코드가 한다

`--모델` 을 주면 Gemini 가 가이드 본문에서 회피 표현을 뽑는다. 자유 서술이라 규칙만
으로는 놓치기 때문이다. 그때도 **뽑은 것이 원문에 실제로 있는지 C001 이 대조하고**,
없는 것은 고쳐 넣지 않고 버린다 -- `intake.py` I001 과 같은 수다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import ledger as LG                                        # noqa: E402
from jaso import wording as WD                                       # noqa: E402

작법DIR = Path(__file__).resolve().parent / "corpus" / "작법"

위반 = LG.위반

# 가이드가 "이건 쓰지 마라" 를 말하는 꼴. 따옴표 안에 든 것을 캔다.
_피하라 = re.compile(
    r"['\"‘“]([^'\"’”]{2,30})['\"’”][^.\n]{0,30}?"
    r"(?:같은\s*)?(?:표현|말|문구|문장)?[^.\n]{0,20}?"
    r"(?:피하|쓰지\s*마|삼가|지양|금물|좋지\s*않|진부|식상|흔하|뻔하)")
# 따옴표 없이 "~라는 표현은 피하라" 꼴
_피하라2 = re.compile(
    r"(?:^|[.\n·-]\s*)([가-힣][^.\n'\"‘“]{2,24}?)\s*(?:라는|이라는|같은)\s*"
    r"(?:표현|말|문구|문장)[^.\n]{0,16}?(?:피하|쓰지\s*마|삼가|지양|금물|진부|식상)")

# **너무 흔하거나 짧은 것은 애초에 안 받는다.** 사전이 오염되면 성한 글이 걸린다.
_안받는말 = {"저는", "제가", "그리고", "하지만", "때문에", "습니다", "입니다",
             "자기소개서", "자소서", "지원자", "회사", "직무", "경험", "역량",
             "노력", "성장", "생각", "사람", "다음", "이런", "그런"}


# 캐다가 안내문 자체를 물어 온 것. **버릴 자리가 여기다.**
#
# 실측: `'저는' 이라는 말은 쓰지 마십시오` 에서 따옴표 쪽 자가 두 글자를 안 받아
# 미끄러졌고, 따옴표 없는 쪽 자가 `이라는 말은 쓰지 마십시오. 그리고` 를 통째로
# 물어 왔다. C001(원문 대조)이 그것을 잡긴 했지만 -- **관문이 잡는 것과 애초에 안
# 무는 것은 다른 일이다.** 잡기만 하면 버린 것 목록이 잡음으로 차서 아무도 안 읽는다.
_안내문 = re.compile(r"피하|쓰지\s*마|삼가|지양|금물|진부|식상|시오$|니다$|"
                     r"^(이)?라는|^같은|^표현|^말은|^문구")


def _캔말인가(말: str) -> bool:
    return bool(말) and not _안내문.search(말)


@dataclass
class 배운것:
    말: str
    갈래: str = "상투구"          # 상투구 · 이음말 · 주장어
    출처: str = ""
    받은날: str = ""


@dataclass
class 작법:
    것들: list = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.것들)

    def __len__(self) -> int:
        return len(self.것들)

    def 갈래(self, 이름: str) -> list:
        return sorted({x.말 for x in self.것들 if x.갈래 == 이름})


# ---------------------------------------------------------------- 뽑기

def 뽑기(글: str, 출처: str = "") -> list:
    """가이드 본문에서 '피하라' 고 적힌 표현을 캔다. **LLM 을 안 쓴다.**"""
    오늘, out, 본것 = date.today().isoformat(), [], set()
    for 자 in (_피하라, _피하라2):
        for m in 자.finditer(글 or ""):
            말 = re.sub(r"\s+", " ", m.group(1)).strip(" .,·-")
            if 말 and 말 not in 본것 and _캔말인가(말):
                본것.add(말)
                out.append(배운것(말=말, 갈래="상투구", 출처=출처, 받은날=오늘))
    return out


def 프롬프트(글: str) -> str:
    """`--모델` 이 쓰는 것. **판정 이야기는 안 싣는다** -- 뽑기만 시킨다."""
    return f"""아래는 자기소개서 작성 안내 글입니다. 이 글이 **쓰지 말라고 지목한
표현**만 뽑아 주십시오.

{글[:12000]}

## 어떻게

- 글에 **적혀 있는 그대로** 옮기십시오. 다듬거나 바꾸지 마십시오.
- 안내 글이 지목하지 않은 것은 넣지 마십시오.
- '저는' · '입니다' 같이 어느 글에나 있는 말은 넣지 마십시오.

한 줄에 하나씩, 표현만 출력하십시오. 설명·번호·따옴표를 붙이지 마십시오."""


def 모델로뽑기(글: str, 출처: str = "", 묻기=None) -> list:
    """Gemini 로 뽑는다. **뽑은 것은 아래 `검사` 가 원문과 대조한다.**"""
    if 묻기 is None:
        from jaso import write as WR
        묻기 = WR._풀에게
    답 = 묻기(프롬프트(글)) or ""
    오늘, out, 본것 = date.today().isoformat(), [], set()
    for 줄 in 답.splitlines():
        말 = re.sub(r"^[\s\d.)*\-–·]+", "", 줄).strip(" '\"‘’“”.,")
        if 말 and 말 not in 본것:
            본것.add(말)
            out.append(배운것(말=말, 갈래="상투구", 출처=출처, 받은날=오늘))
    return out


# ---------------------------------------------------------------- 관문 C001~C003

def 검사(것들: list, 원문: str, 성한글: str = "") -> tuple:
    """(받을 것, 위반). **하나라도 걸리면 그 낱말은 사전에 안 붙는다.**"""
    받을것, vs = [], []
    for x in 것들:
        if not x.출처.strip():
            vs.append(위반("C002", "hard", x.말, "출처가 없다 -- 어디서 배웠는지 "
                                                "모르면 지어낸 것과 구별이 안 된다"))
            continue
        if x.말 not in (원문 or ""):
            vs.append(위반("C001", "hard", x.말,
                          "**출처 원문에 그 글자가 없다** -- 모델이 다듬었거나 "
                          "지어낸 것이다. 고쳐 넣지 않고 버린다"))
            continue
        if len(x.말) < 3 or x.말 in _안받는말 or not re.search(r"[가-힣]", x.말):
            vs.append(위반("C003", "hard", x.말,
                          "너무 짧거나 어느 글에나 있는 말이다 -- 받으면 성한 글이 "
                          "걸린다"))
            continue
        if 성한글 and x.말 in 성한글:
            vs.append(위반("C003", "hard", x.말,
                          "**성한 표본에 이 말이 있다** -- 받으면 원장에 붙은 글이 "
                          "P003 에 걸린다. 사전을 늘리다가 관문을 못 쓰게 만드는 자리다"))
            continue
        받을것.append(x)
    return 받을것, vs


# ---------------------------------------------------------------- 원장

def 담기(것들: list, dir: Path | None = None) -> Path | None:
    것들 = [x for x in 것들 if x.출처.strip()]
    if not 것들:
        return None
    import hashlib
    import urllib.parse
    d = Path(dir or 작법DIR)
    d.mkdir(parents=True, exist_ok=True)
    출처 = 것들[0].출처
    host = urllib.parse.urlsplit(출처).netloc or "손으로"
    h = hashlib.sha1(출처.encode("utf-8")).hexdigest()[:8]
    p = d / f"{re.sub(r'[^A-Za-z0-9.-]', '_', host)}_{h}.json"
    p.write_text(json.dumps(
        {"출처": 출처, "받은날": 것들[0].받은날,
         "배운것": [{"말": x.말, "갈래": x.갈래} for x in 것들]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def 읽기(dir: Path | None = None) -> 작법:
    d = Path(dir or 작법DIR)
    out = []
    if d.is_dir():
        for p in sorted(d.glob("*.json")):
            try:
                x = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            출처 = str(x.get("출처") or "")
            if not 출처.strip():
                continue
            for b in (x.get("배운것") or []):
                말 = str((b or {}).get("말") or "").strip()
                if 말:
                    out.append(배운것(말=말, 갈래=str(b.get("갈래") or "상투구"),
                                    출처=출처, 받은날=str(x.get("받은날") or "")))
    return 작법(out)


def 받기(질의: str = "", urls=(), 몇: int = 8, 모델: bool = False,
        묻기=None, 성한글: str = "") -> dict:
    """가이드를 받아 뽑고 검사한다. **고르지 않고 다 돌려준다.**"""
    from jaso import fetch as JF
    from dig import extract as EX
    from dig import fetch as DF
    from dig import find as FD

    보고 = {"창구별": {}, "쪽별": {}, "받을것": [], "버린것": [], "본문": {}}
    골라둔 = list(urls)
    if 질의:
        r = FD.찾기(질의, 몇=몇)
        보고["창구별"] = r.창구별
        골라둔 += [x.url for x in r.것들]
    for u in 골라둔:
        if any(w in u for w in JF.안받는곳):
            보고["쪽별"][u] = "안 받는 곳 (남의 합격 자소서 본문)"
            continue
        응답들 = [x for x in DF.캐기(u, 곁문까지=False) if x.됐나]
        if not 응답들:
            보고["쪽별"][u] = "못 받았다"
            continue
        글 = " ".join(str(EX.뽑기(x.몸통, x.꼴, x.url).get("글") or "")
                     for x in 응답들)
        보고["본문"][u] = 글
        것들 = 뽑기(글, u)
        if 모델:
            것들 += 모델로뽑기(글, u, 묻기)
        받을것, vs = 검사(것들, 글, 성한글)
        보고["받을것"] += 받을것
        보고["버린것"] += vs
        보고["쪽별"][u] = f"받을 것 {len(받을것)}개 · 버린 것 {len(vs)}개"
    return 보고


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="작성 가이드에서 작법을 배운다")
    ap.add_argument("--질의", dest="질의", default="")
    ap.add_argument("--url", dest="urls", nargs="+", default=[])
    ap.add_argument("--몇", dest="몇", type=int, default=8)
    ap.add_argument("--모델", action="store_true", help="Gemini 로도 뽑는다 (대조한다)")
    ap.add_argument("--곳", default=str(작법DIR))
    ap.add_argument("--배운것", action="store_true", help="지금 사전에 무엇이 붙었나")
    ap.add_argument("--그냥보기", action="store_true")
    a = ap.parse_args(argv)

    if a.배운것:
        L = 읽기(a.곳)
        print(f"배운 것 {len(L)}개 · 출처 {len({x.출처 for x in L.것들})}곳")
        print(f"  씨앗 상투구 {len(WD.상투구)}개 + 배운 것 {len(L.갈래('상투구'))}개")
        for x in L.것들[:40]:
            print(f"  · {x.말}    <- {x.출처[:50]}")
        if not L:
            print("  (아직 없다. `--질의` 로 받아라 -- **VM 에서**)")
        return 0 if L else 3

    if not (a.질의 or a.urls):
        ap.error("--질의 나 --url 을 주십시오 (또는 --배운것)")

    성한글 = ""
    표본 = ROOT / "tests" / "fixtures" / "자소서_성한것.md"
    if 표본.is_file():
        성한글 = 표본.read_text(encoding="utf-8")
    보고 = 받기(a.질의, a.urls, a.몇, a.모델, 성한글=성한글)
    for 이름, 말 in (보고["창구별"] or {}).items():
        print(f"  [창구 {이름}] {말}")
    for u, 말 in 보고["쪽별"].items():
        print(f"  {말:<32} {u[:64]}")

    print(f"\n받을 것 {len(보고['받을것'])}개")
    for x in 보고["받을것"][:30]:
        print(f"  · {x.말}")
    if 보고["버린것"]:
        print(f"\n버린 것 {len(보고['버린것'])}개 -- **왜 버렸는지 적는다**")
        for v in 보고["버린것"][:12]:
            print(f"  {v}")
    if not 보고["받을것"]:
        print("\n**받을 것이 없다.** 위의 까닭이 다음에 무엇을 할지 알려 준다.")
        return 3
    if a.그냥보기:
        return 0

    담긴곳 = {}
    for x in 보고["받을것"]:
        담긴곳.setdefault(x.출처, []).append(x)
    for 출처, 것들 in 담긴곳.items():
        p = 담기(것들, a.곳)
        print(f"[담음] {p}  ({len(것들)}개)" if p else f"[못담음] {출처}")
    print("\n이제 관문이 이만큼 더 본다:  python3 jaso/learn.py --배운것")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
