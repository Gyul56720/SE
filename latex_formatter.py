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
