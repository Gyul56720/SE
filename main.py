"""
전체 파이프라인 진입점.

  python main.py "roofline model"                 수집(LLM 미사용) -> 분석 -> 정리
  python main.py "roofline model" --deep           적응형 리서치(gap 판단 + citation walk) 포함
  python main.py --ask "TPU와 GPU roofline 차이는?"  Q&A 레이어만 실행 (vault 전체 대상)
"""
from __future__ import annotations
import argparse

from config import note_folder


def run_pipeline(keyword: str, deep: bool, top_n: int, domain: str | None):
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


def run_ask(question: str):
    import qa_setup
    print(qa_setup.ask_vault(question))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="논문 리서치 파이프라인")
    parser.add_argument("keyword", nargs="?", help="검색 키워드 (예: 'roofline model')")
    parser.add_argument("--deep", action="store_true", help="적응형 리서치 루프(gap 판단+citation walk) 사용")
    parser.add_argument("--top-n", type=int, default=6, help="기간 구간별 상위 몇 편을 남길지")
    parser.add_argument("--domain", default=None, help='분야 태그, 예: "전자전기컴퓨터" -- 상위 폴더가 "<도메인>-<키워드>"로 생김')
    parser.add_argument("--ask", metavar="QUESTION", help="수집 대신, vault 전체에 대해 Q&A만 실행")
    args = parser.parse_args()

    if args.ask:
        run_ask(args.ask)
    elif args.keyword:
        run_pipeline(args.keyword, deep=args.deep, top_n=args.top_n, domain=args.domain)
    else:
        parser.print_help()
