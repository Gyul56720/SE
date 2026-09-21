# -*- coding: utf-8 -*-
"""손으로 옮길 때 쓰는 연장 -- **조각내고, 맞추고, 대조한다.**

## 왜 있나

`translate.py` 는 Gemini 로 옮긴다.  키가 없는 자리(에이전트 세션)에서는 못 돈다.
그때 사람(또는 에이전트)이 직접 옮기게 되는데, 그냥 옮기면 두 가지가 조용히
망가진다 -- **태그 구조**가 어긋나고(표가 깨지고 그림이 사라진다), **수**가
빠진다.  그 둘은 눈으로 안 보인다.

그래서 옮기는 일 자체는 사람이 하되, **조각내기와 대조는 기계가 한다.**
`translate.대조()` 를 그대로 쓴다 -- Gemini 가 옮긴 것을 재던 바로 그 자다.

## 쓰는 법

    python3 edu/번역/손번역.py --목록                 어느 장이 얼마나 남았나
    python3 edu/번역/손번역.py --조각 T1_device 0     0번 조각의 원문을 찍는다
    python3 edu/번역/손번역.py --저장 T1_device 0 파일 옮긴 것을 넣는다
    python3 edu/번역/손번역.py --맞추기 T1_device     조각을 이어 대조하고 낸다
    python3 edu/번역/손번역.py --검사                 낸 것 전부를 다시 대조한다

`--맞추기` 는 **대조를 통과해야만** `한국어/<키>.html` 을 쓴다.  안 통과하면
무엇이 어긋났는지 적고 아무것도 안 쓴다 -- 반쪽을 통권처럼 내놓지 않는다.
"""
from __future__ import annotations

import json
import os
import re
import sys

여기 = os.path.dirname(os.path.abspath(__file__))
뿌리 = os.path.dirname(os.path.dirname(여기))
sys.path.insert(0, os.path.join(뿌리, "edu"))
sys.path.insert(0, 여기)

원문곳 = os.path.join(뿌리, "edu", "원문")
한국어 = os.path.join(여기, "한국어")
조각곳 = os.path.join(여기, "조각")
차례경로 = os.path.join(원문곳, "차례.json")

조각크기 = 9000          # 자.  한 번에 옮기기 좋은 크기 -- 재서 정했다


def 차례():
    return json.load(open(차례경로, encoding="utf-8"))["장"]


def 이론장들():
    """대학원 이론서(T 계열)만, 번호 순서로."""
    것 = [c for c in 차례()
         if re.fullmatch(r"T\d+_\w+", c["모듈"])]
    것.sort(key=lambda c: int(re.match(r"T(\d+)", c["모듈"]).group(1)))
    return 것


def 원문(모듈):
    c = next(x for x in 차례() if x["모듈"] == 모듈)
    return open(os.path.join(원문곳, c["파일"]), encoding="utf-8").read()


def 나누기(h, 크기=조각크기):
    """`<h2` 자리에서만 끊는다 -- 문단 한가운데를 자르면 옮길 수가 없다.

    이어 붙이면 **원문과 글자까지 같아야 한다.**  `--맞추기` 가 그것을 본다.
    """
    자리 = [m.start() for m in re.finditer(r"<h2", h)]
    경계 = [0] + 자리 + [len(h)]
    토막 = [h[a:b] for a, b in zip(경계, 경계[1:]) if b > a]
    조각, 현재 = [], ""
    for t in 토막:
        if 현재 and len(현재) + len(t) > 크기:
            조각.append(현재)
            현재 = t
        else:
            현재 += t
    if 현재:
        조각.append(현재)
    if "".join(조각) != h:
        raise AssertionError("조각을 이으면 원문이 아니다 -- 나누기가 틀렸다")
    return 조각


def 조각길(모듈, i):
    os.makedirs(os.path.join(조각곳, 모듈), exist_ok=True)
    return os.path.join(조각곳, 모듈, f"{i:02d}.html")


def 키(모듈):
    return 모듈.split("_")[0]


def 맞추기(모듈, 보고=print):
    조각 = 나누기(원문(모듈))
    모은것 = []
    빠진 = []
    for i in range(len(조각)):
        p = 조각길(모듈, i)
        if not os.path.exists(p):
            빠진.append(i)
            continue
        모은것.append(open(p, encoding="utf-8").read())
    if 빠진:
        보고(f"{모듈}: 조각 {len(조각)}개 중 {빠진} 이 없다 -- 안 낸다")
        return False
    합 = "".join(모은것)
    import translate
    문제 = translate.대조(원문(모듈), 합)
    if 문제:
        보고(f"{모듈}: **대조 실패** -- 안 낸다")
        for m in 문제:
            보고("   - " + m)
        return False
    os.makedirs(한국어, exist_ok=True)
    낼곳 = os.path.join(한국어, f"{키(모듈)}.html")
    open(낼곳, "w", encoding="utf-8").write(합)
    한글 = len(re.findall(r"[가-힣]", 합))
    보고(f"{모듈}: 대조 통과 · {len(합):,}자 (한글 {한글:,}) -> "
       f"{os.path.relpath(낼곳, 뿌리)}")
    return True


def 목록(보고=print):
    보고(f"{'장':16s} {'원문자':>8s} {'조각':>4s} {'옮김':>4s}  {'낸 것':>10s}")
    남은자 = 0
    for c in 이론장들():
        m = c["모듈"]
        n = len(나누기(원문(m)))
        한 = sum(1 for i in range(n) if os.path.exists(조각길(m, i)))
        낸것 = os.path.join(한국어, f"{키(m)}.html")
        상태 = "있다" if os.path.exists(낸것) else "-"
        if not os.path.exists(낸것):
            남은자 += c["자"]
        보고(f"{m:16s} {c['자']:8,} {n:4d} {한:4d}  {상태:>10s}")
    보고(f"\n아직 안 낸 장의 원문: {남은자:,}자")


def 검사(보고=print):
    나쁨 = 0
    import translate
    for c in 이론장들():
        m = c["모듈"]
        p = os.path.join(한국어, f"{키(m)}.html")
        if not os.path.exists(p):
            continue
        문제 = translate.대조(원문(m), open(p, encoding="utf-8").read())
        if 문제:
            나쁨 += 1
            보고(f"{m}: {문제}")
    보고(f"낸 장 대조: {'전부 통과' if not 나쁨 else f'{나쁨}장 어긋남'}")
    return 나쁨 == 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("--목록", "-l"):
        목록()
    elif a[0] == "--조각":
        조각 = 나누기(원문(a[1]))
        i = int(a[2])
        sys.stdout.write(조각[i])
    elif a[0] == "--조각수":
        print(len(나누기(원문(a[1]))))
    elif a[0] == "--저장":
        모듈, i, 파일 = a[1], int(a[2]), a[3]
        글 = open(파일, encoding="utf-8").read()
        open(조각길(모듈, i), "w", encoding="utf-8").write(글)
        print(f"{모듈} 조각 {i}: {len(글):,}자 저장")
    elif a[0] == "--조각대조":
        # **조각 하나를 낸 즉시 잰다.**  장을 다 옮기고 나서 재면 어디서
        # 어긋났는지 찾느라 다시 읽어야 한다 -- 조각마다 재면 그 자리에서 안다.
        import translate
        모듈, i = a[1], int(a[2])
        원 = 나누기(원문(모듈))[i]
        옮 = open(조각길(모듈, i), encoding="utf-8").read()
        문제 = translate.대조(원, 옮)
        print(f"{모듈}[{i}] {len(원):,} -> {len(옮):,}자 "
              f"({len(옮)/len(원):.2f}) : "
              + ("통과" if not 문제 else " / ".join(문제)))
        sys.exit(0 if not 문제 else 1)
    elif a[0] == "--맞추기":
        sys.exit(0 if 맞추기(a[1]) else 1)
    elif a[0] == "--검사":
        sys.exit(0 if 검사() else 1)
    else:
        print(__doc__)
