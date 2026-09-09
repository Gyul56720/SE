"""**예시 본문을 그 기계에만 둔다.** 저장소에는 한 줄도 안 올라간다.

    python3 jaso/keep.py --질의 "합격 자기소개서 예시" --몇 20
    python3 jaso/keep.py --url '<주소>' ...
    python3 jaso/keep.py --목록                    # 무엇이 있나
    python3 jaso/keep.py --내보내기                # bench --예시 에 넣을 경로들
    python3 jaso/keep.py --지우기                  # 다 지운다

## 왜 `mine.py` 와 따로인가 -- 계약이 다르다

    mine.py   **재고 버린다.** 담기는 것은 수뿐이다(M001). 그래서 저장소에 담아도 된다
    keep.py   **본문을 든다.** `bench --예시` 로 "그렇게 만들어줘" 를 재려면 글이 필요하다

한 파일에 두면 언젠가 M001 이 헐거워진다. 계약이 다르면 자리도 다르다.

## K001 -- **무시 규칙에 안 잡히면 저장하지 않는다**

여기는 남의 글이 실제로 앉는 유일한 자리다. 한 번 커밋되면 되돌릴 수 없다 --
`git rm` 을 해도 히스토리에 남는다.

그래서 **쓰기 전에 `git check-ignore` 로 물어본다.** 무시 규칙이 그 자리를 안 잡고
있으면 **한 자도 안 쓴다.** 규칙을 적어 놓고 추적을 안 끊는 사고를 이 저장소가 이미
겪었고(`gates/G018`), 여기서는 그 사고가 남의 이력을 공개 저장소에 올리는 일이 된다.

    K001  저장 자리가 무시 규칙에 잡히는가   hard -- 아니면 저장 안 한다
    K002  출처가 적혔는가                     hard
    K003  `Public_agent/` 밖인가              hard -- 거기는 커밋되는 곳이다

## 이 글로 무엇을 하고 무엇을 안 하나

| | |
|---|---|
| 한다 | `bench --예시` 로 "그렇게 만들어줘" 를 **재는 것**. `mine` 으로 형식을 캐는 것 |
| **안 한다** | 자소서 생성 재료로 그냥 쓰는 것. `echo.py` 로 겹침을 안 재고 넘기는 것 |

관문은 이 글과 대조하지 않는다 -- **그 사람의 원장**과 대조한다. 그래서 여기서 온
표현이 생성물에 남아도 관문은 초록불을 낸다. 그것을 잡는 자는 `echo.py` 뿐이고,
그것은 판정이 아니라 **사람이 보는 수**다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import ledger as LG                                        # noqa: E402

보기DIR = Path(__file__).resolve().parent / "corpus" / "보기"

위반 = LG.위반


def 무시되나(p: Path) -> bool:
    """**`git check-ignore` 에게 묻는다.** 내가 `.gitignore` 를 읽어 흉내 내지 않는다.

    규칙 문법(부정 규칙 · 디렉터리 · 전역 무시)을 다시 구현하면 언젠가 어긋나고,
    어긋나는 쪽은 늘 '무시된다고 잘못 믿는' 쪽이다.
    """
    try:
        r = subprocess.run(["git", "check-ignore", "-q", str(p)],
                           cwd=str(ROOT), capture_output=True, timeout=20)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False                       # 모르는 것은 안 되는 것으로 다룬다


def 검사(곳: Path, 출처: str) -> list:
    vs = []
    곳 = Path(곳)
    맛보기 = 곳 / "_확인용.txt"
    if not 무시되나(맛보기):
        vs.append(위반("K001", "hard", str(곳),
                      "**무시 규칙이 이 자리를 안 잡는다 -- 한 자도 안 쓴다.** "
                      "여기는 남의 글이 앉는 자리이고, 한 번 커밋되면 `git rm` 을 "
                      "해도 히스토리에 남는다. `.gitignore` 에 "
                      f"`{곳.relative_to(ROOT) if ROOT in 곳.parents else 곳}/` "
                      "를 먼저 넣어라"))
    if not (출처 or "").strip():
        vs.append(위반("K002", "hard", "출처", "출처가 없다"))
    공개 = (ROOT / "Public_agent").resolve()
    if 곳.resolve() == 공개 or 공개 in 곳.resolve().parents:
        vs.append(위반("K003", "hard", str(곳),
                      "`Public_agent/` 는 커밋되는 곳이다"))
    return vs


def 담기(글: str, 출처: str, 곳: Path | None = None) -> tuple:
    """`(경로, 위반들)`. **위반이 있으면 경로가 None 이고 아무것도 안 쓴다.**"""
    d = Path(곳 or 보기DIR)
    vs = 검사(d, 출처)
    if LG.hard(vs):
        return None, vs
    d.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha1((글 or "").encode("utf-8")).hexdigest()[:12]
    host = urllib.parse.urlsplit(출처).netloc or "손으로"
    p = d / f"{re.sub(r'[^A-Za-z0-9.-]', '_', host)}_{h}.txt"
    if p.exists():
        return p, vs                       # 같은 글은 다시 안 쓴다
    p.write_text(
        f"# 출처: {출처}\n# 받은날: {date.today().isoformat()}\n"
        "# **이 파일은 저장소에 안 올라간다.** 남의 글이다 -- 재는 데만 쓰고,\n"
        "# 생성물에 표현이 남았는지는 `python3 jaso/echo.py` 로 잰다.\n"
        f"{'-' * 60}\n{글}\n", encoding="utf-8")
    return p, vs


def 읽기(곳: Path | None = None) -> list:
    """`[(경로, 출처, 본문)]`. 머리말은 떼고 준다."""
    d = Path(곳 or 보기DIR)
    out = []
    if d.is_dir():
        for p in sorted(d.glob("*.txt")):
            글 = p.read_text(encoding="utf-8")
            출처 = ""
            m = re.match(r"# 출처: (.*)", 글)
            if m:
                출처 = m.group(1).strip()
            몸 = 글.split("-" * 60, 1)[-1].strip()
            if 몸:
                out.append((p, 출처, 몸))
    return out


def 받기(질의: str = "", urls=(), 몇: int = 20, 곳: Path | None = None,
        최소: int = 400) -> dict:
    from dig import extract as EX
    from dig import fetch as DF
    from dig import find as FD

    보고 = {"창구별": {}, "쪽별": {}, "담은것": [], "위반": []}
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
                     for x in 응답들).strip()
        if len(글) < 최소:
            보고["쪽별"][u] = f"너무 짧다 ({len(글)}자)"
            continue
        p, vs = 담기(글, u, 곳)
        보고["위반"] += vs
        if p is None:
            보고["쪽별"][u] = "**안 담았다** (아래 위반)"
            break                          # K001 이면 다음 쪽도 마찬가지다
        보고["담은것"].append(p)
        보고["쪽별"][u] = f"담았다 · {len(글)}자 · {p.name}"
    return 보고


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="예시 본문을 그 기계에만 둔다 (저장소에는 안 올라간다)")
    ap.add_argument("--질의", dest="질의", default="")
    ap.add_argument("--url", dest="urls", nargs="+", default=[])
    ap.add_argument("--몇", dest="몇", type=int, default=20)
    ap.add_argument("--곳", default=str(보기DIR))
    ap.add_argument("--목록", action="store_true")
    ap.add_argument("--내보내기", action="store_true",
                    help="bench --예시 에 그대로 넣을 경로들")
    ap.add_argument("--지우기", action="store_true")
    a = ap.parse_args(argv)
    곳 = Path(a.곳)

    if a.지우기:
        n = 0
        for p, _, _ in 읽기(곳):
            p.unlink()
            n += 1
        print(f"{n}개 지웠다")
        return 0

    if a.목록 or a.내보내기:
        것들 = 읽기(곳)
        if not 것들:
            print(f"담긴 것이 없다: {곳}\n"
                  "  python3 jaso/keep.py --질의 \"...\" 로 받아라 (**VM 에서**)",
                  file=sys.stderr)
            return 3
        if a.내보내기:
            print(" ".join(f"'{p}'" for p, _, _ in 것들))
            return 0
        print(f"예시 {len(것들)}편 · {곳}\n")
        for p, 출처, 몸 in 것들:
            print(f"  {len(몸):>6}자  {p.name}")
            print(f"          {출처[:66]}")
        _꼬리표(곳)
        return 0

    if not (a.질의 or a.urls):
        ap.error("--질의 나 --url 을 주십시오 (또는 --목록 · --내보내기 · --지우기)")

    # **받기 전에 자리부터 본다.** 다 긁어 놓고 못 쓴다고 하면 그 왕복이 낭비다.
    막힌것 = LG.hard(검사(곳, "확인"))
    if 막힌것:
        for v in 막힌것:
            print(f"  {v}", file=sys.stderr)
        return 1

    보고 = 받기(a.질의, a.urls, a.몇, 곳)
    for 이름, 말 in (보고["창구별"] or {}).items():
        print(f"  [창구 {이름}] {말}")
    for u, 말 in 보고["쪽별"].items():
        print(f"  {말:<40} {u[:56]}")
    for v in LG.hard(보고["위반"]):
        print(f"  {v}", file=sys.stderr)
    print(f"\n담은 것 {len(보고['담은것'])}편 -> {곳}")
    if not 보고["담은것"]:
        print("\n**한 편도 못 담았다.** 위의 까닭이 다음에 무엇을 할지 알려 준다.")
        return 3
    _꼬리표(곳)
    return 0


def _꼬리표(곳: Path) -> None:
    print("\n" + "=" * 62)
    print(f"**이 폴더는 저장소에 안 올라간다** ({곳}) -- K001 이 그것을 먼저 확인한다.")
    print("남의 글이다. 재는 데만 쓴다:")
    print("  python3 jaso/mine.py --url ...        # 형식만 캔다 (본문 안 남김)")
    print("  python3 jaso/bench.py --예시 $(python3 jaso/keep.py --내보내기) ...")
    print("  python3 jaso/echo.py --글 자소서.md --예시 $(… --내보내기)")
    print("**관문은 이 글과 대조하지 않는다** -- 그 사람의 원장과 대조한다.")
    print("  그래서 여기서 온 표현이 생성물에 남아도 관문은 초록불을 낸다.")
    print("  그것을 잡는 자는 echo.py 뿐이고, 판정이 아니라 사람이 보는 수다.")


if __name__ == "__main__":
    raise SystemExit(main())
