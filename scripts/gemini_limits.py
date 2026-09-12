#!/usr/bin/env python3
"""**모델이 한 번에 뭘 할 수 있는지 API 에 물어본다.** 그리고 우리가 실제로 쓰는 값과
견준다.

왜 필요한가. 두 숫자를 우리가 **짐작으로** 쓰고 있었다.

  1. `GEMINI_MAX_OUTPUT=8192` -- 이건 모델의 한도가 아니라 **우리가 요청에 적어 보내는
     상한**이다. 모델의 진짜 한도(`outputTokenLimit`)는 ListModels 가 알려 주는데,
     `bot_tools.list_available_models()` 는 그 응답을 받아 놓고 **이름만 꺼내고 버린다**
     (bot_tools.py:443 -- `inputTokenLimit`·`outputTokenLimit` 을 안 읽는다).
     한도가 8,192보다 크면 우리는 매 호출에서 그 차이만큼을 스스로 버리고 있다.

  2. `flow.py:CHUNK` 의 주석이 "8,192토큰 = 한글로 대략 8천 자" 라고 적어 뒀다.
     **대략**이다. countTokens 가 정확히 답해 주는 것을 짐작으로 두었다.

둘 다 공짜로 확인된다 -- ListModels 도 countTokens 도 generateContent 쿼터를 안 쓴다.
산문 한 자도 안 만든다.

  python3 scripts/gemini_limits.py                  # 한도표
  python3 scripts/gemini_limits.py --book novel/drift.json   # 실제 원고로 자/토큰을 잰다

출력의 마지막 줄이 이 저장소의 지금 설정과 견준 결론이다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import requests                                              # noqa: E402

BASE = "https://generativelanguage.googleapis.com/v1beta"
# 이 저장소가 실제로 쓰는 축. 여기 없는 모델도 표에는 나오지만 결론은 이것들로 낸다.
# 소설이 안 쓰는 것들. 표가 37줄이 되면 정작 봐야 할 flash 계열이 안 보인다
# (실측 2026-09-07: lyria(음악) · deep-research · robotics · transcribe · nano-banana 가
#  같이 나왔다). **거르는 것은 표시일 뿐 한도 판단과 무관하다.**
_SKIP = ("embedding", "aqa", "imagen", "veo", "tts", "vision", "learnlm",
         "lyria", "deep-research", "robotics", "computer-use", "antigravity",
         "transcribe", "banana", "image")


def _keys() -> list:
    """.env 와 환경변수에서 키를 모은다. llm_pool 과 같은 자리를 본다."""
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    out = []
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEYS"):
        v = os.environ.get(name, "")
        out += [x.strip() for x in v.replace(";", ",").split(",") if x.strip()]
    seen, uniq = set(), []
    for k in out:
        if k not in seen:
            seen.add(k)
            uniq.append(k)
    return uniq


def parse(data: dict) -> list:
    """ListModels 응답에서 쓸 것만 -- **한도까지 들고 온다.**

    `bot_tools.list_available_models()` 는 같은 응답을 받아 이름만 꺼내고 한도를
    버린다. 그래서 이 저장소는 모델이 한 번에 얼마를 낼 수 있는지 모른 채
    8,192 라는 자기 상한만 보내 왔다. 여기서는 버리지 않는다.

    HTTP 와 갈라 둔 이유는 **네트워크 없이 검사하려고**다.
    """
    rows = []
    for m in data.get("models", []):
        if "generateContent" not in (m.get("supportedGenerationMethods") or []):
            continue
        name = m.get("name", "")
        name = name[len("models/"):] if name.startswith("models/") else name
        if any(s in name.lower() for s in _SKIP):
            continue
        rows.append({"name": name,
                     "in": int(m.get("inputTokenLimit") or 0),
                     "out": int(m.get("outputTokenLimit") or 0),
                     # **무엇을 지원하는지도 들고 온다.** 안 들고 왔더니 countTokens 를
                     # 지원하지 않는 모델에 countTokens 를 걸어 404 를 받았다
                     # (실측 2026-09-07 VM).
                     "does": tuple(m.get("supportedGenerationMethods") or ())})
    return rows


def models(key: str, timeout: float = 20.0) -> list:
    """ListModels 를 부른다. **생성 쿼터를 안 쓰는 메타데이터 조회다.**"""
    r = requests.get(f"{BASE}/models", params={"key": key, "pageSize": 1000},
                     timeout=timeout)
    r.raise_for_status()
    return parse(r.json())


def count(key: str, model: str, text: str, timeout: float = 20.0) -> int:
    """countTokens -- **짐작 대신 이것을 쓴다.** 생성 쿼터를 안 쓴다."""
    # 열쇠는 models() 와 같게 **params** 로 보낸다. 전에는 여기 없는 이름(_hdr · _die)을 불러
    # 이 함수가 불리는 순간 NameError 였다(실측 2026-09-12, rehearsal.미정의이름 이 찾았다).
    r = requests.post(f"{BASE}/models/{model}:countTokens", params={"key": key},
                      json={"contents": [{"parts": [{"text": text}]}]},
                      timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"countTokens 실패 ({model}): {r.status_code} {r.text[:200]}")
    return int(r.json().get("totalTokens") or 0)


def sample(book: str) -> str:
    """실제 원고에서 표본을 뽑는다. 없으면 빈 문자열 -- **지어내지 않는다**."""
    p = Path(book)
    if not p.exists():
        return ""
    try:
        b = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return ""
    return "".join(b.get("chunks") or [])[:4000]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default=str(REPO / "novel" / "drift.json"),
                    help="자/토큰 비를 잴 원고 (없으면 그 단계를 건너뛴다)")
    a = ap.parse_args()

    keys = _keys()
    if not keys:
        print("키가 없다. .env 의 GEMINI_API_KEY 를 확인해라.", file=sys.stderr)
        return 1

    try:
        rows = models(keys[0])
    except Exception as e:
        print(f"ListModels 실패: {e}", file=sys.stderr)
        return 1
    if not rows:
        print("쓸 수 있는 모델이 없다.", file=sys.stderr)
        return 1

    ours = int(os.environ.get("GEMINI_MAX_OUTPUT", "8192"))
    print(f"모델 {len(rows)}개 (키 {len(keys)}개 중 첫 키로 조회)")
    print(f"{'모델':38} {'입력 한도':>10} {'출력 한도':>10}   우리가 쓰는 값")
    print("-" * 82)
    for m in sorted(rows, key=lambda r: -r["out"]):
        gap = ""
        if m["out"] > ours:
            # **"버리고 있다" 고 쓰지 않는다.** 그렇게 찍었더니 그렇게 읽혔는데,
            # 틀린 읽기였다(실측 2026-09-07): 상한이 8,192여도 **닿지를 않는다**.
            # 같은 날 10만 자 원고를 재보니 3,200자를 시켜 평균 1,734자가 왔다.
            # 잘리고 있는 것이 아니라 모자라게 오는 것이다 -- 상한을 올려도 안 변한다.
            # 여유일 뿐이라고 적는다.
            gap = f"  <- {m['out'] / ours:.0f}배 여유 (지금은 안 닿는다)"
        print(f"{m['name']:38} {m['in']:>10,} {m['out']:>10,}   {ours:,}{gap}")

    best = max(rows, key=lambda r: r["out"])
    # **잴 모델은 따로 고른다.** 출력 한도가 제일 큰 것이 countTokens 를 지원한다는
    # 보장이 없다 -- 그렇게 골랐다가 404 를 받았다(실측 2026-09-07 VM).
    countable = [m for m in rows if "countTokens" in m["does"]]
    ruler = max(countable, key=lambda r: r["out"]) if countable else None
    print("-" * 82)

    txt = sample(a.book)
    if not txt:
        print(f"원고가 없어 자/토큰은 못 쟀다 ({a.book}).")
        print("  -- 그 비를 모르면 덩어리 크기를 토큰으로 환산할 수 없다.")
        return 0
    if ruler is None:
        print("countTokens 를 지원하는 모델이 없다 -- 자/토큰은 못 잰다.")
        print("  (그 비를 모르면 덩어리 크기를 토큰으로 환산할 수 없다)")
        return 0
    try:
        n = count(keys[0], ruler["name"], txt)
    except Exception as e:
        print(f"{e}", file=sys.stderr)
        return 1
    if not n:
        print("countTokens 가 0 을 돌려줬다 -- 표본을 못 읽었다.", file=sys.stderr)
        return 1

    per = len(txt) / n
    print(f"실제 원고 {len(txt):,}자 = {n:,}토큰   ->  1토큰당 {per:.2f}자")
    print(f"  ({ruler['name']} 로 쟀다. 토크나이저는 모델 계열마다 다를 수 있다)")
    print()
    # **여기서 지어내지 않는다.** 잰 값으로만 환산한다.
    can = int(best["out"] * per)
    now = int(ours * per)
    from novel import flow
    print(f"한 호출로 받을 수 있는 글자   지금 설정 {now:,}자 / 모델 한도 {can:,}자")
    print(f"시킨 덩어리                   DRIFT_CHUNK = {flow.CHUNK:,}자"
          f"  (모델 한도의 {flow.CHUNK / can * 100:.1f}%)")
    print()
    print("  **상한과 실제로 오는 양은 다르다.** 시킨 만큼 오는지는 원고를 재야 안다:")
    print("    python3 -c \"import json,statistics as st;"
          "c=[len(x) for x in json.load(open('novel/drift.json'))['chunks']];"
          "print(len(c),'덩어리 · 평균',round(st.mean(c)))\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
