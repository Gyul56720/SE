# -*- coding: utf-8 -*-
"""**Priya 의 검증 보고서가 회로를 가리는가 -- 아니면 늘 nsw_fir 을 도는가.**

사용자(2026-09-22): *"fir 만든걸 mera에 못쓰는건 제대로된 에이전트가 아니야"*

실측 2026-09-23, `house/dv/agent.py` 를 재 보니:

    SIM.돌리기 호출 여섯 중 **하나만** `설계=` 를 넘겼다
      -> 나머지 다섯은 `설계=None` 이라 **언제나 nsw_fir 을 돈다**
      -> 다른 회로를 넘기면 닫기곡선만 그 회로고 나머지 수는 전부 FIR 것이다

    구성 스윕이 `{"STAGES": 2}` · `{"CDC_STAGES": 3}` · `{"GATE_POLICY": 0}`
      -> FIR 의 파라미터 이름이다. 그리고 `{"STAGES": 3}` 은 **기본값**이라
         네 구성 중 하나는 아무것도 안 바꾸고 돌았다

    `sch.py` 의 구조도에 `nsw_fir` 이 **그림틀 안에** 박혀 있었다
      -> 부르는 쪽이 옳은 이름을 넘겨도 `nsw_fir (mera_rec …)` 로 찍힌다

Ethan 쪽에서 고친 것과 **같은 병**이다(PR #381).

실행: python3 tests/test_dv범용.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


from house import designs as DES               # noqa: E402
from house import rtlscan as SCAN              # noqa: E402
from house.dv import agent as DA               # noqa: E402

_소스 = (뿌리 / "house" / "dv" / "agent.py").read_text(encoding="utf-8")


def _호출들(글: str, 이름: str) -> list:
    """`이름(` 으로 시작하는 호출의 인자 글을 괄호를 세어 잘라 낸다."""
    난것 = []
    for m in re.finditer(re.escape(이름) + r"\(", 글):
        i, 깊이 = m.end(), 1
        while i < len(글) and 깊이:
            깊이 += (글[i] == "(") - (글[i] == ")")
            i += 1
        난것.append(글[m.end():i - 1])
    return 난것


# ============================================ 1. **모든 실행이 그 회로를 돈다**
_호출 = _호출들(_소스, "SIM.돌리기")
_빠진것 = [c for c in _호출 if "설계=" not in c]
ok(_호출, f"SIM.돌리기 호출을 찾는다 ({len(_호출)}개)")
ok(not _빠진것,
   "**모든 `SIM.돌리기` 가 `설계=` 를 넘긴다** — 안 넘기면 `설계=None` 이라 "
   "언제나 nsw_fir 을 돈다"
   + (f" (빠진 것 {len(_빠진것)}개: {[c[:40] for c in _빠진것]})" if _빠진것 else ""))

# ============================================ 2. 구성 스윕이 회로에서 난다
_d = DES.찾기("fir")
_기본 = DA._기본파라(_d)
_조합 = DA._구조구성(_d)
ok(_기본 and "STAGES" in _기본,
   f"톱 파라미터를 RTL 에서 읽는다 ({len(_기본)}개) — `설계.파라` 는 비어 있다 "
   f"({getattr(_d, '파라', {})})")
ok(_조합, f"구성이 난다 ({[DA._구성글(c) for c in _조합]})")
ok(all(any(_기본.get(k) != v for k, v in c.items()) for c in _조합),
   "**기본값과 같은 구성이 안 난다** — `{'STAGES': 3}` 이 기본값인데 구성에 "
   "들어 있어서, 넷 중 하나가 아무것도 안 바꾸고 돌았다")
_이름들 = {k for c in _조합 for k in c}
ok(_이름들 <= set(_기본),
   f"흔드는 이름이 전부 **이 회로에 있는** 파라미터다 ({sorted(_이름들)})")
ok(len({k for c in _조합 for k in c}) >= 2,
   "**파라미터마다 자리를 준다** — 앞에서부터 자르면 한 이름이 다 먹는다")

# 회로에 구조 파라미터가 없으면 **지어내지 않는다**
class _빈설계:
    파라, RTL, top = {}, [], ""
ok(DA._구조구성(_빈설계()) == [],
   "흔들 구조 파라미터가 없으면 **빈 목록** — 없는 파라미터를 지어내지 않는다")

# ============================================ 3. 글에 FIR 이름이 안 박혀 있다
sys.path.insert(0, str(뿌리 / "tests"))
import _소스보기                                             # noqa: E402

# **이 도우미부터 스스로를 검사한다.** 첫 판이 토큰을 줄바꿈으로 이어 붙여
# 소스를 뭉갰고, 「없어야 한다」 검사는 뭉갠 소스에서 **언제나 통과**했다.
_소스보기.자기검사()
_산주장 = _소스보기.산주장

_산 = _산주장(_소스)
for 없어야, 뭐 in (
    ('{"STAGES": 2}', "구성 스윕에 박힌 `{\"STAGES\": 2}`"),
    ('{"TAPS": 8, "STAGES": 3, "GATE_POLICY": 1}', "파형 뜨기에 박힌 파라미터"),
    ('"nsw_fir  TAPS=8', "구조도의 `nsw_fir  TAPS=8 · STAGES=3`"),
    ("STAGES·CDC_STAGES·GATE_POLICY 를 바꿔도 돈다", "계획 표에 박힌 파라미터 이름"),
    ("비동기 두 도메인 · ICG 클럭게이팅", "구조도 부제에 박힌 FIR 설명"),
):
    ok(없어야 not in _산, f"**지웠다**: {뭐}")

_sch = _산주장((뿌리 / "house" / "sch.py").read_text(encoding="utf-8"))
ok('DUT — nsw_fir' not in _sch,
   "**그림틀에 `nsw_fir` 이 안 박혀 있다** — 부르는 쪽이 옳은 이름을 넘겨도 "
   "`nsw_fir (…)` 로 찍히던 자리다")

# ============================================ 4. 라벨과 부제가 회로에서 난다
_m = {"top": _d.top, "기본파라": _기본, "구성조합": _조합,
     "훑기": SCAN.훑기(_d.RTL, _d.top)}
_보일 = DA._보일파라(_m)
ok(set(_보일) & _이름들,
   f"**구조도가 이 실행이 흔든 파라미터를 보인다** ({_보일}) — 알파벳 순으로 "
   f"자르면 ACCW·CDC_STAGES·CNTW 처럼 아무 이야기 없는 셋이 뽑힌다")
_부제 = DA._회로부제(_m)
ok("클럭" in _부제 and "FSM" in _부제,
   f"부제를 RTL 스캔에서 읽는다 ({_부제})")
ok(DA._회로부제({"훑기": {}}), "스캔이 비면 **비었다고 적는다** — 지어내지 않는다")

# ============================================ 5. 커버리지 분모가 한 군데에서 난다
from house import sim as SIM                                 # noqa: E402

_r = SIM.돌리기(None, seed=3, txn=40, maxlen=64, cap=60000, 설계=_d)
ok("cov_all" in _r and "cov_hit" in _r,
   f"**테스트벤치가 분모를 내보낸다** (hit {_r.get('cov_hit')}/{_r.get('cov_all')}) "
   f"— 파이썬에 `52` 를 따로 적어 두면 TB 에서 칸이 늘어도 조용히 안 바뀐다")
ok(abs(100.0 * _r["cov_hit"] / _r["cov_all"] - _r["cov_pct"]) < 1e-3,
   "hit/all 이 cov_pct 와 **맞는다** — 되맞춰 본다")
ok("* 52" not in _산 and "/ 100 * 52" not in _산,
   "파이썬 쪽에 박힌 `52` 산술이 없다 (못 읽었을 때의 되돌이값만 남긴다)")

# ============================================ 6. 요약이 실패를 센다
ok('x.get("fail") or x.get("timeout")' in _산,
   "**요약이 구성별 실패를 세고 나서 적는다** — 옛 판은 실패를 안 보고 "
   "«각각 회귀 통과» 라고 적었다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for f in FAIL:
        print("   · " + f)
    raise SystemExit(1)
print("dv범용: 회로를 가린다 · 구성이 RTL 에서 난다 · 분모가 한 군데다 -- 통과")
