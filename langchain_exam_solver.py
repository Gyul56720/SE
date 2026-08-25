"""
LangChain 기반 편입수학 이론서 검증기 (exam_verifier.py의 LangChain 버전).

exam_verifier.py는 gemini_client.py(REST 직접호출)로 이론서 전체(~470KB)를 프롬프트에
통째로 욱여넣는 "직접 주입형" 방식이었다. 이 스크립트는 그 대신 LangChain ReAct agent가
`list_theory_notes`/`read_theory_note` 도구로 필요한 노트만 그때그때 찾아 읽는 "에이전틱
RAG형" 방식이다 -- 어느 노트를 실제로 참고했는지 도구 호출 기록(intermediate_steps)으로
그대로 남는다는 점이 직접 주입형과의 핵심 차이.

문제 원문은 exam_verifier.py가 이미 만들어둔 체크포인트(<exam>-checkpoint.jsonl)의
problem_text를 재사용한다 (같은 시험 PDF를 또 이미지 인식시키는 중복 작업을 피함).
정답 채점은 exam_verifier.grade_exam()을 그대로 재사용한다 (채점 자체는 LangChain과
무관한 별도 단계이므로 이미 검증된 코드를 다시 쓰는 게 낫다).

  python langchain_exam_solver.py --exam "성균관대-2024-편입수학"
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

import gemini_client
from config import GEMINI_API_KEY, GEMINI_API_KEY_FALLBACK, GEMINI_MODEL
from theory_generator import BOOK_ROOT
from exam_verifier import LOG_DIR, find_exam_pairs, grade_exam, _load_checkpoint

# gemini_client.py의 REST 호출과 달리 ChatGoogleGenerativeAI는 그 자동 fallback-키 전환
# 로직을 안 거친다. 429(쿼터 초과)를 잡아서 이 순서대로 다음 키로 넘어가 재시도한다.
_API_KEYS = [k for k in (GEMINI_API_KEY, GEMINI_API_KEY_FALLBACK) if k]


@tool
def list_theory_notes() -> str:
    """편입수학 이론서에 있는 모든 노트의 상대경로 목록을 과목별로 반환한다.
    read_theory_note에 넘길 정확한 경로를 확인할 때 먼저 이걸 호출할 것."""
    return "\n".join(str(p.relative_to(BOOK_ROOT)) for p in sorted(BOOK_ROOT.rglob("*.md")))


@tool
def read_theory_note(relative_path: str) -> str:
    """list_theory_notes로 확인한 상대경로 하나를 그대로 넘기면 그 노트 파일 전체
    내용을 반환한다. 경로가 틀리면 에러 메시지를 반환하니 list_theory_notes로 정확한
    경로를 다시 확인할 것."""
    path = BOOK_ROOT / relative_path
    if not path.exists() or path.suffix != ".md":
        return f"오류: '{relative_path}' 파일을 찾을 수 없음. list_theory_notes로 정확한 경로를 다시 확인할 것."
    return path.read_text(encoding="utf-8")


REACT_PROMPT = PromptTemplate.from_template("""당신은 편입수학 문제를 푸는 채점관입니다. 아래 도구로 이론서 노트를 필요한 만큼 찾아
읽고, 그 안에 있는 정의/정리/공식/계산테크닉만 근거로 문제를 풉니다. 도구로 읽은 이론서
밖의 지식(당신이 원래 알고 있는 일반 수학 지식)을 끌어와서 빈틈을 채우면 안 됩니다.
이론서 어디에도 필요한 내용이 없으면 최종 답을 "N/A (이론서에 없음: <이유>)"로 답하십시오.
단순히 계산이 복잡하다는 이유로 N/A로 도피하지 말고, 이론서에 있는 정의/정리/공식을
구체적인 숫자에 적용하는 것은 얼마든지 정상적인 풀이입니다.

최종 답은 보기 번호를 고르려 하지 말고, 직접 계산해서 나온 값 자체를 쓰십시오 (예: "4",
"178π/15"). 보기 번호와의 매칭은 이후 별도 채점 단계가 처리하니 신경 쓰지 않아도 됩니다.

사용 가능한 도구:
{tools}

다음 형식을 반드시 지키십시오:

Question: 풀어야 할 문제
Thought: 지금 뭘 해야 하는지 생각
Action: 사용할 도구, 반드시 [{tool_names}] 중 하나
Action Input: 그 도구에 넘길 입력
Observation: 도구 실행 결과
... (Thought/Action/Action Input/Observation을 필요한 만큼 반복)
Thought: 이제 최종 답을 알겠다
Final Answer: 실제로 참고한 노트 경로, 단계별 풀이 과정, 최종 답(객관식이면 "보기번호 (계산값)" 형식)을 전부 포함한 최종 답변

시작!

Question: {input}
Thought:{agent_scratchpad}""")

STRUCTURE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "sufficient": {"type": "BOOLEAN", "description": "이론서만으로 풀 수 있었는지"},
        "cited_sources": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "실제로 참고한 노트 경로들"},
        "reasoning": {"type": "STRING", "description": "단계별 풀이 과정"},
        "answer": {"type": "STRING", "description": "최종 답. sufficient=false면 \"N/A\""},
    },
    "required": ["sufficient", "cited_sources", "reasoning", "answer"],
}

STRUCTURE_PROMPT = """다음은 LangChain agent가 자유 텍스트로 낸 풀이 결과다. 이걸 지정된 JSON
스키마로 그대로 구조화하라 (내용을 새로 판단하거나 바꾸지 말고 옮겨 적기만 할 것):

--- agent 출력 시작 ---
{raw}
--- agent 출력 끝 ---
"""


def build_agent_executor(api_key: str) -> AgentExecutor:
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=api_key, temperature=0)
    tools = [list_theory_notes, read_theory_note]
    agent = create_react_agent(llm, tools, REACT_PROMPT)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True,
                          max_iterations=15, return_intermediate_steps=True)


class ExecutorPool:
    """ChatGoogleGenerativeAI는 gemini_client.py의 REST 호출과 달리 자동 키-전환을 안 타므로,
    429(쿼터 초과)를 여기서 잡아서 다음 키로 executor를 다시 만들어 재시도한다."""

    def __init__(self):
        if not _API_KEYS:
            raise RuntimeError("GEMINI_API_KEY가 비어 있다.")
        self._key_index = 0
        self._executor = build_agent_executor(_API_KEYS[0])

    def invoke(self, payload: dict) -> dict:
        while True:
            try:
                return self._executor.invoke(payload)
            except Exception as e:
                is_quota = "ResourceExhausted" in type(e).__name__ or "429" in str(e) or "quota" in str(e).lower()
                if is_quota and self._key_index + 1 < len(_API_KEYS):
                    self._key_index += 1
                    print(f"  [LangChain] 키 {self._key_index}가 쿼터 초과로 보임 -- 보조 키로 전환.")
                    self._executor = build_agent_executor(_API_KEYS[self._key_index])
                    continue
                raise


def solve_one_with_agent(pool: ExecutorPool, number: str, problem_text: str, choices: list[dict]) -> dict:
    print(f"  [LangChain agent 풀이 중] 문제 {number}...")
    choices_block = ("\n보기: " + "; ".join(f"{c['label']} {c['value']}" for c in choices)) if choices else ""
    result = pool.invoke({"input": f"문제 {number}: {problem_text}{choices_block}\n\n"
                                    f"(참고: 최종 답은 보기 번호가 아니라 계산한 값 자체로 답할 것 -- "
                                    f"번호 매칭은 이후 채점 단계가 별도로 처리한다)"})
    raw_output = result["output"]
    tool_calls = [
        {"tool": step[0].tool, "input": step[0].tool_input}
        for step in result.get("intermediate_steps", [])
    ]
    structured = gemini_client.generate_json(STRUCTURE_PROMPT.format(raw=raw_output), STRUCTURE_SCHEMA)
    return {
        "number": number,
        "problem_text": problem_text,
        "choices": choices,
        "tool_calls": tool_calls,
        "raw_agent_output": raw_output,
        **structured,
    }


def _lc_checkpoint_path(exam_key: str) -> Path:
    return LOG_DIR / f"{exam_key}-langchain-checkpoint.jsonl"


def _load_lc_checkpoint(exam_key: str) -> dict[str, dict]:
    path = _lc_checkpoint_path(exam_key)
    if not path.exists():
        return {}
    return {json.loads(line)["number"]: json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _append_lc_checkpoint(exam_key: str, entry: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with _lc_checkpoint_path(exam_key).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def write_langchain_log(exam_key: str, title: str, solved: list[dict], graded: list[dict]) -> Path:
    graded_by_num = {g["number"]: g for g in graded}
    lines = [f"# {title}", ""]
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
        lines.append("**agent가 실제로 호출한 도구:**")
        if p["tool_calls"]:
            for tc in p["tool_calls"]:
                lines.append(f"  - `{tc['tool']}({tc['input']})`")
        else:
            lines.append("  - (없음)")
        lines.append(f"**참고한 노트:** {', '.join(p['cited_sources']) or '(없음)'}")
        lines.append(f"**풀이:**\n{p['reasoning']}")
        lines.append(f"**내 답:** {p['answer']}  /  **공식 정답:** {g.get('official_answer','?')}")
        lines.append(f"**채점 비고:** {g.get('grading_note','')}")
        lines.append("")
    total = len(solved)
    if total:
        lines.insert(1, f"**결과: {correct}/{total} 정답 ({correct/total*100:.1f}%), 오답 {wrong}, N/A(오답 처리) {na}**\n")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    md_path = LOG_DIR / f"{title}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [결과] {correct}/{total} 정답 ({correct/total*100:.1f}%), 오답 {wrong}, N/A {na}")
    print(f"  [로그] {md_path}")
    return md_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LangChain agent로 편입수학 이론서 검증")
    parser.add_argument("--exam", required=True, help='"<학교>-<연도>-편입수학" 형식')
    parser.add_argument("--title", default=None, help="로그 파일 제목 (기본: <exam>-편입수학- LangChain 검증로그)")
    args = parser.parse_args()

    pairs = find_exam_pairs()
    if args.exam not in pairs or "정답" not in pairs[args.exam]:
        raise SystemExit(f"'{args.exam}' 페어를 못 찾음. exam_verifier.py --list로 확인할 것.")

    problems = _load_checkpoint(args.exam)
    if not problems:
        raise SystemExit(f"'{args.exam}'의 체크포인트가 없음. 먼저 exam_verifier.py로 문제 원문을 추출해둘 것.")

    title = args.title or f"{args.exam}-편입수학- LangChain 검증로그"

    # LangChain 전용 체크포인트: 이미 이 agent로 풀어놓은 문제는 건너뛰고 남은 것만 이어서
    # 처리한다 (exam_verifier.py의 배치 체크포인트와 같은 취지 -- 쿼터로 중간에 죽어도
    # 다음 실행에서 이어감).
    lc_cache = _load_lc_checkpoint(args.exam)
    remaining = {n: e for n, e in problems.items() if n not in lc_cache}
    print(f"[체크포인트] 전체 {len(problems)}문제, 이미 풀린 것 {len(lc_cache)}개, 이번에 풀 것 {len(remaining)}개")

    pool = ExecutorPool()
    for number, entry in remaining.items():
        try:
            result = solve_one_with_agent(pool, number, entry["problem_text"], entry.get("choices", []))
            _append_lc_checkpoint(args.exam, result)
            lc_cache[number] = result
        except Exception as e:
            print(f"  [문제 {number} 실패, 체크포인트에 저장 안 됨 -- 다음 실행에서 재시도됨] {e}")

    solved = [lc_cache[n] for n in problems if n in lc_cache]
    if not solved:
        raise SystemExit("풀이 결과가 하나도 없음.")

    graded = grade_exam(solved, pairs[args.exam]["정답"])
    write_langchain_log(args.exam, title, solved, graded)
