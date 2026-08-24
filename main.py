"""
전체 파이프라인 진입점.

  python main.py "roofline model"                 수집(LLM 미사용) -> 분석 -> 정리
  python main.py "roofline model" --deep           적응형 리서치(gap 판단 + citation walk) 포함
  python main.py "roofline model" --math           위 흐름 + 후보 논문마다 수학 공식/개념 추출까지 연결
  python main.py --ask "TPU와 GPU roofline 차이는?"  Q&A 레이어만 실행 (vault 전체 대상)
"""
from __future__ import annotations
import argparse

from config import note_folder


def run_pipeline(keyword: str, deep: bool, top_n: int, domain: str | None, math: bool):
    import collector
    import analyzer
    import organizer

    if deep:
        import research_graph
        periods = research_graph.deep_collect(keyword, max_iterations=2, top_n_per_period=top_n)
    else:
        periods = collector.collect(keyword, top_n_per_period=top_n)

    all_candidates = [c for cands in periods.values() for c in cands]
    print(f"\n총 {len(all_candidates)}편 후보 확정. 분석 시작...")

    analyses = analyzer.analyze_all(all_candidates)
    vault_path = note_folder(keyword, domain, "Survey Notes")
    written = organizer.write_notes(analyses, keyword=keyword, vault_path=vault_path)

    print(f"\n완료: {len(written)}개 노트를 {vault_path} 에 기록했다.")
    print("Obsidian에서 그래프뷰를 열면 predecessor 링크로 연결된 발전 계보가 보인다.")

    if math:
        run_math_batch(all_candidates)


def run_math_batch(candidates: list):
    """수집된 후보 논문마다 원문 PDF를 받아 수학 공식/구조(아키텍처)를 추출한다 (math_extractor.py 연동).
    pdf_url이 없어도 doi가 있으면 Unpaywall로 합법 오픈액세스 사본을 먼저 찾아본다.
    그래도 없는 논문은 건너뛴다. 결과는 도메인/키워드와 무관하게 '편입 수학/' 폴더 하나에 모인다.
    Survey Notes 분석과 별개 Gemini 호출이라 --math 지정 시에만 돈다."""
    import math_extractor
    import deep_review
    from sources import unpaywall

    concept_index = math_extractor.load_existing_concept_index()

    targets = []
    for c in candidates:
        if not c.pdf_url and c.doi:
            oa_url = unpaywall.find_oa_pdf_url(c.doi)
            if oa_url:
                print(f"[Unpaywall] '{c.title[:60]}' 오픈액세스 사본 발견")
                c.pdf_url = oa_url
        if c.pdf_url:
            targets.append(c)

    print(f"\n[수학/구조 추출] PDF 확보된 후보 {len(targets)}/{len(candidates)}편 대상으로 시작...")
    for i, c in enumerate(targets, 1):
        print(f"[수학/구조 추출 {i}/{len(targets)}] {c.title[:60]}...")
        try:
            text = deep_review.fetch_pdf_text(c.pdf_url)
            result = math_extractor.extract_math(text, c.title)
            math_extractor.write_math_note(result, c.title, c.year, concept_slug_index=concept_index)
        except Exception as e:
            print(f"  실패: {e}")


def run_ask(question: str):
    import qa_setup
    print(qa_setup.ask_vault(question))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="논문 리서치 파이프라인")
    parser.add_argument("keyword", nargs="?", help="검색 키워드 (예: 'roofline model')")
    parser.add_argument("--deep", action="store_true", help="적응형 리서치 루프(gap 판단+citation walk) 사용")
    parser.add_argument("--math", action="store_true", help="후보 논문마다 원문에서 수학 공식/개념까지 추출 (math_extractor.py 연동)")
    parser.add_argument("--top-n", type=int, default=6, help="기간 구간별 상위 몇 편을 남길지")
    parser.add_argument("--domain", default=None, help='분야 태그, 예: "전자전기컴퓨터" -- "<도메인>/<키워드>" 폴더 구조로 중첩됨')
    parser.add_argument("--ask", metavar="QUESTION", help="수집 대신, vault 전체에 대해 Q&A만 실행")
    args = parser.parse_args()

    if args.ask:
        run_ask(args.ask)
    elif args.keyword:
        run_pipeline(args.keyword, deep=args.deep, top_n=args.top_n, domain=args.domain, math=args.math)
    else:
        parser.print_help()
