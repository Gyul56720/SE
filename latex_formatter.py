r"""LaTeX 수식을 **디스코드에서 실제로 보이게** 만든다. LaTeX 설치가 필요 없다.

사용자(2026-09-14): "letax 가 설치되어 있지 않는데, letax 로 방정식 깔끔하게 보게 할 수
있어? 디스코드라서 어쩔 수 없나?"

## 첫 판이 틀렸던 자리 -- 적어 둔다

처음 이 파일은 수식을 ```` ```math ```` 코드 펜스로 감쌌다. **디스코드는 그것을 수식으로
렌더링하지 않는다** -- ```` ```math ```` 는 GitHub/GitLab 것이고, 디스코드에서는 그냥
고정폭 블록으로 `E = mc^2` 글자 그대로 보인다. 그리고 그때 붙은 검사는

    self.assertIn("E = mc^2", res)

였는데, 이건 **함수가 입력을 그대로 돌려줘도 통과한다**(실측: 항등·쓰레기붙이기·줄바꿈
셋 다 통과). 감싼다는 것을 한 번도 확인하지 않았다. 그래서 "됐다" 는 초록불이 떴는데
부탁은 하나도 안 풀려 있었다.

## 지금 하는 두 가지 -- LaTeX 없이

    유니코드(수식)   sympy 로 파싱해 **글자 그림**으로 그린다.  ```` ``` ```` 안에 넣으면
                    고정폭이라 분수선·근호가 줄이 맞는다. 디스코드에서 바로 보인다
    그림(수식)       matplotlib 의 **mathtext** 로 PNG 를 그린다. `text.usetex=False` 라
                    LaTeX 설치가 필요 없다 -- 진짜 조판된 수식이 이미지로 나온다

봇은 이미 `discord.File` 로 파일을 보낸다(`discord_bot_server.py`). 그림 쪽이 "깔끔한
수식" 에 가장 가깝고, 유니코드 쪽은 **아무것도 설치 안 해도** 되는 대신 단순한 식에서만
곱게 나온다.

## 셋으로 답한다 -- 못 하면 못 한다고 한다

`유니코드`·`그림` 은 `{됐나, ..., 왜}` 를 준다. 딸린 것이 없으면 `됐나=False` 이고 `왜` 에
무엇이 없는지 적는다. **조용히 원문을 돌려주고 성공한 척하지 않는다** -- 그러면 이 파일이
처음에 한 잘못을 되풀이하는 것이다.

    유니코드: sympy + antlr4-python3-runtime   (requirements.txt)
    그림    : matplotlib                        (requirements.txt)
"""

from __future__ import annotations

import os
import tempfile

코드펜스 = "```"


def 유니코드(수식: str) -> dict:
    r"""LaTeX 를 **글자 그림**으로. {됐나, 글, 왜}.

    `\frac{x^2+1}{\sqrt{y}}` ->

         2
        x  + 1
        ──────
          √y

    줄이 맞아야 읽히므로 부르는 쪽은 고정폭(코드 블록)에 넣어야 한다 -- `디스코드글` 이
    그렇게 한다."""
    if not (수식 or "").strip():
        return {"됐나": False, "글": None, "왜": "빈 수식이다"}
    try:
        import sympy
        from sympy.parsing.latex import parse_latex
    except ImportError as e:
        return {"됐나": False, "글": None, "왜": f"sympy 가 없다: {e}"}
    try:
        식 = parse_latex(수식)
    except Exception as e:                                          # noqa: BLE001
        # antlr4 가 없으면 여기서 ImportError 가 난다 -- 파싱 실패와 **같이 잡되 까닭은 나눈다**
        왜 = f"{type(e).__name__}: {str(e)[:120]}"
        if "antlr" in str(e).lower():
            왜 += " -- `pip install antlr4-python3-runtime==4.11`"
        return {"됐나": False, "글": None, "왜": f"LaTeX 를 못 읽었다 ({왜})"}
    try:
        글 = sympy.pretty(식, use_unicode=True)
    except Exception as e:                                          # noqa: BLE001
        return {"됐나": False, "글": None, "왜": f"글자 그림을 못 그렸다: {type(e).__name__}: {e}"}
    return {"됐나": True, "글": 글, "왜": ""}


def 그림(수식: str, 경로: str = None, 글자크기: int = 28, dpi: int = 200) -> dict:
    r"""LaTeX 를 **PNG** 로. {됐나, 경로, 왜}.

    matplotlib 의 mathtext 를 쓴다 -- `text.usetex=False` 이므로 **LaTeX 설치가 필요 없다**
    (실측 2026-09-14: usetex False 로 681x256 PNG 가 나왔다). mathtext 는 LaTeX 의
    부분집합이라 `\frac`·`\sqrt`·`\int`·`\sum`·위첨자·아래첨자는 되고, 패키지를 쓰는
    명령(`\usepackage` 류)은 안 된다.

    수식은 `$...$` 로 감싼다 -- 이미 감겨 있으면 그대로 둔다."""
    if not (수식 or "").strip():
        return {"됐나": False, "경로": None, "왜": "빈 수식이다"}
    try:
        import matplotlib
        matplotlib.use("Agg")                                       # 화면 없는 서버에서 돈다
        import matplotlib.pyplot as plt
    except ImportError as e:
        return {"됐나": False, "경로": None,
                "왜": f"matplotlib 이 없다: {e} -- `pip install matplotlib`"}

    글 = 수식.strip()
    if not (글.startswith("$") and 글.endswith("$")):
        글 = f"${글}$"
    경로 = 경로 or os.path.join(tempfile.mkdtemp(prefix="수식-"), "수식.png")
    os.makedirs(os.path.dirname(경로) or ".", exist_ok=True)
    그림판 = plt.figure(figsize=(0.01, 0.01))
    try:
        그림판.text(0, 0, 글, fontsize=글자크기)
        그림판.savefig(경로, dpi=dpi, bbox_inches="tight", pad_inches=0.25)
    except Exception as e:                                          # noqa: BLE001
        return {"됐나": False, "경로": None,
                "왜": f"mathtext 가 못 그렸다: {type(e).__name__}: {str(e)[:120]}"}
    finally:
        plt.close(그림판)
    if not (os.path.isfile(경로) and os.path.getsize(경로) > 0):
        return {"됐나": False, "경로": None, "왜": "파일이 안 생겼거나 비었다"}
    return {"됐나": True, "경로": 경로, "왜": ""}


def 디스코드글(수식: str) -> str:
    r"""디스코드에 **그대로 붙여 넣을** 글. 이미지가 아니라 글로 보낼 때 쓴다.

    ```` ```math ```` 를 **안 쓴다** -- 디스코드가 그것을 수식으로 안 그린다(이 파일 머리말).
    쓰는 것은 맨 코드 펜스이고, 안에는 `유니코드` 가 그린 글자 그림이 들어간다. 못 그리면
    **원문을 그대로 넣되 그렇다고 적는다** -- 조용히 원문을 수식인 척 내놓지 않는다."""
    r = 유니코드(수식)
    if r["됐나"]:
        return f"{코드펜스}\n{r['글']}\n{코드펜스}"
    return (f"{코드펜스}\n{수식}\n{코드펜스}\n"
            f"(수식으로 못 그렸다 -- {r['왜']})")


def format_latex(formula: str) -> str:
    """뒤호환. 처음 판의 이름이다 -- `디스코드글` 을 부른다."""
    return 디스코드글(formula)


# ------------------------------------------------------------------ 답 안의 수식
# 사용자(2026-09-15): "풀이는 latex 를 제공해줘야해." 그리고 곧바로: **"letax 깨졋어."**
#
# ## 첫 판이 왜 깨졌나 -- sympy 를 표시에 썼다
#
# 사용자가 붙여 준 실제 출력이 진단이었다. 두 가지가 났다.
#
# *하나 -- 조용히 뜻이 바뀌었다.* `\iint_{V} e^{2x-y}(2x+y)\,dA` 를 sympy 에 넣으면
#
#     dA⋅e^{2⋅x - y}⋅iint_{V}(2⋅x + y)
#
# 가 나온다. **이중적분이 곱셈이 됐다** -- `\iint` 와 `dA` 를 그냥 기호로 읽고 곱한
# 것이다. 그런데 `됐나=True` 다. 틀린 답을 자신 있게 낸다. 이 저장소의 말로,
# **검사하지 않은 초록불**이 수식에서 난 꼴이다.
#
# *둘 -- 못 읽으면 날 LaTeX 를 뱉었다.* `\quad` · `\begin{pmatrix}` · `\to` 가 든 식은
# 파싱이 실패해서 `\det \begin{pmatrix} 2 & -1 \\ ...` 가 코드 펜스 안에 그대로 나갔다.
#
# ## 그래서 **읽는 것(sympy)** 이 아니라 **그리는 것(mathtext)** 을 쓴다
#
# 우리는 수식을 **이해할 필요가 없다. 보여 주기만 하면 된다.** sympy 는 파서라 모르는
# 것을 만나면 지어내거나 죽고, matplotlib 의 mathtext 는 조판기라 모양만 그린다.
# 실측(사용자가 준 그 식들로): sympy 는 6개 중 1개를 **틀리게** 그리고 3개가 실패,
# mathtext 는 아래 `손질` 을 거치면 **6개 중 5개**가 제대로 그려진다(못 그리는 것은
# `\begin{pmatrix}` 하나인데 그것도 `손질` 이 읽을 수 있는 꼴로 바꾼다).
#
# `유니코드()` 는 남겨 둔다 -- 한 식을 사람이 콕 집어 물을 때는 여전히 쓸모가 있다.
# **다만 답을 다듬는 데는 안 쓴다.**
import re as _re

_덩어리 = _re.compile(r"\$\$(.+?)\$\$", _re.S)
_인라인 = _re.compile(r"(?<!\$)\$([^$\n]+?)\$(?!\$)")
_그림상한 = 8          # 한 풀이에 세우는 식이 여럿이다. 넷은 모자랐다


def _행렬풀기(글: str) -> str:
    r"""`\begin{pmatrix} a & b \\ c & d \end{pmatrix}` 를 mathtext 가 아는 꼴로.

    mathtext 에는 행렬 환경이 없다 -- 그대로 두면 식 전체가 안 그려진다. 괄호 안에
    행을 `;` 로 갈라 넣으면 **뜻이 살아 있고 그려진다.** 조판은 덜 곱지만, 날
    `\begin{pmatrix}` 가 화면에 나가는 것보다 훨씬 낫다.
    """
    def 바꾸기(m):
        # **열은 쉼표로 가른다.** 처음에는 공백(`\ \ `)으로 했는데 mathtext 가 그것을
        # 뭉개서 `2 & -1` 이 `2 - 1`(뺄셈!) 로, `2 & 1` 이 `21` 로 보였다 -- 뜻이 바뀐
        # 그림은 안 그린 것보다 나쁘다(실측 2026-09-15, 눈으로 확인).
        속 = m.group(2).strip()
        행 = [",\\ ".join(c.strip() for c in r.split("&") if c.strip())
             for r in _re.split(r"\\\\", 속) if r.strip()]
        여 = {"p": ("(", ")"), "b": ("[", "]"), "v": ("|", "|"), "V": (r"\|", r"\|")}
        왼, 오 = 여.get(m.group(1), ("(", ")"))
        return r"\left" + 왼 + (r";\ \ ".join(행)) + r"\right" + 오
    return _re.sub(r"\\begin\{([pbvV])matrix\}(.+?)\\end\{[pbvV]matrix\}",
                   바꾸기, 글, flags=_re.S)


def 손질(글: str) -> str:
    r"""mathtext 가 모르는 몇 가지를 아는 꼴로 바꾼다. **뜻은 안 바꾼다.**

    실측으로 고른 것들이다 -- 이것만으로 사용자가 준 식 여섯 중 다섯이 그려졌다.
    """
    글 = _행렬풀기(글 or "")
    글 = _re.sub(r"\\(qquad|quad)(?![A-Za-z])", "  ", 글)
    글 = _re.sub(r"\\[;:!,]", " ", 글)            # 가는 공백들
    글 = 글.replace("\\ ", " ")
    글 = _re.sub(r"\\[td]frac(?![A-Za-z])", r"\\frac", 글)
    글 = _re.sub(r"\\le(?![A-Za-z])", r"\\leq", 글)
    글 = _re.sub(r"\\ge(?![A-Za-z])", r"\\geq", 글)
    글 = _re.sub(r"\\to(?![A-Za-z])", r"\\rightarrow", 글)
    글 = _re.sub(r"\\(text|mathrm|mathbf|operatorname)\{([^{}]*)\}", r"\\mathit{\2}", 글)
    return 글.strip()


# 줄 안 수식은 그림으로 안 뺀다 -- 한 문단에 그림 열 장이 끼면 그것도 못 읽는다.
# 대신 **글자로 바꿔** 산문에 그대로 둔다. 뜻을 바꾸지 않는 치환만 쓴다.
_글자로 = [(r"\left", ""), (r"\right", ""), (r"\,", ""), (r"\;", " "), (r"\!", ""),
        (r"\cdot", "·"), (r"\times", "×"), (r"\pm", "±"), (r"\mp", "∓"),
        (r"\leq", "≤"), (r"\geq", "≥"), (r"\le", "≤"), (r"\ge", "≥"), (r"\neq", "≠"),
        (r"\approx", "≈"), (r"\rightarrow", "→"), (r"\to", "→"), (r"\infty", "∞"),
        (r"\partial", "∂"), (r"\nabla", "∇"), (r"\int", "∫"), (r"\iint", "∬"),
        (r"\sum", "Σ"), (r"\prod", "∏"), (r"\sqrt", "√"), (r"\in", "∈"),
        (r"\alpha", "α"), (r"\beta", "β"), (r"\gamma", "γ"), (r"\delta", "δ"),
        (r"\epsilon", "ε"), (r"\theta", "θ"), (r"\lambda", "λ"), (r"\mu", "μ"),
        (r"\pi", "π"), (r"\rho", "ρ"), (r"\sigma", "σ"), (r"\tau", "τ"),
        (r"\phi", "φ"), (r"\omega", "ω"), (r"\Delta", "Δ"), (r"\Omega", "Ω"),
        (r"\quad", " "), (r"\qquad", "  ")]
_위 = str.maketrans("0123456789+-n()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ⁿ⁽⁾")
_아래 = str.maketrans("0123456789+-()", "₀₁₂₃₄₅₆₇₈₉₊₋₍₎")


def 읽기쉽게(식: str) -> str:
    r"""줄 안 수식을 **글자로.** `$I_D$` -> `I_D`, `$x^2$` -> `x²`, `$\mu_n$` -> `μ_n`.

    못 바꾸는 것은 그대로 둔다 -- **지우지 않는다.** 날 `\frac{a}{b}` 가 남는 것이
    수식이 통째로 사라지는 것보다 낫다(이 파일이 처음에 한 잘못이 '못 한 것을 한 척' 이다).
    """
    글 = 식 or ""
    글 = _re.sub(r"\\[td]?frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", 글)
    글 = _re.sub(r"\\sqrt\{([^{}]+)\}", r"√(\1)", 글)
    for a, b in _글자로:
        글 = 글.replace(a, b)
    글 = _re.sub(r"\^\{([0-9n+\-()]+)\}", lambda m: m.group(1).translate(_위), 글)
    글 = _re.sub(r"\^([0-9n])(?![0-9A-Za-z])", lambda m: m.group(1).translate(_위), 글)
    글 = _re.sub(r"_\{([0-9+\-()]+)\}", lambda m: m.group(1).translate(_아래), 글)
    글 = _re.sub(r"_\{([A-Za-z]{1,4})\}", r"_\1", 글)
    # **남은 묶음은 괄호로 바꾼다. 그냥 지우면 뜻이 바뀐다.**
    # 실측 2026-09-15: `e^{2x-y}` 가 `e^2x-y` 가 됐다 -- 지수가 `2` 하나로 읽힌다.
    # 괄호로 남기면 `e^(2x-y)` 라 사람이 제대로 읽는다.
    글 = _re.sub(r"([\^_])\{([^{}]*)\}", r"\1(\2)", 글)
    글 = 글.replace("{", "").replace("}", "")
    return _re.sub(r"\s{2,}", " ", 글).strip()


def 답다듬기(글: str, 그림도: bool = True) -> dict:
    r"""봇의 답에 박힌 LaTeX 를 **보이게** 바꾼다. {글, 그림들, 셈}.

    `$$...$$` (세우는 식) -> **PNG**. mathtext 가 조판한다.
    `$...$`  (줄 안 수식) -> **글자**. 그림으로 빼면 문단이 그림투성이가 된다.

    **sympy 를 안 쓴다** -- 이 함수의 머리말에 적힌 까닭이다.
    """
    글 = 글 or ""
    그림들, 셈 = [], {"덩어리": 0, "줄안": 0, "그림": 0, "못그림": 0}

    def _덩(m):
        셈["덩어리"] += 1
        수식 = m.group(1).strip()
        if 그림도 and len(그림들) < _그림상한:
            r = 그림(손질(수식))
            if r["됐나"]:
                그림들.append(r["경로"])
                셈["그림"] += 1
                return ""                      # 그림으로 나가므로 글에서는 뺀다
        셈["못그림"] += 1
        # 못 그려도 **날 LaTeX 를 내보내지 않는다** -- 사용자가 본 그 화면이 그것이다.
        return f"\n{코드펜스}\n{읽기쉽게(수식)}\n{코드펜스}\n"

    def _인(m):
        셈["줄안"] += 1
        바뀐 = 읽기쉽게(m.group(1).strip())
        if not 바뀐:
            셈["못그림"] += 1
            return m.group(0)
        return f"`{바뀐}`"

    글 = _덩어리.sub(_덩, 글)
    글 = _인라인.sub(_인, 글)
    return {"글": _re.sub(r"\n{3,}", "\n\n", 글).strip(), "그림들": 그림들, "셈": 셈}
