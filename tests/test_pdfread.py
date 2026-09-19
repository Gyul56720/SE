# -*- coding: utf-8 -*-
"""큰 PDF 를 **실제로 읽어** 본다.

## 왜 있나 (실측 2026-09-19)

사용자가 2000 쪽짜리 PDF 를 봇에 줬다. 봇은 `read_image` 를 불렀고 그것은 PDF 를
통째로 모델에 실어 보낸다. 돌아온 것:

    The input token count exceeds the maximum number of tokens allowed

그러자 봇은 **"텍스트를 복사해 붙여넣거나 페이지별 스크린샷으로 나눠 올려
달라"** 고 답했다. 도구가 없어서가 아니라 **쓰지 않아서**였고, 사람에게 일을
떠넘긴 것이다(CLAUDE.md '사람에게 설치를 시키지 마라' 와 같은 병).

바이트 상한(20 MB)은 통과했다 -- **토큰은 바이트가 아니다**. 그래서 쪽수로 막고,
글은 로컬에서 뽑는다.

이 검사는 저장소에 있는 **진짜 594 쪽 PDF** 로 네 가지를 본다:

    1. 훑기가 쪽수와 목차를 낸다
    2. 찾기가 그 말이 나오는 쪽을 집는다
    3. 읽기가 그 범위만 준다
    4. **read_image 가 큰 PDF 를 통째로 안 보낸다** -- 이것이 원래 버그다
"""
import os
import shutil
import subprocess
import sys
import tempfile
import pytest

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 뿌리)

쪽PDF = os.path.join(뿌리, "survey", "HLS_IP_Specification.pdf")
도구있나 = all(shutil.which(x) for x in ("pdfinfo", "pdftotext"))
pytestmark = pytest.mark.skipif(
    not (도구있나 and os.path.exists(쪽PDF)),
    reason="poppler-utils 또는 시험용 PDF 가 없다")


def test_훑기가_쪽수와_목차를_낸다():
    import pdfread
    r = pdfread.훑기(쪽PDF, repo=뿌리)
    assert "594" in r, r[:300]
    assert "쪽" in r
    assert "목차" in r, "목차를 못 뽑았다"
    # 적어도 몇 개는 나와야 한다 -- 0 개면 뽑기가 안 도는 것이다
    번호줄 = [l for l in r.splitlines() if l.strip()[:1].isdigit() and ":" in l]
    assert len(번호줄) >= 5, f"목차 줄이 {len(번호줄)}개뿐이다\n{r[:600]}"
    assert "read_pdf" in r, "어떻게 더 읽는지 안 알려 준다"


def test_찾기가_그_말이_나오는_쪽만_집는다():
    import pdfread
    r = pdfread.찾기(쪽PDF, "Cholesky", repo=뿌리, 최대=3)
    assert "못 찾았다" not in r, r[:300]
    assert "쪽에서 나왔다" in r
    assert "--- " in r and " 쪽 ---" in r, "앞뒤 줄을 안 준다"
    assert "cholesky" in r.lower()


def test_없는_말은_없다고_한다():
    """**못 찾은 것을 찾은 척하지 않는다.**"""
    import pdfread
    r = pdfread.찾기(쪽PDF, "zzzqqq없을말xyzzy", repo=뿌리)
    assert "못 찾았다" in r, r[:300]
    assert "글층은 있다" in r, "글층이 있는지도 안 알려 준다"


def test_읽기가_범위만_준다():
    import pdfread
    r = pdfread.읽기(쪽PDF, "13-14", repo=뿌리)
    assert "13-14 쪽" in r, r[:200]
    assert len(r) > 500
    r2 = pdfread.읽기(쪽PDF, "13", repo=뿌리)
    assert len(r2) < len(r), "한 쪽이 두 쪽보다 길다 -- 범위가 안 먹는다"


def test_쪽수_상한이_있다():
    """한 번에 다 주지 않는다 -- 주면 부르는 쪽에서 다시 터진다."""
    import pdfread
    r = pdfread.읽기(쪽PDF, "1-500", repo=뿌리)
    assert f"1-{pdfread.쪽최대}" in r, r[:200]
    assert "다시 불러라" in r


def test_틀린_쪽_지정은_틀렸다고_한다():
    import pdfread
    assert "쪽 지정 틀림" in pdfread.읽기(쪽PDF, "가나다", repo=뿌리)
    assert "쪽 지정 틀림" in pdfread.읽기(쪽PDF, "9999", repo=뿌리)
    assert "PDF 없음" in pdfread.읽기("없는파일.pdf", repo=뿌리)
    assert "PDF 아님" in pdfread.읽기("CLAUDE.md", repo=뿌리)


def test_read_image_가_큰_PDF_를_통째로_안_보낸다():
    """**이것이 원래 버그다.**

    큰 PDF 를 read_image 에 주면 모델에 실어 보내지 말고, 어떻게 읽으면 되는지
    돌려줘야 한다. 이 검사는 네트워크를 쓰지 않는다 -- 통째로 보내려 했다면
    llm_pool 을 부르다 실패하거나 시간이 오래 걸렸을 것이고, 여기서는 즉시
    안내문이 나와야 한다.
    """
    import imageread
    r = imageread.읽기(쪽PDF, repo=뿌리)
    assert "통째로 안 보낸다" in r, r[:400]
    assert "594" in r
    assert "read_pdf" in r, "대신 무엇을 쓰라는 말이 없다"
    assert "그림 못 읽음" not in r, "모델을 부르려 했다"


def test_작은_PDF_는_예전대로_그림으로_간다():
    """몇 쪽짜리(문제지 사진 같은 것)는 시각 모델로 보내는 길이 살아 있어야 한다.

    막는 것은 쉽고, **막기만 하면 원래 되던 것이 죽는다.**  그래서 두 방향을
    다 본다: 큰 것은 막히고 작은 것은 통과한다.
    """
    import pathlib
    import imageread
    if not (shutil.which("pdfseparate") and shutil.which("pdfunite")):
        pytest.skip("pdfseparate/pdfunite 가 없다 -- 작은 PDF 를 못 만든다")
    d = tempfile.mkdtemp(prefix="smallpdf_")
    try:
        r = subprocess.run(["pdfseparate", "-f", "1", "-l", "2", 쪽PDF,
                            os.path.join(d, "p-%d.pdf")],
                           capture_output=True, timeout=300)
        조각 = sorted(os.path.join(d, f) for f in os.listdir(d)
                    if f.startswith("p-") and f.endswith(".pdf"))
        assert 조각, f"쪽을 못 잘랐다: {r.stderr[:200]}"
        작은 = os.path.join(d, "작은.pdf")
        r = subprocess.run(["pdfunite"] + 조각 + [작은],
                           capture_output=True, timeout=300)
        assert os.path.exists(작은), f"합치지 못했다: {r.stderr[:200]}"
        판정 = imageread._큰PDF인가(pathlib.Path(작은))
        assert 판정 is None, f"{len(조각)} 쪽짜리를 크다고 했다: {판정}"
        # 그리고 큰 것은 여전히 막혀야 한다
        막힘 = imageread._큰PDF인가(pathlib.Path(쪽PDF))
        assert 막힘 and "594" in 막힘, f"큰 PDF 가 안 막혔다: {막힘}"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_부르기가_모드를_알아서_고른다():
    import pdfread
    assert "쪽에서 나왔다" in pdfread.부르기(쪽PDF, 물음="Cholesky", repo=뿌리)
    assert "13-14 쪽" in pdfread.부르기(쪽PDF, 쪽="13-14", repo=뿌리)
    assert "목차" in pdfread.부르기(쪽PDF, repo=뿌리)
    assert "모드 모름" in pdfread.부르기(쪽PDF, 모드="없는모드", repo=뿌리)


if __name__ == "__main__":
    import sys as _s, os as _o
    _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
    import _run
    _run.돌리기(globals())
