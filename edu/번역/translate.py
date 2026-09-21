# -*- coding: utf-8 -*-
"""이론서를 한국어로 옮긴다 -- **Gemini 가 옮기고, 이 파일이 검사한다.**

    python3 edu/번역/translate.py --장 T1            # 한 장만
    python3 edu/번역/translate.py --전부             # 전부
    python3 edu/번역/translate.py --전부 --확인만    # 옮기지 않고 검사만

## 왜 Claude 가 아니라 Gemini 인가

CLAUDE.md 의 규칙이다: **산문은 Gemini, 판단은 Claude.**  번역은 토큰의
대부분을 먹는 산문 작업이고, 그것을 구독으로 청구할 이유가 없다.
이 파일은 배선과 **검사**만 하고, 옮기는 일은 전부 Gemini 가 한다.

## 번역의 진짜 실패 방식

번역기가 틀리는 방식은 오역이 아니다.  오역은 읽으면 보인다.  진짜 무서운 것은
**조용히 사라지는 것**이다:

    * 문단 하나를 통째로 빼먹는다        -> 논리가 끊기는데 티가 안 난다
    * 코드 블록 안의 식별자를 번역한다   -> `always_ff` 가 `항상_ff` 가 된다
    * <table> 의 행 수가 달라진다        -> 표가 어긋나는데 숫자는 그럴듯하다
    * 수식의 첨자를 잃는다               -> V_GS 가 VGS 가 된다

그래서 옮긴 뒤에 **기계가 다섯 가지를 대조한다**.  하나라도 어긋나면 그 덩이는
**버리고 다시 옮긴다**.  세 번 실패하면 원문을 그대로 두고 빨간불을 낸다 --
조용히 반쪽짜리를 내보내지 않는다.

## 용어는 고정한다

같은 말이 장마다 다르게 번역되면 그것은 다른 개념으로 읽힌다.
`용어집.json` 이 한 번 정하고 프롬프트에 매번 실린다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time

여기 = os.path.dirname(os.path.abspath(__file__))
뿌리 = os.path.dirname(os.path.dirname(여기))
sys.path.insert(0, os.path.join(뿌리, "orchestrator"))
sys.path.insert(0, os.path.join(뿌리, "edu"))

곳간 = os.path.join(여기, "곳간")          # 옮긴 것을 해시로 캐시한다
용어집경로 = os.path.join(여기, "용어집.json")

# ---------------------------------------------------------------------------
# 쪼개기 -- HTML 을 통째로 던지면 모델이 구조를 잃는다
# ---------------------------------------------------------------------------
# 최상위 블록 단위로 자른다.  <pre> 는 **통째로 건너뛴다** (코드는 안 옮긴다).
덩이패턴 = re.compile(
    r"(<pre\b.*?</pre>|<h[1-3]\b.*?</h[1-3]>|<table\b.*?</table>|"
    r"<figure\b.*?</figure>|<div\b[^>]*>.*?</div>|<p\b.*?</p>)",
    re.S)


def 쪼개기(html: str):
    """(덩이, 옮길것인가) 목록."""
    조각, 끝 = [], 0
    for m in 덩이패턴.finditer(html):
        if m.start() > 끝:
            사이 = html[끝:m.start()]
            if 사이.strip():
                조각.append((사이, True))
        t = m.group(0)
        조각.append((t, not t.lstrip().startswith("<pre")))
        끝 = m.end()
    if 끝 < len(html) and html[끝:].strip():
        조각.append((html[끝:], True))
    return 조각


# ---------------------------------------------------------------------------
# 검사 -- 여기가 이 파일의 요점
# ---------------------------------------------------------------------------
태그패턴 = re.compile(r"</?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>")
코드패턴 = re.compile(r"<code\b.*?</code>", re.S)


def 태그열(s: str):
    """여는/닫는 태그의 **순서 있는 목록**.  구조가 같은지 보는 기준."""
    return re.findall(r"</?[a-zA-Z][a-zA-Z0-9]*", s)


# 문단·표처럼 **자리를 지켜야 하는** 태그와, 문장 안에서 **자리를 옮겨도 되는**
# 태그를 가른다.
#
# 왜 가르나 (실측 2026-09-21): 영어 "falls by a factor of ten for every
# <b>85 mV</b> that V<sub>GS</sub> drops" 를 한국어로 옮기면
# "V<sub>GS</sub> 가 ... <b>85 mV</b> 내려갈 때마다" 가 된다.  태그는 하나도
# 안 늘고 안 줄었는데 **순서가 바뀐다** -- 한국어 어순이 그러므로.  순서만 보는
# 검사는 이것을 '구조가 다르다' 로 낸다.  그러면 옳은 번역을 고치게 되고,
# 고치다 보면 한국어가 뻣뻣해진다.
#
# 그렇다고 순서를 통째로 포기하면 <b> 가 이 <div> 에서 저 <div> 로 건너뛴 것도
# 못 본다.  그래서 **구조 태그는 순서까지, 안쪽 태그는 그 블록 안에 같은 것이
# 같은 수만큼 있는지**를 본다.
구조태그 = {"div", "p", "table", "thead", "tbody", "tfoot", "tr", "td", "th",
         "h1", "h2", "h3", "h4", "pre", "ul", "ol", "li", "blockquote",
         "figure", "figcaption", "svg", "g", "path", "rect", "circle",
         "line", "text", "tspan", "polyline", "polygon", "caption"}


def 구조열(s: str):
    """구조 태그만, 순서 그대로."""
    return [t for t in 태그열(s)
            if t.lstrip("</").lower() in 구조태그]


def 안쪽셈(s: str):
    """구조 태그로 끊은 토막마다, 그 안의 안쪽 태그를 세어 둔다."""
    from collections import Counter
    토막, 현재 = [], []
    for m in re.finditer(r"</?[a-zA-Z][a-zA-Z0-9]*", s):
        이름 = m.group(0).lstrip("</").lower()
        if 이름 in 구조태그:
            토막.append(Counter(현재))
            현재 = []
        else:
            현재.append(m.group(0).lower())
    토막.append(Counter(현재))
    return 토막


def 대조(원문: str, 옮긴것: str):
    """다섯 가지를 본다.  어긋난 것의 목록을 돌려준다 (비면 통과)."""
    문제 = []

    # 1. 태그 구조가 그대로인가 -- 구조는 순서까지, 안쪽은 블록 단위로
    a, b = 구조열(원문), 구조열(옮긴것)
    if a != b:
        같은데까지 = next((i for i in range(min(len(a), len(b)))
                      if a[i] != b[i]), min(len(a), len(b)))
        문제.append(f"구조 태그가 다르다 (원문 {len(a)}개, 옮긴것 {len(b)}개, "
                   f"{같은데까지}번째에서 갈린다)")
    else:
        ia, ib = 안쪽셈(원문), 안쪽셈(옮긴것)
        다른블록 = [k for k, (x, y) in enumerate(zip(ia, ib)) if x != y]
        if 다른블록:
            k = 다른블록[0]
            문제.append(f"블록 안의 태그가 다르다 ({len(다른블록)}곳, 처음은 "
                       f"{k}번째 블록: {dict(ia[k] - ib[k])} 가 빠지고 "
                       f"{dict(ib[k] - ia[k])} 가 늘었다)")

    # 2. <code> 속은 **글자까지** 같아야 한다 -- 식별자를 옮기면 안 된다
    ca = [re.sub(r"\s+", " ", x) for x in 코드패턴.findall(원문)]
    cb = [re.sub(r"\s+", " ", x) for x in 코드패턴.findall(옮긴것)]
    if ca != cb:
        문제.append(f"<code> 속이 바뀌었다 ({len(ca)}개 중 "
                   f"{sum(1 for x, y in zip(ca, cb) if x != y)}개)")

    # 3. 표의 행·열 수가 같은가
    for 태그 in ("<tr", "<td", "<th"):
        if 원문.count(태그) != 옮긴것.count(태그):
            문제.append(f"{태그}> 수가 다르다 "
                       f"({원문.count(태그)} -> {옮긴것.count(태그)})")

    # 4. 숫자가 사라지지 않았는가 -- 번역기가 수를 빼먹는 일이 실제로 있다
    # 끝에 붙은 문장부호는 떼고 본다.  영어 "= 7.62." 와 한국어 "= 7.62 다."
    # 는 같은 수인데, 안 떼면 앞은 `7.62.` 뒤는 `7.62` 로 잡혀 **빠졌다고
    # 잘못 낸다**(실측 2026-09-21).
    def _수뽑기(t):
        return [x.rstrip(".,") for x in
                re.findall(r"\d[\d,.]*", re.sub(r"<[^>]+>", " ", t))]

    수a = _수뽑기(원문)
    수b = _수뽑기(옮긴것)
    if sorted(수a) != sorted(수b):
        빠진 = [x for x in 수a if 수a.count(x) > 수b.count(x)]
        if 빠진:
            문제.append(f"숫자가 빠졌다: {빠진[:4]}")

    # 5. 통째로 짧아지지 않았는가 -- 문단 누락의 흔한 증상
    글a = len(re.sub(r"<[^>]+>", "", 원문).strip())
    글b = len(re.sub(r"<[^>]+>", "", 옮긴것).strip())
    if 글a > 200 and 글b < 글a * 0.35:
        문제.append(f"너무 짧아졌다 ({글a} -> {글b}자) -- 문단이 빠진 듯하다")

    return 문제


# ---------------------------------------------------------------------------
# 용어집
# ---------------------------------------------------------------------------
기본용어 = {
    "threshold voltage": "문턱전압", "overdrive": "과구동",
    "cutoff": "차단영역", "triode": "선형영역(triode)",
    "saturation": "포화영역", "subthreshold": "아문턱",
    "transconductance": "트랜스컨덕턴스", "output resistance": "출력저항",
    "leakage": "누설", "body effect": "바디효과",
    "gate capacitance": "게이트 용량", "setup": "셋업", "hold": "홀드",
    "metastability": "준안정", "propagation delay": "전파지연",
    "slew": "슬루", "logical effort": "논리적 노력(logical effort)",
    "skew": "스큐", "jitter": "지터", "corner": "코너",
    "sampling": "표본화", "aliasing": "엘리어싱", "quantization": "양자화",
    "equalization": "등화", "eye diagram": "아이 다이어그램",
    "golden model": "골든모델", "testbench": "테스트벤치",
    "mutation score": "변이 점수", "timing shell": "타이밍 껍데기",
    "datasheet": "데이터시트", "deliverable": "납품물",
    "prior art": "선행기술", "claim": "청구항",
}


def 용어집():
    if os.path.exists(용어집경로):
        return json.load(open(용어집경로, encoding="utf-8"))
    os.makedirs(여기, exist_ok=True)
    json.dump(기본용어, open(용어집경로, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return dict(기본용어)


# ---------------------------------------------------------------------------
# 옮기기
# ---------------------------------------------------------------------------
프롬프트 = """You are translating a graduate-level semiconductor IP design textbook
from English into Korean for a reader who has a BS in electrical engineering.

ABSOLUTE RULES — violating any of these makes the output unusable:

1. Output ONLY the translated HTML fragment. No preamble, no explanation,
   no markdown fences.
2. Keep EVERY HTML tag exactly as it appears, in the same order, with the
   same attributes. Do not add, remove, merge or reorder tags.
3. Do NOT translate anything inside <code> or <pre>. Copy those byte for byte,
   including comments inside code.
4. Do NOT translate: signal names, keywords, file names, tool names,
   units, or any identifier that would appear in source code.
5. Keep every number exactly as written, including subscripts inside <sub>.
6. Translate every sentence. Do not summarise, do not omit, do not merge
   paragraphs.

STYLE: write plain, direct Korean for an engineer. Use 해라체 ("~한다", "~이다"),
not 존댓말. Prefer short sentences. Keep the original's directness; do not
soften statements.

FIXED TERMS — use exactly these Korean words for these English terms:
{용어}

Translate this fragment:

{덩이}"""


# ---------------------------------------------------------------------------
# 묶어 부르기 -- 프롬프트가 본문보다 비싸지는 것을 막는다
# ---------------------------------------------------------------------------
# 실측 2026-09-20 (전체 교재를 재 보고): 옮길 덩이가 **3,323개**, 옮길 글자가
# 172만 자다.  덩이 하나에 한 번씩 부르면 프롬프트(지시 + 용어집 300여 항목)가
# **호출마다** 실린다 -- 대략 900 토큰 × 3,323 = 300만 토큰이, 본문(47만 토큰)의
# 여섯 배다.  **번역 값의 대부분이 같은 지시문을 3,323번 다시 보내는 데 든다.**
#
# 그래서 덩이를 묶어 한 번에 보낸다.  묶은 것을 다시 가르려면 표식이 필요한데,
# 표식은 **모델이 지울 수 있다.**  그래서 표식이 하나라도 없어지면 그 묶음은
# 버리고 **덩이 하나씩** 다시 부른다 -- 느려질 뿐 틀리지 않는다.
# **묶음 크기는 값과 위험의 저울이다.**
#
# 값: 호출마다 지시문+용어집 853 토큰이 다시 실린다.  6,000자면 387회, 10,000자면
# 250회, 20,000자면 194회다(--어림).  사용자의 키가 분당·하루 한도에 걸려 멈췄으므로
# 줄일 수 있는 유일한 손잡이가 이 호출 수다.
#
# 위험: **모델의 출력 한도**다.  Gemini 계열은 입력이 수십만 토큰이어도 출력은
# 8,192 토큰인 판이 흔하다.  한국어는 글자당 토큰이 많아서(≈1.3자/토큰) 10,000자
# 입력이면 출력이 대략 8,000자 ≈ 6,000 토큰 -- 아슬아슬하게 안쪽이다.  20,000자면
# 넘긴다.  넘기면 응답이 잘리고, 잘리면 표식이 사라져 그 묶음을 통째로 버린다 --
# **쿼터를 쓰고 아무것도 못 얻는다.**
#
# 그래서 기본을 10,000자로 두고, 묶음이 두 번 깨지면 **스스로 절반으로 줄인다**
# (`_묶음줄이기`).  모델의 한도를 몰라도 한두 번 만에 맞는 크기를 찾는다.
묶음자 = 10000                    # 한 번에 보낼 본문 글자 수 (적응적으로 줄어든다)
최소묶음자 = 1500
표식틀 = "<!--B{}-->"
표식패턴 = re.compile(r"<!--B(\d+)-->")


def 묶기(덩이들, 상한=None):
    """[(i, 덩이)] -> [[(i, 덩이), ...]]  -- 글자 수로 묶는다."""
    상한 = 상한 or 묶음자
    묶음, 지금, 셈 = [], [], 0
    for i, d in 덩이들:
        if 지금 and 셈 + len(d) > 상한:
            묶음.append(지금)
            지금, 셈 = [], 0
        지금.append((i, d))
        셈 += len(d)
    if 지금:
        묶음.append(지금)
    return 묶음


def 묶음글(묶음):
    return "\n".join(표식틀.format(i) + "\n" + d for i, d in 묶음)


def 묶음가르기(글, 묶음):
    """표식으로 다시 가른다.  하나라도 없으면 None (부른 쪽이 낱개로 돌아간다)."""
    자리 = {int(m.group(1)): m for m in 표식패턴.finditer(글)}
    if set(자리) != {i for i, _ in 묶음}:
        return None
    차례 = sorted(자리.items(), key=lambda kv: kv[1].start())
    if [i for i, _ in 차례] != [i for i, _ in 묶음]:
        return None                      # 순서가 바뀌었다 -- 믿지 않는다
    난것 = {}
    for n, (i, m) in enumerate(차례):
        끝 = 차례[n + 1][1].start() if n + 1 < len(차례) else len(글)
        난것[i] = 글[m.end():끝].strip()
    return 난것


def _묶음줄이기():
    """묶음이 잇달아 깨지면 절반으로.  **모델의 출력 한도를 몰라도 맞춰 간다.**

    깨지는 까닭은 대개 하나다 -- 응답이 출력 토큰 한도에서 잘려 뒤쪽 표식이
    사라진다.  그것은 묶음을 줄이면 사라지고, 줄이지 않으면 남은 쿼터를 전부
    같은 방식으로 버린다.
    """
    global 묶음자
    새것 = max(최소묶음자, 묶음자 // 2)
    if 새것 != 묶음자:
        print(f"    (묶음 {묶음자:,} -> {새것:,}자 -- 응답이 잘린 꼴이다)", flush=True)
        묶음자 = 새것
    return 묶음자


def 묶어옮기기(묶음, pool, 용어문자열, 시도=2):
    """묶음 하나를 한 번에 옮긴다.  {i: 옮긴것} 또는 None(낱개로 가라)."""
    import llm_pool
    for _ in range(시도):
        p = 묶음프롬프트.format(용어=용어문자열, 덩이=묶음글(묶음))
        try:
            r = llm_pool.ask(pool, p)
        except Exception:                                 # noqa: BLE001
            time.sleep(2)
            continue
        t = re.sub(r"^```[a-zA-Z]*\n", "", (r or "").strip())
        t = re.sub(r"\n```$", "", t).strip()
        갈린것 = 묶음가르기(t, 묶음)
        if 갈린것 is None:
            continue                      # 표식을 잃었다 -- 한 번 더, 그래도 안 되면 낱개
        # **덩이마다 따로 대조한다.** 묶었다고 검사를 묶지 않는다.
        좋은것 = {i: 갈린것[i] for i, d in 묶음 if not 대조(d, 갈린것[i])}
        if len(좋은것) == len(묶음):
            return 좋은것
        if 좋은것:
            return 좋은것                 # 통과한 것만 쓰고 나머지는 낱개로 간다
    return None


묶음프롬프트 = 프롬프트.replace(
    "Translate this fragment:",
    """The input contains SEVERAL fragments, each preceded by a marker like <!--B12-->.

7. Copy EVERY <!--Bnn--> marker exactly as it appears, on its own line, in the
   same order, immediately before that fragment's translation. Do not renumber
   them, do not add markers, do not drop any. The markers are how the output is
   split back apart; a missing marker throws away the whole batch.

Translate these fragments:""")


def 옮기기(덩이: str, pool, 용어문자열: str, 시도=3):
    """한 덩이를 옮긴다.  검사를 통과할 때까지 최대 `시도` 번."""
    import llm_pool
    마지막문제 = ["아직 안 해봤다"]
    for n in range(시도):
        p = 프롬프트.format(용어=용어문자열, 덩이=덩이)
        try:
            r = llm_pool.ask(pool, p)
        except Exception as e:                                # noqa: BLE001
            마지막문제 = [f"호출 실패: {str(e)[:120]}"]
            time.sleep(2 * (n + 1))
            continue
        t = (r or "").strip()
        t = re.sub(r"^```[a-zA-Z]*\n", "", t)
        t = re.sub(r"\n```$", "", t).strip()
        문제 = 대조(덩이, t)
        if not 문제:
            return t, None
        마지막문제 = 문제
    return None, 마지막문제


def 해시(s: str):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def 장옮기기(이름: str, html: str, pool, 용어문자열: str, 확인만=False):
    """장 하나를 옮긴다.  **캐시는 덩이 단위, 호출은 묶음 단위.**

    캐시를 덩이 단위로 두는 까닭: 중간에 끊겨도 다시 돌리면 이미 옮긴 덩이는
    안 부른다.  172만 자를 한 번에 끝낼 수 없으므로(쿼터) 이어 돌리는 것이 기본이다.
    """
    os.makedirs(곳간, exist_ok=True)
    조각 = 쪼개기(html)
    나온것 = [d for d, _ in 조각]
    실패 = []

    # 1) 캐시에 없는 것만 모은다
    남은 = []
    for i, (덩이, 옮길까) in enumerate(조각):
        if not 옮길까 or not 덩이.strip():
            continue
        캐시 = os.path.join(곳간, f"{해시(덩이)}.html")
        if os.path.exists(캐시):
            나온것[i] = open(캐시, encoding="utf-8").read()
            continue
        if 확인만:
            실패.append((i, ["아직 안 옮겼다"]))
            continue
        남은.append((i, 덩이))

    # 2) 묶어서 부른다
    덩이맵 = dict(남은)
    아직 = []
    깨짐 = 0
    for 묶음 in 묶기(남은):
        난것 = 묶어옮기기(묶음, pool, 용어문자열)
        if not 난것:
            아직 += 묶음
            깨짐 += 1
            if 깨짐 >= 2:
                _묶음줄이기()      # 출력 한도에 걸린 꼴이다 -- 스스로 줄인다
                깨짐 = 0
            continue
        for i, t in 난것.items():
            open(os.path.join(곳간, f"{해시(덩이맵[i])}.html"), "w",
                 encoding="utf-8").write(t)
            나온것[i] = t
        아직 += [(i, d) for i, d in 묶음 if i not in 난것]

    # 3) 묶음에서 못 건진 것만 낱개로 -- 느릴 뿐 틀리지 않는다
    for i, 덩이 in 아직:
        t, 문제 = 옮기기(덩이, pool, 용어문자열)
        if t is None:
            실패.append((i, 문제))        # 원문을 그대로 둔다 -- 반쪽을 안 낸다
        else:
            open(os.path.join(곳간, f"{해시(덩이)}.html"), "w",
                 encoding="utf-8").write(t)
            나온것[i] = t
    return "".join(나온것), 실패


class 통째실패(Exception):
    """한 장이 거의 통째로 안 옮겨졌다 -- **영어를 한국어 파일로 내보내지 않는다.**

    실측 2026-09-20: 사용자가 VM 에서 돌린 뒤 `--상태` 가 **캐시 0 · 낸 장 3** 을
    냈다.  한 덩이도 못 옮겼는데 장 파일은 세 개가 생긴 것이다 -- 덩이가 실패하면
    원문을 그대로 두게 해 놨기 때문이다(반쪽을 안 내려던 것이 **영어 파일을
    한국어 파일 이름으로 내는** 꼴이 됐다).  그러니 통째로 실패하면 멈춘다.
    """


def 장옮기기_안전(이름, html, pool, 용어문자열, 확인만=False, 최소성공=0.5):
    """장옮기기 + **거의 다 실패했으면 터뜨린다.**"""
    조각 = 쪼개기(html)
    옮길것 = sum(1 for d, 옮길까 in 조각 if 옮길까 and d.strip())
    옮긴것, 실패 = 장옮기기(이름, html, pool, 용어문자열, 확인만)
    if 확인만 or 옮길것 == 0:
        return 옮긴것, 실패
    성공 = 옮길것 - len(실패)
    if 성공 < 옮길것 * 최소성공:
        문제 = 실패[0][1] if 실패 else ["(까닭 없음)"]
        raise 통째실패(
            f"{이름}: 덩이 {옮길것}개 중 {성공}개만 옮겼다 -- 멈춘다.\n"
            f"  첫 까닭: {문제}\n"
            "  영어를 한국어 파일로 내보내지 않는다. 까닭을 먼저 보라:\n"
            "    bash scripts/번역돌리기.sh --진단")
    return 옮긴것, 실패


# ---------------------------------------------------------------------------
# 값 어림 -- 돌리기 전에 얼마나 드는지 잰다
# ---------------------------------------------------------------------------
# 토큰은 세는 것이 아니라 **어림하는 것**이다(모델의 토크나이저가 여기 없다).
# 그래서 어림에 쓴 비율을 같이 적는다 -- 수만 주고 근거를 안 주면 믿을 수 없다.
영어자당토큰 = 1 / 3.7        # 영어 + HTML 태그
한글자당토큰 = 1 / 1.3        # 한국어는 글자당 토큰이 훨씬 많다
번역길이비 = 0.75             # 옮기면 글자 수가 이 정도가 된다(태그 포함)


def 어림(장들, 용어문자열, 묶음=None):
    """[(키, html)] -> 호출 수 · 입력/출력 토큰 어림."""
    지시토큰 = int(len(프롬프트) * 영어자당토큰) + int(len(용어문자열) * 한글자당토큰)
    본문자 = 호출 = 덩이수 = 0
    for _, html in 장들:
        덩이들 = [(i, d) for i, (d, 옮길까) in enumerate(쪼개기(html))
                if 옮길까 and d.strip()]
        덩이수 += len(덩이들)
        본문자 += sum(len(d) for _, d in 덩이들)
        호출 += len(묶기(덩이들, 묶음))
    입력 = 호출 * 지시토큰 + int(본문자 * 영어자당토큰)
    출력 = int(본문자 * 번역길이비 * 한글자당토큰)
    낱개호출 = 덩이수
    낱개입력 = 낱개호출 * 지시토큰 + int(본문자 * 영어자당토큰)
    return {"장": len(장들), "덩이": 덩이수, "본문자": 본문자,
            "호출": 호출, "지시토큰": 지시토큰,
            "입력토큰": 입력, "출력토큰": 출력,
            "낱개호출": 낱개호출, "낱개입력토큰": 낱개입력}


def 장들읽기(고른것):
    """옮길 [(키, html)].  **먼저 `edu/원문/` 을 본다** -- VM 은 장을 못 짓는다.

    원문이 없으면(개발 자리) 모듈을 직접 그린다.  둘 다 없으면 빈 목록이다.
    """
    import 원문내기
    난것 = [(키, html) for 키, _, html in 원문내기.읽기()]
    if not 난것:
        import importlib
        import buildT
        for 모듈, 함수들 in buildT.이론 + buildT.대학원:
            try:
                m = importlib.import_module(모듈)
            except ModuleNotFoundError:
                continue
            for f in 함수들:
                fn = getattr(m, f, None)
                if fn:
                    난것.append((모듈.split("_")[0], fn()))
    if 고른것:
        고 = {x.split("_")[0] for x in 고른것}
        난것 = [(k, h) for k, h in 난것 if k in 고]
    # **이론서(T 계열)를 먼저 옮긴다.**  쿼터가 하루에 다 안 되면 어디서 끊기든
    # 한 권은 손에 남아야 한다 -- 179장에 고루 퍼뜨려 놓으면 아무것도 못 읽는다.
    난것.sort(key=lambda kh: (0 if kh[0][:1] == "T" and kh[0][1:2].isdigit() else 1))
    return 난것


def 진단(장들, 용어문자열):
    """**한 덩이만** 옮겨 보고 무엇이 어긋났는지 그대로 보인다.

    통째 실패의 까닭은 대개 넷 중 하나다: 키가 없다 · 쿼터가 끝났다 ·
    모델이 태그를 바꾼다 · 모델이 앞뒤에 설명을 붙인다.  넷은 **증상이 달라서**
    응답 원문을 한 번 보면 바로 갈린다.  그런데 지금까지는 그 원문을 아무도
    못 봤다 -- 실패하면 조용히 원문을 두고 넘어갔기 때문이다.
    """
    import llm_pool
    pool = llm_pool.build_pool()
    print(f"후보 {len(pool) if pool else 0}개")
    if not pool:
        print("**키가 없다** -- GEMINI_API_KEY 를 세워라. 이것이 까닭이다.",
              file=sys.stderr)
        return 2
    덩이 = None
    for _, html in 장들:
        for d, 옮길까 in 쪼개기(html):
            if 옮길까 and 200 < len(d.strip()) < 1200:
                덩이 = d.strip()
                break
        if 덩이:
            break
    if not 덩이:
        print("진단에 쓸 덩이를 못 찾았다", file=sys.stderr)
        return 2
    print("\n=== 보낸 덩이 ===\n" + 덩이[:600])
    p = 프롬프트.format(용어=용어문자열, 덩이=덩이)
    try:
        r = llm_pool.ask(pool, p)
    except Exception as e:                                  # noqa: BLE001
        print(f"\n**호출 자체가 실패했다**: {type(e).__name__}: {e}", file=sys.stderr)
        print("  쿼터·키·망 중 하나다. 메시지를 그대로 보라.", file=sys.stderr)
        return 3
    t = re.sub(r"^```[a-zA-Z]*\n", "", (r or "").strip())
    t = re.sub(r"\n```$", "", t).strip()
    print("\n=== 받은 것 ===\n" + (t[:900] if t else "(빈 응답)"))
    문제 = 대조(덩이, t)
    if 문제:
        print("\n**어긋난 곳** (이것 때문에 버린다):", file=sys.stderr)
        for x in 문제:
            print("  - " + str(x)[:200], file=sys.stderr)
        return 1
    print("\n대조 통과 -- 이 덩이는 멀쩡하다. 통째 실패라면 쿼터나 묶음 쪽을 보라.")
    return 0


def main():
    global 묶음자
    ap = argparse.ArgumentParser()
    ap.add_argument("--장", nargs="*", help="옮길 장 (예: T1). 없으면 --전부 를 쓴다")
    ap.add_argument("--전부", action="store_true")
    ap.add_argument("--확인만", action="store_true",
                    help="옮기지 않고 무엇이 남았는지만 본다")
    ap.add_argument("--어림", action="store_true",
                    help="**부르지 않고** 호출 수와 토큰을 어림한다")
    ap.add_argument("--진단", action="store_true",
                    help="덩이 하나만 옮겨 보고 **원문·응답·어긋난 곳**을 그대로 찍는다")
    ap.add_argument("--묶음", type=int, default=묶음자,
                    help=f"한 번에 보낼 본문 글자 수 (기본 {묶음자})")
    ap.add_argument("--낼곳", default=os.path.join(여기, "한국어"))
    a = ap.parse_args()
    묶음자 = a.묶음

    용어 = 용어집()
    용어문자열 = "\n".join(f"  {k} -> {v}" for k, v in sorted(용어.items()))
    장들 = 장들읽기(a.장 or [])
    if not 장들:
        print("옮길 장이 없다 -- `python3 edu/원문내기.py` 로 원문을 먼저 꺼낸다",
              file=sys.stderr)
        return 2

    if a.어림:
        e = 어림(장들, 용어문자열, a.묶음)
        print(f"장 {e['장']} · 덩이 {e['덩이']:,} · 옮길 글자 {e['본문자']:,}")
        print(f"묶음 {a.묶음:,}자 -> **호출 {e['호출']:,}회**  "
              f"(낱개로 부르면 {e['낱개호출']:,}회)")
        print(f"호출마다 지시+용어집 {e['지시토큰']:,} 토큰")
        print(f"입력 어림 {e['입력토큰']:,} 토큰   (낱개면 {e['낱개입력토큰']:,})")
        print(f"출력 어림 {e['출력토큰']:,} 토큰")
        print(f"어림에 쓴 비율: 영어 {1/영어자당토큰:.1f}자/토큰 · "
              f"한국어 {1/한글자당토큰:.1f}자/토큰 · 번역 길이비 {번역길이비}")
        print("재시도(구조 어긋남)는 안 셌다 -- 실제는 이보다 10~20% 많다")
        return 0

    if a.진단:
        return 진단(장들, 용어문자열)

    pool = None
    if not a.확인만:
        import llm_pool
        pool = llm_pool.build_pool()
        if not pool:
            print("LLM 후보 풀이 비었다 -- GEMINI_API_KEY 를 설정하라", file=sys.stderr)
            return 2
        print(f"후보 {len(pool)}개 · 장 {len(장들)}개 · 묶음 {a.묶음:,}자")

    os.makedirs(a.낼곳, exist_ok=True)
    총실패 = 0
    for 키, html in 장들:
        t0 = time.time()
        try:
            옮긴것, 실패 = 장옮기기_안전(키, html, pool, 용어문자열, a.확인만)
        except 통째실패 as e:
            print(f"\n[멈춤] {e}", file=sys.stderr)
            return 3
        open(os.path.join(a.낼곳, f"{키}.html"), "w",
             encoding="utf-8").write(옮긴것)
        총실패 += len(실패)
        됨 = len(os.listdir(곳간)) if os.path.isdir(곳간) else 0
        print(f"  {키:<12} {len(html):>7,}자 -> {len(옮긴것):>7,}자  "
              f"{time.time()-t0:5.1f}초  실패 {len(실패)}  누적 덩이 {됨:,}",
              flush=True)
        for i, 문제 in 실패[:3]:
            print(f"       덩이 {i}: {문제}")

    print(f"\n남은 실패 {총실패}개")
    return 1 if 총실패 else 0


if __name__ == "__main__":
    sys.exit(main())
