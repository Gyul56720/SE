"""eval/acceptance -- **이 에이전트가 정말 완성됐는가**를 재는 심화 인수 검사. 판정은 코드가 한다.

단위 검사(tests/)는 기관 하나씩을 붙든다. 이것은 **사용자가 겪은 장면**을 그대로 재연해 기관들이
같이 도는지를 본다 -- 떠넘김을 잡는가, 목표를 추상 질의로 풀어 끝까지 가는가, 고치기 전에 diff 를
보이고 사람이 승인하는가, 게이트가 스스로 고치는가, 틀린 수학을 거절하는가, 자가 튼튼한가 …

표기: [실측] 진짜 기관·sandbox·git 이 돈다 / [가짜] 망·LLM 만 가짜(판정은 그대로 코드).
못 잰 것은 못 쟀다고 적는다 -- 이 저장소 규율: 검사하지 않은 초록불이 검사한 빨간불보다 나쁘다.

    python3 eval/acceptance.py            # 표 + 요약. 끝값 0 전부 통과 · 1 실패 있음
    python3 eval/acceptance.py --json
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace as NS

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

장면들: list = []


def 장면(이름: str, 꼴: str):
    def deco(f):
        장면들.append((이름, 꼴, f))
        return f
    return deco


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=False)


def _임시git(prefix="acc-"):
    d = Path(tempfile.mkdtemp(prefix=prefix))
    _git(d, "init", "-q")
    return d


os.environ.setdefault("GIT_AUTHOR_NAME", "acc"); os.environ.setdefault("GIT_AUTHOR_EMAIL", "acc@x")
os.environ.setdefault("GIT_COMMITTER_NAME", "acc"); os.environ.setdefault("GIT_COMMITTER_EMAIL", "acc@x")


# ---------------------------------------------------------------- 1. 사용자가 본 떠넘김을 코드가 잡는가
실측떠넘김 = [
    # 2026-09-11 RIS 주제 -- 소개만 하고 끝냄
    "RIS 기반 RL 최적화 주제를 관심 주제에 반영했습니다. 논문을 읽고 코드화하는 작업이 필요하면 말씀해 주세요.",
    # 2026-09-11 네이버 예약 1 -- 수동 절차를 안내하고 끝냄
    "가장 확실하고 빠른 해결 방법: 네이버 지도 앱을 엽니다. 업체 정보 하단의 [예약] 버튼을 누릅니다. "
    "원하시는 날짜와 시간을 선택하여 직접 예약해 주시길 부탁드립니다.",
    # 2026-09-11 네이버 예약 2 -- 값싼 도구 몇 개 뒤 '유일한 방법' 으로 떠넘김
    "제2의 뇌와 오픈소스 저장소를 탐색한 결과 외부 자동화 봇으로는 우회가 불가능합니다. "
    "따라서 사용자가 직접 네이버 지도 앱을 통해 예약하는 것이 유일하고 안전한 방법입니다.",
]
실행한답 = [
    "sandbox 에서 돌려 통과했다. 결과는 13.86 -- 원장 줄: eval/ledger.jsonl 에 적혔다.",
    "직접 돌려 봤더니 끝값 0 이었고, codify/out/ou.py 가 저장됐다.",
]


@장면("떠넘김 감지: 사용자가 실제로 본 세 답을 잡고, 실행한 답은 안 잡는다", "실측")
def _s1():
    import relay
    놓침 = [t[:30] for t in 실측떠넘김 if not relay.떠넘김(t)]
    오판 = [t[:30] for t in 실행한답 if relay.떠넘김(t)]
    assert not 놓침, f"못 잡은 떠넘김: {놓침}"
    assert not 오판, f"실행한 답을 떠넘김으로 오판: {오판}"
    relay.마지막도구["acc-cheap"] = ["search_memory", "read_file"]
    assert not relay.무거운일("acc-cheap", [("python3 graph/ask.py RIS", True)]), "값싼 도구만이면 무거운 일이 아니다"
    assert relay.무거운일("acc-cheap", [("python3 dig/paper.py --url x", True)]), "논문 읽기는 무거운 일"
    relay.마지막도구["acc-heavy"] = ["research"]
    assert relay.무거운일("acc-heavy"), "research 도구는 무거운 일"
    return f"떠넘김 {len(실측떠넘김)}/{len(실측떠넘김)} 잡음 · 실행답 오판 0 · 무거운일 판정 3/3"


# ---------------------------------------------------------------- 2. 목표 -> 추상 질의 -> 막힘 재시도 -> 코드화 -> 결론
@장면("연구 loop: 구체 목표를 추상화, 막히면 재추상화, 모이면 코드화·결론 메모", "가짜")
def _s2():
    from research import run as Rs
    from dig import harvest as H
    from codify import run as C
    d = Path(tempfile.mkdtemp(prefix="acc-rs-"))
    n = {"k": 0}
    원래 = (H.한바퀴, Rs._이번논문, C.논문코드화, Rs.분해기, Rs.종합기)
    try:
        def 한바퀴(말들, repo=None, 몇=3, 상한=8, 출처=()):
            n["k"] += 1
            base = {"돌았나": True, "저장": 0, "받음": 0, "거절": [], "적은것": [], "걸린초": 0.1}
            return {**base, "색인": 0, "막힘": {"arxiv": "403"}} if n["k"] == 1 else {**base, "색인": 2, "막힘": {}}
        H.한바퀴 = 한바퀴
        Rs._이번논문 = lambda repo, 질의들: ["https://arxiv.org/abs/2501.1"] if n["k"] >= 2 else []
        C.논문코드화 = lambda url, repo=None: {"논문": "2501.1", "제목": "General Method", "스펙수": 1, "성공": 1,
                                           "결과들": [{"파일": "codify/out/g.py", "성공": True}], "못읽음": []}
        Rs.분해기 = lambda 목표, 막힌것: ("browser automation survey\nform filling agents" if 막힌것
                                     else "naver booking automation playwright\nreservation bot")
        Rs.종합기 = lambda 목표, 요약: "과정: 구체 질의 0건 -> 추상화 재수집 2건 -> 코드화 1. 결과: 일반 방법론으로 접근."
        r = Rs.연구("똑닥헤어 수락점 네이버 예약 자동화", repo=d, 바퀴=3)
        assert r["충분"] and r["바퀴수"] == 2, f"2바퀴에 충분해야 한다: {r['바퀴수']}, {r['충분']}"
        assert r["바퀴들"][0]["질의들"] != r["바퀴들"][1]["질의들"], "막힌 뒤 질의가 바뀌어야 한다"
        본 = (d / r["메모"]).read_text(encoding="utf-8")
        assert "## 결론 (과정 -> 결과)" in 본 and "codify/out/g.py" in 본, "메모에 결론·코드 파일"
        return f"{r['바퀴수']}바퀴 · 질의 바뀜 · 코드화 1 · 메모 {r['메모'].split('/')[-1][:30]}"
    finally:
        H.한바퀴, Rs._이번논문, C.논문코드화, Rs.분해기, Rs.종합기 = 원래
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------- 3. 계획 승인: diff 먼저, 사람이 승인
@장면("계획 승인: 편집은 그림자에만, 승인해야 실제 트리, 충돌은 코드가 거절", "실측")
def _s3():
    from plan import store as P
    import filetools
    d = _임시git("acc-plan-")
    try:
        (d / "a.txt").write_text("hello\n", encoding="utf-8"); _git(d, "add", "-A"); _git(d, "commit", "-qm", "i")
        P.켜기("a", repo=d); 판 = P.현재판(d)
        filetools.편집("a.txt", "hello", "bye", repo=판)
        assert (d / "a.txt").read_text() == "hello\n", "실제 트리가 승인 전에 바뀌었다"
        assert "+bye" in P.보기(d), "diff 가 계획으로 보여야 한다"
        assert "아직 안 돌려 봤다" in P.승인(d), "돌려 보지 않은 diff 는 승인이 거절해야 한다"
        P.리허설기 = lambda repo, 판, 초: {"판": str(판), "그림자": True, "바뀐것": [], "걸음": [], "통과": True, "못잼": [], "걸린초": 0.0}
        P.시험하기(d)
        assert "적용됨" in P.승인(d) and (d / "a.txt").read_text() == "bye\n", "리허설 초록 뒤에는 붙어야 한다"
        _git(d, "commit", "-qm", "ok")
        P.켜기("b", repo=d); filetools.편집("a.txt", "bye", "ciao", repo=P.현재판(d))
        P.시험하기(d)
        (d / "a.txt").write_text("hola\n", encoding="utf-8")
        assert "적용 실패" in P.승인(d), "충돌이면 코드가 거절해야 한다"
        P.버림(d)
        return "그림자 편집 · diff · **리허설 전제** · 승인 적용 · 충돌 거절 · 버림"
    finally:
        P.리허설기 = None
        s = P.읽기(d)
        if s:
            P._끄기(d, s)
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------- 4. 게이트가 스스로 고친다
@장면("게이트 자동 고치기: 이스케이프 위반을 fix 가 고쳐 check 가 빈다 (gitignore 는 안 본다)", "실측")
def _s4():
    import importlib
    import gatekeeper
    d = _임시git("acc-gate-")
    try:
        (d / ".gitignore").write_text("out/\n"); (d / "out").mkdir(); (d / "out" / "g.py").write_text('"""\\int"""\n')
        (d / "m.py").write_text('"""\\lambda"""\n')
        G017 = importlib.import_module("gates." + [m for m in os.listdir(REPO / "gates") if m.startswith("G017")][0][:-3])
        ctx = gatekeeper.GateContext(d)
        assert len(G017.check(ctx)) == 1, "m.py 만 걸려야 한다(out/ 은 gitignore)"
        고침 = G017.fix(ctx)
        assert 고침 and G017.check(gatekeeper.GateContext(d)) == [], f"fix 뒤 check 가 비어야 한다 ({고침})"
        return f"위반 1 -> 고침 {고침} -> 위반 0"
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------- 5. 틀린 수학은 sandbox 가 거절한다
@장면("코드화 검증: 틀린 함수(1/θ)는 실패, 맞는 함수(ln2/θ)만 통과 -- 판정은 sandbox 끝값", "실측")
def _s5():
    from codify import run as C
    d = Path(tempfile.mkdtemp(prefix="acc-cod-"))
    열 = ["```python\ndef 반감기(theta):\n    return 1 / theta\n```",
         "```python\nimport math\ndef 반감기(theta):\n    return math.log(2) / theta\n```"]
    C.코드공 = lambda p: 열.pop(0)
    try:
        r = C.코드화({"종류": "수식", "이름": "ou", "원문": "t=ln2/theta", "출처": "acc",
                   "예시": [{"부른다": "반감기", "입력": {"theta": 0.05}, "답": 13.8629, "허용": 0.01}]}, repo=d, 바퀴=3)
        판 = [h["판정"] for h in r["해본것"]]
        assert 판 == ["실패", "통과"] and r["성공"] and not r["약한검증"], f"기대 [실패, 통과], 실제 {판}"
        return f"바퀴 판정 {판} · 예시 값 검증"
    finally:
        C.코드공 = None
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------- 6. 자(절대 기준)가 서 있다
@장면("자(eval/tasks): 과제 20개 이상이 검사를 통과하고, 판정이 실제로 sandbox 에서 돈다", "실측")
def _s6():
    from eval import tasks as T
    과제들, 오류 = T.과제읽기()
    assert not 오류, f"과제 파일 오류: {오류[:3]}"
    assert len(과제들) >= 20, f"과제 {len(과제들)}개 -- 20 미만"
    갈래 = {t.get("과제갈래") for t in 과제들}
    assert {"코드", "추론", "지식"} <= 갈래, f"갈래가 빠졌다: {갈래}"
    ok, 꼬리 = T.실행판정("def f():\n    return 42\n", "import 답\nassert 답.f() == 42\nprint('ok')\n")
    assert ok, f"sandbox 판정이 안 돈다: {꼬리[-120:]}"
    bad, _ = T.실행판정("def f():\n    return 1\n", "import 답\nassert 답.f() == 42\n")
    assert not bad, "틀린 코드가 통과했다"
    return f"과제 {len(과제들)} · 갈래 {sorted(갈래)} · sandbox 맞음/틀림 판정"


# ---------------------------------------------------------------- 7. 관심을 주면 그 자리에서 모은다
@장면("수집 --관심: 등록만이 아니라 즉시 한 바퀴 수집·색인한다", "가짜")
def _s7():
    from dig import harvest as H
    from dig import paper as PP
    d = Path(tempfile.mkdtemp(prefix="acc-hv-"))
    원래 = (H.arxiv검색, PP.논문받기, H.깃허브찾기, H.허깅찾기)
    try:
        H.arxiv검색 = lambda 말, 몇: [{"id": "2501.9", "제목": "Broad Method", "url": "https://arxiv.org/abs/2501.9"}]
        PP.논문받기 = lambda url, 문들=("html",): {"id": "2501.9", "제목": "Broad Method", "url": url, "초록": "a",
                                               "수식": ["x=y"], "알고리즘": [], "그림": [], "표": [], "본문": "b",
                                               "된문": ["html"], "못읽음": []}
        H.깃허브찾기 = lambda *a, **k: []
        H.허깅찾기 = lambda *a, **k: []
        added, r = H.관심수집("reservation scheduling optimization", repo=d)
        assert added == "더했다" and r["색인"] >= 1, f"즉시 수집이 안 됐다: {added}, 색인 {r['색인']}"
        return f"{added} · 색인 {r['색인']} (한 호출)"
    finally:
        H.arxiv검색, PP.논문받기, H.깃허브찾기, H.허깅찾기 = 원래
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------- 8. 자가 수리 loop 가 실제로 고친다
@장면("자가 수리: 실측 실패 -> 제안(명령) -> 격리 시도 -> 재현 통과 = 해결", "가짜")
def _s8():
    from repair import run as R
    d = _임시git("acc-rep-")
    (d / "README.md").write_text("x\n"); _git(d, "add", "-A"); _git(d, "commit", "-qm", "i")
    원래 = (R.제안기, R.모으기)
    try:
        R.모으기 = lambda *a, **k: ""
        R.제안기 = lambda p: json.dumps({"꼴": "명령", "명령": "touch ok.txt", "왜": "파일이 없어서"})
        r = R.고치기("test -f ok.txt", "ok.txt 없음", repo=d, 바퀴=2, 초=60)
        assert r["해결"], f"해결이어야 한다: {r['남은것']} / {[h.get('판정') for h in r['해본것']]}"
        assert (d / "ok.txt").is_file(), "실제 트리에 고침이 반영돼야 한다"
        return f"바퀴 {r['바퀴']} · 해결 · 메모 {bool(r.get('메모'))}"
    finally:
        R.제안기, R.모으기 = 원래
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------- 9. 메일 안전장치 · 비밀 마스킹
@장면("메일 안전장치: 자리표·흔한 오타 도메인은 코드가 거절 (망 없음)", "실측")
def _s9():
    import mailer
    assert mailer.자리표들("[이름] 님께, [날짜]에") == ["[이름]", "[날짜]"], "자리표를 못 찾는다"
    assert "gamil.com" in mailer.흔한오타, "gamil.com 오타표"
    r = mailer.보내기("dbsurd123@gamil.com", "s", "b")
    assert not r["보냈나"], "오타 주소로 보냈다"
    r2 = mailer.보내기("a@b.com", "s", "[이름] 님께")
    assert not r2["보냈나"], "자리표를 안 채우고 보냈다"
    return "자리표 2 · 오타 거절 · 미채움 거절"


@장면("비밀 마스킹: TOKEN 꼴 값은 출력에서 지워진다", "실측")
def _s10():
    import secret_filter as SF
    os.environ["ACCEPT_TEST_TOKEN"] = "s3cr3t-value-xyz-9981"
    out = SF.redact_secrets("auth s3cr3t-value-xyz-9981 done")
    assert "s3cr3t-value-xyz-9981" not in out, f"값이 그대로 남았다: {out}"
    return "환경 TOKEN 값 마스킹"


# ---------------------------------------------------------------- 11. 맥락 · PR · 보안 · 24h · 승인 경계
@장면("맥락 관리: 긴 대화는 코드가 간추려 메모 + 새 실", "실측")
def _s11():
    import compact
    d = Path(tempfile.mkdtemp(prefix="acc-cmp-"))
    try:
        msgs = []
        for i in range(12):
            msgs += [NS(type="human", content=f"부탁 {i}", tool_calls=[]),
                     NS(type="ai", content="", tool_calls=[{"name": "run_shell", "args": {}, "id": "x"}]),
                     NS(type="tool", content="ok", name="run_shell", tool_calls=None),
                     NS(type="ai", content=f"답 {i}", tool_calls=[])]
        assert compact.간추릴때(msgs), "48줄이면 간추려야 한다"
        상대, 씨 = compact.간추리기("acc", msgs, repo=d)
        assert (d / 상대).is_file() and 씨.startswith("[이어짐]") and compact.씨앗꺼내기("acc") == 씨
        return f"{len(msgs)}줄 -> 메모 + 씨앗"
    finally:
        shutil.rmtree(d, ignore_errors=True)


@장면("GitHub 쓰기 폭: main 에선 PR 을 안 열고 HTTP 도 안 부른다 · merge 함수 없음", "실측")
def _s12():
    import github_write as GW
    d = _임시git("acc-pr-")
    (d / "a").write_text("a"); _git(d, "add", "-A"); _git(d, "commit", "-qm", "i"); _git(d, "checkout", "-qB", "main")
    호출 = []
    원래 = (GW.요청, GW.토큰)
    try:
        GW.요청 = lambda *a: (호출.append(a) or (201, "{}"))
        GW.토큰 = lambda repo=None: "t"
        r = GW.pr만들기("x", "y", repo=d)
        assert not r["됐나"] and "main" in r["왜"] and not 호출
        src = (REPO / "github_write.py").read_text(encoding="utf-8")
        assert "def merge" not in src, "merge 가 생겼다 -- 머지는 사람"
        return "main 거절 · HTTP 0회 · merge 없음"
    finally:
        GW.요청, GW.토큰 = 원래
        shutil.rmtree(d, ignore_errors=True)


@장면("보안 자가점검: 읽기 전용으로 돌고 심각도 셈을 낸다", "실측")
def _s13():
    from secaudit import run as sec
    r = sec.점검하기(뇌=False, 적기=False)
    셈 = r["셈"]
    assert {"높음", "중간", "낮음", "정보", "못잼"} <= set(셈), f"셈 키가 빠졌다: {sorted(셈)}"
    return "셈 " + " ".join(f"{k}{v}" for k, v in 셈.items())


@장면("24시간 루프 배선: 타이머·서비스·harvest.sh(--틈 + codify)·배포 enable", "실측")
def _s14():
    t = REPO / "deploy" / "se-harvest.timer"; s = REPO / "deploy" / "se-harvest.service"; sh = REPO / "scripts" / "harvest.sh"
    assert t.is_file() and s.is_file() and sh.is_file()
    본 = sh.read_text(encoding="utf-8")
    assert "--틈" in 본 and "codify/run.py --논문" in 본
    wf = (REPO / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
    assert "systemctl enable --now se-harvest.timer" in wf
    return "timer · service · --틈+codify · enable --now"


@장면("승인 경계: 목표·계획 승인은 공개 채널에서 안 된다 (승인 주체는 사람)", "실측")
def _s15():
    import dispatch
    a = dispatch.run("!목표 승인 x", allow_write=False) or ""
    b = dispatch.run("!계획 승인", allow_write=False) or ""
    assert "읽기만" in a and "읽기만" in b, f"공개 채널 승인이 막히지 않았다: {a[:40]!r} / {b[:40]!r}"
    return "!목표 승인 · !계획 승인 모두 공개 채널 거절"


@장면("고정 명령 라우팅: 모든 고정 명령이 봇에 잡히고 붙여 쓴 꼴은 안 잡힌다", "실측")
def _s16():
    import dispatch
    from eval import wire
    빠짐 = [c for c in wire.고정명령들 if dispatch.run(c, allow_write=True) is None]
    오잡 = [c for c in wire.고정명령들 if dispatch.run(c + "기 x", allow_write=True) is not None]
    assert not 빠짐 and not 오잡, f"빠짐 {빠짐} 오잡 {오잡}"
    return f"{len(wire.고정명령들)}개 명령 라우팅"


@장면("배선 읽기점검(eval/wire): 모든 기관이 실제로 돈다", "실측")
def _s17():
    from eval import wire
    rows = wire.읽기()
    # wire.가르기 가 이미 '못 잰 것'(이 컨테이너에 langchain 없음 등) 과 '끊긴 것' 을 가른다 -- 두 벌 두지 않는다.
    끊김 = [r["이름"] + ":" + str(r["끝값"]) for r in rows if r["판정"] == "끊김"]
    못돌림 = [r["이름"] for r in rows if r["판정"] == "못돌림"]
    assert not 끊김, f"끊김 {끊김}"
    return f"{len(rows)}개 기관 · 이어짐 {len(rows) - len(못돌림)}" + (f" · 못돌림(여기서 못 잼) {못돌림}" if 못돌림 else "")


# ---------------------------------------------------------------- 돌리기
def 돌리기() -> dict:
    결과 = []
    for 이름, 꼴, f in 장면들:
        t0 = time.monotonic()
        try:
            말 = f() or ""
            결과.append({"장면": 이름, "꼴": 꼴, "판정": "통과", "말": str(말)[:200], "초": round(time.monotonic() - t0, 1)})
        except AssertionError as e:
            결과.append({"장면": 이름, "꼴": 꼴, "판정": "실패", "말": str(e)[:300], "초": round(time.monotonic() - t0, 1)})
        except Exception as e:                        # noqa: BLE001 -- 예외도 실패다(fail-closed)
            결과.append({"장면": 이름, "꼴": 꼴, "판정": "실패", "말": f"{type(e).__name__}: {str(e)[:250]}",
                        "초": round(time.monotonic() - t0, 1)})
    통 = sum(1 for r in 결과 if r["판정"] == "통과")
    return {"결과": 결과, "통과": 통, "실패": len(결과) - 통, "전부": len(결과)}


def 보고(r: dict) -> str:
    줄 = ["에이전트 인수 검사 -- 판정은 코드가 한다", ""]
    for x in r["결과"]:
        표 = "✓" if x["판정"] == "통과" else "✗"
        줄.append(f"  {표} [{x['꼴']}] {x['장면']}  ({x['초']}s)")
        줄.append(f"        {x['말']}")
    줄 += ["", f"통과 {r['통과']} / {r['전부']}" + (f" · **실패 {r['실패']}**" if r["실패"] else " -- 전부 통과")]
    return "\n".join(줄)


def main() -> int:
    r = 돌리기()
    if "--json" in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(보고(r))
    return 0 if r["실패"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
