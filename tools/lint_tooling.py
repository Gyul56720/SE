"""docs/tooling-rules.md 의 규칙 중 **기계로 잡히는 것**만 검사한다.

왜 필요한가. 2026-09-03 하루에 고친 도구 버그 15 개 중 둘은 **같은 병의 형제**였다:
진단기의 [3] 판정을 고쳐놓고 [2] 를 그대로 뒀고, .env 시험의 탐색 경로를 고쳐놓고
환경변수를 그대로 뒀다. 둘 다 다음 실행에서 다시 걸렸다. 고친 뒤 grep 으로 같은
모양을 찾았으면 그 자리에서 끝났을 일이다.

규칙은 추상적인 좋은 습관이 아니라 **실제로 실제로 겪은 버그**이다. 각 규칙에 그것을 만든
커밋이 붙어 있다. 규칙을 새로 만들면 검사도 같이 만든다 -- 검사 없는 규칙은 잊힌다.

검사 종류는 셋뿐이다.
    forbid       이 패턴이 나오면 안 된다
    require      when 이 파일에 있으면 require(들)도 그 파일에 있어야 한다.
                 리스트면 **전부** 있어야 한다 -- OR 로 두면 하나만 남겨도 통과해서
                 규칙이 아무것도 걸러내지 못하게 된다(실측: RPM-분리와 상태코드-분기가 그랬다)
    require_near when 이 나올 때마다 그 뒤 window 글자 안에 require 가 있어야 한다

**주석도 패턴를 만족시킨다.** 패턴 검사의 어쩔 수 없는 한계다. 그래서 규칙마다
tests/test_tooling_rules.py 가 "그 버그를 되살리면 실제로 실패하는가"를 확인한다 --
실패해야 할 때 실패하지 못하는 규칙은 소용이 없고, 실제로 처음 판에서 넷이 그랬다.

패턴으로 못 잡는 규칙(②·③·⑥·⑦)은 여기 없다. 그것들은 시험으로 지킨다 --
tests/test_planner_repair.py 와 tests/test_tensor_rank_verifier.py 에 들어 있다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

RULES = [
    dict(
        id="RPM-분리", rule="①",
        desc="429 를 record_exhausted 로 확정 기록하는 파일은 분당/일일을 갈라야 한다",
        why="분당 한도(1분이면 풀림)를 일일 소진으로 적어 후보 8 개를 자정까지 봉인했다. "
            "사용자는 그날 LLM 을 부른 적이 없었고 그 말이 맞았다",
        commit="860b2d7",
        globs=["orchestrator/*.py"],
        # OR 로 뒀더니 docstring 의 "bot_tools.is_rpm_quota_error" 가 규칙을
        # 만족시켜, _is_rpm 을 통째로 지워도 통과했다. 이름이 아니라 **동작**을 건다.
        # 이름만 적으면 **정의부**(def _is_rpm(e))가 규칙을 만족시켜, 호출을 지워도
        # 그대로 통과한다. meta_defects 가 이것을 잡았다. 호출부의 모양까지 적는다.
        when=r"record_exhausted\(",
        require=[r"if _is_rpm\(e\)", r"record_rpm_cooldown\(label\)"],
    ),
    dict(
        id="심판-재주입", rule="④",
        desc="problems/*/run.py 가 drive 를 부를 때 final_verifier 를 넘겨야 한다",
        why="재계획이 plan.json 을 새로 쓰면서 주입한 심판을 지웠다. 그 뒤로는 LLM 이 "
            "제 답에 스스로 합격을 주고 drive 가 그것을 solved 로 올렸다",
        commit="cdc640b",
        globs=["orchestrator/problems/*/run.py"],
        when=r"\.drive\(", require=r"final_verifier\s*=", window=400,
    ),
    dict(
        id="재채점-출처", rule="④",
        desc="run.py 가 verify.check 를 부르면 verify.TARGET 을 런 쪽으로 돌려야 한다",
        why="재채점이 저장소 원본 예산을 읽어, 예산을 풀어 돌린 멀쩡한 통과에 "
            "'심판이 지워졌다'는 거짓 경보를 붙였다. 거짓 경보는 경보를 죽인다",
        commit="69d5416",
        globs=["orchestrator/problems/*/run.py"],
        when=r"verify\.check\(", require=r"verify\.TARGET",
    ),
    dict(
        id="키-쌍", rule="⑥",
        desc="시험이 GEMINI_API_KEY 를 건드리면 _FALLBACK 도 같이 건드려야 한다",
        why="build_pool 은 키를 둘 읽는데 시험은 앞의 것만 치웠다. FALLBACK 이 환경에 "
            "있는 VM 에서만 깨졌다 -- 내 컨테이너에는 없어서 통과했다",
        commit="e0defa3",
        globs=["tests/*.py"],
        when=r'"GEMINI_API_KEY"', require=r'GEMINI_API_KEY_FALLBACK',
    ),
    dict(
        id="마감-실측", rule="③",
        desc="GEMINI_TIMEOUT 기본값은 실측 145.55 초보다 커야 한다",
        why="60 초 마감을 걸어놓고 145 초짜리 응답에서 돌아온 504 를 구글 탓했다. "
            "짧은 프롬프트는 1~3 초에 오므로 문제가 커진 뒤에야 드러난다",
        commit="0945e18",
        globs=["orchestrator/llm_pool.py"],
        check="timeout",
    ),
    dict(
        id="예산-일치", rule="③",
        desc="기술서에 적는 실행 예산은 --node-timeout 인자에서 와야 한다",
        why="손으로 적은 숫자는 조용히 어긋난다. 기술서가 '600초 쓸 수 있다'고 하는데 "
            "실제 예산이 60초면, 풀던 코드가 끊기고 그 사실이 '틀렸다'로 읽힌다. "
            "재보지 않은 상수를 박는 병(마감 60초 vs 실측 145초)과 같은 것이다",
        commit="C-단계",
        globs=["orchestrator/problems/*/run.py"],
        when=r"\{budget:", require=r"budget=a\.node_timeout",
    ),
    dict(
        id="계산-강제", rule="④",
        desc="계산을 요구하는 런은 수리안 채택 전에도 그것을 검사해야 한다",
        why="심판은 출력만 보므로 어떻게 얻었는지 묻지 않는다. 그래서 오케스트레이터가 "
            "다섯 판 내리 상수로 적은 코드를 냈고 알고리즘 교체가 0 회였다. 최종 관문에서만 막으면 "
            "라운드를 다 쓴 뒤에야 알게 되므로, 수리안 단계에서 되먹여야 한다",
        commit="휴리스틱-제한",
        globs=["orchestrator/planner.py"],
        # 이름만 요구하면 **정의부**가 규칙을 만족시켜, 호출을 통째로 지워도 통과했다.
        # RPM-분리가 docstring 때문에 걸러내지 못하게 된 것과 같은 병이다. 호출부를 정확히 건다.
        when=r'_code_defect\(code, "solve"\)',
        require=r"or _computation_defect\(run_dir, code\)",
    ),
    dict(
        id="미지-범주", rule="①",
        desc="분류기에는 미지 범주가 있어야 한다",
        why="태그가 안 걸리면 '알려진 방식 밖'이라 부르고 흥미롭다고 했는데, 실제로는 답을 "
            "상수로 적어 넣은 코드였다. else 가 확정 범주를 단언하면 거기가 거짓말이다",
        commit="6be1ed0",
        globs=["orchestrator/method_trace.py"],
        # OR 로 뒀더니 셋 중 하나만 남아도 통과했다. 세 범주가 **전부** 있어야 한다 --
        # 새 방법(미분류) / 방법 없음(상수로 적은 것) / 아직 없음(골격)은 서로 다른 사건이다.
        when=r"^MARKERS\s*=",
        require=[r'"알려진 방식 밖"', r'"계산 없음\(상수로 적음\)"', r'"미완성\(내용 없음\)"',
                 r'"계산 없음\(빈 배열만\)"'],
    ),
    dict(
        id="구간-네자리", rule="②",
        desc="문헌 구간 보고는 위/상한/상한아래/하한아래 네 자리를 갈라야 한다",
        why="M >= lower 이기만 하면 '구간 안'이라 적어서, 상한 재현(23)과 상한 "
            "돌파(22)가 같은 문장으로 나왔다. 예산 27 을 '구간 [19,23] 안'이라 했다",
        commit="f732554, f92748e",
        globs=["orchestrator/problems/tensor_rank/verify.py"],
        when=r'd\["interval"\]', require=r'"at_upper"',
    ),
    dict(
        id="상태코드-분기", rule="①",
        desc="진단기의 판정은 상태코드를 보고 갈라야 한다",
        why="200 이 아닌 것을 전부 '구글 쪽 문제'로 뭉쳤다. 429 와 503 은 할 일이 "
            "정반대다. [3] 을 고쳐놓고 [2] 를 그대로 둬서 같은 실수를 두 번 했다",
        commit="25ab7ca",
        globs=["orchestrator/probe_gemini.py"],
        # OR 로 뒀더니 set(hist) 만 남아도 통과했다. [2] 의 상태코드 분기와
        # [3] 의 히스토그램 분기가 **둘 다** 있어야 한다 -- 하나를 고치고 다른 하나를
        # 방치한 것이 실제로 실제로 겪은 버그이다.
        when=r"verdict\.append\(", require=[r"st in \(", r"set\(hist\)"],
    ),
    dict(
        id="버전-보존", rule="⑦",
        desc="노드 코드를 덮어쓰기 전에 이전 판을 남겨야 한다",
        why="수리가 코드를 그냥 덮어써서, 같은 알고리즘을 미세조정한 것인지 교체한 것인지 "
            "잴 대상이 남지 않았다. 없는 축은 리뷰에 안 보인다",
        commit="7ec0f6d",
        globs=["orchestrator/planner.py"],
        # 여기도 정의부가 만족시키고 있었다. 호출부를 적는다.
        when=r"run_dir / node\.component\)\.write_text",
        require=r"prev = _snapshot_code\(run_dir, node\)",
    ),
    dict(
        id="심판-무해", rule="④",
        desc="주입 심판 파일이 풀이법이나 알려진 분해를 담으면 안 된다",
        why="repair_node 는 노드에 verifier 를 읽기 전용으로 보여준다. 심판이 답을 "
            "담고 있으면 오케스트레이터가 베끼고 시험 전체가 무의미해진다",
        commit="7396131",
        globs=["orchestrator/problems/*/verify.py"],
        forbid=r"\blstsq\b|\bpinv\b|\bstrassen\b|\bladerman\b|\bcp_als\b|\bparafac\b",
    ),
]


def _files(globs) -> list:
    out = []
    for g in globs:
        out += sorted(REPO.glob(g))
    return [p for p in out if p.is_file()]


def _check_timeout(path: Path) -> list:
    """실측 지연(145.55s)보다 마감이 큰지. 패턴이 아니라 값을 본다."""
    m = re.search(r'GEMINI_TIMEOUT",\s*"(\d+(?:\.\d+)?)"', path.read_text(encoding="utf-8"))
    if not m:
        return [f"{path.name}: GEMINI_TIMEOUT 기본값을 못 찾았다"]
    v = float(m.group(1))
    return [] if v > 145.55 else [f"{path.name}: 기본 마감 {v}s <= 실측 145.55s"]


def _def_headers(src: str) -> list:
    """def / class 서명 줄만 모은다. 데코레이터와 여러 줄 서명도 포함한다."""
    out, keep = [], 0
    for line in src.splitlines():
        t = line.strip()
        if keep or t.startswith(("def ", "async def ", "class ")):
            out.append(line)
            keep = 0 if t.rstrip().endswith(":") else 1
    return out


def _top_level_or(pat: str) -> bool:
    """정규식에 대괄호 밖 | 가 있는가. 있으면 대안 하나만 남아도 통과한다."""
    depth = 0
    i = 0
    while i < len(pat):
        c = pat[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth = max(0, depth - 1)
        elif c == "|" and depth == 0:
            return True
        i += 1
    return False


def meta_defects(rules=RULES) -> list:
    """**규칙 자체의 약점**을 잡는다. 유도 변형이 못 보는 두 가지다.

    ① require 안의 OR. 대안 중 하나만 남아도 통과하므로 규칙이 아무것도 걸러내지 못하게 된다. 실측으로
       처음 판의 네 실패 중 셋이 이것이었다 -- RPM-분리(_is_rpm 또는 is_rpm_quota_error,
       뒤엣것이 docstring 에만 있었다), 상태코드-분기(st in ( 또는 set(hist)),
       미지-범주(미분류 또는 상수로 적은 것 또는 골격). 리스트로 나눠 적으면 전부 AND 가 된다.

    ② 정의부가 규칙을 만족시키는 경우. require 패턴이 `def 이름(` 에도 걸리면, 호출을
       통째로 지워도 정의가 남아 통과다. 계산-강제가 그랬다. 호출부의 모양까지 적어야
       한다(인자 이름을 포함시키는 식으로).

    유도 변형은 같은 패턴으로 지우므로 이 둘을 못 본다 -- 걸리는 자리가 전부 사라져서
    어차피 실패한다. 그래서 규칙의 **모양**을 직접 본다."""
    bad = []
    for r in rules:
        need = r.get("require")
        if not need:
            continue
        pats = need if isinstance(need, list) else [need]
        for pat in pats:
            if _top_level_or(pat):
                bad.append((r, f"require {pat!r} 에 OR 가 있다 -- 대안 하나만 남아도 "
                               f"통과한다. 리스트로 나눠 적으면 전부 있어야 통과한다"))
            for path in _files(r["globs"]):
                for head in _def_headers(path.read_text(encoding="utf-8", errors="replace")):
                    if re.search(pat, head):
                        bad.append((r, f"require {pat!r} 가 정의부에도 걸린다 "
                                       f"({path.name}: {head.strip()[:60]}) -- 호출을 "
                                       f"지워도 정의가 남아 그대로 통과한다"))
                        break
    return bad


def auto_red(rule: dict, src: str) -> list:
    """규칙에서 **변형을 유도한다.** 손으로 고른 변형 하나로는 실제로 걸러내는지 확인할 수 없다.

    왜 필요한가. red-green 을 손으로 쓰면 "내가 고른 그 변형에 걸린다"만 증명된다.
    변형을 약하게 고르면 규칙이 아무것도 못 걸러내도 통과이고, 실제로 심판-무해가 그랬다 --
    그때 나는 규칙이 아니라 변형을 고쳤다. 게다가 변형과 규칙을 같은 사람이 같은 때에
    쓰므로 맹점을 공유한다. 규칙 ④(검사기는 대상과 다른 출처)가 red-green 자체에 걸린다.

    그래서 변형을 규칙에서 뽑는다. require 패턴에 걸리는 **모든 자리**를 지우면 그
    규칙은 반드시 실패해야 한다. 실패하지 않으면 그 패턴이 다른 무언가에 -- 주석이나
    정의부에 -- 걸려 있다는 뜻이고, 그것이 아무것도 걸러내지 못하는 규칙의 정체다. 이 방식이었으면
    RPM-분리(docstring)와 계산-강제(정의부)를 손으로 짚지 않고도 잡았다.

    **이것이 증명하는 것은 반응 여부뿐이다.** 패턴이 통째로 사라졌을 때 규칙이 반응한다는
    것까지다. 실측으로 걸린 두 약점 -- OR 조건과 정의부 매칭 -- 은 이 방식으로 못 잡는다.
    같은 패턴으로 지우니 걸리는 자리가 전부 사라져서 어차피 실패하기 때문이다. 그 둘은
    meta_defects 가 따로 잡는다.

    (변형본, 지운 패턴, 안내) 목록을 돌려준다. when 까지 지워지면 그 변형은 무효이므로
    걸러낸다 -- 규칙이 안 걸리는 이유가 규칙이 약해서가 아니라 검사 대상이 사라져서이기 때문이다."""
    out = []
    if "forbid" in rule:
        return [(src + "\n\nnp.linalg.lstsq(A, b)\n", rule["forbid"], "금지 패턴 주입")]
    if rule.get("check") == "timeout":
        return [(re.sub(r'(GEMINI_TIMEOUT",\s*")\d+(?:\.\d+)?(")', r"\g<1>60\g<2>", src),
                 "GEMINI_TIMEOUT", "마감을 60 으로")]
    need = rule.get("require")
    if not need:
        return []
    for pat in (need if isinstance(need, list) else [need]):
        mutated = re.sub(pat, "", src)
        if mutated == src:
            continue                       # 이 파일엔 그 패턴이 없다
        if rule.get("when") and not re.search(rule["when"], mutated, re.M):
            continue                       # when 까지 지워졌다 -- 무효한 변형
        out.append((mutated, pat, "require 패턴를 전부 지움"))
    return out


def run(rules=RULES) -> list:
    bad = []
    for r in rules:
        files = _files(r["globs"])
        if not files:
            bad.append((r, f"검사 대상 파일이 없다: {r['globs']}"))
            continue
        for path in files:
            src = path.read_text(encoding="utf-8", errors="replace")
            rel = path.relative_to(REPO)
            if r.get("check") == "timeout":
                for msg in _check_timeout(path):
                    bad.append((r, msg))
            elif "forbid" in r:
                hits = sorted(set(re.findall(r["forbid"], src, re.I)))
                if hits:
                    bad.append((r, f"{rel}: 금지된 패턴 {hits}"))
            elif "window" in r:
                for m in re.finditer(r["when"], src):
                    seg = src[m.start():m.start() + r["window"]]
                    if not re.search(r["require"], seg):
                        line = src[:m.start()].count("\n") + 1
                        bad.append((r, f"{rel}:{line}: '{m.group(0)}' 뒤 "
                                       f"{r['window']}자 안에 {r['require']} 가 없다"))
            else:
                if re.search(r["when"], src, re.M):
                    need = r["require"]
                    for pat in (need if isinstance(need, list) else [need]):
                        if not re.search(pat, src, re.M):
                            bad.append((r, f"{rel}: {r['when']} 는 있는데 {pat} 가 없다"))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description="도구 규칙 grep 검사")
    ap.add_argument("--list", action="store_true", help="규칙과 근거만 보인다")
    a = ap.parse_args()

    if a.list:
        for r in RULES:
            print(f"[{r['rule']}] {r['id']:12} {r['desc']}")
            print(f"{'':17} 근거({r['commit']}): {r['why']}")
        return 0

    bad = meta_defects() + run()
    if bad:
        print(f"규칙 위반 {len(bad)}건:")
        for r, msg in bad:
            print(f"\n  [{r['rule']}] {r['id']} -- {r['desc']}")
            print(f"      {msg}")
            print(f"      왜({r['commit']}): {r['why']}")
        return 1
    print(f"도구 규칙 {len(RULES)}개 -- 통과 "
          f"(패턴으로 못 잡는 ②③⑥⑦ 는 tests/ 가 지킨다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
