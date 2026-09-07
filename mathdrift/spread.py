"""**발산** -- 공간을 최대한 많이 낳는다. 이 단계에서 죽이는 것은 없다.

    python3 mathdrift/spread.py --check              # 지금 무엇을 쓸 수 있나 (호출 0회)
    python3 mathdrift/spread.py --n 300              # 300개
    python3 mathdrift/spread.py --n 5 --dry          # 호출 없이 프롬프트만 본다
    python3 mathdrift/spread.py --show               # 원장을 본다
    python3 mathdrift/spread.py --lineage S17        # 씨앗까지의 사슬

## 왜 안 죽이나

공간은 틀릴 수 없다 -- 쓸모없을 뿐이다. 틀린 정리는 원장을 오염시키지만 빈 공간은
탐색해봐야 아무것도 안 나올 뿐이다. 그래서 발산에는 게이트를 안 건다. 4축 심판은
**다음 커밋의 별도 배치**이고, 여기서 흉내내면 발산이 죽는다.

## 대신 스키마는 강제한다

만 개를 자유 산문으로 뽑아 두면 검증할 때 만 번을 다시 파싱해야 한다 -- 생성 비용만큼이
다시 든다. `novel/flow.py` 와 같은 배치다: **모델은 자유롭게 쓰고, 받는 것은 칸이다.**

## 쿼터 -- 묶어서 부른다

무료 티어에서 병목은 일일 한도가 아니라 **분당 한도(RPM)** 다. 구글 문서 기준으로 한도는
**프로젝트** 단위이고 RPM 은 모델별로 따로 걸린다(flash 10/분 남짓). 공간 하나에 호출
하나면 300개에 30분 이상이고, 그 시간의 대부분은 쿨다운을 기다리는 것이다.

그래서 **한 번에 여러 개를 받는다.** 부모 하나를 보여 주고 연산자 K 개를 함께 걸어
K 개를 받는다. 호출이 1/K 로 준다. 공짜로 얻는 것이 하나 더 있다 -- 모델이 K 개를 **한
자리에서 보므로** 서로 다르게 쓴다. 따로 부르면 비슷한 것이 K 벌 나온다.

풀은 `orchestrator/llm_pool.py` 를 그대로 쓴다. 429 를 맞으면 그 후보를 소진 표시하고
다음으로 넘어가고, 성공한 후보는 pin 되고, RPM 은 60초 쿨다운으로 따로 처리된다 --
이 저장소가 이미 갖고 있는 것을 새로 짜지 않는다.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mathdrift import measure as ME                                   # noqa: E402
from mathdrift import ops as OPS                                      # noqa: E402
from mathdrift import space as SP                                     # noqa: E402

# **한 번에 받는 공간 수.** 크게 잡을수록 호출이 줄지만, 하나가 깨지면 그 묶음이 통째로
# 흔들리고 출력이 길어져 뒤엣것이 성의 없어진다. 5 는 출력 1,500토큰 남짓이라
# llm_pool 의 기본 상한(8,192)에 한참 못 미친다.
BATCH = 5


def prompt(parent: dict, picks: list[tuple[str, str, int]]) -> str:
    """**이름이 아니라 식이 표류한다. 그리고 여기서는 아무것도 안 막는다.**

    두 번 데었다.

    하나. 이름과 산문으로 주고받았더니 모델이 부모 이름에 연산자 어휘를 덧붙이는 데로
    수렴했다(실측 85개). 프롬프트도 자도 전부 낱말이었으니 표류가 어휘 공간에서 일어난
    것이다. 그래서 오가는 것을 **식**으로 바꿨다.

    둘. 그 다음에는 심판을 프롬프트에 실었다 -- 해독기와 부호화기를 내라, 기계가 이렇게
    네 단계로 검사한다. 20개 중 20개가 시금석점을 안 냈고, 무엇보다 **발산이 사양서가
    됐다.** `novel/` 에서 이미 겪은 그것이다: *관문을 나중에 붙였다가 원고가 관문을
    통과하려고 균질해졌다.*

    그래서 심판 얘기를 여기서 **전부 뺐다.** 코드 칸은 선택이고, 없다고 벌점이 없다.
    검증은 `recall.py` 가 나중에 **따로** 한다 -- 생성기는 그것을 몰라야 한다.
    """
    body = "\n".join(f"    {f}: {parent.get(f) if parent.get(f) not in ('', None) else '(비어 있음)'}"
                     for f in ("식", "점", "정의역"))
    lines = []
    for op, what, dist in picks:
        far = "  ← 먼 이주여도 좋다" if dist >= 2 else ""
        lines.append(f"  · {op} : {what}{far}")
    ops_block = "\n".join(lines)
    return f"""너는 행렬곱 복잡도 문제의 **식**을 넓히는 중이다. 해를 찾는 것이 아니라
**해를 찾을 수 있는 식**을 적는 것이 일이다.

지금 있는 식(부모):
{body}

이 **식**에 연산자를 하나씩 건다. {len(picks)}개다.

{ops_block}

연산자마다 새 식 하나씩, **JSON 배열 하나로만** 답해라. 원소는 {len(picks)}개다.

  연산자 : 위 목록의 이름 그대로 (짝을 맞추려는 칸이다)
  식     : **오로지 수학적 기호만.** 한국어를 한 글자도 쓰지 마라.
           부모 식을 놓고 이 연산자가 그것을 **기호로** 어떻게 바꾸는지 쓴다 --
           lim 이 붙거나, 체가 바뀌거나, 첨자에 조건이 붙거나, = 이 <= 가 되거나,
           합의 범위가 달라지거나, 새 변수가 들어오거나.
           설명하고 싶은 것은 전부 `왜` 칸에 적는다. 여기는 식만 있는 칸이다
  점     : 해가 무엇인지 **기호로** (예: (U,V,W,lam) in F^{{n^2 x m}} x ... x F^m)
  정의역 : F = R · F = F_2 · F = {{-1,0,1}} · ... 처럼 **기호로**
  왜     : 왜 이것이 그럴듯한가 (**여기만 한국어로 쓴다.** 사람이 읽는 칸이고
           다음 세대에게는 전달되지 않는다)

선택 칸. **적을 수 있으면 적고 아니면 비워라. 없다고 벌점 없다.**

  치수   : 점이 수 몇 개인가
  해독   : `def decode(p):` 점 -> (U, V, W, lambda). U,V,W 는 4x7, lambda 는 길이 7
  부호화 : `def encode(U, V, W, lam):` 그 역함수
           (표준 라이브러리만. Fraction 은 이미 있다. 임포트하지 마라)

규칙 넷.

  · **엄밀할 필요 없다.** 정리도 증명도 아니다. **그럴듯한 식이면 된다**
  · **모르는 칸은 비워라.** 지어내지 마라 -- 빈 칸은 벌점이 아니다
  · **부모 식을 부정하지 마라.** 부모의 해가 새 식 안에서도 해로 남아야 한다
  · **{len(picks)}개를 서로 다르게 써라.** 연산자가 다르므로 식도 달라야 한다
  · **`식`·`점`·`정의역` 에 한국어가 있으면 그건 식이 아니라 설명이다.**
    "같은 식을 F_2 위에서" (X)
    `sum_r lam_r U[(i,k),r] V[(k',j),r] W[(i',j'),r] = d(k,k') d(j,j') d(i,i')  over F_2` (O)
  · **부모에게 이름이 없다.** 붙일 이름도 없다 -- 식만 오간다

JSON 배열:"""


# JSON 문자열 안에서 `\` 뒤에 올 수 있는 것은 이것뿐이다. LaTeX 는 그 규약을 모른다 --
# `\lambda` 는 JSON 파서에게 "잘못된 이스케이프" 다. 식을 기호로 받기 시작하자 이것이
# 바로 물렸다(실측 2026-09-07: 다섯 묶음 중 하나를 통째로 잃었다 -- 20%).
#
# 모델에게 "역슬래시를 두 번 써라" 라고 시키지 않는다. 그건 프롬프트를 사양서로 만드는
# 길이고 이미 한 번 데었다. **읽는 쪽에서 고친다.**
_JSON_ESC = set('"\\/bfnrtu')


def _fix_escapes(t: str) -> str:
    r"""JSON 이 모르는 `\x` 를 `\\x` 로 바꾼다.

    **글자가 뒤따르면 LaTeX 명령으로 본다.** `\t` `\b` `\f` `\n` `\r` 은 JSON 이스케이프
    이면서 동시에 LaTeX 명령의 머리다 -- `\to` `\beta` `\frac` `\nabla` `\rho`. 그것을
    구별 안 하면 `\to` 가 탭이 되고 `\big` 이 백스페이스가 된다(실측). LaTeX 명령은
    `\` + 글자이므로 그것으로 가른다.

    `\uXXXX` 는 뒤에 16진수 넷이 올 때만 유니코드로 본다 (`\upsilon` 은 LaTeX).
    `\"` `\\` `\/` 는 글자가 아니라 헷갈릴 일이 없다.

    **여기에는 진짜 애매함이 하나 남는다** -- 문자열 안의 진짜 줄바꿈 뒤에 글자가 오면
    (`"...\nabc"`) LaTeX 로 오해한다. 이 함수는 **평범한 파싱이 실패한 뒤에만** 불리므로
    피해 범위가 거기까지다. 이 도메인에서는 `\nabla` 쪽이 압도적으로 흔하다.
    """
    out, i, n = [], 0, len(t)
    while i < n:
        c = t[i]
        if c != "\\" or i + 1 >= n:
            out.append(c)
            i += 1
            continue
        nxt = t[i + 1]
        keep = nxt in _JSON_ESC
        if keep and nxt.isalpha():
            if nxt == "u":
                hexpart = t[i + 2:i + 6]
                keep = len(hexpart) == 4 and all(ch in "0123456789abcdefABCDEF"
                                                 for ch in hexpart)
            else:
                # 글자가 뒤따르면 LaTeX 명령이다 (\to \beta \frac \nabla \rho ...)
                keep = not (i + 2 < n and t[i + 2].isalpha())
        if keep:
            out.append(c)
            out.append(nxt)
            i += 2
        else:
            out.append("\\\\")
            i += 1
    return "".join(out)


_INNER = re.compile(r"\{[^{}]*\}", re.S)


def _balanced(t: str):
    """중괄호를 세어 **덩어리를 통째로** 떠낸다.

    처음에는 정규식 `\\{[^{{}}]*\\}` 로 떴는데, 그것은 **안쪽 중괄호가 없는 것만** 문다 --
    `{"해독": {"U": ...}}` 같이 겹친 것이 오면 바깥이 아니라 안쪽 `{"U": ...}` 를 집어
    온다. recall.py 의 답이 정확히 그 꼴이라, 멀쩡한 답을 "가능 칸이 없다" 며 거절로
    셌다(실측). 세어서 뜨면 겹쳐도 바깥이 잡힌다.
    """
    out, depth, start, instr, esc = [], 0, -1, False, False
    for i, ch in enumerate(t):
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
            continue
        if ch == '"':
            instr = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                out.append(t[start:i + 1])
                start = -1
            elif depth < 0:
                depth = 0
    return out


def objects(raw) -> list[dict]:
    """**하나가 깨져도 나머지는 건진다.** 통째로 못 읽으면 덩어리를 낱낱이 읽는다 --
    묶어 부르는 것의 값이 한 글자 때문에 다섯을 잃는 데서 사라지면 안 된다."""
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if not isinstance(raw, str):
        return []
    t = raw.strip()
    if "```" in t:
        parts = t.split("```")
        if len(parts) > 1:
            t = parts[1]
            t = t[4:] if t.lstrip().startswith("json") else t
    # **통째로 먼저 읽는다.** 겹친 중괄호가 있으면 이 길로만 온전히 온다.
    # 실패하면 LaTeX 역슬래시를 고쳐 한 번 더 -- 식을 기호로 받으면 이것이 바로 물린다.
    for cand in (t, _fix_escapes(t)):
        try:
            d = json.loads(cand)
        except ValueError:
            continue
        if isinstance(d, dict):
            return [d]
        if isinstance(d, list):
            return [x for x in d if isinstance(x, dict)]
    t = _fix_escapes(t)
    i, j = t.find("["), t.rfind("]")
    if 0 <= i < j:
        try:
            d = json.loads(t[i:j + 1])
            if isinstance(d, list):
                return [x for x in d if isinstance(x, dict)]
        except ValueError:
            pass
    # **두 번 훑는다.** 세어 뜨는 것은 겹친 중괄호에 강하지만, 바깥이 안 닫힌 채
    # 깨져 오면 그 안의 멀쩡한 것까지 통째로 삼킨다(실측: 다섯 중 둘이 하나로 줄었다).
    # 그래서 세어 뜬 것을 먼저 건지고, **남은 자리**에 안쪽 덩어리 훑기를 한 번 더 건다.
    out, rest = [], t
    for chunk in _balanced(t):
        try:
            d = json.loads(chunk)
        except ValueError:
            continue
        if isinstance(d, dict):
            out.append(d)
            rest = rest.replace(chunk, " ", 1)
    for m in _INNER.finditer(rest):
        try:
            d = json.loads(m.group(0))
        except ValueError:
            continue
        if isinstance(d, dict):
            out.append(d)
    return out


def _pick_ops(led: dict, seed: str, n: int, k: int) -> list[tuple[str, str, int]]:
    """연산자 k 개. 겹치지 않게 뽑고, 덜 써 본 것으로 채운다."""
    got, i = [], 0
    while len(got) < k and i < k * 8:
        op, what, dist = OPS.draw(seed, n * k + i)
        if op not in {g[0] for g in got}:
            got.append((op, what, dist))
        i += 1
    for op in OPS.rarest(led["ops_used"]):
        if len(got) >= k:
            break
        if op not in {g[0] for g in got}:
            what, dist = OPS.BY_NAME[op]
            got.append((op, what, dist))
    return got[:k]


def step(led: dict, llm, seed: str, n: int, k: int = BATCH, log=print) -> list[dict]:
    """호출 한 번 = 공간 여러 개. **부모는 원장에서 고른다** -- 계보가 끊길 수가 없다."""
    if not led["spaces"]:
        log("[발산] 원장이 비어 있다 -- 씨앗 공간이 있어야 시작한다")
        return []
    picks = _pick_ops(led, seed, n, k)
    parent = led["spaces"][n % len(led["spaces"])]

    try:
        raw = llm(prompt(parent, picks))
    except Exception as e:                                    # noqa: BLE001
        log(f"[발산] 호출 실패({type(e).__name__}: {str(e)[:70]}) -- 건너뛴다")
        return []

    recs = objects(raw)
    if not recs:
        log("[발산] JSON 을 못 읽었다 -- 이 묶음을 건너뛴다")
        return []

    # **연산자 이름으로 짝짓는다.** 순서만 믿으면 모델이 하나를 빼먹었을 때 이후가 전부
    # 어긋난 부모-연산자로 원장에 박힌다. 이름이 안 맞는 것만 순서로 채운다.
    by_name = {op: (what, dist) for op, what, dist in picks}
    left = [p[0] for p in picks]
    out = []
    for rec in recs:
        want = (rec.get("연산자") or "").strip()
        if want not in by_name or want not in left:
            want = left[0] if left else None
        if want is None:
            break
        left.remove(want)
        _, dist = by_name[want]
        made = SP.add(led, rec, parent=parent["id"], op=want, dist=dist)
        made["잰것"] = ME.measure(made, parent)
        out.append(made)
        log(f"[발산] {made['id']} <- {parent['id']} / {want} : "
            f"{str(made.get('식') or '')[:46]} | {ME.note(made['잰것'])}")
    if len(out) < len(picks):
        log(f"[발산] {len(picks)}개 중 {len(out)}개만 왔다")
    return out


# 옛 이름. 한 번에 하나만 받던 시절의 서명 -- 배선 검사가 이것으로 짜여 있다.
def one(led: dict, llm, seed: str, n: int, log=print) -> dict | None:
    got = step(led, llm, seed, n, k=1, log=log)
    return got[0] if got else None


# ── 풀 ────────────────────────────────────────────────────────────────
def _pool():
    """`orchestrator/llm_pool.py` 를 그대로 쓴다. **여기서 임포트한다** -- dry 는
    무거운 것도 키도 안 끌고 온다."""
    from orchestrator import llm_pool
    pool = llm_pool.build_pool()
    if not pool:
        raise RuntimeError("후보가 하나도 없다 (GEMINI_API_KEY 확인)")
    return llm_pool, pool


def _live():
    llm_pool, pool = _pool()

    def call(p: str) -> str:
        text, label = llm_pool.call(pool, p, pool_id="mathdrift", verbose=False)
        return text

    return call


def check() -> int:
    """**호출을 0회 하고** 지금 무엇을 쓸 수 있는지 본다. 300개를 걸기 전에 이것부터."""
    try:
        llm_pool, pool = _pool()
    except Exception as e:                                    # noqa: BLE001
        print(f"풀을 못 세웠다: {e}")
        return 1
    import quota_tracker as q

    keys, live = {}, 0
    for label, _ in pool:
        kid = label.split(":", 1)[0]
        keys.setdefault(kid, []).append(label)
    print(f"후보 {len(pool)}개 / 키 {len(keys)}개")
    print("  (한도는 **프로젝트** 단위다. 같은 프로젝트에서 키만 늘리면 한도는 그대로다)")
    for kid, labels in keys.items():
        alive = [lb for lb in labels
                 if not q.is_dead(lb) and q.remaining(lb) > 0 and not q.is_rpm_cooling(lb)]
        live += len(alive)
        rem = sum(max(0, q.remaining(lb)) for lb in alive)
        print(f"  {kid:<14} 후보 {len(labels):>2}개 · 지금 쓸 수 있는 것 {len(alive):>2}개 "
              f"· 남은 것으로 추정 {rem:,}회")
    if not live:
        print("\n지금 쓸 수 있는 후보가 없다 -- 돌려도 429 만 쌓인다.")
        return 3
    print(f"\n묶음 {BATCH}개씩이면 공간 300개에 호출 {-(-300 // BATCH)}회.")
    print("RPM 이 병목이므로 남은 일일 잔량보다 이 호출 수가 중요하다.")
    return 0


def remeasure(led: dict, path=None) -> int:
    """**호출 0회.** 원장에 이미 있는 것을 새 자로 다시 잰다.

    자를 고치면 지금까지 뽑은 것을 다시 뽑아야 하는 줄 알았는데, 잰 것은 원장에 다 있으므로
    다시 계산하면 된다. 자가 틀린 채로 300개를 뽑으면 어느 것이 쓸 만한지 못 고른다 --
    자를 먼저 맞추고 그 다음에 크게 돈다.

    바닥값(KEEP_MIN · KEEP_SHARE)을 **실측으로 정하라고** 분포를 같이 찍는다.
    """
    rows, was, now = [], 0, 0
    for rec in led["spaces"]:
        old = rec.get("잰것") or {}
        if old.get("씨앗"):
            continue
        parent = SP.get(led, (rec.get("계보") or {}).get("부모"))
        new = ME.measure(rec, parent)
        rec["잰것"] = new
        was += 1 if old.get("확산") else 0
        now += 1 if new["확산"] else 0
        rows.append((rec["id"], rec.get("계보", {}).get("연산자", ""), new,
                     str(rec.get("식") or "")))
    SP.save(led, path)

    print(f"다시 잰 공간 {len(rows)}개 -- 겹침 많음 {was}개 → {now}개\n")
    print(f"{'id':<5} {'연산자':<10} {'가져온말':>6} {'부모몫':>7}  식")
    for sid, op, m, expr in sorted(rows, key=lambda r: -r[2]["몫"]):
        print(f"{sid:<5} {op:<10} {m['물려받음']:>6} {m['몫']:>7.3f}  {expr[:60]}")
    print("\n**이 수는 판정이 아니다.** 낱말 겹침으로 인과를 재던 자는 두 번 뒤집혔다 --"
          " 부모 말을 그대로 달고\n수식어만 바꾼 것이 최고점(0.933)을 받고, 진짜 이주"
          "(ε-근사 · 그로텐디크)가 0 으로 깔렸다.")

    vals = sorted(r[2]["몫"] for r in rows)
    if vals:
        def q(f):
            return vals[min(len(vals) - 1, int(len(vals) * f))]
        print(f"\n부모몫 분포 -- 최소 {vals[0]:.3f} / 4분위 {q(.25):.3f} / 중앙 {q(.5):.3f}"
              f" / 3분위 {q(.75):.3f} / 최대 {vals[-1]:.3f}")
        print(f"지금 바닥값: 물려받음 >= {ME.KEEP_MIN} · 부모몫 >= {ME.KEEP_SHARE}")
        print("바닥값은 MATHDRIFT_KEEP_MIN / MATHDRIFT_KEEP_SHARE 로 바꿔 다시 재 본다.")
    return 0


# **`--known` 을 뗐다.** 알려진 갈아타기 넷을 찾아 주던 것인데, 찾는 방식이 한국어
# 낱말 grep 이었다("군대수", "표수", "근사"...). 식으로 표류시키기로 해 놓고 판정도 찾기도
# 낱말로 하고 있었으면 같은 잘못을 세 번째 되풀이하는 것이다. 식을 기호로 견주는 법이
# 생기기 전까지는 아무것도 안 센다.

# **식을 기호로 가른다.** 낱말이 아니라 LaTeX 토큰이다 -- `\lim` `\inf` `_` `{` `N` ...
_TEX = re.compile(r"\\[a-zA-Z]+|\\.|[A-Za-z]+|\d+|\S")


def tokens(expr: str) -> list[str]:
    return _TEX.findall(expr or "")


def diff(led: dict, sid: str) -> int:
    """연산자가 식에 **무엇을 했나.** 호출 0회, 아무것도 안 거른다.

    실측 2026-09-07(20개): 식을 기호로 받기 시작하자 자식이 부모 식을 거의 그대로
    물려받고 한 자리만 바꾸는 꼴이 됐다 -- `\inf` -> `\sup`(쌍대), `H` -> `\hat{H}`(완비화),
    앞에 `S^{-1}`(국소화), `=` -> `\equiv`(이산화). **그것이 보존적 확장이 맞는 모습**이라
    겹침이 높은 것이 이번에는 좋은 신호다. 다만 화면이 70자에서 잘려 무엇이 바뀌었는지
    볼 수가 없었다. 이 명령이 그 자리다.
    """
    rec = SP.get(led, sid)
    if rec is None:
        print(f"{sid} 가 원장에 없다")
        return 1
    g = rec.get("계보") or {}
    par = SP.get(led, g.get("부모"))
    if par is None:
        print(f"{sid} 는 씨앗이다 -- 견줄 부모가 없다")
        return 0

    a, b = tokens(par.get("식")), tokens(rec.get("식"))
    print(f"{sid}  <- {par['id']} / {g.get('연산자')} (거리 {g.get('거리')})\n")
    print(f"  부모: {par.get('식')}")
    print(f"  자식: {rec.get('식')}\n")

    kept = 0
    rows = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b).get_opcodes():
        if tag == "equal":
            kept += i2 - i1
            continue
        if tag in ("delete", "replace"):
            rows.append(("-", " ".join(a[i1:i2])))
        if tag in ("insert", "replace"):
            rows.append(("+", " ".join(b[j1:j2])))
    if not rows:
        print("  **바뀐 것이 없다.** 식이 글자 그대로 같다 -- 연산자가 아무 일도 안 했다")
    else:
        print("  바뀐 것:")
        for mark, txt in rows:
            print(f"    {mark} {txt[:100]}")
    big = max(len(a), len(b)) or 1
    print(f"\n  그대로 둔 토큰 {kept}/{big}  (부모 {len(a)} 토큰, 자식 {len(b)} 토큰)")
    print("\n  **판정이 아니다.** 연산자가 식에 무엇을 했는지 보여 줄 뿐이다.")
    return 0


def card(led: dict, sid: str) -> int:
    """공간 하나를 칸째로 펼친다. **이름만 보고 판정하지 않으려고 있는 것이다.**

    실측 2026-09-07(60개): 이름만 보면 부모 이름에 연산자 어휘를 덧붙인 것처럼 보이는
    무리가 있었다. 그것이 정말 작명인지 이주인지는 `점`·`표기`·`되사상` 을 봐야 안다.
    """
    rec = SP.get(led, sid)
    if rec is None:
        print(f"{sid} 가 원장에 없다")
        return 1
    g = rec.get("계보") or {}
    par = SP.get(led, g.get("부모"))
    print(f"{rec['id']}  <- {g.get('부모')} / {g.get('연산자')} (거리 {g.get('거리')})"
          f"  [{rec.get('등급')}]")
    print(f"계보: {' -> '.join(SP.lineage(led, sid))}")
    print(f"잰것: {ME.note(rec.get('잰것') or {})}\n")
    for f in SP.FIELDS:
        v = rec.get(f)
        print(f"  {f:<6}: {v if v else '(비어 있음)'}")
    if par:
        print(f"\n--- 부모 {par['id']} ---")
        for f in ("식", "점", "정의역"):
            print(f"  {f:<6}: {par.get(f) or '(비어 있음)'}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20, help="이번에 낳을 공간 수(대략)")
    ap.add_argument("--batch", type=int, default=BATCH, help="호출 하나가 낳는 공간 수")
    ap.add_argument("--dry", action="store_true", help="호출 없이 프롬프트만 본다")
    ap.add_argument("--check", action="store_true", help="쓸 수 있는 후보를 본다(호출 0회)")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--remeasure", action="store_true",
                    help="원장을 새 자로 다시 잰다 (호출 0회)")
    ap.add_argument("--lineage", default="")
    ap.add_argument("--card", default="", help="공간 하나를 칸째로 (예: --card S34)")
    ap.add_argument("--diff", default="",
                    help="연산자가 식에 무엇을 했나 (예: --diff S10). 호출 0회")
    ap.add_argument("--path", default="")
    a = ap.parse_args(argv)

    if a.check:
        return check()

    led = SP.load(a.path or None)

    if a.diff:
        return diff(led, a.diff)

    if a.card:
        return card(led, a.card)

    if a.remeasure:
        return remeasure(led, a.path or None)

    if a.show:
        print(f"공간 {len(led['spaces'])}개")
        print(SP.brief(led))
        s = ME.spread(led)
        print(f"\n낱말 겹침 {s['확산']}/{s['잰공간']} (몫 {s['몫']:.2f})"
              "  ← 눈금이지 판정이 아니다")
        okn = sum(1 for x in led["spaces"] if x.get("등급") == "검증가능")
        print(f"검증가능 {okn}개 (코드 칸을 채운 것 -- 없다고 벌점은 없다)")
        print("연산자 씀: " + ", ".join(f"{k} {v}" for k, v in
                                     sorted(led["ops_used"].items(), key=lambda x: -x[1])))
        return 0

    if a.lineage:
        for sid in SP.lineage(led, a.lineage):
            r = SP.get(led, sid) or {}
            g = r.get("계보") or {}
            print(f"  {sid:<5} {g.get('연산자','씨앗'):<10} {r.get('이름','')}")
        return 0

    rounds = max(1, -(-a.n // max(1, a.batch)))

    if a.dry:
        for i in range(min(rounds, 3)):
            picks = _pick_ops(led, "dry", i, a.batch)
            print("=" * 70)
            print(prompt(led["spaces"][i % len(led["spaces"])], picks))
        return 0

    try:
        llm = _live()
    except Exception as e:                                    # noqa: BLE001
        print(f"못 돌린다: {e}")
        return 1

    t0, made = time.time(), 0
    for i in range(rounds):
        made += len(step(led, llm, seed=str(len(led["spaces"])), n=i, k=a.batch))
        SP.save(led, a.path or None)
        print(f"[발산] {i + 1}/{rounds}회 · 공간 {made}개 · {time.time() - t0:.0f}초")
    print(f"\n호출 {rounds}회로 {made}개를 원장에 올렸다. 공간 {len(led['spaces'])}개.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
