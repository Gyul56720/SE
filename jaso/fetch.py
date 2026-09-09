"""**문항을 받아 원장에 담는다.** `dig/find.py` -> `dig/` -> `jaso/corpus.py`.

    python3 jaso/fetch.py --질의 "2026 상반기 자기소개서 문항"
    python3 jaso/fetch.py --url 'https://<채용공고>' --회사 무봉테크
    python3 jaso/fetch.py --질의 "자소서 문항" --몇 8 --그냥보기   # 안 담고 보기만

`law/fetch.py` 가 법제처에서 조문을 받아 원장에 담는 자리와 같다. 다른 것은 **출처가
한 곳이 아니라는 점**이다 -- 채용 공고는 회사마다 다른 데 있고, 그래서 앞에
`dig/find.py`(질의 -> 주소)가 한 걸음 더 붙는다.

## 여기서는 못 돌린다

이 에이전트 컨테이너는 나가는 길이 막혀 있다(프록시 CONNECT 403). **VM 에서 돌려라.**
여기서 되는 것은 배선 검사뿐이고, `tests/test_jaso_fetch.py` 가 `dig.fetch.한번` 을
갈아 끼워 그 배선을 붙든다.

## 받는 것과 안 받는 것

| | |
|---|---|
| 받는다 | 채용 공고의 **문항**(공고문) · 공개된 **작성법 안내** |
| **안 받는다** | **남의 합격 자소서 본문** |

뒤엣것을 안 받는 이유는 저작권만이 아니다. 남의 자소서를 재료로 삼으면 **그 문장이
새 자소서에 스며든다.** 그것은 참고가 아니라 표절이고, 이 파이프라인이 잡으려는
`P001 치환 가능` 을 스스로 만드는 짓이다.

로그인·유료벽은 안 건드린다(`dig/README.md` 와 같은 선).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dig import extract as EX                                        # noqa: E402
from dig import fetch as DF                                          # noqa: E402
from dig import find as FD                                           # noqa: E402
from jaso import corpus as CP                                        # noqa: E402

# 이런 데서 온 것은 안 담는다 -- 남의 자소서 본문이 있는 자리.
안받는곳 = ("자소서합격", "합격자소서", "합격자기소개서", "자소서항목모음집")


def _눕히기(것) -> list:
    """중첩된 것을 글 목록으로 편다.

    **실측: `목록` 은 `[[...]]` 이다**(표 하나에 항목 여럿). `str(x)` 를 그대로
    쓰면 파이썬 repr(`['1. 본인이...', ...]`)이 글이 되고, 대괄호와 따옴표가 섞여
    문항 어미가 안 잡힌다 -- 문항 0개가 나오고 까닭은 안 보인다.
    """
    if 것 is None:
        return []
    if isinstance(것, (list, tuple, set)):
        return [y for x in 것 for y in _눕히기(x)]
    if isinstance(것, dict):
        return [y for x in 것.values() for y in _눕히기(x)]
    return [str(것)] if str(것).strip() else []


def 한쪽에서(url: str, 회사: str = "", 틈: float = DF.기본틈) -> tuple:
    """주소 하나에서 문항을 캔다. `(받은문항들, 못받은까닭)`.

    **앞문이 되어도 곁문을 본다** -- `dig/fetch.캐기` 를 그대로 쓴다. 채용 공고는
    모바일 쪽에만 전문이 있는 일이 흔하다.
    """
    응답들 = DF.캐기(url, 곁문까지=True, 틈=틈)
    된것 = [r for r in 응답들 if r.됐나]
    if not 된것:
        return [], (응답들[0].왜 if 응답들 else "아무 문도 안 열렸다")
    글벌 = []
    for r in 된것:
        뽑 = EX.뽑기(r.몸통, r.꼴, r.최종url or r.url)
        글벌.append(str(뽑.get("글") or ""))
        글벌 += _눕히기(뽑.get("제목들")) + _눕히기(뽑.get("목록"))
    return CP.문항뽑기("\n".join(글벌), url, 회사), ""


def 받기(질의: str = "", urls=(), 회사: str = "", 몇: int = 8,
        틈: float = DF.기본틈) -> dict:
    """질의나 주소로 문항을 받는다. **고르지 않고 받은 것을 다 돌려준다.**"""
    보고 = {"질의": 질의, "찾은주소": [], "쪽별": {}, "문항": [], "창구별": {}}
    골라둔 = list(urls)
    if 질의:
        r = FD.찾기(질의, 몇=몇, 틈=틈)
        보고["창구별"] = r.창구별
        골라둔 += [x.url for x in r.것들]
    보고["찾은주소"] = 골라둔
    for u in 골라둔:
        if any(w in u for w in 안받는곳):
            보고["쪽별"][u] = "안 받는 곳 (남의 합격 자소서 본문)"
            continue
        got, 왜 = 한쪽에서(u, 회사, 틈)
        보고["쪽별"][u] = f"문항 {len(got)}개" if got else (왜 or "문항 없음")
        보고["문항"] += got
    return 보고


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="자소서 문항을 받아 원장에 담는다")
    ap.add_argument("--질의", dest="질의", default="")
    ap.add_argument("--url", dest="urls", nargs="+", default=[])
    ap.add_argument("--회사", default="")
    ap.add_argument("--몇", dest="몇", type=int, default=8)
    ap.add_argument("--틈", dest="틈", type=float, default=DF.기본틈)
    ap.add_argument("--곳", default=str(CP.문항DIR))
    ap.add_argument("--그냥보기", action="store_true", help="원장에 안 담고 보기만")
    a = ap.parse_args(argv)
    if not (a.질의 or a.urls):
        ap.error("--질의 나 --url 을 주십시오")

    보고 = 받기(a.질의, a.urls, a.회사, a.몇, a.틈)
    for 이름, 말 in (보고["창구별"] or {}).items():
        print(f"  [창구 {이름}] {말}")
    for u, 말 in 보고["쪽별"].items():
        print(f"  {말:<28} {u[:70]}")

    got = 보고["문항"]
    print(f"\n문항 {len(got)}개")
    for q in got[:20]:
        print(f"  · {q.글[:90]}")
    if not got:
        print("\n**한 문항도 못 받았다.** 위의 까닭이 다음에 무엇을 할지 알려 준다.")
        return 3
    if a.그냥보기:
        return 0

    담긴곳 = {}
    for q in got:
        담긴곳.setdefault(q.출처, []).append(q)
    for 출처, 것들 in 담긴곳.items():
        p = CP.담기(것들, a.곳)
        print(f"[담음] {p}  ({len(것들)}개)" if p else f"[못담음] 출처가 없다: {출처}")
    print(f"\n이제 묻는다:  python3 jaso/ask.py --표 내원장.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
