"""
5. 딥다이브 리뷰 Agent (선택적, 배치 파이프라인과 별개)

analyzer.py는 초록만 보고 JSON 스키마로 짧게 요약한다 (24편 전부를 훑는 1차 스캔용).
이 모듈은 그 반대: 논문 한 편을 지정하면 PDF 원문 전체를 받아와서, 자유 형식
장문 프롬프트로 Gemini에게 챕터 구성의 서술형 리뷰를 쓰게 한다.

파이프라인: Survey Notes(짧은 노트 24편)에서 논문을 "뽑아서" -> 그 논문 metadata
(제목/arxiv_id)를 그대로 써서 딥리뷰. Survey Notes에 없는 새 논문도 그대로 지원.

  python deep_review.py --list                         Survey Notes 목록 번호 보기
  python deep_review.py --index 3 --angle "..."         목록의 3번 논문으로 딥리뷰
  python deep_review.py "TPU v4" --angle "..."          Survey Notes에서 제목 부분일치 검색 후 딥리뷰
  python deep_review.py "새로운 논문 제목"                Survey Notes에 없으면 arXiv 직접 검색으로 폴백
  python deep_review.py --arxiv-id 1704.04760 --angle "메모리 병목 관점에서"
  python deep_review.py --pdf ./my_paper.pdf --angle "학부생도 이해하는 눈높이로"

PDF 원문에 없는 내용을 지어내지 말라고 프롬프트에서 명시적으로 못 박아서,
자유서술이라도 논문에 실제로 없는 수치를 만들어내는 걸 최대한 억제한다.
"""

from __future__ import annotations
import argparse
import re
from io import BytesIO
from pathlib import Path

import requests
from pypdf import PdfReader

import gemini_client
from config import OBSIDIAN_VAULT_PATH, note_folder
from sources import arxiv_source, unpaywall

MAX_CHARS = 400_000  # 안전 상한 (대략 10만 토큰대) -- 대부분의 논문 전문은 이 안에 들어옴


def _slugify(title: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", title).strip()
    slug = re.sub(r"[\s]+", " ", slug)[:80]
    return slug


def _parse_frontmatter(path: Path) -> dict | None:
    """organizer.py가 쓴 노트의 --- ... --- 프론트매터를 간단히 파싱 (key: value 한 줄씩)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end]
    fm: dict = {}
    for line in block.strip().splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip().strip('"')
    fm["_path"] = path
    return fm


def list_survey_notes(survey_notes_path: Path) -> list[dict]:
    """Survey Notes 폴더의 모든 노트를 (제목/연도/arxiv_id 등) 읽어온다."""
    if not survey_notes_path.exists():
        return []
    notes = []
    for f in sorted(survey_notes_path.glob("*.md")):
        fm = _parse_frontmatter(f)
        if fm and fm.get("title"):
            notes.append(fm)
    return notes


def print_survey_notes(notes: list[dict], survey_notes_path: Path) -> None:
    if not notes:
        print(f"[알림] Survey Notes 폴더({survey_notes_path})가 비어 있다. 먼저 main.py로 수집부터 할 것.")
        return
    for i, n in enumerate(notes, 1):
        has_arxiv = "arxiv" if n.get("arxiv_id") else "doi만"
        print(f"  [{i}] {n['title']} ({n.get('year', '?')})  [{has_arxiv}]")


def find_survey_note(query: str, notes: list[dict]) -> dict | None:
    """제목 부분일치(대소문자 무시)로 Survey Notes 중 하나를 찾는다."""
    query_l = query.lower()
    matches = [n for n in notes if query_l in n.get("title", "").lower()]
    if not matches:
        return None
    if len(matches) > 1:
        print(f"[알림] '{query}'로 {len(matches)}건 매칭됨, 첫 번째 사용: {matches[0]['title']}")
    return matches[0]


def _note_to_paper(note: dict) -> arxiv_source.Paper | None:
    """Survey Note의 arxiv_id로 PDF URL을 바로 구성. arxiv_id가 없으면 doi로 Unpaywall
    합법 오픈액세스 조회를 폴백으로 시도한다. 둘 다 없으면 None (호출부가 --pdf 안내)."""
    arxiv_id = note.get("arxiv_id", "")
    if arxiv_id:
        return arxiv_source.Paper(
            title=note["title"],
            year=int(note.get("year", 0) or 0),
            arxiv_id=arxiv_id,
            pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
            source="survey-note",
        )
    doi = note.get("doi", "")
    if doi:
        oa_url = unpaywall.find_oa_pdf_url(doi)
        if oa_url:
            print(f"[Unpaywall] '{note['title']}' 합법 오픈액세스 사본 발견: {oa_url}")
            return arxiv_source.Paper(
                title=note["title"],
                year=int(note.get("year", 0) or 0),
                arxiv_id="",
                doi=doi,
                pdf_url=oa_url,
                source="unpaywall",
            )
    return None


def resolve_paper(keyword: str | None, arxiv_id: str | None, index: int | None,
                   survey_notes_path: Path) -> arxiv_source.Paper:
    """우선순위: --index > --arxiv-id > Survey Notes 제목 매칭 > arXiv 원격 검색(폴백)."""
    notes = list_survey_notes(survey_notes_path)

    if index is not None:
        if not (1 <= index <= len(notes)):
            raise RuntimeError(f"--index {index}는 범위 밖이다 (1~{len(notes)}). --list로 목록 확인할 것.")
        note = notes[index - 1]
        paper = _note_to_paper(note)
        if paper:
            print(f"[Survey Notes #{index}] {paper.title} ({paper.year}) -- arxiv:{paper.arxiv_id}")
            return paper
        raise RuntimeError(f"'{note['title']}'는 arxiv_id도 없고 Unpaywall에서도 오픈액세스 사본을 못 찾았다. "
                           f"--pdf로 직접 지정할 것.")

    if arxiv_id:
        results = arxiv_source.search(arxiv_id, 1990, 2030, max_results=1)
        if not results:
            raise RuntimeError(f"arxiv_id '{arxiv_id}'로 논문을 찾지 못했다.")
        return results[0]

    if keyword:
        note = find_survey_note(keyword, notes)
        if note:
            paper = _note_to_paper(note)
            if paper:
                print(f"[Survey Notes 매칭] {paper.title} ({paper.year}) -- arxiv:{paper.arxiv_id}")
                return paper
            print(f"[알림] Survey Notes에 '{note['title']}'는 있지만 arxiv_id가 없다(doi만). arXiv 원격 검색으로 폴백.")

    if not keyword:
        raise RuntimeError("검색어가 없다. keyword, --index, --arxiv-id, --pdf 중 하나는 줘야 한다.")

    results = arxiv_source.search(keyword, 1990, 2030, max_results=5)
    if not results:
        raise RuntimeError(f"'{keyword}'로 arXiv에서도 논문을 찾지 못했다. --pdf로 로컬 파일을 직접 지정하거나 --arxiv-id를 써볼 것.")
    top = results[0]
    print(f"[arXiv 원격 검색] {top.title} ({top.year}) -- arxiv:{top.arxiv_id}")
    if len(results) > 1:
        print("  (다른 후보: " + ", ".join(f"{r.title[:50]}..." for r in results[1:3]) + ")")
        print("  (제목이 다르게 잡히면 --arxiv-id로 정확히 지정할 것 -- 원격 검색은 부정확할 수 있음)")
    return top


def fetch_pdf_text(pdf_url: str) -> str:
    resp = requests.get(pdf_url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    reader = PdfReader(BytesIO(resp.content))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages).strip()
    if not text:
        raise RuntimeError("PDF에서 텍스트를 추출하지 못했다 (스캔본이거나 이미지 기반 PDF일 수 있음).")
    return text


def load_local_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages).strip()
    if not text:
        raise RuntimeError(f"'{path}'에서 텍스트를 추출하지 못했다.")
    return text


_REVIEW_PROMPT = """당신은 어려운 논문을 일반 독자도 흥미롭게 읽을 수 있는 장문의 한국어 리뷰로
풀어 쓰는 기술 작가입니다. 아래는 논문 원문 전체(PDF에서 추출한 텍스트, 순서가 다소
섞이거나 표/그림 캡션이 깨져 있을 수 있음)입니다.

이 논문을 "{angle}"으로 리뷰를 작성하세요.

작성 규칙:
- 챕터(장) 단위로 구성하되, 챕터 수는 내용에 맞게 자유롭게 정하세요 (보통 4~6장).
- 각 장은 소제목을 달고, 친근한 설명체로 씁니다. 비유를 적극 활용해도 좋습니다
  (단, 비유는 기술적 정확성을 해치지 않는 선에서).
- 숫자, 성능 수치, 구조적 디테일(예: 파라미터 개수, 클럭, 면적 비율, 실험 결과)은
  반드시 아래 원문에 실제로 등장하는 값만 인용하세요. 원문에 없는 수치를 절대
  지어내지 마세요 -- 모르면 "논문에 명시되지 않음"이라고 쓰세요.
- 마지막 장은 이 논문이 이후 연구/산업에 남긴 의의로 마무리하세요.
- 전체 분량은 충분히 길게 (한국어 기준 A4 4~8페이지 상당) 씁니다. 짧게 요약하지 마세요.
- 마크다운 헤딩(##)으로 챕터를 구분하세요. 최상위 제목(#)은 쓰지 마세요 (제목은 별도로 붙습니다).

--- 논문 원문 시작 ---
{paper_text}
--- 논문 원문 끝 ---
"""


def generate_deep_review(paper_text: str, angle: str) -> str:
    if len(paper_text) > MAX_CHARS:
        print(f"[경고] 원문이 {len(paper_text)}자라 {MAX_CHARS}자로 잘라서 전달함 (뒷부분 손실 가능).")
        paper_text = paper_text[:MAX_CHARS]
    prompt = _REVIEW_PROMPT.format(angle=angle, paper_text=paper_text)
    return gemini_client.generate(prompt)


_TEMPLATE = """---
title: "{title}"
year: {year}
arxiv_id: "{arxiv_id}"
angle: "{angle}"
tags: [deep-review]
---

# {title} ({year}) -- 딥다이브 리뷰

*관점: {angle}*

{body}
"""


def write_deep_review(paper: arxiv_source.Paper, angle: str, body: str, vault_path: Path | None = None) -> Path:
    vault_path = vault_path or DEEP_REVIEW_PATH
    vault_path.mkdir(parents=True, exist_ok=True)

    content = _TEMPLATE.format(
        title=paper.title.replace('"', "'"),
        year=paper.year,
        arxiv_id=paper.arxiv_id or "",
        angle=angle,
        body=body,
    )
    out_path = vault_path / f"[Deep Review] {_slugify(paper.title)} ({paper.year}).md"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def _resolve_paths(domain: str | None, topic: str | None) -> tuple[Path, Path]:
    """main.py로 수집할 때 쓴 것과 같은 (domain, topic)을 주면 해당 하위 폴더를,
    안 주면 예전 방식대로 .env의 OBSIDIAN_VAULT_PATH(평평한 구조)를 쓴다."""
    if topic:
        return note_folder(topic, domain, "Survey Notes"), note_folder(topic, domain, "Deep Reviews")
    return OBSIDIAN_VAULT_PATH, OBSIDIAN_VAULT_PATH.parent / "Deep Reviews"


def run(keyword: str | None, arxiv_id: str | None, pdf_path: str | None, index: int | None,
        angle: str, domain: str | None, topic: str | None):
    angle = angle or "핵심 기여를 중심으로"
    survey_notes_path, deep_review_path = _resolve_paths(domain, topic)

    if pdf_path:
        local = Path(pdf_path)
        text = load_local_pdf_text(local)
        # 로컬 PDF만 있는 경우 메타데이터가 없으니 파일명으로 대체
        paper = arxiv_source.Paper(title=local.stem, year=0, pdf_url=str(local))
    else:
        paper = resolve_paper(keyword, arxiv_id, index, survey_notes_path)
        if not paper.pdf_url:
            raise RuntimeError(f"'{paper.title}'의 PDF URL을 찾지 못했다. --pdf로 로컬 파일을 직접 지정할 것.")
        print(f"[다운로드] {paper.pdf_url}")
        text = fetch_pdf_text(paper.pdf_url)

    print(f"[추출 완료] {len(text)}자. Gemini에게 딥다이브 리뷰 생성 요청 중 (시간 걸릴 수 있음)...")
    body = generate_deep_review(text, angle)

    out_path = write_deep_review(paper, angle, body, vault_path=deep_review_path)
    print(f"\n완료: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="논문 한 편 딥다이브 리뷰 생성 (PDF 원문 기반, 자유서술)")
    parser.add_argument("keyword", nargs="?", help="논문 제목 또는 검색 키워드")
    parser.add_argument("--arxiv-id", help="arXiv ID를 직접 지정 (검색 생략)")
    parser.add_argument("--pdf", help="로컬 PDF 파일 경로 (arXiv 검색 생략)")
    parser.add_argument("--index", type=int, default=None, help="--list로 본 Survey Notes 목록의 번호")
    parser.add_argument("--list", action="store_true", help="Survey Notes 목록 번호만 보고 종료")
    parser.add_argument("--domain", default=None, help='main.py --domain과 같은 값. 예: "전자전기컴퓨터"')
    parser.add_argument("--topic", default=None,
                         help='main.py에 준 키워드와 같은 값 (폴더 "<도메인>-<키워드>"를 찾는 데 씀). '
                              '안 주면 예전 평평한 vault 경로를 그대로 씀')
    parser.add_argument("--angle", default=None, help='리뷰 관점, 예: "Systolic Array 관점에서"')
    args = parser.parse_args()

    if args.list:
        survey_notes_path, _ = _resolve_paths(args.domain, args.topic)
        print_survey_notes(list_survey_notes(survey_notes_path), survey_notes_path)
    elif not args.keyword and args.index is None and not args.arxiv_id and not args.pdf:
        parser.print_help()
    else:
        run(args.keyword, args.arxiv_id, args.pdf, args.index, args.angle, args.domain, args.topic)
