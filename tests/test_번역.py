# -*- coding: utf-8 -*-
"""번역 파이프라인을 **가짜 LLM 으로** 붙든다 -- 키 없이, 망 없이 돈다.

사용자: "전체 번역본 만들어줘 gemini로."  번역은 172만 자 · 387회 호출짜리
일이고, 한 번 돌리면 쿼터를 크게 먹는다.  **돌리기 전에 배선이 옳은지는
여기서 증명한다.**

## 무엇을 붙드나

1. **묶어 부르기** -- 덩이 3,323개를 낱개로 부르면 지시문(용어집 포함)이
   호출마다 실려 입력 토큰이 본문의 여섯 배가 된다(실측: 330만 대 80만).
   묶어 보내고 표식으로 다시 가른다.
2. **표식을 잃으면 낱개로 돌아간다** -- 모델이 `<!--B7-->` 를 지울 수 있다.
   그때 묶음을 통째로 버리고 하나씩 다시 부른다. 느려질 뿐 틀리지 않는다.
3. **구조가 어긋난 번역은 안 쓴다** -- 코드가 번역됐거나 태그가 바뀌었으면
   그 덩이는 원문을 그대로 두고 실패로 보고한다(반쪽을 안 낸다).
4. **캐시** -- 두 번째 실행은 부르지 않는다. 쿼터가 끊겨도 이어 돌린다.
5. **원문 파일에서 읽는다** -- VM 은 장을 못 짓는다(저장소 밖 자료가 필요).
"""
import os
import shutil
import sys
import tempfile
import types

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(뿌리, "edu"))
sys.path.insert(0, os.path.join(뿌리, "edu", "번역"))

import translate as T  # noqa: E402

용어 = "  setup -> 셋업"

본보기 = ("<h2>A2.1 Setup</h2>"
        "<p>The setup time is a property of the flop.</p>"
        "<pre><code>always_ff @(posedge clk) q &lt;= d;</code></pre>"
        "<p>Hold has no period in it.</p>"
        "<table><tr><td>a</td><td>b</td></tr></table>")


class 가짜풀:
    """부른 횟수를 세고, 정해진 방식으로 답한다."""

    def __init__(self, 방식="정상"):
        self.방식, self.횟수 = 방식, 0

    def ask(self, pool, p):
        self.횟수 += 1
        몸 = p.split("Translate these fragments:")[-1]
        몸 = 몸.split("Translate this fragment:")[-1].strip()
        if self.방식 == "표식없음":
            몸 = T.표식패턴.sub("", 몸)
        if self.방식 == "코드번역":
            몸 = 몸.replace("always_ff", "항상_ff")
        return 몸


def _풀꽂기(가짜):
    m = types.ModuleType("llm_pool")
    m.ask = 가짜.ask
    m.build_pool = lambda: ["fake"]
    sys.modules["llm_pool"] = m


def _새곳간():
    d = tempfile.mkdtemp(prefix="번역곳간-")
    T.곳간 = d
    return d


def test_묶고_다시_가른다():
    덩이들 = [(0, "a" * 100), (1, "b" * 100), (2, "c" * 100)]
    묶음 = T.묶기(덩이들, 상한=250)
    assert [len(m) for m in 묶음] == [2, 1], 묶음
    글 = T.묶음글(묶음[0])
    갈린 = T.묶음가르기(글, 묶음[0])
    assert 갈린 == {0: "a" * 100, 1: "b" * 100}


def test_표식을_잃으면_None_이다():
    묶음 = [(0, "a"), (1, "b")]
    글 = T.묶음글(묶음).replace(T.표식틀.format(1), "")
    assert T.묶음가르기(글, 묶음) is None


def test_순서가_바뀌면_안_믿는다():
    묶음 = [(0, "aaa"), (1, "bbb")]
    글 = T.표식틀.format(1) + "\nbbb\n" + T.표식틀.format(0) + "\naaa"
    assert T.묶음가르기(글, 묶음) is None


def test_한_장을_묶어_옮긴다_그리고_호출이_한_번뿐이다():
    _새곳간()
    f = 가짜풀()
    _풀꽂기(f)
    옮긴것, 실패 = T.장옮기기("A2", 본보기, ["fake"], 용어)
    assert not 실패, 실패
    assert f.횟수 == 1, f"덩이 넷을 {f.횟수}번에 나눠 불렀다 -- 묶기가 안 걸렸다"
    assert "always_ff" in 옮긴것 and "<table>" in 옮긴것


def test_두_번째_실행은_부르지_않는다():
    _새곳간()
    f = 가짜풀()
    _풀꽂기(f)
    T.장옮기기("A2", 본보기, ["fake"], 용어)
    처음 = f.횟수
    T.장옮기기("A2", 본보기, ["fake"], 용어)
    assert f.횟수 == 처음, "캐시가 있는데 또 불렀다 -- 쿼터를 두 배로 쓴다"


def test_표식을_잃으면_낱개로_돌아가고_결과는_옳다():
    _새곳간()
    f = 가짜풀("표식없음")
    _풀꽂기(f)
    옮긴것, 실패 = T.장옮기기("A2", 본보기, ["fake"], 용어)
    assert not 실패, 실패
    # 묶음 2번(시도) + 낱개 3번(옮길 덩이 수) -- 낱개로 내려갔다는 뜻
    assert f.횟수 > 1, "표식을 잃었는데도 한 번에 끝냈다 -- 검사가 무의미하다"
    assert "Hold has no period" in 옮긴것


def test_코드를_번역하면_그_덩이는_버린다():
    _새곳간()
    f = 가짜풀("코드번역")
    _풀꽂기(f)
    옮긴것, 실패 = T.장옮기기("A2", 본보기, ["fake"], 용어)
    assert "항상_ff" not in 옮긴것, "코드가 번역된 채 결과에 들어갔다"
    assert "always_ff" in 옮긴것, "원문을 그대로 두지 않았다"


def test_묶으면_호출이_확_준다():
    장들 = [("A2", 본보기 * 40)]
    묶음 = T.어림(장들, 용어, 6000)
    assert 묶음["호출"] < 묶음["낱개호출"] / 3, 묶음
    assert 묶음["입력토큰"] < 묶음["낱개입력토큰"], 묶음


def test_원문파일에서_읽는다():
    """VM 은 장을 못 짓는다 -- `edu/원문/` 이 있으면 그것을 읽어야 한다."""
    import 원문내기
    assert os.path.exists(원문내기.차례경로), (
        "edu/원문/차례.json 이 없다 -- `python3 edu/원문내기.py` 로 꺼내 커밋한다")
    난것 = 원문내기.읽기()
    assert len(난것) >= 150, f"원문이 {len(난것)}장뿐이다"
    키, 경로, html = 난것[0]
    assert html.lstrip().startswith("<h1"), html[:80]


def test_통째로_실패하면_영어를_한국어_파일로_안_낸다():
    """실측 2026-09-20: VM 에서 `--상태` 가 **캐시 0 · 낸 장 3** 을 냈다.

    한 덩이도 못 옮겼는데 장 파일은 생겼다 -- 실패한 덩이에 원문을 그대로 두는
    규칙이, 통째로 실패하면 **영어 파일을 한국어 이름으로 내는** 꼴이 됐다.
    """
    _새곳간()

    class 늘실패:
        횟수 = 0

        def ask(self, pool, p):
            늘실패.횟수 += 1
            return "I cannot translate this."      # 태그가 다 사라진다 -> 대조 실패

    f = 늘실패()
    _풀꽂기(f)
    try:
        T.장옮기기_안전("A2", 본보기, ["fake"], 용어)
        raise AssertionError("통째로 실패했는데 조용히 넘어갔다")
    except T.통째실패 as e:
        assert "멈춘다" in str(e) and "--진단" in str(e), str(e)


def test_반만_실패하면_멈추지_않는다():
    """문턱이 너무 빡빡하면 멀쩡한 실행이 멈춘다 -- 경계도 본다."""
    _새곳간()
    f = 가짜풀()
    _풀꽂기(f)
    옮긴것, 실패 = T.장옮기기_안전("A2", 본보기, ["fake"], 용어)
    assert not 실패 and "always_ff" in 옮긴것


def test_묶음이_깨지면_스스로_줄인다():
    """출력 한도에 걸리면 응답이 잘려 표식이 사라진다 -- 그때 묶음을 줄여야 한다.

    안 줄이면 남은 쿼터를 **같은 방식으로 전부 버린다**(사용자의 키가 하루 한도에
    걸린 자리가 여기다).
    """
    원래 = T.묶음자
    try:
        T.묶음자 = 8000
        assert T._묶음줄이기() == 4000
        assert T._묶음줄이기() == 2000
        T.묶음자 = T.최소묶음자
        assert T._묶음줄이기() == T.최소묶음자, "최소 밑으로 내려가면 안 된다"
    finally:
        T.묶음자 = 원래


def test_이론서를_먼저_옮긴다():
    """쿼터가 하루에 안 끝나면 **어디서 끊기든 한 권은 손에 남아야** 한다."""
    장들 = T.장들읽기([])
    if len(장들) < 20:
        print("    (원문이 적다 -- 순서 검사를 건너뛴다)")
        return
    키들 = [k for k, _ in 장들]
    T계열 = [i for i, k in enumerate(키들) if k[:1] == "T" and k[1:2].isdigit()]
    assert T계열, f"T 계열이 없다: {키들[:5]}"
    assert max(T계열) < len(T계열) + 2, (
        f"T 계열이 앞에 몰려 있지 않다: {키들[:12]}")


def test_묶기는_옮긴_장만_모으고_몇_장인지_센다():
    """쿼터가 끊겨 반만 옮겨도 묶을 수 있어야 한다 -- 대신 **반쪽이라고 적는다.**"""
    import 한국어책
    원래 = 한국어책.한국어
    d = tempfile.mkdtemp(prefix="한국어-")
    try:
        한국어책.한국어 = d
        본문, 있는것, 전체 = 한국어책.묶기()
        assert 전체 >= 60, f"원문 차례가 {전체}권뿐이다"
        assert 있는것 == 0 and not 본문.strip(), "옮긴 것이 없는데 뭔가 모았다"
        open(os.path.join(d, "T1.html"), "w", encoding="utf-8").write(
            '<h1 id="t1">T1. 소자</h1><p>문턱전압은 소자의 성질이다.</p>')
        본문, 있는것, 전체 = 한국어책.묶기()
        assert 있는것 == 1 and "문턱전압" in 본문, (있는것, 본문[:80])
        차 = 한국어책.차례만들기(본문)
        assert 'href="#t1"' in 차 and "T1. 소자" in 차, 차
    finally:
        한국어책.한국어 = 원래
        shutil.rmtree(d, ignore_errors=True)


def test_옮긴_것이_없으면_PDF_를_만들지_않는다():
    import 한국어책
    원래 = 한국어책.한국어
    d = tempfile.mkdtemp(prefix="한국어빈-")
    낼것 = os.path.join(d, "x.pdf")
    try:
        한국어책.한국어 = d
        assert 한국어책.내기(낼것) == 2, "빈 채로 PDF 를 만들었다"
        assert not os.path.exists(낼것)
    finally:
        한국어책.한국어 = 원래
        shutil.rmtree(d, ignore_errors=True)


def test_PDF_가_실제로_나온다():
    """weasyprint 가 있는 자리에서는 **진짜 PDF 를 만든다** -- 글자만 보지 않는다."""
    try:
        import weasyprint  # noqa: F401
    except Exception:                                     # noqa: BLE001
        print("    (weasyprint 가 없다 -- 렌더는 개발 자리에서만 본다. "
              "VM·CI 에는 일부러 안 깐다: 한 번 쓰는 렌더에 무거운 의존성을 안 얹는다)")
        return
    import 한국어책
    원래 = 한국어책.한국어
    d = tempfile.mkdtemp(prefix="한국어pdf-")
    낼것 = os.path.join(d, "책.pdf")
    try:
        한국어책.한국어 = d
        open(os.path.join(d, "T1.html"), "w", encoding="utf-8").write(
            '<h1 id="t1">T1. 소자</h1><p>문턱전압 V<sub>th</sub> 는 소자의 성질이다.</p>')
        assert 한국어책.내기(낼것) == 0
        assert os.path.getsize(낼것) > 2000, os.path.getsize(낼것)
        assert open(낼것, "rb").read(5) == b"%PDF-"
    finally:
        한국어책.한국어 = 원래
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    import _run
    _run.돌리기(globals())
