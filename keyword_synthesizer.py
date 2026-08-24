"""
raw 키워드/텍스트 뭉치를 LLM으로 압축해서, (1) 실제 검색에 쓸 영문 핵심 구 2개(search_terms,
중요도순) + (2) 폴더 계층 2단계(folder_domain/folder_topic)로 재조립하고, main.py 파이프라인
(collector.collect 이하)에 그대로 넘겨 수집을 시작한다.

원문을 통째로 압축한 긴 문장(예: 20단어)을 그대로 검색어로 쓰면 arXiv 쿼리 파서가 깨져서
submittedDate 범위 필터가 무시되는 버그가 있다 (실측 확인됨 -- 2005-2013 구간 검색에 2025년
논문이 나옴). 그래서 검색은 LLM이 중요도(weight)로 판단한 최상위 2개 구로만 하고, 폴더명도
같은 2단계로 짧게 유지한다. --domain을 직접 주면 folder_domain 대신 그걸 쓴다.

  python keyword_synthesizer.py "라벨1, 라벨2, ..."        텍스트/키워드 뭉치를 압축만
  python keyword_synthesizer.py --file raw.txt --search     압축 후 바로 파이프라인 실행
  python keyword_synthesizer.py --file raw.txt --search --deep --math --domain "전자전기컴퓨터"

압축 결과(원문 미리보기 + 검색어 2개 + 폴더 계층 + 근거)는 keyword_synthesis_log.jsonl에 한 줄씩 누적된다.
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
                            "arXiv/Semantic Scholar 검색어로 바로 쓸 수 있게 명사구 중심으로 작성. "
                            "길어도 됨 -- 이건 검색 정확도용이지 폴더명이 아님.",
        },
        "folder_domain": {
            "type": "STRING",
            "description": "폴더 구조의 상위 계층. 이 주제가 속하는 더 넓고 추상적인 연구 분야를 "
                            "2~5단어의 짧은 명사구로 (예: '하드웨어 가속기 성능 모델링'). "
                            "compressed_keyword를 그대로 쓰지 말고 반드시 더 짧고 추상화된 상위 개념으로 압축할 것.",
        },
        "folder_topic": {
            "type": "STRING",
            "description": "폴더 구조의 하위 계층. folder_domain보다 한 단계 더 구체적인 주제를 "
                            "2~5단어의 짧은 명사구로 (예: 'TPU-GPU Roofline 분석'). "
                            "folder_domain의 하위 개념이어야 하고, 그 자체로도 폴더명으로 쓸 만큼 짧아야 함.",
        },
        "search_terms": {
            "type": "ARRAY",
            "description": "실제 arXiv/Semantic Scholar 검색에 쓸 영문 핵심 구(phrase) 정확히 2개. "
                            "원문에 담긴 모든 개념을 중요도(weight)로 판단해서 가장 비중 높은 2개만 "
                            "남기고 나머지는 버릴 것 -- 20단어짜리 문장을 그대로 검색어로 쓰면 arXiv "
                            "쿼리 파서가 깨져서 날짜 필터가 무시되는 문제가 있으므로 반드시 2개, 각 "
                            "2~4단어의 짧은 영문 구로 압축한다. search_terms[0]이 가장 중요도(weight)가 "
                            "높은 핵심 개념, search_terms[1]이 그다음으로 중요한 보조 개념.",
            "items": {"type": "STRING"},
            "minItems": 2,
            "maxItems": 2,
        },
        "rationale": {"type": "STRING", "description": "왜 이렇게 압축/계층화했는지 1-2문장"},
    },
    "required": ["compressed_keyword", "folder_domain", "folder_topic", "search_terms", "rationale"],
}

PROMPT_TMPL = """다음은 검색 대상이 될 원문 키워드/텍스트 뭉치다. 여기 담긴 핵심 주제를 분석해서
지정된 JSON 스키마로만, 한국어로 답하라.

- compressed_keyword: 사람이 읽을 참고용 압축 문장(로그에만 남음). 나열/중복/무관한 내용은
  버리고 핵심 개념만 남길 것.
- folder_domain / folder_topic: 결과가 저장될 폴더 이름으로 쓸 것이므로 반드시 둘 다 짧게.
  folder_domain은 더 추상적인 상위 연구 분야, folder_topic은 그 아래 더 구체적인 하위 주제.
  둘을 합쳐도 폴더 깊이는 "<folder_domain>/<folder_topic>" 딱 2단계를 넘지 않는다 -- 그 이상
  세분화하지 말 것.
- search_terms: 실제 검색에 쓰이는 값이라 가장 중요하다. 원문의 모든 개념에 중요도(weight)를
  매긴 뒤, 가장 비중 높은 2개만 남겨서 각각 2~4단어의 짧은 영문 구로 표현할 것. 나머지 개념은
  전부 버린다 -- 검색어를 길게 유지하려 하지 말 것 (긴 검색어는 정확도를 오히려 떨어뜨린다).

--- 원문 시작 ---
{raw_text}
--- 원문 끝 ---
"""

MAX_CHARS = 50_000
LOG_PATH = Path(__file__).parent / "keyword_synthesis_log.jsonl"


def synthesize(raw_text: str) -> dict:
    """원문 키워드/텍스트를 압축된 검색 keyword 문장 + 2단계 폴더 계층(domain/topic)으로 재조립한다."""
    text = raw_text[:MAX_CHARS]
    prompt = PROMPT_TMPL.format(raw_text=text)
    data = gemini_client.generate_json(prompt, SCHEMA)
    return {
        "compressed_keyword": data.get("compressed_keyword", "").strip(),
        "folder_domain": data.get("folder_domain", "").strip(),
        "folder_topic": data.get("folder_topic", "").strip(),
        "search_terms": [t.strip() for t in data.get("search_terms", []) if t.strip()][:2],
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
    print(f'[압축 완료] 참고용 요약 = "{result["compressed_keyword"]}"')
    print(f'  검색어(가중치순 2개) = {result["search_terms"]}')
    print(f'  폴더 구조 = "{result["folder_domain"]}/{result["folder_topic"]}"')
    print(f"  근거: {result['rationale']}")
    print(f"  로그: {log_path}")

    if args.search:
        import main
        domain = args.domain or result["folder_domain"]
        main.run_pipeline(result["search_terms"], deep=args.deep, top_n=args.top_n,
                           domain=domain, math=args.math, label=result["folder_topic"])
