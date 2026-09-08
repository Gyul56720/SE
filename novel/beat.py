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
from novel import hooks as HK
from novel import serial as SR
from novel import space as SP

EP = int(os.environ.get("EPISODE_SPAN", "5000"))
BEATS = 3


def ep_no(book: dict) -> int:
    """지금 회차 번호(0부터). 카드가 있으면 카드의 번호다 -- 회차는 분량으로도 넘어가고,
    마지막 비트를 다 썼을 때도 넘어간다(아래 ensure). 분량만 보면 같은 회차를 두 번 쓴다."""
    if book.get("_ep") is not None:
        return int(book["_ep"])
    c = book.get("card")
    if c and c.get("ep") is not None:
        return int(c["ep"])
    return sum(len(c) for c in (book.get("chunks") or [])) // max(1, EP)

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


def _overlap(a: str, b: str) -> bool:
    """두 문장이 두 글자 넘는 낱말을 하나라도 나누는가."""
    import re
    wa = {w for w in re.split(r"[\s·,.\"'“”]+", a) if len(w) >= 3}
    wb = {w for w in re.split(r"[\s·,.\"'“”]+", b) if len(w) >= 3}
    return bool(wa & wb)


# **갈고리는 사건이다.** 사용자(2026-09-08): "질문 이딴 게 재미없다고. 구체적인 사건으로 --
# 누가 죽든가 팔이 잘리든가 키스를 하든가 관계를 맺든가. 자극적이게 끝내라고." 그리고
# "하드코딩하지 마. 이런 게 아주 많이 있어야 해. 표본 먼저 뽑던가."
# 첫 런의 갈고리가 "...믿는 겁니까?" 였다. 질문 · 예감 · 대사 · 미소는 갈고리가 아니다.
# 종류는 hooks.py 에 있다 -- 표본(631회차 중 120개를 읽어 분류)과 사용자 요구에서 온
# **본보기**이지 닫힌 목록이 아니다. 회차마다 다섯 개씩 돌려 보여 주고, 목록 밖을 지어내도
# 된다. 지키는 것은 **꼴**이다: 몸 · 자리 · 목숨에 되돌릴 수 없는 일이 **벌어진 문장.**
_ASK = ("?", "？")
# 조용한 끝의 꼴. 표본 120개 중 83개가 이렇게 끝났다 -- 미소 · 한숨 · 눈을 감음 · 바라봄.
_QUIET = ("미소", "웃었다", "웃으며", "한숨", "눈을 감", "바라보았다", "바라보고", "잠들",
          "생각했다", "느꼈다", "것 같았다", "듯했다", "돌아섰다", "걸음을 옮겼다")


def hook_ok(kind: str, text: str) -> str:
    """갈고리가 사건인가. **꼴만 본다** -- 종류는 안 본다. 문제가 있으면 이유를, 없으면 빈 것."""
    t = text.strip()
    if not kind.strip():
        return "갈고리 종류가 비었다 -- 한 낱말로 무엇이 벌어지는지 이름을 붙여라"
    if not t:
        return "갈고리가 비었다"
    if t.endswith(_ASK) or t.rstrip("\"'”’.。").endswith(("까", "냐", "니", "지", "걸까", "일까")):
        return "갈고리가 질문이다 -- 질문은 사건이 아니다. 무엇이 벌어졌는지 평서문으로"
    if t.startswith(("\"", "“", "'", "‘")):
        return "갈고리가 대사다 -- 말은 사건이 아니다. 몸에 벌어지는 일로"
    if any(q in t[-14:] for q in _QUIET):
        return "갈고리가 조용히 끝난다 -- 미소 · 한숨 · 바라봄은 사건이 아니다. 몸 · 자리 · 목숨에 벌어진 일로"
    if t.rstrip("\"'”’.。").endswith(("것이다", "것이었다", "터였다", "참이었다", "려 했다", "려고 했다")):
        return "갈고리가 예고다 -- 벌어지려는 문장이 아니라 벌어진 문장으로"
    return ""


# ---------------------------------------------------------------- 세우기

def plants(book: dict) -> list:
    """심어 두고 아직 안 거둔 것. (무엇, 심은 회차)"""
    return [p for p in (book.get("plants") or []) if p.get("거둠") is None]


def _plants_block(book: dict) -> str:
    ps = plants(book)
    if not ps:
        return "[심어 둔 것] 아직 없다 -- 이번 회차에 하나 심어라."
    now = ep_no(book)
    rows = []
    for p in ps:
        age = now - int(p.get("ep", now))
        rows.append(f"    · {p['무엇']}" + ("   ← 세 회차 넘게 묵었다. 거두거나 버려라" if age >= 3 else ""))
    return "[심어 둔 것 -- 거둘 수 있는 것]\n" + "\n".join(rows)


def card_prompt(book: dict) -> str:
    from novel import flow
    a = SR.arc(book)
    cur = SR.current(book) or {}
    st = SR.stage(book)
    tp = turning_point(book)
    prev = book.get("card") or {}
    tail = "".join(book.get("chunks") or [])[-600:]
    world = flow.brief(book["ledger"], now=len(book.get("chunks") or []))
    seed = str(book.get("seed_id") or book.get("first") or "")
    n = ep_no(book)
    return f"""이번 **회차**의 각본을 세운다. 약 {EP:,}자 분량이다. 산문을 쓰지 마라 -- JSON 만 낸다.
게임 · 일본 라이트노벨 · 애니메이션의 전개 문법으로 짠다 -- 아래 [전개 본보기] 가 그것이다.

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

{_plants_block(book)}

[전개 본보기 -- 이 회차의 비트는 이런 꼴로 짠다. 하나둘 고른다]
{SP.render("전개", seed, n, 3)}
{SP.render("큰줄기", seed, n, 1)}

[로맨스 · 싸움 · 체계 본보기 -- 비트 하나에 하나씩 얹을 수 있다]
{SP.render("로맨스", seed, n, 2)}
{SP.render("싸움", seed, n, 1)}
{SP.render("시스템", seed, n, 1)}

[설정 본보기 -- 세계의 규칙을 하나 더 세우거나 쓸 때. 값은 네가 정하고 원장이 지킨다]
{SP.render("설정", seed, n, 1)}

[인물 본보기 -- 새 사람을 세우거나 있는 사람을 쓸 때]
{SP.render("인물", seed, n, 2)}

낸다:
{{"질문": "주인공이 이번 회차에 원하는 것 한 문장. 손에 잡히는 것으로 -- 초대장 · 서명 · 한 사람의 입",
  "방해": "누가 무엇으로 막는가. 사람이어야 한다 -- 사정이나 운명이 아니라",
  "비트": [{{"무엇": "한 문장. 일이 하나 벌어진다", "꼴": "장면"}},
          {{"무엇": "...", "꼴": "장면"}},
          {{"무엇": "여기서 질문의 답이 갈린다", "꼴": "장면"}}],
  "답": "얻는다 | 잃는다 | 반만",
  "갈고리종류": "무엇이 벌어지는지 한 낱말 (아래 본보기 중 하나이거나, 네가 지은 것)",
  "갈고리": "회차의 마지막 문단에서 **실제로 벌어지는 일** 한 문장. 평서문. 다음 회차가 여기서 시작한다",
  "심음": "이번 회차에 지나가듯 심어 두는 것 한 문장 -- 나중에 거둘 소문 · 흔적 · 이명 · 물건. 이번 회차에서 설명하지 않는다",
  "거둠": "[심어 둔 것] 중 이번 회차에 거두는 것을 **그 낱말 그대로**. 없으면 빈 문자열"}}

규칙 -- 빌드업 (개연성은 여기서 온다):
{SP.rules("빌드업")}

규칙:
- **갈고리는 사건이다. 질문 · 예감 · 대사 · 미소가 아니다.** "믿는 겁니까?" 같은 것은
  갈고리가 아니다. 몸 · 자리 · 목숨에 **되돌릴 수 없는 일**이 회차의 마지막 문단에서
  벌어진다. 이런 것들이다 (본보기다 -- 이 밖의 것을 지어내도 된다, 꼴만 같으면):
{HK.render(str(book.get('seed_id') or book.get('first') or ''), ep_no(book))}
  갈고리는 그 일이 **벌어진 문장**이다. 벌어지려는 문장이 아니다. 끝난 줄 알았는데 더 큰
  것이 오는 것도 좋다 -- 그때는 그것이 곁의 누구를 어떻게 하는지까지.
- 앞 회차의 '남긴 것' 에서 시작한다. 그것이 이번 회차의 첫 비트를 만든다.
- **무대와 판돈이 앞 회차보다 크다.** 같은 방에서 같은 값을 걸면 앞 회차를 되풀이한 것이다.
  사건을 더 잔혹하게 하지 말고 **판을 넓혀라** -- 방에서 연회장으로, 한 사람의 평판에서
  가문의 자리로, 가문에서 도시로 (RYU.md ④).
{"- **첫 회차다.** 주인공이 무엇을 원하는지 한 문장으로 드러나야 한다 -- 살아남는 연재는 전부 1화에서 목적을 낸다(HIKI.md)." if ep_no(book) == 0 else ""}
- 비트는 셋. 세기는 뒤로 갈수록 오른다. 꼴은 "장면"(한 자리 · 한 때 · 대사가 민다) 또는
  "요약"(시간을 접는다 -- 며칠이 한 문단). 요약은 하나 이하.
- 답은 성장 단계를 따른다. 지는 단계면 "잃는다" 나 "반만". 이기는 단계에서도 값을 치른다.
- 인물은 [세계]에 있는 사람을 쓴다. 새 사람은 하나까지.
- 전환점이 있으면 비트 3 이 그것이다.
- 이름 · 사건 · 대사를 산문으로 쓰지 마라. 각본은 한 문장씩이다."""


def ensure(book: dict, llm) -> "dict | None":
    """회차가 바뀌었으면 카드를 새로 낸다. **회차당 호출 한 번.** 실패하면 카드 없이 간다."""
    n = _chars(book)
    by_len = n // max(1, EP)
    card = book.get("card")
    nchunks = len(book.get("chunks") or [])
    if card:
        # **회차가 끝나는 조건은 둘이다.** 분량이 찼거나, 마지막 비트를 이미 썼거나.
        # 실측 2026-09-08 밤: 분량만 봤더니 갈고리(자격 박탈 선언)를 쓴 뒤에도 같은 카드가
        # 남아 다음 덩어리가 **같은 장면을 다시 썼다** -- 사용자: "이거 똑같은 씬 이전에
        # 나왔는데 또 반복된다."
        last_given = card.get("_last_given")
        done = last_given is not None and nchunks > int(last_given)
        if by_len <= int(card.get("ep", 0)) and not done:
            return card
        ep = max(by_len, int(card.get("ep", 0)) + 1)
        if done and by_len <= int(card.get("ep", 0)):
            D._log(f"[회차] 마지막 비트를 썼다 -- 분량이 안 찼어도 다음 회차로 넘어간다")
    else:
        ep = by_len
    book["_ep"] = ep
    try:
        prompt = card_prompt(book)
        got = D.call_json(D._llm_for(llm, "director"), prompt, label="회차 각본")
        # **갈고리가 사건이 아니면 한 번 되묻는다.** 그래도 아니면 카드를 버린다 --
        # 질문으로 끝나는 회차를 열 번 쓰느니 각본 없이 가는 편이 낫다.
        why = hook_ok(str(got.get("갈고리종류") or "").strip(), str(got.get("갈고리") or ""))
        if why:
            D._log(f"[회차] 갈고리를 되묻는다 -- {why}")
            got = D.call_json(D._llm_for(llm, "director"),
                              prompt + f"\n\n앞서 낸 각본의 갈고리가 틀렸다: {why}. 다시 낸다.",
                              tries=2, label="회차 각본(되묻기)")
            why = hook_ok(str(got.get("갈고리종류") or "").strip(), str(got.get("갈고리") or ""))
            if why:
                raise ValueError(why)
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
        sow = str(got.get("심음") or "").strip()
        reap = str(got.get("거둠") or "").strip()
        book["card"] = {"ep": ep, "at": n, "질문": q,
                        "방해": str(got.get("방해") or "").strip(),
                        "비트": beats,
                        "답": str(got.get("답") or "").strip(),
                        "갈고리종류": str(got.get("갈고리종류") or "").strip(),
                        "갈고리": str(got.get("갈고리") or "").strip(),
                        "심음": sow, "거둠": reap,
                        "전환점": turning_point(book)}
        # **심고 거두는 원장.** 거둠은 심어 둔 것과 낱말이 겹쳐야 친다 -- 안 겹치면 거둔 것이
        # 아니라 새로 꺼낸 것이고, 그것은 로그에 남긴다(뜬금없음의 기록).
        ps = book.setdefault("plants", [])
        if reap:
            hit = next((p for p in ps if p.get("거둠") is None and
                        (reap in p["무엇"] or p["무엇"] in reap or _overlap(reap, p["무엇"]))), None)
            if hit:
                hit["거둠"] = ep
                D._log(f"[회차]   거둔다: {hit['무엇']} (회차 {int(hit['ep']) + 1}에 심은 것)")
            else:
                D._log(f"[회차]   거둔다고 했는데 심은 적이 없다: {reap} -- 새로 꺼낸 것이다")
        if sow:
            ps.append({"무엇": sow, "ep": ep, "거둠": None})
            D._log(f"[회차]   심는다: {sow}")
        D._log(f"[회차] {ep + 1} -- 원하는 것: {q}")
        for i, b in enumerate(beats, 1):
            D._log(f"[회차]   비트 {i} ({b['꼴']}) {b['무엇']}")
        D._log(f"[회차]   갈고리({book['card']['갈고리종류']}): {book['card']['갈고리']}")
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
        rows.append(f"  · 앞 비트는 이미 썼다. **{k}번 비트부터** 쓴다 -- 되풀이하지 마라."
                    " 앞 덩어리에서 벌어진 일(선언 · 박탈 · 사살)은 **다시 벌어지지 않는다.**")
    if k >= len(c["비트"]):
        # 마지막 비트를 이 덩어리에 맡겼다. 다음 덩어리는 다음 회차다(ensure 가 본다).
        c["_last_given"] = len(book.get("chunks") or [])
    rows.append("  · 장면 비트는 한 자리 · 한 때에서 벌어지고 대사가 민다. 요약 비트는 시간을"
                " 접는다 -- 며칠이 한 문단이어도 된다. 세기는 비트마다 오른다.")
    # **연출과 대사 -- 애니 · 라노벨의 꼴.** 사용자: "상황이 머릿속에 안 떠오른다."
    seed = str(book.get("seed_id") or book.get("first") or "")
    nn = len(book.get("chunks") or [])
    rows.append("  · 연출:\n" + SP.render("연출", seed, nn, 2).replace("    ", "      "))
    rows.append("  · 대사:\n" + SP.render("대사", seed, nn, 2).replace("    ", "      "))
    # 사용자(2026-09-08 밤): "전투씬 더 자세히 · 묘사 더 생생하게 · 주변 반응 더 격하게 · 19세."
    rows.append("  · 싸움이 있으면:\n" + SP.render("싸움", seed, nn, 1).replace("    ", "      "))
    rows.append("  · 몸과 살갗:\n" + SP.render("외모", seed, nn, 1).replace("    ", "      ")
                + "\n" + SP.render("관능", seed, nn, 1).replace("    ", "      "))
    rows.append("  · 주변의 반응:\n" + SP.render("반응", seed, nn, 1).replace("    ", "      "))
    if c.get("거둠"):
        rows.append(f"  · **거둔다:** {c['거둠']} -- 앞 회차에 심어 둔 그 낱말 · 그 물건을 그대로 다시 쓴다."
                    " 새 인물이 이 자리에서 나오면 기척 → 실루엣 → 한 마디 → 이명 → 판이 바뀐다.")
    if c.get("심음"):
        rows.append(f"  · **심는다:** {c['심음']} -- 지나가듯 한 문장. 설명하지 마라, 누구도 그것에 반응하지 마라.")
    if c.get("갈고리"):
        kind = c.get("갈고리종류") or ""
        rows.append(f"  · 마지막 비트를 쓰게 되면 회차의 마지막 문단에서 **{kind}**이 벌어진다:"
                    f" **{c['갈고리']}** -- 이것이 **벌어진 문장**에서 끊어라. 예고하지 마라,"
                    " 묻고 끝내지 마라, 미소나 한숨으로 정리하지 마라.")
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
    out.append(f"  답: {c.get('답', '')} / 갈고리({c.get('갈고리종류', '')}): {c.get('갈고리', '')}"
               + (f" / 전환점: {c['전환점']}" if c.get("전환점") else ""))
    if c.get("심음") or c.get("거둠"):
        out.append(f"  심음: {c.get('심음', '')} / 거둠: {c.get('거둠', '')}")
    ps = plants(book)
    if ps:
        out.append("  아직 안 거둔 것: " + " · ".join(p["무엇"] for p in ps))
    return "\n".join(out)
