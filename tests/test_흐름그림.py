# -*- coding: utf-8 -*-
"""`edu/sch_flow.py` 의 그림들이 **실제로 그려지고 밖으로 안 새는가.**

사용자(2026-09-20): *"각각 다이어그램 처럼 설명해줘. 모든 내용 저런 사진 써서."*

그림은 돌려 볼 수가 없어서 잘못을 알아채기 어렵다(sch.py 가 처음 시험될 때
그린 인버터는 VDD 와 PMOS 소스가 **안 이어져 있었다** -- 그럴듯해 보였다).
그래서 기계가 볼 수 있는 것만이라도 붙든다.

  1. 열세 장이 전부 예외 없이 그려진다
  2. viewBox 가 있고 태그 짝이 맞는다 (HTML 에 박히므로 깨지면 뒤가 다 날아간다)
  3. **글자가 캔버스 밖으로 안 나간다** -- 나가면 PDF 에서 잘린다
  4. 라벨에 한글이 없다 -- 영어판이 이 그림을 그대로 쓰고, 이 기계에는
     한글 글꼴이 없어서 네모(두부)가 된다
  5. 그림이 장에 **실제로 꽂혀 있다** -- 지어 놓고 안 쓰는 것을 막는다
  6. **자해검사** -- 일부러 밖으로 뺀 글자를 넣으면 이 검사가 빨개진다

    python3 tests/test_흐름그림.py
"""
from __future__ import annotations

import os
import re
import sys

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(뿌리, "edu"))

import sch_flow  # noqa: E402

fails = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        fails.append(말)


_한글 = re.compile(r"[가-힣]")


def _캔버스들(h):
    return [(int(a), int(b))
            for a, b in re.findall(r'viewBox="0 0 (\d+) (\d+)"', h)]


def _밖으로나간글자(h, 여유=40):
    """여러 <svg> 가 이어붙은 그림도 있으므로 조각마다 따로 본다."""
    나간것 = []
    for 조각 in re.findall(r"<svg.*?</svg>", h, re.S):
        m = re.search(r'viewBox="0 0 (\d+) (\d+)"', 조각)
        if not m:
            continue
        W, H = int(m.group(1)), int(m.group(2))
        for t in re.finditer(r'<text x="([-\d.]+)" y="([-\d.]+)"[^>]*>(.*?)<',
                             조각):
            x, y = float(t.group(1)), float(t.group(2))
            if x < -여유 or y < 0 or x > W + 여유 or y > H + 6:
                나간것.append((round(x), round(y), W, H, t.group(3)[:24]))
    return 나간것


print("[그려지나] 열세 장이 예외 없이 나온다")
그림들 = {}
for 이름, f in sch_flow._목록.items():
    try:
        그림들[이름] = f()
    except Exception as e:
        ok(False, f"{이름} 이 터졌다 -- {type(e).__name__}: {e}")
ok(len(그림들) == len(sch_flow._목록),
   f"{len(그림들)}/{len(sch_flow._목록)} 장이 그려졌다")
ok(len(sch_flow._목록) >= 13,
   f"그림이 {len(sch_flow._목록)}장이다 (붙여 준 화면 수만큼은 있어야 한다)")

print()
print("[깨지나] SVG 가 HTML 안에서 안 터진다")
for 이름, h in 그림들.items():
    ok(h.count("<svg") == h.count("</svg>") and h.count("<svg") >= 1,
       f"{이름}: <svg> 짝이 맞는다 ({h.count('<svg')})")
    ok(bool(_캔버스들(h)), f"{이름}: viewBox 가 있다")
    ok("<div" not in h and "<p>" not in h,
       f"{이름}: SVG 안에 HTML 을 안 섞었다")

print()
print("[새나] 글자가 캔버스 밖으로 안 나간다 -- 나가면 PDF 에서 잘린다")
for 이름, h in 그림들.items():
    나감 = _밖으로나간글자(h)
    ok(not 나감, f"{이름}: 밖으로 나간 글자 없음 (얻은 값 {나감[:2]})")

print()
print("[두부] 라벨에 한글이 없다 -- 이 기계에 한글 글꼴이 없다")
for 이름, h in 그림들.items():
    글자들 = re.findall(r"<text[^>]*>(.*?)</text>", h)
    한 = [t for t in 글자들 if _한글.search(t)]
    ok(not 한, f"{이름}: 한글 라벨 없음 (얻은 값 {한[:2]})")

print()
print("[쓰이나] 지어만 놓고 장에 안 꽂은 그림이 없다")
장글 = ""
for f in sorted(os.listdir(os.path.join(뿌리, "edu"))):
    if re.match(r"T\d+_.*\.py$", f):
        장글 += open(os.path.join(뿌리, "edu", f), encoding="utf-8").read()
안쓴것 = [n for n in sch_flow._목록 if f"sch_flow.{n}(" not in 장글]
ok(not 안쓴것, f"모든 그림이 T 계열 장에 꽂혀 있다 (얻은 값 {안쓴것})")

print()
print("[자해] 일부러 밖으로 뺀 글자를 넣으면 이 검사가 빨개진다")
from sch import svg, 글  # noqa: E402
나쁜그림 = svg(200, 100, 글(400, 300, "way outside"))
ok(bool(_밖으로나간글자(나쁜그림)),
   "밖으로 나간 글자를 실제로 잡는다 -- 안 잡으면 위의 통과가 빈 통과다")
나쁜한글 = svg(200, 100, "<text x=\"10\" y=\"20\">한글라벨</text>")
ok(bool([t for t in re.findall(r"<text[^>]*>(.*?)</text>", 나쁜한글)
         if _한글.search(t)]),
   "한글 라벨을 실제로 잡는다")

print()
if fails:
    print(f"흐름 그림: {len(fails)}개 실패")
    for m in fails:
        print("   -", m)
    sys.exit(1)
print(f"흐름 그림 {len(그림들)}장: 그려짐 · 안 깨짐 · 안 샘 · 두부 없음 · "
      f"장에 꽂힘 -- 통과")
