"""**의미층까지 뜯어 재고 그대로 시킨다** -- 인과 · 갈등 · 복선 · 거리 · 속도.

지금까지는 "의미는 지면에 없으니 못 잰다" 고 적고 프롬프트에서 뺐다. 문면만으로
문장은 겹칠 수 있지만 **이야기가 겹치지는 않는다.** 연구용으로 최대한 복제하는 것이
목적이면 의미층도 재야 한다.

재는 방법은 하나뿐이다. **읽는 것을 시킨다.** 토막마다 한 번 물어서 스물두 칸짜리
기록 하나를 받는다(추출기 = Gemini, 토막당 1회. A 는 67토막이니 예순일곱 번, 한 번
뽑아 두면 끝이다). spine.py 가 한 칸(무엇이 달라졌나)만 받던 것을 스물두 칸으로
넓힌 것이다 -- **호출 수는 그대로다.**

받는 칸은 전부 **셀 수 있는 것**이다. 자유 서술은 두 칸(무엇 · 누구)뿐이고 나머지는
정해진 낱말 중 하나이거나 수다. 그래야 A 의 분포를 내고, 우리 원고를 같은 추출기로
재서 견줄 수 있다. **재는 축에 매이지 않은 줄은 프롬프트에 안 쓴다** 는 계약은
여기서도 그대로다.

    python3 scripts/deep_learn.py novel/corpus --only A     # 예순일곱 번, 한 번만
    python3 novel/deep.py show                              # 분포를 본다
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

PATH = Path(os.environ.get("DRIFT_DEEP",
                           Path(__file__).resolve().parent / "deep.json"))

# 칸 하나하나. (물음, 고를 낱말들 또는 수의 범위)
# **고를 낱말을 못 정하는 칸은 안 만든다** -- 세지 못하면 분포도 없고 견줄 수도 없다.
PICK = {
    "장면꼴": ("이 대목은 무엇인가", ("장면", "여파", "요약", "회상")),
    "속도":   ("시간을 어떻게 다루나", ("건너뜀", "요약", "장면", "늘임")),
    "거리":   ("서술이 인물에게서 얼마나 떨어져 있나", ("생각속", "어깨너머", "멀리")),
    "시간":   ("앞 대목과의 시간 관계", ("이어짐", "건너뜀", "되돌아감")),
    "자리":   ("어디인가", ("실내", "실외", "이동중")),
    "원인":   ("이 대목의 일이 무엇 때문에 일어났나",
               ("인물의결정", "타인의행동", "우연", "환경", "앞대목")),
    "갈등축": ("무엇과 무엇이 부딪히나",
               ("사람대사람", "자신과", "세계와", "제도와", "없음")),
    "갈등끝": ("그 부딪힘이 이 대목에서 어떻게 되나",
               ("해소", "유예", "악화", "없음")),
    "앎격차": ("독자와 인물 중 누가 더 아나", ("독자만", "인물만", "같음")),
    "욕망":   ("이 대목에서 바라던 것이 어떻게 되나",
               ("얻음", "잃음", "유예", "없음")),
    "닫는법": ("이 대목이 무엇으로 닫히나",
               ("질문", "위협", "등장", "결정", "여운", "정리")),
}
# 수로 받는 칸. (물음, 낮은값, 높은값)
NUM = {
    "원인거리": ("그 원인이 몇 대목 전에 놓였나(같은 대목이면 0)", 0, 30),
    "사슬깊이": ("이 일이 몇 단계짜리 원인 사슬 끝인가", 1, 4),
    "갈등세기": ("부딪힘의 세기(0 없음 ~ 4 돌이킬 수 없음)", 0, 4),
    "거둔거리": ("앞에 심어 둔 것을 거두었다면 몇 대목 전 것인가(아니면 0)", 0, 60),
    "새사실":   ("독자가 이 대목에서 새로 알게 된 사실의 수", 0, 5),
    "인물수":   ("이 대목에 나오는 사람 수", 0, 12),
    "새인물":   ("그중 처음 나오는 사람 수", 0, 5),
}
# 자유 서술. **두 칸뿐이다.** 늘리면 요약이 되고, 요약은 원고가 베낀다.
FREE = ("무엇", "누구", "심은것")

# 프롬프트에 실을 칸과 그 말투. 여기 없는 칸은 재기만 하고 안 싣는다.
SAY = {
    "장면꼴": "이 대목의 꼴",
    "속도": "시간 다루기",
    "거리": "서술의 거리",
    "시간": "앞 대목과의 이음",
    "자리": "자리",
    "원인": "이 일이 일어나는 까닭",
    "갈등축": "부딪히는 것",
    "갈등세기": "부딪힘의 세기(0~4)",
    "갈등끝": "그 부딪힘의 끝",
    "앎격차": "독자와 인물의 앎",
    "욕망": "바라던 것",
    "닫는법": "닫는 법",
    "사슬깊이": "원인 사슬의 깊이",
    "새사실": "새로 알려 줄 사실의 수",
    "인물수": "나오는 사람 수",
    "새인물": "처음 나오는 사람 수",
}


def ask(text: str) -> str:
    """**한 번에 다 묻는다.** 칸마다 따로 물으면 스물두 배가 든다."""
    lines = []
    for k, (q, opts) in PICK.items():
        lines.append(f'  "{k}": {q}? -- {" · ".join(opts)} 중 하나')
    for k, (q, lo, hi) in NUM.items():
        lines.append(f'  "{k}": {q}? -- {lo}부터 {hi}까지의 수')
    lines.append('  "무엇": 이 대목에서 달라진 것 하나를 한 줄로')
    lines.append('  "누구": 누구에게')
    lines.append('  "심은것": 나중에 쓰일 만한 것을 처음 놓았다면 짧은 이름, 없으면 ""')
    body = "\n".join(lines)
    return f"""아래는 어떤 소설의 한 대목이다. 읽고 아래 칸을 채워라.

{text[:6000]}

====
{body}

규칙:
- **원문 문장을 옮기지 마라.** 낱말도 그대로 쓰지 마라. 무슨 일인지만 네 말로.
- 줄거리를 요약하지 마라. 칸만 채운다.
- 고를 낱말이 정해진 칸은 **반드시 그 중 하나**로 답한다. 새 낱말을 만들지 마라.
- 모르면 가장 가까운 것을 고른다. 빈칸으로 두지 마라.

JSON 하나로만 답한다."""


def clean(got: dict) -> dict:
    """받은 것을 자로 다듬는다. **정해진 낱말이 아니면 버린다** -- 새 낱말이 섞이면
    분포가 조용히 망가진다."""
    out = {}
    for k, (_q, opts) in PICK.items():
        v = str(got.get(k, "")).strip()
        out[k] = v if v in opts else ""
    for k, (_q, lo, hi) in NUM.items():
        try:
            out[k] = max(lo, min(hi, int(float(got.get(k, lo)))))
        except (TypeError, ValueError):
            out[k] = None
    for k in FREE:
        out[k] = str(got.get(k, ""))[:120]
    return out


def learn(recs: list) -> dict:
    """분포를 낸다. 고르는 칸은 몫, 수는 폭(25~75%)."""
    out = {"share": {}, "band": {}, "n": len(recs)}
    for k in PICK:
        c = Counter(r[k] for r in recs if r.get(k))
        tot = sum(c.values()) or 1
        out["share"][k] = {a: round(n / tot, 4) for a, n in c.most_common()}
    for k in NUM:
        v = sorted(r[k] for r in recs if isinstance(r.get(k), int))
        if len(v) < 5:
            continue
        n = len(v)
        out["band"][k] = {"lo": v[n // 4], "mid": v[n // 2],
                          "hi": v[min(n - 1, n * 3 // 4)]}
    # **복선의 사거리**는 거둔 것만 모아 따로 본다. 0(안 거둠)이 섞이면 뭉개진다.
    far = sorted(r["거둔거리"] for r in recs
                 if isinstance(r.get("거둔거리"), int) and r["거둔거리"] > 0)
    if far:
        out["복선"] = {"거두는 몫": round(len(far) / max(1, len(recs)), 4),
                       "사거리 가운데": far[len(far) // 2],
                       "제일 먼 것": far[-1]}
    plant = [r for r in recs if r.get("심은것")]
    out["심는 몫"] = round(len(plant) / max(1, len(recs)), 4)
    return out


def load(path=None) -> dict:
    p = Path(path) if path else PATH
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def at(n: int, path=None) -> dict | None:
    """덩어리 n 이 따라갈 기록. 원고가 표본보다 길어지면 마지막 것을 쓴다."""
    recs = load(path).get("recs") or []
    if not recs:
        return None
    return recs[min(n, len(recs) - 1)]


def brief(n: int, path=None) -> str:
    """프롬프트에 붙일 한 덩이. **A 의 그 대목이 실제로 어땠는지를 그대로 시킨다.**

    분포가 아니라 그 대목의 값을 준다 -- 복제가 목적이면 "장면꼴이 대개 장면이다"
    가 아니라 "이번 대목은 여파다" 라야 한다."""
    r = at(n, path)
    if not r:
        return ""
    rows = []
    for k in ("장면꼴", "속도", "거리", "시간", "자리", "원인", "갈등축",
              "갈등세기", "갈등끝", "앎격차", "욕망", "인물수", "새인물",
              "새사실", "닫는법"):
        v = r.get(k)
        if v in ("", None):
            continue
        rows.append(f"{SAY[k]} **{v}**")
    if not rows:
        return ""
    out = ["[이 대목의 짜임] **이대로 짠다.** 아래는 다 다시 재서 판정한다.",
           "  " + " · ".join(rows)]
    if r.get("무엇"):
        out.append(f"  · 달라지는 것 하나: {r['무엇']}"
                   + (f" ({r['누구']}에게)" if r.get("누구") else ""))
    if r.get("심은것"):
        out.append(f"  · 나중에 쓸 것을 하나 놓는다: {r['심은것']} "
                   "-- 놓기만 하고 설명하지 마라")
    if isinstance(r.get("거둔거리"), int) and r["거둔거리"] > 0:
        out.append(f"  · 앞({r['거둔거리']}대목쯤 전)에서 놓았던 것을 여기서 거둔다")
    out.append("  · **무엇으로 그렇게 되는지는 네가 정한다.** 위는 짜임이지 본보기가 아니다.")
    return "\n".join(out)


def gap(mine: dict, theirs: dict) -> dict:
    """같은 추출기로 우리 원고를 재서 A 의 그 대목과 견준다. **겹친 칸의 몫.**"""
    same, seen, miss = 0, 0, []
    for k in PICK:
        a, b = mine.get(k), theirs.get(k)
        if not a or not b:
            continue
        seen += 1
        if a == b:
            same += 1
        else:
            miss.append(f"{k} {a}≠{b}")
    for k in NUM:
        a, b = mine.get(k), theirs.get(k)
        if not isinstance(a, int) or not isinstance(b, int):
            continue
        seen += 1
        lo, hi = NUM[k][1], NUM[k][2]
        if abs(a - b) <= max(1, (hi - lo) // 8):
            same += 1
        else:
            miss.append(f"{k} {a}≠{b}")
    return {"겹친 몫": round(same / seen, 3) if seen else 0.0,
            "잰 칸": seen, "어긋난 것": miss}


def table(data: dict) -> str:
    """사람이 읽을 표."""
    d = data.get("dist") or {}
    out = [f"토막 {d.get('n', 0)}개"]
    for k, sh in (d.get("share") or {}).items():
        out.append(f"  {k:<7} " + " · ".join(f"{a} {v:.0%}" for a, v in sh.items()))
    for k, b in (d.get("band") or {}).items():
        out.append(f"  {k:<7} {b['lo']} ~ {b['hi']} (가운데 {b['mid']})")
    if d.get("복선"):
        f = d["복선"]
        out.append(f"  복선    거두는 몫 {f['거두는 몫']:.0%} · "
                   f"사거리 가운데 {f['사거리 가운데']}대목 · 제일 먼 것 {f['제일 먼 것']}대목")
    out.append(f"  심는 몫 {d.get('심는 몫', 0):.0%}")
    return "\n".join(out)


def main(argv=None) -> int:
    import sys
    print(table(load()) if load() else f"아직 없다: {PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
