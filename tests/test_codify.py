"""codify(논문 이론 -> 검증된 코드)를 임시 저장소·가짜 코드공으로 **끝까지 돌려** 붙든다.

사용자 규정: 논문의 수식·알고리즘을 코드로, **표/데이터 같은 결과로 검증**(원장 역할).
이 저장소 규율대로 판정은 모델이 아니라 sandbox 에서 돌린 검사의 끝값이 한다.

붙드는 것: (1) 예시 입출력으로 **값까지** 검증 -- 틀린 함수는 실패해 재시도, 맞으면 성공,
(2) 예시 없으면 약한 검증(import·호출)이라고 **정직히 표시**(안 속인다), (3) 같은 코드
되풀이·바퀴 상한이면 멈춘다, (4) 성공한 코드만 codify/out 저장 + graph 색인(지은이=
'코드(검증통과)'), (5) 못 한 것은 미해결(수집기의 틈), (6) 모델 못 부르면 끝값 3, (7) 논문
코드화는 dig/paper 를 거쳐 수식·알고리즘을 스펙으로, (8) `!코드화` 배선 · 도구.

LLM·망 없이 돈다. 실행: python3 tests/test_codify.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from codify import run as C  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


임시 = Path(tempfile.mkdtemp(prefix="test-codify-"))

try:
    print("== 예시 입출력으로 값까지 검증: 틀리면 재시도, 맞으면 성공 ==")
    열 = ["```python\ndef 반감기(theta):\n    return theta\n```",                       # 틀림
         "```python\nimport math\ndef 반감기(theta):\n    return math.log(2) / theta\n```"]  # 맞음
    프 = []
    C.코드공 = lambda p: (프.append(p) or 열.pop(0))
    스펙 = {"종류": "수식", "이름": "ou반감기", "원문": "t_half = ln2/theta", "출처": "arxiv:x",
          "예시": [{"부른다": "반감기", "입력": {"theta": 0.05}, "답": 13.8629, "허용": 0.01}]}
    r = C.코드화(스펙, repo=임시, 바퀴=3)
    ok(r["성공"] and r["바퀴"] == 2 and [h["판정"] for h in r["해본것"]] == ["실패", "통과"],
       f"**틀린 함수 실패 -> 맞는 함수 통과 (값 검증)** ({[h['판정'] for h in r['해본것']]})")
    ok(not r["약한검증"], "예시가 있으면 약한 검증이 아니다")
    ok(r["파일"] == "codify/out/ou반감기.py" and (임시 / r["파일"]).is_file(), "성공 코드가 저장된다")
    내용 = (임시 / r["파일"]).read_text(encoding="utf-8")
    ok("출처: arxiv:x" in 내용 and "예시 입출력 통과" in 내용 and "math.log(2)" in 내용, "파일 머리에 출처·검증·코드")
    ok("틀린" not in 프[1] or "이미 낸 코드" in 프[1], "둘째 프롬프트에 지난 실패가 들어간다")
    ok("13.8629" in 프[0], "예시 값이 프롬프트에 있다")

    print("\n== 예시 없으면 약한 검증(정직) ==")
    C.코드공 = lambda p: "```python\ndef f(x):\n    return x + 1\n```"
    r = C.코드화({"종류": "알고리즘", "이름": "증분", "원문": "add one", "예시": []}, repo=임시)
    ok(r["성공"] and r["약한검증"], "예시 없으면 성공하되 약한 검증으로 표시")
    ok("약한 검증" in C.보고(r), "보고가 약한 검증임을 말한다")
    내용 = (임시 / r["파일"]).read_text(encoding="utf-8")
    ok("약한 검증(예시 없음)" in 내용, "파일에도 약한 검증 표시")

    print("\n== 같은 코드 되풀이 · 바퀴 상한 ==")
    C.코드공 = lambda p: "```python\ndef 반감기(theta):\n    return 0\n```"      # 늘 틀림, 늘 같음
    r = C.코드화(스펙, repo=임시, 바퀴=5)
    ok(not r["성공"] and r["바퀴"] == 2 and r["해본것"][-1]["판정"] == "반복" and "되풀이" in r["남은것"],
       f"**같은 코드 두 번이면 멈춘다** ({[h['판정'] for h in r['해본것']]})")
    정 = {"n": 0}

    def 매번다른(p):
        정["n"] += 1
        return f"```python\ndef 반감기(theta):\n    return {정['n']}\n```"
    C.코드공 = 매번다른
    r = C.코드화(스펙, repo=임시, 바퀴=99)
    ok(r["바퀴"] == 5 and 정["n"] == 5, f"**바퀴 99 줘도 최대 5** ({r['바퀴']}, 호출 {정['n']})")
    ok("ou반감기" in C.미해결들(임시), "성공 못 한 것은 미해결(수집기의 틈)")

    print("\n== 깨진 블록 · 모델 못 부름 ==")
    C.코드공 = lambda p: "설명만 하고 코드 블록이 없음"
    r = C.코드화({"종류": "수식", "이름": "블록없음", "원문": "x", "예시": []}, repo=임시, 바퀴=2)
    ok(not r["성공"] and any(h["판정"] == "깨짐" for h in r["해본것"]), "블록 없으면 깨짐")

    def 죽는(p):
        raise RuntimeError("쿼터")
    C.코드공 = 죽는
    r = C.코드화({"종류": "수식", "이름": "x", "원문": "x"}, repo=임시)
    ok(not r["돌았나"] and "코드공을 못 불렀다" in r["남은것"], "모델 못 부르면 돌았나=False (끝값 3)")

    print("\n== 성공 코드만 graph 에 색인된다 (지은이=검증통과) ==")
    from graph import store
    nodes, _ = store.읽기(임시)
    색인된 = [n for n in nodes if n.get("지은이") == "코드(검증통과)"]
    ok(색인된 and any("ou반감기" in n.get("요약", "") or "codify" in " ".join(n.get("깃발", [])) for n in 색인된),
       f"검증 통과한 코드화가 graph 에 {len(색인된)}개")

    print("\n== 논문 코드화: dig/paper 거쳐 수식·알고리즘을 스펙으로 ==")
    from dig import paper as PP
    논 = {"id": "2501.1", "제목": "P", "url": "u", "수식": ["\\alpha x"], "알고리즘": ["for x: update"],
         "그림": [], "표": [], "본문": "", "초록": "", "된문": ["html"], "못읽음": []}
    PP.논문받기 = lambda url, 문들=None: 논
    C.코드공 = lambda p: "```python\ndef f(*a, **k):\n    return 0\ndef run(*a, **k):\n    return 0\n```"
    try:
        r = C.논문코드화("https://arxiv.org/abs/2501.1", repo=임시)
        ok(r["스펙수"] == 2 and r["성공"] == 2, f"수식 1 + 알고리즘 1 = 스펙 2, 약한 검증 둘 다 성공 ({r})")
        보 = C.보고(r)
        ok("논문 코드화" in 보 and "성공 2" in 보, "논문 보고")
    finally:
        PP.논문받기 = None
finally:
    C.코드공 = None
    shutil.rmtree(임시, ignore_errors=True)

print("\n== 배선 ==")
import dispatch  # noqa: E402
ok("논문" in (dispatch.run("!코드화", allow_write=True) or ""), "!코드화 도움말")
ok("관리 채널" in (dispatch.run("!코드화 논문 2501.1", allow_write=False) or ""), "공개 채널 거절")
불림 = []
dispatch.run("!코드화 논문 2501.00001", runner=lambda argv, 로그, 무엇: (불림.append(argv) or "시작"), allow_write=True)
ok(불림 and 불림[0][:3] == ["python3", "codify/run.py", "--논문"], f"배경으로 논문 코드화 ({불림})")
ok(dispatch.run("!코드화기 x") is None, "붙여 쓴 `!코드화기` 는 명령이 아니다")
from router import call as Rt  # noqa: E402
ok("코드공" in Rt.역할들, "router 역할표에 코드공")
_도구 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("def codify_paper" in _도구 and _서버.count(" codify_paper,") >= 2, "codify_paper 도구·ADMIN_TOOLS·임포트")
ok("codify/run.py" in _서버, "프롬프트가 codify 를 이름을 대고 시킨다")
_sh = (뿌리 / "scripts" / "harvest.sh").read_text(encoding="utf-8")
ok("codify/run.py --논문" in _sh, "24h 루프가 harvest 뒤 codify 를 돈다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("codify: 값 검증 재시도 · 약한 검증 정직 · 되풀이 멈춤 · 색인 · 논문 · 배선 -- 통과")
