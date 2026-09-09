r"""**문제 원장** -- 식이 아니라 *문제*를 적는다. 그리고 판정기 없이는 못 적는다.

`mathdrift` 는 식을 적었다. 51개를 재 보니 41개가 **뜻이 안 정해진 기호**를 갖고
있었다 -- `\Phi(U)\Phi(V)\Phi(W) = \Phi(\delta)` 에서 Phi 가 무엇인지 아무 데도
없었다. 그런 것은 공간이 아니라 공간의 **이름**이다. 답을 아무도 검산할 수 없다.

그래서 여기서는 문법을 바꾼다.

    문제 하나 = (물음, 표본, 판정) -- 셋이 다 **도는 코드**여야 한다

`space.add()` 가 부모 없는 공간을 검사해서 거절하는 것이 아니라 **아예 못 받게**
되어 있는 것과 같은 수다. 판정기를 못 적으면 문제가 아니다. 이 규칙 하나가 어제의
41개를 입구에서 막는다.

## 칸

    물음   사람이 읽는 한 줄. **자식에게 안 넘어간다** (mathdrift 의 `왜` 와 같다)
    표본   def sample(rng) -> 후보      무작위 후보 하나
    판정   def judge(x) -> bool         그 후보가 답인가
    옮김   def embed(x) -> 후보         **부모의 후보를 이 문제의 후보로.** 씨앗은 없다

`옮김` 이 요점이다. mathdrift 에서 Phi 가 자유 기호로 남았던 자리가 여기서는
**코드**다. 부모의 해가 새 문제 안에서도 해로 남는지를 그것으로 실제로 확인한다.

## 도약을 기계가 판정한다

    보존   부모의 답 x 에 대해 judge(embed(x)) 가 참이다      -- 옛 해가 살아남는다
    확장   이 문제의 답 y 를 **부모의 판정기가 읽지도 못한다** -- 새 점이 생겼다

둘 다면 도약이다. 하나만이면 아니다. `reach.py` 가 그것을 돌린다.

## 판정기는 이 프로세스에서 안 돈다

`exec` 는 임의 코드를 실행한다. `_judge.py` 자식에서 돈다 -- `mathgen/_worker.py`
와 `mathdrift/_child.py` 가 같은 이유로 그렇게 되어 있다. **샌드박스가 아니라
프로세스 분리다.** 부모의 임포트와 원장에 못 닿을 뿐, 같은 기계에서 실제로 돈다.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = HERE / "seed.json"
PATH = Path(os.environ.get("SEEK_LEDGER", HERE / "ledger.json"))

# 세 칸이 다 코드다. 하나라도 비면 문제가 아니다.
CODE = ("표본", "판정")
FIELDS = ("물음", "표본", "판정", "옮김")


class NotAProblem(ValueError):
    """판정기가 없거나 안 도는 것을 원장에 넣으려 했다."""


def blank() -> dict:
    return {"seq": 0, "problems": []}


def get(led: dict, pid: str) -> dict | None:
    ps = led.get("problems") or []
    if isinstance(pid, str) and pid[:1] == "P" and pid[1:].isdigit():
        k = int(pid[1:]) - 1
        if 0 <= k < len(ps) and ps[k].get("id") == pid:
            return ps[k]
    for p in ps:
        if p.get("id") == pid:
            return p
    return None


def add(led: dict, rec: dict, parent: str, op: str, check=True) -> dict:
    """문제 하나를 원장에 올린다. **판정기가 실제로 돌지 않으면 안 받는다.**

    비었는지만 보는 것이 아니라 **돌려 본다.** 비었는지만 보면 `def judge(x): pass`
    가 통과하고, 그건 판정기가 아니라 판정기의 이름이다 -- 어제 41개가 걸린 그 자리를
    그대로 반복하는 것이다.
    """
    if parent != "-" and get(led, parent) is None:
        raise ValueError(f"부모 {parent} 가 원장에 없다 -- 계보가 끊긴 문제는 안 받는다")
    for f in CODE:
        if not str(rec.get(f) or "").strip():
            raise NotAProblem(f"`{f}` 가 비었다 -- 판정기 없는 것은 문제가 아니다")
    if parent != "-" and not str(rec.get("옮김") or "").strip():
        raise NotAProblem("`옮김` 이 비었다 -- 부모의 답이 여기서도 답인지 볼 수가 없다")
    if check:
        from seek import judge as J
        ok, why, 잰것 = J.runs(rec)
        if not ok:
            raise NotAProblem(f"판정기가 안 돈다: {why}")
        # **도는 것만으로는 모자란다.** `def judge(x): return True` 는 멀쩡히 돌고
        # 참/거짓도 제대로 돌려주는데 아무것도 안 거른다 -- 뽑은 것이 다 답이면
        # 찾을 것이 없고, 그건 문제가 아니라 문제의 모양이다.
        #
        # 실측 2026-09-09: 이 줄이 없을 때 낳은 것이 21개 중 21개 다 받아들여졌다.
        # 100% 는 프롬프트가 좋다는 뜻일 수도 있지만 **거르는 데가 없다는 뜻일 수도**
        # 있고, 그 둘을 구분할 방법이 그때는 없었다.
        #
        # **반대쪽(하나도 안 받는다)은 안 막는다.** P1 이 그렇다 -- 무작위 정렬망
        # 22,991개를 봐야 하나가 걸린다. 어려운 것과 틀린 것을 여기서 가를 수 없으므로
        # 받아 두고 `seek/audit.py` 가 눈에 보이게 적는다.
        if 잰것 and 잰것["본것"] and 잰것["받음"] == 잰것["본것"]:
            raise NotAProblem(
                f"판정기가 뽑은 것을 다 받는다 ({잰것['본것']}개 중 {잰것['받음']}개)"
                " -- 아무것이나 답이면 찾을 것이 없다")

    led["seq"] += 1
    out = {"id": f"P{led['seq']}"}
    for f in FIELDS:
        v = rec.get(f)
        out[f] = v.strip() if isinstance(v, str) else (v if v is not None else "")
    par = get(led, parent) if parent != "-" else None
    out["계보"] = {"부모": parent, "연산자": op}
    out["깊이"] = 0 if par is None else par.get("깊이", 0) + 1
    led["problems"].append(out)
    return out


def lineage(led: dict, pid: str) -> list:
    chain, cur, seen = [], pid, set()
    while cur and cur not in seen:
        seen.add(cur)
        chain.append(cur)
        rec = get(led, cur)
        cur = (rec.get("계보") or {}).get("부모") if rec else None
        if cur == "-":
            break
    return list(reversed(chain))


def save(led: dict, path=None) -> None:
    p = Path(path or PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(led, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def load(path=None) -> dict:
    p = Path(path or PATH)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    if SEED.exists():
        return json.loads(SEED.read_text(encoding="utf-8"))
    return blank()


def brief(led: dict) -> str:
    rows = []
    for p in led.get("problems", []):
        g = p.get("계보") or {}
        rows.append(f"{p['id']:<5} {g.get('연산자', '씨앗'):<12} 깊이 {p.get('깊이', 0)}  "
                    f"{str(p.get('물음') or '')[:64]}")
    return "\n".join(rows)
