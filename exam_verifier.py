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

**"이론서 밖 지식 금지"의 정확한 의미**: 이론서에 없는 정리나 공식(예: 이론서가 안 가르치는
새로운 적분 기법, 이론서에 없는 정리)을 끌어오는 것은 금지입니다. 하지만 이론서에 있는
공식/테크닉을 문제에 주어진 **구체적인 숫자에 대입해서 계산하는 것**은 위반이 아니라 정상적인
문제 풀이입니다 -- 예를 들어 이론서의 "미정계수법" 테크닉을 이 문제의 특정 다항식 차수에
적용해서 계산하는 것은 전혀 문제 없습니다. 사칙연산, 인수분해, 미분/적분의 기계적 계산처럼
모든 수학에서 당연히 전제되는 기초 조작도 금지 대상이 아닙니다.

이론서에 정말로 없는 개념/정리가 필요한 경우에만 sufficient=false, answer="N/A"로 답하십시오.
단순히 계산이 복잡하거나, 문제의 이미지/텍스트를 읽기 까다롭다는 이유로 N/A로 도피하지
마십시오 -- 이미지가 실제로 읽을 수 없을 정도로 손상된 경우가 아니라면 최선을 다해 읽고
풀이를 시도해야 합니다.

**경고**: 이 풀이는 이후 별도의 감사(audit) 단계에서, 여기 쓰인 정리/공식이 실제로 이론서에
있는지 검증됩니다. 이론서에 아예 없는 정리나 공식을 사용한 것이 발각되면 그 문제는 무조건
N/A로 강제 처리됩니다. 하지만 이론서에 있는 내용을 정확히 적용해서 얻은 결과는 감사를
통과하니, 정당하게 풀 수 있는 문제까지 지레 겁먹고 N/A로 도피할 필요는 없습니다.

이론서에 있는 내용만으로 풀 수 있는 문제라면, 정확히 어느 노트의 어느 killing equation/
테크닉을 썼는지 cited_sources에 파일명으로 밝히고, reasoning에는 사용한 정리/공식을 이론서
표현 그대로 인용하면서 풀이 과정을 상세히 서술하십시오.

**객관식 문제의 보기 추출(매우 중요, 채점 정확도의 핵심):** 문제에 ①②③④⑤ 또는 1)~5) 같은
보기가 있으면, choices 배열에 **보기 5개 전부를 label과 실제 값(수식 포함) 그대로** 옮겨
적으십시오 (예: [{{"label":"①","value":"3π+1"}}, {{"label":"②","value":"4"}}, ...]). 정답표
PDF는 보통 "3번"처럼 보기 번호만 적혀 있어서, 이 번호가 실제로 어떤 값을 가리키는지는 오직
이 choices 배열로만 알 수 있습니다 -- 이걸 빠뜨리면 계산이 아무리 정확해도 채점이 원천적으로
불가능해집니다. 보기가 없는 주관식 문제는 choices를 빈 배열로 둡니다.

최종 answer는 계산으로 얻은 값 자체를 씁니다 (보기 번호를 몰라도 됨 -- 번호 매칭은 채점
단계가 choices를 보고 알아서 합니다)."""

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
                    "problem_text": {"type": "STRING", "description": "문제 원문을 텍스트로 옮겨 적은 것 (수식은 LaTeX, 보기 제외)"},
                    "choices": {
                        "type": "ARRAY",
                        "description": "객관식 보기 전부 (label+실제 값). 주관식이면 빈 배열.",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "label": {"type": "STRING", "description": "보기 기호 (①, 1), a) 등 PDF에 적힌 그대로)"},
                                "value": {"type": "STRING", "description": "그 보기의 실제 값/수식"},
                            },
                            "required": ["label", "value"],
                        },
                    },
                    "sufficient": {"type": "BOOLEAN", "description": "제공된 이론서 노트만으로 풀이가 가능했는지 여부"},
                    "cited_sources": {
                        "type": "ARRAY", "items": {"type": "STRING"},
                        "description": "실제로 사용한 이론서 노트 파일명 목록 (sufficient=false면 빈 배열)",
                    },
                    "reasoning": {"type": "STRING", "description": "단계별 풀이 과정 전체 (sufficient=false면 어디서 막혔는지 설명)"},
                    "answer": {"type": "STRING", "description": "최종 계산값. sufficient=false면 반드시 \"N/A\""},
                },
                "required": ["number", "problem_text", "choices", "sufficient", "cited_sources", "reasoning", "answer"],
            },
        },
    },
    "required": ["problems"],
}

SOLVE_PROMPT_TMPL = SOLVE_PERSONA + """

--- 이론서 전문 시작 ---
{theory_book}
--- 이론서 전문 끝 ---

첨부된 PDF는 편입수학 시험 문제지다. {scope_instruction} 지정된 JSON 스키마로 풀어라.
"""

LIST_NUMBERS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "numbers": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "PDF에 있는 모든 문제 번호, 순서대로"},
    },
    "required": ["numbers"],
}

LIST_NUMBERS_PROMPT = "첨부된 PDF는 시험 문제지다. 여기 있는 모든 문제 번호를 순서대로 나열하라 (풀이는 하지 말 것)."

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

GRADE_PROMPT_TMPL = """다음은 편입수학 문제에 대한 풀이 결과다 (문제번호, 내가 낸 답, 그
문제의 객관식 보기 목록 -- 주관식이면 choices가 빈 배열):

{my_answers_json}

첨부된 PDF는 이 시험의 공식 정답표다. 보통 "3번"처럼 보기 번호만 적혀 있다 -- 그 번호가
실제로 어떤 값인지는 위 choices 배열에서 같은 번호(label)를 찾아 그 value를 보고 판단한다
(예: 정답표가 "②"이고 choices에 {{"label":"②","value":"4"}}가 있으면 공식 정답의 실제 값은
"4"). choices가 빈 배열(주관식)이면 정답표에 적힌 값 자체를 그대로 내 답과 비교한다.

표기 형식이 다르더라도(예: "3"과 "x=3") 값이 같으면 "정답"으로 판정한다. 내 답이 "N/A"였던
문제는 값을 비교하지 말고 무조건 verdict="N/A"로 처리한다. official_answer 필드에는 보기
번호가 아니라 그 번호가 가리키는 **실제 값**을 적어라. 지정된 JSON 스키마로만 답하라.
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


def list_problem_numbers(problem_pdf: Path) -> list[str]:
    data = gemini_client.generate_json(LIST_NUMBERS_PROMPT, LIST_NUMBERS_SCHEMA, images=[problem_pdf])
    return data.get("numbers", [])


def solve_exam(problem_pdf: Path, theory_book: str, target_numbers: list[str] | None = None) -> list[dict]:
    scope = (f"이번 호출에서는 문제 번호 {', '.join(target_numbers)}에 해당하는 문제만 풀어라 "
             f"(그 외 번호는 이번엔 무시할 것). " if target_numbers else "문제지에 있는 모든 문제를 ")
    prompt = SOLVE_PROMPT_TMPL.format(theory_book=theory_book, scope_instruction=scope)
    print(f"  [풀이 중] {problem_pdf.name} 문제 {target_numbers or '전체'} (이론서 {len(theory_book):,}자)...")
    data = gemini_client.generate_json(prompt, SOLVE_SCHEMA, images=[problem_pdf])
    return data.get("problems", [])


def _checkpoint_path(exam_key: str) -> Path:
    return LOG_DIR / f"{exam_key}-checkpoint.jsonl"


def _load_checkpoint(exam_key: str) -> dict[str, dict]:
    path = _checkpoint_path(exam_key)
    if not path.exists():
        return {}
    solved_by_num: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            solved_by_num[entry["number"]] = entry
    return solved_by_num


def _append_checkpoint(exam_key: str, entries: list[dict]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with _checkpoint_path(exam_key).open("a", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def solve_exam_batched(problem_pdf: Path, theory_book: str, exam_key: str, batch_size: int = 5) -> list[dict]:
    """한 번에 문제를 전부 풀게 하면 응답이 길어져서 중간에 잘리는 경우가 있었다 (실측:
    20문제 요청했는데 10개만 반환됨). 번호만 먼저 가볍게 뽑은 뒤 작은 배치로 나눠서 풀고,
    배치 하나가 성공할 때마다 즉시 체크포인트 파일(<exam_key>-checkpoint.jsonl)에 append한다.
    API 쿼터 등으로 중간에 죽어도, 다음 실행 때 이미 푼 번호는 건너뛰고 남은 배치만 이어서
    처리한다 -- 실행을 몇 번에 걸쳐 나눠 완주할 수 있게 하는 장치."""
    numbers = list_problem_numbers(problem_pdf)
    cached = _load_checkpoint(exam_key)
    remaining = [n for n in numbers if n not in cached]
    print(f"  [문제 목록] 전체 {len(numbers)}문제, 체크포인트에 {len(cached)}개 이미 있음, "
          f"이번에 풀 것 {len(remaining)}개: {remaining}")
    for i in range(0, len(remaining), batch_size):
        batch = remaining[i:i + batch_size]
        try:
            result = solve_exam(problem_pdf, theory_book, target_numbers=batch)
            _append_checkpoint(exam_key, result)
            for r in result:
                cached[r["number"]] = r
        except Exception as e:
            print(f"  [배치 실패, 체크포인트에 저장 안 됨 -- 다음 실행에서 재시도됨] {batch}: {e}")
    return [cached[n] for n in numbers if n in cached]


def grade_exam(solved: list[dict], answer_pdf: Path) -> list[dict]:
    my_answers = [{"number": p["number"], "answer": p["answer"], "choices": p.get("choices", [])} for p in solved]
    prompt = GRADE_PROMPT_TMPL.format(my_answers_json=json.dumps(my_answers, ensure_ascii=False, indent=2))
    print(f"  [채점 중] {answer_pdf.name} 대조...")
    data = gemini_client.generate_json(prompt, GRADE_SCHEMA, images=[answer_pdf])
    return data.get("results", [])


def audit_exam(solved: list[dict], theory_book: str, batch_size: int = 5) -> list[dict]:
    """solve_exam()의 풀이가 실제로 이론서 안의 내용만 썼는지 별도 호출로 재검증한다.
    이 감사는 정답 PDF를 전혀 보지 않으므로, 채점 결과와 무관하게 순수하게 '근거의 정직성'만
    판정한다. 위반이 발견되면 verify_one()에서 그 문제의 answer를 강제로 N/A로 덮어써서,
    이론서 밖 지식으로 우연히 맞힌 답도 정답으로 인정하지 않는 실질적인 페널티를 적용한다.
    solve와 마찬가지로 배치로 쪼개서, 배치 하나가 API 오류로 실패해도 나머지 배치의 감사
    결과는 살아남게 한다 (실패한 배치는 감사 미실행으로 남고, 다음 실행에서 재감사됨)."""
    audits: list[dict] = []
    for i in range(0, len(solved), batch_size):
        chunk = solved[i:i + batch_size]
        audit_input = [{"number": p["number"], "sufficient": p["sufficient"],
                         "cited_sources": p["cited_sources"], "reasoning": p["reasoning"]} for p in chunk]
        prompt = AUDIT_PROMPT_TMPL.format(theory_book=theory_book,
                                           solved_json=json.dumps(audit_input, ensure_ascii=False, indent=2))
        print(f"  [감사 중] 문제 {[p['number'] for p in chunk]} 이론서 밖 지식 사용 여부 검증...")
        try:
            data = gemini_client.generate_json(prompt, AUDIT_SCHEMA)
            audits.extend(data.get("audits", []))
        except Exception as e:
            print(f"  [감사 배치 실패, 이 배치는 미감사로 남김] {[p['number'] for p in chunk]}: {e}")
    return audits


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
    correct = wrong = na = penalized = ungraded = 0
    for p in solved:
        g = graded_by_num.get(p["number"], {})
        verdict = g.get("verdict", "N/A" if p["answer"] == "N/A" else "채점불가")
        if p.get("audit_violation"):
            penalized += 1
        if verdict == "정답":
            correct += 1
        elif verdict == "N/A":
            na += 1
        elif verdict == "채점불가":
            ungraded += 1
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
    graded_total = total - ungraded
    pct = f"{correct/graded_total*100:.1f}%" if graded_total else "N/A"
    ungraded_note = f", 채점불가(집계 제외) {ungraded}" if ungraded else ""
    lines.insert(2, f"**결과: {correct}/{graded_total} 정답 ({pct}), 오답 {wrong}, N/A(오답 처리) {na}{ungraded_note} (그중 감사 위반으로 강제 N/A {penalized}건)**\n")

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

    print(f"  [결과] {correct}/{graded_total} 정답 ({pct}), 오답 {wrong}, N/A {na}{ungraded_note} (감사 위반 강제 N/A {penalized}건)")
    print(f"  [로그] {md_path}")
    return md_path, jsonl_path


def verify_one(exam_key: str, files: dict[str, Path], theory_book: str):
    if "문제" not in files or "정답" not in files:
        print(f"[건너뜀] {exam_key}: 문제/정답 PDF 페어가 안 맞음 ({list(files.keys())})")
        return
    solved = solve_exam_batched(files["문제"], theory_book, exam_key)
    if not solved:
        print(f"[중단] {exam_key}: 풀이 결과가 하나도 없어서 로그를 남길 게 없음")
        return

    try:
        audits = audit_exam(solved, theory_book)
        solved = apply_audit_penalty(solved, audits)
    except Exception as e:
        print(f"  [감사 실패, 건너뜀] {e}")

    try:
        graded = grade_exam(solved, files["정답"])
    except Exception as e:
        print(f"  [채점 실패, 로그만 남김] {e}")
        graded = []

    # 감사/채점 중 하나가 실패해도 이미 푼 결과는 반드시 로그에 남긴다 (API 쿼터 등으로
    # 후반 단계가 죽어도 앞서 얻은 결과가 통째로 날아가지 않도록).
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
