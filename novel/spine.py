"""**한 작품의 뼈대를 뽑아 그 순서를 따라 쓴다.**

사용자가 방향으로 삼고 싶은 작품(I)이 있다. 그 이야기의 **차례**를 따라가되 문장은
우리 것으로, 꼴은 웹소설로 쓴다.

어떻게. 작품을 토막으로 자른 뒤 토막마다 **한 줄짜리 상태 변화**만 뽑는다(추출기 =
Gemini, 토막당 한 번). 뽑는 것은 TAXONOMY 서사층의 최소 단위다: 무엇이 달라졌는가 ·
누구에게 · 무엇 때문에. **문장은 안 가져온다** -- 원문 문장이 프롬프트로 들어가면
원고가 그것을 베낀다(다섯 번 겪었다).

그러고 나면 집필할 때 덩어리마다 비트를 하나씩 준다. 우리 원고는 그 차례를 따라가되
무엇으로 그렇게 되는지는 스스로 정한다.

**한계를 밝힌다.** 남의 작품의 사건 순서를 그대로 따라 쓰는 것은 그 작품에 기댄 글이
된다. 습작·연구로는 흔한 방식이지만 발표할 것이라면 사람이 판단할 몫이다. 뼈대는
저장소에 안 올린다(gitignore).

    python3 novel/spine.py build novel/corpus/I --out novel/spine.json
    python3 novel/spine.py show  novel/spine.json
    python3 novel/spine.py cover novel/spine.json novel/final.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import plot, profile as PF                                 # noqa: E402

PATH = Path(os.environ.get("DRIFT_SPINE", Path(__file__).resolve().parent / "spine.json"))
# 한 토막에서 뽑는 비트 수. 하나면 놓치고, 여럿이면 프롬프트가 목록이 된다.
PER_UNIT = int(os.environ.get("DRIFT_SPINE_PER", "1"))


def ask(text: str) -> str:
    """**짧게 묻는다.** 요약을 시키는 것이 아니라 상태 변화 한 줄을 시킨다."""
    kinds = " · ".join(plot.CHANGE)
    return f"""아래는 어떤 소설의 한 대목이다. 이 대목에서 **무엇이 달라졌는지** 한 줄로 적어라.

{text[:6000]}

규칙:
- 줄거리를 요약하지 마라. **달라진 것 하나**만 적는다.
- 갈래는 이 중 하나로: {kinds}
- 원문 문장을 옮겨 적지 마라. 낱말도 그대로 쓰지 마라 -- 무슨 일이 있었는지만 네 말로.
- 사람 이름은 그대로 써도 된다.

{{"갈래": "위 중 하나", "무엇": "한 줄", "누구": "누구에게"}} 꼴의 JSON 하나로만 답한다."""


def build(root, llm=None, out=None) -> dict:
    """토막마다 비트 하나. **덩어리당 호출 한 번**이고 그것으로 끝이다."""
    from novel import drive as D
    # _extractor(None) 은 None 을 돌려준다(주입한 것은 주입한 대로 쓰는 규칙).
    call = llm or D._extractor(D.default_llm)
    beats = []
    files = PF.unit_files(root)
    for i, (work, f) in enumerate(files, 1):
        text = f.read_text(encoding="utf-8")
        if len(text) < PF.MIN_UNIT:
            continue
        try:
            got = D.call_json(call, ask(text), tries=1, label=f"뼈대 {i}/{len(files)}")
        except Exception as e:
            print(f"  {i}: 못 뽑았다 ({type(e).__name__}) -- 건너뛴다", file=sys.stderr)
            continue
        if not isinstance(got, dict) or not got.get("무엇"):
            continue
        beats.append({"n": len(beats) + 1, "from": f.name,
                      "갈래": str(got.get("갈래", ""))[:12],
                      "무엇": str(got["무엇"])[:120],
                      "누구": str(got.get("누구", ""))[:60]})
        if i % 10 == 0:
            print(f"  {i}/{len(files)} · 비트 {len(beats)}개", file=sys.stderr)
    data = {"_": "남의 작품에서 뽑은 사건 차례. 문장은 안 들어 있다.",
            "_from": str(root), "beats": beats}
    (Path(out) if out else PATH).write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def load(path=None) -> list:
    p = Path(path) if path else PATH
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("beats") or []


def at(n: int, path=None) -> dict | None:
    """덩어리 n 이 따라갈 비트. 원고가 뼈대보다 길어지면 남은 것을 그대로 쓴다."""
    beats = load(path)
    if not beats:
        return None
    return beats[min(n, len(beats) - 1)]


def brief(n: int, path=None) -> str:
    b = at(n, path)
    if not b:
        return ""
    return ("[이 대목에서 일어날 일] **하나만.** 다 벌이지 마라.\n"
            f"  · 무엇이 달라지나: **{b['갈래']}** -- {b['무엇']}\n"
            f"  · 누구에게: {b['누구']}\n"
            "  · **무엇으로 그렇게 되는지는 네가 정한다.** 이 대목이 끝났을 때 위 하나는\n"
            "    실제로 달라져 있어야 한다. 말로 정리하지 말고 겪게 해라.\n"
            "  · 문장과 꼴은 우리 것이다 -- 위는 차례일 뿐 본보기가 아니다.")


def cover(spine_path, book_path) -> dict:
    """**얼마나 따라갔나.** 원고 덩어리 수와 비트 수를 견준다(호출 없음)."""
    beats = load(spine_path)
    book = json.loads(Path(book_path).read_text(encoding="utf-8"))
    n = len(book.get("chunks") or [])
    return {"비트": len(beats), "덩어리": n,
            "따라간 몫": min(1.0, n / max(1, len(beats)))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="한 작품의 사건 차례")
    ap.add_argument("cmd", choices=["build", "show", "cover"])
    ap.add_argument("a", nargs="?", default="")
    ap.add_argument("b", nargs="?", default="")
    ap.add_argument("--out", default="")
    x = ap.parse_args(argv)
    if x.cmd == "build":
        d = build(x.a, out=x.out or None)
        print(f"비트 {len(d['beats'])}개 -> {x.out or PATH}")
        return 0
    if x.cmd == "show":
        for b in load(x.a or None)[:200]:
            print(f"{b['n']:>4}  {b['갈래']:<6} {b['무엇'][:60]}  ({b['누구'][:20]})")
        return 0
    c = cover(x.a or None, x.b)
    print(f"비트 {c['비트']}개 · 우리 덩어리 {c['덩어리']}개 · 따라간 몫 {c['따라간 몫']:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
