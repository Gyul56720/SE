"""**첫 쪽을 재는 자.** 실제 1화를 여기 넣고 우리 1화와 견준다.

사용자(2026-09-09): "게시글을 읽지말고, 실제 1화를 가져와 일본 라노벨이나 한국 웹소설."

**이 세션에서는 그것을 못 했다.** 소설이 올라와 있는 자리가 전부 막혀 있다 --
ncode.syosetu.com · kakuyomu.jp · novelpia.com · munpia · naver · kakao · joara ·
alphapolis · 심지어 wikipedia 까지 나가는 길에서 거절됐다(실측 2026-09-09, 위 열넷을
전부 두드려 봤다). 검색은 되지만 돌아오는 것은 **줄거리 요약과 조언글**이고, 그것이
사용자가 읽지 말라고 한 바로 그것이다.

그래서 지어내지 않는다. 대신 **자를 만든다.** 실제 1화를 손에 넣을 수 있는 쪽은
사용자다 -- 파일로 떨궈 주면 이 모듈이 그것을 재고, 우리 원고의 첫 회차를 같은 자로
재서 나란히 놓는다. 그 다음에 숫자를 보고 `targets.json` 을 고친다. 이 저장소의 규율
그대로다: **잰 것만 프롬프트에 싣는다.**

    python3 -m novel.first 실제1화.txt 우리1화.txt

## 무엇을 재나

`profile.measure` 는 토막 전체의 비율을 잰다. 첫 쪽에서 갈리는 것은 그것과 다르다 --
**독자가 몇 자를 견뎌야 첫 대사가 나오는가**, 첫 문장이 긴가 짧은가, 앞머리에 이름을
몇 개나 던지는가. 이탈은 거기서 난다. 그래서 앞 `HEAD` 자만 따로 잰다.

여기 밴드(있어야 할 폭)를 적지 않는다. 재기 전에 폭을 적으면 그것은 잰 것이 아니라
내 짐작이고, 이 저장소가 두 번 그것으로 틀렸다(액션 통째 싣기 · lanobe 대사 몫).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from novel import profile, rhythm

# 앞머리로 볼 자수. 웹소설 한 회차가 5,000자 안팎이고 이탈은 첫 화면에서 난다.
HEAD = 1500

# 대사의 시작. rhythm._QUOTE 에 일본 원문의 「 을 더했다 -- 이 자는 남의 1화도 잰다.
_TALK = re.compile(r"[\"“「『]")


def to_talk(text: str) -> int:
    """첫 대사가 나오기까지 독자가 읽어야 하는 자수. 대사가 없으면 글 전체 길이."""
    m = _TALK.search(text)
    return m.start() if m else len(text)


def first_len(text: str) -> int:
    """첫 문장의 길이. 첫 줄이 대사면 그 대사 줄의 길이다."""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if _TALK.match(line):
            return len(line)
        parts = [s for s in re.split(r"(?<=[.!?…])\s+", line) if s.strip()]
        return len(parts[0]) if parts else len(line)
    return 0


def measure(text: str, head: int = HEAD) -> dict:
    """첫 쪽의 프로필. 앞 `head` 자를 따로 재고, 글 전체 길이를 같이 준다."""
    text = text.strip()
    if not text:
        return {}
    top = text[:head]
    p = profile.measure(top) or {}
    # **없는 축을 0 으로 적지 않는다.** profile.measure 는 서술문이 하나도 없으면 빈
    # 것을 준다 -- 앞머리가 대사로만 열리는 1화가 그렇다. 그때 `p.get(k, 0.0)` 으로
    # 채우면 "대사 0.00" 이라고 **거짓으로** 답한다. 잘못 답하는 자는 없느니만 못하다
    # (pr_merged.sh 가 겪은 것). 그래서 대사 몫은 여기서 직접 세고, 서술이 있어야
    # 나오는 축은 **아예 빼서** 표에 "-" 로 뜨게 한다.
    tell, talk = rhythm._lines(top)
    out = {
        "to_talk":  to_talk(text),                   # 첫 대사까지 몇 자
        "first_len": first_len(text),                # 첫 문장 길이
        "dialog":   len(talk) / (len(tell) + len(talk)) if (tell or talk) else 0.0,
        "chars":    len(text),                       # 회차 전체 길이
    }
    for k in ("short", "da_share", "outside", "names", "sent_len"):
        if k in p:                                   # 앞머리 서술문에서만 나오는 축들
            out[k] = p[k]
    return out


_AXES = (("to_talk", "첫 대사까지", "{:,.0f}자"), ("first_len", "첫 문장", "{:.0f}자"),
         ("sent_len", "문장 길이", "{:.1f}자"), ("dialog", "대사 줄 몫", "{:.2f}"),
         ("short", "짧은 문장", "{:.2f}"), ("da_share", "-다 몫", "{:.2f}"),
         ("outside", "설명·수치", "{:.2f}"), ("names", "이름/천자", "{:.1f}"),
         ("chars", "회차 분량", "{:,.0f}자"))


def table(rows: list) -> str:
    """(이름, 프로필) 목록을 표로. 축이 줄이고 글이 칸이다 -- 실제 1화와 우리 것을
    **나란히** 놓고 어느 축이 얼마나 벌어졌는지 보려고 만든 것이다(profile.table 과 같은 꼴)."""
    out = ["  " + "축".ljust(12) + "".join(n[:10].rjust(12) for n, _ in rows)]
    out.append("  " + "-" * (12 + 12 * len(rows)))
    for k, label, f in _AXES:
        line = "  " + label.ljust(12)
        for _, m in rows:
            line += (f.format(m[k]) if k in m else "-").rjust(12)
        out.append(line)
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="첫 회차를 잰다. 실제 1화와 우리 1화를 견준다.")
    ap.add_argument("files", nargs="+", help="첫 회차가 든 텍스트 파일들")
    ap.add_argument("--head", type=int, default=HEAD, help=f"앞머리로 볼 자수 (기본 {HEAD})")
    a = ap.parse_args(argv)
    rows = []
    for f in a.files:
        p = Path(f)
        if not p.exists():
            print(f"없는 파일: {f}", file=sys.stderr)
            return 2
        m = measure(p.read_text(encoding="utf-8"), head=a.head)
        if not m:
            print(f"빈 파일: {f}", file=sys.stderr)
            return 2
        rows.append((p.stem, m))
    print(table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
