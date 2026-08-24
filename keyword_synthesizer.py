"""
raw 키워드/텍스트 뭉치를 LLM으로 압축해서 검색용 keyword 문장 하나로 재조립하고,
그 결과를 main.py 파이프라인(collector.collect 이하)에 그대로 넘겨 수집을 시작한다.

  python keyword_synthesizer.py "라벨1, 라벨2, ..."        텍스트/키워드 뭉치를 압축만
  python keyword_synthesizer.py --file raw.txt --search     압축 후 바로 파이프라인 실행
  python keyword_synthesizer.py --file raw.txt --search --deep --math --domain "전자전기컴퓨터"

압축 결과(원문 미리보기 + 압축 keyword + 근거)는 keyword_synthesis_log.jsonl에 한 줄씩 누적된다.
"""

from __future__ import annotations
import argparse
import json
from datetime import datetime
from pathlib import Path

import gemini_client

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "compressed_keyword": {
            "type": "STRING",
            "description": "원문 키워드/텍스트를 압축 재조립한 하나의 검색 문장. "
                            "arXiv/Semantic Scholar 검색어로 바로 쓸 수 있게 명사구 중심으로 작성.",
        },
        "rationale": {"type": "STRING", "description": "왜 이렇게 압축했는지 1-2문장"},
    },
    "required": ["compressed_keyword", "rationale"],
}

PROMPT_TMPL = """다음은 검색 대상이 될 원문 키워드/텍스트 뭉치다. 여기 담긴 핵심 주제를 분석해서,
논문 검색(arXiv/Semantic Scholar)에 바로 쓸 수 있는 하나의 압축된 검색 키워드 문장으로 재조립하라.
나열/중복/무관한 내용은 버리고 핵심 개념만 남길 것. 반드시 지정된 JSON 스키마로만, 한국어로 답하라.

--- 원문 시작 ---
{raw_text}
--- 원문 끝 ---
"""

MAX_CHARS = 50_000
LOG_PATH = Path(__file__).parent / "keyword_synthesis_log.jsonl"


def synthesize(raw_text: str) -> dict:
    """원문 키워드/텍스트를 압축된 검색 keyword 문장 하나로 재조립한다."""
    text = raw_text[:MAX_CHARS]
    prompt = PROMPT_TMPL.format(raw_text=text)
    data = gemini_client.generate_json(prompt, SCHEMA)
    return {
        "compressed_keyword": data.get("compressed_keyword", "").strip(),
        "rationale": data.get("rationale", "").strip(),
    }


def log_result(raw_text: str, result: dict) -> Path:
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "raw_preview": raw_text[:300],
        **result,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return LOG_PATH


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="raw 키워드/텍스트를 LLM으로 압축해 검색용 keyword 문장으로 재조립 후, 원하면 파이프라인까지 실행"
    )
    parser.add_argument("raw", nargs="?", help="원문 키워드/텍스트 (인용부호로 감싸서 전달)")
    parser.add_argument("--file", help="원문을 파일에서 읽음 (raw 인자 대신)")
    parser.add_argument("--search", action="store_true",
                         help="압축 직후 main.py 파이프라인(수집→분석→정리)을 압축된 keyword로 바로 실행")
    parser.add_argument("--deep", action="store_true", help="--search와 함께: 적응형 리서치 루프 사용")
    parser.add_argument("--math", action="store_true", help="--search와 함께: 수학 공식/개념 추출까지 연결")
    parser.add_argument("--top-n", type=int, default=6)
    parser.add_argument("--domain", default=None)
    args = parser.parse_args()

    if args.file:
        raw_text = Path(args.file).read_text(encoding="utf-8")
    elif args.raw:
        raw_text = args.raw
    else:
        parser.error("raw 인자 또는 --file 중 하나는 필요하다")

    result = synthesize(raw_text)
    log_path = log_result(raw_text, result)
    print(f'[압축 완료] keyword = "{result["compressed_keyword"]}"')
    print(f"  근거: {result['rationale']}")
    print(f"  로그: {log_path}")

    if args.search:
        import main
        main.run_pipeline(result["compressed_keyword"], deep=args.deep, top_n=args.top_n,
                           domain=args.domain, math=args.math)
