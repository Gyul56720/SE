"""!자가개선 을 임시 저장소 + 진짜 sandbox·plan 으로 **끝까지 돌려** 붙든다. 모델·망만 가짜.

사용자(2026-09-11): "시스템을 개선할 방법을 스스로 탐색해서 제안한 뒤에 샌드박스에서 시뮬레이션하고
성능 평가가 이루어졌다고 판단되면 사용자의 동의를 구하고 자가 개선한다. 제2의 뇌를 근거로 하고,
탐색 범위가 부족하면 스스로 넓힌다."

붙드는 것: (1) 틈의 판정 명령이 실제 트리에서 빨강일 때만 틈이다(초록이면 '이미초록'),
(2) 제2의 뇌에 근거가 모자라면 스스로 넓혀 모은다(확장바퀴 상한), (3) 제안은 **그림자에만** 닿고
red->green 이 뒤집혀야 하며 리허설이 초록이어야 **동의 대기**가 된다 -- 실제 트리는 그대로,
(4) 사람이 승인해야 붙는다(봇은 dispatch 로 승인 못 침), (5) 안 고쳐지는 제안은 버리고 다음 후보,
(6) 검사를 약화시키는 패치·게이트를 만지는 패치는 거절, (7) 계획판이 켜져 있으면 안 돈다,
(8) 후보 상한 5, (9) 원장·메모, (10) 배선(명령·자연어·6h 루프·배포·union).

실행: python3 tests/test_improve.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from improve import run as I  # noqa: E402
from plan import store as P   # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=False)


os.environ.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})
d = Path(tempfile.mkdtemp(prefix="test-improve-"))
초록리허설 = lambda repo, 판, 초, 전부=False, 전부초=1800: {  # noqa: E731
    "판": str(판), "그림자": True, "바뀐것": ["mod.py"], "걸음": [("문법", 0, ""), ("게이트", 0, "")],
    "통과": True, "못잼": [], "걸린초": 0.1}
틈 = {"종류": "CI실패검사", "무엇": "test_mod.py", "판정명령": "python3 tests/test_mod.py", "왜": "main CI 가 빨강이다"}
고치는패치 = json.dumps({"꼴": "패치", "왜": "f 가 2를 돌려 검사가 깨진다 -> 1", "근거": ["dig/corpus/x.md#abc"],
                    "편집": [{"path": "mod.py", "old": "return 2", "new": "return 1"}]}, ensure_ascii=False)
try:
    git(d, "init", "-q")
    (d / "gatekeeper.py").write_text("import sys\nprint('[게이트 통과] 흉내')\nsys.exit(0)\n", encoding="utf-8")
    (d / "tests").mkdir()
    (d / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8")
    (d / "tests" / "test_mod.py").write_text('import sys; sys.path.insert(0, ".")\nimport mod\nassert mod.f() == 1, "f 는 1"\nprint("ok")\n', encoding="utf-8")
    git(d, "add", "-A"); git(d, "commit", "-qm", "bug")

    from research import run as Rs
    Rs.분해기 = lambda 목표, 막힌것: "general method one\ngeneral method two"   # 모델 없이 빠르게
    I.틈모으기_ = lambda repo: [틈]
    P.리허설기 = 초록리허설
    # 여기 대목들은 **흐름**을 본다(패치가 붙고 시뮬을 지나 동의대기까지). 검사 없는 가짜 패치가 많으니 공허 판정은
    # 주입으로 꺼 둔다 -- 진짜 공허 판정은 아래 '초록의 뜻' 대목에서 실제 저장소로 붙든다.
    I.공허검사기 = lambda repo, 판: {"공허": False, "말": "검사 주입", "검사들": [], "코드들": []}
    넓힌 = []
    I.넓히기_ = lambda 질의들, repo: 넓힌.append(list(질의들))

    print("== 근거: 제2의 뇌가 비면 스스로 넓힌다 (상한까지) ==")
    근 = I.근거모으기(틈, d)
    ok(근["확장"] == I.확장바퀴 and len(넓힌) == I.확장바퀴 and 근["참고"] == [], f"**참고 0 -> {I.확장바퀴}바퀴 넓혀 모았다** (질의 {len(근['질의'])}개)")
    ok(all(q for qs in 넓힌 for q in qs), "넓힐 때 일반 방법론 질의를 준다(기계 일반화라도)")

    print("\n== 탐색 -> 제안 -> 그림자 시뮬 -> 동의 대기 (실제 트리는 그대로) ==")
    I.제안기 = lambda prompt: 고치는패치
    r = I.자가개선(d, 몇=3)
    후 = r["동의대기"]
    ok(r["돌았나"] and 후 is not None and 후["판정"] == "동의대기", f"동의 대기 후보가 생긴다 ({[x['판정'] for x in r['해본']]})")
    ok((d / "mod.py").read_text(encoding="utf-8") == "def f():\n    return 2\n", "**실제 트리는 안 바뀌었다**")
    ok(P.현재판(d) is not None and str(P.읽기(d)["요청"]).startswith("자가개선:"), "그림자 계획판이 열려 동의를 기다린다")
    ok(후["댄근거"] == ["dig/corpus/x.md#abc"] and "근거" in I.보고(r), "제안이 댄 근거(출처#해시)가 보고에 남는다")
    ok("+    return 1" in 후["diff"] and "-    return 2" in 후["diff"], "diff 가 사람에게 보인다")
    ok("사람의 동의" in 후["말"] and "red->green" in 후["말"], "red->green · 리허설 초록 뒤 동의를 기다린다고 말한다")
    본 = (d / r["메모"]).read_text(encoding="utf-8")
    ok("자가개선 탐색" in 본 and "동의 대기" in 본, "메모가 남는다(밤에 장기기억으로)")
    꼴들 = [x.get("꼴") for x in I.원장읽기(d)]
    ok(["탐색", "후보", "끝"] == [k for k in 꼴들 if k in ("탐색", "후보", "끝")], f"원장 탐색/후보/끝 ({꼴들})")

    print("\n== 사람이 승인해야 붙는다 ==")
    ok("계획판이 이미 켜져 있다" in I.자가개선(d)["남은것"], "동의 대기 중엔 또 돌지 않는다(한 번에 하나)")
    말 = I.승인(d, 누가="검사")
    ok("적용됨" in 말 and (d / "mod.py").read_text(encoding="utf-8") == "def f():\n    return 1\n", f"**승인하면 실제 트리에 붙는다** ({말[:40]})")
    ok(P.현재판(d) is None and any(x.get("꼴") == "승인" for x in I.원장읽기(d)), "계획판이 닫히고 승인이 원장에 남는다")
    git(d, "commit", "-qam", "improved")
    r2 = I.한후보(틈, d)
    ok(r2["판정"] == "이미초록", "고친 뒤엔 같은 틈이 '이미초록' 이다 -- 틈이 아니다")

    print("\n== 안 고쳐지는 제안은 버리고 다음 후보로 ==")
    (d / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8"); git(d, "commit", "-qam", "bug again")
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "x", "편집": [{"path": "mod.py", "old": "return 2", "new": "return 3"}]})
    r = I.자가개선(d, 몇=3)
    ok(r["동의대기"] is None and r["해본"][0]["판정"] == "빨강그대로" and P.현재판(d) is None,
       f"**패치를 붙여도 빨강이면 버린다** ({r['해본'][0]['판정']})")
    ok((d / "mod.py").read_text(encoding="utf-8") == "def f():\n    return 2\n", "실제 트리는 그대로")

    print("\n== 검사를 약화시키는 패치 · 게이트를 만지는 패치는 거절 ==")
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "x", "편집": [{"path": "tests/test_mod.py", "old": 'assert mod.f() == 1, "f 는 1"\n', "new": ""}]})
    r = I.자가개선(d, 몇=1)
    ok(r["해본"][0]["판정"] == "적용실패" and "약화" in r["해본"][0]["말"], "**assert 를 빼는 패치는 거절**")
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "x", "새파일": [{"path": "gates/G999_x.py", "내용": "RULE_ID='G999'\n"}]})
    r = I.자가개선(d, 몇=1)
    ok(r["해본"][0]["판정"] == "적용실패", f"**gates/ 를 만드는 패치는 거절**(toolgate) ({r['해본'][0]['말'][:50]})")
    I.제안기 = lambda prompt: "고칠 수 없다"
    r = I.자가개선(d, 몇=1)
    ok(r["해본"][0]["판정"] == "제안없음", "패치 꼴이 아니면 제안없음")

    print("\n== 리허설 빨강이면 붙이지 않는다 ==")
    I.제안기 = lambda prompt: 고치는패치
    P.리허설기 = lambda repo, 판, 초, 전부=False, 전부초=1800: {"판": str(판), "그림자": True, "바뀐것": ["mod.py"], "걸음": [("게이트", 1, "G0 위반")], "통과": False, "못잼": [], "걸린초": 0.1}
    r = I.자가개선(d, 몇=1)
    ok(r["해본"][0]["판정"] == "리허설빨강" and P.현재판(d) is None, "**red->green 이어도 리허설이 빨강이면 버린다**")
    P.리허설기 = 초록리허설

    print("\n== `!개선 <말>`: 사람이 말한 개선 -- red->green 이 아니라 **레포 전체 회귀 없음**이 판정 ==")
    I.틈모으기_ = lambda repo: [틈]
    본판 = {"전부": None}

    def 리허설_회귀없음(repo, 판, 초, 전부=False, 전부초=1800):
        본판["전부"] = 전부
        return {"판": str(판), "그림자": True, "바뀐것": ["mod.py"], "걸음": [("레포 전체(회귀)", 0, "새로 깨진 것 없음")],
                "통과": True, "못잼": [], "걸린초": 1.0, "회귀": {"새로깨짐": [], "고쳐짐": [], "그대로빨강": []}}
    P.리허설기 = 리허설_회귀없음
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "부탁대로 고침", "근거": ["arxiv#1"],
                                      "편집": [{"path": "mod.py", "old": "return 2", "new": "return 1"}]}, ensure_ascii=False)
    r = I.사용자개선("f 가 1을 돌려주게 해줘", d, 초=30)
    ok(r["판정"] == "동의대기" and 본판["전부"] is True,
       f"**부탁은 레포 전체 시뮬을 거쳐 동의 대기** (판정 {r['판정']}, 전부={본판['전부']})")
    ok(r["회귀"] == {"새로깨짐": [], "고쳐짐": [], "그대로빨강": []} and "회귀 없음" in I.부탁보고(r), "회귀 결과가 보고에 남는다")
    ok(r["댄근거"] == ["arxiv#1"] and (d / "mod.py").read_text(encoding="utf-8") == "def f():\n    return 2\n",
       "근거를 대고, 실제 트리는 그대로")
    ok("판열림" == I.사용자개선("또", d)["판정"], "동의 대기 중엔 또 안 받는다")
    ok("적용됨" in I.승인(d, 누가="검사"), "`!개선 승인` 으로 붙는다")
    git(d, "commit", "-qam", "부탁 반영")

    print("\n== 고약한 제안기: 실제 모델처럼 틀리는 답 -- 그래도 끝까지 가는가 ==")
    # 사용자(2026-09-12): "왜 이런 버그가 계속 생기지? 근본적으로 잡아봐." -- 여기까지의 가짜 제안기는
    # 전부 얌전했다(old 가 글자 그대로, JSON 이 깨끗). 실제 모델은 펜스로 감싸고 앞뒤에 말을 붙이고
    # 들여쓰기 한 칸을 틀린다. 얌전한 가짜로만 검사하면 첫 실전에서만 터진다. 그래서 고약하게 만든다.
    (d / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8"); git(d, "commit", "-qam", "고약 전")
    P.리허설기 = 리허설_회귀없음
    호출 = []

    def _고약_공백(prompt):            # 펜스 + 앞뒤 말 + 들여쓰기 두 칸(파일은 네 칸)
        호출.append(prompt)
        return ('물론입니다. 아래처럼 고치면 됩니다.\n```json\n'
                + json.dumps({"꼴": "패치", "왜": "공백 틀림", "근거": ["x#1"],
                              "편집": [{"path": "mod.py", "old": "def f():\n  return 2\n", "new": "def f():\n    return 1\n"}]}, ensure_ascii=False)
                + '\n```\n끝입니다. {참고}')
    I.제안기 = _고약_공백
    r = I.사용자개선("f 가 1", d, 초=30)
    ok(r["판정"] == "동의대기" and r.get("적용시도") == 1 and len(호출) == 1,
       f"**펜스·말·들여쓰기 틀림은 되묻지 않고 그 자리에서 맞춘다** (판정 {r['판정']} · 시도 {r.get('적용시도')} · 호출 {len(호출)})")
    I.버림(d)

    print("\n== 남은 계획판: 봇이 켠 것은 봇이 치운다 ==")
    # 실측 2026-09-12(VM): `!개선` 이 0.3분 만에 "판열림 -- 사람이 끝내라" 로 죽었다. 앞 실행이 남긴 판이었다.
    # 동의를 기다릴 자격은 '지금 diff 그대로 리허설 초록' 인 판에만 있다. 나머지는 찌꺼기 -- 치우고 이어 간다.
    P.켜기("죽은 실행이 남긴 판", repo=d, 누가="개선")          # 시험 안 함
    r = I.사용자개선("f 가 1", d, 초=30)
    ok(r["판정"] == "동의대기" and any(x.get("꼴") == "판정리" and x.get("왜") == "시험을 안 한 판" for x in I.원장읽기(d)),
       f"**시험 안 한 판은 치우고 이어 간다** -- 사람 몫이 아니다 (판정 {r['판정']})")
    ok("판열림" == I.사용자개선("또", d)["판정"], "지금 diff 그대로 초록인 판은 그대로 동의를 기다린다")
    (Path(P.현재판(d)) / "mod.py").write_text("def f():\n    return 3\n", encoding="utf-8")   # 시험 뒤 또 바뀜
    r = I.사용자개선("f 가 1", d, 초=30)
    줄 = [x for x in I.원장읽기(d) if x.get("꼴") == "판정리" and x.get("왜") == "시험한 뒤 코드가 또 바뀜"]
    ok(r["판정"] == "동의대기" and 줄, f"시험한 뒤 또 바뀐 판도 치운다 (판정 {r['판정']})")
    ok(줄 and 줄[-1].get("diff") and "return 3" in (d / 줄[-1]["diff"]).read_text(encoding="utf-8"),
       f"치우기 전에 그 판의 diff 를 logs/ 에 남긴다 -- 사람 손일 수도 있다 ({(줄 or [{}])[-1].get('diff')})")
    I.버림(d)
    # 실측 2026-09-12(VM): PDF 부탁이 시험 중일 때 자가개선이 나란히 돌아 그 판을 '시험 안 한 판' 이라며 치웠다.
    # 켠 프로세스가 살아 있으면 남의 일이 도는 중이다 -- **치우지 않는다.** 기다리고, 한도를 넘기면 말한다.
    import subprocess as _sp
    산것 = _sp.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    _틈0, _한도0 = I._기다림틈, I.기다림초
    I._기다림틈, I.기다림초 = 0.2, 0.5                  # 기다림 자체는 아래 대목에서 따로 붙든다
    try:
        P.켜기("나란히 도는 실행의 판", repo=d, 누가="개선")
        상태 = d / P.상태상대; 상 = json.loads(상태.read_text(encoding="utf-8"))
        상["pid"], 상["태어난시각"] = 산것.pid, P.태어난시각(산것.pid)
        상태.write_text(json.dumps(상, ensure_ascii=False), encoding="utf-8")
        r = I.사용자개선("f 가 1", d, 초=30)
        ok(r["판정"] == "판열림" and "넘게 쓰고 있다" in r["말"] and P.현재판(d) is not None,
           f"**켠 프로세스가 살아 있으면 치우지 않는다** (판정 {r['판정']} · {r['말'][:40]})")
        ok("넘게 쓰고 있다" in I.자가개선(d)["남은것"], "자가개선도 같은 판단을 한다")
    finally:
        산것.kill(); 산것.wait()
        I._기다림틈, I.기다림초 = _틈0, _한도0
    r = I.사용자개선("f 가 1", d, 초=30)
    ok(r["판정"] == "동의대기" and any(x.get("꼴") == "판정리" for x in I.원장읽기(d)[-3:]),
       f"그 프로세스가 죽으면 찌꺼기다 -- 치우고 이어 간다 (판정 {r['판정']})")
    I.버림(d)
    P.켜기("죽은 판", repo=d, 누가="자가개선")
    import shutil as _sh; _sh.rmtree(P.현재판(d), ignore_errors=True)                       # 디렉터리가 사라진 판
    r = I.사용자개선("f 가 1", d, 초=30)
    ok(r["판정"] == "동의대기", f"디렉터리가 사라진 판도 막지 않는다 (판정 {r['판정']})")

    print("\n== 산 실행이 판을 쥐고 있으면 **기다렸다 이어 간다** (사람에게 안 넘긴다) ==")
    # 실측 2026-09-12(VM): "계획판을 다른 실행이 쓰는 중이다 … 그 실행이 끝나면 다시 부탁하라" 가
    # 사용자에게 갔다. 이 일 자체가 배경이므로 기다릴 수 있다.
    import subprocess as _sp3
    I.버림(d)
    짧은일 = _sp3.Popen([sys.executable, "-c", "import time; time.sleep(3)"])
    P.켜기("나란히 도는 실행", repo=d, 누가="개선")
    상태p = d / P.상태상대
    상 = json.loads(상태p.read_text(encoding="utf-8"))
    상["pid"], 상["태어난시각"] = 짧은일.pid, P.태어난시각(짧은일.pid)
    상태p.write_text(json.dumps(상, ensure_ascii=False), encoding="utf-8")
    _틈전, I._기다림틈 = I._기다림틈, 0.4
    try:
        막힘, 말2 = I.판정리(d)
        # 기다린 뒤 판이 남아 있으면 찌꺼기로 치우고, 비었으면 그대로 이어 간다 -- 어느 쪽이든 **막지 않는다**.
        ok(not 막힘 and ("이어 간다" in 말2 or "치웠다" in 말2), f"**기다렸다 이어 간다** ({말2[:70]})")
        꼴들2 = [x.get("꼴") for x in I.원장읽기(d)]
        ok("기다림" in 꼴들2 and "기다림끝" in 꼴들2, f"기다린 것이 원장에 남는다 ({꼴들2[-4:]})")
    finally:
        짧은일.kill(); 짧은일.wait()
        I._기다림틈 = _틈전

    print("\n== 한도를 넘기면 그때만 사람에게 말한다 ==")
    긴일 = _sp3.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        P.켜기("오래 쥔 실행", repo=d, 누가="자가개선")
        상 = json.loads(상태p.read_text(encoding="utf-8"))
        상["pid"], 상["태어난시각"] = 긴일.pid, P.태어난시각(긴일.pid)
        상태p.write_text(json.dumps(상, ensure_ascii=False), encoding="utf-8")
        _틈전, _한도전 = I._기다림틈, I.기다림초
        I._기다림틈, I.기다림초 = 0.2, 0.5
        try:
            막힘, 말3 = I.판정리(d)
            ok(막힘 and "넘게 쓰고 있다" in 말3, f"한도를 넘기면 막는다 ({말3[:60]})")
        finally:
            I._기다림틈, I.기다림초 = _틈전, _한도전
    finally:
        긴일.kill(); 긴일.wait()
    I.버림(d)

    print("\n== pid 돌려쓰기: 같은 pid 라도 태어난시각이 다르면 남이다 ==")
    # pid 만 보면 죽은 실행의 판을 '남이 쓰는 중' 으로 읽어 **영영 안 치운다** -- 거짓 양성은 멈춤이다.
    ok(I._살아있나(os.getppid()) is True, "부모는 살아 있다(pid 만 볼 때)")
    ok(I._살아있나(os.getppid(), 태어난시각=999999) is False,
       "**태어난시각이 다르면 죽은 것으로 본다** -- pid 돌려쓰기에 안 속는다")
    ok(I._살아있나(os.getppid(), 태어난시각=P.태어난시각(os.getppid())) is True, "태어난시각이 맞으면 살아 있다")
    ok(I._살아있나(os.getpid()) is False, "나 자신은 막지 않는다")
    ok(P.태어난시각(os.getpid()) is not None and P.태어난시각(2 ** 30) is None, "태어난시각: 있는 pid 만 숫자")
    좀비 = _sp3.Popen([sys.executable, "-c", "pass"])       # 끝났는데 안 거둬 간 것 -- os.kill(pid,0) 은 된다
    try:
        import time as _t3
        for _ in range(50):
            if P.프로세스표(좀비.pid)[0] == "Z":
                break
            _t3.sleep(0.1)
        ok(P.프로세스표(좀비.pid)[0] == "Z" and I._살아있나(좀비.pid) is False,
           f"**좀비는 죽은 것으로 본다** -- 아니면 끝난 실행을 한도까지 기다린다 (상태 {P.프로세스표(좀비.pid)[0]})")
    finally:
        좀비.wait()
    I.버림(d)

    호출.clear()

    def _고약_틀린old(prompt):         # 첫 답은 없는 글, 되묻자 실제 글을 베껴 맞춘다
        호출.append(prompt)
        if len(호출) == 1:
            return json.dumps({"꼴": "패치", "왜": "틀림", "편집": [{"path": "mod.py", "old": "    return 99\n", "new": "    return 1\n"}]})
        return json.dumps({"꼴": "패치", "왜": "맞음", "편집": [{"path": "mod.py", "old": "    return 2\n", "new": "    return 1\n"}]})
    I.제안기 = _고약_틀린old
    r = I.사용자개선("f 가 1", d, 초=30)
    ok(r["판정"] == "동의대기" and r.get("적용시도") == 2,
       f"**뜻이 틀린 old 는 실제 글을 들려 되묻고 둘째에 맞춘다** (판정 {r['판정']} · 시도 {r.get('적용시도')})")
    ok(len(호출) == 2 and "[적용 실패 1/3]" in 호출[1] and "실제 글" in 호출[1] and "return 2" in 호출[1],
       "되묻는 프롬프트에 **그 파일의 실제 글**과 실패 이유가 든다")
    I.버림(d)

    호출.clear()

    def _고약_잡답(prompt):            # 첫 답 없는 글 -> 되물으니 잡담 -> 또 되물으니 맞는 패치
        호출.append(prompt)
        if len(호출) == 1:
            return json.dumps({"꼴": "패치", "왜": "틀림", "편집": [{"path": "mod.py", "old": "def 없는함수():\n    return 0\n", "new": "x\n"}]})
        if len(호출) == 2:
            return "네, 알겠습니다. 다시 살펴보겠습니다."
        return json.dumps({"꼴": "패치", "왜": "맞음", "편집": [{"path": "mod.py", "old": "    return 2\n", "new": "    return 1\n"}]})
    I.제안기 = _고약_잡답
    r = I.사용자개선("f 가 1", d, 초=30)
    ok(r["판정"] == "동의대기" and r.get("적용시도") == 2 and len(호출) == 3,
       f"**잡답도 예산 안에서 다시 청한다** (판정 {r['판정']} · 시도 {r.get('적용시도')} · 호출 {len(호출)})")
    ok("어디에도 없다" in 호출[1] and "새파일" in 호출[1] and "def f():" in 호출[1],
       "**없는 글이면 파일 전체를 주고 '새파일로 지어라' 고 말한다**")
    ok("[답이 JSON 꼴이 아니었다]" in 호출[2], "잡답 뒤에는 JSON 만 달라고 못박는다")
    되묻기줄 = [x for x in I.원장읽기(d) if x.get("꼴") == "되묻기"]
    ok(len(되묻기줄) >= 2 and 되묻기줄[-2]["패치꼴"] is False and "알겠습니다" in 되묻기줄[-2]["답머리"] and 되묻기줄[-1]["패치꼴"] is True,
       "**모델이 무엇이라 답했는지 원장에 남는다** -- 다음엔 추측 없이 본다")
    I.버림(d)

    호출.clear()
    I.제안기 = lambda prompt: (호출.append(prompt) or json.dumps({"꼴": "패치", "왜": "x", "편집": [{"path": "mod.py", "old": "    return 99\n", "new": "x\n"}]}))
    r = I.사용자개선("f 가 1", d, 초=30)
    ok(r["판정"] == "조사로" and r.get("적용시도") == 3 and "3번" in r["말"] and P.현재판(d) is None,
       f"끝까지 안 맞으면 **몇 번 청했는지** 말하고 판을 닫고 **긴 호흡으로 넘긴다** ({r['말'][:60]})")

    print("\n== '사람' 이라 물러나면 코드가 사람 몫인지 가른다 (프롬프트로 설득하지 않는다) ==")
    I.제안기 = lambda prompt: json.dumps({"꼴": "사람", "사람이_할_것": "무거운 라이브러리가 필요하고 정책이 걱정돼 사람이 정해야 합니다"}, ensure_ascii=False)
    r = I.사용자개선("md 를 pdf 로", d, 초=30)
    ok(r["판정"] == "조사로" and "사람 몫이 아니다" in r["말"], f"**걱정·무게는 사람 몫이 아니다 -> 조사로** ({r['판정']})")
    I.제안기 = lambda prompt: json.dumps({"꼴": "사람", "사람이_할_것": "GEMINI_API_KEY 를 !열쇠 로 넣어 주세요"}, ensure_ascii=False)
    r = I.사용자개선("키가 필요한 일", d, 초=30)
    ok(r["판정"] == "제안없음" and "열쇠" in r["말"], f"**열쇠·승인은 사람 몫 -> 그대로 사람에게** ({r['판정']})")
    ok(I.사람몫인가("계정을 만들어 주세요") and not I.사람몫인가("라이브러리가 무겁습니다"), "가르는 규칙")
    ok((d / "mod.py").read_text(encoding="utf-8") == "def f():\n    return 2\n", "실제 트리는 한 번도 안 건드렸다")

    print("\n== 해석: 펜스·말·뒤따르는 중괄호에도 JSON 을 뽑는다 ==")
    ok(I.해석('설명.\n```json\n{"꼴": "사람", "사람이_할_것": "키"}\n```\n끝 {x}') == {"꼴": "사람", "사람이_할_것": "키"},
       "펜스와 앞뒤 말을 벗긴다")
    ok(I.해석('{"꼴": "패치", "왜": "x", "편집": [{"path": "a", "old": "b", "new": "c"}]} 뒤에 {"딴것": 1}') is not None,
       "**탐욕 정규식이 삼키던 꼴**도 첫 온전한 사전을 뽑는다")
    ok(I.해석("그냥 말") is None and I.해석('{"꼴": "패치"}') is None, "꼴이 안 맞으면 None")
    # 다음 대목은 '옳은 old' 제안기를 전제한다 -- 고약한 것을 되돌린다.
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "부탁대로 고침", "근거": ["arxiv#1"],
                                      "편집": [{"path": "mod.py", "old": "return 2", "new": "return 1"}]}, ensure_ascii=False)

    print("\n== 멀리서 깨뜨리면 거절한다 ==")
    (d / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8"); git(d, "commit", "-qam", "again")
    P.리허설기 = lambda repo, 판, 초, 전부=False, 전부초=1800: {
        "판": str(판), "그림자": True, "바뀐것": ["mod.py"], "걸음": [("레포 전체(회귀)", 1, "새로 깨짐 ['test_far.py']")],
        "통과": False, "못잼": [], "걸린초": 1.0, "회귀": {"새로깨짐": ["test_far.py"], "고쳐짐": [], "그대로빨강": []}}
    # 같은 패치를 되풀이해도 같은 빨강 -> 두 번 더 청한 뒤 **조사로** (사람에게가 아니다)
    r = I.사용자개선("뭔가 고쳐줘", d, 초=30)
    ok(r["판정"] == "조사로" and r.get("시뮬시도") == 3 and P.현재판(d) is None,
       f"**레포 전체에서 새로 깨지면 붙이지 않는다** -- 두 번 더 청하고 그래도면 조사로 ({r['판정']} · 시뮬 {r.get('시뮬시도')})")
    ok(r["회귀"]["새로깨짐"] == ["test_far.py"] and "test_far.py" in I.부탁보고(r), "무엇이 깨졌는지 사람에게 말한다")

    print("\n== 시뮬이 빨가면 꼬리를 들려 다시 청한다 -- 둘째에 초록이면 붙는다 ==")
    # 실측 2026-09-12(VM): 새 파일 둘을 붙였는데 지은 검사가 빨갛게 나와 거기서 버렸다.
    (d / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8"); git(d, "commit", "-qam", "again2")
    시험횟수 = {"n": 0}
    받은2 = []

    def 리허설_처음빨강(repo, 판, 초, 전부=False, 전부초=1800):
        시험횟수["n"] += 1
        빨 = 시험횟수["n"] == 1
        return {"판": str(판), "그림자": True, "바뀐것": ["mod.py"], "걸음": [("레포 전체(회귀)", 1 if 빨 else 0, "새로 깨짐 ['test_far.py']" if 빨 else "없음")],
                "통과": not 빨, "못잼": [], "걸린초": 1.0, "회귀": {"새로깨짐": ["test_far.py"] if 빨 else [], "고쳐짐": [], "그대로빨강": []}}
    P.리허설기 = 리허설_처음빨강
    I.제안기 = lambda prompt: (받은2.append(prompt) or json.dumps({"꼴": "패치", "왜": "x", "편집": [{"path": "mod.py", "old": "return 2", "new": "return 1"}]}))
    r = I.사용자개선("고쳐줘", d, 초=30)
    ok(r["판정"] == "동의대기" and r.get("시뮬시도") == 2, f"**빨강 -> 되묻기 -> 초록이면 동의대기** ({r['판정']} · 시뮬 {r.get('시뮬시도')})")
    ok(len(받은2) == 2 and "[시뮬 판정 1/2]" in 받은2[1] and "test_far.py" in 받은2[1],
       "되묻는 프롬프트에 **무엇이 깨졌는지**가 든다")
    I.버림(d)
    P.리허설기 = 리허설_회귀없음
    ok(I.사용자개선("", d)["판정"] == "빈부탁", "빈 부탁은 안 받는다")
    P.리허설기 = 초록리허설

    print("\n== 틈이 없으면 멈추지 않는다: 제2의 뇌로 성능 개선거리 ==")
    I.틈모으기_ = lambda repo: []                      # 고칠 틈 없음
    P.리허설기 = 리허설_회귀없음
    본참 = {"프롬프트": ""}

    def 고르기_가짜(prompt):
        본참["프롬프트"] = prompt
        return json.dumps({"꼴": "부탁", "부탁": "mod.f 가 1을 돌려주게 하라", "왜": "최신 방법 적용",
                         "근거": ["arxiv:2501.9#aa"]}, ensure_ascii=False)
    I.고르기기 = 고르기_가짜
    I.넓히기_ = lambda 질의들, repo: None
    from graph import ask as _ask
    _원래찾기 = _ask.찾기
    _ask.찾기 = lambda 물음, repo=None, 최대=5: [(9, {"출처": "dig/corpus/x.md", "해시": "aa", "요약": "새 방법 A"})]
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "적용", "근거": ["arxiv:2501.9#aa"],
                                      "편집": [{"path": "mod.py", "old": "return 2", "new": "return 1"}]}, ensure_ascii=False)
    try:
        r = I.자가개선(d, 몇=3)
        ok(r["성능"] and r["동의대기"] is not None and r["동의대기"]["판정"] == "동의대기",
           f"**틈 0 -> 성능 개선거리로 넘어가 동의 대기** ({r.get('성능')}, {(r['동의대기'] or {}).get('판정')})")
        ok(r["동의대기"].get("성능거리") and r["동의대기"]["부탁"] == "mod.f 가 1을 돌려주게 하라",
           "제2의 뇌가 고른 것이 부탁이 된다")
        ok("저장소 얼개" in 본참["프롬프트"] and "dig/corpus/x.md #aa" in 본참["프롬프트"],
           "고르기 프롬프트에 저장소 얼개와 모은 참고가 들어간다")
        ok("성능 개선거리" in I.보고(r), "보고가 성능 길로 갔다고 말한다")
        꼴들2 = [x.get("꼴") for x in I.원장읽기(d)]
        ok("성능고르기" in 꼴들2, "원장에 성능고르기가 남는다")
        # 승인 결과를 **본다**. 실측: 거절이 조용히 지나가 판이 열린 채 다음 대목이 "판열림" 으로 죽었다.
        _승 = I.승인(d, 누가="검사")
        ok("적용됨" in _승, f"성능 개선거리도 승인으로 붙는다 ({_승[:80]})")
        git(d, "commit", "-qam", "성능 반영")

        print("\n== 근거가 없으면 정직히 멈춘다 ==")
        (d / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8"); git(d, "commit", "-qam", "again")
        _ask.찾기 = lambda 물음, repo=None, 최대=5: []
        r = I.자가개선(d, 몇=1)
        ok(r["동의대기"] is None and "참고가 없다" in r["해본"][0]["말"],
           f"**뇌가 비면 '수집이 먼저다' 라고 말한다** ({r['해본'][0]['판정']})")
        _ask.찾기 = lambda 물음, repo=None, 최대=5: [(9, {"출처": "s", "해시": "b", "요약": "x"})]
        I.고르기기 = lambda prompt: json.dumps({"꼴": "없음", "왜": "적용할 만한 것이 없다"}, ensure_ascii=False)
        r = I.자가개선(d, 몇=1)
        ok(r["해본"][0]["판정"] == "고를것없음", "고를 것이 없으면 그렇다고 한다")
    finally:
        _ask.찾기 = _원래찾기
        I.고르기기 = None

    print("\n== 후보 상한 5 ==")
    I.틈모으기_ = lambda repo: [dict(틈, 무엇=f"t{i}") for i in range(8)]
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "x", "편집": [{"path": "mod.py", "old": "return 2", "new": "return 3"}]})
    r = I.자가개선(d, 몇=99)
    ok(len(r["해본"]) == 5 and r["틈수"] == 8, f"**몇=99 줘도 후보 5개까지** ({len(r['해본'])})")
    ok("5개 후보" in r["남은것"], "다 실패하면 그렇다고 말한다")
finally:
    I.제안기 = I.틈모으기_ = I.넓히기_ = I.고르기기 = None
    I.모델막힘 = False
    Rs.분해기 = None
    P.리허설기 = None
    s = P.읽기(d)
    if s:
        P._끄기(d, s)
    shutil.rmtree(d, ignore_errors=True)

print("\n== 배선 ==")
import dispatch  # noqa: E402
ok("동의" in (dispatch.run("!자가개선", allow_write=True) or "") or "자가개선" in (dispatch.run("!자가개선 도움", allow_write=True) or ""), "!자가개선 도움말")
ok("관리 채널" in (dispatch.run("!자가개선 승인", allow_write=False) or ""), "공개 채널에서 승인 못 한다")
ok(dispatch.run("!개선 상태", allow_write=True) == dispatch.run("!자가개선 상태", allow_write=True) is not None,
   "**`!개선` 도 같은 명령이다**(사용자가 실제로 친 것)")
ok(dispatch.run("!개선기 x") is None and dispatch.run("!자가개선기 x") is None, "붙여 쓴 꼴은 명령이 아니다")
ok(dispatch.고르기("개선해줘")[0] == "!자가개선", "자연어 '개선해줘' 도 간다")
불림2 = []
dispatch.run("!개선 답변을 더 빠르게 해줘", runner=lambda argv, 로그, 무엇: (불림2.append(argv) or "시작"), allow_write=True)
ok(불림2 and 불림2[0][:3] == ["python3", "improve/run.py", "--부탁"] and 불림2[0][3] == "답변을 더 빠르게 해줘",
   f"**`!개선 <말>` 이 그 말을 그대로 부탁으로 넘긴다** ({불림2})")
_run = (뿌리 / "improve" / "run.py").read_text(encoding="utf-8")
ok("def 사용자개선" in _run and "전부: bool = True" in _run, "부탁은 기본이 레포 전체 시뮬이다")
# 실측 2026-09-12(VM): pdf 변환 부탁에 모델이 "무거운 라이브러리·정책" 을 이유로 '사람' 이라며 물러났다.
# 규칙이 '좁게' 만 말하고 새 기능의 길을 안 열어 줬기 때문이다.
_pp = I.부탁프롬프트("md 를 pdf 로", 뿌리, {"참고": [], "확장": 0}, [])
ok("새 모듈" in _pp and "requirements.txt 한 줄" in _pp, "새 기능의 길(새 모듈·검사·의존성 한 줄)은 사실로 한 줄만 적는다")
ok("하지 마라" not in _pp.split("사람만 가진 값")[-1][:200], "**설득 문구는 없다** -- 회피는 코드(사람몫인가)가 가른다")
_bot3 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok('"판정: **조사로**" in _출' in _bot3 and '"--목표"' in _bot3, "**봇이 '조사로' 를 보면 목표 모드 조사를 코드로 띄운다**")
ok("def 성능개선" in _run and "def 부탁고르기" in _run, "틈이 없을 때 가는 길이 있다")
ok('if str(REPO) not in sys.path' in _run, "**스크립트로 돌 때 뿌리를 넣는다**(ModuleNotFoundError 사고)")
ok(not dispatch.도구로쳐도되나("!자가개선 승인")[0], "**봇은 dispatch_command 로 승인을 못 친다**")
ok(dispatch.고르기("스스로 개선할 점 찾아봐")[0] == "!자가개선" and dispatch.고르기("자가개선 점검")[0] == "!자가개선 점검", "자연어 -> !자가개선")
불림 = []
dispatch.run("!자가개선", runner=lambda argv, 로그, 무엇: (불림.append(argv) or "시작"), allow_write=True)
ok(불림 and 불림[0][:2] == ["python3", "improve/run.py"], f"배경으로 돈다 ({불림})")
_서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
ok("async def _자가개선지켜보기" in _서버 and "asyncio.create_task(_자가개선지켜보기())" in _서버 and "IMPROVE_SEC" in _서버,
   "**봇이 6h 마다 스스로 돌아 동의를 구한다**")
ok("!자가개선" in _서버 and "승인` 은 사람만" in _서버, "프롬프트가 !자가개선 을 이름을 대고 '승인은 사람만' 을 적는다")
_wf = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('"improve/**.py"' in _wf, "improve 가 배포 경로에")
ok("improve/ledger.jsonl merge=union" in (뿌리 / ".gitattributes").read_text(encoding="utf-8"), "원장은 union")
p = subprocess.run(["python3", "improve/run.py", "--틈만"], cwd=str(뿌리), capture_output=True, text=True, timeout=120)
ok(p.returncode == 0 and "틈" in p.stdout, f"--틈만 CLI 가 돈다 ({p.stdout.strip().splitlines()[-1][:40] if p.stdout.strip() else ''})")

print("\n== 파일 고르기: git 이 아는 것만 · 명령 꾸러미 · 조사 떼기 ==")
# 실측 2026-09-12(VM): `!개선 수집망 url에 인스타그램, x, meta 추가해줘` 가 고른 파일이
# `.venv-torch/lib/python3.12/site-packages/torch/_meta_registrations.py` 였다 -- 건너뛸 곳을 손으로
# 적어 두었는데 `.venv-torch` 는 그 중 어느 이름도 아니었다. 남의 코드를 발췌로 받으면 못 고친다.
import subprocess as _sp2
_d3 = Path(tempfile.mkdtemp(prefix="improve-고르기-"))
try:
    _g = lambda *a: _sp2.run(["git", "-C", str(_d3), *a], capture_output=True, text=True)  # noqa: E731
    _g("init", "-q"); _g("config", "user.email", "t@t"); _g("config", "user.name", "t")
    (_d3 / ".gitignore").write_text(".venv*\n", encoding="utf-8")
    (_d3 / "dig").mkdir(); (_d3 / "dig" / "__init__.py").write_text("", encoding="utf-8")
    (_d3 / "dig" / "search.py").write_text("틀들 = ('https://x/?q={q}',)  # url 목록\n" * 3, encoding="utf-8")
    (_d3 / ".venv-torch" / "lib" / "site-packages" / "torch").mkdir(parents=True)
    (_d3 / ".venv-torch" / "lib" / "site-packages" / "torch" / "_meta_registrations.py").write_text(
        "# meta url url url\n" * 50, encoding="utf-8")
    _g("add", "-A"); _g("commit", "-qm", "init")
    났 = I.저장소파이썬(_d3)
    ok("dig/search.py" in 났 and not any(".venv" in x for x in 났),
       f"**git 이 추적하는 것만** -- 무시된 .venv-torch 는 없다 ({[x for x in 났 if chr(46)+chr(118) in x]})")
    고른 = I._관련파일찾기("수집망 url에 meta 추가해줘", _d3)
    ok(고른 and all(not x.startswith(".venv") for x in 고른), f"고른 파일에 남의 코드가 없다 ({고른})")
    ok("dig/__init__.py" not in 고른, f"빈 꾸러미 표지는 안 고른다 ({고른})")
finally:
    shutil.rmtree(_d3, ignore_errors=True)

ok("url" in I._낱말뽑기("수집망 url에 meta 추가해줘") and "pdf" in I._낱말뽑기("md가 안보이니 pdf로"),
   "**한글 조사가 붙은 라틴 낱말을 떼어 낸다** (`url에` -> `url` · `pdf로` -> `pdf`)")
ok("dig" in I._부탁의모듈("수집망 고쳐줘") and "novel" in I._부탁의모듈("소설 문체"),
   "고정 명령 이름(`!수집` · `!소설`)으로 그 꾸러미를 찾는다 -- dispatch 에 묻는다(목록 없음)")
ok(I._부탁의모듈("아무 말도 아니다") == [], "아무 명령도 안 가리키면 빈 목록")

print("\n== 패치 꼴이 아닌 답도 한 번 더 청하고, 그래도 아니면 긴 호흡으로 ==")
# 실측 2026-09-12(VM): 첫 답이 패치 꼴이 아니어서 그 자리에서 끝났다(판정: 제안없음).
# 적용 실패와 시뮬 빨강은 이미 되풀이하는데 이 자리만 한 번에 포기했다.
호출2 = []


def _둘째에패치(prompt):
    호출2.append(prompt)
    if len(호출2) == 1:
        return "알겠습니다. 아래와 같이 고치면 좋겠습니다만 JSON 은 아닙니다."
    return json.dumps({"꼴": "패치", "왜": "둘째에 꼴을 맞췄다", "편집": [{"path": "mod.py", "old": "return 2", "new": "return 1"}]}, ensure_ascii=False)


with tempfile.TemporaryDirectory() as _d4:
    d4 = Path(_d4)
    git(d4, "init", "-q"); git(d4, "config", "user.email", "t@t"); git(d4, "config", "user.name", "t")
    (d4 / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8")
    git(d4, "add", "-A"); git(d4, "commit", "-qm", "init")
    P.리허설기 = 리허설_회귀없음
    I.제안기 = _둘째에패치
    r = I.사용자개선("f 가 1", d4, 초=30)
    ok(r["판정"] == "동의대기" and r.get("제안시도") == 2 and len(호출2) == 2,
       f"**꼴이 아니면 다시 청해서 둘째에 간다** (판정 {r['판정']} · 시도 {r.get('제안시도')})")
    ok("JSON 하나만" in 호출2[1] and "알겠습니다" in 호출2[1],
       "되묻는 프롬프트에 **꼴을 못박고 앞 답이 무엇이었는지** 보여 준다")
    I.버림(d4)
    I.제안기 = lambda prompt: "끝까지 JSON 이 아닌 말"
    r = I.사용자개선("f 가 1", d4, 초=30)
    ok(r["판정"] == "조사로" and "두 번 청해도" in r["말"],
       f"**두 번 청해도 아니면 긴 호흡으로 넘긴다** -- 사람 몫이 아니다 (판정 {r['판정']})")

print("\n== 초록의 뜻: 코드는 바뀌었는데 그 변경 없이도 초록인 검사뿐이면 공허 -- 빨강과 같이 다룬다 ==")
# 사용자(2026-09-12): "구조가 좋으면 모델의 성능을 이길 수 있다." 오늘 초록으로 지나간 것 셋(#194 함수만 정의한
# 검사 · #201 글자 검사 · 구글 문 셋)이 전부 여기서 걸린다. 판정은 rehearsal.공허검사 -- 모델이 아니다.
I.공허검사기 = None                    # 진짜 판정
호출3 = []


def _처음은공허(prompt):
    호출3.append(prompt)
    if len(호출3) == 1:                 # 코드만 바꾸고 검사는 assert True -- #201 꼴
        return json.dumps({"꼴": "패치", "왜": "공허", "편집": [{"path": "mod.py", "old": "return 2", "new": "return 1"}],
                           "새파일": [{"path": "tests/test_공허.py", "내용": "assert True\n"}]}, ensure_ascii=False)
    return json.dumps({"꼴": "패치", "왜": "증인", "편집": [{"path": "mod.py", "old": "return 2", "new": "return 1"}],
                       "새파일": [{"path": "tests/test_공허.py", "내용": "import sys; sys.path.insert(0, '.')\nimport mod\nassert mod.f() == 1\n"}]}, ensure_ascii=False)


with tempfile.TemporaryDirectory() as _d5:
    d5 = Path(_d5)
    git(d5, "init", "-q"); git(d5, "config", "user.email", "t@t"); git(d5, "config", "user.name", "t")
    (d5 / "mod.py").write_text("def f():\n    return 2\n", encoding="utf-8"); (d5 / "tests").mkdir()
    git(d5, "add", "-A"); git(d5, "commit", "-qm", "init")
    P.리허설기 = 리허설_회귀없음
    I.제안기 = _처음은공허
    r = I.사용자개선("f 가 1", d5, 초=30)
    ok(r["판정"] == "동의대기" and r.get("시뮬시도") == 2 and len(호출3) == 2,
       f"**공허한 초록은 막고 되물어, 증인 검사가 오면 동의대기** (판정 {r['판정']} · 시뮬시도 {r.get('시뮬시도')})")
    ok("공허" in 호출3[1] and "코드 변경 없이도" in 호출3[1], "되묻는 프롬프트에 왜 공허한지가 든다")
    ok(any(x.get("꼴") == "공허" for x in I.원장읽기(d5)), "원장에 공허 판정이 남는다")
    I.버림(d5)
    I.제안기 = lambda prompt: json.dumps({"꼴": "패치", "왜": "검사 없음", "편집": [{"path": "mod.py", "old": "return 2", "new": "return 1"}]}, ensure_ascii=False)
    r = I.사용자개선("f 가 1", d5, 초=30)
    ok(r["판정"] == "조사로" and "재는 검사가 없다" in r["말"],
       f"**검사 없는 코드 변경은 끝까지 안 받고 조사로 넘긴다** -- 구글 문 셋이 지나간 자리 (판정 {r['판정']})")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("improve: 근거·확장 · 시뮬·동의대기 · 승인 · 버림 · 거절 · 리허설 · 상한 · 배선 -- 통과")
