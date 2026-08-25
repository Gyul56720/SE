"""
Groq(openai/gpt-oss-120b, 무료 티어)의 "순수 추론력"만으로 같은 문제를 얼마나 맞히는지
exam_verifier.py의 Gemini(이론서 그라운딩) 결과와 비교하는 일회성 테스트 스크립트.

이론서 전문(476KB, ~12만 토큰)을 매 배치에 통째로 넣는 exam_verifier.py 방식은 Groq
무료 티어 컨텍스트/토큰 한도를 넘어서 요청 자체가 거부됐다 (400: message too long).
그래서 이론서 없이 모델 자체 수학 지식만으로 풀게 한다 -- exam_verifier.py와 그라운딩
조건이 다르므로 "완전히 공정한 비교"는 아니고, "이 무료 모델이 이 난이도의 문제를 얼마나
스스로 풀 수 있는가"에 대한 답이다.

이미 exam_verifier.py로 한 번 푼 시험만 대상으로 한다 -- PDF를 다시 읽지 않고, 체크포인트에
저장된 problem_text/choices(이미 LaTeX $ 델리미터까지 붙어 있음)와 .jsonl 로그의
official_answer(이미 옵션 번호가 아니라 실제 값으로 풀려 있음)를 그대로 재사용한다.
채점(정답/오답 판정)은 이미 알고 있는 official_answer와 Groq의 답을 Gemini에게 텍스트로만
비교시킨다 (PDF 재첨부 없음, 저렴한 호출) -- Groq 자신에게 채점을 맡기면 스스로에게 관대하게
판정할 위험이 있어서 제외했다.
"""
from __future__ import annotations
import json

import groq_client
import gemini_client
from exam_verifier import LOG_DIR, _load_checkpoint

SOLVE_PERSONA_NO_THEORY = """당신은 편입수학(대학 편입 시험 수학) 문제를 푸는 채점관입니다.
표준적인 대학 미적분학/선형대수학/다변수미적분학/공학수학 범위 안에서, 문제를 단계별로
풀이하고 최종 답을 제시하십시오. 정말로 풀 수 없는 문제만 answer="N/A"로 답하십시오.

**중요:** answer 필드에는 보기 번호(①②③ 등)가 아니라 계산으로 얻은 실제 값을 쓰십시오
(예: "⑤" 대신 "8ln2+12"). 번호만 쓰면 채점이 불가능합니다."""

GROQ_SOLVE_SCHEMA = {
    "type": "object",
    "properties": {
        "problems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "string"},
                    "reasoning": {"type": "string"},
                    "answer": {"type": "string"},
                },
                "required": ["number", "reasoning", "answer"],
            },
        },
    },
    "required": ["problems"],
}

VERDICT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "results": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "number": {"type": "STRING"},
                    "verdict": {"type": "STRING", "enum": ["정답", "오답", "N/A"]},
                },
                "required": ["number", "verdict"],
            },
        },
    },
    "required": ["results"],
}


def solve_batch_groq(batch: list[dict], model: str | None = None) -> list[dict]:
    payload = [{"number": p["number"], "problem_text": p["problem_text"], "choices": p.get("choices", [])}
               for p in batch]
    prompt = SOLVE_PERSONA_NO_THEORY + f"""

다음 문제들을 풀어라 (이미 텍스트로 옮겨진 문제, 보기 포함):
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
    data = groq_client.generate_json(prompt, GROQ_SOLVE_SCHEMA, model=model)
    return data.get("problems", [])


def judge_batch(batch: list[dict], official_by_num: dict[str, str]) -> dict[str, str]:
    payload = [{"number": p["number"], "my_answer": p["answer"],
                "official_answer": official_by_num.get(p["number"], "")} for p in batch]
    prompt = f"""다음은 문제별 (내 답, 공식 정답) 쌍이다. 표기 형식이 달라도(예: "3"과 "x=3")
값이 같으면 "정답", 다르면 "오답"으로 판정하라. my_answer가 "N/A"면 무조건 "N/A"로 판정하라.

{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
    data = gemini_client.generate_json(prompt, VERDICT_SCHEMA)
    return {r["number"]: r["verdict"] for r in data.get("results", [])}


def run(exam_key: str, model: str | None = None) -> None:
    checkpoint = _load_checkpoint(exam_key)
    numbers = list(checkpoint.keys())

    jsonl_path = LOG_DIR / f"{exam_key}-편입수학-검증로그.jsonl"
    official_by_num: dict[str, str] = {}
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            official_by_num[e["number"]] = e.get("official_answer") or ""

    problems = [checkpoint[n] for n in numbers]
    groq_results: list[dict] = []
    batch_size = 3
    for i in range(0, len(problems), batch_size):
        batch = problems[i:i + batch_size]
        print(f"  [Groq 풀이 중] 문제 {[p['number'] for p in batch]}...")
        try:
            groq_results.extend(solve_batch_groq(batch, model=model))
        except Exception as e:
            print(f"  [Groq 배치 실패] {[p['number'] for p in batch]}: {e}")

    verdicts: dict[str, str] = {}
    for i in range(0, len(groq_results), 10):
        chunk = groq_results[i:i + 10]
        try:
            verdicts.update(judge_batch(chunk, official_by_num))
        except Exception as e:
            print(f"  [채점 실패] {[p['number'] for p in chunk]}: {e}")

    used_model = model or groq_client.DEFAULT_MODEL
    correct = wrong = na = 0
    lines = [f"# {exam_key} -- Groq({used_model}) vs Gemini 비교 테스트\n"]
    for r in groq_results:
        v = verdicts.get(r["number"], "채점불가")
        if v == "정답":
            correct += 1
        elif v == "N/A":
            na += 1
        elif v == "오답":
            wrong += 1
        lines.append(f"## 문제 {r['number']} — {v}")
        lines.append(f"**Groq 답:** {r['answer']}  /  **공식 정답:** {official_by_num.get(r['number'], '?')}")
        lines.append(f"**풀이:** {r['reasoning'][:500]}")
        lines.append("")

    total = len(groq_results)
    pct = f"{correct/total*100:.1f}%" if total else "N/A"
    lines.insert(1, f"**결과: {correct}/{total} 정답 ({pct}), 오답 {wrong}, N/A {na}**\n")

    model_tag = used_model.replace("/", "_")
    out_path = LOG_DIR / f"{exam_key}-groq-{model_tag}-비교테스트.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [결과] {correct}/{total} 정답 ({pct}), 오답 {wrong}, N/A {na}")
    print(f"  [로그] {out_path}")


if __name__ == "__main__":
    import sys
    exam_key = sys.argv[1] if len(sys.argv) > 1 else "건국대-2024-편입수학-A형"
    model = sys.argv[2] if len(sys.argv) > 2 else None
    run(exam_key, model=model)
