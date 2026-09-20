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


def 대조(원문: str, 옮긴것: str):
    """다섯 가지를 본다.  어긋난 것의 목록을 돌려준다 (비면 통과)."""
    문제 = []

    # 1. 태그 구조가 그대로인가
    a, b = 태그열(원문), 태그열(옮긴것)
    if a != b:
        문제.append(f"태그 구조가 다르다 (원문 {len(a)}개, 옮긴것 {len(b)}개)")

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
    수a = re.findall(r"\d[\d,.]*", re.sub(r"<[^>]+>", " ", 원문))
    수b = re.findall(r"\d[\d,.]*", re.sub(r"<[^>]+>", " ", 옮긴것))
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
    os.makedirs(곳간, exist_ok=True)
    조각 = 쪼개기(html)
    나온것, 실패 = [], []
    for i, (덩이, 옮길까) in enumerate(조각):
        if not 옮길까 or not 덩이.strip():
            나온것.append(덩이)
            continue
        캐시 = os.path.join(곳간, f"{해시(덩이)}.html")
        if os.path.exists(캐시):
            나온것.append(open(캐시, encoding="utf-8").read())
            continue
        if 확인만:
            실패.append((i, ["아직 안 옮겼다"]))
            나온것.append(덩이)
            continue
        t, 문제 = 옮기기(덩이, pool, 용어문자열)
        if t is None:
            실패.append((i, 문제))
            나온것.append(덩이)            # 원문을 그대로 둔다 -- 반쪽을 안 낸다
        else:
            open(캐시, "w", encoding="utf-8").write(t)
            나온것.append(t)
    return "".join(나온것), 실패


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--장", nargs="*", help="옮길 장 (예: T1). 없으면 --전부 를 쓴다")
    ap.add_argument("--전부", action="store_true")
    ap.add_argument("--확인만", action="store_true",
                    help="옮기지 않고 무엇이 남았는지만 본다")
    ap.add_argument("--낼곳", default=os.path.join(여기, "한국어"))
    a = ap.parse_args()

    import importlib
    용어 = 용어집()
    용어문자열 = "\n".join(f"  {k} -> {v}" for k, v in sorted(용어.items()))

    pool = None
    if not a.확인만:
        import llm_pool
        pool = llm_pool.build_pool()
        if not pool:
            print("LLM 후보 풀이 비었다 -- GEMINI_API_KEY 를 설정하라", file=sys.stderr)
            return 2
        print(f"후보 {len(pool)}개")

    import buildT
    목록 = buildT.이론 + buildT.대학원
    고른것 = a.장 or []
    os.makedirs(a.낼곳, exist_ok=True)

    총실패 = 0
    for 모듈, 함수들 in 목록:
        키 = 모듈.split("_")[0]
        if 고른것 and 키 not in 고른것 and 모듈 not in 고른것:
            continue
        try:
            m = importlib.import_module(모듈)
        except ModuleNotFoundError:
            continue
        for f in 함수들:
            fn = getattr(m, f, None)
            if fn is None:
                continue
            html = fn()
            t0 = time.time()
            옮긴것, 실패 = 장옮기기(키, html, pool, 용어문자열, a.확인만)
            open(os.path.join(a.낼곳, f"{키}.html"), "w",
                 encoding="utf-8").write(옮긴것)
            총실패 += len(실패)
            print(f"  {키:<6} {len(html):>7,}자 -> {len(옮긴것):>7,}자  "
                  f"{time.time()-t0:5.1f}초  실패 {len(실패)}")
            for i, 문제 in 실패[:3]:
                print(f"       덩이 {i}: {문제}")

    print(f"\n남은 실패 {총실패}개")
    return 1 if 총실패 else 0


if __name__ == "__main__":
    sys.exit(main())
