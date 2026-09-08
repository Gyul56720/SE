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

두 번째 요구(2026-09-08 저녁, "도파민 요소가 없다 · 전투 · 스킬 · 직함 · 세계관 더 자세히")로
칸이 셋 는다. 호출은 안 는다 -- 같은 카드에 실린다.

    쾌감    이번 회차에서 독자가 통쾌한 자리 한 문장과 그 비트 번호. **회차마다 하나.**
            지는 단계에서도 작은 것 하나는 되갚는다      (HIKI.md ざまぁ 회계 · STORY.md 3절 Ely)
    설정    이번 회차에 세우는 세계 설정 하나 -- 직함 · 등급 · 기술 · 법칙 · 구역. 이름과
            규칙 한 줄. book["codex"](설정집)에 쌓여 다음 회차부터 그 이름 그대로 쓴다
    전투    싸움이 있으면 누가 누구와 · 격 · 결착 · 남는 것. 없으면 빈 것

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
    """지금 회차 번호(0부터)."""
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


# ---------------------------------------------------------------- 설정집 · 쾌감

def codex(book: dict) -> list:
    """세운 설정. (이름, 규칙, 세운 회차). 카드가 "설정" 을 낼 때마다 하나 는다."""
    return [c for c in (book.get("codex") or []) if isinstance(c, dict) and c.get("이름")]


def _codex_block(book: dict, k: int = 10) -> str:
    cs = codex(book)
    if not cs:
        return ("[설정집] 아직 없다 -- 이번 회차에 하나 세워라. 직함 · 등급 · 기술 · 법칙 · 구역 ·"
                " 절차 중 하나, 이름과 규칙 한 줄.")
    rows = [f"    · {c['이름']}: {c.get('규칙', '')}" for c in cs[-k:]]
    return "[설정집 -- 이 세계에서 이미 세운 것. 이름은 그대로 쓴다]\n" + "\n".join(rows)


def _parse_setting(v) -> "tuple | None":
    """"설정" 칸. {"이름": ..., "규칙": ...} 또는 "이름 -- 규칙" 한 줄. 이름이 없으면 없는 것."""
    if isinstance(v, dict):
        name = str(v.get("이름") or "").strip()
        rule = str(v.get("규칙") or "").strip()
    else:
        s = str(v or "").strip()
        for sep in (" -- ", " — ", ": ", " : "):
            if sep in s:
                name, rule = (x.strip() for x in s.split(sep, 1))
                break
        else:
            name, rule = s, ""
    if not name or name in ("이름", "..."):
        return None
    return name, rule


# 회차가 끝났을 때 무엇이 달라지는가. 넷 중 하나다 -- 넷 다 그대로면 안 쓴 회차다.
AXES = ("장소", "처지", "관계", "앎")


def _parse_moved(v) -> "dict | None":
    """"바뀜" 칸. {"축": ..., "무엇": ...} 또는 "축 -- 무엇" 한 줄. 축이 넷 밖이면 낱말로 찾는다."""
    if isinstance(v, dict):
        ax = str(v.get("축") or "").strip()
        what = str(v.get("무엇") or "").strip()
    else:
        s = str(v or "").strip()
        ax, what = "", s
        for sep in (" -- ", " — ", ": ", " : "):
            if sep in s:
                ax, what = (x.strip() for x in s.split(sep, 1))
                break
    if not what:
        return None
    if ax not in AXES:
        ax = next((a for a in AXES if a in ax or a in what), "")
    return {"축": ax, "무엇": what}


def joy_ok(text: str) -> str:
    """쾌감이 사건인가. 갈고리와 같은 계약 -- 벌어진 문장. 빈 것도 안 된다: 회차마다 하나다."""
    if not str(text or "").strip():
        return "쾌감이 비었다 -- 회차마다 하나는 있다. 지는 회차면 작은 것 하나"
    why = hook_ok("쾌감", text)
    return why.replace("갈고리", "쾌감") if why else ""


def _joy_at(got: dict, beats: int, st) -> int:
    """쾌감이 벌어지는 비트. 안 주면 지는 단계는 가운데, 이기는 단계는 마지막."""
    try:
        j = int(str(got.get("쾌감자리") or "").strip() or 0)
    except ValueError:
        j = 0
    if not 1 <= j <= beats:
        j = beats if (st and st[0] == "이긴다") else max(1, min(beats, 2))
    return j


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
{f"[앞 회차에 바뀐 것] **{(prev.get('바뀜') or {}).get('축', '')}** 축이 바뀌었다 -- {(prev.get('바뀜') or {}).get('무엇', '')}. **이번엔 다른 축을 바꿔라.**" if (prev.get('바뀜') or {}).get('축') else ''}

{_plants_block(book)}

{_codex_block(book)}

[전개 본보기 -- 이 회차의 비트는 이런 꼴로 짠다. 하나둘 고른다]
{SP.render("전개", seed, n, 4)}

[인물 본보기 -- 새 사람을 세우거나 있는 사람을 쓸 때]
{SP.render("인물", seed, n, 2)}

[전투 본보기 -- 이 회차에 싸움이 있으면 이런 꼴이다]
{SP.render("전투", seed, n, 2)}

[세계 본보기 -- 설정을 세울 때 이런 꼴이다]
{SP.render("세계", seed, n, 2)}

[쾌감 본보기 -- 이 회차의 통쾌한 자리는 이런 꼴이다. 하나 고르거나 지어낸다]
{SP.render("쾌감", seed, n, 3)}

[전환 본보기 -- 회차와 회차 사이를 굴리는 꼴. 판이 흔들리는 자리가 여기서 나온다]
{SP.render("전환", seed, n, 3)}

낸다:
{{"질문": "주인공이 이번 회차에 원하는 것 한 문장. 손에 잡히는 것으로 -- 초대장 · 서명 · 한 사람의 입",
  "방해": "누가 무엇으로 막는가. 사람이어야 한다 -- 사정이나 운명이 아니라",
  "비트": [{{"무엇": "한 문장. 일이 하나 벌어진다", "꼴": "장면"}},
          {{"무엇": "...", "꼴": "장면"}},
          {{"무엇": "여기서 질문의 답이 갈린다", "꼴": "장면"}}],
  "답": "얻는다 | 잃는다 | 반만",
  "바뀜": {{"축": "장소 | 처지 | 관계 | 앎  넷 중 하나", "무엇": "회차가 끝났을 때 무엇이 어떻게 달라져 있는가 한 문장"}},
  "쾌감": "이번 회차에서 독자가 통쾌한 자리 한 문장. **벌어진 문장**으로 -- 되갚음 · 인정 · 격 상승 · 무릎 · 압도 · 구원 · 전리품. 지는 회차면 작은 것 하나",
  "쾌감자리": "그것이 벌어지는 비트 번호 (1 · 2 · 3)",
  "전투": "이번 회차에 싸움이 있으면 한 문장 -- 누가 누구와 · 격은 어느 쪽이 위인가 · 무엇으로 결착 · 무엇이 남는가. 없으면 빈 문자열",
  "설정": {{"이름": "이번 회차에 세우는 세계 설정 하나 -- 직함 · 등급 · 기술 · 법칙 · 구역 · 절차의 **이름**", "규칙": "그것이 무엇을 되게 하고 무엇을 막는가 한 줄. 숫자가 아니라 이름과 조건"}},
  "갈고리종류": "무엇이 벌어지는지 한 낱말 (아래 본보기 중 하나이거나, 네가 지은 것)",
  "갈고리": "회차의 마지막 문단에서 **실제로 벌어지는 일** 한 문장. 평서문. 다음 회차가 여기서 시작한다",
  "심음": "이번 회차에 지나가듯 심어 두는 것 한 문장 -- 나중에 거둘 소문 · 흔적 · 이명 · 물건. 이번 회차에서 설명하지 않는다",
  "거둠": "[심어 둔 것] 중 이번 회차에 거두는 것을 **그 낱말 그대로**. 없으면 빈 문자열"}}

규칙 -- 빌드업 (개연성은 여기서 온다):
{SP.rules("빌드업")}

규칙 -- 판이 흔들리는가 (이것이 제일 중요하다):
- **회차가 끝났을 때 장소 · 처지 · 관계 · 앎 중 하나는 반드시 달라져 있다.** 넷 다 그대로면
  그 회차는 안 쓴 것과 같다. 그것을 "바뀜" 칸에 축과 함께 적어라.
- **앞 회차와 다른 축을 바꿔라.** 세 회차 내리 같은 축이면 같은 장면을 세 번 쓴 것이다.
- **한 회차에 큰 사건 하나.** 둘을 넣으면 둘 다 작아진다. 비트 셋은 그 하나로 가는 길이다.
- **예상은 배신하고 기대는 배신하지 마라.** 독자가 예상한 길은 빗나가게 하되, 독자가 바라는
  것은 준다. 바라는 것을 안 주는 것은 뒤통수가 아니라 그냥 배신이다.
- **정리하고 쉬는 회차를 잇달아 두지 마라.** 문제를 풀면 그 자리에서 더 큰 것이 보인다.

규칙 -- 쾌감 · 설정 · 전투:
- **회차마다 쾌감이 하나 있다.** 지는 단계에서도 -- 큰 것을 잃는 회차에 작은 것 하나를 되갚는다
  (잔 하나 · 말 한마디 · 물러선 걸음). 이기는 단계면 답이 그것이다. 쾌감은 갈고리처럼
  **벌어진 문장**이다 -- 예감 · 질문 · 미소가 아니다. 당한 만큼보다 조금 더 돌려준다.
- **설정은 이름이지 숫자가 아니다.** 등급 · 직함 · 기술은 이름으로 부르고 조건으로 묶는다.
  상태창 · 수치 · 게이지를 열지 마라. 세운 설정은 [설정집]에 남고 다음 회차부터 그 이름
  그대로 쓴다. **쓰기 한 회차 앞에 세워라** -- 처음 나온 이름의 기술이 결착을 내면 뜬금없다.
  [설정집]에 이미 있는 것을 다시 세우지 마라. 이번 회차에 세울 것이 없으면 빈 것으로 둔다.
- **싸움이 있으면 격 · 조건 · 결착 · 남는 것을 정한다.** 첫 합에서 격이 드러나고, 결착은
  한 방이고, 상처는 다음 회차에 남는다. 구원은 **심어 둔 사람**만 한다 -- 구해진 값이 빚이다.

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
    ep = n // max(1, EP)
    card = book.get("card")
    if card and card.get("ep") == ep:
        return card
    try:
        prompt = card_prompt(book)
        got = D.call_json(D._llm_for(llm, "director"), prompt, label="회차 각본")
        # **갈고리가 사건이 아니면 한 번 되묻는다.** 그래도 아니면 카드를 버린다 --
        # 질문으로 끝나는 회차를 열 번 쓰느니 각본 없이 가는 편이 낫다.
        # **쾌감도 같은 되묻기에 얹는다.** 다만 쾌감이 두 번 다 틀리면 카드는 살리고 쾌감만
        # 비운다 -- 쾌감은 더하는 것이지 카드의 뼈대가 아니다.
        why = hook_ok(str(got.get("갈고리종류") or "").strip(), str(got.get("갈고리") or ""))
        why_joy = joy_ok(str(got.get("쾌감") or ""))
        if why or why_joy:
            D._log(f"[회차] 되묻는다 -- {' / '.join(x for x in (why, why_joy) if x)}")
            asks = ". ".join(f"{k} 틀렸다: {v}" for k, v in (("갈고리가", why), ("쾌감이", why_joy)) if v)
            got = D.call_json(D._llm_for(llm, "director"),
                              prompt + f"\n\n앞서 낸 각본의 {asks}. 다시 낸다.",
                              tries=2, label="회차 각본(되묻기)")
            why = hook_ok(str(got.get("갈고리종류") or "").strip(), str(got.get("갈고리") or ""))
            if why:
                raise ValueError(why)
            why_joy = joy_ok(str(got.get("쾌감") or ""))
            if why_joy:
                D._log(f"[회차] 쾌감이 여전히 틀렸다({why_joy}) -- 이번 회차는 쾌감 없이 간다")
                got["쾌감"] = ""
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
        joy = str(got.get("쾌감") or "").strip()
        setting = _parse_setting(got.get("설정"))
        moved = _parse_moved(got.get("바뀜"))
        book["card"] = {"ep": ep, "at": n, "질문": q,
                        "방해": str(got.get("방해") or "").strip(),
                        "비트": beats,
                        "답": str(got.get("답") or "").strip(),
                        "바뀜": moved,
                        "쾌감": joy,
                        "쾌감자리": _joy_at(got, len(beats), SR.stage(book)) if joy else 0,
                        "전투": str(got.get("전투") or "").strip(),
                        "설정": {"이름": setting[0], "규칙": setting[1]} if setting else None,
                        "갈고리종류": str(got.get("갈고리종류") or "").strip(),
                        "갈고리": str(got.get("갈고리") or "").strip(),
                        "심음": sow, "거둠": reap,
                        "전환점": turning_point(book)}
        # **설정집.** 같은 이름은 다시 안 세운다 -- 다시 세우면 값이 둘이고 그것이 모순이다.
        if setting:
            cx = book.setdefault("codex", [])
            if any(c.get("이름") == setting[0] for c in cx if isinstance(c, dict)):
                D._log(f"[회차]   설정을 다시 세웠다: {setting[0]} -- 설정집의 것이 이긴다")
                book["card"]["설정"] = None
            else:
                cx.append({"이름": setting[0], "규칙": setting[1], "ep": ep})
                D._log(f"[회차]   설정: {setting[0]} -- {setting[1]}")
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
        if moved:
            same = (card.get("바뀜") or {}).get("축") if isinstance(card, dict) else None
            D._log(f"[회차]   바뀜({moved['축'] or '?'}): {moved['무엇']}"
                   + ("   ← 앞 회차와 같은 축이다" if same and same == moved["축"] else ""))
        else:
            D._log("[회차]   바뀜이 비었다 -- 이 회차는 판이 안 흔들린다")
        if joy:
            D._log(f"[회차]   쾌감(비트 {book['card']['쾌감자리']}): {joy}")
        if book["card"]["전투"]:
            D._log(f"[회차]   전투: {book['card']['전투']}")
        D._log(f"[회차]   갈고리({book['card']['갈고리종류']}): {book['card']['갈고리']}")
        if book["card"]["전환점"]:
            D._log(f"[회차]   전환점: {book['card']['전환점']}")
        return book["card"]
    except Exception as e:
        D._log(f"[회차] 각본을 못 세웠다({type(e).__name__}: {str(e)[:80]}) -- 이번 회차는 각본 없이 간다")
        book["card"] = None
        return None


# ---------------------------------------------------------------- 프롬프트

def _chunk() -> int:
    """한 덩어리의 크기. flow 를 늦게 부른다 -- flow 가 이 파일을 먼저 임포트한다."""
    try:
        from novel import flow
        return max(1, int(flow.CHUNK))
    except Exception:
        return 3200


def beat_span(book: dict) -> tuple:
    """이번 덩어리가 덮을 비트 범위 `(부터, 까지)`.

    **회차당 덩어리 수로 나눈다.** 예전에는 회차 안에서 얼마나 왔느냐(글자 수)로 비트
    하나를 골랐는데, 회차당 덩어리가 비트 수보다 적으면 **뒤쪽 비트가 영영 안 쓰인다.**

    실측 2026-09-08: 덩어리 3,200자 · 회차 5,000자라 회차당 덩어리가 1.56개인데 비트는
    셋이었다. 열 덩어리를 써도 비트 3 이 한 번도 안 나왔다 -- 비트 3 은 "여기서 답이
    갈린다" 이고 갈고리 · 전환점 · 쾌감이 전부 거기 있다. 그래서 매 회차가 열고 밀다가
    잘렸다. 사용자 평이 그것이다: "전개가 없다. 한 씬의 반복이다."

    이제 한 덩어리가 비트 여럿을 덮을 수 있고, **회차의 마지막 덩어리는 반드시 마지막
    비트까지** 간다. 회차가 답 없이 끝나는 일이 없어진다.

    **회차 경계와 덩어리 경계는 안 맞는다.** 회차는 글자 수로 끊기고 덩어리는 모델이
    돌려주는 단위라, 어떤 회차는 덩어리 둘을 받고 어떤 회차는 하나만 받는다. 그래서
    시작(`lo`)은 **이 카드로 이미 몇 덩어리를 썼나**로 정하고, 끝(`hi`)은 **이 회차에
    분량이 얼마나 남았나**로 정한다. 남은 것이 덩어리 하나보다 적으면 이번이 마지막이고,
    그때는 무조건 마지막 비트까지 간다 -- 덩어리 하나짜리 회차는 그 하나가 셋을 다 덮는다.
    """
    card = book.get("card") or {}
    beats = len(card.get("비트") or []) or BEATS
    total = _chars(book)
    ch = _chunk()
    done = max(0, total - int(card.get("at", total)))   # 이 카드로 이미 쓴 분량
    left = EP - (total % max(1, EP))                    # 이 회차에 남은 분량
    n = max(1, -(-EP // ch))                            # 회차에 들어갈 덩어리 수(올림)
    i = done // ch                                      # 이 카드로 이미 쓴 덩어리 수
    lo = min(beats, i * beats // n + 1)
    hi = beats if left <= ch else max(lo, (i + 1) * beats // n)
    return max(1, lo), min(beats, max(lo, hi))


def beat_at(book: dict) -> int:
    """지금 덩어리가 시작할 비트(1부터)."""
    return beat_span(book)[0]


def last_chunk(book: dict) -> bool:
    """이번 덩어리로 이 회차가 닫히는가. 답과 갈고리는 여기서 터진다."""
    return (EP - (_chars(book) % max(1, EP))) <= _chunk()


def brief(book: dict) -> str:
    """**[이번 회차] 블록.** 카드가 없으면 빈 것 -- 예전 프롬프트 그대로다."""
    if not has(book):
        return ""
    c = book["card"]
    k, upto = beat_span(book)
    last = upto >= len(c["비트"])
    rows = [f"  · 주인공이 원하는 것: {c['질문']}"]
    if c.get("방해"):
        rows.append(f"  · 막는 것: {c['방해']}")
    rows.append("  · 비트:")
    for i, b in enumerate(c["비트"], 1):
        mark = "→" if k <= i <= upto else " "
        tail = f"   ← 여기서 답이 갈린다: {c['답']}" if i == len(c["비트"]) and c.get("답") else ""
        rows.append(f"      {mark} {i}. ({b['꼴']}) {b['무엇']}{tail}")
    if k > 1:
        rows.append(f"  · 앞 비트는 이미 썼다. **{k}번 비트부터** 쓴다 -- 되풀이하지 마라.")
    # **한 덩어리가 비트 여럿을 덮는다.** 회차당 덩어리가 비트 수보다 적어서, 하나씩
    # 쓰면 뒤쪽 비트가 영영 안 쓰인다(실측 2026-09-08).
    if upto > k:
        rows.append(f"  · **이번 대목에서 비트 {k}부터 {upto}까지 전부 쓴다.** 하나만 쓰고 멈추지 마라"
                    " -- 이 대목 안에서 비트가 넘어가고, 넘어간 자리가 보여야 한다.")
    if last:
        rows.append("  · **이번 대목이 이 회차의 끝이다.** 여기서 답이 갈리고 회차가 닫힌다."
                    " 다음 대목으로 미루지 마라 -- 미루면 이 회차는 답 없이 끝난다.")
    rows.append("  · 장면 비트는 한 자리 · 한 때에서 벌어지고 대사가 민다. 요약 비트는 시간을"
                " 접는다 -- 며칠이 한 문단이어도 된다. 세기는 비트마다 오른다.")
    # **판이 흔들리는가.** 사용자: "한 씬의 반복이다. 판이 계속 흔들려야 한다."
    ch = c.get("바뀜") or {}
    if ch.get("무엇"):
        rows.append(f"  · **이 회차가 끝나면 달라져 있는 것** ({ch.get('축', '')}): {ch['무엇']}"
                    " -- 회차가 닫힐 때 이것이 실제로 달라져 있어야 한다. 말로 달라졌다고 하지 말고"
                    " 달라진 자리를 보여라.")
    # **연출과 대사 -- 애니 · 라노벨의 꼴.** 사용자: "상황이 머릿속에 안 떠오른다."
    seed = str(book.get("seed_id") or book.get("first") or "")
    nn = len(book.get("chunks") or [])
    rows.append("  · 연출:\n" + SP.render("연출", seed, nn, 2).replace("    ", "      "))
    rows.append("  · 대사:\n" + SP.render("대사", seed, nn, 2).replace("    ", "      "))
    # **쾌감 · 전투 · 설정 -- 도파민의 자리.** 사용자: "도파민 요소가 없다."
    if c.get("쾌감"):
        j = int(c.get("쾌감자리") or 0)
        where = f"비트 {j}에서 " if j else ""
        done = "   ← 앞 비트에서 이미 벌어졌다. 되풀이하지 마라" if j and j < k else ""
        rows.append(f"  · **쾌감** ({where}벌어진다): {c['쾌감']} -- 벌어진 문장으로 쓴다."
                    " 설명하지 마라, 놀라고 감탄하는 것은 곁의 사람들이다. 당한 만큼보다 조금 더." + done)
    if c.get("전투"):
        # **액션은 통째로 싣는다**(빌드업과 같은 계약). 돌려 뽑으면 정작 싸우는 회차에
        # 안 걸린다 -- 알아보기 쉬운 액션은 다섯 규율이 다 있어야 선다.
        rows.append(f"  · **싸움**: {c['전투']}\n"
                    "      첫 합에서 격이 드러나고, 기술은 이름을 부르고, 결착은 한 방이다. 상처는 남는다.\n"
                    "      액션은 이렇게 쓴다:\n" + SP.rules("액션").replace("    ", "      ")
                    + "\n      전투 문법:\n" + SP.render("전투", seed, nn, 2).replace("    ", "      "))
    # **수위.** `--heat` 를 켠 원고에만. 머리 둘(어른만 · 원하는지가 보인다)은 조건이라
    # 늘 싣고, 나머지는 돌려 뽑는다.
    if float(book.get("heat") or 0) > 0:
        rows.append("  · **수위 (성인)**:\n" + SP.head("수위").replace("    ", "      ")
                    + "\n" + SP.render("수위", seed, nn, 2, skip=SP.HEAD["수위"]).replace("    ", "      "))
    s = c.get("설정") or {}
    if s.get("이름"):
        rows.append(f"  · **이 회차의 설정**: {s['이름']} -- {s.get('규칙', '')}. 이름으로 부르고"
                    " 조건으로 묶는다. 상태창 · 수치를 열지 마라 -- 격은 부르는 말과 물러서는 걸음으로 보인다.")
    cx = codex(book)
    if cx:
        rows.append("  · 설정집 (이 이름 그대로 쓴다 · 다시 설명하지 마라): "
                    + " · ".join(f"{x['이름']}({x.get('규칙', '')})" for x in cx[-6:]))
    if c.get("거둠"):
        rows.append(f"  · **거둔다:** {c['거둠']} -- 앞 회차에 심어 둔 그 낱말 · 그 물건을 그대로 다시 쓴다."
                    " 새 인물이 이 자리에서 나오면 기척 → 실루엣 → 한 마디 → 이명 → 판이 바뀐다.")
    if c.get("심음"):
        rows.append(f"  · **심는다:** {c['심음']} -- 지나가듯 한 문장. 설명하지 마라, 누구도 그것에 반응하지 마라.")
    if c.get("갈고리"):
        kind = c.get("갈고리종류") or ""
        when = ("**이 대목의 마지막 문단에서** " if last else "마지막 비트를 쓰게 되면 회차의 마지막 문단에서 ")
        rows.append(f"  · {when}**{kind}**이 벌어진다:"
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
    if c.get("바뀜"):
        out.append(f"  바뀜({c['바뀜'].get('축', '')}): {c['바뀜'].get('무엇', '')}")
    if c.get("쾌감"):
        out.append(f"  쾌감(비트 {c.get('쾌감자리', '')}): {c['쾌감']}")
    if c.get("전투"):
        out.append(f"  전투: {c['전투']}")
    if (c.get("설정") or {}).get("이름"):
        out.append(f"  설정: {c['설정']['이름']} -- {c['설정'].get('규칙', '')}")
    if c.get("심음") or c.get("거둠"):
        out.append(f"  심음: {c.get('심음', '')} / 거둠: {c.get('거둠', '')}")
    ps = plants(book)
    if ps:
        out.append("  아직 안 거둔 것: " + " · ".join(p["무엇"] for p in ps))
    cx = codex(book)
    if cx:
        out.append(f"  설정집 {len(cx)}개: " + " · ".join(x["이름"] for x in cx[-8:]))
    return "\n".join(out)


def show_codex(book: dict) -> str:
    """설정집 전부. drift.sh codex 가 부른다."""
    cx = codex(book)
    if not cx:
        return "설정집이 비어 있다 -- 각본이 서면 회차마다 하나씩 는다."
    return "\n".join(f"  {i + 1:2}. {x['이름']} -- {x.get('규칙', '')}  (회차 {int(x.get('ep', 0)) + 1})"
                     for i, x in enumerate(cx))
