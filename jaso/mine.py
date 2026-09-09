"""**합격 자소서에서 문법을 캔다.** 본문은 안 남기고 **잰 것만** 남긴다.

    python3 jaso/mine.py --질의 "합격 자소서 예시" --몇 12
    python3 jaso/mine.py --url '<주소>' ...
    python3 jaso/mine.py --분포            # 지금까지 잰 것의 분포
    python3 jaso/mine.py --문법후보        # forms.py 에 넣을 초안을 낸다

## 문법은 문장이 아니라 구조다

"합격 문법을 뽑는다" 는 **본문을 들고 있을 필요가 없다.** 문단이 몇 개인가 · 첫 문장이
장면인가 결론인가 · 100자에 수가 몇 개인가 · 문장 길이가 고른가 -- 이것이 문법이고,
전부 **세면 나온다.**

그래서 여기는 **잰 수만 담는다.** 본문은 담기지 않는다(`M001` 이 그것을 붙든다).
그렇게 하면 두 가지가 동시에 풀린다.

    남의 글이 결과물에 섞일 통로가 **없어진다**   -> 표절 검사에 걸릴 자리가 없다
    저작물을 복제해 두지 않는다                   -> 사본이 아니라 통계다

## 이 수가 무엇이고 무엇이 아닌가

**합격 자소서에서 관찰된 형식 분포**다. 그것 이상도 이하도 아니다.

| | |
|---|---|
| **아니다** | "이 형식이면 합격률이 높다" -- 불합격 쪽 표본이 통째로 없다. 합격자만 올리기 때문이다(선택 편향). 불합격 자소서도 같은 분포일 수 있고, 그러면 이 수는 아무것도 안 가린다 |
| **아니다** | 인과 -- 합격은 학점·전공·경력·면접·TO 가 대부분 정한다 |
| **맞다** | **문법 후보를 만드는 재료.** 여기서 나온 형식을 `jaso/forms.py` 에 후보로 넣고, **순위는 `bench.py` 가 관문으로 낸다** |

마지막 줄이 요점이다. 이 분포는 **가설을 만들고**, 채점은 바깥의 심판이 한다.
`mathgen` 이 씨앗을 어디서 가져오든 채점은 sympy 가 한 것과 같은 배치다.

## 관문

    M001  담긴 것에 **본문이 없는가**        hard -- 있으면 담지 않는다
    M002  출처가 적혔는가                     hard
    M003  표본이 결론을 낼 만한가             표시 -- 적으면 적다고 화면에 적는다
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics as st
import sys
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import beats as BT                                         # noqa: E402
from jaso import ledger as LG                                        # noqa: E402
from jaso import swap as SW                                          # noqa: E402
from jaso import wording as WD                                       # noqa: E402

잰것DIR = Path(__file__).resolve().parent / "corpus" / "잰형식"

위반 = LG.위반

# 첫 문장 갈래. **뜻을 안 읽고 꼴로만 가른다**(`scripts/which_web.py` 와 같은 수).
_장면 = re.compile(r"\d{4}년|\d+월|아침|새벽|밤|그날|당시|처음|앞에|화면|자리에|"
                   r"섰|앉|들어섰|열었|울렸|받았|보였|마주")
_결론 = re.compile(r"(입니다|이라고 생각합니다|였습니다)\s*[.。]?\s*$")
_일반론 = re.compile(r"^저는\s|^제\s|^사람은|^우리는|^누구나|^세상은")
_되풀이 = re.compile(r"(에 대해|에 관하여)\s*(말씀|서술|기술|소개)")


@dataclass
class 잰형식:
    """**본문이 없다.** 세어 놓은 수와 출처뿐이다."""
    출처: str = ""
    받은날: str = ""
    글자수: int = 0
    문단수: int = 0
    문장수: int = 0
    문장길이: float = 0.0
    문장고름: float = 0.0
    문단고름: float = 0.0
    첫문장: str = ""              # 장면 · 결론 · 일반론 · 되풀이 · 그밖
    수밀도: float = 0.0           # 100자당 수 개수
    고유밀도: float = 0.0         # 100자당 고유명사꼴 개수
    이음말밀도: float = 0.0       # 문장당 이음말
    수동밀도: float = 0.0
    상투구수: int = 0
    결과있나: bool = False
    본문해시: str = ""            # 같은 글을 두 번 안 세려고. **되돌릴 수 없다**
    # **문단마다 아홉 수.** 박자와 차례가 여기서 나온다(`jaso/beats.py`).
    # 수뿐이라 M001 을 안 깬다 -- 글은 한 조각도 안 들어간다.
    문단벡터: list = field(default_factory=list)


# 고유명사로 볼 꼴 -- 영문 낱말, 한글 2~6자 + 기관 꼬리표, 따옴표 안.
_고유 = re.compile(r"[A-Z][A-Za-z0-9+#.]{1,}|[가-힣]{2,6}(?:테크|전자|은행|공사|공단|"
                   r"대학교|연구소|병원|화학|제철|카드|증권|물산|중공업|바이오|팀|과|부)")
_수 = re.compile(r"\d[\d,]*(?:\.\d+)?")


def 재기(글: str, 출처: str = "") -> 잰형식:
    """글 하나에서 **형식만** 잰다. 돌려주는 것에 본문이 없다."""
    글 = re.sub(r"\r\n?", "\n", 글 or "").strip()
    문단 = SW.문단들(글)
    문장 = WD.문장들(글)
    n = len(글)
    첫 = 문장[0] if 문장 else ""
    갈래 = ("되풀이" if _되풀이.search(첫) else
           "일반론" if _일반론.search(첫) else
           "장면" if _장면.search(첫) else
           "결론" if _결론.search(첫) else "그밖")
    이음, 문장수 = WD.이음밀도(글)
    수동, _ = WD.수동밀도(글)
    return 잰형식(
        출처=출처, 받은날=date.today().isoformat(), 글자수=n,
        문단수=len(문단), 문장수=len(문장),
        문장길이=round(st.fmean([len(s) for s in 문장]), 1) if 문장 else 0.0,
        문장고름=round(WD.문장고름(글), 3),
        문단고름=round(WD.고름([len(p) for p in 문단]), 3),
        첫문장=갈래,
        수밀도=round(len(_수.findall(글)) * 100 / n, 2) if n else 0.0,
        고유밀도=round(len(set(_고유.findall(글))) * 100 / n, 2) if n else 0.0,
        이음말밀도=round(이음 / 문장수, 3) if 문장수 else 0.0,
        수동밀도=round(수동 / 문장수, 3) if 문장수 else 0.0,
        상투구수=len(WD.상투(글)),
        결과있나=bool(WD.성과수들(글)),
        본문해시=hashlib.sha1(글.encode("utf-8")).hexdigest()[:16],
        문단벡터=[list(v) for v in BT.글재기(글)])


# ---------------------------------------------------------------- 관문 M001~M003

# 잰 것이 들고 있어도 되는 칸. **글이 담길 수 있는 칸은 여기 없다.**
허용칸 = set(잰형식().__dict__) - {"출처"}


def 검사(것: 잰형식, 원문: str = "") -> list:
    """M001~M002. **본문이 섞여 들어왔으면 안 담는다.**"""
    vs = []
    if not (것.출처 or "").strip():
        vs.append(위반("M002", "hard", 것.본문해시 or "?",
                      "출처가 없다 -- 어디서 잰 것인지 모르면 지어낸 것과 구별이 안 된다"))
    d = asdict(것)
    for 칸, 값 in d.items():
        if 칸 == "출처":
            continue
        if isinstance(값, str) and len(값) > 24:
            vs.append(위반("M001", "hard", 칸,
                          f"**글이 담겼다**({len(값)}자) -- 여기는 잰 수만 담는다"))
        if isinstance(값, str) and 원문 and len(값) >= 12 and 값 in 원문:
            vs.append(위반("M001", "hard", 칸,
                          "**원문 조각이 담겼다** -- 사본이 아니라 통계여야 한다"))
    return vs


def 담기(것들: list, dir: Path | None = None) -> Path | None:
    """**검사를 지난 것만 담는다.** 본문이 섞였으면 그 줄을 뺀다."""
    받을것 = [x for x in 것들 if not LG.hard(검사(x))]
    if not 받을것:
        return None
    d = Path(dir or 잰것DIR)
    d.mkdir(parents=True, exist_ok=True)
    host = urllib.parse.urlsplit(받을것[0].출처).netloc or "손으로"
    h = hashlib.sha1(받을것[0].출처.encode("utf-8")).hexdigest()[:8]
    p = d / f"{re.sub(r'[^A-Za-z0-9.-]', '_', host)}_{h}.json"
    p.write_text(json.dumps([asdict(x) for x in 받을것],
                            ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def 읽기(dir: Path | None = None) -> list:
    d = Path(dir or 잰것DIR)
    out, 본해시 = [], set()
    if d.is_dir():
        for p in sorted(d.glob("*.json")):
            try:
                것들 = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for x in (것들 if isinstance(것들, list) else []):
                if not isinstance(x, dict) or not str(x.get("출처") or "").strip():
                    continue
                h = str(x.get("본문해시") or "")
                if h and h in 본해시:            # 같은 글을 두 번 안 센다
                    continue
                본해시.add(h)
                out.append(잰형식(**{k: v for k, v in x.items()
                                   if k in 잰형식().__dict__}))
    return out


# ---------------------------------------------------------------- 분포

수칸 = ("글자수", "문단수", "문장수", "문장길이", "문장고름", "문단고름",
        "수밀도", "고유밀도", "이음말밀도", "수동밀도", "상투구수")


def 분포(것들: list) -> dict:
    """중앙값과 사분위. **평균을 안 쓴다** -- 한 편이 길면 평균이 통째로 끌려간다."""
    out = {"표본": len(것들)}
    for 칸 in 수칸:
        값 = sorted(getattr(x, 칸) for x in 것들)
        if not 값:
            continue
        out[칸] = {"중앙": round(st.median(값), 2),
                  "아래": round(값[len(값) // 4], 2),
                  "위": round(값[min(len(값) - 1, 3 * len(값) // 4)], 2)}
    갈래 = {}
    for x in 것들:
        갈래[x.첫문장] = 갈래.get(x.첫문장, 0) + 1
    out["첫문장"] = dict(sorted(갈래.items(), key=lambda kv: -kv[1]))
    out["결과있는비율"] = (round(sum(1 for x in 것들 if x.결과있나) / len(것들), 2)
                       if 것들 else 0.0)
    return out


def 문법후보(d: dict) -> str:
    """분포에서 `forms.py` 에 넣을 초안을 낸다. **가설이지 결론이 아니다.**"""
    if not d.get("표본"):
        return "(잰 것이 없다)"
    첫 = next(iter(d.get("첫문장") or {"그밖": 0}))
    줄 = []
    if 첫 == "장면":
        줄.append("**첫 문장을 장면으로 엽니다.** 그때 눈앞에 있던 것 하나를 적습니다.")
    elif 첫 == "결론":
        줄.append("**첫 문장에 결론을 놓습니다.** 무엇을 했고 무엇이 달라졌는지 한 문장으로.")
    if (문단 := d.get("문단수", {}).get("중앙")):
        줄.append(f"문단을 {int(문단)}개 안팎으로 나눕니다.")
    if (길이 := d.get("문장길이", {}).get("중앙")):
        줄.append(f"문장을 {int(길이)}자 안팎으로 씁니다.")
    if (수 := d.get("수밀도", {}).get("중앙")):
        줄.append(f"100자에 수를 {수:.1f}개쯤 둡니다 -- 위 재료에 있는 수만.")
    if (이음 := d.get("이음말밀도", {}).get("중앙")) is not None and 이음 < 0.3:
        줄.append("'또한' · '이를 통해' 같은 이음말을 거의 쓰지 않습니다.")
    if d.get("결과있는비율", 0) > 0.6:
        줄.append("무엇이 달라졌는지를 반드시 적습니다.")
    줄 += ["위 경험에서만 나올 수 있는 것을 문단마다 하나는 둡니다.",
          "저를 설명하는 형용사 대신 제가 한 일을 씁니다."]
    몸 = "\n".join(f'         "{x}",' for x in 줄)
    return (f'    "캔것": 문법(\n        "캔것", "합격 자소서 {d["표본"]}편에서 '
            f'관찰된 형식 (가설)",\n        [\n{몸}\n        ]),')


# ---------------------------------------------------------------- 받기

def 받기(질의: str = "", urls=(), 몇: int = 12) -> dict:
    """공개된 쪽에서 받아 **재고 버린다.** 본문은 어디에도 안 남는다."""
    from dig import extract as EX
    from dig import fetch as DF
    from dig import find as FD

    보고 = {"창구별": {}, "쪽별": {}, "잰것": [], "버린것": []}
    골라둔 = list(urls)
    if 질의:
        r = FD.찾기(질의, 몇=몇)
        보고["창구별"] = r.창구별
        골라둔 += [x.url for x in r.것들]
    for u in 골라둔:
        응답들 = [x for x in DF.캐기(u, 곁문까지=False) if x.됐나]
        if not 응답들:
            보고["쪽별"][u] = "못 받았다"
            continue
        글 = " ".join(str(EX.뽑기(x.몸통, x.꼴, x.url).get("글") or "")
                     for x in 응답들)
        if len(글) < 300:
            보고["쪽별"][u] = f"너무 짧다 ({len(글)}자) -- 자소서 본문이 아닌 듯"
            continue
        것 = 재기(글, u)
        vs = 검사(것, 글)
        if LG.hard(vs):
            보고["버린것"] += vs
            보고["쪽별"][u] = f"버림 ({len(vs)}건)"
            continue
        보고["잰것"].append(것)
        보고["쪽별"][u] = (f"쟀다 · {것.글자수}자 · 문단 {것.문단수} · "
                        f"첫문장 {것.첫문장}")
        del 글                                  # **본문을 여기서 버린다**
    return 보고


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="합격 자소서에서 형식만 잰다 (본문은 안 남긴다)")
    ap.add_argument("--질의", dest="질의", default="")
    ap.add_argument("--url", dest="urls", nargs="+", default=[])
    ap.add_argument("--몇", dest="몇", type=int, default=12)
    ap.add_argument("--곳", default=str(잰것DIR))
    ap.add_argument("--분포", action="store_true")
    ap.add_argument("--문법후보", action="store_true")
    a = ap.parse_args(argv)

    if a.분포 or a.문법후보:
        것들 = 읽기(a.곳)
        d = 분포(것들)
        if not 것들:
            print(f"잰 것이 없다: {a.곳}\n"
                  "  python3 jaso/mine.py --질의 \"...\" 로 받아라 (**VM 에서**)",
                  file=sys.stderr)
            return 3
        if a.문법후보:
            print("# jaso/forms.py 의 `문법들` 에 넣을 초안 -- **가설이지 결론이 아니다**\n")
            print(문법후보(d))
            print("\n넣은 뒤 반드시 재라:  python3 jaso/bench.py --표 원장.json "
                  "--문항 \"...\" --문법 캔것 --문법 기본 --맨")
            return 0
        print(f"표본 {d['표본']}편\n")
        print(f"{'칸':<12}{'아래':>8}{'중앙':>8}{'위':>8}")
        for 칸 in 수칸:
            if 칸 in d:
                print(f"{칸:<12}{d[칸]['아래']:>8}{d[칸]['중앙']:>8}{d[칸]['위']:>8}")
        print(f"\n첫 문장: {d['첫문장']}")
        print(f"결과(수)를 적은 비율: {d['결과있는비율']:.0%}")
        if d["표본"] < 30:
            print(f"\n**표본이 {d['표본']}편뿐이다** -- 분포라고 부르기 이르다")
        _꼬리표()
        return 0

    if not (a.질의 or a.urls):
        ap.error("--질의 나 --url 을 주십시오 (또는 --분포 · --문법후보)")

    보고 = 받기(a.질의, a.urls, a.몇)
    for 이름, 말 in (보고["창구별"] or {}).items():
        print(f"  [창구 {이름}] {말}")
    for u, 말 in 보고["쪽별"].items():
        print(f"  {말:<44} {u[:56]}")
    것들 = 보고["잰것"]
    print(f"\n잰 것 {len(것들)}편")
    if 보고["버린것"]:
        print(f"버린 것 {len(보고['버린것'])}건:")
        for v in 보고["버린것"][:6]:
            print(f"  {v}")
    if not 것들:
        print("\n**한 편도 못 쟀다.** 위의 까닭이 다음에 무엇을 할지 알려 준다.")
        return 3
    담긴곳 = {}
    for x in 것들:
        담긴곳.setdefault(x.출처, []).append(x)
    for 출처, 벌 in 담긴곳.items():
        p = 담기(벌, a.곳)
        print(f"[담음] {p}" if p else f"[못담음] {출처}")
    print("\n다음:  python3 jaso/mine.py --분포  ·  --문법후보")
    _꼬리표()
    return 0


def _꼬리표() -> None:
    print("\n" + "=" * 62)
    print("**이것은 합격 자소서에서 관찰된 형식 분포다.**")
    print("  '이 형식이면 합격률이 높다' 가 아니다 -- 불합격 쪽 표본이 통째로 없다")
    print("  (합격자만 올린다). 불합격 자소서도 같은 분포일 수 있다.")
    print("  여기서 나온 형식은 **문법 후보**이고, 순위는 jaso/bench.py 가 관문으로 낸다.")
    print("**본문은 담기지 않았다** -- 잰 수와 출처뿐이다(M001).")


if __name__ == "__main__":
    raise SystemExit(main())
