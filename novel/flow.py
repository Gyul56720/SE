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
import difflib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel import drive as D                                          # noqa: E402
from novel import echo                                                # noqa: E402
from novel import diffusion                                           # noqa: E402
from novel import matter                                              # noqa: E402
from novel import shock as SH                                         # noqa: E402
from novel import rhythm                                              # noqa: E402
from novel import style                                               # noqa: E402

# 한 번에 받는 덩어리. 너무 크면 모델이 뒤로 갈수록 늘어지고, 너무 작으면 점층이 덩어리
# 경계에 잘린다. 1,200~1,500자가 문장론(점층 -> 전환)이 한 바퀴 도는 크기다.
# 인물 카드에 적는 것. **정하면 적어두고 다음부터 참조한다** -- 적어두지 않으면 모델은
# 세 덩어리 뒤에 다른 사람으로 만든다. 대사가 인물마다 달라지는 것도 이 카드에서 나온다:
# "거칠게" 는 한 인물의 특징이지 소설의 규칙이 아니다.
CARD = ("나이", "키", "성격", "혈액형", "가족", "과거", "트라우마",
        "좋아하는 것", "싫어하는 것", "취미", "전공", "직업", "말투", "버릇", "겉모습")

# **게이트는 최소로 만든다.** 자유도가 이 모드의 전부다 -- 기각이 잦으면 그 자유가 죽는다.
#
# 그래서 모순을 따지는 자리를 이만큼으로 줄인다:
#   · **주요 인물**(두 덩어리 이상 나온 사람)의
#   · **핵심 칸**(나이 · 생사 · 가족 · 직업 · 이름)만.
#
# 나머지는 전부 **기록만 하고 기각하지 않는다** -- 주변 사물, 스쳐 간 인물, 장소 묘사,
# 잡다한 사실. 실측(VM): "은색의 불규칙한 소리를 내는 물건" 이 "1950년대 독일 잡화점에서
# 판매된 은색 모델" 로 자세해진 것을 기각했다. 그건 같은 라이터고, 그런 기각이 원고를
# 못 나오게 한다. 놓친 모순은 사람이 읽다 발견하지만 과잉 기각은 글 자체를 없앤다.
CORE = ("나이", "생사", "가족", "직업", "이름", "성별")
# 주요 인물의 조건 둘 -- **자주 나오고, 카드가 두툼하다.** 하나만 보면 스쳐 간 행인이
# 두 번 언급됐다고 주요 인물이 되고, 그 사람 나이가 바뀐 것으로 원고가 기각된다(실측).
# 소설이 실제로 붙잡고 가는 사람은 등장이 잦고 설정도 쌓인다.
MAIN_AFTER = 3        # 이만큼 덩어리에 나와야
MAIN_FIELDS = 3       # 그리고 카드에 이만큼 칸이 차야 주요 인물이다

# **숫자로 정해지는 칸만 엄격하게 본다.** 나머지는 묘사이고, 묘사는 뒤로 갈수록 자세해지는
# 것이 정상이다 -- 그것까지 모순으로 잡으면 두 번째 덩어리부터 진도가 안 나간다.
# 실측(2026-09-04 VM): "은색의 불규칙한 소리를 내는 물건" 이 "1950년대 초반 독일 잡화점에서
# 판매된 은색 모델" 로 자세해진 것을 모순으로 기각했다. 그건 같은 라이터다.
STRICT = ("나이", "키", "혈액형", "생일", "몸무게", "연도", "번호")
SIMILAR = 0.55        # 이만큼 닮았으면 같은 것을 더 자세히 말한 것으로 본다

CHUNK = 1400
# 다시 쓰는 횟수. 모순·리듬·농도가 이 예산을 함께 쓴다. 둘이던 것을 셋으로 올렸다 --
# 재는 자가 늘었는데 예산이 그대로면 첫 지적만 고치고 끝난다.
# **표류 계수** -- 부조리의 세기. 1.0 이면 축을 전부 매번 켠다.
#
# 축을 넷이나 겹쳐 놓으니(확산 · 급발진 · 소재 · 사건) 뒤로 갈수록 부조리가 쌓였다.
# 사용자 평: "후반부로 갈 수록 조금 부조리가 심해져. drift 계수를 0.8로 해줘."
#
# 그래서 계수 하나로 셋을 함께 조인다 -- 급발진이 켜지는 비율, 소재의 갈래가 붙는 비율,
# 사건이 터지는 간격. 켜고 끄는 것은 해시라서 **이어 쓰기에도 같은 자리에서 같게** 나온다.
# 확산과 리듬은 건드리지 않는다. 그건 부조리가 아니라 문장의 문제다.
#
# 0.8 → 0.5 로 내렸다가 **1.0 으로 되돌렸다.** 계수를 낮춰서 밀도를 잡으려 했는데, 정작
# 밀도를 올린 것은 계수가 아니라 소재 축이었다(아래 MATTER). 급발진을 반으로 줄이니
# 밀도는 그대로인 채 인물만 밋밋해졌다 -- 원인이 아닌 것을 조인 셈이다.
#
# 그래서 급발진·사건은 매 덩어리 · 2,000자로 되돌리고, 소재 축을 끈다. 사용자 평이
# 가리킨 것이 그 배치였다: "매 덩어리 확산 + 급발진 1 / 2,000자마다 사건 -- 딱 이때가
# 제일 좋다."
DRIFT = 1.0

# **소재 축의 비율. 0 이면 끈다.**
#
# 갈래(총격전·던전·에일리언)와 매체(편지·노래·라디오)를 매 덩어리에 얹었더니 확산과
# 급발진 위에 셋이 더 쌓여 "너무 밀도가 높아졌다". 재료를 넓히려던 것이 재료를 들이붓는
# 것이 됐다. 껐다 -- 필요하면 --matter 0.3 처럼 조금만 켠다.
MATTER = 0.0

MAX_REWRITE = 3
# 다음 덩어리에 넘기는 꼬리. 900자였는데, 그러면 세 덩어리 앞의 소품이 창 밖으로 빠지고
# 점층이 매번 새로 시작한다(실측: "갈 수록 농도가 얕아져"). 식은 소품은 diffusion 이
# 이름으로 따로 올려주지만, 꼬리 자체도 한 뼘 늘려 둔다.
TAIL = 1200

# 첫 문장. **여기서 모든 것이 파생된다** -- 줄거리를 안 짜므로 이 몇 줄이 씨앗의 전부다.
# 좌표(나이·장소·자세)를 놓고, 배경을 하나의 그림으로 묶고, 마지막에 밖에서 안으로
# 넘어간다("아, 또 독일인가 하고 나는 생각했다"). style.py 의 [상황]/[전환] 이 말하는
# 것을 한 문단이 다 하고 있어서, 이 자리에 두면 다음 덩어리가 그 리듬을 이어받는다.
FIRST = (
    "서른 일곱 살이던 그때, 나는 보잉 747기 좌석에 앉아 있었다. "
    "그 거대한 비행기는 두터운 비구름을 뚫고 내려와, 함부르크 공항에 착륙을 "
    "시도하고 있었다.\n"
    "11월의 차가운 비가 대지를 어둡게 물들이고 있었고, 비옷을 걸친 정비공들, "
    "민둥민둥한 공항 빌딩 위에 나부끼는 깃발, BMW의 광고판 등 이런저런 것들이 "
    "플랑드르파의 음울한 그림의 배경처럼 보였다. 아, 또 독일인가 하고 나는 생각했다."
)

# 첫 덩어리에만 실린다. **내용을 지정하지 않는다** -- 예전엔 여기에 "양조장의 내력을
# 풀어라 / 크리스마스 이브다 / 오로라로 흘러라" 가 적혀 있었는데, 그건 그때 씨앗에 묶인
# 각본이었다. 첫 문장을 갈아 끼우면 그런 지시는 남의 이야기를 시키는 것이 된다.
#
# 그래서 **무엇을 쓸지가 아니라 어떻게 열지만** 말한다. 세계가 아직 비어 있어 확산 지시가
# 실리지 않는 유일한 덩어리이므로, 여기서 할 일은 딱 하나다 -- 다음 덩어리가 붙잡을
# 손잡이를 몇 개 만들어 두는 것.
OPENING = """[이 첫 덩어리가 할 일]
  * **첫 문장이 놓은 좌표에서 출발해라.** 거기 있는 것들(그 장소, 그 계절, 그 사물,
    화자의 나이)이 이야기의 재료다. 새 무대를 따로 차리지 마라.
  * **사람을 하나 만나게 해라.** 이름을 주고, 사정을 한 줄 주고, 말을 시켜라. 세계는
    사람에서 자란다.
  * **가짜를 진짜처럼 지어내라** -- 그 건물이 언제 지어졌는지, 왜 그렇게 불리는지,
    누가 거기 있었는지. 사전에 없는 것이라도 있는 것처럼 대라.
  * 사건을 만들려 애쓰지 마라. 첫 덩어리는 **손잡이를 만드는 자리**다 -- 다음 덩어리가
    다시 만질 사람 하나, 장소 하나, 물건 하나. 그걸로 충분하다.
  * 마지막은 닫지 마라. 문장 하나를 열어둔 채로 끊어라."""


# ---------------------------------------------------------------- 원장

def blank(first: str = FIRST) -> dict:
    # shocks: 지금까지 터진 사건의 수. 뽑기가 여기 묶여 있어 이어 쓰기에도 순서가 이어진다.
    # since: 마지막 사건 이후 쓴 글자 수.
    # words: 지어낸 낱말과 그 뜻. **기록만 하고 절대 기각하지 않는다** -- 다만 한 번 뜻을
    # 준 말은 계속 같은 뜻으로 쓰여야 해서 원장에 남긴다.
    return {"first": first, "chunks": [], "shocks": 0, "since": 0, "drift": DRIFT,
            "matter": MATTER,
            "ledger": {
        "people": {}, "places": {}, "facts": {}, "time": [], "objects": {},
        "words": {}}}


def _merge(ledger: dict, delta: dict, at: int = 0) -> list:
    """새로 확정된 것을 원장에 더한다. **기각할 것만** 돌려준다.

    기각 대상은 위 CORE 참고 -- 주요 인물의 핵심 칸뿐이다. 나머지는 값이 달라져도
    새 값으로 갱신하고 넘어간다. 세계는 자라라고 두는 것이지 붙잡아 두는 것이 아니다."""
    clashes = []

    def _elaborates(old_v: str, new_v: str) -> bool:
        """새 값이 옛 값을 더 자세히 말한 것인가. 판정이 애매하면 **너그러운 쪽**이다."""
        a, b = re.sub(r"\s+", "", old_v), re.sub(r"\s+", "", new_v)
        if a in b or b in a:
            return True
        if difflib.SequenceMatcher(None, a, b).ratio() >= SIMILAR:
            return True
        aw = {w for w in re.split(r"[\s·,]+", old_v) if len(w) >= 2}
        bw = {w for w in re.split(r"[\s·,]+", new_v) if len(w) >= 2}
        return bool(aw & bw)

    def _clean(v):
        return str(v).strip() if isinstance(v, (str, int, float)) and str(v).strip() else None

    # ---- 인물: 카드로 자란다. 주요 인물의 핵심 칸만 기각한다.
    for name, v in (delta.get("people") or {}).items():
        cur = ledger["people"].get(name)
        card = dict(cur) if isinstance(cur, dict) else ({"소개": cur} if cur else {})
        seen = int(card.get("_seen", 0)) + 1
        filled = len([k for k in card if not k.startswith("_")])
        main = seen >= MAIN_AFTER and filled >= MAIN_FIELDS
        fields = v if isinstance(v, dict) else {"소개": v}
        for f, raw in fields.items():
            fv = _clean(raw)
            if fv is None or f == "_seen":
                continue
            old_v = card.get(f)
            if not old_v or old_v == fv:
                card[f] = fv
                continue
            gated = main and any(k in f for k in CORE)
            if not gated:
                card[f] = fv if len(fv) > len(old_v) else old_v   # 자세한 쪽을 남긴다
                continue
            if any(k in f for k in STRICT):
                a, b = re.sub(r"\D", "", old_v), re.sub(r"\D", "", fv)
                if a and a == b:
                    continue
            elif _elaborates(old_v, fv):
                card[f] = fv if len(fv) > len(old_v) else old_v
                continue
            clashes.append(f"{name}의 {f}: 앞에서는 '{old_v}' 였는데 지금 '{fv}' 다")
        card["_seen"] = seen
        ledger["people"][name] = card

    # ---- 나머지: **기록만 한다. 절대 기각하지 않는다.**
    for bucket in ("places", "facts", "objects", "words"):
        for k, raw in (delta.get(bucket) or {}).items():
            v = _clean(raw)
            if v is None:
                continue
            old_v = ledger[bucket].get(k)
            ledger[bucket][k] = v if not old_v or len(v) > len(str(old_v)) else old_v
    # **언제 놓였는지 적어 둔다.** 회수는 가까운 과거를 향해야 한다 -- 나이를 모르면
    # 첫 장면의 물건이 영원히 "식은 소품" 으로 남아 원고를 처음으로 되돌린다(실측).
    age = ledger.setdefault("_age", {})
    for name in diffusion.props(ledger):
        age.setdefault(name, at)
    for t in (delta.get("time") or []):
        if t and t not in ledger["time"]:
            ledger["time"].append(t)
    return clashes


def is_main(card) -> bool:
    """주요 인물인가 -- 자주 나왔고(3회) 카드도 두툼하다(3칸). _merge 와 같은 잣대다."""
    if not isinstance(card, dict):
        return False
    filled = sum(1 for k, v in card.items() if v and not k.startswith("_"))
    return int(card.get("_seen", 0)) >= MAIN_AFTER and filled >= MAIN_FIELDS


# 브리핑에 쓰는 창의 크기와 상한.
#
# **원장은 자라도 브리핑은 자라면 안 된다.** 원고가 길어질수록 인물·장소·사물·사실이
# 쌓이고, 그것이 매 덩어리 프롬프트에 통째로 실리면서 뒤로 갈수록 농도가 올라갔다
# (사용자 평: "뒤로 갈수록 조금 밀도가 높아져서 처음 1/2 지점 정도로 유지해주면 좋겠다").
#
# 그래서 브리핑을 **창(window)** 으로 만든다. 최근 열두 덩어리 안에 놓인 것만 싣고,
# 주요 인물은 나이와 무관하게 늘 싣는다 -- 그 사람들의 카드가 대사를 갈라 놓는 근거라서
# 빠지면 목소리가 무너진다. 그러고도 넘치면 글자 수로 자른다.
#
# 잘려 나간 것이 사라지는 것은 아니다. 원장에는 그대로 남아 모순 검사에 계속 쓰인다 --
# 눈앞에서 치우는 것이지 잊는 것이 아니다.
BRIEF_WINDOW = 12
BRIEF_MAX = 1400


def brief(ledger: dict, limit: int = 40, now: int = 0) -> str:
    """원장을 프롬프트에 실을 형태로.

    **주요 인물만 카드를 통째로 펼친다.** 대사가 인물마다 달라지려면 나이도 말투도
    트라우마도 그 자리에 있어야 하지만, 그건 계속 말하는 사람 이야기다. 5만 자를 쓰면
    스쳐 간 사람이 쉰 명씩 쌓이는데(우체부, 옆자리 손님, 이름만 나온 삼촌) 그들의 카드까지
    매 덩어리에 펼치면 프롬프트가 원장으로 가득 찬다 -- 그러면 정작 읽어야 할 꼬리와 확산
    지시가 뒤로 밀리고, 호출 하나가 무거워져 RPM 도 빨리 마른다.

    그래서 조연은 **한 줄로 접는다.** 접혀 있어도 이름은 남으니 확산의 연료로는 그대로
    쓰인다. 그 사람이 다시 자주 나오기 시작하면 _seen 이 차면서 저절로 펼쳐진다.
    """
    out = []
    age = ledger.get("_age") or {}

    def fresh(k):
        born = age.get(k)
        return born is None or now - born <= BRIEF_WINDOW

    people = list(ledger.get("people", {}).items())
    if people:
        main = [(n, c) for n, c in people if is_main(c)]
        # 조연도 창으로 자른다. **주요 인물만 나이를 안 본다** -- 그 카드가 대사를 갈라
        # 놓는 근거라서 빠지면 목소리가 무너진다. 스쳐 간 사람은 이름만 남아 있으면
        # 되는데, 그 이름이 쉰 개면 그것이 곧 밀도다.
        rest = [(n, c) for n, c in people if not is_main(c) and fresh(n)]
        if main:
            out.append("  [인물]")
            for name, card in main:
                fields = " · ".join(f"{k} {v}" for k, v in card.items()
                                    if v and not k.startswith("_"))
                out.append(f"    {name} — {fields}")
        if rest:
            brief_rest = []
            for name, card in rest[-limit:]:
                if isinstance(card, dict):
                    bit = next((f"{k} {v}" for k, v in card.items()
                                if v and not k.startswith("_")), "")
                else:
                    bit = str(card)
                brief_rest.append(f"{name}({bit})" if bit else name)
            out.append("  [스쳐 간 사람] " + " · ".join(brief_rest))
    for bucket, label in (("places", "장소"), ("objects", "사물"), ("facts", "사실"),
                          ("words", "지어낸 말")):
        items = [(k, v) for k, v in (ledger.get(bucket) or {}).items() if fresh(k)][-limit:]
        if items:
            out.append(f"  {label}: " + " · ".join(f"{k}={v}" for k, v in items))
    if ledger.get("time"):
        out.append("  시간: " + " → ".join(ledger["time"][-6:]))

    text = "\n".join(out) or "  (아직 비어 있다)"
    if len(text) > BRIEF_MAX:
        # 넘치면 뒤에서부터 자른다. 주요 인물 줄이 앞에 있어서 그쪽이 먼저 살아남는다.
        keep, used = [], 0
        for line in out:
            if used + len(line) > BRIEF_MAX:
                keep.append("  (오래된 것은 접었다 -- 원장에는 그대로 있다)")
                break
            keep.append(line)
            used += len(line) + 1
        text = "\n".join(keep)
    return text


# 이어 쓰는 덩어리에만 붙는다. **원고가 첫 장면으로 되돌아간 실측** 때문에 생겼다 --
# 확산이 "다시 만질 것" 으로 첫 문장의 공항과 비행기를 계속 올려 주니 모델이 성실하게
# 거기로 돌아갔다. 나이(diffusion.FUEL_AGE)로 연료를 자르는 것이 근본 대응이고, 이건
# 그 위에 얹는 못이다 -- 재료와 장소를 갈라 말해 준다.
FORWARD = """
  * **이 마지막 문장 다음 순간부터 써라.** 여기가 지금이다.
  * **시간은 앞으로만 간다.** 앞 장면으로 돌아가지 마라. 특히 **첫 장면으로는 절대
    돌아가지 마라** -- 그 공항, 그 비행기, 그 도착은 이미 지나갔다. 회상으로 들르는 것도
    한 덩어리에 한 번을 넘기지 마라.
  * 위 [세계] 에 적힌 것은 **다시 쓸 수 있는 재료**이지 다시 갈 장소가 아니다."""


# ---------------------------------------------------------------- 프롬프트

def _level(book: dict) -> float:
    """이 덩어리의 표류 세기. 원고의 계수를 중심으로 덩어리마다 흔들린다."""
    return matter.level_at(book.get("seed_id") or book["first"],
                           len(book["chunks"]),
                           float(book.get("drift", DRIFT)))


def _matter(book: dict) -> str:
    """**소재** -- 이번 덩어리에 섞을 재료. 확산·리듬이 '어떻게' 라면 이건 '무엇' 이다.

    이 축이 없을 때 모델은 늘 비슷한 것을 냈다 -- 술집, 부두, 낡은 차, 담배. 세계가
    넓어져도 재료가 안 넓어졌다.
    """
    seed = book.get("seed_id") or book["first"]
    n = len(book["chunks"])
    rate = float(book.get("matter", MATTER))
    if not matter.gate(seed, n, "matter", rate):
        return ""
    return matter.brief(matter.draw(seed, n, _level(book)))


def _impulse(book: dict) -> str:
    """**급발진** -- 인물이 스스로 저지르는 것. 사건(shock)과 다른 물건이다.

    사건은 밖에서 들이닥쳐 점층을 끊는다. 급발진은 흐름 **안에서** 한 번 튄다 -- 세계가
    바뀌지 않고 분위기만 바뀌므로, 확산을 대신하지 않고 확산 안에 들어간다. 그래서 매
    덩어리에 하나씩 걸어도 된다. 뽑기는 덩어리 번호에 묶여 이어 쓰기에도 재현된다.
    """
    seed = book.get("seed_id") or book["first"]
    n = len(book["chunks"])
    # 계수만큼만 켠다. 꺼진 덩어리에서도 성격은 그대로다 -- 저지르지 않을 뿐이다.
    if not matter.gate(seed, n, "impulse", _level(book)):
        return ("  * 이번 덩어리에는 급발진을 넣지 마라. 그렇다고 사람이 바뀌는 것은"
                " 아니다 -- 저지르지 않을 뿐, 말투도 태도도 그대로다.")
    return SH.impulse_brief(SH.impulse(seed, n))


def _push(book: dict) -> str:
    """이 덩어리가 할 일 -- **평소엔 확산, 사건 차례엔 사건.**

    사건은 확산을 **한 덩어리만** 대신한다. 터지고 나면 다음 덩어리부터 다시 점층이다 --
    다만 그때의 세계는 사건이 바꿔 놓은 세계라, 같은 자리에서 다시 쌓지 않는다.
    """
    if book.get("_shock"):
        return SH.brief(book["_shock"]) + """

  * 다음 덩어리부터는 **다시 점층이다.** 사건은 여기서 한 번 끊는 것이지 방향을 바꾸는
    것이 아니다. 이 사건이 남긴 것에서 다시 쌓기 시작한다."""
    return _diffuse(book)


def _diffuse(book: dict) -> str:
    """**확산 지시** -- 뒤로 갈수록 옅어지는 것을 여기서 막는다.

    다음 덩어리에게 넘어가는 것은 꼬리 900자뿐이라, 세 덩어리 앞의 소품은 창 밖으로
    빠진다. 그래서 **식은 소품을 이름으로 짚어 다시 올려준다.** 원장을 제약이 아니라
    재료로 쓰는 자리가 여기다.
    """
    fuel = diffusion.cold(book["ledger"], "".join(book["chunks"])[-TAIL:],
                          now=len(book["chunks"]))
    pick = ("  * 이번에 다시 만질 것 -- " + " · ".join(fuel[:8]) + "\n"
            "    이 중 **둘 이상**을 다시 꺼내되, 똑같이 쓰지 마라. 한 단계 키운다:\n"
            "      그냥 놓여 있던 것이 → 쓰이거나 · 망가지거나 · 없어지거나 ·\n"
            "      다른 사람 손에 있거나 · 그것 때문에 일이 생긴다\n") if fuel else ""
    return f"""[확산] **이야기는 뒤로 갈수록 짙어져야 한다 -- 옅어지면 실패다.**

한 덩어리는 세계를 **넓히고(새것)** 동시에 **깊게 한다(앞엣것을 키운다).** 둘 중 하나만
하면 산만해지거나 제자리를 돈다. 이건 재서 판정한다:

  * 새로 놓는 것 **{diffusion.LIMITS['new']}개 이상** -- 새 사람, 새 장소, 새 물건, 새 사실.
    이름을 붙이되 **연식·산지·상표를 접두사로 달지 마라**('1982년형 볼보', '1978년산
    판화집' 처럼). 연도 표기는 이 덩어리에 {diffusion.LABEL_MAX}개까지다. 구체성은 명사를
    꾸미는 데서 오지 않고 **그것이 무엇을 하는가**에서 온다. 상황 설명으로 분량을 채우지 마라.
  * 앞에서 나온 것 **{diffusion.LIMITS['back']}개 이상**을 다시 만진다. 다만 **한 이름을
    {diffusion.ECHO_MAX}번까지만 부른다** -- 회수는 다시 부르는 것이 아니라 다시 쓰는 것이다.
    두 번째부터는 '그것', '그 차', '그 종이' 로 받아라.
{pick}
[대사가 이야기다] **설명으로 넘기지 말고 말로 진행시켜라.**
  * 긴 대사 **{diffusion.LIMITS['long']}개 이상**({diffusion.TALK_LONG}자 넘게) -- 누가 한 번은
    길게 떠든다. 변명이든, 수다든, 아무도 안 물어본 집안 내력이든, 틀린 지식이든.
    **소품의 유래는 서술이 아니라 이 자리에서 나온다.**
  * 짧은 대사 **{diffusion.LIMITS['short']}개 이상**({diffusion.TALK_SHORT}자 이하) -- 끊고,
    받아치고, 딴소리한다. 긴 것과 짧은 것이 번갈아야 대화가 리듬을 갖는다.
  * **이상한 대화를 해라.** 지금 상황과 상관없는 것을 궁금해하고, 엉뚱한 데서 정색하고,
    농담을 무표정하게 던진다. 용건만 오가는 대사가 제일 재미없다.
  * **감탄사를 지어내고 문법을 놓아라.** "끼얏호", "어라랍쇼", "헐랭", "우와씨", "쓰읍",
    "푸하" -- 사전에 없어도 좋다. 그 사람이 낼 법한 소리면 그만이다. 문장을 끝까지
    맺지 않아도, 어순이 뒤집혀도, 조사가 빠져도 된다. **말끝을 다듬으면 그게 딱딱함이다.**

{_impulse(book)}
{_matter(book)}
[잡소리] **쓸데없는 말이 이 소설의 재미다 -- 다만 늘 같은 수를 쓰지 마라.**
아래는 **개그 자리에서만** 꺼내는 수다. 매 덩어리마다 전부 하려 들면 그게 버릇이 되고,
버릇이 되는 순간 안 웃긴다. 이 덩어리에 어울리는 것 **하나쯤**만 골라라. 안 골라도 된다.
  · 아무도 안 물어본 내력을 길게 늘어놓는다
  · 멍청한 소리를 아주 진지하게 한다. 아무도 안 웃는다
  · 지금 상황과 아무 상관없는 것을 두고 둘이 다툰다
  · 틀린 지식을 자신 있게 말하고, 아무도 고쳐 주지 않는다
  · 별명을 붙인다. 본인만 모른다

[전환] **외현에서 내현으로.** 이 덩어리 어딘가에서 한 번은 넘어가라 -- 사물·풍경·행동을
보다가 생각·기억·잃어버린 것으로. 그 자리에서만 넘어간다. 넘어가는 지점은 매번 달라야
한다."""


def write_prompt(book: dict, feedback: str = "") -> str:
    tail = "".join(book["chunks"])[-TAIL:]
    opening = not book["chunks"]
    return f"""{'이 문장으로 소설을 연다' if opening else '아래 글을 이어서 쓴다'}.

{style.narrator()}

[이 소설의 온도] **가볍고 재미있게.** 무겁게 가지 마라. 큰일 앞에서도 사소한 것을 신경
쓰고, 농담은 무표정하게 던지고, 과장된 반응은 옆 사람이 한다. 비장해지려는 문장이 나오면
그 다음 줄에서 김을 빼라.

[대사] **인물에 맞게.** 소설 전체에 한 가지 말투를 씌우지 마라 -- 거친 것은 어떤 인물의
특징이지 이 소설의 규칙이 아니다.
- 아래 [세계]의 인물 카드에 **말투**가 적혀 있으면 그대로 쓴다. 마흔둘 정비공과 스물셋
  대학원생과 예순의 어머니는 같은 문장을 쓰지 않는다.
- 카드에 없는 인물이면 **지금 정하고, 그 다음부터 그대로 간다.** 나이·성격·직업·과거가
  말투를 정한다. 정한 것은 추출기가 카드에 적어둔다.
- 말을 끊고, 겹치고, 대답 대신 딴소리를 하는 것은 누구나 한다. 어휘는 자유다 -- 상표든
  욕이든 외국어든 사투리든 **그 사람이 쓸 법한 말**을 그대로 쓴다.

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

[세계 — 지금까지 놓인 것들]
{brief(book['ledger'], now=len(book['chunks']))}
  * 이건 금지 목록이 아니라 **연료다.** 여기 있는 것을 다시 꺼내 쓰는 것이 이 소설의
    본체다. 어긋나게만 쓰지 마라 -- 나머지는 전부 자유다.
  * 여기 없는 것은 **새로 지어내도 된다.** 지어냈으면 자세히 지어내라 -- 이름, 연도,
    누가 지었는지, 왜 그렇게 불리는지.
  * 인물이 새로 나오면 **그 자리에서 사람을 만들어라.** 나이와 키, 성격, 가족, 과거,
    트라우마, 좋아하는 것, 취미, 전공, 직업, 말투, 버릇까지. 전부 한 번에 늘어놓지는 마라 --
    지금 필요한 두세 개만 문장에 녹이고, 나머지는 뒤에서 하나씩 드러낸다.

{OPENING if opening else _push(book)}

{'[첫 문장 — 이것으로 시작하라]' if opening else '[지금까지의 끝부분 — 여기서 이어 쓴다]'}
{book['first'] if opening else '...' + tail}
{'' if opening else FORWARD}

규칙:
- 약 {CHUNK}자를 쓴다. 끊지 말고 이어라. 회차도 씬도 없다.
- **줄거리를 미리 정하지 마라.** 지금 문장에서 다음 문장이 나오게 하라. 앞 문장을 좁히거나,
  키우거나, 뒤집어라(점층). 그러다 밖에서 안으로 들어가라(전환). 그 리듬을 매번 다르게.
- **길이를 섞어라 -- 이건 재서 판정한다.** 다 쓴 뒤 코드가 세어 보고, 넘으면 숫자를
  돌려주며 다시 시킨다:
    · 마흔 자 넘는 긴 문장이 **서술문의 15% 이상**. 짧은 문장 서넛에 하나씩은
      쉼표로 이어 붙인 긴 문장이 와야 한다
    · **짧은 '-다'** 로 끝나는 서술문이 62% 아래. 긴 '-다' 는 세지 않는다 --
      단조로움의 정체는 종결어미가 아니라 길이다
    · 짧은 '-다' 가 내리 **네 번**을 넘지 않는다. 셋째나 넷째에서 생각을 붙이거나,
      대사를 넣거나, 문장을 끝내지 마라
    · 대사가 전체 줄의 **10% 이상**. 사람을 만나게 하고 말을 시켜라
- **앞에 쓴 문장을 다시 적지 마라.** [지금까지의 끝부분]은 읽으라고 준 것이지 옮겨
  적으라고 준 것이 아니다. 그 다음 문장부터 시작해라. 분량이 모자라면 앞 문단을
  복사하지 말고 **새 일이 일어나게** 해라.
- 사람과 장소의 이름을 구체적으로 대라. 없는 것도 있는 것처럼 자세히 -- 다만 그 자세함이
  수식어가 아니라 **행동과 사정**으로 오게 해라.
{feedback}

산문만 출력한다. 제목도 머리말도 표식도 쓰지 마라."""


def extract_prompt(chunk: str) -> str:
    return f"""아래 글에서 **새로 확정된 사실만** 뽑아 JSON 으로 옮긴다.

{chunk}

규칙:
- 확정된 것만. 추측·비유·인물의 생각은 넣지 마라.
- 값은 짧은 한국어로. 한 항목에 한 줄.
- 새로 나온 것이 없는 칸은 빈 객체로 둔다.
- **인물은 카드로 적는다.** 글에 드러난 칸만 채워라. 안 나온 칸은 빼라 -- 지어내지 마라.
  쓸 수 있는 칸: {" · ".join(CARD)}
- **지어낸 낱말은 words 에 뜻과 함께 적어라.** 사전에 없는 말이 나오고 거기 뜻이나 유래가
  달렸으면 그것이다. 한 번 적힌 말은 다음 덩어리에서도 같은 뜻으로 쓰인다.
- 말투 칸이 중요하다. 그 사람이 어떻게 말하는지 한 줄로 적어라
  (예: "존댓말인데 끝을 흐린다", "짧게 끊고 욕을 섞는다", "말이 길고 자꾸 되묻는다").
  **입버릇·감탄사가 있으면 그것까지 적어라** -- "놀라면 '어라랍쇼' 라고 한다",
  "말 시작 전에 '쓰읍' 하고 숨을 들이켠다". 그 사람이 다음에도 같은 소리를 내야 한다.

JSON 만 출력:
{{"people": {{"이름": {{"나이": "42", "직업": "양조장 정비공",
                     "말투": "짧게 끊는다. 욕을 섞는다", "과거": "..."}}}},
  "places": {{"장소": "어떤 곳인가 한 줄"}},
  "objects": {{"사물": "무엇인가 한 줄"}},
  "words": {{"꿉꿉하다": "눅눅한데 마음 쪽에 쓰는 말. 웅포 지방 말"}},
  "facts": {{"항목": "확정된 값"}},
  "time": ["시점 한 줄"]}}"""


# ---------------------------------------------------------------- 루프

def _after(book: dict, text: str) -> None:
    """덩어리를 채택한 뒤. 사건이 터졌으면 계수를 올리고 분량을 0 부터 다시 센다."""
    if book.get("_shock"):
        book["shocks"] = book.get("shocks", 0) + 1
        book["since"] = 0
    else:
        book["since"] = book.get("since", 0) + len(text)
    book["_shock"] = None


def step(book: dict, llm, log=None) -> dict:
    """덩어리 하나.

    두 가지를 본다. **모순은 원고를 죽이고, 리듬은 죽이지 않는다.**

      · 모순 -- 앞에서 쓴 것과 어긋나면 기각하고 다시 받는다. 끝내 못 풀면 멈춘다.
      · 리듬 -- 짧은 '-다' 가 줄줄이거나 대사가 없으면 숫자를 돌려주고 다시 받되,
        끝내 안 고쳐지면 **그중 제일 나은 것을 채택한다.** 취향 때문에 원고를 버릴 수는
        없다 -- 자유도가 이 모드의 전부다.
    """
    # **사건 차례인가.** 분량이 찼거나(약 2,000자), 원장이 부풀어 프롬프트가 무거워졌거나.
    # 첫 덩어리는 건너뛴다 -- 시작하자마자 남이 문을 부수고 들어오면 세계가 서기 전이다.
    book.setdefault("shocks", 0)
    book.setdefault("since", 0)
    book["_shock"] = None
    if book["chunks"]:
        D._log(f"[flow] 이번 세기 {_level(book):.2f} (기준 {book.get('drift', DRIFT)})")
    if book["chunks"] and SH.due(book["since"],
                                 len(brief(book["ledger"], now=len(book["chunks"]))),
                                 _level(book)):
        book["_shock"] = SH.draw(book.get("seed_id") or book["first"], book["shocks"])
        D._log(f"[flow] 사건 {book['shocks'] + 1} -- {book['_shock']['who']} / "
               f"{book['_shock']['how']} / {book['_shock']['scale']}")

    feedback = ""
    best = None
    # 재시도가 메아리로만 소진되면 아래 반환문이 clashes 를 못 찾는다(실측:
    # UnboundLocalError). 판정을 한 번도 못 했다는 뜻이므로 빈 목록에서 시작한다.
    clashes: list[str] = []                                   # (점수, 본문, 원장) -- 리듬만 걸린 후보
    for attempt in range(1, MAX_REWRITE + 2):
        text = D._llm_for(llm, "narrator")(write_prompt(book, feedback)).strip()

        # **꼬리를 옮겨 적은 앞부분은 도려낸다.** 판정할 것도 없다 -- 이미 원고에 있는
        # 글자다. 호출을 한 번 더 쓰는 것보다 잘라내는 편이 싸고 확실하다.
        text, dropped = echo.trim(text, "".join(book["chunks"]))
        if dropped:
            D._log(f"[flow] 앞 글을 옮겨 적은 {dropped:,}자를 도려냈다")

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
        clashes = _merge(probe, delta, at=len(book["chunks"]))
        if not clashes:
            # 사건 덩어리는 확산으로 재지 않는다 -- 거기서는 넓히고 회수하라고 시키지
            # 않았다. 리듬만 본다(대사와 길이는 사건이든 아니든 지켜야 한다).
            # **메아리는 모순과 같은 급이다** -- 취향이 아니라 결함이라 반드시 다시 받는다.
            # 실측: 한 덩어리 2,024자 중 610자(30%)가 글자 하나 안 틀리고 반복이었다.
            noise = echo.check(text, "".join(book["chunks"][:-1]))
            if noise and attempt <= MAX_REWRITE:
                D._log(f"[flow] 메아리 -- 다시 쓴다 ({attempt}/{MAX_REWRITE}): {noise[0][:60]}")
                feedback = ("\n[직전 시도가 앞 문장을 그대로 다시 뱉었다]\n"
                            + "\n".join(f"  · {c}" for c in noise)
                            + "\n  같은 사건을 다시 쓰지 말고 **그 다음에 일어나는 일**을 써라.\n")
                continue

            limp = rhythm.check(text) + noise
            mark = rhythm.score(text)
            if not book.get("_shock"):
                limp += diffusion.check(text, book["ledger"], probe,
                                        now=len(book["chunks"]))
                mark += diffusion.score(text, book["ledger"], probe)
            if limp and attempt <= MAX_REWRITE:
                if best is None or mark < best[0]:
                    best = (mark, text, probe)
                D._log(f"[flow] 농도·리듬 {len(limp)}건 -- 다시 쓴다 "
                       f"({attempt}/{MAX_REWRITE}): {limp[0][:70]}")
                feedback = ("\n[직전 시도를 재서 나온 숫자다. 이것만 고쳐라]\n"
                            + "\n".join(f"  · {c}" for c in limp)
                            + "\n  사건은 그대로 좋다. **줄이지 말고 늘려라** -- 세계를 더 놓고,"
                              " 앞엣것을 다시 꺼내고, 말을 더 시켜라.\n")
                continue
            if limp:
                if best is not None and best[0] < mark:
                    text, probe = best[1], best[2]
                    D._log("[flow] 끝내 못 고쳤다 -- 그중 제일 짙은 것을 채택한다")
                else:
                    D._log("[flow] 끝내 못 고쳤다 -- 그대로 채택한다")
            book["ledger"] = probe
            book["chunks"].append(text)
            _after(book, text)
            D._log(f"[flow] 덩어리 {len(book['chunks'])} · {len(text):,}자 · "
                   f"누적 {sum(len(c) for c in book['chunks']):,}자")
            return {"status": "ok", "chars": len(text), "clashes": []}
        D._log(f"[flow] 모순 {len(clashes)}건 -- 다시 쓴다 ({attempt}/{MAX_REWRITE + 1}): "
               f"{clashes[0][:80]}")
        feedback = ("\n[직전 시도가 기각된 이유 — 앞에서 쓴 것과 어긋난다]\n"
                    + "\n".join(f"  · {c}" for c in clashes)
                    + "\n  **이것만** 고쳐라. 나머지는 자유다 -- 몸을 사리지 말고,"
                      " 사건도 대사도 소품도 앞서와 같은 밀도로 그대로 가라.\n")
    if best is not None:              # 모순은 못 풀었지만 리듬만 걸린 후보가 있다
        book["ledger"] = best[2]
        book["chunks"].append(best[1])
        _after(book, best[1])
        D._log("[flow] 마지막 시도가 모순이다 -- 앞서 통과한 후보를 채택한다")
        return {"status": "ok", "chars": len(best[1]), "clashes": []}
    return {"status": "blocked", "chars": 0, "clashes": clashes}


def _save(book: dict, path) -> None:
    if path:
        Path(path).write_text(json.dumps(book, ensure_ascii=False, indent=1),
                              encoding="utf-8")


def run(book: dict, llm, target: int, path=None, deadline=None) -> dict:
    # **시작하자마자 한 번 쓴다.** 첫 덩어리를 다 받고서야 파일이 생기면, 아직 쓰는
    # 중인지 시작도 못 한 건지 밖에서 구분할 방법이 없다(실측: --read 가
    # FileNotFoundError 로 죽었는데 프로세스는 멀쩡히 첫 덩어리를 받고 있었다).
    _save(book, path)
    while sum(len(c) for c in book["chunks"]) < target:
        if deadline and time.time() > deadline:
            D._log("[flow] 시간 상한 -- 여기서 멈춘다")
            break
        r = step(book, llm)
        _save(book, path)
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
    ap.add_argument("--hours", type=float, default=12.0)
    ap.add_argument("--drift", type=float, default=DRIFT,
                    help="표류 계수 0~1. 낮출수록 급발진·사건이 줄어든다 (기본 1.0)")
    ap.add_argument("--matter", type=float, default=MATTER,
                    help="소재 축(갈래·매체)을 섞는 비율 0~1. 기본 0 -- 꺼져 있다")
    a = ap.parse_args()

    if a.read:
        if not Path(a.read).exists():
            print(f"그런 파일이 없다: {a.read}\n"
                  f"  런은 **시작하자마자** 한 번 저장한다. 그러니 파일이 없다는 것은\n"
                  f"  아직 쓰는 중이라는 뜻이 아니라 **런이 시작도 못 했다**는 뜻이다.\n"
                  f"  살아 있는지, 왜 죽었는지 순서대로 봐라:\n"
                  f"    /usr/bin/pgrep -af 'novel/flow.py'\n"
                  f"    tail -40 logs/flow.log\n"
                  f"  (--out 에 준 경로와 --read 에 준 경로가 같은지도 확인해라)",
                  file=sys.stderr)
            return 1
        book = json.loads(Path(a.read).read_text(encoding="utf-8"))
        print(text_of(book))
        print(f"\n---\n덩어리 {len(book['chunks'])}개 · "
              f"{sum(len(c) for c in book['chunks']):,}자", file=sys.stderr)
        return 0

    path = a.resume or a.out
    book = (json.loads(Path(path).read_text(encoding="utf-8"))
            if a.resume and Path(a.resume).exists() else blank(a.first))
    # **--drift 는 이어 쓰기에도 먹는다.** 뒤로 갈수록 부조리가 심해지면 중간에 낮춰서
    # 이어 갈 수 있어야 한다 -- 그러자고 원고를 버리게 하면 안 된다.
    book["drift"] = max(0.0, min(1.0, a.drift))
    book["matter"] = max(0.0, min(1.0, a.matter))
    D._log(f"[flow] 목표 {a.chars:,}자 · 지금 "
           f"{sum(len(c) for c in book['chunks']):,}자 · 표류 계수 {book['drift']}"
           f" · 소재 {book['matter']}")
    r = run(book, D.default_llm, a.chars, path, time.time() + a.hours * 3600)
    D._log(f"[flow] 끝 -- 덩어리 {r['chunks']}개 · {r['chars']:,}자 · {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
