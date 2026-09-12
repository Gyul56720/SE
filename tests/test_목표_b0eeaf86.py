"""[목표] md가 안보이니 discord에서는 pdf로 제공해라. 핸드폰에서 한글이 보이는 PDF 가 Discord 첨부로 와야 한다

검증 항목:
1. discord_pdf 모듈 존재 및 reportlab 연동
2. 한글 마크다운 텍스트 및 .md 파일에서 유효한 PDF (%PDF 헤더) 생성
3. discord_bot_server.py 에서 .md 산출물 시 .pdf 첨부 배선
4. requirements.txt 에 reportlab 등록
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# 1. 모듈 임포트 검증
try:
    import discord_pdf as D
except ImportError as e:
    raise AssertionError(f"discord_pdf 모듈을 찾을 수 없음: {e}") from e

# 2. 마크다운 -> PDF 변환 및 %PDF 헤더 검증
md_샘플 = """# 조사 결과 보고서

## 1. 개요
안녕하세요. 핸드폰 Discord 화면에서 한글이 정상적으로 보여야 합니다.

- 첫 번째 항목: 리포트랩 기반 변환
- 두 번째 항목: 나눔고딕 등 CJK 트루타입 폰트 임베딩

```python
def hello():
    print("한글 지원 PDF 생성 성공")
```
"""

r = D.만들기(md_샘플)
pdf_경로 = r.get("경로")
assert pdf_경로 and os.path.exists(pdf_경로), f"PDF 파일이 생성되지 않음: {pdf_경로}"

try:
    with open(pdf_경로, "rb") as f:
        pdf_바이트 = f.read()
    assert pdf_바이트.startswith(b"%PDF"), f"PDF 헤더(%PDF)가 올바르지 않음: {pdf_바이트[:10]}"
    assert len(pdf_바이트) > 500, f"PDF 내용이 너무 작음: {len(pdf_바이트)} bytes"
    assert r.get("쪽수", 0) >= 1, "쪽수가 1 이상이어야 함"
finally:
    if os.path.exists(pdf_경로):
        os.remove(pdf_경로)

# 3. md파일을pdf로 함수 및 파일 변환 검증
d = Path(tempfile.mkdtemp(prefix="test-md-pdf-"))
try:
    md_파일 = d / "테스트_결론.md"
    md_파일.write_text("---\ntopic: test\n---\n\n# 결론\n\n핸드폰에서 한글이 보이는 PDF입니다.\n", encoding="utf-8")
    r2 = D.md파일을pdf로(md_파일, d / "pdf")
    생성된_pdf = Path(r2["경로"])
    assert 생성된_pdf.is_file(), f"md파일을pdf로 생성 실패: {생성된_pdf}"
    assert 생성된_pdf.name == "테스트_결론.pdf", f"PDF 파일명이 맞지 않음: {생성된_pdf.name}"
    with open(생성된_pdf, "rb") as f:
        pdf_data = f.read()
    assert pdf_data.startswith(b"%PDF"), "생성된 PDF 헤더가 올바르지 않음"
finally:
    import shutil
    shutil.rmtree(d, ignore_errors=True)

# 4. 배선 확인: discord_bot_server.py 및 requirements.txt
bot_code = (REPO / "discord_bot_server.py").read_text(encoding="utf-8")
assert "discord_pdf.md파일을pdf로" in bot_code, "discord_bot_server.py에 discord_pdf.md파일을pdf로 호출이 있어야 함"
assert 'rel.endswith(".md")' in bot_code, "discord_bot_server.py에 .md 산출물 분기 처리가 있어야 함"

reqs = (REPO / "requirements.txt").read_text(encoding="utf-8")
assert "reportlab" in reqs, "requirements.txt에 reportlab이 등록되어 있어야 함"

print("test_목표_b0eeaf86: 통과")
