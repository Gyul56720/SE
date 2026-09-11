"""commit_guard -- 봇이 **자가 수정을 커밋하기 전에** 지나야 하는 문 하나. 게이트 · 바뀐 파일의 검사 · main CI.

실측 2026-09-11: 봇의 커밋 경로(git_sync)는 게이트 15개만 보고 커밋했다. 테스트 전체는 CI 가
뒤늦게 돌렸는데 아무도 안 읽었고, main 이 하루 넘게 빨강인 채 자가 커밋이 35번 넘게 쌓였다.
사용자: "봇 커밋 경로에 테스트를 넣고, CI 빨강을 봇이 읽게 하라".

세 문을 차례로 지난다(모두 코드 판정):
  1. 게이트 -- gatekeeper.run_gates(고치기=True): 고칠 수 있는 위반은 고치고, 남는 위반은 막는다
  2. 검사   -- audit.감사(커밋=False): **바뀐 .py 가 거는 검사만** 작업 트리 사본에서 돌린다.
              빨강이면 막는다. 검사를 못 돌렸으면(끝값 3 · git 못 봄) **막는다** -- 검사하지 않은
              초록불이 검사한 빨간불보다 나쁘다(fail-closed)
  3. CI     -- ci_watch.보기(): main 의 마지막 gates.yml 이 빨강이면 막는다 -- 빨강 위에 쌓지 않는다.
              그 검사부터 고치라고 이름을 준다. 못 읽었으면(못잼) 경고만 -- 근거 없이 막지 않는다

돌려주는 것: (통과, 보고). 보고는 사람에게 그대로 보여도 되는 글이다.

    python3 commit_guard.py            # 지금 작업 트리에 대해 문 셋을 지나 본다. 끝값 0 통과 · 1 막힘
    python3 commit_guard.py --배선     # 임포트만 (읽기 점검)
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent

# 검사가 꽂는 자리. None 이면 진짜 기관.
게이트기 = None    # (repo) -> (통과:bool, 고친것:list[str], 위반요약:str)
감사기 = None      # (repo) -> dict  (audit.감사 의 꼴)
CI기 = None        # (repo) -> dict  (ci_watch.보기 의 꼴)


def _게이트(repo: Path):
    import gatekeeper
    report = gatekeeper.run_gates(repo, 고치기=True)
    return report.passed, list(getattr(report, "고친것", [])), ("" if report.passed else report.summary())


def _감사(repo: Path) -> dict:
    from audit import run as A
    return A.감사(repo, 커밋=False, 초=180)


def _ci(repo: Path) -> dict:
    import ci_watch
    return ci_watch.보기(repo)


def 검사(repo=None, 게이트: bool = True, 감사: bool = True, ci: bool = True) -> "tuple[bool, str]":
    repo = Path(repo or REPO)
    줄: list[str] = []
    통과 = True

    if 게이트:
        try:
            ok, 고친것, 요약 = (게이트기 or _게이트)(repo)
        except Exception as e:                        # noqa: BLE001 -- 문이 고장 나면 닫힌 문이다
            ok, 고친것, 요약 = False, [], f"게이트를 못 돌렸다: {type(e).__name__}: {str(e)[:120]}"
        for x in 고친것:
            줄.append(f"  고침 {x}")
        if not ok:
            통과 = False
            줄.append("[게이트 차단] 커밋하지 않았다.\n" + 요약)

    if 감사 and 통과:
        try:
            r = (감사기 or _감사)(repo)
        except Exception as e:                        # noqa: BLE001
            r = {"결과": None, "안덮임": [], "안봄": [], "변경": None, "오류": f"{type(e).__name__}: {str(e)[:120]}"}
        if r.get("결과") is None:
            통과 = False
            줄.append("[검사 차단] 바뀐 파일의 검사를 못 돌렸다 -- " + (r.get("오류") or "git 을 못 봤다")
                     + ". **검사하지 않은 초록불은 초록이 아니다** -- 커밋하지 않았다")
        else:
            빨강 = [(t, 끝, 꼬리) for t, 끝, 꼬리 in r["결과"] if 끝 != 0]
            초록 = [t for t, 끝, _ in r["결과"] if 끝 == 0]
            if 초록:
                줄.append(f"  검사 통과 {len(초록)}개: " + ", ".join(Path(t).name for t in 초록))
            if r.get("안덮임"):
                줄.append("  검사 없는 .py 변경(버그가 샌다면 여기): " + ", ".join(r["안덮임"][:5]))
            if 빨강:
                통과 = False
                줄.append(f"[검사 차단] 바뀐 파일이 거는 검사 {len(빨강)}개가 빨강 -- 커밋하지 않았다. "
                         "먼저 고쳐라(재현: `python3 <검사>`; 막히면 repair 도구에 재현 명령 + 오류를 줘라)")
                for t, 끝, 꼬리 in 빨강:
                    줄.append(f"  ✗ {t} (끝값 {끝})")
                    for x in (꼬리 or [])[-3:]:
                        줄.append(f"      {x[:160]}")

    if ci:
        try:
            c = (CI기 or _ci)(repo)
        except Exception as e:                        # noqa: BLE001
            c = {"상태": "못잼", "실패": [], "말": f"CI 를 못 읽었다: {type(e).__name__}"}
        if c["상태"] == "빨강":
            통과 = False
            줄.append("[CI 차단] " + c["말"])
            줄.append("  빨강 위에 자가 수정을 쌓지 않는다. 위 검사부터 고쳐 main 을 초록으로 만들어라"
                     " -- 사람의 결정이 필요한 검사(문체 규칙 등)면 그렇다고 사람에게 말하라")
        elif c["상태"] == "못잼":
            줄.append("  (경고) " + c["말"])
        else:
            줄.append("  " + c["말"])

    return 통과, "\n".join(줄)


def main() -> int:
    if "--배선" in sys.argv:
        import gatekeeper, ci_watch  # noqa: F401,E401
        from audit import run  # noqa: F401
        print("commit_guard 배선: 게이트 · 검사 · CI 임포트 됨")
        return 0
    ok, 보고 = 검사()
    print(보고)
    print("통과 -- 커밋해도 된다" if ok else "막힘 -- 커밋하지 마라")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
