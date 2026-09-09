"""**24시간 루프.** 회차를 이어서 낸다.

디렉터(카드)와 작가(산문)를 **가른다** -- 카드는 회차당 한 번, 300토큰 남짓이고
무엇을 쓸지가 거기서 갈린다. 산문은 토큰의 대부분이다.

키가 없으면 **못 돌린다고 사실대로 말한다.** 다른 것으로 대신하지 않는다.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from nv2 import card as CARD, ledger as LG, ruler, write


def blank(seed: str, arc: dict, 분량: int = 5000) -> dict:
    return {"씨앗": seed, "회차": 0, "회차분량": 분량, "원장": LG.blank(),
            "도착지": arc, "회차들": [], "장부": []}


def step(book: dict, llm_writer, llm_director, owed=()) -> dict:
    eps = book.get("회차들") or []
    prev = eps[-1]["글"] if eps else ""
    hook = (book.get("도착지") or {}).get("_끝", "")
    c = CARD.make(book, book.get("도착지") or {}, llm_director, prev_hook=hook)
    if c.get("_실패"):
        book.setdefault("장부", []).append(f"회차 {book['회차']}: 각본 실패 -- {c['_실패']}")
        c = {}
    r = write.once(book, c, llm_writer, prev=prev, owed=owed)
    if r["상태"] != "ok":
        book.setdefault("장부", []).append(f"회차 {book['회차']}: {r['상태']}")
        return r
    eps.append({"회차": book["회차"], "카드": c, "글": r["글"], "잰것": r.get("잰것", {})})
    book["회차들"] = eps
    book["회차"] = int(book["회차"]) + 1
    if c.get("끝"):
        book.setdefault("도착지", {})["_끝"] = c["끝"]
    return r


def loop(book: dict, path: Path, llm_writer, llm_director, hours: float = 24.0,
          target: int = 0, log=print) -> dict:
    end = time.time() + hours * 3600
    owed: list = []
    while time.time() < end:
        n = book["회차"]
        r = step(book, llm_writer, llm_director, owed=owed)
        owed = r.get("넘길말") or []
        path.write_text(json.dumps(book, ensure_ascii=False), encoding="utf-8")
        wrote = sum(len(e["글"]) for e in book.get("회차들") or [])
        log(f"[회차 {n}] {len(r.get('글', '')):,}자 · 누적 {wrote:,}자"
            + (f" · 수리 {len(r.get('수리') or [])}건" if r.get("수리") else "")
            + (f" · 어긋남 {[a for a, _d, _v in r.get('어긋남') or []]}" if r.get("어긋남") else "")
            + (f" · 예산에 막혀 뺀 것 {r['떨어뜨림']}" if r.get("떨어뜨림") else ""))
        if target and wrote >= target:
            log(f"목표 {target:,}자에 닿았다.")
            break
    return book


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="회차를 이어서 낸다")
    ap.add_argument("--원고", default="nv2/book.json")
    ap.add_argument("--시간", type=float, default=24.0)
    ap.add_argument("--글자", type=int, default=0)
    ap.add_argument("--분량", type=int, default=5000, help="회차 하나의 분량")
    a = ap.parse_args(argv)
    print("이 명령은 화자(LLM)를 붙여야 돈다. 키가 없으면 돌지 않는다 --"
          " 다른 것으로 대신하지 않는다.", file=sys.stderr)
    print(f"  원고 {a.원고} · {a.시간}시간 · 회차 {a.분량:,}자"
          f" · 사는 규칙 {[r.축 for r in __import__('nv2.rules', fromlist=['x']).live()]}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
