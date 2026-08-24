"""
편입수학 이론서 검증기. "이론서에 있는 내용만으로 실제 기출문제를 풀 수 있는가"를 실측한다.

사용자가 문제 PDF와 정답 PDF를 각각 별도 파일로 준비해서 아래 폴더에 넣으면 된다:
  <Obsidian Vault>/편입수학 검증/모의고사_PDF/
    <학교>-<연도>-편입수학-문제.pdf
    <학교>-<연도>-편입수학-정답.pdf

이미지/스캔본 PDF도 그대로 처리 가능하다 -- gemini_client.py의 _image_part()가 확장자만 보고
mimeType을 정하는 범용 구조라 파일 그대로 넘기면 Gemini가 문서 이해(OCR 불필요)로 읽는다.

두 단계로 나눠서 부른다 (풀이 단계가 정답을 못 보게 격리하기 위함):
  1) solve_exam()   : 문제 PDF + 이론서 전체를 문맥으로 주고, "이론서에 없는 정리/공식은 쓰지
                       말고, 부족하면 N/A로 답하라"고 강제한 뒤 문제별로 풂 (정답 PDF는 안 보여줌)
  2) grade_exam()    : 1)의 풀이 결과 + 정답 PDF를 같이 주고 문제별로 정답/오답 판정
     N/A는 항상 오답으로 집계한다.

결과는 검증로그/ 밑에 사람이 읽을 .md 로그와 분석용 .jsonl을 둘 다 남긴다.

  python exam_verifier.py --list                       페어링된 시험 목록만 확인
  python exam_verifier.py --exam "성균관대-2024"         해당 시험 하나만 검증
  python exam_verifier.py --all                         모의고사_PDF/에 있는 페어 전부 검증
"""

from __future__ import annotations
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import gemini_client
from theory_generator import BOOK_ROOT, VAULT_ROOT

VERIFY_ROOT = VAULT_ROOT / "편입수학 검증"
PDF_DIR = VERIFY_ROOT / "모의고사_PDF"
LOG_DIR = VERIFY_ROOT / "검증로그"

SOLVE_PERSONA = """당신은 채점관입니다. 아래 제공되는 "이론서 전문"에 적힌 정의/정리/공식/
계산테크닉만 근거로 삼아 문제를 풉니다. 이론서에 없는 정리나 공식이 필요하다고 판단되면,
당신이 원래 알고 있는 일반 수학 지식으로 채워 넣지 말고, 반드시 sufficient=false, answer="N/A"
로 답하십시오. 이론서에 있는 내용만으로 풀 수 있는 문제라면, 정확히 어느 노트의 어느
killing equation/테크닉을 썼는지 cited_sources에 파일명으로 밝히고 풀이 과정을 상세히
서술하십시오."""

SOLVE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "problems": {
            "type": "ARRAY",
            "description": "PDF에 있는 모든 문제를 번호 순서대로, 빠짐없이 처리한 결과",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "number": {"type": "STRING", "description": "문제 번호 (PDF에 적힌 그대로)"},
                    "problem_text": {"type": "STRING", "description": "문제 원문을 텍스트로 옮겨 적은 것 (수식은 LaTeX)"},
                    "sufficient": {"type": "BOOLEAN", "description": "제공된 이론서 노트만으로 풀이가 가능했는지 여부"},
                    "cited_sources": {
                        "type": "ARRAY", "items": {"type": "STRING"},
                        "description": "실제로 사용한 이론서 노트 파일명 목록 (sufficient=false면 빈 배열)",
                    },
                    "reasoning": {"type": "STRING", "description": "단계별 풀이 과정 전체 (sufficient=false면 어디서 막혔는지 설명)"},
                    "answer": {"type": "STRING", "description": "최종 답. sufficient=false면 반드시 \"N/A\""},
                },
                "required": ["number", "problem_text", "sufficient", "cited_sources", "reasoning", "answer"],
            },
        },
    },
    "required": ["problems"],
}

SOLVE_PROMPT_TMPL = SOLVE_PERSONA + """

--- 이론서 전문 시작 ---
{theory_book}
--- 이론서 전문 끝 ---

첨부된 PDF는 편입수학 시험 문제지다. 문제지에 있는 모든 문제를 지정된 JSON 스키마로 풀어라.
"""

GRADE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "results": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "number": {"type": "STRING"},
                    "my_answer": {"type": "STRING"},
                    "official_answer": {"type": "STRING", "description": "정답 PDF에서 읽은 해당 번호의 공식 정답"},
                    "verdict": {"type": "STRING", "enum": ["정답", "오답", "N/A"], "description": "my_answer가 N/A였으면 무조건 N/A"},
                    "grading_note": {"type": "STRING", "description": "표기 형식이 달라도 같은 값이면 정답 처리한 이유, 또는 왜 다른지"},
                },
                "required": ["number", "my_answer", "official_answer", "verdict", "grading_note"],
            },
        },
    },
    "required": ["results"],
}

GRADE_PROMPT_TMPL = """다음은 편입수학 문제에 대한 풀이 결과다 (문제번호, 내가 낸 답):

{my_answers_json}

첨부된 PDF는 이 시험의 공식 정답표다. 각 문제 번호에 대해 공식 정답을 읽어서 내 답과
비교하라. 표기 형식이 다르더라도(예: "3"과 "x=3"과 "③") 값이 같으면 "정답"으로 판정한다.
내 답이 "N/A"였던 문제는 값을 비교하지 말고 무조건 verdict="N/A"로 처리한다. 지정된 JSON
스키마로만 답하라.
"""


def load_theory_book() -> str:
    """이론서 전체를 노트 경로 헤더와 함께 하나의 문자열로 합친다 (인용 근거 추적용)."""
    parts = []
    for md_file in sorted(BOOK_ROOT.rglob("*.md")):
        rel = md_file.relative_to(BOOK_ROOT)
        parts.append(f"\n\n=== [{rel}] ===\n{md_file.read_text(encoding='utf-8')}")
    return "".join(parts)


def find_exam_pairs() -> dict[str, dict[str, Path]]:
    """모의고사_PDF/ 안에서 <이름>-문제.pdf / <이름>-정답.pdf 페어를 찾는다.
    학교별 하위 폴더로 정리해도 되도록 재귀적으로 찾는다."""
    pairs: dict[str, dict[str, Path]] = {}
    if not PDF_DIR.exists():
        return pairs
    for pdf in PDF_DIR.rglob("*.pdf"):
        m = re.match(r"^(.+)-(문제|정답)\.pdf$", pdf.name)
        if not m:
            continue
        key, kind = m.group(1), m.group(2)
        pairs.setdefault(key, {})[kind] = pdf
    return pairs


def solve_exam(problem_pdf: Path, theory_book: str) -> list[dict]:
    prompt = SOLVE_PROMPT_TMPL.format(theory_book=theory_book)
    print(f"  [풀이 중] {problem_pdf.name} (이론서 {len(theory_book):,}자 문맥으로 제공)...")
    data = gemini_client.generate_json(prompt, SOLVE_SCHEMA, images=[problem_pdf])
    return data.get("problems", [])


def grade_exam(solved: list[dict], answer_pdf: Path) -> list[dict]:
    my_answers = [{"number": p["number"], "answer": p["answer"]} for p in solved]
    prompt = GRADE_PROMPT_TMPL.format(my_answers_json=json.dumps(my_answers, ensure_ascii=False, indent=2))
    print(f"  [채점 중] {answer_pdf.name} 대조...")
    data = gemini_client.generate_json(prompt, GRADE_SCHEMA, images=[answer_pdf])
    return data.get("results", [])


def write_logs(exam_key: str, solved: list[dict], graded: list[dict]) -> tuple[Path, Path]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    graded_by_num = {g["number"]: g for g in graded}
    timestamp = datetime.now().isoformat(timespec="seconds")

    # 사람이 읽는 로그
    lines = [f"# {exam_key} 편입수학 검증 로그", f"검증 시각: {timestamp}", ""]
    correct = wrong = na = 0
    for p in solved:
        g = graded_by_num.get(p["number"], {})
        verdict = g.get("verdict", "N/A" if p["answer"] == "N/A" else "채점불가")
        if verdict == "정답":
            correct += 1
        elif verdict == "N/A":
            na += 1
        else:
            wrong += 1
        lines.append(f"## 문제 {p['number']} — {verdict}")
        lines.append(f"**문제:** {p['problem_text']}")
        lines.append(f"**이론서로 충분했는가:** {p['sufficient']}")
        lines.append(f"**인용한 노트:** {', '.join(p['cited_sources']) or '(없음)'}")
        lines.append(f"**풀이:**\n{p['reasoning']}")
        lines.append(f"**내 답:** {p['answer']}  /  **공식 정답:** {g.get('official_answer','?')}")
        lines.append(f"**채점 비고:** {g.get('grading_note','')}")
        lines.append("")
    total = len(solved)
    lines.insert(2, f"**결과: {correct}/{total} 정답 ({correct/total*100:.1f}%), 오답 {wrong}, N/A(오답 처리) {na}**\n")

    md_path = LOG_DIR / f"{exam_key}-편입수학-검증로그.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    # 분석용 구조화 로그
    jsonl_path = LOG_DIR / f"{exam_key}-편입수학-검증로그.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for p in solved:
            g = graded_by_num.get(p["number"], {})
            entry = {"timestamp": timestamp, "exam": exam_key, **p, "verdict": g.get("verdict"),
                      "official_answer": g.get("official_answer"), "grading_note": g.get("grading_note")}
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"  [결과] {correct}/{total} 정답 ({correct/total*100:.1f}%), 오답 {wrong}, N/A {na}")
    print(f"  [로그] {md_path}")
    return md_path, jsonl_path


def verify_one(exam_key: str, files: dict[str, Path], theory_book: str):
    if "문제" not in files or "정답" not in files:
        print(f"[건너뜀] {exam_key}: 문제/정답 PDF 페어가 안 맞음 ({list(files.keys())})")
        return
    solved = solve_exam(files["문제"], theory_book)
    graded = grade_exam(solved, files["정답"])
    write_logs(exam_key, solved, graded)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="편입수학 이론서를 실제 기출로 검증")
    parser.add_argument("--list", action="store_true", help="페어링된 시험 목록만 확인")
    parser.add_argument("--exam", help='"<학교>-<연도>" 형식으로 시험 하나만 지정')
    parser.add_argument("--all", action="store_true", help="모의고사_PDF/의 모든 페어 검증")
    args = parser.parse_args()

    pairs = find_exam_pairs()

    if args.list:
        for key, files in pairs.items():
            status = "OK" if "문제" in files and "정답" in files else f"불완전({list(files.keys())})"
            print(f"  {key}: {status}")
    elif args.exam:
        if args.exam not in pairs:
            raise SystemExit(f"'{args.exam}' 페어를 못 찾음. --list로 확인할 것.")
        theory_book = load_theory_book()
        verify_one(args.exam, pairs[args.exam], theory_book)
    elif args.all:
        if not pairs:
            print(f"[알림] {PDF_DIR}에 <이름>-문제.pdf / <이름>-정답.pdf 페어가 없다.")
        theory_book = load_theory_book()
        for key, files in pairs.items():
            verify_one(key, files, theory_book)
    else:
        parser.print_help()
