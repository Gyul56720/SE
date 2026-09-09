"""**오래 돌며 모은다.** `dig` 로 캐고, 스스로 질의를 넓혀 간다.

    python3 jaso/crawl.py --분 60 --씨앗 "합격 자기소개서 예시"
    python3 jaso/crawl.py --분 60                  # 씨앗도 원장에서 뽑는다
    python3 jaso/crawl.py --분 60 --모델           # 질의를 Gemini 가 더 낸다
    python3 jaso/crawl.py --살펴만                 # 안 받고 무엇을 물을지만

## 백그라운드로 돌릴 때 (`CLAUDE.md` 의 규칙 그대로)

```bash
mkdir -p ~/SE/logs
setsid nohup python3 ~/SE/jaso/crawl.py --분 60 \\
    > ~/SE/logs/jaso_crawl.log 2>&1 < /dev/null &
disown
pgrep -af jaso/crawl.py          # **`ps -p $!` 로 보지 마라 -- 거짓 음성이 난다**
tail -f ~/SE/logs/jaso_crawl.log
```

멈추려면 `--그만` 이 가리키는 파일을 만든다(기본 `jaso/corpus/보기/.그만`).
`pkill -f` 는 쓰지 마라 -- 명령줄에 그 패턴이 들어 있으면 자기 셸까지 죽는다.

## 질의를 하드코딩하지 않는다

씨앗을 안 주면 **있는 것에서 뽑는다** -- 문항 원장의 흔한 낱말, 이미 받은 쪽의 제목,
사용자가 준 회사·직무·학과. 하나도 없으면 **그렇다고 말하고 멈춘다.** 목록을 코드에
박으면 그 목록 밖은 영영 안 찾아지고, 그 목록은 늘 모자란다.

그리고 **받은 것에서 질의를 넓힌다.** 받아 온 쪽의 제목에서 자주 나오는 낱말을 씨앗에
붙여 다음 질의를 만든다 -- 한 바퀴 돌 때마다 물을 것이 늘어난다.

## 예의

같은 쪽을 두 번 안 받고(주소·본문 해시), 요청 사이에 `--틈`(기본 3초)을 둔다.
빨리 긁으면 그 쪽이 막고, 막히면 아무것도 못 받는다 -- 느린 것이 빠른 것이다.

## 담는 자리는 둘이고 계약이 다르다

    jaso/keep.py   **본문**을 그 기계에만 (K001: 무시 규칙에 안 잡히면 한 자도 안 쓴다)
    jaso/mine.py   **잰 것만** (M001: 본문이 섞이면 안 담는다). 이쪽은 담아도 된다
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import keep as KP                                          # noqa: E402
from jaso import ledger as LG                                        # noqa: E402
from jaso import mine as MN                                          # noqa: E402

_낱말 = re.compile(r"[0-9A-Za-z가-힣]{2,}")
# 질의에 붙여 봐야 아무 데나 걸리는 말. **질의 목록이 아니라 걸러내는 목록이다.**
_흔한 = {"자기", "소개", "소개서", "합격", "예시", "지원", "채용", "모집", "공고",
         "대학", "회사", "기업", "안내", "바로", "가기", "확인", "사이트", "정보",
         "블로그", "네이버", "다음", "티스토리", "관련", "검색", "결과"}


def 씨앗뽑기(a) -> list:
    """**질의를 코드에 안 박는다.** 있는 것에서 뽑는다."""
    씨 = [x for x in a.씨앗 if x.strip()]
    for x in (a.회사, a.직무, a.학과):
        if x.strip():
            씨.append(f"{x.strip()} 자기소개서 문항")
    try:
        from jaso import corpus as CP
        말 = Counter(w for q in CP.읽기(a.문항곳).문항들
                    for w in _낱말.findall(q.글) if w not in _흔한 and len(w) >= 2)
        씨 += [f"{w} 자기소개서" for w, _ in 말.most_common(4)]
    except Exception:
        pass
    for _, 출처, 몸 in KP.읽기(a.곳)[:20]:
        말 = Counter(w for w in _낱말.findall(몸[:600])
                    if w not in _흔한 and len(w) >= 3)
        씨 += [f"{w} 자기소개서 예시" for w, _ in 말.most_common(1)]
    본것, out = set(), []
    for x in 씨:
        x = re.sub(r"\s+", " ", x).strip()
        if x and x not in 본것:
            본것.add(x)
            out.append(x)
    return out


def 넓히기(제목들: list, 씨앗: str, 몇: int = 3) -> list:
    """받아 온 쪽의 제목에서 다음 질의를 만든다. **한 바퀴마다 물을 것이 는다.**"""
    말 = Counter(w for t in 제목들 for w in _낱말.findall(t)
                if w not in _흔한 and len(w) >= 3 and w not in 씨앗)
    return [f"{w} {씨앗}" for w, n in 말.most_common(몇) if n >= 2]


def 모델질의(씨앗들: list, 묻기=None) -> list:
    """`--모델` -- 질의를 더 낸다. **검색어일 뿐이라 판정에 안 쓰인다.**"""
    if 묻기 is None:
        from jaso import write as WR
        묻기 = WR._풀에게
    벌 = "\n".join(f"- {x}" for x in 씨앗들[:8])
    답 = 묻기(f"""아래는 지금까지 쓴 검색어입니다.

{벌}

같은 것을 찾되 **다른 말로** 검색할 검색어를 8개만 더 적어 주십시오.
한 줄에 하나씩, 검색어만 출력하십시오.""") or ""
    return [re.sub(r"^[\s\d.)*\-–·]+", "", x).strip()
            for x in 답.splitlines() if x.strip()][:8]


def 돌리기(a, 묻기=None) -> dict:
    from dig import extract as EX
    from dig import fetch as DF
    from dig import find as FD

    끝날때 = time.time() + max(1, a.분) * 60
    그만파일 = Path(a.그만) if a.그만 else (Path(a.곳) / ".그만")
    씨앗들 = 씨앗뽑기(a)
    if not 씨앗들:
        return {"왜": "물을 것이 하나도 없다 -- `--씨앗` 을 주거나, 문항 원장을 "
                     "먼저 채워라(`jaso/fetch.py`)", "담음": 0}

    본주소 = {출처 for _, 출처, _ in KP.읽기(a.곳)}
    본해시 = {x.본문해시 for x in MN.읽기(a.잰곳)}
    할것, 한것 = list(씨앗들), set()
    보고 = {"담음": 0, "잼": 0, "건너뜀": 0, "못받음": 0, "질의": 0, "왜": ""}

    while time.time() < 끝날때 and 할것:
        if 그만파일.exists():
            보고["왜"] = f"{그만파일} 이 있어 멈췄다"
            break
        질의 = 할것.pop(0)
        if 질의 in 한것:
            continue
        한것.add(질의)
        보고["질의"] += 1
        r = FD.찾기(질의, 몇=a.몇)
        print(f"[{time.strftime('%H:%M:%S')}] 물음 {보고['질의']}: {질의!r} "
              f"-> 주소 {len(r.것들)}개", flush=True)
        if not r.것들:
            for 이름, 말 in r.창구별.items():
                print(f"    [{이름}] {말}", flush=True)
        할것 += [x for x in 넓히기([x.제목 for x in r.것들], 질의)
                if x not in 한것]

        for x in r.것들:
            if time.time() >= 끝날때 or 그만파일.exists():
                break
            if x.url in 본주소:
                보고["건너뜀"] += 1
                continue
            본주소.add(x.url)
            time.sleep(max(0.0, a.틈))
            응답들 = [y for y in DF.캐기(x.url, 곁문까지=False) if y.됐나]
            if not 응답들:
                보고["못받음"] += 1
                continue
            글 = " ".join(str(EX.뽑기(y.몸통, y.꼴, y.url).get("글") or "")
                         for y in 응답들).strip()
            if len(글) < a.최소:
                보고["건너뜀"] += 1
                continue
            잰것 = MN.재기(글, x.url)
            if 잰것.본문해시 in 본해시:          # 미러가 표본을 부풀린다
                보고["건너뜀"] += 1
                continue
            본해시.add(잰것.본문해시)
            if not LG.hard(MN.검사(잰것, 글)):
                MN.담기([잰것], a.잰곳)
                보고["잼"] += 1
            p, vs = KP.담기(글, x.url, a.곳)
            if p is None:
                보고["왜"] = " · ".join(str(v) for v in LG.hard(vs))
                return 보고                     # K001 이면 다음도 마찬가지다
            보고["담음"] += 1
            print(f"    담음 {len(글):>6}자  {p.name}  <- {x.url[:52]}", flush=True)

        if a.모델 and len(할것) < 3 and time.time() < 끝날때:
            더 = [q for q in 모델질의(list(한것), 묻기) if q not in 한것]
            할것 += 더
            print(f"    모델이 질의 {len(더)}개를 더 냈다", flush=True)

    if not 보고["왜"]:
        보고["왜"] = ("시간이 다 됐다" if time.time() >= 끝날때
                    else "더 물을 것이 없다")
    return 보고


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="오래 돌며 모은다 (dig)")
    ap.add_argument("--분", dest="분", type=int, default=60)
    ap.add_argument("--씨앗", dest="씨앗", action="append", default=[])
    ap.add_argument("--회사", default="")
    ap.add_argument("--직무", default="")
    ap.add_argument("--학과", default="")
    ap.add_argument("--몇", dest="몇", type=int, default=12, help="질의마다 주소 수")
    ap.add_argument("--틈", dest="틈", type=float, default=3.0,
                    help="요청 사이 쉬는 초 -- 빨리 긁으면 그 쪽이 막는다")
    ap.add_argument("--최소", dest="최소", type=int, default=400)
    ap.add_argument("--곳", default=str(KP.보기DIR))
    ap.add_argument("--잰곳", default=str(MN.잰것DIR))
    ap.add_argument("--문항곳", default="")
    ap.add_argument("--그만", default="", help="이 파일이 생기면 멈춘다")
    ap.add_argument("--모델", action="store_true", help="질의를 Gemini 가 더 낸다")
    ap.add_argument("--살펴만", action="store_true", help="안 받고 무엇을 물을지만")
    a = ap.parse_args(argv)
    if not a.문항곳:
        from jaso import corpus as CP
        a.문항곳 = str(CP.문항DIR)

    if a.살펴만:
        씨 = 씨앗뽑기(a)
        print(f"물을 것 {len(씨)}개 (씨앗)")
        for x in 씨:
            print(f"  · {x}")
        if not 씨:
            print("\n**하나도 없다.** `--씨앗` 을 주거나 문항 원장을 먼저 채워라",
                  file=sys.stderr)
            return 3
        print("\n받아 오면 그 쪽 제목에서 질의가 더 늘어난다")
        return 0

    막힌것 = LG.hard(KP.검사(Path(a.곳), "확인"))
    if 막힌것:
        for v in 막힌것:
            print(f"  {v}", file=sys.stderr)
        return 1

    시작 = time.time()
    보고 = 돌리기(a)
    print(f"\n{'=' * 62}")
    print(f"{(time.time() - 시작) / 60:.1f}분 · 물음 {보고['질의']}개 · "
          f"본문 {보고['담음']}편 · 잰 것 {보고['잼']}편 · "
          f"건너뜀 {보고['건너뜀']} · 못받음 {보고['못받음']}")
    print(f"멈춘 까닭: {보고['왜']}")
    if not 보고["담음"]:
        print("\n**한 편도 못 담았다.** 위의 까닭이 다음에 무엇을 할지 알려 준다 --\n"
              "  프록시가 끊었다 -> 이 환경의 나가는 길이 막힌 것. 다른 데서 돌려라")
        return 3
    print(f"\n다음:\n"
          f"  python3 jaso/keep.py --목록\n"
          f"  python3 jaso/mine.py --분포  ·  --문법후보\n"
          f"  python3 jaso/beats.py --차례  ·  --문법후보")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
