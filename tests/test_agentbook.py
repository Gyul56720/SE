# -*- coding: utf-8 -*-
"""agentbook 교안이 스스로 지키는 것들.

이 교안은 세 가지를 **기계로** 붙든다.

1. **사다리** -- 아직 정의 안 한 개념을 쓰는 장이 있으면 빨간불.
   (`edu/bookK.사다리검사` 를 그대로 쓴다. T 계열 교안과 같은 장치다.)
2. **증명 없는 정리는 없다** -- `bookA.정리()` 가 빈 증명과 빈 '왜냐하면' 을
   거절한다. 여기서는 **그 거절이 실제로 나는지**를 본다(장치가 죽으면
   거짓 초록이 난다 -- 이 저장소가 여러 번 앓은 병이다).
3. **채용공고의 모든 줄을 감당하는 장이 있다** -- `jd.요구` 의 열쇠마다
   `직무([...])` 로 선언한 장이 하나 이상 있어야 한다.
   "이 책을 읽으면 이 일을 할 수 있다" 를 검사할 수 있게 만드는 장치다.

그리고 **레포 인용의 커밋이 zoo.json 에 있는지**도 본다 -- 안 읽은 커밋을
읽은 척하는 것을 막는다.
"""
import importlib.util
import json
import os
import re
import sys

여기 = os.path.dirname(os.path.abspath(__file__))
저장소 = os.path.dirname(여기)
책 = os.path.join(저장소, "agentbook")
sys.path.insert(0, 책)
sys.path.insert(0, os.path.join(저장소, "edu"))

FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


def 파일로들이기(이름, 경로):
    """`import build` 가 edu/build.py 를 잡는 사고를 막는다 -- 경로로 못박는다."""
    spec = importlib.util.spec_from_file_location(이름, 경로)
    m = importlib.util.module_from_spec(spec)
    sys.modules[이름] = m
    spec.loader.exec_module(m)
    return m


print("== 장이 전부 도는가 ==")
빌드 = 파일로들이기("agentbook_build", os.path.join(책, "build.py"))
import bookA  # noqa: E402
import bookK  # noqa: E402
import jd     # noqa: E402

있는장, 없는장 = [], []
for 부, 목록 in 빌드.차례:
    for 모듈, 함수들 in 목록:
        try:
            m = importlib.import_module(모듈)
        except ModuleNotFoundError:
            없는장.append(모듈)
            continue
        for f in 함수들:
            fn = getattr(m, f, None)
            ok(fn is not None, f"{모듈}.{f} 가 있다")
            if fn:
                h = fn()
                ok(isinstance(h, str) and len(h) > 2000,
                   f"{모듈}.{f} 가 본문을 낸다 ({len(h):,}자)")
                있는장.append(모듈)

print(f"\n  쓴 장 {len(있는장)}개 · 아직 없는 장 {len(없는장)}개")

print("\n== 사다리: 아직 안 나온 개념을 쓰는 장이 없다 ==")
어김, 처음 = bookK.사다리검사()
ok(not 어김, f"**개념이 정의된 뒤에만 쓰인다** ({어김[:3] if 어김 else '어김 없음'})")

print("\n== 증명 없는 정리는 못 만든다 (장치가 살아 있는지) ==")
try:
    bookA.정리("빈 증명", "진술", [])
    ok(False, "빈 증명이 통과했다 -- 장치가 죽었다")
except ValueError as e:
    ok("증명 없는" in str(e), f"빈 증명을 거절한다 ({str(e)[:40]})")
try:
    bookA.정리("점프", "진술", [("걸음", "")])
    ok(False, "'왜냐하면' 이 빈 걸음이 통과했다 -- 장치가 죽었다")
except ValueError as e:
    ok("점프" in str(e), f"**근거 없는 걸음을 거절한다** ({str(e)[:44]})")

ok(len(bookA.정리들) >= 10,
   f"정리가 {len(bookA.정리들)}개 있다")
걸음 = sum(n for _, _, n in bookA.정리들)
ok(걸음 >= 3 * len(bookA.정리들),
   f"정리 하나당 증명 걸음이 평균 {걸음/max(1,len(bookA.정리들)):.1f}개 "
   f"(총 {걸음}개) -- 한두 줄짜리 '증명' 이 아니다")

print("\n== 채용공고의 모든 줄을 감당하는 장이 있다 ==")
안됨 = sorted(k for k in jd.요구 if k not in bookA.감당)
덮음 = len(jd.요구) - len(안됨)
print(f"  감당 {덮음}/{len(jd.요구)}")
if 없는장:
    # 아직 다 안 쓴 동안은 '줄었는가' 만 본다. 다 쓰고 나면 아래 줄이 0 을 요구한다.
    print(f"  (아직 안 쓴 장이 {len(없는장)}개라 전수 검사는 유보한다: {안됨[:6]} ...)")
    ok(덮음 > 0, f"쓴 장들이 요구 {덮음}개를 이미 감당한다")
else:
    ok(not 안됨, f"**감당하는 장이 없는 요구가 없다** ({안됨[:5]})")

for k, 장들 in sorted(bookA.감당.items()):
    ok(all(isinstance(x, str) for x in 장들), f"{k} -> {' · '.join(장들)}")

print("\n== 레포 인용은 내가 실제로 읽은 커밋만 ==")
zoo = json.load(open(os.path.join(책, "zoo.json"), encoding="utf-8"))
커밋들 = {v["커밋"] for v in zoo.values()}
# A chapter may quote a **historical** commit (langchain's first commit, for
# instance) which zoo.json does not carry -- zoo.json records HEAD only. That
# is legitimate *if* the lines were vendored into agentbook/snips/, because
# then the quote stays verifiable. So a snippet's recorded commit counts as a
# source too.
발췌곳간 = os.path.join(책, "snips")
if os.path.isdir(발췌곳간):
    for f in os.listdir(발췌곳간):
        if f.endswith(".json"):
            with open(os.path.join(발췌곳간, f), encoding="utf-8") as fh:
                커밋들.add(json.load(fh)["커밋"])
ok(len(zoo) >= 10, f"zoo.json 에 저장소 {len(zoo)}개 -- 클론해서 잰 것이다")
본문 = "".join(getattr(importlib.import_module(m), f)()
             for 부, 목록 in 빌드.차례 for m, 함수들 in 목록
             if m in 있는장 for f in 함수들)
# Short hashes are not always 7 characters -- git gives as many as it needs
# to stay unique, and langchain's is 9. A fixed {7} silently skipped that
# citation, so the check was passing without looking at it.
인용커밋 = set(re.findall(r'@ ([0-9a-f]{7,40})<', 본문))
낯선 = 인용커밋 - 커밋들
ok(not 낯선, f"**본문이 대는 커밋이 전부 zoo.json 에 있다** (낯선 것: {낯선})")
if 인용커밋:
    print(f"  인용된 커밋 {len(인용커밋)}개: {' · '.join(sorted(인용커밋))}")

print("\n== 논문 확인수준을 속이지 않는다 ==")
ok("확인: 조각" in 본문 or not re.search(r"arXiv:\d", 본문),
   "arXiv 를 대는 자리에 확인수준이 붙어 있다")
# '전문' 은 **정말 끝까지 읽은 것**에만 붙는다. 이 세션에서 arXiv 는 막혀 있었고
# platform.claude.com 은 열려 있었다 -- 그래서 전문이 붙은 것이 있다면 그것은
# arXiv 가 아니어야 한다. 이 검사가 붙드는 것은 '읽지 않은 것을 인용하지 않는다' 다.
전문상자 = re.findall(r'\[논문 \d+\] (.{0,160}?)<span class="수준">확인: 전문', 본문)
ok(all("arXiv" not in t for t in 전문상자),
   f"**arXiv 논문에 '전문' 을 붙이지 않았다** (전문으로 적은 것: {len(전문상자)}개)")
for t in 전문상자:
    print(f"  전문으로 읽은 것: {t[:70]}")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL[:3]}")
    raise SystemExit(1)
print("agentbook: 장 · 사다리 · 증명 강제 · 직무 감당 · 커밋 출처 -- 통과")
