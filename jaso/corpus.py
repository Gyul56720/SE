"""**문항 원장** -- 실제 공고에서 받은 자소서 문항과 그 출처.

    python3 jaso/corpus.py                       # 원장에 무엇이 있나
    python3 jaso/corpus.py --찾 역량             # 그 말이 든 문항
    python3 jaso/corpus.py --갈래                # 요구 종류별로 몇 개인가

`law/corpus.py` 가 조문 원문을 담는 자리와 같다. 다른 것은 **여기 든 것이 판정 대상이
아니라 재료**라는 점이다 -- 문항은 대조할 것이 아니라 물어볼 것을 정하는 데 쓴다.

## 출처를 안 적은 문항은 안 받는다

`reason/` S005 가 출처를 **표시**로 다룬 것과 다르다. 여기서는 **거절**한다. 까닭이
분명하다 -- 출처 없는 문항은 내가 지어낸 문항과 구별이 안 되고, 지어낸 문항으로 만든
질문은 **있지도 않은 공고에 맞춰 사용자의 시간을 쓰게 한다.**

## 문항을 어떻게 알아보나

한국 자소서 문항은 끝이 정해져 있다 -- `기술하시오` · `서술해 주십시오` ·
`작성해 주세요`. 그리고 대개 `(1,000자 이내)` 가 붙는다. 이 둘로 캔다.

**뜻을 안 읽는다.** 그래서 광고 문구나 안내문이 섞여 들어올 수 있고, 그것은 `--찾`
으로 사람이 걸러 보게 둔다. `dig/` 의 규율이다 -- 줄이면 줄인 것을 아무도 못 되찾는다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jaso import item as IT                                          # noqa: E402

문항DIR = Path(__file__).resolve().parent / "corpus" / "문항"

# 자소서 문항의 끝. **이 목록이 원장의 크기를 정한다** -- 빠뜨린 어미는 그 문항을
# 통째로 못 보게 한다. 실측으로 늘린다.
_문항끝 = re.compile(
    r"(기술|서술|작성|설명|소개|기재|작성|답변|말씀|이야기)\s*(하|해|하여|해\s*)?"
    r"\s*(시오|주십시오|주세요|주시기\s*바랍니다|주시오|십시오|보십시오|봅시다)"
    r"|기술하십시오|서술하십시오|적어\s*주십시오|적어\s*주세요")
_글자칸 = re.compile(r"[(\[]\s*[^)\]]{0,24}?\d[\d,]*\s*자[^)\]]{0,20}[)\]]")
_번호 = re.compile(r"^\s*(?:Q\s*)?(\d{1,2})\s*[.)\]]\s*")
_잡말 = re.compile(r"쿠키|로그인|회원가입|저작권|개인정보|광고|배너|바로가기")


@dataclass
class 받은문항:
    글: str
    출처: str                      # **비면 원장이 안 받는다**
    받은날: str = ""
    회사: str = ""
    번호: str = ""

    @property
    def id(self) -> str:
        return hashlib.sha1(self.글.encode("utf-8")).hexdigest()[:10]

    def 쪼갠것(self) -> IT.문항:
        return IT.쪼개기(self.글, self.번호)


@dataclass
class 원장:
    문항들: list = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.문항들)

    def __len__(self) -> int:
        return len(self.문항들)

    def 찾기(self, 말: str) -> list:
        return [q for q in self.문항들 if 말 in q.글]

    def 갈래별(self) -> dict:
        out = {}
        for q in self.문항들:
            for r in q.쪼갠것().요구:
                out.setdefault(r.종류, []).append(q)
        return out


def _끝자리(평: str):
    """문항이 끝나는 자리들. 어미로 끝나거나 `(700자)` 로 끝난다."""
    자리 = [(m.start(), m.end()) for m in _문항끝.finditer(평)]
    자리 += [(m.start(), m.end()) for m in _글자칸.finditer(평)]
    자리.sort()
    # 어미 바로 뒤에 `(700자)` 가 붙어 있으면 한 자리로 친다
    편것, i = [], 0
    while i < len(자리):
        s, e = 자리[i]
        while i + 1 < len(자리) and 0 <= 자리[i + 1][0] - e <= 3:
            e = 자리[i + 1][1]
            i += 1
        편것.append(e)
        i += 1
    return 편것


def 문항뽑기(글: str, 출처: str = "", 회사: str = "") -> list:
    """글에서 자소서 문항으로 보이는 대목을 캔다. **고르지 않고 다 내놓는다.**

    ## 줄로 자르면 안 된다 -- 두 번 데었다

    실측 (1) 공고 한 쪽에서 문항 셋이 **한 줄에** 이어져 있었다. 줄로 자르면
    `1. … (1,000자 이내) 2. 팀으로 …` 이 통째로 한 덩어리라 첫 문항만 남고 나머지가
    사라진다. 실측 (2) 반대로 `<li>` 안에서 문항 하나가 **두 줄에 걸쳐** 있었다.
    줄로 자르면 앞 반쪽은 어미가 없어 버려지고 뒤 반쪽만 남아 **문항의 머리가 잘린다** --
    그리고 잘린 문항으로 만든 질문은 사용자에게 엉뚱한 것을 묻는다.

    그래서 **먼저 공백을 눕히고, 끝나는 자리(어미 · `(700자)`)로 자른다.** 시작은
    바로 앞의 번호 표시(`1.` · `Q2)`)이거나 앞 문항이 끝난 자리다.
    """
    평 = re.sub(r"\s+", " ", 글 or "").strip()
    번호자리 = [m.start() for m in re.finditer(r"(?:(?<=\s)|^)(?:Q\s*)?\d{1,2}\s*[.)]\s", 평)]
    out, 본것, 앞 = [], set(), 0
    오늘 = date.today().isoformat()
    for 끝 in _끝자리(평):
        시작 = max([앞] + [b for b in 번호자리 if b < 끝])
        조각 = 평[시작:끝].strip(" .·-")
        앞 = 끝
        m = _번호.match(조각)
        번호 = m.group(1) if m else ""
        본문 = (조각[m.end():] if m else 조각).strip()
        if not (12 <= len(본문) <= 400) or _잡말.search(본문) or 본문 in 본것:
            continue
        본것.add(본문)
        out.append(받은문항(글=본문, 출처=출처, 받은날=오늘, 회사=회사, 번호=번호))
    return out


def _이름(출처: str) -> str:
    host = urllib.parse.urlsplit(출처).netloc or "손으로"
    h = hashlib.sha1(출처.encode("utf-8")).hexdigest()[:8]
    return f"{re.sub(r'[^A-Za-z0-9.-]', '_', host)}_{h}.json"


def 담기(것들: list, dir: Path | None = None) -> Path | None:
    """받은 문항을 원장에 담는다. **출처 없는 것은 뺀다.**"""
    것들 = [q for q in 것들 if q.출처.strip()]
    if not 것들:
        return None
    d = Path(dir or 문항DIR)
    d.mkdir(parents=True, exist_ok=True)
    p = d / _이름(것들[0].출처)
    p.write_text(json.dumps(
        {"출처": 것들[0].출처, "받은날": 것들[0].받은날, "회사": 것들[0].회사,
         "문항": [{"글": q.글, "번호": q.번호} for q in 것들]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def 읽기(dir: Path | None = None) -> 원장:
    """원장 디렉터리를 읽는다. **없으면 빈 원장이다 -- 예외가 아니다.**"""
    d = Path(dir or 문항DIR)
    out = []
    if d.is_dir():
        for p in sorted(d.glob("*.json")):
            try:
                x = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            출처 = str(x.get("출처") or "")
            if not 출처.strip():                 # 출처 없는 파일은 통째로 뺀다
                continue
            for q in (x.get("문항") or []):
                글 = str((q or {}).get("글") or "").strip()
                if 글:
                    out.append(받은문항(글=글, 출처=출처,
                                      받은날=str(x.get("받은날") or ""),
                                      회사=str(x.get("회사") or ""),
                                      번호=str((q or {}).get("번호") or "")))
    return 원장(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="문항 원장을 본다")
    ap.add_argument("--곳", default=str(문항DIR))
    ap.add_argument("--찾", dest="찾", default="")
    ap.add_argument("--갈래", action="store_true")
    a = ap.parse_args(argv)

    L = 읽기(a.곳)
    if not L:
        print(f"문항 원장이 비어 있다: {a.곳}\n"
              "  python3 jaso/fetch.py --질의 '2026 자기소개서 문항' 로 받아라\n"
              "  (**이 컨테이너는 나가는 길이 막혀 있다** -- VM 에서 돌려라)",
              file=sys.stderr)
        return 3
    보일것 = L.찾기(a.찾) if a.찾 else L.문항들
    print(f"문항 {len(L)}개 · 출처 {len({q.출처 for q in L.문항들})}곳"
          + (f" · '{a.찾}' 든 것 {len(보일것)}개" if a.찾 else ""))
    if a.갈래:
        for 종류, qs in sorted(L.갈래별().items(), key=lambda x: -len(x[1])):
            print(f"  {종류:<8}{len(qs):>4}개")
        return 0
    for q in 보일것[:40]:
        s = q.쪼갠것()
        칸 = f"{s.상한}자" if s.상한 else "글자 수 없음"
        print(f"\n[{q.id}] {칸} · 요구 {s.쪼갬}개 · {urllib.parse.urlsplit(q.출처).netloc}")
        print(f"  {q.글[:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
