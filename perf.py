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


def _git(판: Path, *a) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(판), *a], capture_output=True, text=True)


def 한번(판: Path, argv: "list[str]", 시한초: int = 워크로드시한초) -> "tuple[float | None, int, str]":
    """한 번 돌린 벽시계 초. 끝값이 0 이 아니면 시간을 **안 돌려준다**(None) -- 터진 것의
    시간은 성능이 아니다."""
    import os
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


def 잡음바닥(바탕표본: "list[float]", 후보표본: "list[float]" = None) -> "float | None":
    r"""**이만큼의 Δ 는 빨라진 것이라 말하지 않는다.** 두 계열의 흔들림을 더한다.

    처음에는 바탕 표본을 홀짝으로 갈라 두 중앙값의 차를 썼다(A/A 대조, 공짜다). **검사가
    그것을 깨뜨렸다** -- 같은 프로그램 둘(0.10초 · 0.10초)에서 Δ = -0.0002 인데 홀짝 차는
    0.0001 이어서 **ACCEPT 가 났다.** 홀짝 차는 *한 계열 안의 일치*를 재는데, 그것은 계열
    **사이**의 흔들림보다 체계적으로 작다. 측정 장치가 제 잡음을 낮게 불렀다.

        잡음바닥 = MAD(바탕) + MAD(후보)

    그리고 이것만으로는 모자라서 `갈렸나` 를 같이 요구한다 -- 아래를 보라."""
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
            "Δ": (round(b중 - a중, 4) if (a중 is not None and b중 is not None) else None),
            "잡음바닥": 잡음바닥(a표본, b표본),
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
    줄 = {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "워크로드": 잰.get("워크로드"), "바탕판": 바탕, "후보판": 후보,
         "결정": (결과 or {}).get("결정"), "V": (결과 or {}).get("V"),
         "바탕중앙값": 잰.get("바탕중앙값"), "후보중앙값": 잰.get("후보중앙값"),
         "Δ": (결과 or {}).get("Δ"), "잡음바닥": 잰.get("잡음바닥"),
         "짝이김": 잰.get("짝이김"), "부호p": 잰.get("부호p"),
         "J바탕": (결과 or {}).get("J바탕"), "J후보": (결과 or {}).get("J후보"),
         "바탕표본": 잰.get("바탕표본"), "후보표본": 잰.get("후보표본"),
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
    줄 = [f"{'때':17} {'워크로드':10} {'바탕':>9} {'후보':>9} {'Δ':>9} {'잡음':>8} {'결정':>8}"]
    for x in 것[-12:]:
        def 수(v, n=4):
            return f"{v:.{n}f}" if isinstance(v, (int, float)) else "--"
        줄.append(f"{str(x.get('때'))[:16]:17} {str(x.get('워크로드'))[:10]:10} "
                  f"{수(x.get('바탕중앙값')):>9} {수(x.get('후보중앙값')):>9} "
                  f"{수(x.get('Δ')):>9} {수(x.get('잡음바닥')):>8} {str(x.get('결정')):>8}")
    받음 = [x for x in 것 if x.get("결정") == "ACCEPT"]
    줄.append(f"\nACCEPT {len(받음)} / {len(것)}번. "
              + ("가장 큰 이득: " + max(((x.get('Δ') or 0), str(x.get('워크로드')))
                                   for x in 받음)[1] if 받음 else "아직 받아들인 것이 없다"))
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
    a = ap.parse_args(argv)
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
        print(f"\n**{r['결정']}** · Δ {r['Δ']}초")
        for w in r["까닭"]:
            print(f"  {w}")
        return 0 if r["결정"] == "ACCEPT" else 1
    print(보고())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
