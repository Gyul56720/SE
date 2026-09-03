"""docs/tooling-rules.md 의 규칙 중 **기계로 잡히는 것**만 검사한다.

왜 필요한가. 2026-09-03 하루에 고친 도구 버그 15 개 중 둘은 **같은 병의 형제**였다:
진단기의 [3] 판정을 고쳐놓고 [2] 를 그대로 뒀고, .env 시험의 탐색 경로를 고쳐놓고
환경변수를 그대로 뒀다. 둘 다 다음 실행에서 다시 걸렸다. 고친 뒤 grep 으로 같은
모양을 찾았으면 그 자리에서 끝났을 일이다.

규칙은 추상적인 좋은 습관이 아니라 **실제로 물린 자국**이다. 각 규칙에 그것을 만든
커밋이 붙어 있다. 규칙을 새로 만들면 검사도 같이 만든다 -- 검사 없는 규칙은 잊힌다.

검사 종류는 셋뿐이다.
    forbid       이 무늬가 나오면 안 된다
    require      when 이 파일에 있으면 require(들)도 그 파일에 있어야 한다.
                 리스트면 **전부** 있어야 한다 -- OR 로 두면 하나만 남겨도 통과해서
                 규칙이 이빨을 잃는다(실측: RPM-분리와 상태코드-분기가 그랬다)
    require_near when 이 나올 때마다 그 뒤 window 글자 안에 require 가 있어야 한다

**주석도 무늬를 만족시킨다.** 무늬 검사의 어쩔 수 없는 한계다. 그래서 규칙마다
tests/test_tooling_rules.py 가 "그 버그를 되살리면 실제로 빨개지는가"를 확인한다 --
빨개지지 못하는 규칙은 장식이고, 실제로 처음 판에서 넷이 그랬다.

무늬로 못 잡는 규칙(②·③·⑥·⑦)은 여기 없다. 그것들은 시험으로 지킨다 --
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
        # 만족시켜, _is_rpm 을 통째로 지워도 초록이었다. 이름이 아니라 **동작**을 건다.
        when=r"record_exhausted\(", require=[r"_is_rpm\(e\)", r"record_rpm_cooldown\("],
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
            "있는 VM 에서만 깨졌다 -- 내 컨테이너에는 없어서 초록이었다",
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
        id="미지-범주", rule="①",
        desc="분류기에는 미지 범주가 있어야 한다",
        why="태그가 안 걸리면 '미분류'라 부르고 흥미롭다고 했는데 실은 상수표 "
            "하드코딩이었다. else 가 확정 범주를 단언하면 거기가 거짓말이다",
        commit="6be1ed0",
        globs=["orchestrator/method_trace.py"],
        # OR 로 뒀더니 셋 중 하나만 남아도 통과했다. 세 범주가 **전부** 있어야 한다 --
        # 새 방법(미분류) / 방법 없음(상수표) / 아직 없음(골격)은 서로 다른 사건이다.
        when=r"^MARKERS\s*=",
        require=[r'"미분류"', r'"상수표\(계산 없음\)"', r'"골격/미완"'],
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
        # 방치한 것이 실제로 물린 자국이다.
        when=r"verdict\.append\(", require=[r"st in \(", r"set\(hist\)"],
    ),
    dict(
        id="판본-보존", rule="⑦",
        desc="노드 코드를 덮어쓰기 전에 이전 판을 남겨야 한다",
        why="수리가 코드를 그냥 덮어써서, 같은 알고리즘을 다듬은 것인지 갈아탄 것인지 "
            "잴 대상이 남지 않았다. 없는 축은 리뷰에 안 보인다",
        commit="7ec0f6d",
        globs=["orchestrator/planner.py"],
        when=r"run_dir / node\.component\)\.write_text", require=r"_snapshot_code\(",
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
    """실측 지연(145.55s)보다 마감이 큰지. 무늬가 아니라 값을 본다."""
    m = re.search(r'GEMINI_TIMEOUT",\s*"(\d+(?:\.\d+)?)"', path.read_text(encoding="utf-8"))
    if not m:
        return [f"{path.name}: GEMINI_TIMEOUT 기본값을 못 찾았다"]
    v = float(m.group(1))
    return [] if v > 145.55 else [f"{path.name}: 기본 마감 {v}s <= 실측 145.55s"]


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
                    bad.append((r, f"{rel}: 금지된 무늬 {hits}"))
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

    bad = run()
    if bad:
        print(f"규칙 위반 {len(bad)}건:")
        for r, msg in bad:
            print(f"\n  [{r['rule']}] {r['id']} -- {r['desc']}")
            print(f"      {msg}")
            print(f"      왜({r['commit']}): {r['why']}")
        return 1
    print(f"도구 규칙 {len(RULES)}개 -- 통과 "
          f"(무늬로 못 잡는 ②③⑥⑦ 는 tests/ 가 지킨다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
