# -*- coding: utf-8 -*-
"""큰 PDF 를 **모델에 통째로 던지지 않고** 읽는다.

## 왜 있나 (실측 2026-09-19)

사용자가 2000 쪽짜리 PDF 를 봇에 줬다. 봇은 `read_image` 를 불렀고, 그것은 PDF
바이트를 통째로 inline_data 로 실어 보낸다. 돌아온 것은:

    The input token count exceeds the maximum number of tokens allowed

그리고 봇은 **"텍스트를 복사해 붙여넣거나 페이지별 스크린샷으로 나눠 올려
달라"** 고 답했다. 사용자에게 일을 떠넘긴 것이다 -- 이 저장소가 이미 한 번 배운
잘못이다(CLAUDE.md '사람에게 설치를 시키지 마라').

바이트 상한(20 MB)은 통과했다. **토큰은 바이트가 아니다.** PDF 한 쪽은 그림
한 장에 준하는 토큰을 먹으므로, 3 MB 짜리 600 쪽 문서가 한계를 훌쩍 넘는다.

## 무엇을 하나

PDF 는 **글이 들어 있는 파일**이다. 그림처럼 다룰 이유가 없다.

    훑기(path)              쪽수 · 글자수 · 제목 · 목차 · 글층이 있나
    읽기(path, 쪽="10-25")   그 쪽만 글로 뽑는다
    찾기(path, "RS(544")     **문서 전체를 뒤져 나온 쪽과 앞뒤를 준다**
    그림으로(path, 쪽=7)     그 쪽만 PNG 로 그려 모델에 보낸다 (스캔본·도면용)

`찾기` 가 2000 쪽 문서에서 실제로 쓰는 것이다. 사람이 "그 IP 스펙의 레지스터
맵" 을 물으면 전체를 읽을 이유가 없다 -- 그 말이 나오는 쪽만 읽으면 된다.

## 글층이 없으면

스캔본은 `pdftotext` 가 빈 문자열을 낸다. 그때만 `pdftoppm` 으로 **고른 쪽만**
PNG 로 그려 시각 모델에 보낸다. 통째로 보내지 않는다.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

쪽최대 = 40              # 한 번에 글로 돌려주는 쪽 수 상한
글자최대 = 60000         # 한 번에 돌려주는 글자 수 상한
그림쪽최대 = 8           # 한 번에 그림으로 보내는 쪽 수 상한


def _도구있나(이름: str) -> bool:
    return shutil.which(이름) is not None


def _쪽수(쪽: Path):
    r = subprocess.run(["pdfinfo", str(쪽)], capture_output=True, text=True,
                       timeout=120)
    if r.returncode:
        return None, (r.stderr or r.stdout).strip()[:200]
    info = {}
    for l in r.stdout.splitlines():
        if ":" in l:
            k, v = l.split(":", 1)
            info[k.strip()] = v.strip()
    try:
        return int(info.get("Pages", "0")), info
    except ValueError:
        return None, "Pages 를 못 읽었다"


def _쪽범위(쪽: str, 총: int):
    """'10-25' · '7' · '' 를 (처음, 끝) 으로. 범위를 넘으면 **잘라서 말한다**."""
    쪽 = (쪽 or "").strip()
    if not 쪽:
        return 1, min(쪽최대, 총), ""
    m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", 쪽)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
    elif 쪽.isdigit():
        a = b = int(쪽)
    else:
        return None, None, f"쪽 표기를 모르겠다: {쪽!r} -- '10-25' 나 '7' 처럼 써라"
    a = max(1, a)
    b = min(총, b)
    말 = ""
    if b - a + 1 > 쪽최대:
        b = a + 쪽최대 - 1
        말 = f" (한 번에 {쪽최대} 쪽까지만 -- 다음은 {b+1} 부터 다시 불러라)"
    if a > 총:
        return None, None, f"{총} 쪽짜리인데 {a} 쪽을 달라고 했다"
    return a, b, 말


def _글뽑기(쪽: Path, a: int, b: int, 레이아웃=True) -> str:
    cmd = ["pdftotext"]
    if 레이아웃:
        cmd.append("-layout")
    cmd += ["-f", str(a), "-l", str(b), str(쪽), "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return r.stdout


def 훑기(path: str, repo: str = "") -> str:
    """쪽수·글층·목차. **무엇을 어떻게 더 읽으면 되는지까지 말한다.**"""
    쪽 = _경로(path, repo)
    if isinstance(쪽, str):
        return 쪽
    if not _도구있나("pdfinfo"):
        return "[PDF 못 읽음] pdfinfo 가 없다 (poppler-utils)"
    총, info = _쪽수(쪽)
    if 총 is None:
        return f"[PDF 못 읽음] {쪽.name}: {info}"
    맛보기 = _글뽑기(쪽, 1, min(5, 총))
    글있나 = len(맛보기.strip()) > 80
    크기 = 쪽.stat().st_size
    줄 = [f"[{쪽.name}] {총:,} 쪽 · {크기/1024/1024:.1f} MB"]
    if isinstance(info, dict):
        for k in ("Title", "Author", "Producer", "Page size"):
            if info.get(k):
                줄.append(f"  {k}: {info[k]}")
    if not 글있나:
        줄 += ["", "**글층이 없다** (스캔본으로 보인다). 그림으로 읽어야 한다:",
              f"  read_pdf(path, 모드='그림', 쪽='1-4')   <- 한 번에 {그림쪽최대} 쪽까지"]
        return "\n".join(줄)
    전체 = _글뽑기(쪽, 1, 총, 레이아웃=False)
    줄.append(f"  글자 {len(전체):,}자 · 쪽당 평균 {len(전체)//max(총,1):,}자")
    # **한 번 뽑은 글을 다시 쓴다.**  처음에는 제목을 찾느라 200 쪽씩 다시
    # 뽑았고, 1791 쪽 문서에서 pdftotext 를 열 번 돌려 18.5 초가 걸렸다.
    # 같은 것을 두 번 뽑을 이유가 없다.
    제목들 = _제목찾기(전체.split("\f"))
    if 제목들:
        줄 += ["", f"목차로 보이는 줄 {len(제목들)}개 (쪽: 제목):"]
        for p, t in 제목들[:60]:
            줄.append(f"  {p:4d}: {t[:90]}")
        if len(제목들) > 60:
            줄.append(f"  ... 그리고 {len(제목들)-60}개 더")
    줄 += ["", "**통째로 읽지 마라.** 이렇게 쓴다:",
          "  read_pdf(path, 모드='찾기', 물음='RS(544,514)')   <- 그 말이 나오는 쪽만",
          "  read_pdf(path, 쪽='120-150')                      <- 그 범위만 글로",
          "  read_pdf(path, 모드='그림', 쪽='137')             <- 도면이면 그림으로"]
    return "\n".join(줄)


_제목꼴 = re.compile(
    r"^\s*((?:\d+(?:\.\d+)*|[A-Z]\d+(?:\.\d+)*|Appendix\s+[A-Z])"
    r"[.)]?\s+\S.{2,90})\s*$")


def _제목찾기(쪽글들):
    """번호가 붙은 줄을 목차로 본다. **없으면 없다고 한다** -- 지어내지 않는다.

    이미 뽑아 둔 쪽별 글을 받는다 -- 다시 뽑지 않는다.
    """
    out = []
    for i, 쪽글 in enumerate(쪽글들):
        p = i + 1
        for l in 쪽글.splitlines()[:6]:
            m = _제목꼴.match(l)
            if m:
                t = re.sub(r"\s+", " ", m.group(1)).strip()
                if len(t) > 4 and not t[-1].isdigit():
                    out.append((p, t))
                break
    # 같은 제목이 여러 쪽에 걸쳐 나오면(머리글) 첫 쪽만 남긴다
    본것, 추림 = set(), []
    for p, t in out:
        if t in 본것:
            continue
        본것.add(t)
        추림.append((p, t))
    return 추림


def 찾기(path: str, 물음: str, repo: str = "", 앞뒤: int = 3, 최대: int = 20) -> str:
    """문서 전체에서 말을 찾아 **나온 쪽과 앞뒤 줄**을 준다.

    2000 쪽 문서에서 실제로 쓰는 길이다. 통째로 읽는 대신 필요한 쪽만 집는다.
    """
    쪽 = _경로(path, repo)
    if isinstance(쪽, str):
        return 쪽
    물음 = (물음 or "").strip()
    if not 물음:
        return "[찾기] 무엇을 찾을지 안 줬다"
    총, info = _쪽수(쪽)
    if 총 is None:
        return f"[PDF 못 읽음] {쪽.name}: {info}"
    글 = _글뽑기(쪽, 1, 총, 레이아웃=False)
    쪽글들 = 글.split("\f")
    낮춤 = 물음.lower()
    맞은쪽 = []
    for i, 쪽글 in enumerate(쪽글들, 1):
        if 낮춤 in 쪽글.lower():
            맞은쪽.append(i)
    if not 맞은쪽:
        return (f"[{쪽.name}] {총:,} 쪽 전체에서 {물음!r} 를 **못 찾았다**. "
                f"글층은 있다(글자 {len(글):,}자) -- 표기가 다를 수 있으니 "
                f"더 짧은 말로 다시 찾아 보라")
    줄 = [f"[{쪽.name}] {물음!r}: {len(맞은쪽)} 쪽에서 나왔다 -- "
         f"{', '.join(str(p) for p in 맞은쪽[:30])}"
         + (" ..." if len(맞은쪽) > 30 else "")]
    for p in 맞은쪽[:최대]:
        쪽글 = 쪽글들[p - 1].splitlines()
        자리 = [i for i, l in enumerate(쪽글) if 낮춤 in l.lower()]
        줄.append("")
        줄.append(f"--- {p} 쪽 ---")
        본줄 = set()
        for i in 자리[:4]:
            for j in range(max(0, i - 앞뒤), min(len(쪽글), i + 앞뒤 + 1)):
                if j not in 본줄:
                    본줄.add(j)
        for j in sorted(본줄):
            줄.append("  " + 쪽글[j].rstrip()[:160])
    if len(맞은쪽) > 최대:
        줄 += ["", f"({len(맞은쪽)-최대} 쪽 더 있다. "
                   f"read_pdf(path, 쪽='<번호>') 로 그 쪽을 통째로 읽어라)"]
    return "\n".join(줄)


def 읽기(path: str, 쪽: str = "", repo: str = "") -> str:
    """고른 쪽만 글로. **범위를 안 주면 앞쪽만** 주고 어떻게 더 읽는지 말한다."""
    p = _경로(path, repo)
    if isinstance(p, str):
        return p
    총, info = _쪽수(p)
    if 총 is None:
        return f"[PDF 못 읽음] {p.name}: {info}"
    a, b, 말 = _쪽범위(쪽, 총)
    if a is None:
        return f"[쪽 지정 틀림] {말}"
    글 = _글뽑기(p, a, b)
    if len(글.strip()) < 40:
        return (f"[{p.name}] {a}-{b} 쪽에 글층이 없다 -- 스캔본이거나 도면이다. "
                f"read_pdf(path, 모드='그림', 쪽='{a}') 를 써라")
    잘렸나 = ""
    if len(글) > 글자최대:
        글 = 글[:글자최대]
        잘렸나 = f"\n\n[여기서 잘랐다 -- {글자최대:,}자 상한. 더 좁은 쪽 범위를 달라]"
    return (f"[{p.name}] {총:,} 쪽 중 {a}-{b} 쪽{말}\n"
            f"{'-'*60}\n{글}{잘렸나}")


def 그림으로(path: str, 쪽: str = "1", question: str = "", repo: str = "",
           해상도: int = 150) -> str:
    """고른 쪽만 PNG 로 그려 시각 모델에 보낸다. 스캔본·도면용."""
    import imageread
    p = _경로(path, repo)
    if isinstance(p, str):
        return p
    if not _도구있나("pdftoppm"):
        return "[PDF 못 읽음] pdftoppm 이 없다 (poppler-utils)"
    총, info = _쪽수(p)
    if 총 is None:
        return f"[PDF 못 읽음] {p.name}: {info}"
    a, b, 말 = _쪽범위(쪽, 총)
    if a is None:
        return f"[쪽 지정 틀림] {말}"
    if b - a + 1 > 그림쪽최대:
        b = a + 그림쪽최대 - 1
        말 = f" (그림은 한 번에 {그림쪽최대} 쪽까지)"
    d = tempfile.mkdtemp(prefix="pdfpng_")
    try:
        r = subprocess.run(["pdftoppm", "-png", "-r", str(해상도),
                            "-f", str(a), "-l", str(b), str(p),
                            os.path.join(d, "pg")],
                           capture_output=True, text=True, timeout=900)
        if r.returncode:
            return f"[PDF 못 그림] {(r.stderr or r.stdout)[:200]}"
        파일들 = sorted(f for f in os.listdir(d) if f.endswith(".png"))
        if not 파일들:
            return "[PDF 못 그림] PNG 가 안 나왔다"
        낸것 = [f"[{p.name}] {a}-{b} 쪽을 그림으로 읽는다{말}"]
        for f in 파일들:
            낸것.append(imageread.읽기(os.path.join(d, f), question, repo=repo))
        return "\n\n".join(낸것)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _경로(path: str, repo: str):
    뿌리 = repo or os.path.dirname(os.path.abspath(__file__))
    쪽 = Path(path)
    if not 쪽.is_absolute():
        쪽 = Path(뿌리) / path
    if not 쪽.is_file():
        return f"[PDF 없음] {쪽} -- 경로가 틀렸거나 첨부가 저장되지 않았다"
    if 쪽.suffix.lower() != ".pdf":
        return f"[PDF 아님] {쪽.name} -- read_pdf 는 .pdf 만 읽는다"
    return 쪽


def 부르기(path: str, 모드: str = "", 쪽: str = "", 물음: str = "",
         repo: str = "") -> str:
    """도구 하나로 네 가지를 한다. 모드를 안 주면 **알아서 고르고 그 이유를 말한다**."""
    모드 = (모드 or "").strip()
    물음 = (물음 or "").strip()
    if not 모드:
        if 물음:
            모드 = "찾기"
        elif 쪽:
            모드 = "읽기"
        else:
            모드 = "훑기"
    if 모드 in ("훑기", "outline", "info"):
        return 훑기(path, repo=repo)
    if 모드 in ("찾기", "search", "grep"):
        return 찾기(path, 물음, repo=repo)
    if 모드 in ("그림", "image", "render", "ocr"):
        return 그림으로(path, 쪽 or "1", 물음, repo=repo)
    if 모드 in ("읽기", "text", "read"):
        return 읽기(path, 쪽, repo=repo)
    return (f"[모드 모름] {모드!r} -- 훑기 · 찾기 · 읽기 · 그림 중 하나")
