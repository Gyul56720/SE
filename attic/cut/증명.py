r"""증명 -- 유효성을 **산수로 확인되는 항**으로 내보낸다. solver 도 이 저장소도 필요 없다.

## 왜 이것이 따로 있나

`판정.유효판정` 은 `max{a z : z in X_VNE}` 를 MIP 로 푼다. 손 증명을 안 믿는다는 점에서
이미 독립이지만, 두 가지가 남는다.

    1. **그 인스턴스에서만** 증명이다. 손 증명이 주장하는 "모든 인스턴스" 는 확인 못 한다.
    2. 확인하려면 **scipy 와 이 저장소**가 있어야 한다. 남이 그 판정을 다시 하려면
       우리 코드를 믿어야 하고, 그러면 독립이 아니라 재현이다.

여기서 내는 것은 다르다. **어느 제약을 어떤 배수로 더했는지**를 적고, 쓴 줄을 통째로
증서 안에 넣는다. 확인하는 쪽은 곱하고 더하고 견주기만 한다 -- 연립방정식도, 탐색도,
부동소수점도 없다(`Fraction` 으로 정확히 센다).

## 꼴 (Chvátal-Gomory 1계)

정수 z >= 0 과 제약 `A z <= b`(등식은 양쪽) 에 대해, 배수 λ >= 0 (등식은 부호 자유) 를 잡으면

    λᵀA z <= λᵀb                       -- 곱해서 더한 것
    a <= λᵀA  (성분마다) 이고 z >= 0   -->  a z <= λᵀA z <= λᵀb
    a 가 정수면 a z 도 정수            -->  a z <= floor(λᵀb)

그래서 확인할 것은 셋뿐이다.

    (1) `<=` 줄의 배수가 음수가 아닌가
    (2) 성분마다 a[j] <= (λᵀA)[j] 인가
    (3) b >= λᵀb  (a 가 정수면 b >= floor(λᵀb))

**z >= 0 을 쓴다.** (2) 가 등호가 아니라 부등호인 까닭이 그것이므로 증서에 명시한다.

## 이 증서가 닿지 않는 곳 -- 숨기지 않는다

덮개 부등식이 늘 1계 CG 로 서는 것은 아니다. 아래 `노드덮개증서` 의 유도는
`|T| * min_{v in T} cpu(v) > sum_{u in S} cap(u)` 일 때만 선다. 덮개 조건
`sum_{v in T} cpu(v) > sum cap(u)` 보다 **좁다**(cpu 가 다 같으면 둘이 같아진다).

좁은 만큼 못 내는 증서가 있고, 그때는 `못잼` 이다 -- **"증서가 없다" 를 "무효다" 로도
"유효다" 로도 읽지 않는다.** 그 자리는 여전히 `유효판정`(MIP)과 손 증명이 받친다.

## 두 물음을 갈라 묻는다

    확인(증서)        산수가 맞나            -- 이 저장소도 solver 도 필요 없다
    줄대조(p, 증서)   인용한 줄이 진짜 그 모델의 줄인가 -- 여기서만 FF 를 쓴다

둘을 합치면 "이 부등식은 이 모델에서 유효하다" 가 된다. 갈라 두는 까닭은, 남이 증서만
받아도 (1) 을 혼자 할 수 있어야 하기 때문이다.
"""

from __future__ import annotations

from fractions import Fraction

맞다 = "맞다"
어긋난다 = "어긋난다"
못잼 = "못잼"


def _분수(x) -> Fraction:
    """float 을 **정확히** 분수로. 0.1 이 1/10 이 아니라는 것까지 그대로 들고 간다."""
    return Fraction(x).limit_denominator(10 ** 9) if isinstance(x, float) else Fraction(x)


def _정수인가(x: Fraction) -> bool:
    return x.denominator == 1


# ------------------------------------------------------------------ 확인 (산수만)
def 확인(증서: dict) -> dict:
    r"""증서의 산수가 맞나. **이 파일 말고는 아무것도 안 쓴다** -- numpy 도 scipy 도 FF 도.

    돌려주는 것: {판정, 어긋남, 말, 합우변, 내림}
    판정은 셋이다 -- 맞다 / 어긋난다 / 못잼(증서가 꼴을 안 갖췄다).
    """
    어긋: list = []
    try:
        a = {k: _분수(v) for k, v in (증서["부등식"]["a"] or {}).items()}
        b = _분수(증서["부등식"]["b"])
        줄들 = list(증서["쓴줄"])
    except (KeyError, TypeError, ValueError) as e:
        return {"판정": 못잼, "어긋남": [], "말": f"증서 꼴이 아니다: {type(e).__name__}: {e}"}
    if not 줄들:
        return {"판정": 못잼, "어긋남": [], "말": "쓴 줄이 하나도 없다 -- 더할 것이 없다"}

    합계수: dict = {}
    합우변 = Fraction(0)
    for i, 줄 in enumerate(줄들):
        꼴 = 줄.get("꼴")
        if 꼴 not in ("<=", "="):
            return {"판정": 못잼, "어긋남": [], "말": f"{i}번 줄의 꼴이 '<=' 도 '=' 도 아니다: {꼴!r}"}
        try:
            배수 = _분수(줄["배수"])
            우변 = _분수(줄["우변"])
            계수 = {k: _분수(v) for k, v in (줄["계수"] or {}).items()}
        except (KeyError, TypeError, ValueError) as e:
            return {"판정": 못잼, "어긋남": [], "말": f"{i}번 줄을 못 읽는다: {type(e).__name__}: {e}"}
        # (1) `<=` 줄의 배수는 음수면 안 된다 -- 음수를 곱하면 부등호가 뒤집힌다
        if 꼴 == "<=" and 배수 < 0:
            어긋.append(f"{줄.get('이름', i)}: `<=` 줄에 음수 배수 {배수} -- 부등호가 뒤집힌다")
        if 배수 == 0:
            continue
        for k, v in 계수.items():
            합계수[k] = 합계수.get(k, Fraction(0)) + 배수 * v
        합우변 += 배수 * 우변

    # (2) 성분마다 a[j] <= (λᵀA)[j]  -- z >= 0 이라 이것으로 충분하다
    for k, v in a.items():
        if v > 합계수.get(k, Fraction(0)):
            어긋.append(f"{k}: a {v} > 더한 계수 {합계수.get(k, Fraction(0))} -- z>=0 으로도 못 덮는다")

    # (3) b >= λᵀb  (a 가 정수면 내림까지)
    정수a = all(_정수인가(v) for v in a.values())
    쓸우변 = 합우변
    내림 = False
    if 정수a and 증서.get("정수성", True):
        import math
        쓸우변 = Fraction(math.floor(합우변))
        내림 = 쓸우변 != 합우변
    if b < 쓸우변:
        어긋.append(f"b {b} < 더한 우변 {쓸우변}"
                   + (f" (= floor {합우변})" if 내림 else "") + " -- 부등식이 너무 세다")

    if 어긋:
        return {"판정": 어긋난다, "어긋남": 어긋, "합우변": str(합우변), "내림": 내림,
                "말": f"**증서가 안 선다** ({len(어긋)}곳): " + " · ".join(어긋[:3])}
    return {"판정": 맞다, "어긋남": [], "합우변": str(합우변), "내림": 내림,
            "말": f"a z <= {합우변}" + (f" -> 내림 {쓸우변}" if 내림 else "")
                + f" <= b {b} -- **산수로 선다**(z>=0 · {len(줄들)}줄)"}


# ------------------------------------------------------------------ 줄대조 (모델과 맞나)
def 줄대조(p, 증서: dict, 허용: float = 1e-9) -> dict:
    """증서가 인용한 줄이 **진짜 그 FF 의 줄인가.** 여기서만 모델을 본다.

    증서 안의 계수를 그대로 믿으면, 없는 제약을 지어내 무엇이든 증명할 수 있다."""
    import numpy as np
    변수 = 이름표(p)
    이름줄 = {}
    for 이름, 줄, 우 in zip(p.eq이름 or [], p.A_eq, p.b_eq):
        이름줄[이름] = ("=", 줄, float(우))
    for 이름, 줄, 우 in zip(p.ub이름 or [], p.A_ub, p.b_ub):
        이름줄[이름] = ("<=", 줄, float(우))
    어긋 = []
    for 줄 in 증서.get("쓴줄") or []:
        이름 = 줄.get("이름")
        if 이름 not in 이름줄:
            어긋.append(f"{이름}: 이 모델에 그런 줄이 없다")
            continue
        꼴, 계수, 우변 = 이름줄[이름]
        if 줄.get("꼴") != 꼴:
            어긋.append(f"{이름}: 꼴이 다르다 (증서 {줄.get('꼴')} vs 모델 {꼴})")
        if abs(float(줄.get("우변", 0)) - 우변) > 허용:
            어긋.append(f"{이름}: 우변이 다르다 (증서 {줄.get('우변')} vs 모델 {우변})")
        적힌 = {k: float(v) for k, v in (줄.get("계수") or {}).items()}
        for j, 값 in enumerate(계수):
            if abs(float(적힌.get(변수[j], 0.0)) - float(값)) > 허용:
                어긋.append(f"{이름}: {변수[j]} 계수가 다르다 "
                           f"(증서 {적힌.get(변수[j], 0.0)} vs 모델 {값})")
                break
        남은 = set(적힌) - set(변수)
        if 남은:
            어긋.append(f"{이름}: 모델에 없는 변수를 적었다 {sorted(남은)[:3]}")
    if 어긋:
        return {"판정": 어긋난다, "어긋남": 어긋,
                "말": f"**인용한 줄이 모델과 다르다** ({len(어긋)}곳): " + " · ".join(어긋[:2])}
    return {"판정": 맞다, "어긋남": [],
            "말": f"인용한 {len(증서.get('쓴줄') or [])}줄이 모델의 줄과 같다"}


def 이름표(p) -> list:
    """열 번호 -> 변수 이름. 증서가 숫자가 아니라 이름으로 말하게 한다."""
    이름 = [None] * len(p.c)
    for (v, u), j in p.x자리.items():
        이름[j] = f"x[{v},{u}]"
    for (e, 호), j in p.y자리.items():
        이름[j] = f"y[{e},{호}]"
    return 이름


def _줄뽑기(p, 이름: str, 배수) -> dict:
    """그 이름의 줄을 **통째로** 증서에 담는다(0 이 아닌 계수만). 자기완결이 요점이다."""
    변수 = 이름표(p)
    for 목, A, bb, 꼴 in ((p.eq이름 or [], p.A_eq, p.b_eq, "="),
                        (p.ub이름 or [], p.A_ub, p.b_ub, "<=")):
        if 이름 in 목:
            i = 목.index(이름)
            계수 = {변수[j]: float(v) for j, v in enumerate(A[i]) if abs(float(v)) > 1e-12}
            return {"이름": 이름, "꼴": 꼴, "계수": 계수, "우변": float(bb[i]), "배수": float(배수)}
    raise KeyError(f"그런 줄이 없다: {이름}")


# ------------------------------------------------------------------ 노드덮개의 CG 증서
def 노드덮개증서(p, S, T) -> dict:
    r"""`sum_{v in T} sum_{u in S} x[v,u] <= |T|-1` 의 1계 CG 증서. 못 내면 `못잼`.

    **유도.** CPU 줄(u in S)에 배수 λ, 배치 등식(v in T)에 배수 μ 를 준다.

        x[v,u] 의 더한 계수  =  λ*cpu(v) + μ      (v in T, u in S)
        더한 우변           =  λ*C + |T|*μ        (C = sum_{u in S} cap(u))

    a 는 v in T, u in S 에서 1 이므로 `λ*m + μ >= 1` 이면 (2)가 선다(m = min cpu).
    μ = max(0, 1 - λm) 으로 두면 더한 우변이 `|T| - λ(|T|m - C)` 이고,
    이것이 `|T|` 보다 작아야 내림이 `|T|-1` 이하로 떨어진다. 즉 **|T|*m > C** 가 조건이다.

    덮개 조건(`sum_{v in T} cpu(v) > C`)보다 좁다. cpu 가 다 같으면 둘이 같다."""
    S, T = sorted(S), sorted(T)
    if not S or not T:
        return {"있나": False, "말": "S 나 T 가 비었다"}
    try:
        cap = {u: float(p.바탕.노드[u]["cpu"]) for u in S}
        cpu = {v: float(p.요청.노드[v]["cpu"]) for v in T}
    except KeyError as e:
        return {"있나": False, "말": f"S·T 에 없는 노드가 있다: {e}"}
    C = sum(cap.values())
    m = min(cpu.values())
    if len(T) * m <= C:
        return {"있나": False,
                "말": f"**1계 CG 로는 못 세운다** (|T|*min cpu = {len(T)}*{m} = {len(T) * m} "
                    f"<= sum cap = {C}). 덮개 조건은 서도 이 증서는 더 좁다 -- 못잼이지 "
                    "무효가 아니다"}
    # λ 는 (2)를 아슬아슬하게 채우는 가장 작은 것으로: λ*m = 1 -> λ = 1/m, μ = 0
    λ = Fraction(1) / _분수(m)
    μ = Fraction(0)
    쓴줄 = [_줄뽑기(p, f"CPU[{u}]", λ) for u in S]
    if μ:
        쓴줄 += [_줄뽑기(p, f"배치[{v}]", μ) for v in T]
    a = {f"x[{v},{u}]": 1 for v in T for u in S}
    증 = {
        "이름": "노드덮개",
        "부등식": {"a": a, "b": len(T) - 1},
        "쓴줄": 쓴줄,
        "정수성": True,
        "가정": ["z >= 0", "z 는 정수"],
        "유도": (f"CPU 줄 {len(S)}개에 배수 {λ} (= 1/min cpu). 더한 우변 {λ * _분수(C)} 를 "
               f"내림하면 {int(λ * _분수(C))} <= |T|-1 = {len(T) - 1}"),
    }
    return {"있나": True, "증서": 증, "λ": str(λ), "μ": str(μ), "C": C, "m": m}


def 보고(증서: dict, 산수: dict, 대조: dict = None) -> str:
    줄 = [f"**증서 · {증서.get('이름', '?')}**",
         f"  부등식  {len(증서['부등식']['a'])}항 <= {증서['부등식']['b']}",
         f"  쓴 줄   {len(증서['쓴줄'])}개 · 가정 {', '.join(증서.get('가정') or [])}",
         f"  유도    {증서.get('유도', '')}",
         f"  산수    **{산수['판정']}** -- {산수['말']}"]
    if 대조 is not None:
        줄.append(f"  줄대조  **{대조['판정']}** -- {대조['말']}")
    줄.append("  **산수는 이 저장소 없이 확인된다.** 줄대조만 모델을 본다")
    return "\n".join(줄)


# ------------------------------------------------------------------ CG-1 폐포 소속 (자동)
폐포안 = "폐포안"
폐포밖 = "폐포밖"


def cg폐포판정(p, a: dict, b: float, 정수성: bool = True, 시한초: float = 30.0) -> dict:
    r"""**f = (a,b) 가 기초 행 넷(배치·일대일·CPU·대역·흐름보존)의 CG-1 결합인가.**

    `판정.독립판정` 과 **다른 물음**이다. 그것은 "다른 여섯 연산자의 *이 인스턴스* 후보를
    LP 에 얹고도 자르는가" 였다 -- 비교 대상이 다른 템플릿이었다. 여기서는 **모델 자신의
    기초 행**(`p.A_eq` · `p.A_ub`, 그 위 다른 부등식은 안 얹는다)만 놓고 λ >= 0(등식은
    부호 자유)을 자동으로 찾는다. `노드덮개증서` 가 손으로 하던 일 -- 어느 배수로 어느
    줄을 더하면 이 부등식이 나오나 -- 을 일반화한 것이다.

        min λᵀb   subject to   λᵀA >= a (성분마다), λ_ub >= 0
        찾으면(정수 a 면 내림까지) b >= 최소값  ->  **폐포안**
        못 찾으면(그 LP 가 infeasible)          ->  **폐포밖** -- 어떤 배수로도 안 된다
        수치가 애매하면                          ->  **못잼**

    **찾는 것은 solver 가 한다 -- 이것은 탐색이다.** `증명.확인` 처럼 solver 없이 도는
    함수가 아니다. 다만 찾고 나면 λ 를 유리수로 되돌려 `확인` 으로 **다시** 검증한다 --
    LP 가 준 부동소수점 λ 를 그대로 믿지 않는다. 그래서 최종 판정은 여전히 산수가 낸다.

    **닿는 범위.** 이것은 **rank-1** CG 다 -- 기초 행을 한 번 결합해서 나오는 것만 본다.
    반복 CG(그 결과에 또 CG를 먹이는 것)는 더 많은 것을 폐포 안에 넣을 수 있고, 여기서는
    안 잰다. `폐포밖` 은 "rank-1 로는 못 만든다" 이지 "독립이다" 가 아니다."""
    import numpy as np
    from .판정 import 벡터

    try:
        a벡 = 벡터(p, a)
    except KeyError as e:
        return {"판정": 못잼, "말": f"a 를 못 읽는다: {e}"}
    try:
        from scipy.optimize import linprog
    except ImportError as e:
        return {"판정": 못잼, "말": f"scipy 가 없다: {e}"}

    n_eq, n_ub = len(p.b_eq), len(p.b_ub)
    if n_eq + n_ub == 0:
        return {"판정": 폐포밖, "말": "이 모델에 기초 행이 없다"}
    # A_ub_lp x <= b_ub_lp 꼴로: λᵀA >= a 를 -λᵀA <= -a 로 뒤집는다
    합A = np.vstack([p.A_eq, p.A_ub]) if n_eq and n_ub else (p.A_eq if n_eq else p.A_ub)
    합b = np.concatenate([p.b_eq, p.b_ub]) if n_eq and n_ub else (p.b_eq if n_eq else p.b_ub)
    A_lp = -합A.T                          # 변수: λ (길이 n_eq+n_ub). 행: 원 변수 하나마다
    b_lp = -a벡
    경계 = [(-np.inf, np.inf)] * n_eq + [(0, np.inf)] * n_ub
    목적 = 합b                             # min λᵀb

    try:
        r = linprog(목적, A_ub=A_lp, b_ub=b_lp, bounds=경계, method="highs",
                   options={"time_limit": 시한초})
    except Exception as e:                                          # noqa: BLE001
        return {"판정": 못잼, "말": f"{type(e).__name__}: {e}"[:140]}

    if r.status == 2:                                                # infeasible
        return {"판정": 폐포밖, "말": "**어떤 배수로도 a <= λᵀA 를 못 채운다** "
                                  "-- rank-1 CG 폐포 밖이다"}
    if r.status != 0 or r.x is None:
        return {"판정": 못잼, "말": f"solver status={r.status}: {getattr(r, 'message', '')}"[:140]}

    λ = r.x
    # **먼저 solver 의 raw 최적값으로 걸러낸다.** 유리수로 되돌리기 전에 이미 최적값이
    # b 보다 뚜렷이 크면(반올림으로 메꿀 수 없을 만큼) 그건 "반올림 오차" 가 아니라
    # **정말로 못 만드는 것**이다 -- solver 가 낸 최적값 자체가 도달 가능한 하한이므로.
    # 실측: 처음엔 이 구분이 없어서 `b=-1` 처럼 뚜렷이 안 되는 경우까지 "못잼(반올림 오차)"
    # 로 뭉개고 있었다. 얼마나 벌어졌는지로 가른다 -- 작은 틈만 반올림 탓으로 돌린다.
    최적값 = float(r.fun)
    if 정수성 and all(float(v).is_integer() for v in a.values()):
        import math
        근사최적 = math.floor(최적값 + 1e-7)
    else:
        근사최적 = 최적값
    if 근사최적 > b + 1e-6:
        return {"판정": 폐포밖,
                "말": f"**LP 최적값 자체가 b 를 못 채운다** (min λᵀb ≈ {최적값:.6g}"
                    + (f" -> 내림 {근사최적}" if 근사최적 != 최적값 else "")
                    + f" > b {b}) -- 반올림이 아니라 진짜로 안 된다"}

    # ---- 부동소수점 λ 를 유리수로 되돌려 **산수로 다시 검증한다** ----
    이름들 = (list(p.eq이름 or []) + list(p.ub이름 or []))
    꼴들 = (["="] * n_eq) + (["<="] * n_ub)
    쓴줄 = []
    for i, (이름, 꼴, λi) in enumerate(zip(이름들, 꼴들, λ)):
        if abs(λi) < 1e-9:
            continue
        try:
            줄 = _줄뽑기(p, 이름, Fraction(λi).limit_denominator(10 ** 6))
        except KeyError:
            return {"판정": 못잼, "말": f"줄 이름을 못 찾았다: {이름}"}
        쓴줄.append(줄)
    if not 쓴줄:
        return {"판정": 폐포밖, "말": "λ 가 전부 0 이다 -- a 가 이미 0 이 아닌 한 뜻이 없다"}

    변수 = 이름표(p)
    a_str = {변수[j]: float(v) for j, v in enumerate(a벡) if abs(float(v)) > 1e-12}
    증서 = {"이름": "cg자동", "부등식": {"a": a_str, "b": float(b)},
          "쓴줄": 쓴줄, "정수성": 정수성}
    산 = 확인(증서)
    if 산["판정"] == 맞다:
        return {"판정": 폐포안, "말": f"**폐포 안이다** -- {산['말']}", "증서": 증서, "확인": 산}
    if 산["판정"] == 어긋난다:
        return {"판정": 못잼, "말": f"LP 는 찾았는데 유리수로 되돌리니 안 선다"
                                  f"(반올림 오차) -- {산['말'][:80]}", "증서": 증서}
    return {"판정": 못잼, "말": 산["말"]}
