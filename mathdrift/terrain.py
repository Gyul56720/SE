"""**스키마 통로** -- 원장이 아는 것을 다음 세대에게 넘긴다. 호출 0회.

지금까지 자식이 본 것은 부모의 `식`·`점`·`정의역` **세 칸**이 전부였다. 원장에 공간이
하나든 여든다섯이든 프롬프트의 모양이 같았다 -- **원장이 커져도 아는 것이 안 늘었다.**
추론은 스키마와 논리로 되는데, 스키마 쪽 통로가 세 칸 폭이었던 것이다.

## 판정은 한 방울도 안 흐른다

이 저장소는 심판을 프롬프트에 실었다가 두 번 데었다. 원고가 관문에 맞춰 균질해졌다.
그 규칙은 옳다. 다만 그때 실린 것은 **가치 판단**이었다 -- 점수, 통과/탈락, 무엇을 내라는
사양. 여기서 흐르는 것은 그것이 아니다.

    실으면 안 되는 것          실어도 되는 것
    점수 · 통과 여부           지금까지 무엇이 있는가
    "이것이 좋다"              "이 부모에서 이미 이런 식이 나왔다"
    "이렇게 써라"              "정의역이 이렇게 갈려 있다"

가르는 자리는 하나다. **겨눌 수 있는 수인가.** 점수는 겨눌 수 있고 그래서 균질해진다.
지형은 겨눌 것이 없다 -- 그냥 거기에 무엇이 있다는 말이다.

그래서 이 파일은 `재현` · `판정` · `잰것` · `어긋남` 을 **한 칸도 읽지 않는다.**
읽는 것은 `식` · `정의역` · 계보뿐이다. 검사가 그것을 강제한다.

## 그리고 이것도 게이트가 아니다

아무것도 안 거른다. 형제 목록은 **있는 그대로** 나가고, 몇 개만 실리는 것은 프롬프트
길이 때문이지 골라서가 아니다.

## 균질해지는지를 같이 잰다

두 번 다 균질해진 뒤에야 알았다. 이름을 눈으로 보고서야. 이번에는 **자를 같이 낸다** --
같은 부모에서 나온 형제끼리 기호가 얼마나 겹치는가(`spread_of`). 통로가 모델을
베끼게 만들면 이 수가 오른다. 통로를 켠 런과 끈 런을 견주면 된다.

    MATHDRIFT_SCHEMA=0 python3 mathdrift/spread.py --n 50   # 통로를 닫고 돌린다
    python3 mathdrift/spread.py --terrain                   # 무엇이 실리는지 본다
    python3 mathdrift/spread.py --terrain S1                # 그 부모 자리에서
"""
from __future__ import annotations

import os

from mathdrift import act as ACT
from mathdrift import mono as MO
from mathdrift import space as SP

# 통로를 닫으려면 0. 견주려고 있는 스위치다 -- 통로가 균질하게 만드는지 재려면
# 같은 씨앗으로 켜고 끄고 두 번 돌려야 한다.
ON = os.environ.get("MATHDRIFT_SCHEMA", "1") != "0"

# 형제를 몇 개까지 보여 주나. 늘리면 프롬프트가 원장으로 찬다 -- `novel/` 이 겪은 그것.
SIBS = int(os.environ.get("MATHDRIFT_SCHEMA_SIBS", "6"))
# 식 한 줄의 길이. 자르는 것은 고르는 것이 아니다 -- 앞에서부터 자른다.
CUT = int(os.environ.get("MATHDRIFT_SCHEMA_CUT", "120"))

# **판정 칸.** 이 통로는 여기를 절대 안 읽는다. 검사가 이 목록으로 확인한다.
VERDICT_FIELDS = ("재현", "잰것", "판정", "어긋남", "검산m")


def siblings(led: dict, parent_id: str) -> list:
    """이 부모에서 이미 나온 (연산자, 식). **거르지 않는다.**"""
    out = []
    for s in led.get("spaces", []):
        g = s.get("계보") or {}
        if g.get("부모") != parent_id:
            continue
        expr = str(s.get("식") or "").strip()
        if expr:
            out.append((g.get("연산자", ""), expr))
    return out


def census(led: dict) -> dict:
    """원장의 지형. **세는 것뿐이다** -- 어느 쪽이 좋다는 말은 없다."""
    grades = {3: 0, 2: 0, 1: 0, 0: 0}
    dims = []
    for s in led.get("spaces", []):
        # 연산자가 정해 적어 둔 등급을 먼저 본다 -- 글자보다 그쪽이 사슬의 진짜 궤적이다
        grades[s.get("정의역등급") or MO.domain_grade(str(s.get("정의역") or ""))] += 1
        d = MO._int(s.get("치수"))
        if d is not None:
            dims.append(d)
    return {"정의역": grades, "치수": (min(dims), max(dims)) if dims else None,
            "공간수": len(led.get("spaces", []))}


def spread_of(led: dict, parent_id: str) -> float | None:
    """형제끼리 기호가 얼마나 겹치나. **자이지 판정이 아니다.**

    0 에 가까우면 서로 다른 식들이고, 1 에 가까우면 한 틀을 베낀 것이다. 통로를 켜서
    이 수가 오르면 그 통로가 모델을 베끼게 만든 것이다 -- 그때는 통로를 좁힌다.
    형제가 둘 미만이면 견줄 것이 없으니 None 이다."""
    sibs = [e for _, e in siblings(led, parent_id)]
    if len(sibs) < 2:
        return None
    toks = [set(ACT.tokens(e)) for e in sibs]
    pairs, tot = 0, 0.0
    for i in range(len(toks)):
        for j in range(i + 1, len(toks)):
            union = toks[i] | toks[j]
            if not union:
                continue
            tot += len(toks[i] & toks[j]) / len(union)
            pairs += 1
    return round(tot / pairs, 3) if pairs else None


def brief(led: dict, parent_id: str) -> str:
    """프롬프트에 붙일 한 덩이. **아무것도 없으면 빈 줄이다.**

    `dyn.brief` 와 같은 배치다 -- 실을 것이 없으면 한 글자도 안 싣는다. 늘 실으면
    그것 자체가 상수가 되어 묻힌다."""
    if not ON:
        return ""
    sibs = siblings(led, parent_id)
    c = census(led)
    lines = []
    if sibs:
        lines.append("이 부모에서 이미 나온 식:")
        for op, expr in sibs[:SIBS]:
            lines.append(f"  {op:<10} {expr[:CUT]}")
        if len(sibs) > SIBS:
            lines.append(f"  ... 그리고 {len(sibs) - SIBS}개 더")
    g = c["정의역"]
    if c["공간수"] > 1 and any(g.values()):
        lines.append(f"원장 {c['공간수']}개의 정의역: "
                     f"R/C {g[3]} · Z/N/Q {g[2]} · F_q {g[1]} · (없음) {g[0]}")
    if c["치수"] and c["치수"][0] != c["치수"][1]:
        lo, hi = c["치수"]
        lines.append(f"적힌 치수의 폭: {lo} ~ {hi}")
    # 폭이 한 점이면 안 싣는다. "91 ~ 91" 은 지형이 아니라 자리만 차지하는 줄이다 --
    # 씨앗뿐인 원장에서 그것 하나 때문에 덩이가 나갔다(실측).
    if not lines:
        return ""
    # **무엇이 좋은지는 말하지 않는다.** 지형만 말하고 무엇을 할지는 안 시킨다.
    return ("[지금까지의 지형] 겹치라는 말도 피하라는 말도 아니다. 그냥 이렇게 있다.\n"
            + "\n".join(lines))


# ── 되풀이 ────────────────────────────────────────────────────────────
# **LLM 이 24시간 같은 말을 반복하는 것**이 이 파이프라인의 진짜 실패다. 틀린 공간은
# 빈 공간일 뿐이지만(README), 같은 공간을 만 번 적은 원장은 **원장이 아니다.**
#
# 그런데 이것도 기각으로 막지 않는다. 재서 보여 준다 -- 되풀이가 늘면 통로를 넓히거나
# 급발진 몫(`ops.JUMP_SHARE`)을 올릴 일이지, 발산을 죽일 일이 아니다.

def _sig(expr: str) -> frozenset:
    return frozenset(ACT.tokens(expr or ""))


def stale(led: dict, near: float = 0.9) -> dict:
    """앞엣것과 기호가 거의 같은 공간이 몇이나 되나. **호출 0회.**

    `near` 는 자카드 겹침이다. 1.0 이면 토큰 집합이 완전히 같은 것만 센다.
    돌던 런이 정체됐는지 여기서 본다 -- 24시간 뒤에 이 수가 크면 그 시간은 헛돈 것이다."""
    seen: list = []
    same, nearly, pairs = 0, 0, []
    for sp in led.get("spaces", []):
        t = _sig(sp.get("식") or "")
        if not t:
            continue
        hit = None
        for prev_id, prev in seen:
            u = t | prev
            if u and len(t & prev) / len(u) >= near:
                hit = prev_id
                break
        if hit:
            if t == dict(seen).get(hit):
                same += 1
            else:
                nearly += 1
            pairs.append((sp["id"], hit))
        seen.append((sp["id"], t))
    n = len(seen)
    return {"잰공간": n, "똑같음": same, "거의같음": nearly,
            "몫": round((same + nearly) / n, 3) if n else 0.0,
            "짝": pairs[:12]}


# 앞머리를 몇 자까지 견주나. 로그가 40자쯤에서 잘려도 보이던 그 길이다.
HEAD = int(os.environ.get("MATHDRIFT_HEAD", "36"))


def by_depth(led: dict) -> list:
    """깊이별로 **부모를 얼마나 그대로 물려받았나.** 호출 0회.

    실측 2026-09-08, VM 51개 런(스키마 통로 이전 코드):

        깊이 1  부모몫 0.270   <- 여기가 건강하다. 매장 -> phi 준동형, 점근화 -> omega
        깊이 2  부모몫 0.770
        깊이 3  부모몫 0.887   <- 서른 걸음 중 아홉이 부모 식과 앞 36자가 글자 그대로 같다

    **오르는 것이 신호다.** 깊이가 쌓일수록 자식이 부모를 더 베낀다면, 연산자가 이름만
    걸리고 식에는 아무 일도 안 한 것이다(S8 의 자식 넷이 국소화·상대화·이산화·쌍대인데
    앞 36자가 다 같았다). 임계점은 깊이 8 이 아니라 **깊이 3 에 이미 와 있었다.**

    그래서 24시간을 어디까지 파는 것이 뜻이 있는지는 이 표가 정한다 -- 부모몫이 1 에
    붙는 깊이 아래로는 더 파도 같은 식이 늘 뿐이다.

    **이것도 판정이 아니다.** 아무것도 안 거른다.
    """
    rows = {}
    for sp in led.get("spaces", []):
        d = sp.get("깊이")
        if not isinstance(d, int) or d == 0:
            continue
        got = (sp.get("잰것") or {}).get("몫")
        par = SP.get(led, (sp.get("계보") or {}).get("부모") or "")
        pe = str((par or {}).get("식") or "")
        e = str(sp.get("식") or "")
        r = rows.setdefault(d, {"몫": [], "그대로": 0, "수": 0})
        r["수"] += 1
        if isinstance(got, (int, float)):
            r["몫"].append(float(got))
        # **앞머리가 글자 그대로 같은 것.** 낱말 겹침과 달리 이건 못 우긴다.
        # 둘 다 36자가 있어야 "앞 36자가 같다" 가 뜻이 있다 -- 짧은 쪽이 36자가 안 되면
        # 비교가 늘 거짓이 되어(자른 길이가 달라서) 세지 못한다.
        if len(e) >= HEAD and len(pe) >= HEAD and e[:HEAD] == pe[:HEAD]:
            r["그대로"] += 1
    out = []
    for d in sorted(rows):
        r = rows[d]
        out.append({"깊이": d, "수": r["수"], "그대로": r["그대로"],
                    "부모몫": round(sum(r["몫"]) / len(r["몫"]), 3) if r["몫"] else None})
    return out


def show(led: dict, parent_id: str = "") -> int:
    ids = [parent_id] if parent_id else [s["id"] for s in led.get("spaces", [])]
    if not ids:
        print("원장이 비어 있다")
        return 0
    print(f"통로: {'열림' if ON else '닫힘 (MATHDRIFT_SCHEMA=0)'}"
          f" · 형제 {SIBS}개까지 · 식 {CUT}자까지\n")
    for sid in ids:
        if SP.get(led, sid) is None:
            print(f"{sid} 은 원장에 없다")
            return 1
        b = brief(led, sid)
        sp = spread_of(led, sid)
        head = f"=== {sid} 를 부모로 삼을 때"
        if sp is not None:
            head += f"  (형제 겹침 {sp})"
        print(head)
        print(b if b else "  (실을 것이 없다 -- 한 글자도 안 싣는다)")
        print()
    if not parent_id:
        vals = [v for v in (spread_of(led, s["id"]) for s in led["spaces"]) if v is not None]
        if vals:
            vals.sort()
            print(f"형제 겹침 분포 -- 최소 {vals[0]} / 중앙 {vals[len(vals) // 2]}"
                  f" / 최대 {vals[-1]}   ({len(vals)}자리)")
            print("**이 수가 통로를 켠 뒤 오르면 통로가 베끼게 만든 것이다.** 자이지 판정이 아니다.")
        st = stale(led)
        print(f"\n되풀이 -- 앞엣것과 똑같음 {st['똑같음']} · 거의 같음 {st['거의같음']}"
              f" / {st['잰공간']}개 (몫 {st['몫']})")
        for a, b in st["짝"][:6]:
            print(f"    {a} 는 {b} 와 거의 같다")
        print("**24시간 뒤에 이 몫이 크면 그 시간은 헛돈 것이다.** 기각하지 않는다 -- 재서 보여 준다.")
        rows = by_depth(led)
        if rows:
            print(f"\n{'깊이':>4} {'공간':>5} {'부모몫':>7} {'앞머리 그대로':>12}")
            for r in rows:
                sh = f"{r['부모몫']:.3f}" if r["부모몫"] is not None else "-"
                print(f"{r['깊이']:>4} {r['수']:>5} {sh:>7} {str(r['그대로']) + '개':>12}")
            print("**부모몫이 깊이를 따라 오르면 연산자가 이름만 걸린 것이다.**")
            print("실측 2026-09-08 (통로 이전, 51개): 깊이 1 에 0.270 · 2 에 0.770 · 3 에 0.887 --")
            print("깊이 3 에서 서른 걸음 중 아홉이 부모 식과 앞 36자가 글자 그대로 같았다.")
    return 0
