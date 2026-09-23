# -*- coding: utf-8 -*-
"""**그림이 XML 로 읽히는가 -- 파서에 실제로 넣어 본다.**

실측 2026-09-23. 테이프아웃 상태 지도를 `.svg` 파일 하나로 내서 브라우저로
열었더니 **빈 쪽**이 나왔다. 파 보니 이 저장소가 내는 **그림 전부**가 XML 로
안 읽히고 있었다.

    font-family=&#x27;NanumGothic&#x27;,&#x27;Noto Sans CJK KR&#x27;,sans-serif
                ^ 따옴표 없이 시작해서 첫 공백에서 잘린다

**보고서 PDF 는 멀쩡해 보였다.** HTML 안에 박힌 SVG 는 너그럽게 읽히기
때문이다. 그래서 그림 수백 장을 내는 동안 아무도 몰랐다 -- **그림을 파일
하나로 건네 보기 전에는 드러나지 않는 자리**였다.

여기서는 **눈으로 안 본다.** `xml.etree` 에 넣어 본다. 그리고 검사가 제
구실을 하는지 보려고 **옛 꼴을 일부러 만들어** 빨개지는지도 본다 -- 늘
초록인 장치는 없느니만 못하다.

실행: python3 tests/test_그림XML.py
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


from house import tapeout as TO       # noqa: E402
from house import viz as V            # noqa: E402

# 그림마다 **작은 진짜 입력**을 준다. 빈 입력만 주면 빈그림 한 장만 재게 된다.
그림들 = [
    ("빈그림", lambda: V.빈그림()),
    ("막대", lambda: V.막대(["가", "나", "다"], [3, 1, 2], "제목", "y")),
    ("선", lambda: V.선([1, 2, 3], [("ㄱ", [1, 4, 9]), ("ㄴ", [2, 2, 2])], "제목")),
    ("산점", lambda: V.산점([1, 2, 3], [2, 1, 3], "제목")),
    ("히스토그램", lambda: V.히스토그램([1, 2, 2, 3, 5, 8], 제목="제목")),
    ("히트맵", lambda: V.히트맵([[1, 2], [3, 4]], "제목")),
    ("게이지묶음", lambda: V.게이지묶음([("가", 0.4, "40 %", "#1f6feb")], "제목")),
    ("흐름", lambda: V.흐름(["가", "나", "다"], "제목", 아래글="아래글")),
    ("상태도", lambda: V.상태도(["IDLE", "RUN"], [("IDLE", "RUN", "go")], "제목")),
    ("파형", lambda: V.파형([("clk", "0101"), ("d", "0011")], "제목")),
    ("예약표", lambda: V.예약표(["mul", "add"], [("t0", 0, [0, 1]), ("t1", 1, [0])],
                            "제목")),
    ("블록도", lambda: V.블록도([("A", 20, 20, 90, 40, "#eef4fb", "부제"),
                            ("B", 200, 20, 90, 40, "#fdf3e0", "")],
                           [("A", "B", "x", None)], "제목")),
    # **`표()` 는 여기 안 넣는다.** 그것은 SVG 가 아니라 HTML `<table>` 조각이라
    # XML 파서에 넣을 물건이 아니다. 그 자리는 tests/test_보고서글자.py 가 본다.
    ("테이프아웃 지도", lambda: TO.지도()),
    ("테이프아웃 지도(주인)", lambda: TO.지도(주인="dft")),
]

print("\n[1] 그림마다 XML 파서에 넣어 본다")
난것 = {}
for 이름, 짓기 in 그림들:
    try:
        g = 짓기()
    except Exception as e:                                   # noqa: BLE001
        ok(False, f"{이름} — 그림을 짓다가 죽었다: {type(e).__name__}: {e}")
        continue
    난것[이름] = g
    try:
        뿌리태그 = ET.fromstring(g).tag
        ok(뿌리태그.endswith("svg"), f"{이름} — XML 로 읽히고 뿌리가 svg 다")
    except ET.ParseError as e:
        ok(False, f"{이름} — XML 이 깨졌다: {e}")

print("\n[2] 이 검사가 그 결함을 실제로 잡나 -- 옛 꼴을 만들어 본다")
옛꼴 = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" '
      "font-family=&#x27;NanumGothic&#x27;,sans-serif font-size=\"11\"></svg>")
깨졌나 = False
try:
    ET.fromstring(옛꼴)
except ET.ParseError:
    깨졌나 = True
ok(깨졌나, "따옴표 없는 font-family 는 이 파서가 빨갛게 낸다 — 늘 초록이 아니다")

print("\n[3] 지도가 산 데이터에서 나온다 -- 칸 수가 마일스톤 수와 같다")
g = 난것.get("테이프아웃 지도") or TO.지도()
뿌리요소 = ET.fromstring(g)
글들 = [(e.text or "") for e in 뿌리요소.iter() if e.tag.endswith("text")]
이름들 = [m["이름"] for m in TO.마일스톤표()]
빠진 = [n for n in 이름들 if n not in 글들]
ok(not 빠진, f"마일스톤 {len(이름들)}칸이 한 칸도 안 빠지고 그림에 있다 ({빠진})")
칩글 = {TO._짧게(c["이름"]) for m in TO.마일스톤표() for c in m["조건"]}
빠진칩 = [x for x in 칩글 if x not in 글들]
ok(not 빠진칩, f"항목 {len(칩글)}개가 한 개도 안 빠지고 칩으로 찍힌다 ({빠진칩[:3]})")
w = TO.어디까지()
ok(("◀ 지금 여기" in 글들) == bool(w["막힌곳"]),
   f"막힌 칸이 있을 때만 '지금 여기' 를 찍는다 (막힌곳 {w['막힌곳']})")

print("\n[4] 글이 상자를 안 넘친다 -- 칩 폭을 글자 너비로 잡았나")
넘침 = []
for m in TO.마일스톤표():
    for c in m["조건"]:
        글 = TO._짧게(c["이름"])
        여유 = (V.글자너비(글, 9) + 16) - V.글자너비(글, 9)
        if 여유 < 12:
            넘침.append(글)
ok(not 넘침, f"칩마다 글 좌우 여백이 있다 ({넘침[:3]})")
_긴것 = TO._짧게("아주 긴 항목 이름을 넣어 보면 어떻게 되나 하는 물음 (괄호 속은 떨어진다)")
ok(len(_긴것) <= 30 and "(" not in _긴것,
   f"긴 이름은 줄이고 괄호 속 설명은 떨어뜨린다 -> {_긴것!r}")

print("\n" + "=" * 62)
if FAIL:
    print(f"실패 {len(FAIL)}개")
    for x in FAIL:
        print("  · " + x)
    raise SystemExit(1)
print("전부 통과")
