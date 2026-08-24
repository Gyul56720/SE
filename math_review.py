"""
수학 개념 추출 Agent CLI (transfer_math_chatbot 연동 진입점).

  python math_review.py --list                         Survey Notes 목록 번호 보기
  python math_review.py --index 3                       목록의 3번 논문에서 수학 논리/공식 추출
  python math_review.py "TPU v4"                        Survey Notes에서 제목 부분일치 검색 후 추출
  python math_review.py --arxiv-id 1704.04760           arXiv ID로 직접 지정
  python math_review.py --pdf ./my_paper.pdf            로컬 PDF 직접 지정
  python math_review.py --image ./photos/eq.jpg         사진 속 수식을 바로 질의 (논문 조회 없이,
                                                          transfer_math_chatbot의 이미지 인식 기능 그대로)
  python math_review.py --image ./eq.jpg --ask "이 부분만 설명해줘"

논문 조회/원문 다운로드는 deep_review.py의 로직을 그대로 재사용한다 (같은 로직 두 번 짜지 않기 위함).
결과는 "<도메인>-<키워드>/Math Concepts/" 폴더에 [Math] 접두어를 붙여 저장하고,
같은 폴더의 원 논문 Survey Note로 source_paper 위키링크를, 근접 개념 중 이미 vault에
있는 것과는 자동으로 상호 위키링크를 건다.
"""

from __future__ import annotations
import argparse
from pathlib import Path

import deep_review
import math_extractor
from config import OBSIDIAN_VAULT_PATH


def _resolve_math_vault(domain: str | None, topic: str | None) -> Path:
    if topic:
        from config import note_folder
        return note_folder(topic, domain, "Math Concepts")
    return OBSIDIAN_VAULT_PATH.parent / "Math Concepts"


def run_image(image_paths: list[str], question: str | None):
    paths = [Path(p) for p in image_paths]
    missing = [p for p in paths if not p.exists()]
    if missing:
        raise RuntimeError(f"이미지 파일을 찾을 수 없다: {missing}")
    print(f"[이미지 인식] {len(paths)}개 파일 전달 중 (transfer_math_chatbot 경로)...")
    answer = math_extractor.extract_math_from_image(paths, question)
    print("\n해설:")
    print(answer)


def run_paper(keyword: str | None, arxiv_id: str | None, pdf_path: str | None, index: int | None,
              domain: str | None, topic: str | None):
    survey_notes_path, _ = deep_review._resolve_paths(domain, topic)

    if pdf_path:
        local = Path(pdf_path)
        text = deep_review.load_local_pdf_text(local)
        title, year = local.stem, None
    else:
        paper = deep_review.resolve_paper(keyword, arxiv_id, index, survey_notes_path)
        if not paper.pdf_url:
            raise RuntimeError(f"'{paper.title}'의 PDF URL을 찾지 못했다. --pdf로 로컬 파일을 직접 지정할 것.")
        print(f"[다운로드] {paper.pdf_url}")
        text = deep_review.fetch_pdf_text(paper.pdf_url)
        title, year = paper.title, paper.year

    print(f"[추출 완료] {len(text)}자. Gemini로 수학 논리/공식 추출 중 (시간 걸릴 수 있음)...")
    result = math_extractor.extract_math(text, title)
    print(f"  공식 {len(result.formulas)}개, 핵심 개념 {len(result.key_concepts)}개, "
          f"근접 개념 {len(result.adjacent_concepts)}개 추출됨")

    math_vault = _resolve_math_vault(domain, topic)
    concept_index = math_extractor.load_existing_concept_index(math_vault)
    out_path = math_extractor.write_math_note(
        result, title, year, domain=domain, topic=topic,
        vault_path=math_vault, concept_slug_index=concept_index,
    )
    print(f"\n완료: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="논문에서 수학 논리/공식 추출 + 근접 개념 제시 (transfer_math_chatbot 연동)")
    parser.add_argument("keyword", nargs="?", help="논문 제목 또는 검색 키워드")
    parser.add_argument("--arxiv-id", help="arXiv ID를 직접 지정 (검색 생략)")
    parser.add_argument("--pdf", help="로컬 PDF 파일 경로 (arXiv 검색 생략)")
    parser.add_argument("--index", type=int, default=None, help="--list로 본 Survey Notes 목록의 번호")
    parser.add_argument("--list", action="store_true", help="Survey Notes 목록 번호만 보고 종료")
    parser.add_argument("--domain", default=None, help='main.py --domain과 같은 값')
    parser.add_argument("--topic", default=None, help='main.py에 준 키워드와 같은 값')
    parser.add_argument("--image", action="append", default=None,
                         help="수식 사진 경로 (여러 번 지정 가능). 지정 시 논문 조회 없이 이미지만으로 질의")
    parser.add_argument("--ask", default=None, help="--image와 함께 쓸 구체적 질문 (생략 시 기본 질문 사용)")
    args = parser.parse_args()

    if args.image:
        run_image(args.image, args.ask)
    elif args.list:
        survey_notes_path, _ = deep_review._resolve_paths(args.domain, args.topic)
        deep_review.print_survey_notes(deep_review.list_survey_notes(survey_notes_path), survey_notes_path)
    elif not args.keyword and args.index is None and not args.arxiv_id and not args.pdf:
        parser.print_help()
    else:
        run_paper(args.keyword, args.arxiv_id, args.pdf, args.index, args.domain, args.topic)
