"""회로도를 **그린다.** LaTeX 설치가 필요 없다 -- schemdraw + matplotlib 뿐.

사용자(2026-09-15): "디지털/아날로그 회로 설계에 사용되는 그림들(cmos nmos capacitor
inductor ... current mirror 등)이나, 원리를 설명해주는 그런 기능도 필요해."

## 왜 schemdraw 인가

회로도를 그리는 표준은 `circuitikz` 인데 그건 **LaTeX 설치**가 필요하다. 이 저장소는
이미 그 길을 한 번 안 가기로 했다(`latex_formatter.py` -- mathtext 로 LaTeX 없이 수식을
그린다). schemdraw 는 순수 파이썬이고 matplotlib 위에서 돈다. matplotlib 은 이미
`requirements.txt` 에 있다.

## 왜 `langchain` 을 안 쓰나

`bot_tools` 는 맨 위에서 langchain 셋을 임포트해서, 그것이 없는 데서는 **파일을 읽어 볼
수조차 없다** -- 검사가 못 돈다. `imageread.py` 와 같은 자리다.

## 앵커는 `absanchors` 로 잡는다 -- 실측으로 배운 것

`M.anchors['gate']` 는 **그 소자 안에서의 상대 좌표**다. 두 트랜지스터의 게이트를 이으려고
그것을 쓰면 **엉뚱한 높이에 선이 그어진다**(실측 2026-09-15: 게이트 버스가 소스 높이로
지나가 접지와 붙은 것처럼 보였다. 두 번 그렸고 두 번 다 틀렸다). 그림에 놓인 뒤의
자리는 `M.absanchors['gate']` 다. **본보기들이 그렇게 쓴다 -- 베껴 쓸 때 그 줄을 지켜라.**
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap

시한초 = 60
_머리 = textwrap.dedent('''
    import matplotlib
    matplotlib.use("Agg")
    import schemdraw
    import schemdraw.elements as elm
    from schemdraw import logic
''').strip()


def 됐나틀(됐나, 경로, 왜):
    return {"됐나":됐나, "경로": 경로, "왜": 왜}


def 그리기(코드: str, 경로: str = None) -> dict:
    """schemdraw 코드를 돌려 PNG 를 만든다. {됐나, 경로, 왜}.

    코드는 `d` 라는 `schemdraw.Drawing` 안에서 돈다 -- `with` 를 쓸 필요가 없고,
    `d += elm...` 로 쌓으면 된다. 저장은 여기서 한다.

    **딴 프로세스에서 돌린다.** 그려 보라고 준 코드가 매달리거나 터져도 봇이 같이
    죽으면 안 된다. 시한 60초.
    """
    # **dedent 를 strip 보다 먼저 한다.** 거꾸로 하면 첫 줄만 들여쓰기가 벗겨져
    # 공통 앞머리가 빈 문자열이 되고, dedent 가 아무 일도 안 한다 -- 그러면 붙여 넣은
    # 코드가 통째로 `IndentationError` 다(실측 2026-09-15: 본보기 넷이 다 그렇게 터졌다).
    코드 = textwrap.dedent(코드 or "").strip("\n").rstrip()
    if not 코드.strip():
        return 됐나틀(False, None, "빈 코드다")
    경로 = 경로 or os.path.join(tempfile.mkdtemp(prefix="회로-"), "회로.png")
    os.makedirs(os.path.dirname(경로) or ".", exist_ok=True)
    본 = (f"{_머리}\n"
         f"with schemdraw.Drawing(file={경로!r}, show=False) as d:\n"
         f"    d.config(unit=2.4, fontsize=13)\n"
         + textwrap.indent(코드, "    ") + "\n")
    쪽 = os.path.join(tempfile.mkdtemp(prefix="회로코드-"), "그린다.py")
    with open(쪽, "w", encoding="utf-8") as f:
        f.write(본)
    try:
        r = subprocess.run([sys.executable, 쪽], capture_output=True, text=True,
                           timeout=시한초)
    except subprocess.TimeoutExpired:
        return 됐나틀(False, None, f"{시한초}초 안에 안 끝났다 -- 코드가 매달렸다")
    if r.returncode != 0:
        # **역추적 틀이 아니라 까닭을 낸다.** 뒤 네 줄을 그냥 자르면 `^^^^^^` 와
        # `File "..."` 만 남아 무엇이 틀렸는지 안 보인다(실측 2026-09-15). 마지막 줄이
        # 예외 줄이고, 그 위에서 코드 줄(`    d += ...`)을 하나 찾아 같이 보인다 --
        # 고쳐 쓰려면 "어디가" 와 "왜" 가 둘 다 있어야 한다.
        줄들 = [l for l in (r.stderr or r.stdout or "").strip().splitlines() if l.strip()]
        까닭 = 줄들[-1] if 줄들 else "까닭을 못 읽었다"
        어디 = next((l.strip() for l in reversed(줄들[:-1])
                   if l.startswith("    ") and not l.lstrip().startswith(("^", "File", "~"))), "")
        # **빈 그림은 빈 그림이라고 말한다.** `elm.없는소자()` 처럼 schemdraw 가 모르는
        # 이름을 쓰면 AttributeError 가 아니라 아무것도 안 그려진 채 끝나고, matplotlib 이
        # `Axis limits cannot be NaN or Inf` 를 낸다 -- 사람이 읽고 고칠 수 있는 말이
        # 아니다(실측 2026-09-15). 무엇을 고쳐야 하는지로 옮겨 적는다.
        if "Axis limits cannot be" in 까닭:
            return 됐나틀(False, None,
                       "**아무것도 안 그려졌다** -- 소자 이름이 틀렸거나 `d +=` 로 "
                       "하나도 안 쌓았다. `example` 로 본보기를 먼저 그려 그 꼴을 봐라"
                       + (f"\n  그 줄: {어디}" if 어디 and "raise" not in 어디 else ""))
        return 됐나틀(False, None, "schemdraw 가 터졌다: " + 까닭
                    + (f"\n  그 줄: {어디}" if 어디 and "raise" not in 어디 else ""))
    if not (os.path.isfile(경로) and os.path.getsize(경로) > 0):
        return 됐나틀(False, None, "파일이 안 생겼거나 비었다")
    return 됐나틀(True, 경로, "")


# ------------------------------------------------------------------ 본보기
# **여기 있는 것은 그려 보고 눈으로 확인한 것이다.** 베껴 쓰면 맞는 그림이 나온다.
# 처음 두 판은 `anchors` 를 써서 게이트 버스가 어긋났다 -- `absanchors` 로 고쳤다.
본보기 = {
    "전류미러": '''
        M1 = d.add(elm.AnalogNFet().anchor('source').at((0, 0)).label('$M_1$', loc='left'))
        M2 = d.add(elm.AnalogNFet().anchor('source').at((5, 0)).label('$M_2$', loc='right'))
        for M, 이름 in ((M1, '$I_{REF}$'), (M2, '$I_{OUT}$')):
            d += elm.Ground().at(M.absanchors['source'])
            d += elm.Line().at(M.absanchors['drain']).up().length(0.9)
            d += elm.SourceI().up().label(이름)
            d += elm.Vdd().label('$V_{DD}$')
        g1, g2 = M1.absanchors['gate'], M2.absanchors['gate']
        d += elm.Line().at(g1).to(g2)
        d1 = M1.absanchors['drain']
        d += elm.Line().at(g1).up().toy(d1)
        d += elm.Line().to(d1)
        d += elm.Dot().at(d1)
        d += elm.Dot().at(g2)
    ''',
    "CMOS인버터": '''
        MP = d.add(elm.AnalogPFet().anchor('drain').at((0, 0)).label('$M_P$', loc='left'))
        MN = d.add(elm.AnalogNFet().anchor('drain').at((0, -2.2)).label('$M_N$', loc='left'))
        d += elm.Line().at(MP.absanchors['source']).up().length(0.7)
        d += elm.Vdd().label('$V_{DD}$')
        d += elm.Ground().at(MN.absanchors['source'])
        gp, gn = MP.absanchors['gate'], MN.absanchors['gate']
        d += elm.Line().at(gp).to(gn)
        d += elm.Line().at(gp).left().length(1.2).label('$V_{IN}$', loc='left')
        d += elm.Line().at(MP.absanchors['drain']).to(MN.absanchors['drain'])
        마디 = MN.absanchors['drain']
        d += elm.Dot().at(마디)
        d += elm.Line().at(마디).right().length(1.6).label('$V_{OUT}$', loc='right')
    ''',
    "공통소스": '''
        M1 = d.add(elm.AnalogNFet().anchor('source').at((0, 0)).label('$M_1$', loc='right'))
        d += elm.Ground().at(M1.absanchors['source'])
        d += elm.Line().at(M1.absanchors['drain']).up().length(0.5)
        d += elm.Dot()
        d += elm.Resistor().up().label('$R_D$')
        d += elm.Vdd().label('$V_{DD}$')
        아웃 = M1.absanchors['drain']
        d += elm.Line().at(아웃).right().length(1.8).label('$v_{out}$', loc='right')
        d += elm.Line().at(M1.absanchors['gate']).left().length(1.0)
        d += elm.SourceV().down().label('$v_{in}$')
        d += elm.Ground()
    ''',
    # **첫 판은 축전기가 떠 있었다** -- `d.here` 가 출력선 끝이라 마디에서 떨어졌다.
    # 마디를 변수로 잡아 거기서 내린다. 그려 보고 눈으로 확인한 판이 이것이다.
    "RC저역": '''
        d += elm.SourceV().up().label('$v_{in}$')
        위 = d.here
        d += elm.Resistor().right().label('$R$')
        마디 = d.here
        d += elm.Dot().at(마디)
        d += elm.Line().at(마디).right().length(1.4).label('$v_{out}$', loc='right')
        d += elm.Capacitor().at(마디).down().toy(0).label('$C$')
        d += elm.Line().left().tox(위[0])
        d += elm.Ground()
    ''',
}


def 본보기그리기(이름: str, 경로: str = None) -> dict:
    """본보기 하나를 그린다. 이름을 모르면 아는 이름을 알려준다."""
    코드 = 본보기.get(이름)
    if 코드 is None:
        return 됐나틀(False, None, f"모르는 본보기다 -- 아는 것: {' · '.join(본보기)}")
    return 그리기(코드, 경로)
