#!/usr/bin/env python3
# 결정 원장(ctrl/결정.jsonl)을 사람이 보기 좋게 표로 읽는다.
#
# **쓰기는 자연어로 봇이 한다** -- 이 파일은 읽기(+검사)만 한다. 하드코딩 파이프라인이
# 아니라, 봇이 남긴 결정을 눈으로 확인하는 창이다.
#
# 규율 검사 하나: 결정마다 '무효화'(이 결정이 깨지는 조건)가 비어 있으면 빨간다 --
# 못 적으면 그것은 결정이 아니라 광고다(CLAUDE.md '과장하지 않는다').
import json, sys, pathlib

LEDGER = pathlib.Path(__file__).with_name("결정.jsonl")

def 읽기():
    if not LEDGER.exists():
        print("결정 원장이 아직 없다:", LEDGER); return []
    줄들 = []
    for i, line in enumerate(LEDGER.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            줄들.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"[{i}행] JSON 이 아니다: {e}"); sys.exit(1)
    return 줄들

def 보이기(줄들):
    빈무효화 = []
    for d in 줄들:
        print(f"── {d.get('날짜','?')}  {d.get('결정','?')}")
        print(f"   근거  : {d.get('근거','(없음)')}")
        무효화 = (d.get('무효화') or '').strip()
        print(f"   무효화: {무효화 or '(비어 있음 ← 채워라)'}")
        if d.get('대안'):
            print(f"   대안  : {d['대안']}")
        if not 무효화:
            빈무효화.append(d.get('결정','?'))
        print()
    print(f"결정 {len(줄들)}개.", end=" ")
    if 빈무효화:
        print(f"**무효화 빈 것 {len(빈무효화)}개: {빈무효화}** — 결정이 아니라 광고다. 채워라.")
        return 1
    print("모두 무효화 조건이 적혀 있다 — 정직한 원장.")
    return 0

if __name__ == "__main__":
    sys.exit(보이기(읽기()))
