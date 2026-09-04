"""연속 집필 -- **조립하지 않는다. 한 문장에서 이어 쓴다.**

지금까지는 결말을 먼저 정하고 거꾸로 비트를 쌓았다(episode.py). 그 방식은 인과가 튼튼한
대신 문장이 칸에 갇힌다 -- 씬마다 분량이 할당되고, 회차마다 구조가 요구되고, 관문 아홉이
매번 판정한다. 그렇게 나온 원고가 무겁고 단조로웠다(2026-09-04 사용자 평).

여기서는 반대로 간다:

  · **줄거리를 먼저 짜지 않는다.** 첫 문장 하나에서 다음이 파생되고, 그 다음이 또 파생된다
  · **조립하지 않는다.** 씬도 회차도 없다. 덩어리(chunk)를 이어 붙인다
  · **관문을 끈다.** 남기는 것은 **모순 하나**뿐이다 -- 앞에서 쓴 것과 어긋나는가
  · 어휘도 사건도 자유다. 조건에 맞지 않아도 상관없다

모순만 남기는 이유. 자유롭게 쓰라고 하면 모델은 세 덩어리 뒤에 인물 이름을 바꾸고, 죽은
사람을 걷게 하고, 겨울이던 계절을 여름으로 만든다. 그것만은 코드가 잡아야 한다 -- 취향은
사람이 보면 되지만 모순은 길어질수록 사람도 못 본다.

그래서 **세계를 JSON 원장으로 키운다.** 덩어리마다 추출기가 새로 확정된 것을 뽑아 원장에
더하고, 그때 원장과 부딪히는 것이 있으면 그 덩어리를 기각하고 다시 쓴다.

    python3 novel/flow.py --chars 6000 --out novel/flow.json
    python3 novel/flow.py --resume novel/flow.json --chars 12000   # 이어서
    python3 novel/flow.py --read novel/flow.json                   # 읽기
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import drive as D                                          # noqa: E402
from novel import style                                               # noqa: E402

# 한 번에 받는 덩어리. 너무 크면 모델이 뒤로 갈수록 늘어지고, 너무 작으면 점층이 덩어리
# 경계에 잘린다. 1,200~1,500자가 문장론(점층 -> 전환)이 한 바퀴 도는 크기다.
CHUNK = 1400
MAX_REWRITE = 2          # 모순으로 기각됐을 때 다시 쓰는 횟수
TAIL = 900               # 다음 덩어리에 넘기는 꼬리 길이

FIRST = ("그를 처음 만난 건, 크리스마스 이브의 아이슬란드, "
         "레이캬비크에서 차로 한 시간쯤 떨어진 작은 양조장에서였다.")

# 첫 덩어리에만 붙는 지시. **줄거리가 아니라 흐름의 방향만** 준다 -- 무엇이 일어나는지는
# 정해주지 않는다(그것을 정하는 순간 다시 조립이 된다). 어디를 거쳐 가라는 것뿐이다.
OPENING = """[이 첫 덩어리가 지나갈 자리]
  1. 그 양조장의 내력을 **가짜를 진짜처럼** 풀어라 -- 언제, 누가, 왜 지었는지. 이름과
     연도를 대라. 왜 그렇게 불리는지까지. 그 사람의 사정 한 줄을 붙여라.
  2. 거기서 화자가 무엇을 하고 있었는지로 미끄러져라. 크리스마스 이브다.
  3. 그리고 **오로라 이야기로 흘러라.** 설명하지 말고, 그날 밤 그것이 어땠는지로.
  * 순서만 지키고 내용은 자유다. 사건을 만들려 애쓰지 마라 -- 만나는 장면 하나면 된다."""


# ---------------------------------------------------------------- 원장

def blank(first: str = FIRST) -> dict:
    return {"first": first, "chunks": [], "ledger": {
        "people": {}, "places": {}, "facts": {}, "time": [], "objects": {}}}


def _merge(ledger: dict, delta: dict) -> list:
    """새로 확정된 것을 원장에 더한다. **부딪히는 것만** 돌려준다.

    같은 키에 다른 값이 오는 것만 모순으로 본다. 값이 없던 자리를 채우는 것은 세계가
    자라는 것이지 모순이 아니다 -- 그 구분을 못 하면 두 번째 덩어리부터 전부 기각된다."""
    clashes = []
    for bucket in ("people", "places", "facts", "objects"):
        for k, v in (delta.get(bucket) or {}).items():
            if not isinstance(v, (str, int, float)) or not str(v).strip():
                continue
            old = ledger[bucket].get(k)
            if old and str(old).strip() and str(old).strip() != str(v).strip():
                clashes.append(f"{bucket}.{k}: 앞에서는 '{old}' 였는데 지금 '{v}' 다")
            else:
                ledger[bucket][k] = v
    for t in (delta.get("time") or []):
        if t and t not in ledger["time"]:
            ledger["time"].append(t)
    return clashes


def brief(ledger: dict, limit: int = 40) -> str:
    """원장을 프롬프트에 실을 형태로. 길어지면 최근 것만 -- 앞부분은 어차피 안 바뀐다."""
    out = []
    for bucket, label in (("people", "인물"), ("places", "장소"),
                          ("objects", "사물"), ("facts", "사실")):
        items = list(ledger.get(bucket, {}).items())[-limit:]
        if items:
            out.append(f"  {label}: " + " · ".join(f"{k}={v}" for k, v in items))
    if ledger.get("time"):
        out.append("  시간: " + " → ".join(ledger["time"][-6:]))
    return "\n".join(out) or "  (아직 비어 있다)"


# ---------------------------------------------------------------- 프롬프트

def write_prompt(book: dict, feedback: str = "") -> str:
    tail = "".join(book["chunks"])[-TAIL:]
    opening = not book["chunks"]
    return f"""{'이 문장으로 소설을 연다' if opening else '아래 글을 이어서 쓴다'}.

{style.narrator()}

[이 소설의 온도] **가볍고 재미있게.** 무겁게 가지 마라. 큰일 앞에서도 사소한 것을 신경
쓰고, 농담은 무표정하게 던지고, 과장된 반응은 옆 사람이 한다. 비장해지려는 문장이 나오면
그 다음 줄에서 김을 빼라.

[대사] 거칠고 현실적으로. 다듬지 마라. 말을 끊고, 겹치고, 대답 대신 딴소리를 한다.
어휘는 자유다 -- 상표든 욕이든 외국어든 그 사람이 쓸 법한 말을 그대로 쓴다.

[어디로 가든] **미리 정하지 마라.** 살인이든 불륜이든 사랑이든 실종이든, 지금 쓰는
문장이 다음을 부르는 대로 간다. 앞 덩어리와 크게 상관없는 곳으로 새도 좋다 -- 사람은
원래 상관없는 일들 사이에 산다.
- 새 인물이나 장소가 나오면 **그 사람의 사정을 하나 더 만들어라.** 그 사정이 또 다음
  사람을 부른다. 세계는 그렇게 연쇄로 넓어진다.
- 넓히기만 하고 회수하지 않아도 된다. 끝맺지 않은 것이 남아 있는 편이 진짜 같다.

[리얼리즘] **편의주의 금지 -- 하루에 두 번 울리는 종을 쓰지 마라.**
- 우연이 문제를 풀지 않는다. 필요한 순간에 딱 맞춰 나타나는 사람·전화·열쇠·기억을 쓰지
  마라. 우연은 문제를 **만들 때만** 써라.
- 인물은 화자를 돕기 위해 움직이지 않는다. 자기 사정 때문에 움직이고, 그러다 화자에게
  도움이 되거나 방해가 된다.
- 정보는 대가를 치르고 얻는다. 누가 그냥 설명해주지 않는다. 물어도 대답을 안 하거나,
  절반만 하거나, 틀리게 한다.
- 실패한 것은 실패한 채로 둬라. 잃은 것을 뒤에서 돌려주지 마라.
- 몸은 회복이 느리고, 돈은 모자라고, 날씨는 사정을 봐주지 않는다.

[세계 — 지금까지 확정된 것]
{brief(book['ledger'])}
  * 여기 적힌 것과 어긋나게 쓰지 마라. 나머지는 전부 자유다.
  * 여기 없는 것은 **새로 지어내도 된다.** 지어냈으면 자세히 지어내라 -- 이름, 연도,
    누가 지었는지, 왜 그렇게 불리는지.

{OPENING if opening else ''}

{'[첫 문장 — 이것으로 시작하라]' if opening else '[지금까지의 끝부분]'}
{book['first'] if opening else '...' + tail}

규칙:
- 약 {CHUNK}자를 쓴다. 끊지 말고 이어라. 회차도 씬도 없다.
- **줄거리를 미리 정하지 마라.** 지금 문장에서 다음 문장이 나오게 하라. 앞 문장을 좁히거나,
  키우거나, 뒤집어라(점층). 그러다 밖에서 안으로 들어가라(전환). 그 리듬을 매번 다르게.
- **장문과 단문을 섞어라.** 짧은 '-다' 문장이 세 번 이어지면 그 다음은 반드시 길게 가거나,
  대사를 넣거나, 문장을 끝내지 마라. 지금 이 규칙이 가장 자주 깨진다.
- 사람 이름, 상표, 연도, 지명을 구체적으로 대라. 없는 것도 있는 것처럼 자세히.
{feedback}

산문만 출력한다. 제목도 머리말도 표식도 쓰지 마라."""


def extract_prompt(chunk: str) -> str:
    return f"""아래 글에서 **새로 확정된 사실만** 뽑아 JSON 으로 옮긴다.

{chunk}

규칙:
- 확정된 것만. 추측·비유·인물의 생각은 넣지 마라.
- 값은 짧은 한국어 명사구로. 한 항목에 한 줄.
- 새로 나온 것이 없는 칸은 빈 객체로 둔다.

JSON 만 출력:
{{"people": {{"이름": "그가 누구인가 한 줄"}},
  "places": {{"장소": "어떤 곳인가 한 줄"}},
  "objects": {{"사물": "무엇인가 한 줄"}},
  "facts": {{"항목": "확정된 값"}},
  "time": ["시점 한 줄"]}}"""


# ---------------------------------------------------------------- 루프

def step(book: dict, llm, log=None) -> dict:
    """덩어리 하나. 모순이면 기각하고 다시 쓴다. 반환 {status, chars, clashes}."""
    feedback = ""
    for attempt in range(1, MAX_REWRITE + 2):
        text = D._llm_for(llm, "narrator")(write_prompt(book, feedback)).strip()
        if len(text) < 200:
            D._log(f"[flow] 덩어리가 {len(text)}자로 왔다 -- 다시 받는다")
            continue
        try:
            delta = D.call_json(D._llm_for(llm, "extractor"), extract_prompt(text),
                                label="flow 추출")
        except ValueError as e:
            D._log(f"[flow] 추출 실패({e}) -- 원장 갱신 없이 채택한다")
            delta = {}
        probe = json.loads(json.dumps(book["ledger"]))     # 시험용 사본
        clashes = _merge(probe, delta)
        if not clashes:
            book["ledger"] = probe
            book["chunks"].append(text)
            D._log(f"[flow] 덩어리 {len(book['chunks'])} · {len(text):,}자 · "
                   f"누적 {sum(len(c) for c in book['chunks']):,}자")
            return {"status": "ok", "chars": len(text), "clashes": []}
        D._log(f"[flow] 모순 {len(clashes)}건 -- 다시 쓴다 ({attempt}/{MAX_REWRITE + 1}): "
               f"{clashes[0][:80]}")
        feedback = ("\n[직전 시도가 기각된 이유 — 앞에서 쓴 것과 어긋난다]\n"
                    + "\n".join(f"  · {c}" for c in clashes)
                    + "\n  이것만 고쳐라. 나머지는 자유다.\n")
    return {"status": "blocked", "chars": 0, "clashes": clashes}


def run(book: dict, llm, target: int, path=None, deadline=None) -> dict:
    while sum(len(c) for c in book["chunks"]) < target:
        if deadline and time.time() > deadline:
            D._log("[flow] 시간 상한 -- 여기서 멈춘다")
            break
        r = step(book, llm)
        if path:
            Path(path).write_text(json.dumps(book, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
        if r["status"] != "ok":
            D._log("[flow] 모순을 못 풀었다 -- 멈춘다")
            break
    return {"chunks": len(book["chunks"]),
            "chars": sum(len(c) for c in book["chunks"])}


def text_of(book: dict) -> str:
    return "\n\n".join(book["chunks"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="novel/flow.json")
    ap.add_argument("--resume", default="")
    ap.add_argument("--read", default="")
    ap.add_argument("--chars", type=int, default=6000)
    ap.add_argument("--first", default=FIRST)
    ap.add_argument("--hours", type=float, default=3.0)
    a = ap.parse_args()

    if a.read:
        book = json.loads(Path(a.read).read_text(encoding="utf-8"))
        print(text_of(book))
        print(f"\n---\n덩어리 {len(book['chunks'])}개 · "
              f"{sum(len(c) for c in book['chunks']):,}자", file=sys.stderr)
        return 0

    path = a.resume or a.out
    book = (json.loads(Path(path).read_text(encoding="utf-8"))
            if a.resume and Path(a.resume).exists() else blank(a.first))
    D._log(f"[flow] 목표 {a.chars:,}자 · 지금 "
           f"{sum(len(c) for c in book['chunks']):,}자")
    r = run(book, D.default_llm, a.chars, path, time.time() + a.hours * 3600)
    D._log(f"[flow] 끝 -- 덩어리 {r['chunks']}개 · {r['chars']:,}자 · {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
