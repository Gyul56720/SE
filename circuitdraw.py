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
import re as _re
import subprocess
import sys
import tempfile
import textwrap

시한초 = 60
_머리 = textwrap.dedent('''
    import matplotlib
    matplotlib.use("Agg")
    import sys
    sys.path.insert(0, %r)
    try:
        import latex_formatter as _lf
        _lf.글꼴세우기()          # 한글 라벨이 두부로 안 나오게 (실측 2026-09-15)
    except Exception:
        pass
    import schemdraw
    import schemdraw.elements as elm
    from schemdraw import logic
''').strip() % os.path.dirname(os.path.abspath(__file__))


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
    try:
        import latex_formatter as _lf
        # **따옴표 안만 본다.** 코드 전체를 보면 한글 **주석**에 걸린다 -- 주석은
        # 그림에 안 나가는데 본보기가 통째로 거절됐다(실측 2026-09-15). 두부가 되는
        # 것은 화면에 그려지는 글자, 곧 문자열 리터럴뿐이다.
        _주석없이 = _re.sub(r"(?m)#.*$", "", 코드)
        _라벨들 = " ".join(a or b for a, b in
                         _re.findall(r"'([^']*)'|\"([^\"]*)\"", _주석없이))
        if _lf.한글있나(_라벨들) and not _lf.한글글꼴():
            return 됐나틀(False, None,
                       "라벨에 한글이 있는데 이 기계에 한글 글꼴이 없다 -- 그리면 네모로 "
                       "나온다(두부). **라벨을 영어로 써라**(EDA 판의 말이 어차피 영어다)")
    except ImportError:
        pass
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
    "current_mirror": '''
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
    "cmos_inverter": '''
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
    "common_source_amp": '''
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
    "rc_lowpass": '''
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

    # ---- 디지털 ----------------------------------------------------------------
    # 사용자(2026-09-15): "디지털 회로 설계로 아날로그 회로 설계처럼 스키마틱 출력이랑
    # 개념, 변수 등의 석사 교과서적 내용들을 물어 볼 수 있으면 좋겠어."
    "cmos_nand2": '''
        P1 = d.add(elm.AnalogPFet().anchor('drain').at((0, 0)).label('$M_{P1}$', loc='left'))
        P2 = d.add(elm.AnalogPFet().anchor('drain').at((2.4, 0)).label('$M_{P2}$', loc='right'))
        for P in (P1, P2):
            d += elm.Line().at(P.absanchors['source']).up().length(0.6)
        위 = P1.absanchors['source'][1] + 0.6
        d += elm.Line().at((0, 위)).to((2.4, 위))
        d += elm.Vdd().at((1.2, 위)).label('$V_{DD}$')
        d += elm.Line().at(P1.absanchors['drain']).to(P2.absanchors['drain'])
        마디 = P1.absanchors['drain']
        N1 = d.add(elm.AnalogNFet().anchor('drain').at((0, -1.6)).label('$M_{N1}$', loc='left'))
        N2 = d.add(elm.AnalogNFet().anchor('drain').at(N1.absanchors['source']).label('$M_{N2}$', loc='left'))
        d += elm.Line().at(마디).to(N1.absanchors['drain'])
        d += elm.Dot().at(마디)
        d += elm.Ground().at(N2.absanchors['source'])
        d += elm.Line().at(마디).right().tox(3.6).label('$Y$', loc='right')
        d += elm.Line().at(P1.absanchors['gate']).to(N1.absanchors['gate'])
        d += elm.Line().at(N1.absanchors['gate']).left().tox(-1.6).label('$A$', loc='left')
        d += elm.Line().at(P2.absanchors['gate']).right().tox(5.6)
        d += elm.Line().down().toy(N2.absanchors['gate'][1])
        d += elm.Line().left().to(N2.absanchors['gate'])
        d += elm.Line().at((5.6, P2.absanchors['gate'][1])).up().length(0.7).label('$B$', loc='right')
    ''',
    "logic_gates": '''
        d += logic.Nand().right().label('NAND', loc='top').at((0, 3))
        d += logic.Nor().right().label('NOR', loc='top').at((0, 1.2))
        d += logic.Xor().right().label('XOR', loc='top').at((0, -0.6))
        d += logic.Not().right().label('NOT', loc='top').at((0, -2.2))
        d += logic.Tgate().right().label('T-GATE', loc='top').at((0, -3.8))
    ''',
    "setup_hold": '''
        d += logic.TimingDiagram(
            {'signal': [
                {'name': 'CLK', 'wave': 'P....'},
                {'name': 'D',   'wave': 'x3..x', 'data': ['D valid']},
                {'name': 'Q',   'wave': 'x.3..', 'data': ['Q']}]},
            ygap=.4, grid=False)
    ''',
    "karnaugh_map": '''
        d += logic.Kmap(names='ABCD',
                        truthtable=[('1100', '1'), ('1101', '1'),
                                    ('1111', '1'), ('1110', '1')])
    ''',
}


# **영어 이름으로도 부를 수 있게 한다.** 사용자(2026-09-15): "한국어로 쓰지마.
# 영어로해줘." EDA 판의 말이 영어라 에이전트가 영어 이름을 칠 가능성이 높다 --
# 모르는 이름이라고 돌려보내는 것보다 받아 주는 편이 낫다.
# --- 2차. **전부 그려서 눈으로 확인하고 넣었다**(2026-09-15). 교재 표기를 따른다:
# 소자 라벨은 `elm.Label().at(center)` 로 몸통에 얹고, 게이트 선은 앵커가 있는
# **오른쪽**으로 뺀다. 처음엔 `loc='left'` 라벨이 소자 위에 겹쳐 그림이 뭉개졌다.
본보기["cascode"] = """
    M1 = d.add(elm.AnalogNFet().anchor('source').at((0, 0)))
    d += elm.Label().at(M1.absanchors['center']).label('$M_1$').color('#333')
    d += elm.Ground().at(M1.absanchors['source'])
    d += elm.Line().at(M1.absanchors['gate']).right().length(1.2).label('$V_{IN}$', loc='right')
    M2 = d.add(elm.AnalogNFet().anchor('source').at(M1.absanchors['drain']))
    d += elm.Label().at(M2.absanchors['center']).label('$M_2$').color('#333')
    d += elm.Line().at(M2.absanchors['gate']).right().length(1.2).label('$V_B$', loc='right')
    o = M2.absanchors['drain']
    d += elm.Dot().at(o)
    d += elm.Line().at(o).left().length(1.6).label('$V_{OUT}$', loc='left')
    d += elm.Line().at(o).up().length(0.6)
    d += elm.SourceI().up().label('$I_{BIAS}$')
    d += elm.Vdd().label('$V_{DD}$')
"""

본보기["source_follower"] = """
    M1 = d.add(elm.AnalogNFet().anchor('drain').at((0, 0)))
    d += elm.Label().at(M1.absanchors['center']).label('$M_1$').color('#333')
    d += elm.Line().at(M1.absanchors['drain']).up().length(0.7)
    d += elm.Vdd().label('$V_{DD}$')
    d += elm.Line().at(M1.absanchors['gate']).right().length(1.3).label('$V_{IN}$', loc='right')
    s = M1.absanchors['source']
    d += elm.Dot().at(s)
    d += elm.Line().at(s).left().length(1.7).label('$V_{OUT}$', loc='left')
    d += elm.Line().at(s).down().length(0.6)
    d += elm.SourceI().down().label('$I_{BIAS}$')
    d += elm.Ground()
"""

본보기["common_gate"] = """
    M1 = d.add(elm.AnalogNFet().anchor('source').at((0, 0)))
    d += elm.Label().at(M1.absanchors['center']).label('$M_1$').color('#333')
    d += elm.Line().at(M1.absanchors['gate']).right().length(1.3).label('$V_B$', loc='right')
    s = M1.absanchors['source']
    d += elm.Dot().at(s)
    d += elm.Line().at(s).down().length(0.7)
    d += elm.SourceI().down().label('$I_{IN}$')
    d += elm.Ground()
    dr = M1.absanchors['drain']
    d += elm.Dot().at(dr)
    d += elm.Line().at(dr).left().length(1.7).label('$V_{OUT}$', loc='left')
    d += elm.Line().at(dr).up().length(0.5)
    d += elm.Resistor().up().label('$R_D$')
    d += elm.Vdd().label('$V_{DD}$')
"""

본보기["diff_pair"] = """
    M1 = d.add(elm.AnalogNFet().anchor('source').at((0, 0)))
    d += elm.Label().at(M1.absanchors['center']).label('$M_1$').color('#333')
    M2 = d.add(elm.AnalogNFet().anchor('source').at((4.5, 0)).reverse())
    d += elm.Label().at(M2.absanchors['center']).label('$M_2$').color('#333')
    t1, t2 = M1.absanchors['source'], M2.absanchors['source']
    d += elm.Line().at(t1).to(t2)
    tail = ((t1.x + t2.x) / 2, t1.y)
    d += elm.Dot().at(tail)
    d += elm.Line().at(tail).down().length(0.6)
    d += elm.SourceI().down().label('$I_{SS}$')
    d += elm.Ground()
    d += elm.Line().at(M1.absanchors['gate']).right().length(0.9).label('$V_{IN+}$', loc='top')
    d += elm.Line().at(M2.absanchors['gate']).left().length(0.9).label('$V_{IN-}$', loc='top')
    for M, nm, side in ((M1, '$V_{O-}$', 'left'), (M2, '$V_{O+}$', 'right')):
        dr = M.absanchors['drain']
        d += elm.Dot().at(dr)
        d += elm.Line().at(dr).up().length(0.4)
        d += elm.Resistor().up().label('$R_D$')
        d += elm.Vdd().label('$V_{DD}$')
        d += elm.Line().at(dr).theta(180 if side == 'left' else 0).length(1.3).label(nm, loc=side)
"""

본보기["transmission_gate"] = """
    MN = d.add(elm.AnalogNFet().anchor('source').at((0, 0)))
    d += elm.Label().at((-0.55, 0.83)).label('$M_N$').color('#333')
    MP = d.add(elm.AnalogPFet().anchor('source').at((4.2, 1.6667)))
    d += elm.Label().at((3.65, 0.83)).label('$M_P$').color('#333')
    low = [MN.absanchors['source'], (0, -1.0), (4.2, -1.0), MP.absanchors['drain']]
    high = [MN.absanchors['drain'], (0, 2.7), (4.2, 2.7), MP.absanchors['source']]
    for path in (low, high):
        for a, b in zip(path, path[1:]):
            d += elm.Line().at(a).to(b)
    d += elm.Dot().at((2.1, -1.0))
    d += elm.Line().at((2.1, -1.0)).down().length(0.8).label('$IN$', loc='bottom')
    d += elm.Dot().at((2.1, 2.7))
    d += elm.Line().at((2.1, 2.7)).up().length(0.8).label('$OUT$', loc='top')
    d += elm.Line().at(MN.absanchors['gate']).right().length(0.8).label('$CLK$', loc='right')
    d += elm.Line().at(MP.absanchors['gate']).right().length(0.8).label('$\\\\overline{CLK}$', loc='right')
"""


별칭 = {
    # **표준 이름은 영어다**(사용자 2026-09-15: "스키매틱은 대학 교재 혹은 현업에서
    # 사용되는 형식을 따르도록 모든 용어 명칭 개념들을 영어로"). 한국어로 물어도
    # 찾히게 한글을 별칭으로 남긴다.
    "전류미러": "current_mirror", "cm": "current_mirror", "mirror": "current_mirror",
    "CMOS인버터": "cmos_inverter", "inverter": "cmos_inverter",
    "공통소스": "common_source_amp", "cs_amp": "common_source_amp",
    "common_source": "common_source_amp", "cs": "common_source_amp",
    "RC저역": "rc_lowpass", "rc_filter": "rc_lowpass", "rc": "rc_lowpass",
    "CMOS낸드": "cmos_nand2", "nand": "cmos_nand2", "cmos_nand": "cmos_nand2",
    "논리게이트": "logic_gates", "gates": "logic_gates",
    "셋업홀드": "setup_hold", "timing": "setup_hold",
    "카르노맵": "karnaugh_map", "kmap": "karnaugh_map", "karnaugh": "karnaugh_map",
    "캐스코드": "cascode", "소스팔로워": "source_follower", "sf": "source_follower",
    "공통게이트": "common_gate", "cg": "common_gate",
    "차동쌍": "diff_pair", "differential_pair": "diff_pair",
    "전송게이트": "transmission_gate", "tg": "transmission_gate",
}
영어이름 = 별칭          # 옛 이름. 부르는 데가 있어 남긴다


def 본보기그리기(이름: str, 경로: str = None) -> dict:
    """본보기 하나를 그린다. 이름을 모르면 아는 이름을 알려준다."""
    이름 = (이름 or "").strip()
    이름 = 별칭.get(이름, 별칭.get(이름.lower(), 이름))
    코드 = 본보기.get(이름)
    if 코드 is None:
        # **정식 이름을 알려준다.** 예전에는 별칭 목록을 보여 줬는데, 그러면 정작
        # 본보기의 진짜 이름은 어디에도 안 나온다. 정식 이름은 영어다(사용자 2026-09-15).
        return 됐나틀(False, None,
                    "모르는 본보기다 -- 아는 것(정식 이름은 영어다): "
                    + " · ".join(f"`{k}`" for k in 본보기)
                    + ". 한국어 별칭도 받는다(전류미러 · 차동쌍 · 카르노맵 ...)")
    return 그리기(코드, 경로)
