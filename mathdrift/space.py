"""**공간 원장** -- 후보가 아니라 *형식화*를 적는다.

`mathgen` 은 문제를 만들고 `novel/flow.py` 는 원고를 만든다. 여기서 만드는 것은 둘 다
아니다. **탐색공간 자체**다.

왜 한 층 올렸나. b=3 m=22 는 같은 공간(실수 CP 분해)을 CP-ALS · 무작위 재시작 · 강화학습 ·
flip graph 로 여러 번 훑어 소진됐다. 고정된 공간 안의 탐색은 정의상 최적화이고, 최적화는
자기가 받은 형식화를 떠나지 못한다. 역사적으로 이 문제를 뚫은 것은 전부 **공간을 갈아탄
것**이었다 -- 랭크에서 경계 랭크로(Schönhage), 텐서에서 군대수로(Cohn-Umans).

그래서 원장의 원소는 점이 아니라 공간이다. 그리고 **공간은 틀릴 수 없다.** 쓸모없을 뿐이다.
틀린 정리는 원장을 오염시키지만 빈 공간은 탐색해봐야 아무것도 안 나올 뿐이라, 발산
단계에서 엄밀성을 요구할 이유가 없다.

## 인과성은 검사하지 않는다 -- 구성으로 보장한다

`mathgen` 의 거꾸로 만들기와 같은 수다. 거기서는 답 F 를 먼저 골라 f = F' 를 문제로 내니
정답이 구성상 확실했다. 여기서는:

    새 공간 = 연산자(원장에 이미 있는 공간)

모델에게 "공간을 발명하라" 고 묻지 않는다. "여기 공간 S 가 있다, 여기 *경계화* 를 걸어라,
무엇이 되나" 라고 묻는다. 부모는 항상 원장에 있고 연산자는 고정 목록에서 나오므로
**계보 칸은 비거나 지어낼 수가 없다.** 인과성이 검사 항목이 아니라 문법이 된다.

## 칸을 비워도 기각하지 않는다

빈 칸은 나중에 채울 것이지 탈락 사유가 아니다. 이번 단계에서 죽이는 것은 없다 --
`novel/DRIFT.md` 의 첫 규칙 그대로다: *과잉 기각은 글 자체를 없앤다.* 다만 `되사상`
(이 공간의 점이 원래 문제로 어떻게 돌아가나)이 비면 나중에 검증이 아예 불가능하므로,
기각은 안 하되 **등급을 '검증불가'로 적어 둔다.**
"""
from __future__ import annotations

import json
import os
from pathlib import Path

PATH = Path(os.environ.get("MATHDRIFT_LEDGER",
                           Path(__file__).resolve().parent / "ledger.json"))

# **씨앗은 코드고 원장은 런타임 상태다.** 둘을 한 파일에 두었다가 사고를 냈다 --
# 원장이 추적되고 있어서 VM 이 낳은 공간 15개가 `git pull` 한 번에 씨앗만 든 커밋본으로
# 되돌아갔다(실측 2026-09-07). compression/ledger.json 과 novel/*.json 이 같은 이유로
# 이미 .gitignore 에 있는데 그 규약을 안 따랐던 것이다.
#
# 이제 원장은 추적하지 않고, 없으면 여기서 새로 세운다. 씨앗을 고치는 것은 커밋이고,
# 공간을 낳는 것은 런이다.
SEED = Path(__file__).resolve().parent / "seed.json"

# 공간 하나가 갖는 칸. **전부 비어도 받는다.**
#
# 처음에는 이름과 산문(`표기`·`되사상`·`크기`)으로 주고받았다. 그랬더니 모델이 부모
# 이름에 연산자 어휘를 덧붙이는 데로 수렴했고(실측 85개), 낱말 겹침을 재는 자가 그것을
# 최고점으로 줬다. 프롬프트도 자도 전부 낱말이었으니 표류가 어휘 공간에서 일어난 것이다.
#
# 그래서 오가는 것을 **식과 수와 코드**로 바꿨다. 표류하는 것은 이름이 아니라 `식` --
# 제약식 자체다. 씨앗의 식은 Brent 항등식이고, 연산자는 그 식을 변형한다(경계화는 ε 을
# 넣어 극한식으로, 표수 이동은 같은 식을 F_2 위에서, 대칭성 강제는 G-불변 해로 제한).
# 이름은 장식할 수 있어도 **식과 수는 장식할 수 없다.**
FIELDS = ("식", "점", "정의역", "유도", "치수", "해독", "부호화", "시금석점", "왜")

# **`이름` 칸을 없앴다.** 두 번 다 거기서 장식이 시작됐다 --
#   1차(85개) "멀티리니어 랭크 스펙트럼" + 연산자 어휘
#   2차(50개) "행렬곱 지수 식" + 수식어  (식으로 바꿨는데 장식이 식 쪽으로 따라왔다)
# 자식이 부모 이름을 못 보면 덧붙일 것도 없다. 부를 것이 필요하면 `식` 을 잘라 쓴다.
#
# `왜` 는 남기되 **자식에게 전달하지 않는다**(`spread.prompt` 가 안 싣는다). 사람이
# 원장을 읽을 때만 쓰는 칸이고, 표류 통로에는 기호만 흐른다.
HUMAN = ("왜",)

# `유도` 는 **가설에서 증명으로 가는 자리**다. 여기까지 파이프라인은 자식 식을 주장만
# 했다 -- "경계화를 걸면 이런 식이 된다" 고 적을 뿐 부모 식에서 그리로 가는 길을 보이지
# 않았다. 그것이 겉핥기고, 이름을 짓는 것과 다를 바가 없다. 걸음은 sympy 가 읽는 평문
# 수식이고, `prove.py` 가 이웃한 둘을 참/거짓/미정으로 가른다(호출 0회).
#
# `해독` 이 특별하다 -- 산문 되사상("요네다 매몰로 재해석")은 돌릴 것이 없어서 공허해도
# 통과했다. 코드는 **돌려 보면 끝난다.** 그래도 버리지 않는다: 다음 세대의 부모로는 쓴다.
NEEDED = "해독"

GRADES = ("미검증", "검증불가", "생존", "사망")


def blank() -> dict:
    return {"seq": 0, "spaces": [], "ops_used": {}}


def load(path=None) -> dict:
    """원장을 읽는다. **없으면 씨앗에서 새로 세운다** -- 빈 원장은 발산이 못 시작한다."""
    p = Path(path or PATH)
    if not p.exists():
        try:
            d = json.loads(SEED.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return blank()
        for k, v in blank().items():
            d.setdefault(k, v)
        return d
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return blank()
    for k, v in blank().items():
        d.setdefault(k, v)
    return d


def save(led: dict, path=None) -> None:
    p = Path(path or PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(led, ensure_ascii=False, indent=2), encoding="utf-8")


def get(led: dict, sid: str) -> dict | None:
    for s in led["spaces"]:
        if s.get("id") == sid:
            return s
    return None


def grade(rec: dict) -> str:
    """**등급은 벌이 아니라 표다.**

    처음에는 되사상이 비면 `검증불가` 를 붙였다. 그런데 그것이 프롬프트로 새어 들어가
    발산을 사양서로 만들었다 -- 20개 중 20개가 코드 칸을 채우려다 식이 밋밋해졌다.
    자유도가 이 단계의 전부이므로, 없는 것을 벌하지 않고 **있는 것을 표시**한다.

      · `검증가능`  해독기가 있고, 시금석점이 있거나 부호화로 만들 수 있다
                    -> `recall.py` 가 나중에 돌려 볼 수 있다
      · `미검증`    나머지 전부. **결함이 아니다.** 다음 세대의 부모로도 그대로 쓴다
    """
    if not (rec.get("해독") or "").strip():
        return "미검증"
    if rec.get("시금석점") or (rec.get("부호화") or "").strip():
        return "검증가능"
    return "미검증"


def add(led: dict, rec: dict, parent: str, op: str, dist: int = 1) -> dict:
    """공간 하나를 원장에 올린다. **부모와 연산자 없이는 올릴 수 없다.**

    이 서명이 인과성을 강제하는 자리다. `parent` 가 원장에 없으면 거절한다 -- 내용을
    판정해서 거절하는 것이 아니라, 계보가 끊긴 것을 원장이 못 받게 하는 것이다.
    """
    if parent != "-" and get(led, parent) is None:
        raise ValueError(f"부모 {parent} 가 원장에 없다 -- 계보가 끊긴 공간은 안 받는다")
    led["seq"] += 1
    out = {"id": f"S{led['seq']}"}
    for f in FIELDS:
        v = rec.get(f)
        out[f] = v.strip() if isinstance(v, str) else (v if v is not None else "")
    out["계보"] = {"부모": parent, "연산자": op, "거리": dist}
    out["등급"] = grade(out)
    out["잰것"] = {}
    led["spaces"].append(out)
    led["ops_used"][op] = led["ops_used"].get(op, 0) + 1
    return out


def lineage(led: dict, sid: str) -> list[str]:
    """씨앗까지 거슬러 올라간 사슬. 계보가 사슬로 남는다는 것이 이 설계의 요점이다."""
    chain, cur, seen = [], sid, set()
    while cur and cur not in seen:
        seen.add(cur)
        chain.append(cur)
        rec = get(led, cur)
        if not rec:
            break
        cur = (rec.get("계보") or {}).get("부모")
        if cur == "-":
            break
    return list(reversed(chain))


def brief(led: dict, limit: int = 30) -> str:
    out = []
    for s in led["spaces"][-limit:]:
        g = s["계보"]
        out.append(f"  {s['id']:<5} {g['연산자']:<10} <- {g['부모']:<4} "
                   f"[{s['등급']}]  {str(s.get('식') or '')[:70]}")
    return "\n".join(out)
