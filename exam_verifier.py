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
계산테크닉만 근거로 삼아 문제를 풉니다.

이것은 절대적인 규칙이며 예외가 없습니다: 이론서에 명시적으로 나오지 않는 정리, 공식, 계산
테크닉을 단 하나라도 사용하면 안 됩니다. 당신이 원래 알고 있는 일반 수학 지식으로 빈틈을
채워 넣는 것은 엄격히 금지됩니다. 이론서만으로 부족하다고 판단되면 절대 추측하지 말고
반드시 sufficient=false, answer="N/A"로 답하십시오 -- 틀린 답보다 정직한 N/A가 항상 낫습니다.

**경고**: 이 풀이는 이후 별도의 감사(audit) 단계에서, 여기 쓰인 모든 사실/공식/정리가 실제로
이론서에 있는지 하나하나 대조 검증됩니다. 이론서에 없는 내용을 몰래 사용한 것이 감사에서
발각되면, 그 문제는 답이 맞았더라도 무조건 N/A(오답)로 강제 처리됩니다 -- 즉 이론서에 없는
지식으로 우연히 맞히는 것은 아무 의미가 없고 오히려 감사 실패로 이어집니다. 따라서 조금이라도
이론서에 근거가 불확실한 단계가 있다면 그 지점에서 sufficient=false로 처리하는 것이 유리합니다.

이론서에 있는 내용만으로 풀 수 있는 문제라면, 정확히 어느 노트의 어느 killing equation/
테크닉을 썼는지 cited_sources에 파일명으로 밝히고, reasoning에는 사용한 정리/공식을 이론서
표현 그대로 인용하면서 풀이 과정을 상세히 서술하십시오."""

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

AUDIT_PERSONA = """당신은 엄격한 감사관입니다. 아래는 어떤 학생이 "제공된 이론서 내용만
사용해서" 풀었다고 주장하는 문제별 풀이입니다. 당신의 임무는 각 풀이를 이론서 전문과
한 줄 한 줄 대조해서, 실제로 사용된 모든 수학적 사실/정리/공식/계산테크닉이 이론서 안에
문자 그대로(또는 명백히 동등하게) 존재하는지 검증하는 것입니다.

풀이 안에 있는 임의의 정리·공식·계산 단계 중 단 하나라도 이론서 어디에서도 찾을 수 없다면,
그 학생은 일반 수학 지식을 몰래 썼다고 판단하고 violation=true로 처리하십시오. 학생이
cited_sources에 어느 노트를 썼다고 주장했더라도, 실제로 그 노트(또는 이론서 어디에도)에
해당 사실이 없다면 그대로 믿지 말고 violation=true로 판정하십시오. 근거를 봐줄 때는
관대하게 해석하지 말고, "이론서에 명시적으로 있는가"만 기준으로 하십시오."""

AUDIT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "audits": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "number": {"type": "STRING"},
                    "violation": {"type": "BOOLEAN", "description": "이론서에 없는 지식을 사용했으면 true"},
                    "violation_detail": {"type": "STRING", "description": "위반이면 구체적으로 어떤 사실/공식이 이론서에 없는지, 위반이 아니면 빈 문자열"},
                },
                "required": ["number", "violation", "violation_detail"],
            },
        },
    },
    "required": ["audits"],
}

AUDIT_PROMPT_TMPL = AUDIT_PERSONA + """

--- 이론서 전문 시작 ---
{theory_book}
--- 이론서 전문 끝 ---

--- 학생의 풀이 시작 ---
{solved_json}
--- 학생의 풀이 끝 ---

각 문제 번호에 대해 지정된 JSON 스키마로만 감사 결과를 답하라. sufficient=false로 이미
N/A 처리된 문제는 애초에 이론서 지식을 안 썼다고 주장하는 것이므로 violation=false로 둔다.
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


def audit_exam(solved: list[dict], theory_book: str) -> list[dict]:
    """solve_exam()의 풀이가 실제로 이론서 안의 내용만 썼는지 별도 호출로 재검증한다.
    이 감사는 정답 PDF를 전혀 보지 않으므로, 채점 결과와 무관하게 순수하게 '근거의 정직성'만
    판정한다. 위반이 발견되면 verify_one()에서 그 문제의 answer를 강제로 N/A로 덮어써서,
    이론서 밖 지식으로 우연히 맞힌 답도 정답으로 인정하지 않는 실질적인 페널티를 적용한다."""
    audit_input = [{"number": p["number"], "sufficient": p["sufficient"],
                     "cited_sources": p["cited_sources"], "reasoning": p["reasoning"]} for p in solved]
    prompt = AUDIT_PROMPT_TMPL.format(theory_book=theory_book,
                                       solved_json=json.dumps(audit_input, ensure_ascii=False, indent=2))
    print(f"  [감사 중] 풀이 {len(solved)}건이 이론서 밖 지식을 썼는지 검증...")
    data = gemini_client.generate_json(prompt, AUDIT_SCHEMA)
    return data.get("audits", [])


def apply_audit_penalty(solved: list[dict], audits: list[dict]) -> list[dict]:
    """감사에서 위반(violation=true)이 발견된 문제는 answer를 강제로 N/A로 덮어쓴다.
    원래 답이 맞았든 틀렸든 상관없이 -- 이론서 밖 지식을 썼다는 사실 자체가 이 검증의
    목적(이론서만으로 충분한가)에 어긋나므로 무조건 무효 처리한다."""
    audit_by_num = {a["number"]: a for a in audits}
    for p in solved:
        a = audit_by_num.get(p["number"])
        p["audit_violation"] = bool(a and a.get("violation"))
        p["audit_detail"] = a.get("violation_detail", "") if a else ""
        if p["audit_violation"] and p["answer"] != "N/A":
            print(f"  [감사 위반] 문제 {p['number']}: {p['audit_detail'][:80]} -> N/A로 강제 처리")
            p["answer"] = "N/A"
            p["sufficient"] = False
    return solved


def write_logs(exam_key: str, solved: list[dict], graded: list[dict]) -> tuple[Path, Path]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    graded_by_num = {g["number"]: g for g in graded}
    timestamp = datetime.now().isoformat(timespec="seconds")

    # 사람이 읽는 로그
    lines = [f"# {exam_key} 편입수학 검증 로그", f"검증 시각: {timestamp}", ""]
    correct = wrong = na = penalized = 0
    for p in solved:
        g = graded_by_num.get(p["number"], {})
        verdict = g.get("verdict", "N/A" if p["answer"] == "N/A" else "채점불가")
        if p.get("audit_violation"):
            penalized += 1
        if verdict == "정답":
            correct += 1
        elif verdict == "N/A":
            na += 1
        else:
            wrong += 1
        lines.append(f"## 문제 {p['number']} — {verdict}" + (" (감사 위반으로 강제 N/A)" if p.get("audit_violation") else ""))
        lines.append(f"**문제:** {p['problem_text']}")
        lines.append(f"**이론서로 충분했는가:** {p['sufficient']}")
        lines.append(f"**인용한 노트:** {', '.join(p['cited_sources']) or '(없음)'}")
        if p.get("audit_violation"):
            lines.append(f"**감사 위반 내용:** {p['audit_detail']}")
        lines.append(f"**풀이:**\n{p['reasoning']}")
        lines.append(f"**내 답:** {p['answer']}  /  **공식 정답:** {g.get('official_answer','?')}")
        lines.append(f"**채점 비고:** {g.get('grading_note','')}")
        lines.append("")
    total = len(solved)
    lines.insert(2, f"**결과: {correct}/{total} 정답 ({correct/total*100:.1f}%), 오답 {wrong}, N/A(오답 처리) {na} (그중 감사 위반으로 강제 N/A {penalized}건)**\n")

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

    print(f"  [결과] {correct}/{total} 정답 ({correct/total*100:.1f}%), 오답 {wrong}, N/A {na} (감사 위반 강제 N/A {penalized}건)")
    print(f"  [로그] {md_path}")
    return md_path, jsonl_path


def verify_one(exam_key: str, files: dict[str, Path], theory_book: str):
    if "문제" not in files or "정답" not in files:
        print(f"[건너뜀] {exam_key}: 문제/정답 PDF 페어가 안 맞음 ({list(files.keys())})")
        return
    solved = solve_exam(files["문제"], theory_book)
    audits = audit_exam(solved, theory_book)
    solved = apply_audit_penalty(solved, audits)
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
