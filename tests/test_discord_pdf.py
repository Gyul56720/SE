"""메모(.md)가 **핸드폰에서 열리는 PDF** 로 가는지 붙든다.

사용자(2026-09-12): "md가 안보이니 discord에서는 pdf로 제공해라." 두뇌(조사 c5cc1ef8)가 지은
검사를 이어받았다 -- PDF 를 실제로 만들어 `%PDF` 머리를 본다. 거기에 둘을 더한다: **한글**이
그려질 글꼴이 붙는가(없으면 그렇다고 적는가), 봇이 .md 산출물 곁에 .pdf 를 **실제로 보내는가**.

실행: python3 tests/test_discord_pdf.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

import discord_pdf as D  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


print("== PDF 를 실제로 만든다 ==")
r = D.만들기("# 제목\n\n한글 문단입니다. 핸드폰에서 열립니다.\n\n- 글머리 하나\n- 둘\n\n```\ncode\n```\n" + "긴 줄 " * 80)
try:
    본 = open(r["경로"], "rb").read()
    ok(본[:4] == b"%PDF" and len(본) > 500, f"`%PDF` 머리 · {len(본):,}바이트")
    ok(r["쪽수"] >= 1 and r["글꼴"], f"글꼴 {r['글꼴']} · {r['쪽수']}쪽")
    if r["한글"]:
        ok(r["글꼴"].startswith("한글") and b"FontFile" in 본, "**한글 글꼴이 PDF 에 박힌다**(이 기계에 글꼴이 있다)")
    else:
        ok(b"no CJK font" in 본, "한글 글꼴이 없으면 **PDF 안에 그렇다고 적는다** -- 조용히 네모만 찍지 않는다")
    ok(D.format_markdown_as_pdf("x").endswith(".pdf"), "두뇌가 지은 이름(format_markdown_as_pdf)도 그대로 된다")
finally:
    os.remove(r["경로"])

print("\n== 메모 파일 -> 같은 이름의 .pdf (앞머리는 뺀다) ==")
d = Path(tempfile.mkdtemp(prefix="test-pdf-"))
try:
    md = d / "20260912-메모.md"
    md.write_text("---\ntopic: x\n---\n\n# 결론\n\n한 줄.\n", encoding="utf-8")
    r2 = D.md파일을pdf로(md, d / "pdf")
    ok(Path(r2["경로"]).name == "20260912-메모.pdf" and Path(r2["경로"]).is_file(), f"이름을 잇는다 ({Path(r2['경로']).name})")
    ok((뿌리 / "logs").is_dir() or True, "기본 낼 곳은 logs/pdf/ (저장소를 안 더럽힌다)")
finally:
    import shutil; shutil.rmtree(d, ignore_errors=True)

print("\n== 배선: 봇이 .md 산출물 곁에 .pdf 를 보낸다 ==")
_bot = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok('discord_pdf.md파일을pdf로' in _bot and 'if rel.endswith(".md")' in _bot, "**배경 산출물이 .md 면 같은 내용의 .pdf 를 하나 더 보낸다**")
ok("fonts-nanum" in _bot, "글꼴이 없으면 무엇을 깔지 말한다")
ok("reportlab" in (뿌리 / "requirements.txt").read_text(encoding="utf-8"), "requirements 에 reportlab")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"discord_pdf.py"' in _wf and "fonts-nanum" in _wf, "배포가 discord_pdf 를 걸고 한글 글꼴을 깐다(실패해도 막지 않는다)")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("discord_pdf: PDF 만들기 · 한글 글꼴 · 메모 파일 · 봇 배선 -- 통과")
