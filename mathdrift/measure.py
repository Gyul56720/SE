"""**확산을 잰다** -- 새것과 물려받은 것. `novel/diffusion.py` 의 두 계수를 공간 층으로.

원문의 규율 그대로다:

> 확산은 이 둘이 **함께** 있을 때만 일어난다. 새것만 있으면 산만해지고(연결 없는 나열),
> 되돌아온 것만 있으면 제자리를 돈다.

공간 층에서 그 둘은 이렇게 된다:

  · **새것**     부모에 없던 구조. 0 이면 이름만 바꾼 것이다
  · **물려받음**  부모에서 그대로 온 것. 0 이면 인과성이 없다 -- 남의 공간이다

"완전히 다르면 안 된다" 가 재는 것이 정확히 뒤엣것이다.

## 재는 방식과 그 한계를 먼저 적는다

칸에 적힌 낱말을 토큰으로 갈라 집합으로 견준다. **이것은 대리값이다.** 같은 구조를 다른
낱말로 쓰면 물려받은 것을 못 보고, 다른 구조를 같은 낱말로 쓰면 물려받았다고 잘못 센다.
`mathgen/README.md` 가 압축비에 대해 적어 둔 것과 같은 종류의 정직한 한계다.

제대로 재려면 두 공간 사이의 사상을 실제로 만들어 봐야 하는데, 그건 검증 단계의 일이고
비싸다. 여기서는 **싸게 재서 숫자를 돌려주되 아무것도 죽이지 않는다** -- 그것이
`diffusion.py` 의 첫 번째 제약이었다.
"""
from __future__ import annotations

import os
import re

from mathdrift import space as SP

_TOK = re.compile(r"[0-9A-Za-z가-힣]+")

# 어느 공간에나 나오는 말. 세면 전부 "물려받았다" 로 보여서 계수가 죽는다.
STOP = {"이", "그", "것", "수", "의", "를", "은", "는", "에", "로", "와", "과", "한",
        "하는", "있는", "되는", "공간", "점", "문제", "구조", "하나", "모든", "위", "안"}


# 낱말로 세지 않는 칸.
#   왜        사람에게 하는 설명이라 부모 얘기를 그대로 옮겨 적는다 -- 물려받음이 부푼다
#   해독      코드다. def·for·range 가 겹치는 것은 인과가 아니다
#   시금석점  수다. 셀 것이 낱말이 아니다
# 남는 것은 `식`·`점`·`정의역`·`이름` 이고, 그중 **`식` 이 이 자를 지탱한다** --
# 이름과 산문으로 재던 자가 뒤집혔던 이유가 그것이었다.
SKIP_FIELDS = ("왜", "해독", "시금석점")


def _toks(rec: dict) -> set[str]:
    """내용 칸만 본다."""
    buf = []
    for f in SP.FIELDS:
        if f in SKIP_FIELDS:
            continue
        v = rec.get(f)
        buf.append(v if isinstance(v, str) else str(v or ""))
    return {t for t in _TOK.findall(" ".join(buf)) if len(t) > 1 and t not in STOP}


# **한 낱말이 겹친 것은 물려받은 것이 아니다.** 실측: 아무 상관 없는 공간("날씨/기압")도
# "연속" 하나가 겹쳐서 확산으로 셌다. 그래서 겹친 낱말의 절대 수에 바닥을 둔다.
KEEP_MIN = int(os.environ.get("MATHDRIFT_KEEP_MIN", "2"))

# **몫의 분모는 부모다.** 처음에는 자식 어휘로 나눴는데, 그러면 **새 낱말을 많이 쓴 자식이
# 벌을 받는다** -- 그리고 새 낱말을 많이 쓰는 것이 바로 우리가 원하는 것이다.
#
# 실측(VM 첫 15개, 2026-09-07): 물려받음이 4로 같은데 새것이 21인 것은 몫 0.16 이고 새것이
# 적은 것은 더 높게 나왔다. 그 자로 재니 "자리스키 닫힘"(경계 랭크의 이웃) 과 "비가환
# 군대수"(Cohn-Umans) 가 **남의 공간** 으로 찍혔다 -- 알려진 갈아타기 넷 중 셋이 첫 15개
# 안에 나왔는데 자가 그것을 못 알아본 것이다.
#
# 물어야 할 것은 "자식이 부모 말을 얼마나 썼나" 가 아니라 **"부모의 무엇을 가져왔나"** 다.
# 분모를 부모 어휘로 바꾸면 새것을 많이 더한 것이 안 깎인다.
#
# 바닥값은 **실측으로 정할 것**이다. `spread.py --remeasure` 가 분포를 찍어 주므로, 그것을
# 보고 여기를 고친다. 지금 값은 첫 15개를 보고 잡은 것이라 표본이 얇다.
KEEP_SHARE = float(os.environ.get("MATHDRIFT_KEEP_SHARE", "0.10"))


def measure(child: dict, parent: dict | None) -> dict:
    """두 계수와, 둘이 함께 있는지.

    `몫` 은 **부모 어휘 중 물려받은 몫**이다. `자식몫` 도 같이 적어 둔다 -- 옛 자가
    무엇을 보고 있었는지 대조할 수 있어야 바닥값을 고칠 때 근거가 남는다.
    """
    c = _toks(child)
    if parent is None:                      # 씨앗은 부모가 없다 -- 잴 것이 없다
        return {"새것": len(c), "물려받음": 0, "몫": 0.0, "자식몫": 0.0,
                "확산": False, "씨앗": True}
    p = _toks(parent)
    new, kept = len(c - p), len(c & p)
    share = kept / len(p) if p else 0.0             # 부모의 얼마를 가져왔나
    cshare = kept / len(c) if c else 0.0            # 옛 자 (대조용)
    real = kept >= KEEP_MIN and share >= KEEP_SHARE
    out = {"새것": new, "물려받음": kept, "몫": round(share, 3),
           "자식몫": round(cshare, 3), "확산": bool(new and real), "씨앗": False}
    # **수로도 잰다.** 낱말은 장식할 수 있어도 치수와 정의역은 못 한다. 판정에는 안
    # 쓰고 적어만 둔다 -- 이 둘이 부모와 똑같으면 식이 정말 바뀌었는지 의심할 자리다.
    try:
        out["치수차"] = int(child.get("치수") or 0) - int(parent.get("치수") or 0)
    except (TypeError, ValueError):
        out["치수차"] = None
    out["정의역바뀜"] = ((child.get("정의역") or "").strip()
                    != (parent.get("정의역") or "").strip())
    return out


def note(m: dict) -> str:
    """숫자를 사람 말로. **판정이 아니라 관찰이다** -- 어느 쪽도 기각 사유가 아니다."""
    if m.get("씨앗"):
        return "씨앗"
    if not m["확산"] and not m["새것"]:
        return "제자리 -- 이름만 바뀐 것일 수 있다"
    if not m["확산"]:
        return (f"인과 약함 -- 부모에서 가져온 것이 {m['물려받음']}개"
                f" (부모의 {m['몫']}). 남의 공간일 수 있다")
    return f"확산 (새것 {m['새것']} / 물려받음 {m['물려받음']}, 몫 {m['몫']})"


def spread(led: dict) -> dict:
    """원장 전체에서 확산이 얼마나 일어났나. 이어 돌릴 때 얕아지는지를 본다."""
    n = ok = 0
    for s in led["spaces"]:
        m = s.get("잰것") or {}
        if m.get("씨앗"):
            continue
        n += 1
        ok += 1 if m.get("확산") else 0
    return {"잰공간": n, "확산": ok, "몫": (ok / n) if n else 0.0}


# 이름이 부모 이름을 그대로 품었나. **자가 뒤집혀 있는 것을 드러내는 자리다.**
#
# 실측 2026-09-07(60개): 부모 이름("멀티리니어 랭크 스펙트럼")에 연산자 어휘를 덧붙인
# 무리가 부모몫 최상위를 차지했고(S9 0.529 · S8 0.471 · S34 0.370), 이름이 정말 바뀐
# 것들("지수 대역 Exponent Cone", "오차 허용 지수 영역")이 바닥에 깔렸다. 뒤엣것이
# Strassen 의 점근 스펙트럼과 경계 랭크 쪽이다 -- **진짜 이주일수록 이름이 바뀌고,
# 이름이 바뀌면 낱말 겹침을 재는 자가 깎는다.**
#
# 그래서 이것은 판정이 아니라 **자를 의심하는 눈금**이다. 아무것도 기각하지 않는다.
DECO_MIN = int(os.environ.get("MATHDRIFT_DECO_MIN", "2"))


def decorated(child: dict, parent: dict | None) -> bool:
    if not parent:
        return False
    cn = {t for t in _TOK.findall(child.get("이름") or "") if len(t) > 1 and t not in STOP}
    pn = {t for t in _TOK.findall(parent.get("이름") or "") if len(t) > 1 and t not in STOP}
    return bool(pn) and len(cn & pn) >= min(DECO_MIN, len(pn))
