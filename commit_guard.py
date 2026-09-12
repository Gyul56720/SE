"""commit_guard -- 봇이 **자가 수정을 커밋하기 전에** 지나야 하는 문 하나. 게이트 · 바뀐 파일의 검사 · main CI.

실측 2026-09-11: 봇의 커밋 경로(git_sync)는 게이트 15개만 보고 커밋했다. 테스트 전체는 CI 가
뒤늦게 돌렸는데 아무도 안 읽었고, main 이 하루 넘게 빨강인 채 자가 커밋이 35번 넘게 쌓였다.
사용자: "봇 커밋 경로에 테스트를 넣고, CI 빨강을 봇이 읽게 하라".

먼저 **영향 분석**(impact)을 보고에 붙인다 -- 이 변경이 어느 입구(답변 경로·커밋 경로·게이트)에
닿는지. 막지는 않는다. 그 다음 세 문을 차례로 지난다(모두 코드 판정):
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
메타기 = None      # (repo, 바뀐파일들) -> dict{commit, 말, FG, FR, INVALID}. None 이면 _메타 (mutate 원장을 읽는다)


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


def _ci캐시(repo: Path) -> dict:
    import ci_watch
    return ci_watch.캐시보기(repo)


def _바뀐py(repo: Path) -> "list[str] | None":
    from audit import run as A
    변경 = A.변경파일(repo, False)
    return None if 변경 is None else [c for c in 변경 if c.endswith(".py")]


# ------------------------------------------------------------------ 상태기계: R -> G, 그리고 Commit(P)
# 사용자(2026-09-12)의 수식을 그대로 코드 이름으로 둔다. 논리가 주석에만 있으면 읽을 수 없다.
#
#   S0 = R   필요한 도구를 아직 안 불렀다
#        G   필요한 도구를 부르고 기본 검증이 지났다
#
#   R --[ V(P) = 1 ]--> G            V 는 요구된 검증 도구들의 실행 결과
#
#   FG = {m | T(P)=PASS, T(Pm)=PASS, Pm ≢ P}            의미가 달라졌는데 Green 으로 남는다
#   FR = {m | T(P)=PASS, T(Pm)=FAIL, Cause(FAIL) ≠ m}   변형 탓이 아닌데 Red 로 판정된다
#   R(신뢰) = (FG ∪ FR)^c
#
#   Commit(P) = 1[ V(P)=1 ∧ T(P)=PASS ∧ (FG ∪ FR) = ∅ ]
#
# G 라는 것이 검증이 성공했다는 보장은 아니다 -- 그래서 G 뒤에 2차(mutate)가 FG·FR 을 뒤진다.
빨강, 초록 = "R", "G"


def 상태(도구호출됨: bool, 기본검증통과: bool) -> str:
    """S0. 도구를 안 불렀으면 R -- 기본 검증이 지났든 말든 그렇다(실측 없는 답이다)."""
    return 초록 if (도구호출됨 and 기본검증통과) else 빨강


def 전이(이전: str, V: int) -> str:
    """R --[V(P)=1]--> G. V=0 이면 G 에서도 R 로 되돌아간다(검증이 깨졌다)."""
    return 초록 if int(V) == 1 else 빨강


def 승인(V: int, T통과: bool, FG: int, FR: int) -> dict:
    """Commit(P) = 1[ V=1 ∧ T(P)=PASS ∧ (FG ∪ FR) = ∅ ]. **순수 지시함수 -- 아무것도 재지 않는다.**"""
    조건 = {"V(P)=1": int(V) == 1, "T(P)=PASS": bool(T통과), "FG=∅": int(FG) == 0, "FR=∅": int(FR) == 0}
    값 = 1 if all(조건.values()) else 0
    깨진것 = [k for k, v in 조건.items() if not v]
    return {"Commit": 값, "조건": 조건, "깨진것": 깨진것,
            "말": f"Commit(P) = {값}" + (f" · 깨진 조건: {', '.join(깨진것)}" if 깨진것 else " · 네 조건이 다 섰다")}


# ------------------------------------------------------------------ 커밋 판정: 여섯 항의 논리곱
# 사용자(2026-09-12):
#
#   Commit = BasePass ∧ ToolInvoked ∧ SemanticObservation ∧ EnvironmentInvariant
#            ∧ ¬FalseGreen ∧ ¬FalseRed
#
# 이 파일은 **판정하지 않는다.** 여섯 항은 저마다 다른 곳에서 이미 재어 온다 --
#
#   BasePass             이 파일의 검사 문 · gatekeeper · ci_watch(진짜 빨강)
#   ToolInvoked          relay.도구호출들 / bot_tools.이번셸  (도구 0회면 실측 없는 답이다)
#   SemanticObservation  rehearsal 의 공허 · 절제 · 열쇠 · 미정의 · 순환
#   EnvironmentInvariant mutate.환경보존됐나 · 단일변형인가 · 절제의 I1·I4
#   ¬FalseGreen          mutate 의 FALSE_GREEN 셈
#   ¬FalseRed            mutate 의 FALSE_RED 셈 (귀속은 복원 재실행으로 한다)
#
# 여기서 하는 일은 **논리곱과 보고**뿐이다.
#
# 항마다 세 값이다: 참 · 거짓 · 못잼. **거짓이 하나라도 있으면 막는다.** 못잼은 막지 않고 적는다 --
# 이 저장소의 규율이 "모르는 것은 초록이 아니다" 이고, 오늘 그 반쪽을 더 배웠다:
# **재지 않은 것을 빨강이라 하는 것도 같은 잘못이다**(거짓 빨강은 전부를 멈춘다).
참, 거짓, 못잼 = "참", "거짓", "못잼"
여섯항 = ("BasePass", "ToolInvoked", "SemanticObservation", "EnvironmentInvariant",
       "NoFalseGreen", "NoFalseRed")


def 여섯조건(항들: dict) -> dict:
    """{항: (상태, 말)} -> {commit, 거짓인항, 못잰항, 표}. **순수 함수 -- 아무것도 재지 않는다.**"""
    거짓인항 = [k for k in 여섯항 if (항들.get(k) or (못잼, ""))[0] == 거짓]
    못잰항 = [k for k in 여섯항 if (항들.get(k) or (못잼, ""))[0] == 못잼]
    표 = []
    for k in 여섯항:
        상태, 말 = 항들.get(k) or (못잼, "안 쟀다")
        표시 = {참: "O", 거짓: "X", 못잼: "?"}[상태]
        표.append(f"  [{표시}] {k:20} {말[:110]}")
    return {"commit": not 거짓인항, "거짓인항": 거짓인항, "못잰항": 못잰항, "표": "\n".join(표)}


def _메타(repo: Path, 바뀐: "list[str]") -> dict:
    """**2차 메타검증 결과를 읽어 온다 -- 여기서 판정하지 않는다.**

    사용자(2026-09-12): "Red/Green 은 1차 전이, FR/FG 는 그 판정이 옳았나를 보는 2차 메타층이고,
    Commit = Green ∧ (FR∪FG)^c 다." 판정은 mutate 가 하고, 이 문은 그 결과로 **막을지만** 정한다.
    커밋이 만진 파일에 걸린 FALSE_GREEN 만 본다 -- 저장소 어딘가의 옛 거짓초록으로 무관한 커밋을
    인질로 잡지 않는다. 사냥을 한 적이 없으면 `없다` 로 말하고 막지 않는다(모르는 것은 빨강도 아니다)."""
    import mutate
    걸린것 = mutate.파일별거짓초록(repo, 바뀐)
    마지막 = mutate.마지막사냥(repo)
    if not 마지막:
        return {"commit": True, "있나": False, "FG": 0, "FR": 0, "INVALID": 0,
                "말": "거짓초록 사냥 기록이 없다 -- `!거짓초록` 으로 재면 이 문이 켜진다(막지 않는다)"}
    r = mutate.신뢰(True, {mutate.거짓초록: len(걸린것),
                         mutate.거짓빨강: int(마지막.get(mutate.거짓빨강, 0)),
                         mutate.못쓸변형: int(마지막.get(mutate.못쓸변형, 0))})
    r["있나"] = True
    if 걸린것:
        r["말"] += " · 이 커밋이 만진 파일의 FALSE_GREEN: " + ", ".join(
            f"{x.get('target')} [{x.get('mutation', '')[:30]}]" for x in 걸린것[:4])
    return r


def 검사(repo=None, 게이트: bool = True, 감사: bool = True, ci: bool = True,
        빠름: bool = False, 메타: bool = True) -> "tuple[bool, str]":
    """빠름=True (봇의 답변 경로): **망을 안 타고**(CI 는 캐시) **.py 가 안 바뀌었으면 검사·CI 문을 건너뛴다.**

    실측 2026-09-11(이 문을 붙이고 나서 든 의심): git_sync 는 관리 채널 답변 경로 안에서 돈다
    (GIT_LOCK -> run_in_executor). 여기에 검사 전체와 GitHub 조회를 넣으면 **사람이 답을 몇 분 기다린다.**
    그리고 기억·원장만 적는 커밋(봇이 가장 자주 하는 일)까지 main 빨강에 인질이 된다.
    그래서 코드가 안 바뀐 커밋은 게이트만 지나고, 코드가 바뀐 커밋만 검사·CI 문을 지난다.
    """
    repo = Path(repo or REPO)
    줄: list[str] = []
    통과 = True
    항들: dict = {}                                   # 여섯 항 -- 각 문이 지나가며 채운다

    if 빠름:
        바뀐 = _바뀐py(repo)
        if 바뀐 is None:
            줄.append("  (경고) git 을 못 봐 무엇이 바뀌었는지 모른다 -- 게이트만 지난다")
            감사 = ci = False
        elif not 바뀐:
            줄.append("  코드(.py) 변경 없음 -- 기억·원장 커밋이므로 게이트만 지난다")
            감사 = ci = False

    if 감사:                                          # 코드가 바뀐 커밋에만 -- 무엇에 딸려 움직이는지 먼저 보인다
        try:
            import impact
            r영 = impact.영향(repo, 커밋=False)
            if r영["파일"]:
                줄.append(impact.보고(r영))
        except Exception as e:                        # noqa: BLE001 -- 보고용이다. 막지 않는다
            줄.append(f"  (영향 분석 못 함: {type(e).__name__})")

    if 게이트:
        try:
            ok, 고친것, 요약 = (게이트기 or _게이트)(repo)
        except Exception as e:                        # noqa: BLE001 -- 문이 고장 나면 닫힌 문이다
            ok, 고친것, 요약 = False, [], f"게이트를 못 돌렸다: {type(e).__name__}: {str(e)[:120]}"
        for x in 고친것:
            줄.append(f"  고침 {x}")
        if not ok:
            통과 = False
            항들["BasePass"] = (거짓, f"게이트 위반: {요약[:80]}")
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
            항들["BasePass"] = ((거짓, f"바뀐 파일이 거는 검사 {len(빨강)}개가 빨강") if 빨강
                             else 항들.get("BasePass") or (참, f"게이트 통과 · 검사 {len(r['결과'])}개 초록"))
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
            c = (CI기 or (_ci캐시 if 빠름 else _ci))(repo)
        except Exception as e:                        # noqa: BLE001
            c = {"상태": "못잼", "실패": [], "말": f"CI 를 못 읽었다: {type(e).__name__}"}
        if c["상태"] == "빨강":
            통과 = False
            항들["BasePass"] = (거짓, "main CI 빨강 -- 빨강 위에 쌓지 않는다")
            줄.append("[CI 차단] " + c["말"])
            줄.append("  빨강 위에 자가 수정을 쌓지 않는다. 위 검사부터 고쳐 main 을 초록으로 만들어라"
                     " -- 사람의 결정이 필요한 검사(문체 규칙 등)면 그렇다고 사람에게 말하라")
        elif c["상태"] == "못잼":
            줄.append("  (경고) " + c["말"])
        else:
            줄.append("  " + c["말"])

    if 메타 and not 빠름:
        # 1차(게이트·검사·CI)가 다 초록이어도, 그 초록이 거짓이면 커밋하지 않는다.
        바뀐 = _바뀐py(repo) or []
        try:
            m = (메타기 or _메타)(repo, 바뀐)
        except Exception as e:                        # noqa: BLE001 -- 문이 고장 나면 알리고 막지 않는다
            m = {"commit": True, "있나": False, "말": f"메타검증을 못 읽었다: {type(e).__name__}"}
        if not m.get("있나"):
            줄.append("  (경고) " + m["말"])
            항들["NoFalseGreen"] = (못잼, "거짓초록 사냥 기록이 없다 -- `!거짓초록` 으로 재라")
            항들["NoFalseRed"] = (못잼, "같다")
            항들["EnvironmentInvariant"] = (못잼, "변형 판정을 안 돌려 환경 불변식을 못 쟀다")
        else:
            FG, FR, 무효 = int(m.get("FG", 0)), int(m.get("FR", 0)), int(m.get("INVALID", 0))
            항들["NoFalseGreen"] = ((거짓, f"FALSE_GREEN {FG}개 -- 그 초록은 못 믿는다") if FG
                                 else (참, "FALSE_GREEN 0"))
            항들["NoFalseRed"] = ((거짓, f"FALSE_RED {FR}개 -- 변형과 무관한 실패를 잡힌 것으로 셀 수 없다") if FR
                               else (참, "FALSE_RED 0"))
            항들["EnvironmentInvariant"] = ((거짓, f"판정에 쓸 수 없는 것 {무효}개(Δ≠{{m}} · E(P)≠E(Pm))") if 무효
                                         else (참, "단일 변형 · 환경 동일이 지켜졌다"))
            if not m.get("commit"):
                통과 = False
                줄.append("[메타 차단] " + m["말"])
            else:
                줄.append("  메타검증 통과 -- " + m["말"])

    # ------- 여섯 항을 모아 논리곱으로 판정한다 (여기서 재지 않는다) -------
    if "BasePass" not in 항들:
        항들["BasePass"] = (참, "게이트 통과(코드 변경 없음 -- 검사·CI 문은 건너뛴다)") if 빠름 else (못잼, "안 쟀다")
    항들.setdefault("ToolInvoked", _도구항(빠름))
    항들.setdefault("SemanticObservation", _의미항(repo))
    여섯 = 여섯조건(항들)
    if not 여섯["commit"]:
        통과 = False
    줄.append("Commit = BasePass ∧ ToolInvoked ∧ SemanticObservation ∧ EnvironmentInvariant"
             " ∧ ¬FalseGreen ∧ ¬FalseRed")
    줄.append(여섯["표"])
    _도구상태 = (항들.get("ToolInvoked") or (못잼, ""))[0]
    _바탕상태 = (항들.get("BasePass") or (못잼, ""))[0]
    S0 = 상태(_도구상태 != 거짓, _바탕상태 != 거짓)
    _V = 1 if (여섯["commit"] and _바탕상태 != 거짓) else 0
    _FG = 1 if "NoFalseGreen" in 여섯["거짓인항"] else 0
    _FR = 1 if "NoFalseRed" in 여섯["거짓인항"] else 0
    승 = 승인(_V, _바탕상태 != 거짓, _FG, _FR)
    줄.append(f"  S0 = {S0} · 전이 V(P)={_V} -> {전이(S0, _V)} · {승['말']}")
    줄.append(f"  -> {'허용' if 통과 else '막음'}"
             + (f" · 거짓인 항: {', '.join(여섯['거짓인항'])}" if 여섯["거짓인항"] else "")
             + (f" · 못 잰 항: {', '.join(여섯['못잰항'])}" if 여섯["못잰항"] else ""))
    return 통과, "\n".join(줄)


def _도구항(빠름: bool) -> tuple:
    """ToolInvoked -- 이번 턴에 도구가 돌았나. 봇 경로 밖(CLI·검사)에서는 못잼이다."""
    try:
        import bot_tools
        import relay
    except Exception:                                 # noqa: BLE001 -- 봇 없는 기계에서는 못 들인다
        return (못잼, "봇 밖에서 돌았다 -- 도구 호출을 셀 수 없다")
    셸 = bot_tools.이번셸() or []
    이름들 = [n for v in (relay.마지막도구 or {}).values() for n in (v or [])]
    if 셸 or 이름들:
        return (참, f"도구 {len(이름들)}개 · 셸 {len(셸)}줄")
    return (못잼, "이번 턴에 센 도구가 없다 -- 원장·메모만 적는 커밋이면 그것이 맞다")


def _의미항(repo: Path) -> tuple:
    """SemanticObservation = Obs(T, P) -- **검사가 결과를 관찰하나.**

    두 곳에서 이미 재어 온다(여기서 재지 않는다):
      1. mutate.관찰됐나 -- 반환값 변형이 잡히는가. 이것이 관찰의 **측정**이다
      2. improve 원장의 관문 사슬(공허·절제·열쇠·미정의·순환) 판정
    1 이 있으면 그것을 쓰고, 없으면 2 를, 둘 다 없으면 못잼이다."""
    try:
        import mutate
        바뀐 = _바뀐py(repo) or []
        것 = [x for x in mutate.원장읽기(repo)
              if x.get("operator") in ("return_none", "return_zero", "return_minus1", "const_return")
              and str(x.get("target", "")).split(":")[0] in set(바뀐)]
        if 것:
            잡 = [x for x in 것 if x.get("outcome") == mutate.잡힘]
            산 = [x for x in 것 if x.get("outcome") == mutate.살아남음]
            if 산 and not 잡:
                return (거짓, f"Obs=0 -- 이 커밋이 만진 코드의 반환값 변형 {len(산)}개가 다 살았다(부르기만 한다)")
            if 잡:
                return (참, f"Obs=1 -- 반환값 변형 {len(잡)}/{len(것)}개가 잡혔다")
    except Exception:                                 # noqa: BLE001 -- 못 읽으면 아래 원장으로 간다
        pass
    막은것 = {"공허": "검사가 변경을 증언하지 않는다", "절제": "기능을 빼도 검사가 안 무너진다",
            "열쇠": "원장에 없는 열쇠를 읽는다", "미정의": "없는 이름을 부른다",
            "순환": "검사가 제 실행이 고친 원장을 읽는다"}
    try:
        from improve import run as I
        행들 = I.원장읽기(repo)[-40:]
    except Exception:                                 # noqa: BLE001
        return (못잼, "관문 기록을 못 읽었다")
    걸린 = [x.get("꼴") for x in 행들 if x.get("꼴") in 막은것]
    if 걸린:
        return (거짓, f"관문이 막았다: {걸린[-1]} -- {막은것[걸린[-1]]}")
    지난것 = [x for x in 행들 if x.get("꼴") in ("동의대기", "승인", "끝")]
    if 지난것:
        return (참, "관문 사슬(공허·절제·열쇠·미정의·순환)을 지난 패치다")
    return (못잼, "최근 패치 기록이 없다 -- 원장·메모만 적는 커밋이면 그것이 맞다")


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
