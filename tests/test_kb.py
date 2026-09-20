# -*- coding: utf-8 -*-
"""**디스코드가 교재로 답하는 길**을 붙든다.

사용자 지시(2026-09-20): *"너가 영어로 작성해서 VM에 넣으면 그걸 질문하면 디스코드가
대답할 수 있게."*  그 길은 세 토막이다.

    edu/kb/kb.jsonl   커밋된 교재 본문 (VM 은 교재를 못 짓는다 -- 밖의 자료가 필요하다)
    edu/용어.py       한국어 물음 -> 영어 본문의 말
    bot_tools.textbook 도구로 묶고, 두 프롬프트가 그것을 부르게 한다

## 이 검사가 실제로 막는 것

*하나.* **장을 새로 쓰고 색인을 안 지은 것.**  그러면 봇은 그 장을 영원히 못 찾고,
못 찾았다고 말하지도 않는다 -- 그냥 기억으로 답한다.  `edu/*.py` 를 AST 로 훑어
`ch_*` 를 가진 모듈이 전부 색인에 있는지 본다(렌더는 2분 30초라 여기서 안 돌린다).

*둘.* **한국어로 물으면 아무것도 안 걸리는 것.**  본문은 영어다.  물음-정답 짝을
두고 옳은 장이 상위에 오는지 본다.

*셋 -- 그리고 이것이 요점.* **이 검사가 거짓 초록인 것.**  찾기가 무엇을 주든
초록이면 검사가 아니다.  그래서 `test_자해_색인망가뜨리면_빨개진다` 가 색인에서
그 장을 **빼고** 같은 물음을 던져, 그때는 **못 찾아야** 한다고 못 박는다.
"""
import ast
import io
import json
import os
import sys

import pytest

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 뿌리)
sys.path.insert(0, os.path.join(뿌리, "edu"))

import kb            # noqa: E402
import 용어           # noqa: E402


# ---------------------------------------------------------------------------
def test_색인이_있다():
    assert os.path.exists(kb.원장), (
        "edu/kb/kb.jsonl 이 없다. `python3 edu/kb.py --짓기` 로 짓고 커밋한다 -- "
        "VM 은 교재를 못 짓는다(저장소 밖 자료가 필요하다)")
    m = kb.요약()
    assert m.get("절", 0) >= 400, m
    assert not m.get("못한것"), m["못한것"]


def _ast로_장가진모듈():
    """렌더하지 않고 `ch_*` 를 가진 모듈 이름만 모은다 (싸다)."""
    난것 = set()
    d = os.path.join(뿌리, "edu")
    for p in sorted(os.listdir(d)):
        if not p.endswith(".py") or p[:-3] in kb.틀:
            continue
        try:
            t = ast.parse(open(os.path.join(d, p), encoding="utf-8").read())
        except SyntaxError:
            continue
        if any(isinstance(n, ast.FunctionDef) and n.name.startswith("ch_")
               for n in t.body):
            난것.add(p[:-3])
    return 난것


def test_새_장을_쓰고_색인을_안_지으면_걸린다():
    있는것 = {r["모듈"] for r in kb.싣기()}
    써야할것 = _ast로_장가진모듈()
    빠진것 = sorted(써야할것 - 있는것)
    assert not 빠진것, (
        f"색인에 없는 장: {빠진것}. `python3 edu/kb.py --짓기` 를 다시 돌리고 "
        "edu/kb/ 를 같이 커밋한다")


# ---------------------------------------------------------------------------
# 물음 -> 답이 있어야 하는 장.  말표를 늘릴 때 여기도 늘린다.
# ---------------------------------------------------------------------------
짝 = [
    ("준안정 상태가 뭐고 MTBF 는 어떻게 계산해?",        ("X3_cdc", "C_digital", "B_device", "T3_meta")),
    ("셋업 홀드 위반이 나면 뭘 봐야 해?",                 ("X2_timing", "B_device", "Z17_gates")),
    ("클럭 도메인 넘길 때 그레이 코드를 왜 써?",          ("X3_cdc", "C_digital")),
    ("DFE 탭이 하는 일이 뭐야?",                          ("X4_link", "F_comm", "P_iface", "Y2_pcie")),
    ("8b/10b 의 running disparity 규칙 설명해줘",         ("Z22_8b10b", "F_comm", "P_iface")),
    ("SEC-DED 해밍 부호 신드롬이 어떻게 나와?",           ("Z23_ecc", "X5_fec", "F_comm", "I_info")),
    ("고정소수점 비트폭은 어떻게 정해?",                  ("X1_fixed", "E_dsp")),
    ("문턱전압과 바디효과 관계가 뭐야?",                  ("B_device", "T1_device", "X31_analog")),
    ("HLS 로 hand RTL 보다 좋은 QoR 내는 방법",           ("Z15_hls", "Y12_hls", "Q_more")),
    ("AXI 버스트와 outstanding 이 뭐야?",                 ("X37_bus", "Z11_axi", "J_blocks")),
    ("IR drop 과 decap 을 어떻게 잡아?",                  ("X32_pdn", "L_phys", "X14_physdes")),
    ("MIPI CSI-2 패킷 헤더 구조 알려줘",                  ("P_iface", "Y1_mipi", "Z21_spec")),
    ("변이 점수가 뭐고 왜 재?",                           ("Z1_team", "Z3_bar", "H_verif", "X8_verif")),
    ("SRAM 비트셀과 센스앰프가 어떻게 동작해?",           ("X10_mem", "J_blocks", "B_device")),
    ("PLL 루프 대역폭은 어떻게 정해?",                    ("X12_ams", "B_device", "T7_pll")),
    ("전력 영역과 UPF 아이솔레이션 셀",                   ("X43_lowpower", "X7_power", "L_phys")),
    ("NLDM 이 뭐고 슬루가 왜 두 번째 축인가",             ("T2_delay", "B_device", "X2_timing")),
    ("긴 배선에 리피터를 몇 개 넣어야 하나",              ("T2_delay", "B_device", "X14_physdes")),
    ("논리적 노력으로 단수를 어떻게 정하나",              ("T2_delay", "B_device", "Z17_gates")),
]


@pytest.mark.parametrize("물음,후보", 짝)
def test_한국어로_물어도_옳은_장이_온다(물음, 후보):
    절들, 말 = kb.찾기(물음, 개수=5)
    assert 절들, f"아무것도 못 찾았다: {물음} (못 바꾼 말: {말['못바꾼말']})"
    온것 = [r["모듈"] for r in 절들]
    assert any(m in 후보 for m in 온것), (
        f"{물음}\n  기대: {후보}\n  온 것: {온것}\n  바꾼 말: {말['영어로']}")


def test_덮지_못한_주제를_적어_둔다():
    """`edu/kb/빈자리.md` 에 적힌 주제는 **정말로 교재에 없어야** 한다.

    실측 2026-09-20: "SRAM 의 SNM" 과 "ESD 보호" 를 물었더니 엉뚱한 장이 왔다.
    까 보니 코퍼스 전체에 `noise margin` 이 **0회**, ESD 는 EMC 장의 곁다리뿐이었다.
    **못 덮은 것을 못 덮었다고 적어 두지 않으면** 봇이 그 자리에서 기억으로 답한다.

    그리고 이 검사는 반대쪽도 막는다 -- 나중에 그 장을 쓰면 **빨개진다.**
    그때 할 일은 빈자리 목록에서 그 줄을 지우는 것이다.
    """
    p = os.path.join(뿌리, "edu", "kb", "빈자리.md")
    assert os.path.exists(p), "빈자리.md 가 없다 -- 못 덮은 주제를 적어 둔다"
    말들 = [l.split("`")[1] for l in open(p, encoding="utf-8").read().splitlines()
           if l.startswith("- `")]
    assert 말들, "빈자리 목록이 비었다 -- 형식은 '- `찾을말` — 설명' 이다"
    본문 = "\n".join(r["글"].lower() for r in kb.싣기())
    이제있는것 = [w for w in 말들 if w.lower() in 본문]
    assert not 이제있는것, (
        f"이제 교재가 덮는다: {이제있는것}. edu/kb/빈자리.md 에서 그 줄을 지우고 "
        "tests/test_kb.py 의 물음-정답 짝에 더한다")


def test_못_바꾼_한국어_말을_숨기지_않는다():
    _, 말 = kb.찾기("깍두기 볶음밥 레시피 알려줘", 개수=3)
    assert "볶음밥" in 말["못바꾼말"] or "레시피" in 말["못바꾼말"], 말


def test_말표가_실제로_바꾼다():
    확장, 바뀐것, _ = 용어.넓히기("준안정 동기화기 셋업")
    assert "metastability" in 확장 and "synchronizer" in 확장, 확장
    assert len(바뀐것) >= 3, 바뀐것


# ---------------------------------------------------------------------------
# 자해검사 -- 이 검사가 빨개질 수 있음을 증명한다
# ---------------------------------------------------------------------------
def test_자해_색인망가뜨리면_빨개진다():
    """CDC 장들을 색인에서 빼면, 준안정 물음이 **그 장을 못 찾아야** 한다.

    이걸 안 해 두면 `찾기` 가 무엇을 주든 위의 짝 검사가 통과할 수 있다.

    (fixture 를 안 쓴다 -- 이 저장소의 스크립트 러너는 fixture 를 흉내 내지 않아서,
    `tmp_path` 를 받는 검사는 `python3 tests/test_kb.py` 로 못 돈다.)
    """
    import tempfile
    뺄것 = {"X3_cdc", "C_digital", "B_device", "T3_meta"}
    원래문서 = kb.싣기()
    남은 = [r for r in 원래문서 if r["모듈"] not in 뺄것]
    assert len(남은) < len(원래문서), "뺄 것이 애초에 없었다 -- 검사가 무의미하다"
    원래원장 = kb.원장
    d = tempfile.mkdtemp()
    p = os.path.join(d, "kb.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r, ensure_ascii=False) for r in 남은))
    try:
        kb.원장, kb._실림 = p, None
        절들, _ = kb.찾기("준안정 상태가 뭐고 MTBF 는 어떻게 계산해?", 개수=5)
        온것 = [r["모듈"] for r in 절들]
        assert not (set(온것) & 뺄것), f"뺐는데도 왔다 -- 찾기가 색인을 안 본다: {온것}"
    finally:
        kb.원장, kb._실림 = 원래원장, None
        os.remove(p)
        os.rmdir(d)


# ---------------------------------------------------------------------------
# 도구와 프롬프트에 실제로 물렸나 -- 도구가 있어도 안 적히면 안 쓴다
# ---------------------------------------------------------------------------
def _이름들(파일, 변수):
    t = ast.parse(open(os.path.join(뿌리, 파일), encoding="utf-8").read())
    for n in t.body:
        if isinstance(n, ast.Assign) and any(
                getattr(x, "id", "") == 변수 for x in n.targets):
            return {e.id for e in n.value.elts if isinstance(e, ast.Name)}
    return set()


def test_두_채널_도구목록에_다_들어갔다():
    assert "textbook" in _이름들("discord_bot_server.py", "ADMIN_TOOLS")
    assert "textbook" in _이름들("main_public.py", "PUBLIC_TOOLS")


def test_두_프롬프트가_교재규칙을_끼운다():
    import eda_prompt
    assert "textbook(" in eda_prompt.교재규칙
    for f in ("discord_bot_server.py", "main_public.py"):
        s = open(os.path.join(뿌리, f), encoding="utf-8").read()
        assert "_eda.교재규칙" in s, f"{f} 에 교재규칙이 안 끼워졌다"


def test_근거와_답의_꼴을_같이_준다():
    """도구가 돌려주는 그 글을 **langchain 없이** 검사한다.

    `bot_tools.textbook` 은 `@tool` 껍데기라 langchain 이 없으면 임포트도 안 된다.
    건너뛰는 검사는 검사가 아니므로(저장소 미결 #9 가 같은 병이다) 로직을
    `kb.답근거` 로 빼 두었다 -- 여기서 실제로 돈다.
    """
    글 = kb.답근거("준안정 상태 MTBF 계산", sections=3)
    assert "###" in 글, 글[:300]
    assert "graduate-seminar" in 글, 글[-400:]
    assert "Korean→English" in 글, 글[:300]
    assert "metastab" in 글.lower(), 글[:600]
    # 잘린 절은 어떻게 다 받는지 알려 준다
    긴것 = max(kb.싣기(), key=lambda r: len(r["글"]))
    if len(긴것["글"]) > 4500:
        assert "section_id=" in kb.답근거(긴것["절"], sections=8)


def test_안_덮는_것을_물으면_도구가_먼저_말한다():
    """빈자리에 적힌 주제를 물으면 답 첫머리에 '안 덮는다' 가 붙어야 한다.

    (전에는 `noise margin` 으로 물었다.  **T4.3 이 그것을 메워서** 이 검사가
    빨개졌고 -- 설계대로다 -- 아직 안 메운 ESD 로 바꿨다.  이 자리도 T16 을
    쓰면 빨개진다.  그때는 빈자리 목록과 여기를 같이 고친다.)
    """
    글 = kb.답근거("ESD 보호에 electrostatic discharge 클램프가 어떻게 들어가나",
                 sections=3)
    assert "does not cover" in 글, 글[:400]


def test_도구_껍데기는_로직을_안_들고_있다():
    """껍데기가 다시 로직을 품으면 검사가 못 보는 자리가 생긴다."""
    t = ast.parse(open(os.path.join(뿌리, "bot_tools.py"), encoding="utf-8").read())
    for n in ast.walk(t):
        if isinstance(n, ast.FunctionDef) and n.name == "textbook":
            몸 = [x for x in n.body if not isinstance(x, ast.Expr)]
            assert len(몸) <= 5, (
                "bot_tools.textbook 이 다시 두꺼워졌다 -- 로직은 edu/kb.py 의 "
                "답근거() 에 둔다 (langchain 없는 자리에서도 검사되도록)")
            return
    raise AssertionError("bot_tools.textbook 이 없다")


def test_도구_독스트링이_답의_꼴을_말한다():
    """모델이 읽는 것은 독스트링이다 -- 거기에 없으면 안 지킨다."""
    t = ast.parse(open(os.path.join(뿌리, "bot_tools.py"), encoding="utf-8").read())
    for n in ast.walk(t):
        if isinstance(n, ast.FunctionDef) and n.name == "textbook":
            d = ast.get_docstring(n) or ""
            for 있어야 in ("graduate-seminar", "governing relation",
                        "Never present recall", "Korean"):
                assert 있어야 in d, f"도구 설명에 '{있어야}' 가 없다"
            return
    raise AssertionError("bot_tools.textbook 이 없다")


if __name__ == "__main__":
    import _run
    _run.돌리기(globals())
