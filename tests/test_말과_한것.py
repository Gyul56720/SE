"""**"못 받았다" 는 말이 사실인지 잰다.**

    python3 tests/test_말과_한것.py

실측 2026-09-09. 공개 채널이 이렇게 답했다.

    현재 외부 네트워크 차단 및 보안 정책(403 Forbidden 등)으로 인해 직접적인
    데이터 수집이 제한되고 있습니다.

사용자가 같은 주소를 VM 에서 직접 돌려 보고 **"안막혔어"** 라고 했다. 즉
**안 해 보고 막혔다고 한 것**이다.

프롬프트에는 이미 적혀 있었다 -- "해 보기 전에 '수단이 없다' 고 하지 마라",
"안 되면 실패한 명령과 오류를 그대로 대라"(규칙 4·5). **적혀 있는데 어겼다.**
그러면 규칙을 더 적을 것이 아니라 **말이 사실인지 코드가 재야 한다** -- 이
저장소가 봇의 자동 rebase 에서 배운 것과 같다(규칙은 사람에게 적혀 있었고
그 줄은 봇에게 적혀 있었다).

`discord_bot_server` 는 langgraph·discord 없이는 임포트가 안 되므로, 그 파일에서
이 함수만 떼어 내 돌린다. **문자열로 재지 않는다** -- 함수를 진짜로 부른다.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

fails = []


def ok(cond, msg):
    print(("  OK   " if cond else "  실패 ") + msg)
    if not cond:
        fails.append(msg)


def _떼어내기():
    """`discord_bot_server.py` 에서 이 검사에 필요한 것만 떼어 실제로 돌린다."""
    src = (ROOT / "discord_bot_server.py").read_text(encoding="utf-8")
    나무 = ast.parse(src)
    쓸것 = []
    for n in 나무.body:
        if isinstance(n, ast.Assign) and any(
                getattr(t, "id", "") == "못받았다말" for t in n.targets):
            쓸것.append(n)
        elif isinstance(n, ast.FunctionDef) and n.name == "_말과_한것이_맞나":
            쓸것.append(n)
    if len(쓸것) < 2:
        return None, None
    ns: dict = {}
    exec(compile(ast.Module(body=쓸것, type_ignores=[]), "<떼어냄>", "exec"), ns)
    return ns.get("_말과_한것이_맞나"), ns.get("못받았다말")


맞나, 말들 = _떼어내기()
ok(맞나 is not None,
   "**`_말과_한것이_맞나` 가 discord_bot_server 에 있다** -- 없으면 어긋남을 아무도 안 잰다")
if 맞나 is None:
    print("떼어내지 못했다 -- 더 못 본다")
    sys.exit(1)

print()
print("── 안 해 보고 '막혔다' 고 하면 짚는다 (그때 그 답) ──────")
그때답 = ("중화역 근처 맛집 정보를 확인하기 위해 주요 검색 엔진과 맛집 서비스에 "
         "접근을 시도하였으나, 현재 외부 네트워크 차단 및 보안 정책(403 Forbidden 등)"
         "으로 인해 직접적인 데이터 수집이 제한되고 있습니다.")
난것 = 맞나(그때답, [])
ok(난것, "**(회귀) 그 답에 어긋남이 뜬다** -- 셸을 한 번도 안 불렀으므로")
ok("안 해 본 것" in 난것, "'막힌 것이 아니라 안 해 본 것' 이라고 적는다")
ok("dig/run.py" in 난것, "무엇을 하면 되는지 명령까지 적는다")

print()
print("── 부른 것이 다 성공했는데 '막혔다' 고 해도 짚는다 ───────")
난것 = 맞나("접근이 제한되어 조회할 수 없습니다", [("curl a", True), ("curl b", True)])
ok(난것 and "전부 성공했다" in 난것,
   "**성공만 해 놓고 못 받았다고 하면 어긋남이다** -- 무엇이 막혔는지 보여야 한다")
ok("2개" in 난것, "몇 개를 불렀는지 적는다")

print()
print("── 진짜 실패했으면 **아무 말 안 한다** ───────────────────")
ok(맞나("403 으로 막혀 못 받았다", [("curl a", False)]) == "",
   "**한 번이라도 실패했으면 그 말은 사실이다** -- 참말에 딴지를 걸면 안 된다")
ok(맞나("403 차단", [("a", True), ("b", False)]) == "", "하나만 실패해도 사실")

print()
print("── 못 받았다는 말이 없으면 안 본다 ──────────────────────")
ok(맞나("맛집 셋을 정리했습니다. 메뉴와 값은 아래와 같습니다", []) == "",
   "**멀쩡한 답에는 아무것도 안 붙인다** -- 셸을 안 불러도 답할 수 있는 물음이 있다")
ok(맞나("", []) == "" and 맞나(None, []) == "", "빈 답으로 안 죽는다")

print()
print("── 무엇을 '못 받았다' 로 보는가 ─────────────────────────")
for w in ("차단", "403", "수집이 제한", "긁어올 수 없", "접근이 제한"):
    ok(w in 말들, f"'{w}' 를 본다")
ok(len(말들) >= 8, f"여러 꼴을 본다 ({len(말들)}개) -- 모델이 매번 다르게 쓴다")
ok(맞나("파일을 못 찾았습니다", []) == "",
   "**아무 실패 말이나 잡지 않는다** -- 잡으면 멀쩡한 답에 잔소리가 붙는다")

print()
print("── 답을 지우지는 않는다 ────────────────────────────────")
ok(맞나(그때답, [])[:2] == "**",
   "붙일 말만 돌려준다 -- 답을 바꾸거나 버리지 않는다(부르는 쪽이 뒤에 잇는다)")

print()
if fails:
    print(f"말과 한 것: {len(fails)}개 실패 -- {fails}")
    sys.exit(1)
print("안 해 보고 막혔다고 하면 짚음 · 다 성공했는데 못 받았다 해도 짚음 · "
      "진짜 실패엔 침묵 · 멀쩡한 답엔 안 붙음 -- 통과")
