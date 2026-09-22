# -*- coding: utf-8 -*-
"""**디스코드 2000자 벽을 넘겨 스펙을 받는다.**

사용자(2026-09-22): "2000자 제한 때문에 스펙이 전부 안들어가 이건 어떻게 해결해야할까?"

디스코드 한 메시지는 2000자다(니트로 없으면). 진짜 IP 요구사항서는 그보다 길다 --
2026-09-21 에 받은 MERA HAS 편지가 4천 자가 넘었다. 그래서 잘려 들어오고, 잘린
스펙으로 지은 제안서는 **틀린 제안서**다. 게다가 어디가 잘렸는지 아무도 모른다.

**첨부 파일에는 그 벽이 없다.** `spec.md` 를 끌어다 놓으면 8 MB 까지 들어온다.
그러니 벽을 넘기는 방법은 "나눠서 붙여넣기" 가 아니라 **"파일로 준다"** 이다.

여기서 하는 일은 하나뿐이다 -- **첨부의 글을 꺼내 요청 글에 이어 붙인다.**
잘라야 하면 **잘랐다고 적는다**(`글자최대`). 말없이 자르는 것이 이 벽의 병이다.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# 글로 읽는 꼴. **바이너리는 안 읽는다** -- 깨진 바이트를 프롬프트에 붙이면
# 모델이 그것을 스펙으로 읽는다(실측 2026-09-15 의 PNG `cat` 사고와 같은 꼴).
글꼴 = (".txt", ".md", ".markdown", ".rst", ".csv", ".tsv", ".json", ".yaml", ".yml",
      ".v", ".sv", ".svh", ".vh", ".vhd", ".py", ".c", ".h", ".cpp", ".tcl", ".xdc",
      ".sdc", ".log", ".ini", ".cfg", ".toml")
PDF꼴 = (".pdf",)

글자최대 = 60_000        # 한 요청에 붙일 수 있는 첨부 글의 총량
파일당최대 = 40_000


def 읽을수있나(경로) -> bool:
    return Path(경로).suffix.lower() in 글꼴 + PDF꼴


def 한파일(경로, 상한: int = 파일당최대) -> "tuple[str, str]":
    """(글, 까닭). 못 읽으면 글이 빈다. **잘랐으면 글 끝에 적는다.**"""
    p = Path(경로)
    꼬 = p.suffix.lower()
    if not p.exists():
        return "", f"없다: {p.name}"
    if 꼬 in PDF꼴:
        try:
            import pdfread
            글 = pdfread.읽기(str(p))
        except Exception as e:                               # noqa: BLE001
            return "", f"PDF 를 못 읽었다 ({type(e).__name__}: {e})"
        if 글.startswith("[") and "못 읽음" in 글[:40]:
            return "", 글[:120]
        return 글[:상한] + ("" if len(글) <= 상한 else
                          f"\n[여기서 잘랐다 -- {상한:,}자 상한]"), ""
    if 꼬 not in 글꼴:
        return "", f"글로 못 읽는 꼴이다: {꼬 or '(확장자 없음)'}"
    try:
        글 = p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return "", f"못 열었다: {e}"
    if not 글.strip():
        return "", "비어 있다"
    return 글[:상한] + ("" if len(글) <= 상한 else
                      f"\n[여기서 잘랐다 -- {상한:,}자 상한]"), ""


def 붙이기(본문: str, 첨부들, 상한: int = 글자최대) -> "tuple[str, list]":
    """(이어 붙인 글, 적을 말들). 첨부가 없으면 본문 그대로.

    **잘린 것을 말없이 넘기지 않는다** -- 무엇을 몇 자 읽었고 무엇을 왜 못 읽었는지
    돌려준다. 부르는 쪽이 그것을 사람에게 보인다.
    """
    본문 = 본문 or ""
    말 = []
    덩이 = []
    남 = 상한
    for a in (첨부들 or []):
        이름 = Path(a).name
        글, 까닭 = 한파일(a, min(파일당최대, max(남, 0)))
        if not 글:
            말.append(f"`{이름}` 못 읽음 — {까닭}")
            continue
        덩이.append(f"\n\n----- 첨부: {이름} -----\n{글}")
        남 -= len(글)
        말.append(f"`{이름}` {len(글):,}자 읽음")
        if 남 <= 0:
            말.append(f"**총 {상한:,}자 상한에 닿아 나머지 첨부는 안 읽었다**")
            break
    return 본문 + "".join(덩이), 말
