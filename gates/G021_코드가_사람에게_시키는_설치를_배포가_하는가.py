"""
G021 -- 코드가 **사람에게 시키는 설치**를 배포가 하는가.

사용자(2026-09-12), 같은 말을 세 번: "사람 몫으로 넘기는 건 최종이라고." · "그 판단을 왜
스스로 못하냐고." · "한글 폰트를 확인하는 것도 머지가 필요해?"

실측 2026-09-12: `investigate/discord_pdf.py` 가 한글 글꼴이 없으면 사용자에게
`sudo apt-get install -y fonts-nanum` 을 하라고 말한다. 그런데 `deploy-oracle.yml` 은
그 꾸러미를 깔지 않는다. 그래서 **기능이 될지 안 될지를 코드가 모르고**, 그 물음이 사람에게
갔다 -- "VM 에 글꼴이 있나요?" 읽기만 하는 `ls` 한 줄인데도 사람이 했다.

꾸러미를 배포가 깔면 그 물음 자체가 없어진다. 코드가 기대는 것을 코드가 깔기 때문이다.

## 무엇을 위반으로 보는가

저장소의 `.py` 가 `apt-get install <꾸러미>` (또는 `apt install`) 를 **글로 담고 있는데**
배포 워크플로에 그 꾸러미 이름이 없는 경우. 사람에게 시킬 설치라면 배포가 할 수 있다.

## 무엇을 안 잡는가 -- 그리고 왜

  · `tests/` 와 `gates/` 는 안 본다 -- 서버에서 도는 코드가 아니다(이 게이트 자신을 포함)
  · pip 으로 깔리는 것은 안 본다 -- `requirements.txt` 가 그 자리다(배포가 이미 깐다)
  · 배포 워크플로가 없는 저장소는 넘어간다
  · **`# G021: 사람 몫` 을 그 줄에 달면 넘어간다.** 기계가 못 하는 설치가 있다(유료 키,
    하드웨어). 다만 **눈에 보이게** 고르게 한다 -- 조용히 넘기는 것과 적어 두고 넘기는
    것은 다르다

## 왜 검출기가 아니라 게이트인가

이 저장소가 앓은 병은 늘 같은 것이다: **기능은 좋아졌는데 그 기능이 도는 기계에 닿지
못한다**(G013 이 배포 트리거로 막은 것과 같은 병의 다른 얼굴이다). 거기에 하나가 더
붙는다 -- 닿았는지를 **사람에게 물어서** 알아낸다. 그 물음을 없앤다.
"""
from __future__ import annotations

import re

RULE_ID = "G021"
TITLE = "코드가 사람에게 시키는 설치를 배포가 하는가"
ORIGIN = "2026-09-12 fonts-nanum (discord_pdf 가 사람에게 apt 를 시키고 배포는 안 깔았다)"
OPT_OUT = "G021: 사람 몫"

_워크플로들 = (".github/workflows/deploy-oracle.yml",)
_안보는곳 = ("tests", "gates")
# `apt-get install -y fonts-nanum` · `apt install fonts-nanum` · sudo 붙은 것 모두.
_APT = re.compile(r"\bapt(?:-get)?\s+install\s+((?:-[A-Za-z-]+\s+)*)([A-Za-z0-9][A-Za-z0-9.+_-]*)")


def _배포글(repo) -> "str | None":
    """배포 워크플로들의 글을 이어 붙인 것. 하나도 없으면 None."""
    조각 = []
    for rel in _워크플로들:
        p = repo / rel
        if p.is_file():
            조각.append(p.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(조각) if 조각 else None


def _시키는것(ctx) -> "list[tuple[str, int, str]]":
    """(상대경로, 줄번호, 꾸러미) 목록 -- 코드가 사람에게 깔라고 하는 것들."""
    out = []
    for path in ctx.python_files():
        rel = ctx.rel(path)
        if any(part in _안보는곳 for part in rel.split("/")[:-1]) or rel.split("/")[0] in _안보는곳:
            continue
        try:
            본 = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "apt" not in 본:
            continue
        for n, 줄 in enumerate(본.splitlines(), 1):
            if OPT_OUT in 줄:
                continue
            for m in _APT.finditer(줄):
                out.append((rel, n, m.group(2)))
    return out


def check(ctx) -> "list[str]":
    배포 = _배포글(ctx.repo)
    if 배포 is None:
        return []                                  # 배포 워크플로가 없는 저장소 -- 할 일 없음
    위반 = []
    for rel, n, 꾸러미 in _시키는것(ctx):
        if 꾸러미 in 배포:
            continue
        위반.append(
            f"{rel}:{n}: 코드가 사람에게 `apt install {꾸러미}` 를 시키는데 배포가 그것을 "
            f"깔지 않는다 -- 기능이 그 기계에서 될지를 코드가 모르고, 그 물음이 사람에게 간다. "
            f"{_워크플로들[0]} 의 설치 단계에 {꾸러미} 를 넣어라 "
            f"(기계가 못 하는 설치라면 그 줄에 `# {OPT_OUT}` 를 달아라).")
    return 위반
