"""**회차 각본 -- 덩어리 위의 층.**

## 왜 있나

STORY.md 2절. 플롯도 연출도 재미없었고 뿌리는 하나였다: 생성 단위가 3,200자 덩어리인데
플롯(원하는 것 · 방해 · 전환점)도 연출(장면 · 요약 · 세기)도 그보다 큰 단위에 산다.
회차 층이 없었다. 덩어리마다 지시를 한 블록씩 덧대던 것(tension.py)은 걷어냈다 --
금지문이 열둘인 프롬프트에 열셋째를 얹는 것은 설계가 아니다.

## 무엇을 하나

약 {EP}자마다 **디렉터가 회차 카드를 한 장 낸다.** 호출 한 번이다.

    질문    주인공이 이번 회차에 원하는 것 한 문장 (Zwaan 1995: 독자는 의도를 축으로 따라간다)
    방해    누가 무엇으로 막는가                    (Zillmann: 위험이 있어야 서스펜스가 선다)
    비트    셋. 각각 장면인지 요약인지. 세기는 뒤로 갈수록 오른다
                                                    (Chakrabarty 2024: 시간을 늘이고 줄인다;
                                                     Tian 2024: 각성이 쌓여야 한다)
    답      비트 3 에서 질문의 답이 갈린다 -- 얻는다 · 잃는다 · 반만
                                                    (Ely 2015: 결과가 뻔하면 분산이 0)
    갈고리  회차 끝에 답이 안 난 채 남는 것          (Loewenstein 1994 · 연재의 회차 끝)
    전환점  이 회차에 오면 다섯 중 어느 것            (Papalampidi 2019: 기회 · 계획 변경 ·
                                                     돌아올 수 없는 지점 · 대좌절 · 절정)

덩어리는 이제 자유 이어 쓰기가 아니라 **비트를 쓴다.** 문체 규율은 그대로다.

## 무엇을 대신하나

카드가 있으면 무작위 사건(shock · plot.brief 의 사건축)을 **뽑지 않는다.** 그것이 인과
없는 사건의 나열을 만들던 자리다(Trabasso 1985). 카드의 비트는 앞 회차의 갈고리에서
나온다 -- 인과가 구조로 들어간다.

## 도착지가 없으면 각본도 없다

카드는 빚(serial) 위에 선다: 이번 마디의 빚 · 성장 단계 · 전환점이 입력이다. 도착지가 안
세워진 원고(검사 · 옛 DRIFT)는 카드 없이 예전대로 간다 -- 없는 것을 지어내서 시키지
않는다.

    EPISODE_SPAN=5000   한 회차의 분량. 잰 값이 아니라 웹소설 회차의 통상 길이다.
"""
from __future__ import annotations

import os

from novel import drive as D
from novel import serial as SR

EP = int(os.environ.get("EPISODE_SPAN", "5000"))
BEATS = 3

# 전환점 다섯(Papalampidi & Keller 2019). 빚 위에 얹는다 -- 마디의 마지막 회차에 온다.
TPS = {
    "기회": "주인공 앞에 처음으로 길이 하나 열린다. 아직 잡지는 못한다.",
    "계획 변경": "가던 길이 막혀 다른 길로 간다. 되돌릴 수 있는 마지막 자리다.",
    "돌아올 수 없는 지점": "여기서 한 일은 되돌릴 수 없다. 판돈이 오른다.",
    "대좌절": "가진 것을 잃는다. 제일 낮은 자리다 -- 여기서 다음 회차가 선다.",
    "절정": "처음에 못 하던 것을 한다. 값을 치른 만큼만 이긴다.",
}


def _chars(book: dict) -> int:
    return sum(len(c) for c in (book.get("chunks") or []))


def turning_point(book: dict) -> str:
    """이번 회차에 오는 전환점. **마디의 마지막 회차에만** 온다. 없으면 빈 것."""
    ds = SR.arc(book).get("debts") or []
    if not ds:
        return ""
    if SR.closing(book):
        return "절정"
    n, span = _chars(book), SR.span(book)
    if (n % span) + EP < span:            # 이 회차 안에서 마디가 안 끝난다
        return ""
    i, k = SR.where(book), len(ds)
    if i >= k:
        return ""                         # 끝을 향하는 마디 -- 절정은 closing 이 준다
    if i == 0:
        return "기회"
    if i == k - 1:
        return "대좌절"
    return "계획 변경" if i <= (k - 1) // 2 else "돌아올 수 없는 지점"


def has(book: dict) -> bool:
    c = book.get("card")
    return bool(c and c.get("질문") and c.get("비트"))


# ---------------------------------------------------------------- 세우기

def card_prompt(book: dict) -> str:
    from novel import flow
    a = SR.arc(book)
    cur = SR.current(book) or {}
    st = SR.stage(book)
    tp = turning_point(book)
    prev = book.get("card") or {}
    tail = "".join(book.get("chunks") or [])[-600:]
    world = flow.brief(book["ledger"], now=len(book.get("chunks") or []))
    return f"""이번 **회차**의 각본을 세운다. 약 {EP:,}자 분량이다. 산문을 쓰지 마라 -- JSON 만 낸다.

[이 소설이 닿을 자리] {a.get('end', '')}
{f"[처음의 주인공] {a['start']}" if a.get('start') else ''}
[이번 마디가 향하는 것] {cur.get('무엇', '')}
{f"[성장 단계] {st[0]} -- {st[1]}" if st else ''}
{f"[이번 회차에 오는 전환점] **{tp}** -- {TPS[tp]}" if tp else ''}

[세계 -- 지금까지 확정된 것]
{world}

[지금까지의 끝부분]
...{tail}

{f"[앞 회차] 원하던 것: {prev.get('질문', '')} / 답: {prev.get('답', '')} / 남긴 것: {prev.get('갈고리', '')}" if prev.get('질문') else ''}

낸다:
{{"질문": "주인공이 이번 회차에 원하는 것 한 문장. 손에 잡히는 것으로 -- 초대장 · 서명 · 한 사람의 입",
  "방해": "누가 무엇으로 막는가. 사람이어야 한다 -- 사정이나 운명이 아니라",
  "비트": [{{"무엇": "한 문장. 일이 하나 벌어진다", "꼴": "장면"}},
          {{"무엇": "...", "꼴": "장면"}},
          {{"무엇": "여기서 질문의 답이 갈린다", "꼴": "장면"}}],
  "답": "얻는다 | 잃는다 | 반만",
  "갈고리": "회차 끝에 답이 안 난 채로 남는 것 한 문장. 다음 회차가 여기서 시작한다"}}

규칙:
- 앞 회차의 '남긴 것' 에서 시작한다. 그것이 이번 회차의 첫 비트를 만든다.
- 비트는 셋. 세기는 뒤로 갈수록 오른다. 꼴은 "장면"(한 자리 · 한 때 · 대사가 민다) 또는
  "요약"(시간을 접는다 -- 며칠이 한 문단). 요약은 하나 이하.
- 답은 성장 단계를 따른다. 지는 단계면 "잃는다" 나 "반만". 이기는 단계에서도 값을 치른다.
- 인물은 [세계]에 있는 사람을 쓴다. 새 사람은 하나까지.
- 전환점이 있으면 비트 3 이 그것이다.
- 이름 · 사건 · 대사를 산문으로 쓰지 마라. 각본은 한 문장씩이다."""


def ensure(book: dict, llm) -> "dict | None":
    """회차가 바뀌었으면 카드를 새로 낸다. **회차당 호출 한 번.** 실패하면 카드 없이 간다."""
    n = _chars(book)
    ep = n // max(1, EP)
    card = book.get("card")
    if card and card.get("ep") == ep:
        return card
    try:
        got = D.call_json(D._llm_for(llm, "director"), card_prompt(book), label="회차 각본")
        beats = []
        for b in (got.get("비트") or [])[:BEATS]:
            if isinstance(b, dict) and str(b.get("무엇") or "").strip():
                kind = "요약" if str(b.get("꼴") or "").strip() == "요약" else "장면"
                beats.append({"무엇": str(b["무엇"]).strip(), "꼴": kind})
            elif isinstance(b, str) and b.strip():
                beats.append({"무엇": b.strip(), "꼴": "장면"})
        q = str(got.get("질문") or "").strip()
        if not q or not beats:
            raise ValueError(f"각본이 비었다: 질문={q!r} 비트={len(beats)}개")
        book["card"] = {"ep": ep, "at": n, "질문": q,
                        "방해": str(got.get("방해") or "").strip(),
                        "비트": beats,
                        "답": str(got.get("답") or "").strip(),
                        "갈고리": str(got.get("갈고리") or "").strip(),
                        "전환점": turning_point(book)}
        D._log(f"[회차] {ep + 1} -- 원하는 것: {q}")
        for i, b in enumerate(beats, 1):
            D._log(f"[회차]   비트 {i} ({b['꼴']}) {b['무엇']}")
        if book["card"]["전환점"]:
            D._log(f"[회차]   전환점: {book['card']['전환점']}")
        return book["card"]
    except Exception as e:
        D._log(f"[회차] 각본을 못 세웠다({type(e).__name__}: {str(e)[:80]}) -- 이번 회차는 각본 없이 간다")
        book["card"] = None
        return None


# ---------------------------------------------------------------- 프롬프트

def beat_at(book: dict) -> int:
    """지금 덩어리가 시작할 비트(1부터). 회차 안에서 얼마나 왔느냐로 정한다."""
    card = book.get("card") or {}
    done = _chars(book) - int(card.get("at", 0))
    k = int(done * BEATS / max(1, EP)) + 1
    return max(1, min(len(card.get("비트") or []) or BEATS, k))


def brief(book: dict) -> str:
    """**[이번 회차] 블록.** 카드가 없으면 빈 것 -- 예전 프롬프트 그대로다."""
    if not has(book):
        return ""
    c = book["card"]
    k = beat_at(book)
    rows = [f"  · 주인공이 원하는 것: {c['질문']}"]
    if c.get("방해"):
        rows.append(f"  · 막는 것: {c['방해']}")
    rows.append("  · 비트:")
    for i, b in enumerate(c["비트"], 1):
        mark = "→" if i == k else " "
        tail = f"   ← 여기서 답이 갈린다: {c['답']}" if i == len(c["비트"]) and c.get("답") else ""
        rows.append(f"      {mark} {i}. ({b['꼴']}) {b['무엇']}{tail}")
    if k > 1:
        rows.append(f"  · 앞 비트는 이미 썼다. **{k}번 비트부터** 쓴다 -- 되풀이하지 마라.")
    rows.append("  · 장면 비트는 한 자리 · 한 때에서 벌어지고 대사가 민다. 요약 비트는 시간을"
                " 접는다 -- 며칠이 한 문단이어도 된다. 세기는 비트마다 오른다.")
    if c.get("갈고리"):
        rows.append(f"  · 마지막 비트를 쓰게 되면 **{c['갈고리']}** 가 답이 안 난 채로 끝나게"
                    " 하고 거기서 끊어라. 정리하지 마라.")
    if c.get("전환점"):
        rows.append(f"  · 이 회차의 마지막 비트는 **{c['전환점']}**이다 -- {TPS[c['전환점']]}")
    rows.append("  · 이 각본을 옮겨 적지 마라. 각본에 없는 것은 자유다 -- 다만 각본을 거스르지 마라.")
    return "[이번 회차]\n" + "\n".join(rows)


def show(book: dict) -> str:
    if not has(book):
        return "각본이 없다 -- 도착지가 있으면 다음 덩어리에서 세운다."
    c = book["card"]
    out = [f"회차 {c['ep'] + 1} · 원하는 것: {c['질문']}", f"  막는 것: {c.get('방해', '')}"]
    out += [f"  {i}. ({b['꼴']}) {b['무엇']}" for i, b in enumerate(c["비트"], 1)]
    out.append(f"  답: {c.get('답', '')} / 갈고리: {c.get('갈고리', '')}"
               + (f" / 전환점: {c['전환점']}" if c.get("전환점") else ""))
    return "\n".join(out)
