# -*- coding: utf-8 -*-
"""이 책에만 있는 조각들 -- 정리·증명 · 레포 해부 · 논문 밑줄 · 언어 비교.

`edu/bookK.py` 가 주는 것(장·개념·표·그림·정의·유도·예제·짚기·사고)은 그대로 쓰고,
사용자가 요구한 네 가지를 여기에 더한다.

1. **"모든 이론에는 근거가 있어야 한다. 이는 수학의 증명이다."**
   그래서 `정리()` 는 **증명 없이는 만들어지지 않는다** -- 인자가 아니라 강제다.
   증명의 한 걸음은 `(이렇게, 왜냐하면)` 쌍이라, `왜냐하면` 을 비우면 그 줄이
   논리 점프다. `bookK.유도` 와 같은 규율이고, 이 책에서는 그것이 증명이다.

2. **레포 해부.** 별을 몇 백 개 받은 저장소를 "이런 게 있다" 로 넘기지 않는다.
   저장소마다 **내가 실제로 클론해서 읽은 커밋**을 적고, 그 커밋의 파일·줄을
   인용한다. `레포()` 가 그 머리말을 찍는다.

3. **논문 밑줄.** 초록의 핵심 구절에 밑줄을 긋고, 밑줄마다 "이게 무슨 뜻이냐" 를
   표로 붙인다. 머리에 **확인수준**(전문·초록·조각)을 박는다 -- CLAUDE.md 의
   *읽지 않은 것을 인용하지 않는다* 를 이 책에서 지키는 방법이다.

4. **언어 비교.** 같은 한 가지 일을 Python · Rust · TypeScript · Go · Java(Spring) ·
   셸로 나란히 적는다. 문법이 다른 것이 아니라 **무엇을 강제하느냐가 다르다** 는
   것을 보이는 게 목적이다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "edu"))

from bookK import 안전  # noqa: E402

_정리번호 = [0]
_논문번호 = [0]
정리들 = []       # (번호, 제목, 증명걸음수) -- 검사가 본다


def 정리(제목, 진술, 증명걸음, 종류="정리", 가정=None, 끝="∎"):
    """정리 하나와 그 증명.  **증명 없이는 못 만든다.**

    제목     : "추측 디코딩은 대상 분포를 바꾸지 않는다"
    진술     : 정리의 내용 (HTML). 기호를 먼저 정의하고 쓴다
    증명걸음 : [(이렇게, 왜냐하면), ...] -- 왜냐하면이 비면 그 줄이 점프다
    종류     : 정리 · 보조정리 · 따름정리 · 명제
    가정     : 이 정리가 서 있는 가정 (없으면 정리가 아니라 관찰이다)

    이 함수가 던지는 예외는 **책이 안 나오게 하는 것이 목적**이다. 근거 없는
    주장을 조용히 통과시키면 그 다음부터는 아무도 안 읽는다.
    """
    if not 증명걸음:
        raise ValueError(f"증명 없는 정리: {제목!r} -- 이 책은 그것을 안 받는다")
    빈칸 = [i for i, (_, 왜) in enumerate(증명걸음, 1) if not str(왜).strip()]
    if 빈칸:
        raise ValueError(f"{제목!r}: 증명 {빈칸} 번째 걸음에 '왜냐하면' 이 비었다 -- 점프다")
    _정리번호[0] += 1
    번호 = _정리번호[0]
    정리들.append((번호, 제목, len(증명걸음)))
    가정h = f'<div class="정리가정"><b>가정.</b> {가정}</div>' if 가정 else ""
    걸음h = "".join(
        f'<tr><td class="증명번호">{i}</td><td class="증명말">{a}</td>'
        f'<td class="증명왜">{b}</td></tr>'
        for i, (a, b) in enumerate(증명걸음, 1))
    return (f'<div class="정리"><div class="정리머리">{종류} {번호}. {제목}</div>'
            f'<div class="정리속">{진술}</div>{가정h}</div>'
            f'<div class="증명"><div class="증명머리">증명.</div>'
            f'<table class="증명표"><tbody>{걸음h}</tbody></table>'
            f'<div class="증명끝">{끝}</div></div>')


def 보조정리(제목, 진술, 증명걸음, **kw):
    return 정리(제목, 진술, 증명걸음, 종류="보조정리", **kw)


def 따름정리(제목, 진술, 증명걸음, **kw):
    return 정리(제목, 진술, 증명걸음, 종류="따름정리", **kw)


def 레포(이름, 주소, 커밋, 줄들, 한마디=""):
    """저장소 하나의 명찰.

    커밋을 반드시 적는다 -- "langgraph 는 이렇다" 는 **언제의** langgraph 냐에
    따라 틀린 말이 된다. 이 책이 읽은 커밋은 `agentbook/zoo.json` 에 있다.
    """
    몸 = f'<div class="레포속">{한마디}</div>' if 한마디 else ""
    줄h = "".join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in 줄들)
    return (f'<div class="레포"><div class="레포머리">{이름}'
            f'<span class="주소">{안전(주소)} @ {안전(커밋)}</span></div>'
            f'{몸}<table class="레포표"><tbody>{줄h}</tbody></table></div>')


def 논문(제목, 출처, 확인수준, 인용, 밑줄풀이, 왜중요=""):
    """논문 하나를 **밑줄 쳐 가며** 읽힌다.

    인용     : 본문/초록의 글. 핵심 구절을 `{1}...{/1}` 로 감싸면 밑줄이 되고
               위첨자 번호가 붙는다
    밑줄풀이 : [(구절, 무슨 뜻인가), ...] -- 위 번호와 같은 순서
    확인수준 : 전문 · 초록 · 조각 -- **읽은 만큼만 적는다.**
               `조각` 은 검색 결과 조각만 봤다는 뜻이고, 그러면 그 논문의
               세부 주장을 이 책의 근거로 쓰지 않는다
    """
    if 확인수준 not in ("전문", "초록", "조각", "코드"):
        raise ValueError(f"모르는 확인수준: {확인수준}")
    if 인용.count("{") != len(밑줄풀이) * 2:
        raise ValueError(f"{제목!r}: 밑줄 {인용.count('{')//2}개인데 풀이 {len(밑줄풀이)}개")
    _논문번호[0] += 1
    글 = 안전(인용)
    for i in range(len(밑줄풀이), 0, -1):
        글 = 글.replace("{%d}" % i, f'<u class="핵">').replace(
            "{/%d}" % i, f'</u><sup>{i}</sup>')
    풀h = "".join(f'<tr><th>{i}</th><td class="밑줄">{구}</td><td>{뜻}</td></tr>'
                 for i, (구, 뜻) in enumerate(밑줄풀이, 1))
    중요 = f'<div class="레포속">{왜중요}</div>' if 왜중요 else ""
    return (f'<div class="논문"><div class="논문머리">[논문 {_논문번호[0]}] {제목}'
            f'<span class="수준">확인: {확인수준}</span></div>'
            f'<div class="논문인용">{글}</div>'
            f'<table class="논문풀이"><tbody>{풀h}</tbody></table>{중요}</div>')


def 논문출처(줄들):
    return ('<table><caption>이 장이 쓴 논문과 <b>내가 어디까지 읽었는지</b>. '
            '확인수준이 <i>조각</i>인 것은 검색 결과만 본 것이라, 그 논문의 '
            '세부 주장을 근거로 쓰지 않았다.</caption>'
            '<thead><tr><th>논문</th><th>주소</th><th>확인수준</th>'
            '<th>이 책에서 쓴 곳</th></tr></thead><tbody>'
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
                      for r in 줄들) + '</tbody></table>')


def 언어(제목, 칸들, 짚기=""):
    """같은 일을 여러 말로.  칸 하나는 (언어이름, 코드, 한줄평)."""
    몸 = []
    for 이름, 코드, 평 in 칸들:
        평h = f'<div class="언어짚">{평}</div>' if 평 else ""
        몸.append(f'<div class="언어칸"><div class="언어이름">{안전(이름)}</div>'
                 f'<pre><code>{안전(코드)}</code></pre>{평h}</div>')
    끝 = f'<div class="언어짚" style="border:0;padding-top:5pt">{짚기}</div>' if 짚기 else ""
    return (f'<div class="언어"><div class="언어머리">{제목}</div>'
            + "".join(몸) + 끝 + '</div>')


감당 = {}          # 열쇠 -> 그것을 감당한다고 선언한 장 번호들. 검사가 본다


def 직무(줄들, 장번호=None):
    """이 장이 채용공고의 어느 줄을 감당하나.  `jd.py` 의 열쇠를 쓴다.

    선언은 **기록된다.** `tests/test_agentbook.py` 가 `jd.요구` 전체와 맞춰 보고,
    감당하는 장이 하나도 없는 요구가 있으면 빨간불을 낸다 -- "이 책을 읽으면 이
    일을 할 수 있다" 를 검사할 수 있게 만드는 장치다.
    """
    import bookK
    if 장번호 is None:
        장번호 = bookK.장들[-1].번호 if bookK.장들 else "?"
    import jd
    항 = []
    for k in 줄들:
        if k not in jd.요구:
            raise KeyError(f"모르는 직무 열쇠: {k!r} (jd.py 에 없다)")
        감당.setdefault(k, []).append(장번호)
    for k in 줄들:
        항.append(f"<b>{jd.어디(k)}</b> {jd.글(k)}")
    return ('<div class="직무"><b>이 장이 감당하는 채용 요구</b><br>'
            + "<br>".join(항) + '</div>')


def 소스(열쇠, 설명="", 풀이=(), 접기=()):
    """**남의 코드를 줄 단위로 읽힌다.**

    `agentbook/snips/` 에 박아 둔 발췌를 꺼내 줄 번호와 함께 찍고, 줄마다 풀이를
    붙인다. 사용자 지시(2026-09-21): "코드도 다 분석해줘 일일이."

    열쇠 : 발췌의 이름 (`발췌.py` 가 만든 것)
    풀이 : [(줄번호, "이 줄이 무엇을 하나"), ...] -- 번호는 **원본 파일의 줄 번호**
    접기 : 지면을 아끼려고 `...` 로 줄일 줄 범위들 [(a, b), ...]
    """
    import 발췌
    메타, 줄들 = 발췌.읽기(열쇠)
    풀이표 = dict(풀이)
    접을것 = set()
    for a, b in 접기:
        접을것 |= set(range(a, b + 1))
    몸 = []
    접힘중 = False
    for n, 글 in 줄들:
        if n in 접을것:
            if not 접힘중:
                몸.append('<tr><td class="소스번호">&#8942;</td>'
                         '<td class="소스글">&#8230;</td></tr>')
                접힘중 = True
            continue
        접힘중 = False
        강조 = ' class="소스짚"' if n in 풀이표 else ""
        몸.append(f'<tr{강조}><td class="소스번호">{n}</td>'
                 f'<td class="소스글">{안전(글)}</td></tr>')
    풀h = ""
    if 풀이:
        풀h = ('<table class="소스풀이"><thead><tr><th>줄</th><th>이 줄이 하는 일</th>'
              '</tr></thead><tbody>'
              + "".join(f'<tr><td class="소스번호">{n}</td><td>{t}</td></tr>'
                        for n, t in 풀이) + '</tbody></table>')
    설h = f'<div class="소스설명">{설명}</div>' if 설명 else ""
    return (f'<div class="소스"><div class="소스머리">{안전(메타["저장소"])}'
            f'<span class="소스경로">{안전(메타["경로"])}:'
            f'{메타["시작"]}&ndash;{메타["끝"]} @ {안전(메타["커밋"])}</span></div>'
            f'{설h}<table class="소스표"><tbody>{"".join(몸)}</tbody></table>'
            f'{풀h}</div>')


def 말풀이(줄들):
    """**용어를 한 표로.** 사용자 지시: "무슨 뭐로 감싼다 뭐로 한다 이해가 안되는데"

    줄 하나는 (말, 영어, 무슨 뜻인가, 왜 그렇게 부르나) 다. 네 번째 칸이 중요하다 --
    이름의 유래를 알면 그 말이 다시 나왔을 때 안 막힌다.
    """
    return ('<table class="말풀이"><caption>이 절에서 처음 나오는 말. '
            '<b>이름이 왜 그런지까지 적는다</b> &mdash; 그래야 다음에 안 막힌다.</caption>'
            '<thead><tr><th>말</th><th>영어</th><th>무슨 뜻인가</th>'
            '<th>왜 그렇게 부르나</th></tr></thead><tbody>'
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
                      for r in 줄들) + '</tbody></table>')
