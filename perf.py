#!/usr/bin/env python3
r"""**성능개선** -- 같은 입력으로 되풀이 돌려 **실제로 빨라진 변경만** 받아들인다.

    성능개선()
        지금 프로그램 P
              ↓
        후보 P'              (여기서 만들지 않는다. 받는다)
              ↓
        V(P')               깨지지 않았는가
              ↓
        같은 워크로드         같은 기계 · 같은 입력 · 번갈아 돌린다
              ↓
        t(P') < t(P) ?      중앙값으로 견준다
              ↓
          ACCEPT / REJECT

    J(P) = 1 / median(t(P))       크면 좋다

## 최적화 알고리즘이 아니다

무엇을 최적화할지 여기서 정하지 않는다. **"같은 프로그램을 같은 입력으로 되풀이 돌리고,
실행시간을 견줘 더 빠른 변경만 채택한다."** 그것만 한다.

## 빠져나갈 구멍을 둘 막는다

**① 깨뜨려서 빠른 것.** 검사를 지우거나 일을 덜 하면 언제나 빠르다. 그래서 V 가 먼저다 --
V 가 빨갛면 시간을 아예 재지 않는다(재면 그 수가 근거처럼 보인다).

**② 잡음을 개선이라 부르는 것.** 같은 판을 두 번 재도 수가 다르다. 그래서 바탕의 표본을
홀짝으로 갈라 **바탕 자신과 견준 차이**를 잡음 바닥으로 쓴다(A/A 대조, 공짜다).

    |Δ| <= 잡음바닥   ->  **REJECT(못잼).** 빨라졌다고 말하지 않는다

그리고 번갈아 돌린다(A B A B ...) -- 기계 부하가 몇 분 사이에 흐르므로, A 를 다 돌린 뒤
B 를 다 돌리면 그 흐름이 통째로 Δ 가 된다.

    python3 perf.py --워크로드목록
    python3 perf.py --재기 관문                     지금 HEAD 를 잰다
    python3 perf.py --결정 --후보 <갈래|커밋>        ACCEPT/REJECT (적는다)
    python3 perf.py --보고
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
성능경로 = "falsegreen/성능.jsonl"
기본반복 = 7                  # 홀수 -- 중앙값이 표본 하나가 되게
워크로드시한초 = 600
맑은환경 = {"PYTHONDONTWRITEBYTECODE": "1"}

# 워크로드는 **ASTRA 가 실제로 늘 돌리는 것**이어야 한다. 그리고 결정적이어야 한다 --
# 망·LLM·시계에 매인 것은 여기 두지 않는다(그 흔들림이 Δ 를 덮는다).
워크로드들 = {
    "관문": {"argv": ["python3", "-B", "gatekeeper.py"],
           "왜": "커밋마다 돈다. 여기가 빨라지면 **모든 커밋이** 빨라진다"},
    "변형생성": {"argv": ["python3", "-B", "-c",
                     "import mutate, subprocess, pathlib\n"
                     "r = subprocess.run(['git','ls-files','*.py'],capture_output=True,text=True)\n"
                     "fs = [x for x in r.stdout.split() if not x.startswith('tests/')][:40]\n"
                     "n = 0\n"
                     "for f in fs:\n"
                     "    s = pathlib.Path(f).read_text(encoding='utf-8',errors='replace')\n"
                     "    import rehearsal\n"
                     "    for 이름 in list(rehearsal._함수자리(s))[:6]:\n"
                     "        n += len(mutate.변형들(s, 이름))\n"
                     "print(n)"],
             "왜": "사냥의 알맹이. AST 를 읽어 변형을 짓는다 -- 순수 CPU 이고 결정적이다"},
    "검사고르기": {"argv": ["python3", "-B", "-c",
                      "import mutate, subprocess\n"
                      "from pathlib import Path\n"
                      "r = subprocess.run(['git','ls-files','*.py'],capture_output=True,text=True)\n"
                      "fs = [x for x in r.stdout.split() if not x.startswith('tests/')]\n"
                      "print(sum(len(mutate._검사고르기(Path('.'), f)) for f in fs))"],
              "왜": "파일마다 어느 검사를 돌릴지 고른다. 파일 수에 제곱으로 붙는 자리다"},
    "요약": {"argv": ["python3", "-B", "-c", "import mutate; print(mutate.요약()['잰변형'])"],
           "왜": "원장 전체를 읽어 한 줄로 줄인다. 원장이 커지면 여기가 먼저 느려진다"},
}


def _기계() -> dict:
    r"""**어느 기계에서 쟀나.** 실측 2026-09-13: 같은 워크로드가 이 컨테이너에서 13.41초,
    VM 에서 9.94초였다. 기계를 안 적으면 원장이 두 기계를 섞어 놓고 **아무 표시도 안 한다** --
    나중에 그 줄들을 나란히 읽으면 없던 개선·없던 퇴화가 보인다."""
    import platform
    return {"이름": platform.node(), "코어": os.cpu_count()}


def _git(판: Path, *a) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(판), *a], capture_output=True, text=True)


def 한번(판: Path, argv: "list[str]", 시한초: int = 워크로드시한초) -> "tuple[float | None, int, str]":
    """한 번 돌린 벽시계 초. 끝값이 0 이 아니면 시간을 **안 돌려준다**(None) -- 터진 것의
    시간은 성능이 아니다."""
    env = {**os.environ, "PYTHONPATH": str(판), **맑은환경}
    t0 = time.perf_counter()
    try:
        r = subprocess.run(argv, cwd=str(판), env=env, capture_output=True, text=True,
                           timeout=시한초)
    except subprocess.TimeoutExpired:
        return None, 124, "Timeout"
    걸림 = time.perf_counter() - t0
    글 = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        return None, r.returncode, 글[-400:]
    return 걸림, 0, 글[-200:]


def 잰다(판: Path, argv: "list[str]", 반복: int = 기본반복) -> dict:
    """같은 것을 `반복`번 돌린다. {표본, 중앙값, 최소, 최대, 터진것, 까닭}."""
    표본, 터짐, 까닭 = [], 0, ""
    for _ in range(max(1, 반복)):
        초, rc, 글 = 한번(판, argv)
        if 초 is None:
            터짐 += 1
            까닭 = 까닭 or f"rc={rc}: {글.strip()[:160]}"
            continue
        표본.append(round(초, 4))
    return {"표본": 표본, "중앙값": (round(statistics.median(표본), 4) if 표본 else None),
            "최소": (min(표본) if 표본 else None), "최대": (max(표본) if 표본 else None),
            "터진것": 터짐, "까닭": 까닭}


def 흔들림(표본: "list[float]") -> "float | None":
    """MAD -- 중앙값에서의 중앙 거리. 표본이 3개 미만이면 None(**모르면 모른다고 한다**)."""
    if len(표본) < 3:
        return None
    m = statistics.median(표본)
    return round(statistics.median([abs(x - m) for x in 표본]), 4)


def 짝차(바탕표본: "list[float]", 후보표본: "list[float]") -> "list[float]":
    """짝마다 (후보 - 바탕). 음수면 그 짝에서 후보가 빨랐다."""
    return [round(b - a, 4) for a, b in zip(바탕표본 or [], 후보표본 or [])]


def 짝Δ(바탕표본: "list[float]", 후보표본: "list[float]") -> "float | None":
    """**짝차의 중앙값.** 기계 흐름이 짝 안에서 상쇄되므로 이것이 이득의 추정값이다."""
    차 = 짝차(바탕표본, 후보표본)
    return round(statistics.median(차), 4) if 차 else None


def 잡음바닥(바탕표본: "list[float]", 후보표본: "list[float]" = None) -> "float | None":
    r"""**이만큼의 Δ 는 빨라진 것이라 말하지 않는다.** 짝차 자신의 흔들림(MAD).

    두 번 틀렸다. 적어 둔다.

    **① 홀짝 중앙값 차.** 검사가 깨뜨렸다 -- 같은 프로그램 둘(0.10 · 0.10초)에서 Δ=-0.0002
    인데 홀짝 차가 0.0001 이어서 ACCEPT 가 났다. 홀짝 차는 *한 계열 안의 일치*라서 계열
    **사이**보다 체계적으로 작다.

    **② MAD(바탕) + MAD(후보).** 실측이 깨뜨렸다 -- 관문 후보가 **14짝 전부**에서 빨랐는데
    (p = 0.006%) Δ -0.364 < 바닥 0.509 로 REJECT 가 났다. 긴 판에서 기계 부하가 흘러
    (바탕 13.78~14.80초) 두 MAD 가 같이 부풀었는데, **그 흐름은 짝 안에서 상쇄된다.**

        짝차 = [-0.40, -0.41, -0.31, -0.59, -0.80, ... ]   전부 음수
        짝 중앙값 -0.374  ·  **짝차의 MAD 0.063**  ->  5.9배. 구별된다
        안 짝으로: 0.322 + 0.187 = 0.509  <- 기계 흐름이 그대로 들어 있다

    방향(부호검정)은 짝으로 보면서 크기는 안 짝으로 봤다 -- **같은 실수를 다른 항에서**
    되풀이한 것이다. 문턱을 낮춘 것이 아니라 두 항을 같은 근거 위에 올린 것이다: 짝 흔들림이
    큰데 계열 흔들림이 작은 경우에는 이 기준이 **더** 엄하다.

    짝이 안 맞으면(한쪽이 터져 수가 다르면) 옛 꼴로 돌아간다 -- 짝이 없으니 그럴 수밖에 없다."""
    if 바탕표본 and 후보표본 and len(바탕표본) == len(후보표본):
        return 흔들림(짝차(바탕표본, 후보표본))
    a = 흔들림(바탕표본 or [])
    if a is None:
        return None
    b = 흔들림(후보표본 or []) if 후보표본 else 0.0
    return round(a + (b if b is not None else 0.0), 4)


부호문턱 = 0.01              # 부호검정 p 가 이 아래여야 빨라졌다고 한다 (한쪽꼬리)
짝최소 = 3


def 부호검정p(이김: int, 짝: int) -> "float | None":
    r"""**이만큼 쏠리는 것이 우연일 확률.** P(X >= 이김 | p=0.5), 한쪽꼬리 이항 정확검정.

        7/7 -> 0.78%    6/7 -> 6.25%    11/12 -> 0.32%    6/6 -> 1.56%

    **실측 2026-09-13: "짝 전부 이겨야 한다" 는 규칙은 임의적이었다.** 관문 후보가 6/7 로
    나왔을 때 그 규칙은 REJECT 를 냈는데, 그 거절은 **우연히 옳았다**(6/7 은 p=6.25% 로
    실제로 못 미친다). 하지만 규칙이 n 을 안 보므로 6/6(p=1.56%)도 받고 11/12(p=0.32%)는
    버렸다. p 를 직접 세면 문턱이 하나가 되고, 못 넘었을 때 **몇 짝이 더 필요한지도** 말해 줄 수 있다."""
    if 짝 < 짝최소 or 이김 < 0 or 이김 > 짝:
        return None
    from math import comb
    return sum(comb(짝, k) for k in range(이김, 짝 + 1)) / (2 ** 짝)


def 몇짝이면(이김: int, 짝: int, 문턱: float = 부호문턱, 한계: int = 60) -> "int | None":
    """지금 승률이 그대로 간다면 **몇 짝에서** 문턱을 넘나. 못 넘으면 None."""
    if 짝 <= 0:
        return None
    비 = 이김 / 짝
    for n in range(짝 + 1, 한계 + 1):
        pp = 부호검정p(int(round(비 * n)), n)
        if pp is not None and pp <= 문턱:
            return n
    return None


def 짝이김(바탕표본: "list[float]", 후보표본: "list[float]") -> "tuple[int, int]":
    """**짝마다 누가 빨랐나.** (후보가 이긴 짝 수, 짝 수).

    `견주기` 는 한 회차에 바탕과 후보를 **잇따라** 돌린다 -- 그래서 i번째 둘은 같은 기계
    상태에서 난 **짝**이다. 짝으로 보면 기계 부하의 흐름이 양쪽에 똑같이 얹혀 상쇄된다."""
    짝 = list(zip(바탕표본, 후보표본))
    return sum(1 for a, b in 짝 if b < a), len(짝)


def 짝으로갈렸나(바탕표본: "list[float]", 후보표본: "list[float]",
           문턱: float = 부호문턱) -> bool:
    r"""**쏠림이 우연이라고 보기 어려운가** -- 부호검정 p <= 문턱.

    **실측 2026-09-13: 처음에는 짝을 안 보고 `max(후보) < min(바탕)`(분포 갈림)을 요구했다.**
    그랬더니 관문 13.94 -> 13.64초(2.1% · **일곱 짝 전부 후보가 빨랐다**)를 REJECT 했다 --
    4·5회차에 기계 부하가 올라가 양쪽이 같이 느려져 *짝이 아닌* 최대·최소가 겹쳤다. 번갈아
    돌려 짝을 만들어 놓고 **짝 정보를 버린 것**이 잘못이었다."""
    이김, 짝 = 짝이김(바탕표본, 후보표본)
    pp = 부호검정p(이김, 짝)
    return pp is not None and pp <= 문턱


def 갈렸나(바탕표본: "list[float]", 후보표본: "list[float]") -> bool:
    """짝이 안 맞을 때(한쪽이 터져 표본 수가 다를 때) 쓰는 보조 길 -- 분포가 아예 갈렸나."""
    if len(바탕표본) < 3 or len(후보표본) < 3:
        return False
    return max(후보표본) < min(바탕표본)


def 견주기(바탕판: Path, 후보판: Path, argv: "list[str]", 반복: int = 기본반복,
        말하기=None) -> dict:
    """**번갈아** 돌려 둘을 잰다(A B B A ...). 기계 부하가 흐르는 것을 Δ 로 읽지 않게."""
    말 = 말하기 or (lambda s: print(s, flush=True))
    a표본, b표본, 터짐 = [], [], {"바탕": 0, "후보": 0}
    까닭 = {"바탕": "", "후보": ""}
    for i in range(max(2, 반복)):
        차례 = [("바탕", 바탕판, a표본), ("후보", 후보판, b표본)]
        if i % 2:
            차례.reverse()                          # 순서도 번갈아 -- 먼저 도는 쪽의 이득을 없앤다
        for 누구, 판, 통 in 차례:
            초, rc, 글 = 한번(판, argv)
            if 초 is None:
                터짐[누구] += 1
                까닭[누구] = 까닭[누구] or f"rc={rc}: {글.strip()[:160]}"
            else:
                통.append(round(초, 4))
        말(f"[성능] {i + 1}/{반복} 바탕 {a표본[-1] if a표본 else '--'} · "
          f"후보 {b표본[-1] if b표본 else '--'}")
    a중 = round(statistics.median(a표본), 4) if a표본 else None
    b중 = round(statistics.median(b표본), 4) if b표본 else None
    return {"바탕표본": a표본, "후보표본": b표본, "바탕중앙값": a중, "후보중앙값": b중,
            "Δ": (짝Δ(a표본, b표본) if len(a표본) == len(b표본) and a표본
                 else (round(b중 - a중, 4) if (a중 is not None and b중 is not None) else None)),
            "중앙값차": (round(b중 - a중, 4) if (a중 is not None and b중 is not None) else None),
            "짝차": 짝차(a표본, b표본), "잡음바닥": 잡음바닥(a표본, b표본),
            "짝이김": 짝이김(a표본, b표본), "짝으로갈렸나": 짝으로갈렸나(a표본, b표본),
            "부호p": 부호검정p(*짝이김(a표본, b표본)),
            "갈렸나": 갈렸나(a표본, b표본),
            "바탕흔들림": 흔들림(a표본), "후보흔들림": 흔들림(b표본),
            "터진것": 터짐, "까닭": 까닭}


def _바뀐파일들(바탕판: Path, 후보판: Path) -> "list[str]":
    """두 판의 추적되는 .py 가운데 **글이 다른 것**. V 가 무엇을 돌려야 하는지 이것이 정한다."""
    r = _git(후보판, "-c", "core.quotepath=off", "ls-files", "-z", "*.py")
    것 = [x for x in r.stdout.split("\0") if x]
    다른 = []
    for f in 것:
        a, b = 바탕판 / f, 후보판 / f
        try:
            if not a.is_file() or a.read_bytes() != b.read_bytes():
                다른.append(f)
        except OSError:
            다른.append(f)
    return 다른


def 기본V(바탕판: Path, 후보판: Path, 말하기=None) -> "tuple[bool, str]":
    """**깨지지 않았는가.** 바뀐 파일을 재는 검사를 후보 판에서 돌린다.

    검사를 지우거나 일을 덜 하면 언제나 빠르다. V 가 먼저 서야 시간이 뜻을 갖는다."""
    import mutate
    말 = 말하기 or (lambda s: None)
    바뀐 = [f for f in _바뀐파일들(바탕판, 후보판) if not f.startswith("tests/")]
    검사 = []
    for f in 바뀐[:12]:
        for t in mutate._검사고르기(후보판, f):
            if t not in 검사:
                검사.append(t)
    if not 검사:
        return False, (f"바뀐 파일 {len(바뀐)}개를 재는 검사를 못 찾았다 -- "
                       "**V 를 못 쟀으므로 받아들이지 않는다**")
    말(f"[성능] V: 검사 {len(검사)}개 ({', '.join(검사[:4])})")
    빨강, 어디, 글 = mutate._돌려보기(후보판, 검사)
    if 빨강:
        return False, f"{어디} 가 빨갛다: {글.strip().splitlines()[-1][:140] if 글.strip() else ''}"
    return True, f"검사 {len(검사)}개 초록"


def 성능개선(바탕판, 후보판, 워크로드: str = "관문", 반복: int = 기본반복, V=None,
         repo=None, 말하기=None) -> dict:
    r"""**V(P') ∧ (t(P') < t(P) - 잡음바닥)** 일 때만 ACCEPT. 기본은 REJECT.

    돌려주는 것: {결정, 까닭, Δ, J바탕, J후보, 잰것}"""
    말 = 말하기 or (lambda s: print(s, flush=True))
    바탕판, 후보판 = Path(바탕판), Path(후보판)
    일 = 워크로드들.get(워크로드)
    if not 일:
        return {"결정": "REJECT", "까닭": [f"워크로드 '{워크로드}' 를 모른다 "
                                      f"({', '.join(워크로드들)})"], "Δ": None, "잰것": {}}
    V = V or 기본V
    통과, V말 = V(바탕판, 후보판, 말하기=말) if V is 기본V else V(바탕판, 후보판)
    if not 통과:
        # **시간을 아예 안 잰다.** 재면 그 수가 근거처럼 보인다.
        return {"결정": "REJECT", "까닭": [f"V(P') 가 안 섰다: {V말}",
                                      "시간은 재지 않았다 -- 깨진 것이 빠른 것은 개선이 아니다"],
                "Δ": None, "V": False, "잰것": {"V말": V말}}
    잰것 = 견주기(바탕판, 후보판, 일["argv"], 반복, 말하기=말)
    잰것["V말"] = V말
    잰것["워크로드"] = 워크로드
    # **무엇이 다른지 적는다.** 실측 2026-09-13: 후보 판을 떠 놓고 그 뒤에 커밋을 더 해서,
    # 비교가 "G016 다섯 줄" 이 아니라 "커밋 여섯 개 + G016" 이 된 일이 **두 번** 났다. 그것을
    # 출력에서 알 길이 없었다(V 가 고른 검사 수로만 눈치챘다). 오염된 벤치마크는 **수가 나오기
    # 때문에** 더 위험하다 -- 그러니 Δ 옆에 늘 적어 둔다.
    잰것["바뀐파일"] = _바뀐파일들(바탕판, 후보판)
    막힘 = []
    if 잰것["터진것"]["후보"]:
        막힘.append(f"후보가 워크로드에서 {잰것['터진것']['후보']}번 터졌다: {잰것['까닭']['후보'][:120]}")
    if 잰것["터진것"]["바탕"]:
        막힘.append(f"바탕이 워크로드에서 {잰것['터진것']['바탕']}번 터졌다 -- 견줄 바탕이 없다")
    if 잰것["Δ"] is None:
        막힘.append("둘 중 하나를 못 쟀다")
    바닥 = 잰것["잡음바닥"]
    if not 막힘 and 바닥 is None:
        막힘.append(f"잡음 바닥을 못 쟀다(표본 {len(잰것['바탕표본'])}개) -- 반복을 4 이상으로")
    elif not 막힘 and 잰것["Δ"] >= 0:
        막힘.append(f"느려졌거나 같다 (Δ {잰것['Δ']:+.4f}초)")
    elif not 막힘 and abs(잰것["Δ"]) <= 바닥:
        막힘.append(f"**잡음과 구별되지 않는다** (Δ {잰것['Δ']:+.4f}초 · 잡음바닥 {바닥:.4f}초) "
                   "-- 빨라졌다고 말하지 않는다")
    elif not 막힘 and not (잰것["짝으로갈렸나"] or 잰것["갈렸나"]):
        이김, 짝 = 잰것["짝이김"]
        pp = 잰것["부호p"]
        더 = 몇짝이면(이김, 짝)
        막힘.append(f"**쏠림이 우연일 수 있다** (후보가 이긴 짝 {이김}/{짝} · 부호검정 p "
                   f"{(f'{pp:.2%}' if pp is not None else '못 잼')} > 문턱 {부호문턱:.0%})"
                   + (f" -- 같은 승률이면 **짝 {더}개**(`--반복 {더}`)에서 판정된다. "
                      "기준을 낮추지 말고 표본을 늘려라" if 더
                      else " -- 승률이 낮아 표본을 늘려도 안 된다"))
    J바탕 = (round(1 / 잰것["바탕중앙값"], 4) if 잰것["바탕중앙값"] else None)
    J후보 = (round(1 / 잰것["후보중앙값"], 4) if 잰것["후보중앙값"] else None)
    잰것.update({"J바탕": J바탕, "J후보": J후보})
    if 막힘:
        return {"결정": "REJECT", "까닭": 막힘, "Δ": 잰것["Δ"], "V": True,
                "J바탕": J바탕, "J후보": J후보, "잰것": 잰것}
    빠름 = -잰것["Δ"] / 잰것["바탕중앙값"] * 100
    p글 = f"{잰것['부호p']:.2%}" if 잰것["부호p"] is not None else "--"
    return {"결정": "ACCEPT", "V": True, "Δ": 잰것["Δ"], "J바탕": J바탕, "J후보": J후보,
            "까닭": [f"V(P') 섰다: {V말}",
                   f"t {잰것['바탕중앙값']:.4f} -> {잰것['후보중앙값']:.4f}초 "
                   f"({빠름:.1f}% 빠름 · 잡음바닥 {바닥:.4f}초보다 크다 · "
                   f"짝 {잰것['짝이김'][0]}/{잰것['짝이김'][1]} · 부호검정 p {p글})",
                   f"J = 1/t: {J바탕} -> {J후보}"],
            "잰것": 잰것}


def 적기(repo=None, 결과: dict = None, 바탕: str = "", 후보: str = "") -> dict:
    repo = Path(repo or REPO)
    잰 = (결과 or {}).get("잰것") or {}
    때 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # **줄마다 고유 id.** `때` 는 초 단위라 같은 초에 쓰인 줄들이 겹친다(실측: 흉내 검사에서
    # 두 줄이 같은 `때` 를 받아 버림 하나가 둘을 물었다). 쓰는 시점의 줄 수를 붙여 가른다.
    id = f"{때}#{len(기록들(repo)) + 1}"
    줄 = {"id": id, "때": 때, "기계": _기계(),
         "워크로드": 잰.get("워크로드"), "바탕판": 바탕, "후보판": 후보,
         "결정": (결과 or {}).get("결정"), "V": (결과 or {}).get("V"),
         "바탕중앙값": 잰.get("바탕중앙값"), "후보중앙값": 잰.get("후보중앙값"),
         "Δ": (결과 or {}).get("Δ"), "잡음바닥": 잰.get("잡음바닥"),
         "짝이김": 잰.get("짝이김"), "부호p": 잰.get("부호p"),
         "J바탕": (결과 or {}).get("J바탕"), "J후보": (결과 or {}).get("J후보"),
         "바탕표본": 잰.get("바탕표본"), "후보표본": 잰.get("후보표본"),
         "짝차": 잰.get("짝차"), "중앙값차": 잰.get("중앙값차"),
         "바뀐파일": 잰.get("바뀐파일"),
         "까닭": (결과 or {}).get("까닭") or []}
    p = repo / 성능경로
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")
    return 줄


def 기록들(repo=None) -> "list[dict]":
    p = Path(repo or REPO) / 성능경로
    if not p.is_file():
        return []
    out = []
    for 줄 in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if 줄.strip():
            try:
                out.append(json.loads(줄))
            except ValueError:
                continue
    return out


def 보고(repo=None) -> str:
    것 = 기록들(repo)
    if not 것:
        return (f"{성능경로} 가 비어 있다 -- `python3 perf.py --재기 관문` 으로 한 번 재거나 "
                "`--결정 --후보 <갈래>` 로 견줘라")
    # **버림 줄은 무른 대상을 이름으로 가리킨다.** 원장은 덧붙이기만 하므로 ACCEPT 줄을 지우지
    # 않는다 -- 그 대신 `무른것`(그 줄의 `때`)으로 짚는다. 안 그러면 보고가 "ACCEPT 2번" 이라고
    # 말하는데 그 둘 중 하나는 **내가 버린 것**이다(실측 2026-09-13).
    #
    # 처음에는 "바로 앞의 판정" 으로 찾게 했다. **그것도 틀렸다** -- 내 버림 줄은 두 ACCEPT
    # **뒤**에 있어서, 버린 07:13 이 아니라 쓰기로 한 07:22 를 물렀다. 위치로 짚는 것은
    # 원장이 덧붙여지는 동안 뜻이 바뀐다. 이름으로 짚어야 한다.
    무른것 = {str(x.get("무른것")) for x in 것 if x.get("결정") == "버림" and x.get("무른것")}
    이름없는버림 = [x for x in 것 if x.get("결정") == "버림" and not x.get("무른것")]
    무름 = {i for i, x in enumerate(것)
          if (x.get("id") and str(x["id"]) in 무른것)
          or (not x.get("id") and str(x.get("때")) in 무른것)}

    def 수(v, n=4):
        return f"{v:.{n}f}" if isinstance(v, (int, float)) else "--"

    def 기계글(x):
        기 = x.get("기계") or {}
        return f"{str(기.get('이름') or '?')[:9]}/{기.get('코어') or '?'}"

    줄 = [f"{'때':17} {'기계':12} {'바탕':>8} {'후보':>8} {'Δ':>8} {'잡음':>7} {'결정':>8}"]
    처음 = max(0, len(것) - 12)
    for i, x in enumerate(것[처음:], start=처음):
        줄.append(f"{str(x.get('때'))[:16]:17} {기계글(x):12} "
                  f"{수(x.get('바탕중앙값')):>8} {수(x.get('후보중앙값')):>8} "
                  f"{수(x.get('Δ')):>8} {수(x.get('잡음바닥')):>7} {str(x.get('결정')):>8}"
                  + ("   <- 무름(뒤에서 버렸다)" if i in 무름 else ""))
    판정 = [x for i, x in enumerate(것) if i not in 무름 and x.get("결정") in ("ACCEPT", "REJECT")]
    받음 = [x for x in 판정 if x.get("결정") == "ACCEPT"]
    줄.append(f"\n살아 있는 판정 {len(판정)}번 중 ACCEPT {len(받음)}번"
              + (f" (무른 것 {len(무름)}개)" if 무름 else "") + ". "
              + (f"가장 큰 이득 {min((x.get('Δ') or 0) for x in 받음):+.4f}초"
                 if 받음 else "아직 받아들인 것이 없다"))
    if 이름없는버림:
        줄.append(f"버림 줄 {len(이름없는버림)}개에 `무른것` 이 안 적혀 있다 -- **셈에 반영하지 "
                  "못한다**(무엇을 물렀는지 모른다). `--버림 <때>` 로 다시 적어라.")
    기계들 = {기계글(x) for x in 것 if x.get("기계")}
    if len(기계들) > 1:
        줄.append(f"**기계가 {len(기계들)}가지 섞여 있다** ({', '.join(sorted(기계들))}) -- "
                  "다른 기계의 줄끼리 견주지 마라. 한 판정 안의 바탕·후보만 견줄 수 있다.")
    if 것[-1].get("까닭"):
        줄.append("마지막 까닭: " + " · ".join(str(w)[:90] for w in 것[-1]["까닭"][:3]))
    return "\n".join(줄)


def _판꺼내기(repo: Path, 가리킴: str, 말하기=None) -> "tuple[Path, bool]":
    """갈래·커밋이면 임시 판을 꺼낸다. 이미 디렉터리면 그대로 쓴다. (판, 치워야하나)."""
    p = Path(가리킴)
    if p.is_dir():
        return p, False
    판 = Path(tempfile.mkdtemp(prefix="se-성능-"))
    r = _git(repo, "worktree", "add", "--detach", str(판), 가리킴)
    if r.returncode != 0:
        shutil.rmtree(판, ignore_errors=True)
        raise SystemExit(f"'{가리킴}' 으로 판을 못 꺼냈다: {r.stderr.strip()[:200]}")
    return 판, True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="성능개선 -- 실제로 빨라진 변경만 받아들인다")
    ap.add_argument("--워크로드목록", action="store_true")
    ap.add_argument("--재기", default=None, help="이 워크로드로 지금 HEAD 를 잰다")
    ap.add_argument("--결정", action="store_true", help="바탕과 후보를 견줘 ACCEPT/REJECT")
    ap.add_argument("--바탕", default="HEAD", help="갈래·커밋·디렉터리 (기본 HEAD)")
    ap.add_argument("--후보", default=None, help="갈래·커밋·디렉터리")
    ap.add_argument("--워크로드", default="관문")
    ap.add_argument("--반복", type=int, default=기본반복)
    ap.add_argument("--보고", action="store_true")
    ap.add_argument("--버림", default=None,
                    help="그 판정을 무른다 (원장의 `때` 값 -- 앞 글자만 줘도 된다)")
    ap.add_argument("--까닭", default="", help="--버림 과 함께: 왜 버리나")
    a = ap.parse_args(argv)
    if a.버림:
        맞는 = [x for x in 기록들()
              if (str(x.get("id") or x.get("때") or "").startswith(a.버림)
                  or str(x.get("때", "")).startswith(a.버림))
              and x.get("결정") in ("ACCEPT", "REJECT")]
        if not 맞는:
            print(f"'{a.버림}' 로 시작하는 판정 줄이 없다")
            return 2
        if len(맞는) > 1:
            print(f"'{a.버림}' 에 {len(맞는)}줄이 걸린다 -- 더 길게 줘라")
            return 2
        적기(결과={"결정": "버림", "Δ": None, "V": None, "잰것": {},
                 "까닭": [a.까닭 or "(까닭을 안 적었다)"]},
           바탕=맞는[0].get("바탕판", ""), 후보=맞는[0].get("후보판", ""))
        # `무른것` 은 적기가 모르는 칸이라 마지막 줄에 덧붙인다
        import json as _j
        p = REPO / 성능경로
        줄들 = [x for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        마 = _j.loads(줄들[-1])
        마["무른것"] = 맞는[0].get("id") or 맞는[0]["때"]
        줄들[-1] = _j.dumps(마, ensure_ascii=False)
        p.write_text("\n".join(줄들) + "\n", encoding="utf-8")
        print(f"{맞는[0]['때']} 의 {맞는[0]['결정']} 을 물렀다")
        return 0
    if a.워크로드목록:
        for 이름, 일 in 워크로드들.items():
            print(f"  {이름:10} {일['왜']}")
        return 0
    if a.재기:
        일 = 워크로드들.get(a.재기)
        if not 일:
            print(f"'{a.재기}' 를 모른다 ({', '.join(워크로드들)})")
            return 2
        판, 치울까 = _판꺼내기(REPO, "HEAD")
        try:
            r = 잰다(판, 일["argv"], a.반복)
        finally:
            if 치울까:
                _git(REPO, "worktree", "remove", "--force", str(판))
                shutil.rmtree(판, ignore_errors=True)
        print(f"{a.재기}: 중앙값 {r['중앙값']}초 (표본 {r['표본']} · 터진 것 {r['터진것']})")
        print(f"  흔들림(MAD) {흔들림(r['표본'])}초 · J = 1/t = "
              f"{round(1 / r['중앙값'], 4) if r['중앙값'] else '--'}")
        # **바탕선도 원장에 남긴다** -- 기계마다 다르고(실측: 컨테이너 13.4초 · VM 9.94초)
        # 판 따라 달라진다. 적어 두지 않으면 "전에는 얼마였나" 를 물을 데가 없다.
        적기(결과={"결정": "재기", "Δ": None, "V": None,
                 "잰것": {"워크로드": a.재기, "바탕중앙값": r["중앙값"], "바탕표본": r["표본"],
                        "잡음바닥": 흔들림(r["표본"])}},
           바탕=_git(REPO, "rev-parse", "--short", "HEAD").stdout.strip())
        print(f"  {성능경로} 에 남겼다 -- 이 기계의 바탕선이다")
        return 0
    if a.결정:
        if not a.후보:
            print("--후보 <갈래|커밋|디렉터리> 가 있어야 한다")
            return 2
        바, 바치움 = _판꺼내기(REPO, a.바탕)
        후, 후치움 = _판꺼내기(REPO, a.후보)
        try:
            r = 성능개선(바, 후, a.워크로드, a.반복)
        finally:
            for 판, 치움 in ((바, 바치움), (후, 후치움)):
                if 치움:
                    _git(REPO, "worktree", "remove", "--force", str(판))
                    shutil.rmtree(판, ignore_errors=True)
        적기(결과=r, 바탕=a.바탕, 후보=a.후보)
        바뀜 = (r.get("잰것") or {}).get("바뀐파일") or []
        print(f"\n**{r['결정']}** · Δ {r['Δ']}초")
        print(f"  두 판의 차이: 파일 {len(바뀜)}개 -- {', '.join(바뀜[:6])}"
              + (" ..." if len(바뀜) > 6 else ""))
        if len(바뀜) > 3:
            print("  **생각보다 많으면 비교가 오염된 것이다** -- 후보를 지금 HEAD 에서 다시 떠라")
        for w in r["까닭"]:
            print(f"  {w}")
        return 0 if r["결정"] == "ACCEPT" else 1
    print(보고())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
